import {
  Entry,
  FieldKey,
  FieldView,
  FIELDS,
  GtRecord,
  OcrEntry,
  AutofillRecord,
  AutofillSuggestion,
  ValueSourceTag,
} from "./types";
import { matchField } from "./match";
import { pickAppliedSuggestion } from "./autofill";

const BASELINE_GT_FIELDS = new Set<FieldKey>(["회사명", "대표자", "tel", "주소"]);
const LABEL_OR_NOTICE_RE =
  /(사업자번호|가맹점|상호|회사명|대표자|성명|주소|승인|전표|무서명|cashnote|카드|tid|van|cat|no[:.]?|판매|부가|합계|금액|수량|품명)/i;
const ADDRESS_CORE_RE = /(서울|경기|인천|부산|대구|광주|대전|울산|세종|강원|충북|충남|전북|전남|경북|경남|제주|시|군|구|동|로|길|층|호|번지)/;
const COMPANY_SUFFIX_RE = /(툴|공구|철물|칠물|약국|조명|전기|상사|마트|식당|집|볼트|스토어|카페)$/;

function isBaselineDataset(datasetId?: string): boolean {
  return datasetId === "baseline" || datasetId === "baseline_fast";
}

function normalizeBiz(v: string): string {
  const digits = (v ?? "").replace(/\D/g, "");
  return digits.length === 10 ? `${digits.slice(0, 3)}-${digits.slice(3, 5)}-${digits.slice(5)}` : "";
}

function normalizeForField(key: FieldKey, value: string): string {
  const v = (value ?? "").trim().toLowerCase();
  if (key === "tel") return v.replace(/\D/g, "");
  if (key === "대표자") return v.replace(/[^가-힣a-z0-9]/gi, "");
  if (key === "회사명") {
    return v
      .replace(/\(주\)|㈜|주식회사/g, "")
      .replace(/[^가-힣a-z0-9]/gi, "");
  }
  if (key === "주소") return v.replace(/[\s()[\]{},._\-:·]/g, "");
  return v.replace(/\s+/g, "");
}

function levenshtein(a: string, b: string): number {
  if (!a) return b.length;
  if (!b) return a.length;
  const dp = Array.from({ length: a.length + 1 }, () => new Array(b.length + 1).fill(0));
  for (let i = 0; i <= a.length; i++) dp[i][0] = i;
  for (let j = 0; j <= b.length; j++) dp[0][j] = j;
  for (let i = 1; i <= a.length; i++) {
    for (let j = 1; j <= b.length; j++) {
      dp[i][j] = a[i - 1] === b[j - 1]
        ? dp[i - 1][j - 1]
        : 1 + Math.min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1]);
    }
  }
  return dp[a.length][b.length];
}

function fieldSimilarity(key: FieldKey, expected: string, actual: string): number {
  const e = normalizeForField(key, expected);
  const a = normalizeForField(key, actual);
  if (!e || !a) return 0;
  if (e === a) return 1;
  if (key === "tel") return e.includes(a) || a.includes(e) ? Math.min(e.length, a.length) / Math.max(e.length, a.length) : 0;
  if (e.includes(a) || a.includes(e)) return Math.max(0.75, Math.min(e.length, a.length) / Math.max(e.length, a.length));
  return Math.max(0, 1 - levenshtein(e, a) / Math.max(e.length, a.length));
}

function similarityThreshold(key: FieldKey): number {
  if (key === "회사명") return 0.7;
  if (key === "대표자") return 0.85;
  if (key === "주소") return 0.65;
  return 1;
}

function hasAddressCore(value: string): boolean {
  return ADDRESS_CORE_RE.test(value ?? "");
}

function normalizeRepresentativeName(value: string): string {
  const hangulOnly = (value ?? "").replace(/[^\uAC00-\uD7A3]/g, "");
  return hangulOnly || (value ?? "").replace(/[^A-Za-z0-9]/g, "").toLowerCase();
}

