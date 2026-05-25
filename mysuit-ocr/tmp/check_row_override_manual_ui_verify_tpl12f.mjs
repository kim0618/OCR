#!/usr/bin/env node
// TPL-12F-ROW-OVERRIDE-MANUAL-UI-VERIFY
// Source-marker runner. Confirms that the operational UI surface for the
// rowOverrides MVP is still wired exactly as TPL-12A/B/C/D left it, so the
// human-driven browser checklist in tmp/tpl_12f_row_override_manual_ui_verify.md
// can rely on the same wiring.
//
// This runner does NOT modify production code and does NOT drive the browser.
//
// Tag on success: [ROW_OVERRIDE_MANUAL_UI_VERIFY_TPL12F] PASS

import {
  readFileSync,
  existsSync,
  readdirSync,
  statSync,
} from "node:fs";
import { resolve, dirname, relative } from "node:path";
import { fileURLToPath } from "node:url";
import { execSync } from "node:child_process";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, "..");
const REPO_ROOT = resolve(ROOT, "..");
const TAG = "[ROW_OVERRIDE_MANUAL_UI_VERIFY_TPL12F]";

const failures = [];
function fail(msg) { failures.push(msg); console.error(`${TAG} FAIL ${msg}`); }
function note(msg) { console.log(`${TAG} NOTE ${msg}`); }
function ok(msg)   { console.log(`${TAG} OK ${msg}`); }
function readSafe(p) { try { return readFileSync(p, "utf8"); } catch { return null; } }
function walk(dir) {
  const out = [];
  const stack = [dir];
  while (stack.length) {
    const cur = stack.pop();
    let entries = [];
    try { entries = readdirSync(cur); } catch { continue; }
    for (const e of entries) {
      const p = resolve(cur, e);
      let st;
      try { st = statSync(p); } catch { continue; }
      if (st.isDirectory()) stack.push(p);
      else out.push(p);
    }
  }
  return out;
}
function stripComments(src) {
  return src.replace(/\/\*[\s\S]*?\*\//g, "").replace(/(^|[^:])\/\/[^\n]*/g, "$1");
}

// ---------------------------------------------------------------------------
// Paths
// ---------------------------------------------------------------------------
const VERIFY_MD = resolve(ROOT, "tmp/tpl_12f_row_override_manual_ui_verify.md");
const OCR_CANVAS_PANE = resolve(ROOT, "src/common/ui/OcrCanvasPane.tsx");
const TEMPLATE_ANNOTATOR = resolve(ROOT, "src/components/template/ui/TemplateAnnotator.tsx");
const TEMPLATE_RIGHT_PANEL = resolve(ROOT, "src/components/template/ui/TemplateRightPanel.tsx");
const PAYLOAD_BUILDER = resolve(ROOT, "src/components/template/utils/buildTemplateExportPayload.ts");
const TYPES_OCR = resolve(ROOT, "src/common/types/ocr.ts");
const TABLE_REGION = resolve(ROOT, "src/common/utils/ocrTableRegion.ts");
const BACKEND_MAIN = resolve(REPO_ROOT, "ocr-server/main.py");
const TEMPLATES_JSON = resolve(REPO_ROOT, "ocr-server/data/templates.json");

// ---------------------------------------------------------------------------
// 1. Manual verify markdown present + required scenarios
// ---------------------------------------------------------------------------
if (!existsSync(VERIFY_MD)) {
  fail(`verify markdown missing: ${relative(ROOT, VERIFY_MD)}`);
} else {
  ok(`verify markdown present`);
  const md = readSafe(VERIFY_MD) ?? "";
  for (const heading of [
    /^##\s+1\.\s+Summary/m,
    /^##\s+2\.\s+Environment/m,
    /^##\s+3\.\s+Manual Checklist/m,
    /^##\s+4\.\s+Findings/m,
    /^##\s+5\.\s+Automatic Verification/m,
    /^##\s+6\.\s+Final Decision/m,
  ]) {
    if (!heading.test(md)) fail(`verify markdown missing section: ${heading}`);
    else ok(`verify markdown section present: ${heading.source.replace(/[\\^$?+]|\\s\+/g, " ").trim()}`);
  }
  for (const tag of [
    "Template tab access",
    "table region select",
    "rowTemplate create",
    "row adjust toggle",
    "boundary handles visible",
    "drag row height",
    "reset all overrides",
    "save/reload",
    "existing features regression",
  ]) {
    if (!md.includes(tag)) fail(`verify markdown missing scenario row: ${tag}`);
    else ok(`verify markdown scenario row present: ${tag}`);
  }
}

// ---------------------------------------------------------------------------
// 2. TemplateAnnotator — rowAdjustTargetId state still wired
// ---------------------------------------------------------------------------
const annSrc = readSafe(TEMPLATE_ANNOTATOR) ?? "";
const annCode = stripComments(annSrc);
if (!/const\s+\[\s*rowAdjustTargetId\s*,\s*setRowAdjustTargetId\s*\]\s*=\s*useState/.test(annCode))
  fail(`TemplateAnnotator: rowAdjustTargetId useState missing`);
else ok(`TemplateAnnotator: rowAdjustTargetId useState present`);
if (!/<OcrCanvasPane[\s\S]{0,2000}rowAdjustTargetId\s*=\s*\{\s*rowAdjustTargetId\s*\}/.test(annCode))
  fail(`TemplateAnnotator does not forward rowAdjustTargetId to OcrCanvasPane`);
else ok(`TemplateAnnotator forwards rowAdjustTargetId to OcrCanvasPane`);
if (!/<TemplateRightPanel[\s\S]{0,2000}rowAdjustTargetId\s*=\s*\{\s*rowAdjustTargetId\s*\}/.test(annCode))
  fail(`TemplateAnnotator does not forward rowAdjustTargetId to TemplateRightPanel`);
else ok(`TemplateAnnotator forwards rowAdjustTargetId to TemplateRightPanel`);

// ---------------------------------------------------------------------------
// 3. TemplateRightPanel — toggle + count + reset + clearTableMeta integration
// ---------------------------------------------------------------------------
const trpSrc = readSafe(TEMPLATE_RIGHT_PANEL) ?? "";
const trpCode = stripComments(trpSrc);
if (!/행\s*개별\s*조정\s*시작|행\s*개별\s*조정\s*종료/.test(trpCode))
  fail(`TemplateRightPanel: "행 개별 조정 시작/종료" toggle label missing`);
else ok(`TemplateRightPanel: "행 개별 조정" toggle label present`);
if (!/모든\s*행\s*조정\s*초기화/.test(trpCode))
  fail(`TemplateRightPanel: "모든 행 조정 초기화" button missing`);
else ok(`TemplateRightPanel: "모든 행 조정 초기화" button present`);
if (!/조정된\s*행/.test(trpCode))
  fail(`TemplateRightPanel: rowOverrides count display missing`);
else ok(`TemplateRightPanel: rowOverrides count display present`);
if (!/function\s+clearRowOverrides\s*\(/.test(trpCode))
  fail(`TemplateRightPanel.clearRowOverrides helper missing`);
else ok(`clearRowOverrides helper present`);
if (!/function\s+clearTableMeta\b[\s\S]{0,800}rowOverrides\s*:\s*undefined/.test(trpCode))
  fail(`clearTableMeta does not reset rowOverrides`);
else ok(`clearTableMeta resets rowOverrides`);
if (!/setRowAdjustTargetId\s*\(\s*selected\.id\s*\)/.test(trpCode))
  fail(`rowAdjust toggle does not call setRowAdjustTargetId(selected.id)`);
else ok(`rowAdjust toggle sets target id`);

// ---------------------------------------------------------------------------
// 4. OcrCanvasPane — handle + drag + materialize usage
// ---------------------------------------------------------------------------
const canvasSrc = readSafe(OCR_CANVAS_PANE) ?? "";
const canvasCode = stripComments(canvasSrc);
if (!/data-role="row-boundary-handle"/.test(canvasCode))
  fail(`OcrCanvasPane: data-role="row-boundary-handle" marker missing`);
else ok(`OcrCanvasPane: row-boundary-handle marker present`);
if (!/isRowAdjustActive/.test(canvasCode))
  fail(`OcrCanvasPane: isRowAdjustActive guard missing`);
else ok(`OcrCanvasPane: isRowAdjustActive guard present`);
if (!/setRowBoundaryDragBoth/.test(canvasCode))
  fail(`OcrCanvasPane: setRowBoundaryDragBoth missing`);
else ok(`OcrCanvasPane: row-boundary drag plumbing present`);
if (!/applyRowBoundaryDragFrame/.test(canvasCode))
  fail(`OcrCanvasPane: applyRowBoundaryDragFrame helper missing`);
else ok(`OcrCanvasPane: applyRowBoundaryDragFrame helper present`);
if (!/rowOverrides\s*:\s*merged/.test(canvasCode))
  fail(`OcrCanvasPane: merged rowOverrides not committed`);
else ok(`OcrCanvasPane commits merged rowOverrides`);
if (!/materializeTableRowsWithOverrides/.test(canvasCode))
  fail(`OcrCanvasPane: materializeTableRowsWithOverrides not used`);
else ok(`OcrCanvasPane: materializeTableRowsWithOverrides used for displayRows`);
if (!/setDragBoth\s*\(\s*null\s*\)/.test(canvasCode))
  fail(`OcrCanvasPane: row-boundary handle does not clear the normal drag (mutually exclusive)`);
else ok(`OcrCanvasPane: row-boundary clears normal drag (mutually exclusive)`);

// Existing rowTemplate flow preserved
if (!/drawRowTemplate/.test(canvasCode))
  fail(`OcrCanvasPane lost drawRowTemplate flow`);
else ok(`OcrCanvasPane drawRowTemplate flow preserved`);

// ---------------------------------------------------------------------------
// 5. buildTemplateExportPayload — rowOverrides preserved + materialize used
// ---------------------------------------------------------------------------
const payloadSrc = readSafe(PAYLOAD_BUILDER) ?? "";
const payloadCode = stripComments(payloadSrc);
if (!/materializeTableRowsWithOverrides/.test(payloadCode))
  fail(`buildTemplateExportPayload no longer uses materialize helper`);
else ok(`buildTemplateExportPayload uses materialize helper`);
if (!/hasRowOverrides/.test(payloadCode))
  fail(`buildTemplateExportPayload missing hasRowOverrides legacy guard`);
else ok(`buildTemplateExportPayload hasRowOverrides legacy guard present`);
if (!/rowOverrides/.test(payloadCode))
  fail(`buildTemplateExportPayload does not handle rowOverrides`);
else ok(`buildTemplateExportPayload handles rowOverrides`);

// ---------------------------------------------------------------------------
// 6. types/ocr.ts + ocrTableRegion.ts wiring
// ---------------------------------------------------------------------------
const typesSrc = readSafe(TYPES_OCR) ?? "";
if (!/export\s+type\s+TableRowOverride\b/.test(typesSrc))
  fail(`TableRowOverride type missing`);
else ok(`TableRowOverride type present`);
if (!/rowOverrides\?\s*:\s*TableRowOverride\[\]/.test(typesSrc))
  fail(`TableMeta.rowOverrides?: TableRowOverride[] missing`);
else ok(`TableMeta.rowOverrides? present`);

const helperSrc = readSafe(TABLE_REGION) ?? "";
if (!/export\s+function\s+materializeTableRowsWithOverrides\b/.test(helperSrc))
  fail(`materializeTableRowsWithOverrides export missing`);
else ok(`materializeTableRowsWithOverrides export present`);
if (!/MIN_ROW_HEIGHT/.test(helperSrc))
  fail(`MIN_ROW_HEIGHT constant missing`);
else ok(`MIN_ROW_HEIGHT constant present`);

// ---------------------------------------------------------------------------
// 7. Backend contract preserved — main.py / templates.json untouched
// ---------------------------------------------------------------------------
if (existsSync(BACKEND_MAIN)) {
  const py = readSafe(BACKEND_MAIN) ?? "";
  if (/rowOverrides|rowAdjust/.test(py))
    fail(`ocr-server/main.py references rowOverrides/rowAdjust — backend contract changed`);
  else ok(`ocr-server/main.py: rowOverrides not consumed (backend contract preserved)`);
} else {
  note(`ocr-server/main.py not found — backend untouched check skipped`);
}
if (existsSync(TEMPLATES_JSON)) {
  if (/rowOverrides/.test(readSafe(TEMPLATES_JSON) ?? ""))
    note(`templates.json carries rowOverrides — expected after user-saved TPL-12 templates (phase-aware NOTE)`);
  else ok(`templates.json: no rowOverrides (fixture untouched)`);
}

// ---------------------------------------------------------------------------
// 8. src/lib absent + @/lib imports = 0
// ---------------------------------------------------------------------------
const SRC_LIB = resolve(ROOT, "src/lib");
if (existsSync(SRC_LIB)) {
  const f = walk(SRC_LIB);
  if (f.length > 0) fail(`src/lib must be absent or empty`);
  else ok(`src/lib present but empty`);
} else ok(`src/lib absent`);

const SRC_ROOT = resolve(ROOT, "src");
const allSrcFiles = walk(SRC_ROOT).filter((p) =>
  p.endsWith(".ts") || p.endsWith(".tsx") || p.endsWith(".mjs") || p.endsWith(".js")
);
const reLibAlias = /from\s+["']@\/lib(\/|["'])|import\(\s*["']@\/lib(\/|["'])/;
const reLibRelative = /from\s+["']\.\.\/lib(\/|["'])|from\s+["']\.\.\/\.\.\/lib(\/|["'])/;
let aliasHits = 0, relHits = 0;
for (const p of allSrcFiles) {
  const src = readSafe(p) ?? "";
  if (reLibAlias.test(src)) { aliasHits++; fail(`@/lib import in ${relative(ROOT, p)}`); }
  if (reLibRelative.test(src)) { relHits++; fail(`relative lib import in ${relative(ROOT, p)}`); }
}
if (aliasHits === 0) ok(`@/lib imports: 0`);
if (relHits === 0) ok(`relative lib imports: 0`);

// ---------------------------------------------------------------------------
// 9. New-file scope check (TPL-12F adds only verify md + this runner)
// ---------------------------------------------------------------------------
function gitStatusPorcelain() {
  try {
    return execSync("git status --porcelain", {
      cwd: REPO_ROOT, stdio: ["ignore", "pipe", "ignore"],
    }).toString("utf8").split(/\r?\n/).filter(Boolean);
  } catch { return null; }
}
const porcelain = gitStatusPorcelain();
if (porcelain == null) note(`git status unavailable — skipping new-file scope check`);
else {
  const FORBID_NEW = [
    /^mysuit-ocr\/src\/components\/test\//,
    /^mysuit-ocr\/src\/components\/runocr\//,
    /^mysuit-ocr\/src\/components\/template\//,
    /^mysuit-ocr\/src\/common\//,
    /^mysuit-ocr\/src\/app\//,
    /^mysuit-ocr\/public\/data\/testsets\//,
    /^ocr-server\//,
  ];
  const PHASE_ALLOW = new Set([
    "mysuit-ocr/src/components/template/utils/unstructuredDefinition.ts", // TPL-3
    "mysuit-ocr/src/components/runocr/utils/extractUnstructuredTableRows.ts", // TPL-8B
    "mysuit-ocr/src/common/utils/tableResultViewModel.ts", // TPL-8D
  ]);
  let hits = 0;
  for (const line of porcelain) {
    if (!line.startsWith("?? ")) continue;
    const path = line.slice(3).replace(/^"|"$/g, "");
    if (!FORBID_NEW.some((re) => re.test(path))) continue;
    if (PHASE_ALLOW.has(path)) { note(`new production (allowed from earlier phases): ${path}`); continue; }
    fail(`new untracked production file: ${path}`); hits++;
  }
  if (hits === 0) ok(`new-file scope check: clean`);
}

// ---------------------------------------------------------------------------
if (failures.length === 0) {
  console.log(`${TAG} PASS`);
  process.exit(0);
} else {
  console.error(`${TAG} FAIL count=${failures.length}`);
  for (const m of failures) console.error(`${TAG}   - ${m}`);
  process.exit(1);
}
