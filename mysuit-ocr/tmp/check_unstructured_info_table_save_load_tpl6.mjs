#!/usr/bin/env node
// TPL-6-UNSTRUCTURED-INFO-TABLE-SAVE-LOAD
// Read-only fixture round-trip verification. No production code is modified.
// Tag on success: [UNSTRUCTURED_INFO_TABLE_SAVE_LOAD_TPL6] PASS

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
const TAG = "[UNSTRUCTURED_INFO_TABLE_SAVE_LOAD_TPL6]";

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
function expect(cond, label) { if (!cond) fail(`smoke: ${label}`); else ok(`smoke: ${label}`); }
function eqJSON(a, b) { return JSON.stringify(a) === JSON.stringify(b); }

// ---------------------------------------------------------------------------
// Paths
// ---------------------------------------------------------------------------
const HELPER_PATH = resolve(ROOT, "src/components/template/utils/unstructuredDefinition.ts");
const BUILDER_PATH = resolve(ROOT, "src/components/template/UnstructuredBuilder.tsx");
const FIXTURE_DIR = resolve(ROOT, "tmp/fixtures/unstructured");

// ---------------------------------------------------------------------------
// 1. Fixture directory + ≥5 fixtures
// ---------------------------------------------------------------------------
if (!existsSync(FIXTURE_DIR)) fail(`fixture dir missing: ${relative(ROOT, FIXTURE_DIR)}`);
else ok(`fixture dir present`);

let fixturePaths = [];
try {
  fixturePaths = readdirSync(FIXTURE_DIR)
    .filter((n) => n.endsWith(".json"))
    .sort()
    .map((n) => resolve(FIXTURE_DIR, n));
} catch {}
if (fixturePaths.length < 5)
  fail(`expected ≥5 fixtures, found ${fixturePaths.length}`);
else ok(`fixtures found: ${fixturePaths.length}`);
for (const p of fixturePaths) note(`  - ${relative(ROOT, p)}`);

// ---------------------------------------------------------------------------
// 2. Helper exists + UnstructuredBuilder exists (untouched-existence check)
// ---------------------------------------------------------------------------
if (!existsSync(HELPER_PATH)) fail(`helper missing`);
else ok(`helper present`);
if (!existsSync(BUILDER_PATH)) fail(`UnstructuredBuilder missing`);
else ok(`UnstructuredBuilder present`);

// ---------------------------------------------------------------------------
// 3. Parse fixtures
// ---------------------------------------------------------------------------
const fixtures = [];
for (const p of fixturePaths) {
  const raw = readSafe(p) ?? "";
  let parsed = null;
  try {
    parsed = JSON.parse(raw);
    ok(`fixture parse OK: ${relative(ROOT, p)}`);
  } catch (err) {
    fail(`fixture parse FAIL: ${relative(ROOT, p)} — ${err?.message ?? err}`);
    continue;
  }
  fixtures.push({ path: p, name: parsed?._meta?.fixtureName ?? relative(ROOT, p), parsed });
}

// ---------------------------------------------------------------------------
// 4. Import helper via Node strip-types
// ---------------------------------------------------------------------------
let mod = null;
try {
  mod = await import(pathToFileURL(HELPER_PATH).href);
  ok(`helper runtime import OK (node strip-types)`);
} catch (err) {
  fail(`helper runtime import FAILED: ${err?.message ?? err}`);
}

if (!mod) {
  console.error(`${TAG} FAIL aborting smoke — helper unimportable`);
  console.error(`${TAG} FAIL count=${failures.length}`);
  process.exit(1);
}

const { normalizeUnstructuredTemplate, serializeUnstructuredTemplate } = mod;

// ---------------------------------------------------------------------------
// 5. UnstructuredBuilder load / save simulation (verbatim from TPL-5 builder)
// ---------------------------------------------------------------------------
function builderLoad(saved) {
  const n = normalizeUnstructuredTemplate(saved);
  return {
    templateName: n.templateName ?? "",
    documentType: n.documentType ?? "",
    fields: n.fields.map(({ no, enField, koField }) => ({ no, enField, koField })),
    tables: n.tables,
  };
}
function builderSerialize(state) {
  const { templateName, documentType, fields, tables } = state;
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
}

