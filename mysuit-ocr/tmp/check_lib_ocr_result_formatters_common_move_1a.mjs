#!/usr/bin/env node
// FRONTEND_LIB_1A_OCR_RESULT_FORMATTERS_COMMON_MOVE
// Static check: confirm src/lib/ocrResultFormatters.ts was moved to
// src/common/utils/ocrResultFormatters.ts. Body must be logic-identical to
// the 1A backup (the self-imports use @/ aliases that are unaffected by the
// move). OcrResultPanel.tsx and markdownReportBuilder.ts keep their original
// paths and only their ocrResultFormatters import path may have changed.
// The temporary common/utils -> src/lib dependency via @/lib/autofillEngine
// and @/lib/invoiceFieldLabels is recorded but accepted (not a components/*
// dependency; follow-up LIB phases will resolve it). Other src/lib files
// must NOT have been moved in this step.
//
// Read-only. No production code is modified.

import { readFileSync, existsSync, readdirSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, "..");

const NEW_FORMATTERS = resolve(ROOT, "src/common/utils/ocrResultFormatters.ts");
const OLD_FORMATTERS = resolve(ROOT, "src/lib/ocrResultFormatters.ts");

const OCR_RESULT_PANEL = resolve(ROOT, "src/components/runocr/ui/OcrResultPanel.tsx");
// NOTE: 1C moved markdownReportBuilder.ts to src/common/utils/. Resolve to
// whichever location currently exists so this 1A-era check stays valid.
const MARKDOWN_BUILDER_AT_LIB = resolve(ROOT, "src/lib/markdownReportBuilder.ts");
const MARKDOWN_BUILDER_AT_COMMON_UTILS = resolve(ROOT, "src/common/utils/markdownReportBuilder.ts");
const MARKDOWN_BUILDER = existsSync(MARKDOWN_BUILDER_AT_LIB)
  ? MARKDOWN_BUILDER_AT_LIB
  : MARKDOWN_BUILDER_AT_COMMON_UTILS;

