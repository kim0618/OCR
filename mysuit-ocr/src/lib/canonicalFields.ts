/**
 * canonicalFields.ts — OP-1: 영수증/거래명세서 공통 canonicalField registry
 *
 * 설계 원칙:
 *  - 사용자 입력 라벨과 내부 canonicalField를 분리한다.
 *  - documentType별 alias 해석이 달라지며, 거래명세서는 supplier/buyer 측면 모호성을 처리한다.
 *  - isTableColumn=true 항목은 tableRows 행 단위 컬럼이다.
 *  - 이 파일은 타입/상수/헬퍼만 정의한다. Template/RunOCR/History 연결은 OP-2 이후.
 */

// ============================================================
// DocumentType Keys
// ============================================================

export type DocumentTypeKey =
  | "receipt"
  | "invoice_statement"
  | "finance_slip"
  | "unknown";

// ============================================================
// Field Group / Side / ValueType
// ============================================================

/** 필드 분류 그룹. */
export type CanonicalFieldGroup =
  | "party"      // 거래 당사자 식별 (supplier/buyer/merchant)
  | "merchant"   // 영수증 전용 가맹점 정보
  | "document"   // 문서 메타데이터 (issueDate 등)
  | "amount"     // 문서 단위 금액 합계
  | "summary"    // 보조 합계/잔액/누계
  | "table"      // 표 행 단위 컬럼 (isTableColumn=true)
  | "payment"    // 결제 수단 정보 (영수증 전용)
  | "metadata";  // 시스템 메타 (tableDetected, rowCount 등)

/** 거래 당사자 측면. 영수증은 "merchant", 거래명세서는 "supplier"/"buyer", 공통은 "none". */
export type CanonicalFieldSide = "supplier" | "buyer" | "merchant" | "none";

/** 값 유형. */
export type CanonicalValueType =
  | "text"
  | "number"
  | "amount"
  | "date"
  | "quantity"
  | "code"
  | "address"
  | "phone"
  | "businessNumber"
  | "boolean";

// ============================================================
// Mapping / Status
// ============================================================

/** 필드 자동매칭 상태. */
export type MappingStatus = "auto" | "ambiguous" | "manual" | "unmapped";

/** OCR 결과 값의 출처. */
export type RuntimeValueSource =
  | "OCR"              // OCR raw 추출
  | "NORM"             // parser normalization 보정
  | "GT_REF"           // party_master / reference DB 자동채움
  | "GT_SIMILARITY"    // partial/similarity 보정
  | "TEMPLATE_REGION"  // template region 기반 추출
  | "AUTO_FILL"        // history 기반 자동채움
  | "USER_EDIT"        // 사용자 수동 수정
  | "EMPTY";           // 값 없음

/** 판정 상태. Test 탭 O/△/X 기준과 동일. */
export type FieldStatus = "O" | "△" | "X" | "—" | "N/A";

// ============================================================
// Core Definition Type
// ============================================================

export type CanonicalFieldDefinition = {
  /** 내부 canonical 키. 공백/특수문자 없는 camelCase. */
  canonicalField: string;
  /** 한글 표시 라벨. */
  labelKo: string;
  /** 영문 표시 라벨 (선택). */
  labelEn?: string;
  /** 이 필드가 속하는 문서 유형 목록. */
  documentTypes: DocumentTypeKey[];
  /** 필드 분류 그룹. */
  group: CanonicalFieldGroup;
  /** 거래 당사자 측면. 해당 없으면 "none". */
  side: CanonicalFieldSide;
  /** 값 유형. */
  valueType: CanonicalValueType;
  /** 사용자가 입력할 수 있는 alias 목록 (한글/영문 혼용). */
  aliases: string[];
  /** true = tableRows 행 단위 컬럼. false = 문서 단위 필드. */
  isTableColumn: boolean;
  /** true = history/party_master 기반 자동채움 대상. */
  isAutoFillTarget: boolean;
  /** true = 거래명세서에서 supplier/buyer 측면 명시 없으면 ambiguous. */
  requiresSideDisambiguation: boolean;
  /** 설명 (선택). */
  description?: string;
};

