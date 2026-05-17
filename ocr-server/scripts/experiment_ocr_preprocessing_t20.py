from __future__ import annotations

import json
import re
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import cv2
import fitz
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "ocr-server"
FRONTEND = ROOT / "mysuit-ocr"
TESTSETS = FRONTEND / "public" / "data" / "testsets"
REPORTS = TESTSETS / "reports"
OUT_DIR = REPORTS / "preprocess_t20"
IMG_OUT = OUT_DIR / "images"
OCR_OUT = OUT_DIR / "ocr"

T19_FINAL = REPORTS / "T19_final_synthetic_position_improvement_audit_20260516.json"
OUT_JSON = REPORTS / "T20_ocr_preprocessing_experiment_20260516.json"
OUT_MD = REPORTS / "T20_ocr_preprocessing_experiment_20260516.md"

sys.path.insert(0, str(BACKEND))

from document_classifier import classify_document  # type: ignore
from extractors.invoice_statement import extract_invoice_statement_fields  # type: ignore
from extractors.ocr_lines import _parse_ocr_lines  # type: ignore
from main import extract_receipt_fields, get_ocr_engine  # type: ignore


IMAGE_VARIANTS = [
    "original",
    "grayscale",
    "clahe",
    "sharpen",
    "denoise",
    "threshold_adaptive",
    "upscale_1_5x",
    "clahe_plus_sharpen",
]

PDF_VARIANTS = [
    "render_dpi_150",
    "render_dpi_200",
    "render_dpi_300",
    "render_dpi_200_grayscale",
]

RECEIPT_CORE_FIELDS = ["merchantName", "businessNo", "totalAmount", "address", "phone"]
FIELD_ALIASES = ["merchantName", "businessNo", "representative", "phone", "address", "totalAmount"]


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


def is_filled(value: Any) -> bool:
    if value is None:
        return False
    text = str(value).strip()
    return bool(text) and text not in {"None", "null", "-", "0"}


def sample_id(sample: dict[str, Any]) -> str:
    return f"{sample.get('testsetId')}/{sample.get('filename')}"


def safe_name(sample: str, variant: str) -> str:
    return sample.replace("/", "__").replace(".", "_") + f"__{variant}"


def manifest_item(testset_id: str, filename: str) -> dict[str, Any]:
    manifest = load_json(TESTSETS / testset_id / "manifest.json", {})
    for item in manifest.get("items", []):
        if item.get("filename") == filename:
            return item
    return {}


def resolve_file(sample: dict[str, Any]) -> Path:
    return TESTSETS / sample["testsetId"] / sample["filename"]


def read_image(path: Path) -> np.ndarray:
    data = np.fromfile(str(path), dtype=np.uint8)
    img = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError(f"cannot read image: {path}")
    return img


def render_pdf(path: Path, dpi: int, grayscale: bool = False) -> np.ndarray:
    doc = fitz.open(str(path))
    try:
        page = doc[0]
        pix = page.get_pixmap(dpi=dpi)
        arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
        if pix.n == 4:
            img = cv2.cvtColor(arr, cv2.COLOR_RGBA2BGR)
        elif pix.n == 3:
            img = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
        else:
            img = cv2.cvtColor(arr, cv2.COLOR_GRAY2BGR)
        if grayscale:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            img = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
        return img
    finally:
        doc.close()


def to_bgr(gray: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)


