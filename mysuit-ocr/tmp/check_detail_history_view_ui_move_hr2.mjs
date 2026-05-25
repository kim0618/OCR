#!/usr/bin/env node
// FRONTEND_HR_2_DETAIL_HISTORY_VIEW_UI_MOVE
// Static check: confirm src/components/history/DetailHistoryView.tsx was
// moved to src/components/history/ui/DetailHistoryView.tsx. Body must be
// logic-identical to the HR-2 backup (only the single relative import to
// `../layout/AppProviders` shifts depth to `../../layout/AppProviders`).
// HistoryWorkspace.tsx is the sole production importer and keeps its
// original path with only the DetailHistoryView import path corrected.
// historyStore / imageStore / groundTruthStore / restoreProfileStore /
// autofillEngine must NOT be modified. The two HR-1 popup files and
// TestWorkspace must also remain untouched.
//
// Read-only. No production code is modified.

import { readFileSync, existsSync, readdirSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, "..");

const NEW_DETAIL = resolve(ROOT, "src/components/history/ui/DetailHistoryView.tsx");
const OLD_DETAIL = resolve(ROOT, "src/components/history/DetailHistoryView.tsx");

const HISTORY_WORKSPACE = resolve(ROOT, "src/components/history/HistoryWorkspace.tsx");
const CREATE_POPUP = resolve(ROOT, "src/components/history/ui/CreateHistoryPopup.tsx");
const EDIT_POPUP = resolve(ROOT, "src/components/history/ui/EditHistoryPopup.tsx");

// NOTE: After CS-2 (historyStore common/storage move) the file lives at
// src/common/storage/historyStore.ts. Resolve to whichever currently exists
// so this HR-2-era check stays valid across both states.
const HISTORY_STORE_AT_LIB = resolve(ROOT, "src/lib/historyStore.ts");
const HISTORY_STORE_AT_COMMON_STORAGE = resolve(ROOT, "src/common/storage/historyStore.ts");
const HISTORY_STORE = existsSync(HISTORY_STORE_AT_LIB)
  ? HISTORY_STORE_AT_LIB
  : HISTORY_STORE_AT_COMMON_STORAGE;
// NOTE: After CS-1 (imageStore common/storage move) the file lives at
// src/common/storage/imageStore.ts. Resolve to whichever currently exists
// so this HR-2-era check stays valid across both states.
const IMAGE_STORE_AT_LIB = resolve(ROOT, "src/lib/imageStore.ts");
const IMAGE_STORE_AT_COMMON_STORAGE = resolve(ROOT, "src/common/storage/imageStore.ts");
const IMAGE_STORE = existsSync(IMAGE_STORE_AT_LIB)
  ? IMAGE_STORE_AT_LIB
  : IMAGE_STORE_AT_COMMON_STORAGE;
// NOTE: After LC-4A (groundTruthStore common/storage move) the file lives at
// src/common/storage/groundTruthStore.ts. Resolve to whichever currently
// exists so this HR-2-era check stays valid across both states.
const GROUND_TRUTH_STORE_AT_LIB = resolve(ROOT, "src/lib/groundTruthStore.ts");
const GROUND_TRUTH_STORE_AT_COMMON_STORAGE = resolve(ROOT, "src/common/storage/groundTruthStore.ts");
const GROUND_TRUTH_STORE = existsSync(GROUND_TRUTH_STORE_AT_LIB)
  ? GROUND_TRUTH_STORE_AT_LIB
  : GROUND_TRUTH_STORE_AT_COMMON_STORAGE;
// NOTE: After LC-4B (restoreProfileStore common/storage move) the file lives
// at src/common/storage/restoreProfileStore.ts. Resolve to whichever
// currently exists so this HR-2-era check stays valid across both states.
const RESTORE_PROFILE_STORE_AT_LIB = resolve(ROOT, "src/lib/restoreProfileStore.ts");
const RESTORE_PROFILE_STORE_AT_COMMON_STORAGE = resolve(ROOT, "src/common/storage/restoreProfileStore.ts");
const RESTORE_PROFILE_STORE = existsSync(RESTORE_PROFILE_STORE_AT_LIB)
  ? RESTORE_PROFILE_STORE_AT_LIB
  : RESTORE_PROFILE_STORE_AT_COMMON_STORAGE;
// NOTE: After LIB-CLEAN-4F, autofillEngine.ts lives at
// src/common/utils/autofillEngine.ts. Resolve to whichever currently exists
// so this HR-2-era check stays valid across both states.
const AUTOFILL_AT_LIB = resolve(ROOT, "src/lib/autofillEngine.ts");
const AUTOFILL_AT_COMMON_UTILS = resolve(ROOT, "src/common/utils/autofillEngine.ts");
const AUTOFILL_ENGINE = existsSync(AUTOFILL_AT_LIB)
  ? AUTOFILL_AT_LIB
  : AUTOFILL_AT_COMMON_UTILS;

