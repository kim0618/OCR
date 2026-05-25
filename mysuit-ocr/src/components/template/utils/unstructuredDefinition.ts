/**
 * Unstructured template definition types and pure helpers (TPL-3).
 *
 * Boundary: this module is a pure helper. It MUST NOT import React, DOM,
 * window/document, localStorage/sessionStorage/IndexedDB, fetch/XHR,
 * backend code, fixtures, templates.json, public/data, or any UI component.
 *
 * The shape is designed to be backward-compatible with the legacy
 * Unstructured payload `{ mode: "unstructured", fields, regions: [] }` while
 * adding `info` / `tables` and optional `documentType`. The serializer always
 * mirrors `info` back into legacy `fields` so existing readers (e.g.
 * RunOCR mapOcrResponse) keep working unchanged.
 */

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type LegacyUnstructuredField = {
  no: number;
  enField: string;
  koField: string;
};

export type UnstructuredInfoField = {
  key: string;
  labelKo: string;
  labelEn?: string;
  aliases?: string[];
  required?: boolean;
  visible?: boolean;
  order?: number;
  description?: string;
  /** Legacy mirror — kept so round-trip from fields-only payloads is stable. */
  no?: number;
};

export type UnstructuredColumnSource = "user" | "auto" | "legacy";

export type UnstructuredTableColumn = {
  columnKey: string;
  labelKo: string;
  labelEn?: string;
  aliases?: string[];
  required?: boolean;
  visible?: boolean;
  order?: number;
  source?: UnstructuredColumnSource;
  confidence?: number;
  userConfirmed?: boolean;
};

export type UnstructuredTableDef = {
  tableKey: string;
  labelKo: string;
  labelEn?: string;
  columns: UnstructuredTableColumn[];
  aliases?: string[];
  required?: boolean;
  order?: number;
  userConfirmed?: boolean;
  description?: string;
};

export type UnstructuredTemplateDefinition = {
  mode: "unstructured";
  templateName?: string;
  /**
   * Optional. Never auto-filled by normalize/serialize — preserved as-is when
   * present, omitted when absent. Existing fields-only templates may have no
   * documentType, and that state must be preserved (no implicit "receipt"
   * default).
   */
  documentType?: string;
  info: UnstructuredInfoField[];
  tables: UnstructuredTableDef[];
  /** Legacy mirror — derived from `info` on serialize. */
  fields: LegacyUnstructuredField[];
  /** Always `[]` for unstructured; preserved for payload-shape compatibility. */
  regions: never[];
};

export type UnstructuredTemplateInputState = {
  templateName?: string;
  documentType?: string;
  info?: UnstructuredInfoField[];
  tables?: UnstructuredTableDef[];
};

// ---------------------------------------------------------------------------
// Internal safe coercion helpers
// ---------------------------------------------------------------------------

function safeString(v: unknown): string {
  if (typeof v === "string") return v;
  if (v == null) return "";
  return String(v);
}

function safeOptionalString(v: unknown): string | undefined {
  if (typeof v !== "string") return undefined;
  const t = v.trim();
  return t.length > 0 ? v : undefined;
}

function safeNumber(v: unknown, fallback: number): number {
  return typeof v === "number" && Number.isFinite(v) ? v : fallback;
}

function safeOptionalNumber(v: unknown): number | undefined {
  return typeof v === "number" && Number.isFinite(v) ? v : undefined;
}

function safeOptionalBoolean(v: unknown): boolean | undefined {
  return typeof v === "boolean" ? v : undefined;
}

function safeStringArray(v: unknown): string[] | undefined {
  if (!Array.isArray(v)) return undefined;
  const out: string[] = [];
  for (const e of v) {
    if (typeof e === "string" && e.length > 0) out.push(e);
  }
  return out.length > 0 ? out : undefined;
}

function safeColumnSource(v: unknown): UnstructuredColumnSource | undefined {
  return v === "user" || v === "auto" || v === "legacy" ? v : undefined;
}

// ---------------------------------------------------------------------------
// Internal normalizers
// ---------------------------------------------------------------------------