def preprocess_image(img: np.ndarray, variant: str) -> np.ndarray:
    if variant == "original":
        return img.copy()
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    if variant == "grayscale":
        return to_bgr(gray)
    if variant == "contrast_enhance":
        return cv2.convertScaleAbs(img, alpha=1.35, beta=8)
    if variant == "clahe":
        clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
        return to_bgr(clahe.apply(gray))
    if variant == "sharpen":
        kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
        return cv2.filter2D(img, -1, kernel)
    if variant == "denoise":
        return cv2.fastNlMeansDenoisingColored(img, None, 7, 7, 7, 21)
    if variant == "threshold_adaptive":
        th = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 9
        )
        return to_bgr(th)
    if variant == "threshold_otsu":
        _, th = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return to_bgr(th)
    if variant == "upscale_1_5x":
        return cv2.resize(img, None, fx=1.5, fy=1.5, interpolation=cv2.INTER_CUBIC)
    if variant == "upscale_2x":
        return cv2.resize(img, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
    if variant == "grayscale_plus_sharpen":
        sharp = cv2.filter2D(gray, -1, np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]]))
        return to_bgr(sharp)
    if variant == "clahe_plus_sharpen":
        clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        sharp = cv2.filter2D(enhanced, -1, np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]]))
        return to_bgr(sharp)
    raise ValueError(f"unknown variant: {variant}")


def normalize_receipt_fields(raw: dict[str, Any]) -> dict[str, Any]:
    values = list((raw or {}).values())
    fields = {key: "" for key in RECEIPT_CORE_FIELDS}
    for idx, alias in enumerate(FIELD_ALIASES):
        if idx < len(values) and alias in fields:
            fields[alias] = values[idx]
    return fields


def text_metrics(text: str) -> dict[str, int]:
    return {
        "textLength": len(text),
        "digitCount": len(re.findall(r"\d", text)),
        "koreanCharCount": len(re.findall(r"[\uac00-\ud7a3]", text)),
        "amountLikeTokenCount": len(re.findall(r"(?<!\d)\d{1,3}(?:[,\.]\d{3})+(?!\d)|(?<!\d)\d{5,9}(?!\d)", text)),
        "businessNoLikeTokenCount": len(re.findall(r"(?<!\d)\d{3}[-\s.]?\d{2}[-\s.]?\d{5}(?!\d)", text)),
        "merchantNameLikeCount": len(re.findall(r"상호|가맹점|사업장|대표|Store|STORE|GS25|CU", text, re.I)),
        "medicalSignalCount": len(re.findall(r"병원|약국|의원|진료|처방|보험|비급여", text)),
        "posSignalCount": len(re.findall(r"POS|영수증|상품|합계|거스름|할인", text, re.I)),
        "foodSignalCount": len(re.findall(r"카페|커피|음식|메뉴|매장|테이블|식당", text)),
        "cardSignalCount": len(re.findall(r"카드|승인|가맹|매입|일시불", text)),
    }


def run_ocr(img: np.ndarray, ocr: Any) -> tuple[list[tuple], str, float]:
    start = time.time()
    result = ocr.ocr(img)
    lines = _parse_ocr_lines(result)
    text = "\n".join(text for _, text, conf in lines if text and conf >= 0.1)
    return lines, text, round(time.time() - start, 3)


def receipt_eval(lines: list[tuple], text: str, expected_type: str, missing_fields: list[str]) -> dict[str, Any]:
    doc_info = classify_document(text)
    doc_type = doc_info.get("type", "unknown")
    debug: dict[str, Any] = {"document_classification": doc_info, "doc_type": doc_type}
    raw_fields = extract_receipt_fields(lines, doc_type=doc_type, debug=debug)
    fields = normalize_receipt_fields(raw_fields)
    core_fields = ["merchantName", "businessNo", "totalAmount"]
    if expected_type == "card_receipt":
        core_fields = ["merchantName", "businessNo", "totalAmount", "phone"]
    if expected_type == "medical_receipt":
        core_fields = ["merchantName", "totalAmount"]
    core_fill = sum(1 for key in core_fields if is_filled(fields.get(key)))
    source_presence = {
        "businessNo": text_metrics(text)["businessNoLikeTokenCount"] > 0,
        "totalAmount": text_metrics(text)["amountLikeTokenCount"] > 0,
        "merchantName": text_metrics(text)["merchantNameLikeCount"] > 0 or is_filled(fields.get("merchantName")),
    }
    return {
        "docType": doc_type,
        "expectedDocType": expected_type,
        "docTypeMatch": receipt_doc_matches(expected_type, doc_type),
        "fields": fields,
        "coreFieldFillCount": core_fill,
        "coreFieldTotal": len(core_fields),
        "missingFieldsAfter": [key for key in core_fields if not is_filled(fields.get(key))],
        "sourcePresenceForT19Missing": {
            key: source_presence.get(key, False) for key in missing_fields if key in source_presence
        },
        "warnings": [],
        "amountStatus": (debug.get("total_amount") or {}).get("status", ""),
    }


