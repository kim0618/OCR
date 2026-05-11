# OP-0 TEST 탭과 운영 탭 구조 비교 분석 리포트

작성일: 2026-05-11
직전 리포트: R-2 (R2_invoice_statement_remaining_analysis_20260511.md)

---

## 1. 작업 목적

Test 탭은 M-2f/GT-ADDR/R-1/R-2를 거치며 GT 기반 판정 정책이 정리되었다. 하지만 실제 운영은 Template/RunOCR/History 탭에서 동작한다.
표 작업(T-1)으로 진입하기 전에 다음을 결정한다.

1. Test 탭의 어떤 정책이 운영 탭에 이미 반영되어 있는가
2. canonicalField/alias/documentType-aware mapping이 어디까지 구현되어 있는가
3. 표 작업 전에 운영 탭에 먼저 반영해야 할 최소 작업은 무엇인가
4. 표 작업 이후로 미뤄도 되는 작업은 무엇인가
5. 안전한 진행 순서는 무엇인가

코드 수정: **없음**. 분석 리포트만.

---

## 2. 분석 범위

| 영역 | 파일/컴포넌트 | 확인 내용 |
|---|---|---|
| Test | `src/components/test/TestWorkspace.tsx` | computeFieldFinalStatus, InvoiceProfile, GT_REF, documentFields 구조 |
| Template (구) | `src/app/template/page.tsx`, `src/components/template/TemplateBuilder.tsx`, `src/components/ocr/core/types.ts`, `src/components/ocr/core/export.ts` | 정형/비정형, FieldType, Region 구조, localStorage 저장 |
| Template (신) | `src/app/btemplate/page.tsx`, `src/components/btemplate/TemplateWorkspace.tsx` | 서버 기반 템플릿 CRUD |
| RunOCR | `src/app/runocr/page.tsx`, `src/components/upload/UploadWorkspace.tsx`, `src/components/upload/OcrResultPanel.tsx` | 템플릿 선택, /ocr/extract 호출, 결과 매핑, autofill |
| History (구) | `src/components/history/HistoryWorkspace.tsx`, `src/lib/historyStore.ts`, `src/components/history/DetailHistoryView.tsx` | localStorage 기반 OCR 결과 저장 |
| History (신) | `src/components/history/BHistoryWorkspace.tsx` | API 기반 OCR 결과 CRUD |
| Autofill engine | `src/lib/autofillEngine.ts` | FIELD_ALIASES, 사업자번호 기반 history 매칭 |
| Backend proxy | `src/app/api/ocr-extract/route.ts` | /ocr/extract 프록시 |

---

## 3. Test 탭 현재 구조

### 3-1. 데이터 흐름

```
1. dataset 선택 (invoice_statement / baseline / google 등)
   ↓
2. manifest.json 로드 → ManifestItem[] (documentType, qualityTags, invoiceProfile 포함)
   ↓
3. ground_truth.json 로드 → GtRecord[] (receipt fields + documentFields + financeFields)
   ↓
4. ocr_cache.json 로드 (있으면) 또는 Run All 실행 → OcrEntry[]
   ↓
5. (옵션) party_master.json 로드 → PartyMasterMap (M-2f GT_REF 용)
   ↓
6. computeAllFieldViews(gt, ocr, autofill, dataset) → receipt 필드 view
   ↓
7. document 필드: getInvoiceNormalization + getPartyMasterCandidateForField + getPartyMasterPromotion
   → computeFieldFinalStatus(masterSelected: promoted) → O/△/X
   ↓
8. batch table + 상세 카드 + KPI 모두 동일한 computeFieldFinalStatus 호출
```

### 3-2. 핵심 타입 (TestWorkspace.tsx 및 core/types.ts)

