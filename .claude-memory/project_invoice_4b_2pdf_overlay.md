---
name: invoice-4b-2pdf-overlay
description: "FULL-UNSTRUCTURED-INVOICE-4B — 2.pdf visual overlay diagnostics. PNG/HTML/token-map confirm 4A: amount label cy=550 ↔ balance 누계 cy=559 overlap, line amount candidates=0, fakeRowRisk HIGH. Patch NOT advised."
metadata: 
  node_type: memory
  type: project
  originSessionId: f77d3bbb-cacf-4543-a448-7f5a4f8cc3b7
---

4B (precheck/diagnostics-only, 2026-05-31) generated visual overlay artifacts for 2.pdf:
- `tmp/full_unstructured_invoice_4b_2pdf_overlay.png` (377 KB, 950×672, rotated 90° to match OCR coords — PyMuPDF fitz render + PIL bbox draw)
- `tmp/full_unstructured_invoice_4b_2pdf_overlay.html` (29 KB, absolute-positioned divs over PNG + token-type legend + 47-row money classification table; hover for token detail)
- `tmp/full_unstructured_invoice_4b_2pdf_token_map_compact.json` (144 tokens, id/text≤32/x/cy/w/h/type/nearestLabel/reason)
- `tmp/full_unstructured_invoice_4b_2pdf_visual_overlay_summary.json` (aggregate + decision)

Working tree unchanged: only the carried-over 3C/3E/3F/3H patch in `invoice_statement_free.py`; 4B added 0 operational edits.

**Visual confirmation of 4A's decisive finding**: 공급금액 amount label cy=550 vs 누계진역 balance label cy=559 → cy overlap visually verified (PNG has both labels highlighted: green-on-amount, red-on-balance, almost on the same horizontal line at x=705 vs x=95 respectively). Token counts: 144 positioned, 47 money-shape, 10 product_code (4B's stricter `PRODUCT_CODE_RE` correctly separated NRFS75M / OP-NA0300 / INAP250G style codes that 4A's coarse money-regex previously caught as 55 false-positives), 32 name-like, 3 field labels, 7 balance labels. Money classification: line_amount_candidates=0, balance_or_footer=43, unknown=1. fakeRowRisk=high. patchReadiness=not_ready. releaseAllowed=False.

**Recommended next: H1 — Columnar Holdout Validation Precheck** (preferred — verify 5.pdf safeRelease generality on multi-supplier holdout before any 2.pdf attempt). Alternative if holdout unavailable: **4C — OCR code-vs-money disambiguator precheck** (refine money-regex to exclude OP-NA0300 style product codes; required precondition for any 2.pdf patch). 4D (deeper segmentation, column-aware x-grouping + amount-sum vs balance cross-check) deferred until 4C + holdout both done.

**How to apply:** the PNG/HTML overlay artifacts are for human visual inspection — open `tmp/...overlay.html` in a browser (it references the PNG sibling file). Going forward, do NOT advance to 2.pdf patch without (a) holdout-verified safeRelease generality, (b) working code-vs-money disambiguator (4C), AND (c) a non-spatial solution for the 누계진역/공급금액 cy overlap (no simple y-cut works). Forbidden: 2.pdf release patch ahead of these prerequisites, rowText blind zip, threshold/precision/safeRelease relaxation, 1.jpg/5.pdf regression, 4/6.pdf forced release, 7-sample architecture decision. PyMuPDF (`fitz`) + PIL available in environment for visual diagnostics. /ocr/extract appends to ocr-server/data/review_log.jsonl — restore after probe. Artifacts: tmp/full_unstructured_invoice_4b_2pdf_*.
