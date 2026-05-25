#!/usr/bin/env node
// TPL-12B-ROW-OVERRIDE-SAVE-LOAD
// Static + runtime smoke. Verifies buildTemplateExportPayload folds
// rowOverrides into materialized rows AND preserves rowOverrides as a
// separate key — without touching UI, types, helper, or backend.
//
// Tag on success: [ROW_OVERRIDE_SAVE_LOAD_TPL12B] PASS

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
const TAG = "[ROW_OVERRIDE_SAVE_LOAD_TPL12B]";

// Node 24 strip-types — register a small loader so `.ts` siblings imported
// via bare relative paths resolve at runtime (same pattern as TPL-8B/8D/8F/10/12A).
const LOADER_DIR = mkdtempSync(join(tmpdir(), "tpl12b-loader-"));
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
const PAYLOAD_BUILDER = resolve(ROOT, "src/components/template/utils/buildTemplateExportPayload.ts");
const OCR_TABLE_REGION = resolve(ROOT, "src/common/utils/ocrTableRegion.ts");
const TYPES_OCR = resolve(ROOT, "src/common/types/ocr.ts");
const OCR_CANVAS_OPS = resolve(ROOT, "src/common/utils/ocrCanvasOps.ts");
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
const FIXTURE_DIR = resolve(ROOT, "tmp/fixtures/template_table_row_overrides");

// ---------------------------------------------------------------------------
// 1. buildTemplateExportPayload — required edits
// ---------------------------------------------------------------------------
const payloadSrc = readSafe(PAYLOAD_BUILDER) ?? "";
const payloadCode = stripComments(payloadSrc);

if (!/from\s+["'][^"']*ocrTableRegion["']/.test(payloadCode))
  fail(`buildTemplateExportPayload does not import from ocrTableRegion`);
else ok(`buildTemplateExportPayload imports from ocrTableRegion`);

if (!/materializeTableRowsWithOverrides/.test(payloadCode))
  fail(`buildTemplateExportPayload does not call materializeTableRowsWithOverrides`);
else ok(`buildTemplateExportPayload references materializeTableRowsWithOverrides`);

if (!/rowOverrides/.test(payloadCode))
  fail(`buildTemplateExportPayload does not handle rowOverrides`);
else ok(`buildTemplateExportPayload handles rowOverrides`);

// Backward-compat phrase: rowOverrides key only present when input had one.
// We look for the spread guard `...(hasRowOverrides ? { rowOverrides: ... } : {})`.
if (!/hasRowOverrides/.test(payloadCode))
  fail(`buildTemplateExportPayload missing legacy guard (hasRowOverrides marker)`);
else ok(`buildTemplateExportPayload guards legacy output via hasRowOverrides`);

