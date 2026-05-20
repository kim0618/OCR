import argparse
import json
import sys
import time
from pathlib import Path

import requests


ROOT = Path(r"D:/Free_Vue/OCR")
INVOICE_DIR = ROOT / "mysuit-ocr/public/data/testsets/invoice_statement"
BASELINE_DIR = ROOT / "mysuit-ocr/public/data/testsets/baseline"
OUT_DIR = ROOT / "tmp/safe_perf_jpeg_quality_regression"

INVOICE_CASES = [
    {"name": "invoice_1", "template_id": "TPL-31D13CF3", "file": "1.jpg", "expected_rows": 28, "documentType": "invoice_statement"},
    {"name": "invoice_2", "template_id": "TPL-5A8C2374", "file": "2.pdf", "expected_rows": 13, "documentType": "invoice_statement"},
    {"name": "invoice_3", "template_id": "TPL-E4B15A22", "file": "3.pdf", "expected_rows": 1, "documentType": "invoice_statement"},
    {"name": "invoice_4", "template_id": "TPL-FD07531C", "file": "4.pdf", "expected_rows": 1, "documentType": "invoice_statement"},
    {"name": "invoice_5", "template_id": "TPL-B8936EDE", "file": "5.pdf", "expected_rows": 6, "documentType": "invoice_statement"},
    {"name": "invoice_6", "template_id": "TPL-95328E52", "file": "6.pdf", "expected_rows": 6, "documentType": "invoice_statement"},
    {"name": "invoice_7", "template_id": "TPL-3AFD383E", "file": "7.pdf", "expected_rows": 1, "documentType": "invoice_statement"},
]

RECEIPT_CASES = [
    {"name": "receipt_1", "template_id": "TPL-003", "file": "1.jpg"},
    {"name": "receipt_2", "template_id": "TPL-003", "file": "2.jpg"},
    {"name": "receipt_3", "template_id": "TPL-003", "file": "3.jpg"},
    {"name": "receipt_4", "template_id": "TPL-003", "file": "4.jpg"},
    {"name": "receipt_7", "template_id": "TPL-003", "file": "7.jpg"},
    {"name": "receipt_8", "template_id": "TPL-003", "file": "8.jpg"},
    {"name": "receipt_10", "template_id": "TPL-003", "file": "10.jpg"},
    {"name": "receipt_a1", "template_id": "TPL-003", "file": "a1.jpg"},
    {"name": "receipt_a2", "template_id": "TPL-003", "file": "a2.jpg"},
]

RECEIPT_FIELDS = ["회사명", "사업자번호", "대표자", "전화번호", "주소", "총합계금액"]


def load_templates(base_url: str) -> dict:
    try:
        res = requests.get(f"{base_url}/templates", timeout=30)
        res.raise_for_status()
        payload = res.json()
    except Exception as exc:
        print(f"[WARN] template fetch failed: {exc}")
        return {}
    if isinstance(payload, dict):
        items = (payload.get("resultMap") or {}).get("templateList") or payload.get("templates") or []
    else:
        items = payload
    by_id = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        tid = str(item.get("template_id") or "")
        tpl = item.get("template_json") or {}
        if isinstance(tpl, str):
            try:
                tpl = json.loads(tpl)
            except Exception:
                tpl = {}
        if tid:
            by_id[tid] = tpl
    return by_id


def invoice_row_count(resp: dict) -> int:
    rows = (resp.get("document_fields") or {}).get("tableRows") or []
    return len(rows) if isinstance(rows, list) else 0


def invoice_core(resp: dict) -> dict:
    doc = resp.get("document_fields") or {}
    return {
        "doc_type": resp.get("doc_type") or resp.get("documentType"),
        "supplierBusinessNo": doc.get("supplierBusinessNo", ""),
        "supplierName": doc.get("supplierName", ""),
        "buyerBusinessNo": doc.get("buyerBusinessNo", ""),
        "buyerName": doc.get("buyerName", ""),
        "totalAmount": doc.get("totalAmount", ""),
        "rowCount": invoice_row_count(resp),
    }


def receipt_core(resp: dict) -> dict:
    fields = resp.get("receipt_fields") or {}
    return {key: fields.get(key, "") for key in RECEIPT_FIELDS}


def post_case(base_url: str, case: dict, kind: str, templates: dict) -> dict:
    file_path = (INVOICE_DIR if kind == "invoice" else BASELINE_DIR) / case["file"]
    tpl = templates.get(case["template_id"], {})
    form = {
        "template_id": case["template_id"],
        "model_id": "paddleocr",
    }
    document_type = case.get("documentType") or tpl.get("documentType") or ""
    if document_type:
        form["documentType"] = document_type
    regions = tpl.get("regions") or []
    if kind == "invoice" and regions:
        form["regions"] = json.dumps(regions, ensure_ascii=False)
    start = time.perf_counter()
    with file_path.open("rb") as f:
        res = requests.post(
            f"{base_url}/ocr/extract",
            data=form,
            files={"file": (case["file"], f)},
            timeout=360,
        )
    elapsed = time.perf_counter() - start
    res.raise_for_status()
    data = res.json()
    data["_regression_meta"] = {
        "name": case["name"],
        "kind": kind,
        "file": str(file_path),
        "wallClockSeconds": round(elapsed, 3),
        "responseSizeBytes": len(res.content),
    }
    return data


