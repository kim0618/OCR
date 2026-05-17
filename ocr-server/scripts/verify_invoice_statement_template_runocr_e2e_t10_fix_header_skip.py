"""
T-10-fix template_colguides header row 자동 제외 검증 스크립트.

6.pdf rowCount 7/6 over 해결 및 전체 E2E 회귀 없음 확인.
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

OUT_JSON = REPORT_DIR / "T10_fix_template_colguides_header_skip_20260516.json"
OUT_MD = REPORT_DIR / "T10_fix_template_colguides_header_skip_20260516.md"

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
    "합계", "계약코드", "공급금액합계", "소비자금액합계",
    "전일잔액", "당일거래금액", "누계잔액", "구분", "채권", "약정", "인수", "서명",
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
        template.get("name"), template.get("template_name"),
        template.get("sourceFileName"), template.get("fileName"),
        template.get("originalFileName"),
        tj.get("name"), tj.get("templateName"), tj.get("sourceFileName"),
        tj.get("fileName"), tj.get("filename"), tj.get("originalFileName"),
    ]
    if isinstance(file_info, dict):
        values.extend([
            file_info.get("name"), file_info.get("fileName"),
            file_info.get("filename"), file_info.get("originalFileName"),
        ])
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
    names = " ".join(all_name_fields(row)).lower()
    sample_map = {
        "3.pdf": "거래_3", "4.pdf": "거래_4",
        "6.pdf": "거래_6", "7.pdf": "거래_7",
    }
    return sample in sample_map and sample_map[sample] in names


def select_template(sample: str, templates: list[dict[str, Any]]) -> dict[str, Any] | None:
    candidates = [row for row in templates if is_target_template(row, sample)]
    if not candidates:
        return None
    ranked = []
    for index, row in enumerate(candidates):
        summary = summarize_template(row)
        doc_ok = 1 if summary.get("documentType") == "invoice_statement" else 0
        table_ok = 1 if summary.get("tableRegionCount") else 0
        name_ok = 1 if is_target_template(row, sample) else 0
        updated = date_score(summary.get("updatedAt"))
        ranked.append(((doc_ok, table_ok, name_ok, updated, index), row, summary))
    ranked.sort(key=lambda item: item[0])
    score, row, summary = ranked[-1]
    parts = [
        "documentType=invoice_statement" if score[0] else "documentType missing/mismatch",
        "table region exists" if score[1] else "table region missing",
        "filename matched",
    ]
    if summary.get("updatedAt"):
        parts.append(f"latest updatedAt={summary['updatedAt']}")
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
    boundary = f"----codex-t10-fix-hdr-{uuid.uuid4().hex}"
    chunks: list[bytes] = []
    for key, value in fields.items():
        chunks.append(f"--{boundary}\r\n".encode("utf-8"))
        chunks.append(f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode("utf-8"))
        chunks.append(value.encode("utf-8"))
        chunks.append(b"\r\n")
    chunks.append(f"--{boundary}\r\n".encode("utf-8"))
    chunks.append((
        f'Content-Disposition: form-data; name="file"; filename="{sample}"\r\n'
        f"Content-Type: {MIMES[sample]}\r\n\r\n"
    ).encode("utf-8"))
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
        "rowCount": row_count,
        "expectedRowCount": EXPECTED[sample],
        "status": status,
        "extractionSource": meta.get("extractionSource") or inv_debug.get("extractionSource"),
        "tableBoundsUsed": meta.get("tableBoundsUsed"),
        "columnGuidesReceived": meta.get("columnGuidesReceived"),
        "columnGuidesUsed": meta.get("columnGuidesUsed"),
        "columnGuidesCount": meta.get("columnGuidesCount"),
        # T-10-fix: new fields
        "headerRowsSkippedCount": meta.get("headerRowsSkippedCount", 0),
        "headerRowsSkippedSamples": meta.get("headerRowsSkippedSamples", []),
        "headerSkipAppliedSource": meta.get("headerSkipAppliedSource", ""),
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
    rows_json = json.dumps(rows, ensure_ascii=False)
    text = "\n".join(row_text(row) for row in rows)
    checks: dict[str, Any] = {}
    if sample == "6.pdf":
        checks["ANDC300C row kept"] = "ANDC300C" in text
        checks["quantity 0 row kept"] = (
            '"quantity": "0"' in rows_json
            or '"quantity":"0"' in rows_json
            or " 0 " in f" {text} "
        )
        checks["headerRowsSkippedCount"] = result.get("headerRowsSkippedCount", 0)
        checks["headerRowsSkippedSamples"] = result.get("headerRowsSkippedSamples", [])
    if sample == "7.pdf":
        checks["quantity=1,000 kept"] = "1,000" in text or "1000" in text
    if sample == "5.pdf":
        checks["multiline layout rowCount"] = result.get("rowCount")
    if sample == "2.pdf":
        checks["OP-anchor rowCount"] = result.get("rowCount")
        checks["summaryFooterMixed"] = result.get("summaryFooterMixed")
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
            missing_annotations.append({
                "sample": sample,
                "reason": "templates.json에 샘플명과 매칭되는 template record 없음",
                "required": "UI에서 invoice_statement documentType, table region, colGuides 저장 필요",
            })
            issues.append({"sample": sample, "problem": "annotation 없음",
                           "cause": "저장된 template record 없음", "followup": "UI 저장 후 재검증"})
            samples[sample] = entry
            continue

        summary = selected["summary"]
        if summary.get("documentType") != "invoice_statement" or not summary.get("tableRegionCount"):
            missing_annotations.append({
                "sample": sample,
                "reason": "template은 있으나 documentType 또는 table region 조건 미충족",
                "required": "documentType=invoice_statement 및 table region 저장 필요",
            })
            issues.append({"sample": sample, "problem": "실행 가능한 annotation 없음",
                           "cause": f"documentType={summary.get('documentType')}, tableRegionCount={summary.get('tableRegionCount')}",
                           "followup": "UI annotation 저장 확인"})
            samples[sample] = entry
            continue

        api = post_extract(sample, selected["raw"], manifest)
        result = parse_result(sample, api)
        entry.update({
            "apiExecuted": True,
            "result": result,
            "specificChecks": sample_specific_checks(sample, result),
            "status": result["status"],
        })
        if result.get("rowCount") != EXPECTED[sample]:
            direction = "short" if result.get("status") == "short" else "over"
            followup = ("header skip 조건 완화 필요" if direction == "short"
                        else "header skip 조건 추가 보정 필요" if sample == "6.pdf"
                        else "tableBounds 하단 조정 필요")
            issues.append({"sample": sample, "problem": f"rowCount {direction}",
                           "cause": f"{result.get('rowCount')}/{EXPECTED[sample]}", "followup": followup})
        samples[sample] = entry

    executed = [e for e in samples.values() if e.get("apiExecuted")]
    exact = [e for e in executed if e.get("status") == "exact"]
    missing = [e for e in samples.values() if not e.get("apiExecuted")]

    if len(exact) == len(SAMPLES):
        decision = "전체 E2E 7/7 exact 달성 → Template/RunOCR E2E 1차 마감"
    elif missing:
        decision = "일부 annotation 없음 → UI 저장 후 재검증 필요"
    elif any(e.get("status") == "over" for e in executed):
        over_samples = [e["sample"] for e in executed if e.get("status") == "over"]
        if "6.pdf" in over_samples:
            decision = "6.pdf 여전히 over → header skip 조건 추가 보정 필요"
        else:
            decision = f"over 샘플: {over_samples} → tableBounds 하단 조정 필요"
    elif any(e.get("status") == "short" for e in executed):
        short_samples = [e["sample"] for e in executed if e.get("status") == "short"]
        if "6.pdf" in short_samples:
            decision = "6.pdf short 발생 → header skip이 실제 row를 제거했으므로 조건 완화"
        else:
            decision = f"short 샘플: {short_samples} → tableBounds 범위 확장 필요"
    else:
        decision = "E2E 통과 후 다음 단계로 이동"

    return {
        "task": "T-10-fix-header-skip",
        "baseUrl": BASE_URL,
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "files": {"script": str(Path(__file__).resolve()), "markdown": str(OUT_MD), "json": str(OUT_JSON)},
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
    summary = report["summary"]
    s6 = samples.get("6.pdf", {})
    s6_result = s6.get("result") or {}
    s6_checks = s6.get("specificChecks") or {}

    lines.append("# T-10-fix template_colguides header row 자동 제외 결과")
    lines.append("")

    lines.append("## 1. 수정 파일")
    lines.append("- `ocr-server/extractors/invoice_statement.py`")
    lines.append("")

    lines.append("## 2. 백업 파일")
    lines.append("- `ocr-server/backup/invoice_statement_20260516_before_T10_fix_template_header_skip.py`")
    lines.append("")

    lines.append("## 3. 핵심 요약")
    lines.append(f"- {summary['decision']}")
    lines.append(f"- exact: {summary['exact']}/{summary['total']}")
    lines.append(f"- 생성: {report['generatedAt']}")
    lines.append("")

    lines.append("## 4. 기존 문제")
    lines.append("- 6.pdf E2E rowCount: **7/6 (over)**")
    lines.append("- extra row text: `NO 제품코드 5 24001 270305`")
    lines.append("- 원인: tableBounds가 헤더를 포함하고 colGuides 경로가 헤더 행을 데이터 row로 오인")
    lines.append("")

    lines.append("## 5. header row skip 로직")
    lines.append("- 적용 경로: `template_colguides_expected_columns` (`skip_contact_filter=True`)")
    lines.append("- 판정 기준: `_is_colguides_header_like_row()` — 확장 header keyword(NO, 제품코드 포함) 2개 이상 AND strong item signal 없음")
    lines.append("- 위치 기반: tableBounds 상단 20% 이내 + keyword 1개 이상 → header")
    lines.append("- strong item signal 예외: mixed-case 제품코드(ANDC300C 패턴), Korean 4자+ (품목명 내용)")
    lines.append("")

    lines.append("## 6. 6.pdf 결과")
    lines.append("| 항목 | 결과 |")
    lines.append("|---|---|")
    lines.append(f"| doc_type | {md(s6_result.get('doc_type'))} |")
    lines.append(f"| extractionSource | {md(s6_result.get('extractionSource'))} |")
    lines.append(f"| tableBoundsUsed | {md(s6_result.get('tableBoundsUsed'))} |")
    lines.append(f"| columnGuidesUsed | {md(s6_result.get('columnGuidesUsed'))} |")
    lines.append(f"| rowCount | {md(s6_result.get('rowCount'))}/{EXPECTED['6.pdf']} |")
    lines.append(f"| headerRowsSkipped | {md(s6_checks.get('headerRowsSkippedCount'))} |")
    lines.append(f"| headerRowsSkippedSamples | {md(s6_checks.get('headerRowsSkippedSamples'))} |")
    lines.append(f"| ANDC300C 유지 | {md(s6_checks.get('ANDC300C row kept'))} |")
    lines.append(f"| quantity 0 유지 | {md(s6_checks.get('quantity 0 row kept'))} |")
    lines.append("")

    lines.append("## 7. 전체 E2E rowCount 결과")
    lines.append("| 샘플 | 기대 | 결과 | 상태 |")
    lines.append("|---|---:|---:|---|")
    for sample in SAMPLES:
        entry = samples[sample]
        lines.append(
            f"| {sample} | {EXPECTED[sample]} | {md(result_cell(entry, 'rowCount'))} | {md(entry.get('status'))} |"
        )
    lines.append("")

    lines.append("## 8. 회귀 확인")
    lines.append("| 항목 | 결과 |")
    lines.append("|---|---|")
    s2_checks = (samples.get("2.pdf", {}).get("specificChecks") or {})
    s5_checks = (samples.get("5.pdf", {}).get("specificChecks") or {})
    s7_checks = (samples.get("7.pdf", {}).get("specificChecks") or {})
    lines.append(f"| 2.pdf OP-anchor 유지 | rowCount={md(s2_checks.get('OP-anchor rowCount'))} |")
    lines.append(f"| 5.pdf multiline 유지 | rowCount={md(s5_checks.get('multiline layout rowCount'))} |")
    lines.append(f"| 7.pdf quantity=1,000 유지 | {md(s7_checks.get('quantity=1,000 kept'))} |")
    test_7_7 = all(
        result_cell(samples[s], "rowCount") == EXPECTED[s]
        for s in SAMPLES
        if samples[s].get("apiExecuted")
    )
    lines.append(f"| Test 기준 rowCount 7/7 유지 | {md(test_7_7)} |")
    lines.append("")

    lines.append("## 9. 검증 결과")
    validation = report["validation"]
    lines.append(f"- py_compile: {validation['script_py_compile']}")
    lines.append(f"- E2E script: {validation['e2e_script']}")
    lines.append(f"- typecheck: {validation['npm_typecheck']}")
    lines.append(f"- build: {validation['npm_build']}")
    lines.append("")

    lines.append("## 10. 다음 작업 판단")
    lines.append(f"- {summary['decision']}")
    lines.append("")

    if report.get("issues"):
        lines.append("## 11. 발견 문제")
        lines.append("| 샘플 | 문제 | 원인 | 후속 |")
        lines.append("|---|---|---|---|")
        for issue in report["issues"]:
            lines.append(
                f"| {md(issue.get('sample'))} | {md(issue.get('problem'))} | {md(issue.get('cause'))} | {md(issue.get('followup'))} |"
            )
        lines.append("")

    return "\n".join(lines)


def main() -> int:
    report = verify()
    write_json(OUT_JSON, report)
    write_text(OUT_MD, render_markdown(report))

    summary = report["summary"]
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    # 6.pdf 상세 출력
    s6 = report["samples"].get("6.pdf", {})
    s6_result = s6.get("result") or {}
    s6_checks = s6.get("specificChecks") or {}
    print(f"\n=== 6.pdf ===")
    print(f"  rowCount: {s6_result.get('rowCount')}/{EXPECTED['6.pdf']} [{s6.get('status')}]")
    print(f"  headerRowsSkippedCount: {s6_checks.get('headerRowsSkippedCount', 0)}")
    print(f"  headerRowsSkippedSamples: {s6_checks.get('headerRowsSkippedSamples', [])}")
    print(f"  ANDC300C kept: {s6_checks.get('ANDC300C row kept')}")
    print(f"  quantity 0 kept: {s6_checks.get('quantity 0 row kept')}")

    print(f"\nWrote {OUT_JSON}")
    print(f"Wrote {OUT_MD}")
    return 0 if summary["exact"] == summary["total"] else 1


if __name__ == "__main__":
    sys.exit(main())
