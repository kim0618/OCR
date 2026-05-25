## TPL-2 Unstructured Info/Table Definition Precheck

### 1. Summary
- src/lib cleanup status: 완료. `src/lib` absent, `@/lib/*` import 0건, 상대경로 lib import 0건. 이전 TPL-1 결과 그대로 유지.
- 현재 비정형 구조: [UnstructuredBuilder.tsx](mysuit-ocr/src/components/template/UnstructuredBuilder.tsx)의 단일 `fields: { no, enField, koField }[]` 배열만 관리. 캔버스/이미지/region 없음.
- 거래명세서 지원에 부족한 점: ① 반복되는 표 컬럼을 표현할 수단 없음 (모든 필드를 1-value 필드로 취급). ② info 영역(공급자/공급받는자/합계) ↔ table 영역(품목 row 반복) 의미 분리 없음. ③ RunOCR `mapOcrResponse`도 `template.fields`를 1-value lookup으로만 매핑.
- 추천 UI 방향: **방식 B (버튼 두 개 분리)** — 현재 헤더에 `[추가]` + `[삭제]` 위치에 `[+ 영역 정의]` `[+ 테이블 정의]` `[삭제]`로 명시 분리. info/tables 자료구조와 1:1 대응되어 사용자 학습/디버깅 모두 유리.
- 추천 data shape: **후보 3 (legacy fields + info/tables adapter)**. `{ mode: "unstructured", info: UnstructuredInfoField[], tables: UnstructuredTableDef[], fields?: legacyFields[] }` — 신규 template은 `info`+`tables`로 저장하고, 기존 `fields` 키는 load 시 → `info`로 normalize, save 시 legacy reader 호환을 위해 `info`를 동시에 `fields`로도 직렬화.
- 구현 진입 가능 여부: ✅ 가능. UnstructuredBuilder만 수정하면 되고, OcrCanvasPane/TestWorkspace/backend는 무관. RunOCR `mapOcrResponse`는 `info` 우선 + `fields` fallback의 thin adapter로 통일.
- 추천 첫 구현 작업: **TPL-3-UNSTRUCTURED-INFO-TABLE-TYPES-AND-HELPERS** — `src/components/template/utils/unstructuredDefinition.ts` 신설 + 타입/정규화 helper만. UI/payload는 다음 단계.
- 이번 precheck에서 운영 코드 수정 여부: 없음. 산출물(`tmp/*`) + 로그(`ocr-server/logs/*`)만 생성.

