## TPL-8C Template and Unstructured Table Result Alignment Precheck

### 1. Summary
- 현재 테이블 결과 경로: 세 갈래.
  1. **Backend canonical** — `raw.document_fields.tableRows` (+ `tableMeta`): invoice_statement 한정, backend가 canonical 키로 채움
  2. **Field 단위 table** — `OcrFieldResult.field_type === "table"`의 `value` (JSON string) / `tableRows` / `table_data`: cleanJsonBuilder가 fallback chain으로 처리
  3. **Unstructured projection** — `result.unstructuredTables[i].rows` (TPL-8B에서 채움): user-defined columnKey로 projection
- 템플릿 생성 테이블 결과 구조: 사용자가 캔버스에서 좌표(`rowTemplate`, `colGuides`) 지정 → backend가 invoice_statement에서 `document_fields.tableRows`를 채움 → OcrResultPanel이 `buildStructuredTableViewModel`로 Preview 렌더. `table.columns` 필드는 type/schema(`TableColumnDef`)는 이미 존재하지만 UI/저장은 spread-only이고 **UI는 아직 없음** ([TemplateRightPanel.tsx:82](mysuit-ocr/src/components/template/ui/TemplateRightPanel.tsx#L82) — `getColumns` helper만 존재).
- 비정형 테이블 결과 구조: `template.tables[].columns[].columnKey` → TPL-8B `extractUnstructuredTableRows`가 `document_fields.tableRows`를 projection → `result.unstructuredTables[i].rows`. **UI consumer 없음** (TPL-8C 작업 범위).
- Preview/Custom 현재 표시 구조: 둘 다 `docTableRows + docTableDisplayCols`로 동일 source를 보지만 ViewModel은 Preview만 `buildStructuredTableViewModel` 사용, Custom은 raw normalize. `result.unstructuredTables`는 두 탭 모두 무시. divergence 위험은 ViewModel 비대칭 + unstructuredTables 미consumer 두 가지.
- 공통 TableResult ViewModel 필요 여부: ✅ **필요**. Preview/Custom + Clean JSON/Markdown + 향후 Template table.columns + 현재 unstructuredTables가 모두 같은 정규화 view model을 바라봐야 일관성/중복방지 가능.
- 추천 다음 구현 작업: **TPL-8D-TABLE-RESULT-VIEWMODEL-HELPER** — pure helper 신설 (UI 미수정), backend tableRows + unstructuredTables + future template projection을 단일 `TableResultViewModel[]`로 normalize.
- 이번 precheck에서 운영 코드 수정 여부: 없음 (산출물 + 로그만).

### 2. Current Template Table Flow
- table region: 사용자가 [OcrCanvasPane.tsx](mysuit-ocr/src/common/ui/OcrCanvasPane.tsx)에서 `fieldType: "table"` Region을 캔버스 drag로 지정. `Region.table` ([ocr.ts:31-39](mysuit-ocr/src/common/types/ocr.ts#L31-L39))에 메타 보관
- rowTemplate: `region.table.rowTemplate: Rect` — 한 행의 좌표 템플릿. OcrCanvasPane이 drag로 생성하고, rows 배열은 `buildTableRows()`로 자동 생성
- columnGuides: `region.table.colGuides: number[]` — 0~1 비율 세로선 좌표. 클릭/drag로 추가, `normalizeColGuides`로 정렬·중복제거
- table.columns 현재 여부: **타입은 있고 UI는 없음**. `Region.table.columns?: TableColumnDef[]` ([ocr.ts:38](mysuit-ocr/src/common/types/ocr.ts#L38)), `TableColumnDef = { index, koField?, enField?, canonicalColumn?, mappingStatus?, mappingCandidates? }`. TemplateRightPanel에 `getColumns`/`updateColumn` helper는 있으나 렌더 JSX는 의도적으로 비어 있음 ("컬럼 정의는 제거, 가변/고정/세로가이드/종료키워드만"). TPL-1 plan에서 TPL-9에 작업 예약.
- buildTemplateExportPayload 저장 구조: ([buildTemplateExportPayload.ts:62-85](mysuit-ocr/src/components/template/utils/buildTemplateExportPayload.ts#L62-L85)) `region.table = { mode, rowTemplate, rows, colGuides, colX, stopKeywords, tableName?, columns? }`. `columns` 키는 spread-only(empty면 omit).
- RunOCR 결과와의 연결: 사용자 region template 저장 후 RunOCR가 호출되면 backend가 region 좌표를 사용해 invoice_statement extractor를 돌리고 `response.document_fields.tableRows`를 채워 보냄. 즉 **현재는 backend가 컬럼 매핑까지 다 해주고**, frontend는 결과만 표시.
- 현재 OcrResultPanel 표시 방식: Preview 탭에서 `buildStructuredTableViewModel({rows: docTableRows, displayCols: docTableDisplayCols, emptyValue: "-"})`로 view model 생성 → `<table className="or-table-result">` 렌더. Custom 탭은 같은 `docTableRows + docTableDisplayCols`로 `<textarea>` 편집 grid 렌더. Validation 탭은 표 단위로 같은 helper 재사용.
- 앞으로 컬럼 지정 기능을 붙일 때 필요한 점:
  - UI: TemplateRightPanel에 컬럼 정의 카드 + 컬럼 grid (비정형 UI 패턴 참고)
  - schema: `region.table.columns: TableColumnDef[]` 채움 (현재 spread-only)
  - RunOCR 연동: backend가 `document_fields.tableRows`를 canonical 키로 주는데, 사용자가 `table.columns`로 custom columnKey/labelKo를 정의하면 frontend가 **canonical → user-defined projection**을 수행 (TPL-8B와 동일한 패턴, 다른 source/target)
  - ViewModel: backend canonical 결과를 user columns로 projection한 결과가 Preview/Custom에 표시되어야 함

### 3. Current Unstructured Table Flow
- documentType: TPL-5 UI의 문서 유형 select. invoice_statement이면 projection 활성화
- template.tables: TPL-5 UI에서 카드별 추가/삭제. `{ tableKey, labelKo, labelEn?, columns: [{columnKey, labelKo, labelEn?}] }` 저장
- extractUnstructuredTableRows: TPL-8B 신설 helper. backend `document_fields.tableRows`를 user `template.tables[0].columns[].columnKey`로 projection
- unstructuredTables: TPL-7에서 mapOcrResponse가 skeleton 첨부 → TPL-8B에서 첫 번째 user table에 rows 채움
- rows projection: invoice_statement + 비어있지 않은 tableRows + 첫 user table의 columns가 있어야 작동. canonical 키와 user columnKey가 일치하면 1:1 매핑, mismatch면 ""
- 현재 표시 여부: ❌ **OcrResultPanel은 result.unstructuredTables를 읽지 않음**. Markdown/Clean JSON도 미consumer. UI/export 모두 TPL-8C 이후 작업.
- 한계:
  - invoice_statement 전용 (다른 documentType에서는 rows []  유지)
  - 첫 번째 user table만 (backend tableRows가 단일이므로)
  - canonical key 직접 매칭만 (aliases lookup은 TPL-8B-2 보류)
  - 사용자 정의 columnKey가 canonical과 다르면 빈 값

### 4. Existing Backend/Structured Table Flow
- document_fields.tableRows: backend `extractors/invoice_statement.py:7136` 에서 `canonical["tableRows"]`로 채워짐. 키: rowIndex/itemCode/itemName/spec/lotNo/serialNo/manufacturingNo/expiryDate/quantity/unit/unitPrice/supplyAmount/taxAmount/amount/totalAmount/manufacturer
- structuredTableViewModel: [structuredTableViewModel.ts](mysuit-ocr/src/common/utils/structuredTableViewModel.ts) — `buildStructuredTableViewModel({rows, displayCols, emptyValue})` → `{columns: [{key,label}], rows: [{cells: [{key,value,displayValue,isEmpty}]}], meta: {rowCount, columnCount, hasRows, hasColumns}}`. 한 줄 contract: cell normalization rules (Unicode dash→ASCII, trim, null→"").
- invoiceTableDisplay: [invoiceTableDisplay.ts](mysuit-ocr/src/common/utils/invoiceTableDisplay.ts) — `buildInvoicePreviewCols(tableMeta, rows): Array<{key: string; labelKo: string}>`. tableMeta.expectedColumnKeys → tableMeta.columns → hasValue fallback + filter 순서로 display columns 결정.
- OcrResultPanel structured preview: Preview 탭에서 `buildStructuredTableViewModel` view model을 직접 렌더 ([OcrResultPanel.tsx:1028-1097](mysuit-ocr/src/components/runocr/ui/OcrResultPanel.tsx#L1028-L1097)). Custom 탭은 같은 `docTableRows + docTableDisplayCols`를 받지만 `<textarea>` 편집 grid로 렌더 ([:1337-1416](mysuit-ocr/src/components/runocr/ui/OcrResultPanel.tsx#L1337-L1416))
- Clean JSON: [cleanJsonBuilder.ts:130-171](mysuit-ocr/src/common/utils/cleanJsonBuilder.ts#L130-L171) — fields의 `field_type === "table"`만 처리. fallback chain: `docTableRows` > `field.tableRows` > `field.table_data` > `JSON.parse(field.value)`. `result.unstructuredTables` 미consumer.
- Markdown: [markdownReportBuilder.ts:51-73](mysuit-ocr/src/common/utils/markdownReportBuilder.ts#L51-L73) — `docTableRows`를 받아 행 수 표시. `result.unstructuredTables` 미consumer.
- 기존 tableRows와 unstructuredTables의 관계: `unstructuredTables[0].rows`는 `document_fields.tableRows`의 projection. backend tableRows는 read-only source, unstructuredTables는 derived view. 둘은 **같은 데이터의 다른 표현**.

### 5. Preview vs Custom Analysis
- Preview 탭이 현재 보는 데이터: `docTableRows` (raw backend rows) + `docTableDisplayCols` (buildInvoicePreviewCols 결과) → `buildStructuredTableViewModel`로 정규화된 view model. `result.unstructuredTables` 미사용.
- Custom 탭이 현재 보는 데이터: 동일 `docTableRows + docTableDisplayCols`, 단 view model 빌더 없이 raw로 grid 렌더 + textarea 편집. `customTableEdits` state로 사용자 편집 반영.
- 두 탭이 달라질 위험: **MEDIUM**. 같은 source를 보지만 normalization 경로가 다르므로:
  - Preview는 cell value를 `normalizeStructuredTableCell` (Unicode dash, trim, null→"") 처리
  - Custom은 `normalizeCell(r[k])` 처리 (다른 normalize 함수)
  - 결과: Preview는 "-" 표시, Custom은 "" 표시가 가능 → 같은 cell이 다르게 보일 수 있음
- 동일해야 하는 데이터: 컬럼 수, 컬럼 순서, 컬럼 라벨, 행 수, cell raw value (사용자가 편집하기 전까지), empty/null/dash 표현
- 표현상 차이를 허용할 수 있는 부분: 색상/폰트/정렬/edit textarea 등 표시 정책. 데이터 값은 동일해야 함.
- 추천 원칙:
  1. **하나의 정규화 ViewModel을 두 탭에서 공유**
  2. cell value normalization은 ViewModel에서 단일 책임
  3. UI는 cell.displayValue / cell.value를 다르게 표시할 수 있지만 데이터는 같은 시점에 같음
  4. Custom의 edit overlay는 ViewModel 위에 별도 patch state로 분리 (현재 `customTableEdits` 패턴 유지 가능)

### 6. Proposed Common TableResult ViewModel

```ts
export type TableResultSource =
  | "backend_document_fields"        // raw.document_fields.tableRows (invoice_statement)
  | "unstructured_definition"        // result.unstructuredTables[].rows (TPL-8B projection)
  | "template_region_canonical"      // 향후 Template 생성 table.columns projection
  | "field_value_legacy";            // OcrFieldResult.field_type === "table" → value JSON (legacy)

export type TableResultColumn = {
  columnKey: string;          // user/canonical key (e.g. "itemName")
  labelKo: string;            // 표시 라벨 (한글 우선)
  labelEn?: string;
  source?: "user" | "canonical" | "fallback"; // 컬럼이 어디서 왔는지
};

export type TableResultCell = {
  key: string;            // == column.columnKey
  rawValue: string;       // 정규화 전 값 (디버그/export용)
  value: string;          // 정규화된 값 (Unicode dash → "-", trim, null → "")
  isEmpty: boolean;       // value === ""
  displayValue: string;   // isEmpty ? emptyPlaceholder : value
};

export type TableResultRow = {
  cells: TableResultCell[];  // column 순서와 정렬됨
};

export type TableResultMeta = {
  documentType?: string;
  source: TableResultSource;
  rowCount: number;
  columnCount: number;
  hasRows: boolean;
  hasColumns: boolean;
  /** 원본 데이터 식별자 (invoice_statement의 expectedColumnKeys, user tableKey 등) */
  originalKey?: string;
};

export type TableResultViewModel = {
  tableKey: string;       // user tableKey 또는 fallback (e.g. "items")
  labelKo: string;
  labelEn?: string;
  source: TableResultSource;
  columns: TableResultColumn[];
  rows: TableResultRow[];
  meta: TableResultMeta;
};
```

#### source 구분
| source | 입력 | columns 출처 | rows 출처 |
|---|---|---|---|
| `backend_document_fields` | `result.document_fields.tableRows + tableMeta` | `buildInvoicePreviewCols(tableMeta, rows)` (canonical key + 한글 label) | `tableRows` 그대로 |
| `unstructured_definition` | `result.unstructuredTables[i]` | `template.tables[i].columns` (user-defined) | `result.unstructuredTables[i].rows` (TPL-8B projection) |
| `template_region_canonical` (future TPL-10) | `result.document_fields.tableRows + template.regions[i].table.columns` | `table.columns[]` (user-defined) | `document_fields.tableRows`에서 user columnKey로 projection |
| `field_value_legacy` | `OcrFieldResult.value` (JSON string) / `field.tableRows` / `field.table_data` | fallback canonical key (`col_N` 또는 INVOICE_TABLE_COL_PRIORITY) | parsed cells |

#### backend tableRows 변환 (source: backend_document_fields)
```ts
const tableRows = raw.document_fields?.tableRows ?? [];
const displayCols = buildInvoicePreviewCols(raw.document_fields?.tableMeta, tableRows);
const vm = buildTableResultViewModel({
  source: "backend_document_fields",
  tableKey: "items",
  labelKo: "품목표",
  columns: displayCols.map(c => ({ columnKey: c.key, labelKo: c.labelKo, source: "canonical" })),
  rawRows: tableRows,
  documentType: "invoice_statement",
});
```

#### unstructuredTables 변환 (source: unstructured_definition)
```ts
for (const t of result.unstructuredTables ?? []) {
  const vm = buildTableResultViewModel({
    source: "unstructured_definition",
    tableKey: t.tableKey,
    labelKo: t.labelKo,
    labelEn: t.labelEn,
    columns: t.columns.map(c => ({ columnKey: c.columnKey, labelKo: c.labelKo, labelEn: c.labelEn, source: "user" })),
    rawRows: t.rows,
    documentType: result.documentType,
  });
}
```

#### future template table.columns 변환 (source: template_region_canonical)
```ts
// TPL-10에서 추가
for (const region of template.regions) {
  if (region.fieldType !== "table") continue;
  const userColumns = region.table?.columns ?? [];
  if (userColumns.length === 0) continue;
  const projectedRows = projectByColumnKey(raw.document_fields?.tableRows ?? [], userColumns);
  const vm = buildTableResultViewModel({
    source: "template_region_canonical",
    tableKey: region.name || `region_${region.id}`,
    labelKo: region.koField || region.name,
    columns: userColumns.map(c => ({ columnKey: c.canonicalColumn || c.enField || `col_${c.index}`, labelKo: c.koField || c.enField || "", labelEn: c.enField, source: "user" })),
    rawRows: projectedRows,
  });
}
```

#### empty state 기준
- `rows.length === 0` → "테이블 데이터 없음"
- `columns.length === 0` → "컬럼 정의 없음"
- 모든 cell value === "" → 빈 표 + 안내 (현재 missingExpectedWarning 패턴 유지)

### 7. Proposed Ownership

| 후보 | 장점 | 단점 | feature boundary 위험 | 테스트 용이성 | 추천 |
|---|---|---|---|---|---|
| `src/components/runocr/utils/buildTableResultViewModel.ts` | RunOCR 전용으로 시작, 비대화 위험 ↓ | 향후 Test/Template generation에서 재사용 시 common으로 이동 필요 | 낮음 | 높음 (pure helper) | ⚠️ 시작점으로는 OK, 장기적으로는 common 이동 |
| **`src/common/utils/tableResultViewModel.ts`** (신규) | RunOCR / Test / Template generation에서 모두 재사용 가능. `structuredTableViewModel`이 이미 common에 있어 같은 계층 | 신규 파일이 common에 추가됨 (1개) | 낮음 | 높음 | ✅ **강력 추천** |
| `structuredTableViewModel.ts` 확장 | 기존 helper 재사용 | 한 파일이 비대해짐 (다중 source 분기). 기존 fixture 영향 위험 | 중간 | 중간 | ❌ 비추 (locked behavior 영향 위험 — `tmp/fixtures/table_view_model_v1/` 8개 fixture로 잠금) |
| OcrResultPanel 내부 local helper | 즉시 작업 가능 | UI 컴포넌트 비대화 + Markdown/CleanJson에서 재사용 불가 | 높음 (UI 정책 누설) | 낮음 | ❌ 비추 |

**추천: `src/common/utils/tableResultViewModel.ts`** 신설. 기존 `structuredTableViewModel.ts`는 그대로 두고, 새 helper가 그것을 내부에서 호출하여 backend source를 처리 + unstructured/template source를 별도 분기로 처리. fixture lock(`tmp/fixtures/table_view_model_v1/`)에 영향 없음.

### 8. Implementation Plan

#### 1. TPL-8D-TABLE-RESULT-VIEWMODEL-HELPER
- 작업명: TPL-8D-TABLE-RESULT-VIEWMODEL-HELPER
- 도구: Claude Code (Opus 4.7)
- 목표: 공통 `TableResultViewModel` 타입 + `buildTableResultViewModels(result, template?)` helper 신설. backend `document_fields.tableRows` + `result.unstructuredTables`를 단일 `TableResultViewModel[]`로 normalize.
- 수정 파일 후보:
  - **신규**: `src/common/utils/tableResultViewModel.ts`
  - 운영 코드 0 touch (UI/mapOcrResponse/cleanJsonBuilder/markdownReportBuilder/Template 모두 미수정)
- 금지 사항: OcrResultPanel UI 수정, mapOcrResponse 수정, cleanJsonBuilder/markdownReportBuilder 수정
- 검증 기준: 신규 helper 단위 smoke 6+ 케이스 PASS — backend-only / unstructured-only / both / 빈 결과 / cell normalization 일치(`buildStructuredTableViewModel`과 동등) / input mutation 가드. typecheck/build PASS. 기존 51개 runner 회귀 0. markdown contract PASS.

#### 2. TPL-8E-TABLE-RESULT-PREVIEW-CUSTOM-UI
- 작업명: TPL-8E-TABLE-RESULT-PREVIEW-CUSTOM-UI
- 도구: Claude Code (Opus 4.7)
- 목표: OcrResultPanel Preview/Custom 양쪽이 `buildTableResultViewModels` 결과를 단일 source로 사용. 기존 `docTableRows + docTableDisplayCols → buildStructuredTableViewModel` 경로를 helper 호출로 통합. unstructuredTables도 자동 노출.
- 수정 파일 후보:
  - `src/components/runocr/ui/OcrResultPanel.tsx` — Preview 탭 + Custom 탭 + Validation 탭의 table render path를 helper 결과 기반으로 일원화
  - **금지**: 기존 invoice_statement structured preview 사라지지 않게 유지 (source: backend_document_fields가 우선)
- 금지 사항: cleanJsonBuilder/markdownReportBuilder 수정 (TPL-8F 작업), mapOcrResponse 수정, helper 추가 신규 (TPL-8D만)
- 검증 기준: 기존 invoice_statement Preview screenshot/markdown 결과 동일성 fixture 통과. unstructuredTables가 있는 case에서 추가 표 표시. Custom 탭 textarea 편집 기능 무회귀. 47개+ 기존 runner PASS.

#### 3. TPL-8F-TABLE-RESULT-EXPORT-INTEGRATION
- 작업명: TPL-8F-TABLE-RESULT-EXPORT-INTEGRATION
- 도구: Claude Code (Opus 4.7)
- 목표: cleanJsonBuilder / markdownReportBuilder가 `TableResultViewModel[]`을 input으로 받도록 확장. 기존 input shape도 backward compat 유지.
- 수정 파일 후보:
  - `src/common/utils/cleanJsonBuilder.ts` — `TableResultViewModel[]` input 추가, 기존 `docTableRows + docTableDisplayCols` input 유지 (deprecated path)
  - `src/common/utils/markdownReportBuilder.ts` — 동일
  - OcrResultPanel — toMarkdown/toCleanJson 호출 시 새 input 전달
- 금지 사항: OcrResultPanel UI 추가 변경, helper 신규 추가, mapOcrResponse 수정
- 검증 기준: markdown contract 21 PASS (회귀 0). Clean JSON v1 fixture 무회귀. unstructuredTables를 가진 fixture에서 export에 표 row 포함.

#### 4. TPL-9-TEMPLATE-TABLE-COLUMN-DEFINITION-UI
- 작업명: TPL-9-TEMPLATE-TABLE-COLUMN-DEFINITION-UI
- 도구: Claude Code (Opus 4.7)
- 목표: TemplateRightPanel에 `table.columns` UI 추가 — 비정형 카드 grid 패턴 차용 (`28px / 1fr / 1fr / 24px`). columnGuides와 columns의 index를 연결 표시.
- 수정 파일 후보:
  - `src/components/template/ui/TemplateRightPanel.tsx` (table region 선택 시 신규 섹션)
  - 신규: `src/components/template/ui/TemplateTableColumnEditor.tsx` (선택)
  - `src/common/types/ocr.ts` `TableColumnDef`에 optional 필드 추가 (TPL-1 plan에 따라 columnKey/labelKo/labelEn/required/visible/order/source/userConfirmed)
- 금지 사항: OcrCanvasPane 수정, UnstructuredBuilder 수정, Test/RunOCR 수정, profiles.ts 직접 import
- 검증 기준: TPL-1 plan §12 #3 검증 기준 그대로 적용

#### 5. TPL-10-TEMPLATE-TABLE-COLUMN-RESULT-PROJECTION
- 작업명: TPL-10-TEMPLATE-TABLE-COLUMN-RESULT-PROJECTION
- 도구: Claude Code (Opus 4.7)
- 목표: 템플릿 생성에서 사용자가 `region.table.columns`를 정의한 경우, mapOcrResponse 또는 buildTableResultViewModel에서 backend `document_fields.tableRows`를 user columnKey로 projection. unstructured와 동일 패턴.
- 수정 파일 후보:
  - `src/common/utils/tableResultViewModel.ts` — `source: "template_region_canonical"` 분기 추가
  - `src/components/runocr/utils/mapOcrResponse.ts` — region-based template 분기에서 columns가 있으면 projection 결과 첨부 (또는 ViewModel 빌더가 result + template을 모두 받는 형태)
- 금지 사항: UnstructuredBuilder 수정, backend 수정
- 검증 기준: 기존 region-based template 결과 무회귀. table.columns가 있는 region에서 projection 결과가 ViewModel에 포함.

### 9. Risk Assessment
- Preview/Custom divergence risk: **MEDIUM (현재)** → TPL-8D/E로 LOW. 현재 두 탭이 normalize 함수가 달라서 같은 cell이 다르게 표시될 수 있음.
- duplicate table display risk: **HIGH** (TPL-8E 미진행 시). unstructuredTables를 그대로 UI에 추가하면 invoice_statement에서 같은 데이터가 두 표로 표시될 위험. TPL-8D ViewModel이 source 우선순위(backend > unstructured > field_value)를 정해야 함.
- template table future compatibility risk: **LOW** (ViewModel이 `source: template_region_canonical`을 미리 정의하면 추가 비용 없음).
- existing receipt compatibility risk: **LOW** — receipt는 `field_type !== "table"` 위주. `field_value_legacy` source가 fallback chain을 유지.
- invoice_statement structured preview risk: **MEDIUM** — `buildStructuredTableViewModel` fixture 8개로 잠겨 있음. 신규 ViewModel은 그것을 wrap하거나 동등 출력을 보장해야 함. TPL-8D smoke에서 fixture 동등성 검증 필수.
- export compatibility risk: **MEDIUM** — Clean JSON v1 contract와 markdown contract가 잠겨 있음. TPL-8F는 backward compat path를 반드시 유지해야 함.
- result schema risk: **LOW** — `unstructuredTables` 키는 TPL-7/8B에서 이미 attach. ViewModel은 derived state이므로 result shape 변경 0.

### 10. Do Not Start Yet
- TPL-8D / TPL-8E / TPL-8F / TPL-9 / TPL-10 어떤 단계도 본 precheck에서는 시작 금지
- OcrResultPanel UI에 `unstructuredTables` 표시 추가 금지
- cleanJsonBuilder/markdownReportBuilder에 unstructuredTables consumer 추가 금지
- `src/common/utils/tableResultViewModel.ts` 신규 파일 추가 금지
- `structuredTableViewModel.ts` 수정 금지 (fixture lock 보호)
- TableColumnDef 타입 확장 금지 (TPL-9 작업)
- mapOcrResponse 변경 금지
- 사용자 정의 columnKey가 backend canonical과 다른 경우의 alias resolution 구현 금지

### 11. Verification Results
- production code modified: NO
- src/lib absent: YES
- @/lib import 0: YES
- typecheck: 다음 run에서 PASS 확인 예정
- build: 다음 run에서 PASS 확인 예정
- static precheck: 다음 run에서 PASS 확인 예정 ([TABLE_RESULT_ALIGNMENT_PRECHECK_TPL8C] PASS)
- FAIL count: 0
