# FRONTEND FileDropzone Common UI Precheck - 2026-05-22

## 1. 사용 도구와 모델
- 사용 도구: Codex
- 사용 모델: Codex
- 작업명: CODEX_FRONTEND_FILEDROPZONE_COMMON_UI_PRECHECK_NO_PROD_MODIFY

## 2. 코드 수정 여부
- 운영 코드 수정: 없음
- 파일 이동/import 수정/rename/refactor: 없음
- 생성 허용 파일만 작성했다.

## 3. 생성 파일
- `tmp/codex_frontend_filedropzone_common_ui_precheck.py`
- `docs/FRONTEND_FILEDROPZONE_COMMON_UI_PRECHECK_20260522.md`
- `docs/FRONTEND_FILEDROPZONE_COMMON_UI_PRECHECK_20260522.json`
- `docs/FRONTEND_FILEDROPZONE_COMMON_UI_PRECHECK_MAP_20260522.csv`

## 4. 분석 범위
- `src/components/common/FileDropzone.tsx`
- `src/components/ocr/OcrCanvasPane.tsx`
- `src/components/template/ui/OcrAnnotator.tsx`
- `src/components/runocr/RunOcrWorkspace.tsx`
- `src/common/ui` 폴더 존재 여부
- `src/components/test/TestWorkspace.tsx` 읽기 전용 범위

## 5. FileDropzone 역할 요약
- currentPath: `src/components/common/FileDropzone.tsx`
- lineCount: 105
- export: default `FileDropzone`
- props: onPickFile, accept?, hasFile?, children?, fileInputRef?, className?, style?
- 역할: drag/drop + hidden file picker UI. 선택된 파일을 `onPickFile`로 위임하고, 파일이 있을 때는 children preview UI를 렌더링한다.
- drag/drop 처리: 있음
- file picker 처리: 있음
- feature-specific policy: 없음
- OCR 전용 business logic: 없음. 단 empty-state 문구와 `uw-*` class는 문서 업로드 UI 색채가 있다.
- browser API: drag event `dataTransfer`, hidden input click/change.
- `src/common/ui` 현재 존재 여부: False

Imports:
- `import React, { useRef, useState } from "react";`

Exports:
- `export default function FileDropzone({`

## 6. importedBy 분석
| file | importPath | feature | usagePurpose |
|---|---|---|---|
| `src/components/ocr/OcrCanvasPane.tsx` | `../common/FileDropzone` | ocr/shared | OCR canvas empty/upload surface; delegates picked or dropped file to parent via onPickFile. |
| `src/components/runocr/RunOcrWorkspace.tsx` | `../common/FileDropzone` | runocr | RunOCR upload panel dropzone with preview children when a file is selected. |

TestWorkspace 직접 import는 발견되지 않았다.

