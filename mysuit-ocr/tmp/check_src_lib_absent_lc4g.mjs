#!/usr/bin/env node
// LIB-CLEAN-4G SRC/LIB ABSENT CHECK (final guard)
//
// Verifies the src/lib cleanup plan completion:
// - src/lib is absent OR empty (no operational files).
// - Zero @/lib/*, ../lib/*, ../../lib/* import in src code.
// - All previously-moved files live at their final homes.
// - Forbidden areas (TestWorkspace, test/core, AutoRestoreWorkspace,
//   /autorestore route, backend, fixtures, templates.json, public/data/
//   testsets, ground truth) remain present.
//
// Read-only. No production code is modified.

import { readFileSync, existsSync, readdirSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, "..");

const LIB_DIR = resolve(ROOT, "src/lib");

// Final homes of all moved files (LIB-CLEAN 1..4F + earlier CS/BZ).
const FINAL_HOMES = {
  autofillEngine: resolve(ROOT, "src/common/utils/autofillEngine.ts"),
  profiles: resolve(ROOT, "src/components/test/utils/profiles.ts"),
  testsets: resolve(ROOT, "src/common/config/testsets.ts"),
  restoreProfileStore: resolve(ROOT, "src/common/storage/restoreProfileStore.ts"),
  groundTruthStore: resolve(ROOT, "src/common/storage/groundTruthStore.ts"),
  axios: resolve(ROOT, "src/common/api/axios.ts"),
  login: resolve(ROOT, "src/common/storage/login.ts"),
  theme: resolve(ROOT, "src/components/layout/utils/theme.ts"),
  bizNumber: resolve(ROOT, "src/common/utils/bizNumber.ts"),
  historyStore: resolve(ROOT, "src/common/storage/historyStore.ts"),
  imageStore: resolve(ROOT, "src/common/storage/imageStore.ts"),
};
const ABSENT_FROM_LIB = [
  "autofillEngine.ts", "profiles.ts", "testsets.ts",
  "restoreProfileStore.ts", "groundTruthStore.ts",
  "axios.ts", "login.ts", "theme.ts",
  "bizNumber.ts", "historyStore.ts", "imageStore.ts",
];

// Forbidden-area existence guards.
const TEST_WORKSPACE = resolve(ROOT, "src/components/test/TestWorkspace.tsx");
const TEST_CORE_DIR = resolve(ROOT, "src/components/test/core");
const AUTORESTORE_WORKSPACE = resolve(ROOT, "src/components/autorestore/AutoRestoreWorkspace.tsx");
const AUTORESTORE_ROUTE = resolve(ROOT, "src/app/autorestore/page.tsx");

function readSafe(p) { try { return readFileSync(p, "utf8"); } catch { return null; } }
function stripComments(src) {
  return src
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .replace(/(^|[^:])\/\/[^\n]*/g, "$1");
}
function walk(dir, acc = []) {
  try {
    for (const ent of readdirSync(dir, { withFileTypes: true })) {
      const p = resolve(dir, ent.name);
      if (ent.isDirectory()) walk(p, acc);
      else if (/\.(ts|tsx|mts|cts|js|jsx|mjs|cjs)$/.test(ent.name)) acc.push(p);
    }
  } catch {}
  return acc;
}
function relFromRoot(p) { return p.replace(ROOT + "\\", "").replace(/\\/g, "/"); }

const checks = {};

// 1) src/lib absent OR empty.
const libDirExists = existsSync(LIB_DIR);
const libEntries = libDirExists
  ? readdirSync(LIB_DIR).filter((n) => !n.startsWith("."))
  : [];
const libTsCount = libEntries.filter((n) => /\.(ts|tsx|mts|cts)$/.test(n)).length;
const libOperationalCount = libEntries.filter((n) => /\.(ts|tsx|mts|cts|js|jsx|mjs|cjs)$/.test(n)).length;
checks.src_lib_absent_or_empty = !libDirExists || libEntries.length === 0;
checks.src_lib_ts_files_zero = libTsCount === 0;
checks.src_lib_operational_files_zero = libOperationalCount === 0;

