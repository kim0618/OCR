#!/usr/bin/env node
// FRONTEND_STRUCTURE_5C_OCR_CORE_TABLE_COMMON_MOVE
// Static check: confirm src/components/ocr/core/table.ts was moved to
// src/common/utils/ocrTableRegion.ts. Body must be logic-identical (apart
// from the self-import paths) to the 5C backup. export.ts and
// OcrCanvasPane.tsx must remain at their original locations, only their
// import paths may have changed. 5A (types under common/types) and 5B (ops
// under common/utils) are still intact.
//
// Read-only. No production code is modified.

import { readFileSync, existsSync, readdirSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, "..");

const NEW_TABLE = resolve(ROOT, "src/common/utils/ocrTableRegion.ts");
const OLD_TABLE = resolve(ROOT, "src/components/ocr/core/table.ts");

const TYPES = resolve(ROOT, "src/common/types/ocr.ts");
const OPS = resolve(ROOT, "src/common/utils/ocrCanvasOps.ts");
// NOTE: 5C originally pinned export.ts to src/components/ocr/core/export.ts.
// After 5D (Template export payload move) the file is at
// src/components/template/utils/buildTemplateExportPayload.ts. We resolve
// EXPORT to whichever location currently exists so this 5C-era check stays
// valid across both states.
const EXPORT_AT_CORE = resolve(ROOT, "src/components/ocr/core/export.ts");
const EXPORT_AT_TEMPLATE_UTILS = resolve(
  ROOT, "src/components/template/utils/buildTemplateExportPayload.ts",
);
const EXPORT = existsSync(EXPORT_AT_CORE) ? EXPORT_AT_CORE : EXPORT_AT_TEMPLATE_UTILS;
// NOTE: 5C originally pinned OcrCanvasPane to src/components/ocr/. After 5F
// (OcrCanvasPane common/ui move) it lives at src/common/ui/OcrCanvasPane.tsx.
// Resolve to whichever location currently exists so this 5C-era check stays
// valid across both states.
const OCR_CANVAS_AT_COMPONENTS = resolve(ROOT, "src/components/ocr/OcrCanvasPane.tsx");
const OCR_CANVAS_AT_COMMON_UI = resolve(ROOT, "src/common/ui/OcrCanvasPane.tsx");
const OCR_CANVAS = existsSync(OCR_CANVAS_AT_COMPONENTS)
  ? OCR_CANVAS_AT_COMPONENTS
  : OCR_CANVAS_AT_COMMON_UI;
// NOTE: After 6B (Template annotator rename) the annotator lives at
// .../TemplateAnnotator.tsx. Resolve to whichever currently exists.
const ANNOTATOR_AT_OCR_NAME = resolve(ROOT, "src/components/template/ui/OcrAnnotator.tsx");
const ANNOTATOR_AT_TEMPLATE_NAME = resolve(ROOT, "src/components/template/ui/TemplateAnnotator.tsx");
const ANNOTATOR = existsSync(ANNOTATOR_AT_OCR_NAME)
  ? ANNOTATOR_AT_OCR_NAME
  : ANNOTATOR_AT_TEMPLATE_NAME;
// NOTE: 5C originally pinned the right panel at .../OcrRightPanel.tsx. After
// 6A (Template right panel rename) the file lives at .../TemplateRightPanel.tsx
// with the default-export identifier renamed too. Resolve to whichever
// location currently exists; the logic-equivalence normalizer below also
// collapses the rename.
const RIGHT_PANEL_AT_OCR_NAME = resolve(ROOT, "src/components/template/ui/OcrRightPanel.tsx");
const RIGHT_PANEL_AT_TEMPLATE_NAME = resolve(ROOT, "src/components/template/ui/TemplateRightPanel.tsx");
const RIGHT_PANEL = existsSync(RIGHT_PANEL_AT_OCR_NAME)
  ? RIGHT_PANEL_AT_OCR_NAME
  : RIGHT_PANEL_AT_TEMPLATE_NAME;

