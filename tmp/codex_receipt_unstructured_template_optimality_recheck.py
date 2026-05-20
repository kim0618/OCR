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
OUT_JSON = ROOT / "tmp" / "CODEX_RECEIPT_UNSTRUCTURED_TEMPLATE_OPTIMALITY_RECHECK_20260520.json"
OUT_MD = ROOT / "tmp" / "CODEX_RECEIPT_UNSTRUCTURED_TEMPLATE_OPTIMALITY_RECHECK_20260520.md"
API_URL = "http://127.0.0.1:9099/ocr/extract"

EXCLUDE_FILES = {"9.jpg"}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".pdf"}
SEMANTIC_FIELDS = ["회사명", "사업자번호", "대표자", "tel", "주소", "총합계금액"]


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
    for item in data:
        if item.get("template_name") == "영수증" or item.get("template_id") == "TPL-003":
            return item
    raise RuntimeError("영수증 template not found")


def target_files() -> list[Path]:
    files = [
        p for p in BASELINE_DIR.iterdir()
        if p.is_file() and p.suffix.lower() in IMAGE_EXTS and p.name not in EXCLUDE_FILES
    ]
    return sorted(files, key=lambda p: (re.sub(r"\d+", lambda m: f"{int(m.group()):08d}", p.stem), p.suffix))


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def image_size(path: Path) -> list[int] | None:
    if path.suffix.lower() == ".pdf":
        return None
    img = cv2.imread(str(path))
    if img is None:
        return None
    h, w = img.shape[:2]
    return [w, h]


def norm(v: Any) -> str:
    return re.sub(r"\s+", "", str(v or "").strip())


def response_size(obj: Any) -> int:
    return len(json.dumps(obj, ensure_ascii=False).encode("utf-8"))


def slim_variants(resp: dict[str, Any]) -> dict[str, int]:
    no_images = {k: v for k, v in resp.items() if k not in {"processed_image", "original_image"}}
    no_debug = {k: v for k, v in no_images.items() if k not in {"extract_debug", "preprocessingDebug"}}
    clean = {
        "templateName": "영수증",
        "info": [
            {"key": k, "label": k, "value": "" if v is None else str(v)}
            for k, v in (resp.get("receipt_fields") or {}).items()
        ],
        "tables": [],
    }
    return {
        "raw": response_size(resp),
        "noImages": response_size(no_images),
        "noImagesNoDebug": response_size(no_debug),
        "cleanJson": response_size(clean),
    }


def dumps_time_ms(obj: Any, repeats: int = 5) -> float:
    start = time.perf_counter()
    for _ in range(repeats):
        json.dumps(obj, ensure_ascii=False)
    return round((time.perf_counter() - start) * 1000 / repeats, 3)


def semantic_detection(fields: dict[str, Any], full_text: str) -> dict[str, bool]:
    text = "\n".join([*(str(v or "") for v in fields.values()), full_text or ""])
    return {
        "businessNoDetected": bool(re.search(r"\b\d{3}-?\d{2}-?\d{5}\b", text)),
        "totalAmountDetected": bool(re.search(r"\d{1,3}(?:,\d{3})+\b", text)),
        "merchantNameDetected": bool(norm(fields.get("회사명"))) or any("상호" in k and norm(v) for k, v in fields.items()),
        "phoneDetected": bool(re.search(r"(?:0\d{1,2})[-\s]?\d{3,4}[-\s]?\d{4}", text)),
        "addressDetected": bool(norm(fields.get("주소"))),
    }


def field_summary(fields: dict[str, Any]) -> dict[str, Any]:
    keys = list(fields.keys())
    filled = [k for k in keys if norm(fields.get(k))]
    return {
        "fieldKeys": keys,
        "fieldCount": len(keys),
        "filledCount": len(filled),
        "emptyCount": len(keys) - len(filled),
        "fillRate": round(len(filled) / len(keys), 4) if keys else 0.0,
        "majorFields": {k: fields.get(k, "") for k in SEMANTIC_FIELDS if k in fields},
    }


def stable_projection(resp: dict[str, Any]) -> dict[str, Any]:
    fields = resp.get("receipt_fields") or {}
    return {
        "doc_type": resp.get("doc_type"),
        "receipt_fields": {k: fields.get(k) for k in sorted(fields)},
        "fillRate": field_summary(fields)["fillRate"],
        "semantic": semantic_detection(fields, resp.get("full_text", "")),
    }


