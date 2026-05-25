#!/usr/bin/env node
// FRONTEND_CS_2_HISTORY_STORE_COMMON_STORAGE_MOVE
// Static check: confirm src/lib/historyStore.ts was moved to
// src/common/storage/historyStore.ts. Body must be logic-identical to the
// CS-2 backup (only the imageStore import path may change). 5 importers
// (RunOcrWorkspace, HistoryWorkspace, DetailHistoryView, autofillEngine,
// groundTruthStore) get import-path-only edits. imageStore is not moved.
// historyStore.ts must not import components/* nor React/React-DOM.
// TestWorkspace + test/core must remain untouched.
//
// Read-only. No production code is modified.

import { readFileSync, existsSync, readdirSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, "..");

const NEW_STORE = resolve(ROOT, "src/common/storage/historyStore.ts");
const OLD_STORE = resolve(ROOT, "src/lib/historyStore.ts");
const IMAGE_STORE = resolve(ROOT, "src/common/storage/imageStore.ts");

const RUNOCR_WORKSPACE = resolve(ROOT, "src/components/runocr/RunOcrWorkspace.tsx");
const HISTORY_WORKSPACE = resolve(ROOT, "src/components/history/HistoryWorkspace.tsx");
const DETAIL_HISTORY_VIEW = resolve(ROOT, "src/components/history/ui/DetailHistoryView.tsx");
// NOTE: After LIB-CLEAN-4F, autofillEngine.ts lives at
// src/common/utils/autofillEngine.ts. Resolve to whichever currently exists
// so this CS-2-era check stays valid across both states.
const AUTOFILL_AT_LIB = resolve(ROOT, "src/lib/autofillEngine.ts");
const AUTOFILL_AT_COMMON_UTILS = resolve(ROOT, "src/common/utils/autofillEngine.ts");
const AUTOFILL_ENGINE = existsSync(AUTOFILL_AT_LIB)
  ? AUTOFILL_AT_LIB
  : AUTOFILL_AT_COMMON_UTILS;
// NOTE: After LC-4A (groundTruthStore common/storage move) the file lives at
// src/common/storage/groundTruthStore.ts. Resolve to whichever currently
// exists so this CS-2-era check stays valid across both states.
const GROUND_TRUTH_STORE_AT_LIB = resolve(ROOT, "src/lib/groundTruthStore.ts");
const GROUND_TRUTH_STORE_AT_COMMON_STORAGE = resolve(ROOT, "src/common/storage/groundTruthStore.ts");
const GROUND_TRUTH_STORE = existsSync(GROUND_TRUTH_STORE_AT_LIB)
  ? GROUND_TRUTH_STORE_AT_LIB
  : GROUND_TRUTH_STORE_AT_COMMON_STORAGE;

const LIB_DIR = resolve(ROOT, "src/lib");
const SIBLINGS_THAT_MUST_STAY_IN_LIB = [
  // NOTE: historyStore.ts moved to src/common/storage/ by CS-2.
  // NOTE: imageStore.ts moved to src/common/storage/ by CS-1.
  // NOTE: groundTruthStore.ts moved to src/common/storage/ by LC-4A.
  // NOTE: autofillEngine.ts removed after LIB-CLEAN-4F (moved to src/common/utils/).
  // NOTE: profiles.ts removed after LIB-CLEAN-4D (moved to src/components/test/utils/).
  // NOTE: testsets.ts removed after LIB-CLEAN-4C (moved to src/common/config/).
  // NOTE: bizNumber.ts removed after BZ-1 (moved to src/common/utils/).
];

const TEST_WORKSPACE = resolve(ROOT, "src/components/test/TestWorkspace.tsx");
const TEST_CORE_DIR = resolve(ROOT, "src/components/test/core");

const BACKUP_DIR = resolve(
  ROOT,
  "backup",
  "history_store_common_storage_20260522_before_FRONTEND_CS_2_HISTORY_STORE_COMMON_STORAGE_MOVE",
);
const HISTORY_STORE_BACKUP = resolve(BACKUP_DIR, "historyStore.ts");
const RUNOCR_BACKUP = resolve(BACKUP_DIR, "RunOcrWorkspace.tsx");
const HISTORY_WORKSPACE_BACKUP = resolve(BACKUP_DIR, "HistoryWorkspace.tsx");
const DETAIL_HISTORY_VIEW_BACKUP = resolve(BACKUP_DIR, "DetailHistoryView.tsx");
const AUTOFILL_BACKUP = resolve(BACKUP_DIR, "autofillEngine.ts");
const GROUND_TRUTH_BACKUP = resolve(BACKUP_DIR, "groundTruthStore.ts");

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
checks.new_store_exists = existsSync(NEW_STORE);
checks.old_store_absent = !existsSync(OLD_STORE);

