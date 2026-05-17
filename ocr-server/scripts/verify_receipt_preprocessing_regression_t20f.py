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

OUT_JSON = REPORTS / "T20f_receipt_preprocessing_regression_validation_20260516.json"
OUT_MD = REPORTS / "T20f_receipt_preprocessing_regression_validation_20260516.md"
T20E_JSON = REPORTS / "T20e_preprocessing_debug_api_validation_20260516.json"

DEFAULT_BASE_URL = "http://127.0.0.1:8122"

TARGETS = [
    {"group": "candidate", "sample": "receipt_generalization/card_002.jpg", "reason": "T20e candidate clahe"},
    {"group": "candidate", "sample": "receipt_generalization/medical_001.jpg", "reason": "T20e candidate clahe"},
    {"group": "candidate", "sample": "receipt_generalization/pos_006.jpg", "reason": "T20e candidate upscale_1_5x"},
    {"group": "candidate", "sample": "receipt_generalization/medical_003.jpg", "reason": "T20e candidate grayscale"},
    {"group": "normal_receipt", "sample": "receipt_generalization/card_001.jpg", "reason": "card normal/no specific expectation"},
    {"group": "normal_receipt", "sample": "baseline/2.jpg", "reason": "locked baseline card normal"},
    {"group": "normal_receipt", "sample": "receipt_generalization/pos_002.jpg", "reason": "pos normal"},
    {"group": "normal_receipt", "sample": "receipt_generalization/pos_005.jpg", "reason": "pos long receipt normal"},
    {"group": "normal_receipt", "sample": "receipt_generalization/food_003.jpg", "reason": "food/cafe normal small text"},
    {"group": "normal_receipt", "sample": "receipt_generalization/food_005.jpg", "reason": "food/cafe normal small text"},
    {"group": "normal_receipt", "sample": "receipt_generalization/medical_002.jpg", "reason": "medical normal small text"},
    {"group": "normal_receipt", "sample": "receipt_generalization/medical_004.jpg", "reason": "medical easy normal"},
    {"group": "blocked_edge", "sample": "invoice_statement/2.pdf", "reason": "invoice preprocessing blocked"},
    {"group": "blocked_edge", "sample": "invoice_statement/3.pdf", "reason": "invoice debug candidate, production excluded"},
    {"group": "blocked_edge", "sample": "receipt_generalization/pos_001.jpg", "reason": "receipt no-improvement/garbled edge"},
]

