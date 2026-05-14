# T-8-final 거래명세서 tableRows 1차 안정화 마감 리포트

## 1. 최종 결론
- 거래명세서 tableRows 1차 안정화는 완료로 판정한다.
- rowCount는 7개 샘플 모두 GT와 exact match다.
- expected display schema 기준 주요 컬럼 매핑은 현재 품질 기준을 통과했다.
- T-9a에서 잔여 empty field의 OCR 후보까지 재스캔했으나, 추가로 안전하게 자동 복구할 수 있는 항목은 없었다.
- 후속 T-9 계열은 마감 차단 이슈가 아니라 별도 고도화 범위로 분리한다.

## 2. 작업 범위 요약
- T-6 계열: expectedColumns/schema/display 정리, row grouping 안정화, GT row alignment, Template bounds/colGuides 검증, OP-anchor reconstruction 기반 마련.
- T-7 계열: row-level value mapping 안정화, 금액 계열 오배치 점검, doc-level pushdown 및 quantity 병합 회귀 확인.
- T-8 계열: 2.pdf insuranceCode OCR source missing warning 정책, 5.pdf multiline layout 후처리로 itemCode/unitPrice/amount 복구.
- T-9a: 잔여 empty field OCR 후보 스캔, 5.pdf quantity 후보 안전성 검토, 3.pdf/2.pdf source missing 및 구조 한계 재분류.

## 3. 최종 rowCount 결과
| 샘플 | GT | OCR | 상태 |
|---|---:|---:|---|
| 1.jpg | 28 | 28 | exact |
| 2.pdf | 13 | 13 | exact |
| 3.pdf | 1 | 1 | exact |
| 4.pdf | 1 | 1 | exact |
| 5.pdf | 6 | 6 | exact |
| 6.pdf | 6 | 6 | exact |
| 7.pdf | 1 | 1 | exact |

## 4. 샘플별 최종 상태
| 샘플 | 주요 성과 | 남은 한계 | 판정 |
|---|---|---|---|
| 1.jpg | rowCount 28/28, display fill 98.5%, itemName/spec/manufacturingNo/expiryDate/quantity/unitPrice/amount 안정 | optional amount/summary row columns empty | pass |
| 2.pdf | rowCount 13/13, OP-anchor reconstruction으로 13행 복구, OP-* itemCode 및 단가 계열 유지 | insuranceCode OCR source missing, 임의 생성 금지 | pass_with_warning |
| 3.pdf | rowCount 1/1, itemName 유지, garbage quantity 제거 유지 | 낮은 fill rate는 OCR/구조 한계, insuranceCode source missing | acceptable_limit |
| 4.pdf | rowCount 1/1, taxAmount=2,576,000, totalAmount=28,338,000, lotNo/unit/quantity 유지 | doc-level pushdown warning 추적 | pass_with_warning |
| 5.pdf | rowCount 6/6, itemName/itemCode/unitPrice/amount 6/6, multiline layout 후처리 적용 | quantity 2/6, 후보 3/6 ambiguous, supply/tax/total은 안전 연결 보류 | pass_with_warning |
| 6.pdf | rowCount 6/6, ANDC300C row 유지, itemCode/itemName/quantity/lotNo/expiryDate 안정 | optional serial/manufacturing/unit/remark empty | pass |
| 7.pdf | rowCount 1/1, serialLotComposite/unit/quantity=1,000 유지 | manufacturingNo/remark optional empty | pass |

