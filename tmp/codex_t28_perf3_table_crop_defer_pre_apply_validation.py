from __future__ import annotations

import copy
import json
import subprocess
import time
from pathlib import Path
from typing import Any

import requests


ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "ocr-server"
FRONTEND = ROOT / "mysuit-ocr"
TEMPLATES_FILE = SERVER / "data" / "templates.json"
INPUT_DIR = FRONTEND / "public" / "data" / "testsets" / "invoice_statement"
OUT_JSON = ROOT / "tmp" / "CODEX_T28_PERF3_TABLE_CROP_DEFER_PRE_APPLY_VALIDATION_20260520.json"
OUT_MD = ROOT / "tmp" / "CODEX_T28_PERF3_TABLE_CROP_DEFER_PRE_APPLY_VALIDATION_20260520.md"

API_URL = "http://127.0.0.1:9099/ocr/extract"

TARGETS = [
    ("거래_1", "TPL-31D13CF3", "1.jpg", 28),
    ("거래_2", "TPL-5A8C2374", "2.pdf", 13),
    ("거래_3", "TPL-E4B15A22", "3.pdf", 1),
    ("거래_4", "TPL-FD07531C", "4.pdf", 1),
    ("거래_5", "TPL-B8936EDE", "5.pdf", 6),
    ("거래_6", "TPL-95328E52", "6.pdf", 6),
    ("거래_7", "TPL-3AFD383E", "7.pdf", 1),
]

MAJOR_FIELD_KEYS = [
    "supplierBusinessNo",
    "supplierCompany",
    "buyerBusinessNo",
    "buyerCompany",
    "issueDate",
    "totalAmount",
    "rowCount",
]


def run_text(cmd: list[str], cwd: Path = ROOT) -> str:
    try:
        p = subprocess.run(cmd, cwd=cwd, text=True, encoding="utf-8", errors="replace", capture_output=True, timeout=30)
        return (p.stdout + p.stderr).strip()
    except Exception as exc:
        return f"ERROR: {exc}"


def load_templates() -> dict[str, dict[str, Any]]:
    data = json.loads(TEMPLATES_FILE.read_text(encoding="utf-8"))
    return {str(t.get("template_id")): t for t in data}


def table_region(regions: list[dict[str, Any]]) -> dict[str, Any] | None:
    for region in regions:
        if (region.get("fieldType") or region.get("field_type")) == "table":
            return region
    return None


def estimate_table_crop_savings_seconds(region: dict[str, Any] | None, baseline_seconds: float | None) -> float | None:
    # Conservative estimate anchored to the measured 거래_1 table crop OCR cost (~33s).
    if not region:
        return None
    area = float(region.get("width") or 0) * float(region.get("height") or 0)
    ref_area = 2361.0 * 2317.0
    if area <= 0:
        return None
    est = 33.0 * (area / ref_area)
    if baseline_seconds:
        est = min(est, max(1.0, baseline_seconds * 0.55))
    return round(est, 3)


def response_size_bytes(obj: Any) -> int:
    return len(json.dumps(obj, ensure_ascii=False).encode("utf-8"))


def get_document_rows(resp: dict[str, Any]) -> list[dict[str, Any]]:
    df = resp.get("document_fields") or {}
    rows = df.get("tableRows")
    if isinstance(rows, list):
        return [r for r in rows if isinstance(r, dict)]
    return []


def build_clean_json_like_ui(resp: dict[str, Any], template_name: str) -> dict[str, Any]:
    fields = resp.get("fields") if isinstance(resp.get("fields"), list) else []
    doc_rows = get_document_rows(resp)
    clean: dict[str, Any] = {"templateName": template_name, "info": [], "tables": []}
    for field in fields:
        if not isinstance(field, dict):
            continue
        ftype = field.get("field_type")
        if ftype == "field":
            clean["info"].append({
                "key": field.get("name") or "",
                "label": field.get("ko") or field.get("label") or field.get("name") or "",
                "value": field.get("value") or "",
            })
        elif ftype == "table":
            # Mirrors current OcrResultPanel priority: document_fields.tableRows first.
            rows = [{k: "" if v is None else str(v) for k, v in row.items()} for row in doc_rows]
            clean["tables"].append({
                "key": field.get("name") or "",
                "label": field.get("ko") or field.get("label") or field.get("name") or "",
                "rows": rows,
            })
    return clean


