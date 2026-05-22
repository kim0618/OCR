# FRONTEND RUNOCR FOLDER MOVE PRECHECK 20260522

## 1. 사용 도구와 모델
- 사용 도구: Codex
- 사용 모델: Codex
- 작업명: `CODEX_FRONTEND_RUNOCR_FOLDER_MOVE_PRECHECK_NO_PROD_MODIFY`

## 2. 코드 수정 여부
- 운영 코드 수정 없음.
- 파일 이동/삭제 없음.
- import 경로 수정 없음.
- fixture/backend/templates/manifest 수정 없음.

## 3. 생성 파일
- `tmp/codex_frontend_runocr_folder_move_precheck.py`
- `docs/FRONTEND_RUNOCR_FOLDER_MOVE_PRECHECK_20260522.md`
- `docs/FRONTEND_RUNOCR_FOLDER_MOVE_PRECHECK_20260522.json`
- `docs/FRONTEND_RUNOCR_FOLDER_MOVE_PRECHECK_MAP_20260522.csv`

## 4. 현재 dirty 상태
현재 dirty 상태는 기록만 했고 되돌리지 않았다. 3D4 display policy fix 관련 변경이 섞여 있을 수 있으므로 실제 이동은 3D4 PASS 후 진행하는 것이 안전하다.

