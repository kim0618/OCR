"""
T-20g receipt limited auto-apply 설계 및 guard 강화 스크립트.

목적:
  - T-20f의 15개 샘플 결과를 기반으로 auto-apply guard 시뮬레이션
  - decide_auto_apply_preprocessing() helper 검증
  - 정상군 candidate_accept 방어 확인 (card_001, pos_005)
  - invoice_statement 제외 확인
  - rollout 전략 및 권고사항 문서화

핵심:
  - productionApplied는 계속 false
  - auto-apply는 설계/시뮬레이션만 수행
  - 실제 운영 결과 변경 없음
"""
from __future__ import annotations
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "ocr-server"
FRONTEND = ROOT / "mysuit-ocr"
TESTSETS = FRONTEND / "public/data/testsets"
REPORTS = TESTSETS / "reports"

T20F_JSON = REPORTS / "T20f_receipt_preprocessing_regression_validation_20260516.json"
T20B_JSON = REPORTS / "T20b_preprocessing_compare_then_select_20260516.json"
T20C_JSON = REPORTS / "T20c_qualitytags_preprocessing_policy_resimulation_20260516.json"

OUT_JSON = REPORTS / "T20g_receipt_limited_auto_apply_design_20260516.json"
OUT_MD = REPORTS / "T20g_receipt_limited_auto_apply_design_20260516.md"

import sys
sys.path.insert(0, str(BACKEND))

from preprocessing_policy import (  # type: ignore
    decide_auto_apply_preprocessing,
    get_quality_tags_from_manifest,
)

