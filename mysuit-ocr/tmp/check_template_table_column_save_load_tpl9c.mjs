#!/usr/bin/env node
// TPL-9C-TEMPLATE-TABLE-COLUMN-SAVE-LOAD
// Read-only fixture + runtime smoke. Imports buildExportPayload from the
// real production helper and verifies the save payload preserves user-
// defined table.columns alongside rowTemplate/rows/colGuides/stopKeywords
// /tableName for every fixture. Also mirrors the TemplateRightPanel
// getColumns policy locally to verify colGuides ↔ columns mismatch
// handling.
//
// Tag on success: [TEMPLATE_TABLE_COLUMN_SAVE_LOAD_TPL9C] PASS

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
const TAG = "[TEMPLATE_TABLE_COLUMN_SAVE_LOAD_TPL9C]";

// Node 24 strip-types loader — resolve sibling .ts files from bare relative
// specifiers (buildTemplateExportPayload imports from "../../../common/..."
// without extensions, same pattern as TPL-8B/8D/8F runners).
const LOADER_DIR = mkdtempSync(join(tmpdir(), "tpl9c-loader-"));
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
function expect(cond, label) { if (!cond) fail(`smoke: ${label}`); else ok(`smoke: ${label}`); }
function eqJSON(a, b) { return JSON.stringify(a) === JSON.stringify(b); }

// ---------------------------------------------------------------------------
// Paths
// ---------------------------------------------------------------------------
const FIXTURE_DIR = resolve(ROOT, "tmp/fixtures/template_table_columns");
const PAYLOAD_BUILDER = resolve(ROOT, "src/components/template/utils/buildTemplateExportPayload.ts");
const TEMPLATE_RIGHT_PANEL = resolve(ROOT, "src/components/template/ui/TemplateRightPanel.tsx");
const TEMPLATE_ANNOTATOR = resolve(ROOT, "src/components/template/ui/TemplateAnnotator.tsx");
const OCR_CANVAS_PANE = resolve(ROOT, "src/common/ui/OcrCanvasPane.tsx");
const OCR_TYPES = resolve(ROOT, "src/common/types/ocr.ts");
const VIEWMODEL = resolve(ROOT, "src/common/utils/tableResultViewModel.ts");
const MAPPER = resolve(ROOT, "src/components/runocr/utils/mapOcrResponse.ts");
const OCR_RESULT_PANEL = resolve(ROOT, "src/components/runocr/ui/OcrResultPanel.tsx");
const RUNOCR_WORKSPACE = resolve(ROOT, "src/components/runocr/RunOcrWorkspace.tsx");
const UNSTRUCTURED_BUILDER = resolve(ROOT, "src/components/template/UnstructuredBuilder.tsx");
const TEST_WORKSPACE = resolve(ROOT, "src/components/test/TestWorkspace.tsx");
const CLEAN_JSON = resolve(ROOT, "src/common/utils/cleanJsonBuilder.ts");
const MARKDOWN_REPORT = resolve(ROOT, "src/common/utils/markdownReportBuilder.ts");

// ---------------------------------------------------------------------------
// 1. Fixture directory + ≥6 fixtures
// ---------------------------------------------------------------------------
if (!existsSync(FIXTURE_DIR)) fail(`fixture dir missing: ${relative(ROOT, FIXTURE_DIR)}`);
else ok(`fixture dir present`);

let fixturePaths = [];
try {
  fixturePaths = readdirSync(FIXTURE_DIR)
    .filter((n) => n.endsWith(".json"))
    .sort()
    .map((n) => resolve(FIXTURE_DIR, n));
} catch {}
if (fixturePaths.length < 6) fail(`expected ≥6 fixtures, found ${fixturePaths.length}`);
else ok(`fixtures found: ${fixturePaths.length}`);
for (const p of fixturePaths) note(`  - ${relative(ROOT, p)}`);

// Required fixture filenames
const REQUIRED_FIXTURES = [
  "legacy_no_columns.json",
  "column_key_only.json",
  "label_ko_only.json",
  "canonical_only.json",
  "full_columns.json",
  "colguides_mismatch_more_columns.json",
  "colguides_mismatch_less_columns.json",
  "full_table_props_with_columns.json",
];
for (const name of REQUIRED_FIXTURES) {
  if (!existsSync(resolve(FIXTURE_DIR, name)))
    fail(`required fixture missing: ${name}`);
  else ok(`required fixture present: ${name}`);
}

