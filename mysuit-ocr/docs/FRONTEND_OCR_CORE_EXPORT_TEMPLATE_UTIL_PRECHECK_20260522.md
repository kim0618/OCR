# FRONTEND OCR Core Export Template Util Precheck - 2026-05-22

## 1. 사용 도구와 모델
- 사용 도구: Codex
- 사용 모델: Codex
- 작업명: CODEX_FRONTEND_OCR_CORE_EXPORT_TEMPLATE_UTIL_PRECHECK_NO_PROD_MODIFY

## 2. 코드 수정 여부
- 운영 코드 수정: 없음
- 파일 이동/import 수정/rename/refactor: 없음
- 생성 허용 파일만 작성했다.

## 3. 생성 파일
- `tmp/codex_frontend_ocr_core_export_template_util_precheck.py`
- `docs/FRONTEND_OCR_CORE_EXPORT_TEMPLATE_UTIL_PRECHECK_20260522.md`
- `docs/FRONTEND_OCR_CORE_EXPORT_TEMPLATE_UTIL_PRECHECK_20260522.json`
- `docs/FRONTEND_OCR_CORE_EXPORT_TEMPLATE_UTIL_PRECHECK_MAP_20260522.csv`

## 4. 분석 범위
- `src/components/ocr/core/export.ts`
- `src/components/template/ui/OcrAnnotator.tsx`
- `src/components/template/ui/OcrRightPanel.tsx`
- `src/components/ocr/OcrCanvasPane.tsx`
- `src/common/types/ocr.ts`
- `src/common/utils/ocrCanvasOps.ts`
- `src/common/utils/ocrTableRegion.ts`
- `src/components/runocr/RunOcrWorkspace.tsx`
- `src/components/test/TestWorkspace.tsx` 읽기 전용 범위

## 5. export.ts 역할 요약
- currentPath: `src/components/ocr/core/export.ts`
- lineCount: 90
- 역할: Template save/export payload builder. template metadata, image info, regions, multi subRegions, check mode, table payload를 저장용 구조로 직렬화한다.
- sideEffects: 모듈 로드 시 side effect 없음.
- React/browser 의존: 없음.
- common/types 의존: `LoadedImage`, `Rect`, `Region`.
- common/utils 의존: `calcMultiSubRegions`, `normalizeRatios`, `normalizeColGuides`.
- components 의존: 없음.
- `src/components/template/utils` 현재 존재 여부: False

Imports:
- `import type { LoadedImage, Rect, Region } from "../../../common/types/ocr";`
- `import { calcMultiSubRegions, normalizeRatios } from "../../../common/utils/ocrCanvasOps";`
- `import { normalizeColGuides } from "../../../common/utils/ocrTableRegion";`

Exports:
- `export function buildExportPayload(params:`

## 6. importedBy 분석
| file | importPath | symbols | feature | usagePurpose |
|---|---|---|---|---|
| `src/components/template/ui/OcrAnnotator.tsx` | `../../ocr/core/export` | buildExportPayload | template | Template editor save/export payload is memoized from templateName, loaded image, regions, and documentType before save. |

RunOCR, OcrCanvasPane, OcrRightPanel, TestWorkspace는 `export.ts`를 직접 import하지 않는다.

## 7. Template 전용 여부
- 판정: `TEMPLATE_UTIL_READY_WITH_RENAME`
- common/utils 판정: `COMMON_UTIL_NOT_RECOMMENDED`
- 이유: output은 Template 저장/persistence payload 정책이다. 좌표/캔버스/table primitive가 아니라 save contract를 구성한다.
- 직접 production consumer는 `OcrAnnotator.tsx` 하나뿐이며, 저장 직전 `exportPayload` memo와 save body 구성에 연결된다.

