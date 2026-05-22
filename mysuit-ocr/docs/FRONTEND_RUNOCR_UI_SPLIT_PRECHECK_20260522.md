# FRONTEND RUNOCR UI SPLIT PRECHECK 20260522

## 1. 사용 도구와 모델
- 도구: Codex
- 모델: Codex
- 작업명: CODEX_FRONTEND_RUNOCR_UI_SPLIT_PRECHECK_NO_PROD_MODIFY

## 2. 코드 수정 여부
- 운영 코드 수정: 없음
- UI 파일 생성: 없음
- import 수정/파일 이동/fixture 수정: 없음
- 생성한 파일은 precheck 스크립트와 문서 리포트뿐이다.

## 3. 생성 파일
- `tmp/codex_frontend_runocr_ui_split_precheck.py`
- `docs/FRONTEND_RUNOCR_UI_SPLIT_PRECHECK_20260522.md`
- `docs/FRONTEND_RUNOCR_UI_SPLIT_PRECHECK_20260522.json`
- `docs/FRONTEND_RUNOCR_UI_SPLIT_MAP_20260522.csv`

## 4. 분석 범위
- 필수: `src/components/runocr/RunOcrWorkspace.tsx`
- 참고: `src/components/runocr/ui/*`, `src/components/runocr/utils/*`

## 5. RunOcrWorkspace JSX 구조 요약
- 전체 라인 수: 1490
- 결과 화면 branch: 1114-1225
  - `OcrCanvasPane` 또는 `OcrDocViewer`를 문서 영역에 표시한다.
  - `OcrResultPanel`을 오른쪽 결과 패널에 표시한다.
  - scan overlay와 hidden file input이 같은 branch 안에 있다.
- 기본 화면 main return: 1228-1490
  - template topbar: 1230-1306
  - upload panel: 1307-1338
  - guide/model/run button panel: 1339-1462
  - template hover tooltip: 1463-1490

## 6. RunOcrControls 후보 분석
- 후보 범위: 1230-1462
- 포함 후보: template topbar, file dropzone/preview, model select, file info, guide, run button
- 예상 props 수: 26
- handler 수: 8
- setter 수: 4
- 위험도: HIGH
- 판정: `DO_LATER_SPLIT_SMALLER`
- 이유: 한 번에 RunOcrControls로 빼면 템플릿, 파일, 모델, 실행 버튼, tooltip, ref까지 넘어가 props가 16개를 크게 넘는다.

## 7. RunOcrResultLayout 후보 분석
- 후보 범위: 1114-1225
- direct props 방식 예상 props 수: 35 / 위험도 HIGH
- node composition 방식 예상 props 수: 4 / 위험도 LOW
- 판정: Extract RunOcrResultLayout with node composition only.
- 이유: OcrDocViewer/OcrResultPanel props를 layout 컴포넌트로 직접 넘기면 위험하지만, viewer/result/hidden input을 node로 넘기면 layout 책임만 분리된다.

## 8. props 폭발 위험
- `RunOcrControls`를 한 번에 분리하면 템플릿 선택, 파일 선택, preview/render 상태, model select, run button, tooltip, ref, router handler가 모두 props로 넘어간다.
- `RunOcrResultLayout`을 direct props 방식으로 만들면 `OcrDocViewer`와 `OcrResultPanel` props를 그대로 중계하는 컴포넌트가 되어 책임이 흐려진다.
- `RunOcrResultLayout`을 node composition 방식으로 만들면 props를 `viewer`, `resultPanel`, `scanOverlay`, `hiddenFileInput` 수준으로 낮출 수 있다.

## 9. extraction options 비교
| option | risk | recommendation |
| --- | --- | --- |
| RunOcrControls only | HIGH | DO_LATER |
| RunOcrResultLayout direct props | HIGH | DO_NOT_USE |
| RunOcrControls + RunOcrResultLayout together | HIGH | DO_NOT_DO_IN_PHASE_3A |
| RunOcrResultLayout node composition only | LOW | DO_FIRST |
| Hold UI split | LOW | ACCEPTABLE_BUT_NOT_PRIMARY |

## 10. Phase 3A 추천 범위
- 추천: A. RunOcrResultLayout만 node composition 방식으로 분리
- 범위:
  - `RunOcrResultLayout.tsx`만 생성
  - `viewer`, `resultPanel`, `scanOverlay`, `hiddenFileInput`을 node로 전달
  - state/handler/request/mapping/history/autofill 이동 없음
  - `RunOcrControls`는 보류
- 위험도: LOW
- 이유: 첫 UI split은 layout 책임만 떼어내면 props 폭발을 피하고, RunOcrWorkspace의 orchestration 책임을 유지할 수 있다.

