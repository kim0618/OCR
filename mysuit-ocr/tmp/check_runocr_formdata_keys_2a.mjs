#!/usr/bin/env node
// FRONTEND_STRUCTURE_2A_RUNOCR_BUILD_OCR_FORMDATA_EXTRACT
// Read-only static check. Historical backup comparison is strict when the
// backup exists, and SKIP_WITH_REASON when the old snapshot is unavailable.

import { readFileSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, "..");

const BACKUP_PATH = resolve(
  ROOT,
  "backup",
  "RunOcrWorkspace_20260522_before_FRONTEND_STRUCTURE_2A_RUNOCR_BUILD_OCR_FORMDATA_EXTRACT.tsx",
);
const UTIL_PATH = resolve(ROOT, "src/components/runocr/utils/buildOcrFormData.ts");
const WORKSPACE_PATH = resolve(ROOT, "src/components/runocr/RunOcrWorkspace.tsx");

function readSafe(p) {
  try {
    return readFileSync(p, "utf8");
  } catch {
    return null;
  }
}

function appendKeysIn(source) {
  if (!source) return [];
  const formDataIdx = source.lastIndexOf("new FormData()");
  const window = formDataIdx >= 0 ? source.slice(formDataIdx, formDataIdx + 5000) : source;
  const keys = [];
  const re = /formData\.append\(\s*"([^"]+)"/g;
  let m;
  while ((m = re.exec(window)) !== null) keys.push(m[1]);
  return keys;
}

function appendKeysInUtil(source) {
  if (!source) return [];
  const keys = [];
  const re = /formData\.append\(\s*"([^"]+)"/g;
  let m;
  while ((m = re.exec(source)) !== null) keys.push(m[1]);
  return keys;
}

const backupSrc = readSafe(BACKUP_PATH);
const utilSrc = readSafe(UTIL_PATH);
const workspaceSrc = readSafe(WORKSPACE_PATH);
const skippedBackupChecks = [];

if (!backupSrc) {
  skippedBackupChecks.push({
    check: "formdata_key_parity_vs_backup",
    reason: `SKIP_WITH_REASON: historical backup not found: ${BACKUP_PATH}`,
  });
}
if (!utilSrc) {
  console.error(`[FATAL] util not found: ${UTIL_PATH}`);
  process.exit(2);
}
if (!workspaceSrc) {
  console.error(`[FATAL] workspace not found: ${WORKSPACE_PATH}`);
  process.exit(2);
}

const beforeKeys = appendKeysIn(backupSrc);
const afterUtilKeys = appendKeysInUtil(utilSrc);
const backupComparisonAvailable = backupSrc !== null;

const sameOrder = backupComparisonAvailable
  ? JSON.stringify(beforeKeys) === JSON.stringify(afterUtilKeys)
  : true;
const sameSet = backupComparisonAvailable
  ? beforeKeys.length === afterUtilKeys.length &&
    [...new Set(beforeKeys)].sort().join(",") === [...new Set(afterUtilKeys)].sort().join(",")
  : true;

const postRunOcrSegment = (() => {
  const idx = workspaceSrc.indexOf("async function runOcr()");
  if (idx < 0) return "";
  return workspaceSrc.slice(idx, idx + 5000);
})();
const inlineRemoved =
  !/formData\.append\(\s*"template_id"/.test(postRunOcrSegment) &&
  !/formData\.append\(\s*"regions"/.test(postRunOcrSegment) &&
  !/formData\.append\(\s*"model_id"/.test(postRunOcrSegment) &&
  !/formData\.append\(\s*"documentType"/.test(postRunOcrSegment);

const callsBuilder =
  /buildOcrFormData\s*\(/.test(workspaceSrc) ||
  /runOcrRequest\s*\(/.test(workspaceSrc);

const summary = {
  task: "FRONTEND-STRUCTURE-2A-RUNOCR-BUILD-OCR-FORMDATA-EXTRACT",
  backupPath: BACKUP_PATH,
  utilPath: UTIL_PATH,
  workspacePath: WORKSPACE_PATH,
  beforeKeys,
  afterUtilKeys,
  skippedBackupChecks,
  sameOrder,
  sameSet,
  inlineRemoved,
  callsBuilder,
};

console.log(JSON.stringify(summary, null, 2));

const allPass = sameOrder && sameSet && inlineRemoved && callsBuilder;
const label = allPass && skippedBackupChecks.length > 0 ? "PASS_WITH_SKIPPED_BACKUP" : allPass ? "PASS" : "FAIL";
console.log(`[FORMDATA_KEY_PARITY] ${label}`);
process.exit(allPass ? 0 : 1);
