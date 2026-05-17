/**
 * profiles.ts — Test 탭 기준 profile 정책의 단일 진입점
 *
 * 설계 원칙 (docs/TEST_PROFILE_SCHEMA_20260427.md):
 *  - profile은 manifest documentType 기준으로만 결정. OCR 결과로 동적 변경 금지.
 *  - finance_slip은 suppression 기본값이 아니라 finance_profile 평가 대상.
 *  - profile에 없는 필드는 not_applicable (KPI 분모 제외, 시각적으로 "—").
 *  - 영수증 KPI와 finance KPI는 절대 같은 분모에 합치지 않는다.
 *
 * 이 파일은 타입/상수/매핑/헬퍼만 정의한다.
 * UI 컬럼 분기 · GT 확장 · finance parser는 별도 단계에서 진행.
 */

import type { DocumentType } from "./testsets";

// ============================================================
// Profile / Overlay 타입
// ============================================================

/** Test 탭 평가 기준 profile. */
export type Profile = "receipt" | "finance" | "document" | "none";

/** receipt_profile 위에 덧씌우는 overlay. */
export type Overlay = "card" | "medical";

/** resolveProfile() 반환값. */
export type ProfileResolution = {
  /** base profile */
  base: Profile;
  /** 활성 overlay 목록 (receipt 계열에만 해당, finance/none은 빈 배열) */
  overlays: Overlay[];
};

// ============================================================
// 컬럼 키 타입
// ============================================================

/**
 * receipt_profile 컬럼.
 * 기존 core/types.ts FieldKey ("회사명" 등)와 별개로 논리명 정의.
 * UI 렌더 시 FieldKey ↔ ReceiptFieldKey 매핑은 상위 레이어 책임.
 */
export type ReceiptFieldKey =
  | "companyName"
  | "bizNumber"
  | "totalAmount"
  | "representative"
  | "phone"
  | "address";

/** finance_profile 컬럼. */
export type FinanceFieldKey =
  | "bankName"
  | "transactionType"
  | "transactionDateTime"
  | "amount"
  | "balanceAfter"
  | "accountMasked"
  | "branchOrChannel"
  | "memo";

export type DocumentFieldKey =
  | "supplierCompany"
  | "supplierBizNumber"
  | "supplierRepresentative"
  | "supplierAddress"
  | "buyerCompany"
  | "buyerBizNumber"
  | "buyerRepresentative"
  | "buyerAddress"
  | "issueDate"
  | "supplyAmount"
  | "taxAmount"
  | "totalAmount"
  | "tableDetected"
  | "rowCount"
  | "firstRowPreview"
  | "subtotal"
  | "cumulativeAmount"
  | "previousBalance"
  | "transactionAmount"
  | "cumulativeBalance"
  | "totalQuantity";

/** card overlay 추가 컬럼. */
export type CardOverlayFieldKey =
  | "cardIssuer"
  | "cardNumberMasked"
  | "approvalNo"
  | "approvalDateTime"
  | "installment";

/** medical overlay 추가 컬럼 (1차: 표시만, KPI 비반영). */
export type MedicalOverlayFieldKey = "department" | "insuranceType";

/** 모든 컬럼 키의 유니온. */
export type AnyFieldKey =
  | ReceiptFieldKey
  | FinanceFieldKey
  | DocumentFieldKey
  | CardOverlayFieldKey
  | MedicalOverlayFieldKey;

// ============================================================
// Tier 정의 (docs/FINANCE_PARSER_TARGET_20260427.md §2)
// ============================================================

/** finance Tier-1: 1차 selected 판정 기준 필드. */
export const FINANCE_TIER1_FIELDS: readonly FinanceFieldKey[] = [
  "bankName",
  "transactionType",
  "transactionDateTime",
  "amount",
] as const;

/** finance Tier-2: 보조 필드 (없어도 selected 가능). */
export const FINANCE_TIER2_FIELDS: readonly FinanceFieldKey[] = [
  "balanceAfter",
  "accountMasked",
  "branchOrChannel",
  "memo",
] as const;

/** document(invoice_statement) 거래 당사자 필드 — 공급자/공급받는자 회사·사업자·대표·주소. */
export const DOCUMENT_PARTY_FIELDS: readonly DocumentFieldKey[] = [
  "supplierCompany",
  "supplierBizNumber",
  "supplierRepresentative",
  "supplierAddress",
  "buyerCompany",
  "buyerBizNumber",
  "buyerRepresentative",
  "buyerAddress",
] as const;

// ============================================================
// 컬럼 세트 상수
// ============================================================

/**
 * receipt_profile 컬럼 목록.
 * 필수(required) / 선택(optional) 구분 포함.
 */
