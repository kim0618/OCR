#!/usr/bin/env node
// TPL-8F-TABLE-RESULT-EXPORT-INTEGRATION
// Static + runtime smoke. Verifies cleanJsonBuilder / markdownReportBuilder
// accept optional `tableResultViewModels` without disturbing the Clean JSON
// v1 / Markdown v1 fixture-locked contracts, and emit unstructured tables
// when the new input carries `source: "unstructured_definition"` entries.
//
// Tag on success: [TABLE_RESULT_EXPORT_INTEGRATION_TPL8F] PASS

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
const TAG = "[TABLE_RESULT_EXPORT_INTEGRATION_TPL8F]";

// Node 24 strip-types — register a small loader so `.ts` siblings imported
// via bare relative paths resolve at runtime (same pattern as TPL-8B/8D).
const LOADER_DIR = mkdtempSync(join(tmpdir(), "tpl8f-loader-"));
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
  // Also resolve absolute @/ aliases (used by export builders) to src/.
  if (specifier.startsWith("@/")) {
    const SRC = "${pathToFileURL(resolve(ROOT, "src")).href}";
    const rel = specifier.slice(2);
    const tsHref = SRC + "/" + rel + ".ts";
    try {
      if (existsSync(fileURLToPath(new URL(tsHref)))) return next(tsHref, context);
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
const CLEAN_JSON = resolve(ROOT, "src/common/utils/cleanJsonBuilder.ts");
const MARKDOWN_REPORT = resolve(ROOT, "src/common/utils/markdownReportBuilder.ts");
const OCR_RESULT_PANEL = resolve(ROOT, "src/components/runocr/ui/OcrResultPanel.tsx");
const VIEWMODEL_HELPER = resolve(ROOT, "src/common/utils/tableResultViewModel.ts");
const MAPPER = resolve(ROOT, "src/components/runocr/utils/mapOcrResponse.ts");
const EXTRACT_HELPER = resolve(ROOT, "src/components/runocr/utils/extractUnstructuredTableRows.ts");
const STRUCTURED_VM = resolve(ROOT, "src/common/utils/structuredTableViewModel.ts");
const INVOICE_DISPLAY = resolve(ROOT, "src/common/utils/invoiceTableDisplay.ts");
const RUNOCR_WORKSPACE = resolve(ROOT, "src/components/runocr/RunOcrWorkspace.tsx");
const UNSTRUCTURED_BUILDER = resolve(ROOT, "src/components/template/UnstructuredBuilder.tsx");
const UNSTRUCTURED_DEF = resolve(ROOT, "src/components/template/utils/unstructuredDefinition.ts");
const TEMPLATE_RIGHT_PANEL = resolve(ROOT, "src/components/template/ui/TemplateRightPanel.tsx");
const TEST_WORKSPACE = resolve(ROOT, "src/components/test/TestWorkspace.tsx");
const OCR_CANVAS_PANE = resolve(ROOT, "src/common/ui/OcrCanvasPane.tsx");

// ---------------------------------------------------------------------------
// 1. Builders extended with tableResultViewModels optional input
// ---------------------------------------------------------------------------
const cjSrc = readSafe(CLEAN_JSON) ?? "";
const cjCode = stripComments(cjSrc);
const mdSrc = readSafe(MARKDOWN_REPORT) ?? "";
const mdCode = stripComments(mdSrc);

if (!/BuildCleanJsonInput\s*=\s*\{[\s\S]*?tableResultViewModels\?\s*:/m.test(cjCode))
  fail(`BuildCleanJsonInput missing optional tableResultViewModels field`);
else ok(`BuildCleanJsonInput.tableResultViewModels?: present`);

if (!/BuildMarkdownReportInput\s*=\s*\{[\s\S]*?tableResultViewModels\?\s*:/m.test(mdCode))
  fail(`BuildMarkdownReportInput missing optional tableResultViewModels field`);
else ok(`BuildMarkdownReportInput.tableResultViewModels?: present`);

// Type-only import from tableResultViewModel (TPL-8F) OR runtime import that
// also brings selectRepresentativeTableResultViewModels in (TPL-13B).
const _tpl13bShipped_cj = /selectRepresentativeTableResultViewModels/.test(cjCode);
const _tpl13bShipped_md = /selectRepresentativeTableResultViewModels/.test(mdCode);
if (_tpl13bShipped_cj) {
  note(`cleanJsonBuilder uses runtime import incl. selectRepresentativeTableResultViewModels (TPL-13B shipped)`);
} else if (!/import\s+type\s+\{\s*TableResultViewModel\s*\}\s*from\s+["']@\/common\/utils\/tableResultViewModel["']/.test(cjCode)) {
  fail(`cleanJsonBuilder does not import type TableResultViewModel`);
} else {
  ok(`cleanJsonBuilder imports TableResultViewModel type`);
}
if (_tpl13bShipped_md) {
  note(`markdownReportBuilder uses runtime import incl. selectRepresentativeTableResultViewModels (TPL-13B shipped)`);
} else if (!/import\s+type\s+\{\s*TableResultViewModel\s*\}\s*from\s+["']@\/common\/utils\/tableResultViewModel["']/.test(mdCode)) {
  fail(`markdownReportBuilder does not import type TableResultViewModel`);
} else {
  ok(`markdownReportBuilder imports TableResultViewModel type`);
}

// Clean JSON output includes a new optional unstructuredTables key (TPL-8F).
// TPL-13B replaces per-source emission with a single representative `tables`
// entry; the unstructuredTables type declaration is kept for legacy
// type-shape compat.
if (!/unstructuredTables\?\s*:/.test(cjCode))
  fail(`CleanJsonResult missing optional unstructuredTables type declaration`);
else ok(`CleanJsonResult.unstructuredTables?: type present (legacy shape preserved)`);

// Both builders gate on source === "unstructured_definition" (TPL-8F) OR
// delegate source-priority selection to selectRepresentativeTableResultViewModels
// (TPL-13B).
if (!/source\s*===\s*"unstructured_definition"/.test(cjCode) && !_tpl13bShipped_cj)
  fail(`cleanJsonBuilder does not filter unstructured_definition`);
else if (_tpl13bShipped_cj)
  note(`cleanJsonBuilder uses selectRepresentativeTableResultViewModels (TPL-13B) instead of per-source filter`);
else ok(`cleanJsonBuilder filters unstructured_definition`);
if (!/source\s*===\s*"unstructured_definition"/.test(mdCode) && !_tpl13bShipped_md)
  fail(`markdownReportBuilder does not filter unstructured_definition`);
else if (_tpl13bShipped_md)
  note(`markdownReportBuilder uses selectRepresentativeTableResultViewModels (TPL-13B) instead of per-source filter`);
else ok(`markdownReportBuilder filters unstructured_definition`);

// Markdown adds 비정형 테이블 section heading
if (!/##\s*비정형\s*테이블/.test(mdCode))
  fail(`markdownReportBuilder missing '## 비정형 테이블' section`);
else ok(`markdownReportBuilder includes '## 비정형 테이블' section header`);

// ---------------------------------------------------------------------------
// 2. OcrResultPanel passes tableResultViewModels to both exports
// ---------------------------------------------------------------------------
const orpSrc = readSafe(OCR_RESULT_PANEL) ?? "";
const orpCode = stripComments(orpSrc);
// buildCleanJsonResult call site
if (!/buildCleanJsonResult\(\{[\s\S]{0,400}tableResultViewModels[\s\S]{0,400}\}\)/m.test(orpCode))
  fail(`OcrResultPanel buildCleanJsonResult call missing tableResultViewModels arg`);
else ok(`OcrResultPanel passes tableResultViewModels to buildCleanJsonResult`);
// buildMarkdownReport call site
if (!/buildMarkdownReport\(\{[\s\S]{0,400}tableResultViewModels[\s\S]{0,200}\}\)/m.test(orpCode))
  fail(`OcrResultPanel buildMarkdownReport call missing tableResultViewModels arg`);
else ok(`OcrResultPanel passes tableResultViewModels to buildMarkdownReport`);

// ---------------------------------------------------------------------------
// 3. Untouched files
// ---------------------------------------------------------------------------
const untouched = [
  ["tableResultViewModel.ts", VIEWMODEL_HELPER],
  ["mapOcrResponse.ts", MAPPER],
  ["extractUnstructuredTableRows.ts", EXTRACT_HELPER],
  ["structuredTableViewModel.ts", STRUCTURED_VM],
  ["invoiceTableDisplay.ts", INVOICE_DISPLAY],
  ["RunOcrWorkspace.tsx", RUNOCR_WORKSPACE],
  ["UnstructuredBuilder.tsx", UNSTRUCTURED_BUILDER],
  ["unstructuredDefinition.ts", UNSTRUCTURED_DEF],
  ["TemplateRightPanel.tsx", TEMPLATE_RIGHT_PANEL],
  ["TestWorkspace.tsx", TEST_WORKSPACE],
  ["OcrCanvasPane.tsx", OCR_CANVAS_PANE],
];
for (const [label, p] of untouched) {
  if (!existsSync(p)) fail(`expected untouched file missing: ${label}`);
  else ok(`present (untouched expected): ${label}`);
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
// 5. Runtime smoke — dynamically import the two builders
// ---------------------------------------------------------------------------
let cjMod = null, mdMod = null;
try {
  cjMod = await import(pathToFileURL(CLEAN_JSON).href);
  ok(`cleanJsonBuilder runtime import succeeded`);
} catch (err) {
  fail(`cleanJsonBuilder runtime import failed: ${err?.message ?? err}`);
}
try {
  mdMod = await import(pathToFileURL(MARKDOWN_REPORT).href);
  ok(`markdownReportBuilder runtime import succeeded`);
} catch (err) {
  fail(`markdownReportBuilder runtime import failed: ${err?.message ?? err}`);
}
if (!cjMod || !mdMod) {
  console.error(`${TAG} FAIL aborting smoke — imports failed`);
  console.error(`${TAG} FAIL count=${failures.length}`);
  process.exit(1);
}
const { buildCleanJsonResult } = cjMod;
const { buildMarkdownReport } = mdMod;
expect(typeof buildCleanJsonResult === "function", `buildCleanJsonResult is function`);
expect(typeof buildMarkdownReport === "function", `buildMarkdownReport is function`);

// Helper to build a fake TableResultViewModel quickly
function mkVM(opts) {
  const columns = opts.columns.map((c) => ({ columnKey: c.key, labelKo: c.labelKo, ...(c.labelEn ? { labelEn: c.labelEn } : {}), source: opts.colSource ?? "user" }));
  const rows = (opts.rows ?? []).map((row, idx) => ({
    index: idx,
    values: Object.fromEntries(columns.map((c) => [c.columnKey, row[c.columnKey] ?? ""])),
    cells: columns.map((c) => {
      const v = row[c.columnKey] ?? "";
      const isEmpty = v === "";
      return { key: c.columnKey, value: v, displayValue: isEmpty ? "-" : v, isEmpty };
    }),
  }));
  return {
    tableKey: opts.tableKey,
    labelKo: opts.labelKo,
    ...(opts.labelEn ? { labelEn: opts.labelEn } : {}),
    source: opts.source,
    columns,
    rows,
    meta: {
      source: opts.source,
      rowCount: rows.length,
      columnCount: columns.length,
      hasRows: rows.length > 0,
      hasColumns: columns.length > 0,
      ...(opts.documentType ? { documentType: opts.documentType } : {}),
    },
  };
}

// ── SMOKE 1: backward compat (no tableResultViewModels) — same output ────
{
  const fields = [
    { name: "회사명", field_type: "field", value: "ACME", ko: "회사명" },
  ];
  const r1 = buildCleanJsonResult({ templateName: "T", fields });
  expect(typeof r1 === "object" && r1.templateName === "T", "case1 backcompat: templateName preserved");
  expect(Array.isArray(r1.info) && r1.info.length === 1, "case1 backcompat: 1 info entry");
  expect(!("unstructuredTables" in r1), "case1 backcompat: no unstructuredTables key");
  expect(!("tables" in r1), "case1 backcompat: no tables (no table fields)");

  const md = buildMarkdownReport({ fields, processingTime: 1.0 });
  expect(md.startsWith("# OCR 결과"), "case1 backcompat md: contract heading");
  expect(!/##\s*비정형\s*테이블/.test(md), "case1 backcompat md: no unstructured section");
}

// ── SMOKE 2: backend-only via tableResultViewModels — no duplicate emit ──
{
  const fields = [{ name: "items", field_type: "table", value: "" }];
  const docTableRows = [{ itemName: "A", quantity: "1", amount: "100" }];
  const docTableDisplayCols = [
    { key: "itemName" }, { key: "quantity" }, { key: "amount" },
  ];
  const backendVM = mkVM({
    source: "backend_document_fields",
    colSource: "canonical",
    tableKey: "document_fields.tableRows",
    labelKo: "문서 표",
    columns: [
      { key: "itemName", labelKo: "품목명" },
      { key: "quantity", labelKo: "수량" },
      { key: "amount",   labelKo: "금액" },
    ],
    rows: [{ itemName: "A", quantity: "1", amount: "100" }],
    documentType: "invoice_statement",
  });
  const r2 = buildCleanJsonResult({
    templateName: "T",
    fields,
    docTableRows,
    docTableDisplayCols,
    tableResultViewModels: [backendVM],
  });
  expect(Array.isArray(r2.tables) && r2.tables.length === 1, "case2 backend-only: existing tables path emits 1 table");
  expect(!("unstructuredTables" in r2), "case2 backend-only: no unstructuredTables (backend filtered out)");

  const md = buildMarkdownReport({
    fields, processingTime: 1.0, docTableRows,
    tableResultViewModels: [backendVM],
  });
  expect(!/##\s*비정형\s*테이블/.test(md), "case2 backend-only md: no unstructured section added");
}

// ── SMOKE 3: unstructured export — clean json ────────────────────────────
{
  const fields = [{ name: "items", field_type: "table", value: "" }];
  const itemsVM = mkVM({
    source: "unstructured_definition",
    tableKey: "items",
    labelKo: "품목표",
    labelEn: "items",
    columns: [
      { key: "itemName", labelKo: "품목명" },
      { key: "quantity", labelKo: "수량" },
      { key: "amount",   labelKo: "금액" },
    ],
    rows: [
      { itemName: "약품A", quantity: "10", amount: "10,000" },
      { itemName: "약품B", quantity: "5",  amount: "" },
    ],
  });
  const r3 = buildCleanJsonResult({
    templateName: "T", fields,
    tableResultViewModels: [itemsVM],
  });
  // TPL-8F emitted `unstructuredTables`; TPL-13B promotes it to representative
  // `tables`. Accept whichever shape the current builder produces (the entry
  // must exist and carry the expected user-defined columns/rows).
  const u = Array.isArray(r3.tables) && r3.tables[0]
    ? r3.tables[0]
    : (Array.isArray(r3.unstructuredTables) ? r3.unstructuredTables[0] : null);
  const uKey = u && (("tableKey" in u && u.tableKey) || u.key);
  const uLabel = u && (("labelKo" in u && u.labelKo) || u.label);
  expect(u != null, "case3 unstructured cj: entry exists (tables or unstructuredTables)");
  expect(uKey === "items", "case3 unstructured cj: tableKey/key = items");
  expect(uLabel === "품목표", "case3 unstructured cj: labelKo/label = 품목표");
  expect(Array.isArray(u.columns) && u.columns.length === 3
    && u.columns[0].columnKey === "itemName"
    && u.columns[1].columnKey === "quantity"
    && u.columns[2].columnKey === "amount",
    "case3 unstructured cj: column order preserved");
  expect(Array.isArray(u.rows) && u.rows.length === 2, "case3 unstructured cj: 2 rows");
  expect(u.rows[0].itemName === "약품A" && u.rows[0].quantity === "10" && u.rows[0].amount === "10,000",
    "case3 unstructured cj: row[0] values");
  expect(u.rows[1].itemName === "약품B" && u.rows[1].amount === "",
    "case3 unstructured cj: row[1] empty cell preserved");
}

// ── SMOKE 4: unstructured export — markdown ─────────────────────────────
{
  const fields = [{ name: "회사명", field_type: "field", value: "ACME", ko: "회사명" }];
  const itemsVM = mkVM({
    source: "unstructured_definition",
    tableKey: "items",
    labelKo: "품목표",
    columns: [
      { key: "itemName", labelKo: "품목명" },
      { key: "quantity", labelKo: "수량" },
    ],
    rows: [
      { itemName: "약품A", quantity: "10" },
      { itemName: "약품B", quantity: "5"  },
    ],
  });
  const md = buildMarkdownReport({
    fields, processingTime: 1.5,
    tableResultViewModels: [itemsVM],
  });
  expect(md.startsWith("# OCR 결과"), "case4 unstructured md: main heading preserved");
  expect(/##\s*비정형\s*테이블/.test(md), "case4 unstructured md: '## 비정형 테이블' section present");
  expect(/###\s*품목표/.test(md), "case4 unstructured md: '### 품목표' title present");
  expect(/\|\s*품목명\s*\|\s*수량\s*\|/.test(md), "case4 unstructured md: header labels");
  expect(/약품A\s*\|\s*10/.test(md), "case4 unstructured md: row[0] data");
  expect(/약품B\s*\|\s*5/.test(md), "case4 unstructured md: row[1] data");
}

// ── SMOKE 5: empty rows — safe ───────────────────────────────────────────
{
  const fields = [{ name: "회사명", field_type: "field", value: "ACME", ko: "회사명" }];
  const emptyVM = mkVM({
    source: "unstructured_definition",
    tableKey: "items", labelKo: "품목표",
    columns: [{ key: "itemName", labelKo: "품목명" }],
    rows: [],
  });
  const r5 = buildCleanJsonResult({ templateName: "T", fields, tableResultViewModels: [emptyVM] });
  // TPL-8F → `unstructuredTables`; TPL-13B → representative `tables`.
  const r5entry = Array.isArray(r5.tables) && r5.tables[0]
    ? r5.tables[0]
    : (Array.isArray(r5.unstructuredTables) ? r5.unstructuredTables[0] : null);
  expect(r5entry != null,
    "case5 empty rows cj: VM still emitted (tables or unstructuredTables)");
  expect(Array.isArray(r5entry.rows) && r5entry.rows.length === 0,
    "case5 empty rows cj: rows: []");

  const md = buildMarkdownReport({
    fields, processingTime: 1.0, tableResultViewModels: [emptyVM],
  });
  expect(/추출된 행이 없습니다/.test(md), "case5 empty rows md: '추출된 행이 없습니다' notice");
}

// ── SMOKE 6: empty columns — safe ────────────────────────────────────────
{
  const fields = [{ name: "회사명", field_type: "field", value: "ACME", ko: "회사명" }];
  const emptyColVM = mkVM({
    source: "unstructured_definition",
    tableKey: "items", labelKo: "품목표",
    columns: [],
    rows: [],
  });
  const md = buildMarkdownReport({
    fields, processingTime: 1.0, tableResultViewModels: [emptyColVM],
  });
  expect(/정의된 컬럼이 없습니다/.test(md), "case6 empty columns md: '정의된 컬럼이 없습니다' notice");
}

// ── SMOKE 7: input mutation guard ────────────────────────────────────────
{
  const fields = [{ name: "items", field_type: "table", value: "" }];
  const vm = mkVM({
    source: "unstructured_definition",
    tableKey: "t", labelKo: "T",
    columns: [{ key: "a", labelKo: "A" }],
    rows: [{ a: "x" }],
  });
  const snap = JSON.parse(JSON.stringify(vm));
  buildCleanJsonResult({ templateName: "T", fields, tableResultViewModels: [vm] });
  buildMarkdownReport({ fields, processingTime: 1.0, tableResultViewModels: [vm] });
  expect(JSON.stringify(vm) === JSON.stringify(snap),
    "case7 mutation: VM not mutated by either builder");
}

// ---------------------------------------------------------------------------
// 6. Existing Clean JSON v1 fixture runner — must still PASS
// ---------------------------------------------------------------------------
try {
  execSync("node tmp/check_clean_json_v1_fixtures_js.mjs", {
    cwd: ROOT, stdio: "ignore",
  });
  ok(`Clean JSON v1 fixture runner: PASS`);
} catch (err) {
  fail(`Clean JSON v1 fixture runner FAILED — backward compat broken`);
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
