/**
 * ocrResultFormatters.ts
 *
 * Shared pure formatters used by OcrResultPanel's Preview / Custom / Validation
 * tabs and by the Markdown / Clean JSON helpers.
 *
 * Extracted from OcrResultPanel.tsx by FRONTEND-CLEANUP-2B.
 *
 * Purity:
 *  - No React hooks, no DOM, no storage, no closures over component state.
 *  - Output is fully determined by the input arguments.
 *  - Inputs are never mutated.
 *
 * These formatters were originally defined inline in OcrResultPanel.tsx and
 * called from Preview / Custom / Validation JSX, autofill detail rows, and
 * toMarkdown. They are moved here so that markdownReportBuilder.ts can depend
 * on them without forcing Preview / Custom / Validation JSX to import the
 * markdown builder.
 */

import type { AutofillAction, OutputValueSource } from "./autofillEngine";
import { resolveFieldLabel } from "@/common/utils/invoiceFieldLabels";

// ── Input shape ───────────────────────────────────────────────────────────────

/**
 * Minimum field shape these formatters read. Callers may pass wider field
 * objects (e.g. OcrFieldResult) — only these properties are consulted.
 */
export type OcrFormatterField = {
  name: string;
  ko?: string;
  en?: string;
  value?: string | null;
  source?: OutputValueSource;
  autofillAction?: AutofillAction;
};

// ── Label formatters ──────────────────────────────────────────────────────────

export function fieldLabel(field: OcrFormatterField): string {
  const { primary } = resolveFieldLabel({ name: field.name, ko: field.ko, en: field.en });
  return primary;
}

export function fieldLabelFull(field: OcrFormatterField): string {
  const { primary, secondary } = resolveFieldLabel({ name: field.name, ko: field.ko, en: field.en });
  if (secondary && secondary !== primary) return `${primary} (${secondary})`;
  return primary;
}

// ── Amount-like classification (used by autofill detail rendering) ────────────

const AMOUNT_LIKE_TOKENS = [
  "총합계금액",
  "합계금액",
  "총액",
  "totalamount",
  "amount",
  "판매금액",
  "부가세",
  "공급가액",
];

export function isAmountLikeField(field: OcrFormatterField): boolean {
  const label = fieldLabel(field).replace(/\s+/g, "").toLowerCase();
  return AMOUNT_LIKE_TOKENS.some((key) => label.includes(key.toLowerCase()));
}

// ── Adoption label (OCR / 복원 / 직접입력 / -) ────────────────────────────────

export type OcrAdoptionLabel = "OCR" | "복원" | "직접입력" | "-";

export function getAdoptionLabel(field: OcrFormatterField): OcrAdoptionLabel {
  if (field.autofillAction === "confirmed") return "OCR";
  if (field.autofillAction === "corrected") return "복원";
  if (field.autofillAction === "filled") return "복원";
  if (field.source === "text") return "직접입력";
  if (field.source === "biz" || field.source === "gt") return "복원";
  if (field.value && String(field.value).trim()) return "OCR";
  return "-";
}

// ── Table field value parser ──────────────────────────────────────────────────

export type TableCell = { value: string; confidence: number };

export type ParsedTableField = {
  rows: TableCell[][];
  nonEmpty: TableCell[][];
  displayRows: TableCell[][];
  isSingleCol: boolean;
  rowLabel: string;
};

/**
 * Parse a serialized table field value and compute display orientation.
 *
 * Rules (preserved from original OcrResultPanel.parseTableField):
 *  - All rows have uniform N > 1 columns  → real multi-row table, keep as-is.
 *  - Otherwise (single-col rows, or jagged/mixed column counts) → flatten all
 *    cells into one display row (transposed representation).
 */
export function parseTableField(value: string): ParsedTableField {
  let rows: TableCell[][] = [];
  try { rows = JSON.parse(value); } catch { /* ignore */ }
  const nonEmpty = rows.filter((r) => r.length > 0);
  const colCounts = nonEmpty.map((r) => r.length);
  const uniqueCounts = new Set(colCounts);
  const firstCount = nonEmpty[0]?.length ?? 0;
  const keepAsIs = uniqueCounts.size === 1 && firstCount > 1;
  const displayRows = keepAsIs
    ? rows
    : [nonEmpty.flatMap((r) => r)];
  const actualRows = keepAsIs ? nonEmpty.length : 1;
  const rowLabel = actualRows === 1
    ? `${nonEmpty.flatMap((r) => r).length}항목, 1행`
    : `${actualRows}행`;
  return { rows, nonEmpty, displayRows, isSingleCol: !keepAsIs, rowLabel };
}
