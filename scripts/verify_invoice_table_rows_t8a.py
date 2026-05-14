"""
T-8a: Verify multiline column layout post-processing for 5.pdf.

Checks:
- rowCount 7/7 exact
- 5.pdf itemCode/unitPrice/amount fill count before/after
- 5.pdf itemName/quantity regression check
- 1/2/3/4/6/7 fill rate regression check
- multilineLayoutMappingApplied flag
- valueMappingWarnings content
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
OUT_JSON = REPORT_DIR / "T8a_multiline_layout_value_mapping_20260514.json"
OUT_MD = REPORT_DIR / "T8a_multiline_layout_value_mapping_20260514.md"

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

# T-8b baseline fill rates (from T-8b run)
BASELINE_FILL_RATES = {
    "1.jpg": 60.4, "2.pdf": 44.8, "3.pdf": 16.7,
    "4.pdf": 80.0, "5.pdf": 14.8, "6.pdf": 50.0, "7.pdf": 66.7,
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


def filled_missing(rows: list[dict], cols: list[str]) -> tuple[float, int, int, list[str], list[str]]:
    filled = 0
    total = len(rows) * len(cols) if rows and cols else 0
    counts = {col: 0 for col in cols}
    for row in rows:
        for col in cols:
            v = str(row.get(col) or "").strip()
            if v and v not in {"None", "null", "0"}:
                filled += 1
                counts[col] += 1
    filled_keys = [c for c in cols if counts[c] > 0]
    missing_keys = [c for c in cols if counts[c] == 0]
    rate = round(filled / total * 100, 1) if total else 0.0
    return rate, filled, total, filled_keys, missing_keys


def main() -> int:
    manifest = load_json(MANIFEST_PATH)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    results: dict[str, dict] = {}
    row_exact = 0
    all_pass = True

    for filename in SAMPLES:
        tec = get_tec(manifest, filename)
        required = tec.get("required", [])
        optional = tec.get("optional", [])
        all_cols = list(dict.fromkeys(required + optional))

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

        fill_rate, filled, total, filled_keys, missing_keys = filled_missing(rows, all_cols)
        baseline = BASELINE_FILL_RATES.get(filename, 0.0)
        delta = round(fill_rate - baseline, 1)

        warnings = meta.get("valueMappingWarnings") or []
        multiline_applied = meta.get("multilineLayoutMappingApplied", False)
        multiline_filled = meta.get("multilineLayoutFilledKeys", [])
        multiline_counts = meta.get("multilineLayoutCandidateCounts", {})

        # 5.pdf specific checks
        if filename == "5.pdf":
            key_counts = {}
            for key in ["itemName", "itemCode", "quantity", "unitPrice", "amount"]:
                cnt = sum(1 for r in rows if str(r.get(key) or "").strip())
                key_counts[key] = cnt
            results[filename] = {
                "rowCount": {"gt": GT_ROW_COUNTS[filename], "actual": row_count, "ok": row_ok},
                "extractionSource": meta.get("extractionSource", "N/A"),
                "fillRate": fill_rate,
                "fillRateBaseline": baseline,
                "fillRateDelta": delta,
                "filled": filled,
                "total": total,
                "filledKeys": filled_keys,
                "missingKeys": missing_keys,
                "keyFillCounts": key_counts,
                "multilineApplied": multiline_applied,
                "multilineFilledKeys": multiline_filled,
                "multilineCandidateCounts": multiline_counts,
                "valueMappingWarnings": warnings,
                "apiElapsedSec": elapsed,
            }
            sign = "+" if delta >= 0 else ""
            print(f"{filename}: rowCount={row_count}/{GT_ROW_COUNTS[filename]} {'OK' if row_ok else 'FAIL'}")
            print(f"  fillRate={fill_rate:.1f}% (baseline={baseline:.1f}% delta={sign}{delta:.1f}%)")
            print(f"  keyFillCounts: {key_counts}")
            print(f"  multilineApplied={multiline_applied} filledKeys={multiline_filled}")
            print(f"  candidateCounts={multiline_counts}")
            if warnings:
                for w in warnings:
                    print(f"  warning: {w}")
        else:
            results[filename] = {
                "rowCount": {"gt": GT_ROW_COUNTS[filename], "actual": row_count, "ok": row_ok},
                "extractionSource": meta.get("extractionSource", "N/A"),
                "fillRate": fill_rate,
                "fillRateBaseline": baseline,
                "fillRateDelta": delta,
                "filled": filled,
                "total": total,
                "filledKeys": filled_keys,
                "missingKeys": missing_keys,
                "multilineApplied": multiline_applied,
                "valueMappingWarnings": warnings,
                "apiElapsedSec": elapsed,
            }
            sign = "+" if delta >= 0 else ""
            regression = "" if delta >= -2.0 else " [REGRESSION]"
            print(f"{filename}: rowCount={row_count}/{GT_ROW_COUNTS[filename]} {'OK' if row_ok else 'FAIL'} "
                  f"fill={fill_rate:.1f}%({sign}{delta:.1f}%){regression}")

    print(f"\nrowCount exact: {row_exact}/7")

    # Build markdown report
    lines_out = [
        "# T-8a 5.pdf 다단 OCR layout value mapping 결과",
        "",
        "## 1. rowCount",
        "| 샘플 | GT | OCR | 상태 |",
        "|---|---:|---:|---|",
    ]
    for fn in SAMPLES:
        r = results[fn]["rowCount"]
        lines_out.append(f"| {fn} | {r['gt']} | {r['actual']} | {'OK' if r['ok'] else 'FAIL'} |")

    lines_out.extend([
        "",
        "## 2. fill rate before/after",
        "| 샘플 | before | after | delta | extractionSource |",
        "|---|---:|---:|---:|---|",
    ])
    for fn in SAMPLES:
        r = results[fn]
        sign = "+" if r["fillRateDelta"] >= 0 else ""
        lines_out.append(
            f"| {fn} | {r['fillRateBaseline']:.1f}% | {r['fillRate']:.1f}% | "
            f"{sign}{r['fillRateDelta']:.1f}% | {r['extractionSource']} |"
        )

    lines_out.extend([
        "",
        "## 3. 5.pdf key fill counts",
        "| key | filled rows | total rows |",
        "|---|---:|---:|",
    ])
    if "keyFillCounts" in results.get("5.pdf", {}):
        for key, cnt in results["5.pdf"]["keyFillCounts"].items():
            lines_out.append(f"| {key} | {cnt} | {GT_ROW_COUNTS['5.pdf']} |")

    lines_out.extend([
        "",
        "## 4. 5.pdf multiline 매핑 결과",
        f"- multilineLayoutMappingApplied: {results.get('5.pdf', {}).get('multilineApplied')}",
        f"- filledKeys: {results.get('5.pdf', {}).get('multilineFilledKeys')}",
        f"- candidateCounts: {results.get('5.pdf', {}).get('multilineCandidateCounts')}",
        "",
        "## 5. valueMappingWarnings",
        "| 샘플 | warnings |",
        "|---|---|",
    ])
    for fn in SAMPLES:
        ws = results[fn].get("valueMappingWarnings", [])
        lines_out.append(f"| {fn} | {'; '.join(ws) if ws else '-'} |")

    with OUT_JSON.open("w", encoding="utf-8") as f:
        json.dump({"task": "T-8a", "date": "2026-05-14", "samples": results}, f, ensure_ascii=False, indent=2)
    with OUT_MD.open("w", encoding="utf-8") as f:
        f.write("\n".join(lines_out) + "\n")

    print(f"JSON: {OUT_JSON}")
    print(f"MD: {OUT_MD}")
    return 0 if row_exact == 7 else 1


if __name__ == "__main__":
    sys.exit(main())
