# CLEAN JSON CONTRACT 20260521

## 1. 사용 도구와 모델
- 사용 도구: Codex
- 사용 모델: Codex
- 작업명: `CODEX_CLEAN_JSON_CONTRACT_PRECHECK_NO_PROD_MODIFY`
- 생성 시각: `2026-05-21T13:47:56`

## 2. 운영 코드 수정 없음 확인
- 이번 작업은 문서화/계약 정의 전용이다.
- 운영 frontend/backend/templates/manifest/GT는 수정하지 않았다.
- 생성 파일은 이 스크립트와 docs 리포트만이다.
- repo dirty 상태: `DIRTY`
- dirty entries:
```text
?? docs/CLEAN_JSON_CONTRACT_20260521.json
?? docs/CLEAN_JSON_CONTRACT_20260521.md
?? tmp/
```

## 3. 확인한 소스
- `src/components/upload/OcrResultPanel.tsx`
- `src/lib/invoiceTableDisplay.ts`
- `src/components/history/DetailHistoryView.tsx`
- `src/components/test/TestWorkspace.tsx`

핵심 위치:
- Clean JSON 생성: `OcrResultPanel.tsx:854`
- `toCleanJson`: `OcrResultPanel.tsx:888`
- `shouldDisplayRowIndex`: `invoiceTableDisplay.ts:128`
- `buildInvoicePreviewCols`: `invoiceTableDisplay.ts:204`
- TestWorkspace `getDisplayTableColumns`: `TestWorkspace.tsx:4623`

## 4. 현재 Clean JSON 생성 흐름
1. `document_fields.tableRows`를 `docTableRows`로 읽는다.
2. `document_fields.tableMeta`를 `docTableMeta`로 읽는다.
3. `docTableDisplayCols = buildInvoicePreviewCols(docTableMeta, docTableRows)`로 Preview 표시 컬럼을 만든다.
4. `field_type === "field"`는 `info` 항목이 된다.
5. `field_type === "table"`은 `tables` 항목이 된다.
6. 구조화 거래명세서 rows는 `docTableDisplayCols` 순서로 ordered object를 만든다.
7. fallback은 `field.tableRows` -> `field.table_data` -> `JSON.parse(field.value)` 순서다.
8. Copy/Export는 현재 Markdown/Clean JSON 모드에 따라 문자열을 내보낸다.

## 5. Clean JSON v1 Contract
현재 운영 출력은 다음 top-level 구조를 유지한다.

```ts
type CleanJsonV1Payload = {
  templateName: string;
  info?: Array<{ key: string; label: string; value: string }>;
  tables?: Array<{ key: string; label: string; rows: Array<Record<string, string>> }>;
};
```

- `templateName`: 항상 존재한다. 현재 코드는 `templateName ?? ""`를 사용하며 `documentType/doc_type`으로 대체하지 않는다.
- `info`: `field_type === "field"` 항목에서 만든다. `key=f.name`, `label=f.ko || f.label || f.name`, `value=f.value ?? ""`.
- `tables`: `field_type === "table"` 항목에서 만든다. `key=f.name`, `label=f.ko || f.label || f.name`, `rows`를 가진다.
- v1 tables는 사용자 출력에 별도 `columns` 배열을 넣지 않는다.
- `confidence`, `bbox`, `source`, `original`, OCR debug/timing/raw image 계열 값은 Clean JSON의 사용자용 구조에 포함하지 않는다.

## 6. Rows / Column Order Contract
- `rows`는 배열이다.
- 각 row는 표시 컬럼 순서 기반 ordered object다.
- 구조화 거래명세서에서는 `Object.keys(row)` 원본 순서에 의존하지 않는다.
- Clean JSON rows key order는 Preview `docTableDisplayCols` 순서와 같아야 한다.
- Preview에서 숨긴 내부 컬럼은 Clean JSON에서도 숨겨야 한다.
- Preview에서 표시한 실제 컬럼은 Clean JSON에서도 표시해야 한다.

