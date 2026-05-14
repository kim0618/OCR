# T-6k 거래명세서 샘플별 실제 표 컬럼명 display schema 고정 결과

## 1. 수정 파일
- `d:/Free_Vue/OCR/mysuit-ocr/public/data/testsets/invoice_statement/manifest.json`
- `d:/Free_Vue/OCR/mysuit-ocr/src/lib/testsets.ts`
- `d:/Free_Vue/OCR/mysuit-ocr/src/components/test/TestWorkspace.tsx`

## 2. 백업 파일
- `d:/Free_Vue/OCR/mysuit-ocr/backup/invoice_statement_manifest_20260513_before_T6k_display_schema.json`
- `d:/Free_Vue/OCR/mysuit-ocr/backup/testsets_20260513_before_T6k_display_schema.ts`
- `d:/Free_Vue/OCR/mysuit-ocr/backup/TestWorkspace_20260513_before_T6k_display_schema.tsx`

## 3. 핵심 요약
- manifest에 `tableExpectedColumns.display[]` 배열 추가 — 샘플별 실제 문서 표 헤더명 고정
- `InvoiceTableExpectedDisplayColumn` 타입 추가 (testsets.ts)
- expected 모드에서 display 배열을 최우선 사용 (TestWorkspace.tsx)
- `colLabelMap`에 manifest display labels를 최우선 merge
- composite key (`manufacturingExpiryComposite`, `serialLotComposite`) 지원 강화
- missing 표시를 `라벨(key)` 형식으로 개선

## 4. 기존 문제
- canonical key 공통 라벨 때문에 실제 문서 컬럼명과 UI 표시명이 달랐음
  - 예: 1.jpg "품목" → UI "품목명" (TABLE_COLUMN_META 라벨)
  - 예: 2.pdf "보험No" → UI "보험코드" (canonical 라벨)
- expected 표가 검증자가 보는 실제 문서 헤더 기준이 아니라 내부 key 라벨 기준으로 보였음

## 5. 샘플별 display schema
| 샘플 | 목표 count | 실제 count | key 순서 일치 | 표시 컬럼 |
|---|---:|---:|---|---|
| 1.jpg | 7 | 7 | ✓ | 품목·규격·제조번호·유효기간·수량·단가·금액 |
| 2.pdf | 8 | 8 | ✓ | NO·품목코드·품목명·수량·소비자단가·공급단가·공급금액·보험No |
| 3.pdf | 9 | 9 | ✓ | 순번·보험코드·품명·규격·수량·단가·금액·제조회사·제조번호/유효기간 |
| 4.pdf | 7 | 7 | ✓ | 품목명·LotNo.·단위·수량·단가·공급가액·세액 |
| 5.pdf | 5 | 5 | ✓ | 품명·품목코드·수량·단가·금액 |
| 6.pdf | 6 | 6 | ✓ | NO·제품코드·제품명·수량·LotNo·유효일자 |
| 7.pdf | 4 | 4 | ✓ | 품명·시리얼/로트No.·단위·수량 |

## 6. 코드 경로

### manifest display schema
- `tableExpectedColumns.display?: InvoiceTableExpectedDisplayColumn[]`
- 순서: required와 동일, label이 실제 문서 헤더명

### InvoiceProfile type (testsets.ts)
- `InvoiceTableExpectedDisplayColumn` interface 추가 (`key: string`, `label: string`)
- `tableExpectedColumns.display?: InvoiceTableExpectedDisplayColumn[]` 추가

### TestWorkspace.tsx expected mode
- `getManifestExpectedColKeys()`: display 배열 있으면 display.key[] 우선, 없으면 required[] fallback
- `getManifestDisplayLabelMap()`: display 배열에서 key→label 맵 추출 (신규 함수)
- `colLabelMap`: canonical → CUSTOM_COL_LABELS → manifestDisplayLabelMap (우선순위)
- `manifestMissingRequired`: `manufacturingExpiryComposite`, `serialLotComposite` 판정 추가
- missing 표시: `라벨(key)` 형식으로 개선

### resolveDisplayColValue
- `manufacturingExpiryComposite`: backend 직접 값 → 성분 조합 순서로 표시
- `serialLotComposite`: backend 직접 값 → serialNo||lotNo 순서
- `consumerUnitPrice`/`supplyUnitPrice`: backend 직접 값 → unitPrice fallback

### CUSTOM_COL_LABELS
- `manufacturingExpiryComposite: "제조번호/유효기간"` 추가
- `serialLotComposite: "시리얼/로트No."` 추가

## 7. 정적 검증 결과
| 샘플 | display 존재 | count 일치 | 순서 일치 | key 일치 | 판정 |
|---|---|---|---|---|---|
| 1.jpg | ✓ | 7/7 ✓ | ✓ | ✓ | OK |
| 2.pdf | ✓ | 8/8 ✓ | ✓ | ✓ | OK |
| 3.pdf | ✓ | 9/9 ✓ | ✓ | ✓ | OK |
| 4.pdf | ✓ | 7/7 ✓ | ✓ | ✓ | OK |
| 5.pdf | ✓ | 5/5 ✓ | ✓ | ✓ | OK |
| 6.pdf | ✓ | 6/6 ✓ | ✓ | ✓ | OK |
| 7.pdf | ✓ | 4/4 ✓ | ✓ | ✓ | OK |

## 8. 검증 명령 결과
- `npm.cmd run typecheck`: 통과 ✓
- `npm.cmd run build`: 통과 ✓

## 9. 남은 문제
- 이번 작업은 표시 컬럼명 고정 작업이다. backend 미수정.
- rowCount/value mapping 문제는 별도 후속 작업에서 진행한다.
- Template colGuides 실제 좌표 정확도 검증은 후속 작업이다.
- 2.pdf, 5.pdf의 value mapping 부족 (expected 표에는 올바른 컬럼명이 보이지만 값이 비어 있는 경우)은 T-7 또는 T-6h-fix-2pdf에서 처리 예정.