export const RECEIPT_COLUMNS: readonly { key: ReceiptFieldKey; required: boolean }[] = [
  { key: "companyName",    required: true  },
  { key: "bizNumber",      required: true  },
  { key: "totalAmount",    required: true  },
  { key: "representative", required: false },
  { key: "phone",          required: false },
  { key: "address",        required: false },
] as const;

/**
 * finance_profile 컬럼 목록.
 * Tier-1은 required=true, Tier-2는 required=false.
 */
export const FINANCE_COLUMNS: readonly { key: FinanceFieldKey; required: boolean }[] = [
  { key: "bankName",            required: true  },
  { key: "transactionType",     required: true  },
  { key: "transactionDateTime", required: true  },
  { key: "amount",              required: true  },
  { key: "balanceAfter",        required: false },
  { key: "accountMasked",       required: false },
  { key: "branchOrChannel",     required: false },
  { key: "memo",                required: false },
] as const;

export const DOCUMENT_COLUMNS: readonly { key: DocumentFieldKey; required: boolean }[] = [
  { key: "supplierCompany",        required: true  },
  { key: "supplierBizNumber",      required: true  },
  { key: "supplierRepresentative", required: false },
  { key: "supplierAddress",        required: false },
  { key: "buyerCompany",           required: true  },
  { key: "buyerBizNumber",         required: false },
  { key: "buyerRepresentative",    required: false },
  { key: "buyerAddress",           required: false },
  { key: "issueDate",              required: true  },
  { key: "supplyAmount",           required: false },
  { key: "taxAmount",              required: false },
  { key: "totalAmount",            required: true  },
  { key: "tableDetected",          required: true  },
  { key: "rowCount",               required: false },
  { key: "firstRowPreview",        required: false },
  { key: "subtotal",               required: false },
  { key: "cumulativeAmount",       required: false },
  { key: "previousBalance",        required: false },
  { key: "transactionAmount",      required: false },
  { key: "cumulativeBalance",      required: false },
  { key: "totalQuantity",          required: false },
] as const;

/** card overlay 추가 컬럼 (전부 선택). */
export const CARD_OVERLAY_COLUMNS: readonly { key: CardOverlayFieldKey; required: boolean }[] = [
  { key: "cardIssuer",        required: false },
  { key: "cardNumberMasked",  required: false },
  { key: "approvalNo",        required: false },
  { key: "approvalDateTime",  required: false },
  { key: "installment",       required: false },
] as const;

/** medical overlay 추가 컬럼 (1차: 전부 선택, KPI 비반영). */
export const MEDICAL_OVERLAY_COLUMNS: readonly { key: MedicalOverlayFieldKey; required: boolean }[] = [
  { key: "department",    required: false },
  { key: "insuranceType", required: false },
] as const;

// ============================================================
// not_applicable 정의
// ============================================================

/**
 * finance_profile에서 not_applicable인 receipt 필드들.
 * 이 필드들은 finance_slip 문서의 KPI 분모에서 제외하고 "—"로 표시한다.
 */
const FINANCE_NOT_APPLICABLE: ReadonlySet<ReceiptFieldKey> = new Set<ReceiptFieldKey>([
  "companyName",
  "bizNumber",
  "representative",
  "phone",
  "address",
  "totalAmount",
]);

/**
 * receipt_profile에서 not_applicable인 finance 필드들.
 * finance 필드가 영수증 평가에 섞이지 않도록 한다.
 */
const RECEIPT_NOT_APPLICABLE: ReadonlySet<FinanceFieldKey> = new Set<FinanceFieldKey>([
  "bankName",
  "transactionType",
  "transactionDateTime",
  "amount",
  "balanceAfter",
  "accountMasked",
  "branchOrChannel",
  "memo",
]);

const DOCUMENT_FIELD_SET: ReadonlySet<DocumentFieldKey> = new Set<DocumentFieldKey>(
  DOCUMENT_COLUMNS.map((c) => c.key),
);

// ============================================================
// documentType → profile 매핑 (docs/TEST_PROFILE_SCHEMA §3)
// ============================================================

const DOCUMENT_TYPE_PROFILE_MAP: Record<DocumentType, ProfileResolution> = {
  pos_receipt:          { base: "receipt",  overlays: []                },
  food_cafe_receipt:    { base: "receipt",  overlays: []                },
  card_receipt:         { base: "receipt",  overlays: ["card"]          },
  medical_receipt:      { base: "receipt",  overlays: ["medical"]       },
  finance_slip:         { base: "finance",  overlays: []                },
  invoice_statement:    { base: "document", overlays: []                },
  tax_invoice:          { base: "document", overlays: []                },
  transaction_statement:{ base: "document", overlays: []                },
  unknown:              { base: "none",     overlays: []                },
};

// ============================================================
// 헬퍼 함수
// ============================================================