```typescript
// ManifestItem
type InvoiceProfile = {
  invoiceSubType?: string;
  amountProfile?: "supply_tax_total" | "total_only" | "subtotal_cumulative"
                | "balance_cumulative" | "no_amount_summary" | "quantity_total_only"
                | "ambiguous_amount";
  partyProfile?: "supplier_buyer" | "supplier_weak" | "party_garbled"
               | "buyer_only" | "buyer_rep_optional";
  tableProfile?: "multi_item_table" | "single_item_table" | "item_quantity_table"
              | "lot_serial_quantity_table" | "serial_quantity_table";
  summaryFields?: Record<string, { label: string; appliesToAmount: boolean }>;
  visibleAmountFields?: string[];
  fieldLabels?: Record<string, string>;
};

// DOCUMENT_FIELD_META (key fields)
//   supplierCompany / supplierBizNumber / supplierRepresentative / supplierAddress
//   buyerCompany / buyerBizNumber / buyerRepresentative / buyerAddress
//   issueDate / supplyAmount / taxAmount / totalAmount /
//   subtotal / cumulativeAmount / previousBalance / transactionAmount / cumulativeBalance / totalQuantity
//   tableDetected / rowCount / firstRowPreview

// AMOUNT_PROFILE_AMOUNT_FIELDS
//   supply_tax_total      → [supplyAmount, taxAmount, totalAmount]
//   subtotal_cumulative   → [subtotal, cumulativeAmount]
//   balance_cumulative    → [previousBalance, transactionAmount, cumulativeBalance]
//   no_amount_summary     → []
//   quantity_total_only   → [totalQuantity]

// PARTY_MASTER_*_FIELDS (M-2f 자동채움 대상)
//   supplier: { supplierCompany: "company", supplierRepresentative: "representative", supplierAddress: "address" }
//   buyer:    { buyerCompany: "company", buyerRepresentative: "representative", buyerAddress: "address" }
// PARTY_ADDRESS_FIELDS (자동채움 제외 = address)
//   { "supplierAddress", "buyerAddress" }
```

### 3-3. 판정 로직

| 함수 | 위치 | 역할 |
|---|---|---|
| `computeFieldFinalStatus` | TestWorkspace.tsx L165 | 단일 진실 함수. 상세 카드/batch table/KPI 모두 호출. O/△/X/— 반환 |
| `documentMatchStatus` | L144 | normalize 후 substring 기반 O/△/X 판정 |
| `normalizeDocumentCompare` | L133 | 공백/괄호/구두점 제거 + lowercase |
| `getPartyMasterPromotion` | L3283 | biz exact + reference 존재 시 promoted=true (address 제외) |
| `getPartyMasterCandidateForField` | L3223 | biz key로 party_master lookup |
| `computeNormalizedAuxStatus` | L344 | NORM row용 별도 보조 status (address digitSignature 체크 포함) |

판정 우선순위 (M-2f):
1. OCR direct match → O
2. NORM direct match → O
3. GT_REF 자동채움 (biz exact + reference) → △ (company/representative만)
4. partial/similarity → △
5. 실패 → X

### 3-4. 운영으로 이전 가능한 정책

| Test 정책 | 운영 이전 우선순위 | 비고 |
|---|---|---|
| documentType / invoiceProfile 메타 구조 | **높음** | Template UI에서 sample이 어떤 profile에 속하는지 알아야 fieldLabels override, visibleAmountFields 등 적용 가능 |
| canonical field 명 (supplierCompany 등) | **높음** | RunOCR 결과를 templateField와 매칭하는 핵심 |
| amountProfile별 표시/평가 필드 | **중간** | RunOCR 출력에서 N/A 필드를 숨기는 정책 |
| partyProfile 예외 (buyer_only 등) | **중간** | 거래명세서 변형 처리 |
| GT_REF 자동채움 (party_master) | **낮음** | 운영에서는 history-based autofill이 따로 있음. 통합 검토는 OP-3 단계 |
| GT_SIMILARITY/partial source 태그 | **중간** | OcrFieldResult.source에 추가 필요 |
| computeFieldFinalStatus O/△/X | **중간** | 운영의 OCR-only context에서는 GT가 없어 단순화 필요 |
| tableRows 표시 구조 | **표 작업 후** | T-1 결과 후 운영 이전 |

---

## 4. Template 탭 현재 구조

### 4-1. 템플릿 종류

| 종류 | 모드 | 컴포넌트 | 저장 방식 |
|---|---|---|---|
| 정형 (region-based) | "template" | OcrAnnotator | `localStorage["mysuit_ocr_templates"]` |
| 비정형 (label list) | "unstructured" | UnstructuredBuilder | 동일 localStorage |
| 서버 정형 | (별도 라우트) | btemplate/TemplateWorkspace | API 기반 CRUD |

### 4-2. 필드 저장 구조

**정형 템플릿 (Region):**
```typescript
type FieldType = "field" | "multi" | "check" | "table";

type Region = {
  id: string;
  name: string;          // 사용자 입력 라벨 (한글 또는 영문)
  fieldType: FieldType;
  x, y, width, height: number;
  parts?: 2 | 3;         // multi 전용
  ratios?: number[];
  checkMode?: CheckMode; // check 전용
  table?: TableMeta;     // table 전용
};
```

**비정형 템플릿 (UnstructuredField):**
```typescript
type UnstructuredField = {
  no: number;
  enField: string;       // 영문 필드명
  koField: string;       // 한글 필드명
};
```

