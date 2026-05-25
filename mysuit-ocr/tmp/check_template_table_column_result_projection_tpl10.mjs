#!/usr/bin/env node
// TPL-10-TEMPLATE-TABLE-COLUMN-RESULT-PROJECTION
// Static + runtime smoke. Verifies the new template_region_canonical source
// in buildTableResultViewModels(result, template) projects backend
// document_fields.tableRows by user template.regions[].table.columns. Also
// verifies OcrResultPanel/RunOcrWorkspace wiring and Clean JSON / Markdown
// export extension (templateTables key + "## 템플릿 테이블" section).
//
// Tag on success: [TEMPLATE_TABLE_COLUMN_RESULT_PROJECTION_TPL10] PASS

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
const TAG = "[TEMPLATE_TABLE_COLUMN_RESULT_PROJECTION_TPL10]";

// Node 24 strip-types — register a small loader so `.ts` siblings imported
// via bare relative paths resolve at runtime (same pattern as TPL-8B/8D/8F).
const LOADER_DIR = mkdtempSync(join(tmpdir(), "tpl10-loader-"));
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
const VIEWMODEL_HELPER = resolve(ROOT, "src/common/utils/tableResultViewModel.ts");
const OCR_RESULT_PANEL = resolve(ROOT, "src/components/runocr/ui/OcrResultPanel.tsx");
const RUNOCR_WORKSPACE = resolve(ROOT, "src/components/runocr/RunOcrWorkspace.tsx");
const CLEAN_JSON = resolve(ROOT, "src/common/utils/cleanJsonBuilder.ts");
const MARKDOWN_REPORT = resolve(ROOT, "src/common/utils/markdownReportBuilder.ts");
const MAPPER = resolve(ROOT, "src/components/runocr/utils/mapOcrResponse.ts");
const EXTRACT_HELPER = resolve(ROOT, "src/components/runocr/utils/extractUnstructuredTableRows.ts");
const TEMPLATE_RIGHT_PANEL = resolve(ROOT, "src/components/template/ui/TemplateRightPanel.tsx");
const TEMPLATE_ANNOTATOR = resolve(ROOT, "src/components/template/ui/TemplateAnnotator.tsx");
const OCR_CANVAS_PANE = resolve(ROOT, "src/common/ui/OcrCanvasPane.tsx");
const PAYLOAD_BUILDER = resolve(ROOT, "src/components/template/utils/buildTemplateExportPayload.ts");
const TYPES_OCR = resolve(ROOT, "src/common/types/ocr.ts");
const OCR_TABLE_REGION = resolve(ROOT, "src/common/utils/ocrTableRegion.ts");
const OCR_CANVAS_OPS = resolve(ROOT, "src/common/utils/ocrCanvasOps.ts");
const UNSTRUCTURED_BUILDER = resolve(ROOT, "src/components/template/UnstructuredBuilder.tsx");
const UNSTRUCTURED_DEF = resolve(ROOT, "src/components/template/utils/unstructuredDefinition.ts");
const TEST_WORKSPACE = resolve(ROOT, "src/components/test/TestWorkspace.tsx");

// ---------------------------------------------------------------------------
// 1. tableResultViewModel.ts — template_region_canonical activated
// ---------------------------------------------------------------------------
const vmSrc = readSafe(VIEWMODEL_HELPER) ?? "";
const vmCode = stripComments(vmSrc);

if (!/buildTableResultViewModels\s*\(\s*result\s*:\s*unknown\s*,\s*template\s*\?\s*:\s*unknown\s*,?\s*\)/.test(vmCode))
  fail(`buildTableResultViewModels signature does not accept (result, template?) (TPL-10)`);
else ok(`buildTableResultViewModels(result, template?) signature present`);

