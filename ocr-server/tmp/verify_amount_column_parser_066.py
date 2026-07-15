"""Full 066 replay verification for the amount-column parser rule."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path


SERVER = Path(__file__).resolve().parents[1]
EVAL = SERVER / "eval"
RUN = EVAL / "runs" / "066_20260709_122046" / "thin"
sys.path.insert(0, str(SERVER))
sys.path.insert(0, str(EVAL))

from build_manifest import build_manifest  # noqa: E402
from compare_table import compare_table  # noqa: E402
from gt_loader import load_gt_aggregate  # noqa: E402
from replay_compare import replay_dispatch  # noqa: E402
from extractors.invoice_statement import _group_rows, _line_from_raw  # noqa: E402
from amount_column_probe_066 import apply_candidate  # noqa: E402


def has_required_amount_header(raw: list) -> bool:
    lines = [line for item in raw if (line := _line_from_raw(item))]
    if not lines:
        return False
    for group in _group_rows(lines, tolerance_factor=0.55):
        text = re.sub(
            r"\s+",
            "",
            " ".join(str(line.text or "") for line in sorted(group, key=lambda item: item.x)),
        )
        if "\uae08\uc561" in text and ("\uc218\ub7c9" in text or "\ub2e8\uac00" in text):
            return True
    return False


def amount_statuses(table: dict) -> tuple[dict[str, str], int]:
    statuses: dict[str, str] = {}
    ext_only_filled = 0
    ext_only = {str(value) for value in table.get("extOnlyRowIdx") or []}
    for row in table.get("rows") or []:
        key = str(row.get("rowIndex"))
        amount = (row.get("cells") or {}).get("amount") or {}
        statuses[key] = str(amount.get("status") or "")
        if key in ext_only and str(amount.get("ext") or "").strip():
            ext_only_filled += 1
    return statuses, ext_only_filled


def keyed(rows: list[dict]) -> dict[str, dict]:
    return {str(row.get("rowIndex")): row for row in rows}


def main() -> None:
    manifest = build_manifest("invoice_thin")
    samples = {sample["sourceFile"]: sample for sample in manifest["samples"]}
    gt_all = load_gt_aggregate(str(EVAL / manifest["gtAggregate"]), profile="thin")
    snapshots = sorted((RUN / "snapshots").glob("*.json"))
    result = {
        "snapshotCount": len(snapshots),
        "headerCandidateDocs": 0,
        "activeDocs": 0,
        "effectiveAmountChanges": 0,
        "gain": 0,
        "regression": 0,
        "spuriousDelta": 0,
        "rowCountIncreaseDocs": 0,
        "quantityChanges": 0,
        "unitPriceChanges": 0,
        "docs": [],
    }
    for number, snapshot_path in enumerate(snapshots, 1):
        source = snapshot_path.name[:-5]
        sample = samples.get(source)
        sample_path = RUN / "samples" / snapshot_path.name
        if not sample or not sample_path.exists():
            continue
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
        if not has_required_amount_header(snapshot.get("ocr_lines_raw") or []):
            continue
        result["headerCandidateDocs"] += 1
        baseline, route = replay_dispatch(snapshot)
        before_rows = baseline.get("tableRows") or []
        applied = apply_candidate(snapshot.get("ocr_lines_raw") or [], before_rows)
        if applied:
            after_rows, recovery = applied
            before_by_id = keyed(before_rows)
            after_by_id = keyed(after_rows)
            effective = sum(
                str(after_by_id[key].get("amount") or "").strip()
                != str(before_by_id.get(key, {}).get("amount") or "").strip()
                for key in after_by_id
            )
            quantity_changes = sum(
                str(after_by_id[key].get("quantity") or "").strip()
                != str(before_by_id.get(key, {}).get("quantity") or "").strip()
                for key in after_by_id
            )
            unit_price_changes = sum(
                str(after_by_id[key].get("unitPrice") or "").strip()
                != str(before_by_id.get(key, {}).get("unitPrice") or "").strip()
                for key in after_by_id
            )
            gt = gt_all[sample["gtKey"]]
            before_cmp = compare_table(gt["tableRows"], before_rows)
            after_cmp = compare_table(gt["tableRows"], after_rows)
            before_status, before_spurious = amount_statuses(before_cmp)
            after_status, after_spurious = amount_statuses(after_cmp)
            keys = set(before_status) | set(after_status)
            gain = sum(before_status.get(key) != "match" and after_status.get(key) == "match" for key in keys)
            regression = sum(before_status.get(key) == "match" and after_status.get(key) != "match" for key in keys)
            row_count_delta = len(after_rows) - len(before_rows)
            result["activeDocs"] += 1
            result["effectiveAmountChanges"] += effective
            result["gain"] += gain
            result["regression"] += regression
            result["spuriousDelta"] += after_spurious - before_spurious
            result["rowCountIncreaseDocs"] += int(row_count_delta > 0)
            result["quantityChanges"] += quantity_changes
            result["unitPriceChanges"] += unit_price_changes
            result["docs"].append({
                "sourceFile": source,
                "route": route,
                "filledByRule": len(recovery.get("changed") or []),
                "effectiveAmountChanges": effective,
                "gain": gain,
                "regression": regression,
                "spuriousDelta": after_spurious - before_spurious,
                "rowCountDelta": row_count_delta,
                "quantityChanges": quantity_changes,
                "unitPriceChanges": unit_price_changes,
            })
        if result["headerCandidateDocs"] % 100 == 0:
            print(
                f"progress snapshots={number}/{len(snapshots)} "
                f"headerCandidates={result['headerCandidateDocs']} active={result['activeDocs']}",
                flush=True,
            )
    output = SERVER / "tmp" / "verify_amount_column_parser_066.result.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
