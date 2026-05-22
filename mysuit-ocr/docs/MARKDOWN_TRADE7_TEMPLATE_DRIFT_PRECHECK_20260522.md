# MARKDOWN TRADE7 TEMPLATE DRIFT PRECHECK 20260522

## 1. 사용 도구와 모델
- 사용 도구: Codex
- 사용 모델: Codex
- 작업명: `CODEX_MARKDOWN_TRADE7_TEMPLATE_DRIFT_PRECHECK_NO_PROD_MODIFY`

## 2. 코드 수정 여부
- 운영 코드 수정 없음.
- `ocr-server/data/templates.json` 수정 없음.
- markdown fixture 수정 없음.
- rollback/rebake/import 수정/파일 이동 없음.

## 3. 생성 파일
- `tmp/codex_markdown_trade7_template_drift_precheck.py`
- `docs/MARKDOWN_TRADE7_TEMPLATE_DRIFT_PRECHECK_20260522.md`
- `docs/MARKDOWN_TRADE7_TEMPLATE_DRIFT_PRECHECK_20260522.json`
- `docs/MARKDOWN_TRADE7_TEMPLATE_DRIFT_PRECHECK_DIFF_20260522.csv`

## 4. 분석 범위
- backend template: `ocr-server/data/templates.json`
- markdown fixture: `tmp/fixtures/markdown_v1/invoice_statement/trade_7_7pdf.md`
- manifest: `tmp/fixtures/markdown_v1/manifest.json`
- 2C markdown check report/log evidence

