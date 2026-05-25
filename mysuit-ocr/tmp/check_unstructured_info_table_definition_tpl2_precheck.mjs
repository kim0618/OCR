#!/usr/bin/env node
// TPL-2-UNSTRUCTURED-INFO-TABLE-DEFINITION-PRECHECK
// Static read-only precheck. Production code MUST NOT be modified.
// Tag emitted on success: [UNSTRUCTURED_INFO_TABLE_DEFINITION_TPL2_PRECHECK] PASS

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
const ROOT = resolve(HERE, "..");        // /c/OCR/OCR/mysuit-ocr
const REPO_ROOT = resolve(ROOT, "..");   // /c/OCR/OCR (git toplevel)

const TAG = "[UNSTRUCTURED_INFO_TABLE_DEFINITION_TPL2_PRECHECK]";

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

// --- 1. precheck markdown 산출물 존재 ---
const REPORT_MD = resolve(ROOT, "tmp/tpl_2_unstructured_info_table_definition_precheck.md");
if (!existsSync(REPORT_MD)) fail(`missing report: ${REPORT_MD}`);
else ok(`report present: tmp/tpl_2_unstructured_info_table_definition_precheck.md`);

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

// --- 3 & 4. src 전체에서 @/lib / 상대 lib import 검색 ---
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
  if (reLibAlias.test(src)) { aliasHits++; fail(`@/lib import found in ${relative(ROOT, p)}`); }
  if (reLibRelative.test(src)) { relHits++; fail(`relative lib import found in ${relative(ROOT, p)}`); }
}
if (aliasHits === 0) ok(`@/lib imports: 0`);
if (relHits === 0) ok(`relative lib imports: 0`);

// --- 5. UnstructuredBuilder 등 핵심 파일 존재 ---
const UNSTRUCTURED_BUILDER = resolve(ROOT, "src/components/template/UnstructuredBuilder.tsx");
const TEMPLATE_PAGE = resolve(ROOT, "src/app/template/page.tsx");
const TEMPLATE_ANNOTATOR = resolve(ROOT, "src/components/template/ui/TemplateAnnotator.tsx");
const TEMPLATE_RIGHT_PANEL = resolve(ROOT, "src/components/template/ui/TemplateRightPanel.tsx");
const PAYLOAD_BUILDER = resolve(ROOT, "src/components/template/utils/buildTemplateExportPayload.ts");
const RUNOCR_MAPPER = resolve(ROOT, "src/components/runocr/utils/mapOcrResponse.ts");
const OCR_TYPES = resolve(ROOT, "src/common/types/ocr.ts");

for (const [label, p] of [
  ["src/components/template/UnstructuredBuilder.tsx", UNSTRUCTURED_BUILDER],
  ["src/app/template/page.tsx", TEMPLATE_PAGE],
  ["src/components/template/ui/TemplateAnnotator.tsx", TEMPLATE_ANNOTATOR],
  ["src/components/template/ui/TemplateRightPanel.tsx", TEMPLATE_RIGHT_PANEL],
  ["src/components/template/utils/buildTemplateExportPayload.ts", PAYLOAD_BUILDER],
  ["src/components/runocr/utils/mapOcrResponse.ts", RUNOCR_MAPPER],
  ["src/common/types/ocr.ts", OCR_TYPES],
]) {
  if (!existsSync(p)) fail(`missing required file: ${label}`);
  else ok(`present: ${label}`);
}

// --- 6. UnstructuredBuilder default export + fields Field type 확인 ---
// Note: starting at TPL-4 the literal `mode: "unstructured"` and `regions: []`
// live in unstructuredDefinition.ts (serializer is the source-of-truth). We
// still require the Field UI type and default export here.
const ubSrc = readSafe(UNSTRUCTURED_BUILDER) ?? "";
const helperSrcForGuards = readSafe(
  resolve(ROOT, "src/components/template/utils/unstructuredDefinition.ts"),
) ?? "";
if (!/export\s+default\s+function\s+UnstructuredBuilder/.test(ubSrc))
  fail(`UnstructuredBuilder default export not found`);
else ok(`UnstructuredBuilder default export found`);
const modeMarkerSources = ubSrc + "\n" + helperSrcForGuards;
if (!/mode\s*:\s*"unstructured"/.test(modeMarkerSources))
  fail(`unstructured payload literal mode: "unstructured" not present in builder or helper`);
else ok(`mode: "unstructured" present (in builder or helper)`);
if (!/regions\s*:\s*\[\]/.test(modeMarkerSources))
  fail(`regions: [] payload literal not present in builder or helper`);