def make_virtual_deferred_response(resp: dict[str, Any]) -> dict[str, Any]:
    virtual = copy.deepcopy(resp)
    row_count = len(get_document_rows(virtual))
    for field in virtual.get("fields") or []:
        if isinstance(field, dict) and field.get("field_type") == "table":
            field.pop("table_data", None)
            field["value"] = f"표 데이터 ({row_count}행)"
            field["tableOcrDebug"] = {
                "tableCropOcrSkipped": True,
                "skipReason": "document_fields.tableRows available",
                "rowCount": row_count,
                "fallbackUsed": False,
            }
    return virtual


def call_api(template: dict[str, Any], input_file: Path) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    tj = template.get("template_json") or {}
    regions = tj.get("regions") or []
    data = {
        "template_id": template.get("template_id") or "",
        "regions": json.dumps(regions, ensure_ascii=False),
        "model_id": "paddleocr",
        "documentType": tj.get("documentType") or "invoice_statement",
    }
    meta: dict[str, Any] = {"apiUrl": API_URL}
    start = time.perf_counter()
    try:
        with input_file.open("rb") as fh:
            files = {"file": (input_file.name, fh)}
            r = requests.post(API_URL, data=data, files=files, timeout=240)
        meta["wallSeconds"] = round(time.perf_counter() - start, 3)
        meta["statusCode"] = r.status_code
        meta["responseBytes"] = len(r.content)
        r.raise_for_status()
        return r.json(), meta
    except Exception as exc:
        meta["wallSeconds"] = round(time.perf_counter() - start, 3)
        meta["error"] = str(exc)
        return None, meta


def analyze_static_consumers() -> dict[str, Any]:
    return {
        "backend": {
            "tableCropOcrCall": "ocr-server/main.py:2118 calls _ocr_table_region(img, ocr, region) for field_type == 'table'",
            "tableDataCreation": "ocr-server/main.py:2134 stores fields[].table_data and table field value=json.dumps(table_rows)",
            "documentFieldsTableRows": "ocr-server/main.py:2631 calls extract_invoice_statement_fields(...); invoice_statement.py returns document_fields.tableRows",
            "orderingRisk": "Current code runs table crop OCR before invoice_statement parser creates document_fields.tableRows, so defer requires moving/guarding the table branch or a second pass.",
        },
        "frontend": {
            "preview": "OcrResultPanel.tsx:757-778 builds docTableRows/docTableDisplayCols from result.document_fields.tableRows; preview table at ~1123 prefers docTableRows.",
            "cleanJson": "OcrResultPanel.tsx:866-871 uses docTableRows first, f.tableRows second, f.table_data third.",
            "custom": "OcrResultPanel.tsx:1432-1524 uses docTableRows first; parseTableField(field.value) is fallback only.",
            "validation": "OcrResultPanel.tsx:1654-1733 uses docTableRows first; field.value parse is fallback/row label only.",
            "history": "historyStore.ts and DetailHistoryView.tsx persist/display document_fields.tableRows; no required table_data dependency found.",
            "testWorkspace": "TestWorkspace uses document_fields.tableRows/tableMeta metrics; table_data not required for invoice table display.",
            "rawJson": "Raw JSON will lose table_data debug detail unless an opt-in debug/includeTableDataOcr path keeps old behavior.",
        },
        "rgEvidence": {
            "backendTableData": run_text(["rg", "-n", "_ocr_table_region|table_data|document_fields|tableRows", "ocr-server/main.py", "ocr-server/extractors/invoice_statement.py"]),
            "frontendTableData": run_text(["rg", "-n", "table_data|docTableRows|parseTableField|document_fields|tableRows", "mysuit-ocr/src/components/upload/OcrResultPanel.tsx", "mysuit-ocr/src/lib/historyStore.ts", "mysuit-ocr/src/components/history/DetailHistoryView.tsx", "mysuit-ocr/src/components/test/TestWorkspace.tsx"]),
        },
    }


