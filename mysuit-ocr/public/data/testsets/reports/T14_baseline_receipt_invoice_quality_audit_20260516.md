# T-14 baseline 영수증 + invoice_statement 기존 샘플 전체 품질 audit

## 1. 생성 파일
- `mysuit-ocr\public\data\testsets\reports\T14_baseline_receipt_invoice_quality_audit_20260516.json`
- `mysuit-ocr\public\data\testsets\reports\T14_baseline_receipt_invoice_quality_audit_20260516.md`
- `ocr-server/scripts/verify_baseline_receipt_invoice_quality_t14.py`

## 2. 검증 대상 testset
| testsetId | sample count | documentTypes | 비고 |
|---|---:|---|---|
| baseline | 10 | {"card_receipt": 7, "food_cafe_receipt": 1, "medical_receipt": 1, "finance_slip": 1} | auditSource=validation_results_baseline_after_final_selection_edge_cases.json |
| baseline_fast | 5 | {"card_receipt": 4, "finance_slip": 1} | auditSource=validation_results_baseline_fast_after_final_selection_edge_cases.json |
| google | 11 | {"food_cafe_receipt": 5, "pos_receipt": 3, "finance_slip": 1, "unknown": 1, "medical_receipt": 1} | auditSource=validation_results_google_final_before_lock_fields.json |
| google_fast | 5 | {"food_cafe_receipt": 4, "pos_receipt": 1} | auditSource=validation_results_top_fields_generalization.json |
| invoice_statement | 7 | {"invoice_statement": 7} | auditSource=T8_final_precheck_invoice_statement_full_quality_20260514.json |
| new_samples | 9 | {"pos_receipt": 8, "unknown": 1} | 이미지 존재 확인만 |
| receipt_generalization | 19 | {"pos_receipt": 6, "food_cafe_receipt": 5, "medical_receipt": 4, "card_receipt": 2, "finance_slip": 2} | auditSource=ocr_cache.json |
| tax_invoice | 0 | {"tax_invoice": 1} | placeholder/missing file 있음; audit 제외(no_samples/placeholder) |

## 3. 전체 요약
| 항목 | 결과 |
|---|---|
| total samples | 57 |
| selected | 49 |
| suppressed | 6 |
| unknown | 2 |
| error | 0 |
| documentType count | {"card_receipt": 13, "food_cafe_receipt": 15, "medical_receipt": 6, "finance_slip": 5, "pos_receipt": 10, "unknown": 1, "invoice_statement": 7} |
| warning count | 36 |

## 4. documentType별 품질
| documentType | total | selected | suppressed | unknown | error | 주요 missing | 주요 warning | 판정 |
|---|---:|---:|---:|---:|---:|---|---|---|
| card_receipt | 13 | 11 | 2 | 0 | 0 | {"merchantName": 2, "businessNo": 2, "phone": 1, "address": 1} | {"doc_type_mismatch": 3, "cache_based_parser": 2} | needs_followup |
| finance_slip | 5 | 1 | 4 | 0 | 0 | {} | {"cache_based_parser": 2, "finance_slip_policy_review": 2} | pass_with_warning |
| food_cafe_receipt | 15 | 14 | 0 | 1 | 0 | {"merchantName": 4, "totalAmount": 1} | {"cache_based_parser": 5} | needs_followup |
| invoice_statement | 7 | 7 | 0 | 0 | 0 | {"remark": 7, "totalAmount": 3, "amount": 3, "unit": 2, "supplyAmount": 2, "taxAmount": 2, "insuranceCode": 2, "serialNo": 2} | {"insuranceCode": 2, "taxAmount=doc_level_pushdown": 1, "totalAmount=doc_level_pushdown": 1, "multiline_layout_mapping_applied": 1, "quantity": 1} | pass_with_warning |
| medical_receipt | 6 | 6 | 0 | 0 | 0 | {"merchantName": 2} | {"doc_type_mismatch": 4, "cache_based_parser": 4} | needs_followup |
| pos_receipt | 10 | 9 | 0 | 1 | 0 | {"businessNo": 5, "merchantName": 3, "totalAmount": 1} | {"cache_based_parser": 6, "doc_type_mismatch": 2} | needs_followup |
| unknown | 1 | 1 | 0 | 0 | 0 | {"merchantName": 1} | {} | pass_with_warning |