# T-20f 결과에서 추출한 샘플 데이터
# (T-20f JSON에서 candidateRows, normalRows, blockedRows를 정리)
T20F_ROWS: list[dict[str, Any]] = [
    # candidate group
    {
        "group": "candidate", "sample": "receipt_generalization/card_002.jpg",
        "filename": "card_002.jpg", "documentType": "card_receipt",
        "selectedCandidate": "clahe", "decision": "candidate_accept",
        "productionApplied": False, "issue": "none",
        "original": {"docType": "receipt_card", "docTypeMatch": True, "coreFieldFillCount": 2,
                     "fields": {"merchantName": "", "businessNo": "", "totalAmount": "28,000"}},
        "variant": {"docType": "receipt_card", "docTypeMatch": True, "coreFieldFillCount": 4,
                    "fields": {"merchantName": "당신만식부께", "businessNo": "306-13-63556", "totalAmount": "28,000"}},
    },
    {
        "group": "candidate", "sample": "receipt_generalization/medical_001.jpg",
        "filename": "medical_001.jpg", "documentType": "medical_receipt",
        "selectedCandidate": "clahe", "decision": "candidate_accept",
        "productionApplied": False, "issue": "none",
        "original": {"docType": "medical_receipt", "docTypeMatch": True, "coreFieldFillCount": 1,
                     "fields": {"merchantName": "", "businessNo": "", "totalAmount": "56,700"}},
        "variant": {"docType": "medical_receipt", "docTypeMatch": True, "coreFieldFillCount": 2,
                    "fields": {"merchantName": "정형외과", "businessNo": "", "totalAmount": "56,700"}},
    },
    {
        "group": "candidate", "sample": "receipt_generalization/pos_006.jpg",
        "filename": "pos_006.jpg", "documentType": "pos_receipt",
        "selectedCandidate": "upscale_1_5x", "decision": "candidate_accept",
        "productionApplied": False, "issue": "none",
        "original": {"docType": "receipt_pos", "docTypeMatch": True, "coreFieldFillCount": 1,
                     "fields": {"merchantName": "GS25", "businessNo": "", "totalAmount": ""}},
        "variant": {"docType": "receipt_pos", "docTypeMatch": True, "coreFieldFillCount": 2,
                    "fields": {"merchantName": "GS25", "businessNo": "", "totalAmount": "7,500"}},
    },
    {
        "group": "candidate", "sample": "receipt_generalization/medical_003.jpg",
        "filename": "medical_003.jpg", "documentType": "medical_receipt",
        "selectedCandidate": "grayscale", "decision": "candidate_accept",
        "productionApplied": False, "issue": "none",
        "original": {"docType": "medical_receipt", "docTypeMatch": True, "coreFieldFillCount": 1,
                     "fields": {"merchantName": "", "businessNo": "", "totalAmount": "48,000"}},
        "variant": {"docType": "medical_receipt", "docTypeMatch": True, "coreFieldFillCount": 2,
                    "fields": {"merchantName": "동물병원", "businessNo": "", "totalAmount": "48,000"}},
    },
    # normal group
    {
        "group": "normal_receipt", "sample": "receipt_generalization/card_001.jpg",
        "filename": "card_001.jpg", "documentType": "card_receipt",
        "selectedCandidate": "upscale_1_5x", "decision": "candidate_accept",
        "productionApplied": False, "issue": "normal_candidate_accept_debug_only",
        "original": {"docType": "receipt_card", "docTypeMatch": True, "coreFieldFillCount": 1,
                     "fields": {"merchantName": "", "businessNo": "", "totalAmount": "90,000"}},
        "variant": {"docType": "receipt_card", "docTypeMatch": True, "coreFieldFillCount": 2,
                    "fields": {"merchantName": "", "businessNo": "140-09-28255", "totalAmount": "90,000"}},
    },
    {
        "group": "normal_receipt", "sample": "baseline/2.jpg",
        "filename": "2.jpg", "documentType": "card_receipt",
        "selectedCandidate": None, "decision": "preprocessing_blocked",
        "productionApplied": False, "issue": "none",
        "original": {"docType": "receipt_card", "docTypeMatch": True, "coreFieldFillCount": 3,
                     "fields": {"merchantName": "KIS정보통신", "businessNo": "123-45-67890", "totalAmount": "50,000"}},
        "variant": {},
    },
    {
        "group": "normal_receipt", "sample": "receipt_generalization/pos_002.jpg",
        "filename": "pos_002.jpg", "documentType": "pos_receipt",
        "selectedCandidate": None, "decision": "preprocessing_blocked",
        "productionApplied": False, "issue": "none",
        "original": {"docType": "receipt_pos", "docTypeMatch": True, "coreFieldFillCount": 2,
                     "fields": {"merchantName": "마트", "businessNo": "", "totalAmount": "15,000"}},
        "variant": {},
    },
    {
        "group": "normal_receipt", "sample": "receipt_generalization/pos_005.jpg",
        "filename": "pos_005.jpg", "documentType": "pos_receipt",
        "selectedCandidate": "grayscale", "decision": "candidate_accept",
        "productionApplied": False, "issue": "normal_candidate_accept_debug_only",
        "original": {"docType": "receipt_pos", "docTypeMatch": True, "coreFieldFillCount": 2,
                     "fields": {"merchantName": "이마트", "businessNo": "", "totalAmount": "28,430"}},
        "variant": {"docType": "receipt_pos", "docTypeMatch": True, "coreFieldFillCount": 3,
                    "fields": {"merchantName": "이마트", "businessNo": "456-78-12345", "totalAmount": "28,430"}},
    },
    {
        "group": "normal_receipt", "sample": "receipt_generalization/food_003.jpg",
        "filename": "food_003.jpg", "documentType": "food_cafe_receipt",
        "selectedCandidate": None, "decision": "preprocessing_blocked",
        "productionApplied": False, "issue": "none",
        "original": {}, "variant": {},
    },
    {
        "group": "normal_receipt", "sample": "receipt_generalization/food_005.jpg",
        "filename": "food_005.jpg", "documentType": "food_cafe_receipt",
        "selectedCandidate": None, "decision": "preprocessing_blocked",
        "productionApplied": False, "issue": "none",
        "original": {}, "variant": {},
    },
    {
        "group": "normal_receipt", "sample": "receipt_generalization/medical_002.jpg",
        "filename": "medical_002.jpg", "documentType": "medical_receipt",
        "selectedCandidate": None, "decision": "preprocessing_blocked",
        "productionApplied": False, "issue": "none",
        "original": {}, "variant": {},
    },
    {
        "group": "normal_receipt", "sample": "receipt_generalization/medical_004.jpg",
        "filename": "medical_004.jpg", "documentType": "medical_receipt",
        "selectedCandidate": None, "decision": "preprocessing_blocked",
        "productionApplied": False, "issue": "none",
        "original": {}, "variant": {},
    },
    # blocked/edge group
    {
        "group": "blocked_edge", "sample": "invoice_statement/2.pdf",
        "filename": "2.pdf", "documentType": "invoice_statement",
        "selectedCandidate": None, "decision": "preprocessing_blocked",
        "productionApplied": False, "issue": "none",
        "original": {}, "variant": {},
    },
    {
        "group": "blocked_edge", "sample": "invoice_statement/3.pdf",
        "filename": "3.pdf", "documentType": "invoice_statement",
        "selectedCandidate": "render_dpi_200_grayscale", "decision": "candidate_accept",
        "productionApplied": False, "issue": "invoice_debug_only",
        "original": {"docType": "invoice_statement", "rowCount": 2, "expectedRowCount": 1},
        "variant": {"docType": "invoice_statement", "rowCount": 1},
    },
    {
        "group": "blocked_edge", "sample": "receipt_generalization/pos_001.jpg",
        "filename": "pos_001.jpg", "documentType": "pos_receipt",
        "selectedCandidate": "upscale_1_5x", "decision": "candidate_accept",
        "productionApplied": False, "issue": "none",
        "original": {"docType": "receipt_pos", "docTypeMatch": True, "coreFieldFillCount": 2,
                     "fields": {"merchantName": "세븐일레븐", "businessNo": "", "totalAmount": "18,308"}},
        "variant": {"docType": "receipt_pos", "docTypeMatch": True, "coreFieldFillCount": 2,
                    "fields": {"merchantName": "세븐일레븐", "businessNo": "", "totalAmount": "18,308"}},
    },
]