// ============================================================
// Mapping Result Types
// ============================================================

export type FieldMappingCandidate = {
  canonicalField: string;
  confidence: number;
  reason: string;
};

export type FieldMappingResult = {
  /** 템플릿에서 저장된 필드 키. */
  fieldKey: string;
  /** 사용자 입력 한글 라벨. */
  labelKo: string;
  /** 매핑 컨텍스트 문서 유형. */
  documentType?: DocumentTypeKey;
  /** 최종 확정된 canonicalField (ambiguous이면 null). */
  canonicalField?: string;
  /** 후보 목록 (confidence 내림차순). */
  candidates: FieldMappingCandidate[];
  /** 최종 선택 신뢰도. */
  confidence: number;
  /** 매핑 상태. */
  mappingStatus: MappingStatus;
  /** 매핑 결정 이유 설명. */
  reason: string;
};

export type RuntimeFieldValue = {
  fieldKey: string;
  labelKo: string;
  canonicalField?: string;
  value: string;
  source: RuntimeValueSource;
  status?: FieldStatus;
  confidence?: number;
  debug?: Record<string, unknown>;
};

// ============================================================
// Registry — 영수증 canonical fields
// ============================================================

const RECEIPT_FIELDS: CanonicalFieldDefinition[] = [
  {
    canonicalField: "merchantName",
    labelKo: "가맹점명",
    labelEn: "Merchant Name",
    documentTypes: ["receipt"],
    group: "merchant",
    side: "merchant",
    valueType: "text",
    aliases: ["상호", "상호명", "가맹점명", "매장명", "업체명", "회사명", "사업장명", "점포명", "상점명"],
    isTableColumn: false,
    isAutoFillTarget: true,
    requiresSideDisambiguation: false,
  },
  {
    canonicalField: "merchantBizNumber",
    labelKo: "사업자번호",
    labelEn: "Business Registration Number",
    documentTypes: ["receipt"],
    group: "merchant",
    side: "merchant",
    valueType: "businessNumber",
    aliases: ["사업자번호", "사업자등록번호", "등록번호", "사업자 No", "사업자No", "사업자 번호", "bizNo"],
    isTableColumn: false,
    isAutoFillTarget: false,
    requiresSideDisambiguation: false,
  },
  {
    canonicalField: "merchantRepresentative",
    labelKo: "대표자",
    labelEn: "Representative",
    documentTypes: ["receipt"],
    group: "merchant",
    side: "merchant",
    valueType: "text",
    aliases: ["대표자", "대표자명", "대표", "성명", "대표자 성명"],
    isTableColumn: false,
    isAutoFillTarget: true,
    requiresSideDisambiguation: false,
  },
  {
    canonicalField: "merchantAddress",
    labelKo: "주소",
    labelEn: "Address",
    documentTypes: ["receipt"],
    group: "merchant",
    side: "merchant",
    valueType: "address",
    aliases: ["주소", "사업장주소", "소재지", "사업장소재지", "사업장 주소"],
    isTableColumn: false,
    isAutoFillTarget: true,
    requiresSideDisambiguation: false,
  },
  {
    canonicalField: "merchantPhone",
    labelKo: "전화번호",
    labelEn: "Phone",
    documentTypes: ["receipt"],
    group: "merchant",
    side: "merchant",
    valueType: "phone",
    aliases: ["전화번호", "전화", "TEL", "Tel", "연락처", "대표번호", "전화 번호"],
    isTableColumn: false,
    isAutoFillTarget: false,
    requiresSideDisambiguation: false,
  },
  {
    canonicalField: "paymentAmount",
    labelKo: "결제금액",
    labelEn: "Payment Amount",
    documentTypes: ["receipt"],
    group: "payment",
    side: "none",
    valueType: "amount",
    aliases: ["결제금액", "승인금액", "청구금액", "결제 금액", "지불금액"],
    isTableColumn: false,
    isAutoFillTarget: false,
    requiresSideDisambiguation: false,
  },
  {
    canonicalField: "cardNumber",
    labelKo: "카드번호",
    labelEn: "Card Number",
    documentTypes: ["receipt"],
    group: "payment",
    side: "none",
    valueType: "code",
    aliases: ["카드번호", "카드 번호", "카드No", "card number"],
    isTableColumn: false,
    isAutoFillTarget: false,
    requiresSideDisambiguation: false,
  },
  {
    canonicalField: "approvalNumber",
    labelKo: "승인번호",
    labelEn: "Approval Number",
    documentTypes: ["receipt"],
    group: "payment",
    side: "none",
    valueType: "code",
    aliases: ["승인번호", "승인 번호", "인증번호", "거래번호"],
    isTableColumn: false,
    isAutoFillTarget: false,
    requiresSideDisambiguation: false,
  },
  {
    canonicalField: "installment",
    labelKo: "할부",
    labelEn: "Installment",
    documentTypes: ["receipt"],
    group: "payment",
    side: "none",
    valueType: "text",
    aliases: ["할부", "할부개월", "할부 개월"],
    isTableColumn: false,
    isAutoFillTarget: false,
    requiresSideDisambiguation: false,
  },
  {
    canonicalField: "paymentMethod",
    labelKo: "결제수단",
    labelEn: "Payment Method",
    documentTypes: ["receipt"],
    group: "payment",
    side: "none",
    valueType: "text",
    aliases: ["결제수단", "지불방법", "결제방법", "지불수단"],
    isTableColumn: false,
    isAutoFillTarget: false,
    requiresSideDisambiguation: false,
  },
  {
    canonicalField: "receiptNo",
    labelKo: "영수증번호",
    labelEn: "Receipt Number",
    documentTypes: ["receipt"],
    group: "metadata",
    side: "none",
    valueType: "code",
    aliases: ["영수증번호", "영수번호", "영수증 번호"],
    isTableColumn: false,
    isAutoFillTarget: false,
    requiresSideDisambiguation: false,
  },
];