def run_phase(base_url: str, phase: str) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    templates = load_templates(base_url)
    summary = {"phase": phase, "baseUrl": base_url, "invoice": [], "receipt": []}
    for case in INVOICE_CASES:
        print(f"[{phase}] {case['name']} {case['file']}", flush=True)
        data = post_case(base_url, case, "invoice", templates)
        (OUT_DIR / f"{phase}_{case['name']}.json").write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        core = invoice_core(data)
        summary["invoice"].append({
            "name": case["name"],
            "file": case["file"],
            "expectedRows": case["expected_rows"],
            "actualRows": core["rowCount"],
            "rowCountPass": core["rowCount"] == case["expected_rows"],
            "processing_time": data.get("processing_time"),
            "wallClockSeconds": data["_regression_meta"]["wallClockSeconds"],
            "responseSizeBytes": data["_regression_meta"]["responseSizeBytes"],
            "core": core,
        })
    for case in RECEIPT_CASES:
        print(f"[{phase}] {case['name']} {case['file']}", flush=True)
        data = post_case(base_url, case, "receipt", templates)
        (OUT_DIR / f"{phase}_{case['name']}.json").write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        core = receipt_core(data)
        filled = sum(1 for v in core.values() if str(v).strip())
        summary["receipt"].append({
            "name": case["name"],
            "file": case["file"],
            "processing_time": data.get("processing_time"),
            "wallClockSeconds": data["_regression_meta"]["wallClockSeconds"],
            "responseSizeBytes": data["_regression_meta"]["responseSizeBytes"],
            "fields": core,
            "filledCount": filled,
            "fillRate": round(filled / len(RECEIPT_FIELDS), 4),
        })
    out = OUT_DIR / f"{phase}_summary.json"
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] wrote {out}", flush=True)


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def compare() -> None:
    before = read_json(OUT_DIR / "before_summary.json")
    after = read_json(OUT_DIR / "after_summary.json")
    result = {"pass": True, "invoice": [], "receipt": [], "sizes": {}}
    before_invoice = {row["name"]: row for row in before["invoice"]}
    after_invoice = {row["name"]: row for row in after["invoice"]}
    for case in INVOICE_CASES:
        name = case["name"]
        b = before_invoice[name]
        a = after_invoice[name]
        same_core = b["core"] == a["core"]
        row_ok = b["actualRows"] == a["actualRows"] == case["expected_rows"]
        ok = same_core and row_ok
        result["pass"] = result["pass"] and ok
        result["invoice"].append({
            "name": name,
            "file": case["file"],
            "sameCore": same_core,
            "rowCountOk": row_ok,
            "beforeRows": b["actualRows"],
            "afterRows": a["actualRows"],
            "beforeSizeBytes": b["responseSizeBytes"],
            "afterSizeBytes": a["responseSizeBytes"],
        })
    before_receipt = {row["name"]: row for row in before["receipt"]}
    after_receipt = {row["name"]: row for row in after["receipt"]}
    for case in RECEIPT_CASES:
        name = case["name"]
        b = before_receipt[name]
        a = after_receipt[name]
        same_fields = b["fields"] == a["fields"]
        same_fill = b["filledCount"] == a["filledCount"]
        ok = same_fields and same_fill
        result["pass"] = result["pass"] and ok
        result["receipt"].append({
            "name": name,
            "file": case["file"],
            "sameReceiptFields": same_fields,
            "sameFilledCount": same_fill,
            "beforeFillRate": b["fillRate"],
            "afterFillRate": a["fillRate"],
            "beforeSizeBytes": b["responseSizeBytes"],
            "afterSizeBytes": a["responseSizeBytes"],
        })
    before_total = sum(row["responseSizeBytes"] for row in before["invoice"] + before["receipt"])
    after_total = sum(row["responseSizeBytes"] for row in after["invoice"] + after["receipt"])
    result["sizes"] = {
        "beforeTotalBytes": before_total,
        "afterTotalBytes": after_total,
        "reductionBytes": before_total - after_total,
        "reductionPercent": round((before_total - after_total) / before_total * 100, 2) if before_total else 0,
    }
    out = OUT_DIR / "compare_summary.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
    if not result["pass"]:
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:9109")
    parser.add_argument("--phase", choices=["before", "after"])
    parser.add_argument("--compare", action="store_true")
    args = parser.parse_args()
    if args.phase:
        run_phase(args.base_url.rstrip("/"), args.phase)
    if args.compare:
        compare()
    if not args.phase and not args.compare:
        parser.error("use --phase before, --phase after, or --compare")


if __name__ == "__main__":
    main()