| git status --short |
| --- |
|  M src/components/upload/OcrResultPanel.tsx |
|  M src/lib/invoiceTableDisplay.ts |
|  M ../ocr-server/data/review_log.jsonl |
|  M ../ocr-server/requirements.txt |
| ?? docs/CLEAN_JSON_CONTRACT_20260521.json |
| ?? docs/CLEAN_JSON_CONTRACT_20260521.md |
| ?? docs/CLEAN_JSON_V1_FIXTURE_CHECK_post_extraction_20260521_20260521.json |
| ?? docs/CLEAN_JSON_V1_FIXTURE_CHECK_post_extraction_20260521_20260521.md |
| ?? docs/CLEAN_JSON_V1_FIXTURE_CHECK_pre_extraction_20260521_20260521.json |
| ?? docs/CLEAN_JSON_V1_FIXTURE_CHECK_pre_extraction_20260521_20260521.md |
| ?? docs/CLEAN_JSON_V1_FIXTURE_LOCK_20260521.json |
| ?? docs/CLEAN_JSON_V1_FIXTURE_LOCK_20260521.md |
| ?? docs/FRONTEND_CLEANUP_1B_JS_CLEAN_JSON_FIXTURE_RUNNER_20260521.json |
| ?? docs/FRONTEND_CLEANUP_1B_JS_CLEAN_JSON_FIXTURE_RUNNER_20260521.md |
| ?? docs/FRONTEND_CLEANUP_1_CLEAN_JSON_BUILDER_EXTRACT_20260521.json |
| ?? docs/FRONTEND_CLEANUP_1_CLEAN_JSON_BUILDER_EXTRACT_20260521.md |
| ?? docs/FRONTEND_CLEANUP_2B_MARKDOWN_BUILDER_EXTRACT_20260521.json |
| ?? docs/FRONTEND_CLEANUP_2B_MARKDOWN_BUILDER_EXTRACT_20260521.md |
| ?? docs/FRONTEND_CLEANUP_3A_PREVIEW_TABLE_BUILDER_PRECHECK_20260521.json |
| ?? docs/FRONTEND_CLEANUP_3A_PREVIEW_TABLE_BUILDER_PRECHECK_20260521.md |
| ?? docs/FRONTEND_CLEANUP_3C_TABLE_RENDERER_PRECHECK_20260521.json |
| ?? docs/FRONTEND_CLEANUP_3C_TABLE_RENDERER_PRECHECK_20260521.md |
| ?? docs/FRONTEND_CLEANUP_3D0_2_TABLE_VIEW_MODEL_CONTRACT_TRIM_PRECHECK_20260521.json |
| ?? docs/FRONTEND_CLEANUP_3D0_2_TABLE_VIEW_MODEL_CONTRACT_TRIM_PRECHECK_20260521.md |
| ?? docs/FRONTEND_CLEANUP_3D0_TABLE_VIEW_MODEL_CONTRACT_PRECHECK_20260521.json |
| ?? docs/FRONTEND_CLEANUP_3D0_TABLE_VIEW_MODEL_CONTRACT_PRECHECK_20260521.md |
| ?? docs/FRONTEND_CLEANUP_3D1_5_TABLE_VIEW_MODEL_INPUT_FIXTURE_PREP_20260521.json |
| ?? docs/FRONTEND_CLEANUP_3D1_5_TABLE_VIEW_MODEL_INPUT_FIXTURE_PREP_20260521.md |
| ?? docs/FRONTEND_CLEANUP_3D1_TABLE_VIEW_MODEL_FIXTURE_LOCK_20260521.json |
| ?? docs/FRONTEND_CLEANUP_3D1_TABLE_VIEW_MODEL_FIXTURE_LOCK_20260521.md |
| ?? docs/FRONTEND_CLEANUP_3D2_RUNNER_RESULT_20260521.json |
| ?? docs/FRONTEND_CLEANUP_3D2_STRUCTURED_TABLE_VIEW_MODEL_HELPER_20260521.json |
| ?? docs/FRONTEND_CLEANUP_3D2_STRUCTURED_TABLE_VIEW_MODEL_HELPER_20260521.md |
| ?? docs/FRONTEND_CLEANUP_3D3_APPLY_STRUCTURED_TABLE_VIEW_MODEL_PREVIEW_ONLY_20260521.json |
| ?? docs/FRONTEND_CLEANUP_3D3_APPLY_STRUCTURED_TABLE_VIEW_MODEL_PREVIEW_ONLY_20260521.md |
| ?? docs/FRONTEND_CLEANUP_3D3_SMOKE_COLUMN_POLICY_PRECHECK_20260521.json |
| ?? docs/FRONTEND_CLEANUP_3D3_SMOKE_COLUMN_POLICY_PRECHECK_20260521.md |
| ?? docs/FRONTEND_CLEANUP_OCR_RESULT_PANEL_CYCLE_1_CLOSEOUT_20260521.json |
| ?? docs/FRONTEND_CLEANUP_OCR_RESULT_PANEL_CYCLE_1_CLOSEOUT_20260521.md |
| ?? docs/FRONTEND_FILE_INVENTORY_USAGE_PRECHECK_20260521.json |
| ?? docs/FRONTEND_FILE_INVENTORY_USAGE_PRECHECK_20260521.md |
| ?? docs/FRONTEND_FILE_INVENTORY_USAGE_PRECHECK_TABLE_20260521.csv |
| ?? docs/FRONTEND_INVOICE_TABLE_DISPLAY_POLICY_FIX_20260522.json |
| ?? docs/FRONTEND_INVOICE_TABLE_DISPLAY_POLICY_FIX_20260522.md |
| ?? docs/FRONTEND_INVOICE_TABLE_DISPLAY_POLICY_FIX_PRECHECK_20260522.json |
| ?? docs/FRONTEND_INVOICE_TABLE_DISPLAY_POLICY_FIX_PRECHECK_20260522.md |
| ?? docs/FRONTEND_TARGET_STRUCTURE_OWNERSHIP_MAP_20260522.csv |
| ?? docs/FRONTEND_TARGET_STRUCTURE_OWNERSHIP_PRECHECK_20260522.json |
| ?? docs/FRONTEND_TARGET_STRUCTURE_OWNERSHIP_PRECHECK_20260522.md |
| ?? docs/MARKDOWN_V1_CONTRACT_20260521.json |
| ?? docs/MARKDOWN_V1_CONTRACT_20260521.md |
| ?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_3D3_20260521_20260521.json |
| ?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_3D3_20260521_20260521.md |
| ?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_3D4_20260522_20260521.json |
| ?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_3D4_20260522_20260521.md |
| ?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_extraction_20260521_20260521.json |
| ?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_extraction_20260521_20260521.md |
| ?? docs/MARKDOWN_V1_FIXTURE_CHECK_pre_extraction_20260521_20260521.json |
| ?? docs/MARKDOWN_V1_FIXTURE_CHECK_pre_extraction_20260521_20260521.md |
| ?? docs/MARKDOWN_V1_FIXTURE_CHECK_regression_3D2_20260521_20260521.json |
| ?? docs/MARKDOWN_V1_FIXTURE_CHECK_regression_3D2_20260521_20260521.md |
| ?? docs/MARKDOWN_V1_FIXTURE_COVERAGE_EOL_PRECHECK_20260521.json |
| ?? docs/MARKDOWN_V1_FIXTURE_COVERAGE_EOL_PRECHECK_20260521.md |
| ?? docs/MARKDOWN_V1_FIXTURE_LOCK_20260521.json |
| ?? docs/MARKDOWN_V1_FIXTURE_LOCK_20260521.md |
| ?? src/lib/cleanJsonBuilder.ts |
| ?? src/lib/markdownReportBuilder.ts |
| ?? src/lib/ocrResultFormatters.ts |
| ?? src/lib/structuredTableViewModel.ts |
| ?? tmp/ |
| ?? ../ocr-server/requirements-aws.txt |