### 4-3. 테이블필드 구조

```typescript
type TableMeta = {
  mode?: "repeat" | "auto";       // 고정 그리드 vs 가변 그리드
  rowTemplate?: Rect;              // repeat 모드의 단일 row 패턴
  rows?: Rect[];                   // auto 모드의 row 영역 목록
  colGuides?: number[];            // 컬럼 분할 x 좌표
  stopKeywords?: string[];         // 종료 키워드 (합계/소계 등)
};
```

현재 구조는 **컬럼 정의가 좌표만** 있고, **컬럼 의미(canonicalField)는 없음**. 즉 "이 컬럼은 수량인지 단가인지 금액인지" 정보가 없다.

### 4-4. canonicalField 지원 여부

| 항목 | 현재 상태 |
|---|---|
| Template 필드에 canonicalField 슬롯 | **없음** |
| Template 필드에 documentType 슬롯 | **없음** |
| Template 필드에 alias 슬롯 | **없음** |
| Template에서 fieldKey와 표시 label 분리 | **분리 안 됨** (name이 곧 label이자 매칭 키) |
| autofillEngine FIELD_ALIASES (runtime only) | **있음** — 회사명/상호/가맹점명 → "회사명" 정규화. 단 저장 안 됨 |

`autofillEngine.AUTOFILLABLE_FIELDS` = `["회사명", "사업자번호", "대표자", "tel", "전화번호", "주소"]`.
이는 영수증 한정 (단일 회사 컨텍스트). 거래명세서 supplier/buyer 양쪽 컨텍스트는 미반영.

### 4-5. 현재 한계

1. **canonicalField가 없어 동일 의미 필드 매칭 불가**
   - 사용자가 "회사명"이라고 적으면 영수증 merchantName인지 거래명세서 supplierCompany인지 모름
2. **거래명세서의 supplier/buyer 양쪽 컨텍스트 미지원**
   - 사용자가 "회사명" 1개만 적으면 어느 측인지 결정 불가
3. **tableRows 컬럼 의미 미정의**
   - 컬럼 좌표만 있고 (품명/수량/단가/금액) 같은 의미 라벨 없음
4. **documentType 무관 매핑**
   - Template은 어떤 문서 종류든 동일한 raw 영역 매칭만 수행

---

## 5. RunOCR 탭 현재 구조

### 5-1. 데이터 흐름

```
UploadWorkspace.tsx (variant="runocr"):

1. localStorage에서 템플릿 목록 로드
   ↓
2. 사용자가 템플릿 + 이미지 + model_id 선택
   ↓
3. FormData 작성:
   { file, template_id?, regions? (정형일 때), model_id }
   ↓
4. POST /ocr/extract (Next API → backend proxy)
   ↓
5. backend 응답:
   {
     fields: OcrFieldResult[],           // 템플릿 region별 결과
     full_text: string,
     processing_time: number,
     receipt_fields?: Record<string,any>, // documentType별 추출 결과 (제한적)
     finance_fields?: Record<string,any>, // finance documentType 결과
     processed_image?: string
   }
   ↓
6. buildRunOcrResult(): 응답을 OcrResult로 변환
   - 정형 템플릿: response.fields 직접 사용
   - 비정형/템플릿 없음: receipt_fields + finance_fields를 RECEIPT_ALIAS로 매핑
   ↓
7. attachSourceBoxes(): OCR raw 라인 bbox 재매핑 + overlayAdoption 계산
   ↓
8. runAutofill(autofillEngine): 사업자번호 기반 history 후보 → 자동 채움
   ↓
9. saveHistoryRun(): localStorage["mysuit_ocr_history"] 에 저장
```

### 5-2. 템플릿 필드와 OCR 결과 매핑 방식

**현재 매핑은 label-based** (Korean label / English label 매칭):

```typescript
// UploadWorkspace.tsx — RECEIPT_ALIAS 일부
const RECEIPT_ALIAS: Record<string, string> = {
  "전화번호": "tel",
  "Tel": "tel",
  "TEL": "tel",
};
```

```typescript
// OcrResultPanel.tsx — OcrFieldResult
export type OcrFieldResult = {
  name: string;          // 사용자 라벨 ("회사명" 등)
  field_type: string;
  value: string;
  confidence: number;
  bbox: number[];
  source?: "ocr" | "biz" | "gt" | "text";   // 일부 source 태그 있음
  applied?: string;
  autofillAction?: "filled" | "corrected" | "confirmed" | "none";
  suggestions?: AutofillSuggestion[];
  original?: string;
  sourceBboxes?: FieldSourceBox[];
  overlayAdoption?: FieldOverlayAdoption;
  en?: string;
  ko?: string;
};
```

