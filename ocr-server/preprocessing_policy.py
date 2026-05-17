"""
OCR preprocessing policy loader and compare_then_select guard.

Debug/experimental mode only. Production OCR path is unchanged.
Default: disabled (debug_preprocessing=False in all callers).

Usage (future main.py integration):
    from preprocessing_policy import get_candidates, compare_then_select
    if debug_preprocessing:
        candidates = get_candidates(quality_tags, doc_type)
        result = compare_then_select(original, variant_results, quality_tags, doc_type)
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parent.parent
_POLICY_JSON = (
    _ROOT / "mysuit-ocr" / "public" / "data" / "testsets" / "reports"
    / "T20a_preprocessing_policy_20260516.json"
)

# Supported variants (T-20c conditional_accept 대상)
SUPPORTED_VARIANTS = {
    "grayscale",
    "clahe",
    "upscale_1_5x",
    "clahe_plus_sharpen",
    "render_dpi_200_grayscale",
}

# 기본 차단 (T-20c에서 confirmed blocked)
ALWAYS_BLOCKED = {"threshold_adaptive", "denoise", "render_dpi_150", "render_dpi_200", "render_dpi_300"}


def _load_policy() -> dict[str, Any]:
    if _POLICY_JSON.exists():
        try:
            return json.loads(_POLICY_JSON.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


_POLICY: dict[str, Any] = _load_policy()


def get_candidates(quality_tags: list[str], doc_type: str) -> list[str]:
    """qualityTags/documentType 기반 candidate variant 목록 반환.

    Returns:
        List of variant names to try in compare_then_select.
        Empty list if blocked or no applicable variants.
    """
    qt = [t.lower() for t in (quality_tags or [])]

    # preprocessing_blocked → 후보 없음
    if "preprocessing_blocked" in qt:
        return []

    # invoice_statement 기본 차단. preprocessing_candidate가 있어야 후보 생성.
    if doc_type == "invoice_statement":
        if "preprocessing_candidate" not in qt:
            return []
        if "pdf_low_resolution" in qt:
            return ["render_dpi_200_grayscale"]
        return []

    # receipt 계열
    candidates: list[str] = []

    # blurred: clahe + upscale_1_5x
    if "blurred" in qt:
        for v in ["clahe", "upscale_1_5x", "clahe_plus_sharpen"]:
            if v not in candidates:
                candidates.append(v)

    # shadow / low_contrast: clahe
    if "shadow" in qt or "low_contrast" in qt:
        for v in ["clahe", "clahe_plus_sharpen"]:
            if v not in candidates:
                candidates.append(v)

    # long_receipt + small_text 복합: grayscale, clahe
    if "long_receipt" in qt and "small_text" in qt:
        for v in ["grayscale", "clahe", "clahe_plus_sharpen"]:
            if v not in candidates:
                candidates.append(v)

    # garbled_source: upscale_1_5x, clahe_plus_sharpen
    if "garbled_source" in qt:
        for v in ["upscale_1_5x", "clahe_plus_sharpen"]:
            if v not in candidates:
                candidates.append(v)

    # preprocessing_candidate만 있고 위 태그 없으면 기본 후보
    if "preprocessing_candidate" in qt and not candidates:
        candidates = ["clahe", "upscale_1_5x"]

    # 미지원/기본차단 제거
    candidates = [v for v in candidates if v in SUPPORTED_VARIANTS and v not in ALWAYS_BLOCKED]
    return candidates


def _is_filled(v: Any) -> bool:
    return bool(v and str(v).strip() not in {"", "None", "null", "-", "0"})


def apply_receipt_guard(
    original: dict[str, Any],
    variant_result: dict[str, Any],
) -> dict[str, str | list[str]]:
    """Receipt compare guard.

    Uses T-20 precomputed improvements/regressions.
    Returns dict with decision, reasons.
    """
    if variant_result.get("error"):
        return {"decision": "reject", "reasons": [f"ocr_error: {variant_result['error']}"]}

    improvements: list[str] = variant_result.get("improvements", [])
    regressions: list[str] = variant_result.get("regressions", [])
    reasons: list[str] = []

    # core field 회귀 체크
    orig_fields = original.get("fields") or {}
    var_fields = variant_result.get("fields") or {}
    for field in ("merchantName", "businessNo", "totalAmount"):
        if _is_filled(orig_fields.get(field)) and not _is_filled(var_fields.get(field)):
            regressions = list(regressions) + [f"field_lost: {field}"]

    # docType 회귀 체크
    if original.get("docTypeMatch") and not variant_result.get("docTypeMatch"):
        regressions = list(regressions) + ["docType_regressed"]

    if regressions:
        return {"decision": "reject", "reasons": regressions}
    if improvements:
        return {"decision": "candidate_accept", "reasons": improvements}
    return {"decision": "no_improvement", "reasons": ["no_improvement"]}


def apply_invoice_guard(
    original: dict[str, Any],
    variant_result: dict[str, Any],
    expected_row_count: int | None,
) -> dict[str, str | list[str]]:
    """Invoice statement compare guard.

    rowCount exact는 필수 조건.
    """
    if variant_result.get("error"):
        return {"decision": "reject", "reasons": [f"ocr_error: {variant_result['error']}"]}

    improvements: list[str] = variant_result.get("improvements", [])
    regressions: list[str] = variant_result.get("regressions", [])

    if regressions:
        return {"decision": "reject", "reasons": regressions}

    # rowCount exact 필수
    if expected_row_count is not None:
        actual_rows = variant_result.get("rowCount")
        if actual_rows != expected_row_count:
            return {
                "decision": "reject",
                "reasons": [f"rowcount_mismatch: expected={expected_row_count}, got={actual_rows}"],
            }

    if improvements:
        return {"decision": "candidate_accept", "reasons": improvements}
    return {"decision": "no_improvement", "reasons": ["no_improvement"]}


def compare_then_select(
    original: dict[str, Any],
    variant_results: list[dict[str, Any]],
    quality_tags: list[str],
    doc_type: str,
    expected_row_count: int | None = None,
    debug_preprocessing: bool = False,
) -> dict[str, Any]:
    """원본과 전처리 variant 결과를 비교해 candidate를 선택한다.

    Args:
        original: original OCR result dict (from T-20 or live)
        variant_results: list of variant result dicts (variant + improvements/regressions/fields etc.)
        quality_tags: sample's qualityTags
        doc_type: documentType string
        expected_row_count: for invoice_statement guard
        debug_preprocessing: must be True to have any effect (safety gate)

    Returns:
        dict with selected_candidate, would_apply_in_debug, variant_decisions
    """
    candidates = get_candidates(quality_tags, doc_type)
    is_invoice = doc_type == "invoice_statement"

    variant_decisions: list[dict[str, Any]] = []
    selected_candidate: str | None = None

    for vr in variant_results:
        vname = vr.get("variant", "")
        if vname == "original":
            continue
        if vname in ALWAYS_BLOCKED:
            variant_decisions.append({"variant": vname, "decision": "always_blocked", "reasons": []})
            continue
        if vname not in candidates:
            variant_decisions.append({
                "variant": vname,
                "decision": "policy_skip",
                "reasons": [f"not_in_candidates_for_tags={quality_tags}"],
            })
            continue

        if is_invoice:
            guard = apply_invoice_guard(original, vr, expected_row_count)
        else:
            guard = apply_receipt_guard(original, vr)

        variant_decisions.append({"variant": vname, **guard})
        if guard["decision"] == "candidate_accept" and selected_candidate is None:
            selected_candidate = vname

    would_apply = debug_preprocessing and selected_candidate is not None
    return {
        "candidates": candidates,
        "variantDecisions": variant_decisions,
        "selectedCandidate": selected_candidate,
        "wouldApplyInDebug": would_apply,
        "wouldApplyInProduction": False,
    }


# ============================================================
# Manifest lookup helpers (T-20d)
# ============================================================

_TESTSETS_ROOT = _ROOT / "mysuit-ocr" / "public" / "data" / "testsets"


def _lookup_manifest_item(filename: str) -> dict[str, Any]:
    """Scan testset manifests for filename, return matching item or {}."""
    for testset_dir in _TESTSETS_ROOT.iterdir():
        if not testset_dir.is_dir():
            continue
        manifest_path = testset_dir / "manifest.json"
        if not manifest_path.exists():
            continue
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
            for item in data.get("items", []):
                if item.get("filename") == filename:
                    return item
        except Exception:
            pass
    return {}


def get_quality_tags_from_manifest(filename: str) -> list[str]:
    """Return qualityTags for a filename from any testset manifest."""
    return _lookup_manifest_item(filename).get("qualityTags", [])


def get_expected_row_count(filename: str) -> int | None:
    """Return expectedRowCount for invoice samples."""
    item = _lookup_manifest_item(filename)
    return (item.get("invoiceProfile") or {}).get("expectedRowCount")


def get_table_expected_columns(filename: str) -> dict[str, Any] | None:
    """Return tableExpectedColumns for invoice samples."""
    item = _lookup_manifest_item(filename)
    return (item.get("invoiceProfile") or {}).get("tableExpectedColumns")


# ============================================================
# Live preprocessing variant runner (T-20d)
# ============================================================

def apply_image_preprocessing(img: Any, variant: str) -> Any:
    """Apply preprocessing variant to a BGR numpy image.

    Returns preprocessed image. Raises ValueError for unsupported variants.
    """
    import cv2
    import numpy as np

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    if variant == "grayscale":
        return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    if variant == "clahe":
        clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
        return cv2.cvtColor(clahe.apply(gray), cv2.COLOR_GRAY2BGR)
    if variant == "upscale_1_5x":
        return cv2.resize(img, None, fx=1.5, fy=1.5, interpolation=cv2.INTER_CUBIC)
    if variant == "clahe_plus_sharpen":
        clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
        sharp = cv2.filter2D(enhanced, -1, kernel)
        return cv2.cvtColor(sharp, cv2.COLOR_GRAY2BGR)
    raise ValueError(f"unsupported image variant: {variant}")


def render_pdf_variant(data: bytes, variant: str) -> Any:
    """Render first page of a PDF for a given preprocessing variant.

    Returns BGR numpy image.
    """
    import fitz
    import cv2
    import numpy as np

    if variant != "render_dpi_200_grayscale":
        raise ValueError(f"unsupported pdf variant: {variant}")

    doc = fitz.open(stream=data, filetype="pdf")
    try:
        page = doc[0]
        pix = page.get_pixmap(dpi=200)
        arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
        if pix.n == 4:
            img = cv2.cvtColor(arr, cv2.COLOR_RGBA2BGR)
        elif pix.n == 3:
            img = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
        else:
            img = cv2.cvtColor(arr, cv2.COLOR_GRAY2BGR)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    finally:
        doc.close()


def compute_receipt_improvements(
    original: dict[str, Any],
    variant_result: dict[str, Any],
) -> tuple[list[str], list[str]]:
    """Compare original vs variant receipt fields, return (improvements, regressions)."""
    orig_fields = original.get("fields") or {}
    var_fields = variant_result.get("fields") or {}
    core = ["merchantName", "businessNo", "totalAmount"]

    orig_fill = sum(1 for f in core if _is_filled(orig_fields.get(f)))
    var_fill = sum(1 for f in core if _is_filled(var_fields.get(f)))

    improvements: list[str] = []
    regressions: list[str] = []

    if var_fill > orig_fill:
        improvements.append("core field fill increased")
    elif var_fill < orig_fill:
        regressions.append("core field fill decreased")

    if original.get("docTypeMatch") and not variant_result.get("docTypeMatch"):
        regressions.append("docType regressed")
    elif not original.get("docTypeMatch") and variant_result.get("docTypeMatch"):
        improvements.append("docType improved")

    return improvements, regressions


def compute_invoice_improvements(
    original: dict[str, Any],
    variant_result: dict[str, Any],
    expected_rc: int | None,
) -> tuple[list[str], list[str]]:
    """Compare original vs variant invoice rowCounts, return (improvements, regressions)."""
    orig_rc = original.get("rowCount")
    var_rc = variant_result.get("rowCount")
    improvements: list[str] = []
    regressions: list[str] = []

    if expected_rc is not None:
        if orig_rc != expected_rc and var_rc == expected_rc:
            improvements.append("rowCount exact recovered")
        elif orig_rc == expected_rc and var_rc != expected_rc:
            regressions.append(f"rowCount mismatch expected {expected_rc}")
        elif var_rc != expected_rc:
            regressions.append(f"rowCount mismatch expected {expected_rc}")

    return improvements, regressions


# ============================================================
# Auto-apply decision helper (T-20g)
# ============================================================

# Receipt doc_type values accepted as "receipt" (not invoice)
_RECEIPT_DOC_TYPES = {
    "receipt_card", "receipt_pos", "medical_receipt", "bank_slip",
    "card_receipt", "pos_receipt", "food_cafe_receipt", "medical_receipt",
    "receipt",
}

# Amount threshold: bare number >= 10M won → likely false positive
_AMOUNT_FP_THRESHOLD = 10_000_000


def decide_auto_apply_preprocessing(
    original: dict[str, Any],
    candidate_result: dict[str, Any],
    sample_meta: dict[str, Any],
    debug_decision: dict[str, Any],
) -> dict[str, Any]:
    """Determine whether preprocessing result is safe to auto-apply in production.

    This helper is for DESIGN / VALIDATION purposes only.
    The actual productionApplied=True gate is NOT implemented here.
    Returns a decision dict describing whether auto-apply would be allowed.

    Args:
        original: original OCR result (docType, coreFieldFillCount, fields, ...)
        candidate_result: selected variant result (same structure)
        sample_meta: dict with documentType, qualityTags, filename
        debug_decision: dict from compare_then_select (decision, selectedCandidate, ...)

    Returns:
        {
            "autoApplyAllowed": bool,
            "reason": list[str],
            "riskLevel": "low" | "medium" | "high",
            "requiresManualReview": bool,
        }
    """
    import re as _re

    reasons: list[str] = []
    doc_type = sample_meta.get("documentType", "unknown")
    quality_tags = [t.lower() for t in (sample_meta.get("qualityTags") or [])]
    ocr_doc_type = (original.get("docType") or "").lower()

    # ── Rule 1: invoice_statement は auto-apply 永久除外 ──
    is_invoice = doc_type == "invoice_statement" or ocr_doc_type == "invoice_statement"
    if is_invoice:
        return {
            "autoApplyAllowed": False,
            "reason": ["invoice_excluded_from_auto_apply"],
            "riskLevel": "high",
            "requiresManualReview": False,
        }

    # ── Rule 2: debug decision must be candidate_accept ──
    if debug_decision.get("decision") != "candidate_accept":
        return {
            "autoApplyAllowed": False,
            "reason": [f"debug_decision_not_accept: {debug_decision.get('decision')}"],
            "riskLevel": "low",
            "requiresManualReview": False,
        }

    # ── Rule 3: preprocessing_blocked tag → always blocked ──
    if "preprocessing_blocked" in quality_tags:
        return {
            "autoApplyAllowed": False,
            "reason": ["preprocessing_blocked_tag"],
            "riskLevel": "high",
            "requiresManualReview": False,
        }

    # ── Rule 4: preprocessing_candidate tag REQUIRED for auto-apply ──
    # Prevents normal receipts with matching tags (e.g. pos_005 with long_receipt+small_text)
    # from being auto-applied without T-20 experiment confirmation.
    if "preprocessing_candidate" not in quality_tags:
        reasons.append("no_preprocessing_candidate_tag")

    # ── Rule 5: critical field must not be lost ──
    orig_fields = original.get("fields") or {}
    var_fields = candidate_result.get("fields") or {}
    for field in ("merchantName", "businessNo", "totalAmount"):
        if _is_filled(orig_fields.get(field)) and not _is_filled(var_fields.get(field)):
            reasons.append(f"critical_field_lost: {field}")

    # ── Rule 6: improvement delta must be positive ──
    orig_fill = original.get("coreFieldFillCount", 0)
    var_fill = candidate_result.get("coreFieldFillCount", 0)
    debug_improvements = debug_decision.get("reasons", [])
    has_improvement = (var_fill > orig_fill) or bool(debug_improvements)
    if not has_improvement:
        reasons.append("no_positive_improvement_delta")

    # ── Rule 7: false positive amount check ──
    raw_amount = var_fields.get("totalAmount", "")
    if raw_amount and str(raw_amount).strip():
        try:
            _digits = _re.sub(r"[,\s원₩]", "", str(raw_amount))
            _amt = int(_digits or "0")
            if _amt >= _AMOUNT_FP_THRESHOLD:
                reasons.append(f"false_positive_amount_suspected: {raw_amount}")
        except Exception:
            pass

    # ── Rule 8: docType must not have regressed ──
    if original.get("docTypeMatch") and not candidate_result.get("docTypeMatch", True):
        reasons.append("docType_regressed")

    # ── Final decision ──
    if reasons:
        has_critical = any(
            "critical_field_lost" in r or "false_positive" in r or "docType_regressed" in r
            for r in reasons
        )
        risk = "high" if has_critical else "medium"
        needs_review = "no_preprocessing_candidate_tag" in reasons or has_critical
        return {
            "autoApplyAllowed": False,
            "reason": reasons,
            "riskLevel": risk,
            "requiresManualReview": needs_review,
        }

    return {
        "autoApplyAllowed": True,
        "reason": ["all_guards_passed"],
        "riskLevel": "low",
        "requiresManualReview": False,
    }
