# T-7a: Remaining Value Mapping and Amount Column Stabilization
**작업일**: 2026-05-14
**모델**: Claude Code Sonnet

---

## 1. 수정 파일

| 파일 | 수정 내용 |
|---|---|
| `ocr-server/extractors/invoice_statement.py` | Fix1~Fix5 (아래 상세 참조) |

## 2. 백업 파일

| 백업 파일 | 설명 |
|---|---|
| `backup/invoice_statement_20260514_1100_before_T7a_value_mapping.py` | T-7a 작업 전 전체 백업 |

---

## 3. rowCount before/after

| 샘플 | GT | Before T-7a | After T-7a | 상태 |
|---|---|---|---|---|
| 1.jpg | 28 | 28 | 28 | OK |
| 2.pdf | 13 | 13 | 13 | OK |
| 3.pdf | 1 | 1 | 1 | OK |
| 4.pdf | 1 | 1 | 1 | OK |
| 5.pdf | 6 | 6 | 6 | OK |
| 6.pdf | 6 | 6 | 6 | OK |
| 7.pdf | 1 | 1 | 1 | OK |

rowCount: 7/7 exact 유지

---

## 4. Fill Rate before/after

주의: fill rate는 각 샘플의 manifest tableExpectedColumns (required+optional) 기준으로 계산.
T-6m 기술서의 baseline 수치는 계산 방식이 다를 수 있음 (required-only 등).

| 샘플 | T-7a 시작 전 | T-7a 완료 후 | delta | extractionSource |
|---|---|---|---|---|
| 1.jpg | 60.4% | 60.4% | 0.0% | expected_columns_header_match |
| 2.pdf | 44.8% | 44.8% | 0.0% | op_anchor_reconstructed_table |
| 3.pdf | 16.7% | 16.7% | 0.0% | legacy_text_items |
| 4.pdf | 60.0% | 80.0% | +20.0% | expected_columns_header_match |
| 5.pdf | 14.8% | 14.8% | 0.0% | legacy_text_items |
| 6.pdf | 50.0% | 50.0% | 0.0% | expected_columns_header_match |
| 7.pdf | 50.0% | 66.7% | +16.7% | expected_columns_header_match |

---

## 5. 샘플별 개선 내용

### 4.pdf (+20.0% fill rate)
- taxAmount 복구: OCR 원문에 "2,576,000" 확인. 문서 레벨 금액 값을 단일 품목 행에 pushdown.
- totalAmount 복구: OCR 원문에 "28,338,000 (TOTAL)" 확인. 동일 pushdown 적용.
- 적용 로직: extract_invoice_statement_fields - rowCount==1 문서에서 row-level 컬럼 비어있고 doc-level 금액 있을 때 복사. expected columns에 포함된 경우에만.

### 7.pdf (+16.7% fill rate)
- quantity=1,000 복구: OCR에서 "1,000"이 itemName/serialLotComposite/unit과 다른 y-band에 위치해 별도 행으로 분리됨. no_item_name 거부로 손실됐던 것 복구.
- 적용 로직: _table_items_with_expected_columns - quantity만 있는 행을 직전 행(serialLotComposite/unit 존재, quantity 없음)에 병합. 수치 범위 guard (1~100,000) 적용.

### 3.pdf (fill rate 동일, 내부 개선)
- garbage quantity 제거: header_column_mapping 경로에서 '제조회사 o묘 0 공급받눈재인료관용'이 quantity로 잘못 매핑됐던 것 제거.
- itemName 경로 복구: score 비교 개선으로 legacy_text_items 경로가 올바르게 선택됨. itemName='에스피씨세파클러캡슬250mg30 캡슐' 복구.
- fill rate: 쓰레기 값 제거 및 itemName 복구로 동일 유지 (2/12 = 16.7%).

---

## 6. 샘플별 남은 문제

### 1.jpg
- missing: unit, supplyAmount, taxAmount, totalAmount, remark (모두 optional)
- 판정: 문서 헤더에 해당 컬럼 없음. OCR source 부재. 수정 대상 아님.

### 2.pdf
- missing: insuranceCode (all 13 rows), amount, totalAmount, remark (optional)
- 판정: OCR 원문 "보험NO □ 14 □ S O" - 보험코드 데이터가 OCR에서 불명확. OP-anchor 열에 명확한 insuranceCode 패턴 없음.
- insuranceCode: OCR source missing 판정. valueMappingWarnings 추가 필요 (현재 미구현).

### 3.pdf
- extractionSource: legacy_text_items
- itemName 끝에 '0묘' 잡음 포함 (OCR garbled text)
- insuranceCode, spec, quantity, unitPrice, amount, manufacturer, manufacturingExpiryComposite 모두 미채움
- 판정: 문서 OCR 품질 낮아 구조 추출 한계. 주요 컬럼 복구 위해 별도 구조 보정 필요.

