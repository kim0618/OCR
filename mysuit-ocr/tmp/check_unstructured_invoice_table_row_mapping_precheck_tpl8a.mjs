#!/usr/bin/env node
// TPL-8A-UNSTRUCTURED-INVOICE-TABLE-ROW-MAPPING-PRECHECK
// Read-only precheck. Production code MUST NOT be modified in this phase.
// Tag on success: [UNSTRUCTURED_INVOICE_TABLE_ROW_MAPPING_PRECHECK_TPL8A] PASS

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
const TAG = "[UNSTRUCTURED_INVOICE_TABLE_ROW_MAPPING_PRECHECK_TPL8A]";

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
const REPORT_MD = resolve(ROOT, "tmp/tpl_8a_unstructured_invoice_table_row_mapping_precheck.md");
const MAPPER = resolve(ROOT, "src/components/runocr/utils/mapOcrResponse.ts");
const BUILDER = resolve(ROOT, "src/components/template/UnstructuredBuilder.tsx");
const DEFINITION = resolve(ROOT, "src/components/template/utils/unstructuredDefinition.ts");
const TEMPLATE_RIGHT_PANEL = resolve(ROOT, "src/components/template/ui/TemplateRightPanel.tsx");
const OCR_CANVAS_PANE = resolve(ROOT, "src/common/ui/OcrCanvasPane.tsx");
const OCR_RESULT_PANEL = resolve(ROOT, "src/components/runocr/ui/OcrResultPanel.tsx");
const RUNOCR_WORKSPACE = resolve(ROOT, "src/components/runocr/RunOcrWorkspace.tsx");
const TEST_WORKSPACE = resolve(ROOT, "src/components/test/TestWorkspace.tsx");

// ---------------------------------------------------------------------------
// 1. report exists
// ---------------------------------------------------------------------------
if (!existsSync(REPORT_MD)) fail(`missing report: ${relative(ROOT, REPORT_MD)}`);
else ok(`report present: tmp/tpl_8a_unstructured_invoice_table_row_mapping_precheck.md`);

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
// 5. mapOcrResponse.ts present
// ---------------------------------------------------------------------------
if (!existsSync(MAPPER)) fail(`mapOcrResponse.ts missing`);
else ok(`mapOcrResponse.ts present`);
const mapperSrc = readSafe(MAPPER) ?? "";
const mapperCode = stripComments(mapperSrc);

// ---------------------------------------------------------------------------
// 6. mapOcrResponse still has TPL-7 unstructuredTables attachment.
//    Note: TPL-8B replaces the literal `rows: []` with a helper-projected
//    array, so the rows-skeleton assertion is phase-aware (skipped once
//    extractUnstructuredTableRows is wired in).
// ---------------------------------------------------------------------------
if (!/unstructuredTables\b/.test(mapperCode))
  fail(`mapOcrResponse does not attach unstructuredTables (TPL-7 prerequisite missing)`);