## 7. rowIndex Contract
- rowIndex는 무조건 숨기지 않는다.
- 실제 expected 컬럼이면 Clean JSON rows에 포함한다.
- 내부 생성 행번호이면 Clean JSON rows에서 제외한다.
- 표시 근거는 `externalExpectedKeys` 또는 `tableMeta.expectedColumnKeys`의 `rowIndex`다.
- `tableMeta.columns`에만 있는 `rowIndex`는 단독 표시 근거가 아니다.
- rows 안의 `rowIndex` 값만으로 표시하지 않는다.
- `document_fields.tableRows` 원본은 변경하지 않는다.
- Clean JSON builder는 display columns를 신뢰해야 하며, `Object.keys(row)`로 `rowIndex`를 되살리면 안 된다.

현재 거래명세서 기준:
- rowIndex 제외: 거래_1, 거래_4, 거래_5, 거래_7
- rowIndex 유지: 거래_2, 거래_3, 거래_6
- 거래_3 `insuranceCode`/`amount` extra는 rowIndex와 별도 이슈다.

## 8. Preview / Custom / Validation / History / TestWorkspace
- Preview: `docTableDisplayCols`를 사용한다.
- Clean JSON: 같은 `docTableDisplayCols`로 row object를 만든다.
- Custom/Validation: 구조화 tableRows가 있으면 `docTableDisplayCols` 경로를 사용한다.
- History: `DetailHistoryView`가 `buildInvoicePreviewCols(tableMeta, tableRows)`를 사용한다.
- TestWorkspace: 별도 `getDisplayTableColumns` 경로가 있으나 `shouldDisplayRowIndex`를 사용한다. `all` 모드는 의도적으로 정책 미적용이다.

## 9. Clean JSON v2 확장 방향
FRONTEND-CLEANUP-1에서는 v1 출력 구조를 바꾸지 않는다.

장기 방향:
- top-level key는 `templateName`, `info`, `tables` 중심으로 유지한다.
- `info2`, `info3`, `table2` 같은 top-level key는 만들지 않는다.
- 여러 영역은 `info` 배열의 여러 item으로 표현한다.
- 여러 테이블은 `tables` 배열의 여러 item으로 표현한다.
- 향후 v2의 `info` item은 `key`, `label`, `fields`를 가진 section이 될 수 있다.
- v1 field-array info를 v2 section-array info로 바꾸는 작업은 별도 마이그레이션이다.

## 10. Helper 분리 계약 초안
추천 helper 이름: `buildCleanJsonResult`

입력 후보:
```ts
type BuildCleanJsonInput = {
  templateName?: string | null;
  fields: OcrField[];
  documentFields?: Record<string, unknown> | null;
  docTableRows?: Record<string, unknown>[] | null;
  docTableDisplayCols?: Array<{ key: string }> | null;
  tableMeta?: Record<string, unknown> | null;
};
```

출력 후보:
```ts
type CleanJsonV1Payload = {
  templateName: string;
  info?: CleanInfoItem[];
  tables?: CleanTableItem[];
};
```

책임:
- Clean JSON v1만 생성한다.
- field/table 값을 현재와 동일하게 정규화한다.
- 구조화 tableRows는 입력받은 display columns 순서를 따른다.
- legacy fallback을 유지한다.

책임 아님:
- Raw JSON 생성
- React state/useMemo/copy/export UI
- Preview column 자체 계산
- `document_fields.tableRows` 원본 변경
- v2 출력 구조 도입

## 11. Before / After 검증 기준
- Clean JSON before/after deep equality
- `templateName` 동일
- `info` 배열 동일
- `tables` 배열 동일
- 거래명세서 rows key order 동일
- 거래_1/4/5/7 rowIndex 제외 유지
- 거래_2/3/6 rowIndex 유지
- 거래_3 `insuranceCode`/`amount` 동작 변경 없음
- Preview column order와 Clean JSON row keys 일치
- Raw JSON 모드 변경 없음
- Copy/Export 동작 변경 없음
- typecheck/build PASS

