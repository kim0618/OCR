import { normalizeBizNumber } from "@/common/utils/bizNumber";
import { readHistoryRuns, type HistoryOutputField } from "@/common/storage/historyStore";
import { readRestoreProfiles, isMeaninglessValue } from "@/common/storage/restoreProfileStore";

export type AutofillSource = "biz";
export type OutputValueSource = "ocr" | "biz" | "gt" | "text";
export type AutofillAction = "filled" | "corrected" | "confirmed" | "none";

export type AutofillSuggestion = {
  field: string;
  value: string;
  source: AutofillSource;
  confidence: number;
  reason?: string;
  label?: string;
  sourceType?: "history" | "groundTruth" | "cache" | "restoreProfile";
  createdAt?: string;
  updatedAt?: string;
  templateName?: string | null;
  fileName?: string;
  hitCount?: number;
};

export type AutofillCandidateRecord = {
  businessNumber: string;
  fields: Record<string, string>;
  source?: string;
  sourceType?: "history" | "groundTruth" | "cache" | "restoreProfile";
  fileName?: string;
  templateName?: string | null;
  createdAt?: string;
  updatedAt?: string;
  hitCount?: number;
};

export type AutofillRunStatus =
  | "not_run"
  | "no_business_number"
  | "no_candidates"
  | "confirmed"
  | "corrected"
  | "applied";

export type AutofillRunSummary = {
  status: AutofillRunStatus;
  businessNumber?: string;
  candidateCount: number;
  confirmedCount: number;
  correctedCount: number;
  filledCount: number;
  skippedCount?: number;
  message?: string;
};

export type AutofillFieldMetadata = {
  source?: OutputValueSource;
  applied?: string;
  autofillAction?: AutofillAction;
  suggestions?: AutofillSuggestion[];
};

export type AutofillOutputFieldLike = AutofillFieldMetadata & {
  name?: string;
  en?: string;
  ko?: string;
  label?: string;
  value?: string;
  original?: string;
};

export const AUTOFILLABLE_FIELDS = [
  "회사명",
  "사업자번호",
  "대표자",
  "tel",
  "전화번호",
  "주소",
] as const;

const GROUND_TRUTH_STORAGE_KEY = "mysuit_ocr_groundtruth";

const FIELD_ALIASES: Record<string, string> = {
  "회사명": "회사명",
  "상호": "회사명",
  "상호명": "회사명",
  "가맹점명": "회사명",
  companyname: "회사명",
  merchantname: "회사명",
  storename: "회사명",
  vendorname: "회사명",
  suppliername: "회사명",
  "사업자번호": "사업자번호",
  "사업자등록번호": "사업자번호",
  "등록번호": "사업자번호",
  bizno: "사업자번호",
  businessnumber: "사업자번호",
  businessregistrationnumber: "사업자번호",
  "대표자": "대표자",
  "대표자명": "대표자",
  representative: "대표자",
  representativename: "대표자",
  ownername: "대표자",
  ceoname: "대표자",
  tel: "tel",
  telephone: "tel",
  phone: "tel",
  phonenumber: "tel",
  "전화": "tel",
  "전화번호": "tel",
  "주소": "주소",
  address: "주소",
  storeaddress: "주소",
  companyaddress: "주소",
  businessaddress: "주소",
  "총합계금액": "총합계금액",
  "합계금액": "총합계금액",
  "총액": "총합계금액",
  totalamount: "총합계금액",
  amount: "총합계금액",
  "판매금액": "판매금액",
  saleamount: "판매금액",
  "부가세": "부가세",
  taxamount: "부가세",
  "공급가액": "공급가액",
  supplyamount: "공급가액",
  "승인번호": "승인번호",
  approvalnumber: "승인번호",
  "카드번호": "카드번호",
  cardnumber: "카드번호",
  "거래일시": "거래일시",
  transactiondate: "거래일시",
  transactiondatetime: "거래일시",
  "전표번호": "전표번호",
  slipnumber: "전표번호",
  "가맹번호": "가맹번호",
  merchantnumber: "가맹번호",
};

function compactKey(field: string): string {
  return (field ?? "").replace(/\s+/g, "").replace(/[_\-.]/g, "").toLowerCase();
}

export function normalizeAutofillFieldKey(field: string): string {
  const raw = (field ?? "").trim();
  if (!raw) return "";
  return FIELD_ALIASES[raw] ?? FIELD_ALIASES[compactKey(raw)] ?? raw;
}

