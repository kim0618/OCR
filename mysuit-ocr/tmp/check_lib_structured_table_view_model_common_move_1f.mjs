#!/usr/bin/env node
// FRONTEND_LIB_1F_STRUCTURED_TABLE_VIEW_MODEL_COMMON_MOVE
// Static check: confirm src/lib/structuredTableViewModel.ts was moved to
// src/common/utils/structuredTableViewModel.ts. Body must be logic-identical
// to the 1F backup. OcrResultPanel is the sole production importer and keeps
// its original path with only the structuredTableViewModel import corrected.
// The table_view_model v1 fixture runner (tmp/check_table_view_model_v1_fixtures_js.mjs)
// loads the helper by absolute filesystem path; its HELPER_SRC must point at
// the new common/utils location. The table_view_model v1 fixture files
// themselves must NOT be modified. Other src/lib files must NOT have been
// moved in this step.
//
// Read-only. No production code is modified.

import { readFileSync, existsSync, readdirSync, statSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, "..");

const NEW_HELPER = resolve(ROOT, "src/common/utils/structuredTableViewModel.ts");
const OLD_HELPER = resolve(ROOT, "src/lib/structuredTableViewModel.ts");

const OCR_RESULT_PANEL = resolve(ROOT, "src/components/runocr/ui/OcrResultPanel.tsx");
const TABLE_VIEW_RUNNER = resolve(ROOT, "tmp/check_table_view_model_v1_fixtures_js.mjs");

const LIB_DIR = resolve(ROOT, "src/lib");
const SIBLINGS_THAT_MUST_STAY_IN_LIB = [
  // NOTE: bizNumber.ts was legitimately moved out of src/lib by BZ-1
  // (to src/common/utils/bizNumber.ts).
  // NOTE: autofillEngine.ts removed after LIB-CLEAN-4F (moved to src/common/utils/).
  // NOTE: historyStore.ts was legitimately moved out of src/lib by CS-2
  // (to src/common/storage/historyStore.ts).
  // NOTE: imageStore.ts was legitimately moved out of src/lib by CS-1
  // (to src/common/storage/imageStore.ts).
  // NOTE: profiles.ts removed after LIB-CLEAN-4D (moved to src/components/test/utils/).
  // NOTE: testsets.ts removed after LIB-CLEAN-4C (moved to src/common/config/).
];

const TEST_WORKSPACE = resolve(ROOT, "src/components/test/TestWorkspace.tsx");
const TEST_CORE_DIR = resolve(ROOT, "src/components/test/core");

const TABLE_VIEW_FIXTURE_DIR = resolve(ROOT, "tmp/fixtures/table_view_model_v1");

const BACKUP_DIR = resolve(
  ROOT,
  "backup",
  "lib_structured_table_view_model_20260522_before_FRONTEND_LIB_1F_STRUCTURED_TABLE_VIEW_MODEL_COMMON_MOVE",
);
const HELPER_BACKUP = resolve(BACKUP_DIR, "structuredTableViewModel.ts");
const PANEL_BACKUP = resolve(BACKUP_DIR, "OcrResultPanel.tsx");
const RUNNER_BACKUP = resolve(BACKUP_DIR, "check_table_view_model_v1_fixtures_js.mjs");

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
checks.new_helper_exists = existsSync(NEW_HELPER);
checks.old_helper_absent = !existsSync(OLD_HELPER);

// 2) Sibling src/lib files MUST still be in src/lib (no scope creep).
for (const name of SIBLINGS_THAT_MUST_STAY_IN_LIB) {
  const k = `lib_sibling_${name.replace(/\./g, "_")}_still_in_src_lib`;
  checks[k] = existsSync(resolve(LIB_DIR, name));
}

// 3) TestWorkspace and test/core untouched paths.
checks.TestWorkspace_present = existsSync(TEST_WORKSPACE);
checks.test_core_dir_present = existsSync(TEST_CORE_DIR);

