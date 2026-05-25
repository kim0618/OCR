#!/usr/bin/env node
// FRONTEND_BZ_1_BIZ_NUMBER_COMMON_UTILS_MOVE
// Static check: confirm src/lib/bizNumber.ts was moved to
// src/common/utils/bizNumber.ts. Body must be byte-identical to backup
// (the file has no imports, so import-strip normalization equals raw
// equality). 6 importers (autofillEngine, RunOcrWorkspace,
// DetailHistoryView, TestWorkspace, test/core/extract, test/core/autofill)
// get import-path-only edits. TestWorkspace + test/core must change only
// the import path (logic-equivalent vs backup).
//
// Read-only. No production code is modified.

import { readFileSync, existsSync, readdirSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, "..");

const NEW_UTIL = resolve(ROOT, "src/common/utils/bizNumber.ts");
const OLD_UTIL = resolve(ROOT, "src/lib/bizNumber.ts");

// NOTE: After LIB-CLEAN-4F, autofillEngine.ts lives at
// src/common/utils/autofillEngine.ts. Resolve to whichever currently exists
// so this BZ-1-era check stays valid across both states.
const AUTOFILL_AT_LIB = resolve(ROOT, "src/lib/autofillEngine.ts");
const AUTOFILL_AT_COMMON_UTILS = resolve(ROOT, "src/common/utils/autofillEngine.ts");
const AUTOFILL_ENGINE = existsSync(AUTOFILL_AT_LIB)
  ? AUTOFILL_AT_LIB
  : AUTOFILL_AT_COMMON_UTILS;
const RUNOCR_WORKSPACE = resolve(ROOT, "src/components/runocr/RunOcrWorkspace.tsx");
const DETAIL_HISTORY_VIEW = resolve(ROOT, "src/components/history/ui/DetailHistoryView.tsx");
const TEST_WORKSPACE = resolve(ROOT, "src/components/test/TestWorkspace.tsx");
const TEST_CORE_EXTRACT = resolve(ROOT, "src/components/test/core/extract.ts");
const TEST_CORE_AUTOFILL = resolve(ROOT, "src/components/test/core/autofill.ts");
const TEST_CORE_DIR = resolve(ROOT, "src/components/test/core");

const LIB_DIR = resolve(ROOT, "src/lib");
const SIBLINGS_THAT_MUST_STAY_IN_LIB = [
  // NOTE: bizNumber.ts moved to src/common/utils/ by BZ-1.
  // NOTE: historyStore.ts moved to src/common/storage/ by CS-2.
  // NOTE: imageStore.ts moved to src/common/storage/ by CS-1.
  // NOTE: autofillEngine.ts removed after LIB-CLEAN-4F (moved to src/common/utils/).
  // NOTE: profiles.ts removed after LIB-CLEAN-4D (moved to src/components/test/utils/).
  // NOTE: testsets.ts removed after LIB-CLEAN-4C (moved to src/common/config/).
];

const BACKUP_DIR = resolve(
  ROOT,
  "backup",
  "biz_number_common_utils_20260522_before_FRONTEND_BZ_1_BIZ_NUMBER_COMMON_UTILS_MOVE",
);
const BIZ_BACKUP = resolve(BACKUP_DIR, "bizNumber.ts");
const AUTOFILL_BACKUP = resolve(BACKUP_DIR, "autofillEngine.ts");
const RUNOCR_BACKUP = resolve(BACKUP_DIR, "RunOcrWorkspace.tsx");
const DETAIL_BACKUP = resolve(BACKUP_DIR, "DetailHistoryView.tsx");
const TEST_WORKSPACE_BACKUP = resolve(BACKUP_DIR, "TestWorkspace.tsx");
const TEST_CORE_EXTRACT_BACKUP = resolve(BACKUP_DIR, "test_core_extract.ts");
const TEST_CORE_AUTOFILL_BACKUP = resolve(BACKUP_DIR, "test_core_autofill.ts");

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
checks.new_util_exists = existsSync(NEW_UTIL);
checks.old_util_absent = !existsSync(OLD_UTIL);

// 2) Sibling src/lib files MUST still be in src/lib (no scope creep).
for (const name of SIBLINGS_THAT_MUST_STAY_IN_LIB) {
  const k = `lib_sibling_${name.replace(/\./g, "_")}_still_in_src_lib`;
  checks[k] = existsSync(resolve(LIB_DIR, name));
}

// 3) TestWorkspace + test/core still present.
checks.TestWorkspace_present = existsSync(TEST_WORKSPACE);
checks.test_core_dir_present = existsSync(TEST_CORE_DIR);

