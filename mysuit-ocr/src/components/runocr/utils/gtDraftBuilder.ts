import {
  selectRepresentativeTableResultViewModels,
  type TableResultViewModel,
} from "@/common/utils/tableResultViewModel";
import type {
  CandidateField,
  UnmappedTextCandidate,
  UserSelectedField,
} from "./candidateFieldBuilder";

export type DraftGtResultMode =
  | "template"
  | "unstructured_template"
  | "full_unstructured"
  | "unknown";

export type DraftGtFieldStatus =
  | "present_extracted"
  | "present_corrected"
  | "not_reviewed"
  | "present_unreadable"
  | "not_present_in_document"
  | "ambiguous"
  | "excluded"
  | "not_applicable";

export type DraftGtRowType = "item" | "summary" | "excluded" | "unknown";
export type DraftGtReviewStatus = "draft" | "reviewed" | "needs_review";

export type DraftGtOrientation = {
  expectedOrientation: "upright" | "rotated" | "unknown";
  expectedRotation: number;
  allowRightAngleRotation: boolean;
  allowDeskew: boolean;
};

export type DraftGtField = {
  key: string;
  labelKo?: string;
  labelEn?: string;
  originalValue: string;
  value: string;
  edited: boolean;
  confidence: number | null;
  fieldStatus: DraftGtFieldStatus;
  bboxRefs?: unknown[];
};

export type DraftGtTableRow = {
  rowIndex: number;
  rowType: DraftGtRowType;
  itemName: string;
  spec: string;
  productCode?: string;
  lotNo?: string;
  expiryDate?: string;
  quantity: string;
  unitPrice: string;
  amount: string;
  amountOnly: boolean;
  missingFields: string[];
  fieldStatus: Record<string, DraftGtFieldStatus>;
  reviewStatus: DraftGtReviewStatus;
  excludeReason: string | null;
  sourceRowMeta?: Record<string, unknown>;
  bboxRefs?: Record<string, unknown[]>;
};

export type DraftGtExcludedRow = {
  rowIndex: number;
  rowType: "summary" | "excluded" | "unknown";
  excludeReason: string;
  textCompact?: string;
};

export type DraftGtReviewMeta = {
  status: DraftGtReviewStatus;
  reviewedBy: string | null;
  reviewedAt: string | null;
  notes: string;
};

export type DraftGtSourceMeta = {
  sourceFile?: string;
  documentType: string;
  resultMode: DraftGtResultMode;
  generatedAt: string;
  builderVersion: string;
  [key: string]: unknown;
};

export type DraftGtDocument = {
  schemaVersion: string;
  sampleId?: string;
  sourceFile?: string;
  documentType: string;
  resultMode: DraftGtResultMode;
  orientationGt: DraftGtOrientation;
  normalizedResult: {
    fields: DraftGtField[];
    tableRows: DraftGtTableRow[];
  };
  candidates?: {
    fields?: unknown[];
    tableRows?: unknown[];
    excludedRows?: DraftGtExcludedRow[];
    candidateFields: CandidateField[];
    unmappedTextCandidates: UnmappedTextCandidate[];
    userSelectedFields: UserSelectedField[];
  };
  excludedRows: DraftGtExcludedRow[];
  reviewMeta: DraftGtReviewMeta;
  sourceMeta: DraftGtSourceMeta;
  builderMeta: {
    builderVersion: string;
    warnings: string[];
    exportBlocked: boolean;
  };
};

export type DraftGtBuilderInput = {
  ocrResult: unknown;
  editedFields?: unknown[] | null;
  customTableEdits?: Record<string, string>[] | null;
  tableResultViewModels?: unknown[] | null;
  resultMode?: DraftGtResultMode;
  documentType?: string;
  sourceFile?: string;
  sampleId?: string;
  orientationGt?: Partial<DraftGtOrientation>;
  sourceMeta?: Partial<DraftGtSourceMeta>;
  candidates?: unknown;
};

export type DraftGtBuilderOutput = {
  document: DraftGtDocument;
  warnings: string[];
  exportBlocked: boolean;
};

const BUILDER_VERSION = "gt-draft-builder-1d";
const SCHEMA_VERSION = "draft-gt-document.v1";
const RAW_OCR_POLICY_MARKER = "rawOcr_full_dump_forbidden";

