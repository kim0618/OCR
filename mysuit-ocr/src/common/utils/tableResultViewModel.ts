/**
 * tableResultViewModel.ts (TPL-8D)
 *
 * Pure helper that normalizes every supported table result source into a
 * single, render-friendly view model array. Preview / Custom / Clean JSON /
 * Markdown / future Template column projection all consume the SAME view
 * model so they cannot diverge (TPL-8C precheck).
 *
 * Supported sources:
 *   - `backend_document_fields`   : raw.document_fields.tableRows (invoice
 *     statement extracted by backend; canonical-keyed) — TPL-8D
 *   - `template_region_canonical` : Template generation table.columns
 *     projection of document_fields.tableRows — TPL-10
 *   - `unstructured_definition`   : result.unstructuredTables (TPL-8B
 *     projection of user template.tables[].columns) — TPL-8D
 *
 * Placeholder source (future phase):
 *   - `field_value_legacy` : OcrFieldResult.value (JSON string) fallback
 *
 * Boundary:
 *   - Pure helper. No React, DOM, storage, fetch, backend.
 *   - Read-only on input: never mutates `result` or any nested object.
 *   - Delegates cell normalization to `buildStructuredTableViewModel` so
 *     that Preview's existing fixture lock (tmp/fixtures/table_view_model_v1/)
 *     is preserved verbatim for the backend source.
 */

import { buildStructuredTableViewModel } from "./structuredTableViewModel";
import {
  buildInvoicePreviewCols,
  type InvoiceDisplayCol,
} from "./invoiceTableDisplay";

// ---------------------------------------------------------------------------
// Public types
// ---------------------------------------------------------------------------

export type TableResultSource =
  | "backend_document_fields"
  | "unstructured_definition"
  | "template_region_canonical"
  | "field_value_legacy";

export type TableResultColumn = {
  columnKey: string;
  labelKo: string;
  labelEn?: string;
  /** Provenance hint: "user" for user-defined, "canonical" for backend-driven. */
  source?: "user" | "canonical" | "fallback";
};

export type TableResultCell = {
  key: string;
  value: string;
  displayValue: string;
  isEmpty: boolean;
};

export type TableResultRow = {
  index: number;
  /** Quick key→value lookup. Same normalized strings as `cells[i].value`. */
  values: Record<string, string>;
  /** Ordered by `columns`. Same length as `columns`. */
  cells: TableResultCell[];
};

export type TableResultMeta = {
  documentType?: string;
  source: TableResultSource;
  rowCount: number;
  columnCount: number;
  hasRows: boolean;
  hasColumns: boolean;
  /** Free-form identifier for the originating source (e.g. "document_fields.tableRows"). */
  originalSource?: string;
};

export type TableResultViewModel = {
  tableKey: string;
  labelKo: string;
  labelEn?: string;
  source: TableResultSource;
  columns: TableResultColumn[];
  rows: TableResultRow[];
  meta: TableResultMeta;
};

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

const EMPTY_PLACEHOLDER = "-";

function isPlainRecord(v: unknown): v is Record<string, unknown> {
  return !!v && typeof v === "object" && !Array.isArray(v);
}

function safeOptionalString(v: unknown): string | undefined {
  if (typeof v !== "string") return undefined;
  const trimmed = v.trim();
  return trimmed.length > 0 ? v : undefined;
}

/**
 * Convert `buildStructuredTableViewModel`'s `{columns, rows: [{cells}], meta}`
 * output into the TPL-8D `TableResultViewModel` shape. We retain the rich
 * per-cell normalization from the structured helper and add a `values` map.
 */
