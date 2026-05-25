#!/usr/bin/env node
// TPL-12G-ROW-BOUNDARY-LOCAL-ADJUST-FIX
// Verifies the row boundary drag was switched from height-only cascade to
// LOCAL boundary adjust (row i + row i+1 only, row i+2+ unchanged) AND that
// the region move handler shifts absolute-y rowOverrides by dy.
//
// Tag on success: [ROW_BOUNDARY_LOCAL_ADJUST_TPL12G] PASS

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
const TAG = "[ROW_BOUNDARY_LOCAL_ADJUST_TPL12G]";

const LOADER_DIR = mkdtempSync(join(tmpdir(), "tpl12g-loader-"));
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
const TABLE_REGION = resolve(ROOT, "src/common/utils/ocrTableRegion.ts");
const TYPES_OCR = resolve(ROOT, "src/common/types/ocr.ts");
const PAYLOAD_BUILDER = resolve(ROOT, "src/components/template/utils/buildTemplateExportPayload.ts");
const TEMPLATE_ANNOTATOR = resolve(ROOT, "src/components/template/ui/TemplateAnnotator.tsx");
const TEMPLATE_RIGHT_PANEL = resolve(ROOT, "src/components/template/ui/TemplateRightPanel.tsx");
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
// 1. OcrCanvasPane: TPL-12G markers + helper untouched
// ---------------------------------------------------------------------------
const canvasSrc = readSafe(OCR_CANVAS_PANE) ?? "";
const canvasCode = stripComments(canvasSrc);

if (!/rowTopY/.test(canvasCode))
  fail(`OcrCanvasPane: rowTopY anchor not present (TPL-12G local adjust marker)`);
else ok(`OcrCanvasPane: rowTopY anchor present (TPL-12G)`);
if (!/nextBottomY/.test(canvasCode))
  fail(`OcrCanvasPane: nextBottomY anchor not present (TPL-12G local adjust marker)`);
else ok(`OcrCanvasPane: nextBottomY anchor present (TPL-12G)`);
if (!/hasNextRow/.test(canvasCode))
  fail(`OcrCanvasPane: hasNextRow flag not present`);
else ok(`OcrCanvasPane: hasNextRow flag present`);

// Local adjust math markers
if (!/boundaryY/.test(canvasCode))
  fail(`OcrCanvasPane: boundaryY variable missing in drag frame`);
else ok(`OcrCanvasPane: boundaryY variable present`);
if (!/upperHeight/.test(canvasCode) || !/lowerHeight/.test(canvasCode))
  fail(`OcrCanvasPane: upperHeight/lowerHeight markers missing`);
else ok(`OcrCanvasPane: upperHeight/lowerHeight markers present`);

// row i+1 override emitted
if (!/d\.rowIndex\s*\+\s*1/.test(canvasCode))
  fail(`OcrCanvasPane: row i+1 override (d.rowIndex + 1) not emitted`);
else ok(`OcrCanvasPane: row i+1 override emitted (d.rowIndex + 1)`);
if (!/y\s*:\s*boundaryY/.test(canvasCode))
  fail(`OcrCanvasPane: y: boundaryY assignment missing in i+1 override`);
else ok(`OcrCanvasPane: y: boundaryY assignment present in i+1 override`);

// upsert helper
if (!/upsertRowOverrideLocal/.test(canvasCode))
  fail(`OcrCanvasPane: upsertRowOverrideLocal helper missing`);
else ok(`OcrCanvasPane: upsertRowOverrideLocal helper present`);

// min height clamp
if (!/upperLimit/.test(canvasCode) || !/lowerLimit/.test(canvasCode))
  fail(`OcrCanvasPane: boundary clamp limits missing`);
else ok(`OcrCanvasPane: boundary clamp limits present`);

// Existing helpers still imported (TPL-12A/12C wiring intact)
if (!/materializeTableRowsWithOverrides/.test(canvasCode))
  fail(`OcrCanvasPane: materializeTableRowsWithOverrides usage missing (regression)`);
else ok(`OcrCanvasPane: materializeTableRowsWithOverrides still used`);
if (!/MIN_ROW_HEIGHT/.test(canvasCode))
  fail(`OcrCanvasPane: MIN_ROW_HEIGHT usage missing`);
else ok(`OcrCanvasPane: MIN_ROW_HEIGHT in use`);

// Move handler — rowOverrides.y shift
if (!/shiftedRowOverrides/.test(canvasCode))
  fail(`OcrCanvasPane: move handler does not shift rowOverrides (TPL-12G)`);
else ok(`OcrCanvasPane: move handler shifts rowOverrides`);
if (!/ov\.y\s*\+\s*dyEff/.test(canvasCode))
  fail(`OcrCanvasPane: move handler missing ov.y + dyEff shift expression`);
else ok(`OcrCanvasPane: move handler shifts ov.y by dyEff`);

// Existing rowTemplate / colGuide flows preserved
if (!/drawRowTemplate/.test(canvasCode))
  fail(`OcrCanvasPane lost drawRowTemplate flow (regression)`);
