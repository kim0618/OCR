"""
T-7a: Invoice Statement Table Row Verification Script
Calls /ocr/extract API for 7 invoice samples using manifest tableExpectedColumns,
and reports:
- rowCount before/after
- extractionSource
- expectedValueFillRate before/after
- expectedMissingKeys per sample
- valueMappingWarnings
- Amount column misplacement candidates
"""

import json
import os
import sys
import time
import re
import requests
from pathlib import Path

# --- Config ---
BASE_URL = "http://localhost:9099"
TESTSET_DIR = Path("c:/OCR/mysuit-ocr/public/data/testsets/invoice_statement")
ROOT_DIR = Path("c:/OCR")
MANIFEST_PATH = TESTSET_DIR / "manifest.json"

GT_ROW_COUNTS = {
    "1.jpg": 28,
    "2.pdf": 13,
    "3.pdf": 1,
    "4.pdf": 1,
    "5.pdf": 6,
    "6.pdf": 6,
    "7.pdf": 1,
}

SAMPLE_MIMES = {
    "1.jpg": "image/jpeg",
    "2.pdf": "application/pdf",
    "3.pdf": "application/pdf",
    "4.pdf": "application/pdf",
    "5.pdf": "application/pdf",
    "6.pdf": "application/pdf",
    "7.pdf": "application/pdf",
}

# T-6m reported baselines (fill rate % using per-sample expected cols)
BASELINE_FILL_RATES = {
    "1.jpg": 98.5,
    "2.pdf": 61.5,
    "3.pdf": 22.2,
    "4.pdf": 85.7,
    "5.pdf": 26.7,
    "6.pdf": 88.9,
    "7.pdf": 75.0,
}

AMOUNT_LIKE_RE = re.compile(r"\d{1,3}(?:,\d{3})+")


def load_manifest() -> dict:
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def get_invoice_profile(manifest: dict, filename: str) -> dict:
    for item in manifest.get("items", []):
        if item.get("filename") == filename:
            return item.get("invoiceProfile", {})
    return {}


