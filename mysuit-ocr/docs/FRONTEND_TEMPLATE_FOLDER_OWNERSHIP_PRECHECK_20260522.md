# FRONTEND TEMPLATE FOLDER OWNERSHIP PRECHECK 20260522

## 1. 사용 도구와 모델
- 도구: Codex
- 모델: Codex
- 작업명: CODEX_FRONTEND_TEMPLATE_FOLDER_OWNERSHIP_PRECHECK_NO_PROD_MODIFY

## 2. 코드 수정 여부
- 운영 코드 수정: 없음
- 파일 이동/import 수정/리팩토링/주석 추가/fixture/templates/backend 수정: 없음
- 현재 dirty 상태는 되돌리지 않았다.

## 3. 생성 파일
- `tmp/codex_frontend_template_folder_ownership_precheck.py`
- `docs/FRONTEND_TEMPLATE_FOLDER_OWNERSHIP_PRECHECK_20260522.md`
- `docs/FRONTEND_TEMPLATE_FOLDER_OWNERSHIP_PRECHECK_20260522.json`
- `docs/FRONTEND_TEMPLATE_FOLDER_OWNERSHIP_MAP_20260522.csv`

## 4. 분석 범위
- `src/components/ocr/*`
- `src/components/ocr/core/*`
- `src/components/template/*`
- `src/app/template/page.tsx`
- `src/app/ocr/page.tsx`
- `src/app/runocr/page.tsx`
- `src/components/runocr/*`
- `src/components/test/TestWorkspace.tsx` 읽기 전용
- `src/lib/*`, `src/types/*` 참고

## 5. Template 관련 파일 목록
| currentPath | lines | ownership | targetPath | risk | notes |
| --- | ---: | --- | --- | --- | --- |
| `src/app/template/page.tsx` | 281 | TEMPLATE_WORKSPACE | `src/app/template/page.tsx` | MEDIUM | Template route의 실제 entry. OcrAnnotator와 UnstructuredBuilder를 직접 조립한다. |
| `src/app/ocr/page.tsx` | 48 | REVIEW_NEEDED | `src/app/ocr/page.tsx` | HIGH | OcrAnnotator와 TemplateWorkspace를 직접 import한다. Template 이동 시 legacy route 유지 여부를 먼저 결정해야 한다. |
| `src/components/ocr/TemplateWorkspace.tsx` | 180 | TEMPLATE_WORKSPACE | `src/components/template/TemplateWorkspace.tsx` | LOW | 현재 /ocr route에서 사용. 목표 구조상 components/template 루트로 이동 후보. |
| `src/components/ocr/OcrAnnotator.tsx` | 442 | TEMPLATE_PRIVATE_UI | `src/components/template/ui/OcrAnnotator.tsx` | HIGH | Template page와 legacy /ocr route에서 dynamic import. canvas/right panel/core/save 흐름을 품고 있어 Phase 1에서는 보류 권장. |
| `src/components/ocr/OcrCanvasPane.tsx` | 1527 | RUNOCR_SHARED_CANDIDATE | `src/common/ui/OcrCanvasPane.tsx 또는 src/components/template/ui/OcrCanvasPane.tsx` | VERY_HIGH | Template editor와 RunOCR Custom tab이 동시에 사용한다. 바로 template 전용으로 이동하면 RunOCR import 영향이 크다. |
| `src/components/ocr/OcrRightPanel.tsx` | 507 | TEMPLATE_PRIVATE_UI | `src/components/template/ui/TemplateRightPanel.tsx` | HIGH | Template region metadata/documentType/table controls에 가깝다. rename은 별도 phase 권장. |
| `src/components/ocr/core/types.ts` | 110 | COMMON_UTIL_CANDIDATE | `src/common/types/ocrCanvas.ts 또는 src/components/template/utils/types.ts` | HIGH | RunOCR OcrCanvasPane도 의존하므로 common/types 후보. common 이동은 feature 안정화 후. |
| `src/components/ocr/core/table.ts` | 151 | TEMPLATE_PRIVATE_UTIL | `src/components/template/utils/table.ts` | MEDIUM | Template table column definition의 기반 후보. |
| `src/components/ocr/core/ops.ts` | 99 | TEMPLATE_PRIVATE_UTIL | `src/components/template/utils/ops.ts` | HIGH | region add/update/delete/geometry 성격. OcrAnnotator와 같이 이동하는 phase가 안전하다. |
| `src/components/ocr/core/export.ts` | 90 | TEMPLATE_PRIVATE_UTIL | `src/components/template/utils/templateMapper.ts` | MEDIUM | 목표 구조의 templateMapper.ts 후보. templates.json contract와 연결되어 검증 필요. |
| `src/components/template/UnstructuredBuilder.tsx` | 311 | TEMPLATE_PRIVATE_UI | `src/components/template/ui/UnstructuredBuilder.tsx` | MEDIUM | 이미 template 폴더에 있으나 ui 하위로 이동 후보. |
| `src/components/common/FileDropzone.tsx` | 105 | COMMON_UI_CANDIDATE | `src/common/ui/FileDropzone.tsx` | MEDIUM | RunOCR에서 사용. Template에서도 재사용 가능하지만 common 이동은 별도 phase. |
| `src/components/common/RequireLogin.tsx` | 35 | COMMON_UI_CANDIDATE | `src/common/ui/RequireLogin.tsx` | LOW | route guard 성격. Template 전용 아님. |
| `src/components/runocr/RunOcrWorkspace.tsx` | 1556 | DO_NOT_MOVE_YET | `src/components/runocr/RunOcrWorkspace.tsx` | VERY_HIGH | OcrCanvasPane 공유 여부 판단 때문에 읽기 대상. 이번 Template move 범위 아님. |
| `src/components/test/TestWorkspace.tsx` | 6409 | TEST_ONLY_OR_TEST_SHARED | `NO_MOVE_WITHOUT_USER_CONFIRMATION` | VERY_HIGH | 사용자 확인 전 작업 금지. 이번 precheck에서는 읽기/영향 기록만. |