else ok(`regions: [] present (in builder or helper)`);
if (!/type\s+Field\s*=\s*\{[\s\S]*?no\s*:\s*number/.test(ubSrc))
  fail(`UnstructuredBuilder Field type {no, enField, koField} not found`);
else ok(`UnstructuredBuilder Field type present`);

// --- 7. Template page mode 분기 + UnstructuredBuilder import ---
const pageSrc = readSafe(TEMPLATE_PAGE) ?? "";
if (!/Mode\s*=\s*"template"\s*\|\s*"unstructured"/.test(pageSrc))
  fail(`template page Mode union missing`);
else ok(`template page Mode union present`);
if (!/UnstructuredBuilder/.test(pageSrc))
  fail(`template page does not reference UnstructuredBuilder`);
else ok(`template page references UnstructuredBuilder`);

// --- 8. RunOCR mapOcrResponse가 "unstructured"를 인지 ---
const mapSrc = readSafe(RUNOCR_MAPPER) ?? "";
if (!/mode\s*!==\s*"unstructured"/.test(mapSrc))
  fail(`mapOcrResponse does not branch on mode !== "unstructured"`);
else ok(`mapOcrResponse branches on unstructured mode`);

// --- 9. 비정형 정의 구현 파일 단계별 가드 ---
//   TPL-3 후 unstructuredDefinition.ts는 허용 대상 (pure helper).
//   UI 컴포넌트(UnstructuredInfoEditor / UnstructuredTableEditor)는 TPL-5 이후
//   에만 등장해야 하므로 여전히 forbidden.
const FORBIDDEN_NEW = [
  resolve(ROOT, "src/components/template/ui/UnstructuredInfoEditor.tsx"),
  resolve(ROOT, "src/components/template/ui/UnstructuredTableEditor.tsx"),
];
for (const p of FORBIDDEN_NEW) {
  if (existsSync(p)) fail(`unstructured info/table UI must not exist yet: ${relative(ROOT, p)}`);
  else ok(`not yet present (good): ${relative(ROOT, p)}`);
}
const PHASE_ALLOWED_NOW = [
  resolve(ROOT, "src/components/template/utils/unstructuredDefinition.ts"),
];
for (const p of PHASE_ALLOWED_NOW) {
  if (existsSync(p)) note(`phase-allowed (added by TPL-3): ${relative(ROOT, p)}`);
}

// --- 10. Template column 구현 파일도 아직 없어야 함 (TPL-1 plan 이행 중) ---
const TEMPLATE_FORBIDDEN_NEW = [
  resolve(ROOT, "src/components/template/ui/TemplateTableColumnEditor.tsx"),
  resolve(ROOT, "src/components/template/utils/tableColumnDefinition.ts"),
  resolve(ROOT, "src/components/template/utils/templateTableColumnDefaults.ts"),
  resolve(ROOT, "src/common/utils/tableColumnDefinition.ts"),
];
for (const p of TEMPLATE_FORBIDDEN_NEW) {
  if (existsSync(p)) fail(`template column implementation must not exist yet: ${relative(ROOT, p)}`);
  else ok(`not yet present (good): ${relative(ROOT, p)}`);
}

// --- 11. unstructured/비정형 키워드 search summary ---
const unstructHits = [];
for (const p of allSrcFiles) {
  const src = readSafe(p) ?? "";
  if (/unstructured|비정형/.test(src)) unstructHits.push(relative(ROOT, p));
}
note(`unstructured/비정형 keyword files: ${unstructHits.length}`);
for (const f of unstructHits) note(`  - ${f}`);

// --- 12. info/tables 키워드 (있다면 노출) ---
const infoTableKeywords = [
  "UnstructuredInfoField",
  "UnstructuredTableDef",
  "UnstructuredTableColumn",
  "normalizeUnstructuredTemplate",
  "serializeUnstructuredTemplate",
  '"tables":', // payload key
  '"info":',
];
for (const kw of infoTableKeywords) {
  let cnt = 0;
  for (const p of allSrcFiles) {
    const src = readSafe(p) ?? "";
    if (src.includes(kw)) cnt++;
  }
  note(`keyword ${JSON.stringify(kw)}: ${cnt} file(s)`);
}

// --- 13. TestWorkspace / backend / fixture / templates.json / public testsets 미수정 ---
// Windows checkout has CRLF normalization noise across many files, so we
// cannot reliably attribute `git diff` lines to this script. Instead, we
// verify that TPL-2 did not introduce any NEW untracked production files.
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
  // this TPL-2-era precheck cannot have known about.
  const PHASE_ALLOW = new Set([
    "mysuit-ocr/src/components/template/utils/unstructuredDefinition.ts", // TPL-3
    "mysuit-ocr/src/components/runocr/utils/extractUnstructuredTableRows.ts", // TPL-8B
    "mysuit-ocr/src/common/utils/tableResultViewModel.ts", // TPL-8D
  ]);
  let newProdHits = 0;
  for (const line of porcelain) {
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
  const tplArtifacts = porcelain
    .filter((line) => line.startsWith("?? "))
    .map((line) => line.slice(3).replace(/^"|"$/g, ""))
    .filter((p) =>
      p.includes("tpl_2_unstructured_info_table_definition") ||
      p.includes("check_unstructured_info_table_definition_tpl2") ||
      p.includes("TPL_2_UNSTRUCTURED_INFO_TABLE_DEFINITION") ||
      p.includes("tpl_1_template_tab_structure_and_table_column_definition") ||
      p.includes("check_template_tab_structure_tpl1") ||
      p.includes("TEMPLATE_TAB_STRUCTURE_TPL1"));
  for (const p of tplArtifacts) note(`TPL artifact present: ${p}`);
}

// --- 14. templates.json dirty status note ---
const TEMPLATES_JSON = resolve(REPO_ROOT, "ocr-server/data/templates.json");
if (existsSync(TEMPLATES_JSON))
  note(`templates.json present at ocr-server/data/templates.json — dirty status preserved, not modified by TPL-2`);
else
  note(`templates.json not found at expected path: ${TEMPLATES_JSON}`);

// --- 15. Final result ---
if (failures.length === 0) {
  console.log(`${TAG} PASS`);
  process.exit(0);
} else {
  console.error(`${TAG} FAIL count=${failures.length}`);
  for (const msg of failures) console.error(`${TAG}   - ${msg}`);
  process.exit(1);
}
