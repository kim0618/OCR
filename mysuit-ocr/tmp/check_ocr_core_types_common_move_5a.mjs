#!/usr/bin/env node
// FRONTEND_STRUCTURE_5A_OCR_CORE_TYPES_COMMON_MOVE
// Static check: confirm src/components/ocr/core/types.ts was moved to
// src/common/types/ocr.ts with import paths corrected, while ops.ts, table.ts,
// export.ts and OcrCanvasPane.tsx remain at their original locations.
// Logic of the moved type file must be byte-identical to the backup (apart
// from being a move).
//
// Read-only. No production code is modified.

import { readFileSync, existsSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, "..");

const NEW_TYPES = resolve(ROOT, "src/common/types/ocr.ts");
const OLD_TYPES = resolve(ROOT, "src/components/ocr/core/types.ts");

// NOTE: 5A originally pinned ops.ts to src/components/ocr/core/ops.ts. After
// 5B (OCR core ops common move) ops.ts is at src/common/utils/ocrCanvasOps.ts.
// We resolve OPS to whichever location currently exists so this 5A-era check
// stays valid across both states.
const OPS_AT_CORE = resolve(ROOT, "src/components/ocr/core/ops.ts");
const OPS_AT_COMMON_UTILS = resolve(ROOT, "src/common/utils/ocrCanvasOps.ts");
const OPS = existsSync(OPS_AT_CORE) ? OPS_AT_CORE : OPS_AT_COMMON_UTILS;
// NOTE: 5A originally pinned table.ts to src/components/ocr/core/table.ts.
// After 5C (OCR core table common move) table.ts is at
// src/common/utils/ocrTableRegion.ts. We resolve TABLE to whichever location
// currently exists so this 5A-era check stays valid across both states.
const TABLE_AT_CORE = resolve(ROOT, "src/components/ocr/core/table.ts");
const TABLE_AT_COMMON_UTILS = resolve(ROOT, "src/common/utils/ocrTableRegion.ts");
const TABLE = existsSync(TABLE_AT_CORE) ? TABLE_AT_CORE : TABLE_AT_COMMON_UTILS;
// NOTE: 5A originally pinned export.ts to src/components/ocr/core/export.ts.
// After 5D (Template export payload move) the file is at
// src/components/template/utils/buildTemplateExportPayload.ts. We resolve
// EXPORT to whichever location currently exists so this 5A-era check stays
// valid across both states.
const EXPORT_AT_CORE = resolve(ROOT, "src/components/ocr/core/export.ts");
const EXPORT_AT_TEMPLATE_UTILS = resolve(
  ROOT, "src/components/template/utils/buildTemplateExportPayload.ts",
);
const EXPORT = existsSync(EXPORT_AT_CORE) ? EXPORT_AT_CORE : EXPORT_AT_TEMPLATE_UTILS;
// NOTE: 5A originally pinned OcrCanvasPane to src/components/ocr/. After 5F
// (OcrCanvasPane common/ui move) it lives at src/common/ui/OcrCanvasPane.tsx.
// Resolve to whichever location currently exists so this 5A-era check stays
// valid across both states.
const OCR_CANVAS_AT_COMPONENTS = resolve(ROOT, "src/components/ocr/OcrCanvasPane.tsx");
const OCR_CANVAS_AT_COMMON_UI = resolve(ROOT, "src/common/ui/OcrCanvasPane.tsx");
const OCR_CANVAS = existsSync(OCR_CANVAS_AT_COMPONENTS)
  ? OCR_CANVAS_AT_COMPONENTS
  : OCR_CANVAS_AT_COMMON_UI;
// NOTE: After 6B (Template annotator rename) the annotator lives at
// .../TemplateAnnotator.tsx. Resolve to whichever currently exists.
const ANNOTATOR_AT_OCR_NAME = resolve(ROOT, "src/components/template/ui/OcrAnnotator.tsx");
const ANNOTATOR_AT_TEMPLATE_NAME = resolve(ROOT, "src/components/template/ui/TemplateAnnotator.tsx");
const ANNOTATOR = existsSync(ANNOTATOR_AT_OCR_NAME)
  ? ANNOTATOR_AT_OCR_NAME
  : ANNOTATOR_AT_TEMPLATE_NAME;
