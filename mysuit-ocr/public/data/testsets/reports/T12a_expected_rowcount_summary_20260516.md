# T-12a expectedRowCount metadata 및 rowCount exact summary 결과

## 1. 수정 파일

| 파일 | 변경 내용 |
|---|---|
| `mysuit-ocr/src/lib/testsets.ts` | `InvoiceProfile`에 `expectedRowCount?: number` 추가 |
| `mysuit-ocr/public/data/testsets/invoice_statement/manifest.json` | 7개 아이템 `invoiceProfile`에 `expectedRowCount` 추가 |
| `mysuit-ocr/src/components/test/TestWorkspace.tsx` | `DocTypeSummaryRow` 4개 필드 추가, `docTypeSummary` 집계 로직, sub-table 컬럼, `InvoiceTableRowsPanel` 배지 |

## 2. 핵심 요약

- `InvoiceProfile.expectedRowCount` 타입 추가 → manifest에서 명시적 기대 행 수 관리
- 7개 샘플 모두 expectedRowCount 설정 (1.jpg: 28, 2.pdf: 13, 나머지: 1/6/6/1)
- documentType 집계 표에 **exact / short / over** 컬럼 추가
- `InvoiceTableRowsPanel` 헤더에 "행 수: N / 기대 M · 정상/부족/초과" 배지 추가
- typecheck ✓ / build ✓ (44.1 kB)

## 3. manifest expectedRowCount 추가

| 샘플 | expectedRowCount | 근거 |
|---|---:|---|
| 1.jpg | 28 | T-10 E2E exact 확인값 |
| 2.pdf | 13 | T-10 E2E exact 확인값 |
| 3.pdf | 1 | T-10 E2E exact 확인값 |
| 4.pdf | 1 | T-10 E2E exact 확인값 |
| 5.pdf | 6 | T-10 E2E exact 확인값 |
| 6.pdf | 6 | T-10-fix-header-skip 후 E2E exact 확인값 |
| 7.pdf | 1 | T-10 E2E exact 확인값 |

## 4. UI summary 변경

### DocTypeSummaryRow 신규 필드

```typescript
rowExactCount: number;   // actualRowCount === expectedRowCount
rowShortCount: number;   // actualRowCount < expectedRowCount
rowOverCount: number;    // actualRowCount > expectedRowCount
rowUnknownCount: number; // expectedRowCount 없음
```

### 거래명세서 sub-table 컬럼 변경

| 이전 | 이후 |
|---|---|
| rows有 / warn | rows有 / **exact** / **short** / **over** / warn |

- exact (녹색): actualRowCount === expectedRowCount
- short (황색): actualRowCount < expectedRowCount  
- over (적색): actualRowCount > expectedRowCount

### 집계 로직 (docTypeSummary useMemo, document profile)

```typescript
const expectedRowCount = manifestItem?.invoiceProfile?.expectedRowCount;
const actualRowCount = tMeta?.rowCount ?? Number(docFields?.rowCount ?? 0);
if (expectedRowCount != null) {
  if (actualRowCount === expectedRowCount) row.rowExactCount++;
  else if (actualRowCount < expectedRowCount) row.rowShortCount++;
  else row.rowOverCount++;
} else {
  row.rowUnknownCount++;
}
```

## 5. 상세 표시 변경 (InvoiceTableRowsPanel)

"행 수: N" → "행 수: **N** / 기대 M · **정상**" (exact)  
또는 "행 수: **N** / 기대 M · **부족**" (short)  
또는 "행 수: **N** / 기대 M · **초과**" (over)

상태별 색상:
- 정상: `#22c55e` (녹색)
- 부족: `#f59e0b` (황색)
- 초과: `#ef4444` (적색)
- 기대값 없음: 기존 "행 수: N" 만 표시

## 6. 검증 결과

- typecheck: **passed** (0 errors)
- build: **passed** (/test 44.1 kB)
- OCR 로직 미수정 → 기존 T-10/T-11 결과 회귀 없음

## 7. 다음 작업 판단

**rowCount exact summary 완료 → field-level missing/warning summary로 이동**

현재 invoice_statement 집계 표에서 볼 수 있는 것:
- selected / suppressed / not_run / 선택률
- 필드별 채움 수 (supplierCompany, buyerCompany, rowCount, ...)
- rows有 (tableRows 반환 샘플 수)
- exact / short / over (rowCount 정확도)
- warn (valueMappingWarnings 있는 샘플 수)

후속 후보:
1. `expectedMissingKeys` / `valueMappingWarnings` 상세 필드별 집계
2. `expectedValueFillRate` avg 집계 표시
3. tax_invoice / transaction_statement 샘플 추가 및 parser 분기