## 6. importedBy 분석
| file | importedBy | imports |
| --- | --- | --- |
| `src/app/template/page.tsx` | - | src/components/layout/AppShell.tsx, src/components/ocr/OcrAnnotator.tsx, src/components/template/UnstructuredBuilder.tsx, src/lib/imageStore.ts |
| `src/app/ocr/page.tsx` | - | src/components/layout/AppShell.tsx, src/components/ocr/OcrAnnotator.tsx, src/components/ocr/TemplateWorkspace.tsx |
| `src/components/ocr/TemplateWorkspace.tsx` | src/app/ocr/page.tsx | src/components/common/AppProviders.tsx |
| `src/components/ocr/OcrAnnotator.tsx` | src/app/ocr/page.tsx, src/app/template/page.tsx | src/components/common/AppProviders.tsx, src/components/ocr/OcrCanvasPane.tsx, src/components/ocr/OcrRightPanel.tsx, src/components/ocr/core/export.ts, src/components/ocr/core/types.ts, src/lib/imageStore.ts |
| `src/components/ocr/OcrCanvasPane.tsx` | src/components/ocr/OcrAnnotator.tsx, src/components/runocr/RunOcrWorkspace.tsx | src/components/common/FileDropzone.tsx, src/components/ocr/core/ops.ts, src/components/ocr/core/table.ts, src/components/ocr/core/types.ts |
| `src/components/ocr/OcrRightPanel.tsx` | src/components/ocr/OcrAnnotator.tsx | src/components/ocr/core/ops.ts, src/components/ocr/core/table.ts, src/components/ocr/core/types.ts |
| `src/components/ocr/core/types.ts` | src/components/ocr/OcrAnnotator.tsx, src/components/ocr/OcrCanvasPane.tsx, src/components/ocr/OcrRightPanel.tsx, src/components/ocr/core/export.ts, src/components/ocr/core/ops.ts, src/components/ocr/core/table.ts, src/components/runocr/RunOcrWorkspace.tsx, src/components/runocr/utils/buildOcrFormData.ts | - |
| `src/components/ocr/core/table.ts` | src/components/ocr/OcrCanvasPane.tsx, src/components/ocr/OcrRightPanel.tsx, src/components/ocr/core/export.ts | src/components/ocr/core/ops.ts, src/components/ocr/core/types.ts |
| `src/components/ocr/core/ops.ts` | src/components/ocr/OcrCanvasPane.tsx, src/components/ocr/OcrRightPanel.tsx, src/components/ocr/core/export.ts, src/components/ocr/core/table.ts | src/components/ocr/core/types.ts |
| `src/components/ocr/core/export.ts` | src/components/ocr/OcrAnnotator.tsx | src/components/ocr/core/ops.ts, src/components/ocr/core/table.ts, src/components/ocr/core/types.ts |
| `src/components/template/UnstructuredBuilder.tsx` | src/app/template/page.tsx | src/components/common/AppProviders.tsx |
| `src/components/common/FileDropzone.tsx` | src/components/ocr/OcrCanvasPane.tsx, src/components/runocr/RunOcrWorkspace.tsx | - |
| `src/components/common/RequireLogin.tsx` | src/app/autorestore/page.tsx, src/app/history/page.tsx | src/lib/login.ts |
| `src/components/runocr/RunOcrWorkspace.tsx` | src/app/runocr/page.tsx | src/components/common/AppProviders.tsx, src/components/common/FileDropzone.tsx, src/components/ocr/OcrCanvasPane.tsx, src/components/ocr/core/types.ts, src/components/runocr/ui/CornerAdjust.tsx, src/components/runocr/ui/OcrDocViewer.tsx, src/components/runocr/ui/OcrResultPanel.tsx, src/components/runocr/ui/RunOcrResultLayout.tsx, src/components/runocr/utils/mapOcrResponse.ts, src/components/runocr/utils/runOcrRequest.ts, src/lib/autofillEngine.ts, src/lib/bizNumber.ts, src/lib/historyStore.ts, src/lib/imageStore.ts |
| `src/components/test/TestWorkspace.tsx` | src/app/test/page.tsx | src/components/common/AppProviders.tsx, src/components/test/core/autofill.ts, src/components/test/core/extract.ts, src/components/test/core/finalize.ts, src/components/test/core/match.ts, src/components/test/core/types.ts, src/lib/bizNumber.ts, src/lib/invoiceTableDisplay.ts, src/lib/profiles.ts, src/lib/testsets.ts |

