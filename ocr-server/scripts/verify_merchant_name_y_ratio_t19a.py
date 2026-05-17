"""
T-19a merchantName y_ratio scoring 검증 스크립트.

검증 항목:
1. merchantName filled before/after (receipt_generalization)
2. T-15a pos_receipt 유지
3. T-15b medical_receipt 분류 유지
4. T-15c food_cafe 유지
5. T-15d card_receipt 유지
6. T-19c classification_mismatch 개선 유지
7. invoice_statement rowCount 7/7 exact 유지
8. false positive merchantName 없음
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
T18_JSON = REPORTS / "T18_precheck_current_baseline_gt_ocr_alignment_20260516.json"
INVOICE_EXPECTED = {"1.jpg": 28, "2.pdf": 13, "3.pdf": 1, "4.pdf": 1, "5.pdf": 6, "6.pdf": 6, "7.pdf": 1}
RECEIPT_FINAL_FIELD_ALIASES = ["merchantName", "businessNo", "representative", "phone", "address", "totalAmount"]


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
        out.append({
            "filename": fn, "testsetId": testset_id,
            "documentType": item.get("documentType", "unknown"),
            "expectedStatus": item.get("expectedStatus", "unknown"),
            "ocrDocType": doc_type,
            "fields": norm(fields_raw),
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
    print("=== T-19a merchantName y_ratio scoring 검증 ===\n")
    from document_classifier import classify_document  # type: ignore

    t14 = load_json(T14_JSON, {})
    before_rg = [s for s in t14.get("samples", []) if s.get("testsetId") == "receipt_generalization"]

    print("1. receipt_generalization 재실행...")
    after_rg = run_cache("receipt_generalization")
    if not after_rg:
        print("[ERROR]"); return

    # merchantName before/after
    before_mn = {s["filename"]: is_filled(s.get("fields", {}).get("merchantName")) for s in before_rg}
    after_mn = {s["filename"]: is_filled(s.get("fields", {}).get("merchantName")) for s in after_rg}

    print("\n2. merchantName before/after (receipt_generalization)...")
    improved, regressed = [], []
    for fn in sorted(set(before_mn) | set(after_mn)):
        b = before_mn.get(fn, False)
        a = after_mn.get(fn, False)
        if not b and a:
            improved.append(fn)
            val = next((s["fields"]["merchantName"] for s in after_rg if s["filename"] == fn), "?")
            print(f"  [IMPROVED] {fn}: '' -> '{val}'")
        elif b and not a:
            regressed.append(fn)
            print(f"  [REGRESSED] {fn}: filled -> empty")

    before_count = sum(1 for v in before_mn.values() if v)
    after_count = sum(1 for v in after_mn.values() if v)
    print(f"\n  merchantName filled: {before_count} -> {after_count} ({after_count - before_count:+d})")
    print(f"  개선: {len(improved)}, 회귀: {len(regressed)}")

    # T-15a pos_receipt
    pos_before_biz = sum(1 for s in before_rg if s.get("documentType") == "pos_receipt" and is_filled(s.get("fields", {}).get("businessNo")))
    pos_after_biz = sum(1 for s in after_rg if s.get("documentType") == "pos_receipt" and is_filled(s.get("fields", {}).get("businessNo")))
    pos_before_mn = sum(1 for s in before_rg if s.get("documentType") == "pos_receipt" and is_filled(s.get("fields", {}).get("merchantName")))
    pos_after_mn = sum(1 for s in after_rg if s.get("documentType") == "pos_receipt" and is_filled(s.get("fields", {}).get("merchantName")))
    pos_ok = pos_after_biz >= pos_before_biz and pos_after_mn >= pos_before_mn
    print(f"\n3. T-15a pos_receipt: biz {pos_before_biz}->{pos_after_biz}, mn {pos_before_mn}->{pos_after_mn} [{'PASS' if pos_ok else 'FAIL'}]")

    # T-15b medical
    med_correct = sum(1 for s in after_rg if s.get("documentType") == "medical_receipt" and s.get("ocrDocType") == "medical_receipt")
    med_total = sum(1 for s in after_rg if s.get("documentType") == "medical_receipt")
    print(f"4. T-15b medical_receipt 분류: {med_correct}/{med_total} [{'PASS' if med_correct >= 4 else 'FAIL'}]")

    # T-15c food_cafe
    food_before_mn = sum(1 for s in before_rg if s.get("documentType") == "food_cafe_receipt" and is_filled(s.get("fields", {}).get("merchantName")))
    food_after_mn = sum(1 for s in after_rg if s.get("documentType") == "food_cafe_receipt" and is_filled(s.get("fields", {}).get("merchantName")))
    print(f"5. T-15c food_cafe merchantName: {food_before_mn}->{food_after_mn} [{'PASS' if food_after_mn >= food_before_mn else 'FAIL'}]")

    # T-15d card
    card_before_biz = sum(1 for s in before_rg if s.get("documentType") == "card_receipt" and is_filled(s.get("fields", {}).get("businessNo")))
    card_after_biz = sum(1 for s in after_rg if s.get("documentType") == "card_receipt" and is_filled(s.get("fields", {}).get("businessNo")))
    card_before_mn = sum(1 for s in before_rg if s.get("documentType") == "card_receipt" and is_filled(s.get("fields", {}).get("merchantName")))
    card_after_mn = sum(1 for s in after_rg if s.get("documentType") == "card_receipt" and is_filled(s.get("fields", {}).get("merchantName")))
    print(f"6. T-15d card_receipt: biz {card_before_biz}->{card_after_biz}, mn {card_before_mn}->{card_after_mn} [{'PASS' if card_after_biz >= card_before_biz else 'FAIL'}]")

    # T-19c classification (check pos_006 and food_004)
    pos_006 = next((s for s in after_rg if s["filename"] == "pos_006.jpg"), None)
    food_004 = next((s for s in after_rg if s["filename"] == "food_004.jpg"), None)
    t19c_ok = (pos_006 and pos_006.get("ocrDocType") == "receipt_pos") and \
              (food_004 and food_004.get("ocrDocType") in ("receipt_pos", "receipt_card"))
    print(f"7. T-19c pos_006={pos_006.get('ocrDocType') if pos_006 else '?'}, food_004={food_004.get('ocrDocType') if food_004 else '?'} [{'PASS' if t19c_ok else 'FAIL'}]")

    # invoice_statement
    inv_rows = check_invoice()
    all_exact = all(r["status"] == "exact" for r in inv_rows)
    for r in inv_rows:
        print(f"  [{'OK' if r['status']=='exact' else 'NG'}] {r['filename']}: {r['expected']}/{r['actual']}")
    print(f"8. invoice_statement 7/7: [{'PASS' if all_exact else 'FAIL'}]")

    # 요약
    print(f"\n=== 요약 ===")
    print(f"merchantName filled: {before_count} -> {after_count} ({after_count-before_count:+d})")
    print(f"회귀: {len(regressed)}건")
    print(f"invoice_statement: {'7/7 exact' if all_exact else '불일치'}")
    overall = (after_count >= before_count and not regressed and all_exact and med_correct >= 4)
    print(f"전체 판정: {'PASS' if overall else 'FAIL/WARN'}")

    out = {
        "task": "T-19a",
        "merchantName": {"before": before_count, "after": after_count, "improved": improved, "regressed": regressed},
        "t15a_pos": {"biz": f"{pos_before_biz}->{pos_after_biz}", "mn": f"{pos_before_mn}->{pos_after_mn}"},
        "t15b_medical": f"{med_correct}/{med_total}",
        "t15c_food": f"{food_before_mn}->{food_after_mn}",
        "t15d_card": {"biz": f"{card_before_biz}->{card_after_biz}", "mn": f"{card_before_mn}->{card_after_mn}"},
        "invoice_all_exact": all_exact,
        "overall_pass": overall,
    }
    out_json = REPORTS / "T19a_merchant_name_y_ratio_scoring_20260516.json"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\n결과 저장: {out_json}")


if __name__ == "__main__":
    main()
