# FRONTEND components/common ownership precheck

## 1. 사용 도구와 모델
- Tool: Codex
- Model: Codex
- Task: `CODEX_FRONTEND_COMPONENTS_COMMON_OWNERSHIP_PRECHECK_NO_PROD_MODIFY`

## 2. 코드 수정 여부
- codeModified: false
- 운영 코드 수정 없음
- 파일 이동/import 수정/rename/fixture/templates/backend 수정 없음

## 3. 생성 파일
- `tmp/codex_frontend_components_common_ownership_precheck.py`
- `docs/FRONTEND_COMPONENTS_COMMON_OWNERSHIP_PRECHECK_20260522.md`
- `docs/FRONTEND_COMPONENTS_COMMON_OWNERSHIP_PRECHECK_20260522.json`
- `docs/FRONTEND_COMPONENTS_COMMON_OWNERSHIP_MAP_20260522.csv`
- `ocr-server/logs/codex_CODEX_FRONTEND_COMPONENTS_COMMON_OWNERSHIP_PRECHECK_NO_PROD_MODIFY.out.log`
- `ocr-server/logs/codex_CODEX_FRONTEND_COMPONENTS_COMMON_OWNERSHIP_PRECHECK_NO_PROD_MODIFY.err.log`

## 4. 분석 범위
- `src/components/common/AppProviders.tsx`
- `src/components/common/RequireLogin.tsx`
- `src/app/**`
- `src/components/runocr/**`, `template/**`, `history/**`, `restore/**`, `autorestore/**`, `login/**`, `layout/**`
- `src/components/test/TestWorkspace.tsx` 읽기 전용
- `src/common/**`
- `src/lib/**`

## 5. AppProviders 역할/import 영향
- currentPath: `src/components/common/AppProviders.tsx`
- lineCount: 362
- recommendation: `src/components/layout/AppProviders.tsx`
- 역할: Global UI provider/context for loading overlay and alert/confirm modal API.
- Provider/global UI state/context: true
- common/ui 적합성: Possible but weaker than layout because it is an app-level provider, not a reusable leaf UI component.
- layout 적합성: Strong fit.

| importedBy | importPath | feature | TestWorkspace |
|---|---|---|---|
| `src/app/layout.tsx` | `../components/common/AppProviders` | app | False |
| `src/app/layout.tsx` | `components/common/AppProviders` | app | False |
| `src/components/autorestore/AutoRestoreWorkspace.tsx` | `../common/AppProviders` | restore | False |
| `src/components/history/DetailHistoryView.tsx` | `../common/AppProviders` | history | False |
| `src/components/history/HistoryWorkspace.tsx` | `../common/AppProviders` | history | False |
| `src/components/login/LoginWorkspace.tsx` | `../common/AppProviders` | login | False |
| `src/components/runocr/RunOcrWorkspace.tsx` | `../common/AppProviders` | runocr | False |
| `src/components/runocr/ui/OcrResultPanel.tsx` | `../common/AppProviders` | runocr | False |
| `src/components/runocr/ui/OcrResultPanel.tsx` | `../../common/AppProviders` | runocr | False |
| `src/components/template/TemplateWorkspace.tsx` | `../common/AppProviders` | template | False |
| `src/components/template/ui/TemplateAnnotator.tsx` | `../common/AppProviders` | template | False |
| `src/components/template/ui/TemplateAnnotator.tsx` | `../../common/AppProviders` | template | False |
| `src/components/template/UnstructuredBuilder.tsx` | `../common/AppProviders` | template | False |
| `src/components/test/TestWorkspace.tsx` | `../common/AppProviders` | test | True |


## 6. RequireLogin 역할/import 영향
- currentPath: `src/components/common/RequireLogin.tsx`
- lineCount: 35
- recommendation: `src/components/login/ui/RequireLogin.tsx`
- 역할: Client-side auth guard that checks stored login state and redirects unauthenticated users to /login.
- auth guard / route protection / login feature policy: true
- common/ui 적합성: Weak: it imports login/auth policy and is not generic UI.
- login/ui 적합성: Strong fit.

| importedBy | importPath | feature | TestWorkspace |
|---|---|---|---|
| `src/app/autorestore/page.tsx` | `@/components/common/RequireLogin` | app | False |
| `src/app/autorestore/page.tsx` | `components/common/RequireLogin` | app | False |
| `src/app/history/page.tsx` | `@/components/common/RequireLogin` | app | False |
| `src/app/history/page.tsx` | `components/common/RequireLogin` | app | False |