## 7. ownership 분류
- `TEMPLATE_WORKSPACE`: route/workspace entry 성격. Phase 1 이동 후보.
- `TEMPLATE_PRIVATE_UI`: Template 전용 UI. annotation/canvas/save와 얽힌 파일은 Phase 2 이후.
- `TEMPLATE_PRIVATE_UTIL`: Template 전용 operation/export/table helper.
- `RUNOCR_SHARED_CANDIDATE`: RunOCR와 Template이 공유 중이라 바로 template 전용 이동 금지.
- `COMMON_UI_CANDIDATE` / `COMMON_UTIL_CANDIDATE`: feature 안정화 후 common 전환 후보.
- `TEST_ONLY_OR_TEST_SHARED`: 사용자 확인 전 이동 금지.

## 8. targetPath 제안
상세 targetPath는 위 표와 JSON/CSV에 기록했다. 핵심은 `TemplateWorkspace`는 `components/template` 루트로, Template 전용 UI는 `components/template/ui`, Template 전용 로직은 `components/template/utils`, 공유 canvas/type은 common 후보로 둔다는 것이다.

## 9. 위험도 평가
- LOW: `TemplateWorkspace` route/workspace 이동처럼 import 영향이 작음.
- MEDIUM: `UnstructuredBuilder`, `export.ts`, `table.ts`처럼 제한적 import 수정과 route smoke가 필요함.
- HIGH: `OcrAnnotator`, `OcrRightPanel`, `ops.ts`처럼 annotation/save/region metadata와 얽힘.
- VERY_HIGH: `OcrCanvasPane`, `TestWorkspace`, RunOCR 공유 파일처럼 다중 feature 영향이 큼.

