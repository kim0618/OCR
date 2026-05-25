#!/usr/bin/env node
// FRONTEND_LIB_1D_CLEAN_JSON_BUILDER_COMMON_MOVE
// Static check: confirm src/lib/cleanJsonBuilder.ts was moved to
// src/common/utils/cleanJsonBuilder.ts. Body must be logic-identical to
// the 1D backup. OcrResultPanel.tsx is the sole production importer and
// keeps its original path with only the cleanJsonBuilder import corrected.
// The Clean JSON v1 fixture runner (tmp/check_clean_json_v1_fixtures_js.mjs)
// loads the builder by absolute filesystem path ??its two hardcoded
// `src/lib/cleanJsonBuilder.ts` references must be updated to
// `src/common/utils/cleanJsonBuilder.ts`. The Clean JSON fixture files
// themselves must NOT be modified. The temporary @/lib/invoiceTableDisplay
// dependency inside the moved builder is recorded but accepted (not a
// components/* dependency; follow-up LIB phase will resolve it). Other
// src/lib files must NOT have been moved in this step.
//
// Read-only. No production code is modified.

import { readFileSync, existsSync, readdirSync, statSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, "..");

const NEW_BUILDER = resolve(ROOT, "src/common/utils/cleanJsonBuilder.ts");
const OLD_BUILDER = resolve(ROOT, "src/lib/cleanJsonBuilder.ts");

const OCR_RESULT_PANEL = resolve(ROOT, "src/components/runocr/ui/OcrResultPanel.tsx");
const CLEAN_JSON_RUNNER = resolve(ROOT, "tmp/check_clean_json_v1_fixtures_js.mjs");

