#!/usr/bin/env node
// TPL-9A-TEMPLATE-TABLE-COLUMN-DEFINITION-PRECHECK
// Read-only precheck. No production code is modified.
// Tag on success: [TEMPLATE_TABLE_COLUMN_DEFINITION_PRECHECK_TPL9A] PASS

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
const TAG = "[TEMPLATE_TABLE_COLUMN_DEFINITION_PRECHECK_TPL9A]";

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
const REPORT_MD = resolve(ROOT, "tmp/tpl_9a_template_table_column_definition_precheck.md");
const TEMPLATE_RIGHT_PANEL = resolve(ROOT, "src/components/template/ui/TemplateRightPanel.tsx");
const TEMPLATE_ANNOTATOR = resolve(ROOT, "src/components/template/ui/TemplateAnnotator.tsx");
const OCR_CANVAS_PANE = resolve(ROOT, "src/common/ui/OcrCanvasPane.tsx");
const OCR_TYPES = resolve(ROOT, "src/common/types/ocr.ts");
const PAYLOAD_BUILDER = resolve(ROOT, "src/components/template/utils/buildTemplateExportPayload.ts");
const OCR_TABLE_REGION = resolve(ROOT, "src/common/utils/ocrTableRegion.ts");
const VIEWMODEL = resolve(ROOT, "src/common/utils/tableResultViewModel.ts");
const MAPPER = resolve(ROOT, "src/components/runocr/utils/mapOcrResponse.ts");
const OCR_RESULT_PANEL = resolve(ROOT, "src/components/runocr/ui/OcrResultPanel.tsx");
const UNSTRUCTURED_BUILDER = resolve(ROOT, "src/components/template/UnstructuredBuilder.tsx");
const UNSTRUCTURED_DEF = resolve(ROOT, "src/components/template/utils/unstructuredDefinition.ts");
const TEST_WORKSPACE = resolve(ROOT, "src/components/test/TestWorkspace.tsx");
const CLEAN_JSON = resolve(ROOT, "src/common/utils/cleanJsonBuilder.ts");
const MARKDOWN_REPORT = resolve(ROOT, "src/common/utils/markdownReportBuilder.ts");

// ---------------------------------------------------------------------------
// 1. Report present
// ---------------------------------------------------------------------------
if (!existsSync(REPORT_MD)) fail(`missing report: ${relative(ROOT, REPORT_MD)}`);
else ok(`report present: tmp/tpl_9a_template_table_column_definition_precheck.md`);

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
// 5-9. Key files exist
// ---------------------------------------------------------------------------
const requiredFiles = [
  ["TemplateRightPanel.tsx", TEMPLATE_RIGHT_PANEL],
  ["TemplateAnnotator.tsx", TEMPLATE_ANNOTATOR],
  ["OcrCanvasPane.tsx", OCR_CANVAS_PANE],
  ["common/types/ocr.ts", OCR_TYPES],
  ["buildTemplateExportPayload.ts", PAYLOAD_BUILDER],
  ["ocrTableRegion.ts", OCR_TABLE_REGION],
  ["tableResultViewModel.ts", VIEWMODEL],
  ["mapOcrResponse.ts", MAPPER],
  ["OcrResultPanel.tsx", OCR_RESULT_PANEL],
  ["UnstructuredBuilder.tsx", UNSTRUCTURED_BUILDER],
  ["unstructuredDefinition.ts", UNSTRUCTURED_DEF],
  ["TestWorkspace.tsx", TEST_WORKSPACE],
  ["cleanJsonBuilder.ts", CLEAN_JSON],
  ["markdownReportBuilder.ts", MARKDOWN_REPORT],
];
for (const [label, p] of requiredFiles) {
  if (!existsSync(p)) fail(`missing required file: ${label}`);
  else ok(`present: ${label}`);
}

