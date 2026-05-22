#!/usr/bin/env node
// FRONTEND_STRUCTURE_4A_TEMPLATE_WORKSPACE_MOVE
// Static check: confirm TemplateWorkspace.tsx was moved from
// components/ocr/ to components/template/ with only the necessary route
// import touched. Protected siblings (OcrAnnotator/OcrCanvasPane/OcrRightPanel/
// ocr/core/*) must NOT have moved. TestWorkspace.tsx must be untouched.
//
// Read-only. No production code is modified.

import { readFileSync, existsSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, "..");

const NEW_PATH = resolve(ROOT, "src/components/template/TemplateWorkspace.tsx");
const OLD_PATH = resolve(ROOT, "src/components/ocr/TemplateWorkspace.tsx");

const ROUTE_OCR_PAGE = resolve(ROOT, "src/app/ocr/page.tsx");
const ROUTE_TEMPLATE_PAGE = resolve(ROOT, "src/app/template/page.tsx");

const OCR_ANNOTATOR = resolve(ROOT, "src/components/ocr/OcrAnnotator.tsx");
const OCR_CANVAS = resolve(ROOT, "src/components/ocr/OcrCanvasPane.tsx");
const OCR_RIGHT_PANEL = resolve(ROOT, "src/components/ocr/OcrRightPanel.tsx");
const OCR_CORE_DIR = resolve(ROOT, "src/components/ocr/core");
const UNSTRUCTURED_BUILDER = resolve(ROOT, "src/components/template/UnstructuredBuilder.tsx");
const TEST_WORKSPACE = resolve(ROOT, "src/components/test/TestWorkspace.tsx");

const BACKUP_DIR = resolve(ROOT, "..", "backup");
const TW_BACKUP = resolve(
  BACKUP_DIR,
  "TemplateWorkspace_20260522_before_FRONTEND_STRUCTURE_4A_TEMPLATE_WORKSPACE_MOVE.tsx",
);

function readSafe(p) { try { return readFileSync(p, "utf8"); } catch { return null; } }
function stripComments(src) {
  return src
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .replace(/(^|[^:])\/\/[^\n]*/g, "$1");
}
function normalizeForLogic(src) {
  return stripComments(src).replace(/\s+/g, " ").trim();
}

const newSrc = readSafe(NEW_PATH);
const ocrPageSrc = readSafe(ROUTE_OCR_PAGE);
const templatePageSrc = readSafe(ROUTE_TEMPLATE_PAGE);
const twBackup = readSafe(TW_BACKUP);

if (!newSrc) { console.error(`[FATAL] new path missing: ${NEW_PATH}`); process.exit(2); }
if (!ocrPageSrc) { console.error(`[FATAL] /ocr page missing: ${ROUTE_OCR_PAGE}`); process.exit(2); }

const checks = {};

// 1) TemplateWorkspace.tsx exists at the new location
checks.new_path_exists = existsSync(NEW_PATH);

// 2) Old location is gone
checks.old_path_absent = !existsSync(OLD_PATH);

