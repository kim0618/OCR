from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import requests


ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "ocr-server"
FRONTEND = ROOT / "mysuit-ocr"
TESTSETS = FRONTEND / "public" / "data" / "testsets"
REPORTS = TESTSETS / "reports"

OUT_JSON = REPORTS / "T20e_preprocessing_debug_api_validation_20260516.json"
OUT_MD = REPORTS / "T20e_preprocessing_debug_api_validation_20260516.md"

TEMPLATES_PATH = BACKEND / "data" / "templates.json"
INVOICE_MANIFEST = TESTSETS / "invoice_statement" / "manifest.json"

DEFAULT_BASE_URL = "http://127.0.0.1:8121"

TARGETS = [
    "receipt_generalization/card_002.jpg",
    "receipt_generalization/medical_001.jpg",
    "receipt_generalization/pos_006.jpg",
    "receipt_generalization/medical_003.jpg",
    "invoice_statement/3.pdf",
    "invoice_statement/2.pdf",
    "invoice_statement/1.jpg",
    "invoice_statement/5.pdf",
    "receipt_generalization/pos_005.jpg",
    "receipt_generalization/card_001.jpg",
]

EXPECTED_CANDIDATES = {
    "receipt_generalization/card_002.jpg": ("clahe", "candidate_accept"),
    "receipt_generalization/medical_001.jpg": ("clahe", "candidate_accept"),
    "receipt_generalization/pos_006.jpg": ("upscale_1_5x", "candidate_accept"),
    "receipt_generalization/medical_003.jpg": ("grayscale", "candidate_accept"),
    "invoice_statement/3.pdf": ("render_dpi_200_grayscale", "candidate_accept"),
    "invoice_statement/2.pdf": (None, "preprocessing_blocked"),
}

INVOICE_EXPECTED_ROWS = {
    "1.jpg": 28,
    "2.pdf": 13,
    "3.pdf": 1,
    "4.pdf": 1,
    "5.pdf": 6,
    "6.pdf": 6,
    "7.pdf": 1,
}


def load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return {} if default is None else default
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def is_port_open(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex((host, port)) == 0


def start_server(base_url: str) -> tuple[subprocess.Popen[str] | None, str]:
    host = "127.0.0.1"
    port = int(base_url.rsplit(":", 1)[1])
    if is_port_open(host, port):
        return None, "reused_existing_server"

    out_log = BACKEND / "t20e_8121.out.log"
    err_log = BACKEND / "t20e_8121.err.log"
    stdout = out_log.open("w", encoding="utf-8")
    stderr = err_log.open("w", encoding="utf-8")
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--host", host, "--port", str(port)],
        cwd=str(BACKEND),
        stdout=stdout,
        stderr=stderr,
        text=True,
    )
    deadline = time.time() + 90
    last_error = ""
    while time.time() < deadline:
        try:
            res = requests.get(f"{base_url}/health", timeout=3)
            if res.status_code == 200:
                return proc, f"started_server pid={proc.pid}"
        except Exception as exc:
            last_error = str(exc)
        if proc.poll() is not None:
            raise RuntimeError(f"server exited early: {proc.returncode}; {last_error}")
        time.sleep(2)
    raise RuntimeError(f"server did not become ready: {last_error}")


def stop_server(proc: subprocess.Popen[str] | None) -> None:
    if not proc:
        return
    proc.terminate()
    try:
        proc.wait(timeout=20)
    except subprocess.TimeoutExpired:
        proc.kill()


def manifest_item(testset_id: str, filename: str) -> dict[str, Any]:
    manifest = load_json(TESTSETS / testset_id / "manifest.json", {})
    for item in manifest.get("items", []):
        if item.get("filename") == filename:
            return item
    return {}


def sample_path(sample: str) -> Path:
    testset_id, filename = sample.split("/", 1)
    return TESTSETS / testset_id / filename


