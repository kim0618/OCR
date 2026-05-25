#!/usr/bin/env node
// TPL-13B-TABLE-RESULT-DEDUP-REPRESENTATIVE-TABLE
// Verifies representative-table dedup: only one source per physical table
// is rendered / exported, picked by priority template > unstructured >
// backend > legacy.
//
// Tag on success: [TABLE_RESULT_REPRESENTATIVE_DEDUP_TPL13B] PASS

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
const TAG = "[TABLE_RESULT_REPRESENTATIVE_DEDUP_TPL13B]";

const LOADER_DIR = mkdtempSync(join(tmpdir(), "tpl13b-loader-"));
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
const CLEAN_JSON = resolve(ROOT, "src/common/utils/cleanJsonBuilder.ts");
const MARKDOWN_REPORT = resolve(ROOT, "src/common/utils/markdownReportBuilder.ts");
const OCR_RESULT_PANEL = resolve(ROOT, "src/components/runocr/ui/OcrResultPanel.tsx");
const OCR_CANVAS_PANE = resolve(ROOT, "src/common/ui/OcrCanvasPane.tsx");
const TEMPLATE_RIGHT_PANEL = resolve(ROOT, "src/components/template/ui/TemplateRightPanel.tsx");
const TEMPLATE_ANNOTATOR = resolve(ROOT, "src/components/template/ui/TemplateAnnotator.tsx");
const PAYLOAD_BUILDER = resolve(ROOT, "src/components/template/utils/buildTemplateExportPayload.ts");
const TYPES_OCR = resolve(ROOT, "src/common/types/ocr.ts");
const TABLE_REGION = resolve(ROOT, "src/common/utils/ocrTableRegion.ts");
const MAPPER = resolve(ROOT, "src/components/runocr/utils/mapOcrResponse.ts");
const EXTRACT_HELPER = resolve(ROOT, "src/components/runocr/utils/extractUnstructuredTableRows.ts");
const UNSTRUCTURED_BUILDER = resolve(ROOT, "src/components/template/UnstructuredBuilder.tsx");
const UNSTRUCTURED_DEF = resolve(ROOT, "src/components/template/utils/unstructuredDefinition.ts");
const TEST_WORKSPACE = resolve(ROOT, "src/components/test/TestWorkspace.tsx");
const BACKEND_MAIN = resolve(REPO_ROOT, "ocr-server/main.py");
const TEMPLATES_JSON = resolve(REPO_ROOT, "ocr-server/data/templates.json");