// ---------------------------------------------------------------------------
// 10-12. Type / marker summary (informational + invariants)
// ---------------------------------------------------------------------------
const typesSrc = readSafe(OCR_TYPES) ?? "";
if (!/export\s+type\s+TableColumnDef\s*=\s*\{/.test(typesSrc))
  fail(`TableColumnDef type not exported from common/types/ocr.ts`);
else ok(`TableColumnDef type exported`);
if (!/columns\?\:\s*TableColumnDef\[\]/.test(typesSrc))
  fail(`TableMeta.columns?: TableColumnDef[] declaration missing`);
else ok(`TableMeta.columns?: TableColumnDef[] declared`);
if (!/rowTemplate\?\:\s*Rect/.test(typesSrc))
  fail(`TableMeta.rowTemplate?: Rect declaration missing`);
else ok(`TableMeta.rowTemplate?: Rect declared`);
if (!/colGuides\?\:\s*number\[\]/.test(typesSrc))
  fail(`TableMeta.colGuides?: number[] declaration missing`);
else ok(`TableMeta.colGuides?: number[] declared`);
if (!/mode\?\:\s*"repeat"\s*\|\s*"auto"/.test(typesSrc))
  fail(`TableMeta.mode?: "repeat" | "auto" declaration missing`);
else ok(`TableMeta.mode?: "repeat" | "auto" declared`);

// TemplateRightPanel still has the helpers but no JSX column section yet
const trpSrc = readSafe(TEMPLATE_RIGHT_PANEL) ?? "";
if (!/function\s+getColumns\b/.test(trpSrc))
  fail(`TemplateRightPanel getColumns helper missing (TPL-9 prerequisite)`);
else ok(`TemplateRightPanel getColumns helper present`);
if (!/function\s+updateColumn\b/.test(trpSrc))
  fail(`TemplateRightPanel updateColumn helper missing`);
else ok(`TemplateRightPanel updateColumn helper present`);
// Phase-aware: at TPL-9A the column editor JSX is NOT yet mounted; once
// TPL-9B ships it is. Both states are valid.
const trpStripped = trpSrc
  .replace(/\/\*[\s\S]*?\*\//g, "")
  .replace(/\{\s*\/\*[\s\S]*?\*\/\s*\}/g, "")
  .replace(/(^|[^:])\/\/[^\n]*/g, "$1");
if (/<h3[^>]*>\s*컬럼\s*정의\s*</.test(trpStripped))
  note(`TemplateRightPanel has '컬럼 정의' <h3> section (phase-aware NOTE — TPL-9B shipped)`);
else ok(`TemplateRightPanel does not yet have '컬럼 정의' <h3> section (TPL-9B pending — good)`);

// OcrCanvasPane has rowTemplate + colGuides handlers
const canvasSrc = readSafe(OCR_CANVAS_PANE) ?? "";
if (!/drawRowTemplate/.test(canvasSrc))
  fail(`OcrCanvasPane drawRowTemplate handler missing`);
else ok(`OcrCanvasPane drawRowTemplate handler present`);
if (!/colGuideTargetId/.test(canvasSrc))
  fail(`OcrCanvasPane colGuideTargetId handling missing`);
else ok(`OcrCanvasPane colGuideTargetId handling present`);

// buildTemplateExportPayload spreads columns
const payloadSrc = readSafe(PAYLOAD_BUILDER) ?? "";
if (!/r\.table\?\.columns/.test(payloadSrc))
  fail(`buildTemplateExportPayload does not spread r.table.columns`);
else ok(`buildTemplateExportPayload spreads r.table.columns`);

// buildTableRows iterates with rowTemplate.height
const tableRegionSrc = readSafe(OCR_TABLE_REGION) ?? "";
if (!/buildTableRows/.test(tableRegionSrc))
  fail(`ocrTableRegion.buildTableRows not exported`);
else ok(`ocrTableRegion.buildTableRows present`);

// ---------------------------------------------------------------------------
// 13. No production code modified by this precheck — only tmp/* and logs.
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
// 14-17. Report contains required sections + plans
// ---------------------------------------------------------------------------
const reportSrc = readSafe(REPORT_MD) ?? "";
const requiredSections = [
  { name: "Row Strategy", re: /### 4\. Row Strategy/ },
  { name: "Column Strategy", re: /### 5\. Column Strategy/ },
  { name: "Proposed Template Table Columns Schema", re: /### 6\. Proposed Template Table Columns Schema/ },
  { name: "Proposed UI Layout", re: /### 7\. Proposed UI Layout/ },
  { name: "Interaction with TableResultViewModel", re: /### 8\. Interaction with TableResultViewModel/ },
  { name: "Risk Assessment", re: /### 9\. Risk Assessment/ },
  { name: "Recommended Implementation Plan", re: /### 10\. Recommended Implementation Plan/ },
  { name: "TPL-9B plan", re: /TPL-9B-TEMPLATE-TABLE-COLUMN-DEFINITION-UI/ },
  { name: "TPL-9C plan", re: /TPL-9C-TEMPLATE-TABLE-COLUMN-SAVE-LOAD/ },
  { name: "TPL-10 plan", re: /TPL-10-TEMPLATE-TABLE-COLUMN-RESULT-PROJECTION/ },
  { name: "TPL-11 plan", re: /TPL-11-TEMPLATE-TABLE-ROW-OVERRIDES-PRECHECK/ },
  { name: "TableColumnDef schema draft", re: /columnKey\?/ },
  { name: "rowOverrides discussion", re: /rowOverrides/ },
];
for (const { name, re } of requiredSections) {
  if (!re.test(reportSrc)) fail(`report missing section/marker: ${name}`);
  else ok(`report contains: ${name}`);
}

// ---------------------------------------------------------------------------
// 18. Informational keyword counts
// ---------------------------------------------------------------------------
const keywords = {
  "TableColumnDef": 0,
  "rowTemplate": 0,
  "colGuides": 0,
  "buildTableRows": 0,
  "normalizeColGuides": 0,
  "table.columns": 0,
};
for (const p of allSrcFiles) {
  const src = readSafe(p) ?? "";
  for (const kw of Object.keys(keywords)) if (src.includes(kw)) keywords[kw]++;
}
for (const [kw, cnt] of Object.entries(keywords)) note(`keyword "${kw}": ${cnt} src file(s)`);

// ---------------------------------------------------------------------------
if (failures.length === 0) {
  console.log(`${TAG} PASS`);
  process.exit(0);
} else {
  console.error(`${TAG} FAIL count=${failures.length}`);
  for (const m of failures) console.error(`${TAG}   - ${m}`);
  process.exit(1);
}