const TEST_WORKSPACE = resolve(ROOT, "src/components/test/TestWorkspace.tsx");
const TEST_CORE_DIR = resolve(ROOT, "src/components/test/core");

const TEMPLATE_UTILS_DIR = resolve(ROOT, "src/components/template/utils");
const TEMPLATE_TABLE_COLUMN_EDITOR = resolve(
  ROOT, "src/components/template/ui/TemplateTableColumnEditor.tsx",
);

const BACKUP_DIR = resolve(
  ROOT,
  "backup",
  "ocr_core_table_20260522_before_FRONTEND_STRUCTURE_5C_OCR_CORE_TABLE_COMMON_MOVE",
);
const TABLE_BACKUP = resolve(BACKUP_DIR, "table.ts");
const EXPORT_BACKUP = resolve(BACKUP_DIR, "export.ts");
const CANVAS_BACKUP = resolve(BACKUP_DIR, "OcrCanvasPane.tsx");
const RIGHT_PANEL_BACKUP = resolve(BACKUP_DIR, "OcrRightPanel.tsx");

function readSafe(p) { try { return readFileSync(p, "utf8"); } catch { return null; } }
function stripComments(src) {
  return src
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .replace(/(^|[^:])\/\/[^\n]*/g, "$1");
}
function stripImportPaths(src) {
  return src.replace(/from\s+["'][^"']+["']/g, 'from "<<IMPORT>>"');
}
function stripDynamicImportPaths(src) {
  return src.replace(/import\(\s*["'][^"']+["']\s*\)/g, 'import("<<IMPORT>>")');
}
// Collapse the 6A rename (OcrRightPanel <-> TemplateRightPanel).
function stripRenamedRightPanelIdentifiers(src) {
  return src
    .replace(/\bOcrRightPanel\b/g, "<<RIGHT_PANEL>>")
    .replace(/\bTemplateRightPanel\b/g, "<<RIGHT_PANEL>>");
}
function normalizeImportInsensitive(src) {
  return stripRenamedRightPanelIdentifiers(
    stripDynamicImportPaths(stripImportPaths(stripComments(src))),
  )
    .replace(/\s+/g, " ")
    .trim();
}

const checks = {};
const skippedBackupChecks = [];

// 1) New path exists, old path absent.
checks.new_table_exists = existsSync(NEW_TABLE);
checks.old_table_absent = !existsSync(OLD_TABLE);

// 2) Protected siblings still at original / 5A / 5B locations.
checks.types_still_under_common_types = existsSync(TYPES);
checks.ops_still_under_common_utils = existsSync(OPS);
checks.export_untouched_path = existsSync(EXPORT);
checks.OcrCanvasPane_untouched_path = existsSync(OCR_CANVAS);
checks.OcrAnnotator_untouched_path = existsSync(ANNOTATOR);
checks.OcrRightPanel_untouched_path = existsSync(RIGHT_PANEL);

// 3) TestWorkspace + test/core untouched paths.
checks.TestWorkspace_present = existsSync(TEST_WORKSPACE);
checks.test_core_dir_present = existsSync(TEST_CORE_DIR);