### 5.pdf
- extractionSource: legacy_text_items
- itemCode, unitPrice, amount, supplyAmount, taxAmount, totalAmount 모두 미채움
- OCR 원문에 "NRFS75M, NRDA4P" 등의 itemCode와 금액 데이터 존재하나, 품목명/코드/금액이 서로 다른 OCR row에 분리됨
- 판정: 복잡한 다단 layout으로 legacy path에서 연결 불가. T-7a 범위 초과.

### 6.pdf
- missing: serialNo, manufacturingNo, unit, remark (모두 optional)
- 판정: 문서 헤더에 해당 컬럼 없음. 올바르게 비어 있음.

---

## 7. 금액 계열 컬럼 점검 결과

### amountColWarnings (amount 패턴이 비금액 컬럼에 있는 경우)
- 4.pdf row[0].quantity='1,000': quantity 컬럼에 콤마 포맷 숫자. 실제는 수량이므로 false positive.
- 7.pdf row[0].quantity='1,000': 동일. 수량이 1,000개이므로 정상.

### amount 컬럼 오배치 실제 사례
없음. 감지된 '1,000' 패턴은 실제 수량 값으로 확인됨.

### amount 혼용 점검
- 4.pdf: amount 컬럼 미채움, supplyAmount='25,760,000' 채움. 문서에 'amount' 헤더 없고 'supplyAmount' 헤더만 있어서 정상.

---

## 8. valueMappingWarnings 요약

### 4.pdf (doc-level pushdown)
- taxAmount=doc_level_pushdown: 문서 레벨 taxAmount를 단일 행에 복사
- totalAmount=doc_level_pushdown: 문서 레벨 totalAmount를 단일 행에 복사

### 2.pdf insuranceCode
- 13개 row 모두 insuranceCode 미채움
- OCR 원문: "보험NO □ 14 □ S O" - 실질 데이터 불명확
- 판정: OCR source missing

---

## 9. 구현된 Fix 목록

| Fix | 위치 | 내용 |
|---|---|---|
| Fix1 | _table_item_column_score | garbage quantity (한글 포함 또는 20자 초과)는 score에서 제외 |
| Fix2 | _build_canonical_table_rows | quantity에 한글/긴 텍스트 있으면 clear |
| Fix3 | _table_items_with_expected_columns | quantity-only 행을 직전 행에 병합 (serialLotComposite+unit guard) |
| Fix4 | _detect_table | header_items vs table_items 선택 시 count가 같으면 score도 비교 |
| Fix5 | extract_invoice_statement_fields | 단일 행 문서에서 taxAmount/supplyAmount/totalAmount를 doc-level에서 pushdown |

---

## 10. 검증 결과

| 검증 항목 | 결과 |
|---|---|
| python -m py_compile extractors/invoice_statement.py | PASS |
| python scripts/verify_invoice_table_rows_t7a.py | PASS (rowCount 7/7) |
| npm run typecheck | PASS |
| npm run build | PASS |

---

## 11. 회귀 여부

| 샘플 | rowCount | extractionSource | 회귀 여부 |
|---|---|---|---|
| 1.jpg | 28/28 | expected_columns_header_match | 없음 |
| 2.pdf | 13/13 | op_anchor_reconstructed_table | 없음 |
| 3.pdf | 1/1 | legacy_text_items | 없음 (내부 개선) |
| 4.pdf | 1/1 | expected_columns_header_match | 없음 |
| 5.pdf | 6/6 | legacy_text_items | 없음 |
| 6.pdf | 6/6 | expected_columns_header_match | 없음 |
| 7.pdf | 1/1 | expected_columns_header_match | 없음 |

1.jpg/4.pdf/6.pdf 안정 결과 유지.

---

## 12. 다음 작업 판단

T-7a 목표 달성:
- rowCount 7/7 exact 유지
- 4.pdf: taxAmount/totalAmount 복구 (+20%)
- 7.pdf: quantity=1,000 복구 (+16.7%)
- 3.pdf: garbage quantity 제거, itemName 경로 복구

남은 한계 (다음 단계 판단 필요):
- 2.pdf insuranceCode: OCR source missing 확인. valueMappingWarnings 명시적 추가 고려.
- 5.pdf itemCode/unitPrice/amount: 다단 OCR layout 구조 문제. 별도 T-8 작업 또는 샘플 교체 검토.
- 1.jpg/6.pdf fill rate 낮음: 계산 방식 차이 (required+optional vs required-only). 계산 기준 통일 검토.
