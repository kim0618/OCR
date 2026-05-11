# OP-1 canonicalField registry 설계 리포트

작성일: 2026-05-11  
직전 작업: T-2 (T2_test_ui_tableRows_column_validation_20260511.md), OP-0  
참고: T-1, R-1, R-2, OP-0

---

## 1. 작업 목적

영수증과 거래명세서, 그리고 T-1/T-2에서 정의한 tableRows 컬럼까지 공통으로 사용할 canonicalField registry를 설계한다.  
이후 Template 비정형 필드명 자동매칭(OP-2), RunOCR canonical 기반 출력(OP-3), History 저장 구조 확장(OP-4), T-3 parser tableRows 추출의 기준이 된다.

코드 수정: **src/lib/canonicalFields.ts 신규 생성** (기존 운영 코드 import 없음 — 운영 동작 변경 없음)

---

## 2. 전제

- 이번 작업은 설계 기준 수립이다. Template/RunOCR/History 실제 동작 변경은 OP-2 이후.
- canonicalFields.ts는 독립 파일이며, 현재 어떤 운영 코드에도 import되지 않는다.
- 기존 Test 탭 판정(O/△/X), party_master, GT_REF 로직 변경 없음.
- 거래명세서 invoice_statement.py 수정 없음.

---

## 3. canonicalField가 필요한 이유

### 현재 문제 (OP-0 분석 결과)

| 문제 | 현상 |
|---|---|
| 사용자 라벨 기반 매핑 | "회사명" 입력 시 영수증인지 거래명세서인지, 공급자인지 공급받는자인지 알 수 없음 |
| documentType 무관 처리 | Template은 문서 종류에 상관없이 동일한 raw 영역 매칭만 수행 |
| alias 통일 없음 | autofillEngine은 runtime only alias, Test 탭은 별도 normalize — 같은 의미 필드가 다른 키로 처리 |
| tableRows 컬럼 의미 없음 | 컬럼 좌표만 있고 품명/수량/단가/금액 의미 없음 |
| source/status 분기 불일치 | Test 탭: GT_REF/GT_SIMILARITY/NORM/OCR / 운영: ocr/biz/gt/text 4종 |

### canonicalField 도입 효과

1. 사용자 입력 라벨 → canonicalField 변환으로 alias 통일
2. documentType + side로 거래명세서 양쪽 주체 처리
3. isTableColumn 플래그로 문서 필드와 행 단위 컬럼 분리
4. T-3 parser tableRows 출력 시 canonicalField 키 사용 → Test 탭 expectedColumns와 일치
5. History에 canonicalField 저장 → 추후 집계/검색 가능

---

## 4. 타입 설계 초안

### DocumentTypeKey
```typescript
type DocumentTypeKey = "receipt" | "invoice_statement" | "finance_slip" | "unknown";
```

### CanonicalFieldDefinition
```typescript
type CanonicalFieldDefinition = {
  canonicalField: string;          // 내부 canonical 키 (camelCase)
  labelKo: string;                 // 한글 표시 라벨
  labelEn?: string;                // 영문 표시 라벨
  documentTypes: DocumentTypeKey[];
  group: CanonicalFieldGroup;      // party / merchant / document / amount / summary / table / payment / metadata
  side: CanonicalFieldSide;        // supplier / buyer / merchant / none
  valueType: CanonicalValueType;   // text / number / amount / date / quantity / code / address / phone / businessNumber / boolean
  aliases: string[];               // 사용자가 입력할 수 있는 라벨 목록
  isTableColumn: boolean;          // true = tableRows 행 단위 컬럼
  isAutoFillTarget: boolean;       // true = history/party_master 자동채움 대상
  requiresSideDisambiguation: boolean; // true = side 미명시 시 ambiguous
};
```

### FieldMappingResult
```typescript
type FieldMappingResult = {
  fieldKey: string;
  labelKo: string;
  documentType?: DocumentTypeKey;
  canonicalField?: string;            // ambiguous이면 undefined
  candidates: FieldMappingCandidate[];
  confidence: number;
  mappingStatus: MappingStatus;       // auto / ambiguous / manual / unmapped
  reason: string;
};
```

### RuntimeFieldValue
```typescript
type RuntimeFieldValue = {
  fieldKey: string;
  labelKo: string;
  canonicalField?: string;
  value: string;
  source: RuntimeValueSource;  // OCR / NORM / GT_REF / GT_SIMILARITY / TEMPLATE_REGION / AUTO_FILL / USER_EDIT / EMPTY
  status?: FieldStatus;        // O / △ / X / — / N/A
  confidence?: number;
  debug?: Record<string, unknown>;
};
```

