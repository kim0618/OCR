from __future__ import annotations

import hashlib
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


TASK = "CODEX_FRONTEND_CLEANUP_3D1_5_TABLE_VIEW_MODEL_INPUT_FIXTURE_PREP_NO_PROD_MODIFY"
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
INPUT_DIR = FIXTURE_ROOT / "inputs"
OUTPUT_DIR = FIXTURE_ROOT / "invoice_statement"
SYNTHETIC_DIR = FIXTURE_ROOT / "synthetic"
MANIFEST_PATH = FIXTURE_ROOT / "manifest.json"
REPORT_MD = ROOT / "docs" / "FRONTEND_CLEANUP_3D1_5_TABLE_VIEW_MODEL_INPUT_FIXTURE_PREP_20260521.md"
REPORT_JSON = ROOT / "docs" / "FRONTEND_CLEANUP_3D1_5_TABLE_VIEW_MODEL_INPUT_FIXTURE_PREP_20260521.json"
DEFAULT_API_URL = "http://127.0.0.1:9099/ocr/extract"
FALLBACK_PORT = 9142
INVOICE_DATA_DIR = ROOT / "public" / "data" / "testsets" / "invoice_statement"
EMPTY_VALUE = "-"


CASES = [
    {"caseId": "trade_1_1jpg", "templateName": "거래_1", "templateId": "TPL-31D13CF3", "file": "1.jpg", "inputFixture": "inputs/trade_1_1jpg.input.json", "outputFixture": "invoice_statement/trade_1_1jpg.view_model.json", "expectedRowCount": 28, "rowIndexExpected": "excluded"},
    {"caseId": "trade_2_2pdf", "templateName": "거래_2", "templateId": "TPL-5A8C2374", "file": "2.pdf", "inputFixture": "inputs/trade_2_2pdf.input.json", "outputFixture": "invoice_statement/trade_2_2pdf.view_model.json", "expectedRowCount": 13, "rowIndexExpected": "included"},
    {"caseId": "trade_3_3pdf", "templateName": "거래_3", "templateId": "TPL-E4B15A22", "file": "3.pdf", "inputFixture": "inputs/trade_3_3pdf.input.json", "outputFixture": "invoice_statement/trade_3_3pdf.view_model.json", "expectedRowCount": 1, "rowIndexExpected": "included"},
    {"caseId": "trade_4_4pdf", "templateName": "거래_4", "templateId": "TPL-FD07531C", "file": "4.pdf", "inputFixture": "inputs/trade_4_4pdf.input.json", "outputFixture": "invoice_statement/trade_4_4pdf.view_model.json", "expectedRowCount": 1, "rowIndexExpected": "excluded"},
    {"caseId": "trade_5_5pdf", "templateName": "거래_5", "templateId": "TPL-B8936EDE", "file": "5.pdf", "inputFixture": "inputs/trade_5_5pdf.input.json", "outputFixture": "invoice_statement/trade_5_5pdf.view_model.json", "expectedRowCount": 6, "rowIndexExpected": "excluded"},
    {"caseId": "trade_6_6pdf", "templateName": "거래_6", "templateId": "TPL-95328E52", "file": "6.pdf", "inputFixture": "inputs/trade_6_6pdf.input.json", "outputFixture": "invoice_statement/trade_6_6pdf.view_model.json", "expectedRowCount": 6, "rowIndexExpected": "included"},
    {"caseId": "trade_7_7pdf", "templateName": "거래_7", "templateId": "TPL-3AFD383E", "file": "7.pdf", "inputFixture": "inputs/trade_7_7pdf.input.json", "outputFixture": "invoice_statement/trade_7_7pdf.view_model.json", "expectedRowCount": 1, "rowIndexExpected": "excluded"},
]

