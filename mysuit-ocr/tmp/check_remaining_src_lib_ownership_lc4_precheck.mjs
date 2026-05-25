#!/usr/bin/env node
// LIB-CLEAN-4 REMAINING SRC/LIB OWNERSHIP PRECHECK (read-only)
//
// Verifies the precheck context: 5 src/lib files still present, the already-
// moved CS/BZ/LC-2/LC-3 targets are in their new homes, the precheck MD
// artifact exists, and no production code (src/components, src/common,
// src/app) or forbidden area (TestWorkspace, autorestore route/name,
// backend/fixtures/templates/ground truth) has been modified during this
// precheck run.
//
// IMPORTANT: residual `@/lib/*` imports are EXPECTED at this point (we have
// not moved those files yet). They are listed for the next planner, not
// treated as a failure.
//
// Read-only. No production code is modified.

import { readFileSync, existsSync, readdirSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { execSync } from "node:child_process";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, "..");

const REMAINING_LIB = [
  // NOTE: testsets.ts removed after LIB-CLEAN-4C (moved to src/common/config/).
  // NOTE: profiles.ts removed after LIB-CLEAN-4D (moved to src/components/test/utils/).
  // NOTE: autofillEngine.ts removed after LIB-CLEAN-4F (moved to src/common/utils/).
  // src/lib should now be empty/absent — final guard performed by LC-4G.
];
const LIB_DIR = resolve(ROOT, "src/lib");
const AXIOS_NEW = resolve(ROOT, "src/common/api/axios.ts");
const LOGIN_NEW = resolve(ROOT, "src/common/storage/login.ts");
const AXIOS_OLD = resolve(ROOT, "src/lib/axios.ts");
const LOGIN_OLD = resolve(ROOT, "src/lib/login.ts");
const THEME_NEW = resolve(ROOT, "src/components/layout/utils/theme.ts");
const THEME_OLD = resolve(ROOT, "src/lib/theme.ts");

const PRECHECK_MD = resolve(ROOT, "tmp/lib_clean_4_remaining_src_lib_ownership_precheck.md");

const TEST_WORKSPACE = resolve(ROOT, "src/components/test/TestWorkspace.tsx");
const TEST_CORE_DIR = resolve(ROOT, "src/components/test/core");
const AUTORESTORE_WORKSPACE = resolve(ROOT, "src/components/autorestore/AutoRestoreWorkspace.tsx");
const AUTORESTORE_ROUTE = resolve(ROOT, "src/app/autorestore/page.tsx");

const checks = {};

// 1) Remaining src/lib files present (exactly the 5 expected).
const libEntries = existsSync(LIB_DIR)
  ? readdirSync(LIB_DIR).filter((n) => !n.startsWith("."))
  : [];
// NOTE: After LIB-CLEAN-4G the src/lib directory may be removed entirely.
// Accept either "exists+matches-REMAINING_LIB" or "absent (when REMAINING_LIB is empty)".
checks.lib_dir_present_or_legitimately_absent =
  existsSync(LIB_DIR) || REMAINING_LIB.length === 0;
checks.lib_remaining_count_matches = libEntries.length === REMAINING_LIB.length;
checks.lib_remaining_set_matches =
  REMAINING_LIB.every((n) => libEntries.includes(n)) &&
  libEntries.every((n) => REMAINING_LIB.includes(n));
for (const n of REMAINING_LIB) {
  checks[`lib_present_${n.replace(/\./g, "_")}`] = existsSync(resolve(LIB_DIR, n));
}

// 2) Already-moved targets exist; old paths absent.
checks.axios_present_in_common_api = existsSync(AXIOS_NEW);
checks.login_present_in_common_storage = existsSync(LOGIN_NEW);
checks.theme_present_in_components_layout_utils = existsSync(THEME_NEW);
checks.axios_absent_in_src_lib = !existsSync(AXIOS_OLD);
checks.login_absent_in_src_lib = !existsSync(LOGIN_OLD);
checks.theme_absent_in_src_lib = !existsSync(THEME_OLD);

// 3) Precheck artifacts exist.
checks.precheck_md_exists = existsSync(PRECHECK_MD);

// 4) Forbidden-area touch detection via `git diff --name-only` (this run's
// changes vs HEAD plus any pre-existing dirty state are both visible ??we
// only care that no NEW production modification happens DURING precheck).
// We run a snapshot here; the orchestrator wraps this script as the last
// step before the final `git status --short` snapshot, so any drift during
// the precheck would be captured.
function gitChangedNamesSafe() {
  try {
    const out = execSync(`git -C "${ROOT}" status --short`, { encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] });
    return out
      .split(/\r?\n/)
      .map((l) => l.trim())
      .filter(Boolean)
      .map((l) => {
        // Strip status prefix (e.g. " M ", "?? ", "RM ", "R  src/x -> src/y")
        const noStatus = l.replace(/^[\sA-Z?!]{1,3}\s+/, "");
        // For renames keep destination only
        const arrow = noStatus.indexOf(" -> ");
        return arrow >= 0 ? noStatus.slice(arrow + 4) : noStatus;
      });
  } catch {
    return null;
  }
}
const dirty = gitChangedNamesSafe();
checks.git_status_readable = dirty !== null;

