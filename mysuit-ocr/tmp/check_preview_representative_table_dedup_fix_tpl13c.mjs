#!/usr/bin/env node
// TPL-13C-PREVIEW-REPRESENTATIVE-TABLE-DEDUP-FIX
// Verifies Preview no longer shows duplicate representative tables. The fix
// is OcrResultPanel-only: a Preview-specific markdown variant that omits
// the TPL-13B `## 템플릿 테이블` / `## 비정형 테이블` sections, plus
// standalone JSX section guards keyed on `hasPreviewTableFieldRow`.
//
// Tag on success: [PREVIEW_REPRESENTATIVE_TABLE_DEDUP_FIX_TPL13C] PASS

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
const TAG = "[PREVIEW_REPRESENTATIVE_TABLE_DEDUP_FIX_TPL13C]";

const LOADER_DIR = mkdtempSync(join(tmpdir(), "tpl13c-loader-"));
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
const UNSTRUCTURED_BUILDER = resolve(ROOT, "src/components/template/UnstructuredBuilder.tsx");
const UNSTRUCTURED_DEF = resolve(ROOT, "src/components/template/utils/unstructuredDefinition.ts");
const TEST_WORKSPACE = resolve(ROOT, "src/components/test/TestWorkspace.tsx");
const BACKEND_MAIN = resolve(REPO_ROOT, "ocr-server/main.py");
const TEMPLATES_JSON = resolve(REPO_ROOT, "ocr-server/data/templates.json");

// ---------------------------------------------------------------------------
// 1. OcrResultPanel — Preview dedup primitives
// ---------------------------------------------------------------------------
const orpSrc = readSafe(OCR_RESULT_PANEL) ?? "";
const orpCode = stripComments(orpSrc);

if (!/const\s+hasPreviewTableFieldRow\s*=\s*previewTableFields\.length\s*>\s*0/.test(orpCode))
  fail(`OcrResultPanel: hasPreviewTableFieldRow flag missing`);
else ok(`OcrResultPanel: hasPreviewTableFieldRow flag present`);

// Two markdown variants
if (!/const\s+toMarkdown\s*=/.test(orpCode))
  fail(`OcrResultPanel: toMarkdown (export-bound) missing`);
else ok(`OcrResultPanel: toMarkdown (export-bound) present`);
if (!/const\s+toMarkdownForPreview\s*=/.test(orpCode))
  fail(`OcrResultPanel: toMarkdownForPreview missing`);
else ok(`OcrResultPanel: toMarkdownForPreview present`);

// toMarkdownForPreview must NOT pass tableResultViewModels to the builder
// (otherwise the duplicate sections come back). Confirm by inspecting the
// function body — it should not contain `tableResultViewModels`.
const previewMdMatch = orpCode.match(
  /const\s+toMarkdownForPreview\s*=\s*\(\)\s*=>\s*buildMarkdownReport\(\s*\{([\s\S]*?)\}\s*\)/,
);
if (!previewMdMatch) {
  fail(`OcrResultPanel: toMarkdownForPreview body does not call buildMarkdownReport({...})`);
} else if (/tableResultViewModels/.test(previewMdMatch[1])) {
  fail(`OcrResultPanel: toMarkdownForPreview must NOT pass tableResultViewModels (causes Preview duplicate)`);
} else {
  ok(`OcrResultPanel: toMarkdownForPreview omits tableResultViewModels (no duplicate sections)`);
}
// Conversely, toMarkdown (export) MUST still carry tableResultViewModels.
const exportMdMatch = orpCode.match(
  /const\s+toMarkdown\s*=\s*\(\)\s*=>\s*buildMarkdownReport\(\s*\{([\s\S]*?)\}\s*\)/,
);
if (!exportMdMatch) {
  fail(`OcrResultPanel: toMarkdown body does not call buildMarkdownReport({...})`);
} else if (!/tableResultViewModels/.test(exportMdMatch[1])) {
  fail(`OcrResultPanel: toMarkdown (export) lost tableResultViewModels — export markdown would lose section`);
} else {
  ok(`OcrResultPanel: toMarkdown (export) carries tableResultViewModels (export markdown complete)`);
}

// Preview Markdown render call site uses toMarkdownForPreview.
if (!/<Markdown[\s\S]{0,1500}>\{\s*toMarkdownForPreview\(\)\s*\}<\/Markdown>/.test(orpCode))
  fail(`Preview <Markdown> render does not use toMarkdownForPreview()`);
else ok(`Preview <Markdown> render uses toMarkdownForPreview() (TPL-13C)`);