const TEST_WORKSPACE = resolve(ROOT, "src/components/test/TestWorkspace.tsx");
const TEST_CORE_DIR = resolve(ROOT, "src/components/test/core");

const BACKUP_DIR = resolve(
  ROOT,
  "backup",
  "detail_history_view_ui_20260522_before_FRONTEND_HR_2_DETAIL_HISTORY_VIEW_UI_MOVE",
);
const DETAIL_BACKUP = resolve(BACKUP_DIR, "DetailHistoryView.tsx");
const HISTORY_WORKSPACE_BACKUP = resolve(BACKUP_DIR, "HistoryWorkspace.tsx");

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
checks.new_detail_exists = existsSync(NEW_DETAIL);
checks.old_detail_absent = !existsSync(OLD_DETAIL);

// 2) Sibling files in history/ui still present (HR-1 artefacts).
checks.HistoryWorkspace_present = existsSync(HISTORY_WORKSPACE);
checks.CreateHistoryPopup_still_in_history_ui = existsSync(CREATE_POPUP);
checks.EditHistoryPopup_still_in_history_ui = existsSync(EDIT_POPUP);

// 3) Store/util layer files NOT touched (still present).
checks.historyStore_present = existsSync(HISTORY_STORE);
checks.imageStore_present = existsSync(IMAGE_STORE);
checks.groundTruthStore_present = existsSync(GROUND_TRUTH_STORE);
checks.restoreProfileStore_present = existsSync(RESTORE_PROFILE_STORE);
checks.autofillEngine_present = existsSync(AUTOFILL_ENGINE);

// 4) TestWorkspace + test/core untouched paths.
checks.TestWorkspace_present = existsSync(TEST_WORKSPACE);
checks.test_core_dir_present = existsSync(TEST_CORE_DIR);

// 5) New DetailHistoryView identity preserved.
const newDetailSrc = readSafe(NEW_DETAIL);
checks.new_detail_default_export_preserved =
  newDetailSrc !== null && /export\s+default\s+function\s+DetailHistoryView\b/.test(newDetailSrc);
