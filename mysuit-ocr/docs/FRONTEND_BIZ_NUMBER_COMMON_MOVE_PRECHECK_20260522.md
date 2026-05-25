# FRONTEND_BIZ_NUMBER_COMMON_MOVE_PRECHECK_20260522

## 1. 사용 도구와 모델
- 사용 도구: Codex
- 사용 모델: Codex
- 작업명: CODEX_FRONTEND_BIZ_NUMBER_COMMON_MOVE_PRECHECK_NO_PROD_MODIFY

## 2. 코드 수정 여부
- 운영 코드 수정: 없음
- 파일 이동/rename/import 수정: 없음
- fixture/templates/backend 수정: 없음
- autorestore 관련 작업: 없음
- 생성 가능한 precheck 산출물만 작성했다.

## 3. 생성 파일
- tmp/codex_frontend_biz_number_common_move_precheck.py
- docs/FRONTEND_BIZ_NUMBER_COMMON_MOVE_PRECHECK_20260522.md
- docs/FRONTEND_BIZ_NUMBER_COMMON_MOVE_PRECHECK_20260522.json
- docs/FRONTEND_BIZ_NUMBER_COMMON_MOVE_PRECHECK_MAP_20260522.csv

## 4. 분석 범위
- src/lib/bizNumber.ts
- src/lib/autofillEngine.ts
- src/components/runocr/**
- src/components/history/**
- src/components/test/TestWorkspace.tsx
- src/components/test/core/**
- src/common/**
- src/app/**

## 5. bizNumber 역할 요약
- currentPath: src/lib/bizNumber.ts
- lineCount: 92
- imports: []
- exports: function normalizeBizNumber, function extractBizNumber
- mainResponsibility: 사업자번호 normalize/checksum validation/OCR text extraction helper.
- normalize 여부: True
- format 여부: True
- validate 여부: True
- OCR/autofill 사용 여부: True
- React 의존: False
- DOM/window/document/localStorage 의존: False
- backend/API 의존: False
- components/* 의존: False
- side effect: False
- common/utils 적합성: COMMON_UTIL_READY_WITH_IMPORT_ONLY
- moveRisk: MEDIUM

## 6. importedBy 분석
- src/lib/autofillEngine.ts:1 [lib, runtime] import { normalizeBizNumber } from "./bizNumber";
- src/components/test/TestWorkspace.tsx:4 [test, runtime] import { extractBizNumber, normalizeBizNumber } from "@/lib/bizNumber";
- src/components/history/ui/DetailHistoryView.tsx:27 [history, runtime] import { normalizeBizNumber } from "@/lib/bizNumber";
- src/components/test/core/autofill.ts:12 [test-core, runtime] import { extractBizNumber, normalizeBizNumber } from "@/lib/bizNumber";
- src/components/test/core/extract.ts:9 [test-core, runtime] import { normalizeBizNumber } from "@/lib/bizNumber";
- src/components/runocr/RunOcrWorkspace.tsx:39 [runocr, runtime] import { extractBizNumber } from "@/lib/bizNumber";

핵심 직접 import:
- src/lib/autofillEngine.ts: normalizeBizNumber
- src/components/runocr/RunOcrWorkspace.tsx: extractBizNumber
- src/components/history/ui/DetailHistoryView.tsx: normalizeBizNumber
- src/components/test/TestWorkspace.tsx: extractBizNumber, normalizeBizNumber
- src/components/test/core/extract.ts: normalizeBizNumber
- src/components/test/core/autofill.ts: extractBizNumber, normalizeBizNumber

## 7. TestWorkspace/test-core 영향
- 판정: TEST_CORE_DIRECT_IMPORT_BUT_SAFE_IMPORT_PATH_ONLY
- TestWorkspace 직접 import: True
- test/core 직접 import: True
- TestWorkspace 수정 필요: True
- test/core 수정 필요: True
- logic 수정 필요: False
- 설명: TestWorkspace and test/core import bizNumber directly; move impact is import path-only, but TestWorkspace policy should be explicitly acknowledged in move step.

## 8. dependency 영향
- bizNumber가 다른 lib를 import하는지: False
- autofillEngine -> bizNumber: True
- ocrResultFormatters 관계: False
- RunOCR 직접 사용: True
- History 직접 사용: True
- Clean JSON/Markdown/table runner 영향: No direct production dependency found; tmp/static checks reference filename only.
- 이동 후 common/utils가 src/lib를 import하게 되는지: False
- 순환 의존 가능성: LOW: bizNumber has no imports.

## 9. common/utils 적합성
- 판정: COMMON_UTIL_READY_BUT_TEST_IMPORT_CHECK_REQUIRED
- 이유: 순수 문자열/번호 normalize/format/validate/extract helper이며 storage, React, DOM, backend, components 의존이 없다.
- TestWorkspace/test-core가 직접 import하므로 실제 move 단계에서 import path-only 변경임을 static check로 보장해야 한다.

## 10. target path 비교
| 후보 | 추천 | 장점 | 단점 | risk |
| --- | --- | --- | --- | --- |
| src/common/utils/bizNumber.ts | YES | shared pure util 위치, RunOCR/History/Test/autofill 공유 | TestWorkspace/test-core import path 보정 필요 | MEDIUM |
| src/lib 유지 | NO | 변경 없음 | src/lib cleanup 지연 | LOW |
| src/components/test/utils/bizNumber.ts | NO | Test feature-local | app code가 test util을 import하게 됨 | HIGH |
| autofillEngine 내부 흡수 | NO | autofillEngine 의존 축소 | RunOCR/History/Test 직접 사용과 충돌 | HIGH |
| 보류 | NO | TestWorkspace import를 건드리지 않음 | 안전한 common util 이동 지연 | LOW |

## 11. 실제 이동 추천
- 추천 선택지: A. bizNumber.ts만 src/common/utils/bizNumber.ts로 이동
- autofillEngine과 묶지 않는다.
- TestWorkspace/test-core는 import path-only 변경으로 제한한다.
- common/utils가 src/lib를 import하지 않도록 static check에 포함한다.

## 12. static check 설계
- tmp/check_biz_number_common_utils_move_bz1.mjs
- src/common/utils/bizNumber.ts 존재
- src/lib/bizNumber.ts 부재
- src/common/utils/bizNumber.ts가 components/*를 import하지 않음
- React/DOM/window/document/localStorage 의존 없음
- @/lib/bizNumber 잔존 없음
- TestWorkspace 미수정 또는 import-only 확인
- test/core 미수정 또는 import-only 확인
- autofillEngine import path 정상
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
R  src/lib/historyStore.ts -> src/common/storage/historyStore.ts
R  src/lib/imageStore.ts -> src/common/storage/imageStore.ts
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
 M src/lib/autofillEngine.ts
 M src/lib/groundTruthStore.ts
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
?? docs/FRONTEND_AUTORESTORE_TO_RESTORE_MAP_20260522.csv
?? docs/FRONTEND_AUTORESTORE_TO_RESTORE_PRECHECK_20260522.json
?? docs/FRONTEND_AUTORESTORE_TO_RESTORE_PRECHECK_20260522.md
?? docs/FRONTEND_CC_1_APP_PROVIDERS_LAYOUT_MOVE_20260522.json
?? docs/FRONTEND_CC_1_APP_PROVIDERS_LAYOUT_MOVE_20260522.md
?? docs/FRONTEND_CC_2_REQUIRE_LOGIN_LOGIN_UI_MOVE_20260522.json
?? docs/FRONTEND_CC_2_REQUIRE_LOGIN_LOGIN_UI_MOVE_20260522.md
?? docs/FRONTEND_COMMON_STORAGE_BOUNDARY_MAP_20260522.csv
?? docs/FRONTEND_COMMON_STORAGE_BOUNDARY_PRECHECK_20260522.json
?? docs/FRONTEND_COMMON_STORAGE_BOUNDARY_PRECHECK_20260522.md
?? docs/FRONTEND_COMPONENTS_COMMON_ABSENT_CHECK_20260522.json
?? docs/FRONTEND_COMPONENTS_COMMON_ABSENT_CHECK_20260522.md
?? docs/FRONTEND_COMPONENTS_COMMON_OWNERSHIP_MAP_20260522.csv
?? docs/FRONTEND_COMPONENTS_COMMON_OWNERSHIP_PRECHECK_20260522.json
?? docs/FRONTEND_COMPONENTS_COMMON_OWNERSHIP_PRECHECK_20260522.md
?? docs/FRONTEND_CS_1_IMAGE_STORE_COMMON_STORAGE_MOVE_20260522.json
?? docs/FRONTEND_CS_1_IMAGE_STORE_COMMON_STORAGE_MOVE_20260522.md
?? docs/FRONTEND_CS_2_HISTORY_STORE_COMMON_STORAGE_MOVE_20260522.json
?? docs/FRONTEND_CS_2_HISTORY_STORE_COMMON_STORAGE_MOVE_20260522.md
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
?? docs/FRONTEND_IMAGE_STORE_COMMON_STORAGE_MOVE_PRECHECK_20260522.json
?? docs/FRONTEND_IMAGE_STORE_COMMON_STORAGE_MOVE_PRECHECK_20260522.md
?? docs/FRONTEND_IMAGE_STORE_COMMON_STORAGE_MOVE_PRECHECK_MAP_20260522.csv
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
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_HISTORY_STORE_COMMON_STORAGE_MOVE_20260522_20260521.json
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_HISTORY_STORE_COMMON_STORAGE_MOVE_20260522_20260521.md
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_IMAGE_STORE_COMMON_STORAGE_MOVE_20260522_20260521.json
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_IMAGE_STORE_COMMON_STORAGE_MOVE_20260522_20260521.md
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
?? tmp/check_history_store_common_storage_move_cs2.mjs
?? tmp/check_image_store_common_storage_move_cs1.mjs
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
?? tmp/codex_frontend_autorestore_to_restore_precheck.py
?? tmp/codex_frontend_biz_number_common_move_precheck.py
?? tmp/codex_frontend_common_storage_boundary_precheck.py
?? tmp/codex_frontend_components_common_absent_check.py
?? tmp/codex_frontend_components_common_ownership_precheck.py
?? tmp/codex_frontend_detail_history_view_ui_move_precheck.py
?? tmp/codex_frontend_filedropzone_common_ui_precheck.py
?? tmp/codex_frontend_history_restore_structure_precheck.py
?? tmp/codex_frontend_history_store_ownership_precheck.py
?? tmp/codex_frontend_image_store_common_storage_move_precheck.py
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
- BZ-1 move에서 bizNumber 단일 파일 이동과 import path 보정만 수행한다.
- `tmp/check_biz_number_common_utils_move_bz1.mjs`를 작성/실행한다.
- autorestore/restoreProfileStore/profiles 작업은 이번 흐름과 분리한다.
