# FRONTEND RUNOCR CYCLE 1 CLOSEOUT 20260522

## 1. 사용 도구와 모델
- 도구: Codex
- 모델: Codex
- 작업명: CODEX_FRONTEND_RUNOCR_CYCLE1_CLOSEOUT_NO_PROD_MODIFY

## 2. 코드 수정 여부
- 운영 코드 수정: 없음
- 주석 추가: 없음
- 파일 이동/import 수정/fixture 수정/templates.json 수정/backend 수정: 없음
- 이번 작업은 close-out 문서화만 수행했다.

## 3. 생성 파일
- `tmp/codex_frontend_runocr_cycle1_closeout.py`
- `docs/FRONTEND_RUNOCR_CYCLE1_CLOSEOUT_20260522.md`
- `docs/FRONTEND_RUNOCR_CYCLE1_CLOSEOUT_20260522.json`

## 4. Cycle 1 목적
RunOCR Cycle 1의 목적은 업로드 중심의 기존 구조를 `runocr` feature boundary로 옮기고, OCR 요청 구성/API 호출/raw response mapping/결과 layout을 찾기 쉬운 파일로 분리하는 것이었다. 라인 수 감소보다 유지보수자가 "요청은 어디?", "mapping은 어디?", "결과 layout은 어디?"를 바로 찾게 만드는 데 초점을 뒀다.

## 5. 완료 작업 요약
| task | summary | report | exists |
| --- | --- | --- | --- |
| 1. FRONTEND-STRUCTURE-1-RUNOCR-FOLDER-MOVE | components/upload를 components/runocr로 이동하고 UploadWorkspace를 RunOcrWorkspace로 rename했다. | `docs/FRONTEND_STRUCTURE_1_RUNOCR_FOLDER_MOVE_20260522.md` | True |
| 2. FRONTEND-STRUCTURE-1B-RUNOCR-WORKSPACE-NAMING-CLEANUP | UploadWorkspace 계열 내부 식별자를 RunOcrWorkspace 계열로 정리했다. | `docs/FRONTEND_STRUCTURE_1B_RUNOCR_WORKSPACE_NAMING_CLEANUP_20260522.md` | True |
| 3. FRONTEND-STRUCTURE-2A-RUNOCR-BUILD-OCR-FORMDATA-EXTRACT | buildOcrFormData.ts를 생성하고 /ocr/extract FormData 구성을 분리했다. key parity PASS. | `docs/FRONTEND_STRUCTURE_2A_RUNOCR_BUILD_OCR_FORMDATA_EXTRACT_20260522.md` | True |
| 4. FRONTEND-STRUCTURE-2B-RUNOCR-REQUEST-EXTRACT | runOcrRequest.ts를 생성하고 endpoint, fetch, ok check, json parse를 분리했다. | `docs/FRONTEND_STRUCTURE_2B_RUNOCR_REQUEST_EXTRACT_20260522.md` | True |
| 5. FRONTEND-STRUCTURE-2C-RUNOCR-BUILD-RUN-OCR-RESULT-EXTRACT | mapOcrResponse.ts를 생성하고 buildRunOcrResult 순수 mapping을 분리했다. | `docs/FRONTEND_STRUCTURE_2C_RUNOCR_BUILD_RUN_OCR_RESULT_EXTRACT_20260522.md` | True |
| 6. MARKDOWN-V1-TRADE7-FIXTURE-REBAKE | trade_7 markdown fixture drift를 현재 backend actual 기준으로 rebake해 markdown runner 6/6 PASS를 회복했다. | `docs/MARKDOWN_V1_TRADE7_FIXTURE_REBAKE_20260522.md` | True |
| 7. FRONTEND-STRUCTURE-3A-RUNOCR-RESULT-LAYOUT-SPLIT | RunOcrResultLayout.tsx를 생성하고 결과 화면 layout을 node composition으로 분리했다. | `docs/FRONTEND_STRUCTURE_3A_RUNOCR_RESULT_LAYOUT_SPLIT_20260522.md` | True |
| 8. FRONTEND-STRUCTURE-3B-RUNOCR-DOC-COMMENTS | RunOCR 8개 파일에 file header/JSDoc을 추가하고 comments-only 검증을 완료했다. | `docs/FRONTEND_STRUCTURE_3B_RUNOCR_DOC_COMMENTS_20260522.md` | True |