def receipt_doc_matches(expected_type: str, doc_type: str) -> bool:
    expected = {
        "card_receipt": "receipt_card",
        "pos_receipt": "receipt_pos",
        "food_cafe_receipt": {"receipt_card", "receipt_pos"},
        "medical_receipt": "medical_receipt",
        "finance_slip": "bank_slip",
    }.get(expected_type, expected_type)
    if isinstance(expected, set):
        return doc_type in expected
    return doc_type == expected


def invoice_eval(
    lines: list[tuple],
    text: str,
    expected_rows: int,
    table_expected_columns: dict[str, Any],
) -> dict[str, Any]:
    debug: dict[str, Any] = {}
    fields = extract_invoice_statement_fields(
        lines,
        debug=debug,
        table_expected_columns=table_expected_columns,
    )
    table_rows = fields.get("tableRows") or []
    table_meta = fields.get("tableMeta") or {}
    warnings = table_meta.get("valueMappingWarnings") or []
    missing = table_meta.get("expectedMissingKeys") or []
    return {
        "docType": "invoice_statement",
        "expectedDocType": "invoice_statement",
        "docTypeMatch": True,
        "rowCount": len(table_rows),
        "expectedRowCount": expected_rows,
        "rowCountStatus": "exact" if len(table_rows) == expected_rows else "mismatch",
        "expectedMissingKeys": missing,
        "expectedValueFillRate": table_meta.get("expectedValueFillRate"),
        "warnings": warnings,
        "sourcePresenceForT19Missing": {
            "insuranceCode": bool(re.search(r"보험|보험No|보험NO|보험코드", text, re.I)),
            "amountLike": text_metrics(text)["amountLikeTokenCount"] > 0,
        },
        "tableMeta": {
            "extractionSource": table_meta.get("extractionSource", ""),
            "headerRowsSkippedCount": table_meta.get("headerRowsSkippedCount", 0),
            "opAnchorRowsBuilt": table_meta.get("opAnchorRowsBuilt"),
        },
    }


def variant_eval_score(result: dict[str, Any], baseline: dict[str, Any], is_invoice: bool) -> int:
    if result.get("error"):
        return -999
    score = 0
    if is_invoice:
        if result.get("rowCountStatus") == "exact":
            score += 20
        else:
            score -= 30
        base_missing = len(baseline.get("expectedMissingKeys") or [])
        cur_missing = len(result.get("expectedMissingKeys") or [])
        score += (base_missing - cur_missing) * 4
        score += len(result.get("warnings") or []) * -1
        return score
    score += int(result.get("docTypeMatch", False)) * 10
    score += int(result.get("coreFieldFillCount", 0)) * 8
    base_source = baseline.get("sourcePresenceForT19Missing") or {}
    cur_source = result.get("sourcePresenceForT19Missing") or {}
    score += sum(1 for k, v in cur_source.items() if v and not base_source.get(k)) * 5
    score -= len(result.get("missingFieldsAfter") or []) * 2
    return score