def call_api(path: Path, template: dict[str, Any]) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    form = {"template_id": template.get("template_id", ""), "model_id": "paddleocr"}
    start = time.perf_counter()
    meta: dict[str, Any] = {"apiUrl": API_URL}
    try:
        with path.open("rb") as fh:
            res = requests.post(API_URL, data=form, files={"file": (path.name, fh)}, timeout=240)
        meta["wallClockSeconds"] = round(time.perf_counter() - start, 3)
        meta["statusCode"] = res.status_code
        meta["responseBytesHttp"] = len(res.content)
        res.raise_for_status()
        return res.json(), meta
    except Exception as exc:
        meta["wallClockSeconds"] = round(time.perf_counter() - start, 3)
        meta["error"] = str(exc)
        return None, meta


def source_fields(extract_debug: dict[str, Any]) -> dict[str, str]:
    fs = extract_debug.get("field_sources")
    return fs if isinstance(fs, dict) else {}


def reocr_recovered_fields(field_sources: dict[str, str]) -> list[dict[str, str]]:
    recovered = []
    for key, src in field_sources.items():
        s = str(src or "")
        if any(token in s for token in ["upper", "amount", "handwritten", "reocr"]):
            recovered.append({"field": key, "source": s})
    return recovered


def analyze_run(file_path: Path, resp: dict[str, Any], api_meta: dict[str, Any], round_idx: int) -> dict[str, Any]:
    fields = resp.get("receipt_fields") if isinstance(resp.get("receipt_fields"), dict) else {}
    summary = field_summary(fields)
    debug = resp.get("extract_debug") if isinstance(resp.get("extract_debug"), dict) else {}
    timings = debug.get("timings") if isinstance(debug.get("timings"), dict) else {}
    fs = source_fields(debug)
    recovered = reocr_recovered_fields(fs)
    full = float(timings.get("full_ocr_ms") or 0)
    upper = float(timings.get("upper_reocr_total_ms") or 0)
    amount = float(timings.get("amount_reocr_total_ms") or 0)
    hand = float(timings.get("handwritten_total_reocr_total_ms") or 0)
    re_total = upper + amount + hand
    processing = float(resp.get("processing_time") or 0)
    sizes = slim_variants(resp)
    sem = semantic_detection(fields, resp.get("full_text", ""))
    if summary["fillRate"] < 0.8 or not sem["businessNoDetected"] or not sem["totalAmountDetected"]:
        status = "WARN"
    else:
        status = "PASS"
    # Safe skip can only be asserted when the OCR stage did not run. If it ran,
    # response-only evidence cannot prove no regression without an A/B disable run.
    can_skip = "yes" if re_total == 0 else ("unknown" if not recovered else "no")
    return {
        "round": round_idx,
        "fileName": file_path.name,
        "filePath": str(file_path),
        "imageSize": image_size(file_path),
        "fileSizeBytes": file_path.stat().st_size,
        "fileSha256": sha256_file(file_path),
        "wallClockSeconds": api_meta.get("wallClockSeconds"),
        "processing_time": resp.get("processing_time"),
        "doc_type": resp.get("doc_type"),
        "fieldSummary": summary,
        "filledCount": summary["filledCount"],
        "emptyCount": summary["emptyCount"],
        "fillRate": summary["fillRate"],
        "majorFields": summary["majorFields"],
        "semanticDetection": sem,
        "status": status,
        "timings": timings,
        "ocrCallBreakdown": {
            "detectOrientationMs": timings.get("detect_orientation_ms"),
            "fullOcrMs": full,
            "upperReOcrMs": upper,
            "amountReOcrMs": amount,
            "handwrittenReOcrMs": hand,
            "reOcrTotalMs": re_total,
            "processingTimeMs": processing * 1000,
            "reOcrSharePercent": round((re_total / (processing * 1000)) * 100, 2) if processing > 0 else 0,
            "upperRan": timings.get("upper_reocr_ran"),
            "amountRan": timings.get("amount_reocr_ran"),
            "handwrittenRan": timings.get("handwritten_total_reocr_ran"),
        },
        "fieldSources": fs,
        "fieldsRecoveredByReOcr": recovered,
        "canSkipReOcrSafelyFromCurrentEvidence": can_skip,
        "responseSizes": sizes,
        "jsonSerializationMs": {
            "raw": dumps_time_ms(resp),
            "noImagesNoDebug": dumps_time_ms({
                k: v for k, v in resp.items()
                if k not in {"processed_image", "original_image", "extract_debug", "preprocessingDebug", "full_text"}
            }),
        },
        "stableProjection": stable_projection(resp),
    }


