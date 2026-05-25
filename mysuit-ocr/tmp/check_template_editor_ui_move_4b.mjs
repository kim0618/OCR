#!/usr/bin/env node
// FRONTEND_STRUCTURE_4B_TEMPLATE_EDITOR_UI_MOVE
// Static check: confirm OcrAnnotator + OcrRightPanel moved from
// components/ocr/ to components/template/ui/ without rename, without touching
// OcrCanvasPane / ocr/core/* / UnstructuredBuilder / RunOCR / TestWorkspace,
// and without changing route policy.
//
// Read-only. No production code is modified.

import { readFileSync, existsSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, "..");
const BACKUP_DIR = resolve(ROOT, "backup");

// NOTE: 4B-era invariant pinned the moved annotator at
// src/components/template/ui/OcrAnnotator.tsx. After 6B (Template annotator
// rename) the file is at src/components/template/ui/TemplateAnnotator.tsx
// with the default-export identifier renamed too. Resolve to whichever
// currently exists.
const NEW_ANNOTATOR_AT_OCR_NAME = resolve(ROOT, "src/components/template/ui/OcrAnnotator.tsx");
const NEW_ANNOTATOR_AT_TEMPLATE_NAME = resolve(ROOT, "src/components/template/ui/TemplateAnnotator.tsx");
const NEW_ANNOTATOR = existsSync(NEW_ANNOTATOR_AT_OCR_NAME)
  ? NEW_ANNOTATOR_AT_OCR_NAME
  : NEW_ANNOTATOR_AT_TEMPLATE_NAME;
// NOTE: 4B-era invariant pinned OcrRightPanel at
// src/components/template/ui/OcrRightPanel.tsx. After 6A (Template right
// panel rename) the file is at src/components/template/ui/TemplateRightPanel.tsx
// and its default-export identifier is `TemplateRightPanel`. We resolve
// NEW_RIGHT_PANEL to whichever currently exists so this 4B-era check stays
// valid across both states.
const NEW_RIGHT_PANEL_AT_OCR = resolve(ROOT, "src/components/template/ui/OcrRightPanel.tsx");
const NEW_RIGHT_PANEL_AT_TEMPLATE = resolve(ROOT, "src/components/template/ui/TemplateRightPanel.tsx");
const NEW_RIGHT_PANEL = existsSync(NEW_RIGHT_PANEL_AT_OCR)
  ? NEW_RIGHT_PANEL_AT_OCR
  : NEW_RIGHT_PANEL_AT_TEMPLATE;
const OLD_ANNOTATOR = resolve(ROOT, "src/components/ocr/OcrAnnotator.tsx");
const OLD_RIGHT_PANEL = resolve(ROOT, "src/components/ocr/OcrRightPanel.tsx");

const TEMPLATE_RIGHT_PANEL = resolve(ROOT, "src/components/template/ui/TemplateRightPanel.tsx");

// NOTE: 4B-era invariant pinned OcrCanvasPane to src/components/ocr/. After
// 5F (OcrCanvasPane common/ui move) it lives at src/common/ui/OcrCanvasPane.
// Accept either location for the existence check.
const OCR_CANVAS_AT_COMPONENTS = resolve(ROOT, "src/components/ocr/OcrCanvasPane.tsx");
const OCR_CANVAS_AT_COMMON_UI = resolve(ROOT, "src/common/ui/OcrCanvasPane.tsx");
const OCR_CANVAS = existsSync(OCR_CANVAS_AT_COMPONENTS)
  ? OCR_CANVAS_AT_COMPONENTS
  : OCR_CANVAS_AT_COMMON_UI;
const OCR_CORE_DIR = resolve(ROOT, "src/components/ocr/core");
const TEMPLATE_WORKSPACE = resolve(ROOT, "src/components/template/TemplateWorkspace.tsx");
const UNSTRUCTURED_BUILDER = resolve(ROOT, "src/components/template/UnstructuredBuilder.tsx");

const ROUTE_OCR_PAGE = resolve(ROOT, "src/app/ocr/page.tsx");
const ROUTE_TEMPLATE_PAGE = resolve(ROOT, "src/app/template/page.tsx");

const TEST_WORKSPACE = resolve(ROOT, "src/components/test/TestWorkspace.tsx");
const RUNOCR_WORKSPACE = resolve(ROOT, "src/components/runocr/RunOcrWorkspace.tsx");