function legacyFieldToInfo(raw: unknown, index: number): UnstructuredInfoField {
  const r = (raw ?? {}) as Record<string, unknown>;
  const en = safeString(r.enField).trim();
  const ko = safeString(r.koField).trim();
  const no = safeNumber(r.no, index + 1);
  const key = en.length > 0 ? en : `info_${no}`;
  const out: UnstructuredInfoField = {
    key,
    labelKo: ko,
    order: no,
    no,
  };
  if (en.length > 0) out.labelEn = en;
  return out;
}

function normalizeInfoField(raw: unknown, index: number): UnstructuredInfoField {
  const r = (raw ?? {}) as Record<string, unknown>;
  const order = safeNumber(r.order, index + 1);
  const ko = safeString(r.labelKo).trim();
  const en = safeOptionalString(r.labelEn);
  const explicitKey = safeOptionalString(r.key);
  const key = explicitKey ?? (en ?? `info_${order}`);
  const out: UnstructuredInfoField = {
    key,
    labelKo: ko,
    order,
    no: safeNumber(r.no, order),
  };
  if (en !== undefined) out.labelEn = en;
  const aliases = safeStringArray(r.aliases);
  if (aliases) out.aliases = aliases;
  const required = safeOptionalBoolean(r.required);
  if (required !== undefined) out.required = required;
  const visible = safeOptionalBoolean(r.visible);
  if (visible !== undefined) out.visible = visible;
  const description = safeOptionalString(r.description);
  if (description !== undefined) out.description = description;
  return out;
}

function normalizeColumn(raw: unknown, index: number): UnstructuredTableColumn {
  const r = (raw ?? {}) as Record<string, unknown>;
  const order = safeNumber(r.order, index + 1);
  const ko = safeString(r.labelKo).trim();
  const en = safeOptionalString(r.labelEn);
  const explicitKey = safeOptionalString(r.columnKey);
  const key = explicitKey ?? (en ?? `column_${order}`);
  const out: UnstructuredTableColumn = {
    columnKey: key,
    labelKo: ko,
    order,
  };
  if (en !== undefined) out.labelEn = en;
  const aliases = safeStringArray(r.aliases);
  if (aliases) out.aliases = aliases;
  const required = safeOptionalBoolean(r.required);
  if (required !== undefined) out.required = required;
  const visible = safeOptionalBoolean(r.visible);
  if (visible !== undefined) out.visible = visible;
  const source = safeColumnSource(r.source);
  if (source !== undefined) out.source = source;
  const confidence = safeOptionalNumber(r.confidence);
  if (confidence !== undefined) out.confidence = confidence;
  const userConfirmed = safeOptionalBoolean(r.userConfirmed);
  if (userConfirmed !== undefined) out.userConfirmed = userConfirmed;
  return out;
}

function normalizeTable(raw: unknown, index: number): UnstructuredTableDef {
  const r = (raw ?? {}) as Record<string, unknown>;
  const order = safeNumber(r.order, index + 1);
  const ko = safeString(r.labelKo).trim();
  const en = safeOptionalString(r.labelEn);
  const explicitKey = safeOptionalString(r.tableKey);
  const key = explicitKey ?? (en ?? `table_${order}`);
  const rawColumns = Array.isArray(r.columns) ? (r.columns as unknown[]) : [];
  const columns = rawColumns
    .map((c, i) => normalizeColumn(c, i))
    .sort((a, b) => (a.order ?? 0) - (b.order ?? 0))
    .map((c, i) => ({ ...c, order: i + 1 }));
  const out: UnstructuredTableDef = {
    tableKey: key,
    labelKo: ko.length > 0 ? ko : en ?? `테이블 ${order}`,
    columns,
    order,
  };
  if (en !== undefined) out.labelEn = en;
  const aliases = safeStringArray(r.aliases);
  if (aliases) out.aliases = aliases;
  const required = safeOptionalBoolean(r.required);
  if (required !== undefined) out.required = required;
  const userConfirmed = safeOptionalBoolean(r.userConfirmed);
  if (userConfirmed !== undefined) out.userConfirmed = userConfirmed;
  const description = safeOptionalString(r.description);
  if (description !== undefined) out.description = description;
  return out;
}

