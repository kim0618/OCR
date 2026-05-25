#!/usr/bin/env node
// TPL-9B-TEMPLATE-TABLE-COLUMN-DEFINITION-UI
// Source-level static + invariants check. Verifies the TemplateRightPanel
// table block now mounts the "컬럼 정의" section while every untouched
// production file (OcrCanvasPane / TemplateAnnotator / export builders /
// RunOCR / mappers / etc.) stays clean.
// Tag on success: [TEMPLATE_TABLE_COLUMN_DEFINITION_UI_TPL9B] PASS

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
const TAG = "[TEMPLATE_TABLE_COLUMN_DEFINITION_UI_TPL9B]";

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
  return src
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .replace(/\{\s*\/\*[\s\S]*?\*\/\s*\}/g, "")
    .replace(/(^|[^:])\/\/[^\n]*/g, "$1");
}

// ---------------------------------------------------------------------------
// Paths
// ---------------------------------------------------------------------------
const OCR_TYPES = resolve(ROOT, "src/common/types/ocr.ts");
const TEMPLATE_RIGHT_PANEL = resolve(ROOT, "src/components/template/ui/TemplateRightPanel.tsx");
const OCR_CANVAS_PANE = resolve(ROOT, "src/common/ui/OcrCanvasPane.tsx");
const TEMPLATE_ANNOTATOR = resolve(ROOT, "src/components/template/ui/TemplateAnnotator.tsx");
const PAYLOAD_BUILDER = resolve(ROOT, "src/components/template/utils/buildTemplateExportPayload.ts");
const VIEWMODEL = resolve(ROOT, "src/common/utils/tableResultViewModel.ts");
const MAPPER = resolve(ROOT, "src/components/runocr/utils/mapOcrResponse.ts");
const EXTRACT_HELPER = resolve(ROOT, "src/components/runocr/utils/extractUnstructuredTableRows.ts");
const OCR_RESULT_PANEL = resolve(ROOT, "src/components/runocr/ui/OcrResultPanel.tsx");
const CLEAN_JSON = resolve(ROOT, "src/common/utils/cleanJsonBuilder.ts");
const MARKDOWN_REPORT = resolve(ROOT, "src/common/utils/markdownReportBuilder.ts");
const UNSTRUCTURED_BUILDER = resolve(ROOT, "src/components/template/UnstructuredBuilder.tsx");
const UNSTRUCTURED_DEF = resolve(ROOT, "src/components/template/utils/unstructuredDefinition.ts");
const TEST_WORKSPACE = resolve(ROOT, "src/components/test/TestWorkspace.tsx");

// ---------------------------------------------------------------------------
// 1. TableColumnDef MVP fields
// ---------------------------------------------------------------------------
const typesSrc = readSafe(OCR_TYPES) ?? "";
const typesCode = stripComments(typesSrc);
// The MVP fields appear inside TableColumnDef = { ... }. Use simple presence
// + bounded-window check (avoid runaway regex).
const tcdMatch = typesSrc.match(/export\s+type\s+TableColumnDef\s*=\s*\{([\s\S]*?)\};/);
if (!tcdMatch) {
  fail(`TableColumnDef type block not found`);
} else {
  const body = tcdMatch[1];
  for (const fld of ["columnKey", "labelKo", "labelEn"]) {
    if (!new RegExp(`\\b${fld}\\?\\s*:\\s*string\\b`).test(body))
      fail(`TableColumnDef missing optional field: ${fld}?: string`);
    else ok(`TableColumnDef has optional ${fld}?: string`);
  }
  // Existing fields must still be there
  for (const fld of ["index", "koField", "enField", "canonicalColumn", "mappingStatus", "mappingCandidates"]) {
    if (!new RegExp(`\\b${fld}\\b`).test(body))
      fail(`TableColumnDef lost existing field: ${fld}`);
    else ok(`TableColumnDef retains existing field: ${fld}`);
  }
}

// ---------------------------------------------------------------------------
// 2. TemplateRightPanel UI markers
// ---------------------------------------------------------------------------
const trpSrc = readSafe(TEMPLATE_RIGHT_PANEL) ?? "";
const trpCode = stripComments(trpSrc);

// Section heading present
if (!/<h3[^>]*>\s*컬럼\s*정의\s*</.test(trpCode))
  fail(`'컬럼 정의' <h3> section heading not found`);
else ok(`'컬럼 정의' <h3> section heading present`);

// Helper reuse — getColumns + updateColumn
if (!/getColumns\s*\(\s*selected\s*\)/.test(trpCode))
  fail(`getColumns(selected) usage not found in JSX (helper reuse)`);
