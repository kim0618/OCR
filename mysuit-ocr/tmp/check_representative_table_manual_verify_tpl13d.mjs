#!/usr/bin/env node
// TPL-13D-REPRESENTATIVE-TABLE-MANUAL-VERIFY
// Source-marker runner. Confirms the TPL-13B/13C wiring (representative
// table dedup + Preview-only markdown variant) is intact so the human
// verifier can rely on it. Does NOT drive a browser.
//
// Tag on success: [REPRESENTATIVE_TABLE_MANUAL_VERIFY_TPL13D] PASS

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
const TAG = "[REPRESENTATIVE_TABLE_MANUAL_VERIFY_TPL13D]";

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
const VERIFY_MD = resolve(ROOT, "tmp/tpl_13d_representative_table_manual_verify.md");
const OCR_RESULT_PANEL = resolve(ROOT, "src/components/runocr/ui/OcrResultPanel.tsx");
const VIEWMODEL_HELPER = resolve(ROOT, "src/common/utils/tableResultViewModel.ts");
const CLEAN_JSON = resolve(ROOT, "src/common/utils/cleanJsonBuilder.ts");
const MARKDOWN_REPORT = resolve(ROOT, "src/common/utils/markdownReportBuilder.ts");
const TEMPLATE_RIGHT_PANEL = resolve(ROOT, "src/components/template/ui/TemplateRightPanel.tsx");
const TEMPLATE_ANNOTATOR = resolve(ROOT, "src/components/template/ui/TemplateAnnotator.tsx");
const OCR_CANVAS_PANE = resolve(ROOT, "src/common/ui/OcrCanvasPane.tsx");
const PAYLOAD_BUILDER = resolve(ROOT, "src/components/template/utils/buildTemplateExportPayload.ts");
const TYPES_OCR = resolve(ROOT, "src/common/types/ocr.ts");
const TABLE_REGION = resolve(ROOT, "src/common/utils/ocrTableRegion.ts");
const MAPPER = resolve(ROOT, "src/components/runocr/utils/mapOcrResponse.ts");
const EXTRACT_HELPER = resolve(ROOT, "src/components/runocr/utils/extractUnstructuredTableRows.ts");
const TEST_WORKSPACE = resolve(ROOT, "src/components/test/TestWorkspace.tsx");
const BACKEND_MAIN = resolve(REPO_ROOT, "ocr-server/main.py");
const TEMPLATES_JSON = resolve(REPO_ROOT, "ocr-server/data/templates.json");

// ---------------------------------------------------------------------------
// 1. Manual verify markdown present + required scenarios
// ---------------------------------------------------------------------------
if (!existsSync(VERIFY_MD)) {
  fail(`verify markdown missing: ${relative(ROOT, VERIFY_MD)}`);
} else {
  ok(`verify markdown present`);
  const md = readSafe(VERIFY_MD) ?? "";
  for (const heading of [
    /^##\s+1\.\s+Summary/m,
    /^##\s+2\.\s+Manual Checklist/m,
    /^##\s+3\.\s+Expected Result/m,
    /^##\s+4\.\s+Findings/m,
    /^##\s+5\.\s+Automatic Verification/m,
    /^##\s+6\.\s+Final Decision/m,
  ]) {
    if (!heading.test(md)) fail(`verify markdown missing section: ${heading}`);
    else ok(`verify markdown section present: ${heading.source.replace(/[\\^$?+]|\\s\+/g, " ").trim()}`);
  }
  for (const tag of [
    "Template representative Preview",
    "Template representative Custom",
    "Template representative JSON",
    "Unstructured representative Preview",
    "Backend-only Preview",
  ]) {
    if (!md.includes(tag)) fail(`verify markdown missing scenario row: ${tag}`);
    else ok(`verify markdown scenario row present: ${tag}`);
  }
}

// ---------------------------------------------------------------------------
// 2. OcrResultPanel — TPL-13B/13C wiring intact
// ---------------------------------------------------------------------------
const orpSrc = readSafe(OCR_RESULT_PANEL) ?? "";
const orpCode = stripComments(orpSrc);

if (!/const\s+toMarkdownForPreview\s*=/.test(orpCode))
  fail(`OcrResultPanel: toMarkdownForPreview missing (TPL-13C regression)`);
else ok(`OcrResultPanel: toMarkdownForPreview present (TPL-13C)`);