export function isAutofillableField(field: string): boolean {
  const key = normalizeAutofillFieldKey(field);
  return key !== "총합계금액" && (AUTOFILLABLE_FIELDS as readonly string[]).includes(key);
}

export function isEmptyOcrValue(value: unknown): boolean {
  return value === null || value === undefined || String(value).trim() === "";
}

export function canAutoApplySuggestion(suggestion: AutofillSuggestion): boolean {
  return (
    suggestion.source === "biz" &&
    suggestion.confidence >= 0.9 &&
    !isEmptyOcrValue(suggestion.value) &&
    isAutofillableField(suggestion.field)
  );
}

function clampConfidence(value: number): number {
  return Math.max(0, Math.min(1, value));
}

function recencyScore(value?: string): number {
  if (!value) return 0;
  const ts = Date.parse(value.replace(" ", "T"));
  if (!Number.isFinite(ts)) return 0;
  const ageDays = Math.max(0, (Date.now() - ts) / 86_400_000);
  if (ageDays <= 1) return 0.012;
  if (ageDays <= 7) return 0.009;
  if (ageDays <= 30) return 0.006;
  if (ageDays <= 90) return 0.003;
  return 0;
}

function valueQualityScore(value: string): number {
  const text = String(value ?? "").trim();
  if (!text) return -0.05;
  if (text.length <= 1) return -0.03;
  if (/^[\W_]+$/.test(text)) return -0.03;
  if (/^(없음|미상|null|undefined|-)+$/i.test(text)) return -0.04;
  if (text.length >= 3) return 0.004;
  return 0;
}

function suggestionPriority(suggestion: AutofillSuggestion): number {
  let score = suggestion.confidence;
  if (suggestion.sourceType === "restoreProfile") score += 0.025;
  if (suggestion.sourceType === "history") score += 0.02;
  if (suggestion.sourceType === "groundTruth") score += 0.015;
  if ((suggestion.hitCount ?? 0) >= 2) score += Math.min(0.012, (suggestion.hitCount ?? 0) * 0.003);
  score += recencyScore(suggestion.updatedAt ?? suggestion.createdAt);
  score += valueQualityScore(suggestion.value);
  return clampConfidence(score);
}

export function sortAutofillSuggestions(suggestions: AutofillSuggestion[]): AutofillSuggestion[] {
  return [...suggestions].sort((a, b) => {
    if (a.field !== b.field) return a.field.localeCompare(b.field);
    const priorityDiff = suggestionPriority(b) - suggestionPriority(a);
    if (priorityDiff !== 0) return priorityDiff;
    const hitDiff = (b.hitCount ?? 0) - (a.hitCount ?? 0);
    if (hitDiff !== 0) return hitDiff;
    return String(b.updatedAt ?? b.createdAt ?? "").localeCompare(String(a.updatedAt ?? a.createdAt ?? ""));
  });
}

function normalizeBusinessNumber(value: string): string {
  return normalizeBizNumber(value) ?? value.replace(/\D/g, "");
}

function normalizeComparableValue(field: string, value: unknown): string {
  const text = String(value ?? "").trim();
  const normalizedField = normalizeAutofillFieldKey(field);
  if (normalizedField === "사업자번호") return normalizeBusinessNumber(text);
  if (normalizedField === "tel") return text.replace(/\D/g, "");
  return text.replace(/\s+/g, "");
}

function valuesMatch(field: string, a: unknown, b: unknown): boolean {
  const left = normalizeComparableValue(field, a);
  const right = normalizeComparableValue(field, b);
  return !!left && !!right && left === right;
}

function putField(map: Record<string, string>, key: string, value: unknown) {
  const normalizedKey = normalizeAutofillFieldKey(key);
  const text = String(value ?? "").trim();
  if (!normalizedKey || !text) return;
  map[normalizedKey] = text;
}

function valueOfObjectField(field: unknown, key: string): unknown {
  if (!field || typeof field !== "object") return undefined;
  return (field as Record<string, unknown>)[key];
}

function getHistoryFieldValue(field: unknown): string {
  const modified = String(valueOfObjectField(field, "modified") ?? "").trim();
  if (modified) return modified;
  return String(valueOfObjectField(field, "original") ?? "").trim();
}

function isUserEditedHistoryField(field: unknown): boolean {
  const source = String(valueOfObjectField(field, "source") ?? "").trim();
  if (source === "text") return true;
  if (source === "biz" || source === "gt") return false;
  const original = String(valueOfObjectField(field, "original") ?? "").trim();
  const modified = String(valueOfObjectField(field, "modified") ?? "").trim();
  return !!modified && modified !== original;
}

