"""
Diagnostic-only: 거래_3 template + 3.pdf raw response inspection.

Reads templates.json, finds 거래_3 (TPL-E4B15A22), posts 3.pdf to
/ocr/extract with the saved regions, and dumps parser's view of the
table (header detection, column guides, extract_debug, warnings).

No code under ocr-server/ is modified. Output written to OCR/tmp_diag_3pdf_geori3_out.json.
"""

from __future__ import annotations
import json, sys, time, uuid, urllib.request, urllib.error
from pathlib import Path

BASE_URL = "http://127.0.0.1:9099"
ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "ocr-server"
FRONTEND = ROOT / "mysuit-ocr"
TEMPLATES = BACKEND / "data" / "templates.json"
PDF = FRONTEND / "public/data/testsets/invoice_statement/3.pdf"
OUT = ROOT / "tmp_diag_3pdf_geori3_out.json"
TARGET_TEMPLATE_ID = "TPL-E4B15A22"


def load_template():
    data = json.loads(TEMPLATES.read_text(encoding="utf-8"))
    for row in data:
        if str(row.get("template_id") or "") == TARGET_TEMPLATE_ID:
            return row
    raise SystemExit(f"template {TARGET_TEMPLATE_ID} not found")


def multipart(fields, file_bytes, filename, mime):
    boundary = f"----diag-{uuid.uuid4().hex}"
    parts = []
    for k, v in fields.items():
        parts.append(f"--{boundary}\r\n".encode())
        parts.append(f'Content-Disposition: form-data; name="{k}"\r\n\r\n'.encode())
        parts.append(v.encode("utf-8"))
        parts.append(b"\r\n")
    parts.append(f"--{boundary}\r\n".encode())
    parts.append(
        (f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
         f"Content-Type: {mime}\r\n\r\n").encode()
    )
    parts.append(file_bytes)
    parts.append(b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode())
    return b"".join(parts), boundary


def main():
    if not PDF.exists():
        raise SystemExit(f"PDF not found: {PDF}")
    tpl = load_template()
    tj = tpl.get("template_json") or {}
    regions = tj.get("regions") or []

    print(f"template={tpl.get('template_id')} name={tpl.get('template_name')!r}")
    print(f"regions={len(regions)} documentType={tj.get('documentType')!r}")
    table_regions = [r for r in regions if r.get("fieldType") == "table" or r.get("type") == "table"]
    print(f"table regions: {len(table_regions)}")
    for tr in table_regions:
        print("  table bounds:", {k: tr.get(k) for k in ("x", "y", "width", "height")})
        t = tr.get("table") or {}
        cg = t.get("colGuides") or t.get("colX") or tr.get("colGuides") or []
        print(f"  colGuides: {len(cg) if isinstance(cg, list) else 'n/a'} -> {cg[:10] if isinstance(cg, list) else cg}")

    fields = {
        "template_id": str(tpl.get("template_id") or ""),
        "regions": json.dumps(regions, ensure_ascii=False),
        "model_id": "",
        "documentType": "invoice_statement",
    }
    body, boundary = multipart(fields, PDF.read_bytes(), "3.pdf", "application/pdf")
    req = urllib.request.Request(
        f"{BASE_URL}/ocr/extract",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            text = resp.read().decode("utf-8", errors="replace")
            status = resp.status
    except urllib.error.HTTPError as e:
        text = e.read().decode("utf-8", errors="replace")
        status = e.code
    elapsed = round(time.time() - t0, 1)
    print(f"\nHTTP {status} elapsed={elapsed}s")

    try:
        resp_json = json.loads(text)
    except Exception:
        print("ERROR: response not JSON")
        print(text[:1000])
        return

    df = resp_json.get("document_fields") or {}
    meta = df.get("tableMeta") or {}
    rows = df.get("tableRows") or []
    debug = resp_json.get("extract_debug") or {}
    inv_dbg = debug.get("invoice_statement") or {}

    print("\n=== top-level ===")
    print("doc_type:", resp_json.get("doc_type"))
    print("template_path:", resp_json.get("template_path"))

    print("\n=== tableMeta ===")
    for k in (
        "extractionSource",
        "tableBoundsUsed",
        "tableBoundsSource",
        "columnGuidesReceived",
        "columnGuidesUsed",
        "columnGuidesCount",
        "expectedColumnKeys",
        "expectedValueFillRate",
        "expectedFilledKeys",
        "expectedMissingKeys",
        "columns",
        "columnLabels",
        "headerY",
        "headerLine",
    ):
        v = meta.get(k)
        if v is None:
            continue
        if isinstance(v, list) and len(v) > 20:
            print(f"  {k}: list[{len(v)}] head={v[:10]}")
        else:
            print(f"  {k}: {v}")
    wn = meta.get("valueMappingWarnings") or meta.get("warnings") or []
    if wn:
        print("  valueMappingWarnings:")
        for w in wn[:30]:
            print("    -", w)

    print(f"\n=== tableRows ({len(rows)}) ===")
    for i, r in enumerate(rows[:5]):
        print(f"  [{i}] keys={list(r.keys()) if isinstance(r, dict) else type(r).__name__}")
        if isinstance(r, dict):
            for k, v in r.items():
                if k.startswith("_"):
                    continue
                vs = str(v)
                if len(vs) > 120: vs = vs[:117] + "..."
                print(f"      {k}: {vs}")

    print("\n=== invoice_statement debug (extract_debug.invoice_statement) ===")
    # Print top-level keys only to avoid huge output
    if isinstance(inv_dbg, dict):
        for k, v in inv_dbg.items():
            if isinstance(v, (dict, list)):
                if isinstance(v, list) and len(v) > 10:
                    print(f"  {k}: list[{len(v)}] head={v[:5]}")
                elif isinstance(v, dict):
                    print(f"  {k}: dict keys={list(v.keys())[:20]}")
                else:
                    print(f"  {k}: {v}")
            else:
                print(f"  {k}: {v}")

    OUT.write_text(json.dumps(resp_json, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nfull response written to: {OUT}")


if __name__ == "__main__":
    main()
