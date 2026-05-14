# T-6m Expected Column Value Mapping Stabilization 보고서

**생성일**: 2026-05-14  
**작업**: T-6m value mapping 안정화  
**기반**: T-6n rowCount 7/7 exact 달성 이후 value fill rate 개선

---

## 1. 수정 파일 목록

| 파일 | 변경 내용 |
|---|---|
| `ocr-server/extractors/invoice_statement.py` | 3개 섹션 수정 (T-6m: value mapping 보정) |
| `ocr-server/scripts/verify_invoice_table_rows_t6m.py` | 신규 생성 (value fill rate 검증 스크립트) |

## 2. 백업 파일 목록

| 파일 | 경로 |
|---|---|
| invoice_statement_20260514_before_T6m_value_mapping.py | `ocr-server/backup/` |

---

## 3. rowCount before/after (7개 샘플)

| 샘플 | GT | before | after | 상태 |
|---|---:|---:|---:|---|
| 1.jpg | 28 | 28 | 28 | exact (유지) |
| 2.pdf | 13 | 13 | 13 | exact (유지) |
| 3.pdf | 1 | 1 | 1 | exact (유지) |
| 4.pdf | 1 | 1 | 1 | exact (유지) |
| 5.pdf | 6 | 6 | 6 | exact (유지) |
| 6.pdf | 6 | 6 | 6 | exact (유지) |
| 7.pdf | 1 | 1 | 1 | exact (유지) |

**rowCount 회귀 없음 ✓**

---

## 4. Expected Column Fill Rate before/after

### 4.1 1.jpg (28 rows × 7 cols)

| 컬럼 | key | before | after | 변화 |
|---|---|---:|---:|---|
| 품목 | itemName | 100% | 100% | - |
| 규격 | spec | 100% | 100% | - |
| 제조번호 | manufacturingNo | 96.4% | 96.4% | - |
| 유효기간 | expiryDate | 96.4% | 96.4% | - |
| 수량 | quantity | 96.4% | 96.4% | - |
| 단가 | unitPrice | 100% | 100% | - |
| 금액 | amount | 100% | 100% | - |
| **overall** | | **98.5%** | **98.5%** | **0** |

1행 각 컬럼 누락 (1/28): OCR 데이터 누락으로 추정. 현재 단계에서 수정 불가.

### 4.2 2.pdf (13 rows × 8 cols, op_anchor_reconstructed_table)

| 컬럼 | key | before | after | 변화 |
|---|---|---:|---:|---|
| NO | rowIndex | 100% | 100% | - |
| 품목코드 | itemCode | 100%* | 92.3%† | 품질 개선 |
| 품목명 | itemName | 15.4% | 30.8% | **+15.4pp** |
| 수량 | quantity | 61.5% | 69.2% | **+7.7pp** |
| 소비자단가 | consumerUnitPrice | 92.3% | 92.3% | - |
| 공급단가 | supplyUnitPrice | 92.3% | 92.3% | - |
| 공급금액 | supplyAmount | 23.1% | 15.4% | -7.7pp‡ |
| 보험No | insuranceCode | 0% | 0% | 미개선 |
| **overall** | | **60.6%** | **61.5%** | **+0.9pp** |

*before itemCode 100%는 "Y", "2" 등 잘못된 값 포함. 수정 후 "OP-NA0300", "OP-NA0030" 등 올바른 OP-* 코드로 개선.  
†1개 row: extra_anchor(단독 확장 앵커) 텍스트가 3자 미만 → itemCode="" 처리(올바른 동작).  
‡supplyAmount 감소: 약품명 텍스트가 이전에는 amount로 잘못 분류되다가 이제 itemName으로 올바르게 분류됨. 실제 값 개선.

**insuranceCode 0% 분석**: 2.pdf의 보험No 컬럼 라인이 `[A-Za-z]{1,3}\d{2,}` 패턴에 해당하는 OCR 텍스트를 포함하지 않음. 패턴을 더 완화하거나 실제 OCR 출력을 분석하면 추가 개선 가능 (T-7 대상).

### 4.3 3.pdf (1 row × 9 cols, header_column_mapping)

| 컬럼 | key | before | after | 변화 |
|---|---|---:|---:|---|
| 순번 | rowIndex | 100% | 100% | - |
| 보험코드 | insuranceCode | 0% | 0% | - |
| 품명 | itemName | 0% | 0% | - |
| 규격 | spec | 0% | 0% | - |
| 수량 | quantity | 100%* | 100%* | - |
| 단가 | unitPrice | 0% | 0% | - |
| 금액 | amount | 0% | 0% | - |
| 제조회사 | manufacturer | 0% | 0% | - |
| 제조번호/유효기간 | manufacturingExpiryComposite | 0% | 0% | - |
| **overall** | | **22.2%** | **22.2%** | **0** |

