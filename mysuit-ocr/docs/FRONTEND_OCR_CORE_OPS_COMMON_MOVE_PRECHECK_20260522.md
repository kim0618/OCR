# FRONTEND OCR Core Ops Common Move Precheck - 2026-05-22

## 1. 사용 도구와 모델
- 사용 도구: Codex
- 사용 모델: Codex
- 작업명: CODEX_FRONTEND_OCR_CORE_OPS_COMMON_MOVE_PRECHECK_NO_PROD_MODIFY

## 2. 코드 수정 여부
- 운영 코드 수정: 없음
- 파일 이동/import 수정/rename/refactor: 없음
- 생성 파일만 작성했다.

## 3. 생성 파일
- `tmp/codex_frontend_ocr_core_ops_common_move_precheck.py`
- `docs/FRONTEND_OCR_CORE_OPS_COMMON_MOVE_PRECHECK_20260522.md`
- `docs/FRONTEND_OCR_CORE_OPS_COMMON_MOVE_PRECHECK_20260522.json`
- `docs/FRONTEND_OCR_CORE_OPS_COMMON_MOVE_PRECHECK_MAP_20260522.csv`

## 4. 분석 범위
- `src/components/ocr/core/ops.ts`
- `src/components/ocr/core/table.ts`
- `src/components/ocr/core/export.ts`
- `src/components/ocr/OcrCanvasPane.tsx`
- `src/components/template/ui/OcrAnnotator.tsx`
- `src/components/template/ui/OcrRightPanel.tsx`
- `src/common/types/ocr.ts`
- `src/components/runocr/RunOcrWorkspace.tsx`
- `src/components/test/TestWorkspace.tsx` 읽기 전용 범위

## 5. ops.ts 역할 요약
- currentPath: `src/components/ocr/core/ops.ts`
- lineCount: 99
- 역할: OCR canvas/region operation helper. clamp, rect normalization, uid/id parsing, split ratio normalization, label style sizing, sub-region calculation, area clamp를 담당한다.
- sideEffects: 모듈 로드 시 side effect 없음. `uid`는 호출 시에만 `Math.random`/`Date.now`를 사용한다.
- React/browser 의존: React는 `CSSProperties` type-only import뿐이며 runtime React/window/document/localStorage 의존은 없다.
- components 의존: 없음.
- common types 의존: `src/common/types/ocr`의 `Rect`, `Region` type-only import.

Imports:
- `import type { CSSProperties } from "react";`
- `import type { Rect, Region } from "../../../common/types/ocr";`

Exports:
- `export function clamp(n: number, min: number, max: number)`
- `export function normalizeRect(x: number, y: number, w: number, h: number)`
- `export function uid(prefix = "r")`
- `export function parseIndex(name: string, prefix: string)`
- `export function normalizeRatios(parts: 2 | 3, ratios?: number[])`
- `export function boxLabelStyle(wPx: number, hPx: number): CSSProperties`
- `export function calcMultiSubRegions(r: Region)`
- `export function clampRectToArea(rect: Rect, area: Rect): Rect`

## 6. importedBy 분석
| file | importPath | symbols | feature | usagePurpose |
|---|---|---|---|---|
| `src/components/ocr/OcrCanvasPane.tsx` | `./core/ops` | boxLabelStyle, clamp, clampRectToArea, normalizeRatios, normalizeRect, parseIndex, uid | shared | interactive OCR canvas drawing, drag, resize, clamp, duplicate, label positioning, split ratio handling |
| `src/components/template/ui/OcrRightPanel.tsx` | `../../ocr/core/ops` | normalizeRatios, calcMultiSubRegions | template | right panel split/sub-region preview for selected OCR region |
| `src/components/ocr/core/table.ts` | `./ops` | clampRectToArea | shared-internal | table row template and row band rectangles are clamped to table area |
| `src/components/ocr/core/export.ts` | `./ops` | calcMultiSubRegions, normalizeRatios | template | template export payload normalizes split region ratios and materializes subRegions |

RunOCR는 `ops.ts`를 직접 import하지 않지만 `RunOcrWorkspace`가 사용하는 `OcrCanvasPane` 경로를 통해 간접 영향을 받는다.

