# FRONTEND_LIB_OCR_RESULT_FORMATTERS_COMMON_MOVE_PRECHECK_20260522

## 1. 사용 도구와 모델
- 도구: Codex
- 모델: Codex
- 작업명: CODEX_FRONTEND_LIB_OCR_RESULT_FORMATTERS_COMMON_MOVE_PRECHECK_NO_PROD_MODIFY

## 2. 코드 수정 여부
- 운영 코드 수정 여부: false
- 파일 이동/import 수정/rename/fixture/templates/backend 수정: false
- 생성 가능한 precheck 산출물만 작성했다.

## 3. 생성 파일
- `tmp/codex_frontend_lib_ocr_result_formatters_common_move_precheck.py`
- `docs/FRONTEND_LIB_OCR_RESULT_FORMATTERS_COMMON_MOVE_PRECHECK_20260522.md`
- `docs/FRONTEND_LIB_OCR_RESULT_FORMATTERS_COMMON_MOVE_PRECHECK_20260522.json`
- `docs/FRONTEND_LIB_OCR_RESULT_FORMATTERS_COMMON_MOVE_PRECHECK_MAP_20260522.csv`

## 4. 분석 범위
- `src/lib/ocrResultFormatters.ts`
- `src/components/runocr`
- `src/components/template`
- `src/common`
- `src/components/test/TestWorkspace.tsx`
- `src/app`

참고 리포트:
- `docs/FRONTEND_LIB_OWNERSHIP_PRECHECK_20260522.md`
- `docs/FRONTEND_STRUCTURE_6B_TEMPLATE_ANNOTATOR_RENAME_20260522.md`
- `docs/FRONTEND_STRUCTURE_5F_OCR_CANVAS_PANE_COMMON_UI_MOVE_20260522.md`
- `docs/FRONTEND_RUNOCR_CYCLE1_CLOSEOUT_20260522.md`