## 5. 최종 warning 목록
| 샘플 | warning | 의미 | 후속 |
|---|---|---|---|
| 2.pdf | insuranceCode:ocr_source_missing | 보험No/보험코드 후보가 OCR 원문에서 명확하지 않아 빈 값 유지 | T-9c 후보 |
| 3.pdf | insuranceCode:ocr_source_missing | 단일 row 문서이나 보험코드 OCR source가 명확하지 않음 | T-9b/T-9c 후보 |
| 4.pdf | taxAmount=doc_level_pushdown | 문서 레벨 taxAmount를 단일 row에 보수적으로 복사 | 모니터링 |
| 4.pdf | totalAmount=doc_level_pushdown | 문서 레벨 totalAmount를 단일 row에 보수적으로 복사 | 모니터링 |
| 5.pdf | multiline_layout_mapping_applied | 다단 OCR layout의 itemCode/unitPrice/amount 블록을 기존 6행에 매핑 | 완료 |
| 5.pdf | quantity:ambiguous_numeric_candidates | quantity 후보가 3/6만 확인되어 자동 채움 보류 | T-9a 이후 별도 후보 |

## 6. 금액 계열 최종 점검
- 실제 금액 계열 오배치 없음.
- 4.pdf와 7.pdf의 `quantity=1,000`은 금액이 아니라 수량으로 정상 분류했다.
- 4.pdf의 taxAmount/totalAmount doc-level pushdown은 warning으로 추적된다.
- summary 금액이 table row로 섞인 심각 사례는 발견되지 않았다.
- 5.pdf는 itemCode/unitPrice/amount 6/6 복구 후에도 rowCount와 기존 non-empty value를 보존했다.

## 7. 전체 필드 점검 요약
- supplier/buyer가 뒤바뀐 명확한 사례 없음.
- 사업자번호/전화번호가 lot/serial로 오인된 명확한 사례 없음.
- summary 금액이 table row로 오염된 심각 사례 없음.
- 6.pdf supplier empty는 buyer-only 문서 구조상 정상 한계로 분류한다.
- 전체 문서 필드 쪽 심각 회귀는 없으며, tableRows 마감 판단을 막지 않는다.

## 8. 최종 검증 결과
- py_compile: PASS (`extractors/invoice_statement.py`, `scripts/verify_invoice_table_rows_t9a.py`)
- verify script: PASS (`verify_invoice_statement_full_quality_t8_final_precheck.py`, `verify_invoice_table_rows_t9a.py` 기준 rowCount 7/7)
- typecheck: PASS (`npm.cmd run typecheck`)
- build: PASS (`npm.cmd run build`, exit code 0)
- build warning: 기존 `ESLint: nextVitals is not iterable` 메시지는 계속 출력되나 build exit code는 0이다.

## 9. 남은 후속 후보
### T-9b. 3.pdf 낮은 fill rate 원인 분석
- 필요성: 보험코드/규격/수량/단가/금액/제조회사/제조번호-유효기간 후보가 label proximity 기준으로 명확하지 않다.
- 예상 범위: 3.pdf OCR raw 구조 분석, 단일 row 문서 전용 후보 스코어링, garbage text guard 강화.

### T-9c. 2.pdf 보험No OCR source 개선
- 필요성: OP-anchor reconstruction은 안정화됐지만 insuranceCode source가 OCR 원문에서 명확하지 않다.
- 예상 범위: 보험No/header 주변 OCR 품질 개선 또는 source missing 표시 UX 개선. 임의 생성은 금지.

### T-9d. Template/RunOCR 저장 annotation 기반 end-to-end 검증
- 필요성: tableRows 안정화 결과가 Template/RunOCR 저장 annotation 경로에서도 유지되는지 확인해야 한다.
- 예상 범위: 저장 annotation 기반 RunOCR, template bounds/colGuides 재사용, UI 표시/저장 회귀 검증.

### 5.pdf quantity 추가 복구
- 현재 판단: quantity 후보가 3/6만 확인되어 자동 복구 보류.
- 예상 범위: 다단 OCR layout에서 수량 블록과 단가/금액 블록을 더 정교하게 분리하는 별도 고도화.

## 10. 다음 작업 판단
- 거래명세서 tableRows 1차 안정화는 마감한다.
- 후속 T-9는 별도 고도화로 분리한다.
- 다음 작업은 Template/RunOCR E2E 검증 또는 다른 문서 유형 확장으로 이동 가능하다.
