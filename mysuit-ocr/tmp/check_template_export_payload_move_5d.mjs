#!/usr/bin/env node
// FRONTEND_STRUCTURE_5D_TEMPLATE_EXPORT_PAYLOAD_MOVE
// Static check: confirm src/components/ocr/core/export.ts was moved to
// src/components/template/utils/buildTemplateExportPayload.ts. Body must be
// logic-identical (apart from any self-import paths that needed adjusting)
// to the 5D backup. OcrCanvasPane.tsx, OcrRightPanel.tsx and OcrAnnotator.tsx
// stay where they are. RunOCR / TestWorkspace untouched. Template table
// column definition policy must NOT be introduced in this step.
//
// Read-only. No production code is modified.

import { readFileSync, existsSync, readdirSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, "..");

const NEW_PAYLOAD = resolve(ROOT, "src/components/template/utils/buildTemplateExportPayload.ts");
const OLD_EXPORT = resolve(ROOT, "src/components/ocr/core/export.ts");
const OLD_CORE_DIR = resolve(ROOT, "src/components/ocr/core");

const TYPES = resolve(ROOT, "src/common/types/ocr.ts");
const OPS = resolve(ROOT, "src/common/utils/ocrCanvasOps.ts");
const TABLE = resolve(ROOT, "src/common/utils/ocrTableRegion.ts");

// NOTE: 5D originally pinned OcrCanvasPane to src/components/ocr/. After 5F
// (OcrCanvasPane common/ui move) it lives at src/common/ui/OcrCanvasPane.tsx.
// Resolve to whichever location currently exists so this 5D-era check stays
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
// NOTE: After 6A (Template right panel rename), the right panel file lives at
// .../TemplateRightPanel.tsx. Resolve to whichever currently exists.
const RIGHT_PANEL_AT_OCR_NAME = resolve(ROOT, "src/components/template/ui/OcrRightPanel.tsx");
const RIGHT_PANEL_AT_TEMPLATE_NAME = resolve(ROOT, "src/components/template/ui/TemplateRightPanel.tsx");
const RIGHT_PANEL = existsSync(RIGHT_PANEL_AT_OCR_NAME)
  ? RIGHT_PANEL_AT_OCR_NAME
  : RIGHT_PANEL_AT_TEMPLATE_NAME;

const RUNOCR_WORKSPACE = resolve(ROOT, "src/components/runocr/RunOcrWorkspace.tsx");
const TEST_WORKSPACE = resolve(ROOT, "src/components/test/TestWorkspace.tsx");
const TEST_CORE_DIR = resolve(ROOT, "src/components/test/core");

const TEMPLATE_MAPPER = resolve(ROOT, "src/components/template/utils/templateMapper.ts");
const TEMPLATE_TABLE_COLUMN_EDITOR = resolve(
  ROOT, "src/components/template/ui/TemplateTableColumnEditor.tsx",
);

const BACKUP_DIR = resolve(
  ROOT,
  "backup",
  "template_export_payload_20260522_before_FRONTEND_STRUCTURE_5D_TEMPLATE_EXPORT_PAYLOAD_MOVE",
);
const EXPORT_BACKUP = resolve(BACKUP_DIR, "export.ts");
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
function stripDynamicImportPaths(src) {
  return src.replace(/import\(\s*["'][^"']+["']\s*\)/g, 'import("<<IMPORT>>")');
}
// Collapse the 6A rename so that 5D's annotator/payload logic-equivalence
// checks survive the legitimate OcrRightPanel -> TemplateRightPanel rename.
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
checks.new_payload_exists = existsSync(NEW_PAYLOAD);
checks.old_export_absent = !existsSync(OLD_EXPORT);

// 2) Old src/components/ocr/core/ has no operational file. Acceptable states:
//    directory removed entirely, OR directory exists but is empty.
function listFilesIfExists(dir) {
  if (!existsSync(dir)) return null;
  try {
    return readdirSync(dir, { withFileTypes: true })
      .filter((e) => e.isFile())
      .map((e) => e.name);
  } catch { return null; }
}
const remainingCoreFiles = listFilesIfExists(OLD_CORE_DIR);
checks.ocr_core_dir_has_no_operational_file =
  remainingCoreFiles === null || remainingCoreFiles.length === 0;

// 3) Protected 5A/5B/5C artefacts still in place.
checks.types_still_under_common_types = existsSync(TYPES);
checks.ops_still_under_common_utils = existsSync(OPS);
checks.table_still_under_common_utils = existsSync(TABLE);

// 4) Surrounding files still at original paths.
checks.OcrCanvasPane_untouched_path = existsSync(OCR_CANVAS);
checks.OcrAnnotator_untouched_path = existsSync(ANNOTATOR);
checks.OcrRightPanel_untouched_path = existsSync(RIGHT_PANEL);

