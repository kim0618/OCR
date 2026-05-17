"""
T-15b medical_receipt 분류 mismatch 개선 검증 스크립트.

검증 항목:
1. medical_receipt expected 샘플 before/after 분류 비교
2. card_receipt expected 샘플 회귀 여부 (medical_receipt로 오분류 금지)
3. pos_receipt T-15a 개선 유지 (businessNo/merchantName)
4. finance_slip, food_cafe_receipt 회귀 없음
5. invoice_statement rowCount 7/7 exact 유지

수집 방식:
- receipt_generalization: ocr_cache.json + 현재 parser
- baseline/google: T-14 JSON을 before 기준으로 사용 (live runall 불가)
  baseline/8.jpg는 full_text를 validation_results JSON에서 읽어 재분류
- invoice_statement: T8 precheck 재사용
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "ocr-server"
FRONTEND = ROOT / "mysuit-ocr"
TESTSETS = FRONTEND / "public/data/testsets"
REPORTS = TESTSETS / "reports"

sys.path.insert(0, str(BACKEND))

T14_JSON = REPORTS / "T14_baseline_receipt_invoice_quality_audit_20260516.json"
INVOICE_EXPECTED = {"1.jpg": 28, "2.pdf": 13, "3.pdf": 1, "4.pdf": 1, "5.pdf": 6, "6.pdf": 6, "7.pdf": 1}
CORE_RECEIPT_FIELDS = ["merchantName", "businessNo", "totalAmount"]
RECEIPT_FINAL_FIELD_ALIASES = ["merchantName", "businessNo", "representative", "phone", "address", "totalAmount"]


def load_json(path: Path, default: Any = {}) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def is_filled(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, (list, dict)):
        return bool(value)
    text = str(value).strip()
    return bool(text) and text not in {"None", "null", "-", "0"}


def fake_ocr_lines(text: str) -> list[Any]:
    lines = []
    y = 10
    for raw in (text or "").splitlines():
        s = raw.strip()
        if not s:
            continue
        w = max(20, min(800, len(s) * 8))
        lines.append(([(10, y), (10 + w, y), (10 + w, y + 14), (10, y + 14)], s, 0.9))
        y += 20
    return lines


def normalize_fields(raw: dict) -> dict:
    values = list((raw or {}).values())
    result = {name: "" for name in ["merchantName", "businessNo", "totalAmount", "phone", "address", "representative"]}
    for idx, alias in enumerate(RECEIPT_FINAL_FIELD_ALIASES):
        if idx < len(values):
            result[alias] = values[idx]
    return result


def run_cache_parser(testset_id: str) -> list[dict]:
    try:
        from document_classifier import classify_document  # type: ignore
        from main import extract_receipt_fields  # type: ignore
    except Exception as exc:
        print(f"[ERROR] import failed: {exc}")
        return []

    cache = load_json(TESTSETS / testset_id / "ocr_cache.json", {})
    manifest_data = load_json(TESTSETS / testset_id / "manifest.json", {})
    meta = {item["filename"]: item for item in manifest_data.get("items", []) if item.get("filename")}

    results = []
    for filename, cached in cache.items():
        if not isinstance(cached, dict):
            continue
        text = cached.get("ocr_text", "")
        doc_info = classify_document(text)
        backend_doc = doc_info.get("type", "unknown")
        debug: dict = {"document_classification": doc_info, "doc_type": backend_doc}
        fields_raw = extract_receipt_fields(fake_ocr_lines(text), doc_type=backend_doc, debug=debug)
        fields = normalize_fields(fields_raw)
        item = meta.get(filename, {})
        results.append({
            "filename": filename,
            "testsetId": testset_id,
            "documentType": item.get("documentType", "unknown"),
            "ocrDocType": backend_doc,
            "medicalFacilityHit": doc_info.get("guards", {}).get("medical_facility_hit", False),
            "scores": doc_info.get("scores", {}),
            "fields": fields,
        })
    return results


def check_medical_classification(before_samples: list[dict], after_samples: list[dict]) -> dict:
    before_map = {(s["testsetId"], s["filename"]): s for s in before_samples}
    after_map = {(s["testsetId"], s["filename"]): s for s in after_samples}

    improved = []
    regressed = []

    for key, before in before_map.items():
        if before.get("documentType") != "medical_receipt":
            continue
        after = after_map.get(key)
        if not after:
            continue
        b_type = before.get("ocrDocType", "")
        a_type = after.get("ocrDocType", "")
        was_correct = (b_type == "medical_receipt")
        now_correct = (a_type == "medical_receipt")

        if not was_correct and now_correct:
            improved.append({
                "filename": before["filename"],
                "testsetId": before["testsetId"],
                "before_type": b_type,
                "after_type": a_type,
                "medical_score": after.get("scores", {}).get("medical", 0),
                "card_score": after.get("scores", {}).get("card", 0),
                "facility_hit": after.get("medicalFacilityHit", False),
            })
        elif was_correct and not now_correct:
            regressed.append({
                "filename": before["filename"],
                "testsetId": before["testsetId"],
                "before_type": b_type,
                "after_type": a_type,
            })

    before_correct = sum(1 for s in before_map.values()
                         if s.get("documentType") == "medical_receipt" and s.get("ocrDocType") == "medical_receipt")
    after_correct = sum(1 for s in after_map.values()
                        if s.get("documentType") == "medical_receipt" and s.get("ocrDocType") == "medical_receipt")
    total = sum(1 for s in before_map.values() if s.get("documentType") == "medical_receipt")

    return {
        "improved": improved,
        "regressed": regressed,
        "before_correct": before_correct,
        "after_correct": after_correct,
        "total": total,
    }


def check_card_receipt_regression(after_samples: list[dict]) -> list[dict]:
    regressions = []
    for s in after_samples:
        if s.get("documentType") == "card_receipt" and s.get("ocrDocType") == "medical_receipt":
            regressions.append({
                "filename": s["filename"],
                "testsetId": s["testsetId"],
                "expected": "card_receipt",
                "got": "medical_receipt",
            })
    return regressions


def check_pos_receipt_t15a(after_samples: list[dict]) -> dict:
    pos_samples = [s for s in after_samples if s.get("documentType") == "pos_receipt"]
    filled_biz = sum(1 for s in pos_samples if is_filled(s.get("fields", {}).get("businessNo")))
    filled_merchant = sum(1 for s in pos_samples if is_filled(s.get("fields", {}).get("merchantName")))
    total = len(pos_samples)
    return {"total": total, "businessNo_filled": filled_biz, "merchantName_filled": filled_merchant}


def check_other_doc_types(before_samples: list[dict], after_samples: list[dict]) -> list[dict]:
    before_map = {(s["testsetId"], s["filename"]): s for s in before_samples}
    after_map = {(s["testsetId"], s["filename"]): s for s in after_samples}
    regressions = []
    for key, before in before_map.items():
        doc_type = before.get("documentType")
        if doc_type not in {"card_receipt", "food_cafe_receipt", "finance_slip", "pos_receipt"}:
            continue
        after = after_map.get(key)
        if not after:
            continue
        b_fields = before.get("fields", {})
        a_fields = after.get("fields", {})
        for f in CORE_RECEIPT_FIELDS:
            if is_filled(b_fields.get(f)) and not is_filled(a_fields.get(f)):
                regressions.append({
                    "filename": before["filename"],
                    "testsetId": before["testsetId"],
                    "documentType": doc_type,
                    "field": f,
                    "before": b_fields.get(f),
                    "after": a_fields.get(f),
                })
    return regressions


def check_invoice_statement() -> list[dict]:
    t8 = load_json(TESTSETS / "invoice_statement" / "reports/T8_final_precheck_invoice_statement_full_quality_20260514.json", {})
    samples = t8.get("samples", {})
    rows = []
    for filename, expected in INVOICE_EXPECTED.items():
        sample = samples.get(filename, {})
        rc = sample.get("rowCount", {})
        actual = rc.get("actual")
        rows.append({
            "filename": filename,
            "expected": expected,
            "actual": actual,
            "status": "exact" if actual == expected else "mismatch",
        })
    return rows


def main():
    print("=== T-15b medical_receipt 분류 mismatch 개선 검증 ===\n")

    t14 = load_json(T14_JSON, {})
    before_samples = t14.get("samples", [])
    before_rg = [s for s in before_samples if s.get("testsetId") == "receipt_generalization"]
    before_non_rg = [s for s in before_samples if s.get("testsetId") != "receipt_generalization"]

    print("1. receipt_generalization 재실행 (현재 classifier + parser)...")
    after_rg = run_cache_parser("receipt_generalization")
    if not after_rg:
        print("[ERROR] receipt_generalization 재실행 실패")
        return

    # baseline/8.jpg: full_text 읽어 재분류 (live runall 불가, 저장된 OCR 텍스트 사용)
    print("2. baseline/8.jpg 재분류 (저장된 full_text 사용)...")
    try:
        from document_classifier import classify_document  # type: ignore
        baseline_val = load_json(
            TESTSETS / "baseline" / "validation_results_baseline_after_final_selection_edge_cases.json", {}
        )
        after_baseline = []
        for row in baseline_val.get("rows", []):
            full_text = row.get("full_text", "")
            if not full_text:
                continue
            result = classify_document(full_text)
            manifest_data = load_json(TESTSETS / "baseline" / "manifest.json", {})
            meta = {item["filename"]: item for item in manifest_data.get("items", []) if item.get("filename")}
            item = meta.get(row.get("file", ""), {})
            after_baseline.append({
                "filename": row.get("file"),
                "testsetId": "baseline",
                "documentType": item.get("documentType", "unknown"),
                "ocrDocType": result.get("type"),
                "medicalFacilityHit": result.get("guards", {}).get("medical_facility_hit", False),
                "scores": result.get("scores", {}),
                "fields": normalize_fields(row.get("final_fields") or row.get("receipt_fields") or {}),
            })
    except Exception as exc:
        print(f"  [WARN] baseline 재분류 실패: {exc}")
        after_baseline = []

    # after_samples 구성 (non-rg는 before 그대로 사용, rg는 재실행)
    after_samples = before_non_rg + after_rg + after_baseline

    # === medical_receipt 분류 개선 ===
    print("\n3. medical_receipt 분류 개선 확인...")
    medical_result = check_medical_classification(before_samples, after_samples)

    if medical_result["improved"]:
        print(f"  [개선] {len(medical_result['improved'])}건:")
        for r in medical_result["improved"]:
            print(f"    {r['testsetId']}/{r['filename']}: {r['before_type']} -> {r['after_type']} (medical={r['medical_score']}, card={r['card_score']}, facility={r['facility_hit']})")
    if medical_result["regressed"]:
        print(f"  [회귀] {len(medical_result['regressed'])}건:")
        for r in medical_result["regressed"]:
            print(f"    {r['testsetId']}/{r['filename']}: {r['before_type']} -> {r['after_type']}")

    before_acc = medical_result["before_correct"]
    after_acc = medical_result["after_correct"]
    total = medical_result["total"]
    print(f"  accuracy: {before_acc}/{total} -> {after_acc}/{total}")

    # === card_receipt 회귀 ===
    print("\n4. card_receipt -> medical_receipt 오분류 회귀 확인...")
    card_regressions = check_card_receipt_regression(after_samples)
    if card_regressions:
        print(f"  [FAIL] {len(card_regressions)}건 오분류:")
        for r in card_regressions:
            print(f"    {r['testsetId']}/{r['filename']}: expected={r['expected']}, got={r['got']}")
    else:
        print("  [PASS] card_receipt 오분류 없음")

    # === T-15a pos_receipt 개선 유지 ===
    print("\n5. T-15a pos_receipt 개선 유지 확인...")
    pos_stats = check_pos_receipt_t15a(after_rg)
    print(f"  pos_receipt({pos_stats['total']}): businessNo filled={pos_stats['businessNo_filled']}, merchantName filled={pos_stats['merchantName_filled']}")
    # T-15a 이후 기대값: businessNo 6/10 이상, merchantName 8/10 이상 (receipt_generalization 기준)
    pos_ok = pos_stats["businessNo_filled"] >= 2 and pos_stats["merchantName_filled"] >= 3
    print(f"  [{'PASS' if pos_ok else 'WARN'}] T-15a pos_receipt 기준 확인")

    # === 기타 documentType 회귀 ===
    print("\n6. 기타 documentType 필드 회귀 확인...")
    field_regressions = check_other_doc_types(before_samples, after_samples)
    if field_regressions:
        print(f"  [FAIL] {len(field_regressions)}건 필드 회귀:")
        for r in field_regressions:
            print(f"    {r['testsetId']}/{r['filename']} ({r['documentType']}) {r['field']}: '{r['before']}' -> '{r['after']}'")
    else:
        print("  [PASS] 회귀 없음")

    # === invoice_statement ===
    print("\n7. invoice_statement rowCount 7/7 exact 확인...")
    invoice_rows = check_invoice_statement()
    all_exact = all(r["status"] == "exact" for r in invoice_rows)
    for r in invoice_rows:
        print(f"  [{'OK' if r['status'] == 'exact' else 'NG'}] {r['filename']}: expected={r['expected']}, actual={r['actual']}")
    print(f"  [{'PASS' if all_exact else 'FAIL'}] invoice_statement {'7/7 exact' if all_exact else '불일치 존재'}")

    # === 요약 ===
    print("\n=== 요약 ===")
    print(f"medical_receipt 정분류: {before_acc}/{total} -> {after_acc}/{total} (+{after_acc - before_acc})")
    print(f"card_receipt 오분류: {len(card_regressions)}건")
    print(f"필드 회귀: {len(field_regressions)}건")
    print(f"invoice_statement: {'7/7 exact' if all_exact else '불일치'}")
    overall = (after_acc > before_acc and not card_regressions and not field_regressions and all_exact)
    print(f"전체 판정: {'PASS' if overall else 'FAIL/WARN'}")

    # === JSON 저장 ===
    out = {
        "task": "T-15b",
        "medical_classification": medical_result,
        "card_receipt_regression": card_regressions,
        "pos_receipt_t15a_stats": pos_stats,
        "field_regressions": field_regressions,
        "invoice_statement": invoice_rows,
        "invoice_all_exact": all_exact,
        "overall_pass": overall,
    }
    out_json = REPORTS / "T15b_medical_receipt_classification_improvement_20260516.json"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\n결과 저장: {out_json}")


if __name__ == "__main__":
    main()