if (!/buildTemplateRegionCanonicalViewModels\s*\(/.test(vmCode))
  fail(`buildTemplateRegionCanonicalViewModels function not present`);
else ok(`buildTemplateRegionCanonicalViewModels function present`);

if (/void\s+_template\s*;\s*\/\/\s*placeholder\s+for\s+TPL-10/.test(vmCode))
  fail(`stale "void _template; // placeholder for TPL-10" line still present`);
else ok(`stale TPL-10 placeholder removed`);

// Source emit order: backend → template → unstructured
const orderRe = /buildBackendDocumentFieldsViewModel[\s\S]+?buildTemplateRegionCanonicalViewModels[\s\S]+?buildUnstructuredViewModels/;
if (!orderRe.test(vmCode))
  fail(`Source emit order is not backend → template_region_canonical → unstructured`);
else ok(`Source emit order: backend → template → unstructured`);

// Helper consumes template.regions[].table.columns
if (!/template\.regions/.test(vmCode))
  fail(`helper does not reference template.regions`);
else ok(`helper reads template.regions`);
if (!/table\.columns|table\.columns|table\b\s*\.\s*columns/.test(vmCode))
  fail(`helper does not reference table.columns`);
else ok(`helper reads table.columns`);

// Column-key resolution priority: columnKey → canonicalColumn → labelEn → enField
const keyPriority = /columnKey[\s\S]{0,200}canonicalColumn[\s\S]{0,200}labelEn[\s\S]{0,200}enField/;
if (!keyPriority.test(vmCode))
  fail(`column-key resolution priority (columnKey→canonicalColumn→labelEn→enField) not present`);
else ok(`column-key priority columnKey→canonicalColumn→labelEn→enField`);

// labelKo fallback chain
const labelKoChain = /labelKo[\s\S]{0,200}koField[\s\S]{0,200}canonicalColumn[\s\S]{0,200}columnKey[\s\S]{0,200}컬럼/;
if (!labelKoChain.test(vmCode))
  fail(`labelKo fallback chain not present`);
else ok(`labelKo fallback chain present`);

// Pure helper — no React/DOM/storage/fetch/UI imports
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
let pureOk = true;
for (const re of forbidden) {
  if (re.test(vmCode)) { fail(`forbidden in helper: ${re}`); pureOk = false; }
}
if (pureOk) ok(`helper remains pure (no React/DOM/storage/fetch/UI)`);

// ---------------------------------------------------------------------------
// 2. OcrResultPanel — passes activeTemplate
// ---------------------------------------------------------------------------
const panelSrc = readSafe(OCR_RESULT_PANEL) ?? "";
const panelCode = stripComments(panelSrc);

if (!/activeTemplate\s*\?\s*:\s*unknown/.test(panelCode))
  fail(`OcrResultPanel Props missing activeTemplate?: unknown`);
else ok(`OcrResultPanel Props has activeTemplate?: unknown`);

if (!/buildTableResultViewModels\s*\(\s*result\s*,\s*activeTemplate\s*\)/.test(panelCode))
  fail(`OcrResultPanel does not call buildTableResultViewModels(result, activeTemplate)`);
else ok(`OcrResultPanel calls buildTableResultViewModels(result, activeTemplate)`);

if (!/templateRegionTableResultViewModels/.test(panelCode))
  fail(`OcrResultPanel does not derive templateRegionTableResultViewModels`);
else ok(`OcrResultPanel derives templateRegionTableResultViewModels`);

if (!/template_region_canonical/.test(panelCode))
  fail(`OcrResultPanel does not filter source === "template_region_canonical"`);
else ok(`OcrResultPanel filters template_region_canonical`);

if (!/템플릿\s*테이블/.test(panelCode))
  fail(`OcrResultPanel missing '템플릿 테이블' section heading`);
else ok(`OcrResultPanel renders '템플릿 테이블' section`);

// Existing backend/unstructured logic preserved
if (!/backendTableResultViewModel/.test(panelCode))
  fail(`OcrResultPanel lost backendTableResultViewModel derivation`);
else ok(`OcrResultPanel keeps backendTableResultViewModel`);
if (!/unstructuredTableResultViewModels/.test(panelCode))
  fail(`OcrResultPanel lost unstructuredTableResultViewModels derivation`);
else ok(`OcrResultPanel keeps unstructuredTableResultViewModels`);

// ---------------------------------------------------------------------------
// 3. RunOcrWorkspace — passes activeTemplate prop
// ---------------------------------------------------------------------------
const wsSrc = readSafe(RUNOCR_WORKSPACE) ?? "";
const wsCode = stripComments(wsSrc);
if (!/<OcrResultPanel[\s\S]{0,2000}activeTemplate\s*=\s*\{[^}]+\}/.test(wsCode))
  fail(`RunOcrWorkspace does not pass activeTemplate to OcrResultPanel`);
