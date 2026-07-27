"""Classify itemName rows that remain parser-dropped across two OCR models."""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
SERVER = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(SERVER))

from itemname_drop_analysis import (  # noqa: E402
    _best_line,
    _line_text,
    rejection_reason,
    relaxed_synth_reason,
    synth_rejection_reason,
)
from replay_free import _deserialize_lines  # noqa: E402
from extractors.master_match import get_matcher  # noqa: E402
from extractors import invoice_statement_free as F  # noqa: E402


def _load(path: str) -> dict[str, Any]:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _arithmetic_merge_possible(
    line_index: int | None,
    raw_lines: list,
    compared_rows: list[dict[str, Any]],
) -> bool:
    if line_index is None or not (0 <= line_index < len(raw_lines)):
        return False
    try:
        name_points = raw_lines[line_index][0]
        name_ys = [float(point[1]) for point in name_points]
    except Exception:
        return False
    cy = sum(name_ys) / len(name_ys)
    band = max((max(name_ys) - min(name_ys)) * 1.2, 14.0)
    values: set[float] = set()
    for index, raw_line in enumerate(raw_lines):
        if index == line_index:
            continue
        try:
            points, text = raw_line[0], str(raw_line[1] or "")
            ys = [float(point[1]) for point in points]
        except Exception:
            continue
        if not ys or abs(sum(ys) / len(ys) - cy) > band:
            continue
        for raw_value in F._TRIPLE_MONEY_RE.findall(text):
            parsed = F._upa_parse_money(raw_value)
            if parsed is not None and parsed > 0:
                values.add(parsed)
    triples: set[tuple[float, frozenset[float]]] = set()
    for quantity in values:
        if not (float(quantity).is_integer() and 2 <= quantity <= 9999):
            continue
        for unit_price in values:
            if unit_price < 10 or unit_price == quantity:
                continue
            for amount in values:
                if amount < 100 or amount in (quantity, unit_price):
                    continue
                if abs(quantity * unit_price - amount) <= 1:
                    triples.add((amount, frozenset((quantity, unit_price))))
    if len(triples) != 1:
        return False
    amount, quantity_unit = next(iter(triples))
    quantity, unit_price = sorted(quantity_unit)

    def row_value(row: dict[str, Any], key: str) -> float | None:
        cell = ((row.get("cells") or {}).get(key) or {}).get("ext")
        return F._upa_parse_money(F._UPA_SQ_RE.sub("", str(cell or "")))

    targets = 0
    for row in compared_rows:
        item_name = ((row.get("cells") or {}).get("itemName") or {}).get("ext")
        if str(item_name or "").strip() or row_value(row, "amount") != amount:
            continue
        row_quantity = row_value(row, "quantity")
        row_unit = row_value(row, "unitPrice")
        if row_quantity is not None and row_quantity != quantity:
            continue
        if row_unit is not None and row_unit != unit_price:
            continue
        if row_quantity == quantity or row_unit == unit_price:
            targets += 1
    return targets == 1


def _run_reason(
    run_dir: Path,
    compare_dir: Path,
    rows_by_source: dict[str, list[dict[str, Any]]],
) -> tuple[
    dict[str, str], Counter[str], Counter[str], Counter[str], Counter[str],
    set[str],
]:
    matcher = get_matcher()
    result: dict[str, str] = {}
    reasons: Counter[str] = Counter()
    current_synth: Counter[str] = Counter()
    relaxed: Counter[str] = Counter()
    learn_gate: Counter[str] = Counter()
    arithmetic_sources: set[str] = set()
    for source, targets in rows_by_source.items():
        snap_path = run_dir / "snapshots" / f"{source}.json"
        compare_path = compare_dir / f"{source}.json"
        if not snap_path.is_file() or not compare_path.is_file():
            for target in targets:
                key = target["key"]
                result[key] = "missing_input"
                reasons["missing_input"] += 1
            continue
        snap = _load(str(snap_path))
        compared = _load(str(compare_path))
        raw_lines = _deserialize_lines(snap.get("ocr_lines_raw")) or []
        texts = [_line_text(line) for line in raw_lines]
        compared_rows = (compared.get("table") or {}).get("rows") or []
        existing_names = [
            str(((row.get("cells") or {}).get("itemName") or {}).get("ext") or "")
            for row in compared_rows
        ]
        used_amounts = {
            re.sub(
                r"\D",
                "",
                str(((row.get("cells") or {}).get("amount") or {}).get("ext") or ""),
            )
            for row in compared_rows
        }
        used_amounts.discard("")
        path = str(compared.get("extractionPath") or "unknown")
        for target in targets:
            line, ratio, line_index = _best_line(str(target.get("gt") or ""), texts)
            if ratio < 0.90:
                reason = "no_single_line"
                current_reason = "no_name_line"
                relaxed_reason = "no_name_line"
            else:
                reason = rejection_reason(line)
                current_reason = synth_rejection_reason(
                    line,
                    line_index,
                    raw_lines,
                    existing_names,
                    used_amounts,
                    matcher,
                )
                relaxed_reason = relaxed_synth_reason(
                    line,
                    line_index,
                    raw_lines,
                    existing_names,
                    used_amounts,
                    matcher,
                )
            tagged = f"{path}:{reason}"
            result[target["key"]] = tagged
            reasons[tagged] += 1
            current_synth[f"{path}:{current_reason}"] += 1
            relaxed[f"{path}:{relaxed_reason}"] += 1
            if (
                current_reason in {"name_gate", "master_below_floor"}
                and _arithmetic_merge_possible(
                    line_index, raw_lines, compared_rows
                )
            ):
                arithmetic_sources.add(source)
            if current_reason == "name_gate" and line:
                counts = matcher._learn.get(str(line).strip()) or {}
                total = sum(counts.values())
                dominance = max(counts.values(), default=0) / total if total else 0.0
                if total:
                    learn_gate[f"{path}:exact_key"] += 1
                for minimum, required in ((3, 0.80), (5, 0.90), (10, 0.95)):
                    if total >= minimum and dominance >= required:
                        learn_gate[
                            f"{path}:count{minimum}_dom{int(required * 100)}"
                        ] += 1
    return (
        result, reasons, current_synth, relaxed, learn_gate, arithmetic_sources
    )