// NOTE: 5A originally pinned OcrRightPanel at .../OcrRightPanel.tsx. After 6A
// (Template right panel rename) the file lives at .../TemplateRightPanel.tsx.
// Resolve to whichever currently exists.
const RIGHT_PANEL_AT_OCR_NAME = resolve(ROOT, "src/components/template/ui/OcrRightPanel.tsx");
const RIGHT_PANEL_AT_TEMPLATE_NAME = resolve(ROOT, "src/components/template/ui/TemplateRightPanel.tsx");
const RIGHT_PANEL = existsSync(RIGHT_PANEL_AT_OCR_NAME)
  ? RIGHT_PANEL_AT_OCR_NAME
  : RIGHT_PANEL_AT_TEMPLATE_NAME;
const RUNOCR = resolve(ROOT, "src/components/runocr/RunOcrWorkspace.tsx");
const RUNOCR_FORMDATA = resolve(ROOT, "src/components/runocr/utils/buildOcrFormData.ts");

const TEST_WORKSPACE = resolve(ROOT, "src/components/test/TestWorkspace.tsx");
const TEST_CORE_TYPES = resolve(ROOT, "src/components/test/core/types.ts");

const BACKUP_DIR = resolve(
  ROOT,
  "backup",
  "ocr_core_types_20260522_before_FRONTEND_STRUCTURE_5A_OCR_CORE_TYPES_COMMON_MOVE",
);
const TYPES_BACKUP = resolve(BACKUP_DIR, "types.ts");

function readSafe(p) { try { return readFileSync(p, "utf8"); } catch { return null; } }
function stripComments(src) {
  return src
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .replace(/(^|[^:])\/\/[^\n]*/g, "$1");
}
function normalizeForLogic(src) {
  return stripComments(src).replace(/\s+/g, " ").trim();
}

const checks = {};

// 1) New path exists, old path absent
checks.new_types_exists = existsSync(NEW_TYPES);
checks.old_types_absent = !existsSync(OLD_TYPES);

// 2) Protected core siblings still at original ocr/core/
checks.ops_untouched_path = existsSync(OPS);
checks.table_untouched_path = existsSync(TABLE);
checks.export_untouched_path = existsSync(EXPORT);

// 3) Protected OcrCanvasPane and template/ui still at original paths
checks.OcrCanvasPane_untouched_path = existsSync(OCR_CANVAS);
checks.OcrAnnotator_untouched_path = existsSync(ANNOTATOR);
checks.OcrRightPanel_untouched_path = existsSync(RIGHT_PANEL);

// 4) RunOCR files still present at original paths
checks.RunOcrWorkspace_present = existsSync(RUNOCR);
checks.buildOcrFormData_present = existsSync(RUNOCR_FORMDATA);

// 5) TestWorkspace untouched and test/core/types still has its own copy
checks.TestWorkspace_present = existsSync(TEST_WORKSPACE);
checks.test_core_types_present = existsSync(TEST_CORE_TYPES);

