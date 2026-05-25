# FRONTEND_LIB_1F_STRUCTURED_TABLE_VIEW_MODEL_COMMON_MOVE 20260522

## 1. 사용 도구와 모델
- 도구: Claude Code (VSCode extension)
- 모델: Claude Opus 4.7 (1M context)
- 작업 디렉터리: `mysuit-ocr/`

## 2. 작업 목적
src/lib 해체 LIB-1 여섯 번째 micro-step. `src/lib/structuredTableViewModel.ts`만
`src/common/utils/structuredTableViewModel.ts`로 이동한다.
caller가 넘긴 rows와 displayCols를 UI-agnostic table view model로 변환하는
순수 helper(`buildStructuredTableViewModel` + 관련 타입)를 common/utils로 이전.

- 본문/시그니처 byte-identical 유지.
- 영향 받은 파일은 import path만 보정 (OcrResultPanel 1줄 + table_view_model
  runner HELPER_SRC 1줄).
- table_view_model fixture 미수정 + rebake 미실행.
- structuredTableViewModel은 invoiceTableDisplay를 직접 import하지 않으며 새
  src/lib 임시 의존도 생기지 않음.
- invoiceTableDisplay/bizNumber/autofillEngine 등 다른 lib 파일 미이동.
- TestWorkspace, test/core, History, Template, common/ui 등 전부 미수정.

## 3. 백업 파일
경로: `mysuit-ocr/backup/lib_structured_table_view_model_20260522_before_FRONTEND_LIB_1F_STRUCTURED_TABLE_VIEW_MODEL_COMMON_MOVE/`

| 파일 | bytes |
| --- | --- |
| `structuredTableViewModel.ts` | 4,843 |
| `OcrResultPanel.tsx` | 81,713 |
| `check_table_view_model_v1_fixtures_js.mjs` | 12,242 |

## 4. 이동 파일

| from | to | 방식 | 본문 변경 |
| --- | --- | --- | --- |
| `src/lib/structuredTableViewModel.ts` | `src/common/utils/structuredTableViewModel.ts` | `git mv` | 본문 byte-identical. 내부에 @/ import 0건 — 깊이 변경 영향 없음. |

## 5. 수정 파일 (import path 보정만)

| 파일 | before | after |
| --- | --- | --- |
| `src/components/runocr/ui/OcrResultPanel.tsx` | `@/lib/structuredTableViewModel` | `@/common/utils/structuredTableViewModel` |
| `tmp/check_table_view_model_v1_fixtures_js.mjs` (HELPER_SRC) | `path.join(ROOT, "src", "lib", "structuredTableViewModel.ts")` | `path.join(ROOT, "src", "common", "utils", "structuredTableViewModel.ts")` |

OcrResultPanel.tsx 12줄에 `@/lib/structuredTableViewModel` 문자열이 doc-comment로
남아 있음. 코드 import 아님, 동작 무영향. 1F 검사는 `stripComments` 후 잔존
검색하여 통과.

기존 1A/1B/1C/1D/1E 검사 sibling 가드에서 `structuredTableViewModel.ts` 제거
(검사 로직 변경 없음, 리스트 갱신만).

## 6. 핵심 변경 내용
- `common/utils/`에 structuredTableViewModel.ts 추가 (LIB 입주 8번째).
- 새 파일은 `components/*` / React / React-DOM / window / document /
  localStorage / `@/lib/*` / `invoiceTableDisplay` 모두 무참조.
- 1F 신규 static check 22개 검증 항목 PASS.
- 1A/1B/1C/1D/1E sibling 가드 5개 정리.
- src/ 운영 코드 잔존 `@/lib/structuredTableViewModel` /
  `../lib/structuredTableViewModel` 0건.

## 7. common/utils boundary 확인
`src/common/utils/structuredTableViewModel.ts` 검증 (1F 스크립트):

| 항목 | 결과 |
| --- | --- |
| `from "components/*"` | 없음 |
| `from "react"` / `from "react-dom"` | 없음 |
| `window` / `document` / `localStorage` | 없음 |
| `from "@/lib/*"` | 없음 (caller가 displayCols 주입) |
| `invoiceTableDisplay` 참조 | 없음 |
| 백업 대비 logic-equivalence | 동일 |
| `export function buildStructuredTableViewModel` | 보존 |

## 8. table_view_model fixture 미수정 확인
- `tmp/fixtures/table_view_model_v1/` 디렉터리 미손상 (1F check가 파일 카운트
  + 총 bytes 스냅샷으로 확인).
- 실제 contract 동등성은 `check_table_view_model_v1_fixtures_js.mjs` 8/8 PASS로
  확인 (1F HELPER_SRC 갱신 후에도 통과).
- 본 작업에서 fixture 수정 또는 rebake 미실행.