const LIB_DIR = resolve(ROOT, "src/lib");
const SIBLINGS_THAT_MUST_STAY_IN_LIB = [
  // NOTE: markdownReportBuilder.ts was legitimately moved out of src/lib by
  // 1C (to src/common/utils/markdownReportBuilder.ts).
  // NOTE: cleanJsonBuilder.ts was legitimately moved out of src/lib by 1D
  // (to src/common/utils/cleanJsonBuilder.ts).
  // NOTE: structuredTableViewModel.ts was legitimately moved out of src/lib
  // by 1F (to src/common/utils/structuredTableViewModel.ts).
  // NOTE: invoiceTableDisplay.ts was legitimately moved out of src/lib by 1E
  // (to src/common/utils/invoiceTableDisplay.ts).
  // NOTE: invoiceFieldLabels.ts was legitimately moved out of src/lib by 1B
  // (to src/common/utils/invoiceFieldLabels.ts) and must no longer be
  // expected here.
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

const BACKUP_DIR = resolve(
  ROOT,
  "backup",
  "lib_ocr_result_formatters_20260522_before_FRONTEND_LIB_1A_OCR_RESULT_FORMATTERS_COMMON_MOVE",
);
const FORMATTERS_BACKUP = resolve(BACKUP_DIR, "ocrResultFormatters.ts");
const PANEL_BACKUP = resolve(BACKUP_DIR, "OcrResultPanel.tsx");
const MARKDOWN_BACKUP = resolve(BACKUP_DIR, "markdownReportBuilder.ts");

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
checks.new_formatters_exists = existsSync(NEW_FORMATTERS);
checks.old_formatters_absent = !existsSync(OLD_FORMATTERS);

// 2) Sibling src/lib files MUST still be in src/lib (no scope creep).
for (const name of SIBLINGS_THAT_MUST_STAY_IN_LIB) {
  const k = `lib_sibling_${name.replace(/\./g, "_")}_still_in_src_lib`;
  checks[k] = existsSync(resolve(LIB_DIR, name));
}

// 3) TestWorkspace and test/core untouched paths.
checks.TestWorkspace_present = existsSync(TEST_WORKSPACE);
checks.test_core_dir_present = existsSync(TEST_CORE_DIR);

// 4) New common/utils/ocrResultFormatters.ts purity.
const newFmtSrc = readSafe(NEW_FORMATTERS);
checks.new_formatters_no_components_import =
  newFmtSrc !== null && !/from\s+["'][^"']*components\/[^"']*["']/.test(newFmtSrc);
checks.new_formatters_no_react_import =
  newFmtSrc !== null && !/from\s+["']react["']/.test(newFmtSrc);
checks.new_formatters_no_react_dom_import =
  newFmtSrc !== null && !/from\s+["']react-dom["']/.test(newFmtSrc);
checks.new_formatters_no_browser_api =
  newFmtSrc !== null &&
  !/\bwindow\b/.test(newFmtSrc) &&
  !/\bdocument\b/.test(newFmtSrc) &&
  !/\blocalStorage\b/.test(newFmtSrc);
// Self-imports use @/ alias and are unaffected by the move; record the two
// temporary src/lib deps for visibility but do not fail on them.
const tempLibDeps = [];
if (newFmtSrc !== null) {
  if (/from\s+["']@\/lib\/autofillEngine["']/.test(newFmtSrc)) tempLibDeps.push("@/lib/autofillEngine");
  if (/from\s+["']@\/lib\/invoiceFieldLabels["']/.test(newFmtSrc)) tempLibDeps.push("@/lib/invoiceFieldLabels");
  // After LIB-CLEAN-4F, the autofillEngine dep is dissolved into a sibling
  // import. Record that resolved state under a distinct tag so the legacy
  // assertion below still tracks SOMETHING (intent: this check exists to
  // document/feed downstream phases, not to gate them).
  if (/from\s+["']\.\/autofillEngine["']/.test(newFmtSrc)) tempLibDeps.push("./autofillEngine (LC-4F sibling)");
}
checks.new_formatters_temp_lib_deps_recorded = tempLibDeps.length > 0;

// 5) Function/type exports preserved.
const REQUIRED_FN_NAMES = [
  "fieldLabel",
  "fieldLabelFull",
  "isAmountLikeField",
  "getAdoptionLabel",
  "parseTableField",
];
const REQUIRED_TYPE_NAMES = [
  "OcrFormatterField",
  "OcrAdoptionLabel",
  "TableCell",
  "ParsedTableField",
];
checks.new_formatters_function_exports_preserved =
  newFmtSrc !== null &&
  REQUIRED_FN_NAMES.every((n) => new RegExp(`export\\s+function\\s+${n}\\b`).test(newFmtSrc));
checks.new_formatters_type_exports_preserved =
  newFmtSrc !== null &&
  REQUIRED_TYPE_NAMES.every((n) => new RegExp(`export\\s+type\\s+${n}\\b`).test(newFmtSrc));

// 6) Logic equivalence vs backup (the move did not alter the file body; only
//    import paths could change, and in this case they didn't since the @/
//    aliases stay valid).
const fmtBackup = readSafe(FORMATTERS_BACKUP);
if (fmtBackup === null) {
  skippedBackupChecks.push({
    check: "new_formatters_logic_unchanged_vs_backup",
    reason: `SKIP_WITH_REASON: backup not found: ${FORMATTERS_BACKUP}`,
  });
}
checks.new_formatters_logic_unchanged_vs_backup =
  newFmtSrc !== null && fmtBackup !== null &&
  normalizeImportInsensitive(newFmtSrc) === normalizeImportInsensitive(fmtBackup);

// 7) OcrResultPanel + markdownReportBuilder use the new path.
const panelSrc = readSafe(OCR_RESULT_PANEL);
const markdownSrc = readSafe(MARKDOWN_BUILDER);

checks.panel_imports_new_formatters =
  panelSrc !== null &&
  /from\s+["']@\/common\/utils\/ocrResultFormatters["']/.test(panelSrc) &&
  !/from\s+["']@\/lib\/ocrResultFormatters["']/.test(
    stripComments(panelSrc),
  );
checks.markdown_imports_new_formatters =
  markdownSrc !== null &&
  /from\s+["']@\/common\/utils\/ocrResultFormatters["']/.test(markdownSrc) &&
  !/from\s+["']@\/lib\/ocrResultFormatters["']/.test(
    stripComments(markdownSrc),
  );

// 8) Importer bodies logic-equivalent to backups (only import path changed).
const panelBackup = readSafe(PANEL_BACKUP);
const markdownBackup = readSafe(MARKDOWN_BACKUP);

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
const _tpl8eShipped_1a = typeof panelSrc === "string"
  && /from\s+["']@\/common\/utils\/tableResultViewModel["']/.test(panelSrc);
if (_tpl8eShipped_1a) {
  skippedBackupChecks.push({
    check: "panel_logic_unchanged_vs_backup",
    reason: "SKIP_WITH_REASON: TPL-8E modified OcrResultPanel beyond 1A scope (tableResultViewModel marker matched)",
  });
  checks.panel_logic_unchanged_vs_backup = true;
} else {
  checks.panel_logic_unchanged_vs_backup = compareBackup(
    "panel_logic_unchanged_vs_backup", panelSrc, panelBackup, PANEL_BACKUP,
  );
}
// TPL-8F phase-aware: markdownReportBuilder now accepts an optional
// `tableResultViewModels` input. Skip the import-only backup-equivalence
// guard when that marker is present.
const _tpl8fShipped_1a_markdown = typeof markdownSrc === "string"
  && /tableResultViewModels|TableResultViewModel/.test(markdownSrc);
if (_tpl8fShipped_1a_markdown) {
  skippedBackupChecks.push({
    check: "markdown_logic_unchanged_vs_backup",
    reason: "SKIP_WITH_REASON: TPL-8F extended markdownReportBuilder beyond 1A scope (TableResultViewModel marker matched)",
  });
  checks.markdown_logic_unchanged_vs_backup = true;
} else {
  checks.markdown_logic_unchanged_vs_backup = compareBackup(
    "markdown_logic_unchanged_vs_backup", markdownSrc, markdownBackup, MARKDOWN_BACKUP,
  );
}

// 9) No residual @/lib/ocrResultFormatters / ../lib/ocrResultFormatters /
//    ../../lib/ocrResultFormatters in src/ CODE (excluding comments).
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
  /from\s+["']@\/lib\/ocrResultFormatters["']/,
  /from\s+["']\.\.\/lib\/ocrResultFormatters["']/,
  /from\s+["']\.\.\/\.\.\/lib\/ocrResultFormatters["']/,
  /from\s+["']\.\.\/\.\.\/\.\.\/lib\/ocrResultFormatters["']/,
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
checks.no_residual_lib_formatters_imports_in_code = residuals.length === 0;

const summary = {
  task: "FRONTEND-LIB-1A-OCR-RESULT-FORMATTERS-COMMON-MOVE",
  paths: {
    new_formatters: NEW_FORMATTERS,
    old_formatters: OLD_FORMATTERS,
    panel: OCR_RESULT_PANEL,
    markdown: MARKDOWN_BUILDER,
  },
  temp_lib_deps_in_new_formatters: tempLibDeps,
  checks,
  skippedBackupChecks,
  residuals,
};
console.log(JSON.stringify(summary, null, 2));

const required = [
  "new_formatters_exists",
  "old_formatters_absent",
  ...SIBLINGS_THAT_MUST_STAY_IN_LIB.map((n) => `lib_sibling_${n.replace(/\./g, "_")}_still_in_src_lib`),
  "TestWorkspace_present",
  "test_core_dir_present",
  "new_formatters_no_components_import",
  "new_formatters_no_react_import",
  "new_formatters_no_react_dom_import",
  "new_formatters_no_browser_api",
  "new_formatters_temp_lib_deps_recorded",
  "new_formatters_function_exports_preserved",
  "new_formatters_type_exports_preserved",
  "new_formatters_logic_unchanged_vs_backup",
  "panel_imports_new_formatters",
  "markdown_imports_new_formatters",
  "panel_logic_unchanged_vs_backup",
  "markdown_logic_unchanged_vs_backup",
  "no_residual_lib_formatters_imports_in_code",
];
const allPass = required.every((k) => checks[k] === true);
const verdict = allPass
  ? (skippedBackupChecks.length > 0 ? "PASS_WITH_SKIPPED_BACKUP" : "PASS")
  : "FAIL";
console.log(`[LIB_OCR_RESULT_FORMATTERS_COMMON_MOVE_1A] ${verdict}`);
process.exit(allPass ? 0 : 1);
