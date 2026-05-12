# T-6e-fix3 required expectedColumns 최종 정렬 결과

## 1. 수정 파일
- `C:\OCR\mysuit-ocr\public\data\testsets\invoice_statement\manifest.json`
- `C:\OCR\mysuit-ocr\src\components\test\TestWorkspace.tsx`

## 2. 백업 파일
- `C:\OCR\mysuit-ocr\backup\invoice_statement_manifest_20260512_before_T6e_fix3_required_expected_columns_final.json`
- `C:\OCR\mysuit-ocr\backup\TestWorkspace_20260512_before_T6e_fix3_required_expected_columns_final.tsx`

## 3. 핵심 요약

1. **manifest.json** — 2.pdf, 3.pdf, 6.pdf, 7.pdf의 `tableExpectedColumns.required` 배열을 사용자 제공 실제 표 컬럼과 일치하도록 수정
2. **TestWorkspace.tsx** — `getManifestExpectedColKeys`의 타입을 `string[]`으로 확장, `CUSTOM_COL_LABELS`, `resolveDisplayColValue` 추가

---

## 4. 수정 전 문제

| 샘플 | 수정 전 required count | 수정 전 required keys | 문제 |
|---|---:|---|---|
| 2.pdf | 6 | itemCode, itemName, quantity, unitPrice, supplyAmount, insuranceCode | rowIndex 없음, 소비자/공급단가 분리 안 됨 |
| 3.pdf | 9 | insuranceCode, itemName, spec, quantity, unitPrice, amount, manufacturer, manufacturingNo, expiryDate | rowIndex 없음, 제조번호/유효기간 복합 1컬럼이 2개로 분리됨 |
| 6.pdf | 5 | itemCode, itemName, quantity, lotNo, expiryDate | rowIndex 없음 |
| 7.pdf | 4 | itemName, serialNo, unit, quantity | "시리얼/로트No." 복합 컬럼이 serialNo만으로 표시됨 |

---

## 5. 샘플별 최종 required expected 컬럼

| 샘플 | expected count | required keys | 표시 label | 결과 |
|---|---:|---|---|---|
| **1.jpg** | **7** | itemName, spec, manufacturingNo, expiryDate, quantity, unitPrice, amount | 품목명, 규격, 제조번호, 유효기간, 수량, 단가, 금액 | ✓ 변경 없음 |
| **2.pdf** | **8** | rowIndex, itemCode, itemName, quantity, consumerUnitPrice, supplyUnitPrice, supplyAmount, insuranceCode | 행, 품목코드, 품목명, 수량, 소비자단가, 공급단가, 공급가액, 보험코드 | ✓ |
| **3.pdf** | **9** | rowIndex, insuranceCode, itemName, spec, quantity, unitPrice, amount, manufacturer, manufacturingExpiry | 행, 보험코드, 품목명, 규격, 수량, 단가, 금액, 제조사, 제조번호/유효기간 | ✓ |
| **4.pdf** | **7** | itemName, lotNo, unit, quantity, unitPrice, supplyAmount, taxAmount | 품목명, LOT/제조번호, 단위, 수량, 단가, 공급가액, 세액 | ✓ 변경 없음 |
| **5.pdf** | **5** | itemName, itemCode, quantity, unitPrice, amount | 품목명, 품목코드, 수량, 단가, 금액 | ✓ 변경 없음 |
| **6.pdf** | **6** | rowIndex, itemCode, itemName, quantity, lotNo, expiryDate | 행, 품목코드, 품목명, 수량, LOT/제조번호, 유효기간 | ✓ |
| **7.pdf** | **4** | itemName, serialLot, unit, quantity | 품목명, 시리얼/로트No., 단위, 수량 | ✓ |

---

## 6. 타입/복합 컬럼 처리

### consumerUnitPrice, supplyUnitPrice (2.pdf)
- 기존 `TableColumnKey`에 없는 display-only key
- manifest `required`에 string으로 저장 (`string[]` 타입이므로 TypeScript 오류 없음)
- `getManifestExpectedColKeys` 타입을 `string[]`으로 확장 → filter 제거
- `CUSTOM_COL_LABELS`: `{ consumerUnitPrice: "소비자단가", supplyUnitPrice: "공급단가" }`
- 셀 값: `resolveDisplayColValue(row, "consumerUnitPrice")` → `row.unitPrice`(임시) 표시

### manufacturingExpiry (3.pdf)
- `"제조번호/유효기간"` 복합 컬럼을 단일 display key로 표현
- `CUSTOM_COL_LABELS`: `{ manufacturingExpiry: "제조번호/유효기간" }`
- `resolveDisplayColValue`: `row.manufacturingNo + " / " + row.expiryDate` (둘 다 있을 경우), 하나만 있으면 그것만

### serialLot (7.pdf)
- `"시리얼/로트No."` 복합 표시 key
- `CUSTOM_COL_LABELS`: `{ serialLot: "시리얼/로트No." }`
- `resolveDisplayColValue`: `row.serialNo || row.lotNo`

### rowIndex (2.pdf, 3.pdf, 6.pdf)
- 기존 `TableColumnKey`에 있는 canonical key
- manifest에 추가 시 `ALL_COL_KEY_SET.has("rowIndex")` = true (이전 코드와 호환)
- label: "행" (TABLE_COLUMN_META.labelKo)

---

## 7. TestWorkspace.tsx 변경 요약

| 변경 항목 | 내용 |
|---|---|
| `getManifestExpectedColKeys` 반환 타입 | `TableColumnKey[]` → `string[]`, ALL_COL_KEY_SET 필터 제거 |
| `CUSTOM_COL_LABELS` 상수 추가 | 4개 커스텀 key의 한국어 라벨 |
| `resolveDisplayColValue` 함수 추가 | composite/custom key 셀 값 해석 |
| `getDisplayTableColumns` 파라미터 | `manifestExpectedColKeys?: string[]` |
| `colLabelMap` | TABLE_COLUMN_META + CUSTOM_COL_LABELS merge |
| 셀 렌더링 | `row[col as keyof]` → `resolveDisplayColValue(row, col)` |
| `manifestMissingRequired` | composite key missing 판정 로직 추가 |

---

## 8. 검증 결과

- **typecheck**: ✓ PASS (오류 없음)
- **build**: ✓ PASS (`/test` 43 kB, 모든 route 빌드 성공)

---

## 9. 다음 작업 판단

**expected count/label/key 7개 샘플 모두 사용자 기준과 일치** (rowIndex 라벨 "행" vs "NO" 차이 제외).

- 브라우저에서 샘플 선택 시 expected 컬럼 버튼 활성화 + 올바른 컬럼 표시 확인 가능
- consumerUnitPrice/supplyUnitPrice 셀 값은 현재 `row.unitPrice`로 임시 표시 (2개가 같은 값) → 실제 2.pdf OCR에서 별도 추출 여부 확인 필요
- manufacturingExpiry 셀 값은 `manufacturingNo / expiryDate` 조합으로 표시
- serialLot 셀 값은 `serialNo || lotNo` 로직으로 표시
- **다음 단계**: RunAll로 실제 값 매핑/rowCount 확인 → T-6g-fix 또는 T-7 금액 계열
