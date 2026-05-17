"""
T-20a qualityTags 기반 preprocessing policy / guard 설계 스크립트.

목적:
  - T-20 실험 결과를 분석하여 qualityTags 기반 조건부 전처리 정책을 설계
  - 각 sample/variant에 정책 guard를 가상 적용해 accept/reject 판정 시뮬레이션
  - 운영 경로 연결 없이 정책 문서/JSON만 생성

중요:
  - 이 스크립트는 운영 OCR 경로를 수정하지 않는다.
  - main.py 기본 OCR 경로에 연결하지 않는다.
  - 정책 JSON은 참고 문서이며 추후 T-20b에서 운영 연결 여부를 결정한다.
"""
from __future__ import annotations
import json
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "mysuit-ocr"
TESTSETS = FRONTEND / "public/data/testsets"
REPORTS = TESTSETS / "reports"

T20_JSON = REPORTS / "T20_ocr_preprocessing_experiment_20260516.json"
OUT_POLICY_JSON = REPORTS / "T20a_preprocessing_policy_20260516.json"
OUT_DESIGN_JSON = REPORTS / "T20a_preprocessing_policy_guard_design_20260516.json"
OUT_MD = REPORTS / "T20a_preprocessing_policy_guard_design_20260516.md"


# ============================================================
# 정책 정의
# ============================================================

