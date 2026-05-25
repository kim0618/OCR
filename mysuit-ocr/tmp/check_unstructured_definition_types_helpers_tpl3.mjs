#!/usr/bin/env node
// TPL-3-UNSTRUCTURED-DEFINITION-TYPES-AND-HELPERS
// Static + runtime smoke check. Production scope: only the one new file
// src/components/template/utils/unstructuredDefinition.ts is allowed.
// All UI/save/load/RunOCR/Test/backend paths must be untouched.
//
// Runtime smoke imports the .ts helper directly via Node 22+ TS strip-types.

import {
  readFileSync,
  existsSync,
  readdirSync,
  statSync,
} from "node:fs";
import { resolve, dirname, relative } from "node:path";
import { fileURLToPath } from "node:url";
import { pathToFileURL } from "node:url";
import { execSync } from "node:child_process";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, "..");
const REPO_ROOT = resolve(ROOT, "..");

const TAG = "[UNSTRUCTURED_DEFINITION_TYPES_HELPERS_TPL3]";

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
// 1. New helper file must exist
// ---------------------------------------------------------------------------
const HELPER_PATH = resolve(ROOT, "src/components/template/utils/unstructuredDefinition.ts");
if (!existsSync(HELPER_PATH)) {
  fail(`missing helper: ${relative(ROOT, HELPER_PATH)}`);
} else {
  ok(`present: src/components/template/utils/unstructuredDefinition.ts`);
}

// ---------------------------------------------------------------------------
// 2-5. Untouched production files (UnstructuredBuilder / TemplateRightPanel /
//      RunOCR / TestWorkspace). We re-check existence + ensure that no new
//      production files were introduced beyond the single allowed helper.
// ---------------------------------------------------------------------------
const UNSTRUCTURED_BUILDER = resolve(ROOT, "src/components/template/UnstructuredBuilder.tsx");
const TEMPLATE_RIGHT_PANEL = resolve(ROOT, "src/components/template/ui/TemplateRightPanel.tsx");
const TEMPLATE_ANNOTATOR = resolve(ROOT, "src/components/template/ui/TemplateAnnotator.tsx");
const OCR_CANVAS_PANE = resolve(ROOT, "src/common/ui/OcrCanvasPane.tsx");
const RUNOCR_MAPPER = resolve(ROOT, "src/components/runocr/utils/mapOcrResponse.ts");
const TEST_WORKSPACE = resolve(ROOT, "src/components/test/TestWorkspace.tsx");

for (const [label, p] of [
  ["UnstructuredBuilder.tsx", UNSTRUCTURED_BUILDER],
  ["TemplateRightPanel.tsx", TEMPLATE_RIGHT_PANEL],
  ["TemplateAnnotator.tsx", TEMPLATE_ANNOTATOR],
  ["OcrCanvasPane.tsx", OCR_CANVAS_PANE],
  ["RunOCR mapOcrResponse.ts", RUNOCR_MAPPER],
  ["TestWorkspace.tsx", TEST_WORKSPACE],
]) {
  if (!existsSync(p)) fail(`expected file missing: ${label}`);
  else ok(`present (untouched expected): ${label}`);
}

// ---------------------------------------------------------------------------
// 6. src/lib absent
// ---------------------------------------------------------------------------
const SRC_LIB = resolve(ROOT, "src/lib");
if (existsSync(SRC_LIB)) {
  const files = walk(SRC_LIB);
  if (files.length > 0) fail(`src/lib must be absent or empty, found ${files.length} files`);
  else ok(`src/lib present but empty`);
} else ok(`src/lib absent`);