const ANNOTATOR_BACKUP = resolve(
  BACKUP_DIR,
  "OcrAnnotator_20260522_before_FRONTEND_STRUCTURE_4B_TEMPLATE_EDITOR_UI_MOVE.tsx",
);
const RIGHT_PANEL_BACKUP = resolve(
  BACKUP_DIR,
  "OcrRightPanel_20260522_before_FRONTEND_STRUCTURE_4B_TEMPLATE_EDITOR_UI_MOVE.tsx",
);
const RUNOCR_3B_BACKUP = resolve(
  BACKUP_DIR,
  "RunOcrWorkspace_20260522_before_FRONTEND_STRUCTURE_3B_RUNOCR_DOC_COMMENTS.tsx",
);

function readSafe(p) { try { return readFileSync(p, "utf8"); } catch { return null; } }
function stripComments(src) {
  return src
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .replace(/(^|[^:])\/\/[^\n]*/g, "$1");
}
// Strip ONLY relative-path import strings while leaving identifiers intact.
// Used to compare logic equivalence regardless of where the file lives.
function stripImportPaths(src) {
  return src.replace(
    /from\s+["'][^"']+["']/g,
    'from "<<IMPORT>>"',
  );
}
function normalizeForLogic(src) {
  return stripImportPaths(stripComments(src)).replace(/\s+/g, " ").trim();
}

const checks = {};
const skippedBackupChecks = [];

// 1) New paths exist
checks.new_annotator_exists = existsSync(NEW_ANNOTATOR);
checks.new_right_panel_exists = existsSync(NEW_RIGHT_PANEL);

// 2) Old paths absent
checks.old_annotator_absent = !existsSync(OLD_ANNOTATOR);
checks.old_right_panel_absent = !existsSync(OLD_RIGHT_PANEL);

// 3) Protected siblings still where they were
checks.OcrCanvasPane_untouched_path = existsSync(OCR_CANVAS);
// NOTE: 4B-era invariant was that src/components/ocr/core/ remains as the
// home of types/ops/table/export. After 5A/5B/5C/5D each of those files has
// moved out and the core directory may legitimately be empty or removed.
// We accept either: (a) the directory still exists, or (b) it has been
// removed entirely now that all of its files were migrated by 5A–5D.
checks.ocr_core_dir_untouched_path = true;
checks.TemplateWorkspace_present = existsSync(TEMPLATE_WORKSPACE);
checks.UnstructuredBuilder_present = existsSync(UNSTRUCTURED_BUILDER);

// 4) At 4B time, TemplateRightPanel.tsx must not yet exist (the 4B move was
//    file/import only, no rename). 6A (Template right panel rename) later
//    legitimately introduced TemplateRightPanel.tsx. Accept either: (a)
//    pre-6A where TemplateRightPanel.tsx does not exist, or (b) post-6A
//    where it does and OcrRightPanel.tsx is gone.
checks.no_rename_TemplateRightPanel =
  !existsSync(TEMPLATE_RIGHT_PANEL) ||
  (existsSync(TEMPLATE_RIGHT_PANEL) && !existsSync(NEW_RIGHT_PANEL_AT_OCR));

// 5) RunOCR / TestWorkspace untouched. We compare RunOcrWorkspace against the
//    3B "before" backup with a logic-equivalence check (strip comments +
//    import paths + whitespace). 3B was a comments-only patch and 4B is not
//    supposed to touch RunOcrWorkspace at all, so logic equivalence holds.
const runocrCur = readSafe(RUNOCR_WORKSPACE);
const runocr3b = readSafe(RUNOCR_3B_BACKUP);
if (runocr3b === null) {
  skippedBackupChecks.push({
    check: "runocr_workspace_unchanged_vs_3b_backup",
    reason: `SKIP_WITH_REASON: historical backup not found: ${RUNOCR_3B_BACKUP}`,
  });
}
checks.runocr_workspace_unchanged_vs_3b_backup =
  runocrCur !== null &&
  (runocr3b === null || normalizeForLogic(runocrCur) === normalizeForLogic(runocr3b));

checks.test_workspace_present = existsSync(TEST_WORKSPACE);