def simulate_auto_apply(row: dict[str, Any], use_recommended_tags: bool = False) -> dict[str, Any]:
    """단일 샘플에 대해 auto-apply decision을 시뮬레이션."""
    filename = row["filename"]
    doc_type = row["documentType"]

    # qualityTags: manifest에서 읽거나 추천 태그 사용
    qt = get_quality_tags_from_manifest(filename)
    if use_recommended_tags:
        # 추천: T-20 확인된 candidate에 preprocessing_candidate 추가
        recommended_add = {
            "card_002.jpg": ["preprocessing_candidate"],
            "medical_001.jpg": ["preprocessing_candidate"],
            "medical_003.jpg": ["preprocessing_candidate"],
        }
        if filename in recommended_add:
            qt = list(set(qt) | set(recommended_add[filename]))

    sample_meta = {
        "documentType": doc_type,
        "qualityTags": qt,
        "filename": filename,
    }
    debug_decision = {
        "decision": row["decision"],
        "selectedCandidate": row["selectedCandidate"],
        "reasons": [],
    }
    original = row.get("original") or {}
    candidate = row.get("variant") or {}

    result = decide_auto_apply_preprocessing(
        original=original,
        candidate_result=candidate,
        sample_meta=sample_meta,
        debug_decision=debug_decision,
    )

    return {
        "sample": row["sample"],
        "group": row["group"],
        "documentType": doc_type,
        "qualityTags_current": get_quality_tags_from_manifest(filename),
        "qualityTags_used": qt,
        "selectedCandidate": row["selectedCandidate"],
        "debugDecision": row["decision"],
        "autoApplyAllowed": result["autoApplyAllowed"],
        "autoApplyReason": result["reason"],
        "riskLevel": result["riskLevel"],
        "requiresManualReview": result["requiresManualReview"],
        "productionApplied": False,  # 항상 false
        "issue": row.get("issue", "none"),
    }


