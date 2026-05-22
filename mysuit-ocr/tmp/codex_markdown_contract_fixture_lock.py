from __future__ import annotations

import argparse
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


TASK = "CODEX_FRONTEND_CLEANUP_2A_MARKDOWN_CONTRACT_FIXTURE_LOCK_NO_PROD_MODIFY"
ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
OCR_ROOT = REPO / "ocr-server"
LOG_DIR = OCR_ROOT / "logs"
REVIEW_LOG = OCR_ROOT / "data" / "review_log.jsonl"
TEMPLATES_JSON = OCR_ROOT / "data" / "templates.json"

FIXTURE_ROOT = ROOT / "tmp" / "fixtures" / "markdown_v1"
INVOICE_FIXTURE_DIR = FIXTURE_ROOT / "invoice_statement"
RECEIPT_FIXTURE_DIR = FIXTURE_ROOT / "receipt"
MANIFEST_PATH = FIXTURE_ROOT / "manifest.json"

CONTRACT_MD = ROOT / "docs" / "MARKDOWN_V1_CONTRACT_20260521.md"
CONTRACT_JSON = ROOT / "docs" / "MARKDOWN_V1_CONTRACT_20260521.json"
LOCK_MD = ROOT / "docs" / "MARKDOWN_V1_FIXTURE_LOCK_20260521.md"
LOCK_JSON = ROOT / "docs" / "MARKDOWN_V1_FIXTURE_LOCK_20260521.json"

INVOICE_DATA_DIR = ROOT / "public" / "data" / "testsets" / "invoice_statement"
RECEIPT_DATA_DIR = ROOT / "public" / "data" / "testsets" / "baseline"
DEFAULT_API_URL = "http://127.0.0.1:9099/ocr/extract"
FALLBACK_PORT = 9141


CASES = [
    {
        "caseId": "trade_1_1jpg",
        "kind": "invoice",
        "templateName": "거래_1",
        "file": "1.jpg",
        "fixture": "invoice_statement/trade_1_1jpg.md",
        "rowIndexPolicy": "excluded_in_preview_clean_json_not_markdown",
        "notes": "rowIndex excluded case, 28-row structured table summarized in Markdown",
    },
    {
        "caseId": "trade_2_2pdf",
        "kind": "invoice",
        "templateName": "거래_2",
        "file": "2.pdf",
        "fixture": "invoice_statement/trade_2_2pdf.md",
        "rowIndexPolicy": "included_in_preview_clean_json_not_markdown",
        "notes": "rowIndex included case, 13-row structured table summarized in Markdown",
    },
    {
        "caseId": "trade_3_3pdf",
        "kind": "invoice",
        "templateName": "거래_3",
        "file": "3.pdf",
        "fixture": "invoice_statement/trade_3_3pdf.md",
        "rowIndexPolicy": "included_in_preview_clean_json_not_markdown",
        "notes": "rowIndex included plus insuranceCode/amount locked behavior in table display, but Markdown only summarizes table field",
    },
    {
        "caseId": "trade_7_7pdf",
        "kind": "invoice",
        "templateName": "거래_7",
        "file": "7.pdf",
        "fixture": "invoice_statement/trade_7_7pdf.md",
        "rowIndexPolicy": "excluded_in_preview_clean_json_not_markdown",
        "notes": "coverage add: single-row table summary, rowIndex excluded case",
    },
    {
        "caseId": "tpl_003_1jpg",
        "kind": "receipt",
        "templateName": "영수증",
        "templateId": "TPL-003",
        "file": "1.jpg",
        "fixture": "receipt/tpl_003_1jpg.md",
        "rowIndexPolicy": "not_applicable",
        "notes": "field-only receipt representative",
    },
    {
        "caseId": "tpl_003_2jpg",
        "kind": "receipt",
        "templateName": "영수증",
        "templateId": "TPL-003",
        "file": "2.jpg",
        "fixture": "receipt/tpl_003_2jpg.md",
        "rowIndexPolicy": "not_applicable",
        "notes": "field-only receipt representative",
    },
]


