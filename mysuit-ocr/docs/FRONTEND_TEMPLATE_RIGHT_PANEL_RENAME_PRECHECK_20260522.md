# FRONTEND Template Right Panel Rename Precheck - 2026-05-22

## 1. 사용 도구와 모델
- 사용 도구: Codex
- 사용 모델: Codex
- 작업명: CODEX_FRONTEND_TEMPLATE_RIGHT_PANEL_RENAME_PRECHECK_NO_PROD_MODIFY

## 2. 코드 수정 여부
- 운영 코드 수정: 없음
- 파일 이동/import 수정/rename/refactor: 없음
- 생성 허용 파일만 작성했다.

## 3. 생성 파일
- `tmp/codex_frontend_template_right_panel_rename_precheck.py`
- `docs/FRONTEND_TEMPLATE_RIGHT_PANEL_RENAME_PRECHECK_20260522.md`
- `docs/FRONTEND_TEMPLATE_RIGHT_PANEL_RENAME_PRECHECK_20260522.json`
- `docs/FRONTEND_TEMPLATE_RIGHT_PANEL_RENAME_PRECHECK_MAP_20260522.csv`

## 4. 분석 범위
- `src/components/template/ui/OcrRightPanel.tsx`
- `src/components/template/ui/OcrAnnotator.tsx`
- `src/common/ui/OcrCanvasPane.tsx`
- `src/components/template/TemplateWorkspace.tsx`
- `src/app/ocr/page.tsx`
- `src/app/template/page.tsx`
- `src/components/runocr/RunOcrWorkspace.tsx`
- `src/components/test/TestWorkspace.tsx` 읽기 전용 범위

## 5. OcrRightPanel 역할 요약
- currentPath: `src/components/template/ui/OcrRightPanel.tsx`
- lineCount: 507
- export: default `OcrRightPanel`
- props: imgRef, templateName, setTemplateName, documentType, setDocumentType, loaded, regions, setRegions, selectedId, setSelectedId, rowTemplateTargetId, setRowTemplateTargetId, colGuideTargetId, setColGuideTargetId, updateName, deleteRegion
- 역할: Template editor right panel. 템플릿명/문서유형, 출력 필드 정의, 선택 region preview, table row/col guide, stop keywords, table column metadata를 다룬다.
- Template 전용 여부: YES
- OcrCanvasPane 관계: 직접 import하지 않고 OcrAnnotator가 selection/region/table state를 중재한다.
- OcrAnnotator 관계: 유일한 production consumer.
- RunOCR/Test 의존: 직접 import 없음.

Imports:
- `import React, { useEffect, useMemo, useRef, useState } from "react";`
- `import type { FieldType, LoadedImage, Region, TableColumnDef } from "../../../common/types/ocr";`
- `import { normalizeRatios, calcMultiSubRegions } from "../../../common/utils/ocrCanvasOps";`
- `import { normalizeColGuides } from "../../../common/utils/ocrTableRegion";`

Exports:
- `export default function OcrRightPanel(props: Props) {`

## 6. importedBy 분석
| file | importPath | feature | usagePurpose |
|---|---|---|---|
| `src/components/template/ui/OcrAnnotator.tsx` | `./OcrRightPanel` | template | Template annotator right panel for template metadata, output field definitions, selected region preview, table controls, and table column metadata. |

`components/ocr/OcrRightPanel` 런타임 import는 남아 있지 않다. 검색 결과의 다수는 과거 docs/tmp static check 기록이다.

## 7. rename 적합성
- 판정: `RENAME_READY_FILE_AND_SYMBOLS`
- 이유: 현재 파일은 Template 전용 UI이고 direct consumer가 `OcrAnnotator` 하나뿐이다.
- 파일명만 바꾸면 내부 default function 이름 `OcrRightPanel`이 남아 파일명과 심볼명이 어긋난다.
- 따라서 실제 rename micro-step에서는 파일명과 default component/local import symbol을 함께 `TemplateRightPanel`로 맞추는 것이 유지보수성 측면에서 낫다.
- `Props` type은 로컬 비-export 타입이므로 `TemplateRightPanelProps`로 바꾸는 것은 선택 사항이다. 이번 추천은 component symbol까지이며, props type rename은 static check 난이도를 조금 올리므로 필요 시 포함한다.

