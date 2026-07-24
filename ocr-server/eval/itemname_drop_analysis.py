"""Locate itemName parser-drop targets in frozen OCR lines and classify gates."""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
from collections import Counter, defaultdict
from difflib import SequenceMatcher

HERE = os.path.dirname(os.path.abspath(__file__))
SERVER = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, SERVER)

import contract as C  # noqa: E402
from parser_drop_classify import _collapse_alnum  # noqa: E402
from replay_free import _deserialize_lines  # noqa: E402
from extractors import invoice_statement_free as F  # noqa: E402
from extractors.master_match import clean_query_name, get_matcher  # noqa: E402


def _line_text(line: object) -> str:
    value = getattr(line, "text", None)
    if value is None and isinstance(line, dict):
        value = line.get("text")
    if value is None and isinstance(line, (list, tuple)) and len(line) >= 2:
        value = line[1]
    return str(value or "")


def _best_line(gt: str, lines: list[str]) -> tuple[str | None, float, int | None]:
    target = _collapse_alnum(gt)
    if len(target) < 2:
        return None, 0.0, None
    normalized = [_collapse_alnum(line) for line in lines]
    for index, value in enumerate(normalized):
        if target in value:
            return lines[index], 1.0, index
    best_ratio, best_index = 0.0, None
    for index, value in enumerate(normalized):
        ratio = SequenceMatcher(None, target, value).ratio()
        if ratio > best_ratio:
            best_ratio, best_index = ratio, index
    return (
        lines[best_index] if best_index is not None else None,
        best_ratio,
        best_index,
    )


def _center_y(line: object) -> tuple[float, float] | None:
    try:
        points = line[0] if isinstance(line, (list, tuple)) else line.get("points")
        ys = [float(point[1]) for point in points]
    except Exception:
        return None
    if not ys:
        return None
    return sum(ys) / len(ys), max(max(ys) - min(ys), 1.0)


def synth_rejection_reason(
    line: str | None,
    line_index: int | None,
    raw_lines: list,
    existing_names: list[str],
    used_amounts: set[str],
    matcher: object,
) -> str:
    if not line or line_index is None:
        return "no_name_line"
    if not F._adopt_name_line_ok(line):
        return "name_gate"
    normalized = _collapse_alnum(line)
    existing = [_collapse_alnum(value) for value in existing_names if value]
    if normalized in existing:
        return "exact_duplicate"
    if any(SequenceMatcher(None, normalized, value).ratio() >= 0.8
           for value in existing if value):
        return "fuzzy_duplicate"
    try:
        candidates = matcher.top_candidates(clean_query_name(line), 1)
    except Exception:
        candidates = []
    if not candidates or candidates[0][0] < F._SYNTH_SIM_FLOOR:
        return "master_below_floor"
    center = _center_y(raw_lines[line_index])
    if center is None:
        return "no_geometry"
    cy, height = center
    band = max(height * 1.2, 14.0)
    for index, raw_line in enumerate(raw_lines):
        if index == line_index:
            continue
        other = _center_y(raw_line)
        if other is None or abs(other[0] - cy) > band:
            continue
        for value in F._SYNTH_MONEY_RE.findall(_line_text(raw_line)):
            digits = re.sub(r"\D", "", value)
            if len(digits) >= 4 and digits not in used_amounts:
                return "eligible"
    return "no_unused_same_band_money"


def relaxed_synth_reason(
    line: str | None,
    line_index: int | None,
    raw_lines: list,
    existing_names: list[str],
    used_amounts: set[str],
    matcher: object,
) -> str:
    """Probe a master-first alternative to the hardcoded drug-suffix gate."""
    if not line or line_index is None:
        return "no_name_line"
    text = F._normalize_text(line)
    if F._is_summary_or_header_line(text) or F._metadata_negative_reason(text):
        return "metadata_negative"
    if not (re.search(r"[가-힣]{2,}", text) or re.search(r"[A-Za-z]{4,}", text)):
        return "no_name_signal"
    normalized = _collapse_alnum(text)
    existing = [_collapse_alnum(value) for value in existing_names if value]
    if normalized in existing:
        return "exact_duplicate"
    if any(SequenceMatcher(None, normalized, value).ratio() >= 0.8
           for value in existing if value):
        return "fuzzy_duplicate"
    try:
        candidates = matcher.top_candidates(clean_query_name(text), 1)
    except Exception:
        candidates = []
    if not candidates or candidates[0][0] < 0.65:
        return "master_below_065"
    center = _center_y(raw_lines[line_index])
    if center is None:
        return "no_geometry"
    cy, height = center
    band = max(height * 1.2, 14.0)
    for index, raw_line in enumerate(raw_lines):
        if index == line_index:
            continue
        other = _center_y(raw_line)
        if other is None or abs(other[0] - cy) > band:
            continue
        for value in F._SYNTH_MONEY_RE.findall(_line_text(raw_line)):
            digits = re.sub(r"\D", "", value)
            if len(digits) >= 4 and digits not in used_amounts:
                return "eligible"
    return "no_unused_same_band_money"


def rejection_reason(line: str | None) -> str:
    if not line:
        return "no_single_line"
    text = F._normalize_comma_space_money_text(line)
    if F._is_summary_or_header_line(text):
        return "summary_header_gate"
    text = F._strip_leading_row_index(text)
    tokens = F._merge_comma_space_money_tokens(text.split())
    if len(tokens) < 3:
        return "tokens_lt_3"
    numerics = [
        (index, token)
        for index, token in enumerate(tokens)
        if F._is_number_token(token)
    ]
    if len(numerics) < 2:
        return "numerics_lt_2"
    if numerics[0][0] == 0:
        return "leading_numeric_no_label"
    if F._parse_table_row_candidate(text, 1) is None:
        return "candidate_other_reject"
    return "candidate_accepted_later_lost"


