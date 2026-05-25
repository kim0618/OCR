#!/usr/bin/env node
// LIB_CLEAN_1_THEME_MOVE
// Static check: confirm src/lib/theme.ts was moved to
// src/components/layout/utils/theme.ts. Body must be logic-identical to
// the LC-1 backup (only the single Header.tsx import path changes).
// theme.ts is a React hook (useTheme) so the new location must keep
// React allowed; only components/* imports beyond what was already there
// are flagged.
//
// Read-only. No production code is modified.

import { readFileSync, existsSync, readdirSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, "..");

const NEW_THEME = resolve(ROOT, "src/components/layout/utils/theme.ts");
const OLD_THEME = resolve(ROOT, "src/lib/theme.ts");

const HEADER = resolve(ROOT, "src/components/layout/Header.tsx");

const LIB_DIR = resolve(ROOT, "src/lib");
// LC-1 must NOT move any other src/lib/* file. Later LIB-CLEAN steps may
// legitimately move additional files, so this historical check keeps only
// the files that still remain after LC-2.
const SIBLINGS_THAT_MUST_STAY_IN_LIB = [
  // NOTE: autofillEngine.ts removed after LIB-CLEAN-4F (moved to src/common/utils/).
  // NOTE: profiles.ts removed after LIB-CLEAN-4D (moved to src/components/test/utils/).
  // NOTE: testsets.ts removed after LIB-CLEAN-4C (moved to src/common/config/).
];
const LOGIN_STORAGE = resolve(ROOT, "src/common/storage/login.ts");
const AXIOS_API = resolve(ROOT, "src/common/api/axios.ts");

const TEST_WORKSPACE = resolve(ROOT, "src/components/test/TestWorkspace.tsx");
const TEST_CORE_DIR = resolve(ROOT, "src/components/test/core");

const BACKUP_DIR = resolve(
  ROOT,
  "backup",
  "theme_layout_utils_20260522_before_LIB_CLEAN_1_THEME_MOVE",
);
const THEME_BACKUP = resolve(BACKUP_DIR, "theme.ts");
const HEADER_BACKUP = resolve(BACKUP_DIR, "Header.tsx");

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
checks.new_theme_exists = existsSync(NEW_THEME);
checks.old_theme_absent = !existsSync(OLD_THEME);

// 2) Sibling src/lib files MUST still be in src/lib (LC-1 only moves theme).
for (const name of SIBLINGS_THAT_MUST_STAY_IN_LIB) {
  const k = `lib_sibling_${name.replace(/\./g, "_")}_still_in_src_lib`;
  checks[k] = existsSync(resolve(LIB_DIR, name));
}
checks.login_moved_to_common_storage_or_still_in_src_lib =
  existsSync(LOGIN_STORAGE) || existsSync(resolve(LIB_DIR, "login.ts"));
checks.axios_moved_to_common_api_or_still_in_src_lib =
  existsSync(AXIOS_API) || existsSync(resolve(LIB_DIR, "axios.ts"));

// 3) TestWorkspace + test/core untouched (LC-1 does not change test area).
checks.TestWorkspace_present = existsSync(TEST_WORKSPACE);
checks.test_core_dir_present = existsSync(TEST_CORE_DIR);

// 4) New theme.ts purity:
//    - export useTheme preserved
//    - imports only react (the original file imports nothing else)
//    - no components/* import
const newThemeSrc = readSafe(NEW_THEME);
checks.new_theme_useTheme_export_preserved =
  newThemeSrc !== null && /export\s+function\s+useTheme\b/.test(newThemeSrc);
checks.new_theme_imports_react_only =
  newThemeSrc !== null &&
  /from\s+["']react["']/.test(newThemeSrc) &&
  !/from\s+["'][^"']*\/components\//.test(newThemeSrc) &&
  !/from\s+["']@\/(?!common|components\/layout)/.test(stripComments(newThemeSrc));
checks.new_theme_no_components_import_outside_self =
  newThemeSrc !== null && !/from\s+["'][^"']*\/components\//.test(newThemeSrc);
checks.new_theme_storage_key_preserved =
  newThemeSrc !== null && /["']mysuit_ocr_theme["']/.test(newThemeSrc);

// 5) Logic equivalence vs backup (import-strip normalization).
function compareBackup(name, cur, backup, backupPath) {
  if (backup === null) {
    skippedBackupChecks.push({ check: name, reason: `SKIP_WITH_REASON: backup not found: ${backupPath}` });
    return cur !== null;
  }
  return cur !== null && backup !== null &&
    normalizeImportInsensitive(cur) === normalizeImportInsensitive(backup);
}
checks.new_theme_logic_unchanged_vs_backup = compareBackup(
  "new_theme_logic_unchanged_vs_backup", newThemeSrc, readSafe(THEME_BACKUP), THEME_BACKUP,
);

// 6) Header.tsx imports new path; no @/lib/theme; body logic-equivalent vs backup.
const headerSrc = readSafe(HEADER);
checks.header_imports_new_path =
  headerSrc !== null &&
  (/from\s+["']\.\/utils\/theme["']/.test(headerSrc) ||
    /from\s+["']@\/components\/layout\/utils\/theme["']/.test(headerSrc)) &&
  !/from\s+["']@\/lib\/theme["']/.test(stripComments(headerSrc)) &&
  !/from\s+["']\.\.\/lib\/theme["']/.test(stripComments(headerSrc)) &&
  !/from\s+["']\.\.\/\.\.\/lib\/theme["']/.test(stripComments(headerSrc));
checks.header_logic_unchanged_vs_backup = compareBackup(
  "header_logic_unchanged_vs_backup", headerSrc, readSafe(HEADER_BACKUP), HEADER_BACKUP,
);

// 7) No residual @/lib/theme / ../lib/theme / ../../lib/theme in src code.
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
  /from\s+["']@\/lib\/theme["']/,
  /from\s+["']\.\.\/lib\/theme["']/,
  /from\s+["']\.\.\/\.\.\/lib\/theme["']/,
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
checks.no_residual_lib_theme_imports_in_code = residuals.length === 0;

const summary = {
  task: "LIB-CLEAN-1-THEME-MOVE",
  paths: {
    new_theme: NEW_THEME,
    old_theme: OLD_THEME,
    header: HEADER,
  },
  checks,
  skippedBackupChecks,
  residuals,
};
console.log(JSON.stringify(summary, null, 2));

const required = [
  "new_theme_exists",
  "old_theme_absent",
  ...SIBLINGS_THAT_MUST_STAY_IN_LIB.map((n) => `lib_sibling_${n.replace(/\./g, "_")}_still_in_src_lib`),
  "login_moved_to_common_storage_or_still_in_src_lib",
  "axios_moved_to_common_api_or_still_in_src_lib",
  "TestWorkspace_present",
  "test_core_dir_present",
  "new_theme_useTheme_export_preserved",
  "new_theme_imports_react_only",
  "new_theme_no_components_import_outside_self",
  "new_theme_storage_key_preserved",
  "new_theme_logic_unchanged_vs_backup",
  "header_imports_new_path",
  "header_logic_unchanged_vs_backup",
  "no_residual_lib_theme_imports_in_code",
];
const allPass = required.every((k) => checks[k] === true);
const verdict = allPass
  ? (skippedBackupChecks.length > 0 ? "PASS_WITH_SKIPPED_BACKUP" : "PASS")
  : "FAIL";
console.log(`[THEME_LAYOUT_UTILS_MOVE_LC1] ${verdict}`);
process.exit(allPass ? 0 : 1);
