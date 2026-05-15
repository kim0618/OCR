"""
T-10 all remaining invoice_statement Template/RunOCR E2E verification.

Reporting-only script. It verifies saved template annotations for all seven
invoice_statement samples and calls /ocr/extract only for samples with a saved
table template. It does not edit templates, frontend source, extractor logic,
manifest, or ground truth.
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

OUT_JSON = REPORT_DIR / "T10_all_remaining_template_runocr_e2e_invoice_statement_20260515.json"
OUT_MD = REPORT_DIR / "T10_all_remaining_template_runocr_e2e_invoice_statement_20260515.md"

SAMPLES = ["1.jpg", "2.pdf", "3.pdf", "4.pdf", "5.pdf", "6.pdf", "7.pdf"]
EXPECTED = {"1.jpg": 28, "2.pdf": 13, "3.pdf": 1, "4.pdf": 1, "5.pdf": 6, "6.pdf": 6, "7.pdf": 1}
MIMES = {
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


def summarize_template(template: dict[str, Any]) -> dict[str, Any]:
    tj = template.get("template_json") or {}
    regions = tj.get("regions") or []
    tables = table_regions(regions)
    table = tables[0] if tables else {}
    table_meta = table.get("table") or {}
    col_guides = table_meta.get("colGuides") or table_meta.get("colX") or table.get("colGuides") or []
    bounds = None
    if table:
        bounds = {k: table.get(k) for k in ["x", "y", "width", "height"]}
        if isinstance(bounds.get("y"), (int, float)) and isinstance(bounds.get("height"), (int, float)):
            bounds["yMax"] = bounds["y"] + bounds["height"]
    return {
        "template_id": template.get("template_id"),
        "filename": filename_of(tj),
        "documentType": tj.get("documentType"),
        "table_region_count": len(tables),
        "table_region": bounds,
        "colGuides_count": len(col_guides) if isinstance(col_guides, list) else 0,
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
    data = {
        "template_id": str(template.get("template_id") or ""),
        "regions": json.dumps(tj.get("regions") or [], ensure_ascii=False),
        "model_id": "",
        "documentType": "invoice_statement",
    }
    cols = expected_columns(sample, manifest)
    if cols:
        data["tableExpectedColumns"] = json.dumps(cols, ensure_ascii=False)
    boundary = f"----codex-t10-all-{uuid.uuid4().hex}"
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
    warnings = meta.get("valueMappingWarnings") or meta.get("warnings") or []
    if isinstance(warnings, str):
        warnings = [warnings]
    return {
        "http_status": api.get("http_status"),
        "doc_type": response.get("doc_type"),
        "extractionSource": meta.get("extractionSource"),
        "tableBoundsUsed": meta.get("tableBoundsUsed"),
        "columnGuidesReceived": meta.get("columnGuidesReceived"),
        "columnGuidesUsed": meta.get("columnGuidesUsed"),
        "rowCount": row_count,
        "expectedRowCount": EXPECTED[sample],
        "status": "exact" if row_count == EXPECTED[sample] else ("short" if row_count and row_count < EXPECTED[sample] else "over"),
        "expectedValueFillRate": meta.get("expectedValueFillRate"),
        "expectedMissingKeys": meta.get("expectedMissingKeys") or [],
        "valueMappingWarnings": warnings,
        "rowPreview": rows[:3] if isinstance(rows, list) else [],
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
            "status": "skipped_no_saved_template_annotation",
        }
        if not matched:
            issues.append({
                "sample": sample,
                "problem": "annotation 없음",
                "cause": "templates.json에 저장된 table template 없음",
                "followup": "UI에서 invoice_statement table region/colGuides 저장",
            })
            samples[sample] = entry
            continue
        api = post_extract(sample, matched["raw"], manifest)
        result = parse_result(sample, api)
        entry.update({"apiExecuted": True, "result": result, "status": result["status"]})
        if result["doc_type"] != "invoice_statement":
            issues.append({"sample": sample, "problem": "doc_type mismatch", "cause": str(result["doc_type"]), "followup": "documentType 저장/payload 확인"})
        if result["rowCount"] != EXPECTED[sample]:
            issues.append({"sample": sample, "problem": f"rowCount {result['status']}", "cause": f"{result['rowCount']}/{EXPECTED[sample]}", "followup": "해당 샘플 tableBounds 조정"})
        samples[sample] = entry

    executed = [s for s in samples.values() if s.get("apiExecuted")]
    exact = [s for s in executed if s.get("status") == "exact"]
    missing = [s for s in samples.values() if not s.get("apiExecuted")]
    if len(exact) == len(SAMPLES):
        decision = "7/7 E2E exact → 거래명세서 Template/RunOCR 1차 완료"
    elif missing:
        decision = "annotation 없음 → UI 저장 필요"
    elif len(exact) < len(executed):
        decision = "일부 over/short → 해당 샘플 tableBounds 조정"
    else:
        decision = "History/result persistence 검증 필요"
    return {
        "task": "T-10-all-remaining",
        "date": "2026-05-15",
        "baseUrl": BASE_URL,
        "createdFiles": {"script": str(Path(__file__).resolve()), "markdown": str(OUT_MD), "json": str(OUT_JSON)},
        "samples": samples,
        "issues": issues,
        "summary": {"executed": len(executed), "exact": len(exact), "missing": len(missing), "total": len(SAMPLES)},
        "verification": {"script_py_compile": "not_run_in_script", "e2e_script": "completed", "typecheck": "not_run_in_script", "build": "not_run_in_script"},
        "decision": decision,
    }


def render_markdown(report: dict[str, Any]) -> str:
    samples = report["samples"]
    lines = [
        "# T-10 all remaining Template/RunOCR E2E 결과",
        "",
        "## 1. 생성 파일",
        f"- Script: `{report['createdFiles']['script']}`",
        f"- Markdown report: `{report['createdFiles']['markdown']}`",
        f"- JSON report: `{report['createdFiles']['json']}`",
        "",
        "## 2. 핵심 요약",
        f"- API: `{report['baseUrl']}`",
        f"- 요약: {md(report['summary'])}",
        f"- 다음 판단: {report['decision']}",
        "",
        "## 3. Template annotation 확인",
        "| 샘플 | template_id | documentType | table region | colGuides | 실행 여부 |",
        "|---|---|---|---|---|---|",
    ]
    for sample in SAMPLES:
        row = samples[sample]
        tmpl = row.get("template") or {}
        lines.append(
            f"| {sample} | {md(tmpl.get('template_id'))} | {md(tmpl.get('documentType'))} | "
            f"{md(tmpl.get('table_region'))} | {md(tmpl.get('colGuides_count'))} | {md(row.get('apiExecuted'))} |"
        )
    lines.extend(["", "## 4. E2E rowCount 결과", "| 샘플 | GT | Test 기준 | RunOCR E2E | 상태 |", "|---|---:|---:|---:|---|"])
    for sample in SAMPLES:
        row = samples[sample]
        result = row.get("result") or {}
        lines.append(f"| {sample} | {EXPECTED[sample]} | {EXPECTED[sample]} | {md(result.get('rowCount'))} | {md(row.get('status'))} |")
    lines.extend(["", "## 5. tableMeta/debug 결과", "| 샘플 | doc_type | extractionSource | tableBoundsUsed | columnGuidesUsed | warnings |", "|---|---|---|---|---|---|"])
    for sample in SAMPLES:
        result = (samples[sample].get("result") or {})
        warnings = result.get("valueMappingWarnings") or []
        lines.append(
            f"| {sample} | {md(result.get('doc_type'))} | {md(result.get('extractionSource'))} | "
            f"{md(result.get('tableBoundsUsed'))} | {md(result.get('columnGuidesUsed'))} | {md(warnings[:4] if isinstance(warnings, list) else warnings)} |"
        )
    lines.append("")
    lines.append("## 6. 샘플별 상세")
    for sample in SAMPLES:
        row = samples[sample]
        result = row.get("result") or {}
        lines.append(f"### {sample}")
        lines.append(f"- template: {md((row.get('template') or {}).get('template_id'))}")
        lines.append(f"- rowCount: {md(result.get('rowCount'))}/{EXPECTED[sample]} ({md(row.get('status'))})")
        lines.append(f"- tableMeta: source={md(result.get('extractionSource'))}, bounds={md(result.get('tableBoundsUsed'))}, colGuidesReceived={md(result.get('columnGuidesReceived'))}, colGuidesUsed={md(result.get('columnGuidesUsed'))}")
        lines.append(f"- row preview: {md(result.get('rowPreview'))}")
        lines.append("")
    lines.extend(["## 7. 발견 문제", "| 샘플 | 문제 | 원인 | 후속 |", "|---|---|---|---|"])
    if report["issues"]:
        for issue in report["issues"]:
            lines.append(f"| {md(issue.get('sample'))} | {md(issue.get('problem'))} | {md(issue.get('cause'))} | {md(issue.get('followup'))} |")
    else:
        lines.append("| - | 없음 | - | - |")
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
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    print(report["decision"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