def analyze(run: str, compare_dir_name: str = "replay_compare") -> dict:
    run_dir = os.path.join(C.RUNS_DIR, run)
    compare_dir = os.path.join(run_dir, compare_dir_name)
    classify_path = os.path.join(
        run_dir, f"PARSER_DROP_CLASSIFY_{compare_dir_name}.json"
    )
    with open(classify_path, encoding="utf-8") as fh:
        classification = json.load(fh)
    defects = [
        row for row in classification.get("defects") or []
        if row.get("column") == "itemName"
        and row.get("class") == "parser_drop"
        and row.get("pattern") == "drop"
    ]

    path_by_source: dict[str, str] = {}
    for path in glob.glob(os.path.join(compare_dir, "*.json")):
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
        path_by_source[doc.get("sourceFile") or os.path.basename(path)[:-5]] = (
            doc.get("extractionPath") or "unknown"
        )

    grouped: dict[str, list[dict]] = defaultdict(list)
    for defect in defects:
        grouped[defect["src"]].append(defect)

    counts = Counter()
    documents: dict[str, set[str]] = defaultdict(set)
    sources: dict[str, set[str]] = defaultdict(set)
    examples: dict[str, list[dict]] = defaultdict(list)
    synth_counts = Counter()
    relaxed_synth_counts = Counter()
    relaxed_sources: dict[str, set[str]] = defaultdict(set)
    matcher = get_matcher()
    for source, rows in grouped.items():
        snap_path = os.path.join(run_dir, "snapshots", source + ".json")
        if not os.path.isfile(snap_path):
            for _ in rows:
                counts["missing_snapshot"] += 1
            continue
        with open(snap_path, encoding="utf-8") as fh:
            snap = json.load(fh)
        raw_lines = _deserialize_lines(snap.get("ocr_lines_raw")) or []
        lines = [
            _line_text(line)
            for line in raw_lines
        ]
        extraction_path = path_by_source.get(source, "unknown")
        with open(os.path.join(compare_dir, source + ".json"), encoding="utf-8") as fh:
            compared = json.load(fh)
        compared_rows = compared.get("table", {}).get("rows") or []
        existing_names = [
            str((row.get("cells") or {}).get("itemName", {}).get("ext") or "")
            for row in compared_rows
        ]
        used_amounts = {
            re.sub(
                r"\D", "",
                str((row.get("cells") or {}).get("amount", {}).get("ext") or ""),
            )
            for row in compared_rows
        }
        used_amounts.discard("")
        for defect in rows:
            line, ratio, line_index = _best_line(
                str(defect.get("gtRaw") or ""), lines
            )
            if ratio < 0.90:
                reason = "no_single_line"
            else:
                reason = rejection_reason(line)
            key = f"{extraction_path}:{reason}"
            counts[key] += 1
            synth_reason = synth_rejection_reason(
                line, line_index, raw_lines, existing_names, used_amounts, matcher
            )
            synth_counts[f"{extraction_path}:{synth_reason}"] += 1
            relaxed_reason = relaxed_synth_reason(
                line, line_index, raw_lines, existing_names, used_amounts, matcher
            )
            relaxed_synth_counts[f"{extraction_path}:{relaxed_reason}"] += 1
            relaxed_sources[relaxed_reason].add(source)
            documents[key].add(source)
            sources[reason].add(source)
            if len(examples[key]) < 12:
                examples[key].append({
                    "sourceFile": source,
                    "location": defect.get("location"),
                    "gt": defect.get("gtRaw"),
                    "line": line,
                    "lineRatio": round(ratio, 4),
                    "synthReason": synth_reason,
                    "relaxedSynthReason": relaxed_reason,
                })

    return {
        "run": run,
        "compareDir": compare_dir_name,
        "dropRows": len(defects),
        "dropDocuments": len(grouped),
        "counts": dict(counts),
        "documents": {key: len(value) for key, value in documents.items()},
        "synthCounts": dict(synth_counts),
        "relaxedSynthCounts": dict(relaxed_synth_counts),
        "relaxedSources": {
            key: sorted(value) for key, value in relaxed_sources.items()
        },
        "sourcesByReason": {
            key: sorted(value) for key, value in sources.items()
        },
        "examples": dict(examples),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="067_20260720_175949")
    ap.add_argument("--compare-dir", default="replay_compare")
    ap.add_argument("--json-out", default=None)
    ap.add_argument("--targets-out", default=None)
    ap.add_argument("--relaxed-targets-out", default=None)
    args = ap.parse_args()
    result = analyze(args.run, args.compare_dir)
    print(json.dumps({
        "run": result["run"],
        "dropRows": result["dropRows"],
        "dropDocuments": result["dropDocuments"],
        "counts": result["counts"],
        "documents": result["documents"],
        "synthCounts": result["synthCounts"],
        "relaxedSynthCounts": result["relaxedSynthCounts"],
    }, ensure_ascii=False, indent=2))
    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as fh:
            json.dump(result, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
    if args.targets_out:
        sources = sorted({
            source
            for values in result["sourcesByReason"].values()
            for source in values
        })
        with open(args.targets_out, "w", encoding="utf-8") as fh:
            fh.write("\n".join(sources) + ("\n" if sources else ""))
    if args.relaxed_targets_out:
        sources = result["relaxedSources"].get("eligible") or []
        with open(args.relaxed_targets_out, "w", encoding="utf-8") as fh:
            fh.write("\n".join(sources) + ("\n" if sources else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
