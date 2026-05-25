import { existsSync, readdirSync, readFileSync } from "node:fs";
import { resolve } from "node:path";

const ROOT = process.cwd();
const rel = (p) => resolve(ROOT, p);
const read = (p) => (existsSync(rel(p)) ? readFileSync(rel(p), "utf8") : "");

const checks = {};

const targetPath = "src/common/storage/restoreProfileStore.ts";
const oldPath = "src/lib/restoreProfileStore.ts";

checks.target_exists = existsSync(rel(targetPath));
checks.source_absent = !existsSync(rel(oldPath));
checks.axios_api_exists = existsSync(rel("src/common/api/axios.ts"));
checks.old_axios_absent = !existsSync(rel("src/lib/axios.ts"));
checks.login_storage_exists = existsSync(rel("src/common/storage/login.ts"));
checks.old_login_absent = !existsSync(rel("src/lib/login.ts"));
checks.ground_truth_storage_exists = existsSync(rel("src/common/storage/groundTruthStore.ts"));
checks.old_ground_truth_absent = !existsSync(rel("src/lib/groundTruthStore.ts"));

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
checks.no_alias_old_restore_profile_import = !srcText.includes("@/lib/restoreProfileStore");
checks.no_relative_parent_old_restore_profile_import = !/\.\.\/lib\/restoreProfileStore/.test(srcText);
checks.no_relative_grandparent_old_restore_profile_import = !/\.\.\/\.\.\/lib\/restoreProfileStore/.test(srcText);
checks.no_literal_src_lib_restore_profile = !srcText.includes("src/lib/restoreProfileStore");
// NOTE: After LIB-CLEAN-4F, autofillEngine lives at src/common/utils/.
// Resolve to whichever location currently exists.
const autofillCurrentRel =
  read("src/lib/autofillEngine.ts") !== ""
    ? "src/lib/autofillEngine.ts"
    : "src/common/utils/autofillEngine.ts";
const autofillCurrent = read(autofillCurrentRel);
checks.new_imports_present =
  read("src/components/autorestore/AutoRestoreWorkspace.tsx").includes("@/common/storage/restoreProfileStore") &&
  read("src/components/history/ui/DetailHistoryView.tsx").includes("@/common/storage/restoreProfileStore") &&
  autofillCurrent.includes("@/common/storage/restoreProfileStore");
checks.autofill_no_sibling_restore_profile_import =
  !/from\s+["']\.\/restoreProfileStore["']/.test(autofillCurrent) &&
  !/from\s+["']\.\.\/lib\/restoreProfileStore["']/.test(autofillCurrent);

const storeSrc = read(targetPath);
checks.exports_preserved =
  /export\s+const\s+RESTORE_PROFILE_STORAGE_KEY\b/.test(storeSrc) &&
  /export\s+type\s+RestoreProfileFields\b/.test(storeSrc) &&
  /export\s+type\s+RestoreProfile\b/.test(storeSrc) &&
  /export\s+const\s+AUTOFILL_TO_PROFILE_KEY\b/.test(storeSrc) &&
  /export\s+const\s+PROFILE_FIELD_LABELS\b/.test(storeSrc) &&
  /export\s+function\s+isMeaninglessValue\b/.test(storeSrc) &&
  /export\s+function\s+readRestoreProfiles\b/.test(storeSrc) &&
  /export\s+function\s+writeRestoreProfiles\b/.test(storeSrc) &&
  /export\s+function\s+deleteRestoreProfile\b/.test(storeSrc) &&
  /export\s+function\s+findRestoreProfile\b/.test(storeSrc) &&
  /export\s+function\s+sortRestoreProfilesByUpdatedAt\b/.test(storeSrc);
checks.storage_key_preserved =
  storeSrc.includes('export const RESTORE_PROFILE_STORAGE_KEY = "mysuit_ocr_restore_profiles"');
checks.read_write_delete_update_logic_preserved =
  storeSrc.includes("window.localStorage.getItem(RESTORE_PROFILE_STORAGE_KEY)") &&
  storeSrc.includes("window.localStorage.setItem(RESTORE_PROFILE_STORAGE_KEY, JSON.stringify(profiles))") &&
  storeSrc.includes("deleteRestoreProfile") &&
  storeSrc.includes("findRestoreProfile") &&
  storeSrc.includes("sortRestoreProfilesByUpdatedAt");
checks.data_shape_preserved =
  /businessNo:\s*string/.test(storeSrc) &&
  /partyType:\s*string/.test(storeSrc) &&
  /fields:\s*RestoreProfileFields/.test(storeSrc) &&
  /sourceHistoryId:\s*string/.test(storeSrc) &&
  /sourceFileName:\s*string/.test(storeSrc);
checks.no_old_self_reference =
  !storeSrc.includes("@/lib/restoreProfileStore") &&
  !storeSrc.includes("src/lib/restoreProfileStore");
checks.no_components_import =
  !/from\s+["'][^"']*components\//.test(storeSrc) &&
  !/from\s+["']@\/components\//.test(storeSrc);
checks.no_backend_import = !/from\s+["'][^"']*backend/i.test(storeSrc);
checks.no_fixture_template_ground_truth_data_import =
  !/from\s+["'][^"']*(fixture|fixtures|templates|public\/data|groundtruth\.json)/i.test(storeSrc);

checks.testworkspace_not_in_restore_profile_import_scope =
  !/(@\/common\/storage\/restoreProfileStore|@\/lib\/restoreProfileStore|\.\.\/lib\/restoreProfileStore|\.\.\/\.\.\/lib\/restoreProfileStore)/.test(
    read("src/components/test/TestWorkspace.tsx"),
  );
checks.test_core_not_in_restore_profile_import_scope =
  !srcFiles
    .filter((file) => file.startsWith("src/components/test/core/"))
    .some((file) =>
      /(@\/common\/storage\/restoreProfileStore|@\/lib\/restoreProfileStore|\.\.\/lib\/restoreProfileStore|\.\.\/\.\.\/lib\/restoreProfileStore)/.test(
        read(file),
      ),
    );

checks.autorestore_folder_name_preserved = existsSync(rel("src/components/autorestore/AutoRestoreWorkspace.tsx"));
checks.autorestore_route_preserved = existsSync(rel("src/app/autorestore/page.tsx"));
checks.autorestore_workspace_name_preserved =
  read("src/components/autorestore/AutoRestoreWorkspace.tsx").includes("export default function AutoRestoreWorkspace");

const failures = Object.entries(checks).filter(([, ok]) => !ok);

console.log("LC-4B restoreProfileStore storage move checks");
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
