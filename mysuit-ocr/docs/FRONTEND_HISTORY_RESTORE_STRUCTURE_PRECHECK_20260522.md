# FRONTEND history/restore structure precheck

## 1. 사용 도구와 모델
- Tool: Codex
- Model: Codex
- Task: `CODEX_FRONTEND_HISTORY_RESTORE_STRUCTURE_PRECHECK_NO_PROD_MODIFY`

## 2. 코드 수정 여부
- codeModified: false
- 운영 코드 수정 없음
- 파일 이동/import 수정/rename/fixture/templates/backend 수정 없음

## 3. 생성 파일
- `tmp/codex_frontend_history_restore_structure_precheck.py`
- `docs/FRONTEND_HISTORY_RESTORE_STRUCTURE_PRECHECK_20260522.md`
- `docs/FRONTEND_HISTORY_RESTORE_STRUCTURE_PRECHECK_20260522.json`
- `docs/FRONTEND_HISTORY_RESTORE_STRUCTURE_MAP_20260522.csv`
- `ocr-server/logs/codex_CODEX_FRONTEND_HISTORY_RESTORE_STRUCTURE_PRECHECK_NO_PROD_MODIFY.out.log`
- `ocr-server/logs/codex_CODEX_FRONTEND_HISTORY_RESTORE_STRUCTURE_PRECHECK_NO_PROD_MODIFY.err.log`

## 4. 분석 범위
- history/autorestore components and routes
- related src/lib stores/profile/autofill/test files
- src/common, RunOCR, login RequireLogin, layout AppProviders
- TestWorkspace read-only

## 5. history 구조 분석
| file | role | target | risk | importedBy |
|---|---|---|---|---|
| `src/components/history/HistoryWorkspace.tsx` | History route workspace/list controller with create/edit/detail popup orchestration. | `src/components/history/HistoryWorkspace.tsx` | LOW | 0 |
| `src/components/history/DetailHistoryView.tsx` | History detail view, confirmed result editing, GT comparison, restore profile save/update actions. | `src/components/history/ui/DetailHistoryView.tsx` | MEDIUM | 1 |
| `src/components/history/popup/CreateHistoryPopup.tsx` | History create popup UI. | `src/components/history/ui/CreateHistoryPopup.tsx` | LOW | 1 |
| `src/components/history/popup/EditHistoryPopup.tsx` | History edit popup UI. | `src/components/history/ui/EditHistoryPopup.tsx` | LOW | 1 |
| `src/app/history/page.tsx` | Next route page wrapper. | `src/app/history/page.tsx` | MEDIUM | 0 |

## 6. restore/autorestore 구조 분석
| file | role | target | risk | importedBy |
|---|---|---|---|---|
| `src/components/autorestore/AutoRestoreWorkspace.tsx` | Restore/autofill profile management workspace. | `src/components/restore/RestoreWorkspace.tsx or src/components/restore/AutoRestoreWorkspace.tsx` | MEDIUM | 1 |
| `src/app/autorestore/page.tsx` | Next route page wrapper. | `src/app/autorestore/page.tsx` | LOW | 0 |

## 7. 관련 src/lib ownership 분석
| file | owner | target | risk | TestWorkspace |
|---|---|---|---|---|
| `src/lib/historyStore.ts` | history/utils | `src/components/history/utils/historyStore.ts` | HIGH | NO_TEST_IMPACT |
| `src/lib/imageStore.ts` | history/common boundary | `src/components/history/utils/imageStore.ts or src/common/utils/imageStore.ts` | HIGH | NO_TEST_IMPACT |
| `src/lib/restoreProfileStore.ts` | restore/utils | `src/components/restore/utils/restoreProfileStore.ts` | MEDIUM_HIGH | NO_TEST_IMPACT |
| `src/lib/profiles.ts` | test/restore shared policy | `DEFER: src/components/test/utils/profiles.ts or src/components/restore/utils/profiles.ts after separate precheck` | HIGH | DEFER_DUE_TO_TEST_WORKSPACE_POLICY |
| `src/lib/autofillEngine.ts` | shared domain util | `DEFER_SEPARATE_PRECHECK` | HIGH | NO_TEST_IMPACT |
| `src/lib/bizNumber.ts` | common/utils | `src/common/utils/bizNumber.ts` | HIGH | DEFER_DUE_TO_TEST_WORKSPACE_POLICY |
| `src/lib/groundTruthStore.ts` | test/utils | `DEFER: src/components/test/utils/groundTruthStore.ts` | HIGH | NO_TEST_IMPACT |
| `src/lib/testsets.ts` | test/utils | `DEFER: src/components/test/utils/testsets.ts` | HIGH | DEFER_DUE_TO_TEST_WORKSPACE_POLICY |


## 8. autofillEngine 특별 분석
- verdict: `DEFER_SEPARATE_PRECHECK`
- reason: Imports historyStore and restoreProfileStore at runtime and is consumed by RunOCR, History and common type formatting. Move after history/restore store ownership is settled.
- runtime consumers: 4
- type-only/common consumers include `ocrResultFormatters` if imported as types.

## 9. TestWorkspace 영향 분석
- profiles, bizNumber, groundTruthStore, testsets are TestWorkspace-coupled and should be deferred or approved as import-only work.
- history/restore UI moves do not require TestWorkspace logic changes.

## 10. target path 후보
- See JSON/CSV map for per-file candidates.

## 11. 위험도 분류
- LOW: history popup UI.
- MEDIUM: DetailHistoryView UI move, autorestore folder move.
- HIGH: stores, autofillEngine, TestWorkspace-coupled files.

