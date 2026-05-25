#!/usr/bin/env node
// TPL-12A-ROW-OVERRIDE-TYPES-AND-HELPERS
// Static + runtime smoke. Verifies the new TableRowOverride type and the
// materializeTableRowsWithOverrides pure helper. UI / payload / backend are
// not touched at this phase.
//
// Tag on success: [ROW_OVERRIDE_TYPES_HELPERS_TPL12A] PASS

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
const TAG = "[ROW_OVERRIDE_TYPES_HELPERS_TPL12A]";

// Node 24 strip-types — register a small loader so `.ts` siblings imported
// via bare relative paths resolve at runtime (same pattern as TPL-8B/8D/8F/10).
const LOADER_DIR = mkdtempSync(join(tmpdir(), "tpl12a-loader-"));
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
const TYPES_OCR = resolve(ROOT, "src/common/types/ocr.ts");
const TABLE_REGION = resolve(ROOT, "src/common/utils/ocrTableRegion.ts");
const OCR_CANVAS_OPS = resolve(ROOT, "src/common/utils/ocrCanvasOps.ts");
const OCR_CANVAS_PANE = resolve(ROOT, "src/common/ui/OcrCanvasPane.tsx");
const TEMPLATE_RIGHT_PANEL = resolve(ROOT, "src/components/template/ui/TemplateRightPanel.tsx");
const TEMPLATE_ANNOTATOR = resolve(ROOT, "src/components/template/ui/TemplateAnnotator.tsx");
const PAYLOAD_BUILDER = resolve(ROOT, "src/components/template/utils/buildTemplateExportPayload.ts");
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
// 1. types/ocr.ts — TableRowOverride + TableMeta.rowOverrides? present
// ---------------------------------------------------------------------------
const typesSrc = readSafe(TYPES_OCR) ?? "";
const typesCode = stripComments(typesSrc);