// ---------------------------------------------------------------------------
// 2. Untouched production files (existence + invariants)
// ---------------------------------------------------------------------------
const untouched = [
  ["buildTemplateExportPayload.ts", PAYLOAD_BUILDER],
  ["TemplateRightPanel.tsx", TEMPLATE_RIGHT_PANEL],
  ["TemplateAnnotator.tsx", TEMPLATE_ANNOTATOR],
  ["OcrCanvasPane.tsx", OCR_CANVAS_PANE],
  ["common/types/ocr.ts", OCR_TYPES],
  ["tableResultViewModel.ts", VIEWMODEL],
  ["mapOcrResponse.ts", MAPPER],
  ["OcrResultPanel.tsx", OCR_RESULT_PANEL],
  ["RunOcrWorkspace.tsx", RUNOCR_WORKSPACE],
  ["UnstructuredBuilder.tsx", UNSTRUCTURED_BUILDER],
  ["TestWorkspace.tsx", TEST_WORKSPACE],
  ["cleanJsonBuilder.ts", CLEAN_JSON],
  ["markdownReportBuilder.ts", MARKDOWN_REPORT],
];
for (const [label, p] of untouched) {
  if (!existsSync(p)) fail(`expected untouched file missing: ${label}`);
  else ok(`present (untouched expected): ${label}`);
}

// rowOverrides scope: at TPL-9C time this was deferred to TPL-11. TPL-12A
// later introduced the schema (TableRowOverride + TableMeta.rowOverrides?)
// and the pure helper materializeTableRowsWithOverrides in ocrTableRegion.ts.
// Allow those two specific files; everything else must still be free of the
// symbol (UI/payload integration belongs to later phases).
const srcFiles = walk(resolve(ROOT, "src")).filter((p) =>
  p.endsWith(".ts") || p.endsWith(".tsx")
);
const _TPL12_ROW_OVERRIDE_ALLOW = new Set([
  resolve(ROOT, "src/common/types/ocr.ts"),                                       // TPL-12A
  resolve(ROOT, "src/common/utils/ocrTableRegion.ts"),                            // TPL-12A
  resolve(ROOT, "src/components/template/utils/buildTemplateExportPayload.ts"),   // TPL-12B
  resolve(ROOT, "src/common/ui/OcrCanvasPane.tsx"),                               // TPL-12C
  resolve(ROOT, "src/components/template/ui/TemplateAnnotator.tsx"),              // TPL-12C
  resolve(ROOT, "src/components/template/ui/TemplateRightPanel.tsx"),             // TPL-12C
]);
for (const p of srcFiles) {
  const src = readSafe(p) ?? "";
  if (/\browOverrides\b/.test(src) && !_TPL12_ROW_OVERRIDE_ALLOW.has(p)) {
    fail(`rowOverrides reference found in ${relative(ROOT, p)} — outside TPL-12A/12B/12C allow-list`);
  }
}
ok(`no rowOverrides reference in src/ outside TPL-12A/12B/12C allow-list`);

// ---------------------------------------------------------------------------
// 3. src/lib absent + @/lib imports = 0
// ---------------------------------------------------------------------------
const SRC_LIB = resolve(ROOT, "src/lib");
if (existsSync(SRC_LIB)) {
  const f = walk(SRC_LIB);
  if (f.length > 0) fail(`src/lib must be absent or empty`);
  else ok(`src/lib present but empty`);
} else ok(`src/lib absent`);

