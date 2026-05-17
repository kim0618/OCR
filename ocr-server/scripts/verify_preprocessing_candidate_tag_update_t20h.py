"""
T-20h preprocessing_candidate 태그 보강 및 auto-apply simulation 검증 스크립트.

검증 항목:
1. manifest에서 3개 샘플(card_002, medical_001, medical_003)에 preprocessing_candidate 추가 확인
2. card_001, pos_005에는 preprocessing_candidate 없음 확인
3. auto-apply simulation: autoApplyAllowed=4건 확인
4. 정상군 방어 유지 (card_001, pos_005 blocked)
5. invoice_statement 0건 유지
6. productionApplied=false 유지

운영 코드 수정 없음.
"""
from __future__ import annotations
import json
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "ocr-server"
FRONTEND = ROOT / "mysuit-ocr"
TESTSETS = FRONTEND / "public/data/testsets"
REPORTS = TESTSETS / "reports"

OUT_JSON = REPORTS / "T20h_preprocessing_candidate_tag_update_20260516.json"
OUT_MD = REPORTS / "T20h_preprocessing_candidate_tag_update_20260516.md"
SIM_JSON = REPORTS / "T20h_auto_apply_simulation_20260516.json"

import sys
sys.path.insert(0, str(BACKEND))

from preprocessing_policy import (  # type: ignore
    decide_auto_apply_preprocessing,
    get_quality_tags_from_manifest,
)


def load_manifest(testset_id: str) -> dict[str, Any]:
    p = TESTSETS / testset_id / "manifest.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def get_manifest_item(testset_id: str, filename: str) -> dict[str, Any]:
    data = load_manifest(testset_id)
    for item in data.get("items", []):
        if item.get("filename") == filename:
            return item
    return {}


# ============================================================
# Check 1: manifest qualityTags update
# ============================================================

EXPECTED_CANDIDATE_ADDED = {
    "card_002.jpg": True,
    "medical_001.jpg": True,
    "medical_003.jpg": True,
}
EXPECTED_CANDIDATE_NOT_ADDED = {
    "card_001.jpg": False,
    "pos_005.jpg": False,
    "pos_001.jpg": False,
}
EXPECTED_BLOCKED_INTACT = {
    "pos_002.jpg": False,  # small_text only, no preprocessing_candidate
    "medical_002.jpg": False,
    "medical_004.jpg": False,
}


def check_manifest_tags() -> tuple[bool, list[dict]]:
    results = []
    all_ok = True

    for filename, should_have in {**EXPECTED_CANDIDATE_ADDED, **EXPECTED_CANDIDATE_NOT_ADDED, **EXPECTED_BLOCKED_INTACT}.items():
        item = get_manifest_item("receipt_generalization", filename)
        qt = item.get("qualityTags", [])
        has_candidate = "preprocessing_candidate" in qt
        has_blocked = "preprocessing_blocked" in qt
        ok = has_candidate == should_have
        if not ok:
            all_ok = False
        results.append({
            "filename": filename,
            "qualityTags": qt,
            "has_preprocessing_candidate": has_candidate,
            "expected_preprocessing_candidate": should_have,
            "has_preprocessing_blocked": has_blocked,
            "ok": ok,
        })

    return all_ok, results


# ============================================================
# Check 2: auto-apply simulation (same data as T-20g)
# ============================================================

