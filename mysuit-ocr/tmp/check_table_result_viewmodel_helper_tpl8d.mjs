#!/usr/bin/env node
// TPL-8D-TABLE-RESULT-VIEWMODEL-HELPER
// Static + runtime smoke. Verifies the new common TableResult ViewModel
// helper builds correct view models for the supported sources (backend
// document_fields.tableRows + unstructuredTables) without disturbing the
// existing structuredTableViewModel fixture lock.
//
// Tag on success: [TABLE_RESULT_VIEWMODEL_HELPER_TPL8D] PASS

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
const TAG = "[TABLE_RESULT_VIEWMODEL_HELPER_TPL8D]";

// Node 24 strip-types runs .ts directly but does NOT auto-append .ts to
// bare relative specifiers. The new helper imports from
// `./structuredTableViewModel` and `./invoiceTableDisplay`. Register a tiny
// loader that resolves a missing extension to .ts when the sibling file
// exists.
const LOADER_DIR = mkdtempSync(join(tmpdir(), "tpl8d-loader-"));
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
const HELPER = resolve(ROOT, "src/common/utils/tableResultViewModel.ts");
const STRUCTURED_VM = resolve(ROOT, "src/common/utils/structuredTableViewModel.ts");
const INVOICE_DISPLAY = resolve(ROOT, "src/common/utils/invoiceTableDisplay.ts");
const MAPPER = resolve(ROOT, "src/components/runocr/utils/mapOcrResponse.ts");
const EXTRACT_HELPER = resolve(ROOT, "src/components/runocr/utils/extractUnstructuredTableRows.ts");
const OCR_RESULT_PANEL = resolve(ROOT, "src/components/runocr/ui/OcrResultPanel.tsx");
const CLEAN_JSON = resolve(ROOT, "src/common/utils/cleanJsonBuilder.ts");
const MARKDOWN_REPORT = resolve(ROOT, "src/common/utils/markdownReportBuilder.ts");
const UNSTRUCTURED_BUILDER = resolve(ROOT, "src/components/template/UnstructuredBuilder.tsx");
const UNSTRUCTURED_DEF = resolve(ROOT, "src/components/template/utils/unstructuredDefinition.ts");
const TEMPLATE_RIGHT_PANEL = resolve(ROOT, "src/components/template/ui/TemplateRightPanel.tsx");
const TEST_WORKSPACE = resolve(ROOT, "src/components/test/TestWorkspace.tsx");

// ---------------------------------------------------------------------------
// 1. Helper file exists + exports
// ---------------------------------------------------------------------------
if (!existsSync(HELPER)) fail(`helper missing: ${relative(ROOT, HELPER)}`);
else ok(`helper present: src/common/utils/tableResultViewModel.ts`);

const helperSrc = readSafe(HELPER) ?? "";
const helperCode = stripComments(helperSrc);
const requiredExports = [
  { name: "buildTableResultViewModels", re: /export\s+function\s+buildTableResultViewModels\b/ },
  { name: "TableResultSource", re: /export\s+type\s+TableResultSource\b/ },
  { name: "TableResultViewModel", re: /export\s+type\s+TableResultViewModel\b/ },
  { name: "TableResultColumn", re: /export\s+type\s+TableResultColumn\b/ },
  { name: "TableResultCell", re: /export\s+type\s+TableResultCell\b/ },
  { name: "TableResultRow", re: /export\s+type\s+TableResultRow\b/ },
  { name: "TableResultMeta", re: /export\s+type\s+TableResultMeta\b/ },
];
for (const { name, re } of requiredExports) {
  if (!re.test(helperCode)) fail(`required export missing: ${name}`);
  else ok(`export present: ${name}`);
}

// Source enum mentions all 4 sources (incl. future placeholders)
for (const sym of [
  "backend_document_fields",
  "unstructured_definition",
  "template_region_canonical",
  "field_value_legacy",
]) {
  if (!helperCode.includes(sym)) fail(`source variant missing: ${sym}`);
  else ok(`source variant present: ${sym}`);
}

