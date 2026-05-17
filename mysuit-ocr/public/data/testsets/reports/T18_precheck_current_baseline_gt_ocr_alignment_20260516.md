# T-18-precheck 현재 baseline + 거래명세서 GT/OCR 정합성 리포트

## 1. 생성 파일
- `mysuit-ocr\public\data\testsets\reports\T18_precheck_current_baseline_gt_ocr_alignment_20260516.md`
- `mysuit-ocr\public\data\testsets\reports\T18_precheck_current_baseline_gt_ocr_alignment_20260516.json`
- `mysuit-ocr\public\data\testsets\reports\T18_precheck_current_baseline_runall_snapshot_20260516.json`
- `ocr-server/scripts/verify_current_baseline_runall_gt_alignment_t18_precheck.py`

## 2. 실행 대상
| testsetId | images | executed | skipped | 비고 |
|---|---:|---:|---:|---|
| baseline | 10 | 10 | 0 | target=runall_target; docs={'card_receipt': 7, 'food_cafe_receipt': 1, 'medical_receipt': 1, 'finance_slip': 1} |
| baseline_fast | 5 | 5 | 0 | target=runall_target; docs={'card_receipt': 4, 'finance_slip': 1} |
| google | 11 | 11 | 0 | target=runall_target; docs={'food_cafe_receipt': 5, 'pos_receipt': 3, 'finance_slip': 1, 'unknown': 1, 'medical_receipt': 1} |
| google_fast | 5 | 5 | 0 | target=runall_target; docs={'food_cafe_receipt': 4, 'pos_receipt': 1} |
| invoice_statement | 7 | 7 | 0 | target=runall_target; docs={'invoice_statement': 7} |
| new_samples | 9 | 0 | 9 | target=reference_only; docs={'pos_receipt': 8, 'unknown': 1} |
| receipt_generalization | 19 | 19 | 0 | target=runall_target; docs={'pos_receipt': 6, 'food_cafe_receipt': 5, 'medical_receipt': 4, 'card_receipt': 2, 'finance_slip': 2} |
| tax_invoice | 0 | 0 | 0 | target=no_samples; docs={'tax_invoice': 1}; placeholder/missing |
| transaction_statement | 0 | 0 | 0 | 예비 타입, 실제 샘플 없음 |

## 3. 전체 인식률 요약
| 지표 | 값 |
|---|---:|
| totalSamples | 57 |
| executableSamples | 57 |
| docTypeMatchRate | 77.2% |
| coreFieldFillRate | 87.6% |
| coreFieldGtMatchRate | 99.1% |
| rowCountExactRate | 100.0% |
| warningCount | 40 |
| sourceMissingCount | 18 |
| metadataIssueCount | 2 |

## 4. documentType별 결과
| documentType | samples | docType match | core fill | 주요 missing | 주요 warning | 판정 |
|---|---:|---:|---:|---|---|---|
| card_receipt | 13 | 10/13 (76.9%) | 94.5% | {"merchantName": 1, "phone": 1, "address": 1} | {"doc_type_mismatch": 3, "cache_based_parser": 2} | followup |
| finance_slip | 5 | 4/5 (80.0%) | 0.0% | {} | {"cache_based_parser": 2, "doc_type_mismatch": 1, "metadata_issue": 1} | followup |
| food_cafe_receipt | 15 | 13/15 (86.7%) | 90.0% | {"merchantName": 2, "totalAmount": 1} | {"cache_based_parser": 5, "doc_type_mismatch": 2} | followup |
| invoice_statement | 7 | 7/7 (100.0%) | 0.0% | {"remark": 7, "totalAmount": 3, "amount": 3, "unit": 2, "supplyAmount": 2, "taxAmount": 2, "insuranceCode": 2, "serialNo": 2} | {"insuranceCode": 2, "taxAmount=doc_level_pushdown": 1, "totalAmount=doc_level_pushdown": 1, "multiline_layout_mapping_applied": 1, "quantity": 1} | followup |
| medical_receipt | 6 | 4/6 (66.7%) | 83.3% | {"merchantName": 2} | {"cache_based_parser": 4, "doc_type_mismatch": 2} | followup |
| pos_receipt | 10 | 6/10 (60.0%) | 76.7% | {"businessNo": 4, "merchantName": 2, "totalAmount": 1} | {"cache_based_parser": 6, "doc_type_mismatch": 4, "metadata_issue": 1} | followup |
| unknown | 1 | 0/1 (0.0%) | 50.0% | {"merchantName": 1} | {"doc_type_mismatch": 1} | followup |