// ============================================================
// Registry — 거래명세서 party / document / amount / summary fields
// ============================================================

const INVOICE_PARTY_FIELDS: CanonicalFieldDefinition[] = [
  {
    canonicalField: "supplierCompany",
    labelKo: "공급자 상호",
    documentTypes: ["invoice_statement"],
    group: "party",
    side: "supplier",
    valueType: "text",
    aliases: [
      "공급자상호", "공급자 상호", "공급자 회사명", "공급자회사명",
      "공급자", "판매자", "발행자", "공급하는자", "매출처",
    ],
    isTableColumn: false,
    isAutoFillTarget: true,
    requiresSideDisambiguation: false,
    description: "side token '공급자/판매자'로 auto 가능",
  },
  {
    canonicalField: "supplierBizNumber",
    labelKo: "공급자 사업자번호",
    documentTypes: ["invoice_statement"],
    group: "party",
    side: "supplier",
    valueType: "businessNumber",
    aliases: [
      "공급자 사업자번호", "공급자사업자번호",
      "공급자 사업자등록번호", "공급자 등록번호",
    ],
    isTableColumn: false,
    isAutoFillTarget: false,
    requiresSideDisambiguation: false,
  },
  {
    canonicalField: "supplierRepresentative",
    labelKo: "공급자 대표자",
    documentTypes: ["invoice_statement"],
    group: "party",
    side: "supplier",
    valueType: "text",
    aliases: ["공급자 대표자", "공급자 대표", "공급자대표자"],
    isTableColumn: false,
    isAutoFillTarget: true,
    requiresSideDisambiguation: false,
  },
  {
    canonicalField: "supplierAddress",
    labelKo: "공급자 주소",
    documentTypes: ["invoice_statement"],
    group: "party",
    side: "supplier",
    valueType: "address",
    aliases: ["공급자 주소", "공급자주소", "공급자 소재지", "공급자 사업장주소"],
    isTableColumn: false,
    isAutoFillTarget: false,
    requiresSideDisambiguation: false,
  },
  {
    canonicalField: "buyerCompany",
    labelKo: "공급받는자 상호",
    documentTypes: ["invoice_statement"],
    group: "party",
    side: "buyer",
    valueType: "text",
    aliases: [
      "공급받는자상호", "공급받는자 상호", "공급받는자 회사명",
      "공급받는자", "구매자", "받는자", "거래처명", "매입처", "수신자",
    ],
    isTableColumn: false,
    isAutoFillTarget: true,
    requiresSideDisambiguation: false,
    description: "side token '공급받는자/거래처'로 auto 가능",
  },
  {
    canonicalField: "buyerBizNumber",
    labelKo: "공급받는자 사업자번호",
    documentTypes: ["invoice_statement"],
    group: "party",
    side: "buyer",
    valueType: "businessNumber",
    aliases: [
      "공급받는자 사업자번호", "공급받는자사업자번호",
      "거래처 사업자번호", "거래처 등록번호",
    ],
    isTableColumn: false,
    isAutoFillTarget: false,
    requiresSideDisambiguation: false,
  },
  {
    canonicalField: "buyerRepresentative",
    labelKo: "공급받는자 대표자",
    documentTypes: ["invoice_statement"],
    group: "party",
    side: "buyer",
    valueType: "text",
    aliases: ["공급받는자 대표자", "공급받는자 대표", "거래처 대표자"],
    isTableColumn: false,
    isAutoFillTarget: true,
    requiresSideDisambiguation: false,
  },
  {
    canonicalField: "buyerAddress",
    labelKo: "공급받는자 주소",
    documentTypes: ["invoice_statement"],
    group: "party",
    side: "buyer",
    valueType: "address",
    aliases: [
      "공급받는자 주소", "공급받는자주소", "납품처 주소",
      "배송지", "거래처 주소", "수신자 주소",
    ],
    isTableColumn: false,
    isAutoFillTarget: false,
    requiresSideDisambiguation: false,
  },
];

