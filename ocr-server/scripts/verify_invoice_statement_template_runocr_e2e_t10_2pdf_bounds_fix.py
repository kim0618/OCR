"""
T-10 2.pdf bounds-fix verification.

Reporting-only script. It reads saved template annotations, calls /ocr/extract
against the running backend, and writes Markdown/JSON reports. It does not edit
templates.json, extractor code, UI code, manifest, or ground truth.
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

OUT_JSON = REPORT_DIR / "T10_2pdf_bounds_fix_runocr_e2e_20260515.json"
OUT_MD = REPORT_DIR / "T10_2pdf_bounds_fix_runocr_e2e_20260515.md"

SAMPLES = ["2.pdf", "1.jpg", "5.pdf"]
EXPECTED_ROW_COUNTS = {"1.jpg": 28, "2.pdf": 13, "5.pdf": 6}
SAMPLE_MIMES = {
    "1.jpg": "image/jpeg",
    "2.pdf": "application/pdf",
    "5.pdf": "application/pdf",
}
SUMMARY_KEYWORDS = [
    "합계",
    "계약코드",
    "공급금액합계",
    "소비자금액합계",
    "전일잔액",
    "당일거래금액",
    "누계잔액",
]


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def md(value: Any) -> str:
    if value is None or value == "":
        return "-"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (dict, list)):
        text = json.dumps(value, ensure_ascii=False)
    else:
        text = str(value)
    return text.replace("\n", "<br>").replace("|", "\\|")


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


def table_regions(regions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [r for r in regions if r.get("fieldType") == "table" or r.get("type") == "table"]


def expected_columns_for(sample: str, manifest: dict[str, Any]) -> dict[str, Any] | None:
    for item in manifest.get("items", []):
        if item.get("filename") == sample:
            return (item.get("invoiceProfile") or {}).get("tableExpectedColumns") or None
    return None


def template_filename(template_json: dict[str, Any]) -> str | None:
    file_info = template_json.get("file") or {}
    if isinstance(file_info, dict):
        return file_info.get("name") or file_info.get("filename")
    return template_json.get("filename") or template_json.get("fileName")


def summarize_template(template: dict[str, Any]) -> dict[str, Any]:
    tj = template.get("template_json") or {}
    regions = tj.get("regions") or []
    tables = table_regions(regions)
    table = tables[0] if tables else {}
    table_meta = table.get("table") or {}
    col_guides = table_meta.get("colGuides") or table_meta.get("colX") or table.get("colGuides") or []
    bounds = None
    if table:
        bounds = {
            "x": table.get("x"),
            "y": table.get("y"),
            "width": table.get("width"),
            "height": table.get("height"),
        }
    y_range = None
    if bounds and isinstance(bounds.get("y"), (int, float)) and isinstance(bounds.get("height"), (int, float)):
        y_range = [bounds["y"], bounds["y"] + bounds["height"]]
    return {
        "template_id": template.get("template_id"),
        "template_name": template.get("template_name"),
        "filename": template_filename(tj),
        "documentType": tj.get("documentType"),
        "regions_count": len(regions),
        "table_region_count": len(tables),
        "table_region": bounds,
        "tableBoundsYRange": y_range,
        "colGuides_count": len(col_guides) if isinstance(col_guides, list) else 0,
        "colGuides": col_guides if isinstance(col_guides, list) else [],
    }


def discover_templates() -> dict[str, dict[str, Any]]:
    rows = load_json(TEMPLATES_PATH, [])
    by_file: dict[str, dict[str, Any]] = {}
    for row in rows:
        summary = summarize_template(row)
        filename = summary.get("filename")
        if filename in EXPECTED_ROW_COUNTS and summary.get("table_region_count"):
            by_file[str(filename)] = {"raw": row, "summary": summary}
    return by_file


def multipart_post(sample: str, data: dict[str, str]) -> dict[str, Any]:
    sample_path = TESTSET_DIR / sample
    file_bytes = sample_path.read_bytes()
    boundary = f"----codex-t10-2pdf-{uuid.uuid4().hex}"
    chunks: list[bytes] = []
    for key, value in data.items():
        chunks.append(f"--{boundary}\r\n".encode("utf-8"))
        chunks.append(f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode("utf-8"))
        chunks.append(value.encode("utf-8"))
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
    request = urllib.request.Request(
        f"{BASE_URL}/ocr/extract",
        data=b"".join(chunks),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    started = time.time()
    try:
        with urllib.request.urlopen(request, timeout=420) as response:
            status = response.status
            text = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        status = exc.code
        text = exc.read().decode("utf-8", errors="replace")
    except Exception as exc:
        return {"http_status": None, "elapsed_sec": round(time.time() - started, 1), "error": str(exc)}
    result: dict[str, Any] = {"http_status": status, "elapsed_sec": round(time.time() - started, 1)}
    try:
        result["response"] = json.loads(text)
    except Exception:
        result["error"] = text[:1000]
    return result


def call_runocr(sample: str, template: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    tj = template.get("template_json") or {}
    regions = tj.get("regions") or []
    payload = {
        "template_id": str(template.get("template_id") or ""),
        "regions": json.dumps(regions, ensure_ascii=False),
        "model_id": "",
        "documentType": "invoice_statement",
    }
    expected = expected_columns_for(sample, manifest)
    if expected:
        payload["tableExpectedColumns"] = json.dumps(expected, ensure_ascii=False)
    result = multipart_post(sample, payload)
    result["payload"] = {
        "template_id": payload["template_id"],
        "regions": True,
        "documentType": payload["documentType"],
        "tableExpectedColumns": bool(expected),
    }
    return result


def extract_result(sample: str, api_result: dict[str, Any]) -> dict[str, Any]:
    response = api_result.get("response") or {}
    fields = response.get("document_fields") or {}
    table_meta = fields.get("tableMeta") or {}
    table_debug = fields.get("tableDebug") or {}
    extract_debug = response.get("extract_debug") or {}
    invoice_debug = extract_debug.get("invoice_statement") or {}
    if not table_debug and isinstance(invoice_debug, dict):
        table_debug = invoice_debug.get("tableDebug") or invoice_debug.get("debug") or {}
    rows = fields.get("tableRows") or []
    row_count = to_int(fields.get("rowCount"))
    if row_count is None and isinstance(rows, list):
        row_count = len(rows)
    row_text = json.dumps(rows, ensure_ascii=False)
    summary_hits = [kw for kw in SUMMARY_KEYWORDS if kw in row_text]
    warnings = table_meta.get("valueMappingWarnings") or table_meta.get("warnings") or []
    if isinstance(warnings, str):
        warnings = [warnings]
    return {
        "sample": sample,
        "http_status": api_result.get("http_status"),
        "elapsed_sec": api_result.get("elapsed_sec"),
        "doc_type": response.get("doc_type"),
        "template_path": bool(extract_debug.get("template_path")),
        "tableRows_exists": isinstance(rows, list) and bool(rows),
        "rowCount": row_count,
        "expectedRowCount": EXPECTED_ROW_COUNTS[sample],
        "status": "exact" if row_count == EXPECTED_ROW_COUNTS[sample] else "mismatch",
        "tableMeta_exists": bool(table_meta),
        "extractionSource": table_meta.get("extractionSource"),
        "tableBoundsUsed": table_meta.get("tableBoundsUsed"),
        "tableBoundsSource": table_meta.get("tableBoundsSource"),
        "columnGuidesReceived": table_meta.get("columnGuidesReceived"),
        "columnGuidesUsed": table_meta.get("columnGuidesUsed"),
        "columnGuidesCount": table_meta.get("columnGuidesCount"),
        "expectedValueFillRate": table_meta.get("expectedValueFillRate"),
        "expectedMissingKeys": table_meta.get("expectedMissingKeys") or [],
        "valueMappingWarnings": warnings,
        "firstRows": rows[:3] if isinstance(rows, list) else [],
        "lastRows": rows[-3:] if isinstance(rows, list) else [],
        "summaryRowIncluded": bool(summary_hits),
        "summaryKeywordHits": summary_hits,
        "tableDebugKeys": sorted(table_debug.keys()) if isinstance(table_debug, dict) else [],
        "error": api_result.get("error"),
        "payload": api_result.get("payload"),
    }


def verify() -> dict[str, Any]:
    manifest = load_json(MANIFEST_PATH, {})
    templates = discover_templates()
    samples: dict[str, Any] = {}
    issues: list[dict[str, str]] = []
    for sample in SAMPLES:
        matched = templates.get(sample)
        entry: dict[str, Any] = {
            "sample": sample,
            "expectedRowCount": EXPECTED_ROW_COUNTS[sample],
            "template": matched.get("summary") if matched else None,
            "apiExecuted": False,
            "result": None,
        }
        if not matched:
            entry["status"] = "skipped_no_saved_template_annotation"
            issues.append({
                "sample": sample,
                "issue": "saved annotation missing",
                "cause": "templates.json에 해당 샘플 table template 없음",
                "followup": "UI에서 annotation 저장 후 재검증",
            })
            samples[sample] = entry
            continue
        api = call_runocr(sample, matched["raw"], manifest)
        result = extract_result(sample, api)
        entry["apiExecuted"] = True
        entry["result"] = result
        entry["status"] = result["status"]
        if result["doc_type"] != "invoice_statement":
            issues.append({
                "sample": sample,
                "issue": "doc_type mismatch",
                "cause": f"doc_type={result['doc_type']}",
                "followup": "documentType 저장/payload 확인",
            })
        if result["columnGuidesReceived"] is not True:
            issues.append({
                "sample": sample,
                "issue": "columnGuidesReceived false",
                "cause": f"columnGuidesReceived={result['columnGuidesReceived']}",
                "followup": "colGuides payload 재확인",
            })
        if result["rowCount"] != EXPECTED_ROW_COUNTS[sample]:
            issues.append({
                "sample": sample,
                "issue": "rowCount mismatch",
                "cause": f"RunOCR={result['rowCount']}, expected={EXPECTED_ROW_COUNTS[sample]}",
                "followup": "tableBounds 하단 y 추가 조정",
            })
        if sample == "2.pdf" and result["summaryRowIncluded"]:
            issues.append({
                "sample": sample,
                "issue": "summary row included",
                "cause": ", ".join(result["summaryKeywordHits"]),
                "followup": "하단 summary/잔액 영역 제외 후 재저장",
            })
        samples[sample] = entry

    r2 = (samples.get("2.pdf") or {}).get("result") or {}
    r1 = (samples.get("1.jpg") or {}).get("result") or {}
    r5 = (samples.get("5.pdf") or {}).get("result") or {}
    if r2.get("columnGuidesReceived") is False:
        decision = "columnGuidesReceived=false 재발 → colGuides payload 재확인"
    elif r2.get("rowCount") == 13 and r1.get("rowCount") == 28 and r5.get("rowCount") == 6:
        decision = "2.pdf 13/13 달성 → 7.pdf/6.pdf annotation 저장 및 E2E 확장"
    elif r2.get("rowCount") != 13:
        decision = "2.pdf 여전히 over → tableBounds 하단 y 추가 조정"
    else:
        decision = "extractionSource/rowCount 이상 → 별도 T-10-fix 진행"

    return {
        "task": "T-10-2pdf-bounds-fix",
        "date": "2026-05-15",
        "baseUrl": BASE_URL,
        "createdFiles": {
            "script": str(Path(__file__).resolve()),
            "markdown": str(OUT_MD),
            "json": str(OUT_JSON),
        },
        "samples": samples,
        "issues": issues,
        "summary": {
            "apiExecuted": sum(1 for s in samples.values() if s.get("apiExecuted")),
            "exact": sum(1 for s in samples.values() if s.get("status") == "exact"),
            "total": len(samples),
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
    s2 = samples.get("2.pdf") or {}
    t2 = s2.get("template") or {}
    r2 = s2.get("result") or {}
    lines: list[str] = []
    lines.append("# T-10 2.pdf tableBounds 재조정 RunOCR E2E 결과")
    lines.append("")
    lines.append("## 1. 생성 파일")
    lines.append(f"- Script: `{report['createdFiles']['script']}`")
    lines.append(f"- Markdown report: `{report['createdFiles']['markdown']}`")
    lines.append(f"- JSON report: `{report['createdFiles']['json']}`")
    lines.append("")
    lines.append("## 2. 핵심 요약")
    lines.append(f"- API: `{report['baseUrl']}`")
    lines.append(f"- 2.pdf 상태: {md(s2.get('status'))}")
    lines.append(f"- 회귀 포함 실행: {md(report['summary'])}")
    lines.append(f"- 다음 판단: {report['decision']}")
    lines.append("")
    lines.append("## 3. 2.pdf annotation 확인")
    lines.append("| 항목 | 결과 |")
    lines.append("|---|---|")
    lines.append(f"| template_id | {md(t2.get('template_id'))} |")
    lines.append(f"| documentType | {md(t2.get('documentType'))} |")
    lines.append(f"| table region | {md(t2.get('table_region'))} |")
    lines.append(f"| colGuides count | {md(t2.get('colGuides_count'))} |")
    lines.append(f"| tableBounds y 범위 | {md(t2.get('tableBoundsYRange'))} |")
    lines.append("")
    lines.append("## 4. 2.pdf E2E 결과")
    lines.append("| 항목 | 결과 |")
    lines.append("|---|---|")
    for key in [
        "doc_type",
        "extractionSource",
        "tableBoundsUsed",
        "columnGuidesReceived",
        "columnGuidesUsed",
        "rowCount",
    ]:
        lines.append(f"| {key} | {md(r2.get(key))} |")
    lines.append("| expected rowCount | 13 |")
    lines.append(f"| 상태 | {md(r2.get('status'))} |")
    lines.append("")
    lines.append("## 5. row preview 점검")
    lines.append(f"- 첫 3개 row: {md(r2.get('firstRows'))}")
    lines.append(f"- 마지막 3개 row: {md(r2.get('lastRows'))}")
    lines.append(f"- summary row 포함 여부: {md(r2.get('summaryRowIncluded'))} {md(r2.get('summaryKeywordHits'))}")
    lines.append("")
    lines.append("## 6. 회귀 확인")
    lines.append("| 샘플 | 기대 | 결과 | 상태 |")
    lines.append("|---|---:|---:|---|")
    for sample in ["1.jpg", "5.pdf", "2.pdf"]:
        row = samples.get(sample) or {}
        result = row.get("result") or {}
        lines.append(
            f"| {sample} | {EXPECTED_ROW_COUNTS[sample]} | {md(result.get('rowCount'))} | {md(row.get('status'))} |"
        )
    lines.append("")
    lines.append("## 7. 발견 문제")
    lines.append("| 문제 | 원인 | 후속 |")
    lines.append("|---|---|---|")
    if report["issues"]:
        for issue in report["issues"]:
            lines.append(
                f"| {md(issue.get('sample'))}: {md(issue.get('issue'))} | {md(issue.get('cause'))} | {md(issue.get('followup'))} |"
            )
    else:
        lines.append("| 없음 | - | - |")
    lines.append("")
    lines.append("## 8. 검증 결과")
    v = report["verification"]
    lines.append(f"- script py_compile: {md(v.get('script_py_compile'))}")
    lines.append(f"- E2E script: {md(v.get('e2e_script'))}")
    lines.append(f"- typecheck: {md(v.get('typecheck'))}")
    lines.append(f"- build: {md(v.get('build'))}")
    lines.append("")
    lines.append("## 9. 다음 작업 판단")
    lines.append(f"- {report['decision']}")
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
