#!/usr/bin/env node
// TPL-13A-TEMPLATE-COLUMN-HIGHLIGHT-UI
// Verifies the column-highlight UI plumbing across TemplateAnnotator,
// TemplateRightPanel and OcrCanvasPane and confirms the interval math is
// consistent. This runner is source + math based — no browser interaction.
//
// Tag on success: [TEMPLATE_COLUMN_HIGHLIGHT_UI_TPL13A] PASS

import {
  readFileSync,
  existsSync,
  readdirSync,
  statSync,
  writeFileSync,
  mkdtempSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { resolve, dirname, relative, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { execSync } from "node:child_process";
import { register } from "node:module";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, "..");
const REPO_ROOT = resolve(ROOT, "..");
const TAG = "[TEMPLATE_COLUMN_HIGHLIGHT_UI_TPL13A]";

const LOADER_DIR = mkdtempSync(join(tmpdir(), "tpl13a-loader-"));
const LOADER_PATH = join(LOADER_DIR, "loader.mjs");
writeFileSync(LOADER_PATH, `
import { existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
export function resolve(specifier, context, next) {
  if (specifier.startsWith(".") && !/\\.(ts|tsx|js|mjs|cjs|json)$/.test(specifier)) {
    try {
      const candidate = new URL(specifier + ".ts", context.parentURL);
      if (existsSync(fileURLToPath(candidate))) return next(candidate.href, context);
    } catch {}
  }
  return next(specifier, context);
}
`);
register(pathToFileURL(LOADER_PATH).href);

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
function expect(cond, label) { if (!cond) fail(`smoke: ${label}`); else ok(`smoke: ${label}`); }

// ---------------------------------------------------------------------------
// Paths
// ---------------------------------------------------------------------------
const OCR_CANVAS_PANE = resolve(ROOT, "src/common/ui/OcrCanvasPane.tsx");
const TEMPLATE_ANNOTATOR = resolve(ROOT, "src/components/template/ui/TemplateAnnotator.tsx");
const TEMPLATE_RIGHT_PANEL = resolve(ROOT, "src/components/template/ui/TemplateRightPanel.tsx");
const PAYLOAD_BUILDER = resolve(ROOT, "src/components/template/utils/buildTemplateExportPayload.ts");
const TYPES_OCR = resolve(ROOT, "src/common/types/ocr.ts");
const TABLE_REGION = resolve(ROOT, "src/common/utils/ocrTableRegion.ts");
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
// 1. TemplateAnnotator: state + props forwarded + reset paths
// ---------------------------------------------------------------------------
const annSrc = readSafe(TEMPLATE_ANNOTATOR) ?? "";
const annCode = stripComments(annSrc);

if (!/const\s+\[\s*selectedTableColumnTarget\s*,\s*setSelectedTableColumnTarget\s*\]\s*=\s*useState/.test(annCode))
  fail(`TemplateAnnotator: selectedTableColumnTarget useState missing`);
else ok(`TemplateAnnotator: selectedTableColumnTarget useState present`);

if (!/<OcrCanvasPane[\s\S]{0,2500}selectedTableColumnTarget\s*=\s*\{\s*selectedTableColumnTarget\s*\}/.test(annCode))
  fail(`TemplateAnnotator does not forward selectedTableColumnTarget to OcrCanvasPane`);
else ok(`TemplateAnnotator forwards selectedTableColumnTarget to OcrCanvasPane`);

if (!/<TemplateRightPanel[\s\S]{0,2500}selectedTableColumnTarget\s*=\s*\{\s*selectedTableColumnTarget\s*\}[\s\S]{0,400}setSelectedTableColumnTarget\s*=\s*\{\s*setSelectedTableColumnTarget\s*\}/.test(annCode))
  fail(`TemplateAnnotator does not forward selectedTableColumnTarget + setter to TemplateRightPanel`);
else ok(`TemplateAnnotator forwards selectedTableColumnTarget + setter to TemplateRightPanel`);

const resetTouchCount = (annCode.match(/setSelectedTableColumnTarget\s*\(\s*null\s*\)/g) ?? []).length;
if (resetTouchCount < 3)
  fail(`TemplateAnnotator: setSelectedTableColumnTarget(null) reset paths < 3 (saw ${resetTouchCount})`);
else ok(`TemplateAnnotator: setSelectedTableColumnTarget(null) called in ${resetTouchCount} reset paths`);

// ---------------------------------------------------------------------------
// 2. TemplateRightPanel: prop typing + focus/click handlers + active style
// ---------------------------------------------------------------------------
const trpSrc = readSafe(TEMPLATE_RIGHT_PANEL) ?? "";
const trpCode = stripComments(trpSrc);

if (!/selectedTableColumnTarget\s*:\s*\{[^}]*regionId\s*:\s*string[^}]*columnIndex\s*:\s*number/.test(trpCode))
  fail(`TemplateRightPanel: selectedTableColumnTarget prop type shape missing`);