// ============================================================
// 공통 필드 — receipt + invoice_statement 양쪽에서 사용
// ============================================================

const COMMON_FIELDS: CanonicalFieldDefinition[] = [
  {
    canonicalField: "issueDate",
    labelKo: "거래/발행일",
    labelEn: "Issue Date",
    documentTypes: ["receipt", "invoice_statement"],
    group: "document",
    side: "none",
    valueType: "date",
    aliases: [
      "거래일자", "발행일", "영수일자", "작성일자", "날짜", "일자",
      "거래 일자", "작성 일자", "invoice date",
    ],
    isTableColumn: false,
    isAutoFillTarget: false,
    requiresSideDisambiguation: false,
  },
  {
    canonicalField: "supplyAmount",
    labelKo: "공급가액",
    labelEn: "Supply Amount",
    documentTypes: ["receipt", "invoice_statement"],
    group: "amount",
    side: "none",
    valueType: "amount",
    aliases: ["공급가액", "공급가", "공급금액", "공급액"],
    isTableColumn: false,
    isAutoFillTarget: false,
    requiresSideDisambiguation: false,
  },
  {
    canonicalField: "taxAmount",
    labelKo: "세액",
    labelEn: "Tax Amount",
    documentTypes: ["receipt", "invoice_statement"],
    group: "amount",
    side: "none",
    valueType: "amount",
    aliases: ["세액", "부가세", "VAT", "vat", "부가가치세"],
    isTableColumn: false,
    isAutoFillTarget: false,
    requiresSideDisambiguation: false,
  },
  {
    canonicalField: "totalAmount",
    labelKo: "합계금액",
    labelEn: "Total Amount",
    documentTypes: ["receipt", "invoice_statement"],
    group: "amount",
    side: "none",
    valueType: "amount",
    aliases: [
      "합계", "합계금액", "총액", "총합계", "총합계금액",
      "결제금액", "청구금액", "총금액",
    ],
    isTableColumn: false,
    isAutoFillTarget: false,
    requiresSideDisambiguation: false,
  },
];