def static_analysis() -> dict[str, Any]:
    return {
        "unstructuredTemplatePath": "TPL-003 has no regions, so RunOCR sends template_id/model_id without regions and backend takes the non-region full OCR receipt path.",
        "ocrCallStructure": "detect_document -> detect_orientation -> OCR image resize/preprocess -> full OCR -> conditional upper re-OCR -> conditional amount re-OCR -> conditional handwritten-total re-OCR.",
        "upperReOcrCondition": "upper re-OCR runs when upper_bbox exists and pre-extract did not fill businessNo, company, representative, tel, and address. It is skipped only when upper_ready is true.",
        "amountReOcrCondition": "amount re-OCR is skipped for bank_slip/form_or_handwritten/invoice_statement or when pre_amount_strong is true; otherwise it runs if amount_bbox exists.",
        "downscaleEvidence": "main.py uses ocr_max_w=950 and comments state 850px regressed small receipt digits/separators, so lower default downscale remains unsafe without A/B GT evidence.",
        "responseSlimEvidence": "Unstructured response includes processed_image, original_image, full_text, extract_debug/timings by default; these dominate bytes but not OCR processing_time.",
        "autofillBoundary": "Frontend autofill runs after API in UploadWorkspace; this API script measures backend OCR/parser only. Cache key should not include frontend history unless caching post-autofill UI result.",
        "outputFieldsDependency": "OCR cache, response slim, and semantic re-OCR gating can be designed independently of outputFields/no_1~no_6 and future info/tables UI.",
        "rgEvidence": {
            "main": run_text(["rg", "-n", "ocr_max_w|850px|upper_ready|pre_amount_strong|upper_reocr|amount_reocr|handwritten_total|field_sources|processed_image|original_image|extract_debug", "ocr-server/main.py"]),
            "frontend": run_text(["rg", "-n", "mode !== \"unstructured\"|template_id|regions|receipt_fields|autofill|processed_image|original_image", "mysuit-ocr/src/components/upload/UploadWorkspace.tsx"]),
        },
    }


def cache_stability(round1: list[dict[str, Any]], round2: list[dict[str, Any]]) -> dict[str, Any]:
    by2 = {r["fileName"]: r for r in round2}
    rows = []
    stable_count = 0
    for r1 in round1:
        r2 = by2.get(r1["fileName"])
        if not r2:
            continue
        same = r1["stableProjection"] == r2["stableProjection"]
        if same:
            stable_count += 1
        rows.append({
            "fileName": r1["fileName"],
            "stableProjectionSame": same,
            "docType1": r1["doc_type"],
            "docType2": r2["doc_type"],
            "fillRate1": r1["fillRate"],
            "fillRate2": r2["fillRate"],
            "processing1": r1["processing_time"],
            "processing2": r2["processing_time"],
            "wall1": r1["wallClockSeconds"],
            "wall2": r2["wallClockSeconds"],
        })
    return {
        "stableCount": stable_count,
        "totalCompared": len(rows),
        "allStable": stable_count == len(rows) and len(rows) > 0,
        "rows": rows,
        "cacheKeyRecommendation": [
            "fileSha256",
            "templateId",
            "template updatedAt or template hash",
            "OCR model/version/language config",
            "preprocessing options: debugPreprocessing, autoApplyPreprocessing, qualityTagsJson",
            "documentType hint",
            "backend code/version for OCR/parser policy",
        ],
        "invalidation": [
            "file bytes changed",
            "template changed",
            "OCR model or PaddleOCR config changed",
            "preprocessing policy/options changed",
            "parser/amount/regex policy changed",
            "debug/autoApply options changed",
        ],
        "verdict": "PASS" if stable_count == len(rows) and len(rows) > 0 else "WARN",
    }


