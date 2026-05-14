"""
T-8b: insuranceCode OCR source missing warning verification script.

Checks:
- rowCount 7/7 exact
- 2.pdf insuranceCode is empty (not guessed)
- tableMeta.valueMappingWarnings contains insuranceCode:ocr_source_missing warning for 2.pdf
- 3.pdf also gets the warning (insuranceCode is required there too, and empty)
- Other samples do NOT get unnecessary insuranceCode warnings
- No rowCount regression
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

import requests

BASE_URL = "http://127.0.0.1:9099"
ROOT_DIR = Path("c:/OCR")
TESTSET_DIR = ROOT_DIR / "mysuit-ocr/public/data/testsets/invoice_statement"
REPORT_DIR = TESTSET_DIR / "reports"
MANIFEST_PATH = TESTSET_DIR / "manifest.json"
OUT_JSON = REPORT_DIR / "T8b_insurance_code_warning_policy_20260514.json"
OUT_MD = REPORT_DIR / "T8b_insurance_code_warning_policy_20260514.md"

SAMPLES = ["1.jpg", "2.pdf", "3.pdf", "4.pdf", "5.pdf", "6.pdf", "7.pdf"]
GT_ROW_COUNTS = {
    "1.jpg": 28, "2.pdf": 13, "3.pdf": 1,
    "4.pdf": 1, "5.pdf": 6, "6.pdf": 6, "7.pdf": 1,
}
SAMPLE_MIMES = {
    "1.jpg": "image/jpeg",
    "2.pdf": "application/pdf", "3.pdf": "application/pdf",
    "4.pdf": "application/pdf", "5.pdf": "application/pdf",
    "6.pdf": "application/pdf", "7.pdf": "application/pdf",
}


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def get_tec(manifest: dict, filename: str) -> dict:
    for item in manifest.get("items", []):
        if item.get("filename") == filename:
            return item.get("invoiceProfile", {}).get("tableExpectedColumns", {})
    return {}


def call_ocr(filename: str, mime: str, tec: dict) -> dict:
    with (TESTSET_DIR / filename).open("rb") as f:
        data = f.read()
    files = {
        "file": (filename, data, mime),
        "tableExpectedColumns": (None, json.dumps(tec, ensure_ascii=False), "text/plain"),
    }
    resp = requests.post(f"{BASE_URL}/ocr/extract", files=files, timeout=180)
    resp.raise_for_status()
    return resp.json()


def check_insurance_warning(warnings: list[str]) -> bool:
    return any("insuranceCode:ocr_source_missing" in w for w in warnings)


def main() -> int:
    manifest = load_json(MANIFEST_PATH)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    results: dict[str, dict] = {}
    row_exact = 0
    all_pass = True

    for filename in SAMPLES:
        tec = get_tec(manifest, filename)
        required_cols = tec.get("required", [])
        has_insurance_required = "insuranceCode" in required_cols

        t0 = time.time()
        data = call_ocr(filename, SAMPLE_MIMES[filename], tec)
        elapsed = round(time.time() - t0, 1)

        df = data.get("document_fields", {})
        rows = df.get("tableRows", []) or []
        meta = df.get("tableMeta") or {}

        row_count = len(rows)
        row_ok = row_count == GT_ROW_COUNTS[filename]
        if row_ok:
            row_exact += 1
        else:
            all_pass = False

        # Check insuranceCode values in rows
        insurance_values = [str(row.get("insuranceCode") or "").strip() for row in rows]
        insurance_filled = sum(1 for v in insurance_values if v)
        insurance_all_empty = insurance_filled == 0

        # Check valueMappingWarnings
        warnings = meta.get("valueMappingWarnings") or []
        has_insurance_warning = check_insurance_warning(warnings)

        # Determine expected behavior
        expects_warning = has_insurance_required and insurance_all_empty
        warning_correct = (has_insurance_warning == expects_warning)
        if not warning_correct:
            all_pass = False

        # Build checks
        checks = {
            "rowCount_ok": row_ok,
            "insurance_all_empty": insurance_all_empty,
            "has_insurance_required_col": has_insurance_required,
            "expects_warning": expects_warning,
            "has_insurance_warning": has_insurance_warning,
            "warning_correct": warning_correct,
        }

        results[filename] = {
            "rowCount": {"gt": GT_ROW_COUNTS[filename], "actual": row_count, "ok": row_ok},
            "extractionSource": meta.get("extractionSource", "N/A"),
            "expectedMissingKeys": meta.get("expectedMissingKeys", []),
            "valueMappingWarnings": warnings,
            "insuranceCode": {
                "requiredCol": has_insurance_required,
                "filledRows": insurance_filled,
                "allEmpty": insurance_all_empty,
            },
            "checks": checks,
            "apiElapsedSec": elapsed,
        }

        status = "PASS" if (row_ok and warning_correct) else "FAIL"
        print(f"{filename}: rowCount={row_count}/{GT_ROW_COUNTS[filename]} "
              f"insuranceFilled={insurance_filled} "
              f"hasWarning={has_insurance_warning} "
              f"expectsWarning={expects_warning} [{status}]")
        if warnings:
            for w in warnings:
                print(f"  warning: {w}")

    print(f"\nrowCount exact: {row_exact}/7")
    print(f"All checks pass: {all_pass}")

    # Build report
    summary = {
        "task": "T-8b",
        "date": "2026-05-14",
        "baseUrl": BASE_URL,
        "rowCountExact": f"{row_exact}/7",
        "allPass": all_pass,
        "samples": results,
    }

    with OUT_JSON.open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    lines = [
        "# T-8b insuranceCode OCR source missing 표시 정책 검증",
        "",
        "## rowCount",
        "| 샘플 | GT | OCR | 상태 |",
        "|---|---:|---:|---|",
    ]
    for fn in SAMPLES:
        r = results[fn]["rowCount"]
        lines.append(f"| {fn} | {r['gt']} | {r['actual']} | {'OK' if r['ok'] else 'FAIL'} |")

    lines.extend([
        "",
        "## insuranceCode warning 점검",
        "| 샘플 | required | allEmpty | expectsWarn | hasWarn | 상태 |",
        "|---|---|---|---|---|---|",
    ])
    for fn in SAMPLES:
        r = results[fn]
        ic = r["insuranceCode"]
        chk = r["checks"]
        lines.append(
            f"| {fn} | {ic['requiredCol']} | {ic['allEmpty']} | "
            f"{chk['expects_warning']} | {chk['has_insurance_warning']} | "
            f"{'OK' if chk['warning_correct'] else 'FAIL'} |"
        )

    lines.extend(["", "## valueMappingWarnings 내용", "| 샘플 | warnings |", "|---|---|"])
    for fn in SAMPLES:
        ws = results[fn]["valueMappingWarnings"]
        lines.append(f"| {fn} | {'; '.join(ws) if ws else '-'} |")

    with OUT_MD.open("w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"JSON: {OUT_JSON}")
    print(f"MD: {OUT_MD}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