const INVOICE_SUMMARY_FIELDS: CanonicalFieldDefinition[] = [
  {
    canonicalField: "subtotal",
    labelKo: "소계",
    documentTypes: ["invoice_statement"],
    group: "summary",
    side: "none",
    valueType: "amount",
    aliases: ["소계"],
    isTableColumn: false,
    isAutoFillTarget: false,
    requiresSideDisambiguation: false,
  },
  {
    canonicalField: "cumulativeAmount",
    labelKo: "누계",
    documentTypes: ["invoice_statement"],
    group: "summary",
    side: "none",
    valueType: "amount",
    aliases: ["누계", "누계금액"],
    isTableColumn: false,
    isAutoFillTarget: false,
    requiresSideDisambiguation: false,
  },
  {
    canonicalField: "previousBalance",
    labelKo: "전일잔액",
    documentTypes: ["invoice_statement"],
    group: "summary",
    side: "none",
    valueType: "amount",
    aliases: ["전일잔액", "이전잔액", "전잔"],
    isTableColumn: false,
    isAutoFillTarget: false,
    requiresSideDisambiguation: false,
  },
  {
    canonicalField: "transactionAmount",
    labelKo: "당일거래금액",
    documentTypes: ["invoice_statement"],
    group: "summary",
    side: "none",
    valueType: "amount",
    aliases: ["당일거래금액", "금일거래금액", "거래금액"],
    isTableColumn: false,
    isAutoFillTarget: false,
    requiresSideDisambiguation: false,
  },
  {
    canonicalField: "cumulativeBalance",
    labelKo: "누계잔액",
    documentTypes: ["invoice_statement"],
    group: "summary",
    side: "none",
    valueType: "amount",
    aliases: ["누계잔액", "잔액"],
    isTableColumn: false,
    isAutoFillTarget: false,
    requiresSideDisambiguation: false,
  },
  {
    canonicalField: "totalQuantity",
    labelKo: "총수량",
    documentTypes: ["invoice_statement"],
    group: "summary",
    side: "none",
    valueType: "quantity",
    aliases: ["총수량", "총 수량", "합계수량"],
    isTableColumn: false,
    isAutoFillTarget: false,
    requiresSideDisambiguation: false,
  },
];

// 시스템 메타 (Test 탭 판정 필드, 운영에서는 hidden 처리)
const INVOICE_META_FIELDS: CanonicalFieldDefinition[] = [
  {
    canonicalField: "tableDetected",
    labelKo: "품목표 존재",
    documentTypes: ["invoice_statement"],
    group: "metadata",
    side: "none",
    valueType: "boolean",
    aliases: [],
    isTableColumn: false,
    isAutoFillTarget: false,
    requiresSideDisambiguation: false,
  },
  {
    canonicalField: "rowCount",
    labelKo: "행 수",
    documentTypes: ["invoice_statement"],
    group: "metadata",
    side: "none",
    valueType: "number",
    aliases: ["행 수", "행수", "품목 수"],
    isTableColumn: false,
    isAutoFillTarget: false,
    requiresSideDisambiguation: false,
  },
  {
    canonicalField: "firstRowPreview",
    labelKo: "첫 행 미리보기",
    documentTypes: ["invoice_statement"],
    group: "metadata",
    side: "none",
    valueType: "text",
    aliases: ["첫 행"],
    isTableColumn: false,
    isAutoFillTarget: false,
    requiresSideDisambiguation: false,
  },
];

// ============================================================
// Registry — 거래명세서 tableRows 컬럼 (isTableColumn=true)
// ============================================================

