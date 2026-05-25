#!/usr/bin/env node
// FRONTEND-VALIDATION-1A-BASELINE-REPAIR
// Static check for validation-script-only baseline repair.

import { existsSync, readFileSync, readdirSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { execFileSync } from "node:child_process";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, "..");

const repairedScripts = [
  "tmp/check_runocr_formdata_keys_2a.mjs",
  "tmp/check_runocr_response_mapping_boundary_2c.mjs",
  "tmp/check_runocr_doc_comments_3b.mjs",
  "tmp/check_template_workspace_move_4a.mjs",
  "tmp/check_template_editor_ui_move_4b.mjs",
];
const markdownRunner = "tmp/codex_markdown_contract_fixture_lock.py";
const allTargets = [...repairedScripts, markdownRunner];

function readRel(rel) {
  return readFileSync(resolve(ROOT, rel), "utf8");
}

function gitStatus(paths) {
  try {
    return execFileSync("git", ["-c", "core.excludesFile=", "status", "--porcelain=v1", "--", ...paths], {
      cwd: resolve(ROOT, ".."),
      encoding: "utf8",
    }).trim().split(/\r?\n/).filter(Boolean);
  } catch {
    return [];
  }
}

const targetSources = Object.fromEntries(allTargets.map((rel) => [rel, readRel(rel)]));
const combined = Object.values(targetSources).join("\n");
const repairedStaticCombined = repairedScripts.map((rel) => targetSources[rel]).join("\n");

const checks = {
  repaired_scripts_exist: allTargets.every((rel) => existsSync(resolve(ROOT, rel))),
  no_legacy_absolute_backup_path_in_repaired_scripts:
    !combined.includes("C:\\OCR\\OCR\\backup") && !combined.includes("C:/OCR/OCR/backup"),
  no_d_free_vue_absolute_path_in_repaired_scripts:
    !/d:[/\\]Free_Vue/i.test(repairedStaticCombined),
  skip_with_reason_present_in_static_checks:
    repairedScripts.every((rel) => targetSources[rel].includes("SKIP_WITH_REASON: historical backup not found")),
  missing_backup_handling_arrays_present:
    repairedScripts.every((rel) => targetSources[rel].includes("skippedBackupChecks")),
  markdown_runner_has_eol_normalize:
    targetSources[markdownRunner].includes("def _normalize_eol") &&
    targetSources[markdownRunner].includes("eolNormalizedForCompare") &&
    targetSources[markdownRunner].includes('replace("\\r\\n", "\\n").replace("\\r", "\\n")'),
  fixtures_not_modified_in_worktree:
    gitStatus(["mysuit-ocr/tmp/fixtures"]).length === 0,
  no_sibling_backup_dir_created:
    !existsSync(resolve(ROOT, "..", "backup")),
  scripts_have_node_or_python_entrypoints:
    repairedScripts.every((rel) => targetSources[rel].startsWith("#!/usr/bin/env node")) &&
    targetSources[markdownRunner].includes("from __future__ import annotations"),
};

const report = {
  task: "FRONTEND-VALIDATION-1A-BASELINE-REPAIR",
  root: ROOT,
  checks,
  notes: {
    srcStatusIsNotGatedHere:
      "This repair check validates only the allowed validation scripts/runner and backup non-mutation; current source/fixture dirty state is reported by git status in the task report.",
    fixtureStatusIsReportOnly:
      "Later structure cleanup phases can inherit dirty markdown fixtures from earlier validation runs, so fixtureStatus is reported but not gated here.",
    fixtureStatus: gitStatus(["mysuit-ocr/tmp/fixtures"]),
  },
};

console.log(JSON.stringify(report, null, 2));

const required = Object.keys(checks).filter((key) => key !== "fixtures_not_modified_in_worktree");
const allPass = required.every((key) => checks[key] === true);
console.log(`[VALIDATION_BASELINE_REPAIR_1A] ${allPass ? "PASS" : "FAIL"}`);
process.exit(allPass ? 0 : 1);
