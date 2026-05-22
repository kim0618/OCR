# FRONTEND RUNOCR RESPONSE MAPPING PRECHECK 20260522

## 1. 사용 도구와 모델
- 사용 도구: Codex
- 사용 모델: Codex
- 작업명: `CODEX_FRONTEND_RUNOCR_RESPONSE_MAPPING_PRECHECK_NO_PROD_MODIFY`

## 2. 코드 수정 여부
- 운영 코드 수정 없음.
- `RunOcrWorkspace.tsx` 수정 없음.
- `mapOcrResponse.ts` 생성 없음.
- `runOcrRequest.ts`, `buildOcrFormData.ts`, `runocr/ui/*`, `src/lib/*` 수정 없음.
- import 수정/파일 이동/fixture 수정 없음.

## 3. 생성 파일
- `tmp/codex_frontend_runocr_response_mapping_precheck.py`
- `docs/FRONTEND_RUNOCR_RESPONSE_MAPPING_PRECHECK_20260522.md`
- `docs/FRONTEND_RUNOCR_RESPONSE_MAPPING_PRECHECK_20260522.json`
- `docs/FRONTEND_RUNOCR_RESPONSE_MAPPING_MAP_20260522.csv`

## 4. 분석 범위
- `src/components/runocr/RunOcrWorkspace.tsx`
- `src/components/runocr/utils/runOcrRequest.ts`
- `src/components/runocr/utils/buildOcrFormData.ts`
- 참고: history/autofill 관련 흐름과 최근 2A/2B 리포트

