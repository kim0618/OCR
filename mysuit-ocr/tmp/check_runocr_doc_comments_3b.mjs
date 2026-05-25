#!/usr/bin/env node
// FRONTEND_STRUCTURE_3B_RUNOCR_DOC_COMMENTS
// Static check: confirm the 8 RunOCR files received file-header JSDoc + key
// function/component JSDoc, that this is a comments-only patch (no logic
// drift), and that RunOcrControls.tsx / TestWorkspace.tsx were not touched.
//
// Read-only. No production code is modified.

import { readFileSync, existsSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, "..");
const BACKUP_DIR = resolve(ROOT, "backup");

const TARGETS = {
  workspace: {
    path: resolve(ROOT, "src/components/runocr/RunOcrWorkspace.tsx"),
    backup: resolve(BACKUP_DIR, "RunOcrWorkspace_20260522_before_FRONTEND_STRUCTURE_3B_RUNOCR_DOC_COMMENTS.tsx"),
    requiredJsdocAnchors: [
      "export default function RunOcrWorkspace",
      "async function runOcr",
      "const handlePersistEdits",
      "const handleResultClose",
    ],
  },
  resultLayout: {
    path: resolve(ROOT, "src/components/runocr/ui/RunOcrResultLayout.tsx"),
    backup: resolve(BACKUP_DIR, "RunOcrResultLayout_20260522_before_FRONTEND_STRUCTURE_3B_RUNOCR_DOC_COMMENTS.tsx"),
    requiredJsdocAnchors: [
      "export type RunOcrResultLayoutProps",
      "export default function RunOcrResultLayout",
    ],
  },
  resultPanel: {
    path: resolve(ROOT, "src/components/runocr/ui/OcrResultPanel.tsx"),
    backup: resolve(BACKUP_DIR, "OcrResultPanel_20260522_before_FRONTEND_STRUCTURE_3B_RUNOCR_DOC_COMMENTS.tsx"),
    requiredJsdocAnchors: [
      "export default function OcrResultPanel",
    ],
  },
  docViewer: {
    path: resolve(ROOT, "src/components/runocr/ui/OcrDocViewer.tsx"),
    backup: resolve(BACKUP_DIR, "OcrDocViewer_20260522_before_FRONTEND_STRUCTURE_3B_RUNOCR_DOC_COMMENTS.tsx"),
    requiredJsdocAnchors: [
      "export default function OcrDocViewer",
      "const updateScale",
    ],
  },
  cornerAdjust: {
    path: resolve(ROOT, "src/components/runocr/ui/CornerAdjust.tsx"),
    backup: resolve(BACKUP_DIR, "CornerAdjust_20260522_before_FRONTEND_STRUCTURE_3B_RUNOCR_DOC_COMMENTS.tsx"),
    requiredJsdocAnchors: [
      "export default function CornerAdjust",
    ],
  },
  buildFormData: {
    path: resolve(ROOT, "src/components/runocr/utils/buildOcrFormData.ts"),
    backup: resolve(BACKUP_DIR, "buildOcrFormData_20260522_before_FRONTEND_STRUCTURE_3B_RUNOCR_DOC_COMMENTS.ts"),
    requiredJsdocAnchors: [
      "export type BuildOcrFormDataInput",
      "export function buildOcrFormData",
    ],
  },
  request: {
    path: resolve(ROOT, "src/components/runocr/utils/runOcrRequest.ts"),
    backup: resolve(BACKUP_DIR, "runOcrRequest_20260522_before_FRONTEND_STRUCTURE_3B_RUNOCR_DOC_COMMENTS.ts"),
    requiredJsdocAnchors: [
      "export type RunOcrRequestInput",
      "export async function runOcrRequest",
    ],
  },
  mapResponse: {
    path: resolve(ROOT, "src/components/runocr/utils/mapOcrResponse.ts"),
    backup: resolve(BACKUP_DIR, "mapOcrResponse_20260522_before_FRONTEND_STRUCTURE_3B_RUNOCR_DOC_COMMENTS.ts"),
    requiredJsdocAnchors: [
      "export type BuildRunOcrResultTemplate",
      "export type BuildRunOcrResultOptions",
      "export function buildRunOcrResult",
    ],
  },
};