### 2. Current Unstructured Flow
- route/page: [src/app/template/page.tsx](mysuit-ocr/src/app/template/page.tsx)
- mode 분기: `useState<Mode>("template")`에서 `Mode = "template" | "unstructured"` ([page.tsx:17](mysuit-ocr/src/app/template/page.tsx#L17), [page.tsx:91](mysuit-ocr/src/app/template/page.tsx#L91)). 모드 카드 클릭(`handleModeChange`)으로 전환되고 `mode === "template"`이면 `TemplateAnnotator` 렌더, 아니면 `UnstructuredBuilder` 렌더 ([page.tsx:239-252](mysuit-ocr/src/app/template/page.tsx#L239-L252)).
- main component: [src/components/template/UnstructuredBuilder.tsx](mysuit-ocr/src/components/template/UnstructuredBuilder.tsx) (311 lines).
- state:
  - `templateName: string`
  - `fields: Field[]` where `Field = { no: number, enField: string, koField: string }` ([UnstructuredBuilder.tsx:6-10](mysuit-ocr/src/components/template/UnstructuredBuilder.tsx#L6-L10))
  - `selectedNo: number | null`
- fields structure: 단일 평면 배열. `no`는 sequence(insertion order +1). `enField`/`koField`는 free string. canonical/required/visible/order 등 메타 없음.
- add/delete behavior:
  - `addField()`: `nextNo = max(fields[].no) + 1`, append `{ no: nextNo, enField: "", koField: "" }` ([UnstructuredBuilder.tsx:27-30](mysuit-ocr/src/components/template/UnstructuredBuilder.tsx#L27-L30))
  - 삭제: `selectedNo`로 한 행 제거 ([UnstructuredBuilder.tsx:234-244](mysuit-ocr/src/components/template/UnstructuredBuilder.tsx#L234-L244))
- save behavior: `handleSave()` ([UnstructuredBuilder.tsx:45-82](mysuit-ocr/src/components/template/UnstructuredBuilder.tsx#L45-L82))
  - 검증: `templateName` non-empty, `fields.length > 0`
  - payload: `{ template_id: selectedTemplateId || "LOCAL-${Date.now()}", template_name, template_json: { templateName, mode: "unstructured", fields, regions: [] }, updated_at }`
  - localStorage(`LOCAL_TEMPLATES_KEY = "mysuit_ocr_templates"`)에만 저장, 서버 POST 없음
  - `window.dispatchEvent("mysuit-ocr-template-saved")` 발행
- load behavior: useEffect ([UnstructuredBuilder.tsx:36-43](mysuit-ocr/src/components/template/UnstructuredBuilder.tsx#L36-L43)) — `selectedTemplate.templateName`/`.template_name` 읽고 `Array.isArray(selectedTemplate.fields)`이면 `setFields(selectedTemplate.fields)`.
- localStorage/server behavior: localStorage에만 저장. 서버 `/templates` POST 없음. Template flow는 동일 키에 저장하면서 서버 POST도 수행(`TemplateAnnotator.saveTemplateJson`).
- 현재 한계:
  1. 반복 행 표(품목표)를 표현할 자료구조 없음.
  2. info 필드와 (가상의) table 컬럼을 사용자가 시각적으로 구분할 수 없음.
  3. RunOCR mapOcrResponse는 `template.fields`만 single-value lookup으로 매핑 ([mapOcrResponse.ts:117-145](mysuit-ocr/src/components/runocr/utils/mapOcrResponse.ts#L117-L145)) — table row 결과를 받아도 표시할 수 없음.
  4. canonical/required/visible/order 같은 메타가 없어 KPI/검증 정책을 붙일 수 없음.
  5. `fields`는 backward compat 잠금 — 키를 바꾸려면 마이그레이션 필요.

### 3. Current UI Analysis
- 출력 필드 정의 영역: 우측 패널, `oc-section` ([UnstructuredBuilder.tsx:229-306](mysuit-ocr/src/components/template/UnstructuredBuilder.tsx#L229-L306))
- 현재 버튼:
  - 헤더 우측: `[추가]` `[삭제]` (`oc-section-header` 내) — `addField` / `selectedNo` 기준 삭제
  - 상단 박스: `[삭제]` `[저장]` 또는 `[수정]` — template 자체 저장/삭제/초기화
- 현재 grid columns: `28px / 1fr / 1fr` — `No / 영문 필드명 / 한글 필드명` ([UnstructuredBuilder.tsx:250-261](mysuit-ocr/src/components/template/UnstructuredBuilder.tsx#L250-L261))
- empty state: `"필드가 없습니다."` muted 텍스트 ([UnstructuredBuilder.tsx:264](mysuit-ocr/src/components/template/UnstructuredBuilder.tsx#L264))
- save/delete buttons: 상단 박스에 우측 정렬, accent 컬러 저장 버튼.
- 화면 배치: `[좌: 비정형 설명 dropzone-style 카드 + 3-card 보조설명] [우: 저장박스 + 템플릿명 + 출력 필드 정의]`
- 거래명세서 지원 관점에서 부족한 점:
  - 표(품목표) 입력 영역 없음 — 사용자가 "어디에 표 컬럼을 정의해야 하는지" 안내 부재.
  - 모든 입력 행이 동일한 평면 grid 라서 info ↔ table column 의미 시각화 불가.
  - `[추가]` 하나라서 새로 추가되는 행이 일반 필드인지 표 컬럼인지 사용자가 결정할 단계 없음.
  - 한 화면에서 여러 개 테이블(예: 품목표 + 합계표)을 추가/이름 부여할 수단 없음.

### 4. Button Strategy Comparison

| option | UI | pros | cons | recommendation |
|---|---|---|---|---|
| A. One button + type select | `[+ 정의 추가 ▼]` → drop-down `(일반 영역 / 테이블 영역)` | UI 칸 적게 차지; type 추가/변경 시 메뉴만 늘리면 됨 | 클릭 단계 +1, type 인지 단계 별도; UI 자료구조(info/tables)가 한 곳에 묶인 듯한 인상 → 사용자가 "표"라는 별도 개념을 늦게 인지; drop-down 위치/접근성 부담 | ❌ MVP 비추 — 사용자 학습 곡선 ↑, JSON 구조와 UI 직결성 ↓ |
| B. Two buttons: 영역 정의 / 테이블 정의 | `[+ 영역 정의] [+ 테이블 정의] [삭제]` 헤더 우측 | info/tables JSON 구조와 1:1 대응; 거래명세서 사용자에게 "두 종류"임을 즉시 시각화; table 추가 시 별도 sub-section 자연스럽게 mount; 추후 type 추가는 별도 섹션으로 확장 | 버튼 폭 ↑(헤더 가로공간); MVP에서는 type 2종만 지원 (확장 시 버튼 늘림) | ✅ **추천** — JSON 구조/사용자 인지/구현 단순성 모두 우위 |

**최종 추천: 방식 B.** info와 table은 의미가 다르고(평면 1-value vs 반복 multi-column), 버튼 분리가 자료구조와 UI를 일치시켜 사용자 mental model을 단순화한다. drop-down은 type이 4+ 개로 늘었을 때 재검토.

### 5. Proposed Unstructured Data Shape

후보 비교:

| 후보 | shape | pros | cons |
|---|---|---|---|
| 1. fields 유지 + tableDefinitions 추가 | `{ mode, fields, tableDefinitions }` | 기존 `fields` 100% 호환 | "fields = info"라는 암묵 가정 모호; UI 일관성 ↓ |
| 2. info/tables로 분리 | `{ mode, info, tables }` | 의미 명확; UI ↔ JSON 1:1 | 기존 `fields` 기반 template load 시 마이그레이션 필요 |
| 3. **legacy fields + info/tables 동시 출력** | `{ mode, info, tables, fields }` (fields = info 미러) | 신규 reader는 `info`/`tables` 사용; 기존 reader(mapOcrResponse 등)는 `fields` 그대로; load 시 `fields → info` normalize | 직렬화 중복 (info 데이터를 fields에도 한 번 더 출력) — 단, 작은 비용 |

**추천: 후보 3.** 저장 시 `info`를 `fields`로도 직렬화하여 기존 reader 호환, load 시 `info` 없으면 `fields` → `info` normalize. 후속 reader 마이그레이션 완료 후 `fields` mirror 제거(별도 phase).

#### UnstructuredInfoField
- `key: string` — 안정적 식별자 (e.g. `supplierCompany`, `info_1`)
- `labelKo: string` — 한글 라벨
- `labelEn: string` — 영문/key 표시명
- `aliases?: string[]` — 동의어 헤더 후보
- `required?: boolean`
- `visible?: boolean`
- `order?: number` — 미설정 시 배열 index
- `description?: string`
- (호환) `no?: number` — legacy `fields[].no` 호환용 (load adapter에서 채움)

#### UnstructuredTableDef
- `tableKey: string` — `items_table` 같은 식별자
- `labelKo: string` — 표 한글명 ("품목표")
- `labelEn?: string`
- `columns: UnstructuredTableColumn[]`
- `aliases?: string[]` — 표 헤더 후보 키워드 (예: "품목", "내역")
- `required?: boolean` — 문서에 반드시 있어야 하는지
- `order?: number`
- `userConfirmed?: boolean`
- `description?: string`

#### UnstructuredTableColumn
- `columnKey: string`
- `labelKo: string`
- `labelEn?: string`
- `aliases?: string[]`
- `required?: boolean`
- `visible?: boolean`
- `order?: number`
- `source?: "auto" | "manual" | "default"`
- `confidence?: number`
- `userConfirmed?: boolean`

### 6. Backward Compatibility Strategy
- 기존 fields 기반 template 처리: load 시 `template_json.info`가 없고 `fields`만 있으면, `info = fields.map(f => ({ key: f.enField || `info_${f.no}`, labelEn: f.enField, labelKo: f.koField, order: f.no, ... }))`로 normalize. `tables = []`.
- 신규 info/tables template 처리: load 시 `info`와 `tables`를 그대로 사용. `fields`는 무시 (단, 저장 시 mirror로 다시 채움).
- 저장 시 legacy fields 유지 여부: ✅ 유지. `payload.fields = info.map(i => ({ no: i.order ?? idx+1, enField: i.labelEn, koField: i.labelKo }))`. 신규 키 `info`/`tables`는 그대로 직렬화. 기존 RunOCR mapOcrResponse는 `fields` reader 그대로 동작.
- 불러오기 시 normalize 방식: `normalizeUnstructuredTemplate(json)` helper 작성 — `info`/`tables` 우선, 없으면 `fields → info` 변환. table은 신규 template에서만 존재.
- 기존 영수증 template 영향: 없음. 저장된 `fields` 그대로 RunOCR가 single-value lookup → 결과 동일.
- 거래명세서 신규 template 처리: `info`(공급자/공급받는자/합계) + `tables: [{ tableKey: "items_table", columns: [품목명, 수량, 단가, 금액, ...] }]`. RunOCR side에서 `tables` reader 추가 후 표 행을 별도 컴포넌트로 표시 (TPL-7).

### 7. Relationship with Template Table Columns

| 필드 | 비정형 (UnstructuredTableColumn) | 템플릿 (TableColumnDef, src/common/types/ocr.ts) |
|---|---|---|
| columnKey / index | ✅ `columnKey` (의미 기반) | ✅ `index` + (TPL-2 제안) `columnKey?` |
| labelKo | ✅ | ✅ (제안 추가) / 또는 `koField` |
| labelEn | ✅ | ✅ (제안 추가) / 또는 `enField` |
| aliases | ✅ | 신규 (제안) |
| required | ✅ | 신규 (제안) |
| visible | ✅ | 신규 (제안) |
| order | ✅ | 신규 (제안) — 미설정 시 `index` |
| source | ✅ `auto`/`manual`/`default` | 신규 (제안) |
| confidence | ✅ | 신규 (제안) |
| userConfirmed | ✅ | 신규 (제안) |
| canonicalColumn | (선택) | ✅ 기존 |
| **guideId / guideX / width** | ❌ 비정형은 좌표 없음 | ✅ **템플릿 전용** |
| **anchorKeywords / headerAliases** | ✅ 비정형 전용 (표 헤더 텍스트 검색) | ❌ 템플릿은 좌표로 끊음 |

- 공통화 가능한 필드: `columnKey`, `labelKo`, `labelEn`, `aliases`, `required`, `visible`, `order`, `source`, `confidence`, `userConfirmed` (10개)
- 템플릿 생성 전용 필드: `guideId`, `guideX`, `width` (좌표 기반)
- 비정형 생성 전용 필드: `anchorKeywords`, `headerAliases`, `valueHints` 후보 (의미 기반)

**공통 타입 분리 여부: 당장은 분리하지 않는다.** 두 흐름의 표 컬럼은 의미는 비슷하지만 **좌표 기반 vs 텍스트 기반**의 본질적 차이가 있고, MVP에서 한 타입에 모두 우겨넣으면 optional 필드가 폭증하고 invariant가 흐려진다. 우선 각 흐름에 독립 타입을 두고, 양쪽 모두 실 사용 fixture가 쌓인 뒤(TPL-8) 공통 base type을 추출하는 편이 안전. 양쪽 모두에서 `BaseColumnDef = { columnKey, labelKo, labelEn?, aliases?, required?, visible?, order?, source?, confidence?, userConfirmed? }` 추출 가능성은 열려 있음.

### 8. Proposed UI Layout

비정형 우측 패널, 현재 `출력 필드 정의` 섹션 → `출력 정의`로 명칭 변경 + 내부를 info / table 두 sub-section으로 분리:

```
┌─ 저장 박스 ─────────────────────────────────────────────────┐
│                                       [삭제] [저장]/[수정]  │
└────────────────────────────────────────────────────────────┘
┌─ 패널 ─────────────────────────────────────────────────────┐
│ 템플릿 명  [____________________________________]          │
│                                                            │
│ ── 출력 정의 ──────────────────────────────────────────────│
│ [+ 영역 정의]  [+ 테이블 정의]  [삭제]                      │
│                                                            │
│ ▣ 일반 영역                                                 │
│   ┌ grid 28px / 1fr / 1fr ─────────────────────────────────┐│
│   │ No │ 영문 필드명 │ 한글 필드명                          ││
│   ├────┼─────────────┼───────────────────────────────────────┤│
│   │ 1  │ [supplier ] │ [공급자명          ]                ││
│   │ 2  │ [bizNo    ] │ [사업자번호         ]                ││
│   └────┴─────────────┴───────────────────────────────────────┘│
│   empty: "정의된 영역이 없습니다."                          │
│                                                            │
│ ▣ 테이블 정의                                                │
│   ┌ 테이블 카드 1 ────────────────────────────────────────────┐│
│   │ 테이블명 [품목표____________]  [+ 컬럼] [✕ 표 삭제]        ││
│   │ ┌ grid 28px / 1fr / 1fr ────────────────────────────────┐││
│   │ │ No │ 영문 컬럼명 │ 한글 컬럼명                          │││
│   │ ├────┼─────────────┼───────────────────────────────────────┤││
│   │ │ 1  │ [itemName ] │ [품목명              ]                │││
│   │ │ 2  │ [quantity ] │ [수량                ]                │││
│   │ │ 3  │ [unitPrice] │ [단가                ]                │││
│   │ │ 4  │ [amount   ] │ [금액                ]                │││
│   │ └────┴─────────────┴───────────────────────────────────────┘││
│   └─────────────────────────────────────────────────────────────┘│
│   empty: "정의된 테이블이 없습니다."                        │
└────────────────────────────────────────────────────────────┘
```

포함할 것:
- **버튼 위치**: 출력 정의 섹션 헤더 우측 — `[+ 영역 정의]` `[+ 테이블 정의]` `[삭제]`
- **리스트 구분 방식**: 두 sub-section (`일반 영역`, `테이블 정의`). 각 sub-section에 자체 grid + empty state
- **table section empty state**: "정의된 테이블이 없습니다." 카피
- **table 선택/삭제 방식**: 테이블 카드의 헤더에 `[✕ 표 삭제]` 버튼. 카드 클릭 시 선택 상태 + 우측 `[삭제]` 헤더 버튼으로 컬럼 행 제거.
- **column 추가/삭제 방식**: 테이블 카드 헤더 `[+ 컬럼]` + 행 선택 후 헤더 `[삭제]` 또는 카드 헤더 옆 단축 버튼.
- **MVP에서 제외할 항목**:
  - canonical 매핑 select
  - source/confidence/userConfirmed 시각화 chip (schema는 만들되 UI는 후속)
  - drag-and-drop reorder
  - column valueType
  - aliases multi-input
  - 자동 추천 (TPL-5에서 별도 phase)
  - 다중 표 간 dependency (예: 합계가 품목표 sum과 일치하는지)

### 9. Risk Assessment

- UI risk: **LOW** — UnstructuredBuilder의 우측 패널 일부만 교체. 캔버스/Template/RunOCR 영향 없음.
- save/load risk: **MEDIUM** — payload에 `info`/`tables` 키 추가하면서 `fields` mirror도 유지해야 함. normalize/serialize helper 단위 테스트 필수.
- backward compatibility risk: **LOW** — 기존 `fields`만 있는 template은 normalize로 `info`로 변환. `tables`는 신규 template에서만 존재.
- RunOCR integration risk: **MEDIUM** — info 읽기는 `fields` 호환으로 무수정 가능. 표 결과 표시는 RunOCR result 컴포넌트에 신규 path 필요 (TPL-7에서 별도).
- Template 생성 table editor와의 중복 risk: **MEDIUM** — 양쪽이 비슷한 schema를 갖게 되지만, 좌표 vs 의미의 본질 차이로 당장 공통화는 비추. fixture 누적 후 base type 추출 (TPL-8).
- TestWorkspace risk: **LOW** — Test는 manifest documentType + profiles 기반. 비정형 정책 무관.
- backend/fixture risk: **LOW** — backend는 `/templates`에 unstructured 저장이 없음 (localStorage only). fixture 영향 없음. RunOCR `/ocr/extract`는 manifest documentType 기반으로 동작 — 비정형 신규 schema는 frontend 전용에서 1차 검증.

### 10. Recommended TPL Implementation Plan

#### 1. TPL-3-UNSTRUCTURED-INFO-TABLE-TYPES-AND-HELPERS
- 작업명: TPL-3-UNSTRUCTURED-INFO-TABLE-TYPES-AND-HELPERS
- 도구: Claude Code (Opus 4.7)
- 목표: `UnstructuredInfoField`, `UnstructuredTableDef`, `UnstructuredTableColumn` 타입과 `normalizeUnstructuredTemplate` / `serializeUnstructuredTemplate` (legacy fields mirror 포함) helper 신설.
- 수정 파일 후보:
  - `src/components/template/utils/unstructuredDefinition.ts` (신설)
- 절대 수정 금지: UnstructuredBuilder.tsx, TemplateAnnotator, TemplateRightPanel, OcrCanvasPane, backend, profiles.ts, testsets.ts, templates.json.
- 검증 기준: typecheck/build PASS. mjs smoke test로 round-trip(`fields-only` template ↔ `info`/`tables` template) 무손실.
- 선행 조건: TPL-2 PASS.

#### 2. TPL-4-UNSTRUCTURED-INFO-TABLE-PAYLOAD-COMPAT
- 작업명: TPL-4-UNSTRUCTURED-INFO-TABLE-PAYLOAD-COMPAT
- 도구: Claude Code (Opus 4.7)
- 목표: UnstructuredBuilder save/load adapter를 `normalize/serialize` helper로 교체. UI는 그대로(아직 info/tables 분리 X), 내부 payload만 `{ info, tables, fields }`로 출력. localStorage 호환 확인.
- 수정 파일 후보:
  - `src/components/template/UnstructuredBuilder.tsx` (save/load helper 사용)
  - `src/components/template/utils/unstructuredDefinition.ts`
- 절대 수정 금지: TemplateAnnotator, OcrCanvasPane, RunOCR, backend.
- 검증 기준: 기존 fields-only template → load → save → 동일 결과. 신규 `info`/`tables` template → load → save 무손실. RunOCR mapOcrResponse 동작 변화 없음.
- 선행 조건: TPL-3.

#### 3. TPL-5-UNSTRUCTURED-INFO-TABLE-EDITOR-UI
- 작업명: TPL-5-UNSTRUCTURED-INFO-TABLE-EDITOR-UI
- 도구: Claude Code (Opus 4.7)
- 목표: UnstructuredBuilder UI 분할 — `[+ 영역 정의]` / `[+ 테이블 정의]` / `[삭제]` 버튼 분리 + 일반 영역 sub-section + 테이블 정의 sub-section + 테이블 카드 (이름/컬럼 grid/추가/삭제).
- 수정 파일 후보:
  - `src/components/template/UnstructuredBuilder.tsx`
  - `src/components/template/ui/UnstructuredInfoEditor.tsx` (신설, 선택)
  - `src/components/template/ui/UnstructuredTableEditor.tsx` (신설, 선택)
- 절대 수정 금지: TemplateAnnotator, OcrCanvasPane, RunOCR, backend.
- 검증 기준: UI smoke — 영역/테이블 추가/삭제, 카드 grid 입력 → state 반영. legacy fields-only template load 시 일반 영역에 표시.
- 선행 조건: TPL-4.

#### 4. TPL-6-UNSTRUCTURED-INFO-TABLE-SAVE-LOAD
- 작업명: TPL-6-UNSTRUCTURED-INFO-TABLE-SAVE-LOAD
- 도구: Claude Code (Opus 4.7)
- 목표: 신규 UI에서 입력한 `info`/`tables`가 save → localStorage → load → UI 복원 round-trip 보장. 기존 영수증 template과의 호환 e2e fixture.
- 수정 파일 후보:
  - `src/components/template/utils/unstructuredDefinition.ts` (edge case)
  - `src/components/template/UnstructuredBuilder.tsx` (save/load wiring)
- 절대 수정 금지: 기타 영역 동일.
- 검증 기준: round-trip mjs PASS (`fixtures/unstructured/*.json` 5+ 케이스).
- 선행 조건: TPL-5.

#### 5. TPL-7-UNSTRUCTURED-RUNOCR-INFO-TABLE-INTEGRATION
- 작업명: TPL-7-UNSTRUCTURED-RUNOCR-INFO-TABLE-INTEGRATION
- 도구: Claude Code (Opus 4.7)
- 목표: RunOCR `mapOcrResponse`에서 `template.info`/`template.tables`를 읽어 결과에 info 필드 + 표 row를 분리 표시. `template.fields`(legacy) fallback 유지.
- 수정 파일 후보:
  - `src/components/runocr/utils/mapOcrResponse.ts`
  - `src/components/runocr/RunOcrWorkspace.tsx` (또는 OcrResultPanel) — 표 결과 표시 컴포넌트
- 절대 수정 금지: Template 생성 흐름, OcrCanvasPane, TestWorkspace, backend.
- 검증 기준: 거래명세서 fixture → info + table row 결과 표시. 영수증 fixture → 기존 단일 필드 결과 변화 없음.
- 선행 조건: TPL-6.

#### 6. TPL-8-TEMPLATE-TABLE-COLUMN-EDITOR-ALIGNMENT
- 작업명: TPL-8-TEMPLATE-TABLE-COLUMN-EDITOR-ALIGNMENT
- 도구: Claude Code (Opus 4.7)
- 목표: 비정형 `UnstructuredTableColumn`과 템플릿 `TableColumnDef`의 공통 필드(10개) 정리 + (선택) `BaseColumnDef` 추출. TPL-1에서 보류한 템플릿 쪽 컬럼 정의 UI(TPL-1 plan §12-#3)도 이 단계에서 비정형 UI 패턴을 참고하여 추가.
- 수정 파일 후보:
  - `src/common/types/ocr.ts`
  - `src/components/template/utils/tableColumnDefinition.ts` (TPL-1 plan에 따라 신설 예정)
  - `src/components/template/ui/TemplateRightPanel.tsx`
  - `src/components/template/ui/TemplateTableColumnEditor.tsx` (신설)
- 절대 수정 금지: OcrCanvasPane, profiles.ts, testsets.ts, backend.
- 검증 기준: 양쪽 흐름에서 공통 필드 round-trip + 템플릿 쪽 컬럼 editor UI smoke.
- 선행 조건: TPL-7.

### 11. Do Not Start Yet
- TPL-3 ~ TPL-8 어떤 단계도 본 precheck 단계에서는 시작 금지.
- `UnstructuredBuilder` 수정 금지.
- `info`/`tables` 타입 또는 helper 파일 신설 금지.
- UI 분리 버튼/카드 추가 금지.
- save/load adapter 변경 금지.
- RunOCR `mapOcrResponse` 변경 금지.
- Template 생성 쪽 table column editor 신설 금지 (TPL-1 plan에 따라 TPL-8까지 보류).
- `templates.json`, fixture, backend, public/data/testsets 일체 수정 금지.

### 12. Verification Results
- production code modified: NO
- src/lib absent: YES
- @/lib import 0: YES
- typecheck: 다음 run에서 PASS 확인 예정 (npm run typecheck via 실행 명령)
- build: 다음 run에서 PASS 확인 예정 (npm run build via 실행 명령)
- static precheck: 다음 run에서 PASS 확인 예정 ([UNSTRUCTURED_INFO_TABLE_DEFINITION_TPL2_PRECHECK] PASS)
- FAIL count: 0 (precheck script가 검증)