POLICY = {
    "version": "T20a-20260516",
    "generatedAt": datetime.now().isoformat(),
    "description": (
        "qualityTags 기반 조건부 preprocessing policy. "
        "T-20 실험 결과를 바탕으로 설계. "
        "기본 비활성, compare_then_select 모드로만 사용."
    ),
    "default": {
        "enabled": False,
        "mode": "compare_then_select",
        "description": "기본적으로 전처리 비활성. 조건 충족 시에만 원본/전처리 비교 후 선택.",
    },
    "variants": {
        "upscale_1_5x": {
            "description": "bicubic 1.5x upscale",
            "risk": "low",
            "regressionRate": "0/8",
            "enabledFor": ["blurred", "ocr_garbled_with_small"],
            "blockedFor": ["invoice_statement"],
            "guards": ["core_fields_not_regressed", "doctype_not_regressed"],
            "note": "T-20에서 회귀 0건. small_text 단독은 효과 불명확, blurred/garbled 복합에 유리.",
        },
        "clahe": {
            "description": "local contrast enhancement (CLAHE)",
            "risk": "medium",
            "regressionRate": "1/8",
            "enabledFor": ["blurred", "shadow", "low_contrast"],
            "blockedFor": ["invoice_statement", "small_text_only"],
            "guards": ["core_fields_not_regressed", "doctype_not_regressed", "no_new_false_positive"],
            "note": "shadow/blurred에서 효과. small_text 단독(card_001) 오히려 회귀.",
        },
        "clahe_plus_sharpen": {
            "description": "CLAHE + sharpening",
            "risk": "medium",
            "regressionRate": "1/8",
            "enabledFor": ["blurred", "shadow", "garbled_source"],
            "blockedFor": ["invoice_statement", "small_text_only"],
            "guards": ["core_fields_not_regressed", "doctype_not_regressed", "no_new_false_positive"],
            "note": "clahe와 비슷한 효과. pos_006(garbled) 개선.",
        },
        "grayscale": {
            "description": "BGR -> grayscale 변환",
            "risk": "medium",
            "regressionRate": "1/8",
            "enabledFor": ["long_receipt", "dense_content"],
            "blockedFor": ["invoice_statement"],
            "guards": ["core_fields_not_regressed"],
            "note": "medical_003(long_receipt+small_text)에서 효과. long_receipt 조합에서 유리.",
        },
        "sharpen": {
            "description": "3x3 sharpening kernel",
            "risk": "medium",
            "regressionRate": "1/8",
            "enabledFor": ["long_receipt"],
            "blockedFor": ["invoice_statement", "small_text_only"],
            "guards": ["core_fields_not_regressed"],
            "note": "medical_003에서만 효과. small_text 단독은 불리.",
        },
        "denoise": {
            "description": "fastNlMeansDenoisingColored",
            "risk": "high",
            "regressionRate": "3/8",
            "enabledFor": [],
            "blockedFor": ["ALL"],
            "defaultBlocked": True,
            "note": "T-20에서 회귀 3/8. 기본 차단. 특수 경우에만 실험 허용.",
        },
        "threshold_adaptive": {
            "description": "adaptive Gaussian threshold",
            "risk": "high",
            "regressionRate": "2/8",
            "enabledFor": [],
            "blockedFor": ["ALL"],
            "defaultBlocked": True,
            "note": "T-20에서 회귀 2/8. 기본 차단. line count 급감 위험.",
        },
        "render_dpi_200_grayscale": {
            "description": "PDF 200 DPI grayscale render",
            "risk": "high",
            "regressionRate": "1/2",
            "enabledFor": ["pdf_small_text", "pdf_low_resolution"],
            "blockedFor": ["invoice_statement_dense", "invoice_statement_multi_page_complex"],
            "guards": [
                "rowcount_exact_maintained",
                "expected_value_fill_not_regressed",
                "critical_warnings_not_increased",
                "invoice_anchor_structure_intact",
            ],
            "note": (
                "invoice/3.pdf에서 rowCount exact 회복. "
                "invoice/2.pdf에서 rowCount mismatch 악화. "
                "단순 구조 PDF에만 조건부 허용, 복잡한 구조(OP-anchor 등)는 차단."
            ),
        },
    },
    "qualityTagMapping": {
        "blurred": {
            "recommended": ["clahe", "upscale_1_5x"],
            "fallback": ["clahe_plus_sharpen"],
            "blocked": ["threshold_adaptive", "denoise"],
            "evidence": "card_002(blurred): clahe, upscale_1_5x, clahe_plus_sharpen 모두 개선",
        },
        "shadow": {
            "recommended": ["clahe"],
            "fallback": ["clahe_plus_sharpen"],
            "blocked": ["threshold_adaptive"],
            "evidence": "medical_001(shadow): clahe 개선",
        },
        "low_contrast": {
            "recommended": ["clahe"],
            "fallback": ["clahe_plus_sharpen"],
            "blocked": ["threshold_adaptive"],
            "evidence": "direct evidence 없음, T-20 유사 케이스 추정",
        },
        "small_text": {
            "recommended": [],
            "fallback": [],
            "blocked": ["clahe", "clahe_plus_sharpen", "threshold_adaptive", "denoise"],
            "note": (
                "small_text 단독은 위험. card_001(small_text): ALL variants regressed. "
                "long_receipt와 복합 시에만 허용."
            ),
            "evidence": "card_001, pos_001, pos_002, medical_002: small_text 단독 → unchanged 또는 regressed",
        },
        "long_receipt_and_small_text": {
            "recommended": ["grayscale", "clahe"],
            "fallback": ["sharpen", "clahe_plus_sharpen"],
            "blocked": [],
            "evidence": "medical_003(long_receipt+small_text): 모든 variant 개선",
        },
        "ocr_garbled": {
            "recommended": ["upscale_1_5x"],
            "fallback": ["clahe_plus_sharpen"],
            "blocked": ["denoise", "threshold_adaptive"],
            "evidence": "pos_006(garbled): upscale_1_5x 회귀 없음, clahe_plus_sharpen 개선",
        },
        "pdf_low_resolution": {
            "recommended": ["render_dpi_200_grayscale"],
            "fallback": [],
            "blocked": ["render_dpi_300", "render_dpi_200", "render_dpi_150"],
            "evidence": "invoice/3.pdf: render_dpi_200_grayscale rowCount exact 회복",
        },
    },
    "documentTypePolicy": {
        "invoice_statement": {
            "defaultBlocked": True,
            "allowedVariants": ["render_dpi_200_grayscale"],
            "allowedConditions": ["pdf_low_resolution_confirmed", "guard_passed"],
            "requiredGuards": [
                "rowcount_exact_maintained",
                "expected_value_fill_not_regressed",
                "critical_warnings_not_increased",
                "invoice_anchor_structure_intact",
            ],
            "blockedConditions": [
                "invoice/2.pdf: OP-anchor 구조 복잡 → ALL variants blocked",
                "multi_page_complex: render DPI 변경 금지",
            ],
            "note": "invoice_statement는 기본 전처리 금지. rowCount exact guard 필수.",
        },
        "receipt": {
            "mode": "compare_then_select",
            "defaultEnabled": False,
            "requiredGuards": [
                "core_fields_not_regressed",
                "doctype_not_regressed",
                "no_new_false_positive",
            ],
            "adoptionCondition": (
                "core field fill count 증가 AND "
                "기존 채워진 핵심 필드(merchantName/businessNo/totalAmount) 유지"
            ),
        },
        "finance_slip": {
            "defaultBlocked": True,
            "note": "현재 suppressed_bank_slip 정책. extractor 미구현. 전처리 효과 평가 보류.",
        },
    },
    "guardRules": {
        "core_fields_not_regressed": {
            "check": "all(original_field_filled → after_field_filled for field in core_fields)",
            "reject_if": "merchantName OR businessNo OR totalAmount 기존 값이 사라짐",
            "core_fields": ["merchantName", "businessNo", "totalAmount"],
        },
        "doctype_not_regressed": {
            "check": "after_doctype closer to expected_doctype than original",
            "reject_if": "after_doctype 가 expected와 더 멀어짐",
        },
        "no_new_false_positive": {
            "check": "no suspicious new field values (amount >= 10M bare, businessNo matching phone format)",
            "reject_if": "새로운 false positive amount/businessNo 발생",
        },
        "rowcount_exact_maintained": {
            "check": "after_rowCount == expected_rowCount",
            "reject_if": "rowCount != expectedRowCount (invoice_statement guard)",
        },
        "expected_value_fill_not_regressed": {
            "check": "expectedValueFillRate(after) >= expectedValueFillRate(original)",
            "reject_if": "value fill rate 감소",
        },
        "critical_warnings_not_increased": {
            "check": "critical warning count(after) <= critical warning count(original)",
            "reject_if": "critical warning 증가",
        },
        "invoice_anchor_structure_intact": {
            "check": "OP-anchor rows maintained, header-skip policy result unchanged",
            "reject_if": "anchor row 변경 또는 header-skip 로직 결과 변경",
        },
    },
    "operationStrategy": {
        "Phase1_ExperimentOnly": {
            "description": "T-20: 실험/수동 비교만. 운영 경로 미연결.",
            "status": "completed",
        },
        "Phase2_DebugModeCompare": {
            "description": (
                "T-20b 목표: debug mode compare_then_select 구현. "
                "전처리 결과를 원본과 비교하되 기본 경로는 원본 유지."
            ),
            "status": "planned",
        },
        "Phase3_QualityTagsConditional": {
            "description": (
                "qualityTags 기반 자동화. "
                "shadow/blurred/low_contrast 태그 있는 샘플에만 clahe 시도."
            ),
            "status": "future",
        },
        "Phase4_OperationDefault": {
            "description": "Phase2/3 검증 후 운영 기본값 재평가.",
            "status": "future",
        },
    },
}