def response_slim_analysis(runs: list[dict[str, Any]]) -> dict[str, Any]:
    sizes = [r["responseSizes"] for r in runs]
    return {
        "avgRawBytes": round(mean(s["raw"] for s in sizes)),
        "avgNoImagesBytes": round(mean(s["noImages"] for s in sizes)),
        "avgNoImagesNoDebugBytes": round(mean(s["noImagesNoDebug"] for s in sizes)),
        "avgCleanJsonBytes": round(mean(s["cleanJson"] for s in sizes)),
        "avgRawSerializationMs": round(mean(r["jsonSerializationMs"]["raw"] for r in runs), 3),
        "avgSlimSerializationMs": round(mean(r["jsonSerializationMs"]["noImagesNoDebug"] for r in runs), 3),
        "effectOnProcessingTime": "Not material: processing_time is dominated by OCR/preprocessing before response serialization.",
        "effectOnWallUi": "Likely useful for transfer, browser JSON parse, Raw JSON rendering, and history storage size.",
        "previewRisk": "processed_image/original_image are used by UploadWorkspace for preview/history; slim default needs explicit includeImages or separate image path.",
        "verdict": "PASS for UI/transport optimization, not a core OCR processing_time optimization.",
    }


def reocr_analysis(round1: list[dict[str, Any]]) -> dict[str, Any]:
    rows = []
    for r in round1:
        b = r["ocrCallBreakdown"]
        recovered = r["fieldsRecoveredByReOcr"]
        rows.append({
            "fileName": r["fileName"],
            "fullOcrMs": b["fullOcrMs"],
            "upperReOcrMs": b["upperReOcrMs"],
            "amountReOcrMs": b["amountReOcrMs"],
            "handwrittenReOcrMs": b["handwrittenReOcrMs"],
            "reOcrTotalMs": b["reOcrTotalMs"],
            "processingTime": r["processing_time"],
            "reOcrSharePercent": b["reOcrSharePercent"],
            "upperRan": b["upperRan"],
            "amountRan": b["amountRan"],
            "handwrittenRan": b["handwrittenRan"],
            "fieldsRecoveredByReOcr": recovered,
            "canSkipSafely": r["canSkipReOcrSafelyFromCurrentEvidence"],
            "fillRate": r["fillRate"],
            "businessNoDetected": r["semanticDetection"]["businessNoDetected"],
            "totalAmountDetected": r["semanticDetection"]["totalAmountDetected"],
        })
    avg_re = mean(r["reOcrTotalMs"] for r in rows) if rows else 0
    return {
        "rows": rows,
        "avgReOcrMs": round(avg_re, 1),
        "upperRanFiles": [r["fileName"] for r in rows if r["upperRan"]],
        "amountRanFiles": [r["fileName"] for r in rows if r["amountRan"]],
        "handwrittenRanFiles": [r["fileName"] for r in rows if r["handwrittenRan"]],
        "whyWarn": [
            "upper re-OCR ran for all measured files; current response-only data cannot prove it can be removed without A/B disabling it.",
            "field_sources show upper_block contributions for some top fields, so unconditional skip risks company/business/phone/address recall.",
            "a1/a2 are lower-fill/edge samples; gating should remain conservative there.",
            "amount re-OCR ran only on selected files, but totalAmount recovery is a critical field; skip only when full/pre extract has strong total.",
        ],
        "safeGatingConditionsToTest": [
            "Skip upper re-OCR only if pre/full OCR already has businessNo, totalAmount, merchantName, phone, and address with high confidence.",
            "Keep upper re-OCR if businessNo, phone, address, or merchantName is blank.",
            "Keep amount re-OCR if totalAmount is blank, low-confidence, review-required, or doc_type is hard/unknown-like.",
            "Keep all re-OCR for low fillRate candidates, blurry/small-text/quality-tagged images, and a1/a2-like edge cases.",
            "Roll out behind an option and compare GT before/after; any field loss is FAIL.",
        ],
        "verdict": "WARN",
    }