## 5. baseline 영수증 핵심 필드 점검
| documentType | 핵심 필드 | filled | missing | 주요 문제 |
|---|---|---:|---:|---|
| card_receipt | address | 12 | 1 | missing 집중 개선 후보 |
| card_receipt | businessNo | 11 | 2 | missing 집중 개선 후보 |
| card_receipt | merchantName | 11 | 2 | missing 집중 개선 후보 |
| card_receipt | phone | 12 | 1 | missing 집중 개선 후보 |
| card_receipt | totalAmount | 11 | 2 | missing 집중 개선 후보 |
| food_cafe_receipt | merchantName | 11 | 4 | missing 집중 개선 후보 |
| food_cafe_receipt | totalAmount | 14 | 1 | missing 집중 개선 후보 |
| medical_receipt | merchantName | 4 | 2 | missing 집중 개선 후보 |
| medical_receipt | totalAmount | 6 | 0 | OK |
| pos_receipt | businessNo | 5 | 5 | missing 집중 개선 후보 |
| pos_receipt | merchantName | 7 | 3 | missing 집중 개선 후보 |
| pos_receipt | totalAmount | 9 | 1 | missing 집중 개선 후보 |
| unknown | merchantName | 0 | 1 | missing 집중 개선 후보 |
| unknown | totalAmount | 1 | 0 | OK |

## 6. invoice_statement 회귀 확인
| sample | expectedRowCount | actualRowCount | status | warning |
|---|---:|---:|---|---|
| 1.jpg | 28 | 28 | exact | [] |
| 2.pdf | 13 | 13 | exact | ["insuranceCode:ocr_source_missing:보험No OCR 원문에서 보험코드 후보를 찾지 못함 - 빈 값 유지"] |
| 3.pdf | 1 | 1 | exact | ["insuranceCode:ocr_source_missing:보험No OCR 원문에서 보험코드 후보를 찾지 못함 - 빈 값 유지"] |
| 4.pdf | 1 | 1 | exact | ["taxAmount=doc_level_pushdown", "totalAmount=doc_level_pushdown"] |
| 5.pdf | 6 | 6 | exact | ["multiline_layout_mapping_applied", "quantity:ambiguous_numeric_candidates:quantity candidates 3/6; kept existing empty values"] |
| 6.pdf | 6 | 6 | exact | [] |
| 7.pdf | 1 | 1 | exact | [] |

## 7. qualityTags 분석
| qualityTag | total | fail/error | 주요 missing | 주요 warning |
|---|---:|---:|---|---|
| __none__ | 23 | 5 | {"remark": 4, "totalAmount": 3, "supplyAmount": 2, "taxAmount": 2, "insuranceCode": 2, "amount": 2} | {"doc_type_mismatch": 5, "insuranceCode": 2, "cache_based_parser": 1, "multiline_layout_mapping_applied": 1, "quantity": 1} |
| address_garbled | 1 | 1 | {"amount": 1, "remark": 1} | {"taxAmount=doc_level_pushdown": 1, "totalAmount=doc_level_pushdown": 1} |
| address_tail_missing | 1 | 1 | {"manufacturingNo": 1, "remark": 1} | {} |
| blurred | 1 | 1 | {"merchantName": 1, "businessNo": 1, "address": 1} | {"cache_based_parser": 1} |
| buyer_only_document | 1 | 1 | {"serialNo": 1, "manufacturingNo": 1, "unit": 1, "remark": 1} | {} |
| handwritten | 2 | 0 | {} | {"doc_type_mismatch": 2} |
| long_receipt | 3 | 1 | {"businessNo": 1} | {"cache_based_parser": 3, "doc_type_mismatch": 1} |
| lot_serial_table | 1 | 1 | {"serialNo": 1, "manufacturingNo": 1, "unit": 1, "remark": 1} | {} |
| low_contrast | 1 | 1 | {"merchantName": 1} | {"cache_based_parser": 1} |
| no_amount_summary | 2 | 2 | {"manufacturingNo": 2, "remark": 2, "serialNo": 1, "unit": 1} | {} |
| ocr_garbled | 1 | 1 | {"amount": 1, "remark": 1} | {"taxAmount=doc_level_pushdown": 1, "totalAmount=doc_level_pushdown": 1} |
| ocr_noise | 11 | 1 | {"merchantName": 1} | {"doc_type_mismatch": 1} |
| optional_supplier | 1 | 1 | {"serialNo": 1, "manufacturingNo": 1, "unit": 1, "remark": 1} | {} |
| party_block_garbled | 1 | 1 | {"amount": 1, "remark": 1} | {"taxAmount=doc_level_pushdown": 1, "totalAmount=doc_level_pushdown": 1} |
| rotated | 1 | 0 | {} | {"cache_based_parser": 1, "finance_slip_policy_review": 1} |
| shadow | 2 | 2 | {"merchantName": 2, "totalAmount": 1} | {"cache_based_parser": 2} |
| skewed | 2 | 1 | {"merchantName": 1, "totalAmount": 1} | {"cache_based_parser": 2, "finance_slip_policy_review": 1} |
| small_text | 13 | 8 | {"merchantName": 6, "businessNo": 5, "phone": 1, "totalAmount": 1} | {"cache_based_parser": 12, "doc_type_mismatch": 1} |