def call_ocr(filename: str, mime: str, table_expected_columns: dict | None) -> dict:
    fpath = TESTSET_DIR / filename
    if not fpath.exists():
        raise FileNotFoundError(f"Sample not found: {filename}")

    with open(fpath, "rb") as f:
        data = f.read()

    form_data = {"file": (filename, data, mime)}
    extra = {}
    if table_expected_columns:
        extra["tableExpectedColumns"] = (None, json.dumps(table_expected_columns), "text/plain")

    resp = requests.post(
        f"{BASE_URL}/ocr/extract",
        files={**{"file": (filename, data, mime)}, **(
            {"tableExpectedColumns": (None, json.dumps(table_expected_columns), "text/plain")}
            if table_expected_columns else {}
        )},
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()


def compute_fill_rate(rows: list[dict], expected_cols: list[str]) -> tuple[float, int, int, list[str]]:
    """Returns (fill_rate_pct, filled, total, all_missing_cols)."""
    if not rows or not expected_cols:
        return 0.0, 0, 0, list(expected_cols)

    total = 0
    filled = 0
    missing_count: dict[str, int] = {}

    for row in rows:
        for col in expected_cols:
            v = str(row.get(col) or "").strip()
            total += 1
            if v and v not in ("None", "null", "0"):
                filled += 1
            else:
                missing_count[col] = missing_count.get(col, 0) + 1

    fill_rate = filled / total * 100 if total > 0 else 0.0
    all_missing = [k for k, v in missing_count.items() if v == len(rows)]
    partial_missing = {k: v for k, v in missing_count.items() if 0 < v < len(rows)}
    return fill_rate, filled, total, all_missing


def check_amount_columns(rows: list[dict], expected_cols: list[str]) -> list[str]:
    """Find amount values in non-amount columns."""
    warnings = []
    amount_col_keys = {
        "unitPrice", "consumerUnitPrice", "supplyUnitPrice",
        "supplyAmount", "taxAmount", "amount", "totalAmount",
    }
    for i, row in enumerate(rows):
        for col in expected_cols:
            if col in amount_col_keys:
                continue
            v = str(row.get(col) or "").strip()
            if AMOUNT_LIKE_RE.search(v):
                warnings.append(f"row[{i}] col={col!r} has amount-like value: {v!r}")
    return warnings


def main():
    manifest = load_manifest()
    results = {}
    report_lines = []
    report_lines.append("# T-7a Invoice Table Row Verification Report")
    report_lines.append("Date: 2026-05-14")
    report_lines.append("")

    all_pass = True
    rc_pass_count = 0

    for filename in ["1.jpg", "2.pdf", "3.pdf", "4.pdf", "5.pdf", "6.pdf", "7.pdf"]:
        mime = SAMPLE_MIMES[filename]
        gt_count = GT_ROW_COUNTS[filename]

        profile = get_invoice_profile(manifest, filename)
        tec = profile.get("tableExpectedColumns")
        req_cols = (tec or {}).get("required", [])
        opt_cols = (tec or {}).get("optional", [])
        expected_cols = list(dict.fromkeys(req_cols + opt_cols))

        print(f"\n{'='*60}")
        print(f"Processing: {filename}")
        print(f"  expected_cols: {expected_cols}")
        print(f"{'='*60}")

        try:
            t0 = time.time()
            data = call_ocr(filename, mime, tec)
            elapsed = time.time() - t0
            print(f"  API call: {elapsed:.1f}s")
        except Exception as e:
            print(f"  ERROR: {e}")
            results[filename] = {"error": str(e)}
            report_lines.append(f"## {filename} — ERROR: {e}")
            report_lines.append("")
            all_pass = False
            continue

        df = data.get("document_fields", {})
        rows = df.get("tableRows", [])
        table_meta = df.get("tableMeta") or {}
        src = table_meta.get("extractionSource", "N/A")
        actual_count = len(rows)

        fill_rate, filled, total, all_missing = compute_fill_rate(rows, expected_cols)
        baseline_fr = BASELINE_FILL_RATES.get(filename, 0.0)
        fr_delta = fill_rate - baseline_fr
        delta_sign = "+" if fr_delta >= 0 else ""

        amount_warnings = check_amount_columns(rows, expected_cols)

        # Collect valueMappingWarnings from rows
        mapping_warnings = []
        for i, row in enumerate(rows):
            w = row.get("valueMappingWarnings") or row.get("_warnings") or []
            if isinstance(w, list):
                for ww in w:
                    mapping_warnings.append(f"row[{i}]: {ww}")
            elif w:
                mapping_warnings.append(f"row[{i}]: {w}")

        row_count_ok = (actual_count == gt_count)
        if row_count_ok:
            rc_pass_count += 1
        else:
            all_pass = False

        results[filename] = {
            "rowCount_gt": gt_count,
            "rowCount_actual": actual_count,
            "rowCount_ok": row_count_ok,
            "extractionSource": src,
            "fillRate": round(fill_rate, 1),
            "fillRate_baseline": baseline_fr,
            "fillRate_delta": round(fr_delta, 1),
            "filled": filled,
            "total": total,
            "expectedCols": expected_cols,
            "allMissingCols": all_missing,
            "amountColWarnings": amount_warnings,
            "mappingWarnings": mapping_warnings,
        }

        rc_mark = "OK" if row_count_ok else "FAIL"
        print(f"  rowCount: GT={gt_count} actual={actual_count} [{rc_mark}]")
        print(f"  extractionSource: {src}")
        print(f"  fillRate: {fill_rate:.1f}% (baseline: {baseline_fr:.1f}%, delta: {delta_sign}{fr_delta:.1f}%)")
        print(f"  filled: {filled}/{total}")
        print(f"  allMissingCols: {all_missing}")
        if amount_warnings:
            print(f"  amountColWarnings: {amount_warnings}")
        if mapping_warnings:
            print(f"  mappingWarnings: {mapping_warnings}")

        # Show per-row detail for small-row samples
        if actual_count <= 6:
            for i, row in enumerate(rows[:3]):
                filled_fields = {
                    k: str(v)[:50]
                    for k, v in row.items()
                    if k in expected_cols and v and str(v).strip() not in ("", "None", "null", "0")
                }
                print(f"  row[{i}] filled: {filled_fields}")

        # Build report section
        report_lines.append(f"## {filename}")
        report_lines.append(f"- rowCount: GT={gt_count} actual={actual_count} {'OK' if row_count_ok else 'FAIL'}")
        report_lines.append(f"- extractionSource: {src}")
        report_lines.append(f"- fillRate: {fill_rate:.1f}% (baseline={baseline_fr}%, delta={delta_sign}{fr_delta:.1f}%)")
        report_lines.append(f"- filled: {filled}/{total}")
        report_lines.append(f"- expectedCols: {expected_cols}")
        report_lines.append(f"- allMissingCols: {all_missing}")
        if amount_warnings:
            report_lines.append(f"- amountColWarnings:")
            for w in amount_warnings:
                report_lines.append(f"  - {w}")
        if mapping_warnings:
            report_lines.append(f"- valueMappingWarnings:")
            for w in mapping_warnings:
                report_lines.append(f"  - {w}")
        if rows and actual_count <= 6:
            report_lines.append(f"- rowDetail:")
            for i, row in enumerate(rows[:6]):
                rd = {
                    k: str(v)[:50]
                    for k, v in row.items()
                    if k in expected_cols and v and str(v).strip() not in ("", "None", "null", "0")
                }
                report_lines.append(f"  row[{i}]: {rd}")
        report_lines.append("")

    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"rowCount exact: {rc_pass_count}/7")

    report_lines.append("## Summary")
    report_lines.append(f"- rowCount exact: {rc_pass_count}/7")
    if rc_pass_count == 7:
        report_lines.append("- rowCount: ALL PASS (7/7)")
    else:
        report_lines.append(f"- rowCount: REGRESSION ({rc_pass_count}/7)")
    report_lines.append("")

    if rc_pass_count < 7:
        print("WARNING: rowCount regression detected!")
    else:
        print("rowCount 7/7 OK")

    # Fill rate summary
    print("\nFill Rate Summary:")
    for filename, r in results.items():
        if "error" in r:
            continue
        rc_ok = "OK" if r["rowCount_ok"] else "FAIL"
        sign = "+" if r["fillRate_delta"] >= 0 else ""
        print(f"  {filename}: {r['fillRate']}% (delta: {sign}{r['fillRate_delta']}%) rowCount={rc_ok}")

    # Save results JSON
    out_json = ROOT_DIR / "reports" / "T7a_remaining_value_mapping_amount_columns_20260514.json"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\nResults saved: {out_json}")

    # Save report MD
    out_md = ROOT_DIR / "reports" / "T7a_remaining_value_mapping_amount_columns_20260514.md"
    with open(out_md, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))
    print(f"Report saved: {out_md}")

    sys.exit(0 if rc_pass_count == 7 else 1)


if __name__ == "__main__":
    main()
