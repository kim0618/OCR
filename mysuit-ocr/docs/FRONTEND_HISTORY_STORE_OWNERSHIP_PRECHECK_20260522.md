# FRONTEND_HISTORY_STORE_OWNERSHIP_PRECHECK_20260522

## 1. 사용 도구와 모델
- 사용 도구: Codex
- 사용 모델: Codex
- 작업명: CODEX_FRONTEND_HISTORY_STORE_OWNERSHIP_PRECHECK_NO_PROD_MODIFY

## 2. 코드 수정 여부
- 운영 코드 수정: 없음
- 파일 이동/rename/import 수정: 없음
- fixture/templates/backend 수정: 없음
- 생성 가능한 precheck 산출물만 작성했다.

## 3. 생성 파일
- tmp/codex_frontend_history_store_ownership_precheck.py
- docs/FRONTEND_HISTORY_STORE_OWNERSHIP_PRECHECK_20260522.md
- docs/FRONTEND_HISTORY_STORE_OWNERSHIP_PRECHECK_20260522.json
- docs/FRONTEND_HISTORY_STORE_OWNERSHIP_PRECHECK_MAP_20260522.csv

## 4. 분석 범위
- src/lib/historyStore.ts
- src/lib/imageStore.ts
- src/lib/restoreProfileStore.ts
- src/lib/autofillEngine.ts
- src/lib/profiles.ts
- src/components/history/**
- src/components/runocr/**
- src/components/autorestore/**
- src/components/restore/**
- src/app/history/**
- src/app/runocr/**
- src/components/test/TestWorkspace.tsx
- src/components/test/core/**
- src/common/**

## 5. historyStore 역할 요약
- currentPath: src/lib/historyStore.ts
- lineCount: 807
- imports: [{"symbols": "{ saveImage as idbSaveImage, getImage as idbGetImage, deleteImagesFor as idbDeleteImagesFor }", "source": "./imageStore", "typeOnly": false}]
- exports: type RunStatus, type HistoryOcrField, type HistoryOutputField, type HistoryAutofillRunSummary, type HistoryImageStorageMode, type HistoryRunRecord, function getOriginalHistoryImage, function getProcessedHistoryImage, function readHistoryRuns, function appendHistoryRun, function updateHistoryRun, function clearHistoryRuns, function deleteHistoryRun, const HISTORY_INDEX_KEY, const HISTORY_DETAILS_KEY, type HistoryIndexSummary, type HistoryIndexItem, type HistoryDetailDocumentFields, type HistoryDetailRecord, function readHistoryIndex, function readHistoryDetails, function buildHistoryIndexItem, function buildHistoryDetail, function syncHistoryIndexAndDetailOnCreate, function syncHistoryDetailTableRowsOnSave, function syncHistoryIndexAndDetailOnSave, function readHistoryListWithFallback, function detailToHistoryRunRecord, function readHistoryDetailWithFallback
- mainResponsibility: browser-side OCR history persistence store. legacy list, index/detail records, append/update/delete/clear, image hydration, sync helpers를 제공한다.
- 저장소 성격: YES
- localStorage/IndexedDB/browser API: YES
- backend/API: NO
- React 의존: NO
- components/* 의존: NO
- History 전용성: NO. History 화면뿐 아니라 RunOCR 저장 흐름과 autofill 후보 수집에서 runtime으로 공유된다.
- moveRisk: HIGH

## 6. importedBy 분석
- src/components/history/HistoryWorkspace.tsx:9 [history, type-only] import { readHistoryListWithFallback, readHistoryDetailWithFallback, deleteHistoryRun, clearHistoryRuns, hydrateHistoryRecordImages, type RunStatus, type HistoryRunRecord } from "@/lib/historyStore";
- src/components/runocr/RunOcrWorkspace.tsx:37 [runocr, type-only] import { appendHistoryRun, updateHistoryRun, syncHistoryIndexAndDetailOnCreate, type HistoryDetailDocumentFields, type HistoryOcrField, type HistoryOutputField } from "@/lib/historyStore";
- src/lib/groundTruthStore.ts:5 [lib, type-only] import type { HistoryOutputField } from "./historyStore";
- src/lib/autofillEngine.ts:2 [lib, type-only] import { readHistoryRuns, type HistoryOutputField } from "./historyStore";

주요 production consumer:
- RunOCR: appendHistoryRun, updateHistoryRun, syncHistoryIndexAndDetailOnCreate 및 History type들을 runtime/type으로 사용한다.
- HistoryWorkspace: list/detail read, delete/clear, image hydration을 사용한다.
- DetailHistoryView: updateHistoryRun, syncHistoryDetailTableRowsOnSave, syncHistoryIndexAndDetailOnSave 및 History type들을 사용한다.
- autofillEngine: readHistoryRuns를 runtime으로 import한다.
- groundTruthStore: HistoryOutputField를 type-only로 import한다.

## 7. dependency 영향
- historyStore -> imageStore runtime import: True
- historyStore -> restoreProfileStore direct import: False
- historyStore -> autofillEngine direct import: True
- historyStore -> common/utils direct import: False
- 순환 의존 가능성: direct cycle은 없지만, history/utils로 이동하면 src/lib/autofillEngine -> components/history/utils runtime import가 생겨 boundary 위험이 커진다.
- RunOCR가 history 저장을 위해 historyStore를 runtime 사용하므로, components/history/utils로 이동하면 components/runocr -> components/history/utils feature dependency가 생긴다.

## 8. TestWorkspace 영향
- 판정: NO_TEST_IMPACT
- TestWorkspace 직접 import: False
- test/core 직접 import: False
- 이동 시 TestWorkspace 수정 필요: False

## 9. target path 비교
| 후보 | 추천 | 장점 | 단점 | feature dependency risk |
| --- | --- | --- | --- | --- |
| src/components/history/utils/historyStore.ts | NO | History UI/route와 이름상 맞음 | RunOCR/autofillEngine이 history feature를 runtime import | HIGH |
| src/common/utils/historyStore.ts | NO | feature dependency는 줄어듦 | stateful persistence store라 utils 의미가 약함 | LOW_MEDIUM |
| src/common/storage/historyStore.ts 또는 src/common/data/historyStore.ts | YES, 별도 precheck 후 | shared persistence boundary로 가장 자연스러움 | 새 common boundary 설계 필요 | LOW |
| src/lib 유지 | YES, 당장 유지 후보 | 새 feature dependency를 만들지 않음 | src/lib 정리 지연 | CURRENT |
| 보류 | YES | imageStore/autofillEngine ownership 정리 후 판단 가능 | 즉시 이동 없음 | LOW |

## 10. 실제 이동 추천
- 추천 선택지: D. 이동 보류
- 대안: B. common storage/data 계층을 별도 precheck로 먼저 정의한 뒤 이동
- 비추천: A. historyStore.ts만 src/components/history/utils/historyStore.ts로 이동
- 이유: 단독 history/utils 이동은 RunOCR와 src/lib/autofillEngine에 history feature dependency를 만든다.
- imageStore와 묶지 않고, RunOCR history adapter 분리도 이번 작업에 묶지 않는다.

## 11. static check 설계
- tmp/check_history_store_move_hr3.mjs
- target 파일 존재 및 source 파일 부재 확인
- historyStore exports 유지 확인
- RunOCR/History/autofillEngine/groundTruthStore import path 정상 확인
- components/runocr가 components/history/utils를 import하지 않음 확인, 또는 의도된 예외로 명시
- src/lib/autofillEngine이 components/history/utils를 runtime import하지 않음 확인
- TestWorkspace 미수정 또는 import-only 영향 없음 확인
- imageStore/restoreProfileStore/autofillEngine 미수정 확인
- npm run typecheck PASS
- npm run build PASS

## 12. dirty 상태
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

## 13. typecheck/build 결과
- typecheck: PASS (exitCode=0)
- build: PASS (exitCode=0)
- known stderr noise: ESLint nextVitals is not iterable은 exit code 0이면 known issue로 기록.

## 14. 다음 작업 제안
- common storage/data boundary precheck를 먼저 수행한다.
- historyStore/imageStore/autofillEngine의 공유 저장소 경계를 함께 검토하되 실제 move는 한 파일씩 진행한다.
- Template table column definition 진입 전에는 historyStore를 무리하게 history/utils로 옮기지 않는 편이 안전하다.
