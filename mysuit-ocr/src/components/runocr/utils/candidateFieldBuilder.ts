export type CandidateFieldType =
  | "shipmentNo"
  | "orderNo"
  | "documentNo"
  | "salesType"
  | "barcodeNo"
  | "customerCode"
  | "deliveryPlace"
  | "managerName"
  | "printDate"
  | "pageInfo"
  | "phoneNo"
  | "faxNo"
  | "note"
  | "unknownIdentifier"
  | "unknownKeyValue";

export type CandidateFieldStatus = "candidate" | "duplicateOfNormalized";
export type CandidateFieldReviewStatus = "review_recommended" | "accepted" | "rejected";
export type CandidateFieldSource = "full_text_line" | "fields" | "document_fields" | "raw_ocr_fields";

export type CandidateField = {
  candidateId: string;
  candidateType: CandidateFieldType;
  labelKo: string;
  labelEn: string;
  value: string;
  sourceText: string;
  confidence: number;
  source: CandidateFieldSource;
  bboxRefs?: unknown[];
  status: CandidateFieldStatus;
  reviewStatus: CandidateFieldReviewStatus;
  normalizedKeySuggestion?: string;
};

export type UnmappedTextCandidate = {
  candidateId: string;
  text: string;
  confidence: number | null;
  reason: string;
  bboxRefs?: unknown[];
};

export type UserSelectedField = {
  key: string;
  labelKo: string;
  labelEn: string;
  value: string;
  sourceCandidateId: string;
  reviewStatus: CandidateFieldReviewStatus;
  fieldStatus: CandidateFieldStatus;
};

export type CandidateFieldBuilderInput = {
  result?: unknown;
  normalizedResult?: unknown;
  maxUnmappedTextCandidates?: number;
  maxLines?: number;
};

export type CandidateFieldBuilderOutput = {
  candidateFields: CandidateField[];
  unmappedTextCandidates: UnmappedTextCandidate[];
  userSelectedFields: UserSelectedField[];
  warnings: string[];
  builderMeta: {
    builderVersion: string;
    rawOcrPolicy: {
      fullTextIncluded: false;
      imageBase64Included: false;
    };
    noAutoPromotionToNormalizedResult: true;
  };
};

const BUILDER_VERSION = "candidate-field-builder-1g";
const FULL_TEXT_OUTPUT_FORBIDDEN_MARKER = "full_text_output_forbidden";
const IMAGE_BASE64_OUTPUT_FORBIDDEN_MARKER = "image_base64_output_forbidden";
const CANDIDATE_NOT_AUTO_PROMOTED_MARKER = "candidate_not_auto_promoted_to_normalizedResult";

const MAX_SOURCE_TEXT_LENGTH = 60;
const MAX_VALUE_LENGTH = 80;
const DEFAULT_MAX_UNMAPPED = 50;
const DEFAULT_MAX_LINES = 180;

const NORMALIZED_KEYS = new Set([
  "supplierBizNumber",
  "supplierCompany",
  "supplierAddress",
  "supplierRepresentative",
  "buyerBizNumber",
  "buyerCompany",
  "buyerAddress",
  "buyerRepresentative",
  "issueDate",
  "totalAmount",
  "supplyAmount",
  "taxAmount",
  "cumulativeAmount",
  "tableRows",
  "itemName",
  "spec",
  "productCode",
  "lotNo",
  "expiryDate",
  "quantity",
  "unitPrice",
  "amount",
]);