## 8. target 파일명 비교
| target | roleAccuracy | recommended | pros | cons |
|---|---:|---:|---|---|
| `src/components/template/utils/buildTemplateExportPayload.ts` | HIGH | YES | Names the only exported function's responsibility directly; Clearly scoped to Template persistence payload rather than generic mapping; Leaves future TemplateTableColumnEditor policy free to live in separate files | Longer filename |
| `src/components/template/utils/templateMapper.ts` | MEDIUM | NO | Good umbrella name if multiple template import/export mappers are added later | Too broad for the current single export and could attract canonical mapping/column policy too early |
| `src/components/template/utils/templateExport.ts` | MEDIUM_HIGH | NO | Short and template-specific | Less explicit than buildTemplateExportPayload; could be confused with UI/export command code |
| `src/components/template/utils/exportTemplatePayload.ts` | MEDIUM_HIGH | NO | Describes output shape and avoids generic mapper naming | Verb-object order is less aligned with current buildExportPayload function name |
| `defer` | LOW | NO | Avoids one import update until Template table column design | Leaves src/components/ocr/core containing a Template-only file and delays OcrCanvasPane common/ui cleanup |

추천 target은 `src/components/template/utils/buildTemplateExportPayload.ts`다. `templateMapper.ts`는 이후 import/load mapper나 column canonical mapping까지 끌어들일 수 있어 지금 이름으로는 너무 넓다.

## 9. dependency graph
- `export.ts` -> `src/common/types/ocr`, `src/common/utils/ocrCanvasOps`, `src/common/utils/ocrTableRegion`
- `OcrAnnotator.tsx` -> `../../ocr/core/export`
- `OcrCanvasPane.tsx` -> export.ts 직접 import 없음
- `OcrRightPanel.tsx` -> export.ts 직접 import 없음
- `RunOcrWorkspace.tsx` -> export.ts 직접 import 없음
- `TestWorkspace.tsx` -> export.ts 직접 import 없음

export.ts만 먼저 이동 가능하다. 이 이동은 OcrCanvasPane의 직접 의존을 줄이는 작업은 아니지만, `src/components/ocr/core`의 마지막 Template-only 파일을 제거해 OcrCanvasPane common/ui 이동 전 구조를 정리한다.

## 10. 실제 이동/보류 추천
- 추천: A. `export.ts`만 `src/components/template/utils/buildTemplateExportPayload.ts`로 이동
- import 수정 범위: `src/components/template/ui/OcrAnnotator.tsx` 1곳
- 실제 5D에서 필요: `src/components/template/utils` 디렉터리가 없으면 생성
- 이번 phase에서 하지 않을 것: `OcrCanvasPane` 이동, Template table column definition 구현, TestWorkspace 수정
- 위험도: LOW_MEDIUM

