#!/usr/bin/env node
// TPL-12C-ROW-OVERRIDE-CANVAS-UI
// Static check. Verifies the row-adjust UI plumbing across TemplateAnnotator,
// TemplateRightPanel and OcrCanvasPane — without modifying types, helper,
// payload builder, or backend.
//
// Tag on success: [ROW_OVERRIDE_CANVAS_UI_TPL12C] PASS

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
const TAG = "[ROW_OVERRIDE_CANVAS_UI_TPL12C]";

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
const OCR_CANVAS_PANE = resolve(ROOT, "src/common/ui/OcrCanvasPane.tsx");
const TEMPLATE_ANNOTATOR = resolve(ROOT, "src/components/template/ui/TemplateAnnotator.tsx");
const TEMPLATE_RIGHT_PANEL = resolve(ROOT, "src/components/template/ui/TemplateRightPanel.tsx");
const PAYLOAD_BUILDER = resolve(ROOT, "src/components/template/utils/buildTemplateExportPayload.ts");
const TYPES_OCR = resolve(ROOT, "src/common/types/ocr.ts");
const TABLE_REGION = resolve(ROOT, "src/common/utils/ocrTableRegion.ts");
const OCR_CANVAS_OPS = resolve(ROOT, "src/common/utils/ocrCanvasOps.ts");
const VIEWMODEL_HELPER = resolve(ROOT, "src/common/utils/tableResultViewModel.ts");
const OCR_RESULT_PANEL = resolve(ROOT, "src/components/runocr/ui/OcrResultPanel.tsx");
const RUNOCR_WORKSPACE = resolve(ROOT, "src/components/runocr/RunOcrWorkspace.tsx");
const CLEAN_JSON = resolve(ROOT, "src/common/utils/cleanJsonBuilder.ts");
const MARKDOWN_REPORT = resolve(ROOT, "src/common/utils/markdownReportBuilder.ts");
const UNSTRUCTURED_BUILDER = resolve(ROOT, "src/components/template/UnstructuredBuilder.tsx");
const UNSTRUCTURED_DEF = resolve(ROOT, "src/components/template/utils/unstructuredDefinition.ts");
const TEST_WORKSPACE = resolve(ROOT, "src/components/test/TestWorkspace.tsx");
const BACKEND_MAIN = resolve(REPO_ROOT, "ocr-server/main.py");
const TEMPLATES_JSON = resolve(REPO_ROOT, "ocr-server/data/templates.json");

// ---------------------------------------------------------------------------
// 1. TemplateAnnotator — rowAdjustTargetId state + props forwarded
// ---------------------------------------------------------------------------
const annSrc = readSafe(TEMPLATE_ANNOTATOR) ?? "";
const annCode = stripComments(annSrc);

if (!/const\s+\[\s*rowAdjustTargetId\s*,\s*setRowAdjustTargetId\s*\]\s*=\s*useState/.test(annCode))
  fail(`TemplateAnnotator: rowAdjustTargetId useState missing`);
else ok(`TemplateAnnotator: rowAdjustTargetId useState present`);

// Forwarded to BOTH children
if (!/<OcrCanvasPane[\s\S]{0,1500}rowAdjustTargetId\s*=\s*\{\s*rowAdjustTargetId\s*\}[\s\S]{0,400}setRowAdjustTargetId\s*=\s*\{\s*setRowAdjustTargetId\s*\}/.test(annCode))
  fail(`TemplateAnnotator: rowAdjustTargetId not forwarded to OcrCanvasPane`);
else ok(`TemplateAnnotator forwards rowAdjustTargetId/setRowAdjustTargetId to OcrCanvasPane`);

if (!/<TemplateRightPanel[\s\S]{0,1500}rowAdjustTargetId\s*=\s*\{\s*rowAdjustTargetId\s*\}[\s\S]{0,400}setRowAdjustTargetId\s*=\s*\{\s*setRowAdjustTargetId\s*\}/.test(annCode))
  fail(`TemplateAnnotator: rowAdjustTargetId not forwarded to TemplateRightPanel`);