def candidate_ranking(cache: dict[str, Any], slim: dict[str, Any], reocr: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "rank": 1,
            "candidate": "OCR cache",
            "verdict": cache["verdict"],
            "expectedBenefit": "Highest for repeated same file/template/options; can avoid OCR and parser work on cache hit.",
            "singleRunBenefit": "None on first run.",
            "repeatRunBenefit": "Very high.",
            "risk": "Low with complete key/invalidation.",
            "implementationScope": "Backend cache around final OCR/parser response or OCR-line artifacts.",
            "futureInfoTablesCompatibility": "Compatible and independent from outputFields/no_1~no_6.",
            "nextValidationNeeded": "Implement dry-run cache lookup/hash logging, then assert stableProjection equality on all baseline files.",
        },
        {
            "rank": 2,
            "candidate": "Response slim / opt-in images+debug",
            "verdict": "PASS",
            "expectedBenefit": "Large payload reduction and faster UI parse/render/history storage; not a core OCR time reduction.",
            "singleRunBenefit": "Moderate for wall/UI after OCR; low for backend processing_time.",
            "repeatRunBenefit": "Moderate storage/network benefit.",
            "risk": "Low if preview/history can request images/debug explicitly.",
            "implementationScope": "API response flags and frontend request behavior.",
            "futureInfoTablesCompatibility": "Compatible; clean info/tables needs structured values, not base64/debug.",
            "nextValidationNeeded": "Check Preview, Raw JSON, History detail with includeImages/includeDebug toggles.",
        },
        {
            "rank": 3,
            "candidate": "Conservative semantic upper/amount re-OCR gating",
            "verdict": reocr["verdict"],
            "expectedBenefit": "Best single-run OCR-time lever if safe; measured re-OCR share can be significant.",
            "singleRunBenefit": "Potentially high, but not yet safe.",
            "repeatRunBenefit": "Also helps uncached runs.",
            "risk": "Medium/high until A/B proves no loss of company/businessNo/phone/address/total.",
            "implementationScope": "Backend gating based on semantic completeness/confidence, not UI field names.",
            "futureInfoTablesCompatibility": "Compatible if based on semantic extracted fields.",
            "nextValidationNeeded": "A/B disable only when proposed safe conditions pass; compare GT/fillRate per file.",
        },
        {
            "rank": 4,
            "candidate": "Parser regex micro-optimization",
            "verdict": "WARN low priority",
            "expectedBenefit": "Small compared with OCR/re-OCR.",
            "singleRunBenefit": "Low.",
            "repeatRunBenefit": "Low.",
            "risk": "Medium because parser changes can alter values.",
            "implementationScope": "Parser profiling only before any edits.",
            "futureInfoTablesCompatibility": "Compatible.",
            "nextValidationNeeded": "Profile parser on saved OCR lines; do not change regex without GT pass.",
        },
        {
            "rank": 5,
            "candidate": "Downscale below current 950px",
            "verdict": "FAIL for default",
            "expectedBenefit": "Could reduce full OCR but current code already resizes to 950px.",
            "singleRunBenefit": "Possible but unsafe.",
            "repeatRunBenefit": "Possible but unsafe.",
            "risk": "High: existing code comment records 850px receipt digit/separator regression.",
            "implementationScope": "Would affect OCR input policy.",
            "futureInfoTablesCompatibility": "Technically independent but accuracy risk affects future info/tables.",
            "nextValidationNeeded": "Only revisit with separate 900/850/800 tmp A/B and strict GT pass.",
        },
        {
            "rank": 99,
            "candidate": "outputFields/no_1~no_6 shortcut",
            "verdict": "FAIL/excluded",
            "expectedBenefit": "Not considered.",
            "singleRunBenefit": "Irrelevant.",
            "repeatRunBenefit": "Irrelevant.",
            "risk": "Conflicts with future info/tables and task constraints.",
            "implementationScope": "Do not pursue.",
            "futureInfoTablesCompatibility": "Not compatible.",
            "nextValidationNeeded": "None.",
        },
    ]


