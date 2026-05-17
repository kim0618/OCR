# T-19-final synthetic position improvement audit

## 1. 생성 파일
- `mysuit-ocr/public/data/testsets/reports/T19_final_synthetic_position_improvement_audit_20260516.md`
- `mysuit-ocr/public/data/testsets/reports/T19_final_synthetic_position_improvement_audit_20260516.json`
- `mysuit-ocr/public/data/testsets/reports/T19_final_runall_snapshot_20260516.json`
- `ocr-server/scripts/verify_t19_series_final_audit.py`

## 2. 핵심 요약
- T-18 대비 docType match rate는 77.2% -> 87.7%로 개선됐다.
- core field fill rate는 87.6% -> 94.6%로 개선됐다.
- classification_mismatch는 T-19c 기준 9건 -> 3건으로 감소했고, invoice_statement false positive는 0건으로 유지된다.
- merchantName/businessNo synthetic y_ratio 개선은 회귀 없이 누적 유지된다.
- 남은 한계는 parser보다는 OCR source missing/garbled, metadata mismatch, suppressed policy 쪽으로 이동했다.

## 3. T-18 vs T-19-final 전체 비교
| 지표 | T-18 | T-19-final | 변화 |
|---|---|---|---|
| totalSamples | 57 | 57 | 0.0 |
| executableSamples | 57 | 57 | 0.0 |
| docTypeMatchRate | 77.2 | 87.7 | 10.5 |
| coreFieldFillRate | 87.6 | 94.6 | 7.0 |
| coreFieldGtMatchRate | 99.1 | 99.1 | 0.0 |
| warningCount | 40 | 32 | -8.0 |
| sourceMissingCount | 18 | 9 | -9.0 |
| metadataIssueCount | 2 | 2 | 0.0 |

## 4. failure reason 변화
| reason | T-18 | T-19-final | 변화 |
|---|---|---|---|
| ambiguous_candidates | 1 | 1 | 0 |
| classification_mismatch | 9 | 3 | -6 |
| metadata_mismatch | 1 | 1 | 0 |
| ocr_source_garbled | 3 | 4 | 1 |
| ocr_source_missing | 2 | 4 | 2 |
| ok | 30 | 37 | 7 |
| parser_missed_source_exists | 4 | 0 | -4 |
| suppressed_policy | 7 | 7 | 0 |

## 5. documentType별 결과
| documentType | 핵심 변화 | 남은 이슈 | 판정 |
|---|---|---|---|
| card_receipt | T-15/T-19b businessNo 유지, merchantName 개선 유지 | baseline/a1 계열 classification 잔여 및 일부 OCR noise | followup |
| pos_receipt | classification 6/10 -> 9/10, pos_top_signal 및 pos_006 복구 | pos_003 metadata mismatch, businessNo OCR source missing/garbled 잔여 | improved_followup |
| food_cafe_receipt | invoice_statement false positive 제거, food_002 merchantName 복구 | food_001 OCR source 부족/unknown 잔여 | improved_followup |
| medical_receipt | medical_receipt 정분류 2/4 -> 4/4 유지, baseline/google medical도 개선 | medical_001 등 source missing/garbled businessNo는 전처리 후보 | pass_with_source_followup |
| finance_slip | selected 0 유지, suppressed policy 정합화 유지 | extractor 장기 후보이나 현재 실패로 보지 않음 | policy_pass |
| invoice_statement | rowCount 7/7 exact 유지 | 2/3 insuranceCode source missing, 5 quantity ambiguous warning 유지 | pass |

## 6. T-19 시리즈 개선 케이스
| sample | before | after | 개선 내용 |
|---|---|---|---|
| baseline/8.jpg | receipt_card | medical_receipt | classification position weighting |
| google/5.jpg | receipt_card | receipt_pos | classification position weighting |
| google/9.jpg | receipt_pos | medical_receipt | classification position weighting |
| google_fast/5.jpg | receipt_card | receipt_pos | classification position weighting |
| receipt_generalization/food_004.jpg | invoice_statement | receipt_pos | classification position weighting |
| receipt_generalization/pos_006.jpg | unknown | receipt_pos | classification position weighting |
| receipt_generalization/card_002.jpg | merchantName missing/weak | merchantName recovered | synthetic y_ratio merchantName scoring |
| receipt_generalization/food_002.jpg | merchantName missing/weak | merchantName recovered | synthetic y_ratio merchantName scoring |
| receipt_generalization/food_003.jpg | merchantName missing/weak | merchantName recovered | synthetic y_ratio merchantName scoring |
| receipt_generalization/food_005.jpg | merchantName missing/weak | merchantName recovered | synthetic y_ratio merchantName scoring |
| receipt_generalization/medical_002.jpg | merchantName missing/weak | merchantName recovered | synthetic y_ratio merchantName scoring |
| receipt_generalization/pos_006.jpg | merchantName missing/weak | merchantName recovered | synthetic y_ratio merchantName scoring |
| receipt_generalization/card_001.jpg | businessNo missing | businessNo recovered | synthetic y_ratio businessNo scoring |
| receipt_generalization/card_002.jpg | businessNo missing | businessNo recovered | synthetic y_ratio businessNo scoring |
| receipt_generalization/pos_005.jpg | businessNo missing | businessNo recovered | synthetic y_ratio businessNo scoring |
| receipt_generalization/pos_006.jpg | totalAmount false positive 22,719,138 | false positive suppressed | totalAmount bare negative scoring |

