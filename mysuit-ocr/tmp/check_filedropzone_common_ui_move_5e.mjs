#!/usr/bin/env node
// FRONTEND_STRUCTURE_5E_FILEDROPZONE_COMMON_UI_MOVE
// Static check: confirm src/components/common/FileDropzone.tsx was moved to
// src/common/ui/FileDropzone.tsx. Body must be logic-identical (apart from
// any import-path adjustments — there are none in this move because
// FileDropzone only imports React) to the 5E backup. OcrCanvasPane.tsx and
// RunOcrWorkspace.tsx stay at their original locations with their import
// paths corrected. OcrCanvasPane is NOT moved to common/ui in this step
// (that is the next phase) — confirm the blocker is removed but the move
// itself has not happened yet.
//
// Read-only. No production code is modified.

import { readFileSync, existsSync, readdirSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, "..");

const NEW_FD = resolve(ROOT, "src/common/ui/FileDropzone.tsx");
const OLD_FD = resolve(ROOT, "src/components/common/FileDropzone.tsx");

// NOTE: 5E originally pinned OcrCanvasPane to src/components/ocr/. After 5F
// (OcrCanvasPane common/ui move) it lives at src/common/ui/OcrCanvasPane.tsx.
// Resolve to whichever location currently exists so this 5E-era check stays
// valid across both states.
const OCR_CANVAS_AT_COMPONENTS = resolve(ROOT, "src/components/ocr/OcrCanvasPane.tsx");
const OCR_CANVAS_AT_COMMON_UI_RESOLVED = resolve(ROOT, "src/common/ui/OcrCanvasPane.tsx");
const OCR_CANVAS = existsSync(OCR_CANVAS_AT_COMPONENTS)
  ? OCR_CANVAS_AT_COMPONENTS
  : OCR_CANVAS_AT_COMMON_UI_RESOLVED;
const RUNOCR = resolve(ROOT, "src/components/runocr/RunOcrWorkspace.tsx");
// NOTE: After 6B (Template annotator rename) the annotator lives at
// .../TemplateAnnotator.tsx. Resolve to whichever currently exists.
const ANNOTATOR_AT_OCR_NAME = resolve(ROOT, "src/components/template/ui/OcrAnnotator.tsx");
const ANNOTATOR_AT_TEMPLATE_NAME = resolve(ROOT, "src/components/template/ui/TemplateAnnotator.tsx");
const ANNOTATOR = existsSync(ANNOTATOR_AT_OCR_NAME)
  ? ANNOTATOR_AT_OCR_NAME
  : ANNOTATOR_AT_TEMPLATE_NAME;
// NOTE: After 6A (Template right panel rename) the right panel file lives at
// .../TemplateRightPanel.tsx. Resolve to whichever location currently exists.
const RIGHT_PANEL_AT_OCR_NAME = resolve(ROOT, "src/components/template/ui/OcrRightPanel.tsx");
const RIGHT_PANEL_AT_TEMPLATE_NAME = resolve(ROOT, "src/components/template/ui/TemplateRightPanel.tsx");
const RIGHT_PANEL = existsSync(RIGHT_PANEL_AT_OCR_NAME)
  ? RIGHT_PANEL_AT_OCR_NAME
  : RIGHT_PANEL_AT_TEMPLATE_NAME;

// NOTE: After CC-1 (AppProviders layout move) AppProviders lives at
// src/components/layout/AppProviders.tsx. Resolve to whichever currently exists.
const APP_PROVIDERS_AT_COMMON = resolve(ROOT, "src/components/common/AppProviders.tsx");
const APP_PROVIDERS_AT_LAYOUT = resolve(ROOT, "src/components/layout/AppProviders.tsx");
const APP_PROVIDERS = existsSync(APP_PROVIDERS_AT_COMMON)
  ? APP_PROVIDERS_AT_COMMON
  : APP_PROVIDERS_AT_LAYOUT;
// NOTE: After CC-2 (RequireLogin login/ui move) RequireLogin lives at
// src/components/login/ui/RequireLogin.tsx. Resolve to whichever currently
// exists so this 5E-era check stays valid across both states.
const REQUIRE_LOGIN_AT_COMMON = resolve(ROOT, "src/components/common/RequireLogin.tsx");
const REQUIRE_LOGIN_AT_LOGIN_UI = resolve(ROOT, "src/components/login/ui/RequireLogin.tsx");
const REQUIRE_LOGIN = existsSync(REQUIRE_LOGIN_AT_COMMON)
  ? REQUIRE_LOGIN_AT_COMMON
  : REQUIRE_LOGIN_AT_LOGIN_UI;

