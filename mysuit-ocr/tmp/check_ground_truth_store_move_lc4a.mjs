import { existsSync, readdirSync, readFileSync } from "node:fs";
import { resolve } from "node:path";

const ROOT = process.cwd();
const rel = (p) => resolve(ROOT, p);
const read = (p) => (existsSync(rel(p)) ? readFileSync(rel(p), "utf8") : "");

const checks = {};

const targetPath = "src/common/storage/groundTruthStore.ts";
const oldPath = "src/lib/groundTruthStore.ts";

checks.target_exists = existsSync(rel(targetPath));
checks.source_absent = !existsSync(rel(oldPath));
checks.axios_api_exists = existsSync(rel("src/common/api/axios.ts"));
checks.old_axios_absent = !existsSync(rel("src/lib/axios.ts"));
checks.login_storage_exists = existsSync(rel("src/common/storage/login.ts"));
checks.old_login_absent = !existsSync(rel("src/lib/login.ts"));

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
checks.no_alias_old_ground_truth_import = !srcText.includes("@/lib/groundTruthStore");
checks.no_relative_parent_old_ground_truth_import = !/\.\.\/lib\/groundTruthStore/.test(srcText);
checks.no_relative_grandparent_old_ground_truth_import = !/\.\.\/\.\.\/lib\/groundTruthStore/.test(srcText);
checks.no_literal_src_lib_ground_truth = !srcText.includes("src/lib/groundTruthStore");
checks.new_imports_present =
  read("src/components/runocr/ui/OcrResultPanel.tsx").includes("@/common/storage/groundTruthStore") &&
  read("src/components/history/ui/DetailHistoryView.tsx").includes("@/common/storage/groundTruthStore");

const storeSrc = read(targetPath);
checks.exports_preserved =
  /export\s+type\s+GroundTruthMap\b/.test(storeSrc) &&
  /export\s+function\s+compositeKey\b/.test(storeSrc) &&
  /export\s+function\s+fieldKey\b/.test(storeSrc) &&
  /export\s+function\s+getGroundTruth\b/.test(storeSrc) &&
  /export\s+function\s+saveGroundTruth\b/.test(storeSrc) &&
  /export\s+function\s+clearGroundTruth\b/.test(storeSrc) &&
  /export\s+type\s+MatchStatus\b/.test(storeSrc) &&
  /export\s+function\s+compareToGt\b/.test(storeSrc);
checks.storage_key_preserved = storeSrc.includes('const STORAGE_KEY = "mysuit_ocr_groundtruth"');
checks.read_write_delete_logic_preserved =
  storeSrc.includes("window.localStorage.getItem(STORAGE_KEY)") &&
  storeSrc.includes("window.localStorage.setItem(STORAGE_KEY, JSON.stringify(store))") &&
  storeSrc.includes("delete store[compositeKey(template, file)]") &&
  storeSrc.includes("writeStore(store)");
checks.data_shape_preserved =
  /export\s+type\s+GroundTruthMap\s*=\s*Record<string,\s*string>/.test(storeSrc) &&
  /type\s+GroundTruthStore\s*=\s*Record<string,\s*GroundTruthMap>/.test(storeSrc);
checks.imports_history_store_common_storage =
  /from\s+["']@\/common\/storage\/historyStore["']/.test(storeSrc);
checks.no_old_self_reference =
  !storeSrc.includes("@/lib/groundTruthStore") &&
  !storeSrc.includes("src/lib/groundTruthStore");
checks.no_components_import =
  !/from\s+["'][^"']*components\//.test(storeSrc) &&
  !/from\s+["']@\/components\//.test(storeSrc);
checks.no_backend_import = !/from\s+["'][^"']*backend/i.test(storeSrc);
checks.no_fixture_template_ground_truth_data_import =
  !/from\s+["'][^"']*(fixture|fixtures|templates|public\/data|groundtruth\.json)/i.test(storeSrc);

checks.testworkspace_not_in_ground_truth_import_scope =
  !/(@\/common\/storage\/groundTruthStore|@\/lib\/groundTruthStore|\.\.\/lib\/groundTruthStore|\.\.\/\.\.\/lib\/groundTruthStore)/.test(
    read("src/components/test/TestWorkspace.tsx"),
  );
checks.test_core_not_in_ground_truth_import_scope =
  !srcFiles
    .filter((file) => file.startsWith("src/components/test/core/"))
    .some((file) =>
      /(@\/common\/storage\/groundTruthStore|@\/lib\/groundTruthStore|\.\.\/lib\/groundTruthStore|\.\.\/\.\.\/lib\/groundTruthStore)/.test(
        read(file),
      ),
    );

checks.autorestore_folder_name_preserved = existsSync(rel("src/components/autorestore/AutoRestoreWorkspace.tsx"));
checks.autorestore_route_preserved = existsSync(rel("src/app/autorestore/page.tsx"));
checks.autorestore_workspace_name_preserved =
  read("src/components/autorestore/AutoRestoreWorkspace.tsx").includes("export default function AutoRestoreWorkspace");

const failures = Object.entries(checks).filter(([, ok]) => !ok);

console.log("LC-4A groundTruthStore storage move checks");
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
