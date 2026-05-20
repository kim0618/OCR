from __future__ import annotations

import json
import re
import subprocess
import time
from pathlib import Path
from statistics import mean
from typing import Any

import cv2
import requests


ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "ocr-server"
FRONTEND = ROOT / "mysuit-ocr"
BASELINE_DIR = FRONTEND / "public" / "data" / "testsets" / "baseline"
TEMPLATES_FILE = SERVER / "data" / "templates.json"
OUT_JSON = ROOT / "tmp" / "CODEX_RECEIPT_REOCR_GATING_DRY_RUN_AB_20260520.json"
OUT_MD = ROOT / "tmp" / "CODEX_RECEIPT_REOCR_GATING_DRY_RUN_AB_20260520.md"
API_URL = "http://127.0.0.1:9099/ocr/extract"

TARGET_NAMES = ["1.jpg", "2.jpg", "3.jpg", "4.jpg", "7.jpg", "8.jpg", "10.jpg", "a1.jpg", "a2.jpg"]
EXCLUDED = ["9.jpg"]
CORE_FIELDS = ["회사명", "사업자번호", "대표자", "tel", "주소", "총합계금액"]
UPPER_FIELDS = ["회사명", "사업자번호", "대표자", "tel", "주소"]
AMOUNT_FIELDS = ["총합계금액"]
HARD_FILES = {"a1.jpg", "a2.jpg"}


def run_text(cmd: list[str], cwd: Path = ROOT) -> str:
    try:
        p = subprocess.run(cmd, cwd=cwd, text=True, encoding="utf-8", errors="replace", capture_output=True, timeout=30)
        return (p.stdout + p.stderr).strip()
    except Exception as exc:
        return f"ERROR: {exc}"


def load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def find_template() -> dict[str, Any]:
    data = load_json(TEMPLATES_FILE, [])
    for row in data:
        if row.get("template_id") == "TPL-003" or row.get("template_name") == "영수증":
            return row
    raise RuntimeError("TPL-003 영수증 template not found")


def image_size(path: Path) -> list[int] | None:
    img = cv2.imread(str(path))
    if img is None:
        return None
    h, w = img.shape[:2]
    return [w, h]


def norm(v: Any) -> str:
    return re.sub(r"\s+", "", str(v or "").strip())


def response_size(obj: Any) -> int:
    return len(json.dumps(obj, ensure_ascii=False).encode("utf-8"))


def call_api(path: Path, template: dict[str, Any]) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    form = {"template_id": template.get("template_id", ""), "model_id": "paddleocr"}
    meta: dict[str, Any] = {"apiUrl": API_URL}
    start = time.perf_counter()
    try:
        with path.open("rb") as fh:
            r = requests.post(API_URL, data=form, files={"file": (path.name, fh)}, timeout=240)
        meta["wallClockSeconds"] = round(time.perf_counter() - start, 3)
        meta["statusCode"] = r.status_code
        meta["httpResponseBytes"] = len(r.content)
        r.raise_for_status()
        return r.json(), meta
    except Exception as exc:
        meta["wallClockSeconds"] = round(time.perf_counter() - start, 3)
        meta["error"] = str(exc)
        return None, meta


def field_summary(fields: dict[str, Any]) -> dict[str, Any]:
    keys = list(fields.keys())
    filled = [k for k in keys if norm(fields.get(k))]
    return {
        "fieldCount": len(keys),
        "filledCount": len(filled),
        "emptyCount": len(keys) - len(filled),
        "fillRate": round(len(filled) / len(keys), 4) if keys else 0.0,
        "coreValues": {k: fields.get(k, "") for k in CORE_FIELDS if k in fields},
    }


def detect_semantic(fields: dict[str, Any], full_text: str) -> dict[str, bool]:
    text = "\n".join([*(str(v or "") for v in fields.values()), full_text or ""])
    return {
        "merchantNameDetected": bool(norm(fields.get("회사명"))),
        "businessNoDetected": bool(re.search(r"\b\d{3}-?\d{2}-?\d{5}\b", text)),
        "phoneDetected": bool(re.search(r"(?:0\d{1,2})[-\s]?\d{3,4}[-\s]?\d{4}", text)),
        "addressDetected": bool(norm(fields.get("주소"))),
        "totalAmountDetected": bool(norm(fields.get("총합계금액"))) or bool(re.search(r"\d{1,3}(?:,\d{3})+\b", text)),
    }


