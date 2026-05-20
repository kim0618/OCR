"""Drill deeper into header detection / column guide processing."""
import json, sys
from pathlib import Path

p = Path(__file__).resolve().parent / "tmp_diag_3pdf_geori3_out.json"
data = json.loads(p.read_text(encoding="utf-8"))
sys.stdout.reconfigure(encoding="utf-8")

inv = (data.get("extract_debug") or {}).get("invoice_statement") or {}
tdbg = inv.get("table", {}).get("tableDebug") or {}

print("=== tableDebug full dump (compact) ===")
for k in tdbg.keys():
    v = tdbg[k]
    if isinstance(v, (dict, list)):
        sv = json.dumps(v, ensure_ascii=False)
        if len(sv) > 800: sv = sv[:797] + "..."
    else:
        sv = repr(v)
    print(f"\n[{k}]\n{sv}")
