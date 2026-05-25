# FRONTEND_LIB_1A_OCR_RESULT_FORMATTERS_COMMON_MOVE 20260522

## 1. 사용 도구와 모델
- 도구: Claude Code (VSCode extension)
- 모델: Claude Opus 4.7 (1M context)
- 작업 디렉터리: `mysuit-ocr/`

## 2. 작업 목적
src/lib 해체 LIB-1 common formatter/display utils 이동의 첫 micro-step.
`src/lib/ocrResultFormatters.ts`만 `src/common/utils/ocrResultFormatters.ts`로
이동하여 순수 formatter(`fieldLabel`, `fieldLabelFull`, `isAmountLikeField`,
`getAdoptionLabel`, `parseTableField` 및 관련 타입)를 common/utils로 이전한다.

- 함수 이름/시그니처/본문 byte-identical 유지.
- 영향 받은 파일은 import path만 보정 (OcrResultPanel 1줄, markdownReportBuilder 1줄).
- 새 파일이 `@/lib/autofillEngine`(type-only)와 `@/lib/invoiceFieldLabels`를
  여전히 참조 — 본 작업에서 허용하는 임시 src/lib 의존이며, 후속 LIB 단계에서
  해소.
- `markdownReportBuilder`, `cleanJsonBuilder`, `invoiceFieldLabels`,
  `autofillEngine` 등 다른 lib 파일은 이번 작업에서 이동하지 않는다.