// ---------------------------------------------------------------------------
// 1. tableResultViewModel.ts — representative helper
// ---------------------------------------------------------------------------
const vmSrc = readSafe(VIEWMODEL_HELPER) ?? "";
const vmCode = stripComments(vmSrc);
if (!/export\s+function\s+selectRepresentativeTableResultViewModels\s*\(/.test(vmCode))
  fail(`selectRepresentativeTableResultViewModels export missing`);
else ok(`selectRepresentativeTableResultViewModels export present`);

// Priority chain markers
if (!/template_region_canonical[\s\S]{0,200}unstructured_definition[\s\S]{0,200}backend_document_fields/.test(vmCode))
  fail(`representative priority chain template>unstructured>backend not encoded`);
else ok(`representative priority chain template>unstructured>backend encoded`);

// ---------------------------------------------------------------------------
// 2. OcrResultPanel — uses representative helper + dedup gates
// ---------------------------------------------------------------------------
const orpSrc = readSafe(OCR_RESULT_PANEL) ?? "";
const orpCode = stripComments(orpSrc);
if (!/selectRepresentativeTableResultViewModels/.test(orpCode))
  fail(`OcrResultPanel does not import/use selectRepresentativeTableResultViewModels`);
else ok(`OcrResultPanel uses selectRepresentativeTableResultViewModels`);
if (!/representativeFirstVM/.test(orpCode))
  fail(`OcrResultPanel: representativeFirstVM derivation missing`);
else ok(`OcrResultPanel: representativeFirstVM derivation present`);
// Standalone template section gated by previewTableFields.length === 0 (TPL-13B)
// OR !hasPreviewTableFieldRow (TPL-13C renamed the guard for clarity).
if (!/previewTableFields\.length\s*===\s*0\s*\n?\s*&&\s*templateRegionTableResultViewModels\.length\s*>\s*0/.test(orpCode)
    && !/!hasPreviewTableFieldRow\s*\n?\s*&&\s*templateRegionTableResultViewModels\.length\s*>\s*0/.test(orpCode))
  fail(`OcrResultPanel: Preview template standalone not gated by previewTableFields.length === 0 / !hasPreviewTableFieldRow`);
else ok(`OcrResultPanel: Preview template standalone gated by previewTableFields-empty / !hasPreviewTableFieldRow (TPL-13B/C)`);
// Standalone Custom template section gated by editedFields.every (no table field)
if (!/editedFields\.every\(\(f\)\s*=>\s*f\.field_type\s*!==\s*"table"\)[\s\S]{0,200}templateRegionTableResultViewModels\.length\s*>\s*0/.test(orpCode))
  fail(`OcrResultPanel: Custom template standalone not gated by editedFields.every(no-table)`);
else ok(`OcrResultPanel: Custom template standalone gated by editedFields.every(no-table)`);

// Custom field-row uses representative VM
if (!/customRepVM/.test(orpCode))
  fail(`OcrResultPanel: Custom customRepVM (representative) variable missing`);
else ok(`OcrResultPanel: Custom uses customRepVM representative`);
if (!/previewRepVM/.test(orpCode))
  fail(`OcrResultPanel: Preview previewRepVM (representative) variable missing`);
else ok(`OcrResultPanel: Preview uses previewRepVM representative`);

// ---------------------------------------------------------------------------
// 3. cleanJsonBuilder — representative dedup policy
// ---------------------------------------------------------------------------
const cjSrc = readSafe(CLEAN_JSON) ?? "";
const cjCode = stripComments(cjSrc);
if (!/selectRepresentativeTableResultViewModels/.test(cjCode))
  fail(`cleanJsonBuilder does not import selectRepresentativeTableResultViewModels`);
else ok(`cleanJsonBuilder imports selectRepresentativeTableResultViewModels`);
// templateTables / unstructuredTables key assignment markers removed from production output
if (/result\.templateTables\s*=/.test(cjCode))
  fail(`cleanJsonBuilder still emits result.templateTables key (TPL-13B should drop it)`);
else ok(`cleanJsonBuilder: result.templateTables key emission removed (TPL-13B)`);
if (/result\.unstructuredTables\s*=/.test(cjCode))
  fail(`cleanJsonBuilder still emits result.unstructuredTables key (TPL-13B should drop it)`);
else ok(`cleanJsonBuilder: result.unstructuredTables key emission removed (TPL-13B)`);
// representative-source override path present
if (!/repSource\s*===\s*"template_region_canonical"\s*\|\|\s*repSource\s*===\s*"unstructured_definition"/.test(cjCode))
  fail(`cleanJsonBuilder: representative source override condition missing`);
else ok(`cleanJsonBuilder: representative source override condition present`);
// Optional columns on CleanJsonTable type
if (!/columns\?\s*:\s*Array<\s*\{\s*columnKey\s*:\s*string\s*;\s*labelKo\s*:\s*string\s*\}\s*>/.test(cjCode))
  fail(`cleanJsonBuilder: CleanJsonTable.columns? optional field missing`);
else ok(`cleanJsonBuilder: CleanJsonTable.columns? optional field present`);

// ---------------------------------------------------------------------------
// 4. markdownReportBuilder — representative dedup policy
// ---------------------------------------------------------------------------
const mdSrc = readSafe(MARKDOWN_REPORT) ?? "";
const mdCode = stripComments(mdSrc);
if (!/selectRepresentativeTableResultViewModels/.test(mdCode))
  fail(`markdownReportBuilder does not import selectRepresentativeTableResultViewModels`);
else ok(`markdownReportBuilder imports selectRepresentativeTableResultViewModels`);
// Single representative heading (not duplicate sections)
if (!/repHeading/.test(mdCode))
  fail(`markdownReportBuilder: repHeading variable missing (TPL-13B single section)`);
else ok(`markdownReportBuilder: repHeading variable present`);
// Both heading literals still in source (selected via switch on source)
if (!/##\s*템플릿\s*테이블/.test(mdCode))
  fail(`markdownReportBuilder: "## 템플릿 테이블" heading literal missing`);
else ok(`markdownReportBuilder: "## 템플릿 테이블" heading literal present`);
if (!/##\s*비정형\s*테이블/.test(mdCode))
  fail(`markdownReportBuilder: "## 비정형 테이블" heading literal missing`);
else ok(`markdownReportBuilder: "## 비정형 테이블" heading literal present`);

// ---------------------------------------------------------------------------
// 5. Untouched files
// ---------------------------------------------------------------------------
for (const [label, p] of [
  ["TemplateRightPanel.tsx", TEMPLATE_RIGHT_PANEL],
  ["OcrCanvasPane.tsx", OCR_CANVAS_PANE],
  ["TemplateAnnotator.tsx", TEMPLATE_ANNOTATOR],
  ["buildTemplateExportPayload.ts", PAYLOAD_BUILDER],
  ["types/ocr.ts", TYPES_OCR],
  ["ocrTableRegion.ts", TABLE_REGION],
  ["mapOcrResponse.ts", MAPPER],
  ["extractUnstructuredTableRows.ts", EXTRACT_HELPER],
  ["UnstructuredBuilder.tsx", UNSTRUCTURED_BUILDER],
  ["unstructuredDefinition.ts", UNSTRUCTURED_DEF],
  ["TestWorkspace.tsx", TEST_WORKSPACE],
]) {
  if (!existsSync(p)) fail(`expected file missing: ${label}`);
  else ok(`present: ${label}`);
}

// Backend/templates.json untouched
if (existsSync(BACKEND_MAIN)) {
  if (/selectRepresentativeTableResultViewModels|representativeFirstVM/.test(readSafe(BACKEND_MAIN) ?? ""))
    fail(`ocr-server/main.py references TPL-13B helpers`);
  else ok(`ocr-server/main.py: no TPL-13B references`);
}
if (existsSync(TEMPLATES_JSON)) {
  if (/selectRepresentativeTableResultViewModels|representativeFirstVM/.test(readSafe(TEMPLATES_JSON) ?? ""))
    fail(`templates.json carries TPL-13B references`);
  else ok(`templates.json: no TPL-13B references`);
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
// 7. Runtime smoke
// ---------------------------------------------------------------------------
let vmMod = null, cjMod = null, mdMod = null;
try { vmMod = await import(pathToFileURL(VIEWMODEL_HELPER).href); ok(`tableResultViewModel import OK`); }
catch (err) { fail(`tableResultViewModel import failed: ${err?.message ?? err}`); }
try { cjMod = await import(pathToFileURL(CLEAN_JSON).href); ok(`cleanJsonBuilder import OK`); }
catch (err) { fail(`cleanJsonBuilder import failed: ${err?.message ?? err}`); }
try { mdMod = await import(pathToFileURL(MARKDOWN_REPORT).href); ok(`markdownReportBuilder import OK`); }
catch (err) { fail(`markdownReportBuilder import failed: ${err?.message ?? err}`); }
if (!vmMod || !cjMod || !mdMod) {
  console.error(`${TAG} FAIL aborting — imports failed`);
  console.error(`${TAG} FAIL count=${failures.length}`);
  process.exit(1);
}
const { buildTableResultViewModels, selectRepresentativeTableResultViewModels } = vmMod;
const { buildCleanJsonResult } = cjMod;
const { buildMarkdownReport } = mdMod;
expect(typeof selectRepresentativeTableResultViewModels === "function", `selectRepresentative is function`);

// Build canonical fixtures shared by smoke cases.
const backendResult = {
  doc_type: "invoice_statement",
  document_fields: {
    tableRows: [
      { itemName: "헥사", quantity: "1", unitPrice: "100", amount: "100" },
      { itemName: "이부", quantity: "2", unitPrice: "200", amount: "400" },
    ],
    tableMeta: { expectedColumnKeys: ["itemName", "quantity", "unitPrice", "amount"] },
  },
};
const templateForBackend = {
  regions: [{
    id: "table_1", name: "품목표", fieldType: "table",
    table: {
      tableName: "품목표",
      columns: [
        { index: 0, columnKey: "itemName", labelKo: "품목명" },
        { index: 1, columnKey: "amount",   labelKo: "금액" },
      ],
    },
  }],
};
const backendPlusUnstructuredResult = {
  doc_type: "invoice_statement",
  document_fields: {
    tableRows: [{ itemName: "헥사", quantity: "1", unitPrice: "100", amount: "100" }],
    tableMeta: { expectedColumnKeys: ["itemName", "quantity", "unitPrice", "amount"] },
  },
  unstructuredTables: [{
    tableKey: "items_u", labelKo: "비정형품목",
    columns: [{ columnKey: "itemName", labelKo: "품목명" }],
    rows: [{ itemName: "비정형헥사" }],
  }],
};

// ── CASE 1: backend-only ──────────────────────────────────────────────────
{
  const vms = buildTableResultViewModels(backendResult);
  const reps = selectRepresentativeTableResultViewModels(vms);
  expect(reps.length === 1 && reps[0].source === "backend_document_fields",
    "case1 backend-only: representative = backend");
  // Clean JSON: legacy path preserved (backend representative does NOT
  // override; result depends on docTableRows fed by the caller).
  const cj = buildCleanJsonResult({
    templateName: "T",
    fields: [{ name: "items", field_type: "table", value: "", ko: "품목" }],
    docTableRows: backendResult.document_fields.tableRows,
    docTableDisplayCols: [
      { key: "itemName" }, { key: "quantity" }, { key: "unitPrice" }, { key: "amount" },
    ],
    tableResultViewModels: vms,
  });
  expect(Array.isArray(cj.tables) && cj.tables.length === 1,
    "case1 backend-only cj: 1 tables entry");
  expect(!("templateTables" in cj),
    "case1 backend-only cj: no templateTables key");
  expect(!("unstructuredTables" in cj),
    "case1 backend-only cj: no unstructuredTables key");
  expect(!("columns" in cj.tables[0]),
    "case1 backend-only cj: tables[0] has no columns metadata (legacy shape)");
}

// ── CASE 2: backend + template ────────────────────────────────────────────
{
  const vms = buildTableResultViewModels(backendResult, templateForBackend);
  const reps = selectRepresentativeTableResultViewModels(vms);
  expect(reps.length === 1 && reps[0].source === "template_region_canonical",
    "case2 backend+template: representative = template");
  const cj = buildCleanJsonResult({
    templateName: "T",
    fields: [{ name: "items", field_type: "table", value: "", ko: "품목" }],
    docTableRows: backendResult.document_fields.tableRows,
    docTableDisplayCols: [
      { key: "itemName" }, { key: "quantity" }, { key: "unitPrice" }, { key: "amount" },
    ],
    tableResultViewModels: vms,
  });
  expect(Array.isArray(cj.tables) && cj.tables.length === 1,
    "case2 backend+template cj: 1 tables entry (representative)");
  expect(cj.tables[0].key === "품목표",
    "case2 backend+template cj: tables[0] uses template tableKey");
  expect(Array.isArray(cj.tables[0].columns) && cj.tables[0].columns.length === 2,
    "case2 backend+template cj: tables[0].columns shows 2 user-defined columns");
  expect(!("templateTables" in cj),
    "case2 backend+template cj: no templateTables key");
  expect(!("unstructuredTables" in cj),
    "case2 backend+template cj: no unstructuredTables key");
  const md = buildMarkdownReport({
    fields: [{ name: "items", field_type: "table", value: "", ko: "품목", label: "품목", confidence: 1 }],
    processingTime: 1.0,
    docTableRows: backendResult.document_fields.tableRows,
    tableResultViewModels: vms,
  });
  expect(/##\s*템플릿\s*테이블/.test(md),
    "case2 backend+template md: has 템플릿 테이블 section");
  expect(!/##\s*비정형\s*테이블/.test(md),
    "case2 backend+template md: NO 비정형 테이블 section");
}

// ── CASE 3: backend + unstructured ────────────────────────────────────────
{
  const vms = buildTableResultViewModels(backendPlusUnstructuredResult);
  const reps = selectRepresentativeTableResultViewModels(vms);
  expect(reps.length === 1 && reps[0].source === "unstructured_definition",
    "case3 backend+unstructured: representative = unstructured");
  const cj = buildCleanJsonResult({
    templateName: "T",
    fields: [{ name: "items", field_type: "table", value: "", ko: "품목" }],
    docTableRows: backendPlusUnstructuredResult.document_fields.tableRows,
    docTableDisplayCols: [{ key: "itemName" }],
    tableResultViewModels: vms,
  });
  expect(Array.isArray(cj.tables) && cj.tables.length === 1
    && cj.tables[0].key === "items_u",
    "case3 backend+unstructured cj: tables[0].key = unstructured tableKey");
  expect(!("templateTables" in cj),
    "case3 backend+unstructured cj: no templateTables key");
  expect(!("unstructuredTables" in cj),
    "case3 backend+unstructured cj: no unstructuredTables key");
  const md = buildMarkdownReport({
    fields: [{ name: "items", field_type: "table", value: "", ko: "품목", label: "품목", confidence: 1 }],
    processingTime: 1.0,
    tableResultViewModels: vms,
  });
  expect(/##\s*비정형\s*테이블/.test(md),
    "case3 backend+unstructured md: has 비정형 테이블 section");
  expect(!/##\s*템플릿\s*테이블/.test(md),
    "case3 backend+unstructured md: NO 템플릿 테이블 section");
}

// ── CASE 4: backend + template + unstructured ─────────────────────────────
{
  const result = {
    ...backendResult,
    unstructuredTables: [{
      tableKey: "items_u", labelKo: "비정형품목",
      columns: [{ columnKey: "itemName", labelKo: "품목명" }],
      rows: [{ itemName: "비정형" }],
    }],
  };
  const vms = buildTableResultViewModels(result, templateForBackend);
  const reps = selectRepresentativeTableResultViewModels(vms);
  expect(reps.length === 1 && reps[0].source === "template_region_canonical",
    "case4 all-sources: representative = template (priority wins)");
  const cj = buildCleanJsonResult({
    templateName: "T",
    fields: [{ name: "items", field_type: "table", value: "", ko: "품목" }],
    docTableRows: result.document_fields.tableRows,
    docTableDisplayCols: [{ key: "itemName" }],
    tableResultViewModels: vms,
  });
  expect(cj.tables.length === 1 && cj.tables[0].key === "품목표",
    "case4 all-sources cj: tables[0] uses template tableKey (not backend/unstructured)");
  expect(!("templateTables" in cj) && !("unstructuredTables" in cj),
    "case4 all-sources cj: no legacy alt keys");
  const md = buildMarkdownReport({
    fields: [{ name: "items", field_type: "table", value: "", ko: "품목", label: "품목", confidence: 1 }],
    processingTime: 1.0,
    docTableRows: result.document_fields.tableRows,
    tableResultViewModels: vms,
  });
  expect(/##\s*템플릿\s*테이블/.test(md),
    "case4 all-sources md: 템플릿 테이블 section present");
  expect(!/##\s*비정형\s*테이블/.test(md),
    "case4 all-sources md: NO 비정형 테이블 section");
}

// ── CASE 5: no table source ───────────────────────────────────────────────
{
  expect(JSON.stringify(selectRepresentativeTableResultViewModels([])) === "[]",
    "case5 no-table: empty input returns empty array");
  expect(JSON.stringify(selectRepresentativeTableResultViewModels(null)) === "[]",
    "case5 no-table: null input returns empty array");
  const cj = buildCleanJsonResult({
    templateName: "T",
    fields: [{ name: "회사명", field_type: "field", value: "ACME", ko: "회사명" }],
  });
  expect(!("tables" in cj),
    "case5 no-table cj: no tables key");
  expect(!("templateTables" in cj) && !("unstructuredTables" in cj),
    "case5 no-table cj: no alt keys");
  const md = buildMarkdownReport({
    fields: [{ name: "회사명", field_type: "field", value: "ACME", ko: "회사명", label: "회사명", confidence: 1 }],
    processingTime: 1.0,
  });
  expect(!/##\s*템플릿\s*테이블/.test(md) && !/##\s*비정형\s*테이블/.test(md),
    "case5 no-table md: no extra sections");
}

// ── CASE 6: existing Clean JSON v1 fixture (no tableResultViewModels) ─────
{
  const cj = buildCleanJsonResult({
    templateName: "거래명세서",
    fields: [
      { name: "회사명", field_type: "field", value: "ACME", ko: "회사명" },
      { name: "items", field_type: "table", value: "[[\"A\",\"1\"]]", ko: "품목" },
    ],
  });
  expect(typeof cj === "object" && cj.templateName === "거래명세서",
    "case6 legacy cj: templateName preserved");
  expect(Array.isArray(cj.info) && cj.info.length === 1,
    "case6 legacy cj: info[1]");
  expect(Array.isArray(cj.tables) && cj.tables.length === 1,
    "case6 legacy cj: tables[1] from field path");
  expect(!("columns" in cj.tables[0]),
    "case6 legacy cj: tables[0] has no columns (backward-compat byte shape)");
  expect(!("templateTables" in cj) && !("unstructuredTables" in cj),
    "case6 legacy cj: no alt keys");
}

// ── CASE 7: mutation guard ────────────────────────────────────────────────
{
  const vms = buildTableResultViewModels(backendResult, templateForBackend);
  const snap = JSON.stringify(vms);
  selectRepresentativeTableResultViewModels(vms);
  selectRepresentativeTableResultViewModels(vms);
  expect(JSON.stringify(vms) === snap,
    "case7 mutation: input view models unchanged after two calls");
}

// ---------------------------------------------------------------------------
// 8. Existing fixture runners must still PASS
// ---------------------------------------------------------------------------
try {
  execSync("node tmp/check_clean_json_v1_fixtures_js.mjs", {
    cwd: ROOT, stdio: "ignore",
  });
  ok(`Clean JSON v1 fixture runner: PASS (no regression)`);
} catch {
  fail(`Clean JSON v1 fixture runner FAILED — TPL-13B broke backward compat`);
}
try {
  execSync("node tmp/check_table_view_model_v1_fixtures_js.mjs", {
    cwd: ROOT, stdio: "ignore",
  });
  ok(`table_view_model_v1 fixture runner: PASS (no regression)`);
} catch {
  fail(`table_view_model_v1 fixture runner FAILED`);
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