/**
 * documentType으로 profile을 결정한다.
 *
 * 원칙: manifest의 documentType이 profile을 결정한다.
 *   OCR 결과 기반 동적 변경 금지.
 *   알 수 없는 documentType 값이 오면 none으로 안전 처리.
 */
export function resolveProfile(documentType: string | undefined | null): ProfileResolution {
  if (!documentType) return { base: "none", overlays: [] };
  const mapped = DOCUMENT_TYPE_PROFILE_MAP[documentType as DocumentType];
  return mapped ?? { base: "none", overlays: [] };
}

/**
 * base profile의 기본 컬럼 키 목록을 반환한다.
 * document/none은 빈 배열 (아직 미구현 슬롯).
 */
export function getBaseColumns(profile: Profile): readonly AnyFieldKey[] {
  switch (profile) {
    case "receipt":  return RECEIPT_COLUMNS.map((c) => c.key);
    case "finance":  return FINANCE_COLUMNS.map((c) => c.key);
    case "document": return DOCUMENT_COLUMNS.map((c) => c.key);
    case "none":     return [];
  }
}

/**
 * overlay 목록에 해당하는 추가 컬럼 키 목록을 반환한다.
 */
export function getOverlayColumns(overlays: Overlay[]): readonly AnyFieldKey[] {
  const result: AnyFieldKey[] = [];
  for (const overlay of overlays) {
    if (overlay === "card")    result.push(...CARD_OVERLAY_COLUMNS.map((c) => c.key));
    if (overlay === "medical") result.push(...MEDICAL_OVERLAY_COLUMNS.map((c) => c.key));
  }
  return result;
}

/**
 * documentType을 받아 Test UI에서 보여줄 전체 컬럼 키 목록을 반환한다.
 * base 컬럼 + overlay 컬럼 순서.
 */
export function getVisibleColumns(documentType: string | undefined | null): readonly AnyFieldKey[] {
  const { base, overlays } = resolveProfile(documentType);
  return [...getBaseColumns(base), ...getOverlayColumns(overlays)];
}

/**
 * 해당 profile에서 fieldKey가 not_applicable인지 판단한다.
 *
 * not_applicable = KPI 분모 제외 + 시각적 "—" 표시.
 * no_baseline(GT 없음)과 의미가 다르므로 호출부에서 구분해야 한다.
 */
export function isNotApplicableField(
  profile: Profile,
  fieldKey: string,
): boolean {
  switch (profile) {
    case "finance":
      return FINANCE_NOT_APPLICABLE.has(fieldKey as ReceiptFieldKey);
    case "receipt":
      return RECEIPT_NOT_APPLICABLE.has(fieldKey as FinanceFieldKey);
    case "document":
      return !DOCUMENT_FIELD_SET.has(fieldKey as DocumentFieldKey);
    case "none":
      return true; // 미구현 profile: 모든 필드 not_applicable
  }
}

/**
 * finance_profile에서 Tier-1 필드인지 반환한다.
 * (selected 판정 기준 필드 = Tier-1 전원 추출 필요)
 */
export function isFinanceTier1(fieldKey: FinanceFieldKey): boolean {
  return (FINANCE_TIER1_FIELDS as readonly string[]).includes(fieldKey);
}

/**
 * documentType mismatch 경고용 — profile과 OCR 신호가 충돌하는지 확인 힌트.
 * 실제 판단은 상위 레이어(UI/경고 배지)에서 수행하고,
 * 이 함수는 profile을 동적으로 바꾸지 않는다.
 *
 * @returns true = manifest documentType 재검토 권장 (profile_suspected_mismatch)
 */
export function isProfileMismatchSuspected(
  documentType: string | undefined | null,
  ocrDocType: string | undefined | null,
): boolean {
  if (!documentType || !ocrDocType) return false;
  const { base } = resolveProfile(documentType);
  // OCR 분류기가 finance(bank_slip)인데 manifest가 receipt 계열이거나 그 반대
  const ocrIsFinance = ocrDocType === "bank_slip";
  const manifestIsFinance = base === "finance";
  return ocrIsFinance !== manifestIsFinance;
}

// ============================================================
// KPI family 분류 (docs/TEST_SUPPRESSION_POLICY_NOTE §7)
// ============================================================

export type KpiFamily =
  | "receipt"      // 영수증 정확도 KPI
  | "finance"      // 금융전표 추출률 KPI
  | "document"     // 미구현 (예약)
  | "none";        // suppressed/unknown 카운트만

/**
 * documentType이 속하는 KPI family를 반환한다.
 * 영수증 KPI와 finance KPI를 절대 같은 분모에 합치지 않기 위한 경계선.
 */
export function resolveKpiFamily(documentType: string | undefined | null): KpiFamily {
  const { base } = resolveProfile(documentType);
  return base as KpiFamily;
}