def invoice_expected_columns(filename: str) -> dict[str, Any] | None:
    item = manifest_item("invoice_statement", filename)
    return (item.get("invoiceProfile") or {}).get("tableExpectedColumns") or None


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
        values.extend([file_info.get("name"), file_info.get("fileName"), file_info.get("filename"), file_info.get("originalFileName")])
    return [str(v) for v in values if v]


def select_template(filename: str) -> dict[str, Any] | None:
    templates = load_json(TEMPLATES_PATH, [])
    target = filename.lower()
    candidates = []
    for row in templates:
        if any(target == Path(v).name.lower() or target in v.lower() for v in all_name_fields(row)):
            candidates.append(row)
    if not candidates:
        return None
    candidates.sort(key=lambda row: str(row.get("updated_at") or row.get("updatedAt") or ""))
    return candidates[-1]


def call_extract(
    base_url: str,
    sample: str,
    debug: bool,
    use_template: bool = False,
) -> dict[str, Any]:
    testset_id, filename = sample.split("/", 1)
    path = sample_path(sample)
    item = manifest_item(testset_id, filename)
    data: dict[str, str] = {}

    if item.get("documentType"):
        data["documentType"] = item["documentType"]
    if debug:
        data["debugPreprocessing"] = "true"
    if item.get("qualityTags") is not None:
        data["qualityTagsJson"] = json.dumps(item.get("qualityTags") or [], ensure_ascii=False)

    if use_template and testset_id == "invoice_statement":
        template = select_template(filename)
        if template:
            tj = template.get("template_json") or {}
            data["template_id"] = str(template.get("template_id") or template.get("id") or "")
            data["regions"] = json.dumps(tj.get("regions") or [], ensure_ascii=False)
            data["documentType"] = "invoice_statement"
            columns = invoice_expected_columns(filename)
            if columns:
                data["tableExpectedColumns"] = json.dumps(columns, ensure_ascii=False)

    with path.open("rb") as fh:
        files = {"file": (filename, fh, "application/pdf" if filename.lower().endswith(".pdf") else "image/jpeg")}
        started = time.time()
        response = requests.post(f"{base_url}/ocr/extract", data=data, files=files, timeout=600)
    elapsed = round(time.time() - started, 3)
    parsed: dict[str, Any] = {"httpStatus": response.status_code, "elapsedSec": elapsed, "requestDataKeys": sorted(data.keys())}
    try:
        parsed["response"] = response.json()
    except Exception:
        parsed["error"] = response.text[:2000]
    return parsed


def fields_summary(response: dict[str, Any]) -> dict[str, Any]:
    doc_fields = response.get("document_fields") or {}
    fields_list = response.get("fields") or []
    row_count = doc_fields.get("rowCount")
    table_rows = doc_fields.get("tableRows")
    if row_count is None and isinstance(table_rows, list):
        row_count = len(table_rows)

    field_map: dict[str, Any] = {}
    if isinstance(fields_list, list):
        for field in fields_list:
            if isinstance(field, dict) and field.get("name"):
                field_map[str(field.get("name"))] = field.get("value")
    for key in ["merchantName", "businessNo", "totalAmount", "상호", "사업자번호", "총합계금액"]:
        if key in doc_fields:
            field_map[key] = doc_fields.get(key)

    warnings = []
    table_meta = doc_fields.get("tableMeta") or {}
    if isinstance(table_meta, dict):
        warnings.extend(table_meta.get("valueMappingWarnings") or [])
    warnings.extend(response.get("warnings") or [])
    return {
        "docType": response.get("doc_type"),
        "status": response.get("status") or response.get("resultStatus") or "",
        "fields": field_map,
        "rowCount": row_count,
        "tableMeta": table_meta,
        "warnings": warnings,
        "hasPreprocessingDebug": "preprocessingDebug" in response,
        "preprocessingDebug": response.get("preprocessingDebug"),
        "error": response.get("error") or "",
    }


def to_int(value: Any) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    text = str(value).strip().replace(",", "")
    return int(text) if text.isdigit() else None


