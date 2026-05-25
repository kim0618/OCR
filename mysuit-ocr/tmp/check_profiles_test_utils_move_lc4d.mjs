#!/usr/bin/env node
// LIB-CLEAN-4D PROFILES TEST/UTILS MOVE
// Static check: confirm src/lib/profiles.ts was moved to
// src/components/test/utils/profiles.ts. Body must be logic-identical to
// the LC-4D backup (import path strip). TestWorkspace is the sole importer
// and gets a 2-line import-path-only edit. profiles.ts keeps its
// @/common/config/testsets type-only import unchanged.
//
// Read-only. No production code is modified.

import { readFileSync, existsSync, readdirSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, "..");

const NEW_PATH = resolve(ROOT, "src/components/test/utils/profiles.ts");
const OLD_PATH = resolve(ROOT, "src/lib/profiles.ts");
const TEST_UTILS_DIR = resolve(ROOT, "src/components/test/utils");

const TEST_WORKSPACE = resolve(ROOT, "src/components/test/TestWorkspace.tsx");
const TEST_CORE_DIR = resolve(ROOT, "src/components/test/core");

const LIB_DIR = resolve(ROOT, "src/lib");
// NOTE: autofillEngine.ts removed after LIB-CLEAN-4F (moved to src/common/utils/).
const EXPECTED_REMAINING_LIB = [];

// Already-moved guard.
const TESTSETS_NEW = resolve(ROOT, "src/common/config/testsets.ts");
const AXIOS_NEW = resolve(ROOT, "src/common/api/axios.ts");
const LOGIN_NEW = resolve(ROOT, "src/common/storage/login.ts");
const GROUND_TRUTH_NEW = resolve(ROOT, "src/common/storage/groundTruthStore.ts");
const RESTORE_PROFILE_NEW = resolve(ROOT, "src/common/storage/restoreProfileStore.ts");
const THEME_NEW = resolve(ROOT, "src/components/layout/utils/theme.ts");
const TESTSETS_OLD = resolve(ROOT, "src/lib/testsets.ts");
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
  "profiles_test_utils_20260522_before_LIB_CLEAN_4D_PROFILES_TEST_UTILS_MOVE",
);
const PROFILES_BACKUP = resolve(BACKUP_DIR, "profiles.ts");
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
checks.test_utils_dir_exists = existsSync(TEST_UTILS_DIR);

// 2) Already-moved targets in expected new homes; src/lib old paths absent.
checks.testsets_in_common_config = existsSync(TESTSETS_NEW);
checks.axios_in_common_api = existsSync(AXIOS_NEW);
checks.login_in_common_storage = existsSync(LOGIN_NEW);
checks.ground_truth_in_common_storage = existsSync(GROUND_TRUTH_NEW);
checks.restore_profile_in_common_storage = existsSync(RESTORE_PROFILE_NEW);
checks.theme_in_components_layout_utils = existsSync(THEME_NEW);
checks.testsets_absent_in_src_lib = !existsSync(TESTSETS_OLD);
checks.axios_absent_in_src_lib = !existsSync(AXIOS_OLD);
checks.login_absent_in_src_lib = !existsSync(LOGIN_OLD);
checks.ground_truth_absent_in_src_lib = !existsSync(GROUND_TRUTH_OLD);
checks.restore_profile_absent_in_src_lib = !existsSync(RESTORE_PROFILE_OLD);
checks.theme_absent_in_src_lib = !existsSync(THEME_OLD);

// 3) src/lib remaining set is exactly the expected 1 file.
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

