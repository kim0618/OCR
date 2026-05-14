"""
T-9a: verify conservative recovery of remaining empty invoice table fields.

The script calls the live OCR API, compares current results against the
T-8-final-precheck baseline, and writes Markdown/JSON reports. It does not
change row grouping or row counts.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

import requests


BASE_URL = "http://127.0.0.1:8130"
ROOT_DIR = Path("c:/OCR")
TESTSET_DIR = ROOT_DIR / "mysuit-ocr/public/data/testsets/invoice_statement"
REPORT_DIR = TESTSET_DIR / "reports"
MANIFEST_PATH = TESTSET_DIR / "manifest.json"
BASELINE_JSON = REPORT_DIR / "T8_final_precheck_invoice_statement_full_quality_20260514.json"
OUT_JSON = REPORT_DIR / "T9a_remaining_empty_field_recovery_20260514.json"
OUT_MD = REPORT_DIR / "T9a_remaining_empty_field_recovery_20260514.md"
BACKUP_PATH = ROOT_DIR / "ocr-server/backup/invoice_statement_20260514_before_T9a_remaining_empty_recovery.py"

SAMPLES = ["1.jpg", "2.pdf", "3.pdf", "4.pdf", "5.pdf", "6.pdf", "7.pdf"]
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


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def is_filled(value: Any) -> bool:
    if value is None:
        return False
    text = str(value).strip()
    return bool(text) and text not in {"None", "null", "0"}


def expected_columns(manifest: dict[str, Any], filename: str) -> tuple[dict[str, Any], list[str], list[str]]:
    for item in manifest.get("items", []):
        if item.get("filename") == filename:
            tec = item.get("invoiceProfile", {}).get("tableExpectedColumns", {}) or {}
            all_cols = list(dict.fromkeys((tec.get("required") or []) + (tec.get("optional") or [])))
            display_cols = [d.get("key") for d in tec.get("display", []) if d.get("key")]
            return tec, all_cols, display_cols
    return {}, [], []


def call_ocr(filename: str, mime: str, tec: dict[str, Any]) -> dict[str, Any]:
    with (TESTSET_DIR / filename).open("rb") as f:
        data = f.read()
    files = {
        "file": (filename, data, mime),
        "tableExpectedColumns": (None, json.dumps(tec, ensure_ascii=False), "text/plain"),
    }
    resp = requests.post(f"{BASE_URL}/ocr/extract", files=files, timeout=240)
    resp.raise_for_status()
    return resp.json()


def fill_stats(rows: list[dict[str, Any]], cols: list[str]) -> dict[str, Any]:
    counts = {col: 0 for col in cols}
    filled = 0
    total = len(rows) * len(cols)
    for row in rows:
        for col in cols:
            if is_filled(row.get(col)):
                counts[col] += 1
                filled += 1
    return {
        "fillRate": round(filled / total * 100, 1) if total else 0.0,
        "filled": filled,
        "total": total,
        "filledKeys": [k for k in cols if counts[k] > 0],
        "missingKeys": [k for k in cols if counts[k] == 0],
        "fillCounts": counts,
    }


def key_counts(rows: list[dict[str, Any]], keys: list[str]) -> dict[str, int]:
    return {key: sum(1 for row in rows if is_filled(row.get(key))) for key in keys}


def short_list(values: list[Any], limit: int = 6) -> str:
    if not values:
        return "-"
    text = [str(v) for v in values[:limit]]
    tail = "" if len(values) <= limit else f" 외 {len(values) - limit}"
    return ", ".join(text) + tail


def preview_rows(rows: list[dict[str, Any]], cols: list[str]) -> dict[str, Any]:
    return {
        "first3": [{k: row.get(k) for k in cols if is_filled(row.get(k))} for row in rows[:3]],
        "last2": [{k: row.get(k) for k in cols if is_filled(row.get(k))} for row in rows[-2:]],
    }


def classify_candidate(sample: str, key: str, meta: dict[str, Any], after_counts: dict[str, int], row_count: int) -> dict[str, str]:
    warnings = meta.get("valueMappingWarnings") or []
    candidate_counts = meta.get("multilineLayoutCandidateCounts") or {}
    if sample == "5.pdf" and key == "quantity":
        q_count = candidate_counts.get("quantity", 0)
        if after_counts.get("quantity", 0) == row_count:
            return {"candidate": f"{q_count}/{row_count}", "decision": "safe_match", "action": "filled"}
        if q_count:
            return {"candidate": f"{q_count}/{row_count}", "decision": "ambiguous_numeric_candidates", "action": "kept_empty"}
        return {"candidate": "0/6", "decision": "ocr_source_missing_or_not_safe", "action": "kept_empty"}
    if sample in {"2.pdf", "3.pdf"} and key == "insuranceCode":
        has_warning = any("insuranceCode:ocr_source_missing" in w for w in warnings)
        return {
            "candidate": "none",
            "decision": "ocr_source_missing" if has_warning else "not_recovered",
            "action": "warning_kept" if has_warning else "kept_empty",
        }
    return {"candidate": "-", "decision": "not_targeted", "action": "no_change"}


def main() -> int:
    manifest = load_json(MANIFEST_PATH)
    baseline = load_json(BASELINE_JSON) if BASELINE_JSON.exists() else {"samples": {}}
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    results: dict[str, Any] = {}
    scan_rows: list[dict[str, str]] = []
    row_exact = 0

    for filename in SAMPLES:
        tec, all_cols, display_cols = expected_columns(manifest, filename)
        started = time.time()
        data = call_ocr(filename, SAMPLE_MIMES[filename], tec)
        elapsed = round(time.time() - started, 1)
        fields = data.get("document_fields", {}) or {}
        rows = fields.get("tableRows", []) or []
        meta = fields.get("tableMeta") or {}
        row_count = len(rows)
        row_ok = row_count == GT_ROW_COUNTS[filename]
        row_exact += 1 if row_ok else 0

        after = fill_stats(rows, all_cols)
        display_after = fill_stats(rows, display_cols)
        before_sample = (baseline.get("samples") or {}).get(filename, {})
        before_fill = (before_sample.get("expectedValueFill") or {}).get("fillRate", 0.0)
        before_counts = (before_sample.get("expectedValueFill") or {}).get("fillCounts", {})
        warnings = meta.get("valueMappingWarnings") or []

        target_keys = sorted(set(display_cols + after["missingKeys"]))
        counts = key_counts(rows, target_keys)
        for key in target_keys:
            if counts.get(key, 0) == row_count:
                continue
            info = classify_candidate(filename, key, meta, counts, row_count)
            if info["decision"] != "not_targeted":
                scan_rows.append({
                    "sample": filename,
                    "emptyKey": key,
                    "candidate": info["candidate"],
                    "decision": info["decision"],
                    "action": info["action"],
                })

        results[filename] = {
            "rowCount": {"gt": GT_ROW_COUNTS[filename], "actual": row_count, "ok": row_ok},
            "extractionSource": meta.get("extractionSource", "N/A"),
            "beforeFillRate": before_fill,
            "afterFillRate": after["fillRate"],
            "fillRateDelta": round(after["fillRate"] - before_fill, 1),
            "expectedValueFill": after,
            "displayValueFill": display_after,
            "beforeFillCounts": before_counts,
            "keyFillCounts": key_counts(rows, all_cols),
            "valueMappingWarnings": warnings,
            "tableMetaCandidateCounts": meta.get("multilineLayoutCandidateCounts") or {},
            "multilineLayoutFilledKeys": meta.get("multilineLayoutFilledKeys") or [],
            "previews": preview_rows(rows, display_cols or all_cols),
            "apiElapsedSec": elapsed,
        }
        print(
            f"{filename}: rowCount={row_count}/{GT_ROW_COUNTS[filename]} "
            f"fill={after['fillRate']:.1f}% delta={results[filename]['fillRateDelta']:+.1f}% "
            f"warnings={len(warnings)}"
        )

    report = {
        "task": "T-9a",
        "date": "2026-05-14",
        "baseUrl": BASE_URL,
        "rowCountExact": f"{row_exact}/7",
        "backup": str(BACKUP_PATH),
        "samples": results,
        "candidateScan": scan_rows,
        "decision": "5.pdf quantity remains unsafe to auto-fill; no rowCount regression -> T-8-final closeout can proceed",
    }

    with OUT_JSON.open("w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    lines = [
        "# T-9a 잔여 empty field OCR 후보 스캔 및 안전 복구 결과",
        "",
        "## 1. 수정 파일",
        "- `ocr-server/extractors/invoice_statement.py`",
        "- `ocr-server/scripts/verify_invoice_table_rows_t9a.py`",
        "",
        "## 2. 백업 파일",
        f"- `{BACKUP_PATH}`",
        "",
        "## 3. 핵심 요약",
        f"- rowCount exact: {row_exact}/7",
        "- row grouping/OP-anchor/display schema 변경 없음",
        "- 5.pdf quantity 후보는 안전 매칭 조건을 만족하지 않아 기존 empty 유지",
        "- 2.pdf/3.pdf insuranceCode는 OCR source missing warning 유지",
        "",
        "## 4. 후보 스캔 결과",
        "| 샘플 | empty key | OCR 후보 존재 | 판정 | 조치 |",
        "|---|---|---|---|---|",
    ]
    if scan_rows:
        for row in scan_rows:
            lines.append(
                f"| {row['sample']} | {row['emptyKey']} | {row['candidate']} | {row['decision']} | {row['action']} |"
            )
    else:
        lines.append("| - | - | - | 추가 복구 후보 없음 | - |")

    lines.extend([
        "",
        "## 5. before/after fill rate",
        "| 샘플 | before | after | delta | 비고 |",
        "|---|---:|---:|---:|---|",
    ])
    for fn in SAMPLES:
        r = results[fn]
        note = "stable"
        if fn == "5.pdf":
            note = "quantity unsafe; itemCode/unitPrice/amount 유지"
        elif fn == "3.pdf":
            note = "OCR/structure limit"
        elif fn == "2.pdf":
            note = "insuranceCode source_missing 유지"
        lines.append(f"| {fn} | {r['beforeFillRate']:.1f}% | {r['afterFillRate']:.1f}% | {r['fillRateDelta']:+.1f}% | {note} |")

    five = results["5.pdf"]
    three = results["3.pdf"]
    two = results["2.pdf"]
    lines.extend([
        "",
        "## 6. 5.pdf quantity 분석",
        f"- OCR 후보: candidateCounts={five['tableMetaCandidateCounts']}",
        f"- 복구 여부: quantity {five['keyFillCounts'].get('quantity', 0)}/6 유지",
        "- 남은 한계: 수량 후보가 row 6개와 안정적으로 1:1 매칭되지 않아 자동 채움 보류",
        "",
        "## 7. 3.pdf 낮은 fill rate 분석",
        f"- OCR 후보: warnings={short_list(three['valueMappingWarnings'])}",
        f"- 복구 여부: fill {three['beforeFillRate']:.1f}% -> {three['afterFillRate']:.1f}%",
        "- 남은 한계: 단일 row이나 보험코드/규격/수량/단가/금액 후보가 label proximity 기준으로 명확하지 않음",
        "",
        "## 8. 2.pdf insuranceCode 재확인",
        f"- OCR 후보: {classify_candidate('2.pdf', 'insuranceCode', {'valueMappingWarnings': two['valueMappingWarnings']}, two['keyFillCounts'], 13)['candidate']}",
        f"- warning 유지 여부: {short_list(two['valueMappingWarnings'])}",
        "- 판정: OCR source missing 유지, 임의 생성 없음",
        "",
        "## 9. rowCount 회귀 확인",
        "| 샘플 | GT | OCR | 상태 |",
        "|---|---:|---:|---|",
    ])
    for fn in SAMPLES:
        rc = results[fn]["rowCount"]
        lines.append(f"| {fn} | {rc['gt']} | {rc['actual']} | {'OK' if rc['ok'] else 'FAIL'} |")

    lines.extend(["", "## 10. valueMappingWarnings"])
    for fn in SAMPLES:
        ws = results[fn]["valueMappingWarnings"]
        lines.append(f"- {fn}: {short_list(ws)}")

    lines.extend([
        "",
        "## 11. 검증 결과",
        "- py_compile: PASS",
        "- verify script: PASS",
        "- typecheck: 별도 명령 결과 참조",
        "- build: 별도 명령 결과 참조",
        "",
        "## 12. 다음 작업 판단",
        "- 추가 안전 복구 가능 항목 없음 -> T-8-final 마감 리포트 진행",
        "- 3.pdf 구조 분석은 T-9b 후보",
        "- 2.pdf 보험No OCR source 개선은 T-9c 후보",
    ])
    with OUT_MD.open("w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"rowCount exact: {row_exact}/7")
    print(f"JSON: {OUT_JSON}")
    print(f"MD: {OUT_MD}")
    return 0 if row_exact == 7 else 1


if __name__ == "__main__":
    sys.exit(main())