## 9. TestWorkspace 미수정 확인
- `src/components/test/TestWorkspace.tsx` 미수정. structuredTableViewModel을
  직접 import한 적이 없음.
- `src/components/test/core/*` 미수정.
- History/Template/common/ui 전부 미수정.

## 10. static check 결과 (1F 신규 스크립트)
- 파일: `tmp/check_lib_structured_table_view_model_common_move_1f.mjs`
- 명령: `node tmp/check_lib_structured_table_view_model_common_move_1f.mjs`
- 결과: **PASS** (22/22 checks, skippedBackupChecks=0, residuals=0)

## 11. runner 결과 (27개)

| # | runner | 결과 | 비고 |
| --- | --- | --- | --- |
| 1 | `npm run typecheck` | **PASS** (exit 0) | — |
| 2 | `npm run build` | **PASS** (exit 0) | known noise `ESLint: nextVitals is not iterable` |
| 3 | `node tmp/check_table_view_model_v1_fixtures_js.mjs` | **PASS** (8/8) | exit 0, 1F HELPER_SRC 갱신 후 통과 |
| 4 | `node tmp/check_clean_json_v1_fixtures_js.mjs` | **PASS** (9/9) | exit 0 |
| 5 | `python tmp/codex_markdown_contract_fixture_lock.py --check --phase post_LIB_STRUCTURED_TABLE_VIEW_MODEL_COMMON_MOVE_20260522` | **PASS** (6/6) | exit 0 |
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
| 21 | `node tmp/check_lib_ocr_result_formatters_common_move_1a.mjs` | **PASS** | sibling 가드 structuredTableViewModel 제거 |
| 22 | `node tmp/check_lib_invoice_field_labels_common_move_1b.mjs` | **PASS** | sibling 가드 structuredTableViewModel 제거 |
| 23 | `node tmp/check_lib_markdown_report_builder_common_move_1c.mjs` | **PASS** | sibling 가드 structuredTableViewModel 제거 |
| 24 | `node tmp/check_lib_clean_json_builder_common_move_1d.mjs` | **PASS** | sibling 가드 structuredTableViewModel 제거 |
| 25 | `node tmp/check_lib_invoice_table_display_common_move_1e.mjs` | **PASS** | sibling 가드 structuredTableViewModel 제거 |
| 26 | `node tmp/check_lib_structured_table_view_model_common_move_1f.mjs` | **PASS** | 22/22 |
| 27 | `node tmp/check_validation_baseline_repair_1a.mjs` | **PASS** | exit 0 |

요약: 24개 노드 러너 + 1 파이썬 러너 + typecheck + build 전부 exit 0.
PASS 또는 PASS_WITH_SKIPPED_BACKUP만 존재, FAIL 0건.

## 12. typecheck / build 결과
- `npm run typecheck` → **PASS** (exit 0)
- `npm run build` → **PASS** (exit 0)
- 로그: `ocr-server/logs/codex_FRONTEND_LIB_1F_STRUCTURED_TABLE_VIEW_MODEL_COMMON_MOVE.out.log`,
  `ocr-server/logs/codex_FRONTEND_LIB_1F_STRUCTURED_TABLE_VIEW_MODEL_COMMON_MOVE.err.log`

## 13. known stderr noise
- `ESLint: nextVitals is not iterable` — 빌드 exit 0, non-blocking (사전 기재된 known noise).

## 14. 남은 이슈
- 과거 phase(2A/2B/3B/4A/4B)의 logic-equivalence 검사는 backup 파일 부재로
  `PASS_WITH_SKIPPED_BACKUP`로 처리되고 있다. 1F와 무관한 사전 상태.
- `common/utils/ocrResultFormatters.ts`가 여전히 `@/lib/autofillEngine`을
  type-only import (1A 시점부터, 후속 LIB phase에서 해소).
- `OcrResultPanel.tsx:12` doc-comment에 `@/lib/structuredTableViewModel` 잔존
  (수정 금지 파일, 코드 import 아님, 동작 무영향).
- `src/lib/profiles.ts`의 doc-comment 문자열 `core/types.ts`는 5A 시점부터의
  잔존.

## 15. 다음 작업 제안 (소단위 micro-step 권장)
- `bizNumber` 이동은 TestWorkspace 영향 확인 후 진행.
- `autofillEngine → common/utils` 이동 precheck (1A의 남은 type-only 임시
  의존 해소 — runtime 사용처 광범위, 별도 phase 권장).
- `profiles/imageStore/historyStore/restoreProfileStore/groundTruthStore/testsets`는
  별도 precheck 후 진행.
- components/common 잔여(AppProviders/RequireLogin) 정리 precheck.
- history/restore 구조 정리 precheck.
- TestWorkspace 구조 정리는 별도 사용자 확인 후 진행.