// 5) profiles.ts purity at new location.
const newSrc = readSafe(NEW_PATH);
checks.new_path_no_components_import =
  newSrc !== null && !/from\s+["'][^"']*components\/[^"']*["']/.test(newSrc);
checks.new_path_no_react_import =
  newSrc !== null && !/from\s+["']react["']/.test(newSrc);
checks.new_path_no_react_dom_import =
  newSrc !== null && !/from\s+["']react-dom["']/.test(newSrc);
// Tightened: only flag actual browser-API member access / call sites, not
// string literals like Profile = "document". profiles.ts uses "document" /
// "none" as profile name literals — those are NOT browser API references.
{
  const codeOnly = stripComments(newSrc ?? "");
  checks.new_path_no_browser_api =
    newSrc !== null &&
    !/\bwindow\./.test(codeOnly) &&
    !/\bdocument\./.test(codeOnly) &&
    !/\blocalStorage\./.test(codeOnly) &&
    !/\bsessionStorage\./.test(codeOnly) &&
    !/\bindexedDB\./.test(codeOnly) &&
    !/\bnavigator\./.test(codeOnly) &&
    !/\bfetch\s*\(/.test(codeOnly);
}
checks.new_path_no_backend_or_node_fs_import =
  newSrc !== null &&
  !/from\s+["'](?:node:)?(?:fs|fs\/promises|path)["']/.test(newSrc) &&
  !/from\s+["'][^"']*backend[^"']*["']/.test(newSrc);
checks.new_path_no_at_lib_import =
  newSrc !== null && !/from\s+["']@\/lib\/[^"']+["']/.test(newSrc);
checks.new_path_no_old_sibling_testsets_import =
  newSrc !== null &&
  !/from\s+["']\.\/testsets["']/.test(newSrc) &&
  !/from\s+["']@\/lib\/testsets["']/.test(newSrc);
checks.new_path_keeps_common_config_testsets_import =
  newSrc !== null && /from\s+["']@\/common\/config\/testsets["']/.test(newSrc);
checks.new_path_no_storage_or_api_import =
  newSrc !== null &&
  !/from\s+["']@\/common\/storage\/[^"']+["']/.test(newSrc) &&
  !/from\s+["']@\/common\/api\/[^"']+["']/.test(newSrc);

// 6) Required exports preserved (sample: representative APIs consumed by
//    TestWorkspace + the public policy surface listed in the precheck).
const REQUIRED_EXPORTS = [
  "Profile",
  "Overlay",
  "ProfileResolution",
  "ReceiptFieldKey",
  "FinanceFieldKey",
  "DocumentFieldKey",
  "AnyFieldKey",
  "FINANCE_TIER1_FIELDS",
  "FINANCE_TIER2_FIELDS",
  "DOCUMENT_PARTY_FIELDS",
  "RECEIPT_COLUMNS",
  "FINANCE_COLUMNS",
  "DOCUMENT_COLUMNS",
  "resolveProfile",
  "getBaseColumns",
  "getOverlayColumns",
  "getVisibleColumns",
  "isNotApplicableField",
  "isFinanceTier1",
  "isProfileMismatchSuspected",
  "KpiFamily",
  "resolveKpiFamily",
  "TableColumnKey",
  "GridModeRecommendation",
  "TableColumnMeta",
  "TABLE_COLUMN_META",
  "TableProfilePolicyResult",
  "getExpectedTableColumns",
  "TableRowsValidation",
];
checks.new_path_required_exports_preserved =
  newSrc !== null &&
  REQUIRED_EXPORTS.every((n) =>
    new RegExp(`export\\s+(?:function|type|const|interface|async\\s+function)\\s+${n}\\b`).test(newSrc),
  );

// 7) Logic equivalence vs backup (import strip — only `./testsets` →
//    `@/common/config/testsets` was already done in LC-4C, so the LC-4D
//    move itself adds NO new import edit; the file is byte-equivalent
//    even before strip).
function compareBackup(name, cur, backup, backupPath) {
  if (backup === null) {
    skippedBackupChecks.push({ check: name, reason: `SKIP_WITH_REASON: backup not found: ${backupPath}` });
    return cur !== null;
  }
  return cur !== null && backup !== null &&
    normalizeImportInsensitive(cur) === normalizeImportInsensitive(backup);
}
checks.new_path_logic_unchanged_vs_backup = compareBackup(
  "new_path_logic_unchanged_vs_backup", newSrc, readSafe(PROFILES_BACKUP), PROFILES_BACKUP,
);

// 8) TestWorkspace imports the new path; old path absent in code.
const tsxSrc = readSafe(TEST_WORKSPACE);
checks.test_workspace_imports_new_path =
  tsxSrc !== null &&
  /from\s+["']@\/components\/test\/utils\/profiles["']/.test(tsxSrc) &&
  !/from\s+["']@\/lib\/profiles["']/.test(stripComments(tsxSrc));

// 9) TestWorkspace body logic-equivalent to backup (import path-only edit).
checks.test_workspace_logic_unchanged_vs_backup = compareBackup(
  "test_workspace_logic_unchanged_vs_backup", tsxSrc, readSafe(TEST_WORKSPACE_BACKUP), TEST_WORKSPACE_BACKUP,
);

// 10) No residual @/lib/profiles, ../lib/profiles, ../../lib/profiles in src code.
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
  /from\s+["']@\/lib\/profiles["']/,
  /from\s+["']\.\.\/lib\/profiles["']/,
  /from\s+["']\.\.\/\.\.\/lib\/profiles["']/,
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
checks.no_residual_lib_profiles_imports_in_code = residuals.length === 0;

const summary = {
  task: "LIB-CLEAN-4D-PROFILES-TEST-UTILS-MOVE",
  paths: {
    new_path: NEW_PATH,
    old_path: OLD_PATH,
    test_utils_dir: TEST_UTILS_DIR,
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
  "test_utils_dir_exists",
  "testsets_in_common_config",
  "axios_in_common_api",
  "login_in_common_storage",
  "ground_truth_in_common_storage",
  "restore_profile_in_common_storage",
  "theme_in_components_layout_utils",
  "testsets_absent_in_src_lib",
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
  "new_path_no_old_sibling_testsets_import",
  "new_path_keeps_common_config_testsets_import",
  "new_path_no_storage_or_api_import",
  "new_path_required_exports_preserved",
  "new_path_logic_unchanged_vs_backup",
  "test_workspace_imports_new_path",
  "test_workspace_logic_unchanged_vs_backup",
  "no_residual_lib_profiles_imports_in_code",
];
const allPass = required.every((k) => checks[k] === true);
const verdict = allPass
  ? (skippedBackupChecks.length > 0 ? "PASS_WITH_SKIPPED_BACKUP" : "PASS")
  : "FAIL";
console.log(`[PROFILES_TEST_UTILS_MOVE_LC4D] ${verdict}`);
process.exit(allPass ? 0 : 1);