권장 fixture:
- invoice_statement 거래_1~거래_7
- 영수증 TPL-003 baseline 일부 또는 전체
- field-only 문서
- table 없는 문서
- legacy `table_data` fallback 문서

## 12. 리스크와 주의사항
- `OcrResultPanel.tsx`의 `useMemo` 의존성 누락 위험
- `docTableDisplayCols` 전달 누락으로 row order/rowIndex 회귀 위험
- `field.tableRows/table_data/value` fallback 누락 위험
- helper가 `Object.keys(row)`를 사용해 숨긴 컬럼을 되살릴 위험
- v2 구조를 너무 일찍 적용해 breaking change가 생길 위험
- 현재 v1 `info` field-array와 미래 v2 `info` section-array 혼동 위험

## 13. Typecheck / Build 결과
| Command | Status | Exit | Seconds |
| --- | --- | --- | --- |
| npm run typecheck | PASS | 0 | 2.124 |
| npm run build | PASS | 0 | 15.868 |


### typecheck stdout tail
```text

> mysuit-ocr@0.1.0 typecheck
> tsc --noEmit


```

### typecheck stderr tail
```text
(empty)
```

### build stdout tail
```text

> mysuit-ocr@0.1.0 build
> next build

   ▲ Next.js 15.5.4
   - Environments: .env.local

   Creating an optimized production build ...
 ✓ Compiled successfully in 1728ms
   Linting and checking validity of types ...
   Collecting page data ...
   Generating static pages (0/18) ...
   Generating static pages (4/18) 
   Generating static pages (8/18) 
   Generating static pages (13/18) 
 ✓ Generating static pages (18/18)
   Finalizing page optimization ...
   Collecting build traces ...

Route (app)                                 Size  First Load JS
┌ ○ /                                      349 B         102 kB
├ ○ /_not-found                            993 B         103 kB
├ ƒ /api/autofill-cache                    141 B         102 kB
├ ƒ /api/biz-validate                      141 B         102 kB
├ ƒ /api/ground-truth                      141 B         102 kB
├ ƒ /api/login                             141 B         102 kB
├ ƒ /api/ocr-cache                         141 B         102 kB
├ ƒ /api/ocr-extract                       141 B         102 kB
├ ƒ /api/test-images                       141 B         102 kB
├ ○ /autorestore                         3.13 kB         113 kB
├ ○ /history                             9.08 kB         148 kB
├ ○ /login                                4.1 kB         127 kB
├ ○ /ocr                                 2.74 kB         113 kB
├ ○ /runocr                              65.3 kB         184 kB
├ ○ /template                            5.73 kB         116 kB
└ ○ /test                                47.2 kB         157 kB
+ First Load JS shared by all             102 kB
  ├ chunks/255-4efeec91c7871d79.js       45.7 kB
  ├ chunks/4bd1b696-c023c6e3521b1417.js  54.2 kB
  └ other shared chunks (total)          2.15 kB


○  (Static)   prerendered as static content
ƒ  (Dynamic)  server-rendered on demand


```

### build stderr tail
```text
 ⨯ ESLint: nextVitals is not iterable

```

## 14. 다음 작업 제안
1. FRONTEND-CLEANUP-1에서 `buildCleanJsonResult` 순수 helper를 분리하되 v1 출력 deep equality를 먼저 고정한다.
2. 거래_1~거래_7 fixture로 Preview column order와 Clean JSON row keys를 비교한다.
3. 거래_3 `insuranceCode`/`amount`는 별도 정책 작업으로 분리한다.
4. Clean JSON helper 분리 후 table renderer/label map 공통화를 다음 단계로 진행한다.
