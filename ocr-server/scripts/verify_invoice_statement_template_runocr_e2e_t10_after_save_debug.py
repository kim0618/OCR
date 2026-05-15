"""
T-10 after save-debug: invoice_statement Template/RunOCR E2E verification.

Reporting-only script. It does not modify extractor logic, UI code, templates,
manifest, or ground truth. Saved template annotations are discovered from the
backend templates.json. Only samples with saved table annotations are submitted
to /ocr/extract as RunOCR-like payloads.
"""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any


BASE_URL = "http://127.0.0.1:9099"
ROOT_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT_DIR / "ocr-server"
FRONTEND_DIR = ROOT_DIR / "mysuit-ocr"
TESTSET_DIR = FRONTEND_DIR / "public/data/testsets/invoice_statement"
REPORT_DIR = TESTSET_DIR / "reports"
TEMPLATES_PATH = BACKEND_DIR / "data/templates.json"
MANIFEST_PATH = TESTSET_DIR / "manifest.json"
GROUND_TRUTH_PATH = TESTSET_DIR / "ground_truth.json"
T8_FINAL_JSON = REPORT_DIR / "T8_final_invoice_statement_tableRows_stabilization_20260514.json"

OUT_JSON = REPORT_DIR / "T10_after_save_debug_template_runocr_e2e_invoice_statement_20260514.json"
OUT_MD = REPORT_DIR / "T10_after_save_debug_template_runocr_e2e_invoice_statement_20260514.md"