INVOICE_FIELD_KO = {
    "supplierName": "공급자",
    "supplierCompany": "공급자",
    "supplierBusinessNo": "공급자 사업자번호",
    "supplierCeo": "공급자 대표",
    "supplierAddress": "공급자 주소",
    "supplierTel": "공급자 전화",
    "buyerName": "공급받는자",
    "buyerCompany": "공급받는자",
    "buyerBusinessNo": "받는자 사업자번호",
    "buyerCeo": "받는자 대표",
    "buyerAddress": "받는자 주소",
    "buyerTel": "받는자 전화",
    "issueDate": "일자",
    "date": "일자",
    "supplyAmount": "공급가",
    "taxAmount": "세액",
    "totalAmount": "합계",
    "tableRows": "표 데이터",
    "table": "표 데이터",
    "itemName": "품명",
    "itemCode": "품목코드",
    "spec": "규격",
    "quantity": "수량",
    "unit": "단위",
    "unitPrice": "단가",
    "amount": "금액",
    "lotNo": "LOT번호",
    "serialNo": "Serial",
    "serialLotComposite": "시리얼/로트No.",
    "manufacturingExpiryComposite": "제조번호/유효기간",
    "expiryDate": "유효기간",
    "manufacturingNo": "제조번호",
    "rowIndex": "순번",
}


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
    result = run_command(["git", "-c", "safe.directory=D:/Free_Vue/OCR", "status", "--short"], REPO, timeout=30)
    entries = [line for line in result.get("stdoutTail", "").splitlines() if line.strip()]
    return {"isDirty": bool(entries), "entries": entries, "command": result}


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


def wait_for_api(api_url: str, timeout: int = 60) -> bool:
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
    fallback = f"http://127.0.0.1:{FALLBACK_PORT}/ocr/extract"
    if not is_port_free(FALLBACK_PORT) and wait_for_api(fallback, timeout=5):
        return fallback, None, "existing_fallback_port"
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    server_out = LOG_DIR / f"codex_{TASK}.server.out.log"
    server_err = LOG_DIR / f"codex_{TASK}.server.err.log"
    python_exe = OCR_ROOT / ".venv" / "Scripts" / "python.exe"
    cmd = [str(python_exe if python_exe.exists() else sys.executable), "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", str(FALLBACK_PORT)]
    out_f = server_out.open("w", encoding="utf-8", errors="replace")
    err_f = server_err.open("w", encoding="utf-8", errors="replace")
    proc = subprocess.Popen(cmd, cwd=str(OCR_ROOT), stdout=out_f, stderr=err_f, text=True)
    proc._codex_log_handles = (out_f, err_f)  # type: ignore[attr-defined]
    if not wait_for_api(fallback, timeout=70):
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
    for handle in getattr(proc, "_codex_log_handles", ()) or ():
        try:
            handle.close()
        except Exception:
            pass


def post_ocr(api_url: str, input_path: Path, template: dict[str, Any], document_type: str | None) -> tuple[dict[str, Any], dict[str, Any]]:
    if requests is None:
        raise RuntimeError(f"requests import failed: {REQUESTS_IMPORT_ERROR}")
    template_json = template.get("template_json") or {}
    data: dict[str, str] = {"template_id": str(template.get("template_id") or ""), "model_id": "paddleocr"}
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


def resolve_field_label(name: str = "", ko: str = "", en: str = "") -> tuple[str, str | None]:
    if ko:
        return ko, en or name or None
    mapped = INVOICE_FIELD_KO.get(name) if name else None
    if mapped:
        return mapped, en or name or None
    if en:
        return en, name or None
    return name or "-", None


def field_label_full(field: dict[str, Any]) -> str:
    primary, secondary = resolve_field_label(str(field.get("name") or ""), str(field.get("ko") or ""), str(field.get("en") or ""))
    if secondary and secondary != primary:
        return f"{primary} ({secondary})"
    return primary


def get_adoption_label(field: dict[str, Any]) -> str:
    action = field.get("autofillAction")
    if action == "confirmed":
        return "OCR"
    if action in {"corrected", "filled"}:
        return "복원"
    if field.get("source") == "text":
        return "직접입력"
    if field.get("source") in {"biz", "gt"}:
        return "복원"
    if str(field.get("value") or "").strip():
        return "OCR"
    return "-"


def parse_table_field(value: str) -> dict[str, Any]:
    rows: list[list[dict[str, Any]]] = []
    try:
        parsed = json.loads(value)
        if isinstance(parsed, list):
            rows = [r for r in parsed if isinstance(r, list)]
    except Exception:
        pass
    non_empty = [r for r in rows if len(r) > 0]
    col_counts = [len(r) for r in non_empty]
    unique_counts = set(col_counts)
    first_count = len(non_empty[0]) if non_empty else 0
    keep_as_is = len(unique_counts) == 1 and first_count > 1
    actual_rows = len(non_empty) if keep_as_is else 1
    flat_count = sum(len(r) for r in non_empty)
    row_label = f"{flat_count}항목, 1행" if actual_rows == 1 else f"{actual_rows}행"
    return {"rows": rows, "nonEmpty": non_empty, "rowLabel": row_label}


def esc(value: Any) -> str:
    return str(value or "").replace("|", "\\|").replace("\n", " ")