## 10. Phase 1 이동 추천
- 추천: A. route/workspace만 먼저 이동
- 범위:
  - src/components/ocr/TemplateWorkspace.tsx -> src/components/template/TemplateWorkspace.tsx
  - src/app/ocr/page.tsx 및 관련 route import만 최소 수정
  - OcrAnnotator/OcrCanvasPane/OcrRightPanel/core는 그대로 둔다
  - UnstructuredBuilder ui 하위 이동은 Phase 1B 또는 Phase 2로 둔다
- Phase 1에서 제외:
  - OcrAnnotator 이동
  - OcrCanvasPane 이동
  - OcrRightPanel rename
  - components/ocr/core 이동
  - TestWorkspace 관련 이동
  - common/ui 또는 common/utils 이동
- 위험도: LOW_TO_MEDIUM
- 이유: 첫 이동은 import 영향이 작아야 한다. canvas/annotation/core는 RunOCR와 legacy route까지 얽혀 있어 별도 phase가 안전하다.

## 11. Template table column definition 대비 파일 위치
| proposedPath | purpose |
| --- | --- |
| `src/components/template/ui/TemplateTableColumnEditor.tsx` | 테이블 컬럼 정의/순서/label 편집 UI |
| `src/components/template/utils/recommendTemplateColumns.ts` | OCR/header 기반 자동 컬럼 추천 |
| `src/components/template/utils/mapHeaderToCanonicalKey.ts` | 표 헤더를 canonical key로 매핑 |
| `src/components/template/utils/templateColumnStore.ts` | template column definition 저장/로드 후보 |
| `src/common/utils/invoiceTableDisplay.ts` | 현재 display policy와 연결. common 이동은 feature 안정화 후 검토. |

## 12. common 후보
| current | target | reason | timing |
| --- | --- | --- | --- |
| `src/components/ocr/OcrCanvasPane.tsx` | `src/common/ui/OcrCanvasPane.tsx` | Template editor와 RunOCR Custom tab이 공유한다. | feature 폴더 안정화 후 |
| `src/components/ocr/core/types.ts` | `src/common/types/ocrCanvas.ts` | Region/FieldType type은 Template과 RunOCR canvas 양쪽에 걸친다. | OcrCanvasPane ownership 확정 후 |
| `src/components/common/FileDropzone.tsx` | `src/common/ui/FileDropzone.tsx` | RunOCR에서 쓰는 shared UI이며 Template에서도 재사용 가능하다. | common 폴더 전환 phase |
| `src/components/common/RequireLogin.tsx` | `src/common/ui/RequireLogin.tsx` | feature 전용이 아닌 route guard. | common 폴더 전환 phase |

## 13. dirty 상태
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
?? docs/FRONTEND_RUNOCR_CYCLE1_CLOSEOUT_20260522.json
?? docs/FRONTEND_RUNOCR_CYCLE1_CLOSEOUT_20260522.md
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

## 14. typecheck/build 결과
- `npm run typecheck`: PASS (exit 0)
- `npm run build`: PASS (exit 0)
- known stderr noise: ESLint: nextVitals is not iterable

## 15. 다음 작업 제안
1. Template folder move Phase 1: TemplateWorkspace route/workspace 이동만 진행
2. OcrAnnotator/OcrRightPanel/core 이동은 별도 Phase 2 precheck 후 진행
3. OcrCanvasPane common/shared ownership은 RunOCR 영향 분석 후 결정
4. TPL-95328E52 dirty 영향 precheck 유지
5. TestWorkspace는 사용자 확인 전 이동/수정 금지