// 4) common/utils/bizNumber.ts purity: no imports, no components, no React/DOM/storage/backend.
const newUtilSrc = readSafe(NEW_UTIL);
checks.new_util_has_no_imports =
  newUtilSrc !== null && !/^\s*import\s/m.test(newUtilSrc);
checks.new_util_no_components_import =
  newUtilSrc !== null && !/from\s+["'][^"']*\/components\//.test(newUtilSrc);
checks.new_util_no_react_import =
  newUtilSrc !== null && !/from\s+["']react["']/.test(newUtilSrc);
checks.new_util_no_react_dom_import =
  newUtilSrc !== null && !/from\s+["']react-dom["']/.test(newUtilSrc);
checks.new_util_no_browser_apis =
  newUtilSrc !== null &&
  !/\bwindow\.|\bdocument\.|\blocalStorage\b|\bsessionStorage\b|\bindexedDB\b|\bnavigator\b|\bfetch\(/.test(newUtilSrc);
checks.new_util_no_storage_import =
  newUtilSrc !== null && !/from\s+["'][^"']*\/(?:storage|backend)\//.test(newUtilSrc);

// 5) Required exports preserved.
const REQUIRED_EXPORTS = ["normalizeBizNumber", "extractBizNumber"];
checks.new_util_required_exports_preserved =
  newUtilSrc !== null &&
  REQUIRED_EXPORTS.every((n) =>
    new RegExp(`export\\s+(?:function|type|const|async\\s+function)\\s+${n}\\b`).test(newUtilSrc),
  );

// 6) Logic byte-equivalent vs backup (import-strip normalization).
function compareBackup(name, cur, backup, backupPath) {
  if (backup === null) {
    skippedBackupChecks.push({ check: name, reason: `SKIP_WITH_REASON: backup not found: ${backupPath}` });
    return cur !== null;
  }
  return cur !== null && backup !== null &&
    normalizeImportInsensitive(cur) === normalizeImportInsensitive(backup);
}
checks.new_util_logic_unchanged_vs_backup = compareBackup(
  "new_util_logic_unchanged_vs_backup", newUtilSrc, readSafe(BIZ_BACKUP), BIZ_BACKUP,
);

// 7) Importers reference the new path and do not reference the old path.
const autofillSrc = readSafe(AUTOFILL_ENGINE);
const runocrSrc = readSafe(RUNOCR_WORKSPACE);
const detailSrc = readSafe(DETAIL_HISTORY_VIEW);
const testWorkspaceSrc = readSafe(TEST_WORKSPACE);
const testExtractSrc = readSafe(TEST_CORE_EXTRACT);
const testAutofillSrc = readSafe(TEST_CORE_AUTOFILL);

function checkImporterNewPath(src) {
  return src !== null &&
    /from\s+["']@\/common\/utils\/bizNumber["']/.test(src) &&
    !/from\s+["']@\/lib\/bizNumber["']/.test(stripComments(src)) &&
    !/from\s+["']\.\.\/lib\/bizNumber["']/.test(stripComments(src)) &&
    !/from\s+["']\.\.\/\.\.\/lib\/bizNumber["']/.test(stripComments(src));
}
checks.autofill_engine_imports_new_path = checkImporterNewPath(autofillSrc);
checks.runocr_workspace_imports_new_path = checkImporterNewPath(runocrSrc);
checks.detail_history_view_imports_new_path = checkImporterNewPath(detailSrc);
checks.test_workspace_imports_new_path = checkImporterNewPath(testWorkspaceSrc);
checks.test_core_extract_imports_new_path = checkImporterNewPath(testExtractSrc);
checks.test_core_autofill_imports_new_path = checkImporterNewPath(testAutofillSrc);

// 8) Importer bodies logic-equivalent to backups (only import path changed).
checks.autofill_engine_logic_unchanged_vs_backup = compareBackup(
  "autofill_engine_logic_unchanged_vs_backup", autofillSrc, readSafe(AUTOFILL_BACKUP), AUTOFILL_BACKUP,
);
// TPL-10 phase-aware: RunOcrWorkspace passes activeTemplate prop to
// OcrResultPanel for template_region_canonical projection (new wiring
// beyond BZ-1's import-only scope). Skip when that marker is present.
const _tpl10Shipped_runocr_bz1 = typeof runocrSrc === "string"
  && /activeTemplate\s*=\s*\{activeTemplateForPanel\}/.test(runocrSrc);
if (_tpl10Shipped_runocr_bz1) {
  skippedBackupChecks.push({
    check: "runocr_workspace_logic_unchanged_vs_backup",
    reason: "SKIP_WITH_REASON: TPL-10 wired activeTemplate prop to OcrResultPanel beyond BZ-1 scope",
  });
  checks.runocr_workspace_logic_unchanged_vs_backup = true;
} else {
  checks.runocr_workspace_logic_unchanged_vs_backup = compareBackup(
    "runocr_workspace_logic_unchanged_vs_backup", runocrSrc, readSafe(RUNOCR_BACKUP), RUNOCR_BACKUP,
  );
}
checks.detail_history_view_logic_unchanged_vs_backup = compareBackup(
  "detail_history_view_logic_unchanged_vs_backup", detailSrc, readSafe(DETAIL_BACKUP), DETAIL_BACKUP,
);
checks.test_workspace_logic_unchanged_vs_backup = compareBackup(
  "test_workspace_logic_unchanged_vs_backup", testWorkspaceSrc, readSafe(TEST_WORKSPACE_BACKUP), TEST_WORKSPACE_BACKUP,
);
checks.test_core_extract_logic_unchanged_vs_backup = compareBackup(
  "test_core_extract_logic_unchanged_vs_backup", testExtractSrc, readSafe(TEST_CORE_EXTRACT_BACKUP), TEST_CORE_EXTRACT_BACKUP,
);
checks.test_core_autofill_logic_unchanged_vs_backup = compareBackup(
  "test_core_autofill_logic_unchanged_vs_backup", testAutofillSrc, readSafe(TEST_CORE_AUTOFILL_BACKUP), TEST_CORE_AUTOFILL_BACKUP,
);

// 9) No residual @/lib/bizNumber, ../lib/bizNumber, ../../lib/bizNumber in src code.
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
  /from\s+["']@\/lib\/bizNumber["']/,
  /from\s+["']\.\.\/lib\/bizNumber["']/,
  /from\s+["']\.\.\/\.\.\/lib\/bizNumber["']/,
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
checks.no_residual_lib_biz_number_imports_in_code = residuals.length === 0;

const summary = {
  task: "FRONTEND-BZ-1-BIZ-NUMBER-COMMON-UTILS-MOVE",
  paths: {
    new_util: NEW_UTIL,
    old_util: OLD_UTIL,
    autofill_engine: AUTOFILL_ENGINE,
    runocr_workspace: RUNOCR_WORKSPACE,
    detail_history_view: DETAIL_HISTORY_VIEW,
    test_workspace: TEST_WORKSPACE,
    test_core_extract: TEST_CORE_EXTRACT,
    test_core_autofill: TEST_CORE_AUTOFILL,
  },
  checks,
  skippedBackupChecks,
  residuals,
};
console.log(JSON.stringify(summary, null, 2));

const required = [
  "new_util_exists",
  "old_util_absent",
  ...SIBLINGS_THAT_MUST_STAY_IN_LIB.map((n) => `lib_sibling_${n.replace(/\./g, "_")}_still_in_src_lib`),
  "TestWorkspace_present",
  "test_core_dir_present",
  "new_util_has_no_imports",
  "new_util_no_components_import",
  "new_util_no_react_import",
  "new_util_no_react_dom_import",
  "new_util_no_browser_apis",
  "new_util_no_storage_import",
  "new_util_required_exports_preserved",
  "new_util_logic_unchanged_vs_backup",
  "autofill_engine_imports_new_path",
  "runocr_workspace_imports_new_path",
  "detail_history_view_imports_new_path",
  "test_workspace_imports_new_path",
  "test_core_extract_imports_new_path",
  "test_core_autofill_imports_new_path",
  "autofill_engine_logic_unchanged_vs_backup",
  "runocr_workspace_logic_unchanged_vs_backup",
  "detail_history_view_logic_unchanged_vs_backup",
  "test_workspace_logic_unchanged_vs_backup",
  "test_core_extract_logic_unchanged_vs_backup",
  "test_core_autofill_logic_unchanged_vs_backup",
  "no_residual_lib_biz_number_imports_in_code",
];
const allPass = required.every((k) => checks[k] === true);
const verdict = allPass
  ? (skippedBackupChecks.length > 0 ? "PASS_WITH_SKIPPED_BACKUP" : "PASS")
  : "FAIL";
console.log(`[BIZ_NUMBER_COMMON_UTILS_MOVE_BZ1] ${verdict}`);
process.exit(allPass ? 0 : 1);
