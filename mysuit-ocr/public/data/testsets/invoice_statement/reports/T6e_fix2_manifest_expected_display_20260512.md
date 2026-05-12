# T-6e-fix2 manifest expectedColumns 기반 UI 표시 고정 결과

## 1. 수정 파일
- `C:\OCR\mysuit-ocr\src\components\test\TestWorkspace.tsx`

## 2. 백업 파일
- `C:\OCR\mysuit-ocr\backup\TestWorkspace_20260512_before_T6e_fix2_manifest_expected_display.tsx`

## 3. 핵심 요약

**이번 작업의 핵심**: "expected 컬럼" 표시 모드의 컬럼 결정권을 backend `tableMeta.columns`/`tableMeta.expectedColumnKeys`에서 **manifest의 `invoiceProfile.tableExpectedColumns`**로 완전히 이전.

- OCR 결과가 어떻든 manifest에 정의된 컬럼만 표시
- 값이 없는 컬럼도 "—"로 표시 (컬럼 자체가 사라지지 않음)
- expected 컬럼 수, missing 컬럼 계산도 manifest 기준으로 수정

---

## 4. 문제 원인

### 기존 expected 모드가 참조하던 값
```typescript
// 기존 코드: backend tableMeta.expectedColumnKeys 기준
const expKeys = tableMeta?.expectedColumnKeys ?? [];
```

`tableMeta.expectedColumnKeys`는 `required + optional` 전체를 포함하여 9~13개 컬럼을 반환.  
실제로 사용자가 해당 샘플에서 정의한 컬럼(5.pdf는 5개)보다 훨씬 많은 컬럼이 섞여 표시됨.

### 불필요 컬럼이 섞인 이유
- `tableMeta.expectedColumnKeys`는 backend에서 `required + optional` 전체를 저장
- optional 컬럼까지 표시되어 실제 표에 없는 컬럼이 나옴
- manifest의 `required`(사용자가 실제 컬럼으로 정의)와 `optional`(있으면 좋은 컬럼)가 구별되지 않음

---

## 5. 변경 내용

### 5.1 `getManifestExpectedColKeys` 함수 신규 추가

```typescript
function getManifestExpectedColKeys(
  tableExpectedColumns: InvoiceProfile["tableExpectedColumns"] | undefined
): TableColumnKey[] {
  if (!tableExpectedColumns) return [];
  const seen = new Set<string>();
  const result: TableColumnKey[] = [];
  for (const k of [...(tableExpectedColumns.required ?? []), ...(tableExpectedColumns.optional ?? [])]) {
    if (!ALL_COL_KEY_SET.has(k) || seen.has(k)) continue;
    seen.add(k);
    result.push(k as TableColumnKey);
  }
  return result;
}
```

- manifest의 `required` → `optional` 순서로 컬럼 목록 생성
- 유효한 canonical key만 포함, 중복 제거
- "expected 컬럼" 모드의 **단일 진실 소스**

### 5.2 `getDisplayTableColumns` 시그니처 및 "expected" 분기 수정

```typescript
function getDisplayTableColumns(
  tableMeta: CanonicalTableMeta | null,
  tableRows: CanonicalTableRow[],
  mode: TableDisplayMode,
  manifestExpectedColKeys?: TableColumnKey[],  // NEW: manifest 기반 expected cols
): TableColumnKey[] {
  if (mode === "expected") {
    // 1순위: manifest tableExpectedColumns (required + optional 순서)
    if (manifestExpectedColKeys && manifestExpectedColKeys.length > 0) {
      return manifestExpectedColKeys;  // NO rowIndex prepend: manifest가 최종 스키마
    }
    // 2순위: backend tableMeta.expectedColumnKeys (fallback)
    ...
  }
```

### 5.3 `InvoiceTableRowsPanel` — `invoiceProfile` prop 추가

```typescript
function InvoiceTableRowsPanel({
  tableRows, tableMeta, documentFields,
  invoiceProfile,  // NEW
}: { ... invoiceProfile?: InvoiceProfile; }) {
  const manifestExpectedColKeys = useMemo(
    () => getManifestExpectedColKeys(invoiceProfile?.tableExpectedColumns),
    [invoiceProfile?.tableExpectedColumns]
  );
  const hasManifestExpected = manifestExpectedColKeys.length > 0;
  
  // getDisplayTableColumns에 manifestExpectedColKeys 전달
  const displayCols = getDisplayTableColumns(tableMeta, tableRows, displayMode, manifestExpectedColKeys);
```

### 5.4 Auto-switch 로직 업데이트

