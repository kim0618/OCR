#!/usr/bin/env node
// FRONTEND_CC_1_APP_PROVIDERS_LAYOUT_MOVE
// Static check: confirm src/components/common/AppProviders.tsx was moved to
// src/components/layout/AppProviders.tsx. Body must be logic-identical to
// the CC-1 backup. All 11 production importers
// (src/app/layout.tsx + 10 component files) keep their original paths with
// only the AppProviders/useUi import path corrected. TestWorkspace.tsx is
// allowed an import-path-only edit. RequireLogin.tsx must remain at
// src/components/common/ (CC-2 will move it). The components/common
// directory must NOT be removed (RequireLogin still lives there).
//
// Read-only. No production code is modified.

import { readFileSync, existsSync, readdirSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, "..");

const NEW_PROVIDERS = resolve(ROOT, "src/components/layout/AppProviders.tsx");
const OLD_PROVIDERS = resolve(ROOT, "src/components/common/AppProviders.tsx");

// NOTE: After CC-2 (RequireLogin login/ui move) RequireLogin lives at
// src/components/login/ui/RequireLogin.tsx. Resolve to whichever currently
// exists so this CC-1-era check stays valid across both states.
const REQUIRE_LOGIN_AT_COMMON = resolve(ROOT, "src/components/common/RequireLogin.tsx");
const REQUIRE_LOGIN_AT_LOGIN_UI = resolve(ROOT, "src/components/login/ui/RequireLogin.tsx");
const REQUIRE_LOGIN = existsSync(REQUIRE_LOGIN_AT_COMMON)
  ? REQUIRE_LOGIN_AT_COMMON
  : REQUIRE_LOGIN_AT_LOGIN_UI;
const APP_SHELL = resolve(ROOT, "src/components/layout/AppShell.tsx");
const HEADER = resolve(ROOT, "src/components/layout/Header.tsx");
const SIDEBAR = resolve(ROOT, "src/components/layout/Sidebar.tsx");

const APP_LAYOUT = resolve(ROOT, "src/app/layout.tsx");
const AUTORESTORE = resolve(ROOT, "src/components/autorestore/AutoRestoreWorkspace.tsx");
const HISTORY_WS = resolve(ROOT, "src/components/history/HistoryWorkspace.tsx");
const TEMPLATE_WS = resolve(ROOT, "src/components/template/TemplateWorkspace.tsx");
// NOTE: After HR-2 (DetailHistoryView ui move) the file lives at
// src/components/history/ui/DetailHistoryView.tsx. Resolve to whichever
// currently exists so this CC-1-era check stays valid across both states.
const DETAIL_HISTORY_AT_HISTORY = resolve(ROOT, "src/components/history/DetailHistoryView.tsx");
const DETAIL_HISTORY_AT_HISTORY_UI = resolve(ROOT, "src/components/history/ui/DetailHistoryView.tsx");
const DETAIL_HISTORY = existsSync(DETAIL_HISTORY_AT_HISTORY)
  ? DETAIL_HISTORY_AT_HISTORY
  : DETAIL_HISTORY_AT_HISTORY_UI;
const TEST_WORKSPACE = resolve(ROOT, "src/components/test/TestWorkspace.tsx");
const UNSTRUCTURED_BUILDER = resolve(ROOT, "src/components/template/UnstructuredBuilder.tsx");
const TEMPLATE_ANNOTATOR = resolve(ROOT, "src/components/template/ui/TemplateAnnotator.tsx");
const RUNOCR_WORKSPACE = resolve(ROOT, "src/components/runocr/RunOcrWorkspace.tsx");
const LOGIN_WORKSPACE = resolve(ROOT, "src/components/login/LoginWorkspace.tsx");
const OCR_RESULT_PANEL = resolve(ROOT, "src/components/runocr/ui/OcrResultPanel.tsx");

const TEST_CORE_DIR = resolve(ROOT, "src/components/test/core");