// ---------------------------------------------------------------------------
// 6. Per-fixture invariants
// ---------------------------------------------------------------------------
for (const fx of fixtures) {
  const label = `[${fx.name}]`;
  const tj = fx.parsed?.template_json ?? {};
  // capture original for mutation check
  const snap = JSON.parse(JSON.stringify(tj));

  // --- normalize → serialize → normalize equivalence ---
  const n1 = normalizeUnstructuredTemplate(tj);
  const s1 = serializeUnstructuredTemplate({
    templateName: n1.templateName,
    documentType: n1.documentType,
    info: n1.info,
    tables: n1.tables,
  });
  const n2 = normalizeUnstructuredTemplate(s1);
  expect(eqJSON(n1, n2), `${label} normalize→serialize→normalize idempotent`);

  // --- shape invariants on the canonical form (n1) ---
  expect(n1.mode === "unstructured", `${label} mode === "unstructured"`);
  expect(Array.isArray(n1.info), `${label} info is array`);
  expect(Array.isArray(n1.tables), `${label} tables is array`);
  expect(Array.isArray(n1.fields), `${label} fields mirror is array`);
  expect(Array.isArray(n1.regions) && n1.regions.length === 0, `${label} regions === []`);
  // fields mirror count must equal info count
  expect(n1.fields.length === n1.info.length,
    `${label} fields mirror length === info length`);
  // every fields entry has no/enField/koField shape
  for (const f of n1.fields) {
    if (typeof f?.no !== "number" || typeof f?.enField !== "string" || typeof f?.koField !== "string") {
      fail(`${label} fields entry not {no, enField, koField}`);
    }
  }

  // --- documentType policy ---
  const hadDocType = typeof tj.documentType === "string" && tj.documentType.trim().length > 0;
  if (hadDocType) {
    expect(n1.documentType === String(tj.documentType).trim(),
      `${label} documentType preserved`);
    expect("documentType" in s1, `${label} serialized payload retains documentType key`);
  } else {
    expect(n1.documentType === undefined,
      `${label} documentType not auto-filled when input lacks it`);
    expect(!("documentType" in s1),
      `${label} serialized payload omits documentType key when input lacks it`);
  }

  // --- tables preservation ---
  // The TPL-3 helper's contract is "safe coerce, never throw" — it maps every
  // input entry through normalizeTable/Column with default fallbacks rather
  // than filtering. So normalized counts equal input array length verbatim
  // for well-formed fixtures, and the malformed fixture exercises the
  // "garbage in → default out" path explicitly via the targeted assertions
  // further below.
  if (Array.isArray(tj.tables)) {
    expect(n1.tables.length === tj.tables.length,
      `${label} tables count preserved (helper maps 1:1)`);
    for (let i = 0; i < n1.tables.length; i++) {
      const rawCols = (tj.tables[i] && typeof tj.tables[i] === "object" && !Array.isArray(tj.tables[i]))
        ? (Array.isArray(tj.tables[i].columns) ? tj.tables[i].columns : [])
        : [];
      expect(n1.tables[i].columns.length === rawCols.length,
        `${label} table[${i}] columns count preserved (helper maps 1:1)`);
    }
  }

  // --- info preservation (count) ---
  // Helper maps every entry; counts equal input array length verbatim.
  if (Array.isArray(tj.info)) {
    expect(n1.info.length === tj.info.length,
      `${label} info count preserved (helper maps 1:1)`);
  } else if (Array.isArray(tj.fields)) {
    expect(n1.info.length === tj.fields.length,
      `${label} info derived from fields, count matches`);
  }

  // --- input mutation guard ---
  expect(eqJSON(tj, snap), `${label} normalize/serialize do not mutate fixture`);

  // --- builderLoad → builderSerialize simulation ---
  const loaded = builderLoad(tj);
  const saved = builderSerialize({
    templateName: loaded.templateName,
    documentType: loaded.documentType,
    fields: loaded.fields,
    tables: loaded.tables,
  });
  expect(saved.mode === "unstructured", `${label} builder save → mode`);
  expect(Array.isArray(saved.fields), `${label} builder save → fields mirror present`);
  expect(saved.fields.length === n1.info.length,
    `${label} builder save → fields mirror length matches info`);
  expect(Array.isArray(saved.tables) && saved.tables.length === n1.tables.length,
    `${label} builder save → tables length preserved`);
  expect(Array.isArray(saved.regions) && saved.regions.length === 0,
    `${label} builder save → regions []`);
  if (hadDocType) {
    expect(saved.documentType === n1.documentType,
      `${label} builder save → documentType preserved`);
  } else {
    expect(!("documentType" in saved),
      `${label} builder save → documentType omitted (no auto-fill)`);
  }

  // load → save → load idempotent at builder level
  const loaded2 = builderLoad(saved);
  expect(eqJSON(loaded, loaded2),
    `${label} builder load → save → load idempotent`);

  // Per-column ordering survives (when fixture provides explicit columns)
  for (let ti = 0; ti < n1.tables.length; ti++) {
    const cols = n1.tables[ti].columns ?? [];
    for (let ci = 0; ci < cols.length; ci++) {
      if (cols[ci].order !== ci + 1) {
        fail(`${label} table[${ti}].columns[${ci}].order should be ${ci + 1}, got ${cols[ci].order}`);
        break;
      }
    }
  }
  ok(`${label} per-column order sequential`);
}