const DEFAULT_ORIENTATION_GT: DraftGtOrientation = {
  expectedOrientation: "upright",
  expectedRotation: 0,
  allowRightAngleRotation: false,
  allowDeskew: true,
};

const FIELD_KEYS = [
  "itemName",
  "spec",
  "productCode",
  "lotNo",
  "expiryDate",
  "quantity",
  "unitPrice",
  "amount",
] as const;

const COLUMN_KEY_ALIASES: Record<string, (typeof FIELD_KEYS)[number]> = {
  itemName: "itemName",
  name: "itemName",
  item: "itemName",
  spec: "spec",
  productCode: "productCode",
  code: "productCode",
  lotNo: "lotNo",
  lot: "lotNo",
  expiryDate: "expiryDate",
  exp: "expiryDate",
  expiry: "expiryDate",
  quantity: "quantity",
  qty: "quantity",
  unitPrice: "unitPrice",
  price: "unitPrice",
  amount: "amount",
  total: "amount",
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return !!value && typeof value === "object" && !Array.isArray(value);
}

function asString(value: unknown): string {
  if (value === null || value === undefined) return "";
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  return "";
}

function optionalNonEmptyString(value: unknown): string | undefined {
  const text = asString(value).trim();
  return text.length > 0 ? asString(value) : undefined;
}