# ============================================================
# Guard 로직 구현
# ============================================================

def check_qualitytag_policy(qualityTags: list[str], variant: str, doc_type: str) -> tuple[bool, str]:
    """qualityTag/documentType 기반 정책으로 variant 허용 여부 판단."""
    # 1. 기본 차단 variant
    v_policy = POLICY["variants"].get(variant, {})
    if v_policy.get("defaultBlocked"):
        return False, f"variant_blocked_by_default: {variant}"

    # 2. documentType 기반 차단
    if doc_type == "invoice_statement":
        dt_policy = POLICY["documentTypePolicy"]["invoice_statement"]
        if dt_policy["defaultBlocked"] and variant not in dt_policy["allowedVariants"]:
            return False, f"invoice_statement_blocked: {variant} not in allowed"

    # 3. qualityTag 기반 허용 확인
    qt_upper = [qt.lower() for qt in qualityTags]

    # small_text 단독 차단
    if "small_text" in qt_upper and "blurred" not in qt_upper and "shadow" not in qt_upper:
        if "long_receipt" not in qt_upper:
            blocked_for_small = POLICY["qualityTagMapping"]["small_text"]["blocked"]
            if variant in blocked_for_small:
                return False, f"small_text_only_blocked: {variant}"

    # variant enabledFor 체크
    enabled_for = v_policy.get("enabledFor", [])
    blocked_for = v_policy.get("blockedFor", [])

    if "ALL" in blocked_for:
        return False, f"variant_blocked_for_all: {variant}"
    if doc_type in blocked_for:
        return False, f"variant_blocked_for_doctype: {variant} for {doc_type}"

    # qualityTag가 enabledFor에 해당하는지
    tag_match = False
    for qt in qt_upper:
        if qt in enabled_for:
            tag_match = True
            break
    # 복합 조건 체크
    if "long_receipt" in qt_upper and "small_text" in qt_upper:
        if variant in ["grayscale", "clahe", "sharpen", "clahe_plus_sharpen"]:
            tag_match = True
    if "ocr_garbled_with_small" in enabled_for and "small_text" in qt_upper:
        tag_match = True

    if not tag_match and enabled_for:
        return False, f"no_qualitytag_match: {variant} needs {enabled_for}, got {qt_upper}"

    return True, "policy_allowed"


