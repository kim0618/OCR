# FRONTEND_LIB_INVOICE_FIELD_LABELS_COMMON_MOVE_PRECHECK_20260522

## 1. 사용 도구와 모델
- 도구: Codex
- 모델: Codex
- 작업명: CODEX_FRONTEND_LIB_INVOICE_FIELD_LABELS_COMMON_MOVE_PRECHECK_NO_PROD_MODIFY

## 2. 코드 수정 여부
- 운영 코드 수정 여부: false
- 파일 이동/import 수정/rename/fixture/templates/backend 수정: false
- 생성 가능한 precheck 산출물만 작성했다.

## 3. 생성 파일
- `tmp/codex_frontend_lib_invoice_field_labels_common_move_precheck.py`
- `docs/FRONTEND_LIB_INVOICE_FIELD_LABELS_COMMON_MOVE_PRECHECK_20260522.md`
- `docs/FRONTEND_LIB_INVOICE_FIELD_LABELS_COMMON_MOVE_PRECHECK_20260522.json`
- `docs/FRONTEND_LIB_INVOICE_FIELD_LABELS_COMMON_MOVE_PRECHECK_MAP_20260522.csv`

## 4. 분석 범위
- `src/lib/invoiceFieldLabels.ts`
- `src/common/utils/ocrResultFormatters.ts`
- `src/components/runocr`
- `src/components/template`
- `src/common`
- `src/components/test/TestWorkspace.tsx`
- `src/app`

참고 리포트:
- `docs/FRONTEND_LIB_OWNERSHIP_PRECHECK_20260522.md`
- `docs/FRONTEND_LIB_1A_OCR_RESULT_FORMATTERS_COMMON_MOVE_20260522.md`
- `docs/FRONTEND_STRUCTURE_6B_TEMPLATE_ANNOTATOR_RENAME_20260522.md`
- `docs/FRONTEND_STRUCTURE_5F_OCR_CANVAS_PANE_COMMON_UI_MOVE_20260522.md`