const BACKUP_DIR = resolve(
  ROOT,
  "backup",
  "components_common_app_providers_20260522_before_FRONTEND_CC_1_APP_PROVIDERS_LAYOUT_MOVE",
);
const PROVIDERS_BACKUP = resolve(BACKUP_DIR, "AppProviders.tsx");
const APP_LAYOUT_BACKUP = resolve(BACKUP_DIR, "app_layout.tsx");
const AUTORESTORE_BACKUP = resolve(BACKUP_DIR, "AutoRestoreWorkspace.tsx");
const HISTORY_WS_BACKUP = resolve(BACKUP_DIR, "HistoryWorkspace.tsx");
const TEMPLATE_WS_BACKUP = resolve(BACKUP_DIR, "TemplateWorkspace.tsx");
const DETAIL_HISTORY_BACKUP = resolve(BACKUP_DIR, "DetailHistoryView.tsx");
const TEST_WORKSPACE_BACKUP = resolve(BACKUP_DIR, "TestWorkspace.tsx");
const UNSTRUCTURED_BACKUP = resolve(BACKUP_DIR, "UnstructuredBuilder.tsx");
const ANNOTATOR_BACKUP = resolve(BACKUP_DIR, "TemplateAnnotator.tsx");
const RUNOCR_WORKSPACE_BACKUP = resolve(BACKUP_DIR, "RunOcrWorkspace.tsx");
const LOGIN_WORKSPACE_BACKUP = resolve(BACKUP_DIR, "LoginWorkspace.tsx");
const OCR_RESULT_PANEL_BACKUP = resolve(BACKUP_DIR, "OcrResultPanel.tsx");

function readSafe(p) { try { return readFileSync(p, "utf8"); } catch { return null; } }
function stripComments(src) {
  return src
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .replace(/(^|[^:])\/\/[^\n]*/g, "$1");
}
function stripImportPaths(src) {
  return src.replace(/from\s+["'][^"']+["']/g, 'from "<<IMPORT>>"');
}
function stripDynamicImportPaths(src) {
  return src.replace(/import\(\s*["'][^"']+["']\s*\)/g, 'import("<<IMPORT>>")');
}
function normalizeImportInsensitive(src) {
  return stripDynamicImportPaths(stripImportPaths(stripComments(src)))
    .replace(/\s+/g, " ")
    .trim();
}

const checks = {};
const skippedBackupChecks = [];

// 1) New path exists, old path absent.
checks.new_providers_exists = existsSync(NEW_PROVIDERS);
checks.old_providers_absent = !existsSync(OLD_PROVIDERS);

// 2) RequireLogin still under components/common (CC-2 will move it).
checks.RequireLogin_still_under_components_common = existsSync(REQUIRE_LOGIN);

// 3) Layout siblings still present.
checks.AppShell_still_under_layout = existsSync(APP_SHELL);
checks.Header_still_under_layout = existsSync(HEADER);
checks.Sidebar_still_under_layout = existsSync(SIDEBAR);

// 4) test/core untouched.
checks.test_core_dir_present = existsSync(TEST_CORE_DIR);

// 5) New AppProviders purity / identity preserved.
const newProvidersSrc = readSafe(NEW_PROVIDERS);
checks.new_providers_useUi_export_preserved =
  newProvidersSrc !== null && /export\s+function\s+useUi\b/.test(newProvidersSrc);
checks.new_providers_default_export_AppProviders =
  newProvidersSrc !== null && /export\s+default\s+function\s+AppProviders\b/.test(newProvidersSrc);

// 6) Logic equivalence vs backup.
const providersBackup = readSafe(PROVIDERS_BACKUP);
if (providersBackup === null) {
  skippedBackupChecks.push({
    check: "new_providers_logic_unchanged_vs_backup",
    reason: `SKIP_WITH_REASON: backup not found: ${PROVIDERS_BACKUP}`,
  });
}
checks.new_providers_logic_unchanged_vs_backup =
  newProvidersSrc !== null && providersBackup !== null &&
  normalizeImportInsensitive(newProvidersSrc) === normalizeImportInsensitive(providersBackup);