`name` 필드가 사용자 라벨 / 한글 / 영문 어느 쪽이든 들어올 수 있고 매칭이 라벨 기반이라 일관성이 부족.

### 5-3. canonicalField 지원 여부

| 항목 | 현재 상태 |
|---|---|
| 응답에 canonicalField 필드 | **없음** |
| documentType-aware 매핑 | **없음** (receipt_fields / finance_fields가 응답에 와도 documentType 분기 안 함) |
| documentFields (invoice_statement) 사용 | **사용 안 함** (Test 탭만 사용) |
| source 태그 | **부분적** (ocr/biz/gt/text 정도. GT_REF/GT_SIMILARITY 없음) |
| autofillAction | **있음** (filled/corrected/confirmed/none) |
| confidence | **있음** (numeric) |
| tableRows | **응답 type 없음** (field_type="table"은 정의되어 있으나 실제 처리 안 됨) |

### 5-4. 현재 한계

1. **documentFields(거래명세서) 출력 미활용** — backend가 보내도 RunOCR에서 표시/저장 안 함
2. **canonicalField 없음** — 사용자 라벨 그대로 매칭되어 alias 처리 어려움
3. **tableRows 처리 부재** — 단일 cell value만 지원
4. **GT_REF / GT_SIMILARITY 개념 없음** — Test 탭의 보정 source가 운영에선 표현 불가
5. **N/A / profile 정책 없음** — N/A 표시 또는 amountProfile 기반 필드 숨김 미구현

---

## 6. History 탭 현재 구조

### 6-1. 저장 구조

`src/lib/historyStore.ts`:

```typescript
export type HistoryRunRecord = {
  job_id: string;
  file_name: string;
  template_name: string | null;
  processing_time: number;
  created_at: string;
  status: "success" | "fail";
  image_url?: string;
  ocr_fields?: HistoryOcrField[];     // raw OCR 라인별
  output_fields?: HistoryOutputField[]; // 사용자 매핑 결과
  autofill_summary?: HistoryAutofillRunSummary;
};

export type HistoryOutputField = {
  no?: number;
  en: string;          // 영문 라벨
  ko: string;          // 한글 라벨
  original: string;    // OCR 원본
  modified: string;    // 사용자 수정 후
  confidence: number;
  source?: "ocr" | "biz" | "gt" | "text";
  applied?: string;
  autofillAction?: "filled" | "corrected" | "confirmed" | "none";
  suggestions?: AutofillSuggestion[];
};
```

저장소: localStorage (key `mysuit_ocr_history`, 최대 50건, quota exceeded 시 graceful degradation).
서버 기반: `BHistoryWorkspace`가 API CRUD 제공.

### 6-2. 표시 구조

`HistoryWorkspace.tsx`: 목록 (job_id / file / template / processing_time / status)
`DetailHistoryView.tsx`: 상세 (image + ocr_fields 테이블 + output_fields 테이블 + GT 비교 + 편집)

### 6-3. source/status/debug 저장 여부

| 항목 | 저장 여부 |
|---|---|
| source (ocr/biz/gt/text) | ✅ |
| confidence | ✅ |
| autofillAction | ✅ |
| applied (어떤 후보가 적용됐는지) | ✅ |
| autofill suggestions 목록 | ✅ |
| canonicalField | ❌ |
| status (O/△/X) | ❌ (GT 없는 운영 환경) |
| documentType | ❌ |
| tableRows | ❌ |
| extractDebug (parser anchor/evidence) | ❌ |

### 6-4. 현재 한계

1. **canonicalField 없음** → 같은 의미 필드를 다른 라벨로 저장한 기록은 검색/집계 불가
2. **documentType 분류 없음** → 영수증/거래명세서/finance 통계 분리 불가
3. **tableRows 저장 슬롯 없음**
4. **source가 ocr/biz/gt/text 4종으로 제한** → GT_REF/GT_SIMILARITY/NORM 등 신규 source 추가 필요
5. **자동복원 외 normalization 정보 부족** → Test의 normalization 후보 디버그가 운영에선 사라짐

---

## 7. Test 기준과 운영 구조의 차이