## 5. baseline 영수증 GT/OCR 정합성
| sample | documentType | docType result | core fields | issue | reason |
|---|---|---|---|---|---|
| baseline/1.jpg | card_receipt | match | merchantName:exact, businessNo:exact, totalAmount:exact, phone:normalized_match, address:exact | - | ok |
| baseline/2.jpg | card_receipt | match | merchantName:exact, businessNo:exact, totalAmount:exact, phone:wrong_value, address:exact | - | ok |
| baseline/3.jpg | card_receipt | match | merchantName:exact, businessNo:exact, totalAmount:exact, phone:exact, address:partial_match | - | ok |
| baseline/4.jpg | card_receipt | match | merchantName:exact, businessNo:exact, totalAmount:exact, phone:exact, address:exact | - | ok |
| baseline/7.jpg | food_cafe_receipt | match | merchantName:exact, totalAmount:exact | - | ok |
| baseline/8.jpg | medical_receipt | mismatch(receipt_card) | merchantName:exact, totalAmount:exact | - | classification_mismatch |
| baseline/9.jpg | finance_slip | match | - | - | suppressed_policy |
| baseline/10.jpg | card_receipt | match | merchantName:exact, businessNo:exact, totalAmount:exact, phone:exact, address:exact | - | ok |
| baseline/a1.jpg | card_receipt | mismatch(receipt_pos) | merchantName:exact, businessNo:exact, totalAmount:exact, phone:exact, address:exact | - | classification_mismatch |
| baseline/a2.jpg | card_receipt | mismatch(form_or_handwritten) | - | - | suppressed_policy |
| baseline_fast/1.jpg | card_receipt | match | merchantName:exact, businessNo:exact, totalAmount:exact, phone:normalized_match, address:exact | - | ok |
| baseline_fast/4.jpg | card_receipt | match | merchantName:exact, businessNo:exact, totalAmount:exact, phone:exact, address:exact | - | ok |
| baseline_fast/9.jpg | finance_slip | match | - | - | suppressed_policy |
| baseline_fast/10.jpg | card_receipt | match | merchantName:exact, businessNo:exact, totalAmount:exact, phone:exact, address:exact | - | ok |
| baseline_fast/a2.jpg | card_receipt | mismatch(form_or_handwritten) | - | - | suppressed_policy |
| google/1.jpg | food_cafe_receipt | match | merchantName:exact, totalAmount:exact | - | ok |
| google/2.jpg | food_cafe_receipt | match | merchantName:exact, totalAmount:exact | - | ok |
| google/3.jpg | food_cafe_receipt | match | merchantName:exact, totalAmount:exact | - | ok |
| google/4.jpeg | pos_receipt | match | merchantName:exact, businessNo:exact, totalAmount:exact | - | ok |
| google/5.jpg | pos_receipt | mismatch(receipt_card) | merchantName:exact, businessNo:exact, totalAmount:exact | - | classification_mismatch |
| google/6.jpg | finance_slip | mismatch(bank_slip) | - | - | suppressed_policy |
| google/7.jpg | pos_receipt | match | merchantName:exact, businessNo:exact, totalAmount:exact | - | ok |
| google/8.jpg | unknown | mismatch(receipt_pos) | merchantName:source_missing, totalAmount:exact | merchantName | classification_mismatch |
| google/9.jpg | medical_receipt | mismatch(receipt_pos) | merchantName:exact, totalAmount:exact | - | classification_mismatch |
| google/10.jpg | food_cafe_receipt | match | merchantName:exact, totalAmount:exact | - | ok |
| google/11.jpg | food_cafe_receipt | match | merchantName:exact, totalAmount:exact | - | ok |
| google_fast/1.jpg | food_cafe_receipt | match | merchantName:exact, totalAmount:exact | - | ok |
| google_fast/10.jpg | food_cafe_receipt | match | merchantName:exact, totalAmount:exact | - | ok |
| google_fast/11.jpg | food_cafe_receipt | match | merchantName:exact, totalAmount:exact | - | ok |
| google_fast/3.jpg | food_cafe_receipt | match | merchantName:exact, totalAmount:exact | - | ok |
| google_fast/5.jpg | pos_receipt | mismatch(receipt_card) | merchantName:source_missing, businessNo:source_missing, totalAmount:exact | merchantName, businessNo | classification_mismatch |
| receipt_generalization/card_001.jpg | card_receipt | match | merchantName:source_missing, businessNo:exact, totalAmount:exact, phone:source_missing, address:exact | merchantName, phone | ocr_source_garbled |
| receipt_generalization/card_002.jpg | card_receipt | match | merchantName:exact, businessNo:exact, totalAmount:exact, phone:exact, address:source_missing | address | ocr_source_garbled |
| receipt_generalization/finance_001.jpg | finance_slip | match | - | - | suppressed_policy |
| receipt_generalization/finance_002.jpg | finance_slip | match | - | - | suppressed_policy |
| receipt_generalization/food_001.jpg | food_cafe_receipt | mismatch(unknown) | merchantName:source_missing, totalAmount:source_missing | merchantName, totalAmount | classification_mismatch |
| receipt_generalization/food_002.jpg | food_cafe_receipt | match | merchantName:source_missing, totalAmount:exact | merchantName | parser_missed_source_exists |
| receipt_generalization/food_003.jpg | food_cafe_receipt | match | merchantName:exact, totalAmount:exact | - | ok |
| receipt_generalization/food_004.jpg | food_cafe_receipt | mismatch(invoice_statement) | merchantName:exact, totalAmount:exact | - | classification_mismatch |
| receipt_generalization/food_005.jpg | food_cafe_receipt | match | merchantName:exact, totalAmount:exact | - | ok |
| receipt_generalization/medical_001.jpg | medical_receipt | match | merchantName:source_missing, totalAmount:exact | merchantName | parser_missed_source_exists |
| receipt_generalization/medical_002.jpg | medical_receipt | match | merchantName:source_missing, totalAmount:exact | merchantName | parser_missed_source_exists |
| receipt_generalization/medical_003.jpg | medical_receipt | match | merchantName:exact, totalAmount:exact | - | ok |
| receipt_generalization/medical_004.jpg | medical_receipt | match | merchantName:exact, totalAmount:exact | - | ok |
| receipt_generalization/pos_001.jpg | pos_receipt | match | merchantName:exact, businessNo:source_missing, totalAmount:exact | businessNo | ocr_source_garbled |
| receipt_generalization/pos_002.jpg | pos_receipt | match | merchantName:source_missing, businessNo:source_missing, totalAmount:exact | merchantName, businessNo | parser_missed_source_exists |
| receipt_generalization/pos_003.jpg | pos_receipt | mismatch(medical_receipt) | merchantName:exact, businessNo:exact, totalAmount:exact | - | metadata_mismatch |
| receipt_generalization/pos_004.jpg | pos_receipt | match | merchantName:exact, businessNo:exact, totalAmount:exact | - | ok |
| receipt_generalization/pos_005.jpg | pos_receipt | match | merchantName:exact, businessNo:exact, totalAmount:exact | - | ok |
| receipt_generalization/pos_006.jpg | pos_receipt | mismatch(unknown) | merchantName:exact, businessNo:source_missing, totalAmount:source_missing | businessNo, totalAmount | classification_mismatch |

