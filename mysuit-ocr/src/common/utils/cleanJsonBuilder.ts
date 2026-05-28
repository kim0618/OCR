/**
 * cleanJsonBuilder.ts
 *
 * Pure helper that builds the Clean JSON v1 payload consumed by OcrResultPanel's
 * Preview / Copy / Export. Extracted from OcrResultPanel.tsx by FRONTEND-CLEANUP-1.
 *
 * Contract:  docs/CLEAN_JSON_CONTRACT_20260521.md
 * Fixtures:  tmp/fixtures/clean_json_v1/
 *
 * Purity:
 *  - No React hooks, no DOM, no storage, no closures over component state.
 *  - Output is fully determined by the input object.
 *  - Inputs are never mutated.
 *
 * LOCKED: 거래_3 insuranceCode/amount extra columns are current Clean JSON v1
 * behavior. See docs/CLEAN_JSON_V1_FIXTURE_LOCK_20260521.md — do not change here.
 */

import {
  INVOICE_TABLE_COL_PRIORITY,
  hasMeaningfulTableValue,
  normalizeTableCell,
} from "@/common/utils/invoiceTableDisplay";
import {
  selectRepresentativeTableResultViewModels,
  type TableResultViewModel,
} from "@/common/utils/tableResultViewModel";

// ── Output types ───────────────────────────────────────────────────────────────

export type CleanJsonInfo = {
  key: string;
  label: string;
  en?: string;
  value: string;
};

export type CleanJsonTable = {
  key: string;
  label: string;
  en?: string;
  rows: Record<string, string>[];
  /**
   * TPL-13B: optional column metadata. Present only when this entry was
   * promoted from a representative `template_region_canonical` /
   * `unstructured_definition` view model (i.e., user-defined columns).
   * Legacy backend-only tables (built from `docTableRows`) omit this key,
   * preserving the Clean JSON v1 fixture lock.
   */
  columns?: Array<{ columnKey: string; labelKo: string }>;
};

/**
 * TPL-8F: optional unstructured table block. Only populated when the caller
 * supplies `tableResultViewModels` with `source: "unstructured_definition"`
 * entries. The existing Clean JSON v1 contract (templateName/info/tables) is
 * preserved byte-identically when this input is absent (fixture lock).
 */
export type CleanJsonUnstructuredTable = {
  tableKey: string;
  labelKo: string;
  columns: Array<{ columnKey: string; labelKo: string }>;
  rows: Record<string, string>[];
};

/**
 * TPL-10: optional template table block. Only populated when the caller
 * supplies `tableResultViewModels` with `source: "template_region_canonical"`
 * entries (template.regions[].table.columns projection of backend tableRows).
 * Kept in a separate `templateTables` key — does NOT merge into
 * `unstructuredTables` to preserve semantic distinction.
 */
export type CleanJsonTemplateTable = {
  tableKey: string;
  labelKo: string;
  columns: Array<{ columnKey: string; labelKo: string }>;
  rows: Record<string, string>[];
};

export type CleanJsonResult = {
  templateName: string;
  info?: CleanJsonInfo[];
  tables?: CleanJsonTable[];
  /** TPL-10: only present when tableResultViewModels carry template entries. */
  templateTables?: CleanJsonTemplateTable[];
  /** TPL-8F: only present when tableResultViewModels carry unstructured entries. */
  unstructuredTables?: CleanJsonUnstructuredTable[];
};

// ── Input types ────────────────────────────────────────────────────────────────

/**
 * Minimum field shape the builder reads. Callers may pass wider field objects
 * (e.g. OcrFieldResult) — only these properties are consulted.
 */
export type CleanJsonInputField = {
  name: string;
  field_type: string;
  value?: string | null;
  ko?: string;
  en?: string;
  label?: string;
  tableRows?: Record<string, unknown>[];
  table_data?: unknown;
};

export type BuildCleanJsonInput = {
  templateName?: string | null;
  fields: ReadonlyArray<CleanJsonInputField>;
  docTableRows?: Record<string, unknown>[] | null;
  docTableDisplayCols?: ReadonlyArray<{ key: string }> | null;
  /**
   * TPL-8F: optional unified TableResult view models. Only
   * `source === "unstructured_definition"` entries influence the output
   * (appended as `unstructuredTables`). The `backend_document_fields` source
   * is intentionally ignored here because it overlaps with the existing
   * `docTableRows` / `docTableDisplayCols` path that is contract-locked by
   * Clean JSON v1 fixtures.
   */
  tableResultViewModels?: ReadonlyArray<TableResultViewModel>;
};

// ── Internal table-row helpers ─────────────────────────────────────────────────

const FALLBACK_CELL_KEYS_EXCLUDED = new Set([
  "itemCode",
  "lotNo",
  "unit",
  "supplyAmount",
  "taxAmount",
  "totalAmount",
  "remark",
]);

