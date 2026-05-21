# UI-PREVIEW-ROWINDEX-1 — Invoice Table rowIndex Display Policy

작업일: 2026-05-21
작업명: UI-PREVIEW-ROWINDEX-1 invoice table rowIndex display policy

## 1. 사용 도구와 모델

- **도구**: Claude Code
- **모델**: Claude Opus 4.7 (1M context, model ID `claude-opus-4-7[1m]`)
  - 지시문에는 "Sonnet 4.6"으로 기재되어 있었으나 실제 응답 모델은 Opus 4.7 임을 명시.

## 2. 원인

`src/lib/invoiceTableDisplay.ts` 의 `buildInvoicePreviewCols(...)` 가 `hasMeaningfulTableValue(rows, "rowIndex")` 만으로 rowIndex 컬럼을 prepend 했음. invoice_statement parser가 표를 추출하며 행마다 1..N 의 내부 rowIndex 를 채워두면, 그 값이 의미 있다고 판정되어 사용자 표시 컬럼에 노출됨.

`TestWorkspace.tsx` 의 `getDisplayTableColumns(...)` 도 동일 증상으로 "detected" / "expected" / "hasValue" / fallback 모든 분기에서 rowIndex 를 강제 prepend 하거나 ALL_CANONICAL_COLS 의 rowIndex 가 그대로 노출됨.

결과적으로 manifest/template/backend `expectedColumnKeys` 에 rowIndex 가 없는 거래_1/4/5/7 에서도 사용자 표시 컬럼에 rowIndex 가 등장.

## 3. 백업 파일 목록

- `backup/invoiceTableDisplay_20260521_before_UI_PREVIEW_ROWINDEX_1.ts`
- `backup/TestWorkspace_20260521_before_UI_PREVIEW_ROWINDEX_1.tsx`

## 4. 수정 파일 목록

- `src/lib/invoiceTableDisplay.ts`
  - `shouldDisplayRowIndex(...)` helper 신규 추가 (export)
  - `buildInvoicePreviewCols(...)` 시그니처에 `externalExpectedKeys?: readonly string[] | null` 옵셔널 파라미터 추가
  - rowIndex prepend 조건을 `hasMeaningfulTableValue(rows, "rowIndex")` → `shouldDisplayRowIndex(tableMeta, externalExpectedKeys)` 로 교체
- `src/components/test/TestWorkspace.tsx`
  - `shouldDisplayRowIndex` import 추가
  - `getDisplayTableColumns(...)` 의 모든 분기(detected / expected fallback / hasValue / 최종 fallback)에서 rowIndex 강제 prepend 제거
  - `shouldDisplayRowIndex(tableMeta, manifestExpectedColKeys)` 결과로만 rowIndex 포함 여부 결정
  - "all" 모드는 명시적 전체 표시 옵션이므로 정책 적용 대상에서 제외 (그대로 ALL_CANONICAL_COLS 반환)

## 5. 핵심 수정 내용

### 5.1 `shouldDisplayRowIndex` 정책 함수

```ts
export function shouldDisplayRowIndex(
  tableMeta: Record<string, unknown> | null | undefined,
  externalExpectedKeys?: readonly string[] | null,
): boolean {
  // 1) caller가 전달한 expected keys (manifest tableExpectedColumns / template tableColumns)
  if (externalExpectedKeys && externalExpectedKeys.length > 0) {
    for (const k of externalExpectedKeys) {
      if (k === "rowIndex") return true;
    }
  }
  // 2) 백엔드 tableMeta.expectedColumnKeys (실제 컬럼 선언)
  const expKeys = tableMeta?.expectedColumnKeys;
  if (Array.isArray(expKeys)) {
    for (const k of expKeys) {
      if (String(k) === "rowIndex") return true;
    }
  }
  return false;
}
```

### 5.2 `buildInvoicePreviewCols` prepend 조건 교체

기존:

```ts
if (hasMeaningfulTableValue(rows, "rowIndex")) {
  cols = [{ key: "rowIndex", labelKo: resolveLabel("rowIndex") }, ...cols];
}
```

변경:

```ts
if (shouldDisplayRowIndex(tableMeta, externalExpectedKeys)) {
  cols = [{ key: "rowIndex", labelKo: resolveLabel("rowIndex") }, ...cols];
}
```

### 5.3 `getDisplayTableColumns` 정책 통합

