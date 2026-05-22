#!/usr/bin/env node
// FRONTEND_STRUCTURE_3A_RUNOCR_RESULT_LAYOUT_SPLIT
// Static check: confirm the RunOCR result-branch layout was lifted into a
// presentational node-composition component (RunOcrResultLayout) without
// pulling state/handlers/request/mapping/history/autofill along, and that
// RunOcrControls was NOT created.
//
// Read-only. No production code is modified.

import { readFileSync, existsSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, "..");

const LAYOUT_PATH = resolve(ROOT, "src/components/runocr/ui/RunOcrResultLayout.tsx");
const CONTROLS_PATH = resolve(ROOT, "src/components/runocr/ui/RunOcrControls.tsx");
const WORKSPACE_PATH = resolve(ROOT, "src/components/runocr/RunOcrWorkspace.tsx");
const OCR_RESULT_PANEL_PATH = resolve(ROOT, "src/components/runocr/ui/OcrResultPanel.tsx");
const OCR_DOC_VIEWER_PATH = resolve(ROOT, "src/components/runocr/ui/OcrDocViewer.tsx");
const CORNER_ADJUST_PATH = resolve(ROOT, "src/components/runocr/ui/CornerAdjust.tsx");

function readSafe(p) { try { return readFileSync(p, "utf8"); } catch { return null; } }

const layoutSrc = readSafe(LAYOUT_PATH);
const workspaceSrc = readSafe(WORKSPACE_PATH);
const ocrResultPanelSrc = readSafe(OCR_RESULT_PANEL_PATH);
const ocrDocViewerSrc = readSafe(OCR_DOC_VIEWER_PATH);
const cornerAdjustSrc = readSafe(CORNER_ADJUST_PATH);

if (!layoutSrc) { console.error(`[FATAL] not found: ${LAYOUT_PATH}`); process.exit(2); }
if (!workspaceSrc) { console.error(`[FATAL] not found: ${WORKSPACE_PATH}`); process.exit(2); }

const checks = {};

// 1) RunOcrResultLayout.tsx exists
checks.layout_exists = existsSync(LAYOUT_PATH);

// 2) RunOcrControls.tsx must NOT exist (out of scope for 3A)
checks.controls_not_created = !existsSync(CONTROLS_PATH);

// 3) Layout exposes the expected node-composition props
const LAYOUT_PROP_NAMES = ["viewer", "resultPanel", "scanOverlay", "hiddenFileInput"];
checks.layout_props_present = LAYOUT_PROP_NAMES.every((name) =>
  new RegExp(`\\b${name}\\b\\s*[:?]`).test(layoutSrc),
);

// 4) Layout uses ReactNode-style props (no concrete prop types like OcrResult,
//    FieldType, etc.). Use word-boundary matching that also rejects identifiers
//    where the symbol is a prefix of a longer name (e.g. OcrResult in
//    OcrResultPanel, Corner in CornerAdjust) and ignore string occurrences
//    inside source code comments.
const stripComments = (src) =>
  src
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .replace(/(^|[^:])\/\/[^\n]*/g, "$1");
const layoutSrcNoComments = stripComments(layoutSrc);
const LAYOUT_HEAVY_PROP_TYPES = ["OcrResult", "OcrFieldResult", "FieldType", "Corner", "Region"];
const heavyTypesInLayout = LAYOUT_HEAVY_PROP_TYPES.filter((t) =>
  new RegExp(`(^|[^A-Za-z0-9_])${t}(?![A-Za-z0-9_])`).test(layoutSrcNoComments),
);
checks.layout_no_heavy_types = heavyTypesInLayout.length === 0;
checks.layout_heavy_types_found = heavyTypesInLayout;

// 5) Layout does NOT import OcrDocViewer / OcrResultPanel / CornerAdjust
const FORBIDDEN_CHILD_IMPORTS = [
  /from\s+["'][^"']*OcrDocViewer["']/,
  /from\s+["'][^"']*OcrResultPanel["']/,
  /from\s+["'][^"']*CornerAdjust["']/,
];
const childImportLeaks = FORBIDDEN_CHILD_IMPORTS.filter((re) => re.test(layoutSrc)).map((re) => re.source);
checks.layout_no_child_imports = childImportLeaks.length === 0;
checks.layout_child_import_leaks = childImportLeaks;