const TABLE_COLUMN_FIELDS: CanonicalFieldDefinition[] = [
  {
    canonicalField: "rowIndex",
    labelKo: "행번호",
    documentTypes: ["invoice_statement"],
    group: "table",
    side: "none",
    valueType: "number",
    aliases: ["NO", "번호", "순번", "순서"],
    isTableColumn: true,
    isAutoFillTarget: false,
    requiresSideDisambiguation: false,
  },
  {
    canonicalField: "itemCode",
    labelKo: "품목코드",
    documentTypes: ["invoice_statement"],
    group: "table",
    side: "none",
    valueType: "code",
    aliases: ["품목코드", "코드", "상품코드", "제품코드", "단품코드"],
    isTableColumn: true,
    isAutoFillTarget: false,
    requiresSideDisambiguation: false,
  },
  {
    canonicalField: "itemName",
    labelKo: "품목명",
    documentTypes: ["invoice_statement"],
    group: "table",
    side: "none",
    valueType: "text",
    aliases: ["품명", "품목", "품목명", "상품명", "제품명", "약품명", "내역"],
    isTableColumn: true,
    isAutoFillTarget: false,
    requiresSideDisambiguation: false,
  },
  {
    canonicalField: "spec",
    labelKo: "규격",
    documentTypes: ["invoice_statement"],
    group: "table",
    side: "none",
    valueType: "text",
    aliases: ["규격", "규격명", "포장", "용량"],
    isTableColumn: true,
    isAutoFillTarget: false,
    requiresSideDisambiguation: false,
  },
  {
    canonicalField: "lotNo",
    labelKo: "LOT/제조번호",
    documentTypes: ["invoice_statement"],
    group: "table",
    side: "none",
    valueType: "code",
    aliases: ["Lot", "LOT", "Lot No", "LOT NO", "LotNo.", "로트번호", "제조번호", "제조번호/로트"],
    isTableColumn: true,
    isAutoFillTarget: false,
    requiresSideDisambiguation: false,
  },
  {
    canonicalField: "serialNo",
    labelKo: "Serial",
    documentTypes: ["invoice_statement"],
    group: "table",
    side: "none",
    valueType: "code",
    aliases: ["Serial", "S/N", "시리얼", "일련번호", "serial", "시리얼/로트No."],
    isTableColumn: true,
    isAutoFillTarget: false,
    requiresSideDisambiguation: false,
  },
  {
    canonicalField: "manufacturingNo",
    labelKo: "제조번호",
    documentTypes: ["invoice_statement"],
    group: "table",
    side: "none",
    valueType: "code",
    aliases: ["제조번호(별도)", "제조NO", "제조 No"],
    isTableColumn: true,
    isAutoFillTarget: false,
    requiresSideDisambiguation: false,
  },
  {
    canonicalField: "expiryDate",
    labelKo: "유효기간",
    documentTypes: ["invoice_statement"],
    group: "table",
    side: "none",
    valueType: "date",
    aliases: ["유효기간", "유효일자", "사용기한", "유효기한"],
    isTableColumn: true,
    isAutoFillTarget: false,
    requiresSideDisambiguation: false,
  },
  {
    canonicalField: "quantity",
    labelKo: "수량",
    documentTypes: ["invoice_statement"],
    group: "table",
    side: "none",
    valueType: "quantity",
    aliases: ["수량", "Qty", "QTY", "수", "출고수량", "수량(EA)"],
    isTableColumn: true,
    isAutoFillTarget: false,
    requiresSideDisambiguation: false,
  },
  {
    canonicalField: "unit",
    labelKo: "단위",
    documentTypes: ["invoice_statement"],
    group: "table",
    side: "none",
    valueType: "text",
    aliases: ["단위", "단위규격", "EA", "BOX"],
    isTableColumn: true,
    isAutoFillTarget: false,
    requiresSideDisambiguation: false,
  },
  {
    canonicalField: "unitPrice",
    labelKo: "단가",
    documentTypes: ["invoice_statement"],
    group: "table",
    side: "none",
    valueType: "amount",
    aliases: ["단가", "공급단가", "소비자단가"],
    isTableColumn: true,
    isAutoFillTarget: false,
    requiresSideDisambiguation: false,
  },
  {
    canonicalField: "supplyAmount",
    labelKo: "공급가액(행)",
    documentTypes: ["invoice_statement"],
    group: "table",
    side: "none",
    valueType: "amount",
    aliases: ["공급금액", "공급가액", "공급액"],
    isTableColumn: true,
    isAutoFillTarget: false,
    requiresSideDisambiguation: false,
    description: "행 단위 공급가액. 문서 단위 supplyAmount와 구분은 isTableColumn=true로 식별.",
  },
  {
    canonicalField: "taxAmount",
    labelKo: "세액(행)",
    documentTypes: ["invoice_statement"],
    group: "table",
    side: "none",
    valueType: "amount",
    aliases: ["세액", "부가세", "VAT"],
    isTableColumn: true,
    isAutoFillTarget: false,
    requiresSideDisambiguation: false,
    description: "행 단위 세액. 문서 단위 taxAmount와 구분은 isTableColumn=true로 식별.",
  },
  {
    canonicalField: "amount",
    labelKo: "금액",
    documentTypes: ["invoice_statement"],
    group: "table",
    side: "none",
    valueType: "amount",
    aliases: ["금액", "행금액"],
    isTableColumn: true,
    isAutoFillTarget: false,
    requiresSideDisambiguation: false,
    description: "컬럼 라벨이 '금액'인 경우. '공급금액/공급가액' 라벨이면 supplyAmount 사용.",
  },
  {
    canonicalField: "totalAmount",
    labelKo: "합계금액(행)",
    documentTypes: ["invoice_statement"],
    group: "table",
    side: "none",
    valueType: "amount",
    aliases: ["합계금액(행)", "합계(행)"],
    isTableColumn: true,
    isAutoFillTarget: false,
    requiresSideDisambiguation: false,
  },
  {
    canonicalField: "manufacturer",
    labelKo: "제조사",
    documentTypes: ["invoice_statement"],
    group: "table",
    side: "none",
    valueType: "text",
    aliases: ["제조사", "제조원", "회사", "제조회사"],
    isTableColumn: true,
    isAutoFillTarget: false,
    requiresSideDisambiguation: false,
  },
  {
    canonicalField: "insuranceCode",
    labelKo: "보험코드",
    documentTypes: ["invoice_statement"],
    group: "table",
    side: "none",
    valueType: "code",
    aliases: ["보험코드", "보험NO", "보험번호", "보험약가코드", "급여코드"],
    isTableColumn: true,
    isAutoFillTarget: false,
    requiresSideDisambiguation: false,
  },
  {
    canonicalField: "remark",
    labelKo: "비고",
    documentTypes: ["invoice_statement"],
    group: "table",
    side: "none",
    valueType: "text",
    aliases: ["비고", "적요", "메모"],
    isTableColumn: true,
    isAutoFillTarget: false,
    requiresSideDisambiguation: false,
  },
];