// Export / Copy handlers still call toMarkdown() — they pass through the
// previewMode toggle. We accept either `toMarkdown()` or `previewMode === "markdown" ? toMarkdown()`.
if (!/toMarkdown\(\)/.test(orpCode))
  fail(`OcrResultPanel: no toMarkdown() call site (Copy/Export markdown payload would be empty)`);
else ok(`OcrResultPanel: toMarkdown() still referenced by handlers (Copy/Export markdown complete)`);

// Standalone JSX section guards switched to !hasPreviewTableFieldRow
// (TPL-13B used `previewTableFields.length === 0`; TPL-13C uses the named flag).
if (!/!hasPreviewTableFieldRow[\s\S]{0,200}templateRegionTableResultViewModels\.length\s*>\s*0/.test(orpCode))
  fail(`OcrResultPanel: Preview template standalone guard not switched to !hasPreviewTableFieldRow`);
else ok(`OcrResultPanel: Preview template standalone gated by !hasPreviewTableFieldRow`);
if (!/!hasPreviewTableFieldRow[\s\S]{0,400}unstructuredTableResultViewModels\.length\s*>\s*0/.test(orpCode))
  fail(`OcrResultPanel: Preview unstructured standalone guard not switched to !hasPreviewTableFieldRow`);
else ok(`OcrResultPanel: Preview unstructured standalone gated by !hasPreviewTableFieldRow`);

// Field-row uses previewRepVM (representative VM) — TPL-13B marker still intact.
if (!/previewRepVM\s*=\s*representativeFirstVM\s*\?\?\s*backendTableResultViewModel/.test(orpCode))
  fail(`OcrResultPanel: field-row previewRepVM = representativeFirstVM ?? backendTableResultViewModel missing (TPL-13B regression)`);
else ok(`OcrResultPanel: field-row uses representativeFirstVM ?? backendTableResultViewModel (TPL-13B preserved)`);

// Custom path (customRepVM) intact
if (!/customRepVM\s*=\s*representativeFirstVM\s*\?\?\s*backendTableResultViewModel/.test(orpCode))
  fail(`OcrResultPanel: Custom customRepVM = representativeFirstVM ?? backendTableResultViewModel missing (TPL-13B regression)`);
else ok(`OcrResultPanel: Custom uses representativeFirstVM ?? backendTableResultViewModel (TPL-13B preserved)`);

// ---------------------------------------------------------------------------
// 2. Files outside scope: NOT modified
// ---------------------------------------------------------------------------
// We only confirm they still exist (other phases may have modified them
// earlier; TPL-13C touches only OcrResultPanel).
for (const [label, p] of [
  ["TemplateRightPanel.tsx", TEMPLATE_RIGHT_PANEL],
  ["TemplateAnnotator.tsx", TEMPLATE_ANNOTATOR],
  ["OcrCanvasPane.tsx", OCR_CANVAS_PANE],
  ["buildTemplateExportPayload.ts", PAYLOAD_BUILDER],
  ["types/ocr.ts", TYPES_OCR],
  ["ocrTableRegion.ts", TABLE_REGION],
  ["mapOcrResponse.ts", MAPPER],
  ["extractUnstructuredTableRows.ts", EXTRACT_HELPER],
  ["tableResultViewModel.ts", VIEWMODEL_HELPER],
  ["cleanJsonBuilder.ts", CLEAN_JSON],
  ["markdownReportBuilder.ts", MARKDOWN_REPORT],
  ["UnstructuredBuilder.tsx", UNSTRUCTURED_BUILDER],
  ["unstructuredDefinition.ts", UNSTRUCTURED_DEF],
  ["TestWorkspace.tsx", TEST_WORKSPACE],
]) {
  if (!existsSync(p)) fail(`required file missing: ${label}`);
  else ok(`present: ${label}`);
}

// Tableresult helper / cleanJsonBuilder / markdownReportBuilder must NOT
// carry TPL-13C UI symbols.
for (const [label, p] of [
  ["tableResultViewModel.ts", VIEWMODEL_HELPER],
  ["cleanJsonBuilder.ts", CLEAN_JSON],
  ["markdownReportBuilder.ts", MARKDOWN_REPORT],
]) {
  const codeOnly = stripComments(readSafe(p) ?? "");
  if (/hasPreviewTableFieldRow|toMarkdownForPreview/.test(codeOnly))
    fail(`${label}: carries TPL-13C UI symbols (helpers must stay UI-free)`);
  else ok(`${label}: no TPL-13C UI symbols`);
}

