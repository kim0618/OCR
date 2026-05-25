#!/usr/bin/env node
// FRONTEND_STRUCTURE_6A_TEMPLATE_RIGHT_PANEL_RENAME
// Static check: confirm src/components/template/ui/OcrRightPanel.tsx was
// renamed to src/components/template/ui/TemplateRightPanel.tsx and that the
// default function inside is `TemplateRightPanel`. OcrAnnotator must import
// TemplateRightPanel from the new path and use the new JSX tag. Logic body
// (props type, JSX, state, handlers) must be byte-identical to the 6A backup
// apart from the renamed identifier on the default export line. Template
// table column definition policy must NOT be introduced.
//
// Read-only. No production code is modified.

import { readFileSync, existsSync, readdirSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, "..");

const NEW_PANEL = resolve(ROOT, "src/components/template/ui/TemplateRightPanel.tsx");
const OLD_PANEL = resolve(ROOT, "src/components/template/ui/OcrRightPanel.tsx");

// NOTE: After 6B (Template annotator rename) the annotator lives at
// .../TemplateAnnotator.tsx. Resolve to whichever currently exists; the
// rename-identifier normalizer below also collapses the OcrAnnotator/
// TemplateAnnotator identifier rename.
const ANNOTATOR_AT_OCR_NAME = resolve(ROOT, "src/components/template/ui/OcrAnnotator.tsx");
const ANNOTATOR_AT_TEMPLATE_NAME = resolve(ROOT, "src/components/template/ui/TemplateAnnotator.tsx");
const ANNOTATOR = existsSync(ANNOTATOR_AT_OCR_NAME)
  ? ANNOTATOR_AT_OCR_NAME
  : ANNOTATOR_AT_TEMPLATE_NAME;
const OCR_CANVAS = resolve(ROOT, "src/common/ui/OcrCanvasPane.tsx");
const FILEDROPZONE = resolve(ROOT, "src/common/ui/FileDropzone.tsx");
const TYPES = resolve(ROOT, "src/common/types/ocr.ts");
const OPS = resolve(ROOT, "src/common/utils/ocrCanvasOps.ts");
const TABLE = resolve(ROOT, "src/common/utils/ocrTableRegion.ts");

const RUNOCR_WORKSPACE = resolve(ROOT, "src/components/runocr/RunOcrWorkspace.tsx");
const RUNOCR_UI_DIR = resolve(ROOT, "src/components/runocr/ui");
const RUNOCR_UTILS_DIR = resolve(ROOT, "src/components/runocr/utils");
const TEST_WORKSPACE = resolve(ROOT, "src/components/test/TestWorkspace.tsx");
const TEST_CORE_DIR = resolve(ROOT, "src/components/test/core");

const TEMPLATE_MAPPER = resolve(ROOT, "src/components/template/utils/templateMapper.ts");
const TEMPLATE_TABLE_COLUMN_EDITOR = resolve(
  ROOT, "src/components/template/ui/TemplateTableColumnEditor.tsx",
);

const BACKUP_DIR = resolve(
  ROOT,
  "backup",
  "template_right_panel_20260522_before_FRONTEND_STRUCTURE_6A_TEMPLATE_RIGHT_PANEL_RENAME",
);
const PANEL_BACKUP = resolve(BACKUP_DIR, "OcrRightPanel.tsx");
const ANNOTATOR_BACKUP = resolve(BACKUP_DIR, "OcrAnnotator.tsx");

function readSafe(p) { try { return readFileSync(p, "utf8"); } catch { return null; } }
function stripComments(src) {
  return src
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .replace(/(^|[^:])\/\/[^\n]*/g, "$1");
}
function stripImportPaths(src) {
  return src.replace(/from\s+["'][^"']+["']/g, 'from "<<IMPORT>>"');
}
// 6A renames the default-export function name AND the local JSX tag in
// OcrAnnotator. 6B then renames OcrAnnotator -> TemplateAnnotator across the
// file/import/JSX. For logic-equivalence vs backup we collapse both renames
// so the diff reduces to "just renames".
function stripRenamedIdentifiers(src) {
  return src
    .replace(/\bOcrRightPanel\b/g, "<<RIGHT_PANEL>>")
    .replace(/\bTemplateRightPanel\b/g, "<<RIGHT_PANEL>>")
    .replace(/\bOcrAnnotator\b/g, "<<ANNOTATOR>>")
    .replace(/\bTemplateAnnotator\b/g, "<<ANNOTATOR>>");
}
function normalizeForRenameLogic(src) {
  return stripRenamedIdentifiers(stripImportPaths(stripComments(src)))
    .replace(/\s+/g, " ")
    .trim();
}

const checks = {};
const skippedBackupChecks = [];

// 1) New path exists, old path absent.
checks.new_panel_exists = existsSync(NEW_PANEL);
checks.old_panel_absent = !existsSync(OLD_PANEL);

// 2) Protected 5A/5B/5C/5E/5F artefacts still in place.
checks.types_still_under_common_types = existsSync(TYPES);
checks.ops_still_under_common_utils = existsSync(OPS);
checks.table_still_under_common_utils = existsSync(TABLE);
checks.OcrCanvasPane_still_under_common_ui = existsSync(OCR_CANVAS);
checks.FileDropzone_still_under_common_ui = existsSync(FILEDROPZONE);