// ============================================================
// 모호성 필드 — 거래명세서에서 side 미명시 시 ambiguous
// ============================================================

/**
 * 거래명세서에서 "회사명/상호명" 같이 side가 없는 입력 라벨의 후보 처리.
 * Template 비정형 필드명 매핑 시 이 목록으로 ambiguous 여부 판단한다.
 */
export const INVOICE_AMBIGUOUS_ALIASES: Record<string, string[]> = {
  "회사명":   ["supplierCompany", "buyerCompany"],
  "상호명":   ["supplierCompany", "buyerCompany"],
  "업체명":   ["supplierCompany", "buyerCompany"],
  "상호":     ["supplierCompany", "buyerCompany"],
  "사업자번호":  ["supplierBizNumber", "buyerBizNumber"],
  "사업자등록번호": ["supplierBizNumber", "buyerBizNumber"],
  "등록번호":  ["supplierBizNumber", "buyerBizNumber"],
  "대표자":   ["supplierRepresentative", "buyerRepresentative"],
  "대표자명":  ["supplierRepresentative", "buyerRepresentative"],
  "대표":     ["supplierRepresentative", "buyerRepresentative"],
  "주소":     ["supplierAddress", "buyerAddress"],
};

/**
 * 거래명세서에서 supplier side로 확정하는 토큰 목록.
 * 입력 라벨에 이 토큰이 포함되면 supplierXxx로 매핑.
 */
export const SUPPLIER_SIDE_TOKENS = ["공급자", "판매자", "발행자", "공급하는자", "매출처"] as const;

/**
 * 거래명세서에서 buyer side로 확정하는 토큰 목록.
 * 입력 라벨에 이 토큰이 포함되면 buyerXxx로 매핑.
 */
export const BUYER_SIDE_TOKENS = [
  "공급받는자", "구매자", "받는자", "거래처", "매입처", "수신자", "납품처",
] as const;

// ============================================================
// 통합 Registry
// ============================================================

export const CANONICAL_FIELD_REGISTRY: readonly CanonicalFieldDefinition[] = [
  ...RECEIPT_FIELDS,
  ...INVOICE_PARTY_FIELDS,
  ...COMMON_FIELDS,
  ...INVOICE_SUMMARY_FIELDS,
  ...INVOICE_META_FIELDS,
  ...TABLE_COLUMN_FIELDS,
] as const;

