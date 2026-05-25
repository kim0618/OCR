#!/usr/bin/env node
// LIB-CLEAN-4F AUTOFILL ENGINE COMMON/UTILS MOVE
// Static check: confirm src/lib/autofillEngine.ts was moved to
// src/common/utils/autofillEngine.ts. Body must be logic-identical to the
// LC-4F backup (import path strip). 4 importers (RunOcrWorkspace,
// OcrResultPanel, DetailHistoryView, common/utils/ocrResultFormatters) get
// import-path-only edits. ocrResultFormatters gets a sibling import
// (./autofillEngine) — this dissolves the 1A-era residual @/lib/autofillEngine
// type-only dependency.
//
// SPECIAL ALLOWLIST: autofillEngine.ts contains ONE SSR-guarded
// `window.localStorage.getItem('mysuit_ocr_groundtruth')` read inside
// readGroundTruthCandidateRecords(). The check ALLOWS this specific case
// and FAILS on any other browser-storage call (setItem/removeItem/clear,
// sessionStorage, indexedDB) or any newly-introduced browser global.
//
// Read-only. No production code is modified.

import { readFileSync, existsSync, readdirSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, "..");

const NEW_PATH = resolve(ROOT, "src/common/utils/autofillEngine.ts");
const OLD_PATH = resolve(ROOT, "src/lib/autofillEngine.ts");
const LIB_DIR = resolve(ROOT, "src/lib");

const OCR_RESULT_FORMATTERS = resolve(ROOT, "src/common/utils/ocrResultFormatters.ts");
const RUN_OCR_WORKSPACE = resolve(ROOT, "src/components/runocr/RunOcrWorkspace.tsx");
const OCR_RESULT_PANEL = resolve(ROOT, "src/components/runocr/ui/OcrResultPanel.tsx");
const DETAIL_HISTORY_VIEW = resolve(ROOT, "src/components/history/ui/DetailHistoryView.tsx");

// Already-moved guards (whole LIB-CLEAN 1..4D + 4F target).
const TESTSETS_NEW = resolve(ROOT, "src/common/config/testsets.ts");
const PROFILES_NEW = resolve(ROOT, "src/components/test/utils/profiles.ts");
const AXIOS_NEW = resolve(ROOT, "src/common/api/axios.ts");
const LOGIN_NEW = resolve(ROOT, "src/common/storage/login.ts");
const GROUND_TRUTH_NEW = resolve(ROOT, "src/common/storage/groundTruthStore.ts");
const RESTORE_PROFILE_NEW = resolve(ROOT, "src/common/storage/restoreProfileStore.ts");
const THEME_NEW = resolve(ROOT, "src/components/layout/utils/theme.ts");
const TESTSETS_OLD = resolve(ROOT, "src/lib/testsets.ts");
const PROFILES_OLD = resolve(ROOT, "src/lib/profiles.ts");
const AXIOS_OLD = resolve(ROOT, "src/lib/axios.ts");
const LOGIN_OLD = resolve(ROOT, "src/lib/login.ts");
const GROUND_TRUTH_OLD = resolve(ROOT, "src/lib/groundTruthStore.ts");
const RESTORE_PROFILE_OLD = resolve(ROOT, "src/lib/restoreProfileStore.ts");
const THEME_OLD = resolve(ROOT, "src/lib/theme.ts");

const TEST_WORKSPACE = resolve(ROOT, "src/components/test/TestWorkspace.tsx");
const TEST_CORE_DIR = resolve(ROOT, "src/components/test/core");
const AUTORESTORE_WORKSPACE = resolve(ROOT, "src/components/autorestore/AutoRestoreWorkspace.tsx");
const AUTORESTORE_ROUTE = resolve(ROOT, "src/app/autorestore/page.tsx");

const BACKUP_DIR = resolve(
  ROOT,
  "backup",
  "autofill_engine_common_utils_20260522_before_LIB_CLEAN_4F_AUTOFILL_ENGINE_MOVE",
);
const AUTOFILL_BACKUP = resolve(BACKUP_DIR, "autofillEngine.ts");
const OCR_RESULT_FORMATTERS_BACKUP = resolve(BACKUP_DIR, "ocrResultFormatters.ts");
const RUN_OCR_BACKUP = resolve(BACKUP_DIR, "RunOcrWorkspace.tsx");
const OCR_RESULT_PANEL_BACKUP = resolve(BACKUP_DIR, "OcrResultPanel.tsx");
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
checks.new_path_exists = existsSync(NEW_PATH);
checks.old_path_absent = !existsSync(OLD_PATH);