## 5. upload 폴더 파일 목록
| currentPath | targetPath | role | lines | imports | importedBy | ownership | risk | riskReason | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| src/components/upload/CornerAdjust.tsx | src/components/runocr/components/CornerAdjust.tsx | RunOCR corner adjustment UI | 174 | [] | ["src/components/upload/UploadWorkspace.tsx"] | RUNOCR_PRIVATE | MEDIUM | internal relative import path changes after nested move | ["Future common component candidate only if Template/History starts importing it."] |
| src/components/upload/OcrDocViewer.tsx | src/components/runocr/components/OcrDocViewer.tsx | RunOCR document image/PDF viewer with overlay support | 224 | ["src/components/upload/OcrResultPanel.tsx", "src/lib/invoiceFieldLabels.ts"] | ["src/components/upload/UploadWorkspace.tsx"] | RUNOCR_PRIVATE | MEDIUM | internal relative import path changes after nested move | ["Future common component candidate only if Template/History starts importing it."] |
| src/components/upload/OcrResultPanel.tsx | src/components/runocr/components/OcrResultPanel.tsx | RunOCR OCR result Preview/Custom/Validation/JSON/Markdown panel | 1660 | ["src/components/common/AppProviders.tsx", "src/lib/autofillEngine.ts", "src/lib/cleanJsonBuilder.ts", "src/lib/groundTruthStore.ts", "src/lib/markdownReportBuilder.ts", "src/lib/structuredTableViewModel.ts"] | ["src/components/upload/OcrDocViewer.tsx", "src/components/upload/UploadWorkspace.tsx"] | RUNOCR_PRIVATE | HIGH | large RunOCR surface and route-facing behavior | ["Large dirty-prone file; move only after 3D4 display policy fix is stable."] |
| src/components/upload/UploadWorkspace.tsx | src/components/runocr/RunOcrWorkspace.tsx | RunOCR upload/request workspace and result layout orchestrator | 1587 | ["src/components/common/AppProviders.tsx", "src/components/common/FileDropzone.tsx", "src/components/ocr/OcrCanvasPane.tsx", "src/components/ocr/core/types.ts", "src/components/upload/CornerAdjust.tsx", "src/components/upload/OcrDocViewer.tsx", "src/components/upload/OcrResultPanel.tsx", "src/lib/bizNumber.ts", "src/lib/historyStore.ts", "src/lib/imageStore.ts"] | ["src/app/runocr/page.tsx"] | RUNOCR_PRIVATE | HIGH | large RunOCR surface and route-facing behavior | ["Rename to RunOcrWorkspace without internal logic split in Phase 1."] |

## 6. 파일별 역할/사용처
- `UploadWorkspace.tsx`: `/runocr` route가 직접 import하는 RunOCR workspace. 내부에서 result panel/viewer/corner adjust를 조합한다.
- `OcrResultPanel.tsx`: RunOCR 결과 Preview/Custom/Validation/JSON/Markdown 패널. 큰 파일이고 현재 3D4 dirty 가능성이 있어 이동 전 안정화 필요.
- `OcrDocViewer.tsx`: RunOCR 문서 viewer. 현재 upload 내부에서만 사용된다.
- `CornerAdjust.tsx`: RunOCR corner adjust UI. 현재 upload 내부에서만 사용된다.

## 7. importedBy 분석
- 외부 직접 import는 `src/app/runocr/page.tsx -> UploadWorkspace` 1개로 확인됨.
- `History`, `Test`, `Template`에서 upload 컴포넌트를 직접 import하는 사용처는 발견되지 않음.
- upload 내부 상대 import는 `UploadWorkspace -> OcrResultPanel/OcrDocViewer/CornerAdjust`, `OcrDocViewer -> OcrResultPanel type` 경로가 핵심이다.
- barrel export는 없음.