## 5. ocrResultFormatters 역할 요약
- currentPath: `src/lib/ocrResultFormatters.ts`
- lineCount: 120
- mainResponsibility: Pure OCR result display/report formatters: field labels, amount-like detection, adoption labels, and serialized table field parsing for RunOCR result UI and markdown report generation.
- sideEffects: False
- browser/localStorage/IndexedDB: False
- React 의존: False
- components/* 의존: False
- common/utils 적합성: Good fit: pure deterministic helpers with no React, DOM, storage, backend, or components/* dependency. Caveat: it currently imports src/lib/autofillEngine types and src/lib/invoiceFieldLabels.
- moveRisk: LOW

imports:
- `import type { AutofillAction, OutputValueSource } from "@/lib/autofillEngine";`
- `import { resolveFieldLabel } from "@/lib/invoiceFieldLabels";`

exports:
- `export type OcrFormatterField = {`
- `export function fieldLabel(field: OcrFormatterField): string {`
- `export function fieldLabelFull(field: OcrFormatterField): string {`
- `export function isAmountLikeField(field: OcrFormatterField): boolean {`
- `export type OcrAdoptionLabel = "OCR" | "복원" | "직접입력" | "-";`
- `export function getAdoptionLabel(field: OcrFormatterField): OcrAdoptionLabel {`
- `export type TableCell = { value: string; confidence: number };`
- `export type ParsedTableField = {`
- `export function parseTableField(value: string): ParsedTableField {`

exported names:
fieldLabel, fieldLabelFull, isAmountLikeField, getAdoptionLabel, parseTableField, OcrFormatterField, OcrAdoptionLabel, TableCell, ParsedTableField

## 6. importedBy 분석
| file | importPath | kind | imported symbols | feature | import 수정 필요 | TestWorkspace 영향 |
|---|---|---|---|---|---:|---:|
| `src/components/runocr/ui/OcrResultPanel.tsx` | `@/lib/ocrResultFormatters` | static | `{ fieldLabel, fieldLabelFull, getAdoptionLabel, isAmountLikeField, parseTableField, }` | runocr | True | False |
| `src/lib/markdownReportBuilder.ts` | `@/lib/ocrResultFormatters` | static | `this file. They consume * the shared formatters in ocrResultFormatters.ts. Only the markdown copy / * export / preview-markdown-render code paths import buildMarkdownReport. * * Markdown v1 contract (unchanged in this extraction): * - First line: "# OCR 결과" * - "- 처리 시간: **N.NNs**" and "- 필드 수: **N건**" summary bullets * - Markdown table: No / 필드명 / 값 / 신뢰도 / 채택 * - One row per field, in `fields` order * - field_type === "table" rows render only "표 데이터 (N행)" summary, * where N comes from docTableRows.length if available, else from the * legacy parseTableField rowLabel * - Pipe and newline in label/value are escaped via `esc()` * - Line endings are "\n" only (matches LF fixture policy) */ import { fieldLabelFull, getAdoptionLabel, parseTableField, type OcrFormatterField, }` | lib | True | False |

## 7. common/utils 적합성
- 판정: `COMMON_UTIL_READY_WITH_IMPORT_ONLY`
- 이유: The file is pure and has no React, DOM, storage, backend, or components/* dependency. Moving to common/utils requires only import path updates in OcrResultPanel and markdownReportBuilder.
- common -> components 의존 발생 여부: false
- TestWorkspace 직접 import 영향: false
- 주의: 이동 직후에는 `autofillEngine` type import와 `invoiceFieldLabels` import가 `src/lib`에 남을 수 있다. 이는 components 의존은 아니며, 후속 LIB-1/별도 precheck에서 정리한다.

## 8. target path 비교
| target | 추천 | 장점 | 단점 | import 수정 범위 | risk |
|---|---:|---|---|---|---|
| `src/common/utils/ocrResultFormatters.ts` | True | Matches shared pure formatter role; Allows RunOCR UI and report builders to depend on common utils; No components/* dependency introduced | Temporarily common/utils would import from src/lib/autofillEngine and src/lib/invoiceFieldLabels until later LIB moves; Requires import-only updates in two consumers | src/components/runocr/ui/OcrResultPanel.tsx; src/lib/markdownReportBuilder.ts | LOW |
| `src/components/runocr/utils/ocrResultFormatters.ts` | False | Close to the main UI consumer | markdownReportBuilder in src/lib would import feature code or need to move too; Less aligned with shared report/display helper role | src/components/runocr/ui/OcrResultPanel.tsx; src/lib/markdownReportBuilder.ts | MEDIUM |
| `src/lib/ocrResultFormatters.ts` | False | No immediate code change | Leaves src/lib cleanup stalled; Does not progress LIB-1 common utils | none | LOW |
| `DEFER` | False | Avoids any current dirty-state interaction | Unnecessary given small import surface and pure helper shape | none | LOW |

## 9. 실제 이동 추천
- 추천 선택지: A. `ocrResultFormatters.ts`만 `src/common/utils/ocrResultFormatters.ts`로 이동
- 이유: 첫 LIB 이동은 작게 시작하는 것이 안전하고, direct consumer가 2곳뿐이며 순수 formatter이다.
- 필요한 import 수정: `src/components/runocr/ui/OcrResultPanel.tsx`, `src/lib/markdownReportBuilder.ts`
- 묶음 이동(D)은 비추천: markdown/clean json과 한 번에 묶으면 첫 LIB 이동 diff가 커진다.

## 10. static check 설계
- tmp/check_lib_ocr_result_formatters_common_move_1a.mjs
- src/common/utils/ocrResultFormatters.ts exists
- src/lib/ocrResultFormatters.ts absent
- src/common/utils/ocrResultFormatters.ts does not import src/components/*
- React/localStorage/window/document/fetch/indexedDB dependency remains absent
- src/components/runocr/ui/OcrResultPanel.tsx import path points to common utils
- src/lib/markdownReportBuilder.ts import path points to common utils
- No @/lib/ocrResultFormatters or ../../lib/ocrResultFormatters remains in src
- TestWorkspace unchanged
- RunOCR boundary checks PASS
- Template checks PASS
- table_view_model/Clean JSON/Markdown checks PASS
- npm run typecheck PASS
- npm run build PASS

## 11. dirty 상태
```text
 M docs/FRONTEND_CLEANUP_1B_JS_CLEAN_JSON_FIXTURE_RUNNER_20260521.json
 M docs/FRONTEND_CLEANUP_1B_JS_CLEAN_JSON_FIXTURE_RUNNER_20260521.md
 M docs/FRONTEND_CLEANUP_3D2_RUNNER_RESULT_20260521.json
 M src/app/ocr/page.tsx
 M src/app/template/page.tsx