## 7. target path 후보 비교
### AppProviders
| target | risk | recommended | route/common boundary |
|---|---|---|---|
| `src/components/layout/AppProviders.tsx` | MEDIUM | True | src/app/layout.tsx import path only / LOW |
| `src/common/ui/AppProviders.tsx` | MEDIUM | False | src/app/layout.tsx import path only / LOW if no components/* import, but semantic fit is weaker |
| `src/common/utils/AppProviders.tsx` | HIGH | False | path only / MEDIUM |
| `src/components/common 유지` | LOW | False | none / LOW |
| `보류` | LOW | False | none / LOW |


### RequireLogin
| target | risk | recommended | route/common boundary |
|---|---|---|---|
| `src/components/login/ui/RequireLogin.tsx` | LOW_MEDIUM | True | route wrapper import path only / LOW |
| `src/components/login/RequireLogin.tsx` | LOW_MEDIUM | False | path only / LOW |
| `src/common/ui/RequireLogin.tsx` | MEDIUM | False | path only / MEDIUM semantic boundary risk |
| `src/components/layout/RequireLogin.tsx` | MEDIUM | False | path only / LOW |
| `src/components/common 유지` | LOW | False | none / LOW |
| `보류` | LOW | False | none / LOW |


## 8. TestWorkspace 영향
- AppProviders: `TEST_WORKSPACE_DIRECT_IMPORT_BUT_SAFE_IMPORT_PATH_ONLY`
- RequireLogin: `NO_TEST_IMPACT`
- AppProviders 이동 시 `TestWorkspace.tsx`는 import path-only 수정 후보다. 로직 수정은 필요하지 않다.

## 9. 이동 순서 추천
- CC-1: `AppProviders.tsx` -> `src/components/layout/AppProviders.tsx`
- CC-2: `RequireLogin.tsx` -> `src/components/login/ui/RequireLogin.tsx`
- CC-3: `src/components/common` empty/absent 확인
- 둘은 target ownership이 다르므로 함께 이동보다 분리 micro-step을 권장한다.

## 10. static check 설계
- target files exist
- source files absent after move
- src/components/common is empty or absent
- import paths resolve
- common/ui files do not import components/*
- TestWorkspace changes are import-path-only if AppProviders moves
- RunOCR/Template checks PASS
- LIB checks PASS
- typecheck/build PASS


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
RM src/lib/cleanJsonBuilder.ts -> src/common/utils/cleanJsonBuilder.ts
R  src/lib/invoiceFieldLabels.ts -> src/common/utils/invoiceFieldLabels.ts
R  src/lib/invoiceTableDisplay.ts -> src/common/utils/invoiceTableDisplay.ts
RM src/lib/markdownReportBuilder.ts -> src/common/utils/markdownReportBuilder.ts
RM src/components/ocr/core/ops.ts -> src/common/utils/ocrCanvasOps.ts
RM src/lib/ocrResultFormatters.ts -> src/common/utils/ocrResultFormatters.ts
RM src/components/ocr/core/table.ts -> src/common/utils/ocrTableRegion.ts
R  src/lib/structuredTableViewModel.ts -> src/common/utils/structuredTableViewModel.ts
 M src/components/history/DetailHistoryView.tsx
 M src/components/runocr/RunOcrWorkspace.tsx
 M src/components/runocr/ui/OcrDocViewer.tsx
 M src/components/runocr/ui/OcrResultPanel.tsx
 M src/components/runocr/utils/buildOcrFormData.ts
RM src/components/template/ui/OcrAnnotator.tsx -> src/components/template/ui/TemplateAnnotator.tsx
RM src/components/template/ui/OcrRightPanel.tsx -> src/components/template/ui/TemplateRightPanel.tsx
RM src/components/ocr/core/export.ts -> src/components/template/utils/buildTemplateExportPayload.ts
 M src/components/test/TestWorkspace.tsx
 M tmp/check_clean_json_v1_fixtures_js.mjs
 M tmp/check_runocr_doc_comments_3b.mjs
 M tmp/check_runocr_formdata_keys_2a.mjs
 M tmp/check_runocr_response_mapping_boundary_2c.mjs
 M tmp/check_table_view_model_v1_fixtures_js.mjs
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
?? docs/FRONTEND_LIB_1E_INVOICE_TABLE_DISPLAY_COMMON_MOVE_20260522.json
?? docs/FRONTEND_LIB_1E_INVOICE_TABLE_DISPLAY_COMMON_MOVE_20260522.md
?? docs/FRONTEND_LIB_1F_STRUCTURED_TABLE_VIEW_MODEL_COMMON_MOVE_20260522.json
?? docs/FRONTEND_LIB_1F_STRUCTURED_TABLE_VIEW_MODEL_COMMON_MOVE_20260522.md
?? docs/FRONTEND_LIB_CLEAN_JSON_BUILDER_COMMON_MOVE_PRECHECK_20260522.json
?? docs/FRONTEND_LIB_CLEAN_JSON_BUILDER_COMMON_MOVE_PRECHECK_20260522.md
?? docs/FRONTEND_LIB_CLEAN_JSON_BUILDER_COMMON_MOVE_PRECHECK_MAP_20260522.csv
?? docs/FRONTEND_LIB_INVOICE_FIELD_LABELS_COMMON_MOVE_PRECHECK_20260522.json
?? docs/FRONTEND_LIB_INVOICE_FIELD_LABELS_COMMON_MOVE_PRECHECK_20260522.md
?? docs/FRONTEND_LIB_INVOICE_FIELD_LABELS_COMMON_MOVE_PRECHECK_MAP_20260522.csv
?? docs/FRONTEND_LIB_INVOICE_TABLE_DISPLAY_COMMON_MOVE_PRECHECK_20260522.json
?? docs/FRONTEND_LIB_INVOICE_TABLE_DISPLAY_COMMON_MOVE_PRECHECK_20260522.md
?? docs/FRONTEND_LIB_INVOICE_TABLE_DISPLAY_COMMON_MOVE_PRECHECK_MAP_20260522.csv
?? docs/FRONTEND_LIB_MARKDOWN_REPORT_BUILDER_COMMON_MOVE_PRECHECK_20260522.json
?? docs/FRONTEND_LIB_MARKDOWN_REPORT_BUILDER_COMMON_MOVE_PRECHECK_20260522.md
?? docs/FRONTEND_LIB_MARKDOWN_REPORT_BUILDER_COMMON_MOVE_PRECHECK_MAP_20260522.csv
?? docs/FRONTEND_LIB_OCR_RESULT_FORMATTERS_COMMON_MOVE_PRECHECK_20260522.json
?? docs/FRONTEND_LIB_OCR_RESULT_FORMATTERS_COMMON_MOVE_PRECHECK_20260522.md
?? docs/FRONTEND_LIB_OCR_RESULT_FORMATTERS_COMMON_MOVE_PRECHECK_MAP_20260522.csv
?? docs/FRONTEND_LIB_OWNERSHIP_MAP_20260522.csv
?? docs/FRONTEND_LIB_OWNERSHIP_PRECHECK_20260522.json
?? docs/FRONTEND_LIB_OWNERSHIP_PRECHECK_20260522.md
?? docs/FRONTEND_LIB_STRUCTURED_TABLE_VIEW_MODEL_COMMON_MOVE_PRECHECK_20260522.json
?? docs/FRONTEND_LIB_STRUCTURED_TABLE_VIEW_MODEL_COMMON_MOVE_PRECHECK_20260522.md
?? docs/FRONTEND_LIB_STRUCTURED_TABLE_VIEW_MODEL_COMMON_MOVE_PRECHECK_MAP_20260522.csv
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
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_LIB_INVOICE_TABLE_DISPLAY_COMMON_MOVE_20260522_20260521.json
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_LIB_INVOICE_TABLE_DISPLAY_COMMON_MOVE_20260522_20260521.md
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_LIB_MARKDOWN_REPORT_BUILDER_COMMON_MOVE_20260522_20260521.json
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_LIB_MARKDOWN_REPORT_BUILDER_COMMON_MOVE_20260522_20260521.md
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_LIB_OCR_RESULT_FORMATTERS_COMMON_MOVE_20260522_20260521.json
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_LIB_OCR_RESULT_FORMATTERS_COMMON_MOVE_20260522_20260521.md
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_LIB_STRUCTURED_TABLE_VIEW_MODEL_COMMON_MOVE_20260522_20260521.json
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_LIB_STRUCTURED_TABLE_VIEW_MODEL_COMMON_MOVE_20260522_20260521.md
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
?? tmp/check_lib_invoice_table_display_common_move_1e.mjs
?? tmp/check_lib_markdown_report_builder_common_move_1c.mjs
?? tmp/check_lib_ocr_result_formatters_common_move_1a.mjs
?? tmp/check_lib_structured_table_view_model_common_move_1f.mjs
?? tmp/check_ocr_canvas_pane_common_ui_move_5f.mjs
?? tmp/check_ocr_core_ops_common_move_5b.mjs
?? tmp/check_ocr_core_table_common_move_5c.mjs
?? tmp/check_ocr_core_types_common_move_5a.mjs
?? tmp/check_template_annotator_rename_6b.mjs
?? tmp/check_template_export_payload_move_5d.mjs
?? tmp/check_template_right_panel_rename_6a.mjs
?? tmp/check_validation_baseline_repair_1a.mjs
?? tmp/codex_frontend_components_common_ownership_precheck.py
?? tmp/codex_frontend_filedropzone_common_ui_precheck.py
?? tmp/codex_frontend_lib_clean_json_builder_common_move_precheck.py
?? tmp/codex_frontend_lib_invoice_field_labels_common_move_precheck.py
?? tmp/codex_frontend_lib_invoice_table_display_common_move_precheck.py
?? tmp/codex_frontend_lib_markdown_report_builder_common_move_precheck.py
?? tmp/codex_frontend_lib_ocr_result_formatters_common_move_precheck.py
?? tmp/codex_frontend_lib_ownership_precheck.py
?? tmp/codex_frontend_lib_structured_table_view_model_common_move_precheck.py
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

## 12. typecheck/build 결과
- typecheck: PASS / exitCode 0
- build: PASS / exitCode 0
- known stderr noise: ESLint `nextVitals is not iterable`는 exit code 0이면 known issue

## 13. 다음 작업 제안
- AppProviders layout 이동을 먼저 별도 step으로 진행.
- RequireLogin login/ui 이동은 다음 별도 step으로 진행.
- 마지막에 components/common empty check를 수행.