else ok(`TemplateAnnotator forwards rowAdjustTargetId/setRowAdjustTargetId to TemplateRightPanel`);

// resetForm / file upload / template load all reset the new state
const resetTouchCount = (annCode.match(/setRowAdjustTargetId\s*\(\s*null\s*\)/g) ?? []).length;
if (resetTouchCount < 3)
  fail(`TemplateAnnotator: setRowAdjustTargetId(null) reset sites < 3 (saw ${resetTouchCount})`);
else ok(`TemplateAnnotator: setRowAdjustTargetId(null) called in ${resetTouchCount} reset paths`);

// ---------------------------------------------------------------------------
// 2. TemplateRightPanel — toggle button + reset + clearTableMeta integration
// ---------------------------------------------------------------------------
const trpSrc = readSafe(TEMPLATE_RIGHT_PANEL) ?? "";
const trpCode = stripComments(trpSrc);

if (!/rowAdjustTargetId\s*:\s*string\s*\|\s*null/.test(trpCode))
  fail(`TemplateRightPanel: rowAdjustTargetId prop type missing`);
else ok(`TemplateRightPanel: rowAdjustTargetId prop typed`);
if (!/setRowAdjustTargetId\s*:\s*React\.Dispatch/.test(trpCode))
  fail(`TemplateRightPanel: setRowAdjustTargetId setter prop type missing`);
else ok(`TemplateRightPanel: setRowAdjustTargetId setter prop typed`);

// UI markers
if (!/행\s*개별\s*조정\s*시작|행\s*개별\s*조정\s*종료/.test(trpCode))
  fail(`TemplateRightPanel: "행 개별 조정 시작/종료" toggle label missing`);
else ok(`TemplateRightPanel: "행 개별 조정" toggle label present`);
if (!/모든\s*행\s*조정\s*초기화/.test(trpCode))
  fail(`TemplateRightPanel: "모든 행 조정 초기화" button missing`);
else ok(`TemplateRightPanel: "모든 행 조정 초기화" button present`);
if (!/조정된\s*행/.test(trpCode))
  fail(`TemplateRightPanel: "조정된 행 N개" count display missing`);
else ok(`TemplateRightPanel: rowOverrides count display present`);

// clearTableMeta must also clear rowOverrides
if (!/function\s+clearTableMeta\b[\s\S]{0,800}rowOverrides\s*:\s*undefined/.test(trpCode))
  fail(`TemplateRightPanel.clearTableMeta does not reset rowOverrides`);
else ok(`clearTableMeta resets rowOverrides`);

