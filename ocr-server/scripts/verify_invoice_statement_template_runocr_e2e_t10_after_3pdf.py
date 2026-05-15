"""
T-10 after 3pdf invoice_statement Template/RunOCR E2E verification.

This is a reporting-only script. It reads saved template annotations, selects
the best matching template per sample, calls /ocr/extract only when a saved
table annotation exists, and writes JSON/Markdown reports.
"""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime
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

OUT_JSON = REPORT_DIR / "T10_after_3pdf_template_runocr_e2e_20260515.json"
OUT_MD = REPORT_DIR / "T10_after_3pdf_template_runocr_e2e_20260515.md"

SAMPLES = ["1.jpg", "2.pdf", "3.pdf", "4.pdf", "5.pdf", "6.pdf", "7.pdf"]
EXPECTED = {
    "1.jpg": 28,
    "2.pdf": 13,
    "3.pdf": 1,
    "4.pdf": 1,
    "5.pdf": 6,
    "6.pdf": 6,
    "7.pdf": 1,
}
MIMES = {
    "1.jpg": "image/jpeg",
    "2.pdf": "application/pdf",
    "3.pdf": "application/pdf",
    "4.pdf": "application/pdf",
    "5.pdf": "application/pdf",
    "6.pdf": "application/pdf",
    "7.pdf": "application/pdf",
}
REGRESSION_BASELINE = {"1.jpg": 28, "2.pdf": 13, "5.pdf": 6}
SUMMARY_TOKENS = [
    "합계",
    "계약코드",
    "공급금액합계",
    "소비자금액합계",
    "전일잔액",
    "당일거래금액",
    "누계잔액",
    "구분",
    "채권",
    "약정",
    "인수",
    "서명",
]


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


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


def date_score(value: Any) -> float:
    if not value:
        return 0.0
    text = str(value).replace("Z", "+00:00")
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S.%f%z"):
        try:
            return datetime.strptime(text, fmt).timestamp()
        except ValueError:
            pass
    return 0.0


