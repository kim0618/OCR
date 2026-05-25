# FRONTEND_LIB_1D_CLEAN_JSON_BUILDER_COMMON_MOVE 20260522

## 1. 사용 도구와 모델
- 도구: Claude Code (VSCode extension)
- 모델: Claude Opus 4.7 (1M context)
- 작업 디렉터리: `mysuit-ocr/`

## 2. 작업 목적
src/lib 해체 LIB-1 네 번째 micro-step. `src/lib/cleanJsonBuilder.ts`만
`src/common/utils/cleanJsonBuilder.ts`로 이동하여 Clean JSON v1 builder
(`buildCleanJsonResult` + 관련 타입)를 common/utils로 이전한다.

- 본문/시그니처/Clean JSON v1 contract byte-identical 유지.
- 영향 받은 파일은 import path만 보정: OcrResultPanel 1줄 + Clean JSON v1
  fixture runner의 하드코딩 경로 2곳.
- Clean JSON fixture 파일 미수정, fixture rebake 미실행.
- 새 builder가 `@/lib/invoiceTableDisplay`에 임시 의존하는 것은 허용
  (components 의존이 아니므로 boundary 위반 아님, 후속 LIB phase에서 해소).
- structuredTableViewModel/invoiceTableDisplay/autofillEngine 등 다른 lib
  파일은 이번 작업에서 이동하지 않는다.
- TestWorkspace, common/ui, Template, OCR core artefact 전부 미수정.

## 3. 백업 파일
경로: `mysuit-ocr/backup/lib_clean_json_builder_20260522_before_FRONTEND_LIB_1D_CLEAN_JSON_BUILDER_COMMON_MOVE/`

| 파일 | bytes |
| --- | --- |
| `cleanJsonBuilder.ts` | 5,919 |
| `OcrResultPanel.tsx` | 81,695 |
| `check_clean_json_v1_fixtures_js.mjs` | 17,892 |

## 4. 이동 파일

| from | to | 방식 | 본문 변경 |
| --- | --- | --- | --- |
| `src/lib/cleanJsonBuilder.ts` | `src/common/utils/cleanJsonBuilder.ts` | `git mv` | 본문 byte-identical. 유일한 의존(`@/lib/invoiceTableDisplay`)은 `@/` alias라 깊이 변경 영향 없음. |

## 5. 수정 파일 (import path 보정만)

| 파일 | before | after |
| --- | --- | --- |
| `src/components/runocr/ui/OcrResultPanel.tsx` | `@/lib/cleanJsonBuilder` | `@/common/utils/cleanJsonBuilder` |
| `tmp/check_clean_json_v1_fixtures_js.mjs` (loader path) | `path.join(ROOT, "src", "lib", "cleanJsonBuilder.ts")` | `path.join(ROOT, "src", "common", "utils", "cleanJsonBuilder.ts")` |
| `tmp/check_clean_json_v1_fixtures_js.mjs` (purity check) | `path.join(ROOT, "src", "lib", "cleanJsonBuilder.ts")` | `path.join(ROOT, "src", "common", "utils", "cleanJsonBuilder.ts")` |

OcrResultPanel.tsx 10/780줄에 `@/lib/cleanJsonBuilder` 문자열이 doc-comment로
남아 있음 (Clean JSON routing 설명 + 추출 이력 표시 주석). 코드 import 아님,
동작 무영향. 1D 검사는 `stripComments` 후 잔존 검색하여 통과.

기존 1A/1B/1C 검사 sibling 가드에서 `cleanJsonBuilder.ts`를 제거 (검사 로직
변경 없음, 리스트 갱신만).

## 6. 핵심 변경 내용
- `common/utils/`에 cleanJsonBuilder.ts 추가 (LIB 입주 5번째).
- 새 파일은 `components/*` / React / React-DOM / window / document / localStorage /
  sessionStorage / fetch / XMLHttpRequest 모두 무참조.
- `buildCleanJsonResult` 함수 보존.
- Clean JSON v1 fixture runner의 하드코딩된 경로 2곳(loader + sourcePurityCheck)
  모두 새 위치로 갱신. fixture 파일 자체는 미수정.
- 1D 신규 static check 작성 (28개 검증 항목): 10개 lib sibling 잔류 가드,
  common/utils 순수성, runner 경로 갱신 검증, fixture 디렉터리 미손상 스냅샷,
  임시 `@/lib/invoiceTableDisplay` 의존 명시적 기록 등.
- 1A/1B/1C 검사 sibling 리스트에서 cleanJsonBuilder 제거.

## 7. common/utils boundary 확인
`src/common/utils/cleanJsonBuilder.ts` 검증 (1D 스크립트):

| 항목 | 결과 |
| --- | --- |
| `from "components/*"` | 없음 |
| `from "react"` / `from "react-dom"` | 없음 |
| `window` / `document` / `localStorage` / `sessionStorage` / `fetch(` / `XMLHttpRequest` | 모두 없음 |
| 백업 대비 logic-equivalence | 동일 |
| `export function buildCleanJsonResult` | 보존 |
| 의존 module | `@/lib/invoiceTableDisplay` (임시) |

## 8. 임시 @/lib/invoiceTableDisplay 의존 기록
새 파일이 다음 모듈을 여전히 src/lib에서 import한다:

| import | kind | 후속 처리 |
| --- | --- | --- |
| `import { INVOICE_TABLE_COL_PRIORITY, hasMeaningfulTableValue, normalizeTableCell } from "@/lib/invoiceTableDisplay"` | runtime | `invoiceTableDisplay.ts → common/utils` 이동 별도 phase에서 해소 |