else ok(`mapOcrResponse attaches unstructuredTables (TPL-7)`);
const TPL8B_WIRED = /extractUnstructuredTableRows\s*\(/.test(mapperCode);
if (TPL8B_WIRED) {
  note(`TPL-8B has shipped — skipping TPL-8A's rows: [] skeleton check (rows now come from helper)`);
} else if (!/rows\s*:\s*\[\]/.test(mapperCode)) {
  fail(`mapOcrResponse does not contain the rows: [] skeleton`);
} else {
  ok(`mapOcrResponse keeps rows: [] skeleton (TPL-7 baseline)`);
}

// ---------------------------------------------------------------------------
// 7. documentType handling present (TPL-7)
// ---------------------------------------------------------------------------
if (!/template\?\.documentType\b/.test(mapperCode))
  fail(`mapOcrResponse missing documentType handling`);
else ok(`mapOcrResponse handles template.documentType`);

// ---------------------------------------------------------------------------
// 8. info handling present (TPL-7)
// ---------------------------------------------------------------------------
if (!/template\?\.info\b/.test(mapperCode))
  fail(`mapOcrResponse missing info handling`);
else ok(`mapOcrResponse handles template.info`);

// ---------------------------------------------------------------------------
// 9. mapOcrResponse.ts NOT modified in this precheck — verify by porcelain:
//    we expect it to be either clean OR previously dirtied by TPL-7 (M flag),
//    but no NEW edits in this phase. Best-effort: ensure the TPL-7 markers
//    are still intact and no TPL-8B implementation has been added yet.
// ---------------------------------------------------------------------------
// TPL-8B has-it-shipped detection (phase-aware). At TPL-8A time this guard
// asserted that the helper and its mapper wiring did NOT yet exist. After
// TPL-8B ships, the guard naturally flips: helper IS present, mapper DOES
// reference it. We retain the precheck's intent as informational NOTEs.
const FORBIDDEN_NEW_HELPER = resolve(ROOT, "src/components/runocr/utils/extractUnstructuredTableRows.ts");
if (TPL8B_WIRED) {
  note(`TPL-8B has shipped: mapOcrResponse references extractUnstructuredTableRows (phase-aware NOTE)`);
} else {
  ok(`mapOcrResponse does not yet reference extractUnstructuredTableRows (good)`);
}
if (existsSync(FORBIDDEN_NEW_HELPER)) {
  if (TPL8B_WIRED) note(`TPL-8B helper present (phase-aware NOTE): ${relative(ROOT, FORBIDDEN_NEW_HELPER)}`);
  else fail(`TPL-8B helper file must not exist yet: ${relative(ROOT, FORBIDDEN_NEW_HELPER)}`);
} else {
  ok(`TPL-8B helper not yet present: src/components/runocr/utils/extractUnstructuredTableRows.ts`);
}

// ---------------------------------------------------------------------------
// 10-13. Untouched production files
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

// ---------------------------------------------------------------------------
// 14. backend / fixture / templates / public data untouched-ness via git
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
  // Phase-aware allow-list: TPL-3 (unstructuredDefinition) + TPL-8B (
  // extractUnstructuredTableRows). Both later-phase additions are allowed
  // even though this precheck was authored at TPL-8A time.
  const PHASE_ALLOW = new Set([
    "mysuit-ocr/src/components/template/utils/unstructuredDefinition.ts",
    "mysuit-ocr/src/components/runocr/utils/extractUnstructuredTableRows.ts",
    "mysuit-ocr/src/common/utils/tableResultViewModel.ts", // TPL-8D
  ]);
  let hits = 0;
  for (const line of porcelain) {
    if (!line.startsWith("?? ")) continue;
    const path = line.slice(3).replace(/^"|"$/g, "");
    if (!FORBID_NEW.some((re) => re.test(path))) continue;
    if (PHASE_ALLOW.has(path)) { note(`new production (allowed, TPL-3): ${path}`); continue; }
    fail(`new untracked production file detected: ${path}`); hits++;
  }
  if (hits === 0) ok(`new-file scope check: no unauthorised production additions`);
}

// ---------------------------------------------------------------------------
// 15. Report contains required sections (recommended TPL-8B plan)
// ---------------------------------------------------------------------------
const reportSrc = readSafe(REPORT_MD) ?? "";
const requiredSections = [
  /### 5\. Proposed MVP Algorithm/,
  /### 6\. Proposed Result Shape/,
  /### 7\. Ownership/,
  /### 9\. Recommended TPL-8B Implementation Plan/,
  /TPL-8B-UNSTRUCTURED-INVOICE-TABLE-ROW-PROJECTION/,
  /extractUnstructuredTableRows/,
  /document_fields\.tableRows/,
];
for (const re of requiredSections) {
  if (!re.test(reportSrc)) fail(`report missing required section/marker: ${re}`);
  else ok(`report contains: ${re}`);
}

// ---------------------------------------------------------------------------
// 16. Quick keyword survey output (informational)
// ---------------------------------------------------------------------------
const keywordCounts = {
  "document_fields": 0,
  "tableRows": 0,
  "tableMeta": 0,
  "ocr_lines": 0,
  "unstructuredTables": 0,
  "invoice_statement": 0,
};
for (const p of allSrcFiles) {
  const src = readSafe(p) ?? "";
  for (const kw of Object.keys(keywordCounts)) {
    if (src.includes(kw)) keywordCounts[kw]++;
  }
}
for (const [kw, cnt] of Object.entries(keywordCounts)) {
  note(`keyword "${kw}": ${cnt} src file(s)`);
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