## 7. common/utils 적합성
- 판정: `COMMON_UTIL_READY_WITH_RENAME`
- 이유: Template panel, OcrCanvasPane, table/export helper가 같이 쓰는 OCR canvas/region pure helper이며 common에서 components를 참조할 필요가 없다.
- 주의: `boxLabelStyle` 때문에 React `CSSProperties` type-only import가 남는다. 이는 runtime React dependency가 아니므로 허용 가능하지만, 5B static check에서 type-only 여부를 확인하는 것이 좋다.

## 8. target 파일명 비교
| target | roleAccuracy | recommended | pros | cons |
|---|---:|---:|---|---|
| `src/common/utils/ocrCanvasOps.ts` | HIGH | YES | Matches current canvas editing operations; Broad enough for geometry, ratio, id parsing, and label style helpers; Fits future OcrCanvasPane common/ui move | Name is broader than pure geometry helpers |
| `src/common/utils/ocrGeometry.ts` | MEDIUM | NO | Clear for clamp and rectangle normalization helpers | Too narrow for uid, parseIndex, normalizeRatios, and boxLabelStyle |
| `src/common/utils/ocrRegionOps.ts` | MEDIUM_HIGH | NO | Captures region-oriented helpers and split sub-region logic | Less direct for OcrCanvasPane ownership and table clamp reuse |
| `src/common/utils/ocrCanvasGeometry.ts` | MEDIUM | NO | Good if helpers are split down to geometry-only functions later | Current file contains non-geometry operations |
| `defer` | LOW | NO | Avoids import churn until table/export decisions are done | Keeps OcrCanvasPane blocked by feature-local ops dependency |

추천 target은 `src/common/utils/ocrCanvasOps.ts`다. `ocrGeometry.ts`는 현재 파일의 id/ratio/label style 책임까지 담기에는 좁다.

## 9. dependency graph
- `ops.ts` -> `src/common/types/ocr`, React `CSSProperties` type-only
- `table.ts` -> `src/common/types/ocr`, `./ops`
- `export.ts` -> `src/common/types/ocr`, `./ops`, `./table`
- `OcrCanvasPane.tsx` -> `./core/ops`, `./core/table`, `src/common/types/ocr`
- `OcrRightPanel.tsx` -> `../../ocr/core/ops`, `../../ocr/core/table`, `src/common/types/ocr`

`table.ts`와 `export.ts`가 `ops.ts`를 의존하지만, `ops.ts`는 table/export를 역참조하지 않는다. 따라서 ops만 먼저 common으로 이동 가능하다.

## 10. 5B 실제 이동 추천
- 추천: A. `ops.ts`만 `src/common/utils/ocrCanvasOps.ts`로 이동
- import 수정 범위: `OcrCanvasPane.tsx`, `OcrRightPanel.tsx`, `table.ts`, `export.ts`
- 5B에서 하지 않을 것: `table.ts` 이동, `export.ts` 이동, `OcrCanvasPane` 이동, `TestWorkspace` 수정
- 위험도: LOW_MEDIUM

