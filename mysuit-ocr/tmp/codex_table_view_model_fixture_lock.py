from __future__ import annotations

import json
import socket
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import requests
except Exception as exc:  # pragma: no cover
    requests = None
    REQUESTS_IMPORT_ERROR = exc
else:
    REQUESTS_IMPORT_ERROR = None


TASK = "CODEX_FRONTEND_CLEANUP_3D1_TABLE_VIEW_MODEL_FIXTURE_LOCK_NO_PROD_MODIFY"
ROOT = Path(__file__).resolve().parents[1]
OCR_ROOT = ROOT.parent / "ocr-server"
LOG_DIR = OCR_ROOT / "logs"
OUT_LOG = LOG_DIR / f"codex_{TASK}.out.log"
ERR_LOG = LOG_DIR / f"codex_{TASK}.err.log"
SERVER_OUT_LOG = LOG_DIR / f"codex_{TASK}.server.out.log"
SERVER_ERR_LOG = LOG_DIR / f"codex_{TASK}.server.err.log"
TEMPLATES_JSON = OCR_ROOT / "data" / "templates.json"
REVIEW_LOG = OCR_ROOT / "data" / "review_log.jsonl"
FIXTURE_ROOT = ROOT / "tmp" / "fixtures" / "table_view_model_v1"
INVOICE_FIXTURE_DIR = FIXTURE_ROOT / "invoice_statement"
MANIFEST_PATH = FIXTURE_ROOT / "manifest.json"
REPORT_MD = ROOT / "docs" / "FRONTEND_CLEANUP_3D1_TABLE_VIEW_MODEL_FIXTURE_LOCK_20260521.md"
REPORT_JSON = ROOT / "docs" / "FRONTEND_CLEANUP_3D1_TABLE_VIEW_MODEL_FIXTURE_LOCK_20260521.json"
DEFAULT_API_URL = "http://127.0.0.1:9099/ocr/extract"
FALLBACK_PORT = 9141
INVOICE_DATA_DIR = ROOT / "public" / "data" / "testsets" / "invoice_statement"


CASES = [
    {"caseId": "trade_1_1jpg", "templateName": "거래_1", "templateId": "TPL-31D13CF3", "file": "1.jpg", "fixture": "invoice_statement/trade_1_1jpg.view_model.json", "expectedRowCount": 28, "rowIndexExpected": "excluded"},
    {"caseId": "trade_2_2pdf", "templateName": "거래_2", "templateId": "TPL-5A8C2374", "file": "2.pdf", "fixture": "invoice_statement/trade_2_2pdf.view_model.json", "expectedRowCount": 13, "rowIndexExpected": "included"},
    {"caseId": "trade_3_3pdf", "templateName": "거래_3", "templateId": "TPL-E4B15A22", "file": "3.pdf", "fixture": "invoice_statement/trade_3_3pdf.view_model.json", "expectedRowCount": 1, "rowIndexExpected": "included"},
    {"caseId": "trade_4_4pdf", "templateName": "거래_4", "templateId": "TPL-FD07531C", "file": "4.pdf", "fixture": "invoice_statement/trade_4_4pdf.view_model.json", "expectedRowCount": 1, "rowIndexExpected": "excluded"},
    {"caseId": "trade_5_5pdf", "templateName": "거래_5", "templateId": "TPL-B8936EDE", "file": "5.pdf", "fixture": "invoice_statement/trade_5_5pdf.view_model.json", "expectedRowCount": 6, "rowIndexExpected": "excluded"},
    {"caseId": "trade_6_6pdf", "templateName": "거래_6", "templateId": "TPL-95328E52", "file": "6.pdf", "fixture": "invoice_statement/trade_6_6pdf.view_model.json", "expectedRowCount": 6, "rowIndexExpected": "included"},
    {"caseId": "trade_7_7pdf", "templateName": "거래_7", "templateId": "TPL-3AFD383E", "file": "7.pdf", "fixture": "invoice_statement/trade_7_7pdf.view_model.json", "expectedRowCount": 1, "rowIndexExpected": "excluded"},
]