## 5. invoiceFieldLabels 역할 요약
- currentPath: `src/lib/invoiceFieldLabels.ts`
- lineCount: 65
- mainResponsibility: UI-only invoice_statement canonical field label dictionary and field label resolver helpers.
- label dictionary: True
- sideEffects: False
- browser/localStorage/IndexedDB: False
- React 의존: False
- components/* 의존: False
- common/utils 적합성: Good fit: static label dictionary and pure resolver helpers with no imports, React, DOM, storage, backend, or components/* dependency.
- moveRisk: LOW

imports:
- 없음

exports:
- `export const INVOICE_FIELD_KO: Record<string, string> = {`
- `export function resolveFieldLabel(opts: {`
- `export function fieldDisplayLabel(opts: { name?: string; ko?: string; en?: string }): string {`

exported names:
INVOICE_FIELD_KO, resolveFieldLabel, fieldDisplayLabel

## 6. importedBy 분석
| file | importPath | kind | imported symbols | feature | import 수정 필요 | TestWorkspace 영향 |
|---|---|---|---|---|---:|---:|
| `src/common/utils/ocrResultFormatters.ts` | `@/lib/invoiceFieldLabels` | static | `{ resolveFieldLabel }` | common | True | False |
| `src/components/runocr/ui/OcrDocViewer.tsx` | `@/lib/invoiceFieldLabels` | static | `{ resolveFieldLabel }` | runocr | True | False |

## 7. common/utils 적합성
- 판정: `COMMON_UTIL_READY_WITH_IMPORT_ONLY`
- 이유: The file is a no-import static label dictionary plus pure resolver helpers. Moving to common/utils only requires import path updates in ocrResultFormatters and OcrDocViewer.
- common -> components 의존 발생 여부: false
- TestWorkspace 직접 import 영향: false

## 8. ocrResultFormatters 임시 의존 해소 가능성
- ocrResultFormatters path: `src/common/utils/ocrResultFormatters.ts`
- 현재 `@/lib/invoiceFieldLabels` import 중: True
- 추천 import: `@/common/utils/invoiceFieldLabels`
- 해소 가능: True
- 순환 의존 위험: LOW
- 판단: invoiceFieldLabels has no import dependencies, so ocrResultFormatters can import it from common/utils without introducing a cycle.

## 9. target path 비교
| target | 추천 | 장점 | 단점 | import 수정 범위 | risk |
|---|---:|---|---|---|---|
| `src/common/utils/invoiceFieldLabels.ts` | True | Resolves common/utils/ocrResultFormatters temporary runtime import from src/lib; Matches static shared label dictionary role; Keeps RunOCR display helper dependency common | Requires import-only updates in two consumers | src/common/utils/ocrResultFormatters.ts; src/components/runocr/ui/OcrDocViewer.tsx | LOW |
| `src/components/runocr/utils/invoiceFieldLabels.ts` | False | Close to OcrDocViewer consumer | common/utils/ocrResultFormatters would need to import from components/runocr, which violates common boundary; Not suitable while ocrResultFormatters is common | src/common/utils/ocrResultFormatters.ts; src/components/runocr/ui/OcrDocViewer.tsx | HIGH |
| `src/lib/invoiceFieldLabels.ts` | False | No immediate code change | Leaves common/utils -> src/lib temporary dependency unresolved; Does not progress LIB-1 cleanup | none | LOW |
| `DEFER` | False | Avoids current dirty-state interaction | Unnecessary given pure no-import file and small consumer surface | none | LOW |

## 10. 실제 이동 추천
- 추천 선택지: A. `invoiceFieldLabels.ts`만 `src/common/utils/invoiceFieldLabels.ts`로 이동
- 이유: 단순 label dictionary/helper이고 import가 없는 순수 파일이며, 1A 이후 남은 `common/utils/ocrResultFormatters.ts -> @/lib/invoiceFieldLabels` 임시 runtime 의존을 해소한다.
- 필요한 import 수정: `src/common/utils/ocrResultFormatters.ts`, `src/components/runocr/ui/OcrDocViewer.tsx`
- D는 사실상 A의 import 조정에 포함된다. 추가 파일 이동은 하지 않는다.

## 11. static check 설계
- tmp/check_lib_invoice_field_labels_common_move_1b.mjs
- src/common/utils/invoiceFieldLabels.ts exists
- src/lib/invoiceFieldLabels.ts absent
- src/common/utils/invoiceFieldLabels.ts does not import src/components/*
- React/localStorage/window/document/fetch/indexedDB dependency remains absent
- src/common/utils/ocrResultFormatters.ts imports @/common/utils/invoiceFieldLabels
- src/components/runocr/ui/OcrDocViewer.tsx imports @/common/utils/invoiceFieldLabels
- @/lib/invoiceFieldLabels string absent from src
- No circular dependency between common/utils/ocrResultFormatters and common/utils/invoiceFieldLabels
- TestWorkspace unchanged
- RunOCR boundary checks PASS
- Template checks PASS
- table_view_model/Clean JSON/Markdown checks PASS
- npm run typecheck PASS
- npm run build PASS

## 12. dirty 상태
```text
 M docs/FRONTEND_CLEANUP_1B_JS_CLEAN_JSON_FIXTURE_RUNNER_20260521.json
 M docs/FRONTEND_CLEANUP_1B_JS_CLEAN_JSON_FIXTURE_RUNNER_20260521.md
 M docs/FRONTEND_CLEANUP_3D2_RUNNER_RESULT_20260521.json
 M src/app/ocr/page.tsx
 M src/app/template/page.tsx
R  src/components/ocr/core/types.ts -> src/common/types/ocr.ts
R  src/components/common/FileDropzone.tsx -> src/common/ui/FileDropzone.tsx
RM src/components/ocr/OcrCanvasPane.tsx -> src/common/ui/OcrCanvasPane.tsx
RM src/components/ocr/core/ops.ts -> src/common/utils/ocrCanvasOps.ts
R  src/lib/ocrResultFormatters.ts -> src/common/utils/ocrResultFormatters.ts
RM src/components/ocr/core/table.ts -> src/common/utils/ocrTableRegion.ts
 M src/components/runocr/RunOcrWorkspace.tsx
 M src/components/runocr/ui/OcrResultPanel.tsx
 M src/components/runocr/utils/buildOcrFormData.ts
RM src/components/template/ui/OcrAnnotator.tsx -> src/components/template/ui/TemplateAnnotator.tsx
RM src/components/template/ui/OcrRightPanel.tsx -> src/components/template/ui/TemplateRightPanel.tsx
RM src/components/ocr/core/export.ts -> src/components/template/utils/buildTemplateExportPayload.ts
 M src/lib/markdownReportBuilder.ts
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
?? docs/FRONTEND_LIB_1A_OCR_RESULT_FORMATTERS_COMMON_MOVE_20260522.json
?? docs/FRONTEND_LIB_1A_OCR_RESULT_FORMATTERS_COMMON_MOVE_20260522.md
?? docs/FRONTEND_LIB_OCR_RESULT_FORMATTERS_COMMON_MOVE_PRECHECK_20260522.json
?? docs/FRONTEND_LIB_OCR_RESULT_FORMATTERS_COMMON_MOVE_PRECHECK_20260522.md
?? docs/FRONTEND_LIB_OCR_RESULT_FORMATTERS_COMMON_MOVE_PRECHECK_MAP_20260522.csv
?? docs/FRONTEND_LIB_OWNERSHIP_MAP_20260522.csv
?? docs/FRONTEND_LIB_OWNERSHIP_PRECHECK_20260522.json
?? docs/FRONTEND_LIB_OWNERSHIP_PRECHECK_20260522.md
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
?? docs/FRONTEND_STRUCTURE_6B_TEMPLATE_ANNOTATOR_RENAME_20260522.json
?? docs/FRONTEND_STRUCTURE_6B_TEMPLATE_ANNOTATOR_RENAME_20260522.md
?? docs/FRONTEND_TEMPLATE_ANNOTATOR_RENAME_PRECHECK_20260522.json
?? docs/FRONTEND_TEMPLATE_ANNOTATOR_RENAME_PRECHECK_20260522.md
?? docs/FRONTEND_TEMPLATE_ANNOTATOR_RENAME_PRECHECK_MAP_20260522.csv
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
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_LIB_OCR_RESULT_FORMATTERS_COMMON_MOVE_20260522_20260521.json
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_LIB_OCR_RESULT_FORMATTERS_COMMON_MOVE_20260522_20260521.md
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_OCR_CANVAS_PANE_COMMON_UI_MOVE_20260522_20260521.json
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_OCR_CANVAS_PANE_COMMON_UI_MOVE_20260522_20260521.md
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_OCR_CORE_OPS_COMMON_MOVE_20260522_20260521.json
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_OCR_CORE_OPS_COMMON_MOVE_20260522_20260521.md
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_OCR_CORE_TABLE_COMMON_MOVE_20260522_20260521.json
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_OCR_CORE_TABLE_COMMON_MOVE_20260522_20260521.md
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_OCR_CORE_TYPES_COMMON_MOVE_20260522_20260521.json
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_OCR_CORE_TYPES_COMMON_MOVE_20260522_20260521.md
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_TEMPLATE_ANNOTATOR_RENAME_20260522_20260521.json
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_TEMPLATE_ANNOTATOR_RENAME_20260522_20260521.md
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_TEMPLATE_EXPORT_PAYLOAD_MOVE_20260522_20260521.json
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_TEMPLATE_EXPORT_PAYLOAD_MOVE_20260522_20260521.md
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_TEMPLATE_RIGHT_PANEL_RENAME_20260522_20260521.json
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_TEMPLATE_RIGHT_PANEL_RENAME_20260522_20260521.md
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_VALIDATION_BASELINE_REPAIR_20260522_20260521.json
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_VALIDATION_BASELINE_REPAIR_20260522_20260521.md
?? tmp/check_filedropzone_common_ui_move_5e.mjs
?? tmp/check_lib_ocr_result_formatters_common_move_1a.mjs
?? tmp/check_ocr_canvas_pane_common_ui_move_5f.mjs
?? tmp/check_ocr_core_ops_common_move_5b.mjs
?? tmp/check_ocr_core_table_common_move_5c.mjs
?? tmp/check_ocr_core_types_common_move_5a.mjs
?? tmp/check_template_annotator_rename_6b.mjs
?? tmp/check_template_export_payload_move_5d.mjs
?? tmp/check_template_right_panel_rename_6a.mjs
?? tmp/check_validation_baseline_repair_1a.mjs
?? tmp/codex_frontend_filedropzone_common_ui_precheck.py
?? tmp/codex_frontend_lib_invoice_field_labels_common_move_precheck.py
?? tmp/codex_frontend_lib_ocr_result_formatters_common_move_precheck.py
?? tmp/codex_frontend_lib_ownership_precheck.py
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

- `../ocr-server/data/templates.json` dirty 상태가 있으면 실제 이동 전 영향 후보로 유지한다.
- TPL-95328E52 dirty 영향 precheck 후보를 유지한다.

## 13. typecheck/build 결과
- typecheck: `PASS` exitCode=0
- build: `PASS` exitCode=0
- known stderr noise: ESLint `nextVitals is not iterable`은 exit code 0이면 known issue로 기록한다.

## 14. 다음 작업 제안
- Proceed with option A as a small move-only micro-step.
- Create a move-specific static checker before or during the actual move step.
- Confirm @/lib/invoiceFieldLabels is absent from src after the move.
- Continue LIB-1 with another low-risk pure helper only after checks pass.