// 6) Layout does NOT touch fetch / history / autofill / runOcrRequest / buildOcrFormData / mapOcrResponse
const FORBIDDEN_KEYWORDS = [
  "fetch(",
  "appendHistoryRun",
  "updateHistoryRun",
  "syncHistoryIndexAndDetailOnCreate",
  "AutofillSuggestion",
  "AutofillRunSummary",
  "buildAutofillSuggestionsFromCandidates",
  "collectInternalAutofillCandidates",
  "applyAutofillToOutputFields",
  "runOcrRequest",
  "buildOcrFormData",
  "mapOcrResponse",
  "buildRunOcrResult",
  "useState",
  "useEffect",
  "useMemo",
  "useRef",
  "useRouter",
  "localStorage",
  "setOcrResult",
];
const leaked = FORBIDDEN_KEYWORDS.filter((k) => layoutSrc.includes(k));
checks.layout_no_forbidden_keywords = leaked.length === 0;
checks.layout_forbidden_keywords_found = leaked;

// 7) Workspace imports RunOcrResultLayout
checks.workspace_imports_layout =
  /import\s+RunOcrResultLayout\s+from\s+["']\.\/ui\/RunOcrResultLayout["']/.test(workspaceSrc);

// 8) Workspace renders <RunOcrResultLayout viewer={...} resultPanel={...} ... />
checks.workspace_renders_layout = /<\s*RunOcrResultLayout\b/.test(workspaceSrc);

// 9) Workspace must still own the runOcr/autofill/history flow
const RESIDENT_KEYWORDS = [
  "async function runOcr",
  "appendHistoryRun",
  "updateHistoryRun",
  "syncHistoryIndexAndDetailOnCreate",
  "AutofillSuggestion",
  "AutofillRunSummary",
  "setOcrResult",
  "useState",
  "useEffect",
];
const missingResident = RESIDENT_KEYWORDS.filter((k) => !workspaceSrc.includes(k));
checks.workspace_keeps_runocr_autofill_history = missingResident.length === 0;
checks.workspace_missing_resident_keywords = missingResident;

// 10) Workspace must no longer contain the inline `uw-result-root` wrapper duplicate.
//     (Layout owns it now; the workspace should not render it directly.)
checks.workspace_no_inline_result_root =
  !/<div\s+className=["']uw-result-root["']/.test(workspaceSrc);

// 11) The 3 protected ui components must be unchanged regarding their default export
//     signatures. (Light sanity: check the export default function names are intact.)
checks.ocrResultPanel_export_intact =
  ocrResultPanelSrc !== null && /export\s+default\s+function\s+OcrResultPanel/.test(ocrResultPanelSrc);
checks.ocrDocViewer_export_intact =
  ocrDocViewerSrc !== null && /export\s+default\s+function\s+OcrDocViewer/.test(ocrDocViewerSrc);
checks.cornerAdjust_export_intact =
  cornerAdjustSrc !== null && /export\s+default\s+function\s+CornerAdjust/.test(cornerAdjustSrc);

const summary = {
  task: "FRONTEND-STRUCTURE-3A-RUNOCR-RESULT-LAYOUT-SPLIT",
  layoutPath: LAYOUT_PATH,
  workspacePath: WORKSPACE_PATH,
  controlsPathChecked: CONTROLS_PATH,
  checks,
};
console.log(JSON.stringify(summary, null, 2));

const required = [
  "layout_exists",
  "controls_not_created",
  "layout_props_present",
  "layout_no_heavy_types",
  "layout_no_child_imports",
  "layout_no_forbidden_keywords",
  "workspace_imports_layout",
  "workspace_renders_layout",
  "workspace_keeps_runocr_autofill_history",
  "workspace_no_inline_result_root",
  "ocrResultPanel_export_intact",
  "ocrDocViewer_export_intact",
  "cornerAdjust_export_intact",
];
const allPass = required.every((k) => checks[k] === true);
console.log(`[RUNOCR_RESULT_LAYOUT_BOUNDARY] ${allPass ? "PASS" : "FAIL"}`);
process.exit(allPass ? 0 : 1);