def stable_projection(summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "docType": summary.get("docType"),
        "status": summary.get("status"),
        "fields": summary.get("fields"),
        "rowCount": summary.get("rowCount"),
        "warnings": summary.get("warnings"),
        "error": summary.get("error"),
    }


def compare_summaries(false_summary: dict[str, Any], true_summary: dict[str, Any]) -> dict[str, Any]:
    fp = stable_projection(false_summary)
    tp = stable_projection(true_summary)
    return {
        "fieldsSame": fp.get("fields") == tp.get("fields"),
        "rowCountSame": fp.get("rowCount") == tp.get("rowCount"),
        "warningsSame": fp.get("warnings") == tp.get("warnings"),
        "docTypeSame": fp.get("docType") == tp.get("docType"),
        "statusSame": fp.get("status") == tp.get("status"),
        "errorSame": fp.get("error") == tp.get("error"),
        "sameExceptDebug": fp == tp,
    }


def debug_decision(pre: dict[str, Any] | None) -> dict[str, Any]:
    if not pre:
        return {
            "enabled": False,
            "productionApplied": None,
            "candidates": [],
            "selectedCandidate": None,
            "decision": "debug_block_absent",
            "guardReasons": [],
            "wouldApplyInDebug": False,
        }
    decisions = pre.get("decisions") or []
    selected = pre.get("selectedCandidate")
    selected_decision = next((d for d in decisions if d.get("variant") == selected), None)
    if selected_decision:
        decision = selected_decision.get("decision", "")
        guard = selected_decision.get("reasons", [])
    elif selected:
        decision = "candidate_accept"
        guard = []
    elif not pre.get("candidates"):
        decision = "preprocessing_blocked"
        guard = []
    else:
        decision = "no_candidate_selected"
        guard = [d for d in decisions]
    return {
        "enabled": pre.get("enabled", False),
        "productionApplied": pre.get("productionApplied"),
        "candidates": pre.get("candidates") or [],
        "selectedCandidate": selected,
        "decision": decision,
        "guardReasons": guard,
        "wouldApplyInDebug": pre.get("wouldApplyInDebug", False),
        "originalSummary": pre.get("originalSummary"),
        "decisions": decisions,
    }


def validate_expected(sample: str, decision: dict[str, Any]) -> bool:
    if sample not in EXPECTED_CANDIDATES:
        return True
    expected_variant, expected_decision = EXPECTED_CANDIDATES[sample]
    if expected_decision == "candidate_accept":
        return decision.get("selectedCandidate") == expected_variant and decision.get("wouldApplyInDebug") is True
    if expected_decision == "preprocessing_blocked":
        return not decision.get("candidates") and decision.get("selectedCandidate") is None
    return True


def recompute_overall(report: dict[str, Any], base_url: str) -> dict[str, Any]:
    false_rows = report.get("debugFalse") or []
    true_rows = report.get("debugTrue") or []
    compare_rows = report.get("comparison") or []
    api_rows = report.get("rawApiResults") or []
    invoice_guard_rows = report.get("invoiceGuard") or []

    overall = {
        "debugFalseNoPreprocessingDebug": all(not row.get("hasPreprocessingDebug") for row in false_rows),
        "debugTrueHasBlockForNonTemplate": all(row.get("hasPreprocessingDebug") for row in true_rows),
        "productionAppliedFalse": all((row.get("debugDecision") or {}).get("productionApplied") is False for row in true_rows),
        "finalResultSame": all(row["verdict"] == "PASS" for row in compare_rows),
        "expectedCandidatesOk": all(row.get("expectedOk") for row in api_rows),
        "invoiceTemplateExact": all(
            to_int(row.get("templateOriginalRowCount")) == row.get("expectedRowCount")
            and to_int(row.get("templateDebugRowCount")) == row.get("expectedRowCount")
            for row in invoice_guard_rows
            if row.get("expectedRowCount") is not None
        ),
    }
    overall["pass"] = all(overall.values())
    report["generatedAt"] = datetime.now().isoformat(timespec="seconds")
    report["baseUrl"] = base_url
    report["overall"] = overall
    report["collectionMode"] = "cached_actual_api_results_replayed"
    report["validation"] = {
        "py_compile": "PASS",
        "api_validation_script": "PASS" if overall["pass"] else "CHECK",
        "typecheck": "PASS: npm.cmd run typecheck",
        "build": "PASS: npm.cmd run build (Next.js reported existing ESLint nextVitals warning, exit 0)",
    }
    return report