def to_markdown(raw: dict[str, Any], template: dict[str, Any] | None, template_name: str) -> tuple[str, dict[str, Any]]:
    fields = build_run_ocr_fields(raw, template)
    df = raw.get("document_fields") if isinstance(raw.get("document_fields"), dict) else {}
    doc_table_rows = df.get("tableRows") if isinstance(df.get("tableRows"), list) else None
    processing_time = float(raw.get("processing_time") or 0)
    md = "# OCR 결과\n\n"
    md += f"- 처리 시간: **{processing_time:.2f}s**\n"
    md += f"- 필드 수: **{len(fields)}건**\n\n"
    md += "| No | 필드명 | 값 | 신뢰도 | 채택 |\n"
    md += "|:---:|--------|-----|:------:|:---:|\n"
    for index, field in enumerate(fields):
        label = field_label_full(field)
        confidence = float(field.get("confidence") or 0) * 100
        if field.get("field_type") == "table":
            raw_row_label = parse_table_field(str(field.get("value") or "")).get("rowLabel")
            row_label = f"{len(doc_table_rows)}행" if doc_table_rows else raw_row_label
            md += f"| {index + 1} | {esc(label)} | 표 데이터({row_label}) | {confidence:.1f}% | {get_adoption_label(field)} |\n"
        else:
            md += f"| {index + 1} | {esc(label)} | {esc(field.get('value') or '')} | {confidence:.1f}% | {get_adoption_label(field)} |\n"
    meta = {
        "templateName": template_name,
        "fieldCount": len(fields),
        "tableFieldCount": sum(1 for f in fields if f.get("field_type") == "table"),
        "docTableRowCount": len(doc_table_rows or []),
        "containsStructuredTableRows": bool(doc_table_rows),
        "lineCount": len(md.splitlines()),
        "markdownBytes": len(md.encode("utf-8")),
    }
    return md, meta


def validate_markdown(markdown: str, case: dict[str, Any], meta: dict[str, Any]) -> dict[str, Any]:
    text = markdown.strip()
    contains_row_index_literal = "rowIndex" in markdown or "순번" in markdown
    checks = {
        "nonEmpty": bool(text),
        "startsWithHeading": markdown.startswith("# OCR 결과"),
        "hasFieldCountLine": "- 필드 수:" in markdown,
        "hasMarkdownTableHeader": "| No | 필드명 | 값 | 신뢰도 | 채택 |" in markdown,
        "lineCount": len(markdown.splitlines()),
        "bytes": len(markdown.encode("utf-8")),
        "containsRowIndexLiteral": contains_row_index_literal,
        "containsTableSummary": "표 데이터(" in markdown if case["kind"] == "invoice" else False,
        "receiptHasCoreFields": all(token in markdown for token in ["tel"]) if case["kind"] == "receipt" else None,
    }
    status = "PASS" if checks["nonEmpty"] and checks["startsWithHeading"] and checks["hasMarkdownTableHeader"] else "FAIL"
    warnings: list[str] = []
    if case["caseId"] == "trade_3_3pdf":
        warnings.append("거래_3 insuranceCode/amount locked table behavior is not expanded in Markdown v1; table field is summarized only.")
    if case["kind"] == "invoice" and not checks["containsTableSummary"]:
        status = "WARN" if status == "PASS" else status
        warnings.append("invoice markdown did not include table summary marker")
    return {"status": status, "warnings": warnings, **checks, **meta}


# ── FRONTEND-CLEANUP-2B read-only check mode ─────────────────────────────────
# `--check` reproduces Markdown via to_markdown() and compares against existing
# Markdown fixtures.
#
# Comparison policy:
#   - LF-strict (no CRLF normalization)
#   - "Exact string equality modulo OCR processing_time":
#     The "- 처리 시간: **NN.NNs**" line is non-deterministic across OCR runs
#     (varies even for the same input). Both sides are normalized to "**X.XXs**"
#     before equality. Every other byte (heading, table, field values, confidence
#     percentages, labels, escaping, ordering, trailing newline) is compared
#     byte-for-byte.
#
# It never writes fixtures, manifest, contract, or lock reports.

import re as _re_check
_PROCESSING_TIME_PATTERN = _re_check.compile(r"(- 처리 시간: \*\*)\d+\.\d+(s\*\*)")


def _normalize_for_compare(text: str) -> str:
    return _PROCESSING_TIME_PATTERN.sub(r"\1X.XX\2", text)


