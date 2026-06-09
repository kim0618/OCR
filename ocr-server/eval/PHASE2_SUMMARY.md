# Phase 2 — RUNNER (DONE, 2026-06-09)

## Deliverables
| Artifact | Purpose |
|---|---|
| `eval/run_batch.py` | POST each active sample to live `:9099` `/ocr/extract`, capture `document_fields`, record extractionSource, resume + parallel + error isolation |
| `eval/phase2_check.py` | Gate checker (latest run by default) |
| `eval/runs/<ts>/` | Per-sample results + `run_meta.json` (gitignored) |

## Gate result — GO
```
python eval/run_batch.py --workers 3   -> ok=6 error=0 (exit 0)
python eval/phase2_check.py            -> GATE PASS - 6/6 ok, 0 errors, all classified, UTF-8 intact
```
Run dir: `eval/runs/20260609_143048/`

## Request that triggers the free path
`file` + `documentType=invoice_statement` + `templateMode=unstructured`, **no regions**
(free guard = `not region_list and _is_unstructured_template`, main.py:2952-2955).

## Per-sample outcome (data for Phase 3 — not judged here)
| sample | pages | path | rows (ext) | GT rows | client ms |
|---|---|---|---|---|---|
| 1.jpg | 1 | **free** | 28 | 28 | 68k |
| 3.pdf | 1 | fallback | 2 | 1 | 102k |
| 4.pdf | **2** | fallback | 2 | 1 | 135k |
| 5.pdf | **22** | **free** | 6 | 6 | 194k |
| 6.pdf | 1 | fallback | 6 | 6 | 77k |
| 7.pdf | 1 | fallback | 1 | 1 | 75k |

free=2, fallback=4. Row-count mismatches (3.pdf, 4.pdf) are **measurement signal** for
Phase 3/4 buckets, recorded faithfully — Phase 2 does not fix or judge.

## Corrections vs plan (verified, folded in)
1. **Plan assumption "samples are 1 page" is FALSE.** Real page counts: 4.pdf=2, 5.pdf=22.
   The plan's `assert pageCount == 1` would wrongly kill 4/5.pdf.
2. **Server is page-0 scoped** even for multi-page PDFs (5.pdf 22pp -> 6 rows == page-0 GT).
   So the runner **records `pageCount` + `multiPage` flag (non-fatal)** and proceeds with
   page-0 semantics — consistent with the product's "read page 1 only" design. Comparison
   stays page-0 extraction vs page-0 GT. multiPage samples are surfaced separately, not failed.
3. **Console mojibake was a cp949 stdout artifact, not data loss.** Saved JSON is correct
   UTF-8 (code points verified in Hangul range U+AC00-U+D7A3, no U+FFFD). Checker asserts
   no replacement chars in any saved result.
4. **`extractionSource` is a marker string, not literal "free"/"fallback"** (e.g.
   `invoice_statement_free_success_shape`, `legacy_text_items_supply_tax_reconstructed`).
   Runner records the raw value and classifies path via substring `"free"`.
5. **`rowIndex` is a string** in extractor output (`"1"`) vs **int** in GT (`1`) -> Phase 3
   row alignment/compare must normalize type. (Noted for COMPARE.)

## Governance
Writes only under `eval/runs/` (gitignored). No operational logic or `public/data` touched.

## Next — Phase 3 (COMPARE)
`compare_fields.py` (labelEn match + value normalization freeze + per-sample required set +
edited tracking) and `compare_table.py` (per-row pool, value keys only, excludedRows excluded,
rowIndex type-normalized) + 4-bucket tagging (recognition-A / structure-B / preprocessing /
layout). Gate: comparison matches human spot-check on 6 samples.