function getHistoryFieldKey(field: unknown): string {
  const candidates = ["ko", "en", "name", "label", "field"];
  for (const key of candidates) {
    const normalized = normalizeAutofillFieldKey(String(valueOfObjectField(field, key) ?? ""));
    if (["회사명", "사업자번호", "대표자", "tel", "주소", "총합계금액"].includes(normalized)) {
      return normalized;
    }
  }
  return "";
}

function readGroundTruthCandidateRecords(): AutofillCandidateRecord[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(GROUND_TRUTH_STORAGE_KEY);
    if (!raw) return [];
    const store = JSON.parse(raw) as Record<string, Record<string, string>>;
    if (!store || typeof store !== "object") return [];
    return Object.entries(store).flatMap(([composite, values]) => {
      if (!values || typeof values !== "object") return [];
      const fields: Record<string, string> = {};
      for (const [key, value] of Object.entries(values)) putField(fields, key, value);
      const businessNumber = normalizeBusinessNumber(fields["사업자번호"] ?? "");
      if (!businessNumber) return [];
      const [templateName, fileName] = composite.split("::");
      return [{
        businessNumber,
        fields,
        source: "groundTruthStore",
        sourceType: "groundTruth",
        templateName: templateName || null,
        fileName: fileName || undefined,
      }];
    });
  } catch {
    return [];
  }
}

function readHistoryCandidateRecords(): AutofillCandidateRecord[] {
  const candidateFields = ["companyName", "businessNumber", "representative", "tel", "address"].map(normalizeAutofillFieldKey);
  const businessNumberKey = normalizeAutofillFieldKey("businessNumber");

  return readHistoryRuns().flatMap((run) => {
    const fields: Record<string, string> = {};
    let businessNumber = "";
    for (const row of run.output_fields ?? []) {
      const key = getHistoryFieldKey(row);
      const value = getHistoryFieldValue(row);
      if (!key || !value) continue;
      if (key === businessNumberKey) {
        businessNumber = normalizeBusinessNumber(value);
      }
      if (!isUserEditedHistoryField(row)) continue;
      if (candidateFields.includes(key)) {
        fields[key] = value;
      }
    }
    if (!businessNumber || Object.keys(fields).length === 0) return [];
    return [{
      businessNumber,
      fields,
      source: "history",
      sourceType: "history",
      templateName: run.template_name,
      fileName: run.file_name,
      createdAt: run.created_at,
      updatedAt: run.created_at,
    }];
  });
}

function readRestoreProfileCandidates(): AutofillCandidateRecord[] {
  try {
    return readRestoreProfiles().flatMap((profile) => {
      const bizNo = normalizeBusinessNumber(profile.businessNo ?? "");
      if (!bizNo) return [];
      const fields: Record<string, string> = {};
      for (const [rawKey, val] of Object.entries(profile.fields ?? {})) {
        if (isEmptyOcrValue(val) || isMeaninglessValue(val)) continue;
        const normalizedKey = normalizeAutofillFieldKey(rawKey);
        if (!normalizedKey || !isAutofillableField(normalizedKey)) continue;
        fields[normalizedKey] = val;
      }
      if (Object.keys(fields).length === 0) return [];
      const candidate: AutofillCandidateRecord = {
        businessNumber: bizNo,
        fields,
        source: "restoreProfile",
        sourceType: "restoreProfile",
        fileName: profile.sourceFileName,
        createdAt: profile.createdAt,
        updatedAt: profile.updatedAt,
      };
      return [candidate];
    });
  } catch {
    return [];
  }
}

export function collectInternalAutofillCandidates(businessNumber?: string): AutofillCandidateRecord[] {
  const restoreProfiles = readRestoreProfileCandidates();
  if (businessNumber) {
    const normalizedBizNo = normalizeBusinessNumber(businessNumber);
    const matchingRestore = restoreProfiles.filter(
      (c) => normalizeBusinessNumber(c.businessNumber) === normalizedBizNo,
    );
    if (matchingRestore.length > 0) {
      // 1순위: restore profiles에 같은 사업자번호 후보 있음
      return matchingRestore;
    }
    // 2순위: history fallback
    return readHistoryCandidateRecords();
  }
  // businessNumber 없이 호출 시 전체 반환 (restore 우선 + history fallback)
  return restoreProfiles.length > 0
    ? restoreProfiles
    : readHistoryCandidateRecords();
}

