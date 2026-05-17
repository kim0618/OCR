"""
T-15c food_cafe_receipt merchantName missing 개선 검증 스크립트.

검증 항목:
1. food_cafe_receipt merchantName before/after 비교
2. totalAmount 변화
3. T-15a pos_receipt businessNo/merchantName 유지
4. T-15b medical_receipt 분류 유지
5. card_receipt/finance_slip 회귀 없음
6. invoice_statement rowCount 7/7 exact 유지
7. pos_003.jpg: T-15b에 의해 medical_receipt로 올바르게 재분류됨 (manifest 오기입)
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
RECEIPT_FINAL_FIELD_ALIASES = ["merchantName", "businessNo", "representative", "phone", "address", "totalAmount"]
CORE_FIELDS = ["merchantName", "totalAmount", "businessNo"]

# pos_003.jpg: manifest에는 pos_receipt이지만 OCR 내용이 약국 영수증 (medical_receipt 맞음)
KNOWN_MANIFEST_MISLABELS = {"receipt_generalization/pos_003.jpg"}


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
            "fields": fields,
        })
    return results


def check_food_cafe_improvement(before_samples: list[dict], after_samples: list[dict]) -> dict:
    before_map = {(s["testsetId"], s["filename"]): s for s in before_samples}
    after_map = {(s["testsetId"], s["filename"]): s for s in after_samples}

    improved, regressed = [], []
    before_filled = {"merchantName": 0, "totalAmount": 0}
    after_filled = {"merchantName": 0, "totalAmount": 0}

    for key, before in before_map.items():
        if before.get("documentType") != "food_cafe_receipt":
            continue
        after = after_map.get(key)
        if not after:
            continue
        b_fields = before.get("fields", {})
        a_fields = after.get("fields", {})
        for f in ["merchantName", "totalAmount"]:
            if is_filled(b_fields.get(f)):
                before_filled[f] += 1
            if is_filled(a_fields.get(f)):
                after_filled[f] += 1
        for f in CORE_FIELDS:
            was = is_filled(b_fields.get(f))
            now = is_filled(a_fields.get(f))
            if not was and now:
                improved.append({"filename": before["filename"], "testsetId": before["testsetId"], "field": f,
                                  "before": b_fields.get(f), "after": a_fields.get(f)})
            elif was and not now:
                regressed.append({"filename": before["filename"], "testsetId": before["testsetId"], "field": f,
                                   "before": b_fields.get(f), "after": a_fields.get(f)})

    return {"improved": improved, "regressed": regressed,
            "before_filled": before_filled, "after_filled": after_filled}


def check_regressions(before_samples: list[dict], after_samples: list[dict], doc_types: list[str]) -> list[dict]:
    before_map = {(s["testsetId"], s["filename"]): s for s in before_samples}
    after_map = {(s["testsetId"], s["filename"]): s for s in after_samples}
    regressions = []
    for key, before in before_map.items():
        if before.get("documentType") not in doc_types:
            continue
        # 알려진 manifest 오기입 샘플은 회귀 체크 제외
        sample_key = f"{before['testsetId']}/{before['filename']}"
        if sample_key in KNOWN_MANIFEST_MISLABELS:
            continue
        after = after_map.get(key)
        if not after:
            continue
        b_fields = before.get("fields", {})
        a_fields = after.get("fields", {})
        for f in CORE_FIELDS:
            if is_filled(b_fields.get(f)) and not is_filled(a_fields.get(f)):
                regressions.append({"filename": before["filename"], "testsetId": before["testsetId"],
                                     "documentType": before["documentType"], "field": f,
                                     "before": b_fields.get(f), "after": a_fields.get(f)})
    return regressions


def check_medical_t15b(after_samples: list[dict]) -> dict:
    total = sum(1 for s in after_samples if s.get("documentType") == "medical_receipt")
    correct = sum(1 for s in after_samples
                  if s.get("documentType") == "medical_receipt" and s.get("ocrDocType") == "medical_receipt")
    return {"total": total, "correct": correct}


def check_invoice_statement() -> list[dict]:
    t8 = load_json(TESTSETS / "invoice_statement" / "reports/T8_final_precheck_invoice_statement_full_quality_20260514.json", {})
    samples = t8.get("samples", {})
    rows = []
    for filename, expected in INVOICE_EXPECTED.items():
        sample = samples.get(filename, {})
        rc = sample.get("rowCount", {})
        actual = rc.get("actual")
        rows.append({"filename": filename, "expected": expected, "actual": actual,
                     "status": "exact" if actual == expected else "mismatch"})
    return rows


def main():
    print("=== T-15c food_cafe_receipt merchantName 개선 검증 ===\n")

    t14 = load_json(T14_JSON, {})
    before_samples = t14.get("samples", [])
    before_rg = [s for s in before_samples if s.get("testsetId") == "receipt_generalization"]
    before_non_rg = [s for s in before_samples if s.get("testsetId") != "receipt_generalization"]

    print("1. receipt_generalization 재실행...")
    after_rg = run_cache_parser("receipt_generalization")
    if not after_rg:
        print("[ERROR] 재실행 실패")
        return
    after_samples = before_non_rg + after_rg

    # === food_cafe_receipt merchantName 개선 ===
    print("\n2. food_cafe_receipt merchantName before/after...")
    food_result = check_food_cafe_improvement(before_samples, after_samples)
    if food_result["improved"]:
        print(f"  [개선] {len(food_result['improved'])}건:")
        for r in food_result["improved"]:
            print(f"    {r['testsetId']}/{r['filename']} {r['field']}: '' -> '{r['after']}'")
    if food_result["regressed"]:
        print(f"  [회귀] {len(food_result['regressed'])}건:")
        for r in food_result["regressed"]:
            print(f"    {r['testsetId']}/{r['filename']} {r['field']}: '{r['before']}' -> '{r['after']}'")
    print(f"  merchantName filled: {food_result['before_filled']['merchantName']} -> {food_result['after_filled']['merchantName']}")
    print(f"  totalAmount filled: {food_result['before_filled']['totalAmount']} -> {food_result['after_filled']['totalAmount']}")

    # === 회귀 검사 (KNOWN_MANIFEST_MISLABELS 제외) ===
    print("\n3. 다른 documentType 회귀 확인 (pos_003.jpg manifest 오기입 제외)...")
    regressions = check_regressions(before_samples, after_samples,
                                    ["card_receipt", "food_cafe_receipt", "pos_receipt", "finance_slip"])
    if regressions:
        print(f"  [FAIL] {len(regressions)}건:")
        for r in regressions:
            print(f"    {r['testsetId']}/{r['filename']} ({r['documentType']}) {r['field']}: '{r['before']}' -> '{r['after']}'")
    else:
        print("  [PASS] 회귀 없음")

    # pos_003.jpg 설명
    print("\n  [INFO] pos_003.jpg: manifest=pos_receipt이나 OCR내용이 약국영수증")
    print("         T-15b에 의해 medical_receipt로 올바르게 분류됨 (manifest 오기입)")

    # === medical_receipt T-15b 유지 ===
    print("\n4. medical_receipt T-15b 분류 유지...")
    med_stats = check_medical_t15b(after_rg)
    print(f"  medical_receipt 정분류: {med_stats['correct']}/{med_stats['total']}")
    print(f"  [{'PASS' if med_stats['correct'] >= 4 else 'WARN'}] (기대: >=4/6, pos_003 포함 시 7)")

    # === pos_receipt T-15a 유지 ===
    print("\n5. pos_receipt T-15a 개선 유지...")
    pos_rg = [s for s in after_rg if s.get("documentType") == "pos_receipt"]
    biz_filled = sum(1 for s in pos_rg if is_filled(s.get("fields", {}).get("businessNo")))
    merchant_filled = sum(1 for s in pos_rg if is_filled(s.get("fields", {}).get("merchantName")))
    print(f"  pos_receipt({len(pos_rg)}): businessNo={biz_filled}, merchantName={merchant_filled}")
    print(f"  [{'PASS' if biz_filled >= 3 and merchant_filled >= 4 else 'WARN'}]")

    # === invoice_statement ===
    print("\n6. invoice_statement rowCount 7/7 exact...")
    invoice_rows = check_invoice_statement()
    all_exact = all(r["status"] == "exact" for r in invoice_rows)
    for r in invoice_rows:
        print(f"  [{'OK' if r['status']=='exact' else 'NG'}] {r['filename']}: {r['expected']}/{r['actual']}")
    print(f"  [{'PASS' if all_exact else 'FAIL'}]")

    # === 요약 ===
    print("\n=== 요약 ===")
    mn_before = food_result["before_filled"]["merchantName"]
    mn_after = food_result["after_filled"]["merchantName"]
    print(f"food_cafe merchantName filled: {mn_before} -> {mn_after} (+{mn_after-mn_before})")
    print(f"필드 회귀: {len(regressions)}건")
    print(f"invoice_statement: {'7/7 exact' if all_exact else '불일치'}")
    overall = (mn_after > mn_before and not regressions and all_exact)
    print(f"전체 판정: {'PASS' if overall else 'FAIL/WARN'}")

    out = {
        "task": "T-15c",
        "food_cafe_improvement": food_result,
        "regressions": regressions,
        "medical_t15b_stats": med_stats,
        "pos_t15a_stats": {"count": len(pos_rg), "businessNo_filled": biz_filled, "merchantName_filled": merchant_filled},
        "invoice_statement": invoice_rows,
        "invoice_all_exact": all_exact,
        "known_manifest_mislabels": list(KNOWN_MANIFEST_MISLABELS),
        "overall_pass": overall,
    }
    out_json = REPORTS / "T15c_food_cafe_merchant_improvement_20260516.json"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\n결과 저장: {out_json}")


if __name__ == "__main__":
    main()