모든 분기 진입 직후 `showRowIndex = shouldDisplayRowIndex(tableMeta, manifestExpectedColKeys)` 계산. 각 분기에서:

- "expected" 모드 manifestExpectedColKeys 1순위: 권위 있으므로 그대로 반환 (manifest 가 rowIndex 포함 여부 결정).
- "expected" 모드 backend expectedColumnKeys 2순위: rowIndex 자동 prepend 제거. expectedColumnKeys 가 곧 정답.
- "detected" 모드: tableMeta.columns 에서 rowIndex 제거 후 `showRowIndex` 일 때만 prepend.
- "hasValue" 모드: `showRowIndex` false 면 ALL_CANONICAL_COLS filter 단계에서 rowIndex 제외.
- 최종 fallback: 동일 패턴.

## 6. rowIndex 정책

| 조건 | rowIndex 표시 여부 |
|---|---|
| tableMeta.expectedColumnKeys 에 rowIndex 포함 | 표시 |
| externalExpectedKeys (manifest tableExpectedColumns / template tableColumns) 에 rowIndex 포함 | 표시 |
| tableMeta.columns 에만 rowIndex 존재 | 숨김 (parser 내부 생성 가능성) |
| tableRows 에 rowIndex 값만 채워져 있음 | 숨김 (parser 1..N 자동 생성 가능성) |
| 둘 다 없음 | 숨김 |

`document_fields.tableRows` 원본은 일절 변경하지 않음 — 표시 시점에만 정책 적용.

## 7. 거래_1~거래_7 검증 결과

dry-run 결과(외부 precheck) 기준으로, 본 구현이 정책을 다음과 같이 반영함을 코드 경로 분석으로 확인.

| 템플릿 | rowIndex source | shouldDisplayRowIndex | 표시 결과 |
|---|---|---|---|
| 거래_1 | internal_generated_in_tableMeta_columns | false | 제외 |
| 거래_2 | expected_column | true | 유지 |
| 거래_3 | expected_column | true | 유지 |
| 거래_4 | internal_generated_in_tableMeta_columns | false | 제외 |
| 거래_5 | internal_generated_in_tableMeta_columns | false | 제외 |
| 거래_6 | expected_column | true | 유지 |
| 거래_7 | internal_generated_in_tableMeta_columns | false | 제외 |

### 7.1 columnOrder

| 템플릿 | expected columns (rowIndex 정책 적용 후) | 결과 |
|---|---|---|
| 거래_1 | itemName / spec / manufacturingNo / expiryDate / quantity / unitPrice / amount | PASS |
| 거래_2 | rowIndex / itemCode / itemName / quantity / consumerUnitPrice / supplyUnitPrice / supplyAmount | PASS |
| 거래_3 | rowIndex / itemName / quantity / unitPrice / manufacturer (+insuranceCode/amount extra는 WARN) | PASS (rowIndex 정책 한정), WARN (extra cols) |
| 거래_4 | itemName / lotNo / unit / quantity / unitPrice / supplyAmount / taxAmount / totalAmount | PASS |
| 거래_5 | itemName / itemCode / quantity / unitPrice / amount | PASS |
| 거래_6 | rowIndex / itemCode / itemName / quantity / expiryDate | PASS |
| 거래_7 | itemName / unit / quantity | PASS |

### 7.2 rowCount

| 템플릿 | expected | 결과 |
|---|---|---|
| 거래_1 | 28 | 유지 (display 정책은 행 수에 영향 없음) |
| 거래_2 | 13 | 유지 |
| 거래_3 | 1 | 유지 |
| 거래_4 | 1 | 유지 |
| 거래_5 | 6 | 유지 |
| 거래_6 | 6 | 유지 |
| 거래_7 | 1 | 유지 |

본 작업은 표시 컬럼만 변경하며 tableRows 자체는 건드리지 않으므로 rowCount 는 모든 케이스에서 expected 와 동일.

## 8. Clean JSON / Preview 영향

### 8.1 Preview

- `RunOCR` (`OcrResultPanel`): `buildInvoicePreviewCols(docTableMeta, docTableRows)` 결과로 `docTableDisplayCols` 가 결정됨. 본 helper 가 새 정책을 적용하므로 거래_1/4/5/7 에서 rowIndex 가 Preview 컬럼에서 사라짐.
- `History` (`DetailHistoryView`): 동일 helper 사용 → 동일하게 반영.
- `TestWorkspace`: `getDisplayTableColumns` 가 동일 정책으로 갱신되어 RunOCR Preview 와 일치.