else ok(`RunOcrWorkspace passes activeTemplate to OcrResultPanel`);

// ---------------------------------------------------------------------------
// 4. Clean JSON / Markdown — template export support
// ---------------------------------------------------------------------------
const cjSrc = readSafe(CLEAN_JSON) ?? "";
const cjCode = stripComments(cjSrc);
const mdSrc = readSafe(MARKDOWN_REPORT) ?? "";
const mdCode = stripComments(mdSrc);

// TPL-10 originally required `templateTables?` key + per-source filter.
// TPL-13B keeps the legacy TYPE declarations for back-compat but routes
// emission through selectRepresentativeTableResultViewModels (no longer
// filters by source inline). Phase-aware detect the TPL-13B marker.
const _tpl13bShipped_cj_tpl10 = /selectRepresentativeTableResultViewModels/.test(cjCode);
const _tpl13bShipped_md_tpl10 = /selectRepresentativeTableResultViewModels/.test(mdCode);

if (!/templateTables\?\s*:/.test(cjCode))
  fail(`CleanJsonResult missing optional templateTables`);
else ok(`CleanJsonResult.templateTables?: present (legacy type preserved)`);

if (!/CleanJsonTemplateTable\b/.test(cjCode))
  fail(`CleanJsonTemplateTable type missing`);
else ok(`CleanJsonTemplateTable type present (legacy type preserved)`);

if (_tpl13bShipped_cj_tpl10) {
  note(`cleanJsonBuilder routes template_region_canonical via selectRepresentativeTableResultViewModels (TPL-13B)`);
} else if (!/source\s*===\s*"template_region_canonical"/.test(cjCode)) {
  fail(`cleanJsonBuilder does not filter template_region_canonical`);
} else {
  ok(`cleanJsonBuilder filters template_region_canonical`);
}

if (!/source\s*===\s*"template_region_canonical"/.test(mdCode) && !_tpl13bShipped_md_tpl10)
  fail(`markdownReportBuilder does not filter template_region_canonical`);
else if (_tpl13bShipped_md_tpl10)
  note(`markdownReportBuilder routes template_region_canonical via selectRepresentativeTableResultViewModels (TPL-13B)`);
else ok(`markdownReportBuilder filters template_region_canonical`);

