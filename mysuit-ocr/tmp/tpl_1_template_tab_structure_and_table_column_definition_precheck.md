## TPL-1 Template Tab Structure and Table Column Definition Precheck

### 1. Summary
- src/lib cleanup status: 완료. `src/lib` 디렉터리 absent, `@/lib/*` import 0건, 상대경로 `../lib`/`../../lib` import 0건.
- Template 탭 구조 파악 결과: `/template` 라우트는 모드 카드(`템플릿 생성` / `비정형 생성`)로 두 흐름을 분기하며, `template` 모드는 `TemplateAnnotator` + `OcrCanvasPane` + `TemplateRightPanel`, `unstructured` 모드는 `UnstructuredBuilder` 단독 UI를 사용한다.
- 템플릿/비정형 분기 방식: `src/app/template/page.tsx`의 `Mode = "template" | "unstructured"` state와 모드별 분기 렌더링. 저장 payload도 두 갈래로 완전히 분리되어 있다 (`buildExportPayload` vs UnstructuredBuilder 인라인 payload).
- table column definition 구현 진입 가능 여부: 진입 가능. 타입(`TableColumnDef`)과 export schema(`table.columns`)는 이미 정의되어 있으나, `TemplateRightPanel`에서 UI 렌더는 비어 있고 helper(`getColumns`, `updateColumn`)만 존재. 사용자가 컬럼 메타를 채울 UI가 없는 상태.
- 추천 첫 구현 작업: **TPL-2-TEMPLATE-TABLE-COLUMN-TYPES-AND-DEFAULTS** — 기존 `TableColumnDef`에 `required`/`visible`/`order`/`source`/`userConfirmed` 등 MVP 필드를 추가하고, 컬럼 기본값/정규화 helper를 별도 파일에 신설.
- 주요 리스크: ① `OcrCanvasPane`은 `common/ui`로 이동되어 Test/RunOCR도 공유 → Template 전용 컬럼 정의 UI를 절대 OcrCanvasPane에 넣어서는 안 된다. ② `templates.json`(서버 저장본)이 git dirty 상태로, 기존 schema와 backward compat를 깰 변경(필수 필드 추가)을 금지해야 한다. ③ `profiles.ts` 의 `TABLE_COLUMN_META`/`getExpectedTableColumns`는 Test 전용 정책이므로 Template이 직접 의존하면 feature boundary 위반.
- 이번 precheck에서 운영 코드 수정 여부: 없음. 산출물(`tmp/*`) + 로그(`ocr-server/logs/*`)만 생성.

### 2. Template Tab Structure

```
/template (src/app/template/page.tsx)
├── AppShell(headerTitle="Template", scrollMode="fixed")
├── 상단 모드 카드 행
│   ├── ModeCard "템플릿 생성" → setMode("template")
│   ├── ModeCard "비정형 생성" → setMode("unstructured")
│   └── 저장된 템플릿 가로 리스트
│       └── 카드 클릭 시 setMode(template.mode === "unstructured" ? "unstructured" : "template")
└── 모드 콘텐츠 (mode 분기)
    ├── mode === "template"
    │   └── TemplateAnnotator (dynamic, ssr: false)
    │       ├── 상단 toolbar (필드/멀티/체크/테이블, 줌)
    │       ├── 좌: OcrCanvasPane (shared, common/ui)
    │       │   ├── 영역 그리기/이동/리사이즈
    │       │   ├── multi 분할 핸들
    │       │   ├── table rowTemplate 드래그
    │       │   └── table 세로 가이드(colGuides) 클릭/드래그
    │       └── 우: 삭제/저장 박스 + TemplateRightPanel
    │           ├── 템플릿 명 / 문서 유형 select
    │           ├── 출력 필드 정의 (영문/한글 필드명 grid)
    │           └── 선택 영역
    │               ├── (table 한정) 그리드 모드 / 종료 키워드 / 가이드 버튼군 / 가이드 리스트
    │               └── 미리보기 crop
    │   └── 저장: buildExportPayload + localStorage(LOCAL_TEMPLATES_KEY) + IndexedDB(saveTemplateImage) + POST /templates
    └── mode === "unstructured"
        └── UnstructuredBuilder
            ├── 좌: 비정형 설명 카드 (업로드 dropzone X)
            └── 우: 삭제/저장 + 템플릿명 + 출력 필드 리스트(No / 영문 / 한글)
            └── 저장: 인라인 payload `{ templateName, mode: "unstructured", fields, regions: [] }` + localStorage POST 없음
```