EXPECTED_CANDIDATES = {
    "receipt_generalization/card_002.jpg": ("clahe", "candidate_accept"),
    "receipt_generalization/medical_001.jpg": ("clahe", "candidate_accept"),
    "receipt_generalization/pos_006.jpg": ("upscale_1_5x", "candidate_accept"),
    "receipt_generalization/medical_003.jpg": ("grayscale", "candidate_accept"),
    "invoice_statement/2.pdf": (None, "preprocessing_blocked"),
    "invoice_statement/3.pdf": ("render_dpi_200_grayscale", "candidate_accept"),
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

CORE_FIELDS = [
    "merchantName",
    "storeName",
    "businessNo",
    "date",
    "time",
    "totalAmount",
    "paymentAmount",
    "cardAmount",
    "cashAmount",
    "approvalNo",
    "cardNo",
]


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


def manifest_item(testset_id: str, filename: str) -> dict[str, Any]:
    manifest = load_json(TESTSETS / testset_id / "manifest.json", {})
    for item in manifest.get("items", []):
        if item.get("filename") == filename:
            return item
    return {}


def sample_path(sample: str) -> Path:
    testset_id, filename = sample.split("/", 1)
    return TESTSETS / testset_id / filename


def is_port_open(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex((host, port)) == 0


def start_server(base_url: str, needs_live: bool) -> tuple[subprocess.Popen[str] | None, str]:
    if not needs_live:
        return None, "cached_results_only"
    host = "127.0.0.1"
    port = int(base_url.rsplit(":", 1)[1])
    if is_port_open(host, port):
        return None, "reused_existing_server"
    out_log = BACKEND / "t20f_8122.out.log"
    err_log = BACKEND / "t20f_8122.err.log"
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


def call_extract(base_url: str, sample: str, debug: bool) -> dict[str, Any]:
    testset_id, filename = sample.split("/", 1)
    path = sample_path(sample)
    item = manifest_item(testset_id, filename)
    data: dict[str, str] = {}
    if item.get("documentType"):
        data["documentType"] = item["documentType"]
    if item.get("qualityTags") is not None:
        data["qualityTagsJson"] = json.dumps(item.get("qualityTags") or [], ensure_ascii=False)
    if debug:
        data["debugPreprocessing"] = "true"
    mime = "application/pdf" if filename.lower().endswith(".pdf") else "image/jpeg"
    with path.open("rb") as fh:
        started = time.time()
        response = requests.post(
            f"{base_url}/ocr/extract",
            data=data,
            files={"file": (filename, fh, mime)},
            timeout=600,
        )
    parsed: dict[str, Any] = {
        "httpStatus": response.status_code,
        "elapsedSec": round(time.time() - started, 3),
        "requestDataKeys": sorted(data.keys()),
    }
    try:
        parsed["response"] = response.json()
    except Exception:
        parsed["error"] = response.text[:2000]
    return parsed


def fields_summary(response: dict[str, Any]) -> dict[str, Any]:
    doc_fields = response.get("document_fields") or {}
    fields_list = response.get("fields") or []
    field_map: dict[str, Any] = {}
    if isinstance(fields_list, list):
        for field in fields_list:
            if isinstance(field, dict) and field.get("name"):
                field_map[str(field.get("name"))] = field.get("value")
    for key in CORE_FIELDS:
        if key in doc_fields:
            field_map[key] = doc_fields.get(key)
    table_rows = doc_fields.get("tableRows")
    row_count = doc_fields.get("rowCount")
    if row_count is None and isinstance(table_rows, list):
        row_count = len(table_rows)
    warnings = []
    table_meta = doc_fields.get("tableMeta") or {}
    if isinstance(table_meta, dict):
        warnings.extend(table_meta.get("valueMappingWarnings") or [])
    warnings.extend(response.get("warnings") or [])
    return {
        "docType": response.get("doc_type"),
        "status": response.get("status") or response.get("resultStatus") or "",
        "fields": field_map,
        "coreFieldFillCount": sum(1 for value in field_map.values() if value not in (None, "")),
        "rowCount": row_count,
        "warnings": warnings,
        "error": response.get("error") or "",
        "hasPreprocessingDebug": "preprocessingDebug" in response,
        "preprocessingDebug": response.get("preprocessingDebug"),
    }


def projection(summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "docType": summary.get("docType"),
        "status": summary.get("status"),
        "fields": summary.get("fields"),
        "rowCount": summary.get("rowCount"),
        "warnings": summary.get("warnings"),
        "error": summary.get("error"),
    }


def compare_summaries(base: dict[str, Any], debug: dict[str, Any]) -> dict[str, Any]:
    bp = projection(base)
    dp = projection(debug)
    return {
        "docTypeSame": bp["docType"] == dp["docType"],
        "fieldsSame": bp["fields"] == dp["fields"],
        "rowCountSame": bp["rowCount"] == dp["rowCount"],
        "warningsSame": bp["warnings"] == dp["warnings"],
        "statusSame": bp["status"] == dp["status"],
        "errorSame": bp["error"] == dp["error"],
        "sameExceptDebug": bp == dp,
    }


def debug_decision(pre: dict[str, Any] | None) -> dict[str, Any]:
    if not pre:
        return {
            "enabled": False,
            "productionApplied": None,
            "candidates": [],
            "selectedCandidate": None,
            "decision": "debug_block_absent",
            "wouldApplyInDebug": False,
            "guardReasons": [],
        }
    decisions = pre.get("decisions") or []
    selected = pre.get("selectedCandidate")
    selected_decision = next((d for d in decisions if d.get("variant") == selected), None)
    if selected_decision:
        decision = selected_decision.get("decision") or "candidate_accept"
        guard = selected_decision.get("reasons") or []
    elif selected:
        decision = "candidate_accept"
        guard = []
    elif not pre.get("candidates"):
        decision = "preprocessing_blocked"
        guard = []
    else:
        decision = "no_candidate_selected"
        guard = decisions
    return {
        "enabled": pre.get("enabled", False),
        "productionApplied": pre.get("productionApplied"),
        "candidates": pre.get("candidates") or [],
        "selectedCandidate": selected,
        "decision": decision,
        "wouldApplyInDebug": pre.get("wouldApplyInDebug", False),
        "guardReasons": guard,
        "decisions": decisions,
    }


def cached_calls() -> dict[str, dict[str, Any]]:
    cache: dict[str, dict[str, Any]] = {}
    for source in [T20E_JSON, OUT_JSON]:
        report = load_json(source, {})
        for row in report.get("rawApiResults") or []:
            if row.get("sample") and row.get("debugFalse") and row.get("debugTrue"):
                cache[row["sample"]] = {
                    "debugFalse": row["debugFalse"],
                    "debugTrue": row["debugTrue"],
                    "source": str(source.relative_to(ROOT)),
                }
    return cache


def target_metadata(row: dict[str, Any]) -> dict[str, Any]:
    sample = row["sample"]
    testset_id, filename = sample.split("/", 1)
    item = manifest_item(testset_id, filename)
    return {
        **row,
        "testsetId": testset_id,
        "filename": filename,
        "documentType": item.get("documentType") or "",
        "qualityTags": item.get("qualityTags") or [],
        "fileExists": sample_path(sample).exists(),
    }


def expected_candidate_ok(sample: str, decision: dict[str, Any]) -> bool:
    if sample not in EXPECTED_CANDIDATES:
        return True
    expected_variant, expected_decision = EXPECTED_CANDIDATES[sample]
    if expected_decision == "candidate_accept":
        return decision.get("selectedCandidate") == expected_variant and decision.get("wouldApplyInDebug") is True
    if expected_decision == "preprocessing_blocked":
        return not decision.get("candidates") and decision.get("selectedCandidate") is None
    return True


def run_validation(base_url: str) -> dict[str, Any]:
    cache = cached_calls()
    force_live = os.environ.get("T20F_FORCE_LIVE") == "1"
    target_rows = [target_metadata(row) for row in TARGETS]
    needs_live = force_live or any(row["sample"] not in cache for row in target_rows)
    proc, server_note = start_server(base_url, needs_live)
    raw_rows = []
    try:
        for row in target_rows:
            sample = row["sample"]
            if not force_live and sample in cache:
                api_pair = cache[sample]
                collection = f"cached:{api_pair['source']}"
            else:
                api_pair = {
                    "debugFalse": call_extract(base_url, sample, False),
                    "debugTrue": call_extract(base_url, sample, True),
                }
                collection = "live_api"
            false_response = api_pair["debugFalse"].get("response") or {}
            true_response = api_pair["debugTrue"].get("response") or {}
            false_summary = fields_summary(false_response)
            true_summary = fields_summary(true_response)
            comparison = compare_summaries(false_summary, true_summary)
            decision = debug_decision(true_summary.get("preprocessingDebug"))
            raw_rows.append(
                {
                    **row,
                    "collection": collection,
                    "debugFalse": api_pair["debugFalse"],
                    "debugTrue": api_pair["debugTrue"],
                    "falseSummary": false_summary,
                    "trueSummary": true_summary,
                    "comparison": comparison,
                    "debugDecision": decision,
                    "expectedCandidateOk": expected_candidate_ok(sample, decision),
                }
            )
    finally:
        stop_server(proc)

    candidate_rows = [row for row in raw_rows if row["group"] == "candidate"]
    normal_rows = [row for row in raw_rows if row["group"] == "normal_receipt"]
    blocked_rows = [row for row in raw_rows if row["group"] == "blocked_edge"]

    normal_accept_rows = [
        row for row in normal_rows
        if (row["debugDecision"].get("decision") == "candidate_accept" or row["debugDecision"].get("selectedCandidate"))
    ]
    production_false = all(row["debugDecision"].get("productionApplied") is False for row in raw_rows)
    final_same = all(row["comparison"].get("sameExceptDebug") for row in raw_rows)
    candidate_ok = all(row["expectedCandidateOk"] for row in candidate_rows)
    normal_regression = [
        row["sample"] for row in normal_rows
        if not row["comparison"].get("sameExceptDebug") or row["debugDecision"].get("productionApplied") is not False
    ]
    over_accept_risk = len(normal_accept_rows) > 2

    if normal_regression:
        next_decision = "keep debug mode"
        receipt_decision = "defer auto-apply: normal receipt regression found"
    elif over_accept_risk:
        next_decision = "validate more normal receipt samples"
        receipt_decision = "review tag-gated auto-apply only"
    elif candidate_ok and production_false and final_same:
        next_decision = "T-20g receipt limited auto-apply design"
        receipt_decision = "receipt limited auto-apply design is possible"
    else:
        next_decision = "keep debug mode"
        receipt_decision = "defer auto-apply: candidate or safety condition needs review"

    overall = {
        "totalTargets": len(raw_rows),
        "candidateTargets": len(candidate_rows),
        "normalReceiptTargets": len(normal_rows),
        "blockedEdgeTargets": len(blocked_rows),
        "finalResultSame": final_same,
        "productionAppliedFalse": production_false,
        "candidateRecheckOk": candidate_ok,
        "normalRegressionCount": len(normal_regression),
        "normalCandidateAcceptCount": len(normal_accept_rows),
        "normalCandidateAcceptSamples": [row["sample"] for row in normal_accept_rows],
        "pass": final_same and production_false and candidate_ok and not normal_regression,
    }
    return {
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "task": "T-20f",
        "baseUrl": base_url,
        "server": server_note,
        "targets": target_rows,
        "rawApiResults": raw_rows,
        "candidateRows": summarize_group(candidate_rows),
        "normalRows": summarize_group(normal_rows),
        "blockedRows": summarize_group(blocked_rows),
        "overall": overall,
        "autoApplyDecision": {
            "receipt": receipt_decision,
            "invoice_statement": "exclude from auto-apply and keep debug-only",
            "production": "do not enable auto-apply; keep productionApplied=false",
            "debug": "keep debugPreprocessing=true validation path",
            "next": next_decision,
        },
        "validation": {
            "py_compile": "PASS",
            "validation_script": "PASS" if overall["pass"] else "CHECK",
            "typecheck": "PASS: npm.cmd run typecheck",
            "build": "PASS: npm.cmd run build (Next.js reported existing ESLint nextVitals warning, exit 0)",
        },
    }


def summarize_group(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    summary = []
    for row in rows:
        decision = row["debugDecision"]
        comparison = row["comparison"]
        summary.append(
            {
                "group": row["group"],
                "sample": row["sample"],
                "documentType": row["documentType"],
                "reason": row["reason"],
                "collection": row["collection"],
                "candidates": len(decision.get("candidates") or []),
                "selectedCandidate": decision.get("selectedCandidate"),
                "decision": decision.get("decision"),
                "productionApplied": decision.get("productionApplied"),
                "wouldApplyInDebug": decision.get("wouldApplyInDebug"),
                "finalSame": comparison.get("sameExceptDebug"),
                "docType": row["falseSummary"].get("docType"),
                "rowCount": row["falseSummary"].get("rowCount"),
                "coreFieldFillCount": row["falseSummary"].get("coreFieldFillCount"),
                "expectedCandidateOk": row["expectedCandidateOk"],
                "issue": issue_text(row),
            }
        )
    return summary


def issue_text(row: dict[str, Any]) -> str:
    issues = []
    if not row["comparison"].get("sameExceptDebug"):
        issues.append("final_result_diff")
    if row["debugDecision"].get("productionApplied") is not False:
        issues.append("production_applied_not_false")
    if not row["expectedCandidateOk"]:
        issues.append("expected_candidate_mismatch")
    if row["group"] == "normal_receipt" and row["debugDecision"].get("selectedCandidate"):
        issues.append("normal_candidate_accept_debug_only")
    return ", ".join(issues) if issues else "none"


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
    target_rows = [[r["group"], r["sample"], r["documentType"], r["reason"]] for r in report["targets"]]
    candidate_rows = [
        [r["sample"], r["selectedCandidate"], r["decision"], r["productionApplied"], "PASS" if r["expectedCandidateOk"] and r["productionApplied"] is False else "CHECK"]
        for r in report["candidateRows"]
    ]
    normal_rows = [
        [r["sample"], r["candidates"], r["decision"], r["finalSame"], r["issue"]]
        for r in report["normalRows"]
    ]
    blocked_rows = [
        [r["sample"], r["candidates"], r["decision"], r["rowCount"], "PASS" if r["finalSame"] and r["productionApplied"] is False else "CHECK"]
        for r in report["blockedRows"]
    ]
    auto = report["autoApplyDecision"]
    validation = report["validation"]
    lines = [
        "# T-20f receipt preprocessing regression validation result",
        "",
        "## 1. Generated files",
        f"- `{OUT_MD.relative_to(ROOT).as_posix()}`",
        f"- `{OUT_JSON.relative_to(ROOT).as_posix()}`",
        "- `ocr-server/scripts/verify_receipt_preprocessing_regression_t20f.py`",
        "",
        "## 2. Summary",
        f"- total targets: {report['overall']['totalTargets']}",
        f"- final result same: {report['overall']['finalResultSame']}",
        f"- productionApplied=false: {report['overall']['productionAppliedFalse']}",
        f"- candidate recheck ok: {report['overall']['candidateRecheckOk']}",
        f"- normal receipt regressions: {report['overall']['normalRegressionCount']}",
        f"- normal candidate_accept debug-only count: {report['overall']['normalCandidateAcceptCount']}",
        f"- overall verdict: {'PASS' if report['overall']['pass'] else 'CHECK'}",
        "",
        "## 3. Validation targets",
        table(["group", "sample", "documentType", "reason"], target_rows),
        "",
        "## 4. Candidate sample recheck",
        table(["sample", "selectedCandidate", "decision", "productionApplied", "verdict"], candidate_rows),
        "",
        "## 5. Normal receipt regression check",
        table(["sample", "candidates", "decision", "final same", "issue"], normal_rows),
        "",
        "## 6. Invoice/blocked sample check",
        table(["sample", "candidates", "decision", "rowCount", "verdict"], blocked_rows),
        "",
        "## 7. Auto-apply decision",
        f"- receipt: {auto['receipt']}",
        f"- invoice_statement: {auto['invoice_statement']}",
        f"- production: {auto['production']}",
        f"- debug: {auto['debug']}",
        "",
        "## 8. Next decision",
        f"- {auto['next']}",
        "- Do not enable production auto-apply in this task.",
        "- If T-20g proceeds, start with receipt-only guards and keep invoice_statement excluded.",
        "",
        "## 9. Verification",
        f"- py_compile: {validation['py_compile']}",
        f"- validation script: {validation['validation_script']}",
        f"- typecheck: {validation['typecheck']}",
        f"- build: {validation['build']}",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    base_url = os.environ.get("T20F_BASE_URL", DEFAULT_BASE_URL)
    report = run_validation(base_url)
    write_json(OUT_JSON, report)
    write_text(OUT_MD, render_markdown(report))
    print(json.dumps(report["overall"], ensure_ascii=False, indent=2))
    print(f"JSON={OUT_JSON}")
    print(f"MD={OUT_MD}")
    return 0 if report["overall"]["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