// ---------------------------------------------------------------------------
// 2. Untouched-by-TPL-12B files (other phases may have edited them — we only
//    require the file to exist and to not have introduced rowOverrides text
//    in operational code outside the two allow-listed paths from TPL-12A).
// ---------------------------------------------------------------------------
const REQUIRED_FILES = [
  ["OcrCanvasPane.tsx", OCR_CANVAS_PANE],
  ["ocrCanvasOps.ts", OCR_CANVAS_OPS],
  ["ocrTableRegion.ts", OCR_TABLE_REGION],
  ["ocr.ts (types)", TYPES_OCR],
  ["TemplateRightPanel.tsx", TEMPLATE_RIGHT_PANEL],
  ["TemplateAnnotator.tsx", TEMPLATE_ANNOTATOR],
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

// rowOverrides symbol must remain confined to TPL-12A's two files + TPL-12B's
// payload builder + TPL-12C's three UI files. Every other operational file
// must be free of the symbol.
const TPL12_ALLOW = new Set([
  TYPES_OCR,
  OCR_TABLE_REGION,
  PAYLOAD_BUILDER,
  OCR_CANVAS_PANE,        // TPL-12C
  TEMPLATE_ANNOTATOR,     // TPL-12C
  TEMPLATE_RIGHT_PANEL,   // TPL-12C
]);
for (const [label, p] of [
  ["OcrCanvasPane.tsx", OCR_CANVAS_PANE],
  ["TemplateRightPanel.tsx", TEMPLATE_RIGHT_PANEL],
  ["TemplateAnnotator.tsx", TEMPLATE_ANNOTATOR],
  ["tableResultViewModel.ts", VIEWMODEL_HELPER],
  ["OcrResultPanel.tsx", OCR_RESULT_PANEL],
  ["RunOcrWorkspace.tsx", RUNOCR_WORKSPACE],
  ["cleanJsonBuilder.ts", CLEAN_JSON],
  ["markdownReportBuilder.ts", MARKDOWN_REPORT],
  ["UnstructuredBuilder.tsx", UNSTRUCTURED_BUILDER],
  ["unstructuredDefinition.ts", UNSTRUCTURED_DEF],
]) {
  const codeOnly = stripComments(readSafe(p) ?? "");
  if (TPL12_ALLOW.has(p)) {
    if (/rowOverrides|materializeTableRowsWithOverrides|TableRowOverride/.test(codeOnly))
      note(`${label}: rowOverride symbol present (allowed — TPL-12C shipped)`);
    else ok(`${label}: no rowOverride symbol yet (TPL-12C not shipped)`);
    continue;
  }
  if (/rowOverrides|materializeTableRowsWithOverrides|TableRowOverride/.test(codeOnly))
    fail(`${label} references rowOverride symbols (out of TPL-12B/12C allow-list)`);
  else ok(`${label}: no rowOverride symbols (out of scope)`);
}

if (existsSync(BACKEND_MAIN)) {
  if (/rowOverrides/.test(readSafe(BACKEND_MAIN) ?? ""))
    fail(`ocr-server/main.py references rowOverrides — backend contract change forbidden`);
  else ok(`ocr-server/main.py: no rowOverrides (backend untouched)`);
}
if (existsSync(TEMPLATES_JSON)) {
  if (/rowOverrides/.test(readSafe(TEMPLATES_JSON) ?? ""))
    note(`templates.json carries rowOverrides — expected after user-saved TPL-12 templates (phase-aware NOTE)`);
  else ok(`templates.json: no rowOverrides (fixture untouched)`);
}

// ---------------------------------------------------------------------------
// 3. Fixture dir + count + parseability
// ---------------------------------------------------------------------------
if (!existsSync(FIXTURE_DIR)) fail(`fixture dir missing: ${relative(ROOT, FIXTURE_DIR)}`);
else ok(`fixture dir present`);

const fixtureFiles = (existsSync(FIXTURE_DIR) ? readdirSync(FIXTURE_DIR) : [])
  .filter((n) => n.endsWith(".json"))
  .sort();
if (fixtureFiles.length < 6) fail(`expected ≥6 fixtures, found ${fixtureFiles.length}`);
else ok(`fixtures found: ${fixtureFiles.length}`);

for (const name of [
  "legacy_no_row_overrides.json",
  "single_height_override.json",
  "single_y_override.json",
  "y_and_height_override.json",
  "invalid_overrides.json",
  "area_clamp_trailing_trim.json",
  "full_table_props_with_row_overrides.json",
]) {
  if (!existsSync(resolve(FIXTURE_DIR, name)))
    fail(`required fixture missing: ${name}`);
  else ok(`fixture present: ${name}`);
}

const fixtures = {};
for (const f of fixtureFiles) {
  const p = resolve(FIXTURE_DIR, f);
  try {
    fixtures[f] = JSON.parse(readFileSync(p, "utf8"));
    ok(`fixture parse: ${f}`);
  } catch (err) {
    fail(`fixture parse failed: ${f} (${err?.message ?? err})`);
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
// 5. Runtime smoke — import buildExportPayload + materialize helper
// ---------------------------------------------------------------------------
let payloadMod = null, helperMod = null;
try {
  payloadMod = await import(pathToFileURL(PAYLOAD_BUILDER).href);
  ok(`buildTemplateExportPayload runtime import succeeded`);
} catch (err) {
  fail(`buildTemplateExportPayload runtime import failed: ${err?.message ?? err}`);
}
try {
  helperMod = await import(pathToFileURL(OCR_TABLE_REGION).href);
  ok(`ocrTableRegion runtime import succeeded`);
} catch (err) {
  fail(`ocrTableRegion runtime import failed: ${err?.message ?? err}`);
}
if (!payloadMod || !helperMod) {
  console.error(`${TAG} FAIL aborting — imports failed`);
  console.error(`${TAG} FAIL count=${failures.length}`);
  process.exit(1);
}
const { buildExportPayload } = payloadMod;
const { materializeTableRowsWithOverrides } = helperMod;
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

function eqRect(a, b) {
  return a && b && a.x === b.x && a.y === b.y && a.width === b.width && a.height === b.height;
}

// ── CASE 1: legacy_no_row_overrides — byte-compat ─────────────────────────
{
  const fx = fixtures["legacy_no_row_overrides.json"];
  const snap = JSON.parse(JSON.stringify(fx));
  const out = runFixture("legacy_no_row_overrides.json");
  expect(JSON.stringify(fx) === JSON.stringify(snap),
    "case1 legacy: input fixture not mutated");
  const t = out.regions[0].table;
  expect(t && Array.isArray(t.rows) && t.rows.length === 4,
    "case1 legacy: 4 rows preserved");
  expect(!Object.prototype.hasOwnProperty.call(t, "rowOverrides"),
    "case1 legacy: rowOverrides key NOT added to saved table");
  const inputRows = fx.regions[0].table.rows;
  for (let i = 0; i < inputRows.length; i++) {
    if (!eqRect(t.rows[i], inputRows[i])) fail(`case1 legacy: rows[${i}] differs from input`);
  }
  ok(`case1 legacy: saved rows byte-identical to input rows`);
}

// ── CASE 2: single_height_override ────────────────────────────────────────
{
  const fx = fixtures["single_height_override.json"];
  const snap = JSON.parse(JSON.stringify(fx));
  const out = runFixture("single_height_override.json");
  expect(JSON.stringify(fx) === JSON.stringify(snap),
    "case2 height: input not mutated");
  const t = out.regions[0].table;
  expect(Array.isArray(t.rows) && t.rows.length === 3, "case2 height: 3 rows");
  expect(t.rows[0].y === 480 && t.rows[0].height === 60,
    "case2 height: row[0] untouched");
  expect(t.rows[1].y === 540 && t.rows[1].height === 80,
    "case2 height: row[1] keeps base y, height=80");
  expect(t.rows[2].y === 620 && t.rows[2].height === 60,
    "case2 height: row[2] cascades to y=620, height=60");
  expect(Array.isArray(t.rowOverrides)
    && t.rowOverrides.length === 1
    && t.rowOverrides[0].rowIndex === 1
    && t.rowOverrides[0].height === 80,
    "case2 height: rowOverrides preserved verbatim");
}

// ── CASE 3: single_y_override ─────────────────────────────────────────────
{
  const out = runFixture("single_y_override.json");
  const t = out.regions[0].table;
  expect(t.rows[1].y === 555 && t.rows[1].height === 60,
    "case3 y: row[1] y=555, height=60");
  expect(t.rows[2].y === 615 && t.rows[2].height === 60,
    "case3 y: row[2] cascades to y=615");
  expect(Array.isArray(t.rowOverrides)
    && t.rowOverrides[0].rowIndex === 1
    && t.rowOverrides[0].y === 555,
    "case3 y: rowOverrides preserved");
}

// ── CASE 4: y_and_height_override ─────────────────────────────────────────
{
  const out = runFixture("y_and_height_override.json");
  const t = out.regions[0].table;
  expect(t.rows[1].y === 555 && t.rows[1].height === 90,
    "case4 y+h: row[1] y=555 height=90");
  expect(t.rows[2].y === 645 && t.rows[2].height === 60,
    "case4 y+h: row[2] cascades to y=645");
  // locked preserved on the rowOverrides entry
  expect(Array.isArray(t.rowOverrides)
    && t.rowOverrides[0].rowIndex === 1
    && t.rowOverrides[0].y === 555
    && t.rowOverrides[0].height === 90
    && t.rowOverrides[0].locked === true,
    "case4 y+h: rowOverrides preserved with locked=true");
}

// ── CASE 5: invalid_overrides ─────────────────────────────────────────────
{
  const fx = fixtures["invalid_overrides.json"];
  const out = runFixture("invalid_overrides.json");
  const t = out.regions[0].table;
  const inputRows = fx.regions[0].table.rows;
  expect(t.rows.length === inputRows.length,
    "case5 invalid: row count unchanged (all malformed overrides ignored)");
  for (let i = 0; i < inputRows.length; i++) {
    if (!eqRect(t.rows[i], inputRows[i]))
      fail(`case5 invalid: rows[${i}] differs from base after ignoring bad overrides`);
  }
  ok(`case5 invalid: saved rows identical to base rows`);
  // rowOverrides itself is preserved (so user can fix it later) even though
  // every entry is invalid.
  expect(Array.isArray(t.rowOverrides) && t.rowOverrides.length === 5,
    "case5 invalid: rowOverrides preserved verbatim (5 entries, even invalid)");
}

// ── CASE 6: area_clamp_trailing_trim ──────────────────────────────────────
{
  const out = runFixture("area_clamp_trailing_trim.json");
  const t = out.regions[0].table;
  const areaTop = 100;
  const areaBottom = 100 + 200;  // 300
  for (const r of t.rows) {
    if (r.y < areaTop - 1) fail(`case6 clamp: row above area top: ${JSON.stringify(r)}`);
    if (r.y + r.height > areaBottom + 1) fail(`case6 clamp: row past area bottom: ${JSON.stringify(r)}`);
    if (r.height < 4) fail(`case6 clamp: row height < MIN_ROW_HEIGHT: ${JSON.stringify(r)}`);
  }
  ok(`case6 clamp: every saved row inside area & ≥ MIN_ROW_HEIGHT`);
  // row[0] height should be 160 (override applied)
  expect(t.rows[0].height === 160,
    "case6 clamp: row[0].height=160 (override applied)");
  // Some trailing rows trimmed (base had 4 rows; with row[0]=160 the rest
  // start at y=260 and must fit in remaining 40 of area → at most one fits)
  expect(t.rows.length < 4,
    "case6 clamp: trailing rows trimmed (less than base count)");
}

// ── CASE 7: full_table_props_with_row_overrides ───────────────────────────
{
  const fx = fixtures["full_table_props_with_row_overrides.json"];
  const out = runFixture("full_table_props_with_row_overrides.json");
  const t = out.regions[0].table;
  expect(t.mode === "repeat", "case7 full: mode preserved");
  expect(t.rowTemplate && t.rowTemplate.height === 60,
    "case7 full: rowTemplate preserved");
  expect(Array.isArray(t.colGuides) && t.colGuides.length === 3,
    "case7 full: colGuides preserved");
  expect(Array.isArray(t.stopKeywords) && t.stopKeywords.length === 3,
    "case7 full: stopKeywords preserved");
  expect(t.tableName === "품목표", "case7 full: tableName preserved");
  expect(Array.isArray(t.columns) && t.columns.length === 4,
    "case7 full: columns preserved");
  expect(Array.isArray(t.rowOverrides) && t.rowOverrides.length === 2,
    "case7 full: rowOverrides preserved (2 entries)");
  // rows materialized: row[1].height=90 (override), row[2] cascades from
  // (540+90)=630, row[3].y=720 (override).
  expect(t.rows[1].height === 90,
    "case7 full: row[1].height=90");
  expect(t.rows[2].y === 630,
    "case7 full: row[2].y=630 cascaded from row[1]");
  expect(t.rows[3].y === 720,
    "case7 full: row[3].y=720 from override");
  // mutation guard
  expect(JSON.stringify(fx) === JSON.stringify(JSON.parse(JSON.stringify(fx))),
    "case7 full: fixture parse stable");
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
    if (JSON.stringify(fx) !== snap)
      fail(`case8 mutation: fixture ${name} mutated by buildExportPayload`);
  }
  ok(`case8 mutation: all fixtures unchanged after 2 calls each`);
}

// ── CASE 9: backend-shape sanity — saved rows are Rect[] (no extra keys) ──
{
  const out = runFixture("full_table_props_with_row_overrides.json");
  const t = out.regions[0].table;
  for (const r of t.rows) {
    const keys = Object.keys(r).sort();
    if (keys.join(",") !== "height,width,x,y") {
      fail(`case9 shape: saved row has unexpected keys: ${keys.join(",")}`);
    }
  }
  ok(`case9 shape: saved rows are pure Rect[] (no rowOverride leakage)`);
}

// ---------------------------------------------------------------------------
// 6. New-file scope check
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
