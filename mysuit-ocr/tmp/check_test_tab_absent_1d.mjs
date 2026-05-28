import { existsSync, readdirSync, readFileSync } from "node:fs";
import { join, relative } from "node:path";
import { execFileSync } from "node:child_process";

const ROOT = process.cwd();
const BACKUP_DIR = join(ROOT, "backup", "test_tab_20260526_before_remove");
const REPORT = join(ROOT, "tmp", "test_tab_1d_absent_check.md");

const preExistingDirty = new Set([
  "docs/FRONTEND_CLEANUP_1B_JS_CLEAN_JSON_FIXTURE_RUNNER_20260521.json",
  "docs/FRONTEND_CLEANUP_1B_JS_CLEAN_JSON_FIXTURE_RUNNER_20260521.md",
  "docs/FRONTEND_CLEANUP_3D2_RUNNER_RESULT_20260521.json",
  "next.config.ts",
  "src/app/api/ocr-extract/route.ts",
  "src/common/ui/OcrCanvasPane.tsx",
  "src/common/utils/cleanJsonBuilder.ts",
  "src/components/runocr/RunOcrWorkspace.tsx",
  "src/components/runocr/ui/OcrResultPanel.tsx",
  "src/components/runocr/utils/mapOcrResponse.ts",
  "src/components/template/UnstructuredBuilder.tsx",
  "src/components/template/ui/TemplateAnnotator.tsx",
  "src/components/template/ui/TemplateRightPanel.tsx",
  "../ocr-server/data/review_log.jsonl",
  "public/data/testsets/invoice_statement/1-1.jpg",
  "src/components/template/utils/canonicalColumnOptions.ts",
  "src/components/template/utils/documentTypeGroup.ts",
  "tmp/check_unstructured_selection_delete_ux_tpl14a.mjs",
]);

const allowedNewOrModified = new Set([
  "tmp/test_tab_1a_removal_precheck.md",
  "tmp/check_test_tab_removal_precheck_1a.mjs",
  "tmp/test_tab_1b_backup_ui_hide.md",
  "tmp/check_test_tab_backup_ui_hide_1b.mjs",
  "tmp/test_tab_1c_route_remove_archive.md",
  "tmp/check_test_tab_route_remove_archive_1c.mjs",
  "tmp/test_tab_1d_absent_check.md",
  "tmp/check_test_tab_absent_1d.mjs",
  "../ocr-server/logs/codex_TEST_TAB_1A_REMOVAL_PRECHECK_NO_PROD_MODIFY.out.log",
  "../ocr-server/logs/codex_TEST_TAB_1A_REMOVAL_PRECHECK_NO_PROD_MODIFY.err.log",
  "../ocr-server/logs/codex_TEST_TAB_1B_BACKUP_AND_UI_HIDE.out.log",
  "../ocr-server/logs/codex_TEST_TAB_1B_BACKUP_AND_UI_HIDE.err.log",
  "../ocr-server/logs/codex_TEST_TAB_1C_ROUTE_REMOVE_ARCHIVE.out.log",
  "../ocr-server/logs/codex_TEST_TAB_1C_ROUTE_REMOVE_ARCHIVE.err.log",
  "../ocr-server/logs/codex_TEST_TAB_1D_ABSENT_CHECK.out.log",
  "../ocr-server/logs/codex_TEST_TAB_1D_ABSENT_CHECK.err.log",
]);

const allowedNewPrefixes = ["backup/test_tab_20260526_before_remove/"];
const allowedRemovedPrefixes = ["src/app/test/", "src/components/test/"];

const checks = [];
function check(name, ok, detail = "") {
  checks.push({ name, ok, detail });
  console.log(`[${ok ? "PASS" : "FAIL"}] ${name}${detail ? ` - ${detail}` : ""}`);
}

function walk(dir, out = []) {
  if (!existsSync(dir)) return out;
  for (const ent of readdirSync(dir, { withFileTypes: true })) {
    const p = join(dir, ent.name);
    if (ent.isDirectory()) walk(p, out);
    else out.push(p);
  }
  return out;
}

function rel(p) {
  return relative(ROOT, p).replaceAll("\\", "/");
}

function readText(path) {
  return existsSync(path) ? readFileSync(path, "utf8") : "";
}

function stripComments(text) {
  return text
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .replace(/(^|[^:])\/\/.*$/gm, "$1");
}

function normalizeStatusPath(line) {
  const body = line.slice(3).trim();
  const p = body.includes(" -> ") ? body.split(" -> ").pop() : body;
  return p.replaceAll("\\", "/");
}

function gitStatusLines() {
  try {
    return execFileSync("git", ["status", "--short"], {
      cwd: ROOT,
      encoding: "utf8",
      stdio: ["ignore", "pipe", "pipe"],
    }).split(/\r?\n/).filter(Boolean);
  } catch {
    return ["GIT_STATUS_FAILED"];
  }
}

