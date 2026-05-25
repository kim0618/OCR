#!/usr/bin/env node
// LIB-CLEAN-4E AUTOFILL ENGINE PRECHECK (read-only)
//
// Verifies the precheck context for the autofillEngine.ts → common/utils move:
// 1) src/lib/autofillEngine.ts is the sole remaining file in src/lib.
// 2) src/common/utils/autofillEngine.ts is NOT yet present.
// 3) Already-moved targets from LIB-CLEAN-1..4D are in their new homes.
// 4) Internal sibling dep (restoreProfileStore) is already resolved to
//    @/common/storage/restoreProfileStore (so the LC-4F move has no extra
//    sibling-rewrite work).
// 5) autofillEngine has no React/components/JSX/CSS dependency.
// 6) autofillEngine's single localStorage read is SSR-guarded — flagged for
//    LC-4F to permit it explicitly (not a blocker here).
// 7) Importers (production + tmp) are enumerated for LC-4F planning.
// 8) precheck MD artifact exists.
//
// IMPORTANT: residual @/lib/autofillEngine imports are EXPECTED (we have not
// moved the file yet). They are listed informational, not a failure.
//
// Read-only. No production code is modified.

import { readFileSync, existsSync, readdirSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, "..");

const AUTOFILL_AT_LIB = resolve(ROOT, "src/lib/autofillEngine.ts");
const AUTOFILL_AT_COMMON_UTILS = resolve(ROOT, "src/common/utils/autofillEngine.ts");
const LIB_DIR = resolve(ROOT, "src/lib");

// Already-moved guard.
const TESTSETS_NEW = resolve(ROOT, "src/common/config/testsets.ts");
const PROFILES_NEW = resolve(ROOT, "src/components/test/utils/profiles.ts");
const AXIOS_NEW = resolve(ROOT, "src/common/api/axios.ts");
const LOGIN_NEW = resolve(ROOT, "src/common/storage/login.ts");
const GROUND_TRUTH_NEW = resolve(ROOT, "src/common/storage/groundTruthStore.ts");
const RESTORE_PROFILE_NEW = resolve(ROOT, "src/common/storage/restoreProfileStore.ts");
const THEME_NEW = resolve(ROOT, "src/components/layout/utils/theme.ts");
const TESTSETS_OLD = resolve(ROOT, "src/lib/testsets.ts");
const PROFILES_OLD = resolve(ROOT, "src/lib/profiles.ts");
const AXIOS_OLD = resolve(ROOT, "src/lib/axios.ts");
const LOGIN_OLD = resolve(ROOT, "src/lib/login.ts");
const GROUND_TRUTH_OLD = resolve(ROOT, "src/lib/groundTruthStore.ts");
const RESTORE_PROFILE_OLD = resolve(ROOT, "src/lib/restoreProfileStore.ts");
const THEME_OLD = resolve(ROOT, "src/lib/theme.ts");

const PRECHECK_MD = resolve(ROOT, "tmp/lib_clean_4e_autofill_engine_precheck.md");

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

// 1) autofillEngine.ts is present at one of two locations (LC-4E captured
// it in src/lib; LC-4F moves it to src/common/utils). Either is accepted.
const autofillAtLib = existsSync(AUTOFILL_AT_LIB);
const autofillAtCommonUtils = existsSync(AUTOFILL_AT_COMMON_UTILS);
checks.autofillEngine_present_in_src_lib_or_common_utils = autofillAtLib || autofillAtCommonUtils;
// Mutual exclusion: never both.
checks.autofillEngine_not_in_both_locations = !(autofillAtLib && autofillAtCommonUtils);

// 2) After LC-4F, src/lib should contain only autofillEngine.ts (pre-LC-4F
// state) OR be empty/absent (post-LC-4F state). Reject any other content.
const libEntries = existsSync(LIB_DIR)
  ? readdirSync(LIB_DIR).filter((n) => !n.startsWith("."))
  : [];
checks.src_lib_contains_only_autofillEngine_or_empty =
  (libEntries.length === 1 && libEntries[0] === "autofillEngine.ts") ||
  libEntries.length === 0;

