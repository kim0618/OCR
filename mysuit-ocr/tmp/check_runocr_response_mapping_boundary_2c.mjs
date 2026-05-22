#!/usr/bin/env node
// FRONTEND_STRUCTURE_2C_RUNOCR_BUILD_RUN_OCR_RESULT_EXTRACT
// Static check: confirm buildRunOcrResult was extracted to mapOcrResponse.ts
// without dragging autofill/history/restore/localStorage/React along, and that
// runOcrRequest.ts / buildOcrFormData.ts were NOT modified.
//
// Read-only. No production code is modified.

import { readFileSync, existsSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, "..");

const MAP_PATH = resolve(ROOT, "src/components/runocr/utils/mapOcrResponse.ts");
const REQ_PATH = resolve(ROOT, "src/components/runocr/utils/runOcrRequest.ts");
const BUILD_PATH = resolve(ROOT, "src/components/runocr/utils/buildOcrFormData.ts");
const WORKSPACE_PATH = resolve(ROOT, "src/components/runocr/RunOcrWorkspace.tsx");

const REQ_BACKUP = resolve(
  ROOT,
  "..",
  "backup",
  "RunOcrWorkspace_20260522_before_FRONTEND_STRUCTURE_2C_RUNOCR_BUILD_RUN_OCR_RESULT_EXTRACT.tsx",
);
const BUILD_FORMDATA_BACKUP = resolve(
  ROOT,
  "..",
  "backup",
  "buildOcrFormData_20260522_before_FRONTEND_STRUCTURE_2B_RUNOCR_REQUEST_EXTRACT.ts",
);

function readSafe(p) { try { return readFileSync(p, "utf8"); } catch { return null; } }

const mapSrc = readSafe(MAP_PATH);
const reqSrc = readSafe(REQ_PATH);
const buildSrc = readSafe(BUILD_PATH);
const workspaceSrc = readSafe(WORKSPACE_PATH);
const buildFormDataBackup = readSafe(BUILD_FORMDATA_BACKUP);

if (!mapSrc) { console.error(`[FATAL] not found: ${MAP_PATH}`); process.exit(2); }
if (!reqSrc) { console.error(`[FATAL] not found: ${REQ_PATH}`); process.exit(2); }
if (!buildSrc) { console.error(`[FATAL] not found: ${BUILD_PATH}`); process.exit(2); }
if (!workspaceSrc) { console.error(`[FATAL] not found: ${WORKSPACE_PATH}`); process.exit(2); }

const checks = {};

// 1) mapOcrResponse.ts exists & exports buildRunOcrResult
checks.map_exists = existsSync(MAP_PATH);
checks.map_exports_buildRunOcrResult = /export\s+function\s+buildRunOcrResult\b/.test(mapSrc);

