#!/usr/bin/env node
// FRONTEND_LIB_1B_INVOICE_FIELD_LABELS_COMMON_MOVE
// Static check: confirm src/lib/invoiceFieldLabels.ts was moved to
// src/common/utils/invoiceFieldLabels.ts. Body must be logic-identical to
// the 1B backup. Importers (ocrResultFormatters, OcrDocViewer,
// DetailHistoryView) keep their original locations and only the
// invoiceFieldLabels import path may have changed. The 1A-era temporary
// @/lib/invoiceFieldLabels runtime dependency inside
// common/utils/ocrResultFormatters.ts must be dissolved by this step
// (replaced with @/common/utils/invoiceFieldLabels). The remaining 1A temp
// dep on @/lib/autofillEngine (type-only) is still allowed pending its own
// follow-up phase. Other src/lib files must NOT be moved in this step.
//
// Read-only. No production code is modified.

import { readFileSync, existsSync, readdirSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, "..");

const NEW_LABELS = resolve(ROOT, "src/common/utils/invoiceFieldLabels.ts");
const OLD_LABELS = resolve(ROOT, "src/lib/invoiceFieldLabels.ts");

const OCR_RESULT_FORMATTERS = resolve(ROOT, "src/common/utils/ocrResultFormatters.ts");
const OCR_DOC_VIEWER = resolve(ROOT, "src/components/runocr/ui/OcrDocViewer.tsx");
// NOTE: After HR-2 (DetailHistoryView ui move) the file lives at
// src/components/history/ui/DetailHistoryView.tsx. Resolve to whichever
// currently exists so this 1B-era check stays valid across both states.
const DETAIL_HISTORY_AT_HISTORY = resolve(ROOT, "src/components/history/DetailHistoryView.tsx");
const DETAIL_HISTORY_AT_HISTORY_UI = resolve(ROOT, "src/components/history/ui/DetailHistoryView.tsx");
const DETAIL_HISTORY = existsSync(DETAIL_HISTORY_AT_HISTORY)
  ? DETAIL_HISTORY_AT_HISTORY
  : DETAIL_HISTORY_AT_HISTORY_UI;
const OCR_RESULT_PANEL = resolve(ROOT, "src/components/runocr/ui/OcrResultPanel.tsx");
// NOTE: 1C moved markdownReportBuilder.ts to src/common/utils/. Resolve to
// whichever location currently exists so this 1B-era check stays valid.
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
  "lib_invoice_field_labels_20260522_before_FRONTEND_LIB_1B_INVOICE_FIELD_LABELS_COMMON_MOVE",
);
const LABELS_BACKUP = resolve(BACKUP_DIR, "invoiceFieldLabels.ts");
const FORMATTERS_BACKUP = resolve(BACKUP_DIR, "ocrResultFormatters.ts");
const DOC_VIEWER_BACKUP = resolve(BACKUP_DIR, "OcrDocViewer.tsx");
const DETAIL_HISTORY_BACKUP = resolve(BACKUP_DIR, "DetailHistoryView.tsx");

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
checks.new_labels_exists = existsSync(NEW_LABELS);
checks.old_labels_absent = !existsSync(OLD_LABELS);

// 2) Sibling src/lib files MUST still be in src/lib (no scope creep).
for (const name of SIBLINGS_THAT_MUST_STAY_IN_LIB) {
  const k = `lib_sibling_${name.replace(/\./g, "_")}_still_in_src_lib`;
  checks[k] = existsSync(resolve(LIB_DIR, name));
}

// 3) TestWorkspace and test/core untouched paths.
checks.TestWorkspace_present = existsSync(TEST_WORKSPACE);
checks.test_core_dir_present = existsSync(TEST_CORE_DIR);

