import { existsSync, readdirSync, readFileSync } from "node:fs";
import { resolve } from "node:path";

const ROOT = process.cwd();
const rel = (p) => resolve(ROOT, p);
const read = (p) => (existsSync(rel(p)) ? readFileSync(rel(p), "utf8") : "");

const checks = {};

const axiosPath = "src/common/api/axios.ts";
const oldAxiosPath = "src/lib/axios.ts";
const loginPath = "src/common/storage/login.ts";
const oldLoginPath = "src/lib/login.ts";

checks.target_exists = existsSync(rel(axiosPath));
checks.source_absent = !existsSync(rel(oldAxiosPath));
checks.login_storage_exists = existsSync(rel(loginPath));
checks.old_login_absent = !existsSync(rel(oldLoginPath));

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
  for (const ent of readdirSync(rel(dir), { withFileTypes: true })) {
    const p = `${dir}/${ent.name}`;
    if (ent.isDirectory()) {
      if (ent.name !== "node_modules") walk(p);
    } else if (/\.(ts|tsx|js|jsx|mjs)$/.test(ent.name)) {
      srcFiles.push(p);
    }
  }
}
walk("src");

const srcText = srcFiles.map((file) => `${file}\n${read(file)}`).join("\n");
checks.no_alias_old_axios_import = !srcText.includes("@/lib/axios");
checks.no_relative_parent_old_axios_import = !/\.\.\/lib\/axios/.test(srcText);
checks.no_relative_grandparent_old_axios_import = !/\.\.\/\.\.\/lib\/axios/.test(srcText);
checks.no_literal_src_lib_axios = !srcText.includes("src/lib/axios");
checks.new_axios_imports_present =
  read("src/components/history/HistoryWorkspace.tsx").includes("@/common/api/axios") &&
  read("src/components/login/LoginWorkspace.tsx").includes("@/common/api/axios");

const axiosSrc = read(axiosPath);
checks.axios_exports_preserved =
  /export\s+default\s+api\b/.test(axiosSrc) &&
  /export\s+\{\s*ApiResponseError\s*\}/.test(axiosSrc);
checks.axios_create_settings_preserved =
  /axios\.create\(\s*\{[\s\S]*baseURL:\s*["']\/api["'][\s\S]*timeout:\s*30000[\s\S]*withCredentials:\s*true[\s\S]*\}\s*\)/.test(axiosSrc);
checks.request_interceptor_preserved =
  /api\.interceptors\.request\.use/.test(axiosSrc) &&
  /getStoredLogin\(\)/.test(axiosSrc) &&
  /config\.headers\.Authorization\s*=/.test(axiosSrc) &&
  /gvLoginId/.test(axiosSrc) &&
  /user_id/.test(axiosSrc);
checks.response_interceptor_preserved =
  /api\.interceptors\.response\.use/.test(axiosSrc) &&
  /loginCode\s*===\s*["']9999["']/.test(axiosSrc) &&
  /ResultCode\s*===\s*["']Validation["']/.test(axiosSrc) &&
  /status\s*===\s*401/.test(axiosSrc) &&
  /clearLogin\(\)/.test(axiosSrc);
checks.login_import_updated =
  axiosSrc.includes("@/common/storage/login") &&
  !axiosSrc.includes("@/lib/login") &&
  !/from\s+["']\.\/login["']/.test(axiosSrc);
checks.no_self_old_axios_import =
  !axiosSrc.includes("@/lib/axios") &&
  !axiosSrc.includes("src/lib/axios");
checks.no_components_import_in_axios = !/from\s+["'][^"']*components\//.test(axiosSrc);
checks.no_backend_fixture_template_groundtruth_import =
  !/from\s+["'][^"']*(backend|fixture|fixtures|templates|groundTruth|ground-truth)/i.test(axiosSrc);

checks.testworkspace_not_in_axios_import_scope =
  !/(@\/common\/api\/axios|@\/lib\/axios|\.\.\/lib\/axios|\.\.\/\.\.\/lib\/axios)/.test(
    read("src/components/test/TestWorkspace.tsx"),
  );
checks.test_core_not_in_axios_import_scope =
  !srcFiles
    .filter((file) => file.startsWith("src/components/test/core/"))
    .some((file) => /(@\/common\/api\/axios|@\/lib\/axios|\.\.\/lib\/axios|\.\.\/\.\.\/lib\/axios)/.test(read(file)));

checks.autorestore_folder_name_preserved = existsSync(rel("src/components/autorestore/AutoRestoreWorkspace.tsx"));
checks.autorestore_route_preserved = existsSync(rel("src/app/autorestore/page.tsx"));
checks.autorestore_workspace_name_preserved =
  read("src/components/autorestore/AutoRestoreWorkspace.tsx").includes("export default function AutoRestoreWorkspace");

const failures = Object.entries(checks).filter(([, ok]) => !ok);

console.log("LC-3 axios api move checks");
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
