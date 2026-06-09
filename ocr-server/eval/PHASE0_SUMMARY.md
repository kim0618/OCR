# Phase 0 — SCHEMA-CONTRACT (DONE, 2026-06-09)

## Deliverables
| Artifact | Purpose |
|---|---|
| `eval/GT_CONTRACT.md` | The single contract the harness obeys (plan §5, refined to real fixtures) |
| `eval/.gitignore` | `runs/`, `__pycache__/` ignored — only code + contract tracked |
| `eval/phase0_contract_check.py` | Gate checker: validates 6 GT files parse 100% + conform |
| `eval/PHASE0_SUMMARY.md` | This note |

## Gate result — GO
```
python eval/phase0_contract_check.py  ->  GATE PASS - 6/6  (exit 0)
```
All of `1.jpg, 3.pdf, 4.pdf, 5.pdf, 6.pdf, 7.pdf` conform. `2.pdf` correctly absent.

## Refinements vs the plan (verified against code/fixtures, folded into the contract)
1. **Per-sample field is exactly ONE of `{totalAmount, totalQuantity}`**, never both/neither.
   Every sample = 12 common + 1 = 13 fields; union = 14. (Plan listed both as loose optional.)
   Checker enforces "exactly one".
2. **`rowType`** appears in GT rows but is in neither the §3.1 value set nor the plan's
   exclude list -> classified as **meta, excluded from value comparison** (contract §3.2).
3. **`productCode` vs `itemCode`**: extractor `TABLE_ROW_KEYS` tuple lists `itemCode`, but the
   emitted+normalized row carries `productCode` (extractor L2228 + main.py:3069-3081), which is
   what GT uses. Comparison aligns on `productCode`. (Plan §3 mis-cited the tuple line.)
4. All 6 fixtures are **rich** (bboxRefs present); `excludedRows` all `[]`. Thin-GT and
   excludedRows code paths are specified but **unexercised** until Phase 6/7.

## Governance check (CLAUDE.md)
- New subsystem under `ocr-server/eval/`; **no** operational OCR logic touched.
- `public/data` read **only**. `runs/` (future outputs) gitignored.
- One pre-existing edit this session: corrected a **stale docstring** in
  `extractors/invoice_statement_free.py` (comment only, logic unchanged, backed up to
  `backup/invoice_statement_free_20260609_before_docstring_fix.py`).

## Next — Phase 1 (INGEST)
`build_manifest.py` (auto-pair image<->GT by sourceFile, status incl. 2.pdf=excluded) +
`gt_loader.py` (flatten `fields[]`->{labelEn:value}, graceful thin, split `excludedRows`).
Gate: 6-image manifest + loader 6/6 via checker. Reuses the constants frozen here.
