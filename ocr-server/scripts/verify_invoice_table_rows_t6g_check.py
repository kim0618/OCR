"""T-6g-check invoice_statement expected-schema analysis.

This script does not modify extraction logic. It reads the invoice_statement
manifest, optionally calls /ocr/extract for all 7 samples, and writes a Markdown
and JSON analysis report focused on rowCount and expected-column value mapping.

Usage:
  cd d:/Free_Vue/OCR/ocr-server
  python scripts/verify_invoice_table_rows_t6g_check.py --api-url http://127.0.0.1:8116
  python scripts/verify_invoice_table_rows_t6g_check.py --start-server --port 8116
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any


try:
    import requests
except Exception:  # pragma: no cover - reported in runtime status
    requests = None  # type: ignore[assignment]


SERVER_ROOT = Path(__file__).resolve().parents[1]
OCR_ROOT = SERVER_ROOT.parent
FRONTEND_ROOT = OCR_ROOT / "mysuit-ocr"
TESTSET_DIR = FRONTEND_ROOT / "public" / "data" / "testsets" / "invoice_statement"
MANIFEST_PATH = TESTSET_DIR / "manifest.json"
OCR_CACHE_PATH = TESTSET_DIR / "ocr_cache.json"
REPORTS_DIR = TESTSET_DIR / "reports"
REPORT_PATH = REPORTS_DIR / "T6g_check_expected_schema_runall_analysis_20260512.md"
JSON_REPORT_PATH = REPORTS_DIR / "T6g_check_expected_schema_runall_analysis_20260512.json"


TARGET_SCHEMA: dict[str, dict[str, Any]] = {
    "1.jpg": {
        "target_count": 7,
        "target_row_count": 28,
        "columns": [
            ("품목", "itemName"),
            ("규격", "spec"),
            ("제조번호", "manufacturingNo"),
            ("유효기간", "expiryDate"),
            ("수량", "quantity"),
            ("단가", "unitPrice"),
            ("금액", "amount"),
        ],
    },
    "2.pdf": {
        "target_count": 8,
        "target_row_count": None,
        "columns": [
            ("NO", "rowIndex"),
            ("품목코드", "itemCode"),
            ("품목명", "itemName"),
            ("수량", "quantity"),
            ("소비자단가", "consumerUnitPrice"),
            ("공급단가", "supplyUnitPrice"),
            ("공급금액", "supplyAmount"),
            ("보험No", "insuranceCode"),
        ],
    },
    "3.pdf": {
        "target_count": 9,
        "target_row_count": None,
        "columns": [
            ("순번", "rowIndex"),
            ("보험코드", "insuranceCode"),
            ("품명", "itemName"),
            ("규격", "spec"),
            ("수량", "quantity"),
            ("단가", "unitPrice"),
            ("금액", "amount"),
            ("제조회사", "manufacturer"),
            ("제조번호/유효기간", "manufacturingExpiryComposite"),
        ],
    },
    "4.pdf": {
        "target_count": 7,
        "target_row_count": None,
        "columns": [
            ("품목명", "itemName"),
            ("LotNo.", "lotNo"),
            ("단위", "unit"),
            ("수량", "quantity"),
            ("단가", "unitPrice"),
            ("공급가액", "supplyAmount"),
            ("세액", "taxAmount"),
        ],
    },
    "5.pdf": {
        "target_count": 5,
        "target_row_count": 6,
        "columns": [
            ("품명", "itemName"),
            ("품목코드", "itemCode"),
            ("수량", "quantity"),
            ("단가", "unitPrice"),
            ("금액", "amount"),
        ],
    },
    "6.pdf": {
        "target_count": 6,
        "target_row_count": 6,
        "columns": [
            ("NO", "rowIndex"),
            ("제품코드", "itemCode"),
            ("제품명", "itemName"),
            ("수량", "quantity"),
            ("LotNo", "lotNo"),
            ("유효일자", "expiryDate"),
        ],
    },
    "7.pdf": {
        "target_count": 4,
        "target_row_count": 1,
        "columns": [
            ("품명", "itemName"),
            ("시리얼/로트No.", "serialLotComposite"),
            ("단위", "unit"),
            ("수량", "quantity"),
        ],
    },
}


CUSTOM_RESOLVER_KEYS = {
    "consumerUnitPrice": ("unitPrice",),
    "supplyUnitPrice": ("unitPrice",),
    "manufacturingExpiry": ("manufacturingNo", "expiryDate"),
    "manufacturingExpiryComposite": ("manufacturingNo", "expiryDate"),
    "serialLot": ("serialNo", "lotNo"),
    "serialLotComposite": ("serialNo", "lotNo"),
}


@dataclass
class SourceStatus:
    latest_reports: list[str]
    ocr_cache_exists: bool
    ocr_cache_has_coordinates: bool
    saved_table_result_files: list[str]


def load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def manifest_items() -> dict[str, dict[str, Any]]:
    data = load_json(MANIFEST_PATH, {})
    items = data.get("items") if isinstance(data, dict) else []
    return {str(item.get("filename")): item for item in items if isinstance(item, dict)}


def expected_columns_from_manifest(item: dict[str, Any]) -> dict[str, list[str]]:
    profile = item.get("invoiceProfile") if isinstance(item, dict) else {}
    tec = profile.get("tableExpectedColumns") if isinstance(profile, dict) else {}
    if not isinstance(tec, dict):
        return {"required": [], "optional": []}
    required = [str(x) for x in tec.get("required", [])]
    optional = [str(x) for x in tec.get("optional", [])]
    return {"required": required, "optional": optional}


def inspect_saved_sources() -> SourceStatus:
    latest_reports: list[str] = []
    if REPORTS_DIR.exists():
        reports = sorted(REPORTS_DIR.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)
        latest_reports = [p.name for p in reports[:12]]

    cache = load_json(OCR_CACHE_PATH, {})
    has_coords = False
    if isinstance(cache, dict):
        for value in cache.values():
            if not isinstance(value, dict):
                continue
            if any(k in value for k in ("ocr_lines", "ocrLines", "lines", "words")):
                has_coords = True
                break

    table_files: list[str] = []
    for path in TESTSET_DIR.glob("**/*"):
        if not path.is_file() or path.suffix.lower() not in {".json", ".md"}:
            continue
        if path.name in {"manifest.json", "ocr_cache.json", "ground_truth.json", "autofill_cache.json"}:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if "tableRows" in text or "tableMeta" in text or "rowCount" in text:
            table_files.append(str(path.relative_to(TESTSET_DIR)))

    return SourceStatus(
        latest_reports=latest_reports,
        ocr_cache_exists=OCR_CACHE_PATH.exists(),
        ocr_cache_has_coordinates=has_coords,
        saved_table_result_files=table_files[:20],
    )


def healthcheck(api_url: str, timeout: float = 2.0) -> tuple[bool, str]:
    if requests is None:
        return False, "requests import failed"
    try:
        response = requests.get(api_url.rstrip("/") + "/docs", timeout=timeout)
        return response.status_code < 500, f"GET /docs status={response.status_code}"
    except Exception as exc:
        return False, str(exc)


def start_server(port: int) -> subprocess.Popen[str]:
    python = SERVER_ROOT / ".venv" / "Scripts" / "python.exe"
    if not python.exists():
        python = Path(sys.executable)
    return subprocess.Popen(
        [str(python), "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", str(port)],
        cwd=str(SERVER_ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )


def wait_for_server(api_url: str, seconds: int = 20) -> tuple[bool, str]:
    last = ""
    for _ in range(seconds):
        ok, detail = healthcheck(api_url, timeout=1.5)
        last = detail
        if ok:
            return True, detail
        time.sleep(1)
    return False, last


def call_extract(api_url: str, filename: str, expected_columns: dict[str, list[str]], timeout: int) -> dict[str, Any]:
    if requests is None:
        return {"ok": False, "error": "requests package is not available"}

    sample_path = TESTSET_DIR / filename
    if not sample_path.exists():
        return {"ok": False, "error": f"sample file not found: {sample_path}"}

    url = api_url.rstrip("/") + "/ocr/extract"
    try:
        print(f"Calling /ocr/extract for {filename} ...", flush=True)
        with sample_path.open("rb") as fh:
            response = requests.post(
                url,
                files={"file": (filename, fh, "application/octet-stream")},
                data={"tableExpectedColumns": json.dumps(expected_columns, ensure_ascii=False)},
                timeout=timeout,
            )
        if response.status_code >= 400:
            return {
                "ok": False,
                "status_code": response.status_code,
                "error": response.text[:1000],
            }
        payload = response.json()
        document_fields = payload.get("document_fields") or payload.get("documentFields") or {}
        return {"ok": True, "status_code": response.status_code, "payload": payload, "document_fields": document_fields}
    except Exception as exc:
        return {"ok": False, "error": repr(exc)}


def row_value(row: dict[str, Any], key: str) -> str:
    if key in CUSTOM_RESOLVER_KEYS:
        values = [str(row.get(k) or "").strip() for k in CUSTOM_RESOLVER_KEYS[key]]
        return " / ".join([v for v in values if v])
    value = row.get(key)
    return "" if value is None else str(value).strip()


def nonempty_columns(rows: list[dict[str, Any]], keys: list[str]) -> tuple[list[str], list[str]]:
    present: list[str] = []
    empty: list[str] = []
    for key in keys:
        if any(row_value(row, key) for row in rows if isinstance(row, dict)):
            present.append(key)
        else:
            empty.append(key)
    return present, empty


def compact(value: Any, max_len: int = 90) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        text = ", ".join(str(x) for x in value)
    elif isinstance(value, dict):
        text = json.dumps(value, ensure_ascii=False, sort_keys=True)
    else:
        text = str(value)
    text = text.replace("\n", " ").replace("|", "\\|")
    return text if len(text) <= max_len else text[: max_len - 3] + "..."


def summarize_debug(table_debug: dict[str, Any]) -> dict[str, Any]:
    rejected = table_debug.get("rejectedRows")
    if not isinstance(rejected, list):
        rejected = []
    reason_counts = Counter(str(r.get("reason", "unknown")) for r in rejected if isinstance(r, dict))
    return {
        "headerUsed": table_debug.get("headerUsed") or table_debug.get("expectedColumnsUsed"),
        "headerRowFound": table_debug.get("headerRowFound") or table_debug.get("headerBandFound"),
        "headerScore": table_debug.get("headerScore") or table_debug.get("selectedHeaderBand", {}).get("score")
        if isinstance(table_debug.get("selectedHeaderBand"), dict)
        else table_debug.get("headerScore"),
        "fallbackSource": table_debug.get("fallbackSource") or table_debug.get("fallbackReason"),
        "rejectedRows": dict(reason_counts),
    }


def extract_table_debug(payload: dict[str, Any], document_fields: dict[str, Any]) -> dict[str, Any]:
    debug = payload.get("extract_debug") or payload.get("extractDebug") or {}
    invoice_debug = debug.get("invoice_statement") if isinstance(debug, dict) else {}
    if isinstance(invoice_debug, dict):
        table_debug = invoice_debug.get("tableDebug") or invoice_debug.get("table", {}).get("tableDebug")
        if isinstance(table_debug, dict):
            return table_debug
    table_debug = document_fields.get("tableDebug") or document_fields.get("tableRowsDebug")
    return table_debug if isinstance(table_debug, dict) else {}


def classify_failures(
    filename: str,
    schema_ok: bool,
    api_result: dict[str, Any],
    rows: list[dict[str, Any]],
    meta: dict[str, Any],
    empty_cols: list[str],
) -> list[str]:
    failures: list[str] = []
    if not schema_ok:
        failures.append("schema_mismatch")
    if not api_result.get("ok"):
        failures.append("api_run_failed")
        failures.append("no_saved_result")
        return failures

    target_rows = TARGET_SCHEMA[filename]["target_row_count"]
    row_count = len(rows)
    if target_rows is not None:
        if row_count < target_rows:
            failures.append("row_count_short")
        elif row_count > target_rows:
            failures.append("row_count_over")

    table_debug = meta.get("_tableDebug") if isinstance(meta.get("_tableDebug"), dict) else {}
    debug_summary = summarize_debug(table_debug)
    if debug_summary.get("headerUsed") is False and debug_summary.get("headerRowFound") is False:
        failures.append("header_detect_fail")

    expected_keys = [key for _, key in TARGET_SCHEMA[filename]["columns"]]
    meta_missing = meta.get("missingExpectedColumnKeys")
    if isinstance(meta_missing, list) and meta_missing:
        failures.append("value_mapping_wrong")
    if any(k in empty_cols for k in expected_keys):
        for key in empty_cols:
            if key in {"consumerUnitPrice", "supplyUnitPrice"}:
                failures.append("custom_key_empty")
            elif key in {"manufacturingExpiryComposite", "serialLotComposite", "manufacturingExpiry", "serialLot"}:
                failures.append("composite_display_empty")
            elif key != "rowIndex":
                failures.append("value_mapping_wrong")

    if row_count and rows:
        summary_markers = ("합계", "TOTAL", "공급가액", "세액", "총수", "계약")
        for row in rows:
            text = " ".join(str(v) for v in row.values() if v)
            if any(marker in text for marker in summary_markers):
                failures.append("summary_row_mixed")
                break

    return sorted(set(failures)) or ["ok"]


def analyze(api_url: str | None, timeout: int) -> dict[str, Any]:
    manifest = manifest_items()
    saved_sources = inspect_saved_sources()

    schema_results: dict[str, dict[str, Any]] = {}
    sample_results: dict[str, dict[str, Any]] = {}

    for filename, target in TARGET_SCHEMA.items():
        item = manifest.get(filename, {})
        manifest_expected = expected_columns_from_manifest(item)
        manifest_required = manifest_expected["required"]
        target_keys = [key for _, key in target["columns"]]
        schema_ok = manifest_required == target_keys
        schema_results[filename] = {
            "target_count": target["target_count"],
            "manifest_count": len(manifest_required),
            "target_keys": target_keys,
            "manifest_required": manifest_required,
            "manifest_optional": manifest_expected["optional"],
            "ok": schema_ok,
        }

        api_result: dict[str, Any] = {"ok": False, "error": "api_url not provided"}
        if api_url:
            api_result = call_extract(api_url, filename, manifest_expected, timeout)

        document_fields = api_result.get("document_fields") if api_result.get("ok") else {}
        if not isinstance(document_fields, dict):
            document_fields = {}
        rows_raw = document_fields.get("tableRows") or []
        rows = [r for r in rows_raw if isinstance(r, dict)] if isinstance(rows_raw, list) else []
        meta = document_fields.get("tableMeta") or {}
        if not isinstance(meta, dict):
            meta = {}
        payload = api_result.get("payload") if isinstance(api_result.get("payload"), dict) else {}
        table_debug = extract_table_debug(payload, document_fields) if api_result.get("ok") else {}
        meta["_tableDebug"] = table_debug

        present, empty = nonempty_columns(rows, target_keys)
        table_meta_columns = meta.get("columns") if isinstance(meta.get("columns"), list) else []
        wrong_suspects = [
            key for key in empty if key not in {"rowIndex"} and any(row_value(row, key) for row in rows) is False
        ]

        sample_results[filename] = {
            "collection_method": "api" if api_result.get("ok") else "none",
            "success": bool(api_result.get("ok")),
            "error": api_result.get("error", ""),
            "status_code": api_result.get("status_code"),
            "doc_type": payload.get("doc_type") or payload.get("document_type"),
            "rowCount": len(rows) if api_result.get("ok") else None,
            "targetRowCount": target["target_row_count"],
            "tableRowsPreview": rows[:3],
            "tableMeta": {k: v for k, v in meta.items() if k != "_tableDebug"},
            "tableDebugSummary": summarize_debug(table_debug),
            "valuePresentColumns": present,
            "valueEmptyColumns": empty,
            "wrongSuspectColumns": wrong_suspects,
            "customCompositeDisplay": {
                key: {
                    "displayable": key in CUSTOM_RESOLVER_KEYS,
                    "nonempty": key in present,
                    "sourceKeys": list(CUSTOM_RESOLVER_KEYS.get(key, (key,))),
                }
                for key in target_keys
                if key in CUSTOM_RESOLVER_KEYS
            },
            "failures": classify_failures(filename, schema_ok, api_result, rows, meta, empty),
        }

    return {
        "generatedAt": time.strftime("%Y-%m-%d %H:%M:%S"),
        "apiUrl": api_url or "",
        "manifestPath": str(MANIFEST_PATH),
        "savedSources": saved_sources.__dict__,
        "schema": schema_results,
        "samples": sample_results,
    }


def judgment_for_row(filename: str, current: int | None, target: int | None) -> tuple[str, str]:
    if current is None:
        return "-", "수집 실패"
    if target is None:
        if filename == "2.pdf" and current <= 2:
            return "?", "대량 누락 의심"
        return "?", "이미지 기준 확인 필요"
    diff = current - target
    if diff == 0:
        return "0", "OK"
    if diff < 0:
        return str(diff), "부족"
    return f"+{diff}", "초과"


def priority_for_failures(failures: list[str]) -> str:
    if "api_run_failed" in failures:
        return "P0 데이터 확보"
    if "row_count_short" in failures or "header_detect_fail" in failures:
        return "P1"
    if "value_mapping_wrong" in failures or "custom_key_empty" in failures or "composite_display_empty" in failures:
        return "P2"
    if "schema_mismatch" in failures:
        return "P1"
    return "P3"


def render_report(data: dict[str, Any]) -> str:
    schema = data["schema"]
    samples = data["samples"]
    saved = data["savedSources"]
    api_used = bool(data.get("apiUrl"))
    api_success_count = sum(1 for r in samples.values() if r.get("success"))
    cache_limit = "ocr_cache.json은 ocr_text 중심이며 좌표 OCR 라인이 없어 실제 row grouping 재현용으로는 부족함"

    lines: list[str] = []
    lines.append("# T-6g-check expected schema 기준 RunAll 결과 분석\n")
    lines.append("## 1. 분석 대상")
    lines.append(f"- 사용한 데이터 소스: manifest.json, reports 디렉터리, ocr_cache.json, API {data.get('apiUrl') or '(미사용)'}")
    lines.append(f"- API 실행 여부: {'실행' if api_used else '미실행'} ({api_success_count}/7 성공)")
    lines.append(f"- 저장 결과 사용 여부: {'tableRows/tableMeta 후보 파일 있음' if saved['saved_table_result_files'] else '저장된 tableRows/tableMeta JSON 없음'}")
    lines.append(f"- 한계: {cache_limit}")
    lines.append("")

    lines.append("## 2. expected schema 정적 검증")
    lines.append("| 샘플 | 목표 count | manifest count | expected columns | 판정 |")
    lines.append("|---|---:|---:|---|---|")
    for filename in TARGET_SCHEMA:
        s = schema[filename]
        cols = ", ".join(f"{label} `{key}`" for label, key in TARGET_SCHEMA[filename]["columns"])
        verdict = "일치" if s["ok"] else f"불일치: manifest={compact(s['manifest_required'])}"
        lines.append(f"| {filename} | {s['target_count']} | {s['manifest_count']} | {cols} | {verdict} |")
    lines.append("")

    lines.append("## 3. OCR 결과 수집 상태")
    lines.append("| 샘플 | 결과 수집 방식 | 성공 여부 | 비고 |")
    lines.append("|---|---|---|---|")
    for filename in TARGET_SCHEMA:
        r = samples[filename]
        note = f"status={r.get('status_code')}, doc_type={r.get('doc_type')}" if r.get("success") else compact(r.get("error") or "결과 없음")
        lines.append(f"| {filename} | {r['collection_method']} | {'성공' if r['success'] else '실패'} | {note} |")
    lines.append("")

    lines.append("## 4. 샘플별 rowCount 비교")
    lines.append("| 샘플 | 목표 row 수 | 현재 rowCount | 차이 | 판정 |")
    lines.append("|---|---:|---:|---:|---|")
    for filename in TARGET_SCHEMA:
        r = samples[filename]
        target = r["targetRowCount"]
        current = r["rowCount"]
        diff, verdict = judgment_for_row(filename, current, target)
        target_text = "확인 필요" if target is None else str(target)
        current_text = "-" if current is None else str(current)
        lines.append(f"| {filename} | {target_text} | {current_text} | {diff} | {verdict} |")
    lines.append("")

    lines.append("## 5. 샘플별 컬럼 값 매핑 상태")
    lines.append("| 샘플 | 값 있는 컬럼 | 비어 있는 컬럼 | 잘못 들어간 의심 컬럼 | 비고 |")
    lines.append("|---|---|---|---|---|")
    for filename in TARGET_SCHEMA:
        r = samples[filename]
        custom = r.get("customCompositeDisplay") or {}
        custom_note = "; ".join(f"{k}: {'값 있음' if v['nonempty'] else '비어 있음'}" for k, v in custom.items())
        lines.append(
            f"| {filename} | {compact(r['valuePresentColumns'])} | {compact(r['valueEmptyColumns'])} | "
            f"{compact(r['wrongSuspectColumns'])} | {custom_note or '-'} |"
        )
    lines.append("")

    lines.append("## 6. tableMeta 요약")
    lines.append("| 샘플 | extractionSource | expectedColumnKeys | matchedColumnKeys | valueColumnKeys | missingExpectedColumnKeys |")
    lines.append("|---|---|---|---|---|---|")
    for filename in TARGET_SCHEMA:
        meta = samples[filename].get("tableMeta") or {}
        lines.append(
            f"| {filename} | {compact(meta.get('extractionSource'))} | {compact(meta.get('expectedColumnKeys'))} | "
            f"{compact(meta.get('matchedColumnKeys'))} | {compact(meta.get('valueColumnKeys'))} | "
            f"{compact(meta.get('missingExpectedColumnKeys'))} |"
        )
    lines.append("")

    lines.append("## 7. 샘플별 실패 유형")
    lines.append("| 샘플 | 실패 유형 | 원인 추정 | 우선순위 |")
    lines.append("|---|---|---|---|")
    for filename in TARGET_SCHEMA:
        r = samples[filename]
        failures = r["failures"]
        reason = " / ".join(failures)
        if "schema_mismatch" in failures:
            reason += "; manifest key와 목표 key 차이 확인 필요"
        if "api_run_failed" in failures:
            reason += "; 실제 tableRows/tableMeta 수집 실패"
        lines.append(f"| {filename} | {compact(failures)} | {compact(reason, 130)} | {priority_for_failures(failures)} |")
    lines.append("")

    lines.append("## 8. 주요 샘플 상세 분석")
    for filename in TARGET_SCHEMA:
        r = samples[filename]
        s = schema[filename]
        rows = r.get("tableRowsPreview") or []
        dbg = r.get("tableDebugSummary") or {}
        lines.append(f"\n### {filename}")
        lines.append(f"- expected {s['target_count']}개 유지 여부: {'유지' if s['ok'] else '불일치'}")
        if filename == "1.jpg":
            lines.append(f"- rowCount 28 여부: 현재 {r['rowCount']}")
            lines.append("- 누락 row 추정: 현재 rowCount가 28보다 작으면 row_count_short, API 실패 시 판단 불가")
        elif filename == "2.pdf":
            lines.append(f"- rowCount가 기존 2에서 개선되었는지: 현재 {r['rowCount']}, 2 이하이면 개선 확인 불가")
            lines.append("- 소비자단가/공급단가/공급금액/보험No 분리 가능성: meta/valueColumnKeys와 preview 값 기준으로 판단")
        elif filename == "3.pdf":
            lines.append(f"- manufacturingExpiryComposite 상태: {r.get('customCompositeDisplay', {}).get('manufacturingExpiryComposite')}")
        elif filename == "4.pdf":
            lines.append(f"- LotNo/단위/수량/단가/공급가액/세액 상태: 값 있음={compact(r['valuePresentColumns'])}, 비어 있음={compact(r['valueEmptyColumns'])}")
        elif filename == "5.pdf":
            lines.append(f"- rowCount 6 유지 여부: 현재 {r['rowCount']}")
        elif filename == "6.pdf":
            lines.append(f"- rowCount 6 유지 여부: 현재 {r['rowCount']}")
            lines.append(f"- NO/제품코드/제품명/LotNo/유효일자 상태: 값 있음={compact(r['valuePresentColumns'])}")
        elif filename == "7.pdf":
            lines.append(f"- rowCount 1 유지 여부: 현재 {r['rowCount']}")
            lines.append(f"- serialLotComposite 상태: {r.get('customCompositeDisplay', {}).get('serialLotComposite')}")
        lines.append(f"- 값 매핑 상태: 값 있음={compact(r['valuePresentColumns'])}; 비어 있음={compact(r['valueEmptyColumns'])}")
        lines.append(f"- tableDebug 요약: {compact(dbg, 160)}")
        lines.append(f"- tableRows 첫 3개 preview: {compact(rows, 220)}")
        lines.append(f"- 다음 수정 포인트: {next_fix_point(r['failures'])}")
    lines.append("")

    lines.append("## 9. 다음 작업 제안")
    all_failures = {f for r in samples.values() for f in r["failures"]}
    if "api_run_failed" in all_failures:
        decision = "먼저 API 실행 환경/저장 결과 확보가 필요"
    elif "row_count_short" in all_failures or "header_detect_fail" in all_failures:
        decision = "T-6g-fix row grouping 우선"
    elif "value_mapping_wrong" in all_failures or "custom_key_empty" in all_failures:
        decision = "T-6h expected boundary/value mapping 우선"
    elif "composite_display_empty" in all_failures:
        decision = "T-6e-fix4 custom/composite value resolver 우선"
    else:
        decision = "T-7 금액 계열로 이동 가능"
    lines.append(f"- 결론: {decision}")
    lines.append("- 후보: T-6g-fix row grouping 우선")
    lines.append("- 후보: T-6h expected boundary/value mapping 우선")
    lines.append("- 후보: T-6e-fix4 custom/composite value resolver 우선")
    lines.append("- 후보: T-6i table bounds 연동 우선")
    lines.append("- 후보: T-7 금액 계열로 이동 가능")
    lines.append("")

    lines.append("## 10. 최종 결론")
    lines.append(f"- 현재 상태: API {api_success_count}/7 성공, schema 일치 {sum(1 for s in schema.values() if s['ok'])}/7")
    lines.append(f"- 가장 큰 병목: {decision}")
    lines.append("- 다음 작업명: " + ("T-6g-fix" if "row_count_short" in all_failures else "T-6h-check/fix"))
    lines.append("- 수정 대상 예상 파일: ocr-server/extractors/invoice_statement.py, 필요 시 TestWorkspace.tsx display resolver")
    lines.append("")
    lines.append("### 저장 데이터 메모")
    lines.append(f"- 최신 reports: {compact(saved['latest_reports'], 180)}")
    lines.append(f"- tableRows/tableMeta 후보 파일: {compact(saved['saved_table_result_files'], 180)}")
    lines.append(f"- ocr_cache 좌표 포함 여부: {saved['ocr_cache_has_coordinates']}")
    return "\n".join(lines) + "\n"


def next_fix_point(failures: list[str]) -> str:
    if "api_run_failed" in failures:
        return "API 실행 가능 상태 또는 raw tableRows/tableMeta 저장물이 필요"
    if "schema_mismatch" in failures:
        return "manifest required key와 UI custom/composite key 명칭 정합성 확인"
    if "row_count_short" in failures or "header_detect_fail" in failures:
        return "header band 탐지와 row grouping 후보 조건 점검"
    if "value_mapping_wrong" in failures:
        return "expected boundary/value mapping 점검"
    if "custom_key_empty" in failures or "composite_display_empty" in failures:
        return "custom/composite resolver와 source key 채움 상태 점검"
    return "큰 차단 이슈 없음"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-url", default="", help="Existing backend URL, e.g. http://127.0.0.1:8116")
    parser.add_argument("--start-server", action="store_true", help="Start a temporary uvicorn server.")
    parser.add_argument("--port", type=int, default=8116)
    parser.add_argument("--timeout", type=int, default=180)
    args = parser.parse_args()

    server: subprocess.Popen[str] | None = None
    api_url = args.api_url.strip()

    if args.start_server:
        api_url = api_url or f"http://127.0.0.1:{args.port}"
        server = start_server(args.port)
        ok, detail = wait_for_server(api_url)
        if not ok:
            print(f"Temporary server failed to become ready: {detail}")
    elif api_url:
        ok, detail = healthcheck(api_url)
        print(f"API healthcheck: ok={ok}, detail={detail}")
        if not ok:
            print("API is not reachable; report will record collection failure.")

    try:
        data = analyze(api_url or None, timeout=args.timeout)
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        JSON_REPORT_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        REPORT_PATH.write_text(render_report(data), encoding="utf-8")

        print(f"JSON report: {JSON_REPORT_PATH}")
        print(f"Markdown report: {REPORT_PATH}")
        for filename, result in data["samples"].items():
            print(
                f"{filename}: success={result['success']} rowCount={result['rowCount']} "
                f"failures={','.join(result['failures'])}"
            )
    finally:
        if server is not None:
            server.terminate()
            try:
                server.wait(timeout=8)
            except subprocess.TimeoutExpired:
                server.kill()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