## 11. static check 설계
- target common utils file exists at src/common/utils/ocrCanvasOps.ts
- src/components/ocr/core/ops.ts is absent after actual move
- common utils file does not import src/components/*
- common utils file does not use runtime React/browser/window/document/localStorage APIs
- common utils file imports OCR shape types from src/common/types/ocr
- src contains no src/components/ocr/core/ops import string after move
- OcrCanvasPane remains at src/components/ocr/OcrCanvasPane.tsx for 5B
- table.ts/export.ts remain at src/components/ocr/core for 5B
- TestWorkspace is not modified
- npm run typecheck PASS
- npm run build PASS
- tmp/check_ocr_core_types_common_move_5a.mjs PASS
- validation 1A checks PASS or PASS_WITH_SKIPPED_BACKUP

## 12. dirty 상태
```text
  M mysuit-ocr/docs/FRONTEND_CLEANUP_1B_JS_CLEAN_JSON_FIXTURE_RUNNER_20260521.json
  M mysuit-ocr/docs/FRONTEND_CLEANUP_1B_JS_CLEAN_JSON_FIXTURE_RUNNER_20260521.md
  M mysuit-ocr/docs/FRONTEND_CLEANUP_3D2_RUNNER_RESULT_20260521.json
 R  mysuit-ocr/src/components/ocr/core/types.ts -> mysuit-ocr/src/common/types/ocr.ts
  M mysuit-ocr/src/components/ocr/OcrCanvasPane.tsx
  M mysuit-ocr/src/components/ocr/core/export.ts
  M mysuit-ocr/src/components/ocr/core/ops.ts
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
 ?? mysuit-ocr/docs/FRONTEND_OCR_CORE_OWNERSHIP_MAP_20260522.csv
 ?? mysuit-ocr/docs/FRONTEND_OCR_CORE_OWNERSHIP_PRECHECK_20260522.json
 ?? mysuit-ocr/docs/FRONTEND_OCR_CORE_OWNERSHIP_PRECHECK_20260522.md
 ?? mysuit-ocr/docs/FRONTEND_STRUCTURE_5A_OCR_CORE_TYPES_COMMON_MOVE_20260522.json
 ?? mysuit-ocr/docs/FRONTEND_STRUCTURE_5A_OCR_CORE_TYPES_COMMON_MOVE_20260522.md
 ?? mysuit-ocr/docs/FRONTEND_VALIDATION_1A_BASELINE_REPAIR_20260522.json
 ?? mysuit-ocr/docs/FRONTEND_VALIDATION_1A_BASELINE_REPAIR_20260522.md
 ?? mysuit-ocr/docs/FRONTEND_VALIDATION_BASELINE_REPAIR_PRECHECK_20260522.json
 ?? mysuit-ocr/docs/FRONTEND_VALIDATION_BASELINE_REPAIR_PRECHECK_20260522.md
 ?? mysuit-ocr/docs/FRONTEND_VALIDATION_BASELINE_REPAIR_PRECHECK_MAP_20260522.csv
 ?? mysuit-ocr/docs/MARKDOWN_V1_FIXTURE_CHECK_post_OCR_CORE_TYPES_COMMON_MOVE_20260522_20260521.json
 ?? mysuit-ocr/docs/MARKDOWN_V1_FIXTURE_CHECK_post_OCR_CORE_TYPES_COMMON_MOVE_20260522_20260521.md
 ?? mysuit-ocr/docs/MARKDOWN_V1_FIXTURE_CHECK_post_VALIDATION_BASELINE_REPAIR_20260522_20260521.json
 ?? mysuit-ocr/docs/MARKDOWN_V1_FIXTURE_CHECK_post_VALIDATION_BASELINE_REPAIR_20260522_20260521.md
 ?? mysuit-ocr/tmp/check_ocr_core_types_common_move_5a.mjs
 ?? mysuit-ocr/tmp/check_validation_baseline_repair_1a.mjs
 ?? mysuit-ocr/tmp/codex_frontend_ocr_canvas_pane_shared_precheck.py
 ?? mysuit-ocr/tmp/codex_frontend_ocr_core_ops_common_move_precheck.py
 ?? mysuit-ocr/tmp/codex_frontend_ocr_core_ownership_precheck.py
 ?? mysuit-ocr/tmp/codex_frontend_validation_baseline_repair_precheck.py
```

## 13. typecheck/build 결과
- `npm run typecheck`: PASS (exit 0)
- `npm run build`: PASS (exit 0)
- stdout log: `C:\OCR\OCR\ocr-server\logs\codex_CODEX_FRONTEND_OCR_CORE_OPS_COMMON_MOVE_PRECHECK_NO_PROD_MODIFY.out.log`
- stderr log: `C:\OCR\OCR\ocr-server\logs\codex_CODEX_FRONTEND_OCR_CORE_OPS_COMMON_MOVE_PRECHECK_NO_PROD_MODIFY.err.log`
- known stderr noise: ESLint `nextVitals is not iterable`은 exit code 0이면 non-blocking으로 기록.

## 14. 다음 작업 제안
- `node tmp/check_ocr_core_ops_common_move_5b.mjs`
- `npm run typecheck`
- `npm run build`
- `node tmp/check_ocr_core_types_common_move_5a.mjs`
- `node tmp/check_validation_baseline_repair_1a.mjs`
- `node tmp/check_runocr_formdata_keys_2a.mjs`
- `node tmp/check_runocr_response_mapping_boundary_2c.mjs`
- `node tmp/check_runocr_doc_comments_3b.mjs`
- `node tmp/check_template_workspace_move_4a.mjs`
- `node tmp/check_template_editor_ui_move_4b.mjs`

다음 실제 구조 작업은 `FRONTEND-STRUCTURE-5B-OCR-CORE-OPS-COMMON-MOVE`로 잡고, 그 뒤에 `table.ts` common/utils 이동 precheck와 `export.ts` template/utils 이동 precheck를 분리하는 것이 안전하다.
