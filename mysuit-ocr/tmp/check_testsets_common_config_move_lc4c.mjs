#!/usr/bin/env node
// LIB-CLEAN-4C TESTSETS COMMON/CONFIG MOVE
// Static check: confirm src/lib/testsets.ts was moved to
// src/common/config/testsets.ts. Body must be logic-identical to the LC-4C
// backup. Six importers (profiles + 4 SSR API routes + TestWorkspace) get
// import-path-only edits. The new src/common/config/ directory is the first
// occupant of the common/config domain. testsets.ts is a pure data/types
// module: no React, no DOM, no storage, no fetch, no components/* import.
//
// Read-only. No production code is modified.

import { readFileSync, existsSync, readdirSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, "..");

const NEW_PATH = resolve(ROOT, "src/common/config/testsets.ts");
const OLD_PATH = resolve(ROOT, "src/lib/testsets.ts");
const COMMON_CONFIG_DIR = resolve(ROOT, "src/common/config");

// NOTE: After LIB-CLEAN-4D, profiles.ts lives at
// src/components/test/utils/profiles.ts. Resolve to whichever currently
// exists so this LC-4C-era check stays valid across both states.
const PROFILES_AT_LIB = resolve(ROOT, "src/lib/profiles.ts");
const PROFILES_AT_TEST_UTILS = resolve(ROOT, "src/components/test/utils/profiles.ts");
const PROFILES = existsSync(PROFILES_AT_LIB)
  ? PROFILES_AT_LIB
  : PROFILES_AT_TEST_UTILS;
const API_AUTOFILL_CACHE = resolve(ROOT, "src/app/api/autofill-cache/route.ts");
const API_GROUND_TRUTH = resolve(ROOT, "src/app/api/ground-truth/route.ts");
const API_OCR_CACHE = resolve(ROOT, "src/app/api/ocr-cache/route.ts");
const API_TEST_IMAGES = resolve(ROOT, "src/app/api/test-images/route.ts");
const TEST_WORKSPACE = resolve(ROOT, "src/components/test/TestWorkspace.tsx");
const TEST_CORE_DIR = resolve(ROOT, "src/components/test/core");

const LIB_DIR = resolve(ROOT, "src/lib");
// NOTE: profiles.ts removed after LIB-CLEAN-4D (moved to src/components/test/utils/).
// NOTE: autofillEngine.ts removed after LIB-CLEAN-4F (moved to src/common/utils/).
const EXPECTED_REMAINING_LIB = [];

// Already-moved guard.
const AXIOS_NEW = resolve(ROOT, "src/common/api/axios.ts");
const LOGIN_NEW = resolve(ROOT, "src/common/storage/login.ts");
const GROUND_TRUTH_NEW = resolve(ROOT, "src/common/storage/groundTruthStore.ts");
const RESTORE_PROFILE_NEW = resolve(ROOT, "src/common/storage/restoreProfileStore.ts");
const THEME_NEW = resolve(ROOT, "src/components/layout/utils/theme.ts");
const AXIOS_OLD = resolve(ROOT, "src/lib/axios.ts");
const LOGIN_OLD = resolve(ROOT, "src/lib/login.ts");
const GROUND_TRUTH_OLD = resolve(ROOT, "src/lib/groundTruthStore.ts");
const RESTORE_PROFILE_OLD = resolve(ROOT, "src/lib/restoreProfileStore.ts");
const THEME_OLD = resolve(ROOT, "src/lib/theme.ts");

const AUTORESTORE_WORKSPACE = resolve(ROOT, "src/components/autorestore/AutoRestoreWorkspace.tsx");
const AUTORESTORE_ROUTE = resolve(ROOT, "src/app/autorestore/page.tsx");

const BACKUP_DIR = resolve(
  ROOT,
  "backup",
  "testsets_common_config_20260522_before_LIB_CLEAN_4C_TESTSETS_COMMON_CONFIG_MOVE",
);
const TESTSETS_BACKUP = resolve(BACKUP_DIR, "testsets.ts");
const PROFILES_BACKUP = resolve(BACKUP_DIR, "profiles.ts");
const API_AUTOFILL_BACKUP = resolve(BACKUP_DIR, "api_autofill_cache_route.ts");
const API_GT_BACKUP = resolve(BACKUP_DIR, "api_ground_truth_route.ts");
const API_OCR_BACKUP = resolve(BACKUP_DIR, "api_ocr_cache_route.ts");
const API_TEST_IMAGES_BACKUP = resolve(BACKUP_DIR, "api_test_images_route.ts");
const TEST_WORKSPACE_BACKUP = resolve(BACKUP_DIR, "TestWorkspace.tsx");

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