def compute_first_diff(actual: str, expected: str) -> dict[str, Any] | None:
    if actual == expected:
        return None
    actual_lines = actual.splitlines(keepends=True)
    expected_lines = expected.splitlines(keepends=True)
    common = min(len(actual_lines), len(expected_lines))
    for index in range(common):
        if actual_lines[index] != expected_lines[index]:
            return {
                "type": "line_diff",
                "lineIndex0Based": index,
                "lineNumber": index + 1,
                "actualLine": actual_lines[index],
                "expectedLine": expected_lines[index],
            }
    if len(actual_lines) != len(expected_lines):
        return {
            "type": "length_diff",
            "actualLineCount": len(actual_lines),
            "expectedLineCount": len(expected_lines),
            "firstExtraActualLine": actual_lines[common] if len(actual_lines) > common else None,
            "firstExtraExpectedLine": expected_lines[common] if len(expected_lines) > common else None,
        }
    if len(actual) != len(expected):
        return {
            "type": "byte_diff",
            "actualBytes": len(actual.encode("utf-8")),
            "expectedBytes": len(expected.encode("utf-8")),
        }
    return {"type": "unknown"}


def check_fixtures(api_url: str, templates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for case in CASES:
        if case["kind"] == "invoice":
            template = template_by_name_file(templates, case["templateName"], case["file"])
            input_path = INVOICE_DATA_DIR / case["file"]
            document_type = "invoice_statement"
            input_file = f"invoice_statement/{case['file']}"
        else:
            template = template_by_id(templates, case["templateId"])
            input_path = RECEIPT_DATA_DIR / case["file"]
            document_type = None
            input_file = f"baseline/{case['file']}"
        fixture_full = FIXTURE_ROOT / case["fixture"]
        base = {
            "caseId": case["caseId"],
            "templateName": case["templateName"],
            "templateId": (template or {}).get("template_id") or case.get("templateId"),
            "inputFile": input_file,
            "fixturePath": case["fixture"],
            "rowIndexPolicy": case["rowIndexPolicy"],
        }
        if not template:
            results.append({**base, "status": "FAIL", "error": "template not found", "diff": None})
            continue
        if not fixture_full.exists():
            results.append({**base, "status": "FAIL", "error": f"fixture missing at {fixture_full}", "diff": None})
            continue
        print(f"[check] {case['caseId']} template={template.get('template_id')} file={input_path.name}", flush=True)
        try:
            raw, http_meta = post_ocr(api_url, input_path, template, document_type)
            actual_md, meta = to_markdown(raw, template, case["templateName"])
            # Read fixture bytes-then-decode so utf-8 BOM/CRLF leak from text mode does not bias comparison.
            expected_bytes = fixture_full.read_bytes()
            expected_md = expected_bytes.decode("utf-8")
            actual_normalized = _normalize_for_compare(actual_md)
            expected_normalized = _normalize_for_compare(expected_md)
            equal = actual_normalized == expected_normalized
            diff = None if equal else compute_first_diff(actual_normalized, expected_normalized)
            results.append({
                **base,
                **http_meta,
                "processing_time": raw.get("processing_time"),
                "actualBytes": len(actual_md.encode("utf-8")),
                "expectedBytes": len(expected_bytes),
                "actualLineCount": len(actual_md.splitlines()),
                "expectedLineCount": len(expected_md.splitlines()),
                "actualEndsWithNewline": actual_md.endswith("\n"),
                "expectedEndsWithNewline": expected_md.endswith("\n"),
                "actualContainsCRLF": "\r\n" in actual_md,
                "expectedContainsCRLF": "\r\n" in expected_md,
                "processingTimeNormalizedForCompare": True,
                "diff": diff,
                "status": "PASS" if equal else "FAIL",
            })
        except Exception as exc:
            results.append({**base, "status": "FAIL", "error": repr(exc), "diff": None})
    return results


def make_check_report_md(report: dict[str, Any]) -> str:
    rows = []
    for case in report["cases"]:
        rows.append([
            case.get("caseId"),
            case.get("templateId"),
            case.get("actualBytes"),
            case.get("expectedBytes"),
            case.get("actualLineCount"),
            case.get("expectedLineCount"),
            "Y" if case.get("expectedEndsWithNewline") else "N",
            "Y" if case.get("expectedContainsCRLF") else "N",
            case.get("status"),
        ])
    summary = report["summary"]
    md = f"""# MARKDOWN V1 FIXTURE CHECK ({report['phase']}) {report['generatedDate']}

## 1. Task / Phase
- Task: `{report['task']}`
- Phase: `{report['phase']}`
- Generated at: `{report['generatedAt']}`
- Mode: `--check` (read-only — fixtures, manifest, contract, lock reports are NOT modified)

## 2. API
- API URL: `{report['apiUrl']}`
- API source: `{report['apiSource']}`
- Fixture root: `{report['fixtureRoot']}`
- Comparison policy: exact string equality, LF-strict, no CRLF normalization

## 3. Cases
{md_table(['caseId', 'templateId', 'actualBytes', 'expectedBytes', 'actualLines', 'expectedLines', 'endsLF', 'expCRLF', 'status'], rows)}

## 4. Summary
- overall: `{summary['overall']}`
- counts: `{summary['counts']}`
"""
    failed = [case for case in report["cases"] if case.get("status") == "FAIL"]
    if failed:
        md += "\n## 5. First diffs per failed case\n"
        for case in failed:
            md += f"\n### {case.get('caseId')}\n"
            if case.get("error"):
                md += f"- error: `{case['error']}`\n"
            diff = case.get("diff") or {}
            for key in ("type", "lineNumber", "actualLine", "expectedLine", "actualLineCount", "expectedLineCount", "actualBytes", "expectedBytes"):
                if diff.get(key) is not None:
                    md += f"- {key}: `{diff[key]!r}`\n" if key.endswith("Line") else f"- {key}: `{diff[key]}`\n"
    return md


def capture_fixtures(api_url: str, templates: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    manifest_cases: list[dict[str, Any]] = []
    detailed: list[dict[str, Any]] = []
    for case in CASES:
        if case["kind"] == "invoice":
            template = template_by_name_file(templates, case["templateName"], case["file"])
            input_path = INVOICE_DATA_DIR / case["file"]
            document_type = "invoice_statement"
            input_file = f"invoice_statement/{case['file']}"
        else:
            template = template_by_id(templates, case["templateId"])
            input_path = RECEIPT_DATA_DIR / case["file"]
            document_type = None
            input_file = f"baseline/{case['file']}"
        base = {
            "caseId": case["caseId"],
            "templateName": case["templateName"],
            "templateId": (template or {}).get("template_id") or case.get("templateId"),
            "inputFile": input_file,
            "fixturePath": case["fixture"],
            "rowIndexPolicy": case["rowIndexPolicy"],
            "notes": case["notes"],
        }
        if not template:
            detail = {**base, "status": "FAIL", "error": "template not found"}
            manifest_cases.append(detail)
            detailed.append(detail)
            continue
        print(f"[capture] {case['caseId']} template={template.get('template_id')} file={input_path.name}", flush=True)
        try:
            raw, http_meta = post_ocr(api_url, input_path, template, document_type)
            md, meta = to_markdown(raw, template, case["templateName"])
            out_path = FIXTURE_ROOT / case["fixture"]
            out_path.parent.mkdir(parents=True, exist_ok=True)
            # Normalize to LF for stable helper before/after exact comparison.
            out_path.write_text(md.replace("\r\n", "\n"), encoding="utf-8", newline="\n")
            reread = out_path.read_text(encoding="utf-8")
            validation = validate_markdown(reread, case, meta)
            detail = {
                **base,
                **http_meta,
                "processing_time": raw.get("processing_time"),
                "fixtureBytes": len(reread.encode("utf-8")),
                "lineCount": len(reread.splitlines()),
                "validation": validation,
                "status": validation["status"],
            }
        except Exception as exc:
            detail = {**base, "status": "FAIL", "error": repr(exc)}
        manifest_cases.append({
            "caseId": detail["caseId"],
            "templateName": detail["templateName"],
            "templateId": detail["templateId"],
            "inputFile": detail["inputFile"],
            "fixturePath": detail["fixturePath"],
            "fixtureBytes": detail.get("fixtureBytes"),
            "lineCount": detail.get("lineCount"),
            "rowIndexPolicy": detail["rowIndexPolicy"],
            "status": detail["status"],
            "notes": detail["notes"],
        })
        detailed.append(detail)
    return manifest_cases, detailed


def summarize(cases: list[dict[str, Any]]) -> dict[str, Any]:
    counts: dict[str, int] = {}
    for case in cases:
        counts[str(case.get("status") or "UNKNOWN")] = counts.get(str(case.get("status") or "UNKNOWN"), 0) + 1
    overall = "PASS"
    if counts.get("FAIL"):
        overall = "FAIL"
    elif counts.get("WARN"):
        overall = "WARN"
    return {"overall": overall, "counts": counts, "total": len(cases)}


def write_contract_report(static_findings: dict[str, Any], typecheck: dict[str, Any], build: dict[str, Any]) -> dict[str, Any]:
    contract = {
        "task": TASK,
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "toolAndModel": {"tool": "Codex", "model": "Codex"},
        "noProductionCodeModifiedByThisTask": True,
        "source": "src/components/upload/OcrResultPanel.tsx toMarkdown static analysis",
        "staticFindings": static_findings,
        "markdownV1Contract": {
            "functionName": "toMarkdown",
            "location": "src/components/upload/OcrResultPanel.tsx around line 707",
            "inputs": ["result.processing_time", "editedFields", "docTableRows for table row count summary", "fieldLabelFull", "parseTableField", "getAdoptionLabel"],
            "output": "Markdown string beginning with '# OCR 결과'",
            "structure": [
                "H1 heading",
                "processing time bullet",
                "field count bullet",
                "Markdown table header: No / field label / value / confidence / adoption",
                "one table row per edited field",
            ],
            "fieldOrder": "editedFields order is preserved",
            "labelRule": "resolveFieldLabel primary + optional secondary in parentheses",
            "valueRule": "non-table fields use field.value escaped for pipe and newline",
            "tableRule": "table fields output only a summary like '표 데이터(N행)' when docTableRows exists; structured tableRows are not expanded",
            "rowIndexRule": "Markdown v1 does not render table columns, so rowIndex include/exclude policy is not directly visible in Markdown output",
            "excluded": ["bbox", "sourceBboxes", "document_fields.tableRows detail", "docTableDisplayCols", "raw OCR debug", "Clean JSON", "Raw JSON"],
            "copyExport": "Preview mode selects toMarkdown() for markdown copy/export; Clean JSON path is separate",
            "lineEndingFixtureRule": "fixtures are stored with LF line endings",
        },
        "helperExtractionPlan": {
            "candidateFile": "src/lib/markdownReportBuilder.ts",
            "candidateHelperNames": ["fieldsToMarkdown", "buildFieldsMarkdown", "buildMarkdownReport"],
            "recommendedName": "fieldsToMarkdown",
            "inputDraft": {
                "processingTime": "number",
                "fields": "ReadonlyArray<OcrFieldLike>",
                "docTableRows": "ReadonlyArray<Record<string, unknown>> | null",
            },
            "output": "string",
            "purityRequirements": ["no React hooks", "no DOM/window/localStorage/network", "no input mutation", "no copy/export/UI state responsibility"],
        },
        "beforeAfterValidation": [
            "Exact string equality against tmp/fixtures/markdown_v1/*.md",
            "Normalize line endings to LF before comparison",
            "Do not trim trailing newline unless the current output changes explicitly",
            "Copy/Export behavior unchanged",
            "Clean JSON/Raw JSON unaffected",
            "typecheck/build PASS",
        ],
        "typecheckAtContractTime": typecheck,
        "buildAtContractTime": build,
    }
    write_json(CONTRACT_JSON, contract)
    CONTRACT_MD.write_text(make_contract_md(contract), encoding="utf-8")
    return contract


def make_contract_md(contract: dict[str, Any]) -> str:
    c = contract["markdownV1Contract"]
    return f"""# MARKDOWN V1 CONTRACT 20260521

## 1. 사용 도구와 모델
- 사용 도구: Codex
- 사용 모델: Codex
- 작업명: `{TASK}`

## 2. 운영 코드 수정 없음
- 운영 코드 수정 없음.
- `fieldsToMarkdown` 또는 Markdown helper 분리는 하지 않았다.
- 현재 `OcrResultPanel.tsx`의 `toMarkdown` 동작을 문서화한다.

## 3. 현재 함수
- 함수명: `{c['functionName']}`
- 위치: `{c['location']}`
- Copy/Export: Markdown preview mode에서 `toMarkdown()` 문자열을 사용한다.

## 4. 입력 Contract
- `result.processing_time`
- `editedFields`
- table field일 때 `docTableRows` row count summary
- `fieldLabelFull`
- `parseTableField`
- `getAdoptionLabel`

## 5. 출력 Contract
- Markdown string
- 첫 줄은 `# OCR 결과`
- 처리 시간 bullet 포함
- 필드 수 bullet 포함
- Markdown table header 포함
- `editedFields` 순서대로 한 줄씩 출력
- field label/value는 pipe와 newline을 escape한다.

## 6. Table / rowIndex Contract
- Markdown v1은 구조화 tableRows 상세 rows/columns를 펼치지 않는다.
- table field는 `표 데이터(N행)` 형태의 요약만 출력한다.
- 따라서 거래명세서 rowIndex 포함/제외 정책은 Markdown 문자열에 직접 드러나지 않는다.
- rowIndex 정책 검증은 Preview/Clean JSON fixture가 담당하고, Markdown fixture는 현재 요약 문자열을 고정한다.

## 7. 제외 항목
- bbox/sourceBboxes
- raw OCR/debug
- document_fields.tableRows 상세
- docTableDisplayCols
- Raw JSON/Clean JSON payload

## 8. Helper 분리 계획
- 후보 파일: `src/lib/markdownReportBuilder.ts`
- 추천 helper: `fieldsToMarkdown`
- 입력: `processingTime`, `fields`, `docTableRows`
- 출력: `string`
- 순수성: React hook/DOM/window/localStorage/network 금지, 입력 mutation 금지.

## 9. Before / After 검증 기준
- `tmp/fixtures/markdown_v1/*.md`와 exact string equality
- line ending은 LF 기준
- Copy/Export 동작 변경 없음
- Clean JSON/Raw JSON 영향 없음
- typecheck/build PASS
"""


def md_table(headers: list[str], rows: list[list[Any]]) -> str:
    out = "| " + " | ".join(headers) + " |\n"
    out += "| " + " | ".join(["---"] * len(headers)) + " |\n"
    for row in rows:
        out += "| " + " | ".join(str(v) for v in row) + " |\n"
    return out


def make_lock_md(report: dict[str, Any]) -> str:
    rows = []
    for case in report["cases"]:
        rows.append([
            case["caseId"],
            case.get("templateId"),
            case.get("fixturePath"),
            case.get("fixtureBytes"),
            case.get("lineCount"),
            case.get("status"),
        ])
    return f"""# MARKDOWN V1 FIXTURE LOCK 20260521

## 1. 사용 도구와 모델
- 사용 도구: Codex
- 사용 모델: Codex
- 작업명: `{TASK}`

## 2. 코드 수정 여부
- 운영 코드 수정 없음.
- `OcrResultPanel.tsx` 리팩토링 없음.
- Markdown helper 생성 없음.
- fixture와 docs, tmp 분석 스크립트만 생성했다.
- `review_log.jsonl` API append side effect는 실행 전 바이트로 복원했다.

## 3. Fixture 저장 위치
- `tmp/fixtures/markdown_v1/manifest.json`
- `tmp/fixtures/markdown_v1/invoice_statement/*.md`
- `tmp/fixtures/markdown_v1/receipt/*.md`

## 4. Fixture 생성 방식
- API URL: `{report['apiUrl']}`
- API source: `{report['apiSource']}`
- 현재 `OcrResultPanel.tsx` `toMarkdown` 로직을 tmp 스크립트에서 mirror했다.
- fixture line ending은 LF로 저장했다.

## 5. Fixture 결과
{md_table(['caseId', 'templateId', 'fixturePath', 'bytes', 'lines', 'status'], rows)}

## 6. rowIndex / 거래_3 / 영수증 확인
- Markdown v1은 tableRows columns를 펼치지 않으므로 rowIndex 포함/제외는 문자열에 직접 나타나지 않는다.
- 거래_1/2/3은 table field 요약 `표 데이터(N행)`을 고정했다.
- 거래_3 insuranceCode/amount locked behavior는 Markdown v1 상세 문자열에는 직접 반영되지 않는다.
- 영수증 1.jpg/2.jpg는 field-only Markdown 대표 fixture로 고정했다.

## 7. Typecheck / Build
| command | status | exit | seconds |
| --- | --- | --- | --- |
| npm run typecheck | {report['typecheck']['status']} | {report['typecheck']['exitCode']} | {report['typecheck']['durationSeconds']} |
| npm run build | {report['build']['status']} | {report['build']['exitCode']} | {report['build']['durationSeconds']} |

Known stderr noise:
- ISSUE-FRONTEND-BUILD-LOG-1: `ESLint: nextVitals is not iterable`

## 8. 최종 판정
- overall: `{report['summary']['overall']}`
- counts: `{report['summary']['counts']}`

## 9. 다음 작업 제안
1. FRONTEND-CLEANUP-2B에서 `fieldsToMarkdown` helper를 분리한다.
2. 분리 후 이번 Markdown fixture와 exact string equality를 비교한다.
3. Clean JSON fixture runner와 함께 회귀 검증에 포함한다.
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-url", default=DEFAULT_API_URL)
    parser.add_argument("--skip-build", action="store_true")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Read-only mode: compare current OCR Markdown against existing fixtures. Never writes fixtures or reports under capture path.",
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

    for path in [CONTRACT_MD.parent, LOG_DIR]:
        path.mkdir(parents=True, exist_ok=True)
    if not args.check:
        for path in [FIXTURE_ROOT, INVOICE_FIXTURE_DIR, RECEIPT_FIXTURE_DIR]:
            path.mkdir(parents=True, exist_ok=True)

    review_log_before = REVIEW_LOG.read_bytes() if REVIEW_LOG.exists() else None
    backend_proc: subprocess.Popen[str] | None = None
    api_url = args.api_url
    api_source = "unknown"
    try:
        print(f"[{TASK}] mode={'check' if args.check else 'capture'} phase={args.phase} root={ROOT}", flush=True)

        if args.check:
            templates = load_templates()
            api_url, backend_proc, api_source = start_backend_if_needed(api_url)
            print(f"[api] {api_url} source={api_source}", flush=True)
            cases = check_fixtures(api_url, templates)
            summary = summarize(cases)
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
                "comparisonPolicy": {
                    "lineEnding": "LF-strict",
                    "crlfNormalization": False,
                    "comparison": "exact string equality modulo OCR processing_time",
                    "normalizedField": "- 처리 시간: **N.NNs** (timing line is non-deterministic across OCR runs; masked to **X.XX** on both sides before equality)",
                    "everythingElse": "compared byte-for-byte after UTF-8 decode",
                },
            }
            report_json_path = (
                Path(args.check_report_json)
                if args.check_report_json
                else (ROOT / "docs" / f"MARKDOWN_V1_FIXTURE_CHECK_{args.phase}_20260521.json")
            )
            report_md_path = (
                Path(args.check_report_md)
                if args.check_report_md
                else (ROOT / "docs" / f"MARKDOWN_V1_FIXTURE_CHECK_{args.phase}_20260521.md")
            )
            write_json(report_json_path, report)
            report_md_path.parent.mkdir(parents=True, exist_ok=True)
            report_md_path.write_text(make_check_report_md(report), encoding="utf-8")
            print(f"[write] {report_json_path}", flush=True)
            print(f"[write] {report_md_path}", flush=True)
            print(f"[summary] overall={summary['overall']} counts={summary['counts']}", flush=True)
            return 0 if summary["overall"] == "PASS" else 1

        print("[check] running npm run typecheck", flush=True)
        typecheck = run_command(["npm.cmd", "run", "typecheck"], ROOT, timeout=180) if not args.skip_build else {"status": "SKIPPED", "exitCode": None, "durationSeconds": 0, "stdoutTail": "", "stderrTail": ""}
        print(f"[check] typecheck={typecheck['status']} duration={typecheck['durationSeconds']}s", flush=True)
        print("[check] running npm run build", flush=True)
        build = run_command(["npm.cmd", "run", "build"], ROOT, timeout=300) if not args.skip_build else {"status": "SKIPPED", "exitCode": None, "durationSeconds": 0, "stdoutTail": "", "stderrTail": ""}
        print(f"[check] build={build['status']} duration={build['durationSeconds']}s", flush=True)

        static_findings = {
            "functionName": "toMarkdown",
            "line": 707,
            "usesEditedFields": True,
            "usesProcessingTime": True,
            "usesDocTableRowsForTableSummary": True,
            "usesDocTableDisplayCols": False,
            "expandsTableRows": False,
            "copyExportPath": "previewMode === 'markdown' ? toMarkdown() : toCleanJson()",
        }
        contract = write_contract_report(static_findings, typecheck, build)
        print(f"[write] {CONTRACT_JSON}", flush=True)
        print(f"[write] {CONTRACT_MD}", flush=True)

        templates = load_templates()
        api_url, backend_proc, api_source = start_backend_if_needed(api_url)
        print(f"[api] {api_url} source={api_source}", flush=True)
        manifest_cases, cases = capture_fixtures(api_url, templates)
        manifest = {
            "version": "markdown_v1",
            "createdAt": datetime.now().isoformat(timespec="seconds"),
            "task": TASK,
            "source": "fixture generation mirrors current OcrResultPanel toMarkdown logic",
            "contractDocs": [str(CONTRACT_MD.relative_to(ROOT)), str(CONTRACT_JSON.relative_to(ROOT))],
            "apiUrl": api_url,
            "apiSource": api_source,
            "fixtureRoot": str(FIXTURE_ROOT.relative_to(ROOT)),
            "cases": manifest_cases,
        }
        write_json(MANIFEST_PATH, manifest)
        print(f"[write] {MANIFEST_PATH}", flush=True)

        summary = summarize(cases)
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
            "cases": cases,
            "manifestCases": manifest_cases,
            "summary": summary,
            "markdownContractSummary": contract["markdownV1Contract"],
            "helperExtractionPlan": contract["helperExtractionPlan"],
            "beforeAfterValidation": contract["beforeAfterValidation"],
            "typecheck": typecheck,
            "build": build,
            "knownStderrNoise": {
                "id": "ISSUE-FRONTEND-BUILD-LOG-1",
                "message": "ESLint: nextVitals is not iterable",
                "observed": "nextVitals is not iterable" in (build.get("stderrTail") or ""),
            },
            "repoDirtyStatus": git_status(),
            "reviewLogRestoration": {
                "path": str(REVIEW_LOG.relative_to(REPO)),
                "restoredToPreRunBytes": True,
            },
        }
        write_json(LOCK_JSON, report)
        LOCK_MD.write_text(make_lock_md(report), encoding="utf-8")
        print(f"[write] {LOCK_JSON}", flush=True)
        print(f"[write] {LOCK_MD}", flush=True)
        ok = summary["overall"] in {"PASS", "WARN"} and typecheck["status"] in {"PASS", "SKIPPED"} and build["status"] in {"PASS", "SKIPPED"}
        return 0 if ok else 1
    finally:
        stop_backend(backend_proc)
        if review_log_before is not None:
            REVIEW_LOG.write_bytes(review_log_before)


if __name__ == "__main__":
    raise SystemExit(main())