// 2) src/lib empty (or absent). Final guard is LC-4G but we assert
// LC-4F outcome here to fail fast if a leftover slipped in.
const libEntries = existsSync(LIB_DIR)
  ? readdirSync(LIB_DIR).filter((n) => !n.startsWith("."))
  : [];
checks.src_lib_empty_or_absent = libEntries.length === 0;

// 3) Already-moved targets in expected new homes; src/lib old paths absent.
checks.testsets_in_common_config = existsSync(TESTSETS_NEW);
checks.profiles_in_components_test_utils = existsSync(PROFILES_NEW);
checks.axios_in_common_api = existsSync(AXIOS_NEW);
checks.login_in_common_storage = existsSync(LOGIN_NEW);
checks.ground_truth_in_common_storage = existsSync(GROUND_TRUTH_NEW);
checks.restore_profile_in_common_storage = existsSync(RESTORE_PROFILE_NEW);
checks.theme_in_components_layout_utils = existsSync(THEME_NEW);
checks.testsets_absent_in_src_lib = !existsSync(TESTSETS_OLD);
checks.profiles_absent_in_src_lib = !existsSync(PROFILES_OLD);
checks.axios_absent_in_src_lib = !existsSync(AXIOS_OLD);
checks.login_absent_in_src_lib = !existsSync(LOGIN_OLD);
checks.ground_truth_absent_in_src_lib = !existsSync(GROUND_TRUTH_OLD);
checks.restore_profile_absent_in_src_lib = !existsSync(RESTORE_PROFILE_OLD);
checks.theme_absent_in_src_lib = !existsSync(THEME_OLD);

// 4) TestWorkspace + test/core + autorestore route/name unchanged in presence.
checks.TestWorkspace_present = existsSync(TEST_WORKSPACE);
checks.test_core_dir_present = existsSync(TEST_CORE_DIR);
checks.AutoRestoreWorkspace_present = existsSync(AUTORESTORE_WORKSPACE);
checks.autorestore_route_present = existsSync(AUTORESTORE_ROUTE);

// 5) common/utils/autofillEngine.ts purity (with SSR-guarded localStorage
// allowlist).
const newSrc = readSafe(NEW_PATH);
const newCode = newSrc !== null ? stripComments(newSrc) : "";

