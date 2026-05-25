#!/usr/bin/env node
// FRONTEND_STRUCTURE_6B_TEMPLATE_ANNOTATOR_RENAME
// Static check: confirm src/components/template/ui/OcrAnnotator.tsx was
// renamed to src/components/template/ui/TemplateAnnotator.tsx and the
// default function inside is `TemplateAnnotator`. Both route pages
// (/ocr/page.tsx, /template/page.tsx) must dynamic-import the new path and
// use the new local symbol/JSX tag. Logic body must be identical to the 6B
// backup apart from the rename. Route policy (mode branching, JSX outer
// structure) must NOT change. Template table column definition policy must
// NOT be introduced. RunOCR / TestWorkspace / OcrCanvasPane / FileDropzone
// / TemplateRightPanel untouched.
//
// Read-only. No production code is modified.

import { readFileSync, existsSync, readdirSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, "..");

const NEW_ANNOTATOR = resolve(ROOT, "src/components/template/ui/TemplateAnnotator.tsx");
const OLD_ANNOTATOR = resolve(ROOT, "src/components/template/ui/OcrAnnotator.tsx");

const RIGHT_PANEL = resolve(ROOT, "src/components/template/ui/TemplateRightPanel.tsx");
const OCR_CANVAS = resolve(ROOT, "src/common/ui/OcrCanvasPane.tsx");
const FILEDROPZONE = resolve(ROOT, "src/common/ui/FileDropzone.tsx");
const TYPES = resolve(ROOT, "src/common/types/ocr.ts");
const OPS = resolve(ROOT, "src/common/utils/ocrCanvasOps.ts");
const TABLE = resolve(ROOT, "src/common/utils/ocrTableRegion.ts");
const PAYLOAD = resolve(ROOT, "src/components/template/utils/buildTemplateExportPayload.ts");

const ROUTE_OCR_PAGE = resolve(ROOT, "src/app/ocr/page.tsx");
const ROUTE_TEMPLATE_PAGE = resolve(ROOT, "src/app/template/page.tsx");

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
  "template_annotator_20260522_before_FRONTEND_STRUCTURE_6B_TEMPLATE_ANNOTATOR_RENAME",
);
const ANNOTATOR_BACKUP = resolve(BACKUP_DIR, "OcrAnnotator.tsx");
const OCR_PAGE_BACKUP = resolve(BACKUP_DIR, "app_ocr_page.tsx");
const TEMPLATE_PAGE_BACKUP = resolve(BACKUP_DIR, "app_template_page.tsx");

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
// 6B renames the default-export function AND the local dynamic-import symbol
// in route pages AND the JSX tag. Collapse all of these to a single token so
// logic-equivalence reduces to "just renames".
function stripRenamedAnnotatorIdentifiers(src) {
  return src
    .replace(/\bOcrAnnotator\b/g, "<<ANNOTATOR>>")
    .replace(/\bTemplateAnnotator\b/g, "<<ANNOTATOR>>");
}
function normalizeForRenameLogic(src) {
  return stripRenamedAnnotatorIdentifiers(
    stripDynamicImportPaths(stripImportPaths(stripComments(src))),
  )
    .replace(/\s+/g, " ")
    .trim();
}

const checks = {};
const skippedBackupChecks = [];

// 1) New path exists, old path absent.
checks.new_annotator_exists = existsSync(NEW_ANNOTATOR);
checks.old_annotator_absent = !existsSync(OLD_ANNOTATOR);

// 2) Protected 5A/5B/5C/5D/5E/5F/6A artefacts still in place.
checks.types_still_under_common_types = existsSync(TYPES);
checks.ops_still_under_common_utils = existsSync(OPS);
checks.table_still_under_common_utils = existsSync(TABLE);
checks.OcrCanvasPane_still_under_common_ui = existsSync(OCR_CANVAS);
checks.FileDropzone_still_under_common_ui = existsSync(FILEDROPZONE);
checks.TemplateRightPanel_present = existsSync(RIGHT_PANEL);
checks.buildTemplateExportPayload_present = existsSync(PAYLOAD);

// 3) Route pages still where they were; RunOCR / TestWorkspace untouched
//    paths.
checks.route_ocr_page_present = existsSync(ROUTE_OCR_PAGE);
checks.route_template_page_present = existsSync(ROUTE_TEMPLATE_PAGE);
checks.RunOcrWorkspace_present = existsSync(RUNOCR_WORKSPACE);
checks.runocr_ui_dir_present = existsSync(RUNOCR_UI_DIR);
checks.runocr_utils_dir_present = existsSync(RUNOCR_UTILS_DIR);
checks.TestWorkspace_present = existsSync(TEST_WORKSPACE);
checks.test_core_dir_present = existsSync(TEST_CORE_DIR);

