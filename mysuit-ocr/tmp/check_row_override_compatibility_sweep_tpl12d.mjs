#!/usr/bin/env node
// TPL-12D-ROW-OVERRIDE-COMPATIBILITY-SWEEP
// Compatibility sweep for the full rowOverrides flow (TPL-12A→12B→12C).
// No production code is modified by this runner.
//
// Tag on success: [ROW_OVERRIDE_COMPATIBILITY_SWEEP_TPL12D] PASS

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
const TAG = "[ROW_OVERRIDE_COMPATIBILITY_SWEEP_TPL12D]";

// Node 24 strip-types — same pattern as TPL-8B/8D/8F/10/12A/12B.
const LOADER_DIR = mkdtempSync(join(tmpdir(), "tpl12d-loader-"));
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
function eqRect(a, b) {
  return a && b && a.x === b.x && a.y === b.y && a.width === b.width && a.height === b.height;
}

// ---------------------------------------------------------------------------
// Paths
// ---------------------------------------------------------------------------
const PAYLOAD_BUILDER = resolve(ROOT, "src/components/template/utils/buildTemplateExportPayload.ts");
const OCR_TABLE_REGION = resolve(ROOT, "src/common/utils/ocrTableRegion.ts");
const OCR_CANVAS_OPS = resolve(ROOT, "src/common/utils/ocrCanvasOps.ts");
const TYPES_OCR = resolve(ROOT, "src/common/types/ocr.ts");
const OCR_CANVAS_PANE = resolve(ROOT, "src/common/ui/OcrCanvasPane.tsx");
const TEMPLATE_RIGHT_PANEL = resolve(ROOT, "src/components/template/ui/TemplateRightPanel.tsx");
const TEMPLATE_ANNOTATOR = resolve(ROOT, "src/components/template/ui/TemplateAnnotator.tsx");
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
const FIXTURE_DIR = resolve(ROOT, "tmp/fixtures/template_table_row_overrides_compat");

// ---------------------------------------------------------------------------
// 1. Fixture dir + parse
// ---------------------------------------------------------------------------
if (!existsSync(FIXTURE_DIR)) fail(`fixture dir missing: ${relative(ROOT, FIXTURE_DIR)}`);
else ok(`fixture dir present`);

const fixtureFiles = (existsSync(FIXTURE_DIR) ? readdirSync(FIXTURE_DIR) : [])
  .filter((n) => n.endsWith(".json"))
  .sort();
if (fixtureFiles.length < 5) fail(`expected ≥5 fixtures, found ${fixtureFiles.length}`);
else ok(`fixtures found: ${fixtureFiles.length}`);

const REQUIRED_FIXTURES = [
  "legacy_template_no_overrides.json",
  "template_with_overrides_basic.json",
  "template_with_columns_and_overrides.json",
  "template_reset_overrides_expected.json",
  "template_clear_row_template_expected.json",
  "template_move_shift_policy.json",
  "template_resize_policy.json",
];
for (const name of REQUIRED_FIXTURES) {
  if (!existsSync(resolve(FIXTURE_DIR, name))) fail(`required fixture missing: ${name}`);
  else ok(`fixture present: ${name}`);
}

const fixtures = {};
for (const f of fixtureFiles) {
  try {
    fixtures[f] = JSON.parse(readFileSync(resolve(FIXTURE_DIR, f), "utf8"));
    ok(`fixture parse: ${f}`);
  } catch (err) {
    fail(`fixture parse failed: ${f} (${err?.message ?? err})`);
  }
}

// ---------------------------------------------------------------------------
// 2. Operational files unchanged-since-12C: existence + no rowOverrides drift
//    outside TPL-12A/B/C allow-list.
// ---------------------------------------------------------------------------
const TPL12_ALLOW = new Set([
  TYPES_OCR,                // TPL-12A
  OCR_TABLE_REGION,         // TPL-12A
  PAYLOAD_BUILDER,          // TPL-12B
  OCR_CANVAS_PANE,          // TPL-12C
  TEMPLATE_ANNOTATOR,       // TPL-12C
  TEMPLATE_RIGHT_PANEL,     // TPL-12C
]);
const REQUIRED_FILES = [
  ["OcrCanvasPane.tsx", OCR_CANVAS_PANE],
  ["TemplateRightPanel.tsx", TEMPLATE_RIGHT_PANEL],
  ["TemplateAnnotator.tsx", TEMPLATE_ANNOTATOR],
  ["buildTemplateExportPayload.ts", PAYLOAD_BUILDER],
  ["types/ocr.ts", TYPES_OCR],
  ["ocrTableRegion.ts", OCR_TABLE_REGION],
  ["ocrCanvasOps.ts", OCR_CANVAS_OPS],
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
  else ok(`present (expected): ${label}`);
}