| 항목 | Test 탭 | 운영 탭 (Template/RunOCR/History) | 차이/문제 |
|---|---|---|---|
| documentType | manifest.documentType + invoiceProfile 메타 | 없음 (template은 documentType 무관) | 운영은 문서 종류 모름 |
| profile (amount/party/table) | invoiceProfile으로 정책 분기 | 없음 | 운영은 N/A 처리, 측면 분기 불가 |
| canonicalField | DOCUMENT_FIELD_META (supplierCompany 등 22개) | 없음 (label만) | 동일 의미 매칭 불가 |
| alias mapping | normalizeDocumentCompare + GT alias | autofillEngine FIELD_ALIASES (runtime) | 양쪽이 다른 사전. 통합 필요 |
| selectedValue | OCR > NORM > GT_REF > GT_SIMILARITY > 빈값 (M-2f) | OCR + autofill 자동복원 | 결과 우선순위 다름 |
| source/status | GT_REF/GT_SIMILARITY/GT_ANCHOR_EMPTY/NORM/OCR/EMPTY | OCR/BIZ/GT/TEXT | status 분류 체계 다름 |
| GT_REF | party_master.json 기반 (M-2f) | autofillEngine history+groundTruth 기반 | reference 소스가 다름 |
| O/△/X | computeFieldFinalStatus 통일 | 없음 (GT 없는 운영) | 운영은 confidence threshold만 |
| tableRows | 메타만 (tableDetected/rowCount/firstRowPreview) | 미구현 | 양쪽 모두 미완성 |
| 저장 위치 | dataset 폴더 (manifest/gt/cache) | localStorage / API | 분리됨 (의도된 분리) |

**가장 큰 구조 차이:**
1. **canonicalField 부재** — Test에 있는 supplierCompany 등 의미 키가 운영에는 없음
2. **documentType-aware 추출 결과(documentFields/financeFields) 미활용** — backend가 제공해도 RunOCR이 무시
3. **status 분류 체계 분기** — Test = GT 비교 기반, 운영 = autofill source 태그 기반

---

## 8. 영수증/거래명세서 공통 canonical mapping 가능성

| 질문 | 답변 |
|---|---|
| canonicalField registry를 공통으로 만들 수 있는가? | **예** — 영수증은 단일 측, 거래명세서는 supplier/buyer 측을 명시. 한 registry에 group/side 슬롯 두면 통합 가능 |
| documentType별 alias mapping을 만들 수 있는가? | **예** — 같은 "회사명"이라도 receipt → merchantName, invoice_statement → supplierCompany?buyerCompany 후보 |
| 같은 alias라도 documentType에 따라 다르게 해석해야 하는가? | **예** — 거래명세서에서 "사업자번호"는 supplier/buyer 양 후보 |
| confidence/ambiguous 구조가 필요한가? | **예** — 매칭 결과에 candidates 배열 + ambiguous flag 필요 |
| Template UI에서 ambiguous 후보를 보여줄 수 있는가? | 현재는 못 함. UI 추가 필요 (드롭다운/선택지) |

**핵심 접근:**
- **공통 registry**에 모든 canonical 정의 등록
- 각 canonical은 `documentTypes: [...]` + `side: "supplier"|"buyer"|"any"` + `group: "party"|"address"|"amount"|"date"|"table"` 보유
- 매칭 엔진은 사용자 입력 라벨 + documentType + position context로 best canonical 선택
- ambiguous면 후보 목록 반환 → UI에서 사용자 선택

---

## 9. 비정형 필드명 자동매칭 가능성

| 입력 필드명 | 영수증 매핑 | 거래명세서 매핑 | 모호성 | 처리 방식 |
|---|---|---|---|---|
| 회사명 | merchantName (단일) | supplierCompany / buyerCompany | **모호** | documentType=invoice_statement면 후보 2개, 사용자 선택 또는 영역 위치 기반 자동 |
| 상호명 | merchantName | supplierCompany / buyerCompany | 모호 | 위와 동일 |
| 업체명 | merchantName | supplierCompany / buyerCompany | 모호 | 위와 동일 |
| 가맹점명 | merchantName | (해당 없음) | 명확 | receipt 한정 |
| 사업자번호 | businessNumber | supplierBizNumber / buyerBizNumber | **모호** | 위와 동일 |
| 대표자 | representative | supplierRepresentative / buyerRepresentative | **모호** | 위와 동일 |
| 주소 | address | supplierAddress / buyerAddress | **모호** | 위와 동일 |
| 전화번호 | tel | (보통 supplier 측) | 약모호 | invoice_statement면 supplier 기본, 필요 시 후보 |
| 총합계금액 | totalAmount | totalAmount | 명확 | 직접 매핑 |
| 공급가액 | (없음) | supplyAmount | 명확 | invoice_statement 한정 |
| 세액 / 부가세 | taxAmount | taxAmount | 명확 | 직접 매핑 |
| 합계 | totalAmount | totalAmount | 명확 | 직접 매핑 |
| 소계 | (없음) | subtotal | 명확 | invoice_statement 한정 |
| 누계 | (없음) | cumulativeAmount | 명확 | invoice_statement 한정 |
| 전일잔액 | (없음) | previousBalance | 명확 | invoice_statement 한정 |
| 당일거래금액 | (없음) | transactionAmount | 명확 | invoice_statement 한정 |
| 누계잔액 | (없음) | cumulativeBalance | 명확 | invoice_statement 한정 |

