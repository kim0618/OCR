# FRONTEND OCR Core Table Common Move Precheck - 2026-05-22

## 1. 사용 도구와 모델
- 사용 도구: Codex
- 사용 모델: Codex
- 작업명: CODEX_FRONTEND_OCR_CORE_TABLE_COMMON_MOVE_PRECHECK_NO_PROD_MODIFY

## 2. 코드 수정 여부
- 운영 코드 수정: 없음
- 파일 이동/import 수정/rename/refactor: 없음
- 생성 허용 파일만 작성했다.

## 3. 생성 파일
- `tmp/codex_frontend_ocr_core_table_common_move_precheck.py`
- `docs/FRONTEND_OCR_CORE_TABLE_COMMON_MOVE_PRECHECK_20260522.md`
- `docs/FRONTEND_OCR_CORE_TABLE_COMMON_MOVE_PRECHECK_20260522.json`
- `docs/FRONTEND_OCR_CORE_TABLE_COMMON_MOVE_PRECHECK_MAP_20260522.csv`

## 4. 분석 범위
- `src/components/ocr/core/table.ts`
- `src/components/ocr/core/export.ts`
- `src/components/ocr/OcrCanvasPane.tsx`
- `src/components/template/ui/OcrRightPanel.tsx`
- `src/components/template/ui/OcrAnnotator.tsx`
- `src/common/types/ocr.ts`
- `src/common/utils/ocrCanvasOps.ts`
- `src/components/runocr/RunOcrWorkspace.tsx`
- `src/components/test/TestWorkspace.tsx` 읽기 전용 범위

## 5. table.ts 역할 요약
- currentPath: `src/components/ocr/core/table.ts`
- lineCount: 151
- 역할: OCR table-region helper. column guide 정규화, rowTemplate 기반 repeat row 생성, stop keyword 정규화, OCR box row band 자동 감지, stop row 판정을 담당한다.
- sideEffects: 모듈 로드 시 side effect 없음.
- React/browser 의존: 없음.
- common/types 의존: `Rect` type.
- common/utils 의존: `clampRectToArea`.
- components 의존: 없음.

Imports:
- `import type { Rect } from "../../../common/types/ocr";`
- `import { clampRectToArea } from "../../../common/utils/ocrCanvasOps";`

Exports:
- `export type OcrBox =`
- `export function normalizeColGuides(guides?: number[]): number[]`
- `export function buildTableRows(area: Rect, rowTemplate: Rect): Rect[]`
- `export function normalizeStopKeywords(list?: string[]): string[]`
- `export function autoDetectRowBands(params:`
- `export function isStopRow(params: { rowText: string; stopKeywords: string[] })`

## 6. importedBy 분석
| file | importPath | symbols | feature | usagePurpose |
|---|---|---|---|---|
| `src/components/ocr/OcrCanvasPane.tsx` | `./core/table` | buildTableRows, normalizeColGuides | shared | interactive table region editing: add/normalize column guides and build repeat rows from rowTemplate |
| `src/components/template/ui/OcrRightPanel.tsx` | `../../ocr/core/table` | normalizeColGuides | template | right panel table metadata display, guide count, guide removal, and guide list rendering |
| `src/components/ocr/core/export.ts` | `./table` | normalizeColGuides | template | template export payload normalizes colGuides and derives colX |

RunOCR는 `table.ts`를 직접 import하지 않지만 `RunOcrWorkspace`가 사용하는 `OcrCanvasPane` 경로를 통해 간접 영향을 받는다.

## 7. common/utils 적합성
- 판정: `COMMON_UTIL_READY_WITH_RENAME`
- 이유: 현재 `table.ts`는 Template 저장 payload 자체가 아니라 OCR table region primitive helper다.
- common 이동 시 components 의존은 생기지 않는다. 필요한 의존은 `src/common/types/ocr`와 `src/common/utils/ocrCanvasOps`로 이미 common 쪽에 있다.
- `export.ts`와 결합은 `normalizeColGuides` 단일 helper 재사용 수준이므로 export.ts와 동시 이동할 필요는 낮다.

## 8. Template table column definition 영향
- 현재 파일은 `rowTemplate`, `colGuides`, `rows`, `stopKeywords` 같은 primitive를 다룬다.
- 향후 `TemplateTableColumnEditor`의 자동 추천 + 사용자 확인 흐름에서 재사용 가능성이 높다.
- 다만 column canonical mapping, 사용자 확인 상태, 저장 payload 변환 같은 Template policy는 common에 넣지 말고 `components/template/utils`에 둬야 한다.
- 따라서 지금은 common primitive로 이동 가능하되, 이후 Template table column definition은 이 common helper 위에 Template 전용 policy layer를 얹는 방식이 적합하다.

