#!/usr/bin/env node
// TPL-8C-TEMPLATE-AND-UNSTRUCTURED-TABLE-RESULT-ALIGNMENT-PRECHECK
// Read-only precheck. Production code MUST NOT be modified.
// Tag on success: [TABLE_RESULT_ALIGNMENT_PRECHECK_TPL8C] PASS

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
const TAG = "[TABLE_RESULT_ALIGNMENT_PRECHECK_TPL8C]";

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

// ---------------------------------------------------------------------------
// Paths
// ---------------------------------------------------------------------------
const REPORT_MD = resolve(ROOT, "tmp/tpl_8c_template_and_unstructured_table_result_alignment_precheck.md");
const OCR_RESULT_PANEL = resolve(ROOT, "src/components/runocr/ui/OcrResultPanel.tsx");
const MAPPER = resolve(ROOT, "src/components/runocr/utils/mapOcrResponse.ts");
const EXTRACT_HELPER = resolve(ROOT, "src/components/runocr/utils/extractUnstructuredTableRows.ts");
const STRUCTURED_VM = resolve(ROOT, "src/common/utils/structuredTableViewModel.ts");
const INVOICE_DISPLAY = resolve(ROOT, "src/common/utils/invoiceTableDisplay.ts");
const CLEAN_JSON = resolve(ROOT, "src/common/utils/cleanJsonBuilder.ts");
const MARKDOWN_REPORT = resolve(ROOT, "src/common/utils/markdownReportBuilder.ts");
const TEMPLATE_RIGHT_PANEL = resolve(ROOT, "src/components/template/ui/TemplateRightPanel.tsx");
const OCR_CANVAS_PANE = resolve(ROOT, "src/common/ui/OcrCanvasPane.tsx");
const PAYLOAD_BUILDER = resolve(ROOT, "src/components/template/utils/buildTemplateExportPayload.ts");
const OCR_TYPES = resolve(ROOT, "src/common/types/ocr.ts");
const UNSTRUCTURED_BUILDER = resolve(ROOT, "src/components/template/UnstructuredBuilder.tsx");
const UNSTRUCTURED_DEF = resolve(ROOT, "src/components/template/utils/unstructuredDefinition.ts");
const TEST_WORKSPACE = resolve(ROOT, "src/components/test/TestWorkspace.tsx");

// ---------------------------------------------------------------------------
// 1. Report exists
// ---------------------------------------------------------------------------
if (!existsSync(REPORT_MD)) fail(`missing report: ${relative(ROOT, REPORT_MD)}`);
else ok(`report present: tmp/tpl_8c_template_and_unstructured_table_result_alignment_precheck.md`);

// ---------------------------------------------------------------------------
// 2. src/lib absent
// ---------------------------------------------------------------------------
const SRC_LIB = resolve(ROOT, "src/lib");
if (existsSync(SRC_LIB)) {
  const f = walk(SRC_LIB);
  if (f.length > 0) fail(`src/lib must be absent or empty`);
  else ok(`src/lib present but empty`);
} else ok(`src/lib absent`);

// ---------------------------------------------------------------------------
// 3-4. @/lib + relative lib imports = 0
// ---------------------------------------------------------------------------
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
// 5-12. Key files exist + content summary
// ---------------------------------------------------------------------------
const requiredFiles = [
  ["OcrResultPanel.tsx", OCR_RESULT_PANEL],
  ["mapOcrResponse.ts", MAPPER],
  ["extractUnstructuredTableRows.ts", EXTRACT_HELPER],
  ["structuredTableViewModel.ts", STRUCTURED_VM],
  ["invoiceTableDisplay.ts", INVOICE_DISPLAY],
  ["cleanJsonBuilder.ts", CLEAN_JSON],
  ["markdownReportBuilder.ts", MARKDOWN_REPORT],
  ["TemplateRightPanel.tsx", TEMPLATE_RIGHT_PANEL],
  ["OcrCanvasPane.tsx", OCR_CANVAS_PANE],
  ["buildTemplateExportPayload.ts", PAYLOAD_BUILDER],
  ["common/types/ocr.ts", OCR_TYPES],
  ["UnstructuredBuilder.tsx", UNSTRUCTURED_BUILDER],
  ["unstructuredDefinition.ts", UNSTRUCTURED_DEF],
  ["TestWorkspace.tsx", TEST_WORKSPACE],
];
for (const [label, p] of requiredFiles) {
  if (!existsSync(p)) fail(`missing required file: ${label}`);
  else ok(`present: ${label}`);
}