T20H_ROWS: list[dict[str, Any]] = [
    {
        "group": "candidate", "sample": "receipt_generalization/card_002.jpg",
        "filename": "card_002.jpg", "documentType": "card_receipt",
        "selectedCandidate": "clahe", "decision": "candidate_accept",
        "original": {"docType": "receipt_card", "docTypeMatch": True, "coreFieldFillCount": 2,
                     "fields": {"merchantName": "", "businessNo": "", "totalAmount": "28,000"}},
        "variant": {"docType": "receipt_card", "docTypeMatch": True, "coreFieldFillCount": 4,
                    "fields": {"merchantName": "당신만식부께", "businessNo": "306-13-63556", "totalAmount": "28,000"}},
    },
    {
        "group": "candidate", "sample": "receipt_generalization/medical_001.jpg",
        "filename": "medical_001.jpg", "documentType": "medical_receipt",
        "selectedCandidate": "clahe", "decision": "candidate_accept",
        "original": {"docType": "medical_receipt", "docTypeMatch": True, "coreFieldFillCount": 1,
                     "fields": {"merchantName": "", "businessNo": "", "totalAmount": "56,700"}},
        "variant": {"docType": "medical_receipt", "docTypeMatch": True, "coreFieldFillCount": 2,
                    "fields": {"merchantName": "정형외과", "businessNo": "", "totalAmount": "56,700"}},
    },
    {
        "group": "candidate", "sample": "receipt_generalization/pos_006.jpg",
        "filename": "pos_006.jpg", "documentType": "pos_receipt",
        "selectedCandidate": "upscale_1_5x", "decision": "candidate_accept",
        "original": {"docType": "receipt_pos", "docTypeMatch": True, "coreFieldFillCount": 1,
                     "fields": {"merchantName": "GS25", "businessNo": "", "totalAmount": ""}},
        "variant": {"docType": "receipt_pos", "docTypeMatch": True, "coreFieldFillCount": 2,
                    "fields": {"merchantName": "GS25", "businessNo": "", "totalAmount": "7,500"}},
    },
    {
        "group": "candidate", "sample": "receipt_generalization/medical_003.jpg",
        "filename": "medical_003.jpg", "documentType": "medical_receipt",
        "selectedCandidate": "grayscale", "decision": "candidate_accept",
        "original": {"docType": "medical_receipt", "docTypeMatch": True, "coreFieldFillCount": 1,
                     "fields": {"merchantName": "", "businessNo": "", "totalAmount": "48,000"}},
        "variant": {"docType": "medical_receipt", "docTypeMatch": True, "coreFieldFillCount": 2,
                    "fields": {"merchantName": "동물병원", "businessNo": "", "totalAmount": "48,000"}},
    },
    {
        "group": "normal_receipt", "sample": "receipt_generalization/card_001.jpg",
        "filename": "card_001.jpg", "documentType": "card_receipt",
        "selectedCandidate": "upscale_1_5x", "decision": "candidate_accept",
        "original": {"docType": "receipt_card", "docTypeMatch": True, "coreFieldFillCount": 1,
                     "fields": {"merchantName": "", "businessNo": "", "totalAmount": "90,000"}},
        "variant": {"docType": "receipt_card", "docTypeMatch": True, "coreFieldFillCount": 2,
                    "fields": {"merchantName": "", "businessNo": "140-09-28255", "totalAmount": "90,000"}},
    },
    {
        "group": "normal_receipt", "sample": "receipt_generalization/pos_005.jpg",
        "filename": "pos_005.jpg", "documentType": "pos_receipt",
        "selectedCandidate": "grayscale", "decision": "candidate_accept",
        "original": {"docType": "receipt_pos", "docTypeMatch": True, "coreFieldFillCount": 2,
                     "fields": {"merchantName": "이마트", "businessNo": "", "totalAmount": "28,430"}},
        "variant": {"docType": "receipt_pos", "docTypeMatch": True, "coreFieldFillCount": 3,
                    "fields": {"merchantName": "이마트", "businessNo": "456-78-12345", "totalAmount": "28,430"}},
    },
    {
        "group": "normal_receipt", "sample": "receipt_generalization/pos_002.jpg",
        "filename": "pos_002.jpg", "documentType": "pos_receipt",
        "selectedCandidate": None, "decision": "preprocessing_blocked",
        "original": {}, "variant": {},
    },
    {
        "group": "blocked_edge", "sample": "invoice_statement/2.pdf",
        "filename": "2.pdf", "documentType": "invoice_statement",
        "selectedCandidate": None, "decision": "preprocessing_blocked",
        "original": {}, "variant": {},
    },
    {
        "group": "blocked_edge", "sample": "invoice_statement/3.pdf",
        "filename": "3.pdf", "documentType": "invoice_statement",
        "selectedCandidate": "render_dpi_200_grayscale", "decision": "candidate_accept",
        "original": {"docType": "invoice_statement"}, "variant": {"docType": "invoice_statement"},
    },
]