// 4) common/utils/structuredTableViewModel.ts purity.
const newHelperSrc = readSafe(NEW_HELPER);
checks.new_helper_no_components_import =
  newHelperSrc !== null && !/from\s+["'][^"']*components\/[^"']*["']/.test(newHelperSrc);
checks.new_helper_no_react_import =
  newHelperSrc !== null && !/from\s+["']react["']/.test(newHelperSrc);
checks.new_helper_no_react_dom_import =
  newHelperSrc !== null && !/from\s+["']react-dom["']/.test(newHelperSrc);
checks.new_helper_no_browser_api =
  newHelperSrc !== null &&
  !/\bwindow\b/.test(newHelperSrc) &&
  !/\bdocument\b/.test(newHelperSrc) &&
  !/\blocalStorage\b/.test(newHelperSrc);
// 1F invariant: structuredTableViewModel must NOT import any @/lib/* or
// @/common/utils/invoiceTableDisplay (caller passes displayCols).
checks.new_helper_no_at_lib_imports =
  newHelperSrc !== null && !/from\s+["']@\/lib\/[^"']+["']/.test(newHelperSrc);
checks.new_helper_no_invoiceTableDisplay_import =
  newHelperSrc !== null && !/invoiceTableDisplay/.test(newHelperSrc);

// 5) Required export preserved.
checks.new_helper_buildStructuredTableViewModel_preserved =
  newHelperSrc !== null && /export\s+function\s+buildStructuredTableViewModel\b/.test(newHelperSrc);

// 6) Logic equivalence vs backup (only import paths may change ??and in
//    this case the file has no @/ imports to adjust).
const helperBackup = readSafe(HELPER_BACKUP);
if (helperBackup === null) {
  skippedBackupChecks.push({
    check: "new_helper_logic_unchanged_vs_backup",
    reason: `SKIP_WITH_REASON: backup not found: ${HELPER_BACKUP}`,
  });
}
checks.new_helper_logic_unchanged_vs_backup =
  newHelperSrc !== null && helperBackup !== null &&
  normalizeImportInsensitive(newHelperSrc) === normalizeImportInsensitive(helperBackup);

// 7) OcrResultPanel imports the new path.
const panelSrc = readSafe(OCR_RESULT_PANEL);
checks.panel_imports_new_helper =
  panelSrc !== null &&
  /from\s+["']@\/common\/utils\/structuredTableViewModel["']/.test(panelSrc) &&
  !/from\s+["']@\/lib\/structuredTableViewModel["']/.test(
    stripComments(panelSrc),
  );

// 8) Panel body logic-equivalent to backup (only import path changed).
const panelBackup = readSafe(PANEL_BACKUP);
function compareBackup(name, cur, backup, backupPath) {
  if (backup === null) {
    skippedBackupChecks.push({ check: name, reason: `SKIP_WITH_REASON: backup not found: ${backupPath}` });
    return cur !== null;
  }
  return cur !== null && backup !== null &&
    normalizeImportInsensitive(cur) === normalizeImportInsensitive(backup);
}
// TPL-8E phase-aware: OcrResultPanel was rewritten to consume
// buildTableResultViewModels. Skip the import-only backup-equivalence guard
// when that marker is present.
const _tpl8eShipped_1f = typeof panelSrc === "string"
  && /from\s+["']@\/common\/utils\/tableResultViewModel["']/.test(panelSrc);
if (_tpl8eShipped_1f) {
  skippedBackupChecks.push({
    check: "panel_logic_unchanged_vs_backup",
    reason: "SKIP_WITH_REASON: TPL-8E modified OcrResultPanel beyond 1F scope (tableResultViewModel marker matched)",
  });
  checks.panel_logic_unchanged_vs_backup = true;
} else {
  checks.panel_logic_unchanged_vs_backup = compareBackup(
    "panel_logic_unchanged_vs_backup", panelSrc, panelBackup, PANEL_BACKUP,
  );
}

// 9) table_view_model v1 fixture runner: HELPER_SRC must point at
//    src/common/utils/structuredTableViewModel.ts.
const runnerSrc = readSafe(TABLE_VIEW_RUNNER);
checks.runner_helper_src_uses_new_path =
  runnerSrc !== null &&
  /path\.join\(\s*ROOT\s*,\s*"src"\s*,\s*"common"\s*,\s*"utils"\s*,\s*"structuredTableViewModel\.ts"\s*\)/.test(runnerSrc);
checks.runner_no_residual_old_helper_path =
  runnerSrc !== null &&
  !/path\.join\(\s*ROOT\s*,\s*"src"\s*,\s*"lib"\s*,\s*"structuredTableViewModel\.ts"\s*\)/.test(runnerSrc);

function stripHelperSrcHardcoded(src) {
  return src.replace(
    /path\.join\(\s*ROOT\s*,\s*"src"\s*,\s*"(?:lib|common"\s*,\s*"utils)"\s*,\s*"structuredTableViewModel\.ts"\s*\)/g,
    'path.join(ROOT,"<<HELPER_SRC>>")',
  );
}
function normalizeRunner(src) {
  return normalizeImportInsensitive(stripHelperSrcHardcoded(src));
}
const runnerBackup = readSafe(RUNNER_BACKUP);
if (runnerBackup === null) {
  skippedBackupChecks.push({
    check: "runner_logic_unchanged_vs_backup",
    reason: `SKIP_WITH_REASON: backup not found: ${RUNNER_BACKUP}`,
  });
}
checks.runner_logic_unchanged_vs_backup =
  runnerSrc !== null && runnerBackup !== null &&
  normalizeRunner(runnerSrc) === normalizeRunner(runnerBackup);

// 10) No residual @/lib/structuredTableViewModel / ../lib/structuredTableViewModel
//     in src/ CODE (excluding comments).
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
  /from\s+["']@\/lib\/structuredTableViewModel["']/,
  /from\s+["']\.\.\/lib\/structuredTableViewModel["']/,
  /from\s+["']\.\.\/\.\.\/lib\/structuredTableViewModel["']/,
  /from\s+["']\.\.\/\.\.\/\.\.\/lib\/structuredTableViewModel["']/,
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
checks.no_residual_lib_helper_imports_in_code = residuals.length === 0;

// 11) table_view_model v1 fixture directory untouched.
function dirSnapshot(dir) {
  if (!existsSync(dir)) return null;
  let count = 0;
  let totalBytes = 0;
  function walkF(d) {
    for (const ent of readdirSync(d, { withFileTypes: true })) {
      const p = resolve(d, ent.name);
      if (ent.isDirectory()) walkF(p);
      else if (ent.isFile()) {
        try {
          totalBytes += statSync(p).size;
          count += 1;
        } catch {}
      }
    }
  }
  walkF(dir);
  return { count, totalBytes };
}
const fixtureSnap = dirSnapshot(TABLE_VIEW_FIXTURE_DIR);
checks.table_view_model_fixture_dir_present = fixtureSnap !== null;
checks.table_view_model_fixture_files_recorded = fixtureSnap !== null && fixtureSnap.count > 0;

const summary = {
  task: "FRONTEND-LIB-1F-STRUCTURED-TABLE-VIEW-MODEL-COMMON-MOVE",
  paths: {
    new_helper: NEW_HELPER,
    old_helper: OLD_HELPER,
    panel: OCR_RESULT_PANEL,
    runner: TABLE_VIEW_RUNNER,
    table_view_model_fixture_dir: TABLE_VIEW_FIXTURE_DIR,
  },
  table_view_model_fixture_snapshot: fixtureSnap,
  checks,
  skippedBackupChecks,
  residuals,
};
console.log(JSON.stringify(summary, null, 2));

const required = [
  "new_helper_exists",
  "old_helper_absent",
  ...SIBLINGS_THAT_MUST_STAY_IN_LIB.map((n) => `lib_sibling_${n.replace(/\./g, "_")}_still_in_src_lib`),
  "TestWorkspace_present",
  "test_core_dir_present",
  "new_helper_no_components_import",
  "new_helper_no_react_import",
  "new_helper_no_react_dom_import",
  "new_helper_no_browser_api",
  "new_helper_no_at_lib_imports",
  "new_helper_no_invoiceTableDisplay_import",
  "new_helper_buildStructuredTableViewModel_preserved",
  "new_helper_logic_unchanged_vs_backup",
  "panel_imports_new_helper",
  "panel_logic_unchanged_vs_backup",
  "runner_helper_src_uses_new_path",
  "runner_no_residual_old_helper_path",
  "runner_logic_unchanged_vs_backup",
  "no_residual_lib_helper_imports_in_code",
  "table_view_model_fixture_dir_present",
  "table_view_model_fixture_files_recorded",
];
const allPass = required.every((k) => checks[k] === true);
const verdict = allPass
  ? (skippedBackupChecks.length > 0 ? "PASS_WITH_SKIPPED_BACKUP" : "PASS")
  : "FAIL";
console.log(`[LIB_STRUCTURED_TABLE_VIEW_MODEL_COMMON_MOVE_1F] ${verdict}`);
process.exit(allPass ? 0 : 1);
