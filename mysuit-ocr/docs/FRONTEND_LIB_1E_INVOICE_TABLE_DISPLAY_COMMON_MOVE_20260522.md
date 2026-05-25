# FRONTEND_LIB_1E_INVOICE_TABLE_DISPLAY_COMMON_MOVE 20260522

## 1. 사용 도구와 모델
- 도구: Claude Code (VSCode extension)
- 모델: Claude Opus 4.7 (1M context)
- 작업 디렉터리: `mysuit-ocr/`

## 2. 작업 목적
src/lib 해체 LIB-1 다섯 번째 micro-step. `src/lib/invoiceTableDisplay.ts`만
`src/common/utils/invoiceTableDisplay.ts`로 이동하여 invoice table 표시 정책
helper(`INVOICE_TABLE_COL_PRIORITY`, `INVOICE_COL_LABEL_MAP`,
`normalizeTableCell`, `hasMeaningfulTableValue`, `shouldDisplayRowIndex`,
`buildInvoicePreviewCols`)를 common/utils로 이전한다.

- 본문/시그니처 byte-identical 유지.
- 영향 받은 파일 4곳에서 import path만 보정 (OcrResultPanel + DetailHistoryView +
  TestWorkspace + cleanJsonBuilder).
- 1D에서 남긴 `common/utils/cleanJsonBuilder.ts`의 `@/lib/invoiceTableDisplay`
  runtime 임시 의존을 `@/common/utils/invoiceTableDisplay`로 해소.
- Clean JSON v1 fixture runner의 하드코딩된 invoice path + alias mapping을 새
  위치로 갱신. fixture 미수정 + rebake 미실행.
- TestWorkspace는 **import path-only 변경**만 허용된 상태로 진행 — logic, JSX,
  state, handler, test flow, test/core 구조 모두 byte-identical.
- structuredTableViewModel/bizNumber/autofillEngine 등 다른 lib 파일 미이동.

## 3. 백업 파일
경로: `mysuit-ocr/backup/lib_invoice_table_display_20260522_before_FRONTEND_LIB_1E_INVOICE_TABLE_DISPLAY_COMMON_MOVE/`

| 파일 | bytes |
| --- | --- |
| `invoiceTableDisplay.ts` | 15,277 |
| `OcrResultPanel.tsx` | 81,704 |
| `DetailHistoryView.tsx` | 35,395 |
| `TestWorkspace.tsx` | 299,972 |
| `cleanJsonBuilder.ts` | 5,919 |
| `check_clean_json_v1_fixtures_js.mjs` | 18,058 |

## 4. 이동 파일

| from | to | 방식 | 본문 변경 |
| --- | --- | --- | --- |
| `src/lib/invoiceTableDisplay.ts` | `src/common/utils/invoiceTableDisplay.ts` | `git mv` | 본문 byte-identical. invoiceTableDisplay 자체에는 import가 없는 leaf-ish 파일. |

## 5. 수정 파일 (import path 보정만)

| 파일 | before | after |
| --- | --- | --- |
| `src/components/runocr/ui/OcrResultPanel.tsx` | `@/lib/invoiceTableDisplay` | `@/common/utils/invoiceTableDisplay` |
| `src/components/history/DetailHistoryView.tsx` | `@/lib/invoiceTableDisplay` | `@/common/utils/invoiceTableDisplay` |
| `src/components/test/TestWorkspace.tsx` | `@/lib/invoiceTableDisplay` | `@/common/utils/invoiceTableDisplay` |
| `src/common/utils/cleanJsonBuilder.ts` | `@/lib/invoiceTableDisplay` | `@/common/utils/invoiceTableDisplay` |
| `tmp/check_clean_json_v1_fixtures_js.mjs` (invoice path) | `path.join(ROOT, "src", "lib", "invoiceTableDisplay.ts")` | `path.join(ROOT, "src", "common", "utils", "invoiceTableDisplay.ts")` |
| `tmp/check_clean_json_v1_fixtures_js.mjs` (alias mapping) | `["@/lib/invoiceTableDisplay", "./invoiceTableDisplay.cjs"]` | `["@/common/utils/invoiceTableDisplay", "./invoiceTableDisplay.cjs"]` |

OcrResultPanel.tsx 13줄에 `@/lib/invoiceTableDisplay` 문자열이 doc-comment로
남아 있음. 코드 import 아님, 동작 무영향. 1E 검사는 `stripComments` 후 잔존 검색.

기존 1A/1B/1C/1D 검사 sibling 가드에서 `invoiceTableDisplay.ts` 제거 + 1D의
`new_builder_temp_lib_deps_recorded`와 `runner_logic_unchanged_vs_backup`를
post-1E 상태 허용으로 보완 (검사 로직 변경 없음).

## 6. 핵심 변경 내용
- `common/utils/`에 invoiceTableDisplay.ts 추가 (LIB 입주 6번째).
- 새 파일은 `components/*` / React / React-DOM / window / document / localStorage
  모두 무참조.