R  src/components/ocr/core/types.ts -> src/common/types/ocr.ts
R  src/components/common/FileDropzone.tsx -> src/common/ui/FileDropzone.tsx
RM src/components/ocr/OcrCanvasPane.tsx -> src/common/ui/OcrCanvasPane.tsx
RM src/components/ocr/core/ops.ts -> src/common/utils/ocrCanvasOps.ts
RM src/components/ocr/core/table.ts -> src/common/utils/ocrTableRegion.ts
 M src/components/runocr/RunOcrWorkspace.tsx
 M src/components/runocr/utils/buildOcrFormData.ts
RM src/components/template/ui/OcrAnnotator.tsx -> src/components/template/ui/TemplateAnnotator.tsx
RM src/components/template/ui/OcrRightPanel.tsx -> src/components/template/ui/TemplateRightPanel.tsx
RM src/components/ocr/core/export.ts -> src/components/template/utils/buildTemplateExportPayload.ts
 M tmp/check_runocr_doc_comments_3b.mjs
 M tmp/check_runocr_formdata_keys_2a.mjs
 M tmp/check_runocr_response_mapping_boundary_2c.mjs
 M tmp/check_template_editor_ui_move_4b.mjs
 M tmp/check_template_workspace_move_4a.mjs
 M tmp/codex_markdown_contract_fixture_lock.py
 M ../ocr-server/data/review_log.jsonl
 M ../ocr-server/data/templates.json
