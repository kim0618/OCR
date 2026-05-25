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
} from "@/common/utils/ocrResultFormatters";
import {
  selectRepresentativeTableResultViewModels,
  type TableResultViewModel,
} from "@/common/utils/tableResultViewModel";

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
  /**
   * TPL-8F: optional unified TableResult view models. Only
   * `source === "unstructured_definition"` entries influence the output
   * (appended as a new "## 비정형 테이블" section after the main field
   * table). `backend_document_fields` is intentionally skipped because it
   * overlaps with the existing `docTableRows` summary row that is contract-
   * locked by Markdown v1 fixtures.
   */
  tableResultViewModels?: ReadonlyArray<TableResultViewModel>;
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

  // TPL-13B: representative table dedup.
  //   Up to TPL-10 we appended both `## 템플릿 테이블` and `## 비정형 테이블`
  //   sections — duplicating the same physical table when both projections
  //   were available. Now we emit ONE section based on the highest-priority
  //   representative source:
  //     template_region_canonical → ## 템플릿 테이블
  //     unstructured_definition   → ## 비정형 테이블
  //     backend_document_fields   → no extra section (the main field table
  //       above already covers it via the `표 데이터 (N행)` summary row that
  //       is contract-locked by Markdown v1)
  //   Backward compat: when `tableResultViewModels` is absent (Markdown v1
  //   fixture path) NO extra section is appended — identical to pre-TPL-8F.
  const repVMs = Array.isArray(input.tableResultViewModels)
    ? selectRepresentativeTableResultViewModels(input.tableResultViewModels)
    : [];
  const repSource = repVMs[0]?.source;
  const repHeading =
    repSource === "template_region_canonical" ? "## 템플릿 테이블"
    : repSource === "unstructured_definition" ? "## 비정형 테이블"
    : null;
  if (repHeading && repVMs.length > 0) {
    md += `\n${repHeading}\n`;
    for (const vm of repVMs) {
      const title = vm.labelKo || vm.labelEn || vm.tableKey;
      md += `\n### ${escapeCell(title)}\n\n`;
      if (vm.columns.length === 0) {
        md += `_정의된 컬럼이 없습니다._\n`;
        continue;
      }
      const headerLabels = vm.columns.map((c) =>
        escapeCell(c.labelKo || c.labelEn || c.columnKey),
      );
      md += `| ${headerLabels.join(" | ")} |\n`;
      md += `| ${vm.columns.map(() => "---").join(" | ")} |\n`;
      if (vm.rows.length === 0) {
        md += `\n_추출된 행이 없습니다._\n`;
        continue;
      }
      for (const row of vm.rows) {
        const cells = vm.columns.map((c) => {
          const cell = row.cells.find((x) => x.key === c.columnKey);
          return escapeCell(cell ? cell.displayValue : "-");
        });
        md += `| ${cells.join(" | ")} |\n`;
      }
    }
  }

  return md;
}
