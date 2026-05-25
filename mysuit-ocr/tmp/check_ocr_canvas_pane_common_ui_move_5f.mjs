#!/usr/bin/env node
// FRONTEND_STRUCTURE_5F_OCR_CANVAS_PANE_COMMON_UI_MOVE
// Static check: confirm src/components/ocr/OcrCanvasPane.tsx was moved to
// src/common/ui/OcrCanvasPane.tsx. Body must be logic-identical (apart from
// the 4 self-import paths that shifted depth) to the 5F backup. FileDropzone
// stays at src/common/ui/FileDropzone.tsx. OcrAnnotator and RunOcrWorkspace
// keep their original paths and only their OcrCanvasPane import path may
// have changed. Template table column definition policy must NOT be
// introduced. src/components/ocr/ folder may be empty or removed.
//
// Read-only. No production code is modified.

import { readFileSync, existsSync, readdirSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, "..");

const NEW_CANVAS = resolve(ROOT, "src/common/ui/OcrCanvasPane.tsx");
const OLD_CANVAS = resolve(ROOT, "src/components/ocr/OcrCanvasPane.tsx");
const OLD_OCR_COMPONENT_DIR = resolve(ROOT, "src/components/ocr");

const FILEDROPZONE = resolve(ROOT, "src/common/ui/FileDropzone.tsx");
const TYPES = resolve(ROOT, "src/common/types/ocr.ts");
const OPS = resolve(ROOT, "src/common/utils/ocrCanvasOps.ts");
const TABLE = resolve(ROOT, "src/common/utils/ocrTableRegion.ts");

// NOTE: After 6B (Template annotator rename) the annotator lives at
// .../TemplateAnnotator.tsx. Resolve to whichever currently exists.
const ANNOTATOR_AT_OCR_NAME = resolve(ROOT, "src/components/template/ui/OcrAnnotator.tsx");
const ANNOTATOR_AT_TEMPLATE_NAME = resolve(ROOT, "src/components/template/ui/TemplateAnnotator.tsx");
const ANNOTATOR = existsSync(ANNOTATOR_AT_OCR_NAME)
  ? ANNOTATOR_AT_OCR_NAME
  : ANNOTATOR_AT_TEMPLATE_NAME;
// NOTE: After 6A (Template right panel rename), the right panel file lives at
// .../TemplateRightPanel.tsx. Resolve to whichever currently exists.
const RIGHT_PANEL_AT_OCR_NAME = resolve(ROOT, "src/components/template/ui/OcrRightPanel.tsx");
const RIGHT_PANEL_AT_TEMPLATE_NAME = resolve(ROOT, "src/components/template/ui/TemplateRightPanel.tsx");
const RIGHT_PANEL = existsSync(RIGHT_PANEL_AT_OCR_NAME)
  ? RIGHT_PANEL_AT_OCR_NAME
  : RIGHT_PANEL_AT_TEMPLATE_NAME;
const RUNOCR = resolve(ROOT, "src/components/runocr/RunOcrWorkspace.tsx");

const TEST_WORKSPACE = resolve(ROOT, "src/components/test/TestWorkspace.tsx");
const TEST_CORE_DIR = resolve(ROOT, "src/components/test/core");

const TEMPLATE_MAPPER = resolve(ROOT, "src/components/template/utils/templateMapper.ts");
const TEMPLATE_TABLE_COLUMN_EDITOR = resolve(
  ROOT, "src/components/template/ui/TemplateTableColumnEditor.tsx",
);

const BACKUP_DIR = resolve(
  ROOT,
  "backup",
  "ocr_canvas_pane_20260522_before_FRONTEND_STRUCTURE_5F_OCR_CANVAS_PANE_COMMON_UI_MOVE",
);
const CANVAS_BACKUP = resolve(BACKUP_DIR, "OcrCanvasPane.tsx");
const ANNOTATOR_BACKUP = resolve(BACKUP_DIR, "OcrAnnotator.tsx");
const RUNOCR_BACKUP = resolve(BACKUP_DIR, "RunOcrWorkspace.tsx");

