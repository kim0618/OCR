# T-9a 잔여 empty field OCR 후보 스캔 및 안전 복구 결과

## 1. 수정 파일
- `ocr-server/extractors/invoice_statement.py`
- `ocr-server/scripts/verify_invoice_table_rows_t9a.py`

## 2. 백업 파일
- `c:\OCR\ocr-server\backup\invoice_statement_20260514_before_T9a_remaining_empty_recovery.py`

## 3. 핵심 요약
- rowCount exact: 7/7
- row grouping/OP-anchor/display schema 변경 없음
- 5.pdf quantity 후보는 안전 매칭 조건을 만족하지 않아 기존 empty 유지
- 2.pdf/3.pdf insuranceCode는 OCR source missing warning 유지

## 4. 후보 스캔 결과
| 샘플 | empty key | OCR 후보 존재 | 판정 | 조치 |
|---|---|---|---|---|
| 2.pdf | insuranceCode | none | ocr_source_missing | warning_kept |
| 3.pdf | insuranceCode | none | ocr_source_missing | warning_kept |
| 5.pdf | quantity | 3/6 | ambiguous_numeric_candidates | kept_empty |

## 5. before/after fill rate
| 샘플 | before | after | delta | 비고 |
|---|---:|---:|---:|---|
| 1.jpg | 60.4% | 60.4% | +0.0% | stable |
| 2.pdf | 44.8% | 44.8% | +0.0% | insuranceCode source_missing 유지 |
| 3.pdf | 16.7% | 16.7% | +0.0% | OCR/structure limit |
| 4.pdf | 80.0% | 80.0% | +0.0% | stable |
| 5.pdf | 48.1% | 48.1% | +0.0% | quantity unsafe; itemCode/unitPrice/amount 유지 |
| 6.pdf | 50.0% | 50.0% | +0.0% | stable |
| 7.pdf | 66.7% | 66.7% | +0.0% | stable |

## 6. 5.pdf quantity 분석
- OCR 후보: candidateCounts={'itemCode': 6, 'quantity': 3, 'unitPrice': 6, 'amount': 6}
- 복구 여부: quantity 2/6 유지
- 남은 한계: 수량 후보가 row 6개와 안정적으로 1:1 매칭되지 않아 자동 채움 보류

## 7. 3.pdf 낮은 fill rate 분석
- OCR 후보: warnings=insuranceCode:ocr_source_missing:보험No OCR 원문에서 보험코드 후보를 찾지 못함 - 빈 값 유지
- 복구 여부: fill 16.7% -> 16.7%
- 남은 한계: 단일 row이나 보험코드/규격/수량/단가/금액 후보가 label proximity 기준으로 명확하지 않음

## 8. 2.pdf insuranceCode 재확인
- OCR 후보: none
- warning 유지 여부: insuranceCode:ocr_source_missing:보험No OCR 원문에서 보험코드 후보를 찾지 못함 - 빈 값 유지
- 판정: OCR source missing 유지, 임의 생성 없음

## 9. rowCount 회귀 확인
| 샘플 | GT | OCR | 상태 |
|---|---:|---:|---|
| 1.jpg | 28 | 28 | OK |
| 2.pdf | 13 | 13 | OK |
| 3.pdf | 1 | 1 | OK |
| 4.pdf | 1 | 1 | OK |
| 5.pdf | 6 | 6 | OK |
| 6.pdf | 6 | 6 | OK |
| 7.pdf | 1 | 1 | OK |

## 10. valueMappingWarnings
- 1.jpg: -
- 2.pdf: insuranceCode:ocr_source_missing:보험No OCR 원문에서 보험코드 후보를 찾지 못함 - 빈 값 유지
- 3.pdf: insuranceCode:ocr_source_missing:보험No OCR 원문에서 보험코드 후보를 찾지 못함 - 빈 값 유지
- 4.pdf: taxAmount=doc_level_pushdown, totalAmount=doc_level_pushdown
- 5.pdf: multiline_layout_mapping_applied, quantity:ambiguous_numeric_candidates:quantity candidates 3/6; kept existing empty values
- 6.pdf: -
- 7.pdf: -

## 11. 검증 결과
- py_compile: PASS
- verify script: PASS
- typecheck: 별도 명령 결과 참조
- build: 별도 명령 결과 참조

## 12. 다음 작업 판단
- 추가 안전 복구 가능 항목 없음 -> T-8-final 마감 리포트 진행
- 3.pdf 구조 분석은 T-9b 후보
- 2.pdf 보험No OCR source 개선은 T-9c 후보