## 6. invoice_statement GT/OCR 정합성
| sample | expected rows | actual rows | row status | fill rate | warnings | 판정 |
|---|---:|---:|---|---:|---|---|
| 1.jpg | 28 | 28 | exact | 60.4 | [] | pass |
| 2.pdf | 13 | 13 | exact | 44.8 | ["insuranceCode:ocr_source_missing:보험No OCR 원문에서 보험코드 후보를 찾지 못함 - 빈 값 유지"] | pass |
| 3.pdf | 1 | 1 | exact | 16.7 | ["insuranceCode:ocr_source_missing:보험No OCR 원문에서 보험코드 후보를 찾지 못함 - 빈 값 유지"] | pass |
| 4.pdf | 1 | 1 | exact | 80.0 | ["taxAmount=doc_level_pushdown", "totalAmount=doc_level_pushdown"] | pass |
| 5.pdf | 6 | 6 | exact | 48.1 | ["multiline_layout_mapping_applied", "quantity:ambiguous_numeric_candidates:quantity candidates 3/6; kept existing empty values"] | pass |
| 6.pdf | 6 | 6 | exact | 50.0 | [] | pass |
| 7.pdf | 1 | 1 | exact | 66.7 | [] | pass |

## 7. 실패 원인 분류
| reason | count | 대표 샘플 | 설명 |
|---|---:|---|---|
| classification_mismatch | 9 | ["baseline/8.jpg", "baseline/a1.jpg", "google/5.jpg", "google/8.jpg", "google/9.jpg"] | 분류 결과와 manifest documentType 불일치 |
| suppressed_policy | 7 | ["baseline/9.jpg", "baseline/a2.jpg", "baseline_fast/9.jpg", "baseline_fast/a2.jpg", "google/6.jpg"] | suppression 정책상 정상 처리 |
| parser_missed_source_exists | 4 | ["receipt_generalization/food_002.jpg", "receipt_generalization/medical_001.jpg", "receipt_generalization/medical_002.jpg", "receipt_generalization/pos_002.jpg"] | OCR source는 일부 있으나 parser/선택 규칙이 놓친 후보 |
| ocr_source_garbled | 3 | ["receipt_generalization/card_001.jpg", "receipt_generalization/card_002.jpg", "receipt_generalization/pos_001.jpg"] | OCR 원문이 깨져 필드 복구가 어려움 |
| ocr_source_missing | 2 | ["invoice_statement/2.pdf", "invoice_statement/3.pdf"] | OCR 원문 자체가 없거나 GT 근거를 찾기 어려움 |
| metadata_mismatch | 1 | ["receipt_generalization/pos_003.jpg"] | manifest/GT의 문서유형 또는 기대값이 실제 샘플과 불일치 |
| ambiguous_candidates | 1 | ["invoice_statement/5.pdf"] | 여러 후보가 있어 보수적으로 비움 |

