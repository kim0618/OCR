"""Quick check: does /ocr/extract return original_image + processed_image for 1.jpg receipt run?"""
import requests, os, sys

API = "http://127.0.0.1:9099/ocr/extract"
path = r"d:\Free_Vue\OCR\mysuit-ocr\public\images\1.jpg"

with open(path, "rb") as fh:
    files = {"file": (os.path.basename(path), fh.read())}
r = requests.post(API, files=files, data={}, timeout=600)
print(f"HTTP {r.status_code}")
j = r.json()
print(f"keys: {list(j.keys())}")
oi = j.get("original_image")
pi = j.get("processed_image")
print(f"original_image: {'present' if oi else 'MISSING'} (len={len(oi) if oi else 0})")
print(f"processed_image: {'present' if pi else 'MISSING'} (len={len(pi) if pi else 0})")
print(f"fields count: {len(j.get('fields') or [])}")
print(f"receipt_fields: {j.get('receipt_fields')}")