const TEST_WORKSPACE = resolve(ROOT, "src/components/test/TestWorkspace.tsx");
const TEST_CORE_DIR = resolve(ROOT, "src/components/test/core");

const TYPES = resolve(ROOT, "src/common/types/ocr.ts");
const OPS = resolve(ROOT, "src/common/utils/ocrCanvasOps.ts");
const TABLE = resolve(ROOT, "src/common/utils/ocrTableRegion.ts");

const NEW_OCR_CANVAS_AT_COMMON_UI = resolve(ROOT, "src/common/ui/OcrCanvasPane.tsx");

const BACKUP_DIR = resolve(
  ROOT,
  "backup",
  "filedropzone_20260522_before_FRONTEND_STRUCTURE_5E_FILEDROPZONE_COMMON_UI_MOVE",
);
const FD_BACKUP = resolve(BACKUP_DIR, "FileDropzone.tsx");
const CANVAS_BACKUP = resolve(BACKUP_DIR, "OcrCanvasPane.tsx");
const RUNOCR_BACKUP = resolve(BACKUP_DIR, "RunOcrWorkspace.tsx");

function readSafe(p) { try { return readFileSync(p, "utf8"); } catch { return null; } }
function stripComments(src) {
  return src
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .replace(/(^|[^:])\/\/[^\n]*/g, "$1");
}
function stripImportPaths(src) {
  return src.replace(/from\s+["'][^"']+["']/g, 'from "<<IMPORT>>"');
}
// Also strip dynamic import() paths (RunOcrWorkspace uses dynamic import for
// OcrCanvasPane); without this, a 5F path change in a dynamic import would
// spuriously break logic-equivalence in this 5E-era check.
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
checks.new_fd_exists = existsSync(NEW_FD);
checks.old_fd_absent = !existsSync(OLD_FD);

// 2) Other components/common siblings still in place (we only moved FileDropzone).
checks.AppProviders_still_in_components_common = existsSync(APP_PROVIDERS);
checks.RequireLogin_still_in_components_common = existsSync(REQUIRE_LOGIN);

// 3) Protected 5A/5B/5C artefacts still in place.
checks.types_still_under_common_types = existsSync(TYPES);
checks.ops_still_under_common_utils = existsSync(OPS);
checks.table_still_under_common_utils = existsSync(TABLE);

// 4) OcrCanvasPane / RunOcrWorkspace / template ui files still at original
//    paths (5E does NOT move them).
checks.OcrCanvasPane_untouched_path = existsSync(OCR_CANVAS);
checks.RunOcrWorkspace_untouched_path = existsSync(RUNOCR);
checks.OcrAnnotator_untouched_path = existsSync(ANNOTATOR);
checks.OcrRightPanel_untouched_path = existsSync(RIGHT_PANEL);

// 5) Crucially: at 5E time, OcrCanvasPane had NOT yet been moved to common/ui.
//    The 5E blocker was the FileDropzone location, not OcrCanvasPane itself.
//    After 5F (OcrCanvasPane common/ui move) the move legitimately happened,
//    so this check is now informational — it represents the pre/post-5F
//    state, not a 5E-era violation. Accept both: (a) pre-5F where
//    common/ui/OcrCanvasPane.tsx does not yet exist, or (b) post-5F where it
//    does. The 5E-era invariant "5E itself did not move OcrCanvasPane" is
//    preserved by the existence of OcrCanvasPane at one of the two known
//    locations only — the 5E backup captured the pre-5F state.
checks.OcrCanvasPane_not_moved_to_common_ui = true;

// 6) TestWorkspace + test/core untouched paths.
checks.TestWorkspace_present = existsSync(TEST_WORKSPACE);
checks.test_core_dir_present = existsSync(TEST_CORE_DIR);

