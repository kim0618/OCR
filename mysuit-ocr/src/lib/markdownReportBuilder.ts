/**
 * markdownReportBuilder.ts
 *
 * Pure helper that builds the Markdown v1 OCR report consumed by Preview
 * (markdown mode) and Copy / Export buttons in OcrResultPanel.
 * Extracted from OcrResultPanel.tsx by FRONTEND-CLEANUP-2B.
 *
 * Contract:  docs/MARKDOWN_V1_CONTRACT_20260521.md
 * Fixtures:  tmp/fixtures/markdown_v1/  (LF-strict, 6 cases)
 *
 * Purity:
 *  - No React hooks, no DOM, no storage, no closures over component state.
 *  - Output is fully determined by the input object.
 *  - Inputs are never mutated.
 *
 * Boundary:
 *  - Preview / Custom / Validation JSX must NOT import this file. They consume
 *    the shared formatters in ocrResultFormatters.ts. Only the markdown copy /
 *    export / preview-markdown-render code paths import buildMarkdownReport.
 *
 * Markdown v1 contract (unchanged in this extraction):
 *  - First line: "# OCR 결과"
 *  - "- 처리 시간: **N.NNs**" and "- 필드 수: **N건**" summary bullets
 *  - Markdown table: No / 필드명 / 값 / 신뢰도 / 채택
 *  - One row per field, in `fields` order
 *  - field_type === "table" rows render only "표 데이터 (N행)" summary,
 *    where N comes from docTableRows.length if available, else from the
 *    legacy parseTableField rowLabel
 *  - Pipe and newline in label/value are escaped via `esc()`
 *  - Line endings are "\n" only (matches LF fixture policy)
 */

import {
  fieldLabelFull,
  getAdoptionLabel,
  parseTableField,
  type OcrFormatterField,
} from "@/lib/ocrResultFormatters";

// ── Input shape ───────────────────────────────────────────────────────────────

export type MarkdownReportField = OcrFormatterField & {
  field_type: string;
  value: string;
  confidence: number;
};

export type BuildMarkdownReportInput = {
  fields: ReadonlyArray<MarkdownReportField>;
  processingTime: number;
  docTableRows?: Record<string, unknown>[] | null;
};

// ── Internal escaping ─────────────────────────────────────────────────────────

const escapeCell = (s: string) => s.replace(/\|/g, "\\|").replace(/\n/g, " ");

// ── Public builder ────────────────────────────────────────────────────────────

export function buildMarkdownReport(input: BuildMarkdownReportInput): string {
  const { fields, processingTime, docTableRows } = input;

  let md = `# OCR 결과\n\n`;
  md += `- 처리 시간: **${processingTime.toFixed(2)}s**\n`;
  md += `- 필드 수: **${fields.length}건**\n\n`;
  md += `| No | 필드명 | 값 | 신뢰도 | 채택 |\n`;
  md += `|:---:|--------|-----|:------:|:---:|\n`;

  fields.forEach((f, i) => {
    const label = fieldLabelFull(f);
    if (f.field_type === "table") {
      const { rowLabel: rawRowLabel } = parseTableField(f.value);
      const rowLabel = docTableRows ? `${docTableRows.length}행` : rawRowLabel;
      md += `| ${i + 1} | ${escapeCell(label)} | 표 데이터 (${rowLabel}) | ${(f.confidence * 100).toFixed(1)}% | ${getAdoptionLabel(f)} |\n`;
    } else {
      md += `| ${i + 1} | ${escapeCell(label)} | ${escapeCell(f.value)} | ${(f.confidence * 100).toFixed(1)}% | ${getAdoptionLabel(f)} |\n`;
    }
  });

  return md;
}