// 6) New common/types/ocr.ts is pure type module: no React / browser /
//    components/* / localStorage / window / document imports.
const newTypesSrc = readSafe(NEW_TYPES);
checks.new_types_no_react_import =
  newTypesSrc !== null && !/from\s+["']react["']/.test(newTypesSrc);
checks.new_types_no_components_import =
  newTypesSrc !== null && !/from\s+["'][^"']*components\/[^"']*["']/.test(newTypesSrc);
checks.new_types_no_browser_api =
  newTypesSrc !== null &&
  !/\bwindow\b/.test(newTypesSrc) &&
  !/\bdocument\b/.test(newTypesSrc) &&
  !/\blocalStorage\b/.test(newTypesSrc);
// Only type-level exports — no top-level executable code other than `export type` /
// `export interface` blocks. Defensive: forbid `import` lines at all.
checks.new_types_no_imports =
  newTypesSrc !== null && !/^\s*import\s+/m.test(newTypesSrc);

// 7) Byte/logic equivalence with backup (the move did not alter the file body)
const backupSrc = readSafe(TYPES_BACKUP);
// TPL-9B phase-aware: TableColumnDef now carries optional columnKey/labelKo
// /labelEn fields. Skip the byte-equivalence guard when that marker is
// present.
const _tpl9bShipped_5a = typeof newTypesSrc === "string"
  && /columnKey\?\s*:\s*string/.test(newTypesSrc);
if (_tpl9bShipped_5a) {
  checks.new_types_logic_unchanged_vs_backup = true;
  checks._tpl9b_types_backup_check_skipped = true;
} else {
  checks.new_types_logic_unchanged_vs_backup =
    newTypesSrc !== null &&
    backupSrc !== null &&
    normalizeForLogic(newTypesSrc) === normalizeForLogic(backupSrc);
}

// 8) Importers updated to common/types/ocr. Confirm the exact path each file
//    must use (depends on its depth).
const opsSrc = readSafe(OPS);
const tableSrc = readSafe(TABLE);
const exportSrc = readSafe(EXPORT);
const canvasSrc = readSafe(OCR_CANVAS);
const annotatorSrc = readSafe(ANNOTATOR);
const rightPanelSrc = readSafe(RIGHT_PANEL);
const runOcrSrc = readSafe(RUNOCR);
const formDataSrc = readSafe(RUNOCR_FORMDATA);

// NOTE: depending on whether ops.ts has been moved by 5B, the relative path to
// common/types/ocr differs (3 levels up from src/components/ocr/core/ vs.
// 1 level up from src/common/utils/). Accept both.
checks.ops_imports_common_types =
  opsSrc !== null &&
  (/from\s+["']\.\.\/\.\.\/\.\.\/common\/types\/ocr["']/.test(opsSrc) ||
    /from\s+["']\.\.\/types\/ocr["']/.test(opsSrc)) &&
  !/from\s+["']\.\/types["']/.test(opsSrc);
// NOTE: depending on whether table.ts has been moved by 5C, the relative path
// to common/types/ocr differs (3 levels up from src/components/ocr/core/ vs.
// 1 level up from src/common/utils/). Accept both.
checks.table_imports_common_types =
  tableSrc !== null &&
  (/from\s+["']\.\.\/\.\.\/\.\.\/common\/types\/ocr["']/.test(tableSrc) ||
    /from\s+["']\.\.\/types\/ocr["']/.test(tableSrc)) &&
  !/from\s+["']\.\/types["']/.test(tableSrc);
// NOTE: export.ts may be at ocr/core/ (3 levels up to src/) or at
// template/utils/ (also 3 levels up to src/) — both depth-3 relative imports
// resolve identically. Either way we expect the common/types/ocr path.
checks.export_imports_common_types =
  exportSrc !== null &&
  /from\s+["']\.\.\/\.\.\/\.\.\/common\/types\/ocr["']/.test(exportSrc) &&
  !/from\s+["']\.\/types["']/.test(exportSrc);
// NOTE: depending on whether OcrCanvasPane has moved by 5F, the relative path
// to common/types/ocr differs (2 levels up from src/components/ocr/ vs.
// 1 level up from src/common/ui/). Accept both.
checks.canvas_imports_common_types =
  canvasSrc !== null &&
  (/from\s+["']\.\.\/\.\.\/common\/types\/ocr["']/.test(canvasSrc) ||
    /from\s+["']\.\.\/types\/ocr["']/.test(canvasSrc)) &&
  !/from\s+["']\.\/core\/types["']/.test(canvasSrc);
checks.annotator_imports_common_types =
  annotatorSrc !== null &&
  /from\s+["']\.\.\/\.\.\/\.\.\/common\/types\/ocr["']/.test(annotatorSrc) &&
  !/from\s+["']\.\.\/\.\.\/ocr\/core\/types["']/.test(annotatorSrc);
checks.right_panel_imports_common_types =
  rightPanelSrc !== null &&
  /from\s+["']\.\.\/\.\.\/\.\.\/common\/types\/ocr["']/.test(rightPanelSrc) &&
  !/from\s+["']\.\.\/\.\.\/ocr\/core\/types["']/.test(rightPanelSrc);
checks.runocr_workspace_imports_common_types =
  runOcrSrc !== null &&
  /from\s+["']\.\.\/\.\.\/common\/types\/ocr["']/.test(runOcrSrc) &&
  !/from\s+["']\.\.\/ocr\/core\/types["']/.test(runOcrSrc);
checks.runocr_formdata_imports_common_types =
  formDataSrc !== null &&
  /from\s+["']\.\.\/\.\.\/\.\.\/common\/types\/ocr["']/.test(formDataSrc) &&
  !/from\s+["']\.\.\/\.\.\/ocr\/core\/types["']/.test(formDataSrc);

// 9) ops.ts, table.ts, export.ts contents are logic-equivalent to backup
//    (only the import path was permitted to change).
const opsBackup = readSafe(resolve(BACKUP_DIR, "ops.ts"));
const tableBackup = readSafe(resolve(BACKUP_DIR, "table.ts"));
const exportBackup = readSafe(resolve(BACKUP_DIR, "export.ts"));
function stripImportPaths(src) {
  return src.replace(/from\s+["'][^"']+["']/g, 'from "<<IMPORT>>"');
}
function normalizeImportInsensitive(src) {
  return stripImportPaths(stripComments(src)).replace(/\s+/g, " ").trim();
}
checks.ops_logic_unchanged_vs_backup =
  opsSrc !== null && opsBackup !== null &&
  normalizeImportInsensitive(opsSrc) === normalizeImportInsensitive(opsBackup);
// TPL-12A phase-aware: ocrTableRegion.ts gained materializeTableRowsWithOverrides
// + MIN_ROW_HEIGHT beyond 5A's import-only scope. Skip the byte-equivalence
// guard when that marker is present.
const _tpl12aShipped_table_5a = typeof tableSrc === "string"
  && /materializeTableRowsWithOverrides/.test(tableSrc);
if (_tpl12aShipped_table_5a) {
  checks.table_logic_unchanged_vs_backup = true;
  checks._tpl12a_table_backup_check_skipped = true;
} else {
  checks.table_logic_unchanged_vs_backup =
    tableSrc !== null && tableBackup !== null &&
    normalizeImportInsensitive(tableSrc) === normalizeImportInsensitive(tableBackup);
}
// TPL-12B phase-aware: buildTemplateExportPayload now imports
// materializeTableRowsWithOverrides and applies it when a region carries
// rowOverrides — beyond 5A's import-only scope.
const _tpl12bShipped_export_5a = typeof exportSrc === "string"
  && /materializeTableRowsWithOverrides/.test(exportSrc);
if (_tpl12bShipped_export_5a) {
  checks.export_logic_unchanged_vs_backup = true;
  checks._tpl12b_export_backup_check_skipped = true;
} else {
  checks.export_logic_unchanged_vs_backup =
    exportSrc !== null && exportBackup !== null &&
    normalizeImportInsensitive(exportSrc) === normalizeImportInsensitive(exportBackup);
}

// 10) Type / interface export names preserved (spot check key names).
const REQUIRED_NAMES = [
  "FieldType",
  "CheckMode",
  "MappingStatus",
  "FieldMappingCandidate",
  "TableColumnDef",
  "Rect",
  "TableMeta",
  "Region",
  "LoadedImage",
  "DragKind",
];
checks.required_export_names_preserved =
  newTypesSrc !== null &&
  REQUIRED_NAMES.every((n) => new RegExp(`export\\s+type\\s+${n}\\b`).test(newTypesSrc));

const summary = {
  task: "FRONTEND-STRUCTURE-5A-OCR-CORE-TYPES-COMMON-MOVE",
  paths: {
    new_types: NEW_TYPES,
    old_types: OLD_TYPES,
    ops: OPS,
    table: TABLE,
    export: EXPORT,
    canvas: OCR_CANVAS,
    annotator: ANNOTATOR,
    right_panel: RIGHT_PANEL,
    runocr_workspace: RUNOCR,
    runocr_formdata: RUNOCR_FORMDATA,
  },
  checks,
};

console.log(JSON.stringify(summary, null, 2));

const required = [
  "new_types_exists",
  "old_types_absent",
  "ops_untouched_path",
  "table_untouched_path",
  "export_untouched_path",
  "OcrCanvasPane_untouched_path",
  "OcrAnnotator_untouched_path",
  "OcrRightPanel_untouched_path",
  "RunOcrWorkspace_present",
  "buildOcrFormData_present",
  "TestWorkspace_present",
  "test_core_types_present",
  "new_types_no_react_import",
  "new_types_no_components_import",
  "new_types_no_browser_api",
  "new_types_no_imports",
  "new_types_logic_unchanged_vs_backup",
  "ops_imports_common_types",
  "table_imports_common_types",
  "export_imports_common_types",
  "canvas_imports_common_types",
  "annotator_imports_common_types",
  "right_panel_imports_common_types",
  "runocr_workspace_imports_common_types",
  "runocr_formdata_imports_common_types",
  "ops_logic_unchanged_vs_backup",
  "table_logic_unchanged_vs_backup",
  "export_logic_unchanged_vs_backup",
  "required_export_names_preserved",
];
const allPass = required.every((k) => checks[k] === true);
console.log(`[OCR_CORE_TYPES_COMMON_MOVE_5A] ${allPass ? "PASS" : "FAIL"}`);
process.exit(allPass ? 0 : 1);
