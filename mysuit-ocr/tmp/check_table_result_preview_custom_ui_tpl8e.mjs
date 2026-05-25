#!/usr/bin/env node
// TPL-8E-TABLE-RESULT-PREVIEW-CUSTOM-UI
// Source-level static check: verifies OcrResultPanel.tsx now sources both
// Preview and Custom table rendering through buildTableResultViewModels,
// preserving the existing structured invoice path while exposing
// unstructured tables. UI runtime smoke is not feasible without JSX support
// in Node strip-types, so we rely on careful source-pattern assertions.
//
// Tag on success: [TABLE_RESULT_PREVIEW_CUSTOM_UI_TPL8E] PASS

import {
  readFileSync,
  existsSync,
  readdirSync,
  statSync,
} from "node:fs";
import { resolve, dirname, relative } from "node:path";
import { fileURLToPath } from "node:url";
import { execSync } from "node:child_process";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, "..");
const REPO_ROOT = resolve(ROOT, "..");
const TAG = "[TABLE_RESULT_PREVIEW_CUSTOM_UI_TPL8E]";

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

// ---------------------------------------------------------------------------
// Paths
// ---------------------------------------------------------------------------
const OCR_RESULT_PANEL = resolve(ROOT, "src/components/runocr/ui/OcrResultPanel.tsx");
const VIEWMODEL_HELPER = resolve(ROOT, "src/common/utils/tableResultViewModel.ts");
const MAPPER = resolve(ROOT, "src/components/runocr/utils/mapOcrResponse.ts");
const EXTRACT_HELPER = resolve(ROOT, "src/components/runocr/utils/extractUnstructuredTableRows.ts");
const STRUCTURED_VM = resolve(ROOT, "src/common/utils/structuredTableViewModel.ts");
const INVOICE_DISPLAY = resolve(ROOT, "src/common/utils/invoiceTableDisplay.ts");
const CLEAN_JSON = resolve(ROOT, "src/common/utils/cleanJsonBuilder.ts");
const MARKDOWN_REPORT = resolve(ROOT, "src/common/utils/markdownReportBuilder.ts");
const RUNOCR_WORKSPACE = resolve(ROOT, "src/components/runocr/RunOcrWorkspace.tsx");
const UNSTRUCTURED_BUILDER = resolve(ROOT, "src/components/template/UnstructuredBuilder.tsx");
const UNSTRUCTURED_DEF = resolve(ROOT, "src/components/template/utils/unstructuredDefinition.ts");
const TEMPLATE_RIGHT_PANEL = resolve(ROOT, "src/components/template/ui/TemplateRightPanel.tsx");
const TEST_WORKSPACE = resolve(ROOT, "src/components/test/TestWorkspace.tsx");
const OCR_CANVAS_PANE = resolve(ROOT, "src/common/ui/OcrCanvasPane.tsx");

// ---------------------------------------------------------------------------
// 1. OcrResultPanel.tsx present + sourced
// ---------------------------------------------------------------------------
if (!existsSync(OCR_RESULT_PANEL)) fail(`OcrResultPanel.tsx missing`);
else ok(`OcrResultPanel.tsx present`);

const panelSrc = readSafe(OCR_RESULT_PANEL) ?? "";
const panelCode = stripComments(panelSrc);

