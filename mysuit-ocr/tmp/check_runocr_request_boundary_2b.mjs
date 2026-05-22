#!/usr/bin/env node
// FRONTEND_STRUCTURE_2B_RUNOCR_REQUEST_EXTRACT
// Static check: confirm the OCR API request boundary lives in runOcrRequest.ts
// and the previously-inline fetch/ok/json sequence is gone from RunOcrWorkspace.tsx.
// Also confirm that response-shape concerns (mapping/history/autofill) did NOT
// leak into runOcrRequest.ts, and that downstream mapping (buildRunOcrResult)
// is still in RunOcrWorkspace.tsx.
//
// Read-only. No production code is modified.

import { readFileSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, "..");

const REQ_PATH = resolve(ROOT, "src/components/runocr/utils/runOcrRequest.ts");
const BUILD_PATH = resolve(ROOT, "src/components/runocr/utils/buildOcrFormData.ts");
const WORKSPACE_PATH = resolve(ROOT, "src/components/runocr/RunOcrWorkspace.tsx");

function readSafe(p) {
  try { return readFileSync(p, "utf8"); } catch { return null; }
}

const reqSrc = readSafe(REQ_PATH);
const buildSrc = readSafe(BUILD_PATH);
const workspaceSrc = readSafe(WORKSPACE_PATH);

if (!reqSrc) { console.error(`[FATAL] not found: ${REQ_PATH}`); process.exit(2); }
if (!buildSrc) { console.error(`[FATAL] not found: ${BUILD_PATH}`); process.exit(2); }
if (!workspaceSrc) { console.error(`[FATAL] not found: ${WORKSPACE_PATH}`); process.exit(2); }

const checks = {};

// 1) runOcrRequest.ts imports buildOcrFormData
checks.req_imports_buildOcrFormData =
  /import\s*\{[^}]*buildOcrFormData[^}]*\}\s*from\s*["']\.\/buildOcrFormData["']/.test(reqSrc);

// 2) runOcrRequest.ts contains fetch(
checks.req_has_fetch = /\bfetch\s*\(/.test(reqSrc);

// 3) runOcrRequest.ts contains !res.ok handling and "OCR 요청 실패" parity message
checks.req_has_not_ok = /!\s*res\.ok/.test(reqSrc);
checks.req_has_error_message = reqSrc.includes("OCR 요청 실패");

// 4) runOcrRequest.ts exports runOcrRequest
checks.req_exports_runOcrRequest = /export\s+async\s+function\s+runOcrRequest\b/.test(reqSrc);

// 5) RunOcrWorkspace.tsx no longer directly fetches the OCR endpoint
//    (we look for the prior inline pattern: fetch(ocrEndpoint, …) or
//     fetch on "/ocr/extract" / "/api/ocr-extract" anywhere in the file)
checks.workspace_no_direct_ocr_fetch =
  !/fetch\s*\(\s*ocrEndpoint/.test(workspaceSrc) &&
  !/fetch\s*\(\s*[`"'][^`"']*\/ocr\/extract/.test(workspaceSrc) &&
  !/fetch\s*\(\s*[`"']\/api\/ocr-extract/.test(workspaceSrc);

// 6) RunOcrWorkspace.tsx calls runOcrRequest(
checks.workspace_calls_runOcrRequest = /runOcrRequest\s*\(/.test(workspaceSrc);

// 7) RunOcrWorkspace.tsx no longer constructs `const ocrEndpoint =` for /ocr/extract
checks.workspace_no_ocrEndpoint_local =
  !/const\s+ocrEndpoint\s*=/.test(workspaceSrc);

// 8) Response mapping / history / autofill keywords MUST NOT leak into runOcrRequest.ts
//    Strip comments first so JSDoc that *mentions* these keywords (to explain
//    boundary intent) does not produce a false positive.
const stripComments = (src) =>
  src
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .replace(/(^|[^:])\/\/[^\n]*/g, "$1");
const reqSrcNoComments = stripComments(reqSrc);
const leakKeywords = [
  "buildRunOcrResult",
  "appendHistoryRun",
  "updateHistoryRun",
  "syncHistoryIndexAndDetailOnCreate",
  "AutofillSuggestion",
  "AutofillRunSummary",
  "collectInternalAutofillCandidates",
  "setOcrResult",
  "setCurrentJobId",
  "setCurrentCreatedAt",
  "raw_ocr_fields",
];
const leaks = leakKeywords.filter((k) => reqSrcNoComments.includes(k));
checks.req_no_mapping_history_autofill_leak = leaks.length === 0;
checks.req_leaked_keywords = leaks;

// 9) buildRunOcrResult must remain referenced in RunOcrWorkspace.tsx (mapping still there)
checks.workspace_keeps_buildRunOcrResult = /buildRunOcrResult\s*\(/.test(workspaceSrc);

// 10) buildOcrFormData.ts must not have been altered to depend on runOcrRequest
//     (compare against comment-stripped source — 3B added JSDoc).
const buildSrcNoComments = stripComments(buildSrc);
checks.build_does_not_import_request =
  !/from\s*["']\.\/runOcrRequest["']/.test(buildSrcNoComments);

// 11) Error message parity with prior inline behavior
checks.error_message_parity = checks.req_has_error_message;

const summary = {
  task: "FRONTEND-STRUCTURE-2B-RUNOCR-REQUEST-EXTRACT",
  reqPath: REQ_PATH,
  workspacePath: WORKSPACE_PATH,
  checks,
};
console.log(JSON.stringify(summary, null, 2));

const requiredTrue = [
  "req_imports_buildOcrFormData",
  "req_has_fetch",
  "req_has_not_ok",
  "req_has_error_message",
  "req_exports_runOcrRequest",
  "workspace_no_direct_ocr_fetch",
  "workspace_calls_runOcrRequest",
  "workspace_no_ocrEndpoint_local",
  "req_no_mapping_history_autofill_leak",
  "workspace_keeps_buildRunOcrResult",
  "build_does_not_import_request",
  "error_message_parity",
];
const allPass = requiredTrue.every((k) => checks[k] === true);
console.log(`[RUNOCR_REQUEST_BOUNDARY] ${allPass ? "PASS" : "FAIL"}`);
process.exit(allPass ? 0 : 1);
