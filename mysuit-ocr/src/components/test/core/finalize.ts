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

  if (meta.allowAutofill && applied && autofillValue) {
    finalValue = autofillValue;
    finalSource = applied.source === "biz" ? "autofill_biz" : "autofill_text_suggestion";
  } else if (ocrNorm) {
    finalValue = ocrNorm;
    finalSource = "ocr_normalized";
  } else if (ocrRaw) {
    finalValue = ocrRaw;
    finalSource = "ocr";
  } else if (gtVal) {
    // GT is a reference only. Do not let baseline GT make OCR/AUTO failures
    // look like successful adopted values.
    finalValue = "";
    finalSource = "gt_only";
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
  };
}

export function computeAllFieldViews(
  gt: Entry,
  ocr: OcrEntry | null,
  autofill: AutofillRecord | null,
): Record<FieldKey, FieldView> {
  const out = {} as Record<FieldKey, FieldView>;
  for (const f of FIELDS) {
    out[f.key] = computeFieldView(f.key, gt, ocr, autofill);
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
    const isAutofillApplied = src === "autofill_biz" || src === "autofill_text_suggestion";
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