?? docs/FRONTEND_FILEDROPZONE_COMMON_UI_PRECHECK_20260522.json
?? docs/FRONTEND_FILEDROPZONE_COMMON_UI_PRECHECK_20260522.md
?? docs/FRONTEND_FILEDROPZONE_COMMON_UI_PRECHECK_MAP_20260522.csv
?? docs/FRONTEND_LIB_OWNERSHIP_MAP_20260522.csv
?? docs/FRONTEND_LIB_OWNERSHIP_PRECHECK_20260522.json
?? docs/FRONTEND_LIB_OWNERSHIP_PRECHECK_20260522.md
?? docs/FRONTEND_OCR_CANVAS_PANE_COMMON_MOVE_PRECHECK_20260522.json
?? docs/FRONTEND_OCR_CANVAS_PANE_COMMON_MOVE_PRECHECK_20260522.md
?? docs/FRONTEND_OCR_CANVAS_PANE_COMMON_MOVE_PRECHECK_MAP_20260522.csv
?? docs/FRONTEND_OCR_CANVAS_PANE_SHARED_MAP_20260522.csv
?? docs/FRONTEND_OCR_CANVAS_PANE_SHARED_PRECHECK_20260522.json
?? docs/FRONTEND_OCR_CANVAS_PANE_SHARED_PRECHECK_20260522.md
?? docs/FRONTEND_OCR_CORE_EXPORT_TEMPLATE_UTIL_PRECHECK_20260522.json
?? docs/FRONTEND_OCR_CORE_EXPORT_TEMPLATE_UTIL_PRECHECK_20260522.md
?? docs/FRONTEND_OCR_CORE_EXPORT_TEMPLATE_UTIL_PRECHECK_MAP_20260522.csv
?? docs/FRONTEND_OCR_CORE_OPS_COMMON_MOVE_PRECHECK_20260522.json
?? docs/FRONTEND_OCR_CORE_OPS_COMMON_MOVE_PRECHECK_20260522.md
?? docs/FRONTEND_OCR_CORE_OPS_COMMON_MOVE_PRECHECK_MAP_20260522.csv
?? docs/FRONTEND_OCR_CORE_OWNERSHIP_MAP_20260522.csv
?? docs/FRONTEND_OCR_CORE_OWNERSHIP_PRECHECK_20260522.json
?? docs/FRONTEND_OCR_CORE_OWNERSHIP_PRECHECK_20260522.md
?? docs/FRONTEND_OCR_CORE_TABLE_COMMON_MOVE_PRECHECK_20260522.json
?? docs/FRONTEND_OCR_CORE_TABLE_COMMON_MOVE_PRECHECK_20260522.md
?? docs/FRONTEND_OCR_CORE_TABLE_COMMON_MOVE_PRECHECK_MAP_20260522.csv
?? docs/FRONTEND_STRUCTURE_5A_OCR_CORE_TYPES_COMMON_MOVE_20260522.json
?? docs/FRONTEND_STRUCTURE_5A_OCR_CORE_TYPES_COMMON_MOVE_20260522.md
?? docs/FRONTEND_STRUCTURE_5B_OCR_CORE_OPS_COMMON_MOVE_20260522.json
?? docs/FRONTEND_STRUCTURE_5B_OCR_CORE_OPS_COMMON_MOVE_20260522.md
?? docs/FRONTEND_STRUCTURE_5C_OCR_CORE_TABLE_COMMON_MOVE_20260522.json
?? docs/FRONTEND_STRUCTURE_5C_OCR_CORE_TABLE_COMMON_MOVE_20260522.md
?? docs/FRONTEND_STRUCTURE_5D_TEMPLATE_EXPORT_PAYLOAD_MOVE_20260522.json
?? docs/FRONTEND_STRUCTURE_5D_TEMPLATE_EXPORT_PAYLOAD_MOVE_20260522.md
?? docs/FRONTEND_STRUCTURE_5E_FILEDROPZONE_COMMON_UI_MOVE_20260522.json
?? docs/FRONTEND_STRUCTURE_5E_FILEDROPZONE_COMMON_UI_MOVE_20260522.md
?? docs/FRONTEND_STRUCTURE_5F_OCR_CANVAS_PANE_COMMON_UI_MOVE_20260522.json
?? docs/FRONTEND_STRUCTURE_5F_OCR_CANVAS_PANE_COMMON_UI_MOVE_20260522.md
?? docs/FRONTEND_STRUCTURE_6A_TEMPLATE_RIGHT_PANEL_RENAME_20260522.json
?? docs/FRONTEND_STRUCTURE_6A_TEMPLATE_RIGHT_PANEL_RENAME_20260522.md
?? docs/FRONTEND_STRUCTURE_6B_TEMPLATE_ANNOTATOR_RENAME_20260522.json
?? docs/FRONTEND_STRUCTURE_6B_TEMPLATE_ANNOTATOR_RENAME_20260522.md
?? docs/FRONTEND_TEMPLATE_ANNOTATOR_RENAME_PRECHECK_20260522.json
?? docs/FRONTEND_TEMPLATE_ANNOTATOR_RENAME_PRECHECK_20260522.md
?? docs/FRONTEND_TEMPLATE_ANNOTATOR_RENAME_PRECHECK_MAP_20260522.csv
?? docs/FRONTEND_TEMPLATE_RIGHT_PANEL_RENAME_PRECHECK_20260522.json
?? docs/FRONTEND_TEMPLATE_RIGHT_PANEL_RENAME_PRECHECK_20260522.md
?? docs/FRONTEND_TEMPLATE_RIGHT_PANEL_RENAME_PRECHECK_MAP_20260522.csv
?? docs/FRONTEND_VALIDATION_1A_BASELINE_REPAIR_20260522.json
?? docs/FRONTEND_VALIDATION_1A_BASELINE_REPAIR_20260522.md
?? docs/FRONTEND_VALIDATION_BASELINE_REPAIR_PRECHECK_20260522.json
?? docs/FRONTEND_VALIDATION_BASELINE_REPAIR_PRECHECK_20260522.md
?? docs/FRONTEND_VALIDATION_BASELINE_REPAIR_PRECHECK_MAP_20260522.csv
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_FILEDROPZONE_COMMON_UI_MOVE_20260522_20260521.json
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_FILEDROPZONE_COMMON_UI_MOVE_20260522_20260521.md
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_OCR_CANVAS_PANE_COMMON_UI_MOVE_20260522_20260521.json
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_OCR_CANVAS_PANE_COMMON_UI_MOVE_20260522_20260521.md
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_OCR_CORE_OPS_COMMON_MOVE_20260522_20260521.json
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_OCR_CORE_OPS_COMMON_MOVE_20260522_20260521.md
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_OCR_CORE_TABLE_COMMON_MOVE_20260522_20260521.json
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_OCR_CORE_TABLE_COMMON_MOVE_20260522_20260521.md
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_OCR_CORE_TYPES_COMMON_MOVE_20260522_20260521.json
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_OCR_CORE_TYPES_COMMON_MOVE_20260522_20260521.md
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_TEMPLATE_ANNOTATOR_RENAME_20260522_20260521.json
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_TEMPLATE_ANNOTATOR_RENAME_20260522_20260521.md
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_TEMPLATE_EXPORT_PAYLOAD_MOVE_20260522_20260521.json
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_TEMPLATE_EXPORT_PAYLOAD_MOVE_20260522_20260521.md
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_TEMPLATE_RIGHT_PANEL_RENAME_20260522_20260521.json
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_TEMPLATE_RIGHT_PANEL_RENAME_20260522_20260521.md
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_VALIDATION_BASELINE_REPAIR_20260522_20260521.json
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_VALIDATION_BASELINE_REPAIR_20260522_20260521.md
?? tmp/check_filedropzone_common_ui_move_5e.mjs
?? tmp/check_ocr_canvas_pane_common_ui_move_5f.mjs
?? tmp/check_ocr_core_ops_common_move_5b.mjs
?? tmp/check_ocr_core_table_common_move_5c.mjs
?? tmp/check_ocr_core_types_common_move_5a.mjs
?? tmp/check_template_annotator_rename_6b.mjs
?? tmp/check_template_export_payload_move_5d.mjs
?? tmp/check_template_right_panel_rename_6a.mjs
?? tmp/check_validation_baseline_repair_1a.mjs
?? tmp/codex_frontend_filedropzone_common_ui_precheck.py
?? tmp/codex_frontend_lib_ocr_result_formatters_common_move_precheck.py
?? tmp/codex_frontend_lib_ownership_precheck.py
?? tmp/codex_frontend_ocr_canvas_pane_common_move_precheck.py
?? tmp/codex_frontend_ocr_canvas_pane_shared_precheck.py
?? tmp/codex_frontend_ocr_core_export_template_util_precheck.py
?? tmp/codex_frontend_ocr_core_ops_common_move_precheck.py
?? tmp/codex_frontend_ocr_core_ownership_precheck.py
?? tmp/codex_frontend_ocr_core_table_common_move_precheck.py
?? tmp/codex_frontend_template_annotator_rename_precheck.py
?? tmp/codex_frontend_template_right_panel_rename_precheck.py
?? tmp/codex_frontend_validation_baseline_repair_precheck.py
```

- `../ocr-server/data/templates.json` dirty 상태가 있으면 실제 이동 전 영향 후보로 유지한다.
- TPL-95328E52 dirty 영향 precheck 후보를 유지한다.

## 12. typecheck/build 결과
- typecheck: `PASS` exitCode=0
- build: `PASS` exitCode=0
- known stderr noise: ESLint `nextVitals is not iterable`은 exit code 0이면 known issue로 기록한다.

## 13. 다음 작업 제안
- Proceed with option A as a small move-only micro-step.
- Create a move-specific static checker before or during the actual move step.
- Keep markdownReportBuilder/cleanJsonBuilder moves separate.
- Later, move invoiceFieldLabels to common/utils so ocrResultFormatters can stop importing it from src/lib.
