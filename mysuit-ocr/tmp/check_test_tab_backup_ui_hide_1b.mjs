import { existsSync, readdirSync, readFileSync } from "node:fs";
import { join, relative } from "node:path";
import { execFileSync } from "node:child_process";

const ROOT = process.cwd();
const BACKUP_DIR = join(ROOT, "backup", "test_tab_20260526_before_remove");
const REPORT = join(ROOT, "tmp", "test_tab_1b_backup_ui_hide.md");

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
  "tmp/check_test_tab_removal_precheck_1a.mjs",
  "tmp/check_unstructured_selection_delete_ux_tpl14a.mjs",
  "tmp/test_tab_1a_removal_precheck.md",
]);

const allowedNewOrModified = new Set([
  "tmp/test_tab_1b_backup_ui_hide.md",
  "tmp/check_test_tab_backup_ui_hide_1b.mjs",
  "tmp/test_tab_1c_route_remove_archive.md",
  "tmp/check_test_tab_route_remove_archive_1c.mjs",
  "tmp/test_tab_1d_absent_check.md",
  "tmp/check_test_tab_absent_1d.mjs",
  "../ocr-server/logs/codex_TEST_TAB_1B_BACKUP_AND_UI_HIDE.out.log",
  "../ocr-server/logs/codex_TEST_TAB_1B_BACKUP_AND_UI_HIDE.err.log",
  "../ocr-server/logs/codex_TEST_TAB_1C_ROUTE_REMOVE_ARCHIVE.out.log",
  "../ocr-server/logs/codex_TEST_TAB_1C_ROUTE_REMOVE_ARCHIVE.err.log",
  "../ocr-server/logs/codex_TEST_TAB_1D_ABSENT_CHECK.out.log",
  "../ocr-server/logs/codex_TEST_TAB_1D_ABSENT_CHECK.err.log",
]);

const allowedNewPrefixes = [
  "backup/test_tab_20260526_before_remove/",
];

const allowedRemovedPrefixes = [
  "src/app/test/",
  "src/components/test/",
];

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

function normalizeStatusPath(line) {
  const body = line.slice(3).trim();
  return (body.includes(" -> ") ? body.split(" -> ").pop() : body).replaceAll("\\", "/");
}

check("backup 디렉터리 존재", existsSync(BACKUP_DIR), rel(BACKUP_DIR));
check("backup에 src/app/test/page.tsx 존재", existsSync(join(BACKUP_DIR, "src", "app", "test", "page.tsx")));
check("backup에 src/components/test/TestWorkspace.tsx 존재", existsSync(join(BACKUP_DIR, "src", "components", "test", "TestWorkspace.tsx")));

const coreFiles = ["types.ts", "match.ts", "extract.ts", "autofill.ts", "finalize.ts"];
for (const file of coreFiles) {
  check(`backup에 src/components/test/core/${file} 존재`, existsSync(join(BACKUP_DIR, "src", "components", "test", "core", file)));
}

check("backup에 src/components/test/utils/profiles.ts 존재", existsSync(join(BACKUP_DIR, "src", "components", "test", "utils", "profiles.ts")));
check("1A report backup 또는 reference 존재", existsSync(join(BACKUP_DIR, "tmp", "test_tab_1a_removal_precheck.md")) || existsSync(join(ROOT, "tmp", "test_tab_1a_removal_precheck.md")));
const routeExistsInSource = existsSync(join(ROOT, "src", "app", "test", "page.tsx"));
const routeExistsInBackup = existsSync(join(BACKUP_DIR, "src", "app", "test", "page.tsx"));
check("src/app/test/page.tsx source present or 1C archive backup present", routeExistsInSource || routeExistsInBackup);
const workspaceExistsInSource = existsSync(join(ROOT, "src", "components", "test", "TestWorkspace.tsx"));
const workspaceExistsInBackup = existsSync(join(BACKUP_DIR, "src", "components", "test", "TestWorkspace.tsx"));
check("src/components/test/TestWorkspace.tsx source present or 1C archive backup present", workspaceExistsInSource || workspaceExistsInBackup);
check("운영 src/common/config/testsets.ts 존재", existsSync(join(ROOT, "src", "common", "config", "testsets.ts")));
check("운영 public/data/testsets 존재", existsSync(join(ROOT, "public", "data", "testsets")));

const apiRoutes = [
  "test-images",
  "ocr-cache",
  "autofill-cache",
  "ground-truth",
];
for (const route of apiRoutes) {
  check(`API route 유지: ${route}`, existsSync(join(ROOT, "src", "app", "api", route, "route.ts")));
}

const sidebarPath = join(ROOT, "src", "components", "layout", "Sidebar.tsx");
const sidebarText = existsSync(sidebarPath) ? readFileSync(sidebarPath, "utf8") : "";
const defaultItemsMatch = sidebarText.match(/const\s+DEFAULT_ITEMS[\s\S]*?\];/);
const defaultItemsText = defaultItemsMatch?.[0] ?? "";
const exposesTestMenu = /label:\s*["']Test["']|href:\s*["']\/test["']/.test(defaultItemsText);
check("Sidebar/layout/menu에 Test 메뉴가 노출되지 않음", !exposesTestMenu);

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
check("운영 코드에서 Test 탭 관련 import path 수정 없음", unexpected.length === 0, unexpected.slice(0, 8).join("; "));

const srcLib = join(ROOT, "src", "lib");
const srcLibFiles = existsSync(srcLib) ? readdirSync(srcLib).filter((name) => !name.startsWith(".")) : [];
check("src/lib absent 유지", srcLibFiles.length === 0, `files=${srcLibFiles.length}`);

const srcFiles = walk(join(ROOT, "src")).filter((p) => /\.(ts|tsx|js|jsx)$/.test(p));
const aliasHits = [];
for (const file of srcFiles) {
  const text = readFileSync(file, "utf8");
  if (/from\s+["']@\/lib|import\(\s*["']@\/lib/.test(text)) {
    aliasHits.push(rel(file));
  }
}
check("@/lib import 0건 유지", aliasHits.length === 0, aliasHits.join(", "));
check("report 파일 존재", existsSync(REPORT), rel(REPORT));

const failCount = checks.filter((c) => !c.ok).length;
console.log(`FAIL count: ${failCount}`);
if (failCount === 0) {
  console.log("[TEST_TAB_BACKUP_UI_HIDE_1B] PASS");
  process.exit(0);
}
console.log("[TEST_TAB_BACKUP_UI_HIDE_1B] FAIL");
process.exit(1);
