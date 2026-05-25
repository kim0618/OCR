## TPL-9A Template Table Column Definition Precheck

### 1. Summary
- 현재 Template table 구조: 사용자가 캔버스에서 `fieldType: "table"` Region을 drag하여 생성. `region.table = { mode, rowTemplate?, rows?, colGuides?, stopKeywords?, tableName?, columns? }` ([common/types/ocr.ts:31-39](mysuit-ocr/src/common/types/ocr.ts#L31-L39)). mode는 `"repeat"`(고정 그리드, rowTemplate 기반) / `"auto"`(가변 그리드, colGuides + stopKeywords 기반) 두 종류.
- rowTemplate 구조: `Rect = {x, y, width, height}`. OcrCanvasPane이 사용자의 "행 템플릿 지정" drag로 생성 ([OcrCanvasPane.tsx:347-431](mysuit-ocr/src/common/ui/OcrCanvasPane.tsx#L347-L431)). `buildTableRows(area, rowTemplate)`가 동일 height로 region 끝까지 반복하여 `rows: Rect[]`를 자동 채움. **모든 row가 동일 height** — 개별 row 조정 mechanism 부재.
- colGuides 구조: `number[]` (0~1 ratio). 클릭/drag로 추가, `normalizeColGuides`가 정렬·중복제거 (최대 40개). save payload에서 `colX: number[]` (절대 px) 함께 출력.
- table.columns 현재 상태: **타입과 helper는 존재하지만 UI는 없다**. `Region.table.columns?: TableColumnDef[]` ([common/types/ocr.ts:38](mysuit-ocr/src/common/types/ocr.ts#L38)), `TableColumnDef = { index, koField?, enField?, canonicalColumn?, mappingStatus?, mappingCandidates? }` (오직 `index`만 required). `getColumns`/`updateColumn` helper는 TemplateRightPanel에 이미 존재 ([TemplateRightPanel.tsx:82-102](mysuit-ocr/src/components/template/ui/TemplateRightPanel.tsx#L82-L102)) — `colCount = colGuides.length + 1`로 자동 entry 생성. **JSX 렌더만 비어 있음** (의도적 비활성, 코드 주석 `"컬럼 정의는 제거"`).
- 가변형/고정형 구조: `region.table.mode === "repeat"`이면 고정 그리드(rowTemplate + buildTableRows로 행 자동 생성), `"auto"`이면 가변 그리드(rowTemplate undefined, OCR 단계에서 row 자동 감지). columns metadata는 두 mode 모두에서 동일하게 `colGuides + 1` 기반.
- 추천 MVP: **Option A — colGuides 구간 기준 column 자동 생성 + 사용자가 columnKey/labelKo만 입력**. `getColumns` helper가 이미 `colGuides.length + 1`로 entry를 만들고, JSX만 추가하면 됨. 비정형 UI의 28px / 1fr / 1fr grid 카드 패턴 그대로 차용.
- rowOverrides 처리 방침: **TPL-11로 분리**. 현재 `buildTableRows`는 동일 height만 지원하고, per-row 높이 조정은 (a) `rows: Rect[]`를 user-editable로 승격하거나 (b) `rowOverrides?: Array<{index, y?, height?}>` 신설이 필요. 둘 다 TPL-9 column 작업과 독립적이므로 별도 phase로 안전.
- 다음 구현 작업: **TPL-9B-TEMPLATE-TABLE-COLUMN-DEFINITION-UI** — TemplateRightPanel에 컬럼 정의 카드 mount + (선택) TableColumnDef에 optional MVP 필드 추가.
- 이번 precheck에서 운영 코드 수정 여부: 없음. 산출물 + 로그만 생성.

### 2. Current Template Table Flow
- TemplateAnnotator state: `regions: Region[]` + `rowTemplateTargetId: string | null` + `colGuideTargetId: string | null`. table edit 모드 진입 시 OcrCanvasPane에 target id 전달, 사용자가 drag/click → setRegions로 region.table을 갱신.
- TemplateRightPanel UI: table region 선택 시 표시되는 컨트롤 ([TemplateRightPanel.tsx:357-473](mysuit-ocr/src/components/template/ui/TemplateRightPanel.tsx#L357-L473)) — `[가변 그리드 | 고정 그리드]` mode 토글, `[종료 키워드]` input, `[행 템플릿 지정][세로 가이드 찍기][행 템플릿 해제][가이드 전체 삭제][지정 취소][찍기 취소]` 버튼군, `세로 가이드선` 리스트 (각 button 클릭 시 삭제). 컬럼 정의 UI는 **의도적으로 비어 있음** (코드 주석 `"컬럼 정의는 제거, 가변/고정/세로가이드/종료키워드만"`).
- OcrCanvasPane table edit: ① `drawRowTemplate` drag(`rowTemplateTargetId` 활성 시) → `region.table.rowTemplate` set + `buildTableRows()` 호출하여 `rows` 자동 채움. ② colGuide 클릭/`tableCol` drag(`colGuideTargetId` 활성 시) → `region.table.colGuides` push 또는 이동. ③ region resize 시 `clampRectToArea`로 rowTemplate clamp + rows 재계산. ④ region move 시 rowTemplate / rows shift.
- buildTemplateExportPayload: ([buildTemplateExportPayload.ts:61-85](mysuit-ocr/src/components/template/utils/buildTemplateExportPayload.ts#L61-L85)) — table region의 `mode/rowTemplate/rows/colGuides/colX/stopKeywords/tableName?/columns?`를 직렬화. `colX`는 `anchor.x + anchor.width * guide` 형태로 backend가 px 단위 좌표를 알 수 있게 함. **`columns`는 spread-only** — 현재 `r.table.columns`가 정의되어 있으면 그대로 보존, 없으면 키 자체 omit.
- saved payload: `{ id, name, fieldType: "table", x/y/width/height, koField?, enField?, canonicalField?, mappingStatus?, valueType?, table: { mode, rowTemplate|null, rows: Rect[], colGuides: number[], colX: number[], stopKeywords: string[], tableName?, columns? } }`
- RunOCR 연결: 저장된 region 정보를 backend에 보내면 backend가 invoice_statement 등에서 `document_fields.tableRows`를 canonical key로 채워서 응답. frontend는 OcrResultPanel에서 그대로 표시. **현재 `table.columns`는 backend가 사용하지 않음** — 사용자 정의 컬럼 매핑은 frontend projection 단계에서 적용해야 함 (TPL-10 작업).
- 현재 한계: ① columns UI 미구현 (helper만 있음), ② row 개별 높이 조정 불가 (rowTemplate height가 모든 row에 적용), ③ canonical 매핑(`canonicalColumn`)은 type에는 있지만 UI/serialize 단계에서 활용 없음, ④ TableColumnDef에 `columnKey`/`labelKo`/`labelEn` 같은 직관적 필드 없음 (현재 `koField`/`enField`만 — Region과 동일 명명이라 column-specific 컨텍스트 부족).

### 3. Current Table Schema

#### Region
```ts
type Region = {
  id: string;
  name: string;
  fieldType: "field" | "multi" | "check" | "table";
  x, y, width, height: number;
  parts?: 2 | 3; ratios?: number[]; checkMode?; // multi/check
  table?: TableMeta;
  koField?, enField?, canonicalField?, mappingStatus?, mappingCandidates?, valueType?;
};
```

#### TableMeta (`region.table`)
```ts
type TableMeta = {
  mode?: "repeat" | "auto";    // 고정/가변
  rowTemplate?: Rect;           // 한 줄 행 좌표 (mode === "repeat" 한정)
  rows?: Rect[];                // buildTableRows로 자동 생성
  colGuides?: number[];         // 세로 가이드 ratio (0~1)
  stopKeywords?: string[];      // 가변 그리드에서 종료 keyword
  tableName?: string;           // 사용자 정의 테이블 이름 (TPL-9 작업에서 활용 예정)
  columns?: TableColumnDef[];   // 현재 schema 존재, UI 없음
};
```

#### TableColumnDef (현재)
```ts
type TableColumnDef = {
  index: number;
  koField?: string;
  enField?: string;
  canonicalColumn?: string;
  mappingStatus?: "auto" | "ambiguous" | "manual" | "unmapped";
  mappingCandidates?: FieldMappingCandidate[];
};
```

#### rowTemplate / rows 동작
- `buildTableRows(area, rowTemplate)` ([ocrTableRegion.ts:34-50](mysuit-ocr/src/common/utils/ocrTableRegion.ts#L34-L50)) — `y = rowTemplate.y`, `while (y + rt.height <= area.y + area.height) { rows.push({x:rt.x, y, width:rt.width, height:rt.height}); y += rt.height; }`. 모든 row가 **동일 height**.
- mode === "auto"이면 `rowTemplate = undefined` + `rows = undefined` 유지. 행 감지는 backend OCR 단계에서 수행.

#### colGuides → 컬럼 구분
- `normalizeColGuides(arr)` — 0~1 ratio만, 양 끝 제외, 중복 제거(eps=0.002), 최대 40개
- `colGuides`의 N개 가이드는 영역을 N+1개 구획으로 나눔
- `getColumns(region)`는 자동으로 `index 0..N` entry를 생성 (TableColumnDef[])
- 매핑: `column[i]` ↔ guides[i-1]~guides[i] 사이의 영역 (i=0이면 영역 왼쪽 끝~guides[0])

### 4. Row Strategy
- 현재 rowTemplate 반복 방식: 사용자 drag로 `rowTemplate: Rect` 한 줄 지정 → `buildTableRows`가 동일 height로 region.height까지 반복 → `rows: Rect[]` 자동 생성. region resize 시 `rows` 재계산. **모든 row가 동일 height 강제**.
- row 개별 조정 가능성: 현재 schema는 `rows: Rect[]`를 가지고 있지만 사용자가 직접 수정하는 UI는 없음. 가능한 방향:
  - (A) `rows` 자체를 user-editable로 승격 — 각 Rect를 drag로 조정. 단, rowTemplate 갱신 시 user edit가 덮어쓰여지는 문제 해결 필요.
  - (B) `rowOverrides?: Array<{ index: number, y?: number, height?: number }>` 신설 — rowTemplate은 baseline, overrides는 patch. buildTableRows가 overrides를 흡수하도록 변경.
- rowOverrides 후보 schema (TPL-11에서 확정):
  ```ts
  type TableMeta = {
    ...
    rowOverrides?: Array<{
      index: number;        // rowTemplate-derived index (0-based)
      y?: number;           // 절대 y (px) — 미설정 시 rowTemplate.y + index * rowTemplate.height
      height?: number;      // 절대 height (px)
      userConfirmed?: boolean;
    }>;
  };
  ```
- MVP 포함 여부: ❌ **TPL-9에 포함하지 않음**. 이유: ① TableColumnDef UI와 독립적, ② buildTableRows 수정이 OcrCanvasPane의 region resize/move handler에 영향, ③ backend가 절대 `rows: Rect[]`를 어떻게 해석할지 contract 변경 가능. ④ 사용자가 columns만 추가해도 즉시 값이 있는 기능이고, rowOverrides는 정확도 fine-tune 기능 (urgency 낮음).
- 후속 작업 제안: **TPL-11-TEMPLATE-TABLE-ROW-OVERRIDES-PRECHECK** — rowOverrides 도입 시 영향 범위(OcrCanvasPane drag UI / region resize / buildTableRows / backend payload / RunOCR row mapping) 단독 분석. 그 결과로 TPL-12에서 구현.

### 5. Column Strategy

| option | description | pros | cons | recommendation |
|---|---|---|---|---|
| **A. colGuides interval auto columns** | colGuides가 N개면 N+1개 컬럼 자동 생성. 사용자는 columnKey/labelKo만 입력. `getColumns` helper가 이미 이 방식으로 entry 자동 생성. | ① 기존 helper 그대로 활용 ② UI 단순 (카드 row 입력만) ③ colGuides와 column의 1:1 대응이 직관적 ④ 비정형 UI 패턴과 일관 | colGuides가 늘면 컬럼이 자동 증가 (사용자 의도와 불일치 가능) → mismatch 처리 필요 | ✅ **MVP 채택** |
| B. guideStart/guideEnd selection | 사용자가 각 컬럼마다 시작/종료 guide index 선택. 한 컬럼이 여러 guide 구간을 가질 수도 있음. | ① 유연 ② merged column 가능 (예: "단가/금액" 한 컬럼) ③ guide-column 매핑 명시적 | ① UI 복잡 (각 row에 2개 select) ② getColumns가 자동 entry를 만들면 사용자 매핑이 깨질 위험 ③ MVP 범위 초과 | △ 후속 (TPL-10/TPL-12) |
| C. per-column box drawing | 컬럼별로 별도 box를 캔버스에 그림. rowTemplate/colGuides 체계와 별도. | ① 가장 유연 ② 컬럼이 row 영역과 무관 | ① 기존 colGuides 체계와 충돌 ② OcrCanvasPane 대수술 ③ MVP 비추천 | ❌ |

**최종 추천: Option A** — `getColumns` helper의 자동 entry 생성을 그대로 살리고, TemplateRightPanel에 JSX 카드 row만 추가. 비정형 UI(`28px / 1fr / 1fr` grid) 패턴 차용. mismatch는 visible chip ("가이드 수와 다름")으로 안내 + `userConfirmed`로 사용자 확인 표시.

### 6. Proposed Template Table Columns Schema

MVP 필드(이번 TPL-9B/9C에서 추가):
```ts
type TableColumnDef = {
  index: number;             // 기존 (auto-generated, 0-based)
  // NEW MVP
  columnKey?: string;        // 안정적 식별자 (e.g. "itemName")
  labelKo?: string;          // 한글 컬럼명
  labelEn?: string;          // 영문 컬럼명
  // EXISTING (kept for backward compatibility — Region-style legacy)
  koField?: string;          // legacy (Region용 명명)
  enField?: string;          // legacy
  canonicalColumn?: string;
  mappingStatus?: "auto" | "ambiguous" | "manual" | "unmapped";
  mappingCandidates?: FieldMappingCandidate[];
};
```

후속 필드(TPL-9C 또는 TPL-10 작업):
```ts
type TableColumnDef = {
  ...MVP...
  order?: number;            // 명시 정렬 (미설정 시 index)
  required?: boolean;
  visible?: boolean;
  source?: "user" | "auto" | "default";
  userConfirmed?: boolean;
  aliases?: string[];        // canonical 매칭 후보
  // colGuides 연결 (B 옵션에서 활성)
  guideIndex?: number;       // 단일 guide 매핑
  guideStartIndex?: number;
  guideEndIndex?: number;
};
```

MVP는 `columnKey`/`labelKo`/`labelEn`만 추가 (5개 → 8개 필드). 기존 `koField`/`enField`는 backward-compat 차원에서 유지하되 deprecation 주석 권장. UI는 `labelKo`(한글 컬럼명) 우선 표시, `columnKey`는 키 식별자(영문).

#### colGuides 연결 방식 (MVP)
- guide 0개 → column 1개 (영역 전체)
- guide N개 → column N+1개 (자동 자르기)
- `column[i].index === i`로 guide 구간과 대응
- 별도 `guideStartIndex/guideEndIndex` 필드 없이 `index`로 추론 (옵션 A)
- guide 추가/삭제 시 column 배열 자동 확장/축소 (`getColumns` helper가 이미 처리)

#### mismatch 처리
- `region.table.columns.length > guideCount + 1`: 초과분은 `getColumns`가 `slice(0, colCount)`로 자동 축소
- `region.table.columns.length < guideCount + 1`: 부족분은 `getColumns`가 `{ index: i }` empty entry로 자동 보충
- UI는 두 경우 모두 "가이드 N개 → 컬럼 N+1개" 메시지를 헤더 옆에 노출

### 7. Proposed UI Layout

TemplateRightPanel의 `selected.fieldType === "table"` 블록에서 "세로 가이드선 목록" 섹션 아래에 신규 "컬럼 정의" 섹션을 추가:

```
[기존: 그리드 모드 / 종료 키워드 / 가이드 버튼들 / 세로 가이드선 리스트]
─────────────────────────────────────────────────────
컬럼 정의                              ⓘ 가이드 N개 → 컬럼 N+1개
┌ grid 28px / 1.2fr / 1fr / 1fr ──────────────────────────────┐
│ No │ 한글 컬럼명          │ 영문 key      │ canonical (선택) │
├────┼─────────────────────┼──────────────┼──────────────────┤
│ 1  │ [품목명          ]   │ [itemName  ] │ [itemName ▾]     │
│ 2  │ [수량            ]   │ [quantity  ] │ [quantity ▾]     │
│ 3  │ [단가            ]   │ [unitPrice ] │ [unitPrice ▾]    │
│ 4  │ [금액            ]   │ [amount    ] │ [amount ▾]       │
└────┴─────────────────────┴──────────────┴──────────────────┘
empty: "세로 가이드를 추가하면 컬럼이 자동 생성됩니다."
```

포함할 것:
- **위치**: table region 선택 시 표시 — 세로 가이드선 리스트 아래에 신규 sub-section. region이 table이 아니면 미표시.
- **버튼**: MVP는 추가 버튼 불필요 (colGuides 변경 → 자동 update). 굳이 둔다면 헤더 우측에 `[가이드 동기화]`(현재 colGuides 기준 column entries 재생성).
- **grid columns**: `28px / 1.2fr / 1fr / 1fr` — No / 한글 컬럼명 / 영문 key / canonical select.
- **empty state**: colGuides가 비어 있으면 "세로 가이드를 추가하면 컬럼이 자동 생성됩니다." 안내. colGuides 1개만 있어도 컬럼 2개 자동 생성 → empty 분기 거의 없음.
- **columnGuides mismatch 처리**: 헤더에 `ⓘ 가이드 N개 → 컬럼 N+1개` chip 표시. getColumns가 자동 조정하므로 UI 상 mismatch는 시각화만.
- **기존 비정형 UI와의 일관성**: 비정형 UI의 28px/1fr/1fr grid를 동일 패턴으로 채택 (사용자 학습 비용 최소화). canonical select 컬럼은 비정형엔 없는 Template 전용 — 이는 좌표 기반 column 매핑에 특유.

### 8. Interaction with TableResultViewModel
- TPL-10에서 source = template_region_canonical 연결 방식:
  - `tableResultViewModel.ts`의 `buildTableResultViewModels(result, template)`가 두 번째 인자 `template`을 받아 region.table.columns가 정의된 region이 있으면 `template_region_canonical` source의 view model 생성
  - 입력: `result.document_fields.tableRows` + `template.regions[i].table.columns`
  - 동작: backend canonical rows를 user columnKey로 projection (extractUnstructuredTableRows의 region-variant)
- backend `document_fields.tableRows`를 columnKey 기준 projection하는 방식:
  - canonical key (e.g. `itemName`, `quantity`)와 user `columnKey`가 일치 → 1:1 매핑
  - canonical과 다른 user columnKey → `""` (또는 `aliases` lookup, 후속)
  - 같은 패턴이 비정형(TPL-8B `extractUnstructuredTableRows`)에서 이미 검증됨
- 비정형 projection과의 공통점: 
  - 모두 backend canonical-keyed rows를 user columnKey로 projection
  - 같은 stringifyCellValue + buildStructuredTableViewModel 정규화 거침
  - 결과적으로 같은 TableResultViewModel shape (다만 source 라벨만 다름)
- Preview/Custom/export 자동 반영 조건:
  - TPL-10에서 `buildTableResultViewModels(result, activeTemplate)`로 호출 (TPL-8D는 template 미사용)
  - 추가 적으로 `OcrResultPanel`이 `activeTemplate`을 prop으로 받아 useMemo에 의존성으로 추가
  - 그 다음 Preview/Custom/CleanJson/Markdown 전부 자동 노출 (TPL-8E/8F에서 이미 ViewModel 기반)

### 9. Risk Assessment
- OcrCanvasPane impact: **LOW** — TPL-9B는 OcrCanvasPane을 수정하지 않음. colGuides 편집은 캔버스, 컬럼 정의는 우측 패널로 책임 분리 유지.
- TemplateRightPanel complexity: **MEDIUM** — 새 섹션 추가. JSX 길이 증가하지만 기존 helper(`getColumns`/`updateColumn`) 재사용으로 로직 복잡도는 낮음.
- save/load compatibility: **LOW** — buildTemplateExportPayload가 이미 `columns` spread. 신규 필드(columnKey/labelKo/labelEn)는 optional이므로 기존 templates.json 호환.
- colGuides mismatch: **LOW** — `getColumns`가 이미 자동 동기화 (slice/extend). UI chip으로만 시각화.
- rowOverrides scope creep: **LOW** — TPL-11로 분리 명시. TPL-9에 절대 끌어들이지 않음.
- RunOCR projection risk: **LOW** — TPL-9B/9C는 UI/저장만. RunOCR projection은 TPL-10에서 별도 작업.
- existing template compatibility: **LOW** — `column.columnKey`가 없는 기존 template도 정상 load (optional). 신규 column UI에서는 기존 `koField`/`enField` 값이 있으면 그대로 표시하여 점진적 migration.

### 10. Recommended Implementation Plan

#### 1. TPL-9B-TEMPLATE-TABLE-COLUMN-DEFINITION-UI
- 작업명: TPL-9B-TEMPLATE-TABLE-COLUMN-DEFINITION-UI
- 도구: Claude Code (Opus 4.7)
- 목표: TemplateRightPanel에 "컬럼 정의" 섹션 mount. TableColumnDef에 MVP optional 필드(`columnKey?`, `labelKo?`, `labelEn?`) 추가. Option A (colGuides 자동 column 생성) 채택.
- 수정 파일 후보:
  - `src/components/template/ui/TemplateRightPanel.tsx` (table 블록 내부에 신규 섹션 추가)
  - `src/common/types/ocr.ts` (TableColumnDef에 MVP optional 필드 추가)
- 금지 사항:
  - `src/common/ui/OcrCanvasPane.tsx` 수정 금지
  - `src/components/template/utils/buildTemplateExportPayload.ts` 수정 금지 (이미 spread 처리)
  - `tableResultViewModel.ts` / `mapOcrResponse.ts` / `cleanJsonBuilder.ts` / `markdownReportBuilder.ts` 수정 금지
  - UnstructuredBuilder / TestWorkspace 수정 금지
  - profiles.ts 직접 import 금지
  - row override / rowTemplate 동작 변경 금지
- 검증 기준:
  - typecheck/build PASS
  - TemplateRightPanel mount static smoke: table region 선택 시 컬럼 정의 섹션 표시, colGuides 변경에 따라 column entry 자동 동기화
  - 기존 55개 runner PASS (TPL-1/8C에서 forbid한 신규 UI 추가에 phase-aware allow 추가 필요)
  - markdown contract 21 PASS

#### 2. TPL-9C-TEMPLATE-TABLE-COLUMN-SAVE-LOAD
- 작업명: TPL-9C-TEMPLATE-TABLE-COLUMN-SAVE-LOAD
- 도구: Claude Code (Opus 4.7)
- 목표: localStorage round-trip 검증 — TPL-9B에서 입력한 columns가 save → reload → edit 무손실 round-trip. legacy template(columns 없음) load 시 자동 entry 생성 후 사용자 입력 받을 수 있는 상태로 표시.
- 수정 파일 후보:
  - `src/components/template/ui/TemplateAnnotator.tsx` (필요 시 load hydrate 보강 — 현재 `setRegions(selectedTemplate.regions)`로 그대로 복원되므로 변경 거의 없음)
  - fixture: `tmp/fixtures/template_table_columns/`
- 금지 사항: TPL-9B 동일.
- 검증 기준: round-trip fixture 5+ 케이스 PASS (no columns / columnKey only / labelKo only / canonical only / 모든 필드 채움). typecheck/build PASS.

#### 3. TPL-10-TEMPLATE-TABLE-COLUMN-RESULT-PROJECTION
- 작업명: TPL-10-TEMPLATE-TABLE-COLUMN-RESULT-PROJECTION
- 도구: Claude Code (Opus 4.7)
- 목표: `tableResultViewModel.ts`의 `template_region_canonical` source 활성화. backend `document_fields.tableRows`를 user `region.table.columns[].columnKey`로 projection. Preview/Custom/CleanJson/Markdown 자동 반영 (TPL-8E/8F 통합 덕분).
- 수정 파일 후보:
  - `src/common/utils/tableResultViewModel.ts` (template_region_canonical 분기 추가)
  - `src/components/runocr/ui/OcrResultPanel.tsx` (activeTemplate을 buildTableResultViewModels에 전달 — 현재 result만 전달)
  - 신규: `src/components/runocr/utils/extractTemplateRegionTableRows.ts` (선택, TPL-8B와 같은 패턴)
- 금지 사항: TemplateRightPanel/OcrCanvasPane 수정 금지, backend 수정 금지, UnstructuredBuilder/TestWorkspace 수정 금지.
- 검증 기준: smoke — template region에 columns 정의된 경우 ViewModel에 template_region_canonical entry 생성, Preview/Custom에 user columnKey로 표시, Clean JSON/Markdown export 통합. 기존 backend_document_fields/unstructured_definition source 회귀 0.

#### 4. TPL-11-TEMPLATE-TABLE-ROW-OVERRIDES-PRECHECK
- 작업명: TPL-11-TEMPLATE-TABLE-ROW-OVERRIDES-PRECHECK
- 도구: Claude Code (Opus 4.7)
- 목표: row 개별 높이 조정 도입 가능성 단독 precheck. OcrCanvasPane drag UI 영향 / region resize handler 영향 / buildTableRows 변경 / backend payload contract / RunOCR row 매핑 영향 분석. 실제 구현은 TPL-12로 분리.
- 수정 파일 후보: 없음 (precheck — 산출물만)
- 금지 사항: 운영 코드 0 touch.
- 검증 기준: 산출물에 rowOverrides schema 후보 / OcrCanvasPane drag 정책 / backend 영향 / risk assessment 포함. typecheck/build/static precheck PASS.

### 11. Do Not Start Yet
- TPL-9B / TPL-9C / TPL-10 / TPL-11 어떤 단계도 본 precheck 단계에서는 시작 금지
- TableColumnDef 타입 확장 금지 (TPL-9B 작업)
- TemplateRightPanel에 신규 섹션 mount 금지
- TableColumnEditor 신규 컴포넌트 추가 금지
- OcrCanvasPane에 컬럼 편집 UI 추가 금지 (절대)
- tableResultViewModel의 template_region_canonical 분기 활성화 금지 (TPL-10)
- buildTemplateExportPayload column 직렬화 변경 금지 (현재 spread로 충분)
- rowOverrides / 개별 row 높이 조정 구현 금지 (TPL-11/12)
- 기존 templates.json 수정 금지
- profiles.ts import 추가 금지

### 12. Verification Results
- production code modified: NO
- src/lib absent: YES
- @/lib import 0: YES
- typecheck: 다음 run에서 PASS 확인 예정
- build: 다음 run에서 PASS 확인 예정
- static precheck: 다음 run에서 PASS 확인 예정 ([TEMPLATE_TABLE_COLUMN_DEFINITION_PRECHECK_TPL9A] PASS)
- FAIL count: 0
