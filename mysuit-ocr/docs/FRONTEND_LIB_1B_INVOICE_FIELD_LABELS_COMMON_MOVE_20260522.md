# FRONTEND_LIB_1B_INVOICE_FIELD_LABELS_COMMON_MOVE 20260522

## 1. 사용 도구와 모델
- 도구: Claude Code (VSCode extension)
- 모델: Claude Opus 4.7 (1M context)
- 작업 디렉터리: `mysuit-ocr/`

## 2. 작업 목적
src/lib 해체 LIB-1 두 번째 micro-step. `src/lib/invoiceFieldLabels.ts`만
`src/common/utils/invoiceFieldLabels.ts`로 이동하여 UI-only invoice label
dictionary/helper(`INVOICE_FIELD_KO`, `resolveFieldLabel`, `fieldDisplayLabel`)를
common/utils로 이전한다.

- 본문/상수/함수 byte-identical 유지.
- 영향 받은 파일 3곳에서 import path만 보정.
- 1A에서 남긴 `common/utils/ocrResultFormatters.ts`의 `@/lib/invoiceFieldLabels`
  runtime 임시 의존을 `@/common/utils/invoiceFieldLabels`로 해소.
- 다른 lib 파일과 TestWorkspace, 모든 OCR core/template artefact 미수정.
- 잔존 `@/lib/autofillEngine` (type-only) 임시 의존은 후속 LIB phase에서 해소.

## 3. 백업 파일
경로: `mysuit-ocr/backup/lib_invoice_field_labels_20260522_before_FRONTEND_LIB_1B_INVOICE_FIELD_LABELS_COMMON_MOVE/`

| 파일 | bytes |
| --- | --- |
| `invoiceFieldLabels.ts` | 2,196 |
| `ocrResultFormatters.ts` | 4,912 |
| `OcrDocViewer.tsx` | 10,300 |
| `DetailHistoryView.tsx` | 35,386 |

## 4. 이동 파일

| from | to | 방식 | 본문 변경 |
| --- | --- | --- | --- |
| `src/lib/invoiceFieldLabels.ts` | `src/common/utils/invoiceFieldLabels.ts` | `git mv` | 본문 byte-identical. import 0개의 leaf 파일이라 self-import 보정 불필요. |

## 5. 수정 파일 (import path 보정만)

| 파일 | before | after |
| --- | --- | --- |
| `src/common/utils/ocrResultFormatters.ts` | `@/lib/invoiceFieldLabels` | `@/common/utils/invoiceFieldLabels` |
| `src/components/runocr/ui/OcrDocViewer.tsx` | `@/lib/invoiceFieldLabels` | `@/common/utils/invoiceFieldLabels` |
| `src/components/history/DetailHistoryView.tsx` | `@/lib/invoiceFieldLabels` | `@/common/utils/invoiceFieldLabels` |

precheck에는 importer가 2곳으로 적혀 있었으나 실제 importedBy 스캔에서
`DetailHistoryView.tsx`도 포함되어 총 3곳을 보정 (수정 금지 목록에 들어 있지
않은 파일이며 import path 한 줄만 변경).

1A 검사 sibling 가드에서 `invoiceFieldLabels.ts`가 `src/lib/`에 잔류한다는
조건을 1B의 이동 결과에 맞춰 제거 (검사 로직 변경 없음, 리스트 갱신만).

## 6. import 수정 내용
세 파일 모두 `import { resolveFieldLabel } from "@/lib/invoiceFieldLabels"` →
`import { resolveFieldLabel } from "@/common/utils/invoiceFieldLabels"`로 한 줄
교체. 다른 코드/JSX/state/handler 모두 byte-identical.

## 7. common/utils boundary 확인
`src/common/utils/invoiceFieldLabels.ts` 검증 (1B 스크립트):

| 항목 | 결과 |
| --- | --- |
| import 라인 | 0개 (leaf 파일) |
| `from "components/*"` | 없음 |
| `from "react"` / `from "react-dom"` | 없음 |
| `window` / `document` / `localStorage` | 없음 |
| 백업 대비 logic-equivalence | 동일 |
| `export const INVOICE_FIELD_KO` | 보존 |
| `export function resolveFieldLabel` | 보존 |
| `export function fieldDisplayLabel` | 보존 |

## 8. ocrResultFormatters 임시 의존 해소 확인
1A에서 남긴 임시 src/lib 의존 2개 중 runtime 1건 해소:

| dep | 1A 시점 | 1B 결과 |
| --- | --- | --- |
| `@/lib/invoiceFieldLabels` (runtime, `resolveFieldLabel`) | 잔존 | **해소됨** → `@/common/utils/invoiceFieldLabels` |
| `@/lib/autofillEngine` (type-only, `AutofillAction`, `OutputValueSource`) | 잔존 | 잔존 (후속 phase 대상) |

