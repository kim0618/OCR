# FRONTEND_TEMPLATE_ANNOTATOR_RENAME_PRECHECK_20260522

## 1. 사용 도구와 모델
- 도구: Codex
- 모델: Codex
- 작업명: CODEX_FRONTEND_TEMPLATE_ANNOTATOR_RENAME_PRECHECK_NO_PROD_MODIFY

## 2. 코드 수정 여부
- 운영 코드 수정 여부: false
- 파일 이동/import 수정/rename 수행 여부: false
- 생성 파일만 작성했다.

## 3. 생성 파일
- `tmp/codex_frontend_template_annotator_rename_precheck.py`
- `docs/FRONTEND_TEMPLATE_ANNOTATOR_RENAME_PRECHECK_20260522.md`
- `docs/FRONTEND_TEMPLATE_ANNOTATOR_RENAME_PRECHECK_20260522.json`
- `docs/FRONTEND_TEMPLATE_ANNOTATOR_RENAME_PRECHECK_MAP_20260522.csv`

## 4. 분석 범위
- `src/components/template/ui/OcrAnnotator.tsx`
- `src/components/template/ui/TemplateRightPanel.tsx`
- `src/common/ui/OcrCanvasPane.tsx`
- `src/components/template/TemplateWorkspace.tsx`
- `src/app/ocr/page.tsx`
- `src/app/template/page.tsx`
- `src/components/runocr/RunOcrWorkspace.tsx`
- `src/components/test/TestWorkspace.tsx`
- `src/components/template/utils/buildTemplateExportPayload.ts`

참고 리포트:
- `docs/FRONTEND_STRUCTURE_4B_TEMPLATE_EDITOR_UI_MOVE_20260522.md`
- `docs/FRONTEND_STRUCTURE_5F_OCR_CANVAS_PANE_COMMON_UI_MOVE_20260522.md`
- `docs/FRONTEND_STRUCTURE_6A_TEMPLATE_RIGHT_PANEL_RENAME_20260522.md`
- `docs/FRONTEND_TEMPLATE_EDITOR_UI_OWNERSHIP_PRECHECK_20260522.md`

## 5. OcrAnnotator 역할 요약
- currentPath: `src/components/template/ui/OcrAnnotator.tsx`
- lineCount: 442
- exports: `export default function OcrAnnotator({`
- props: `{ selectedTemplate = null, selectedTemplateId = null, }: { selectedTemplate?: any | null; selectedTemplateId?: string | null; }`
- 주요 역할: Template editor annotator that coordinates upload/PDF rendering, template metadata, region drawing state, right-panel editing, local/IndexedDB image persistence, and template save/export payload creation.
- Template 전용 여부: true
- TemplateWorkspace 관계: Used indirectly by /ocr when TemplateWorkspace switches from list mode to editor mode; TemplateWorkspace itself does not import OcrAnnotator.
- app/ocr 관계: Legacy /ocr route dynamically imports and renders it for new-template editor mode.
- app/template 관계: /template route dynamically imports and renders it for template create/edit mode.
- OcrCanvasPane 관계: Parent of common OcrCanvasPane; passes image refs, loaded image, region state, selection, table guide targets, draw mode, and zoom.
- TemplateRightPanel 관계: Parent of TemplateRightPanel; passes template metadata, document type, selected region state, table target setters, and update/delete callbacks.
- buildTemplateExportPayload 관계: Directly imports buildExportPayload and memoizes the save/export payload from templateName, loaded image, regions, and documentType.
- RunOCR/Test 의존 여부: No direct RunOCR import of OcrAnnotator found; RunOCR shares OcrCanvasPane only. / No direct TestWorkspace import of OcrAnnotator found.
- renameRisk: LOW_MEDIUM

imports:
- `import React, { useEffect, useMemo, useRef, useState, useCallback } from "react";`
- `import type { FieldType, LoadedImage, Region } from "../../../common/types/ocr";`
- `import { buildExportPayload } from "../utils/buildTemplateExportPayload";`
- `import OcrCanvasPane from "../../../common/ui/OcrCanvasPane";`
- `import TemplateRightPanel from "./TemplateRightPanel";`
- `import { saveTemplateImage, getTemplateImage, deleteTemplateImage } from "@/lib/imageStore";`
- `import { useUi } from "../../common/AppProviders";`

## 6. importedBy 분석
| file | importPath | kind | feature | rename import 수정 |
|---|---|---|---|---|
| `src/app/ocr/page.tsx` | `../../components/template/ui/OcrAnnotator` | dynamic | route | True |
| `src/app/template/page.tsx` | `../../components/template/ui/OcrAnnotator` | dynamic | template | True |