---

## 5. 영수증 canonical fields

| canonicalField | labelKo | group | valueType | aliases | 처리 |
|---|---|---|---|---|---|
| merchantName | 가맹점명 | merchant | text | 상호, 가맹점명, 매장명, 업체명, 회사명, 사업장명 | auto |
| merchantBizNumber | 사업자번호 | merchant | businessNumber | 사업자번호, 등록번호, 사업자 No | auto |
| merchantRepresentative | 대표자 | merchant | text | 대표자, 대표, 성명 | auto |
| merchantAddress | 주소 | merchant | address | 주소, 소재지, 사업장주소 | auto |
| merchantPhone | 전화번호 | merchant | phone | 전화번호, 전화, TEL, 연락처 | auto |
| issueDate | 거래/발행일 | document | date | 거래일자, 발행일, 날짜, 일자 | auto |
| supplyAmount | 공급가액 | amount | amount | 공급가액, 공급가, 공급금액 | auto |
| taxAmount | 세액 | amount | amount | 세액, 부가세, VAT | auto |
| totalAmount | 합계금액 | amount | amount | 합계, 총액, 합계금액, 결제금액 | auto |
| paymentAmount | 결제금액 | payment | amount | 결제금액, 승인금액, 청구금액 | auto |
| cardNumber | 카드번호 | payment | code | 카드번호, 카드 번호 | auto |
| approvalNumber | 승인번호 | payment | code | 승인번호, 인증번호 | auto |
| installment | 할부 | payment | text | 할부, 할부개월 | auto |
| paymentMethod | 결제수단 | payment | text | 결제수단, 지불방법 | auto |
| receiptNo | 영수증번호 | metadata | code | 영수증번호, 영수번호 | auto |

**영수증 특성**: 단일 주체(merchant) 구조이므로 회사명/사업자번호/대표자/주소 모두 auto 매핑 가능.

---

## 6. 거래명세서 canonical fields

### 6.1 Party 필드

| canonicalField | labelKo | group | side | valueType | aliases | 처리 |
|---|---|---|---|---|---|---|
| supplierCompany | 공급자 상호 | party | supplier | text | 공급자 상호, 공급자 회사명, 공급자, 판매자, 발행자, 매출처 | auto (side token 있으면) |
| supplierBizNumber | 공급자 사업자번호 | party | supplier | businessNumber | 공급자 사업자번호, 공급자 등록번호 | auto |
| supplierRepresentative | 공급자 대표자 | party | supplier | text | 공급자 대표자, 공급자 대표 | auto |
| supplierAddress | 공급자 주소 | party | supplier | address | 공급자 주소, 공급자 소재지 | auto |
| buyerCompany | 공급받는자 상호 | party | buyer | text | 공급받는자 상호, 거래처명, 구매자, 받는자, 매입처 | auto (side token 있으면) |
| buyerBizNumber | 공급받는자 사업자번호 | party | buyer | businessNumber | 공급받는자 사업자번호, 거래처 사업자번호 | auto |
| buyerRepresentative | 공급받는자 대표자 | party | buyer | text | 공급받는자 대표자, 거래처 대표자 | auto |
| buyerAddress | 공급받는자 주소 | party | buyer | address | 공급받는자 주소, 납품처 주소, 배송지 | auto |

### 6.2 Document / Amount / Summary 필드

| canonicalField | labelKo | group | side | valueType | aliases | 처리 |
|---|---|---|---|---|---|---|
| issueDate | 거래/발행일 | document | none | date | 거래일자, 작성일자, 발행일 | auto |
| supplyAmount | 공급가액 | amount | none | amount | 공급가액, 공급가, 공급금액 | auto |
| taxAmount | 세액 | amount | none | amount | 세액, 부가세, VAT | auto |
| totalAmount | 합계금액 | amount | none | amount | 합계, 합계금액, 총액 | auto |
| subtotal | 소계 | summary | none | amount | 소계 | auto |
| cumulativeAmount | 누계 | summary | none | amount | 누계, 누계금액 | auto |
| previousBalance | 전일잔액 | summary | none | amount | 전일잔액, 이전잔액 | auto |
| transactionAmount | 당일거래금액 | summary | none | amount | 당일거래금액, 거래금액 | auto |
| cumulativeBalance | 누계잔액 | summary | none | amount | 누계잔액, 잔액 | auto |
| totalQuantity | 총수량 | summary | none | quantity | 총수량, 합계수량 | auto |
| tableDetected | 품목표 존재 | metadata | none | boolean | — | system |
| rowCount | 행 수 | metadata | none | number | 행 수, 행수 | system |
| firstRowPreview | 첫 행 미리보기 | metadata | none | text | 첫 행 | system |

