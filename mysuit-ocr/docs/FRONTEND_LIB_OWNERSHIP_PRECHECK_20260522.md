# FRONTEND_LIB_OWNERSHIP_PRECHECK_20260522

## 1. 사용 도구와 모델
- 도구: Codex
- 모델: Codex
- 작업명: CODEX_FRONTEND_LIB_OWNERSHIP_PRECHECK_NO_PROD_MODIFY

## 2. 코드 수정 여부
- 운영 코드 수정 여부: false
- 파일 이동/import 수정/rename/fixture/templates/backend 수정: false
- 생성 가능한 precheck 산출물만 작성했다.

## 3. 생성 파일
- `tmp/codex_frontend_lib_ownership_precheck.py`
- `docs/FRONTEND_LIB_OWNERSHIP_PRECHECK_20260522.md`
- `docs/FRONTEND_LIB_OWNERSHIP_PRECHECK_20260522.json`
- `docs/FRONTEND_LIB_OWNERSHIP_MAP_20260522.csv`

## 4. 분석 범위
- `src/lib`
- `src/components/runocr`
- `src/components/template`
- `src/components/history`
- `src/components/autorestore`
- `src/components/login`
- `src/components/layout`
- `src/components/common`
- `src/components/test`
- `src/common`
- `src/app`

## 5. src/lib 파일별 역할 요약
| file | lines | ownership 후보 | targetPath 후보 | risk | TestWorkspace | mainResponsibility |
|---|---:|---|---|---|---|---|
| `src/lib/autofillEngine.ts` | 485 | 보류/추가 precheck 필요 | `DEFER: split/confirm between src/common/utils/autofillEngine.ts and components/restore/utils/autofillEngine.ts` | HIGH | NO_DIRECT_TEST_IMPORT_FOUND | Autofill candidate collection, suggestion ranking, auto-apply policy, and output-field autofill helpers used around RunOCR/history/restore flows. |
| `src/lib/axios.ts` | 137 | 보류/추가 precheck 필요 | `src/common/utils/axios.ts or src/common/api/axios.ts` | MEDIUM | NO_DIRECT_TEST_IMPORT_FOUND | Axios API client factory/interceptors and auth token/header handling. |
| `src/lib/bizNumber.ts` | 92 | common/utils | `src/common/utils/bizNumber.ts` | HIGH | DEFER_UNTIL_USER_CONFIRMATION | Business registration number extraction/normalization/validation helpers. |
| `src/lib/cleanJsonBuilder.ts` | 171 | common/utils | `src/common/utils/cleanJsonBuilder.ts` | LOW | NO_DIRECT_TEST_IMPORT_FOUND | Clean JSON report/output builder for OCR result fixtures and display contracts. |
| `src/lib/groundTruthStore.ts` | 97 | components/test/utils | `src/components/test/utils/groundTruthStore.ts` | MEDIUM | DEFER_UNTIL_USER_CONFIRMATION | Ground-truth browser storage helpers for TestWorkspace validation data. |
| `src/lib/historyStore.ts` | 807 | components/history/utils | `src/components/history/utils/historyStore.ts` | HIGH | NO_DIRECT_TEST_IMPORT_FOUND | History run index/detail persistence, synchronization, migration, and update helpers. |
| `src/lib/imageStore.ts` | 117 | 보류/추가 precheck 필요 | `src/common/utils/imageStore.ts or src/components/template/utils/imageStore.ts` | HIGH | NO_DIRECT_TEST_IMPORT_FOUND | Template image IndexedDB persistence helpers used by Template and RunOCR template cards. |
| `src/lib/invoiceFieldLabels.ts` | 65 | common/utils | `src/common/utils/invoiceFieldLabels.ts` | MEDIUM | NO_DIRECT_TEST_IMPORT_FOUND | Invoice field label and display metadata dictionaries. |
| `src/lib/invoiceTableDisplay.ts` | 335 | common/utils | `src/common/utils/invoiceTableDisplay.ts` | HIGH | DEFER_UNTIL_USER_CONFIRMATION | Invoice table row/column display policy and row-index visibility helpers. |
| `src/lib/login.ts` | 59 | components/login/utils | `src/components/login/utils/login.ts` | MEDIUM | NO_DIRECT_TEST_IMPORT_FOUND | Login/auth token storage and auth request helpers. |
| `src/lib/markdownReportBuilder.ts` | 81 | common/utils | `src/common/utils/markdownReportBuilder.ts` | LOW | NO_DIRECT_TEST_IMPORT_FOUND | Markdown report builder for OCR clean/structured outputs. |
| `src/lib/ocrResultFormatters.ts` | 120 | common/utils | `src/common/utils/ocrResultFormatters.ts` | LOW | NO_DIRECT_TEST_IMPORT_FOUND | OCR result formatting helpers for text, confidence, and display values. |
| `src/lib/profiles.ts` | 484 | 보류/추가 precheck 필요 | `src/common/utils/profiles.ts or src/components/restore/utils/profiles.ts` | HIGH | DEFER_UNTIL_USER_CONFIRMATION | Document/profile definitions and table-column policy metadata for RunOCR/Test validation. |
| `src/lib/restoreProfileStore.ts` | 86 | components/restore/utils | `src/components/restore/utils/restoreProfileStore.ts` | MEDIUM | NO_DIRECT_TEST_IMPORT_FOUND | Restore/autofill profile persistence in browser storage. |
| `src/lib/structuredTableViewModel.ts` | 140 | common/utils | `src/common/utils/structuredTableViewModel.ts` | LOW | NO_DIRECT_TEST_IMPORT_FOUND | Structured table view-model builder for invoice table rendering and fixtures. |
| `src/lib/testsets.ts` | 217 | components/test/utils | `src/components/test/utils/testsets.ts` | HIGH | DEFER_UNTIL_USER_CONFIRMATION | Test dataset manifest/profile loading helpers for TestWorkspace. |
| `src/lib/theme.ts` | 42 | components/layout/utils | `src/components/layout/utils/theme.ts or src/common/utils/theme.ts` | MEDIUM | NO_DIRECT_TEST_IMPORT_FOUND | Theme metadata/constants used by application shell/theme setup. |