*quantity 값이 "회사 o재 0 공급받는사람로부터" (party text) → 오매핑. 3.pdf는 헤더 감지 misalignment로 인한 구조적 문제. T-6m 범위 밖.

**미수정 이유**: 3.pdf는 `header_column_mapping` 경로에서 헤더 행이 party 정보 행으로 잘못 감지됨. rowCount=1 회귀 없이 이를 수정하려면 header 감지 로직 전체 수정이 필요 → T-7에서 검토.

### 4.4 4.pdf (1 row × 7 cols, expected_columns_header_match)

| 컬럼 | key | before | after | 변화 |
|---|---|---:|---:|---|
| 품목명 | itemName | 100% | 100% | - |
| LotNo. | lotNo | 0% | **100%** | **+100pp** |
| 단위 | unit | 100%* | **100%†** | 값 정상화 |
| 수량 | quantity | 100%* | **100%†** | 값 정상화 |
| 단가 | unitPrice | 100% | 100% | - |
| 공급가액 | supplyAmount | 100% | 100% | - |
| 세액 | taxAmount | 0% | 0% | 미개선 |
| **overall** | | **71.4%** | **85.7%** | **+14.3pp** |

*before: unit="0350823-231024-200811"(lot번호 형식), quantity="BOX 1,000"(단위포함)  
†after: unit="BOX", quantity="1,000", lotNo="0350823-231024-200811" (올바르게 분리)

taxAmount: OCR 출력에 taxAmount 컬럼 텍스트 없음 → 데이터 한계.

### 4.5 5.pdf (6 rows × 5 cols, legacy_text_items)

| 컬럼 | key | before | after | 변화 |
|---|---|---:|---:|---|
| 품명 | itemName | 100% | 100% | - |
| 품목코드 | itemCode | 0% | 0% | 미개선 |
| 수량 | quantity | 33.3% | 33.3% | - |
| 단가 | unitPrice | 0% | 0% | 미개선 |
| 금액 | amount | 0% | 0% | 미개선 |
| **overall** | | **26.7%** | **26.7%** | **0** |

**미수정 이유**: 5.pdf는 `legacy_text_items` 경로 사용 (expected_columns_header_match/header_column_mapping 모두 header 미검출). legacy 경로는 컬럼 구조 없이 rawText 기반 추출만 수행 → itemCode/unitPrice/amount 컬럼 값 접근 불가. Header 감지 개선 필요 (T-7 대상).

### 4.6 6.pdf (6 rows × 6 cols, expected_columns_header_match)

| 컬럼 | key | before | after | 변화 |
|---|---|---:|---:|---|
| NO | rowIndex | 100% | 100% | - |
| 제품코드 | itemCode | 100% | 100% | - |
| 제품명 | itemName | 100% | 100% | - |
| 수량 | quantity | 100% | 100% | - |
| LotNo | lotNo | 66.7% | 66.7% | - |
| 유효일자 | expiryDate | 66.7% | 66.7% | - |
| **overall** | | **88.9%** | **88.9%** | **0** |

lotNo/expiryDate 4/6: 2개 row가 OCR 출력에 해당 값 없음. 데이터 한계로 추정.

### 4.7 7.pdf (1 row × 4 cols, expected_columns_header_match)

| 컬럼 | key | before | after | 변화 |
|---|---|---:|---:|---|
| 품명 | itemName | 100% | 100% | - |
| 시리얼/로트No. | serialLotComposite | 100% | 100% | - |
| 단위 | unit | 100% | 100% | - |
| 수량 | quantity | 0% | 0% | 미개선 |
| **overall** | | **75%** | **75%** | **0** |

quantity: OCR 출력 내 quantity 컬럼 경계에 값이 없거나, 값이 "0"으로 필터됨. debug 없이 추가 수정 어려움 → T-7에서 OCR 원문 확인 필요.

---

## 5. 구현된 보정 내용 요약

### Fix 1: 2.pdf itemCode fallback guard
**위치**: `_op_anchor_reconstruct_table` (~line 1067)  
**변경**: `_extract_op_anchor_code(anchor.text) or _clean_value(anchor.text)` → 3자 미만 fallback은 "" 처리  
**효과**: "Y", "2" 등 노이즈 값 itemCode 제거. 올바른 "OP-NA0300" 등만 사용.