const TYPE_LABELS: Record<CandidateFieldType, { ko: string; en: string; labels: string[] }> = {
  shipmentNo: { ko: "출고번호", en: "shipmentNo", labels: ["출고번호", "출고 No", "출고NO", "출고 No.", "출고 번호"] },
  orderNo: { ko: "주문번호", en: "orderNo", labels: ["주문번호", "주문 No", "주문NO", "발주번호", "주문서번호"] },
  documentNo: { ko: "문서번호", en: "documentNo", labels: ["문서번호", "전표번호", "거래명세서번호", "명세서번호", "관리번호"] },
  salesType: { ko: "판매구분", en: "salesType", labels: ["판매구분", "판매 구분", "매출구분", "거래구분"] },
  barcodeNo: { ko: "바코드번호", en: "barcodeNo", labels: ["바코드", "barcode", "BARCODE", "바코드번호"] },
  customerCode: { ko: "거래처코드", en: "customerCode", labels: ["거래처코드", "거래처 코드", "고객코드", "업체코드", "거래처번호"] },
  deliveryPlace: { ko: "배송지", en: "deliveryPlace", labels: ["배송지", "납품처", "납품장소", "배송처", "도착지"] },
  managerName: { ko: "담당자", en: "managerName", labels: ["담당자", "영업사원", "담당", "관리자"] },
  printDate: { ko: "출력일자", en: "printDate", labels: ["출력일자", "출력일시", "발행일시", "인쇄일자"] },
  pageInfo: { ko: "페이지정보", en: "pageInfo", labels: ["페이지", "Page", "1페이지", "2페이지 중 1페이지", "page 1 of 2"] },
  phoneNo: { ko: "전화번호", en: "phoneNo", labels: ["전화", "전화번호", "TEL", "Tel"] },
  faxNo: { ko: "팩스번호", en: "faxNo", labels: ["팩스", "FAX", "Fax"] },
  note: { ko: "비고", en: "note", labels: ["비고", "메모", "특이사항", "참고"] },
  unknownIdentifier: { ko: "미확인 식별자", en: "unknownIdentifier", labels: [] },
  unknownKeyValue: { ko: "미확인 키값", en: "unknownKeyValue", labels: [] },
};

const LABEL_TYPES = Object.keys(TYPE_LABELS).filter(
  (key) => key !== "unknownIdentifier" && key !== "unknownKeyValue",
) as CandidateFieldType[];

function isRecord(value: unknown): value is Record<string, unknown> {
  return !!value && typeof value === "object" && !Array.isArray(value);
}

function asString(value: unknown): string {
  if (value === null || value === undefined) return "";
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  return "";
}

function compactText(value: string, maxLength = MAX_SOURCE_TEXT_LENGTH): string {
  const text = value.replace(/\s+/g, " ").trim();
  if (text.length <= maxLength) return text;
  return `${text.slice(0, Math.max(0, maxLength - 3)).trimEnd()}...`;
}

function normalizeForCompare(value: string): string {
  return value.replace(/\s+/g, "").replace(/[,:：;|()[\]{}]/g, "").toLowerCase();
}

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function compactBBoxRefs(value: unknown): unknown[] | undefined {
  if (!Array.isArray(value)) return undefined;
  const refs = value.filter((bbox) => {
    if (!Array.isArray(bbox)) return true;
    if (bbox.length !== 4) return true;
    return !bbox.every((item) => Number(item) === 0);
  });
  return refs.length > 0 ? refs : undefined;
}

function resolveResult(input: CandidateFieldBuilderInput | unknown): Record<string, unknown> {
  if (isRecord(input) && "result" in input && isRecord(input.result)) return input.result;
  return isRecord(input) ? input : {};
}

function collectNormalizedValues(result: Record<string, unknown>, input: CandidateFieldBuilderInput | unknown): Set<string> {
  const values = new Set<string>();
  const add = (value: unknown) => {
    const text = asString(value).trim();
    if (text) values.add(normalizeForCompare(text));
  };
  const visitRecord = (record: Record<string, unknown>) => {
    for (const [key, value] of Object.entries(record)) {
      if (NORMALIZED_KEYS.has(key)) add(value);
    }
  };
  if (Array.isArray(result.fields)) {
    for (const raw of result.fields) {
      if (!isRecord(raw)) continue;
      const key = asString(raw.name ?? raw.key ?? raw.en).trim();
      if (NORMALIZED_KEYS.has(key)) add(raw.value ?? raw.text);
    }
  }
  if (isRecord(result.document_fields)) visitRecord(result.document_fields);
  if (isRecord(input) && isRecord(input.normalizedResult)) {
    const normalized = input.normalizedResult;
    if (Array.isArray(normalized.fields)) {
      for (const raw of normalized.fields) {
        if (isRecord(raw)) add(raw.value ?? raw.originalValue);
      }
    }
  }
  return values;
}