## 5. 현재 dirty 상태
| scope | git status --short |
| --- | --- |
| frontend |  M src/app/runocr/page.tsx |
| frontend | RM src/components/upload/UploadWorkspace.tsx -> src/components/runocr/RunOcrWorkspace.tsx |
| frontend | R  src/components/upload/CornerAdjust.tsx -> src/components/runocr/ui/CornerAdjust.tsx |
| frontend | R  src/components/upload/OcrDocViewer.tsx -> src/components/runocr/ui/OcrDocViewer.tsx |
| frontend | RM src/components/upload/OcrResultPanel.tsx -> src/components/runocr/ui/OcrResultPanel.tsx |
| frontend |  M src/lib/invoiceTableDisplay.ts |
| frontend |  M ../ocr-server/data/review_log.jsonl |
| frontend |  M ../ocr-server/data/templates.json |
| frontend |  M ../ocr-server/requirements.txt |
| frontend | ?? docs/CLEAN_JSON_CONTRACT_20260521.json |
| frontend | ?? docs/CLEAN_JSON_CONTRACT_20260521.md |
| frontend | ?? docs/CLEAN_JSON_V1_FIXTURE_CHECK_post_extraction_20260521_20260521.json |
| frontend | ?? docs/CLEAN_JSON_V1_FIXTURE_CHECK_post_extraction_20260521_20260521.md |
| frontend | ?? docs/CLEAN_JSON_V1_FIXTURE_CHECK_pre_extraction_20260521_20260521.json |
| frontend | ?? docs/CLEAN_JSON_V1_FIXTURE_CHECK_pre_extraction_20260521_20260521.md |
| frontend | ?? docs/CLEAN_JSON_V1_FIXTURE_LOCK_20260521.json |
| frontend | ?? docs/CLEAN_JSON_V1_FIXTURE_LOCK_20260521.md |
| frontend | ?? docs/FRONTEND_CLEANUP_1B_JS_CLEAN_JSON_FIXTURE_RUNNER_20260521.json |
| frontend | ?? docs/FRONTEND_CLEANUP_1B_JS_CLEAN_JSON_FIXTURE_RUNNER_20260521.md |
| frontend | ?? docs/FRONTEND_CLEANUP_1_CLEAN_JSON_BUILDER_EXTRACT_20260521.json |
| frontend | ?? docs/FRONTEND_CLEANUP_1_CLEAN_JSON_BUILDER_EXTRACT_20260521.md |
| frontend | ?? docs/FRONTEND_CLEANUP_2B_MARKDOWN_BUILDER_EXTRACT_20260521.json |
| frontend | ?? docs/FRONTEND_CLEANUP_2B_MARKDOWN_BUILDER_EXTRACT_20260521.md |
| frontend | ?? docs/FRONTEND_CLEANUP_3A_PREVIEW_TABLE_BUILDER_PRECHECK_20260521.json |
| frontend | ?? docs/FRONTEND_CLEANUP_3A_PREVIEW_TABLE_BUILDER_PRECHECK_20260521.md |
| frontend | ?? docs/FRONTEND_CLEANUP_3C_TABLE_RENDERER_PRECHECK_20260521.json |
| frontend | ?? docs/FRONTEND_CLEANUP_3C_TABLE_RENDERER_PRECHECK_20260521.md |
| frontend | ?? docs/FRONTEND_CLEANUP_3D0_2_TABLE_VIEW_MODEL_CONTRACT_TRIM_PRECHECK_20260521.json |
| frontend | ?? docs/FRONTEND_CLEANUP_3D0_2_TABLE_VIEW_MODEL_CONTRACT_TRIM_PRECHECK_20260521.md |
| frontend | ?? docs/FRONTEND_CLEANUP_3D0_TABLE_VIEW_MODEL_CONTRACT_PRECHECK_20260521.json |
| frontend | ?? docs/FRONTEND_CLEANUP_3D0_TABLE_VIEW_MODEL_CONTRACT_PRECHECK_20260521.md |
| frontend | ?? docs/FRONTEND_CLEANUP_3D1_5_TABLE_VIEW_MODEL_INPUT_FIXTURE_PREP_20260521.json |
| frontend | ?? docs/FRONTEND_CLEANUP_3D1_5_TABLE_VIEW_MODEL_INPUT_FIXTURE_PREP_20260521.md |
| frontend | ?? docs/FRONTEND_CLEANUP_3D1_TABLE_VIEW_MODEL_FIXTURE_LOCK_20260521.json |
| frontend | ?? docs/FRONTEND_CLEANUP_3D1_TABLE_VIEW_MODEL_FIXTURE_LOCK_20260521.md |
| frontend | ?? docs/FRONTEND_CLEANUP_3D2_RUNNER_RESULT_20260521.json |
| frontend | ?? docs/FRONTEND_CLEANUP_3D2_STRUCTURED_TABLE_VIEW_MODEL_HELPER_20260521.json |
| frontend | ?? docs/FRONTEND_CLEANUP_3D2_STRUCTURED_TABLE_VIEW_MODEL_HELPER_20260521.md |
| frontend | ?? docs/FRONTEND_CLEANUP_3D3_APPLY_STRUCTURED_TABLE_VIEW_MODEL_PREVIEW_ONLY_20260521.json |
| frontend | ?? docs/FRONTEND_CLEANUP_3D3_APPLY_STRUCTURED_TABLE_VIEW_MODEL_PREVIEW_ONLY_20260521.md |
| frontend | ?? docs/FRONTEND_CLEANUP_3D3_SMOKE_COLUMN_POLICY_PRECHECK_20260521.json |
| frontend | ?? docs/FRONTEND_CLEANUP_3D3_SMOKE_COLUMN_POLICY_PRECHECK_20260521.md |
| frontend | ?? docs/FRONTEND_CLEANUP_OCR_RESULT_PANEL_CYCLE_1_CLOSEOUT_20260521.json |
| frontend | ?? docs/FRONTEND_CLEANUP_OCR_RESULT_PANEL_CYCLE_1_CLOSEOUT_20260521.md |
| frontend | ?? docs/FRONTEND_FILE_INVENTORY_USAGE_PRECHECK_20260521.json |
| frontend | ?? docs/FRONTEND_FILE_INVENTORY_USAGE_PRECHECK_20260521.md |
| frontend | ?? docs/FRONTEND_FILE_INVENTORY_USAGE_PRECHECK_TABLE_20260521.csv |
| frontend | ?? docs/FRONTEND_INVOICE_TABLE_DISPLAY_POLICY_FIX_20260522.json |
| frontend | ?? docs/FRONTEND_INVOICE_TABLE_DISPLAY_POLICY_FIX_20260522.md |
| frontend | ?? docs/FRONTEND_INVOICE_TABLE_DISPLAY_POLICY_FIX_PRECHECK_20260522.json |
| frontend | ?? docs/FRONTEND_INVOICE_TABLE_DISPLAY_POLICY_FIX_PRECHECK_20260522.md |
| frontend | ?? docs/FRONTEND_RUNOCR_FOLDER_MOVE_PRECHECK_20260522.json |
| frontend | ?? docs/FRONTEND_RUNOCR_FOLDER_MOVE_PRECHECK_20260522.md |
| frontend | ?? docs/FRONTEND_RUNOCR_FOLDER_MOVE_PRECHECK_MAP_20260522.csv |
| frontend | ?? docs/FRONTEND_RUNOCR_REQUEST_EXTRACT_MAP_20260522.csv |
| frontend | ?? docs/FRONTEND_RUNOCR_REQUEST_EXTRACT_PRECHECK_20260522.json |
| frontend | ?? docs/FRONTEND_RUNOCR_REQUEST_EXTRACT_PRECHECK_20260522.md |
| frontend | ?? docs/FRONTEND_RUNOCR_RESPONSE_MAPPING_MAP_20260522.csv |
| frontend | ?? docs/FRONTEND_RUNOCR_RESPONSE_MAPPING_PRECHECK_20260522.json |
| frontend | ?? docs/FRONTEND_RUNOCR_RESPONSE_MAPPING_PRECHECK_20260522.md |
| frontend | ?? docs/FRONTEND_RUNOCR_UTILS_SPLIT_MAP_20260522.csv |
| frontend | ?? docs/FRONTEND_RUNOCR_UTILS_SPLIT_PRECHECK_20260522.json |
| frontend | ?? docs/FRONTEND_RUNOCR_UTILS_SPLIT_PRECHECK_20260522.md |
| frontend | ?? docs/FRONTEND_STRUCTURE_1B_RUNOCR_WORKSPACE_NAMING_CLEANUP_20260522.json |
| frontend | ?? docs/FRONTEND_STRUCTURE_1B_RUNOCR_WORKSPACE_NAMING_CLEANUP_20260522.md |
| frontend | ?? docs/FRONTEND_STRUCTURE_1_RUNOCR_FOLDER_MOVE_20260522.json |
| frontend | ?? docs/FRONTEND_STRUCTURE_1_RUNOCR_FOLDER_MOVE_20260522.md |
| frontend | ?? docs/FRONTEND_STRUCTURE_2A_RUNOCR_BUILD_OCR_FORMDATA_EXTRACT_20260522.json |
| frontend | ?? docs/FRONTEND_STRUCTURE_2A_RUNOCR_BUILD_OCR_FORMDATA_EXTRACT_20260522.md |
| frontend | ?? docs/FRONTEND_STRUCTURE_2B_RUNOCR_REQUEST_EXTRACT_20260522.json |
| frontend | ?? docs/FRONTEND_STRUCTURE_2B_RUNOCR_REQUEST_EXTRACT_20260522.md |
| frontend | ?? docs/FRONTEND_STRUCTURE_2C_RUNOCR_BUILD_RUN_OCR_RESULT_EXTRACT_20260522.json |
| frontend | ?? docs/FRONTEND_STRUCTURE_2C_RUNOCR_BUILD_RUN_OCR_RESULT_EXTRACT_20260522.md |
| frontend | ?? docs/FRONTEND_TARGET_STRUCTURE_OWNERSHIP_MAP_20260522.csv |
| frontend | ?? docs/FRONTEND_TARGET_STRUCTURE_OWNERSHIP_PRECHECK_20260522.json |
| frontend | ?? docs/FRONTEND_TARGET_STRUCTURE_OWNERSHIP_PRECHECK_20260522.md |
| frontend | ?? docs/MARKDOWN_TRADE7_TEMPLATE_DRIFT_PRECHECK_20260522.json |
| frontend | ?? docs/MARKDOWN_TRADE7_TEMPLATE_DRIFT_PRECHECK_20260522.md |
| frontend | ?? docs/MARKDOWN_TRADE7_TEMPLATE_DRIFT_PRECHECK_DIFF_20260522.csv |
| frontend | ?? docs/MARKDOWN_V1_CONTRACT_20260521.json |
| frontend | ?? docs/MARKDOWN_V1_CONTRACT_20260521.md |
| frontend | ?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_3D3_20260521_20260521.json |
| frontend | ?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_3D3_20260521_20260521.md |
| frontend | ?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_3D4_20260522_20260521.json |
| frontend | ?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_3D4_20260522_20260521.md |
| frontend | ?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_RUNOCR_FOLDER_MOVE_20260522_20260521.json |
| frontend | ?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_RUNOCR_FOLDER_MOVE_20260522_20260521.md |
| frontend | ?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_RUNOCR_FORMDATA_EXTRACT_20260522_20260521.json |
| frontend | ?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_RUNOCR_FORMDATA_EXTRACT_20260522_20260521.md |
| frontend | ?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_RUNOCR_NAMING_CLEANUP_20260522_20260521.json |
| frontend | ?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_RUNOCR_NAMING_CLEANUP_20260522_20260521.md |
| frontend | ?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_RUNOCR_REQUEST_EXTRACT_20260522_20260521.json |
| frontend | ?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_RUNOCR_REQUEST_EXTRACT_20260522_20260521.md |
| frontend | ?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_RUNOCR_RESPONSE_MAPPING_2C_20260522_20260521.json |
| frontend | ?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_RUNOCR_RESPONSE_MAPPING_2C_20260522_20260521.md |
| frontend | ?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_extraction_20260521_20260521.json |
| frontend | ?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_extraction_20260521_20260521.md |
| frontend | ?? docs/MARKDOWN_V1_FIXTURE_CHECK_pre_extraction_20260521_20260521.json |
| frontend | ?? docs/MARKDOWN_V1_FIXTURE_CHECK_pre_extraction_20260521_20260521.md |
| frontend | ?? docs/MARKDOWN_V1_FIXTURE_CHECK_regression_3D2_20260521_20260521.json |
| frontend | ?? docs/MARKDOWN_V1_FIXTURE_CHECK_regression_3D2_20260521_20260521.md |
| frontend | ?? docs/MARKDOWN_V1_FIXTURE_COVERAGE_EOL_PRECHECK_20260521.json |
| frontend | ?? docs/MARKDOWN_V1_FIXTURE_COVERAGE_EOL_PRECHECK_20260521.md |
| frontend | ?? docs/MARKDOWN_V1_FIXTURE_LOCK_20260521.json |
| frontend | ?? docs/MARKDOWN_V1_FIXTURE_LOCK_20260521.md |
| frontend | ?? src/components/runocr/utils/ |
| frontend | ?? src/lib/cleanJsonBuilder.ts |
| frontend | ?? src/lib/markdownReportBuilder.ts |
| frontend | ?? src/lib/ocrResultFormatters.ts |
| frontend | ?? src/lib/structuredTableViewModel.ts |
| frontend | ?? tmp/ |
| frontend | ?? ../ocr-server/requirements-aws.txt |
| backend |  M ../mysuit-ocr/src/app/runocr/page.tsx |
| backend | RM ../mysuit-ocr/src/components/upload/UploadWorkspace.tsx -> ../mysuit-ocr/src/components/runocr/RunOcrWorkspace.tsx |
| backend | R  ../mysuit-ocr/src/components/upload/CornerAdjust.tsx -> ../mysuit-ocr/src/components/runocr/ui/CornerAdjust.tsx |
| backend | R  ../mysuit-ocr/src/components/upload/OcrDocViewer.tsx -> ../mysuit-ocr/src/components/runocr/ui/OcrDocViewer.tsx |
| backend | RM ../mysuit-ocr/src/components/upload/OcrResultPanel.tsx -> ../mysuit-ocr/src/components/runocr/ui/OcrResultPanel.tsx |
| backend |  M ../mysuit-ocr/src/lib/invoiceTableDisplay.ts |
| backend |  M data/review_log.jsonl |
| backend |  M data/templates.json |
| backend |  M requirements.txt |
| backend | ?? ../mysuit-ocr/docs/CLEAN_JSON_CONTRACT_20260521.json |
| backend | ?? ../mysuit-ocr/docs/CLEAN_JSON_CONTRACT_20260521.md |
| backend | ?? ../mysuit-ocr/docs/CLEAN_JSON_V1_FIXTURE_CHECK_post_extraction_20260521_20260521.json |
| backend | ?? ../mysuit-ocr/docs/CLEAN_JSON_V1_FIXTURE_CHECK_post_extraction_20260521_20260521.md |
| backend | ?? ../mysuit-ocr/docs/CLEAN_JSON_V1_FIXTURE_CHECK_pre_extraction_20260521_20260521.json |
| backend | ?? ../mysuit-ocr/docs/CLEAN_JSON_V1_FIXTURE_CHECK_pre_extraction_20260521_20260521.md |
| backend | ?? ../mysuit-ocr/docs/CLEAN_JSON_V1_FIXTURE_LOCK_20260521.json |
| backend | ?? ../mysuit-ocr/docs/CLEAN_JSON_V1_FIXTURE_LOCK_20260521.md |
| backend | ?? ../mysuit-ocr/docs/FRONTEND_CLEANUP_1B_JS_CLEAN_JSON_FIXTURE_RUNNER_20260521.json |
| backend | ?? ../mysuit-ocr/docs/FRONTEND_CLEANUP_1B_JS_CLEAN_JSON_FIXTURE_RUNNER_20260521.md |
| backend | ?? ../mysuit-ocr/docs/FRONTEND_CLEANUP_1_CLEAN_JSON_BUILDER_EXTRACT_20260521.json |
| backend | ?? ../mysuit-ocr/docs/FRONTEND_CLEANUP_1_CLEAN_JSON_BUILDER_EXTRACT_20260521.md |
| backend | ?? ../mysuit-ocr/docs/FRONTEND_CLEANUP_2B_MARKDOWN_BUILDER_EXTRACT_20260521.json |
| backend | ?? ../mysuit-ocr/docs/FRONTEND_CLEANUP_2B_MARKDOWN_BUILDER_EXTRACT_20260521.md |
| backend | ?? ../mysuit-ocr/docs/FRONTEND_CLEANUP_3A_PREVIEW_TABLE_BUILDER_PRECHECK_20260521.json |
| backend | ?? ../mysuit-ocr/docs/FRONTEND_CLEANUP_3A_PREVIEW_TABLE_BUILDER_PRECHECK_20260521.md |
| backend | ?? ../mysuit-ocr/docs/FRONTEND_CLEANUP_3C_TABLE_RENDERER_PRECHECK_20260521.json |
| backend | ?? ../mysuit-ocr/docs/FRONTEND_CLEANUP_3C_TABLE_RENDERER_PRECHECK_20260521.md |
| backend | ?? ../mysuit-ocr/docs/FRONTEND_CLEANUP_3D0_2_TABLE_VIEW_MODEL_CONTRACT_TRIM_PRECHECK_20260521.json |
| backend | ?? ../mysuit-ocr/docs/FRONTEND_CLEANUP_3D0_2_TABLE_VIEW_MODEL_CONTRACT_TRIM_PRECHECK_20260521.md |
| backend | ?? ../mysuit-ocr/docs/FRONTEND_CLEANUP_3D0_TABLE_VIEW_MODEL_CONTRACT_PRECHECK_20260521.json |
| backend | ?? ../mysuit-ocr/docs/FRONTEND_CLEANUP_3D0_TABLE_VIEW_MODEL_CONTRACT_PRECHECK_20260521.md |
| backend | ?? ../mysuit-ocr/docs/FRONTEND_CLEANUP_3D1_5_TABLE_VIEW_MODEL_INPUT_FIXTURE_PREP_20260521.json |
| backend | ?? ../mysuit-ocr/docs/FRONTEND_CLEANUP_3D1_5_TABLE_VIEW_MODEL_INPUT_FIXTURE_PREP_20260521.md |
| backend | ?? ../mysuit-ocr/docs/FRONTEND_CLEANUP_3D1_TABLE_VIEW_MODEL_FIXTURE_LOCK_20260521.json |
| backend | ?? ../mysuit-ocr/docs/FRONTEND_CLEANUP_3D1_TABLE_VIEW_MODEL_FIXTURE_LOCK_20260521.md |
| backend | ?? ../mysuit-ocr/docs/FRONTEND_CLEANUP_3D2_RUNNER_RESULT_20260521.json |
| backend | ?? ../mysuit-ocr/docs/FRONTEND_CLEANUP_3D2_STRUCTURED_TABLE_VIEW_MODEL_HELPER_20260521.json |
| backend | ?? ../mysuit-ocr/docs/FRONTEND_CLEANUP_3D2_STRUCTURED_TABLE_VIEW_MODEL_HELPER_20260521.md |
| backend | ?? ../mysuit-ocr/docs/FRONTEND_CLEANUP_3D3_APPLY_STRUCTURED_TABLE_VIEW_MODEL_PREVIEW_ONLY_20260521.json |
| backend | ?? ../mysuit-ocr/docs/FRONTEND_CLEANUP_3D3_APPLY_STRUCTURED_TABLE_VIEW_MODEL_PREVIEW_ONLY_20260521.md |
| backend | ?? ../mysuit-ocr/docs/FRONTEND_CLEANUP_3D3_SMOKE_COLUMN_POLICY_PRECHECK_20260521.json |
| backend | ?? ../mysuit-ocr/docs/FRONTEND_CLEANUP_3D3_SMOKE_COLUMN_POLICY_PRECHECK_20260521.md |
| backend | ?? ../mysuit-ocr/docs/FRONTEND_CLEANUP_OCR_RESULT_PANEL_CYCLE_1_CLOSEOUT_20260521.json |
| backend | ?? ../mysuit-ocr/docs/FRONTEND_CLEANUP_OCR_RESULT_PANEL_CYCLE_1_CLOSEOUT_20260521.md |
| backend | ?? ../mysuit-ocr/docs/FRONTEND_FILE_INVENTORY_USAGE_PRECHECK_20260521.json |
| backend | ?? ../mysuit-ocr/docs/FRONTEND_FILE_INVENTORY_USAGE_PRECHECK_20260521.md |
| backend | ?? ../mysuit-ocr/docs/FRONTEND_FILE_INVENTORY_USAGE_PRECHECK_TABLE_20260521.csv |
| backend | ?? ../mysuit-ocr/docs/FRONTEND_INVOICE_TABLE_DISPLAY_POLICY_FIX_20260522.json |
| backend | ?? ../mysuit-ocr/docs/FRONTEND_INVOICE_TABLE_DISPLAY_POLICY_FIX_20260522.md |
| backend | ?? ../mysuit-ocr/docs/FRONTEND_INVOICE_TABLE_DISPLAY_POLICY_FIX_PRECHECK_20260522.json |
| backend | ?? ../mysuit-ocr/docs/FRONTEND_INVOICE_TABLE_DISPLAY_POLICY_FIX_PRECHECK_20260522.md |
| backend | ?? ../mysuit-ocr/docs/FRONTEND_RUNOCR_FOLDER_MOVE_PRECHECK_20260522.json |
| backend | ?? ../mysuit-ocr/docs/FRONTEND_RUNOCR_FOLDER_MOVE_PRECHECK_20260522.md |
| backend | ?? ../mysuit-ocr/docs/FRONTEND_RUNOCR_FOLDER_MOVE_PRECHECK_MAP_20260522.csv |
| backend | ?? ../mysuit-ocr/docs/FRONTEND_RUNOCR_REQUEST_EXTRACT_MAP_20260522.csv |
| backend | ?? ../mysuit-ocr/docs/FRONTEND_RUNOCR_REQUEST_EXTRACT_PRECHECK_20260522.json |
| backend | ?? ../mysuit-ocr/docs/FRONTEND_RUNOCR_REQUEST_EXTRACT_PRECHECK_20260522.md |
| backend | ?? ../mysuit-ocr/docs/FRONTEND_RUNOCR_RESPONSE_MAPPING_MAP_20260522.csv |
| backend | ?? ../mysuit-ocr/docs/FRONTEND_RUNOCR_RESPONSE_MAPPING_PRECHECK_20260522.json |
| backend | ?? ../mysuit-ocr/docs/FRONTEND_RUNOCR_RESPONSE_MAPPING_PRECHECK_20260522.md |
| backend | ?? ../mysuit-ocr/docs/FRONTEND_RUNOCR_UTILS_SPLIT_MAP_20260522.csv |
| backend | ?? ../mysuit-ocr/docs/FRONTEND_RUNOCR_UTILS_SPLIT_PRECHECK_20260522.json |
| backend | ?? ../mysuit-ocr/docs/FRONTEND_RUNOCR_UTILS_SPLIT_PRECHECK_20260522.md |
| backend | ?? ../mysuit-ocr/docs/FRONTEND_STRUCTURE_1B_RUNOCR_WORKSPACE_NAMING_CLEANUP_20260522.json |
| backend | ?? ../mysuit-ocr/docs/FRONTEND_STRUCTURE_1B_RUNOCR_WORKSPACE_NAMING_CLEANUP_20260522.md |
| backend | ?? ../mysuit-ocr/docs/FRONTEND_STRUCTURE_1_RUNOCR_FOLDER_MOVE_20260522.json |
| backend | ?? ../mysuit-ocr/docs/FRONTEND_STRUCTURE_1_RUNOCR_FOLDER_MOVE_20260522.md |
| backend | ?? ../mysuit-ocr/docs/FRONTEND_STRUCTURE_2A_RUNOCR_BUILD_OCR_FORMDATA_EXTRACT_20260522.json |
| backend | ?? ../mysuit-ocr/docs/FRONTEND_STRUCTURE_2A_RUNOCR_BUILD_OCR_FORMDATA_EXTRACT_20260522.md |
| backend | ?? ../mysuit-ocr/docs/FRONTEND_STRUCTURE_2B_RUNOCR_REQUEST_EXTRACT_20260522.json |
| backend | ?? ../mysuit-ocr/docs/FRONTEND_STRUCTURE_2B_RUNOCR_REQUEST_EXTRACT_20260522.md |
| backend | ?? ../mysuit-ocr/docs/FRONTEND_STRUCTURE_2C_RUNOCR_BUILD_RUN_OCR_RESULT_EXTRACT_20260522.json |
| backend | ?? ../mysuit-ocr/docs/FRONTEND_STRUCTURE_2C_RUNOCR_BUILD_RUN_OCR_RESULT_EXTRACT_20260522.md |
| backend | ?? ../mysuit-ocr/docs/FRONTEND_TARGET_STRUCTURE_OWNERSHIP_MAP_20260522.csv |
| backend | ?? ../mysuit-ocr/docs/FRONTEND_TARGET_STRUCTURE_OWNERSHIP_PRECHECK_20260522.json |
| backend | ?? ../mysuit-ocr/docs/FRONTEND_TARGET_STRUCTURE_OWNERSHIP_PRECHECK_20260522.md |
| backend | ?? ../mysuit-ocr/docs/MARKDOWN_TRADE7_TEMPLATE_DRIFT_PRECHECK_20260522.json |
| backend | ?? ../mysuit-ocr/docs/MARKDOWN_TRADE7_TEMPLATE_DRIFT_PRECHECK_20260522.md |
| backend | ?? ../mysuit-ocr/docs/MARKDOWN_TRADE7_TEMPLATE_DRIFT_PRECHECK_DIFF_20260522.csv |
| backend | ?? ../mysuit-ocr/docs/MARKDOWN_V1_CONTRACT_20260521.json |
| backend | ?? ../mysuit-ocr/docs/MARKDOWN_V1_CONTRACT_20260521.md |
| backend | ?? ../mysuit-ocr/docs/MARKDOWN_V1_FIXTURE_CHECK_post_3D3_20260521_20260521.json |
| backend | ?? ../mysuit-ocr/docs/MARKDOWN_V1_FIXTURE_CHECK_post_3D3_20260521_20260521.md |
| backend | ?? ../mysuit-ocr/docs/MARKDOWN_V1_FIXTURE_CHECK_post_3D4_20260522_20260521.json |
| backend | ?? ../mysuit-ocr/docs/MARKDOWN_V1_FIXTURE_CHECK_post_3D4_20260522_20260521.md |
| backend | ?? ../mysuit-ocr/docs/MARKDOWN_V1_FIXTURE_CHECK_post_RUNOCR_FOLDER_MOVE_20260522_20260521.json |
| backend | ?? ../mysuit-ocr/docs/MARKDOWN_V1_FIXTURE_CHECK_post_RUNOCR_FOLDER_MOVE_20260522_20260521.md |
| backend | ?? ../mysuit-ocr/docs/MARKDOWN_V1_FIXTURE_CHECK_post_RUNOCR_FORMDATA_EXTRACT_20260522_20260521.json |
| backend | ?? ../mysuit-ocr/docs/MARKDOWN_V1_FIXTURE_CHECK_post_RUNOCR_FORMDATA_EXTRACT_20260522_20260521.md |
| backend | ?? ../mysuit-ocr/docs/MARKDOWN_V1_FIXTURE_CHECK_post_RUNOCR_NAMING_CLEANUP_20260522_20260521.json |
| backend | ?? ../mysuit-ocr/docs/MARKDOWN_V1_FIXTURE_CHECK_post_RUNOCR_NAMING_CLEANUP_20260522_20260521.md |
| backend | ?? ../mysuit-ocr/docs/MARKDOWN_V1_FIXTURE_CHECK_post_RUNOCR_REQUEST_EXTRACT_20260522_20260521.json |
| backend | ?? ../mysuit-ocr/docs/MARKDOWN_V1_FIXTURE_CHECK_post_RUNOCR_REQUEST_EXTRACT_20260522_20260521.md |
| backend | ?? ../mysuit-ocr/docs/MARKDOWN_V1_FIXTURE_CHECK_post_RUNOCR_RESPONSE_MAPPING_2C_20260522_20260521.json |
| backend | ?? ../mysuit-ocr/docs/MARKDOWN_V1_FIXTURE_CHECK_post_RUNOCR_RESPONSE_MAPPING_2C_20260522_20260521.md |
| backend | ?? ../mysuit-ocr/docs/MARKDOWN_V1_FIXTURE_CHECK_post_extraction_20260521_20260521.json |
| backend | ?? ../mysuit-ocr/docs/MARKDOWN_V1_FIXTURE_CHECK_post_extraction_20260521_20260521.md |
| backend | ?? ../mysuit-ocr/docs/MARKDOWN_V1_FIXTURE_CHECK_pre_extraction_20260521_20260521.json |
| backend | ?? ../mysuit-ocr/docs/MARKDOWN_V1_FIXTURE_CHECK_pre_extraction_20260521_20260521.md |
| backend | ?? ../mysuit-ocr/docs/MARKDOWN_V1_FIXTURE_CHECK_regression_3D2_20260521_20260521.json |
| backend | ?? ../mysuit-ocr/docs/MARKDOWN_V1_FIXTURE_CHECK_regression_3D2_20260521_20260521.md |
| backend | ?? ../mysuit-ocr/docs/MARKDOWN_V1_FIXTURE_COVERAGE_EOL_PRECHECK_20260521.json |
| backend | ?? ../mysuit-ocr/docs/MARKDOWN_V1_FIXTURE_COVERAGE_EOL_PRECHECK_20260521.md |
| backend | ?? ../mysuit-ocr/docs/MARKDOWN_V1_FIXTURE_LOCK_20260521.json |
| backend | ?? ../mysuit-ocr/docs/MARKDOWN_V1_FIXTURE_LOCK_20260521.md |
| backend | ?? ../mysuit-ocr/src/components/runocr/utils/ |
| backend | ?? ../mysuit-ocr/src/lib/cleanJsonBuilder.ts |
| backend | ?? ../mysuit-ocr/src/lib/markdownReportBuilder.ts |
| backend | ?? ../mysuit-ocr/src/lib/ocrResultFormatters.ts |
| backend | ?? ../mysuit-ocr/src/lib/structuredTableViewModel.ts |
| backend | ?? ../mysuit-ocr/tmp/ |
| backend | ?? requirements-aws.txt |