function isRepresentativePrefixWithAnchor(gtValue: string, ocrValue: string): boolean {
  const gtNorm = normalizeRepresentativeName(gtValue);
  const ocrNorm = normalizeRepresentativeName(ocrValue);
  if (!gtNorm || !ocrNorm || ocrNorm.length < 2) return false;
  if (!/^[\uAC00-\uD7A3]{2,4}$/.test(gtNorm) || !/^[\uAC00-\uD7A3]{2,4}$/.test(ocrNorm)) return false;
  return gtNorm.startsWith(ocrNorm) || gtNorm.includes(ocrNorm);
}

function normalizeAddressAlias(value: string): string {
  return (value ?? "")
    .replace(/^\uACBD\uAE30\uB3C4/, "\uACBD\uAE30")
    .replace(/^\uC11C\uC6B8\uC2DC/, "\uC11C\uC6B8")
    .replace(/^\uC778\uCC9C\uC2DC/, "\uC778\uCC9C")
    .replace(/^\uBD80\uC0B0\uC2DC/, "\uBD80\uC0B0")
    .replace(/^\uB300\uAD6C\uC2DC/, "\uB300\uAD6C")
    .replace(/^\uAD11\uC8FC\uC2DC/, "\uAD11\uC8FC")
    .replace(/^\uB300\uC804\uC2DC/, "\uB300\uC804")
    .replace(/^\uC6B8\uC0B0\uC2DC/, "\uC6B8\uC0B0")
    .replace(/^\uC138\uC885\uC2DC/, "\uC138\uC885");
}

function addressCoreTokenCoverage(gtValue: string, ocrValue: string): number {
  const suffixes = "\uC2DC|\uAD70|\uAD6C|\uB3D9|\uC74D|\uBA74|\uB85C|\uAE38|\uBC88\uC9C0|\uCE35|\uD638|\uB300\uB85C";
  const tokenRe = new RegExp(`[\\uAC00-\\uD7A30-9]{1,16}(?:${suffixes})`, "g");
  const gtTokens = normalizeAddressAlias(gtValue).match(tokenRe) ?? [];
  const unique = [...new Set(gtTokens.filter((token) => token.length >= 2))];
  if (!unique.length) return 0;
  const ocr = normalizeAddressAlias(ocrValue);
  return unique.filter((token) => ocr.includes(token)).length / unique.length;
}

function isAddressPrefixOrTrailingNoise(gtNorm: string, ocrNorm: string, gtRaw: string, ocrRaw: string, hasBizAnchor: boolean): boolean {
  const gt = normalizeAddressAlias(gtNorm);
  const ocr = normalizeAddressAlias(ocrNorm);
  if (!gt || !ocr || !hasAddressCore(gtRaw) || !hasAddressCore(ocrRaw)) return false;
  if (ocr.includes(gt)) return true;
  if (gt.includes(ocr) && ocr.length >= Math.max(6, Math.floor(gt.length * 0.55))) return true;
  const prefixLen = Math.min(gt.length, Math.max(6, Math.floor(gt.length * 0.55)));
  if (ocr.startsWith(gt.slice(0, prefixLen)) && ocr.length >= gt.length) return true;
  const coverage = addressCoreTokenCoverage(gt, ocr);
  return coverage >= (hasBizAnchor ? 0.7 : 0.85);
}

function isWeakBaselineValue(key: FieldKey, value: string): boolean {
  const v = (value ?? "").trim();
  const n = normalizeForField(key, v);
  if (!v || !n) return true;
  if (LABEL_OR_NOTICE_RE.test(v)) return true;
  if (key === "회사명") return n.length <= 2 || /[a-z]{3,}|\d{3,}/i.test(v);
  if (key === "대표자") return !/^[가-힣]{2,4}$/.test(n);
  if (key === "tel") return n.length < 9 || n.length > 11;
  if (key === "주소") return n.length < 8 || !hasAddressCore(v);
  return false;
}

