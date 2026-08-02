---
name: invoice-3b-bucket-priority
description: FULL-UNSTRUCTURED-INVOICE-3B — proximate cause of free-parser fallback is row-candidate detection returning 0 rows (not the release threshold); next patch = 3C Option A
metadata: 
  node_type: memory
  type: project
  originSessionId: f77d3bbb-cacf-4543-a448-7f5a4f8cc3b7
---

3B (precheck-only, 2026-05-29) decomposed the 6/7 free-parser fallbacks from [[invoice-3a-baseline]] using the free parser's internal debug (releaseDecision.metrics + tableCandidates.diagnostics), captured via in-process route re-run.

Corrected root cause: the fallback's *proximate* cause is NOT the release threshold — it's that `_find_table_row_candidates` returns **0 parsed item-rows on 5/7 samples (2,4,5,6,7.pdf)**, and on 3.pdf 2 parsed rows are both dropped by `_filter_table_row_candidates` (low_precision_score). With 0 rows, every release ratio is 0 so all 8 failReasons fire — but they are downstream symptoms. `wouldPassWithoutRowFloor` was False on all 6 (removing the floor wouldn't help). OCR→row grouping DOES work (rowTextCount 12-24 per sample); the weak link is item-row recognition/scoring.

Key cross-check: the **legacy fallback parser recovered 6/6 rows on 5.pdf and 6.pdf** where the free parser produced 0 → free candidate parser is a regression vs legacy on small-row PDF invoices. 4.pdf's "column split" seen in 3A is a *legacy single-row* artifact (free parsed 0); 4.pdf is really an OCR-garble case (tokenInText=false on company/addr/rep).

Separately real but secondary: release threshold (`thresholdVersion=3f_guarded_real_sample_release`) hard-requires minFilteredRows=20 AND minReleaseReadyRows=20 — calibrated to 1.jpg (28 rows), structurally blocks small invoices (GT rows 1-13) once parsing works.

**How to apply:** next patch = 3C "free parser table row-candidate & release generalization" (Option A). Target `invoice_statement_free.py` `_find_table_row_candidates` / `_filter_table_row_candidates` (precision score too aggressive on small-row) / `_evaluate_release_threshold` (≥20 floor). 5.pdf = first "win" target (legacy already 6/6); 2.pdf = hardest (free+legacy both undercount 13). issueDate 주문일자 mis-selection (4 samples) is the only P1 mapping item. supplyAmount/taxAmount = monitor only (match where GT exists). Validate on row-count/supplier-diverse holdout — do NOT overfit threshold/score to these 7; keep 1.jpg 28-row PASS. Architecture (OCR+KIE vs VLM) still undecided. Artifacts: tmp/full_unstructured_invoice_3b_bucket_priority_{summary.json,...precheck.md}.
