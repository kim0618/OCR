/**
 * extractUnstructuredTableRows.ts (TPL-8B)
 *
 * Pure helper that projects backend `document_fields.tableRows` (canonical
 * invoice_statement rows produced by `ocr-server/extractors/invoice_statement.py`)
 * onto a user-defined unstructured template's `tables[].columns[].columnKey`.
 *
 * Algorithm (MVP — invoice_statement only):
 *   1. Only fire when `documentType === "invoice_statement"`.
 *   2. Only fire when `Array.isArray(raw.document_fields.tableRows)` and the
 *      first user table has a non-empty `columns` array.
 *   3. For the FIRST user table, map every backend row to a row keyed by
 *      `column.columnKey`; if the canonical key is missing on the backend
 *      row, that cell becomes "" (empty string).
 *   4. All other user tables (index >= 1) return `[]` — backend currently
 *      ships only the items-table, and multi-table extraction is out of
 *      scope for TPL-8B.
 *   5. Any failure to satisfy 1-4 returns `[]` for every user table (or
 *      `[]` overall when no user tables were declared).
 *
 * Boundary (TPL-8B):
 *   - Pure: no React, no DOM, no storage, no fetch, no backend.
 *   - Does NOT mutate `raw` (read-only on `document_fields.tableRows`).
 *   - Does NOT implement alias resolution / labelKo matching — that is
 *     deliberately deferred to a follow-up phase (TPL-8B-2).
 *   - Does NOT consume `raw.ocr_lines` / bbox / clustering — frontend has
 *     no bbox in the response (see TPL-8A precheck).
 */

export type ExtractUnstructuredTableRowsInputColumn = {
  columnKey?: string;
  labelKo?: string;
  labelEn?: string;
  [key: string]: unknown;
};

export type ExtractUnstructuredTableRowsInputTable = {
  tableKey?: string;
  labelKo?: string;
  labelEn?: string;
  columns?: ExtractUnstructuredTableRowsInputColumn[];
  [key: string]: unknown;
};

export type ExtractUnstructuredTableRowsInput = {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  raw: any;
  documentType?: string;
  tables?: ExtractUnstructuredTableRowsInputTable[];
};

/** Per-user-table rows. Outer index ↔ input.tables index. */
export type UnstructuredTableProjection = Array<Array<Record<string, string>>>;

const INVOICE_DOCUMENT_TYPE = "invoice_statement";

/**
 * Safely stringify a backend row cell value to a frontend-friendly string.
 *   - null / undefined            → ""
 *   - number / boolean / bigint   → String(value)
 *   - string                      → preserved as-is (no trimming —
 *                                    downstream consumers can normalize)
 *   - object / array              → "" (we deliberately avoid JSON.stringify
 *                                    so accidental nested tables don't leak
 *                                    encoded blobs into the projection)
 */
function stringifyCellValue(value: unknown): string {
  if (value === null || value === undefined) return "";
  const t = typeof value;
  if (t === "string") return value as string;
  if (t === "number" || t === "boolean" || t === "bigint") return String(value);
  return "";
}

function projectFirstTable(
  firstTable: ExtractUnstructuredTableRowsInputTable,
  backendRows: ReadonlyArray<Record<string, unknown>>,
): Array<Record<string, string>> {
  const cols = Array.isArray(firstTable.columns) ? firstTable.columns : [];
  if (cols.length === 0 || backendRows.length === 0) return [];
  const keys = cols
    .map((c) => (typeof c?.columnKey === "string" ? c.columnKey : ""))
    .filter((k) => k.length > 0);
  if (keys.length === 0) return [];
  return backendRows.map((row) => {
    const out: Record<string, string> = {};
    const source = row && typeof row === "object" && !Array.isArray(row)
      ? (row as Record<string, unknown>)
      : {};
    for (const key of keys) {
      out[key] = stringifyCellValue(source[key]);
    }
    return out;
  });
}

/**
 * Compute per-user-table row projections.
 *
 * Returns an array shaped like `[rowsForTable0, rowsForTable1, ...]`. The
 * outer index matches `input.tables` exactly. Tables with no projection
 * source get `[]`. If `input.tables` is missing/empty, returns `[]`.
 */
export function extractUnstructuredTableRows(
  input: ExtractUnstructuredTableRowsInput,
): UnstructuredTableProjection {
  const tables = Array.isArray(input?.tables) ? input.tables : [];
  if (tables.length === 0) return [];

  // Pre-fill every user table with [].
  const result: UnstructuredTableProjection = tables.map(() => []);

  // Gating: only invoice_statement currently has a backend canonical
  // tableRows source.
  const docType = typeof input?.documentType === "string"
    ? input.documentType.trim()
    : "";
  if (docType !== INVOICE_DOCUMENT_TYPE) return result;

  const docFields = (input?.raw && typeof input.raw === "object")
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    ? (input.raw as any).document_fields
    : null;
  const backendRowsRaw = docFields && typeof docFields === "object"
    ? (docFields as Record<string, unknown>).tableRows
    : null;
  if (!Array.isArray(backendRowsRaw)) return result;

  // Sanitize backend rows (drop non-object entries silently).
  const backendRows: Array<Record<string, unknown>> = [];
  for (const r of backendRowsRaw as unknown[]) {
    if (r && typeof r === "object" && !Array.isArray(r)) {
      backendRows.push(r as Record<string, unknown>);
    }
  }

  result[0] = projectFirstTable(tables[0], backendRows);
  return result;
}