function wrapStructuredViewModel(params: {
  source: TableResultSource;
  tableKey: string;
  labelKo: string;
  labelEn?: string;
  documentType?: string;
  originalSource: string;
  displayCols: ReadonlyArray<InvoiceDisplayCol>;
  rows: ReadonlyArray<Record<string, unknown>>;
  columnSource: "user" | "canonical";
}): TableResultViewModel {
  const structured = buildStructuredTableViewModel({
    rows: params.rows,
    displayCols: params.displayCols,
    emptyValue: EMPTY_PLACEHOLDER,
  });
  const columns: TableResultColumn[] = structured.columns.map((c) => {
    const inputCol = params.displayCols.find((d) => d.key === c.key);
    const out: TableResultColumn = {
      columnKey: c.key,
      labelKo: c.label,
      source: params.columnSource,
    };
    const labelEn = inputCol && safeOptionalString((inputCol as { labelEn?: unknown }).labelEn);
    if (labelEn !== undefined) out.labelEn = labelEn;
    return out;
  });
  const rows: TableResultRow[] = structured.rows.map((r, idx) => {
    const values: Record<string, string> = {};
    const cells: TableResultCell[] = r.cells.map((cell) => {
      values[cell.key] = cell.value;
      return {
        key: cell.key,
        value: cell.value,
        displayValue: cell.displayValue,
        isEmpty: cell.isEmpty,
      };
    });
    return { index: idx, values, cells };
  });
  const meta: TableResultMeta = {
    source: params.source,
    rowCount: rows.length,
    columnCount: columns.length,
    hasRows: rows.length > 0,
    hasColumns: columns.length > 0,
    originalSource: params.originalSource,
  };
  if (params.documentType !== undefined) meta.documentType = params.documentType;
  const out: TableResultViewModel = {
    tableKey: params.tableKey,
    labelKo: params.labelKo,
    source: params.source,
    columns,
    rows,
    meta,
  };
  if (params.labelEn !== undefined) out.labelEn = params.labelEn;
  return out;
}

// ---------------------------------------------------------------------------
// Source: backend_document_fields
// ---------------------------------------------------------------------------

function buildBackendDocumentFieldsViewModel(
  result: Record<string, unknown>,
  documentType: string | undefined,
): TableResultViewModel | null {
  const df = result.document_fields;
  if (!isPlainRecord(df)) return null;
  const rawRows = df.tableRows;
  if (!Array.isArray(rawRows) || rawRows.length === 0) return null;
  const rows: Array<Record<string, unknown>> = [];
  for (const r of rawRows as unknown[]) {
    if (isPlainRecord(r)) rows.push(r);
  }
  if (rows.length === 0) return null;
  const tableMeta = isPlainRecord(df.tableMeta) ? df.tableMeta : null;
  const displayCols = buildInvoicePreviewCols(tableMeta, rows);
  if (displayCols.length === 0) return null;
  return wrapStructuredViewModel({
    source: "backend_document_fields",
    tableKey: "document_fields.tableRows",
    labelKo: "문서 표",
    documentType,
    originalSource: "document_fields.tableRows",
    displayCols,
    rows,
    columnSource: "canonical",
  });
}

// ---------------------------------------------------------------------------
// Source: unstructured_definition
// ---------------------------------------------------------------------------

function buildUnstructuredViewModels(
  result: Record<string, unknown>,
  documentType: string | undefined,
): TableResultViewModel[] {
  const list = result.unstructuredTables;
  if (!Array.isArray(list) || list.length === 0) return [];
  const out: TableResultViewModel[] = [];
  for (let idx = 0; idx < list.length; idx++) {
    const t = list[idx];
    if (!isPlainRecord(t)) continue;
    const rawColumns = Array.isArray(t.columns) ? (t.columns as unknown[]) : [];
    const columns: InvoiceDisplayCol[] = [];
    const labelEnMap: Record<string, string> = {};
    for (const c of rawColumns) {
      if (!isPlainRecord(c)) continue;
      const columnKey = safeOptionalString(c.columnKey);
      if (!columnKey) continue;
      const labelKo = typeof c.labelKo === "string" ? c.labelKo : "";
      columns.push({ key: columnKey, labelKo: labelKo || columnKey });
      const labelEn = safeOptionalString(c.labelEn);
      if (labelEn !== undefined) labelEnMap[columnKey] = labelEn;
    }
    if (columns.length === 0) continue;
    const rawRows = Array.isArray(t.rows) ? (t.rows as unknown[]) : [];
    const rows: Array<Record<string, unknown>> = [];
    for (const r of rawRows) {
      if (isPlainRecord(r)) rows.push(r);
    }
    const tableKey = safeOptionalString(t.tableKey) ?? `unstructured_${idx + 1}`;
    const labelKoTable =
      (typeof t.labelKo === "string" && t.labelKo.length > 0 && t.labelKo)
      || (typeof t.labelEn === "string" && t.labelEn.length > 0 && t.labelEn)
      || tableKey;
    const labelEnTable = safeOptionalString(t.labelEn);
    const vm = wrapStructuredViewModel({
      source: "unstructured_definition",
      tableKey,
      labelKo: labelKoTable,
      labelEn: labelEnTable,
      documentType,
      originalSource: `unstructuredTables[${idx}]`,
      displayCols: columns,
      rows,
      columnSource: "user",
    });
    // Attach per-column labelEn from the original input (the structured
    // helper drops it because InvoiceDisplayCol doesn't carry labelEn).
    if (Object.keys(labelEnMap).length > 0) {
      vm.columns = vm.columns.map((c) =>
        labelEnMap[c.columnKey] !== undefined
          ? { ...c, labelEn: labelEnMap[c.columnKey] }
          : c,
      );
    }
    out.push(vm);
  }
  return out;
}

