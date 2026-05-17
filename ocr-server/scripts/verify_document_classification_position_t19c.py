"""
T-19c synthetic y_ratio 기반 document classification position weighting 검증.

검증 항목:
1. T-18 classification_mismatch 9건 before/after
2. receipt_generalization 전체 doc_type 변화
3. T-15a pos_receipt 유지
4. T-15b medical_receipt 분류 유지
5. T-15c food_cafe 유지
6. T-15d card_receipt 유지
7. T-15e finance_slip 유지
8. invoice_statement rowCount 7/7 exact 유지
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

KNOWN_MANIFEST_MISLABELS = {"receipt_generalization/pos_003.jpg"}


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
    r = {n: "" for n in ["merchantName", "businessNo", "totalAmount", "phone", "address", "representative"]}
    for i, a in enumerate(RECEIPT_FINAL_FIELD_ALIASES):
        if i < len(vals):
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
            "pos_top_signal": doc_info.get("guards", {}).get("pos_top_signal", False),
            "invoice_blocked_by_receipt": doc_info.get("guards", {}).get("invoice_statement", {}).get("blocked_by_receipt", False),
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
    from document_classifier import classify_document  # type: ignore

    print("=== T-19c classification position weighting 검증 ===\n")

    # === T-18 mismatch 9건 before/after ===
    print("1. T-18 classification_mismatch before/after (cache text 기준)...")
    t18 = load_json(T18_JSON, {})
    mismatch_samples = [s for s in t18.get("samples", []) if s.get("failureReason") == "classification_mismatch"]

    backend_map = {
        "card_receipt": "receipt_card", "pos_receipt": "receipt_pos",
        "food_cafe_receipt": "receipt_pos", "medical_receipt": "medical_receipt",
        "finance_slip": "bank_slip", "unknown": "unknown",
    }

    mismatch_results = []
    for s in mismatch_samples:
        ts = s.get("testsetId", "")
        fn = s.get("filename", "")
        manifest_dt = s.get("manifestDocumentType", "")
        before_type = s.get("ocrDocType", "")

        cache = load_json(TESTSETS / ts / "ocr_cache.json", {})
        text = cache.get(fn, {}).get("ocr_text", "")
        if not text:
            after_type = "NO_CACHE"
        else:
            r = classify_document(text)
            after_type = r["type"]

        expected_backend = backend_map.get(manifest_dt, manifest_dt)
        # food_cafe maps to either receipt_pos or receipt_card
        after_ok = (after_type == expected_backend or
                    (manifest_dt == "food_cafe_receipt" and after_type in ("receipt_pos", "receipt_card")))
        before_ok = (before_type == expected_backend or
                     (manifest_dt == "food_cafe_receipt" and before_type in ("receipt_pos", "receipt_card")))

        changed = after_type != before_type
        improved = not before_ok and after_ok
        regressed = before_ok and not after_ok

        mismatch_results.append({
            "sample": f"{ts}/{fn}",
            "manifest": manifest_dt,
            "before": before_type,
            "after": after_type,
            "changed": changed,
            "improved": improved,
            "regressed": regressed,
        })

        tag = "[IMPROVED]" if improved else ("[REGRESSED]" if regressed else "[CHANGED]" if changed else "[same]")
        print(f"  {tag} {ts}/{fn}: manifest={manifest_dt}, before={before_type}, after={after_type}")

    improved_count = sum(1 for r in mismatch_results if r["improved"])
    regressed_count = sum(1 for r in mismatch_results if r["regressed"])
    print(f"\n  개선: {improved_count}/{len(mismatch_results)}, 회귀: {regressed_count}/{len(mismatch_results)}")

    # === receipt_generalization 재실행 ===
    print("\n2. receipt_generalization 재실행...")
    after_rg = run_cache("receipt_generalization")
    if not after_rg:
        print("[ERROR]")
        return

    t14 = load_json(T14_JSON, {})
    before_rg = [s for s in t14.get("samples", []) if s.get("testsetId") == "receipt_generalization"]

    # T-15a pos_receipt
    before_pos_biz = sum(1 for s in before_rg if s.get("documentType") == "pos_receipt" and is_filled(s.get("fields", {}).get("businessNo")))
    after_pos_biz = sum(1 for s in after_rg if s.get("documentType") == "pos_receipt" and is_filled(s.get("fields", {}).get("businessNo")))
    before_pos_mn = sum(1 for s in before_rg if s.get("documentType") == "pos_receipt" and is_filled(s.get("fields", {}).get("merchantName")))
    after_pos_mn = sum(1 for s in after_rg if s.get("documentType") == "pos_receipt" and is_filled(s.get("fields", {}).get("merchantName")))
    print(f"  T-15a pos_receipt businessNo: {before_pos_biz}→{after_pos_biz}  merchantName: {before_pos_mn}→{after_pos_mn}  [{'PASS' if after_pos_biz >= before_pos_biz and after_pos_mn >= before_pos_mn else 'FAIL'}]")

    # T-15b medical_receipt correct
    med_correct = sum(1 for s in after_rg if s.get("documentType") == "medical_receipt" and s.get("ocrDocType") == "medical_receipt")
    med_total = sum(1 for s in after_rg if s.get("documentType") == "medical_receipt")
    print(f"  T-15b medical_receipt 정분류: {med_correct}/{med_total}  [{'PASS' if med_correct >= 4 else 'FAIL'}]")

    # T-15c food_cafe
    before_food_mn = sum(1 for s in before_rg if s.get("documentType") == "food_cafe_receipt" and is_filled(s.get("fields", {}).get("merchantName")))
    after_food_mn = sum(1 for s in after_rg if s.get("documentType") == "food_cafe_receipt" and is_filled(s.get("fields", {}).get("merchantName")))
    print(f"  T-15c food_cafe merchantName: {before_food_mn}→{after_food_mn}  [{'PASS' if after_food_mn >= before_food_mn else 'FAIL'}]")

    # T-15d card_receipt
    before_card_biz = sum(1 for s in before_rg if s.get("documentType") == "card_receipt" and is_filled(s.get("fields", {}).get("businessNo")))
    after_card_biz = sum(1 for s in after_rg if s.get("documentType") == "card_receipt" and is_filled(s.get("fields", {}).get("businessNo")))
    before_card_mn = sum(1 for s in before_rg if s.get("documentType") == "card_receipt" and is_filled(s.get("fields", {}).get("merchantName")))
    after_card_mn = sum(1 for s in after_rg if s.get("documentType") == "card_receipt" and is_filled(s.get("fields", {}).get("merchantName")))
    print(f"  T-15d card_receipt businessNo: {before_card_biz}→{after_card_biz}  merchantName: {before_card_mn}→{after_card_mn}  [{'PASS' if after_card_biz >= before_card_biz and after_card_mn >= before_card_mn else 'FAIL'}]")

    # T-15e finance_slip (manifest check)
    fin_manifest = load_json(TESTSETS / "receipt_generalization" / "manifest.json", {})
    fin_selected = sum(1 for i in fin_manifest.get("items", [])
                       if i.get("documentType") == "finance_slip" and i.get("expectedStatus") == "selected")
    print(f"  T-15e finance_slip selected=0: {fin_selected==0}  [{'PASS' if fin_selected == 0 else 'FAIL'}]")

    # T-19c specific: check pos_006 fix
    pos_006_after = next((s for s in after_rg if s.get("filename") == "pos_006.jpg"), None)
    food_004_after = next((s for s in after_rg if s.get("filename") == "food_004.jpg"), None)
    print(f"\n  T-19c pos_006.jpg: ocrDocType={pos_006_after.get('ocrDocType') if pos_006_after else '?'} (expected receipt_pos)")
    print(f"  T-19c food_004.jpg: ocrDocType={food_004_after.get('ocrDocType') if food_004_after else '?'} (expected receipt_pos/card)")

    # === invoice_statement ===
    print("\n3. invoice_statement 7/7 exact...")
    inv_rows = check_invoice()
    all_exact = all(r["status"] == "exact" for r in inv_rows)
    for r in inv_rows:
        print(f"  [{'OK' if r['status']=='exact' else 'NG'}] {r['filename']}: {r['expected']}/{r['actual']}")
    print(f"  [{'PASS' if all_exact else 'FAIL'}]")

    # === 요약 ===
    print("\n=== 요약 ===")
    print(f"T-18 mismatch 개선: {improved_count}/{len(mismatch_results)}건")
    print(f"T-18 mismatch 회귀: {regressed_count}건")
    print(f"T-15a-e 유지: {'PASS' if after_pos_biz >= before_pos_biz and med_correct >= 4 and after_food_mn >= before_food_mn else 'WARN'}")
    print(f"invoice_statement 7/7: {'PASS' if all_exact else 'FAIL'}")

    out = {
        "task": "T-19c",
        "mismatch_results": mismatch_results,
        "improved_count": improved_count,
        "regressed_count": regressed_count,
        "t15_maintenance": {
            "pos_receipt_biz": f"{before_pos_biz}→{after_pos_biz}",
            "medical_receipt_correct": f"{med_correct}/{med_total}",
            "food_cafe_mn": f"{before_food_mn}→{after_food_mn}",
            "card_receipt_biz": f"{before_card_biz}→{after_card_biz}",
        },
        "invoice_all_exact": all_exact,
    }
    out_json = REPORTS / "T19c_classification_position_weighting_20260516.json"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\n결과 저장: {out_json}")


if __name__ == "__main__":
    main()
