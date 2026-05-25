#!/usr/bin/env node
// TPL-7-UNSTRUCTURED-RUNOCR-INFO-TABLE-INTEGRATION
// Static + runtime smoke. Verifies mapOcrResponse.ts now handles
// unstructured template.info / template.tables / template.documentType
// without breaking the legacy fields-only path.
// Tag on success: [UNSTRUCTURED_RUNOCR_INFO_TABLE_INTEGRATION_TPL7] PASS

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
const TAG = "[UNSTRUCTURED_RUNOCR_INFO_TABLE_INTEGRATION_TPL7]";

// TPL-8B added a runtime relative import to mapOcrResponse.ts (the new
// extractUnstructuredTableRows helper). Node ESM strip-types does not
// auto-append `.ts` to bare relative specifiers, so we register a small
// loader hook before any dynamic import. This keeps the TPL-7 smoke
// evergreen across later phases that add sibling .ts helpers.
const LOADER_DIR = mkdtempSync(join(tmpdir(), "tpl7-loader-"));
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
const MAPPER = resolve(ROOT, "src/components/runocr/utils/mapOcrResponse.ts");
const BUILDER = resolve(ROOT, "src/components/template/UnstructuredBuilder.tsx");
const DEFINITION = resolve(ROOT, "src/components/template/utils/unstructuredDefinition.ts");
const TEMPLATE_RIGHT_PANEL = resolve(ROOT, "src/components/template/ui/TemplateRightPanel.tsx");
const OCR_CANVAS_PANE = resolve(ROOT, "src/common/ui/OcrCanvasPane.tsx");
const OCR_RESULT_PANEL = resolve(ROOT, "src/components/runocr/ui/OcrResultPanel.tsx");
const RUNOCR_WORKSPACE = resolve(ROOT, "src/components/runocr/RunOcrWorkspace.tsx");
const TEST_WORKSPACE = resolve(ROOT, "src/components/test/TestWorkspace.tsx");

// ---------------------------------------------------------------------------
// 1. mapOcrResponse.ts present + modified
// ---------------------------------------------------------------------------
if (!existsSync(MAPPER)) fail(`mapOcrResponse.ts missing`);
else ok(`mapOcrResponse.ts present`);
const mapperSrc = readSafe(MAPPER) ?? "";
const mapperCode = stripComments(mapperSrc);

// ---------------------------------------------------------------------------
// 2-3. Legacy template.fields path must still be present
// ---------------------------------------------------------------------------
if (!/template\?\.fields\b|template\.fields\b/.test(mapperCode))
  fail(`legacy template.fields reference missing in mapOcrResponse`);
else ok(`legacy template.fields reference present`);
if (!/legacyFields|template\?\.fields\s*\?\?/.test(mapperCode))
  fail(`legacy fields fallback chain not detected`);
else ok(`legacy fields fallback present`);

// ---------------------------------------------------------------------------
// 4. New info handling
// ---------------------------------------------------------------------------
if (!/\btemplate\?\.info\b|\btemplate\.info\b/.test(mapperCode))
  fail(`template.info reference missing — info handling not wired`);
else ok(`template.info handling present`);
if (!/Array\.isArray\(\s*template\?\.info\s*\)/.test(mapperCode))
  fail(`template.info Array.isArray guard missing`);
else ok(`template.info Array.isArray guard present`);

// ---------------------------------------------------------------------------
// 5. documentType handling
// ---------------------------------------------------------------------------
if (!/documentType\?\s*:\s*string/.test(mapperCode))
  fail(`BuildRunOcrResultTemplate.documentType?: string declaration missing`);
else ok(`documentType?: string declared on template type`);
if (!/template\?\.documentType\b/.test(mapperCode))
  fail(`template.documentType not consumed in mapper logic`);
else ok(`template.documentType consumed`);

// ---------------------------------------------------------------------------
// 6. tables handling
// ---------------------------------------------------------------------------
if (!/tables\?\s*:\s*Array/.test(mapperCode))
  fail(`BuildRunOcrResultTemplate.tables?: Array<...> declaration missing`);
else ok(`tables?: Array<...> declared on template type`);
if (!/template\?\.tables\b|template\.tables\b/.test(mapperCode))
  fail(`template.tables not consumed in mapper logic`);
