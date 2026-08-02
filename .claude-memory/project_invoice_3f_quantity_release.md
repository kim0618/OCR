---
name: invoice-3f-quantity-release
description: "FULL-UNSTRUCTURED-INVOICE-3F patched invoice_statement_free.py with row-local qty completion + amount-sum-reconciled safe quantity-optional release; 5.pdf RELEASED 6 rows, 1.jpg no regression, 2.pdf still rejected"
metadata: 
  node_type: memory
  type: project
  originSessionId: f77d3bbb-cacf-4543-a448-7f5a4f8cc3b7
---

3F (2026-05-30) extended `ocr-server/extractors/invoice_statement_free.py` (backup: ocr-server/backup/invoice_statement_free_20260530_3F_before_quantity_completion.py) with:

(1) `_build_columnar_rows_from_ocr_items(full_text=...)` — row-local quantity completion (cy band ±100 around qty label, x±35 around column x, strict qty-token filter excluding date/lot/money/metadata/already-used) + amount-sum reconciliation (sum of line amounts compared to full_text money tokens via `_number_value` to bypass the `_money_parse_value` date-like false-positive). Diag: `quantityCompletion{attempted/method/beforeMissing/afterMissing/candidatesFound/reasons}`, `amountSumActual/Target/Reconciles`.

(2) `_evaluate_release_threshold(columnar_context=...)` — hard-gated quantity-optional safe release. ALL of: columnar.decision=emit, confidence≥0.80, amountSumReconciles=True, itemNamePresentRatio=1.0, amountPresentRatio=1.0, unitPriceParseableRatio≥0.8, metadata=0, forbidden=0, qty_missing_ratio≤0.5, all rows columnar_2d_row source. When met, recompute relaxed-ready directly (bypass buggy `_is_release_ready_table_row` helper) and drop release_ready_ratio/release_ready_rows/quantity_parseable_ratio fail reasons. Adds `columnarSafeRelease{applied/reason/relaxedReleaseReady/droppedFailReasons}` metric; thresholdVersion `3f_columnar_quantity_optional_release`.

(3) extract dispatch threads `source_text` and `columnar_context` through.

Results: **5.pdf RELEASED** (used=True, rows=6, columnarSafeRelease.applied=True, amountSumReconciles=True matched 3,046,635 supplyAmount, relaxedReleaseReady=6/6). **1.jpg no regression** (columnar SKIPPED at parsed=28≥5 gate, strict_column path, 28 rows, first row 헥사메던액0.12%/400/1,050/420,000). **2.pdf still rejected** (confidence 0.3 < 0.80 → safe-release gate unreachable). 3/4/6/7 rejected (no vertical labels). fakeRowSuspect=[]. regressions=[]. freeUsedAfter 1→2.

**Critical helper bug noted** (NOT fixed globally — risks 1.jpg regression): `_is_date_like_number` matches plain 6-digit numbers via `(?:19|20)?\d{6}` so comma-bearing amounts like "420,000" become `_money_parse_value("420,000")=None`. Bleeds into `_is_release_ready_table_row` → `insufficient_numeric_fields` on qty-missing rows whose amount looks 6-digit. **3F mitigation**: only inside the safe-release / reconciliation paths use `_number_value` directly to bypass. Global helper untouched (1.jpg release safety intact). Future 3H+ candidate: comma-aware date-like fix with full regression sweep.

**How to apply:** 5.pdf was the win because OCR genuinely lacks 2 qty tokens (row-local search confirmed 0 found) yet amount-sum exactly matches supplyAmount — the hard gate validates alignment independently. Cosmetic: 5.pdf row 1 itemName=`"노루모에프내복액75ML NRFS75M"` (product code from nearby cy band concat — refine in 3G with tighter name cy range). Next 3G/3H: name-concat cleanup, 2.pdf hard-case (multi-column + interleaved balance), holdout multi-supplier validation. Forbidden: rowText blind zip, threshold/precision relaxation outside the safe-release gate, 4.pdf forced release, 6.pdf forced release (no prices in doc), 7-sample overfit. Keep 1.jpg 28-row no-subtotal PASS forever. /ocr/extract appends to ocr-server/data/review_log.jsonl at runtime — restore after probe. Artifacts: tmp/full_unstructured_invoice_3f_columnar_quantity_release_*.