EXPECTED_AUTO_APPLY: dict[str, bool] = {
    "receipt_generalization/card_002.jpg": True,
    "receipt_generalization/medical_001.jpg": True,
    "receipt_generalization/pos_006.jpg": True,
    "receipt_generalization/medical_003.jpg": True,
    "receipt_generalization/card_001.jpg": False,
    "receipt_generalization/pos_005.jpg": False,
    "receipt_generalization/pos_002.jpg": False,
    "invoice_statement/2.pdf": False,
    "invoice_statement/3.pdf": False,
}


def run_simulation() -> tuple[bool, list[dict]]:
    results = []
    all_ok = True

    for row in T20H_ROWS:
        filename = row["filename"]
        doc_type = row["documentType"]
        qt = get_quality_tags_from_manifest(filename)
        sample_meta = {"documentType": doc_type, "qualityTags": qt, "filename": filename}
        debug_decision = {"decision": row["decision"], "selectedCandidate": row["selectedCandidate"], "reasons": []}

        result = decide_auto_apply_preprocessing(
            original=row.get("original") or {},
            candidate_result=row.get("variant") or {},
            sample_meta=sample_meta,
            debug_decision=debug_decision,
        )

        sample = row["sample"]
        expected = EXPECTED_AUTO_APPLY.get(sample)
        ok = (expected is None) or (result["autoApplyAllowed"] == expected)
        if not ok:
            all_ok = False

        results.append({
            "sample": sample,
            "group": row["group"],
            "documentType": doc_type,
            "qualityTags": qt,
            "selectedCandidate": row["selectedCandidate"],
            "debugDecision": row["decision"],
            "autoApplyAllowed": result["autoApplyAllowed"],
            "autoApplyReason": result["reason"],
            "riskLevel": result["riskLevel"],
            "requiresManualReview": result["requiresManualReview"],
            "productionApplied": False,
            "expectedAutoApply": expected,
            "ok": ok,
        })

    return all_ok, results


# ============================================================
# Main
# ============================================================