// clearRowOverrides helper exists
if (!/function\s+clearRowOverrides\s*\(/.test(trpCode))
  fail(`TemplateRightPanel.clearRowOverrides helper missing`);
else ok(`clearRowOverrides helper present`);

// setTableMode "auto" branch also clears rowOverrides
if (!/function\s+setTableMode\b[\s\S]{0,800}rowOverrides\s*:\s*undefined/.test(trpCode))
  fail(`TemplateRightPanel.setTableMode("auto") does not clear rowOverrides`);
else ok(`setTableMode("auto") clears rowOverrides`);

// mutually exclusive switches: 행 템플릿 지정 / 세로 가이드 / 행 개별 조정
if (!/setRowTemplateTargetId\s*\(\s*selected\.id\s*\)[\s\S]{0,200}setRowAdjustTargetId\s*\(\s*null\s*\)|setRowAdjustTargetId\s*\(\s*null\s*\)[\s\S]{0,200}setRowTemplateTargetId\s*\(\s*selected\.id/.test(trpCode))
  fail(`TemplateRightPanel: 행 템플릿 지정 button does not clear rowAdjustTargetId`);
else ok(`행 템플릿 지정 ↔ rowAdjust mutually exclusive`);

if (!/setRowAdjustTargetId\s*\(\s*selected\.id\s*\)/.test(trpCode))
  fail(`TemplateRightPanel: rowAdjust toggle does not call setRowAdjustTargetId(selected.id)`);
else ok(`rowAdjust toggle sets target id`);

// ---------------------------------------------------------------------------
// 3. OcrCanvasPane — prop, materialize import, handle, drag, upsert
// ---------------------------------------------------------------------------
const canvasSrc = readSafe(OCR_CANVAS_PANE) ?? "";
const canvasCode = stripComments(canvasSrc);

if (!/rowAdjustTargetId\?\s*:\s*string\s*\|\s*null/.test(canvasCode))
  fail(`OcrCanvasPane: rowAdjustTargetId?: string | null prop type missing`);
else ok(`OcrCanvasPane: rowAdjustTargetId prop typed`);

if (!/materializeTableRowsWithOverrides/.test(canvasCode))
  fail(`OcrCanvasPane does not import / use materializeTableRowsWithOverrides`);
else ok(`OcrCanvasPane references materializeTableRowsWithOverrides`);

if (!/MIN_ROW_HEIGHT/.test(canvasCode))
  fail(`OcrCanvasPane does not import MIN_ROW_HEIGHT`);
else ok(`OcrCanvasPane references MIN_ROW_HEIGHT`);

if (!/TableRowOverride/.test(canvasCode))
  fail(`OcrCanvasPane does not import TableRowOverride type`);
else ok(`OcrCanvasPane references TableRowOverride type`);

// row boundary handle marker
if (!/row-boundary-handle/.test(canvasCode))
  fail(`OcrCanvasPane: row-boundary-handle data-role missing`);
else ok(`OcrCanvasPane: row-boundary-handle marker present`);
if (!/isRowAdjustActive/.test(canvasCode))
  fail(`OcrCanvasPane: isRowAdjustActive guard missing`);
else ok(`OcrCanvasPane: isRowAdjustActive guard present`);

// upsert logic markers
if (!/rowBoundaryDrag/.test(canvasCode))
  fail(`OcrCanvasPane: rowBoundaryDrag state missing`);
else ok(`OcrCanvasPane: rowBoundaryDrag state present`);
if (!/applyRowBoundaryDragFrame/.test(canvasCode))
  fail(`OcrCanvasPane: applyRowBoundaryDragFrame helper missing`);
else ok(`OcrCanvasPane: applyRowBoundaryDragFrame helper present`);
if (!/rowOverrides\s*:\s*merged/.test(canvasCode))
  fail(`OcrCanvasPane: merged rowOverrides not committed via setRegions`);
else ok(`OcrCanvasPane commits merged rowOverrides`);

// mutual exclusivity: rowBoundary drag clears the normal DragKind
if (!/setDragBoth\s*\(\s*null\s*\)/.test(canvasCode))
  fail(`OcrCanvasPane: row-boundary handle does not clear the normal drag`);
else ok(`OcrCanvasPane: row-boundary clears normal drag (mutually exclusive)`);

// pointerMove routes through rowBoundaryDragRef.current when set
if (!/rowBoundaryDragRef\.current[\s\S]{0,200}applyRowBoundaryDragFrame/.test(canvasCode))
  fail(`OcrCanvasPane: pointerMove does not branch on rowBoundaryDragRef.current`);
else ok(`OcrCanvasPane pointerMove branches on rowBoundaryDragRef`);

// Existing rowTemplate draw flow preserved
if (!/drawRowTemplate/.test(canvasCode))
  fail(`OcrCanvasPane lost drawRowTemplate flow (regression)`);
else ok(`OcrCanvasPane drawRowTemplate flow preserved`);
if (!/rowTemplateTargetId/.test(canvasCode))
  fail(`OcrCanvasPane lost rowTemplateTargetId support`);
else ok(`OcrCanvasPane rowTemplateTargetId support preserved`);

// ---------------------------------------------------------------------------
// 4. Untouched files — must NOT carry rowAdjust / rowBoundary symbols
//    (TPL-12A/12B allow-list for rowOverrides/TableRowOverride/materialize
//     remains intact: types/ocr.ts, ocrTableRegion.ts, buildTemplateExportPayload.ts)
// ---------------------------------------------------------------------------
const TPL12_ROW_OVERRIDE_ALLOW = new Set([
  TYPES_OCR,
  TABLE_REGION,
  PAYLOAD_BUILDER,
  OCR_CANVAS_PANE,        // TPL-12C
  TEMPLATE_ANNOTATOR,     // TPL-12C
  TEMPLATE_RIGHT_PANEL,   // TPL-12C
]);
for (const [label, p] of [
  ["ocrCanvasOps.ts", OCR_CANVAS_OPS],
  ["tableResultViewModel.ts", VIEWMODEL_HELPER],
  ["OcrResultPanel.tsx", OCR_RESULT_PANEL],
  ["RunOcrWorkspace.tsx", RUNOCR_WORKSPACE],
  ["cleanJsonBuilder.ts", CLEAN_JSON],
  ["markdownReportBuilder.ts", MARKDOWN_REPORT],
  ["UnstructuredBuilder.tsx", UNSTRUCTURED_BUILDER],
  ["unstructuredDefinition.ts", UNSTRUCTURED_DEF],
]) {
  const codeOnly = stripComments(readSafe(p) ?? "");
  if (/rowOverrides|materializeTableRowsWithOverrides|TableRowOverride|rowAdjustTargetId|rowBoundary/.test(codeOnly))
    fail(`${label} references rowOverride / rowAdjust / rowBoundary symbols (out of scope)`);
  else ok(`${label}: no rowOverride / rowAdjust symbols (out of scope)`);
}

// Files that ARE allow-listed for rowOverrides but MUST NOT carry rowAdjust /
// rowBoundary UI symbols (those belong only to TPL-12C UI surface).
for (const [label, p] of [
  ["types/ocr.ts", TYPES_OCR],
  ["ocrTableRegion.ts", TABLE_REGION],
  ["buildTemplateExportPayload.ts", PAYLOAD_BUILDER],
]) {
  const codeOnly = stripComments(readSafe(p) ?? "");
  if (/rowAdjustTargetId|rowBoundary|행 개별 조정/.test(codeOnly))
    fail(`${label} contains TPL-12C UI symbols (must be UI-only)`);
  else ok(`${label}: no TPL-12C UI symbols (correctly UI-free)`);
}

// Backend / templates.json: still no rowOverrides
if (existsSync(BACKEND_MAIN)) {
  const py = readSafe(BACKEND_MAIN) ?? "";
  if (/rowOverrides|rowAdjust/.test(py))
    fail(`ocr-server/main.py references rowOverrides/rowAdjust — backend contract change forbidden`);
  else ok(`ocr-server/main.py: no rowOverrides/rowAdjust (backend untouched)`);
}
if (existsSync(TEMPLATES_JSON)) {
  if (/rowOverrides|rowAdjust/.test(readSafe(TEMPLATES_JSON) ?? ""))
    note(`templates.json carries rowOverrides — expected after user-saved TPL-12 templates (phase-aware NOTE)`);
  else ok(`templates.json: no rowOverrides (fixture untouched)`);
}

// TestWorkspace untouched
if (existsSync(TEST_WORKSPACE)) {
  const tw = stripComments(readSafe(TEST_WORKSPACE) ?? "");
  if (/rowOverrides|rowAdjust|materializeTableRowsWithOverrides/.test(tw))
    fail(`TestWorkspace.tsx carries rowOverrides/rowAdjust symbols (forbidden)`);
  else ok(`TestWorkspace.tsx: no rowOverrides/rowAdjust symbols`);
}

// ---------------------------------------------------------------------------
// 5. src/lib absent + @/lib imports = 0
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
// 6. New-file scope check
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