INVOICE_TABLE_COL_PRIORITY = [
    "itemCode", "itemName", "spec", "lotNo", "serialNo", "manufacturingNo", "expiryDate",
    "quantity", "unit", "consumerUnitPrice", "supplyUnitPrice", "unitPrice",
    "supplyAmount", "taxAmount", "amount", "totalAmount", "manufacturer",
    "insuranceCode", "remark",
]
INVOICE_COL_LABEL_MAP = {
    "rowIndex": "번호",
    "itemCode": "품목코드",
    "itemName": "품목명",
    "spec": "규격",
    "lotNo": "LOT/제조번호",
    "serialNo": "Serial",
    "manufacturingNo": "제조번호",
    "expiryDate": "유효기간",
    "quantity": "수량",
    "unit": "단위",
    "consumerUnitPrice": "소비자단가",
    "supplyUnitPrice": "공급단가",
    "unitPrice": "단가",
    "supplyAmount": "공급금액",
    "taxAmount": "세액",
    "amount": "금액",
    "totalAmount": "합계금액",
    "manufacturer": "제조사",
    "insuranceCode": "보험No",
    "remark": "비고",
    "manufacturingExpiry": "제조번호/유효기간",
    "manufacturingExpiryComposite": "제조번호/유효기간",
    "serialLot": "시리얼 로트No.",
    "serialLotComposite": "시리얼 로트No.",
}
INTERNAL_KEYS = {
    "_rawText", "rawText", "_source", "source", "manufacturingExpiryComposite",
    "serialLotComposite", "rowIndex", "lineIndex", "_confidence", "confidence",
    "bbox", "extractionSource",
}
LOT_KEYS = {"lotNo", "serialLot", "lot", "lotNumber"}
MFG_KEYS = {"manufacturingNo", "manufactureNo", "mfgNo"}
ITEMCODE_KEYS = {"itemCode", "productCode"}
MEANINGLESS = {"", "-", "n/a", "null", "none", "undefined"}
# 3D-4 INVOICE-TABLE-DISPLAY-POLICY-FIX: summary keys never shown as row column.
# Mirrors src/lib/invoiceTableDisplay.ts _SUMMARY_KEYS.
SUMMARY_KEYS = {"totalAmount"}
# 3D-4: composite keys that may bypass is_internal_table_key when explicit.
EXPLICIT_COMPOSITE_ALLOWLIST = {"serialLotComposite"}
EXCLUDED_FIELD_NAMES = {
    "align", "width", "isNumeric", "isIndex", "index", "rowIndex", "columnIndex",
    "sourceRow", "hasEmptyCells", "tableMeta",
}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_command(args: list[str], cwd: Path, timeout: int = 240) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        proc = subprocess.run(args, cwd=str(cwd), text=True, encoding="utf-8", errors="replace", capture_output=True, timeout=timeout, shell=False)
        return {
            "command": " ".join(args),
            "exitCode": proc.returncode,
            "status": "PASS" if proc.returncode == 0 else "FAIL",
            "durationSeconds": round(time.perf_counter() - started, 3),
            "stdoutTail": proc.stdout[-4000:],
            "stderrTail": proc.stderr[-4000:],
            "knownStderrNoise": "nextVitals is not iterable" in proc.stderr,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "command": " ".join(args),
            "exitCode": None,
            "status": "TIMEOUT",
            "durationSeconds": round(time.perf_counter() - started, 3),
            "stdoutTail": (exc.stdout or "")[-4000:] if isinstance(exc.stdout, str) else "",
            "stderrTail": (exc.stderr or "")[-4000:] if isinstance(exc.stderr, str) else "",
            "knownStderrNoise": False,
        }


def load_templates() -> list[dict[str, Any]]:
    return read_json(TEMPLATES_JSON)


def template_by_id(templates: list[dict[str, Any]], template_id: str) -> dict[str, Any]:
    for item in templates:
        if str(item.get("template_id")) == template_id:
            return item
    raise RuntimeError(f"template not found: {template_id}")


