#!/usr/bin/env node
// FRONTEND_STRUCTURE_5B_OCR_CORE_OPS_COMMON_MOVE
// Static check: confirm src/components/ocr/core/ops.ts was moved to
// src/common/utils/ocrCanvasOps.ts. ops body must be logic-identical (apart
// from the type import path) to the 5B backup. table.ts, export.ts and
// OcrCanvasPane.tsx must remain at their original locations, only their
// import paths may have changed. types.ts (5A) is still under common/types/.
//
// Read-only. No production code is modified.

import { readFileSync, existsSync, readdirSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, "..");

const NEW_OPS = resolve(ROOT, "src/common/utils/ocrCanvasOps.ts");
const OLD_OPS = resolve(ROOT, "src/components/ocr/core/ops.ts");

const TYPES = resolve(ROOT, "src/common/types/ocr.ts");
// NOTE: 5B originally pinned table.ts to src/components/ocr/core/table.ts.
// After 5C (OCR core table common move) table.ts is at
// src/common/utils/ocrTableRegion.ts. We resolve TABLE to whichever location
// currently exists so this 5B-era check stays valid across both states.
const TABLE_AT_CORE = resolve(ROOT, "src/components/ocr/core/table.ts");
const TABLE_AT_COMMON_UTILS = resolve(ROOT, "src/common/utils/ocrTableRegion.ts");
const TABLE = existsSync(TABLE_AT_CORE) ? TABLE_AT_CORE : TABLE_AT_COMMON_UTILS;
// NOTE: 5B originally pinned export.ts to src/components/ocr/core/export.ts.
// After 5D (Template export payload move) the file is at
// src/components/template/utils/buildTemplateExportPayload.ts. We resolve
// EXPORT to whichever location currently exists so this 5B-era check stays
// valid across both states.
const EXPORT_AT_CORE = resolve(ROOT, "src/components/ocr/core/export.ts");
const EXPORT_AT_TEMPLATE_UTILS = resolve(
  ROOT, "src/components/template/utils/buildTemplateExportPayload.ts",
);
const EXPORT = existsSync(EXPORT_AT_CORE) ? EXPORT_AT_CORE : EXPORT_AT_TEMPLATE_UTILS;
// NOTE: 5B originally pinned OcrCanvasPane to src/components/ocr/. After 5F
// (OcrCanvasPane common/ui move) it lives at src/common/ui/OcrCanvasPane.tsx.
// Resolve to whichever location currently exists so this 5B-era check stays
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
// NOTE: 5B originally pinned the right panel at .../OcrRightPanel.tsx. After
// 6A (Template right panel rename) the file lives at .../TemplateRightPanel.tsx
// with the default-export identifier renamed too. Resolve to whichever
// location currently exists, and below extend the logic-equivalence
// normalizer to collapse the rename.
const RIGHT_PANEL_AT_OCR_NAME = resolve(ROOT, "src/components/template/ui/OcrRightPanel.tsx");
const RIGHT_PANEL_AT_TEMPLATE_NAME = resolve(ROOT, "src/components/template/ui/TemplateRightPanel.tsx");
const RIGHT_PANEL = existsSync(RIGHT_PANEL_AT_OCR_NAME)
  ? RIGHT_PANEL_AT_OCR_NAME
  : RIGHT_PANEL_AT_TEMPLATE_NAME;

const TEST_WORKSPACE = resolve(ROOT, "src/components/test/TestWorkspace.tsx");
const TEST_CORE_DIR = resolve(ROOT, "src/components/test/core");

const BACKUP_DIR = resolve(
  ROOT,
  "backup",
  "ocr_core_ops_20260522_before_FRONTEND_STRUCTURE_5B_OCR_CORE_OPS_COMMON_MOVE",
);
const OPS_BACKUP = resolve(BACKUP_DIR, "ops.ts");
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
// Strip dynamic import() paths too (e.g. RunOcrWorkspace dynamic-imports
// OcrCanvasPane). Needed so 5F-style path changes don't break this 5B-era
// equivalence check.
function stripDynamicImportPaths(src) {
  return src.replace(/import\(\s*["'][^"']+["']\s*\)/g, 'import("<<IMPORT>>")');
}
// Collapse the 6A rename (OcrRightPanel <-> TemplateRightPanel) so this
// 5B-era logic-equivalence check survives the legitimate identifier rename.
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
checks.new_ops_exists = existsSync(NEW_OPS);
checks.old_ops_absent = !existsSync(OLD_OPS);

// 2) Protected siblings still at original paths.
checks.types_still_under_common_types = existsSync(TYPES);
checks.table_untouched_path = existsSync(TABLE);
checks.export_untouched_path = existsSync(EXPORT);
checks.OcrCanvasPane_untouched_path = existsSync(OCR_CANVAS);
checks.OcrAnnotator_untouched_path = existsSync(ANNOTATOR);
checks.OcrRightPanel_untouched_path = existsSync(RIGHT_PANEL);

