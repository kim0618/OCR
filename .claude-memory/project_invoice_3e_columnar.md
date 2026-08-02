---
name: invoice-3e-columnar
description: "FULL-UNSTRUCTURED-INVOICE-3E patched invoice_statement_free.py with 2D coordinate columnar reconstruction; 5.pdf emit 6/6 rows confidence 0.8, 2.pdf correctly rejected, 1.jpg untouched"
metadata: 
  node_type: memory
  type: project
  originSessionId: f77d3bbb-cacf-4543-a448-7f5a4f8cc3b7
---

3E (2026-05-30) patched `ocr-server/extractors/invoice_statement_free.py` ONLY (backup: ocr-server/backup/invoice_statement_free_20260530_3E_before_columnar_reconstruction.py). Adds raw-OCR-item-coordinate 2D column-row reconstruction for rotated/transposed invoice tables (signature: 수량/단가/금액 labels vertically stacked at similar x, distinct cy).

Helpers: `_detect_vertical_field_labels` (gate via vertical-label-stacking signature; if labels are at SAME cy = normal row-per-line layout like 1.jpg, gate self-skips), `_build_columnar_rows_from_ocr_items` (per-label cy±50 band collects field tokens LEFT of label x with metadata filter; item-name tokens above topmost label cy within field x-range; cluster name tokens by x ±35 to recover columns; best-match each field within ±35 tol; confidence = 0.5·count-consistency + 0.3·field-density + 0.2·emit-coverage; **amount==sum-of-others contamination guard** rejects document-total leakage; emit ≥0.65, diagnostics_only 0.5–0.65, reject <0.5). Extract dispatch tries columnar only when strict+relaxed produced <5 rows. Precision filter keeps `columnar_2d_row` source via the relaxed-keep predicate. New `tableCandidates.columnar` diagnostics block + `candidateStrategy=columnar_2d` label.

Results: **1.jpg NO regression** (parsed=28≥5 → columnar SKIPPED; rows=28, first row 헥사메던액0.12%/1,050/420,000, no subtotal, release pass). **5.pdf primary target SUCCESS** (parsed 2→6, columnar.attempted=true, decision=emit, confidence=0.80, emittedRows=6, columnGroups itemName=6/qty=4/unitPrice=6/amount=6; arithmetic checks pass — 1,650,000+...+273,000=3,046,635=supplyAmount; release still blocked by release_ready_ratio because 2 rows lack qty — honest data limitation, NOT relaxed). **2.pdf correctly REJECTED** (confidence 0.3 < 0.5 because name=2 vs amount=12 mismatch caught the multi-balance contamination — no fake rows emitted). 3/4/6/7 columnar skipped (no_vertical_label_stacking). fakeRowSuspect=[], regressions=[], freeUsed unchanged 1→1.

**How to apply:** columnar runs ONLY on rotated transposed layouts; dense row-per-line tables are untouched (gate). Next 3F: (a) 5.pdf qty band expansion or coordinate re-OCR to fill missing qty (enables release); (b) 2.pdf hard-case multi-column+balance segmentation; (c) holdout multi-supplier validation. Forbidden going forward: rowText blind index-zip (=fake rows), release_ready/precision threshold further relaxation, 4.pdf forced release, 6.pdf forced release (no prices), 7-sample overfit. Keep 1.jpg 28-row no-subtotal PASS forever. Note: /ocr/extract appends to ocr-server/data/review_log.jsonl at runtime — restore after probe runs. Artifacts: tmp/full_unstructured_invoice_3e_column_row_reconstruction_*.