function splitLines(text: string, maxLines: number): string[] {
  return text.split(/\r?\n/).map((line) => line.trim()).filter(Boolean).slice(0, maxLines);
}

function extractValueAfterLabel(line: string, label: string): string {
  const pattern = new RegExp(`${escapeRegExp(label)}\\s*[:：=\\-–—]?\\s*(.*)$`, "i");
  const match = line.match(pattern);
  if (!match) return "";
  return compactText(match[1].replace(/^(번호|No\.?|NO)\s*[:：=\\-–—]?\s*/i, ""), MAX_VALUE_LENGTH);
}

function detectLabelCandidate(line: string): { type: CandidateFieldType; value: string; confidence: number } | null {
  for (const type of LABEL_TYPES) {
    for (const label of TYPE_LABELS[type].labels) {
      const labelHit = new RegExp(escapeRegExp(label), "i").test(line);
      if (!labelHit) continue;
      let value = extractValueAfterLabel(line, label);
      if (type === "pageInfo") value = compactText(line, MAX_VALUE_LENGTH);
      if (!value) continue;
      const exact = normalizeForCompare(line).includes(normalizeForCompare(label));
      return { type, value, confidence: exact ? 0.85 : 0.7 };
    }
  }
  const pageMatch = line.match(/(?:page\s*\d+\s*(?:of|\/)\s*\d+|\d+\s*페이지\s*중\s*\d+\s*페이지|\d+\s*\/\s*\d+)/i);
  if (pageMatch) return { type: "pageInfo", value: compactText(pageMatch[0], MAX_VALUE_LENGTH), confidence: 0.7 };
  return null;
}

function isExcludedIdentifier(value: string): boolean {
  const text = value.trim();
  if (/^\d{1,5}$/.test(text)) return true;
  if (/^\d{4}[-/.]\d{1,2}[-/.]\d{1,2}$/.test(text)) return true;
  if (/^\d{3}-\d{2}-\d{5}$/.test(text)) return true;
  if (/^\d{2,4}-\d{3,4}-\d{4}$/.test(text)) return true;
  if (/^[\d,]+(?:원)?$/.test(text)) return true;
  return false;
}

function detectUnknownIdentifier(line: string): string | null {
  const tokens = line.match(/[A-Z0-9][A-Z0-9-]{5,}/g) ?? [];
  for (const token of tokens) {
    if (!/[A-Z]/.test(token) || !/\d/.test(token)) continue;
    if (isExcludedIdentifier(token)) continue;
    return compactText(token, MAX_VALUE_LENGTH);
  }
  return null;
}

function detectUnknownKeyValue(line: string): { label: string; value: string } | null {
  const match = line.match(/^([^:：=]{2,20})\s*[:：=]\s*(.{2,80})$/);
  if (!match) return null;
  const label = compactText(match[1], 24);
  const value = compactText(match[2], MAX_VALUE_LENGTH);
  if (!label || !value) return null;
  if (/^[\d\s,.-]+$/.test(label)) return null;
  return { label, value };
}

function sourceFieldLabel(field: Record<string, unknown>): string {
  return asString(field.labelKo ?? field.ko ?? field.label ?? field.name ?? field.key ?? field.en).trim();
}

function sourceFieldValue(field: Record<string, unknown>): string {
  return asString(field.value ?? field.text ?? field.originalValue).trim();
}