// 3) TestWorkspace + test/core untouched paths.
checks.TestWorkspace_present = existsSync(TEST_WORKSPACE);
checks.test_core_dir_present = existsSync(TEST_CORE_DIR);

// 4) New common/utils/ocrCanvasOps.ts purity.
const newOpsSrc = readSafe(NEW_OPS);
checks.new_ops_no_components_import =
  newOpsSrc !== null && !/from\s+["'][^"']*components\/[^"']*["']/.test(newOpsSrc);
checks.new_ops_no_browser_api =
  newOpsSrc !== null &&
  !/\bwindow\b/.test(newOpsSrc) &&
  !/\bdocument\b/.test(newOpsSrc) &&
  !/\blocalStorage\b/.test(newOpsSrc);
// CSSProperties type-only react import is permitted; runtime react default
// import / hook import is not.
checks.new_ops_no_react_runtime_import =
  newOpsSrc !== null &&
  !/import\s+React/.test(newOpsSrc) &&
  !/from\s+["']react-dom["']/.test(newOpsSrc);
// types must come from sibling ../types/ocr (post-5A common location).
checks.new_ops_types_via_common_types =
  newOpsSrc !== null && /from\s+["']\.\.\/types\/ocr["']/.test(newOpsSrc);

// 5) Function exports preserved.
const REQUIRED_FN_NAMES = [
  "clamp",
  "normalizeRect",
  "uid",
  "parseIndex",
  "normalizeRatios",
  "boxLabelStyle",
  "calcMultiSubRegions",
  "clampRectToArea",
];
checks.new_ops_export_names_preserved =
  newOpsSrc !== null &&
  REQUIRED_FN_NAMES.every((n) => new RegExp(`export\\s+function\\s+${n}\\b`).test(newOpsSrc));

// 6) Logic equivalence vs backup (only import paths may change).
const opsBackup = readSafe(OPS_BACKUP);
if (opsBackup === null) {
  skippedBackupChecks.push({
    check: "new_ops_logic_unchanged_vs_backup",
    reason: `SKIP_WITH_REASON: backup not found: ${OPS_BACKUP}`,
  });
}
checks.new_ops_logic_unchanged_vs_backup =
  newOpsSrc !== null && opsBackup !== null &&
  normalizeImportInsensitive(newOpsSrc) === normalizeImportInsensitive(opsBackup);

// 7) Importers now reference common/utils/ocrCanvasOps and no longer "./ops"
//    or "../../ocr/core/ops".
const tableSrc = readSafe(TABLE);
const exportSrc = readSafe(EXPORT);
const canvasSrc = readSafe(OCR_CANVAS);
const rightPanelSrc = readSafe(RIGHT_PANEL);

// NOTE: depending on whether table.ts has been moved by 5C, the relative path
// to common/utils/ocrCanvasOps differs (3 levels up from
// src/components/ocr/core/ vs. `./ocrCanvasOps` sibling in src/common/utils/).
// Accept both.
checks.table_imports_common_utils =
  tableSrc !== null &&
  (/from\s+["']\.\.\/\.\.\/\.\.\/common\/utils\/ocrCanvasOps["']/.test(tableSrc) ||
    /from\s+["']\.\/ocrCanvasOps["']/.test(tableSrc)) &&
  !/from\s+["']\.\/ops["']/.test(tableSrc);
checks.export_imports_common_utils =
  exportSrc !== null &&
  /from\s+["']\.\.\/\.\.\/\.\.\/common\/utils\/ocrCanvasOps["']/.test(exportSrc) &&
  !/from\s+["']\.\/ops["']/.test(exportSrc);
// NOTE: depending on whether OcrCanvasPane has moved by 5F, the relative path
// to common/utils/ocrCanvasOps differs (2 levels up from src/components/ocr/
// vs. 1 level up from src/common/ui/). Accept both.
checks.canvas_imports_common_utils =
  canvasSrc !== null &&
  (/from\s+["']\.\.\/\.\.\/common\/utils\/ocrCanvasOps["']/.test(canvasSrc) ||
    /from\s+["']\.\.\/utils\/ocrCanvasOps["']/.test(canvasSrc)) &&
  !/from\s+["']\.\/core\/ops["']/.test(canvasSrc);
checks.right_panel_imports_common_utils =
  rightPanelSrc !== null &&
  /from\s+["']\.\.\/\.\.\/\.\.\/common\/utils\/ocrCanvasOps["']/.test(rightPanelSrc) &&
  !/from\s+["']\.\.\/\.\.\/ocr\/core\/ops["']/.test(rightPanelSrc);

// 8) Importer bodies are logic-equivalent to their 5B backups (only import
//    paths may have changed).
const tableBackup = readSafe(TABLE_BACKUP);
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
// TPL-12A phase-aware: ocrTableRegion.ts (the renamed table.ts) gained
// materializeTableRowsWithOverrides + MIN_ROW_HEIGHT beyond 5B's import-only
// scope. Skip the byte-equivalence guard when that marker is present.
const _tpl12aShipped_table_5b = typeof tableSrc === "string"
  && /materializeTableRowsWithOverrides/.test(tableSrc);
if (_tpl12aShipped_table_5b) {
  skippedBackupChecks.push({
    check: "table_logic_unchanged_vs_backup",
    reason: "SKIP_WITH_REASON: TPL-12A added materializeTableRowsWithOverrides beyond 5B scope",
  });
  checks.table_logic_unchanged_vs_backup = true;
} else {
  checks.table_logic_unchanged_vs_backup = compareBackup(
    "table_logic_unchanged_vs_backup", tableSrc, tableBackup, TABLE_BACKUP,
  );
}
// TPL-12B phase-aware: buildTemplateExportPayload imports & uses
// materializeTableRowsWithOverrides beyond 5B's import-only scope.
const _tpl12bShipped_export_5b = typeof exportSrc === "string"
  && /materializeTableRowsWithOverrides/.test(exportSrc);
if (_tpl12bShipped_export_5b) {
  skippedBackupChecks.push({
    check: "export_logic_unchanged_vs_backup",
    reason: "SKIP_WITH_REASON: TPL-12B wired materializeTableRowsWithOverrides into buildTemplateExportPayload beyond 5B scope",
  });
  checks.export_logic_unchanged_vs_backup = true;
} else {
  checks.export_logic_unchanged_vs_backup = compareBackup(
    "export_logic_unchanged_vs_backup", exportSrc, exportBackup, EXPORT_BACKUP,
  );
}
// TPL-12C phase-aware: OcrCanvasPane gained row boundary UI beyond 5B scope.
const _tpl12cShipped_canvas_5b = typeof canvasSrc === "string"
  && /rowAdjustTargetId/.test(canvasSrc);
if (_tpl12cShipped_canvas_5b) {
  skippedBackupChecks.push({
    check: "canvas_logic_unchanged_vs_backup",
    reason: "SKIP_WITH_REASON: TPL-12C added row-adjust UI to OcrCanvasPane beyond 5B scope",
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
const _tpl9bShipped_5b_panel = typeof rightPanelSrc === "string"
  && /CANONICAL_COLUMN_OPTIONS/.test(rightPanelSrc);
if (_tpl9bShipped_5b_panel) {
  skippedBackupChecks.push({
    check: "right_panel_logic_unchanged_vs_backup",
    reason: "SKIP_WITH_REASON: TPL-9B extended TemplateRightPanel beyond 5B scope (column-definition marker matched)",
  });
  checks.right_panel_logic_unchanged_vs_backup = true;
} else {
  checks.right_panel_logic_unchanged_vs_backup = compareBackup(
    "right_panel_logic_unchanged_vs_backup", rightPanelSrc, rightPanelBackup, RIGHT_PANEL_BACKUP,
  );
}

// 9) No residual "./core/ops" or "../core/ops" or "../../ocr/core/ops"
//    or "ocr/core/ops" strings anywhere in src/components/.
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
  /from\s+["']\.\/ops["']/,
  /from\s+["']\.\.\/ops["']/,
  /from\s+["'][^"']*ocr\/core\/ops["']/,
];
const residuals = [];
for (const f of srcFiles) {
  const s = readSafe(f);
  if (!s) continue;
  for (const re of RESIDUAL_PATTERNS) {
    if (re.test(s)) residuals.push({ file: f, pattern: re.toString() });
  }
}
checks.no_residual_ops_imports = residuals.length === 0;

const summary = {
  task: "FRONTEND-STRUCTURE-5B-OCR-CORE-OPS-COMMON-MOVE",
  paths: {
    new_ops: NEW_OPS,
    old_ops: OLD_OPS,
    types: TYPES,
    table: TABLE,
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
  "new_ops_exists",
  "old_ops_absent",
  "types_still_under_common_types",
  "table_untouched_path",
  "export_untouched_path",
  "OcrCanvasPane_untouched_path",
  "OcrAnnotator_untouched_path",
  "OcrRightPanel_untouched_path",
  "TestWorkspace_present",
  "test_core_dir_present",
  "new_ops_no_components_import",
  "new_ops_no_browser_api",
  "new_ops_no_react_runtime_import",
  "new_ops_types_via_common_types",
  "new_ops_export_names_preserved",
  "new_ops_logic_unchanged_vs_backup",
  "table_imports_common_utils",
  "export_imports_common_utils",
  "canvas_imports_common_utils",
  "right_panel_imports_common_utils",
  "table_logic_unchanged_vs_backup",
  "export_logic_unchanged_vs_backup",
  "canvas_logic_unchanged_vs_backup",
  "right_panel_logic_unchanged_vs_backup",
  "no_residual_ops_imports",
];
const allPass = required.every((k) => checks[k] === true);
const verdict = allPass
  ? (skippedBackupChecks.length > 0 ? "PASS_WITH_SKIPPED_BACKUP" : "PASS")
  : "FAIL";
console.log(`[OCR_CORE_OPS_COMMON_MOVE_5B] ${verdict}`);
process.exit(allPass ? 0 : 1);