else ok(`TemplateRightPanel: selectedTableColumnTarget prop type present`);
if (!/setSelectedTableColumnTarget\s*:\s*React\.Dispatch/.test(trpCode))
  fail(`TemplateRightPanel: setSelectedTableColumnTarget setter type missing`);
else ok(`TemplateRightPanel: setSelectedTableColumnTarget setter type present`);

// focusThisColumn helper (the click+focus handler)
if (!/focusThisColumn/.test(trpCode))
  fail(`TemplateRightPanel: focusThisColumn helper not defined`);
else ok(`TemplateRightPanel: focusThisColumn helper present`);
// setSelectedTableColumnTarget called with regionId/columnIndex shape
if (!/setSelectedTableColumnTarget\s*\(\s*\{\s*regionId\s*:\s*selected\.id\s*,\s*columnIndex\s*:\s*col\.index\s*\}\s*\)/.test(trpCode))
  fail(`TemplateRightPanel: setSelectedTableColumnTarget not called with {regionId, columnIndex}`);
else ok(`TemplateRightPanel: setSelectedTableColumnTarget({regionId, columnIndex}) wired`);

// Click + 3 focus call sites
if (!/onClick\s*=\s*\{\s*focusThisColumn\s*\}/.test(trpCode))
  fail(`TemplateRightPanel: column row onClick=focusThisColumn missing`);
else ok(`TemplateRightPanel: column row onClick=focusThisColumn present`);
const focusOnCount = (trpCode.match(/onFocus\s*=\s*\{\s*focusThisColumn\s*\}/g) ?? []).length;
if (focusOnCount < 3)
  fail(`TemplateRightPanel: onFocus=focusThisColumn count < 3 (labelKo + columnKey + canonical) — saw ${focusOnCount}`);
else ok(`TemplateRightPanel: onFocus=focusThisColumn on ${focusOnCount} controls (labelKo+columnKey+canonical)`);

// Active row style marker
if (!/isColTargetActive/.test(trpCode))
  fail(`TemplateRightPanel: isColTargetActive flag missing`);
else ok(`TemplateRightPanel: isColTargetActive active-style flag present`);

// ---------------------------------------------------------------------------
// 3. OcrCanvasPane: prop + overlay + interval math + pointerEvents none
// ---------------------------------------------------------------------------
const canvasSrc = readSafe(OCR_CANVAS_PANE) ?? "";
const canvasCode = stripComments(canvasSrc);

if (!/selectedTableColumnTarget\?\s*:\s*\{[^}]*regionId\s*:\s*string[^}]*columnIndex\s*:\s*number\s*\}\s*\|\s*null/.test(canvasCode))
  fail(`OcrCanvasPane: selectedTableColumnTarget?: prop type shape missing`);
else ok(`OcrCanvasPane: selectedTableColumnTarget? prop type present`);

if (!/data-role="column-highlight-overlay"/.test(canvasCode))
  fail(`OcrCanvasPane: data-role="column-highlight-overlay" marker missing`);
else ok(`OcrCanvasPane: column-highlight-overlay marker present`);

// Interval math markers (left/right ratio)
if (!/colHL_left/.test(canvasCode) || !/colHL_right/.test(canvasCode))
  fail(`OcrCanvasPane: colHL_left/colHL_right interval ratio markers missing`);
else ok(`OcrCanvasPane: colHL_left/colHL_right markers present`);

// colGuides-based interval calc uses normalizeColGuides
if (!/normalizeColGuides\s*\(\s*r\.table\?\.colGuides\s*\)/.test(canvasCode))
  fail(`OcrCanvasPane: column overlay does not use normalizeColGuides(r.table?.colGuides)`);
else ok(`OcrCanvasPane: column overlay uses normalizeColGuides(r.table?.colGuides)`);

// Out-of-range guard
if (!/colHL_idx\s*<\s*0\s*\|\|\s*colHL_idx\s*>=\s*colHL_colCount/.test(canvasCode))
  fail(`OcrCanvasPane: column overlay out-of-range guard missing`);
else ok(`OcrCanvasPane: out-of-range columnIndex guard present`);

// regionId match guard
if (!/selectedTableColumnTarget\.regionId\s*===\s*r\.id/.test(canvasCode))
  fail(`OcrCanvasPane: column overlay does not gate on regionId === r.id`);
