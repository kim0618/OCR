import { existsSync, readdirSync, readFileSync } from "node:fs";
import { join, relative } from "node:path";
import { execFileSync } from "node:child_process";

const ROOT = process.cwd();
const REPORT = join(ROOT, "tmp", "backend_test_1d_test_images_api_absent_check.md");

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
  "tmp/backend_test_1a_test_api_removal_precheck.md",
  "tmp/backend_test_1b_test_images_api_remove_precheck.md",
  "tmp/backend_test_1c_test_images_api_remove.md",
  "tmp/check_backend_test_api_removal_precheck_1a.mjs",
  "tmp/check_backend_test_images_api_remove_1c.mjs",
  "tmp/check_backend_test_images_api_remove_precheck_1b.mjs",
  "tmp/check_test_tab_absent_1d.mjs",
  "tmp/check_test_tab_backup_ui_hide_1b.mjs",
  "tmp/check_test_tab_removal_precheck_1a.mjs",
  "tmp/check_test_tab_route_remove_archive_1c.mjs",
  "tmp/check_unstructured_selection_delete_ux_tpl14a.mjs",
  "tmp/test_tab_1a_removal_precheck.md",
  "tmp/test_tab_1b_backup_ui_hide.md",
  "tmp/test_tab_1c_route_remove_archive.md",
  "tmp/test_tab_1d_absent_check.md",
]);

const allowedNewOrModified = new Set([
  "tmp/backend_test_1d_test_images_api_absent_check.md",
  "tmp/check_backend_test_images_api_absent_1d.mjs",
  "../ocr-server/logs/codex_BACKEND_TEST_1D_TEST_IMAGES_API_ABSENT_CHECK.out.log",
  "../ocr-server/logs/codex_BACKEND_TEST_1D_TEST_IMAGES_API_ABSENT_CHECK.err.log",
]);

const allowedRemovedPrefixes = ["src/app/test/", "src/components/test/", "src/app/api/test-images/"];

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

check("src/app/api/test-images absent", !existsSync(join(ROOT, "src", "app", "api", "test-images")));
check("src/app/api/test-images/route.ts absent", !existsSync(join(ROOT, "src", "app", "api", "test-images", "route.ts")));
check("src/app/test absent maintained", !existsSync(join(ROOT, "src", "app", "test")));
check("src/components/test absent maintained", !existsSync(join(ROOT, "src", "components", "test")));
check("backup/test_tab_20260526_before_remove exists", existsSync(join(ROOT, "backup", "test_tab_20260526_before_remove")));
check("src/common/config/testsets.ts exists", existsSync(join(ROOT, "src", "common", "config", "testsets.ts")));
check("public/data/testsets exists", existsSync(join(ROOT, "public", "data", "testsets")));
for (const route of ["ocr-cache", "autofill-cache", "ground-truth"]) {
  check(`protected route exists: ${route}`, existsSync(join(ROOT, "src", "app", "api", route, "route.ts")));
}

const srcFiles = walk(join(ROOT, "src")).filter((p) => /\.(ts|tsx|js|jsx)$/.test(p));
const apiHits = [];
const testImageHits = [];
const workspaceHits = [];
const componentsTestHits = [];
const libAliasHits = [];
for (const file of srcFiles) {
  const text = readFileSync(file, "utf8");
  const codeText = stripComments(text);
  const fileRel = rel(file);
  if (/\/api\/test-images/.test(text)) apiHits.push(fileRel);
  if (/test-images/.test(text)) testImageHits.push(fileRel);
  if (/\bTestWorkspace\b/.test(codeText)) workspaceHits.push(fileRel);
  if (/from\s+["'][^"']*components\/test|import\(\s*["'][^"']*components\/test/.test(text)) componentsTestHits.push(fileRel);
  if (/from\s+["']@\/lib|import\(\s*["']@\/lib/.test(text)) libAliasHits.push(fileRel);
}
check("운영 src /api/test-images caller 0", apiHits.length === 0, apiHits.join(", "));
check("운영 src test-images caller 0", testImageHits.length === 0, testImageHits.join(", "));
check("운영 src TestWorkspace reference 0", workspaceHits.length === 0, workspaceHits.join(", "));
check("운영 src components/test import 0", componentsTestHits.length === 0, componentsTestHits.join(", "));

const srcLib = join(ROOT, "src", "lib");
const srcLibFiles = existsSync(srcLib) ? readdirSync(srcLib).filter((name) => !name.startsWith(".")) : [];
check("src/lib absent maintained", srcLibFiles.length === 0, `files=${srcLibFiles.length}`);
check("@/lib import 0 maintained", libAliasHits.length === 0, libAliasHits.join(", "));
check("report exists", existsSync(REPORT), rel(REPORT));

const unexpected = gitStatusLines().filter((line) => {
  if (line === "GIT_STATUS_FAILED") return true;
  const p = normalizeStatusPath(line);
  return (
    !preExistingDirty.has(p) &&
    !allowedNewOrModified.has(p) &&
    !(line.trimStart().startsWith("D ") && allowedRemovedPrefixes.some((prefix) => p.startsWith(prefix)))
  );
});
check("no unexpected production changes for 1D", unexpected.length === 0, unexpected.slice(0, 8).join("; "));

const failCount = checks.filter((c) => !c.ok).length;
console.log(`FAIL count: ${failCount}`);
if (failCount === 0) {
  console.log("[BACKEND_TEST_IMAGES_API_ABSENT_1D] PASS");
  process.exit(0);
}
console.log("[BACKEND_TEST_IMAGES_API_ABSENT_1D] FAIL");
process.exit(1);
