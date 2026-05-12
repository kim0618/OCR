# T-6a Test 표 추출 결과 동적 컬럼 표시 결과

## 1. 수정 파일
- `src/components/test/TestWorkspace.tsx`

## 2. 백업 파일
- `backup/TestWorkspace_20260512_before_T6a_dynamic_table_columns.tsx`

## 3. 핵심 요약
- 기존: 모든 invoice_statement 샘플에서 고정 primary 15개 + secondary 3개 컬럼을 동일하게 표시
- 변경: `tableMeta.columns`(T-6 backend에서 실제 감지된 컬럼 목록) 기준으로 기본 표시 컬럼을 동적 결정
- 표시 모드 3개 추가: **실제 감지 컬럼** / **값 있는 컬럼** / **전체 canonical 18개**
- `getDisplayTableColumns(tableMeta, tableRows, mode)` helper 함수 신규 추가
- `TableDisplayMode` 타입 추가 (`"detected" | "all" | "hasValue"`)
- `ALL_CANONICAL_COLS` 상수 추가 (18개 전체 순서 정의)
- 기존 `INVOICE_TABLE_PRIMARY_COLS` / `INVOICE_TABLE_SECONDARY_COLS` / `showSecondary` 상태 제거
- 전체 canonical 18개 표시 모드에서 canonical key를 컬럼 헤더 아래 작게 보조 표시
- raw tableMeta/tableRows JSON 버튼 유지

## 4. 동적 컬럼 표시 결과

### 표시 컬럼 결정 로직
- **tableMeta.columns 사용** (mode=detected, T-6 backend 감지 컬럼):
  - `tableMeta.columns`가 있으면 canonical key 필터 후 그 순서 그대로 사용
  - `rowIndex`는 항상 첫 번째에 배치 (없으면 자동 추가)
  - 결과: 문서마다 다른 컬럼 목록이 기본 표시됨
- **actualColumns 사용** (mode=detected, tableMeta.columns 없을 때):
  - `tableRows`에서 값이 있는 컬럼을 ALL_CANONICAL_COLS 순서로 필터
  - 완전 fallback: `["rowIndex", "itemName", "quantity"]`
- **값 있는 컬럼** (mode=hasValue):
  - `tableRows.some(row => row[col] != null && row[col] !== "")` 기준
- **전체 canonical** (mode=all):
  - `ALL_CANONICAL_COLS` 18개 전부 표시, canonical key 보조 표시

### UI 변경
- **표시 모드 토글**: 표 위에 3개 버튼 [실제 감지 컬럼] [값 있는 컬럼] [전체 canonical 18개]
  - 활성 모드는 파란 테두리와 반투명 배경으로 강조
  - 현재 표시 컬럼 수 실시간 표시 ("N개 표시")
- **전체 canonical 모드**: 컬럼 헤더 아래에 canonical key를 7px 폰트로 작게 보조 표시
- **기존 보조 컬럼 버튼 제거**: `showSecondary` → 표시 모드로 통합
- **raw 보기 버튼 유지**: "원본 tableMeta 보기" / "원본 tableRows JSON 보기"
- 헤더 요약: "감지 컬럼 N개" 표시 (기존 "컬럼 N개"에서 명확화)

## 5. 샘플별 확인 (브라우저 재실행 필요 — T-6 backend 재시작 후)
| 샘플 | 기본 표시 컬럼 (예상) | 전체 canonical 보기 | 비고 |
|---|---|---|---|
| 1.jpg | rowIndex + tableMeta.columns 기준 (품목명/규격/LOT/유효기간/수량/단위/단가/금액 등) | 18개 전체 | header mapping 성공 시 |
| 2.pdf | rowIndex + tableMeta.columns 기준 | 18개 전체 | |
| 3.pdf | fallback → 값 있는 컬럼 | 18개 전체 | header weak |
| 4.pdf | fallback → 값 있는 컬럼 | 18개 전체 | OCR garbled |
| 5.pdf | rowIndex + tableMeta.columns 기준 (품목명/품목코드/수량/단가/금액) | 18개 전체 | |
| 6.pdf | rowIndex + tableMeta.columns 기준 (제품코드/제품명/수량/Lot No/유효일자) | 18개 전체 | 회귀 방지 기준 |
| 7.pdf | rowIndex + tableMeta.columns 기준 (품명/Serial/단위/수량) | 18개 전체 | |

## 6. 기존 기능 영향
| 항목 | 결과 |
|---|---|
| Test 탭 진입 | 유지 — 영향 없음 |
| invoice_statement 결과 | 동적 컬럼으로 개선 표시 |
| party/address/amount 판정 | 유지 — DocumentFieldCard 등 미수정 |
| TableRowsValidationPanel | 유지 — 미수정 |
| raw tableMeta 보기 | 유지 — 버튼 유지 |
| raw tableRows 보기 | 유지 — 버튼 유지 |
| 영수증 테스트셋 | 유지 — invoice_statement 전용 패널 조건부 표시 |

## 7. 검증 결과
- **typecheck**: 통과 (오류 0건)
- **build**: 성공 (`/test` 41.9 kB — T-6a 코드 반영)
- **브라우저 확인**: backend(T-6) 재시작 후 샘플별 재실행으로 확인 필요

## 8. 남은 문제
- backend `tableMeta.columns`에 실제 OCR 헤더명이 포함되지 않으므로 "제품코드(itemCode)" 형태 표시는 canonical label만 가능 (T-6에서 sourceHeader 추가 시 개선 가능)
- T-6 header mapping이 partial인 문서는 `tableMeta.columns`가 적어 detected 모드에서 컬럼 수 적을 수 있음 → "값 있는 컬럼" 모드로 보완 가능
- 금액 계열 매핑은 후속 T-7 대상
- 수량/LOT/Serial 세부 보강은 후속 T-6b 대상
- RunOCR/Template tableRows 연결 미완료

## 9. 다음 추천 작업
- **T-6b**: 브라우저 확인 후 — quantity/lotNo/serialNo/manufacturingNo/itemCode 세부 보강
- **T-7**: 거래명세서 금액 계열 컬럼 매핑 보강
- **RunOCR-Table-1**: RunOCR 거래명세서 tableRows 표시 반영
