---
name: invoice-3c-candidate-release
description: FULL-UNSTRUCTURED-INVOICE-3C patch to invoice_statement_free.py — relaxed candidate path + generalized release floor; real wall is transposed PDF layout (→3D)
metadata: 
  node_type: memory
  type: project
  originSessionId: f77d3bbb-cacf-4543-a448-7f5a4f8cc3b7
---

3C (2026-05-29) patched `ocr-server/extractors/invoice_statement_free.py` ONLY (main.py/frontend/parsers untouched). Backup: ocr-server/backup/invoice_statement_free_20260529_3C_before_candidate_release_generalization.py.

Changes: (1) `_parse_relaxed_table_row_candidate` + `_is_acceptable_relaxed_row` — a guarded relaxed single-line candidate path (item-name signal + ≥1 money token, rejects summary/metadata) that fires ONLY when strict parsing returns 0 (so 1.jpg's strict path is untouched); (2) `_find_table_row_candidates` gained `allow_relaxed`; extract tries strict(grouped→lines) then relaxed; (3) `_filter_table_row_candidates` keeps relaxed name+amount rows even at column-score<4 (metadata still dropped), records relaxedKeptCount; (4) `_evaluate_release_threshold` floor generalized from flat ≥20 to adaptive (large table ≥20 keeps old strict-generous gate; small table 1-19 allowed but near-perfect: itemName/amount ≥0.99, releaseReadyRatio ≥0.99, + unitPrice/qty parseable + metadata=0), thresholdVersion `3c_generalized_small_row_release`, tableSizeClass metric; (5) diagnostics candidateStrategy.

Results (no-template unstructured, envless): **1.jpg NO regression** (used=True, rows=28, first row 헥사메던액0.12%/1,050/420,000, no subtotal, release pass, strict_column path). candidateImproved 4/7: 2.pdf 0→1, 5.pdf 0→2, 7.pdf 0→3, 4.pdf 0→1. freeUsed 1→1 (NO new release), regressions=0, no false release (small-table candidates correctly blocked by unitPrice/qty parseable gates).

**Further-corrected root cause (key):** the 0-candidate wall is NOT threshold strictness — it's that 2.pdf/5.pdf are **transposed/columnar PDF layouts** (item names in one cy-grouped row, quantities/unitPrices/amounts each in separate rows) and 3.pdf has a single item's fields scattered across non-adjacent grouped rows. cy-row-grouping can't reconstruct "one row = one item" there. 3B's "precision filter over-drops legitimate rows" hypothesis was **disproven**: 3.pdf's 2 strict-parsed candidates are genuine garbage fragments, correctly dropped. 6.pdf has no money tokens at all (order detail, prices absent) so no candidate is correct.

**How to apply:** next = 3D column-aware / transpose-tolerant row reconstruction (zip grouped column-rows: itemNames[i]↔qty[i]↔price[i]↔amount[i]) for 5.pdf/2.pdf, + scattered-field matching for 3.pdf. Do NOT further loosen release floor / precision score on these 7 (overfit → garbage release). Keep 1.jpg 28-row PASS + no subtotal. 4.pdf is OCR-garble (separate OCR track, not structure). Known limitation: relaxed path is gated on strict==0, so a sample with a few garbage strict candidates (3.pdf) can't reach the relaxed path. Note: the /ocr/extract route appends to ocr-server/data/review_log.jsonl at runtime — restore it after probe runs to keep the tree clean. Artifacts: tmp/full_unstructured_invoice_3c_candidate_release_generalization_{summary.json,patch.md}.