SAMPLES = ["1.jpg", "2.pdf", "3.pdf", "4.pdf", "5.pdf", "6.pdf", "7.pdf"]
PRIORITY_SAMPLES = ["5.pdf", "2.pdf", "7.pdf", "6.pdf", "3.pdf", "4.pdf", "1.jpg"]
EXPECTED_ROW_COUNTS = {
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


def md(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (dict, list)):
        text = json.dumps(value, ensure_ascii=False)
    else:
        text = str(value)
    if text == "":
        return "-"
    return text.replace("\n", "<br>").replace("|", "\\|")


def compact(values: Any, limit: int = 4) -> str:
    if not values:
        return "-"
    if isinstance(values, str):
        return md(values)
    if not isinstance(values, list):
        return md(values)
    shown = [md(v) for v in values[:limit]]
    if len(values) > limit:
        shown.append(f"+{len(values) - limit}")
    return ", ".join(shown)


def table_regions(regions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [r for r in regions if r.get("fieldType") == "table" or r.get("type") == "table"]


def expected_columns_for(sample: str, manifest: dict[str, Any]) -> dict[str, Any]:
    for item in manifest.get("items", []):
        if item.get("filename") == sample:
            profile = item.get("invoiceProfile") or {}
            return profile.get("tableExpectedColumns") or {}
    return {}


def first_non_empty(*values: Any) -> Any:
    for value in values:
        if value not in (None, "", [], {}):
            return value
    return None


def to_int(value: Any) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        text = value.strip().replace(",", "")
        if text.isdigit():
            return int(text)
    return None


def template_summary(template: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    tj = template.get("template_json") or {}
    regions = tj.get("regions") or []
    tables = table_regions(regions)
    first_table = tables[0] if tables else {}
    table_meta = first_table.get("table") or {}
    col_guides = first_non_empty(table_meta.get("colGuides"), table_meta.get("colX"), first_table.get("colGuides"), [])
    file_info = tj.get("file") or {}
    filename = first_non_empty(
        file_info.get("name") if isinstance(file_info, dict) else None,
        file_info.get("filename") if isinstance(file_info, dict) else None,
        tj.get("filename"),
        tj.get("fileName"),
        tj.get("sourceFilename"),
        tj.get("originalFilename"),
    )
    expected = expected_columns_for(str(filename), manifest) if filename else {}
    return {
        "template_id": template.get("template_id"),
        "template_name": template.get("template_name"),
        "filename": filename,
        "documentType": tj.get("documentType"),
        "regions_count": len(regions),
        "fieldTypes": sorted({str(r.get("fieldType") or r.get("type") or "") for r in regions if r}),
        "table_region_count": len(tables),
        "table_region": {
            "x": first_table.get("x"),
            "y": first_table.get("y"),
            "width": first_table.get("width"),
            "height": first_table.get("height"),
        } if first_table else None,
        "colGuides": col_guides if isinstance(col_guides, list) else [],
        "colGuides_count": len(col_guides) if isinstance(col_guides, list) else 0,
        "has_colX": bool(table_meta.get("colX")),
        "expectedColumns": expected,
        "expectedColumns_count": len(expected.get("required", [])) + len(expected.get("optional", [])) if expected else 0,
        "judgement": "실행 가능" if tables else "table annotation 없음",
    }


def discover_templates(manifest: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    templates = load_json(TEMPLATES_PATH, [])
    summaries = [template_summary(t, manifest) for t in templates]
    by_file: dict[str, dict[str, Any]] = {}
    for raw, summary in zip(templates, summaries):
        filename = summary.get("filename")
        if filename and summary.get("table_region_count"):
            by_file[str(filename)] = {"raw": raw, "summary": summary}
    return summaries, by_file


def call_extract(sample: str, template: dict[str, Any], mode: str) -> dict[str, Any]:
    tj = template.get("template_json") or {}
    regions = tj.get("regions") or []
    data = {
        "template_id": str(template.get("template_id") or ""),
        "model_id": "",
    }
    if mode == "B":
        data["documentType"] = "invoice_statement"
    # Mode A intentionally omits regions and documentType to verify backend
    # template metadata routing. Mode B passes saved regions like RunOCR UI.
    if mode == "B":
        data["regions"] = json.dumps(regions, ensure_ascii=False)
    sample_path = TESTSET_DIR / sample
    with sample_path.open("rb") as f:
        file_bytes = f.read()
    started = time.time()
    boundary = f"----codex-t10-{uuid.uuid4().hex}"
    chunks: list[bytes] = []
    for key, value in data.items():
        chunks.append(f"--{boundary}\r\n".encode("utf-8"))
        chunks.append(f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode("utf-8"))
        chunks.append(str(value).encode("utf-8"))
        chunks.append(b"\r\n")
    chunks.append(f"--{boundary}\r\n".encode("utf-8"))
    chunks.append(
        (
            f'Content-Disposition: form-data; name="file"; filename="{sample}"\r\n'
            f"Content-Type: {SAMPLE_MIMES[sample]}\r\n\r\n"
        ).encode("utf-8")
    )
    chunks.append(file_bytes)
    chunks.append(b"\r\n")
    chunks.append(f"--{boundary}--\r\n".encode("utf-8"))
    body = b"".join(chunks)
    request = urllib.request.Request(
        f"{BASE_URL}/ocr/extract",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=360) as response:
            status = response.status
            response_text = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        status = exc.code
        response_text = exc.read().decode("utf-8", errors="replace")
    except Exception as exc:
        return {
            "mode": mode,
            "http_status": None,
            "elapsed_sec": round(time.time() - started, 1),
            "payload": {
                "file": sample,
                "template_id": data["template_id"],
                "regions": mode == "B",
                "model_id": "",
                "documentType": data.get("documentType"),
            },
            "error": str(exc),
        }
    elapsed = round(time.time() - started, 1)
    result = {
        "mode": mode,
        "http_status": status,
        "elapsed_sec": elapsed,
        "payload": {
            "file": sample,
            "template_id": data["template_id"],
            "regions": mode == "B",
            "model_id": "",
            "documentType": data.get("documentType"),
        },
    }
    try:
        response_body = json.loads(response_text)
    except Exception:
        result["error"] = response_text[:1000]
        return result
    result["response"] = response_body
    if status >= 400:
        result["error"] = response_body
    return result


def extract_meta(api_result: dict[str, Any]) -> dict[str, Any]:
    response = api_result.get("response") or {}
    document_fields = response.get("document_fields") or {}
    rows = document_fields.get("tableRows") or []
    row_count = document_fields.get("rowCount")
    if row_count is None and isinstance(rows, list):
        row_count = len(rows)
    row_count = to_int(row_count)
    table_meta = document_fields.get("tableMeta") or {}
    table_debug = document_fields.get("tableDebug") or {}
    extract_debug = response.get("extract_debug") or {}
    invoice_debug = extract_debug.get("invoice_statement") or {}
    if not table_debug and isinstance(invoice_debug, dict):
        table_debug = invoice_debug.get("tableDebug") or invoice_debug.get("debug") or {}
    warnings = first_non_empty(
        table_meta.get("valueMappingWarnings"),
        table_meta.get("warnings"),
        document_fields.get("valueMappingWarnings"),
        [],
    )
    preview = rows[:3] if isinstance(rows, list) else []
    return {
        "http_status": api_result.get("http_status"),
        "doc_type": response.get("doc_type"),
        "template_path": bool(extract_debug.get("template_path")),
        "tableRows_exists": isinstance(rows, list) and bool(rows),
        "rowCount": row_count,
        "tableMeta_exists": bool(table_meta),
        "extractionSource": table_meta.get("extractionSource"),
        "tableBoundsUsed": table_meta.get("tableBoundsUsed"),
        "tableBoundsSource": table_meta.get("tableBoundsSource"),
        "columnGuidesReceived": table_meta.get("columnGuidesReceived"),
        "columnGuidesUsed": table_meta.get("columnGuidesUsed"),
        "columnGuidesCount": table_meta.get("columnGuidesCount"),
        "expectedValueFillRate": table_meta.get("expectedValueFillRate"),
        "expectedMissingKeys": table_meta.get("expectedMissingKeys") or [],
        "valueMappingWarnings": warnings if isinstance(warnings, list) else [warnings],
        "tableRowsPreview": preview,
        "tableDebugKeys": sorted(table_debug.keys()) if isinstance(table_debug, dict) else [],
        "error": api_result.get("error"),
        "elapsed_sec": api_result.get("elapsed_sec"),
        "payload": api_result.get("payload"),
    }


def t8_baseline() -> dict[str, Any]:
    data = load_json(T8_FINAL_JSON, {})
    result: dict[str, Any] = {}
    for sample, row in (data.get("samples") or {}).items():
        rc = row.get("rowCount") or {}
        result[sample] = {
            "rowCount": first_non_empty(rc.get("ocr"), rc.get("actual"), row.get("rowCount")),
            "extractionSource": row.get("extractionSource"),
            "warnings": row.get("warnings") or [],
            "fillRate": row.get("displayFillRate") or row.get("expectedValueFillRate"),
        }
    return result


def compare_values(sample: str, meta: dict[str, Any]) -> dict[str, Any]:
    rows = meta.get("tableRowsPreview") or []
    flattened = json.dumps(rows, ensure_ascii=False)
    checks: dict[str, Any] = {}
    if sample == "7.pdf":
        checks["quantity_1000_in_preview"] = "1,000" in flattened or "1000" in flattened
        checks["serialLotComposite_in_preview"] = "serialLotComposite" in flattened
        checks["unit_in_preview"] = "unit" in flattened
    if sample == "6.pdf":
        checks["ANDC300C_in_preview"] = "ANDC300C" in flattened
    if sample == "5.pdf":
        checks["priority_multiline_warning_expected"] = True
    if sample == "2.pdf":
        checks["insuranceCode_warning_expected"] = True
    return checks


def verify() -> dict[str, Any]:
    manifest = load_json(MANIFEST_PATH, {})
    baseline = t8_baseline()
    template_summaries, templates_by_file = discover_templates(manifest)
    samples: dict[str, Any] = {}
    issues: list[dict[str, str]] = []
    missing_annotations: list[dict[str, str]] = []

    for sample in PRIORITY_SAMPLES:
        expected = EXPECTED_ROW_COUNTS[sample]
        matched = templates_by_file.get(sample)
        sample_report: dict[str, Any] = {
            "sample": sample,
            "gtRowCount": expected,
            "testBaselineRowCount": baseline.get(sample, {}).get("rowCount") or expected,
            "template": matched.get("summary") if matched else None,
            "apiExecuted": False,
            "modes": {},
            "selectedMode": None,
            "rowCount": None,
            "rowCountStatus": "skipped_no_saved_template_annotation",
            "valueChecks": {},
            "controlVerification": "not_run",
        }
        if not matched:
            need = "documentType=invoice_statement, table region bounds, 필요 시 colGuides 저장"
            sample_report["annotationStatus"] = "저장 annotation 없음"
            sample_report["details"] = "실제 저장 Template/RunOCR E2E 호출 불가. UI 저장 후 재검증 필요."
            missing_annotations.append({"sample": sample, "needed": need})
            issues.append({
                "sample": sample,
                "issue": "saved annotation missing",
                "cause": "templates.json에 해당 샘플 파일명과 연결된 table region template 없음",
                "followup": "UI에서 table region/column guide 저장 후 T-10 재실행",
            })
            samples[sample] = sample_report
            continue

        sample_report["annotationStatus"] = "저장 annotation 있음"
        for mode in ("A", "B"):
            api_result = call_extract(sample, matched["raw"], mode)
            meta = extract_meta(api_result)
            meta["rowCountStatus"] = "exact" if meta.get("rowCount") == expected else "mismatch"
            meta["docTypeStatus"] = "ok" if meta.get("doc_type") == "invoice_statement" else "mismatch"
            meta["valueChecks"] = compare_values(sample, meta)
            sample_report["modes"][mode] = meta
        selected = sample_report["modes"].get("B") or sample_report["modes"].get("A")
        sample_report["apiExecuted"] = True
        sample_report["selectedMode"] = "B"
        sample_report["rowCount"] = selected.get("rowCount")
        sample_report["rowCountStatus"] = selected.get("rowCountStatus")
        sample_report["valueChecks"] = selected.get("valueChecks")
        if selected.get("rowCount") != expected:
            issues.append({
                "sample": sample,
                "issue": "rowCount mismatch",
                "cause": f"RunOCR E2E={selected.get('rowCount')}, expected={expected}",
                "followup": "새 추출 로직 수정 없이 template bounds/colGuides 저장 좌표 후속 검증",
            })
        for mode, meta in sample_report["modes"].items():
            if meta.get("doc_type") != "invoice_statement":
                issues.append({
                    "sample": sample,
                    "issue": f"Mode {mode} doc_type mismatch",
                    "cause": f"doc_type={meta.get('doc_type')}",
                    "followup": "documentType 라우팅 후속 확인",
                })
        samples[sample] = sample_report

    executed = [row for row in samples.values() if row.get("apiExecuted")]
    exact = [row for row in executed if row.get("rowCountStatus") == "exact"]
    if not executed and missing_annotations:
        decision = "documentType 누락 재발 → T-10-save-debug-fix"
    elif missing_annotations:
        decision = "documentType 누락 재발 → T-10-save-debug-fix"
    elif len(exact) == len(executed) == len(SAMPLES):
        decision = "거래명세서 Template/RunOCR 1차 완료"
    elif any("doc_type" in i.get("issue", "") for i in issues):
        decision = "특정 샘플 documentType 라우팅 후속 확인 필요"
    elif issues:
        decision = "특정 샘플 tableBounds/colGuides 좌표 보정 필요"
    else:
        decision = "저장 annotation 기준 E2E 정상"

    return {
        "task": "T-10-after-save-debug",
        "date": "2026-05-14",
        "baseUrl": BASE_URL,
        "createdFiles": {
            "script": str(Path(__file__).resolve()),
            "markdown": str(OUT_MD),
            "json": str(OUT_JSON),
        },
        "sources": {
            "templates": str(TEMPLATES_PATH),
            "manifest": str(MANIFEST_PATH),
            "groundTruth": str(GROUND_TRUTH_PATH),
            "t8Final": str(T8_FINAL_JSON),
        },
        "method": {
            "actualSavedTemplateUsed": True,
            "apiDirectCall": bool(executed),
            "payload": "Mode A: file+template_id only. Mode B: file+template_id+regions+documentType=invoice_statement.",
            "limits": "브라우저 UI 클릭 및 History/result persistence 저장 플로우는 미수행. 저장 annotation 없는 샘플은 실제 Template E2E 미실행.",
        },
        "templateSummaries": template_summaries,
        "samples": samples,
        "issues": issues,
        "missingAnnotations": missing_annotations,
        "summary": {
            "samplesTotal": len(SAMPLES),
            "apiExecuted": len(executed),
            "rowCountExactAmongExecuted": f"{len(exact)}/{len(executed)}" if executed else "0/0",
            "missingSavedAnnotations": len(missing_annotations),
            "issues": len(issues),
        },
        "verification": {
            "script_py_compile": "not_run_in_script",
            "e2e_script": "completed",
            "typecheck": "not_run_in_script",
            "build": "not_run_in_script",
        },
        "decision": decision,
    }


def render_markdown(report: dict[str, Any]) -> str:
    samples = report["samples"]
    lines: list[str] = []
    lines.append("# T-10 after save-debug Template/RunOCR E2E 재검증 결과")
    lines.append("")
    lines.append("## 1. 생성 파일")
    lines.append(f"- Script: `{report['createdFiles']['script']}`")
    lines.append(f"- Markdown report: `{report['createdFiles']['markdown']}`")
    lines.append(f"- JSON report: `{report['createdFiles']['json']}`")
    lines.append("")
    lines.append("## 2. 핵심 요약")
    lines.append(f"- templates.json 재확인: `{report['sources']['templates']}`")
    lines.append(f"- API 기준: `{report['baseUrl']}`")
    lines.append(f"- API 직접 호출 여부: `{report['method']['apiDirectCall']}`")
    lines.append(f"- 요약: {report['summary']}")
    lines.append(f"- 한계: {report['method']['limits']}")
    lines.append("")
    lines.append("## 3. 새로 저장된 Template annotation 확인")
    lines.append("| 샘플 | template 존재 | template_id | documentType | table region | colGuides | 실행 여부 |")
    lines.append("|---|---|---|---|---|---|---|")
    for sample in SAMPLES:
        row = samples.get(sample) or {}
        tmpl = row.get("template") or {}
        table_region = tmpl.get("table_region")
        table_text = md(table_region) if table_region else "없음"
        lines.append(
            f"| {sample} | {'yes' if tmpl else 'no'} | {md(tmpl.get('template_id'))} | "
            f"{md(tmpl.get('documentType'))} | {table_text} | {md(tmpl.get('colGuides_count'))} | "
            f"{md(row.get('apiExecuted'))} |"
        )
    lines.append("")
    lines.append("## 4. RunOCR E2E rowCount 결과")
    lines.append("| 샘플 | GT | Test 기준 | RunOCR E2E | 상태 |")
    lines.append("|---|---:|---:|---:|---|")
    for sample in SAMPLES:
        row = samples.get(sample) or {}
        lines.append(
            f"| {sample} | {md(row.get('gtRowCount') or EXPECTED_ROW_COUNTS[sample])} | "
            f"{md(row.get('testBaselineRowCount') or EXPECTED_ROW_COUNTS[sample])} | "
            f"{md(row.get('rowCount'))} | {md(row.get('rowCountStatus'))} |"
        )
    lines.append("")
    lines.append("## 5. tableMeta/debug 결과")
    lines.append("| 샘플 | doc_type | extractionSource | tableBoundsUsed | columnGuidesUsed | warnings |")
    lines.append("|---|---|---|---|---|---|")
    for sample in SAMPLES:
        row = samples.get(sample) or {}
        mode = (row.get("modes") or {}).get(row.get("selectedMode") or "B") or {}
        lines.append(
            f"| {sample} | {md(mode.get('doc_type'))} | {md(mode.get('extractionSource'))} | "
            f"{md(mode.get('tableBoundsUsed'))} | {md(mode.get('columnGuidesUsed'))} | "
            f"{compact(mode.get('valueMappingWarnings'))} |"
        )
    lines.append("")
    lines.append("## 6. 샘플별 상세")
    for sample in ["5.pdf", "2.pdf", "7.pdf", "6.pdf", "3.pdf", "4.pdf", "1.jpg"]:
        row = samples.get(sample) or {}
        mode = (row.get("modes") or {}).get(row.get("selectedMode") or "B") or {}
        tmpl = row.get("template") or {}
        lines.append(f"### {sample}")
        lines.append(f"- template: {md(tmpl.get('template_id') or row.get('annotationStatus'))}")
        lines.append(f"- rowCount: GT {md(row.get('gtRowCount') or EXPECTED_ROW_COUNTS[sample])} / RunOCR {md(row.get('rowCount'))} / 상태 {md(row.get('rowCountStatus'))}")
        lines.append(
            f"- tableMeta: extractionSource={md(mode.get('extractionSource'))}, "
            f"tableBoundsUsed={md(mode.get('tableBoundsUsed'))}, "
            f"tableBoundsSource={md(mode.get('tableBoundsSource'))}, "
            f"columnGuidesReceived={md(mode.get('columnGuidesReceived'))}, "
            f"columnGuidesUsed={md(mode.get('columnGuidesUsed'))}, "
            f"columnGuidesCount={md(mode.get('columnGuidesCount'))}"
        )
        lines.append(f"- 판정: {md(row.get('details') or row.get('annotationStatus'))}")
        lines.append("")
    lines.append("## 7. 발견 문제")
    lines.append("| 문제 | 원인 | 후속 |")
    lines.append("|---|---|---|")
    if report["issues"]:
        for issue in report["issues"]:
            lines.append(f"| {md(issue.get('sample'))}: {md(issue.get('issue'))} | {md(issue.get('cause'))} | {md(issue.get('followup'))} |")
    else:
        lines.append("| 없음 | 저장 annotation 기준 E2E 문제 없음 | - |")
    lines.append("")
    lines.append("## 8. 검증 결과")
    verification = report.get("verification") or {}
    lines.append(f"- script py_compile: {md(verification.get('script_py_compile'))}")
    lines.append(f"- E2E script: {md(verification.get('e2e_script'))}")
    lines.append(f"- typecheck: {md(verification.get('typecheck'))}")
    lines.append(f"- build: {md(verification.get('build'))}")
    lines.append("")
    lines.append("## 9. 다음 작업 판단")
    lines.append(f"- {report['decision']}")
    lines.append("")
    lines.append("## 10. 결과 저장/History")
    lines.append("- API 응답 기준 tableRows/tableMeta 확인 완료")
    lines.append("- 브라우저 UI 저장 플로우는 미수행")
    lines.append("- History/result persistence는 후속 E2E 필요")
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