**핵심 관찰:**
- **5개 필드(회사명/상호명/업체명/사업자번호/대표자/주소)에서 거래명세서 측면 모호성** 발생
- 모호성 해결 방법:
  1. **영역 위치 기반**: Region이 문서의 좌측(공급자)/우측(공급받는자) 위치로 후보 정렬
  2. **사용자 선택**: 후보 2개 드롭다운 제시
  3. **prefix 입력 가이드**: "공급자 회사명" / "공급받는자 회사명" 입력 권장

---

## 10. 권장 canonicalField registry 초안

```typescript
type CanonicalFieldDefinition = {
  canonicalField: string;        // ex: "supplierCompany"
  documentTypes: string[];       // ["invoice_statement"]
  labelKo: string;               // 표시용 한글 라벨
  labelEn: string;               // 표시용 영문 라벨
  aliases: string[];             // ["회사명", "상호명", "공급자회사명", ...]
  group: "party" | "address" | "amount" | "summary" | "date" | "table" | "meta";
  side: "supplier" | "buyer" | "any";
  valueType: "string" | "number" | "money" | "date" | "phone" | "biznum";
  isRepeatable: boolean;         // tableRows 컬럼인지
  isTableColumn: boolean;        // 별도 슬롯 (T-1 이후 확정)
  confidenceBase: number;        // 기본 신뢰도 (0~1)
  amountProfileAware?: boolean;  // amountProfile에 따라 N/A 분기 여부
  partyProfileAware?: boolean;   // partyProfile에 따라 N/A 분기 여부
};
```

### Registry 초안 (요약)

| canonicalField | documentTypes | labelKo | aliases (예시) | group | side | valueType |
|---|---|---|---|---|---|---|
| `merchantName` | receipt | 회사명 | 회사명, 상호, 가맹점명, 업체명 | party | any | string |
| `businessNumber` | receipt | 사업자번호 | 사업자번호, 등록번호 | party | any | biznum |
| `representative` | receipt | 대표자 | 대표자, 대표 | party | any | string |
| `address` | receipt | 주소 | 주소 | address | any | string |
| `tel` | receipt | 전화번호 | tel, TEL, 전화번호 | party | any | phone |
| `totalAmount` | receipt, invoice_statement | 합계금액 | 총합계금액, 합계, total | amount | any | money |
| `taxAmount` | receipt, invoice_statement | 세액 | 세액, 부가세, tax | amount | any | money |
| `supplierCompany` | invoice_statement | 공급자 회사명 | 공급자 회사명, 공급자 상호, 공급자 | party | supplier | string |
| `supplierBizNumber` | invoice_statement | 공급자 사업자번호 | 공급자 사업자번호, 공급자 등록번호 | party | supplier | biznum |
| `supplierRepresentative` | invoice_statement | 공급자 대표자 | 공급자 대표자, 공급자 대표 | party | supplier | string |
| `supplierAddress` | invoice_statement | 공급자 주소 | 공급자 주소 | address | supplier | string |
| `buyerCompany` | invoice_statement | 공급받는자 회사명 | 공급받는자 회사명, 거래처 | party | buyer | string |
| `buyerBizNumber` | invoice_statement | 공급받는자 사업자번호 | 공급받는자 사업자번호 | party | buyer | biznum |
| `buyerRepresentative` | invoice_statement | 공급받는자 대표자 | 공급받는자 대표자 | party | buyer | string |
| `buyerAddress` | invoice_statement | 공급받는자 주소 | 공급받는자 주소, 배송지 | address | buyer | string |
| `supplyAmount` | invoice_statement | 공급가액 | 공급가액, 공급가 | amount | any | money |
| `subtotal` | invoice_statement | 소계 | 소계 | summary | any | money |
| `cumulativeAmount` | invoice_statement | 누계 | 누계 | summary | any | money |
| `previousBalance` | invoice_statement | 전일잔액 | 전일잔액 | summary | any | money |
| `transactionAmount` | invoice_statement | 당일거래금액 | 당일거래금액 | summary | any | money |
| `cumulativeBalance` | invoice_statement | 누계잔액 | 누계잔액 | summary | any | money |
| `totalQuantity` | invoice_statement | 총수량 | 총수량 | summary | any | number |
| `issueDate` | invoice_statement, receipt | 발행일 | 발행일, 거래일자, 일자, date | date | any | date |
| `tableRows` | invoice_statement | 품목 표 | 품목, 명세 | table | any | string |