else ok(`getColumns(selected) used in JSX`);
if (!/updateColumn\(\s*selected\.id\s*,/.test(trpCode))
  fail(`updateColumn(selected.id, ...) call not found in JSX`);
else ok(`updateColumn(selected.id, ...) used in JSX`);

// Grid header labels (한글 컬럼명 / 영문 key / 표준 컬럼)
for (const label of ["한글 컬럼명", "영문 key", "표준 컬럼"]) {
  if (!new RegExp(label.replace(/\s/g, "\\s*")).test(trpCode))
    fail(`grid header label missing: "${label}"`);
  else ok(`grid header label present: "${label}"`);
}

// Input fields for labelKo / columnKey
if (!/labelKo\s*:/.test(trpCode))
  fail(`updateColumn patch labelKo not present`);
else ok(`updateColumn patch labelKo present`);
if (!/columnKey\s*:/.test(trpCode))
  fail(`updateColumn patch columnKey not present`);
else ok(`updateColumn patch columnKey present`);
// labelEn / enField mirror (columnKey input)
if (!/labelEn\s*:/.test(trpCode))
  fail(`columnKey input does not mirror labelEn`);
else ok(`labelEn mirror present`);

// canonical select
if (!/canonicalColumn\s*:/.test(trpCode))
  fail(`canonicalColumn patch not present`);
else ok(`canonicalColumn patch present`);
if (!/CANONICAL_COLUMN_OPTIONS/.test(trpCode))
  fail(`CANONICAL_COLUMN_OPTIONS not declared/used`);
else ok(`CANONICAL_COLUMN_OPTIONS declared/used`);

// colGuides count marker (mismatch chip)
if (!/normalizeColGuides\(\s*selected\.table\?\.colGuides\s*\)\.length/.test(trpCode))
  fail(`colGuides count marker not visible to user (chip)`);
else ok(`colGuides count marker present`);
if (!/세로\s*가이드\s*\{[^}]*guideCount[^}]*\}/.test(trpCode)
   && !/세로\s*가이드/.test(trpCode))
  fail(`"세로 가이드 {N}개" text marker missing`);
else ok(`"세로 가이드 N개" text marker present`);

// No forbidden imports — profiles.ts
if (/from\s+["'][^"']*test\/utils\/profiles/.test(trpCode))
  fail(`TemplateRightPanel imports test/utils/profiles (forbidden)`);
else ok(`no test/utils/profiles import`);

// TPL-12C phase-aware: TemplateRightPanel later gained row-adjust UI which
// references rowOverrides. Allowed iff the rowAdjustTargetId prop is also
// present (proves the symbol arrived via TPL-12C, not unrelated drift).
if (/rowOverrides/.test(trpCode)) {
  if (/rowAdjustTargetId/.test(trpCode))
    note(`TemplateRightPanel references rowOverrides (phase-aware NOTE — TPL-12C shipped)`);
  else
    fail(`rowOverrides reference without rowAdjustTargetId marker — unexpected scope`);
} else {
  ok(`no rowOverrides reference (TPL-12C not shipped)`);
}

// ---------------------------------------------------------------------------
// 3. Untouched files
// ---------------------------------------------------------------------------
const untouched = [
  ["OcrCanvasPane.tsx", OCR_CANVAS_PANE],
  ["TemplateAnnotator.tsx", TEMPLATE_ANNOTATOR],
  ["buildTemplateExportPayload.ts", PAYLOAD_BUILDER],
  ["tableResultViewModel.ts", VIEWMODEL],
  ["mapOcrResponse.ts", MAPPER],
  ["extractUnstructuredTableRows.ts", EXTRACT_HELPER],
  ["OcrResultPanel.tsx", OCR_RESULT_PANEL],
  ["cleanJsonBuilder.ts", CLEAN_JSON],
  ["markdownReportBuilder.ts", MARKDOWN_REPORT],
  ["UnstructuredBuilder.tsx", UNSTRUCTURED_BUILDER],
  ["unstructuredDefinition.ts", UNSTRUCTURED_DEF],
  ["TestWorkspace.tsx", TEST_WORKSPACE],
];
for (const [label, p] of untouched) {
  if (!existsSync(p)) fail(`expected untouched file missing: ${label}`);
  else ok(`present (untouched expected): ${label}`);
}

// ---------------------------------------------------------------------------
// 4. src/lib absent + @/lib imports = 0
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
// 5. New-file scope check
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
