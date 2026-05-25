# FRONTEND_DETAIL_HISTORY_VIEW_UI_MOVE_PRECHECK_20260522

## 1. 사용 도구와 모델
- 사용 도구: Codex
- 사용 모델: Codex
- 작업명: CODEX_FRONTEND_DETAIL_HISTORY_VIEW_UI_MOVE_PRECHECK_NO_PROD_MODIFY

## 2. 코드 수정 여부
- 운영 코드 수정: 없음
- 파일 이동/rename/import 수정: 없음
- fixture/templates/backend 수정: 없음
- 생성 파일만 작성했다.

## 3. 생성 파일
- tmp/codex_frontend_detail_history_view_ui_move_precheck.py
- docs/FRONTEND_DETAIL_HISTORY_VIEW_UI_MOVE_PRECHECK_20260522.md
- docs/FRONTEND_DETAIL_HISTORY_VIEW_UI_MOVE_PRECHECK_20260522.json
- docs/FRONTEND_DETAIL_HISTORY_VIEW_UI_MOVE_PRECHECK_MAP_20260522.csv

## 4. 분석 범위
- src/components/history/DetailHistoryView.tsx
- src/components/history/HistoryWorkspace.tsx
- src/components/history/ui/**
- src/app/history/**
- src/lib/historyStore.ts
- src/lib/imageStore.ts
- src/lib/restoreProfileStore.ts
- src/lib/profiles.ts
- src/lib/autofillEngine.ts
- src/lib/groundTruthStore.ts
- src/lib/testsets.ts
- src/components/autorestore/**
- src/components/restore/**
- src/components/test/TestWorkspace.tsx
- src/components/test/core/**
- src/common/**
- src/components/runocr/**

## 5. DetailHistoryView 역할 요약
- currentPath: src/components/history/DetailHistoryView.tsx
- lineCount: 996
- exports: export default function DetailHistoryView
- 주요 역할: HistoryRunRecord 상세 렌더링, output fields/tableRows 편집, GT 저장, 복원 프로필 저장/update 액션 제공.
- UI-only 여부: 순수 UI-only는 아니다. 상세 view UI 성격이 강하지만 store/GT/restore profile action orchestration을 포함한다.
- moveRisk: MEDIUM

## 6. importedBy 분석
- production direct import: src/components/history/HistoryWorkspace.tsx (`./DetailHistoryView`)
- TestWorkspace/test core direct import: 없음
- tmp/static check reference: 일부 있음. HR-2 move static check에서 expectation 갱신 필요.

## 7. history/ui 적합성
- 판정: HISTORY_UI_READY_WITH_IMPORT_ONLY
- 이유: HistoryWorkspace가 feature root/orchestration 역할을 맡고, DetailHistoryView는 상세 화면 조각으로 `history/ui`에 둘 수 있다.
- 단, DetailHistoryView 내부의 store/GT/restore profile action은 유지하되 이번 이동에서는 리팩토링하지 않는 것이 안전하다.

## 8. dependency 영향 분석
- HistoryWorkspace -> DetailHistoryView import 보정 필요.
- DetailHistoryView -> `../layout/AppProviders` 상대 import는 이동 후 `../../layout/AppProviders`로 보정 필요.
- `@/lib/historyStore`, `@/lib/groundTruthStore`, `@/lib/autofillEngine`, `@/lib/restoreProfileStore`, `@/common/utils/*` alias import는 위치 이동 자체로는 구조적으로 유지 가능하다.
- restore/autorestore component 직접 import는 없다.
- 순환 의존 위험: LOW.

## 9. TestWorkspace 영향
- 판정: NO_TEST_IMPACT
- TestWorkspace 직접 import: 없음
- test/core 직접 import: 없음
- 이동 시 TestWorkspace 파일 수정 필요: 없음

## 10. target path 비교
| 후보 | 추천 | 장점 | 단점 | 위험 |
| --- | --- | --- | --- | --- |
| src/components/history/ui/DetailHistoryView.tsx | YES | history root를 Workspace 중심으로 정리, UI 계층 일관성 | 내부 action/store 의존은 남음 | MEDIUM |
| src/components/history/DetailHistoryView.tsx 유지 | NO | import 수정 없음 | root에 상세 UI가 남음 | LOW |
| root 유지 후 내부 UI 조각 분리 | NO | 더 엄밀한 분리 가능 | 이번 범위보다 큰 리팩토링 | MEDIUM |
| 보류 | NO | 즉시 영향 없음 | 구조 정리 지연 | LOW |

## 11. 실제 이동 추천
- 추천: A. DetailHistoryView.tsx만 src/components/history/ui/DetailHistoryView.tsx로 이동
- 필요한 import 수정: HistoryWorkspace import path, moved file 내부 AppProviders 상대 import path
- 금지/비추천: historyStore/imageStore/restore/autorestore 분리와 묶지 않기, JSX/handler 로직 수정하지 않기.

## 12. static check 설계
- tmp/check_detail_history_view_ui_move_hr2.mjs
- src/components/history/ui/DetailHistoryView.tsx 존재 확인
- src/components/history/DetailHistoryView.tsx 부재 확인
- HistoryWorkspace import가 ./ui/DetailHistoryView인지 확인
- src 운영 코드에 components/history/DetailHistoryView 잔존 없음 확인
- TestWorkspace 미수정 또는 import-only 영향 없음 확인
- historyStore/imageStore/restore/autorestore 미수정 확인
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
 M src/components/history/DetailHistoryView.tsx
 M src/components/history/HistoryWorkspace.tsx
R  src/components/history/popup/CreateHistoryPopup.tsx -> src/components/history/ui/CreateHistoryPopup.tsx
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
- known stderr noise: ESLint nextVitals is not iterable 은 exit code 0이면 known issue로 취급.

## 15. 다음 작업 제안
- HR-2 move 단계에서 단일 파일 이동과 import path 보정만 수행한다.
- `tmp/check_detail_history_view_ui_move_hr2.mjs`를 추가해 move-only 범위를 검증한다.
- 이후 historyStore/imageStore/restoreProfileStore/autofillEngine 이동은 별도 precheck로 분리한다.