- 6개 export(`INVOICE_TABLE_COL_PRIORITY`, `INVOICE_COL_LABEL_MAP`,
  `normalizeTableCell`, `hasMeaningfulTableValue`, `shouldDisplayRowIndex`,
  `buildInvoicePreviewCols`) 전부 보존.
- **1D 임시 의존 해소**: cleanJsonBuilder의 `@/lib/invoiceTableDisplay` runtime
  의존이 `@/common/utils/invoiceTableDisplay` sibling import로 정리됨.
- src/ 운영 코드 잔존 `@/lib/invoiceTableDisplay` / `../lib/invoiceTableDisplay` 0건.
- 9개 lib sibling 파일(structuredTableViewModel/bizNumber/autofillEngine/historyStore/
  imageStore/profiles/restoreProfileStore/groundTruthStore/testsets) 잔류 가드 통과.
- 1E 신규 static check 33개 검증 항목 PASS.
- 1A/1B/1C/1D 검사 4개에 sibling 리스트 정리 + 1D의 normalizer 확장 (cleanJsonBuilder/
  invoiceTableDisplay path/alias collapse).

## 7. common/utils boundary 확인
`src/common/utils/invoiceTableDisplay.ts` 검증 (1E 스크립트):

| 항목 | 결과 |
| --- | --- |
| `from "components/*"` | 없음 |
| `from "react"` / `from "react-dom"` | 없음 |
| `window` / `document` / `localStorage` | 없음 |
| 백업 대비 logic-equivalence | 동일 |
| 6개 필수 export | 전부 보존 |

## 8. cleanJsonBuilder 임시 의존 해소 확인
1D 시점에 남긴 임시 src/lib runtime 의존:

| dep | 1D 시점 | 1E 결과 |
| --- | --- | --- |
| `@/lib/invoiceTableDisplay` (runtime: `INVOICE_TABLE_COL_PRIORITY`, `hasMeaningfulTableValue`, `normalizeTableCell`) | 잔존 | **해소됨** → `@/common/utils/invoiceTableDisplay` |

1E 검사의 `clean_json_builder_no_lib_invoice_table_display_dep`, `clean_json_builder_imports_new_display` 가드가 명시적으로 확인.

이제 cleanJsonBuilder는 src/lib 의존 0건. (1A에서 남긴
ocrResultFormatters의 `@/lib/autofillEngine` type-only 의존은 별개 — 향후 별도
phase로 해소)

## 9. TestWorkspace import path-only 수정 확인
- TestWorkspace.tsx 6줄 1줄만 변경 (`@/lib/invoiceTableDisplay → @/common/utils/invoiceTableDisplay`).
- 1E 검사의 `test_workspace_logic_unchanged_vs_backup` (import path strip 후 logic
  equivalence) PASS — 다른 어떤 코드/JSX/state/handler/test flow 변경도 없음을
  byte-equivalent로 확인.
- `src/components/test/core/*` 미수정.

## 10. Clean JSON fixture 미수정 확인
- `tmp/fixtures/clean_json_v1/` 디렉터리 미손상 (1E check 파일 카운트/총 bytes 스냅샷 가드).
- 실제 contract 동등성은 `check_clean_json_v1_fixtures_js.mjs` 9/9 PASS로 확인
  (1E의 runner path/alias 갱신 후에도 deep equality 통과).
- 본 작업에서 fixture 수정 또는 rebake 미실행.

## 11. static check 결과 (1E 신규 스크립트)
- 파일: `tmp/check_lib_invoice_table_display_common_move_1e.mjs`
- 명령: `node tmp/check_lib_invoice_table_display_common_move_1e.mjs`
- 결과: **PASS** (33/33 checks, skippedBackupChecks=0, residuals=0)

## 12. runner 결과 (26개)

