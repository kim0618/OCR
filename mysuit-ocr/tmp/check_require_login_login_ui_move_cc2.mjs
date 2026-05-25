#!/usr/bin/env node
// FRONTEND_CC_2_REQUIRE_LOGIN_LOGIN_UI_MOVE
// Static check: confirm src/components/common/RequireLogin.tsx was moved to
// src/components/login/ui/RequireLogin.tsx. Body must be logic-identical to
// the CC-2 backup. The two route pages (autorestore/page.tsx, history/page.tsx)
// keep their original paths with only the RequireLogin import path
// corrected. AppProviders.tsx (CC-1 artefact) must remain at
// src/components/layout/AppProviders.tsx and NOT be modified by CC-2.
// TestWorkspace must NOT be modified. src/components/common/ may be empty
// or removed entirely.
//
// Read-only. No production code is modified.

import { readFileSync, existsSync, readdirSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, "..");

const NEW_REQUIRE_LOGIN = resolve(ROOT, "src/components/login/ui/RequireLogin.tsx");
const OLD_REQUIRE_LOGIN = resolve(ROOT, "src/components/common/RequireLogin.tsx");
const OLD_COMMON_DIR = resolve(ROOT, "src/components/common");

const APP_PROVIDERS_LAYOUT = resolve(ROOT, "src/components/layout/AppProviders.tsx");
const APP_PROVIDERS_COMMON = resolve(ROOT, "src/components/common/AppProviders.tsx");

const LOGIN_WORKSPACE = resolve(ROOT, "src/components/login/LoginWorkspace.tsx");

const AUTORESTORE_PAGE = resolve(ROOT, "src/app/autorestore/page.tsx");
const HISTORY_PAGE = resolve(ROOT, "src/app/history/page.tsx");

const TEST_WORKSPACE = resolve(ROOT, "src/components/test/TestWorkspace.tsx");
const TEST_CORE_DIR = resolve(ROOT, "src/components/test/core");

const BACKUP_DIR = resolve(
  ROOT,
  "backup",
  "components_common_require_login_20260522_before_FRONTEND_CC_2_REQUIRE_LOGIN_LOGIN_UI_MOVE",
);
const REQUIRE_LOGIN_BACKUP = resolve(BACKUP_DIR, "RequireLogin.tsx");
const AUTORESTORE_BACKUP = resolve(BACKUP_DIR, "app_autorestore_page.tsx");
const HISTORY_BACKUP = resolve(BACKUP_DIR, "app_history_page.tsx");

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
checks.new_require_login_exists = existsSync(NEW_REQUIRE_LOGIN);
checks.old_require_login_absent = !existsSync(OLD_REQUIRE_LOGIN);

// 2) AppProviders (CC-1 artefact) still at layout, NOT back at common.
checks.AppProviders_still_under_layout = existsSync(APP_PROVIDERS_LAYOUT);
checks.AppProviders_absent_from_common = !existsSync(APP_PROVIDERS_COMMON);

// 3) src/components/common is either removed entirely OR empty after CC-2.
function listFilesIfExists(dir) {
  if (!existsSync(dir)) return null;
  try {
    return readdirSync(dir, { withFileTypes: true })
      .filter((e) => e.isFile())
      .map((e) => e.name);
  } catch { return null; }
}
const remainingCommonFiles = listFilesIfExists(OLD_COMMON_DIR);
checks.components_common_dir_empty_or_removed =
  remainingCommonFiles === null || remainingCommonFiles.length === 0;

// 4) LoginWorkspace still present at its original path (CC-2 did not touch it).
checks.LoginWorkspace_still_present = existsSync(LOGIN_WORKSPACE);

// 5) TestWorkspace + test/core untouched paths.
checks.TestWorkspace_present = existsSync(TEST_WORKSPACE);
checks.test_core_dir_present = existsSync(TEST_CORE_DIR);

// 6) New RequireLogin identity preserved.
const newRequireLoginSrc = readSafe(NEW_REQUIRE_LOGIN);
checks.new_require_login_default_export_preserved =
  newRequireLoginSrc !== null &&
  /export\s+default\s+function\s+RequireLogin\b/.test(newRequireLoginSrc);
// Route guard policy preserved: hasStoredLogin + useRouter + /login redirect.
checks.new_require_login_uses_hasStoredLogin =
  newRequireLoginSrc !== null && /\bhasStoredLogin\b/.test(newRequireLoginSrc);
checks.new_require_login_uses_useRouter =
  newRequireLoginSrc !== null && /\buseRouter\b/.test(newRequireLoginSrc);
checks.new_require_login_redirects_to_login =
  newRequireLoginSrc !== null && /\/login/.test(newRequireLoginSrc);