else ok(`OcrCanvasPane: regionId === r.id guard present`);

// pointerEvents none (overlay must not block other interactions)
// Locate the overlay block and verify pointerEvents: "none" inside it.
const overlayBlockMatch = canvasCode.match(
  /data-role="column-highlight-overlay"[\s\S]{0,800}?pointerEvents\s*:\s*"none"/,
);
if (!overlayBlockMatch)
  fail(`OcrCanvasPane: column overlay missing pointerEvents: "none"`);
else ok(`OcrCanvasPane: column overlay has pointerEvents: "none"`);

// 컬럼 N badge label
if (!/컬럼\s*\$\{\s*colHL_idx\s*\+\s*1\s*\}/.test(canvasCode)
    && !/컬럼\s*\{[^}]*colHL_idx[^}]*\+\s*1[^}]*\}/.test(canvasCode))
  fail(`OcrCanvasPane: column overlay '컬럼 N' label missing`);
else ok(`OcrCanvasPane: '컬럼 N' label present in overlay`);

// TPL-12G + earlier flows still intact
if (!/rowAdjustTargetId/.test(canvasCode)) fail(`OcrCanvasPane: rowAdjustTargetId regressed`);
else ok(`OcrCanvasPane: rowAdjustTargetId preserved (TPL-12C)`);
if (!/data-role="row-boundary-handle"/.test(canvasCode)) fail(`OcrCanvasPane: row-boundary-handle regressed`);
else ok(`OcrCanvasPane: row-boundary-handle preserved (TPL-12C)`);
if (!/upsertRowOverrideLocal/.test(canvasCode)) fail(`OcrCanvasPane: local-adjust helper regressed`);
else ok(`OcrCanvasPane: local-adjust helper preserved (TPL-12G)`);
if (!/drawRowTemplate/.test(canvasCode)) fail(`OcrCanvasPane: drawRowTemplate flow regressed`);
else ok(`OcrCanvasPane: drawRowTemplate flow preserved`);

// ---------------------------------------------------------------------------
// 4. Out-of-scope files MUST NOT carry TPL-13A symbols
// ---------------------------------------------------------------------------
const TPL13A_ALLOW = new Set([
  TEMPLATE_ANNOTATOR,
  TEMPLATE_RIGHT_PANEL,
  OCR_CANVAS_PANE,
]);
for (const [label, p] of [
  ["buildTemplateExportPayload.ts", PAYLOAD_BUILDER],
  ["types/ocr.ts", TYPES_OCR],
  ["ocrTableRegion.ts", TABLE_REGION],
  ["tableResultViewModel.ts", VIEWMODEL_HELPER],
  ["OcrResultPanel.tsx", OCR_RESULT_PANEL],
  ["RunOcrWorkspace.tsx", RUNOCR_WORKSPACE],
  ["cleanJsonBuilder.ts", CLEAN_JSON],
  ["markdownReportBuilder.ts", MARKDOWN_REPORT],
  ["UnstructuredBuilder.tsx", UNSTRUCTURED_BUILDER],
  ["unstructuredDefinition.ts", UNSTRUCTURED_DEF],
]) {
  if (TPL13A_ALLOW.has(p)) continue;
  const codeOnly = stripComments(readSafe(p) ?? "");
  if (/selectedTableColumnTarget|setSelectedTableColumnTarget|column-highlight-overlay|colHL_/.test(codeOnly))
    fail(`${label} carries TPL-13A symbols (out of scope)`);
  else ok(`${label}: no TPL-13A symbols (out of scope)`);
}

// Backend / templates.json untouched
if (existsSync(BACKEND_MAIN)) {
  const py = readSafe(BACKEND_MAIN) ?? "";
  if (/selectedTableColumnTarget|column-highlight-overlay|colHL_/.test(py))
    fail(`ocr-server/main.py references TPL-13A symbols — backend untouched policy violated`);
  else ok(`ocr-server/main.py: no TPL-13A symbols`);
}
if (existsSync(TEMPLATES_JSON)) {
  if (/selectedTableColumnTarget|column-highlight-overlay/.test(readSafe(TEMPLATES_JSON) ?? ""))
    fail(`templates.json carries TPL-13A symbols (forbidden)`);
  else ok(`templates.json: no TPL-13A symbols`);
}
if (existsSync(TEST_WORKSPACE)) {
  const tw = stripComments(readSafe(TEST_WORKSPACE) ?? "");
  if (/selectedTableColumnTarget|column-highlight-overlay/.test(tw))
    fail(`TestWorkspace.tsx carries TPL-13A symbols (forbidden)`);
  else ok(`TestWorkspace.tsx: no TPL-13A symbols`);
}

