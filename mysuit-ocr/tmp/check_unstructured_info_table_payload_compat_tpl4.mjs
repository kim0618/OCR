#!/usr/bin/env node
// TPL-4-UNSTRUCTURED-INFO-TABLE-PAYLOAD-COMPAT
// Static + runtime smoke. Only UnstructuredBuilder.tsx is allowed to change
// (helper wiring); UI / RunOCR / TestWorkspace / backend / fixtures untouched.
// Tag on success: [UNSTRUCTURED_INFO_TABLE_PAYLOAD_COMPAT_TPL4] PASS

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
const TAG = "[UNSTRUCTURED_INFO_TABLE_PAYLOAD_COMPAT_TPL4]";

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

// ---------------------------------------------------------------------------
// 1. Helper exists
// ---------------------------------------------------------------------------
if (!existsSync(HELPER_PATH)) fail(`helper missing: ${relative(ROOT, HELPER_PATH)}`);
else ok(`present: src/components/template/utils/unstructuredDefinition.ts`);

// ---------------------------------------------------------------------------
// 2-3. UnstructuredBuilder imports normalize/serialize helpers
// ---------------------------------------------------------------------------
const builderSrc = readSafe(BUILDER_PATH) ?? "";
if (!builderSrc) fail(`UnstructuredBuilder.tsx missing or unreadable`);
const builderStripped = stripComments(builderSrc);
const reImportHelper = /from\s+["']\.\/utils\/unstructuredDefinition["']/;
if (!reImportHelper.test(builderStripped))
  fail(`UnstructuredBuilder does not import from ./utils/unstructuredDefinition`);
else ok(`UnstructuredBuilder imports ./utils/unstructuredDefinition`);
if (!/\bnormalizeUnstructuredTemplate\s*\(/.test(builderStripped))
  fail(`UnstructuredBuilder does not call normalizeUnstructuredTemplate(...)`);
else ok(`UnstructuredBuilder calls normalizeUnstructuredTemplate(...)`);
if (!/\bserializeUnstructuredTemplate\s*\(/.test(builderStripped))
  fail(`UnstructuredBuilder does not call serializeUnstructuredTemplate(...)`);
else ok(`UnstructuredBuilder calls serializeUnstructuredTemplate(...)`);

// ---------------------------------------------------------------------------
// 4-5. UI markers — TPL-4 phase invariant.
//   At pure TPL-4 (no TPL-5 UI yet) these markers MUST be absent.
//   At TPL-5+ the same markers are intentionally shipped, so this guard
//   becomes vestigial; we detect TPL-5 by the documentType useState + tables
//   useState in the builder, then NOTE-and-skip the forbidden-UI assertions.
// ---------------------------------------------------------------------------
const TPL5_MARKERS_PRESENT =
  /\bsetDocumentType\b/.test(builderStripped) &&
  /useState\s*<\s*UnstructuredTableDef\[\]\s*>/.test(builderStripped);
const forbiddenUiPatterns = [
  { name: "문서유형 (label or select option)", re: /문서\s*유형/ },
  { name: "documentType select element", re: /<select[\s\S]{0,80}documentType/ },
  { name: "+ 영역 정의 button", re: /영역\s*정의/ },
  { name: "+ 테이블 정의 button", re: /테이블\s*정의/ },
];
if (TPL5_MARKERS_PRESENT) {
  note(`TPL-5 has shipped — skipping TPL-4's forbidden-UI assertions (documentType state + tables state detected)`);
} else {
  for (const { name, re } of forbiddenUiPatterns) {
    if (re.test(builderStripped))
      fail(`forbidden UI marker present in UnstructuredBuilder: ${name}`);
  }
  ok(`no forbidden UI markers (문서유형 / 영역 정의 / 테이블 정의)`);
}

// fields UI state still present
if (!/useState<Field\[\]>/.test(builderStripped))
  fail(`fields useState<Field[]> removed`);
else ok(`fields useState<Field[]> retained`);
// addField / 추가 button still present
if (!/onClick=\{addField\}/.test(builderStripped))
  fail(`addField onClick wiring missing — add/delete UI must remain`);
else ok(`addField wiring retained`);

// localStorage key not renamed
if (!/LOCAL_TEMPLATES_KEY\s*=\s*"mysuit_ocr_templates"/.test(builderStripped))
  fail(`localStorage key changed from "mysuit_ocr_templates"`);
else ok(`localStorage key "mysuit_ocr_templates" retained`);

// ---------------------------------------------------------------------------
// 6-9. Untouched files
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

// RunOCR mapper must not have been changed to read info/tables yet (TPL-7).
const mapperSrc = readSafe(RUNOCR_MAPPER) ?? "";
const mapperStripped = stripComments(mapperSrc);
if (/\binfo\s*[?:]\s*UnstructuredInfo/.test(mapperStripped))
  fail(`mapOcrResponse references UnstructuredInfo (TPL-7 work — not allowed yet)`);
else ok(`mapOcrResponse has no info/tables wiring (TPL-7 still pending)`);

// ---------------------------------------------------------------------------
// 10. src/lib absent
// ---------------------------------------------------------------------------
const SRC_LIB = resolve(ROOT, "src/lib");
if (existsSync(SRC_LIB)) {
  const files = walk(SRC_LIB);
  if (files.length > 0) fail(`src/lib must be absent or empty, found ${files.length} files`);
  else ok(`src/lib present but empty`);
} else ok(`src/lib absent`);

// ---------------------------------------------------------------------------
// 11. @/lib + relative lib imports = 0
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
// 12-18. Runtime smoke via Node 22+ TS strip-types
//        Round-trip the helper directly (the same helper UnstructuredBuilder
//        calls), covering all backward-compat / forward-shape contracts.
// ---------------------------------------------------------------------------
let mod = null;
try {
  mod = await import(pathToFileURL(HELPER_PATH).href);
  ok(`runtime import succeeded (node strip-types)`);
} catch (err) {
  fail(`runtime import failed: ${err?.message ?? String(err)}`);
}

function expect(cond, label) {
  if (!cond) fail(`smoke: ${label}`);
  else ok(`smoke: ${label}`);
}
function eqJSON(a, b) { return JSON.stringify(a) === JSON.stringify(b); }

if (mod) {
  const { normalizeUnstructuredTemplate, serializeUnstructuredTemplate } = mod;

  // helper to emulate what UnstructuredBuilder does on save:
  const builderSerialize = (templateName, fields, passThrough) => {
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
    return serializeUnstructuredTemplate({
      templateName,
      documentType: passThrough?.documentType,
      info,
      tables: passThrough?.tables ?? [],
    });
  };
  // helper to emulate what UnstructuredBuilder does on load:
  const builderLoad = (saved) => {
    const n = normalizeUnstructuredTemplate(saved);
    return {
      templateName: n.templateName ?? "",
      fields: n.fields.map(({ no, enField, koField }) => ({ no, enField, koField })),
      passThrough: { documentType: n.documentType, tables: n.tables },
    };
  };

  // --- case 1: legacy fields-only input load ---
  const legacy = {
    mode: "unstructured",
    templateName: "영수증_샘플",
    fields: [
      { no: 1, enField: "storeName", koField: "상호" },
      { no: 2, enField: "bizNo", koField: "사업자번호" },
    ],
    regions: [],
  };
  const legacySnap = JSON.parse(JSON.stringify(legacy));
  const loaded1 = builderLoad(legacy);
  expect(loaded1.templateName === "영수증_샘플", "case 1 templateName preserved");
  expect(loaded1.fields.length === 2, "case 1 fields length 2");
  expect(loaded1.fields[0].enField === "storeName" && loaded1.fields[0].koField === "상호",
    "case 1 fields[0] shape");
  expect(loaded1.passThrough.documentType === undefined, "case 1 no documentType invented");
  expect(loaded1.passThrough.tables.length === 0, "case 1 tables empty");
  expect(eqJSON(legacy, legacySnap), "case 1 load did not mutate input");

  // --- case 2: legacy fields-only save round-trip + fields mirror identity ---
  const saved2 = builderSerialize(loaded1.templateName, loaded1.fields, loaded1.passThrough);
  expect(saved2.mode === "unstructured", "case 2 saved mode");
  expect(Array.isArray(saved2.regions) && saved2.regions.length === 0, "case 2 regions: []");
  expect(saved2.fields.length === 2, "case 2 fields mirror length");
  expect(saved2.fields[0].enField === "storeName" && saved2.fields[0].koField === "상호",
    "case 2 fields[0] mirror identity");
  expect(saved2.fields[1].enField === "bizNo" && saved2.fields[1].koField === "사업자번호",
    "case 2 fields[1] mirror identity");
  expect(saved2.info.length === 2 && saved2.info[0].key === "storeName" && saved2.info[0].labelKo === "상호",
    "case 2 info derived from fields");
  expect(!("documentType" in saved2),
    "case 2 documentType key omitted (no auto-fill)");

  // --- case 3: info/tables with documentType — passThrough preserves tables ---
  const newPayload = {
    mode: "unstructured",
    templateName: "거래명세서_샘플",
    documentType: "invoice_statement",
    info: [
      { key: "supplierName", labelKo: "공급자 상호", labelEn: "supplierName" },
    ],
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
  const newSnap = JSON.parse(JSON.stringify(newPayload));
  const loaded3 = builderLoad(newPayload);
  expect(loaded3.passThrough.documentType === "invoice_statement",
    "case 3 documentType captured into passThrough");
  expect(loaded3.passThrough.tables.length === 1,
    "case 3 tables captured into passThrough");
  expect(loaded3.passThrough.tables[0].columns.length === 2,
    "case 3 table columns captured");
  expect(loaded3.fields.length === 1 && loaded3.fields[0].koField === "공급자 상호",
    "case 3 fields mirror derived from info for UI");
  expect(eqJSON(newPayload, newSnap), "case 3 load did not mutate input");

  // --- case 4: save round-trip preserves documentType + tables passThrough ---
  const saved4 = builderSerialize(loaded3.templateName, loaded3.fields, loaded3.passThrough);
  expect(saved4.documentType === "invoice_statement",
    "case 4 saved documentType preserved");
  expect(saved4.tables.length === 1 && saved4.tables[0].tableKey === "items",
    "case 4 saved tables preserved");
  expect(saved4.tables[0].columns.length === 2
    && saved4.tables[0].columns[0].columnKey === "itemName"
    && saved4.tables[0].columns[1].columnKey === "quantity",
    "case 4 saved table columns preserved");
  expect(saved4.fields.length === 1 && saved4.fields[0].koField === "공급자 상호",
    "case 4 fields mirror still present for RunOCR compat");
  expect(Array.isArray(saved4.regions) && saved4.regions.length === 0,
    "case 4 regions: [] preserved");

  // --- case 5: documentType absent — never auto-defaulted at any layer ---
  const saved5 = builderSerialize("untyped", [{ no: 1, enField: "x", koField: "X" }], { tables: [] });
  expect(!("documentType" in saved5), "case 5 documentType key omitted in serialize output");

  // --- case 6: tables in input but UI never touches them — they survive save ---
  const withTables = {
    mode: "unstructured",
    templateName: "with_tables",
    documentType: "invoice_statement",
    info: [{ key: "a", labelKo: "A" }],
    tables: [{ tableKey: "t1", labelKo: "T1", columns: [{ columnKey: "c1", labelKo: "C1" }] }],
    fields: [],
    regions: [],
  };
  const loaded6 = builderLoad(withTables);
  // simulate user editing the visible field (changing koField)
  const userEditedFields = loaded6.fields.map((f) => ({ ...f, koField: f.koField + "_edit" }));
  const saved6 = builderSerialize(loaded6.templateName, userEditedFields, loaded6.passThrough);
  expect(saved6.tables.length === 1 && saved6.tables[0].columns[0].columnKey === "c1",
    "case 6 tables survive even when user edits only info fields");
  expect(saved6.documentType === "invoice_statement",
    "case 6 documentType survives user edits");
  expect(saved6.info[0].labelKo === "A_edit", "case 6 user info edit applied");

  // --- case 7: input mutation guard for both helpers ---
  const orig = {
    mode: "unstructured",
    documentType: "card_receipt",
    info: [{ key: "a", labelKo: "가" }],
    tables: [{ tableKey: "t", labelKo: "T", columns: [{ columnKey: "c", labelKo: "C" }] }],
    fields: [],
    regions: [],
  };
  const snap = JSON.parse(JSON.stringify(orig));
  builderLoad(orig);
  builderSerialize("x", [{ no: 1, enField: "a", koField: "가" }],
    { documentType: orig.documentType, tables: orig.tables });
  expect(eqJSON(orig, snap), "case 7 helpers do not mutate input");
}

// ---------------------------------------------------------------------------
// 19. localStorage key unchanged (already checked above; explicit reaffirm)
// ---------------------------------------------------------------------------
if (/"mysuit_ocr_templates"/.test(builderSrc)) ok(`localStorage key "mysuit_ocr_templates" in source`);
else fail(`localStorage key "mysuit_ocr_templates" missing from UnstructuredBuilder`);

// ---------------------------------------------------------------------------
// 20. New-file scope: only the helper is allowed as new production file.
//     UnstructuredBuilder is `M` (modified), not `??`, so it doesn't count
//     as a new-file violation here.
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
    "mysuit-ocr/src/components/template/utils/unstructuredDefinition.ts",
    "mysuit-ocr/src/components/runocr/utils/extractUnstructuredTableRows.ts", // TPL-8B (later phase)
    "mysuit-ocr/src/common/utils/tableResultViewModel.ts", // TPL-8D (later phase)
  ]);
  let newProdHits = 0;
  for (const line of porcelain) {
    if (!line.startsWith("?? ")) continue;
    const path = line.slice(3).replace(/^"|"$/g, "");
    if (!FORBID_NEW.some((re) => re.test(path))) continue;
    if (PHASE_ALLOW.has(path)) {
      note(`new production file (allowed by TPL-3 helper): ${path}`);
      continue;
    }
    fail(`new untracked production file detected: ${path}`);
    newProdHits++;
  }
  if (newProdHits === 0)
    ok(`new-file scope check: no unauthorised production additions`);
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
