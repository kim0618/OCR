from __future__ import annotations

import hashlib
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
GT_FILE = BASELINE_DIR / "ground_truth.json"
OUT_JSON = ROOT / "tmp" / "CODEX_RECEIPT_UNSTRUCTURED_TEMPLATE_SPEED_PRECHECK_20260520.json"
OUT_MD = ROOT / "tmp" / "CODEX_RECEIPT_UNSTRUCTURED_TEMPLATE_SPEED_PRECHECK_20260520.md"
API_URL = "http://127.0.0.1:9099/ocr/extract"

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".pdf"}
EXCLUDE_FILES = {"9.jpg"}
REQUIRED_FIELD_HINTS = {
    "merchantName": ["회사", "상호", "가맹", "업체"],
    "businessNo": ["사업자"],
    "representative": ["대표"],
    "phone": ["전화", "tel", "TEL", "Tel"],
    "address": ["주소"],
    "totalAmount": ["총", "합계", "금액", "amount"],
}


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


def find_receipt_template() -> dict[str, Any]:
    data = load_json(TEMPLATES_FILE, [])
    for item in data:
        if item.get("template_name") == "영수증":
            return item
        tj = item.get("template_json") if isinstance(item.get("template_json"), dict) else {}
        if tj.get("templateName") == "영수증":
            return item
    for item in data:
        if item.get("template_id") == "TPL-003":
            return item
    raise RuntimeError("receipt template not found")


def target_files() -> list[Path]:
    return sorted(
        [
            p for p in BASELINE_DIR.iterdir()
            if p.is_file() and p.suffix.lower() in IMAGE_EXTS and p.name not in EXCLUDE_FILES
        ],
        key=lambda p: (re.sub(r"\d+", lambda m: f"{int(m.group()):08d}", p.stem), p.suffix),
    )


def image_size(path: Path) -> list[int] | None:
    if path.suffix.lower() == ".pdf":
        return None
    img = cv2.imread(str(path))
    if img is None:
        return None
    h, w = img.shape[:2]
    return [w, h]


def response_size_bytes(obj: Any) -> int:
    return len(json.dumps(obj, ensure_ascii=False).encode("utf-8"))


def slim_response(resp: dict[str, Any]) -> dict[str, Any]:
    out = {
        k: v for k, v in resp.items()
        if k not in {"processed_image", "original_image", "extract_debug", "full_text", "preprocessingDebug"}
    }
    return out


def clean_json_estimate(resp: dict[str, Any], template_name: str) -> dict[str, Any]:
    fields = resp.get("receipt_fields") or {}
    info = [{"key": str(k), "label": str(k), "value": "" if v is None else str(v)} for k, v in fields.items()]
    return {"templateName": template_name, "info": info, "tables": []}


def normalize_value(v: Any) -> str:
    return re.sub(r"\s+", "", str(v or "").strip())


def values_text(fields: dict[str, Any], full_text: str = "") -> str:
    return "\n".join([*(str(v or "") for v in fields.values()), full_text or ""])


def detect_semantics(fields: dict[str, Any], full_text: str = "") -> dict[str, bool]:
    text = values_text(fields, full_text)
    return {
        "businessNoDetected": bool(re.search(r"\b\d{3}-?\d{2}-?\d{5}\b", text)),
        "totalAmountDetected": bool(re.search(r"\d{1,3}(?:,\d{3})+\b", text)),
        "merchantNameDetected": any(bool(normalize_value(v)) and not re.fullmatch(r"[\d,\-\s]+", str(v)) for v in fields.values()),
        "phoneDetected": bool(re.search(r"(?:0\d{1,2})[-\s]?\d{3,4}[-\s]?\d{4}", text)),
        "addressDetected": any(any(token in str(v) for token in ("시", "군", "구", "로", "길", "동")) for v in fields.values()),
    }