// Backend / templates.json / TestWorkspace untouched
if (existsSync(BACKEND_MAIN)) {
  if (/hasPreviewTableFieldRow|toMarkdownForPreview/.test(readSafe(BACKEND_MAIN) ?? ""))
    fail(`ocr-server/main.py contains TPL-13C UI symbols`);
  else ok(`ocr-server/main.py: no TPL-13C UI symbols`);
}
if (existsSync(TEMPLATES_JSON)) {
  if (/hasPreviewTableFieldRow|toMarkdownForPreview/.test(readSafe(TEMPLATES_JSON) ?? ""))
    fail(`templates.json contains TPL-13C UI symbols`);
  else ok(`templates.json: no TPL-13C UI symbols`);
}
if (existsSync(TEST_WORKSPACE)) {
  if (/hasPreviewTableFieldRow|toMarkdownForPreview/.test(readSafe(TEST_WORKSPACE) ?? ""))
    fail(`TestWorkspace.tsx contains TPL-13C UI symbols`);
  else ok(`TestWorkspace.tsx: no TPL-13C UI symbols`);
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
// 4. Behavioral smoke: confirm the markdown helper produces a section ONLY
//    when caller supplies tableResultViewModels — i.e., toMarkdownForPreview
//    (without VMs) MUST produce a markdown that lacks the extra heading.
// ---------------------------------------------------------------------------
let mdMod = null;
try {
  mdMod = await import(pathToFileURL(MARKDOWN_REPORT).href);
  ok(`markdownReportBuilder import succeeded`);
} catch (err) { fail(`markdownReportBuilder import failed: ${err?.message ?? err}`); }
if (!mdMod) {
  console.error(`${TAG} FAIL aborting — imports failed`);
  console.error(`${TAG} FAIL count=${failures.length}`);
  process.exit(1);
}
const { buildMarkdownReport } = mdMod;

const sampleVM = {
  tableKey: "tpl",
  labelKo: "품목표",
  source: "template_region_canonical",
  columns: [{ columnKey: "a", labelKo: "A", source: "user" }],
  rows: [{ index: 0, values: { a: "1" }, cells: [{ key: "a", value: "1", displayValue: "1", isEmpty: false }] }],
  meta: { source: "template_region_canonical", rowCount: 1, columnCount: 1, hasRows: true, hasColumns: true },
};
const sampleFields = [
  { name: "items", field_type: "table", value: "", ko: "품목", label: "품목", confidence: 1 },
];

// ── CASE 1: preview-style call (no tableResultViewModels) ──────────────────
{
  const md = buildMarkdownReport({
    fields: sampleFields,
    processingTime: 1.0,
    docTableRows: [{ a: "1" }],
  });
  expect(!/##\s*템플릿\s*테이블/.test(md),
    "case1 preview-style: NO '## 템플릿 테이블' section");
  expect(!/##\s*비정형\s*테이블/.test(md),
    "case1 preview-style: NO '## 비정형 테이블' section");
  expect(md.startsWith("# OCR 결과"),
    "case1 preview-style: main heading still emitted");
}

// ── CASE 2: export-style call (with tableResultViewModels) ─────────────────
{
  const md = buildMarkdownReport({
    fields: sampleFields,
    processingTime: 1.0,
    docTableRows: [{ a: "1" }],
    tableResultViewModels: [sampleVM],
  });
  expect(/##\s*템플릿\s*테이블/.test(md),
    "case2 export-style: '## 템플릿 테이블' section appended");
}

// ── CASE 3: structural — calling toMarkdownForPreview-equivalent shouldn't
//    accidentally emit the section even if we pass an empty array ─────────
{
  const md = buildMarkdownReport({
    fields: sampleFields,
    processingTime: 1.0,
    tableResultViewModels: [],
  });
  expect(!/##\s*템플릿\s*테이블/.test(md),
    "case3 empty array: helper still omits the section (no representative VM)");
}

// ---------------------------------------------------------------------------
// 5. Re-run TPL-13B representative dedup runner (no regression)
// ---------------------------------------------------------------------------
try {
  execSync("node tmp/check_table_result_representative_dedup_tpl13b.mjs", {
    cwd: ROOT, stdio: "ignore",
  });
  ok(`TPL-13B representative dedup runner: PASS (no regression)`);
} catch {
  fail(`TPL-13B representative dedup runner FAILED — TPL-13C broke previous policy`);
}

// ---------------------------------------------------------------------------
// 6. New-file scope check
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
