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
} from "@/lib/invoiceTableDisplay";

// ── Output types ───────────────────────────────────────────────────────────────

export type CleanJsonInfo = {
  key: string;
  label: string;
  value: string;
};

export type CleanJsonTable = {
  key: string;
  label: string;
  rows: Record<string, string>[];
};

export type CleanJsonResult = {
  templateName: string;
  info?: CleanJsonInfo[];
  tables?: CleanJsonTable[];
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
  label?: string;
  tableRows?: Record<string, unknown>[];
  table_data?: unknown;
};

export type BuildCleanJsonInput = {
  templateName?: string | null;
  fields: ReadonlyArray<CleanJsonInputField>;
  docTableRows?: Record<string, unknown>[] | null;
  docTableDisplayCols?: ReadonlyArray<{ key: string }> | null;
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
    info.push({
      key: field.name,
      label: field.ko || field.label || field.name,
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
    tables.push({
      key: field.name,
      label: field.ko || field.label || field.name,
      rows,
    });
  }

  const result: CleanJsonResult = { templateName: templateName ?? "" };
  if (info.length > 0) result.info = info;
  if (tables.length > 0) result.tables = tables;
  return result;
}