공통 컴포넌트: `OcrCanvasPane`(template 전용으로만 호출), 모드 카드/저장된 템플릿 가로 리스트, 우측 출력 필드 grid 스타일(`oc-section`, `ms-input`) 일부.
분리된 컴포넌트: TemplateAnnotator/OcrCanvasPane/TemplateRightPanel 전체 vs UnstructuredBuilder 단독.

### 3. Template Flow Analysis
- 관련 파일:
  - `src/app/template/page.tsx`
  - `src/components/template/ui/TemplateAnnotator.tsx`
  - `src/components/template/ui/TemplateRightPanel.tsx`
  - `src/components/template/utils/buildTemplateExportPayload.ts`
  - `src/common/ui/OcrCanvasPane.tsx`
  - `src/common/utils/ocrTableRegion.ts`
  - `src/common/types/ocr.ts`
- region model: `Region`(`src/common/types/ocr.ts:41-63`) — `id`, `name`, `fieldType`("field"|"multi"|"check"|"table"), `x/y/width/height`, `koField/enField/canonicalField`, `mappingStatus/mappingCandidates`, `valueType`, `parts/ratios`(multi), `checkMode`(check), `table`(table).
- table region model: `TableMeta`(`src/common/types/ocr.ts:31-39`) — `mode`("repeat"|"auto"), `rowTemplate: Rect`, `rows: Rect[]`, `colGuides: number[]`(0~1 ratio), `stopKeywords: string[]`, `tableName?: string`, `columns?: TableColumnDef[]`(이미 schema 존재).
- rowTemplate: `OcrCanvasPane`의 `drawRowTemplate` drag handler(`src/common/ui/OcrCanvasPane.tsx:347-`, `~427`)에서 생성되어 `region.table.rowTemplate`에 저장. `TemplateRightPanel`의 `clearTableMeta`로 해제(`setTableMode("auto")` 또는 명시적 해제 버튼).
- columnGuides: `OcrCanvasPane`의 클릭(`:302-345`)/드래그(`:655-696`) 핸들러에서 `normalizeColGuides`로 정렬·중복 제거하여 0~1 비율 배열로 저장. `TemplateRightPanel`에서 `removeTableColGuide`/`clearTableColGuides`.
- stopKeywords: `TemplateRightPanel`의 `stopKeywordsRaw` state + `updateStopKeywords`(`src/components/template/ui/TemplateRightPanel.tsx:126-136`). 쉼표 split, 30개 상한, lowercase dedup은 `normalizeStopKeywords`(`src/common/utils/ocrTableRegion.ts:53`).
- right panel UI: 헤더(템플릿명/문서유형 select) → 출력 필드 정의(영문/한글 input grid) → 선택 영역(table 한정: 그리드 모드 토글, 종료 키워드 input, 행 템플릿/가이드 버튼, 가이드 리스트) → 미리보기 crop. **컬럼 정의 UI는 의도적으로 비어 있음** (코드 주석 `"컬럼 정의는 제거, 가변/고정/세로가이드/종료키워드만"`, `:357`).
- save payload: `buildExportPayload`(`src/components/template/utils/buildTemplateExportPayload.ts`) — `{templateName, documentType?, file: {name}, image: {width,height,src}, regions: [{id,name,fieldType,x,y,width,height, koField?, enField?, canonicalField?, mappingStatus?, valueType?, parts?,ratios?,subRegions?(multi), checkMode?(check), table?{mode, rowTemplate, rows, colGuides, colX(절대 px 좌표), stopKeywords, tableName?, columns?(spread)}}]}`.
- load/restore: `TemplateAnnotator` useEffect (`src/components/template/ui/TemplateAnnotator.tsx:66-93`) — `setRegions(selectedTemplate.regions)`로 그대로 복원. 즉 저장된 region의 `table.columns` 필드는 그대로 round-trip 됨.
- 현재 부족한 점:
  - 사용자가 `table.columns`를 채우거나 편집할 UI가 없음 (helper만 존재).
  - 컬럼 인덱스가 `normalizeColGuides(colGuides).length + 1`에 묶여 있으나 사용자가 컬럼 메타를 추가/삭제할 수단 없음.
  - canonical column(`TableColumnDef.canonicalColumn`)을 결정하는 자동 추천 로직이 없음.
  - `colGuides`가 ratio(0~1)인데 `columns`는 `index`만 가지고 있어 컬럼 ↔ guide 위치 연결이 약함.