def compare_ground_truth(file_name: str, resp_fields: dict[str, Any], gt: dict[str, Any]) -> dict[str, Any]:
    gt_fields = ((gt.get(file_name) or {}).get("fields") or {})
    comparisons = []
    exact = 0
    nonempty_expected = 0
    filled_expected = 0
    for key, expected in gt_fields.items():
        exp = normalize_value(expected)
        if exp:
            nonempty_expected += 1
        actual = resp_fields.get(key, "")
        act = normalize_value(actual)
        if exp and act:
            filled_expected += 1
        is_exact = bool(exp and act and exp == act)
        is_contained = bool(exp and act and (exp in act or act in exp))
        if is_exact:
            exact += 1
        comparisons.append({
            "key": key,
            "expected": expected,
            "actual": actual,
            "expectedNonEmpty": bool(exp),
            "actualFilled": bool(act),
            "exact": is_exact,
            "contained": is_contained,
        })
    return {
        "gtFieldCount": len(gt_fields),
        "gtNonEmptyExpectedCount": nonempty_expected,
        "gtFilledExpectedCount": filled_expected,
        "gtExpectedFillRate": round(filled_expected / nonempty_expected, 4) if nonempty_expected else None,
        "gtExactMatchCount": exact,
        "gtExactMatchRate": round(exact / nonempty_expected, 4) if nonempty_expected else None,
        "comparisons": comparisons,
    }


def summarize_fields(resp_fields: dict[str, Any]) -> dict[str, Any]:
    keys = list(resp_fields.keys())
    filled = {k: v for k, v in resp_fields.items() if normalize_value(v)}
    return {
        "fieldKeys": keys,
        "fieldCount": len(keys),
        "filledCount": len(filled),
        "emptyCount": len(keys) - len(filled),
        "fillRate": round(len(filled) / len(keys), 4) if keys else 0.0,
        "raw": resp_fields,
    }


def call_api(path: Path, template: dict[str, Any]) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    form = {
        "template_id": template.get("template_id", ""),
        "model_id": "paddleocr",
    }
    meta: dict[str, Any] = {"apiUrl": API_URL}
    start = time.perf_counter()
    try:
        with path.open("rb") as fh:
            res = requests.post(API_URL, data=form, files={"file": (path.name, fh)}, timeout=240)
        meta["wallClockSeconds"] = round(time.perf_counter() - start, 3)
        meta["statusCode"] = res.status_code
        meta["responseSizeBytesHttp"] = len(res.content)
        res.raise_for_status()
        return res.json(), meta
    except Exception as exc:
        meta["wallClockSeconds"] = round(time.perf_counter() - start, 3)
        meta["error"] = str(exc)
        return None, meta


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def status_for(item: dict[str, Any]) -> str:
    if item.get("error"):
        return "FAIL"
    sem = item.get("semanticDetection") or {}
    if item.get("fillRate", 0) < 0.5:
        return "WARN"
    if not sem.get("businessNoDetected") or not sem.get("totalAmountDetected"):
        return "WARN"
    return "PASS"


def static_analysis() -> dict[str, Any]:
    return {
        "runOcrPayload": "UploadWorkspace uses activeTemplate.mode === 'unstructured' to avoid sending regions; it sends file, template_id, model_id, and optional documentType only.",
        "backendRoute": "ocr-server/main.py /ocr/extract loads template metadata, but because TPL-003 has no regions/template_json regions, region_list stays empty and the non-template full OCR path runs.",
        "ocrCalls": "Unstructured receipt path performs detect_document, detect_orientation OCR/classification, one full OCR on resized/preprocessed ocr_img, then conditional upper/amount/handwritten re-OCR crops.",
        "preprocessing": "Path deskews for preview, resizes OCR input to width 950 unless already between 760 and 950, then applies CLAHE and unsharp mask.",
        "responsePayload": "Default unstructured response includes processed_image, original_image, full_text, fields, receipt_fields, extract_debug with timings, and doc_type.",
        "fieldCrop": "The unstructured '영수증' template does not send region_list, so template field crop OCR is not used. Output fields are frontend mapping from receipt_fields.",
        "autofill": "Backend API does not run frontend autofill. UploadWorkspace may run frontend autofill suggestions after API response; this script measures API/OCR only.",
        "futureInfoTablesCompatibility": "The measured bottlenecks are OCR/preprocessing/conditional re-OCR and response size; they do not depend on current outputFields/no_1~no_6 UI naming.",
        "rgEvidence": {
            "mainReceiptPath": run_text(["rg", "-n", "detect_orientation|ocr_max_w|full_ocr_ms|upper_reocr|amount_reocr|handwritten_total|processed_image|original_image|extract_debug|receipt_fields", "ocr-server/main.py"]),
            "frontendPayload": run_text(["rg", "-n", "mode !== \"unstructured\"|template_id|regions|buildRunOcrResult|receipt_fields|autofill", "mysuit-ocr/src/components/upload/UploadWorkspace.tsx"]),
            "receiptHelpers": run_text(["rg", "-n", "select_best_total_amount|extract_amount|business|phone|address|regex", "ocr-server/amount_extractor.py", "ocr-server/utils/regex_patterns.py", "ocr-server/preprocess.py"]),
        },
    }