def main() -> None:
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    git_status = run_text(["git", "status", "--short"])
    template = find_template()
    files = target_files()
    static = static_analysis()

    rounds: list[list[dict[str, Any]]] = []
    for round_idx in (1, 2):
        current: list[dict[str, Any]] = []
        for path in files:
            resp, meta = call_api(path, template)
            if resp is None:
                current.append({
                    "round": round_idx,
                    "fileName": path.name,
                    "filePath": str(path),
                    "error": meta.get("error"),
                    "wallClockSeconds": meta.get("wallClockSeconds"),
                    "status": "FAIL",
                })
            else:
                current.append(analyze_run(path, resp, meta, round_idx))
            partial = {
                "partial": True,
                "generatedAt": time.strftime("%Y-%m-%d %H:%M:%S"),
                "rounds": rounds + [current],
            }
            (OUT_JSON.parent / "CODEX_RECEIPT_UNSTRUCTURED_TEMPLATE_OPTIMALITY_RECHECK_20260520.partial.json").write_text(
                json.dumps(partial, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        rounds.append(current)

    r1 = [r for r in rounds[0] if not r.get("error")]
    r2 = [r for r in rounds[1] if not r.get("error")]
    cache = cache_stability(r1, r2)
    slim = response_slim_analysis(r1)
    reocr = reocr_analysis(r1)
    ranking = candidate_ranking(cache, slim, reocr)

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
            "fieldCount": template.get("field_count"),
            "regionsCount": len(template.get("regions") or []),
            "modeInferred": "unstructured",
        },
        "baselineDir": str(BASELINE_DIR),
        "excludedFiles": sorted(EXCLUDE_FILES),
        "targetFiles": [p.name for p in files],
        "staticAnalysis": static,
        "rounds": rounds,
        "baselineRecheckSummary": {
            "round1AvgProcessing": round(mean(float(r["processing_time"]) for r in r1), 3),
            "round1AvgWall": round(mean(float(r["wallClockSeconds"]) for r in r1), 3),
            "round1AvgFillRate": round(mean(float(r["fillRate"]) for r in r1), 4),
            "round2AvgProcessing": round(mean(float(r["processing_time"]) for r in r2), 3),
            "round2AvgWall": round(mean(float(r["wallClockSeconds"]) for r in r2), 3),
            "round2AvgFillRate": round(mean(float(r["fillRate"]) for r in r2), 4),
            "slowestRound1": sorted(
                [{"fileName": r["fileName"], "processing_time": r["processing_time"], "wallClockSeconds": r["wallClockSeconds"], "fillRate": r["fillRate"]} for r in r1],
                key=lambda x: float(x["processing_time"]),
                reverse=True,
            )[:5],
        },
        "reOcrAnalysis": reocr,
        "cacheStability": cache,
        "responseSlimAnalysis": slim,
        "downscaleRecheck": {
            "currentPolicy": "OCR image width is capped/upscaled to 950px with min 760px.",
            "evidence": "main.py comment says 850px caused regression on small receipt digits/separators, so 950px was restored.",
            "decision": "Do not recommend below-950 default downscale without separate strict A/B.",
            "verdict": "FAIL for default optimization",
        },
        "outputFieldsDependency": {
            "OCR cache": "independent",
            "response slim": "independent if structured receipt_fields/full_text/debug flags are handled",
            "re-OCR gating": "can be independent if based on semantic completeness/confidence",
            "downscale": "independent but accuracy-risky",
            "no_1~no_6 shortcut": "dependent and excluded",
        },
        "futureInfoTablesCompatibility": {
            "compatibleCandidates": ["OCR cache", "response slim", "semantic re-OCR gating after A/B"],
            "incompatibleCandidates": ["outputFields/no_1~no_6 shortcut"],
            "note": "Recommended candidates operate on OCR execution, response payload, or semantic fields, not on current outputFields names.",
        },
        "finalRanking": ranking,
        "conclusion": {
            "isCurrentBest": True,
            "safestCandidate": "OCR cache, followed by response slim",
            "bestSingleRunCandidate": "Conservative semantic re-OCR gating, but still WARN and requires A/B before recommendation",
            "bestRepeatedRunCandidate": "OCR cache",
            "nowRecommended": ["OCR cache dry-run/implementation", "response slim with opt-in images/debug"],
            "notRecommendedNow": ["unconditional re-OCR skip", "below-950 downscale", "outputFields/no_1~no_6 shortcuts"],
        },
        "preApplyValidationNeeded": [
            "For cache: implement lookup dry-run and confirm stableProjection equality on target set.",
            "For response slim: verify Preview image, History detail, Raw JSON/debug with explicit include flags.",
            "For re-OCR gating: run A/B disabling only under proposed safe conditions and require zero loss on semantic fields/fillRate.",
            "Do not pursue below-950 downscale unless 900/850/800 tmp experiment passes all required fields.",
        ],
    }
    OUT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    OUT_MD.write_text(build_markdown(report), encoding="utf-8")


