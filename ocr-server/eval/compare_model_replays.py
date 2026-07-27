"""Render a same-scope metric table across two or more replay directories."""
from __future__ import annotations

import argparse
import json
import os
from collections import Counter


CELL_KEYS = [
    "itemName", "itemNameMaster", "itemNameLearnA", "itemNameLearnB",
    "itemCode", "itemCodeLearnA", "itemCodeLearnB",
    "spec", "quantity", "unitPrice", "amount", "expiryDate", "manufacturingNo",
]


def _files(path: str) -> set[str]:
    return {name for name in os.listdir(path) if name.endswith(".json")}


def aggregate(path: str, scope: set[str]) -> dict:
    field = Counter()
    cell = Counter()
    per_cell = {key: Counter() for key in CELL_KEYS}
    for filename in sorted(scope):
        with open(os.path.join(path, filename), encoding="utf-8") as fh:
            doc = json.load(fh)
        fc = (doc.get("fields") or {}).get("counts") or {}
        field.update({
            "match": int(fc.get("match") or 0),
            "scored": int(fc.get("scored") or 0),
        })
        table = doc.get("table") or {}
        tc = table.get("cellCounts") or {}
        cell.update({
            "match": int(tc.get("match") or 0),
            "scored": int(tc.get("scored") or 0),
        })
        for row in table.get("rows") or []:
            for key, verdict in (row.get("cells") or {}).items():
                status = verdict.get("status")
                if status not in {"match", "mismatch", "ext_missing"}:
                    continue
                if key in per_cell:
                    per_cell[key]["scored"] += 1
                    per_cell[key]["match"] += int(status == "match")
    return {"field": field, "cell": cell, "perCell": per_cell}


def _pct(counter: Counter) -> str:
    scored = counter["scored"]
    return f"{100 * counter['match'] / scored:.3f}%" if scored else "-"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--run", action="append", required=True,
        help="repeat as LABEL=compare_dir",
    )
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    runs = []
    for value in args.run:
        if "=" not in value:
            ap.error("--run must be LABEL=compare_dir")
        label, path = value.split("=", 1)
        runs.append((label, path))
    scopes = [_files(path) for _, path in runs]
    common = set.intersection(*scopes)
    metrics = {label: aggregate(path, common) for label, path in runs}
    rows = [
        ("FIELD TOTAL", lambda m: m["field"]),
        ("CELL TOTAL", lambda m: m["cell"]),
    ]
    rows.extend((key, lambda m, key=key: m["perCell"][key]) for key in CELL_KEYS)
    lines = [
        "# OCR model replay comparison",
        "",
        f"Common scope: **{len(common):,} documents**",
        "",
        "| metric | " + " | ".join(label for label, _ in runs) + " |",
        "|---|" + "|".join("---:" for _ in runs) + "|",
    ]
    json_rows = {}
    for name, getter in rows:
        values = []
        json_rows[name] = {}
        for label, _ in runs:
            counter = getter(metrics[label])
            values.append(_pct(counter))
            json_rows[name][label] = {
                "match": counter["match"],
                "scored": counter["scored"],
                "accuracyPct": (
                    100 * counter["match"] / counter["scored"]
                    if counter["scored"] else None
                ),
            }
        lines.append(f"| {name} | " + " | ".join(values) + " |")
    lines.append("")
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    json_out = os.path.splitext(args.out)[0] + ".json"
    with open(json_out, "w", encoding="utf-8") as fh:
        json.dump({
            "commonSources": len(common),
            "excludedByRun": {
                label: len(scope - common)
                for (label, _), scope in zip(runs, scopes)
            },
            "metrics": json_rows,
        }, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    print(f"{args.out} ({len(common):,} common documents)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