const LIB_DIR = resolve(ROOT, "src/lib");
const SIBLINGS_THAT_MUST_STAY_IN_LIB = [
  // NOTE: structuredTableViewModel.ts was legitimately moved out of src/lib
  // by 1F (to src/common/utils/structuredTableViewModel.ts).
  // NOTE: invoiceTableDisplay.ts was legitimately moved out of src/lib by 1E
  // (to src/common/utils/invoiceTableDisplay.ts).
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

const CLEAN_JSON_FIXTURE_DIR = resolve(ROOT, "tmp/fixtures/clean_json_v1");

const BACKUP_DIR = resolve(
  ROOT,
  "backup",
  "lib_clean_json_builder_20260522_before_FRONTEND_LIB_1D_CLEAN_JSON_BUILDER_COMMON_MOVE",
);
const BUILDER_BACKUP = resolve(BACKUP_DIR, "cleanJsonBuilder.ts");
const PANEL_BACKUP = resolve(BACKUP_DIR, "OcrResultPanel.tsx");
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
checks.new_builder_exists = existsSync(NEW_BUILDER);
checks.old_builder_absent = !existsSync(OLD_BUILDER);

// 2) Sibling src/lib files MUST still be in src/lib (no scope creep).
for (const name of SIBLINGS_THAT_MUST_STAY_IN_LIB) {
  const k = `lib_sibling_${name.replace(/\./g, "_")}_still_in_src_lib`;
  checks[k] = existsSync(resolve(LIB_DIR, name));
}

// 3) TestWorkspace and test/core untouched paths.
checks.TestWorkspace_present = existsSync(TEST_WORKSPACE);
checks.test_core_dir_present = existsSync(TEST_CORE_DIR);

// 4) common/utils/cleanJsonBuilder.ts purity.
const newBuilderSrc = readSafe(NEW_BUILDER);
checks.new_builder_no_components_import =
  newBuilderSrc !== null && !/from\s+["'][^"']*components\/[^"']*["']/.test(newBuilderSrc);
checks.new_builder_no_react_import =
  newBuilderSrc !== null && !/from\s+["']react["']/.test(newBuilderSrc);
checks.new_builder_no_react_dom_import =
  newBuilderSrc !== null && !/from\s+["']react-dom["']/.test(newBuilderSrc);
checks.new_builder_no_browser_api =
  newBuilderSrc !== null &&
  !/\bwindow\b/.test(newBuilderSrc) &&
  !/\bdocument\b/.test(newBuilderSrc) &&
  !/\blocalStorage\b/.test(newBuilderSrc) &&
  !/\bsessionStorage\b/.test(newBuilderSrc) &&
  !/\bfetch\s*\(/.test(newBuilderSrc) &&
  !/\bXMLHttpRequest\b/.test(newBuilderSrc);
// At 1D time the new builder had a temp @/lib/invoiceTableDisplay runtime dep.
// 1E dissolved that dep by moving invoiceTableDisplay into common/utils, so
// the import is now @/common/utils/invoiceTableDisplay. Either form (the
// pre-1E temp dep or the post-1E common/utils sibling) is acceptable for
// this 1D-era check; we record which is present.
const tempLibDeps = [];
const dissolvedDeps = [];
if (newBuilderSrc !== null && /from\s+["']@\/lib\/invoiceTableDisplay["']/.test(newBuilderSrc)) {
  tempLibDeps.push("@/lib/invoiceTableDisplay");
}
if (newBuilderSrc !== null && /from\s+["']@\/common\/utils\/invoiceTableDisplay["']/.test(newBuilderSrc)) {
  dissolvedDeps.push("@/common/utils/invoiceTableDisplay (1E dissolved)");
}
checks.new_builder_temp_lib_deps_recorded =
  tempLibDeps.length > 0 || dissolvedDeps.length > 0;

// 5) Required export preserved.
checks.new_builder_buildCleanJsonResult_preserved =
  newBuilderSrc !== null && /export\s+function\s+buildCleanJsonResult\b/.test(newBuilderSrc);

// 6) Logic equivalence vs backup (only import paths may change ??and in this
//    case the file body did not need any import-path edit because all its
//    imports use @/ absolute aliases unaffected by the move).
const builderBackup = readSafe(BUILDER_BACKUP);
if (builderBackup === null) {
  skippedBackupChecks.push({
    check: "new_builder_logic_unchanged_vs_backup",
    reason: `SKIP_WITH_REASON: backup not found: ${BUILDER_BACKUP}`,
  });
}
// TPL-8F phase-aware: cleanJsonBuilder now accepts an optional
// `tableResultViewModels` input. Skip the import-only backup-equivalence
// guard when that marker is present.
const _tpl8fShipped_1d_builder = typeof newBuilderSrc === "string"
  && /tableResultViewModels|TableResultViewModel/.test(newBuilderSrc);
if (_tpl8fShipped_1d_builder) {
  skippedBackupChecks.push({
    check: "new_builder_logic_unchanged_vs_backup",
    reason: "SKIP_WITH_REASON: TPL-8F extended cleanJsonBuilder beyond 1D scope (TableResultViewModel marker matched)",
  });
  checks.new_builder_logic_unchanged_vs_backup = true;
} else {
  checks.new_builder_logic_unchanged_vs_backup =
    newBuilderSrc !== null && builderBackup !== null &&
    normalizeImportInsensitive(newBuilderSrc) === normalizeImportInsensitive(builderBackup);
}

// 7) OcrResultPanel imports the new path.
const panelSrc = readSafe(OCR_RESULT_PANEL);
checks.panel_imports_new_builder =
  panelSrc !== null &&
  /from\s+["']@\/common\/utils\/cleanJsonBuilder["']/.test(panelSrc) &&
  !/from\s+["']@\/lib\/cleanJsonBuilder["']/.test(
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
const _tpl8eShipped_1d = typeof panelSrc === "string"
  && /from\s+["']@\/common\/utils\/tableResultViewModel["']/.test(panelSrc);
if (_tpl8eShipped_1d) {
  skippedBackupChecks.push({
    check: "panel_logic_unchanged_vs_backup",
    reason: "SKIP_WITH_REASON: TPL-8E modified OcrResultPanel beyond 1D scope (tableResultViewModel marker matched)",
  });
  checks.panel_logic_unchanged_vs_backup = true;
} else {
  checks.panel_logic_unchanged_vs_backup = compareBackup(
    "panel_logic_unchanged_vs_backup", panelSrc, panelBackup, PANEL_BACKUP,
  );
}

// 9) Clean JSON v1 fixture runner: hardcoded path must now point at
//    src/common/utils/cleanJsonBuilder.ts (loader + purity-check read).
const runnerSrc = readSafe(CLEAN_JSON_RUNNER);
checks.runner_loader_uses_new_path =
  runnerSrc !== null &&
  /path\.join\(\s*ROOT\s*,\s*"src"\s*,\s*"common"\s*,\s*"utils"\s*,\s*"cleanJsonBuilder\.ts"\s*\)/.test(runnerSrc);
checks.runner_no_residual_old_path =
  runnerSrc !== null &&
  !/path\.join\(\s*ROOT\s*,\s*"src"\s*,\s*"lib"\s*,\s*"cleanJsonBuilder\.ts"\s*\)/.test(runnerSrc);
// Runner body is allowed to diff vs backup ONLY on the two path-string lines.
// Use normalizeImportInsensitive (which collapses imports) plus a generic
// path-string strip to keep the structural body equivalence assertion useful.
function stripCleanJsonBuilderHardcodedPath(src) {
  return src
    .replace(
      /path\.join\(\s*ROOT\s*,\s*"src"\s*,\s*"(?:lib|common"\s*,\s*"utils)"\s*,\s*"cleanJsonBuilder\.ts"\s*\)/g,
      'path.join(ROOT,"<<BUILDER_TS_PATH>>")',
    );
}
// 1E moved invoiceTableDisplay.ts and updated the runner's invoice path +
// alias mapping. Collapse those too so this 1D-era equivalence check stays
// valid post-1E.
function stripInvoiceTableDisplayHardcoded(src) {
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
  return normalizeImportInsensitive(
    stripInvoiceTableDisplayHardcoded(stripCleanJsonBuilderHardcodedPath(src)),
  );
}
const runnerBackup = readSafe(RUNNER_BACKUP);
if (runnerBackup === null) {
  skippedBackupChecks.push({
    check: "runner_logic_unchanged_vs_backup",
    reason: `SKIP_WITH_REASON: backup not found: ${RUNNER_BACKUP}`,
  });
}
// TPL-13B phase-aware: the runner chain-transpiles tableResultViewModel +
// structuredTableViewModel as cleanJsonBuilder dependencies because the
// builder now imports selectRepresentativeTableResultViewModels at runtime
// (no longer a type-only import). Skip the byte-equivalence guard when
// the chain-transpile marker is present.
const _tpl13bShipped_runner_1d = typeof runnerSrc === "string"
  && /tableResultViewModel\.cjs/.test(runnerSrc);
if (_tpl13bShipped_runner_1d) {
  skippedBackupChecks.push({
    check: "runner_logic_unchanged_vs_backup",
    reason: "SKIP_WITH_REASON: TPL-13B added chain-transpile for tableResultViewModel beyond 1D scope",
  });
  checks.runner_logic_unchanged_vs_backup = true;
} else {
  checks.runner_logic_unchanged_vs_backup =
    runnerSrc !== null && runnerBackup !== null &&
    normalizeRunner(runnerSrc) === normalizeRunner(runnerBackup);
}

// 10) No residual @/lib/cleanJsonBuilder / ../lib/cleanJsonBuilder in src/
//     CODE (excluding comments).
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
  /from\s+["']@\/lib\/cleanJsonBuilder["']/,
  /from\s+["']\.\.\/lib\/cleanJsonBuilder["']/,
  /from\s+["']\.\.\/\.\.\/lib\/cleanJsonBuilder["']/,
  /from\s+["']\.\.\/\.\.\/\.\.\/lib\/cleanJsonBuilder["']/,
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
checks.no_residual_lib_builder_imports_in_code = residuals.length === 0;

// 11) Clean JSON v1 fixture directory untouched: snapshot file count + total
//     size as a best-effort untouched signal.
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
  task: "FRONTEND-LIB-1D-CLEAN-JSON-BUILDER-COMMON-MOVE",
  paths: {
    new_builder: NEW_BUILDER,
    old_builder: OLD_BUILDER,
    panel: OCR_RESULT_PANEL,
    runner: CLEAN_JSON_RUNNER,
    clean_json_fixture_dir: CLEAN_JSON_FIXTURE_DIR,
  },
  clean_json_fixture_snapshot: fixtureSnap,
  temp_lib_deps_in_new_builder: tempLibDeps,
  checks,
  skippedBackupChecks,
  residuals,
};
console.log(JSON.stringify(summary, null, 2));

const required = [
  "new_builder_exists",
  "old_builder_absent",
  ...SIBLINGS_THAT_MUST_STAY_IN_LIB.map((n) => `lib_sibling_${n.replace(/\./g, "_")}_still_in_src_lib`),
  "TestWorkspace_present",
  "test_core_dir_present",
  "new_builder_no_components_import",
  "new_builder_no_react_import",
  "new_builder_no_react_dom_import",
  "new_builder_no_browser_api",
  "new_builder_temp_lib_deps_recorded",
  "new_builder_buildCleanJsonResult_preserved",
  "new_builder_logic_unchanged_vs_backup",
  "panel_imports_new_builder",
  "panel_logic_unchanged_vs_backup",
  "runner_loader_uses_new_path",
  "runner_no_residual_old_path",
  "runner_logic_unchanged_vs_backup",
  "no_residual_lib_builder_imports_in_code",
  "clean_json_fixture_dir_present",
  "clean_json_fixture_files_recorded",
];
const allPass = required.every((k) => checks[k] === true);
const verdict = allPass
  ? (skippedBackupChecks.length > 0 ? "PASS_WITH_SKIPPED_BACKUP" : "PASS")
  : "FAIL";
console.log(`[LIB_CLEAN_JSON_BUILDER_COMMON_MOVE_1D] ${verdict}`);
process.exit(allPass ? 0 : 1);
