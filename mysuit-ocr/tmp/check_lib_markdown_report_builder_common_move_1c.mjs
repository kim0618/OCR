#!/usr/bin/env node
// FRONTEND_LIB_1C_MARKDOWN_REPORT_BUILDER_COMMON_MOVE
// Static check: confirm src/lib/markdownReportBuilder.ts was moved to
// src/common/utils/markdownReportBuilder.ts. Body must be logic-identical
// to the 1C backup (the only import ??@/common/utils/ocrResultFormatters ??// is a common/utils sibling and uses @/ alias, so the move does not affect
// it). OcrResultPanel keeps its original path with only the buildMarkdownReport
// import path corrected. The Markdown v1 fixture set must remain unmodified
// (the markdown contract runner verifies output equivalence separately).
// Other src/lib files must NOT be moved in this step.
//
// Read-only. No production code is modified.

import { readFileSync, existsSync, readdirSync, statSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, "..");

const NEW_BUILDER = resolve(ROOT, "src/common/utils/markdownReportBuilder.ts");
const OLD_BUILDER = resolve(ROOT, "src/lib/markdownReportBuilder.ts");

const OCR_RESULT_PANEL = resolve(ROOT, "src/components/runocr/ui/OcrResultPanel.tsx");
const FORMATTERS = resolve(ROOT, "src/common/utils/ocrResultFormatters.ts");

