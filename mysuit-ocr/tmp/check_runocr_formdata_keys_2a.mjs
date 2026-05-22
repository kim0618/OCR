#!/usr/bin/env node
// FRONTEND_STRUCTURE_2A_RUNOCR_BUILD_OCR_FORMDATA_EXTRACT
// Static check: append key parity between (pre-extract) backup of RunOcrWorkspace
// and (post-extract) buildOcrFormData.ts. Also verifies the post-extract
// RunOcrWorkspace.tsx no longer carries the extracted block.
//
// Read-only. No production code is modified.

import { readFileSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, "..");

const BACKUP_PATH = resolve(
  ROOT,
  "..",
  "backup",
  "RunOcrWorkspace_20260522_before_FRONTEND_STRUCTURE_2A_RUNOCR_BUILD_OCR_FORMDATA_EXTRACT.tsx",
);
const UTIL_PATH = resolve(ROOT, "src/components/runocr/utils/buildOcrFormData.ts");
const WORKSPACE_PATH = resolve(ROOT, "src/components/runocr/RunOcrWorkspace.tsx");

function readSafe(p) {
  try {
    return readFileSync(p, "utf8");
  } catch (e) {
    return null;
  }
}

// Extract formData.append("KEY", ...) keys. Limited to the runOcr() main extract
// block — identified by the marker comment "코너 페이로드 비활성화" which sits
// directly after the block in both before and after states.
function appendKeysIn(source, blockMarker) {
  if (!source) return [];
  const markerIdx = source.indexOf(blockMarker);
  if (markerIdx < 0) return [];
  const segment = source.slice(0, markerIdx);
  // Walk backwards to the nearest "new FormData()" so we only capture the
  // immediate runOcr() composition (avoids picking up unrelated upload blocks).
  const ctorIdx = segment.lastIndexOf("new FormData()");
  const window = ctorIdx >= 0 ? segment.slice(ctorIdx) : segment;
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

if (!backupSrc) {
  console.error(`[FATAL] backup not found: ${BACKUP_PATH}`);
  process.exit(2);
}
if (!utilSrc) {
  console.error(`[FATAL] util not found: ${UTIL_PATH}`);
  process.exit(2);
}
if (!workspaceSrc) {
  console.error(`[FATAL] workspace not found: ${WORKSPACE_PATH}`);
  process.exit(2);
}

const MARKER = "코너 페이로드 비활성화";
const beforeKeys = appendKeysIn(backupSrc, MARKER);
const afterUtilKeys = appendKeysInUtil(utilSrc);

const sameOrder = JSON.stringify(beforeKeys) === JSON.stringify(afterUtilKeys);
const sameSet =
  beforeKeys.length === afterUtilKeys.length &&
  [...new Set(beforeKeys)].sort().join(",") === [...new Set(afterUtilKeys)].sort().join(",");

// Confirm the extracted block is no longer inline in the new workspace.
// We check: post-extract workspace must NOT contain `formData.append("template_id"`
// in the runOcr() vicinity. (Other FormData usages in revalidate/partial OCR
// are out of scope and use only `file` key — safe.)
const postRunOcrSegment = (() => {
  const idx = workspaceSrc.indexOf("async function runOcr()");
  if (idx < 0) return "";
  const end = workspaceSrc.indexOf(MARKER, idx);
  return end >= 0 ? workspaceSrc.slice(idx, end) : workspaceSrc.slice(idx, idx + 2000);
})();
const inlineRemoved =
  !/formData\.append\(\s*"template_id"/.test(postRunOcrSegment) &&
  !/formData\.append\(\s*"regions"/.test(postRunOcrSegment) &&
  !/formData\.append\(\s*"model_id"/.test(postRunOcrSegment) &&
  !/formData\.append\(\s*"documentType"/.test(postRunOcrSegment);

// After 2B: workspace may call buildOcrFormData indirectly via runOcrRequest.
// Either direct call or runOcrRequest invocation is acceptable for key parity.
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
  sameOrder,
  sameSet,
  inlineRemoved,
  callsBuilder,
};

console.log(JSON.stringify(summary, null, 2));

const allPass = sameOrder && sameSet && inlineRemoved && callsBuilder;
console.log(`[FORMDATA_KEY_PARITY] ${allPass ? "PASS" : "FAIL"}`);
process.exit(allPass ? 0 : 1);