function makeCandidate(params: {
  id: number;
  type: CandidateFieldType;
  value: string;
  sourceText: string;
  source: CandidateFieldSource;
  confidence: number;
  normalizedValues: Set<string>;
  bboxRefs?: unknown[];
}): CandidateField | null {
  const value = compactText(params.value, MAX_VALUE_LENGTH);
  if (!value) return null;
  const normalizedValue = normalizeForCompare(value);
  if (params.normalizedValues.has(normalizedValue)) return null;
  const labels = TYPE_LABELS[params.type];
  const candidate: CandidateField = {
    candidateId: `cf-${String(params.id).padStart(3, "0")}`,
    candidateType: params.type,
    labelKo: labels.ko,
    labelEn: labels.en,
    value,
    sourceText: compactText(params.sourceText),
    confidence: params.confidence,
    source: params.source,
    status: "candidate",
    reviewStatus: "review_recommended",
  };
  if (params.bboxRefs) candidate.bboxRefs = params.bboxRefs;
  if (params.type !== "unknownIdentifier" && params.type !== "unknownKeyValue") {
    candidate.normalizedKeySuggestion = params.type;
  }
  return candidate;
}

function dedupeCandidates(candidates: CandidateField[]): CandidateField[] {
  const byKey = new Map<string, CandidateField>();
  for (const candidate of candidates) {
    const key = `${candidate.candidateType}:${normalizeForCompare(candidate.value)}`;
    const existing = byKey.get(key);
    if (!existing || candidate.confidence > existing.confidence) byKey.set(key, candidate);
  }
  const valuesWithLabel = new Set(
    [...byKey.values()]
      .filter((item) => item.candidateType !== "unknownIdentifier" && item.candidateType !== "unknownKeyValue")
      .map((item) => normalizeForCompare(item.value)),
  );
  return [...byKey.values()].filter((item) => {
    if (item.candidateType !== "unknownIdentifier") return true;
    return !valuesWithLabel.has(normalizeForCompare(item.value));
  });
}

function buildFromLine(
  line: string,
  source: CandidateFieldSource,
  nextId: () => number,
  normalizedValues: Set<string>,
  bboxRefs?: unknown[],
): CandidateField | null {
  const labelHit = detectLabelCandidate(line);
  if (labelHit) {
    return makeCandidate({
      id: nextId(),
      type: labelHit.type,
      value: labelHit.value,
      sourceText: line,
      source,
      confidence: labelHit.confidence,
      normalizedValues,
      bboxRefs,
    });
  }
  const identifier = detectUnknownIdentifier(line);
  if (identifier) {
    return makeCandidate({
      id: nextId(),
      type: "unknownIdentifier",
      value: identifier,
      sourceText: line,
      source,
      confidence: 0.55,
      normalizedValues,
      bboxRefs,
    });
  }
  const keyValue = detectUnknownKeyValue(line);
  if (keyValue) {
    return makeCandidate({
      id: nextId(),
      type: "unknownKeyValue",
      value: keyValue.value,
      sourceText: `${keyValue.label}: ${keyValue.value}`,
      source,
      confidence: 0.5,
      normalizedValues,
      bboxRefs,
    });
  }
  return null;
}

function shouldKeepUnmapped(line: string, normalizedValues: Set<string>): boolean {
  const text = compactText(line);
  if (text.length < 4) return false;
  if (/^[\d\s,.-]+$/.test(text)) return false;
  if (normalizedValues.has(normalizeForCompare(text))) return false;
  return true;
}