(영수증의 approvalNumber/cardNumber, finance의 bankName/accountMasked 등 운영 단계 추가 가능)

---

## 11. 권장 FieldMappingResult 구조

```typescript
type MappingStatus = "auto" | "ambiguous" | "manual" | "unmapped";

type FieldMappingCandidate = {
  canonicalField: string;
  confidence: number;        // 0~1
  reason: string;            // "alias_exact" | "alias_partial" | "region_position" | "documentType_default"
};

type FieldMappingResult = {
  fieldKey: string;          // 템플릿에 저장된 키 (예: "no_1" 또는 region.id)
  labelKo: string;
  labelEn?: string;
  documentType: string;      // 컨텍스트
  canonicalField: string | null;  // 최종 매핑 결과
  candidates: FieldMappingCandidate[];
  confidence: number;
  mappingStatus: MappingStatus;
  reason: string;
};
```

### 예시 (거래명세서 "회사명" 입력)

```json
{
  "fieldKey": "no_1",
  "labelKo": "회사명",
  "documentType": "invoice_statement",
  "canonicalField": null,
  "candidates": [
    { "canonicalField": "supplierCompany", "confidence": 0.5, "reason": "alias_exact_ambiguous_side" },
    { "canonicalField": "buyerCompany",    "confidence": 0.5, "reason": "alias_exact_ambiguous_side" }
  ],
  "confidence": 0.5,
  "mappingStatus": "ambiguous",
  "reason": "documentType=invoice_statement, alias 회사명은 supplier/buyer 양 측면 가능"
}
```

---

## 12. 권장 RuntimeFieldValue 구조

```typescript
type FieldSource =
  | "OCR"               // OCR raw
  | "NORM"              // parser normalization
  | "GT_REF"            // sample/company reference (party_master 또는 history)
  | "GT_SIMILARITY"     // GT/reference 부분 일치 보정
  | "TEMPLATE_REGION"   // region에서 raw 추출
  | "USER_EDIT"         // 사용자 수동 수정
  | "EMPTY";

type FieldStatus = "O" | "△" | "X" | "—" | "N/A";

type RuntimeFieldValue = {
  fieldKey: string;
  labelKo: string;
  canonicalField: string | null;
  value: string;
  source: FieldSource;
  status: FieldStatus;          // 운영에서는 confidence threshold 기반 또는 GT 비교 가능 시 GT 기반
  confidence: number;
  candidates?: Array<{
    value: string;
    source: FieldSource;
    confidence: number;
    reason: string;
  }>;
  debug?: {
    rawOcrValue?: string;
    normalizedValue?: string;
    referenceMatched?: { bizNumber: string; entry: any };
    rules?: string[];
  };
};
```

History 저장 시 이 구조를 그대로 직렬화하면 추후 디버깅/회귀 검증/통계 모두 가능.

---

## 13. 진행 순서 후보

| 순서 | 작업명 | 목적 | 선행 조건 | 예상 영향 | 위험도 | 추천 여부 |
|---|---|---|---|---|---|---|
| A | OP-1: canonical field registry / alias mapping 설계 | Test와 운영 사이 공통 spec 확립 | 없음 | 모든 운영 탭에 type만 추가 | 낮음 | ◯ |
| B | OP-2: Template 비정형 필드명 canonical 후보 매핑 UI/저장 | 사용자가 canonical 선택할 수 있게 | OP-1 | Template 저장 구조 확장 | 중간 | OP-1 후 |
| C | OP-3: RunOCR canonicalField 기반 출력 매핑 | OCR 결과를 canonical로 정규화 | OP-1, OP-2 | RunOCR 결과 구조 확장 | 중간 | OP-2 후 |
| D | OP-4: History 결과 저장 구조 확장 | canonical/status/debug 저장 | OP-3 | localStorage 스키마 변경 | 중간 | OP-3 후 |
| E | T-1: tableProfile별 tableRows 컬럼 정책 정리 | tableRows 컬럼 의미 정의 | 없음 | Test 탭 한정 | 낮음 | ◯ (T-1 결과 → registry에 추가) |
| F | T-2: Test UI tableRows column 표시 | UI 검증 | T-1 | Test 탭 한정 | 낮음 | T-1 후 |
| G | T-3: parser tableRows column extraction | invoice_statement.py 보강 | T-1 | parser 변경 | 중간 | T-2 후 (검증 가능해진 다음) |
| H | Template-Table-1: Template 고정/가변 그리드와 tableProfile 연결 | Template UI에 컬럼 의미 등록 | T-1, OP-1 | Template UI 확장 | 중간 | OP-2 와 병행 |
| I | RunOCR-Table-1: RunOCR tableRows 출력 구조 연결 | 운영에서 tableRows 표시 | T-3, OP-3 | RunOCR 결과 구조 확장 | 중간 | T-3 + OP-3 후 |