else ok(`template.tables consumed`);
if (!/unstructuredTables\b/.test(mapperCode))
  fail(`result metadata key "unstructuredTables" missing`);
else ok(`result attaches "unstructuredTables" metadata`);

// ---------------------------------------------------------------------------
// 7. Untouched UI / helper / test boundaries
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
// OcrResultPanel: structural sanity — must NOT have gained tables-row UI yet
const orpSrc = readSafe(OCR_RESULT_PANEL) ?? "";
if (/\bunstructuredTables\b/.test(stripComments(orpSrc)))
  fail(`OcrResultPanel must not consume unstructuredTables yet (TPL-7 metadata-only)`);
else ok(`OcrResultPanel does not consume unstructuredTables (UI deferred)`);

// ---------------------------------------------------------------------------
// 8. src/lib absent + @/lib imports = 0
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
// 9. Runtime smoke — import mapOcrResponse.ts via Node strip-types.
//    `import type` statements for OcrResult/OcrFieldResult are stripped, so
//    the .tsx UI module is never resolved at runtime.
// ---------------------------------------------------------------------------
let mod = null;
try {
  mod = await import(pathToFileURL(MAPPER).href);
  ok(`runtime import of mapOcrResponse.ts succeeded`);
} catch (err) {
  fail(`runtime import of mapOcrResponse.ts failed: ${err?.message ?? err}`);
}
if (!mod) {
  console.error(`${TAG} FAIL aborting smoke — mapper unimportable`);
  console.error(`${TAG} FAIL count=${failures.length}`);
  process.exit(1);
}
const { buildRunOcrResult } = mod;
expect(typeof buildRunOcrResult === "function", `buildRunOcrResult is exported`);

// Fixture builders
const RECEIPT_RAW = {
  full_text: "회사명: ACME\n사업자번호: 123-45-67890\n총합계금액: 12000",
  receipt_fields: {
    "회사명": "ACME",
    "사업자번호": "123-45-67890",
    "tel": "02-1111-2222",
    "총합계금액": "12000",
  },
  finance_fields: {},
  processing_time: 1.0,
  fields: [],
};

// ---------------------------------------------------------------------------
// SMOKE CASE 1 — Legacy fields-only template path (must be unchanged)
// ---------------------------------------------------------------------------
{
  const tpl = {
    mode: "unstructured",
    fields: [
      { no: 1, enField: "storeName", koField: "회사명" },
      { no: 2, enField: "bizNo",     koField: "사업자번호" },
      { no: 3, enField: "tel",       koField: "전화번호" },
      { no: 4, enField: "totalAmount", koField: "총합계금액" },
    ],
    regions: [],
  };
  const res = buildRunOcrResult(RECEIPT_RAW, tpl);
  expect(Array.isArray(res.fields) && res.fields.length === 4,
    "case1 legacy: 4 fields returned");
  expect(res.fields[0].name === "회사명" && res.fields[0].value === "ACME",
    "case1 legacy: 회사명 lookup");
  expect(res.fields[1].name === "사업자번호" && res.fields[1].value === "123-45-67890",
    "case1 legacy: 사업자번호 lookup");
  expect(res.fields[2].name === "전화번호" && res.fields[2].value === "02-1111-2222",
    "case1 legacy: 전화번호 → tel alias lookup");
  expect(res.fields[3].name === "총합계금액" && res.fields[3].value === "12000",
    "case1 legacy: 총합계금액 lookup");
  expect(!("documentType" in res), "case1 legacy: no documentType attached");
  expect(!("unstructuredTables" in res), "case1 legacy: no unstructuredTables attached");
  // Pre-TPL-7 baseline keys preserved
  expect(res.full_text === RECEIPT_RAW.full_text, "case1 legacy: full_text preserved");
  expect(res.processing_time === RECEIPT_RAW.processing_time,
    "case1 legacy: processing_time preserved");
}