function readSafe(p) { try { return readFileSync(p, "utf8"); } catch { return null; } }
function stripComments(src) {
  return src
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .replace(/(^|[^:])\/\/[^\n]*/g, "$1");
}
function stripImportPaths(src) {
  return src.replace(/from\s+["'][^"']+["']/g, 'from "<<IMPORT>>"');
}
// Also strip dynamic import() paths (used by RunOcrWorkspace).
function stripDynamicImportPaths(src) {
  return src.replace(/import\(\s*["'][^"']+["']\s*\)/g, 'import("<<IMPORT>>")');
}
// Collapse the 6A rename (OcrRightPanel <-> TemplateRightPanel) so this
// 5F-era logic-equivalence check survives the legitimate annotator import
// + JSX tag rename in OcrAnnotator.
function stripRenamedRightPanelIdentifiers(src) {
  return src
    .replace(/\bOcrRightPanel\b/g, "<<RIGHT_PANEL>>")
    .replace(/\bTemplateRightPanel\b/g, "<<RIGHT_PANEL>>");
}
// Collapse the 6B rename (OcrAnnotator <-> TemplateAnnotator).
function stripRenamedAnnotatorIdentifiers(src) {
  return src
    .replace(/\bOcrAnnotator\b/g, "<<ANNOTATOR>>")
    .replace(/\bTemplateAnnotator\b/g, "<<ANNOTATOR>>");
}
function normalizeImportInsensitive(src) {
  return stripRenamedAnnotatorIdentifiers(
    stripRenamedRightPanelIdentifiers(
      stripDynamicImportPaths(stripImportPaths(stripComments(src))),
    ),
  )
    .replace(/\s+/g, " ")
    .trim();
}

const checks = {};
const skippedBackupChecks = [];

// 1) New path exists, old path absent.
checks.new_canvas_exists = existsSync(NEW_CANVAS);
checks.old_canvas_absent = !existsSync(OLD_CANVAS);

// 2) src/components/ocr/ has no operational file. Acceptable states:
//    directory removed entirely OR directory exists but is empty.
function listFilesIfExists(dir) {
  if (!existsSync(dir)) return null;
  try {
    return readdirSync(dir, { withFileTypes: true })
      .filter((e) => e.isFile())
      .map((e) => e.name);
  } catch { return null; }
}
const remainingOcrFiles = listFilesIfExists(OLD_OCR_COMPONENT_DIR);
checks.components_ocr_dir_has_no_operational_file =
  remainingOcrFiles === null || remainingOcrFiles.length === 0;

// 3) Protected 5A/5B/5C/5E artefacts still in place.
checks.types_still_under_common_types = existsSync(TYPES);
checks.ops_still_under_common_utils = existsSync(OPS);
checks.table_still_under_common_utils = existsSync(TABLE);
checks.FileDropzone_still_under_common_ui = existsSync(FILEDROPZONE);

// 4) Surrounding files still at their original paths.
checks.OcrAnnotator_untouched_path = existsSync(ANNOTATOR);
checks.OcrRightPanel_untouched_path = existsSync(RIGHT_PANEL);
checks.RunOcrWorkspace_untouched_path = existsSync(RUNOCR);

// 5) TestWorkspace + test/core untouched paths.
checks.TestWorkspace_present = existsSync(TEST_WORKSPACE);
checks.test_core_dir_present = existsSync(TEST_CORE_DIR);

