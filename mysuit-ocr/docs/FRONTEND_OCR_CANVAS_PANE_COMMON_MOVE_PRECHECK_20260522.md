# FRONTEND OCR Canvas Pane Common Move Precheck - 2026-05-22

## 1. 사용 도구와 모델
- 사용 도구: Codex
- 사용 모델: Codex
- 작업명: CODEX_FRONTEND_OCR_CANVAS_PANE_COMMON_MOVE_PRECHECK_NO_PROD_MODIFY

## 2. 코드 수정 여부
- 운영 코드 수정: 없음
- 파일 이동/import 수정/rename/refactor: 없음
- 생성 허용 파일만 작성했다.

## 3. 생성 파일
- `tmp/codex_frontend_ocr_canvas_pane_common_move_precheck.py`
- `docs/FRONTEND_OCR_CANVAS_PANE_COMMON_MOVE_PRECHECK_20260522.md`
- `docs/FRONTEND_OCR_CANVAS_PANE_COMMON_MOVE_PRECHECK_20260522.json`
- `docs/FRONTEND_OCR_CANVAS_PANE_COMMON_MOVE_PRECHECK_MAP_20260522.csv`

## 4. 분석 범위
- `src/components/ocr/OcrCanvasPane.tsx`
- `src/components/template/ui/OcrAnnotator.tsx`
- `src/components/runocr/RunOcrWorkspace.tsx`
- `src/components/template/ui/OcrRightPanel.tsx`
- `src/common/types/ocr.ts`
- `src/common/utils/ocrCanvasOps.ts`
- `src/common/utils/ocrTableRegion.ts`
- `src/components/template/utils/buildTemplateExportPayload.ts`
- `src/components/test/TestWorkspace.tsx` 읽기 전용 범위

## 5. OcrCanvasPane 역할 요약
- currentPath: `src/components/ocr/OcrCanvasPane.tsx`
- lineCount: 1527
- export: default `OcrCanvasPane(props: Props)`
- props: imgRef, fileInputRef?, onPickFile?, loaded, regions, setRegions, selectedId, setSelectedId, rowTemplateTargetId, setRowTemplateTargetId, colGuideTargetId, setColGuideTargetId, drawMode, setDrawMode, zoomPct, visibleRegionIds?, emptySelectionHint?, drawTargetRegionId?, drawTargetName?, drawTargetFieldType?, onClearSelection?
- 역할: shared interactive OCR canvas UI. 이미지 표시, drop/pick surface, region draw/move/resize/delete/duplicate/undo, multi split, table rowTemplate/colGuide, zoom, visible region filtering을 담당한다.
- Template-only persistence/save policy: 없음
- RunOCR request/result/history/autofill policy: 없음
- browser API: `ResizeObserver`, `window` keydown, pointer events, image rect 계산. UI component로 자연스러운 범위다.

Imports:
- `import React, { useEffect, useMemo, useRef, useState } from "react";`
- `import type { DragKind, FieldType, LoadedImage, Rect, Region, } from "../../common/types/ocr";`
- `import { boxLabelStyle, clamp, clampRectToArea, normalizeRatios, normalizeRect, parseIndex, uid, } from "../../common/utils/ocrCanvasOps";`
- `import { buildTableRows, normalizeColGuides } from "../../common/utils/ocrTableRegion";`
- `import FileDropzone from "../common/FileDropzone";`

Exports:
- `export default function OcrCanvasPane(props: Props)`

## 6. importedBy 분석
| file | importPath | importKind | feature | usagePurpose |
|---|---|---|---|---|
| `src/components/template/ui/OcrAnnotator.tsx` | `../../ocr/OcrCanvasPane` | static | template | Template editor canvas: file pick/drop image display, region drawing/editing, table rowTemplate/colGuide editing, selection state. |
| `src/components/runocr/RunOcrWorkspace.tsx` | `../ocr/OcrCanvasPane` | dynamic next/dynamic ssr:false | runocr | RunOCR custom tab canvas: edit/adopt OCR result regions, show selected OCR field region, preserve RunOCR request/result logic outside canvas. |

TestWorkspace 직접 import는 발견되지 않았다.

## 7. common/ui 적합성
- 판정: `DEFER_DUE_TO_FILEDROPZONE_COMPONENT_DEPENDENCY`
- common-ready 요소: types/ops/table 의존은 모두 `src/common/types`와 `src/common/utils`로 정리되어 있다.
- blocker: `OcrCanvasPane`가 `../common/FileDropzone`을 import한다. 이 상태로 `src/common/ui/OcrCanvasPane.tsx`로 이동하면 common/ui가 `src/components/common/FileDropzone.tsx`를 참조하게 된다.
- 결론: OcrCanvasPane 자체는 shared UI 후보가 맞지만, 단독 이동은 아직 권장하지 않는다. `FileDropzone`을 common-safe path로 먼저 옮기거나 같은 phase에서 함께 정리해야 한다.