## 8. 다음 작업 우선순위 판단
| 후보 | 필요성 | 근거 | 추천 순위 |
|---|---|---|---:|
| OCR raw confidence/bbox 활용 | high | parser/ambiguous/classification reasons=14 | 1 |
| qualityTags 기반 실패 유형 분석 | high | ocr/layout/false-positive reasons=5, __none__ tags=32 | 2 |
| OCR 전처리 실험 | high | source missing/garbled reasons=5 | 3 |

## 9. 결론
- 현재 인식률 수준: docType match 77.2%, core field fill 87.6%, invoice rowCount exact 100.0%.
- GT와 OCR 정합성: GT가 있는 핵심 필드 기준 match 99.1%, GT가 부족한 receipt_generalization은 fill/원인 분류 중심 평가.
- 지금 바로 개선 가능한 영역: metadata mismatch 정리와 OCR source missing/garbled 샘플 분리.
- 전처리/Raw bbox/qualityTags 중 우선순위: OCR raw confidence/bbox 활용.

## 10. 검증 결과
- py_compile: PASS: python -m py_compile scripts/verify_current_baseline_runall_gt_alignment_t18_precheck.py
- verify script: PASS: python scripts/verify_current_baseline_runall_gt_alignment_t18_precheck.py
- typecheck: PASS: npm.cmd run typecheck
- build: PASS: npm.cmd run build (Next.js reported existing ESLint nextVitals warning, exit 0)