def source_groups(field_sources: dict[str, Any]) -> dict[str, list[str]]:
    upper, amount, full, other = [], [], [], []
    for field, src in field_sources.items():
        s = str(src or "")
        if "upper" in s:
            upper.append(field)
        elif "amount" in s or "handwritten_total" in s:
            amount.append(field)
        elif "full" in s:
            full.append(field)
        elif s:
            other.append(field)
    return {"upper": upper, "amount": amount, "full": full, "other": other}


def analyze_response(path: Path, resp: dict[str, Any], meta: dict[str, Any]) -> dict[str, Any]:
    fields = resp.get("receipt_fields") if isinstance(resp.get("receipt_fields"), dict) else {}
    debug = resp.get("extract_debug") if isinstance(resp.get("extract_debug"), dict) else {}
    timings = debug.get("timings") if isinstance(debug.get("timings"), dict) else {}
    field_sources = debug.get("field_sources") if isinstance(debug.get("field_sources"), dict) else {}
    groups = source_groups(field_sources)
    full_ocr = float(timings.get("full_ocr_ms") or 0)
    upper_ms = float(timings.get("upper_reocr_total_ms") or 0)
    amount_ms = float(timings.get("amount_reocr_total_ms") or 0)
    hand_ms = float(timings.get("handwritten_total_reocr_total_ms") or 0)
    processing = float(resp.get("processing_time") or 0)
    re_total = upper_ms + amount_ms + hand_ms
    summary = field_summary(fields)
    sem = detect_semantic(fields, resp.get("full_text", ""))
    status = "PASS"
    if summary["fillRate"] < 0.8 or not sem["businessNoDetected"] or not sem["totalAmountDetected"]:
        status = "WARN"
    return {
        "fileName": path.name,
        "filePath": str(path),
        "imageSize": image_size(path),
        "processing_time": resp.get("processing_time"),
        "wallClockSeconds": meta.get("wallClockSeconds"),
        "responseSizeBytes": response_size(resp),
        "doc_type": resp.get("doc_type"),
        "receiptFields": fields,
        "fieldSummary": summary,
        "filledCount": summary["filledCount"],
        "emptyCount": summary["emptyCount"],
        "fillRate": summary["fillRate"],
        "semanticDetection": sem,
        "fieldSources": field_sources,
        "fieldsFromUpperBlock": groups["upper"],
        "fieldsFromAmountBlock": groups["amount"],
        "fieldsFromFullOcr": groups["full"],
        "fieldsFromOther": groups["other"],
        "reOcrCriticalFields": sorted(set(groups["upper"] + groups["amount"]).intersection(CORE_FIELDS)),
        "upperReOcrUsed": bool(timings.get("upper_reocr_ran")),
        "amountReOcrUsed": bool(timings.get("amount_reocr_ran")),
        "handwrittenReOcrUsed": bool(timings.get("handwritten_total_reocr_ran")),
        "ocrTimings": {
            "detectOrientationMs": timings.get("detect_orientation_ms"),
            "fullOcrMs": full_ocr,
            "upperReOcrMs": upper_ms,
            "amountReOcrMs": amount_ms,
            "handwrittenReOcrMs": hand_ms,
            "reOcrTotalMs": re_total,
            "reOcrSharePercent": round((re_total / (processing * 1000)) * 100, 2) if processing else 0,
        },
        "canSkipUpperSafelyByEvidence": len(groups["upper"]) == 0 and bool(timings.get("upper_reocr_ran")),
        "canSkipAmountSafelyByEvidence": len(groups["amount"]) == 0 and (bool(timings.get("amount_reocr_ran")) or bool(timings.get("handwritten_total_reocr_ran"))),
        "status": status,
    }