## 5. runOcr response flow 요약
| item | line/range | detail |
| --- | --- | --- |
| runOcrRequest call | 838 | const json = await runOcrRequest({ |
| raw json variable | json |  |
| buildRunOcrResult call | 848 | const runResult = isRunOcr ? buildRunOcrResult(json, activeTemplate) : json; |
| buildRunOcrResult definition | {"start": 436, "end": 527} |  |
| autofill flow | {"start": 854, "end": 950} | 22 hits |
| history flow | {"start": 970, "end": 1069} | 13 hits |
| set result | [{"line": 952, "keywords": ["setOcrResult"], "snippet": "setOcrResult(runResult);"}, {"line": 954, "keywords": ["setProcessedImageUrl"], "snippet": "setProcessedImageUrl(runResult.processed_image);"}, {"line": 957, "keywords": ["setCanvasRegions"], "snippet": "setCanvasRegions((prev) => {"}] |  |

요약:
- `runOcrRequest`는 raw `json`을 반환한다.
- `buildRunOcrResult(json, activeTemplate)`가 autofill 전 화면용 `OcrResult`를 만든다.
- 이후 `rawOcrFields`, `originalRunFields`, autofill, source bbox attach, history snapshot, `setOcrResult`가 한 흐름에 이어진다.

## 6. buildRunOcrResult 책임 분석
- 정의 범위: {'start': 436, 'end': 527}
- signature: `function buildRunOcrResult(raw: any, template?: TemplateItem): OcrResult {`
- 입력: ['raw: any', 'template?: TemplateItem']
- 출력: OcrResult
- raw fields read: ['fields', 'finance_fields', 'receipt_fields']
- template dependencies: ['template.fields', 'template.regions', 'template.mode', 'field.enField/koField/no']
- React state/closure dependency: []
- history 포함: False
- autofill 포함: False

판정: `buildRunOcrResult`만 옮기는 것은 `mapOcrResponse.ts`의 최소 안전 범위가 될 수 있다.

## 7. raw response 사용처
| line | purpose | moveToMapOcrResponse | snippet |
| --- | --- | --- | --- |
| 847 | unknown | review | const rawOcrFields: OcrFieldResult[] = Array.isArray(json?.fields) ? (json.fields as OcrFieldResult[]) : []; |
| 848 | initial display result mapping | yes, if buildRunOcrResult-only extraction | const runResult = isRunOcr ? buildRunOcrResult(json, activeTemplate) : json; |
| 865 | autofill business number text source | no for Phase 2C; keep with autofill | json?.full_text, |
| 869 | autofill business number text source | no for Phase 2C; keep with autofill | json?.receipt_fields?.["사업자번호"], |
| 971 | history raw OCR lines | no for Phase 2C; keep with history | Array.isArray((json as any)?.ocr_lines) ? (json as any).ocr_lines : []; |
| 1044 | history/detail snapshot | no for Phase 2C; keep with history | processing_time: Number(json?.processing_time) \|\| 0, |
| 1058 | history/detail snapshot | no for Phase 2C; keep with history | const rawDocFields = (json as Record<string, unknown>)?.document_fields as |

## 8. autofill/restore 경계
- autofill 시작은 business text 구성과 `extractBizNumber` 이후이다.
- raw json의 `full_text`, `receipt_fields["사업자번호"]`, raw fields를 함께 사용한다.
- `applyAutofillToOutputFields`가 `runResult.fields`를 변경하고, 그 결과가 history output_fields에도 들어간다.
- Phase 2C에서는 autofill/restore를 `mapOcrResponse`에 넣지 않는 것이 안전하다.

## 9. history 저장 경계
- 성공 history record는 `appendHistoryRun`에서 생성된다.
- 실패 history record도 catch 안에서 생성된다.
- `processing_time`, `document_fields`, `ocr_lines`, `runResult.processed_image`, `outputFieldsForHistory`, `autofillSummary`가 얽혀 있다.
- Phase 2C에서 history snapshot은 제외하고, 이후 `runOcrHistoryAdapter.ts` 후보로 별도 precheck가 적절하다.

## 10. mapOcrResponse 후보 경계 비교
| id | summary | inputs | outputs | pros | cons | risk | recommendation |
| --- | --- | --- | --- | --- | --- | --- | --- |
| option_1_buildRunOcrResult_only | Move only buildRunOcrResult to utils/mapOcrResponse.ts | ["raw JSON", "template?: TemplateItem"] | ["OcrResult before autofill/source bbox/history"] | Smallest pure boundary; no history/autofill movement; findability improves. | Workspace still contains large post-mapping flow. | LOW-MEDIUM | RECOMMENDED_IF_PHASE_2C_RUNS |
| option_2_mapping_plus_normalize | Move buildRunOcrResult plus rawOcrFields/originalRunFields normalize | ["raw JSON", "template", "isRunOcr"] | ["runResult", "rawOcrFields", "originalRunFields"] | Captures a more useful response mapping bundle. | Starts touching source markers and later attachSourceBboxes/autofill assumptions. | MEDIUM-HIGH | DO_LATER |
| option_3_mapping_plus_autofill | Move response mapping and autofill application together | ["raw JSON", "template", "selectedFile", "restore/autofill dependencies"] | ["runResult with autofill", "autofillSummary", "autofillSuggestions"] | Removes a large chunk from workspace. | Crosses restore/autofill feature boundary and business-number extraction policy. | HIGH | DEFER |
| option_4_mapping_plus_history_snapshot | Move response mapping, autofill, and history snapshot building | ["raw JSON", "run context", "template", "file", "history deps"] | ["state updates or large composite payload"] | Largest line-count reduction. | Too much responsibility; high regression risk; violates clear boundary goal. | VERY_HIGH | DO_NOT_DO_IN_PHASE_2C |

## 11. Phase 2C 추천 범위
권장: **B. buildRunOcrResult만 `utils/mapOcrResponse.ts`로 이동**.

조건:
- `autofill`, `history`, `attachSourceBboxes`, `buildResultRegions`, `setOcrResult`는 유지.
- 함수 이름은 `buildRunOcrResult` 유지 또는 `mapOcrResponseToRunOcrResult`로 명확화 가능.
- input/output contract가 명확한 순수 함수만 옮긴다.

대안:
- 2C를 보류하고 UI split/Template 정리로 이동해도 된다. 다만 “OCR raw response mapping은 어디?”라는 목표를 충족하려면 buildRunOcrResult-only 추출은 가치가 있다.

## 12. Phase 2C 예상 파일
| path | change | notes |
| --- | --- | --- |
| src/components/runocr/utils/mapOcrResponse.ts | create if Phase 2C runs | Only move buildRunOcrResult or equivalent pure mapping. |
| src/components/runocr/RunOcrWorkspace.tsx | modify if Phase 2C runs | Import mapping helper and remove local buildRunOcrResult only. |
| tmp/check_runocr_response_mapping_boundary_2c.mjs | optional create | Static boundary check: no history/autofill/React imports in mapping util. |

## 13. 검증 전략
| validation |
| --- |
| npm run typecheck |
| npm run build |
| node tmp/check_table_view_model_v1_fixtures_js.mjs |
| node tmp/check_clean_json_v1_fixtures_js.mjs |
| python tmp/codex_markdown_contract_fixture_lock.py --check ... |
| FormData key parity check |
| request boundary static check |
| response mapping boundary static check: mapOcrResponse does not import history/autofill/React |
| /runocr manual smoke |
| history save smoke if mapping boundary expands later |

## 14. dirty 상태
현재 dirty 상태는 기록만 했고 되돌리지 않았다.

| git status --short |
| --- |
|  M src/app/runocr/page.tsx |
| RM src/components/upload/UploadWorkspace.tsx -> src/components/runocr/RunOcrWorkspace.tsx |
| R  src/components/upload/CornerAdjust.tsx -> src/components/runocr/ui/CornerAdjust.tsx |
| R  src/components/upload/OcrDocViewer.tsx -> src/components/runocr/ui/OcrDocViewer.tsx |
| RM src/components/upload/OcrResultPanel.tsx -> src/components/runocr/ui/OcrResultPanel.tsx |
|  M src/lib/invoiceTableDisplay.ts |
|  M ../ocr-server/data/review_log.jsonl |
|  M ../ocr-server/data/templates.json |
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
| ?? docs/FRONTEND_RUNOCR_FOLDER_MOVE_PRECHECK_20260522.json |
| ?? docs/FRONTEND_RUNOCR_FOLDER_MOVE_PRECHECK_20260522.md |
| ?? docs/FRONTEND_RUNOCR_FOLDER_MOVE_PRECHECK_MAP_20260522.csv |
| ?? docs/FRONTEND_RUNOCR_REQUEST_EXTRACT_MAP_20260522.csv |
| ?? docs/FRONTEND_RUNOCR_REQUEST_EXTRACT_PRECHECK_20260522.json |
| ?? docs/FRONTEND_RUNOCR_REQUEST_EXTRACT_PRECHECK_20260522.md |
| ?? docs/FRONTEND_RUNOCR_UTILS_SPLIT_MAP_20260522.csv |
| ?? docs/FRONTEND_RUNOCR_UTILS_SPLIT_PRECHECK_20260522.json |
| ?? docs/FRONTEND_RUNOCR_UTILS_SPLIT_PRECHECK_20260522.md |
| ?? docs/FRONTEND_STRUCTURE_1B_RUNOCR_WORKSPACE_NAMING_CLEANUP_20260522.json |
| ?? docs/FRONTEND_STRUCTURE_1B_RUNOCR_WORKSPACE_NAMING_CLEANUP_20260522.md |
| ?? docs/FRONTEND_STRUCTURE_1_RUNOCR_FOLDER_MOVE_20260522.json |
| ?? docs/FRONTEND_STRUCTURE_1_RUNOCR_FOLDER_MOVE_20260522.md |
| ?? docs/FRONTEND_STRUCTURE_2A_RUNOCR_BUILD_OCR_FORMDATA_EXTRACT_20260522.json |
| ?? docs/FRONTEND_STRUCTURE_2A_RUNOCR_BUILD_OCR_FORMDATA_EXTRACT_20260522.md |
| ?? docs/FRONTEND_STRUCTURE_2B_RUNOCR_REQUEST_EXTRACT_20260522.json |
| ?? docs/FRONTEND_STRUCTURE_2B_RUNOCR_REQUEST_EXTRACT_20260522.md |
| ?? docs/FRONTEND_TARGET_STRUCTURE_OWNERSHIP_MAP_20260522.csv |
| ?? docs/FRONTEND_TARGET_STRUCTURE_OWNERSHIP_PRECHECK_20260522.json |
| ?? docs/FRONTEND_TARGET_STRUCTURE_OWNERSHIP_PRECHECK_20260522.md |
| ?? docs/MARKDOWN_V1_CONTRACT_20260521.json |
| ?? docs/MARKDOWN_V1_CONTRACT_20260521.md |
| ?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_3D3_20260521_20260521.json |
| ?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_3D3_20260521_20260521.md |
| ?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_3D4_20260522_20260521.json |
| ?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_3D4_20260522_20260521.md |
| ?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_RUNOCR_FOLDER_MOVE_20260522_20260521.json |
| ?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_RUNOCR_FOLDER_MOVE_20260522_20260521.md |
| ?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_RUNOCR_FORMDATA_EXTRACT_20260522_20260521.json |
| ?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_RUNOCR_FORMDATA_EXTRACT_20260522_20260521.md |
| ?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_RUNOCR_NAMING_CLEANUP_20260522_20260521.json |
| ?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_RUNOCR_NAMING_CLEANUP_20260522_20260521.md |
| ?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_RUNOCR_REQUEST_EXTRACT_20260522_20260521.json |
| ?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_RUNOCR_REQUEST_EXTRACT_20260522_20260521.md |
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
| ?? src/components/runocr/utils/ |
| ?? src/lib/cleanJsonBuilder.ts |
| ?? src/lib/markdownReportBuilder.ts |
| ?? src/lib/ocrResultFormatters.ts |
| ?? src/lib/structuredTableViewModel.ts |
| ?? tmp/ |
| ?? ../ocr-server/requirements-aws.txt |

## 15. Typecheck/Build 결과
| command | status | exit | seconds | known stderr noise |
| --- | --- | ---: | ---: | --- |
| npm.cmd run typecheck | PASS | 0 | 2.306 | False |
| npm.cmd run build | PASS | 0 | 17.29 | True |

## 16. 다음 작업 제안
- 실제 Phase 2C를 한다면 `CODEX_FRONTEND_RUNOCR_RESPONSE_MAPPING_2C_BUILD_RESULT_ONLY`로 작게 진행한다.
- `mapOcrResponse.ts`에는 `buildRunOcrResult`만 이동한다.
- autofill/history/restore는 별도 adapter precheck 전까지 유지한다.