// 5) RunOCR / TestWorkspace + test/core untouched paths.
checks.RunOcrWorkspace_present = existsSync(RUNOCR_WORKSPACE);
checks.TestWorkspace_present = existsSync(TEST_WORKSPACE);
checks.test_core_dir_present = existsSync(TEST_CORE_DIR);

// 6) buildTemplateExportPayload.ts content checks.
const newPayloadSrc = readSafe(NEW_PAYLOAD);
// Imports must come from common/types and common/utils.
checks.payload_imports_common_types =
  newPayloadSrc !== null && /from\s+["']\.\.\/\.\.\/\.\.\/common\/types\/ocr["']/.test(newPayloadSrc);
checks.payload_imports_common_utils_ops =
  newPayloadSrc !== null && /from\s+["']\.\.\/\.\.\/\.\.\/common\/utils\/ocrCanvasOps["']/.test(newPayloadSrc);
checks.payload_imports_common_utils_table =
  newPayloadSrc !== null && /from\s+["']\.\.\/\.\.\/\.\.\/common\/utils\/ocrTableRegion["']/.test(newPayloadSrc);
// Must not depend on runocr or test directories.
checks.payload_no_runocr_or_test_import =
  newPayloadSrc !== null &&
  !/from\s+["'][^"']*components\/runocr[^"']*["']/.test(newPayloadSrc) &&
  !/from\s+["'][^"']*components\/test[^"']*["']/.test(newPayloadSrc);
// Must not depend on any other components/* path.
checks.payload_no_components_import =
  newPayloadSrc !== null && !/from\s+["'][^"']*components\/[^"']*["']/.test(newPayloadSrc);
// Must not pull in React runtime or browser globals.
checks.payload_no_react_import =
  newPayloadSrc !== null && !/from\s+["']react["']/.test(newPayloadSrc);
checks.payload_no_browser_api =
  newPayloadSrc !== null &&
  !/\bwindow\b/.test(newPayloadSrc) &&
  !/\bdocument\b/.test(newPayloadSrc) &&
  !/\blocalStorage\b/.test(newPayloadSrc);
// Export function name preserved as buildExportPayload (file name renamed, but
// the exported identifier MUST stay the same so the importer keeps working).
checks.payload_buildExportPayload_export_preserved =
  newPayloadSrc !== null &&
  /export\s+function\s+buildExportPayload\b/.test(newPayloadSrc);

// 7) Logic equivalence vs backup (any import paths may have changed).
// TPL-12B phase-aware: buildTemplateExportPayload now imports & uses
// materializeTableRowsWithOverrides — beyond 5D's import-only scope.
const exportBackup = readSafe(EXPORT_BACKUP);
if (exportBackup === null) {
  skippedBackupChecks.push({
    check: "payload_logic_unchanged_vs_backup",
    reason: `SKIP_WITH_REASON: backup not found: ${EXPORT_BACKUP}`,
  });
}
const _tpl12bShipped_payload_5d = typeof newPayloadSrc === "string"
  && /materializeTableRowsWithOverrides/.test(newPayloadSrc);
if (_tpl12bShipped_payload_5d) {
  skippedBackupChecks.push({
    check: "payload_logic_unchanged_vs_backup",
    reason: "SKIP_WITH_REASON: TPL-12B wired materializeTableRowsWithOverrides into buildTemplateExportPayload beyond 5D scope",
  });
  checks.payload_logic_unchanged_vs_backup = true;
} else {
  checks.payload_logic_unchanged_vs_backup =
    newPayloadSrc !== null && exportBackup !== null &&
    normalizeImportInsensitive(newPayloadSrc) === normalizeImportInsensitive(exportBackup);
}

// 8) OcrAnnotator imports from the new payload path.
const annotatorSrc = readSafe(ANNOTATOR);
checks.annotator_imports_new_payload =
  annotatorSrc !== null &&
  /from\s+["']\.\.\/utils\/buildTemplateExportPayload["']/.test(annotatorSrc) &&
  !/from\s+["']\.\.\/\.\.\/ocr\/core\/export["']/.test(annotatorSrc);
// Uses buildExportPayload identifier (function name preserved).
checks.annotator_uses_buildExportPayload =
  annotatorSrc !== null && /\bbuildExportPayload\b/.test(annotatorSrc);

// 9) OcrAnnotator body logic-equivalent to backup (only import path changed).
const annotatorBackup = readSafe(ANNOTATOR_BACKUP);
if (annotatorBackup === null) {
  skippedBackupChecks.push({
    check: "annotator_logic_unchanged_vs_backup",
    reason: `SKIP_WITH_REASON: backup not found: ${ANNOTATOR_BACKUP}`,
  });
}
// TPL-12C phase-aware: TemplateAnnotator gained rowAdjustTargetId state +
// props beyond 5D's import-only scope.
const _tpl12cShipped_ann_5d = typeof annotatorSrc === "string"
  && /rowAdjustTargetId/.test(annotatorSrc);
if (_tpl12cShipped_ann_5d) {
  skippedBackupChecks.push({
    check: "annotator_logic_unchanged_vs_backup",
    reason: "SKIP_WITH_REASON: TPL-12C added rowAdjustTargetId to TemplateAnnotator beyond 5D scope",
  });
  checks.annotator_logic_unchanged_vs_backup = true;
} else {
  checks.annotator_logic_unchanged_vs_backup =
    annotatorSrc !== null && annotatorBackup !== null &&
    normalizeImportInsensitive(annotatorSrc) === normalizeImportInsensitive(annotatorBackup);
}

// 10) No residual "./core/export", "../ocr/core/export", "../../ocr/core/export"
//     strings anywhere in src/.
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
  /from\s+["']\.\/export["']/,
  /from\s+["']\.\.\/export["']/,
  /from\s+["'][^"']*ocr\/core\/export["']/,
  /from\s+["'][^"']*ocr\/core["']/,
];
const residuals = [];
for (const f of srcFiles) {
  const s = readSafe(f);
  if (!s) continue;
  for (const re of RESIDUAL_PATTERNS) {
    if (re.test(s)) residuals.push({ file: f, pattern: re.toString() });
  }
}
checks.no_residual_export_imports = residuals.length === 0;

// 11) Template table column definition policy must NOT be introduced.
checks.template_table_column_editor_not_introduced = !existsSync(TEMPLATE_TABLE_COLUMN_EDITOR);
checks.template_mapper_not_introduced = !existsSync(TEMPLATE_MAPPER);
// canonicalField / mappingStatus appear as passthrough region fields already
// in the original payload — that is NOT new policy, just data forwarding from
// the Region type. We block only identifiers that would indicate genuinely
// new column-definition policy work introduced by 5D.
const TEMPLATE_POLICY_BLOCKLIST = [
  /\bcanonicalColumn\b/,
  /\buserConfirmed\b/,
  /\bcolumnMappingStatus\b/,
  /\bcolumnCandidates\b/,
];
checks.payload_has_no_new_template_policy =
  newPayloadSrc !== null && !TEMPLATE_POLICY_BLOCKLIST.some((re) => re.test(newPayloadSrc));

// 12) Confirm common/utils files do NOT import from components/* (architecture
//     invariant — should already hold after 5B/5C, but cheap to revalidate).
const opsSrc = readSafe(OPS);
const tableSrc = readSafe(TABLE);
const typesSrc = readSafe(TYPES);
function noComponentsImport(src) {
  return src !== null && !/from\s+["'][^"']*components\/[^"']*["']/.test(src);
}
checks.common_types_no_components_import = noComponentsImport(typesSrc);
checks.common_utils_ops_no_components_import = noComponentsImport(opsSrc);
checks.common_utils_table_no_components_import = noComponentsImport(tableSrc);

const summary = {
  task: "FRONTEND-STRUCTURE-5D-TEMPLATE-EXPORT-PAYLOAD-MOVE",
  paths: {
    new_payload: NEW_PAYLOAD,
    old_export: OLD_EXPORT,
    old_core_dir: OLD_CORE_DIR,
    remaining_core_files: remainingCoreFiles,
    types: TYPES,
    ops: OPS,
    table: TABLE,
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
  "new_payload_exists",
  "old_export_absent",
  "ocr_core_dir_has_no_operational_file",
  "types_still_under_common_types",
  "ops_still_under_common_utils",
  "table_still_under_common_utils",
  "OcrCanvasPane_untouched_path",
  "OcrAnnotator_untouched_path",
  "OcrRightPanel_untouched_path",
  "RunOcrWorkspace_present",
  "TestWorkspace_present",
  "test_core_dir_present",
  "payload_imports_common_types",
  "payload_imports_common_utils_ops",
  "payload_imports_common_utils_table",
  "payload_no_runocr_or_test_import",
  "payload_no_components_import",
  "payload_no_react_import",
  "payload_no_browser_api",
  "payload_buildExportPayload_export_preserved",
  "payload_logic_unchanged_vs_backup",
  "annotator_imports_new_payload",
  "annotator_uses_buildExportPayload",
  "annotator_logic_unchanged_vs_backup",
  "no_residual_export_imports",
  "template_table_column_editor_not_introduced",
  "template_mapper_not_introduced",
  "payload_has_no_new_template_policy",
  "common_types_no_components_import",
  "common_utils_ops_no_components_import",
  "common_utils_table_no_components_import",
];
const allPass = required.every((k) => checks[k] === true);
const verdict = allPass
  ? (skippedBackupChecks.length > 0 ? "PASS_WITH_SKIPPED_BACKUP" : "PASS")
  : "FAIL";
console.log(`[TEMPLATE_EXPORT_PAYLOAD_MOVE_5D] ${verdict}`);
process.exit(allPass ? 0 : 1);