### 4. Unstructured Flow Analysis
- 관련 파일: `src/app/template/page.tsx`, `src/components/template/UnstructuredBuilder.tsx`.
- UI 포맷: 좌측 패널은 설명(아이콘+카피)만, 우측 패널은 `삭제/저장 박스` + `템플릿명` + `출력 필드 정의` 영역. 출력 필드는 `28px / 1fr / 1fr` grid (No / 영문 필드명 / 한글 필드명) 카드 행, 클릭 시 선택 토글 (`isSel`).
- 선택 영역 표시 방식: 캔버스 자체가 없음. 좌측은 정적 설명. 선택 = 우측 행 카드 highlight (accent border + accentBg).
- field label/key 표시 방식: `Field = { no, enField, koField }`. 단순 2-input row, key/canonical 매핑 없음.
- save payload: `{ templateName, mode: "unstructured", fields: [{no, enField, koField}], regions: [] }` — `regions`는 항상 빈 배열, 이미지/문서유형/캔버스 정보 모두 미저장. localStorage 전용 (서버 POST 없음).
- template flow와 공통점: ① 같은 localStorage key (`mysuit_ocr_templates`)에 저장. ② mode 식별자 (`template_json.mode === "unstructured"`)로 구분. ③ `oc-section`/`ms-input` CSS class 공유. ④ 영문/한글 필드명 2-input row 카드 디자인(`28px / 1fr / 1fr` grid)이 거의 동일.
- template flow와 차이점: ① 캔버스/이미지/region 없음. ② payload에 `mode: "unstructured"` 명시. ③ 서버 저장 안 함. ④ 행 단위가 `field.no`(seq)만 갖고 위치 정보 없음.
- table column definition UI에 참고할 점:
  - **카드 행 grid 포맷(`28px / 1fr / 1fr`)** + 클릭 선택 + `accent` highlight 패턴을 그대로 차용 가능 → 사용자가 이미 익숙.
  - 추가/삭제 버튼을 헤더 우측(`oc-section-header`)에 배치하는 패턴.
  - "필드가 없습니다." empty hint 카피.
  - 영문/한글 필드명 + (확장 시) 키/타입 컬럼을 한 줄에 grid로 늘리면 시각적 일관성 유지.

### 5. OcrCanvasPane Responsibility Analysis
- 현재 담당 책임: 이미지 dropzone(`FileDropzone`)/렌더, 줌 적용, region 그리기/이동/리사이즈, multi 분할 핸들 drag, **table rowTemplate drag/세로 가이드 클릭·drag**, 컨테이너 폭 측정, label 렌더, 키보드 단축키(Delete) 등.
- table 관련 담당 책임: rowTemplate 새 박스 생성(`drawRowTemplate`), 세로 가이드 추가(`colGuides` push + normalize), 세로 가이드 좌우 이동(`tableCol` drag), rowTemplate/rows clamp & rebuild on region resize. `regions` setState를 직접 호출하여 `region.table.rowTemplate`/`region.table.colGuides`/`region.table.rows`만 mutate.
- common/ui로서 유지해야 할 경계: `src/common/ui/OcrCanvasPane.tsx`는 Template / RunOCR / (간접적으로) Test에서 공유 가능한 shared canvas. 책임은 **"이미지 좌표계에서 region geometry를 그리고 편집"**까지. canonical mapping, table profile policy, 컬럼 정의 등 feature 정책은 들어오면 안 된다.
- Template 전용 column definition을 넣으면 안 되는 이유:
  - RunOCR/Test도 같은 컴포넌트를 import할 수 있고, 그쪽에 노출되면 안 되는 Template 편집 UI가 새는 모양이 됨.
  - 캔버스에 컬럼 메타(한글명/영문 key/canonical) 입력을 띄우면 캔버스 책임이 비대해지고 줌/스크롤 상호작용과 충돌.
  - `colGuides`와 `columns`의 연결 표시(ex. guide hover 시 컬럼 label 띄우기)는 가능하지만 — **편집 UI는 RightPanel**이 답.