def analyze(cross: dict[str, Any], left_run: str, right_run: str) -> dict[str, Any]:
    targets = [
        row
        for row in cross.get("persistentParserDropRows") or []
        if row.get("leftPattern") == "drop" and row.get("rightPattern") == "drop"
    ]
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in targets:
        grouped[str(row["sourceFile"])].append(row)
    left_dir, right_dir = Path(left_run), Path(right_run)
    (
        left_map, left_counts, left_synth, left_relaxed, left_learn,
        left_arithmetic,
    ) = _run_reason(
        left_dir, left_dir / "replay_compare", grouped
    )
    (
        right_map, right_counts, right_synth, right_relaxed, right_learn,
        right_arithmetic,
    ) = _run_reason(
        right_dir, right_dir / "replay_compare", grouped
    )
    transitions = Counter(
        (left_map.get(row["key"], "missing"), right_map.get(row["key"], "missing"))
        for row in targets
    )
    return {
        "schemaVersion": "itemname-persistent-drop.v1",
        "rows": len(targets),
        "documents": len(grouped),
        "leftReasons": dict(left_counts.most_common()),
        "rightReasons": dict(right_counts.most_common()),
        "leftCurrentSynth": dict(left_synth.most_common()),
        "rightCurrentSynth": dict(right_synth.most_common()),
        "leftRelaxedSynth": dict(left_relaxed.most_common()),
        "rightRelaxedSynth": dict(right_relaxed.most_common()),
        "leftLearnGateUpperBound": dict(left_learn.most_common()),
        "rightLearnGateUpperBound": dict(right_learn.most_common()),
        "leftArithmeticCandidateDocuments": len(left_arithmetic),
        "rightArithmeticCandidateDocuments": len(right_arithmetic),
        "arithmeticCandidateSources": sorted(left_arithmetic | right_arithmetic),
        "reasonTransitions": {
            f"{left}->{right}": count
            for (left, right), count in transitions.most_common()
        },
    }


def render(result: dict[str, Any]) -> str:
    lines = [
        "# Persistent itemName drop analysis",
        "",
        f"- rows: **{result['rows']:,}**",
        f"- documents: **{result['documents']:,}**",
        f"- arithmetic candidate documents: **"
        f"{len(result['arithmeticCandidateSources']):,}** "
        f"(067 {result['leftArithmeticCandidateDocuments']:,}, "
        f"068 {result['rightArithmeticCandidateDocuments']:,})",
        "",
    ]
    for title, key in (
        ("067 rejection reason", "leftReasons"),
        ("068 rejection reason", "rightReasons"),
        ("067 current-synthesis gate", "leftCurrentSynth"),
        ("068 current-synthesis gate", "rightCurrentSynth"),
        ("067 relaxed-synthesis gate", "leftRelaxedSynth"),
        ("068 relaxed-synthesis gate", "rightRelaxedSynth"),
        ("067 LearnData name-gate upper bound", "leftLearnGateUpperBound"),
        ("068 LearnData name-gate upper bound", "rightLearnGateUpperBound"),
        ("067 → 068 transition", "reasonTransitions"),
    ):
        lines += [f"## {title}", "", "| reason | rows |", "|---|---:|"]
        for reason, count in result[key].items():
            lines.append(f"| {reason} | {count:,} |")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cross", required=True)
    ap.add_argument("--left-run", required=True)
    ap.add_argument("--right-run", required=True)
    ap.add_argument("--json-out", required=True)
    ap.add_argument("--md-out", required=True)
    ap.add_argument("--targets-out")
    args = ap.parse_args()
    result = analyze(_load(args.cross), args.left_run, args.right_run)
    os.makedirs(os.path.dirname(os.path.abspath(args.json_out)), exist_ok=True)
    with open(args.json_out, "w", encoding="utf-8") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    with open(args.md_out, "w", encoding="utf-8") as fh:
        fh.write(render(result))
    if args.targets_out:
        with open(args.targets_out, "w", encoding="utf-8") as fh:
            for source in result["arithmeticCandidateSources"]:
                fh.write(source + "\n")
    print(render(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