// ---------------------------------------------------------------------------
// Source: template_region_canonical (TPL-10)
// ---------------------------------------------------------------------------

/**
 * Projection key priority (column resolves to backend canonical key):
 *   1. column.columnKey
 *   2. column.canonicalColumn
 *   3. column.labelEn
 *   4. column.enField
 *
 * labelKo priority:
 *   1. column.labelKo
 *   2. column.koField
 *   3. column.canonicalColumn
 *   4. column.columnKey
 *   5. `컬럼 N`
 *
 * labelEn priority:
 *   1. column.labelEn
 *   2. column.enField
 *   3. column.columnKey
 *   4. column.canonicalColumn
 */
function resolveTemplateColumnDescriptor(
  c: Record<string, unknown>,
  fallbackIndex: number,
): { columnKey: string; labelKo: string; labelEn: string | undefined } | null {
  const columnKey =
    safeOptionalString(c.columnKey)
    ?? safeOptionalString(c.canonicalColumn)
    ?? safeOptionalString(c.labelEn)
    ?? safeOptionalString(c.enField);
  if (!columnKey) return null;
  const labelKo =
    safeOptionalString(c.labelKo)
    ?? safeOptionalString(c.koField)
    ?? safeOptionalString(c.canonicalColumn)
    ?? safeOptionalString(c.columnKey)
    ?? `컬럼 ${fallbackIndex + 1}`;
  const labelEn =
    safeOptionalString(c.labelEn)
    ?? safeOptionalString(c.enField)
    ?? safeOptionalString(c.columnKey)
    ?? safeOptionalString(c.canonicalColumn);
  return { columnKey, labelKo, labelEn };
}

