#!/usr/bin/env node
// TPL-8B-UNSTRUCTURED-INVOICE-TABLE-ROW-PROJECTION
// Static + runtime smoke for the row projection helper and mapOcrResponse
// integration. Tag on success:
//   [UNSTRUCTURED_INVOICE_TABLE_ROW_PROJECTION_TPL8B] PASS

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
const TAG = "[UNSTRUCTURED_INVOICE_TABLE_ROW_PROJECTION_TPL8B]";

// Node 24 strip-types supports .ts imports, but ESM resolution does NOT
// auto-append the .ts extension for bare/relative specifiers. mapOcrResponse
// uses the project convention `from "./extractUnstructuredTableRows"` (no
// extension) which Next.js bundler resolves at build time. To let this smoke
// import mapOcrResponse.ts directly, we register a tiny loader that appends
// .ts when a bare relative import points to a sibling .ts file.
const LOADER_DIR = mkdtempSync(join(tmpdir(), "tpl8b-loader-"));
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
const HELPER = resolve(ROOT, "src/components/runocr/utils/extractUnstructuredTableRows.ts");
const MAPPER = resolve(ROOT, "src/components/runocr/utils/mapOcrResponse.ts");
const BUILDER = resolve(ROOT, "src/components/template/UnstructuredBuilder.tsx");
const DEFINITION = resolve(ROOT, "src/components/template/utils/unstructuredDefinition.ts");
const TEMPLATE_RIGHT_PANEL = resolve(ROOT, "src/components/template/ui/TemplateRightPanel.tsx");
const OCR_CANVAS_PANE = resolve(ROOT, "src/common/ui/OcrCanvasPane.tsx");
const OCR_RESULT_PANEL = resolve(ROOT, "src/components/runocr/ui/OcrResultPanel.tsx");
const RUNOCR_WORKSPACE = resolve(ROOT, "src/components/runocr/RunOcrWorkspace.tsx");
const TEST_WORKSPACE = resolve(ROOT, "src/components/test/TestWorkspace.tsx");

// ---------------------------------------------------------------------------
// 1. Helper file exists
// ---------------------------------------------------------------------------
if (!existsSync(HELPER)) fail(`helper missing: ${relative(ROOT, HELPER)}`);
else ok(`helper present: src/components/runocr/utils/extractUnstructuredTableRows.ts`);

// ---------------------------------------------------------------------------
// 2. Helper exports extractUnstructuredTableRows
// ---------------------------------------------------------------------------
const helperSrc = readSafe(HELPER) ?? "";
if (!/export\s+function\s+extractUnstructuredTableRows\b/.test(helperSrc))
  fail(`extractUnstructuredTableRows export not found in helper`);
else ok(`extractUnstructuredTableRows export found`);