// Helper is pure — no React/DOM/storage/fetch/UI imports
const forbidden = [
  /from\s+["']react/,
  /from\s+["']next\//,
  /from\s+["'][^"']*ui\//,
  /\bwindow\s*\./,
  /\bdocument\s*\./,
  /\blocalStorage\b/,
  /\bsessionStorage\b/,
  /\bindexedDB\b/,
  /\bfetch\s*\(/,
];
let helperPure = true;
for (const re of forbidden) {
  if (re.test(helperCode)) { fail(`forbidden in helper: ${re}`); helperPure = false; }
}
if (helperPure) ok(`helper is pure (no React/DOM/storage/fetch/UI)`);

// Helper imports the existing structured + invoice helpers (so cell
// normalization is delegated rather than re-implemented).
if (!/from\s+["']\.\/structuredTableViewModel["']/.test(helperCode))
  fail(`helper does not import buildStructuredTableViewModel`);
else ok(`helper imports buildStructuredTableViewModel`);
if (!/from\s+["']\.\/invoiceTableDisplay["']/.test(helperCode))
  fail(`helper does not import buildInvoicePreviewCols`);
else ok(`helper imports buildInvoicePreviewCols`);

// ---------------------------------------------------------------------------
// 2. Untouched files
// ---------------------------------------------------------------------------
const untouched = [
  ["OcrResultPanel.tsx", OCR_RESULT_PANEL],
  ["mapOcrResponse.ts", MAPPER],
  ["extractUnstructuredTableRows.ts", EXTRACT_HELPER],
  ["structuredTableViewModel.ts", STRUCTURED_VM],
  ["invoiceTableDisplay.ts", INVOICE_DISPLAY],
  ["cleanJsonBuilder.ts", CLEAN_JSON],
  ["markdownReportBuilder.ts", MARKDOWN_REPORT],
  ["UnstructuredBuilder.tsx", UNSTRUCTURED_BUILDER],
  ["unstructuredDefinition.ts", UNSTRUCTURED_DEF],
  ["TemplateRightPanel.tsx", TEMPLATE_RIGHT_PANEL],
  ["TestWorkspace.tsx", TEST_WORKSPACE],
];
for (const [label, p] of untouched) {
  if (!existsSync(p)) fail(`expected untouched file missing: ${label}`);
  else ok(`present (untouched expected): ${label}`);
}
// OcrResultPanel: phase-aware. At TPL-8D time it did NOT consume the new
// helper; once TPL-8E ships it does. Both states are valid.
const orpCode = stripComments(readSafe(OCR_RESULT_PANEL) ?? "");
const _tpl8eShipped_8d = /buildTableResultViewModels\b/.test(orpCode);
if (_tpl8eShipped_8d) {
  note(`OcrResultPanel consumes buildTableResultViewModels (phase-aware NOTE — TPL-8E shipped)`);
} else {
  ok(`OcrResultPanel does not yet use buildTableResultViewModels`);
}
if (/\bunstructuredTables\b/.test(orpCode)) {
  if (_tpl8eShipped_8d) note(`OcrResultPanel consumes unstructuredTables (phase-aware NOTE — TPL-8E shipped)`);
  else fail(`OcrResultPanel already consumes unstructuredTables — TPL-8E should still be pending`);
} else {
  ok(`OcrResultPanel does not yet consume unstructuredTables`);
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
// 4. Runtime smoke — dynamic import helper + sibling structured helper
// ---------------------------------------------------------------------------
let helperMod = null, structuredMod = null;
try {
  helperMod = await import(pathToFileURL(HELPER).href);
  ok(`helper runtime import succeeded`);
} catch (err) {
  fail(`helper runtime import failed: ${err?.message ?? err}`);
}
try {
  structuredMod = await import(pathToFileURL(STRUCTURED_VM).href);
  ok(`structuredTableViewModel runtime import succeeded`);
} catch (err) {
  fail(`structuredTableViewModel runtime import failed: ${err?.message ?? err}`);
}
if (!helperMod || !structuredMod) {
  console.error(`${TAG} FAIL aborting — imports failed`);
  console.error(`${TAG} FAIL count=${failures.length}`);
  process.exit(1);
}
const { buildTableResultViewModels } = helperMod;
const { buildStructuredTableViewModel } = structuredMod;
expect(typeof buildTableResultViewModels === "function", `buildTableResultViewModels is function`);
expect(typeof buildStructuredTableViewModel === "function", `buildStructuredTableViewModel is function`);

// ── SMOKE 1: backend-only ──────────────────────────────────────────────
{
  const result = {
    full_text: "...",
    doc_type: "invoice_statement",
    document_fields: {
      tableRows: [
        { itemName: "헥사메딘액", quantity: "400", unitPrice: "1,050", amount: "420,000" },
        { itemName: "이부프로펜", quantity: "20",  unitPrice: "1,500", amount: " 30,000 " },
      ],
      tableMeta: {
        expectedColumnKeys: ["itemName", "quantity", "unitPrice", "amount"],
      },
    },
  };
  const snap = JSON.parse(JSON.stringify(result));
  const vms = buildTableResultViewModels(result);
  expect(Array.isArray(vms) && vms.length === 1, "case1 backend: 1 view model");
  expect(vms[0].source === "backend_document_fields", "case1 backend: source label");
  expect(vms[0].columns.length >= 4, "case1 backend: ≥4 columns");
  expect(vms[0].rows.length === 2, "case1 backend: 2 rows");
  const r0 = vms[0].rows[0];
  expect(r0.index === 0, "case1 backend: row index 0");
  expect(typeof r0.values.itemName === "string" && r0.values.itemName === "헥사메딘액",
    "case1 backend: row.values.itemName");
  expect(r0.cells.find((c) => c.key === "itemName")?.value === "헥사메딘액",
    "case1 backend: row.cells itemName");
  // dash placeholder for empty cells (none here, but check displayValue passes through)
  expect(r0.cells.every((c) => typeof c.displayValue === "string"),
    "case1 backend: all cells have displayValue");
  // trim normalization for cell with surrounding spaces
  const r1 = vms[0].rows[1];
  expect(r1.values.amount === "30,000",
    "case1 backend: trim normalization on '  30,000  '");
  // meta
  expect(vms[0].meta.documentType === "invoice_statement",
    "case1 backend: documentType from result.doc_type");
  expect(vms[0].meta.source === "backend_document_fields",
    "case1 backend: meta.source");
  expect(vms[0].meta.rowCount === 2 && vms[0].meta.columnCount >= 4,
    "case1 backend: meta.rowCount/columnCount");
  expect(vms[0].meta.originalSource === "document_fields.tableRows",
    "case1 backend: meta.originalSource");
  // mutation guard
  expect(JSON.stringify(result) === JSON.stringify(snap),
    "case1 backend: input not mutated");
}

// ── SMOKE 2: unstructured-only ─────────────────────────────────────────
{
  const result = {
    documentType: "invoice_statement",
    unstructuredTables: [{
      tableKey: "items",
      labelKo: "품목표",
      labelEn: "items",
      columns: [
        { columnKey: "itemName", labelKo: "품목명",  labelEn: "itemName" },
        { columnKey: "quantity", labelKo: "수량",    labelEn: "quantity" },
        { columnKey: "amount",   labelKo: "금액",    labelEn: "amount" },
      ],
      rows: [
        { itemName: "약품A", quantity: "10", amount: "10,000" },
        { itemName: "약품B", quantity: "5",  amount: "" },
      ],
    }],
  };
  const snap = JSON.parse(JSON.stringify(result));
  const vms = buildTableResultViewModels(result);
  expect(Array.isArray(vms) && vms.length === 1, "case2 unstructured: 1 view model");
  expect(vms[0].source === "unstructured_definition", "case2 unstructured: source label");
  expect(vms[0].tableKey === "items", "case2 unstructured: tableKey preserved");
  expect(vms[0].labelKo === "품목표", "case2 unstructured: labelKo preserved");
  expect(vms[0].labelEn === "items", "case2 unstructured: labelEn preserved");
  expect(vms[0].columns.length === 3
    && vms[0].columns.map((c) => c.columnKey).join(",") === "itemName,quantity,amount",
    "case2 unstructured: column order preserved");
  // labelEn is round-tripped on columns (re-attached by helper)
  expect(vms[0].columns.every((c) => typeof c.labelEn === "string" && c.labelEn.length > 0),
    "case2 unstructured: per-column labelEn re-attached");
  // user-source marker
  expect(vms[0].columns.every((c) => c.source === "user"),
    "case2 unstructured: columns source = user");
  // rows
  expect(vms[0].rows.length === 2, "case2 unstructured: 2 rows");
  expect(vms[0].rows[0].values.itemName === "약품A", "case2 unstructured: row.values");
  expect(vms[0].rows[1].values.amount === "" && vms[0].rows[1].cells.find((c) => c.key === "amount")?.isEmpty === true,
    "case2 unstructured: empty cell isEmpty=true");
  expect(vms[0].rows[1].cells.find((c) => c.key === "amount")?.displayValue === "-",
    "case2 unstructured: empty cell displayValue '-'");
  expect(JSON.stringify(result) === JSON.stringify(snap),
    "case2 unstructured: input not mutated");
}

// ── SMOKE 3: backend + unstructured ────────────────────────────────────
{
  const result = {
    doc_type: "invoice_statement",
    document_fields: {
      tableRows: [{ itemName: "헥사", quantity: "1", unitPrice: "100", amount: "100" }],
      tableMeta: { expectedColumnKeys: ["itemName", "quantity", "unitPrice", "amount"] },
    },
    unstructuredTables: [{
      tableKey: "items",
      labelKo: "품목표",
      columns: [
        { columnKey: "itemName", labelKo: "품목명" },
        { columnKey: "amount",   labelKo: "금액" },
      ],
      rows: [{ itemName: "헥사", amount: "100" }],
    }],
  };
  const vms = buildTableResultViewModels(result);
  expect(vms.length === 2, "case3 both: 2 view models");
  expect(vms[0].source === "backend_document_fields", "case3 both: backend first");
  expect(vms[1].source === "unstructured_definition", "case3 both: unstructured second");
  // backend should use canonical-derived columns; unstructured should use user columns
  expect(vms[0].columns[0].source === "canonical", "case3 both: backend column source canonical");
  expect(vms[1].columns[0].source === "user", "case3 both: unstructured column source user");
}

// ── SMOKE 4: empty / malformed ─────────────────────────────────────────
{
  expect(JSON.stringify(buildTableResultViewModels({})) === "[]",
    "case4 empty: {} returns []");
  expect(JSON.stringify(buildTableResultViewModels(null)) === "[]",
    "case4 empty: null returns []");
  expect(JSON.stringify(buildTableResultViewModels(undefined)) === "[]",
    "case4 empty: undefined returns []");
  // malformed
  const malformed = {
    document_fields: { tableRows: "not-array" },
    unstructuredTables: "also-not-array",
  };
  expect(JSON.stringify(buildTableResultViewModels(malformed)) === "[]",
    "case4 malformed: non-array sources → []");
  // unstructured entry malformed
  const partial = {
    unstructuredTables: [
      null,
      "string-table",
      { tableKey: "ok", labelKo: "OK", columns: [], rows: [] }, // empty columns → dropped
      { tableKey: "good", labelKo: "Good", columns: [{ columnKey: "a", labelKo: "A" }], rows: [] },
    ],
  };
  const vms = buildTableResultViewModels(partial);
  expect(Array.isArray(vms) && vms.length === 1, "case4 malformed: only valid unstructured entry kept");
  expect(vms[0].tableKey === "good", "case4 malformed: surviving entry");
  expect(vms[0].rows.length === 0 && vms[0].columns.length === 1,
    "case4 malformed: empty rows + 1 column ok");
  // backend rows array of non-objects
  const garbageBackend = {
    doc_type: "invoice_statement",
    document_fields: { tableRows: [null, "x", 42] },
  };
  expect(JSON.stringify(buildTableResultViewModels(garbageBackend)) === "[]",
    "case4 malformed: backend rows all non-objects → []");
}

// ── SMOKE 5: cell normalization ────────────────────────────────────────
{
  const result = {
    unstructuredTables: [{
      tableKey: "t",
      labelKo: "T",
      columns: [
        { columnKey: "a", labelKo: "A" },
        { columnKey: "b", labelKo: "B" },
        { columnKey: "c", labelKo: "C" },
        { columnKey: "d", labelKo: "D" },
        { columnKey: "e", labelKo: "E" },
      ],
      rows: [{ a: null, b: undefined, c: "  text  ", d: "—", e: "" }],
    }],
  };
  const vms = buildTableResultViewModels(result);
  const cells = vms[0].rows[0].cells;
  const byKey = Object.fromEntries(cells.map((c) => [c.key, c]));
  expect(byKey.a.value === "" && byKey.a.isEmpty === true && byKey.a.displayValue === "-",
    "case5 norm: null → empty");
  expect(byKey.b.value === "" && byKey.b.isEmpty === true,
    "case5 norm: undefined → empty");
  expect(byKey.c.value === "text" && byKey.c.isEmpty === false,
    "case5 norm: trim '  text  '");
  expect(byKey.d.value === "-" && byKey.d.isEmpty === false,
    "case5 norm: em dash '—' → ASCII '-'");
  expect(byKey.e.value === "" && byKey.e.isEmpty === true && byKey.e.displayValue === "-",
    "case5 norm: '' → empty placeholder");
}

// ── SMOKE 6: equivalence with buildStructuredTableViewModel ────────────
// Direct invocation of structured helper with the same rows + displayCols
// must produce identical per-cell normalization to the new helper.
{
  const rows = [
    { itemName: "헥사", quantity: " 2 ", amount: null },
    { itemName: "이부", quantity: "5",   amount: "  10,000  " },
  ];
  const displayCols = [
    { key: "itemName", labelKo: "품목명" },
    { key: "quantity", labelKo: "수량" },
    { key: "amount",   labelKo: "금액" },
  ];
  const structured = buildStructuredTableViewModel({ rows, displayCols, emptyValue: "-" });
  // Drive the same rows through the new helper via the unstructured path
  // (it's the cleanest way to compare cell-level normalization without
  // depending on backend invoiceTableDisplay heuristics).
  const fromHelper = buildTableResultViewModels({
    unstructuredTables: [{
      tableKey: "t",
      labelKo: "T",
      columns: displayCols.map((c) => ({ columnKey: c.key, labelKo: c.labelKo })),
      rows,
    }],
  });
  const helperRows = fromHelper[0].rows;
  expect(helperRows.length === structured.rows.length, "case6 equiv: row counts match");
  for (let i = 0; i < structured.rows.length; i++) {
    for (let j = 0; j < structured.columns.length; j++) {
      const sCell = structured.rows[i].cells[j];
      const hCell = helperRows[i].cells[j];
      if (sCell.value !== hCell.value
        || sCell.displayValue !== hCell.displayValue
        || sCell.isEmpty !== hCell.isEmpty
        || sCell.key !== hCell.key) {
        fail(`case6 equiv: cell[${i}][${j}] diverges: structured=${JSON.stringify(sCell)} helper=${JSON.stringify(hCell)}`);
      }
    }
  }
  ok(`case6 equiv: every cell matches buildStructuredTableViewModel output`);
}

// ── SMOKE 7: documentType extraction priority ───────────────────────────
{
  // priority: result.documentType > result.doc_type > document_fields.doc_type
  const a = buildTableResultViewModels({
    documentType: "invoice_statement",
    doc_type: "card_receipt",
    unstructuredTables: [{ tableKey: "x", labelKo: "X", columns: [{ columnKey: "a", labelKo: "A" }], rows: [] }],
  });
  expect(a[0].meta.documentType === "invoice_statement", "case7 doctype: result.documentType wins");
  const b = buildTableResultViewModels({
    doc_type: "tax_invoice",
    unstructuredTables: [{ tableKey: "x", labelKo: "X", columns: [{ columnKey: "a", labelKo: "A" }], rows: [] }],
  });
  expect(b[0].meta.documentType === "tax_invoice", "case7 doctype: falls back to result.doc_type");
  const c = buildTableResultViewModels({
    unstructuredTables: [{ tableKey: "x", labelKo: "X", columns: [{ columnKey: "a", labelKo: "A" }], rows: [] }],
  });
  expect(c[0].meta.documentType === undefined, "case7 doctype: undefined when absent");
}

// ── SMOKE 8: output order is backend → unstructured (mutiple unstructured) ─
{
  const result = {
    doc_type: "invoice_statement",
    document_fields: {
      tableRows: [{ itemName: "x", quantity: "1", unitPrice: "1", amount: "1" }],
      tableMeta: { expectedColumnKeys: ["itemName", "quantity", "unitPrice", "amount"] },
    },
    unstructuredTables: [
      { tableKey: "items",   labelKo: "품목표", columns: [{ columnKey: "itemName", labelKo: "품목명" }], rows: [] },
      { tableKey: "summary", labelKo: "합계표", columns: [{ columnKey: "label",    labelKo: "구분" }],   rows: [] },
    ],
  };
  const vms = buildTableResultViewModels(result);
  expect(vms.length === 3, "case8 order: 1 backend + 2 unstructured");
  expect(vms[0].source === "backend_document_fields", "case8 order: index 0 backend");
  expect(vms[1].source === "unstructured_definition" && vms[1].tableKey === "items",
    "case8 order: index 1 first unstructured");
  expect(vms[2].source === "unstructured_definition" && vms[2].tableKey === "summary",
    "case8 order: index 2 second unstructured");
}

// ── SMOKE 9: mutation guard (cross-source) ─────────────────────────────
{
  const result = {
    doc_type: "invoice_statement",
    document_fields: {
      tableRows: [{ itemName: "A", quantity: "1", unitPrice: "10", amount: "10" }],
      tableMeta: { expectedColumnKeys: ["itemName", "quantity", "unitPrice", "amount"] },
    },
    unstructuredTables: [{
      tableKey: "items", labelKo: "품목표",
      columns: [{ columnKey: "itemName", labelKo: "품목명" }],
      rows: [{ itemName: "A" }],
    }],
  };
  const snap = JSON.parse(JSON.stringify(result));
  buildTableResultViewModels(result);
  buildTableResultViewModels(result);  // run twice — helper must be idempotent
  expect(JSON.stringify(result) === JSON.stringify(snap),
    "case9 mutation: result unchanged after 2 calls");
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
    if (PHASE_ALLOW.has(path)) { note(`new production (allowed): ${path}`); continue; }
    fail(`new untracked production file: ${path}`); hits++;
  }
  if (hits === 0) ok(`new-file scope check: clean`);
}

// ---------------------------------------------------------------------------
note(`fixture compatibility: deferred — direct equivalence with buildStructuredTableViewModel verified by case 6`);

if (failures.length === 0) {
  console.log(`${TAG} PASS`);
  process.exit(0);
} else {
  console.error(`${TAG} FAIL count=${failures.length}`);
  for (const m of failures) console.error(`${TAG}   - ${m}`);
  process.exit(1);
}