// 7) Logic equivalence vs backup.
const backupSrc = readSafe(REQUIRE_LOGIN_BACKUP);
if (backupSrc === null) {
  skippedBackupChecks.push({
    check: "new_require_login_logic_unchanged_vs_backup",
    reason: `SKIP_WITH_REASON: backup not found: ${REQUIRE_LOGIN_BACKUP}`,
  });
}
checks.new_require_login_logic_unchanged_vs_backup =
  newRequireLoginSrc !== null && backupSrc !== null &&
  normalizeImportInsensitive(newRequireLoginSrc) === normalizeImportInsensitive(backupSrc);

// 8) Route pages now import the new path.
const autorestoreSrc = readSafe(AUTORESTORE_PAGE);
const historySrc = readSafe(HISTORY_PAGE);

checks.autorestore_page_imports_login_ui_path =
  autorestoreSrc !== null &&
  /from\s+["']@\/components\/login\/ui\/RequireLogin["']/.test(autorestoreSrc) &&
  !/from\s+["']@\/components\/common\/RequireLogin["']/.test(stripComments(autorestoreSrc));
checks.history_page_imports_login_ui_path =
  historySrc !== null &&
  /from\s+["']@\/components\/login\/ui\/RequireLogin["']/.test(historySrc) &&
  !/from\s+["']@\/components\/common\/RequireLogin["']/.test(stripComments(historySrc));

// 9) Route page bodies logic-equivalent to backups (only import path changed).
const autorestoreBackup = readSafe(AUTORESTORE_BACKUP);
const historyBackup = readSafe(HISTORY_BACKUP);

function compareBackup(name, cur, backup, backupPath) {
  if (backup === null) {
    skippedBackupChecks.push({ check: name, reason: `SKIP_WITH_REASON: backup not found: ${backupPath}` });
    return cur !== null;
  }
  return cur !== null && backup !== null &&
    normalizeImportInsensitive(cur) === normalizeImportInsensitive(backup);
}
checks.autorestore_page_logic_unchanged_vs_backup = compareBackup(
  "autorestore_page_logic_unchanged_vs_backup", autorestoreSrc, autorestoreBackup, AUTORESTORE_BACKUP,
);
checks.history_page_logic_unchanged_vs_backup = compareBackup(
  "history_page_logic_unchanged_vs_backup", historySrc, historyBackup, HISTORY_BACKUP,
);

// 10) No residual @/components/common/RequireLogin /
//     ../common/RequireLogin / ../../common/RequireLogin strings in src/ CODE
//     (excluding comments).
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
  /from\s+["']@\/components\/common\/RequireLogin["']/,
  /from\s+["']\.\.\/common\/RequireLogin["']/,
  /from\s+["']\.\.\/\.\.\/common\/RequireLogin["']/,
  /from\s+["']\.\.\/\.\.\/\.\.\/components\/common\/RequireLogin["']/,
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
checks.no_residual_common_require_login_imports_in_code = residuals.length === 0;

const summary = {
  task: "FRONTEND-CC-2-REQUIRE-LOGIN-LOGIN-UI-MOVE",
  paths: {
    new_require_login: NEW_REQUIRE_LOGIN,
    old_require_login: OLD_REQUIRE_LOGIN,
    components_common_dir: OLD_COMMON_DIR,
    remaining_common_files: remainingCommonFiles,
    app_providers_layout: APP_PROVIDERS_LAYOUT,
    autorestore_page: AUTORESTORE_PAGE,
    history_page: HISTORY_PAGE,
  },
  checks,
  skippedBackupChecks,
  residuals,
};
console.log(JSON.stringify(summary, null, 2));

const required = [
  "new_require_login_exists",
  "old_require_login_absent",
  "AppProviders_still_under_layout",
  "AppProviders_absent_from_common",
  "components_common_dir_empty_or_removed",
  "LoginWorkspace_still_present",
  "TestWorkspace_present",
  "test_core_dir_present",
  "new_require_login_default_export_preserved",
  "new_require_login_uses_hasStoredLogin",
  "new_require_login_uses_useRouter",
  "new_require_login_redirects_to_login",
  "new_require_login_logic_unchanged_vs_backup",
  "autorestore_page_imports_login_ui_path",
  "history_page_imports_login_ui_path",
  "autorestore_page_logic_unchanged_vs_backup",
  "history_page_logic_unchanged_vs_backup",
  "no_residual_common_require_login_imports_in_code",
];
const allPass = required.every((k) => checks[k] === true);
const verdict = allPass
  ? (skippedBackupChecks.length > 0 ? "PASS_WITH_SKIPPED_BACKUP" : "PASS")
  : "FAIL";
console.log(`[REQUIRE_LOGIN_LOGIN_UI_MOVE_CC2] ${verdict}`);
process.exit(allPass ? 0 : 1);