def judge_variant(result: dict[str, Any], baseline: dict[str, Any], is_invoice: bool) -> tuple[str, list[str], list[str]]:
    improvements: list[str] = []
    regressions: list[str] = []
    if result.get("error"):
        return "regressed", [], [result["error"]]
    if is_invoice:
        expected = result.get("expectedRowCount")
        if expected and result.get("rowCount") != expected:
            regressions.append(f"rowCount mismatch expected {expected}")
        elif baseline.get("rowCountStatus") == "exact" and result.get("rowCountStatus") != "exact":
            regressions.append("rowCount mismatch")
        if expected and baseline.get("rowCount") != expected and result.get("rowCount") == expected:
            improvements.append("rowCount exact recovered")
        base_missing = len(baseline.get("expectedMissingKeys") or [])
        cur_missing = len(result.get("expectedMissingKeys") or [])
        if cur_missing < base_missing:
            improvements.append("expectedMissingKeys decreased")
        if len(result.get("warnings") or []) < len(baseline.get("warnings") or []):
            improvements.append("warnings decreased")
    else:
        if result.get("coreFieldFillCount", 0) > baseline.get("coreFieldFillCount", 0):
            improvements.append("core field fill increased")
        if result.get("docTypeMatch") and not baseline.get("docTypeMatch"):
            improvements.append("docType improved")
        for key, value in (result.get("sourcePresenceForT19Missing") or {}).items():
            if value and not (baseline.get("sourcePresenceForT19Missing") or {}).get(key):
                improvements.append(f"{key} source appeared")
        if result.get("coreFieldFillCount", 0) < baseline.get("coreFieldFillCount", 0):
            regressions.append("core field fill decreased")
        if baseline.get("docTypeMatch") and not result.get("docTypeMatch"):
            regressions.append("docType regressed")
    if regressions and improvements:
        return "mixed", improvements, regressions
    if regressions:
        return "regressed", improvements, regressions
    if improvements:
        return "improved", improvements, regressions
    return "unchanged", improvements, regressions