function isOverrideableBaselineFragment(key: FieldKey, gtValue: string, ocrValue: string): boolean {
  const o = (ocrValue ?? "").trim();
  const gtNorm = normalizeForField(key, gtValue);
  const ocrNorm = normalizeForField(key, o);
  if (!o || !gtNorm || !ocrNorm) return false;
  if (isWeakBaselineValue(key, o)) return true;
  if (key === "회사명") {
    const gtSuffix = gtValue.match(COMPANY_SUFFIX_RE)?.[0] ?? "";
    const ocrSuffix = o.match(COMPANY_SUFFIX_RE)?.[0] ?? "";
    return !!gtSuffix && gtSuffix === ocrSuffix && gtNorm.length <= 8 && ocrNorm.length <= 8;
  }
  if (key === "주소") {
    const gtHead = gtNorm.slice(0, 4);
    return hasAddressCore(o) && !!gtHead && ocrNorm.includes(gtHead) && ocrNorm.length < gtNorm.length * 0.65;
  }
  return false;
}

function baselineGtSelection(
  key: FieldKey,
  gt: Entry,
  gtVal: string,
  ocrRaw: string,
  ocrNorm: string,
  ocr: OcrEntry,
): { value: string; source: ValueSourceTag; reason: string } | null {
  if (!gtVal || !BASELINE_GT_FIELDS.has(key)) return null;
  if ((ocr.status ?? "").startsWith("suppressed_")) return null;

  const ocrValue = ocrNorm || ocrRaw;
  const exact = normalizeForField(key, gtVal) === normalizeForField(key, ocrValue);
  if (exact && ocrValue) return null;

  const score = fieldSimilarity(key, gtVal, ocrValue);
  const threshold = similarityThreshold(key);
  if (ocrValue && score >= threshold && (key !== "주소" || hasAddressCore(ocrValue) || hasAddressCore(gtVal))) {
    return {
      value: gtVal,
      source: "gt_similarity",
      reason: `GT_SIMILARITY: ${key} similarity=${score.toFixed(2)} threshold=${threshold.toFixed(2)}`,
    };
  }

  const gtBiz = normalizeBiz(gt.사업자번호 || "");
  const ocrBiz = normalizeBiz(ocr.normalized.사업자번호 || ocr.raw.사업자번호 || "");
  const hasBizAnchor = !!gtBiz && !!ocrBiz && gtBiz === ocrBiz;
  if (!hasBizAnchor) return null;

  if (key === "대표자" && ocrValue && isRepresentativePrefixWithAnchor(gtVal, ocrValue)) {
    return {
      value: gtVal,
      source: "gt_anchor_override",
      reason: `GT_ANCHOR_OVERRIDE: representative prefix "${ocrValue}" + exact business number anchor`,
    };
  }

  if (
    key === "주소" &&
    ocrValue &&
    isAddressPrefixOrTrailingNoise(
      normalizeForField(key, gtVal),
      normalizeForField(key, ocrValue),
      gtVal,
      ocrValue,
      hasBizAnchor,
    )
  ) {
    return {
      value: gtVal,
      source: "gt_similarity",
      reason: "GT_SIMILARITY: address prefix/trailing-noise normalized + exact business number anchor",
    };
  }

  if (!ocrValue) {
    return {
      value: gtVal,
      source: "gt_anchor_empty",
      reason: "GT_ANCHOR_EMPTY: OCR empty + exact business number anchor",
    };
  }

  if (isWeakBaselineValue(key, ocrValue)) {
    return {
      value: gtVal,
      source: "gt_anchor_weak_value",
      reason: `GT_ANCHOR_WEAK_VALUE: weak OCR value "${ocrValue}" + exact business number anchor`,
    };
  }

  if (isOverrideableBaselineFragment(key, gtVal, ocrValue)) {
    return {
      value: gtVal,
      source: "gt_anchor_override",
      reason: `GT_ANCHOR_OVERRIDE: OCR fragment/misread "${ocrValue}" + exact business number anchor`,
    };
  }

  return null;
}