## 6. trade_7 markdown drift 요약
- caseId: `trade_7_7pdf`
- templateId: `TPL-3AFD383E`
- expected: `(113-85-04425)` / `97.1%`
- actual: `113-85-04425` / `100.0%`
- diff: actual removes parentheses and changes confidence 97.1% -> 100.0%
- actual source: `D:\Free_Vue\OCR\mysuit-ocr\docs\MARKDOWN_V1_FIXTURE_CHECK_post_RUNOCR_RESPONSE_MAPPING_2C_20260522_20260521.json`

## 7. templates.json TPL-3AFD383E diff
| templateId | path | old | new | delta |
| --- | --- | --- | --- | --- |
| TPL-3AFD383E | template_json.regions[1].width | 189 | 180 | -9 |
| TPL-3AFD383E | template_json.regions[1].x | 304 | 309 | 5 |
| TPL-3AFD383E | template_json.regions[2].height | 75 | 70 | -5 |
| TPL-3AFD383E | updated_at | 2026-05-21 11:25:46 | 2026-05-22 13:31:56 |  |

## 8. expected fixture 값
- fixturePath: `tmp/fixtures/markdown_v1/invoice_statement/trade_7_7pdf.md`
- lineNumber: 9
- expectedLine: `| 2 | 공급받는자 사업자 번호 (field_2) | (113-85-04425) | 97.1% | OCR |`
- fixture createdAt: `2026-05-21T14:58:31`
- fixture apiUrl: `http://127.0.0.1:9141/ocr/extract`