- TestWorkspace, common/ui/*, Template, runocr의 다른 파일 모두 미수정.

## 3. 백업 파일
경로: `mysuit-ocr/backup/lib_ocr_result_formatters_20260522_before_FRONTEND_LIB_1A_OCR_RESULT_FORMATTERS_COMMON_MOVE/`

| 파일 | bytes |
| --- | --- |
| `ocrResultFormatters.ts` | 4,912 |
| `OcrResultPanel.tsx` | 81,677 |
| `markdownReportBuilder.ts` | 3,551 |

## 4. 이동 파일

| from | to | 방식 | 본문 변경 |
| --- | --- | --- | --- |
| `src/lib/ocrResultFormatters.ts` | `src/common/utils/ocrResultFormatters.ts` | `git mv` | 본문 byte-identical. 내부 self-import는 `@/lib/autofillEngine`, `@/lib/invoiceFieldLabels` 모두 `@/` 절대 alias라 깊이 변경 영향 없음. |

## 5. 수정 파일 (import path 보정만)

| 파일 | before | after |
| --- | --- | --- |
| `src/components/runocr/ui/OcrResultPanel.tsx` | `@/lib/ocrResultFormatters` | `@/common/utils/ocrResultFormatters` |
| `src/lib/markdownReportBuilder.ts` | `@/lib/ocrResultFormatters` | `@/common/utils/ocrResultFormatters` |

OcrResultPanel 689줄에 `@/lib/ocrResultFormatters` 문자열이 도큐멘트 주석으로
남아 있다(`// @/lib/ocrResultFormatters and are reused by ...`). 본 파일은
import path만 변경 허용이고 주석은 코드 동작에 영향 없음. 1A 검사는
`stripComments` 후 잔존 검색하여 통과.

## 6. 핵심 변경 내용
- `src/common/utils/`에 ocrResultFormatters.ts 추가 (5B/5C의 ocrCanvasOps,
  ocrTableRegion에 이어 세 번째 입주자).
- 새 파일은 `components/*` 미참조, React/React-DOM/`window`/`document`/
  `localStorage` 무참조, side effect 없음.
- 함수 5개(`fieldLabel`, `fieldLabelFull`, `isAmountLikeField`,
  `getAdoptionLabel`, `parseTableField`) + 타입 4개(`OcrFormatterField`,
  `OcrAdoptionLabel`, `TableCell`, `ParsedTableField`) 전부 보존.
- 1A 신규 static check 작성 (31개 검증 항목): 13개 lib sibling 파일 잔류
  존재 가드, common/utils 순수성 검증, 임시 src/lib 의존(`@/lib/autofillEngine`,
  `@/lib/invoiceFieldLabels`) 명시적 기록, 잔존 import 스캔, importers
  logic-equivalence 비교.
- 기존 21개 검사 패치 0건. 1A는 path/identifier collapse 없이 자연 흡수.

## 7. common/utils boundary 확인
`src/common/utils/ocrResultFormatters.ts` 검증 (1A 스크립트):

| 항목 | 결과 |
| --- | --- |
| `from "components/*"` import | 없음 |
| `from "react"` / `from "react-dom"` | 없음 |
| `window` / `document` / `localStorage` | 없음 |
| 백업 대비 logic-equivalence | 동일 (path 변경 0건) |
| 필수 export 함수 5개 | 전부 보존 |
| 필수 export 타입 4개 | 전부 보존 |
| 의존 module | `@/lib/autofillEngine` (type-only), `@/lib/invoiceFieldLabels` |

## 8. 임시 src/lib 의존 기록
새 파일이 다음 두 모듈을 여전히 src/lib에서 import한다 (변경 없음):

| import | kind | 후속 처리 |
| --- | --- | --- |
| `import type { AutofillAction, OutputValueSource } from "@/lib/autofillEngine"` | type-only | autofillEngine common/utils 이동 별도 phase에서 해소 |
| `import { resolveFieldLabel } from "@/lib/invoiceFieldLabels"` | runtime | invoiceFieldLabels common/utils 이동 별도 phase에서 해소 |

→ `components/*` 의존은 아니므로 common/utils invariant 위반이 아님. 본 phase의
범위 내에서 의도적으로 남긴 임시 상태.

## 9. TestWorkspace 미수정 확인
- `src/components/test/TestWorkspace.tsx` 미수정. ocrResultFormatters를 직접
  import한 적이 없으며 본 작업으로도 영향 없음.
- `src/components/test/core/*` 미수정.
- src/ 전역에 잔존 `@/lib/ocrResultFormatters` / `../lib/ocrResultFormatters` /
  `../../lib/ocrResultFormatters` 운영 import 0건 (주석 1건 제외).

## 10. static check 결과 (1A 신규 스크립트)
- 파일: `tmp/check_lib_ocr_result_formatters_common_move_1a.mjs`
- 명령: `node tmp/check_lib_ocr_result_formatters_common_move_1a.mjs`
- 결과: **PASS** (31/31 checks, skippedBackupChecks=0, residuals=0)

## 11. runner 결과 (22개)

| # | runner | 결과 | 비고 |
| --- | --- | --- | --- |
| 1 | `npm run typecheck` | **PASS** (exit 0) | — |
| 2 | `npm run build` | **PASS** (exit 0) | known noise `ESLint: nextVitals is not iterable` |
| 3 | `node tmp/check_table_view_model_v1_fixtures_js.mjs` | **PASS** (8/8) | exit 0 |
| 4 | `node tmp/check_clean_json_v1_fixtures_js.mjs` | **PASS** (9/9) | exit 0 |
| 5 | `python tmp/codex_markdown_contract_fixture_lock.py --check --phase post_LIB_OCR_RESULT_FORMATTERS_COMMON_MOVE_20260522` | **PASS** (6/6) | exit 0 |
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
| 21 | `node tmp/check_lib_ocr_result_formatters_common_move_1a.mjs` | **PASS** | 31/31 |
| 22 | `node tmp/check_validation_baseline_repair_1a.mjs` | **PASS** | exit 0 |

요약: 19개 노드 러너 + 1 파이썬 러너 + typecheck + build 전부 exit 0. PASS 또는
PASS_WITH_SKIPPED_BACKUP만 존재, FAIL 0건. 본 1A는 기존 21개 검사 어떤 것도
patch가 필요하지 않았다 (이전 phase 검사들은 ocrResultFormatters를 참조하지
않기 때문).

## 12. typecheck / build 결과
- `npm run typecheck` → **PASS** (exit 0)
- `npm run build` → **PASS** (exit 0)
- 로그: `ocr-server/logs/codex_FRONTEND_LIB_1A_OCR_RESULT_FORMATTERS_COMMON_MOVE.out.log`,
  `ocr-server/logs/codex_FRONTEND_LIB_1A_OCR_RESULT_FORMATTERS_COMMON_MOVE.err.log`

## 13. known stderr noise
- `ESLint: nextVitals is not iterable` — 빌드 exit 0, non-blocking (사전 기재된 known noise).

## 14. 남은 이슈
- 과거 phase(2A/2B/3B/4A/4B)의 logic-equivalence 검사는 backup 파일 부재로
  `PASS_WITH_SKIPPED_BACKUP`로 처리되고 있다. 1A와 무관한 사전 상태.
- `common/utils/ocrResultFormatters.ts`가 여전히 `@/lib/autofillEngine`,
  `@/lib/invoiceFieldLabels`를 참조하는 임시 의존이 존재. components/* 의존이
  아니므로 boundary 위반은 아니지만, 후속 LIB phase에서 해소가 필요.
- `src/components/runocr/ui/OcrResultPanel.tsx` 689줄에 `@/lib/ocrResultFormatters`
  문자열이 주석으로 남아 있다 (코드 import 아님, 동작 무영향).
- `src/lib/profiles.ts`의 doc-comment 문자열 `core/types.ts`는 5A 시점부터의
  잔존.

## 15. 다음 작업 제안 (소단위 micro-step 권장)
- `markdownReportBuilder.ts → common/utils` 이동 precheck 또는 실제 이동
  (ocrResultFormatters와 짝을 이룬 자연스러운 다음 단계).
- `cleanJsonBuilder.ts → common/utils` 이동 precheck.
- `structuredTableViewModel.ts → common/utils` 이동 precheck.
- `invoiceFieldLabels.ts → common/utils` 이동 precheck (ocrResultFormatters의
  임시 src/lib 의존 해소 후보).
- `autofillEngine.ts` 이동 precheck (ocrResultFormatters의 type-only 의존
  해소 후보; runtime 사용처가 많아 별도 phase로 분리 필요).
- `invoiceTableDisplay/bizNumber` 이동은 TestWorkspace 영향 확인 후 진행.
- `profiles/imageStore/historyStore/restoreProfileStore/groundTruthStore/testsets`는
  별도 precheck 후 진행.
- TestWorkspace 정리는 사용자 확인 후 진행.
