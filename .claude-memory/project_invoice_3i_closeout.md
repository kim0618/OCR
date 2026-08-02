---
name: invoice-3i-closeout
description: "FULL-UNSTRUCTURED-INVOICE-3I post-3H baseline close-out — free 2/7 stable (1.jpg + 5.pdf), regressions 0, fakeRow 0, recommended next = 4A 2.pdf balance/footer segmentation precheck"
metadata: 
  node_type: memory
  type: project
  originSessionId: f77d3bbb-cacf-4543-a448-7f5a4f8cc3b7
---

3I (close-out only, 2026-05-30) re-measured 7 samples after 3C→3E→3F→3H cumulative patch. No operational change in 3I (working tree only shows the carried-over patch).

Verified close-out state:
- **1.jpg**: used=True, rows=28, first row 헥사메던액0.12%/15m|*6포/400/1,050/420,000, candidateStrategy=strict_column (columnar gate self-skipped at parsed=28≥5), 무회귀
- **5.pdf**: used=True, rows=6, **itemName=`노루모에프내복액75ML`, spec=`NRFS75M`** (3H product-code routing intact), columnarSafeRelease.applied=True, amountSumReconciles=True (3,046,635 = supplyAmount), candidateStrategy=columnar_2d
- **2.pdf**: used=False, reject maintained (confidence 0.3), legacy fallback 2 rows, fakeRowSuspect=False — must stay rejected until balance/footer segmentation precheck (4A)
- **3.pdf / 7.pdf**: scattered single-row, no forced release
- **4.pdf**: OCR garble excluded (used=False, gate self-skip no_vertical_label_stacking)
- **6.pdf**: price absent excluded (used=False, money tokens 0, gate self-skip)
- Aggregate: HTTP200 7/7, freeUsed=2/7, regressions=[], fakeRowRiskSamples=[], closeoutFailures=[], closeoutGo=True

**Recommended next: FULL-UNSTRUCTURED-INVOICE-4A-2PDF-BALANCE-SEGMENTATION-PRECHECK** (NOT a direct patch). 2.pdf is the largest remaining undercount (GT 13 vs current fallback rows=2). 3G already flagged 2.pdf segmentation as low-medium feasibility with HIGH fake-row risk — so 4A is a dedicated precheck for (1) per-OCR-item cy/x collection, (2) balance-label spatial filter design (전일잔액/계약잔액/누계잔액/공급금액합계 separation), (3) multi-column boundary detection, (4) confidence re-evaluation. Patch only after the precheck.

**Alternative: H1 — Columnar Holdout Validation Precheck** (if multi-supplier holdout samples become available). 5.pdf safeRelease applied only on 5.pdf in 7 samples; verify generality on out-of-distribution invoices before broadening Option B (2.pdf). Architecture decision (OCR+KIE vs VLM) explicitly still forbidden on 7-sample single-buyer set.

**How to apply:** 3I = the official "post-3H" baseline. The accumulated patch state in `invoice_statement_free.py` (3C relaxed candidate + adaptive floor; 3E columnar 2D reconstruction + confidence gate + amount-equals-sum contamination guard; 3F quantity completion + safe-release hard gate + thresholdVersion 3f_columnar_quantity_optional_release; 3H product-code → spec routing via `_looks_like_product_code_token`) is stable and ready for further work. Forbidden going forward: rowText blind zip, release/precision/safeRelease threshold relaxation, 2.pdf forced release, 4.pdf forced release (OCR garble), 6.pdf forced release (no prices), 7-sample overfit tuning, 1.jpg regression, 5.pdf product-code re-merging into itemName. /ocr/extract appends to ocr-server/data/review_log.jsonl — restore after probe. Artifacts: tmp/full_unstructured_invoice_3i_post_3h_baseline_closeout_*.
