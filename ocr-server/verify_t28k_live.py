"""
T-28k live verification:
POST each test image to /ocr/extract and print field values + bbox.

Run:
  d:/Free_Vue/OCR/ocr-server/.venv/Scripts/python.exe d:/Free_Vue/OCR/ocr-server/verify_t28k_live.py
"""
import os
import sys
import json
import time

import requests


API = "http://127.0.0.1:9099/ocr/extract"
TEMPLATE_ID = "TPL-31D13CF3"

# Smoke set: the two T-28k focus images
SMOKE = [
    ("1.jpg",  r"d:\Free_Vue\OCR\mysuit-ocr\public\data\testsets\invoice_statement\1.jpg"),
    ("1-1.jpg", r"d:\Free_Vue\OCR\mysuit-ocr\public\data\testsets\invoice_statement\1\1-1.jpg"),
]

# 7 invoice_statement samples for rowCount regression
# Per spec: 1.jpg=28, 2.pdf=13, 3.pdf=1, 4.pdf=1, 5.pdf=6, 6.pdf=6, 7.pdf=1
REGRESSION = [
    ("1.jpg", r"d:\Free_Vue\OCR\mysuit-ocr\public\data\testsets\invoice_statement\1.jpg", 28),
    ("2.pdf", r"d:\Free_Vue\OCR\mysuit-ocr\public\data\testsets\invoice_statement\2.pdf", 13),
    ("3.pdf", r"d:\Free_Vue\OCR\mysuit-ocr\public\data\testsets\invoice_statement\3.pdf", 1),
    ("4.pdf", r"d:\Free_Vue\OCR\mysuit-ocr\public\data\testsets\invoice_statement\4.pdf", 1),
    ("5.pdf", r"d:\Free_Vue\OCR\mysuit-ocr\public\data\testsets\invoice_statement\5.pdf", 6),
    ("6.pdf", r"d:\Free_Vue\OCR\mysuit-ocr\public\data\testsets\invoice_statement\6.pdf", 6),
    ("7.pdf", r"d:\Free_Vue\OCR\mysuit-ocr\public\data\testsets\invoice_statement\7.pdf", 1),
]


def call_ocr(label: str, path: str, template_id: str = TEMPLATE_ID):
    if not os.path.exists(path):
        print(f"  MISSING: {path}")
        return None
    with open(path, "rb") as fh:
        files = {"file": (os.path.basename(path), fh.read())}
    data = {
        "template_id": template_id,
        "documentType": "invoice_statement",
    }
    t0 = time.time()
    r = requests.post(API, files=files, data=data, timeout=600)
    dt = time.time() - t0
    print(f"  HTTP {r.status_code}  ({dt:.1f}s)")
    if r.status_code != 200:
        print(f"  ERROR body: {r.text[:600]}")
        return None
    return r.json()


def print_fields(label, resp):
    if not resp:
        return
    fields = resp.get("fields") or []
    print(f"  fields={len(fields)}")
    for f in fields:
        nm = f.get("name", "?")
        ko = ""
        ft = f.get("field_type")
        val = f.get("value") or ""
        bbox = f.get("bbox")
        cf = f.get("confidence", 0)
        orig = f.get("original")
        src = f.get("source")
        if ft == "table":
            try:
                rows = json.loads(val) if isinstance(val, str) else val
                n_rows = len(rows) if isinstance(rows, list) else 0
                print(f"    {nm:>8} [{ft}]  rows={n_rows}  bbox={bbox}")
            except Exception:
                print(f"    {nm:>8} [{ft}]  bbox={bbox}")
        else:
            v_short = val if len(val) < 60 else val[:57] + "..."
            extra = []
            if orig and orig != val:
                extra.append(f"orig={orig!r}")
            if src:
                extra.append(f"src={src}")
            extra_s = " " + " ".join(extra) if extra else ""
            print(f"    {nm:>8} [{ft}]  {v_short!r:<60}  conf={cf:.3f}  bbox={bbox}{extra_s}")


def table_row_count(resp) -> int:
    for f in (resp.get("fields") or []):
        if f.get("field_type") == "table":
            td = f.get("table_data")
            if isinstance(td, list):
                return len(td)
            v = f.get("value")
            if isinstance(v, str):
                try:
                    rows = json.loads(v)
                    return len(rows) if isinstance(rows, list) else 0
                except Exception:
                    return 0
    return 0


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "smoke"

    if mode in ("smoke", "all"):
        print("======= SMOKE: 1.jpg / 1-1.jpg field-level checks =======")
        for lbl, path in SMOKE:
            print(f"\n--- {lbl} ---")
            resp = call_ocr(lbl, path)
            print_fields(lbl, resp)

    if mode in ("regression", "all"):
        print("\n======= REGRESSION: 7-sample rowCount =======")
        ok = True
        for lbl, path, expected in REGRESSION:
            print(f"\n--- {lbl} (expected rowCount={expected}) ---")
            resp = call_ocr(lbl, path)
            if not resp:
                ok = False
                continue
            got = table_row_count(resp)
            mark = "OK" if got == expected else "MISMATCH"
            if got != expected:
                ok = False
            print(f"  rowCount: got={got} expected={expected}  -> {mark}")
        print(f"\nRegression: {'PASS' if ok else 'FAIL'}")


if __name__ == "__main__":
    main()