## 9. actual backend 값
- actualLine: `| 2 | 공급받는자 사업자 번호 (field_2) | 113-85-04425 | 100.0% | OCR |
`
- value: `113-85-04425`
- confidence: `100.0%`
- API 재호출은 하지 않았고, 2C markdown runner report를 근거로 삼았다. 따라서 review_log append 부작용은 새로 만들지 않았다.

## 10. 2C 코드 변경과 인과 여부
- relatedTo2C: `NO`
- reason: 2C moved frontend buildRunOcrResult into mapOcrResponse, while markdown fixture runner calls backend /ocr/extract directly and does not import or execute React frontend mapping code. The failing case aligns with dirty backend templates.json changes for TPL-3AFD383E.

## 11. rollback vs rebake 판단
| key | value |
| --- | --- |
| recommendation | NEED_USER_DECISION |
| reason | The drift is almost certainly backend template dirty-state driven, not 2C-driven. Actual looks more accurate, but the template coordinate edit intent is not documented enough to choose rebake automatically. |
| risk | MEDIUM |
| nextAction | Ask whether TPL-3AFD383E template coordinate changes are intended. If yes, rebake trade_7 markdown fixture; if no, rollback only that template dirty change. |
| rollbackCase | Use if templates.json coordinate edits were accidental/manual smoke residue. |
| rebakeCase | Use if TPL-3AFD383E coordinate edits were intentional and current actual is accepted as better OCR. |
| holdKnownDriftCase | Not recommended except as a temporary note because it keeps markdown runner at 5/6. |

