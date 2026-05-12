# T-6 거래명세서 tableRows 컬럼 구조 매핑 1차 결과

## 1. 수정 파일
- `d:/Free_Vue/OCR/ocr-server/extractors/invoice_statement.py`

## 2. 백업 파일
- `d:/Free_Vue/OCR/ocr-server/backup/invoice_statement_20260512_before_T6_column_structure_mapping_round1.py`

## 3. 핵심 요약
- **기존 방식**: 전체 row 텍스트를 연결 → 패턴으로 수량/금액/LOT 등 추출 (컬럼 위치 무시)
- **T-6 신규 방식**: 품목표 헤더 row 탐지 → 헤더 cell x좌표 기준 column boundary 계산 → 각 data row cell을 x좌표로 canonical column에 직접 배치
- 헤더가 없는 문서(4.pdf 등)는 기존 방식으로 안전하게 fallback
- `_structured_text_order_items`의 행 순서 버그 수정 (y좌표 기반 정렬 보장)
- `_build_canonical_table_rows`에서 18개 canonical 컬럼 전체를 복사 (기존은 8개만 복사)
- 빈 컬럼에만 regex 보조 추출 적용 (헤더 기반 값이 있으면 덮어쓰지 않음)
- `_detect_table` 최종 items를 y좌표로 정렬하여 rowIndex가 시각적 순서를 따르게 함

## 4. 보강 범위
- **표 헤더 탐지**: `_find_structured_header_row` — rows를 순회하여 canonical match ≥ 2개인 row를 헤더로 인식
- **컬럼 경계 계산**: `_build_column_boundaries` — 헤더 cell center_x 기반 midpoint boundary
- **canonical column 매핑**: `_HEADER_CANONICAL_MAP` (17개 패턴) — 품목코드/품명/규격/LOT/Serial/제조번호/유효기간/수량/단위/단가/공급가액/세액/금액/합계금액/제조사/보험코드/비고
- **row cell 배치**: `_table_items_from_header_mapping` — `_assign_canonical_by_x`로 x좌표 기준 배치
- **row 정렬**: `_detect_table` 말단에서 y-sort, `_build_canonical_table_rows` 내부 y-sort, `_structured_text_order_items` cy 기반 정렬 수정
- **quantity/LOT/Serial/itemCode 보조 처리**: 헤더 기반으로 값이 있으면 regex 스킵, 없을 때만 보조 패턴 적용
- **금액 계열 보류**: 헤더 기반 column mapping에는 포함 (unitPrice/supplyAmount/taxAmount/amount/totalAmount), 대규모 독립 패턴 보강은 후속

## 5. 구현 상세
- **변경 함수 및 위치**:
  - `_HEADER_CANONICAL_MAP` 상수 추가 (line ~183)
  - `_match_header_to_canonical(text)` 추가 (line ~1105)
  - `_find_structured_header_row(rows, page_h)` 추가
  - `_build_column_boundaries(header_row, page_w)` 추가
  - `_assign_canonical_by_x(cx, boundaries)` 추가
  - `_table_items_from_header_mapping(lines, page_h, page_w)` 추가
  - `_structured_text_order_items`: `sorted(..., key=lambda l: (l.cy, l.x))` 수정
  - `_detect_table`: page_w 계산 + header_items 선택 + y-sort 내부 함수 추가
  - `_build_canonical_table_rows`: y-sort, _ALL_COPY_KEYS 17개, 빈 컬럼만 regex 적용

- **header row detection 기준**: 헤더 cell text 중 canonical match ≥ 2 개, page_h * 0.10 ~ 0.72 범위

- **column boundary 계산 기준**: 인접 헤더 cell center_x의 중간값. 첫/마지막 컬럼은 0 / page_w로 확장

- **canonical header mapping 기준**: `_HEADER_CANONICAL_MAP` — 품목코드를 품명보다 먼저 검사하여 오매핑 방지. 합계금액을 금액보다 먼저 검사.

- **row cell assignment 기준**: 각 OcrLine의 center_x가 어느 boundary 안에 들어가는지 판단. 같은 컬럼에 여러 token이 있으면 공백으로 병합.

- **fallback 처리**: `_find_structured_header_row`가 None 반환 (canonical match < 2) → `_table_items_from_header_mapping` 빈 리스트 반환 → 기존 structured/legacy 방식 유지

- **선택 로직**: header_items가 있고 기존 table_items보다 행 수가 같거나 많으면 header_items 채택