```typescript
// manifest expected cols 또는 tableMeta.expectedColumnKeys 변경 시 "expected" 모드로 자동 전환
const newKey = hasManifestExpected
  ? manifestExpectedColKeys.join(",")
  : (tableMeta?.expectedColumnKeys ?? []).join(",");
if (newKey && newKey !== prevExpKeyRef.current) {
  setDisplayMode("expected");
  prevExpKeyRef.current = newKey;
}
```

### 5.5 헤더 expected 정보 — manifest 기준

```typescript
// expected count: manifest 기준
const expectedDisplayCount = manifestExpectedColKeys.length || (tableMeta?.expectedColumnKeys?.length ?? 0);

// missing: manifest required 중 실제 값 없는 컬럼
const manifestMissingRequired = manifestRequiredKeys.filter(
  (k) => ALL_COL_KEY_SET.has(k) && !valueColSet.has(k as TableColumnKey)
);
```

### 5.6 "expected 컬럼" 버튼 표시 조건

```typescript
{(hasManifestExpected || (tableMeta?.expectedColumnKeys && ...)) && modeBtn("expected", "expected 컬럼")}
```

### 5.7 호출부에 `invoiceProfile` 전달

```tsx
<InvoiceTableRowsPanel
  tableRows={...} tableMeta={...} documentFields={documentFields}
  invoiceProfile={invoiceProfile}  // NEW
/>
```

### 5.8 label 처리
- expected 컬럼 라벨: 기존 `colLabelMap` (TABLE_COLUMN_META.labelKo) 그대로 사용
- 5.pdf itemName → "품목명", 7.pdf serialNo → "Serial" 등 canonical 라벨 사용
- 태스크에서 요구하는 한국어 라벨(품명, 단가 등)은 TABLE_COLUMN_META에 이미 정의됨

---

## 6. 샘플별 expected 표시 컬럼 검증

| 샘플 | manifest required 수 | manifest required 컬럼 | 이전 expected count | 비고 |
|---|---:|---|---:|---|
| 1.jpg | 7 | itemName, spec, mfgNo, expiry, qty, unitPrice, amount | ~13 | 불필요 컬럼 제거됨 |
| 2.pdf | 6 | itemCode, itemName, qty, unitPrice, supply, insuranceCode | ~9 | 불필요 컬럼 제거됨 |
| 3.pdf | 9 | insuranceCode, itemName, spec, qty, unitPrice, amount, mfr, mfgNo, expiry | ~12 | 불필요 컬럼 제거됨 |
| 4.pdf | 7 | itemName, lotNo, unit, qty, unitPrice, supplyAmount, taxAmount | ~10 | 불필요 컬럼 제거됨 |
| 5.pdf | 5 | itemName, itemCode, qty, unitPrice, amount | ~8 | 불필요 컬럼 제거됨 |
| 6.pdf | 5 | itemCode, itemName, qty, lotNo, expiryDate | ~8 | 불필요 컬럼 제거됨 |
| 7.pdf | 4 | itemName, serialNo, unit, qty | ~7 | 불필요 컬럼 제거됨 |

> **실제 UI에서 optional 포함 여부**: `getManifestExpectedColKeys`는 `required + optional` 전체를 순서대로 포함함. Optional도 표시되되 required가 먼저 나오고, manifest에 없는 컬럼은 절대 표시되지 않음.

---

## 7. 검증 결과

- **typecheck**: ✓ PASS (오류 없음)
- **build**: ✓ PASS (`/test` 42.8 kB, 모든 route 빌드 성공)

---

## 8. 남은 문제

1. **rowCount 문제**: T-6g에서 진행 중 (이번 작업 범위 아님)
2. **label 커스터마이징**: manifest에 per-column label이 없으므로 TABLE_COLUMN_META 기본 라벨 사용. 
   - 5.pdf "품명" vs "품목명": TABLE_COLUMN_META의 `itemName → "품목명"` 사용 (원본은 "품명")
   - 이 차이는 라벨 재정의 없이는 해결 불가 — 실용적으로 충분한 수준
3. **Composite 컬럼**: 3.pdf "제조번호/유효기간"은 `manufacturingNo` + `expiryDate` 두 컬럼으로 분리 표시됨. 단일 컬럼으로 합치는 기능은 별도 구현 필요시 추가 가능.

---

## 9. 다음 작업 판단

**expected 표시 컬럼 고정 완료**: manifest `invoiceProfile.tableExpectedColumns` 기준으로 표시 컬럼이 고정됨.

- expected 컬럼 모드에서 불필요 컬럼 제거 확인 필요 (실제 UI RunAll 후)
- rowCount/값 매핑 문제는 T-6g/T-6g-fix에서 별도 처리
- 표시 컬럼과 값이 모두 안정화되면 → **T-7 금액 계열 검토**