## 8. 주요 문제 목록
| priority | 문제 | 영향 문서 | 원인 추정 | 후속 작업 |
|---|---|---|---|---|
| P1 | documentType/status 오분류 또는 unknown | card_receipt | missing=merchantName:2, businessNo:2, phone:1, address:1; warning=doc_type_mismatch:3, cache_based_parser:2; mismatch=3 | classifier signal과 suppression 정책 점검 |
| P2 | documentType/status 오분류 또는 unknown | pos_receipt | missing=businessNo:5, merchantName:3, totalAmount:1; warning=cache_based_parser:6, doc_type_mismatch:2; mismatch=2 | classifier signal과 suppression 정책 점검 |
| P3 | documentType/status 오분류 또는 unknown | medical_receipt | missing=merchantName:2; warning=doc_type_mismatch:4, cache_based_parser:4; mismatch=4 | classifier signal과 suppression 정책 점검 |
| P4 | documentType/status 오분류 또는 unknown | food_cafe_receipt | missing=merchantName:4, totalAmount:1; warning=cache_based_parser:5; mismatch=0 | classifier signal과 suppression 정책 점검 |
| P5 | 핵심 필드 missing | finance_slip | missing=-; warning=cache_based_parser:2, finance_slip_policy_review:2; mismatch=0 | 상단 field extraction과 OCR cache 품질 재검증 |
| P6 | qualityTags metadata 보강 | baseline/google 일부 및 invoice_statement 일부 | __none__ tag가 존재하여 tag 기반 실패 원인 분석 해상도 제한 | 샘플 추가 없이 manifest metadata만 별도 작업에서 보강 |

## 9. 다음 개선 우선순위
- P1: documentType/status 오분류 또는 unknown (card_receipt)
- P2: documentType/status 오분류 또는 unknown (pos_receipt)
- P3: documentType/status 오분류 또는 unknown (medical_receipt)
- P4: documentType/status 오분류 또는 unknown (food_cafe_receipt)
- P5: 핵심 필드 missing (finance_slip)
- P6: qualityTags metadata 보강 (baseline/google 일부 및 invoice_statement 일부)

## 10. 검증 결과
- py_compile: PASS: python -m py_compile scripts/verify_baseline_receipt_invoice_quality_t14.py
- typecheck: PASS: npm.cmd run typecheck
- build: PASS: npm.cmd run build (Next.js reported existing ESLint nextVitals warning, exit 0)

## 수집 방식 한계
- baseline/google 계열은 기존 최신 validation_results JSON을 우선 사용했다.
- receipt_generalization은 RunAll export가 없어 ocr_cache 텍스트와 현재 parser를 이용한 cache_based_parser 결과이며, 실제 재OCR/Template 경로 결과가 아니다.
- new_samples는 이번 범위상 샘플 존재와 metadata 분포만 확인했다.
- tax_invoice는 placeholder로 표시하고 audit 대상에서 제외했다.