// ---------------------------------------------------------------------------
// SMOKE CASE 2 — info-only (TPL-5 builder save w/o documentType / tables)
// ---------------------------------------------------------------------------
{
  const tpl = {
    mode: "unstructured",
    info: [
      { key: "storeName",   labelKo: "회사명",      labelEn: "storeName",   no: 1, order: 1 },
      { key: "bizNo",       labelKo: "사업자번호",  labelEn: "bizNo",       no: 2, order: 2 },
      { key: "totalAmount", labelKo: "총합계금액",  labelEn: "totalAmount", no: 3, order: 3 },
    ],
    tables: [],
    fields: [
      { no: 1, enField: "storeName",   koField: "회사명" },
      { no: 2, enField: "bizNo",       koField: "사업자번호" },
      { no: 3, enField: "totalAmount", koField: "총합계금액" },
    ],
    regions: [],
  };
  const res = buildRunOcrResult(RECEIPT_RAW, tpl);
  expect(Array.isArray(res.fields) && res.fields.length === 3,
    "case2 info-only: 3 fields from info");
  expect(res.fields[0].name === "회사명" && res.fields[0].value === "ACME",
    "case2 info-only: info[0] labelKo → 회사명 looked up");
  expect(res.fields[1].name === "사업자번호" && res.fields[1].value === "123-45-67890",
    "case2 info-only: info[1] looked up");
  expect(!("documentType" in res), "case2 info-only: no documentType attached");
  expect(!("unstructuredTables" in res), "case2 info-only: tables empty → no metadata attached");
}

// ---------------------------------------------------------------------------
// SMOKE CASE 3 — info + tables + documentType (invoice_statement)
// ---------------------------------------------------------------------------
{
  const tpl = {
    mode: "unstructured",
    documentType: "invoice_statement",
    info: [
      { key: "supplierCompany", labelKo: "공급자 상호",  labelEn: "supplierCompany", no: 1, order: 1 },
      { key: "totalAmount",     labelKo: "총합계금액",   labelEn: "totalAmount",     no: 2, order: 2 },
    ],
    tables: [
      {
        tableKey: "items",
        labelKo: "품목표",
        labelEn: "items",
        columns: [
          { columnKey: "itemName",  labelKo: "품목명",  labelEn: "itemName" },
          { columnKey: "quantity",  labelKo: "수량",    labelEn: "quantity" },
          { columnKey: "unitPrice", labelKo: "단가",    labelEn: "unitPrice" },
          { columnKey: "amount",    labelKo: "금액",    labelEn: "amount" },
        ],
      },
    ],
    fields: [
      { no: 1, enField: "supplierCompany", koField: "공급자 상호" },
      { no: 2, enField: "totalAmount",     koField: "총합계금액" },
    ],
    regions: [],
  };
  const invoiceRaw = {
    full_text: "공급자 상호: 거래처A\n총합계금액: 88000",
    receipt_fields: {
      "총합계금액": "88000",
      "공급자 상호": "거래처A",
    },
    finance_fields: {},
    processing_time: 2.0,
    fields: [],
  };
  const res = buildRunOcrResult(invoiceRaw, tpl);
  expect(Array.isArray(res.fields) && res.fields.length === 2,
    "case3 invoice: 2 info-derived fields");
  expect(res.fields[0].name === "공급자 상호" && res.fields[0].value === "거래처A",
    "case3 invoice: info[0] lookup");
  expect(res.fields[1].name === "총합계금액" && res.fields[1].value === "88000",
    "case3 invoice: info[1] lookup");
  // documentType attached
  expect(res.documentType === "invoice_statement",
    "case3 invoice: documentType attached");
  // unstructuredTables attached as skeleton (rows: [])
  expect(Array.isArray(res.unstructuredTables) && res.unstructuredTables.length === 1,
    "case3 invoice: unstructuredTables length 1");
  const meta = res.unstructuredTables[0];
  expect(meta.tableKey === "items", "case3 invoice: tableKey preserved");
  expect(meta.labelKo === "품목표",  "case3 invoice: labelKo preserved");
  expect(Array.isArray(meta.columns) && meta.columns.length === 4,
    "case3 invoice: 4 columns preserved");
  expect(meta.columns[0].columnKey === "itemName"
    && meta.columns[3].columnKey === "amount",
    "case3 invoice: column order itemName … amount");
  expect(Array.isArray(meta.rows) && meta.rows.length === 0,
    "case3 invoice: rows is [] skeleton (TPL-8 work)");
}