if (!/##\s*템플릿\s*테이블/.test(mdCode))
  fail(`markdownReportBuilder missing '## 템플릿 테이블' section`);
else ok(`markdownReportBuilder includes '## 템플릿 테이블' section header`);

// Old unstructured filter — TPL-13B replaces it with representative selector.
if (!/source\s*===\s*"unstructured_definition"/.test(cjCode) && !_tpl13bShipped_cj_tpl10)
  fail(`cleanJsonBuilder lost unstructured_definition filter`);
else if (_tpl13bShipped_cj_tpl10)
  note(`cleanJsonBuilder uses representative selector for unstructured_definition (TPL-13B)`);
else ok(`cleanJsonBuilder keeps unstructured_definition filter`);
if (!/source\s*===\s*"unstructured_definition"/.test(mdCode) && !_tpl13bShipped_md_tpl10)
  fail(`markdownReportBuilder lost unstructured_definition filter`);
else if (_tpl13bShipped_md_tpl10)
  note(`markdownReportBuilder uses representative selector for unstructured_definition (TPL-13B)`);
else ok(`markdownReportBuilder keeps unstructured_definition filter`);

// ---------------------------------------------------------------------------
// 5. Untouched files
// ---------------------------------------------------------------------------
const untouched = [
  ["mapOcrResponse.ts", MAPPER],
  ["extractUnstructuredTableRows.ts", EXTRACT_HELPER],
  ["TemplateRightPanel.tsx", TEMPLATE_RIGHT_PANEL],
  ["TemplateAnnotator.tsx", TEMPLATE_ANNOTATOR],
  ["OcrCanvasPane.tsx", OCR_CANVAS_PANE],
  ["buildTemplateExportPayload.ts", PAYLOAD_BUILDER],
  ["ocr.ts", TYPES_OCR],
  ["ocrTableRegion.ts", OCR_TABLE_REGION],
  ["ocrCanvasOps.ts", OCR_CANVAS_OPS],
  ["UnstructuredBuilder.tsx", UNSTRUCTURED_BUILDER],
  ["unstructuredDefinition.ts", UNSTRUCTURED_DEF],
  ["TestWorkspace.tsx", TEST_WORKSPACE],
];
for (const [label, p] of untouched) {
  if (!existsSync(p)) fail(`expected file missing: ${label}`);
  else ok(`present (untouched expected): ${label}`);
}

// Forbidden content markers in untouched files
for (const [label, p] of [
  ["mapOcrResponse.ts", MAPPER],
  ["extractUnstructuredTableRows.ts", EXTRACT_HELPER],
  ["TemplateRightPanel.tsx", TEMPLATE_RIGHT_PANEL],
  ["OcrCanvasPane.tsx", OCR_CANVAS_PANE],
  ["buildTemplateExportPayload.ts", PAYLOAD_BUILDER],
  ["UnstructuredBuilder.tsx", UNSTRUCTURED_BUILDER],
  ["unstructuredDefinition.ts", UNSTRUCTURED_DEF],
]) {
  const src = stripComments(readSafe(p) ?? "");
  if (/template_region_canonical/.test(src))
    fail(`${label} references template_region_canonical (should be untouched)`);
  else ok(`${label} clean of template_region_canonical reference`);
}

// rowOverrides must remain absent
for (const [label, p] of [
  ["tableResultViewModel.ts", VIEWMODEL_HELPER],
  ["OcrResultPanel.tsx", OCR_RESULT_PANEL],
  ["RunOcrWorkspace.tsx", RUNOCR_WORKSPACE],
  ["cleanJsonBuilder.ts", CLEAN_JSON],
  ["markdownReportBuilder.ts", MARKDOWN_REPORT],
]) {
  const src = stripComments(readSafe(p) ?? "");
  if (/rowOverrides/.test(src)) fail(`${label} contains rowOverrides (TPL-11 scope)`);
  else ok(`${label} has no rowOverrides reference`);
}

// ---------------------------------------------------------------------------
// 6. src/lib absent + @/lib imports = 0
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
// 7. Runtime smoke — dynamic import + projection cases
// ---------------------------------------------------------------------------
let vmMod = null, cjMod = null, mdMod = null;
try {
  vmMod = await import(pathToFileURL(VIEWMODEL_HELPER).href);
  ok(`tableResultViewModel runtime import succeeded`);
} catch (err) { fail(`tableResultViewModel runtime import failed: ${err?.message ?? err}`); }
try {
  cjMod = await import(pathToFileURL(CLEAN_JSON).href);
  ok(`cleanJsonBuilder runtime import succeeded`);
} catch (err) { fail(`cleanJsonBuilder runtime import failed: ${err?.message ?? err}`); }
try {
  mdMod = await import(pathToFileURL(MARKDOWN_REPORT).href);
  ok(`markdownReportBuilder runtime import succeeded`);
} catch (err) { fail(`markdownReportBuilder runtime import failed: ${err?.message ?? err}`); }
if (!vmMod || !cjMod || !mdMod) {
  console.error(`${TAG} FAIL aborting smoke — imports failed`);
  console.error(`${TAG} FAIL count=${failures.length}`);
  process.exit(1);
}
const { buildTableResultViewModels } = vmMod;
const { buildCleanJsonResult } = cjMod;
const { buildMarkdownReport } = mdMod;

// ── SMOKE 1: backend-only (no template) — no-regression ─────────────────
{
  const result = {
    doc_type: "invoice_statement",
    document_fields: {
      tableRows: [
        { itemName: "헥사", quantity: "1", unitPrice: "100", amount: "100" },
      ],
      tableMeta: { expectedColumnKeys: ["itemName", "quantity", "unitPrice", "amount"] },
    },
  };
  const snap = JSON.parse(JSON.stringify(result));
  const vms = buildTableResultViewModels(result);
  expect(vms.length === 1, "case1 backend-only: 1 view model");
  expect(vms[0].source === "backend_document_fields", "case1 backend-only: source backend");
  expect(JSON.stringify(result) === JSON.stringify(snap),
    "case1 backend-only: input unchanged");
  // Same result when template arg is null/undefined
  expect(buildTableResultViewModels(result, undefined).length === 1, "case1 backend-only: template=undefined OK");
  expect(buildTableResultViewModels(result, null).length === 1, "case1 backend-only: template=null OK");
  expect(buildTableResultViewModels(result, {}).length === 1, "case1 backend-only: template={} (no regions) emits only backend");
}

// ── SMOKE 2: template columns projection ────────────────────────────────
{
  const result = {
    documentType: "invoice_statement",
    document_fields: {
      tableRows: [
        { itemName: "헥사", quantity: "1", unitPrice: "100", amount: "100" },
        { itemName: "이부", quantity: "2", unitPrice: "200", amount: "400" },
      ],
      tableMeta: { expectedColumnKeys: ["itemName", "quantity", "unitPrice", "amount"] },
    },
  };
  const template = {
    documentType: "invoice_statement",
    regions: [{
      id: "table_1",
      name: "품목표",
      fieldType: "table",
      table: {
        tableName: "품목표",
        columns: [
          { index: 0, columnKey: "itemName", labelKo: "품목명" },
          { index: 1, columnKey: "quantity", labelKo: "수량" },
          { index: 2, columnKey: "amount",   labelKo: "금액" },
        ],
      },
    }],
  };
  const vms = buildTableResultViewModels(result, template);
  expect(vms.length === 2, "case2 projection: 2 view models (backend + template)");
  expect(vms[0].source === "backend_document_fields", "case2 projection: backend first");
  expect(vms[1].source === "template_region_canonical", "case2 projection: template second");
  const tpl = vms[1];
  expect(tpl.tableKey === "품목표", "case2 projection: tableKey = template.table.tableName");
  expect(tpl.labelKo === "품목표", "case2 projection: labelKo = tableName");
  expect(tpl.columns.length === 3, "case2 projection: 3 columns");
  expect(
    tpl.columns.map((c) => c.columnKey).join(",") === "itemName,quantity,amount",
    "case2 projection: column order = user order",
  );
  expect(tpl.rows.length === 2, "case2 projection: 2 rows from backend");
  // Projected row values use user columnKey (which matches backend key)
  expect(tpl.rows[0].values.itemName === "헥사" && tpl.rows[0].values.quantity === "1" && tpl.rows[0].values.amount === "100",
    "case2 projection: row[0] values");
  expect(tpl.rows[1].values.itemName === "이부" && tpl.rows[1].values.quantity === "2" && tpl.rows[1].values.amount === "400",
    "case2 projection: row[1] values");
  // unitPrice is NOT in user columns → not in projected rows
  expect(!("unitPrice" in tpl.rows[0].values),
    "case2 projection: unitPrice excluded (not in user columns)");
  // columns source = user
  expect(tpl.columns.every((c) => c.source === "user"),
    "case2 projection: columns source = user");
  // meta
  expect(tpl.meta.source === "template_region_canonical", "case2 projection: meta.source");
  expect(tpl.meta.documentType === "invoice_statement", "case2 projection: meta.documentType");
  expect(tpl.meta.originalSource === "template.regions[0].table.columns",
    "case2 projection: meta.originalSource");
}

// ── SMOKE 3: canonicalColumn fallback when columnKey missing ────────────
{
  const result = {
    document_fields: {
      tableRows: [{ itemName: "약품A", quantity: "5", amount: "5000" }],
    },
  };
  const template = {
    regions: [{
      fieldType: "table",
      table: {
        columns: [
          { index: 0, canonicalColumn: "itemName", labelKo: "품목명" },
          { index: 1, canonicalColumn: "amount",   labelKo: "금액" },
        ],
      },
    }],
  };
  const vms = buildTableResultViewModels(result, template);
  const tpl = vms.find((v) => v.source === "template_region_canonical");
  expect(!!tpl, "case3 fallback: template VM emitted");
  expect(tpl.columns.length === 2, "case3 fallback: 2 columns");
  expect(tpl.columns[0].columnKey === "itemName", "case3 fallback: columnKey from canonicalColumn[0]");
  expect(tpl.columns[1].columnKey === "amount",   "case3 fallback: columnKey from canonicalColumn[1]");
  expect(tpl.rows[0].values.itemName === "약품A", "case3 fallback: itemName row value");
  expect(tpl.rows[0].values.amount === "5000",   "case3 fallback: amount row value");
}

// ── SMOKE 4: mismatched key → empty string cell ─────────────────────────
{
  const result = {
    document_fields: {
      tableRows: [{ itemName: "헥사", quantity: "1" }],
    },
  };
  const template = {
    regions: [{
      fieldType: "table",
      table: {
        columns: [
          { index: 0, columnKey: "itemName",      labelKo: "품목명" },
          { index: 1, columnKey: "unknownColumn", labelKo: "알수없음" },
        ],
      },
    }],
  };
  const vms = buildTableResultViewModels(result, template);
  const tpl = vms.find((v) => v.source === "template_region_canonical");
  expect(!!tpl, "case4 mismatch: template VM emitted");
  expect(tpl.rows.length === 1, "case4 mismatch: 1 row");
  expect(tpl.rows[0].values.itemName === "헥사", "case4 mismatch: known key projects");
  expect(tpl.rows[0].values.unknownColumn === "", "case4 mismatch: unknown key → ''");
  const unknownCell = tpl.rows[0].cells.find((c) => c.key === "unknownColumn");
  expect(unknownCell && unknownCell.isEmpty === true && unknownCell.displayValue === "-",
    "case4 mismatch: unknown cell isEmpty=true displayValue='-'");
}

// ── SMOKE 5: no columns → template_region_canonical NOT emitted ─────────
{
  const result = {
    document_fields: {
      tableRows: [{ itemName: "헥사", quantity: "1" }],
    },
  };
  const template = {
    regions: [{
      id: "table_1",
      fieldType: "table",
      table: {
        // columns intentionally missing
        mode: "repeat",
      },
    }],
  };
  const vms = buildTableResultViewModels(result, template);
  expect(vms.every((v) => v.source !== "template_region_canonical"),
    "case5 no-columns: no template_region_canonical VM");
  // template with empty columns array also skipped
  const t2 = {
    regions: [{
      fieldType: "table",
      table: { columns: [] },
    }],
  };
  const vms2 = buildTableResultViewModels(result, t2);
  expect(vms2.every((v) => v.source !== "template_region_canonical"),
    "case5 no-columns: empty columns array also skipped");
  // template with columns of all-empty entries (no columnKey/canonicalColumn) → skipped
  const t3 = {
    regions: [{
      fieldType: "table",
      table: { columns: [{ index: 0 }, { index: 1 }] },
    }],
  };
  const vms3 = buildTableResultViewModels(result, t3);
  expect(vms3.every((v) => v.source !== "template_region_canonical"),
    "case5 no-columns: columns with no key/canonical also skipped");
}

// ── SMOKE 6: backend + template + unstructured — all sources ────────────
{
  const result = {
    doc_type: "invoice_statement",
    document_fields: {
      tableRows: [{ itemName: "헥사", quantity: "1", unitPrice: "100", amount: "100" }],
      tableMeta: { expectedColumnKeys: ["itemName", "quantity", "unitPrice", "amount"] },
    },
    unstructuredTables: [{
      tableKey: "items_u",
      labelKo: "비정형 품목표",
      columns: [{ columnKey: "itemName", labelKo: "품목명" }],
      rows: [{ itemName: "비정형헥사" }],
    }],
  };
  const template = {
    regions: [{
      fieldType: "table",
      table: {
        tableName: "정형품목표",
        columns: [
          { index: 0, columnKey: "itemName", labelKo: "품목명" },
          { index: 1, columnKey: "amount",   labelKo: "금액" },
        ],
      },
    }],
  };
  const snap = JSON.parse(JSON.stringify(result));
  const tplSnap = JSON.parse(JSON.stringify(template));
  const vms = buildTableResultViewModels(result, template);
  expect(vms.length === 3, "case6 all-sources: 3 view models");
  expect(vms[0].source === "backend_document_fields", "case6 all-sources: [0] backend");
  expect(vms[1].source === "template_region_canonical", "case6 all-sources: [1] template");
  expect(vms[2].source === "unstructured_definition", "case6 all-sources: [2] unstructured");
  // Mutation guards
  expect(JSON.stringify(result) === JSON.stringify(snap), "case6 all-sources: result not mutated");
  expect(JSON.stringify(template) === JSON.stringify(tplSnap), "case6 all-sources: template not mutated");
}

// ── SMOKE 7: export — Clean JSON + Markdown carry template tables ───────
{
  const fields = [{ name: "items", field_type: "table", value: "" }];
  const templateVM = {
    tableKey: "품목표",
    labelKo: "품목표",
    source: "template_region_canonical",
    columns: [
      { columnKey: "itemName", labelKo: "품목명", source: "user" },
      { columnKey: "amount",   labelKo: "금액",   source: "user" },
    ],
    rows: [
      {
        index: 0,
        values: { itemName: "헥사", amount: "100" },
        cells: [
          { key: "itemName", value: "헥사", displayValue: "헥사", isEmpty: false },
          { key: "amount",   value: "100",  displayValue: "100",  isEmpty: false },
        ],
      },
    ],
    meta: {
      source: "template_region_canonical",
      rowCount: 1,
      columnCount: 2,
      hasRows: true,
      hasColumns: true,
      originalSource: "template.regions[0].table.columns",
    },
  };
  const cj = buildCleanJsonResult({
    templateName: "T",
    fields,
    tableResultViewModels: [templateVM],
  });
  // TPL-10 expected `templateTables[]`; TPL-13B promotes the template VM to
  // representative `tables[]` (single source per physical table). Accept
  // whichever the current builder emits.
  const case7entry = Array.isArray(cj.tables) && cj.tables[0]
    ? cj.tables[0]
    : (Array.isArray(cj.templateTables) ? cj.templateTables[0] : null);
  const case7Key = case7entry && (("tableKey" in case7entry && case7entry.tableKey) || case7entry.key);
  expect(case7entry != null,
    "case7 export cj: representative table entry emitted (tables or templateTables)");
  expect(case7Key === "품목표", "case7 export cj: tableKey/key = 품목표");
  expect(Array.isArray(case7entry.columns) && case7entry.columns.length === 2
    && case7entry.columns[0].columnKey === "itemName",
    "case7 export cj: columns preserved");
  expect(case7entry.rows[0].itemName === "헥사" && case7entry.rows[0].amount === "100",
    "case7 export cj: row values");
  expect(!("unstructuredTables" in cj), "case7 export cj: no unstructuredTables key emitted");

  const md = buildMarkdownReport({
    fields, processingTime: 1.0,
    tableResultViewModels: [templateVM],
  });
  expect(/##\s*템플릿\s*테이블/.test(md), "case7 export md: '## 템플릿 테이블' section");
  expect(/###\s*품목표/.test(md), "case7 export md: '### 품목표' title");
  expect(/\|\s*품목명\s*\|\s*금액\s*\|/.test(md), "case7 export md: header labels");
  expect(/헥사\s*\|\s*100/.test(md), "case7 export md: row values");
  expect(!/##\s*비정형\s*테이블/.test(md), "case7 export md: no unstructured section");
}

// ── SMOKE 8: export — backward compat without VM input ──────────────────
{
  const fields = [{ name: "회사명", field_type: "field", value: "ACME", ko: "회사명" }];
  const cj = buildCleanJsonResult({ templateName: "T", fields });
  expect(!("templateTables" in cj) && !("unstructuredTables" in cj),
    "case8 backcompat: no template/unstructured keys when input omitted");
  const md = buildMarkdownReport({ fields, processingTime: 1.0 });
  expect(!/##\s*템플릿\s*테이블/.test(md), "case8 backcompat md: no template section");
  expect(!/##\s*비정형\s*테이블/.test(md), "case8 backcompat md: no unstructured section");
}

// ── SMOKE 9: output ordering with all three sources in export ───────────
{
  const fields = [{ name: "items", field_type: "table", value: "" }];
  const templateVM = {
    tableKey: "tpl", labelKo: "TPL", source: "template_region_canonical",
    columns: [{ columnKey: "a", labelKo: "A", source: "user" }],
    rows: [{ index: 0, values: { a: "1" }, cells: [{ key: "a", value: "1", displayValue: "1", isEmpty: false }] }],
    meta: { source: "template_region_canonical", rowCount: 1, columnCount: 1, hasRows: true, hasColumns: true },
  };
  const unstructuredVM = {
    tableKey: "u", labelKo: "U", source: "unstructured_definition",
    columns: [{ columnKey: "a", labelKo: "A", source: "user" }],
    rows: [{ index: 0, values: { a: "2" }, cells: [{ key: "a", value: "2", displayValue: "2", isEmpty: false }] }],
    meta: { source: "unstructured_definition", rowCount: 1, columnCount: 1, hasRows: true, hasColumns: true },
  };
  const backendVM = {
    tableKey: "doc", labelKo: "DOC", source: "backend_document_fields",
    columns: [{ columnKey: "a", labelKo: "A", source: "canonical" }],
    rows: [{ index: 0, values: { a: "9" }, cells: [{ key: "a", value: "9", displayValue: "9", isEmpty: false }] }],
    meta: { source: "backend_document_fields", rowCount: 1, columnCount: 1, hasRows: true, hasColumns: true },
  };
  const cj = buildCleanJsonResult({
    templateName: "T", fields,
    tableResultViewModels: [backendVM, templateVM, unstructuredVM],
  });
  // TPL-10 expected BOTH templateTables AND unstructuredTables to coexist.
  // TPL-13B priority dedup: with templateVM present, only TEMPLATE wins —
  // unstructured + backend are dropped from export. Accept either contract.
  const hasLegacyDualKeys =
    Array.isArray(cj.templateTables) && cj.templateTables.length === 1
    && Array.isArray(cj.unstructuredTables) && cj.unstructuredTables.length === 1;
  const hasRepresentativeTable =
    Array.isArray(cj.tables) && cj.tables.length === 1
    && (cj.tables[0].key === "tpl" || cj.tables[0].tableKey === "tpl");
  expect(hasLegacyDualKeys || hasRepresentativeTable,
    "case9 ordering cj: emits TPL-10 dual keys OR TPL-13B single representative");
  // backend filtered out either way
  const all = JSON.stringify(cj);
  expect(!/"DOC"/.test(all), "case9 ordering cj: backend VM dropped from export");

  const md = buildMarkdownReport({
    fields, processingTime: 1.0,
    tableResultViewModels: [backendVM, templateVM, unstructuredVM],
  });
  const tplIdx = md.indexOf("## 템플릿 테이블");
  const uIdx = md.indexOf("## 비정형 테이블");
  // TPL-10 emitted both sections (template before unstructured). TPL-13B
  // emits only the representative section (template wins when present).
  const legacyDual = tplIdx > 0 && uIdx > 0 && tplIdx < uIdx;
  const dedupTemplateOnly = tplIdx > 0 && uIdx === -1;
  expect(legacyDual || dedupTemplateOnly,
    "case9 ordering md: TPL-10 dual sections (template < unstructured) OR TPL-13B template-only");
}

// ── SMOKE 10: mutation guard ────────────────────────────────────────────
{
  const result = {
    document_fields: { tableRows: [{ a: "x", b: "y" }] },
  };
  const template = {
    regions: [{ fieldType: "table", table: { columns: [{ columnKey: "a", labelKo: "A" }] } }],
  };
  const snap = JSON.parse(JSON.stringify(result));
  const tplSnap = JSON.parse(JSON.stringify(template));
  buildTableResultViewModels(result, template);
  buildTableResultViewModels(result, template);
  expect(JSON.stringify(result) === JSON.stringify(snap), "case10 mutation: result unchanged");
  expect(JSON.stringify(template) === JSON.stringify(tplSnap), "case10 mutation: template unchanged");
}

// ---------------------------------------------------------------------------
// 8. Existing Clean JSON v1 / table_view_model_v1 fixture runners must PASS
// ---------------------------------------------------------------------------
try {
  execSync("node tmp/check_clean_json_v1_fixtures_js.mjs", {
    cwd: ROOT, stdio: "ignore",
  });
  ok(`Clean JSON v1 fixture runner: PASS (no regression)`);
} catch {
  fail(`Clean JSON v1 fixture runner FAILED — backward compat broken`);
}
try {
  execSync("node tmp/check_table_view_model_v1_fixtures_js.mjs", {
    cwd: ROOT, stdio: "ignore",
  });
  ok(`table_view_model_v1 fixture runner: PASS (no regression)`);
} catch {
  fail(`table_view_model_v1 fixture runner FAILED — backward compat broken`);
}

// ---------------------------------------------------------------------------
// 9. New-file scope check
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