## 7. invoice_statement 회귀 확인
| sample | expected | actual | status |
|---|---|---|---|
| 1.jpg | 28 | 28 | exact |
| 2.pdf | 13 | 13 | exact |
| 3.pdf | 1 | 1 | exact |
| 4.pdf | 1 | 1 | exact |
| 5.pdf | 6 | 6 | exact |
| 6.pdf | 6 | 6 | exact |
| 7.pdf | 1 | 1 | exact |
- valueMappingWarnings 유지: 2/3 insuranceCode source missing, 5.pdf quantity ambiguous, 4.pdf doc-level pushdown 유지.
- 6.pdf header skip 및 7.pdf quantity=1,000 유지.

## 8. 남은 실패 샘플
| sample | issue | reason | 후속 |
|---|---|---|---|
| baseline/9.jpg | - | suppressed_policy | no action unless policy changes |
| baseline/a1.jpg | doc_type_mismatch:receipt_pos!=manifest:card_receipt | classification_mismatch | guarded T-19c follow-up or metadata review |
| baseline/a2.jpg | doc_type_mismatch:form_or_handwritten!=manifest:card_receipt | suppressed_policy | no action unless policy changes |
| baseline_fast/9.jpg | - | suppressed_policy | no action unless policy changes |
| baseline_fast/a2.jpg | doc_type_mismatch:form_or_handwritten!=manifest:card_receipt | suppressed_policy | no action unless policy changes |
| google/6.jpg | doc_type_mismatch:bank_slip!=manifest:finance_slip; metadata_issue:locked google manifest=finance_slip, OCR content is likely receipt-like | suppressed_policy | no action unless policy changes |
| google/8.jpg | merchantName | classification_mismatch | guarded T-19c follow-up or metadata review |
| receipt_generalization/card_001.jpg | merchantName, phone | ocr_source_garbled | T-20 preprocessing |
| receipt_generalization/card_002.jpg | address | ocr_source_garbled | T-20 preprocessing |
| receipt_generalization/finance_001.jpg | cache_based_parser:no_live_runall_export | suppressed_policy | no action unless policy changes |
| receipt_generalization/finance_002.jpg | cache_based_parser:no_live_runall_export | suppressed_policy | no action unless policy changes |
| receipt_generalization/food_001.jpg | merchantName, totalAmount | classification_mismatch | guarded T-19c follow-up or metadata review |
| receipt_generalization/medical_001.jpg | merchantName | ocr_source_missing | T-20 preprocessing/source review |
| receipt_generalization/pos_001.jpg | businessNo | ocr_source_garbled | T-20 preprocessing |
| receipt_generalization/pos_002.jpg | merchantName, businessNo | ocr_source_missing | T-20 preprocessing/source review |
| receipt_generalization/pos_003.jpg | cache_based_parser:no_live_runall_export; doc_type_mismatch:medical_receipt!=manifest:pos_receipt; metadata_issue:manifest=pos_receipt, OCR/source indicates medical receipt | metadata_mismatch | metadata cleanup |
| receipt_generalization/pos_006.jpg | businessNo, totalAmount | ocr_source_garbled | T-20 preprocessing |
| invoice_statement/2.pdf | insuranceCode, amount, totalAmount, remark | ocr_source_missing | T-20 preprocessing/source review |
| invoice_statement/3.pdf | insuranceCode, spec, quantity, unitPrice, amount, manufacturer, manufacturingExpiryComposite, lotNo, serialNo, remark | ocr_source_missing | T-20 preprocessing/source review |
| invoice_statement/5.pdf | supplyAmount, taxAmount, totalAmount, remark | ambiguous_candidates | keep warning; raw bbox only if table value accuracy becomes target |

## 9. T-20 전처리 실험 후보
| sample | reason | suggested preprocessing | 기대 효과 |
|---|---|---|---|
| receipt_generalization/card_001.jpg | ocr_source_garbled | sharpen | OCR source recovery / garbled text reduction |
| receipt_generalization/card_002.jpg | ocr_source_garbled | sharpen | OCR source recovery / garbled text reduction |
| receipt_generalization/medical_001.jpg | ocr_source_missing | denoise/illumination correction | OCR source recovery / garbled text reduction |
| receipt_generalization/pos_001.jpg | ocr_source_garbled | sharpen | OCR source recovery / garbled text reduction |
| receipt_generalization/pos_002.jpg | ocr_source_missing | sharpen | OCR source recovery / garbled text reduction |
| receipt_generalization/pos_006.jpg | ocr_source_garbled | sharpen | OCR source recovery / garbled text reduction |
| invoice_statement/2.pdf | ocr_source_missing | PDF DPI 변경 | OCR source recovery / garbled text reduction |
| invoice_statement/3.pdf | ocr_source_missing | PDF DPI 변경 | OCR source recovery / garbled text reduction |
| receipt_generalization/medical_002.jpg | OCR에 사업자번호 없음 (동물병원 영수증) | contrast/CLAHE + sharpen | businessNo/source text visibility check |
| receipt_generalization/medical_003.jpg | OCR에 사업자번호 없음 (수의원 처방영수증) | contrast/CLAHE + sharpen | businessNo/source text visibility check |

## 10. 다음 작업 판단
- 결론: T-20 전처리 실험으로 이동
- metadata mismatch와 suppressed policy는 전처리 대상에서 제외한다.
- T-20은 source missing/garbled 및 small_text/blur/low_contrast/skewed/shadow 태그가 있는 샘플만 좁혀서 진행한다.

## 11. 검증 결과
- py_compile: PASS: python -m py_compile scripts/verify_t19_series_final_audit.py
- verify script: PASS: python scripts/verify_t19_series_final_audit.py
- typecheck: PASS: npm.cmd run typecheck
- build: PASS: npm.cmd run build (Next.js reported existing ESLint nextVitals warning, exit 0)