if (!/export\s+type\s+TableRowOverride\s*=\s*\{[\s\S]*?rowIndex\s*:\s*number/.test(typesCode))
  fail(`TableRowOverride export with required rowIndex: number missing`);
else ok(`TableRowOverride type with rowIndex: number present`);
if (!/y\s*\?\s*:\s*number/.test(typesCode))
  fail(`TableRowOverride.y?: number not present`);
else ok(`TableRowOverride.y?: number present`);
if (!/height\s*\?\s*:\s*number/.test(typesCode))
  fail(`TableRowOverride.height?: number not present`);
else ok(`TableRowOverride.height?: number present`);
if (!/locked\s*\?\s*:\s*boolean/.test(typesCode))
  fail(`TableRowOverride.locked?: boolean not present`);
else ok(`TableRowOverride.locked?: boolean present`);
if (!/rowOverrides\s*\?\s*:\s*TableRowOverride\[\]/.test(typesCode))
  fail(`TableMeta.rowOverrides?: TableRowOverride[] not present`);
else ok(`TableMeta.rowOverrides?: TableRowOverride[] present`);

// Existing fields preserved
for (const re of [
  /mode\s*\?\s*:\s*"repeat"\s*\|\s*"auto"/,
  /rowTemplate\s*\?\s*:\s*Rect/,
  /rows\s*\?\s*:\s*Rect\[\]/,
  /colGuides\s*\?\s*:\s*number\[\]/,
  /columns\s*\?\s*:\s*TableColumnDef\[\]/,
]) {
  if (!re.test(typesCode)) fail(`TableMeta field regressed: ${re}`);
  else ok(`TableMeta field preserved: ${re.source}`);
}

// ---------------------------------------------------------------------------
// 2. ocrTableRegion.ts — buildTableRows preserved + new helper present
// ---------------------------------------------------------------------------
const helperSrc = readSafe(TABLE_REGION) ?? "";
const helperCode = stripComments(helperSrc);

if (!/export\s+function\s+buildTableRows\s*\(/.test(helperCode))
  fail(`buildTableRows export missing (regression)`);
else ok(`buildTableRows export preserved`);

if (!/export\s+function\s+materializeTableRowsWithOverrides\s*\(/.test(helperCode))
  fail(`materializeTableRowsWithOverrides export missing`);
else ok(`materializeTableRowsWithOverrides export present`);

if (!/MIN_ROW_HEIGHT/.test(helperCode))
  fail(`MIN_ROW_HEIGHT constant missing`);
else ok(`MIN_ROW_HEIGHT constant present`);

// Pure helper: no React/DOM/storage/fetch
const forbidden = [
  /from\s+["']react/,
  /\bwindow\s*\./,
  /\bdocument\s*\./,
  /\blocalStorage\b/,
  /\bsessionStorage\b/,
  /\bfetch\s*\(/,
];
let pureOk = true;
for (const re of forbidden) {
  if (re.test(helperCode)) { fail(`forbidden in helper: ${re}`); pureOk = false; }
}
if (pureOk) ok(`helper remains pure (no React/DOM/storage/fetch)`);

// ---------------------------------------------------------------------------
// 3. Untouched files (existence only — we don't compare bodies, since other
//    phases already modified some of these)
// ---------------------------------------------------------------------------
const untouched = [
  ["OcrCanvasPane.tsx", OCR_CANVAS_PANE],
  ["ocrCanvasOps.ts", OCR_CANVAS_OPS],
  ["TemplateRightPanel.tsx", TEMPLATE_RIGHT_PANEL],
  ["TemplateAnnotator.tsx", TEMPLATE_ANNOTATOR],
  ["buildTemplateExportPayload.ts", PAYLOAD_BUILDER],
  ["tableResultViewModel.ts", VIEWMODEL_HELPER],
  ["OcrResultPanel.tsx", OCR_RESULT_PANEL],
  ["RunOcrWorkspace.tsx", RUNOCR_WORKSPACE],
  ["cleanJsonBuilder.ts", CLEAN_JSON],
  ["markdownReportBuilder.ts", MARKDOWN_REPORT],
  ["UnstructuredBuilder.tsx", UNSTRUCTURED_BUILDER],
  ["unstructuredDefinition.ts", UNSTRUCTURED_DEF],
  ["TestWorkspace.tsx", TEST_WORKSPACE],
];
for (const [label, p] of untouched) {
  if (!existsSync(p)) fail(`expected file missing: ${label}`);
  else ok(`present (expected): ${label}`);
}

// Out-of-scope files for TPL-12A. (TPL-12B legitimately adds rowOverride
// handling to buildTemplateExportPayload — phase-aware allow-list when that
// marker is present.)
for (const [label, p] of [
  ["OcrCanvasPane.tsx", OCR_CANVAS_PANE],
  ["TemplateRightPanel.tsx", TEMPLATE_RIGHT_PANEL],
  ["TemplateAnnotator.tsx", TEMPLATE_ANNOTATOR],
  ["buildTemplateExportPayload.ts", PAYLOAD_BUILDER],
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
  // TPL-12B legitimately added rowOverrides handling to buildTemplateExportPayload.
  // TPL-12C legitimately added rowOverrides UI to OcrCanvasPane / TemplateAnnotator /
  // TemplateRightPanel. Phase-aware allow-list those paths when the symbol is present.
  const _PHASE_LATER_ALLOW = new Set([
    PAYLOAD_BUILDER,        // TPL-12B
    OCR_CANVAS_PANE,        // TPL-12C
    TEMPLATE_ANNOTATOR,     // TPL-12C
    TEMPLATE_RIGHT_PANEL,   // TPL-12C
  ]);
  if (_PHASE_LATER_ALLOW.has(p)) {
    if (hasSymbol) note(`${label}: rowOverride symbol present (allowed — TPL-12B/12C shipped)`);
    else ok(`${label}: no rowOverride symbol yet (TPL-12B/12C not shipped)`);
    continue;
  }
  if (hasSymbol)
    fail(`${label} references rowOverrides/materialize/TableRowOverride (TPL-12A out of scope)`);
  else ok(`${label}: no rowOverride symbols (out of scope)`);
}

// Backend / templates.json must not yet carry rowOverrides
if (existsSync(BACKEND_MAIN)) {
  const py = readSafe(BACKEND_MAIN) ?? "";
  if (/rowOverrides/.test(py))
    fail(`ocr-server/main.py references rowOverrides — backend contract change forbidden`);
  else ok(`ocr-server/main.py: no rowOverrides (backend untouched)`);
} else note(`ocr-server/main.py absent — backend untouched check skipped`);
if (existsSync(TEMPLATES_JSON)) {
  if (/rowOverrides/.test(readSafe(TEMPLATES_JSON) ?? ""))
    note(`templates.json contains rowOverrides — expected after user-saved TPL-12 templates (phase-aware NOTE)`);
  else ok(`templates.json: no rowOverrides (fixture untouched)`);
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
// 5. Runtime smoke
// ---------------------------------------------------------------------------
let mod = null;
try {
  mod = await import(pathToFileURL(TABLE_REGION).href);
  ok(`ocrTableRegion runtime import succeeded`);
} catch (err) {
  fail(`ocrTableRegion runtime import failed: ${err?.message ?? err}`);
}
if (!mod) {
  console.error(`${TAG} FAIL aborting smoke — imports failed`);
  console.error(`${TAG} FAIL count=${failures.length}`);
  process.exit(1);
}
const { buildTableRows, materializeTableRowsWithOverrides, MIN_ROW_HEIGHT } = mod;
expect(typeof buildTableRows === "function", `buildTableRows is function`);
expect(typeof materializeTableRowsWithOverrides === "function", `materializeTableRowsWithOverrides is function`);
expect(typeof MIN_ROW_HEIGHT === "number" && MIN_ROW_HEIGHT >= 1, `MIN_ROW_HEIGHT is positive number`);

const area = { x: 60, y: 100, width: 1000, height: 600 };
const rowTemplate = { x: 60, y: 100, width: 1000, height: 50 };
const baseRows = buildTableRows(area, rowTemplate);
expect(baseRows.length === 12, `base rows: 12 generated (area 600 / row 50)`);

// ── SMOKE 1: no overrides clone ────────────────────────────────────────────
{
  const undefOut = materializeTableRowsWithOverrides(baseRows, undefined, area);
  expect(Array.isArray(undefOut) && undefOut.length === baseRows.length,
    "case1 undefined: same length");
  expect(undefOut !== baseRows, "case1 undefined: output array is a fresh array");
  expect(undefOut[0] !== baseRows[0], "case1 undefined: output rects are fresh objects");
  for (let i = 0; i < baseRows.length; i++) {
    const a = baseRows[i], b = undefOut[i];
    if (a.x !== b.x || a.y !== b.y || a.width !== b.width || a.height !== b.height) {
      fail(`case1 undefined: row[${i}] differs`);
    }
  }
  ok(`case1 undefined: row values identical (deep clone)`);
  const emptyOut = materializeTableRowsWithOverrides(baseRows, [], area);
  expect(emptyOut.length === baseRows.length, "case1 empty[]: same length");
  expect(emptyOut[0] !== baseRows[0], "case1 empty[]: fresh objects");
}

// ── SMOKE 2: single height override ────────────────────────────────────────
{
  const ov = [{ rowIndex: 1, height: 80 }];
  const out = materializeTableRowsWithOverrides(baseRows, ov, area);
  expect(out[0].y === baseRows[0].y && out[0].height === 50,
    "case2 height: row[0] untouched");
  expect(out[1].y === baseRows[1].y && out[1].height === 80,
    "case2 height: row[1] keeps base y, height=80");
  expect(out[2].y === out[1].y + 80,
    "case2 height: row[2] cascades from row[1].y + 80");
  expect(out[2].height === 50,
    "case2 height: row[2] keeps base height");
  // Trailing trim: original 12 rows extended past area bottom by 30 (one extra
  // height-50 row partially fits). Last row may have height clamped.
  expect(out.length <= baseRows.length,
    "case2 height: trailing trimmed (no row past area bottom)");
  const last = out[out.length - 1];
  expect(last.y + last.height <= area.y + area.height + 1e-6,
    "case2 height: last row inside area");
}

// ── SMOKE 3: y override + cascade ──────────────────────────────────────────
{
  const ov = [{ rowIndex: 1, y: 200 }];
  const out = materializeTableRowsWithOverrides(baseRows, ov, area);
  expect(out[1].y === 200, "case3 y: row[1] y forced to 200");
  expect(out[1].height === baseRows[1].height,
    "case3 y: row[1] keeps base height");
  expect(out[2].y === 200 + baseRows[1].height,
    "case3 y: row[2] cascades from row[1] (200 + 50)");
}

// ── SMOKE 4: invalid overrides ignored ─────────────────────────────────────
{
  const bad = [
    { rowIndex: -1, height: 80 },             // rowIndex < 0
    { rowIndex: 999, height: 80 },            // out of range
    { rowIndex: 1.5, height: 80 },            // non-integer
    { rowIndex: "0", height: 80 },            // non-number rowIndex
    { rowIndex: 2, height: 0 },               // height too small
    { rowIndex: 2, height: -10 },             // negative height
    { rowIndex: 3, y: NaN },                  // non-finite y
    { rowIndex: 4, y: "200" },                // non-number y
    null, undefined, "not-an-object",
  ];
  const out = materializeTableRowsWithOverrides(baseRows, bad, area);
  // No override fully applied → output identical to base clone
  for (let i = 0; i < baseRows.length; i++) {
    const a = baseRows[i], b = out[i];
    if (!b) continue;  // trim may have removed bottom rows if mismatch
    if (a.x !== b.x || a.y !== b.y || a.width !== b.width || a.height !== b.height) {
      fail(`case4 invalid: row[${i}] diverges (a=${JSON.stringify(a)} b=${JSON.stringify(b)})`);
    }
  }
  ok(`case4 invalid: all malformed overrides ignored`);
}

// ── SMOKE 5: area clamp / trailing trim ────────────────────────────────────
{
  // Huge height override at row 0 should push everything past area bottom →
  // trailing rows get trimmed; last surviving row may have its height clamped.
  const ov = [{ rowIndex: 0, height: 400 }];
  const out = materializeTableRowsWithOverrides(baseRows, ov, area);
  expect(out.length >= 1, "case5 clamp: at least row[0] survives");
  expect(out[0].height === 400, "case5 clamp: row[0] height=400 applied");
  for (const r of out) {
    if (r.y < area.y - 1e-6) fail(`case5 clamp: row above area top: ${JSON.stringify(r)}`);
    if (r.y + r.height > area.y + area.height + 1e-6)
      fail(`case5 clamp: row past area bottom: ${JSON.stringify(r)}`);
    if (r.height < MIN_ROW_HEIGHT) fail(`case5 clamp: row height < MIN_ROW_HEIGHT: ${JSON.stringify(r)}`);
  }
  ok(`case5 clamp: every row within area & ≥ MIN_ROW_HEIGHT`);
  // Last row should NOT be the full base height — either trimmed or clamped
  expect(out.length < baseRows.length,
    "case5 clamp: trailing rows actually trimmed (less than base count)");
}

// ── SMOKE 6: mutation guard ────────────────────────────────────────────────
{
  const baseClone = JSON.parse(JSON.stringify(baseRows));
  const ov = [
    { rowIndex: 1, height: 80, locked: true },
    { rowIndex: 3, y: 300 },
  ];
  const ovClone = JSON.parse(JSON.stringify(ov));
  const areaClone = JSON.parse(JSON.stringify(area));
  materializeTableRowsWithOverrides(baseRows, ov, area);
  materializeTableRowsWithOverrides(baseRows, ov, area); // run twice
  expect(JSON.stringify(baseRows) === JSON.stringify(baseClone),
    "case6 mutation: baseRows unchanged");
  expect(JSON.stringify(ov) === JSON.stringify(ovClone),
    "case6 mutation: rowOverrides unchanged");
  expect(JSON.stringify(area) === JSON.stringify(areaClone),
    "case6 mutation: area unchanged");
  // locked is silently preserved on input but not consumed at materialization
  ok(`case6 mutation: locked override preserved on input, ignored at materialization`);
}

// ── SMOKE 7: buildTableRows backward-compat ────────────────────────────────
{
  const rows = buildTableRows(area, rowTemplate);
  expect(rows.length === 12, "case7 backcompat: buildTableRows still emits 12 rows");
  expect(rows[0].x === 60 && rows[0].y === 100 && rows[0].height === 50,
    "case7 backcompat: row[0] shape preserved");
  expect(rows[11].y === 100 + 11 * 50,
    "case7 backcompat: cascade preserved");
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