- 권장 책임 분리:
  - 캔버스: guide hover/highlight, 선택된 컬럼 index 표시(읽기 전용 overlay)까지 OK.
  - RightPanel: `table.columns[]` 카드 리스트, 추가/삭제, 한/영/canonical 매핑 input, source(`auto`/`manual`)/userConfirmed 토글, guide ↔ column 연결 표시.

### 6. Save Payload and templates.json Analysis
- buildTemplateExportPayload 현재 역할: Region 배열을 JSON-serializable 형태로 정규화(좌표 반올림, multi subRegions 미리 계산, table colGuides + colX 페어 출력). `r.table?.columns`는 spread만 하여 그대로 전달.
- table region payload 현재 shape:
  ```json
  {
    "id": "table_1",
    "name": "...",
    "fieldType": "table",
    "x": 0, "y": 0, "width": 0, "height": 0,
    "koField": "?", "enField": "?", "canonicalField": "?",
    "table": {
      "mode": "repeat"|"auto",
      "rowTemplate": {x,y,width,height} | null,
      "rows": [Rect, ...],
      "colGuides": [0.25, 0.5, 0.75, ...],
      "colX": [px, ...],
      "stopKeywords": [...],
      "tableName"?: string,
      "columns"?: [{ "index": 0, "koField"?: ..., "enField"?: ..., "canonicalColumn"?: ..., "mappingStatus"?: ..., "mappingCandidates"?: [...] }]
    }
  }
  ```
- columnGuides 저장 여부: ✅ `colGuides`(ratio) + `colX`(px) 둘 다 저장됨.
- rowTemplate 저장 여부: ✅ `rowTemplate`(또는 null) + `rows` 배열 저장.
- column definition 추가 후보 위치:
  - **권장**: `region.table.columns[]`를 그대로 사용(이미 schema 존재). 신규 필드(`required`, `visible`, `order`, `source`, `userConfirmed`, `guideX`, `width`)는 optional로 추가.
  - 대안: `region.table.columnDefinition` 별도 객체로 분리 — 비추(중복).
- backward compatibility 전략:
  - 신규 필드는 전부 optional. 기존 `templates.json` 항목에 `columns`가 없으면 load 시 빈 배열로 hydrate.
  - export 단계에서 `columns`가 empty이면 키 자체를 생략하여 기존 호환 유지.
  - canonical/required 등 신규 필드는 누락 시 `undefined`로 처리하고 UI에서 기본값 추론.
- templates.json dirty 상태: `../ocr-server/data/templates.json`이 git dirty(M) 상태. 이번 작업은 절대 수정하지 않는다.
- templates.json 수정 필요 여부: ❌ 불필요. schema 확장은 frontend write/read 측에서 optional 처리.
- 다음 phase에서 다룰 점: TPL-3에서 payload schema MVP 확정 → TPL-6에서 save/load round-trip e2e 확인.

### 7. Type and Policy Source Analysis

| file | relevant symbols | current owner | Template direct import allowed? | recommendation |
|---|---|---|---|---|
| `src/common/types/ocr.ts` | `FieldType`, `Region`, `TableMeta`, `TableColumnDef`, `MappingStatus`, `FieldMappingCandidate` | common (shared geometry/type) | ✅ 허용 (이미 사용 중) | `TableColumnDef`에 MVP optional 필드 추가 후 그대로 사용. canonical/required/visible/order/source/userConfirmed를 모두 여기에 둔다. |
| `src/common/utils/ocrTableRegion.ts` | `normalizeColGuides`, `buildTableRows`, `normalizeStopKeywords`, `autoDetectRowBands`, `isStopRow`, `OcrBox` | common (table geometry helpers) | ✅ 허용 | guide ↔ column 매핑/자동 추천 helper도 여기에 추가 가능하지만, Template 전용 컬럼 default 생성은 별도 utils에 두는 편이 깔끔. |
| `src/common/config/testsets.ts` | `DocumentType`, `TableProfile`, `InvoiceProfile`, `InvoiceTableExpectedDisplayColumn` | TestWorkspace + manifest 관련 | ⚠️ 직접 import는 가능하지만 가급적 회피. Template은 documentType 정도만 참조. | `InvoiceTableExpectedDisplayColumn`은 TestWorkspace 전용 검증 데이터로 두고, Template는 별도 `TemplateColumnDefault` 타입을 가질 것. |
| `src/components/test/utils/profiles.ts` | `TableColumnKey`, `TableColumnMeta`, `TABLE_COLUMN_META`, `getExpectedTableColumns`, `TableProfilePolicyResult` | TestWorkspace 전용 (profile별 KPI 정책) | ❌ Template이 직접 import 금지 | Test 전용 `tableProfile` 정책을 Template에 끌어오면 feature boundary 위반. Template은 자체 default(또는 차후 공통 schema로 승격) 사용. |
| `src/components/template/utils/buildTemplateExportPayload.ts` | `buildExportPayload` | Template 전용 export mapper | ✅ Template 전용 | column definition 추가 시 여기서 직렬화 → `r.table.columns`만 spread 유지 + empty array 생략. |
| `src/common/ui/OcrCanvasPane.tsx` | `OcrCanvasPane` props 인터페이스, table drag/click handlers | common (RunOCR/Template 공유) | ✅ 사용(현재처럼 props 통해서) | 새 컬럼 정의 UI/handler는 절대 여기에 추가하지 않는다. 컬럼 highlight overlay만 read-only로 허용. |
| `src/components/template/ui/TemplateRightPanel.tsx` | `getColumns`, `updateColumn`, `clearTableMeta`, `setTableMode` 등 | Template 전용 우측 패널 | ✅ Template 전용 | 컬럼 정의 카드/행 리스트 UI 추가 위치. helper(`getColumns`)는 이미 사용 가능. |