checks.new_path_no_components_import =
  newSrc !== null && !/from\s+["'][^"']*\/components\//.test(newSrc);
checks.new_path_no_react_import =
  newSrc !== null && !/from\s+["']react(?:-dom)?["']/.test(newSrc);
checks.new_path_no_backend_or_node_fs_import =
  newSrc !== null &&
  !/from\s+["'](?:node:)?(?:fs|fs\/promises|path)["']/.test(newSrc) &&
  !/from\s+["'][^"']*backend[^"']*["']/.test(newSrc);
checks.new_path_no_at_lib_import =
  newSrc !== null && !/from\s+["']@\/lib\/[^"']+["']/.test(newSrc);
checks.new_path_no_fetch_or_xhr =
  newSrc !== null &&
  !/\bfetch\s*\(/.test(newCode) &&
  !/\bXMLHttpRequest\b/.test(newCode);
checks.new_path_no_document_dom =
  newSrc !== null && !/\bdocument\./.test(newCode);
checks.new_path_no_window_navigation =
  newSrc !== null &&
  !/\bwindow\.location\b/.test(newCode) &&
  !/\bwindow\.history\b/.test(newCode);

// SSR-guarded localStorage allowlist:
// - sessionStorage: forbidden anywhere.
// - indexedDB: forbidden anywhere.
// - localStorage.setItem / removeItem / clear: forbidden (no writes).
// - window.localStorage.getItem('mysuit_ocr_groundtruth'): permitted, EXACTLY 1 occurrence.
// - typeof window === "undefined" SSR guard must be present.
const sessionStorageCount = (newCode.match(/\bsessionStorage\b/g) || []).length;
const indexedDbCount = (newCode.match(/\bindexedDB\b/g) || []).length;
const localStorageWriteCount = (newCode.match(/\.localStorage\.(?:setItem|removeItem|clear)\b/g) || []).length;
const allowedLocalStorageReadRe = /window\.localStorage\.getItem\(\s*GROUND_TRUTH_STORAGE_KEY\s*\)|window\.localStorage\.getItem\(\s*["']mysuit_ocr_groundtruth["']\s*\)/g;
const allowedLocalStorageReadCount = (newCode.match(allowedLocalStorageReadRe) || []).length;
const totalWindowLocalStorageCount = (newCode.match(/\bwindow\.localStorage\b/g) || []).length;
const otherWindowLocalStorageCount = totalWindowLocalStorageCount - allowedLocalStorageReadCount;
const ssrGuardCount = (newCode.match(/typeof\s+window\s*===\s*["']undefined["']/g) || []).length;

checks.new_path_no_sessionStorage = sessionStorageCount === 0;
checks.new_path_no_indexedDB = indexedDbCount === 0;
checks.new_path_no_localStorage_writes = localStorageWriteCount === 0;
checks.new_path_other_window_localStorage_zero = otherWindowLocalStorageCount === 0;
checks.new_path_allowed_localStorage_read_exactly_one = allowedLocalStorageReadCount === 1;
checks.new_path_ssr_guard_present = ssrGuardCount >= 1;
checks.new_path_keeps_readGroundTruthCandidateRecords =
  newSrc !== null && /function\s+readGroundTruthCandidateRecords\b/.test(newSrc);

// 6) Internal alias imports preserved (3 deps).
checks.new_path_keeps_bizNumber_import =
  newSrc !== null && /from\s+["']@\/common\/utils\/bizNumber["']/.test(newSrc);
checks.new_path_keeps_historyStore_import =
  newSrc !== null && /from\s+["']@\/common\/storage\/historyStore["']/.test(newSrc);
checks.new_path_keeps_restoreProfile_import =
  newSrc !== null && /from\s+["']@\/common\/storage\/restoreProfileStore["']/.test(newSrc);

// 7) Required exports preserved (19 exports: 10 type + 1 const + 9 fn).
const REQUIRED_TYPE_EXPORTS = [
  "AutofillSource",
  "OutputValueSource",
  "AutofillAction",
  "AutofillSuggestion",
  "AutofillCandidateRecord",
  "AutofillRunStatus",
  "AutofillRunSummary",
  "AutofillFieldMetadata",
  "AutofillOutputFieldLike",
];
const REQUIRED_FN_EXPORTS = [
  "normalizeAutofillFieldKey",
  "isAutofillableField",
  "isEmptyOcrValue",
  "canAutoApplySuggestion",
  "sortAutofillSuggestions",
  "collectInternalAutofillCandidates",
  "buildAutofillSuggestionsFromCandidates",
  "applyAutofillToOutputFields",
  "suggestionsForHistoryField",
];
checks.new_path_required_type_exports_preserved =
  newSrc !== null &&
  REQUIRED_TYPE_EXPORTS.every((n) =>
    new RegExp(`export\\s+type\\s+${n}\\b`).test(newSrc),
  );
checks.new_path_required_fn_exports_preserved =
  newSrc !== null &&
  REQUIRED_FN_EXPORTS.every((n) =>
    new RegExp(`export\\s+function\\s+${n}\\b`).test(newSrc),
  );
checks.new_path_AUTOFILLABLE_FIELDS_preserved =
  newSrc !== null && /export\s+const\s+AUTOFILLABLE_FIELDS\b/.test(newSrc);

// 8) Logic equivalence vs backup (import strip — body byte-identical
// expected since all 3 deps are alias imports that survive the move).
function compareBackup(name, cur, backup, backupPath) {
  if (backup === null) {
    skippedBackupChecks.push({ check: name, reason: `SKIP_WITH_REASON: backup not found: ${backupPath}` });
    return cur !== null;
  }
  return cur !== null && backup !== null &&
    normalizeImportInsensitive(cur) === normalizeImportInsensitive(backup);
}
checks.new_path_logic_unchanged_vs_backup = compareBackup(
  "new_path_logic_unchanged_vs_backup", newSrc, readSafe(AUTOFILL_BACKUP), AUTOFILL_BACKUP,
);

// 9) Importers reference the new path; old `@/lib/autofillEngine` absent in
// code (excluding comments).
const runOcrSrc = readSafe(RUN_OCR_WORKSPACE);
const panelSrc = readSafe(OCR_RESULT_PANEL);
const detailSrc = readSafe(DETAIL_HISTORY_VIEW);
const formattersSrc = readSafe(OCR_RESULT_FORMATTERS);

function importerHasNoOldLib(src) {
  if (src === null) return false;
  const codeOnly = stripComments(src);
  return !/from\s+["']@\/lib\/autofillEngine["']/.test(codeOnly) &&
         !/from\s+["']\.\.\/lib\/autofillEngine["']/.test(codeOnly) &&
         !/from\s+["']\.\.\/\.\.\/lib\/autofillEngine["']/.test(codeOnly);
}
checks.run_ocr_imports_new_path =
  runOcrSrc !== null &&
  /from\s+["']@\/common\/utils\/autofillEngine["']/.test(runOcrSrc) &&
  importerHasNoOldLib(runOcrSrc);
checks.panel_imports_new_path =
  panelSrc !== null &&
  /from\s+["']@\/common\/utils\/autofillEngine["']/.test(panelSrc) &&
  importerHasNoOldLib(panelSrc);
checks.detail_history_imports_new_path =
  detailSrc !== null &&
  /from\s+["']@\/common\/utils\/autofillEngine["']/.test(detailSrc) &&
  importerHasNoOldLib(detailSrc);

// ocrResultFormatters resolves the 1A-era residual dep via SIBLING import.
checks.ocrResultFormatters_imports_sibling_autofillEngine =
  formattersSrc !== null &&
  /from\s+["']\.\/autofillEngine["']/.test(formattersSrc) &&
  importerHasNoOldLib(formattersSrc);

// 10) Importer bodies logic-equivalent to backups (only import path changed).
// TPL-10 phase-aware: RunOcrWorkspace passes activeTemplate prop to
// OcrResultPanel for template_region_canonical projection (new wiring beyond
// LC-4F's import-only scope). Skip the import-only equivalence guard when
// that marker is present.
const _tpl10Shipped_runocr_lc4f = typeof runOcrSrc === "string"
  && /activeTemplate\s*=\s*\{activeTemplateForPanel\}/.test(runOcrSrc);
if (_tpl10Shipped_runocr_lc4f) {
  skippedBackupChecks.push({
    check: "run_ocr_logic_unchanged_vs_backup",
    reason: "SKIP_WITH_REASON: TPL-10 wired activeTemplate prop to OcrResultPanel beyond LC-4F scope",
  });
  checks.run_ocr_logic_unchanged_vs_backup = true;
} else {
  checks.run_ocr_logic_unchanged_vs_backup = compareBackup(
    "run_ocr_logic_unchanged_vs_backup", runOcrSrc, readSafe(RUN_OCR_BACKUP), RUN_OCR_BACKUP,
  );
}
// TPL-8E phase-aware: OcrResultPanel was rewritten to consume
// buildTableResultViewModels. Skip the import-only backup-equivalence guard
// when that marker is present.
const _tpl8eShipped_lc4f = typeof panelSrc === "string"
  && /from\s+["']@\/common\/utils\/tableResultViewModel["']/.test(panelSrc);
if (_tpl8eShipped_lc4f) {
  skippedBackupChecks.push({
    check: "panel_logic_unchanged_vs_backup",
    reason: "SKIP_WITH_REASON: TPL-8E modified OcrResultPanel beyond LC-4F scope (tableResultViewModel marker matched)",
  });
  checks.panel_logic_unchanged_vs_backup = true;
} else {
  checks.panel_logic_unchanged_vs_backup = compareBackup(
    "panel_logic_unchanged_vs_backup", panelSrc, readSafe(OCR_RESULT_PANEL_BACKUP), OCR_RESULT_PANEL_BACKUP,
  );
}
checks.detail_history_logic_unchanged_vs_backup = compareBackup(
  "detail_history_logic_unchanged_vs_backup", detailSrc, readSafe(DETAIL_HISTORY_BACKUP), DETAIL_HISTORY_BACKUP,
);
checks.ocrResultFormatters_logic_unchanged_vs_backup = compareBackup(
  "ocrResultFormatters_logic_unchanged_vs_backup", formattersSrc, readSafe(OCR_RESULT_FORMATTERS_BACKUP), OCR_RESULT_FORMATTERS_BACKUP,
);

// 11) Global residual scan: zero @/lib/* imports anywhere in src (this is
// the LC-4G precursor — final guard will be LC-4G's own script).
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
const LIB_RESIDUAL_RE = /from\s+["'](?:@\/lib\/[^"']+|\.\.\/lib\/[^"']+|\.\.\/\.\.\/lib\/[^"']+)["']/g;
const libResiduals = [];
for (const f of srcFiles) {
  const s = readSafe(f);
  if (!s) continue;
  const codeOnly = stripComments(s);
  let m;
  while ((m = LIB_RESIDUAL_RE.exec(codeOnly))) {
    libResiduals.push({ file: f, match: m[0] });
  }
}
checks.no_residual_lib_imports_in_src_code = libResiduals.length === 0;

const summary = {
  task: "LIB-CLEAN-4F-AUTOFILL-ENGINE-MOVE",
  paths: {
    new_path: NEW_PATH,
    old_path: OLD_PATH,
    lib_dir: LIB_DIR,
    run_ocr_workspace: RUN_OCR_WORKSPACE,
    ocr_result_panel: OCR_RESULT_PANEL,
    detail_history_view: DETAIL_HISTORY_VIEW,
    ocr_result_formatters: OCR_RESULT_FORMATTERS,
  },
  found_in_lib: libEntries,
  ssr_localstorage_allowlist: {
    permitted_pattern: "window.localStorage.getItem(GROUND_TRUTH_STORAGE_KEY) — mysuit_ocr_groundtruth",
    allowed_count: 1,
    actual_allowed_reads: allowedLocalStorageReadCount,
    other_window_localstorage_uses: otherWindowLocalStorageCount,
    ssr_guards_present: ssrGuardCount,
    writes: localStorageWriteCount,
  },
  checks,
  skippedBackupChecks,
  libResiduals,
};
console.log(JSON.stringify(summary, null, 2));

const required = [
  "new_path_exists",
  "old_path_absent",
  "src_lib_empty_or_absent",
  "testsets_in_common_config",
  "profiles_in_components_test_utils",
  "axios_in_common_api",
  "login_in_common_storage",
  "ground_truth_in_common_storage",
  "restore_profile_in_common_storage",
  "theme_in_components_layout_utils",
  "testsets_absent_in_src_lib",
  "profiles_absent_in_src_lib",
  "axios_absent_in_src_lib",
  "login_absent_in_src_lib",
  "ground_truth_absent_in_src_lib",
  "restore_profile_absent_in_src_lib",
  "theme_absent_in_src_lib",
  "TestWorkspace_present",
  "test_core_dir_present",
  "AutoRestoreWorkspace_present",
  "autorestore_route_present",
  "new_path_no_components_import",
  "new_path_no_react_import",
  "new_path_no_backend_or_node_fs_import",
  "new_path_no_at_lib_import",
  "new_path_no_fetch_or_xhr",
  "new_path_no_document_dom",
  "new_path_no_window_navigation",
  "new_path_no_sessionStorage",
  "new_path_no_indexedDB",
  "new_path_no_localStorage_writes",
  "new_path_other_window_localStorage_zero",
  "new_path_allowed_localStorage_read_exactly_one",
  "new_path_ssr_guard_present",
  "new_path_keeps_readGroundTruthCandidateRecords",
  "new_path_keeps_bizNumber_import",
  "new_path_keeps_historyStore_import",
  "new_path_keeps_restoreProfile_import",
  "new_path_required_type_exports_preserved",
  "new_path_required_fn_exports_preserved",
  "new_path_AUTOFILLABLE_FIELDS_preserved",
  "new_path_logic_unchanged_vs_backup",
  "run_ocr_imports_new_path",
  "panel_imports_new_path",
  "detail_history_imports_new_path",
  "ocrResultFormatters_imports_sibling_autofillEngine",
  "run_ocr_logic_unchanged_vs_backup",
  "panel_logic_unchanged_vs_backup",
  "detail_history_logic_unchanged_vs_backup",
  "ocrResultFormatters_logic_unchanged_vs_backup",
  "no_residual_lib_imports_in_src_code",
];
const allPass = required.every((k) => checks[k] === true);
const verdict = allPass
  ? (skippedBackupChecks.length > 0 ? "PASS_WITH_SKIPPED_BACKUP" : "PASS")
  : "FAIL";
console.log(`[AUTOFILL_ENGINE_COMMON_UTILS_MOVE_LC4F] ${verdict}`);
process.exit(allPass ? 0 : 1);
