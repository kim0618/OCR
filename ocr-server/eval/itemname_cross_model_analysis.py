"""Find item-name failures that persist across two OCR-model replays.

The classifier reports already decide whether a failed GT cell was present in
OCR and whether the parser dropped, misplaced, or replaced it.  This tool joins
those reports by immutable ``sourceFile + GT row location`` so model-specific
recognition failures do not get mistaken for parser work.

Read-only inputs; outputs JSON/Markdown plus an optional source list suitable
for a partial replay.
"""
from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from typing import Any


def _load(path: str) -> dict[str, Any]:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _item_parser_drops(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for defect in report.get("defects") or []:
        if (
            defect.get("column") == "itemName"
            and defect.get("class") == "parser_drop"
            and str(defect.get("location") or "").startswith("row")
        ):
            key = f"{defect.get('src')}#{defect.get('location')}"
            out[key] = defect
    return out


def _protected(report: dict[str, Any], name: str) -> set[str]:
    cross = report.get("rawMasterCross") or {}
    rows = cross.get("protectedRows") or {}
    return set(rows.get(name) or [])


def analyze(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    a = _item_parser_drops(left)
    b = _item_parser_drops(right)
    common_keys = sorted(set(a) & set(b))
    pattern_pairs: Counter[tuple[str, str]] = Counter()
    stable_patterns: Counter[str] = Counter()
    rows: list[dict[str, Any]] = []
    for key in common_keys:
        da, db = a[key], b[key]
        pa = str(da.get("pattern") or "unknown")
        pb = str(db.get("pattern") or "unknown")
        pattern_pairs[(pa, pb)] += 1
        if pa == pb:
            stable_patterns[pa] += 1
        rows.append({
            "key": key,
            "sourceFile": da.get("src"),
            "location": da.get("location"),
            "leftPattern": pa,
            "rightPattern": pb,
            "leftStatus": da.get("status"),
            "rightStatus": db.get("status"),
            "gt": db.get("gtRaw") or da.get("gtRaw"),
            "gtNorm": db.get("gtNorm") or da.get("gtNorm"),
            "leftExt": da.get("extNorm"),
            "rightExt": db.get("extNorm"),
            "leftOcrHow": da.get("ocrHow"),
            "rightOcrHow": db.get("ocrHow"),
        })

    left_master_wrong = _protected(left, "rawCorrect_masterWrong")
    right_master_wrong = _protected(right, "rawCorrect_masterWrong")
    common_master_wrong = sorted(left_master_wrong & right_master_wrong)
    sources = sorted({
        row["sourceFile"] for row in rows if row.get("sourceFile")
    } | {
        key.rsplit("#", 1)[0] for key in common_master_wrong
    })
    return {
        "schemaVersion": "itemname-cross-model.v1",
        "leftRun": left.get("runDir"),
        "rightRun": right.get("runDir"),
        "summary": {
            "leftParserDropRows": len(a),
            "rightParserDropRows": len(b),
            "commonParserDropRows": len(common_keys),
            "commonParserDropDocuments": len({
                row["sourceFile"] for row in rows if row.get("sourceFile")
            }),
            "leftRawCorrectMasterWrong": len(left_master_wrong),
            "rightRawCorrectMasterWrong": len(right_master_wrong),
            "commonRawCorrectMasterWrong": len(common_master_wrong),
            "targetDocuments": len(sources),
        },
        "stablePatterns": dict(stable_patterns),
        "patternTransitions": {
            f"{left_pattern}->{right_pattern}": count
            for (left_pattern, right_pattern), count
            in pattern_pairs.most_common()
        },
        "commonRawCorrectMasterWrong": common_master_wrong,
        "targetSources": sources,
        "persistentParserDropRows": rows,
    }


def _render_md(result: dict[str, Any]) -> str:
    s = result["summary"]
    lines = [
        "# Cross-model itemName parser analysis",
        "",
        f"- left parser-drop: **{s['leftParserDropRows']:,} rows**",
        f"- right parser-drop: **{s['rightParserDropRows']:,} rows**",
        f"- persistent parser-drop: **{s['commonParserDropRows']:,} rows / "
        f"{s['commonParserDropDocuments']:,} documents**",
        f"- persistent raw-correct → Master-wrong: "
        f"**{s['commonRawCorrectMasterWrong']:,} rows**",
        "",
        "## Stable parser patterns",
        "",
        "| pattern | rows |",
        "|---|---:|",
    ]
    for pattern, count in sorted(
        result["stablePatterns"].items(), key=lambda item: item[1], reverse=True
    ):
        lines.append(f"| {pattern} | {count:,} |")
    lines += [
        "",
        "## Pattern transitions",
        "",
        "| left → right | rows |",
        "|---|---:|",
    ]
    for transition, count in result["patternTransitions"].items():
        lines.append(f"| {transition} | {count:,} |")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--left", required=True)
    ap.add_argument("--right", required=True)
    ap.add_argument("--json-out", required=True)
    ap.add_argument("--md-out", required=True)
    ap.add_argument("--targets-out", default=None)
    args = ap.parse_args()
    result = analyze(_load(args.left), _load(args.right))
    os.makedirs(os.path.dirname(os.path.abspath(args.json_out)), exist_ok=True)
    with open(args.json_out, "w", encoding="utf-8") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    with open(args.md_out, "w", encoding="utf-8") as fh:
        fh.write(_render_md(result))
    if args.targets_out:
        with open(args.targets_out, "w", encoding="utf-8") as fh:
            for source in result["targetSources"]:
                fh.write(source + "\n")
    print(json.dumps(result["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