1B 검사의 `formatters_no_lib_labels_runtime_dep`, `formatters_lib_autofill_engine_dep_still_present` 가드가 명시적으로 확인.

## 9. TestWorkspace 미수정 확인
- `src/components/test/TestWorkspace.tsx` 미수정. invoiceFieldLabels를 직접 import한 적이 없음.
- `src/components/test/core/*` 미수정.
- src/ 전역에 잔존 `@/lib/invoiceFieldLabels` / `../lib/invoiceFieldLabels` 운영 import 0건.

## 10. static check 결과 (1B 신규 스크립트)
- 파일: `tmp/check_lib_invoice_field_labels_common_move_1b.mjs`
- 명령: `node tmp/check_lib_invoice_field_labels_common_move_1b.mjs`
- 결과: **PASS** (33/33 checks, skippedBackupChecks=0, residuals=0)

## 11. runner 결과 (23개)

| # | runner | 결과 | 비고 |
| --- | --- | --- | --- |
| 1 | `npm run typecheck` | **PASS** (exit 0) | — |
| 2 | `npm run build` | **PASS** (exit 0) | known noise `ESLint: nextVitals is not iterable` |
| 3 | `node tmp/check_table_view_model_v1_fixtures_js.mjs` | **PASS** (8/8) | exit 0 |
| 4 | `node tmp/check_clean_json_v1_fixtures_js.mjs` | **PASS** (9/9) | exit 0 |
| 5 | `python tmp/codex_markdown_contract_fixture_lock.py --check --phase post_LIB_INVOICE_FIELD_LABELS_COMMON_MOVE_20260522` | **PASS** (6/6) | exit 0 |
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
| 21 | `node tmp/check_lib_ocr_result_formatters_common_move_1a.mjs` | **PASS** | sibling 가드에서 invoiceFieldLabels 제거 (1B로 정당하게 이동) |
| 22 | `node tmp/check_lib_invoice_field_labels_common_move_1b.mjs` | **PASS** | 33/33 |
| 23 | `node tmp/check_validation_baseline_repair_1a.mjs` | **PASS** | exit 0 |

요약: 20개 노드 러너 + 1 파이썬 러너 + typecheck + build 전부 exit 0.
PASS 또는 PASS_WITH_SKIPPED_BACKUP만 존재, FAIL 0건.

## 12. typecheck / build 결과
- `npm run typecheck` → **PASS** (exit 0)
- `npm run build` → **PASS** (exit 0)
- 로그: `ocr-server/logs/codex_FRONTEND_LIB_1B_INVOICE_FIELD_LABELS_COMMON_MOVE.out.log`,
  `ocr-server/logs/codex_FRONTEND_LIB_1B_INVOICE_FIELD_LABELS_COMMON_MOVE.err.log`

## 13. known stderr noise
- `ESLint: nextVitals is not iterable` — 빌드 exit 0, non-blocking (사전 기재된 known noise).

## 14. 남은 이슈
- 과거 phase(2A/2B/3B/4A/4B)의 logic-equivalence 검사는 backup 파일 부재로
  `PASS_WITH_SKIPPED_BACKUP`로 처리되고 있다. 1B와 무관한 사전 상태.
- `common/utils/ocrResultFormatters.ts`가 여전히 `@/lib/autofillEngine`을
  type-only import한다. 후속 LIB phase에서 해소 필요.
- `src/components/runocr/ui/OcrResultPanel.tsx:689` doc-comment에
  `@/lib/ocrResultFormatters` 잔존 (1A 시점부터, 동작 무영향).
- `src/lib/profiles.ts`의 doc-comment 문자열 `core/types.ts`는 5A 시점부터의
  잔존.

## 15. 다음 작업 제안 (소단위 micro-step 권장)
- `markdownReportBuilder.ts → common/utils` 이동 precheck 또는 실제 이동
  (ocrResultFormatters와 짝을 이룬 자연스러운 단계).
- `cleanJsonBuilder.ts → common/utils` 이동 precheck.
- `structuredTableViewModel.ts → common/utils` 이동 precheck.
- `autofillEngine.ts` 이동 precheck — 1A의 type-only 임시 의존 해소 목적이
  있으나 runtime 사용처가 광범위하여 별도 phase로 분리 권장.
- `invoiceTableDisplay/bizNumber` 이동은 TestWorkspace 영향 확인 후 진행.
- `profiles/imageStore/historyStore/restoreProfileStore/groundTruthStore/testsets`는
  별도 precheck 후 진행.
- TestWorkspace 정리는 사용자 확인 후 진행.