function cleanTableRowsFromObjects(
  rows: Record<string, unknown>[],
  cols: ReadonlyArray<{ key: string }> | null | undefined,
): Record<string, string>[] {
  const orderedKeys =
    cols && cols.length > 0
      ? cols.map((col) => col.key)
      : INVOICE_TABLE_COL_PRIORITY.map((col) => col.key).filter((key) =>
          hasMeaningfulTableValue(rows, key),
        );
  return rows.map((row) => {
    const obj: Record<string, string> = {};
    for (const key of orderedKeys) obj[key] = normalizeTableCell(row[key]);
    return obj;
  });
}

function cleanTableRowsFromCells(raw: unknown): Record<string, string>[] {
  if (!Array.isArray(raw)) return [];
  const rows = raw.filter((row): row is unknown[] => Array.isArray(row));
  if (rows.length === 0) return [];
  const fallbackKeys = INVOICE_TABLE_COL_PRIORITY
    .map((col) => col.key)
    .filter((key) => !FALLBACK_CELL_KEYS_EXCLUDED.has(key));
  return rows.map((row) => {
    const obj: Record<string, string> = {};
    row.forEach((cell, ci) => {
      const key = fallbackKeys[ci] ?? `col_${ci + 1}`;
      const value =
        cell && typeof cell === "object" && "value" in cell
          ? (cell as { value?: unknown }).value
          : cell;
      obj[key] = normalizeTableCell(value);
    });
    return obj;
  });
}

// ── Public builder ─────────────────────────────────────────────────────────────

/**
 * Build the Clean JSON v1 payload from resolved inputs.
 *
 * Caller responsibilities:
 *  - Resolve `docTableRows` from `result.document_fields.tableRows`.
 *  - Compute `docTableDisplayCols` via `buildInvoicePreviewCols(...)`.
 *  - Provide the canonical `templateName`.
 *
 * The function does not call any OCR/parser and does not touch storage.
 */
export function buildCleanJsonResult(input: BuildCleanJsonInput): CleanJsonResult {
  const { templateName, fields, docTableRows, docTableDisplayCols } = input;

  const info: CleanJsonInfo[] = [];
  for (const field of fields) {
    if (field.field_type !== "field") continue;
    const en = String(field.en ?? "").trim();
    const ko = String(field.ko ?? "").trim();
    info.push({
      key: en || field.name,
      label: ko || field.label || field.name,
      value: field.value ?? "",
    });
  }

  const tables: CleanJsonTable[] = [];
  for (const field of fields) {
    if (field.field_type !== "table") continue;
    let rows: Record<string, string>[] = [];
    if (docTableRows && docTableDisplayCols && docTableDisplayCols.length > 0) {
      rows = cleanTableRowsFromObjects(docTableRows, docTableDisplayCols);
    } else if (Array.isArray(field.tableRows) && field.tableRows.length > 0) {
      rows = cleanTableRowsFromObjects(field.tableRows, null);
    } else if (Array.isArray(field.table_data)) {
      rows = cleanTableRowsFromCells(field.table_data);
    } else if (field.value) {
      try {
        rows = cleanTableRowsFromCells(JSON.parse(field.value));
      } catch {
        /* ignore malformed legacy table value */
      }
    }
    const en = String(field.en ?? "").trim();
    const ko = String(field.ko ?? "").trim();
    tables.push({
      key: en || field.name,
      label: ko || field.label || field.name,
      rows,
    });
  }

  const result: CleanJsonResult = { templateName: templateName ?? "" };
  if (info.length > 0) result.info = info;
  if (tables.length > 0) result.tables = tables;

  // TPL-13B: representative table dedup.
  //   Up to TPL-10 we emitted `templateTables` / `unstructuredTables` as
  //   separate optional keys, which duplicated the same physical table
  //   across `tables` + `templateTables` (or `unstructuredTables`) when the
  //   user defined columns. Now a single representative entry per physical
  //   table goes into `tables`, and the legacy alt-keys are dropped.
  //
  //   Priority (selectRepresentativeTableResultViewModels):
  //     template_region_canonical > unstructured_definition >
  //     backend_document_fields > field_value_legacy
  //
  //   Backward compat:
  //     - When `tableResultViewModels` is absent (Clean JSON v1 fixture path)
  //       we leave `tables` untouched.
  //     - When the representative is `backend_document_fields`, we also
  //       leave `tables` untouched — the legacy `docTableRows` path already
  //       produced the same data and its shape is contract-locked.
  //     - Only template / unstructured representatives replace `tables`.
  if (Array.isArray(input.tableResultViewModels) && input.tableResultViewModels.length > 0) {
    const repVMs = selectRepresentativeTableResultViewModels(input.tableResultViewModels);
    const repSource = repVMs[0]?.source;
    if (repSource === "template_region_canonical" || repSource === "unstructured_definition") {
      const replacedTables: CleanJsonTable[] = repVMs.map((vm) => ({
        key: vm.tableKey,
        label: vm.labelKo,
        columns: vm.columns.map((c) => ({ columnKey: c.columnKey, labelKo: c.labelKo })),
        rows: vm.rows.map((row) => {
          const obj: Record<string, string> = {};
          for (const cell of row.cells) obj[cell.key] = cell.value;
          return obj;
        }),
      }));
      result.tables = replacedTables;
    }
    // `templateTables` / `unstructuredTables` keys are intentionally not
    // emitted — the representative entry is already in `tables`.
  }

  return result;
}