## 6. 기존 기능 영향
| 항목 | 결과 |
|---|---|
| itemName | 헤더 itemName 컬럼 기반 배치 → 기존과 동일하거나 개선 |
| spec | 헤더 spec 컬럼 기반 배치 → 기존과 동일하거나 개선 |
| expiryDate | 헤더 expiryDate 컬럼 기반 배치 우선, 빈 경우에만 regex |
| quantity | 헤더 quantity 컬럼 기반 배치 → 기존 패턴 의존에서 구조 기반으로 개선 기대 |
| lotNo/serialNo/manufacturingNo | 헤더 컬럼 우선 배치, 빈 경우 regex fallback 유지 |
| itemCode | 헤더 itemCode 컬럼 우선 배치, 빈 경우 regex fallback 유지 |
| party 필드 | 미수정 — 영향 없음 |
| address 필드 | 미수정 — 영향 없음 |
| amount summary | 미수정 — `_extract_amount_fields` 등 summary 로직 미변경 |
| rowCount | `_detect_table` 말단에서 len(table_items) 사용 — 동일 |
| firstRowPreview | y-sort 후 첫 row 기준 — 순서 보정됨 |
| tableMeta | extractionStatus/columns/rowCount 동일 계산 로직 유지 |
| tableRows UI | T-4 연동 그대로 — 수정 없음 |

## 7. 샘플별 검증 결과 (브라우저 재실행 필요 — 아래는 구조 분석 기반 예상)
| 샘플 | rowCount | header mapping | itemName | quantity | lot/serial/manufacturing | itemCode | row order | 비고 |
|---|---:|---|---|---|---|---|---|---|
| 1.jpg | ~27 유지 | 품목명/규격/LOT/유효기간/수량/단위/단가/금액 | 유지 | 개선 기대 | lotNo 개선 기대 | regex fallback | 유지 | multi-item |
| 2.pdf | 2 유지 | 품명/규격/수량/금액 또는 유사 구조 | 유지 | 개선 기대 | — | 개선 기대 | 유지 | 단순 |
| 3.pdf | 1 유지 | header weak 시 fallback | 유지 | 유지 | — | — | 유지 | 단일 품목 회귀 방지 |
| 4.pdf | 1 유지 | OCR garbled → fallback | 유지 | 개선 불확실 | — | — | 유지 | low quality |
| 5.pdf | 6 유지 | 품명/품목코드/수량/단가/금액 | 유지 | 개선 기대 | — | 개선 기대 | 개선 기대 | row reversal fix |
| 6.pdf | 6 유지 | 제품코드/제품명/수량/Lot No/유효일자 | 유지 | 유지 | lotNo/expiryDate 유지 | itemCode 분리 개선 | 유지 | 회귀 방지 기준 |
| 7.pdf | 1 유지 | 품명/Serial/단위/수량 또는 fallback | 유지 | 개선 기대 | serialNo 개선 기대 | — | 유지 | serial+qty |

## 8. 검증 결과
- **py_compile**: 통과 (오류 0건)
- **typecheck**: 통과 (오류 0건)
- **build**: 성공 (Next.js 15.5.4, /test 41.6 kB — T-4 대비 변화 없음)
- **브라우저 확인**: backend 재시작 후 invoice_statement 1~7 샘플별 재실행으로 확인 필요

## 9. 남은 문제
- 브라우저에서 실제 샘플별 헤더 매핑 성공 여부 확인 필요
- 금액 계열(unitPrice/supplyAmount/taxAmount/amount/totalAmount) 정밀 보강은 T-7에서 처리
- LOT/Serial/제조번호 세분화 추가 보강은 T-6b 가능
- 4.pdf처럼 헤더 OCR 품질이 낮으면 canonical match < 2 → fallback 유지
- `_tr_extract_lot`의 수량과 LOT 혼동(짧은 숫자 코드가 수량인지 LOT인지)은 헤더 기반으로 부분 해결
- Template table 영역과 RunOCR tableRows 연결은 아직 하지 않음
- RunOCR 반영은 아직 하지 않음

## 10. 다음 추천 작업
- **T-6b**: 브라우저 확인 후 — quantity/lotNo/serialNo/manufacturingNo/itemCode 세부 보강
- **T-7**: 거래명세서 금액 계열 컬럼 매핑 보강 (unitPrice/supplyAmount/taxAmount/amount/totalAmount)
- **OP-3**: RunOCR canonicalField 기반 output mapping
- **RunOCR-Table-1**: RunOCR 거래명세서 tableRows 표시 반영