---

## 7. tableRows canonical columns (isTableColumn=true)

| canonicalColumn | labelKo | valueType | aliases (대표) | required 후보 | 비고 |
|---|---|---|---|---|---|
| rowIndex | 행번호 | number | NO, 번호, 순번 | optional | 미리 인쇄된 행 번호 |
| itemCode | 품목코드 | code | 품목코드, 코드, 제품코드 | lot_serial: optional, item_quantity: required | ERP 코드 |
| itemName | 품목명 | text | 품명, 품목, 품목명, 상품명, 제품명 | **모든 profile 필수** | 가장 중요한 컬럼 |
| spec | 규격 | text | 규격, 규격명, 포장, 용량 | optional | 의약품 중심 |
| lotNo | LOT/제조번호 | code | Lot, LOT, 제조번호, 로트번호 | lot_serial: required | 배치 단위 추적 |
| serialNo | Serial | code | Serial, S/N, 시리얼, 시리얼/로트No. | serial: required | 개별 unit 식별 |
| manufacturingNo | 제조번호 | code | 제조번호(별도) | optional | lotNo와 통합 권장 |
| expiryDate | 유효기간 | date | 유효기간, 유효일자, 사용기한 | optional | YYYYMMDD / YYMMDD |
| quantity | 수량 | quantity | 수량, Qty, 출고수량 | **모든 profile 필수** | |
| unit | 단위 | text | 단위, EA, BOX | optional | |
| unitPrice | 단가 | amount | 단가, 공급단가, 소비자단가 | conditional | 금액 있는 profile |
| supplyAmount | 공급가액(행) | amount | 공급금액, 공급가액 | conditional | '공급금액/공급가액' 라벨 시 |
| taxAmount | 세액(행) | amount | 세액, 부가세 | optional | 행 단위 세액 |
| amount | 금액 | amount | 금액, 행금액 | conditional | '금액' 라벨 시 |
| totalAmount | 합계금액(행) | amount | 합계금액(행) | optional | amount + taxAmount |
| manufacturer | 제조사 | text | 제조사, 제조원, 제조회사 | optional | 의약품 중심 |
| insuranceCode | 보험코드 | code | 보험코드, 보험NO, 급여코드 | optional | 의약품 보험 코드 |
| remark | 비고 | text | 비고, 적요, 메모 | optional | |

---

## 8. documentType별 alias 해석 차이

| 입력 라벨 | 영수증 매핑 | 거래명세서 매핑 | 처리 |
|---|---|---|---|
| 회사명 | merchantName (auto) | supplierCompany / buyerCompany (**ambiguous**) | 거래명세서: side 토큰 선택 필요 |
| 상호명 | merchantName (auto) | supplierCompany / buyerCompany (**ambiguous**) | 위와 동일 |
| 가맹점명 | merchantName (auto) | 해당 없음 | 영수증 전용 |
| 상호 | merchantName (auto) | supplierCompany / buyerCompany (**ambiguous**) | |
| 사업자번호 | merchantBizNumber (auto) | supplierBizNumber / buyerBizNumber (**ambiguous**) | |
| 등록번호 | merchantBizNumber (auto) | supplierBizNumber / buyerBizNumber (**ambiguous**) | |
| 대표자 | merchantRepresentative (auto) | supplierRepresentative / buyerRepresentative (**ambiguous**) | |
| 주소 | merchantAddress (auto) | supplierAddress / buyerAddress (**ambiguous**) | |
| 전화번호 | merchantPhone (auto) | supplierAddress 주변 필드 (weak signal) | |
| 공급가액 | supplyAmount (auto) | supplyAmount (auto) | 동일 canonical |
| 세액 / 부가세 | taxAmount (auto) | taxAmount (auto) | 동일 canonical |
| 합계 / 합계금액 | totalAmount (auto) | totalAmount (auto) | 동일 canonical |
| 거래일자 | issueDate (auto) | issueDate (auto) | 동일 canonical |
| 공급자 상호 | 해당 없음 | supplierCompany (auto) | side token "공급자" 확정 |
| 공급받는자 상호 | 해당 없음 | buyerCompany (auto) | side token "공급받는자" 확정 |