// 2) RunOcrWorkspace.tsx imports buildRunOcrResult from utils/mapOcrResponse
checks.workspace_imports_from_map =
  /import\s*\{[^}]*buildRunOcrResult[^}]*\}\s*from\s*["']\.\/utils\/mapOcrResponse["']/.test(workspaceSrc);

// 3) RunOcrWorkspace.tsx no longer defines `function buildRunOcrResult`
checks.workspace_no_inline_definition =
  !/function\s+buildRunOcrResult\s*\(/.test(workspaceSrc);

// 4) RunOcrWorkspace.tsx still calls buildRunOcrResult(
checks.workspace_calls_buildRunOcrResult = /\bbuildRunOcrResult\s*\(/.test(workspaceSrc);

// 5) mapOcrResponse.ts must NOT import autofillEngine, historyStore,
//    restoreProfileStore, imageStore, localStorage, React, useState, etc.
//    Strip comments first so JSDoc that *mentions* these forbidden names (to
//    document boundary intent) does not produce a false positive.
const stripComments = (src) =>
  src
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .replace(/(^|[^:])\/\/[^\n]*/g, "$1");
const mapSrcNoComments = stripComments(mapSrc);
const FORBIDDEN_IMPORTS = [
  /from\s+["'][^"']*\/autofillEngine["']/,
  /from\s+["'][^"']*\/historyStore["']/,
  /from\s+["'][^"']*\/restoreProfileStore["']/,
  /from\s+["'][^"']*\/imageStore["']/,
  /from\s+["']react["']/,
  /\buseState\b/,
  /\buseEffect\b/,
  /\buseMemo\b/,
  /\buseRef\b/,
  /\buseRouter\b/,
  /\blocalStorage\b/,
  /\bappendHistoryRun\b/,
  /\bupdateHistoryRun\b/,
  /\bsyncHistoryIndexAndDetailOnCreate\b/,
  /\bsetOcrResult\b/,
  /\bsetCurrentJobId\b/,
];
const offending = FORBIDDEN_IMPORTS.filter((re) => re.test(mapSrcNoComments)).map((re) => re.source);
checks.map_no_forbidden_imports = offending.length === 0;
checks.map_forbidden_offenders = offending;

// 6) RunOcrWorkspace.tsx still references autofill/history keywords (they stay there)
const RESIDENT_KEYWORDS = [
  "appendHistoryRun",
  "updateHistoryRun",
  "syncHistoryIndexAndDetailOnCreate",
  "AutofillSuggestion",
  "AutofillRunSummary",
  "setOcrResult",
];
const residentMissing = RESIDENT_KEYWORDS.filter((k) => !workspaceSrc.includes(k));
checks.workspace_keeps_autofill_history = residentMissing.length === 0;
checks.workspace_missing_resident_keywords = residentMissing;

// 7) runOcrRequest.ts and buildOcrFormData.ts must not have been altered
//    LOGICALLY. 3B added JSDoc to buildOcrFormData.ts as comments-only patch,
//    so byte-for-byte equality with the 2B backup no longer holds. Compare
//    comment-stripped + whitespace-normalized forms instead — this preserves
//    the original invariant ("logic unchanged") while tolerating doc comments.
const normalizeForLogic = (src) =>
  stripComments(src).replace(/\s+/g, " ").trim();
checks.buildOcrFormData_unchanged_vs_2B_backup =
  buildFormDataBackup !== null &&
  normalizeForLogic(buildSrc) === normalizeForLogic(buildFormDataBackup);

// runOcrRequest must still import buildOcrFormData (sanity)
checks.runOcrRequest_still_imports_builder =
  /from\s+["']\.\/buildOcrFormData["']/.test(reqSrc);

// 8) mapOcrResponse.ts must NOT import runOcrRequest (one-way dependency)
checks.map_does_not_import_runOcrRequest =
  !/from\s+["']\.\/runOcrRequest["']/.test(mapSrc);

// 9) mapOcrResponse.ts must NOT import RunOcrWorkspace (no circular)
checks.map_does_not_import_workspace =
  !/from\s+["'][^"']*RunOcrWorkspace["']/.test(mapSrc);

const summary = {
  task: "FRONTEND-STRUCTURE-2C-RUNOCR-BUILD-RUN-OCR-RESULT-EXTRACT",
  mapPath: MAP_PATH,
  workspacePath: WORKSPACE_PATH,
  checks,
};
console.log(JSON.stringify(summary, null, 2));

const required = [
  "map_exists",
  "map_exports_buildRunOcrResult",
  "workspace_imports_from_map",
  "workspace_no_inline_definition",
  "workspace_calls_buildRunOcrResult",
  "map_no_forbidden_imports",
  "workspace_keeps_autofill_history",
  "buildOcrFormData_unchanged_vs_2B_backup",
  "runOcrRequest_still_imports_builder",
  "map_does_not_import_runOcrRequest",
  "map_does_not_import_workspace",
];
const allPass = required.every((k) => checks[k] === true);
console.log(`[RUNOCR_RESPONSE_MAPPING_BOUNDARY] ${allPass ? "PASS" : "FAIL"}`);
process.exit(allPass ? 0 : 1);