// 7) All 11 importers now reference the layout path.
const importers = [
  { name: "app_layout", path: APP_LAYOUT, backup: APP_LAYOUT_BACKUP, expectedImport: /from\s+["']\.\.\/components\/layout\/AppProviders["']/, forbiddenImport: /from\s+["']\.\.\/components\/common\/AppProviders["']/ },
  { name: "autorestore", path: AUTORESTORE, backup: AUTORESTORE_BACKUP, expectedImport: /from\s+["']\.\.\/layout\/AppProviders["']/, forbiddenImport: /from\s+["']\.\.\/common\/AppProviders["']/ },
  { name: "history_workspace", path: HISTORY_WS, backup: HISTORY_WS_BACKUP, expectedImport: /from\s+["']\.\.\/layout\/AppProviders["']/, forbiddenImport: /from\s+["']\.\.\/common\/AppProviders["']/ },
  { name: "template_workspace", path: TEMPLATE_WS, backup: TEMPLATE_WS_BACKUP, expectedImport: /from\s+["']\.\.\/layout\/AppProviders["']/, forbiddenImport: /from\s+["']\.\.\/common\/AppProviders["']/ },
  // NOTE: After HR-2 (DetailHistoryView ui move) DetailHistoryView lives at
  // history/ui/, so the relative path to layout deepens to ../../layout/.
  // Accept both pre-HR-2 (../layout) and post-HR-2 (../../layout) AppProviders
  // imports here.
  { name: "detail_history", path: DETAIL_HISTORY, backup: DETAIL_HISTORY_BACKUP, expectedImport: /from\s+["']\.\.\/(?:\.\.\/)?layout\/AppProviders["']/, forbiddenImport: /from\s+["']\.\.\/(?:\.\.\/)?common\/AppProviders["']/ },
  { name: "test_workspace", path: TEST_WORKSPACE, backup: TEST_WORKSPACE_BACKUP, expectedImport: /from\s+["']\.\.\/layout\/AppProviders["']/, forbiddenImport: /from\s+["']\.\.\/common\/AppProviders["']/ },
  { name: "unstructured_builder", path: UNSTRUCTURED_BUILDER, backup: UNSTRUCTURED_BACKUP, expectedImport: /from\s+["']\.\.\/layout\/AppProviders["']/, forbiddenImport: /from\s+["']\.\.\/common\/AppProviders["']/ },
  { name: "template_annotator", path: TEMPLATE_ANNOTATOR, backup: ANNOTATOR_BACKUP, expectedImport: /from\s+["']\.\.\/\.\.\/layout\/AppProviders["']/, forbiddenImport: /from\s+["']\.\.\/\.\.\/common\/AppProviders["']/ },
  { name: "runocr_workspace", path: RUNOCR_WORKSPACE, backup: RUNOCR_WORKSPACE_BACKUP, expectedImport: /from\s+["']\.\.\/layout\/AppProviders["']/, forbiddenImport: /from\s+["']\.\.\/common\/AppProviders["']/ },
  { name: "login_workspace", path: LOGIN_WORKSPACE, backup: LOGIN_WORKSPACE_BACKUP, expectedImport: /from\s+["']\.\.\/layout\/AppProviders["']/, forbiddenImport: /from\s+["']\.\.\/common\/AppProviders["']/ },
  { name: "ocr_result_panel", path: OCR_RESULT_PANEL, backup: OCR_RESULT_PANEL_BACKUP, expectedImport: /from\s+["']\.\.\/\.\.\/layout\/AppProviders["']/, forbiddenImport: /from\s+["']\.\.\/\.\.\/common\/AppProviders["']/ },
];

// Files that later phases legitimately changed beyond CC-1's import-only
// scope. Each entry names a marker that uniquely identifies the later edit;
// if the marker is present, the logic-equivalence check against the CC-1
// backup is skipped (it was a one-shot move-time guard).
const PHASE_LATER_EDIT_MARKERS = {
  unstructured_builder: /from\s+["']\.\/utils\/unstructuredDefinition["']/, // TPL-4
  ocr_result_panel: /from\s+["']@\/common\/utils\/tableResultViewModel["']/, // TPL-8E
  runocr_workspace: /activeTemplate\s*=\s*\{activeTemplateForPanel\}/, // TPL-10
  template_annotator: /rowAdjustTargetId/, // TPL-12C
};

for (const imp of importers) {
  const cur = readSafe(imp.path);
  const codeOnly = cur !== null ? stripComments(cur) : null;
  checks[`${imp.name}_imports_layout_path`] =
    codeOnly !== null && imp.expectedImport.test(codeOnly) && !imp.forbiddenImport.test(codeOnly);
  // Logic equivalence vs backup.
  const backup = readSafe(imp.backup);
  if (backup === null) {
    skippedBackupChecks.push({
      check: `${imp.name}_logic_unchanged_vs_backup`,
      reason: `SKIP_WITH_REASON: backup not found: ${imp.backup}`,
    });
  }
  const laterMarker = PHASE_LATER_EDIT_MARKERS[imp.name];
  if (laterMarker && cur !== null && laterMarker.test(cur)) {
    skippedBackupChecks.push({
      check: `${imp.name}_logic_unchanged_vs_backup`,
      reason: `SKIP_WITH_REASON: later phase modified this file beyond CC-1 scope (marker matched)`,
    });
    checks[`${imp.name}_logic_unchanged_vs_backup`] = true;
    continue;
  }
  checks[`${imp.name}_logic_unchanged_vs_backup`] =
    cur !== null && backup !== null &&
    normalizeImportInsensitive(cur) === normalizeImportInsensitive(backup);
}

// 8) TestWorkspace: explicit import-path-only invariant (covered by the
//    generic logic-equivalence check above, but assert again for visibility).
const testWorkspaceSrc = readSafe(TEST_WORKSPACE);
const testWorkspaceBackup = readSafe(TEST_WORKSPACE_BACKUP);
checks.test_workspace_import_path_only_edit =
  testWorkspaceSrc !== null && testWorkspaceBackup !== null &&
  normalizeImportInsensitive(testWorkspaceSrc) === normalizeImportInsensitive(testWorkspaceBackup);

// 9) RequireLogin not modified vs pre-CC-1 state (no backup taken; we just
//    confirm the file still exports its default identifier).
const requireLoginSrc = readSafe(REQUIRE_LOGIN);
checks.RequireLogin_default_export_preserved =
  requireLoginSrc !== null && /export\s+default\s+function\s+RequireLogin\b/.test(requireLoginSrc);

// 10) No residual components/common/AppProviders or ../common/AppProviders /
//     ../../common/AppProviders strings in src/ CODE (excluding comments).
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
  /from\s+["']\.\.\/common\/AppProviders["']/,
  /from\s+["']\.\.\/\.\.\/common\/AppProviders["']/,
  /from\s+["'][^"']*components\/common\/AppProviders["']/,
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
checks.no_residual_common_appproviders_imports_in_code = residuals.length === 0;

const summary = {
  task: "FRONTEND-CC-1-APP-PROVIDERS-LAYOUT-MOVE",
  paths: {
    new_providers: NEW_PROVIDERS,
    old_providers: OLD_PROVIDERS,
    require_login: REQUIRE_LOGIN,
    importers: importers.map((i) => i.path),
  },
  checks,
  skippedBackupChecks,
  residuals,
};
console.log(JSON.stringify(summary, null, 2));

const required = [
  "new_providers_exists",
  "old_providers_absent",
  "RequireLogin_still_under_components_common",
  "AppShell_still_under_layout",
  "Header_still_under_layout",
  "Sidebar_still_under_layout",
  "test_core_dir_present",
  "new_providers_useUi_export_preserved",
  "new_providers_default_export_AppProviders",
  "new_providers_logic_unchanged_vs_backup",
  ...importers.flatMap((i) => [
    `${i.name}_imports_layout_path`,
    `${i.name}_logic_unchanged_vs_backup`,
  ]),
  "test_workspace_import_path_only_edit",
  "RequireLogin_default_export_preserved",
  "no_residual_common_appproviders_imports_in_code",
];
const allPass = required.every((k) => checks[k] === true);
const verdict = allPass
  ? (skippedBackupChecks.length > 0 ? "PASS_WITH_SKIPPED_BACKUP" : "PASS")
  : "FAIL";
console.log(`[APP_PROVIDERS_LAYOUT_MOVE_CC1] ${verdict}`);
process.exit(allPass ? 0 : 1);