---

## 9. ambiguous 처리 정책

### 9.1 ambiguous 발생 조건

1. 거래명세서에서 "회사명/상호명/사업자번호/대표자/주소" 처럼 side 없는 라벨 입력
2. 하나의 alias가 2개 이상의 candidateField에 매핑되는 경우

### 9.2 ambiguous 해소 방법 (우선순위 순)

| 방법 | 설명 | 자동 처리 가능 |
|---|---|---|
| **Side token 분석** | 입력 라벨에 "공급자/공급받는자/거래처/납품처" 포함 여부 확인 | 예 |
| **Region 위치 기반** | Template에서 region이 문서 좌측(공급자)/우측(공급받는자) 위치에 있으면 side 추론 | 부분 |
| **사용자 선택** | Template UI에서 후보 드롭다운 제시 → 사용자 선택 | 수동 |
| **Prefix 가이드** | 사용자에게 "공급자 회사명", "공급받는자 사업자번호" 입력 권장 | 가이드 |

### 9.3 Side token 목록

```typescript
const SUPPLIER_SIDE_TOKENS = ["공급자", "판매자", "발행자", "공급하는자", "매출처"];
const BUYER_SIDE_TOKENS = ["공급받는자", "구매자", "받는자", "거래처", "매입처", "수신자", "납품처"];
```

### 9.4 Table column context

- 사용자가 Template에서 table field를 정의하는 경우: `isTableColumn=true` context
- 일반 field context의 "금액" != table column context의 "금액(행)"
- mapping engine은 context flag로 분리 처리

---

## 10. FieldMappingResult 예시

### 10.1 거래명세서 — ambiguous 케이스 (회사명)

```json
{
  "fieldKey": "no_1",
  "labelKo": "회사명",
  "documentType": "invoice_statement",
  "canonicalField": null,
  "candidates": [
    {
      "canonicalField": "supplierCompany",
      "confidence": 0.55,
      "reason": "alias_ambiguous_side"
    },
    {
      "canonicalField": "buyerCompany",
      "confidence": 0.55,
      "reason": "alias_ambiguous_side"
    }
  ],
  "confidence": 0.55,
  "mappingStatus": "ambiguous",
  "reason": "후보 2개 — side 토큰 또는 사용자 선택 필요"
}
```

### 10.2 거래명세서 — auto 케이스 (공급자 상호)

```json
{
  "fieldKey": "no_2",
  "labelKo": "공급자 상호",
  "documentType": "invoice_statement",
  "canonicalField": "supplierCompany",
  "candidates": [
    {
      "canonicalField": "supplierCompany",
      "confidence": 0.9,
      "reason": "alias_exact"
    }
  ],
  "confidence": 0.9,
  "mappingStatus": "auto",
  "reason": "alias_exact"
}
```

### 10.3 영수증 — auto 케이스 (회사명)

```json
{
  "fieldKey": "no_1",
  "labelKo": "회사명",
  "documentType": "receipt",
  "canonicalField": "merchantName",
  "candidates": [
    {
      "canonicalField": "merchantName",
      "confidence": 0.9,
      "reason": "alias_exact"
    }
  ],
  "confidence": 0.9,
  "mappingStatus": "auto",
  "reason": "alias_exact"
}
```

### 10.4 거래명세서 table column — itemName

```json
{
  "fieldKey": "col_1",
  "labelKo": "품명",
  "documentType": "invoice_statement",
  "canonicalField": "itemName",
  "candidates": [
    {
      "canonicalField": "itemName",
      "confidence": 0.9,
      "reason": "alias_exact"
    }
  ],
  "confidence": 0.9,
  "mappingStatus": "auto",
  "reason": "alias_exact"
}
```

---

## 11. RuntimeFieldValue 예시

### 11.1 OCR 추출 성공

```json
{
  "fieldKey": "no_1",
  "labelKo": "공급자 상호",
  "canonicalField": "supplierCompany",
  "value": "부광약품(주)",
  "source": "OCR",
  "status": "O",
  "confidence": 0.94
}
```

### 11.2 GT_REF 자동채움 (party_master 기반)

```json
{
  "fieldKey": "no_1",
  "labelKo": "공급자 대표자",
  "canonicalField": "supplierRepresentative",
  "value": "LEE WOO HYUN",
  "source": "GT_REF",
  "status": "△",
  "confidence": 0.85,
  "debug": {
    "bizNumber": "118-81-00450",
    "masterMatched": true,
    "rawOcrValue": "LEE WOOHVON"
  }
}
```