## 12. 이동 순서 추천
- HR-1: history popup -> history/ui (LOW)
- HR-2: DetailHistoryView -> history/ui (MEDIUM)
- HR-3: historyStore ownership move precheck/move (HIGH)
- HR-4: imageStore separate precheck (HIGH)
- RS-1: autorestore folder -> restore precheck/move (MEDIUM)
- RS-2: restoreProfileStore move (MEDIUM_HIGH)
- RS-3: profiles separate precheck (HIGH)
- AF-1: autofillEngine separate ownership precheck (HIGH)
- BN-1: bizNumber common/utils precheck (HIGH)
- TEST-1: groundTruthStore/testsets defer until TestWorkspace approval (HIGH)

## 13. static check 설계
- target file exists and source absent after each move
- import paths resolve
- TestWorkspace is unchanged or import-path-only when explicitly approved
- common/utils imports no components/* path
- history/autorestore routes compile
- RunOCR boundary checks PASS
- LIB/common checks PASS
- typecheck/build PASS


## 14. dirty 상태
```text
 M docs/FRONTEND_CLEANUP_1B_JS_CLEAN_JSON_FIXTURE_RUNNER_20260521.json
 M docs/FRONTEND_CLEANUP_1B_JS_CLEAN_JSON_FIXTURE_RUNNER_20260521.md
 M docs/FRONTEND_CLEANUP_3D2_RUNNER_RESULT_20260521.json
 M src/app/autorestore/page.tsx
 M src/app/history/page.tsx
 M src/app/layout.tsx
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
 M src/components/autorestore/AutoRestoreWorkspace.tsx
 M src/components/history/DetailHistoryView.tsx
 M src/components/history/HistoryWorkspace.tsx
R  src/components/common/AppProviders.tsx -> src/components/layout/AppProviders.tsx
 M src/components/login/LoginWorkspace.tsx
R  src/components/common/RequireLogin.tsx -> src/components/login/ui/RequireLogin.tsx
 M src/components/runocr/RunOcrWorkspace.tsx
 M src/components/runocr/ui/OcrDocViewer.tsx
 M src/components/runocr/ui/OcrResultPanel.tsx
 M src/components/runocr/utils/buildOcrFormData.ts
 M src/components/template/TemplateWorkspace.tsx
 M src/components/template/UnstructuredBuilder.tsx
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
?? docs/FRONTEND_CC_1_APP_PROVIDERS_LAYOUT_MOVE_20260522.json
?? docs/FRONTEND_CC_1_APP_PROVIDERS_LAYOUT_MOVE_20260522.md
?? docs/FRONTEND_CC_2_REQUIRE_LOGIN_LOGIN_UI_MOVE_20260522.json
?? docs/FRONTEND_CC_2_REQUIRE_LOGIN_LOGIN_UI_MOVE_20260522.md
?? docs/FRONTEND_COMPONENTS_COMMON_ABSENT_CHECK_20260522.json
?? docs/FRONTEND_COMPONENTS_COMMON_ABSENT_CHECK_20260522.md
?? docs/FRONTEND_COMPONENTS_COMMON_OWNERSHIP_MAP_20260522.csv
?? docs/FRONTEND_COMPONENTS_COMMON_OWNERSHIP_PRECHECK_20260522.json
?? docs/FRONTEND_COMPONENTS_COMMON_OWNERSHIP_PRECHECK_20260522.md
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
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_APP_PROVIDERS_LAYOUT_MOVE_20260522_20260521.json
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_APP_PROVIDERS_LAYOUT_MOVE_20260522_20260521.md
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
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_REQUIRE_LOGIN_LOGIN_UI_MOVE_20260522_20260521.json
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_REQUIRE_LOGIN_LOGIN_UI_MOVE_20260522_20260521.md
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_TEMPLATE_ANNOTATOR_RENAME_20260522_20260521.json
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_TEMPLATE_ANNOTATOR_RENAME_20260522_20260521.md
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_TEMPLATE_EXPORT_PAYLOAD_MOVE_20260522_20260521.json
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_TEMPLATE_EXPORT_PAYLOAD_MOVE_20260522_20260521.md
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_TEMPLATE_RIGHT_PANEL_RENAME_20260522_20260521.json
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_TEMPLATE_RIGHT_PANEL_RENAME_20260522_20260521.md
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_VALIDATION_BASELINE_REPAIR_20260522_20260521.json
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_VALIDATION_BASELINE_REPAIR_20260522_20260521.md
?? tmp/check_app_providers_layout_move_cc1.mjs
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
?? tmp/check_require_login_login_ui_move_cc2.mjs
?? tmp/check_template_annotator_rename_6b.mjs
?? tmp/check_template_export_payload_move_5d.mjs
?? tmp/check_template_right_panel_rename_6a.mjs
?? tmp/check_validation_baseline_repair_1a.mjs
?? tmp/codex_frontend_components_common_absent_check.py
?? tmp/codex_frontend_components_common_ownership_precheck.py
?? tmp/codex_frontend_filedropzone_common_ui_precheck.py
?? tmp/codex_frontend_history_restore_structure_precheck.py
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

## 15. typecheck/build 결과
- typecheck: PASS / exitCode 0
- build: PASS / exitCode 0
- known stderr noise: ESLint `nextVitals is not iterable`는 exit code 0이면 known issue

## 16. 다음 작업 제안
- HR-1 history popup -> history/ui move precheck/move부터 진행.
- autofillEngine, bizNumber, groundTruthStore/testsets는 별도 precheck 또는 TestWorkspace 승인 후 진행.
