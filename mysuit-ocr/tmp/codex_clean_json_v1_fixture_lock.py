from __future__ import annotations

import argparse
import json
import os
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


TASK = "CODEX_CLEAN_JSON_V1_FIXTURE_LOCK_NO_PROD_MODIFY"
ROOT = Path(__file__).resolve().parents[1]
OCR_ROOT = ROOT.parent / "ocr-server"
LOG_DIR = OCR_ROOT / "logs"
TEMPLATES_JSON = OCR_ROOT / "data" / "templates.json"
CONTRACT_MD = ROOT / "docs" / "CLEAN_JSON_CONTRACT_20260521.md"
CONTRACT_JSON = ROOT / "docs" / "CLEAN_JSON_CONTRACT_20260521.json"
FIXTURE_ROOT = ROOT / "tmp" / "fixtures" / "clean_json_v1"
INVOICE_FIXTURE_DIR = FIXTURE_ROOT / "invoice_statement"
RECEIPT_FIXTURE_DIR = FIXTURE_ROOT / "receipt"
MANIFEST_PATH = FIXTURE_ROOT / "manifest.json"
REPORT_MD = ROOT / "docs" / "CLEAN_JSON_V1_FIXTURE_LOCK_20260521.md"
REPORT_JSON = ROOT / "docs" / "CLEAN_JSON_V1_FIXTURE_LOCK_20260521.json"

DEFAULT_API_URL = "http://127.0.0.1:9099/ocr/extract"
FALLBACK_PORT = 9137

INVOICE_DATA_DIR = ROOT / "public" / "data" / "testsets" / "invoice_statement"
RECEIPT_DATA_DIR = ROOT / "public" / "data" / "testsets" / "baseline"


INVOICE_CASES = [
    {
        "caseId": "trade_1_1jpg",
        "templateName": "거래_1",
        "file": "1.jpg",
        "fixture": "invoice_statement/trade_1_1jpg.clean.json",
        "rowCountExpected": 28,
        "rowIndexExpected": "excluded",
        "expectedKeys": ["itemName", "spec", "manufacturingNo", "expiryDate", "quantity", "unitPrice", "amount"],
    },
    {
        "caseId": "trade_2_2pdf",
        "templateName": "거래_2",
        "file": "2.pdf",
        "fixture": "invoice_statement/trade_2_2pdf.clean.json",
        "rowCountExpected": 13,
        "rowIndexExpected": "included",
        "expectedKeys": ["rowIndex", "itemCode", "itemName", "quantity", "consumerUnitPrice", "supplyUnitPrice", "supplyAmount"],
    },
    {
        "caseId": "trade_3_3pdf",
        "templateName": "거래_3",
        "file": "3.pdf",
        "fixture": "invoice_statement/trade_3_3pdf.clean.json",
        "rowCountExpected": 1,
        "rowIndexExpected": "included",
        "expectedKeys": ["rowIndex", "itemName", "quantity", "unitPrice", "manufacturer"],
        "knownExtraLockCandidates": ["insuranceCode", "amount"],
    },
    {
        "caseId": "trade_4_4pdf",
        "templateName": "거래_4",
        "file": "4.pdf",
        "fixture": "invoice_statement/trade_4_4pdf.clean.json",
        "rowCountExpected": 1,
        "rowIndexExpected": "excluded",
        "expectedKeys": ["itemName", "lotNo", "unit", "quantity", "unitPrice", "supplyAmount", "taxAmount", "totalAmount"],
    },
    {
        "caseId": "trade_5_5pdf",
        "templateName": "거래_5",
        "file": "5.pdf",
        "fixture": "invoice_statement/trade_5_5pdf.clean.json",
        "rowCountExpected": 6,
        "rowIndexExpected": "excluded",
        "expectedKeys": ["itemName", "itemCode", "quantity", "unitPrice", "amount"],
    },
    {
        "caseId": "trade_6_6pdf",
        "templateName": "거래_6",
        "file": "6.pdf",
        "fixture": "invoice_statement/trade_6_6pdf.clean.json",
        "rowCountExpected": 6,
        "rowIndexExpected": "included",
        "expectedKeys": ["rowIndex", "itemCode", "itemName", "quantity", "expiryDate"],
    },
    {
        "caseId": "trade_7_7pdf",
        "templateName": "거래_7",
        "file": "7.pdf",
        "fixture": "invoice_statement/trade_7_7pdf.clean.json",
        "rowCountExpected": 1,
        "rowIndexExpected": "excluded",
        "expectedKeys": ["itemName", "unit", "quantity"],
    },
]

RECEIPT_CASES = [
    {
        "caseId": "tpl_003_1jpg",
        "templateName": "영수증",
        "templateId": "TPL-003",
        "file": "1.jpg",
        "fixture": "receipt/tpl_003_1jpg.clean.json",
    },
    {
        "caseId": "tpl_003_2jpg",
        "templateName": "영수증",
        "templateId": "TPL-003",
        "file": "2.jpg",
        "fixture": "receipt/tpl_003_2jpg.clean.json",
    },
]