// ---------------------------------------------------------------------------
// 2. import buildTableResultViewModels
// ---------------------------------------------------------------------------
if (!/from\s+["']@\/common\/utils\/tableResultViewModel["']/.test(panelCode))
  fail(`OcrResultPanel does not import from @/common/utils/tableResultViewModel`);
else ok(`OcrResultPanel imports tableResultViewModel`);
if (!/\bbuildTableResultViewModels\b/.test(panelCode))
  fail(`OcrResultPanel does not reference buildTableResultViewModels`);
else ok(`OcrResultPanel references buildTableResultViewModels`);
if (!/\bTableResultViewModel\b/.test(panelCode))
  fail(`OcrResultPanel does not import TableResultViewModel type`);
else ok(`OcrResultPanel imports TableResultViewModel type`);

// ---------------------------------------------------------------------------
// 3. tableResultViewModels useMemo present
// ---------------------------------------------------------------------------
if (!/const\s+tableResultViewModels\s*=\s*useMemo\(/.test(panelCode))
  fail(`tableResultViewModels useMemo not found`);
else ok(`tableResultViewModels useMemo present`);
// TPL-10 made the second arg (activeTemplate) live. Accept either form:
// buildTableResultViewModels(result) or buildTableResultViewModels(result, <expr>).
if (!/buildTableResultViewModels\s*\(\s*result\s*[,)]/.test(panelCode))
  fail(`useMemo body does not call buildTableResultViewModels(result[, template])`);
else ok(`useMemo calls buildTableResultViewModels(result[, template])`);

// Derived backend/unstructured slots
if (!/backendTableResultViewModel/.test(panelCode))
  fail(`backendTableResultViewModel derivation missing`);
else ok(`backendTableResultViewModel derivation present`);
if (!/unstructuredTableResultViewModels/.test(panelCode))
  fail(`unstructuredTableResultViewModels derivation missing`);
else ok(`unstructuredTableResultViewModels derivation present`);
if (!/backend_document_fields/.test(panelCode))
  fail(`backend_document_fields source filter not present`);
else ok(`backend_document_fields filter present`);
if (!/unstructured_definition/.test(panelCode))
  fail(`unstructured_definition source filter not present`);
else ok(`unstructured_definition filter present`);

// ---------------------------------------------------------------------------
// 4. Preview path uses backendTableResultViewModel
// ---------------------------------------------------------------------------
// The Preview structured-table block lives inside previewTableFields.map.
// Replace marker: the if-guard references backendTableResultViewModel
// (TPL-8E) or previewRepVM (TPL-13B representative dedup).
if (!/tableIdx\s*===\s*0\s*&&\s*backendTableResultViewModel/.test(panelCode)
    && !/tableIdx\s*===\s*0\s*&&\s*previewRepVM/.test(panelCode))
  fail(`Preview structured-table guard not wired to backendTableResultViewModel / previewRepVM`);
else ok(`Preview structured-table guard uses backendTableResultViewModel or previewRepVM (TPL-8E/13B)`);

// Preview unstructured sub-section
if (!/unstructuredTableResultViewModels\.length\s*>\s*0/.test(panelCode))
  fail(`Preview/Custom unstructured sub-section guard missing`);
else ok(`unstructured sub-section guard present`);
if (!/비정형\s*테이블/.test(panelCode))
  fail(`"비정형 테이블" section header missing`);
else ok(`"비정형 테이블" section header present`);

// ---------------------------------------------------------------------------
// 5. Custom path uses backendTableResultViewModel
// ---------------------------------------------------------------------------
// Custom block in field.field_type === "table" gates on backend VM (TPL-8E)
// or customRepVM (TPL-13B representative dedup).
if (!/backendTableResultViewModel\s*\n?\s*&&\s*backendTableResultViewModel\.columns\.length/.test(panelCode)
   && !/if\s*\(\s*backendTableResultViewModel[\s\S]{0,200}columns\.length\s*>\s*0\s*\)/.test(panelCode)
   && !/customRepVM\s*&&\s*customRepVM\.columns\.length/.test(panelCode))
  fail(`Custom table guard not wired to backendTableResultViewModel / customRepVM .columns.length`);
else ok(`Custom table guard uses backendTableResultViewModel or customRepVM (TPL-8E/13B)`);

// Custom rows derived from VM cells (rather than from docTableRows.map normalization)
if (!/vm\.rows\.map\(\s*\(\s*row\s*\)\s*=>\s*\{[\s\S]{0,200}row\.cells/.test(panelCode))
  fail(`Custom baseRows not derived from vm.rows -> row.cells`);
else ok(`Custom baseRows derived from VM rows.cells`);

// Custom column iteration now uses vm.columns / col.columnKey
if (!/vm\.columns\.map\(\(col\)/.test(panelCode))
  fail(`Custom does not iterate vm.columns`);
else ok(`Custom iterates vm.columns`);
if (!/col\.columnKey/.test(panelCode))
  fail(`Custom does not reference col.columnKey`);
else ok(`Custom references col.columnKey`);
if (!/col\.labelKo/.test(panelCode))
  fail(`Custom does not reference col.labelKo`);
else ok(`Custom references col.labelKo`);

// customTableEdits state retained (Custom edit functionality intact)
if (!/setCustomTableEdits/.test(panelCode))
  fail(`customTableEdits state setter missing (Custom edit broken?)`);
else ok(`customTableEdits state setter retained`);
if (!/customTableEdits\s*\?\?\s*baseRows/.test(panelCode))
  fail(`Custom editRows fallback to baseRows missing`);
else ok(`Custom editRows = customTableEdits ?? baseRows`);

// ---------------------------------------------------------------------------
// 6. Validation path — must still work; we don't require migration but the
//    docTableRows derivation must remain because cleanJsonBuilder /
//    markdownReportBuilder still consume it (TPL-8F territory).
// ---------------------------------------------------------------------------
if (!/const\s+docTableRows\s*=\s*useMemo/.test(panelCode))
  fail(`docTableRows useMemo removed — but cleanJsonBuilder/markdownReportBuilder still need it`);
else ok(`docTableRows useMemo retained (downstream export consumers)`);

// ---------------------------------------------------------------------------
// 7. Empty state strings present
// ---------------------------------------------------------------------------
if (!/추출된 행이 없습니다/.test(panelCode))
  fail(`empty rows state '추출된 행이 없습니다.' missing`);
else ok(`empty rows state string present`);
if (!/정의된 컬럼이 없습니다/.test(panelCode))
  fail(`empty columns state '정의된 컬럼이 없습니다.' missing`);
else ok(`empty columns state string present`);

// ---------------------------------------------------------------------------
// 8. Untouched: other files not modified
// ---------------------------------------------------------------------------
const untouched = [
  ["tableResultViewModel.ts", VIEWMODEL_HELPER],
  ["mapOcrResponse.ts", MAPPER],
  ["extractUnstructuredTableRows.ts", EXTRACT_HELPER],
  ["structuredTableViewModel.ts", STRUCTURED_VM],
  ["invoiceTableDisplay.ts", INVOICE_DISPLAY],
  ["cleanJsonBuilder.ts", CLEAN_JSON],
  ["markdownReportBuilder.ts", MARKDOWN_REPORT],
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

// cleanJsonBuilder / markdownReportBuilder: phase-aware. At TPL-8E time
// neither consumed the new VM; once TPL-8F ships both do. Both states valid.
const cjSrc = stripComments(readSafe(CLEAN_JSON) ?? "");
if (/TableResultViewModel|buildTableResultViewModels/.test(cjSrc))
  note(`cleanJsonBuilder consumes TableResultViewModel (phase-aware NOTE — TPL-8F shipped)`);
else ok(`cleanJsonBuilder does not yet consume TableResultViewModel (TPL-8F still pending)`);

const mdSrc = stripComments(readSafe(MARKDOWN_REPORT) ?? "");
if (/TableResultViewModel|buildTableResultViewModels/.test(mdSrc))
  note(`markdownReportBuilder consumes TableResultViewModel (phase-aware NOTE — TPL-8F shipped)`);
else ok(`markdownReportBuilder does not yet consume TableResultViewModel (TPL-8F still pending)`);

// ---------------------------------------------------------------------------
// 9. src/lib absent + @/lib imports = 0
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