## 7. route 영향 분석
| route | dynamic import | importPath | usageCount | 영향 |
|---|---:|---|---:|---|
| `src/app/ocr/page.tsx` | True | `../../components/template/ui/OcrAnnotator` | 1 | No route policy change needed; rename only changes the dynamic import path and optionally local symbol. |
| `src/app/template/page.tsx` | True | `../../components/template/ui/OcrAnnotator` | 1 | No route policy change needed; rename only changes the dynamic import path and optionally local symbol. |

- `/ocr` route 이름 정책은 이번 rename과 분리한다.
- route policy 변경 없이 dynamic import path와 local symbol만 바꿀 수 있다.

## 8. rename 적합성
- 판정: `RENAME_READY_FILE_AND_SYMBOLS`
- 이유: Production import surface is limited to two route dynamic imports. The component is Template-domain UI, and retaining OcrAnnotator as the default function after a TemplateAnnotator file rename would leave an avoidable file/internal-symbol mismatch.
- RunOCR/Test 직접 import 없음: true
- route와 Template editor 사용처만 영향: true

## 9. rename 범위 후보 비교
| 후보 | 추천 | 장점 | 단점 | import 수정 범위 | static check 난이도 |
|---|---:|---|---|---|---|
| candidate1_file_only | False | Smallest diff; Only route dynamic import path strings need to change | File name and default component name remain inconsistent; Searches for OcrAnnotator still point at the renamed file | src/app/ocr/page.tsx; src/app/template/page.tsx | LOW |
| candidate2_file_and_symbols | True | Best matches Template domain ownership; Avoids lingering public component-name mismatch; Still has a very small production touch set | Slightly larger textual rename than file-only | src/app/ocr/page.tsx; src/app/template/page.tsx | LOW_MEDIUM |
| candidate3_defer | False | No immediate production change | Leaves the last Template UI filename mismatch unresolved | 없음 | LOW |

## 10. 실제 rename 추천
- 추천 선택지: B. 파일명 + component/function/type 이름까지 TemplateAnnotator로 rename
- 권장 범위: Rename file plus default function/local dynamic component symbols to TemplateAnnotator; keep prop shape and logic unchanged.
- 필요한 import 수정:
  - src/app/ocr/page.tsx dynamic import path and local const/render symbol
  - src/app/template/page.tsx dynamic import path and local const/render symbol
- 보류:
  - Do not change route policy for /ocr
  - Do not touch TestWorkspace
  - Do not modify templates.json or fixtures
  - Only rename inline props type if introduced as a named type in the same micro-step; no API shape change
- 위험도: LOW_MEDIUM

## 11. static check 설계
- tmp/check_template_annotator_rename_6b.mjs
- src/components/template/ui/TemplateAnnotator.tsx exists
- src/components/template/ui/OcrAnnotator.tsx absent
- src/app/ocr/page.tsx dynamic import points to ../../components/template/ui/TemplateAnnotator
- src/app/template/page.tsx dynamic import points to ../../components/template/ui/TemplateAnnotator
- No components/ocr/OcrAnnotator string remains in src
- No components/template/ui/OcrAnnotator import path remains in src
- RunOCR/TestWorkspace unchanged by actual rename step
- common/ui/OcrCanvasPane unchanged unless comment-only rename is explicitly included
- TemplateRightPanel unchanged
- npm run typecheck PASS
- npm run build PASS
- Existing 4A/4B/5A/5B/5C/5D/5E/5F/6A checks remain PASS
- validation baseline repair check remains PASS