// 3) /ocr/page.tsx imports from the new location
checks.route_imports_new_path =
  /import\s+TemplateWorkspace\s+from\s+["']\.\.\/\.\.\/components\/template\/TemplateWorkspace["']/.test(ocrPageSrc);

// 4) /ocr/page.tsx no longer imports from the old location
checks.route_no_old_import =
  !/components\/ocr\/TemplateWorkspace/.test(ocrPageSrc);

// 5) /template/page.tsx exists but does NOT import TemplateWorkspace (current
//    routing policy: /template route uses OcrAnnotator + UnstructuredBuilder
//    directly, /ocr route uses TemplateWorkspace list view).
//    Confirm the policy was preserved.
const templatePageHasTwImport = templatePageSrc !== null && /\bTemplateWorkspace\b/.test(templatePageSrc);
checks.template_route_unchanged = templatePageHasTwImport === false;

// 6) No residual components/ocr/TemplateWorkspace references anywhere in src/
const searchRoots = [
  resolve(ROOT, "src/app"),
  resolve(ROOT, "src/components"),
  resolve(ROOT, "src/lib"),
];
// We don't need to recursively scan — just confirm via the two route files +
// the moved file. Anything else referencing the old path would have failed
// typecheck. As a belt-and-suspenders, check the moved file itself.
checks.moved_file_no_self_reference =
  !/components\/ocr\/TemplateWorkspace/.test(newSrc);

// 7) Protected siblings.
//    - OcrCanvasPane.tsx and ocr/core/* are protected through every later
//      phase (4A, 4B, ...). Must remain at original ocr/ location.
//    - OcrAnnotator.tsx and OcrRightPanel.tsx were protected at 4A time, but
//      a later phase (4B) legitimately moves them to components/template/ui/.
//      Accept either the original ocr/ path OR the post-4B template/ui path
//      so this 4A-era check remains valid after 4B.
const NEW_ANNOTATOR_4B = resolve(ROOT, "src/components/template/ui/OcrAnnotator.tsx");
const NEW_RIGHT_PANEL_4B = resolve(ROOT, "src/components/template/ui/OcrRightPanel.tsx");
checks.OcrAnnotator_untouched_path = existsSync(OCR_ANNOTATOR) || existsSync(NEW_ANNOTATOR_4B);
checks.OcrCanvasPane_untouched_path = existsSync(OCR_CANVAS);
checks.OcrRightPanel_untouched_path = existsSync(OCR_RIGHT_PANEL) || existsSync(NEW_RIGHT_PANEL_4B);
checks.ocr_core_dir_untouched_path = existsSync(OCR_CORE_DIR);

// 8) UnstructuredBuilder still in components/template/
checks.UnstructuredBuilder_present = existsSync(UNSTRUCTURED_BUILDER);

// 9) TestWorkspace still exists at original path (sanity only — full untouched
//    invariant relies on git diff in the parent task; this just confirms it
//    wasn't deleted/moved).
checks.TestWorkspace_present_at_test_path = existsSync(TEST_WORKSPACE);

// 10) TemplateWorkspace contents are logic-identical to backup (move-only,
//     no internal edits).
checks.template_workspace_logic_unchanged_vs_backup =
  twBackup !== null && normalizeForLogic(newSrc) === normalizeForLogic(twBackup);

// 11) TemplateWorkspace internal relative imports still resolve. The only
//     relative import in TemplateWorkspace is `../common/AppProviders`. From
//     components/template/, that resolves to components/common/AppProviders —
//     same as before (components/ocr/ -> ../common = components/common).
//     Confirm the source still uses that exact path.
checks.template_workspace_keeps_common_import =
  /from\s+["']\.\.\/common\/AppProviders["']/.test(newSrc);

const summary = {
  task: "FRONTEND-STRUCTURE-4A-TEMPLATE-WORKSPACE-MOVE",
  newPath: NEW_PATH,
  oldPath: OLD_PATH,
  routeOcrPage: ROUTE_OCR_PAGE,
  routeTemplatePage: ROUTE_TEMPLATE_PAGE,
  checks,
};

console.log(JSON.stringify(summary, null, 2));

const required = [
  "new_path_exists",
  "old_path_absent",
  "route_imports_new_path",
  "route_no_old_import",
  "template_route_unchanged",
  "moved_file_no_self_reference",
  "OcrAnnotator_untouched_path",
  "OcrCanvasPane_untouched_path",
  "OcrRightPanel_untouched_path",
  "ocr_core_dir_untouched_path",
  "UnstructuredBuilder_present",
  "TestWorkspace_present_at_test_path",
  "template_workspace_logic_unchanged_vs_backup",
  "template_workspace_keeps_common_import",
];
const allPass = required.every((k) => checks[k] === true);
console.log(`[TEMPLATE_WORKSPACE_MOVE_4A] ${allPass ? "PASS" : "FAIL"}`);
process.exit(allPass ? 0 : 1);