### 11.3 tableRows 행 단위 값

```json
{
  "fieldKey": "col_itemName",
  "labelKo": "품목명",
  "canonicalField": "itemName",
  "value": "헥사메던액0.12%",
  "source": "TEMPLATE_REGION",
  "status": null,
  "confidence": 0.97
}
```

---

## 12. Template 적용 설계

### 12.1 현재 한계 (OP-0 분석)

- Template 필드 `name`이 사용자 라벨 = 매핑 키 = 표시 라벨로 통합되어 있음
- canonicalField 슬롯 없음
- table column context 없음

### 12.2 목표 구조 (OP-2 설계 기준)

```typescript
// Region에 canonicalField 슬롯 추가
type Region = {
  id: string;
  name: string;              // 사용자 입력 라벨 (유지)
  canonicalField?: string;   // 추가: 매핑된 canonical key
  mappingStatus?: MappingStatus; // 추가: auto / ambiguous / manual / unmapped
  fieldType: FieldType;
  // ... 기존 필드
};

// TableColumn에 canonicalColumn 슬롯 추가
type TableColumn = {
  index: number;
  label: string;             // 사용자 입력 컬럼 라벨
  canonicalColumn?: string;  // 추가: canonical column key
  required?: boolean;
};
```

### 12.3 Template 저장 흐름 (OP-2 이후)

```
1. 사용자가 Template에서 필드 이름 입력
   ↓
2. resolveAliasMapping(label, documentType) 호출
   ↓
3. auto → canonicalField 자동 저장
   ambiguous → UI에서 후보 드롭다운 표시 → 사용자 선택 후 저장
   unmapped → canonicalField=undefined로 저장 (label만 보존)
   ↓
4. Template 저장 시 canonicalField 포함
```

---

## 13. RunOCR 적용 설계

### 13.1 현재 한계 (OP-0 분석)

- `documentFields`(invoice_statement 추출 결과) 미활용
- label-based 매핑만 있어 canonical 정규화 없음
- tableRows 처리 부재

### 13.2 목표 구조 (OP-3 설계 기준)

```typescript
// OCR 결과 응답에 canonicalField 추가
type OcrFieldResult = {
  name: string;           // 사용자 라벨 (유지)
  canonicalField?: string; // 추가
  value: string;
  source: RuntimeValueSource; // 추가 (OCR/NORM/GT_REF 등)
  status?: FieldStatus;    // 추가 (GT 비교 시)
  confidence: number;
  // ... 기존 필드
};

// tableRows 출력 추가
type OcrResult = {
  fields: OcrFieldResult[];
  tableRows?: TableRowOutput[]; // 추가: T-3 이후
  tableMeta?: TableMetaOutput;  // 추가: T-3 이후
};
```

### 13.3 RunOCR 매핑 흐름 (OP-3 이후)

```
1. Template의 canonicalField 목록 로드
   ↓
2. OCR 응답의 documentFields/financeFields를 canonicalField 기준으로 매핑
   ↓
3. amountProfile 기반 N/A 필드 처리
   ↓
4. tableRows (T-3 이후): tableMeta + tableRows 배열 포함
   ↓
5. OcrFieldResult에 canonicalField + source + status 포함하여 반환
```

---

## 14. History 적용 설계

### 14.1 현재 한계 (OP-0 분석)

- canonicalField 없음 → 같은 의미 필드를 다른 라벨로 저장한 기록 검색 불가
- documentType 분류 없음 → 영수증/거래명세서 통계 분리 불가
- tableRows 저장 슬롯 없음

### 14.2 목표 구조 (OP-4 설계 기준)

```typescript
// History 출력 필드에 canonicalField/source/status 추가
type HistoryOutputField = {
  no?: number;
  en: string;
  ko: string;              // 사용자 라벨 (유지)
  canonicalField?: string; // 추가
  original: string;
  modified: string;
  confidence: number;
  source: RuntimeValueSource; // 확장 (기존 "ocr"/"biz" → RuntimeValueSource)
  status?: FieldStatus;    // 추가
  applied?: string;
  autofillAction?: string;
};

// History run record에 documentType + tableRows 추가
type HistoryRunRecord = {
  // ... 기존 필드
  documentType?: string;   // 추가
  tableRows?: TableRowOutput[]; // 추가 (T-3 이후)
};
```

---

## 15. 단계별 진행 계획