## 6. importedBy 분석 요약
- `src/lib/autofillEngine.ts`: `src/components/history/DetailHistoryView.tsx`(history), `src/components/runocr/RunOcrWorkspace.tsx`(runocr), `src/components/runocr/ui/OcrResultPanel.tsx`(runocr), `src/lib/ocrResultFormatters.ts`(unknown)
- `src/lib/axios.ts`: `src/components/history/HistoryWorkspace.tsx`(history), `src/components/login/LoginWorkspace.tsx`(login)
- `src/lib/bizNumber.ts`: `src/components/history/DetailHistoryView.tsx`(history), `src/components/runocr/RunOcrWorkspace.tsx`(runocr), `src/components/test/core/autofill.ts`(test), `src/components/test/core/extract.ts`(test), `src/components/test/TestWorkspace.tsx`(test)
- `src/lib/cleanJsonBuilder.ts`: `src/components/runocr/ui/OcrResultPanel.tsx`(runocr)
- `src/lib/groundTruthStore.ts`: `src/components/history/DetailHistoryView.tsx`(history), `src/components/runocr/ui/OcrResultPanel.tsx`(runocr)
- `src/lib/historyStore.ts`: `src/components/history/DetailHistoryView.tsx`(history), `src/components/history/HistoryWorkspace.tsx`(history), `src/components/runocr/RunOcrWorkspace.tsx`(runocr)
- `src/lib/imageStore.ts`: `src/app/template/page.tsx`(template), `src/components/runocr/RunOcrWorkspace.tsx`(runocr), `src/components/template/ui/TemplateAnnotator.tsx`(template)
- `src/lib/invoiceFieldLabels.ts`: `src/components/history/DetailHistoryView.tsx`(history), `src/components/runocr/ui/OcrDocViewer.tsx`(runocr), `src/lib/ocrResultFormatters.ts`(unknown)
- `src/lib/invoiceTableDisplay.ts`: `src/components/history/DetailHistoryView.tsx`(history), `src/components/runocr/ui/OcrResultPanel.tsx`(runocr), `src/components/test/TestWorkspace.tsx`(test), `src/lib/cleanJsonBuilder.ts`(unknown)
- `src/lib/login.ts`: `src/components/common/RequireLogin.tsx`(login), `src/components/layout/Header.tsx`(layout), `src/components/login/LoginWorkspace.tsx`(login)
- `src/lib/markdownReportBuilder.ts`: `src/components/runocr/ui/OcrResultPanel.tsx`(runocr)
- `src/lib/ocrResultFormatters.ts`: `src/components/runocr/ui/OcrResultPanel.tsx`(runocr), `src/lib/markdownReportBuilder.ts`(unknown)
- `src/lib/profiles.ts`: `src/components/test/TestWorkspace.tsx`(test), `src/components/test/TestWorkspace.tsx`(test)
- `src/lib/restoreProfileStore.ts`: `src/components/autorestore/AutoRestoreWorkspace.tsx`(restore), `src/components/history/DetailHistoryView.tsx`(history)
- `src/lib/structuredTableViewModel.ts`: `src/components/runocr/ui/OcrResultPanel.tsx`(runocr)
- `src/lib/testsets.ts`: `src/app/api/autofill-cache/route.ts`(app), `src/app/api/ground-truth/route.ts`(app), `src/app/api/ocr-cache/route.ts`(app), `src/app/api/test-images/route.ts`(app), `src/components/test/TestWorkspace.tsx`(test)
- `src/lib/theme.ts`: `src/components/layout/Header.tsx`(layout)