## 8. rename 범위 후보 비교
| option | title | recommended | staticCheck | pros | cons |
|---|---|---:|---|---|---|
| A | file only rename | NO | LOW | Smallest diff; No internal symbol churn; Lowest logic risk | File name and default function name diverge; OcrRightPanel string remains in source |
| B | file + component symbol rename | YES | MEDIUM_LOW | File and component naming align; Template ownership is clear to maintainers; Still a narrow single-consumer rename | Slightly more text churn than file-only rename |
| C | defer rename | NO | LOW | No immediate churn | Leaves Template-only UI with OCR-prefixed name after structure cleanup |

## 9. 실제 rename 추천
- 추천: B. 파일명 + default component/local import symbol rename
- 실제 범위:
  - `src/components/template/ui/OcrRightPanel.tsx` -> `src/components/template/ui/TemplateRightPanel.tsx`
  - `export default function OcrRightPanel` -> `TemplateRightPanel`
  - `OcrAnnotator` import path/local identifier/render tag 수정
- 수정하지 않을 범위: RunOCR, TestWorkspace, common/ui/OcrCanvasPane, TemplateWorkspace, app routes.
- 위험도: LOW_MEDIUM

## 10. static check 설계
- src/components/template/ui/TemplateRightPanel.tsx exists
- src/components/template/ui/OcrRightPanel.tsx is absent
- OcrAnnotator imports ./TemplateRightPanel
- OcrAnnotator renders <TemplateRightPanel
- components/ocr/OcrRightPanel string is absent
- components/template/ui/OcrRightPanel import path string is absent
- RunOCR files are not modified
- TestWorkspace is not modified
- common/ui/OcrCanvasPane.tsx is not modified
- npm run typecheck PASS
- npm run build PASS
- 4A/4B/5A/5B/5C/5D/5E/5F checks PASS where applicable
- validation baseline repair check PASS

