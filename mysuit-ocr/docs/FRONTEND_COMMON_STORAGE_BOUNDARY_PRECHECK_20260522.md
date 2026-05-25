# FRONTEND_COMMON_STORAGE_BOUNDARY_PRECHECK_20260522

## 1. 사용 도구와 모델
- 사용 도구: Codex
- 사용 모델: Codex
- 작업명: CODEX_FRONTEND_COMMON_STORAGE_BOUNDARY_PRECHECK_NO_PROD_MODIFY

## 2. 코드 수정 여부
- 운영 코드 수정: 없음
- 파일 이동/rename/import 수정: 없음
- fixture/templates/backend 수정: 없음
- 생성 가능한 precheck 산출물만 작성했다.

## 3. 생성 파일
- tmp/codex_frontend_common_storage_boundary_precheck.py
- docs/FRONTEND_COMMON_STORAGE_BOUNDARY_PRECHECK_20260522.md
- docs/FRONTEND_COMMON_STORAGE_BOUNDARY_PRECHECK_20260522.json
- docs/FRONTEND_COMMON_STORAGE_BOUNDARY_MAP_20260522.csv

## 4. 분석 범위
- src/lib/historyStore.ts
- src/lib/imageStore.ts
- src/lib/autofillEngine.ts
- src/lib/groundTruthStore.ts
- src/lib/restoreProfileStore.ts
- src/lib/profiles.ts
- src/lib/bizNumber.ts
- src/lib/testsets.ts
- src/components/runocr/**
- src/components/history/**
- src/components/autorestore/**
- src/components/restore/**
- src/components/template/**
- src/components/test/TestWorkspace.tsx
- src/components/test/core/**
- src/common/**
- src/app/**

## 5. storage/data 후보 파일 역할 분석
| 파일 | 추천 owner | 추천 target | 위험 | TestWorkspace 영향 |
| --- | --- | --- | --- | --- |
| src/lib/historyStore.ts | common/storage | src/common/storage/historyStore.ts | HIGH | NO_TEST_IMPACT |
| src/lib/imageStore.ts | common/storage | src/common/storage/imageStore.ts | MEDIUM_HIGH | NO_TEST_IMPACT |
| src/lib/autofillEngine.ts | defer separate precheck | DEFER_UNTIL_STORAGE_BOUNDARY | HIGH | TEST_WORKSPACE_DIRECT_IMPORT_BUT_SAFE_IMPORT_PATH_ONLY |
| src/lib/groundTruthStore.ts | defer/test-aware | DEFER_UNTIL_TEST_WORKSPACE_APPROVAL or src/common/storage/groundTruthStore.ts | HIGH | DEFER_DUE_TO_TEST_WORKSPACE_POLICY |
| src/lib/restoreProfileStore.ts | restore/utils or common/storage | src/components/restore/utils/restoreProfileStore.ts after restore boundary OR src/common/storage/restoreProfileStore.ts | MEDIUM_HIGH | NO_TEST_IMPACT |
| src/lib/profiles.ts | restore/data or defer | src/components/restore/utils/profiles.ts or src/common/data/profiles.ts | MEDIUM | TEST_WORKSPACE_DIRECT_IMPORT_BUT_SAFE_IMPORT_PATH_ONLY |
| src/lib/bizNumber.ts | common/utils | src/common/utils/bizNumber.ts | MEDIUM | TEST_WORKSPACE_DIRECT_IMPORT_BUT_SAFE_IMPORT_PATH_ONLY |
| src/lib/testsets.ts | test/utils defer | src/components/test/utils/testsets.ts after user approval | HIGH | TEST_WORKSPACE_DIRECT_IMPORT_BUT_SAFE_IMPORT_PATH_ONLY |

## 6. autofillEngine 특별 분석
- 판정: DEFER_UNTIL_STORAGE_BOUNDARY
- moveRisk: HIGH
- historyStore 의존: True
- restoreProfileStore 의존: True
- bizNumber 의존: True
- common/storage 적합성: No: domain engine, not persistence store
- common/utils 적합성: Not yet
- restore/utils 적합성: No: consumed by RunOCR and History
- runocr/utils 적합성: No: consumed by History/detail and restore profile flow
- 결론: storage boundary가 먼저 정리된 뒤 별도 precheck로 이동 여부를 판단한다.

## 7. importedBy/dependency graph
### dependency edges
- src/lib/historyStore.ts -> src/lib/imageStore.ts (runtime, ./imageStore)
- src/lib/autofillEngine.ts -> src/lib/bizNumber.ts (runtime, ./bizNumber)
- src/lib/autofillEngine.ts -> src/lib/historyStore.ts (runtime, ./historyStore)
- src/lib/autofillEngine.ts -> src/lib/restoreProfileStore.ts (runtime, ./restoreProfileStore)
- src/lib/groundTruthStore.ts -> src/lib/historyStore.ts (type-only, ./historyStore)
- src/lib/profiles.ts -> src/lib/testsets.ts (type-only, ./testsets)

### graph risk
- cycleRisk: MEDIUM: autofillEngine depends on historyStore/restoreProfileStore; moving stores into feature folders would create cross-feature imports.
- sharedBoundaryRisk: HIGH without common/storage; LOW_MEDIUM if browser persistence files move into common/storage.
- featureDependencyRisk: historyStore in components/history/utils would force RunOCR and autofillEngine to import history feature code.

## 8. common/storage vs common/data 판단
- 추천 boundary: src/common/storage/
- 이유: localStorage/IndexedDB/browser persistence 책임이 있는 파일을 common/utils와 분리하면서 feature 간 의존을 줄인다.
- src/common/data/는 순수 data/model 정의에는 가능하지만 historyStore/imageStore 같은 persistence store에는 덜 명확하다.
- src/common/utils/는 formatter/display/pure helper 중심으로 유지하는 것이 좋다.

## 9. 파일별 target 추천
- historyStore.ts -> src/common/storage/historyStore.ts 후보
- imageStore.ts -> src/common/storage/imageStore.ts 후보
- restoreProfileStore.ts -> restore boundary 확정 후 components/restore/utils 또는 common/storage 재판단
- profiles.ts -> Test/restore 영향 확인 후 보류 또는 common/data/components/restore/utils
- groundTruthStore.ts -> TestWorkspace 정책상 보류 또는 common/storage 별도 precheck
- testsets.ts -> TestWorkspace 승인 전 보류
- bizNumber.ts -> src/common/utils/bizNumber.ts 별도 precheck
- autofillEngine.ts -> storage boundary 이후 별도 precheck

## 10. TestWorkspace 영향
- historyStore: NO_TEST_IMPACT
- imageStore: NO_TEST_IMPACT
- autofillEngine: TEST_WORKSPACE_DIRECT_IMPORT_BUT_SAFE_IMPORT_PATH_ONLY
- groundTruthStore: DEFER_DUE_TO_TEST_WORKSPACE_POLICY
- restoreProfileStore: NO_TEST_IMPACT
- profiles: TEST_WORKSPACE_DIRECT_IMPORT_BUT_SAFE_IMPORT_PATH_ONLY
- testsets: TEST_WORKSPACE_DIRECT_IMPORT_BUT_SAFE_IMPORT_PATH_ONLY
- bizNumber: TEST_WORKSPACE_DIRECT_IMPORT_BUT_SAFE_IMPORT_PATH_ONLY

## 11. 이동 순서 추천
- CS-0: common/storage boundary decision (src/common/storage/) - precheck only in this task
- CS-1: imageStore common/storage move (src/lib/imageStore.ts) - leaf-ish IndexedDB store, history/template consumers
- CS-2: historyStore common/storage move (src/lib/historyStore.ts) - after imageStore so sibling storage import is natural
- RS-1: restore/autorestore folder boundary (src/components/autorestore/**) - separate route/feature precheck
- RS-2: restoreProfileStore ownership (src/lib/restoreProfileStore.ts) - restore/utils vs common/storage after restore boundary
- AF-1: autofillEngine separate precheck (src/lib/autofillEngine.ts) - after storage paths settle
- BZ-1: bizNumber common/utils precheck (src/lib/bizNumber.ts) - pure util candidate, check Test impact
- TEST-1: TestWorkspace-approved moves (src/lib/groundTruthStore.ts, src/lib/testsets.ts, src/lib/profiles.ts) - user approval before TestWorkspace structure changes

## 12. static check 설계
- tmp/check_common_storage_boundary_cs0.mjs
- tmp/check_image_store_common_storage_move_cs1.mjs
- tmp/check_history_store_common_storage_move_cs2.mjs
- tmp/check_restore_profile_store_move_rs2.mjs
- tmp/check_autofill_engine_ownership_af1.mjs
- target 파일 존재/source 파일 부재/import path 정상
- common/storage가 components/*를 import하지 않음
- storage 파일과 common/utils 간 순환 없음
- TestWorkspace 미수정 또는 import-only 확인
- RunOCR/History/Template import path 정상
- npm run typecheck PASS
- npm run build PASS

## 13. dirty 상태
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
 M src/components/history/HistoryWorkspace.tsx
R  src/components/history/popup/CreateHistoryPopup.tsx -> src/components/history/ui/CreateHistoryPopup.tsx
RM src/components/history/DetailHistoryView.tsx -> src/components/history/ui/DetailHistoryView.tsx
R  src/components/history/popup/EditHistoryPopup.tsx -> src/components/history/ui/EditHistoryPopup.tsx
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
?? docs/FRONTEND_DETAIL_HISTORY_VIEW_UI_MOVE_PRECHECK_20260522.json
?? docs/FRONTEND_DETAIL_HISTORY_VIEW_UI_MOVE_PRECHECK_20260522.md
?? docs/FRONTEND_DETAIL_HISTORY_VIEW_UI_MOVE_PRECHECK_MAP_20260522.csv
?? docs/FRONTEND_FILEDROPZONE_COMMON_UI_PRECHECK_20260522.json
?? docs/FRONTEND_FILEDROPZONE_COMMON_UI_PRECHECK_20260522.md
?? docs/FRONTEND_FILEDROPZONE_COMMON_UI_PRECHECK_MAP_20260522.csv
?? docs/FRONTEND_HISTORY_RESTORE_STRUCTURE_MAP_20260522.csv
?? docs/FRONTEND_HISTORY_RESTORE_STRUCTURE_PRECHECK_20260522.json
?? docs/FRONTEND_HISTORY_RESTORE_STRUCTURE_PRECHECK_20260522.md
?? docs/FRONTEND_HISTORY_STORE_OWNERSHIP_PRECHECK_20260522.json
?? docs/FRONTEND_HISTORY_STORE_OWNERSHIP_PRECHECK_20260522.md
?? docs/FRONTEND_HISTORY_STORE_OWNERSHIP_PRECHECK_MAP_20260522.csv
?? docs/FRONTEND_HR_1_HISTORY_POPUP_UI_MOVE_20260522.json
?? docs/FRONTEND_HR_1_HISTORY_POPUP_UI_MOVE_20260522.md
?? docs/FRONTEND_HR_2_DETAIL_HISTORY_VIEW_UI_MOVE_20260522.json
?? docs/FRONTEND_HR_2_DETAIL_HISTORY_VIEW_UI_MOVE_20260522.md
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
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_DETAIL_HISTORY_VIEW_UI_MOVE_20260522_20260521.json
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_DETAIL_HISTORY_VIEW_UI_MOVE_20260522_20260521.md
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_FILEDROPZONE_COMMON_UI_MOVE_20260522_20260521.json
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_FILEDROPZONE_COMMON_UI_MOVE_20260522_20260521.md
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_HISTORY_POPUP_UI_MOVE_20260522_20260521.json
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_HISTORY_POPUP_UI_MOVE_20260522_20260521.md
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
?? tmp/check_detail_history_view_ui_move_hr2.mjs
?? tmp/check_filedropzone_common_ui_move_5e.mjs
?? tmp/check_history_popup_ui_move_hr1.mjs
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
?? tmp/codex_frontend_common_storage_boundary_precheck.py
?? tmp/codex_frontend_components_common_absent_check.py
?? tmp/codex_frontend_components_common_ownership_precheck.py
?? tmp/codex_frontend_detail_history_view_ui_move_precheck.py
?? tmp/codex_frontend_filedropzone_common_ui_precheck.py
?? tmp/codex_frontend_history_restore_structure_precheck.py
?? tmp/codex_frontend_history_store_ownership_precheck.py
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

## 14. typecheck/build 결과
- typecheck: PASS (exitCode=0)
- build: PASS (exitCode=0)
- known stderr noise: ESLint nextVitals is not iterable은 exit code 0이면 known issue로 기록.

## 15. 다음 작업 제안
- src/common/storage boundary를 도입하는 방향을 확정한다.
- 첫 move는 imageStore -> common/storage가 가장 자연스럽다.
- 그 다음 historyStore -> common/storage를 진행한다.
- autofillEngine과 TestWorkspace 관련 파일은 별도 precheck/승인 후 진행한다.
