"""Read completed 066 replay sidecars and compare them to frozen samples."""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path

SERVER = Path(__file__).resolve().parents[1]
EVAL = SERVER / "eval"
RUN = EVAL / "runs" / "066_20260709_122046" / "thin"
OUT = SERVER / "tmp" / "analyze_completed_replay_amount_066.result.json"
sys.path.insert(0, str(EVAL))

from build_manifest import build_manifest  # noqa: E402
from compare_table import compare_table  # noqa: E402
from gt_loader import load_gt_aggregate  # noqa: E402


def cells(table):
    result = {}
    for row in table.get("rows") or []:
        row_key = str(row.get("rowIndex"))
        for field, cell in (row.get("cells") or {}).items():
            result[(row_key, field)] = cell
    return result


def main():
    manifest = build_manifest("invoice_thin")
    by_source = {item["sourceFile"]: item for item in manifest["samples"]}
    aggregate = load_gt_aggregate(str(EVAL / manifest["gtAggregate"]), profile="thin")
    result = {
        "basis": "completed 066 thin replay_compare vs frozen samples",
        "documents": 0, "missingBaseline": 0,
        "amount": {"before": Counter(), "after": Counter(), "gain": 0, "regression": 0,
                   "spuriousBefore": 0, "spuriousAfter": 0, "changedCells": 0, "changedDocs": 0},
        "allTableCells": {"gain": 0, "regression": 0, "spuriousDelta": 0},
        "allTableByField": {},
        "amountChangedDocsTableCells": {"gain": 0, "regression": 0, "byField": {}},
        "rowCountChangedDocs": 0, "paths": Counter(), "amountRegressionDocs": [],
        "tableRegressionDocs": [],
        "rowCountGuardCandidates": {
            str(limit): {"docsChanged": 0, "amountChangedCells": 0, "amountGain": 0,
                         "tableGain": 0, "tableRegression": 0}
            for limit in (3, 4, 5, 6, 7, 8, 10, 12, 13, 14, 20)
        },
        "semanticGuardCandidates": {
            name: {"docsChanged": 0, "amountChangedCells": 0, "amountGain": 0,
                   "tableGain": 0, "tableRegression": 0}
            for name in ("no_disagreement", "max13_no_disagreement", "max12_no_disagreement")
        },
    }
    for replay_path in sorted((RUN / "replay_compare").glob("*.json")):
        source = replay_path.name[:-5]
        sample_path = RUN / "samples" / replay_path.name
        meta = by_source.get(source)
        if not sample_path.exists() or not meta:
            result["missingBaseline"] += 1
            continue
        sample = json.loads(sample_path.read_text(encoding="utf-8"))
        sample_rows = (sample.get("documentFields") or {}).get("tableRows") or []
        replay = json.loads(replay_path.read_text(encoding="utf-8"))
        before = compare_table(
            aggregate[meta["gtKey"]]["tableRows"],
            sample_rows,
        )
        after = replay.get("table") or {}
        b_cells, a_cells = cells(before), cells(after)
        keys = set(b_cells) | set(a_cells)
        doc_amount_changed = False
        doc_amount_regression = 0
        doc_amount_changed_cells = 0
        doc_amount_gain = 0
        doc_deltas = []
        for key in keys:
            b, a = b_cells.get(key, {}), a_cells.get(key, {})
            bs, ass = b.get("status"), a.get("status")
            if bs != "match" and ass == "match":
                result["allTableCells"]["gain"] += 1
                doc_deltas.append((key[1], "gain"))
            if bs == "match" and ass != "match":
                result["allTableCells"]["regression"] += 1
                doc_deltas.append((key[1], "regression"))
            result["allTableCells"]["spuriousDelta"] += int(bool(a.get("spurious"))) - int(bool(b.get("spurious")))
            if key[1] != "amount":
                continue
            result["amount"]["before"][str(bs)] += 1
            result["amount"]["after"][str(ass)] += 1
            result["amount"]["spuriousBefore"] += int(bool(b.get("spurious")))
            result["amount"]["spuriousAfter"] += int(bool(a.get("spurious")))
            if str(b.get("extNorm") or "") != str(a.get("extNorm") or ""):
                result["amount"]["changedCells"] += 1
                doc_amount_changed_cells += 1
                doc_amount_changed = True
            if bs != "match" and ass == "match":
                result["amount"]["gain"] += 1
                doc_amount_gain += 1
            if bs == "match" and ass != "match":
                result["amount"]["regression"] += 1
                doc_amount_regression += 1
        if doc_amount_changed:
            result["amount"]["changedDocs"] += 1
            scoped = result["amountChangedDocsTableCells"]
            for field, direction in doc_deltas:
                scoped[direction] += 1
                field_counts = scoped["byField"].setdefault(field, {"gain": 0, "regression": 0})
                field_counts[direction] += 1
            regression_fields = Counter(field for field, direction in doc_deltas if direction == "regression")
            if regression_fields:
                names = [str(row.get("itemName") or "").strip().lower() for row in sample_rows]
                nonempty = [name for name in names if name]
                max_similarity = max(
                    (SequenceMatcher(None, left, right).ratio()
                     for i, left in enumerate(nonempty) for right in nonempty[i + 1:]),
                    default=0.0,
                )
                result["tableRegressionDocs"].append({
                    "sourceFile": source,
                    "rowCount": len(sample_rows),
                    "emptyItemNames": len(names) - len(nonempty),
                    "duplicateItemNames": len(nonempty) - len(set(nonempty)),
                    "maxItemNameSimilarity": round(max_similarity, 4),
                    "gain": sum(1 for _, direction in doc_deltas if direction == "gain"),
                    "regression": sum(regression_fields.values()),
                    "regressionFields": dict(regression_fields),
                })
            for raw_limit, candidate in result["rowCountGuardCandidates"].items():
                if len(sample_rows) > int(raw_limit):
                    continue
                candidate["docsChanged"] += 1
                candidate["amountChangedCells"] += doc_amount_changed_cells
                candidate["amountGain"] += doc_amount_gain
                candidate["tableGain"] += sum(1 for _, direction in doc_deltas if direction == "gain")
                candidate["tableRegression"] += sum(1 for _, direction in doc_deltas if direction == "regression")
            supply_disagreement = False
            for row in sample_rows:
                amount_digits = re.sub(r"\D", "", str(row.get("amount") or "")).lstrip("0")
                supply_tokens = re.findall(r"\d[\d,.]*", str(row.get("supplyAmount") or ""))
                supply_digits = re.sub(r"\D", "", supply_tokens[-1]).lstrip("0") if supply_tokens else ""
                if amount_digits and supply_digits and amount_digits != supply_digits:
                    supply_disagreement = True
                    break
            semantic_allowed = {
                "no_disagreement": not supply_disagreement,
                "max13_no_disagreement": len(sample_rows) <= 13 and not supply_disagreement,
                "max12_no_disagreement": len(sample_rows) <= 12 and not supply_disagreement,
            }
            for name, allowed in semantic_allowed.items():
                if not allowed:
                    continue
                candidate = result["semanticGuardCandidates"][name]
                candidate["docsChanged"] += 1
                candidate["amountChangedCells"] += doc_amount_changed_cells
                candidate["amountGain"] += doc_amount_gain
                candidate["tableGain"] += sum(1 for _, direction in doc_deltas if direction == "gain")
                candidate["tableRegression"] += sum(1 for _, direction in doc_deltas if direction == "regression")
        if doc_amount_regression:
            result["amountRegressionDocs"].append({"sourceFile": source, "count": doc_amount_regression})
        if before.get("rowCountExt") != after.get("rowCountExt"):
            result["rowCountChangedDocs"] += 1
        result["paths"][str(replay.get("extractionPath") or "unknown")] += 1
        result["documents"] += 1
        for field, direction in doc_deltas:
            field_counts = result["allTableByField"].setdefault(field, {"gain": 0, "regression": 0})
            field_counts[direction] += 1
    result["amount"]["before"] = dict(result["amount"]["before"])
    result["amount"]["after"] = dict(result["amount"]["after"])
    result["amount"]["spuriousDelta"] = result["amount"]["spuriousAfter"] - result["amount"]["spuriousBefore"]
    result["amount"]["net"] = result["amount"]["gain"] - result["amount"]["regression"]
    result["paths"] = dict(result["paths"])
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
