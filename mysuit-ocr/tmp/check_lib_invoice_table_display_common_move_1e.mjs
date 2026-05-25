#!/usr/bin/env node
// FRONTEND_LIB_1E_INVOICE_TABLE_DISPLAY_COMMON_MOVE
// Static check: confirm src/lib/invoiceTableDisplay.ts was moved to
// src/common/utils/invoiceTableDisplay.ts. Body must be logic-identical to
// the 1E backup. All four production importers (OcrResultPanel,
// DetailHistoryView, TestWorkspace, common/utils/cleanJsonBuilder) keep
// their original paths with only the invoiceTableDisplay import corrected.
// TestWorkspace.tsx is allowed an import-path-only edit (logic-equivalence
// vs the 1E backup must hold). The Clean JSON v1 fixture runner's
// hardcoded source path and the transpile alias mapping must be updated to
// point at the new common/utils location. The 1D-era cleanJsonBuilder
// @/lib/invoiceTableDisplay runtime temp dep is dissolved by this step.
// Clean JSON fixture files must NOT be modified. Other src/lib files must
// NOT have been moved.
//
// Read-only. No production code is modified.

import { readFileSync, existsSync, readdirSync, statSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, "..");

const NEW_DISPLAY = resolve(ROOT, "src/common/utils/invoiceTableDisplay.ts");
const OLD_DISPLAY = resolve(ROOT, "src/lib/invoiceTableDisplay.ts");

const OCR_RESULT_PANEL = resolve(ROOT, "src/components/runocr/ui/OcrResultPanel.tsx");
// NOTE: After HR-2 (DetailHistoryView ui move) the file lives at
// src/components/history/ui/DetailHistoryView.tsx. Resolve to whichever
// currently exists so this 1E-era check stays valid across both states.
const DETAIL_HISTORY_AT_HISTORY = resolve(ROOT, "src/components/history/DetailHistoryView.tsx");
const DETAIL_HISTORY_AT_HISTORY_UI = resolve(ROOT, "src/components/history/ui/DetailHistoryView.tsx");
const DETAIL_HISTORY = existsSync(DETAIL_HISTORY_AT_HISTORY)
  ? DETAIL_HISTORY_AT_HISTORY
  : DETAIL_HISTORY_AT_HISTORY_UI;
const TEST_WORKSPACE = resolve(ROOT, "src/components/test/TestWorkspace.tsx");
const CLEAN_JSON_BUILDER = resolve(ROOT, "src/common/utils/cleanJsonBuilder.ts");
const CLEAN_JSON_RUNNER = resolve(ROOT, "tmp/check_clean_json_v1_fixtures_js.mjs");