## 8. Template 사용 영향
- 파일: `src/components/template/ui/OcrAnnotator.tsx`
- 현재 import: `../../ocr/OcrCanvasPane`
- 전달 props: image/file pick state, regions/selection state, draw mode, zoom, rowTemplate/colGuide target state.
- save/export, localStorage, IndexedDB image persistence, documentType detection, backend save는 OcrAnnotator에 남아 있고 canvas에는 props로만 전달된다.
- 이동 시 예상 수정: import path만 common/ui target으로 변경.

## 9. RunOCR 사용 영향
- 파일: `src/components/runocr/RunOcrWorkspace.tsx`
- 현재 import: dynamic `../ocr/OcrCanvasPane`, `ssr: false`
- 사용 위치: OCR 결과 화면의 custom tab.
- 전달 props: canvas image/regions/selection/draw/zoom state, visibleRegionIds, emptySelectionHint, OCR field 기반 draw target, clear selection callback.
- request/result/history/autofill/revalidate 로직은 RunOcrWorkspace와 result panel에 남아 있고 canvas 내부로 들어오지 않는다.
- 이동 시 예상 수정: dynamic import path만 common/ui target으로 변경.

## 10. TestWorkspace 영향
- 직접 import 없음.
- 사용자 확인 전 TestWorkspace 수정 금지 정책과 충돌하지 않는다.

## 11. target path 비교
| target | roleAccuracy | recommended | condition | pros | cons |
|---|---:|---:|---|---|---|
| `src/common/ui/OcrCanvasPane.tsx` | HIGH | YES | Ready after FileDropzone is available from common/ui or another common-safe path. | Matches ownership: shared UI used by Template and RunOCR; Simple path for a single shared canvas component; Keeps feature folders from owning cross-feature canvas UI | Requires resolving FileDropzone dependency so common/ui does not import src/components/common |
| `src/common/ui/ocr/OcrCanvasPane.tsx` | MEDIUM_HIGH | NO | Consider only if multiple OCR common UI files are moved together. | Creates a namespace if more OCR-specific common UI grows later | Extra nesting for one file; does not by itself solve FileDropzone dependency |
| `src/components/ocr/OcrCanvasPane.tsx` | MEDIUM | NO | Temporary hold if FileDropzone cannot move yet. | No import churn and no FileDropzone dependency problem | Leaves a single-file feature folder owning shared UI |
| `src/components/shared/OcrCanvasPane.tsx` | LOW | NO | Not recommended. | Names shared intent | Does not match current target structure preference; creates another shared root beside common |

최종 target은 `src/common/ui/OcrCanvasPane.tsx`가 가장 자연스럽다. 단, `FileDropzone` dependency를 먼저 common-safe하게 만들어야 한다.

## 12. 실제 이동/보류 추천
- 추천: `A_AFTER_FILEDROPZONE_PRECONDITION`
- 지금 바로 OcrCanvasPane 단독 이동: 보류
- 선행 조건: `FileDropzone`을 `src/common/ui/FileDropzone.tsx` 등 common-safe path로 이동하거나, OcrCanvasPane 이동 phase에 포함한다.
- 선행 조건 충족 후 범위: OcrCanvasPane 이동 + OcrAnnotator import 수정 + RunOcrWorkspace dynamic import 수정.
- 변경하지 않을 범위: OcrRightPanel, RunOCR request/result/history/autofill helper, TestWorkspace.
- 위험도: 현재 MEDIUM_HIGH, FileDropzone 정리 후 MEDIUM.