def loss_if_skip(item: dict[str, Any], skip_upper: bool, skip_amount: bool) -> dict[str, Any]:
    lost_fields: list[str] = []
    if skip_upper:
        lost_fields.extend([f for f in item["fieldsFromUpperBlock"] if f in CORE_FIELDS])
    if skip_amount:
        lost_fields.extend([f for f in item["fieldsFromAmountBlock"] if f in CORE_FIELDS])
    lost_fields = sorted(set(lost_fields))
    baseline_filled = item["filledCount"]
    expected_filled = max(0, baseline_filled - len([f for f in lost_fields if norm(item["receiptFields"].get(f))]))
    fill_drop = round(item["fillRate"] - (expected_filled / item["fieldSummary"]["fieldCount"] if item["fieldSummary"]["fieldCount"] else 0), 4)
    critical = sorted(set(lost_fields).intersection(["회사명", "사업자번호", "총합계금액"]))
    return {
        "lostFields": lost_fields,
        "criticalLostFields": critical,
        "fillRateDropEstimate": max(0, fill_drop),
        "hasLossRisk": bool(lost_fields),
    }


def candidate_decision(candidate: str, item: dict[str, Any]) -> tuple[bool, bool, str]:
    fields = item["receiptFields"]
    sem = item["semanticDetection"]
    upper_critical = bool(item["fieldsFromUpperBlock"])
    amount_critical = bool(item["fieldsFromAmountBlock"])
    pre_stage_unknown = True

    if candidate == "A_strict_all_core_present":
        # Cannot prove pre-reOCR all-core completeness from current response.
        if pre_stage_unknown:
            return False, False, "unknown_pre_reocr_stage"
        return False, False, "not_reached"
    if candidate == "B_business_amount_merchant_present":
        if pre_stage_unknown:
            return False, False, "unknown_pre_reocr_stage"
        return False, False, "not_reached"
    if candidate == "C_amount_only_gating":
        if item["amountReOcrUsed"] or item["handwrittenReOcrUsed"]:
            if amount_critical:
                return False, False, "keep_amount_reocr_amount_block_contributed"
            return False, True, "skip_amount_no_amount_block_contribution"
        return False, False, "amount_reocr_not_run"
    if candidate == "D_low_risk_skip_only":
        skip_upper = bool(item["upperReOcrUsed"]) and not upper_critical
        skip_amount = (bool(item["amountReOcrUsed"]) or bool(item["handwrittenReOcrUsed"])) and not amount_critical
        if skip_upper or skip_amount:
            return skip_upper, skip_amount, "skip_only_when_no_reocr_field_source_contribution"
        return False, False, "keep_reocr_field_source_contributed_or_not_run"
    if candidate == "E_quality_guarded":
        hard = item["fileName"] in HARD_FILES or item["fillRate"] < 0.9 or item["doc_type"] in {"form_or_handwritten", "unknown"}
        complete = sem["merchantNameDetected"] and sem["businessNoDetected"] and sem["phoneDetected"] and sem["addressDetected"] and sem["totalAmountDetected"]
        if hard:
            return False, False, "keep_hard_or_low_fill_sample"
        if not complete:
            return False, False, "keep_core_semantic_incomplete"
        if upper_critical or amount_critical:
            return False, False, "keep_reocr_contributed_to_final_fields"
        return bool(item["upperReOcrUsed"]), bool(item["amountReOcrUsed"] or item["handwrittenReOcrUsed"]), "skip_quality_guarded_complete_no_contribution"
    if candidate == "F_no_skip_baseline":
        return False, False, "baseline_no_skip"
    raise ValueError(candidate)