## 11. dirty 상태
```text
  M mysuit-ocr/docs/FRONTEND_CLEANUP_1B_JS_CLEAN_JSON_FIXTURE_RUNNER_20260521.json
  M mysuit-ocr/docs/FRONTEND_CLEANUP_1B_JS_CLEAN_JSON_FIXTURE_RUNNER_20260521.md
  M mysuit-ocr/docs/FRONTEND_CLEANUP_3D2_RUNNER_RESULT_20260521.json
 R  mysuit-ocr/src/components/ocr/core/types.ts -> mysuit-ocr/src/common/types/ocr.ts
 R  mysuit-ocr/src/components/common/FileDropzone.tsx -> mysuit-ocr/src/common/ui/FileDropzone.tsx
 RM mysuit-ocr/src/components/ocr/OcrCanvasPane.tsx -> mysuit-ocr/src/common/ui/OcrCanvasPane.tsx
 RM mysuit-ocr/src/components/ocr/core/ops.ts -> mysuit-ocr/src/common/utils/ocrCanvasOps.ts
 RM mysuit-ocr/src/components/ocr/core/table.ts -> mysuit-ocr/src/common/utils/ocrTableRegion.ts
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
 ?? mysuit-ocr/docs/FRONTEND_FILEDROPZONE_COMMON_UI_PRECHECK_20260522.json
 ?? mysuit-ocr/docs/FRONTEND_FILEDROPZONE_COMMON_UI_PRECHECK_20260522.md
 ?? mysuit-ocr/docs/FRONTEND_FILEDROPZONE_COMMON_UI_PRECHECK_MAP_20260522.csv
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
 ?? mysuit-ocr/docs/FRONTEND_STRUCTURE_5E_FILEDROPZONE_COMMON_UI_MOVE_20260522.json
 ?? mysuit-ocr/docs/FRONTEND_STRUCTURE_5E_FILEDROPZONE_COMMON_UI_MOVE_20260522.md
 ?? mysuit-ocr/docs/FRONTEND_STRUCTURE_5F_OCR_CANVAS_PANE_COMMON_UI_MOVE_20260522.json
 ?? mysuit-ocr/docs/FRONTEND_STRUCTURE_5F_OCR_CANVAS_PANE_COMMON_UI_MOVE_20260522.md
 ?? mysuit-ocr/docs/FRONTEND_VALIDATION_1A_BASELINE_REPAIR_20260522.json
 ?? mysuit-ocr/docs/FRONTEND_VALIDATION_1A_BASELINE_REPAIR_20260522.md
 ?? mysuit-ocr/docs/FRONTEND_VALIDATION_BASELINE_REPAIR_PRECHECK_20260522.json
 ?? mysuit-ocr/docs/FRONTEND_VALIDATION_BASELINE_REPAIR_PRECHECK_20260522.md
 ?? mysuit-ocr/docs/FRONTEND_VALIDATION_BASELINE_REPAIR_PRECHECK_MAP_20260522.csv
 ?? mysuit-ocr/docs/MARKDOWN_V1_FIXTURE_CHECK_post_FILEDROPZONE_COMMON_UI_MOVE_20260522_20260521.json
 ?? mysuit-ocr/docs/MARKDOWN_V1_FIXTURE_CHECK_post_FILEDROPZONE_COMMON_UI_MOVE_20260522_20260521.md
 ?? mysuit-ocr/docs/MARKDOWN_V1_FIXTURE_CHECK_post_OCR_CANVAS_PANE_COMMON_UI_MOVE_20260522_20260521.json
 ?? mysuit-ocr/docs/MARKDOWN_V1_FIXTURE_CHECK_post_OCR_CANVAS_PANE_COMMON_UI_MOVE_20260522_20260521.md
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
 ?? mysuit-ocr/tmp/check_filedropzone_common_ui_move_5e.mjs
 ?? mysuit-ocr/tmp/check_ocr_canvas_pane_common_ui_move_5f.mjs
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
 ?? mysuit-ocr/tmp/codex_frontend_template_right_panel_rename_precheck.py
 ?? mysuit-ocr/tmp/codex_frontend_validation_baseline_repair_precheck.py
```

## 12. typecheck/build 결과
- `npm run typecheck`: PASS (exit 0)
- `npm run build`: PASS (exit 0)
- stdout log: `ocr-server/logs/codex_CODEX_FRONTEND_TEMPLATE_RIGHT_PANEL_RENAME_PRECHECK_NO_PROD_MODIFY.out.log`
- stderr log: `ocr-server/logs/codex_CODEX_FRONTEND_TEMPLATE_RIGHT_PANEL_RENAME_PRECHECK_NO_PROD_MODIFY.err.log`
- known stderr noise: ESLint `nextVitals is not iterable`은 exit code 0이면 non-blocking으로 기록.

## 13. 다음 작업 제안
- `node tmp/check_template_right_panel_rename_6a.mjs`
- `npm run typecheck`
- `npm run build`
- `node tmp/check_template_workspace_move_4a.mjs`
- `node tmp/check_template_editor_ui_move_4b.mjs`
- `node tmp/check_ocr_core_types_common_move_5a.mjs`
- `node tmp/check_ocr_core_ops_common_move_5b.mjs`
- `node tmp/check_ocr_core_table_common_move_5c.mjs`
- `node tmp/check_template_export_payload_move_5d.mjs`
- `node tmp/check_filedropzone_common_ui_move_5e.mjs`
- `node tmp/check_ocr_canvas_pane_common_ui_move_5f.mjs`
- `node tmp/check_validation_baseline_repair_1a.mjs`

다음 실제 작업은 `FRONTEND-STRUCTURE-6A-TEMPLATE-RIGHT-PANEL-RENAME`으로 작게 진행하고, 이후 Template table column definition 설계 precheck로 이어가는 것이 자연스럽다.