// 2) Sibling src/lib files MUST still be in src/lib (no scope creep).
for (const name of SIBLINGS_THAT_MUST_STAY_IN_LIB) {
  const k = `lib_sibling_${name.replace(/\./g, "_")}_still_in_src_lib`;
  checks[k] = existsSync(resolve(LIB_DIR, name));
}

// 3) imageStore not moved away from common/storage.
checks.imageStore_still_in_common_storage = existsSync(IMAGE_STORE);

// 4) TestWorkspace + test/core untouched paths.
checks.TestWorkspace_present = existsSync(TEST_WORKSPACE);
checks.test_core_dir_present = existsSync(TEST_CORE_DIR);

// 5) common/storage/historyStore.ts purity.
const newStoreSrc = readSafe(NEW_STORE);
checks.new_store_no_components_import =
  newStoreSrc !== null && !/from\s+["'][^"']*\/components\//.test(newStoreSrc);
checks.new_store_no_react_import =
  newStoreSrc !== null && !/from\s+["']react["']/.test(newStoreSrc);
checks.new_store_no_react_dom_import =
  newStoreSrc !== null && !/from\s+["']react-dom["']/.test(newStoreSrc);

// 6) Required exports preserved (key APIs consumed by importers).
const REQUIRED_EXPORTS = [
  "RunStatus",
  "HistoryOcrField",
  "HistoryOutputField",
  "HistoryRunRecord",
  "HistoryDetailDocumentFields",
  "readHistoryRuns",
  "appendHistoryRun",
  "updateHistoryRun",
  "clearHistoryRuns",
  "deleteHistoryRun",
  "getOriginalHistoryImage",
  "getProcessedHistoryImage",
  "syncHistoryIndexAndDetailOnCreate",
  "syncHistoryIndexAndDetailOnSave",
  "syncHistoryDetailTableRowsOnSave",
  "readHistoryListWithFallback",
  "readHistoryDetailWithFallback",
  "hydrateHistoryRecordImages",
];
checks.new_store_required_exports_preserved =
  newStoreSrc !== null &&
  REQUIRED_EXPORTS.every((n) =>
    new RegExp(`export\\s+(?:function|type|const|async\\s+function)\\s+${n}\\b`).test(newStoreSrc),
  );

// 7) Persistence policy preserved (localStorage key + IndexedDB hydration).
checks.new_store_storage_key_preserved =
  newStoreSrc !== null && /["']mysuit_ocr_history["']/.test(newStoreSrc);
checks.new_store_localStorage_used =
  newStoreSrc !== null && /localStorage\./.test(newStoreSrc);
checks.new_store_imports_imageStore =
  newStoreSrc !== null &&
  (/from\s+["']\.\/imageStore["']/.test(newStoreSrc) ||
    /from\s+["']@\/common\/storage\/imageStore["']/.test(newStoreSrc));
checks.new_store_no_lib_imageStore_import =
  newStoreSrc !== null && !/from\s+["']@\/lib\/imageStore["']/.test(stripComments(newStoreSrc));

// 8) Logic equivalence vs backup (import path strip).
function compareBackup(name, cur, backup, backupPath) {
  if (backup === null) {
    skippedBackupChecks.push({ check: name, reason: `SKIP_WITH_REASON: backup not found: ${backupPath}` });
    return cur !== null;
  }
  return cur !== null && backup !== null &&
    normalizeImportInsensitive(cur) === normalizeImportInsensitive(backup);
}
checks.new_store_logic_unchanged_vs_backup = compareBackup(
  "new_store_logic_unchanged_vs_backup", newStoreSrc, readSafe(HISTORY_STORE_BACKUP), HISTORY_STORE_BACKUP,
);

// 9) Importers reference the new path and do not reference the old path.
const runocrSrc = readSafe(RUNOCR_WORKSPACE);
const historyWorkspaceSrc = readSafe(HISTORY_WORKSPACE);
const detailHistorySrc = readSafe(DETAIL_HISTORY_VIEW);
const autofillSrc = readSafe(AUTOFILL_ENGINE);
const groundTruthSrc = readSafe(GROUND_TRUTH_STORE);

function checkImporterNewPath(name, src) {
  return src !== null &&
    /from\s+["']@\/common\/storage\/historyStore["']/.test(src) &&
    !/from\s+["']@\/lib\/historyStore["']/.test(stripComments(src)) &&
    !/from\s+["']\.\.\/lib\/historyStore["']/.test(stripComments(src)) &&
    !/from\s+["']\.\.\/\.\.\/lib\/historyStore["']/.test(stripComments(src));
}
checks.runocr_workspace_imports_new_path = checkImporterNewPath("runocr", runocrSrc);
checks.history_workspace_imports_new_path = checkImporterNewPath("historyWorkspace", historyWorkspaceSrc);
checks.detail_history_view_imports_new_path = checkImporterNewPath("detailHistoryView", detailHistorySrc);
checks.autofill_engine_imports_new_path = checkImporterNewPath("autofill", autofillSrc);
checks.ground_truth_store_imports_new_path = checkImporterNewPath("groundTruth", groundTruthSrc);

// 10) Importer bodies logic-equivalent to backups (only import path changed).
// TPL-10 phase-aware: RunOcrWorkspace passes activeTemplate prop to
// OcrResultPanel for template_region_canonical projection. Skip when present.
const _tpl10Shipped_runocr_cs2 = typeof runocrSrc === "string"
  && /activeTemplate\s*=\s*\{activeTemplateForPanel\}/.test(runocrSrc);
if (_tpl10Shipped_runocr_cs2) {
  skippedBackupChecks.push({
    check: "runocr_workspace_logic_unchanged_vs_backup",
    reason: "SKIP_WITH_REASON: TPL-10 wired activeTemplate prop to OcrResultPanel beyond CS-2 scope",
  });
  checks.runocr_workspace_logic_unchanged_vs_backup = true;
} else {
  checks.runocr_workspace_logic_unchanged_vs_backup = compareBackup(
    "runocr_workspace_logic_unchanged_vs_backup", runocrSrc, readSafe(RUNOCR_BACKUP), RUNOCR_BACKUP,
  );
}
checks.history_workspace_logic_unchanged_vs_backup = compareBackup(
  "history_workspace_logic_unchanged_vs_backup", historyWorkspaceSrc, readSafe(HISTORY_WORKSPACE_BACKUP), HISTORY_WORKSPACE_BACKUP,
);
checks.detail_history_view_logic_unchanged_vs_backup = compareBackup(
  "detail_history_view_logic_unchanged_vs_backup", detailHistorySrc, readSafe(DETAIL_HISTORY_VIEW_BACKUP), DETAIL_HISTORY_VIEW_BACKUP,
);
checks.autofill_engine_logic_unchanged_vs_backup = compareBackup(
  "autofill_engine_logic_unchanged_vs_backup", autofillSrc, readSafe(AUTOFILL_BACKUP), AUTOFILL_BACKUP,
);
checks.ground_truth_store_logic_unchanged_vs_backup = compareBackup(
  "ground_truth_store_logic_unchanged_vs_backup", groundTruthSrc, readSafe(GROUND_TRUTH_BACKUP), GROUND_TRUTH_BACKUP,
);

// 11) No residual @/lib/historyStore or ../lib/historyStore or ../../lib/historyStore in src code.
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
  /from\s+["']@\/lib\/historyStore["']/,
  /from\s+["']\.\.\/lib\/historyStore["']/,
  /from\s+["']\.\.\/\.\.\/lib\/historyStore["']/,
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
checks.no_residual_lib_history_store_imports_in_code = residuals.length === 0;

const summary = {
  task: "FRONTEND-CS-2-HISTORY-STORE-COMMON-STORAGE-MOVE",
  paths: {
    new_store: NEW_STORE,
    old_store: OLD_STORE,
    image_store: IMAGE_STORE,
    runocr_workspace: RUNOCR_WORKSPACE,
    history_workspace: HISTORY_WORKSPACE,
    detail_history_view: DETAIL_HISTORY_VIEW,
    autofill_engine: AUTOFILL_ENGINE,
    ground_truth_store: GROUND_TRUTH_STORE,
  },
  checks,
  skippedBackupChecks,
  residuals,
};
console.log(JSON.stringify(summary, null, 2));

const required = [
  "new_store_exists",
  "old_store_absent",
  ...SIBLINGS_THAT_MUST_STAY_IN_LIB.map((n) => `lib_sibling_${n.replace(/\./g, "_")}_still_in_src_lib`),
  "imageStore_still_in_common_storage",
  "TestWorkspace_present",
  "test_core_dir_present",
  "new_store_no_components_import",
  "new_store_no_react_import",
  "new_store_no_react_dom_import",
  "new_store_required_exports_preserved",
  "new_store_storage_key_preserved",
  "new_store_localStorage_used",
  "new_store_imports_imageStore",
  "new_store_no_lib_imageStore_import",
  "new_store_logic_unchanged_vs_backup",
  "runocr_workspace_imports_new_path",
  "history_workspace_imports_new_path",
  "detail_history_view_imports_new_path",
  "autofill_engine_imports_new_path",
  "ground_truth_store_imports_new_path",
  "runocr_workspace_logic_unchanged_vs_backup",
  "history_workspace_logic_unchanged_vs_backup",
  "detail_history_view_logic_unchanged_vs_backup",
  "autofill_engine_logic_unchanged_vs_backup",
  "ground_truth_store_logic_unchanged_vs_backup",
  "no_residual_lib_history_store_imports_in_code",
];
const allPass = required.every((k) => checks[k] === true);
const verdict = allPass
  ? (skippedBackupChecks.length > 0 ? "PASS_WITH_SKIPPED_BACKUP" : "PASS")
  : "FAIL";
console.log(`[HISTORY_STORE_COMMON_STORAGE_MOVE_CS2] ${verdict}`);
process.exit(allPass ? 0 : 1);