function scanFieldLikeArray(
  value: unknown,
  source: CandidateFieldSource,
  nextId: () => number,
  normalizedValues: Set<string>,
): CandidateField[] {
  if (!Array.isArray(value)) return [];
  const out: CandidateField[] = [];
  for (const raw of value) {
    if (!isRecord(raw)) continue;
    const label = sourceFieldLabel(raw);
    const fieldValue = sourceFieldValue(raw);
    const line = [label, fieldValue].filter(Boolean).join(": ");
    if (!line) continue;
    const candidate = buildFromLine(line, source, nextId, normalizedValues, compactBBoxRefs(raw.sourceBboxes ?? raw.bboxRefs));
    if (candidate) out.push(candidate);
  }
  return out;
}

function scanDocumentFields(
  value: unknown,
  nextId: () => number,
  normalizedValues: Set<string>,
): CandidateField[] {
  if (!isRecord(value)) return [];
  const out: CandidateField[] = [];
  for (const [key, rawValue] of Object.entries(value)) {
    if (NORMALIZED_KEYS.has(key)) continue;
    const fieldValue = asString(rawValue).trim();
    if (!fieldValue) continue;
    const line = `${key}: ${fieldValue}`;
    const candidate = buildFromLine(line, "document_fields", nextId, normalizedValues);
    if (candidate) out.push(candidate);
  }
  return out;
}

export function buildCandidateFields(input: CandidateFieldBuilderInput | unknown): CandidateFieldBuilderOutput {
  void FULL_TEXT_OUTPUT_FORBIDDEN_MARKER;
  void IMAGE_BASE64_OUTPUT_FORBIDDEN_MARKER;
  void CANDIDATE_NOT_AUTO_PROMOTED_MARKER;
  const result = resolveResult(input);
  const normalizedValues = collectNormalizedValues(result, input);
  const warnings: string[] = [];
  const maxLines = isRecord(input) && typeof input.maxLines === "number" ? input.maxLines : DEFAULT_MAX_LINES;
  const maxUnmapped = isRecord(input) && typeof input.maxUnmappedTextCandidates === "number"
    ? input.maxUnmappedTextCandidates
    : DEFAULT_MAX_UNMAPPED;
  let id = 1;
  const nextId = () => id++;

  const candidates: CandidateField[] = [];
  const lines = splitLines(asString(result.full_text), maxLines);
  for (const line of lines) {
    const candidate = buildFromLine(line, "full_text_line", nextId, normalizedValues);
    if (candidate) candidates.push(candidate);
  }
  candidates.push(...scanFieldLikeArray(result.fields, "fields", nextId, normalizedValues));
  candidates.push(...scanFieldLikeArray(result.raw_ocr_fields, "raw_ocr_fields", nextId, normalizedValues));
  candidates.push(...scanDocumentFields(result.document_fields, nextId, normalizedValues));

  const candidateFields = dedupeCandidates(candidates).map((candidate, index) => ({
    ...candidate,
    candidateId: `cf-${String(index + 1).padStart(3, "0")}`,
  }));
  const candidateSourceTexts = new Set(candidateFields.map((candidate) => normalizeForCompare(candidate.sourceText)));
  const unmappedTextCandidates: UnmappedTextCandidate[] = [];
  for (const line of lines) {
    if (unmappedTextCandidates.length >= maxUnmapped) break;
    if (candidateSourceTexts.has(normalizeForCompare(compactText(line)))) continue;
    if (!shouldKeepUnmapped(line, normalizedValues)) continue;
    unmappedTextCandidates.push({
      candidateId: `ut-${String(unmappedTextCandidates.length + 1).padStart(3, "0")}`,
      text: compactText(line),
      confidence: 0.4,
      reason: "unmapped_compact_line",
    });
  }
  if (lines.length >= maxLines) warnings.push("full_text_line_scan_truncated");

  return {
    candidateFields,
    unmappedTextCandidates,
    userSelectedFields: [],
    warnings,
    builderMeta: {
      builderVersion: BUILDER_VERSION,
      rawOcrPolicy: {
        fullTextIncluded: false,
        imageBase64Included: false,
      },
      noAutoPromotionToNormalizedResult: true,
    },
  };
}