## 9. target 파일명 비교
| target | roleAccuracy | recommended | pros | cons |
|---|---:|---:|---|---|
| `src/common/utils/ocrTableRegion.ts` | HIGH | YES | Covers rowTemplate, row rectangles, table area clamping, OCR row bands, stop-row helpers, and guide normalization; Broad enough for future OcrCanvasPane common/ui dependency; Keeps primitive table-region helpers separate from Template save payload policy | Less explicit about column guides than ocrTableGuides.ts |
| `src/common/utils/ocrTableGuides.ts` | MEDIUM | NO | Very clear for normalizeColGuides and future column guide editor helpers | Too narrow for buildTableRows, autoDetectRowBands, normalizeStopKeywords, and isStopRow |
| `src/common/utils/ocrCanvasTable.ts` | MEDIUM_HIGH | NO | Aligns with OcrCanvasPane interactive table editing | Sounds UI/canvas-specific even though helpers are pure table region utilities |
| `src/components/template/utils/templateTableRegion.ts` | MEDIUM | NO | Keeps future Template table column policy close to Template feature | Unnatural for OcrCanvasPane/RunOCR shared canvas path and would make Template own shared helpers |
| `defer` | LOW | NO | Avoids churn before Template table column definition design | Leaves OcrCanvasPane common/ui blocked by feature-local table helper dependency |

추천 target은 `src/common/utils/ocrTableRegion.ts`다. `ocrTableGuides.ts`는 column guide만 표현해서 현재 row band/stop row/helper 범위를 담기에는 좁다.

## 10. dependency graph
- `table.ts` -> `src/common/types/ocr`, `src/common/utils/ocrCanvasOps`
- `export.ts` -> `src/common/types/ocr`, `src/common/utils/ocrCanvasOps`, `./table`
- `OcrCanvasPane.tsx` -> `src/common/utils/ocrCanvasOps`, `./core/table`
- `OcrRightPanel.tsx` -> `src/common/utils/ocrCanvasOps`, `../../ocr/core/table`
- `OcrAnnotator.tsx` -> `./export` 경유, table.ts 직접 import 없음

`table.ts`는 `export.ts`를 역참조하지 않으므로 table만 먼저 이동 가능하다.

## 11. 실제 이동/보류 추천
- 추천: A. `table.ts`만 `src/common/utils/ocrTableRegion.ts`로 이동
- import 수정 범위: `OcrCanvasPane.tsx`, `OcrRightPanel.tsx`, `export.ts`
- 이번 phase에서 하지 않을 것: `export.ts` 이동, `OcrCanvasPane` 이동, `TestWorkspace` 수정
- 위험도: MEDIUM