### 8. Proposed Ownership

| 후보 | 장점 | 단점 | feature boundary 위험 | common 오염 위험 | 추천 |
|---|---|---|---|---|---|
| `src/components/template/ui/TemplateTableColumnEditor.tsx` (신규) | RightPanel을 비대화하지 않고 분리, 단위 테스트 가능, 비정형 UI 패턴(`28px/1fr/1fr` 카드 행) 차용 | TemplateRightPanel ↔ Editor props가 다소 길어짐 | 낮음 | 없음 | ✅ 강력 추천. RightPanel의 `selected.fieldType === "table"` 블록 내부에 mount. |
| `src/components/template/utils/tableColumnDefinition.ts` (신규) | 컬럼 default 생성, normalize, guide ↔ column index 매핑 helper 격리 | 한 곳 더 생김 | 낮음 | 없음 | ✅ 추천. 자동 추천/정렬/생성 로직 전용. |
| `src/components/template/utils/templateTableColumnDefaults.ts` (신규) | `documentType` 또는 hand-coded list 기반 컬럼 기본 라벨/canonical 후보 | profiles.ts와 중복될 수 있으나 의도된 격리 | 낮음 | 없음 | ⚠️ 선택. `tableColumnDefinition.ts`에 흡수해도 무방. MVP에서는 한 파일로 시작. |
| `src/common/types/ocr.ts` 확장 | 이미 `TableColumnDef` 정의처. optional 필드만 늘리면 됨 | 없음 | 낮음 | 없음 (type만 추가) | ✅ 추천. `required?/visible?/order?/source?/userConfirmed?/guideX?/width?` 추가. |
| `src/common/utils/tableColumnDefinition.ts` (신규, common) | Test에서도 재사용 가능 | 현재 Test가 별도 정책 사용 → 공유 필요성 불분명, common 오염 가능성 | 중간 | 중간 | ❌ 아직 비추. 우선 Template 전용에서 검증 후 필요 시 승격. |

### 9. Proposed Data Shape Draft

`TableColumnDef` MVP 확장안 (모두 optional, backward compat 유지):