def evaluate_candidates(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    names = [
        "A_strict_all_core_present",
        "B_business_amount_merchant_present",
        "C_amount_only_gating",
        "D_low_risk_skip_only",
        "E_quality_guarded",
        "F_no_skip_baseline",
    ]
    out = []
    for name in names:
        rows = []
        total_saved_ms = 0.0
        loss_files = []
        unknown_files = []
        upper_skips = 0
        amount_skips = 0
        for item in items:
            skip_upper, skip_amount, reason = candidate_decision(name, item)
            if reason.startswith("unknown"):
                unknown_files.append(item["fileName"])
            if skip_upper:
                upper_skips += 1
                total_saved_ms += item["ocrTimings"]["upperReOcrMs"]
            if skip_amount:
                amount_skips += 1
                total_saved_ms += item["ocrTimings"]["amountReOcrMs"] + item["ocrTimings"]["handwrittenReOcrMs"]
            loss = loss_if_skip(item, skip_upper, skip_amount)
            if loss["hasLossRisk"]:
                loss_files.append({"fileName": item["fileName"], **loss})
            rows.append({
                "fileName": item["fileName"],
                "skipUpper": skip_upper,
                "skipAmount": skip_amount,
                "reason": reason,
                "savedMsEstimate": round(
                    (item["ocrTimings"]["upperReOcrMs"] if skip_upper else 0)
                    + ((item["ocrTimings"]["amountReOcrMs"] + item["ocrTimings"]["handwrittenReOcrMs"]) if skip_amount else 0),
                    1,
                ),
                **loss,
            })
        if loss_files:
            verdict = "FAIL"
        elif unknown_files and total_saved_ms > 0:
            verdict = "WARN"
        elif unknown_files:
            verdict = "WARN"
        elif total_saved_ms > 0:
            verdict = "PASS"
        else:
            verdict = "PASS_BASELINE_NO_SPEEDUP" if name == "F_no_skip_baseline" else "WARN_NO_SAFE_SPEEDUP"
        out.append({
            "candidate": name,
            "upperSkipFileCount": upper_skips,
            "amountSkipFileCount": amount_skips,
            "estimatedSavedSeconds": round(total_saved_ms / 1000, 3),
            "estimatedAverageSavedSeconds": round((total_saved_ms / 1000) / len(items), 3) if items else 0,
            "lossFiles": loss_files,
            "unknownFiles": unknown_files,
            "verdict": verdict,
            "rows": rows,
        })
    return out


def static_analysis() -> dict[str, Any]:
    return {
        "preReOcrDataAvailability": "Current response exposes final receipt_fields and field_sources, but not fullOcrOnlyFields/pre-reOCR receipt_fields; therefore candidates depending on pre-reOCR completeness cannot be PASS-confirmed.",
        "upperCondition": "main.py upper_ready skips upper re-OCR only when pre_fields already has businessNo/company/representative/tel/address, but those pre_fields are not returned in response.",
        "amountCondition": "main.py pre_amount_strong can skip amount re-OCR; response has final total_amount debug and field_sources, but not a complete candidate-level before/after diff.",
        "outputFieldsIndependence": "Dry-run candidates use semantic fields in receipt_fields/field_sources, not no_1~no_6 or outputFields UI keys.",
        "rgEvidence": {
            "main": run_text(["rg", "-n", "upper_ready|pre_amount_strong|pre_fields|field_sources|upper_reocr|amount_reocr|handwritten_total", "ocr-server/main.py"]),
            "frontend": run_text(["rg", "-n", "mode !== \"unstructured\"|receipt_fields|outputFields|autofill", "mysuit-ocr/src/components/upload/UploadWorkspace.tsx"]),
        },
    }


def instrumentation_needed() -> list[str]:
    return [
        "fullOcrOnlyFields: fields extracted before upper/amount/handwritten re-OCR",
        "preReOcrSemanticCompleteness: merchant/business/rep/tel/address/total booleans before re-OCR",
        "upperBlockRecoveredFields: exact diff between pre_fields and final fields",
        "amountBlockRecoveredFields: exact diff and selected total candidate before/after amount re-OCR",
        "reOcrDecisionTrace: wouldSkipUpperReOcr, wouldSkipAmountReOcr, skipReason, keepReason",
        "qualityTags: small_text/blur/shadow/handwritten-like flags used as gating guards",
    ]


def main() -> None:
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    git_status = run_text(["git", "status", "--short"])
    template = find_template()
    items: list[dict[str, Any]] = []
    for name in TARGET_NAMES:
        path = BASELINE_DIR / name
        resp, meta = call_api(path, template)
        if resp is None:
            items.append({"fileName": name, "error": meta.get("error"), "wallClockSeconds": meta.get("wallClockSeconds")})
        else:
            items.append(analyze_response(path, resp, meta))
        partial = {"partial": True, "generatedAt": time.strftime("%Y-%m-%d %H:%M:%S"), "items": items}
        (OUT_JSON.parent / "CODEX_RECEIPT_REOCR_GATING_DRY_RUN_AB_20260520.partial.json").write_text(
            json.dumps(partial, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    ok_items = [x for x in items if not x.get("error")]
    candidates = evaluate_candidates(ok_items)
    safe_speed_candidates = [c for c in candidates if c["verdict"] == "PASS" and c["estimatedSavedSeconds"] > 0]
    best_safe = max(safe_speed_candidates, key=lambda c: c["estimatedSavedSeconds"], default=None)
    most_effective = max(candidates, key=lambda c: c["estimatedSavedSeconds"], default=None)
    conclusion = (
        "safe_pass_candidate_exists"
        if best_safe
        else "warn_only_need_instrumentation"
    )
    report = {
        "tool": "Codex",
        "model": "Codex",
        "operationCodeModified": False,
        "repoDirtyBeforeWork": bool(git_status.strip()),
        "gitStatusShort": git_status,
        "script": str(Path(__file__).resolve()),
        "apiUrl": API_URL,
        "template": {
            "templateName": template.get("template_name"),
            "templateId": template.get("template_id"),
            "regionsCount": len(template.get("regions") or []),
            "modeInferred": "unstructured",
        },
        "targetFiles": TARGET_NAMES,
        "excludedFiles": EXCLUDED,
        "staticAnalysis": static_analysis(),
        "baseline": {
            "items": items,
            "avgProcessingSeconds": round(mean(float(x.get("processing_time") or 0) for x in ok_items), 3) if ok_items else None,
            "avgWallClockSeconds": round(mean(float(x.get("wallClockSeconds") or 0) for x in ok_items), 3) if ok_items else None,
            "avgFillRate": round(mean(float(x.get("fillRate") or 0) for x in ok_items), 4) if ok_items else None,
            "upperReOcrFiles": [x["fileName"] for x in ok_items if x["upperReOcrUsed"]],
            "amountReOcrFiles": [x["fileName"] for x in ok_items if x["amountReOcrUsed"]],
            "handwrittenReOcrFiles": [x["fileName"] for x in ok_items if x["handwrittenReOcrUsed"]],
        },
        "reOcrContribution": [
            {
                "fileName": x["fileName"],
                "upperReOcrUsed": x["upperReOcrUsed"],
                "amountReOcrUsed": x["amountReOcrUsed"],
                "handwrittenReOcrUsed": x["handwrittenReOcrUsed"],
                "fieldsFromUpperBlock": x["fieldsFromUpperBlock"],
                "fieldsFromAmountBlock": x["fieldsFromAmountBlock"],
                "fieldsFromFullOcr": x["fieldsFromFullOcr"],
                "reOcrCriticalFields": x["reOcrCriticalFields"],
                "canSkipUpperSafelyByEvidence": x["canSkipUpperSafelyByEvidence"],
                "canSkipAmountSafelyByEvidence": x["canSkipAmountSafelyByEvidence"],
                "timings": x["ocrTimings"],
            }
            for x in ok_items
        ],
        "candidateResults": candidates,
        "instrumentationNeeded": instrumentation_needed(),
        "futureInfoTablesCompatibility": {
            "semanticCompletenessCandidates": "compatible with future info/tables because they operate on canonical receipt fields, not outputFields/no_1~no_6.",
            "noShortcutPolicy": "no_1~no_6 or current outputFields-specific shortcuts remain excluded.",
        },
        "finalRecommendation": {
            "conclusion": conclusion,
            "safePassCandidate": best_safe["candidate"] if best_safe else None,
            "mostEffectiveCandidateByEstimatedTime": most_effective["candidate"] if most_effective else None,
            "mostEffectiveEstimatedSavedSeconds": most_effective["estimatedSavedSeconds"] if most_effective else 0,
            "operationalApplyNow": bool(best_safe),
            "recommendedNextStep": (
                "운영 반영 가능 후보가 있으면 해당 조건만 좁게 반영"
                if best_safe
                else "먼저 비침투 debug instrumentation을 추가한 뒤 fullOcrOnly/preReOCR diff 기반 A/B 재검증"
            ),
            "reason": "Current response lacks pre-reOCR fields; all upper re-OCR runs contributed to final fields, so skip cannot be proven safe from baseline response alone.",
        },
    }
    OUT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    OUT_MD.write_text(build_markdown(report), encoding="utf-8")


def build_markdown(report: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# CODEX_RECEIPT_REOCR_GATING_DRY_RUN_AB")
    lines.append("")
    lines.append(f"- 사용 도구: {report['tool']}")
    lines.append(f"- 사용 모델: {report['model']}")
    lines.append("- 운영 코드 수정: 없음")
    lines.append(f"- repo dirty before work: {report['repoDirtyBeforeWork']}")
    lines.append(f"- API URL: `{report['apiUrl']}`")
    lines.append(f"- 스크립트: `{report['script']}`")
    lines.append(f"- 템플릿: {report['template']['templateName']} / `{report['template']['templateId']}`")
    lines.append(f"- 제외 파일: {', '.join(report['excludedFiles'])}")
    lines.append("")
    b = report["baseline"]
    lines.append("## Baseline")
    lines.append(f"- avg processing/wall/fillRate: {b['avgProcessingSeconds']}s / {b['avgWallClockSeconds']}s / {b['avgFillRate']}")
    lines.append(f"- upper re-OCR files: {', '.join(b['upperReOcrFiles'])}")
    lines.append(f"- amount re-OCR files: {', '.join(b['amountReOcrFiles']) or '-'}")
    lines.append(f"- handwritten re-OCR files: {', '.join(b['handwrittenReOcrFiles']) or '-'}")
    lines.append("")
    lines.append("## re-OCR 기여도")
    lines.append("| file | processing | upper fields | amount fields | full fields | reOCR critical | reOCR ms | can skip upper | can skip amount |")
    lines.append("|---|---:|---|---|---|---|---:|:---:|:---:|")
    by_file = {x["fileName"]: x for x in report["baseline"]["items"] if not x.get("error")}
    for row in report["reOcrContribution"]:
        base = by_file[row["fileName"]]
        re_ms = row["timings"]["reOcrTotalMs"]
        lines.append(
            f"| {row['fileName']} | {base['processing_time']} | {', '.join(row['fieldsFromUpperBlock']) or '-'} | "
            f"{', '.join(row['fieldsFromAmountBlock']) or '-'} | {', '.join(row['fieldsFromFullOcr']) or '-'} | "
            f"{', '.join(row['reOcrCriticalFields']) or '-'} | {re_ms:.1f} | "
            f"{row['canSkipUpperSafelyByEvidence']} | {row['canSkipAmountSafelyByEvidence']} |"
        )
    lines.append("")
    lines.append("## 후보 A~F Dry-run")
    lines.append("| candidate | verdict | upper skips | amount skips | est saved s | unknown | loss files |")
    lines.append("|---|---|---:|---:|---:|---|---|")
    for c in report["candidateResults"]:
        lines.append(
            f"| {c['candidate']} | {c['verdict']} | {c['upperSkipFileCount']} | {c['amountSkipFileCount']} | "
            f"{c['estimatedSavedSeconds']} | {', '.join(c['unknownFiles']) or '-'} | "
            f"{', '.join(x['fileName'] for x in c['lossFiles']) or '-'} |"
        )
    lines.append("")
    lines.append("## Instrumentation 필요")
    for item in report["instrumentationNeeded"]:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## 결론")
    rec = report["finalRecommendation"]
    lines.append(f"- conclusion: {rec['conclusion']}")
    lines.append(f"- operationalApplyNow: {rec['operationalApplyNow']}")
    lines.append(f"- safePassCandidate: {rec['safePassCandidate']}")
    lines.append(f"- mostEffectiveCandidateByEstimatedTime: {rec['mostEffectiveCandidateByEstimatedTime']} ({rec['mostEffectiveEstimatedSavedSeconds']}s)")
    lines.append(f"- reason: {rec['reason']}")
    lines.append(f"- next: {rec['recommendedNextStep']}")
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    main()
