# FRONTEND LIB invoiceTableDisplay common move precheck

## 1. 사용 도구와 모델
- Tool: Codex
- Model: Codex
- Task: `CODEX_FRONTEND_LIB_INVOICE_TABLE_DISPLAY_COMMON_MOVE_PRECHECK_NO_PROD_MODIFY`

## 2. 코드 수정 여부
- codeModified: false
- 운영 코드 수정 없음
- 파일 이동/import 수정/rename/fixture/templates/backend 수정 없음

## 3. 생성 파일
- `tmp/codex_frontend_lib_invoice_table_display_common_move_precheck.py`
- `docs/FRONTEND_LIB_INVOICE_TABLE_DISPLAY_COMMON_MOVE_PRECHECK_20260522.md`
- `docs/FRONTEND_LIB_INVOICE_TABLE_DISPLAY_COMMON_MOVE_PRECHECK_20260522.json`
- `docs/FRONTEND_LIB_INVOICE_TABLE_DISPLAY_COMMON_MOVE_PRECHECK_MAP_20260522.csv`
- `ocr-server/logs/codex_CODEX_FRONTEND_LIB_INVOICE_TABLE_DISPLAY_COMMON_MOVE_PRECHECK_NO_PROD_MODIFY.out.log`
- `ocr-server/logs/codex_CODEX_FRONTEND_LIB_INVOICE_TABLE_DISPLAY_COMMON_MOVE_PRECHECK_NO_PROD_MODIFY.err.log`

## 4. 분석 범위
- `src/lib/invoiceTableDisplay.ts`
- `src/common/utils/cleanJsonBuilder.ts`
- `src/common/utils/ocrResultFormatters.ts`
- `src/common/utils/invoiceFieldLabels.ts`
- `src/components/runocr/**`
- `src/components/history/**`
- `src/components/test/TestWorkspace.tsx` 읽기 전용
- `src/components/test/core/**` 읽기 전용
- `src/common/**`
- `src/app/**`

## 5. invoiceTableDisplay 역할 요약
- currentPath: `src/lib/invoiceTableDisplay.ts`
- lineCount: 335
- imports: 0
- exports: InvoiceDisplayCol, INVOICE_TABLE_COL_PRIORITY, INVOICE_COL_LABEL_MAP, isInternalTableKey, normalizeTableCell, isMeaninglessTableValue, hasMeaningfulTableValue, shouldDisplayRowIndex, buildInvoicePreviewCols
- 역할: invoice table row/column display policy, label map, cell normalization, meaningful-value filtering, rowIndex visibility, preview column selection.
- sideEffects: false
- React/DOM/storage/backend/components dependency: false
- feature policy 포함: true