// Internal import depth correctly bumped for AppProviders.
checks.new_detail_app_providers_import_depth_adjusted =
  newDetailSrc !== null &&
  /from\s+["']\.\.\/\.\.\/layout\/AppProviders["']/.test(newDetailSrc) &&
  !/from\s+["']\.\.\/layout\/AppProviders["']/.test(stripComments(newDetailSrc));
// Required store/util identifiers preserved (move-only invariant — these
// imports use @/ aliases and stay valid).
// NOTE: After CS-2 (historyStore moved to src/common/storage/), the alias is
// @/common/storage/historyStore. Accept either form so this HR-2-era check
// stays valid across both states.
checks.new_detail_imports_historyStore =
  newDetailSrc !== null &&
  (/from\s+["']@\/lib\/historyStore["']/.test(newDetailSrc) ||
    /from\s+["']@\/common\/storage\/historyStore["']/.test(newDetailSrc));
checks.new_detail_imports_groundTruthStore =
  newDetailSrc !== null &&
  (/from\s+["']@\/lib\/groundTruthStore["']/.test(newDetailSrc) ||
    /from\s+["']@\/common\/storage\/groundTruthStore["']/.test(newDetailSrc));
checks.new_detail_imports_restoreProfileStore =
  newDetailSrc !== null &&
  (/from\s+["']@\/lib\/restoreProfileStore["']/.test(newDetailSrc) ||
    /from\s+["']@\/common\/storage\/restoreProfileStore["']/.test(newDetailSrc));
// NOTE: After LIB-CLEAN-4F, accept either @/lib/autofillEngine or
// @/common/utils/autofillEngine.
checks.new_detail_imports_autofillEngine =
  newDetailSrc !== null &&
  (/from\s+["']@\/lib\/autofillEngine["']/.test(newDetailSrc) ||
    /from\s+["']@\/common\/utils\/autofillEngine["']/.test(newDetailSrc));

// 6) Logic equivalence vs backup (normalizeImportInsensitive strips import
//    paths so the AppProviders depth bump is collapsed).
const detailBackup = readSafe(DETAIL_BACKUP);
if (detailBackup === null) {
  skippedBackupChecks.push({
    check: "new_detail_logic_unchanged_vs_backup",
    reason: `SKIP_WITH_REASON: backup not found: ${DETAIL_BACKUP}`,
  });
}
checks.new_detail_logic_unchanged_vs_backup =
  newDetailSrc !== null && detailBackup !== null &&
  normalizeImportInsensitive(newDetailSrc) === normalizeImportInsensitive(detailBackup);

// 7) HistoryWorkspace imports the new path; body logic equivalent except for
//    the one import path string.
const workspaceSrc = readSafe(HISTORY_WORKSPACE);
const workspaceBackup = readSafe(HISTORY_WORKSPACE_BACKUP);
checks.workspace_imports_new_detail =
  workspaceSrc !== null &&
  /from\s+["']\.\/ui\/DetailHistoryView["']/.test(workspaceSrc) &&
  !/from\s+["']\.\/DetailHistoryView["']/.test(stripComments(workspaceSrc));
function compareBackup(name, cur, backup, backupPath) {
  if (backup === null) {
    skippedBackupChecks.push({ check: name, reason: `SKIP_WITH_REASON: backup not found: ${backupPath}` });
    return cur !== null;
  }
  return cur !== null && backup !== null &&
    normalizeImportInsensitive(cur) === normalizeImportInsensitive(backup);
}
checks.workspace_logic_unchanged_vs_backup = compareBackup(
  "workspace_logic_unchanged_vs_backup", workspaceSrc, workspaceBackup, HISTORY_WORKSPACE_BACKUP,
);

// 8) Popup default exports still preserved (sanity — CC-2/HR-1 invariants).
const createPopupSrc = readSafe(CREATE_POPUP);
const editPopupSrc = readSafe(EDIT_POPUP);
checks.CreateHistoryPopup_default_export_preserved =
  createPopupSrc !== null && /export\s+default\s+function\s+CreateHistoryPopup\b/.test(createPopupSrc);
checks.EditHistoryPopup_default_export_preserved =
  editPopupSrc !== null && /export\s+default\s+function\s+EditHistoryPopup\b/.test(editPopupSrc);

// 9) Store/util files still expose exports (sanity, no body comparison).
const historyStoreSrc = readSafe(HISTORY_STORE);
const imageStoreSrc = readSafe(IMAGE_STORE);
const groundTruthStoreSrc = readSafe(GROUND_TRUTH_STORE);
const restoreProfileStoreSrc = readSafe(RESTORE_PROFILE_STORE);
const autofillEngineSrc = readSafe(AUTOFILL_ENGINE);
checks.historyStore_has_exports = historyStoreSrc !== null && /export\s+/.test(historyStoreSrc);
checks.imageStore_has_exports = imageStoreSrc !== null && /export\s+/.test(imageStoreSrc);
checks.groundTruthStore_has_exports = groundTruthStoreSrc !== null && /export\s+/.test(groundTruthStoreSrc);
checks.restoreProfileStore_has_exports = restoreProfileStoreSrc !== null && /export\s+/.test(restoreProfileStoreSrc);
checks.autofillEngine_has_exports = autofillEngineSrc !== null && /export\s+/.test(autofillEngineSrc);

// 10) No residual `./DetailHistoryView` / `../DetailHistoryView` /
//     `components/history/DetailHistoryView` references in src/ CODE
//     (excluding comments).
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
  /from\s+["']\.\/DetailHistoryView["']/,
  /from\s+["']\.\.\/DetailHistoryView["']/,
  /from\s+["'][^"']*components\/history\/DetailHistoryView["']/,
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
checks.no_residual_old_detail_imports_in_code = residuals.length === 0;

const summary = {
  task: "FRONTEND-HR-2-DETAIL-HISTORY-VIEW-UI-MOVE",
  paths: {
    new_detail: NEW_DETAIL,
    old_detail: OLD_DETAIL,
    history_workspace: HISTORY_WORKSPACE,
    create_popup: CREATE_POPUP,
    edit_popup: EDIT_POPUP,
  },
  checks,
  skippedBackupChecks,
  residuals,
};
console.log(JSON.stringify(summary, null, 2));

const required = [
  "new_detail_exists",
  "old_detail_absent",
  "HistoryWorkspace_present",
  "CreateHistoryPopup_still_in_history_ui",
  "EditHistoryPopup_still_in_history_ui",
  "historyStore_present",
  "imageStore_present",
  "groundTruthStore_present",
  "restoreProfileStore_present",
  "autofillEngine_present",
  "TestWorkspace_present",
  "test_core_dir_present",
  "new_detail_default_export_preserved",
  "new_detail_app_providers_import_depth_adjusted",
  "new_detail_imports_historyStore",
  "new_detail_imports_groundTruthStore",
  "new_detail_imports_restoreProfileStore",
  "new_detail_imports_autofillEngine",
  "new_detail_logic_unchanged_vs_backup",
  "workspace_imports_new_detail",
  "workspace_logic_unchanged_vs_backup",
  "CreateHistoryPopup_default_export_preserved",
  "EditHistoryPopup_default_export_preserved",
  "historyStore_has_exports",
  "imageStore_has_exports",
  "groundTruthStore_has_exports",
  "restoreProfileStore_has_exports",
  "autofillEngine_has_exports",
  "no_residual_old_detail_imports_in_code",
];
const allPass = required.every((k) => checks[k] === true);
const verdict = allPass
  ? (skippedBackupChecks.length > 0 ? "PASS_WITH_SKIPPED_BACKUP" : "PASS")
  : "FAIL";
console.log(`[DETAIL_HISTORY_VIEW_UI_MOVE_HR2] ${verdict}`);
process.exit(allPass ? 0 : 1);