// ---------------------------------------------------------------------------
// 5. src/lib absent + @/lib imports = 0
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
// 6. Runtime smoke — column interval math (mirror of overlay logic)
//    Imports normalizeColGuides from ocrTableRegion and computes left/right
//    ratios the same way the JSX does.
// ---------------------------------------------------------------------------
let helperMod = null;
try {
  helperMod = await import(pathToFileURL(TABLE_REGION).href);
  ok(`ocrTableRegion runtime import succeeded`);
} catch (err) { fail(`ocrTableRegion runtime import failed: ${err?.message ?? err}`); }
if (!helperMod) {
  console.error(`${TAG} FAIL aborting — imports failed`);
  console.error(`${TAG} FAIL count=${failures.length}`);
  process.exit(1);
}
const { normalizeColGuides } = helperMod;
expect(typeof normalizeColGuides === "function", `normalizeColGuides is function`);

function computeColInterval(rawGuides, columnIndex) {
  const guides = normalizeColGuides(rawGuides);
  const colCount = guides.length + 1;
  if (columnIndex < 0 || columnIndex >= colCount) return null;
  const left = columnIndex === 0 ? 0 : guides[columnIndex - 1];
  const right = columnIndex === guides.length ? 1 : guides[columnIndex];
  return { left, right, widthRatio: Math.max(0, right - left), colCount };
}

// ── SMOKE 1: no colGuides — full region highlight ─────────────────────────
{
  const out = computeColInterval([], 0);
  expect(out !== null, "case1 no guides: column 0 yields overlay");
  expect(out.left === 0 && out.right === 1,
    "case1 no guides: left=0 right=1 (entire region)");
  expect(out.colCount === 1, "case1 no guides: colCount=1");
}

// ── SMOKE 2: colGuides 2 → 3 intervals ────────────────────────────────────
{
  const guides = [0.3, 0.7];
  const c0 = computeColInterval(guides, 0);
  const c1 = computeColInterval(guides, 1);
  const c2 = computeColInterval(guides, 2);
  expect(c0 && c0.left === 0 && Math.abs(c0.right - 0.3) < 1e-9,
    "case2 N=2: column 0 → [0, 0.3]");
  expect(c1 && Math.abs(c1.left - 0.3) < 1e-9 && Math.abs(c1.right - 0.7) < 1e-9,
    "case2 N=2: column 1 → [0.3, 0.7]");
  expect(c2 && Math.abs(c2.left - 0.7) < 1e-9 && c2.right === 1,
    "case2 N=2: column 2 → [0.7, 1]");
}

// ── SMOKE 3: out-of-range columnIndex → no overlay ────────────────────────
{
  const guides = [0.3, 0.7];
  expect(computeColInterval(guides, 3) === null,
    "case3 out-of-range: columnIndex 3 with N=2 returns null");
  expect(computeColInterval(guides, -1) === null,
    "case3 out-of-range: columnIndex -1 returns null");
  expect(computeColInterval([], 1) === null,
    "case3 out-of-range: columnIndex 1 with no guides returns null");
}

// ── SMOKE 4: guides get sorted/dedup'd via normalizeColGuides ─────────────
{
  // Out-of-order + near-dup guides should be normalized.
  const messy = [0.7, 0.3, 0.301];  // 0.301 is within eps of 0.3 → deduplicated
  const c0 = computeColInterval(messy, 0);
  const c1 = computeColInterval(messy, 1);
  const c2 = computeColInterval(messy, 2);
  expect(c0 && c0.left === 0 && c0.right < 0.5,
    "case4 normalize: column 0 right edge under 0.5");
  expect(c1 && c1.left < 0.5 && c1.right > 0.5,
    "case4 normalize: column 1 straddles 0.5");
  expect(c2 && c2.right === 1,
    "case4 normalize: last column reaches 1");
  expect(c0.colCount === c1.colCount && c0.colCount === 3,
    "case4 normalize: dedup reduces messy 3-guide input to 2 guides → 3 columns");
}

// ── SMOKE 5: 0/1 edge values filtered out by normalizeColGuides ───────────
{
  const edge = [0, 0.4, 1];  // 0 and 1 should be excluded
  const c = computeColInterval(edge, 0);
  expect(c && c.colCount === 2,
    "case5 edge: 0 and 1 dropped by normalizeColGuides → only one real guide → 2 columns");
}

// ---------------------------------------------------------------------------
// 7. New-file scope check
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
  if (hits === 0) ok(`new-file scope check: clean`);
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