// 3) OcrAnnotator still at its original path; RunOCR / TestWorkspace
//    untouched paths.
checks.OcrAnnotator_untouched_path = existsSync(ANNOTATOR);
checks.RunOcrWorkspace_untouched_path = existsSync(RUNOCR_WORKSPACE);
checks.runocr_ui_dir_present = existsSync(RUNOCR_UI_DIR);
checks.runocr_utils_dir_present = existsSync(RUNOCR_UTILS_DIR);
checks.TestWorkspace_present = existsSync(TEST_WORKSPACE);
checks.test_core_dir_present = existsSync(TEST_CORE_DIR);

// 4) TemplateRightPanel.tsx default-exports `TemplateRightPanel`, no longer
//    `OcrRightPanel`.
const newPanelSrc = readSafe(NEW_PANEL);
checks.new_panel_default_export_TemplateRightPanel =
  newPanelSrc !== null &&
  /export\s+default\s+function\s+TemplateRightPanel\b/.test(newPanelSrc);
checks.new_panel_no_residual_OcrRightPanel_identifier =
  newPanelSrc !== null && !/\bOcrRightPanel\b/.test(newPanelSrc);

// 5) Imports in TemplateRightPanel.tsx unchanged from the 6A backup (apart
//    from the identifier rename — paths and prop types must be identical).
const panelBackup = readSafe(PANEL_BACKUP);
if (panelBackup === null) {
  skippedBackupChecks.push({
    check: "new_panel_logic_unchanged_vs_backup",
    reason: `SKIP_WITH_REASON: backup not found: ${PANEL_BACKUP}`,
  });
}
// TPL-9B phase-aware: TemplateRightPanel now mounts the column definition
// section. Skip the rename-only backup-equivalence guard when that marker
// is present.
const _tpl9bShipped_6a_panel = typeof newPanelSrc === "string"
  && /CANONICAL_COLUMN_OPTIONS/.test(newPanelSrc);
if (_tpl9bShipped_6a_panel) {
  skippedBackupChecks.push({
    check: "new_panel_logic_unchanged_vs_backup",
    reason: "SKIP_WITH_REASON: TPL-9B extended TemplateRightPanel beyond 6A scope (column-definition marker matched)",
  });
  checks.new_panel_logic_unchanged_vs_backup = true;
} else {
  checks.new_panel_logic_unchanged_vs_backup =
    newPanelSrc !== null && panelBackup !== null &&
    normalizeForRenameLogic(newPanelSrc) === normalizeForRenameLogic(panelBackup);
}

// 6) Confirm prop names preserved (a few representative fields).
const REQUIRED_PROP_NAMES = [
  "imgRef",
  "templateName",
  "setTemplateName",
  "documentType",
  "setDocumentType",
  "loaded",
  "regions",
  "setRegions",
  "selectedId",
  "setSelectedId",
  "rowTemplateTargetId",
  "setRowTemplateTargetId",
  "colGuideTargetId",
  "setColGuideTargetId",
  "updateName",
  "deleteRegion",
];
checks.new_panel_props_preserved =
  newPanelSrc !== null &&
  REQUIRED_PROP_NAMES.every((p) => new RegExp(`\\b${p}\\b`).test(newPanelSrc));

