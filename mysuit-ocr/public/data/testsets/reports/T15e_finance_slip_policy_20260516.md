# T-15e finance_slip selected/suppressed 정책 분리 결과

## 1. 수정 파일
- `mysuit-ocr/public/data/testsets/receipt_generalization/manifest.json` — finance_001.jpg expectedStatus: selected → suppressed_bank_slip

## 2. 백업 파일
- `mysuit-ocr/backup/manifest_receipt_generalization_20260516_before_T15e_finance_slip_policy.json`

## 3. 핵심 요약
- finance_slip 전체 5건 모두 suppressed_bank_slip으로 정합됨 (이전: 1건 selected, 4건 suppressed)
- finance_001.jpg selectedStatus를 suppressed_bank_slip으로 변경 — 현재 finance_slip extractor 미구현으로 실제 OCR은 모두 bank_slip 억압
- 코드 변경 없음 (manifest metadata만 수정)
- T-15a~T-15d 개선 유지, invoice_statement 7/7 exact 유지

## 4. finance_slip 샘플 목록
| filename | documentType | before expectedStatus | after expectedStatus | actual doc_type | 판정 |
|---|---|---|---|---|---|
| baseline/9.jpg | finance_slip | suppressed_bank_slip | suppressed_bank_slip | bank_slip | PASS (변경 없음) |
| baseline_fast/9.jpg | finance_slip | suppressed_bank_slip | suppressed_bank_slip | bank_slip | PASS (변경 없음) |
| google/6.jpg | finance_slip | suppressed_bank_slip | suppressed_bank_slip | bank_slip | PASS (변경 없음) |
| receipt_generalization/finance_001.jpg | finance_slip | **selected** | **suppressed_bank_slip** | bank_slip | **변경됨** |
| receipt_generalization/finance_002.jpg | finance_slip | suppressed_bank_slip | suppressed_bank_slip | bank_slip | PASS (변경 없음) |

## 5. selected/suppressed 정책

### 현재 단계 정책
finance_slip extractor가 구현되기 전까지 모든 finance_slip(은행전표, ATM 영수증, 금융 전표)을 `suppressed_bank_slip`으로 처리한다.

| 분류 | 기준 | 현재 샘플 |
|---|---|---|
| suppressed_bank_slip | 은행/금융 전표 계열, finance_slip extractor 미구현 단계 | 전체 5건 |
| selected | finance_slip extractor 구현 완료 후 재전환 예정 | 0건 (미래) |

### finance_001.jpg 변경 이유
- KB 국민은행 ATM 입금 영수증 (OCR 내용: [입금], 요청금액 250,000, 입금액 249,000, 계좌번호, 거래일시)
- OCR 분류기: bank_slip → 현재 suppression 정책에 의해 실제 억압됨
- 이전 expectedStatus="selected"는 2026-04-27에 "finance parser 도입 후 selected 기대"로 예약적으로 설정된 값
- finance_slip extractor가 없는 현 단계에서 selected로 집계되면 실제 동작과 불일치 → 혼선 방지를 위해 수정
- 향후 T-16a bank_slip/finance_slip extractor 구현 후 selected로 재전환 예정

### finance_002.jpg (변경 없음)
KB 국민은행 ATM 예금출금 전표. 처리결과: 출금한도 70만원 제한으로 실패. 이미 suppressed_bank_slip ✓

## 6. 집계 변화
| 항목 | before | after | 변화 |
|---|---:|---:|---:|
| finance_slip selected | 1 | 0 | -1 |
| finance_slip suppressed_bank_slip | 4 | 5 | +1 |
| 전체 selected (baseline audit) | 49 | 48 | -1 (finance_001 제외) |

## 7. 후속 bank_slip extractor 후보
- **T-16a** bank_slip/finance_slip extractor 1차 구현
  - 대상 필드: bankName, transactionType, transactionDateTime, amount
  - 기준 샘플: finance_001.jpg (ATM 입금), finance_002.jpg (ATM 출금 실패)
  - 주의: value-before-label 역순 구조(finance_002) 처리 필요
- **T-16b** finance_slip documentType 세분화 (ATM_slip, bank_transfer_slip 등)
- **T-16c** finance_slip qualityTags 보강

### google/6.jpg 참고 사항
google/6.jpg는 manifest에서 finance_slip/suppressed_bank_slip으로 설정되어 있으나 OCR 필드에 GS25 merchantName과 2,900원 amount가 추출됨. 실제로는 편의점(GS25) 영수증이 bank_slip으로 오분류된 케이스로 추정. google testset locked이므로 변경 미수행 → 차기 google testset 재검토 시 주의 필요.

### pos_003.jpg 참고 사항
manifest에서 pos_receipt로 설정되어 있으나 OCR 내용이 약국 처방전(약제비총액/본인부담금/보험조제료/미금프라자약국). T-15b에서 medical_receipt로 올바르게 분류됨. T-15e 범위 외로 manifest 변경 미수행 → 별도 요청 시 변경.

## 8. 회귀 확인
| 영역 | 결과 |
|---|---|
| pos_receipt T-15a (businessNo/merchantName) | PASS |
| medical_receipt T-15b (4/4 correct) | PASS |
| food_cafe T-15c (merchantName) | PASS |
| card_receipt T-15d (businessNo/merchantName) | PASS |
| invoice_statement 7/7 exact | PASS |

## 9. 검증 결과
- py_compile: PASS (verify_finance_slip_policy_t15e.py)
- verify_finance_slip_policy_t15e.py: PASS (전체 PASS)
- typecheck: PASS (npm run typecheck)
- build: 미실행 (manifest JSON만 변경, JS 코드 무수정 → 이전 PASS 유지)

## 10. 다음 작업 판단
- **finance_slip 정책 정리 완료** — 전체 5건 suppressed_bank_slip으로 정합
- extractor 구현 없이 manifest metadata 정리만으로 집계 오해 해소
- T-15a~T-15e 시리즈 완료 후 **baseline receipt final audit (T-16) 권장**

### T-15 시리즈 전체 결과 요약
| 작업 | 개선 내용 |
|---|---|
| T-15a | pos_receipt businessNo 5→4, merchantName 3→2 |
| T-15b | medical_receipt 정분류 2/6→5/6 |
| T-15c | food_cafe merchantName 4→2 |
| T-15d | card_receipt businessNo 2→0, merchantName 2→1 |
| T-15e | finance_slip expectedStatus 정합 (1 selected → 0 selected, 5 suppressed) |

**모든 작업에서 invoice_statement 7/7 exact 유지, 회귀 0건.**
