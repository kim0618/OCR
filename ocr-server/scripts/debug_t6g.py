"""T-6g debug script — row extraction analysis for 1.jpg and 2.pdf"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.verify_invoice_table_rows_t6d import make_synthetic_lines, EXPECTED
from extractors.invoice_statement import extract_invoice_statement_fields

cache_path = ROOT.parent / "mysuit-ocr" / "public" / "data" / "testsets" / "invoice_statement" / "ocr_cache.json"
cache = json.loads(cache_path.read_text("utf-8"))

for fname in ["1.jpg", "2.pdf", "5.pdf", "6.pdf"]:
    entry = cache.get(fname, {})
    ocr_text = entry.get("ocr_text", "")
    exp = EXPECTED.get(fname, {})
    tec = {"required": exp.get("required", []), "optional": exp.get("optional", [])}
    synth = make_synthetic_lines(ocr_text)
    debug = {}
    fields = extract_invoice_statement_fields(synth, debug=debug, table_expected_columns=tec)

    inv = debug.get("invoice_statement", {})
    tbl = inv.get("table", {})
    tdbg = tbl.get("tableDebug", {})

    rc = fields.get("rowCount")
    src = tdbg.get("extractionSource", "?")
    tec_used = tdbg.get("expectedColumnsUsed", False)
    matched = tdbg.get("matchedHeaders", [])
    band_found = tdbg.get("headerBandFound", False)
    band = tdbg.get("selectedHeaderBand")
    bnd_cnt = len(tdbg.get("boundaries", []))
    rej = tdbg.get("rejectedRows", [])
    reason_counts: dict = {}
    for r in rej:
        rn = r.get("reason", "unknown")
        reason_counts[rn] = reason_counts.get(rn, 0) + 1
    row_end = tdbg.get("rowEndReason")
    fb = tdbg.get("fallbackReason")

    print(f"=== {fname} ===")
    print(f"  rowCount: {rc}")
    print(f"  extractionSource: {src}")
    print(f"  expectedColumnsUsed: {tec_used}")
    print(f"  matchedHeaders: {matched}")
    print(f"  headerBandFound: {band_found}")
    print(f"  selectedHeaderBand: {band}")
    print(f"  boundaries_count: {bnd_cnt}")
    print(f"  rejectedRows_count: {len(rej)}")
    print(f"  rejection_reasons: {reason_counts}")
    print(f"  rowEndReason: {row_end}")
    print(f"  fallbackReason: {fb}")

    # Show first few rejections
    for r in rej[:5]:
        print(f"    rej: reason={r.get('reason')} y={r.get('y')} text={r.get('text','')[:50]!r}")

    rows = fields.get("tableRows") or []
    for i, row in enumerate(rows[:3]):
        name = row.get("itemName") or (row.get("_rawText") or "")[:30]
        qty = row.get("quantity")
        code = row.get("itemCode")
        print(f"  row{i+1}: itemName={name!r} qty={qty!r} itemCode={code!r}")
    print()