// 4) common/utils/invoiceFieldLabels.ts purity.
const newLabelsSrc = readSafe(NEW_LABELS);
checks.new_labels_no_components_import =
  newLabelsSrc !== null && !/from\s+["'][^"']*components\/[^"']*["']/.test(newLabelsSrc);
checks.new_labels_no_react_import =
  newLabelsSrc !== null && !/from\s+["']react["']/.test(newLabelsSrc);
checks.new_labels_no_react_dom_import =
  newLabelsSrc !== null && !/from\s+["']react-dom["']/.test(newLabelsSrc);
checks.new_labels_no_browser_api =
  newLabelsSrc !== null &&
  !/\bwindow\b/.test(newLabelsSrc) &&
  !/\bdocument\b/.test(newLabelsSrc) &&
  !/\blocalStorage\b/.test(newLabelsSrc);
// Leaf file: no imports at all.
checks.new_labels_no_imports =
  newLabelsSrc !== null && !/^\s*import\s+/m.test(newLabelsSrc);

// 5) Required exports preserved.
const REQUIRED_NAMES = ["INVOICE_FIELD_KO", "resolveFieldLabel", "fieldDisplayLabel"];
checks.new_labels_INVOICE_FIELD_KO_preserved =
  newLabelsSrc !== null && /export\s+const\s+INVOICE_FIELD_KO\b/.test(newLabelsSrc);
checks.new_labels_resolveFieldLabel_preserved =
  newLabelsSrc !== null && /export\s+function\s+resolveFieldLabel\b/.test(newLabelsSrc);
checks.new_labels_fieldDisplayLabel_preserved =
  newLabelsSrc !== null && /export\s+function\s+fieldDisplayLabel\b/.test(newLabelsSrc);

// 6) Logic equivalence vs backup.
const labelsBackup = readSafe(LABELS_BACKUP);
if (labelsBackup === null) {
  skippedBackupChecks.push({
    check: "new_labels_logic_unchanged_vs_backup",
    reason: `SKIP_WITH_REASON: backup not found: ${LABELS_BACKUP}`,
  });
}
checks.new_labels_logic_unchanged_vs_backup =
  newLabelsSrc !== null && labelsBackup !== null &&
  normalizeImportInsensitive(newLabelsSrc) === normalizeImportInsensitive(labelsBackup);

// 7) Importers now reference the new path.
const formattersSrc = readSafe(OCR_RESULT_FORMATTERS);
const docViewerSrc = readSafe(OCR_DOC_VIEWER);
const detailHistorySrc = readSafe(DETAIL_HISTORY);

checks.formatters_imports_new_labels =
  formattersSrc !== null &&
  /from\s+["']@\/common\/utils\/invoiceFieldLabels["']/.test(formattersSrc) &&
  !/from\s+["']@\/lib\/invoiceFieldLabels["']/.test(
    stripComments(formattersSrc),
  );
checks.doc_viewer_imports_new_labels =
  docViewerSrc !== null &&
  /from\s+["']@\/common\/utils\/invoiceFieldLabels["']/.test(docViewerSrc) &&
  !/from\s+["']@\/lib\/invoiceFieldLabels["']/.test(
    stripComments(docViewerSrc),
  );
checks.detail_history_imports_new_labels =
  detailHistorySrc !== null &&
  /from\s+["']@\/common\/utils\/invoiceFieldLabels["']/.test(detailHistorySrc) &&
  !/from\s+["']@\/lib\/invoiceFieldLabels["']/.test(
    stripComments(detailHistorySrc),
  );

// 8) Importer bodies logic-equivalent to backups (only import path changed).
const formattersBackup = readSafe(FORMATTERS_BACKUP);
const docViewerBackup = readSafe(DOC_VIEWER_BACKUP);
const detailHistoryBackup = readSafe(DETAIL_HISTORY_BACKUP);

function compareBackup(name, cur, backup, backupPath) {
  if (backup === null) {
    skippedBackupChecks.push({ check: name, reason: `SKIP_WITH_REASON: backup not found: ${backupPath}` });
    return cur !== null;
  }
  return cur !== null && backup !== null &&
    normalizeImportInsensitive(cur) === normalizeImportInsensitive(backup);
}
checks.formatters_logic_unchanged_vs_backup = compareBackup(
  "formatters_logic_unchanged_vs_backup", formattersSrc, formattersBackup, FORMATTERS_BACKUP,
);
checks.doc_viewer_logic_unchanged_vs_backup = compareBackup(
  "doc_viewer_logic_unchanged_vs_backup", docViewerSrc, docViewerBackup, DOC_VIEWER_BACKUP,
);
checks.detail_history_logic_unchanged_vs_backup = compareBackup(
  "detail_history_logic_unchanged_vs_backup", detailHistorySrc, detailHistoryBackup, DETAIL_HISTORY_BACKUP,
);

// 9) OcrResultPanel + markdownReportBuilder were NOT touched by 1B (they
//    don't import invoiceFieldLabels directly). Confirm they still import
//    ocrResultFormatters from common/utils.
const panelSrc = readSafe(OCR_RESULT_PANEL);
const markdownSrc = readSafe(MARKDOWN_BUILDER);
checks.panel_still_imports_common_formatters =
  panelSrc !== null && /from\s+["']@\/common\/utils\/ocrResultFormatters["']/.test(panelSrc);
checks.markdown_still_imports_common_formatters =
  markdownSrc !== null && /from\s+["']@\/common\/utils\/ocrResultFormatters["']/.test(markdownSrc);

// 10) No residual @/lib/invoiceFieldLabels / ../lib/invoiceFieldLabels in
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
  /from\s+["']@\/lib\/invoiceFieldLabels["']/,
  /from\s+["']\.\.\/lib\/invoiceFieldLabels["']/,
  /from\s+["']\.\.\/\.\.\/lib\/invoiceFieldLabels["']/,
  /from\s+["']\.\.\/\.\.\/\.\.\/lib\/invoiceFieldLabels["']/,
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
checks.no_residual_lib_labels_imports_in_code = residuals.length === 0;

// 11) 1A-era temp dep dissolution: the @/lib/invoiceFieldLabels runtime dep
//     inside common/utils/ocrResultFormatters.ts is gone, replaced with the
//     common/utils sibling import. The @/lib/autofillEngine type-only dep
//     remains (resolved in a later phase).
checks.formatters_no_lib_labels_runtime_dep =
  formattersSrc !== null &&
  !/from\s+["']@\/lib\/invoiceFieldLabels["']/.test(stripComments(formattersSrc));
// NOTE: After LIB-CLEAN-4F, the @/lib/autofillEngine type-only dep is
// dissolved — ocrResultFormatters now imports autofillEngine via the
// common/utils sibling form `./autofillEngine`. Accept either state.
checks.formatters_lib_autofill_engine_dep_still_present =
  formattersSrc !== null &&
  (/from\s+["']@\/lib\/autofillEngine["']/.test(formattersSrc) ||
    /from\s+["']\.\/autofillEngine["']/.test(formattersSrc));

const summary = {
  task: "FRONTEND-LIB-1B-INVOICE-FIELD-LABELS-COMMON-MOVE",
  paths: {
    new_labels: NEW_LABELS,
    old_labels: OLD_LABELS,
    formatters: OCR_RESULT_FORMATTERS,
    doc_viewer: OCR_DOC_VIEWER,
    detail_history: DETAIL_HISTORY,
  },
  checks,
  skippedBackupChecks,
  residuals,
};
console.log(JSON.stringify(summary, null, 2));

const required = [
  "new_labels_exists",
  "old_labels_absent",
  ...SIBLINGS_THAT_MUST_STAY_IN_LIB.map((n) => `lib_sibling_${n.replace(/\./g, "_")}_still_in_src_lib`),
  "TestWorkspace_present",
  "test_core_dir_present",
  "new_labels_no_components_import",
  "new_labels_no_react_import",
  "new_labels_no_react_dom_import",
  "new_labels_no_browser_api",
  "new_labels_no_imports",
  "new_labels_INVOICE_FIELD_KO_preserved",
  "new_labels_resolveFieldLabel_preserved",
  "new_labels_fieldDisplayLabel_preserved",
  "new_labels_logic_unchanged_vs_backup",
  "formatters_imports_new_labels",
  "doc_viewer_imports_new_labels",
  "detail_history_imports_new_labels",
  "formatters_logic_unchanged_vs_backup",
  "doc_viewer_logic_unchanged_vs_backup",
  "detail_history_logic_unchanged_vs_backup",
  "panel_still_imports_common_formatters",
  "markdown_still_imports_common_formatters",
  "no_residual_lib_labels_imports_in_code",
  "formatters_no_lib_labels_runtime_dep",
  "formatters_lib_autofill_engine_dep_still_present",
];
const allPass = required.every((k) => checks[k] === true);
const verdict = allPass
  ? (skippedBackupChecks.length > 0 ? "PASS_WITH_SKIPPED_BACKUP" : "PASS")
  : "FAIL";
console.log(`[LIB_INVOICE_FIELD_LABELS_COMMON_MOVE_1B] ${verdict}`);
process.exit(allPass ? 0 : 1);
