---
name: invoice-3g-quality-hardcase
description: "FULL-UNSTRUCTURED-INVOICE-3G precheck — recommended 3H = Option A (5.pdf product-code → spec, low risk). 2.pdf hard-case deferred (HIGH fake-row risk). Holdout validation (Option D) required before broader work."
metadata: 
  node_type: memory
  type: project
  originSessionId: f77d3bbb-cacf-4543-a448-7f5a4f8cc3b7
---

3G (precheck-only, 2026-05-30) analyzed 3F outcomes without re-running OCR (probe is a pure analyzer of 3F summary + 3D/3E spatial dump knowledge). Working tree unchanged: only the carried-over 3C/3E/3F patch in `invoice_statement_free.py`; 3G adds 0 operational edits.

Findings:
- **5.pdf name concat root cause**: `_build_columnar_rows_from_ocr_items` collects name tokens with `cy < min_label_cy - 100` (cy<720 on 5.pdf). Item names sit at cy 138-216, **product codes** (NRFS75M, NRDA4P, NPRT1OT, NASP15P, INAP250G, DPNL30M) at **cy 673-683** — both within the name band AND at matching x columns (294-559 = item-name x columns), so the helper's x-cluster (±35) merges them. Resulting itemName="노루모에프내복액75ML NRFS75M". Cosmetic only — amount/qty/unit correct.
- **5.pdf safeRelease generality**: gates applied ONLY on 5.pdf in the 7-sample set. 2.pdf was attempted but rejected at confidence 0.3 before reaching the gate; 1.jpg's columnar self-skipped; others lack vertical labels. No false applications. Verdict: `sample_specific_but_guarded` — needs holdout (Option D) before broadening.
- **2.pdf segmentation feasibility = LOW-MEDIUM**: amount band has 12 money tokens (line + 전일잔액/계약잔액/누계잔액/공급금액합계), garbled item names (NAPROXO/LOXOL/ABLEr), multi-column layout, qty band also contaminated (11 tokens). Fake-row risk HIGH even with balance exclusion. Deferred to a dedicated phase (3I) with its own pre-precheck.
- 3.pdf/7.pdf scattered single-row: defer (Option C); requires supply+tax=total reconciliation guard.
- 4.pdf (OCR garble) / 6.pdf (no prices): maintain excluded.

**Recommended 3H: Option A — `_build_columnar_rows_from_ocr_items` per-column cy clustering + product-code regex (`^[A-Z]{2,}[\dA-Z]+$`) → route to spec (NEVER itemName).** Single target file `invoice_statement_free.py`. Low risk: 1.jpg gate self-skipped, 2.pdf reject at emit, others gated out. Success metric: 5.pdf first row itemName loses the product code; release stays (used=True, rows=6, safeRelease.applied=True); 1.jpg 28-row unchanged; 2.pdf reject + fake-row 0 unchanged. Parallel: **Option D holdout validation** (multi-supplier, non-7-sample) before Option B (2.pdf hard-case).

**How to apply:** Future 3H patch must (1) NOT widen name cy band — only narrow per-column, (2) treat product-code-pattern tokens conservatively (assign to spec; never lose hangul name tokens), (3) keep all 3F safe-release hard gates intact, (4) preserve 1.jpg 28-row no-subtotal PASS. Forbidden: rowText blind zip, threshold/precision/safeRelease relaxation, 2.pdf forced release, 4/6.pdf forced release, 7-sample overfit tuning, advancing Option B without holdout. Note: `_money_parse_value`/`_is_date_like_number` 6-digit comma false-positive still helper-bypassed (NOT fixed globally). /ocr/extract appends to ocr-server/data/review_log.jsonl at runtime — restore after probe. Artifacts: tmp/full_unstructured_invoice_3g_columnar_quality_hardcase_{summary.json,…precheck.md}.
