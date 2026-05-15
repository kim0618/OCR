"""
T-10 2.pdf bounds save-check.

This reporting-only script first compares the saved 2.pdf table bounds in
templates.json against the previous over-wide bounds. It calls /ocr/extract only
when the saved bounds changed. It does not edit templates, extractor logic,
frontend source, manifest, or ground truth.
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

OUT_JSON = REPORT_DIR / "T10_2pdf_bounds_save_check_20260515.json"
OUT_MD = REPORT_DIR / "T10_2pdf_bounds_save_check_20260515.md"

PREVIOUS = {"x": 111, "y": 136, "width": 1486, "height": 2112, "yMax": 2248}
EXPECTED = {"1.jpg": 28, "5.pdf": 6, "2.pdf": 13}
MIMES = {"1.jpg": "image/jpeg", "5.pdf": "application/pdf", "2.pdf": "application/pdf"}
SUMMARY_KEYWORDS = ["합계", "계약코드", "잔액", "구분", "채 권", "약정", "전일잔액", "당일거래금액", "누계잔액"]


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
        "table_region_count": len(tables),
        "bounds": bounds_of(table) if table else None,
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
    boundary = f"----codex-save-check-{uuid.uuid4().hex}"
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
    req = urllib.request.Request(
        f"{BASE_URL}/ocr/extract",
        data=b"".join(chunks),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    started = time.time()
    try:
        with urllib.request.urlopen(req, timeout=420) as resp:
            status = resp.status
            text = resp.read().decode("utf-8", errors="replace")
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
    row_text = json.dumps(rows, ensure_ascii=False)
    hits = [kw for kw in SUMMARY_KEYWORDS if kw in row_text]
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
        "lastRows": rows[-3:] if isinstance(rows, list) else [],
        "summaryRowsIncluded": bool(hits),
        "summaryKeywordHits": hits,
        "valueMappingWarnings": meta.get("valueMappingWarnings") or meta.get("warnings") or [],
        "error": api.get("error"),
    }


def compare_bounds(current: dict[str, Any] | None) -> dict[str, Any]:
    current = current or {}
    rows: dict[str, dict[str, Any]] = {}
    changed_any = False
    for key in ["x", "y", "width", "height", "yMax"]:
        old = PREVIOUS.get(key)
        now = current.get(key)
        changed = old != now
        rows[key] = {"previous": old, "current": now, "changed": changed}
        changed_any = changed_any or changed
    return {"rows": rows, "boundsChanged": changed_any, "yMaxReduced": (current.get("yMax") or 0) < PREVIOUS["yMax"]}


def verify() -> dict[str, Any]:
    templates = discover_templates()
    manifest = load_json(MANIFEST_PATH, {})
    t2 = templates.get("2.pdf")
    current_bounds = (t2.get("summary") or {}).get("bounds") if t2 else None
    bounds_check = compare_bounds(current_bounds)
    e2e_executed = bool(bounds_check["boundsChanged"])
    skipped_reason = "" if e2e_executed else "boundsChanged=false; UI table region 재저장 반영 없음"
    samples: dict[str, Any] = {}
    if e2e_executed:
        for sample in ["1.jpg", "5.pdf", "2.pdf"]:
            matched = templates.get(sample)
            if not matched:
                samples[sample] = {"status": "skipped_missing_template", "result": None}
                continue
            api = post_extract(sample, matched["raw"], manifest)
            result = parse_result(sample, api)
            samples[sample] = {"status": result["status"], "result": result}
    else:
        for sample in ["1.jpg", "5.pdf", "2.pdf"]:
            samples[sample] = {"status": "not_run", "result": None}

    r2 = (samples.get("2.pdf") or {}).get("result") or {}
    if not bounds_check["boundsChanged"]:
        decision = "boundsChanged=false → UI 저장/수정 반영 문제 확인"
    elif r2.get("status") == "exact":
        decision = "rowCount 13/13 → 7.pdf/6.pdf annotation 저장으로 이동"
    elif r2.get("status") == "short":
        decision = "boundsChanged=true + rowCount short → 하단 y를 조금 내림"
    else:
        decision = "boundsChanged=true + rowCount over → 하단 y를 더 올림"

    return {
        "task": "T-10-2pdf-bounds-save-check",
        "date": "2026-05-15",
        "baseUrl": BASE_URL,
        "createdFiles": {"script": str(Path(__file__).resolve()), "markdown": str(OUT_MD), "json": str(OUT_JSON)},
        "template2pdf": t2.get("summary") if t2 else None,
        "boundsCheck": bounds_check,
        "e2eExecuted": e2e_executed,
        "skipReason": skipped_reason,
        "samples": samples,
        "verification": {"script_py_compile": "not_run_in_script", "e2e_script": "completed", "typecheck": "not_run_in_script", "build": "not_run_in_script"},
        "decision": decision,
    }


def render_markdown(report: dict[str, Any]) -> str:
    rows = report["boundsCheck"]["rows"]
    samples = report["samples"]
    r2 = (samples.get("2.pdf") or {}).get("result") or {}
    lines = [
        "# T-10 2.pdf bounds 저장 반영 확인 및 E2E 결과",
        "",
        "## 1. 생성 파일",
        f"- Script: `{report['createdFiles']['script']}`",
        f"- Markdown report: `{report['createdFiles']['markdown']}`",
        f"- JSON report: `{report['createdFiles']['json']}`",
        "",
        "## 2. bounds 변경 확인",
        "| 항목 | 이전 | 현재 | 변경 여부 |",
        "|---|---:|---:|---|",
    ]
    for key in ["x", "y", "width", "height", "yMax"]:
        row = rows[key]
        lines.append(f"| {key} | {md(row['previous'])} | {md(row['current'])} | {md(row['changed'])} |")
    lines.extend([
        "",
        "## 3. E2E 실행 여부",
        f"- boundsChanged: {md(report['boundsCheck']['boundsChanged'])}",
        f"- E2E 실행 여부: {md(report['e2eExecuted'])}",
        f"- 실행하지 않았다면 사유: {md(report['skipReason'])}",
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
        "## 5. row preview",
        f"- 마지막 row preview: {md(r2.get('lastRows'))}",
        f"- summary/잔액 row 포함 여부: {md(r2.get('summaryRowsIncluded'))} {md(r2.get('summaryKeywordHits'))}",
        "",
        "## 6. 회귀 확인",
        "| 샘플 | 기대 | 결과 | 상태 |",
        "|---|---:|---:|---|",
    ])
    for sample in ["1.jpg", "5.pdf", "2.pdf"]:
        result = (samples.get(sample) or {}).get("result") or {}
        lines.append(f"| {sample} | {EXPECTED[sample]} | {md(result.get('rowCount'))} | {md((samples.get(sample) or {}).get('status'))} |")
    lines.extend([
        "",
        "## 7. 다음 작업 판단",
        f"- {report['decision']}",
        "",
        "## 8. 검증 결과",
        f"- script py_compile: {md(report['verification'].get('script_py_compile'))}",
        f"- E2E script: {md(report['verification'].get('e2e_script'))}",
        f"- typecheck: {md(report['verification'].get('typecheck'))}",
        f"- build: {md(report['verification'].get('build'))}",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    report = verify()
    write_json(OUT_JSON, report)
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps({"boundsChanged": report["boundsCheck"]["boundsChanged"], "e2eExecuted": report["e2eExecuted"], "decision": report["decision"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