## 6. 현재 RunOCR 구조
```text
src/components/runocr/
  RunOcrWorkspace.tsx
  ui/
    RunOcrResultLayout.tsx
    OcrResultPanel.tsx
    OcrDocViewer.tsx
    CornerAdjust.tsx
  utils/
    buildOcrFormData.ts
    runOcrRequest.ts
    mapOcrResponse.ts
```

| path | exists | lines | bytes |
| --- | --- | ---: | ---: |
| `src/components/runocr/RunOcrWorkspace.tsx` | True | 1556 | 66973 |
| `src/components/runocr/ui/RunOcrResultLayout.tsx` | True | 56 | 1813 |
| `src/components/runocr/ui/OcrResultPanel.tsx` | True | 1692 | 81677 |
| `src/components/runocr/ui/OcrDocViewer.tsx` | True | 250 | 10050 |
| `src/components/runocr/ui/CornerAdjust.tsx` | True | 197 | 7461 |
| `src/components/runocr/utils/buildOcrFormData.ts` | True | 54 | 2131 |
| `src/components/runocr/utils/runOcrRequest.ts` | True | 61 | 2750 |
| `src/components/runocr/utils/mapOcrResponse.ts` | True | 163 | 6791 |

## 7. 파일별 역할
| path | role | notes |
| --- | --- | --- |
| `src/components/runocr/RunOcrWorkspace.tsx` | RunOCR 전체 상태/흐름/orchestration | 파일/템플릿/모델 상태, OCR 실행, history/autofill 흐름, viewer/result 조립을 담당한다. |
| `src/components/runocr/ui/RunOcrResultLayout.tsx` | OCR 결과 화면 layout | viewer/resultPanel/scanOverlay/hiddenFileInput node 배치만 담당한다. |
| `src/components/runocr/ui/OcrResultPanel.tsx` | Preview/Custom/Validation/Clean JSON/Markdown/Raw JSON 결과 패널 | 결과 표시와 tab별 UI를 담당하며 helper 기반 출력 계약과 연결된다. |
| `src/components/runocr/ui/OcrDocViewer.tsx` | 문서 viewer 및 bbox overlay | 문서 이미지/PDF와 field overlay, 선택 interaction을 담당한다. |
| `src/components/runocr/ui/CornerAdjust.tsx` | normalized corner 보정 UI | 0~1 normalized corner 좌표를 표시하고 drag update를 상위로 전달한다. |
| `src/components/runocr/utils/buildOcrFormData.ts` | /ocr/extract FormData 구성 | backend multipart key 계약과 FormData key parity 검증 대상이다. |
| `src/components/runocr/utils/runOcrRequest.ts` | OCR API 호출 경계 | endpoint 결정, FormData 구성, fetch, ok/json 처리까지만 담당한다. |
| `src/components/runocr/utils/mapOcrResponse.ts` | raw OCR response -> OcrResult 순수 mapping | history/autofill/restore/React state에 의존하지 않는 mapping boundary다. |

## 8. 책임 경계
| responsibility | owner |
| --- | --- |
| OCR 요청 파라미터 구성 | `src/components/runocr/utils/buildOcrFormData.ts` |
| OCR API 호출 | `src/components/runocr/utils/runOcrRequest.ts` |
| raw response mapping | `src/components/runocr/utils/mapOcrResponse.ts` |
| 결과 화면 layout | `src/components/runocr/ui/RunOcrResultLayout.tsx` |
| 결과 표시 UI | `src/components/runocr/ui/OcrResultPanel.tsx` |
| 문서 viewer | `src/components/runocr/ui/OcrDocViewer.tsx` |
| RunOCR 실행 orchestration/history/autofill | `src/components/runocr/RunOcrWorkspace.tsx` |

## 9. 검증 상태
| check | status | detail |
| --- | --- | --- |
| typecheck | PASS | exit 0 |
| build | PASS | exit 0; known noise: ESLint: nextVitals is not iterable |
| table view model runner | PASS | 8/8 |
| Clean JSON runner | PASS | 9/9 |
| markdown fixture | PASS | 6/6 |
| FormData key parity | PASS | FRONTEND-STRUCTURE-2A |
| request boundary static check | PASS | FRONTEND-STRUCTURE-2B |
| response mapping boundary static check | PASS | FRONTEND-STRUCTURE-2C |
| result layout boundary static check | PASS | FRONTEND-STRUCTURE-3A |
| doc comments static check | PASS | FRONTEND-STRUCTURE-3B |

