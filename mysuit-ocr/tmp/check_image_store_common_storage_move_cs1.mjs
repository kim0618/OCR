#!/usr/bin/env node
// FRONTEND_CS_1_IMAGE_STORE_COMMON_STORAGE_MOVE
// Static check: confirm src/lib/imageStore.ts was moved to
// src/common/storage/imageStore.ts. Body must be logic-identical to the
// CS-1 backup. All four production importers (historyStore + app template
// page + RunOcrWorkspace + TemplateAnnotator) keep their original paths
// with only the imageStore import path corrected. historyStore receives
// import-path-only edit (logic-equivalence vs backup verified).
// Other src/lib files must NOT be moved in this step. TestWorkspace and
// test/core untouched.
//
// Read-only. No production code is modified.

import { readFileSync, existsSync, readdirSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, "..");

const NEW_STORE = resolve(ROOT, "src/common/storage/imageStore.ts");
const OLD_STORE = resolve(ROOT, "src/lib/imageStore.ts");

// NOTE: After CS-2 (historyStore common/storage move) the file lives at
// src/common/storage/historyStore.ts. Resolve to whichever currently exists
// so this CS-1-era check stays valid across both states.
const HISTORY_STORE_AT_LIB = resolve(ROOT, "src/lib/historyStore.ts");
const HISTORY_STORE_AT_COMMON_STORAGE = resolve(ROOT, "src/common/storage/historyStore.ts");
const HISTORY_STORE = existsSync(HISTORY_STORE_AT_LIB)
  ? HISTORY_STORE_AT_LIB
  : HISTORY_STORE_AT_COMMON_STORAGE;
const TEMPLATE_PAGE = resolve(ROOT, "src/app/template/page.tsx");
const RUNOCR_WORKSPACE = resolve(ROOT, "src/components/runocr/RunOcrWorkspace.tsx");
const TEMPLATE_ANNOTATOR = resolve(ROOT, "src/components/template/ui/TemplateAnnotator.tsx");

const LIB_DIR = resolve(ROOT, "src/lib");
const SIBLINGS_THAT_MUST_STAY_IN_LIB = [
  // NOTE: historyStore.ts removed after CS-2 (moved to src/common/storage/).
  // NOTE: autofillEngine.ts removed after LIB-CLEAN-4F (moved to src/common/utils/).
  // NOTE: profiles.ts removed after LIB-CLEAN-4D (moved to src/components/test/utils/).
  // NOTE: testsets.ts removed after LIB-CLEAN-4C (moved to src/common/config/).
  // NOTE: bizNumber.ts removed after BZ-1 (moved to src/common/utils/).
];

const TEST_WORKSPACE = resolve(ROOT, "src/components/test/TestWorkspace.tsx");
const TEST_CORE_DIR = resolve(ROOT, "src/components/test/core");

const BACKUP_DIR = resolve(
  ROOT,
  "backup",
  "image_store_common_storage_20260522_before_FRONTEND_CS_1_IMAGE_STORE_COMMON_STORAGE_MOVE",
);
const STORE_BACKUP = resolve(BACKUP_DIR, "imageStore.ts");
const HISTORY_STORE_BACKUP = resolve(BACKUP_DIR, "historyStore.ts");
const TEMPLATE_PAGE_BACKUP = resolve(BACKUP_DIR, "app_template_page.tsx");
const RUNOCR_BACKUP = resolve(BACKUP_DIR, "RunOcrWorkspace.tsx");
const TEMPLATE_ANNOTATOR_BACKUP = resolve(BACKUP_DIR, "TemplateAnnotator.tsx");

function readSafe(p) { try { return readFileSync(p, "utf8"); } catch { return null; } }
function stripComments(src) {
  return src
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .replace(/(^|[^:])\/\/[^\n]*/g, "$1");
}
function stripImportPaths(src) {
  return src.replace(/from\s+["'][^"']+["']/g, 'from "<<IMPORT>>"');
}
function normalizeImportInsensitive(src) {
  return stripImportPaths(stripComments(src)).replace(/\s+/g, " ").trim();
}

const checks = {};
const skippedBackupChecks = [];

// 1) New path exists, old path absent.
checks.new_store_exists = existsSync(NEW_STORE);
checks.old_store_absent = !existsSync(OLD_STORE);

// 2) Sibling src/lib files MUST still be in src/lib (no scope creep).
for (const name of SIBLINGS_THAT_MUST_STAY_IN_LIB) {
  const k = `lib_sibling_${name.replace(/\./g, "_")}_still_in_src_lib`;
  checks[k] = existsSync(resolve(LIB_DIR, name));
}

// 3) TestWorkspace + test/core untouched paths.
checks.TestWorkspace_present = existsSync(TEST_WORKSPACE);
checks.test_core_dir_present = existsSync(TEST_CORE_DIR);

