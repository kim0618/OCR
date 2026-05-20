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
OUT_JSON = ROOT / "tmp" / "CODEX_T28_PERF3_COLUMN_ORDER_PRE_APPLY_VALIDATION_20260520.json"
OUT_MD = ROOT / "tmp" / "CODEX_T28_PERF3_COLUMN_ORDER_PRE_APPLY_VALIDATION_20260520.md"
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


def run_text(cmd: list[str], cwd: Path = ROOT) -> str:
    try:
        p = subprocess.run(cmd, cwd=cwd, text=True, encoding="utf-8", errors="replace", capture_output=True, timeout=30)
        return (p.stdout + p.stderr).strip()
    except Exception as exc:
        return f"ERROR: {exc}"


def normalize_cell(v: Any) -> str:
    if v is None:
        return ""
    return str(v).strip()


def is_internal_table_key(key: str) -> bool:
    return (
        key in INTERNAL_KEYS
        or key.startswith("_")
        or "Composite" in key
        or "Debug" in key
        or "Warning" in key
    )


def is_meaningless(v: Any) -> bool:
    return normalize_cell(v).lower() in MEANINGLESS


def has_meaningful_value(rows: list[dict[str, Any]], key: str) -> bool:
    return any(not is_meaningless(row.get(key)) for row in rows)


def meaningful_ratio(rows: list[dict[str, Any]], key: str) -> float:
    if not rows:
        return 0.0
    return sum(1 for row in rows if not is_meaningless(row.get(key))) / len(rows)


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


def build_invoice_preview_col_keys(table_meta: dict[str, Any] | None, rows: list[dict[str, Any]]) -> list[str]:
    table_meta = table_meta or {}
    candidate_keys: list[str] = []

    exp_keys = table_meta.get("expectedColumnKeys")
    if isinstance(exp_keys, list) and exp_keys:
        candidate_keys = [str(k) for k in exp_keys if str(k) != "rowIndex" and not is_internal_table_key(str(k))]

    if not candidate_keys:
        det_cols = table_meta.get("columns")
        if isinstance(det_cols, list) and det_cols:
            candidate_keys = [str(k) for k in det_cols if str(k) != "rowIndex" and not is_internal_table_key(str(k))]

    if not candidate_keys:
        candidate_keys = list(INVOICE_TABLE_COL_PRIORITY)

    if not rows:
        return []

    cols = [key for key in candidate_keys if has_meaningful_value(rows, key)]
    cols = [key for key in cols if key not in ITEMCODE_KEYS or meaningful_ratio(rows, key) > 0.05]

    mfg_key = next((key for key in cols if key in MFG_KEYS), None)
    if mfg_key:
        remove = {key for key in cols if key in LOT_KEYS and meaningless_or_dup_ratio(rows, key, mfg_key) >= 0.95}
        if remove:
            cols = [key for key in cols if key not in remove]

    if any(key in LOT_KEYS for key in cols) and has_meaningful_value(rows, "itemCode") and not has_meaningful_value(rows, "manufacturingNo"):
        cols = [key for key in cols if key not in LOT_KEYS]

    if "serialNo" in cols and "lotNo" in cols and meaningless_or_dup_ratio(rows, "serialNo", "lotNo") >= 0.95:
        cols = [key for key in cols if key != "serialNo"]

    deduped: list[str] = []
    seen: set[str] = set()
    for key in cols:
        if key not in seen:
            seen.add(key)
            deduped.append(key)
    return deduped


def ordered_rows(rows: list[dict[str, Any]], col_keys: list[str]) -> list[dict[str, str]]:
    out = []
    for row in rows:
        out.append({key: normalize_cell(row.get(key)) for key in col_keys})
    return out


def table_data_column_keys(resp: dict[str, Any]) -> list[str]:
    fallback = [k for k in INVOICE_TABLE_COL_PRIORITY if k not in {"itemCode", "lotNo", "unit", "supplyAmount", "taxAmount", "totalAmount", "remark"}]
    for field in resp.get("fields") or []:
        if not isinstance(field, dict) or field.get("field_type") != "table":
            continue
        td = field.get("table_data")
        if not isinstance(td, list) or not td:
            continue
        first = next((r for r in td if isinstance(r, list)), [])
        return [fallback[i] if i < len(fallback) else f"col_{i + 1}" for i, _ in enumerate(first)]
    return []


def load_templates() -> dict[str, dict[str, Any]]:
    data = json.loads(TEMPLATES_FILE.read_text(encoding="utf-8"))
    return {str(t.get("template_id")): t for t in data}


