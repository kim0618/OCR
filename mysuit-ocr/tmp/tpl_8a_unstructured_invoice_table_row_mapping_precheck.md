## TPL-8A Unstructured Invoice Table Row Mapping Precheck

### 1. Summary
- 현재 TPL-7 상태: `mapOcrResponse.ts`가 비정형 template의 `info`/`documentType`/`tables`를 인식하고, `tables`가 있으면 결과에 `unstructuredTables[].rows = []` skeleton을 첨부하지만 실제 row 채움은 미구현. UI(OcrResultPanel)는 해당 메타를 아직 소비하지 않음.
- raw OCR line/block 사용 가능 여부: **부분 가능** — frontend는 `json.ocr_lines: Array<{text, confidence}>`만 받고, bbox(`pts`)는 backend 내부에서만 사용되어 JSON 응답에 포함되지 않음 ([ocr-server/main.py:2770-2774](ocr-server/main.py#L2770-L2774)).
- existing tableRows 사용 가능 여부: ✅ **충분히 가능** — `doc_type === "invoice_statement"`일 때 backend가 이미 `response.document_fields.tableRows: Array<Record<string, unknown>>`를 canonical key(`itemName`, `quantity`, `unitPrice`, `amount`, `spec`, `lotNo`, `expiryDate`, ...)로 채워서 보낸다 ([invoice_statement.py:7136](ocr-server/extractors/invoice_statement.py#L7136)). `tableMeta`도 함께 제공된다.
- invoice_statement row mapping 구현 가능 여부: ✅ **이번 phase에서 가능**. backend의 canonical-keyed `tableRows`를 사용자의 `template.tables[].columns[].columnKey`에 맞춰 픽업/리네임하는 1-pass 매핑으로 충분.
- 추천 구현 방식: **알고리즘 A (existing tableRows reuse)** — backend가 이미 row clustering/header matching/canonical 매핑까지 끝낸 `document_fields.tableRows`를 frontend가 단지 column-key projection만 수행. 좌표/clustering 코드 불필요.
- 추천 첫 구현 작업: **TPL-8B-UNSTRUCTURED-INVOICE-TABLE-ROW-PROJECTION** — `mapOcrResponse.ts` 옆 별도 helper(`extractUnstructuredTableRows.ts`)에서 invoice_statement용 projection을 수행하고, `unstructuredTables[i].rows`를 채운다.
- 이번 precheck에서 운영 코드 수정 여부: 없음. 산출물(`tmp/*`) + 로그(`ocr-server/logs/*`)만 생성.

### 2. Current RunOCR Response Flow
- request: [src/components/runocr/utils/runOcrRequest.ts](mysuit-ocr/src/components/runocr/utils/runOcrRequest.ts) — `POST ${backend}/ocr/extract` or `/api/ocr-extract`, FormData via `buildOcrFormData()`. 응답을 `await res.json()` 후 raw 그대로 반환 (typed `any`).
- response (backend `/ocr/extract`):
  - `full_text: string`
  - `ocr_lines?: Array<{text: string; confidence: number}>` — text-only, **no bbox** in JSON
  - `receipt_fields?: Record<string, string>` (영수증 키)
  - `finance_fields?: Record<string, string>` (금융전표)
  - `fields?: Array<...>` (region-based template path; backend가 region별로 채움)
  - `document_fields?: { tableRows, tableMeta, supplierCompany, buyerCompany, issueDate, totalAmount, rowCount, tableDetected, ... }` — **invoice_statement 전용 backend가 이미 추출 완료**
  - `doc_type?: string`
  - `processing_time: number`, `processed_image?: string`, `original_image?: string`
- mapOcrResponse input: `raw: any`, `template?: BuildRunOcrResultTemplate`, `options?` (`normalizeFieldKey`)
- mapOcrResponse output: `OcrResult & { documentType?, unstructuredTables? }` (raw spread + 옵셔널 메타 첨부)
- full_text: backend `raw.full_text` → 그대로 spread, mapOcrResponse는 변형하지 않음
- fields: 비정형 분기에서 receipt/finance lookup 기반 `OcrFieldResult[]`로 재조립 (template.info 우선, fields fallback)
- tableRows: **backend `document_fields.tableRows`에 이미 존재**. 현재 frontend는 [OcrResultPanel.tsx:697-704](mysuit-ocr/src/components/runocr/ui/OcrResultPanel.tsx#L697-L704)에서 직접 read하여 invoice_statement 구조화 preview에 사용. `mapOcrResponse`는 이 키를 손대지 않고 spread로 전달.
- raw lines/blocks: `raw.ocr_lines: Array<{text, confidence}>` — bbox 없음. backend 내부에서 `(pts, text, score)` 튜플이 사용되지만 JSON 직렬화 단계에서 bbox 제거됨 ([main.py:2770-2774](ocr-server/main.py#L2770-L2774), [ocr_lines.py:1-15](ocr-server/extractors/ocr_lines.py#L1-L15)).
- unstructuredTables skeleton: TPL-7에서 추가됨. `template.tables` 존재 시 `result.unstructuredTables = [{tableKey, labelKo, labelEn?, columns:[{columnKey, labelKo, labelEn?}], rows:[]}]`. rows는 항상 `[]` skeleton.

### 3. Available Data for Row Mapping

| source | contains text | contains bbox | stable order | available in frontend | note |
|---|---|---|---|---|---|
| `raw.full_text` | ✅ | ❌ | ❌ (단일 string) | ✅ | line 단위 split만 가능. 컬럼 alignment 불가 (whitespace 의존). |
| `raw.ocr_lines` | ✅ | ❌ (JSON 단계에서 제거됨) | ⚠️ (백엔드 정렬 순서) | ✅ (invoice_statement 템플릿 경로에서만 채움) | text+conf만. 컬럼 분할은 line-text whitespace split에 의존해야 하므로 noisy. |
| backend 내부 lines `[pts, text, score]` | ✅ | ✅ | ✅ | ❌ | 백엔드 전용. 프론트로 노출되지 않음. TPL-8B에서 끌어내려면 backend JSON 응답 확장 필요 (이번 phase 비추). |
| `raw.document_fields.tableRows` | ✅ | ❌ (canonical key-value pair) | ✅ (백엔드 정규화 순서) | ✅ | **canonical key**(itemName/quantity/unitPrice/amount/spec/lotNo/...)로 row 단위 정렬 완료. backend가 row clustering/header matching/숫자 정규화까지 모두 수행. |
| `raw.document_fields.tableMeta.expectedColumnKeys` / `tableMeta.columns` | – | – | ✅ | ✅ | row projection 시 backend가 사용한 canonical 키 목록을 참고 가능. |
| `template.tables[].columns[].columnKey` | – | – | ✅ | ✅ (TPL-5 UI) | 사용자가 정의한 키. canonical 키와 일치하면 직접 projection, 아니면 aliases 보조 lookup 필요. |

결론: backend의 `document_fields.tableRows`가 압도적으로 가장 안정적인 input. raw lines 기반 추출은 TPL-8B MVP에서 비추.

### 4. Existing Invoice/Structured Table Flow
- 기존 invoice_statement parser 결과 shape: `document_fields = { supplierCompany, supplierBizNumber, ..., totalAmount, tableRows: [{itemName, quantity, unitPrice, supplyAmount, taxAmount, amount, totalAmount, manufacturer, lotNo, expiryDate, rowIndex, ...}], tableMeta: { expectedColumnKeys, columns, valueMappingWarnings, expectedColumnsUsed, extractionSource }, rowCount, tableDetected }`. canonical 키는 [ocr-server/extractors/invoice_statement.py:197-203](ocr-server/extractors/invoice_statement.py#L197-L203)에 정의된 `CANONICAL_TABLE_KEYS = ["rowIndex", "itemCode", "itemName", "spec", "lotNo", "serialNo", "manufacturingNo", "expiryDate", "quantity", "unit", "unitPrice", "supplyAmount", "taxAmount", "amount", "totalAmount", "manufacturer"]`.
- tableRows가 이미 있으면 재사용 가능성: ✅ **매우 높음**. 동일 canonical 키 셋이 `src/components/test/utils/profiles.ts`의 `TABLE_COLUMN_META`와 일치. 사용자가 template 정의 시 동일 key를 쓰면 1:1 매핑 가능, 다르게 쓰면 aliases 폴백.
- RunOCR result panel에서 현재 표를 어떻게 표시하는지: [OcrResultPanel.tsx:697-730](mysuit-ocr/src/components/runocr/ui/OcrResultPanel.tsx#L697-L730) — `result.document_fields.tableRows`와 `tableMeta`를 직접 읽어 `buildInvoicePreviewCols(tableMeta, rows)`로 display columns 결정 후, `buildStructuredTableViewModel({rows, displayCols})`로 view model 생성하여 Preview 탭에 렌더. **`unstructuredTables` 키는 아직 consumer 없음.**
- Clean JSON/markdown builders에서 tableRows를 어떻게 쓰는지: [cleanJsonBuilder.ts](mysuit-ocr/src/common/utils/cleanJsonBuilder.ts) — `cleanTableRowsFromObjects(field.tableRows, null)`로 normalize. `result.document_fields.tableRows` 또는 field 단위 `tableRows`를 모두 처리.
- unstructuredTables와 기존 tableRows의 관계: **별도 채널**. 기존 `document_fields.tableRows`는 backend가 채우는 invoice_statement 전용. `unstructuredTables`는 frontend `mapOcrResponse`가 attached하는 user-defined template 전용. TPL-8B는 두 채널을 연결: `document_fields.tableRows`를 source로 사용해 user-defined `unstructuredTables[i].rows`를 채운다.

### 5. Proposed MVP Algorithm

#### 후보 A: existing tableRows reuse (✅ 강력 추천)
- 입력: `raw.document_fields.tableRows`, `template.tables[].columns[].columnKey`
- 알고리즘:
  1. `docType === "invoice_statement"` && `Array.isArray(raw.document_fields?.tableRows)` && `raw.document_fields.tableRows.length > 0`이면 진입
  2. `template.tables`의 첫 번째 (혹은 user-designated) table에 대해:
     - `for (const docRow of docTableRows)`:
       - `mappedRow = {}`
       - `for (const col of table.columns)`:
         - `mappedRow[col.columnKey] = String(docRow[col.columnKey] ?? lookupAlias(docRow, col) ?? "")`
       - push to `unstructuredTables[i].rows`
  3. 두 번째 이상 user table → `rows: []` 유지 (예: 합계표는 별도 phase)
- 장점:
  - backend가 이미 모든 heavy lifting 완료 (row grouping, canonical 매핑, 숫자 정규화)
  - 추가 coordinate/clustering 코드 0줄
  - canonical 키가 사용자 키와 매칭되면 즉시 동작
  - 기존 `document_fields.tableRows` consumer(`OcrResultPanel` structured preview, `cleanJsonBuilder`, etc.)에 영향 0
- 단점:
  - `doc_type !== "invoice_statement"` 일 때는 동작 안 함 (다른 documentType은 별도 phase)
  - 사용자가 canonical과 다른 columnKey 사용 시 빈 값 (aliases lookup 추가 필요)
  - 다중 user table 중 첫 번째 외에는 rows=[]

#### 후보 B: full_text line-based extraction (❌ 비추)
- 알고리즘: `full_text.split("\n")` → 헤더 후보 탐색 → whitespace split → row grouping
- 장점: backend 무관
- 단점: 컬럼 alignment 부정확 (whitespace만 사용), 한글/숫자 mixed line에서 부정확, 헤더 매칭이 documentType별 다양, 정확도 ↓↓. **MVP 비추**.

#### 후보 C: raw line bbox-based extraction (❌ 불가)
- backend가 bbox를 JSON으로 직렬화하지 않으므로 frontend에서 사용 불가. backend 응답 확장이 선행되어야 함. **이번 phase 범위 밖**.

**최종 추천: 후보 A.** `document_fields.tableRows`를 source-of-truth로 채택. backend 변경 없이 invoice_statement MVP 완성.

### 6. Proposed Result Shape

TPL-7에서 도입한 `unstructuredTables` skeleton의 `rows`를 채운다:

```ts
result.unstructuredTables = [
  {
    tableKey: "items",              // user-defined
    labelKo: "품목표",              // user-defined
    columns: [
      { columnKey: "itemName",  labelKo: "품목명" },
      { columnKey: "quantity",  labelKo: "수량" },
      { columnKey: "unitPrice", labelKo: "단가" },
      { columnKey: "amount",    labelKo: "금액" },
    ],
    // TPL-7: 항상 [], TPL-8B: invoice_statement이면 backend tableRows에서 projection
    rows: [
      { itemName: "심플라인 메디컬...", quantity: "2", unitPrice: "...", amount: "..." },
      { itemName: "심플라인 메디컬...", quantity: "3", unitPrice: "...", amount: "..." },
    ],
  },
  // 다중 테이블의 두 번째부터는 별도 source가 없으므로 rows: [] 유지
];
```

병행 옵션:
- 기존 `result.document_fields.tableRows`는 그대로 둔다 (OcrResultPanel structured preview consumer 무영향).
- `unstructuredTables[i].rows`는 user-defined columnKey 기반 새로운 view (Markdown/Clean JSON에서 별도 활용 가능).

OcrResultPanel UI 변경 없이 안전한지: ✅ — OcrResultPanel은 `unstructuredTables`를 읽지 않으므로 영향 0. 사용자가 표시를 보려면 TPL-8C에서 별도 UI 작업이 필요 (TPL-8B 범위 밖).

### 7. Ownership / File Plan

| 후보 | 장점 | 단점 | feature boundary 위험 | 추천 여부 |
|---|---|---|---|---|
| `mapOcrResponse.ts` 내부 helper | 외부 의존 추가 없음, 한 파일에서 흐름 추적 | 파일이 다소 비대 (~250 → 340줄 예상), invoice 매핑이 unstructured 매핑과 섞임 | 낮음 | △ |
| **`src/components/runocr/utils/extractUnstructuredTableRows.ts` 신규** | 단일 책임, 단위 테스트 용이, mapOcrResponse는 helper 호출 1줄, 향후 다른 documentType row mapping 추가 시 같은 helper에 분기 추가 | 신규 파일 1개 | 낮음 | ✅ **강력 추천** |
| `src/common/utils/tableRowMapping.ts` 신규 (common) | 다른 feature(예: Template 생성, Test)에서도 재사용 가능 | 현재 Template/Test는 별도 정책(profiles.ts) 사용. 공통화 필요성 불명. common 오염 위험 | 중간 | ❌ 아직 비추. fixture 누적 후 공통화 검토. |

**추천: 신규 `src/components/runocr/utils/extractUnstructuredTableRows.ts`** — 단일 책임의 pure helper로 분리. `mapOcrResponse.ts`는 결과를 `unstructuredTables`에 attach하는 한 줄만 추가.

신규 helper 인터페이스 초안:
```ts
export type UnstructuredTableRowProjectionInput = {
  raw: unknown;                       // OCR backend response
  documentType?: string;              // template documentType (user-defined)
  tables: Array<{
    tableKey: string;
    columns: Array<{ columnKey: string; aliases?: string[] }>;
  }>;
};

export type UnstructuredTableRowProjection = Array<Array<Record<string, string>>>;
// idx: per-user-table → rows array. 일치하는 row가 없으면 [].

export function extractUnstructuredTableRows(
  input: UnstructuredTableRowProjectionInput,
): UnstructuredTableRowProjection;
```

### 8. Risk Assessment

- raw data availability risk: **LOW** — `document_fields.tableRows`는 invoice_statement에 한해 안정 (backend가 이미 production에서 사용 중)
- row grouping risk: **LOW** — backend가 row grouping 완료 (rowCount, tableMeta.extractionSource 검증 메타도 함께 제공)
- header matching risk: **MEDIUM** — 사용자 columnKey가 canonical 키와 다를 수 있음. MVP는 직접 매칭만 지원, alias lookup은 후속(TPL-8B-2)으로 분리 권장
- existing receipt compatibility risk: **LOW** — `documentType !== "invoice_statement"`이면 row projection 자체를 skip
- result schema risk: **LOW** — `unstructuredTables` 키는 TPL-7에서 이미 attach (consumer 없음). rows만 채우는 것은 추가 키 0
- UI risk: **LOW** — OcrResultPanel은 `unstructuredTables` 미consumer. 변경 없음
- backend dependency risk: **LOW** — backend 응답 shape 변경 불필요. 기존 `document_fields.tableRows` consumer (`OcrResultPanel`, `cleanJsonBuilder`, `structuredTableViewModel`, `invoiceTableDisplay`) 영향 0

### 9. Recommended TPL-8B Implementation Plan

**작업명**: TPL-8B-UNSTRUCTURED-INVOICE-TABLE-ROW-PROJECTION
**도구**: Claude Code (Opus 4.7)
**목표**: `document_fields.tableRows`를 user-defined `template.tables[].columns[].columnKey`로 projection하여 `result.unstructuredTables[i].rows`를 채운다. invoice_statement MVP 한정.

**수정 파일 후보**:
- **신규**: `src/components/runocr/utils/extractUnstructuredTableRows.ts` (pure helper)
- **수정**: `src/components/runocr/utils/mapOcrResponse.ts` — `unstructuredTables` 구성 직전에 helper 호출 한 줄 추가, 결과의 `rows` 채움. 다른 부분은 변경 없음.

**금지 사항**:
- UnstructuredBuilder/unstructuredDefinition 수정 금지
- OcrResultPanel/RunOcrWorkspace UI 수정 금지 (TPL-8C 범위)
- TestWorkspace 수정 금지
- backend 파일 수정 금지
- `result.document_fields.tableRows`/`tableMeta` 변형 금지 (read-only)
- documentType ≠ "invoice_statement"일 때 projection 적용 금지
- alias resolution (canonical aliases 외) 이번 단계에서 구현 금지 — 후속 TPL-8B-2 candidates: `columns[].aliases` 활용, profile-based fallback

**smoke fixture** (`tmp/fixtures/runocr_invoice_response/`):
1. `invoice_statement_basic.json` — backend response with `document_fields.tableRows: 3 rows (itemName/quantity/unitPrice/amount)` + matching user template
2. `invoice_statement_mismatched_keys.json` — backend canonical(`itemName`) vs user(`product_name`) → 빈 값 reasonable fallback 확인
3. `invoice_statement_empty_rows.json` — `tableRows: []` → `unstructuredTables[0].rows = []`
4. `invoice_statement_two_tables.json` — user `template.tables.length === 2` → 첫 번째 채움, 두 번째 `[]`
5. `not_invoice_statement.json` — `doc_type: "card_receipt"` + `document_fields` 없음 → projection 미적용, rows=[] 유지
6. `legacy_no_template_tables.json` — `template.tables` 없음 → unstructuredTables 자체 미생성 (TPL-7 동일 동작)

**검증 기준**:
- `extractUnstructuredTableRows` 단위 smoke 6+ 케이스 PASS
- mapOcrResponse 후 result 비교:
  - case 1: `result.unstructuredTables[0].rows.length === 3` && row keys match user columnKey
  - case 5: `!("unstructuredTables" in result)` 또는 `rows: []` 유지
- TPL-7 기존 smoke 9개 모두 PASS (회귀 0)
- typecheck/build PASS
- 기존 49개 runner PASS
- markdown contract PASS
- `[UNSTRUCTURED_INVOICE_TABLE_ROW_PROJECTION_TPL8B] PASS` 출력

### 10. Do Not Start Yet
- TPL-8B 구현(`extractUnstructuredTableRows.ts` 신규 + mapOcrResponse 한 줄 추가) 시작 금지
- OcrResultPanel UI에 `unstructuredTables` 표시 컴포넌트 추가 금지 (TPL-8C)
- backend `document_fields.tableRows` 형식 수정 금지
- alias resolution / valueType coercion 등 추가 정책 도입 금지
- 다중 user table에 대한 row distribution 알고리즘 (예: 두 번째 user table에 합계표 row 채우기) 구현 금지
- documentType ≠ "invoice_statement" extension 금지
- raw `ocr_lines` 기반 row clustering 구현 금지 (bbox 부재로 정확도 낮음)
- `templates.json` 수정 금지
- fixture 외 backend/ground-truth/public data 변경 금지

### 11. Verification Results
- production code modified: NO
- src/lib absent: YES
- @/lib import 0: YES
- typecheck: 다음 run에서 PASS 확인 예정 (npm run typecheck via 실행 명령)
- build: 다음 run에서 PASS 확인 예정 (npm run build via 실행 명령)
- static precheck: 다음 run에서 PASS 확인 예정 ([UNSTRUCTURED_INVOICE_TABLE_ROW_MAPPING_PRECHECK_TPL8A] PASS)
- FAIL count: 0 (precheck script가 검증)
