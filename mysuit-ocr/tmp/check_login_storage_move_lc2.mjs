import { existsSync, readdirSync, readFileSync } from "node:fs";
import { resolve } from "node:path";

const ROOT = process.cwd();
const rel = (p) => resolve(ROOT, p);
const read = (p) => (existsSync(rel(p)) ? readFileSync(rel(p), "utf8") : "");

const checks = {};

const loginPath = "src/common/storage/login.ts";
const oldLoginPath = "src/lib/login.ts";
const axiosPath = "src/common/api/axios.ts";
const oldAxiosPath = "src/lib/axios.ts";

checks.target_exists = existsSync(rel(loginPath));
checks.source_absent = !existsSync(rel(oldLoginPath));
checks.axios_moved_to_common_api_or_still_in_src_lib =
  existsSync(rel(axiosPath)) || existsSync(rel(oldAxiosPath));

const expectedLibFiles = [
  // NOTE: autofillEngine.ts removed after LIB-CLEAN-4F (moved to src/common/utils/).
  // NOTE: profiles.ts removed after LIB-CLEAN-4D (moved to src/components/test/utils/).
  // NOTE: testsets.ts removed after LIB-CLEAN-4C (moved to src/common/config/).
];
const actualLibFiles = existsSync(rel("src/lib"))
  ? readdirSync(rel("src/lib")).filter((name) => name.endsWith(".ts")).sort()
  : [];
checks.src_lib_remaining_files_match_expected =
  JSON.stringify(actualLibFiles) === JSON.stringify([...expectedLibFiles].sort());

const srcFiles = [];
function walk(dir) {
  if (!existsSync(rel(dir))) return;
  for (const name of readdirSync(rel(dir), { withFileTypes: true })) {
    const p = `${dir}/${name.name}`;
    if (name.isDirectory()) {
      if (name.name !== "node_modules") walk(p);
    } else if (/\.(ts|tsx|js|jsx|mjs)$/.test(name.name)) {
      srcFiles.push(p);
    }
  }
}
walk("src");

const srcText = srcFiles.map((file) => `${file}\n${read(file)}`).join("\n");
checks.no_alias_old_login_import = !srcText.includes("@/lib/login");
checks.no_relative_parent_old_login_import = !/\.\.\/lib\/login/.test(srcText);
checks.no_relative_grandparent_old_login_import = !/\.\.\/\.\.\/lib\/login/.test(srcText);
checks.no_literal_src_lib_login = !srcText.includes("src/lib/login");
checks.new_login_imports_present =
  srcText.includes("@/common/storage/login") &&
  read("src/components/layout/Header.tsx").includes("@/common/storage/login") &&
  read("src/components/login/LoginWorkspace.tsx").includes("@/common/storage/login") &&
  read("src/components/login/ui/RequireLogin.tsx").includes("@/common/storage/login") &&
  (read("src/common/api/axios.ts").includes("@/common/storage/login") ||
    read("src/lib/axios.ts").includes("@/common/storage/login"));
checks.axios_login_import_path_updated =
  !/from\s+["']\.\/login["']/.test(read("src/common/api/axios.ts") || read("src/lib/axios.ts")) &&
  (read("src/common/api/axios.ts").includes("@/common/storage/login") ||
    read("src/lib/axios.ts").includes("@/common/storage/login"));

const loginSrc = read(loginPath);
checks.login_exports_preserved =
  /export\s+type\s+StoredLogin\b/.test(loginSrc) &&
  /export\s+function\s+getStoredLogin\b/.test(loginSrc) &&
  /export\s+function\s+saveLogin\b/.test(loginSrc) &&
  /export\s+function\s+clearLogin\b/.test(loginSrc) &&
  /export\s+function\s+hasStoredLogin\b/.test(loginSrc);
checks.login_storage_key_preserved = loginSrc.includes('const STORAGE_KEY = "mysuit_ocr_login"');
checks.login_uses_localStorage_same_key =
  loginSrc.includes("window.localStorage.getItem(STORAGE_KEY)") &&
  loginSrc.includes("window.localStorage.setItem(") &&
  loginSrc.includes("window.localStorage.removeItem(STORAGE_KEY)");
checks.no_session_storage_key_added = !/sessionStorage/.test(loginSrc);
checks.no_api_endpoint_added = !/fetch\(|axios\.|api\//.test(loginSrc);
checks.no_components_import_in_login = !/from\s+["'][^"']*components\//.test(loginSrc);
checks.no_backend_fixture_template_groundtruth_import =
  !/from\s+["'][^"']*(backend|fixture|fixtures|templates|groundTruth|ground-truth)/i.test(loginSrc);
checks.no_react_import_in_login = !/from\s+["']react["']/.test(loginSrc);

checks.testworkspace_not_in_login_import_scope =
  !read("src/components/test/TestWorkspace.tsx").includes("@/common/storage/login") &&
  !read("src/components/test/TestWorkspace.tsx").includes("@/lib/login");
checks.test_core_not_in_login_import_scope =
  !srcFiles
    .filter((file) => file.startsWith("src/components/test/core/"))
    .some((file) => /(@\/common\/storage\/login|@\/lib\/login|\.\.\/lib\/login|\.\.\/\.\.\/lib\/login)/.test(read(file)));

checks.autorestore_folder_name_preserved = existsSync(rel("src/components/autorestore/AutoRestoreWorkspace.tsx"));
checks.autorestore_route_preserved = existsSync(rel("src/app/autorestore/page.tsx"));
checks.autorestore_workspace_name_preserved =
  read("src/components/autorestore/AutoRestoreWorkspace.tsx").includes("export default function AutoRestoreWorkspace");

const failures = Object.entries(checks).filter(([, ok]) => !ok);

console.log("LC-2 login storage move checks");
for (const [name, ok] of Object.entries(checks)) {
  console.log(`${ok ? "PASS" : "FAIL"} ${name}`);
}
console.log(`SUMMARY ${Object.keys(checks).length - failures.length}/${Object.keys(checks).length} PASS`);
console.log(`src/lib remaining: ${actualLibFiles.join(", ")}`);

if (failures.length > 0) {
  console.error("Failures:");
  for (const [name] of failures) console.error(`- ${name}`);
  process.exit(1);
}