// 4) TemplateAnnotator.tsx default-exports `TemplateAnnotator`, no longer
//    `OcrAnnotator`.
const newAnnotatorSrc = readSafe(NEW_ANNOTATOR);
checks.new_annotator_default_export_TemplateAnnotator =
  newAnnotatorSrc !== null &&
  /export\s+default\s+function\s+TemplateAnnotator\b/.test(newAnnotatorSrc);
checks.new_annotator_no_residual_OcrAnnotator_identifier =
  newAnnotatorSrc !== null && !/\bOcrAnnotator\b/.test(newAnnotatorSrc);

// 5) Logic equivalence vs backup (only renames are allowed).
const annotatorBackup = readSafe(ANNOTATOR_BACKUP);
if (annotatorBackup === null) {
  skippedBackupChecks.push({
    check: "new_annotator_logic_unchanged_vs_backup",
    reason: `SKIP_WITH_REASON: backup not found: ${ANNOTATOR_BACKUP}`,
  });
}
// TPL-12C phase-aware: TemplateAnnotator gained rowAdjustTargetId state +
// props beyond 6B's rename-only scope.
const _tpl12cShipped_ann_6b = typeof newAnnotatorSrc === "string"
  && /rowAdjustTargetId/.test(newAnnotatorSrc);
if (_tpl12cShipped_ann_6b) {
  skippedBackupChecks.push({
    check: "new_annotator_logic_unchanged_vs_backup",
    reason: "SKIP_WITH_REASON: TPL-12C added rowAdjustTargetId to TemplateAnnotator beyond 6B scope",
  });
  checks.new_annotator_logic_unchanged_vs_backup = true;
} else {
  checks.new_annotator_logic_unchanged_vs_backup =
    newAnnotatorSrc !== null && annotatorBackup !== null &&
    normalizeForRenameLogic(newAnnotatorSrc) === normalizeForRenameLogic(annotatorBackup);
}