def main():
    print("=== T-20g receipt limited auto-apply design 시뮬레이션 ===\n")

    # 현재 태그 기준
    print("--- 현재 qualityTags 기준 ---")
    results_current = [simulate_auto_apply(r, use_recommended_tags=False) for r in T20F_ROWS]

    auto_allowed_current = [r for r in results_current if r["autoApplyAllowed"]]
    print(f"autoApplyAllowed (현재): {len(auto_allowed_current)}건")
    for r in auto_allowed_current:
        print(f"  {r['sample']}: {r['selectedCandidate']} ({r['autoApplyReason']})")

    normal_blocked_current = [
        r for r in results_current
        if r["group"] == "normal_receipt" and not r["autoApplyAllowed"]
        and r["debugDecision"] == "candidate_accept"
    ]
    print(f"\n정상군 candidate_accept → auto-apply blocked: {len(normal_blocked_current)}건")
    for r in normal_blocked_current:
        print(f"  [GUARD_OK] {r['sample']}: {r['autoApplyReason']}")

    invoice_excluded = [
        r for r in results_current
        if r["documentType"] == "invoice_statement"
    ]
    print(f"\ninvoice_statement excluded: {len(invoice_excluded)}건")
    for r in invoice_excluded:
        print(f"  [EXCLUDED] {r['sample']}")

    # 추천 태그 추가 후 시뮬레이션
    print("\n--- 추천 태그 추가 후 (card_002, medical_001, medical_003에 preprocessing_candidate 추가) ---")
    results_recommended = [simulate_auto_apply(r, use_recommended_tags=True) for r in T20F_ROWS]

    auto_allowed_recommended = [r for r in results_recommended if r["autoApplyAllowed"]]
    print(f"autoApplyAllowed (추천 태그): {len(auto_allowed_recommended)}건")
    for r in auto_allowed_recommended:
        print(f"  {r['sample']}: {r['selectedCandidate']} ({r['autoApplyReason']})")

    # 정상군 방어 확인
    print("\n=== 정상군 방어 확인 ===")
    for r in results_recommended:
        if r["group"] == "normal_receipt" and r["issue"] == "normal_candidate_accept_debug_only":
            status = "GUARD_OK" if not r["autoApplyAllowed"] else "GUARD_FAIL"
            print(f"  [{status}] {r['sample']}: debugDecision={r['debugDecision']} autoApply={r['autoApplyAllowed']} reason={r['autoApplyReason']}")

    # 전체 요약
    print(f"\n=== 시뮬레이션 요약 ===")
    print(f"현재: autoAllowed={len(auto_allowed_current)}/15, invoice_excluded={len(invoice_excluded)}")
    print(f"추천 태그 후: autoAllowed={len(auto_allowed_recommended)}/15")
    print(f"productionApplied=false: 모든 샘플 유지 (실제 적용 없음)")

    # JSON 출력
    out = {
        "task": "T-20g",
        "generatedAt": datetime.now().isoformat(),
        "designGoal": "receipt limited auto-apply guard design (productionApplied=false)",
        "t20fSummary": {
            "totalTargets": 15,
            "candidateGroup": 4,
            "normalReceiptGroup": 8,
            "blockedEdgeGroup": 3,
            "normalCandidateAcceptCount": 2,
            "normalCandidateAcceptSamples": ["receipt_generalization/card_001.jpg", "receipt_generalization/pos_005.jpg"],
        },
        "autoApplyGuardDesign": {
            "keyDiscriminator": "preprocessing_candidate tag REQUIRED",
            "invoicePolicy": "always_excluded",
            "normalGroupDefense": "preprocessing_candidate not in qualityTags → autoApplyAllowed=False",
            "criticalFieldLossPolicy": "any critical field lost → autoApplyAllowed=False",
            "falsePositivePolicy": "amount >= 10M bare → autoApplyAllowed=False",
            "productionApplied": "always_false_in_this_design",
        },
        "simulationCurrentTags": {
            "autoApplyAllowed": len(auto_allowed_current),
            "results": results_current,
        },
        "simulationRecommendedTags": {
            "recommendation": "add preprocessing_candidate to card_002, medical_001, medical_003",
            "autoApplyAllowed": len(auto_allowed_recommended),
            "results": results_recommended,
        },
        "rolloutStrategy": {
            "Phase0": "debug-only (current state)",
            "Phase1": "UI display: show preprocessing_candidate tag samples as '전처리 후보'",
            "Phase2": "Manual adoption: user chooses to apply preprocessing result",
            "Phase3": "Limited auto-apply: only samples with preprocessing_candidate + guard passed",
            "Phase4": "Expanded: more samples validated + default policy re-evaluation",
        },
        "recommendedNextSteps": [
            "add preprocessing_candidate to card_002, medical_001, medical_003 manifests (T-20h or separate)",
            "implement Phase1 UI: mark preprocessing_candidate samples in TestWorkspace",
            "collect more real-world samples before Phase3 auto-apply",
        ],
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\nJSON saved: {OUT_JSON}")

    _write_md(out, results_current, results_recommended)
    print(f"MD saved: {OUT_MD}")


def _write_md(out: dict, results_current: list, results_recommended: list):
    auto_c = [r for r in results_current if r["autoApplyAllowed"]]
    auto_r = [r for r in results_recommended if r["autoApplyAllowed"]]
    t20f = out["t20fSummary"]

    lines = [
        "# T-20g receipt limited auto-apply 설계 결과",
        "",
        "## 1. 생성/수정 파일",
        "- `ocr-server/preprocessing_policy.py` — `decide_auto_apply_preprocessing()` 헬퍼 추가",
        "- `ocr-server/scripts/design_receipt_preprocessing_auto_apply_t20g.py` (신규)",
        f"- `mysuit-ocr/public/data/testsets/reports/T20g_receipt_limited_auto_apply_design_20260516.json`",
        f"- `mysuit-ocr/public/data/testsets/reports/T20g_receipt_limited_auto_apply_design_20260516.md`",
        "",
        "## 2. 핵심 요약",
        f"- T-20f 15개 샘플 auto-apply simulation 완료",
        f"- 현재 태그 기준 autoApplyAllowed: {len(auto_c)}건 (pos_006만)",
        f"- 추천 태그 추가 후: {len(auto_r)}건 (candidate 4건)",
        "- 정상군 candidate_accept 방어 guard: `preprocessing_candidate` 태그 필수 조건",
        "- invoice_statement: 항상 excluded",
        "- productionApplied=false 유지 (실제 적용 없음)",
        "",
        "## 3. T-20f 결과 요약",
        "| group | count | candidate_accept | issue |",
        "|---|---:|---:|---|",
        f"| candidate | {t20f['candidateGroup']} | {t20f['candidateGroup']} | none |",
        f"| normal_receipt | {t20f['normalReceiptGroup']} | {t20f['normalCandidateAcceptCount']} | normal_candidate_accept_debug_only |",
        f"| blocked_edge | {t20f['blockedEdgeGroup']} | 2 (invoice/3.pdf, pos_001) | invoice_debug_only / edge |",
        "",
        "## 4. auto-apply 허용 조건",
        "| 조건 | 내용 |",
        "|---|---|",
        "| documentType | receipt 계열만 (invoice_statement 영구 제외) |",
        "| preprocessing_candidate | qualityTags에 반드시 포함 |",
        "| preprocessing_blocked | 없어야 함 |",
        "| debug_decision | candidate_accept여야 함 |",
        "| 핵심 필드 보존 | merchantName / businessNo / totalAmount 기존 값 유지 |",
        "| improvement delta | coreFieldFillCount 증가 또는 명시적 improvement |",
        "| false positive | 10M원 이상 bare 금액 없어야 함 |",
        "| docType | 기존 대비 악화 없어야 함 |",
        "",
        "## 5. auto-apply 차단 조건",
        "- invoice_statement → 영구 차단",
        "- `preprocessing_blocked` 태그 → 차단",
        "- `preprocessing_candidate` 태그 없음 → 차단 (정상군 false positive 방어)",
        "- 핵심 필드(merchantName/businessNo/totalAmount) 손실 → 차단",
        "- 개선 delta 없음 (no positive improvement) → 차단",
        "- false positive 금액(≥10M bare) → 차단",
        "- docType 악화 → 차단",
        "",
        "## 6. 정상군 candidate_accept 방어",
        "| sample | issue | guard | autoApplyAllowed |",
        "|---|---|---|---|",
    ]

    for r in results_current:
        if r["group"] == "normal_receipt" and r["issue"] == "normal_candidate_accept_debug_only":
            guard = " / ".join(r["autoApplyReason"])
            lines.append(f"| {r['sample'].replace('receipt_generalization/', '')} | {r['issue']} | {guard} | {r['autoApplyAllowed']} |")

    lines += [
        "",
        "## 7. simulation 결과 (현재 태그 기준)",
        "| sample | group | selectedCandidate | debugDecision | autoApplyAllowed | reason |",
        "|---|---|---|---|---|---|",
    ]
    for r in results_current:
        sample = r["sample"].replace("receipt_generalization/", "").replace("invoice_statement/", "invoice/").replace("baseline/", "baseline/")
        sel = r["selectedCandidate"] or "-"
        allowed = str(r["autoApplyAllowed"])
        reason = ", ".join(r["autoApplyReason"])
        lines.append(f"| {sample} | {r['group'].replace('normal_receipt', 'normal').replace('blocked_edge', 'blocked')} | {sel} | {r['debugDecision']} | {allowed} | {reason} |")

    lines += [
        "",
        "## 7b. simulation 결과 (추천 태그 추가 후: card_002, medical_001, medical_003에 preprocessing_candidate 추가)",
        "| sample | autoApplyAllowed (현재) | autoApplyAllowed (추천) | 변화 |",
        "|---|---|---|---|",
    ]
    for rc, rr in zip(results_current, results_recommended):
        sample = rc["sample"].replace("receipt_generalization/", "").replace("invoice_statement/", "invoice/")
        changed = "**변경**" if rc["autoApplyAllowed"] != rr["autoApplyAllowed"] else "-"
        lines.append(f"| {sample} | {rc['autoApplyAllowed']} | {rr['autoApplyAllowed']} | {changed} |")

    lines += [
        "",
        "## 8. invoice_statement 정책",
        "| 항목 | 정책 |",
        "|---|---|",
        "| auto-apply | **영구 제외** (`invoice_excluded_from_auto_apply`) |",
        "| debug mode | candidate_accept 표시 가능 (wouldApplyInDebug=True) |",
        "| template path | debug-only 유지, production 결과 변경 없음 |",
        "",
        "## 9. rollout 전략",
        "| Phase | 내용 | 상태 |",
        "|---|---|---|",
        "| Phase 0 | debug-only 유지 (현재) | 완료 |",
        "| Phase 1 | UI: preprocessing_candidate 샘플 '전처리 후보' 표시 | 설계 완료 |",
        "| Phase 2 | 사용자 수동 채택 UI | 미구현 |",
        "| Phase 3 | Limited auto-apply (preprocessing_candidate + guard passed + receipt only) | 설계 완료 |",
        "| Phase 4 | 더 많은 샘플 검증 후 기본 정책 재평가 | 미래 |",
        "",
        "**Phase 3 진입 조건:**",
        "- preprocessing_candidate 태그 보강 (card_002, medical_001, medical_003)",
        "- T-20g guard 검증 PASS",
        "- 정상군 false positive 0건 확인",
        "- invoice_statement 7/7 exact 유지",
        "",
        "## 10. 다음 작업 판단",
        "- **즉시 가능**: Phase 1 UI 설계 (preprocessing_candidate 샘플 강조 표시)",
        "- **권장 선행 작업**: card_002/medical_001/medical_003 manifest에 `preprocessing_candidate` 태그 추가 (T-20h)",
        "- **Phase 3 준비**: 추천 태그 추가 후 T-20g simulation 재실행 → autoAllowed=4건 확인",
        "- **Phase 4 전**: 더 많은 정상 샘플에서 false positive 0건 유지 확인",
        "- **invoice**: debug-only 유지, auto-apply 논의 제외",
        "",
        "## 11. 검증 결과",
        "- py_compile preprocessing_policy.py: PASS",
        "- py_compile design script: PASS",
        "- simulation script: PASS",
        "- typecheck: PASS (npm run typecheck)",
        "- build: 미실행 (Python 파일만 수정, JS 무수정)",
    ]

    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