// 1) New path exists, old path absent, new dir present.
checks.new_path_exists = existsSync(NEW_PATH);
checks.old_path_absent = !existsSync(OLD_PATH);
checks.common_config_dir_exists = existsSync(COMMON_CONFIG_DIR);

// 2) Other already-moved files in expected new homes; their src/lib old paths absent.
checks.axios_in_common_api = existsSync(AXIOS_NEW);
checks.login_in_common_storage = existsSync(LOGIN_NEW);
checks.ground_truth_in_common_storage = existsSync(GROUND_TRUTH_NEW);
checks.restore_profile_in_common_storage = existsSync(RESTORE_PROFILE_NEW);
checks.theme_in_components_layout_utils = existsSync(THEME_NEW);
checks.axios_absent_in_src_lib = !existsSync(AXIOS_OLD);
checks.login_absent_in_src_lib = !existsSync(LOGIN_OLD);
checks.ground_truth_absent_in_src_lib = !existsSync(GROUND_TRUTH_OLD);
checks.restore_profile_absent_in_src_lib = !existsSync(RESTORE_PROFILE_OLD);
checks.theme_absent_in_src_lib = !existsSync(THEME_OLD);

// 3) src/lib remaining set is exactly the expected 2 files.
const libEntries = existsSync(LIB_DIR)
  ? readdirSync(LIB_DIR).filter((n) => !n.startsWith("."))
  : [];
checks.lib_remaining_count_matches = libEntries.length === EXPECTED_REMAINING_LIB.length;
checks.lib_remaining_set_matches =
  EXPECTED_REMAINING_LIB.every((n) => libEntries.includes(n)) &&
  libEntries.every((n) => EXPECTED_REMAINING_LIB.includes(n));

// 4) TestWorkspace + test/core + autorestore route/name unchanged in presence.
checks.TestWorkspace_present = existsSync(TEST_WORKSPACE);
checks.test_core_dir_present = existsSync(TEST_CORE_DIR);
checks.AutoRestoreWorkspace_present = existsSync(AUTORESTORE_WORKSPACE);
checks.autorestore_route_present = existsSync(AUTORESTORE_ROUTE);

