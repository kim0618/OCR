# FRONTEND TEMPLATE EDITOR UI OWNERSHIP PRECHECK 20260522

## 1. 사용 도구와 모델
- 도구: Codex
- 모델: Codex
- 작업명: CODEX_FRONTEND_TEMPLATE_EDITOR_UI_OWNERSHIP_PRECHECK_NO_PROD_MODIFY

## 2. 코드 수정 여부
- 운영 코드 수정: 없음
- 파일 이동/import 수정/rename/리팩토링/주석 추가/fixture/templates/backend 수정: 없음
- 현재 dirty 상태는 되돌리지 않았다.

## 3. 생성 파일
- `tmp/codex_frontend_template_editor_ui_ownership_precheck.py`
- `docs/FRONTEND_TEMPLATE_EDITOR_UI_OWNERSHIP_PRECHECK_20260522.md`
- `docs/FRONTEND_TEMPLATE_EDITOR_UI_OWNERSHIP_PRECHECK_20260522.json`
- `docs/FRONTEND_TEMPLATE_EDITOR_UI_OWNERSHIP_MAP_20260522.csv`

## 4. 분석 범위
- `src/components/ocr/OcrAnnotator.tsx`
- `src/components/ocr/OcrRightPanel.tsx`
- `src/components/ocr/OcrCanvasPane.tsx`
- `src/components/ocr/core/*`
- `src/components/template/TemplateWorkspace.tsx`
- `src/components/template/UnstructuredBuilder.tsx`
- `src/app/ocr/page.tsx`
- `src/app/template/page.tsx`
- `src/components/runocr/*`
- `src/components/test/TestWorkspace.tsx` 읽기 전용

## 5. OcrAnnotator ownership 분석
- 판정: `TEMPLATE_PRIVATE_UI`
- target: `src/components/template/ui/OcrAnnotator.tsx`
- import 사용처: `src/app/ocr/page.tsx, src/app/template/page.tsx`
- RunOCR 직접 import: 없음
- TestWorkspace 직접 import: 없음
- 판단: Template editor entry로 이동 가능하지만 `OcrCanvasPane`, `OcrRightPanel`, `ocr/core/export`, `imageStore`, template save/localStorage 흐름을 조립하므로 logic 변경 없이 move/import-only로 제한해야 한다.

## 6. OcrRightPanel ownership 분석
- 판정: `TEMPLATE_PRIVATE_UI`
- target: `src/components/template/ui/OcrRightPanel.tsx`
- import 사용처: `src/components/ocr/OcrAnnotator.tsx`
- RunOCR 직접 import: 없음
- TestWorkspace 직접 import: 없음
- 판단: OcrAnnotator 내부 right-side panel이므로 OcrAnnotator와 같이 이동하는 것이 좋다. `TemplateRightPanel` rename은 별도 micro-step으로 미룬다.

## 7. OcrCanvasPane shared 영향
- 판정: `EXCLUDE_FROM_4B`
- importedBy: `src/components/ocr/OcrAnnotator.tsx, src/components/runocr/RunOcrWorkspace.tsx`
- 이유: OcrAnnotator와 RunOcrWorkspace가 모두 사용한다. Template 전용 위치로 옮기면 RunOCR import까지 흔든다.
- future candidate: `src/common/ui/OcrCanvasPane.tsx`