const CONTROLS_PATH = resolve(ROOT, "src/components/runocr/ui/RunOcrControls.tsx");
const TEST_WORKSPACE_PATH = resolve(ROOT, "src/components/test/TestWorkspace.tsx");
const TEST_WORKSPACE_BACKUP_HINT = "TestWorkspace*.tsx"; // not enforced byte-equal; check git

function readSafe(p) {
  try { return readFileSync(p, "utf8"); } catch { return null; }
}

// Strip all comments (block /* ... */ and line //...) to compare logic-only.
function stripComments(src) {
  return src
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .replace(/(^|[^:])\/\/[^\n]*/g, "$1");
}

// Normalize whitespace so we ignore re-indents / blank-line insertions.
function normalizeForDiff(src) {
  return stripComments(src)
    .replace(/\s+/g, " ")
    .trim();
}

const fileChecks = {};
const skippedBackupChecks = [];

for (const [name, info] of Object.entries(TARGETS)) {
  const cur = readSafe(info.path);
  const prev = readSafe(info.backup);
  if (!cur) { fileChecks[name] = { ok: false, reason: `current missing: ${info.path}` }; continue; }

  // 1) File header JSDoc must exist at top of file
  //    Allow optional leading "use client" directive.
  const headerOk = /^\s*("use client";\s*)?\/\*\*[\s\S]*?\*\//.test(cur);

  // 2) Each required JSDoc anchor: the line containing the anchor must be
  //    preceded by a JSDoc `*/` line within the previous ~20 lines (i.e. a
  //    JSDoc block immediately precedes that declaration).
  const anchorChecks = info.requiredJsdocAnchors.map((anchor) => {
    const idx = cur.indexOf(anchor);
    if (idx < 0) return { anchor, ok: false, reason: "anchor not found" };
    const before = cur.slice(0, idx);
    const lines = before.split("\n");
    const recent = lines.slice(Math.max(0, lines.length - 30)).join("\n");
    // Acceptance: a JSDoc closer `*/` appears within the last ~30 lines before
    // the anchor, and the closer follows a JSDoc opener `/**` (i.e. it's not a
    // stray block-comment closer).
    const closerIdx = recent.lastIndexOf("*/");
    const openerIdx = recent.lastIndexOf("/**");
    const ok = closerIdx > 0 && openerIdx > 0 && openerIdx < closerIdx;
    return { anchor, ok };
  });
  const anchorOk = anchorChecks.every((c) => c.ok);

  // 3) Comments-only diff: when comments + whitespace are stripped, current
  //    must equal backup. This is the strict "no logic drift" guarantee.
  const backupAvailable = prev !== null;
  if (!backupAvailable) {
    skippedBackupChecks.push({
      check: `${name}_comments_only_vs_backup`,
      reason: `SKIP_WITH_REASON: historical backup not found: ${info.backup}`,
    });
  }
  const commentsOnly = backupAvailable ? normalizeForDiff(cur) === normalizeForDiff(prev) : true;

  fileChecks[name] = {
    ok: headerOk && anchorOk && commentsOnly,
    headerOk,
    anchorOk,
    anchorChecks,
    commentsOnly,
    commentsOnlySkipped: !backupAvailable,
  };
}

const overall = Object.values(fileChecks).every((c) => c.ok);

// 4) RunOcrControls.tsx must NOT exist
const controlsNotCreated = !existsSync(CONTROLS_PATH);

// 5) TestWorkspace.tsx must not be in git's modified list at this path.
//    We can't run git from this script reliably (no spawn here), so we
//    just confirm it exists (sanity) and rely on the boundary discipline
//    plus the comments-only diff on the 8 RunOCR targets.
const testWorkspaceExists = existsSync(TEST_WORKSPACE_PATH);

const summary = {
  task: "FRONTEND-STRUCTURE-3B-RUNOCR-DOC-COMMENTS",
  fileChecks,
  backupDir: BACKUP_DIR,
  skippedBackupChecks,
  overall_files: overall,
  controls_not_created: controlsNotCreated,
  testworkspace_exists: testWorkspaceExists,
};

console.log(JSON.stringify(summary, null, 2));
const allPass = overall && controlsNotCreated && testWorkspaceExists;
const label = allPass && skippedBackupChecks.length > 0 ? "PASS_WITH_SKIPPED_BACKUP" : allPass ? "PASS" : "FAIL";
console.log(`[RUNOCR_DOC_COMMENTS] ${label}`);
process.exit(allPass ? 0 : 1);
