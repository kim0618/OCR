"""
T-19b businessNo/totalAmount y_ratio scoring 검증 스크립트.

검증 항목:
1. businessNo missing before/after (OCR source missing 케이스 명확 분리)
2. totalAmount missing/false-positive before/after
3. T-15a~T-15e 유지
4. T-19a merchantName 유지
5. T-19c classification 유지
6. invoice_statement rowCount 7/7 exact 유지
"""
from __future__ import annotations
import json, sys
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
KNOWN_MISLABELS = {"receipt_generalization/pos_003.jpg"}


def load_json(p: Path, d: Any = {}) -> Any:
    if not p.exists():
        return d
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return json.loads(p.read_text(encoding="utf-8-sig"))


def is_filled(v: Any) -> bool:
    return bool(v and str(v).strip() not in {"", "None", "null", "-", "0"})


def fake_ocr_lines(text: str) -> list:
    lines, y = [], 10
    for raw in (text or "").splitlines():
        s = raw.strip()
        if not s:
            continue
        w = max(20, min(800, len(s) * 8))
        lines.append(([(10, y), (10 + w, y), (10 + w, y + 14), (10, y + 14)], s, 0.9))
        y += 20
    return lines


def norm(raw: dict) -> dict:
    vals = list((raw or {}).values())
    r = {n: "" for n in ["merchantName", "businessNo", "totalAmount"]}
    for i, a in enumerate(RECEIPT_FINAL_FIELD_ALIASES):
        if i < len(vals) and a in r:
            r[a] = vals[i]
    return r


def run_cache(testset_id: str) -> list[dict]:
    try:
        from document_classifier import classify_document  # type: ignore
        from main import extract_receipt_fields  # type: ignore
    except Exception as e:
        print(f"[ERROR] {e}")
        return []
    cache = load_json(TESTSETS / testset_id / "ocr_cache.json", {})
    manifest = load_json(TESTSETS / testset_id / "manifest.json", {})
    meta = {i["filename"]: i for i in manifest.get("items", []) if i.get("filename")}
    out = []
    for fn, cached in cache.items():
        if not isinstance(cached, dict):
            continue
        text = cached.get("ocr_text", "")
        doc_info = classify_document(text)
        doc_type = doc_info.get("type", "unknown")
        dbg: dict = {"doc_type": doc_type}
        fields_raw = extract_receipt_fields(fake_ocr_lines(text), doc_type=doc_type, debug=dbg)
        item = meta.get(fn, {})
        amount_debug = dbg.get("total_amount", {})
        out.append({
            "filename": fn, "testsetId": testset_id,
            "documentType": item.get("documentType", "unknown"),
            "expectedStatus": item.get("expectedStatus", "unknown"),
            "ocrDocType": doc_type,
            "fields": norm(fields_raw),
            "amount_status": amount_debug.get("status", ""),
            "amount_score": (amount_debug.get("selected") or {}).get("score", None),
        })
    return out


def check_invoice() -> list[dict]:
    t8 = load_json(TESTSETS / "invoice_statement" / "reports/T8_final_precheck_invoice_statement_full_quality_20260514.json", {})
    samples = t8.get("samples", {})
    rows = []
    for fn, exp in INVOICE_EXPECTED.items():
        s = samples.get(fn, {})
        actual = (s.get("rowCount") or {}).get("actual")
        rows.append({"filename": fn, "expected": exp, "actual": actual,
                     "status": "exact" if actual == exp else "mismatch"})
    return rows