const reLibAlias = /from\s+["']@\/lib(\/|["'])|import\(\s*["']@\/lib(\/|["'])/;
const reLibRelative = /from\s+["']\.\.\/lib(\/|["'])|from\s+["']\.\.\/\.\.\/lib(\/|["'])/;
let aliasHits = 0, relHits = 0;
const allSrcFiles = walk(resolve(ROOT, "src")).filter((p) =>
  p.endsWith(".ts") || p.endsWith(".tsx") || p.endsWith(".mjs") || p.endsWith(".js")
);
for (const p of allSrcFiles) {
  const src = readSafe(p) ?? "";
  if (reLibAlias.test(src)) { aliasHits++; fail(`@/lib import in ${relative(ROOT, p)}`); }
  if (reLibRelative.test(src)) { relHits++; fail(`relative lib import in ${relative(ROOT, p)}`); }
}
if (aliasHits === 0) ok(`@/lib imports: 0`);
if (relHits === 0) ok(`relative lib imports: 0`);

// ---------------------------------------------------------------------------
// 4. Parse fixtures
// ---------------------------------------------------------------------------
const fixtures = [];
for (const p of fixturePaths) {
  const raw = readSafe(p) ?? "";
  let parsed = null;
  try {
    parsed = JSON.parse(raw);
    ok(`fixture parse OK: ${relative(ROOT, p)}`);
  } catch (err) {
    fail(`fixture parse FAIL: ${relative(ROOT, p)} — ${err?.message ?? err}`);
    continue;
  }
  fixtures.push({ path: p, name: parsed?._meta?.fixtureName ?? relative(ROOT, p), parsed });
}

// ---------------------------------------------------------------------------
// 5. Import buildExportPayload from the real production helper
// ---------------------------------------------------------------------------
let payloadMod = null;
try {
  payloadMod = await import(pathToFileURL(PAYLOAD_BUILDER).href);
  ok(`buildTemplateExportPayload runtime import succeeded`);
} catch (err) {
  fail(`buildTemplateExportPayload runtime import failed: ${err?.message ?? err}`);
}
if (!payloadMod) {
  console.error(`${TAG} FAIL aborting smoke — payload helper unimportable`);
  console.error(`${TAG} FAIL count=${failures.length}`);
  process.exit(1);
}
const { buildExportPayload } = payloadMod;
expect(typeof buildExportPayload === "function", `buildExportPayload is function`);

// ---------------------------------------------------------------------------
// 6. getColumns policy mirror (TemplateRightPanel local helper). MUST match
//    the runtime behavior verbatim — used to assert mismatch handling.
// ---------------------------------------------------------------------------
function mirrorNormalizeColGuides(guides) {
  if (!Array.isArray(guides) || guides.length === 0) return [];
  const filtered = guides
    .map((v) => (Number.isFinite(v) ? v : NaN))
    .filter((v) => Number.isFinite(v))
    .filter((v) => v > 0 && v < 1)
    .sort((a, b) => a - b);
  const eps = 0.002;
  const out = [];
  for (const v of filtered) {
    if (out.length === 0) out.push(v);
    else if (Math.abs(out[out.length - 1] - v) > eps) out.push(v);
  }
  return out.slice(0, 40);
}
function mirrorGetColumns(region) {
  if (!region || region.fieldType !== "table") return [];
  const existing = region.table?.columns ?? [];
  const guideCount = mirrorNormalizeColGuides(region.table?.colGuides).length;
  const colCount = guideCount + 1;
  if (colCount <= 0) return existing;
  if (existing.length >= colCount) return existing.slice(0, colCount);
  const result = [];
  for (let i = 0; i < colCount; i++) result.push(existing[i] ?? { index: i });
  return result;
}

// ---------------------------------------------------------------------------
// 7. Per-fixture round-trip checks
// ---------------------------------------------------------------------------
function findFixture(name) {
  return fixtures.find((f) => f.name === name || f.path.endsWith(`${name}.json`));
}

for (const fx of fixtures) {
  const label = `[${fx.name}]`;
  const fixture = fx.parsed;
  const snap = JSON.parse(JSON.stringify(fixture));

  // Run buildExportPayload with fixture input
  const out = buildExportPayload({
    templateName: fixture.templateName,
    loaded: fixture.loaded,
    regions: fixture.regions,
    documentType: fixture.documentType,
  });

  // Top-level shape
  expect(out && typeof out === "object", `${label} payload is an object`);
  expect(out.templateName === fixture.templateName, `${label} templateName preserved`);
  expect(Array.isArray(out.regions), `${label} regions is array`);
  expect(out.regions.length === fixture.regions.length,
    `${label} regions count preserved`);

  // Mutation guard
  expect(eqJSON(fixture, snap), `${label} buildExportPayload does not mutate fixture`);

  // Per-table region invariants
  for (let ri = 0; ri < fixture.regions.length; ri++) {
    const inputRegion = fixture.regions[ri];
    if (inputRegion.fieldType !== "table") continue;
    const outRegion = out.regions[ri];
    const lr = `${label} region[${ri}]`;

    expect(outRegion.fieldType === "table", `${lr} fieldType preserved`);
    expect(outRegion.table && typeof outRegion.table === "object", `${lr} table object present`);

    const inT = inputRegion.table;
    const outT = outRegion.table;

    // mode preserved
    expect(outT.mode === (inT.mode ?? "repeat"), `${lr} table.mode preserved (default 'repeat')`);

    // rowTemplate preserved (rounded; values match)
    if (inT.rowTemplate) {
      expect(outT.rowTemplate
        && Math.round(inT.rowTemplate.x) === outT.rowTemplate.x
        && Math.round(inT.rowTemplate.y) === outT.rowTemplate.y
        && Math.round(inT.rowTemplate.width) === outT.rowTemplate.width
        && Math.round(inT.rowTemplate.height) === outT.rowTemplate.height,
        `${lr} rowTemplate preserved (rounded)`);
    } else {
      expect(outT.rowTemplate === null,
        `${lr} rowTemplate=null when input has none (export normalizes)`);
    }

    // rows preserved (or [] when input had none)
    if (Array.isArray(inT.rows)) {
      expect(Array.isArray(outT.rows) && outT.rows.length === inT.rows.length,
        `${lr} rows length preserved`);
    } else {
      expect(Array.isArray(outT.rows) && outT.rows.length === 0,
        `${lr} rows = [] when input had none`);
    }

    // colGuides preserved (normalized — same shape as input)
    const expectedGuides = mirrorNormalizeColGuides(inT.colGuides);
    expect(Array.isArray(outT.colGuides) && outT.colGuides.length === expectedGuides.length,
      `${lr} colGuides count matches normalize output`);

    // colX is derived from colGuides → length must match
    expect(Array.isArray(outT.colX) && outT.colX.length === expectedGuides.length,
      `${lr} colX length === colGuides length`);

    // stopKeywords preserved
    const expectedStop = Array.isArray(inT.stopKeywords) ? inT.stopKeywords.slice(0, 30) : [];
    expect(Array.isArray(outT.stopKeywords) && outT.stopKeywords.length === expectedStop.length,
      `${lr} stopKeywords preserved`);

    // tableName preserved (optional)
    if (inT.tableName) {
      expect(outT.tableName === inT.tableName, `${lr} tableName preserved`);
    } else {
      expect(!("tableName" in outT), `${lr} tableName key omitted when input had none`);
    }

    // columns — the key TPL-9C invariant
    if (Array.isArray(inT.columns)) {
      // buildExportPayload spreads columns verbatim (no slice/extend), so
      // the input columns array must round-trip byte-identically.
      expect(Array.isArray(outT.columns)
        && outT.columns.length === inT.columns.length,
        `${lr} columns count preserved verbatim (no slice/extend at export)`);
      // Field-by-field equality on every column entry
      for (let ci = 0; ci < inT.columns.length; ci++) {
        const inCol = inT.columns[ci];
        const outCol = outT.columns[ci];
        expect(eqJSON(inCol, outCol),
          `${lr} columns[${ci}] preserved byte-identically`);
      }
    } else {
      // legacy: input has no columns → export must NOT inject the key
      expect(!("columns" in outT), `${lr} columns key omitted when input had none`);
    }
  }
}

// ---------------------------------------------------------------------------
// 8. getColumns policy targeted checks
// ---------------------------------------------------------------------------

// 8a: legacy_no_columns → mirrorGetColumns yields N+1 entries with default
// { index: i } shape so the UI can render rows.
{
  const fx = findFixture("legacy_no_columns");
  if (fx) {
    const region = fx.parsed.regions[0];
    const cols = mirrorGetColumns(region);
    const guideCount = mirrorNormalizeColGuides(region.table.colGuides).length;
    expect(cols.length === guideCount + 1,
      `legacy: getColumns auto-creates ${guideCount + 1} entries`);
    expect(cols.every((c, i) => c.index === i),
      `legacy: getColumns entries have index 0..N`);
  }
}

// 8b: colguides_mismatch_more_columns → trailing slice
{
  const fx = findFixture("colguides_mismatch_more_columns");
  if (fx) {
    const region = fx.parsed.regions[0];
    const cols = mirrorGetColumns(region);
    const guideCount = mirrorNormalizeColGuides(region.table.colGuides).length;
    const colCount = guideCount + 1;
    expect(cols.length === colCount,
      `mismatch-more: getColumns slices trailing — kept ${colCount} of ${region.table.columns.length}`);
    // Leading entries preserved verbatim (no overwrite)
    for (let i = 0; i < colCount; i++) {
      expect(cols[i].columnKey === region.table.columns[i].columnKey,
        `mismatch-more: leading columns[${i}].columnKey preserved`);
    }
  }
}

// 8c: colguides_mismatch_less_columns → fill with { index: i }
{
  const fx = findFixture("colguides_mismatch_less_columns");
  if (fx) {
    const region = fx.parsed.regions[0];
    const cols = mirrorGetColumns(region);
    const guideCount = mirrorNormalizeColGuides(region.table.colGuides).length;
    const colCount = guideCount + 1;
    expect(cols.length === colCount,
      `mismatch-less: getColumns padded to ${colCount} entries`);
    // First 2 keep their input values; last 2 are filler with only index.
    expect(cols[0].columnKey === "itemName" && cols[1].columnKey === "quantity",
      `mismatch-less: input entries preserved at leading positions`);
    expect(cols[2].columnKey === undefined && cols[2].index === 2,
      `mismatch-less: trailing filler has only index, no columnKey`);
  }
}

// 8d: legacy export path — even though getColumns synthesises entries for
// the UI, buildExportPayload must NOT inject them into the saved payload.
{
  const fx = findFixture("legacy_no_columns");
  if (fx) {
    const out = buildExportPayload({
      templateName: fx.parsed.templateName,
      loaded: fx.parsed.loaded,
      regions: fx.parsed.regions,
      documentType: fx.parsed.documentType,
    });
    expect(!("columns" in out.regions[0].table),
      `legacy export: columns key omitted from saved payload`);
  }
}

// 8e: full_columns export — all six field families preserved on every column
{
  const fx = findFixture("full_columns");
  if (fx) {
    const out = buildExportPayload({
      templateName: fx.parsed.templateName,
      loaded: fx.parsed.loaded,
      regions: fx.parsed.regions,
      documentType: fx.parsed.documentType,
    });
    const outCols = out.regions[0].table.columns;
    for (const c of outCols) {
      for (const k of ["columnKey", "labelKo", "labelEn", "koField", "enField", "canonicalColumn", "index"]) {
        if (!(k in c)) fail(`full_columns: column missing key "${k}"`);
      }
    }
    ok(`full_columns export: every column carries columnKey/labelKo/labelEn/koField/enField/canonicalColumn/index`);
  }
}

// 8f: full_table_props_with_columns — verify columns + tableName + rows +
// rowTemplate + stopKeywords all coexist in the saved payload
{
  const fx = findFixture("full_table_props_with_columns");
  if (fx) {
    const out = buildExportPayload({
      templateName: fx.parsed.templateName,
      loaded: fx.parsed.loaded,
      regions: fx.parsed.regions,
      documentType: fx.parsed.documentType,
    });
    const t = out.regions[0].table;
    expect(t.tableName === "품목표", `full-props: tableName preserved`);
    expect(Array.isArray(t.columns) && t.columns.length === 4, `full-props: 4 columns`);
    expect(Array.isArray(t.rows) && t.rows.length === 3, `full-props: 3 rows`);
    expect(t.rowTemplate && t.rowTemplate.height === 36, `full-props: rowTemplate.height preserved`);
    expect(Array.isArray(t.stopKeywords) && t.stopKeywords.length === 3,
      `full-props: stopKeywords preserved`);
    expect(Array.isArray(t.colGuides) && t.colGuides.length === 3,
      `full-props: colGuides preserved`);
  }
}

// 8g: documentType pass-through
{
  const fx = findFixture("full_columns");
  if (fx) {
    const out = buildExportPayload({
      templateName: fx.parsed.templateName,
      loaded: fx.parsed.loaded,
      regions: fx.parsed.regions,
      documentType: fx.parsed.documentType,
    });
    expect(out.documentType === "invoice_statement",
      `documentType pass-through (invoice_statement)`);
  }
}

// ---------------------------------------------------------------------------
// 9. New-file scope check — only tmp/fixtures/* and tmp/check_*.mjs allowed
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
    if (PHASE_ALLOW.has(path)) { note(`new production (allowed): ${path}`); continue; }
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