## 8. ocr/core 의존 분석
- 판정: `EXCLUDE_FROM_4B`
- 이유: core/types는 RunOCR도 의존하고, ops/table/export는 canvas/right panel/export save path에 묶여 있다.
- 후보: src/components/template/utils/*, src/common/utils/*, src/common/types/*
- 4B에서는 `ocr/core/*` 이동 금지.

## 9. route 영향 분석
- `/ocr`: route policy 변경 없음. `OcrAnnotator` dynamic import path만 4B 수정 후보.
- `/template`: route policy 변경 없음. `OcrAnnotator` dynamic import path만 4B 수정 후보.
- `TemplateWorkspace`: 4A 이동 완료 상태이며 4B 수정 대상 아님.

## 10. Phase 4B 후보 비교
| option | risk | recommendation | pros | cons |
| --- | --- | --- | --- | --- |
| 1. OcrAnnotator만 이동 | MEDIUM_HIGH | NOT_PRIMARY | Template editor entry가 template/ui 아래로 간다. | OcrRightPanel이 기존 ocr 폴더에 남아 ownership이 반쪽짜리가 된다.; OcrAnnotator 내부 상대 import가 더 어색해진다. |
| 2. OcrAnnotator + OcrRightPanel 이동, rename 없음 | MEDIUM | DO_4B | Template private UI 두 파일이 함께 이동한다.; rename이 없어 diff가 작다.; OcrCanvasPane/core는 그대로 두어 RunOCR 영향이 제한된다. | OcrRightPanel 이름은 아직 목표명 TemplateRightPanel이 아니다.; OcrAnnotator 내부 core/canvas import 보정이 필요하다. |
| 3. OcrAnnotator + OcrRightPanel 이동 + TemplateRightPanel rename | HIGH | DEFER_MICRO_STEP | 목표 이름에 더 가깝다. | move와 rename을 동시에 해 review가 어려워진다.; 문자열/참조 static check가 더 복잡해진다. |
| 4. OcrAnnotator/OcrRightPanel/OcrCanvasPane 같이 이동 | VERY_HIGH | DO_NOT_DO | components/ocr를 크게 비울 수 있다. | RunOCR Custom tab도 건드리게 된다.; shared/common ownership 결정을 건너뛰게 된다. |
| 5. 이동 보류, ocr/core precheck 먼저 | LOW | ACCEPTABLE_BUT_NOT_PRIMARY | 더 보수적이다. | Template UI ownership 정리 진척이 없다.; OcrAnnotator/OcrRightPanel은 이미 private UI로 판정 가능하다. |

## 11. Phase 4B 추천 범위
- 추천: OcrAnnotator + OcrRightPanel 이동, rename 없음
- 위험도: MEDIUM
- 이유: 두 파일은 Template private UI이고 RunOCR/Test 직접 import가 없다. OcrCanvasPane/core를 그대로 두면 shared 영향이 제한된다.
- 이동:
  - `src/components/ocr/OcrAnnotator.tsx` -> `src/components/template/ui/OcrAnnotator.tsx`
  - `src/components/ocr/OcrRightPanel.tsx` -> `src/components/template/ui/OcrRightPanel.tsx`
- 유지:
  - `src/components/ocr/OcrCanvasPane.tsx`
  - `src/components/ocr/core/*`
  - `src/components/template/UnstructuredBuilder.tsx`
  - `src/components/template/TemplateWorkspace.tsx`
  - `src/components/runocr/*`
  - `src/components/test/TestWorkspace.tsx`

## 12. target path 제안
- `src/components/ocr/OcrAnnotator.tsx` -> `src/components/template/ui/OcrAnnotator.tsx`
- `src/components/ocr/OcrRightPanel.tsx` -> `src/components/template/ui/OcrRightPanel.tsx`
- `src/components/ocr/OcrCanvasPane.tsx` 유지
- `src/components/ocr/core/*` 유지
- `src/components/template/UnstructuredBuilder.tsx` 유지

## 13. static check 설계
- src/components/template/ui/OcrAnnotator.tsx exists
- src/components/template/ui/OcrRightPanel.tsx exists
- src/components/ocr/OcrAnnotator.tsx absent
- src/components/ocr/OcrRightPanel.tsx absent
- src/components/ocr/OcrCanvasPane.tsx remains
- src/components/ocr/core/types.ts/table.ts/ops.ts/export.ts remain
- src/app/ocr/page.tsx route policy unchanged; only dynamic import path adjusted
- src/app/template/page.tsx route policy unchanged; only dynamic import path adjusted
- TestWorkspace.tsx unchanged
- RunOCR files unchanged
- No components/ocr/OcrAnnotator import string remains
- No components/ocr/OcrRightPanel import string remains
- No OcrRightPanel -> TemplateRightPanel rename in 4B
- npm run typecheck PASS
- npm run build PASS

## 14. Template table column definition 대비
- TemplateTableColumnEditor는 src/components/template/ui/TemplateTableColumnEditor.tsx 후보.
- OcrRightPanel에 table section으로 붙일 수 있지만, 첫 구현은 별도 component로 두는 편이 좋다.
- template column recommend/store/mapper는 src/components/template/utils 아래 후보.
- ocr/core/export.ts는 나중에 templateMapper.ts 후보지만 4B에서는 이동하지 않는다.
- invoiceTableDisplay/common utils와의 연결은 Template table column definition 도입 시 별도 precheck가 필요하다.

## 15. 파일별 import/ownership 표
| currentPath | lines | ownership | targetPath | risk | notes |
| --- | ---: | --- | --- | --- | --- |
| `src/components/ocr/OcrAnnotator.tsx` | 442 | TEMPLATE_PRIVATE_UI | `src/components/template/ui/OcrAnnotator.tsx` | MEDIUM_HIGH | Template route와 legacy /ocr route에서 dynamic import되며 OcrCanvasPane/OcrRightPanel/core/export/imageStore/template save 흐름을 조립한다. |
| `src/components/ocr/OcrRightPanel.tsx` | 507 | TEMPLATE_PRIVATE_UI | `src/components/template/ui/OcrRightPanel.tsx` | MEDIUM | OcrAnnotator 내부에서만 사용된다. rename 없이 OcrAnnotator와 함께 이동하는 것이 안전하다. |
| `src/components/ocr/OcrCanvasPane.tsx` | 1527 | RUNOCR_SHARED_CANDIDATE | `KEEP_AT_src/components/ocr/OcrCanvasPane.tsx_FOR_4B` | VERY_HIGH | OcrAnnotator와 RunOcrWorkspace가 모두 사용한다. 4B 이동 범위에서 제외해야 한다. |
| `src/components/ocr/core/types.ts` | 110 | COMMON_TYPES_CANDIDATE | `KEEP_AT_src/components/ocr/core/types.ts_FOR_4B` | VERY_HIGH | OcrCanvasPane, OcrRightPanel, OcrAnnotator, RunOCR formdata/mapping path가 의존한다. |
| `src/components/ocr/core/table.ts` | 151 | TEMPLATE_PRIVATE_OR_COMMON_UTIL_REVIEW | `KEEP_AT_src/components/ocr/core/table.ts_FOR_4B` | HIGH | OcrCanvasPane/OcrRightPanel/export helper가 의존한다. Template table definition과 연결되지만 4B에서는 보류. |
| `src/components/ocr/core/ops.ts` | 99 | COMMON_UTIL_CANDIDATE | `KEEP_AT_src/components/ocr/core/ops.ts_FOR_4B` | HIGH | Canvas drag/region geometry/right panel/export helper에서 공유된다. |
| `src/components/ocr/core/export.ts` | 90 | TEMPLATE_PRIVATE_UTIL | `KEEP_AT_src/components/ocr/core/export.ts_FOR_4B` | MEDIUM_HIGH | OcrAnnotator save path가 직접 사용한다. 4B에서 OcrAnnotator 이동 후 import만 보정하고 파일 이동은 보류. |
| `src/components/template/TemplateWorkspace.tsx` | 180 | TEMPLATE_WORKSPACE | `src/components/template/TemplateWorkspace.tsx` | LOW | 4A에서 이미 이동 완료. 4B에서 수정 대상 아님. |
| `src/components/template/UnstructuredBuilder.tsx` | 311 | TEMPLATE_PRIVATE_UI | `KEEP_AT_src/components/template/UnstructuredBuilder.tsx_FOR_4B` | MEDIUM | template/ui 이동 후보지만 4B 범위에서는 OcrAnnotator/OcrRightPanel에 집중하기 위해 보류. |
| `src/app/ocr/page.tsx` | 48 | ROUTE_IMPORT_IMPACT | `src/app/ocr/page.tsx` | MEDIUM | OcrAnnotator dynamic import와 TemplateWorkspace import를 가진 route. 4B에서 OcrAnnotator import만 보정 대상. |
| `src/app/template/page.tsx` | 281 | ROUTE_IMPORT_IMPACT | `src/app/template/page.tsx` | MEDIUM | OcrAnnotator와 UnstructuredBuilder를 직접 사용한다. 4B에서 OcrAnnotator import 보정 대상. |
| `src/components/runocr/RunOcrWorkspace.tsx` | 1556 | DO_NOT_MOVE_IN_4B | `src/components/runocr/RunOcrWorkspace.tsx` | VERY_HIGH | OcrCanvasPane dynamic import와 core types를 사용한다. 4B에서는 수정하지 않는 것이 목표. |
| `src/components/test/TestWorkspace.tsx` | 6409 | TEST_ONLY_OR_TEST_SHARED | `NO_MOVE_WITHOUT_USER_CONFIRMATION` | VERY_HIGH | 사용자 확인 전 수정/이동 금지. 이번 precheck에서 읽기만 한다. |

## 16. importedBy/imports
| file | importedBy | imports |
| --- | --- | --- |
| `src/components/ocr/OcrAnnotator.tsx` | src/app/ocr/page.tsx, src/app/template/page.tsx | src/components/common/AppProviders.tsx, src/components/ocr/OcrCanvasPane.tsx, src/components/ocr/OcrRightPanel.tsx, src/components/ocr/core/export.ts, src/components/ocr/core/types.ts, src/lib/imageStore.ts |
| `src/components/ocr/OcrRightPanel.tsx` | src/components/ocr/OcrAnnotator.tsx | src/components/ocr/core/ops.ts, src/components/ocr/core/table.ts, src/components/ocr/core/types.ts |
| `src/components/ocr/OcrCanvasPane.tsx` | src/components/ocr/OcrAnnotator.tsx, src/components/runocr/RunOcrWorkspace.tsx | src/components/common/FileDropzone.tsx, src/components/ocr/core/ops.ts, src/components/ocr/core/table.ts, src/components/ocr/core/types.ts |
| `src/components/ocr/core/types.ts` | src/components/ocr/OcrAnnotator.tsx, src/components/ocr/OcrCanvasPane.tsx, src/components/ocr/OcrRightPanel.tsx, src/components/ocr/core/export.ts, src/components/ocr/core/ops.ts, src/components/ocr/core/table.ts, src/components/runocr/RunOcrWorkspace.tsx, src/components/runocr/utils/buildOcrFormData.ts | - |
| `src/components/ocr/core/table.ts` | src/components/ocr/OcrCanvasPane.tsx, src/components/ocr/OcrRightPanel.tsx, src/components/ocr/core/export.ts | src/components/ocr/core/ops.ts, src/components/ocr/core/types.ts |
| `src/components/ocr/core/ops.ts` | src/components/ocr/OcrCanvasPane.tsx, src/components/ocr/OcrRightPanel.tsx, src/components/ocr/core/export.ts, src/components/ocr/core/table.ts | src/components/ocr/core/types.ts |
| `src/components/ocr/core/export.ts` | src/components/ocr/OcrAnnotator.tsx | src/components/ocr/core/ops.ts, src/components/ocr/core/table.ts, src/components/ocr/core/types.ts |
| `src/components/template/TemplateWorkspace.tsx` | src/app/ocr/page.tsx | src/components/common/AppProviders.tsx |
| `src/components/template/UnstructuredBuilder.tsx` | src/app/template/page.tsx | src/components/common/AppProviders.tsx |
| `src/app/ocr/page.tsx` | - | src/components/layout/AppShell.tsx, src/components/ocr/OcrAnnotator.tsx, src/components/template/TemplateWorkspace.tsx |
| `src/app/template/page.tsx` | - | src/components/layout/AppShell.tsx, src/components/ocr/OcrAnnotator.tsx, src/components/template/UnstructuredBuilder.tsx, src/lib/imageStore.ts |
| `src/components/runocr/RunOcrWorkspace.tsx` | src/app/runocr/page.tsx | src/components/common/AppProviders.tsx, src/components/common/FileDropzone.tsx, src/components/ocr/OcrCanvasPane.tsx, src/components/ocr/core/types.ts, src/components/runocr/ui/CornerAdjust.tsx, src/components/runocr/ui/OcrDocViewer.tsx, src/components/runocr/ui/OcrResultPanel.tsx, src/components/runocr/ui/RunOcrResultLayout.tsx, src/components/runocr/utils/mapOcrResponse.ts, src/components/runocr/utils/runOcrRequest.ts, src/lib/autofillEngine.ts, src/lib/bizNumber.ts, src/lib/historyStore.ts, src/lib/imageStore.ts |
| `src/components/test/TestWorkspace.tsx` | src/app/test/page.tsx | src/components/common/AppProviders.tsx, src/components/test/core/autofill.ts, src/components/test/core/extract.ts, src/components/test/core/finalize.ts, src/components/test/core/match.ts, src/components/test/core/types.ts, src/lib/bizNumber.ts, src/lib/invoiceTableDisplay.ts, src/lib/profiles.ts, src/lib/testsets.ts |

## 17. dirty 상태
```text
 M src/app/ocr/page.tsx
 M src/app/runocr/page.tsx
RM src/components/upload/UploadWorkspace.tsx -> src/components/runocr/RunOcrWorkspace.tsx
RM src/components/upload/CornerAdjust.tsx -> src/components/runocr/ui/CornerAdjust.tsx
RM src/components/upload/OcrDocViewer.tsx -> src/components/runocr/ui/OcrDocViewer.tsx
RM src/components/upload/OcrResultPanel.tsx -> src/components/runocr/ui/OcrResultPanel.tsx
R  src/components/ocr/TemplateWorkspace.tsx -> src/components/template/TemplateWorkspace.tsx
 M src/lib/invoiceTableDisplay.ts
 M ../ocr-server/data/review_log.jsonl
 M ../ocr-server/data/templates.json
 M ../ocr-server/requirements.txt
?? ../.claude-memory/
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
?? docs/FRONTEND_STRUCTURE_4A_TEMPLATE_WORKSPACE_MOVE_20260522.json
?? docs/FRONTEND_STRUCTURE_4A_TEMPLATE_WORKSPACE_MOVE_20260522.md
?? docs/FRONTEND_TARGET_STRUCTURE_OWNERSHIP_MAP_20260522.csv
?? docs/FRONTEND_TARGET_STRUCTURE_OWNERSHIP_PRECHECK_20260522.json
?? docs/FRONTEND_TARGET_STRUCTURE_OWNERSHIP_PRECHECK_20260522.md
?? docs/FRONTEND_TEMPLATE_FOLDER_OWNERSHIP_MAP_20260522.csv
?? docs/FRONTEND_TEMPLATE_FOLDER_OWNERSHIP_PRECHECK_20260522.json
?? docs/FRONTEND_TEMPLATE_FOLDER_OWNERSHIP_PRECHECK_20260522.md
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
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_TEMPLATE_WORKSPACE_MOVE_20260522_20260521.json
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_TEMPLATE_WORKSPACE_MOVE_20260522_20260521.md
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

## 18. typecheck/build 결과
- `npm run typecheck`: PASS (exit 0)
- `npm run build`: PASS (exit 0)
- known stderr noise: ESLint: nextVitals is not iterable

## 19. 다음 작업 제안
1. Phase 4B: OcrAnnotator + OcrRightPanel을 rename 없이 components/template/ui로 이동
2. OcrCanvasPane와 ocr/core는 그대로 유지
3. 4B static check를 만들고 typecheck/build 및 /template, /ocr smoke를 실행
4. 4B 이후 OcrRightPanel rename은 별도 micro-step으로 검토
5. OcrCanvasPane/common 이동은 RunOCR 공유 영향 precheck 후 진행