## 12. 최종 추천
`NEED_USER_DECISION`

근거:
- markdown runner는 backend `/ocr/extract`를 직접 호출하므로 frontend `mapOcrResponse`를 거치지 않는다.
- drift는 `templates.json` dirty 좌표 변경과 같은 시점/대상 템플릿에서 발생한다.
- 현재 actual은 사업자번호 괄호가 사라지고 confidence가 100.0%로 올라간 결과라, OCR 품질 관점에서는 더 나아 보인다.
- 다만 template 좌표 변경 의도/승인 기록이 명확하지 않아 즉시 rebake보다 사용자 결정이 안전하다.

## 13. 다음 실제 작업 방향
- 사용자 결정 후 진행:
  - rollback 선택: `TPL-3AFD383E` 관련 dirty 좌표만 원복하고 markdown runner 6/6 확인.
  - rebake 선택: `trade_7_7pdf.md` 및 manifest metadata만 갱신하고 rebake 사유 문서화.
- known drift 보류는 다음 리팩토링 검증에서 계속 5/6 노이즈가 되므로 비추천.

## 14. Typecheck/Build 결과
| command | status | exit | seconds | known stderr noise |
| --- | --- | ---: | ---: | --- |
| npm.cmd run typecheck | PASS | 0 | 1.586 | False |
| npm.cmd run build | PASS | 0 | 16.746 | True |

## 15. 주의사항
- 이번 작업은 precheck만 수행했다.
- templates.json/fixture/운영 코드는 수정하지 않았다.
- validation plan:
| validation |
| --- |
| If rollback: restore only TPL-3AFD383E template coordinates and rerun markdown check expecting 6/6. |
| If rebake: update only trade_7_7pdf markdown fixture and manifest metadata, then rerun markdown check expecting 6/6. |
| After either action: run typecheck/build and relevant frontend runners to keep baseline clean. |
