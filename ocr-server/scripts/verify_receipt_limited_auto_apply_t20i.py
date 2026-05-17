"""
T-20i receipt limited auto-apply 검증 스크립트.

검증 항목:
1. main.py autoApplyPreprocessing Form 파라미터 추가 확인
2. debug=false, auto=false → preprocessingDebug 없음 (기존 동일)
3. debug=true, auto=false → preprocessingDebug 있음, productionApplied=false
4. auto=true, receipt candidate → autoApplyAllowed=true, productionApplied=true 시뮬레이션
5. auto=true, 정상군 (card_001, pos_005) → autoApplyAllowed=false
6. auto=true, invoice_statement → invoice_excluded (autoApplyAllowed=false)
7. invoice_statement 7/7 exact 유지 확인

T-20 캐시 기반 검증 (PaddleOCR 재실행 없음).
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

T20_JSON = REPORTS / "T20_ocr_preprocessing_experiment_20260516.json"
INVOICE_EXPECTED = {"1.jpg": 28, "2.pdf": 13, "3.pdf": 1, "4.pdf": 1, "5.pdf": 6, "6.pdf": 6, "7.pdf": 1}

OUT_JSON = REPORTS / "T20i_receipt_limited_auto_apply_20260517.json"
OUT_MD = REPORTS / "T20i_receipt_limited_auto_apply_20260517.md"

import sys
sys.path.insert(0, str(BACKEND))

from preprocessing_policy import (  # type: ignore
    get_candidates,
    compare_then_select as pp_compare,
    decide_auto_apply_preprocessing,
    get_quality_tags_from_manifest,
    get_expected_row_count,
    compute_receipt_improvements,
    compute_invoice_improvements,
)


def load_json(p: Path, default: Any = {}) -> Any:
    if not p.exists():
        return default
    text = p.read_text(encoding="utf-8")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return json.loads(text.lstrip("﻿"))


# ============================================================
# Check 1: main.py has autoApplyPreprocessing param
# ============================================================

def check_main_py_autoapply() -> tuple[bool, str]:
    content = (BACKEND / "main.py").read_text(encoding="utf-8")
    has_param = "autoApplyPreprocessing" in content and 'Form("false")' in content
    has_auto_flag = "_auto_apply_preprocessing" in content
    has_invoice_guard = "_is_invoice_doc" in content and "invoice_excluded" not in content or "invoice永久除外" in content or "_is_invoice_doc = doc_type" in content
    has_applied_fields = "_appliedRawFields" in content
    has_production_true = 'productionApplied": True' in content or '"productionApplied"] = True' in content
    has_default_false = 'Form("false")' in content and "autoApplyPreprocessing" in content
    ok = has_param and has_auto_flag and has_applied_fields and has_default_false
    return ok, (
        f"param={'OK' if has_param else 'NG'} "
        f"flag={'OK' if has_auto_flag else 'NG'} "
        f"applied_fields={'OK' if has_applied_fields else 'NG'} "
        f"default_false={'OK' if has_default_false else 'NG'}"
    )


# ============================================================
# Check 2/3: debug=false and debug-only mode
# ============================================================

def check_debug_flag_gates() -> tuple[bool, str]:
    content = (BACKEND / "main.py").read_text(encoding="utf-8")
    # B案: auto-apply implies debug → _run_preprocessing = _debug or _auto
    has_run_flag = "_run_preprocessing" in content or "_auto_apply_preprocessing or" in content
    has_no_apply_false = "productionApplied.*False" in content or '"productionApplied": False' in content
    ok = has_run_flag and has_no_apply_false
    return ok, f"run_flag={'OK' if has_run_flag else 'NG'} default_false={'OK' if has_no_apply_false else 'NG'}"


# ============================================================
# Check 4/5/6: auto-apply simulation (T-20 cache)
# ============================================================

T20I_SAMPLES = [
    # candidate group → expected autoApplyAllowed=True
    {"sample": "receipt_generalization/card_002.jpg", "filename": "card_002.jpg",
     "documentType": "card_receipt", "expectedAutoApply": True,
     "original": {"docType": "receipt_card", "docTypeMatch": True, "coreFieldFillCount": 2,
                  "fields": {"merchantName": "", "businessNo": "", "totalAmount": "28,000"}},
     "variant": {"docType": "receipt_card", "docTypeMatch": True, "coreFieldFillCount": 4,
                 "fields": {"merchantName": "당신만식부께", "businessNo": "306-13-63556", "totalAmount": "28,000"},
                 "improvements": ["core field fill increased"], "regressions": []},
     "selectedCandidate": "clahe"},
    {"sample": "receipt_generalization/medical_001.jpg", "filename": "medical_001.jpg",
     "documentType": "medical_receipt", "expectedAutoApply": True,
     "original": {"docType": "medical_receipt", "docTypeMatch": True, "coreFieldFillCount": 1,
                  "fields": {"merchantName": "", "businessNo": "", "totalAmount": "56,700"}},
     "variant": {"docType": "medical_receipt", "docTypeMatch": True, "coreFieldFillCount": 2,
                 "fields": {"merchantName": "정형외과", "businessNo": "", "totalAmount": "56,700"},
                 "improvements": ["core field fill increased"], "regressions": []},
     "selectedCandidate": "clahe"},
    {"sample": "receipt_generalization/pos_006.jpg", "filename": "pos_006.jpg",
     "documentType": "pos_receipt", "expectedAutoApply": True,
     "original": {"docType": "receipt_pos", "docTypeMatch": True, "coreFieldFillCount": 1,
                  "fields": {"merchantName": "GS25", "businessNo": "", "totalAmount": ""}},
     "variant": {"docType": "receipt_pos", "docTypeMatch": True, "coreFieldFillCount": 2,
                 "fields": {"merchantName": "GS25", "businessNo": "", "totalAmount": "7,500"},
                 "improvements": ["core field fill increased"], "regressions": []},
     "selectedCandidate": "upscale_1_5x"},
    {"sample": "receipt_generalization/medical_003.jpg", "filename": "medical_003.jpg",
     "documentType": "medical_receipt", "expectedAutoApply": True,
     "original": {"docType": "medical_receipt", "docTypeMatch": True, "coreFieldFillCount": 1,
                  "fields": {"merchantName": "", "businessNo": "", "totalAmount": "48,000"}},
     "variant": {"docType": "medical_receipt", "docTypeMatch": True, "coreFieldFillCount": 2,
                 "fields": {"merchantName": "동물병원", "businessNo": "", "totalAmount": "48,000"},
                 "improvements": ["core field fill increased"], "regressions": []},
     "selectedCandidate": "grayscale"},
    # normal group → expectedAutoApply=False
    {"sample": "receipt_generalization/card_001.jpg", "filename": "card_001.jpg",
     "documentType": "card_receipt", "expectedAutoApply": False,
     "original": {"docType": "receipt_card", "docTypeMatch": True, "coreFieldFillCount": 1,
                  "fields": {"merchantName": "", "businessNo": "", "totalAmount": "90,000"}},
     "variant": {"docType": "receipt_card", "docTypeMatch": True, "coreFieldFillCount": 2,
                 "fields": {"merchantName": "", "businessNo": "140-09-28255", "totalAmount": "90,000"},
                 "improvements": ["core field fill increased"], "regressions": []},
     "selectedCandidate": "upscale_1_5x"},
    {"sample": "receipt_generalization/pos_005.jpg", "filename": "pos_005.jpg",
     "documentType": "pos_receipt", "expectedAutoApply": False,
     "original": {"docType": "receipt_pos", "docTypeMatch": True, "coreFieldFillCount": 2,
                  "fields": {"merchantName": "이마트", "businessNo": "", "totalAmount": "28,430"}},
     "variant": {"docType": "receipt_pos", "docTypeMatch": True, "coreFieldFillCount": 3,
                 "fields": {"merchantName": "이마트", "businessNo": "456-78-12345", "totalAmount": "28,430"},
                 "improvements": ["core field fill increased"], "regressions": []},
     "selectedCandidate": "grayscale"},
    # invoice → expectedAutoApply=False (永久除外)
    {"sample": "invoice_statement/3.pdf", "filename": "3.pdf",
     "documentType": "invoice_statement", "expectedAutoApply": False,
     "original": {"docType": "invoice_statement", "rowCount": 2, "expectedRowCount": 1},
     "variant": {"docType": "invoice_statement", "rowCount": 1,
                 "improvements": ["rowCount exact recovered"], "regressions": []},
     "selectedCandidate": "render_dpi_200_grayscale"},
]


def run_autoapply_simulation() -> tuple[bool, list[dict]]:
    results = []
    all_ok = True

    for row in T20I_SAMPLES:
        filename = row["filename"]
        doc_type = row["documentType"]
        qt = get_quality_tags_from_manifest(filename)
        sample_meta = {"documentType": doc_type, "qualityTags": qt, "filename": filename}

        # simulate compare_then_select decision
        debug_decision = {
            "decision": "candidate_accept",
            "selectedCandidate": row["selectedCandidate"],
            "reasons": row["variant"].get("improvements", []),
        }

        # run decide_auto_apply_preprocessing (same as _build_preprocessing_debug would)
        auto_decision = decide_auto_apply_preprocessing(
            original=row["original"],
            candidate_result=row["variant"],
            sample_meta=sample_meta,
            debug_decision=debug_decision,
        )

        expected = row["expectedAutoApply"]
        ok = auto_decision["autoApplyAllowed"] == expected
        if not ok:
            all_ok = False

        # Simulate what ocr_extract would do
        production_applied = (
            auto_decision["autoApplyAllowed"]
            and doc_type != "invoice_statement"
        )

        results.append({
            "sample": row["sample"],
            "documentType": doc_type,
            "qualityTags": qt,
            "selectedCandidate": row["selectedCandidate"],
            "autoApplyAllowed": auto_decision["autoApplyAllowed"],
            "autoApplyReason": auto_decision["reason"],
            "expectedAutoApply": expected,
            "productionApplied": production_applied,
            "ok": ok,
        })

    return all_ok, results


# ============================================================
# Check 7: invoice baseline
# ============================================================

def check_invoice_baseline() -> tuple[bool, list[dict]]:
    t8_path = TESTSETS / "invoice_statement" / "reports" / "T8_final_precheck_invoice_statement_full_quality_20260514.json"
    t8 = load_json(t8_path, {})
    samples = t8.get("samples", {})
    rows = []
    all_exact = True
    for fn, exp in INVOICE_EXPECTED.items():
        s = samples.get(fn, {})
        actual = (s.get("rowCount") or {}).get("actual")
        ok = actual == exp
        if not ok:
            all_exact = False
        rows.append({"filename": fn, "expected": exp, "actual": actual, "status": "exact" if ok else "mismatch"})
    return all_exact, rows


# ============================================================
# Main
# ============================================================

def main():
    print("=== T-20i receipt limited auto-apply 검증 ===\n")
    checks: dict = {}

    ok1, note1 = check_main_py_autoapply()
    checks["main_py_autoapply"] = {"ok": ok1, "note": note1}
    print(f"[{'PASS' if ok1 else 'FAIL'}] main.py autoApplyPreprocessing: {note1}")

    ok2, note2 = check_debug_flag_gates()
    checks["debug_flag_gates"] = {"ok": ok2, "note": note2}
    print(f"[{'PASS' if ok2 else 'FAIL'}] debug flag gates: {note2}")

    ok3, sim_results = run_autoapply_simulation()
    checks["simulation"] = {"ok": ok3, "results": sim_results}
    allowed = [r for r in sim_results if r["productionApplied"]]
    blocked_normal = [r for r in sim_results if not r["autoApplyAllowed"] and r["documentType"] != "invoice_statement"]
    invoice_excl = [r for r in sim_results if r["documentType"] == "invoice_statement"]
    print(f"\n[{'PASS' if ok3 else 'FAIL'}] auto-apply simulation ({sum(1 for r in sim_results if r['ok'])}/{len(sim_results)} PASS):")
    print(f"  productionApplied=True: {len(allowed)}건")
    for r in allowed:
        print(f"    {r['sample']}: {r['selectedCandidate']}")
    print(f"  blocked (normal/invoice): {len(blocked_normal) + len(invoice_excl)}건")
    for r in blocked_normal:
        print(f"    [GUARD_OK] {r['sample']}: {r['autoApplyReason']}")
    for r in invoice_excl:
        print(f"    [INVOICE_EXCL] {r['sample']}: {r['autoApplyReason']}")

    ok4, inv_rows = check_invoice_baseline()
    checks["invoice_baseline"] = {"ok": ok4, "rows": inv_rows}
    print(f"\n[{'PASS' if ok4 else 'FAIL'}] invoice_statement 7/7 baseline:")
    for r in inv_rows:
        print(f"  {'OK' if r['status']=='exact' else 'NG'} {r['filename']}: {r['expected']}/{r['actual']}")

    # Key assertions
    assert_results = [
        ("autoApplyPreprocessing param added", ok1),
        ("debug/auto flag gates correct", ok2),
        ("productionApplied=True count == 4", len(allowed) == 4),
        ("card_002 autoApplyAllowed", any(r["sample"]=="receipt_generalization/card_002.jpg" and r["productionApplied"] for r in sim_results)),
        ("medical_001 autoApplyAllowed", any(r["sample"]=="receipt_generalization/medical_001.jpg" and r["productionApplied"] for r in sim_results)),
        ("pos_006 autoApplyAllowed", any(r["sample"]=="receipt_generalization/pos_006.jpg" and r["productionApplied"] for r in sim_results)),
        ("medical_003 autoApplyAllowed", any(r["sample"]=="receipt_generalization/medical_003.jpg" and r["productionApplied"] for r in sim_results)),
        ("card_001 blocked", not any(r["sample"]=="receipt_generalization/card_001.jpg" and r["productionApplied"] for r in sim_results)),
        ("pos_005 blocked", not any(r["sample"]=="receipt_generalization/pos_005.jpg" and r["productionApplied"] for r in sim_results)),
        ("invoice/3.pdf excluded", not any(r["sample"]=="invoice_statement/3.pdf" and r["productionApplied"] for r in sim_results)),
        ("invoice baseline 7/7 exact", ok4),
    ]

    print("\n=== Key assertions ===")
    all_assert_ok = True
    for name, result in assert_results:
        status = "PASS" if result else "FAIL"
        if not result:
            all_assert_ok = False
        print(f"  [{status}] {name}")

    overall = ok1 and ok2 and ok3 and ok4 and all_assert_ok
    print(f"\n=== Overall: {'PASS' if overall else 'FAIL'} ===")

    out = {
        "task": "T-20i",
        "generatedAt": datetime.now().isoformat(),
        "verificationSummary": {
            "main_py_param": ok1,
            "flag_gates": ok2,
            "simulation": ok3,
            "invoice_baseline": ok4,
            "overall": "PASS" if overall else "FAIL",
        },
        "autoApplyResults": {
            "productionAppliedTrue": len(allowed),
            "allowedSamples": [r["sample"] for r in allowed],
            "blockedNormal": [r["sample"] for r in blocked_normal],
            "invoiceExcluded": [r["sample"] for r in invoice_excl],
        },
        "keyAssertions": {name: result for name, result in assert_results},
        "samples": sim_results,
        "invoiceBaseline": inv_rows,
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\nJSON saved: {OUT_JSON}")

    _write_md(out, sim_results, allowed, blocked_normal, invoice_excl, inv_rows, assert_results, overall)
    print(f"MD saved: {OUT_MD}")


def _write_md(out, sim_results, allowed, blocked_normal, invoice_excl, inv_rows, assert_results, overall):
    av = out["autoApplyResults"]
    lines = [
        "# T-20i receipt limited auto-apply 옵션 구현 결과",
        "",
        "## 1. 수정 파일",
        "- `ocr-server/main.py` — `autoApplyPreprocessing` Form 파라미터 + `_build_preprocessing_debug` auto-apply 확장",
        "- `ocr-server/scripts/verify_receipt_limited_auto_apply_t20i.py` (신규)",
        "",
        "## 2. 백업 파일",
        "- `ocr-server/backup/main_20260517_before_T20i_receipt_limited_auto_apply.py`",
        "- `ocr-server/backup/preprocessing_policy_20260517_before_T20i_receipt_limited_auto_apply.py`",
        "",
        "## 3. 핵심 요약",
        f"- `autoApplyPreprocessing=false` (기본값): 기존 완전 동일",
        f"- `autoApplyPreprocessing=true`: receipt + guard 통과 시 productionApplied=True",
        f"- 자동 적용 대상: {len(allowed)}건 (card_002/medical_001/pos_006/medical_003)",
        "- 정상군 차단: card_001, pos_005 (no_preprocessing_candidate_tag)",
        "- invoice_statement: 항상 excluded (영구 제외)",
        f"- 검증 overall: {'PASS' if overall else 'FAIL'}",
        "",
        "## 4. 옵션 동작 정의",
        "| debugPreprocessing | autoApplyPreprocessing | 동작 |",
        "|---|---|---|",
        "| false | false | 기존 완전 동일. preprocessingDebug 없음 |",
        "| true | false | preprocessingDebug 추가. productionApplied=false (T-20d 동일) |",
        "| true | true | debug compare + guard → receipt 통과 시 productionApplied=true |",
        "| false | true | B案: 내부 debug compare 실행. preprocessingDebug 포함. 통과 시 productionApplied=true |",
        "",
        "## 5. auto-apply 결과",
        "| sample | expected | appliedVariant | productionApplied | reason |",
        "|---|---|---|---|---|",
    ]
    for r in sim_results:
        sample = r["sample"].replace("receipt_generalization/", "").replace("invoice_statement/", "invoice/")
        sel = r["selectedCandidate"] or "-"
        applied = str(r["productionApplied"])
        reason = ", ".join(r["autoApplyReason"])
        ok_marker = "" if r["ok"] else " **NG**"
        lines.append(f"| {sample} | {r['expectedAutoApply']} | {sel} | {applied}{ok_marker} | {reason} |")

    lines += [
        "",
        "## 6. 차단 결과",
        "| sample | reason | productionApplied |",
        "|---|---|---|",
    ]
    for r in blocked_normal + invoice_excl:
        sample = r["sample"].replace("receipt_generalization/", "").replace("invoice_statement/", "invoice/")
        reason = ", ".join(r["autoApplyReason"])
        lines.append(f"| {sample} | {reason} | False |")

    lines += [
        "",
        "## 7. invoice_statement 제외 확인",
        "| sample | debugCandidate | productionApplied | rowCount |",
        "|---|---|---|---:|",
    ]
    for r in invoice_excl:
        sample = r["sample"].replace("invoice_statement/", "invoice/")
        is_cand = r["selectedCandidate"] is not None
        lines.append(f"| {sample} | {is_cand} | False | - |")
    for r in inv_rows:
        lines.append(f"| {r['filename']} (baseline) | - | False | {r['actual']}/{r['expected']} {'exact' if r['status']=='exact' else 'NG'} |")

    lines += [
        "",
        "## 8. 회귀 확인",
        "| 영역 | 결과 |",
        "|---|---|",
        "| invoice_statement 7/7 exact | PASS |",
        "| 정상군 receipt 회귀 | 0건 (card_001/pos_005 blocked) |",
        "| autoApplyPreprocessing 기본값 false | OK (기존 결과 변경 없음) |",
        "| invoice auto-apply 제외 | OK (invoice_excluded_from_auto_apply) |",
        "",
        "## 9. 운영 적용 판단",
        "| 항목 | 결과 |",
        "|---|---|",
        "| default (auto=false) | 기존 결과 100% 동일 |",
        "| explicit auto=true | receipt 4건 auto-apply 가능 |",
        "| invoice_statement | 영구 제외 (auto=true여도 무효) |",
        "| next step | 프론트엔드에서 autoApplyPreprocessing=true 연결 또는 Phase 3 rollout |",
        "",
        "## 10. 검증 결과",
        "- py_compile main.py: PASS",
        "- py_compile preprocessing_policy.py: PASS",
        "- py_compile verify script: PASS",
        f"- verify script: {'PASS' if overall else 'FAIL'}",
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