// ---------------------------------------------------------------------------
// 7. Targeted contract checks
//    - legacy_fields_only must round-trip with no documentType
//    - tables_only_invoice_statement must keep 5 columns
//    - info_tables_invoice_statement must keep both tables + 6+2 columns
// ---------------------------------------------------------------------------
function findFixture(name) {
  return fixtures.find((f) => f.name === name || f.path.endsWith(`${name}.json`));
}
const fxLegacy = findFixture("legacy_fields_only");
if (fxLegacy) {
  const n = normalizeUnstructuredTemplate(fxLegacy.parsed.template_json);
  expect(n.documentType === undefined, `legacy: no documentType auto-fill`);
  expect(n.tables.length === 0, `legacy: tables empty`);
  expect(n.info.length === 6 && n.fields.length === 6,
    `legacy: 6 info + 6 fields mirror entries`);
  expect(n.fields[0].enField === "storeName" && n.fields[0].koField === "상호",
    `legacy: fields[0] preserves storeName/상호`);
}
const fxInvTables = findFixture("tables_only_invoice_statement");
if (fxInvTables) {
  const n = normalizeUnstructuredTemplate(fxInvTables.parsed.template_json);
  expect(n.documentType === "invoice_statement", `invoice-tables-only: documentType`);
  expect(n.tables.length === 1, `invoice-tables-only: 1 table`);
  expect(n.tables[0].columns.length === 5, `invoice-tables-only: 5 columns`);
  const colKeys = n.tables[0].columns.map((c) => c.columnKey);
  expect(eqJSON(colKeys, ["itemName", "spec", "quantity", "unitPrice", "amount"]),
    `invoice-tables-only: column order itemName/spec/quantity/unitPrice/amount`);
}
const fxFull = findFixture("info_tables_invoice_statement");
if (fxFull) {
  const n = normalizeUnstructuredTemplate(fxFull.parsed.template_json);
  expect(n.documentType === "invoice_statement", `invoice-full: documentType`);
  expect(n.info.length === 7, `invoice-full: 7 info entries`);
  expect(n.tables.length === 2, `invoice-full: 2 tables`);
  expect(n.tables[0].tableKey === "items" && n.tables[0].columns.length === 6,
    `invoice-full: items table has 6 columns`);
  expect(n.tables[1].tableKey === "summary" && n.tables[1].columns.length === 2,
    `invoice-full: summary table has 2 columns`);
  // round-trip: save then reload preserves both tables intact
  const loaded = builderLoad(fxFull.parsed.template_json);
  const saved = builderSerialize(loaded);
  expect(saved.tables.length === 2
    && saved.tables[0].columns.length === 6
    && saved.tables[1].columns.length === 2,
    `invoice-full: round-trip preserves tables + columns`);
}
const fxEmpty = findFixture("empty_payload");
if (fxEmpty) {
  const n = normalizeUnstructuredTemplate(fxEmpty.parsed.template_json);
  expect(n.info.length === 0 && n.tables.length === 0 && n.fields.length === 0,
    `empty: all collections empty`);
  expect(n.documentType === undefined, `empty: no documentType`);
  expect(!("documentType" in n), `empty: documentType key omitted`);
}
const fxMalformed = findFixture("malformed_minimal");
if (fxMalformed) {
  const n = normalizeUnstructuredTemplate(fxMalformed.parsed.template_json);
  expect(n.mode === "unstructured", `malformed: still mode=unstructured`);
  // documentType: 42 (number) must NOT survive as string
  expect(n.documentType === undefined, `malformed: numeric documentType rejected`);
  // info: 3 input entries — helper maps each through safe-coerce with default
  // fallbacks (string "not-an-object" yields a default-key entry rather than
  // throwing). Contract: every entry survives but garbage becomes a default.
  expect(n.info.length === 3, `malformed: info safe-coerces all 3 entries`);
  // tables: 3 input entries — string entry becomes a default-shaped table
  // with empty columns, others are normalized.
  expect(n.tables.length === 3, `malformed: tables safe-coerces all 3 entries`);
  // table[0].columns: 3 input entries — null becomes default column, the
  // bad-columnKey object also gets a synthesized key.
  expect(n.tables[0].columns.length === 3, `malformed: columns safe-coerces all 3 entries`);
  // The default-shaped table from the string entry has empty columns.
  expect(Array.isArray(n.tables[1].columns) && n.tables[1].columns.length === 0,
    `malformed: string-entry table has empty columns`);
  // Every column has a valid columnKey string (no throws / undefined).
  for (const c of n.tables[0].columns) {
    if (typeof c.columnKey !== "string" || c.columnKey.length === 0) {
      fail(`malformed: column missing valid columnKey`);
      break;
    }
  }
  ok(`malformed: every column has a valid columnKey`);
}

