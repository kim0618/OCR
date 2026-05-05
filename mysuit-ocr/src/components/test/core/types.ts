export type FieldKey = "회사명" | "사업자번호" | "대표자" | "tel" | "주소" | "총합계금액";

export type Entry = Record<FieldKey, string>;

export const EMPTY_ENTRY = (): Entry => ({
  회사명: "", 사업자번호: "", 대표자: "", tel: "", 주소: "", 총합계금액: "",
});

export type FieldMeta = {
  key: FieldKey;
  label: string;
  allowAutofill: boolean;
};

export const FIELDS: FieldMeta[] = [
  { key: "회사명",     label: "회사명",    allowAutofill: true  },
  { key: "사업자번호", label: "사업자번호", allowAutofill: true  },
  { key: "대표자",     label: "대표자",    allowAutofill: true  },
  { key: "tel",       label: "전화번호",   allowAutofill: true  },
  { key: "주소",      label: "주소",      allowAutofill: true  },
  { key: "총합계금액", label: "총 합계금액", allowAutofill: false },
];

export const AUTOFILLABLE_FIELDS: FieldKey[] = FIELDS.filter((f) => f.allowAutofill).map((f) => f.key);

export type GtRecord = {
  fields: Entry;
  type: string;
  updated_at: string;
  /** finance_profile 기준값 (bankName / transactionType / transactionDateTime / amount 등) */
  financeFields?: Record<string, string>;
  documentFields?: Record<string, string>;
};
export const EMPTY_GT = (): GtRecord => ({ fields: EMPTY_ENTRY(), type: "영수증", updated_at: "" });

export type OcrCacheRecord = { ocr_text: string; scanned_at: string };

export type OcrResponse = {
  fields: { name: string; field_type: string; value: string; confidence: number; bbox: number[] }[];
  full_text: string;
  receipt_fields?: Partial<Entry>;
  /** finance_profile Tier-1 추출 결과 (doc_type=bank_slip일 때만 포함) */
  finance_fields?: Record<string, string>;
  document_fields?: Record<string, string>;
  invoice_fields?: Record<string, string>;
  /** finance_profile review 사유 코드 목록 (내부 감사용) */
  finance_review_reasons?: string[];
  status?: string;
  doc_type?: string;
  processing_time: number;
  processed_image?: string;
};

export type OcrEntry = {
  raw: Entry;            // 서버 receipt_fields 또는 fallback 원본
  normalized: Entry;     // 정규화된 값
  fullText: string;
  displayUrl: string;
  processingTime: number;
  scannedAt: string;
  status?: string;
  docType?: string;
  /** finance_profile Tier-1 값 (bankName / transactionType / transactionDateTime / amount) */
  financeFields?: Record<string, string>;
  documentFields?: Record<string, string>;
  /** finance_profile review 사유 코드 목록 */
  financeReviewReasons?: string[];
};

export type AutofillSource = "biz" | "text";

export type BizMatchReasonCode =
  | "biz_exact"           // 사업자번호 체크섬+완전 일치
  | "company_partial"     // 회사명 부분 일치 (긍정)
  | "owner_match"         // 대표자명 일치 (긍정)
  | "addr_region_match"   // 주소 시/도 일치 (긍정)
  | "no_corroboration"    // 회사명/대표자 어느 것도 OCR 텍스트에 없음 (경고)
  | "fax_context";        // 사업자번호가 FAX 문맥에만 존재 (경고, 오추출 가능성)

export type BizMatchReason = {
  code: BizMatchReasonCode;
  delta: number;                    // confidence 증감
  note: string;
};

export type AutofillSuggestion = {
  source: AutofillSource;
  matchedFrom: string;              // 출처 파일명
  confidence: number;               // 0~1
  score?: number;                   // text similarity 점수
  fields: Partial<Entry>;           // 자동복원 후보 필드값 (금액 제외)
  reasons?: BizMatchReason[];       // biz 매칭 신뢰도 산출 근거 (감사/디버그용)
  suggestedAt: string;
};

/**
 * autofill 상태 레코드.
 *
 *  ⚠️ 주의 ⚠️
 *  - 이것은 ground_truth 가 아니다.
 *  - 이것은 "자동복원 제안(suggestions) + 세션 적용(appliedSource)" 의 기록이며,
 *    디버깅·감사·재현 목적의 부가 캐시다.
 *  - 파일 저장소는 public/images/autofill_cache.json 이며, GT 와 분리되어 있다.
 *  - 사용자가 "기준값으로 확정" 액션을 수행해야만 값이 ground_truth.json 에 반영된다.
 */
export type AutofillRecord = {
  suggestions: AutofillSuggestion[];
  appliedSource: AutofillSource | null;   // 세션에서 사용자가 적용한 source
  appliedAt?: string;
};

export type ValueSourceTag =
  | "empty"
  | "ocr"
  | "ocr_normalized"
  | "gt_similarity"
  | "gt_anchor_empty"
  | "gt_anchor_weak_value"
  | "gt_anchor_override"
  | "autofill_biz"
  | "autofill_text_suggestion"
  | "gt_only"
  | "user_confirmed";

export type FieldView = {
  gt: string;
  ocrRaw: string;
  ocrNormalized: string;
  autofillValue: string;
  autofillSource: AutofillSource | null;
  autofillConfidence: number;
  autofillMatchedFrom: string | null;
  autofillAutoApplicable: boolean;  // biz + high confidence
  autofillApplied: boolean;
  finalValue: string;
  finalSource: ValueSourceTag;
  finalReason?: string;
};

// threshold
export const BIZ_AUTO_APPLY_CONFIDENCE = 0.9;   // biz match 자동적용 하한
export const TEXT_SUGGEST_THRESHOLD    = 0.7;   // text similarity 제안 하한
export const MATCH_THRESHOLD           = 0.6;   // 필드 유사도 OK 하한
