# CODEX_RECEIPT_REOCR_GATING_DRY_RUN_AB

- 사용 도구: Codex
- 사용 모델: Codex
- 운영 코드 수정: 없음
- repo dirty before work: True
- API URL: `http://127.0.0.1:9099/ocr/extract`
- 스크립트: `D:\Free_Vue\OCR\tmp\codex_receipt_reocr_gating_dry_run_ab.py`
- 템플릿: 영수증 / `TPL-003`
- 제외 파일: 9.jpg

## Baseline
- avg processing/wall/fillRate: 23.954s / 24.0s / 0.9259
- upper re-OCR files: 1.jpg, 2.jpg, 3.jpg, 4.jpg, 7.jpg, 8.jpg, 10.jpg, a1.jpg, a2.jpg
- amount re-OCR files: 1.jpg, 8.jpg
- handwritten re-OCR files: a2.jpg

## re-OCR 기여도
| file | processing | upper fields | amount fields | full fields | reOCR critical | reOCR ms | can skip upper | can skip amount |
|---|---:|---|---|---|---|---:|:---:|:---:|
| 1.jpg | 25.27 | 회사명, 사업자번호, 대표자, tel, 주소 | 총합계금액 | - | tel, 대표자, 사업자번호, 주소, 총합계금액, 회사명 | 7008.8 | False | False |
| 2.jpg | 42.83 | 회사명, 사업자번호, 대표자, tel, 주소 | - | 총합계금액 | tel, 대표자, 사업자번호, 주소, 회사명 | 8948.6 | False | False |
| 3.jpg | 26.98 | 회사명, 사업자번호, tel, 주소 | - | 총합계금액 | tel, 사업자번호, 주소, 회사명 | 3936.1 | False | False |
| 4.jpg | 20.67 | 사업자번호, 대표자, tel, 주소 | - | 총합계금액 | tel, 대표자, 사업자번호, 주소 | 4252.1 | False | False |
| 7.jpg | 16.14 | 회사명, 사업자번호, tel | - | 주소, 총합계금액 | tel, 사업자번호, 회사명 | 6172.4 | False | False |
| 8.jpg | 20.41 | 회사명, 사업자번호, 대표자, tel, 주소 | 총합계금액 | - | tel, 대표자, 사업자번호, 주소, 총합계금액, 회사명 | 9485.3 | False | False |
| 10.jpg | 16.5 | 회사명, 사업자번호, 대표자, tel, 주소 | - | 총합계금액 | tel, 대표자, 사업자번호, 주소, 회사명 | 6225.1 | False | False |
| a1.jpg | 22.02 | 사업자번호 | - | 회사명, 총합계금액 | 사업자번호 | 5836.8 | False | False |
| a2.jpg | 24.77 | 회사명, 사업자번호 | - | 대표자, tel, 주소 | 사업자번호, 회사명 | 7008.0 | False | True |

## 후보 A~F Dry-run
| candidate | verdict | upper skips | amount skips | est saved s | unknown | loss files |
|---|---|---:|---:|---:|---|---|
| A_strict_all_core_present | WARN | 0 | 0 | 0.0 | 1.jpg, 2.jpg, 3.jpg, 4.jpg, 7.jpg, 8.jpg, 10.jpg, a1.jpg, a2.jpg | - |
| B_business_amount_merchant_present | WARN | 0 | 0 | 0.0 | 1.jpg, 2.jpg, 3.jpg, 4.jpg, 7.jpg, 8.jpg, 10.jpg, a1.jpg, a2.jpg | - |
| C_amount_only_gating | PASS | 0 | 1 | 0.711 | - | - |
| D_low_risk_skip_only | PASS | 0 | 1 | 0.711 | - | - |
| E_quality_guarded | WARN_NO_SAFE_SPEEDUP | 0 | 0 | 0.0 | - | - |
| F_no_skip_baseline | PASS_BASELINE_NO_SPEEDUP | 0 | 0 | 0.0 | - | - |

## Instrumentation 필요
- fullOcrOnlyFields: fields extracted before upper/amount/handwritten re-OCR
- preReOcrSemanticCompleteness: merchant/business/rep/tel/address/total booleans before re-OCR
- upperBlockRecoveredFields: exact diff between pre_fields and final fields
- amountBlockRecoveredFields: exact diff and selected total candidate before/after amount re-OCR
- reOcrDecisionTrace: wouldSkipUpperReOcr, wouldSkipAmountReOcr, skipReason, keepReason
- qualityTags: small_text/blur/shadow/handwritten-like flags used as gating guards

## 결론
- conclusion: safe_pass_candidate_exists
- operationalApplyNow: True
- safePassCandidate: C_amount_only_gating
- mostEffectiveCandidateByEstimatedTime: C_amount_only_gating (0.711s)
- reason: Current response lacks pre-reOCR fields; all upper re-OCR runs contributed to final fields, so skip cannot be proven safe from baseline response alone.
- next: 운영 반영 가능 후보가 있으면 해당 조건만 좁게 반영