def optimization_candidates(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    timings = [r.get("timings") or {} for r in results if not r.get("error")]
    avg_full = mean([t.get("full_ocr_ms", 0) / 1000 for t in timings if isinstance(t.get("full_ocr_ms"), (int, float))]) if timings else 0
    avg_upper = mean([t.get("upper_reocr_total_ms", 0) / 1000 for t in timings if isinstance(t.get("upper_reocr_total_ms"), (int, float))]) if timings else 0
    avg_amount = mean([t.get("amount_reocr_total_ms", 0) / 1000 for t in timings if isinstance(t.get("amount_reocr_total_ms"), (int, float))]) if timings else 0
    avg_response_reduction = mean([r.get("responseSlimReductionBytes", 0) for r in results if not r.get("error")]) if results else 0
    return [
        {
            "candidate": "OCR cache for repeated RunOCR",
            "priority": 1,
            "expectedEffect": "Large on repeated runs: cache hit can skip full OCR and conditional re-OCR for identical file/template/options.",
            "measuredBasis": "All samples use deterministic file+template API path; avg processing dominated by OCR timings.",
            "accuracyRisk": "Low if cache key includes file hash, template id, OCR model version, preprocessing options, debug/autoApply flags.",
            "futureInfoTablesCompatibility": "Compatible; cache stores OCR/parser result independent of outputFields/info/tables UI.",
            "recommendation": "PASS",
            "validation": "Repeat same 9-file set twice; require identical receipt_fields, doc_type, fillRate.",
        },
        {
            "candidate": "Response slim / omit images and debug by default",
            "priority": 2,
            "expectedEffect": f"UI/transfer/render improvement; average removable payload about {round(avg_response_reduction)} bytes per response. Does not materially reduce OCR processing_time.",
            "measuredBasis": "Compared raw response size with slim response excluding processed_image/original_image/full_text/extract_debug.",
            "accuracyRisk": "Low for OCR values if debug/images remain opt-in.",
            "futureInfoTablesCompatibility": "Compatible; Clean JSON info/tables can be generated from structured fields without base64/debug.",
            "recommendation": "PASS",
            "validation": "Verify Preview image/history features with explicit includeImages/includeDebug option.",
        },
        {
            "candidate": "Conditional re-OCR gating review",
            "priority": 3,
            "expectedEffect": f"Potential when upper/amount re-OCR runs; current avg upper={avg_upper:.2f}s, amount={avg_amount:.2f}s. Optimize only if field recall is unchanged.",
            "measuredBasis": "extract_debug.timings upper_reocr_total_ms / amount_reocr_total_ms.",
            "accuracyRisk": "Medium; upper re-OCR can recover company/business/phone/address and amount re-OCR can recover totals.",
            "futureInfoTablesCompatibility": "Compatible if gating is based on semantic field confidence, not outputFields labels.",
            "recommendation": "WARN",
            "validation": "A/B with GT: no loss of company, businessNo, phone, address, totalAmount; fillRate must not decrease.",
        },
        {
            "candidate": "OCR input downscale below current 950px width",
            "priority": 4,
            "expectedEffect": f"May reduce full OCR time (avg full OCR {avg_full:.2f}s), but current path already resizes to 950px and comments note 850px caused receipt regressions.",
            "measuredBasis": "Static code: ocr_max_w=950, ocr_min_w=760, CLAHE/unsharp applied.",
            "accuracyRisk": "High for small receipt digits, business numbers, total amount.",
            "futureInfoTablesCompatibility": "Technically compatible but accuracy risk affects info/tables extraction.",
            "recommendation": "FAIL for default optimization",
            "validation": "Only revisit with tmp A/B at 900/850/800 and full GT comparison.",
        },
        {
            "candidate": "Parser regex/post-processing micro-optimization",
            "priority": 5,
            "expectedEffect": "Small; field_extract/pre_extract/classify timings are usually much smaller than OCR.",
            "measuredBasis": "timings pre_extract_ms, classify_document_ms, field_extract_ms vs full_ocr/re-OCR.",
            "accuracyRisk": "Medium if regex behavior changes.",
            "futureInfoTablesCompatibility": "Compatible but not the main bottleneck.",
            "recommendation": "WARN/low priority",
            "validation": "Profile CPU-only parser on saved OCR lines before code changes.",
        },
        {
            "candidate": "no_1~no_6/outputFields-specific shortcut",
            "priority": 99,
            "expectedEffect": "Not evaluated.",
            "measuredBasis": "Explicitly excluded by task constraints.",
            "accuracyRisk": "High coupling to current UI.",
            "futureInfoTablesCompatibility": "Conflicts with future info/tables structure.",
            "recommendation": "FAIL/exclude",
            "validation": "Do not pursue.",
        },
    ]


def main() -> None:
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    git_status = run_text(["git", "status", "--short"])
    template = find_receipt_template()
    files = target_files()
    gt = load_json(GT_FILE, {})
    static = static_analysis()

    results: list[dict[str, Any]] = []
    for path in files:
        resp, api_meta = call_api(path, template)
        item: dict[str, Any] = {
            "fileName": path.name,
            "filePath": str(path),
            "fileSizeBytes": path.stat().st_size,
            "fileSha256": sha256_file(path),
            "imageSize": image_size(path),
            "templateName": template.get("template_name"),
            "templateId": template.get("template_id"),
            "api": api_meta,
            "excluded": False,
        }
        if resp is None:
            item["error"] = api_meta.get("error")
            item["status"] = "FAIL"
            results.append(item)
            continue
        receipt_fields = resp.get("receipt_fields") if isinstance(resp.get("receipt_fields"), dict) else {}
        field_summary = summarize_fields(receipt_fields)
        timings = ((resp.get("extract_debug") or {}).get("timings") or {}) if isinstance(resp.get("extract_debug"), dict) else {}
        raw_size = response_size_bytes(resp)
        slim = slim_response(resp)
        clean = clean_json_estimate(resp, str(template.get("template_name") or ""))
        gt_cmp = compare_ground_truth(path.name, receipt_fields, gt)
        sem = detect_semantics(receipt_fields, resp.get("full_text", ""))
        item.update({
            "wallClockSeconds": api_meta.get("wallClockSeconds"),
            "processing_time": resp.get("processing_time"),
            "responseSizeBytes": raw_size,
            "slimResponseSizeBytes": response_size_bytes(slim),
            "responseSlimReductionBytes": raw_size - response_size_bytes(slim),
            "cleanJsonSizeBytes": response_size_bytes(clean),
            "doc_type": resp.get("doc_type"),
            "documentType": resp.get("documentType"),
            "rawOcrFieldCount": len(resp.get("fields") or []),
            "receiptFieldSummary": field_summary,
            "fieldCount": field_summary["fieldCount"],
            "filledCount": field_summary["filledCount"],
            "emptyCount": field_summary["emptyCount"],
            "fillRate": field_summary["fillRate"],
            "majorFields": receipt_fields,
            "semanticDetection": sem,
            "groundTruthComparison": gt_cmp,
            "debugKeys": list((resp.get("extract_debug") or {}).keys()) if isinstance(resp.get("extract_debug"), dict) else [],
            "timings": timings,
            "reocr": {
                "upperRan": timings.get("upper_reocr_ran"),
                "upperSeconds": round((timings.get("upper_reocr_total_ms") or 0) / 1000, 3) if isinstance(timings.get("upper_reocr_total_ms"), (int, float)) else None,
                "amountRan": timings.get("amount_reocr_ran"),
                "amountSeconds": round((timings.get("amount_reocr_total_ms") or 0) / 1000, 3) if isinstance(timings.get("amount_reocr_total_ms"), (int, float)) else None,
                "handwrittenTotalRan": timings.get("handwritten_total_reocr_ran"),
                "handwrittenTotalSeconds": round((timings.get("handwritten_total_reocr_total_ms") or 0) / 1000, 3) if isinstance(timings.get("handwritten_total_reocr_total_ms"), (int, float)) else None,
            },
            "autofillBackendApplied": bool((resp.get("preprocessingDebug") or {}).get("productionApplied")) if isinstance(resp.get("preprocessingDebug"), dict) else False,
        })
        item["status"] = status_for(item)
        results.append(item)
        partial = {"partial": True, "generatedAt": time.strftime("%Y-%m-%d %H:%M:%S"), "results": results}
        (OUT_JSON.parent / "CODEX_RECEIPT_UNSTRUCTURED_TEMPLATE_SPEED_PRECHECK_20260520.partial.json").write_text(
            json.dumps(partial, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    successful = [r for r in results if not r.get("error")]
    slowest = sorted(successful, key=lambda r: float(r.get("processing_time") or 0), reverse=True)
    avg_processing = round(mean([float(r.get("processing_time") or 0) for r in successful]), 3) if successful else None
    avg_wall = round(mean([float(r.get("wallClockSeconds") or 0) for r in successful]), 3) if successful else None
    avg_fill = round(mean([float(r.get("fillRate") or 0) for r in successful]), 4) if successful else None
    summary = {
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
            "fieldCount": template.get("field_count"),
            "regionsCount": len(template.get("regions") or []),
            "modeInferred": "unstructured",
        },
        "baselineDir": str(BASELINE_DIR),
        "excludedFiles": sorted(EXCLUDE_FILES),
        "targetFiles": [p.name for p in files],
        "staticAnalysis": static,
        "results": results,
        "slowestFiles": [
            {
                "fileName": r["fileName"],
                "processing_time": r.get("processing_time"),
                "wallClockSeconds": r.get("wallClockSeconds"),
                "fillRate": r.get("fillRate"),
                "doc_type": r.get("doc_type"),
            }
            for r in slowest[:5]
        ],
        "summary": {
            "fileCount": len(files),
            "successCount": len(successful),
            "errorCount": len(results) - len(successful),
            "avgProcessingSeconds": avg_processing,
            "avgWallClockSeconds": avg_wall,
            "avgFillRate": avg_fill,
            "passCount": sum(1 for r in results if r.get("status") == "PASS"),
            "warnCount": sum(1 for r in results if r.get("status") == "WARN"),
            "failCount": sum(1 for r in results if r.get("status") == "FAIL"),
            "avgResponseSizeBytes": round(mean([r.get("responseSizeBytes", 0) for r in successful])) if successful else None,
            "avgSlimResponseSizeBytes": round(mean([r.get("slimResponseSizeBytes", 0) for r in successful])) if successful else None,
            "avgCleanJsonSizeBytes": round(mean([r.get("cleanJsonSizeBytes", 0) for r in successful])) if successful else None,
        },
        "optimizationCandidates": optimization_candidates(results),
        "recommendedOrder": [
            "1. Add/validate OCR cache for repeated identical file+template+options runs.",
            "2. Add opt-in images/debug and slim default response if UI/history can request images separately.",
            "3. Investigate conditional re-OCR gating only with GT A/B; do not skip upper/amount re-OCR by default yet.",
            "4. Do not globally downscale below current 950px without separate GT PASS evidence.",
        ],
        "preApplyValidationNeeded": [
            "Run the same target set twice for cache validation; receipt_fields/doc_type/fillRate must be identical.",
            "For response slim, verify Preview image, History detail, Raw JSON/debug toggles explicitly.",
            "For any re-OCR gating change, require per-file GT comparison for company/businessNo/phone/address/totalAmount and no fillRate decrease.",
            "Keep all candidates independent of outputFields/no_1~no_6 and compatible with future info/tables Clean JSON.",
        ],
    }
    OUT_JSON.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    OUT_MD.write_text(build_markdown(summary), encoding="utf-8")


def build_markdown(report: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# CODEX_RECEIPT_UNSTRUCTURED_TEMPLATE_SPEED_PRECHECK")
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
    lines.append("## 대상 파일")
    lines.append(", ".join(report["targetFiles"]))
    lines.append("")
    lines.append("## Baseline 속도 / 인식률")
    lines.append("")
    lines.append("| file | doc_type | processing | wall | raw KB | slim KB | fillRate | biz | total | status |")
    lines.append("|---|---|---:|---:|---:|---:|---:|:---:|:---:|---|")
    for r in report["results"]:
        if r.get("error"):
            lines.append(f"| {r['fileName']} | ERROR | - | {r['api'].get('wallClockSeconds')} | - | - | - | - | - | FAIL |")
            continue
        sem = r["semanticDetection"]
        lines.append(
            f"| {r['fileName']} | {r.get('doc_type')} | {r.get('processing_time')} | {r.get('wallClockSeconds')} | "
            f"{round(r.get('responseSizeBytes', 0)/1024, 1)} | {round(r.get('slimResponseSizeBytes', 0)/1024, 1)} | "
            f"{r.get('fillRate')} | {sem.get('businessNoDetected')} | {sem.get('totalAmountDetected')} | {r.get('status')} |"
        )
    lines.append("")
    lines.append("## 느린 파일 TOP")
    for r in report["slowestFiles"]:
        lines.append(f"- {r['fileName']}: processing={r['processing_time']}s, wall={r['wallClockSeconds']}s, fillRate={r['fillRate']}, doc={r['doc_type']}")
    lines.append("")
    lines.append("## 주요 필드 결과")
    for r in report["results"]:
        if r.get("error"):
            continue
        lines.append(f"### {r['fileName']}")
        for k, v in (r.get("majorFields") or {}).items():
            lines.append(f"- {k}: {v}")
    lines.append("")
    lines.append("## 병목 / OCR 호출 구조")
    for key, value in report["staticAnalysis"].items():
        if key == "rgEvidence":
            continue
        lines.append(f"- {key}: {value}")
    lines.append("")
    lines.append("## 응답 크기")
    s = report["summary"]
    lines.append(f"- 평균 raw response: {s['avgResponseSizeBytes']} bytes")
    lines.append(f"- 평균 slim response: {s['avgSlimResponseSizeBytes']} bytes")
    lines.append(f"- 평균 Clean JSON estimate: {s['avgCleanJsonSizeBytes']} bytes")
    lines.append("- response slim은 OCR processing_time 자체보다는 전송/렌더링/Raw JSON 표시 비용에 유효.")
    lines.append("")
    lines.append("## 최적화 후보")
    for c in report["optimizationCandidates"]:
        lines.append(f"### P{c['priority']} {c['candidate']}")
        lines.append(f"- 추천: {c['recommendation']}")
        lines.append(f"- 예상 효과: {c['expectedEffect']}")
        lines.append(f"- 정확도 위험: {c['accuracyRisk']}")
        lines.append(f"- 향후 info/tables 호환성: {c['futureInfoTablesCompatibility']}")
        lines.append(f"- 검증 방법: {c['validation']}")
    lines.append("")
    lines.append("## 운영 반영 추천 순서")
    for item in report["recommendedOrder"]:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## 운영 반영 전 추가 검증")
    for item in report["preApplyValidationNeeded"]:
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    main()