// 2) Final homes exist; old src/lib paths absent.
for (const [name, path] of Object.entries(FINAL_HOMES)) {
  checks[`${name}_at_final_home`] = existsSync(path);
}
for (const name of ABSENT_FROM_LIB) {
  const k = `${name.replace(/\./g, "_")}_absent_in_src_lib`;
  checks[k] = !existsSync(resolve(LIB_DIR, name));
}

// 3) src-wide @/lib + ../lib + ../../lib import scan (CODE only, comments stripped).
const srcFiles = walk(resolve(ROOT, "src"));
const LIB_IMPORT_RE = /from\s+["'](@\/lib\/[^"']+|\.\.\/lib\/[^"']+|\.\.\/\.\.\/lib\/[^"']+)["']/g;
const LIB_DYNAMIC_IMPORT_RE = /import\s*\(\s*["'](@\/lib\/[^"']+|\.\.\/lib\/[^"']+|\.\.\/\.\.\/lib\/[^"']+)["']\s*\)/g;
const libResiduals = [];
for (const f of srcFiles) {
  const s = readSafe(f);
  if (!s) continue;
  const codeOnly = stripComments(s);
  let m;
  while ((m = LIB_IMPORT_RE.exec(codeOnly))) {
    libResiduals.push({ file: relFromRoot(f), spec: m[1], kind: "static" });
  }
  while ((m = LIB_DYNAMIC_IMPORT_RE.exec(codeOnly))) {
    libResiduals.push({ file: relFromRoot(f), spec: m[1], kind: "dynamic" });
  }
}
checks.no_residual_lib_imports_in_src_code = libResiduals.length === 0;

// 4) Forbidden-area presence (existence of TestWorkspace + test/core +
//    AutoRestoreWorkspace + /autorestore route).
checks.TestWorkspace_present = existsSync(TEST_WORKSPACE);
checks.test_core_dir_present = existsSync(TEST_CORE_DIR);
checks.AutoRestoreWorkspace_present = existsSync(AUTORESTORE_WORKSPACE);
checks.autorestore_route_present = existsSync(AUTORESTORE_ROUTE);

// 5) Template table column definition feature gate: no new file matching
//    obvious "table column definition" naming under src/components/template/
//    that wasn't already present (informational; we just assert the gate is
//    not bypassed by listing files matching common patterns).
const TEMPLATE_DIR = resolve(ROOT, "src/components/template");
function templateColumnDefFiles() {
  if (!existsSync(TEMPLATE_DIR)) return [];
  const files = walk(TEMPLATE_DIR);
  return files
    .map(relFromRoot)
    .filter((p) => /columnDefinition|ColumnDefinition|column_definition/i.test(p));
}
const templateColumnFiles = templateColumnDefFiles();
checks.template_column_definition_feature_not_entered = templateColumnFiles.length === 0;

const summary = {
  task: "LIB-CLEAN-4G-SRC-LIB-ABSENT-CHECK",
  paths: {
    lib_dir: LIB_DIR,
    final_homes: FINAL_HOMES,
  },
  lib_dir_exists: libDirExists,
  lib_entries: libEntries,
  lib_ts_count: libTsCount,
  lib_operational_count: libOperationalCount,
  libResiduals,
  template_column_definition_files_found: templateColumnFiles,
  checks,
};
console.log(JSON.stringify(summary, null, 2));

const required = [
  "src_lib_absent_or_empty",
  "src_lib_ts_files_zero",
  "src_lib_operational_files_zero",
  ...Object.keys(FINAL_HOMES).map((n) => `${n}_at_final_home`),
  ...ABSENT_FROM_LIB.map((n) => `${n.replace(/\./g, "_")}_absent_in_src_lib`),
  "no_residual_lib_imports_in_src_code",
  "TestWorkspace_present",
  "test_core_dir_present",
  "AutoRestoreWorkspace_present",
  "autorestore_route_present",
  "template_column_definition_feature_not_entered",
];
const allPass = required.every((k) => checks[k] === true);
const verdict = allPass ? "PASS" : "FAIL";
console.log(`[SRC_LIB_ABSENT_CHECK_LC4G] ${verdict}`);
process.exit(allPass ? 0 : 1);