def build_markdown(report: dict[str, Any]) -> str:
    lines = []
    lines.append("# CODEX_RECEIPT_UNSTRUCTURED_TEMPLATE_OPTIMALITY_RECHECK")
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
    s = report["baselineRecheckSummary"]
    lines.append("## Baseline 재확인")
    lines.append(f"- round1 avg processing/wall/fillRate: {s['round1AvgProcessing']}s / {s['round1AvgWall']}s / {s['round1AvgFillRate']}")
    lines.append(f"- round2 avg processing/wall/fillRate: {s['round2AvgProcessing']}s / {s['round2AvgWall']}s / {s['round2AvgFillRate']}")
    lines.append("")
    lines.append("| file | processing | fillRate | fullOCR ms | reOCR ms | share | recoveredByReOCR | canSkip |")
    lines.append("|---|---:|---:|---:|---:|---:|---|---|")
    for r in report["rounds"][0]:
        if r.get("error"):
            continue
        b = r["ocrCallBreakdown"]
        rec = ", ".join(f"{x['field']}:{x['source']}" for x in r["fieldsRecoveredByReOcr"]) or "-"
        lines.append(
            f"| {r['fileName']} | {r['processing_time']} | {r['fillRate']} | {b['fullOcrMs']:.1f} | "
            f"{b['reOcrTotalMs']:.1f} | {b['reOcrSharePercent']}% | {rec} | {r['canSkipReOcrSafelyFromCurrentEvidence']} |"
        )
    lines.append("")
    lines.append("## OCR Cache 안정성")
    c = report["cacheStability"]
    lines.append(f"- verdict: {c['verdict']}")
    lines.append(f"- stableProjection same: {c['stableCount']}/{c['totalCompared']}")
    lines.append("- cache key: " + ", ".join(c["cacheKeyRecommendation"]))
    lines.append("")
    lines.append("## Response Slim")
    slim = report["responseSlimAnalysis"]
    lines.append(f"- raw/noImages/noImagesNoDebug/CleanJSON avg bytes: {slim['avgRawBytes']} / {slim['avgNoImagesBytes']} / {slim['avgNoImagesNoDebugBytes']} / {slim['avgCleanJsonBytes']}")
    lines.append(f"- serialization raw/slim avg ms: {slim['avgRawSerializationMs']} / {slim['avgSlimSerializationMs']}")
    lines.append(f"- verdict: {slim['verdict']}")
    lines.append("")
    lines.append("## Re-OCR Gating")
    reo = report["reOcrAnalysis"]
    lines.append(f"- verdict: {reo['verdict']}")
    lines.append(f"- upper ran files: {', '.join(reo['upperRanFiles'])}")
    lines.append(f"- amount ran files: {', '.join(reo['amountRanFiles']) or '-'}")
    for reason in reo["whyWarn"]:
        lines.append(f"- {reason}")
    lines.append("")
    lines.append("## Downscale")
    d = report["downscaleRecheck"]
    lines.append(f"- verdict: {d['verdict']}")
    lines.append(f"- {d['currentPolicy']}")
    lines.append(f"- {d['evidence']}")
    lines.append("")
    lines.append("## 최종 후보 순위")
    lines.append("| rank | candidate | verdict | single | repeat | risk |")
    lines.append("|---:|---|---|---|---|---|")
    for item in report["finalRanking"]:
        lines.append(f"| {item['rank']} | {item['candidate']} | {item['verdict']} | {item['singleRunBenefit']} | {item['repeatRunBenefit']} | {item['risk']} |")
    lines.append("")
    lines.append("## 결론")
    concl = report["conclusion"]
    lines.append(f"- 지금 할 수 있는 최선 여부: {concl['isCurrentBest']}")
    lines.append(f"- 가장 안전한 후보: {concl['safestCandidate']}")
    lines.append(f"- 단일 실행 후보: {concl['bestSingleRunCandidate']}")
    lines.append(f"- 반복 실행 후보: {concl['bestRepeatedRunCandidate']}")
    lines.append("- 지금 추천: " + ", ".join(concl["nowRecommended"]))
    lines.append("- 지금 비추천: " + ", ".join(concl["notRecommendedNow"]))
    lines.append("")
    lines.append("## 운영 반영 전 추가 검증")
    for item in report["preApplyValidationNeeded"]:
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    main()