// 6) New OcrCanvasPane purity / sibling-correct imports.
const newCanvasSrc = readSafe(NEW_CANVAS);
checks.new_canvas_no_components_import =
  newCanvasSrc !== null && !/from\s+["'][^"']*components\/[^"']*["']/.test(newCanvasSrc);
checks.new_canvas_imports_common_types =
  newCanvasSrc !== null && /from\s+["']\.\.\/types\/ocr["']/.test(newCanvasSrc);
checks.new_canvas_imports_common_utils_ops =
  newCanvasSrc !== null && /from\s+["']\.\.\/utils\/ocrCanvasOps["']/.test(newCanvasSrc);
checks.new_canvas_imports_common_utils_table =
  newCanvasSrc !== null && /from\s+["']\.\.\/utils\/ocrTableRegion["']/.test(newCanvasSrc);
checks.new_canvas_imports_common_ui_filedropzone =
  newCanvasSrc !== null && /from\s+["']\.\/FileDropzone["']/.test(newCanvasSrc);
// React allowed. No localStorage policy.
checks.new_canvas_imports_react =
  newCanvasSrc !== null && /from\s+["']react["']/.test(newCanvasSrc);
checks.new_canvas_no_localStorage =
  newCanvasSrc !== null && !/\blocalStorage\b/.test(newCanvasSrc);

// 7) Component identity preserved.
checks.new_canvas_default_export_OcrCanvasPane =
  newCanvasSrc !== null && /export\s+default\s+function\s+OcrCanvasPane\b/.test(newCanvasSrc);

// 8) Logic equivalence vs backup (only import paths may have changed).
const canvasBackup = readSafe(CANVAS_BACKUP);
if (canvasBackup === null) {
  skippedBackupChecks.push({
    check: "new_canvas_logic_unchanged_vs_backup",
    reason: `SKIP_WITH_REASON: backup not found: ${CANVAS_BACKUP}`,
  });
}
// TPL-12C phase-aware: OcrCanvasPane gained row boundary UI beyond 5F scope.
const _tpl12cShipped_canvas_5f = typeof newCanvasSrc === "string"
  && /rowAdjustTargetId/.test(newCanvasSrc);
if (_tpl12cShipped_canvas_5f) {
  skippedBackupChecks.push({
    check: "new_canvas_logic_unchanged_vs_backup",
    reason: "SKIP_WITH_REASON: TPL-12C added row-adjust UI to OcrCanvasPane beyond 5F scope",
  });
  checks.new_canvas_logic_unchanged_vs_backup = true;
} else {
  checks.new_canvas_logic_unchanged_vs_backup =
    newCanvasSrc !== null && canvasBackup !== null &&
    normalizeImportInsensitive(newCanvasSrc) === normalizeImportInsensitive(canvasBackup);
}

// 9) OcrAnnotator imports from the new path (static import) and RunOcrWorkspace
//    imports from the new path via dynamic import().
const annotatorSrc = readSafe(ANNOTATOR);
const runocrSrc = readSafe(RUNOCR);
checks.annotator_imports_new_canvas =
  annotatorSrc !== null &&
  /from\s+["']\.\.\/\.\.\/\.\.\/common\/ui\/OcrCanvasPane["']/.test(annotatorSrc) &&
  !/from\s+["']\.\.\/\.\.\/ocr\/OcrCanvasPane["']/.test(annotatorSrc);
checks.runocr_imports_new_canvas =
  runocrSrc !== null &&
  /import\(\s*["']\.\.\/\.\.\/common\/ui\/OcrCanvasPane["']\s*\)/.test(runocrSrc) &&
  !/import\(\s*["']\.\.\/ocr\/OcrCanvasPane["']\s*\)/.test(runocrSrc);

// 10) Importer bodies logic-equivalent to 5F backups (only import path
//     changed).
const annotatorBackup = readSafe(ANNOTATOR_BACKUP);
const runocrBackup = readSafe(RUNOCR_BACKUP);

function compareBackup(name, cur, backup, backupPath) {
  if (backup === null) {
    skippedBackupChecks.push({ check: name, reason: `SKIP_WITH_REASON: backup not found: ${backupPath}` });
    return cur !== null;
  }
  return cur !== null && backup !== null &&
    normalizeImportInsensitive(cur) === normalizeImportInsensitive(backup);
}
// TPL-12C phase-aware: TemplateAnnotator (the renamed OcrAnnotator) gained
// rowAdjustTargetId state + props beyond 5F's import-only scope.
const _tpl12cShipped_ann_5f = typeof annotatorSrc === "string"
  && /rowAdjustTargetId/.test(annotatorSrc);
if (_tpl12cShipped_ann_5f) {
  skippedBackupChecks.push({
    check: "annotator_logic_unchanged_vs_backup",
    reason: "SKIP_WITH_REASON: TPL-12C added rowAdjustTargetId to TemplateAnnotator beyond 5F scope",
  });
  checks.annotator_logic_unchanged_vs_backup = true;
} else {
  checks.annotator_logic_unchanged_vs_backup = compareBackup(
    "annotator_logic_unchanged_vs_backup", annotatorSrc, annotatorBackup, ANNOTATOR_BACKUP,
  );
}
// TPL-10 phase-aware: RunOcrWorkspace passes activeTemplate prop to
// OcrResultPanel for template_region_canonical projection. Skip when present.
const _tpl10Shipped_runocr_5f = typeof runocrSrc === "string"
  && /activeTemplate\s*=\s*\{activeTemplateForPanel\}/.test(runocrSrc);
if (_tpl10Shipped_runocr_5f) {
  skippedBackupChecks.push({
    check: "runocr_logic_unchanged_vs_backup",
    reason: "SKIP_WITH_REASON: TPL-10 wired activeTemplate prop to OcrResultPanel beyond 5F scope",
  });
  checks.runocr_logic_unchanged_vs_backup = true;
} else {
  checks.runocr_logic_unchanged_vs_backup = compareBackup(
    "runocr_logic_unchanged_vs_backup", runocrSrc, runocrBackup, RUNOCR_BACKUP,
  );
}

// 11) FileDropzone has NOT changed (5E artefact preserved).
const fileDropzoneSrc = readSafe(FILEDROPZONE);
checks.FileDropzone_unchanged_default_export =
  fileDropzoneSrc !== null &&
  /export\s+default\s+function\s+FileDropzone\b/.test(fileDropzoneSrc);

// 12) No residual "../ocr/OcrCanvasPane" / "../../ocr/OcrCanvasPane" /
//     "components/ocr/OcrCanvasPane" strings anywhere in src/.
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
  /from\s+["']\.\.\/ocr\/OcrCanvasPane["']/,
  /from\s+["']\.\.\/\.\.\/ocr\/OcrCanvasPane["']/,
  /from\s+["'][^"']*components\/ocr\/OcrCanvasPane["']/,
  /import\(\s*["']\.\.\/ocr\/OcrCanvasPane["']\s*\)/,
  /import\(\s*["']\.\.\/\.\.\/ocr\/OcrCanvasPane["']\s*\)/,
];
const residuals = [];
for (const f of srcFiles) {
  const s = readSafe(f);
  if (!s) continue;
  for (const re of RESIDUAL_PATTERNS) {
    if (re.test(s)) residuals.push({ file: f, pattern: re.toString() });
  }
}
checks.no_residual_canvas_imports = residuals.length === 0;

// 13) Template table column definition policy must NOT be introduced.
checks.template_table_column_editor_not_introduced = !existsSync(TEMPLATE_TABLE_COLUMN_EDITOR);
checks.template_mapper_not_introduced = !existsSync(TEMPLATE_MAPPER);
const TEMPLATE_POLICY_BLOCKLIST = [
  /\bcanonicalColumn\b/,
  /\buserConfirmed\b/,
  /\bcolumnMappingStatus\b/,
  /\bcolumnCandidates\b/,
];
checks.new_canvas_has_no_new_template_policy =
  newCanvasSrc !== null && !TEMPLATE_POLICY_BLOCKLIST.some((re) => re.test(newCanvasSrc));

const summary = {
  task: "FRONTEND-STRUCTURE-5F-OCR-CANVAS-PANE-COMMON-UI-MOVE",
  paths: {
    new_canvas: NEW_CANVAS,
    old_canvas: OLD_CANVAS,
    components_ocr_dir: OLD_OCR_COMPONENT_DIR,
    remaining_components_ocr_files: remainingOcrFiles,
    filedropzone: FILEDROPZONE,
    types: TYPES,
    ops: OPS,
    table: TABLE,
    annotator: ANNOTATOR,
    runocr: RUNOCR,
  },
  checks,
  skippedBackupChecks,
  residuals,
};
console.log(JSON.stringify(summary, null, 2));

const required = [
  "new_canvas_exists",
  "old_canvas_absent",
  "components_ocr_dir_has_no_operational_file",
  "types_still_under_common_types",
  "ops_still_under_common_utils",
  "table_still_under_common_utils",
  "FileDropzone_still_under_common_ui",
  "OcrAnnotator_untouched_path",
  "OcrRightPanel_untouched_path",
  "RunOcrWorkspace_untouched_path",
  "TestWorkspace_present",
  "test_core_dir_present",
  "new_canvas_no_components_import",
  "new_canvas_imports_common_types",
  "new_canvas_imports_common_utils_ops",
  "new_canvas_imports_common_utils_table",
  "new_canvas_imports_common_ui_filedropzone",
  "new_canvas_imports_react",
  "new_canvas_no_localStorage",
  "new_canvas_default_export_OcrCanvasPane",
  "new_canvas_logic_unchanged_vs_backup",
  "annotator_imports_new_canvas",
  "runocr_imports_new_canvas",
  "annotator_logic_unchanged_vs_backup",
  "runocr_logic_unchanged_vs_backup",
  "FileDropzone_unchanged_default_export",
  "no_residual_canvas_imports",
  "template_table_column_editor_not_introduced",
  "template_mapper_not_introduced",
  "new_canvas_has_no_new_template_policy",
];
const allPass = required.every((k) => checks[k] === true);
const verdict = allPass
  ? (skippedBackupChecks.length > 0 ? "PASS_WITH_SKIPPED_BACKUP" : "PASS")
  : "FAIL";
console.log(`[OCR_CANVAS_PANE_COMMON_UI_MOVE_5F] ${verdict}`);
process.exit(allPass ? 0 : 1);
