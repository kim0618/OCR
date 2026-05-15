"""
T-10 2.pdf bounds-adjust verification.

Reporting-only script. It verifies the saved 2.pdf template annotation and
RunOCR E2E result against the running backend. It does not edit templates.json,
extractor code, frontend source, manifest, or ground truth.
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

OUT_JSON = REPORT_DIR / "T10_2pdf_bounds_adjust_runocr_e2e_20260515.json"
OUT_MD = REPORT_DIR / "T10_2pdf_bounds_adjust_runocr_e2e_20260515.md"

SAMPLES = ["2.pdf", "1.jpg", "5.pdf"]
EXPECTED = {"2.pdf": 13, "1.jpg": 28, "5.pdf": 6}
MIMES = {"2.pdf": "application/pdf", "1.jpg": "image/jpeg", "5.pdf": "application/pdf"}
PREVIOUS_2PDF_BOUNDS = {"x": 111, "y": 136, "width": 1486, "height": 2112, "yMax": 2248}
SUMMARY_KEYWORDS = [
    "합계",
    "계약코드",
    "공급금액합계",
    "소비자금액합계",
    "전일잔액",
    "당일거래금액",
    "누계잔액",
    "구분",
    "채 권",
    "약정",
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
        value = json.dumps(value, ensure_ascii=False)
    return str(value).replace("\n", "<br>").replace("|", "\\|")


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


def filename_of(template_json: dict[str, Any]) -> str | None:
    file_info = template_json.get("file") or {}
    if isinstance(file_info, dict):
        return file_info.get("name") or file_info.get("filename")
    return template_json.get("filename") or template_json.get("fileName")


def bounds_of(region: dict[str, Any]) -> dict[str, Any]:
    y = region.get("y")
    h = region.get("height")
    y_max = y + h if isinstance(y, (int, float)) and isinstance(h, (int, float)) else None
    return {
        "x": region.get("x"),
        "y": y,
        "width": region.get("width"),
        "height": h,
        "yMax": y_max,
    }


def summarize_template(template: dict[str, Any]) -> dict[str, Any]:
    tj = template.get("template_json") or {}
    regions = tj.get("regions") or []
    tables = table_regions(regions)
    table = tables[0] if tables else {}
    table_meta = table.get("table") or {}
    col_guides = table_meta.get("colGuides") or table_meta.get("colX") or table.get("colGuides") or []
    return {
        "template_id": template.get("template_id"),
        "filename": filename_of(tj),
        "documentType": tj.get("documentType"),
        "regions_count": len(regions),
        "table_region_count": len(tables),
        "bounds": bounds_of(table) if table else None,
        "colGuides_count": len(col_guides) if isinstance(col_guides, list) else 0,
        "colGuides": col_guides if isinstance(col_guides, list) else [],
    }


def discover_templates() -> dict[str, dict[str, Any]]:
    rows = load_json(TEMPLATES_PATH, [])
    by_file: dict[str, dict[str, Any]] = {}
    for row in rows:
        summary = summarize_template(row)
        filename = summary.get("filename")
        if filename in EXPECTED and summary.get("table_region_count"):
            by_file[str(filename)] = {"raw": row, "summary": summary}
    return by_file


def expected_columns(sample: str, manifest: dict[str, Any]) -> dict[str, Any] | None:
    for item in manifest.get("items", []):
        if item.get("filename") == sample:
            return (item.get("invoiceProfile") or {}).get("tableExpectedColumns") or None
    return None


def post_extract(sample: str, template: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    tj = template.get("template_json") or {}
    regions = tj.get("regions") or []
    data = {
        "template_id": str(template.get("template_id") or ""),
        "regions": json.dumps(regions, ensure_ascii=False),
        "model_id": "",
        "documentType": "invoice_statement",
    }
    cols = expected_columns(sample, manifest)
    if cols:
        data["tableExpectedColumns"] = json.dumps(cols, ensure_ascii=False)

    boundary = f"----codex-t10-adjust-{uuid.uuid4().hex}"
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
            f"Content-Type: {MIMES[sample]}\r\n\r\n"
        ).encode("utf-8")
    )
    chunks.append((TESTSET_DIR / sample).read_bytes())
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


def parse_result(sample: str, api: dict[str, Any]) -> dict[str, Any]:
    response = api.get("response") or {}
    fields = response.get("document_fields") or {}
    meta = fields.get("tableMeta") or {}
    rows = fields.get("tableRows") or []
    row_count = to_int(fields.get("rowCount"))
    if row_count is None and isinstance(rows, list):
        row_count = len(rows)
    text = json.dumps(rows, ensure_ascii=False)
    hits = [kw for kw in SUMMARY_KEYWORDS if kw in text]
    warnings = meta.get("valueMappingWarnings") or meta.get("warnings") or []
    if isinstance(warnings, str):
        warnings = [warnings]
    return {
        "http_status": api.get("http_status"),
        "doc_type": response.get("doc_type"),
        "rowCount": row_count,
        "expectedRowCount": EXPECTED[sample],
        "status": "exact" if row_count == EXPECTED[sample] else ("short" if row_count and row_count < EXPECTED[sample] else "over"),
        "tableRows_exists": isinstance(rows, list) and bool(rows),
        "tableMeta_exists": bool(meta),
        "extractionSource": meta.get("extractionSource"),
        "tableBoundsUsed": meta.get("tableBoundsUsed"),
        "tableBoundsSource": meta.get("tableBoundsSource"),
        "columnGuidesReceived": meta.get("columnGuidesReceived"),
        "columnGuidesUsed": meta.get("columnGuidesUsed"),
        "columnGuidesCount": meta.get("columnGuidesCount"),
        "expectedValueFillRate": meta.get("expectedValueFillRate"),
        "expectedMissingKeys": meta.get("expectedMissingKeys") or [],
        "valueMappingWarnings": warnings,
        "firstRows": rows[:3] if isinstance(rows, list) else [],
        "lastRows": rows[-3:] if isinstance(rows, list) else [],
        "summaryRowsIncluded": bool(hits),
        "summaryKeywordHits": hits,
        "elapsed_sec": api.get("elapsed_sec"),
        "error": api.get("error"),
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
            "expected": EXPECTED[sample],
            "template": matched.get("summary") if matched else None,
            "apiExecuted": False,
            "result": None,
            "status": "skipped",
        }
        if not matched:
            issues.append({"problem": f"{sample} annotation missing", "cause": "template 없음", "followup": "UI 저장 후 재검증"})
            samples[sample] = entry
            continue
        api = post_extract(sample, matched["raw"], manifest)
        result = parse_result(sample, api)
        entry.update({"apiExecuted": True, "result": result, "status": result["status"]})
        if result["doc_type"] != "invoice_statement":
            issues.append({"problem": f"{sample} documentType mismatch", "cause": str(result["doc_type"]), "followup": "documentType payload 확인"})
        if result["columnGuidesReceived"] is not True:
            issues.append({"problem": f"{sample} columnGuidesReceived false", "cause": str(result["columnGuidesReceived"]), "followup": "colGuides payload 재확인"})
        if result["rowCount"] != EXPECTED[sample]:
            issues.append({"problem": f"{sample} rowCount {result['status']}", "cause": f"{result['rowCount']}/{EXPECTED[sample]}", "followup": "tableBounds 하단 y 재조정"})
        if sample == "2.pdf" and result["summaryRowsIncluded"]:
            issues.append({"problem": "2.pdf summary/잔액 row 포함", "cause": ", ".join(result["summaryKeywordHits"]), "followup": "구분/채권/약정 영역 제외 후 재저장"})
        samples[sample] = entry

    r2 = (samples.get("2.pdf") or {}).get("result") or {}
    r1 = (samples.get("1.jpg") or {}).get("result") or {}
    r5 = (samples.get("5.pdf") or {}).get("result") or {}
    if r2.get("columnGuidesReceived") is False:
        decision = "columnGuidesReceived=false 재발 → colGuides payload 재확인"
    elif r2.get("status") == "exact" and r1.get("status") == "exact" and r5.get("status") == "exact":
        decision = "2.pdf 13/13 달성 → 7.pdf/6.pdf/3.pdf/4.pdf annotation 저장 및 E2E 확장"
    elif r2.get("status") == "short":
        decision = "2.pdf short → tableBounds 하단을 너무 올렸으므로 약간 확장"
    else:
        decision = "2.pdf 여전히 over → tableBounds 하단 y 추가 조정"

    current = ((samples.get("2.pdf") or {}).get("template") or {}).get("bounds") or {}
    return {
        "task": "T-10-2pdf-bounds-adjust",
        "date": "2026-05-15",
        "baseUrl": BASE_URL,
        "createdFiles": {"script": str(Path(__file__).resolve()), "markdown": str(OUT_MD), "json": str(OUT_JSON)},
        "previous2pdfBounds": PREVIOUS_2PDF_BOUNDS,
        "current2pdfBounds": current,
        "boundsChanged": current != PREVIOUS_2PDF_BOUNDS,
        "samples": samples,
        "issues": issues,
        "verification": {"script_py_compile": "not_run_in_script", "e2e_script": "completed", "typecheck": "not_run_in_script", "build": "not_run_in_script"},
        "decision": decision,
    }


def render_markdown(report: dict[str, Any]) -> str:
    samples = report["samples"]
    s2 = samples.get("2.pdf") or {}
    r2 = s2.get("result") or {}
    prev = report["previous2pdfBounds"]
    cur = report["current2pdfBounds"]
    lines = [
        "# T-10 2.pdf tableBounds 하단 좌표 재조정 E2E 결과",
        "",
        "## 1. 생성 파일",
        f"- Script: `{report['createdFiles']['script']}`",
        f"- Markdown report: `{report['createdFiles']['markdown']}`",
        f"- JSON report: `{report['createdFiles']['json']}`",
        "",
        "## 2. 핵심 요약",
        f"- bounds 변경 여부: `{report['boundsChanged']}`",
        f"- 2.pdf 상태: {md(r2.get('status'))}",
        f"- 다음 판단: {report['decision']}",
        "",
        "## 3. 2.pdf annotation 변경 확인",
        "| 항목 | 이전 | 이후 |",
        "|---|---|---|",
    ]
    for key in ["x", "y", "width", "height", "yMax"]:
        lines.append(f"| {key} | {md(prev.get(key))} | {md(cur.get(key))} |")
    lines.append(f"| colGuides count | - | {md((s2.get('template') or {}).get('colGuides_count'))} |")
    lines.extend([
        "",
        "## 4. 2.pdf E2E 결과",
        "| 항목 | 결과 |",
        "|---|---|",
    ])
    for key in ["doc_type", "extractionSource", "tableBoundsUsed", "columnGuidesReceived", "columnGuidesUsed", "rowCount"]:
        lines.append(f"| {key} | {md(r2.get(key))} |")
    lines.append("| expected rowCount | 13 |")
    lines.append(f"| 상태 | {md(r2.get('status'))} |")
    lines.extend([
        "",
        "## 5. row preview 점검",
        f"- 첫 3개 row: {md(r2.get('firstRows'))}",
        f"- 마지막 3개 row: {md(r2.get('lastRows'))}",
        f"- summary/잔액 row 포함 여부: {md(r2.get('summaryRowsIncluded'))} {md(r2.get('summaryKeywordHits'))}",
        "",
        "## 6. 회귀 확인",
        "| 샘플 | 기대 | 결과 | 상태 |",
        "|---|---:|---:|---|",
    ])
    for sample in ["1.jpg", "5.pdf", "2.pdf"]:
        result = (samples.get(sample) or {}).get("result") or {}
        lines.append(f"| {sample} | {EXPECTED[sample]} | {md(result.get('rowCount'))} | {md(result.get('status'))} |")
    lines.extend(["", "## 7. 발견 문제", "| 문제 | 원인 | 후속 |", "|---|---|---|"])
    if report["issues"]:
        for issue in report["issues"]:
            lines.append(f"| {md(issue.get('problem'))} | {md(issue.get('cause'))} | {md(issue.get('followup'))} |")
    else:
        lines.append("| 없음 | - | - |")
    v = report["verification"]
    lines.extend([
        "",
        "## 8. 검증 결과",
        f"- script py_compile: {md(v.get('script_py_compile'))}",
        f"- E2E script: {md(v.get('e2e_script'))}",
        f"- typecheck: {md(v.get('typecheck'))}",
        f"- build: {md(v.get('build'))}",
        "",
        "## 9. 다음 작업 판단",
        f"- {report['decision']}",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    report = verify()
    write_json(OUT_JSON, report)
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps({"boundsChanged": report["boundsChanged"], "decision": report["decision"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
