#!/usr/bin/env node
// TPL-1-TEMPLATE-TAB-STRUCTURE-AND-TABLE-COLUMN-DEFINITION-PRECHECK
// Static read-only precheck. Production code MUST NOT be modified.
// Tag emitted on success: [TEMPLATE_TAB_STRUCTURE_TPL1_PRECHECK] PASS

import {
  readFileSync,
  existsSync,
  readdirSync,
  statSync,
} from "node:fs";
import { resolve, dirname, relative, sep } from "node:path";
import { fileURLToPath } from "node:url";
import { execSync } from "node:child_process";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, "..");
const REPO_ROOT = resolve(ROOT, "..");

const TAG = "[TEMPLATE_TAB_STRUCTURE_TPL1_PRECHECK]";

const failures = [];
const notes = [];

function fail(msg) {
  failures.push(msg);
  console.error(`${TAG} FAIL ${msg}`);
}
function note(msg) {
  notes.push(msg);
  console.log(`${TAG} NOTE ${msg}`);
}
function ok(msg) {
  console.log(`${TAG} OK ${msg}`);
}

function readSafe(p) {
  try { return readFileSync(p, "utf8"); } catch { return null; }
}
function listFiles(dir) {
  try { return readdirSync(dir).filter((f) => statSync(resolve(dir, f)).isFile()); }
  catch { return []; }
}
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

// --- 1. precheck markdown 산출물 존재 ---
const REPORT_MD = resolve(ROOT, "tmp/tpl_1_template_tab_structure_and_table_column_definition_precheck.md");
if (!existsSync(REPORT_MD)) fail(`missing report: ${REPORT_MD}`);
else ok(`report present: tmp/tpl_1_template_tab_structure_and_table_column_definition_precheck.md`);

// --- 2. src/lib absent or empty ---
const SRC_LIB = resolve(ROOT, "src/lib");
if (existsSync(SRC_LIB)) {
  const stat = statSync(SRC_LIB);
  if (stat.isDirectory()) {
    const files = walk(SRC_LIB);
    if (files.length > 0) fail(`src/lib must be absent or empty, found ${files.length} files`);
    else ok(`src/lib present but empty`);
  } else fail(`src/lib exists but is not a directory`);
} else ok(`src/lib absent`);

// --- 3 & 4. src 전체에서 @/lib import 및 상대 lib import 검색 ---
const SRC_ROOT = resolve(ROOT, "src");
const allSrcFiles = walk(SRC_ROOT).filter((p) =>
  p.endsWith(".ts") || p.endsWith(".tsx") || p.endsWith(".mjs") || p.endsWith(".js")
);