check("src/app/test absent", !existsSync(join(ROOT, "src", "app", "test")));
check("src/components/test absent", !existsSync(join(ROOT, "src", "components", "test")));
check("backup app/test exists", existsSync(join(BACKUP_DIR, "src", "app", "test", "page.tsx")));
check("backup TestWorkspace exists", existsSync(join(BACKUP_DIR, "src", "components", "test", "TestWorkspace.tsx")));

for (const file of ["types.ts", "match.ts", "extract.ts", "autofill.ts", "finalize.ts"]) {
  check(`backup core ${file} exists`, existsSync(join(BACKUP_DIR, "src", "components", "test", "core", file)));
}
check("backup profiles.ts exists", existsSync(join(BACKUP_DIR, "src", "components", "test", "utils", "profiles.ts")));
const manifestSnapshots = walk(join(BACKUP_DIR, "manifest_snapshots")).filter((p) => p.endsWith("manifest.json"));
check("manifest snapshots exist", manifestSnapshots.length > 0, `count=${manifestSnapshots.length}`);

check("src/common/config/testsets.ts exists", existsSync(join(ROOT, "src", "common", "config", "testsets.ts")));
check("public/data/testsets exists", existsSync(join(ROOT, "public", "data", "testsets")));
for (const route of ["test-images", "ocr-cache", "autofill-cache", "ground-truth"]) {
  check(`API ${route} exists`, existsSync(join(ROOT, "src", "app", "api", route, "route.ts")));
}

const srcFiles = walk(join(ROOT, "src")).filter((p) => /\.(ts|tsx|js|jsx)$/.test(p));
const workspaceHits = [];
const componentsTestHits = [];
const aliasComponentsTestHits = [];
const libAliasHits = [];
for (const file of srcFiles) {
  const text = readText(file);
  const codeText = stripComments(text);
  const fileRel = rel(file);
  if (/\bTestWorkspace\b/.test(codeText)) workspaceHits.push(fileRel);
  if (/from\s+["'][^"']*components\/test|import\(\s*["'][^"']*components\/test/.test(text)) componentsTestHits.push(fileRel);
  if (/from\s+["']@\/components\/test|import\(\s*["']@\/components\/test/.test(text)) aliasComponentsTestHits.push(fileRel);
  if (/from\s+["']@\/lib|import\(\s*["']@\/lib/.test(text)) libAliasHits.push(fileRel);
}
check("src residual TestWorkspace 0", workspaceHits.length === 0, workspaceHits.join(", "));
check("src residual components/test 0", componentsTestHits.length === 0, componentsTestHits.join(", "));
check("src residual @/components/test 0", aliasComponentsTestHits.length === 0, aliasComponentsTestHits.join(", "));

const sidebarText = readText(join(ROOT, "src", "components", "layout", "Sidebar.tsx"));
const defaultItemsText = sidebarText.match(/const\s+DEFAULT_ITEMS[\s\S]*?\];/)?.[0] ?? "";
check("menu/sidebar /test exposure 0", !/href:\s*["']\/test["']|label:\s*["']Test["']/.test(defaultItemsText));

const srcLib = join(ROOT, "src", "lib");
const srcLibFiles = existsSync(srcLib) ? readdirSync(srcLib).filter((name) => !name.startsWith(".")) : [];
check("src/lib absent maintained", srcLibFiles.length === 0, `files=${srcLibFiles.length}`);
check("@/lib import 0", libAliasHits.length === 0, libAliasHits.join(", "));
check("report exists", existsSync(REPORT), rel(REPORT));

for (const path of [
  "src/app/ocr",
  "src/app/runocr",
  "src/app/template",
  "src/app/history",
  "src/app/autorestore",
  "src/app/login",
  "src/components/runocr",
  "src/components/template",
  "src/components/history",
  "src/components/login",
  "src/components/layout",
]) {
  check(`preserved feature path exists: ${path}`, existsSync(join(ROOT, path)));
}

const unexpected = gitStatusLines().filter((line) => {
  if (line === "GIT_STATUS_FAILED") return true;
  const p = normalizeStatusPath(line);
  return (
    !preExistingDirty.has(p) &&
    !allowedNewOrModified.has(p) &&
    !allowedNewPrefixes.some((prefix) => p.startsWith(prefix)) &&
    !(line.trimStart().startsWith("D ") && allowedRemovedPrefixes.some((prefix) => p.startsWith(prefix)))
  );
});
check("no unexpected source changes for 1D", unexpected.length === 0, unexpected.slice(0, 8).join("; "));

const failCount = checks.filter((c) => !c.ok).length;
console.log(`FAIL count: ${failCount}`);
if (failCount === 0) {
  console.log("[TEST_TAB_ABSENT_CHECK_1D] PASS");
  process.exit(0);
}
console.log("[TEST_TAB_ABSENT_CHECK_1D] FAIL");
process.exit(1);