| # | runner | 결과 | 비고 |
| --- | --- | --- | --- |
| 1 | `npm run typecheck` | **PASS** (exit 0) | — |
| 2 | `npm run build` | **PASS** (exit 0) | known noise `ESLint: nextVitals is not iterable` |
| 3 | `node tmp/check_table_view_model_v1_fixtures_js.mjs` | **PASS** (8/8) | exit 0 |
| 4 | `node tmp/check_clean_json_v1_fixtures_js.mjs` | **PASS** (9/9) | exit 0, 1E 경로/alias 갱신 후 통과 |
| 5 | `python tmp/codex_markdown_contract_fixture_lock.py --check --phase post_LIB_INVOICE_TABLE_DISPLAY_COMMON_MOVE_20260522` | **PASS** (6/6) | exit 0 |
| 6 | `node tmp/check_runocr_formdata_keys_2a.mjs` | **PASS_WITH_SKIPPED_BACKUP** | historical 2A backup absent |
| 7 | `node tmp/check_runocr_request_boundary_2b.mjs` | **PASS** | exit 0 |
| 8 | `node tmp/check_runocr_response_mapping_boundary_2c.mjs` | **PASS_WITH_SKIPPED_BACKUP** | historical 2B backup absent |
| 9 | `node tmp/check_runocr_result_layout_boundary_3a.mjs` | **PASS** | exit 0 |
| 10 | `node tmp/check_runocr_doc_comments_3b.mjs` | **PASS_WITH_SKIPPED_BACKUP** | historical 3B backups absent |
| 11 | `node tmp/check_template_workspace_move_4a.mjs` | **PASS_WITH_SKIPPED_BACKUP** | historical 4A backup absent |
| 12 | `node tmp/check_template_editor_ui_move_4b.mjs` | **PASS_WITH_SKIPPED_BACKUP** | historical 4B backups absent |
| 13 | `node tmp/check_template_right_panel_rename_6a.mjs` | **PASS** | exit 0 |
| 14 | `node tmp/check_template_annotator_rename_6b.mjs` | **PASS** | exit 0 |
| 15 | `node tmp/check_ocr_core_types_common_move_5a.mjs` | **PASS** | exit 0 |
| 16 | `node tmp/check_ocr_core_ops_common_move_5b.mjs` | **PASS** | exit 0 |
| 17 | `node tmp/check_ocr_core_table_common_move_5c.mjs` | **PASS** | exit 0 |
| 18 | `node tmp/check_template_export_payload_move_5d.mjs` | **PASS** | exit 0 |
| 19 | `node tmp/check_filedropzone_common_ui_move_5e.mjs` | **PASS** | exit 0 |
| 20 | `node tmp/check_ocr_canvas_pane_common_ui_move_5f.mjs` | **PASS** | exit 0 |
| 21 | `node tmp/check_lib_ocr_result_formatters_common_move_1a.mjs` | **PASS** | sibling 가드 invoiceTableDisplay 제거 |
| 22 | `node tmp/check_lib_invoice_field_labels_common_move_1b.mjs` | **PASS** | sibling 가드 invoiceTableDisplay 제거 |
| 23 | `node tmp/check_lib_markdown_report_builder_common_move_1c.mjs` | **PASS** | sibling 가드 invoiceTableDisplay 제거 |
| 24 | `node tmp/check_lib_clean_json_builder_common_move_1d.mjs` | **PASS** | sibling 가드 + temp dep + runner normalizer 갱신 |
| 25 | `node tmp/check_lib_invoice_table_display_common_move_1e.mjs` | **PASS** | 33/33 |
| 26 | `node tmp/check_validation_baseline_repair_1a.mjs` | **PASS** | exit 0 |

요약: 23개 노드 러너 + 1 파이썬 러너 + typecheck + build 전부 exit 0.
PASS 또는 PASS_WITH_SKIPPED_BACKUP만 존재, FAIL 0건.

## 13. typecheck / build 결과
- `npm run typecheck` → **PASS** (exit 0)
- `npm run build` → **PASS** (exit 0)
- 로그: `ocr-server/logs/codex_FRONTEND_LIB_1E_INVOICE_TABLE_DISPLAY_COMMON_MOVE.out.log`,
  `ocr-server/logs/codex_FRONTEND_LIB_1E_INVOICE_TABLE_DISPLAY_COMMON_MOVE.err.log`

## 14. known stderr noise
- `ESLint: nextVitals is not iterable` — 빌드 exit 0, non-blocking (사전 기재된 known noise).

## 15. 남은 이슈
- 과거 phase(2A/2B/3B/4A/4B)의 logic-equivalence 검사는 backup 파일 부재로
  `PASS_WITH_SKIPPED_BACKUP`로 처리되고 있다. 1E와 무관한 사전 상태.
- `common/utils/ocrResultFormatters.ts`가 여전히 `@/lib/autofillEngine`을
  type-only import (1A 시점부터, 후속 LIB phase에서 해소).
- `OcrResultPanel.tsx:13` doc-comment에 `@/lib/invoiceTableDisplay` 잔존
  (수정 금지 파일, 코드 import 아님, 동작 무영향).
- `src/lib/profiles.ts`의 doc-comment 문자열 `core/types.ts`는 5A 시점부터의
  잔존.

## 16. 다음 작업 제안 (소단위 micro-step 권장)
- `structuredTableViewModel → common/utils` 이동 precheck.
- `bizNumber` 이동은 TestWorkspace 영향 확인 후 진행.
- `autofillEngine → common/utils` 이동 precheck (1A의 남은 type-only 임시
  의존 해소 — runtime 사용처 광범위, 별도 phase 권장).
- `profiles/imageStore/historyStore/restoreProfileStore/groundTruthStore/testsets`는
  별도 precheck 후 진행.
- TestWorkspace 구조 정리는 별도 사용자 확인 후 진행 (이번 1E는 import path-only).
