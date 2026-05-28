#!/usr/bin/env node
// TPL-14A-UNSTRUCTURED-DEFINITION-SELECTION-DELETE-UX
// 비정형 생성 UI(UnstructuredBuilder)에서 일반 영역/테이블/컬럼 삭제 UX를
// 선택 기반 단일 진입점으로 통일했는지 정적으로 검증한다.
// Tag on success: [UNSTRUCTURED_SELECTION_DELETE_UX_TPL14A] PASS
//
// 모든 검증은 read-only. UnstructuredBuilder.tsx만 변경되어야 하며 RunOCR /
// table viewmodel / export builder / TemplateRightPanel / OcrCanvasPane /
// TemplateAnnotator / backend / public data / src/lib 영역은 손대지 않은
// 상태여야 한다.

import {
  readFileSync,
  existsSync,
  readdirSync,
  statSync,
} from "node:fs";
import { resolve, dirname, relative } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, "..");
const TAG = "[UNSTRUCTURED_SELECTION_DELETE_UX_TPL14A]";

const failures = [];
function fail(msg) { failures.push(msg); console.error(`${TAG} FAIL ${msg}`); }
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
const BUILDER_PATH = resolve(ROOT, "src/components/template/UnstructuredBuilder.tsx");
const HELPER_PATH = resolve(ROOT, "src/components/template/utils/unstructuredDefinition.ts");
const TEMPLATE_RIGHT_PANEL = resolve(ROOT, "src/components/template/ui/TemplateRightPanel.tsx");
const TEMPLATE_ANNOTATOR = resolve(ROOT, "src/components/template/ui/TemplateAnnotator.tsx");
const OCR_CANVAS_PANE = resolve(ROOT, "src/common/ui/OcrCanvasPane.tsx");
const TABLE_RESULT_VM = resolve(ROOT, "src/common/utils/tableResultViewModel.ts");
const CLEAN_JSON_BUILDER = resolve(ROOT, "src/common/utils/cleanJsonBuilder.ts");
const MARKDOWN_REPORT_BUILDER = resolve(ROOT, "src/common/utils/markdownReportBuilder.ts");
const MAP_OCR_RESPONSE = resolve(ROOT, "src/components/runocr/utils/mapOcrResponse.ts");
const EXTRACT_UNSTRUCTURED = resolve(ROOT, "src/components/runocr/utils/extractUnstructuredTableRows.ts");
const TEMPLATE_EXPORT = resolve(ROOT, "src/components/template/utils/buildTemplateExportPayload.ts");

// ---------------------------------------------------------------------------
// 0. Builder must exist + import helpers as before
// ---------------------------------------------------------------------------
if (!existsSync(BUILDER_PATH)) fail("UnstructuredBuilder.tsx missing");
else ok("UnstructuredBuilder.tsx present");

const builderSrc = readSafe(BUILDER_PATH) ?? "";
const builderCode = stripComments(builderSrc);