def table_regions(regions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [r for r in regions if r.get("fieldType") == "table" or r.get("type") == "table"]


def all_name_fields(template: dict[str, Any]) -> list[str]:
    tj = template.get("template_json") or {}
    file_info = tj.get("file") or {}
    values: list[Any] = [
        template.get("name"),
        template.get("template_name"),
        template.get("sourceFileName"),
        template.get("fileName"),
        template.get("originalFileName"),
        tj.get("name"),
        tj.get("templateName"),
        tj.get("sourceFileName"),
        tj.get("fileName"),
        tj.get("filename"),
        tj.get("originalFileName"),
    ]
    if isinstance(file_info, dict):
        values.extend(
            [
                file_info.get("name"),
                file_info.get("fileName"),
                file_info.get("filename"),
                file_info.get("originalFileName"),
            ]
        )
    return [str(v) for v in values if v]


def filename_matches(template: dict[str, Any], sample: str) -> bool:
    target = sample.lower()
    return any(target == Path(v).name.lower() or target in v.lower() for v in all_name_fields(template))


def updated_at(template: dict[str, Any]) -> Any:
    tj = template.get("template_json") or {}
    return template.get("updated_at") or template.get("updatedAt") or tj.get("updatedAt") or tj.get("updated_at")


def summarize_template(template: dict[str, Any]) -> dict[str, Any]:
    tj = template.get("template_json") or {}
    regions = tj.get("regions") or []
    tables = table_regions(regions if isinstance(regions, list) else [])
    table = tables[0] if tables else {}
    table_meta = table.get("table") or {}
    col_guides = table_meta.get("colGuides") or table_meta.get("colX") or table.get("colGuides") or []
    bounds = None
    if table:
        bounds = {k: table.get(k) for k in ["x", "y", "width", "height"]}
        if isinstance(bounds.get("y"), (int, float)) and isinstance(bounds.get("height"), (int, float)):
            bounds["yMax"] = bounds["y"] + bounds["height"]
    return {
        "template_id": template.get("template_id") or template.get("id"),
        "nameFields": all_name_fields(template),
        "documentType": tj.get("documentType"),
        "updatedAt": updated_at(template),
        "regionsCount": len(regions) if isinstance(regions, list) else 0,
        "tableRegionCount": len(tables),
        "tableRegion": bounds,
        "colGuidesCount": len(col_guides) if isinstance(col_guides, list) else 0,
        "colGuidesPreview": col_guides[:12] if isinstance(col_guides, list) else [],
    }


def is_target_template(row: dict[str, Any], sample: str) -> bool:
    if filename_matches(row, sample):
        return True
    if sample == "3.pdf":
        names = " ".join(all_name_fields(row)).lower()
        return "거래_3" in names
    if sample == "7.pdf":
        names = " ".join(all_name_fields(row)).lower()
        return "거래_7" in names
    return False


def select_template(sample: str, templates: list[dict[str, Any]]) -> dict[str, Any] | None:
    candidates = [row for row in templates if is_target_template(row, sample)]
    if not candidates:
        return None

    ranked: list[tuple[tuple[int, int, int, float, int], dict[str, Any], dict[str, Any]]] = []
    for index, row in enumerate(candidates):
        summary = summarize_template(row)
        doc_ok = 1 if summary.get("documentType") == "invoice_statement" else 0
        table_ok = 1 if summary.get("tableRegionCount") else 0
        name_ok = 1 if is_target_template(row, sample) else 0
        updated = date_score(summary.get("updatedAt"))
        ranked.append(((doc_ok, table_ok, name_ok, updated, index), row, summary))

    ranked.sort(key=lambda item: item[0])
    score, row, summary = ranked[-1]
    parts = []
    parts.append("documentType=invoice_statement" if score[0] else "documentType missing/mismatch")
    parts.append("table region exists" if score[1] else "table region missing")
    parts.append("filename matched")
    if summary.get("updatedAt"):
        parts.append(f"latest updatedAt={summary['updatedAt']}")
    parts.append("last matching record tie-break")
    return {
        "raw": row,
        "summary": summary,
        "selectedTemplateId": summary.get("template_id"),
        "selectionReason": "; ".join(parts),
        "candidateCount": len(candidates),
    }


def expected_columns(sample: str, manifest: dict[str, Any]) -> dict[str, Any] | None:
    for item in manifest.get("items", []):
        if item.get("filename") == sample:
            return (item.get("invoiceProfile") or {}).get("tableExpectedColumns") or None
    return None


def make_multipart(fields: dict[str, str], sample: str) -> tuple[bytes, str]:
    boundary = f"----codex-t10-final-{uuid.uuid4().hex}"
    chunks: list[bytes] = []
    for key, value in fields.items():
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
    return b"".join(chunks), boundary


def post_extract(sample: str, template: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    tj = template.get("template_json") or {}
    fields = {
        "template_id": str(template.get("template_id") or template.get("id") or ""),
        "regions": json.dumps(tj.get("regions") or [], ensure_ascii=False),
        "model_id": "",
        "documentType": "invoice_statement",
    }
    columns = expected_columns(sample, manifest)
    if columns:
        fields["tableExpectedColumns"] = json.dumps(columns, ensure_ascii=False)

    body, boundary = make_multipart(fields, sample)
    request = urllib.request.Request(
        f"{BASE_URL}/ocr/extract",
        data=body,
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

    parsed: dict[str, Any] = {"http_status": status, "elapsed_sec": round(time.time() - started, 1)}
    try:
        parsed["response"] = json.loads(text)
    except json.JSONDecodeError:
        parsed["error"] = text[:2000]
    return parsed


def row_text(row: Any) -> str:
    if isinstance(row, dict):
        return " ".join(str(v) for v in row.values() if v is not None)
    return str(row)


def has_summary_footer(rows: list[Any]) -> bool:
    text = "\n".join(row_text(row) for row in rows)
    return any(token in text for token in SUMMARY_TOKENS)


def parse_result(sample: str, api: dict[str, Any]) -> dict[str, Any]:
    response = api.get("response") or {}
    fields = response.get("document_fields") or {}
    meta = fields.get("tableMeta") or {}
    debug = response.get("extract_debug") or {}
    inv_debug = debug.get("invoice_statement") or {}
    rows = fields.get("tableRows") or []
    if not isinstance(rows, list):
        rows = []
    row_count = to_int(fields.get("rowCount"))
    if row_count is None:
        row_count = len(rows)
    warnings = meta.get("valueMappingWarnings") or meta.get("warnings") or []
    if isinstance(warnings, str):
        warnings = [warnings]
    status = "exact"
    if row_count != EXPECTED[sample]:
        status = "short" if row_count is not None and row_count < EXPECTED[sample] else "over"
    return {
        "http_status": api.get("http_status"),
        "elapsed_sec": api.get("elapsed_sec"),
        "doc_type": response.get("doc_type"),
        "template_path": response.get("template_path"),
        "tableRowsExists": bool(rows),
        "rowCount": row_count,
        "expectedRowCount": EXPECTED[sample],
        "status": status,
        "tableMetaExists": bool(meta),
        "extractionSource": meta.get("extractionSource") or inv_debug.get("extractionSource"),
        "tableBoundsUsed": meta.get("tableBoundsUsed"),
        "tableBoundsSource": meta.get("tableBoundsSource"),
        "columnGuidesReceived": meta.get("columnGuidesReceived"),
        "columnGuidesUsed": meta.get("columnGuidesUsed"),
        "columnGuidesCount": meta.get("columnGuidesCount"),
        "expectedValueFillRate": meta.get("expectedValueFillRate"),
        "expectedFilledKeys": meta.get("expectedFilledKeys") or [],
        "expectedMissingKeys": meta.get("expectedMissingKeys") or [],
        "valueMappingWarnings": warnings,
        "rowPreviewFirst": rows[:3],
        "rowPreviewLast": rows[-3:],
        "summaryFooterMixed": has_summary_footer(rows),
        "error": api.get("error"),
    }


def sample_specific_checks(sample: str, result: dict[str, Any] | None) -> dict[str, Any]:
    if not result:
        return {}
    rows = result.get("rowPreviewFirst", []) + result.get("rowPreviewLast", [])
    text = "\n".join(row_text(row) for row in rows)
    checks: dict[str, Any] = {}
    if sample == "6.pdf":
        checks["ANDC300C row kept"] = "ANDC300C" in text
    if sample == "7.pdf":
        checks["serialLotComposite/unit/quantity kept"] = {
            "has_1000": "1,000" in text or "1000" in text,
            "has_unit": "EA" in text or "박스" in text or "BOX" in text or "개" in text,
        }
    if sample == "3.pdf":
        checks["itemName kept"] = bool(text.strip())
    if sample == "4.pdf":
        checks["taxAmount/totalAmount target"] = {
            "has_2576000": "2,576,000" in text or "2576000" in text,
            "has_28338000": "28,338,000" in text or "28338000" in text,
        }
    return checks


def verify() -> dict[str, Any]:
    templates = load_json(TEMPLATES_PATH, [])
    manifest = load_json(MANIFEST_PATH, {})
    samples: dict[str, Any] = {}
    issues: list[dict[str, str]] = []
    missing_annotations: list[dict[str, str]] = []

    for sample in SAMPLES:
        selected = select_template(sample, templates)
        entry: dict[str, Any] = {
            "sample": sample,
            "expected": EXPECTED[sample],
            "candidateCount": selected.get("candidateCount") if selected else 0,
            "selectedTemplateId": selected.get("selectedTemplateId") if selected else None,
            "selectionReason": selected.get("selectionReason") if selected else "no filename-matched template record",
            "template": selected.get("summary") if selected else None,
            "apiExecuted": False,
            "result": None,
            "specificChecks": {},
            "status": "skipped_no_saved_template_annotation",
        }

        if not selected:
            missing_annotations.append(
                {
                    "sample": sample,
                    "reason": "templates.json에 샘플명과 매칭되는 template record 없음",
                    "required": "UI에서 invoice_statement documentType, table region, colGuides 저장 필요",
                }
            )
            issues.append(
                {
                    "sample": sample,
                    "problem": "annotation 없음",
                    "cause": "저장된 template record 없음",
                    "followup": "UI 저장 후 재검증",
                }
            )
            samples[sample] = entry
            continue

        summary = selected["summary"]
        if summary.get("documentType") != "invoice_statement" or not summary.get("tableRegionCount"):
            missing_annotations.append(
                {
                    "sample": sample,
                    "reason": "template은 있으나 documentType 또는 table region 조건 미충족",
                    "required": "documentType=invoice_statement 및 table region 저장 필요",
                }
            )
            issues.append(
                {
                    "sample": sample,
                    "problem": "실행 가능한 annotation 없음",
                    "cause": f"documentType={summary.get('documentType')}, tableRegionCount={summary.get('tableRegionCount')}",
                    "followup": "UI annotation 저장 확인",
                }
            )
            samples[sample] = entry
            continue

        api = post_extract(sample, selected["raw"], manifest)
        result = parse_result(sample, api)
        entry.update(
            {
                "apiExecuted": True,
                "result": result,
                "specificChecks": sample_specific_checks(sample, result),
                "status": result["status"],
            }
        )
        if result.get("doc_type") != "invoice_statement":
            issues.append(
                {
                    "sample": sample,
                    "problem": "documentType routing mismatch",
                    "cause": f"doc_type={result.get('doc_type')}",
                    "followup": "documentType payload/template metadata 재확인",
                }
            )
        if result.get("rowCount") != EXPECTED[sample]:
            direction = "short" if result.get("status") == "short" else "over"
            followup = "tableBounds 범위 확장 필요" if direction == "short" else "tableBounds 하단 조정 필요"
            issues.append(
                {
                    "sample": sample,
                    "problem": f"rowCount {direction}",
                    "cause": f"{result.get('rowCount')}/{EXPECTED[sample]}",
                    "followup": followup,
                }
            )
        samples[sample] = entry

    executed = [entry for entry in samples.values() if entry.get("apiExecuted")]
    exact = [entry for entry in executed if entry.get("status") == "exact"]
    missing = [entry for entry in samples.values() if not entry.get("apiExecuted")]
    if len(exact) == len(SAMPLES):
        decision = "7/7 E2E exact → 거래명세서 Template/RunOCR 1차 완료"
    elif missing:
        decision = "일부 annotation 없음 → UI 저장 후 재검증 필요"
    elif any(entry.get("status") == "over" for entry in executed):
        decision = "일부 over → 해당 샘플 tableBounds 하단 조정 필요"
    elif any(entry.get("status") == "short" for entry in executed):
        decision = "일부 short → 해당 샘플 tableBounds 범위 확장 필요"
    else:
        decision = "E2E 통과 후 History/result persistence 검증으로 이동"

    return {
        "task": "T-10-after-3pdf",
        "baseUrl": BASE_URL,
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "files": {
            "script": str(Path(__file__).resolve()),
            "markdown": str(OUT_MD),
            "json": str(OUT_JSON),
        },
        "summary": {
            "total": len(SAMPLES),
            "executed": len(executed),
            "exact": len(exact),
            "skipped": len(missing),
            "decision": decision,
        },
        "samples": samples,
        "issues": issues,
        "missingAnnotations": missing_annotations,
        "validation": {
            "script_py_compile": "not_run_in_script",
            "e2e_script": "completed",
            "npm_typecheck": "not_run_in_script",
            "npm_build": "not_run_in_script",
            "eslint_nextVitals_message": "not_run_in_script",
        },
    }


def result_cell(entry: dict[str, Any], key: str) -> Any:
    result = entry.get("result") or {}
    return result.get(key)


def template_cell(entry: dict[str, Any], key: str) -> Any:
    template = entry.get("template") or {}
    return template.get(key)


def render_markdown(report: dict[str, Any]) -> str:
    lines: list[str] = []
    samples = report["samples"]

    lines.append("# T-10 after 3pdf Template/RunOCR E2E 결과")
    lines.append("")
    lines.append("## 1. 생성 파일")
    lines.append(f"- script: `{report['files']['script']}`")
    lines.append(f"- Markdown report: `{report['files']['markdown']}`")
    lines.append(f"- JSON report: `{report['files']['json']}`")
    lines.append("")

    summary = report["summary"]
    lines.append("## 2. 핵심 요약")
    lines.append(f"- 검증 서버: `{report['baseUrl']}`")
    lines.append(f"- 전체 샘플: {summary['total']}")
    lines.append(f"- E2E 실행: {summary['executed']}")
    lines.append(f"- exact: {summary['exact']}")
    lines.append(f"- skipped: {summary['skipped']}")
    lines.append(f"- 최종 판단: {summary['decision']}")
    lines.append("")

    lines.append("## 3. Template annotation 확인")
    lines.append("| 샘플 | selectedTemplateId | selectionReason | documentType | table region | colGuides | 실행 여부 |")
    lines.append("|---|---|---|---|---|---|---|")
    for sample in SAMPLES:
        entry = samples[sample]
        region = template_cell(entry, "tableRegion")
        region_text = "있음 " + md(region) if region else "없음"
        lines.append(
            "| "
            + " | ".join(
                [
                    md(sample),
                    md(entry.get("selectedTemplateId")),
                    md(entry.get("selectionReason")),
                    md(template_cell(entry, "documentType")),
                    region_text,
                    md(template_cell(entry, "colGuidesCount")),
                    "실행" if entry.get("apiExecuted") else "skipped",
                ]
            )
            + " |"
        )
    lines.append("")

    lines.append("## 4. E2E rowCount 결과")
    lines.append("| 샘플 | GT | Test 기준 | RunOCR E2E | 상태 |")
    lines.append("|---|---:|---:|---:|---|")
    for sample in SAMPLES:
        entry = samples[sample]
        lines.append(
            f"| {sample} | {EXPECTED[sample]} | {EXPECTED[sample]} | "
            f"{md(result_cell(entry, 'rowCount'))} | {md(entry.get('status'))} |"
        )
    lines.append("")

    lines.append("## 5. tableMeta/debug 결과")
    lines.append("| 샘플 | doc_type | extractionSource | tableBoundsUsed | columnGuidesReceived | columnGuidesUsed | warnings |")
    lines.append("|---|---|---|---|---|---|---|")
    for sample in SAMPLES:
        entry = samples[sample]
        lines.append(
            "| "
            + " | ".join(
                [
                    md(sample),
                    md(result_cell(entry, "doc_type")),
                    md(result_cell(entry, "extractionSource")),
                    md(result_cell(entry, "tableBoundsUsed")),
                    md(result_cell(entry, "columnGuidesReceived")),
                    md(result_cell(entry, "columnGuidesUsed")),
                    md(result_cell(entry, "valueMappingWarnings")),
                ]
            )
            + " |"
        )
    lines.append("")

    lines.append("## 6. 샘플별 상세")
    for sample in SAMPLES:
        entry = samples[sample]
        result = entry.get("result") or {}
        lines.append("")
        lines.append(f"### {sample}")
        lines.append(f"- template: {md(entry.get('selectedTemplateId'))} ({md(entry.get('selectionReason'))})")
        lines.append(f"- bounds: {md(template_cell(entry, 'tableRegion'))}")
        lines.append(f"- rowCount: {md(result.get('rowCount'))}/{EXPECTED[sample]}")
        lines.append(f"- extractionSource: {md(result.get('extractionSource'))}")
        lines.append(f"- columnGuides: received={md(result.get('columnGuidesReceived'))}, used={md(result.get('columnGuidesUsed'))}, count={md(result.get('columnGuidesCount'))}")
        lines.append(f"- warning: {md(result.get('valueMappingWarnings'))}")
        if sample == "2.pdf":
            lines.append(f"- summary row 포함 여부: {md(result.get('summaryFooterMixed'))}")
        if sample == "6.pdf":
            lines.append(f"- ANDC300C row 유지 여부: {md((entry.get('specificChecks') or {}).get('ANDC300C row kept'))}")
        if sample == "7.pdf":
            lines.append(f"- serialLotComposite/unit/quantity 유지 여부: {md((entry.get('specificChecks') or {}).get('serialLotComposite/unit/quantity kept'))}")
        lines.append(f"- first rows: {md(result.get('rowPreviewFirst'))}")
        lines.append(f"- last rows: {md(result.get('rowPreviewLast'))}")
        lines.append(f"- 판정: {md(entry.get('status'))}")
    lines.append("")

    lines.append("## 7. 발견 문제")
    lines.append("| 샘플 | 문제 | 원인 추정 | 후속 |")
    lines.append("|---|---|---|---|")
    if report["issues"]:
        for issue in report["issues"]:
            lines.append(f"| {md(issue.get('sample'))} | {md(issue.get('problem'))} | {md(issue.get('cause'))} | {md(issue.get('followup'))} |")
    else:
        lines.append("| - | 없음 | - | - |")
    lines.append("")

    lines.append("## 8. annotation 없는 샘플")
    lines.append("| 샘플 | 사유 | 필요한 작업 |")
    lines.append("|---|---|---|")
    if report["missingAnnotations"]:
        for item in report["missingAnnotations"]:
            lines.append(f"| {md(item.get('sample'))} | {md(item.get('reason'))} | {md(item.get('required'))} |")
    else:
        lines.append("| - | 없음 | - |")
    lines.append("")

    lines.append("## 9. 회귀 확인")
    lines.append("| 샘플 | 기존 E2E | 최종 E2E | 회귀 여부 |")
    lines.append("|---|---:|---:|---|")
    for sample, baseline in REGRESSION_BASELINE.items():
        final = result_cell(samples[sample], "rowCount")
        regression = "없음" if final == baseline else "확인 필요"
        lines.append(f"| {sample} | {baseline} | {md(final)} | {regression} |")
    lines.append("")

    validation = report["validation"]
    lines.append("## 10. 검증 결과")
    lines.append(f"- script py_compile: {validation['script_py_compile']}")
    lines.append(f"- E2E script: {validation['e2e_script']}")
    lines.append(f"- npm typecheck: {validation['npm_typecheck']}")
    lines.append(f"- npm build: {validation['npm_build']}")
    lines.append(f"- 기존 ESLint nextVitals 메시지 여부: {validation['eslint_nextVitals_message']}")
    lines.append("")

    lines.append("## 11. 다음 작업 판단")
    lines.append(f"- {summary['decision']}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    report = verify()
    write_json(OUT_JSON, report)
    write_text(OUT_MD, render_markdown(report))
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    print(f"Wrote {OUT_JSON}")
    print(f"Wrote {OUT_MD}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
