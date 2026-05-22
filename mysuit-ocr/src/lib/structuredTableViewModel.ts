/**
 * structuredTableViewModel.ts
 *
 * Pure helper that builds a UI-agnostic view model for the structured
 * invoice_statement table consumed by OcrResultPanel's Preview / Custom /
 * Validation tabs. Extracted by FRONTEND-CLEANUP-3D-2.
 *
 * Contract / fixtures:
 *  - docs/FRONTEND_CLEANUP_3D0_TABLE_VIEW_MODEL_CONTRACT_PRECHECK_20260521.md
 *  - docs/FRONTEND_CLEANUP_3D0_2_TABLE_VIEW_MODEL_CONTRACT_TRIM_PRECHECK_20260521.md
 *  - tmp/fixtures/table_view_model_v1/  (8 cases incl. synthetic_empty_rows)
 *
 * Cell normalization rule (matches the Python re-implementation used to
 * capture fixtures — see tmp/codex_table_view_model_fixture_lock.py
 * `normalize_cell`):
 *   - null / undefined            -> ""
 *   - Unicode dashes (U+2010..U+2014, U+2212) -> "-"
 *   - leading / trailing whitespace -> trimmed
 *   - everything else preserved as-is
 *
 * Per-cell output rule:
 *   - value        = normalized string
 *   - isEmpty      = value === ""
 *   - displayValue = isEmpty ? emptyValue : value
 *
 * Purity:
 *  - No React hooks, no DOM, no storage, no closures over component state.
 *  - Output is fully determined by the input object.
 *  - Inputs are never mutated.
 *
 * Forbidden in v1 output (intentionally excluded; see contract trim precheck):
 *  - align, width, style, isNumeric, isIndex (Preview-only rendering policy)
 *  - sourceRow, indices, rowIndex metadata (derivable from array position)
 *  - cells.label (duplicate of columns.label)
 *  - meta.hasEmptyCells (derivable from cells)
 *  - React nodes, JSX, event handlers, customTableEdits, validation/adoption/confidence UI
 *
 * Scope:
 *  - Structured table only (docTableRows + docTableDisplayCols).
 *  - Legacy parseTableField(field.value) fallback is NOT covered here.
 *    Future: buildLegacyTableViewModel as a separate helper if needed.
 *
 * LOCKED behavior preserved by virtue of pure data pass-through:
 *  - 거래_3 insuranceCode/amount columns appear in displayCols => appear in output.
 *  - rowIndex column inclusion is decided by the caller (via displayCols);
 *    this helper does not add or strip rowIndex.
 */

export type StructuredTableInputCol = {
  key: string;
  labelKo: string;
};

export type StructuredTableViewModelCell = {
  key: string;
  value: string;
  displayValue: string;
  isEmpty: boolean;
};

export type StructuredTableViewModelRow = {
  cells: StructuredTableViewModelCell[];
};

export type StructuredTableViewModelColumn = {
  key: string;
  label: string;
};

export type StructuredTableViewModelMeta = {
  rowCount: number;
  columnCount: number;
  hasRows: boolean;
  hasColumns: boolean;
};

export type StructuredTableViewModel = {
  columns: StructuredTableViewModelColumn[];
  rows: StructuredTableViewModelRow[];
  meta: StructuredTableViewModelMeta;
};

export type BuildStructuredTableViewModelInput = {
  rows: ReadonlyArray<Record<string, unknown>>;
  displayCols: ReadonlyArray<StructuredTableInputCol>;
  emptyValue?: string;
};

const DEFAULT_EMPTY_VALUE = "-";

// Unicode dash variants normalized to ASCII "-".
// U+2010 hyphen, U+2011 non-breaking hyphen, U+2012 figure dash,
// U+2013 en dash, U+2014 em dash, U+2212 minus sign.
const UNICODE_DASH_PATTERN = /[‐‑‒–—−]/g;

function normalizeStructuredTableCell(value: unknown): string {
  if (value === null || value === undefined) return "";
  return String(value).replace(UNICODE_DASH_PATTERN, "-").trim();
}

/**
 * Build the structured-table view model.
 *
 * Caller responsibilities:
 *  - Resolve `rows` from `result.document_fields.tableRows`.
 *  - Resolve `displayCols` from `buildInvoicePreviewCols(tableMeta, rows)`.
 *  - Decide whether to render the result (this helper does not check).
 *
 * Pure: same input always yields same output, no side effects, no mutation.
 */
export function buildStructuredTableViewModel(
  input: BuildStructuredTableViewModelInput,
): StructuredTableViewModel {
  const { rows, displayCols, emptyValue = DEFAULT_EMPTY_VALUE } = input;

  const columns: StructuredTableViewModelColumn[] = displayCols.map((col) => ({
    key: col.key,
    label: col.labelKo || col.key,
  }));

  const outputRows: StructuredTableViewModelRow[] = rows.map((row) => ({
    cells: displayCols.map((col) => {
      const value = normalizeStructuredTableCell(row[col.key]);
      const isEmpty = value === "";
      const displayValue = isEmpty ? emptyValue : value;
      return { key: col.key, value, displayValue, isEmpty };
    }),
  }));

  return {
    columns,
    rows: outputRows,
    meta: {
      rowCount: outputRows.length,
      columnCount: columns.length,
      hasRows: outputRows.length > 0,
      hasColumns: columns.length > 0,
    },
  };
}