## 13. static check 설계
- src/common/ui/OcrCanvasPane.tsx exists after actual move
- src/components/ocr/OcrCanvasPane.tsx is absent after actual move
- src/components/ocr folder is empty or removable after actual move
- common/ui/OcrCanvasPane.tsx does not import src/components/*
- FileDropzone dependency is common-safe before or during the actual move
- common/ui/OcrCanvasPane.tsx imports common/types/ocr, common/utils/ocrCanvasOps, common/utils/ocrTableRegion
- OcrAnnotator import points to common/ui target
- RunOcrWorkspace dynamic import points to common/ui target
- OcrRightPanel import impact is none
- TestWorkspace is not modified
- RunOCR request/result/history/autofill files are not modified except RunOcrWorkspace import path if needed
- npm run typecheck PASS
- npm run build PASS
- 5A/5B/5C/5D checks PASS
- validation baseline repair check PASS

## 14. dirty 상태
```text
  M mysuit-ocr/docs/FRONTEND_CLEANUP_1B_JS_CLEAN_JSON_FIXTURE_RUNNER_20260521.json
  M mysuit-ocr/docs/FRONTEND_CLEANUP_1B_JS_CLEAN_JSON_FIXTURE_RUNNER_20260521.md
  M mysuit-ocr/docs/FRONTEND_CLEANUP_3D2_RUNNER_RESULT_20260521.json
 R  mysuit-ocr/src/components/ocr/core/types.ts -> mysuit-ocr/src/common/types/ocr.ts
 RM mysuit-ocr/src/components/ocr/core/ops.ts -> mysuit-ocr/src/common/utils/ocrCanvasOps.ts
 RM mysuit-ocr/src/components/ocr/core/table.ts -> mysuit-ocr/src/common/utils/ocrTableRegion.ts
  M mysuit-ocr/src/components/ocr/OcrCanvasPane.tsx
  M mysuit-ocr/src/components/runocr/RunOcrWorkspace.tsx
  M mysuit-ocr/src/components/runocr/utils/buildOcrFormData.ts
  M mysuit-ocr/src/components/template/ui/OcrAnnotator.tsx
  M mysuit-ocr/src/components/template/ui/OcrRightPanel.tsx
 RM mysuit-ocr/src/components/ocr/core/export.ts -> mysuit-ocr/src/components/template/utils/buildTemplateExportPayload.ts
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
 ?? mysuit-ocr/docs/FRONTEND_OCR_CORE_EXPORT_TEMPLATE_UTIL_PRECHECK_20260522.json
 ?? mysuit-ocr/docs/FRONTEND_OCR_CORE_EXPORT_TEMPLATE_UTIL_PRECHECK_20260522.md
 ?? mysuit-ocr/docs/FRONTEND_OCR_CORE_EXPORT_TEMPLATE_UTIL_PRECHECK_MAP_20260522.csv
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
 ?? mysuit-ocr/docs/FRONTEND_STRUCTURE_5D_TEMPLATE_EXPORT_PAYLOAD_MOVE_20260522.json
 ?? mysuit-ocr/docs/FRONTEND_STRUCTURE_5D_TEMPLATE_EXPORT_PAYLOAD_MOVE_20260522.md
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
 ?? mysuit-ocr/docs/MARKDOWN_V1_FIXTURE_CHECK_post_TEMPLATE_EXPORT_PAYLOAD_MOVE_20260522_20260521.json
 ?? mysuit-ocr/docs/MARKDOWN_V1_FIXTURE_CHECK_post_TEMPLATE_EXPORT_PAYLOAD_MOVE_20260522_20260521.md
 ?? mysuit-ocr/docs/MARKDOWN_V1_FIXTURE_CHECK_post_VALIDATION_BASELINE_REPAIR_20260522_20260521.json
 ?? mysuit-ocr/docs/MARKDOWN_V1_FIXTURE_CHECK_post_VALIDATION_BASELINE_REPAIR_20260522_20260521.md
 ?? mysuit-ocr/tmp/check_ocr_core_ops_common_move_5b.mjs
 ?? mysuit-ocr/tmp/check_ocr_core_table_common_move_5c.mjs
 ?? mysuit-ocr/tmp/check_ocr_core_types_common_move_5a.mjs
 ?? mysuit-ocr/tmp/check_template_export_payload_move_5d.mjs
 ?? mysuit-ocr/tmp/check_validation_baseline_repair_1a.mjs
 ?? mysuit-ocr/tmp/codex_frontend_ocr_canvas_pane_common_move_precheck.py
 ?? mysuit-ocr/tmp/codex_frontend_ocr_canvas_pane_shared_precheck.py
 ?? mysuit-ocr/tmp/codex_frontend_ocr_core_export_template_util_precheck.py
 ?? mysuit-ocr/tmp/codex_frontend_ocr_core_ops_common_move_precheck.py
 ?? mysuit-ocr/tmp/codex_frontend_ocr_core_ownership_precheck.py
 ?? mysuit-ocr/tmp/codex_frontend_ocr_core_table_common_move_precheck.py
 ?? mysuit-ocr/tmp/codex_frontend_validation_baseline_repair_precheck.py
```

## 15. typecheck/build 결과
- `npm run typecheck`: PASS (exit 0)
- `npm run build`: PASS (exit 0)
- stdout log: `ocr-server/logs/codex_CODEX_FRONTEND_OCR_CANVAS_PANE_COMMON_MOVE_PRECHECK_NO_PROD_MODIFY.out.log`
- stderr log: `ocr-server/logs/codex_CODEX_FRONTEND_OCR_CANVAS_PANE_COMMON_MOVE_PRECHECK_NO_PROD_MODIFY.err.log`
- known stderr noise: ESLint `nextVitals is not iterable`은 exit code 0이면 non-blocking으로 기록.

## 16. 다음 작업 제안
- `node tmp/check_ocr_canvas_pane_common_move_5e.mjs`
- `npm run typecheck`
- `npm run build`
- `node tmp/check_ocr_core_types_common_move_5a.mjs`
- `node tmp/check_ocr_core_ops_common_move_5b.mjs`
- `node tmp/check_ocr_core_table_common_move_5c.mjs`
- `node tmp/check_template_export_payload_move_5d.mjs`
- `node tmp/check_validation_baseline_repair_1a.mjs`
- `node tmp/check_runocr_formdata_keys_2a.mjs`
- `node tmp/check_runocr_response_mapping_boundary_2c.mjs`
- `node tmp/check_template_workspace_move_4a.mjs`
- `node tmp/check_template_editor_ui_move_4b.mjs`

다음 실제 작업은 FileDropzone common/ui 선행 precheck 또는 micro-move를 먼저 수행하고, 그 다음 `FRONTEND-STRUCTURE-5E-OCR-CANVAS-PANE-COMMON-MOVE`로 OcrCanvasPane을 이동하는 순서가 안전하다.