## 12. static check 설계
- target common utils file exists at src/common/utils/ocrTableRegion.ts
- src/components/ocr/core/table.ts is absent after actual move
- common utils file does not import src/components/*
- common utils file does not use React/browser/window/document/localStorage APIs
- common utils file imports OCR shape types from src/common/types/ocr
- common utils file imports clampRectToArea from src/common/utils/ocrCanvasOps
- src contains no src/components/ocr/core/table import string after move
- OcrCanvasPane remains at src/components/ocr/OcrCanvasPane.tsx for this phase
- export.ts remains at src/components/ocr/core/export.ts for this phase
- TestWorkspace is not modified
- npm run typecheck PASS
- npm run build PASS
- 5A and 5B static checks PASS
- validation 1A checks PASS or PASS_WITH_SKIPPED_BACKUP

## 13. dirty 상태
```text
  M mysuit-ocr/docs/FRONTEND_CLEANUP_1B_JS_CLEAN_JSON_FIXTURE_RUNNER_20260521.json
  M mysuit-ocr/docs/FRONTEND_CLEANUP_1B_JS_CLEAN_JSON_FIXTURE_RUNNER_20260521.md
  M mysuit-ocr/docs/FRONTEND_CLEANUP_3D2_RUNNER_RESULT_20260521.json
 R  mysuit-ocr/src/components/ocr/core/types.ts -> mysuit-ocr/src/common/types/ocr.ts
 RM mysuit-ocr/src/components/ocr/core/ops.ts -> mysuit-ocr/src/common/utils/ocrCanvasOps.ts
  M mysuit-ocr/src/components/ocr/OcrCanvasPane.tsx
  M mysuit-ocr/src/components/ocr/core/export.ts
  M mysuit-ocr/src/components/ocr/core/table.ts
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
 ?? mysuit-ocr/docs/FRONTEND_STRUCTURE_5A_OCR_CORE_TYPES_COMMON_MOVE_20260522.json
 ?? mysuit-ocr/docs/FRONTEND_STRUCTURE_5A_OCR_CORE_TYPES_COMMON_MOVE_20260522.md
 ?? mysuit-ocr/docs/FRONTEND_STRUCTURE_5B_OCR_CORE_OPS_COMMON_MOVE_20260522.json
 ?? mysuit-ocr/docs/FRONTEND_STRUCTURE_5B_OCR_CORE_OPS_COMMON_MOVE_20260522.md
 ?? mysuit-ocr/docs/FRONTEND_VALIDATION_1A_BASELINE_REPAIR_20260522.json
 ?? mysuit-ocr/docs/FRONTEND_VALIDATION_1A_BASELINE_REPAIR_20260522.md
 ?? mysuit-ocr/docs/FRONTEND_VALIDATION_BASELINE_REPAIR_PRECHECK_20260522.json
 ?? mysuit-ocr/docs/FRONTEND_VALIDATION_BASELINE_REPAIR_PRECHECK_20260522.md
 ?? mysuit-ocr/docs/FRONTEND_VALIDATION_BASELINE_REPAIR_PRECHECK_MAP_20260522.csv
 ?? mysuit-ocr/docs/MARKDOWN_V1_FIXTURE_CHECK_post_OCR_CORE_OPS_COMMON_MOVE_20260522_20260521.json
 ?? mysuit-ocr/docs/MARKDOWN_V1_FIXTURE_CHECK_post_OCR_CORE_OPS_COMMON_MOVE_20260522_20260521.md
 ?? mysuit-ocr/docs/MARKDOWN_V1_FIXTURE_CHECK_post_OCR_CORE_TYPES_COMMON_MOVE_20260522_20260521.json
 ?? mysuit-ocr/docs/MARKDOWN_V1_FIXTURE_CHECK_post_OCR_CORE_TYPES_COMMON_MOVE_20260522_20260521.md
 ?? mysuit-ocr/docs/MARKDOWN_V1_FIXTURE_CHECK_post_VALIDATION_BASELINE_REPAIR_20260522_20260521.json
 ?? mysuit-ocr/docs/MARKDOWN_V1_FIXTURE_CHECK_post_VALIDATION_BASELINE_REPAIR_20260522_20260521.md
 ?? mysuit-ocr/tmp/check_ocr_core_ops_common_move_5b.mjs
 ?? mysuit-ocr/tmp/check_ocr_core_types_common_move_5a.mjs
 ?? mysuit-ocr/tmp/check_validation_baseline_repair_1a.mjs
 ?? mysuit-ocr/tmp/codex_frontend_ocr_canvas_pane_shared_precheck.py
 ?? mysuit-ocr/tmp/codex_frontend_ocr_core_ops_common_move_precheck.py
 ?? mysuit-ocr/tmp/codex_frontend_ocr_core_ownership_precheck.py
 ?? mysuit-ocr/tmp/codex_frontend_ocr_core_table_common_move_precheck.py
 ?? mysuit-ocr/tmp/codex_frontend_validation_baseline_repair_precheck.py
```

## 14. typecheck/build 결과
- `npm run typecheck`: PASS (exit 0)
- `npm run build`: PASS (exit 0)
- stdout log: `ocr-server/logs/codex_CODEX_FRONTEND_OCR_CORE_TABLE_COMMON_MOVE_PRECHECK_NO_PROD_MODIFY.out.log`
- stderr log: `ocr-server/logs/codex_CODEX_FRONTEND_OCR_CORE_TABLE_COMMON_MOVE_PRECHECK_NO_PROD_MODIFY.err.log`
- known stderr noise: ESLint `nextVitals is not iterable`은 exit code 0이면 non-blocking으로 기록.

## 15. 다음 작업 제안
- `node tmp/check_ocr_core_table_common_move_5c.mjs`
- `npm run typecheck`
- `npm run build`
- `node tmp/check_ocr_core_types_common_move_5a.mjs`
- `node tmp/check_ocr_core_ops_common_move_5b.mjs`
- `node tmp/check_validation_baseline_repair_1a.mjs`
- `node tmp/check_table_view_model_v1_fixtures_js.mjs`
- `node tmp/check_clean_json_v1_fixtures_js.mjs`
- `python tmp/codex_markdown_contract_fixture_lock.py --check --phase post_OCR_CORE_TABLE_COMMON_MOVE_20260522`

다음 실제 구조 작업은 `FRONTEND-STRUCTURE-5C-OCR-CORE-TABLE-COMMON-MOVE`로 잡고, 그 뒤에 `export.ts` template/utils 이동과 Template table column definition 설계를 분리하는 것이 안전하다.