### Fix 2: 2.pdf 컬럼 라인 분류 순서 재배열 + 패턴 확장
**위치**: `_op_anchor_reconstruct_table` (~line 1089)  
**변경**:
- insuranceCode 체크를 amount 체크보다 먼저 이동 (`[A-Za-z]{1,3}\d{2,}` extended)
- itemName: 숫자 포함 약품명 허용 (guard: `not re.fullmatch(r"[A-Za-z]{1,3}\d{2,}", text)`)
**효과**: itemName 15.4%→30.8% (+15.4pp), itemCode 값 품질 개선

### Fix 3: unit/lotNo 혼동 post-processing
**위치**: `_build_canonical_table_rows` (~line 5754)  
**변경**: unit에 lot번호 패턴(`\d{6,}[-/]\d{6}`) 감지 시 lotNo로 이동; quantity에 "BOX/EA/..." prefix 있으면 unit과 분리  
**효과**: 4.pdf lotNo 0%→100%, unit "0350823-231024-200811"→"BOX", quantity "BOX 1,000"→"1,000"

### Fix 4: tableMeta value mapping 진단 정보 추가
**위치**: `_build_canonical_table_rows` (~line 5836)  
**추가**: `expectedValueFillRate`, `expectedFilledKeys`, `expectedMissingKeys`, `valueMappingWarnings`

---

## 6. 2.pdf OP-anchor value mapping 결과 요약

| 항목 | before | after |
|---|---|---|
| itemCode | 100%("Y","2" 포함 잘못된 값) | 92.3% (올바른 OP-* 코드) |
| itemName | 15.4% (2/13) | 30.8% (4/13) |
| quantity | 61.5% (8/13) | 69.2% (9/13) |
| consumerUnitPrice | 92.3% | 92.3% |
| supplyUnitPrice | 92.3% | 92.3% |
| supplyAmount | 23.1% | 15.4% (drug name 오분류 제거) |
| insuranceCode | 0% | 0% (패턴 불일치, 추가 조사 필요) |

---

## 7. rowCount 회귀 여부

**없음**. 7/7 exact 유지.

```
1.jpg: 28/28 exact
2.pdf: 13/13 exact
3.pdf: 1/1 exact
4.pdf: 1/1 exact
5.pdf: 6/6 exact
6.pdf: 6/6 exact
7.pdf: 1/1 exact
```

---

## 8. py_compile / typecheck / build 결과

| 검증 | 결과 |
|---|---|
| `python -m py_compile extractors/invoice_statement.py` | OK |
| `npm run typecheck` | OK (오류 없음) |
| `npm run build` | OK (ESLint nextVitals 경고는 기존 이슈) |

---

## 9. 남은 missing column 분석

| 샘플 | 미개선 컬럼 | 원인 |
|---|---|---|
| 2.pdf | insuranceCode (0%) | 2.pdf OCR 출력의 보험No 텍스트 형식 미확인 |
| 2.pdf | supplyAmount (15.4%) | 실제 데이터에 3번째 금액 없는 column 다수 |
| 3.pdf | itemName, spec, insuranceCode, unitPrice, amount, manufacturer, manufacturingExpiryComposite | 헤더 오감지 (party text 헤더로 인식) → 구조적 문제 |
| 4.pdf | taxAmount (0%) | OCR 출력에 세액 텍스트 없음 |
| 5.pdf | itemCode, unitPrice, amount (0%) | legacy_text_items 경로: 컬럼 구조 없음 |
| 6.pdf | lotNo (4/6), expiryDate (4/6) | 2개 row 해당 값 OCR 미출력 |
| 7.pdf | quantity (0%) | 컬럼 경계 불일치 또는 OCR 값 없음 |

---

## 10. 다음 작업 판단

**T-7 (금액 계열 검증)으로 이동 가능**.

단, T-6m에서 미해결된 항목은 다음 사이클에서 처리:
- **2.pdf insuranceCode**: 2.pdf 실제 OCR 출력의 보험No 텍스트 형식을 debug로 확인 필요
- **3.pdf 헤더 오감지**: header_column_mapping 헤더 감지 임계값 조정 (rowCount=1 guard 유지 전제)
- **5.pdf header 미검출**: 5.pdf multi-page OCR에서 header row 감지 개선
- **7.pdf quantity**: OCR 출력 debug로 quantity 컬럼 텍스트 확인

---

*보고서 자동 생성: T-6m value mapping stabilization*
