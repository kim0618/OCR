import { existsSync, readdirSync, readFileSync } from "node:fs";
import { join, relative } from "node:path";
import { execFileSync } from "node:child_process";

const ROOT = process.cwd();
const REPORT = join(ROOT, "tmp", "test_tab_1a_removal_precheck.md");

const requiredSections = [
  "### 1. Summary",
  "### 2. Current Test Tab Tree",
  "### 3. UI / Route Exposure",
  "### 4. TestWorkspace Dependency Map",
  "### 5. Test Core File Ownership",
  "### 6. Test Utils / Profiles / Testsets",
  "### 7. API Route Impact",
  "### 8. Backup Plan",
  "### 9. Removal Strategy Options",
  "### 10. Recommended Actual Phase",
  "### 11. Do Not Touch Yet",
  "### 12. Verification Strategy",
  "### 13. Zero-touch Verification",
];

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

check("report 파일 존재", existsSync(REPORT), REPORT);
const reportText = existsSync(REPORT) ? readFileSync(REPORT, "utf8") : "";
for (const section of requiredSections) {
  check(`${section} 섹션 존재`, reportText.includes(section));
}

const routeExists = existsSync(join(ROOT, "src", "app", "test", "page.tsx"));
const routeBackedUp = existsSync(join(ROOT, "backup", "test_tab_20260526_before_remove", "src", "app", "test", "page.tsx"));
check("src/app/test route 존재 또는 1C archive backup 존재 확인", routeExists || routeBackedUp);
const workspaceExists = existsSync(join(ROOT, "src", "components", "test", "TestWorkspace.tsx"));
const workspaceBackedUp = existsSync(join(ROOT, "backup", "test_tab_20260526_before_remove", "src", "components", "test", "TestWorkspace.tsx"));
check("src/components/test/TestWorkspace.tsx 존재 또는 1C archive backup 존재 확인", workspaceExists || workspaceBackedUp);
const coreDir = join(ROOT, "src", "components", "test", "core");
const coreBackupDir = join(ROOT, "backup", "test_tab_20260526_before_remove", "src", "components", "test", "core");
check("src/components/test/core 또는 1C archive backup test files 존재 확인", (existsSync(coreDir) && walk(coreDir).length > 0) || (existsSync(coreBackupDir) && walk(coreBackupDir).length > 0));
check("src/components/test/utils/profiles.ts 존재 또는 1C archive backup 존재 확인", existsSync(join(ROOT, "src", "components", "test", "utils", "profiles.ts")) || existsSync(join(ROOT, "backup", "test_tab_20260526_before_remove", "src", "components", "test", "utils", "profiles.ts")));
check("src/common/config/testsets.ts 존재 확인", existsSync(join(ROOT, "src", "common", "config", "testsets.ts")));

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
check("운영 코드 수정 없음", unexpected.length === 0, unexpected.slice(0, 8).join("; "));

const srcLib = join(ROOT, "src", "lib");
const srcLibFiles = existsSync(srcLib) ? readdirSync(srcLib).filter((name) => !name.startsWith(".")) : [];
check("src/lib absent 유지", srcLibFiles.length === 0, `files=${srcLibFiles.length}`);

const srcFiles = walk(join(ROOT, "src")).filter((p) => /\.(ts|tsx|js|jsx)$/.test(p));
const aliasHits = [];
for (const file of srcFiles) {
  const text = readFileSync(file, "utf8");
  if (/from\s+["']@\/lib|import\(\s*["']@\/lib/.test(text)) {
    aliasHits.push(relative(ROOT, file).replaceAll("\\", "/"));
  }
}
check("@/lib import 0건 유지", aliasHits.length === 0, aliasHits.join(", "));

const failCount = checks.filter((c) => !c.ok).length;
console.log(`FAIL count: ${failCount}`);
if (failCount === 0) {
  console.log("[TEST_TAB_REMOVAL_PRECHECK_1A] PASS");
  process.exit(0);
}
console.log("[TEST_TAB_REMOVAL_PRECHECK_1A] FAIL");
process.exit(1);