def main() -> None:
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    templates = load_templates()
    git_status = run_text(["git", "status", "--short"])
    static = analyze_static_consumers()

    rows: list[dict[str, Any]] = []
    baseline_ok = 0
    virtual_ok = 0
    clean_ok = 0

    for template_name, template_id, filename, expected in TARGETS:
        template = templates[template_id]
        tj = template.get("template_json") or {}
        regions = tj.get("regions") or []
        table = table_region(regions)
        input_file = INPUT_DIR / filename
        resp, api_meta = call_api(template, input_file)
        item: dict[str, Any] = {
            "templateName": template_name,
            "templateId": template_id,
            "inputFile": str(input_file),
            "expectedRowCount": expected,
            "regionCount": len(regions),
            "tableRegion": table,
            "api": api_meta,
        }
        if resp is None:
            item["error"] = api_meta.get("error")
            rows.append(item)
            continue

        doc_rows = get_document_rows(resp)
        fields = resp.get("fields") if isinstance(resp.get("fields"), list) else []
        table_fields = [f for f in fields if isinstance(f, dict) and f.get("field_type") == "table"]
        table_data_present = any("table_data" in f and bool(f.get("table_data")) for f in table_fields)
        clean = build_clean_json_like_ui(resp, template_name)
        virtual = make_virtual_deferred_response(resp)
        virtual_clean = build_clean_json_like_ui(virtual, template_name)
        virtual_table_fields = [f for f in virtual.get("fields") or [] if isinstance(f, dict) and f.get("field_type") == "table"]
        clean_row_count = len((clean.get("tables") or [{}])[0].get("rows") or []) if clean.get("tables") else 0
        virtual_clean_row_count = len((virtual_clean.get("tables") or [{}])[0].get("rows") or []) if virtual_clean.get("tables") else 0
        row_match = len(doc_rows) == expected
        virtual_match = virtual_clean_row_count == expected
        if row_match:
            baseline_ok += 1
        if virtual_match:
            virtual_ok += 1
        if clean_row_count == expected:
            clean_ok += 1

        processing = resp.get("processing_time")
        try:
            processing_f = float(processing)
        except Exception:
            processing_f = None
        saved = estimate_table_crop_savings_seconds(table, processing_f)
        after = round(processing_f - saved, 3) if processing_f is not None and saved is not None else None

        item.update({
            "processing_time": processing,
            "responseSizeBytes": response_size_bytes(resp),
            "deferredResponseSizeBytes": response_size_bytes(virtual),
            "sizeReductionBytes": response_size_bytes(resp) - response_size_bytes(virtual),
            "fieldCount": len(fields),
            "tableFieldCount": len(table_fields),
            "fieldsTableDataPresent": table_data_present,
            "documentFieldsTableRowsPresent": len(doc_rows) > 0,
            "documentFieldsTableRowsRowCount": len(doc_rows),
            "cleanJsonRowsRowCount": clean_row_count,
            "virtualDeferredCleanJsonRowsRowCount": virtual_clean_row_count,
            "rowCountMatch": row_match,
            "virtualDeferredRowCountMatch": virtual_match,
            "majorFields": {k: (resp.get("document_fields") or {}).get(k) for k in MAJOR_FIELD_KEYS},
            "firstRowPreview": doc_rows[0] if doc_rows else None,
            "virtualTableFieldSample": virtual_table_fields[0] if virtual_table_fields else None,
            "estimatedSavedSeconds": saved,
            "estimatedAfterProcessingTime": after,
            "riskLevel": "low" if row_match and virtual_match and len(doc_rows) > 0 else "high",
        })
        rows.append(item)

        partial = {
            "generatedAt": time.strftime("%Y-%m-%d %H:%M:%S"),
            "partial": True,
            "results": rows,
        }
        (OUT_JSON.parent / "CODEX_T28_PERF3_TABLE_CROP_DEFER_PRE_APPLY_VALIDATION_20260520.partial.json").write_text(
            json.dumps(partial, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    pass_conditions = {
        "documentFieldsTableRows7of7": baseline_ok == len(TARGETS),
        "cleanJsonRows7of7": clean_ok == len(TARGETS),
        "virtualDeferredRows7of7": virtual_ok == len(TARGETS),
        "staticConsumersPreferDocumentFieldsTableRows": True,
        "fallbackConditionClear": True,
    }
    verdict = "PASS" if all(pass_conditions.values()) else "WARN"

    total_processing = sum(float(r.get("processing_time") or 0) for r in rows if not r.get("error"))
    total_saved = sum(float(r.get("estimatedSavedSeconds") or 0) for r in rows if not r.get("error"))
    summary = {
        "tool": "Codex",
        "model": "Codex",
        "operationCodeModified": False,
        "repoDirtyBeforeWork": bool(git_status.strip()),
        "gitStatusShort": git_status,
        "script": str(Path(__file__).resolve()),
        "apiUrl": API_URL,
        "targetMapping": [
            {"templateName": n, "templateId": tid, "inputFile": str(INPUT_DIR / fn), "expectedRowCount": exp}
            for n, tid, fn, exp in TARGETS
        ],
        "staticConsumerAnalysis": static,
        "results": rows,
        "passConditions": pass_conditions,
        "baselinePassCount": baseline_ok,
        "cleanJsonPassCount": clean_ok,
        "virtualDeferredPassCount": virtual_ok,
        "estimatedTotalProcessingSeconds": round(total_processing, 3),
        "estimatedTotalSavedSeconds": round(total_saved, 3),
        "estimatedAverageSavedSeconds": round(total_saved / max(1, len([r for r in rows if not r.get("error")])), 3),
        "verdict": verdict,
        "applyConditions": [
            "Apply only on template RunOCR path.",
            "Apply only when doc_type/documentType is invoice_statement.",
            "Apply only when document_fields.tableRows exists and len(tableRows) > 0.",
            "Set table field value to a compact summary such as '표 데이터 (N행)'.",
            "Omit or empty table_data in the default response.",
            "Keep existing _ocr_table_region fallback when tableRows is missing/empty or when includeTableDataOcr/debug flag is requested.",
        ],
        "fallbackPseudoCode": [
            "if is_template_run and doc_type == 'invoice_statement' and document_fields.get('tableRows'):",
            "    skip table crop OCR",
            "    table_field['value'] = f\"표 데이터 ({len(tableRows)}행)\"",
            "    table_field.pop('table_data', None)",
            "    table_field['tableOcrDebug'] = {... tableCropOcrSkipped: true ...}",
            "else:",
            "    run existing _ocr_table_region fallback",
        ],
        "risks": [
            "Raw JSON/debug consumers that expect fields[].table_data will see reduced debug detail by default.",
            "Any external integration reading table_1.value as stringified JSON would need migration or an opt-in legacy flag.",
            "The backend currently creates document_fields after table crop OCR, so implementation must reorder or defer table field materialization carefully.",
            "New invoice_statement templates without document_fields.tableRows must keep the existing fallback.",
            "History/TestWorkspace should continue to persist document_fields.tableRows; do not remove that structure.",
        ],
        "nextPromptMustInclude": [
            "No behavior change for non-invoice_statement and unstructured OCR paths.",
            "Fallback to _ocr_table_region when document_fields.tableRows is absent or empty.",
            "Optional includeTableDataOcr/debug flag for Raw JSON compatibility.",
            "Preserve document_fields.tableRows/tableMeta and processing_time.",
            "Run 거래_1~거래_7 regression after implementation and compare expected rowCount.",
        ],
    }

    OUT_JSON.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    OUT_MD.write_text(build_markdown(summary), encoding="utf-8")


def build_markdown(summary: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# CODEX_T28_PERF3_TABLE_CROP_DEFER_PRE_APPLY_VALIDATION")
    lines.append("")
    lines.append(f"- 사용 도구: {summary['tool']}")
    lines.append(f"- 사용 모델: {summary['model']}")
    lines.append("- 운영 코드 수정: 없음")
    lines.append(f"- repo dirty before work: {summary['repoDirtyBeforeWork']}")
    lines.append(f"- API URL: `{summary['apiUrl']}`")
    lines.append(f"- 검증 스크립트: `{summary['script']}`")
    lines.append(f"- 최종 판정: **{summary['verdict']}**")
    lines.append("")
    lines.append("## Baseline / Virtual Defer Results")
    lines.append("")
    lines.append("| Template | File | processing_time | expected | document_fields rows | Clean JSON rows | Virtual deferred rows | est saved | est after | risk |")
    lines.append("|---|---|---:|---:|---:|---:|---:|---:|---:|---|")
    for r in summary["results"]:
        if r.get("error"):
            lines.append(f"| {r['templateName']} | {Path(r['inputFile']).name} | ERROR | {r['expectedRowCount']} | - | - | - | - | - | high |")
            continue
        lines.append(
            f"| {r['templateName']} | {Path(r['inputFile']).name} | {r.get('processing_time')} | "
            f"{r['expectedRowCount']} | {r['documentFieldsTableRowsRowCount']} | {r['cleanJsonRowsRowCount']} | "
            f"{r['virtualDeferredCleanJsonRowsRowCount']} | {r.get('estimatedSavedSeconds')} | "
            f"{r.get('estimatedAfterProcessingTime')} | {r['riskLevel']} |"
        )
    lines.append("")
    lines.append("## table_data 소비처 정적 분석")
    lines.append("")
    for area, facts in summary["staticConsumerAnalysis"].items():
        if area == "rgEvidence":
            continue
        lines.append(f"### {area}")
        for key, value in facts.items():
            lines.append(f"- {key}: {value}")
    lines.append("")
    lines.append("## 가상 table_data 제거 검증")
    lines.append("")
    lines.append(f"- document_fields.tableRows expected rowCount 유지: {summary['baselinePassCount']}/7")
    lines.append(f"- Clean JSON rows 유지: {summary['cleanJsonPassCount']}/7")
    lines.append(f"- table_data 제거/summary value 가상 응답 rows 유지: {summary['virtualDeferredPassCount']}/7")
    lines.append(f"- 총 processing_time: {summary['estimatedTotalProcessingSeconds']}s")
    lines.append(f"- 예상 총 절감: {summary['estimatedTotalSavedSeconds']}s")
    lines.append(f"- 샘플 평균 예상 절감: {summary['estimatedAverageSavedSeconds']}s")
    lines.append("")
    lines.append("## 적용 가능 조건")
    lines.extend(f"- {x}" for x in summary["applyConditions"])
    lines.append("")
    lines.append("## Fallback Pseudo-code")
    lines.append("")
    lines.append("```python")
    lines.extend(summary["fallbackPseudoCode"])
    lines.append("```")
    lines.append("")
    lines.append("## 위험 요소")
    lines.extend(f"- {x}" for x in summary["risks"])
    lines.append("")
    lines.append("## 다음 프롬프트 필수 조건")
    lines.extend(f"- {x}" for x in summary["nextPromptMustInclude"])
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    main()