// ============================================================
// Helper Functions
// ============================================================

/**
 * canonicalField 키로 registry entry를 찾는다.
 * isTableColumn 플래그로 문서 단위/행 단위 구분 가능.
 */
export function lookupCanonical(
  canonicalField: string,
  opts?: { isTableColumn?: boolean },
): CanonicalFieldDefinition | undefined {
  return CANONICAL_FIELD_REGISTRY.find(
    (e) =>
      e.canonicalField === canonicalField &&
      (opts?.isTableColumn === undefined || e.isTableColumn === opts.isTableColumn),
  );
}

/**
 * documentType 기준으로 해당 문서의 canonical field 목록 반환.
 * isTableColumn 플래그로 문서 필드 / 행 필드 분리 가능.
 */
export function getCanonicalFieldsForDocType(
  documentType: DocumentTypeKey,
  opts?: { isTableColumn?: boolean },
): CanonicalFieldDefinition[] {
  return CANONICAL_FIELD_REGISTRY.filter(
    (e) =>
      e.documentTypes.includes(documentType) &&
      (opts?.isTableColumn === undefined || e.isTableColumn === opts.isTableColumn),
  );
}

/**
 * 사용자 입력 라벨을 받아 documentType 컨텍스트에서 canonical 후보 목록 반환.
 * 영수증 → auto / 거래명세서 → side 토큰 없으면 ambiguous.
 */
export function resolveAliasMapping(
  labelInput: string,
  documentType: DocumentTypeKey,
  opts?: { isTableColumn?: boolean },
): FieldMappingResult {
  const label = labelInput.trim();
  const isTableCtx = opts?.isTableColumn ?? false;

  // alias 전체 비교 (정규화: 공백 제거 + 소문자)
  const norm = (s: string) => s.replace(/\s+/g, "").toLowerCase();
  const normLabel = norm(label);

  const candidates: FieldMappingCandidate[] = [];

  for (const entry of CANONICAL_FIELD_REGISTRY) {
    if (!entry.documentTypes.includes(documentType)) continue;
    if (entry.isTableColumn !== isTableCtx) continue;
    const aliasMatch = entry.aliases.some((a) => norm(a) === normLabel);
    const labelMatch = norm(entry.labelKo) === normLabel;
    if (aliasMatch || labelMatch) {
      candidates.push({
        canonicalField: entry.canonicalField,
        confidence: aliasMatch ? 0.9 : 0.7,
        reason: aliasMatch ? "alias_exact" : "label_match",
      });
    }
  }

  // 거래명세서: ambiguous alias (회사명/사업자번호/대표자/주소) 검사
  if (documentType === "invoice_statement" && !isTableCtx) {
    const ambiguousCandidates = INVOICE_AMBIGUOUS_ALIASES[label];
    if (ambiguousCandidates && candidates.length === 0) {
      for (const cf of ambiguousCandidates) {
        candidates.push({ canonicalField: cf, confidence: 0.55, reason: "alias_ambiguous_side" });
      }
    }
  }

  if (candidates.length === 0) {
    return {
      fieldKey: label,
      labelKo: label,
      documentType,
      canonicalField: undefined,
      candidates: [],
      confidence: 0,
      mappingStatus: "unmapped",
      reason: "alias 매칭 없음",
    };
  }

  if (candidates.length === 1) {
    return {
      fieldKey: label,
      labelKo: label,
      documentType,
      canonicalField: candidates[0].canonicalField,
      candidates,
      confidence: candidates[0].confidence,
      mappingStatus: candidates[0].confidence >= 0.8 ? "auto" : "manual",
      reason: candidates[0].reason,
    };
  }

  // 복수 후보 → ambiguous
  return {
    fieldKey: label,
    labelKo: label,
    documentType,
    canonicalField: undefined,
    candidates,
    confidence: Math.max(...candidates.map((c) => c.confidence)),
    mappingStatus: "ambiguous",
    reason: `후보 ${candidates.length}개 — side 토큰 또는 사용자 선택 필요`,
  };
}
