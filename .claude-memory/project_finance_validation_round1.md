---
name: Finance Validation Round-1 Complete
description: GT inputs and verification results for finance final validation round 1 (3-image set)
type: project
originSessionId: 72948ff4-043b-4e32-84ea-200b40e5bcc3
---
Finance 마지막 검증 1차 라운드 완료 (2026-04-28).

**Why:** Parser 1차 구현 후 정상 케이스 vs 파서 한계 케이스 구분 검증 목적.

**3-image verification set results:**
- baseline/9.jpg → SELECTED (IBK기업은행, transfer, 2025-10-28 09:57:43, 117920)
- receipt_generalization/finance_001.jpg → SELECTED (KB국민은행, deposit, 2018-03-29 19:28, 250000)
- receipt_generalization/finance_002.jpg → REVIEW (KB국민은행, atm_cash, datetime partial, amount empty)

**GT files:**
- baseline/ground_truth.json: 9.jpg financeFields already present (bankName/transactionDateTime/amount/balanceAfter - transactionType missing but OK since TypeScript skips empty GT fields)
- receipt_generalization/ground_truth.json: CREATED NEW with finance_001 (4 fields) and finance_002 (bankName+transactionType only)

**finance_002.jpg review reasons:** DATETIME_FORMAT_UNSTABLE×2 (value-before-label layout, OCR "거래일식" ≠ "거래일시"), AMOUNT_AMBIGUOUS (anchor found but no number after it), TIER1_PARTIAL.

**How to apply:** Next round can focus on parser improvement for finance_002 (value-before-label layout). finance_001 and 9.jpg are locked as selected baselines.