for (const [label, p] of [
  ["tableResultViewModel.ts", VIEWMODEL_HELPER],
  ["OcrResultPanel.tsx", OCR_RESULT_PANEL],
  ["RunOcrWorkspace.tsx", RUNOCR_WORKSPACE],
  ["cleanJsonBuilder.ts", CLEAN_JSON],
  ["markdownReportBuilder.ts", MARKDOWN_REPORT],
  ["UnstructuredBuilder.tsx", UNSTRUCTURED_BUILDER],
  ["unstructuredDefinition.ts", UNSTRUCTURED_DEF],
  ["ocrCanvasOps.ts", OCR_CANVAS_OPS],
  ["TestWorkspace.tsx", TEST_WORKSPACE],
]) {
  if (TPL12_ALLOW.has(p)) continue;
  const codeOnly = stripComments(readSafe(p) ?? "");
  if (/rowOverrides|materializeTableRowsWithOverrides|TableRowOverride|rowAdjustTargetId/.test(codeOnly))
    fail(`${label} references rowOverride symbols (out of TPL-12 allow-list)`);
  else ok(`${label}: no rowOverride symbols (out of scope)`);
}

// ---------------------------------------------------------------------------
// 3. Source markers — confirm TPL-12A/B/C wiring still present
// ---------------------------------------------------------------------------
const typesSrc = readSafe(TYPES_OCR) ?? "";
if (!/export\s+type\s+TableRowOverride\b/.test(typesSrc))
  fail(`TableRowOverride type missing (TPL-12A regression)`);
else ok(`TableRowOverride type present (TPL-12A)`);
if (!/rowOverrides\?\s*:\s*TableRowOverride\[\]/.test(typesSrc))
  fail(`TableMeta.rowOverrides?: TableRowOverride[] missing (TPL-12A regression)`);
else ok(`TableMeta.rowOverrides? present (TPL-12A)`);

const helperSrc = readSafe(OCR_TABLE_REGION) ?? "";
if (!/export\s+function\s+materializeTableRowsWithOverrides\b/.test(helperSrc))
  fail(`materializeTableRowsWithOverrides export missing (TPL-12A regression)`);
else ok(`materializeTableRowsWithOverrides export present (TPL-12A)`);

const payloadSrc = readSafe(PAYLOAD_BUILDER) ?? "";
if (!/materializeTableRowsWithOverrides/.test(payloadSrc))
  fail(`buildTemplateExportPayload no longer uses materialize helper (TPL-12B regression)`);
else ok(`buildTemplateExportPayload uses materialize helper (TPL-12B)`);
if (!/hasRowOverrides/.test(payloadSrc))
  fail(`buildTemplateExportPayload missing legacy hasRowOverrides guard (TPL-12B regression)`);
else ok(`buildTemplateExportPayload hasRowOverrides guard present (TPL-12B)`);

const trpSrc = readSafe(TEMPLATE_RIGHT_PANEL) ?? "";
if (!/rowAdjustTargetId/.test(trpSrc))
  fail(`TemplateRightPanel: rowAdjustTargetId missing (TPL-12C regression)`);
else ok(`TemplateRightPanel: rowAdjustTargetId wired (TPL-12C)`);
if (!/행\s*개별\s*조정/.test(trpSrc))
  fail(`TemplateRightPanel: "행 개별 조정" UI label missing (TPL-12C regression)`);
else ok(`TemplateRightPanel: "행 개별 조정" UI present (TPL-12C)`);
if (!/clearRowOverrides/.test(trpSrc))
  fail(`TemplateRightPanel: clearRowOverrides helper missing (TPL-12C regression)`);