SYNTHETIC_INPUT_PATH = INPUT_DIR / "synthetic_empty_rows.input.json"
SYNTHETIC_OUTPUT_PATH = SYNTHETIC_DIR / "synthetic_empty_rows.view_model.json"
SYNTHETIC_INPUT = {
    "rows": [],
    "displayCols": [
        {"key": "itemName", "labelKo": "품목명"},
        {"key": "quantity", "labelKo": "수량"},
    ],
    "emptyValue": EMPTY_VALUE,
}
SYNTHETIC_OUTPUT = {
    "columns": [
        {"key": "itemName", "label": "품목명"},
        {"key": "quantity", "label": "수량"},
    ],
    "rows": [],
    "meta": {"rowCount": 0, "columnCount": 2, "hasRows": False, "hasColumns": True},
}

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
# Mirrors _EXPLICIT_COMPOSITE_ALLOWLIST in JS. Keeps manufacturingExpiryComposite filtered.
EXPLICIT_COMPOSITE_ALLOWLIST = {"serialLotComposite"}
FORBIDDEN_KEYS = {
    "align", "width", "style", "isNumeric", "isIndex", "sourceRow",
    "index", "columnIndex", "hasEmptyCells", "tableMeta",
}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def output_hashes() -> dict[str, str]:
    return {case["caseId"]: file_sha256(FIXTURE_ROOT / case["outputFixture"]) for case in CASES}


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
    # 3D-4: explicit set + composite allowlist. Mirrors JS invoiceTableDisplay.ts.
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
        # 3D-4: rowIndex/SUMMARY_KEYS 제외, is_internal_table_key는 EXPLICIT_COMPOSITE_ALLOWLIST 항목만 우회.
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

    # itemCode 5% rule (3D-4: explicit 여부와 무관하게 적용)
    cols = [
        col for col in cols
        if col["key"] not in ITEMCODE_KEYS
        or meaningful_ratio(rows, col["key"]) > 0.05
    ]

    # lot/mfg dup (3D-4: explicit 여부와 무관하게 적용 — trade_1 lotNo dup 보존)
    mfg_key = next((col["key"] for col in cols if col["key"] in MFG_KEYS), None)
    if mfg_key:
        remove = {col["key"] for col in cols if col["key"] in LOT_KEYS and meaningless_or_dup_ratio(rows, col["key"], mfg_key) >= 0.95}
        if remove:
            cols = [col for col in cols if col["key"] not in remove]

    # lot 노이즈 (3D-4: explicit lot 키만 면제 — trade_6 정상 lotNo 표시 보장)
    implicit_lot_keys = [col["key"] for col in cols if col["key"] in LOT_KEYS and not is_explicit(col["key"])]
    if implicit_lot_keys and has_meaningful_value(rows, "itemCode") and not has_meaningful_value(rows, "manufacturingNo"):
        remove_set = set(implicit_lot_keys)
        cols = [col for col in cols if col["key"] not in remove_set]

    # serialNo vs lotNo dup (3D-4: explicit 여부와 무관하게 적용)
    if any(col["key"] == "serialNo" for col in cols) and any(col["key"] == "lotNo" for col in cols):
        if meaningless_or_dup_ratio(rows, "serialNo", "lotNo") >= 0.95:
            cols = [col for col in cols if col["key"] != "serialNo"]

    if should_display_row_index(table_meta):
        cols = [{"key": "rowIndex", "labelKo": resolve_label("rowIndex")}] + cols
    return cols


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