// Boundary: helper is pure — no React/DOM/storage/fetch/backend
const helperStripped = stripComments(helperSrc);
const forbidden = [
  /from\s+["']react["']/,
  /from\s+["']react\//,
  /from\s+["']next\//,
  /\bwindow\s*\./,
  /\bdocument\s*\./,
  /\blocalStorage\b/,
  /\bsessionStorage\b/,
  /\bindexedDB\b/,
  /\bfetch\s*\(/,
  /\bXMLHttpRequest\b/,
];
let helperPure = true;
for (const re of forbidden) {
  if (re.test(helperStripped)) { fail(`forbidden runtime/import in helper: ${re}`); helperPure = false; }
}
if (helperPure) ok(`helper is pure (no React/DOM/storage/fetch)`);

// ---------------------------------------------------------------------------
// 3. mapOcrResponse imports + uses the helper
// ---------------------------------------------------------------------------
const mapperSrc = readSafe(MAPPER) ?? "";
const mapperCode = stripComments(mapperSrc);
if (!/from\s+["']\.\/extractUnstructuredTableRows["']/.test(mapperCode))
  fail(`mapOcrResponse does not import from ./extractUnstructuredTableRows`);
else ok(`mapOcrResponse imports extractUnstructuredTableRows`);
if (!/extractUnstructuredTableRows\s*\(/.test(mapperCode))
  fail(`mapOcrResponse does not call extractUnstructuredTableRows(...)`);
else ok(`mapOcrResponse calls extractUnstructuredTableRows(...)`);

// ---------------------------------------------------------------------------
// 4. mapOcrResponse rows now use helper output (no longer literal `[]`)
// ---------------------------------------------------------------------------
// Heuristic: the unstructuredTables tables.map block should reference
// `projectedRows[idx]` (or similar) for `rows:`.
if (!/rows\s*:\s*\(?projectedRows\b/.test(mapperCode) && !/rows\s*:\s*projectedRows\b/.test(mapperCode))
  fail(`mapOcrResponse rows: ... must reference projectedRows array (helper result)`);
else ok(`mapOcrResponse rows uses projectedRows array from helper`);

// ---------------------------------------------------------------------------
// 5-9. Untouched production files (existence + invariants)
// ---------------------------------------------------------------------------
for (const [label, p] of [
  ["UnstructuredBuilder.tsx", BUILDER],
  ["unstructuredDefinition.ts", DEFINITION],
  ["TemplateRightPanel.tsx", TEMPLATE_RIGHT_PANEL],
  ["OcrCanvasPane.tsx", OCR_CANVAS_PANE],
  ["OcrResultPanel.tsx", OCR_RESULT_PANEL],
  ["RunOcrWorkspace.tsx", RUNOCR_WORKSPACE],
  ["TestWorkspace.tsx", TEST_WORKSPACE],
]) {
  if (!existsSync(p)) fail(`expected untouched file missing: ${label}`);
  else ok(`present (untouched expected): ${label}`);
}
// OcrResultPanel should not yet read result.unstructuredTables (TPL-8C territory)
const orpSrc = readSafe(OCR_RESULT_PANEL) ?? "";
if (/\bunstructuredTables\b/.test(stripComments(orpSrc)))
  fail(`OcrResultPanel must not consume unstructuredTables yet (TPL-8C)`);
else ok(`OcrResultPanel does not consume unstructuredTables (UI deferred)`);

// ---------------------------------------------------------------------------
// 10. src/lib absent + @/lib imports = 0
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
// 11. Runtime smoke — import helper + mapper via Node strip-types
// ---------------------------------------------------------------------------
let helperMod = null, mapperMod = null;
try {
  helperMod = await import(pathToFileURL(HELPER).href);
  ok(`helper runtime import succeeded`);
} catch (err) {
  fail(`helper runtime import failed: ${err?.message ?? err}`);
}
try {
  mapperMod = await import(pathToFileURL(MAPPER).href);
  ok(`mapper runtime import succeeded`);
} catch (err) {
  fail(`mapper runtime import failed: ${err?.message ?? err}`);
}
if (!helperMod || !mapperMod) {
  console.error(`${TAG} FAIL aborting — imports failed`);
  console.error(`${TAG} FAIL count=${failures.length}`);
  process.exit(1);
}
const { extractUnstructuredTableRows } = helperMod;
const { buildRunOcrResult } = mapperMod;
expect(typeof extractUnstructuredTableRows === "function", `helper export is function`);
expect(typeof buildRunOcrResult === "function", `buildRunOcrResult export is function`);

const INVOICE_BACKEND_RAW_BASE = {
  full_text: "공급자 상호: 거래처A\n총합계금액: 88000\n품목명 수량 단가 금액 ...",
  receipt_fields: { "총합계금액": "88000" },
  finance_fields: {},
  processing_time: 2.0,
  fields: [],
  doc_type: "invoice_statement",
  document_fields: {
    supplierCompany: "거래처A",
    totalAmount: "88000",
    tableRows: [
      { itemName: "아세트아미노펜",   quantity: "10", unitPrice: "1000", amount: "10000", lotNo: "A123" },
      { itemName: "이부프로펜",       quantity: "20", unitPrice: "1500", amount: "30000", lotNo: "B456" },
    ],
    tableMeta: { expectedColumnKeys: ["itemName", "quantity", "unitPrice", "amount"] },
    rowCount: 2,
    tableDetected: true,
  },
};

// ── SMOKE 1: basic invoice_statement projection ──────────────────────────
{
  const r = extractUnstructuredTableRows({
    raw: INVOICE_BACKEND_RAW_BASE,
    documentType: "invoice_statement",
    tables: [{
      tableKey: "items",
      columns: [
        { columnKey: "itemName" },
        { columnKey: "quantity" },
        { columnKey: "amount" },
      ],
    }],
  });
  expect(Array.isArray(r) && r.length === 1, "case 1 basic: returns 1 table projection");
  expect(Array.isArray(r[0]) && r[0].length === 2, "case 1 basic: 2 rows projected");
  expect(r[0][0].itemName === "아세트아미노펜", "case 1 basic: row[0].itemName");
  expect(r[0][0].quantity === "10", "case 1 basic: row[0].quantity");
  expect(r[0][0].amount === "10000", "case 1 basic: row[0].amount");
  expect(!("lotNo" in r[0][0]), "case 1 basic: only user-defined columnKey projected (lotNo excluded)");
  expect(r[0][1].itemName === "이부프로펜" && r[0][1].quantity === "20" && r[0][1].amount === "30000",
    "case 1 basic: row[1] preserved");
}

// ── SMOKE 2: mismatched columnKey → "" ───────────────────────────────────
{
  const r = extractUnstructuredTableRows({
    raw: INVOICE_BACKEND_RAW_BASE,
    documentType: "invoice_statement",
    tables: [{
      tableKey: "items",
      columns: [
        { columnKey: "itemName" },
        { columnKey: "unknownColumn" },
      ],
    }],
  });
  expect(r[0].length === 2, "case 2 mismatched: rows still produced");
  expect(r[0][0].itemName === "아세트아미노펜", "case 2 mismatched: canonical key still works");
  expect(r[0][0].unknownColumn === "", "case 2 mismatched: unknown key resolves to empty string");
  expect(typeof r[0][0].unknownColumn === "string", "case 2 mismatched: value is a string");
}

// ── SMOKE 3: empty backend rows ──────────────────────────────────────────
{
  const r = extractUnstructuredTableRows({
    raw: { ...INVOICE_BACKEND_RAW_BASE, document_fields: { ...INVOICE_BACKEND_RAW_BASE.document_fields, tableRows: [] } },
    documentType: "invoice_statement",
    tables: [{ tableKey: "items", columns: [{ columnKey: "itemName" }] }],
  });
  expect(Array.isArray(r) && r.length === 1, "case 3 empty: 1 entry returned");
  expect(Array.isArray(r[0]) && r[0].length === 0, "case 3 empty: rows []");
}

// ── SMOKE 4: two user tables — only first filled ─────────────────────────
{
  const r = extractUnstructuredTableRows({
    raw: INVOICE_BACKEND_RAW_BASE,
    documentType: "invoice_statement",
    tables: [
      { tableKey: "items",   columns: [{ columnKey: "itemName" }] },
      { tableKey: "summary", columns: [{ columnKey: "label" }, { columnKey: "value" }] },
    ],
  });
  expect(r.length === 2, "case 4 two-tables: returns 2 entries");
  expect(r[0].length === 2, "case 4 two-tables: first table filled (2 rows)");
  expect(Array.isArray(r[1]) && r[1].length === 0, "case 4 two-tables: second table rows []");
}

// ── SMOKE 5: not invoice_statement → all rows [] ─────────────────────────
{
  const r = extractUnstructuredTableRows({
    raw: INVOICE_BACKEND_RAW_BASE,
    documentType: "receipt",
    tables: [{ tableKey: "items", columns: [{ columnKey: "itemName" }] }],
  });
  expect(r.length === 1 && r[0].length === 0,
    "case 5 not-invoice: projection skipped, rows []");
}
{
  const r = extractUnstructuredTableRows({
    raw: INVOICE_BACKEND_RAW_BASE,
    documentType: "",
    tables: [{ tableKey: "items", columns: [{ columnKey: "itemName" }] }],
  });
  expect(r.length === 1 && r[0].length === 0,
    "case 5 empty-doctype: projection skipped, rows []");
}

// ── SMOKE 6: no template tables → returns [] ─────────────────────────────
{
  expect(JSON.stringify(extractUnstructuredTableRows({ raw: INVOICE_BACKEND_RAW_BASE, documentType: "invoice_statement" })) === "[]",
    "case 6 no-tables (undefined): returns []");
  expect(JSON.stringify(extractUnstructuredTableRows({ raw: INVOICE_BACKEND_RAW_BASE, documentType: "invoice_statement", tables: [] })) === "[]",
    "case 6 no-tables (empty): returns []");
}

// ── SMOKE 6b: malformed input safety ─────────────────────────────────────
{
  // raw is null
  expect(JSON.stringify(extractUnstructuredTableRows({ raw: null, documentType: "invoice_statement", tables: [{ columns: [{ columnKey: "itemName" }] }] })) === "[[]]",
    "case 6b malformed: raw null → [[]]");
  // document_fields missing
  expect(JSON.stringify(extractUnstructuredTableRows({ raw: {}, documentType: "invoice_statement", tables: [{ columns: [{ columnKey: "itemName" }] }] })) === "[[]]",
    "case 6b malformed: no document_fields → [[]]");
  // tableRows non-array
  expect(JSON.stringify(extractUnstructuredTableRows({ raw: { document_fields: { tableRows: "not-array" } }, documentType: "invoice_statement", tables: [{ columns: [{ columnKey: "itemName" }] }] })) === "[[]]",
    "case 6b malformed: tableRows non-array → [[]]");
}

// ── SMOKE 6c: input not mutated ──────────────────────────────────────────
{
  const inputCopy = JSON.parse(JSON.stringify(INVOICE_BACKEND_RAW_BASE));
  const snap = JSON.parse(JSON.stringify(inputCopy));
  const tplCopy = [{ tableKey: "items", columns: [{ columnKey: "itemName" }] }];
  const tplSnap = JSON.parse(JSON.stringify(tplCopy));
  extractUnstructuredTableRows({ raw: inputCopy, documentType: "invoice_statement", tables: tplCopy });
  expect(JSON.stringify(inputCopy) === JSON.stringify(snap),
    "case 6c mutation: raw not mutated");
  expect(JSON.stringify(tplCopy) === JSON.stringify(tplSnap),
    "case 6c mutation: tables not mutated");
}

// ── SMOKE 7: mapOcrResponse end-to-end integration ───────────────────────
{
  const tpl = {
    mode: "unstructured",
    documentType: "invoice_statement",
    info: [
      { key: "supplierCompany", labelKo: "공급자 상호",  labelEn: "supplierCompany", no: 1, order: 1 },
      { key: "totalAmount",     labelKo: "총합계금액",   labelEn: "totalAmount",     no: 2, order: 2 },
    ],
    tables: [{
      tableKey: "items",
      labelKo: "품목표",
      columns: [
        { columnKey: "itemName",  labelKo: "품목명" },
        { columnKey: "quantity",  labelKo: "수량" },
        { columnKey: "unitPrice", labelKo: "단가" },
        { columnKey: "amount",    labelKo: "금액" },
      ],
    }],
    fields: [],
    regions: [],
  };
  const invoiceRaw = {
    ...INVOICE_BACKEND_RAW_BASE,
    receipt_fields: { "총합계금액": "88000", "공급자 상호": "거래처A" },
  };
  const res = buildRunOcrResult(invoiceRaw, tpl);
  // legacy / TPL-7 invariants
  expect(Array.isArray(res.fields) && res.fields.length === 2, "case 7 integ: 2 info-derived fields");
  expect(res.fields[0].name === "공급자 상호" && res.fields[0].value === "거래처A",
    "case 7 integ: info[0] looked up");
  expect(res.fields[1].name === "총합계금액" && res.fields[1].value === "88000",
    "case 7 integ: info[1] looked up");
  expect(res.documentType === "invoice_statement", "case 7 integ: documentType attached");
  // TPL-8B: unstructuredTables[0].rows is now filled
  expect(Array.isArray(res.unstructuredTables) && res.unstructuredTables.length === 1,
    "case 7 integ: unstructuredTables length 1");
  const t0 = res.unstructuredTables[0];
  expect(t0.tableKey === "items", "case 7 integ: tableKey preserved");
  expect(Array.isArray(t0.columns) && t0.columns.length === 4,
    "case 7 integ: 4 columns preserved");
  expect(Array.isArray(t0.rows) && t0.rows.length === 2,
    "case 7 integ: 2 rows PROJECTED (TPL-8B)");
  expect(t0.rows[0].itemName === "아세트아미노펜"
      && t0.rows[0].quantity === "10"
      && t0.rows[0].unitPrice === "1000"
      && t0.rows[0].amount === "10000",
    "case 7 integ: row[0] canonical projection");
  // existing document_fields.tableRows is preserved verbatim (read-only)
  expect(Array.isArray(res.document_fields?.tableRows)
    && res.document_fields.tableRows.length === 2
    && res.document_fields.tableRows[0].lotNo === "A123",
    "case 7 integ: document_fields.tableRows unchanged");
  // legacy keys preserved
  expect(res.full_text === invoiceRaw.full_text, "case 7 integ: full_text preserved");
  expect(res.processing_time === invoiceRaw.processing_time, "case 7 integ: processing_time preserved");
}

// ── SMOKE 7b: mapOcrResponse legacy fields-only path still untouched ────
{
  const tpl = {
    mode: "unstructured",
    fields: [
      { no: 1, enField: "storeName", koField: "회사명" },
      { no: 2, enField: "bizNo",     koField: "사업자번호" },
    ],
    regions: [],
  };
  const raw = {
    full_text: "회사명: ACME\n사업자번호: 123-45-67890",
    receipt_fields: { "회사명": "ACME", "사업자번호": "123-45-67890" },
    finance_fields: {},
    processing_time: 1.0,
    fields: [],
  };
  const res = buildRunOcrResult(raw, tpl);
  expect(res.fields.length === 2, "case 7b legacy: 2 fields built");
  expect(res.fields[0].value === "ACME", "case 7b legacy: 회사명 lookup");
  expect(res.fields[1].value === "123-45-67890", "case 7b legacy: 사업자번호 lookup");
  expect(!("documentType" in res), "case 7b legacy: no documentType injected");
  expect(!("unstructuredTables" in res), "case 7b legacy: no unstructuredTables added");
}

// ── SMOKE 7c: mapOcrResponse invoice_statement w/ tables but doc_type not set on template ─
{
  // user did NOT set template.documentType — even though raw has tableRows,
  // projection must NOT fire (TPL-8B gate on template.documentType).
  const tpl = {
    mode: "unstructured",
    info: [{ key: "supplierCompany", labelKo: "공급자", labelEn: "supplierCompany", no: 1, order: 1 }],
    tables: [{
      tableKey: "items",
      columns: [{ columnKey: "itemName" }, { columnKey: "quantity" }],
    }],
    regions: [],
  };
  const res = buildRunOcrResult(INVOICE_BACKEND_RAW_BASE, tpl);
  expect(Array.isArray(res.unstructuredTables) && res.unstructuredTables.length === 1,
    "case 7c gate: unstructuredTables still attached");
  expect(Array.isArray(res.unstructuredTables[0].rows) && res.unstructuredTables[0].rows.length === 0,
    "case 7c gate: rows = [] when template.documentType is missing");
}

// ── SMOKE 7d: number/null/bool coercion in projection ────────────────────
{
  const raw = {
    ...INVOICE_BACKEND_RAW_BASE,
    document_fields: {
      tableRows: [
        { itemName: "ItemX", quantity: 5, unitPrice: 1000, amount: null, expiryDate: true },
      ],
    },
  };
  const tpl = {
    mode: "unstructured",
    documentType: "invoice_statement",
    tables: [{
      tableKey: "items",
      columns: [
        { columnKey: "itemName" },
        { columnKey: "quantity" },
        { columnKey: "unitPrice" },
        { columnKey: "amount" },
        { columnKey: "expiryDate" },
      ],
    }],
    regions: [],
  };
  const res = buildRunOcrResult(raw, tpl);
  const row = res.unstructuredTables[0].rows[0];
  expect(row.itemName === "ItemX",  "case 7d coerce: string preserved");
  expect(row.quantity === "5",       "case 7d coerce: number → string");
  expect(row.unitPrice === "1000",   "case 7d coerce: number → string");
  expect(row.amount === "",          "case 7d coerce: null → empty string");
  expect(row.expiryDate === "true",  "case 7d coerce: boolean → string");
}

// ---------------------------------------------------------------------------
// 12. New-file scope check
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