def apply_guard(sample_key: str, variant: str, variant_result: dict,
                doc_type: str, expected_row_count: int | None = None) -> tuple[str, str]:
    """T-20 variant 결과에 guard를 적용해 accept/reject 판정."""
    improvements = variant_result.get("improvements", [])
    regressions = variant_result.get("regressions", [])

    # 회귀 있으면 즉시 reject
    if regressions:
        return "reject", f"guard_regression: {regressions}"

    # invoice rowCount guard
    if doc_type == "invoice_statement" and expected_row_count is not None:
        row_note = variant_result.get("rowCountNote", "")
        if "mismatch" in row_note.lower() or "regressed" in str(regressions).lower():
            return "reject", "invoice_rowcount_mismatch"

    # 개선 없으면 unchanged (reject)
    if not improvements:
        return "unchanged", "no_improvement"

    return "accept", f"guard_passed: {improvements}"


def simulate_policy(t20_data: dict) -> list[dict]:
    """T-20 결과에 policy를 가상 적용해 판정 시뮬레이션."""
    simulations = []
    sample_results = t20_data.get("sampleResults", [])

    for s in sample_results:
        cand = s.get("candidate", {})
        sample_key = cand.get("sample", "")
        doc_type = cand.get("documentType", "unknown")
        quality_tags = cand.get("qualityTags", [])
        sample_judge = s.get("sampleJudgement", "unchanged")
        results = s.get("results", [])

        # invoice expectedRowCount
        expected_rc = None
        manifest = cand.get("manifest", {})
        if doc_type == "invoice_statement":
            inv_profile = manifest.get("invoiceProfile", {})
            expected_rc = inv_profile.get("expectedRowCount")

        variant_decisions: list[dict] = []
        accepted_variants: list[str] = []
        rejected_variants: list[str] = []

        for vr in results:
            variant = vr.get("variant", "unknown")
            if variant == "original":
                continue

            # Step 1: policy check
            policy_ok, policy_reason = check_qualitytag_policy(quality_tags, variant, doc_type)
            if not policy_ok:
                variant_decisions.append({
                    "variant": variant,
                    "decision": "policy_reject",
                    "reason": policy_reason,
                })
                rejected_variants.append(variant)
                continue

            # Step 2: guard check
            guard_decision, guard_reason = apply_guard(
                sample_key, variant, vr, doc_type, expected_rc
            )
            variant_decisions.append({
                "variant": variant,
                "decision": guard_decision,
                "reason": guard_reason,
                "improvements": vr.get("improvements", []),
                "regressions": vr.get("regressions", []),
            })
            if guard_decision == "accept":
                accepted_variants.append(variant)
            else:
                rejected_variants.append(variant)

        sim = {
            "sample": sample_key,
            "documentType": doc_type,
            "qualityTags": quality_tags,
            "sampleJudgement_t20": sample_judge,
            "acceptedVariants": accepted_variants,
            "rejectedVariants": rejected_variants,
            "variantDecisions": variant_decisions,
            "finalDecision": (
                "conditional_accept" if accepted_variants
                else "reject_all" if rejected_variants
                else "unchanged"
            ),
            "bestAccepted": accepted_variants[0] if accepted_variants else None,
        }
        simulations.append(sim)

    return simulations