## 12. dirty 상태
```text
 M docs/FRONTEND_CLEANUP_1B_JS_CLEAN_JSON_FIXTURE_RUNNER_20260521.json
 M docs/FRONTEND_CLEANUP_1B_JS_CLEAN_JSON_FIXTURE_RUNNER_20260521.md
 M docs/FRONTEND_CLEANUP_3D2_RUNNER_RESULT_20260521.json
R  src/components/ocr/core/types.ts -> src/common/types/ocr.ts
R  src/components/common/FileDropzone.tsx -> src/common/ui/FileDropzone.tsx
RM src/components/ocr/OcrCanvasPane.tsx -> src/common/ui/OcrCanvasPane.tsx
RM src/components/ocr/core/ops.ts -> src/common/utils/ocrCanvasOps.ts
RM src/components/ocr/core/table.ts -> src/common/utils/ocrTableRegion.ts
 M src/components/runocr/RunOcrWorkspace.tsx
 M src/components/runocr/utils/buildOcrFormData.ts
 M src/components/template/ui/OcrAnnotator.tsx
RM src/components/template/ui/OcrRightPanel.tsx -> src/components/template/ui/TemplateRightPanel.tsx
RM src/components/ocr/core/export.ts -> src/components/template/utils/buildTemplateExportPayload.ts
 M tmp/check_runocr_doc_comments_3b.mjs
 M tmp/check_runocr_formdata_keys_2a.mjs
 M tmp/check_runocr_response_mapping_boundary_2c.mjs
 M tmp/check_template_editor_ui_move_4b.mjs
 M tmp/check_template_workspace_move_4a.mjs
 M tmp/codex_markdown_contract_fixture_lock.py
 M ../ocr-server/data/review_log.jsonl
 M ../ocr-server/data/templates.json
?? docs/FRONTEND_FILEDROPZONE_COMMON_UI_PRECHECK_20260522.json
?? docs/FRONTEND_FILEDROPZONE_COMMON_UI_PRECHECK_20260522.md
?? docs/FRONTEND_FILEDROPZONE_COMMON_UI_PRECHECK_MAP_20260522.csv
?? docs/FRONTEND_OCR_CANVAS_PANE_COMMON_MOVE_PRECHECK_20260522.json
?? docs/FRONTEND_OCR_CANVAS_PANE_COMMON_MOVE_PRECHECK_20260522.md
?? docs/FRONTEND_OCR_CANVAS_PANE_COMMON_MOVE_PRECHECK_MAP_20260522.csv
?? docs/FRONTEND_OCR_CANVAS_PANE_SHARED_MAP_20260522.csv
?? docs/FRONTEND_OCR_CANVAS_PANE_SHARED_PRECHECK_20260522.json
?? docs/FRONTEND_OCR_CANVAS_PANE_SHARED_PRECHECK_20260522.md
?? docs/FRONTEND_OCR_CORE_EXPORT_TEMPLATE_UTIL_PRECHECK_20260522.json
?? docs/FRONTEND_OCR_CORE_EXPORT_TEMPLATE_UTIL_PRECHECK_20260522.md
?? docs/FRONTEND_OCR_CORE_EXPORT_TEMPLATE_UTIL_PRECHECK_MAP_20260522.csv
?? docs/FRONTEND_OCR_CORE_OPS_COMMON_MOVE_PRECHECK_20260522.json
?? docs/FRONTEND_OCR_CORE_OPS_COMMON_MOVE_PRECHECK_20260522.md
?? docs/FRONTEND_OCR_CORE_OPS_COMMON_MOVE_PRECHECK_MAP_20260522.csv
?? docs/FRONTEND_OCR_CORE_OWNERSHIP_MAP_20260522.csv
?? docs/FRONTEND_OCR_CORE_OWNERSHIP_PRECHECK_20260522.json
?? docs/FRONTEND_OCR_CORE_OWNERSHIP_PRECHECK_20260522.md
?? docs/FRONTEND_OCR_CORE_TABLE_COMMON_MOVE_PRECHECK_20260522.json
?? docs/FRONTEND_OCR_CORE_TABLE_COMMON_MOVE_PRECHECK_20260522.md
?? docs/FRONTEND_OCR_CORE_TABLE_COMMON_MOVE_PRECHECK_MAP_20260522.csv
?? docs/FRONTEND_STRUCTURE_5A_OCR_CORE_TYPES_COMMON_MOVE_20260522.json
?? docs/FRONTEND_STRUCTURE_5A_OCR_CORE_TYPES_COMMON_MOVE_20260522.md
?? docs/FRONTEND_STRUCTURE_5B_OCR_CORE_OPS_COMMON_MOVE_20260522.json
?? docs/FRONTEND_STRUCTURE_5B_OCR_CORE_OPS_COMMON_MOVE_20260522.md
?? docs/FRONTEND_STRUCTURE_5C_OCR_CORE_TABLE_COMMON_MOVE_20260522.json
?? docs/FRONTEND_STRUCTURE_5C_OCR_CORE_TABLE_COMMON_MOVE_20260522.md
?? docs/FRONTEND_STRUCTURE_5D_TEMPLATE_EXPORT_PAYLOAD_MOVE_20260522.json
?? docs/FRONTEND_STRUCTURE_5D_TEMPLATE_EXPORT_PAYLOAD_MOVE_20260522.md
?? docs/FRONTEND_STRUCTURE_5E_FILEDROPZONE_COMMON_UI_MOVE_20260522.json
?? docs/FRONTEND_STRUCTURE_5E_FILEDROPZONE_COMMON_UI_MOVE_20260522.md
?? docs/FRONTEND_STRUCTURE_5F_OCR_CANVAS_PANE_COMMON_UI_MOVE_20260522.json
?? docs/FRONTEND_STRUCTURE_5F_OCR_CANVAS_PANE_COMMON_UI_MOVE_20260522.md
?? docs/FRONTEND_STRUCTURE_6A_TEMPLATE_RIGHT_PANEL_RENAME_20260522.json
?? docs/FRONTEND_STRUCTURE_6A_TEMPLATE_RIGHT_PANEL_RENAME_20260522.md
?? docs/FRONTEND_TEMPLATE_RIGHT_PANEL_RENAME_PRECHECK_20260522.json
?? docs/FRONTEND_TEMPLATE_RIGHT_PANEL_RENAME_PRECHECK_20260522.md
?? docs/FRONTEND_TEMPLATE_RIGHT_PANEL_RENAME_PRECHECK_MAP_20260522.csv
?? docs/FRONTEND_VALIDATION_1A_BASELINE_REPAIR_20260522.json
?? docs/FRONTEND_VALIDATION_1A_BASELINE_REPAIR_20260522.md
?? docs/FRONTEND_VALIDATION_BASELINE_REPAIR_PRECHECK_20260522.json
?? docs/FRONTEND_VALIDATION_BASELINE_REPAIR_PRECHECK_20260522.md
?? docs/FRONTEND_VALIDATION_BASELINE_REPAIR_PRECHECK_MAP_20260522.csv
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_FILEDROPZONE_COMMON_UI_MOVE_20260522_20260521.json
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_FILEDROPZONE_COMMON_UI_MOVE_20260522_20260521.md
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_OCR_CANVAS_PANE_COMMON_UI_MOVE_20260522_20260521.json
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_OCR_CANVAS_PANE_COMMON_UI_MOVE_20260522_20260521.md
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_OCR_CORE_OPS_COMMON_MOVE_20260522_20260521.json
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_OCR_CORE_OPS_COMMON_MOVE_20260522_20260521.md
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_OCR_CORE_TABLE_COMMON_MOVE_20260522_20260521.json
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_OCR_CORE_TABLE_COMMON_MOVE_20260522_20260521.md
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_OCR_CORE_TYPES_COMMON_MOVE_20260522_20260521.json
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_OCR_CORE_TYPES_COMMON_MOVE_20260522_20260521.md
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_TEMPLATE_EXPORT_PAYLOAD_MOVE_20260522_20260521.json
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_TEMPLATE_EXPORT_PAYLOAD_MOVE_20260522_20260521.md
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_TEMPLATE_RIGHT_PANEL_RENAME_20260522_20260521.json
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_TEMPLATE_RIGHT_PANEL_RENAME_20260522_20260521.md
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_VALIDATION_BASELINE_REPAIR_20260522_20260521.json
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_VALIDATION_BASELINE_REPAIR_20260522_20260521.md
?? tmp/check_filedropzone_common_ui_move_5e.mjs
?? tmp/check_ocr_canvas_pane_common_ui_move_5f.mjs
?? tmp/check_ocr_core_ops_common_move_5b.mjs
?? tmp/check_ocr_core_table_common_move_5c.mjs
?? tmp/check_ocr_core_types_common_move_5a.mjs
?? tmp/check_template_export_payload_move_5d.mjs
?? tmp/check_template_right_panel_rename_6a.mjs
?? tmp/check_validation_baseline_repair_1a.mjs
?? tmp/codex_frontend_filedropzone_common_ui_precheck.py
?? tmp/codex_frontend_ocr_canvas_pane_common_move_precheck.py
?? tmp/codex_frontend_ocr_canvas_pane_shared_precheck.py
?? tmp/codex_frontend_ocr_core_export_template_util_precheck.py
?? tmp/codex_frontend_ocr_core_ops_common_move_precheck.py
?? tmp/codex_frontend_ocr_core_ownership_precheck.py
?? tmp/codex_frontend_ocr_core_table_common_move_precheck.py
?? tmp/codex_frontend_template_annotator_rename_precheck.py
?? tmp/codex_frontend_template_right_panel_rename_precheck.py
?? tmp/codex_frontend_validation_baseline_repair_precheck.py
```

- `../ocr-server/data/templates.json` dirty 상태가 있으면 실제 rename 전 영향 후보로 유지한다.
- TPL-95328E52 dirty 영향 precheck 후보를 유지한다.

## 13. typecheck/build 결과
- typecheck: `PASS` exitCode=0
- build: `PASS` exitCode=0
- known stderr noise: ESLint `nextVitals is not iterable`은 exit code 0이면 known issue로 기록한다.

## 14. 다음 작업 제안
- Proceed with option B as a dedicated rename-only micro-step.
- Before renaming, inspect current dirty diff for src/components/template/ui/OcrAnnotator.tsx.
- Keep /ocr route naming policy separate from this rename.
- After rename, move to Template table column definition design only after checks pass.