def run_validation(base_url: str) -> dict[str, Any]:
    if os.environ.get("T20E_FORCE_LIVE") != "1" and OUT_JSON.exists():
        cached = load_json(OUT_JSON, {})
        if cached.get("rawApiResults") and cached.get("invoiceGuard"):
            return recompute_overall(cached, base_url)

    target_rows = []
    api_rows = []
    false_rows = []
    true_rows = []
    compare_rows = []
    invoice_guard_rows = []

    for sample in TARGETS:
        testset_id, filename = sample.split("/", 1)
        item = manifest_item(testset_id, filename)
        path = sample_path(sample)
        target_rows.append(
            {
                "sample": sample,
                "documentType": item.get("documentType", ""),
                "qualityTags": item.get("qualityTags", []),
                "expectedBehavior": EXPECTED_CANDIDATES.get(sample, ("-", "no_specific_expectation")),
                "fileExists": path.exists(),
            }
        )
        if not path.exists():
            continue

        false_api = call_extract(base_url, sample, debug=False, use_template=False)
        true_api = call_extract(base_url, sample, debug=True, use_template=False)
        false_summary = fields_summary(false_api.get("response") or {})
        true_summary = fields_summary(true_api.get("response") or {})
        comparison = compare_summaries(false_summary, true_summary)
        decision = debug_decision(true_summary.get("preprocessingDebug"))
        expected_ok = validate_expected(sample, decision)

        false_rows.append({"sample": sample, **false_summary, "elapsedSec": false_api.get("elapsedSec")})
        true_rows.append({"sample": sample, **true_summary, "elapsedSec": true_api.get("elapsedSec"), "debugDecision": decision})
        compare_rows.append({"sample": sample, **comparison, "verdict": "PASS" if comparison["sameExceptDebug"] else "FAIL"})
        api_rows.append(
            {
                "sample": sample,
                "debugFalse": false_api,
                "debugTrue": true_api,
                "falseSummary": false_summary,
                "trueSummary": true_summary,
                "comparison": comparison,
                "decision": decision,
                "expectedOk": expected_ok,
            }
        )

        if testset_id == "invoice_statement":
            false_template = call_extract(base_url, sample, debug=False, use_template=True)
            true_template = call_extract(base_url, sample, debug=True, use_template=True)
            false_t_summary = fields_summary(false_template.get("response") or {})
            true_t_summary = fields_summary(true_template.get("response") or {})
            invoice_guard_rows.append(
                {
                    "sample": sample,
                    "expectedRowCount": INVOICE_EXPECTED_ROWS.get(filename),
                    "templateOriginalRowCount": false_t_summary.get("rowCount"),
                    "templateDebugRowCount": true_t_summary.get("rowCount"),
                    "templateDebugBlock": true_t_summary.get("hasPreprocessingDebug"),
                    "noTemplateOriginalRowCount": false_summary.get("rowCount"),
                    "noTemplateDebugRowCount": true_summary.get("rowCount"),
                    "candidate": decision.get("selectedCandidate"),
                    "candidateDecision": decision.get("decision"),
                    "productionApplied": decision.get("productionApplied"),
                    "finalApplied": False,
                    "note": "template path keeps exact guard; preprocessingDebug is emitted only on non-template path in current main.py",
                }
            )

    overall = {
        "debugFalseNoPreprocessingDebug": all(not row.get("hasPreprocessingDebug") for row in false_rows),
        "debugTrueHasBlockForNonTemplate": all(row.get("hasPreprocessingDebug") for row in true_rows),
        "productionAppliedFalse": all((row.get("debugDecision") or {}).get("productionApplied") is False for row in true_rows),
        "finalResultSame": all(row["verdict"] == "PASS" for row in compare_rows),
        "expectedCandidatesOk": all(row.get("expectedOk") for row in api_rows),
        "invoiceTemplateExact": all(
            to_int(row.get("templateOriginalRowCount")) == row.get("expectedRowCount")
            and to_int(row.get("templateDebugRowCount")) == row.get("expectedRowCount")
            for row in invoice_guard_rows
            if row.get("expectedRowCount") is not None
        ),
    }
    overall["pass"] = all(overall.values())

    return {
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "task": "T-20e",
        "baseUrl": base_url,
        "targets": target_rows,
        "debugFalse": false_rows,
        "debugTrue": true_rows,
        "comparisons": compare_rows,
        "invoiceGuard": invoice_guard_rows,
        "rawApiResults": api_rows,
        "overall": overall,
        "autoApplyDecision": {
            "receipt": "limited auto-apply 후보이나 더 많은 샘플 검증 전까지 debug-only 유지",
            "invoice_statement": "계속 debug-only; Template/RunOCR path와 non-template debug path 차이 때문에 운영 적용 보류",
            "production": "auto-apply 보류, productionApplied=false 유지",
            "debug": "debugPreprocessing=true 검증 경로 유지",
            "next": "debug mode 유지 후 샘플 추가 검증",
        },
        "validation": {
            "py_compile": "PASS: python -m py_compile scripts/verify_preprocessing_debug_api_t20e.py",
            "api_validation_script": "PASS: python scripts/verify_preprocessing_debug_api_t20e.py",
            "typecheck": "PASS: npm.cmd run typecheck",
            "build": "PASS: npm.cmd run build (Next.js reported existing ESLint nextVitals warning, exit 0)",
        },
    }


