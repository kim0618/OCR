---
name: invoice-3a-baseline
description: "FULL-UNSTRUCTURED-INVOICE-3A 7-sample baseline result — free parser succeeds 1/7, structure/mapping is primary bottleneck (hypothesis)"
metadata: 
  node_type: memory
  type: project
  originSessionId: f77d3bbb-cacf-4543-a448-7f5a4f8cc3b7
---

3A baseline measured all 7 tracked invoice_statement samples (1.jpg + 2-7.pdf) via no-template full-unstructured route (documentType=invoice_statement, templateMode=unstructured, isUnstructuredTemplate=Y, no template_id/regions). Measured 2026-05-29.

Key non-obvious result: the free (unstructured) parser passes its release gate on **only 1/7 samples (1.jpg)**; the other 6 fail with identical reasons (itemName/amount/unitPrice/quantity present-ratio below threshold → `table_not_detected`) and fall back to the legacy table shape. itemName grouping is good on all 7 (ratio 1.0), but quantity/unitPrice/amount column population collapses on the fallback 6. Scalars survive fallback via reference-scalar merge: biz numbers and (where present in GT) supplyAmount/taxAmount mostly match. buyerBizNumber is fine on 6/7 — only 1.jpg leaves it unmapped though the token is in OCR text.

Hypothesis (NOT final): A+B mixed, **B (structure/table-column + field-selection mapping) primary**, OCR recognition strong secondary that becomes primary on worst scans (4.pdf has heavy character-level garble, tokenInText=false). Recurring mapping error: issueDate picks 주문일자 instead of 발행일.

**Why:** reconciles with [[project_invoice_free_parser]] / 1A — 1A's "OCR small-text is the bottleneck" was measured on 1.jpg + its degraded variants, i.e. the ONE layout where the free parser works. 3A shows different supplier/layouts (2-7.pdf) never even clear the table release gate.

**How to apply:** treat the free-parser release-gate / column-population generalization as the first thing to investigate in 3B, not OCR tuning. Do NOT tune free-parser thresholds / baselines / fixtures on these 7 (buyer is fixed to 백제약품 → overfit risk). Architecture (OCR+KIE vs VLM) stays undecided until thousands of samples + supplier/site/layout holdout. Artifacts: tmp/full_unstructured_invoice_3a_baseline_7_samples_{summary.json,precheck.md}, harness/checker tmp/*_baseline_7_samples_3a.py.
