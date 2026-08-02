---
name: invoice-3d-transposed-columnar
description: FULL-UNSTRUCTURED-INVOICE-3D precheck — transposed layout confirmed but per-column counts mismatch; 3E = 2D coordinate reconstruction with confidence gate (no fake rows)
metadata: 
  node_type: memory
  type: project
  originSessionId: f77d3bbb-cacf-4543-a448-7f5a4f8cc3b7
---

3D (precheck-only, 2026-05-29) analyzed the transposed/columnar wall from [[invoice-3c-candidate-release]] by instrumenting the free parser's row-grouping during route calls (captured grouped rowText token-types + raw OCR item x-clustering). No operational code changed (the `invoice_statement_free.py` ' M' in the tree is the carried-over 3C patch).

Confirmed: 2.pdf/5.pdf are genuinely transposed — item names, quantities, unit prices, amounts each land in SEPARATE cy-grouped rows (5.pdf: a concatenated item-name row, a "수량" row, a "단가" row of 6 values, a "금액" row of 5 values). But **per-column element counts mismatch** (5.pdf names concatenated into 1-2 rows, qty≈4, unitPrice≈6, amount≈5 vs GT 6), so blind rowText index-zip would pair an item name from one row with an amount from another = fake rows. 2.pdf is worse (multi-column + interleaved footer balances 전일잔액/계약잔액/누계, garbled names, 9/15 metadata rows). 3.pdf single-row: its money tokens are document totals (supply 273,927 / tax 27,393 / total 301,320), not a line amount.

Caveat learned: the harness's `columnarLikely` flag and `xColumnEstimate` (x-gap clustering) are COARSE and over-fire — 1.jpg (clean 7-col row-per-line, already released) also reads columnarLikely=true / xCols=3. Don't trust those absolute numbers; the real transposition test is "are a single item's name+qty+price+amount in the same row (1.jpg) or scattered across rows (5.pdf)".

**Recommended 3E (how to apply):** Option A — 2D spatial reconstruction on RAW OCR item coordinates (cluster by x into columns, by cy into rows within the table region), NOT rowText index-zip. Hard alignment-confidence gate: emit rows only when per-column counts are consistent + coordinates align; otherwise DEFER (prefer no row over fake row). Success metric = "correct rows when confident OR zero fake rows", not "more releases". 5.pdf = primary validation target (may still not fully release because OCR concatenates its item names). 2.pdf → defer to 3F hard-case. 3.pdf/7.pdf → Option C scattered single-row matcher with supply+tax=total reconciliation guard. 4.pdf excluded (OCR garble, xCols=1). 6.pdf excluded (no prices in document). Forbidden: rowText blind zip, threshold/precision loosening, 4.pdf forced release, 7-sample overfit; keep 1.jpg 28-row no-subtotal PASS. Artifacts: tmp/full_unstructured_invoice_3d_transposed_columnar_*.