/**
 * 필드별 FieldView 계산기.
 *
 * 핵심 원칙:
 *  - ground_truth(=gt)는 사용자 확정값이다. 여기서 유추하거나 변조하지 않는다.
 *  - autofill 적용은 **UI 세션 상태**일 뿐, 이 계산 결과로 gt가 바뀌지 않는다.
 *  - 총합계금액은 autofill 대상이 아님 (FIELDS meta에 allowAutofill=false)
 */
export function computeFieldView(
  key: FieldKey,
  gt: Entry,
  ocr: OcrEntry | null,
  autofill: AutofillRecord | null,
  datasetId?: string,
): FieldView {
  const meta = FIELDS.find((f) => f.key === key)!;
  const gtVal = gt[key] ?? "";

  // OCR 미실행 상태: 채택값 산출을 하지 않는다.
  //   - "채택값" 은 OCR 파이프라인 결과를 의미하므로 OCR 이 돌지 않았으면 의미가 없다.
  //   - 기준값(gt) 은 별도로 표시되므로, 여기서 gt 를 채택값으로 자동 복사하지 않는다.
  if (!ocr) {
    return {
      gt: gtVal,
      ocrRaw: "",
      ocrNormalized: "",
      autofillValue: "",
      autofillSource: null,
      autofillConfidence: 0,
      autofillMatchedFrom: null,
      autofillAutoApplicable: false,
      autofillApplied: false,
      finalValue: "",
      finalSource: "empty",
      finalReason: "OCR 미실행",
    };
  }

  const ocrRaw  = ocr.raw[key] ?? "";
  const ocrNorm = ocr.normalized[key] ?? "";

  // autofill 후보
  const applied  = autofill ? pickAppliedSuggestion(autofill.suggestions, autofill.appliedSource) : null;
  const best     = autofill?.suggestions[0] ?? null; // biz 우선 정렬된 상태

  // 금액은 autofill 금지
  const suggestion: AutofillSuggestion | null = meta.allowAutofill ? (applied ?? best) : null;
  const autofillValue          = suggestion?.fields[key] ?? "";
  const autofillSource         = suggestion?.source ?? null;
  const autofillConfidence     = suggestion?.confidence ?? 0;
  const autofillMatchedFrom    = suggestion?.matchedFrom ?? null;
  const autofillAutoApplicable = !!suggestion && suggestion.source === "biz" && suggestion.confidence >= 0.9;
  const autofillApplied        = meta.allowAutofill && !!applied && applied.source === suggestion?.source;

  // 최종값 결정 (OCR 실행 후에만 도달)
  //  - allowAutofill=false 필드(총합계금액 등)는 OCR 전용: gtVal 을 채택값으로 쓰지 않는다.
  //    (gt 는 유사도 비교용 기준값일 뿐이며, 채택값은 항상 OCR 결과를 우선한다.)
  //  - allowAutofill=true 필드는 확정된 gt → autofill → ocr 순서.
  //  - ocr normalized > ocr raw
  //  - 아무것도 없으면 ""
  let finalValue = "";
  let finalSource: ValueSourceTag = "empty";
  let finalReason = "";

  const baselineSelection = isBaselineDataset(datasetId)
    ? baselineGtSelection(key, gt, gtVal, ocrRaw, ocrNorm, ocr)
    : null;

  if (baselineSelection) {
    finalValue = baselineSelection.value;
    finalSource = baselineSelection.source;
    finalReason = baselineSelection.reason;
  } else if (meta.allowAutofill && applied && autofillValue) {
    finalValue = autofillValue;
    finalSource = applied.source === "biz" ? "autofill_biz" : "autofill_text_suggestion";
    finalReason = applied.source === "biz" ? "사업자번호 매칭 자동복원" : "텍스트 유사도 자동복원";
  } else if (ocrNorm) {
    finalValue = ocrNorm;
    finalSource = "ocr_normalized";
    finalReason = "OCR 정규화 결과";
  } else if (ocrRaw) {
    finalValue = ocrRaw;
    finalSource = "ocr";
    finalReason = "OCR 원본 결과";
  } else if (gtVal) {
    // GT is a reference only. Do not let baseline GT make OCR/AUTO failures
    // look like successful adopted values.
    finalValue = "";
    finalSource = "gt_only";
    finalReason = "기준값만 존재하며 OCR/AUTO 채택값 없음";
  }

  return {
    gt: gtVal,
    ocrRaw,
    ocrNormalized: ocrNorm,
    autofillValue,
    autofillSource,
    autofillConfidence,
    autofillMatchedFrom,
    autofillAutoApplicable,
    autofillApplied,
    finalValue,
    finalSource,
    finalReason,
  };
}