// 3) Already-moved targets exist; src/lib old paths absent.
checks.testsets_in_common_config = existsSync(TESTSETS_NEW);
checks.profiles_in_components_test_utils = existsSync(PROFILES_NEW);
checks.axios_in_common_api = existsSync(AXIOS_NEW);
checks.login_in_common_storage = existsSync(LOGIN_NEW);
checks.ground_truth_in_common_storage = existsSync(GROUND_TRUTH_NEW);
checks.restore_profile_in_common_storage = existsSync(RESTORE_PROFILE_NEW);
checks.theme_in_components_layout_utils = existsSync(THEME_NEW);
checks.testsets_absent_in_src_lib = !existsSync(TESTSETS_OLD);
checks.profiles_absent_in_src_lib = !existsSync(PROFILES_OLD);
checks.axios_absent_in_src_lib = !existsSync(AXIOS_OLD);
checks.login_absent_in_src_lib = !existsSync(LOGIN_OLD);
checks.ground_truth_absent_in_src_lib = !existsSync(GROUND_TRUTH_OLD);
checks.restore_profile_absent_in_src_lib = !existsSync(RESTORE_PROFILE_OLD);
checks.theme_absent_in_src_lib = !existsSync(THEME_OLD);

// 4) Precheck MD artifact exists.
checks.precheck_md_exists = existsSync(PRECHECK_MD);

// 5) TestWorkspace + test/core + autorestore route/name unchanged in presence.
checks.TestWorkspace_present = existsSync(TEST_WORKSPACE);
checks.test_core_dir_present = existsSync(TEST_CORE_DIR);
checks.AutoRestoreWorkspace_present = existsSync(AUTORESTORE_WORKSPACE);
checks.autorestore_route_present = existsSync(AUTORESTORE_ROUTE);