## 7. ownership 분류표
```json
{
  "보류/추가 precheck 필요": 4,
  "common/utils": 7,
  "components/test/utils": 2,
  "components/history/utils": 1,
  "components/login/utils": 1,
  "components/restore/utils": 1,
  "components/layout/utils": 1
}
```

## 8. target path 제안
세부 target path 후보는 위 표와 JSON/CSV에 기록했다. `imageStore`, `autofillEngine`, `profiles`, `axios`는 단일 feature로 확정하지 않고 별도 precheck 후보로 둔다.

## 9. 위험도 분류
- HIGH: src/lib/autofillEngine.ts, src/lib/bizNumber.ts, src/lib/historyStore.ts, src/lib/imageStore.ts, src/lib/invoiceTableDisplay.ts, src/lib/profiles.ts, src/lib/testsets.ts
- 보류: src/lib/autofillEngine.ts, src/lib/axios.ts, src/lib/groundTruthStore.ts, src/lib/imageStore.ts, src/lib/profiles.ts, src/lib/testsets.ts

## 10. 이동 순서 추천
- LIB-1 common formatter/display utils: src/lib/invoiceFieldLabels.ts, src/lib/ocrResultFormatters.ts, src/lib/markdownReportBuilder.ts, src/lib/cleanJsonBuilder.ts, src/lib/invoiceTableDisplay.ts, src/lib/structuredTableViewModel.ts, src/lib/bizNumber.ts. Start with low-risk pure helpers. Include table/clean-json checks when table view-model files move.
- LIB-2 history store: src/lib/historyStore.ts. Separate history persistence precheck; verify HistoryWorkspace and RunOCR history writes.
- LIB-3 restore profile/autofill/image persistence: src/lib/restoreProfileStore.ts, src/lib/autofillEngine.ts, src/lib/profiles.ts, src/lib/imageStore.ts. Do not batch blindly. Autofill/profile/imageStore need separate boundary decisions.
- LIB-4 login/api/theme: src/lib/login.ts, src/lib/axios.ts, src/lib/theme.ts. Confirm login/common API/layout ownership before moving.
- LIB-5 test-related: src/lib/groundTruthStore.ts, src/lib/testsets.ts. Blocked until user explicitly approves TestWorkspace-related work.

## 11. TestWorkspace 관련 보류 항목
- `src/lib/groundTruthStore.ts` -> `src/components/test/utils/groundTruthStore.ts` 후보, 사용자 확인 전 이동 금지
- `src/lib/testsets.ts` -> `src/components/test/utils/testsets.ts` 후보, 사용자 확인 전 이동 금지
- `profiles.ts`, `invoiceTableDisplay.ts`, `bizNumber.ts` 등 TestWorkspace import가 있는 common 후보도 실제 이동 시 TestWorkspace 미수정 검증 필요

## 12. static check 설계
- tmp/check_lib_common_utils_move_xxx.mjs
- tmp/check_history_utils_move_xxx.mjs
- tmp/check_restore_utils_move_xxx.mjs
- target files exist and source files are absent for the active micro-step
- all import paths point at the new target paths
- src/common/utils does not import from src/components/*
- TestWorkspace remains unchanged unless explicitly approved
- RunOCR boundary checks PASS
- Template checks PASS
- table_view_model/Clean JSON/Markdown checks PASS
- npm run typecheck PASS
- npm run build PASS

## 13. dirty 상태
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
RM src/components/ocr/core/table.ts -> src/common/utils/ocrTableRegion.ts
 M src/components/runocr/RunOcrWorkspace.tsx
 M src/components/runocr/utils/buildOcrFormData.ts
RM src/components/template/ui/OcrAnnotator.tsx -> src/components/template/ui/TemplateAnnotator.tsx
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
?? tmp/check_ocr_canvas_pane_common_ui_move_5f.mjs
?? tmp/check_ocr_core_ops_common_move_5b.mjs
?? tmp/check_ocr_core_table_common_move_5c.mjs
?? tmp/check_ocr_core_types_common_move_5a.mjs
?? tmp/check_template_annotator_rename_6b.mjs
?? tmp/check_template_export_payload_move_5d.mjs
?? tmp/check_template_right_panel_rename_6a.mjs
?? tmp/check_validation_baseline_repair_1a.mjs
?? tmp/codex_frontend_filedropzone_common_ui_precheck.py
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

## 14. typecheck/build 결과
- typecheck: `PASS` exitCode=0
- build: `PASS` exitCode=0
- known stderr noise: ESLint `nextVitals is not iterable`은 exit code 0이면 known issue로 기록한다.

## 15. 다음 작업 제안
- Start with LIB-1 low-risk common formatter/display helpers, one small batch at a time.
- Run a dedicated precheck before moving historyStore.
- Run separate ownership prechecks for autofillEngine/profiles/imageStore.
- Keep TestWorkspace-related files deferred until user confirmation.
