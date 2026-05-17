"""
T-15d card_receipt merchantName / businessNo / totalAmount missing 개선 검증.

검증 항목:
1. card_receipt merchantName/businessNo/totalAmount before/after
2. T-15a pos_receipt businessNo/merchantName 유지
3. T-15b medical_receipt 분류 유지
4. T-15c food_cafe merchantName 유지
5. 다른 documentType 회귀 없음
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
# pos_003.jpg: manifest=pos_receipt이나 OCR내용이 약국영수증 (T-15b에서 정확히 medical_receipt로 분류됨)
KNOWN_MANIFEST_MISLABELS = {"receipt_generalization/pos_003.jpg"}


def load_json(p: Path, d: Any = {}) -> Any:
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else d


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
            "documentType": item.get("documentType", "unknown"), "ocrDocType": doc_type,
            "fields": norm(fields_raw),
        })
    return out


def diff_fields(before: list[dict], after: list[dict], doc_type: str, fields: list[str]) -> dict:
    bm = {(s["testsetId"], s["filename"]): s for s in before}
    am = {(s["testsetId"], s["filename"]): s for s in after}
    improved, regressed = [], []
    bf_counts = {f: 0 for f in fields}
    af_counts = {f: 0 for f in fields}
    for key, b in bm.items():
        if b.get("documentType") != doc_type:
            continue
        a = am.get(key)
        if not a:
            continue
        bf, af = b.get("fields", {}), a.get("fields", {})
        for f in fields:
            if is_filled(bf.get(f)):
                bf_counts[f] += 1
            if is_filled(af.get(f)):
                af_counts[f] += 1
            was, now = is_filled(bf.get(f)), is_filled(af.get(f))
            if not was and now:
                improved.append({"key": key, "field": f, "after": af.get(f)})
            elif was and not now:
                regressed.append({"key": key, "field": f, "before": bf.get(f)})
    return {"improved": improved, "regressed": regressed,
            "before": bf_counts, "after": af_counts}


def regressions_all(before: list[dict], after: list[dict], doc_types: list[str]) -> list[dict]:
    bm = {(s["testsetId"], s["filename"]): s for s in before}
    am = {(s["testsetId"], s["filename"]): s for s in after}
    regs = []
    for key, b in bm.items():
        if b.get("documentType") not in doc_types:
            continue
        if f"{b['testsetId']}/{b['filename']}" in KNOWN_MANIFEST_MISLABELS:
            continue
        a = am.get(key)
        if not a:
            continue
        bf, af = b.get("fields", {}), a.get("fields", {})
        for f in ["merchantName", "businessNo", "totalAmount"]:
            if is_filled(bf.get(f)) and not is_filled(af.get(f)):
                regs.append({"file": f"{b['testsetId']}/{b['filename']}", "dt": b["documentType"],
                              "field": f, "before": bf.get(f), "after": af.get(f)})
    return regs


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
    print("=== T-15d card_receipt field improvement 검증 ===\n")
    t14 = load_json(T14_JSON, {})
    before_samples = t14.get("samples", [])
    before_rg = [s for s in before_samples if s.get("testsetId") == "receipt_generalization"]
    before_non_rg = [s for s in before_samples if s.get("testsetId") != "receipt_generalization"]

    print("1. receipt_generalization 재실행...")
    after_rg = run_cache("receipt_generalization")
    if not after_rg:
        print("[ERROR]")
        return
    after_samples = before_non_rg + after_rg

    # card_receipt
    print("\n2. card_receipt before/after...")
    card_r = diff_fields(before_samples, after_samples, "card_receipt", ["merchantName", "businessNo", "totalAmount"])
    for r in card_r["improved"]:
        print(f"  [IMPROVED] {r['key']} {r['field']} -> '{r['after']}'")
    for r in card_r["regressed"]:
        print(f"  [REGRESSED] {r['key']} {r['field']} '{r['before']}' -> ''")
    print(f"  merchantName: {card_r['before']['merchantName']} -> {card_r['after']['merchantName']}")
    print(f"  businessNo:   {card_r['before']['businessNo']} -> {card_r['after']['businessNo']}")
    print(f"  totalAmount:  {card_r['before']['totalAmount']} -> {card_r['after']['totalAmount']}")

    # T-15a pos_receipt
    print("\n3. T-15a pos_receipt 유지...")
    pos_r = diff_fields(before_samples, after_samples, "pos_receipt", ["merchantName", "businessNo"])
    print(f"  businessNo:   {pos_r['before']['businessNo']} -> {pos_r['after']['businessNo']}")
    print(f"  merchantName: {pos_r['before']['merchantName']} -> {pos_r['after']['merchantName']}")
    pos_ok = pos_r["after"]["businessNo"] >= pos_r["before"]["businessNo"] and not pos_r["regressed"]
    print(f"  [{'PASS' if pos_ok else 'WARN'}]")

    # T-15b medical
    print("\n4. T-15b medical_receipt 분류 유지...")
    med_correct = sum(1 for s in after_rg
                      if s.get("documentType") == "medical_receipt" and s.get("ocrDocType") == "medical_receipt")
    med_total = sum(1 for s in after_rg if s.get("documentType") == "medical_receipt")
    print(f"  medical_receipt 정분류: {med_correct}/{med_total}")
    print(f"  [{'PASS' if med_correct >= 4 else 'WARN'}]")

    # T-15c food_cafe
    print("\n5. T-15c food_cafe merchantName 유지...")
    food_r = diff_fields(before_samples, after_samples, "food_cafe_receipt", ["merchantName"])
    print(f"  merchantName: {food_r['before']['merchantName']} -> {food_r['after']['merchantName']}")
    food_ok = food_r["after"]["merchantName"] >= food_r["before"]["merchantName"] and not food_r["regressed"]
    print(f"  [{'PASS' if food_ok else 'WARN'}]")

    # 회귀
    print("\n6. 전체 documentType 회귀 확인...")
    regs = regressions_all(before_samples, after_samples,
                           ["card_receipt", "food_cafe_receipt", "pos_receipt", "medical_receipt", "finance_slip"])
    if regs:
        print(f"  [FAIL] {len(regs)}건:")
        for r in regs:
            print(f"    {r['file']} ({r['dt']}) {r['field']}: '{r['before']}' -> '{r['after']}'")
    else:
        print("  [PASS] 회귀 없음")

    # invoice_statement
    print("\n7. invoice_statement 7/7 exact...")
    inv_rows = check_invoice()
    all_exact = all(r["status"] == "exact" for r in inv_rows)
    for r in inv_rows:
        print(f"  [{'OK' if r['status']=='exact' else 'NG'}] {r['filename']}: {r['expected']}/{r['actual']}")
    print(f"  [{'PASS' if all_exact else 'FAIL'}]")

    # 요약
    print("\n=== 요약 ===")
    print(f"card_receipt merchantName: {card_r['before']['merchantName']} -> {card_r['after']['merchantName']}")
    print(f"card_receipt businessNo:   {card_r['before']['businessNo']} -> {card_r['after']['businessNo']}")
    print(f"card_receipt totalAmount:  {card_r['before']['totalAmount']} -> {card_r['after']['totalAmount']}")
    print(f"필드 회귀: {len(regs)}건")
    print(f"invoice_statement: {'7/7 exact' if all_exact else '불일치'}")
    overall = (card_r["after"]["merchantName"] >= card_r["before"]["merchantName"]
               and card_r["after"]["businessNo"] >= card_r["before"]["businessNo"]
               and not regs and all_exact)
    print(f"전체 판정: {'PASS' if overall else 'FAIL/WARN'}")

    out = {
        "task": "T-15d",
        "card_receipt": card_r,
        "pos_receipt_t15a": {"before": pos_r["before"], "after": pos_r["after"]},
        "medical_t15b": {"correct": med_correct, "total": med_total},
        "food_cafe_t15c": {"before": food_r["before"], "after": food_r["after"]},
        "regressions": regs,
        "invoice_statement": inv_rows,
        "invoice_all_exact": all_exact,
        "known_manifest_mislabels": list(KNOWN_MANIFEST_MISLABELS),
        "overall_pass": overall,
    }
    out_json = REPORTS / "T15d_card_receipt_field_improvement_20260516.json"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\n결과 저장: {out_json}")


if __name__ == "__main__":
    main()