def api_health(api_url: str, timeout: float = 2.0) -> bool:
    if requests is None:
        return False
    base = api_url.rsplit("/", 2)[0]
    try:
        res = requests.get(f"{base}/templates", timeout=timeout)
        return res.status_code < 500
    except Exception:
        return False


def wait_for_api(api_url: str, timeout: int = 60) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if api_health(api_url):
            return True
        time.sleep(1)
    return False


def is_port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex(("127.0.0.1", port)) != 0


def start_backend_if_needed(api_url: str) -> tuple[str, subprocess.Popen[str] | None, str]:
    if api_health(api_url):
        return api_url, None, "existing_9099"
    fallback = f"http://127.0.0.1:{FALLBACK_PORT}/ocr/extract"
    if not is_port_free(FALLBACK_PORT) and wait_for_api(fallback, timeout=5):
        return fallback, None, "existing_fallback_port"
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    python_exe = OCR_ROOT / ".venv" / "Scripts" / "python.exe"
    cmd = [str(python_exe if python_exe.exists() else sys.executable), "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", str(FALLBACK_PORT)]
    out_f = SERVER_OUT_LOG.open("w", encoding="utf-8", errors="replace")
    err_f = SERVER_ERR_LOG.open("w", encoding="utf-8", errors="replace")
    proc = subprocess.Popen(cmd, cwd=str(OCR_ROOT), stdout=out_f, stderr=err_f, text=True)
    proc._codex_log_handles = (out_f, err_f)  # type: ignore[attr-defined]
    if not wait_for_api(fallback):
        stop_backend(proc)
        raise RuntimeError(f"Backend did not become ready on {fallback}")
    return fallback, proc, "started_fallback_port"


def stop_backend(proc: subprocess.Popen[str] | None) -> None:
    if proc is None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=10)
    for handle in getattr(proc, "_codex_log_handles", ()):
        try:
            handle.close()
        except Exception:
            pass