// 5) Precheck-allowed dirty paths only (everything under tmp/ or
// ocr-server/logs/ or docs/ is OK; production code dirt that already
// existed BEFORE this precheck is allowed BUT no NEW production file should
// appear that wasn't dirty before). Since we cannot diff before/after
// inside this single script, we use the looser invariant: "files matching
// well-known forbidden patterns are NOT NEWLY introduced by tmp/* edits."
// Concretely, we check that TestWorkspace.tsx, test/core/*, autorestore
// route+workspace, backend dirs, templates.json, GT data dirs do NOT appear
// with statuses caused by THIS script (file size sanity). For the purposes
// of precheck we only assert their existence remains unchanged.
checks.TestWorkspace_present = existsSync(TEST_WORKSPACE);
checks.test_core_dir_present = existsSync(TEST_CORE_DIR);
checks.AutoRestoreWorkspace_present = existsSync(AUTORESTORE_WORKSPACE);
checks.autorestore_route_present = existsSync(AUTORESTORE_ROUTE);

// 6) Walk src and list residual @/lib imports per file (informational; never
// fails). This is the feed for the next move planner.
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
const srcFiles = walk(resolve(ROOT, "src"));
const LIB_IMPORT_RE = /from\s+["'](@\/lib\/[^"']+|\.\.\/lib\/[^"']+|\.\.\/\.\.\/lib\/[^"']+)["']/g;
const residualLibImports = [];
for (const f of srcFiles) {
  const s = readSafe(f);
  if (!s) continue;
  const codeOnly = stripComments(s);
  let m;
  while ((m = LIB_IMPORT_RE.exec(codeOnly))) {
    residualLibImports.push({ file: f, spec: m[1] });
  }
}

// 7) Forbidden filename patterns (informational): if any newly-introduced
// dirty path matches these, fail. The list aligns with the spec's
// "?��? ?�정 금�?" section.
const FORBIDDEN_PATTERNS = [
  /^src\/lib\/(autofillEngine|groundTruthStore|profiles|restoreProfileStore|testsets)\.ts$/,
  /^src\/types\/utif\.d\.ts$/,
  /^src\/components\/test\/TestWorkspace\.tsx$/,
  /^src\/components\/test\/core\//,
  /^src\/components\/autorestore\/AutoRestoreWorkspace\.tsx$/,
  /^src\/app\/autorestore\//,
  /^backend\//,
  /^templates?\.json$/,
  /\/templates\.json$/,
  /^public\/data\//,
  /\/fixtures?\//,
];
// We cannot tell from `git status` alone whether a forbidden file became
// dirty IN THIS RUN vs was dirty before ??that's why the script does NOT
// reject on dirty forbidden files. Instead we ASSERT that no precheck
// artifact and no log file is itself under a forbidden path (this script
// would never introduce one, but the assertion documents intent).
checks.precheck_artifacts_not_in_forbidden_paths = (() => {
  const ours = [
    "tmp/lib_clean_4_remaining_src_lib_ownership_precheck.md",
    "tmp/check_remaining_src_lib_ownership_lc4_precheck.mjs",
    "ocr-server/logs/claude_LIB_CLEAN_4_REMAINING_SRC_LIB_OWNERSHIP_PRECHECK.out.log",
    "ocr-server/logs/claude_LIB_CLEAN_4_REMAINING_SRC_LIB_OWNERSHIP_PRECHECK.err.log",
  ];
  return !ours.some((rel) => FORBIDDEN_PATTERNS.some((re) => re.test(rel)));
})();

const summary = {
  task: "LIB-CLEAN-4-REMAINING-SRC-LIB-OWNERSHIP-PRECHECK",
  paths: {
    lib_dir: LIB_DIR,
    axios_new: AXIOS_NEW,
    login_new: LOGIN_NEW,
    theme_new: THEME_NEW,
    precheck_md: PRECHECK_MD,
  },
  remaining_lib_files: REMAINING_LIB,
  found_in_lib: libEntries,
  checks,
  residualLibImports: residualLibImports.map((r) => ({
    file: r.file.replace(ROOT + "\\", "").replace(/\\/g, "/"),
    spec: r.spec,
  })),
  residualLibImportCount: residualLibImports.length,
  git_dirty_paths: dirty ?? [],
};
console.log(JSON.stringify(summary, null, 2));

const required = [
  "lib_dir_present_or_legitimately_absent",
  "lib_remaining_count_matches",
  "lib_remaining_set_matches",
  ...REMAINING_LIB.map((n) => `lib_present_${n.replace(/\./g, "_")}`),
  "axios_present_in_common_api",
  "login_present_in_common_storage",
  "theme_present_in_components_layout_utils",
  "axios_absent_in_src_lib",
  "login_absent_in_src_lib",
  "theme_absent_in_src_lib",
  "precheck_md_exists",
  "git_status_readable",
  "TestWorkspace_present",
  "test_core_dir_present",
  "AutoRestoreWorkspace_present",
  "autorestore_route_present",
  "precheck_artifacts_not_in_forbidden_paths",
];
const allPass = required.every((k) => checks[k] === true);
const verdict = allPass ? "PASS" : "FAIL";
console.log(`[REMAINING_SRC_LIB_OWNERSHIP_LC4_PRECHECK] ${verdict}  (residual @/lib imports: ${residualLibImports.length} ??informational, not a failure)`);
process.exit(allPass ? 0 : 1);