else ok(`TemplateRightPanel: clearRowOverrides helper present (TPL-12C)`);
// clearTableMeta also clears rowOverrides
if (!/function\s+clearTableMeta\b[\s\S]{0,800}rowOverrides\s*:\s*undefined/.test(trpSrc))
  fail(`TemplateRightPanel.clearTableMeta no longer clears rowOverrides (TPL-12C regression)`);
else ok(`clearTableMeta clears rowOverrides (TPL-12C)`);

const canvasSrc = readSafe(OCR_CANVAS_PANE) ?? "";
if (!/row-boundary-handle/.test(canvasSrc))
  fail(`OcrCanvasPane: row-boundary-handle missing (TPL-12C regression)`);
else ok(`OcrCanvasPane: row-boundary-handle marker present (TPL-12C)`);
if (!/materializeTableRowsWithOverrides/.test(canvasSrc))
  fail(`OcrCanvasPane: materializeTableRowsWithOverrides usage missing (TPL-12C regression)`);
else ok(`OcrCanvasPane: materializeTableRowsWithOverrides used for displayRows (TPL-12C)`);

const annSrc = readSafe(TEMPLATE_ANNOTATOR) ?? "";
if (!/const\s+\[\s*rowAdjustTargetId\s*,/.test(annSrc))
  fail(`TemplateAnnotator: rowAdjustTargetId state missing (TPL-12C regression)`);
else ok(`TemplateAnnotator: rowAdjustTargetId state present (TPL-12C)`);

// ---------------------------------------------------------------------------
// 4. Backend payload contract — main.py / templates.json untouched
// ---------------------------------------------------------------------------
if (existsSync(BACKEND_MAIN)) {
  const py = readSafe(BACKEND_MAIN) ?? "";
  if (/rowOverrides|rowAdjust/.test(py))
    fail(`ocr-server/main.py references rowOverrides/rowAdjust — backend contract changed`);
  else ok(`ocr-server/main.py: rowOverrides not consumed (backend contract preserved)`);
  // Re-confirm backend doesn't even read region.table.rows / rowTemplate.
  const pyCode = py
    .replace(/'''[\s\S]*?'''/g, "")
    .replace(/"""[\s\S]*?"""/g, "")
    .replace(/^[ \t]*#[^\n]*$/gm, "");
  const consumesRows = /\["rows"\]|\.get\(\s*["']rows["']\s*\)/.test(pyCode);
  const consumesRowTemplate = /\["rowTemplate"\]|\.get\(\s*["']rowTemplate["']/.test(pyCode);
  if (consumesRows) note(`backend reads region.table.rows (still safe — rows are pure Rect[])`);
  else ok(`backend does NOT read region.table.rows`);
  if (consumesRowTemplate) note(`backend reads region.table.rowTemplate (still safe — same as rows)`);
  else ok(`backend does NOT read region.table.rowTemplate`);
} else {
  note(`ocr-server/main.py not found — backend check skipped`);
}
if (existsSync(TEMPLATES_JSON)) {
  if (/rowOverrides/.test(readSafe(TEMPLATES_JSON) ?? ""))
    note(`templates.json contains rowOverrides — expected after user-saved TPL-12 templates (phase-aware NOTE)`);
  else ok(`templates.json: no rowOverrides (fixture untouched)`);
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
// 6. Runtime imports + round-trip / policy simulations
// ---------------------------------------------------------------------------
let payloadMod = null, helperMod = null;
try {
  payloadMod = await import(pathToFileURL(PAYLOAD_BUILDER).href);
  ok(`buildTemplateExportPayload runtime import succeeded`);
} catch (err) { fail(`buildTemplateExportPayload runtime import failed: ${err?.message ?? err}`); }
try {
  helperMod = await import(pathToFileURL(OCR_TABLE_REGION).href);
  ok(`ocrTableRegion runtime import succeeded`);
} catch (err) { fail(`ocrTableRegion runtime import failed: ${err?.message ?? err}`); }
if (!payloadMod || !helperMod) {
  console.error(`${TAG} FAIL aborting — imports failed`);
  console.error(`${TAG} FAIL count=${failures.length}`);
  process.exit(1);
}
const { buildExportPayload } = payloadMod;
const { materializeTableRowsWithOverrides, buildTableRows } = helperMod;
expect(typeof buildExportPayload === "function", `buildExportPayload is function`);
expect(typeof materializeTableRowsWithOverrides === "function", `materializeTableRowsWithOverrides is function`);

function runFixture(name) {
  const fx = fixtures[name];
  if (!fx) throw new Error(`fixture not loaded: ${name}`);
  return buildExportPayload({
    templateName: fx.templateName,
    loaded: fx.loaded,
    regions: fx.regions,
    documentType: fx.documentType,
  });
}

// ── CASE 1: legacy no overrides — byte-compat with input rows ─────────────
{
  const fx = fixtures["legacy_template_no_overrides.json"];
  const snap = JSON.stringify(fx);
  const out = runFixture("legacy_template_no_overrides.json");
  expect(JSON.stringify(fx) === snap, "case1 legacy: input not mutated");
  const t = out.regions[0].table;
  expect(!Object.prototype.hasOwnProperty.call(t, "rowOverrides"),
    "case1 legacy: rowOverrides key NOT added to saved table");
  expect(Array.isArray(t.rows) && t.rows.length === 4,
    "case1 legacy: 4 rows preserved");
  const input = fx.regions[0].table.rows;
  for (let i = 0; i < input.length; i++) {
    if (!eqRect(t.rows[i], input[i])) fail(`case1 legacy: rows[${i}] differs`);
  }
  ok(`case1 legacy: rows byte-identical to input (no override path)`);
  expect(Array.isArray(t.colGuides) && t.colGuides.length === 3,
    "case1 legacy: colGuides preserved");
}

// ── CASE 2: overrides round-trip — saved rows reflect overrides + idempotent ─
{
  const out = runFixture("template_with_overrides_basic.json");
  const t = out.regions[0].table;
  // Materialized rows: row[0] (60), row[1] override 80, row[2] cascade
  expect(t.rows[0].y === 480 && t.rows[0].height === 60,
    "case2 round-trip: row[0] preserved");
  expect(t.rows[1].y === 540 && t.rows[1].height === 80,
    "case2 round-trip: row[1] keeps base y, height=80");
  expect(t.rows[2].y === 620 && t.rows[2].height === 60,
    "case2 round-trip: row[2] cascade y=620");
  expect(Array.isArray(t.rowOverrides) && t.rowOverrides.length === 1
    && t.rowOverrides[0].rowIndex === 1 && t.rowOverrides[0].height === 80,
    "case2 round-trip: rowOverrides preserved");
  // Idempotency: feed the saved output as fresh input, export again.
  const out2 = buildExportPayload({
    templateName: out.templateName,
    loaded: { src: "x", fileName: "x", naturalWidth: 1200, naturalHeight: 1600 },
    regions: out.regions,
    documentType: out.documentType,
  });
  expect(JSON.stringify(out2.regions[0].table.rows) === JSON.stringify(t.rows),
    "case2 round-trip: second export produces identical rows (idempotent)");
  expect(JSON.stringify(out2.regions[0].table.rowOverrides) === JSON.stringify(t.rowOverrides),
    "case2 round-trip: second export preserves rowOverrides identically");
}

// ── CASE 3: columns + overrides coexist ───────────────────────────────────
{
  const out = runFixture("template_with_columns_and_overrides.json");
  const t = out.regions[0].table;
  expect(Array.isArray(t.columns) && t.columns.length === 4,
    "case3 mixed: 4 columns preserved");
  expect(Array.isArray(t.rowOverrides) && t.rowOverrides.length === 1
    && t.rowOverrides[0].rowIndex === 1 && t.rowOverrides[0].height === 90
    && t.rowOverrides[0].locked === true,
    "case3 mixed: rowOverrides preserved with locked");
  expect(t.tableName === "품목표", "case3 mixed: tableName preserved");
  expect(Array.isArray(t.stopKeywords) && t.stopKeywords.length === 3,
    "case3 mixed: stopKeywords preserved");
  expect(Array.isArray(t.colGuides) && t.colGuides.length === 3,
    "case3 mixed: colGuides preserved");
  // rows materialized: row[1].height=90, row[2].y = 540 + 90 = 630
  expect(t.rows[1].height === 90, "case3 mixed: row[1].height=90");
  expect(t.rows[2].y === 630, "case3 mixed: row[2].y=630 cascade");
}

// ── CASE 4: reset policy — simulate clearRowOverrides on the region ───────
{
  const fx = fixtures["template_reset_overrides_expected.json"];
  // Simulate TemplateRightPanel.clearRowOverrides: delete the rowOverrides key.
  const mutated = JSON.parse(JSON.stringify(fx));
  const t0 = mutated.regions[0].table;
  delete t0.rowOverrides;
  const out = buildExportPayload({
    templateName: mutated.templateName,
    loaded: mutated.loaded,
    regions: mutated.regions,
    documentType: mutated.documentType,
  });
  const t = out.regions[0].table;
  expect(!Object.prototype.hasOwnProperty.call(t, "rowOverrides"),
    "case4 reset: saved table has no rowOverrides key after clearRowOverrides");
  // rows preserved from input (no override to apply)
  const inputRows = fx.regions[0].table.rows;
  expect(t.rows.length === inputRows.length,
    "case4 reset: row count preserved");
  for (let i = 0; i < inputRows.length; i++) {
    if (!eqRect(t.rows[i], inputRows[i]))
      fail(`case4 reset: rows[${i}] differs from input — clearRowOverrides should NOT mutate rows`);
  }
  ok(`case4 reset: rows byte-identical to input after clearRowOverrides`);
}

// ── CASE 5: clear row template — rowTemplate/rows/rowOverrides all wiped ──
{
  const fx = fixtures["template_clear_row_template_expected.json"];
  // Simulate TemplateRightPanel.clearTableMeta:
  //   rowTemplate=undefined, rows=undefined, rowOverrides=undefined; mode preserved.
  const mutated = JSON.parse(JSON.stringify(fx));
  const t0 = mutated.regions[0].table;
  delete t0.rowTemplate;
  delete t0.rows;
  delete t0.rowOverrides;
  const out = buildExportPayload({
    templateName: mutated.templateName,
    loaded: mutated.loaded,
    regions: mutated.regions,
    documentType: mutated.documentType,
  });
  const t = out.regions[0].table;
  expect(t.rowTemplate === null, "case5 clearMeta: rowTemplate -> null in saved payload");
  expect(Array.isArray(t.rows) && t.rows.length === 0,
    "case5 clearMeta: rows -> [] in saved payload");
  expect(!Object.prototype.hasOwnProperty.call(t, "rowOverrides"),
    "case5 clearMeta: rowOverrides key not emitted");
  expect(Array.isArray(t.colGuides) && t.colGuides.length === 3,
    "case5 clearMeta: colGuides preserved (unaffected by clearTableMeta)");
}

// ── CASE 6: move policy — simulate region shift ───────────────────────────
// Current OcrCanvasPane move handler shifts rowTemplate + rows by (dx, dy)
// but does NOT touch rowOverrides (which is height-only in TPL-12C MVP).
// We mirror the handler here and verify the saved output stays consistent.
{
  const fx = fixtures["template_move_shift_policy.json"];
  const { dx, dy } = fx.moveDelta;
  const moved = JSON.parse(JSON.stringify(fx));
  const r = moved.regions[0];
  const shift = (rect) => ({
    x: rect.x + dx,
    y: rect.y + dy,
    width: rect.width,
    height: rect.height,
  });
  r.x += dx;
  r.y += dy;
  if (r.table.rowTemplate) r.table.rowTemplate = shift(r.table.rowTemplate);
  if (Array.isArray(r.table.rows)) r.table.rows = r.table.rows.map(shift);
  // rowOverrides is intentionally NOT shifted (height-only, no y component).
  const out = buildExportPayload({
    templateName: moved.templateName,
    loaded: moved.loaded,
    regions: moved.regions,
    documentType: moved.documentType,
  });
  const t = out.regions[0].table;
  expect(t.rows[0].x === 60 + dx && t.rows[0].y === 480 + dy,
    "case6 move: row[0] x/y shifted by delta");
  expect(t.rows[1].height === 80,
    "case6 move: row[1].height=80 (override still applied)");
  expect(t.rows[1].y === 540 + dy,
    "case6 move: row[1].y cascade matches new base + override");
  expect(t.rows[2].y === t.rows[1].y + t.rows[1].height,
    "case6 move: row[2].y cascades from row[1]");
  expect(Array.isArray(t.rowOverrides) && t.rowOverrides.length === 1
    && t.rowOverrides[0].rowIndex === 1 && t.rowOverrides[0].height === 80,
    "case6 move: rowOverrides height-only entry unchanged");
  note(`move policy: rowTemplate/rows shift by delta; rowOverrides untouched (height-only safe in TPL-12C MVP)`);
}

// ── CASE 7: resize policy — simulate region resize + canvas/export consistency ─
// Current OcrCanvasPane resize handler clamps rowTemplate to the new area
// and rebuilds rows = buildTableRows(area, rt) — equal-height — but leaves
// rowOverrides untouched. Canvas display + export re-materialize from those
// equal-height base rows + rowOverrides so the user still sees / saves the
// applied override.
{
  const fx = fixtures["template_resize_policy.json"];
  const newArea = fx.resizeArea;
  const resized = JSON.parse(JSON.stringify(fx));
  const r = resized.regions[0];
  r.x = newArea.x;
  r.y = newArea.y;
  r.width = newArea.width;
  r.height = newArea.height;
  // Mirror handler: clampRectToArea(rowTemplate, area) + buildTableRows(area, rt)
  const rt = r.table.rowTemplate; // assume in-area for fixture
  const baseRows = buildTableRows(newArea, rt);
  r.table.rowTemplate = rt;
  r.table.rows = baseRows;
  // rowOverrides unchanged.

  // The export builder re-materializes via materializeTableRowsWithOverrides,
  // so saved rows should reflect overrides on the NEW (smaller) base.
  const out = buildExportPayload({
    templateName: resized.templateName,
    loaded: resized.loaded,
    regions: resized.regions,
    documentType: resized.documentType,
  });
  const t = out.regions[0].table;
  expect(Array.isArray(t.rowOverrides) && t.rowOverrides.length === 1
    && t.rowOverrides[0].rowIndex === 1 && t.rowOverrides[0].height === 80,
    "case7 resize: rowOverrides preserved (resize does not wipe overrides)");
  // row[1] should still carry the override even after resize.
  expect(t.rows.length >= 2, "case7 resize: at least row[0..1] survived");
  expect(t.rows[1].height === 80, "case7 resize: row[1].height=80 (override re-applied on new base)");
  // Every emitted row must sit inside the new area.
  for (const row of t.rows) {
    if (row.y < newArea.y - 1e-6
        || row.y + row.height > newArea.y + newArea.height + 1e-6) {
      fail(`case7 resize: row out of bounds: ${JSON.stringify(row)} vs area ${JSON.stringify(newArea)}`);
    }
  }
  ok(`case7 resize: all saved rows inside new area; trailing trim/clamp applied as needed`);
  note(`resize policy: rows reset by buildTableRows at resize time; rowOverrides + export materialization re-apply correctly. height-only invariant keeps risk LOW.`);
}

// ── CASE 8: cross-fixture mutation guard ──────────────────────────────────
{
  for (const name of fixtureFiles) {
    const fx = fixtures[name];
    const snap = JSON.stringify(fx);
    buildExportPayload({
      templateName: fx.templateName,
      loaded: fx.loaded,
      regions: fx.regions,
      documentType: fx.documentType,
    });
    buildExportPayload({
      templateName: fx.templateName,
      loaded: fx.loaded,
      regions: fx.regions,
      documentType: fx.documentType,
    });
    if (JSON.stringify(fx) !== snap) {
      fail(`case8 mutation: fixture ${name} mutated by buildExportPayload`);
    }
  }
  ok(`case8 mutation: all fixtures unchanged after 2 calls each`);
}

// ── CASE 9: saved rows are pure Rect[] (no rowOverride metadata leakage) ──
{
  for (const name of [
    "template_with_overrides_basic.json",
    "template_with_columns_and_overrides.json",
    "template_move_shift_policy.json",
    "template_resize_policy.json",
  ]) {
    const out = runFixture(name);
    const t = out.regions[0].table;
    for (const row of t.rows) {
      const keys = Object.keys(row).sort();
      if (keys.join(",") !== "height,width,x,y") {
        fail(`case9 shape: ${name} row has unexpected keys: ${keys.join(",")}`);
      }
    }
  }
  ok(`case9 shape: every saved row is a pure Rect (backend contract preserved)`);
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
