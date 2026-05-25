# FRONTEND_LIB_1C_MARKDOWN_REPORT_BUILDER_COMMON_MOVE 20260522

## 1. 사용 도구와 모델
- 도구: Claude Code (VSCode extension)
- 모델: Claude Opus 4.7 (1M context)
- 작업 디렉터리: `mysuit-ocr/`

## 2. 작업 목적
src/lib 해체 LIB-1 세 번째 micro-step. `src/lib/markdownReportBuilder.ts`만
`src/common/utils/markdownReportBuilder.ts`로 이동하여 Markdown v1 report
builder(`buildMarkdownReport` + `MarkdownReportField` + `BuildMarkdownReportInput`
타입)를 common/utils로 이전한다.

- 본문/시그니처/escape 정책/Markdown v1 contract byte-identical 유지.
- 영향 받은 파일은 import path만 보정 (OcrResultPanel 1줄).
- 새 src/lib 임시 의존 발생 0건 — `@/common/utils/ocrResultFormatters` 의존만
  유지(1A의 결과물 sibling).
- 다른 src/lib 파일(cleanJsonBuilder, structuredTableViewModel, autofillEngine 등)
  미이동.
- TestWorkspace, common/ui, Template, OCR core artefact 전부 미수정.
- Markdown v1 fixture 파일 미수정 — 계약 검증은 markdown contract runner가 별도로 확인.

## 3. 백업 파일
경로: `mysuit-ocr/backup/lib_markdown_report_builder_20260522_before_FRONTEND_LIB_1C_MARKDOWN_REPORT_BUILDER_COMMON_MOVE/`

| 파일 | bytes |
| --- | --- |
| `markdownReportBuilder.ts` | 3,560 |
| `OcrResultPanel.tsx` | 81,686 |

## 4. 이동 파일

| from | to | 방식 | 본문 변경 |
| --- | --- | --- | --- |
| `src/lib/markdownReportBuilder.ts` | `src/common/utils/markdownReportBuilder.ts` | `git mv` | 본문 byte-identical. 유일한 import(`@/common/utils/ocrResultFormatters`)는 `@/` alias라 깊이 변경 영향 없음. |

## 5. 수정 파일 (import path 보정만)

| 파일 | before | after |
| --- | --- | --- |
| `src/components/runocr/ui/OcrResultPanel.tsx` | `@/lib/markdownReportBuilder` | `@/common/utils/markdownReportBuilder` |

OcrResultPanel.tsx 11/687줄에 `@/lib/markdownReportBuilder` 문자열이 doc-comment
로 남아 있음 (Markdown 모드 routing 설명 + 추출 이력 표시 주석). 코드 import 아님,
동작 무영향. 1C 검사는 `stripComments` 후 잔존 검색하여 통과.

기존 1A/1B 검사의 `MARKDOWN_BUILDER` 경로 상수와 sibling 가드를 post-1C 상태에
맞게 보완 (검사 로직 변경 없음, 경로 fallback + sibling 리스트 갱신):
- `tmp/check_lib_ocr_result_formatters_common_move_1a.mjs` — `MARKDOWN_BUILDER`
  자동 탐지, `markdownReportBuilder.ts` sibling 가드 제거.
- `tmp/check_lib_invoice_field_labels_common_move_1b.mjs` — 동일 패턴.

## 6. 핵심 변경 내용
- `common/utils/`에 markdownReportBuilder.ts 추가 (1A/1B에 이은 세 번째 LIB 입주자).
- 새 파일은 `components/*` 무참조, React/React-DOM 무참조,
  `window`/`document`/`localStorage` 무참조, **새 src/lib 임시 의존 0건**
  (1A/1B와 달리 후속 해소 필요 의존이 추가되지 않음).
- `buildMarkdownReport` 함수 + `MarkdownReportField`/`BuildMarkdownReportInput`
  타입 전부 보존.
- 1C 신규 static check 작성 (31개 검증 항목): 11개 lib sibling 잔류 가드,
  common/utils 순수성, 새 lib import 금지 가드, 백업 대비 logic-equivalence,
  Markdown v1 fixture 디렉터리 미손상 스냅샷 등.
- 1A/1B 검사 2개 patch — sibling 리스트에서 markdownReportBuilder 제거 + 경로
  자동 탐지 추가.

## 7. common/utils boundary 확인
`src/common/utils/markdownReportBuilder.ts` 검증 (1C 스크립트):

| 항목 | 결과 |
| --- | --- |
| `from "components/*"` | 없음 |
| `from "react"` / `from "react-dom"` | 없음 |
| `window` / `document` / `localStorage` | 없음 |
| `from "@/lib/*"` (신규 임시 의존) | 없음 |
| `@/common/utils/ocrResultFormatters` 의존 | 있음 (1A 결과물 sibling) |
| 백업 대비 logic-equivalence | 동일 |
| `export function buildMarkdownReport` | 보존 |
| `export type MarkdownReportField` | 보존 |
| `export type BuildMarkdownReportInput` | 보존 |