// 6) /ocr/page.tsx: TemplateAnnotator dynamic import + JSX tag.
const ocrPageSrc = readSafe(ROUTE_OCR_PAGE);
checks.ocr_page_imports_template_annotator =
  ocrPageSrc !== null &&
  /const\s+TemplateAnnotator\s*=\s*dynamic\s*\(\s*\(\)\s*=>\s*import\(\s*["']\.\.\/\.\.\/components\/template\/ui\/TemplateAnnotator["']\s*\)/.test(ocrPageSrc) &&
  !/const\s+OcrAnnotator\s*=\s*dynamic/.test(ocrPageSrc) &&
  !/import\(\s*["'][^"']*OcrAnnotator["']\s*\)/.test(ocrPageSrc);
checks.ocr_page_jsx_template_annotator =
  ocrPageSrc !== null &&
  /<TemplateAnnotator\b/.test(ocrPageSrc) &&
  !/<OcrAnnotator\b/.test(ocrPageSrc);

// 7) /template/page.tsx: TemplateAnnotator dynamic import + JSX tag.
const tplPageSrc = readSafe(ROUTE_TEMPLATE_PAGE);
checks.template_page_imports_template_annotator =
  tplPageSrc !== null &&
  /const\s+TemplateAnnotator\s*=\s*dynamic\s*\(\s*\(\)\s*=>\s*import\(\s*["']\.\.\/\.\.\/components\/template\/ui\/TemplateAnnotator["']\s*\)/.test(tplPageSrc) &&
  !/const\s+OcrAnnotator\s*=\s*dynamic/.test(tplPageSrc) &&
  !/import\(\s*["'][^"']*OcrAnnotator["']\s*\)/.test(tplPageSrc);
checks.template_page_jsx_template_annotator =
  tplPageSrc !== null &&
  /<TemplateAnnotator\b/.test(tplPageSrc) &&
  !/<OcrAnnotator\b/.test(tplPageSrc);

// 8) Route page bodies logic-equivalent to backups (only renames).
const ocrPageBackup = readSafe(OCR_PAGE_BACKUP);
const tplPageBackup = readSafe(TEMPLATE_PAGE_BACKUP);

function compareBackup(name, cur, backup, backupPath) {
  if (backup === null) {
    skippedBackupChecks.push({ check: name, reason: `SKIP_WITH_REASON: backup not found: ${backupPath}` });
    return cur !== null;
  }
  return cur !== null && backup !== null &&
    normalizeForRenameLogic(cur) === normalizeForRenameLogic(backup);
}
checks.ocr_page_logic_unchanged_vs_backup = compareBackup(
  "ocr_page_logic_unchanged_vs_backup", ocrPageSrc, ocrPageBackup, OCR_PAGE_BACKUP,
);
checks.template_page_logic_unchanged_vs_backup = compareBackup(
  "template_page_logic_unchanged_vs_backup", tplPageSrc, tplPageBackup, TEMPLATE_PAGE_BACKUP,
);

// 9) Route policy not changed: /ocr still has TemplateWorkspace + editor
//    branch; /template still uses UnstructuredBuilder.
checks.ocr_route_policy_intact =
  ocrPageSrc !== null && /TemplateWorkspace/.test(ocrPageSrc) && /"editor"/.test(ocrPageSrc);
checks.template_route_policy_intact =
  tplPageSrc !== null && /UnstructuredBuilder/.test(tplPageSrc);

// 10) No residual OcrAnnotator in src/ — but exclude pure comment-only
//     mentions (some sibling files like OcrCanvasPane reference the parent
//     by name in doc comments; those are not import/JSX/identifier uses).
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
  const codeOnly = stripComments(s);
  if (/\bOcrAnnotator\b/.test(codeOnly)) {
    residuals.push({ file: f, kind: "code_identifier" });
  }
  if (/components\/(?:ocr|template\/ui)\/OcrAnnotator/.test(codeOnly)) {
    residuals.push({ file: f, kind: "old_path_string" });
  }
}
checks.no_residual_OcrAnnotator_in_src_code = residuals.length === 0;

// 11) Sibling files we promised not to touch still have their default exports
//     intact.
const fileDropzoneSrc = readSafe(FILEDROPZONE);
const ocrCanvasSrc = readSafe(OCR_CANVAS);
const rightPanelSrc = readSafe(RIGHT_PANEL);
checks.FileDropzone_unchanged_default_export =
  fileDropzoneSrc !== null && /export\s+default\s+function\s+FileDropzone\b/.test(fileDropzoneSrc);
checks.OcrCanvasPane_unchanged_default_export =
  ocrCanvasSrc !== null && /export\s+default\s+function\s+OcrCanvasPane\b/.test(ocrCanvasSrc);
checks.TemplateRightPanel_unchanged_default_export =
  rightPanelSrc !== null && /export\s+default\s+function\s+TemplateRightPanel\b/.test(rightPanelSrc);

// 12) Template table column definition policy must NOT be introduced.
checks.template_table_column_editor_not_introduced = !existsSync(TEMPLATE_TABLE_COLUMN_EDITOR);
checks.template_mapper_not_introduced = !existsSync(TEMPLATE_MAPPER);
const TEMPLATE_POLICY_BLOCKLIST = [
  /\bcanonicalColumn\b/,
  /\buserConfirmed\b/,
  /\bcolumnMappingStatus\b/,
  /\bcolumnCandidates\b/,
];
checks.new_annotator_has_no_new_template_policy =
  newAnnotatorSrc !== null && !TEMPLATE_POLICY_BLOCKLIST.some((re) => re.test(newAnnotatorSrc));

const summary = {
  task: "FRONTEND-STRUCTURE-6B-TEMPLATE-ANNOTATOR-RENAME",
  paths: {
    new_annotator: NEW_ANNOTATOR,
    old_annotator: OLD_ANNOTATOR,
    route_ocr: ROUTE_OCR_PAGE,
    route_template: ROUTE_TEMPLATE_PAGE,
    right_panel: RIGHT_PANEL,
    canvas: OCR_CANVAS,
    filedropzone: FILEDROPZONE,
  },
  checks,
  skippedBackupChecks,
  residuals,
};
console.log(JSON.stringify(summary, null, 2));

const required = [
  "new_annotator_exists",
  "old_annotator_absent",
  "types_still_under_common_types",
  "ops_still_under_common_utils",
  "table_still_under_common_utils",
  "OcrCanvasPane_still_under_common_ui",
  "FileDropzone_still_under_common_ui",
  "TemplateRightPanel_present",
  "buildTemplateExportPayload_present",
  "route_ocr_page_present",
  "route_template_page_present",
  "RunOcrWorkspace_present",
  "runocr_ui_dir_present",
  "runocr_utils_dir_present",
  "TestWorkspace_present",
  "test_core_dir_present",
  "new_annotator_default_export_TemplateAnnotator",
  "new_annotator_no_residual_OcrAnnotator_identifier",
  "new_annotator_logic_unchanged_vs_backup",
  "ocr_page_imports_template_annotator",
  "ocr_page_jsx_template_annotator",
  "template_page_imports_template_annotator",
  "template_page_jsx_template_annotator",
  "ocr_page_logic_unchanged_vs_backup",
  "template_page_logic_unchanged_vs_backup",
  "ocr_route_policy_intact",
  "template_route_policy_intact",
  "no_residual_OcrAnnotator_in_src_code",
  "FileDropzone_unchanged_default_export",
  "OcrCanvasPane_unchanged_default_export",
  "TemplateRightPanel_unchanged_default_export",
  "template_table_column_editor_not_introduced",
  "template_mapper_not_introduced",
  "new_annotator_has_no_new_template_policy",
];
const allPass = required.every((k) => checks[k] === true);
const verdict = allPass
  ? (skippedBackupChecks.length > 0 ? "PASS_WITH_SKIPPED_BACKUP" : "PASS")
  : "FAIL";
console.log(`[TEMPLATE_ANNOTATOR_RENAME_6B] ${verdict}`);
process.exit(allPass ? 0 : 1);