function normalizeDraftGtFieldStatus(value: string, edited: boolean): DraftGtFieldStatus {
  if (edited && value !== "") return "present_corrected";
  if (value !== "") return "present_extracted";
  return "not_reviewed";
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

function fieldKey(field: Record<string, unknown>): string {
  return (
    optionalNonEmptyString(field.name)
    ?? optionalNonEmptyString(field.key)
    ?? optionalNonEmptyString(field.en)
    ?? optionalNonEmptyString(field.label)
    ?? ""
  );
}

function fieldValue(field: Record<string, unknown>): string {
  return asString(field.value ?? field.text ?? field.originalValue);
}

function extractBaseFields(ocrResult: unknown): DraftGtField[] {
  const result = isRecord(ocrResult) ? ocrResult : {};
  const rawFields = Array.isArray(result.fields) ? result.fields : [];
  const fields: DraftGtField[] = [];
  for (const raw of rawFields) {
    if (!isRecord(raw)) continue;
    const key = fieldKey(raw);
    if (!key) continue;
    const value = fieldValue(raw);
    const field: DraftGtField = {
      key,
      originalValue: value,
      value,
      edited: false,
      confidence: typeof raw.confidence === "number" ? raw.confidence : null,
      fieldStatus: normalizeDraftGtFieldStatus(value, false),
    };
    const labelKo = optionalNonEmptyString(raw.ko ?? raw.labelKo ?? raw.label);
    const labelEn = optionalNonEmptyString(raw.en ?? raw.labelEn);
    const bboxRefs = compactBBoxRefs(raw.sourceBboxes ?? raw.bboxRefs);
    if (labelKo !== undefined) field.labelKo = labelKo;
    if (labelEn !== undefined) field.labelEn = labelEn;
    if (bboxRefs !== undefined) field.bboxRefs = bboxRefs;
    fields.push(field);
  }
  return fields;
}

function mergeEditedFields(baseFields: DraftGtField[], editedFields: unknown[] | null | undefined): DraftGtField[] {
  const byKey = new Map(baseFields.map((field) => [field.key, { ...field }]));
  const orderedKeys = baseFields.map((field) => field.key);
  if (Array.isArray(editedFields)) {
    for (const raw of editedFields) {
      if (!isRecord(raw)) continue;
      const key = fieldKey(raw);
      if (!key) continue;
      const editedValue = asString(raw.value ?? raw.text ?? "");
      const base = byKey.get(key);
      if (base) {
        const edited = editedValue !== base.originalValue;
        byKey.set(key, {
          ...base,
          value: editedValue,
          edited,
          fieldStatus: normalizeDraftGtFieldStatus(editedValue, edited),
        });
      } else {
        const field: DraftGtField = {
          key,
          originalValue: "",
          value: editedValue,
          edited: editedValue !== "",
          confidence: typeof raw.confidence === "number" ? raw.confidence : null,
          fieldStatus: normalizeDraftGtFieldStatus(editedValue, editedValue !== ""),
        };
        const labelKo = optionalNonEmptyString(raw.ko ?? raw.labelKo ?? raw.label);
        const labelEn = optionalNonEmptyString(raw.en ?? raw.labelEn);
        if (labelKo !== undefined) field.labelKo = labelKo;
        if (labelEn !== undefined) field.labelEn = labelEn;
        byKey.set(key, field);
        orderedKeys.push(key);
      }
    }
  }
  return orderedKeys.map((key) => byKey.get(key)).filter((field): field is DraftGtField => !!field);
}

function resolveColumnKey(columnKey: string): (typeof FIELD_KEYS)[number] | null {
  return COLUMN_KEY_ALIASES[columnKey] ?? null;
}

function rowFieldStatus(value: string): DraftGtFieldStatus {
  return value === "" ? "not_reviewed" : "present_extracted";
}

function makeDraftTableRow(values: Record<string, string>, rowIndex: number): DraftGtTableRow {
  const row: DraftGtTableRow = {
    rowIndex,
    rowType: "item",
    itemName: values.itemName ?? "",
    spec: values.spec ?? "",
    productCode: values.productCode ?? "",
    lotNo: values.lotNo ?? "",
    expiryDate: values.expiryDate ?? "",
    quantity: values.quantity ?? "",
    unitPrice: values.unitPrice ?? "",
    amount: values.amount ?? "",
    amountOnly: false,
    missingFields: [],
    fieldStatus: {},
    reviewStatus: "draft",
    excludeReason: null,
  };
  for (const key of FIELD_KEYS) {
    const value = asString(row[key]);
    row.fieldStatus[key] = rowFieldStatus(value);
  }
  return row;
}

function tableRowsFromViewModel(vm: TableResultViewModel | null): DraftGtTableRow[] {
  if (!vm) return [];
  return vm.rows.map((row, idx) => {
    const values: Record<string, string> = {};
    for (const cell of row.cells) {
      const key = resolveColumnKey(cell.key);
      if (key) values[key] = cell.value;
    }
    const draftRow = makeDraftTableRow(values, idx + 1);
    draftRow.sourceRowMeta = {
      tableKey: vm.tableKey,
      source: vm.source,
      sourceRowIndex: row.index,
    };
    return draftRow;
  });
}

function mergeCustomTableEdits(params: {
  rows: DraftGtTableRow[];
  customTableEdits: Record<string, string>[] | null | undefined;
  representativeTable: TableResultViewModel | null;
  warnings: string[];
}): { rows: DraftGtTableRow[]; exportBlocked: boolean } {
  const edits = params.customTableEdits;
  if (!Array.isArray(edits) || edits.length === 0) {
    return { rows: params.rows.map((row) => ({ ...row, fieldStatus: { ...row.fieldStatus } })), exportBlocked: false };
  }
  if (!params.representativeTable || params.rows.length === 0) {
    params.warnings.push("no_base_table_for_edits");
    return { rows: [], exportBlocked: true };
  }
  if (edits.length !== params.rows.length) {
    params.warnings.push("row_count_mismatch");
  }

  const knownColumns = new Set(params.representativeTable.columns.map((column) => column.columnKey));
  const merged = params.rows.map((row) => ({ ...row, fieldStatus: { ...row.fieldStatus } }));
  edits.forEach((editRow, rowIdx) => {
    if (!isRecord(editRow)) return;
    const target = merged[rowIdx];
    if (!target) {
      params.warnings.push("row_count_mismatch");
      return;
    }
    for (const [rawKey, rawValue] of Object.entries(editRow)) {
      const key = resolveColumnKey(rawKey);
      if (!key || (!knownColumns.has(rawKey) && !COLUMN_KEY_ALIASES[rawKey])) {
        params.warnings.push("unknown_column_key");
        continue;
      }
      target[key] = asString(rawValue);
      target.fieldStatus[key] = "present_corrected";
    }
  });
  return { rows: merged, exportBlocked: false };
}

function normalizeTableResultViewModels(values: unknown[] | null | undefined): TableResultViewModel[] {
  if (!Array.isArray(values)) return [];
  return values.filter((value): value is TableResultViewModel => {
    if (!isRecord(value)) return false;
    return Array.isArray(value.rows) && Array.isArray(value.columns) && typeof value.source === "string";
  });
}

function buildCandidates(value: unknown): DraftGtDocument["candidates"] | undefined {
  if (!isRecord(value)) return undefined;
  const candidates: DraftGtDocument["candidates"] = {
    candidateFields: [],
    unmappedTextCandidates: [],
    userSelectedFields: [],
  };
  if (Array.isArray(value.fields)) candidates.fields = value.fields;
  if (Array.isArray(value.tableRows)) candidates.tableRows = value.tableRows;
  if (Array.isArray(value.excludedRows)) candidates.excludedRows = value.excludedRows as DraftGtExcludedRow[];
  if (Array.isArray(value.candidateFields)) candidates.candidateFields = value.candidateFields as CandidateField[];
  if (Array.isArray(value.unmappedTextCandidates)) {
    candidates.unmappedTextCandidates = value.unmappedTextCandidates as UnmappedTextCandidate[];
  }
  if (Array.isArray(value.userSelectedFields)) candidates.userSelectedFields = value.userSelectedFields as UserSelectedField[];
  return Object.keys(candidates).length > 0 ? candidates : undefined;
}

function documentTypeFromInput(input: DraftGtBuilderInput): string {
  if (input.documentType) return input.documentType;
  if (isRecord(input.ocrResult)) {
    return (
      optionalNonEmptyString(input.ocrResult.documentType)
      ?? optionalNonEmptyString(input.ocrResult.doc_type)
      ?? "unknown"
    );
  }
  return "unknown";
}

export function buildDraftGtDocument(input: DraftGtBuilderInput): DraftGtBuilderOutput {
  void RAW_OCR_POLICY_MARKER;
  const warnings: string[] = [];
  const resultMode = input.resultMode ?? "unknown";
  const documentType = documentTypeFromInput(input);
  let exportBlocked = false;

  if (documentType === "unknown") {
    warnings.push("document_type_missing");
    exportBlocked = true;
  }

  const fields = mergeEditedFields(extractBaseFields(input.ocrResult), input.editedFields);
  const tableViewModels = normalizeTableResultViewModels(input.tableResultViewModels);
  const representativeTables = selectRepresentativeTableResultViewModels(tableViewModels);
  if (representativeTables.length > 1 && Array.isArray(input.customTableEdits) && input.customTableEdits.length > 0) {
    warnings.push("multi_table_merge_ambiguous");
  }
  const representativeTable = representativeTables[0] ?? null;
  const baseRows = tableRowsFromViewModel(representativeTable);
  const mergedRows = mergeCustomTableEdits({
    rows: baseRows,
    customTableEdits: input.customTableEdits,
    representativeTable,
    warnings,
  });
  exportBlocked = exportBlocked || mergedRows.exportBlocked;

  const orientationGt: DraftGtOrientation = {
    ...DEFAULT_ORIENTATION_GT,
    ...(input.orientationGt ?? {}),
  };
  const generatedAt = new Date().toISOString();
  const sourceMeta: DraftGtSourceMeta = {
    ...(input.sourceMeta ?? {}),
    sourceFile: input.sourceFile,
    documentType,
    resultMode,
    generatedAt,
    builderVersion: BUILDER_VERSION,
  };

  const document: DraftGtDocument = {
    schemaVersion: SCHEMA_VERSION,
    documentType,
    resultMode,
    orientationGt,
    normalizedResult: {
      fields,
      tableRows: mergedRows.rows,
    },
    excludedRows: [],
    reviewMeta: {
      status: "draft",
      reviewedBy: null,
      reviewedAt: null,
      notes: "",
    },
    sourceMeta,
    builderMeta: {
      builderVersion: BUILDER_VERSION,
      warnings,
      exportBlocked,
    },
  };
  if (input.sampleId) document.sampleId = input.sampleId;
  if (input.sourceFile) document.sourceFile = input.sourceFile;
  const candidates = buildCandidates(input.candidates);
  if (candidates) document.candidates = candidates;
  return { document, warnings, exportBlocked };
}