## 10. 남은 이슈
- runOcr() 본문에 autofill/history/restore orchestration 응집이 500+ 줄 남아 있다.
- RunOcrControls는 props 26개+ 위험이 있어 한 번에 큰 컴포넌트로 분리하면 안 된다.
- 기본 화면 main return은 아직 미분리 상태다.
- history/restore adapter 분리는 별도 precheck가 필요하다.
- ocr-server/data/templates.json dirty 상태가 남아 있다.
- TPL-95328E52 dirty 영향 precheck가 필요할 수 있다.
- build stderr의 ESLint: nextVitals is not iterable은 exit 0 non-blocking known issue다.
- TestWorkspace는 사용자 확인 전 작업 금지다.

## 11. RunOCR Cycle 2 재진입 조건
- Template folder ownership 정리 후 재진입한다.
- RunOcrControls는 큰 단일 컴포넌트가 아니라 작은 control group 단위로 precheck한다.
- 후보: TemplateTopbar, FileUploadPanel, ModelOptionPanel, RunButtonBar, TemplateHoverTooltip.

## 12. RunOCR Cycle 3 재진입 조건
- History/Restore 구조 정리 후 재진입한다.
- history/autofill orchestration adapter 분리를 검토한다.
- 후보: buildRunOcrHistoryRecord, applyRunOcrAutofill, restore/autofill adapter.

## 13. common/utils 이동 전 재점검
- feature 폴더 안정화 후 common/utils 이동 여부를 재점검한다.
- runocr/utils 중 common 후보가 있는지 확인한다.
- cleanJson/markdown/tableViewModel/invoiceTableDisplay와 import 경계를 확인한다.

## 14. 다음 추천 작업
1. Template folder ownership precheck
2. Template folder 1차 구조 정리
3. TPL-95328E52 dirty 영향 precheck
4. RunOCR Cycle 2는 Template 구조 정리 후 재진입
5. common/utils 이동은 feature 폴더 안정화 후 진행
6. TestWorkspace는 사용자 확인 후 진행

## 15. 주의사항
- TestWorkspace 작업은 사용자 확인 전 금지한다.
- common/utils 이동은 feature 폴더 안정화 후 진행한다.
- `ocr-server/data/templates.json` dirty 상태와 `TPL-95328E52` 영향은 별도 precheck로 다룬다.
- build stderr의 `ESLint: nextVitals is not iterable`은 exit 0 non-blocking known issue로 추적한다.

## 16. 현재 dirty 상태
이번 close-out에서 dirty 상태는 되돌리지 않았다.

```text
 M src/app/runocr/page.tsx
RM src/components/upload/UploadWorkspace.tsx -> src/components/runocr/RunOcrWorkspace.tsx
RM src/components/upload/CornerAdjust.tsx -> src/components/runocr/ui/CornerAdjust.tsx
RM src/components/upload/OcrDocViewer.tsx -> src/components/runocr/ui/OcrDocViewer.tsx
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
?? docs/FRONTEND_RUNOCR_COMMENT_PLAN_MAP_20260522.csv
?? docs/FRONTEND_RUNOCR_COMMENT_PLAN_PRECHECK_20260522.json
?? docs/FRONTEND_RUNOCR_COMMENT_PLAN_PRECHECK_20260522.md
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
?? docs/FRONTEND_STRUCTURE_3A_RUNOCR_RESULT_LAYOUT_SPLIT_20260522.json
?? docs/FRONTEND_STRUCTURE_3A_RUNOCR_RESULT_LAYOUT_SPLIT_20260522.md
?? docs/FRONTEND_STRUCTURE_3B_RUNOCR_DOC_COMMENTS_20260522.json
?? docs/FRONTEND_STRUCTURE_3B_RUNOCR_DOC_COMMENTS_20260522.md
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
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_RUNOCR_DOC_COMMENTS_20260522_20260521.json
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_RUNOCR_DOC_COMMENTS_20260522_20260521.md
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
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_RUNOCR_RESULT_LAYOUT_SPLIT_20260522_20260521.json
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_RUNOCR_RESULT_LAYOUT_SPLIT_20260522_20260521.md
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
?? src/components/runocr/ui/RunOcrResultLayout.tsx
?? src/components/runocr/utils/
?? src/lib/cleanJsonBuilder.ts
?? src/lib/markdownReportBuilder.ts
?? src/lib/ocrResultFormatters.ts
?? src/lib/structuredTableViewModel.ts
?? tmp/
?? ../ocr-server/requirements-aws.txt
```