## 11. 예상 파일/변경
- 신규 후보: `src/components/runocr/ui/RunOcrResultLayout.tsx`
- 수정 후보: `src/components/runocr/RunOcrWorkspace.tsx`
- 보류 후보: `src/components/runocr/ui/RunOcrControls.tsx`
- optional check 후보: `tmp/check_runocr_ui_split_boundary_3a.mjs`

## 12. 검증 전략
- npm run typecheck
- npm run build
- node tmp/check_table_view_model_v1_fixtures_js.mjs
- node tmp/check_clean_json_v1_fixtures_js.mjs
- python tmp/codex_markdown_contract_fixture_lock.py --check --phase post_RUNOCR_UI_SPLIT_3A_20260522
- FormData key parity check
- request boundary static check
- response mapping boundary static check
- UI split boundary static check
- /runocr manual smoke: file selection, OCR run, Preview tab, Clean JSON copy/export

## 13. dirty 상태
현재 dirty 상태는 되돌리지 않았다.

```text
 M src/app/runocr/page.tsx
RM src/components/upload/UploadWorkspace.tsx -> src/components/runocr/RunOcrWorkspace.tsx
R  src/components/upload/CornerAdjust.tsx -> src/components/runocr/ui/CornerAdjust.tsx
R  src/components/upload/OcrDocViewer.tsx -> src/components/runocr/ui/OcrDocViewer.tsx
RM src/components/upload/OcrResultPanel.tsx -> src/components/runocr/ui/OcrResultPanel.tsx
 M src/lib/invoiceTableDisplay.ts
 M ../ocr-server/data/review_log.jsonl
 M ../ocr-server/data/templates.json
 M ../ocr-server/requirements.txt
?? docs/CLEAN_JSON_CONTRACT_20260521.json
?? docs/CLEAN_JSON_CONTRACT_20260521.md
?? docs/CLEAN_JSON_V1_FIXTURE_CHECK_post_extraction_20260521_20260521.json
?? docs/CLEAN_JSON_V1_FIXTURE_CHECK_post_extraction_20260521_20260521.md
?? docs/CLEAN_JSON_V1_FIXTURE_CHECK_pre_extraction_20260521_20260521.json
?? docs/CLEAN_JSON_V1_FIXTURE_CHECK_pre_extraction_20260521_20260521.md
?? docs/CLEAN_JSON_V1_FIXTURE_LOCK_20260521.json
?? docs/CLEAN_JSON_V1_FIXTURE_LOCK_20260521.md
?? docs/FRONTEND_CLEANUP_1B_JS_CLEAN_JSON_FIXTURE_RUNNER_20260521.json
?? docs/FRONTEND_CLEANUP_1B_JS_CLEAN_JSON_FIXTURE_RUNNER_20260521.md
?? docs/FRONTEND_CLEANUP_1_CLEAN_JSON_BUILDER_EXTRACT_20260521.json
?? docs/FRONTEND_CLEANUP_1_CLEAN_JSON_BUILDER_EXTRACT_20260521.md
?? docs/FRONTEND_CLEANUP_2B_MARKDOWN_BUILDER_EXTRACT_20260521.json
?? docs/FRONTEND_CLEANUP_2B_MARKDOWN_BUILDER_EXTRACT_20260521.md
?? docs/FRONTEND_CLEANUP_3A_PREVIEW_TABLE_BUILDER_PRECHECK_20260521.json
?? docs/FRONTEND_CLEANUP_3A_PREVIEW_TABLE_BUILDER_PRECHECK_20260521.md
?? docs/FRONTEND_CLEANUP_3C_TABLE_RENDERER_PRECHECK_20260521.json
?? docs/FRONTEND_CLEANUP_3C_TABLE_RENDERER_PRECHECK_20260521.md
?? docs/FRONTEND_CLEANUP_3D0_2_TABLE_VIEW_MODEL_CONTRACT_TRIM_PRECHECK_20260521.json
?? docs/FRONTEND_CLEANUP_3D0_2_TABLE_VIEW_MODEL_CONTRACT_TRIM_PRECHECK_20260521.md
?? docs/FRONTEND_CLEANUP_3D0_TABLE_VIEW_MODEL_CONTRACT_PRECHECK_20260521.json
?? docs/FRONTEND_CLEANUP_3D0_TABLE_VIEW_MODEL_CONTRACT_PRECHECK_20260521.md
?? docs/FRONTEND_CLEANUP_3D1_5_TABLE_VIEW_MODEL_INPUT_FIXTURE_PREP_20260521.json
?? docs/FRONTEND_CLEANUP_3D1_5_TABLE_VIEW_MODEL_INPUT_FIXTURE_PREP_20260521.md
?? docs/FRONTEND_CLEANUP_3D1_TABLE_VIEW_MODEL_FIXTURE_LOCK_20260521.json
?? docs/FRONTEND_CLEANUP_3D1_TABLE_VIEW_MODEL_FIXTURE_LOCK_20260521.md
?? docs/FRONTEND_CLEANUP_3D2_RUNNER_RESULT_20260521.json
?? docs/FRONTEND_CLEANUP_3D2_STRUCTURED_TABLE_VIEW_MODEL_HELPER_20260521.json
?? docs/FRONTEND_CLEANUP_3D2_STRUCTURED_TABLE_VIEW_MODEL_HELPER_20260521.md
?? docs/FRONTEND_CLEANUP_3D3_APPLY_STRUCTURED_TABLE_VIEW_MODEL_PREVIEW_ONLY_20260521.json
?? docs/FRONTEND_CLEANUP_3D3_APPLY_STRUCTURED_TABLE_VIEW_MODEL_PREVIEW_ONLY_20260521.md
?? docs/FRONTEND_CLEANUP_3D3_SMOKE_COLUMN_POLICY_PRECHECK_20260521.json
?? docs/FRONTEND_CLEANUP_3D3_SMOKE_COLUMN_POLICY_PRECHECK_20260521.md
?? docs/FRONTEND_CLEANUP_OCR_RESULT_PANEL_CYCLE_1_CLOSEOUT_20260521.json
?? docs/FRONTEND_CLEANUP_OCR_RESULT_PANEL_CYCLE_1_CLOSEOUT_20260521.md
?? docs/FRONTEND_FILE_INVENTORY_USAGE_PRECHECK_20260521.json
?? docs/FRONTEND_FILE_INVENTORY_USAGE_PRECHECK_20260521.md
?? docs/FRONTEND_FILE_INVENTORY_USAGE_PRECHECK_TABLE_20260521.csv
?? docs/FRONTEND_INVOICE_TABLE_DISPLAY_POLICY_FIX_20260522.json
?? docs/FRONTEND_INVOICE_TABLE_DISPLAY_POLICY_FIX_20260522.md
?? docs/FRONTEND_INVOICE_TABLE_DISPLAY_POLICY_FIX_PRECHECK_20260522.json
?? docs/FRONTEND_INVOICE_TABLE_DISPLAY_POLICY_FIX_PRECHECK_20260522.md
?? docs/FRONTEND_RUNOCR_FOLDER_MOVE_PRECHECK_20260522.json
?? docs/FRONTEND_RUNOCR_FOLDER_MOVE_PRECHECK_20260522.md
?? docs/FRONTEND_RUNOCR_FOLDER_MOVE_PRECHECK_MAP_20260522.csv
?? docs/FRONTEND_RUNOCR_REQUEST_EXTRACT_MAP_20260522.csv
?? docs/FRONTEND_RUNOCR_REQUEST_EXTRACT_PRECHECK_20260522.json
?? docs/FRONTEND_RUNOCR_REQUEST_EXTRACT_PRECHECK_20260522.md
?? docs/FRONTEND_RUNOCR_RESPONSE_MAPPING_MAP_20260522.csv
?? docs/FRONTEND_RUNOCR_RESPONSE_MAPPING_PRECHECK_20260522.json
?? docs/FRONTEND_RUNOCR_RESPONSE_MAPPING_PRECHECK_20260522.md
?? docs/FRONTEND_RUNOCR_UI_SPLIT_MAP_20260522.csv
?? docs/FRONTEND_RUNOCR_UI_SPLIT_PRECHECK_20260522.json
?? docs/FRONTEND_RUNOCR_UI_SPLIT_PRECHECK_20260522.md
?? docs/FRONTEND_RUNOCR_UTILS_SPLIT_MAP_20260522.csv
?? docs/FRONTEND_RUNOCR_UTILS_SPLIT_PRECHECK_20260522.json
?? docs/FRONTEND_RUNOCR_UTILS_SPLIT_PRECHECK_20260522.md
?? docs/FRONTEND_STRUCTURE_1B_RUNOCR_WORKSPACE_NAMING_CLEANUP_20260522.json
?? docs/FRONTEND_STRUCTURE_1B_RUNOCR_WORKSPACE_NAMING_CLEANUP_20260522.md
?? docs/FRONTEND_STRUCTURE_1_RUNOCR_FOLDER_MOVE_20260522.json
?? docs/FRONTEND_STRUCTURE_1_RUNOCR_FOLDER_MOVE_20260522.md
?? docs/FRONTEND_STRUCTURE_2A_RUNOCR_BUILD_OCR_FORMDATA_EXTRACT_20260522.json
?? docs/FRONTEND_STRUCTURE_2A_RUNOCR_BUILD_OCR_FORMDATA_EXTRACT_20260522.md
?? docs/FRONTEND_STRUCTURE_2B_RUNOCR_REQUEST_EXTRACT_20260522.json
?? docs/FRONTEND_STRUCTURE_2B_RUNOCR_REQUEST_EXTRACT_20260522.md
?? docs/FRONTEND_STRUCTURE_2C_RUNOCR_BUILD_RUN_OCR_RESULT_EXTRACT_20260522.json
?? docs/FRONTEND_STRUCTURE_2C_RUNOCR_BUILD_RUN_OCR_RESULT_EXTRACT_20260522.md
?? docs/FRONTEND_TARGET_STRUCTURE_OWNERSHIP_MAP_20260522.csv
?? docs/FRONTEND_TARGET_STRUCTURE_OWNERSHIP_PRECHECK_20260522.json
?? docs/FRONTEND_TARGET_STRUCTURE_OWNERSHIP_PRECHECK_20260522.md
?? docs/MARKDOWN_TRADE7_TEMPLATE_DRIFT_PRECHECK_20260522.json
?? docs/MARKDOWN_TRADE7_TEMPLATE_DRIFT_PRECHECK_20260522.md
?? docs/MARKDOWN_TRADE7_TEMPLATE_DRIFT_PRECHECK_DIFF_20260522.csv
?? docs/MARKDOWN_V1_CONTRACT_20260521.json
?? docs/MARKDOWN_V1_CONTRACT_20260521.md
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_3D3_20260521_20260521.json
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_3D3_20260521_20260521.md
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_3D4_20260522_20260521.json
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_3D4_20260522_20260521.md
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_RUNOCR_FOLDER_MOVE_20260522_20260521.json
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_RUNOCR_FOLDER_MOVE_20260522_20260521.md
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_RUNOCR_FORMDATA_EXTRACT_20260522_20260521.json
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_RUNOCR_FORMDATA_EXTRACT_20260522_20260521.md
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_RUNOCR_NAMING_CLEANUP_20260522_20260521.json
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_RUNOCR_NAMING_CLEANUP_20260522_20260521.md
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_RUNOCR_REQUEST_EXTRACT_20260522_20260521.json
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_RUNOCR_REQUEST_EXTRACT_20260522_20260521.md
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_RUNOCR_RESPONSE_MAPPING_2C_20260522_20260521.json
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_RUNOCR_RESPONSE_MAPPING_2C_20260522_20260521.md
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_TRADE7_REBAKE_20260522_20260521.json
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_TRADE7_REBAKE_20260522_20260521.md
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_extraction_20260521_20260521.json
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_extraction_20260521_20260521.md
?? docs/MARKDOWN_V1_FIXTURE_CHECK_pre_extraction_20260521_20260521.json
?? docs/MARKDOWN_V1_FIXTURE_CHECK_pre_extraction_20260521_20260521.md
?? docs/MARKDOWN_V1_FIXTURE_CHECK_regression_3D2_20260521_20260521.json
?? docs/MARKDOWN_V1_FIXTURE_CHECK_regression_3D2_20260521_20260521.md
?? docs/MARKDOWN_V1_FIXTURE_COVERAGE_EOL_PRECHECK_20260521.json
?? docs/MARKDOWN_V1_FIXTURE_COVERAGE_EOL_PRECHECK_20260521.md
?? docs/MARKDOWN_V1_FIXTURE_LOCK_20260521.json
?? docs/MARKDOWN_V1_FIXTURE_LOCK_20260521.md
?? docs/MARKDOWN_V1_TRADE7_FIXTURE_REBAKE_20260522.json
?? docs/MARKDOWN_V1_TRADE7_FIXTURE_REBAKE_20260522.md
?? src/components/runocr/utils/
?? src/lib/cleanJsonBuilder.ts
?? src/lib/markdownReportBuilder.ts
?? src/lib/ocrResultFormatters.ts
?? src/lib/structuredTableViewModel.ts
?? tmp/
?? ../ocr-server/requirements-aws.txt
```

## 14. typecheck/build 결과
- `npm run typecheck`: PASS (exit 0)
- `npm run build`: PASS (exit 0)
- known stderr noise: ESLint: nextVitals is not iterable

## 15. 다음 작업 제안
1. Phase 3A로 `RunOcrResultLayout` node composition split만 진행한다.
2. 실제 split 후 runner 3종, typecheck/build, `/runocr` manual smoke를 실행한다.
3. `RunOcrControls`는 props grouping 또는 더 작은 control 단위 precheck 이후 별도 작업으로 진행한다.