// 4) New common/utils/ocrTableRegion.ts purity.
const newTableSrc = readSafe(NEW_TABLE);
checks.new_table_no_components_import =
  newTableSrc !== null && !/from\s+["'][^"']*components\/[^"']*["']/.test(newTableSrc);
checks.new_table_no_react_import =
  newTableSrc !== null && !/from\s+["']react["']/.test(newTableSrc);
checks.new_table_no_react_dom_import =
  newTableSrc !== null && !/from\s+["']react-dom["']/.test(newTableSrc);
checks.new_table_no_browser_api =
  newTableSrc !== null &&
  !/\bwindow\b/.test(newTableSrc) &&
  !/\bdocument\b/.test(newTableSrc) &&
  !/\blocalStorage\b/.test(newTableSrc);
// Imports must come from sibling ../types/ocr and ./ocrCanvasOps (or no other
// import beyond those — and certainly nothing under components/*).
checks.new_table_types_via_common_types =
  newTableSrc !== null && /from\s+["']\.\.\/types\/ocr["']/.test(newTableSrc);
checks.new_table_ops_via_common_utils =
  newTableSrc !== null && /from\s+["']\.\/ocrCanvasOps["']/.test(newTableSrc);

// 5) Function/type exports preserved.
const REQUIRED_NAMES = [
  "normalizeColGuides",
  "buildTableRows",
  "normalizeStopKeywords",
  "autoDetectRowBands",
  "isStopRow",
];
checks.new_table_export_names_preserved =
  newTableSrc !== null &&
  REQUIRED_NAMES.every((n) => new RegExp(`export\\s+function\\s+${n}\\b`).test(newTableSrc));
checks.new_table_OcrBox_type_preserved =
  newTableSrc !== null && /export\s+type\s+OcrBox\b/.test(newTableSrc);

// 6) Logic equivalence vs backup (only import paths may have changed).
const tableBackup = readSafe(TABLE_BACKUP);
if (tableBackup === null) {
  skippedBackupChecks.push({
    check: "new_table_logic_unchanged_vs_backup",
    reason: `SKIP_WITH_REASON: backup not found: ${TABLE_BACKUP}`,
  });
}
// TPL-12A phase-aware: ocrTableRegion.ts gained materializeTableRowsWithOverrides
// + MIN_ROW_HEIGHT beyond 5C's import-only scope. Skip when that marker is
// present.
const _tpl12aShipped_table_5c = typeof newTableSrc === "string"
  && /materializeTableRowsWithOverrides/.test(newTableSrc);
if (_tpl12aShipped_table_5c) {
  skippedBackupChecks.push({
    check: "new_table_logic_unchanged_vs_backup",
    reason: "SKIP_WITH_REASON: TPL-12A added materializeTableRowsWithOverrides beyond 5C scope",
  });
  checks.new_table_logic_unchanged_vs_backup = true;
} else {
  checks.new_table_logic_unchanged_vs_backup =
    newTableSrc !== null && tableBackup !== null &&
    normalizeImportInsensitive(newTableSrc) === normalizeImportInsensitive(tableBackup);
}

// 7) Importers now reference common/utils/ocrTableRegion and no longer
//    "./table" or "../../ocr/core/table" or "./core/table".
const exportSrc = readSafe(EXPORT);
const canvasSrc = readSafe(OCR_CANVAS);
const rightPanelSrc = readSafe(RIGHT_PANEL);

checks.export_imports_common_utils =
  exportSrc !== null &&
  /from\s+["']\.\.\/\.\.\/\.\.\/common\/utils\/ocrTableRegion["']/.test(exportSrc) &&
  !/from\s+["']\.\/table["']/.test(exportSrc);
// NOTE: depending on whether OcrCanvasPane has moved by 5F, the relative path
// to common/utils/ocrTableRegion differs (2 levels up from
// src/components/ocr/ vs. 1 level up from src/common/ui/). Accept both.
checks.canvas_imports_common_utils =
  canvasSrc !== null &&
  (/from\s+["']\.\.\/\.\.\/common\/utils\/ocrTableRegion["']/.test(canvasSrc) ||
    /from\s+["']\.\.\/utils\/ocrTableRegion["']/.test(canvasSrc)) &&
  !/from\s+["']\.\/core\/table["']/.test(canvasSrc);
checks.right_panel_imports_common_utils =
  rightPanelSrc !== null &&
  /from\s+["']\.\.\/\.\.\/\.\.\/common\/utils\/ocrTableRegion["']/.test(rightPanelSrc) &&
  !/from\s+["']\.\.\/\.\.\/ocr\/core\/table["']/.test(rightPanelSrc);

// 8) Importer bodies are logic-equivalent to their 5C backups (only import
//    paths may have changed).
const exportBackup = readSafe(EXPORT_BACKUP);
const canvasBackup = readSafe(CANVAS_BACKUP);
const rightPanelBackup = readSafe(RIGHT_PANEL_BACKUP);

function compareBackup(name, cur, backup, backupPath) {
  if (backup === null) {
    skippedBackupChecks.push({ check: name, reason: `SKIP_WITH_REASON: backup not found: ${backupPath}` });
    return cur !== null;
  }
  return cur !== null && backup !== null &&
    normalizeImportInsensitive(cur) === normalizeImportInsensitive(backup);
}
// TPL-12B phase-aware: buildTemplateExportPayload uses
// materializeTableRowsWithOverrides beyond 5C's import-only scope.
const _tpl12bShipped_export_5c = typeof exportSrc === "string"
  && /materializeTableRowsWithOverrides/.test(exportSrc);
if (_tpl12bShipped_export_5c) {
  skippedBackupChecks.push({
    check: "export_logic_unchanged_vs_backup",
    reason: "SKIP_WITH_REASON: TPL-12B wired materializeTableRowsWithOverrides into buildTemplateExportPayload beyond 5C scope",
  });
  checks.export_logic_unchanged_vs_backup = true;
} else {
  checks.export_logic_unchanged_vs_backup = compareBackup(
    "export_logic_unchanged_vs_backup", exportSrc, exportBackup, EXPORT_BACKUP,
  );
}
// TPL-12C phase-aware: OcrCanvasPane gained row boundary UI beyond 5C scope.
const _tpl12cShipped_canvas_5c = typeof canvasSrc === "string"
  && /rowAdjustTargetId/.test(canvasSrc);
if (_tpl12cShipped_canvas_5c) {
  skippedBackupChecks.push({
    check: "canvas_logic_unchanged_vs_backup",
    reason: "SKIP_WITH_REASON: TPL-12C added row-adjust UI to OcrCanvasPane beyond 5C scope",
  });
  checks.canvas_logic_unchanged_vs_backup = true;
} else {
  checks.canvas_logic_unchanged_vs_backup = compareBackup(
    "canvas_logic_unchanged_vs_backup", canvasSrc, canvasBackup, CANVAS_BACKUP,
  );
}
// TPL-9B phase-aware: TemplateRightPanel now mounts the column definition
// section. Skip the import-only backup-equivalence guard when that marker
// is present.
const _tpl9bShipped_5c_panel = typeof rightPanelSrc === "string"
  && /CANONICAL_COLUMN_OPTIONS/.test(rightPanelSrc);
if (_tpl9bShipped_5c_panel) {
  skippedBackupChecks.push({
    check: "right_panel_logic_unchanged_vs_backup",
    reason: "SKIP_WITH_REASON: TPL-9B extended TemplateRightPanel beyond 5C scope (column-definition marker matched)",
  });
  checks.right_panel_logic_unchanged_vs_backup = true;
} else {
  checks.right_panel_logic_unchanged_vs_backup = compareBackup(
    "right_panel_logic_unchanged_vs_backup", rightPanelSrc, rightPanelBackup, RIGHT_PANEL_BACKUP,
  );
}

// 9) No residual "./table" or "../table" or "ocr/core/table" strings in src/.
function walk(dir, acc = []) {
  try {
    for (const ent of readdirSync(dir, { withFileTypes: true })) {
      const p = resolve(dir, ent.name);
      if (ent.isDirectory()) walk(p, acc);
      else if (/\.(ts|tsx|mts|cts|js|jsx|mjs|cjs)$/.test(ent.name)) acc.push(p);
    }
  } catch {}
  return acc;
}
const srcFiles = walk(resolve(ROOT, "src"));
const RESIDUAL_PATTERNS = [
  /from\s+["']\.\/table["']/,
  /from\s+["']\.\.\/table["']/,
  /from\s+["'][^"']*ocr\/core\/table["']/,
];
const residuals = [];
for (const f of srcFiles) {
  const s = readSafe(f);
  if (!s) continue;
  for (const re of RESIDUAL_PATTERNS) {
    if (re.test(s)) residuals.push({ file: f, pattern: re.toString() });
  }
}
checks.no_residual_table_imports = residuals.length === 0;

// 10) Template table column definition policy must NOT be implemented in this
//     5C step. Confirm that no TemplateTableColumnEditor.tsx has been
//     introduced. The template/utils directory itself was legitimately
//     introduced by 5D (Template export payload move) to house the moved
//     buildTemplateExportPayload.ts; that is a move artefact, not new policy.
//     So we accept either: (a) template/utils does not exist (pre-5D state),
//     or (b) template/utils exists but contains ONLY the 5D-moved file.
checks.template_table_column_editor_not_introduced = !existsSync(TEMPLATE_TABLE_COLUMN_EDITOR);
function templateUtilsOnlyHas5DMove() {
  if (!existsSync(TEMPLATE_UTILS_DIR)) return true;
  try {
    const names = readdirSync(TEMPLATE_UTILS_DIR, { withFileTypes: true })
      .filter((e) => e.isFile())
      .map((e) => e.name)
      .sort();
    // TPL-3 adds unstructuredDefinition.ts (pure helper, no Template column
    // policy). Accept the explicit allow-list below.
    const ALLOWED = new Set([
      "buildTemplateExportPayload.ts",
      "unstructuredDefinition.ts",
    ]);
    return names.length === 0 || names.every((n) => ALLOWED.has(n));
  } catch {
    return true;
  }
}
checks.template_utils_dir_not_introduced = templateUtilsOnlyHas5DMove();
// Also confirm the moved table file does NOT contain any of the Template
// policy concepts (canonical column mapping / user confirmation state / save
// payload transformation) that the 5C precheck explicitly excluded.
const TEMPLATE_POLICY_BLOCKLIST = [
  /\bcanonicalColumn\b/,
  /\bmappingStatus\b/,
  /\buserConfirmed\b/,
  /\bsavePayload\b/,
  /\bbuildExportPayload\b/,
];
checks.new_table_has_no_template_policy =
  newTableSrc !== null && !TEMPLATE_POLICY_BLOCKLIST.some((re) => re.test(newTableSrc));

const summary = {
  task: "FRONTEND-STRUCTURE-5C-OCR-CORE-TABLE-COMMON-MOVE",
  paths: {
    new_table: NEW_TABLE,
    old_table: OLD_TABLE,
    types: TYPES,
    ops: OPS,
    export: EXPORT,
    canvas: OCR_CANVAS,
    annotator: ANNOTATOR,
    right_panel: RIGHT_PANEL,
  },
  checks,
  skippedBackupChecks,
  residuals,
};
console.log(JSON.stringify(summary, null, 2));

const required = [
  "new_table_exists",
  "old_table_absent",
  "types_still_under_common_types",
  "ops_still_under_common_utils",
  "export_untouched_path",
  "OcrCanvasPane_untouched_path",
  "OcrAnnotator_untouched_path",
  "OcrRightPanel_untouched_path",
  "TestWorkspace_present",
  "test_core_dir_present",
  "new_table_no_components_import",
  "new_table_no_react_import",
  "new_table_no_react_dom_import",
  "new_table_no_browser_api",
  "new_table_types_via_common_types",
  "new_table_ops_via_common_utils",
  "new_table_export_names_preserved",
  "new_table_OcrBox_type_preserved",
  "new_table_logic_unchanged_vs_backup",
  "export_imports_common_utils",
  "canvas_imports_common_utils",
  "right_panel_imports_common_utils",
  "export_logic_unchanged_vs_backup",
  "canvas_logic_unchanged_vs_backup",
  "right_panel_logic_unchanged_vs_backup",
  "no_residual_table_imports",
  "template_table_column_editor_not_introduced",
  "template_utils_dir_not_introduced",
  "new_table_has_no_template_policy",
];
const allPass = required.every((k) => checks[k] === true);
const verdict = allPass
  ? (skippedBackupChecks.length > 0 ? "PASS_WITH_SKIPPED_BACKUP" : "PASS")
  : "FAIL";
console.log(`[OCR_CORE_TABLE_COMMON_MOVE_5C] ${verdict}`);
process.exit(allPass ? 0 : 1);