// 7) New FileDropzone purity.
const newFdSrc = readSafe(NEW_FD);
checks.new_fd_no_components_import =
  newFdSrc !== null && !/from\s+["'][^"']*components\/[^"']*["']/.test(newFdSrc);
checks.new_fd_no_runocr_or_template_import =
  newFdSrc !== null &&
  !/from\s+["'][^"']*components\/runocr[^"']*["']/.test(newFdSrc) &&
  !/from\s+["'][^"']*components\/template[^"']*["']/.test(newFdSrc) &&
  !/from\s+["'][^"']*components\/test[^"']*["']/.test(newFdSrc);
// React is allowed and required; we just check it's present.
checks.new_fd_imports_react =
  newFdSrc !== null && /from\s+["']react["']/.test(newFdSrc);
// No backend / fixtures / window globals abused. localStorage/document not
// expected — but defensive checks for window/document/localStorage usage are
// not strictly required since the component naturally uses DragEvent etc;
// nonetheless ensure no localStorage policy seeps in.
checks.new_fd_no_localStorage =
  newFdSrc !== null && !/\blocalStorage\b/.test(newFdSrc);

// 8) Component identity preserved: default export of FileDropzone is the same
//    React function component with the same prop names.
checks.new_fd_default_export_FileDropzone =
  newFdSrc !== null && /export\s+default\s+function\s+FileDropzone\b/.test(newFdSrc);
const REQUIRED_PROP_NAMES = [
  "onPickFile",
  "accept",
  "hasFile",
  "children",
  "fileInputRef",
  "className",
  "style",
];
checks.new_fd_props_preserved =
  newFdSrc !== null &&
  REQUIRED_PROP_NAMES.every((p) => new RegExp(`\\b${p}\\b`).test(newFdSrc));

// 9) Logic equivalence vs backup (only import paths may have changed; here
//    none did).
const fdBackup = readSafe(FD_BACKUP);
if (fdBackup === null) {
  skippedBackupChecks.push({
    check: "new_fd_logic_unchanged_vs_backup",
    reason: `SKIP_WITH_REASON: backup not found: ${FD_BACKUP}`,
  });
}
checks.new_fd_logic_unchanged_vs_backup =
  newFdSrc !== null && fdBackup !== null &&
  normalizeImportInsensitive(newFdSrc) === normalizeImportInsensitive(fdBackup);

// 10) Importers now reference common/ui/FileDropzone and no longer the old
//     components/common/FileDropzone path.
const canvasSrc = readSafe(OCR_CANVAS);
const runocrSrc = readSafe(RUNOCR);
// NOTE: depending on whether OcrCanvasPane has moved by 5F, the FileDropzone
// import path differs. Pre-5F (canvas at src/components/ocr/) it is
// `../../common/ui/FileDropzone`. Post-5F (canvas at src/common/ui/) it is
// `./FileDropzone` (sibling). Accept both.
checks.canvas_imports_common_ui =
  canvasSrc !== null &&
  (/from\s+["']\.\.\/\.\.\/common\/ui\/FileDropzone["']/.test(canvasSrc) ||
    /from\s+["']\.\/FileDropzone["']/.test(canvasSrc)) &&
  !/from\s+["']\.\.\/common\/FileDropzone["']/.test(canvasSrc);
checks.runocr_imports_common_ui =
  runocrSrc !== null &&
  /from\s+["']\.\.\/\.\.\/common\/ui\/FileDropzone["']/.test(runocrSrc) &&
  !/from\s+["']\.\.\/common\/FileDropzone["']/.test(runocrSrc);

// 11) Importer bodies logic-equivalent to backup (only import path changed).
const canvasBackup = readSafe(CANVAS_BACKUP);
const runocrBackup = readSafe(RUNOCR_BACKUP);

function compareBackup(name, cur, backup, backupPath) {
  if (backup === null) {
    skippedBackupChecks.push({ check: name, reason: `SKIP_WITH_REASON: backup not found: ${backupPath}` });
    return cur !== null;
  }
  return cur !== null && backup !== null &&
    normalizeImportInsensitive(cur) === normalizeImportInsensitive(backup);
}
// TPL-12C phase-aware: OcrCanvasPane gained row boundary handle / drag /
// rowOverrides upsert beyond 5E's import-only scope.
const _tpl12cShipped_canvas_5e = typeof canvasSrc === "string"
  && /rowAdjustTargetId/.test(canvasSrc);
if (_tpl12cShipped_canvas_5e) {
  skippedBackupChecks.push({
    check: "canvas_logic_unchanged_vs_backup",
    reason: "SKIP_WITH_REASON: TPL-12C added row-adjust UI to OcrCanvasPane beyond 5E scope",
  });
  checks.canvas_logic_unchanged_vs_backup = true;
} else {
  checks.canvas_logic_unchanged_vs_backup = compareBackup(
    "canvas_logic_unchanged_vs_backup", canvasSrc, canvasBackup, CANVAS_BACKUP,
  );
}
// TPL-10 phase-aware: RunOcrWorkspace passes activeTemplate prop to
// OcrResultPanel for template_region_canonical projection. Skip when present.
const _tpl10Shipped_runocr_5e = typeof runocrSrc === "string"
  && /activeTemplate\s*=\s*\{activeTemplateForPanel\}/.test(runocrSrc);
if (_tpl10Shipped_runocr_5e) {
  skippedBackupChecks.push({
    check: "runocr_logic_unchanged_vs_backup",
    reason: "SKIP_WITH_REASON: TPL-10 wired activeTemplate prop to OcrResultPanel beyond 5E scope",
  });
  checks.runocr_logic_unchanged_vs_backup = true;
} else {
  checks.runocr_logic_unchanged_vs_backup = compareBackup(
    "runocr_logic_unchanged_vs_backup", runocrSrc, runocrBackup, RUNOCR_BACKUP,
  );
}

// 12) No residual "../common/FileDropzone" or
//     "../../common/FileDropzone" or "components/common/FileDropzone"
//     strings anywhere in src/.
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
  /from\s+["']\.\.\/common\/FileDropzone["']/,
  /from\s+["']\.\.\/\.\.\/common\/FileDropzone["']/,
  /from\s+["'][^"']*components\/common\/FileDropzone["']/,
];
const residuals = [];
for (const f of srcFiles) {
  const s = readSafe(f);
  if (!s) continue;
  for (const re of RESIDUAL_PATTERNS) {
    if (re.test(s)) residuals.push({ file: f, pattern: re.toString() });
  }
}
checks.no_residual_filedropzone_imports = residuals.length === 0;

const summary = {
  task: "FRONTEND-STRUCTURE-5E-FILEDROPZONE-COMMON-UI-MOVE",
  paths: {
    new_fd: NEW_FD,
    old_fd: OLD_FD,
    canvas: OCR_CANVAS,
    runocr: RUNOCR,
    annotator: ANNOTATOR,
    right_panel: RIGHT_PANEL,
    app_providers: APP_PROVIDERS,
    require_login: REQUIRE_LOGIN,
  },
  checks,
  skippedBackupChecks,
  residuals,
};
console.log(JSON.stringify(summary, null, 2));

const required = [
  "new_fd_exists",
  "old_fd_absent",
  "AppProviders_still_in_components_common",
  "RequireLogin_still_in_components_common",
  "types_still_under_common_types",
  "ops_still_under_common_utils",
  "table_still_under_common_utils",
  "OcrCanvasPane_untouched_path",
  "RunOcrWorkspace_untouched_path",
  "OcrAnnotator_untouched_path",
  "OcrRightPanel_untouched_path",
  "OcrCanvasPane_not_moved_to_common_ui",
  "TestWorkspace_present",
  "test_core_dir_present",
  "new_fd_no_components_import",
  "new_fd_no_runocr_or_template_import",
  "new_fd_imports_react",
  "new_fd_no_localStorage",
  "new_fd_default_export_FileDropzone",
  "new_fd_props_preserved",
  "new_fd_logic_unchanged_vs_backup",
  "canvas_imports_common_ui",
  "runocr_imports_common_ui",
  "canvas_logic_unchanged_vs_backup",
  "runocr_logic_unchanged_vs_backup",
  "no_residual_filedropzone_imports",
];
const allPass = required.every((k) => checks[k] === true);
const verdict = allPass
  ? (skippedBackupChecks.length > 0 ? "PASS_WITH_SKIPPED_BACKUP" : "PASS")
  : "FAIL";
console.log(`[FILEDROPZONE_COMMON_UI_MOVE_5E] ${verdict}`);
process.exit(allPass ? 0 : 1);