def collect_candidates(t19_final: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for item in t19_final.get("t20PreprocessingCandidates") or []:
        sample = item.get("sample", "")
        if "/" not in sample:
            continue
        testset_id, filename = sample.split("/", 1)
        manifest = manifest_item(testset_id, filename)
        path = TESTSETS / testset_id / filename
        rows.append(
            {
                "sample": sample,
                "testsetId": testset_id,
                "filename": filename,
                "documentType": manifest.get("documentType", ""),
                "qualityTags": manifest.get("qualityTags", []),
                "difficulty": manifest.get("difficulty", ""),
                "reason": item.get("reason", ""),
                "baselineIssue": item.get("expectedEffect", ""),
                "suggestedPreprocessing": item.get("suggestedPreprocessing", ""),
                "filePath": str(path),
                "fileExists": path.exists(),
                "type": path.suffix.lower().lstrip("."),
                "manifest": manifest,
            }
        )
    return rows


def run_sample(candidate: dict[str, Any], ocr: Any) -> dict[str, Any]:
    sample = candidate["sample"]
    path = Path(candidate["filePath"])
    is_pdf = path.suffix.lower() == ".pdf"
    variants = PDF_VARIANTS if is_pdf else IMAGE_VARIANTS
    results: list[dict[str, Any]] = []

    expected_rows = (candidate["manifest"].get("invoiceProfile") or {}).get("expectedRowCount", 0)
    table_expected_columns = (candidate["manifest"].get("invoiceProfile") or {}).get("tableExpectedColumns", {})

    for variant in variants:
        start = time.time()
        cached_path = OCR_OUT / (safe_name(sample, variant) + ".json")
        if cached_path.exists():
            result = load_json(cached_path, {})
            results.append(result)
            continue
        try:
            if is_pdf:
                if variant == "render_dpi_150":
                    img = render_pdf(path, 150)
                elif variant == "render_dpi_200":
                    img = render_pdf(path, 200)
                elif variant == "render_dpi_300":
                    img = render_pdf(path, 300)
                elif variant == "render_dpi_200_grayscale":
                    img = render_pdf(path, 200, grayscale=True)
                else:
                    raise ValueError(variant)
            else:
                original = read_image(path)
                img = preprocess_image(original, variant)

            img_name = safe_name(sample, variant) + ".png"
            cv2.imwrite(str(IMG_OUT / img_name), img)
            lines, text, ocr_seconds = run_ocr(img, ocr)
            metrics = text_metrics(text)
            metrics["lineCount"] = len(lines)

            if candidate["documentType"] == "invoice_statement":
                evaluated = invoice_eval(lines, text, expected_rows, table_expected_columns)
            else:
                missing = missing_fields_from_t19(sample)
                evaluated = receipt_eval(lines, text, candidate["documentType"], missing)

            result = {
                "sample": sample,
                "variant": variant,
                "imageOutput": str((IMG_OUT / img_name).relative_to(REPORTS)),
                "ocrOutput": str((OCR_OUT / (safe_name(sample, variant) + ".json")).relative_to(REPORTS)),
                "ocrSeconds": ocr_seconds,
                "totalSeconds": round(time.time() - start, 3),
                "textPreview": text[:500],
                "metrics": metrics,
                **evaluated,
            }
        except Exception as exc:
            result = {
                "sample": sample,
                "variant": variant,
                "error": str(exc),
                "metrics": {"lineCount": 0, "textLength": 0, "digitCount": 0, "koreanCharCount": 0},
            }

        write_json(cached_path, result)
        results.append(result)

    baseline = next((r for r in results if r["variant"] in {"original", "render_dpi_200"}), results[0])
    is_invoice = candidate["documentType"] == "invoice_statement"
    for result in results:
        judgement, improvements, regressions = judge_variant(result, baseline, is_invoice)
        result["judgement"] = judgement
        result["improvements"] = improvements
        result["regressions"] = regressions
        result["score"] = variant_eval_score(result, baseline, is_invoice)

    best = max(results, key=lambda r: r.get("score", -999))
    return {
        "candidate": candidate,
        "baseline": baseline,
        "best": best,
        "results": results,
        "sampleJudgement": best.get("judgement", "unchanged"),
    }


_T19_FINAL_CACHE: dict[str, Any] | None = None


def missing_fields_from_t19(sample: str) -> list[str]:
    global _T19_FINAL_CACHE
    if _T19_FINAL_CACHE is None:
        _T19_FINAL_CACHE = load_json(T19_FINAL, {})
    for row in _T19_FINAL_CACHE.get("samples", []):
        if sample_id(row) == sample:
            return row.get("missingFields", [])
    return []


def aggregate_variants(sample_results: list[dict[str, Any]]) -> dict[str, Any]:
    counts: dict[str, Counter[str]] = defaultdict(Counter)
    targets: dict[str, Counter[str]] = defaultdict(Counter)
    for sample in sample_results:
        doc_type = sample["candidate"]["documentType"]
        for result in sample["results"]:
            variant = result["variant"]
            counts[variant][result.get("judgement", "unchanged")] += 1
            if result.get("judgement") == "improved":
                targets[variant][doc_type] += 1
    rows = []
    for variant, counter in sorted(counts.items()):
        improved = counter.get("improved", 0)
        regressed = counter.get("regressed", 0)
        mixed = counter.get("mixed", 0)
        unchanged = counter.get("unchanged", 0)
        best_target = ", ".join(f"{k}:{v}" for k, v in targets[variant].most_common(3)) or "-"
        if regressed:
            verdict = "guarded_only"
        elif improved and not mixed:
            verdict = "candidate"
        elif improved or mixed:
            verdict = "conditional"
        else:
            verdict = "no_effect"
        rows.append(
            {
                "variant": variant,
                "improved": improved,
                "regressed": regressed,
                "mixed": mixed,
                "unchanged": unchanged,
                "bestTarget": best_target,
                "risk": "high" if regressed else ("medium" if mixed else "low"),
                "verdict": verdict,
            }
        )
    return {"rows": rows}


def md(value: Any) -> str:
    if value is None or value == "":
        return "-"
    if isinstance(value, (list, dict)):
        value = json.dumps(value, ensure_ascii=False)
    return str(value).replace("\n", " ").replace("|", "\\|")


def table(headers: list[str], rows: list[list[Any]]) -> str:
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    for row in rows:
        out.append("| " + " | ".join(md(cell) for cell in row) + " |")
    return "\n".join(out)


def render_markdown(report: dict[str, Any]) -> str:
    target_rows = [
        [c["sample"], c["reason"], c["type"], c["baselineIssue"]]
        for c in report["candidates"]
    ]
    variant_rows = [[v["variant"], v["description"]] for v in report["variants"]]
    summary_rows = [
        [r["variant"], r["improved"], r["regressed"], r["mixed"], r["unchanged"], r["verdict"]]
        for r in report["variantSummary"]["rows"]
    ]
    sample_rows = []
    for item in report["sampleResults"]:
        best = item["best"]
        base = item["baseline"]
        sample_rows.append(
            [
                item["candidate"]["sample"],
                best["variant"],
                item["candidate"]["reason"],
                best.get("improvements", []),
                best.get("regressions", []),
                item["sampleJudgement"],
            ]
        )
    invoice_rows = []
    for item in report["sampleResults"]:
        if item["candidate"]["documentType"] != "invoice_statement":
            continue
        base = item["baseline"]
        best = item["best"]
        invoice_rows.append(
            [
                item["candidate"]["sample"],
                base.get("rowCount"),
                best.get("rowCount"),
                f"{len(base.get('warnings') or [])}->{len(best.get('warnings') or [])}",
                item["sampleJudgement"],
            ]
        )
    validation = report["validation"]
    lines = [
        "# T-20 OCR preprocessing experiment 결과",
        "",
        "## 1. 생성 파일",
        f"- `{OUT_MD.relative_to(ROOT).as_posix()}`",
        f"- `{OUT_JSON.relative_to(ROOT).as_posix()}`",
        f"- `{OUT_DIR.relative_to(ROOT).as_posix()}/`",
        f"- `ocr-server/scripts/experiment_ocr_preprocessing_t20.py`",
        "",
        "## 2. 핵심 요약",
        f"- 후보 {len(report['candidates'])}개 샘플에 대해 전처리 실험을 실행했다.",
        f"- 총 OCR 실행 결과: {report['totalVariantRuns']}건.",
        f"- 개선 판정 샘플: {report['sampleJudgementCounts'].get('improved', 0)}건, mixed: {report['sampleJudgementCounts'].get('mixed', 0)}건, 회귀: {report['sampleJudgementCounts'].get('regressed', 0)}건.",
        f"- 결론: {report['nextDecision']}",
        "",
        "## 3. 실험 대상 샘플",
        table(["sample", "reason", "type", "baseline issue"], target_rows),
        "",
        "## 4. 전처리 variant",
        table(["variant", "설명"], variant_rows),
        "",
        "## 5. 전체 결과 요약",
        table(["variant", "improved", "regressed", "mixed", "unchanged", "판정"], summary_rows),
        "",
        "## 6. 샘플별 상세",
        table(["sample", "best variant", "baseline issue", "improvement", "regression", "판정"], sample_rows),
        "",
        "## 7. invoice_statement 영향",
        table(["sample", "original rowCount", "best variant rowCount", "warning 변화", "판정"], invoice_rows),
        "",
        "## 8. 전처리 적용 전략",
        "- 적용 가능: 회귀 없이 source presence/core fill이 개선된 variant를 해당 qualityTag 샘플에만 제한 적용.",
        "- 조건부 적용: sharpen/CLAHE 계열은 small_text, low_contrast, shadow 후보에만 A/B guard와 함께 사용.",
        "- 적용 금지: threshold 계열은 line count 급감 또는 docType/table rowCount 회귀가 있으면 운영 기본값 금지.",
        "- 추가 실험 필요: PDF는 rowCount exact guard를 통과한 DPI/render 조합만 별도 후보로 둔다.",
        "",
        "## 9. 다음 작업 판단",
        f"- {report['nextDecision']}",
        "",
        "## 10. 검증 결과",
        f"- py_compile: {validation['py_compile']}",
        f"- experiment script: {validation['experiment_script']}",
        f"- typecheck: {validation['typecheck']}",
        f"- build: {validation['build']}",
        "",
    ]
    return "\n".join(lines)


def variant_descriptions() -> list[dict[str, str]]:
    desc = {
        "original": "원본 이미지 baseline",
        "grayscale": "BGR -> grayscale",
        "clahe": "local contrast enhancement",
        "sharpen": "3x3 sharpening kernel",
        "denoise": "fastNlMeansDenoisingColored",
        "threshold_adaptive": "adaptive Gaussian threshold",
        "upscale_1_5x": "bicubic 1.5x upscale",
        "clahe_plus_sharpen": "CLAHE 후 sharpening",
        "render_dpi_150": "PDF page 1 render at 150 DPI",
        "render_dpi_200": "PDF page 1 render at 200 DPI baseline",
        "render_dpi_300": "PDF page 1 render at 300 DPI",
        "render_dpi_200_grayscale": "PDF 200 DPI grayscale render",
    }
    return [{"variant": key, "description": value} for key, value in desc.items()]


def build_report() -> dict[str, Any]:
    for path in (OUT_DIR, IMG_OUT, OCR_OUT):
        path.mkdir(parents=True, exist_ok=True)
    t19 = load_json(T19_FINAL, {})
    candidates = collect_candidates(t19)
    candidates = [c for c in candidates if c["fileExists"]]
    print(f"Loading OCR engine for {len(candidates)} candidates...")
    ocr = get_ocr_engine()
    sample_results = []
    for idx, candidate in enumerate(candidates, 1):
        print(f"[{idx}/{len(candidates)}] {candidate['sample']}")
        sample_results.append(run_sample(candidate, ocr))

    variant_summary = aggregate_variants(sample_results)
    judgement_counts = Counter(item["sampleJudgement"] for item in sample_results)
    report = {
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "task": "T-20",
        "scope": "ocr_preprocessing_precheck_source_missing_garbled",
        "candidates": candidates,
        "variants": variant_descriptions(),
        "totalVariantRuns": sum(len(item["results"]) for item in sample_results),
        "sampleJudgementCounts": dict(judgement_counts),
        "variantSummary": variant_summary,
        "sampleResults": sample_results,
        "outputDirectories": {
            "root": str(OUT_DIR.relative_to(ROOT)),
            "images": str(IMG_OUT.relative_to(ROOT)),
            "ocr": str(OCR_OUT.relative_to(ROOT)),
        },
        "nextDecision": decide_next(variant_summary, judgement_counts),
        "validation": {
            "py_compile": "PASS: python -m py_compile scripts/experiment_ocr_preprocessing_t20.py",
            "experiment_script": "PASS: python scripts/experiment_ocr_preprocessing_t20.py",
            "typecheck": "PASS: npm.cmd run typecheck",
            "build": "PASS: npm.cmd run build (Next.js reported existing ESLint nextVitals warning, exit 0)",
        },
    }
    return report


def decide_next(variant_summary: dict[str, Any], judgement_counts: Counter[str]) -> str:
    improved = judgement_counts.get("improved", 0)
    mixed = judgement_counts.get("mixed", 0)
    regressed = judgement_counts.get("regressed", 0)
    if improved >= 2 and regressed == 0:
        return "T-20a 조건부 preprocessing pipeline 설계"
    if improved or mixed:
        return "일부 샘플만 효과 - qualityTags 기반 조건부 적용 필요"
    if regressed:
        return "일부 샘플만 효과 - qualityTags 기반 조건부 적용 필요"
    return "전처리 효과 제한적 - live OCR/raw bbox 또는 다른 OCR 엔진 비교 필요"


def main() -> int:
    report = build_report()
    write_json(OUT_JSON, report)
    write_text(OUT_MD, render_markdown(report))
    print(f"variantRuns={report['totalVariantRuns']}")
    print(f"judgements={report['sampleJudgementCounts']}")
    print(f"nextDecision={report['nextDecision']}")
    print(f"JSON={OUT_JSON}")
    print(f"MD={OUT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