// toMarkdownForPreview must NOT pass tableResultViewModels.
const previewMdMatch = orpCode.match(
  /const\s+toMarkdownForPreview\s*=\s*\(\)\s*=>\s*buildMarkdownReport\(\s*\{([\s\S]*?)\}\s*\)/,
);
if (!previewMdMatch) {
  fail(`OcrResultPanel: toMarkdownForPreview body does not call buildMarkdownReport({...})`);
} else if (/tableResultViewModels/.test(previewMdMatch[1])) {
  fail(`OcrResultPanel: toMarkdownForPreview must NOT pass tableResultViewModels (Preview duplicate would return)`);
} else {
  ok(`OcrResultPanel: toMarkdownForPreview omits tableResultViewModels (Preview dedup intact)`);
}

// toMarkdown (export) MUST keep tableResultViewModels.
const exportMdMatch = orpCode.match(
  /const\s+toMarkdown\s*=\s*\(\)\s*=>\s*buildMarkdownReport\(\s*\{([\s\S]*?)\}\s*\)/,
);
if (!exportMdMatch) {
  fail(`OcrResultPanel: toMarkdown body does not call buildMarkdownReport({...})`);
} else if (!/tableResultViewModels/.test(exportMdMatch[1])) {
  fail(`OcrResultPanel: toMarkdown (export) lost tableResultViewModels — export markdown would lose section`);
} else {
  ok(`OcrResultPanel: toMarkdown (export) carries tableResultViewModels (export complete)`);
}

if (!/hasPreviewTableFieldRow/.test(orpCode))
  fail(`OcrResultPanel: hasPreviewTableFieldRow flag missing (TPL-13C regression)`);
else ok(`OcrResultPanel: hasPreviewTableFieldRow flag present (TPL-13C)`);

// Standalone section guards
if (!/!hasPreviewTableFieldRow[\s\S]{0,200}templateRegionTableResultViewModels\.length\s*>\s*0/.test(orpCode))
  fail(`OcrResultPanel: Preview template standalone guard not gated by !hasPreviewTableFieldRow`);
else ok(`OcrResultPanel: Preview template standalone gated by !hasPreviewTableFieldRow`);
if (!/!hasPreviewTableFieldRow[\s\S]{0,400}unstructuredTableResultViewModels\.length\s*>\s*0/.test(orpCode))
  fail(`OcrResultPanel: Preview unstructured standalone guard not gated by !hasPreviewTableFieldRow`);
else ok(`OcrResultPanel: Preview unstructured standalone gated by !hasPreviewTableFieldRow`);

// Preview <Markdown> uses toMarkdownForPreview
if (!/<Markdown[\s\S]{0,1500}>\{\s*toMarkdownForPreview\(\)\s*\}<\/Markdown>/.test(orpCode))
  fail(`OcrResultPanel: Preview <Markdown> does not call toMarkdownForPreview()`);
else ok(`OcrResultPanel: Preview <Markdown> calls toMarkdownForPreview() (TPL-13C)`);

// Representative VM usage (TPL-13B)
if (!/selectRepresentativeTableResultViewModels/.test(orpCode))
  fail(`OcrResultPanel: selectRepresentativeTableResultViewModels reference missing (TPL-13B regression)`);
else ok(`OcrResultPanel: uses selectRepresentativeTableResultViewModels (TPL-13B)`);
if (!/representativeFirstVM/.test(orpCode))
  fail(`OcrResultPanel: representativeFirstVM missing (TPL-13B regression)`);
else ok(`OcrResultPanel: representativeFirstVM present (TPL-13B)`);
if (!/previewRepVM/.test(orpCode))
  fail(`OcrResultPanel: previewRepVM (Preview field-row) missing (TPL-13B regression)`);
else ok(`OcrResultPanel: previewRepVM present (TPL-13B)`);
if (!/customRepVM/.test(orpCode))
  fail(`OcrResultPanel: customRepVM (Custom) missing (TPL-13B regression)`);
else ok(`OcrResultPanel: customRepVM present (TPL-13B)`);

