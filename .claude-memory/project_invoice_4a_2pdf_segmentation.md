---
name: invoice-4a-2pdf-segmentation
description: "FULL-UNSTRUCTURED-INVOICE-4A — 2.pdf segmentation feasibility analysis; key finding = 누계진역(balance) cy 559 overlaps 공급금액(amount) cy 550, spatial filter cannot separate. Patch NOT advised; next = H1 holdout validation"
metadata: 
  node_type: memory
  type: project
  originSessionId: f77d3bbb-cacf-4543-a448-7f5a4f8cc3b7
---

4A (precheck-only, 2026-05-30) instrumented the route on 2.pdf (focused single-sample, ~80 sec) capturing 144 raw OCR items (cy/x/w/text). Working tree unchanged: only the carried-over 3C/3E/3F/3H patch in `invoice_statement_free.py`; 4A added 0 operational edits.

**Critical decisive finding**: 2.pdf's **누계진역(누계잔액) balance label sits at cy ≈ 559, almost identical to the 공급금액(amount) field label at cy ≈ 550**. The two are within OCR row-grouping tolerance, so balance tokens and line-amount tokens occupy the SAME cy band — **simple label-proximity spatial filter cannot separate them**. Combined with: (a) ~55 product/order codes (OP-NA0300 style) at cy 82-95 falsely caught by the money-regex (false-positives that saturate the amount-band classifier), (b) garbled item names (NAPROXO/LOXOL/ABLEr), (c) multi-column layout, (d) line_amount_candidates = 0 under any reasonable label-proximity scheme.

Field-label stack confirmed: 수량 cy=353 x=705 / 소비자단가 공급단가 cy=436 x=704 / 공급금액 cy=550 x=705 (vertical stack at right). Balance labels at LEFT (x≈95-187, varying cy: 82/238/398/458/493/559). Spatially: label x positions ARE distinct, but the cy of 누계진역 (559) overlaps amount band (550±band) — this is the killer.

Result classification: lineAmountCandidates=0, balance_or_footer=55, quantity_candidates=3, unitPrice_candidates=0, unknown=1. 13-row recovery decision = `too_high_risk`. Fake-row risk = HIGH. releaseAllowed = False. patchSafety = `unsafe_without_more_diagnostics_or_holdout`.

**Recommended next: H1 — Columnar Holdout Validation Precheck** (preferred — verify 5.pdf columnarSafeRelease generality on multi-supplier holdout BEFORE attempting any 2.pdf hard-case patch). Alternative (if holdout unavailable): 4B deeper diagnostics phase (per-token visual overlay export, NOT a patch). Direct 2.pdf segmentation patch (Option A) is NOT safe with current evidence.

**How to apply:** going forward, do NOT advance to 2.pdf release patch without (a) holdout-verified generality of 5.pdf's columnarSafeRelease, AND (b) a working code-vs-money disambiguator (current money-regex catches product codes like OP-NA0300 as money), AND (c) a non-spatial solution for the 누계진역/공급금액 cy overlap (maybe x-column distribution analysis + amount-sum reconciliation with totalAmount scalar). 7-sample single-buyer baseline cannot decide architecture (OCR+KIE vs VLM). Forbidden: 2.pdf release patch ahead of these prerequisites, rowText blind zip, threshold/precision/safeRelease relaxation, 1.jpg/5.pdf regression, 4/6.pdf forced release. Note `_money_parse_value` 6-digit comma date-like false-positive remains helper-bypassed. /ocr/extract appends to ocr-server/data/review_log.jsonl — restore after probe. Artifacts: tmp/full_unstructured_invoice_4a_2pdf_balance_segmentation_*.
