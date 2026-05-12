# T-6c 거래명세서 tableRows 컬럼 감지 보강 결과

## 1. 수정 파일
- `d:/Free_Vue/OCR/ocr-server/extractors/invoice_statement.py`

## 2. 백업 파일
- `d:/Free_Vue/OCR/ocr-server/backup/invoice_statement_20260512_before_T6c_header_column_detection_round2.py`

## 3. 핵심 요약
- **`_HEADER_CANONICAL_MAP` 확장**: 누락 패턴 6개 추가 — 보험No/보험번호, 제조회사, 소비자단가, 공급금액, 복합헤더(제조번호/유효기간, 시리얼/로트No.), 품목(단독), LotNo/LOTNO 변형
- **`_find_structured_header_row` 멀티라인 지원**: 인접 행(간격 ≤ 6% page_h) 병합으로 2개 미만 매치인 단일 행도 복합 헤더로 탐지
- **`_build_column_boundaries` 엣지 기반**: center_x → edge midpoint 기준 boundary, 첫 컬럼 x1 기반 시작(0.0 불사용) → NO/순번 같은 비캐노니컬 컬럼의 토큰이 첫 캐노니컬 컬럼으로 잘못 배치되는 문제 해결
- **`_assign_canonical_by_x` proximity fallback**: boundary 밖 토큰에 대해 가장 가까운 컬럼으로 fallback (평균 컬럼 폭 55% 이내)
- **`_split_composite_cell_value` 추가**: manufacturingNo 컬럼에서 날짜형 값 감지 시 expiryDate로 분리, serialNo 컬럼에서 LOT형 값은 lotNo에 보조 배치
- **`_table_items_from_header_mapping` 포함 기준 완화**: has_name_col 시 itemName만 검증, 없을 시 itemCode/quantity/unitPrice/amount 중 하나 존재로 대체

## 4. 보강 범위
- **표 영역 후보 제한**: `_build_column_boundaries` 첫 컬럼 x1 기반 시작으로 상단/왼쪽 비캐노니컬 영역 제한
- **헤더 row 탐지**: 멀티라인 병합 지원, itemName/quantity 보너스 가중치
- **복합/다중 line 헤더**: `_split_composite_cell_value`로 제조번호/유효기간, 시리얼/로트No. 처리
- **column boundary**: edge midpoint 기반, proximity fallback (+55% avg col width tolerance)
- **cell assignment**: `_assign_canonical_by_x` + proximity fallback
- **tableMeta.columns**: `_build_canonical_table_rows`에서 col_fill 기준 actual_columns에 반영 (기존 유지)

## 5. 구현 상세

### 변경 함수
| 함수 | 변경 내용 |
|---|---|
| `_HEADER_CANONICAL_MAP` | 패턴 확장 (6개 추가/재배치) |
| `_find_structured_header_row` | 멀티라인 병합 지원, 가중치 |
| `_build_column_boundaries` | x1/x2 edge 기반, 첫 컬럼 margin |
| `_assign_canonical_by_x` | proximity fallback 추가 |
| `_split_composite_cell_value` | 신규 — composite 컬럼 분리 |
| `_table_items_from_header_mapping` | 완화된 포함 기준, composite 처리 |

### 추가된 헤더 패턴 (T-6c)
| 헤더 텍스트 | canonical key | 비고 |
|---|---|---|
| 보험No, 보험NO, 보험번호 | insuranceCode | 2.pdf |
| 제조회사 | manufacturer | 3.pdf |
| 소비자단가 | unitPrice | 2.pdf |
| 공급금액 | supplyAmount | 2.pdf |
| 제조번호/유효기간, 유효기간/제조번호 | manufacturingNo (+ expiryDate 분리) | 3.pdf composite |
| 시리얼/로트No., Serial/Lot | serialNo (+ lotNo secondary) | 7.pdf composite |
| LotNo, LOTNO | lotNo | 4.pdf |
| 품목 (단독) | itemName | 1.jpg |

### 첫 컬럼 boundary 수정 (6.pdf NO 컬럼 문제)
- 기존: x_start = 0.0 → NO 컬럼의 "1","2","3" 값이 제품코드로 배치
- 변경: x_start = max(0, header_x1 - header_w*0.8) → 실제 컬럼 근처부터 시작

## 6. 샘플별 개선 결과 (브라우저 재실행 필요)
| 샘플 | rowCount | 개선 기대 항목 | 비고 |
|---|---:|---|---|
| 1.jpg | 27 유지 | manufacturingNo, expiryDate, unitPrice, amount 개선 기대 | 품목→itemName 이제 매핑됨 |
| 2.pdf | 2 유지 | insuranceCode, supplyAmount(공급금액) 감지 기대 | 소비자단가→unitPrice 이제 매핑 |
| 3.pdf | 1 유지 | insuranceCode, manufacturer, spec, manufacturingNo, expiryDate 감지 기대 | composite 헤더 처리 |
| 4.pdf | 1 유지 | lotNo, unit 개선 기대 | OCR garbled 한계 |
| 5.pdf | 6 유지 | itemCode, unitPrice, amount 개선 기대 | |
| 6.pdf | 6 유지 | lotNo 회귀 수정 + NO 컬럼 boundary 오염 해결 | 회귀 방지 기준 |
| 7.pdf | 1 유지 | serialNo, unit, quantity 개선 기대 | 시리얼/로트No. composite 처리 |

## 7. 회귀 확인
| 항목 | 결과 |
|---|---|
| itemName | 미수정 — 기존 추출 로직 유지 |
| rowCount | y-sort + 기존 detection 유지 |
| firstRowPreview | 기존 `_canonical_row_preview` 유지 |
| party fields | `_extract_party_fields` 미수정 |
| address fields | party 로직 미수정 |
| amount summary | `_extract_amount_fields` 미수정 |
| tableRows UI | frontend 미수정 |

## 8. 검증 결과
- **py_compile**: 통과
- **typecheck**: 통과 (오류 0건)
- **build**: 성공 (`/test` 42.2 kB)
- **브라우저 확인**: backend 재시작 후 1~7 샘플 재실행으로 확인 필요

## 9. 남은 문제
- 금액 계열(unitPrice/supplyAmount/taxAmount/amount/totalAmount)은 헤더 mapping이 이제 됐지만 실제 cell 값 품질은 OCR 정확도에 따라 다를 수 있음 → T-7
- OCR garbled 문서(4.pdf)의 헤더 감지는 여전히 partial 가능
- Template table bounds 연동은 아직 하지 않음 — 현재는 전체 문서 대상
- RunOCR 반영 미완료

## 10. 다음 추천 작업
- **T-7**: 거래명세서 금액 계열 컬럼 매핑 보강 (unitPrice/supplyAmount/taxAmount/amount/totalAmount 실제 값 품질)
- **T-6d**: table bounds 기반 컬럼 감지 — Template 연동 준비
- **RunOCR-Table-1**: RunOCR 거래명세서 tableRows 표시 반영