INVOICE_TABLE_COL_PRIORITY = [
    "itemCode",
    "itemName",
    "spec",
    "lotNo",
    "serialNo",
    "manufacturingNo",
    "expiryDate",
    "quantity",
    "unit",
    "consumerUnitPrice",
    "supplyUnitPrice",
    "unitPrice",
    "supplyAmount",
    "taxAmount",
    "amount",
    "totalAmount",
    "manufacturer",
    "insuranceCode",
    "remark",
]
INTERNAL_KEYS = {
    "_rawText",
    "rawText",
    "_source",
    "source",
    "manufacturingExpiryComposite",
    "serialLotComposite",
    "rowIndex",
    "lineIndex",
    "_confidence",
    "confidence",
    "bbox",
    "extractionSource",
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


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_command(args: list[str], cwd: Path, timeout: int = 180) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        proc = subprocess.run(
            args,
            cwd=str(cwd),
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            timeout=timeout,
            shell=False,
        )
        return {
            "command": " ".join(args),
            "exitCode": proc.returncode,
            "status": "PASS" if proc.returncode == 0 else "FAIL",
            "durationSeconds": round(time.perf_counter() - started, 3),
            "stdoutTail": proc.stdout[-4000:],
            "stderrTail": proc.stderr[-4000:],
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "command": " ".join(args),
            "exitCode": None,
            "status": "TIMEOUT",
            "durationSeconds": round(time.perf_counter() - started, 3),
            "stdoutTail": (exc.stdout or "")[-4000:] if isinstance(exc.stdout, str) else "",
            "stderrTail": (exc.stderr or "")[-4000:] if isinstance(exc.stderr, str) else "",
        }


def git_status() -> dict[str, Any]:
    result = run_command(["git", "-c", "safe.directory=D:/Free_Vue/OCR", "status", "--short"], ROOT, timeout=30)
    lines = [line for line in result.get("stdoutTail", "").splitlines() if line.strip()]
    return {"isDirty": bool(lines), "entries": lines, "command": result}


def load_templates() -> list[dict[str, Any]]:
    return read_json(TEMPLATES_JSON)


def template_by_name_file(templates: list[dict[str, Any]], name: str, filename: str) -> dict[str, Any] | None:
    exact: list[dict[str, Any]] = []
    same_name: list[dict[str, Any]] = []
    for item in templates:
        tj = item.get("template_json") or {}
        tname = str(item.get("template_name") or tj.get("templateName") or "")
        tfile = str(((tj.get("file") or {}).get("name")) or "")
        if tname == name:
            same_name.append(item)
            if tfile == filename:
                exact.append(item)
    return (exact or same_name or [None])[0]


def template_by_id(templates: list[dict[str, Any]], template_id: str) -> dict[str, Any] | None:
    return next((t for t in templates if str(t.get("template_id")) == template_id), None)


def api_health(api_url: str, timeout: float = 2.0) -> bool:
    if requests is None:
        return False
    base = api_url.rsplit("/", 2)[0]
    try:
        res = requests.get(f"{base}/templates", timeout=timeout)
        return res.status_code < 500
    except Exception:
        return False


def wait_for_api(api_url: str, timeout: int = 40) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if api_health(api_url, timeout=2):
            return True
        time.sleep(1)
    return False


def is_port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex(("127.0.0.1", port)) != 0


def start_backend_if_needed(api_url: str) -> tuple[str, subprocess.Popen[str] | None, str]:
    if api_health(api_url):
        return api_url, None, "existing"
    if not is_port_free(FALLBACK_PORT):
        fallback = f"http://127.0.0.1:{FALLBACK_PORT}/ocr/extract"
        if wait_for_api(fallback, timeout=5):
            return fallback, None, "existing_fallback_port"
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    server_out = LOG_DIR / f"codex_{TASK}.server.out.log"
    server_err = LOG_DIR / f"codex_{TASK}.server.err.log"
    python_exe = OCR_ROOT / ".venv" / "Scripts" / "python.exe"
    cmd = [str(python_exe if python_exe.exists() else sys.executable), "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", str(FALLBACK_PORT)]
    out_f = server_out.open("w", encoding="utf-8", errors="replace")
    err_f = server_err.open("w", encoding="utf-8", errors="replace")
    proc = subprocess.Popen(cmd, cwd=str(OCR_ROOT), stdout=out_f, stderr=err_f, text=True)
    # Keep handles attached to process object for Windows until termination.
    proc._codex_log_handles = (out_f, err_f)  # type: ignore[attr-defined]
    fallback = f"http://127.0.0.1:{FALLBACK_PORT}/ocr/extract"
    if not wait_for_api(fallback, timeout=60):
        stop_backend(proc)
        raise RuntimeError(f"Backend did not become ready on {fallback}; see {server_err}")
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
    handles = getattr(proc, "_codex_log_handles", None)
    if handles:
        for handle in handles:
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
    count = sum(1 for row in rows if not is_meaningless(normalize_cell(row.get(key))))
    return count / len(rows)


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

    cols = [{"key": key, "labelKo": str(col_labels.get(key) or key)} for key in candidate_keys if has_meaningful_value(rows, key)]

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
        cols = [{"key": "rowIndex", "labelKo": str(col_labels.get("rowIndex") or "rowIndex")}] + cols
    return cols


def clean_table_rows_from_objects(rows: list[dict[str, Any]], cols: list[dict[str, str]] | None) -> list[dict[str, str]]:
    if cols:
        ordered_keys = [col["key"] for col in cols]
    else:
        ordered_keys = [key for key in INVOICE_TABLE_COL_PRIORITY if has_meaningful_value(rows, key)]
    out: list[dict[str, str]] = []
    for row in rows:
        obj: dict[str, str] = {}
        for key in ordered_keys:
            obj[key] = normalize_cell(row.get(key))
        out.append(obj)
    return out


def clean_table_rows_from_cells(raw: Any) -> list[dict[str, str]]:
    if not isinstance(raw, list):
        return []
    rows = [row for row in raw if isinstance(row, list)]
    if not rows:
        return []
    excluded = {"itemCode", "lotNo", "unit", "supplyAmount", "taxAmount", "totalAmount", "remark"}
    fallback_keys = [key for key in INVOICE_TABLE_COL_PRIORITY if key not in excluded]
    output: list[dict[str, str]] = []
    for row in rows:
        obj: dict[str, str] = {}
        for idx, cell in enumerate(row):
            key = fallback_keys[idx] if idx < len(fallback_keys) else f"col_{idx + 1}"
            if isinstance(cell, dict) and "value" in cell:
                value = cell.get("value")
            else:
                value = cell
            obj[key] = normalize_cell(value)
        output.append(obj)
    return output


def build_run_ocr_fields(raw: dict[str, Any], template: dict[str, Any] | None) -> list[dict[str, Any]]:
    template_json = (template or {}).get("template_json") or {}
    regions = template_json.get("regions") or []
    mode = template_json.get("mode") or (template or {}).get("mode")
    if template and mode != "unstructured" and regions:
        enriched = []
        for idx, field in enumerate(raw.get("fields") or []):
            if not isinstance(field, dict):
                continue
            region = regions[idx] if idx < len(regions) and isinstance(regions[idx], dict) else {}
            next_field = dict(field)
            next_field["ko"] = next_field.get("ko") or str(region.get("koField") or "").strip()
            next_field["en"] = next_field.get("en") or str(region.get("enField") or region.get("canonicalField") or "").strip()
            enriched.append(next_field)
        return enriched

    receipt_fields = raw.get("receipt_fields") if isinstance(raw.get("receipt_fields"), dict) else {}
    finance_fields = raw.get("finance_fields") if isinstance(raw.get("finance_fields"), dict) else {}
    result_fields: list[dict[str, Any]] = []
    if receipt_fields:
        for name, value in receipt_fields.items():
            result_fields.append({"name": name, "field_type": "field", "value": "" if value is None else str(value), "confidence": 1 if value else 0, "bbox": [0, 0, 0, 0]})
    if not result_fields and finance_fields:
        for name, value in finance_fields.items():
            result_fields.append({"name": name, "field_type": "field", "value": "" if value is None else str(value), "confidence": 1 if value else 0, "bbox": [0, 0, 0, 0]})
    return result_fields or [field for field in raw.get("fields") or [] if isinstance(field, dict)]


def build_clean_json(raw: dict[str, Any], template: dict[str, Any] | None, template_name: str) -> tuple[dict[str, Any], dict[str, Any]]:
    fields = build_run_ocr_fields(raw, template)
    document_fields = raw.get("document_fields") if isinstance(raw.get("document_fields"), dict) else {}
    doc_table_rows = document_fields.get("tableRows") if isinstance(document_fields.get("tableRows"), list) else None
    if doc_table_rows is not None:
        doc_table_rows = [row for row in doc_table_rows if isinstance(row, dict)]
    table_meta = document_fields.get("tableMeta") if isinstance(document_fields.get("tableMeta"), dict) else None
    doc_table_display_cols = build_invoice_preview_cols(table_meta, doc_table_rows) if doc_table_rows else None

    info = []
    for field in fields:
        if field.get("field_type") == "field":
            name = str(field.get("name") or "")
            info.append({"key": name, "label": str(field.get("ko") or field.get("label") or name), "value": "" if field.get("value") is None else str(field.get("value"))})

    tables = []
    for field in fields:
        if field.get("field_type") != "table":
            continue
        rows: list[dict[str, str]] = []
        if doc_table_rows and doc_table_display_cols:
            rows = clean_table_rows_from_objects(doc_table_rows, doc_table_display_cols)
        elif isinstance(field.get("tableRows"), list) and field["tableRows"]:
            rows = clean_table_rows_from_objects([r for r in field["tableRows"] if isinstance(r, dict)], None)
        elif isinstance(field.get("table_data"), list):
            rows = clean_table_rows_from_cells(field.get("table_data"))
        elif field.get("value"):
            try:
                rows = clean_table_rows_from_cells(json.loads(str(field.get("value"))))
            except Exception:
                rows = []
        name = str(field.get("name") or "")
        tables.append({"key": name, "label": str(field.get("ko") or field.get("label") or name), "rows": rows})

    clean: dict[str, Any] = {"templateName": template_name or ""}
    if info:
        clean["info"] = info
    if tables:
        clean["tables"] = tables
    meta = {
        "fieldCount": len(fields),
        "infoCount": len(info),
        "tableCount": len(tables),
        "docTableRowCount": len(doc_table_rows or []),
        "docTableDisplayColumnKeys": [col["key"] for col in (doc_table_display_cols or [])],
        "tableMetaExpectedColumnKeys": table_meta.get("expectedColumnKeys") if table_meta else None,
        "tableMetaColumns": table_meta.get("columns") if table_meta else None,
        "documentFieldsHasTableRows": bool(doc_table_rows),
        "documentFieldsTableRowsHasRowIndex": bool(doc_table_rows and any("rowIndex" in row for row in doc_table_rows)),
    }
    return clean, meta


def post_ocr(api_url: str, input_path: Path, template: dict[str, Any], document_type: str | None) -> tuple[dict[str, Any], dict[str, Any]]:
    if requests is None:
        raise RuntimeError(f"requests import failed: {REQUESTS_IMPORT_ERROR}")
    template_json = template.get("template_json") or {}
    data: dict[str, str] = {
        "template_id": str(template.get("template_id") or ""),
        "model_id": "paddleocr",
    }
    regions = template_json.get("regions")
    if isinstance(regions, list) and regions:
        data["regions"] = json.dumps(regions, ensure_ascii=False)
    doc_type = document_type or template_json.get("documentType")
    if doc_type:
        data["documentType"] = str(doc_type)
    started = time.perf_counter()
    with input_path.open("rb") as file_handle:
        res = requests.post(api_url, data=data, files={"file": (input_path.name, file_handle)}, timeout=240)
    wall = round(time.perf_counter() - started, 3)
    response_size = len(res.content)
    res.raise_for_status()
    return res.json(), {"wallClockSeconds": wall, "responseSizeBytes": response_size, "payloadKeys": sorted(data.keys())}


def validate_fixture(clean: dict[str, Any], case: dict[str, Any], capture_meta: dict[str, Any]) -> dict[str, Any]:
    tables = clean.get("tables") if isinstance(clean.get("tables"), list) else []
    rows = []
    if tables and isinstance(tables[0], dict) and isinstance(tables[0].get("rows"), list):
        rows = tables[0]["rows"]
    row_keys = list(rows[0].keys()) if rows else []
    row_count_expected = case.get("rowCountExpected")
    row_count_actual = len(rows)
    row_index_actual = "included" if "rowIndex" in row_keys else "excluded"
    expected_keys = case.get("expectedKeys") or []
    known_extra = case.get("knownExtraLockCandidates") or []
    extra = [key for key in row_keys if key not in expected_keys]
    missing = [key for key in expected_keys if key not in row_keys]
    status = "PASS"
    warnings: list[str] = []
    if row_count_expected is not None and row_count_actual != row_count_expected:
        status = "FAIL"
        warnings.append(f"rowCount mismatch {row_count_actual}/{row_count_expected}")
    if case.get("rowIndexExpected") and row_index_actual != case["rowIndexExpected"]:
        status = "FAIL"
        warnings.append(f"rowIndex {row_index_actual}, expected {case['rowIndexExpected']}")
    unresolved_locked = [key for key in known_extra if key in row_keys]
    unexpected_extra = [key for key in extra if key not in known_extra]
    if missing or unexpected_extra:
        if status != "FAIL":
            status = "WARN"
        if missing:
            warnings.append(f"missing columns: {missing}")
        if unexpected_extra:
            warnings.append(f"extra columns: {unexpected_extra}")
    if unresolved_locked:
        warnings.append(f"unresolved but locked current behavior: {unresolved_locked}")
    return {
        "shapeValid": "templateName" in clean and isinstance(clean.get("templateName"), str),
        "hasInfoArray": isinstance(clean.get("info"), list),
        "hasTablesArray": isinstance(clean.get("tables"), list),
        "rowCountExpected": row_count_expected,
        "rowCountActual": row_count_actual,
        "rowKeys": row_keys,
        "expectedKeys": expected_keys,
        "rowIndexExpected": case.get("rowIndexExpected"),
        "rowIndexActual": row_index_actual,
        "columnOrderSameAgainstPolicyExpected": row_keys == expected_keys,
        "missingColumns": missing,
        "extraColumns": extra,
        "unresolvedLockedColumns": unresolved_locked,
        "previewCleanJsonColumnOrderSame": row_keys == capture_meta.get("docTableDisplayColumnKeys", []),
        "status": status,
        "warnings": warnings,
    }


def validate_receipt_fixture(clean: dict[str, Any]) -> dict[str, Any]:
    info = clean.get("info") if isinstance(clean.get("info"), list) else []
    tables = clean.get("tables") if isinstance(clean.get("tables"), list) else []
    status = "PASS" if clean.get("templateName") and info else "FAIL"
    return {
        "shapeValid": isinstance(clean.get("templateName"), str),
        "hasInfoArray": isinstance(info, list),
        "infoCount": len(info),
        "hasTablesArray": isinstance(tables, list),
        "tableCount": len(tables),
        "fieldOnlyRepresentative": len(info) > 0 and len(tables) == 0,
        "status": status,
        "warnings": [] if status == "PASS" else ["missing templateName or info fields"],
    }


def fixture_path(rel: str) -> Path:
    return FIXTURE_ROOT / rel


# ── FRONTEND-CLEANUP-1 read-only check mode ──────────────────────────────────
# `--check` reproduces Clean JSON via the same build_clean_json() and deep-compares
# against the existing fixtures. It never writes to fixtures or manifest.

def deep_compare(actual: Any, expected: Any, path: str = "$") -> list[str]:
    """Return a list of human-readable diff messages. Empty list ⇒ equal.
    Dict key order is enforced (Clean JSON v1 row order contract)."""
    if type(actual) is not type(expected):
        return [f"{path}: type mismatch actual={type(actual).__name__} expected={type(expected).__name__}"]
    if isinstance(actual, dict):
        actual_keys = list(actual.keys())
        expected_keys = list(expected.keys())
        if actual_keys != expected_keys:
            return [f"{path}: key order/set mismatch actual={actual_keys} expected={expected_keys}"]
        diffs: list[str] = []
        for key in actual_keys:
            diffs.extend(deep_compare(actual[key], expected[key], f"{path}.{key}"))
        return diffs
    if isinstance(actual, list):
        if len(actual) != len(expected):
            return [f"{path}: length mismatch actual={len(actual)} expected={len(expected)}"]
        diffs = []
        for index, (av, ev) in enumerate(zip(actual, expected)):
            diffs.extend(deep_compare(av, ev, f"{path}[{index}]"))
        return diffs
    if actual != expected:
        return [f"{path}: value mismatch actual={actual!r} expected={expected!r}"]
    return []


def summarize_invoice_actual(clean: dict[str, Any]) -> tuple[int, str, list[str]]:
    tables = clean.get("tables") if isinstance(clean.get("tables"), list) else []
    if not tables or not isinstance(tables[0], dict):
        return 0, "excluded", []
    rows = tables[0].get("rows") if isinstance(tables[0].get("rows"), list) else []
    if not rows:
        return 0, "excluded", []
    row_keys = list(rows[0].keys()) if isinstance(rows[0], dict) else []
    return len(rows), ("included" if "rowIndex" in row_keys else "excluded"), row_keys


def check_cases(api_url: str, templates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []

    for case in INVOICE_CASES:
        template = template_by_name_file(templates, case["templateName"], case["file"])
        fixture_full = fixture_path(case["fixture"])
        base = {
            "caseId": case["caseId"],
            "templateName": case["templateName"],
            "templateId": (template or {}).get("template_id"),
            "inputFile": f"invoice_statement/{case['file']}",
            "fixturePath": case["fixture"],
        }
        if not template:
            results.append({**base, "status": "FAIL", "error": "template not found", "diffs": []})
            continue
        if not fixture_full.exists():
            results.append({**base, "status": "FAIL", "error": f"fixture missing at {fixture_full}", "diffs": []})
            continue
        print(f"[check] {case['caseId']} template={template.get('template_id')} file={case['file']}", flush=True)
        try:
            raw, http_meta = post_ocr(api_url, INVOICE_DATA_DIR / case["file"], template, "invoice_statement")
            actual, _capture_meta = build_clean_json(raw, template, case["templateName"])
            expected = read_json(fixture_full)
            diffs = deep_compare(actual, expected)
            row_count_actual, row_index_actual, row_keys = summarize_invoice_actual(actual)
            results.append({
                **base,
                **http_meta,
                "rowCountExpected": case.get("rowCountExpected"),
                "rowCountActual": row_count_actual,
                "rowIndexExpected": case.get("rowIndexExpected"),
                "rowIndexActual": row_index_actual,
                "rowKeys": row_keys,
                "diffCount": len(diffs),
                "diffs": diffs[:20],
                "status": "PASS" if not diffs else "FAIL",
            })
        except Exception as exc:
            results.append({**base, "status": "FAIL", "error": repr(exc), "diffs": []})

    for case in RECEIPT_CASES:
        template = template_by_id(templates, case["templateId"])
        fixture_full = fixture_path(case["fixture"])
        base = {
            "caseId": case["caseId"],
            "templateName": case["templateName"],
            "templateId": case["templateId"],
            "inputFile": f"baseline/{case['file']}",
            "fixturePath": case["fixture"],
        }
        if not template:
            results.append({**base, "status": "FAIL", "error": "template not found", "diffs": []})
            continue
        if not fixture_full.exists():
            results.append({**base, "status": "FAIL", "error": f"fixture missing at {fixture_full}", "diffs": []})
            continue
        print(f"[check] {case['caseId']} template={template.get('template_id')} file={case['file']}", flush=True)
        try:
            raw, http_meta = post_ocr(api_url, RECEIPT_DATA_DIR / case["file"], template, None)
            actual, _capture_meta = build_clean_json(raw, template, case["templateName"])
            expected = read_json(fixture_full)
            diffs = deep_compare(actual, expected)
            results.append({
                **base,
                **http_meta,
                "infoCount": len(actual.get("info") or []),
                "tableCount": len(actual.get("tables") or []),
                "diffCount": len(diffs),
                "diffs": diffs[:20],
                "status": "PASS" if not diffs else "FAIL",
            })
        except Exception as exc:
            results.append({**base, "status": "FAIL", "error": repr(exc), "diffs": []})

    return results


def capture_cases(api_url: str, templates: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    manifest_cases: list[dict[str, Any]] = []
    detailed_cases: list[dict[str, Any]] = []

    for case in INVOICE_CASES:
        template = template_by_name_file(templates, case["templateName"], case["file"])
        if not template:
            detail = {**case, "status": "FAIL", "error": "template not found"}
            manifest_cases.append(detail)
            detailed_cases.append(detail)
            continue
        input_path = INVOICE_DATA_DIR / case["file"]
        print(f"[capture] {case['caseId']} template={template.get('template_id')} file={input_path.name}", flush=True)
        try:
            raw, http_meta = post_ocr(api_url, input_path, template, "invoice_statement")
            clean, capture_meta = build_clean_json(raw, template, case["templateName"])
            out_path = fixture_path(case["fixture"])
            write_json(out_path, clean)
            reread = read_json(out_path)
            validation = validate_fixture(reread, case, capture_meta)
            detail = {
                **case,
                "templateId": template.get("template_id"),
                "inputFile": f"invoice_statement/{case['file']}",
                "fixturePath": case["fixture"],
                "processing_time": raw.get("processing_time"),
                **http_meta,
                "cleanJsonBytes": len(json.dumps(clean, ensure_ascii=False).encode("utf-8")),
                "captureMeta": capture_meta,
                "validation": validation,
                "status": validation["status"],
            }
        except Exception as exc:
            detail = {
                **case,
                "templateId": template.get("template_id"),
                "inputFile": f"invoice_statement/{case['file']}",
                "fixturePath": case["fixture"],
                "status": "FAIL",
                "error": repr(exc),
            }
        manifest_cases.append({
            "caseId": case["caseId"],
            "templateName": case["templateName"],
            "templateId": detail.get("templateId"),
            "inputFile": detail.get("inputFile"),
            "fixturePath": detail.get("fixturePath"),
            "rowCountExpected": case.get("rowCountExpected"),
            "rowCountActual": (detail.get("validation") or {}).get("rowCountActual"),
            "rowIndexExpected": case.get("rowIndexExpected"),
            "rowIndexActual": (detail.get("validation") or {}).get("rowIndexActual"),
            "rowKeys": (detail.get("validation") or {}).get("rowKeys"),
            "status": detail.get("status"),
        })
        detailed_cases.append(detail)

    for case in RECEIPT_CASES:
        template = template_by_id(templates, case["templateId"])
        if not template:
            detail = {**case, "status": "FAIL", "error": "template not found"}
            manifest_cases.append(detail)
            detailed_cases.append(detail)
            continue
        input_path = RECEIPT_DATA_DIR / case["file"]
        print(f"[capture] {case['caseId']} template={template.get('template_id')} file={input_path.name}", flush=True)
        try:
            raw, http_meta = post_ocr(api_url, input_path, template, None)
            clean, capture_meta = build_clean_json(raw, template, case["templateName"])
            out_path = fixture_path(case["fixture"])
            write_json(out_path, clean)
            reread = read_json(out_path)
            validation = validate_receipt_fixture(reread)
            detail = {
                **case,
                "templateId": template.get("template_id"),
                "inputFile": f"baseline/{case['file']}",
                "fixturePath": case["fixture"],
                "processing_time": raw.get("processing_time"),
                **http_meta,
                "cleanJsonBytes": len(json.dumps(clean, ensure_ascii=False).encode("utf-8")),
                "captureMeta": capture_meta,
                "validation": validation,
                "status": validation["status"],
            }
        except Exception as exc:
            detail = {
                **case,
                "templateId": template.get("template_id"),
                "inputFile": f"baseline/{case['file']}",
                "fixturePath": case["fixture"],
                "status": "FAIL",
                "error": repr(exc),
            }
        manifest_cases.append({
            "caseId": case["caseId"],
            "templateName": case["templateName"],
            "templateId": detail.get("templateId"),
            "inputFile": detail.get("inputFile"),
            "fixturePath": detail.get("fixturePath"),
            "infoCount": (detail.get("validation") or {}).get("infoCount"),
            "tableCount": (detail.get("validation") or {}).get("tableCount"),
            "status": detail.get("status"),
        })
        detailed_cases.append(detail)

    return manifest_cases, detailed_cases


def make_manifest(api_url: str, api_source: str, cases: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "version": "clean_json_v1",
        "createdAt": datetime.now().isoformat(timespec="seconds"),
        "task": TASK,
        "source": "current OcrResultPanel Clean JSON contract reproduced in tmp fixture lock script",
        "contractDocs": [
            str(CONTRACT_MD.relative_to(ROOT)),
            str(CONTRACT_JSON.relative_to(ROOT)),
        ],
        "apiUrl": api_url,
        "apiSource": api_source,
        "fixtureRoot": str(FIXTURE_ROOT.relative_to(ROOT)),
        "cases": cases,
    }


def summarize_status(cases: list[dict[str, Any]]) -> dict[str, Any]:
    counts: dict[str, int] = {}
    for case in cases:
        counts[str(case.get("status") or "UNKNOWN")] = counts.get(str(case.get("status") or "UNKNOWN"), 0) + 1
    overall = "PASS"
    if counts.get("FAIL"):
        overall = "FAIL"
    elif counts.get("WARN"):
        overall = "WARN"
    return {"overall": overall, "counts": counts}


def md_table(headers: list[str], rows: list[list[Any]]) -> str:
    out = "| " + " | ".join(headers) + " |\n"
    out += "| " + " | ".join(["---"] * len(headers)) + " |\n"
    for row in rows:
        out += "| " + " | ".join(str(cell) for cell in row) + " |\n"
    return out


def make_report_md(report: dict[str, Any]) -> str:
    dirty = report["repoDirtyStatus"]
    invoice_rows = []
    receipt_rows = []
    for case in report["cases"]:
        val = case.get("validation") or {}
        if case.get("caseId", "").startswith("trade_"):
            invoice_rows.append([
                case["caseId"],
                case.get("templateId"),
                val.get("rowCountActual"),
                val.get("rowIndexActual"),
                ", ".join(val.get("rowKeys") or []),
                case.get("processing_time"),
                case.get("wallClockSeconds"),
                case.get("status"),
            ])
        else:
            receipt_rows.append([
                case["caseId"],
                case.get("templateId"),
                val.get("infoCount"),
                val.get("tableCount"),
                case.get("processing_time"),
                case.get("wallClockSeconds"),
                case.get("status"),
            ])

    tc = report["typecheck"]
    build = report["build"]
    return f"""# CLEAN JSON V1 FIXTURE LOCK 20260521

## 1. 사용 도구와 모델
- 사용 도구: Codex
- 사용 모델: Codex
- 작업명: `{TASK}`
- 생성 시각: `{report['generatedAt']}`

## 2. 운영 코드 수정 없음 확인
- 운영 frontend/backend/templates/manifest/GT는 수정하지 않았다.
- `OcrResultPanel.tsx` 리팩토링 및 `cleanJsonBuilder.ts` 생성은 하지 않았다.
- 생성물은 tmp 스크립트, tmp fixture, docs 리포트뿐이다.
- repo dirty 상태: `{'DIRTY' if dirty['isDirty'] else 'CLEAN'}`

```text
{chr(10).join(dirty['entries']) if dirty['entries'] else '(none)'}
```

## 3. 참조한 Contract 문서
- `docs/CLEAN_JSON_CONTRACT_20260521.md`
- `docs/CLEAN_JSON_CONTRACT_20260521.json`

## 4. Fixture 저장 위치
- fixture root: `tmp/fixtures/clean_json_v1`
- manifest: `tmp/fixtures/clean_json_v1/manifest.json`
- docs report: `docs/CLEAN_JSON_V1_FIXTURE_LOCK_20260521.md`
- docs json: `docs/CLEAN_JSON_V1_FIXTURE_LOCK_20260521.json`

## 5. API 실행 조건
- API URL: `{report['apiUrl']}`
- API source: `{report['apiSource']}`
- RunOCR와 같은 FormData 계열: `file`, `template_id`, `model_id`, `regions`, `documentType`
- 운영 코드는 수정하지 않았다.

## 6. 거래명세서 Fixture 결과
{md_table(['caseId', 'templateId', 'rows', 'rowIndex', 'rowKeys', 'processing_time', 'wallClockSeconds', 'status'], invoice_rows)}

## 7. 영수증 Fixture 결과
{md_table(['caseId', 'templateId', 'infoCount', 'tableCount', 'processing_time', 'wallClockSeconds', 'status'], receipt_rows)}

## 8. rowIndex / Column Order 검증
- 거래_1/4/5/7은 fixture rows에서 `rowIndex` 제외를 검증했다.
- 거래_2/3/6은 fixture rows에서 `rowIndex` 유지를 검증했다.
- 구조화 거래명세서 rows는 `docTableDisplayCols` 순서로 ordered object를 생성했다.
- fixture 검증은 저장 후 다시 읽어 row keys와 rowCount를 확인했다.

## 9. 거래_3 Locked Current Behavior
- 거래_3의 `insuranceCode`, `amount`는 rowIndex 정책과 별도 이슈다.
- 현재 Clean JSON v1 출력에 존재하면 fixture에 그대로 저장하고 `unresolved but locked current behavior`로 기록한다.
- helper 분리 작업에서는 이 동작을 바꾸면 안 된다.

## 10. Before / After Deep Equality 방법
1. 이번 fixture를 helper 분리 전 golden output으로 사용한다.
2. FRONTEND-CLEANUP-1 이후 같은 API/input/template으로 Clean JSON을 재생성한다.
3. `tmp/fixtures/clean_json_v1` 아래 fixture와 deep equality 비교한다.
4. key order까지 검증하려면 ordered stringify 결과를 비교한다.
5. 비교 실패 시 diff path를 출력한다.
6. Preview column order와 Clean JSON row keys 일치도 별도 검사한다.

## 11. Known Stderr Noise
- `ISSUE-FRONTEND-BUILD-LOG-1`
- `npm run build`는 exit code 0이지만 stderr에 `ESLint: nextVitals is not iterable` 메시지가 기록된다.
- cleanup 작업 실패 원인과 구분해야 한다.

## 12. Typecheck / Build
| command | status | exit | seconds |
| --- | --- | --- | --- |
| npm run typecheck | {tc['status']} | {tc['exitCode']} | {tc['durationSeconds']} |
| npm run build | {build['status']} | {build['exitCode']} | {build['durationSeconds']} |

### build stderr tail
```text
{build.get('stderrTail') or '(empty)'}
```

## 13. 최종 판정
- fixture lock status: `{report['summary']['overall']}`
- status counts: `{report['summary']['counts']}`

## 14. 다음 작업 제안
1. FRONTEND-CLEANUP-1에서 `buildCleanJsonResult` helper를 분리한다.
2. helper 분리 후 이번 fixture와 deep equality를 비교한다.
3. 거래_3 `insuranceCode`/`amount` 정책은 별도 프롬프트로 다룬다.
4. build stderr known noise는 cleanup 실패와 분리해서 추적한다.
"""


def make_check_report_md(report: dict[str, Any]) -> str:
    invoice_rows = []
    receipt_rows = []
    for case in report["cases"]:
        if str(case.get("caseId", "")).startswith("trade_"):
            invoice_rows.append([
                case.get("caseId"),
                case.get("templateId"),
                case.get("rowCountExpected"),
                case.get("rowCountActual"),
                case.get("rowIndexExpected"),
                case.get("rowIndexActual"),
                case.get("diffCount", 0),
                case.get("status"),
            ])
        else:
            receipt_rows.append([
                case.get("caseId"),
                case.get("templateId"),
                case.get("infoCount"),
                case.get("tableCount"),
                case.get("diffCount", 0),
                case.get("status"),
            ])
    summary = report["summary"]
    md = f"""# CLEAN JSON V1 FIXTURE CHECK ({report['phase']}) {report['generatedDate']}

## 1. Task / Phase
- Task: `{report['task']}`
- Phase: `{report['phase']}`
- Generated at: `{report['generatedAt']}`
- Mode: `--check` (read-only — fixtures and manifest are NOT modified)

## 2. API
- API URL: `{report['apiUrl']}`
- API source: `{report['apiSource']}`
- Fixture root: `{report['fixtureRoot']}`

## 3. Invoice cases
{md_table(['caseId', 'templateId', 'rowCountExpected', 'rowCountActual', 'rowIndexExpected', 'rowIndexActual', 'diffCount', 'status'], invoice_rows)}

## 4. Receipt cases
{md_table(['caseId', 'templateId', 'infoCount', 'tableCount', 'diffCount', 'status'], receipt_rows)}

## 5. Summary
- overall: `{summary['overall']}`
- counts: `{summary['counts']}`
"""
    failures = [case for case in report["cases"] if case.get("status") == "FAIL"]
    if failures:
        md += "\n## 6. First diffs per failed case\n"
        for case in failures:
            md += f"\n### {case.get('caseId')}\n"
            if case.get("error"):
                md += f"- error: {case['error']}\n"
            for entry in (case.get("diffs") or [])[:5]:
                md += f"- {entry}\n"
    return md


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-url", default=DEFAULT_API_URL)
    parser.add_argument("--skip-build", action="store_true")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Read-only mode: compare current OCR Clean JSON against existing fixtures. Never writes fixtures or manifest.",
    )
    parser.add_argument(
        "--phase",
        default="check",
        help="Tag for the check report filename (e.g. pre / post). Only used with --check.",
    )
    parser.add_argument("--check-report-json", default=None)
    parser.add_argument("--check-report-md", default=None)
    args = parser.parse_args()

    if requests is None:
        raise RuntimeError(f"requests package is required: {REQUESTS_IMPORT_ERROR}")

    for path in [REPORT_MD.parent, LOG_DIR]:
        path.mkdir(parents=True, exist_ok=True)
    if not args.check:
        for path in [FIXTURE_ROOT, INVOICE_FIXTURE_DIR, RECEIPT_FIXTURE_DIR]:
            path.mkdir(parents=True, exist_ok=True)

    print(f"[{TASK}] mode={'check' if args.check else 'capture'} phase={args.phase} root={ROOT}", flush=True)
    print(f"[contract] md={CONTRACT_MD.exists()} json={CONTRACT_JSON.exists()}", flush=True)
    templates = load_templates()
    print(f"[templates] count={len(templates)} source={TEMPLATES_JSON}", flush=True)

    backend_proc: subprocess.Popen[str] | None = None
    api_url = args.api_url
    api_source = "unknown"
    try:
        api_url, backend_proc, api_source = start_backend_if_needed(api_url)
        print(f"[api] {api_url} source={api_source}", flush=True)

        if args.check:
            cases = check_cases(api_url, templates)
            summary = summarize_status(cases)
            now = datetime.now()
            report = {
                "task": TASK,
                "phase": args.phase,
                "generatedAt": now.isoformat(timespec="seconds"),
                "generatedDate": now.strftime("%Y%m%d"),
                "toolAndModel": {"tool": "Claude Code", "model": "claude-opus-4-7"},
                "noProductionCodeModifiedByThisRunner": True,
                "mode": "check",
                "fixtureRoot": str(FIXTURE_ROOT.relative_to(ROOT)),
                "manifestPath": str(MANIFEST_PATH.relative_to(ROOT)),
                "apiUrl": api_url,
                "apiSource": api_source,
                "cases": cases,
                "summary": summary,
            }
            report_json_path = (
                Path(args.check_report_json)
                if args.check_report_json
                else (ROOT / "docs" / f"CLEAN_JSON_V1_FIXTURE_CHECK_{args.phase}_20260521.json")
            )
            report_md_path = (
                Path(args.check_report_md)
                if args.check_report_md
                else (ROOT / "docs" / f"CLEAN_JSON_V1_FIXTURE_CHECK_{args.phase}_20260521.md")
            )
            write_json(report_json_path, report)
            report_md_path.parent.mkdir(parents=True, exist_ok=True)
            report_md_path.write_text(make_check_report_md(report), encoding="utf-8")
            print(f"[write] {report_json_path}", flush=True)
            print(f"[write] {report_md_path}", flush=True)
            print(f"[summary] overall={summary['overall']} counts={summary['counts']}", flush=True)
            return 0 if summary["overall"] == "PASS" else 1

        manifest_cases, detailed_cases = capture_cases(api_url, templates)
        manifest = make_manifest(api_url, api_source, manifest_cases)
        write_json(MANIFEST_PATH, manifest)
        print(f"[write] {MANIFEST_PATH}", flush=True)

        print("[check] running npm run typecheck", flush=True)
        typecheck = run_command(["npm.cmd", "run", "typecheck"], ROOT, timeout=180) if not args.skip_build else {"status": "SKIPPED", "exitCode": None, "durationSeconds": 0, "stdoutTail": "", "stderrTail": ""}
        print(f"[check] typecheck={typecheck['status']} duration={typecheck['durationSeconds']}s", flush=True)
        print("[check] running npm run build", flush=True)
        build = run_command(["npm.cmd", "run", "build"], ROOT, timeout=300) if not args.skip_build else {"status": "SKIPPED", "exitCode": None, "durationSeconds": 0, "stdoutTail": "", "stderrTail": ""}
        print(f"[check] build={build['status']} duration={build['durationSeconds']}s", flush=True)

        report = {
            "task": TASK,
            "generatedAt": datetime.now().isoformat(timespec="seconds"),
            "toolAndModel": {"tool": "Codex", "model": "Codex"},
            "noProductionCodeModifiedByThisTask": True,
            "contractDocs": [str(CONTRACT_MD.relative_to(ROOT)), str(CONTRACT_JSON.relative_to(ROOT))],
            "fixtureRoot": str(FIXTURE_ROOT.relative_to(ROOT)),
            "manifestPath": str(MANIFEST_PATH.relative_to(ROOT)),
            "apiUrl": api_url,
            "apiSource": api_source,
            "repoDirtyStatus": git_status(),
            "cases": detailed_cases,
            "manifestCases": manifest_cases,
            "summary": summarize_status(detailed_cases),
            "knownStderrNoise": {
                "id": "ISSUE-FRONTEND-BUILD-LOG-1",
                "message": "ESLint: nextVitals is not iterable",
                "buildExitCode": build.get("exitCode"),
            },
            "typecheck": typecheck,
            "build": build,
            "beforeAfterEqualityPlan": [
                "Regenerate Clean JSON after helper extraction using the same inputs and templates.",
                "Deep-compare regenerated payloads with tmp/fixtures/clean_json_v1/*.clean.json.",
                "Use ordered JSON stringify when key order is part of the assertion.",
                "Emit diff path for each mismatch.",
                "Separately assert Preview display columns equal Clean JSON row keys for invoice rows.",
            ],
        }
        write_json(REPORT_JSON, report)
        REPORT_MD.write_text(make_report_md(report), encoding="utf-8")
        print(f"[write] {REPORT_JSON}", flush=True)
        print(f"[write] {REPORT_MD}", flush=True)
        ok = report["summary"]["overall"] in {"PASS", "WARN"} and typecheck["status"] in {"PASS", "SKIPPED"} and build["status"] in {"PASS", "SKIPPED"}
        return 0 if ok else 1
    finally:
        stop_backend(backend_proc)


if __name__ == "__main__":
    raise SystemExit(main())