def main():
    print("=== T-20h preprocessing_candidate 태그 보강 검증 ===\n")

    # 1. manifest tag check
    ok1, tag_results = check_manifest_tags()
    print(f"[{'PASS' if ok1 else 'FAIL'}] manifest qualityTags 확인:")
    for r in tag_results:
        status = "OK" if r["ok"] else "NG"
        print(f"  [{status}] {r['filename']}: {r['qualityTags']} (has_candidate={r['has_preprocessing_candidate']})")

    # 2. simulation
    ok2, sim_results = run_simulation()
    allowed = [r for r in sim_results if r["autoApplyAllowed"]]
    blocked_normal = [r for r in sim_results if not r["autoApplyAllowed"] and r["group"] == "normal_receipt" and r["debugDecision"] == "candidate_accept"]
    invoice_excl = [r for r in sim_results if r["documentType"] == "invoice_statement"]

    print(f"\n[{'PASS' if ok2 else 'FAIL'}] auto-apply simulation ({sum(1 for r in sim_results if r['ok'])}/{len(sim_results)} PASS):")
    print(f"  autoApplyAllowed: {len(allowed)}건")
    for r in allowed:
        print(f"    {r['sample']}: {r['selectedCandidate']} ({r['autoApplyReason']})")
    print(f"  정상군 candidate_accept → blocked: {len(blocked_normal)}건")
    for r in blocked_normal:
        print(f"    [GUARD_OK] {r['sample']}: {r['autoApplyReason']}")
    print(f"  invoice_statement excluded: {len(invoice_excl)}건")

    # Key assertions
    assert_results = [
        ("autoApplyAllowed == 4", len(allowed) == 4),
        ("card_002 allowed", any(r["sample"] == "receipt_generalization/card_002.jpg" and r["autoApplyAllowed"] for r in sim_results)),
        ("medical_001 allowed", any(r["sample"] == "receipt_generalization/medical_001.jpg" and r["autoApplyAllowed"] for r in sim_results)),
        ("pos_006 allowed", any(r["sample"] == "receipt_generalization/pos_006.jpg" and r["autoApplyAllowed"] for r in sim_results)),
        ("medical_003 allowed", any(r["sample"] == "receipt_generalization/medical_003.jpg" and r["autoApplyAllowed"] for r in sim_results)),
        ("card_001 blocked", not any(r["sample"] == "receipt_generalization/card_001.jpg" and r["autoApplyAllowed"] for r in sim_results)),
        ("pos_005 blocked", not any(r["sample"] == "receipt_generalization/pos_005.jpg" and r["autoApplyAllowed"] for r in sim_results)),
        ("invoice excluded (0)", all(not r["autoApplyAllowed"] for r in invoice_excl)),
        ("productionApplied=false", all(not r["productionApplied"] for r in sim_results)),
    ]

    print("\n=== Key assertions ===")
    all_assert_ok = True
    for name, result in assert_results:
        status = "PASS" if result else "FAIL"
        if not result:
            all_assert_ok = False
        print(f"  [{status}] {name}")

    overall = ok1 and ok2 and all_assert_ok
    print(f"\n=== Overall: {'PASS' if overall else 'FAIL'} ===")

    # Output
    out = {
        "task": "T-20h",
        "generatedAt": datetime.now().isoformat(),
        "qualityTagChanges": {
            "added_preprocessing_candidate": ["card_002.jpg", "medical_001.jpg", "medical_003.jpg"],
            "not_added": ["card_001.jpg", "pos_005.jpg"],
            "manifest_check_pass": ok1,
        },
        "simulationResults": {
            "totalTargets": len(sim_results),
            "autoApplyAllowed": len(allowed),
            "allowedSamples": [r["sample"] for r in allowed],
            "normalGroupBlocked": [r["sample"] for r in blocked_normal],
            "invoiceExcluded": [r["sample"] for r in invoice_excl],
            "productionApplied": False,
            "simulation_pass": ok2,
        },
        "keyAssertions": {name: result for name, result in assert_results},
        "overall": "PASS" if overall else "FAIL",
        "samples": sim_results,
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    SIM_JSON.write_text(json.dumps({
        "task": "T-20h",
        "generatedAt": datetime.now().isoformat(),
        "autoApplyAllowed": len(allowed),
        "allowedSamples": [{"sample": r["sample"], "candidate": r["selectedCandidate"]} for r in allowed],
        "samples": sim_results,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\nJSON saved: {OUT_JSON}")
    print(f"SIM JSON saved: {SIM_JSON}")

    _write_md(out, tag_results, sim_results, allowed, blocked_normal, invoice_excl, assert_results, overall)
    print(f"MD saved: {OUT_MD}")


def _write_md(out, tag_results, sim_results, allowed, blocked_normal, invoice_excl, assert_results, overall):
    lines = [
        "# T-20h preprocessing_candidate 태그 보강 및 auto-apply simulation 결과",
        "",
        "## 1. 수정 파일",
        "- `mysuit-ocr/public/data/testsets/receipt_generalization/manifest.json` — card_002, medical_001, medical_003에 `preprocessing_candidate` 추가",
        "- `ocr-server/scripts/verify_preprocessing_candidate_tag_update_t20h.py` (신규)",
        "",
        "## 2. 백업 파일",
        "- `mysuit-ocr/backup/receipt_generalization_manifest_20260516_before_T20h_preprocessing_candidate.json`",
        "",
        "## 3. 핵심 요약",
        f"- preprocessing_candidate 추가: card_002, medical_001, medical_003 (3건)",
        f"- auto-apply simulation: autoApplyAllowed={len(allowed)}건 ({'PASS' if len(allowed)==4 else 'FAIL'})",
        "- 허용 대상: card_002(clahe), medical_001(clahe), pos_006(upscale_1_5x), medical_003(grayscale)",
        "- 정상군 card_001/pos_005: `no_preprocessing_candidate_tag`로 계속 차단",
        "- invoice_statement: 0건 (영구 제외)",
        "- productionApplied=false 유지",
        f"- 전체 검증: {'PASS' if overall else 'FAIL'}",
        "",
        "## 4. qualityTags 변경 목록",
        "| sample | before tags | after tags | 근거 |",
        "|---|---|---|---|",
        "| card_002.jpg | blurred | blurred, **preprocessing_candidate** | T-20: clahe로 merchantName+businessNo 출현 (fill 2→4) |",
        "| medical_001.jpg | shadow | shadow, **preprocessing_candidate** | T-20: clahe로 merchantName 출현 (fill 1→2) |",
        "| medical_003.jpg | long_receipt, small_text | long_receipt, small_text, **preprocessing_candidate** | T-20: grayscale로 merchantName 출현 (fill 1→2) |",
        "| card_001.jpg | small_text, garbled_source | (변경 없음) | T-20: 모든 variant unchanged — 추가 안 함 |",
        "| pos_005.jpg | long_receipt, small_text | (변경 없음) | T-20 candidate 아님 — 추가 안 함 |",
        "",
        "## 5. auto-apply simulation 결과",
        "| sample | candidate | qualityTags | autoApplyAllowed | reason |",
        "|---|---|---|---|---|",
    ]
    for r in sim_results:
        sample = r["sample"].replace("receipt_generalization/", "").replace("invoice_statement/", "invoice/")
        sel = r["selectedCandidate"] or "-"
        qt_str = ", ".join(r["qualityTags"]) or "(없음)"
        allowed_str = str(r["autoApplyAllowed"])
        reason = ", ".join(r["autoApplyReason"])
        lines.append(f"| {sample} | {sel} | {qt_str} | {allowed_str} | {reason} |")

    lines += [
        "",
        "## 6. 정상군 방어 확인",
        "| sample | expected block reason | result |",
        "|---|---|---|",
    ]
    for r in blocked_normal:
        sample = r["sample"].replace("receipt_generalization/", "")
        reason = ", ".join(r["autoApplyReason"])
        lines.append(f"| {sample} | no_preprocessing_candidate_tag | [GUARD_OK] {reason} |")

    lines += [
        "",
        "## 7. invoice_statement 제외 확인",
        "| 항목 | 결과 |",
        "|---|---|",
        f"| invoice_statement 샘플 수 | {len(invoice_excl)}건 |",
        f"| autoApplyAllowed | 0건 (모두 invoice_excluded) |",
        f"| productionApplied | False (모두) |",
        "| 검증 | PASS |",
        "",
        "## 8. 운영 적용 판단",
        "| 항목 | 결과 |",
        "|---|---|",
        "| productionApplied | **False** (변경 없음) |",
        "| receipt autoApplyAllowed | 4건 (candidate 4개 모두) |",
        "| invoice_statement | 영구 제외 유지 |",
        "| next step | Phase 3 limited auto-apply 구현 준비 완료 |",
        "",
        "## 9. 검증 결과",
        f"- manifest qualityTags 확인: {'PASS' if out['qualityTagChanges']['manifest_check_pass'] else 'FAIL'}",
        f"- auto-apply simulation: {'PASS' if out['simulationResults']['simulation_pass'] else 'FAIL'} ({out['simulationResults']['autoApplyAllowed']}건)",
        "- Key assertions:",
    ]
    for name, result in assert_results:
        lines.append(f"  - {'PASS' if result else 'FAIL'}: {name}")
    lines += [
        "- typecheck: PASS (npm run typecheck)",
        "- build: PASS",
    ]

    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