## 8. RunOCR 전용 여부 판정
- 4개 파일 모두 현재 기준 `RUNOCR_PRIVATE`.
- `OcrDocViewer`와 `CornerAdjust`는 향후 Template 공통화 가능성은 있지만, 현재 직접 사용처 기준으로는 RunOCR 전용 이동이 적절하다.

## 9. targetPath 제안
- `src/components/upload/UploadWorkspace.tsx` -> `src/components/runocr/RunOcrWorkspace.tsx`
- `src/components/upload/OcrResultPanel.tsx` -> `src/components/runocr/components/OcrResultPanel.tsx`
- `src/components/upload/OcrDocViewer.tsx` -> `src/components/runocr/components/OcrDocViewer.tsx`
- `src/components/upload/CornerAdjust.tsx` -> `src/components/runocr/components/CornerAdjust.tsx`

## 10. import 변경 예상 목록
| fileToModify | oldImport | newImport | reason | risk |
| --- | --- | --- | --- | --- |
| src/app/runocr/page.tsx | ../../components/upload/UploadWorkspace | ../../components/runocr/RunOcrWorkspace | route entry should point to renamed RunOCR workspace | HIGH |
| src/components/runocr/RunOcrWorkspace.tsx | ./OcrResultPanel | ./components/OcrResultPanel | OcrResultPanel moves under runocr/components | HIGH |
| src/components/runocr/RunOcrWorkspace.tsx | ./OcrDocViewer | ./components/OcrDocViewer | OcrDocViewer moves under runocr/components | MEDIUM |
| src/components/runocr/RunOcrWorkspace.tsx | ./CornerAdjust | ./components/CornerAdjust | CornerAdjust moves under runocr/components | MEDIUM |
| src/components/runocr/components/OcrDocViewer.tsx | ./OcrResultPanel | ./OcrResultPanel | same sibling import after both files move into runocr/components | LOW |

## 11. 이동 위험도
- HIGH: `UploadWorkspace.tsx`, `OcrResultPanel.tsx`, route import.
- MEDIUM: viewer/corner adjust nested component move, internal relative imports.
- LOW: `OcrDocViewer -> OcrResultPanel` type sibling import은 둘 다 같은 target folder로 이동하면 경로 유지 가능.

## 12. 실제 이동 Phase 1 제안
1. `src/components/runocr`와 `components` 하위 폴더를 만든다.
2. `UploadWorkspace.tsx`를 `RunOcrWorkspace.tsx`로 이동/rename한다.
3. `OcrResultPanel`, `OcrDocViewer`, `CornerAdjust`를 `runocr/components`로 이동한다.
4. import 경로만 수정한다.
5. 내부 로직 분리나 리팩토링은 하지 않는다.

## 13. Phase 1에서 하지 말아야 할 것
| forbidden |
| --- |
| useRunOcr 생성 금지 |
| useRunOcrState 생성 금지 |
| runOcrRequest 생성 금지 |
| buildOcrFormData 생성 금지 |
| mapOcrResponse 생성 금지 |
| RunOcrControls 생성 금지 |
| RunOcrResultLayout 생성 금지 |
| OcrResultPanel 리팩토링 금지 |
| OcrDocViewer 리팩토링 금지 |
| 내부 로직 분리 금지 |

## 14. 검증 계획
| validation |
| --- |
| npm run typecheck |
| npm run build |
| node tmp/check_table_view_model_v1_fixtures_js.mjs |
| node tmp/check_clean_json_v1_fixtures_js.mjs |
| python tmp/codex_markdown_contract_fixture_lock.py --check ... |
| /runocr manual smoke: upload invoice and verify Preview |

## 15. Typecheck/Build 결과
| command | status | exit | seconds | known stderr noise |
| --- | --- | ---: | ---: | --- |
| npm.cmd run typecheck | PASS | 0 | 2.132 | False |
| npm.cmd run build | PASS | 0 | 17.161 | True |

## 16. 다음 작업 제안
- 3D4 display policy fix 결과가 PASS인지 먼저 확인한다.
- 이후 `CODEX_FRONTEND_RUNOCR_FOLDER_MOVE_PHASE1` 같은 별도 작업으로 이동만 수행한다.
- Phase 1에서는 import 경로 수정과 typecheck/build/runners/manual smoke까지만 수행하고 내부 분리는 Phase 2로 미룬다.