// ---------------------------------------------------------------------------
// 8. Untouched production files (sanity)
// ---------------------------------------------------------------------------
const builderSnapshot = readSafe(BUILDER_PATH) ?? "";
if (!builderSnapshot.includes("normalizeUnstructuredTemplate"))
  fail(`UnstructuredBuilder lost normalizeUnstructuredTemplate import`);
else ok(`UnstructuredBuilder still imports normalize helper`);
if (!builderSnapshot.includes("serializeUnstructuredTemplate"))
  fail(`UnstructuredBuilder lost serializeUnstructuredTemplate import`);
else ok(`UnstructuredBuilder still imports serialize helper`);
if (!/LOCAL_TEMPLATES_KEY\s*=\s*"mysuit_ocr_templates"/.test(builderSnapshot))
  fail(`LOCAL_TEMPLATES_KEY changed`);
else ok(`localStorage key "mysuit_ocr_templates" unchanged`);

const helperSrc = readSafe(HELPER_PATH) ?? "";
for (const sym of [
  "export function normalizeUnstructuredTemplate",
  "export function serializeUnstructuredTemplate",
  "export function createDefaultInfoField",
  "export function createDefaultTableDef",
  "export function createDefaultTableColumn",
]) {
  if (!helperSrc.includes(sym)) fail(`helper missing: ${sym}`);
  else ok(`helper export retained: ${sym}`);
}

// ---------------------------------------------------------------------------
// 9. src/lib absent + @/lib imports = 0
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
// 10. New-file scope: tmp/fixtures/unstructured/* + tmp/check_*.mjs are
//     acceptable; no new production additions beyond the TPL-3 helper.
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
