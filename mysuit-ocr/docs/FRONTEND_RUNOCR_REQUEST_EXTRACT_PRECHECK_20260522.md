# FRONTEND RUNOCR REQUEST EXTRACT PRECHECK 20260522

## 1. 사용 도구와 모델
- 사용 도구: Codex
- 사용 모델: Codex
- 작업명: `CODEX_FRONTEND_RUNOCR_REQUEST_EXTRACT_PRECHECK_NO_PROD_MODIFY`

## 2. 코드 수정 여부
- 운영 코드 수정 없음.
- `RunOcrWorkspace.tsx` 수정 없음.
- `runOcrRequest.ts` 생성 없음.
- `buildOcrFormData.ts`, `src/components/runocr/ui/*`, `src/lib/*` 수정 없음.
- import 수정/파일 이동/fixture 수정 없음.

## 3. 생성 파일
- `tmp/codex_frontend_runocr_request_extract_precheck.py`
- `docs/FRONTEND_RUNOCR_REQUEST_EXTRACT_PRECHECK_20260522.md`
- `docs/FRONTEND_RUNOCR_REQUEST_EXTRACT_PRECHECK_20260522.json`
- `docs/FRONTEND_RUNOCR_REQUEST_EXTRACT_MAP_20260522.csv`

## 4. 분석 범위
- 필수: `src/components/runocr/RunOcrWorkspace.tsx`
- 필수: `src/components/runocr/utils/buildOcrFormData.ts`
- 참고: `FRONTEND_STRUCTURE_2A_RUNOCR_BUILD_OCR_FORMDATA_EXTRACT_20260522`, RunOCR utils split precheck