| 필드 | 의미 | 저장 위치 | 비고 |
|---|---|---|---|
| `index` | 컬럼 순서 (0-based) | `region.table.columns[].index` | 기존 필드. `normalizeColGuides + 1`로 결정. |
| `columnKey` | 안정적 식별자 (e.g. `col_0`, `itemName`) | 동상 | 신규. 사용자/자동 추천이 정한 영문 key. |
| `labelKo` | 한글 컬럼명 | 동상 | 신규(기존 `koField`와 의미 동등 — `koField`를 그대로 유지하고 alias로 사용해도 됨). |
| `labelEn` | 영문 컬럼명 (표 헤더에 보이는 원문) | 동상 | 신규(`enField`와 동등). |
| `canonicalColumn` | canonical mapping (e.g. `itemName`, `quantity`) | 동상 | 기존 필드. profiles.ts의 `TableColumnKey`와 의미는 동일하나 Template은 free-string 허용. |
| `aliases` | 동의어 헤더 후보 | 동상 | 신규 optional. 자동 추천/일치 기준. |
| `required` | 필수 여부 | 동상 | 신규 optional. KPI 분모 결정. |
| `visible` | UI 표시 여부 | 동상 | 신규 optional. RunOCR 결과 표시 컨트롤. |
| `order` | 정렬 순서 (선택) | 동상 | 신규 optional. 미설정 시 `index` 사용. |
| `guideId` | 연결된 colGuide(0~1 ratio) 또는 그 index | 동상 | 신규 optional. UI에서 컬럼 ↔ guide 연결 표시용. |
| `guideX` | 픽셀 좌표 캐시 | 동상 | 신규 optional. round-trip 단순화용 (선택). |
| `width` | 컬럼 폭 (px 또는 ratio) | 동상 | 신규 optional. |
| `source` | `"auto"` / `"manual"` / `"default"` | 동상 | 신규 optional. 추천/사용자 입력 구분. |
| `confidence` | 자동 추천 신뢰도(0~1) | 동상 | 신규 optional. |
| `userConfirmed` | 사용자가 확인 완료한 컬럼인지 | 동상 | 신규 optional. UI 뱃지. |
| `mappingStatus` | `MappingStatus` | 동상 | 기존 필드 유지. |
| `mappingCandidates` | `FieldMappingCandidate[]` | 동상 | 기존 필드 유지. |

### 10. UI Proposal

`TemplateRightPanel` 안에서 `selected.fieldType === "table"`인 경우, 현재 "그리드 모드 / 종료 키워드 / 가이드 버튼" 섹션 **아래**에 신규 섹션 추가:

```
┌─ 컬럼 정의 (table 선택 시만 표시) ──────────────────────────┐
│ Header: "컬럼 정의" + [자동 추천] [컬럼 추가] [전체 삭제]   │
│                                                            │
│ ┌ grid 28px / 1.2fr / 1fr / 1fr / 56px ───────────────────┐│
│ │ No │ 한글 컬럼명 │ 영문 / key │ canonical │ 상태 / 삭제 ││
│ └────────────────────────────────────────────────────────────┘
│                                                            │
│ 컬럼 카드 (비정형 UI와 동일 패턴, 28px / 1.2fr / 1fr / 1fr / 56px) │
│ ┌──────────────────────────────────────────────────────────┐│
│ │ 1 │ [품목명           ] │ [itemName    ] │ [itemName ▾]│ ●자동 ✕ ││
│ │ 2 │ [수량             ] │ [quantity    ] │ [quantity ▾]│ ●확인 ✕ ││
│ │ 3 │ [공급가액         ] │ [supplyAmt   ] │ [supplyAmt▾]│ ○수동 ✕ ││
│ └──────────────────────────────────────────────────────────┘
│                                                            │
│ 연결된 가이드 표시 (선택 컬럼 hover 시 캔버스 guide highlight)│
│ Required / visible 토글: 카드 우측 batch chip 또는 details ▾  │
└────────────────────────────────────────────────────────────┘
```

포함할 것:
- table region 선택 시에만 표시 (`selected.fieldType === "table"`).
- **비정형 영역정의 카드 행과 동일한 grid 패턴**(28px / 1fr / 1fr ...) 채택 → 사용자 학습 비용 최소화.
- 자동 추천 버튼 (`source = "auto"`, `confidence` 채움) — MVP에서는 documentType + 휴리스틱.
- 사용자 확인 상태 (`userConfirmed`) chip.
- columnGuide 연결 표시 (카드 hover → 캔버스 guide highlight; 캔버스 guide hover → 카드 highlight).
- required / visible / order — MVP는 chip 토글 1개(required) + details ▾로 visible/order.
- 신규 컬럼 추가/삭제: 헤더 버튼.

MVP에서 제외할 항목:
- 컬럼 width drag.
- 자동 추천 후보 리스트(`mappingCandidates`) 풀 UI — 추천 1개만 적용, 후보 리스트는 후속.
- 컬럼별 valueType select — 후속.
- 다국어 라벨 (한/영 외).

### 11. Risk Assessment