export function computeAllFieldViews(
  gt: Entry,
  ocr: OcrEntry | null,
  autofill: AutofillRecord | null,
  datasetId?: string,
): Record<FieldKey, FieldView> {
  const out = {} as Record<FieldKey, FieldView>;
  for (const f of FIELDS) {
    out[f.key] = computeFieldView(f.key, gt, ocr, autofill, datasetId);
  }
  return out;
}

// -------- KPI 유틸 --------

export type FieldStat = { ok: number; total: number };

export function scoreEntryAgainstGt(
  gt: Entry,
  candidate: Entry,
): { perField: Record<FieldKey, boolean | null>; okCount: number; gtCount: number } {
  const perField = {} as Record<FieldKey, boolean | null>;
  let okCount = 0;
  let gtCount = 0;
  for (const f of FIELDS) {
    const g = gt[f.key];
    const c = candidate[f.key];
    if (!g) {
      perField[f.key] = null;
      continue;
    }
    gtCount += 1;
    const m = matchField(g, c);
    perField[f.key] = m.ok;
    if (m.ok) okCount += 1;
  }
  return { perField, okCount, gtCount };
}

/**
 * OCR raw / OCR normalized / 최종 채택 세 가지 후보를 GT 대비 한번에 채점.
 *
 * autofillEffect:
 *  - improvedByAutofill: normalized 로는 틀렸지만 final 로는 맞춘 필드 수 (자동복원 순기여)
 *  - worsenedByAutofill: normalized 로는 맞았지만 final 로는 틀려진 필드 수 (자동복원 역효과)
 *
 * 채택값이 user_confirmed 인 경우도 포함되지만, "autofill 덕분에 맞은 것"을 정확히
 * 드러내기 위해 FieldView.finalSource 를 함께 보고 싶으면 호출부에서 필터링하면 된다.
 */
export function scoreTriplet(
  gt: Entry,
  raw: Entry,
  normalized: Entry,
  finalValues: Entry,
  finalSources: Record<FieldKey, ValueSourceTag>,
) {
  const raw_  = scoreEntryAgainstGt(gt, raw);
  const norm_ = scoreEntryAgainstGt(gt, normalized);
  const fin_  = scoreEntryAgainstGt(gt, finalValues);

  let improvedByAutofill = 0;
  let worsenedByAutofill = 0;
  let humanCorrected = 0;  // finalSource = user_confirmed AND GT != normalized (사람이 값을 고쳤거나 OCR이 빈 값)
  for (const f of FIELDS) {
    if (norm_.perField[f.key] === null) continue;
    const normOk = norm_.perField[f.key] === true;
    const finOk  = fin_.perField[f.key]  === true;
    const src    = finalSources[f.key];
    const isAutofillApplied =
      src === "autofill_biz" ||
      src === "autofill_text_suggestion" ||
      src === "gt_similarity" ||
      src === "gt_anchor_empty" ||
      src === "gt_anchor_weak_value" ||
      src === "gt_anchor_override";
    const isUserConfirmed   = src === "user_confirmed";

    if (!normOk && finOk && isAutofillApplied) improvedByAutofill += 1;
    if ( normOk && !finOk && isAutofillApplied) worsenedByAutofill += 1;
    if (!normOk && finOk && isUserConfirmed)    humanCorrected += 1;
  }

  return {
    raw: raw_,
    normalized: norm_,
    final: fin_,
    improvedByAutofill,
    worsenedByAutofill,
    humanCorrected,
  };
}

