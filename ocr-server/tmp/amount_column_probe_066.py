"""Read-only probe for a conservative fallback amount-column recovery rule.

The probe replays frozen OCR snapshots, applies the candidate to an in-memory
copy, and compares before/after table results.  It never edits parser output.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import re
import statistics
import sys
from pathlib import Path


SERVER = Path(__file__).resolve().parents[1]
EVAL = SERVER / "eval"
sys.path.insert(0, str(SERVER))
sys.path.insert(0, str(EVAL))

from build_manifest import build_manifest  # noqa: E402
from compare_table import compare_table  # noqa: E402
from gt_loader import load_gt, load_gt_aggregate  # noqa: E402
from replay_compare import replay_dispatch  # noqa: E402
from extractors.invoice_statement import _group_rows, _line_from_raw  # noqa: E402


MONEY_RE = re.compile(r"^\d{1,3}(?:[,.]\d{3})+$")
DIGIT_RE = re.compile(r"\d")
COMPACT_RE = re.compile(r"\s+")
AMOUNT = "\uae08\uc561"
QUANTITY = "\uc218\ub7c9"
UNIT_PRICE = "\ub2e8\uac00"
FOOTER_RE = re.compile(
    "|".join(
        (
            "\ud569\\s*\uacc4",          # total
            "\ucd1d\\s*\uacc4",          # grand total
            "\uacf5\\s*\uae09\\s*\uac00\\s*\uc561",  # supply amount
            "\ubd80\\s*\uac00\\s*\uc138",  # VAT
            "\uccad\\s*\uad6c\\s*\uae08\\s*\uc561",  # billed amount
            "\uc21c\\s*\ub9e4\\s*\ucd9c\\s*\uc561",  # net sales
            "\uc5d0\\s*\ub204\\s*\ub9ac",  # discount
            "VAT\\s*\ud3ec\ud568",        # VAT included notice
        )
    ),
    re.I,
)
SUMMARY_ROW_RE = re.compile(
    "|".join(
        (
            "(?:\uacf5|\uad81)\\s*\uae09\\s*\uac00",  # supply price/amount + OCR variant
            "\ubd80\\s*\uac00\\s*\uc138",  # VAT
            "\ud569\\s*\uacc4",              # total
            "\ucd1d\\s*\uacc4",              # grand total
            "\uc5d0\\s*\ub204\\s*\ub9ac",  # discount
            "\uc21c\\s*\ub9e4\\s*\ucd9c",  # net sales
        )
    ),
    re.I,
)


def compact(value: object) -> str:
    return COMPACT_RE.sub("", str(value or "")).strip()


def grouped_text(row: list) -> str:
    return " ".join(str(line.text or "").strip() for line in sorted(row, key=lambda x: x.x))


def amount_header(row: list) -> tuple[float, float] | None:
    """Return (right edge, y) for an exact amount header in a numeric header row."""
    ordered = sorted(row, key=lambda line: line.x)
    row_compact = compact(grouped_text(ordered))
    if AMOUNT not in row_compact:
        return None
    # Reject summary labels; require a numeric-table companion header.
    if QUANTITY not in row_compact and UNIT_PRICE not in row_compact:
        return None
    for line in ordered:
        if compact(line.text) == AMOUNT:
            return line.x + line.w, line.cy
    for left, right in zip(ordered, ordered[1:]):
        if compact(left.text) == "\uae08" and compact(right.text) == "\uc561":
            return max(left.x + left.w, right.x + right.w), (left.cy + right.cy) / 2.0
    return None


def digit_supported(row: dict) -> bool:
    """A real parser row needs numeric evidence outside the target amount cell."""
    numeric_row_fields = (
        "itemCode", "productCode", "spec", "lotNo", "serialNo",
        "manufacturingNo", "expiryDate", "quantity", "unitPrice", "insuranceCode",
    )
    return any(DIGIT_RE.search(str(row.get(key) or "")) for key in numeric_row_fields)


def raw_row_supported(row: dict) -> bool:
    """Reject footer/split rows that have no numeric evidence in their own OCR row."""
    return bool(DIGIT_RE.search(str(row.get("_rawText") or "")))


def raw_has_amount_column(raw: list) -> bool:
    """Cheap snapshot-only prefilter so replay runs only on plausible documents."""
    lines = [line for item in raw if (line := _line_from_raw(item))]
    if not lines:
        return False
    grouped = _group_rows(lines, tolerance_factor=0.55)
    headers = [found for group in grouped if (found := amount_header(group))]
    if len(headers) != 1:
        return False
    header_right, header_y = headers[0]
    page_w = max(line.x + line.w for line in lines)
    values = [
        line
        for line in lines
        if line.cy > header_y
        and MONEY_RE.fullmatch(compact(line.text))
        and abs((line.x + line.w) - header_right) <= page_w * 0.055
    ]
    return len(values) >= 3


def candidate_amounts(raw: list, rows: list[dict]) -> tuple[list[str], dict] | None:
    lines = [line for item in raw if (line := _line_from_raw(item))]
    if not lines or len(rows) < 3:
        return None
    if any(SUMMARY_ROW_RE.search(str(row.get("_rawText") or "")) for row in rows):
        return None
    grouped = _group_rows(lines, tolerance_factor=0.55)
    headers = []
    for group in grouped:
        found = amount_header(group)
        if found:
            headers.append(found)
    if len(headers) != 1:
        return None
    header_right, header_y = headers[0]
    page_w = max(line.x + line.w for line in lines)

    footer_y = None
    for group in grouped:
        y = sum(line.cy for line in group) / len(group)
        if y <= header_y:
            continue
        if FOOTER_RE.search(grouped_text(group)):
            footer_y = y
            break

    candidates = []
    for line in lines:
        value = compact(line.text)
        if line.cy <= header_y:
            continue
        if footer_y is not None and line.cy >= footer_y:
            continue
        if not MONEY_RE.fullmatch(value):
            continue
        right = line.x + line.w
        if abs(right - header_right) > page_w * 0.055:
            continue
        candidates.append((line.cy, right, value.replace(".", ",")))
    candidates.sort()

    supported = rows
    if len(candidates) != len(rows):
        return None
    if len(candidates) < 3:
        return None

    rights = [right for _, right, _ in candidates]
    med_right = statistics.median(rights)
    mad = statistics.median(abs(right - med_right) for right in rights)
    if mad > page_w * 0.012:
        return None
    ys = [y for y, _, _ in candidates]
    gaps = [b - a for a, b in zip(ys, ys[1:])]
    if gaps:
        med_gap = statistics.median(gaps)
        if med_gap <= 0 or max(gaps) > med_gap * 2.4:
            return None

    values = [value for _, _, value in candidates]
    # The document is eligible only if every existing amount agrees ordinally.
    agreement_count = 0
    for row, value in zip(supported, values):
        current = compact(row.get("amount")).replace(".", ",")
        if current and current != value:
            return None
        if current == value:
            agreement_count += 1
    raw_supported_count = sum(raw_row_supported(row) for row in supported)
    if raw_supported_count != len(supported) and agreement_count < 1:
        return None
    return values, {
        "candidateCount": len(values),
        "supportedRowCount": len(supported),
        "footerY": footer_y,
        "headerRight": header_right,
        "rightMad": mad,
        "agreementCount": agreement_count,
        "rawSupportedRowCount": raw_supported_count,
    }


def apply_candidate(raw: list, original_rows: list[dict]) -> tuple[list[dict], dict] | None:
    rows = copy.deepcopy(original_rows)
    found = candidate_amounts(raw, rows)
    if not found:
        return None
    values, debug = found
    changed = []
    for index, (row, value) in enumerate(zip([r for r in rows if digit_supported(r)], values), 1):
        if not compact(row.get("amount")):
            row["amount"] = value
            changed.append({"supportedIndex": index, "rowIndex": row.get("rowIndex"), "value": value})
    if not changed:
        return None
    debug["changed"] = changed
    return rows, debug


def status_map(table: dict) -> tuple[dict[str, str], int]:
    statuses = {}
    ext_only_amounts = 0
    ext_only = {str(x) for x in table.get("extOnlyRowIdx") or []}
    for row in table.get("rows") or []:
        key = str(row.get("rowIndex"))
        cell = (row.get("cells") or {}).get("amount") or {}
        statuses[key] = str(cell.get("status") or "")
        if key in ext_only and str(cell.get("ext") or "").strip():
            ext_only_amounts += 1
    return statuses, ext_only_amounts


def run(testset: str, run_dir: Path) -> dict:
    manifest = build_manifest(testset)
    sample_by_source = {sample["sourceFile"]: sample for sample in manifest["samples"]}
    aggregate = None
    if manifest.get("gtAggregate"):
        aggregate = load_gt_aggregate(str(EVAL / manifest["gtAggregate"]), profile=manifest["kind"])
    result = {
        "testset": testset,
        "snapshotCount": 0,
        "eligibleDocs": 0,
        "modified": 0,
        "gain": 0,
        "regression": 0,
        "spuriousBefore": 0,
        "spuriousAfter": 0,
        "stillFail": 0,
        "docs": [],
    }
    snapshots = run_dir / "snapshots"
    for path in sorted(snapshots.glob("*.json")):
        source = path.name[:-5]
        sample = sample_by_source.get(source)
        if not sample:
            continue
        snap = json.loads(path.read_text(encoding="utf-8"))
        if not raw_has_amount_column(snap.get("ocr_lines_raw") or []):
            result["snapshotCount"] += 1
            continue
        result["snapshotCount"] += 1
        sample_output_path = run_dir / "samples" / path.name
        if not sample_output_path.exists():
            continue
        sample_output = json.loads(sample_output_path.read_text(encoding="utf-8"))
        ext = sample_output.get("documentFields") or {}
        route = str(sample_output.get("extractionPath") or "")
        rows = ext.get("tableRows") or []
        if route != "fallback" or len(rows) < 3:
            continue
        if any(str(row.get("_source") or "") != "invoice_statement_table_parser" for row in rows):
            continue
        applied = apply_candidate(snap.get("ocr_lines_raw") or [], rows)
        if not applied:
            continue
        new_rows, debug = applied
        if aggregate is not None:
            gt = aggregate[sample["gtKey"]]
        else:
            gt = load_gt(str(EVAL / sample["gt"]), profile=manifest["kind"])
        before = compare_table(gt["tableRows"], rows)
        after = compare_table(gt["tableRows"], new_rows)
        before_status, before_spurious = status_map(before)
        after_status, after_spurious = status_map(after)
        keys = set(before_status) | set(after_status)
        gain = sum(before_status.get(key) != "match" and after_status.get(key) == "match" for key in keys)
        regression = sum(before_status.get(key) == "match" and after_status.get(key) != "match" for key in keys)
        changed_count = len(debug["changed"])
        result["eligibleDocs"] += 1
        result["modified"] += changed_count
        result["gain"] += gain
        result["regression"] += regression
        result["spuriousBefore"] += before_spurious
        result["spuriousAfter"] += after_spurious
        result["stillFail"] += max(0, changed_count - gain - max(0, after_spurious - before_spurious))
        result["docs"].append({
            "sourceFile": source,
            "changed": debug["changed"],
            "gain": gain,
            "regression": regression,
            "spuriousDelta": after_spurious - before_spurious,
            "debug": {key: value for key, value in debug.items() if key != "changed"},
        })
    result["spuriousDelta"] = result["spuriousAfter"] - result["spuriousBefore"]
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--testset", default="invoice_thin")
    parser.add_argument("--run-dir", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(run(args.testset, args.run_dir), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