// ---------------------------------------------------------------------------
// 13. New-file scope check + no operational source modified by this precheck.
//     (We don't grep for content drift — just verify no new production
//     files appeared beyond the phase-allow list.)
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
  if (hits === 0) ok(`new-file scope check: no unauthorised production additions`);
}

// ---------------------------------------------------------------------------
// 14-16. Report must contain required sections
// ---------------------------------------------------------------------------
const reportSrc = readSafe(REPORT_MD) ?? "";
const requiredSections = [
  { name: "Preview vs Custom Analysis", re: /### 5\. Preview vs Custom Analysis/ },
  { name: "Proposed Common TableResult ViewModel", re: /### 6\. Proposed Common TableResult ViewModel/ },
  { name: "Proposed Ownership", re: /### 7\. Proposed Ownership/ },
  { name: "Implementation Plan", re: /### 8\. Implementation Plan/ },
  { name: "TPL-8D micro-step", re: /TPL-8D-TABLE-RESULT-VIEWMODEL-HELPER/ },
  { name: "TPL-8E micro-step", re: /TPL-8E-TABLE-RESULT-PREVIEW-CUSTOM-UI/ },
  { name: "TPL-8F micro-step", re: /TPL-8F-TABLE-RESULT-EXPORT-INTEGRATION/ },
  { name: "TPL-9 micro-step", re: /TPL-9-TEMPLATE-TABLE-COLUMN-DEFINITION-UI/ },
  { name: "TPL-10 micro-step", re: /TPL-10-TEMPLATE-TABLE-COLUMN-RESULT-PROJECTION/ },
  { name: "TableResultViewModel type", re: /type\s+TableResultViewModel/ },
  { name: "TableResultSource type", re: /type\s+TableResultSource/ },
  { name: "Risk Assessment", re: /### 9\. Risk Assessment/ },
];
for (const { name, re } of requiredSections) {
  if (!re.test(reportSrc)) fail(`report missing required section/marker: ${name}`);
  else ok(`report contains: ${name}`);
}

// ---------------------------------------------------------------------------
// 17. Informational keyword counts (table result data sources visibility)
// ---------------------------------------------------------------------------
const keywords = {
  "document_fields": 0,
  "tableRows": 0,
  "unstructuredTables": 0,
  "buildStructuredTableViewModel": 0,
  "buildInvoicePreviewCols": 0,
  "buildCleanJsonResult": 0,
  "buildMarkdownReport": 0,
  "TableColumnDef": 0,
};
for (const p of allSrcFiles) {
  const src = readSafe(p) ?? "";
  for (const kw of Object.keys(keywords)) {
    if (src.includes(kw)) keywords[kw]++;
  }
}
for (const [kw, cnt] of Object.entries(keywords)) {
  note(`keyword "${kw}": ${cnt} src file(s)`);
}

// Sanity: phase-aware — at TPL-8C time OcrResultPanel did NOT consume
// unstructuredTables; once TPL-8E ships it does. Both states are valid.
const orpCode = readSafe(OCR_RESULT_PANEL) ?? "";
const _tpl8eShipped_8c = /\bbuildTableResultViewModels\b/.test(orpCode);
if (/\bunstructuredTables\b/.test(orpCode)) {
  if (_tpl8eShipped_8c) note(`OcrResultPanel consumes unstructuredTables (phase-aware NOTE — TPL-8E shipped)`);
  else fail(`OcrResultPanel already consumes unstructuredTables — TPL-8E should still be pending`);
} else {
  ok(`OcrResultPanel does not yet consume unstructuredTables (TPL-8E still pending — good)`);
}
// Sanity: tableResultViewModel.ts — phase-aware. At TPL-8C time this guard
// asserted the file did NOT yet exist. After TPL-8D ships, the guard flips
// to an informational NOTE.
const FUTURE_VM = resolve(ROOT, "src/common/utils/tableResultViewModel.ts");
if (existsSync(FUTURE_VM)) {
  note(`tableResultViewModel.ts present (phase-aware NOTE — TPL-8D shipped)`);
} else {
  ok(`tableResultViewModel.ts not yet present (TPL-8D still pending — good)`);
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