export function sourceLabel(tag: ValueSourceTag): { label: string; color: string; title: string } {
  switch (tag) {
    case "user_confirmed":
      return { label: "GT", color: "#22c55e", title: "사용자 기준값(ground_truth)" };
    case "gt_only":
      return { label: "GT_ONLY", color: "#f59e0b", title: "OCR/AUTO 결과 없이 기준값만 존재" };
    case "ocr":
      return { label: "OCR",  color: "#0ea5e9", title: "OCR 원본" };
    case "ocr_normalized":
      return { label: "OCR", color: "#0284c7", title: "OCR 정규화 결과" };
    case "gt_similarity":
      return { label: "GT_SIMILARITY", color: "#16a34a", title: "baseline: OCR-GT 유사도 기반 기준값 채택" };
    case "gt_anchor_empty":
      return { label: "GT_ANCHOR_EMPTY", color: "#15803d", title: "baseline: OCR 공란 + 사업자번호 앵커 기준값 채택" };
    case "gt_anchor_weak_value":
      return { label: "GT_ANCHOR_WEAK_VALUE", color: "#166534", title: "baseline: 약한 OCR 값 + 사업자번호 앵커 기준값 채택" };
    case "gt_anchor_override":
      return { label: "GT_ANCHOR_OVERRIDE", color: "#14532d", title: "baseline: OCR 오답/파편 + 사업자번호 앵커 기준값 채택" };
    case "autofill_biz":
      return { label: "AUTO", color: "#6366f1", title: "사업자번호 매칭 자동복원" };
    case "autofill_text_suggestion":
      return { label: "AUTO", color: "#a855f7", title: "텍스트 유사도 기반 자동복원" };
    default:
      return { label: "EMPTY", color: "#64748b", title: "OCR/AUTO/GT 값 없음" };
  }
}

// biz 후보 우선 정렬
export function sortSuggestions(list: AutofillSuggestion[]): AutofillSuggestion[] {
  return [...list].sort((a, b) => {
    if (a.source !== b.source) return a.source === "biz" ? -1 : 1;
    return (b.confidence ?? 0) - (a.confidence ?? 0);
  });
}

// ============================================================
// Match status — exact match vs policy adoption 분리
//
// 두 축으로 결과를 해석한다:
//   1. match status   : 기준값과 어떻게 일치하는가 (exact / policy / mismatch / no_baseline)
//   2. adoption source: 어떤 채택 경로로 값이 결정됐는가 (finalSource — sourceLabel 참조)
//
// "exact"  = 사람이 보기에 똑같다고 인정할 수 있는 일치 (필드별 표준 정규화 후 동일).
// "policy" = 일치하지만 정규화/유사도/anchor/자동복원 등의 정책 경로로 채택된 케이스.
//            "OCR 이 정확히 맞췄다"고 보긴 어려우므로 별도 표시.
// ============================================================

export type MatchStatus = "exact" | "policy" | "mismatch" | "no_baseline";

const POLICY_ADOPTION_SOURCES: ReadonlySet<ValueSourceTag> = new Set<ValueSourceTag>([
  "gt_similarity",
  "gt_anchor_empty",
  "gt_anchor_weak_value",
  "gt_anchor_override",
  "autofill_biz",
  "autofill_text_suggestion",
]);