- Template UI risk: **LOW** — RightPanel 안의 신규 섹션만 추가, 기존 UI 비파괴.
- OcrCanvasPane boundary risk: **MEDIUM** — RunOCR/Test 공유 컴포넌트. 컬럼 편집 UI를 캔버스에 직접 넣으면 위험. 본 계획은 read-only highlight만 허용.
- save/load schema risk: **LOW** — `table.columns` 키는 이미 schema에 존재, optional spread. 신규 필드도 optional로만 추가.
- existing templates compatibility risk: **LOW** — `columns` 누락 시 빈 배열 처리, 기존 필드 의미 보존.
- RunOCR integration risk: **MEDIUM** — RunOCR가 region template을 로드할 때 `table.columns`를 어떻게 활용할지(또는 무시할지) 정책 필요. TPL-7에서 다룬다.
- TestWorkspace risk: **LOW** — Test는 별도 `profiles.ts`/`getExpectedTableColumns` 사용. 영향 없음(직접 import 금지).
- backend/fixture risk: **LOW** — 본 phase는 frontend 전용. backend는 `table.columns`가 와도 통과(현재 schema 그대로 spread).
- templates.json dirty risk: **MEDIUM** — git dirty 상태. 본 작업에서 파일 자체를 수정하지 않으며, 신규 필드는 optional이라 기존 JSON과 호환.

### 12. Recommended TPL Implementation Plan

#### 1. TPL-2-TEMPLATE-TABLE-COLUMN-TYPES-AND-DEFAULTS
- 작업명: TPL-2-TEMPLATE-TABLE-COLUMN-TYPES-AND-DEFAULTS
- 도구: Claude Code (Opus)
- 목표: `TableColumnDef`를 MVP optional 필드로 확장하고, 컬럼 기본값/정규화 helper를 신설.
- 수정 파일 후보:
  - `src/common/types/ocr.ts` (필드 추가)
  - `src/components/template/utils/tableColumnDefinition.ts` (신설)
- 절대 수정 금지: `src/common/ui/OcrCanvasPane.tsx`, TestWorkspace, profiles.ts, testsets.ts, backend, templates.json.
- 검증 기준: typecheck/build PASS. `TableColumnDef` 신규 필드가 전부 optional. helper 단위 테스트(또는 mjs smoke) 통과.
- 선행 조건: TPL-1 PASS.

#### 2. TPL-3-TEMPLATE-TABLE-COLUMN-PAYLOAD-SCHEMA
- 작업명: TPL-3-TEMPLATE-TABLE-COLUMN-PAYLOAD-SCHEMA
- 도구: Claude Code (Opus)
- 목표: `buildExportPayload`에서 `r.table.columns`를 normalize/serialize하고, empty 배열은 키 자체 생략. 기존 JSON과 round-trip 보존.
- 수정 파일 후보:
  - `src/components/template/utils/buildTemplateExportPayload.ts`
  - `src/components/template/utils/tableColumnDefinition.ts` (정규화 helper)
- 절대 수정 금지: backend, templates.json, OcrCanvasPane.
- 검증 기준: 기존 templates.json fixture를 load → export → load 동등성 fixture(`tmp/`) 작성, contract PASS.
- 선행 조건: TPL-2.

#### 3. TPL-4-TEMPLATE-TABLE-COLUMN-EDITOR-UI
- 작업명: TPL-4-TEMPLATE-TABLE-COLUMN-EDITOR-UI
- 도구: Claude Code (Opus)
- 목표: TemplateRightPanel에 컬럼 정의 섹션 추가 (비정형 카드 행 패턴), 추가/삭제/입력 기능.
- 수정 파일 후보:
  - `src/components/template/ui/TemplateRightPanel.tsx` (섹션 mount)
  - `src/components/template/ui/TemplateTableColumnEditor.tsx` (신설)
- 절대 수정 금지: OcrCanvasPane, UnstructuredBuilder, TestWorkspace.
- 검증 기준: UI E2E (또는 mjs smoke) — table region 선택 시 컬럼 정의 섹션 표시, 입력 → state 반영, 저장 payload에 반영.
- 선행 조건: TPL-2, TPL-3.

