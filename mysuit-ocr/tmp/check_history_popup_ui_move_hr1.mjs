#!/usr/bin/env node
// FRONTEND_HR_1_HISTORY_POPUP_UI_MOVE
// Static check: confirm src/components/history/popup/CreateHistoryPopup.tsx
// and src/components/history/popup/EditHistoryPopup.tsx were moved to
// src/components/history/ui/. Bodies must be logic-identical to the HR-1
// backup. HistoryWorkspace.tsx is the sole production importer and keeps
// its original path with only the popup import paths corrected.
// DetailHistoryView.tsx and historyStore/imageStore must NOT be touched.
// src/components/history/popup directory may be empty or removed.
//
// Read-only. No production code is modified.

import { readFileSync, existsSync, readdirSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, "..");

const NEW_CREATE = resolve(ROOT, "src/components/history/ui/CreateHistoryPopup.tsx");
const NEW_EDIT = resolve(ROOT, "src/components/history/ui/EditHistoryPopup.tsx");
const OLD_CREATE = resolve(ROOT, "src/components/history/popup/CreateHistoryPopup.tsx");
const OLD_EDIT = resolve(ROOT, "src/components/history/popup/EditHistoryPopup.tsx");
const OLD_POPUP_DIR = resolve(ROOT, "src/components/history/popup");

const HISTORY_WORKSPACE = resolve(ROOT, "src/components/history/HistoryWorkspace.tsx");
// NOTE: After HR-2 (DetailHistoryView ui move) the file lives at
// src/components/history/ui/DetailHistoryView.tsx. Resolve to whichever
// currently exists so this HR-1-era check stays valid across both states.
const DETAIL_HISTORY_AT_HISTORY = resolve(ROOT, "src/components/history/DetailHistoryView.tsx");
const DETAIL_HISTORY_AT_HISTORY_UI = resolve(ROOT, "src/components/history/ui/DetailHistoryView.tsx");
const DETAIL_HISTORY = existsSync(DETAIL_HISTORY_AT_HISTORY)
  ? DETAIL_HISTORY_AT_HISTORY
  : DETAIL_HISTORY_AT_HISTORY_UI;

// NOTE: After CS-2 (historyStore common/storage move) the file lives at
// src/common/storage/historyStore.ts. Resolve to whichever currently exists
// so this HR-1-era check stays valid across both states.
const HISTORY_STORE_AT_LIB = resolve(ROOT, "src/lib/historyStore.ts");
const HISTORY_STORE_AT_COMMON_STORAGE = resolve(ROOT, "src/common/storage/historyStore.ts");
const HISTORY_STORE = existsSync(HISTORY_STORE_AT_LIB)
  ? HISTORY_STORE_AT_LIB
  : HISTORY_STORE_AT_COMMON_STORAGE;
// NOTE: After CS-1 (imageStore common/storage move) the file lives at
// src/common/storage/imageStore.ts. Resolve to whichever currently exists
// so this HR-1-era check stays valid across both states.
const IMAGE_STORE_AT_LIB = resolve(ROOT, "src/lib/imageStore.ts");
const IMAGE_STORE_AT_COMMON_STORAGE = resolve(ROOT, "src/common/storage/imageStore.ts");
const IMAGE_STORE = existsSync(IMAGE_STORE_AT_LIB)
  ? IMAGE_STORE_AT_LIB
  : IMAGE_STORE_AT_COMMON_STORAGE;

const TEST_WORKSPACE = resolve(ROOT, "src/components/test/TestWorkspace.tsx");
const TEST_CORE_DIR = resolve(ROOT, "src/components/test/core");

const BACKUP_DIR = resolve(
  ROOT,
  "backup",
  "history_popup_ui_20260522_before_FRONTEND_HR_1_HISTORY_POPUP_UI_MOVE",
);
const CREATE_BACKUP = resolve(BACKUP_DIR, "CreateHistoryPopup.tsx");
const EDIT_BACKUP = resolve(BACKUP_DIR, "EditHistoryPopup.tsx");
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

// 1) New paths exist, old paths absent.
checks.new_create_exists = existsSync(NEW_CREATE);
checks.new_edit_exists = existsSync(NEW_EDIT);
checks.old_create_absent = !existsSync(OLD_CREATE);
checks.old_edit_absent = !existsSync(OLD_EDIT);

// 2) Old popup directory empty or removed.
function listFilesIfExists(dir) {
  if (!existsSync(dir)) return null;
  try {
    return readdirSync(dir, { withFileTypes: true })
      .filter((e) => e.isFile())
      .map((e) => e.name);
  } catch { return null; }
}
const remainingPopupFiles = listFilesIfExists(OLD_POPUP_DIR);
checks.popup_dir_empty_or_removed =
  remainingPopupFiles === null || remainingPopupFiles.length === 0;

// 3) Untouched siblings.
checks.HistoryWorkspace_present = existsSync(HISTORY_WORKSPACE);
checks.DetailHistoryView_present = existsSync(DETAIL_HISTORY);
checks.historyStore_present = existsSync(HISTORY_STORE);
checks.imageStore_present = existsSync(IMAGE_STORE);
checks.TestWorkspace_present = existsSync(TEST_WORKSPACE);
checks.test_core_dir_present = existsSync(TEST_CORE_DIR);

// 4) Popup file identity preserved.
const newCreateSrc = readSafe(NEW_CREATE);
const newEditSrc = readSafe(NEW_EDIT);
checks.new_create_default_export_preserved =
  newCreateSrc !== null && /export\s+default\s+function\s+CreateHistoryPopup\b/.test(newCreateSrc);