## 11. static check 설계
- target template utils file exists at src/components/template/utils/buildTemplateExportPayload.ts
- src/components/ocr/core/export.ts is absent after actual move
- src/components/ocr/core folder is empty or removable after actual move
- template utils file may import src/common/types/ocr and src/common/utils/*
- template utils file does not import RunOCR or TestWorkspace
- OcrAnnotator import points to template utils target
- OcrCanvasPane remains at src/components/ocr/OcrCanvasPane.tsx for this phase
- common/utils files do not import src/components/*
- TestWorkspace is not modified
- npm run typecheck PASS
- npm run build PASS
- 5A, 5B, and 5C static checks PASS
- validation 1A checks PASS or PASS_WITH_SKIPPED_BACKUP

## 12. dirty 상태
```text
  M mysuit-ocr/docs/FRONTEND_CLEANUP_1B_JS_CLEAN_JSON_FIXTURE_RUNNER_20260521.json
  M mysuit-ocr/docs/FRONTEND_CLEANUP_1B_JS_CLEAN_JSON_FIXTURE_RUNNER_20260521.md
  M mysuit-ocr/docs/FRONTEND_CLEANUP_3D2_RUNNER_RESULT_20260521.json
 R  mysuit-ocr/src/components/ocr/core/types.ts -> mysuit-ocr/src/common/types/ocr.ts
 RM mysuit-ocr/src/components/ocr/core/ops.ts -> mysuit-ocr/src/common/utils/ocrCanvasOps.ts
 RM mysuit-ocr/src/components/ocr/core/table.ts -> mysuit-ocr/src/common/utils/ocrTableRegion.ts
  M mysuit-ocr/src/components/ocr/OcrCanvasPane.tsx
  M mysuit-ocr/src/components/ocr/core/export.ts
  M mysuit-ocr/src/components/runocr/RunOcrWorkspace.tsx
  M mysuit-ocr/src/components/runocr/utils/buildOcrFormData.ts
  M mysuit-ocr/src/components/template/ui/OcrAnnotator.tsx
  M mysuit-ocr/src/components/template/ui/OcrRightPanel.tsx
  M mysuit-ocr/tmp/check_runocr_doc_comments_3b.mjs
  M mysuit-ocr/tmp/check_runocr_formdata_keys_2a.mjs
  M mysuit-ocr/tmp/check_runocr_response_mapping_boundary_2c.mjs
  M mysuit-ocr/tmp/check_template_editor_ui_move_4b.mjs
  M mysuit-ocr/tmp/check_template_workspace_move_4a.mjs
  M mysuit-ocr/tmp/codex_markdown_contract_fixture_lock.py
  M ocr-server/data/review_log.jsonl
  M ocr-server/data/templates.json
 ?? mysuit-ocr/docs/FRONTEND_OCR_CANVAS_PANE_SHARED_MAP_20260522.csv
 ?? mysuit-ocr/docs/FRONTEND_OCR_CANVAS_PANE_SHARED_PRECHECK_20260522.json
 ?? mysuit-ocr/docs/FRONTEND_OCR_CANVAS_PANE_SHARED_PRECHECK_20260522.md
 ?? mysuit-ocr/docs/FRONTEND_OCR_CORE_OPS_COMMON_MOVE_PRECHECK_20260522.json
 ?? mysuit-ocr/docs/FRONTEND_OCR_CORE_OPS_COMMON_MOVE_PRECHECK_20260522.md
 ?? mysuit-ocr/docs/FRONTEND_OCR_CORE_OPS_COMMON_MOVE_PRECHECK_MAP_20260522.csv
 ?? mysuit-ocr/docs/FRONTEND_OCR_CORE_OWNERSHIP_MAP_20260522.csv
 ?? mysuit-ocr/docs/FRONTEND_OCR_CORE_OWNERSHIP_PRECHECK_20260522.json
 ?? mysuit-ocr/docs/FRONTEND_OCR_CORE_OWNERSHIP_PRECHECK_20260522.md
 ?? mysuit-ocr/docs/FRONTEND_OCR_CORE_TABLE_COMMON_MOVE_PRECHECK_20260522.json
 ?? mysuit-ocr/docs/FRONTEND_OCR_CORE_TABLE_COMMON_MOVE_PRECHECK_20260522.md
 ?? mysuit-ocr/docs/FRONTEND_OCR_CORE_TABLE_COMMON_MOVE_PRECHECK_MAP_20260522.csv
 ?? mysuit-ocr/docs/FRONTEND_STRUCTURE_5A_OCR_CORE_TYPES_COMMON_MOVE_20260522.json
 ?? mysuit-ocr/docs/FRONTEND_STRUCTURE_5A_OCR_CORE_TYPES_COMMON_MOVE_20260522.md
 ?? mysuit-ocr/docs/FRONTEND_STRUCTURE_5B_OCR_CORE_OPS_COMMON_MOVE_20260522.json
 ?? mysuit-ocr/docs/FRONTEND_STRUCTURE_5B_OCR_CORE_OPS_COMMON_MOVE_20260522.md
 ?? mysuit-ocr/docs/FRONTEND_STRUCTURE_5C_OCR_CORE_TABLE_COMMON_MOVE_20260522.json
 ?? mysuit-ocr/docs/FRONTEND_STRUCTURE_5C_OCR_CORE_TABLE_COMMON_MOVE_20260522.md
 ?? mysuit-ocr/docs/FRONTEND_VALIDATION_1A_BASELINE_REPAIR_20260522.json
 ?? mysuit-ocr/docs/FRONTEND_VALIDATION_1A_BASELINE_REPAIR_20260522.md
 ?? mysuit-ocr/docs/FRONTEND_VALIDATION_BASELINE_REPAIR_PRECHECK_20260522.json
 ?? mysuit-ocr/docs/FRONTEND_VALIDATION_BASELINE_REPAIR_PRECHECK_20260522.md
 ?? mysuit-ocr/docs/FRONTEND_VALIDATION_BASELINE_REPAIR_PRECHECK_MAP_20260522.csv
 ?? mysuit-ocr/docs/MARKDOWN_V1_FIXTURE_CHECK_post_OCR_CORE_OPS_COMMON_MOVE_20260522_20260521.json
 ?? mysuit-ocr/docs/MARKDOWN_V1_FIXTURE_CHECK_post_OCR_CORE_OPS_COMMON_MOVE_20260522_20260521.md
 ?? mysuit-ocr/docs/MARKDOWN_V1_FIXTURE_CHECK_post_OCR_CORE_TABLE_COMMON_MOVE_20260522_20260521.json
 ?? mysuit-ocr/docs/MARKDOWN_V1_FIXTURE_CHECK_post_OCR_CORE_TABLE_COMMON_MOVE_20260522_20260521.md
 ?? mysuit-ocr/docs/MARKDOWN_V1_FIXTURE_CHECK_post_OCR_CORE_TYPES_COMMON_MOVE_20260522_20260521.json
 ?? mysuit-ocr/docs/MARKDOWN_V1_FIXTURE_CHECK_post_OCR_CORE_TYPES_COMMON_MOVE_20260522_20260521.md
 ?? mysuit-ocr/docs/MARKDOWN_V1_FIXTURE_CHECK_post_VALIDATION_BASELINE_REPAIR_20260522_20260521.json
 ?? mysuit-ocr/docs/MARKDOWN_V1_FIXTURE_CHECK_post_VALIDATION_BASELINE_REPAIR_20260522_20260521.md
 ?? mysuit-ocr/tmp/check_ocr_core_ops_common_move_5b.mjs
 ?? mysuit-ocr/tmp/check_ocr_core_table_common_move_5c.mjs
 ?? mysuit-ocr/tmp/check_ocr_core_types_common_move_5a.mjs
 ?? mysuit-ocr/tmp/check_validation_baseline_repair_1a.mjs
 ?? mysuit-ocr/tmp/codex_frontend_ocr_canvas_pane_shared_precheck.py
 ?? mysuit-ocr/tmp/codex_frontend_ocr_core_export_template_util_precheck.py
 ?? mysuit-ocr/tmp/codex_frontend_ocr_core_ops_common_move_precheck.py
 ?? mysuit-ocr/tmp/codex_frontend_ocr_core_ownership_precheck.py
 ?? mysuit-ocr/tmp/codex_frontend_ocr_core_table_common_move_precheck.py
 ?? mysuit-ocr/tmp/codex_frontend_validation_baseline_repair_precheck.py
```

## 13. typecheck/build 결과
- `npm run typecheck`: PASS (exit 0)
- `npm run build`: PASS (exit 0)
- stdout log: `ocr-server/logs/codex_CODEX_FRONTEND_OCR_CORE_EXPORT_TEMPLATE_UTIL_PRECHECK_NO_PROD_MODIFY.out.log`
- stderr log: `ocr-server/logs/codex_CODEX_FRONTEND_OCR_CORE_EXPORT_TEMPLATE_UTIL_PRECHECK_NO_PROD_MODIFY.err.log`
- known stderr noise: ESLint `nextVitals is not iterable`은 exit code 0이면 non-blocking으로 기록.

## 14. 다음 작업 제안
- `node tmp/check_template_export_payload_move_5d.mjs`
- `npm run typecheck`
- `npm run build`
- `node tmp/check_ocr_core_types_common_move_5a.mjs`
- `node tmp/check_ocr_core_ops_common_move_5b.mjs`
- `node tmp/check_ocr_core_table_common_move_5c.mjs`
- `node tmp/check_validation_baseline_repair_1a.mjs`
- `node tmp/check_table_view_model_v1_fixtures_js.mjs`
- `node tmp/check_clean_json_v1_fixtures_js.mjs`
- `python tmp/codex_markdown_contract_fixture_lock.py --check --phase post_TEMPLATE_EXPORT_PAYLOAD_MOVE_20260522`

다음 실제 구조 작업은 `FRONTEND-STRUCTURE-5D-TEMPLATE-EXPORT-PAYLOAD-MOVE`로 잡고, 그 뒤에 OcrCanvasPane common/ui 이동 precheck를 진행하는 것이 자연스럽다.