→ `components/*` 의존이 아니므로 common/utils invariant 위반이 아님. 본 phase의
범위 내에서 의도적으로 남긴 임시 상태. 1D 검사의 `new_builder_temp_lib_deps_recorded`
가드가 명시적으로 확인.

## 9. Clean JSON fixture 미수정 확인
- `tmp/fixtures/clean_json_v1/` 디렉터리 미손상 (1D check가 파일 카운트 + 총
  bytes 스냅샷으로 확인).
- 실제 contract 동등성은 `check_clean_json_v1_fixtures_js.mjs` 9/9 PASS로 확인
  (Clean JSON v1 deep equality).
- 본 작업에서 fixture를 직접 수정하거나 rebake한 적 없음.

## 10. TestWorkspace 미수정 확인
- `src/components/test/TestWorkspace.tsx` 미수정. cleanJsonBuilder를 직접
  import한 적이 없음.
- `src/components/test/core/*` 미수정.
- src/ 운영 코드에 잔존 `@/lib/cleanJsonBuilder` / `../lib/cleanJsonBuilder` 0건.

## 11. static check 결과 (1D 신규 스크립트)
- 파일: `tmp/check_lib_clean_json_builder_common_move_1d.mjs`
- 명령: `node tmp/check_lib_clean_json_builder_common_move_1d.mjs`
- 결과: **PASS** (28/28 checks, skippedBackupChecks=0, residuals=0)

## 12. runner 결과 (25개)

| # | runner | 결과 | 비고 |
| --- | --- | --- | --- |
| 1 | `npm run typecheck` | **PASS** (exit 0) | — |
| 2 | `npm run build` | **PASS** (exit 0) | known noise `ESLint: nextVitals is not iterable` |
| 3 | `node tmp/check_table_view_model_v1_fixtures_js.mjs` | **PASS** (8/8) | exit 0 |
| 4 | `node tmp/check_clean_json_v1_fixtures_js.mjs` | **PASS** (9/9) | exit 0 — loader 경로 1D 갱신 후 통과 |
| 5 | `python tmp/codex_markdown_contract_fixture_lock.py --check --phase post_LIB_CLEAN_JSON_BUILDER_COMMON_MOVE_20260522` | **PASS** (6/6) | exit 0 |
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
| 21 | `node tmp/check_lib_ocr_result_formatters_common_move_1a.mjs` | **PASS** | sibling 가드 cleanJsonBuilder 제거 |
| 22 | `node tmp/check_lib_invoice_field_labels_common_move_1b.mjs` | **PASS** | sibling 가드 cleanJsonBuilder 제거 |
| 23 | `node tmp/check_lib_markdown_report_builder_common_move_1c.mjs` | **PASS** | sibling 가드 cleanJsonBuilder 제거 |
| 24 | `node tmp/check_lib_clean_json_builder_common_move_1d.mjs` | **PASS** | 28/28 |
| 25 | `node tmp/check_validation_baseline_repair_1a.mjs` | **PASS** | exit 0 |

요약: 22개 노드 러너 + 1 파이썬 러너 + typecheck + build 전부 exit 0.
PASS 또는 PASS_WITH_SKIPPED_BACKUP만 존재, FAIL 0건.

## 13. typecheck / build 결과
- `npm run typecheck` → **PASS** (exit 0)
- `npm run build` → **PASS** (exit 0)
- 로그: `ocr-server/logs/codex_FRONTEND_LIB_1D_CLEAN_JSON_BUILDER_COMMON_MOVE.out.log`,
  `ocr-server/logs/codex_FRONTEND_LIB_1D_CLEAN_JSON_BUILDER_COMMON_MOVE.err.log`

## 14. known stderr noise
- `ESLint: nextVitals is not iterable` — 빌드 exit 0, non-blocking (사전 기재된 known noise).

## 15. 남은 이슈
- 과거 phase(2A/2B/3B/4A/4B)의 logic-equivalence 검사는 backup 파일 부재로
  `PASS_WITH_SKIPPED_BACKUP`로 처리되고 있다. 1D와 무관한 사전 상태.
- `common/utils/cleanJsonBuilder.ts`가 여전히 `@/lib/invoiceTableDisplay`를
  runtime import. 후속 LIB phase에서 invoiceTableDisplay 이동으로 해소 필요.
- `common/utils/ocrResultFormatters.ts`가 여전히 `@/lib/autofillEngine`을
  type-only import (1A 시점부터의 임시 의존, 후속 LIB phase에서 해소).
- `OcrResultPanel.tsx` doc-comment 2곳(10/780줄)에 `@/lib/cleanJsonBuilder`
  잔존 (수정 금지 파일, 코드 import 아님, 동작 무영향).
- `src/lib/profiles.ts`의 doc-comment 문자열 `core/types.ts`는 5A 시점부터의
  잔존.

## 16. 다음 작업 제안 (소단위 micro-step 권장)
- `invoiceTableDisplay → common/utils` 이동 precheck (1D의 runtime 임시 의존
  해소 후보).
- `structuredTableViewModel → common/utils` 이동 precheck.
- `bizNumber` 이동은 TestWorkspace 영향 확인 후 진행.
- `autofillEngine → common/utils` 이동 precheck (1A의 type-only 임시 의존
  해소 — runtime 사용처가 광범위하여 별도 phase로 분리 권장).
- `profiles/imageStore/historyStore/restoreProfileStore/groundTruthStore/testsets`는
  별도 precheck 후 진행.
- TestWorkspace 정리는 사용자 확인 후 진행.