function confidenceForCandidate(candidate: AutofillCandidateRecord, templateName?: string | null): number {
  let confidence = !candidate.source ? 0.9 : 0.95;
  if (candidate.sourceType === "restoreProfile") confidence += 0.025;
  if (candidate.sourceType === "history") confidence += 0.02;
  if (candidate.sourceType === "groundTruth") confidence += 0.015;
  if (candidate.templateName && templateName && candidate.templateName === templateName) confidence += 0.03;
  confidence += recencyScore(candidate.updatedAt ?? candidate.createdAt);
  if ((candidate.hitCount ?? 0) >= 2) confidence += 0.006;
  return clampConfidence(confidence);
}

export function buildAutofillSuggestionsFromCandidates(args: {
  businessNumber: string;
  candidates: AutofillCandidateRecord[];
  templateName?: string | null;
  fileName?: string;
}): AutofillSuggestion[] {
  const businessNumber = normalizeBusinessNumber(args.businessNumber);
  if (!businessNumber) return [];

  const byKey = new Map<string, AutofillSuggestion>();
  for (const candidate of args.candidates) {
    if (normalizeBusinessNumber(candidate.businessNumber) !== businessNumber) continue;
    const confidence = confidenceForCandidate(candidate, args.templateName);
    for (const [field, value] of Object.entries(candidate.fields)) {
      const normalizedField = normalizeAutofillFieldKey(field);
      if (!isAutofillableField(normalizedField) || isEmptyOcrValue(value)) continue;
      const suggestion: AutofillSuggestion = {
        field: normalizedField,
        value,
        source: "biz",
        confidence: clampConfidence(confidence + valueQualityScore(value)),
        label: "매칭복원",
        reason: `사업자번호 ${businessNumber} 내부 매칭${candidate.fileName ? ` (${candidate.fileName})` : ""}`,
        sourceType: candidate.sourceType,
        createdAt: candidate.createdAt,
        updatedAt: candidate.updatedAt,
        templateName: candidate.templateName,
        fileName: candidate.fileName,
        hitCount: candidate.hitCount ?? 1,
      };
      const key = `${normalizedField}::${value}`;
      const prev = byKey.get(key);
      if (!prev) {
        byKey.set(key, suggestion);
      } else {
        const hitCount = (prev.hitCount ?? 1) + 1;
        const merged: AutofillSuggestion = {
          ...(suggestionPriority(suggestion) > suggestionPriority(prev) ? suggestion : prev),
          hitCount,
          confidence: clampConfidence(Math.max(prev.confidence, suggestion.confidence) + Math.min(0.012, hitCount * 0.003)),
        };
        byKey.set(key, merged);
      }
    }
  }
  return sortAutofillSuggestions([...byKey.values()]);
}

function fieldNameOf(field: AutofillOutputFieldLike): string {
  return normalizeAutofillFieldKey(field.ko || field.en || field.label || field.name || "");
}

export function applyAutofillToOutputFields<T extends AutofillOutputFieldLike>(args: {
  fields: T[];
  suggestions: AutofillSuggestion[];
}): T[] {
  return args.fields.map((field) => {
    const normalizedField = fieldNameOf(field);
    const fieldSuggestions = sortAutofillSuggestions(
      args.suggestions.filter((s) => normalizeAutofillFieldKey(s.field) === normalizedField),
    );
    const currentValue = field.value ?? "";
    const auto = fieldSuggestions.find(canAutoApplySuggestion);
    const canApply = isAutofillableField(normalizedField) && !!auto;
    const action: AutofillAction = !canApply
      ? "none"
      : isEmptyOcrValue(currentValue)
        ? "filled"
        : valuesMatch(normalizedField, currentValue, auto.value)
          ? "confirmed"
          : "corrected";
    const shouldUseSuggestion = action === "filled" || action === "corrected";

    return {
      ...field,
      original: field.original ?? currentValue,
      value: shouldUseSuggestion && auto ? auto.value : currentValue,
      source: shouldUseSuggestion ? "biz" : isEmptyOcrValue(currentValue) ? field.source : "ocr",
      applied: shouldUseSuggestion && auto ? auto.value : field.applied,
      autofillAction: action,
      suggestions: fieldSuggestions.length > 0 ? fieldSuggestions : field.suggestions,
    };
  });
}

export function suggestionsForHistoryField(
  row: Pick<HistoryOutputField, "en" | "ko">,
  suggestions: AutofillSuggestion[],
): AutofillSuggestion[] {
  const normalizedField = normalizeAutofillFieldKey(row.ko || row.en);
  return sortAutofillSuggestions(
    suggestions.filter((s) => normalizeAutofillFieldKey(s.field) === normalizedField),
  );
}
