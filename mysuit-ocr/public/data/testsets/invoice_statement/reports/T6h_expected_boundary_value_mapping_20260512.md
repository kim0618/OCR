# T-6h expected boundary/value mapping 보정 결과

## 1. 수정 파일
- `d:/Free_Vue/OCR/ocr-server/extractors/invoice_statement.py`

## 2. 백업 파일
- `d:/Free_Vue/OCR/ocr-server/backup/invoice_statement_20260512_before_T6h_expected_boundary_value_mapping.py`

## 3. 핵심 요약
- **1.jpg `value_mapping_wrong` 제거**: `itemName`, `unitPrice` 값이 이제 모든 행에서 채워짐
- **4.pdf rowCount 개선**: 3 → 4 (y boundary 확장 효과)
- **비표준 key 지원**: `serialLotComposite`, `manufacturingExpiryComposite`, `consumerUnitPrice`, `supplyUnitPrice` 등 row dict에 저장
- **composite display key 자동 생성**: `manufacturingNo+expiryDate` → `manufacturingExpiryComposite`, `serialNo+lotNo` → `serialLotComposite`
- **회귀 없음**: 5.pdf=6, 7.pdf=1 유지

## 4. boundary / assignment 변경 내용

### expected boundary 계산 개선 (`_build_boundaries_from_expected_columns`)
- **`required_keys` 파라미터 추가**: optional 컬럼 중 헤더에서 매칭되지 않은 컬럼은 보간에서 제외
  - 기존 문제: 1.jpg의 optional 6개 컬럼(lotNo, unit, supplyAmount 등)이 보간에 포함되어 필수 컬럼 boundary가 불필요하게 압축됨 (13개 기준으로 폭 계산 → 7개 기준으로 보정)
  - 해결: required 컬럼만 보간 대상 → `half` 값 증가 → 컬럼 폭 정상화
- **첫 번째 컬럼 x_start = table_x_min**: 보간된 첫 컬럼이 항상 테이블 왼쪽 경계부터 시작
  - 기존: x=[294-385] → 1.jpg 품목명이 x<294에 있어 누락
  - 개선: x=[0-385] → 품목명 토큰 포착

### proximity fallback tolerance 확장 (`_assign_canonical_by_x`)
- `avg_col_w * 0.55` → `avg_col_w * 0.70`
- 값 토큰이 헤더 위치와 약간 어긋나도 올바른 컬럼에 배치

### y_max boundary 확장 (`_table_items_with_expected_columns`)
- `page_h * 0.93` → `page_h * 0.96` (expected_columns 경로만)
- 페이지 하단부 데이터 행 캡처 확대 (4.pdf +1 row)
- `_table_items_from_header_mapping`은 0.93 유지 (3.pdf 오인식 방지)

## 5. custom key 처리
| key | 처리 결과 | 비고 |
|---|---|---|
| consumerUnitPrice | row dict 초기화 및 boundary 값 저장 지원 | 2.pdf는 legacy path 사용 중 → 아직 미적용 |
| supplyUnitPrice | row dict 초기화 및 boundary 값 저장 지원 | 2.pdf는 legacy path 사용 중 → 아직 미적용 |

`_table_items_with_expected_columns`에서 `non_canonical_expected_keys` 초기화 → boundary 값이 item dict에 저장됨 → `_build_canonical_table_rows`에서 row로 복사

## 6. composite key 처리
| key | 처리 결과 | 비고 |
|---|---|---|
| manufacturingExpiryComposite | `manufacturingNo + " / " + expiryDate` 자동 생성 | 3.pdf: manufacturingNo/expiryDate 미채워짐 → composite도 미채워짐 |
| serialLotComposite | `serialNo + " / " + lotNo` 자동 생성 | 7.pdf: legacy path로 serialNo/lotNo 미채워짐 → composite도 미채워짐 |
| (1.jpg slc) | lotNo 값 기반으로 자동 생성됨 | 1.jpg에서 `lotNo=24027` → `serialLotComposite=24027` |

composite key는 `_build_canonical_table_rows`에서 성분 필드가 채워진 경우 자동 생성됨.
성분 필드(manufacturingNo, expiryDate, serialNo, lotNo)가 비어 있으면 composite도 비어 있음.