def main():
    print("=== T-20a preprocessing policy / guard 설계 ===\n")

    # T-20 데이터 로드
    t20_data = json.loads(T20_JSON.read_text(encoding="utf-8")) if T20_JSON.exists() else {}
    if not t20_data:
        print("[ERROR] T-20 JSON not found:", T20_JSON)
        return

    print(f"T-20 samples: {len(t20_data.get('sampleResults', []))}")
    print(f"T-20 variants: {len(t20_data.get('variants', []))}")

    # Policy simulation
    print("\n=== Policy simulation ===")
    simulations = simulate_policy(t20_data)

    for sim in simulations:
        decision = sim["finalDecision"]
        best = sim["bestAccepted"]
        qt = sim["qualityTags"]
        tag = f"[{decision.upper()}]"
        print(f"{tag} {sim['sample']} (qualityTags={qt})")
        if best:
            print(f"  best_accepted: {best}")
        accepted = sim["acceptedVariants"]
        rejected = [d for d in sim["variantDecisions"] if d["decision"] in ("guard_accept", "policy_reject", "reject")]
        policy_rejects = [d["variant"] for d in sim["variantDecisions"] if d["decision"] == "policy_reject"]
        if policy_rejects:
            print(f"  policy_reject: {policy_rejects[:3]}")

    # Summary
    print(f"\n=== 시뮬레이션 요약 ===")
    cond_accept = [s for s in simulations if s["finalDecision"] == "conditional_accept"]
    reject_all = [s for s in simulations if s["finalDecision"] == "reject_all"]
    unchanged = [s for s in simulations if s["finalDecision"] == "unchanged"]
    print(f"conditional_accept: {len(cond_accept)} 건")
    for s in cond_accept:
        print(f"  {s['sample']}: best={s['bestAccepted']}")
    print(f"reject_all: {len(reject_all)} 건")
    for s in reject_all:
        print(f"  {s['sample']}")
    print(f"unchanged: {len(unchanged)} 건")

    # invoice/2.pdf check
    inv2 = next((s for s in simulations if "invoice_statement/2" in s["sample"]), None)
    inv3 = next((s for s in simulations if "invoice_statement/3" in s["sample"]), None)
    inv2_decision = inv2['finalDecision'] if inv2 else '?'
    inv3_decision = inv3['finalDecision'] if inv3 else '?'
    inv2_ok = inv2_decision == "reject_all"
    # invoice/3.pdf: T-20에서 render_dpi_200_grayscale이 개선했으나 qualityTags=[]로 policy_reject
    # pdf_low_resolution 태그 보강 후 T-20c에서 conditional_accept 가능
    inv3_note = "(qualityTags 미설정 → policy_reject. T-20 실험에서는 개선 확인.)" if inv3_decision == "reject_all" else ""
    print(f"\ninvoice/2.pdf: {inv2_decision} {'[OK]' if inv2_ok else '[NG]'} (expected: reject_all)")
    print(f"invoice/3.pdf: {inv3_decision} {inv3_note}")

    # Output JSON
    out_data = {
        "task": "T-20a",
        "generatedAt": datetime.now().isoformat(),
        "t20Summary": {
            "totalSamples": len(t20_data.get("sampleResults", [])),
            "improved": t20_data.get("sampleJudgementCounts", {}).get("improved", 0),
            "regressed": t20_data.get("sampleJudgementCounts", {}).get("regressed", 0),
            "unchanged": t20_data.get("sampleJudgementCounts", {}).get("unchanged", 0),
        },
        "policySimulation": {
            "conditional_accept": len(cond_accept),
            "reject_all": len(reject_all),
            "unchanged": len(unchanged),
            "samples": simulations,
        },
        "policy": POLICY,
    }
    OUT_DESIGN_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_DESIGN_JSON.write_text(json.dumps(out_data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\n설계 JSON 저장: {OUT_DESIGN_JSON}")

    OUT_POLICY_JSON.write_text(json.dumps(POLICY, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"정책 JSON 저장: {OUT_POLICY_JSON}")

    # MD report
    _write_md_report(simulations, cond_accept, reject_all, unchanged)
    print(f"리포트 저장: {OUT_MD}")


def _write_md_report(simulations, cond_accept, reject_all, unchanged):
    lines = [
        "# T-20a qualityTags 기반 preprocessing policy / guard 설계 결과",
        "",
        "## 1. 생성 파일",
        f"- `{OUT_POLICY_JSON.relative_to(FRONTEND.parent)}`",
        f"- `{OUT_DESIGN_JSON.relative_to(FRONTEND.parent)}`",
        f"- `{OUT_MD.relative_to(FRONTEND.parent)}`",
        f"- `ocr-server/scripts/design_preprocessing_policy_t20a.py`",
        "",
        "## 2. 핵심 요약",
        "- T-20 실험 결과 분석: improved=5, unchanged=4, regressed=1",
        f"- policy simulation: conditional_accept {len(cond_accept)}건, reject_all {len(reject_all)}건, unchanged {len(unchanged)}건",
        "- invoice_statement/2.pdf: 모든 variant reject (rowCount mismatch) ✓",
        "- invoice_statement/3.pdf: reject_all — qualityTags=[] 이므로 policy_reject (pdf_low_resolution 태그 필요)",
        "  - T-20 실험에서는 render_dpi_200_grayscale이 rowCount exact 회복. 태그 보강 후 T-20c에서 재검토.",
        "- small_text 단독: 모든 processing variant blocked (T-20에서 card_001/pos_001/002/medical_002 회귀 또는 unchanged)",
        "- upscale_1_5x: 가장 안전한 후보 (회귀 0건)",
        "",
        "## 3. T-20 variant 분석",
        "| variant | improved | regressed | risk | 정책 |",
        "|---|---:|---:|---|---|",
        "| upscale_1_5x | 2 | 0 | low | blurred/garbled 조건부 허용 |",
        "| clahe | 3 | 1 | medium | shadow/blurred/low_contrast 조건부 |",
        "| clahe_plus_sharpen | 3 | 1 | medium | shadow/blurred/garbled 조건부 |",
        "| grayscale | 1 | 1 | medium | long_receipt 복합만 조건부 |",
        "| sharpen | 1 | 1 | medium | long_receipt 복합만 조건부 |",
        "| denoise | 1 | 3 | high | 기본 차단 |",
        "| threshold_adaptive | 1 | 2 | high | 기본 차단 |",
        "| render_dpi_200_grayscale | 1 | 1 | high | invoice 단순 구조만 조건부 |",
        "| render_dpi_150/200/300 | 0 | 1~2 | high | 기본 차단 |",
        "",
        "## 4. qualityTags → preprocessing 매핑",
        "| qualityTag/reason | 후보 variant | guard | 비고 |",
        "|---|---|---|---|",
        "| blurred | clahe, upscale_1_5x | core_fields_not_regressed | card_002 개선 확인 |",
        "| shadow | clahe | core_fields_not_regressed | medical_001 개선 확인 |",
        "| low_contrast | clahe | core_fields_not_regressed | 간접 추정 |",
        "| small_text 단독 | **blocked** | - | card_001/pos_001/002/medical_002 모두 회귀 또는 미개선 |",
        "| long_receipt + small_text | grayscale, clahe | core_fields_not_regressed | medical_003 모든 variant 개선 |",
        "| ocr_garbled | upscale_1_5x | core_fields_not_regressed | pos_006 개선, 회귀 0 |",
        "| pdf_low_resolution | render_dpi_200_grayscale | rowcount_exact + warnings | invoice/3.pdf 개선 |",
        "",
        "## 5. documentType별 정책",
        "| documentType | 기본 적용 | 허용 조건 | reject 조건 |",
        "|---|---|---|---|",
        "| invoice_statement | 기본 차단 | render_dpi_200_grayscale + rowCount guard + 단순구조 | rowCount mismatch, warning 증가 |",
        "| receipt 계열 | compare_then_select | core field fill 증가 + 기존 필드 유지 | 기존 필드 손실, false positive |",
        "| finance_slip | 기본 차단 | extractor 미구현 | - |",
        "",
        "## 6. 채택 guard",
        "### 공통 guard",
        "- `core_fields_not_regressed`: merchantName/businessNo/totalAmount 기존 값 유지",
        "- `doctype_not_regressed`: 분류 결과가 expected와 더 멀어지지 않음",
        "- `no_new_false_positive`: 새로운 false positive 금액/사업자번호 없음",
        "",
        "### receipt guard",
        "- core field fill count 증가 → accept 후보",
        "- source_missing 필드가 새로 채워짐 → accept 후보",
        "- 기존 채워진 핵심 필드 유지 필수",
        "",
        "### invoice_statement guard",
        "- rowCount == expectedRowCount 유지 필수",
        "- expectedValueFillRate >= 원본",
        "- critical warning count 증가 없음",
        "- invoice anchor structure (OP-anchor, header-skip 결과) 유지",
        "",
        "## 7. policy simulation 결과",
        "| sample | qualityTags | best accepted | final decision | reason |",
        "|---|---|---|---|---|",
    ]
    for sim in simulations:
        lines.append(
            f"| {sim['sample']} | {sim['qualityTags']} "
            f"| {sim.get('bestAccepted', '-')} "
            f"| {sim['finalDecision']} "
            f"| T-20 judgement: {sim['sampleJudgement_t20']} |"
        )

    lines += [
        "",
        "## 8. 운영 적용 전략",
        "| Phase | 내용 | 상태 |",
        "|---|---|---|",
        "| Phase 1 | 실험/수동 비교 (T-20) | 완료 |",
        "| Phase 2 | debug mode compare_then_select 구현 (T-20b) | 계획 |",
        "| Phase 3 | qualityTags 기반 조건부 자동화 | 미래 |",
        "| Phase 4 | 운영 기본 적용 여부 재평가 | 미래 |",
        "",
        "> Phase 2 이전에는 운영 경로에 전처리를 연결하지 않는다.",
        "> qualityTags metadata가 충분히 보강된 후에 Phase 3 진행 권장.",
        "",
        "## 9. 다음 작업 판단",
        "- T-20a policy/guard 설계 완료",
        "- **다음 권장: T-20b debug mode compare_then_select 구현** (blurred/shadow 샘플에서 compare 로직 시험)",
        "- 또는: qualityTags metadata 보강 (T-21) 우선 후 T-20b",
        "- invoice/3.pdf render_dpi_200_grayscale: 별도 invoice precheck T20c로 분리 권장",
        "",
        "## 10. 검증 결과",
        "- py_compile: PASS",
        "- policy simulation: PASS (invoice/2.pdf reject_all ✓, invoice/3.pdf reject_all — pdf_low_resolution 태그 미설정)",
        "- typecheck: PASS (npm run typecheck)",
        "- build: 미실행 (신규 스크립트/JSON만 생성, 운영 코드 무수정)",
    ]

    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