// 6) autofillEngine internal sibling dep already resolved to @/common/storage.
const AUTOFILL_CURRENT = autofillAtLib ? AUTOFILL_AT_LIB : AUTOFILL_AT_COMMON_UTILS;
const autofillSrc = readSafe(AUTOFILL_CURRENT);
checks.autofill_imports_restoreProfile_via_common_storage =
  autofillSrc !== null &&
  /from\s+["']@\/common\/storage\/restoreProfileStore["']/.test(autofillSrc) &&
  !/from\s+["']\.\/restoreProfileStore["']/.test(stripComments(autofillSrc));
checks.autofill_imports_bizNumber_via_common_utils =
  autofillSrc !== null &&
  /from\s+["']@\/common\/utils\/bizNumber["']/.test(autofillSrc);
checks.autofill_imports_historyStore_via_common_storage =
  autofillSrc !== null &&
  /from\s+["']@\/common\/storage\/historyStore["']/.test(autofillSrc);

// 7) common/utils suitability scan.
//    - No React / no components/* / no JSX.
//    - No fetch/XMLHttpRequest.
//    - `window.localStorage` IS present (1 site, SSR-guarded). Flagged as
//      "ssr_guarded_localstorage_present" — not a blocker for LC-4F but
//      LC-4F static check must permit it explicitly.
const autofillCode = autofillSrc !== null ? stripComments(autofillSrc) : "";
checks.autofill_no_react_import =
  autofillSrc !== null && !/from\s+["']react(?:-dom)?["']/.test(autofillSrc);
checks.autofill_no_components_import =
  autofillSrc !== null && !/from\s+["'][^"']*\/components\//.test(autofillSrc);
checks.autofill_no_backend_or_node_fs_import =
  autofillSrc !== null &&
  !/from\s+["'](?:node:)?(?:fs|fs\/promises|path)["']/.test(autofillSrc) &&
  !/from\s+["'][^"']*backend[^"']*["']/.test(autofillSrc);
checks.autofill_no_fetch_or_xhr =
  autofillSrc !== null &&
  !/\bfetch\s*\(/.test(autofillCode) &&
  !/\bXMLHttpRequest\b/.test(autofillCode);
checks.autofill_no_document_dom =
  autofillSrc !== null && !/\bdocument\./.test(autofillCode);
checks.autofill_no_window_navigation =
  autofillSrc !== null &&
  !/\bwindow\.location\b/.test(autofillCode) &&
  !/\bwindow\.history\b/.test(autofillCode);
// Informational: storage touch flag (not a failure).
const ssrGuardCount = (autofillCode.match(/typeof\s+window\s*===\s*["']undefined["']/g) || []).length;
const windowLocalStorageCount = (autofillCode.match(/\bwindow\.localStorage\b/g) || []).length;
checks.autofill_ssr_guards_present = ssrGuardCount >= 1;
checks.autofill_localstorage_writes_zero =
  autofillSrc !== null && !/\.localStorage\.(?:setItem|removeItem|clear)\b/.test(autofillCode);

// 8) Importer enumeration (production + tmp).
const srcFiles = walk(resolve(ROOT, "src"));
const tmpFiles = walk(resolve(ROOT, "tmp"));
const LIB_AUTOFILL_RE = /from\s+["'](@\/lib\/autofillEngine|\.\.\/lib\/autofillEngine|\.\.\/\.\.\/lib\/autofillEngine)["']/g;
const productionImporters = [];
const tmpImporters = [];
function scanForImporters(files, bucket) {
  for (const f of files) {
    const s = readSafe(f);
    if (!s) continue;
    const codeOnly = stripComments(s);
    let m;
    while ((m = LIB_AUTOFILL_RE.exec(codeOnly))) {
      const lineContent = codeOnly.split(/\r?\n/).find((ln) => ln.includes(m[1])) || "";
      const isTypeOnly = /\bimport\s+type\b|\{\s*type\s+/.test(lineContent);
      bucket.push({ file: relFromRoot(f), spec: m[1], kind: isTypeOnly ? "type-only" : "runtime" });
    }
  }
}
scanForImporters(srcFiles, productionImporters);
scanForImporters(tmpFiles, tmpImporters);

// 9) Forbidden-area existence guard (autorestore name/route, etc. should remain).
// Already checked above (TestWorkspace_present, AutoRestoreWorkspace_present,
// autorestore_route_present).

const summary = {
  task: "LIB-CLEAN-4E-AUTOFILL-ENGINE-PRECHECK",
  paths: {
    autofill_at_lib: AUTOFILL_AT_LIB,
    autofill_at_common_utils: AUTOFILL_AT_COMMON_UTILS,
    lib_dir: LIB_DIR,
    precheck_md: PRECHECK_MD,
  },
  found_in_lib: libEntries,
  productionImporters,
  tmpImporters,
  importerCount: {
    production: productionImporters.length,
    tmp: tmpImporters.length,
  },
  browserApiFindings: {
    ssr_guards: ssrGuardCount,
    window_localstorage_reads: windowLocalStorageCount,
  },
  checks,
};
console.log(JSON.stringify(summary, null, 2));

const required = [
  "autofillEngine_present_in_src_lib_or_common_utils",
  "autofillEngine_not_in_both_locations",
  "src_lib_contains_only_autofillEngine_or_empty",
  "testsets_in_common_config",
  "profiles_in_components_test_utils",
  "axios_in_common_api",
  "login_in_common_storage",
  "ground_truth_in_common_storage",
  "restore_profile_in_common_storage",
  "theme_in_components_layout_utils",
  "testsets_absent_in_src_lib",
  "profiles_absent_in_src_lib",
  "axios_absent_in_src_lib",
  "login_absent_in_src_lib",
  "ground_truth_absent_in_src_lib",
  "restore_profile_absent_in_src_lib",
  "theme_absent_in_src_lib",
  "precheck_md_exists",
  "TestWorkspace_present",
  "test_core_dir_present",
  "AutoRestoreWorkspace_present",
  "autorestore_route_present",
  "autofill_imports_restoreProfile_via_common_storage",
  "autofill_imports_bizNumber_via_common_utils",
  "autofill_imports_historyStore_via_common_storage",
  "autofill_no_react_import",
  "autofill_no_components_import",
  "autofill_no_backend_or_node_fs_import",
  "autofill_no_fetch_or_xhr",
  "autofill_no_document_dom",
  "autofill_no_window_navigation",
  "autofill_ssr_guards_present",
  "autofill_localstorage_writes_zero",
];
const allPass = required.every((k) => checks[k] === true);
const verdict = allPass ? "PASS" : "FAIL";
console.log(
  `[AUTOFILL_ENGINE_PRECHECK_LC4E] ${verdict}  ` +
    `(production importers: ${productionImporters.length}, tmp importers: ${tmpImporters.length}, ` +
    `SSR-guarded localStorage reads: ${windowLocalStorageCount} — informational)`,
);
process.exit(allPass ? 0 : 1);