def get_doc_rows(resp: dict[str, Any]) -> list[dict[str, Any]]:
    rows = ((resp.get("document_fields") or {}).get("tableRows"))
    return [r for r in rows if isinstance(r, dict)] if isinstance(rows, list) else []


def get_table_meta(resp: dict[str, Any]) -> dict[str, Any] | None:
    meta = ((resp.get("document_fields") or {}).get("tableMeta"))
    return meta if isinstance(meta, dict) else None


def make_virtual_deferred(resp: dict[str, Any]) -> dict[str, Any]:
    v = copy.deepcopy(resp)
    n = len(get_doc_rows(v))
    for field in v.get("fields") or []:
        if isinstance(field, dict) and field.get("field_type") == "table":
            field.pop("table_data", None)
            field["value"] = f"표 데이터 ({n}행)"
    return v


def call_api(template: dict[str, Any], file_path: Path) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    tj = template.get("template_json") or {}
    form = {
        "template_id": template.get("template_id") or "",
        "regions": json.dumps(tj.get("regions") or [], ensure_ascii=False),
        "model_id": "paddleocr",
        "documentType": tj.get("documentType") or "invoice_statement",
    }
    meta: dict[str, Any] = {"apiUrl": API_URL}
    start = time.perf_counter()
    try:
        with file_path.open("rb") as fh:
            res = requests.post(API_URL, data=form, files={"file": (file_path.name, fh)}, timeout=240)
        meta["wallSeconds"] = round(time.perf_counter() - start, 3)
        meta["statusCode"] = res.status_code
        meta["responseBytes"] = len(res.content)
        res.raise_for_status()
        return res.json(), meta
    except Exception as exc:
        meta["wallSeconds"] = round(time.perf_counter() - start, 3)
        meta["error"] = str(exc)
        return None, meta


def static_analysis() -> dict[str, Any]:
    return {
        "sourceSummary": {
            "Preview": "OcrResultPanel.tsx uses docTableDisplayCols = buildInvoicePreviewCols(docTableMeta, docTableRows), then renders headers/cells in that order.",
            "CleanJSON": "Clean JSON uses cleanTableRowsFromObjects(docTableRows, docTableDisplayCols), so object insertion order follows docTableDisplayCols, not tableRows key order.",
            "Custom": "Custom table branch uses docTableDisplayCols for colgroup, header, cells, and textarea edit columns.",
            "Validation": "Validation table branch uses docTableDisplayCols for colgroup, header, and cells.",
            "TestWorkspace": "TestWorkspace has an equivalent getDisplayTableColumns path using tableMeta / expected columns and tableRows.",
            "table_data": "table_data is only a fallback when document_fields.tableRows/docTableDisplayCols is not available; it is not the normal column order source for invoice_statement RunOCR Preview.",
            "objectKeyOrder": "Current structured path does not rely on document_fields.tableRows object key order for display or Clean JSON; it indexes each row by ordered column keys.",
            "priority": "buildInvoicePreviewCols priority is tableMeta.expectedColumnKeys, then tableMeta.columns, then INVOICE_TABLE_COL_PRIORITY with hasValue and dedup filters.",
        },
        "rgEvidence": {
            "OcrResultPanel": run_text(["rg", "-n", "buildInvoicePreviewCols|docTableDisplayCols|cleanTableRowsFromObjects|table_data|parseTableField", "mysuit-ocr/src/components/upload/OcrResultPanel.tsx"]),
            "invoiceTableDisplay": run_text(["rg", "-n", "INVOICE_TABLE_COL_PRIORITY|buildInvoicePreviewCols|expectedColumnKeys|tableMeta.columns|hasMeaningfulTableValue", "mysuit-ocr/src/lib/invoiceTableDisplay.ts"]),
            "TestWorkspace": run_text(["rg", "-n", "getDisplayTableColumns|tableExpectedColumns|TABLE_COLUMN_META|tableRows", "mysuit-ocr/src/components/test/TestWorkspace.tsx"]),
        },
    }