def build_input_fixture(raw: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    document_fields = raw.get("document_fields") if isinstance(raw.get("document_fields"), dict) else {}
    rows_raw = document_fields.get("tableRows")
    if not isinstance(rows_raw, list):
        raise RuntimeError("document_fields.tableRows missing")
    rows = [row for row in rows_raw if isinstance(row, dict)]
    table_meta = document_fields.get("tableMeta") if isinstance(document_fields.get("tableMeta"), dict) else None
    display_cols = build_invoice_preview_cols(table_meta, rows)
    input_fixture = {
        "rows": rows,
        "displayCols": [{"key": col["key"], "labelKo": col["labelKo"]} for col in display_cols],
        "emptyValue": EMPTY_VALUE,
    }
    meta = {
        "rawTableRowCount": len(rows),
        "displayColumnKeys": [col["key"] for col in display_cols],
        "trade3LockedBehavior": extract_locked_behavior(input_fixture),
    }
    return input_fixture, meta


def extract_locked_behavior(input_fixture: dict[str, Any]) -> dict[str, Any]:
    cols = input_fixture.get("displayCols") if isinstance(input_fixture.get("displayCols"), list) else []
    col_keys = [col.get("key") for col in cols if isinstance(col, dict)]
    first_row = input_fixture.get("rows", [{}])[0] if input_fixture.get("rows") else {}
    return {
        "insuranceCodeColumnIncluded": "insuranceCode" in col_keys,
        "amountColumnIncluded": "amount" in col_keys,
        "insuranceCodeValue": normalize_cell(first_row.get("insuranceCode")) if isinstance(first_row, dict) else None,
        "amountValue": normalize_cell(first_row.get("amount")) if isinstance(first_row, dict) else None,
    }


def build_output_from_input(input_fixture: dict[str, Any]) -> dict[str, Any]:
    rows = input_fixture.get("rows") if isinstance(input_fixture.get("rows"), list) else []
    display_cols = input_fixture.get("displayCols") if isinstance(input_fixture.get("displayCols"), list) else []
    empty_value = input_fixture.get("emptyValue", EMPTY_VALUE)
    columns = [{"key": str(col["key"]), "label": str(col["labelKo"])} for col in display_cols if isinstance(col, dict)]
    out_rows = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        cells = []
        for col in display_cols:
            key = str(col["key"])
            value = normalize_cell(row.get(key))
            cells.append({"key": key, "value": value, "displayValue": value or str(empty_value), "isEmpty": value == ""})
        out_rows.append({"cells": cells})
    return {
        "columns": columns,
        "rows": out_rows,
        "meta": {
            "rowCount": len(out_rows),
            "columnCount": len(columns),
            "hasRows": len(out_rows) > 0,
            "hasColumns": len(columns) > 0,
        },
    }


def forbidden_paths(value: Any, path: str = "$", *, input_fixture: bool = False) -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if key in FORBIDDEN_KEYS:
                found.append(child_path)
            if not input_fixture and key == "label" and ".cells[" in path:
                found.append(child_path)
            if key == "rowIndex" and not (input_fixture and path.startswith("$.rows[")):
                found.append(child_path)
            forbidden_child_paths = forbidden_paths(child, child_path, input_fixture=input_fixture)
            found.extend(forbidden_child_paths)
    elif isinstance(value, list):
        for idx, child in enumerate(value):
            found.extend(forbidden_paths(child, f"{path}[{idx}]", input_fixture=input_fixture))
    return found


def validate_pair(input_fixture: dict[str, Any], output_fixture: dict[str, Any], case: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    rows = input_fixture.get("rows") if isinstance(input_fixture.get("rows"), list) else []
    display_cols = input_fixture.get("displayCols") if isinstance(input_fixture.get("displayCols"), list) else []
    columns = output_fixture.get("columns") if isinstance(output_fixture.get("columns"), list) else []
    output_rows = output_fixture.get("rows") if isinstance(output_fixture.get("rows"), list) else []
    meta = output_fixture.get("meta") if isinstance(output_fixture.get("meta"), dict) else {}
    input_col_keys = [col.get("key") for col in display_cols if isinstance(col, dict)]
    input_col_labels = [col.get("labelKo") for col in display_cols if isinstance(col, dict)]
    output_col_keys = [col.get("key") for col in columns if isinstance(col, dict)]
    output_col_labels = [col.get("label") for col in columns if isinstance(col, dict)]
    row_index_actual = "included" if "rowIndex" in input_col_keys else "excluded"

    if set(input_fixture.keys()) != {"rows", "displayCols", "emptyValue"}:
        errors.append(f"input top-level keys mismatch: {sorted(input_fixture.keys())}")
    if input_fixture.get("emptyValue") != EMPTY_VALUE:
        errors.append("emptyValue mismatch")
    if len(rows) != meta.get("rowCount"):
        errors.append("input rows length != output meta.rowCount")
    if len(display_cols) != meta.get("columnCount"):
        errors.append("input displayCols length != output meta.columnCount")
    if input_col_keys != output_col_keys:
        errors.append("displayCols keys != output columns keys")
    if input_col_labels != output_col_labels:
        errors.append("displayCols labels != output column labels")
    if row_index_actual != case["rowIndexExpected"]:
        errors.append(f"rowIndex {row_index_actual} != {case['rowIndexExpected']}")
    if len(rows) != case["expectedRowCount"]:
        errors.append(f"rowCount {len(rows)} != {case['expectedRowCount']}")
    for ri, row in enumerate(output_rows):
        cells = row.get("cells") if isinstance(row, dict) else None
        if not isinstance(cells, list) or len(cells) != len(columns):
            errors.append(f"output row {ri} cells length mismatch")
            continue
        if [cell.get("key") for cell in cells if isinstance(cell, dict)] != output_col_keys:
            errors.append(f"output row {ri} cell order mismatch")
    regenerated = build_output_from_input(input_fixture)
    if regenerated != output_fixture:
        errors.append("helper-contract regeneration != output fixture")
    input_forbidden = forbidden_paths(input_fixture, input_fixture=True)
    output_forbidden = forbidden_paths(output_fixture, input_fixture=False)
    if input_forbidden:
        errors.append(f"input forbidden fields: {input_forbidden[:10]}")
    if output_forbidden:
        errors.append(f"output forbidden fields: {output_forbidden[:10]}")
    return {
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "inputRowCount": len(rows),
        "inputColumnCount": len(display_cols),
        "outputRowCount": meta.get("rowCount"),
        "outputColumnCount": meta.get("columnCount"),
        "rowIndexActual": row_index_actual,
        "columnKeys": input_col_keys,
        "inputForbiddenCount": len(input_forbidden),
        "outputForbiddenCount": len(output_forbidden),
    }


def validate_synthetic() -> dict[str, Any]:
    inp = read_json(SYNTHETIC_INPUT_PATH)
    out = read_json(SYNTHETIC_OUTPUT_PATH)
    base_case = {"caseId": "synthetic_empty_rows", "expectedRowCount": 0, "rowIndexExpected": "excluded"}
    result = validate_pair(inp, out, base_case)
    if out.get("columns") != SYNTHETIC_OUTPUT["columns"]:
        result["errors"].append("synthetic columns not retained")
    if out.get("meta", {}).get("hasRows") is not False or out.get("meta", {}).get("hasColumns") is not True:
        result["errors"].append("synthetic meta hasRows/hasColumns mismatch")
    result["status"] = "PASS" if not result["errors"] else "FAIL"
    return result


def capture_inputs(api_url: str, templates: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    manifest_updates: list[dict[str, Any]] = []
    details: list[dict[str, Any]] = []
    for case in CASES:
        template = template_by_id(templates, case["templateId"])
        input_path = INVOICE_DATA_DIR / case["file"]
        print(f"[capture] {case['caseId']} template={case['templateId']} file={input_path.name}", flush=True)
        try:
            raw, http_meta = post_ocr(api_url, input_path, template)
            input_fixture, capture_meta = build_input_fixture(raw)
            write_json(FIXTURE_ROOT / case["inputFixture"], input_fixture)
            output_fixture = read_json(FIXTURE_ROOT / case["outputFixture"])
            validation = validate_pair(input_fixture, output_fixture, case)
            detail = {
                **case,
                "inputFile": f"invoice_statement/{case['file']}",
                "processing_time": raw.get("processing_time"),
                **http_meta,
                "captureMeta": capture_meta,
                "validation": validation,
                "status": validation["status"],
            }
        except Exception as exc:
            detail = {**case, "inputFile": f"invoice_statement/{case['file']}", "status": "FAIL", "error": repr(exc), "validation": {"errors": [repr(exc)]}}
        validation = detail.get("validation") or {}
        update = {
            "caseId": case["caseId"],
            "inputFixturePath": case["inputFixture"],
            "status": detail["status"],
            "inputRowCount": validation.get("inputRowCount"),
            "inputColumnCount": validation.get("inputColumnCount"),
            "rowIndexActual": validation.get("rowIndexActual"),
        }
        if case["caseId"] == "trade_3_3pdf":
            locked = extract_locked_behavior(read_json(FIXTURE_ROOT / case["inputFixture"])) if (FIXTURE_ROOT / case["inputFixture"]).exists() else {}
            update["lockedCurrentBehavior"] = {
                "policy": "LOCKED_CURRENT_BEHAVIOR",
                "reason": "trade_3 insuranceCode/amount extra columns are current v1 behavior and must not change during helper extraction",
                "extraColumns": ["insuranceCode", "amount"],
                "values": {
                    "insuranceCode": locked.get("insuranceCodeValue"),
                    "amount": locked.get("amountValue"),
                },
                "reference": "docs/CLEAN_JSON_V1_FIXTURE_LOCK_20260521.md",
            }
        manifest_updates.append(update)
        details.append(detail)
    return manifest_updates, details


def update_manifest(input_updates: list[dict[str, Any]], synthetic_validation: dict[str, Any]) -> dict[str, Any]:
    manifest = read_json(MANIFEST_PATH)
    updates_by_case = {item["caseId"]: item for item in input_updates}
    for case in manifest.get("cases", []):
        update = updates_by_case.get(case.get("caseId"))
        if not update:
            continue
        case["inputFixturePath"] = update["inputFixturePath"]
        if case.get("caseId") == "trade_3_3pdf":
            case["lockedCurrentBehavior"] = update["lockedCurrentBehavior"]
            notes = case.get("notes") if isinstance(case.get("notes"), list) else []
            marker = "LOCKED_CURRENT_BEHAVIOR trade_3 insuranceCode=669700020 amount=301,320"
            if marker not in notes:
                notes.append(marker)
            case["notes"] = notes
    synthetic_case = {
        "caseId": "synthetic_empty_rows",
        "templateName": "synthetic_empty_rows",
        "templateId": None,
        "inputFile": None,
        "inputFixturePath": "inputs/synthetic_empty_rows.input.json",
        "fixturePath": "synthetic/synthetic_empty_rows.view_model.json",
        "expectedRowCount": 0,
        "actualRowCount": 0,
        "columnCount": 2,
        "rowIndexExpected": "excluded",
        "rowIndexActual": "excluded",
        "status": synthetic_validation["status"],
        "notes": ["synthetic helper edge case", "no OCR/API required", "empty rows with non-empty displayCols"],
    }
    cases = [case for case in manifest.get("cases", []) if case.get("caseId") != "synthetic_empty_rows"]
    cases.append(synthetic_case)
    manifest["cases"] = cases
    manifest["updatedAt"] = datetime.now().isoformat(timespec="seconds")
    manifest["inputContractRef"] = "BuildStructuredTableViewModelInput"
    write_json(MANIFEST_PATH, manifest)
    return manifest


def md_table(headers: list[str], rows: list[list[Any]]) -> str:
    def cell(value: Any) -> str:
        return str(value if value is not None else "").replace("\n", "<br>").replace("|", "\\|")
    out = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    out.extend("| " + " | ".join(cell(v) for v in row) + " |" for row in rows)
    return "\n".join(out)


def write_reports(summary: dict[str, Any]) -> None:
    write_json(REPORT_JSON, summary)
    rows = [
        [
            d["caseId"], d.get("inputFixture"), (d.get("validation") or {}).get("inputRowCount"),
            (d.get("validation") or {}).get("inputColumnCount"), (d.get("validation") or {}).get("rowIndexActual"),
            d.get("status"),
        ]
        for d in summary["details"]
    ]
    synth = summary["syntheticValidation"]
    trade3 = summary["trade3LockedCurrentBehavior"]
    md = f"""# FRONTEND CLEANUP 3D1.5 TABLE VIEW MODEL INPUT FIXTURE PREP 20260521

## 1. 사용 도구와 모델
- 사용 도구: Codex
- 사용 모델: Codex
- 작업명: `{TASK}`

## 2. 코드 수정 여부
- 운영 코드 수정 없음.
- helper 생성 없음.
- 기존 trade_1~trade_7 output fixture 내용 변경 없음: `{summary['outputFixtureHashStatus']}`

## 3. 생성/수정 파일
- `tmp/codex_table_view_model_input_fixture_prep.py`
- `tmp/fixtures/table_view_model_v1/inputs/*.input.json`
- `tmp/fixtures/table_view_model_v1/synthetic/synthetic_empty_rows.view_model.json`
- `tmp/fixtures/table_view_model_v1/manifest.json`
- `docs/FRONTEND_CLEANUP_3D1_5_TABLE_VIEW_MODEL_INPUT_FIXTURE_PREP_20260521.md`
- `docs/FRONTEND_CLEANUP_3D1_5_TABLE_VIEW_MODEL_INPUT_FIXTURE_PREP_20260521.json`

## 4. Raw Input Fixture 결과
- API URL: `{summary['apiUrl']}`
- API source: `{summary['apiSource']}`
{md_table(['caseId', 'inputFixture', 'rows', 'displayCols', 'rowIndex', 'status'], rows)}

## 5. Synthetic Empty Rows Fixture 결과
- input: `inputs/synthetic_empty_rows.input.json`
- output: `synthetic/synthetic_empty_rows.view_model.json`
- status: `{synth['status']}`
- rows: `{synth['inputRowCount']}`
- columns retained: `{synth['inputColumnCount']}`

## 6. Manifest 보강 결과
- `inputFixturePath` 추가: trade_1~trade_7 + synthetic
- synthetic case 추가: `synthetic_empty_rows`
- trade_3 grep marker 추가: `LOCKED_CURRENT_BEHAVIOR`

## 7. 거래_3 LOCKED_CURRENT_BEHAVIOR 기록
- policy: `{trade3.get('policy')}`
- extraColumns: `{trade3.get('extraColumns')}`
- insuranceCode: `{(trade3.get('values') or {}).get('insuranceCode')}`
- amount: `{(trade3.get('values') or {}).get('amount')}`

## 8. Input/Output Consistency Validation 결과
- overall: `{summary['consistencyStatus']}`
- synthetic: `{synth['status']}`
- forbidden field check: `{summary['forbiddenFieldStatus']}`
- review_log restored: `{summary['reviewLogRestored']}`

## 9. Typecheck/Build 결과
{md_table(['command', 'status', 'exitCode', 'seconds', 'known stderr noise'], [[summary['typecheck']['command'], summary['typecheck']['status'], summary['typecheck']['exitCode'], summary['typecheck']['durationSeconds'], summary['typecheck']['knownStderrNoise']], [summary['build']['command'], summary['build']['status'], summary['build']['exitCode'], summary['build']['durationSeconds'], summary['build']['knownStderrNoise']]])}

## 10. 다음 작업 제안
1. input fixture를 읽는다.
2. `buildStructuredTableViewModel(input)`을 실행한다.
3. expected output fixture를 읽는다.
4. deep equality로 비교한다.
5. trade_1~trade_7 + synthetic_empty_rows 총 8개 PASS를 3D-2 gate로 둔다.

3D-2 성공 기준: table view model fixture 8/8 PASS, Clean JSON JS fixture runner 9/9 PASS, Markdown fixture check 6/6 PASS, typecheck/build PASS.
"""
    REPORT_MD.write_text(md, encoding="utf-8")


def main() -> int:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[start] {TASK}", flush=True)
    before_hashes = output_hashes()
    review_before = REVIEW_LOG.read_bytes() if REVIEW_LOG.exists() else None
    proc: subprocess.Popen[str] | None = None
    try:
        templates = load_templates()
        api_url, proc, api_source = start_backend_if_needed(DEFAULT_API_URL)
        input_updates, details = capture_inputs(api_url, templates)
        write_json(SYNTHETIC_INPUT_PATH, SYNTHETIC_INPUT)
        write_json(SYNTHETIC_OUTPUT_PATH, SYNTHETIC_OUTPUT)
        synthetic_validation = validate_synthetic()
        manifest = update_manifest(input_updates, synthetic_validation)
        after_hashes = output_hashes()
        output_hash_status = "PASS" if before_hashes == after_hashes else "FAIL"
        consistency_status = "PASS" if all((d.get("validation") or {}).get("status") == "PASS" for d in details) and synthetic_validation["status"] == "PASS" else "FAIL"
        forbidden_status = "PASS" if all((d.get("validation") or {}).get("inputForbiddenCount") == 0 and (d.get("validation") or {}).get("outputForbiddenCount") == 0 for d in details) and synthetic_validation.get("inputForbiddenCount") == 0 and synthetic_validation.get("outputForbiddenCount") == 0 else "FAIL"
        trade3_case = next(case for case in manifest["cases"] if case.get("caseId") == "trade_3_3pdf")
        locked = trade3_case.get("lockedCurrentBehavior") or {}
        locked_status = "PASS" if locked.get("policy") == "LOCKED_CURRENT_BEHAVIOR" and (locked.get("values") or {}).get("insuranceCode") == "669700020" and (locked.get("values") or {}).get("amount") == "301,320" else "FAIL"
        print(f"[validate] consistency {consistency_status}", flush=True)
        print(f"[validate] output fixture hashes {output_hash_status}", flush=True)
        print(f"[validate] locked marker {locked_status}", flush=True)
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
        status = "PASS" if (
            output_hash_status == "PASS"
            and consistency_status == "PASS"
            and forbidden_status == "PASS"
            and locked_status == "PASS"
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
            "outputFixtureHashStatus": output_hash_status,
            "outputFixtureHashesBefore": before_hashes,
            "outputFixtureHashesAfter": after_hashes,
            "manifest": manifest,
            "details": details,
            "syntheticValidation": synthetic_validation,
            "consistencyStatus": consistency_status,
            "forbiddenFieldStatus": forbidden_status,
            "lockedMarkerStatus": locked_status,
            "trade3LockedCurrentBehavior": locked,
            "typecheck": typecheck,
            "build": build,
            "reviewLogRestored": review_restored,
            "next3D2RunnerFlow": [
                "read input fixture",
                "run buildStructuredTableViewModel(input)",
                "read expected output fixture",
                "compare by deep equality",
                "require trade_1~trade_7 + synthetic_empty_rows 8/8 PASS",
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