### 작업 간 의존성

```
T-1 (Test tableRows 정책)
  ├─→ T-2 (Test UI 표시)
  │   └─→ T-3 (parser column 추출)
  │       └─→ RunOCR-Table-1
  └─→ OP-1 (registry — table column 정의 포함)
        └─→ OP-2 (Template canonical UI)
              ├─→ Template-Table-1
              └─→ OP-3 (RunOCR canonical 매핑)
                    └─→ OP-4 (History 확장)
                          └─→ RunOCR-Table-1
```

---

## 14. 추천 진행 순서

**최소 안전 경로 (권장):**

1. **T-1**: tableProfile별 tableRows 컬럼 정책 정리 (Test 탭 영역 한정, 위험도 최저)
2. **T-2**: Test UI에서 tableRows 컬럼 표시 (T-1 검증)
3. **OP-1**: canonical field registry 설계 (tableRows 컬럼 정의도 포함)
4. **OP-2**: Template 비정형 canonical 후보 매핑 UI/저장 (사용자 입력 정규화)
5. **OP-3**: RunOCR canonical 기반 출력 + documentFields/financeFields 활용
6. **OP-4**: History 저장 구조 확장 (canonical/status/debug)
7. **T-3 / Template-Table-1 / RunOCR-Table-1**: 표 영역 운영 반영

이유:
- T-1/T-2는 Test 영역만 영향 — 운영 회귀 위험 없음
- T-1 결과 후 canonical registry에 table column 슬롯 정의가 가능해짐
- OP-1은 type 추가만 → 회귀 없음
- OP-2부터는 사용자 UX 변경 — 신중하게 점진 적용

**병행 가능한 분기:**
- T-1과 OP-1은 영향 영역이 다르므로 동시 진행 가능. 단 OP-1 최종 등록 시 T-1 결과를 반영해야 하므로 OP-1 완성은 T-1 후가 안전.

---

## 15. 표 작업 전 선행 필요 여부

| 질문 | 답변 |
|---|---|
| OP-1 (canonical registry) 필요 여부 | **표 작업 전에는 불필요**. T-1은 Test 영역만 영향. 다만 OP-1 자체를 T-1과 병행해도 무방. |
| OP-2 (Template canonical UI) 필요 여부 | **표 작업 전에는 불필요**. Template/RunOCR/History는 표 작업과 독립적 영역 |
| RunOCR/History 선반영 필요 여부 | **불필요**. 표 작업은 Test 탭에서 먼저 검증한 뒤 운영 반영 |
| T-1 바로 가능 여부 | **예** — party/address/amount 안정화 완료. T-1 진입 가능 |

---

## 16. 최종 결론

- **Test 탭의 정책 정리**(M-2f/GT-ADDR/R-1/R-2)는 잘 정리되어 있지만, **운영 탭(Template/RunOCR/History)에는 거의 반영되어 있지 않다.**
- 가장 큰 누락 항목: **canonicalField registry**, **documentType-aware 매핑**, **documentFields/financeFields 활용**, **tableRows 처리**.
- 단, 이들은 표 작업(T-1)의 전제 조건이 아니다. T-1은 Test 영역 내부에서 우선 검증하고, 그 결과를 OP-1 canonical registry에 반영하는 흐름이 가장 안전.
- **결론**: **T-1으로 바로 진입 가능**. OP-1~OP-4는 T-1과 병행 또는 T-1 이후 진행.

---

## 17. 변경 파일

- 리포트 파일만 생성: `public/data/testsets/invoice_statement/reports/OP0_test_vs_operation_structure_analysis_20260511.md`
- 코드 수정: **없음**
- 데이터 수정: **없음**

---

## 18. 검증

| 항목 | 결과 |
|---|---|
| typecheck 필요 여부 | 코드 수정 없어 필수 아님. 단 분석 중 type 파일 확인했으나 수정 없음 |
| build 필요 여부 | 불필요 |
| JSON parse 필요 여부 | 불필요 (이전 작업 R-1/R-2에서 이미 검증) |
