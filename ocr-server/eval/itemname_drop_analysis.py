"""Locate itemName parser-drop targets in frozen OCR lines and classify gates."""
from __future__ import annotations

import argparse
import glob
import json
import os
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


def _line_text(line: object) -> str:
    value = getattr(line, "text", None)
    if value is None and isinstance(line, dict):
        value = line.get("text")
    if value is None and isinstance(line, (list, tuple)) and len(line) >= 2:
        value = line[1]
    return str(value or "")


def _best_line(gt: str, lines: list[str]) -> tuple[str | None, float]:
    target = _collapse_alnum(gt)
    if len(target) < 2:
        return None, 0.0
    normalized = [_collapse_alnum(line) for line in lines]
    for index, value in enumerate(normalized):
        if target in value:
            return lines[index], 1.0
    best_ratio, best_index = 0.0, None
    for index, value in enumerate(normalized):
        ratio = SequenceMatcher(None, target, value).ratio()
        if ratio > best_ratio:
            best_ratio, best_index = ratio, index
    return (lines[best_index] if best_index is not None else None), best_ratio


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


def analyze(run: str) -> dict:
    run_dir = os.path.join(C.RUNS_DIR, run)
    compare_dir = os.path.join(run_dir, "replay_compare")
    classify_path = os.path.join(run_dir, "PARSER_DROP_CLASSIFY_replay_compare.json")
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
    for source, rows in grouped.items():
        snap_path = os.path.join(run_dir, "snapshots", source + ".json")
        if not os.path.isfile(snap_path):
            for _ in rows:
                counts["missing_snapshot"] += 1
            continue
        with open(snap_path, encoding="utf-8") as fh:
            snap = json.load(fh)
        lines = [
            _line_text(line)
            for line in (_deserialize_lines(snap.get("ocr_lines_raw")) or [])
        ]
        extraction_path = path_by_source.get(source, "unknown")
        for defect in rows:
            line, ratio = _best_line(str(defect.get("gtRaw") or ""), lines)
            if ratio < 0.90:
                reason = "no_single_line"
            else:
                reason = rejection_reason(line)
            key = f"{extraction_path}:{reason}"
            counts[key] += 1
            documents[key].add(source)
            sources[reason].add(source)
            if len(examples[key]) < 12:
                examples[key].append({
                    "sourceFile": source,
                    "location": defect.get("location"),
                    "gt": defect.get("gtRaw"),
                    "line": line,
                    "lineRatio": round(ratio, 4),
                })

    return {
        "run": run,
        "dropRows": len(defects),
        "dropDocuments": len(grouped),
        "counts": dict(counts),
        "documents": {key: len(value) for key, value in documents.items()},
        "sourcesByReason": {
            key: sorted(value) for key, value in sources.items()
        },
        "examples": dict(examples),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="067_20260720_175949")
    ap.add_argument("--json-out", default=None)
    ap.add_argument("--targets-out", default=None)
    args = ap.parse_args()
    result = analyze(args.run)
    print(json.dumps({
        "run": result["run"],
        "dropRows": result["dropRows"],
        "dropDocuments": result["dropDocuments"],
        "counts": result["counts"],
        "documents": result["documents"],
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
