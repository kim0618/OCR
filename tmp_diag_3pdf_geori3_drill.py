"""Drill into the saved raw response for 거래_3 / 3.pdf."""
import json, sys
from pathlib import Path

p = Path(__file__).resolve().parent / "tmp_diag_3pdf_geori3_out.json"
data = json.loads(p.read_text(encoding="utf-8"))

# UTF-8 stdout
sys.stdout.reconfigure(encoding="utf-8")

df = data.get("document_fields") or {}
meta = df.get("tableMeta") or {}
inv = (data.get("extract_debug") or {}).get("invoice_statement") or {}

print("== columnLabels ==")
print(meta.get("columnLabels"))
print("\n== columns ==")
print(meta.get("columns"))
print("\n== expectedColumnKeys ==")
print(meta.get("expectedColumnKeys"))
print("\n== valueMappingWarnings ==")
for w in (meta.get("valueMappingWarnings") or []):
    print(" -", w)

# Table debug
tdbg = inv.get("table", {}).get("tableDebug") or {}
print("\n== table.tableDebug keys ==", list(tdbg.keys())[:30])
for k in ("headerColumns", "columnSpec", "columnSchema", "headerLine", "header_lines",
          "headerCandidates", "columnGuides", "columnGuidesRaw", "colXFromGuides",
          "headerY", "header_y", "header"):
    v = tdbg.get(k)
    if v is not None:
        print(f"  {k} = {v!r}"[:400])

# tableRowsDebug
trd = inv.get("tableRowsDebug") or {}
print("\n== tableRowsDebug ==")
for k in ("source","rowCandidateCount","generatedRowCount","columnFillCounts",
          "expectedColumnsApplied","expectedColumnKeys","matchedColumnKeys",
          "valueColumnKeys","missingExpectedColumnKeys","displaySchemaColumnKeys",
          "columnSchemaSource","notes"):
    v = trd.get(k)
    if v is not None:
        print(f"  {k} = {v!r}"[:400])

# header line
print("\n== header_line_count / table_header_y ==", inv.get("header_line_count"), "/", inv.get("table_header_y"))

# Show first row data
rows = df.get("tableRows") or []
print(f"\n== rows ({len(rows)}) ==")
for i,r in enumerate(rows):
    print(f"row[{i}]:")
    for k,v in r.items():
        if k.startswith("_") or v in (None, "", [], {}):
            continue
        print(f"  {k!r}: {v!r}")
    rt = r.get("_rawText")
    if rt:
        print(f"  _rawText: {rt!r}")