## 7. rowCount 비교
| 샘플 | 목표 | T-6g-fix rowCount | T-6h rowCount | 판정 |
|---|---:|---:|---:|---|
| 1.jpg | 28 | 29 | 29 | 유지 (value mapping 개선이 핵심) |
| 2.pdf | 확인 필요 | 2 | 2 | 변화 없음 |
| 3.pdf | 확인 필요 | 1 | 1 | 유지 |
| 4.pdf | 확인 필요 | 3 | 4 | +1 (y boundary 확장) |
| 5.pdf | 6 | 6 | 6 | ✓ 유지 |
| 6.pdf | 6 | 5 | 5 | 유지 |
| 7.pdf | 1 | 1 | 1 | ✓ 유지 |

## 8. value mapping 비교
| 샘플 | 개선된 컬럼 | 여전히 비어 있는 컬럼 | 잘못 들어간 의심 | 다음 조치 |
|---|---|---|---|---|
| 1.jpg | itemName, unitPrice, amount, lotNo (이제 채워짐) | (주요 컬럼 완료) | - | value_mapping_wrong 제거됨 |
| 2.pdf | - | consumerUnitPrice, supplyUnitPrice, itemCode, quantity, insuranceCode | - | T-6h-2pdf 또는 T-6i |
| 3.pdf | - | manufacturingExpiryComposite (성분 미채워짐) | - | 후속 작업 |
| 5.pdf | - | itemCode, unitPrice, amount | - | 후속 작업 |
| 6.pdf | - | (rowCount 부족) | - | T-6g-fix2 또는 후속 |
| 7.pdf | - | serialLotComposite, unit, quantity | - | 후속 작업 |

## 9. 주요 샘플 상세

### 1.jpg
- **itemName 개선**: 경계값 x_start=0으로 변경 → x<294에 위치한 품목명 토큰 포착
- **unitPrice 개선**: proximity tolerance 0.55→0.70 + required-only 경계 계산으로 avg_col_w 증가 → 근방 토큰 fallback 성공
- **value_mapping_wrong 제거됨** (T-6h 최대 성과)
- **footer row 제거 시도**: 별도 제거 미성공, rowCount=29 유지 (목표 28 대비 +1)
- **남은 문제**: footer row 1개 잔존, serialLotComposite/manufacturingExpiryComposite 표시 개선 여지

### 2.pdf
- **custom key**: expected_columns 경로가 활성화되어야 consumerUnitPrice/supplyUnitPrice 저장 가능
- **rowCount**: 2 유지 — legacy path 사용 중, row grouping 문제 해결 필요
- **남은 문제**: row detection이 fundamental issue → T-6h-2pdf로 분리 필요

### 5.pdf
- **itemCode**: `_tr_extract_item_code` 시도되지만 rawText에 코드 패턴 없음 → 미채워짐
- **unitPrice/amount**: legacy path에서 숫자 추출 로직 한계
- **남은 문제**: expected_columns 경로 활성화 필요 (header score 1, threshold 2 미달)

### 6.pdf
- **rowCount**: 5 유지 (목표 6 대비 -1)
- **lotNo/expiryDate**: 추출된 5개 row에는 채워짐
- **남은 문제**: 1개 row 추가 복구 → T-6g-fix2 또는 T-6i

### 7.pdf
- **serialLotComposite**: legacy path → serialNo/lotNo 미채워짐 → composite 비어 있음
- **unit/quantity**: legacy path(`_text_order_table_fallback`)에서 추출 안 됨
- **남은 문제**: expected_columns 경로 활성화 필요 → 7.pdf 데이터 행이 y>0.93에 있는 것으로 추정

## 10. 검증 결과
- backend py_compile: 통과 ✓
- verify script: 7/7 API 성공, schema 7/7 일치 ✓
- frontend typecheck: 통과 ✓
- frontend build: 통과 ✓

## 11. 다음 작업 판단
**1.jpg value mapping 완료 → 복합 문제(2.pdf rowCount, 7.pdf composite) 별도 처리**

- **1.jpg**: value mapping 핵심 완료. footer row 1개 잔존(29 vs 28). → T-7 금액 계열 검토 가능
- **2.pdf**: rowCount=2 유지. consumerUnitPrice/supplyUnitPrice 구조적 한계. → T-6h-fix-2pdf 또는 Template bounds 연동
- **5.pdf**: rowCount=6 맞지만 itemCode/unitPrice/amount 미채워짐. → header score 개선 필요
- **6.pdf**: rowCount=5 (목표 6 대비 -1). → T-6g-fix2 또는 Template bounds
- **7.pdf**: rowCount=1, composite 미채워짐. → expected_columns 활성화 필요
- **결론**: 주요 value mapping 개선(1.jpg) 완료. 나머지는 T-6h-fix 또는 T-7로 이동 가능.