## 8. markdown fixture 미수정 확인
- `tmp/fixtures/markdown_v1/` 디렉터리 미손상 (1C check가 파일 카운트 + 총
  bytes 스냅샷으로 확인).
- 실제 contract 동등성은 markdown_contract_fixture_lock runner가 6/6 PASS로
  확인 (LF policy 포함, 출력 byte 일치).
- 본 작업에서 fixture를 직접 수정한 적 없음.

## 9. TestWorkspace 미수정 확인
- `src/components/test/TestWorkspace.tsx` 미수정. markdownReportBuilder를 직접
  import한 적이 없음.
- `src/components/test/core/*` 미수정.
- src/ 운영 코드에 잔존 `@/lib/markdownReportBuilder` / `../lib/markdownReportBuilder` 0건.

## 10. static check 결과 (1C 신규 스크립트)
- 파일: `tmp/check_lib_markdown_report_builder_common_move_1c.mjs`
- 명령: `node tmp/check_lib_markdown_report_builder_common_move_1c.mjs`
- 결과: **PASS** (31/31 checks, skippedBackupChecks=0, residuals=0)

## 11. runner 결과 (24개)

| # | runner | 결과 | 비고 |
| --- | --- | --- | --- |
| 1 | `npm run typecheck` | **PASS** (exit 0) | — |
| 2 | `npm run build` | **PASS** (exit 0) | known noise `ESLint: nextVitals is not iterable` |
| 3 | `node tmp/check_table_view_model_v1_fixtures_js.mjs` | **PASS** (8/8) | exit 0 |
| 4 | `node tmp/check_clean_json_v1_fixtures_js.mjs` | **PASS** (9/9) | exit 0 |
| 5 | `python tmp/codex_markdown_contract_fixture_lock.py --check --phase post_LIB_MARKDOWN_REPORT_BUILDER_COMMON_MOVE_20260522` | **PASS** (6/6) | exit 0 |
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
| 21 | `node tmp/check_lib_ocr_result_formatters_common_move_1a.mjs` | **PASS** | sibling 가드/경로 자동 탐지 patch 적용 |
| 22 | `node tmp/check_lib_invoice_field_labels_common_move_1b.mjs` | **PASS** | sibling 가드/경로 자동 탐지 patch 적용 |
| 23 | `node tmp/check_lib_markdown_report_builder_common_move_1c.mjs` | **PASS** | 31/31 |
| 24 | `node tmp/check_validation_baseline_repair_1a.mjs` | **PASS** | exit 0 |

요약: 21개 노드 러너 + 1 파이썬 러너 + typecheck + build 전부 exit 0.
PASS 또는 PASS_WITH_SKIPPED_BACKUP만 존재, FAIL 0건.

## 12. typecheck / build 결과
- `npm run typecheck` → **PASS** (exit 0)
- `npm run build` → **PASS** (exit 0)
- 로그: `ocr-server/logs/codex_FRONTEND_LIB_1C_MARKDOWN_REPORT_BUILDER_COMMON_MOVE.out.log`,
  `ocr-server/logs/codex_FRONTEND_LIB_1C_MARKDOWN_REPORT_BUILDER_COMMON_MOVE.err.log`

## 13. known stderr noise
- `ESLint: nextVitals is not iterable` — 빌드 exit 0, non-blocking (사전 기재된 known noise).

## 14. 남은 이슈
- 과거 phase(2A/2B/3B/4A/4B)의 logic-equivalence 검사는 backup 파일 부재로
  `PASS_WITH_SKIPPED_BACKUP`로 처리되고 있다. 1C와 무관한 사전 상태.
- `common/utils/ocrResultFormatters.ts`가 여전히 `@/lib/autofillEngine`을
  type-only import한다 (1A 시점부터의 임시 의존, 후속 LIB phase에서 해소).
- `src/components/runocr/ui/OcrResultPanel.tsx`의 doc-comment 2곳에
  `@/lib/markdownReportBuilder` 문자열 잔존 (1C 시점부터, 동작 무영향).
- `src/lib/profiles.ts`의 doc-comment 문자열 `core/types.ts`는 5A 시점부터의
  잔존.

## 15. 다음 작업 제안 (소단위 micro-step 권장)
- `cleanJsonBuilder.ts → common/utils` 이동 precheck (markdown과 짝을 이루는
  natural 다음 단계).
- `structuredTableViewModel.ts → common/utils` 이동 precheck.
- `autofillEngine.ts` 이동 precheck — 1A의 type-only 임시 의존 해소 목적이
  있으나 runtime 사용처가 광범위하여 별도 phase로 분리 권장.
- `invoiceTableDisplay/bizNumber` 이동은 TestWorkspace 영향 확인 후 진행.
- `profiles/imageStore/historyStore/restoreProfileStore/groundTruthStore/testsets`는
  별도 precheck 후 진행.
- TestWorkspace 정리는 사용자 확인 후 진행.