checks.new_edit_default_export_preserved =
  newEditSrc !== null && /export\s+default\s+function\s+EditHistoryPopup\b/.test(newEditSrc);
// Common popup type exports remain.
checks.new_create_HistoryPopupForm_export_preserved =
  newCreateSrc !== null && /\bHistoryPopupForm\b/.test(newCreateSrc);
checks.new_edit_HistoryPopupRow_export_preserved =
  newEditSrc !== null && /\bHistoryPopupRow\b/.test(newEditSrc);

// 5) Logic equivalence vs backup.
const createBackup = readSafe(CREATE_BACKUP);
const editBackup = readSafe(EDIT_BACKUP);
function compareBackup(name, cur, backup, backupPath) {
  if (backup === null) {
    skippedBackupChecks.push({ check: name, reason: `SKIP_WITH_REASON: backup not found: ${backupPath}` });
    return cur !== null;
  }
  return cur !== null && backup !== null &&
    normalizeImportInsensitive(cur) === normalizeImportInsensitive(backup);
}
checks.new_create_logic_unchanged_vs_backup = compareBackup(
  "new_create_logic_unchanged_vs_backup", newCreateSrc, createBackup, CREATE_BACKUP,
);
checks.new_edit_logic_unchanged_vs_backup = compareBackup(
  "new_edit_logic_unchanged_vs_backup", newEditSrc, editBackup, EDIT_BACKUP,
);

// 6) HistoryWorkspace imports the new path; logic equivalent except for
//    the two import path strings.
const workspaceSrc = readSafe(HISTORY_WORKSPACE);
const workspaceBackup = readSafe(HISTORY_WORKSPACE_BACKUP);
checks.workspace_imports_new_create =
  workspaceSrc !== null &&
  /from\s+["']\.\/ui\/CreateHistoryPopup["']/.test(workspaceSrc) &&
  !/from\s+["']\.\/popup\/CreateHistoryPopup["']/.test(stripComments(workspaceSrc));
checks.workspace_imports_new_edit =
  workspaceSrc !== null &&
  /from\s+["']\.\/ui\/EditHistoryPopup["']/.test(workspaceSrc) &&
  !/from\s+["']\.\/popup\/EditHistoryPopup["']/.test(stripComments(workspaceSrc));
checks.workspace_logic_unchanged_vs_backup = compareBackup(
  "workspace_logic_unchanged_vs_backup", workspaceSrc, workspaceBackup, HISTORY_WORKSPACE_BACKUP,
);

// 7) DetailHistoryView, historyStore, imageStore not modified vs pre-HR-1
//    state (no backup taken here; we just confirm their default exports
//    still exist).
const detailHistorySrc = readSafe(DETAIL_HISTORY);
const historyStoreSrc = readSafe(HISTORY_STORE);
const imageStoreSrc = readSafe(IMAGE_STORE);
checks.DetailHistoryView_default_export_preserved =
  detailHistorySrc !== null && /export\s+default\s+function\s+DetailHistoryView\b/.test(detailHistorySrc);
checks.historyStore_has_exports =
  historyStoreSrc !== null && /export\s+/.test(historyStoreSrc);
checks.imageStore_has_exports =
  imageStoreSrc !== null && /export\s+/.test(imageStoreSrc);

// 8) No residual `history/popup/` or `./popup/CreateHistoryPopup` /
//    `./popup/EditHistoryPopup` in src/ CODE (excluding comments).
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
  /from\s+["']\.\/popup\/(?:Create|Edit)HistoryPopup["']/,
  /from\s+["']\.\.\/popup\/(?:Create|Edit)HistoryPopup["']/,
  /from\s+["'][^"']*history\/popup\/(?:Create|Edit)HistoryPopup["']/,
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
checks.no_residual_history_popup_imports_in_code = residuals.length === 0;

const summary = {
  task: "FRONTEND-HR-1-HISTORY-POPUP-UI-MOVE",
  paths: {
    new_create: NEW_CREATE,
    new_edit: NEW_EDIT,
    old_create: OLD_CREATE,
    old_edit: OLD_EDIT,
    popup_dir: OLD_POPUP_DIR,
    remaining_popup_files: remainingPopupFiles,
    history_workspace: HISTORY_WORKSPACE,
    detail_history: DETAIL_HISTORY,
  },
  checks,
  skippedBackupChecks,
  residuals,
};
console.log(JSON.stringify(summary, null, 2));

const required = [
  "new_create_exists",
  "new_edit_exists",
  "old_create_absent",
  "old_edit_absent",
  "popup_dir_empty_or_removed",
  "HistoryWorkspace_present",
  "DetailHistoryView_present",
  "historyStore_present",
  "imageStore_present",
  "TestWorkspace_present",
  "test_core_dir_present",
  "new_create_default_export_preserved",
  "new_edit_default_export_preserved",
  "new_create_HistoryPopupForm_export_preserved",
  "new_edit_HistoryPopupRow_export_preserved",
  "new_create_logic_unchanged_vs_backup",
  "new_edit_logic_unchanged_vs_backup",
  "workspace_imports_new_create",
  "workspace_imports_new_edit",
  "workspace_logic_unchanged_vs_backup",
  "DetailHistoryView_default_export_preserved",
  "historyStore_has_exports",
  "imageStore_has_exports",
  "no_residual_history_popup_imports_in_code",
];
const allPass = required.every((k) => checks[k] === true);
const verdict = allPass
  ? (skippedBackupChecks.length > 0 ? "PASS_WITH_SKIPPED_BACKUP" : "PASS")
  : "FAIL";
console.log(`[HISTORY_POPUP_UI_MOVE_HR1] ${verdict}`);
process.exit(allPass ? 0 : 1);