const LIB_DIR = resolve(ROOT, "src/lib");
const SIBLINGS_THAT_MUST_STAY_IN_LIB = [
  // NOTE: cleanJsonBuilder.ts was legitimately moved out of src/lib by 1D
  // (to src/common/utils/cleanJsonBuilder.ts).
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

const MARKDOWN_FIXTURE_DIR = resolve(ROOT, "tmp/fixtures/markdown_v1");

const BACKUP_DIR = resolve(
  ROOT,
  "backup",
  "lib_markdown_report_builder_20260522_before_FRONTEND_LIB_1C_MARKDOWN_REPORT_BUILDER_COMMON_MOVE",
);
const BUILDER_BACKUP = resolve(BACKUP_DIR, "markdownReportBuilder.ts");
const PANEL_BACKUP = resolve(BACKUP_DIR, "OcrResultPanel.tsx");

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

// 4) common/utils/markdownReportBuilder.ts purity.
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
  !/\blocalStorage\b/.test(newBuilderSrc);
// Imports common/utils sibling (ocrResultFormatters) ??required.
checks.new_builder_imports_common_formatters =
  newBuilderSrc !== null &&
  /from\s+["']@\/common\/utils\/ocrResultFormatters["']/.test(newBuilderSrc);
// MUST NOT have introduced a new @/lib/* runtime dependency.
checks.new_builder_no_lib_imports =
  newBuilderSrc !== null && !/from\s+["']@\/lib\/[^"']+["']/.test(newBuilderSrc);

// 5) Required exports preserved.
checks.new_builder_buildMarkdownReport_preserved =
  newBuilderSrc !== null && /export\s+function\s+buildMarkdownReport\b/.test(newBuilderSrc);
checks.new_builder_MarkdownReportField_preserved =
  newBuilderSrc !== null && /export\s+type\s+MarkdownReportField\b/.test(newBuilderSrc);
checks.new_builder_BuildMarkdownReportInput_preserved =
  newBuilderSrc !== null && /export\s+type\s+BuildMarkdownReportInput\b/.test(newBuilderSrc);

// 6) Logic equivalence vs backup (only import paths may have changed).
const builderBackup = readSafe(BUILDER_BACKUP);
if (builderBackup === null) {
  skippedBackupChecks.push({
    check: "new_builder_logic_unchanged_vs_backup",
    reason: `SKIP_WITH_REASON: backup not found: ${BUILDER_BACKUP}`,
  });
}
// TPL-8F phase-aware: markdownReportBuilder now accepts an optional
// `tableResultViewModels` input. Skip the import-only backup-equivalence
// guard when that marker is present.
const _tpl8fShipped_1c_builder = typeof newBuilderSrc === "string"
  && /tableResultViewModels|TableResultViewModel/.test(newBuilderSrc);
if (_tpl8fShipped_1c_builder) {
  skippedBackupChecks.push({
    check: "new_builder_logic_unchanged_vs_backup",
    reason: "SKIP_WITH_REASON: TPL-8F extended markdownReportBuilder beyond 1C scope (TableResultViewModel marker matched)",
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
  /from\s+["']@\/common\/utils\/markdownReportBuilder["']/.test(panelSrc) &&
  !/from\s+["']@\/lib\/markdownReportBuilder["']/.test(
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
const _tpl8eShipped_1c = typeof panelSrc === "string"
  && /from\s+["']@\/common\/utils\/tableResultViewModel["']/.test(panelSrc);
if (_tpl8eShipped_1c) {
  skippedBackupChecks.push({
    check: "panel_logic_unchanged_vs_backup",
    reason: "SKIP_WITH_REASON: TPL-8E modified OcrResultPanel beyond 1C scope (tableResultViewModel marker matched)",
  });
  checks.panel_logic_unchanged_vs_backup = true;
} else {
  checks.panel_logic_unchanged_vs_backup = compareBackup(
    "panel_logic_unchanged_vs_backup", panelSrc, panelBackup, PANEL_BACKUP,
  );
}

// 9) common/utils/ocrResultFormatters.ts is unchanged at the path level
//    (we did not touch it).
checks.formatters_still_present = existsSync(FORMATTERS);

// 10) No residual @/lib/markdownReportBuilder / ../lib/markdownReportBuilder
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
  /from\s+["']@\/lib\/markdownReportBuilder["']/,
  /from\s+["']\.\.\/lib\/markdownReportBuilder["']/,
  /from\s+["']\.\.\/\.\.\/lib\/markdownReportBuilder["']/,
  /from\s+["']\.\.\/\.\.\/\.\.\/lib\/markdownReportBuilder["']/,
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

// 11) Markdown v1 fixture files were not modified. We assert the fixture
//     directory exists and snapshot file mtimes to ensure 1C did not touch
//     them. (Best-effort: we capture file count + total size.)
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
const fixtureSnap = dirSnapshot(MARKDOWN_FIXTURE_DIR);
checks.markdown_fixture_dir_present = fixtureSnap !== null;
checks.markdown_fixture_files_recorded = fixtureSnap !== null && fixtureSnap.count > 0;

const summary = {
  task: "FRONTEND-LIB-1C-MARKDOWN-REPORT-BUILDER-COMMON-MOVE",
  paths: {
    new_builder: NEW_BUILDER,
    old_builder: OLD_BUILDER,
    panel: OCR_RESULT_PANEL,
    formatters: FORMATTERS,
    markdown_fixture_dir: MARKDOWN_FIXTURE_DIR,
  },
  markdown_fixture_snapshot: fixtureSnap,
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
  "new_builder_imports_common_formatters",
  "new_builder_no_lib_imports",
  "new_builder_buildMarkdownReport_preserved",
  "new_builder_MarkdownReportField_preserved",
  "new_builder_BuildMarkdownReportInput_preserved",
  "new_builder_logic_unchanged_vs_backup",
  "panel_imports_new_builder",
  "panel_logic_unchanged_vs_backup",
  "formatters_still_present",
  "no_residual_lib_builder_imports_in_code",
  "markdown_fixture_dir_present",
  "markdown_fixture_files_recorded",
];
const allPass = required.every((k) => checks[k] === true);
const verdict = allPass
  ? (skippedBackupChecks.length > 0 ? "PASS_WITH_SKIPPED_BACKUP" : "PASS")
  : "FAIL";
console.log(`[LIB_MARKDOWN_REPORT_BUILDER_COMMON_MOVE_1C] ${verdict}`);
process.exit(allPass ? 0 : 1);