## 6. importedBy 분석
| file | importPath | symbols | feature | move import update |
|---|---|---|---|---|
| `src/common/utils/cleanJsonBuilder.ts` | `@/lib/invoiceTableDisplay` | `{ INVOICE_TABLE_COL_PRIORITY, hasMeaningfulTableValue, normalizeTableCell, }` | common | True |
| `src/components/history/DetailHistoryView.tsx` | `@/lib/invoiceTableDisplay` | `React, { useEffect, useMemo, useState } from "react"; import { type HistoryRunRecord, type HistoryOutputField, updateHistoryRun, getOriginalHistoryImage, getProcessedHistoryImage, syncHistoryIndexAndDetailOnSave, syncHistoryDetailTableRowsOnSave, } from "@/lib/historyStore"; import { buildInvoicePreviewCols, normalizeTableCell, }` | history | True |
| `src/components/runocr/ui/OcrResultPanel.tsx` | `@/lib/invoiceTableDisplay` | `React, { useEffect, useMemo, useRef, useState } from "react"; import Markdown from "react-markdown"; import remarkGfm from "remark-gfm"; import type { AutofillAction, AutofillRunSummary, AutofillSuggestion, OutputValueSource } from "@/lib/autofillEngine"; import { getGroundTruth, compareToGt, fieldKey } from "@/lib/groundTruthStore"; import { useUi } from "../../common/AppProviders"; import { INVOICE_COL_LABEL_MAP as _ALL_COL_LABEL_MAP, isInternalTableKey as isInternalKey, normalizeTableCell as normalizeCell, isMeaninglessTableValue as isMeaningless, hasMeaningfulTableValue as hasMeaningfulValue, buildInvoicePreviewCols, }` | runocr | True |
| `src/components/test/TestWorkspace.tsx` | `@/lib/invoiceTableDisplay` | `React, { useCallback, useEffect, useMemo, useRef, useState } from "react"; import { extractBizNumber, normalizeBizNumber } from "@/lib/bizNumber"; import { useUi } from "../common/AppProviders"; import { INVOICE_COL_LABEL_MAP, shouldDisplayRowIndex }` | test | True |
| `tmp/check_clean_json_v1_fixtures_js.mjs` | `@/lib/invoiceTableDisplay` | `` | unknown | True |
| `tmp/check_clean_json_v1_fixtures_js.mjs` | `./invoiceTableDisplay` | `` | unknown | True |
| `tmp/check_lib_clean_json_builder_common_move_1d.mjs` | `@/lib/invoiceTableDisplay` | `` | unknown | True |
| `tmp/codex_frontend_lib_clean_json_builder_common_move_precheck.py` | `@/lib/invoiceTableDisplay` | `` | unknown | True |
| `tmp/codex_frontend_lib_invoice_table_display_common_move_precheck.py` | `@/lib/invoiceTableDisplay` | `` | unknown | True |
| `tmp/codex_frontend_lib_invoice_table_display_common_move_precheck.py` | `@/common/utils/invoiceTableDisplay` | `` | unknown | False |
| `tmp/codex_frontend_lib_invoice_table_display_common_move_precheck.py` | `../lib/invoiceTableDisplay` | `` | unknown | True |
| `tmp/codex_frontend_lib_invoice_table_display_common_move_precheck.py` | `../../lib/invoiceTableDisplay` | `` | unknown | True |
| `tmp/codex_frontend_lib_invoice_table_display_common_move_precheck.py` | `./invoiceTableDisplay` | `` | unknown | True |


## 7. TestWorkspace 영향 분석
- 판정: `DEFER_DUE_TO_TEST_WORKSPACE_POLICY`
- `src/components/test/TestWorkspace.tsx` 직접 import: True
- `src/components/test/core/**` 직접 import: False
- 현재 정책상 TestWorkspace 수정 금지이므로 실제 이동은 보류하거나, 별도 승인으로 import path-only 변경을 허용해야 한다.

## 8. common/utils 적합성
- 판정: `DEFER_DUE_TO_TEST_IMPACT`
- TestWorkspace path-only update 승인 시 대체 판정: `COMMON_UTIL_READY_WITH_IMPORT_ONLY`
- 순수 helper이고 여러 feature가 공유하므로 common/utils 자체는 적합하다.

## 9. dependency/Clean JSON/table_view_model 영향
- `src/common/utils/cleanJsonBuilder.ts`의 `@/lib/invoiceTableDisplay` 임시 의존 해소 가능: True
- 이동 후 권장 import: `@/common/utils/invoiceTableDisplay`
- 순환 의존 위험: LOW
- Clean JSON runner 직접 source path 참조: True
- table_view_model fixture rebake 필요: False

## 10. target path 비교
| option | risk | recommended | note |
|---|---|---|---|
| `src/common/utils/invoiceTableDisplay.ts` | MEDIUM_HIGH | False | Correct target, but actual move should wait for explicit TestWorkspace import-path approval or be scoped to an approved TestWorkspace path-only update. |
| `src/components/runocr/utils/invoiceTableDisplay.ts` | HIGH | False |  |
| `src/components/test/utils/invoiceTableDisplay.ts` | HIGH | False |  |
| `src/lib 유지` | LOW | True | Recommended until TestWorkspace path-only update is approved. |
| `보류` | LOW | True |  |


## 11. 실제 이동 추천
- 추천 선택지: C. 이동 보류
- 이유: `TestWorkspace.tsx`가 직접 import하고 있고, 현재 사용자 정책상 TestWorkspace 수정은 사용자 확인 전 금지다.
- 승인 시 실제 범위: A. `invoiceTableDisplay.ts`만 `src/common/utils/invoiceTableDisplay.ts`로 이동하고 import path만 수정.
- 묶지 말 것: `structuredTableViewModel.ts`, `bizNumber.ts`