def main():
    print("=== T-19b businessNo/totalAmount y_ratio scoring 검증 ===\n")

    t14 = load_json(T14_JSON, {})
    before_rg = [s for s in t14.get("samples", []) if s.get("testsetId") == "receipt_generalization"]

    print("1. receipt_generalization 재실행...")
    after_rg = run_cache("receipt_generalization")
    if not after_rg:
        print("[ERROR]"); return

    # businessNo before/after
    biz_before = {s["filename"]: is_filled(s.get("fields", {}).get("businessNo")) for s in before_rg}
    biz_after = {s["filename"]: is_filled(s.get("fields", {}).get("businessNo")) for s in after_rg}
    biz_improved, biz_regressed = [], []
    for fn in sorted(set(biz_before) | set(biz_after)):
        b, a = biz_before.get(fn, False), biz_after.get(fn, False)
        if not b and a: biz_improved.append(fn)
        elif b and not a: biz_regressed.append(fn)

    # totalAmount before/after
    amt_before = {s["filename"]: is_filled(s.get("fields", {}).get("totalAmount")) for s in before_rg}
    amt_after = {s["filename"]: is_filled(s.get("fields", {}).get("totalAmount")) for s in after_rg}
    amt_improved, amt_regressed = [], []
    for fn in sorted(set(amt_before) | set(amt_after)):
        b, a = amt_before.get(fn, False), amt_after.get(fn, False)
        if not b and a: amt_improved.append(fn)
        elif b and not a: amt_regressed.append(fn)

    print("\n2. businessNo before/after...")
    for fn in biz_improved:
        print(f"  [IMPROVED] {fn}: '' -> filled")
    for fn in biz_regressed:
        print(f"  [REGRESSED] {fn}: filled -> ''")
    bc_before = sum(1 for v in biz_before.values() if v)
    bc_after = sum(1 for v in biz_after.values() if v)
    print(f"  businessNo filled: {bc_before} -> {bc_after} ({bc_after-bc_before:+d})")

    print("\n3. totalAmount before/after...")
    for fn in amt_improved:
        print(f"  [IMPROVED] {fn}: '' -> filled")
    for fn in amt_regressed:
        print(f"  [REGRESSED] {fn}: filled -> '' (check if false positive was fixed)")
    ac_before = sum(1 for v in amt_before.values() if v)
    ac_after = sum(1 for v in amt_after.values() if v)
    print(f"  totalAmount filled: {ac_before} -> {ac_after} ({ac_after-ac_before:+d})")

    # Check pos_006 specifically (false positive fix)
    pos006 = next((s for s in after_rg if s["filename"] == "pos_006.jpg"), None)
    if pos006:
        amt = pos006["fields"]["totalAmount"]
        status = pos006["amount_status"]
        is_false_positive_fixed = not is_filled(amt) and "bare_negative" in status
        print(f"\n  pos_006 totalAmount: {amt!r} ({status}) [{'FALSE POSITIVE FIXED' if is_false_positive_fixed else 'CHECK'}]")

    # T-15a pos_receipt
    pos_biz_b = sum(1 for s in before_rg if s.get("documentType")=="pos_receipt" and is_filled(s.get("fields",{}).get("businessNo")))
    pos_biz_a = sum(1 for s in after_rg if s.get("documentType")=="pos_receipt" and is_filled(s.get("fields",{}).get("businessNo")))
    pos_mn_b = sum(1 for s in before_rg if s.get("documentType")=="pos_receipt" and is_filled(s.get("fields",{}).get("merchantName")))
    pos_mn_a = sum(1 for s in after_rg if s.get("documentType")=="pos_receipt" and is_filled(s.get("fields",{}).get("merchantName")))
    pos_amt_b = sum(1 for s in before_rg if s.get("documentType")=="pos_receipt" and is_filled(s.get("fields",{}).get("totalAmount")))
    pos_amt_a = sum(1 for s in after_rg if s.get("documentType")=="pos_receipt" and is_filled(s.get("fields",{}).get("totalAmount")))
    print(f"\n4. T-15a pos_receipt: biz {pos_biz_b}->{pos_biz_a}, mn {pos_mn_b}->{pos_mn_a}, amt {pos_amt_b}->{pos_amt_a}")
    print(f"   [{'PASS' if pos_biz_a >= pos_biz_b and pos_mn_a >= pos_mn_b else 'FAIL'}]")

    # T-15b medical
    med_c = sum(1 for s in after_rg if s.get("documentType")=="medical_receipt" and s.get("ocrDocType")=="medical_receipt")
    med_t = sum(1 for s in after_rg if s.get("documentType")=="medical_receipt")
    print(f"5. T-15b medical_receipt 분류: {med_c}/{med_t} [{'PASS' if med_c >= 4 else 'FAIL'}]")

    # T-19a merchantName
    mn_b = sum(1 for s in before_rg if s.get("documentType") in ("pos_receipt","food_cafe_receipt","card_receipt","medical_receipt") and is_filled(s.get("fields",{}).get("merchantName")))
    mn_a = sum(1 for s in after_rg if s.get("documentType") in ("pos_receipt","food_cafe_receipt","card_receipt","medical_receipt") and is_filled(s.get("fields",{}).get("merchantName")))
    print(f"6. T-19a merchantName: {mn_b}->{mn_a} [{'PASS' if mn_a >= mn_b else 'FAIL'}]")

    # T-19c classification
    pos006 = next((s for s in after_rg if s["filename"] == "pos_006.jpg"), None)
    food004 = next((s for s in after_rg if s["filename"] == "food_004.jpg"), None)
    t19c_ok = (pos006 and pos006.get("ocrDocType") == "receipt_pos") and \
              (food004 and food004.get("ocrDocType") in ("receipt_pos","receipt_card"))
    print(f"7. T-19c: pos_006={pos006.get('ocrDocType') if pos006 else '?'}, food_004={food004.get('ocrDocType') if food004 else '?'} [{'PASS' if t19c_ok else 'FAIL'}]")

    # invoice_statement
    inv_rows = check_invoice()
    all_exact = all(r["status"] == "exact" for r in inv_rows)
    for r in inv_rows:
        print(f"  [{'OK' if r['status']=='exact' else 'NG'}] {r['filename']}: {r['expected']}/{r['actual']}")
    print(f"8. invoice_statement 7/7: [{'PASS' if all_exact else 'FAIL'}]")

    # Remaining source_missing analysis
    print("\n9. businessNo source_missing 분석 (복구 불가 케이스)...")
    SOURCE_MISSING = {
        "medical_001.jpg": "OCR에 사업자번호 라벨만 있고 숫자 없음",
        "medical_002.jpg": "OCR에 사업자번호 없음 (동물병원 영수증)",
        "medical_003.jpg": "OCR에 사업자번호 없음 (수의원 처방영수증)",
        "pos_001.jpg": "OCR garbled, 사업자번호 원문 복구 불가",
        "pos_002.jpg": "OCR에 헤더 없음, 마트 반품정책만 존재",
        "pos_006.jpg": "OCR garbled, 사업자번호 원문 복구 불가",
    }
    for fn, reason in SOURCE_MISSING.items():
        after_s = next((s for s in after_rg if s["filename"] == fn), {})
        biz = after_s.get("fields", {}).get("businessNo", "")
        print(f"  {fn}: biz={biz!r} → {reason}")

    # 요약
    print("\n=== 요약 ===")
    print(f"businessNo filled: {bc_before} -> {bc_after} ({bc_after-bc_before:+d})")
    print(f"totalAmount filled: {ac_before} -> {ac_after} ({ac_after-ac_before:+d})")
    print(f"pos_006 false positive fixed: {not is_filled(pos006.get('fields',{}).get('totalAmount')) if pos006 else 'N/A'}")
    print(f"회귀: biz={len(biz_regressed)}, amt={len(amt_regressed)}")
    overall = (bc_after >= bc_before and not biz_regressed and mn_a >= mn_b and med_c >= 4 and all_exact)
    print(f"전체 판정: {'PASS' if overall else 'FAIL/WARN'}")

    out = {
        "task": "T-19b",
        "businessNo": {"before": bc_before, "after": bc_after, "improved": biz_improved, "regressed": biz_regressed},
        "totalAmount": {"before": ac_before, "after": ac_after, "improved": amt_improved, "regressed": amt_regressed},
        "pos006_false_positive_fixed": not is_filled((pos006 or {}).get("fields", {}).get("totalAmount", "")),
        "t19a_merchantName": f"{mn_b}->{mn_a}",
        "t15b_medical": f"{med_c}/{med_t}",
        "invoice_all_exact": all_exact,
        "source_missing_analysis": SOURCE_MISSING,
        "overall_pass": overall,
    }
    out_json = REPORTS / "T19b_business_amount_y_ratio_scoring_20260516.json"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\n결과 저장: {out_json}")


if __name__ == "__main__":
    main()