// ---------------------------------------------------------------------------
// 3. tableResultViewModel.ts — representative selector still exported
// ---------------------------------------------------------------------------
const vmCode = stripComments(readSafe(VIEWMODEL_HELPER) ?? "");
if (!/export\s+function\s+selectRepresentativeTableResultViewModels\s*\(/.test(vmCode))
  fail(`tableResultViewModel: selectRepresentativeTableResultViewModels export missing`);
else ok(`tableResultViewModel: selectRepresentativeTableResultViewModels export present`);

// Priority chain still encoded
if (!/template_region_canonical[\s\S]{0,200}unstructured_definition[\s\S]{0,200}backend_document_fields/.test(vmCode))
  fail(`tableResultViewModel: representative priority chain missing`);
else ok(`tableResultViewModel: representative priority chain (template>unstructured>backend) present`);

// ---------------------------------------------------------------------------
// 4. cleanJsonBuilder.ts — TPL-13B dedup intact
// ---------------------------------------------------------------------------
const cjCode = stripComments(readSafe(CLEAN_JSON) ?? "");
if (!/selectRepresentativeTableResultViewModels/.test(cjCode))
  fail(`cleanJsonBuilder: representative helper not imported`);
else ok(`cleanJsonBuilder: imports representative helper (TPL-13B)`);
if (/result\.templateTables\s*=/.test(cjCode))
  fail(`cleanJsonBuilder: result.templateTables emission re-introduced`);
else ok(`cleanJsonBuilder: result.templateTables emission absent (TPL-13B dedup intact)`);
if (/result\.unstructuredTables\s*=/.test(cjCode))
  fail(`cleanJsonBuilder: result.unstructuredTables emission re-introduced`);
else ok(`cleanJsonBuilder: result.unstructuredTables emission absent (TPL-13B dedup intact)`);
// Representative override path still present
if (!/repSource\s*===\s*"template_region_canonical"\s*\|\|\s*repSource\s*===\s*"unstructured_definition"/.test(cjCode))
  fail(`cleanJsonBuilder: representative override path missing`);
else ok(`cleanJsonBuilder: representative override path present`);

// ---------------------------------------------------------------------------
// 5. markdownReportBuilder.ts — single representative section
// ---------------------------------------------------------------------------
const mdCode = stripComments(readSafe(MARKDOWN_REPORT) ?? "");
if (!/selectRepresentativeTableResultViewModels/.test(mdCode))
  fail(`markdownReportBuilder: representative helper not imported`);
else ok(`markdownReportBuilder: imports representative helper (TPL-13B)`);
if (!/repHeading/.test(mdCode))
  fail(`markdownReportBuilder: repHeading variable missing (TPL-13B regression)`);
else ok(`markdownReportBuilder: repHeading variable present (single section)`);
if (!/##\s*템플릿\s*테이블/.test(mdCode))
  fail(`markdownReportBuilder: '## 템플릿 테이블' literal missing`);
else ok(`markdownReportBuilder: '## 템플릿 테이블' literal present`);
if (!/##\s*비정형\s*테이블/.test(mdCode))
  fail(`markdownReportBuilder: '## 비정형 테이블' literal missing`);
else ok(`markdownReportBuilder: '## 비정형 테이블' literal present`);

// ---------------------------------------------------------------------------
// 6. Untouched files (existence only)
// ---------------------------------------------------------------------------
for (const [label, p] of [
  ["TemplateRightPanel.tsx", TEMPLATE_RIGHT_PANEL],
  ["TemplateAnnotator.tsx", TEMPLATE_ANNOTATOR],
  ["OcrCanvasPane.tsx", OCR_CANVAS_PANE],
  ["buildTemplateExportPayload.ts", PAYLOAD_BUILDER],
  ["types/ocr.ts", TYPES_OCR],
  ["ocrTableRegion.ts", TABLE_REGION],
  ["mapOcrResponse.ts", MAPPER],
  ["extractUnstructuredTableRows.ts", EXTRACT_HELPER],
  ["TestWorkspace.tsx", TEST_WORKSPACE],
]) {
  if (!existsSync(p)) fail(`expected file missing: ${label}`);
  else ok(`present: ${label}`);
}

// Backend / templates.json must NOT contain TPL-13B/13C UI symbols.
if (existsSync(BACKEND_MAIN)) {
  if (/hasPreviewTableFieldRow|toMarkdownForPreview|selectRepresentativeTableResultViewModels/.test(readSafe(BACKEND_MAIN) ?? ""))
    fail(`ocr-server/main.py contains TPL-13 UI symbols`);
  else ok(`ocr-server/main.py: no TPL-13 UI symbols`);
}
if (existsSync(TEMPLATES_JSON)) {
  if (/hasPreviewTableFieldRow|toMarkdownForPreview|selectRepresentativeTableResultViewModels/.test(readSafe(TEMPLATES_JSON) ?? ""))
    fail(`templates.json contains TPL-13 UI symbols`);
  else ok(`templates.json: no TPL-13 UI symbols`);
}

// ---------------------------------------------------------------------------
// 7. src/lib absent + @/lib imports = 0
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
// 8. New-file scope check
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