else ok(`OcrCanvasPane: drawRowTemplate flow preserved`);

// ---------------------------------------------------------------------------
// 2. Files outside scope: must NOT have TPL-12G markers
// ---------------------------------------------------------------------------
const TPL12G_ALLOW = new Set([OCR_CANVAS_PANE]);
for (const [label, p] of [
  ["TemplateAnnotator.tsx", TEMPLATE_ANNOTATOR],
  ["TemplateRightPanel.tsx", TEMPLATE_RIGHT_PANEL],
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
  if (TPL12G_ALLOW.has(p)) continue;
  const codeOnly = stripComments(readSafe(p) ?? "");
  if (/rowTopY|nextBottomY|hasNextRow|upsertRowOverrideLocal|applyRowBoundaryDragFrame|setRowBoundaryDrag/.test(codeOnly))
    fail(`${label} carries TPL-12G drag symbols (out of scope)`);
  else ok(`${label}: no TPL-12G drag symbols (out of scope)`);
}

// Backend / templates.json: still no rowOverrides
if (existsSync(BACKEND_MAIN)) {
  const py = readSafe(BACKEND_MAIN) ?? "";
  if (/rowOverrides/.test(py))
    fail(`ocr-server/main.py references rowOverrides — backend contract changed`);
  else ok(`ocr-server/main.py: rowOverrides not consumed`);
}
if (existsSync(TEMPLATES_JSON)) {
  if (/rowOverrides/.test(readSafe(TEMPLATES_JSON) ?? ""))
    note(`templates.json contains rowOverrides — expected after user-saved TPL-12 templates (phase-aware NOTE)`);
  else ok(`templates.json: no rowOverrides`);
}
if (existsSync(TEST_WORKSPACE)) {
  const tw = stripComments(readSafe(TEST_WORKSPACE) ?? "");
  if (/rowOverrides|rowAdjust|applyRowBoundaryDragFrame/.test(tw))
    fail(`TestWorkspace.tsx carries TPL-12 symbols (forbidden)`);
  else ok(`TestWorkspace.tsx: no TPL-12 symbols`);
}

// ---------------------------------------------------------------------------
// 3. src/lib absent + @/lib imports = 0
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
// 4. Runtime smoke — simulate local boundary adjust via materialize helper
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
const { materializeTableRowsWithOverrides, MIN_ROW_HEIGHT } = helperMod;
expect(typeof materializeTableRowsWithOverrides === "function", `materializeTableRowsWithOverrides is function`);

const area = { x: 60, y: 0, width: 1000, height: 500 };

// ── SMOKE 1: local adjust — drag boundary 0/1 from 50 to 60 ───────────────
{
  const baseRows = [
    { x: 60, y: 0,   width: 1000, height: 50 },
    { x: 60, y: 50,  width: 1000, height: 50 },
    { x: 60, y: 100, width: 1000, height: 50 },
  ];
  // Override emitted by local adjust:
  //   row 0: height = boundaryY - 0 = 60
  //   row 1: y = 60, height = nextBottom(100) - 60 = 40
  const overrides = [
    { rowIndex: 0, height: 60 },
    { rowIndex: 1, y: 60, height: 40 },
  ];
  const out = materializeTableRowsWithOverrides(baseRows, overrides, area);
  expect(out[0].y === 0 && out[0].height === 60, "case1 local: row 0 height = 60");
  expect(out[1].y === 60 && out[1].height === 40, "case1 local: row 1 y=60, height=40");
  expect(out[2].y === 100 && out[2].height === 50,
    "case1 local: row 2 y=100 unchanged (local adjust did NOT shift it down)");
}

// ── SMOKE 2: min height clamp ─────────────────────────────────────────────
// Caller clamps boundaryY to [rowTopY + MIN, nextBottom - MIN]. Verify that
// the resulting override pair satisfies the helper's MIN_ROW_HEIGHT filter.
{
  // Simulate boundary clamped exactly to rowTopY + MIN (= 4) and nextBottom - MIN (= 96).
  const baseRows = [
    { x: 60, y: 0,   width: 1000, height: 50 },
    { x: 60, y: 50,  width: 1000, height: 50 },
    { x: 60, y: 100, width: 1000, height: 50 },
  ];
  for (const boundaryY of [MIN_ROW_HEIGHT, 100 - MIN_ROW_HEIGHT]) {
    const upper = boundaryY - 0;
    const lower = 100 - boundaryY;
    const overrides = [
      { rowIndex: 0, height: upper },
      { rowIndex: 1, y: boundaryY, height: lower },
    ];
    const out = materializeTableRowsWithOverrides(baseRows, overrides, area);
    if (out[0].height < MIN_ROW_HEIGHT) fail(`case2 min: row 0 height < MIN @ boundaryY=${boundaryY}`);
    if (out[1].height < MIN_ROW_HEIGHT) fail(`case2 min: row 1 height < MIN @ boundaryY=${boundaryY}`);
    if (out[2].y !== 100) fail(`case2 min: row 2 y shifted @ boundaryY=${boundaryY}: ${out[2].y}`);
  }
  ok(`case2 min: boundary at MIN clamp limits keeps both rows >= MIN and row 2 unchanged`);
}

// ── SMOKE 3: last row boundary — height-only, no row i+1 override ─────────
{
  const baseRows = [
    { x: 60, y: 0,   width: 1000, height: 50 },
    { x: 60, y: 50,  width: 1000, height: 50 },
    { x: 60, y: 100, width: 1000, height: 50 },  // last row in this materialization
  ];
  // Local adjust on last row's bottom: only row 2 height changes (no row 3 to update).
  // The drag handler clamps boundaryY to areaBottom (500). Pick boundaryY=120 → row 2 height=20.
  const overrides = [
    { rowIndex: 2, height: 20 },
  ];
  const out = materializeTableRowsWithOverrides(baseRows, overrides, area);
  expect(out[0].y === 0 && out[0].height === 50, "case3 last: row 0 unchanged");
  expect(out[1].y === 50 && out[1].height === 50, "case3 last: row 1 unchanged");
  expect(out[2].y === 100 && out[2].height === 20, "case3 last: row 2 height=20");
  // Now try a larger drag that pushes row 2 to area bottom (height = 400).
  const out2 = materializeTableRowsWithOverrides(baseRows, [{ rowIndex: 2, height: 400 }], area);
  expect(out2[2].y + out2[2].height <= area.y + area.height + 1e-6,
    "case3 last: row 2 still within area when stretched");
}

// ── SMOKE 4: move y override shift — mirror move handler math ─────────────
// Simulate region.y change of dy=20: every override with finite y should
// shift by dy; height-only overrides untouched.
{
  const before = [
    { rowIndex: 0, height: 60 },
    { rowIndex: 1, y: 60, height: 40 },
    { rowIndex: 3, y: 250, height: 80, locked: true },
  ];
  const dy = 20;
  const shifted = before.map((ov) =>
    ov && typeof ov.y === "number" && Number.isFinite(ov.y)
      ? { ...ov, y: ov.y + dy }
      : ov,
  );
  expect(shifted[0].height === 60 && !("y" in shifted[0]),
    "case4 move: height-only override untouched");
  expect(shifted[1].y === 80 && shifted[1].height === 40,
    "case4 move: y override shifted by dy=20");
  expect(shifted[2].y === 270 && shifted[2].height === 80 && shifted[2].locked === true,
    "case4 move: locked + y override shifted, locked preserved");
}

// ── SMOKE 5: mutation guard ───────────────────────────────────────────────
{
  const baseRows = [
    { x: 60, y: 0,   width: 1000, height: 50 },
    { x: 60, y: 50,  width: 1000, height: 50 },
  ];
  const overrides = [
    { rowIndex: 0, height: 60 },
    { rowIndex: 1, y: 60, height: 40 },
  ];
  const baseSnap = JSON.stringify(baseRows);
  const ovSnap = JSON.stringify(overrides);
  materializeTableRowsWithOverrides(baseRows, overrides, area);
  materializeTableRowsWithOverrides(baseRows, overrides, area);
  expect(JSON.stringify(baseRows) === baseSnap, "case5 mutation: baseRows unchanged");
  expect(JSON.stringify(overrides) === ovSnap, "case5 mutation: overrides unchanged");
}

// ── SMOKE 6: cascade preservation across multi-row table ──────────────────
// Confirms the local-adjust math also works for a longer table: drag
// boundary 2/3 in a 5-row table should leave rows 4 and 5 (indices 3+1 onwards)
// at their original y.
{
  const baseRows = [
    { x: 60, y: 0,   width: 1000, height: 50 },
    { x: 60, y: 50,  width: 1000, height: 50 },
    { x: 60, y: 100, width: 1000, height: 50 },
    { x: 60, y: 150, width: 1000, height: 50 },
    { x: 60, y: 200, width: 1000, height: 50 },
  ];
  // Drag boundary 2/3 from y=150 to y=170. Row 2 height becomes 70, row 3 y=170 height=30.
  const overrides = [
    { rowIndex: 2, height: 70 },
    { rowIndex: 3, y: 170, height: 30 },
  ];
  const out = materializeTableRowsWithOverrides(baseRows, overrides, area);
  expect(out[0].y === 0 && out[0].height === 50, "case6 multi: row 0 unchanged");
  expect(out[1].y === 50 && out[1].height === 50, "case6 multi: row 1 unchanged");
  expect(out[2].y === 100 && out[2].height === 70, "case6 multi: row 2 height=70");
  expect(out[3].y === 170 && out[3].height === 30, "case6 multi: row 3 y=170 height=30");
  expect(out[4].y === 200 && out[4].height === 50,
    "case6 multi: row 4 y=200 unchanged (local adjust did not shift it)");
}

// ---------------------------------------------------------------------------
// 5. New-file scope check
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