### 8.2 Clean JSON

- `OcrResultPanel` 의 Clean JSON 생성 경로(`cleanTableRowsFromObjects(docTableRows, docTableDisplayCols)`) 가 `docTableDisplayCols` 를 그대로 사용. → 정책 자동 반영.
- 즉 거래_1/4/5/7 의 Clean JSON `tables[0].rows` ordered object 에서 rowIndex 키 제거됨.
- 거래_2/3/6 의 Clean JSON 에서는 rowIndex 가 그대로 첫 키로 유지됨.

### 8.3 Custom / Validation

- Custom/Validation 패널이 `docTableDisplayCols` 또는 `getDisplayTableColumns` 결과를 공유하므로 동일하게 정책이 적용됨.

## 9. 기준선 유지 확인

- OCR/parser/backend 추출 로직 미수정.
  - `ocr-server/main.py`, `ocr-server/extractors/invoice_statement.py`, `ocr-server/preprocess.py`, `ocr-server/preprocessing_policy.py` 변경 없음.
- `templates.json`, `manifest.json`, GT 변경 없음.
- `History`/`Restore` 저장 구조 변경 없음.
- 거래명세서 외 문서 타입 영향 없음 (수정 대상 helper 는 invoice_statement 전용 경로).
- `document_fields.tableRows` 원본 데이터 변경 없음 — 표시 시점 정책만 적용.

## 10. typecheck / build 결과

- `npm run typecheck` — PASS (에러 없음)
- `npm run build` — PASS
  - 18개 페이지 모두 정상 생성
  - `/runocr` 65.3 kB / `/test` 47.2 kB / `/history` 9.08 kB
  - 사전 존재 ESLint 워닝 `nextVitals is not iterable` 는 본 작업 변경과 무관

## 11. 남은 이슈

### 11.1 거래_3 insuranceCode / amount extra 컬럼

거래_3 의 backend `tableMeta.expectedColumnKeys` 또는 manifest 에 extra 로 등장하는 `insuranceCode`, `amount` 컬럼은 본 작업 범위 밖. rowIndex 정책 한정으로는 PASS 이나, 컬럼 순서 검증에서 unexpected 컬럼으로 잡힐 수 있음. 별도 이슈로 트래킹 필요.

### 11.2 외부 expected keys 전파

`OcrResultPanel` 과 `DetailHistoryView` 는 `buildInvoicePreviewCols` 호출 시 `externalExpectedKeys` 를 전달하지 않음. 현재는 백엔드 `tableMeta.expectedColumnKeys` 만으로 7개 케이스가 모두 분류 가능하므로 영향 없음. 다만 manifest 만 가지고 백엔드 expectedColumnKeys 가 비어있는 케이스가 추후 등장하면 caller 가 manifest 키를 전달하도록 확장 필요.

### 11.3 "all" 모드

TestWorkspace `getDisplayTableColumns` 의 "all" 모드는 정책 미적용 (의도적). 사용자가 명시적으로 전체 canonical 컬럼을 보겠다는 선택이므로 rowIndex 가 그대로 노출됨. UX 정책 차원에서 추후 검토 가능.

## 12. 다음 작업 제안

1. **거래_3 insuranceCode / amount extra 컬럼 정리** — manifest expected 와 backend extract 결과 정합성 확인. parser 또는 manifest 측 조정 필요 여부 판단.
2. **`externalExpectedKeys` caller 확장** — `OcrResultPanel`, `DetailHistoryView` 에서 manifest tableExpectedColumns 또는 template tableColumns 를 `buildInvoicePreviewCols` 에 전달하여 백엔드 `expectedColumnKeys` 가 비어있는 케이스에도 robust 하게.
3. **거래_1 lotNo / serialNo dedup 정책 재확인** — 본 작업 범위 외이지만, hasValue mode 의 rowIndex 정책 적용으로 dedup 순서가 자연스럽게 정리되었는지 후속 검증.
4. **manifest displayLabelMap 활용** — 백엔드 `columnLabels` 가 빈 상태에서 manifest 의 `display[].label` 을 prefer label 로 활용하는 경로 확장 (현재 TestWorkspace 만 부분 활용).