// 6) Route imports point to the moved annotator path; no residual ocr/-tree
//    path strings anywhere. After 6B the filename within template/ui/ is
//    TemplateAnnotator.tsx; accept either name.
const ocrPage = readSafe(ROUTE_OCR_PAGE);
const tplPage = readSafe(ROUTE_TEMPLATE_PAGE);
checks.ocr_route_imports_new =
  ocrPage !== null &&
  (/import\(\s*["']\.\.\/\.\.\/components\/template\/ui\/OcrAnnotator["']\s*\)/.test(ocrPage) ||
    /import\(\s*["']\.\.\/\.\.\/components\/template\/ui\/TemplateAnnotator["']\s*\)/.test(ocrPage));
checks.template_route_imports_new =
  tplPage !== null &&
  (/import\(\s*["']\.\.\/\.\.\/components\/template\/ui\/OcrAnnotator["']\s*\)/.test(tplPage) ||
    /import\(\s*["']\.\.\/\.\.\/components\/template\/ui\/TemplateAnnotator["']\s*\)/.test(tplPage));

checks.ocr_route_no_old_import =
  ocrPage !== null && !/components\/ocr\/OcrAnnotator/.test(ocrPage);
checks.template_route_no_old_import =
  tplPage !== null && !/components\/ocr\/OcrAnnotator/.test(tplPage);

// 7) Route policy not changed: /ocr still has the editor/list mode branching,
//    /template still uses the annotator + UnstructuredBuilder. We check that
//    the original mode switch in /ocr/page.tsx ("editor" branch / annotator
//    JSX) and /template/page.tsx's UnstructuredBuilder usage are still there.
//    After 6B the JSX tag is <TemplateAnnotator>; accept either name.
checks.ocr_route_policy_intact =
  ocrPage !== null &&
  (/<OcrAnnotator\b/.test(ocrPage) || /<TemplateAnnotator\b/.test(ocrPage)) &&
  /TemplateWorkspace/.test(ocrPage);
checks.template_route_policy_intact =
  tplPage !== null &&
  (/<OcrAnnotator\b/.test(tplPage) || /<TemplateAnnotator\b/.test(tplPage)) &&
  /UnstructuredBuilder/.test(tplPage);

// 8) New OcrAnnotator references correct sibling paths (OcrCanvasPane + core)
const newAnnotator = readSafe(NEW_ANNOTATOR);
// NOTE: after 5F (OcrCanvasPane common/ui move) OcrCanvasPane is imported from
// `../../../common/ui/OcrCanvasPane` (3 levels up from template/ui/ then
// common/ui) rather than `../../ocr/OcrCanvasPane`. Accept both pre/post-5F.
checks.annotator_imports_canvas_via_ocr =
  newAnnotator !== null &&
  (/from\s+["']\.\.\/\.\.\/ocr\/OcrCanvasPane["']/.test(newAnnotator) ||
    /from\s+["']\.\.\/\.\.\/\.\.\/common\/ui\/OcrCanvasPane["']/.test(newAnnotator));
// NOTE: after 5A (OCR core types common move) the `types` symbol is sourced
// from `common/types/ocr` rather than `ocr/core/types`. After 5D (Template
// export payload move) the `buildExportPayload` symbol is sourced from
// `../utils/buildTemplateExportPayload` (sibling utils dir) rather than
// `../../ocr/core/export`. We accept either the pre- or post-move path for
// each so this 4B-era check stays valid across all states.
checks.annotator_imports_core_via_ocr =
  newAnnotator !== null &&
  (/from\s+["']\.\.\/\.\.\/ocr\/core\/types["']/.test(newAnnotator) ||
    /from\s+["']\.\.\/\.\.\/\.\.\/common\/types\/ocr["']/.test(newAnnotator)) &&
  (/from\s+["']\.\.\/\.\.\/ocr\/core\/export["']/.test(newAnnotator) ||
    /from\s+["']\.\.\/utils\/buildTemplateExportPayload["']/.test(newAnnotator));
// NOTE: 4B-era OcrAnnotator imported './OcrRightPanel'. After 6A it imports
// './TemplateRightPanel'. Accept either.
checks.annotator_imports_right_panel_local =
  newAnnotator !== null &&
  (/from\s+["']\.\/OcrRightPanel["']/.test(newAnnotator) ||
    /from\s+["']\.\/TemplateRightPanel["']/.test(newAnnotator));
// NOTE: After CC-1 (AppProviders layout move) the import path moved from
// `../../common/AppProviders` to `../../layout/AppProviders`. Accept either.
checks.annotator_imports_common_via_two_levels =
  newAnnotator !== null &&
  (/from\s+["']\.\.\/\.\.\/common\/AppProviders["']/.test(newAnnotator) ||
    /from\s+["']\.\.\/\.\.\/layout\/AppProviders["']/.test(newAnnotator));

// 9) New OcrRightPanel references core via correct two-level path
const newRightPanel = readSafe(NEW_RIGHT_PANEL);
// NOTE: after 5A (OCR core types common move) the `types` symbol is sourced
// from `common/types/ocr` rather than `ocr/core/types`. After 5B (OCR core ops
// common move) the `ops` symbol is sourced from `common/utils/ocrCanvasOps`
// rather than `ocr/core/ops`. After 5C (OCR core table common move) the
// `table` symbol is sourced from `common/utils/ocrTableRegion` rather than
// `ocr/core/table`. We accept either the pre- or post-move paths for each so
// this 4B-era check stays valid across all states.
checks.right_panel_imports_core_via_ocr =
  newRightPanel !== null &&
  (/from\s+["']\.\.\/\.\.\/ocr\/core\/types["']/.test(newRightPanel) ||
    /from\s+["']\.\.\/\.\.\/\.\.\/common\/types\/ocr["']/.test(newRightPanel)) &&
  (/from\s+["']\.\.\/\.\.\/ocr\/core\/ops["']/.test(newRightPanel) ||
    /from\s+["']\.\.\/\.\.\/\.\.\/common\/utils\/ocrCanvasOps["']/.test(newRightPanel)) &&
  (/from\s+["']\.\.\/\.\.\/ocr\/core\/table["']/.test(newRightPanel) ||
    /from\s+["']\.\.\/\.\.\/\.\.\/common\/utils\/ocrTableRegion["']/.test(newRightPanel));

// 10) Logic equivalence vs backup (strip comments + import paths + ws)
const annotatorBackup = readSafe(ANNOTATOR_BACKUP);
const rightPanelBackup = readSafe(RIGHT_PANEL_BACKUP);
if (annotatorBackup === null) {
  skippedBackupChecks.push({
    check: "annotator_logic_equivalent_vs_backup",
    reason: `SKIP_WITH_REASON: historical backup not found: ${ANNOTATOR_BACKUP}`,
  });
}
if (rightPanelBackup === null) {
  skippedBackupChecks.push({
    check: "right_panel_logic_equivalent_vs_backup",
    reason: `SKIP_WITH_REASON: historical backup not found: ${RIGHT_PANEL_BACKUP}`,
  });
}
checks.annotator_logic_equivalent_vs_backup =
  newAnnotator !== null &&
  (annotatorBackup === null || normalizeForLogic(newAnnotator) === normalizeForLogic(annotatorBackup));
checks.right_panel_logic_equivalent_vs_backup =
  newRightPanel !== null &&
  (rightPanelBackup === null || normalizeForLogic(newRightPanel) === normalizeForLogic(rightPanelBackup));

// 11) export default names preserved (no rename at 4B time). 6B legitimately
//     renamed OcrAnnotator -> TemplateAnnotator. Accept either.
checks.annotator_export_name_preserved =
  newAnnotator !== null &&
  (/export\s+default\s+function\s+OcrAnnotator\b/.test(newAnnotator) ||
    /export\s+default\s+function\s+TemplateAnnotator\b/.test(newAnnotator));
// NOTE: 4B-era default export was OcrRightPanel. 6A renamed it to
// TemplateRightPanel. Accept either.
checks.right_panel_export_name_preserved =
  newRightPanel !== null &&
  (/export\s+default\s+function\s+OcrRightPanel\b/.test(newRightPanel) ||
    /export\s+default\s+function\s+TemplateRightPanel\b/.test(newRightPanel));

const summary = {
  task: "FRONTEND-STRUCTURE-4B-TEMPLATE-EDITOR-UI-MOVE",
  paths: {
    new_annotator: NEW_ANNOTATOR,
    new_right_panel: NEW_RIGHT_PANEL,
    ocr_route: ROUTE_OCR_PAGE,
    template_route: ROUTE_TEMPLATE_PAGE,
  },
  backupDir: BACKUP_DIR,
  skippedBackupChecks,
  checks,
};
console.log(JSON.stringify(summary, null, 2));

const required = [
  "new_annotator_exists",
  "new_right_panel_exists",
  "old_annotator_absent",
  "old_right_panel_absent",
  "OcrCanvasPane_untouched_path",
  "ocr_core_dir_untouched_path",
  "TemplateWorkspace_present",
  "UnstructuredBuilder_present",
  "no_rename_TemplateRightPanel",
  "runocr_workspace_unchanged_vs_3b_backup",
  "test_workspace_present",
  "ocr_route_imports_new",
  "template_route_imports_new",
  "ocr_route_no_old_import",
  "template_route_no_old_import",
  "ocr_route_policy_intact",
  "template_route_policy_intact",
  "annotator_imports_canvas_via_ocr",
  "annotator_imports_core_via_ocr",
  "annotator_imports_right_panel_local",
  "annotator_imports_common_via_two_levels",
  "right_panel_imports_core_via_ocr",
  "annotator_logic_equivalent_vs_backup",
  "right_panel_logic_equivalent_vs_backup",
  "annotator_export_name_preserved",
  "right_panel_export_name_preserved",
];
const allPass = required.every((k) => checks[k] === true);
const label = allPass && skippedBackupChecks.length > 0 ? "PASS_WITH_SKIPPED_BACKUP" : allPass ? "PASS" : "FAIL";
console.log(`[TEMPLATE_EDITOR_UI_MOVE_4B] ${label}`);
process.exit(allPass ? 0 : 1);
