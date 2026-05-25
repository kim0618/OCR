#!/usr/bin/env node
// TPL-5-UNSTRUCTURED-INFO-TABLE-EDITOR-UI
// UI structure + state + save/load wiring verification.
// Tag on success: [UNSTRUCTURED_INFO_TABLE_EDITOR_UI_TPL5] PASS
//
// Read-only static checks + runtime smoke that imports the helper to
// verify the serialize/normalize contract is still honored.

import {
  readFileSync,
  existsSync,
  readdirSync,
  statSync,
} from "node:fs";
import { resolve, dirname, relative } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { execSync } from "node:child_process";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, "..");
const REPO_ROOT = resolve(ROOT, "..");
const TAG = "[UNSTRUCTURED_INFO_TABLE_EDITOR_UI_TPL5]";

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
const HELPER_PATH = resolve(ROOT, "src/components/template/utils/unstructuredDefinition.ts");
const BUILDER_PATH = resolve(ROOT, "src/components/template/UnstructuredBuilder.tsx");
const TEMPLATE_RIGHT_PANEL = resolve(ROOT, "src/components/template/ui/TemplateRightPanel.tsx");
const TEMPLATE_ANNOTATOR = resolve(ROOT, "src/components/template/ui/TemplateAnnotator.tsx");
const OCR_CANVAS_PANE = resolve(ROOT, "src/common/ui/OcrCanvasPane.tsx");
const RUNOCR_MAPPER = resolve(ROOT, "src/components/runocr/utils/mapOcrResponse.ts");
const RUNOCR_WORKSPACE = resolve(ROOT, "src/components/runocr/RunOcrWorkspace.tsx");
const TEST_WORKSPACE = resolve(ROOT, "src/components/test/TestWorkspace.tsx");

if (!existsSync(HELPER_PATH)) fail(`helper missing: unstructuredDefinition.ts`);
else ok(`helper present`);

const builderSrc = readSafe(BUILDER_PATH) ?? "";
if (!builderSrc) fail(`UnstructuredBuilder.tsx missing or unreadable`);
const builderCode = stripComments(builderSrc);