## 5. 현재 request flow 요약
| item | line | detail |
| --- | --- | --- |
| runOcr line range | {"start": 826, "end": 1093} |  |
| buildOcrFormData call | 836 | const formData = buildOcrFormData({ |
| fetch call | 849 | const res = await fetch(ocrEndpoint, { |
| endpoint | 848 | const ocrEndpoint = backendBase ? `${backendBase}/ocr/extract` : "/api/ocr-extract"; const res = await fetch(ocrEndpoint, { |
| response.ok | 853 | if (!res.ok) throw new Error("OCR 요청 실패"); |
| response.json | 854 | const json = await res.json(); |
| catch | 946 | } catch (err) { |
| finally | 1090 | } finally { |

요약:
- `runOcr()` 안에서 `buildOcrFormData` 호출 후 endpoint를 결정하고 `fetch(POST)`를 수행한다.
- `response.ok` 실패 시 `Error`를 throw하고, 성공 시 `response.json()` 결과를 후속 mapping/autofill/history 로직에 넘긴다.
- `setIsOcrRunning(true/false)`와 catch alert/history fail record는 workspace에 남아 있다.

## 6. runOcrRequest 후보 경계 비교
| id | scope | inputs | outputs | pros | cons | risk | recommendation |
| --- | --- | --- | --- | --- | --- | --- | --- |
| option_1_fetch_only | runOcrRequest(formData, endpoint) returns raw Response | ["FormData", "endpoint"] | ["Response"] | smallest extraction; response mapping untouched | caller still owns ok/json boilerplate, so findability improvement is limited | LOW | NOT_PRIMARY |
| option_2_fetch_ok_json | runOcrRequest(input) builds FormData, POSTs, checks ok, returns parsed JSON | ["BuildOcrFormDataInput", "endpoint?"] | ["unknown/raw OCR response JSON"] | clear OCR API request location; endpoint/fetch/ok/json co-located | introduces helper-thrown Error path; message parity must be kept | LOW-MEDIUM | RECOMMENDED |
| option_3_request_error_normalization | option 2 plus normalized error message/status details | ["BuildOcrFormDataInput", "endpoint?", "errorMessage?"] | ["unknown/raw OCR response JSON"] | future-friendly API boundary | more behavior than current code; can accidentally alter UI alert/error console behavior | MEDIUM | DO_LATER_OR_KEEP_MINIMAL |

## 7. input 타입 초안
권장:

```ts
import type { BuildOcrFormDataInput } from "./buildOcrFormData";

export type RunOcrRequestInput = BuildOcrFormDataInput & {
  endpoint?: string;
};
```

판단:
- `BuildOcrFormDataInput`을 그대로 재사용할 수 있다.
- endpoint는 helper 내부에서 `NEXT_PUBLIC_BACKEND_URL` 기준으로 계산하거나, 테스트 용이성을 위해 optional input으로 받을 수 있다.
- 현재 auth header, timeout, AbortSignal은 없다. Phase 2B에는 추가하지 않는 것이 안전하다.

## 8. output 타입 초안
권장:

```ts
export type RunOcrRequestResult = unknown;
```

또는 실제 작업에서는 최소 alias:

```ts
export type RunOcrRawResponse = Record<string, unknown>;
```

판단:
- Phase 2B에서는 response JSON을 그대로 반환한다.
- `mapOcrResponse`는 후순위라 raw response shape를 바꾸지 않는다.

## 9. loading/error 처리 방침
- loading state: `RunOcrWorkspace` 유지.
- catch/alert/fail history record: `RunOcrWorkspace` 유지.
- `runOcrRequest`는 성공 시 JSON 반환, 실패 시 현재와 동일 메시지의 `Error` throw까지만 담당.

## 10. history/restore/autofill 영향
- response 이후 `autofillSuggestions`, `autofillSummary`, `appendHistoryRun`, `syncHistoryIndexAndDetailOnCreate`, `setOcrResult` 흐름은 그대로 workspace에 둔다.
- `runOcrRequest` 추출은 `const json = await runOcrRequest(...)` 형태만 바꾸면 mapping/history/restore에 직접 영향이 없다.
- `mapOcrResponse`는 history/autofill과 얽혀 있으므로 Phase 2B에서 제외한다.

## 11. FormData key parity 영향
- `buildOcrFormData`를 `runOcrRequest` 내부에서 호출해도 input이 같으면 keys는 유지된다.
- 2A parity 기준: `["file","template_id","regions","model_id","documentType"]`.
- 실제 2B에서는 기존 FormData key parity check를 재사용하고, request boundary static check를 추가하는 것이 좋다.

## 12. Phase 2B 추천 범위
추천: **후보 2(fetch + response.ok + json)**.
- 신규 `runOcrRequest.ts` 생성.
- `runOcrRequest(input)` 내부에서 `buildOcrFormData(input)` 호출.
- endpoint 계산, `fetch`, `res.ok`, `res.json()`까지만 포함.
- loading/error UI state, response mapping, history/restore/autofill은 유지.

## 13. Phase 2B 예상 파일
| path | change | notes |
| --- | --- | --- |
| src/components/runocr/utils/runOcrRequest.ts | create | Contains endpoint calculation, buildOcrFormData call, fetch POST, ok check, json parse. |
| src/components/runocr/RunOcrWorkspace.tsx | modify | Replace local formData/endpoint/fetch/ok/json block with runOcrRequest call only. |
| src/components/runocr/utils/buildOcrFormData.ts | no behavior change | May only need existing BuildOcrFormDataInput export; no logic change expected. |
| tmp/check_runocr_request_boundary_2b.mjs | optional create | Static check candidate for request helper boundary. |

## 14. Phase 2B 검증 전략
| validation |
| --- |
| npm run typecheck |
| npm run build |
| node tmp/check_table_view_model_v1_fixtures_js.mjs |
| node tmp/check_clean_json_v1_fixtures_js.mjs |
| python tmp/codex_markdown_contract_fixture_lock.py --check ... |
| FormData key parity check: before/after same order and same set |
| request boundary static check: runOcrRequest imports buildOcrFormData and returns parsed JSON |
| /runocr manual smoke with invoice upload |

## 15. dirty 상태
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
| ?? docs/FRONTEND_RUNOCR_UTILS_SPLIT_MAP_20260522.csv |
| ?? docs/FRONTEND_RUNOCR_UTILS_SPLIT_PRECHECK_20260522.json |
| ?? docs/FRONTEND_RUNOCR_UTILS_SPLIT_PRECHECK_20260522.md |
| ?? docs/FRONTEND_STRUCTURE_1B_RUNOCR_WORKSPACE_NAMING_CLEANUP_20260522.json |
| ?? docs/FRONTEND_STRUCTURE_1B_RUNOCR_WORKSPACE_NAMING_CLEANUP_20260522.md |
| ?? docs/FRONTEND_STRUCTURE_1_RUNOCR_FOLDER_MOVE_20260522.json |
| ?? docs/FRONTEND_STRUCTURE_1_RUNOCR_FOLDER_MOVE_20260522.md |
| ?? docs/FRONTEND_STRUCTURE_2A_RUNOCR_BUILD_OCR_FORMDATA_EXTRACT_20260522.json |
| ?? docs/FRONTEND_STRUCTURE_2A_RUNOCR_BUILD_OCR_FORMDATA_EXTRACT_20260522.md |
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

## 16. Typecheck/Build 결과
| command | status | exit | seconds | known stderr noise |
| --- | --- | ---: | ---: | --- |
| npm.cmd run typecheck | PASS | 0 | 1.783 | False |
| npm.cmd run build | PASS | 0 | 15.434 | True |

## 17. 다음 작업 제안
- `CODEX_FRONTEND_RUNOCR_REQUEST_EXTRACT_2B_FETCH_OK_JSON`로 실제 추출을 진행한다.
- `runOcrRequest.ts`는 request boundary만 담당하고 mapping/history/restore/UI는 건드리지 않는다.
- 검증은 typecheck/build + FormData key parity + runners + `/runocr` manual smoke를 권장한다.