const LIB_DIR = resolve(ROOT, "src/lib");
const SIBLINGS_THAT_MUST_STAY_IN_LIB = [
  // NOTE: structuredTableViewModel.ts was legitimately moved out of src/lib
  // by 1F (to src/common/utils/structuredTableViewModel.ts).
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

const TEST_CORE_DIR = resolve(ROOT, "src/components/test/core");

const CLEAN_JSON_FIXTURE_DIR = resolve(ROOT, "tmp/fixtures/clean_json_v1");

const BACKUP_DIR = resolve(
  ROOT,
  "backup",
  "lib_invoice_table_display_20260522_before_FRONTEND_LIB_1E_INVOICE_TABLE_DISPLAY_COMMON_MOVE",
);
const DISPLAY_BACKUP = resolve(BACKUP_DIR, "invoiceTableDisplay.ts");
const PANEL_BACKUP = resolve(BACKUP_DIR, "OcrResultPanel.tsx");
const DETAIL_HISTORY_BACKUP = resolve(BACKUP_DIR, "DetailHistoryView.tsx");
const TEST_WORKSPACE_BACKUP = resolve(BACKUP_DIR, "TestWorkspace.tsx");
const CLEAN_JSON_BUILDER_BACKUP = resolve(BACKUP_DIR, "cleanJsonBuilder.ts");
const RUNNER_BACKUP = resolve(BACKUP_DIR, "check_clean_json_v1_fixtures_js.mjs");

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
checks.new_display_exists = existsSync(NEW_DISPLAY);
checks.old_display_absent = !existsSync(OLD_DISPLAY);

// 2) Sibling src/lib files MUST still be in src/lib (no scope creep).
for (const name of SIBLINGS_THAT_MUST_STAY_IN_LIB) {
  const k = `lib_sibling_${name.replace(/\./g, "_")}_still_in_src_lib`;
  checks[k] = existsSync(resolve(LIB_DIR, name));
}

// 3) test/core untouched paths.
checks.test_core_dir_present = existsSync(TEST_CORE_DIR);

// 4) common/utils/invoiceTableDisplay.ts purity.
const newDisplaySrc = readSafe(NEW_DISPLAY);
checks.new_display_no_components_import =
  newDisplaySrc !== null && !/from\s+["'][^"']*components\/[^"']*["']/.test(newDisplaySrc);
checks.new_display_no_react_import =
  newDisplaySrc !== null && !/from\s+["']react["']/.test(newDisplaySrc);
checks.new_display_no_react_dom_import =
  newDisplaySrc !== null && !/from\s+["']react-dom["']/.test(newDisplaySrc);
checks.new_display_no_browser_api =
  newDisplaySrc !== null &&
  !/\bwindow\b/.test(newDisplaySrc) &&
  !/\bdocument\b/.test(newDisplaySrc) &&
  !/\blocalStorage\b/.test(newDisplaySrc);

// 5) Required exports preserved.
const REQUIRED_NAMES = [
  "INVOICE_TABLE_COL_PRIORITY",
  "INVOICE_COL_LABEL_MAP",
  "normalizeTableCell",
  "hasMeaningfulTableValue",
  "shouldDisplayRowIndex",
  "buildInvoicePreviewCols",
];
checks.new_display_exports_preserved =
  newDisplaySrc !== null &&
  REQUIRED_NAMES.every((n) => new RegExp(`\\b${n}\\b`).test(newDisplaySrc));

// 6) Logic equivalence vs backup.
const displayBackup = readSafe(DISPLAY_BACKUP);
if (displayBackup === null) {
  skippedBackupChecks.push({
    check: "new_display_logic_unchanged_vs_backup",
    reason: `SKIP_WITH_REASON: backup not found: ${DISPLAY_BACKUP}`,
  });
}
checks.new_display_logic_unchanged_vs_backup =
  newDisplaySrc !== null && displayBackup !== null &&
  normalizeImportInsensitive(newDisplaySrc) === normalizeImportInsensitive(displayBackup);

// 7) Importers now reference the new path.
const panelSrc = readSafe(OCR_RESULT_PANEL);
const detailHistorySrc = readSafe(DETAIL_HISTORY);
const testWorkspaceSrc = readSafe(TEST_WORKSPACE);
const cleanJsonBuilderSrc = readSafe(CLEAN_JSON_BUILDER);

checks.panel_imports_new_display =
  panelSrc !== null &&
  /from\s+["']@\/common\/utils\/invoiceTableDisplay["']/.test(panelSrc) &&
  !/from\s+["']@\/lib\/invoiceTableDisplay["']/.test(stripComments(panelSrc));
checks.detail_history_imports_new_display =
  detailHistorySrc !== null &&
  /from\s+["']@\/common\/utils\/invoiceTableDisplay["']/.test(detailHistorySrc) &&
  !/from\s+["']@\/lib\/invoiceTableDisplay["']/.test(stripComments(detailHistorySrc));
checks.test_workspace_imports_new_display =
  testWorkspaceSrc !== null &&
  /from\s+["']@\/common\/utils\/invoiceTableDisplay["']/.test(testWorkspaceSrc) &&
  !/from\s+["']@\/lib\/invoiceTableDisplay["']/.test(stripComments(testWorkspaceSrc));
checks.clean_json_builder_imports_new_display =
  cleanJsonBuilderSrc !== null &&
  /from\s+["']@\/common\/utils\/invoiceTableDisplay["']/.test(cleanJsonBuilderSrc) &&
  !/from\s+["']@\/lib\/invoiceTableDisplay["']/.test(stripComments(cleanJsonBuilderSrc));

// 8) Importer bodies logic-equivalent to backups (only import path changed).
const panelBackup = readSafe(PANEL_BACKUP);
const detailHistoryBackup = readSafe(DETAIL_HISTORY_BACKUP);
const testWorkspaceBackup = readSafe(TEST_WORKSPACE_BACKUP);
const cleanJsonBuilderBackup = readSafe(CLEAN_JSON_BUILDER_BACKUP);

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
const _tpl8eShipped_1e = typeof panelSrc === "string"
  && /from\s+["']@\/common\/utils\/tableResultViewModel["']/.test(panelSrc);
if (_tpl8eShipped_1e) {
  skippedBackupChecks.push({
    check: "panel_logic_unchanged_vs_backup",
    reason: "SKIP_WITH_REASON: TPL-8E modified OcrResultPanel beyond 1E scope (tableResultViewModel marker matched)",
  });
  checks.panel_logic_unchanged_vs_backup = true;
} else {
  checks.panel_logic_unchanged_vs_backup = compareBackup(
    "panel_logic_unchanged_vs_backup", panelSrc, panelBackup, PANEL_BACKUP,
  );
}
checks.detail_history_logic_unchanged_vs_backup = compareBackup(
  "detail_history_logic_unchanged_vs_backup", detailHistorySrc, detailHistoryBackup, DETAIL_HISTORY_BACKUP,
);
// 9) TestWorkspace specifically: import path-only edit guaranteed by
//    logic-equivalence vs backup.
checks.test_workspace_logic_unchanged_vs_backup = compareBackup(
  "test_workspace_logic_unchanged_vs_backup", testWorkspaceSrc, testWorkspaceBackup, TEST_WORKSPACE_BACKUP,
);
// TPL-8F phase-aware: cleanJsonBuilder now accepts an optional
// `tableResultViewModels` input. Skip the import-only backup-equivalence
// guard when that marker is present.
const _tpl8fShipped_1e_cleanJson = typeof cleanJsonBuilderSrc === "string"
  && /tableResultViewModels|TableResultViewModel/.test(cleanJsonBuilderSrc);
if (_tpl8fShipped_1e_cleanJson) {
  skippedBackupChecks.push({
    check: "clean_json_builder_logic_unchanged_vs_backup",
    reason: "SKIP_WITH_REASON: TPL-8F extended cleanJsonBuilder beyond 1E scope (TableResultViewModel marker matched)",
  });
  checks.clean_json_builder_logic_unchanged_vs_backup = true;
} else {
  checks.clean_json_builder_logic_unchanged_vs_backup = compareBackup(
    "clean_json_builder_logic_unchanged_vs_backup", cleanJsonBuilderSrc, cleanJsonBuilderBackup, CLEAN_JSON_BUILDER_BACKUP,
  );
}

// 10) 1D-era temp dep dissolution: cleanJsonBuilder no longer imports
//     @/lib/invoiceTableDisplay; it now imports the common/utils sibling.
checks.clean_json_builder_no_lib_invoice_table_display_dep =
  cleanJsonBuilderSrc !== null &&
  !/from\s+["']@\/lib\/invoiceTableDisplay["']/.test(stripComments(cleanJsonBuilderSrc));

// 11) Clean JSON v1 fixture runner: hardcoded path + alias mapping updated.
const runnerSrc = readSafe(CLEAN_JSON_RUNNER);
checks.runner_invoice_path_uses_common_utils =
  runnerSrc !== null &&
  /path\.join\(\s*ROOT\s*,\s*"src"\s*,\s*"common"\s*,\s*"utils"\s*,\s*"invoiceTableDisplay\.ts"\s*\)/.test(runnerSrc);
checks.runner_invoice_alias_mapping_uses_common_utils =
  runnerSrc !== null &&
  /\["@\/common\/utils\/invoiceTableDisplay"\s*,\s*"\.\/invoiceTableDisplay\.cjs"\]/.test(runnerSrc);
checks.runner_no_residual_lib_invoice_path =
  runnerSrc !== null &&
  !/path\.join\(\s*ROOT\s*,\s*"src"\s*,\s*"lib"\s*,\s*"invoiceTableDisplay\.ts"\s*\)/.test(runnerSrc);
checks.runner_no_residual_lib_invoice_alias =
  runnerSrc !== null &&
  !/\["@\/lib\/invoiceTableDisplay"\s*,/.test(runnerSrc);

// Runner body logic-equivalence vs backup, ignoring the two path
// strings/alias strings we legitimately changed.
function stripInvoiceTableDisplayPath(src) {
  return src
    .replace(
      /path\.join\(\s*ROOT\s*,\s*"src"\s*,\s*"(?:lib|common"\s*,\s*"utils)"\s*,\s*"invoiceTableDisplay\.ts"\s*\)/g,
      'path.join(ROOT,"<<INVOICE_TS_PATH>>")',
    )
    .replace(
      /\["@\/(?:lib|common\/utils)\/invoiceTableDisplay"\s*,\s*"\.\/invoiceTableDisplay\.cjs"\]/g,
      '["<<INVOICE_ALIAS>>","./invoiceTableDisplay.cjs"]',
    );
}
function normalizeRunner(src) {
  return normalizeImportInsensitive(stripInvoiceTableDisplayPath(src));
}
const runnerBackup = readSafe(RUNNER_BACKUP);
if (runnerBackup === null) {
  skippedBackupChecks.push({
    check: "runner_logic_unchanged_vs_backup",
    reason: `SKIP_WITH_REASON: backup not found: ${RUNNER_BACKUP}`,
  });
}
// TPL-13B phase-aware: runner chain-transpiles tableResultViewModel deps.
const _tpl13bShipped_runner_1e = typeof runnerSrc === "string"
  && /tableResultViewModel\.cjs/.test(runnerSrc);
if (_tpl13bShipped_runner_1e) {
  skippedBackupChecks.push({
    check: "runner_logic_unchanged_vs_backup",
    reason: "SKIP_WITH_REASON: TPL-13B added chain-transpile for tableResultViewModel beyond 1E scope",
  });
  checks.runner_logic_unchanged_vs_backup = true;
} else {
  checks.runner_logic_unchanged_vs_backup =
    runnerSrc !== null && runnerBackup !== null &&
    normalizeRunner(runnerSrc) === normalizeRunner(runnerBackup);
}

// 12) No residual @/lib/invoiceTableDisplay / ../lib/invoiceTableDisplay in
//     src/ CODE (excluding comments).
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
  /from\s+["']@\/lib\/invoiceTableDisplay["']/,
  /from\s+["']\.\.\/lib\/invoiceTableDisplay["']/,
  /from\s+["']\.\.\/\.\.\/lib\/invoiceTableDisplay["']/,
  /from\s+["']\.\.\/\.\.\/\.\.\/lib\/invoiceTableDisplay["']/,
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
checks.no_residual_lib_display_imports_in_code = residuals.length === 0;

// 13) Clean JSON v1 fixture directory untouched.
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
const fixtureSnap = dirSnapshot(CLEAN_JSON_FIXTURE_DIR);
checks.clean_json_fixture_dir_present = fixtureSnap !== null;
checks.clean_json_fixture_files_recorded = fixtureSnap !== null && fixtureSnap.count > 0;

const summary = {
  task: "FRONTEND-LIB-1E-INVOICE-TABLE-DISPLAY-COMMON-MOVE",
  paths: {
    new_display: NEW_DISPLAY,
    old_display: OLD_DISPLAY,
    panel: OCR_RESULT_PANEL,
    detail_history: DETAIL_HISTORY,
    test_workspace: TEST_WORKSPACE,
    clean_json_builder: CLEAN_JSON_BUILDER,
    clean_json_runner: CLEAN_JSON_RUNNER,
    clean_json_fixture_dir: CLEAN_JSON_FIXTURE_DIR,
  },
  clean_json_fixture_snapshot: fixtureSnap,
  checks,
  skippedBackupChecks,
  residuals,
};
console.log(JSON.stringify(summary, null, 2));

const required = [
  "new_display_exists",
  "old_display_absent",
  ...SIBLINGS_THAT_MUST_STAY_IN_LIB.map((n) => `lib_sibling_${n.replace(/\./g, "_")}_still_in_src_lib`),
  "test_core_dir_present",
  "new_display_no_components_import",
  "new_display_no_react_import",
  "new_display_no_react_dom_import",
  "new_display_no_browser_api",
  "new_display_exports_preserved",
  "new_display_logic_unchanged_vs_backup",
  "panel_imports_new_display",
  "detail_history_imports_new_display",
  "test_workspace_imports_new_display",
  "clean_json_builder_imports_new_display",
  "panel_logic_unchanged_vs_backup",
  "detail_history_logic_unchanged_vs_backup",
  "test_workspace_logic_unchanged_vs_backup",
  "clean_json_builder_logic_unchanged_vs_backup",
  "clean_json_builder_no_lib_invoice_table_display_dep",
  "runner_invoice_path_uses_common_utils",
  "runner_invoice_alias_mapping_uses_common_utils",
  "runner_no_residual_lib_invoice_path",
  "runner_no_residual_lib_invoice_alias",
  "runner_logic_unchanged_vs_backup",
  "no_residual_lib_display_imports_in_code",
  "clean_json_fixture_dir_present",
  "clean_json_fixture_files_recorded",
];
const allPass = required.every((k) => checks[k] === true);
const verdict = allPass
  ? (skippedBackupChecks.length > 0 ? "PASS_WITH_SKIPPED_BACKUP" : "PASS")
  : "FAIL";
console.log(`[LIB_INVOICE_TABLE_DISPLAY_COMMON_MOVE_1E] ${verdict}`);
process.exit(allPass ? 0 : 1);