def normalize_cell(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    for dash in ["\u2010", "\u2011", "\u2012", "\u2013", "\u2014", "\u2212"]:
        text = text.replace(dash, "-")
    return text.strip()


def is_meaningless(value: str) -> bool:
    return value.lower() in MEANINGLESS


def has_meaningful_value(rows: list[dict[str, Any]], key: str) -> bool:
    return any(not is_meaningless(normalize_cell(row.get(key))) for row in rows)


def meaningful_ratio(rows: list[dict[str, Any]], key: str) -> float:
    if not rows:
        return 0.0
    return sum(1 for row in rows if not is_meaningless(normalize_cell(row.get(key)))) / len(rows)


def is_internal_table_key(key: str) -> bool:
    return key in INTERNAL_KEYS or key.startswith("_") or "Composite" in key or "Debug" in key or "Warning" in key


def is_lot_dup_of_mfg(lot: str, mfg: str) -> bool:
    if lot == mfg:
        return True
    if len(lot) < 4 or not mfg:
        return False
    return mfg.startswith(lot) or mfg.startswith("C" + lot) or mfg.startswith("c" + lot)


def meaningless_or_dup_ratio(rows: list[dict[str, Any]], key1: str, key2: str) -> float:
    if not rows:
        return 0.0
    count = 0
    for row in rows:
        v1 = normalize_cell(row.get(key1))
        v2 = normalize_cell(row.get(key2))
        if is_meaningless(v1) or is_lot_dup_of_mfg(v1, v2):
            count += 1
    return count / len(rows)


def should_display_row_index(table_meta: dict[str, Any] | None, external_expected: list[str] | None = None) -> bool:
    if external_expected and "rowIndex" in external_expected:
        return True
    exp = (table_meta or {}).get("expectedColumnKeys")
    return isinstance(exp, list) and any(str(k) == "rowIndex" for k in exp)


def build_invoice_preview_cols(table_meta: dict[str, Any] | None, rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    if not rows:
        return []
    table_meta = table_meta or {}
    explicitly_expected: set[str] = set()
    expected_from_meta = table_meta.get("expectedColumnKeys")
    if isinstance(expected_from_meta, list):
        for k in expected_from_meta:
            explicitly_expected.add(str(k))

    def is_explicit(key: str) -> bool:
        return key in explicitly_expected

    def is_allowed_composite(key: str) -> bool:
        return key in EXPLICIT_COMPOSITE_ALLOWLIST and key in explicitly_expected

    candidate_keys: list[str] = []
    exp = table_meta.get("expectedColumnKeys")
    if isinstance(exp, list) and exp:
        candidate_keys = [
            str(k) for k in exp
            if str(k) != "rowIndex"
            and str(k) not in SUMMARY_KEYS
            and (not is_internal_table_key(str(k)) or is_allowed_composite(str(k)))
        ]
    if not candidate_keys:
        det = table_meta.get("columns")
        if isinstance(det, list) and det:
            candidate_keys = [str(k) for k in det if str(k) != "rowIndex" and str(k) not in SUMMARY_KEYS and not is_internal_table_key(str(k))]
    if not candidate_keys:
        candidate_keys = [k for k in INVOICE_TABLE_COL_PRIORITY if k not in SUMMARY_KEYS]

    col_labels = table_meta.get("columnLabels")
    if not isinstance(col_labels, dict):
        col_labels = {}

    def resolve_label(key: str) -> str:
        return str(col_labels.get(key) or INVOICE_COL_LABEL_MAP.get(key) or key)

    cols = [{"key": key, "labelKo": resolve_label(key)} for key in candidate_keys if has_meaningful_value(rows, key)]
    cols = [col for col in cols if col["key"] not in ITEMCODE_KEYS or meaningful_ratio(rows, col["key"]) > 0.05]

    mfg_key = next((col["key"] for col in cols if col["key"] in MFG_KEYS), None)
    if mfg_key:
        remove = {col["key"] for col in cols if col["key"] in LOT_KEYS and meaningless_or_dup_ratio(rows, col["key"], mfg_key) >= 0.95}
        if remove:
            cols = [col for col in cols if col["key"] not in remove]

    implicit_lot_keys = [col["key"] for col in cols if col["key"] in LOT_KEYS and not is_explicit(col["key"])]
    if implicit_lot_keys and has_meaningful_value(rows, "itemCode") and not has_meaningful_value(rows, "manufacturingNo"):
        remove_set = set(implicit_lot_keys)
        cols = [col for col in cols if col["key"] not in remove_set]

    if any(col["key"] == "serialNo" for col in cols) and any(col["key"] == "lotNo" for col in cols):
        if meaningless_or_dup_ratio(rows, "serialNo", "lotNo") >= 0.95:
            cols = [col for col in cols if col["key"] != "serialNo"]

    if should_display_row_index(table_meta):
        cols = [{"key": "rowIndex", "labelKo": resolve_label("rowIndex")}] + cols
    return cols


def build_view_model(raw: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    document_fields = raw.get("document_fields") if isinstance(raw.get("document_fields"), dict) else {}
    rows_raw = document_fields.get("tableRows")
    if not isinstance(rows_raw, list) or not rows_raw:
        raise RuntimeError("document_fields.tableRows missing or empty")
    rows = [row for row in rows_raw if isinstance(row, dict)]
    table_meta = document_fields.get("tableMeta") if isinstance(document_fields.get("tableMeta"), dict) else None
    display_cols = build_invoice_preview_cols(table_meta, rows)
    columns = [{"key": col["key"], "label": col["labelKo"]} for col in display_cols]
    view_rows = []
    for row in rows:
        cells = []
        for col in display_cols:
            value = normalize_cell(row.get(col["key"]))
            cells.append({
                "key": col["key"],
                "value": value,
                "displayValue": value or "-",
                "isEmpty": value == "",
            })
        view_rows.append({"cells": cells})
    view_model = {
        "columns": columns,
        "rows": view_rows,
        "meta": {
            "rowCount": len(view_rows),
            "columnCount": len(columns),
            "hasRows": len(view_rows) > 0,
            "hasColumns": len(columns) > 0,
        },
    }
    meta = {
        "rawTableRowCount": len(rows),
        "columnKeys": [col["key"] for col in columns],
        "tableMetaExpectedColumnKeys": table_meta.get("expectedColumnKeys") if table_meta else None,
        "tableMetaColumns": table_meta.get("columns") if table_meta else None,
        "trade3LockedBehavior": {
            "insuranceCodeColumnIncluded": any(col["key"] == "insuranceCode" for col in columns),
            "amountColumnIncluded": any(col["key"] == "amount" for col in columns),
            "insuranceCodeValue": view_rows[0]["cells"][[col["key"] for col in columns].index("insuranceCode")]["value"] if view_rows and any(col["key"] == "insuranceCode" for col in columns) else None,
            "amountValue": view_rows[0]["cells"][[col["key"] for col in columns].index("amount")]["value"] if view_rows and any(col["key"] == "amount" for col in columns) else None,
        },
    }
    return view_model, meta


def post_ocr(api_url: str, input_path: Path, template: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    if requests is None:
        raise RuntimeError(f"requests import failed: {REQUESTS_IMPORT_ERROR}")
    template_json = template.get("template_json") or {}
    data: dict[str, str] = {"template_id": str(template.get("template_id") or ""), "model_id": "paddleocr"}
    regions = template_json.get("regions")
    if isinstance(regions, list) and regions:
        data["regions"] = json.dumps(regions, ensure_ascii=False)
    data["documentType"] = "invoice_statement"
    started = time.perf_counter()
    with input_path.open("rb") as file_handle:
        res = requests.post(api_url, data=data, files={"file": (input_path.name, file_handle)}, timeout=240)
    wall = round(time.perf_counter() - started, 3)
    response_size = len(res.content)
    res.raise_for_status()
    return res.json(), {"wallClockSeconds": wall, "responseSizeBytes": response_size, "payloadKeys": sorted(data.keys())}


def find_excluded_paths(value: Any, path: str = "$") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if key in EXCLUDED_FIELD_NAMES:
                found.append(child_path)
            if key == "label" and ".cells[" in path:
                found.append(child_path)
            found.extend(find_excluded_paths(child, child_path))
    elif isinstance(value, list):
        for idx, child in enumerate(value):
            found.extend(find_excluded_paths(child, f"{path}[{idx}]"))
    return found


def validate_view_model(vm: dict[str, Any], case: dict[str, Any]) -> dict[str, Any]:
    columns = vm.get("columns") if isinstance(vm.get("columns"), list) else []
    rows = vm.get("rows") if isinstance(vm.get("rows"), list) else []
    meta = vm.get("meta") if isinstance(vm.get("meta"), dict) else {}
    column_keys = [col.get("key") for col in columns if isinstance(col, dict)]
    row_index_actual = "included" if "rowIndex" in column_keys else "excluded"
    errors: list[str] = []
    if len(rows) != case["expectedRowCount"]:
        errors.append(f"rowCount {len(rows)} != {case['expectedRowCount']}")
    if meta.get("rowCount") != len(rows):
        errors.append("meta.rowCount mismatch")
    if meta.get("columnCount") != len(columns):
        errors.append("meta.columnCount mismatch")
    if not columns:
        errors.append("columns empty")
    if row_index_actual != case["rowIndexExpected"]:
        errors.append(f"rowIndex {row_index_actual} != {case['rowIndexExpected']}")
    for ri, row in enumerate(rows):
        cells = row.get("cells") if isinstance(row, dict) else None
        if not isinstance(cells, list) or len(cells) != len(columns):
            errors.append(f"row {ri} cells length mismatch")
            continue
        cell_keys = [cell.get("key") for cell in cells if isinstance(cell, dict)]
        if cell_keys != column_keys:
            errors.append(f"row {ri} cell order mismatch")
        for cell in cells:
            if not isinstance(cell, dict):
                errors.append(f"row {ri} non-object cell")
                continue
            value = cell.get("value")
            display = cell.get("displayValue")
            empty = cell.get("isEmpty")
            if not isinstance(value, str) or not isinstance(display, str) or not isinstance(empty, bool):
                errors.append(f"row {ri} cell scalar type mismatch")
            if empty != (value == ""):
                errors.append(f"row {ri} isEmpty/value mismatch")
    excluded = find_excluded_paths(vm)
    if excluded:
        errors.append(f"excluded fields found: {excluded[:10]}")
    return {
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "actualRowCount": len(rows),
        "columnCount": len(columns),
        "columnKeys": column_keys,
        "rowIndexActual": row_index_actual,
        "excludedFieldCount": len(excluded),
    }


def capture_cases(api_url: str, templates: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    manifest_cases: list[dict[str, Any]] = []
    details: list[dict[str, Any]] = []
    for case in CASES:
        template = template_by_id(templates, case["templateId"])
        input_path = INVOICE_DATA_DIR / case["file"]
        print(f"[capture] {case['caseId']} template={case['templateId']} file={input_path.name}", flush=True)
        try:
            raw, http_meta = post_ocr(api_url, input_path, template)
            vm, capture_meta = build_view_model(raw)
            out_path = FIXTURE_ROOT / case["fixture"]
            write_json(out_path, vm)
            reread = read_json(out_path)
            validation = validate_view_model(reread, case)
            detail = {
                **case,
                "inputFile": f"invoice_statement/{case['file']}",
                "fixturePath": case["fixture"],
                "processing_time": raw.get("processing_time"),
                **http_meta,
                "captureMeta": capture_meta,
                "validation": validation,
                "status": validation["status"],
            }
        except Exception as exc:
            detail = {
                **case,
                "inputFile": f"invoice_statement/{case['file']}",
                "fixturePath": case["fixture"],
                "status": "FAIL",
                "error": repr(exc),
            }
        validation = detail.get("validation") or {}
        notes: list[str] = []
        if case["caseId"] == "trade_3_3pdf":
            locked = ((detail.get("captureMeta") or {}).get("trade3LockedBehavior") or {})
            notes.append(f"locked current behavior: insuranceCode included={locked.get('insuranceCodeColumnIncluded')}, amount included={locked.get('amountColumnIncluded')}")
        if validation.get("errors"):
            notes.extend(validation["errors"])
        manifest_cases.append({
            "caseId": case["caseId"],
            "templateName": case["templateName"],
            "templateId": case["templateId"],
            "inputFile": detail.get("inputFile"),
            "fixturePath": detail.get("fixturePath"),
            "expectedRowCount": case["expectedRowCount"],
            "actualRowCount": validation.get("actualRowCount"),
            "columnCount": validation.get("columnCount"),
            "rowIndexExpected": case["rowIndexExpected"],
            "rowIndexActual": validation.get("rowIndexActual"),
            "status": detail.get("status"),
            "notes": notes,
        })
        details.append(detail)
    return manifest_cases, details


def validate_all_from_disk() -> dict[str, Any]:
    case_results = []
    for case in CASES:
        path = FIXTURE_ROOT / case["fixture"]
        if not path.exists():
            case_results.append({"caseId": case["caseId"], "status": "FAIL", "errors": ["missing fixture"]})
            continue
        case_results.append({"caseId": case["caseId"], **validate_view_model(read_json(path), case)})
    return {
        "status": "PASS" if all(item["status"] == "PASS" for item in case_results) and len(case_results) == 7 else "FAIL",
        "fixtureCount": sum(1 for case in CASES if (FIXTURE_ROOT / case["fixture"]).exists()),
        "cases": case_results,
    }


def md_table(headers: list[str], rows: list[list[Any]]) -> str:
    def cell(value: Any) -> str:
        return str(value if value is not None else "").replace("\n", "<br>").replace("|", "\\|")
    out = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    out.extend("| " + " | ".join(cell(v) for v in row) + " |" for row in rows)
    return "\n".join(out)


def write_reports(summary: dict[str, Any]) -> None:
    write_json(REPORT_JSON, summary)
    manifest_cases = summary["manifest"]["cases"]
    rows = [
        [
            c["caseId"], c["templateId"], c["actualRowCount"], c["expectedRowCount"],
            c["columnCount"], c["rowIndexActual"], c["rowIndexExpected"], c["status"],
        ]
        for c in manifest_cases
    ]
    trade3 = summary["trade3LockedBehavior"]
    md = f"""# FRONTEND CLEANUP 3D1 TABLE VIEW MODEL FIXTURE LOCK 20260521

## 1. 사용 도구와 모델
- 사용 도구: Codex
- 사용 모델: Codex
- 작업명: `{TASK}`

## 2. 코드 수정 여부
- 운영 코드 수정 없음.
- helper 생성 없음.
- 금지 파일(`OcrResultPanel.tsx`, `cleanJsonBuilder.ts`, `markdownReportBuilder.ts`, `ocrResultFormatters.ts`, `invoiceTableDisplay.ts`, `TestWorkspace.tsx`) 수정 없음.

## 3. 생성 파일
- `tmp/codex_table_view_model_fixture_lock.py`
- `tmp/fixtures/table_view_model_v1/manifest.json`
- `tmp/fixtures/table_view_model_v1/invoice_statement/*.view_model.json`
- `docs/FRONTEND_CLEANUP_3D1_TABLE_VIEW_MODEL_FIXTURE_LOCK_20260521.md`
- `docs/FRONTEND_CLEANUP_3D1_TABLE_VIEW_MODEL_FIXTURE_LOCK_20260521.json`

## 4. Fixture 대상
- 대상 데이터셋: `public/data/testsets/invoice_statement`
- API URL: `{summary['apiUrl']}`
- API source: `{summary['apiSource']}`

## 5. Fixture Contract 준수 결과
- 전체 상태: `{summary['status']}`
- disk validation: `{summary['diskValidation']['status']}`
- fixture count: `{summary['diskValidation']['fixtureCount']}/7`
- excluded field validation: PASS when each case `excludedFieldCount == 0`
- fixture body는 trimmed `StructuredTableViewModel`만 포함.

## 6. rowCount / columnCount 결과
{md_table(['caseId', 'templateId', 'actualRows', 'expectedRows', 'columnCount', 'rowIndexActual', 'rowIndexExpected', 'status'], rows)}

## 7. rowIndex 정책 결과
- included expected: 거래_2, 거래_3, 거래_6
- excluded expected: 거래_1, 거래_4, 거래_5, 거래_7
- 결과: `{summary['rowIndexPolicyStatus']}`

## 8. 거래_3 locked behavior 기록
- insuranceCode column included: `{trade3.get('insuranceCodeColumnIncluded')}`
- insuranceCode value: `{trade3.get('insuranceCodeValue')}`
- amount column included: `{trade3.get('amountColumnIncluded')}`
- amount value: `{trade3.get('amountValue')}`

## 9. typecheck/build 결과
{md_table(['command', 'status', 'exitCode', 'seconds', 'known stderr noise'], [[summary['typecheck']['command'], summary['typecheck']['status'], summary['typecheck']['exitCode'], summary['typecheck']['durationSeconds'], summary['typecheck']['knownStderrNoise']], [summary['build']['command'], summary['build']['status'], summary['build']['exitCode'], summary['build']['durationSeconds'], summary['build']['knownStderrNoise']]])}

## 10. 다음 작업 제안
- 3D-2에서 `buildStructuredTableViewModel` helper direct output과 이 fixture를 deep equality로 비교한다.
- Clean JSON JS fixture runner 9/9 PASS, Markdown fixture check 6/6 PASS, typecheck/build PASS를 같은 3D-2 gate로 둔다.
- OcrResultPanel 적용은 helper direct runner가 7/7 PASS한 뒤 별도 단계로 두는 것을 추천한다.
"""
    REPORT_MD.write_text(md, encoding="utf-8")


def main() -> int:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[start] {TASK}", flush=True)
    review_before = REVIEW_LOG.read_bytes() if REVIEW_LOG.exists() else None
    proc: subprocess.Popen[str] | None = None
    api_url = DEFAULT_API_URL
    api_source = "unknown"
    try:
        templates = load_templates()
        api_url, proc, api_source = start_backend_if_needed(DEFAULT_API_URL)
        manifest_cases, details = capture_cases(api_url, templates)
        disk_validation = validate_all_from_disk()
        manifest = {
            "version": "table_view_model_v1",
            "createdAt": datetime.now().isoformat(timespec="seconds"),
            "contractRef": [
                "docs/FRONTEND_CLEANUP_3D0_TABLE_VIEW_MODEL_CONTRACT_PRECHECK_20260521.md",
                "docs/FRONTEND_CLEANUP_3D0_2_TABLE_VIEW_MODEL_CONTRACT_TRIM_PRECHECK_20260521.md",
            ],
            "cases": manifest_cases,
        }
        write_json(MANIFEST_PATH, manifest)
        print("[validate] disk fixture validation " + disk_validation["status"], flush=True)
        print("[typecheck] npm run typecheck", flush=True)
        typecheck = run_command(["npm.cmd", "run", "typecheck"], ROOT, timeout=180)
        print(f"[typecheck] {typecheck['status']} exit={typecheck['exitCode']}", flush=True)
        print("[build] npm run build", flush=True)
        build = run_command(["npm.cmd", "run", "build"], ROOT, timeout=300)
        print(f"[build] {build['status']} exit={build['exitCode']}", flush=True)
        review_after_capture = REVIEW_LOG.read_bytes() if REVIEW_LOG.exists() else None
        review_restored = review_after_capture == review_before
        if review_after_capture != review_before:
            if review_before is None:
                REVIEW_LOG.unlink(missing_ok=True)
            else:
                REVIEW_LOG.write_bytes(review_before)
            review_restored = True
            print("[review_log] restored pre-run bytes", flush=True)
        trade3_detail = next((d for d in details if d.get("caseId") == "trade_3_3pdf"), {})
        trade3_locked = ((trade3_detail.get("captureMeta") or {}).get("trade3LockedBehavior") or {})
        row_index_policy_status = "PASS" if all(c.get("rowIndexActual") == c.get("rowIndexExpected") for c in manifest_cases) else "FAIL"
        status = "PASS" if (
            all(c.get("status") == "PASS" for c in manifest_cases)
            and disk_validation["status"] == "PASS"
            and row_index_policy_status == "PASS"
            and typecheck["status"] == "PASS"
            and build["status"] == "PASS"
            and review_restored
        ) else "FAIL"
        summary = {
            "task": TASK,
            "tool": "Codex",
            "model": "Codex",
            "status": status,
            "apiUrl": api_url,
            "apiSource": api_source,
            "logs": {"stdout": str(OUT_LOG), "stderr": str(ERR_LOG)},
            "codeModified": False,
            "helperCreated": False,
            "manifest": manifest,
            "details": details,
            "diskValidation": disk_validation,
            "rowIndexPolicyStatus": row_index_policy_status,
            "trade3LockedBehavior": trade3_locked,
            "typecheck": typecheck,
            "build": build,
            "reviewLogRestored": review_restored,
            "next3D2Criteria": [
                "helper direct output and fixture deep equality",
                "trade_1~trade_7 7/7 PASS",
                "Clean JSON JS fixture runner 9/9 PASS",
                "Markdown fixture check 6/6 PASS",
                "typecheck/build PASS",
                "recommend OcrResultPanel adoption as a separate step after helper direct runner passes",
            ],
        }
        write_reports(summary)
        print(f"[done] {status}", flush=True)
        return 0 if status == "PASS" else 1
    finally:
        stop_backend(proc)
        review_after = REVIEW_LOG.read_bytes() if REVIEW_LOG.exists() else None
        if review_after != review_before:
            if review_before is None:
                REVIEW_LOG.unlink(missing_ok=True)
            else:
                REVIEW_LOG.write_bytes(review_before)
            print("[review_log] restored in finally", flush=True)


if __name__ == "__main__":
    raise SystemExit(main())