## 7. common/ui 적합성
- 판정: `COMMON_UI_READY_WITH_IMPORT_ONLY`
- 내부 import는 React뿐이며 components/*, feature utils, backend, template/runocr policy 의존이 없다.
- props는 `onPickFile`, `accept`, `hasFile`, `children`, `fileInputRef`, `className`, `style`로 일반적인 dropzone 형태다.
- 현재 RunOCR upload panel과 OcrCanvasPane에서 함께 쓰므로 feature 전용 UI가 아니다.

## 8. OcrCanvasPane blocker 해소 여부
- 현재 blocker: `OcrCanvasPane`이 `src/components/common/FileDropzone.tsx`를 import한다.
- `FileDropzone`을 `src/common/ui/FileDropzone.tsx`로 이동하면 `OcrCanvasPane`은 common-safe path를 참조할 수 있다.
- 이후 `OcrCanvasPane`을 `src/common/ui/OcrCanvasPane.tsx`로 옮길 때는 같은 common/ui 내부 import로 정리 가능하다.
- OcrCanvasPane의 다른 components/* 의존은 현재 발견되지 않았다.

## 9. target path 비교
| target | roleAccuracy | recommended | pros | cons |
|---|---:|---:|---|---|
| `src/common/ui/FileDropzone.tsx` | HIGH | YES | Matches shared UI ownership; Simple path for a single reusable UI primitive; Removes OcrCanvasPane common/ui blocker | Requires creating src/common/ui because it does not exist yet |
| `src/common/ui/file/FileDropzone.tsx` | MEDIUM | NO | Creates a namespace if multiple file input UI pieces appear later | Extra nesting for one file and not needed for the immediate blocker |
| `src/components/common/FileDropzone.tsx` | LOW | NO | No import churn | Keeps OcrCanvasPane common/ui blocked by common -> components dependency risk |
| `bundle with OcrCanvasPane move` | MEDIUM | NO | One phase can finish both blockers | Larger diff and harder to isolate FileDropzone regression from OcrCanvasPane move |

추천 target은 `src/common/ui/FileDropzone.tsx`다. 단일 공통 UI 파일이므로 `src/common/ui/file/` 하위 폴더는 아직 과하다.

## 10. 실제 이동/보류 추천
- 추천: A. FileDropzone만 `src/common/ui/FileDropzone.tsx`로 이동
- 실제 이동 범위: `src/common/ui` 생성, FileDropzone 이동, `OcrCanvasPane`/`RunOcrWorkspace` import 수정
- 이번 micro-step에서 하지 않을 것: OcrCanvasPane 이동, Template/TestWorkspace 수정, RunOCR 로직 수정
- 위험도: LOW_MEDIUM

## 11. static check 설계
- src/common/ui/FileDropzone.tsx exists
- src/components/common/FileDropzone.tsx is absent
- common/ui/FileDropzone.tsx does not import src/components/*
- FileDropzone importedBy uses new common/ui path
- OcrCanvasPane import points to common/ui/FileDropzone
- RunOcrWorkspace import points to common/ui/FileDropzone
- OcrCanvasPane remains at src/components/ocr/OcrCanvasPane.tsx
- TestWorkspace is not modified
- npm run typecheck PASS
- npm run build PASS
- 5A/5B/5C/5D checks PASS
- validation baseline repair check PASS

## 12. dirty 상태
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
 ?? mysuit-ocr/docs/FRONTEND_OCR_CANVAS_PANE_COMMON_MOVE_PRECHECK_20260522.json
 ?? mysuit-ocr/docs/FRONTEND_OCR_CANVAS_PANE_COMMON_MOVE_PRECHECK_20260522.md
 ?? mysuit-ocr/docs/FRONTEND_OCR_CANVAS_PANE_COMMON_MOVE_PRECHECK_MAP_20260522.csv
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
 ?? mysuit-ocr/tmp/codex_frontend_filedropzone_common_ui_precheck.py
 ?? mysuit-ocr/tmp/codex_frontend_ocr_canvas_pane_common_move_precheck.py
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
- stdout log: `ocr-server/logs/codex_CODEX_FRONTEND_FILEDROPZONE_COMMON_UI_PRECHECK_NO_PROD_MODIFY.out.log`
- stderr log: `ocr-server/logs/codex_CODEX_FRONTEND_FILEDROPZONE_COMMON_UI_PRECHECK_NO_PROD_MODIFY.err.log`
- known stderr noise: ESLint `nextVitals is not iterable`은 exit code 0이면 non-blocking으로 기록.

## 14. 다음 작업 제안
- `node tmp/check_filedropzone_common_ui_move.mjs`
- `npm run typecheck`
- `npm run build`
- `node tmp/check_ocr_core_types_common_move_5a.mjs`
- `node tmp/check_ocr_core_ops_common_move_5b.mjs`
- `node tmp/check_ocr_core_table_common_move_5c.mjs`
- `node tmp/check_template_export_payload_move_5d.mjs`
- `node tmp/check_validation_baseline_repair_1a.mjs`
- `node tmp/check_runocr_formdata_keys_2a.mjs`
- `node tmp/check_runocr_response_mapping_boundary_2c.mjs`

다음 실제 작업은 `FRONTEND-STRUCTURE-5E-FILEDROPZONE-COMMON-UI-MOVE` micro-step으로 FileDropzone만 먼저 옮기고, 그 다음 `OcrCanvasPane` common/ui 이동을 진행하는 순서가 안전하다.