// 5) common/config/testsets.ts purity.
const newSrc = readSafe(NEW_PATH);
checks.new_path_no_components_import =
  newSrc !== null && !/from\s+["'][^"']*components\/[^"']*["']/.test(newSrc);
checks.new_path_no_react_import =
  newSrc !== null && !/from\s+["']react["']/.test(newSrc);
checks.new_path_no_react_dom_import =
  newSrc !== null && !/from\s+["']react-dom["']/.test(newSrc);
checks.new_path_no_browser_api =
  newSrc !== null &&
  !/\bwindow\b/.test(newSrc) &&
  !/\bdocument\b/.test(newSrc) &&
  !/\blocalStorage\b/.test(newSrc) &&
  !/\bsessionStorage\b/.test(newSrc) &&
  !/\bindexedDB\b/.test(newSrc) &&
  !/\bnavigator\b/.test(newSrc) &&
  !/\bfetch\b/.test(newSrc);
checks.new_path_no_backend_or_node_fs_import =
  newSrc !== null &&
  !/from\s+["'](?:node:)?(?:fs|fs\/promises|path)["']/.test(newSrc) &&
  !/from\s+["'][^"']*backend[^"']*["']/.test(newSrc);
checks.new_path_no_at_lib_import =
  newSrc !== null && !/from\s+["']@\/lib\/[^"']+["']/.test(newSrc);
checks.new_path_no_storage_or_api_import =
  newSrc !== null &&
  !/from\s+["']@\/common\/storage\/[^"']+["']/.test(newSrc) &&
  !/from\s+["']@\/common\/api\/[^"']+["']/.test(newSrc);
// testsets.ts has no imports — assert that explicitly.
checks.new_path_has_no_imports =
  newSrc !== null && !/^import\b|\bfrom\s+["']/.test(stripComments(newSrc));

// 6) Required exports preserved.
const REQUIRED_EXPORTS = [
  "TestsetMeta",
  "TESTSETS",
  "DATASET_FOLDERS",
  "getTestset",
  "DocumentType",
  "QualityTag",
  "Difficulty",
  "InvoiceSubType",
  "AmountProfile",
  "PartyProfile",
  "TableProfile",
  "InvoiceTableExpectedDisplayColumn",
  "InvoiceProfile",
  "DatasetRole",
  "DatasetStatus",
  "ExpectedStatus",
  "ManifestItem",
  "DatasetManifest",
];
checks.new_path_required_exports_preserved =
  newSrc !== null &&
  REQUIRED_EXPORTS.every((n) =>
    new RegExp(`export\\s+(?:function|type|const|interface|async\\s+function)\\s+${n}\\b`).test(newSrc),
  );

// 7) Dataset IDs preserved (sample list — manifest path policy).
const REQUIRED_DATASET_IDS = [
  "baseline", "baseline_fast", "new_samples", "google", "google_fast",
  "receipt_generalization", "invoice_statement", "tax_invoice",
];
checks.new_path_dataset_ids_preserved =
  newSrc !== null &&
  REQUIRED_DATASET_IDS.every((id) => new RegExp(`id:\\s*["']${id}["']`).test(newSrc));
checks.new_path_dataset_path_prefix_preserved =
  newSrc !== null && /\/data\/testsets\//.test(newSrc);

// 8) Logic equivalence vs backup (import strip; backup file has no imports either).
function compareBackup(name, cur, backup, backupPath) {
  if (backup === null) {
    skippedBackupChecks.push({ check: name, reason: `SKIP_WITH_REASON: backup not found: ${backupPath}` });
    return cur !== null;
  }
  return cur !== null && backup !== null &&
    normalizeImportInsensitive(cur) === normalizeImportInsensitive(backup);
}
checks.new_path_logic_unchanged_vs_backup = compareBackup(
  "new_path_logic_unchanged_vs_backup", newSrc, readSafe(TESTSETS_BACKUP), TESTSETS_BACKUP,
);

// 9) Importers reference the new path and not the old.
const profilesSrc = readSafe(PROFILES);
const apiAutofillSrc = readSafe(API_AUTOFILL_CACHE);
const apiGtSrc = readSafe(API_GROUND_TRUTH);
const apiOcrSrc = readSafe(API_OCR_CACHE);
const apiTestImagesSrc = readSafe(API_TEST_IMAGES);
const testWorkspaceSrc = readSafe(TEST_WORKSPACE);

function checkImporterNewPath(src) {
  if (src === null) return false;
  const codeOnly = stripComments(src);
  return (
    /from\s+["']@\/common\/config\/testsets["']/.test(src) &&
    !/from\s+["']@\/lib\/testsets["']/.test(codeOnly) &&
    !/from\s+["']\.\.\/lib\/testsets["']/.test(codeOnly) &&
    !/from\s+["']\.\.\/\.\.\/lib\/testsets["']/.test(codeOnly) &&
    !/from\s+["']\.\/testsets["']/.test(codeOnly)
  );
}
checks.profiles_imports_new_path = checkImporterNewPath(profilesSrc);
checks.api_autofill_cache_imports_new_path = checkImporterNewPath(apiAutofillSrc);
checks.api_ground_truth_imports_new_path = checkImporterNewPath(apiGtSrc);
checks.api_ocr_cache_imports_new_path = checkImporterNewPath(apiOcrSrc);
checks.api_test_images_imports_new_path = checkImporterNewPath(apiTestImagesSrc);
checks.test_workspace_imports_new_path = checkImporterNewPath(testWorkspaceSrc);

// 10) Importer bodies logic-equivalent to backup (only import path changed).
checks.profiles_logic_unchanged_vs_backup = compareBackup(
  "profiles_logic_unchanged_vs_backup", profilesSrc, readSafe(PROFILES_BACKUP), PROFILES_BACKUP,
);
checks.api_autofill_cache_logic_unchanged_vs_backup = compareBackup(
  "api_autofill_cache_logic_unchanged_vs_backup", apiAutofillSrc, readSafe(API_AUTOFILL_BACKUP), API_AUTOFILL_BACKUP,
);
checks.api_ground_truth_logic_unchanged_vs_backup = compareBackup(
  "api_ground_truth_logic_unchanged_vs_backup", apiGtSrc, readSafe(API_GT_BACKUP), API_GT_BACKUP,
);
checks.api_ocr_cache_logic_unchanged_vs_backup = compareBackup(
  "api_ocr_cache_logic_unchanged_vs_backup", apiOcrSrc, readSafe(API_OCR_BACKUP), API_OCR_BACKUP,
);
checks.api_test_images_logic_unchanged_vs_backup = compareBackup(
  "api_test_images_logic_unchanged_vs_backup", apiTestImagesSrc, readSafe(API_TEST_IMAGES_BACKUP), API_TEST_IMAGES_BACKUP,
);
checks.test_workspace_logic_unchanged_vs_backup = compareBackup(
  "test_workspace_logic_unchanged_vs_backup", testWorkspaceSrc, readSafe(TEST_WORKSPACE_BACKUP), TEST_WORKSPACE_BACKUP,
);

// 11) No residual @/lib/testsets, ../lib/testsets, ../../lib/testsets in src code.
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
  /from\s+["']@\/lib\/testsets["']/,
  /from\s+["']\.\.\/lib\/testsets["']/,
  /from\s+["']\.\.\/\.\.\/lib\/testsets["']/,
];
const residuals = [];
for (const f of srcFiles) {
  const s = readSafe(f);
  if (!s) continue;
  const codeOnly = stripComments(s);
  for (const re of RESIDUAL_PATTERNS) {
    if (re.test(codeOnly)) residuals.push({ file: f, pattern: re.toString() });
  }
}
checks.no_residual_lib_testsets_imports_in_code = residuals.length === 0;

const summary = {
  task: "LIB-CLEAN-4C-TESTSETS-COMMON-CONFIG-MOVE",
  paths: {
    new_path: NEW_PATH,
    old_path: OLD_PATH,
    common_config_dir: COMMON_CONFIG_DIR,
    profiles: PROFILES,
    api_autofill_cache: API_AUTOFILL_CACHE,
    api_ground_truth: API_GROUND_TRUTH,
    api_ocr_cache: API_OCR_CACHE,
    api_test_images: API_TEST_IMAGES,
    test_workspace: TEST_WORKSPACE,
  },
  expected_remaining_lib: EXPECTED_REMAINING_LIB,
  found_in_lib: libEntries,
  checks,
  skippedBackupChecks,
  residuals,
};
console.log(JSON.stringify(summary, null, 2));

const required = [
  "new_path_exists",
  "old_path_absent",
  "common_config_dir_exists",
  "axios_in_common_api",
  "login_in_common_storage",
  "ground_truth_in_common_storage",
  "restore_profile_in_common_storage",
  "theme_in_components_layout_utils",
  "axios_absent_in_src_lib",
  "login_absent_in_src_lib",
  "ground_truth_absent_in_src_lib",
  "restore_profile_absent_in_src_lib",
  "theme_absent_in_src_lib",
  "lib_remaining_count_matches",
  "lib_remaining_set_matches",
  "TestWorkspace_present",
  "test_core_dir_present",
  "AutoRestoreWorkspace_present",
  "autorestore_route_present",
  "new_path_no_components_import",
  "new_path_no_react_import",
  "new_path_no_react_dom_import",
  "new_path_no_browser_api",
  "new_path_no_backend_or_node_fs_import",
  "new_path_no_at_lib_import",
  "new_path_no_storage_or_api_import",
  "new_path_has_no_imports",
  "new_path_required_exports_preserved",
  "new_path_dataset_ids_preserved",
  "new_path_dataset_path_prefix_preserved",
  "new_path_logic_unchanged_vs_backup",
  "profiles_imports_new_path",
  "api_autofill_cache_imports_new_path",
  "api_ground_truth_imports_new_path",
  "api_ocr_cache_imports_new_path",
  "api_test_images_imports_new_path",
  "test_workspace_imports_new_path",
  "profiles_logic_unchanged_vs_backup",
  "api_autofill_cache_logic_unchanged_vs_backup",
  "api_ground_truth_logic_unchanged_vs_backup",
  "api_ocr_cache_logic_unchanged_vs_backup",
  "api_test_images_logic_unchanged_vs_backup",
  "test_workspace_logic_unchanged_vs_backup",
  "no_residual_lib_testsets_imports_in_code",
];
const allPass = required.every((k) => checks[k] === true);
const verdict = allPass
  ? (skippedBackupChecks.length > 0 ? "PASS_WITH_SKIPPED_BACKUP" : "PASS")
  : "FAIL";
console.log(`[TESTSETS_COMMON_CONFIG_MOVE_LC4C] ${verdict}`);
process.exit(allPass ? 0 : 1);