function buildTemplateRegionCanonicalViewModels(
  result: Record<string, unknown>,
  template: unknown,
  documentType: string | undefined,
): TableResultViewModel[] {
  if (!isPlainRecord(template)) return [];
  const regions = template.regions;
  if (!Array.isArray(regions)) return [];

  const df = result.document_fields;
  if (!isPlainRecord(df)) return [];
  const rawRows = df.tableRows;
  if (!Array.isArray(rawRows) || rawRows.length === 0) return [];
  const backendRows: Array<Record<string, unknown>> = [];
  for (const r of rawRows as unknown[]) {
    if (isPlainRecord(r)) backendRows.push(r);
  }
  if (backendRows.length === 0) return [];

  const out: TableResultViewModel[] = [];
  let emitted = 0;
  for (let regionIdx = 0; regionIdx < regions.length; regionIdx++) {
    const region = regions[regionIdx];
    if (!isPlainRecord(region)) continue;
    const fieldType = safeOptionalString(region.fieldType);
    if (fieldType !== undefined && fieldType !== "table") continue;
    const table = isPlainRecord(region.table) ? region.table : null;
    if (!table) continue;
    const rawColumns = Array.isArray(table.columns) ? (table.columns as unknown[]) : [];
    if (rawColumns.length === 0) continue;

    const displayCols: InvoiceDisplayCol[] = [];
    const labelEnMap: Record<string, string> = {};
    const seenKeys = new Set<string>();
    for (let colIdx = 0; colIdx < rawColumns.length; colIdx++) {
      const c = rawColumns[colIdx];
      if (!isPlainRecord(c)) continue;
      const descriptor = resolveTemplateColumnDescriptor(c, colIdx);
      if (!descriptor) continue;
      if (seenKeys.has(descriptor.columnKey)) continue;
      seenKeys.add(descriptor.columnKey);
      displayCols.push({ key: descriptor.columnKey, labelKo: descriptor.labelKo });
      if (descriptor.labelEn !== undefined) labelEnMap[descriptor.columnKey] = descriptor.labelEn;
    }
    if (displayCols.length === 0) continue;

    emitted++;
    const regionId = safeOptionalString(region.id);
    const tableName = safeOptionalString(table.tableName);
    const regionName = safeOptionalString(region.name);
    const tableKey =
      tableName
      ?? regionId
      ?? `template_region_table_${emitted}`;
    const labelKoTable =
      tableName
      ?? regionName
      ?? "템플릿 테이블";
    const vm = wrapStructuredViewModel({
      source: "template_region_canonical",
      tableKey,
      labelKo: labelKoTable,
      documentType,
      originalSource: `template.regions[${regionIdx}].table.columns`,
      displayCols,
      rows: backendRows,
      columnSource: "user",
    });
    if (Object.keys(labelEnMap).length > 0) {
      vm.columns = vm.columns.map((c) =>
        labelEnMap[c.columnKey] !== undefined
          ? { ...c, labelEn: labelEnMap[c.columnKey] }
          : c,
      );
    }
    out.push(vm);
  }
  return out;
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Build the common table result view model array for a RunOCR `result`.
 *
 * Output order:
 *   1. backend_document_fields   (if present and non-empty)
 *   2. template_region_canonical (per template.regions order — TPL-10)
 *   3. unstructured_definition   (per `result.unstructuredTables` order)
 *
 * Future (NOT implemented yet):
 *   4. field_value_legacy
 *
 * Caller responsibilities:
 *   - Decide whether to render duplicates (invoice_statement may have backend
 *     + template + unstructured representing the same physical table).
 *   - Decide UI columns / sorting / styling beyond ViewModel data.
 *   - Supply `template` when a template's table.columns should drive a
 *     projection of backend tableRows.
 */
export function buildTableResultViewModels(
  result: unknown,
  template?: unknown,
): TableResultViewModel[] {
  if (!isPlainRecord(result)) return [];

  const documentType =
    safeOptionalString(result.documentType)
    ?? safeOptionalString(result.doc_type)
    ?? (isPlainRecord(result.document_fields)
      ? safeOptionalString((result.document_fields as Record<string, unknown>).doc_type)
      : undefined)
    ?? (isPlainRecord(template) ? safeOptionalString(template.documentType) : undefined);

  const models: TableResultViewModel[] = [];

  const backend = buildBackendDocumentFieldsViewModel(result, documentType);
  if (backend) models.push(backend);

  const templateRegion = buildTemplateRegionCanonicalViewModels(result, template, documentType);
  for (const vm of templateRegion) models.push(vm);

  const unstructured = buildUnstructuredViewModels(result, documentType);
  for (const vm of unstructured) models.push(vm);

  // field_value_legacy is a reserved placeholder (see TableResultSource) and
  // is intentionally not produced — a later phase will add it.

  return models;
}

/**
 * TPL-13B: pick the representative table result view models for UI / export.
 *
 * The full `buildTableResultViewModels` output may contain multiple
 * representations of the SAME physical table (backend canonical rows, the
 * user's template-column projection, the user's unstructured-table
 * projection). Showing all of them duplicates the same data on screen and in
 * Clean JSON / Markdown.
 *
 * Priority (highest first):
 *   1. `template_region_canonical` — user-defined columns on backend rows
 *   2. `unstructured_definition`   — user-defined columns on a different shape
 *   3. `backend_document_fields`   — canonical fallback
 *   4. `field_value_legacy`        — last-resort fallback
 *
 * When a higher-priority source is present, all lower-priority sources are
 * dropped from the representative output. Inside the chosen tier, the
 * original `buildTableResultViewModels` order is preserved.
 *
 * Pure: never mutates input. Returns a fresh array (the entries themselves
 * are the same references — callers must not mutate them).
 */
export function selectRepresentativeTableResultViewModels(
  viewModels: ReadonlyArray<TableResultViewModel>,
): TableResultViewModel[] {
  if (!Array.isArray(viewModels) || viewModels.length === 0) return [];
  const PRIORITY: ReadonlyArray<TableResultSource> = [
    "template_region_canonical",
    "unstructured_definition",
    "backend_document_fields",
    "field_value_legacy",
  ];
  for (const tier of PRIORITY) {
    const hits = viewModels.filter((vm) => vm && vm.source === tier);
    if (hits.length > 0) return hits;
  }
  return [];
}