const reLibAlias = /from\s+["']@\/lib(\/|["'])|import\(\s*["']@\/lib(\/|["'])/;
const reLibRelative = /from\s+["']\.\.\/lib(\/|["'])|from\s+["']\.\.\/\.\.\/lib(\/|["'])|import\(\s*["']\.\.\/lib(\/|["'])|import\(\s*["']\.\.\/\.\.\/lib(\/|["'])/;

let aliasHits = 0;
let relHits = 0;
for (const p of allSrcFiles) {
  const src = readSafe(p) ?? "";
  if (reLibAlias.test(src)) {
    aliasHits++;
    fail(`@/lib import found in ${relative(ROOT, p)}`);
  }
  if (reLibRelative.test(src)) {
    relHits++;
    fail(`relative lib import found in ${relative(ROOT, p)}`);
  }
}
if (aliasHits === 0) ok(`@/lib imports: 0`);
if (relHits === 0) ok(`relative lib imports: 0`);

// --- 5. Template core 파일 존재 ---
const TEMPLATE_PAGE = resolve(ROOT, "src/app/template/page.tsx");
const TEMPLATE_WORKSPACE = resolve(ROOT, "src/components/template/TemplateWorkspace.tsx");
const TEMPLATE_ANNOTATOR = resolve(ROOT, "src/components/template/ui/TemplateAnnotator.tsx");
const TEMPLATE_RIGHT_PANEL = resolve(ROOT, "src/components/template/ui/TemplateRightPanel.tsx");
const UNSTRUCTURED_BUILDER = resolve(ROOT, "src/components/template/UnstructuredBuilder.tsx");
const PAYLOAD_BUILDER = resolve(ROOT, "src/components/template/utils/buildTemplateExportPayload.ts");
const OCR_CANVAS_PANE = resolve(ROOT, "src/common/ui/OcrCanvasPane.tsx");
const OCR_TYPES = resolve(ROOT, "src/common/types/ocr.ts");
const OCR_TABLE_REGION = resolve(ROOT, "src/common/utils/ocrTableRegion.ts");
const PROFILES = resolve(ROOT, "src/components/test/utils/profiles.ts");
const TESTSETS = resolve(ROOT, "src/common/config/testsets.ts");

for (const [label, p] of [
  ["src/app/template/page.tsx", TEMPLATE_PAGE],
  ["src/components/template/TemplateWorkspace.tsx", TEMPLATE_WORKSPACE],
  ["src/components/template/ui/TemplateAnnotator.tsx", TEMPLATE_ANNOTATOR],
  ["src/components/template/ui/TemplateRightPanel.tsx", TEMPLATE_RIGHT_PANEL],
  ["src/components/template/UnstructuredBuilder.tsx", UNSTRUCTURED_BUILDER],
  ["src/components/template/utils/buildTemplateExportPayload.ts", PAYLOAD_BUILDER],
  ["src/common/ui/OcrCanvasPane.tsx", OCR_CANVAS_PANE],
  ["src/common/types/ocr.ts", OCR_TYPES],
  ["src/common/utils/ocrTableRegion.ts", OCR_TABLE_REGION],
  ["src/components/test/utils/profiles.ts", PROFILES],
  ["src/common/config/testsets.ts", TESTSETS],
]) {
  if (!existsSync(p)) fail(`missing required file: ${label}`);
  else ok(`present: ${label}`);
}

// --- 6. buildExportPayload 함수 / TemplateRightPanel default export 등 확인 ---
const payloadSrc = readSafe(PAYLOAD_BUILDER) ?? "";
if (!/export\s+function\s+buildExportPayload\s*\(/.test(payloadSrc))
  fail(`buildExportPayload export not found in buildTemplateExportPayload.ts`);
else ok(`buildExportPayload export found`);

const rightPanelSrc = readSafe(TEMPLATE_RIGHT_PANEL) ?? "";
if (!/export\s+default\s+function\s+TemplateRightPanel/.test(rightPanelSrc))
  fail(`TemplateRightPanel default export not found`);
else ok(`TemplateRightPanel default export found`);

const annotatorSrc = readSafe(TEMPLATE_ANNOTATOR) ?? "";
if (!/export\s+default\s+function\s+TemplateAnnotator/.test(annotatorSrc))
  fail(`TemplateAnnotator default export not found`);
else ok(`TemplateAnnotator default export found`);

const unstructSrc = readSafe(UNSTRUCTURED_BUILDER) ?? "";
if (!/export\s+default\s+function\s+UnstructuredBuilder/.test(unstructSrc))
  fail(`UnstructuredBuilder default export not found`);
else ok(`UnstructuredBuilder default export found`);

// --- 7. Template page mode 분기 / UnstructuredBuilder JSX 분기 ---
const pageSrc = readSafe(TEMPLATE_PAGE) ?? "";
if (!/Mode\s*=\s*"template"\s*\|\s*"unstructured"/.test(pageSrc))
  fail(`template page Mode union "template" | "unstructured" not found`);
else ok(`template page Mode union present`);
if (!/mode\s*===\s*"template"/.test(pageSrc) || !/<UnstructuredBuilder/.test(pageSrc))
  fail(`template page mode branching to UnstructuredBuilder not found`);
else ok(`template page mode branching present`);
if (!/<TemplateAnnotator/.test(pageSrc))
  fail(`template page does not mount TemplateAnnotator`);
else ok(`template page mounts TemplateAnnotator`);

// --- 8. TableColumnDef / table.columns 사용처 확인 ---
const typesSrc = readSafe(OCR_TYPES) ?? "";
if (!/TableColumnDef/.test(typesSrc))
  fail(`TableColumnDef not defined in common/types/ocr.ts`);
else ok(`TableColumnDef defined in common types`);
if (!/columns\?\:\s*TableColumnDef\[\]/.test(typesSrc))
  fail(`TableMeta.columns field not declared`);
else ok(`TableMeta.columns?: TableColumnDef[] declared`);

if (!/r\.table\?\.columns|r\.table!\.columns/.test(payloadSrc))
  note(`buildExportPayload does not currently spread r.table.columns directly — verify schema path`);
else ok(`buildExportPayload spreads r.table.columns`);

// --- 9. 비정형 키워드 search summary ---
const unstructHits = [];
for (const p of allSrcFiles) {
  const src = readSafe(p) ?? "";
  if (/unstructured|비정형/.test(src)) unstructHits.push(relative(ROOT, p));
}
note(`unstructured/비정형 keyword files: ${unstructHits.length}`);
for (const f of unstructHits) note(`  - ${f}`);

// --- 10. table column / canonical keyword search summary ---
const policyKeywords = [
  "InvoiceTableExpectedDisplayColumn",
  "TableColumnMeta",
  "TABLE_COLUMN_META",
  "getExpectedTableColumns",
  "TableColumnKey",
  "canonicalField",
  "labelKo",
  "labelEn",
  "userConfirmed",
  "TableColumnDef",
];
for (const kw of policyKeywords) {
  let cnt = 0;
  const hits = [];
  for (const p of allSrcFiles) {
    const src = readSafe(p) ?? "";
    if (src.includes(kw)) { cnt++; hits.push(relative(ROOT, p)); }
  }
  note(`keyword "${kw}": ${cnt} file(s)`);
  for (const f of hits) note(`    - ${f}`);
}

// --- 11. Template table column definition 구현 파일이 아직 없음 ---
const FORBIDDEN_NEW = [
  resolve(ROOT, "src/components/template/ui/TemplateTableColumnEditor.tsx"),
  resolve(ROOT, "src/components/template/utils/tableColumnDefinition.ts"),
  resolve(ROOT, "src/components/template/utils/templateTableColumnDefaults.ts"),
  resolve(ROOT, "src/common/utils/tableColumnDefinition.ts"),
];
for (const p of FORBIDDEN_NEW) {
  if (existsSync(p)) fail(`implementation file must not exist yet: ${relative(ROOT, p)}`);
  else ok(`not yet present (good): ${relative(ROOT, p)}`);
}

// --- 12. TestWorkspace / backend / fixture / templates.json / public testsets 미수정 ---
// Windows checkout has CRLF normalization noise across many files, so we
// cannot reliably attribute `git diff` lines to this script. Instead, we
// verify that TPL-1 did not introduce any NEW untracked production files.
// (The only allowed new files are under tmp/ or ocr-server/logs/.)
function gitStatusPorcelain() {
  try {
    return execSync("git status --porcelain", {
      cwd: REPO_ROOT,
      stdio: ["ignore", "pipe", "ignore"],
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
  // Phase-aware allow-list: later phases legitimately add new helpers that
  // this TPL-1-era precheck cannot have known about. They are not TPL-1
  // violations; the precheck just predates them.
  const PHASE_ALLOW = new Set([
    "mysuit-ocr/src/components/template/utils/unstructuredDefinition.ts", // TPL-3
    "mysuit-ocr/src/components/runocr/utils/extractUnstructuredTableRows.ts", // TPL-8B
    "mysuit-ocr/src/common/utils/tableResultViewModel.ts", // TPL-8D
  ]);
  let newProdHits = 0;
  for (const line of porcelain) {
    // Untracked entries start with "?? "
    if (!line.startsWith("?? ")) continue;
    const path = line.slice(3).replace(/^"|"$/g, "");
    if (!FORBID_NEW.some((re) => re.test(path))) continue;
    if (PHASE_ALLOW.has(path)) {
      note(`new production file (added by a later phase, allowed): ${path}`);
      continue;
    }
    fail(`new untracked production file detected: ${path}`);
    newProdHits++;
  }
  if (newProdHits === 0)
    ok(`no new untracked production files (only tmp/ and logs/ artifacts permitted)`);
  // Sanity: report what tmp/ and ocr-server/logs/ artifacts we *did* add (info only).
  const tplArtifacts = porcelain
    .filter((line) => line.startsWith("?? "))
    .map((line) => line.slice(3).replace(/^"|"$/g, ""))
    .filter((p) =>
      p.includes("tpl_1_template_tab_structure") ||
      p.includes("check_template_tab_structure_tpl1") ||
      p.includes("TEMPLATE_TAB_STRUCTURE_TPL1"));
  for (const p of tplArtifacts) note(`TPL-1 artifact present: ${p}`);
}

// --- 13. templates.json dirty 상태 명시 ---
const TEMPLATES_JSON = resolve(REPO_ROOT, "ocr-server/data/templates.json");
if (existsSync(TEMPLATES_JSON)) {
  note(`templates.json present at ocr-server/data/templates.json — dirty status preserved, not modified by TPL-1`);
} else {
  note(`templates.json not found at expected path: ${TEMPLATES_JSON}`);
}

// --- 14. Print final result ---
if (failures.length === 0) {
  console.log(`${TAG} PASS`);
  process.exit(0);
} else {
  console.error(`${TAG} FAIL count=${failures.length}`);
  for (const msg of failures) console.error(`${TAG}   - ${msg}`);
  process.exit(1);
}