| 순서 | 작업명 | 내용 | 선행 조건 | 위험도 |
|---|---|---|---|---|
| **T-3** | parser tableRows column extraction | invoice_statement.py에서 tableRows 배열 + canonicalColumn 키로 출력 | T-1, T-2 완료 | 중간 |
| **OP-2** | Template 비정형 canonical 매핑 UI | resolveAliasMapping 연결, ambiguous 드롭다운 UI | OP-1 완료 | 중간 |
| **OP-3** | RunOCR canonical 기반 출력 매핑 | documentFields 활용 + canonicalField 기반 매핑 | OP-1, OP-2 완료 | 중간 |
| **OP-4** | History 저장 구조 확장 | canonicalField/status/debug 저장 | OP-3 완료 | 중간 |
| **Template-Table-1** | Template 고정/가변 그리드 column mapping | T-1 컬럼 정책 + OP-2 canonical 연결 | OP-2, T-3 완료 | 중간 |
| **RunOCR-Table-1** | RunOCR tableRows 출력 연결 | T-3 + OP-3 완료 | 중간 |

---

## 16. 이번 작업에서 코드 반영 여부

| 항목 | 결과 |
|---|---|
| `src/lib/canonicalFields.ts` | **신규 생성** — 타입/상수/헬퍼 정의 |
| 기존 운영 코드 import | **없음** — 독립 파일, 운영 동작 변경 없음 |
| invoice_statement.py | **수정 없음** |
| ground_truth.json | **수정 없음** |
| manifest.json | **수정 없음** |
| typecheck | ✅ pass |

### canonicalFields.ts 구성 요약

| 섹션 | 내용 |
|---|---|
| Type definitions | DocumentTypeKey, CanonicalFieldGroup, CanonicalFieldSide, CanonicalValueType, MappingStatus, RuntimeValueSource, FieldStatus, CanonicalFieldDefinition, FieldMappingResult, RuntimeFieldValue |
| RECEIPT_FIELDS | 영수증 11개 field (merchantName ~ receiptNo) |
| INVOICE_PARTY_FIELDS | 거래명세서 party 8개 field (supplier/buyer 4개씩) |
| COMMON_FIELDS | 공통 4개 field (issueDate, supplyAmount, taxAmount, totalAmount) |
| INVOICE_SUMMARY_FIELDS | 거래명세서 summary 6개 field |
| INVOICE_META_FIELDS | 시스템 meta 3개 field (tableDetected, rowCount, firstRowPreview) |
| TABLE_COLUMN_FIELDS | tableRows 18개 컬럼 (isTableColumn=true) |
| CANONICAL_FIELD_REGISTRY | 전체 통합 배열 (총 50개 entry) |
| INVOICE_AMBIGUOUS_ALIASES | side 미명시 ambiguous alias 10개 |
| SUPPLIER_SIDE_TOKENS / BUYER_SIDE_TOKENS | side 확정 토큰 목록 |
| lookupCanonical() | canonical 키로 entry 검색 |
| getCanonicalFieldsForDocType() | documentType 기준 field 목록 반환 |
| resolveAliasMapping() | 사용자 라벨 → canonical 후보 변환 |

---

## 17. 다음 추천 작업

| 후보 | 설명 | 선행 조건 | 위험도 |
|---|---|---|---|
| **T-3** | parser tableRows column extraction 1차 | T-1, T-2, OP-1 완료 | 중간 |
| **OP-2** | Template 비정형 필드명 canonical 후보 매핑 | OP-1 완료 | 중간 |
| T-4 | Test UI actual tableRows 검증 | T-3 완료 | 낮음 |
| Template-Table-1 | 고정/가변 그리드 column mapping | OP-2, T-3 완료 | 중간 |

### 추천: **T-3** (parser tableRows column extraction 1차)

추천 이유:
1. T-3에서 invoice_statement.py가 tableRows를 canonicalColumn 키로 출력하면, T-2의 Test UI에서 `extractionStatus="parser_not_ready"`가 즉시 해소됨
2. T-3은 OCR 인식 로직 수정이 아니라 parser 출력 구조 추가이므로 회귀 위험이 관리 가능한 수준
3. OP-1에서 확정된 canonicalField registry가 T-3 parser 출력 키의 기준이 됨

병행 가능: **OP-2** — Template canonical 매핑 UI는 T-3과 독립적. 단, OP-2 최종 완성은 T-3 이후 tableRows column 매핑까지 포함해야 완전해짐.