// ---------------------------------------------------------------------------
// 1. helper imports (existing TPL-3/4) + new createDefault helpers (TPL-5)
// ---------------------------------------------------------------------------
if (!/from\s+["']\.\/utils\/unstructuredDefinition["']/.test(builderCode))
  fail(`UnstructuredBuilder does not import from ./utils/unstructuredDefinition`);
else ok(`UnstructuredBuilder imports from ./utils/unstructuredDefinition`);

const requiredHelperCalls = [
  "normalizeUnstructuredTemplate",
  "serializeUnstructuredTemplate",
  "createDefaultInfoField",
  "createDefaultTableDef",
  "createDefaultTableColumn",
];
for (const sym of requiredHelperCalls) {
  const re = new RegExp(`\\b${sym}\\b`);
  if (!re.test(builderCode)) fail(`UnstructuredBuilder does not reference ${sym}`);
  else ok(`UnstructuredBuilder references ${sym}`);
}

// ---------------------------------------------------------------------------
// 2. New state: documentType + tables (UI-promoted from passThroughRef)
// ---------------------------------------------------------------------------
if (!/useState\s*<\s*string\s*>\s*\(\s*""\s*\)\s*;?\s*[\s\S]{0,200}\bsetDocumentType\b|const\s+\[\s*documentType\b[\s\S]{0,40}useState/.test(builderCode))
  fail(`documentType useState not found`);
else ok(`documentType useState present`);

if (!/const\s+\[\s*tables\b[\s\S]{0,80}useState\s*<\s*UnstructuredTableDef\[\]\s*>/.test(builderCode))
  fail(`tables useState<UnstructuredTableDef[]> not found`);
else ok(`tables useState<UnstructuredTableDef[]> present`);

// passThroughRef should be gone (state promoted)
if (/passThroughRef/.test(builderCode))
  fail(`passThroughRef should be removed once state is promoted to documentType/tables`);
else ok(`passThroughRef removed`);

// ---------------------------------------------------------------------------
// 3. UI text markers
// ---------------------------------------------------------------------------
const requiredUiTexts = [
  { label: "문서 유형 label", re: /문서\s*유형/ },
  { label: "출력 정의 section title", re: /출력\s*정의/ },
  { label: "+ 영역 정의 button", re: /\+\s*영역\s*정의/ },
  { label: "+ 테이블 정의 button", re: /\+\s*테이블\s*정의/ },
  { label: "일반 영역 sub-section", re: /일반\s*영역/ },
  { label: "테이블 정의 sub-section", re: /테이블\s*정의/ },
];
for (const { label, re } of requiredUiTexts) {
  if (!re.test(builderCode)) fail(`UI marker missing: ${label}`);
  else ok(`UI marker present: ${label}`);
}

// documentType select must reference state
if (!/value=\{documentType\}/.test(builderCode))
  fail(`<select value={documentType}> binding missing`);
else ok(`documentType select binds to state`);
if (!/onChange=\{[^}]*setDocumentType/.test(builderCode))
  fail(`documentType onChange does not call setDocumentType`);
else ok(`documentType onChange calls setDocumentType`);

// Document type options sanity (MVP set)
const optionRe = /DOCUMENT_TYPE_OPTIONS\s*[:=]/;
if (!optionRe.test(builderCode))
  fail(`DOCUMENT_TYPE_OPTIONS constant missing`);
else ok(`DOCUMENT_TYPE_OPTIONS constant present`);

// ---------------------------------------------------------------------------
// 4. Save flow wires documentType + tables, info derived from fields
// ---------------------------------------------------------------------------
const saveBlockMatch = builderCode.match(/serializeUnstructuredTemplate\(\{[\s\S]*?\}\)/);
if (!saveBlockMatch) fail(`serializeUnstructuredTemplate(...) call site not found`);
else {
  const block = saveBlockMatch[0];
  if (!/documentType\s*:/.test(block))
    fail(`serialize call missing documentType property`);
  else ok(`serialize call includes documentType`);
  if (!/tables\b/.test(block))
    fail(`serialize call missing tables property`);
  else ok(`serialize call includes tables`);
  if (!/info\b/.test(block))
    fail(`serialize call missing info property`);
  else ok(`serialize call includes info`);
  if (!/templateName\s*:/.test(block))
    fail(`serialize call missing templateName property`);
  else ok(`serialize call includes templateName`);
}

// documentType empty-string → undefined (no auto-fill at builder layer either)
if (!/documentType\.trim\(\)/.test(builderCode))
  fail(`documentType not trimmed before serialize (may pass "" instead of undefined)`);
else ok(`documentType trimmed`);

// ---------------------------------------------------------------------------
// 5. Load flow sets documentType + tables + fields
// ---------------------------------------------------------------------------
if (!/setDocumentType\(\s*normalized\.documentType/.test(builderCode))
  fail(`setDocumentType(normalized.documentType ...) not found in useEffect`);
else ok(`setDocumentType wired in load`);
if (!/setTables\(\s*normalized\.tables/.test(builderCode))
  fail(`setTables(normalized.tables) not found in useEffect`);
else ok(`setTables wired in load`);
if (!/setFields\(\s*normalized\.fields/.test(builderCode))
  fail(`setFields(normalized.fields ...) not found in useEffect`);
else ok(`setFields wired in load (fields mirror)`);

// ---------------------------------------------------------------------------
// 6. Delete/reset wipes documentType + tables
// ---------------------------------------------------------------------------
const handleDeleteIdx = builderCode.indexOf("const handleDelete");
const handleDeleteBlock = handleDeleteIdx >= 0 ? builderCode.slice(handleDeleteIdx, handleDeleteIdx + 1500) : "";
if (!/setDocumentType\(\s*""\s*\)/.test(handleDeleteBlock))
  fail(`handleDelete does not reset documentType to ""`);
else ok(`handleDelete resets documentType`);
if (!/setTables\(\s*\[\s*\]\s*\)/.test(handleDeleteBlock))
  fail(`handleDelete does not reset tables to []`);
else ok(`handleDelete resets tables`);

// ---------------------------------------------------------------------------
// 7. Untouched files
// ---------------------------------------------------------------------------
for (const [label, p] of [
  ["TemplateRightPanel.tsx", TEMPLATE_RIGHT_PANEL],
  ["TemplateAnnotator.tsx", TEMPLATE_ANNOTATOR],
  ["OcrCanvasPane.tsx", OCR_CANVAS_PANE],
  ["RunOCR mapOcrResponse.ts", RUNOCR_MAPPER],
  ["RunOcrWorkspace.tsx", RUNOCR_WORKSPACE],
  ["TestWorkspace.tsx", TEST_WORKSPACE],
]) {
  if (!existsSync(p)) fail(`expected untouched file missing: ${label}`);
  else ok(`present (untouched expected): ${label}`);
}
// mapOcrResponse must not reference info/tables (TPL-7 still pending)
const mapperSrc = readSafe(RUNOCR_MAPPER) ?? "";
const mapperCode = stripComments(mapperSrc);
if (/\binfo\s*:\s*UnstructuredInfo/.test(mapperCode))
  fail(`mapOcrResponse references UnstructuredInfo (TPL-7 work not allowed)`);
else ok(`mapOcrResponse has no info/tables wiring`);

// ---------------------------------------------------------------------------
// 8. localStorage key unchanged
// ---------------------------------------------------------------------------
if (!/LOCAL_TEMPLATES_KEY\s*=\s*"mysuit_ocr_templates"/.test(builderCode))
  fail(`LOCAL_TEMPLATES_KEY changed from "mysuit_ocr_templates"`);
else ok(`localStorage key "mysuit_ocr_templates" preserved`);

// ---------------------------------------------------------------------------
// 9. fields mirror still produced by serialize (helper unchanged behavior)
//    + helper still exports the expected APIs (TPL-3 backward compat).
// ---------------------------------------------------------------------------
const helperSrc = readSafe(HELPER_PATH) ?? "";
for (const sym of [
  "export function normalizeUnstructuredTemplate",
  "export function serializeUnstructuredTemplate",
  "export function createDefaultInfoField",
  "export function createDefaultTableDef",
  "export function createDefaultTableColumn",
]) {
  if (!helperSrc.includes(sym)) fail(`helper missing: ${sym}`);
  else ok(`helper export: ${sym}`);
}

// ---------------------------------------------------------------------------
// 10. Forbidden — no Test-only profile import (boundary)
// ---------------------------------------------------------------------------
if (/from\s+["'][^"']*test\/utils\/profiles/.test(builderCode))
  fail(`UnstructuredBuilder must not import from components/test/utils/profiles.ts`);
else ok(`no Test-only profiles import`);

// ---------------------------------------------------------------------------
// 11. src/lib absent + @/lib imports = 0
// ---------------------------------------------------------------------------
const SRC_LIB = resolve(ROOT, "src/lib");
if (existsSync(SRC_LIB)) {
  const files = walk(SRC_LIB);
  if (files.length > 0) fail(`src/lib must be absent or empty`);
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
// 12. Runtime smoke — verify helper round-trip still honors invariants when
//     UnstructuredBuilder's actual save/load path is simulated.
// ---------------------------------------------------------------------------
let mod = null;
try {
  mod = await import(pathToFileURL(HELPER_PATH).href);
  ok(`runtime import succeeded`);
} catch (err) {
  fail(`runtime import failed: ${err?.message ?? String(err)}`);
}
function expect(cond, label) { if (!cond) fail(`smoke: ${label}`); else ok(`smoke: ${label}`); }
function eqJSON(a, b) { return JSON.stringify(a) === JSON.stringify(b); }

if (mod) {
  const {
    normalizeUnstructuredTemplate,
    serializeUnstructuredTemplate,
    createDefaultInfoField,
    createDefaultTableDef,
    createDefaultTableColumn,
  } = mod;

  // Simulate the new TPL-5 builder save: documentType from state, info from
  // UI fields, tables from state.
  const builderSerialize = (templateName, documentType, fields, tables) => {
    const info = fields.map((f) => {
      const en = (f.enField ?? "").trim();
      const ko = (f.koField ?? "").trim();
      const entry = {
        key: en.length > 0 ? en : `info_${f.no}`,
        labelKo: ko,
        order: f.no,
        no: f.no,
      };
      if (en.length > 0) entry.labelEn = en;
      return entry;
    });
    const trimmed = (documentType ?? "").trim();
    return serializeUnstructuredTemplate({
      templateName,
      documentType: trimmed.length > 0 ? trimmed : undefined,
      info,
      tables,
    });
  };
  const builderLoad = (saved) => {
    const n = normalizeUnstructuredTemplate(saved);
    return {
      templateName: n.templateName ?? "",
      documentType: n.documentType ?? "",
      fields: n.fields.map(({ no, enField, koField }) => ({ no, enField, koField })),
      tables: n.tables,
    };
  };

  // case 1: legacy fields-only template loaded into TPL-5 UI
  const legacy = {
    mode: "unstructured",
    templateName: "영수증_샘플",
    fields: [{ no: 1, enField: "store", koField: "상호" }],
    regions: [],
  };
  const l1 = builderLoad(legacy);
  expect(l1.documentType === "", "case 1 documentType empty (no auto-fill)");
  expect(l1.tables.length === 0, "case 1 tables empty");
  expect(l1.fields.length === 1, "case 1 fields preserved");

  // case 2: invoice template with info + tables + documentType loaded
  const newPayload = {
    mode: "unstructured",
    templateName: "거래명세서",
    documentType: "invoice_statement",
    info: [{ key: "supplier", labelKo: "공급자" }],
    tables: [
      {
        tableKey: "items",
        labelKo: "품목표",
        columns: [
          { columnKey: "itemName", labelKo: "품목명" },
          { columnKey: "quantity", labelKo: "수량" },
        ],
      },
    ],
    fields: [],
    regions: [],
  };
  const l2 = builderLoad(newPayload);
  expect(l2.documentType === "invoice_statement", "case 2 documentType state hydrated");
  expect(l2.tables.length === 1 && l2.tables[0].columns.length === 2, "case 2 tables state hydrated");
  expect(l2.fields.length === 1 && l2.fields[0].koField === "공급자", "case 2 fields mirror hydrated");

  // case 3: save round-trip preserves all three
  const saved2 = builderSerialize(l2.templateName, l2.documentType, l2.fields, l2.tables);
  expect(saved2.documentType === "invoice_statement", "case 3 saved documentType");
  expect(saved2.tables.length === 1 && saved2.tables[0].tableKey === "items", "case 3 saved tables");
  expect(saved2.fields.length === 1 && saved2.fields[0].koField === "공급자",
    "case 3 saved fields mirror");
  expect(Array.isArray(saved2.regions) && saved2.regions.length === 0, "case 3 regions: []");

  // case 4: user clears documentType (selects "선택 안 함") → omitted in payload
  const saved4 = builderSerialize("t", "", [{ no: 1, enField: "a", koField: "A" }], []);
  expect(!("documentType" in saved4), "case 4 documentType key omitted when empty");

  // case 5: user adds a new table via createDefaultTableDef — round-trips intact
  const newTable = createDefaultTableDef(1);
  newTable.columns = [createDefaultTableColumn(1)];
  const saved5 = builderSerialize("with-new-table", "receipt",
    [{ no: 1, enField: "x", koField: "X" }], [newTable]);
  expect(saved5.documentType === "receipt", "case 5 documentType receipt preserved");
  expect(saved5.tables.length === 1, "case 5 newly-added table preserved");
  expect(saved5.tables[0].tableKey === "table_1", "case 5 default tableKey");
  expect(saved5.tables[0].columns.length === 1
    && saved5.tables[0].columns[0].columnKey === "column_1",
    "case 5 default column shape");

  // case 6: default constructors honored by builder defaults
  const di = createDefaultInfoField(1);
  expect(di.key === "field_1" && di.visible === true && di.required === false,
    "case 6 createDefaultInfoField shape");
  const dt = createDefaultTableDef(1);
  expect(dt.tableKey === "table_1" && Array.isArray(dt.columns), "case 6 createDefaultTableDef shape");
  const dc = createDefaultTableColumn(1);
  expect(dc.columnKey === "column_1" && dc.source === "user", "case 6 createDefaultTableColumn shape");

  // case 7: input mutation guard
  const orig = {
    mode: "unstructured",
    documentType: "tax_invoice",
    info: [{ key: "a", labelKo: "가" }],
    tables: [{ tableKey: "t", labelKo: "T", columns: [{ columnKey: "c", labelKo: "C" }] }],
    fields: [],
    regions: [],
  };
  const snap = JSON.parse(JSON.stringify(orig));
  builderLoad(orig);
  builderSerialize("x", "tax_invoice", [{ no: 1, enField: "a", koField: "가" }], orig.tables);
  expect(eqJSON(orig, snap), "case 7 helpers do not mutate input");
}

// ---------------------------------------------------------------------------
// 13. No new untracked production files beyond the helper (TPL-3) + builder
//     update. (Builder is `M`, not `??`.) UI editor sub-files were optional
//     in the TPL-5 spec; we chose to keep everything inline, so neither
//     UnstructuredInfoEditor.tsx nor UnstructuredTableEditor.tsx should
//     exist.
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
  let newProdHits = 0;
  for (const line of porcelain) {
    if (!line.startsWith("?? ")) continue;
    const path = line.slice(3).replace(/^"|"$/g, "");
    if (!FORBID_NEW.some((re) => re.test(path))) continue;
    if (PHASE_ALLOW.has(path)) { note(`new production file (allowed by TPL-3): ${path}`); continue; }
    fail(`new untracked production file detected: ${path}`);
    newProdHits++;
  }
  if (newProdHits === 0) ok(`new-file scope check: clean`);
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