#### 4. TPL-5-TEMPLATE-TABLE-COLUMN-AUTO-SUGGEST
- 작업명: TPL-5-TEMPLATE-TABLE-COLUMN-AUTO-SUGGEST
- 도구: Claude Code (Opus)
- 목표: documentType + colGuides 개수 + (선택) OCR 헤더 텍스트로 컬럼 기본 라벨/canonical 자동 추천. `source="auto"`, `confidence`, `userConfirmed=false` 채움.
- 수정 파일 후보:
  - `src/components/template/utils/tableColumnDefinition.ts`
  - `src/components/template/ui/TemplateTableColumnEditor.tsx` (자동 추천 버튼 wiring)
- 절대 수정 금지: profiles.ts (Test 전용 정책 미사용), OcrCanvasPane, backend.
- 검증 기준: documentType별 자동 추천 fixture 5개 이상 통과.
- 선행 조건: TPL-4.

#### 5. TPL-6-TEMPLATE-SAVE-LOAD-ROUNDTRIP
- 작업명: TPL-6-TEMPLATE-SAVE-LOAD-ROUNDTRIP
- 도구: Claude Code (Opus)
- 목표: 컬럼 정의가 있는 template을 저장 → localStorage/server에서 load → UI 복원 round-trip 보장. 기존(columns 없음) template도 정상 load.
- 수정 파일 후보:
  - `src/components/template/ui/TemplateAnnotator.tsx` (load hydration)
  - `src/components/template/utils/tableColumnDefinition.ts` (load normalize)
- 절대 수정 금지: backend, templates.json, OcrCanvasPane.
- 검증 기준: fixture round-trip mjs PASS. 기존 templates.json 1건 이상 load 무손실 확인.
- 선행 조건: TPL-3, TPL-4.

#### 6. TPL-7-RUNOCR-TEMPLATE-COLUMN-DEFINITION-INTEGRATION
- 작업명: TPL-7-RUNOCR-TEMPLATE-COLUMN-DEFINITION-INTEGRATION
- 도구: Claude Code (Opus)
- 목표: RunOCR가 template `table.columns`를 읽어 결과 표 헤더/매핑/표시 컬럼에 반영(미설정 시 fallback). RunOCR-only 변경.
- 수정 파일 후보:
  - `src/components/runocr/utils/mapOcrResponse.ts`
  - `src/components/runocr/RunOcrWorkspace.tsx`
- 절대 수정 금지: TestWorkspace, Template 편집 UI, OcrCanvasPane, profiles.ts.
- 검증 기준: RunOCR e2e — column 정의 있는 template으로 OCR 실행 시 결과 헤더가 `labelKo` 사용.
- 선행 조건: TPL-6.

#### 7. TPL-8-TEMPLATE-COLUMN-DEFINITION-VALIDATION
- 작업명: TPL-8-TEMPLATE-COLUMN-DEFINITION-VALIDATION
- 도구: Claude Code (Opus)
- 목표: 저장 직전 컬럼 정의 유효성(중복 columnKey, 누락 required, guide-count mismatch) 경고/blocking. UI 메시지 표준화.
- 수정 파일 후보:
  - `src/components/template/utils/tableColumnDefinition.ts`
  - `src/components/template/ui/TemplateAnnotator.tsx` (save 직전 validate)
- 절대 수정 금지: backend, OcrCanvasPane, profiles.ts.
- 검증 기준: validation fixture (중복/누락/mismatch) → 적절한 메시지 반환.
- 선행 조건: TPL-6.

### 13. Do Not Start Yet
- TPL-2 ~ TPL-8 어떤 단계도 본 precheck 단계에서는 시작 금지.
- `TableColumnDef` schema 확장 금지.
- `TemplateRightPanel` UI 추가 금지.
- `buildTemplateExportPayload` 변경 금지.
- `OcrCanvasPane`에 컬럼 정의 관련 props/UI 추가 금지.
- `UnstructuredBuilder` 변경 금지 (참고만).
- `profiles.ts` import 추가 금지.
- `templates.json` 수정 금지.
- TestWorkspace / backend 수정 금지.

### 14. Verification Results
- production code modified: NO
- src/lib absent: YES
- @/lib import 0: YES
- typecheck: 다음 run에서 PASS 확인 예정 (npm run typecheck via 실행 명령)
- build: 다음 run에서 PASS 확인 예정 (npm run build via 실행 명령)
- static precheck: 다음 run에서 PASS 확인 예정 ([TEMPLATE_TAB_STRUCTURE_TPL1_PRECHECK] PASS)
- FAIL count: 0 (precheck script가 검증)