// ---------------------------------------------------------------------------
// 7. @/lib + relative lib imports = 0
// ---------------------------------------------------------------------------
const SRC_ROOT = resolve(ROOT, "src");
const allSrcFiles = walk(SRC_ROOT).filter((p) =>
  p.endsWith(".ts") || p.endsWith(".tsx") || p.endsWith(".mjs") || p.endsWith(".js")
);
const reLibAlias = /from\s+["']@\/lib(\/|["'])|import\(\s*["']@\/lib(\/|["'])/;
const reLibRelative = /from\s+["']\.\.\/lib(\/|["'])|from\s+["']\.\.\/\.\.\/lib(\/|["'])|import\(\s*["']\.\.\/lib(\/|["'])|import\(\s*["']\.\.\/\.\.\/lib(\/|["'])/;
let aliasHits = 0, relHits = 0;
for (const p of allSrcFiles) {
  const src = readSafe(p) ?? "";
  if (reLibAlias.test(src)) { aliasHits++; fail(`@/lib import in ${relative(ROOT, p)}`); }
  if (reLibRelative.test(src)) { relHits++; fail(`relative lib import in ${relative(ROOT, p)}`); }
}
if (aliasHits === 0) ok(`@/lib imports: 0`);
if (relHits === 0) ok(`relative lib imports: 0`);

// ---------------------------------------------------------------------------
// 8. Forbidden imports inside the new helper file
//    (React, DOM, window/document, localStorage, sessionStorage, IndexedDB,
//     fetch, XHR, backend, fixture, templates.json, public/data, UI components)
// ---------------------------------------------------------------------------
const helperSrcRaw = readSafe(HELPER_PATH) ?? "";
const helperSrc = helperSrcRaw; // for export/type/decl grep (comments OK)
// Strip /* ... */ and // ... comments before scanning for forbidden imports /
// runtime symbols — otherwise the boundary docstring itself would trip the
// regex.
const helperSrcStripped = helperSrcRaw
  .replace(/\/\*[\s\S]*?\*\//g, "")
  .replace(/(^|[^:])\/\/[^\n]*/g, "$1");
const forbiddenImportPatterns = [
  { name: "react", re: /from\s+["']react["']|from\s+["']react\// },
  { name: "next", re: /from\s+["']next\// },
  { name: "react-dom", re: /from\s+["']react-dom/ },
  { name: "axios", re: /from\s+["']axios["']/ },
  { name: "fetch (named)", re: /\bimport\s*\{\s*fetch\b/ },
  { name: "ui components", re: /from\s+["'][^"']*ui\//i },
  { name: "fixture path", re: /from\s+["'][^"']*fixtures?\// },
  { name: "templates.json", re: /templates\.json/ },
  { name: "public/data", re: /from\s+["'][^"']*public\/data\// },
];
for (const { name, re } of forbiddenImportPatterns) {
  if (re.test(helperSrcStripped)) fail(`forbidden import in helper: ${name}`);
}
// Forbidden runtime symbol usage
const forbiddenRuntimePatterns = [
  { name: "window.", re: /\bwindow\s*\./ },
  { name: "document.", re: /\bdocument\s*\./ },
  { name: "localStorage", re: /\blocalStorage\b/ },
  { name: "sessionStorage", re: /\bsessionStorage\b/ },
  { name: "indexedDB", re: /\bindexedDB\b/ },
  { name: "fetch(", re: /\bfetch\s*\(/ },
  { name: "XMLHttpRequest", re: /\bXMLHttpRequest\b/ },
];
for (const { name, re } of forbiddenRuntimePatterns) {
  if (re.test(helperSrcStripped)) fail(`forbidden runtime use in helper: ${name}`);
}
ok(`helper has no forbidden imports / runtime symbols`);

// ---------------------------------------------------------------------------
// 9-13. Required exports present
// ---------------------------------------------------------------------------
const requiredExports = [
  "normalizeUnstructuredTemplate",
  "serializeUnstructuredTemplate",
  "createDefaultInfoField",
  "createDefaultTableDef",
  "createDefaultTableColumn",
];
for (const name of requiredExports) {
  const re = new RegExp(`export\\s+function\\s+${name}\\b`);
  if (!re.test(helperSrc)) fail(`required export missing: ${name}`);
  else ok(`export present: ${name}`);
}

const requiredTypes = [
  "LegacyUnstructuredField",
  "UnstructuredInfoField",
  "UnstructuredTableColumn",
  "UnstructuredTableDef",
  "UnstructuredTemplateDefinition",
];
for (const name of requiredTypes) {
  const re = new RegExp(`export\\s+type\\s+${name}\\b`);
  if (!re.test(helperSrc)) fail(`required type missing: ${name}`);
  else ok(`type present: ${name}`);
}

// ---------------------------------------------------------------------------
// 14. documentType support — present in types and normalize/serialize paths
// ---------------------------------------------------------------------------
if (!/documentType\?:\s*string/.test(helperSrc))
  fail(`documentType?: string declaration missing`);
else ok(`documentType?: string declared`);
if (!/safeOptionalString\(j\.documentType\)/.test(helperSrc) && !/documentType\s*=/.test(helperSrc))
  fail(`documentType not handled in normalize`);
else ok(`documentType handled in normalize/serialize`);

// ---------------------------------------------------------------------------
// 15-19. Runtime smoke — dynamically import the .ts helper (Node 22+ strip-types)
// ---------------------------------------------------------------------------
const helperUrl = pathToFileURL(HELPER_PATH).href;
let mod = null;
try {
  mod = await import(helperUrl);
  ok(`runtime import succeeded (node strip-types)`);
} catch (err) {
  fail(`runtime import failed: ${err?.message ?? String(err)}`);
}

function assertEq(actual, expected, label) {
  const a = JSON.stringify(actual);
  const b = JSON.stringify(expected);
  if (a !== b) {
    fail(`smoke: ${label} expected ${b} but got ${a}`);
    return false;
  }
  ok(`smoke: ${label}`);
  return true;
}
function expect(cond, label) {
  if (!cond) fail(`smoke: ${label}`);
  else ok(`smoke: ${label}`);
}

if (mod) {
  const {
    normalizeUnstructuredTemplate,
    serializeUnstructuredTemplate,
    createDefaultInfoField,
    createDefaultTableDef,
    createDefaultTableColumn,
  } = mod;

  // --- case 1: legacy fields-only input ---
  const legacy = {
    mode: "unstructured",
    fields: [
      { no: 1, enField: "storeName", koField: "상호" },
      { no: 2, enField: "bizNo", koField: "사업자번호" },
    ],
    regions: [],
  };
  const legacySnapshot = JSON.parse(JSON.stringify(legacy));
  const r1 = normalizeUnstructuredTemplate(legacy);
  expect(r1.mode === "unstructured", "case 1 mode preserved");
  expect(r1.documentType === undefined, "case 1 no documentType invented");
  expect(Array.isArray(r1.info) && r1.info.length === 2, "case 1 info length 2");
  expect(r1.info[0].key === "storeName" && r1.info[0].labelKo === "상호", "case 1 info[0]");
  expect(r1.info[0].labelEn === "storeName", "case 1 info[0].labelEn");
  expect(r1.info[1].key === "bizNo" && r1.info[1].labelKo === "사업자번호", "case 1 info[1]");
  expect(Array.isArray(r1.tables) && r1.tables.length === 0, "case 1 tables []");
  expect(Array.isArray(r1.fields) && r1.fields.length === 2, "case 1 fields mirror length 2");
  expect(r1.fields[0].enField === "storeName" && r1.fields[0].koField === "상호", "case 1 fields[0]");
  expect(Array.isArray(r1.regions) && r1.regions.length === 0, "case 1 regions []");
  assertEq(legacy, legacySnapshot, "case 1 input not mutated");

  // --- case 2: legacy fields-only WITHOUT documentType (already covered by case 1, explicit) ---
  const legacyNoDoc = { mode: "unstructured", fields: [{ no: 1, enField: "a", koField: "가" }] };
  const r2 = normalizeUnstructuredTemplate(legacyNoDoc);
  expect(r2.documentType === undefined, "case 2 documentType undefined (no auto-fill)");
  expect(!("documentType" in r2), "case 2 documentType key omitted");

  // --- case 3: info/tables WITH documentType ---
  const newPayload = {
    mode: "unstructured",
    documentType: "invoice_statement",
    info: [{ key: "supplierName", labelKo: "공급자 상호", labelEn: "supplierName" }],
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
  const snapshot3 = JSON.parse(JSON.stringify(newPayload));
  const r3 = normalizeUnstructuredTemplate(newPayload);
  expect(r3.documentType === "invoice_statement", "case 3 documentType preserved");
  expect(r3.info.length === 1 && r3.info[0].key === "supplierName", "case 3 info preserved");
  expect(r3.tables.length === 1 && r3.tables[0].tableKey === "items", "case 3 table preserved");
  expect(r3.tables[0].columns.length === 2, "case 3 table.columns length 2");
  expect(
    r3.tables[0].columns[0].columnKey === "itemName"
      && r3.tables[0].columns[1].columnKey === "quantity",
    "case 3 column keys preserved",
  );
  expect(r3.fields.length === 1 && r3.fields[0].koField === "공급자 상호", "case 3 fields mirror from info");
  assertEq(newPayload, snapshot3, "case 3 input not mutated");

  // --- case 4: info/tables WITHOUT documentType ---
  const r4 = normalizeUnstructuredTemplate({
    mode: "unstructured",
    info: [{ key: "x", labelKo: "엑스" }],
    tables: [],
  });
  expect(r4.documentType === undefined, "case 4 documentType undefined");
  expect(!("documentType" in r4), "case 4 documentType key omitted");

  // --- case 5: empty input ---
  const r5 = normalizeUnstructuredTemplate({});
  expect(r5.mode === "unstructured", "case 5 mode");
  expect(r5.info.length === 0 && r5.tables.length === 0 && r5.fields.length === 0, "case 5 empties");
  expect(r5.documentType === undefined, "case 5 documentType undefined");

  // --- case 6: malformed input ---
  for (const bad of [null, undefined, 0, "x", [], { mode: 42 }]) {
    const r = normalizeUnstructuredTemplate(bad);
    expect(r.mode === "unstructured", `case 6 malformed (${typeof bad}) safe mode`);
    expect(Array.isArray(r.info) && Array.isArray(r.tables) && Array.isArray(r.fields),
      `case 6 malformed (${typeof bad}) arrays`);
  }

  // --- case 7: table with columns ordering ---
  const r7 = normalizeUnstructuredTemplate({
    mode: "unstructured",
    tables: [
      {
        tableKey: "t",
        labelKo: "T",
        columns: [
          { columnKey: "b", labelKo: "B", order: 5 },
          { columnKey: "a", labelKo: "A", order: 1 },
        ],
      },
    ],
  });
  expect(r7.tables[0].columns[0].columnKey === "a"
    && r7.tables[0].columns[1].columnKey === "b",
    "case 7 columns sorted by order");
  expect(r7.tables[0].columns[0].order === 1
    && r7.tables[0].columns[1].order === 2,
    "case 7 columns re-numbered 1..N");

  // --- case 8: serialize from editor state → fields mirror generated ---
  const r8 = serializeUnstructuredTemplate({
    templateName: "거래명세서_샘플",
    documentType: "invoice_statement",
    info: [
      { key: "buyer", labelKo: "공급받는자", labelEn: "buyer" },
    ],
    tables: [
      {
        tableKey: "items",
        labelKo: "품목표",
        columns: [{ columnKey: "itemName", labelKo: "품목명" }],
      },
    ],
  });
  expect(r8.templateName === "거래명세서_샘플", "case 8 templateName preserved");
  expect(r8.documentType === "invoice_statement", "case 8 documentType preserved");
  expect(r8.fields.length === 1 && r8.fields[0].enField === "buyer" && r8.fields[0].koField === "공급받는자",
    "case 8 fields mirror generated from info");
  expect(r8.tables.length === 1 && r8.tables[0].columns[0].columnKey === "itemName",
    "case 8 table column preserved");

  // --- case 9: input not mutated (deeper check) ---
  const original = {
    mode: "unstructured",
    documentType: "card_receipt",
    info: [{ key: "a", labelKo: "가", aliases: ["aa"], extra: "xx" }],
    tables: [
      { tableKey: "t", labelKo: "T", columns: [{ columnKey: "c", labelKo: "C" }] },
    ],
    fields: [],
    regions: [],
  };
  const snap = JSON.parse(JSON.stringify(original));
  normalizeUnstructuredTemplate(original);
  serializeUnstructuredTemplate({
    documentType: original.documentType,
    info: original.info,
    tables: original.tables,
  });
  assertEq(original, snap, "case 9 normalize+serialize do not mutate input");

  // --- case 10: documentType is never auto-defaulted ---
  const r10a = normalizeUnstructuredTemplate({ fields: [{ no: 1, enField: "x", koField: "X" }] });
  const r10b = serializeUnstructuredTemplate({ info: [{ key: "x", labelKo: "X" }] });
  expect(r10a.documentType === undefined && !("documentType" in r10a),
    "case 10a normalize: documentType omitted when not provided");
  expect(r10b.documentType === undefined && !("documentType" in r10b),
    "case 10b serialize: documentType omitted when not provided");

  // --- default constructors ---
  const i1 = createDefaultInfoField(1);
  expect(i1.key === "field_1" && i1.order === 1 && i1.no === 1 && i1.visible === true && i1.required === false,
    "createDefaultInfoField(1)");
  const t1 = createDefaultTableDef(1);
  expect(t1.tableKey === "table_1" && Array.isArray(t1.columns) && t1.columns.length === 0
    && t1.order === 1 && t1.required === false && t1.userConfirmed === false,
    "createDefaultTableDef(1)");
  const c1 = createDefaultTableColumn(1);
  expect(c1.columnKey === "column_1" && c1.order === 1 && c1.visible === true
    && c1.required === false && c1.source === "user" && c1.userConfirmed === false,
    "createDefaultTableColumn(1)");
}

// ---------------------------------------------------------------------------
// 20. No new untracked production files beyond the single allowed helper
//     (CRLF noise makes `git diff` unreliable on Windows — we use porcelain
//     to look for new "?? " entries under production directories.)
// ---------------------------------------------------------------------------
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
  const ALLOWED_NEW = new Set([
    "mysuit-ocr/src/components/template/utils/unstructuredDefinition.ts",
    "mysuit-ocr/src/components/runocr/utils/extractUnstructuredTableRows.ts", // TPL-8B (later phase)
    "mysuit-ocr/src/common/utils/tableResultViewModel.ts", // TPL-8D (later phase)
  ]);
  let newProdHits = 0;
  for (const line of porcelain) {
    if (!line.startsWith("?? ")) continue;
    const path = line.slice(3).replace(/^"|"$/g, "");
    if (!FORBID_NEW.some((re) => re.test(path))) continue;
    if (ALLOWED_NEW.has(path)) {
      note(`new production file (allowed by TPL-3): ${path}`);
      continue;
    }
    fail(`new untracked production file detected: ${path}`);
    newProdHits++;
  }
  if (newProdHits === 0)
    ok(`new-file scope check: only allowed helper added`);
}

// ---------------------------------------------------------------------------
// Final
// ---------------------------------------------------------------------------
if (failures.length === 0) {
  console.log(`${TAG} PASS`);
  process.exit(0);
} else {
  console.error(`${TAG} FAIL count=${failures.length}`);
  for (const m of failures) console.error(`${TAG}   - ${m}`);
  process.exit(1);
}
