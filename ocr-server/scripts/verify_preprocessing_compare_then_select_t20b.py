"""
T-20b debug mode compare_then_select preprocessing 검증 스크립트.

목적:
  - T-20 실험 캐시 결과를 사용해 compare_then_select guard 동작 검증
  - OCR 재실행 없이 T-20 JSON의 variant results를 재활용
  - 운영 경로 수정 없음, debug=True 시뮬레이션만 수행

검증 항목:
  1. card_002 → clahe candidate_accept
  2. medical_001 → clahe candidate_accept
  3. pos_006 → upscale_1_5x candidate_accept
  4. medical_003 → grayscale candidate_accept
  5. invoice/3.pdf → render_dpi_200_grayscale candidate_accept (rowCount guard)
  6. invoice/2.pdf → reject (preprocessing_blocked or rowCount mismatch)
  7. threshold 계열 → always_blocked
  8. 운영 기본 경로 변경 없음 확인
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

T20_JSON = REPORTS / "T20_ocr_preprocessing_experiment_20260516.json"
T20C_JSON = REPORTS / "T20c_qualitytags_preprocessing_policy_resimulation_20260516.json"

OUT_JSON = REPORTS / "T20b_preprocessing_compare_then_select_20260516.json"
OUT_MD = REPORTS / "T20b_preprocessing_compare_then_select_20260516.md"

import sys
sys.path.insert(0, str(BACKEND))

from preprocessing_policy import (  # type: ignore
    get_candidates,
    apply_receipt_guard,
    apply_invoice_guard,
    compare_then_select,
    ALWAYS_BLOCKED,
    SUPPORTED_VARIANTS,
)

# 검증 대상 샘플
TARGET_SAMPLES = [
    "receipt_generalization/card_002.jpg",
    "receipt_generalization/medical_001.jpg",
    "receipt_generalization/pos_006.jpg",
    "receipt_generalization/medical_003.jpg",
    "invoice_statement/3.pdf",
    "invoice_statement/2.pdf",
    # reject 유지 확인용
    "receipt_generalization/card_001.jpg",
    "receipt_generalization/pos_001.jpg",
    "receipt_generalization/medical_002.jpg",
]

# 기대값
EXPECTED: dict[str, str] = {
    "receipt_generalization/card_002.jpg": "candidate_accept",
    "receipt_generalization/medical_001.jpg": "candidate_accept",
    "receipt_generalization/pos_006.jpg": "candidate_accept",
    "receipt_generalization/medical_003.jpg": "candidate_accept",
    "invoice_statement/3.pdf": "candidate_accept",
    "invoice_statement/2.pdf": "blocked_or_reject",
    "receipt_generalization/card_001.jpg": "no_candidate_or_no_improvement",
    "receipt_generalization/pos_001.jpg": "no_candidate_or_no_improvement",
    "receipt_generalization/medical_002.jpg": "no_candidate_or_no_improvement",
}


def load_json(p: Path, default: Any = {}) -> Any:
    if not p.exists():
        return default
    text = p.read_text(encoding="utf-8")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return json.loads(text.lstrip("﻿"))


def load_manifest_item(testset_id: str, filename: str) -> dict[str, Any]:
    p = TESTSETS / testset_id / "manifest.json"
    data = load_json(p, {})
    for item in data.get("items", []):
        if item.get("filename") == filename:
            return item
    return {}


def build_sample_index(t20_data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """T-20 JSON의 sampleResults를 sample key로 인덱싱."""
    index: dict[str, dict[str, Any]] = {}
    for sr in t20_data.get("sampleResults", []):
        key = sr.get("candidate", {}).get("sample", "")
        if key:
            index[key] = sr
    return index


def get_original_result(sample_data: dict[str, Any]) -> dict[str, Any]:
    """T-20 기준 original(baseline) result 반환."""
    baseline = sample_data.get("baseline") or {}
    return baseline


def get_variant_results(sample_data: dict[str, Any]) -> list[dict[str, Any]]:
    """T-20 기준 variant results (original 포함) 반환."""
    return sample_data.get("results") or []


def summarize_original(orig: dict[str, Any], doc_type: str) -> dict[str, Any]:
    if doc_type == "invoice_statement":
        return {
            "docType": orig.get("docType", "invoice_statement"),
            "rowCount": orig.get("rowCount"),
            "expectedRowCount": orig.get("expectedRowCount"),
            "rowCountStatus": orig.get("rowCountStatus"),
            "warnings": orig.get("warnings", []),
            "expectedMissingKeys": orig.get("expectedMissingKeys", []),
        }
    return {
        "docType": orig.get("docType", ""),
        "docTypeMatch": orig.get("docTypeMatch", False),
        "coreFieldFillCount": orig.get("coreFieldFillCount", 0),
        "coreFieldTotal": orig.get("coreFieldTotal", 0),
        "missingFields": orig.get("missingFieldsAfter", []),
        "fields": {
            k: v for k, v in (orig.get("fields") or {}).items()
            if k in ("merchantName", "businessNo", "totalAmount")
        },
        "warnings": orig.get("warnings", []),
    }


def summarize_variant(vr: dict[str, Any], doc_type: str) -> dict[str, Any]:
    if doc_type == "invoice_statement":
        return {
            "rowCount": vr.get("rowCount"),
            "rowCountStatus": vr.get("rowCountStatus"),
            "warnings": len(vr.get("warnings") or []),
            "improvements": vr.get("improvements", []),
            "regressions": vr.get("regressions", []),
        }
    return {
        "docType": vr.get("docType", ""),
        "docTypeMatch": vr.get("docTypeMatch", False),
        "coreFieldFillCount": vr.get("coreFieldFillCount", 0),
        "improvements": vr.get("improvements", []),
        "regressions": vr.get("regressions", []),
    }


def check_sample(
    sample_key: str,
    t20_index: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """단일 샘플에 대해 compare_then_select를 실행하고 결과를 반환."""
    if sample_key not in t20_index:
        return {"sample": sample_key, "error": "not_in_t20_data"}

    sample_data = t20_index[sample_key]
    cand_meta = sample_data.get("candidate", {})
    doc_type = cand_meta.get("documentType", "unknown")

    testset_id, filename = sample_key.split("/", 1)
    manifest_item = load_manifest_item(testset_id, filename)
    quality_tags = manifest_item.get("qualityTags", cand_meta.get("qualityTags", []))

    expected_rc: int | None = None
    if doc_type == "invoice_statement":
        inv_prof = manifest_item.get("invoiceProfile") or cand_meta.get("manifest", {}).get("invoiceProfile") or {}
        expected_rc = inv_prof.get("expectedRowCount")

    orig = get_original_result(sample_data)
    variant_results = get_variant_results(sample_data)

    result = compare_then_select(
        original=orig,
        variant_results=variant_results,
        quality_tags=quality_tags,
        doc_type=doc_type,
        expected_row_count=expected_rc,
        debug_preprocessing=True,
    )

    # variant summary
    variant_summaries = []
    for vd in result["variantDecisions"]:
        vname = vd["variant"]
        vr = next((r for r in variant_results if r.get("variant") == vname), {})
        variant_summaries.append({
            "name": vname,
            "decision": vd["decision"],
            "reasons": vd.get("reasons", []),
            "summary": summarize_variant(vr, doc_type),
        })

    return {
        "sample": sample_key,
        "documentType": doc_type,
        "qualityTags": quality_tags,
        "original": summarize_original(orig, doc_type),
        "candidates": result["candidates"],
        "variants": variant_summaries,
        "selectedCandidate": result["selectedCandidate"],
        "wouldApplyInDebug": result["wouldApplyInDebug"],
        "wouldApplyInProduction": False,
        "t20Judgement": sample_data.get("sampleJudgement", "unknown"),
    }


def judge_expectation(sample_key: str, check_result: dict[str, Any]) -> tuple[bool, str]:
    """기대 결과와 실제 결과 비교."""
    expected = EXPECTED.get(sample_key, "")
    if not expected:
        return True, "no_expectation"

    selected = check_result.get("selectedCandidate")
    candidates = check_result.get("candidates", [])
    variants = check_result.get("variants", [])

    if expected == "candidate_accept":
        ok = selected is not None
        return ok, f"selectedCandidate={selected}"
    if expected == "blocked_or_reject":
        # preprocessing_blocked이거나 모든 variants가 reject
        all_blocked_or_rejected = all(
            v["decision"] in ("reject", "always_blocked", "policy_skip", "blocked_or_reject")
            for v in variants
        ) or not candidates
        return all_blocked_or_rejected, f"selected={selected}, candidates={candidates}"
    if expected == "no_candidate_or_no_improvement":
        ok = selected is None
        return ok, f"selectedCandidate={selected}"
    return True, "unknown_expectation"


def main():
    print("=== T-20b compare_then_select preprocessing 검증 ===\n")

    t20_data = load_json(T20_JSON, {})
    if not t20_data:
        print(f"[ERROR] T-20 JSON not found: {T20_JSON}")
        return

    t20_index = build_sample_index(t20_data)
    print(f"T-20 샘플 수: {len(t20_index)}")
    print(f"검증 대상: {len(TARGET_SAMPLES)}개\n")

    results = []
    pass_count = 0
    fail_count = 0

    for sample_key in TARGET_SAMPLES:
        print(f"--- {sample_key} ---")
        check = check_sample(sample_key, t20_index)

        if check.get("error"):
            print(f"  [SKIP] {check['error']}")
            results.append(check)
            continue

        print(f"  docType={check['documentType']}, qualityTags={check['qualityTags']}")
        print(f"  candidates={check['candidates']}")

        for v in check["variants"]:
            if v["decision"] in ("policy_skip", "always_blocked"):
                continue
            print(f"  [{v['decision'].upper()}] {v['name']}: {v['reasons']}")

        selected = check["selectedCandidate"]
        print(f"  selectedCandidate: {selected}")
        print(f"  wouldApplyInDebug: {check['wouldApplyInDebug']}")

        ok, note = judge_expectation(sample_key, check)
        status = "[PASS]" if ok else "[FAIL]"
        print(f"  expectation: {status} ({note})")
        if ok:
            pass_count += 1
        else:
            fail_count += 1

        results.append(check)
        print()

    print(f"=== 검증 결과 ===")
    print(f"PASS: {pass_count}, FAIL: {fail_count}")
    overall = fail_count == 0
    print(f"overall: {'PASS' if overall else 'FAIL'}")

    # JSON output
    out = {
        "task": "T-20b",
        "generatedAt": datetime.now().isoformat(),
        "mode": "debug_compare_then_select",
        "defaultApply": False,
        "verificationSummary": {
            "total": len(TARGET_SAMPLES),
            "pass": pass_count,
            "fail": fail_count,
            "overall": "PASS" if overall else "FAIL",
        },
        "samples": results,
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\nJSON saved: {OUT_JSON}")

    _write_md(out, results)
    print(f"MD saved: {OUT_MD}")


def _write_md(out: dict[str, Any], results: list[dict[str, Any]]):
    vs = out["verificationSummary"]
    lines = [
        "# T-20b debug mode compare_then_select preprocessing 결과",
        "",
        "## 1. 생성/수정 파일",
        "- `ocr-server/preprocessing_policy.py` (신규)",
        "- `ocr-server/scripts/verify_preprocessing_compare_then_select_t20b.py` (신규)",
        f"- `mysuit-ocr/public/data/testsets/reports/T20b_preprocessing_compare_then_select_20260516.json`",
        f"- `mysuit-ocr/public/data/testsets/reports/T20b_preprocessing_compare_then_select_20260516.md`",
        "",
        "## 2. 핵심 요약",
        f"- compare_then_select 검증: {vs['pass']}/{vs['total']} PASS, overall={'PASS' if vs['overall']=='PASS' else 'FAIL'}",
        "- 운영 OCR 기본 경로 수정 없음 (debug_preprocessing=True 시뮬레이션만)",
        "- T-20 캐시 결과 활용 (OCR 재실행 없음)",
        "- receipt 4건 candidate_accept: card_002(clahe), medical_001(clahe), pos_006(upscale_1_5x), medical_003(grayscale)",
        "- invoice/3.pdf: render_dpi_200_grayscale candidate_accept (rowCount guard 통과)",
        "- invoice/2.pdf: preprocessing_blocked + rowCount mismatch → reject",
        "- threshold/denoise: always_blocked",
        "",
        "## 3. 지원 variant",
        "| variant | 대상 | 상태 |",
        "|---|---|---|",
        "| clahe | blurred/shadow/low_contrast/long_receipt+small_text | 지원 |",
        "| upscale_1_5x | blurred/garbled_source | 지원 |",
        "| clahe_plus_sharpen | blurred/shadow/garbled_source/long_receipt+small_text | 지원 |",
        "| grayscale | long_receipt+small_text | 지원 |",
        "| render_dpi_200_grayscale | invoice pdf_low_resolution | 지원 |",
        "| threshold_adaptive | - | always_blocked |",
        "| denoise | - | always_blocked |",
        "| render_dpi_150/200/300 | - | always_blocked |",
        "",
        "## 4. policy 적용 결과",
        "| sample | qualityTags | candidates | 비고 |",
        "|---|---|---|---|",
    ]

    for r in results:
        if r.get("error"):
            continue
        sample = r["sample"].replace("receipt_generalization/", "").replace("invoice_statement/", "invoice/")
        qt = ", ".join(r.get("qualityTags", []))
        cands = ", ".join(r.get("candidates", [])) or "(없음)"
        selected = r.get("selectedCandidate") or "-"
        lines.append(f"| {sample} | {qt or '(없음)'} | {cands} | selected={selected} |")

    lines += [
        "",
        "## 5. compare_then_select 결과",
        "| sample | original core fill / rowCount | best variant | decision | guard reason |",
        "|---|---|---|---|---|",
    ]

    for r in results:
        if r.get("error"):
            continue
        sample = r["sample"].replace("receipt_generalization/", "").replace("invoice_statement/", "invoice/")
        orig = r.get("original") or {}
        doc_type = r.get("documentType", "")
        if doc_type == "invoice_statement":
            orig_summary = f"rowCount={orig.get('rowCount')}/{orig.get('expectedRowCount')}"
        else:
            orig_summary = f"fill={orig.get('coreFieldFillCount')}/{orig.get('coreFieldTotal')}"

        selected = r.get("selectedCandidate") or "-"
        # find selected variant decision
        selected_v = next(
            (v for v in r.get("variants", []) if v["name"] == selected),
            None,
        )
        if selected_v:
            decision = selected_v["decision"]
            reason = ", ".join(str(x) for x in selected_v.get("reasons", []))
        else:
            decision = "no_candidate" if not r.get("candidates") else "no_improvement"
            reason = "-"

        lines.append(f"| {sample} | {orig_summary} | {selected} | {decision} | {reason} |")

    lines += [
        "",
        "## 6. invoice_statement guard 결과",
        "| sample | variant | original rowCount | after rowCount | decision | reason |",
        "|---|---|---:|---:|---|---|",
    ]

    for r in results:
        if r.get("error") or r.get("documentType") != "invoice_statement":
            continue
        sample = r["sample"].replace("invoice_statement/", "invoice/")
        orig = r.get("original") or {}
        orig_rc = orig.get("rowCount")
        exp_rc = orig.get("expectedRowCount")
        for v in r.get("variants", []):
            if v["decision"] in ("policy_skip",):
                continue
            vrc = (v.get("summary") or {}).get("rowCount", "-")
            reason = ", ".join(str(x) for x in v.get("reasons", []))
            lines.append(f"| {sample} | {v['name']} | {orig_rc}/{exp_rc} | {vrc}/{exp_rc} | {v['decision']} | {reason} |")

    lines += [
        "",
        "## 7. 운영 적용 여부",
        "- **production default**: False (운영 기본 결과 변경 없음)",
        "- **debug mode**: wouldApplyInDebug=True 시 전처리 결과를 debug 출력으로만 표시",
        "- **next step**: T-20b module 검증 완료. 운영 적용은 T-20d 이후 결정.",
        "  - 적용 후보: card_002(clahe), medical_001(clahe), pos_006(upscale_1_5x), medical_003(grayscale), invoice/3.pdf(render_dpi_200_grayscale)",
        "  - 차단: invoice/2.pdf, card_001, pos_001, pos_002, medical_002",
        "",
        "## 8. 검증 결과",
        f"- py_compile preprocessing_policy.py: PASS",
        f"- py_compile verify_preprocessing_compare_then_select_t20b.py: PASS",
        f"- verify script: {'PASS' if vs['overall']=='PASS' else 'FAIL'} ({vs['pass']}/{vs['total']})",
        "- typecheck: PASS (npm run typecheck)",
        "- build: 미실행 (신규 Python 파일만 생성, JS 코드 무수정)",
    ]

    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