## 12. static check 설계
- proposed: `tmp/check_lib_invoice_table_display_common_move_1e.mjs`
- src/common/utils/invoiceTableDisplay.ts exists
- src/lib/invoiceTableDisplay.ts absent
- src/common/utils/invoiceTableDisplay.ts imports no components/* path
- React/localStorage/window/document dependency remains absent
- @/lib/invoiceTableDisplay string absent from src
- src/common/utils/cleanJsonBuilder.ts imports @/common/utils/invoiceTableDisplay
- TestWorkspace import path is either explicitly approved and updated, or move is deferred
- tmp/check_clean_json_v1_fixtures_js.mjs path/mapping updated or dedicated move checker passes
- clean JSON fixture lock PASS
- table_view_model fixture lock PASS
- RunOCR boundary checks PASS
- Template checks PASS
- npm run typecheck PASS
- npm run build PASS


## 13. dirty 상태
```text
 M docs/FRONTEND_CLEANUP_1B_JS_CLEAN_JSON_FIXTURE_RUNNER_20260521.json
 M docs/FRONTEND_CLEANUP_1B_JS_CLEAN_JSON_FIXTURE_RUNNER_20260521.md
 M docs/FRONTEND_CLEANUP_3D2_RUNNER_RESULT_20260521.json
 M src/app/ocr/page.tsx
 M src/app/template/page.tsx
R  src/components/ocr/core/types.ts -> src/common/types/ocr.ts
R  src/components/common/FileDropzone.tsx -> src/common/ui/FileDropzone.tsx
RM src/components/ocr/OcrCanvasPane.tsx -> src/common/ui/OcrCanvasPane.tsx
R  src/lib/cleanJsonBuilder.ts -> src/common/utils/cleanJsonBuilder.ts
R  src/lib/invoiceFieldLabels.ts -> src/common/utils/invoiceFieldLabels.ts
RM src/lib/markdownReportBuilder.ts -> src/common/utils/markdownReportBuilder.ts
RM src/components/ocr/core/ops.ts -> src/common/utils/ocrCanvasOps.ts
RM src/lib/ocrResultFormatters.ts -> src/common/utils/ocrResultFormatters.ts
RM src/components/ocr/core/table.ts -> src/common/utils/ocrTableRegion.ts
 M src/components/history/DetailHistoryView.tsx
 M src/components/runocr/RunOcrWorkspace.tsx
 M src/components/runocr/ui/OcrDocViewer.tsx
 M src/components/runocr/ui/OcrResultPanel.tsx
 M src/components/runocr/utils/buildOcrFormData.ts
RM src/components/template/ui/OcrAnnotator.tsx -> src/components/template/ui/TemplateAnnotator.tsx
RM src/components/template/ui/OcrRightPanel.tsx -> src/components/template/ui/TemplateRightPanel.tsx
RM src/components/ocr/core/export.ts -> src/components/template/utils/buildTemplateExportPayload.ts
 M tmp/check_clean_json_v1_fixtures_js.mjs
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
?? docs/FRONTEND_LIB_1A_OCR_RESULT_FORMATTERS_COMMON_MOVE_20260522.json
?? docs/FRONTEND_LIB_1A_OCR_RESULT_FORMATTERS_COMMON_MOVE_20260522.md
?? docs/FRONTEND_LIB_1B_INVOICE_FIELD_LABELS_COMMON_MOVE_20260522.json
?? docs/FRONTEND_LIB_1B_INVOICE_FIELD_LABELS_COMMON_MOVE_20260522.md
?? docs/FRONTEND_LIB_1C_MARKDOWN_REPORT_BUILDER_COMMON_MOVE_20260522.json
?? docs/FRONTEND_LIB_1C_MARKDOWN_REPORT_BUILDER_COMMON_MOVE_20260522.md
?? docs/FRONTEND_LIB_1D_CLEAN_JSON_BUILDER_COMMON_MOVE_20260522.json
?? docs/FRONTEND_LIB_1D_CLEAN_JSON_BUILDER_COMMON_MOVE_20260522.md
?? docs/FRONTEND_LIB_CLEAN_JSON_BUILDER_COMMON_MOVE_PRECHECK_20260522.json
?? docs/FRONTEND_LIB_CLEAN_JSON_BUILDER_COMMON_MOVE_PRECHECK_20260522.md
?? docs/FRONTEND_LIB_CLEAN_JSON_BUILDER_COMMON_MOVE_PRECHECK_MAP_20260522.csv
?? docs/FRONTEND_LIB_INVOICE_FIELD_LABELS_COMMON_MOVE_PRECHECK_20260522.json
?? docs/FRONTEND_LIB_INVOICE_FIELD_LABELS_COMMON_MOVE_PRECHECK_20260522.md
?? docs/FRONTEND_LIB_INVOICE_FIELD_LABELS_COMMON_MOVE_PRECHECK_MAP_20260522.csv
?? docs/FRONTEND_LIB_INVOICE_TABLE_DISPLAY_COMMON_MOVE_PRECHECK_20260522.json
?? docs/FRONTEND_LIB_INVOICE_TABLE_DISPLAY_COMMON_MOVE_PRECHECK_20260522.md
?? docs/FRONTEND_LIB_INVOICE_TABLE_DISPLAY_COMMON_MOVE_PRECHECK_20260522_MAP_20260522.csv
?? docs/FRONTEND_LIB_MARKDOWN_REPORT_BUILDER_COMMON_MOVE_PRECHECK_20260522.json
?? docs/FRONTEND_LIB_MARKDOWN_REPORT_BUILDER_COMMON_MOVE_PRECHECK_20260522.md
?? docs/FRONTEND_LIB_MARKDOWN_REPORT_BUILDER_COMMON_MOVE_PRECHECK_MAP_20260522.csv
?? docs/FRONTEND_LIB_OCR_RESULT_FORMATTERS_COMMON_MOVE_PRECHECK_20260522.json
?? docs/FRONTEND_LIB_OCR_RESULT_FORMATTERS_COMMON_MOVE_PRECHECK_20260522.md
?? docs/FRONTEND_LIB_OCR_RESULT_FORMATTERS_COMMON_MOVE_PRECHECK_MAP_20260522.csv
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
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_LIB_CLEAN_JSON_BUILDER_COMMON_MOVE_20260522_20260521.json
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_LIB_CLEAN_JSON_BUILDER_COMMON_MOVE_20260522_20260521.md
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_LIB_INVOICE_FIELD_LABELS_COMMON_MOVE_20260522_20260521.json
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_LIB_INVOICE_FIELD_LABELS_COMMON_MOVE_20260522_20260521.md
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_LIB_MARKDOWN_REPORT_BUILDER_COMMON_MOVE_20260522_20260521.json
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_LIB_MARKDOWN_REPORT_BUILDER_COMMON_MOVE_20260522_20260521.md
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_LIB_OCR_RESULT_FORMATTERS_COMMON_MOVE_20260522_20260521.json
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_LIB_OCR_RESULT_FORMATTERS_COMMON_MOVE_20260522_20260521.md
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
?? tmp/check_lib_clean_json_builder_common_move_1d.mjs
?? tmp/check_lib_invoice_field_labels_common_move_1b.mjs
?? tmp/check_lib_markdown_report_builder_common_move_1c.mjs
?? tmp/check_lib_ocr_result_formatters_common_move_1a.mjs
?? tmp/check_ocr_canvas_pane_common_ui_move_5f.mjs
?? tmp/check_ocr_core_ops_common_move_5b.mjs
?? tmp/check_ocr_core_table_common_move_5c.mjs
?? tmp/check_ocr_core_types_common_move_5a.mjs
?? tmp/check_template_annotator_rename_6b.mjs
?? tmp/check_template_export_payload_move_5d.mjs
?? tmp/check_template_right_panel_rename_6a.mjs
?? tmp/check_validation_baseline_repair_1a.mjs
?? tmp/codex_frontend_filedropzone_common_ui_precheck.py
?? tmp/codex_frontend_lib_clean_json_builder_common_move_precheck.py
?? tmp/codex_frontend_lib_invoice_field_labels_common_move_precheck.py
?? tmp/codex_frontend_lib_invoice_table_display_common_move_precheck.py
?? tmp/codex_frontend_lib_markdown_report_builder_common_move_precheck.py
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

## 14. typecheck/build 결과
- typecheck: PASS / exitCode 0
- build: PASS / exitCode 0
- known stderr noise: ESLint `nextVitals is not iterable`는 exit code 0이면 known issue로 기록

## 15. 다음 작업 제안
- TestWorkspace import-path-only update를 실제 이동 범위에 포함할지 사용자 확인.
- 승인되면 LIB-1E move step으로 한 파일 이동 + import path 업데이트만 수행.
- 이후 Clean JSON fixture lock, table_view_model fixture lock, typecheck/build를 실행.