// 7) OcrAnnotator imports TemplateRightPanel from new path AND uses the
//    new JSX tag.
const annotatorSrc = readSafe(ANNOTATOR);
checks.annotator_imports_template_right_panel =
  annotatorSrc !== null &&
  /import\s+TemplateRightPanel\s+from\s+["']\.\/TemplateRightPanel["']/.test(annotatorSrc) &&
  !/import\s+OcrRightPanel\b/.test(annotatorSrc) &&
  !/from\s+["']\.\/OcrRightPanel["']/.test(annotatorSrc);
checks.annotator_uses_template_right_panel_jsx =
  annotatorSrc !== null &&
  /<TemplateRightPanel\b/.test(annotatorSrc) &&
  !/<OcrRightPanel\b/.test(annotatorSrc);

// 8) Annotator body logic-equivalent to backup (only import path + JSX tag +
//    identifier renamed).
const annotatorBackup = readSafe(ANNOTATOR_BACKUP);
if (annotatorBackup === null) {
  skippedBackupChecks.push({
    check: "annotator_logic_unchanged_vs_backup",
    reason: `SKIP_WITH_REASON: backup not found: ${ANNOTATOR_BACKUP}`,
  });
}
// TPL-12C phase-aware: TemplateAnnotator gained rowAdjustTargetId state +
// props beyond 6A's rename-only scope.
const _tpl12cShipped_ann_6a = typeof annotatorSrc === "string"
  && /rowAdjustTargetId/.test(annotatorSrc);
if (_tpl12cShipped_ann_6a) {
  skippedBackupChecks.push({
    check: "annotator_logic_unchanged_vs_backup",
    reason: "SKIP_WITH_REASON: TPL-12C added rowAdjustTargetId to TemplateAnnotator beyond 6A scope",
  });
  checks.annotator_logic_unchanged_vs_backup = true;
} else {
  checks.annotator_logic_unchanged_vs_backup =
    annotatorSrc !== null && annotatorBackup !== null &&
    normalizeForRenameLogic(annotatorSrc) === normalizeForRenameLogic(annotatorBackup);
}

// 9) No residual OcrRightPanel anywhere in src/ (file imports OR JSX tags OR
//    type names OR string literals).
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
const residuals = [];
for (const f of srcFiles) {
  const s = readSafe(f);
  if (!s) continue;
  if (/\bOcrRightPanel\b/.test(s)) residuals.push({ file: f, pattern: "OcrRightPanel" });
  if (/components\/template\/ui\/OcrRightPanel/.test(s)) residuals.push({ file: f, pattern: "components/template/ui/OcrRightPanel" });
  if (/components\/ocr\/OcrRightPanel/.test(s)) residuals.push({ file: f, pattern: "components/ocr/OcrRightPanel" });
}
checks.no_residual_OcrRightPanel_in_src = residuals.length === 0;

// 10) FileDropzone / OcrCanvasPane / RunOCR / TestWorkspace not changed by 6A.
//     Spot-check that key identifiers in those files are still where they
//     were. We don't pull in extra backups, but we sanity-check defaults.
const fileDropzoneSrc = readSafe(FILEDROPZONE);
const ocrCanvasSrc = readSafe(OCR_CANVAS);
checks.FileDropzone_unchanged_default_export =
  fileDropzoneSrc !== null && /export\s+default\s+function\s+FileDropzone\b/.test(fileDropzoneSrc);
checks.OcrCanvasPane_unchanged_default_export =
  ocrCanvasSrc !== null && /export\s+default\s+function\s+OcrCanvasPane\b/.test(ocrCanvasSrc);

// 11) Template table column definition policy must NOT be introduced — at
//     6A time. TPL-9B intentionally adds canonicalColumn / columnKey UI, so
//     this guard becomes phase-aware once TPL-9B ships.
checks.template_table_column_editor_not_introduced = !existsSync(TEMPLATE_TABLE_COLUMN_EDITOR);
checks.template_mapper_not_introduced = !existsSync(TEMPLATE_MAPPER);
const TEMPLATE_POLICY_BLOCKLIST = [
  /\bcanonicalColumn\b/,
  /\buserConfirmed\b/,
  /\bcolumnMappingStatus\b/,
  /\bcolumnCandidates\b/,
];
if (_tpl9bShipped_6a_panel) {
  skippedBackupChecks.push({
    check: "new_panel_has_no_new_template_policy",
    reason: "SKIP_WITH_REASON: TPL-9B intentionally introduces canonicalColumn UI in TemplateRightPanel",
  });
  checks.new_panel_has_no_new_template_policy = true;
} else {
  checks.new_panel_has_no_new_template_policy =
    newPanelSrc !== null && !TEMPLATE_POLICY_BLOCKLIST.some((re) => re.test(newPanelSrc));
}

const summary = {
  task: "FRONTEND-STRUCTURE-6A-TEMPLATE-RIGHT-PANEL-RENAME",
  paths: {
    new_panel: NEW_PANEL,
    old_panel: OLD_PANEL,
    annotator: ANNOTATOR,
    canvas: OCR_CANVAS,
    filedropzone: FILEDROPZONE,
    runocr: RUNOCR_WORKSPACE,
  },
  checks,
  skippedBackupChecks,
  residuals,
};
console.log(JSON.stringify(summary, null, 2));

const required = [
  "new_panel_exists",
  "old_panel_absent",
  "types_still_under_common_types",
  "ops_still_under_common_utils",
  "table_still_under_common_utils",
  "OcrCanvasPane_still_under_common_ui",
  "FileDropzone_still_under_common_ui",
  "OcrAnnotator_untouched_path",
  "RunOcrWorkspace_untouched_path",
  "runocr_ui_dir_present",
  "runocr_utils_dir_present",
  "TestWorkspace_present",
  "test_core_dir_present",
  "new_panel_default_export_TemplateRightPanel",
  "new_panel_no_residual_OcrRightPanel_identifier",
  "new_panel_logic_unchanged_vs_backup",
  "new_panel_props_preserved",
  "annotator_imports_template_right_panel",
  "annotator_uses_template_right_panel_jsx",
  "annotator_logic_unchanged_vs_backup",
  "no_residual_OcrRightPanel_in_src",
  "FileDropzone_unchanged_default_export",
  "OcrCanvasPane_unchanged_default_export",
  "template_table_column_editor_not_introduced",
  "template_mapper_not_introduced",
  "new_panel_has_no_new_template_policy",
];
const allPass = required.every((k) => checks[k] === true);
const verdict = allPass
  ? (skippedBackupChecks.length > 0 ? "PASS_WITH_SKIPPED_BACKUP" : "PASS")
  : "FAIL";
console.log(`[TEMPLATE_RIGHT_PANEL_RENAME_6A] ${verdict}`);
process.exit(allPass ? 0 : 1);