function deriveLegacyFields(info: UnstructuredInfoField[]): LegacyUnstructuredField[] {
  return info.map((f, idx) => {
    const no = typeof f.no === "number" ? f.no : f.order ?? idx + 1;
    const en = typeof f.labelEn === "string"
      ? f.labelEn
      : f.key.startsWith("info_") ? "" : f.key;
    return {
      no,
      enField: en,
      koField: safeString(f.labelKo),
    };
  });
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Normalize an arbitrary payload into UnstructuredTemplateDefinition.
 *
 * - Preserves `templateName` and `documentType` when present, never invents
 *   either.
 * - If `info` is present and non-empty, uses it; otherwise lifts legacy
 *   `fields[]` into `info`.
 * - Sorts `info` and `tables` by their declared `order` and then renumbers
 *   sequentially starting at 1.
 * - Always regenerates `fields` as a legacy mirror of the normalized `info`.
 * - Does not mutate the input.
 */
export function normalizeUnstructuredTemplate(
  json: unknown,
): UnstructuredTemplateDefinition {
  const j = (json && typeof json === "object" ? json : {}) as Record<string, unknown>;
  const templateName =
    safeOptionalString(j.templateName) ?? safeOptionalString(j.template_name);
  const documentType = safeOptionalString(j.documentType);

  let info: UnstructuredInfoField[];
  if (Array.isArray(j.info) && (j.info as unknown[]).length > 0) {
    info = (j.info as unknown[]).map((f, i) => normalizeInfoField(f, i));
  } else if (Array.isArray(j.fields)) {
    info = (j.fields as unknown[]).map((f, i) => legacyFieldToInfo(f, i));
  } else {
    info = [];
  }
  info = info
    .slice()
    .sort((a, b) => (a.order ?? 0) - (b.order ?? 0))
    .map((f, idx) => ({ ...f, order: idx + 1, no: idx + 1 }));

  const tables: UnstructuredTableDef[] = Array.isArray(j.tables)
    ? (j.tables as unknown[])
        .map((t, i) => normalizeTable(t, i))
        .sort((a, b) => (a.order ?? 0) - (b.order ?? 0))
        .map((t, idx) => ({ ...t, order: idx + 1 }))
    : [];

  const fields = deriveLegacyFields(info);
  const out: UnstructuredTemplateDefinition = {
    mode: "unstructured",
    info,
    tables,
    fields,
    regions: [],
  };
  if (templateName !== undefined) out.templateName = templateName;
  if (documentType !== undefined) out.documentType = documentType;
  return out;
}

/**
 * Serialize an in-memory editor state into a save-ready payload.
 * Internally delegates to normalize so the output shape is identical.
 */
export function serializeUnstructuredTemplate(
  state: UnstructuredTemplateInputState,
): UnstructuredTemplateDefinition {
  return normalizeUnstructuredTemplate({
    mode: "unstructured",
    templateName: state.templateName,
    documentType: state.documentType,
    info: state.info ?? [],
    tables: state.tables ?? [],
    fields: [],
    regions: [],
  });
}

// ---------------------------------------------------------------------------
// Default constructors for the editor (TPL-5)
// ---------------------------------------------------------------------------

export function createDefaultInfoField(index: number): UnstructuredInfoField {
  const order = Math.max(1, Math.floor(typeof index === "number" ? index : 1));
  return {
    key: `field_${order}`,
    labelKo: "",
    labelEn: "",
    required: false,
    visible: true,
    order,
    no: order,
  };
}

export function createDefaultTableDef(index: number): UnstructuredTableDef {
  const order = Math.max(1, Math.floor(typeof index === "number" ? index : 1));
  return {
    tableKey: `table_${order}`,
    labelKo: `테이블 ${order}`,
    labelEn: "",
    columns: [],
    required: false,
    order,
    userConfirmed: false,
  };
}

export function createDefaultTableColumn(index: number): UnstructuredTableColumn {
  const order = Math.max(1, Math.floor(typeof index === "number" ? index : 1));
  return {
    columnKey: `column_${order}`,
    labelKo: "",
    labelEn: "",
    required: false,
    visible: true,
    order,
    source: "user",
    userConfirmed: false,
  };
}

// ---------------------------------------------------------------------------
// Smoke-test exposure (used only by tmp/check_*.mjs — see TPL-3 plan)
// ---------------------------------------------------------------------------

export const __TPL3_INTERNAL__ = {
  legacyFieldToInfo,
  normalizeInfoField,
  normalizeColumn,
  normalizeTable,
  deriveLegacyFields,
};