if (!/from\s+["']\.\/utils\/unstructuredDefinition["']/.test(builderCode))
  fail("UnstructuredBuilder does not import from ./utils/unstructuredDefinition");
else ok("UnstructuredBuilder imports from ./utils/unstructuredDefinition");

for (const sym of [
  "normalizeUnstructuredTemplate",
  "serializeUnstructuredTemplate",
  "createDefaultInfoField",
  "createDefaultTableDef",
  "createDefaultTableColumn",
]) {
  const re = new RegExp(`\\b${sym}\\b`);
  if (!re.test(builderCode)) fail(`helper symbol missing: ${sym}`);
  else ok(`helper symbol present: ${sym}`);
}

// ---------------------------------------------------------------------------
// 1. SelectedUnstructuredTarget 타입 (또는 동등한 union) + selectedTarget state
// ---------------------------------------------------------------------------
if (!/type\s+SelectedUnstructuredTarget\b/.test(builderCode))
  fail("type SelectedUnstructuredTarget not declared");
else ok("type SelectedUnstructuredTarget declared");

if (!/\btype\s*:\s*["']info["']/.test(builderCode))
  fail("SelectedUnstructuredTarget missing info variant");
else ok("info variant present");
if (!/\btype\s*:\s*["']table["']/.test(builderCode))
  fail("SelectedUnstructuredTarget missing table variant");
else ok("table variant present");
if (!/\btype\s*:\s*["']column["']/.test(builderCode))
  fail("SelectedUnstructuredTarget missing column variant");
else ok("column variant present");

if (!/const\s+\[\s*selectedTarget\s*,\s*setSelectedTarget\s*\]\s*=\s*useState\s*<\s*SelectedUnstructuredTarget\s*>\s*\(\s*null\s*\)/.test(builderCode))
  fail("selectedTarget / setSelectedTarget useState(null) not found");
else ok("selectedTarget state present");

// selectedNo 잔존 금지 — selectedTarget 단일 source of truth
if (/\bsetSelectedNo\b|\bselectedNo\b/.test(builderCode))
  fail("legacy selectedNo / setSelectedNo should be removed (use selectedTarget)");
else ok("legacy selectedNo removed");

// ---------------------------------------------------------------------------
// 2. info / table / column 선택 마커 (click/focus 양쪽)
// ---------------------------------------------------------------------------
const infoSelectionMarkers = [
  /setSelectedTarget\s*\(\s*\{\s*type\s*:\s*["']info["']\s*,\s*index\s*:/,
];
let infoSelMatched = 0;
for (const re of infoSelectionMarkers) if (re.test(builderCode)) infoSelMatched++;
if (infoSelMatched === 0) fail("info selection setter not found");
else ok("info selection setter present");

if (!/setSelectedTarget\s*\(\s*\{\s*type\s*:\s*["']table["']/.test(builderCode))
  fail("table selection setter not found");
else ok("table selection setter present");

if (!/setSelectedTarget\s*\(\s*\{\s*type\s*:\s*["']column["']/.test(builderCode))
  fail("column selection setter not found");
else ok("column selection setter present");

// onFocus 진입으로도 selection 갱신되는지 (info / table / column 각각 최소 1회)
const onFocusInfo = builderCode.match(/onFocus=\{\s*\(\s*\)\s*=>\s*setSelectedTarget\s*\(\s*\{\s*type\s*:\s*["']info["']/g);
const onFocusTable = builderCode.match(/onFocus=\{\s*\(\s*\)\s*=>\s*setSelectedTarget\s*\(\s*\{\s*type\s*:\s*["']table["']/g);
const onFocusColumn = builderCode.match(/onFocus=\{\s*\(\s*\)\s*=>\s*setSelectedTarget\s*\(\s*\{\s*type\s*:\s*["']column["']/g);
if (!onFocusInfo || onFocusInfo.length === 0) fail("info input onFocus selection missing");
else ok(`info input onFocus selection x${onFocusInfo.length}`);
if (!onFocusTable || onFocusTable.length === 0) fail("table input onFocus selection missing");
else ok(`table input onFocus selection x${onFocusTable.length}`);
if (!onFocusColumn || onFocusColumn.length === 0) fail("column input onFocus selection missing");
else ok(`column input onFocus selection x${onFocusColumn.length}`);

// 컬럼 row 클릭 시 stopPropagation 사용 (table 카드 onClick에 가려지지 않도록)
if (!/onClick=\{\s*\(\s*e\s*\)\s*=>\s*\{[^}]*e\.stopPropagation\(\)[^}]*setSelectedTarget\s*\(\s*\{\s*type\s*:\s*["']column["']/m.test(
  builderCode.replace(/\n/g, " "),
))
  fail("column row onClick must stopPropagation before setting column selection");
else ok("column row onClick uses stopPropagation");

// ---------------------------------------------------------------------------
// 3. 선택 대상에 따라 라벨이 바뀌는 단일 삭제 버튼
// ---------------------------------------------------------------------------
for (const label of ["영역 삭제", "테이블 삭제", "컬럼 삭제"]) {
  if (!builderCode.includes(label))
    fail(`delete label "${label}" not found`);
  else ok(`delete label present: ${label}`);
}
// fallback 라벨 "삭제" — null state 표시용. handleDelete 기존 버튼도 "삭제"
// 이므로 builder source에 최소 1회 포함되어야 한다.
if (!/>\s*삭제\s*</.test(builderCode) && !/return\s*["']삭제["']/.test(builderCode))
  fail(`fallback label "삭제" not found`);
else ok(`fallback "삭제" label present`);

if (!/handleSelectedDelete\b/.test(builderCode))
  fail("handleSelectedDelete entry point missing");
else ok("handleSelectedDelete entry point present");

// disabled 정책 — selectedTarget == null일 때 disabled 처리
if (!/disabled=\{[^}]*selectedTarget[^}]*\}/.test(builderCode) &&
    !/isSelectedDeleteDisabled/.test(builderCode))
  fail("delete button disabled state not wired");
else ok("delete button disabled state wired");

// ---------------------------------------------------------------------------
// 4. info / table / column 삭제 경로가 모두 존재
// ---------------------------------------------------------------------------
const collapsed = builderCode.replace(/\s+/g, " ");
if (!/selectedTarget\.type\s*===\s*["']info["']/.test(collapsed))
  fail("info delete branch not found");
else ok("info delete branch present");
if (!/selectedTarget\.type\s*===\s*["']table["']/.test(collapsed))
  fail("table delete branch not found");
else ok("table delete branch present");
if (!/selectedTarget\.type\s*===\s*["']column["']/.test(collapsed))
  fail("column delete branch not found");
else ok("column delete branch present");

// info delete should renumber (no 재번호) — map((f, i) => ({ ...f, no: i + 1 }))
if (!/map\(\s*\(\s*f\s*,\s*i\s*\)\s*=>\s*\(\s*\{\s*\.\.\.f\s*,\s*no\s*:\s*i\s*\+\s*1\s*\}\s*\)\s*\)/.test(collapsed))
  fail("info delete must renumber field.no after filter");
else ok("info delete renumbers field.no");

// ---------------------------------------------------------------------------
// 5. 카드 내부 "표 삭제" 버튼 + 컬럼 row X 삭제 버튼 제거
// ---------------------------------------------------------------------------
if (/표\s*삭제/.test(builderCode))
  fail(`"표 삭제" 버튼 marker가 아직 남아 있음`);
else ok(`"표 삭제" 버튼 marker 제거됨`);

// removeTable / removeColumn helper도 더 이상 사용되지 않아야 한다.
if (/\bremoveTable\b/.test(builderCode))
  fail("removeTable helper should be removed");
else ok("removeTable helper removed");
if (/\bremoveColumn\b/.test(builderCode))
  fail("removeColumn helper should be removed");
else ok("removeColumn helper removed");

// 컬럼 row X 버튼 marker — title="컬럼 삭제" 또는 ✕ symbol
if (/title="컬럼\s*삭제"/.test(builderCode))
  fail(`컬럼 row X 버튼 (title="컬럼 삭제") 아직 남아 있음`);
else ok(`컬럼 row X 버튼 (title="컬럼 삭제") 제거됨`);
if (/>\s*✕\s*</.test(builderCode))
  fail(`컬럼 row X (✕ 글리프) 아직 남아 있음`);
else ok(`컬럼 row X (✕ 글리프) 제거됨`);

// ---------------------------------------------------------------------------
// 6. + 컬럼 / + 영역 정의 / + 테이블 정의 / 상단 삭제 / 저장 버튼 유지
// ---------------------------------------------------------------------------
// "+ 컬럼"은 시각적 일관성 위해 + 접두사 유지. "영역 정의"/"테이블 정의"는
// 사용자 요청으로 + 접두사 제거됨(UI 정돈).
for (const label of ["+ 컬럼", "영역 정의", "테이블 정의"]) {
  if (!builderCode.includes(label))
    fail(`add button label missing: ${label}`);
  else ok(`add button label present: ${label}`);
}

// addField/addTable/addColumn helper 유지
for (const sym of ["addField", "addTable", "addColumn"]) {
  if (!new RegExp(`\\b${sym}\\b`).test(builderCode))
    fail(`add helper missing: ${sym}`);
  else ok(`add helper present: ${sym}`);
}

// ---------------------------------------------------------------------------
// 7. save/load 흐름 보존
// ---------------------------------------------------------------------------
if (!/serializeUnstructuredTemplate\s*\(/.test(builderCode))
  fail("serializeUnstructuredTemplate not invoked");
else ok("serializeUnstructuredTemplate invoked (save)");
if (!/normalizeUnstructuredTemplate\s*\(/.test(builderCode))
  fail("normalizeUnstructuredTemplate not invoked");
else ok("normalizeUnstructuredTemplate invoked (load)");

// serialize block must still pass {templateName, documentType, info, tables}.
// Properties may use shorthand (`info,`) or explicit form (`info:`).
const serializeBlock = builderCode.match(/serializeUnstructuredTemplate\(\{[\s\S]*?\}\)/);
if (!serializeBlock) fail("serialize call site not found");
else {
  const blk = serializeBlock[0];
  for (const key of ["templateName", "documentType", "info", "tables"]) {
    const reExplicit = new RegExp(`\\b${key}\\s*:`);
    const reShorthand = new RegExp(`(^|[\\{,\\s])${key}\\s*[,\\}]`);
    if (!reExplicit.test(blk) && !reShorthand.test(blk))
      fail(`serialize payload missing key: ${key}`);
    else ok(`serialize payload has key: ${key}`);
  }
}

// localStorage key 변경 없음
if (!/LOCAL_TEMPLATES_KEY\s*=\s*"mysuit_ocr_templates"/.test(builderCode))
  fail(`LOCAL_TEMPLATES_KEY changed from "mysuit_ocr_templates"`);
else ok(`LOCAL_TEMPLATES_KEY preserved`);

// ---------------------------------------------------------------------------
// 8. 금지 파일 untouched (helper export 시그니처가 살아있는지로 약하게 확인)
// ---------------------------------------------------------------------------
const helperSrc = readSafe(HELPER_PATH) ?? "";
for (const sig of [
  "export function normalizeUnstructuredTemplate",
  "export function serializeUnstructuredTemplate",
  "export function createDefaultInfoField",
  "export function createDefaultTableDef",
  "export function createDefaultTableColumn",
]) {
  if (!helperSrc.includes(sig))
    fail(`unstructuredDefinition.ts missing export: ${sig}`);
  else ok(`unstructuredDefinition.ts export present: ${sig}`);
}

for (const [label, p] of [
  ["TemplateRightPanel.tsx", TEMPLATE_RIGHT_PANEL],
  ["TemplateAnnotator.tsx", TEMPLATE_ANNOTATOR],
  ["OcrCanvasPane.tsx", OCR_CANVAS_PANE],
  ["tableResultViewModel.ts", TABLE_RESULT_VM],
  ["cleanJsonBuilder.ts", CLEAN_JSON_BUILDER],
  ["markdownReportBuilder.ts", MARKDOWN_REPORT_BUILDER],
  ["mapOcrResponse.ts", MAP_OCR_RESPONSE],
  ["extractUnstructuredTableRows.ts", EXTRACT_UNSTRUCTURED],
  ["buildTemplateExportPayload.ts", TEMPLATE_EXPORT],
]) {
  if (!existsSync(p)) fail(`expected file missing (untouched): ${label}`);
  else ok(`file present (untouched expected): ${label}`);
}

// ---------------------------------------------------------------------------
// 9. src/lib absent + @/lib import 0건
// ---------------------------------------------------------------------------
const SRC_LIB = resolve(ROOT, "src/lib");
if (existsSync(SRC_LIB)) {
  const files = walk(SRC_LIB);
  if (files.length > 0) fail(`src/lib must be absent or empty (found ${files.length} file(s))`);
  else ok("src/lib present but empty");
} else ok("src/lib absent");

const SRC_ROOT = resolve(ROOT, "src");
const allSrcFiles = walk(SRC_ROOT).filter((p) =>
  p.endsWith(".ts") || p.endsWith(".tsx") || p.endsWith(".mjs") || p.endsWith(".js"),
);
const reLibAlias = /from\s+["']@\/lib(\/|["'])|import\(\s*["']@\/lib(\/|["'])/;
const reLibRelative = /from\s+["']\.\.\/lib(\/|["'])|from\s+["']\.\.\/\.\.\/lib(\/|["'])/;
let aliasHits = 0, relHits = 0;
for (const p of allSrcFiles) {
  const src = readSafe(p) ?? "";
  if (reLibAlias.test(src)) { aliasHits++; fail(`@/lib import in ${relative(ROOT, p)}`); }
  if (reLibRelative.test(src)) { relHits++; fail(`relative lib import in ${relative(ROOT, p)}`); }
}
if (aliasHits === 0) ok("@/lib imports: 0");
if (relHits === 0) ok("relative lib imports: 0");

// ---------------------------------------------------------------------------
if (failures.length === 0) {
  console.log(`${TAG} PASS`);
  process.exit(0);
} else {
  console.error(`${TAG} FAIL count=${failures.length}`);
  for (const m of failures) console.error(`${TAG}   - ${m}`);
  process.exit(1);
}