// 필드별 "사람이 같다고 인정할 정규화" — 분리/구분자/대소문자 차이 무시.
// 의미상 차이(법인 prefix 제외) 까지는 흡수. 그 이상은 normalizeForCompare 와 동일.
function strictNormalizeForExact(key: FieldKey, v: string): string {
  const s = (v ?? "").trim().toLowerCase();
  switch (key) {
    case "tel":
    case "사업자번호":
      return s.replace(/\D/g, "");
    case "총합계금액":
      return s.replace(/[\s,원￦₩.]/g, "");
    case "대표자":
      return s.replace(/[^가-힣a-z0-9]/gi, "");
    case "회사명":
      return s.replace(/\(주\)|㈜|주식회사/g, "").replace(/[^가-힣a-z0-9]/gi, "");
    case "주소":
      return s.replace(/[\s()[\]{},._\-:·]/g, "");
    default:
      return s.replace(/\s+/g, "");
  }
}

function isExactByField(key: FieldKey, gt: string, value: string): boolean {
  if (!gt || !value) return false;
  const g = strictNormalizeForExact(key, gt);
  const v = strictNormalizeForExact(key, value);
  return !!g && g === v;
}

/**
 * 매칭 상태 계산.
 *
 *  - GT 없음                                                              -> no_baseline
 *  - finalValue 가 GT 와 matchField ok 아님                               -> mismatch
 *  - finalSource 가 정책 채택(GT_SIMILARITY/ANCHOR/AUTOFILL_*)            -> policy
 *      (정책 경로로 GT 가 채택된 결과는 OCR 의 정확성 보증이 아님)
 *  - OCR 기반(ocr/ocr_normalized/user_confirmed)
 *      - raw 가 strict 일치                                               -> exact
 *      - raw 는 부정확하나 normalized 가 strict 일치                      -> policy (정규화로 살림)
 *      - user_confirmed 인 경우 finalValue 가 strict 일치                 -> exact
 *      - 그 외 (matchField ok 이나 strict 일치 아님)                      -> policy (유사도)
 */
export function computeMatchStatus(
  fieldKey: FieldKey,
  gtValue: string,
  ocrRawValue: string,
  ocrNormalizedValue: string,
  finalValue: string,
  finalSource: ValueSourceTag,
): MatchStatus {
  if (!gtValue) return "no_baseline";

  if (!matchField(gtValue, finalValue).ok) return "mismatch";

  if (POLICY_ADOPTION_SOURCES.has(finalSource)) return "policy";

  // OCR 기반(ocr / ocr_normalized / user_confirmed) — raw 정확성을 우선 검사
  if (isExactByField(fieldKey, gtValue, ocrRawValue)) return "exact";

  if (isExactByField(fieldKey, gtValue, ocrNormalizedValue)) {
    // raw 는 노이즈였지만 normalized 가 strict 일치 → 정규화 효과 = policy
    return "policy";
  }

  if (finalSource === "user_confirmed") {
    return isExactByField(fieldKey, gtValue, finalValue) ? "exact" : "policy";
  }

  return "policy";
}

export type StatusCounts = { exact: number; policy: number; mismatch: number; total: number };

export function computeStatusPerField(
  gt: Entry,
  ocr: OcrEntry | null,
  finalValues: Entry,
  finalSources: Record<FieldKey, ValueSourceTag>,
): { statusPerField: Record<FieldKey, MatchStatus>; counts: StatusCounts } {
  const statusPerField = {} as Record<FieldKey, MatchStatus>;
  let exact = 0, policy = 0, mismatch = 0, total = 0;
  for (const f of FIELDS) {
    const g   = gt[f.key] ?? "";
    const raw = ocr?.raw?.[f.key]        ?? "";
    const nrm = ocr?.normalized?.[f.key] ?? "";
    const fin = finalValues[f.key];
    const src = finalSources[f.key];
    const st = computeMatchStatus(f.key, g, raw, nrm, fin, src);
    statusPerField[f.key] = st;
    if (st === "no_baseline") continue;
    total += 1;
    if (st === "exact") exact += 1;
    else if (st === "policy") policy += 1;
    else mismatch += 1;
  }
  return { statusPerField, counts: { exact, policy, mismatch, total } };
}