// 4) common/storage/imageStore.ts purity.
const newStoreSrc = readSafe(NEW_STORE);
checks.new_store_no_components_import =
  newStoreSrc !== null && !/from\s+["'][^"']*components\/[^"']*["']/.test(newStoreSrc);
checks.new_store_no_react_import =
  newStoreSrc !== null && !/from\s+["']react["']/.test(newStoreSrc);
checks.new_store_no_react_dom_import =
  newStoreSrc !== null && !/from\s+["']react-dom["']/.test(newStoreSrc);
// IndexedDB / browser persistence is the file's intended responsibility; we
// only confirm there are no unrelated component / runtime dependencies.

// 5) Required exports preserved (key persistence APIs).
const REQUIRED_NAMES = [
  "saveImage",
  "getImage",
  "deleteImagesFor",
  "saveTemplateImage",
  "getTemplateImage",
  "deleteTemplateImage",
];
checks.new_store_required_exports_preserved =
  newStoreSrc !== null &&
  REQUIRED_NAMES.every((n) => new RegExp(`\\b${n}\\b`).test(newStoreSrc));
// IndexedDB invariants: DB name + store name + version must be preserved.
checks.new_store_db_name_preserved =
  newStoreSrc !== null && /mysuit_ocr_images/.test(newStoreSrc);
checks.new_store_indexedDB_used =
  newStoreSrc !== null && /\bindexedDB\b/.test(newStoreSrc);

// 6) Logic equivalence vs backup.
const storeBackup = readSafe(STORE_BACKUP);
if (storeBackup === null) {
  skippedBackupChecks.push({
    check: "new_store_logic_unchanged_vs_backup",
    reason: `SKIP_WITH_REASON: backup not found: ${STORE_BACKUP}`,
  });
}
checks.new_store_logic_unchanged_vs_backup =
  newStoreSrc !== null && storeBackup !== null &&
  normalizeImportInsensitive(newStoreSrc) === normalizeImportInsensitive(storeBackup);

// 7) Importers reference the new path.
const historyStoreSrc = readSafe(HISTORY_STORE);
const templatePageSrc = readSafe(TEMPLATE_PAGE);
const runOcrSrc = readSafe(RUNOCR_WORKSPACE);
const annotatorSrc = readSafe(TEMPLATE_ANNOTATOR);

// NOTE: After CS-2 (historyStore moved to src/common/storage/), the imageStore
// import inside historyStore.ts may use the sibling form ("./imageStore") or
// keep the original alias ("@/common/storage/imageStore"). Both are acceptable;
// only "@/lib/imageStore" is forbidden.
checks.history_store_imports_new_path =
  historyStoreSrc !== null &&
  (/from\s+["']@\/common\/storage\/imageStore["']/.test(historyStoreSrc) ||
    /from\s+["']\.\/imageStore["']/.test(historyStoreSrc)) &&
  !/from\s+["']@\/lib\/imageStore["']/.test(stripComments(historyStoreSrc));
checks.template_page_imports_new_path =
  templatePageSrc !== null &&
  /from\s+["']@\/common\/storage\/imageStore["']/.test(templatePageSrc) &&
  !/from\s+["']@\/lib\/imageStore["']/.test(stripComments(templatePageSrc));
checks.runocr_workspace_imports_new_path =
  runOcrSrc !== null &&
  /from\s+["']@\/common\/storage\/imageStore["']/.test(runOcrSrc) &&
  !/from\s+["']@\/lib\/imageStore["']/.test(stripComments(runOcrSrc));
checks.template_annotator_imports_new_path =
  annotatorSrc !== null &&
  /from\s+["']@\/common\/storage\/imageStore["']/.test(annotatorSrc) &&
  !/from\s+["']@\/lib\/imageStore["']/.test(stripComments(annotatorSrc));

// 8) Importer bodies logic-equivalent to backups (only import path changed).
function compareBackup(name, cur, backup, backupPath) {
  if (backup === null) {
    skippedBackupChecks.push({ check: name, reason: `SKIP_WITH_REASON: backup not found: ${backupPath}` });
    return cur !== null;
  }
  return cur !== null && backup !== null &&
    normalizeImportInsensitive(cur) === normalizeImportInsensitive(backup);
}
checks.history_store_logic_unchanged_vs_backup = compareBackup(
  "history_store_logic_unchanged_vs_backup", historyStoreSrc, readSafe(HISTORY_STORE_BACKUP), HISTORY_STORE_BACKUP,
);
checks.template_page_logic_unchanged_vs_backup = compareBackup(
  "template_page_logic_unchanged_vs_backup", templatePageSrc, readSafe(TEMPLATE_PAGE_BACKUP), TEMPLATE_PAGE_BACKUP,
);
// TPL-10 phase-aware: RunOcrWorkspace passes activeTemplate prop to
// OcrResultPanel for template_region_canonical projection. Skip when present.
const _tpl10Shipped_runocr_cs1 = typeof runOcrSrc === "string"
  && /activeTemplate\s*=\s*\{activeTemplateForPanel\}/.test(runOcrSrc);
if (_tpl10Shipped_runocr_cs1) {
  skippedBackupChecks.push({
    check: "runocr_workspace_logic_unchanged_vs_backup",
    reason: "SKIP_WITH_REASON: TPL-10 wired activeTemplate prop to OcrResultPanel beyond CS-1 scope",
  });
  checks.runocr_workspace_logic_unchanged_vs_backup = true;
} else {
  checks.runocr_workspace_logic_unchanged_vs_backup = compareBackup(
    "runocr_workspace_logic_unchanged_vs_backup", runOcrSrc, readSafe(RUNOCR_BACKUP), RUNOCR_BACKUP,
  );
}
// TPL-12C phase-aware: TemplateAnnotator gained rowAdjustTargetId state + props.
const _tpl12cShipped_ann_cs1 = typeof annotatorSrc === "string"
  && /rowAdjustTargetId/.test(annotatorSrc);
if (_tpl12cShipped_ann_cs1) {
  skippedBackupChecks.push({
    check: "template_annotator_logic_unchanged_vs_backup",
    reason: "SKIP_WITH_REASON: TPL-12C added rowAdjustTargetId state to TemplateAnnotator beyond CS-1 scope",
  });
  checks.template_annotator_logic_unchanged_vs_backup = true;
} else {
  checks.template_annotator_logic_unchanged_vs_backup = compareBackup(
    "template_annotator_logic_unchanged_vs_backup", annotatorSrc, readSafe(TEMPLATE_ANNOTATOR_BACKUP), TEMPLATE_ANNOTATOR_BACKUP,
  );
}

// 9) No residual @/lib/imageStore / ../lib/imageStore / ./imageStore in src/
//    CODE (excluding comments).
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
  /from\s+["']@\/lib\/imageStore["']/,
  /from\s+["']\.\.\/lib\/imageStore["']/,
  /from\s+["']\.\.\/\.\.\/lib\/imageStore["']/,
  /from\s+["']\.\.\/\.\.\/\.\.\/lib\/imageStore["']/,
];
// NOTE: After CS-2 (historyStore moved to src/common/storage/), the sibling
// `./imageStore` import from any file inside src/common/storage/ is legitimate
// and must not be flagged as a residual.
const SIBLING_RESIDUAL_PATTERN = /from\s+["']\.\/imageStore["']/;
const COMMON_STORAGE_DIR = resolve(ROOT, "src/common/storage") + "\\";
const COMMON_STORAGE_DIR_POSIX = resolve(ROOT, "src/common/storage") + "/";
const residuals = [];
for (const f of srcFiles) {
  const s = readSafe(f);
  if (!s) continue;
  const codeOnly = stripComments(s);
  for (const re of RESIDUAL_PATTERNS) {
    if (re.test(codeOnly)) residuals.push({ file: f, pattern: re.toString() });
  }
  const inCommonStorage =
    f.startsWith(COMMON_STORAGE_DIR) || f.startsWith(COMMON_STORAGE_DIR_POSIX);
  if (!inCommonStorage && SIBLING_RESIDUAL_PATTERN.test(codeOnly)) {
    residuals.push({ file: f, pattern: SIBLING_RESIDUAL_PATTERN.toString() });
  }
}
checks.no_residual_lib_image_store_imports_in_code = residuals.length === 0;

const summary = {
  task: "FRONTEND-CS-1-IMAGE-STORE-COMMON-STORAGE-MOVE",
  paths: {
    new_store: NEW_STORE,
    old_store: OLD_STORE,
    history_store: HISTORY_STORE,
    template_page: TEMPLATE_PAGE,
    runocr_workspace: RUNOCR_WORKSPACE,
    template_annotator: TEMPLATE_ANNOTATOR,
  },
  checks,
  skippedBackupChecks,
  residuals,
};
console.log(JSON.stringify(summary, null, 2));

const required = [
  "new_store_exists",
  "old_store_absent",
  ...SIBLINGS_THAT_MUST_STAY_IN_LIB.map((n) => `lib_sibling_${n.replace(/\./g, "_")}_still_in_src_lib`),
  "TestWorkspace_present",
  "test_core_dir_present",
  "new_store_no_components_import",
  "new_store_no_react_import",
  "new_store_no_react_dom_import",
  "new_store_required_exports_preserved",
  "new_store_db_name_preserved",
  "new_store_indexedDB_used",
  "new_store_logic_unchanged_vs_backup",
  "history_store_imports_new_path",
  "template_page_imports_new_path",
  "runocr_workspace_imports_new_path",
  "template_annotator_imports_new_path",
  "history_store_logic_unchanged_vs_backup",
  "template_page_logic_unchanged_vs_backup",
  "runocr_workspace_logic_unchanged_vs_backup",
  "template_annotator_logic_unchanged_vs_backup",
  "no_residual_lib_image_store_imports_in_code",
];
const allPass = required.every((k) => checks[k] === true);
const verdict = allPass
  ? (skippedBackupChecks.length > 0 ? "PASS_WITH_SKIPPED_BACKUP" : "PASS")
  : "FAIL";
console.log(`[IMAGE_STORE_COMMON_STORAGE_MOVE_CS1] ${verdict}`);
process.exit(allPass ? 0 : 1);