// ---------------------------------------------------------------------------
// SMOKE CASE 4 — info present but template.fields missing (info > fields)
// ---------------------------------------------------------------------------
{
  const tpl = {
    mode: "unstructured",
    info: [
      { key: "storeName", labelKo: "회사명", labelEn: "storeName", no: 1, order: 1 },
    ],
    regions: [],
  };
  const res = buildRunOcrResult(RECEIPT_RAW, tpl);
  expect(res.fields.length === 1 && res.fields[0].value === "ACME",
    "case4 info-without-fields: info still drives lookup");
}

// ---------------------------------------------------------------------------
// SMOKE CASE 5 — empty info[] falls back to legacy fields[]
// ---------------------------------------------------------------------------
{
  const tpl = {
    mode: "unstructured",
    info: [],
    fields: [
      { no: 1, enField: "storeName", koField: "회사명" },
    ],
    regions: [],
  };
  const res = buildRunOcrResult(RECEIPT_RAW, tpl);
  expect(res.fields.length === 1 && res.fields[0].value === "ACME",
    "case5 empty-info: legacy fields path used as fallback");
}

// ---------------------------------------------------------------------------
// SMOKE CASE 6 — no template (template?: BuildRunOcrResultTemplate omitted)
// ---------------------------------------------------------------------------
{
  const res = buildRunOcrResult(RECEIPT_RAW);
  // With no template, receipt_fields are used directly.
  expect(Array.isArray(res.fields) && res.fields.length === 4,
    "case6 no-template: 4 receipt fields auto-built");
  expect(!("documentType" in res), "case6 no-template: no documentType");
  expect(!("unstructuredTables" in res), "case6 no-template: no unstructuredTables");
}

// ---------------------------------------------------------------------------
// SMOKE CASE 7 — region-based template (mode !== "unstructured")
//   The early-return path must NOT be affected by the new info/tables logic.
// ---------------------------------------------------------------------------
{
  const tpl = {
    mode: "template",
    regions: [
      { koField: "회사명",     enField: "storeName" },
      { koField: "사업자번호", enField: "bizNo" },
    ],
  };
  const regionRaw = {
    full_text: "...",
    receipt_fields: {},
    finance_fields: {},
    processing_time: 1.5,
    fields: [
      { name: "field_1", value: "ACME",            ko: "", en: "" },
      { name: "field_2", value: "123-45-67890",    ko: "", en: "" },
    ],
  };
  const res = buildRunOcrResult(regionRaw, tpl);
  expect(res.fields.length === 2, "case7 region-based: 2 fields enriched");
  expect(res.fields[0].ko === "회사명" && res.fields[0].en === "storeName",
    "case7 region-based: ko/en labels enriched from regions");
  expect(!("documentType" in res), "case7 region-based: documentType not attached on region path");
  expect(!("unstructuredTables" in res), "case7 region-based: unstructuredTables not attached");
}

// ---------------------------------------------------------------------------
// SMOKE CASE 8 — documentType empty string → omitted (helper omit policy)
// ---------------------------------------------------------------------------
{
  const tpl = {
    mode: "unstructured",
    documentType: "   ",
    info: [{ key: "storeName", labelKo: "회사명", labelEn: "storeName", no: 1, order: 1 }],
    tables: [],
    regions: [],
  };
  const res = buildRunOcrResult(RECEIPT_RAW, tpl);
  expect(!("documentType" in res),
    "case8 whitespace-documentType: omitted from result");
}

// ---------------------------------------------------------------------------
// SMOKE CASE 9 — input mutation guard
// ---------------------------------------------------------------------------
{
  const tpl = {
    mode: "unstructured",
    documentType: "receipt",
    info: [{ key: "storeName", labelKo: "회사명", labelEn: "storeName", no: 1, order: 1 }],
    tables: [{
      tableKey: "t",
      labelKo: "T",
      columns: [{ columnKey: "c", labelKo: "C" }],
    }],
    regions: [],
  };
  const tplSnap = JSON.parse(JSON.stringify(tpl));
  const rawSnap = JSON.parse(JSON.stringify(RECEIPT_RAW));
  buildRunOcrResult(RECEIPT_RAW, tpl);
  expect(JSON.stringify(tpl) === JSON.stringify(tplSnap),
    "case9 input mutation: template not mutated");
  expect(JSON.stringify(RECEIPT_RAW) === JSON.stringify(rawSnap),
    "case9 input mutation: raw not mutated");
}

// ---------------------------------------------------------------------------
// 10. New-file scope check
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
