"""Frozen-sample A/B for the production same-row amount helper (no replay)."""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

SERVER = Path(__file__).resolve().parents[1]
EVAL = SERVER / "eval"
RUN = EVAL / "runs" / "066_20260709_122046" / "thin"
OUT = SERVER / "tmp" / "verify_same_row_amount_recovery_066.result.json"
sys.path.insert(0, str(SERVER))
sys.path.insert(0, str(EVAL))

from build_manifest import build_manifest  # noqa: E402
from compare_table import compare_table  # noqa: E402
from extractors.invoice_statement import recover_postjoin_same_row_amounts  # noqa: E402
from gt_loader import load_gt_aggregate  # noqa: E402


def amount_cells(table):
    return {
        str(row.get("rowIndex")): (row.get("cells") or {}).get("amount", {})
        for row in table.get("rows") or [] if (row.get("cells") or {}).get("amount")
    }


def main():
    manifest = build_manifest("invoice_thin")
    sample_by_source = {item["sourceFile"]: item for item in manifest["samples"]}
    aggregate = load_gt_aggregate(str(EVAL / manifest["gtAggregate"]), profile="thin")
    result = {"basis": "066 thin frozen samples; production helper; no replay",
              "documents": 0, "docsChanged": 0, "cellsChanged": 0,
              "gain": 0, "regression": 0, "spuriousDelta": 0,
              "allTableGain": 0, "allTableRegression": 0}
    for path in sorted((RUN / "samples").glob("*.json")):
        source = path.name[:-5]
        meta = sample_by_source.get(source)
        if not meta:
            continue
        sample = json.loads(path.read_text(encoding="utf-8"))
        rows = (sample.get("documentFields") or {}).get("tableRows") or []
        gt_rows = aggregate[meta["gtKey"]]["tableRows"]
        before = compare_table(gt_rows, rows)
        after_rows, debug = recover_postjoin_same_row_amounts(copy.deepcopy(rows))
        result["documents"] += 1
        if not debug.get("applied"):
            continue
        after = compare_table(gt_rows, after_rows)
        b, a = amount_cells(before), amount_cells(after)
        keys = set(b) | set(a)
        result["docsChanged"] += 1
        result["cellsChanged"] += int(debug.get("filledCount") or 0)
        result["gain"] += sum(b.get(k, {}).get("status") != "match" and a.get(k, {}).get("status") == "match" for k in keys)
        result["regression"] += sum(b.get(k, {}).get("status") == "match" and a.get(k, {}).get("status") != "match" for k in keys)
        result["spuriousDelta"] += sum(bool(x.get("spurious")) for x in a.values()) - sum(bool(x.get("spurious")) for x in b.values())
        before_all = {
            (str(row.get("rowIndex")), field): cell
            for row in before.get("rows") or []
            for field, cell in (row.get("cells") or {}).items()
        }
        after_all = {
            (str(row.get("rowIndex")), field): cell
            for row in after.get("rows") or []
            for field, cell in (row.get("cells") or {}).items()
        }
        for key in set(before_all) | set(after_all):
            bs = before_all.get(key, {}).get("status")
            ass = after_all.get(key, {}).get("status")
            result["allTableGain"] += int(bs != "match" and ass == "match")
            result["allTableRegression"] += int(bs == "match" and ass != "match")
    result["net"] = result["gain"] - result["regression"]
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
