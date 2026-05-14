"""
T-9: invoice_statement Template/RunOCR saved-annotation E2E verification.

This is a reporting-only script. It does not change extractor logic, template
data, manifest data, or ground truth data. It discovers saved templates,
emulates the current RunOCR upload payload for samples that have a saved table
template, calls the live OCR API, and writes Markdown/JSON reports.
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
BACKEND_DIR = ROOT_DIR / "ocr-server"
TESTSET_DIR = ROOT_DIR / "mysuit-ocr/public/data/testsets/invoice_statement"
REPORT_DIR = TESTSET_DIR / "reports"
TEMPLATES_PATH = BACKEND_DIR / "data/templates.json"
MANIFEST_PATH = TESTSET_DIR / "manifest.json"
T8_FINAL_JSON = REPORT_DIR / "T8_final_invoice_statement_tableRows_stabilization_20260514.json"

OUT_JSON = REPORT_DIR / "T9_template_runocr_e2e_invoice_statement_20260514.json"
OUT_MD = REPORT_DIR / "T9_template_runocr_e2e_invoice_statement_20260514.md"

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


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def md_escape(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        text = json.dumps(value, ensure_ascii=False)
    else:
        text = str(value)
    return text.replace("\n", "<br>").replace("|", "\\|")


def compact_list(values: Any, limit: int = 4) -> str:
    if not values:
        return "-"
    if isinstance(values, str):
        return values
    if not isinstance(values, list):
        return md_escape(values)
    shown = [md_escape(v) for v in values[:limit]]
    if len(values) > limit:
        shown.append(f"+{len(values) - limit}")
    return ", ".join(shown)


def table_regions(regions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        r for r in regions
        if r.get("fieldType") == "table" or r.get("type") == "table"
    ]


def template_summary(template: dict[str, Any]) -> dict[str, Any]:
    tj = template.get("template_json") or {}
    regions = tj.get("regions") or []
    tables = table_regions(regions)
    first_table = tables[0] if tables else {}
    table_meta = first_table.get("table") or {}
    col_x = table_meta.get("colX") or []
    return {
        "templateId": template.get("template_id"),
        "templateName": template.get("template_name"),
        "file": (tj.get("file") or {}).get("name"),
        "mode": tj.get("mode"),
        "regionCount": len(regions),
        "fieldTypes": sorted({str(r.get("fieldType")) for r in regions}),
        "tableRegionCount": len(tables),
        "tableBounds": {
            "x": first_table.get("x"),
            "y": first_table.get("y"),
            "width": first_table.get("width"),
            "height": first_table.get("height"),
        } if first_table else None,
        "colGuidesCount": len(col_x),
        "colGuides": col_x,
        "hasTableRegion": bool(tables),
    }


def discover_templates() -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    templates = load_json(TEMPLATES_PATH, [])
    summaries = [template_summary(t) for t in templates]
    by_file: dict[str, dict[str, Any]] = {}
    for template, summary in zip(templates, summaries):
        filename = summary.get("file")
        if filename and summary.get("hasTableRegion"):
            by_file[str(filename)] = {
                "raw": template,
                "summary": summary,
            }
    return summaries, by_file


def call_runocr_payload(filename: str, template: dict[str, Any]) -> dict[str, Any]:
    tj = template.get("template_json") or {}
    regions = tj.get("regions") or []
    sample_path = TESTSET_DIR / filename
    with sample_path.open("rb") as f:
        files = {"file": (filename, f.read(), SAMPLE_MIMES[filename])}
    data = {
        "template_id": str(template.get("template_id") or ""),
        "regions": json.dumps(regions, ensure_ascii=False),
        "model_id": "",
    }
    started = time.time()
    resp = requests.post(f"{BASE_URL}/ocr/extract", files=files, data=data, timeout=300)
    elapsed = round(time.time() - started, 1)
    resp.raise_for_status()
    payload = resp.json()
    payload["_apiElapsedSec"] = elapsed
    return payload


def normalize_meta(document_fields: dict[str, Any], response: dict[str, Any]) -> dict[str, Any]:
    meta = document_fields.get("tableMeta") or {}
    debug = document_fields.get("tableDebug") or {}
    extract_debug = response.get("extract_debug") or {}
    invoice_debug = extract_debug.get("invoice_statement") or {}
    if not debug and isinstance(invoice_debug, dict):
        debug = invoice_debug.get("tableDebug") or invoice_debug.get("debug") or {}
    return {
        "extractionSource": meta.get("extractionSource") or "",
        "tableBoundsUsed": meta.get("tableBoundsUsed"),
        "tableBoundsSource": meta.get("tableBoundsSource") or "",
        "columnGuidesReceived": meta.get("columnGuidesReceived"),
        "columnGuidesUsed": meta.get("columnGuidesUsed"),
        "columnGuidesCount": meta.get("columnGuidesCount"),
        "expectedValueFillRate": meta.get("expectedValueFillRate"),
        "expectedFilledKeys": meta.get("expectedFilledKeys") or [],
        "expectedMissingKeys": meta.get("expectedMissingKeys") or [],
        "valueMappingWarnings": meta.get("valueMappingWarnings") or [],
        "rowCount": document_fields.get("rowCount"),
        "debugKeys": sorted(debug.keys()) if isinstance(debug, dict) else [],
        "templatePath": bool(extract_debug.get("template_path")),
    }


def t8_baseline() -> dict[str, Any]:
    data = load_json(T8_FINAL_JSON, {})
    result: dict[str, Any] = {}
    for sample, row in (data.get("samples") or {}).items():
        rc = row.get("rowCount") or {}
        result[sample] = {
            "rowCount": rc.get("ocr") or rc.get("actual"),
            "verdict": row.get("verdict"),
            "displayFillRate": row.get("displayFillRate"),
            "warnings": row.get("warnings") or [],
        }
    return result


def verify() -> dict[str, Any]:
    template_summaries, templates_by_file = discover_templates()
    baseline = t8_baseline()
    samples: dict[str, Any] = {}
    found_issues: list[dict[str, str]] = []

    for sample in SAMPLES:
        gt = GT_ROW_COUNTS[sample]
        entry = {
            "sample": sample,
            "gtRowCount": gt,
            "testBaselineRowCount": baseline.get(sample, {}).get("rowCount"),
            "template": None,
            "runOcrPayload": {
                "regionsPassed": False,
                "tableBoundsDerived": False,
                "columnGuidesDerived": False,
                "docType": None,
            },
            "apiExecuted": False,
            "apiElapsedSec": None,
            "rowCount": None,
            "rowCountStatus": "skipped_no_saved_table_template",
            "documentFieldsHasTableRows": False,
            "documentFieldsHasTableMeta": False,
            "tableMeta": {},
            "error": None,
            "details": "",
        }

        matched = templates_by_file.get(sample)
        if not matched:
            entry["details"] = "저장된 table region template annotation이 없어 실제 RunOCR E2E 호출을 생략함"
            found_issues.append({
                "sample": sample,
                "issue": "saved table template missing",
                "cause": "templates.json에 해당 샘플 파일명과 연결된 table region annotation이 없음",
                "followup": "UI에서 해당 샘플용 table region/column guide 저장 후 재검증",
            })
            samples[sample] = entry
            continue

        raw_template = matched["raw"]
        summary = matched["summary"]
        entry["template"] = summary
        entry["runOcrPayload"]["regionsPassed"] = True
        entry["runOcrPayload"]["tableBoundsDerived"] = bool(summary.get("tableBounds"))
        entry["runOcrPayload"]["columnGuidesDerived"] = (summary.get("colGuidesCount") or 0) > 0

        try:
            response = call_runocr_payload(sample, raw_template)
            entry["apiExecuted"] = True
            entry["apiElapsedSec"] = response.get("_apiElapsedSec")
            entry["runOcrPayload"]["docType"] = response.get("doc_type")
            document_fields = response.get("document_fields") or {}
            rows = document_fields.get("tableRows") or []
            row_count = document_fields.get("rowCount")
            if row_count is None:
                row_count = len(rows) if isinstance(rows, list) else None
            entry["rowCount"] = row_count
            entry["rowCountStatus"] = "exact" if row_count == gt else "mismatch"
            entry["documentFieldsHasTableRows"] = isinstance(rows, list) and bool(rows)
            entry["documentFieldsHasTableMeta"] = bool(document_fields.get("tableMeta"))
            entry["tableMeta"] = normalize_meta(document_fields, response)
            entry["details"] = "RunOCR payload(template_id + regions) 직접 호출 완료"
            if row_count != gt:
                found_issues.append({
                    "sample": sample,
                    "issue": "rowCount mismatch",
                    "cause": f"RunOCR={row_count}, GT={gt}",
                    "followup": "Template bounds/column guide 좌표와 extractor template path 확인",
                })
            if response.get("doc_type") != "invoice_statement":
                found_issues.append({
                    "sample": sample,
                    "issue": "doc_type not invoice_statement",
                    "cause": f"template region OCR classification returned {response.get('doc_type')}",
                    "followup": "Template field regions에 문서 분류에 충분한 텍스트가 포함되는지 확인",
                })
        except Exception as exc:
            entry["error"] = str(exc)
            entry["rowCountStatus"] = "api_error"
            found_issues.append({
                "sample": sample,
                "issue": "api error",
                "cause": str(exc),
                "followup": "backend API 실행 상태와 template payload 처리 확인",
            })
        samples[sample] = entry

    executed = [s for s in samples.values() if s.get("apiExecuted")]
    exact = [s for s in executed if s.get("rowCountStatus") == "exact"]
    skipped = [s for s in samples.values() if not s.get("apiExecuted")]

    blocking_runtime_issues = any(
        issue.get("issue") in {"rowCount mismatch", "doc_type not invoice_statement", "api error"}
        for issue in found_issues
    )
    if blocking_runtime_issues:
        decision = "Template 저장/전달 문제 있음 -> template path 문서분류/table annotation 보정 후 재검증"
    elif found_issues and skipped:
        decision = "저장 annotation 부족으로 전체 E2E 미완료 -> UI template annotation 저장 후 재검증"
    elif len(exact) == len(SAMPLES):
        decision = "E2E 정상 -> 다음 문서 유형 확장 가능"
    elif executed and len(exact) == len(executed):
        decision = "저장 annotation이 있는 샘플 E2E 정상 -> 나머지 annotation 저장 후 재검증"
    else:
        decision = "Template/RunOCR 연동 보정 필요"

    return {
        "task": "T-9",
        "date": "2026-05-14",
        "baseUrl": BASE_URL,
        "apiDirectCall": bool(executed),
        "actualUiRun": False,
        "historyPersistenceChecked": False,
        "templateSource": str(TEMPLATES_PATH),
        "templateSummaries": template_summaries,
        "samples": samples,
        "summary": {
            "samplesTotal": len(SAMPLES),
            "apiExecuted": len(executed),
            "rowCountExactAmongExecuted": f"{len(exact)}/{len(executed)}" if executed else "0/0",
            "skippedNoSavedTableTemplate": len(skipped),
            "issues": len(found_issues),
        },
        "issues": found_issues,
        "decision": decision,
    }


def render_markdown(report: dict[str, Any]) -> str:
    samples = report["samples"]
    lines: list[str] = []
    lines.append("# T-9 Template/RunOCR E2E invoice_statement 검증 결과")
    lines.append("")
    lines.append("## 1. 생성 파일")
    lines.append(f"- JSON: `{OUT_JSON}`")
    lines.append(f"- Markdown: `{OUT_MD}`")
    lines.append(f"- Script: `{Path(__file__)}`")
    lines.append("")
    lines.append("## 2. 검증 방식")
    lines.append("- 실제 UI 저장 template 사용 여부: `templates.json`에 저장된 annotation을 사용")
    lines.append("- API 직접 호출 여부: 저장 table template이 있는 샘플만 `/ocr/extract` 직접 호출")
    lines.append("- 사용한 payload: RunOCR와 동일하게 `file`, `template_id`, `regions`, `model_id` 전달")
    lines.append("- 한계: 실제 브라우저 UI 클릭 및 History persistence 저장은 수행하지 않음")
    lines.append("")
    lines.append("## 3. Template annotation 확인")
    lines.append("| 샘플 | template 존재 | table region | colGuides | 비고 |")
    lines.append("|---|---|---|---|---|")
    for sample, row in samples.items():
        tmpl = row.get("template") or {}
        exists = "yes" if tmpl else "no"
        table = "yes" if tmpl.get("hasTableRegion") else "no"
        col_guides = tmpl.get("colGuidesCount") if tmpl else "-"
        note = tmpl.get("templateId") or row.get("details")
        lines.append(f"| {sample} | {exists} | {table} | {col_guides} | {md_escape(note)} |")
    lines.append("")
    lines.append("## 4. RunOCR payload 확인")
    lines.append("| 샘플 | regions 전달 | tableBounds 유도 | columnGuides 유도 | doc_type |")
    lines.append("|---|---|---|---|---|")
    for sample, row in samples.items():
        payload = row.get("runOcrPayload") or {}
        lines.append(
            f"| {sample} | {payload.get('regionsPassed')} | "
            f"{payload.get('tableBoundsDerived')} | {payload.get('columnGuidesDerived')} | "
            f"{md_escape(payload.get('docType') or '-')} |"
        )
    lines.append("")
    lines.append("## 5. E2E rowCount 결과")
    lines.append("| 샘플 | GT | RunOCR OCR | Test 기준 | 상태 |")
    lines.append("|---|---:|---:|---:|---|")
    for sample, row in samples.items():
        runocr = row.get("rowCount")
        runocr_text = "-" if runocr is None else str(runocr)
        test_text = row.get("testBaselineRowCount")
        test_text = "-" if test_text is None else str(test_text)
        lines.append(
            f"| {sample} | {row.get('gtRowCount')} | {runocr_text} | "
            f"{test_text} | {md_escape(row.get('rowCountStatus'))} |"
        )
    lines.append("")
    lines.append("## 6. tableMeta/debug 결과")
    lines.append("| 샘플 | extractionSource | tableBoundsUsed | columnGuidesUsed | warnings |")
    lines.append("|---|---|---|---|---|")
    for sample, row in samples.items():
        meta = row.get("tableMeta") or {}
        lines.append(
            f"| {sample} | {md_escape(meta.get('extractionSource') or '-')} | "
            f"{md_escape(meta.get('tableBoundsUsed')) or '-'} | "
            f"{md_escape(meta.get('columnGuidesUsed')) or '-'} | "
            f"{compact_list(meta.get('valueMappingWarnings'))} |"
        )
    lines.append("")
    lines.append("## 7. 샘플별 상세")
    for sample in ["1.jpg", "2.pdf", "5.pdf", "7.pdf"]:
        row = samples[sample]
        meta = row.get("tableMeta") or {}
        detail_row_count = row.get("rowCount")
        detail_row_count_text = "-" if detail_row_count is None else str(detail_row_count)
        lines.append(f"### {sample}")
        lines.append(f"- template: {md_escape((row.get('template') or {}).get('templateId') or 'missing')}")
        lines.append(f"- rowCount: GT {row.get('gtRowCount')} / RunOCR {detail_row_count_text} / 상태 {row.get('rowCountStatus')}")
        lines.append(f"- tableMeta: extractionSource={md_escape(meta.get('extractionSource') or '-')}, templatePath={meta.get('templatePath')}")
        lines.append(f"- 비고: {md_escape(row.get('details') or row.get('error') or '-')}")
        lines.append("")
    lines.append("## 8. 발견된 문제")
    lines.append("| 문제 | 원인 추정 | 후속 |")
    lines.append("|---|---|---|")
    if report.get("issues"):
        for issue in report["issues"]:
            lines.append(
                f"| {md_escape(issue.get('sample'))}: {md_escape(issue.get('issue'))} | "
                f"{md_escape(issue.get('cause'))} | {md_escape(issue.get('followup'))} |"
            )
    else:
        lines.append("| 없음 | 저장 annotation 기준 E2E 회귀 없음 | - |")
    lines.append("")
    lines.append("## 9. 다음 작업 판단")
    lines.append(f"- {report.get('decision')}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    report = verify()
    write_json(OUT_JSON, report)
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    print(report["decision"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
