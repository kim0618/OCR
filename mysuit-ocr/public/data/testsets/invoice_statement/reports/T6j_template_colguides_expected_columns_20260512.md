# T-6j Template colGuides 기반 expectedColumns 추출 결과

## 1. 수정 파일
- `d:/Free_Vue/OCR/ocr-server/main.py`
- `d:/Free_Vue/OCR/ocr-server/extractors/invoice_statement.py`

## 2. 백업 파일
- `d:/Free_Vue/OCR/ocr-server/backup/main_20260512_before_T6j_colguides.py`
- `d:/Free_Vue/OCR/ocr-server/backup/invoice_statement_20260512_before_T6j_colguides.py`

## 3. 핵심 요약
- **colGuides 경로 구현 완료**: Header OCR 없이 template column guide로 boundary 직접 생성
- **`columnGuides` Form 파라미터 추가**: 직접 테스트 및 production 연결 가능
- **회귀 없음**: 기존 샘플 결과 전부 유지 (verify script 7/7 성공)
- **5.pdf/2.pdf**: 표준 경로(tableBounds 미제공)는 변화 없음. 올바른 template 좌표 필요.

## 4. colGuides 구조 조사
- **region.table.colGuides**: `number[]` — 정규화(0-1) 세로 분할선 위치
- **region.table.colX**: `number[]` — 절대 픽셀 좌표 (export.ts에서 `anchor.x + anchor.width * guide`로 계산)
- **guide 좌표 타입**: colX = 이미지(img) space 절대 픽셀
- **img space → OCR space 변환**: `ocr_x = col_x_img * (ocr_w / orig_w)` (단순 scale 근사)
- **사용 방식**: N개 colX → N+1개 column region (divider line 방식)

## 5. main.py 전달 구조

### T-6j 추가: columnGuides Form 파라미터
```python
columnGuides: str = Form("")  # T-6j: Template column guide x-positions (OCR space)
```
- JSON 배열로 수신 (OCR space 절대 x 좌표 목록)
- `_tcg: list[float]` 로 파싱 후 `extract_invoice_statement_fields(column_guides=_tcg)` 전달

### T-6i 연장: regions에서 colX 자동 유도
```python
_col_x_img = (_r.get("table") or {}).get("colX", [])
_tcg = [min(float(ocr_w), max(0.0, float(cx) * _sx)) for cx in _col_x_img]
```
- Template region 자동 처리 시 colX → OCR space 변환

## 6. invoice_statement.py 적용 내용

### 새 함수: `_build_boundaries_from_column_guides`
- `required_keys`: expectedColumns.required 순서 기준
- `column_guides_ocr`: OCR space 절대 x 좌표 목록 (divider line)
- `table_bounds`: xMin/xMax 경계 (첫/끝 컬럼 범위)
- 가이드 수 mismatch 시 자동 보정 (분할/보간)
- `source: "template_colguide"`

### 새 함수: `_extract_items_using_boundaries`
- header row 탐지 없이 table_bounds 내 모든 row 대상
- `_is_table_header_row`, `_is_business_contact_line`, `_is_summary_row_for_items` 필터
- column assignment, date validation, validity check 포함
- `source: "template_colguides_expected_columns"`

### `_table_items_with_expected_columns` 수정
- `column_guides` 파라미터 추가
- colGuides 분기: `if column_guides and table_bounds and len(column_guides) > 0`
  - `_build_boundaries_from_column_guides` 호출
  - `_extract_items_using_boundaries` 호출
  - 결과 있으면 즉시 반환 (header detection 생략)
  - 결과 없으면 기존 header detection 경로로 fallback

### `_detect_table` / `extract_invoice_statement_fields` 수정
- `column_guides: list[float] | None = None` 파라미터 추가

### extractionSource 추가
- `"template_colguides_expected_columns"` → 이제 올바르게 표시됨

## 7. 검증 결과
- main.py py_compile: 통과 ✓
- invoice_statement.py py_compile: 통과 ✓
- verify script: 7/7 성공, 기존 결과 유지 ✓
- typecheck: 통과 ✓
- build: 통과 ✓

## 8. 샘플별 결과
| 샘플 | columnGuidesUsed | extractionSource | rowCount | 비고 |
|---|---|---|---:|---|
| 1.jpg | N | expected_columns_header_match | 29 | 기존 유지 ✓ |
| 2.pdf | N | legacy_text_items | 2 | 기존 유지 ✓ |
| 5.pdf | N | legacy_text_items | 6 | 기존 유지 ✓ |
| 6.pdf | N | expected_columns_header_match | 5 | 기존 유지 ✓ |
| 7.pdf | N | expected_columns_header_match | 1 | 기존 유지 ✓ |

표준 경로(columnGuides 미제공)에서는 변화 없음.

## 9. colGuides 테스트 결과 (임의 좌표 주입)
테스트 조건: 5.pdf에 근사 column dividers [190, 350, 490, 650] 주입

결과:
- `colGuidesReceived=True`
- `columnGuideMode="boundary_lines"` (4 guides for 5 columns = perfect match)
- `extractionSource="template_colguides_expected_columns"` (수정 후)
- `rowCount=4` (6 중 4개만 경계에 걸림 — 임의 좌표 근사치 때문)

한계: 테스트용 임의 좌표가 실제 5.pdf 컬럼 위치와 불일치 → 4개만 추출. 실제 template 좌표를 사용해야 함.

## 10. 한계 및 후속

### colGuides 있어도 OCR garble인 경우
- expected_columns header detection은 여전히 OCR에 의존
- colGuides 경로는 header OCR 없이 작동 ✓ (T-6j 핵심 목표 달성)

### 실제 Template 연동 필요
- Frontend RunOCR/Template에서 colX를 `columnGuides` Form param으로 전송하는 연결 필요
- 또는 regions JSON을 통한 자동 유도 (T-6i에서 구현됨)

### rowTemplate 기반 행 분리
- 현재: bounds 내 모든 row를 탐색
- 향후: rowTemplate.height 기반 행 범위 추정 가능 (T-6k)

## 11. 다음 작업 판단
- **colGuides 경로 구현 완료** → Template/RunOCR 실제 연동
- **5.pdf/2.pdf 근본 해결**: 올바른 template 좌표 제공 시 colGuides 경로로 개선 가능
- **1.jpg value mapping 완료, 7.pdf composite 완료** → **T-7 금액 계열 검토 가능**
- colGuides 기반 정확도 검증은 실제 template annotation 후 후속 작업