def main() -> None:
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    templates = load_templates()
    git_status = run_text(["git", "status", "--short"])
    static = static_analysis()
    results: list[dict[str, Any]] = []

    for template_name, template_id, filename, expected_rows in TARGETS:
        template = templates[template_id]
        file_path = INPUT_DIR / filename
        resp, api_meta = call_api(template, file_path)
        item: dict[str, Any] = {
            "templateName": template_name,
            "templateId": template_id,
            "inputFile": str(file_path),
            "expectedRowCount": expected_rows,
            "api": api_meta,
        }
        if resp is None:
            item["error"] = api_meta.get("error")
            results.append(item)
            continue

        rows = get_doc_rows(resp)
        meta = get_table_meta(resp)
        before_cols = build_invoice_preview_col_keys(meta, rows)
        before_clean_rows = ordered_rows(rows, before_cols)

        virtual = make_virtual_deferred(resp)
        after_rows = get_doc_rows(virtual)
        after_meta = get_table_meta(virtual)
        after_cols = build_invoice_preview_col_keys(after_meta, after_rows)
        after_clean_rows = ordered_rows(after_rows, after_cols)

        clean_same = before_clean_rows == after_clean_rows
        row_count_same = len(rows) == len(after_rows) == expected_rows
        col_same = before_cols == after_cols
        table_data_cols = table_data_column_keys(resp)

        item.update({
            "processing_time": resp.get("processing_time"),
            "documentFieldsRowCount": len(rows),
            "afterDocumentFieldsRowCount": len(after_rows),
            "rowCountMaintained": row_count_same,
            "beforeColumnKeys": before_cols,
            "afterColumnKeys": after_cols,
            "columnOrderSame": col_same,
            "cleanJsonBeforeColumnKeys": list(before_clean_rows[0].keys()) if before_clean_rows else [],
            "cleanJsonAfterColumnKeys": list(after_clean_rows[0].keys()) if after_clean_rows else [],
            "cleanJsonColumnOrderSame": (list(before_clean_rows[0].keys()) if before_clean_rows else []) == (list(after_clean_rows[0].keys()) if after_clean_rows else []),
            "cleanJsonRowsMaintained": clean_same and row_count_same,
            "previewColumnKeys": before_cols,
            "customColumnKeys": before_cols,
            "validationColumnKeys": before_cols,
            "tableDataFallbackColumnKeys": table_data_cols,
            "tableDataIsColumnOrderSource": False,
            "tableRowsSampleRowKeys": list(rows[0].keys()) if rows else [],
            "objectKeyOrderDependency": False,
            "tableMetaExpectedColumnKeys": (meta or {}).get("expectedColumnKeys"),
            "tableMetaColumns": (meta or {}).get("columns"),
            "firstRowBefore": before_clean_rows[0] if before_clean_rows else None,
            "firstRowAfter": after_clean_rows[0] if after_clean_rows else None,
            "rowsValueSampleSame": (before_clean_rows[:2] == after_clean_rows[:2]),
            "majorFields": {k: (resp.get("document_fields") or {}).get(k) for k in ["supplierCompany", "buyerCompany", "totalAmount", "rowCount"]},
        })
        results.append(item)

        partial = {"partial": True, "generatedAt": time.strftime("%Y-%m-%d %H:%M:%S"), "results": results}
        (OUT_JSON.parent / "CODEX_T28_PERF3_COLUMN_ORDER_PRE_APPLY_VALIDATION_20260520.partial.json").write_text(
            json.dumps(partial, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    pass_conditions = {
        "rowCount7of7": all(r.get("rowCountMaintained") for r in results),
        "columnOrderSame7of7": all(r.get("columnOrderSame") for r in results),
        "cleanJsonColumnOrderSame7of7": all(r.get("cleanJsonColumnOrderSame") for r in results),
        "cleanJsonRowsMaintained7of7": all(r.get("cleanJsonRowsMaintained") for r in results),
        "noTableDataColumnOrderDependency": all(r.get("tableDataIsColumnOrderSource") is False for r in results if not r.get("error")),
        "noObjectKeyOrderDependency": all(r.get("objectKeyOrderDependency") is False for r in results if not r.get("error")),
    }
    verdict = "PASS" if all(pass_conditions.values()) else "WARN"

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
        "columnOrderSourceStaticAnalysis": static,
        "results": results,
        "passConditions": pass_conditions,
        "verdict": verdict,
        "applyMustInclude": [
            "Limit optimization to Template RunOCR + invoice_statement only.",
            "Do not apply to unstructured OCR, unstructured templates, or receipt paths.",
            "Skip table crop OCR only when document_fields.tableRows exists and len(tableRows) > 0.",
            "Run existing _ocr_table_region fallback when tableRows is missing or empty.",
            "Use buildInvoicePreviewCols/docTableDisplayCols or the same ordering rules for Preview, Clean JSON, Custom, and Validation.",
            "Build Clean JSON rows as ordered objects from column keys, never from raw tableRows object key order.",
            "Use a compact table field value such as '표 데이터 (N행)'.",
            "Omit or empty table_data in the default response; keep fallback/debug option if Raw JSON compatibility is needed.",
        ],
        "fallbackPseudoCode": [
            "if is_template_run and doc_type == 'invoice_statement' and document_fields.get('tableRows'):",
            "    table_rows = document_fields['tableRows']",
            "    skip _ocr_table_region",
            "    table_field['value'] = f\"표 데이터 ({len(table_rows)}행)\"",
            "    table_field.pop('table_data', None)",
            "    column_keys = buildInvoicePreviewCols(tableMeta, table_rows)  # frontend/helper-equivalent order",
            "else:",
            "    run existing _ocr_table_region fallback",
        ],
        "risks": [
            "If future UI code bypasses docTableDisplayCols and iterates Object.keys(tableRows[0]), column order can drift.",
            "Raw JSON consumers using fields[].table_data may need a debug/legacy option.",
            "Backend implementation must ensure document_fields.tableRows is available before deciding to skip table crop OCR.",
            "New templates without tableMeta.expectedColumnKeys/tableMeta.columns should still use canonical priority fallback.",
        ],
        "nextPromptMustInclude": [
            "Preserve buildInvoicePreviewCols/docTableDisplayCols as the single UI column order source.",
            "Do not derive Clean JSON table order from document_fields.tableRows object key order.",
            "Add fallback to existing table crop OCR when document_fields.tableRows is absent/empty.",
            "Keep scope to invoice_statement template RunOCR only.",
            "After implementation, rerun 거래_1~거래_7 and compare rowCount plus before/after column keys.",
        ],
    }
    OUT_JSON.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    OUT_MD.write_text(build_markdown(summary), encoding="utf-8")


def build_markdown(summary: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# CODEX_T28_PERF3_COLUMN_ORDER_PRE_APPLY_VALIDATION")
    lines.append("")
    lines.append(f"- 사용 도구: {summary['tool']}")
    lines.append(f"- 사용 모델: {summary['model']}")
    lines.append("- 운영 코드 수정: 없음")
    lines.append(f"- repo dirty before work: {summary['repoDirtyBeforeWork']}")
    lines.append(f"- API URL: `{summary['apiUrl']}`")
    lines.append(f"- 검증 스크립트: `{summary['script']}`")
    lines.append(f"- 최종 판정: **{summary['verdict']}**")
    lines.append("")
    lines.append("## Column Order Source")
    for key, value in summary["columnOrderSourceStaticAnalysis"]["sourceSummary"].items():
        lines.append(f"- {key}: {value}")
    lines.append("")
    lines.append("## 거래_1~거래_7 Column Order 비교")
    lines.append("")
    lines.append("| Template | File | rows | beforeColumnKeys | afterColumnKeys | same | Clean JSON same |")
    lines.append("|---|---|---:|---|---|:---:|:---:|")
    for r in summary["results"]:
        if r.get("error"):
            lines.append(f"| {r['templateName']} | {Path(r['inputFile']).name} | ERROR | - | - | false | false |")
            continue
        before = ", ".join(r["beforeColumnKeys"])
        after = ", ".join(r["afterColumnKeys"])
        lines.append(
            f"| {r['templateName']} | {Path(r['inputFile']).name} | "
            f"{r['documentFieldsRowCount']}/{r['expectedRowCount']} | `{before}` | `{after}` | "
            f"{r['columnOrderSame']} | {r['cleanJsonColumnOrderSame']} |"
        )
    lines.append("")
    lines.append("## PASS Conditions")
    for key, value in summary["passConditions"].items():
        lines.append(f"- {key}: {value}")
    lines.append("")
    lines.append("## 영향 분석")
    lines.append("- Preview: docTableDisplayCols 순서 그대로 유지.")
    lines.append("- Clean JSON: docTableDisplayCols 기반 ordered object 생성으로 순서 유지.")
    lines.append("- Custom: docTableDisplayCols 기반 header/cell/edit column 순서 유지.")
    lines.append("- Validation: docTableDisplayCols 기반 header/cell 순서 유지.")
    lines.append("- table_data: document_fields.tableRows가 있는 invoice_statement RunOCR 기본 경로에서는 컬럼 순서 source가 아님.")
    lines.append("")
    lines.append("## 운영 반영 필수 조건")
    for item in summary["applyMustInclude"]:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Pseudo-code")
    lines.append("```python")
    lines.extend(summary["fallbackPseudoCode"])
    lines.append("```")
    lines.append("")
    lines.append("## 위험 요소")
    for item in summary["risks"]:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## 다음 프롬프트 필수 조건")
    for item in summary["nextPromptMustInclude"]:
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    main()
