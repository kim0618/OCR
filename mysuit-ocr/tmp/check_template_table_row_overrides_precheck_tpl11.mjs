#!/usr/bin/env node
// TPL-11-TEMPLATE-TABLE-ROW-OVERRIDES-PRECHECK
// Pure precheck. No production code modification — only verifies current
// state and confirms the precheck markdown carries all required sections.
//
// Tag on success: [TEMPLATE_TABLE_ROW_OVERRIDES_PRECHECK_TPL11] PASS

import {
  readFileSync,
  existsSync,
  readdirSync,
  statSync,
} from "node:fs";
import { resolve, dirname, relative } from "node:path";
import { fileURLToPath } from "node:url";
import { execSync } from "node:child_process";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, "..");
const REPO_ROOT = resolve(ROOT, "..");
const TAG = "[TEMPLATE_TABLE_ROW_OVERRIDES_PRECHECK_TPL11]";

const failures = [];
function fail(msg) { failures.push(msg); console.error(`${TAG} FAIL ${msg}`); }
function note(msg) { console.log(`${TAG} NOTE ${msg}`); }
function ok(msg)   { console.log(`${TAG} OK ${msg}`); }
function readSafe(p) { try { return readFileSync(p, "utf8"); } catch { return null; } }
function walk(dir) {
  const out = [];
  const stack = [dir];
  while (stack.length) {
    const cur = stack.pop();
    let entries = [];
    try { entries = readdirSync(cur); } catch { continue; }
    for (const e of entries) {
      const p = resolve(cur, e);
      let st;
      try { st = statSync(p); } catch { continue; }
      if (st.isDirectory()) stack.push(p);
      else out.push(p);
    }
  }
  return out;
}
function stripComments(src) {
  return src.replace(/\/\*[\s\S]*?\*\//g, "").replace(/(^|[^:])\/\/[^\n]*/g, "$1");
}

// ---------------------------------------------------------------------------
// Paths
// ---------------------------------------------------------------------------
const PRECHECK_MD = resolve(ROOT, "tmp/tpl_11_template_table_row_overrides_precheck.md");
const OCR_CANVAS_PANE = resolve(ROOT, "src/common/ui/OcrCanvasPane.tsx");
const OCR_TABLE_REGION = resolve(ROOT, "src/common/utils/ocrTableRegion.ts");
const OCR_CANVAS_OPS = resolve(ROOT, "src/common/utils/ocrCanvasOps.ts");
const PAYLOAD_BUILDER = resolve(ROOT, "src/components/template/utils/buildTemplateExportPayload.ts");
const TEMPLATE_RIGHT_PANEL = resolve(ROOT, "src/components/template/ui/TemplateRightPanel.tsx");
const TEMPLATE_ANNOTATOR = resolve(ROOT, "src/components/template/ui/TemplateAnnotator.tsx");
const TYPES_OCR = resolve(ROOT, "src/common/types/ocr.ts");
const VIEWMODEL_HELPER = resolve(ROOT, "src/common/utils/tableResultViewModel.ts");
const OCR_RESULT_PANEL = resolve(ROOT, "src/components/runocr/ui/OcrResultPanel.tsx");
const RUNOCR_WORKSPACE = resolve(ROOT, "src/components/runocr/RunOcrWorkspace.tsx");
const CLEAN_JSON = resolve(ROOT, "src/common/utils/cleanJsonBuilder.ts");
const MARKDOWN_REPORT = resolve(ROOT, "src/common/utils/markdownReportBuilder.ts");
const UNSTRUCTURED_BUILDER = resolve(ROOT, "src/components/template/UnstructuredBuilder.tsx");
const UNSTRUCTURED_DEF = resolve(ROOT, "src/components/template/utils/unstructuredDefinition.ts");
const TEST_WORKSPACE = resolve(ROOT, "src/components/test/TestWorkspace.tsx");
const BACKEND_MAIN = resolve(REPO_ROOT, "ocr-server/main.py");
const TEMPLATES_JSON = resolve(REPO_ROOT, "ocr-server/data/templates.json");

// ---------------------------------------------------------------------------
// 1. Precheck markdown present + required sections
// ---------------------------------------------------------------------------
if (!existsSync(PRECHECK_MD)) {
  fail(`precheck markdown missing: ${relative(ROOT, PRECHECK_MD)}`);
} else {
  ok(`precheck markdown present`);
  const md = readSafe(PRECHECK_MD) ?? "";
  const REQUIRED_SECTIONS = [
    /^##\s+1\.\s+Summary/m,
    /^##\s+2\.\s+Current Row Flow/m,
    /^##\s+3\.\s+Current Schema/m,
    /^##\s+4\.\s+Row Override Options/m,
    /^##\s+5\.\s+Recommended Schema/m,
    /^##\s+6\.\s+Merge \/ Materialization Strategy/m,
    /^##\s+7\.\s+UI Interaction Plan/m,
    /^##\s+8\.\s+Backend \/ Payload Impact/m,
    /^##\s+9\.\s+Implementation Plan/m,
    /^##\s+10\.\s+Risk Assessment/m,
    /^##\s+11\.\s+Do Not Start Yet/m,
    /^##\s+12\.\s+Verification Results/m,
  ];
  for (const re of REQUIRED_SECTIONS) {
    if (!re.test(md)) fail(`precheck section missing: ${re}`);
    else ok(`precheck section present: ${re.source.replace(/\\.|\^|\$|\?|\+|\\s\+/g, " ").trim()}`);
  }
  for (const tag of ["TPL-12A", "TPL-12B", "TPL-12C", "TPL-12D"]) {
    if (!md.includes(tag)) fail(`precheck missing micro-step tag: ${tag}`);
    else ok(`precheck includes micro-step tag: ${tag}`);
  }
  if (!/rowOverrides/.test(md)) fail(`precheck does not mention rowOverrides`);
  else ok(`precheck mentions rowOverrides`);
  if (!/TableRowOverride/.test(md)) fail(`precheck does not name TableRowOverride schema`);
  else ok(`precheck names TableRowOverride schema`);
  if (!/materializeTableRowsWithOverrides/.test(md))
    fail(`precheck does not name materialize helper`);
  else ok(`precheck names materializeTableRowsWithOverrides`);
}

// ---------------------------------------------------------------------------
// 2. Required production files still exist (this precheck did not delete them)
// ---------------------------------------------------------------------------
const REQUIRED_FILES = [
  ["OcrCanvasPane.tsx", OCR_CANVAS_PANE],
  ["ocrTableRegion.ts", OCR_TABLE_REGION],
  ["ocrCanvasOps.ts", OCR_CANVAS_OPS],
  ["buildTemplateExportPayload.ts", PAYLOAD_BUILDER],
  ["TemplateRightPanel.tsx", TEMPLATE_RIGHT_PANEL],
  ["TemplateAnnotator.tsx", TEMPLATE_ANNOTATOR],
  ["ocr.ts (types)", TYPES_OCR],
  ["tableResultViewModel.ts", VIEWMODEL_HELPER],
  ["OcrResultPanel.tsx", OCR_RESULT_PANEL],
  ["RunOcrWorkspace.tsx", RUNOCR_WORKSPACE],
  ["cleanJsonBuilder.ts", CLEAN_JSON],
  ["markdownReportBuilder.ts", MARKDOWN_REPORT],
  ["UnstructuredBuilder.tsx", UNSTRUCTURED_BUILDER],
  ["unstructuredDefinition.ts", UNSTRUCTURED_DEF],
  ["TestWorkspace.tsx", TEST_WORKSPACE],
];
for (const [label, p] of REQUIRED_FILES) {
  if (!existsSync(p)) fail(`required file missing: ${label}`);
  else ok(`present: ${label}`);
}

// ---------------------------------------------------------------------------
// 3. Operational code zero-touch policy for THIS precheck.
//    TPL-11 itself must not introduce rowOverrides anywhere. TPL-12A later
//    legitimately added the schema (types/ocr.ts) and the pure helper
//    (ocrTableRegion.ts) — those two are phase-aware allow-listed below.
//    All other operational files must still be symbol-free.
// ---------------------------------------------------------------------------
const _TPL12A_ALLOW_PATHS = new Set([
  TYPES_OCR,
  OCR_TABLE_REGION,
  PAYLOAD_BUILDER,
  OCR_CANVAS_PANE,         // TPL-12C
  TEMPLATE_ANNOTATOR,      // TPL-12C
  TEMPLATE_RIGHT_PANEL,    // TPL-12C
]);
for (const [label, p] of [
  ["OcrCanvasPane.tsx", OCR_CANVAS_PANE],
  ["ocrTableRegion.ts", OCR_TABLE_REGION],
  ["ocrCanvasOps.ts", OCR_CANVAS_OPS],
  ["buildTemplateExportPayload.ts", PAYLOAD_BUILDER],
  ["TemplateRightPanel.tsx", TEMPLATE_RIGHT_PANEL],
  ["TemplateAnnotator.tsx", TEMPLATE_ANNOTATOR],
  ["ocr.ts (types)", TYPES_OCR],
  ["tableResultViewModel.ts", VIEWMODEL_HELPER],
  ["OcrResultPanel.tsx", OCR_RESULT_PANEL],
  ["RunOcrWorkspace.tsx", RUNOCR_WORKSPACE],
  ["cleanJsonBuilder.ts", CLEAN_JSON],
  ["markdownReportBuilder.ts", MARKDOWN_REPORT],
  ["UnstructuredBuilder.tsx", UNSTRUCTURED_BUILDER],
  ["unstructuredDefinition.ts", UNSTRUCTURED_DEF],
]) {
  const codeOnly = stripComments(readSafe(p) ?? "");
  const hasSymbol = /rowOverrides|materializeTableRowsWithOverrides|TableRowOverride/.test(codeOnly);
  if (_TPL12A_ALLOW_PATHS.has(p)) {
    if (hasSymbol) note(`${label}: rowOverride symbol present (allowed — TPL-12A shipped)`);
    else ok(`${label}: no rowOverride symbol yet (TPL-12A not shipped or out of scope)`);
  } else {
    if (hasSymbol)
      fail(`${label} contains rowOverrides symbol in code (out of TPL-12A allow-list)`);
    else ok(`${label}: no rowOverrides symbols (zero-touch)`);
  }
}

// ---------------------------------------------------------------------------
// 4. src/lib absent + @/lib imports = 0
// ---------------------------------------------------------------------------
const SRC_LIB = resolve(ROOT, "src/lib");
if (existsSync(SRC_LIB)) {
  const f = walk(SRC_LIB);
  if (f.length > 0) fail(`src/lib must be absent or empty`);
  else ok(`src/lib present but empty`);
} else ok(`src/lib absent`);

const SRC_ROOT = resolve(ROOT, "src");
const allSrcFiles = walk(SRC_ROOT).filter((p) =>
  p.endsWith(".ts") || p.endsWith(".tsx") || p.endsWith(".mjs") || p.endsWith(".js")
);
const reLibAlias = /from\s+["']@\/lib(\/|["'])|import\(\s*["']@\/lib(\/|["'])/;
const reLibRelative = /from\s+["']\.\.\/lib(\/|["'])|from\s+["']\.\.\/\.\.\/lib(\/|["'])/;
let aliasHits = 0, relHits = 0;
for (const p of allSrcFiles) {
  const src = readSafe(p) ?? "";
  if (reLibAlias.test(src)) { aliasHits++; fail(`@/lib import in ${relative(ROOT, p)}`); }
  if (reLibRelative.test(src)) { relHits++; fail(`relative lib import in ${relative(ROOT, p)}`); }
}
if (aliasHits === 0) ok(`@/lib imports: 0`);
if (relHits === 0) ok(`relative lib imports: 0`);

// ---------------------------------------------------------------------------
// 5. Current row-flow markers — informational summary only (do not fail).
// ---------------------------------------------------------------------------
const canvasSrc = readSafe(OCR_CANVAS_PANE) ?? "";
const canvasCode = stripComments(canvasSrc);
note(`OcrCanvasPane rowTemplate occurrences: ${(canvasCode.match(/rowTemplate/g) ?? []).length}`);
note(`OcrCanvasPane buildTableRows call sites: ${(canvasCode.match(/buildTableRows\s*\(/g) ?? []).length}`);
note(`OcrCanvasPane "drawRowTemplate" drag type: ${/drawRowTemplate/.test(canvasCode) ? "present" : "absent"}`);

const regionSrc = readSafe(OCR_TABLE_REGION) ?? "";
const regionCode = stripComments(regionSrc);
if (/export\s+function\s+buildTableRows\s*\(/.test(regionCode))
  ok(`buildTableRows export present in ocrTableRegion.ts`);
else fail(`buildTableRows export missing from ocrTableRegion.ts`);
if (/export\s+function\s+autoDetectRowBands\s*\(/.test(regionCode))
  ok(`autoDetectRowBands export present (mode=auto path)`);
else note(`autoDetectRowBands export absent — only "repeat" mode in helper`);

const typesSrc = readSafe(TYPES_OCR) ?? "";
const typesCode = stripComments(typesSrc);
if (/rowTemplate\?\s*:\s*Rect/.test(typesCode))
  ok(`TableMeta.rowTemplate?: Rect present in types`);
else fail(`TableMeta.rowTemplate?: Rect missing from types`);
if (/rows\?\s*:\s*Rect\[\]/.test(typesCode))
  ok(`TableMeta.rows?: Rect[] present in types`);
else fail(`TableMeta.rows?: Rect[] missing from types`);
if (/rowOverrides/.test(typesCode))
  note(`types/ocr.ts declares rowOverrides (phase-aware NOTE — TPL-12A shipped)`);
else ok(`types/ocr.ts has no rowOverrides yet (TPL-12A not shipped)`);

const payloadSrc = readSafe(PAYLOAD_BUILDER) ?? "";
const payloadCode = stripComments(payloadSrc);
if (/rowTemplate\b/.test(payloadCode))
  ok(`buildTemplateExportPayload emits rowTemplate`);
else fail(`buildTemplateExportPayload does not emit rowTemplate`);
if (/\brows\b/.test(payloadCode))
  ok(`buildTemplateExportPayload emits rows`);
else fail(`buildTemplateExportPayload does not emit rows`);
if (/rowOverrides/.test(payloadCode))
  note(`buildTemplateExportPayload emits rowOverrides (phase-aware NOTE — TPL-12B shipped)`);
else ok(`buildTemplateExportPayload has no rowOverrides yet (TPL-12B not shipped)`);

// ---------------------------------------------------------------------------
// 6. Backend payload usage — confirm rows / rowTemplate NOT consumed by main.py
//    (informational notes only; missing backend should not fail this precheck).
// ---------------------------------------------------------------------------
if (existsSync(BACKEND_MAIN)) {
  const py = readSafe(BACKEND_MAIN) ?? "";
  // We strip Python single-line # comments and triple-quoted blocks for fairness.
  const pyCode = py
    .replace(/'''[\s\S]*?'''/g, "")
    .replace(/"""[\s\S]*?"""/g, "")
    .replace(/^[ \t]*#[^\n]*$/gm, "");
  const consumesRowTemplate = /\brow_template\b|\["rowTemplate"\]|\.get\(\s*["']rowTemplate["']/.test(pyCode);
  const consumesRows = /\["rows"\]|\.get\(\s*["']rows["']\s*\)/.test(pyCode);
  if (consumesRowTemplate)
    note(`backend main.py references rowTemplate (re-check before TPL-12)`);
  else ok(`backend main.py does NOT consume rowTemplate (rowOverrides is frontend-only safe)`);
  if (consumesRows)
    note(`backend main.py references region.table.rows (re-check before TPL-12)`);
  else ok(`backend main.py does NOT consume region.table.rows (rowOverrides is frontend-only safe)`);
} else {
  note(`backend main.py not found at ${BACKEND_MAIN} — backend contract not verified`);
}

// ---------------------------------------------------------------------------
// 7. Existing templates.json — confirm rowOverrides not yet introduced
// ---------------------------------------------------------------------------
if (existsSync(TEMPLATES_JSON)) {
  const tjs = readSafe(TEMPLATES_JSON) ?? "";
  if (/rowOverrides/.test(tjs))
    note(`templates.json contains rowOverrides — expected once TPL-12 ships (user-saved data; phase-aware NOTE)`);
  else ok(`templates.json: no rowOverrides yet (backward-compat baseline confirmed)`);
} else {
  note(`templates.json not found — skipping backward-compat baseline check`);
}

// ---------------------------------------------------------------------------
// 8. New-file scope check — only the two precheck artifacts should be new
// ---------------------------------------------------------------------------
function gitStatusPorcelain() {
  try {
    return execSync("git status --porcelain", {
      cwd: REPO_ROOT, stdio: ["ignore", "pipe", "ignore"],
    }).toString("utf8").split(/\r?\n/).filter(Boolean);
  } catch { return null; }
}
const porcelain = gitStatusPorcelain();
if (porcelain == null) note(`git status unavailable — skipping new-file scope check`);
else {
  const FORBID_NEW = [
    /^mysuit-ocr\/src\/components\/test\//,
    /^mysuit-ocr\/src\/components\/runocr\//,
    /^mysuit-ocr\/src\/components\/template\//,
    /^mysuit-ocr\/src\/common\//,
    /^mysuit-ocr\/src\/app\//,
    /^mysuit-ocr\/public\/data\/testsets\//,
    /^ocr-server\//,
  ];
  const PHASE_ALLOW = new Set([
    "mysuit-ocr/src/components/template/utils/unstructuredDefinition.ts", // TPL-3
    "mysuit-ocr/src/components/runocr/utils/extractUnstructuredTableRows.ts", // TPL-8B
    "mysuit-ocr/src/common/utils/tableResultViewModel.ts", // TPL-8D
  ]);
  let hits = 0;
  for (const line of porcelain) {
    if (!line.startsWith("?? ")) continue;
    const path = line.slice(3).replace(/^"|"$/g, "");
    if (!FORBID_NEW.some((re) => re.test(path))) continue;
    if (PHASE_ALLOW.has(path)) { note(`new production (allowed from earlier phases): ${path}`); continue; }
    fail(`new untracked production file: ${path}`); hits++;
  }
  if (hits === 0) ok(`new-file scope check: clean (only tmp artefacts permitted)`);
}

// ---------------------------------------------------------------------------
if (failures.length === 0) {
  console.log(`${TAG} PASS`);
  process.exit(0);
} else {
  console.error(`${TAG} FAIL count=${failures.length}`);
  for (const m of failures) console.error(`${TAG}   - ${m}`);
  process.exit(1);
}