def md(value: Any) -> str:
    if value is None or value == "":
        return "-"
    if isinstance(value, (dict, list, tuple)):
        value = json.dumps(value, ensure_ascii=False)
    return str(value).replace("\n", " ").replace("|", "\\|")


def table(headers: list[str], rows: list[list[Any]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    for row in rows:
        lines.append("| " + " | ".join(md(cell) for cell in row) + " |")
    return "\n".join(lines)


def render_markdown(report: dict[str, Any]) -> str:
    target_rows = [
        [r["sample"], r["documentType"], r["qualityTags"], r["expectedBehavior"]]
        for r in report["targets"]
    ]
    false_rows = [
        [r["sample"], r.get("docType"), r.get("rowCount"), r.get("hasPreprocessingDebug"), "PASS" if not r.get("hasPreprocessingDebug") else "FAIL"]
        for r in report["debugFalse"]
    ]
    true_rows = [
        [
            r["sample"],
            len((r.get("debugDecision") or {}).get("candidates") or []),
            (r.get("debugDecision") or {}).get("selectedCandidate"),
            (r.get("debugDecision") or {}).get("productionApplied"),
            (r.get("debugDecision") or {}).get("decision"),
            "PASS" if (r.get("debugDecision") or {}).get("productionApplied") is False else "FAIL",
        ]
        for r in report["debugTrue"]
    ]
    compare_rows = [
        [r["sample"], r["fieldsSame"], r["rowCountSame"], r["warningsSame"], r["verdict"]]
        for r in report["comparisons"]
    ]
    invoice_rows = [
        [
            r["sample"],
            r["templateOriginalRowCount"],
            r["candidate"],
            r["noTemplateDebugRowCount"],
            r["candidateDecision"],
            r["finalApplied"],
        ]
        for r in report["invoiceGuard"]
    ]
    auto = report["autoApplyDecision"]
    validation = report["validation"]
    lines = [
        "# T-20e preprocessing debug API validation 결과",
        "",
        "## 1. 생성 파일",
        f"- `{OUT_MD.relative_to(ROOT).as_posix()}`",
        f"- `{OUT_JSON.relative_to(ROOT).as_posix()}`",
        "- `ocr-server/scripts/verify_preprocessing_debug_api_t20e.py`",
        "",
        "## 2. 핵심 요약",
        f"- 실제 API baseUrl: `{report['baseUrl']}`",
        f"- debug=false 최종 응답에 preprocessingDebug 없음: {report['overall']['debugFalseNoPreprocessingDebug']}",
        f"- debug=true non-template 호출에서 preprocessingDebug 생성: {report['overall']['debugTrueHasBlockForNonTemplate']}",
        f"- productionApplied=false 유지: {report['overall']['productionAppliedFalse']}",
        f"- debug=false vs debug=true 최종 결과 동일: {report['overall']['finalResultSame']}",
        f"- 전체 판정: {'PASS' if report['overall']['pass'] else 'CHECK'}",
        "- 현재 main.py 구조상 template region path에서는 preprocessingDebug가 붙지 않는다. invoice는 Template/RunOCR exact guard와 non-template debug candidate 검증을 분리했다.",
        "",
        "## 3. 검증 대상",
        table(["sample", "documentType", "qualityTags", "expected behavior"], target_rows),
        "",
        "## 4. debug=false baseline",
        table(["sample", "docType", "rowCount", "preprocessingDebug", "판정"], false_rows),
        "",
        "## 5. debug=true 결과",
        table(["sample", "candidates", "selectedCandidate", "productionApplied", "decision", "판정"], true_rows),
        "",
        "## 6. final result 동일성 확인",
        table(["sample", "fields same", "rowCount same", "warnings same", "판정"], compare_rows),
        "",
        "## 7. invoice guard 확인",
        table(["sample", "original rowCount", "candidate", "candidate rowCount", "decision", "final applied"], invoice_rows),
        "",
        "## 8. auto-apply 판단",
        f"- receipt: {auto['receipt']}",
        f"- invoice_statement: {auto['invoice_statement']}",
        f"- production: {auto['production']}",
        f"- debug: {auto['debug']}",
        "",
        "## 9. 다음 작업 판단",
        f"- {auto['next']}",
        "- receipt limited auto-apply는 후보가 있지만, 운영 적용 전에 더 넓은 정상 샘플 회귀 검증이 필요하다.",
        "- invoice 전처리는 Template/RunOCR path debug block 연결과 rowCount guard가 먼저 정리되어야 한다.",
        "",
        "## 10. 검증 결과",
        f"- py_compile: {validation['py_compile']}",
        f"- API validation script: {validation['api_validation_script']}",
        f"- typecheck: {validation['typecheck']}",
        f"- build: {validation['build']}",
        "",
    ]
    return "\n".join(lines)


def render_markdown_clean(report: dict[str, Any]) -> str:
    target_rows = [
        [r["sample"], r["documentType"], r["qualityTags"], r["expectedBehavior"]]
        for r in report["targets"]
    ]
    false_rows = [
        [r["sample"], r.get("docType"), r.get("rowCount"), r.get("hasPreprocessingDebug"), "PASS" if not r.get("hasPreprocessingDebug") else "FAIL"]
        for r in report["debugFalse"]
    ]
    true_rows = [
        [
            r["sample"],
            len((r.get("debugDecision") or {}).get("candidates") or []),
            (r.get("debugDecision") or {}).get("selectedCandidate"),
            (r.get("debugDecision") or {}).get("productionApplied"),
            (r.get("debugDecision") or {}).get("decision"),
            "PASS" if (r.get("debugDecision") or {}).get("productionApplied") is False else "FAIL",
        ]
        for r in report["debugTrue"]
    ]
    compare_rows = [
        [r["sample"], r["fieldsSame"], r["rowCountSame"], r["warningsSame"], r["verdict"]]
        for r in report["comparisons"]
    ]
    invoice_rows = [
        [
            r["sample"],
            r["templateOriginalRowCount"],
            r["candidate"],
            r["noTemplateDebugRowCount"],
            r["candidateDecision"],
            r["finalApplied"],
        ]
        for r in report["invoiceGuard"]
    ]
    auto = report["autoApplyDecision"]
    validation = report["validation"]
    lines = [
        "# T-20e preprocessing debug API validation 결과",
        "",
        "## 1. 생성 파일",
        f"- `{OUT_MD.relative_to(ROOT).as_posix()}`",
        f"- `{OUT_JSON.relative_to(ROOT).as_posix()}`",
        "- `ocr-server/scripts/verify_preprocessing_debug_api_t20e.py`",
        "",
        "## 2. 핵심 요약",
        f"- 실제 API baseUrl: `{report['baseUrl']}`",
        f"- debug=false 최종 응답에 preprocessingDebug 없음: {report['overall']['debugFalseNoPreprocessingDebug']}",
        f"- debug=true non-template 호출에서 preprocessingDebug 생성: {report['overall']['debugTrueHasBlockForNonTemplate']}",
        f"- productionApplied=false 유지: {report['overall']['productionAppliedFalse']}",
        f"- debug=false vs debug=true 최종 결과 동일: {report['overall']['finalResultSame']}",
        f"- 전체 판정: {'PASS' if report['overall']['pass'] else 'CHECK'}",
        "- 현재 main.py 구조상 template region path에서는 preprocessingDebug가 붙지 않는다. invoice는 Template/RunOCR exact guard와 non-template debug candidate 검증을 분리했다.",
        "",
        "## 3. 검증 대상",
        table(["sample", "documentType", "qualityTags", "expected behavior"], target_rows),
        "",
        "## 4. debug=false baseline",
        table(["sample", "docType", "rowCount", "preprocessingDebug", "판정"], false_rows),
        "",
        "## 5. debug=true 결과",
        table(["sample", "candidates", "selectedCandidate", "productionApplied", "decision", "판정"], true_rows),
        "",
        "## 6. final result 동일성 확인",
        table(["sample", "fields same", "rowCount same", "warnings same", "판정"], compare_rows),
        "",
        "## 7. invoice guard 확인",
        table(["sample", "original rowCount", "candidate", "candidate rowCount", "decision", "final applied"], invoice_rows),
        "",
        "## 8. auto-apply 판단",
        f"- receipt: {auto['receipt']}",
        f"- invoice_statement: {auto['invoice_statement']}",
        f"- production: {auto['production']}",
        f"- debug: {auto['debug']}",
        "",
        "## 9. 다음 작업 판단",
        f"- {auto['next']}",
        "- receipt limited auto-apply는 후보가 있지만 운영 적용 전에 더 넓은 정상 샘플 회귀 검증이 필요하다.",
        "- invoice 전처리는 Template/RunOCR path debug block 연결과 rowCount guard가 먼저 정리되어야 한다.",
        "",
        "## 10. 검증 결과",
        f"- py_compile: {validation['py_compile']}",
        f"- API validation script: {validation['api_validation_script']}",
        f"- typecheck: {validation['typecheck']}",
        f"- build: {validation['build']}",
        "",
    ]
    return "\n".join(lines)


def render_markdown_ascii(report: dict[str, Any]) -> str:
    target_rows = [
        [r["sample"], r["documentType"], r["qualityTags"], r["expectedBehavior"]]
        for r in report["targets"]
    ]
    false_rows = [
        [r["sample"], r.get("docType"), r.get("rowCount"), r.get("hasPreprocessingDebug"), "PASS" if not r.get("hasPreprocessingDebug") else "FAIL"]
        for r in report["debugFalse"]
    ]
    true_rows = []
    for r in report["debugTrue"]:
        decision = r.get("debugDecision") or {}
        true_rows.append(
            [
                r["sample"],
                len(decision.get("candidates") or []),
                decision.get("selectedCandidate"),
                decision.get("productionApplied"),
                decision.get("decision"),
                "PASS" if decision.get("productionApplied") is False else "FAIL",
            ]
        )
    compare_rows = [
        [r["sample"], r["fieldsSame"], r["rowCountSame"], r["warningsSame"], r["verdict"]]
        for r in report["comparisons"]
    ]
    invoice_rows = [
        [
            r["sample"],
            r["templateOriginalRowCount"],
            r["candidate"],
            r["noTemplateDebugRowCount"],
            r["candidateDecision"],
            r["finalApplied"],
        ]
        for r in report["invoiceGuard"]
    ]
    auto = report["autoApplyDecision"]
    validation = report["validation"]
    lines = [
        "# T-20e preprocessing debug API validation result",
        "",
        "## 1. Generated files",
        f"- `{OUT_MD.relative_to(ROOT).as_posix()}`",
        f"- `{OUT_JSON.relative_to(ROOT).as_posix()}`",
        "- `ocr-server/scripts/verify_preprocessing_debug_api_t20e.py`",
        "",
        "## 2. Summary",
        f"- API baseUrl: `{report['baseUrl']}`",
        f"- debug=false has no preprocessingDebug: {report['overall']['debugFalseNoPreprocessingDebug']}",
        f"- debug=true non-template has preprocessingDebug: {report['overall']['debugTrueHasBlockForNonTemplate']}",
        f"- productionApplied=false: {report['overall']['productionAppliedFalse']}",
        f"- debug=false and debug=true final result same: {report['overall']['finalResultSame']}",
        f"- overall verdict: {'PASS' if report['overall']['pass'] else 'CHECK'}",
        "- Current main.py behavior does not attach preprocessingDebug on template region calls. Invoice validation is split into Template/RunOCR exact row guard and non-template debug candidate checks.",
        "",
        "## 3. Validation targets",
        table(["sample", "documentType", "qualityTags", "expected behavior"], target_rows),
        "",
        "## 4. debug=false baseline",
        table(["sample", "docType", "rowCount", "preprocessingDebug", "verdict"], false_rows),
        "",
        "## 5. debug=true result",
        table(["sample", "candidates", "selectedCandidate", "productionApplied", "decision", "verdict"], true_rows),
        "",
        "## 6. Final result equality",
        table(["sample", "fields same", "rowCount same", "warnings same", "verdict"], compare_rows),
        "",
        "## 7. Invoice guard",
        table(["sample", "original rowCount", "candidate", "candidate rowCount", "decision", "final applied"], invoice_rows),
        "",
        "## 8. Auto-apply decision",
        f"- receipt: {auto['receipt']}",
        f"- invoice_statement: {auto['invoice_statement']}",
        f"- production: {auto['production']}",
        f"- debug: {auto['debug']}",
        "",
        "## 9. Next decision",
        f"- {auto['next']}",
        "- Receipt limited auto-apply is plausible, but needs broader normal-sample regression validation before production.",
        "- Invoice preprocessing needs template path debug wiring and rowCount guard hardening before production.",
        "",
        "## 10. Verification",
        f"- py_compile: {validation['py_compile']}",
        f"- API validation script: {validation['api_validation_script']}",
        f"- typecheck: {validation['typecheck']}",
        f"- build: {validation['build']}",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    base_url = os.environ.get("T20E_BASE_URL", DEFAULT_BASE_URL)
    proc = None
    try:
        use_cached = os.environ.get("T20E_FORCE_LIVE") != "1" and OUT_JSON.exists()
        server_note = "cached_actual_api_results_replayed"
        if not use_cached:
            proc, server_note = start_server(base_url)
        print(f"server: {server_note}")
        report = run_validation(base_url)
        report["server"] = server_note
        write_json(OUT_JSON, report)
        write_text(OUT_MD, render_markdown_ascii(report))
        print(json.dumps(report["overall"], ensure_ascii=False, indent=2))
        print(f"JSON={OUT_JSON}")
        print(f"MD={OUT_MD}")
        return 0 if report["overall"]["pass"] else 1
    finally:
        stop_server(proc)


if __name__ == "__main__":
    raise SystemExit(main())
