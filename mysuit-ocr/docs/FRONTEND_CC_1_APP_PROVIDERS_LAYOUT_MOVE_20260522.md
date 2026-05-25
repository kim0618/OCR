# FRONTEND_CC_1_APP_PROVIDERS_LAYOUT_MOVE 20260522

## 1. 사용 도구와 모델
- 도구: Claude Code (VSCode extension)
- 모델: Claude Opus 4.7 (1M context)
- 작업 디렉터리: `mysuit-ocr/`

## 2. 작업 목적
src/components/common 잔여 정리(CC) 첫 micro-step. `src/components/common/AppProviders.tsx`만
`src/components/layout/AppProviders.tsx`로 이동하여 전역 UI context/provider
(`useUi`, loading overlay, alert/confirm modal)를 app shell 도메인으로 정리.

- 본문/JSX/context provider 구조/useUi 시그니처 byte-identical 유지.
- 영향 받은 파일은 import path만 보정 (11곳).
- TestWorkspace는 **import path-only 변경**만 적용 (logic-equivalence 가드 통과).
- RequireLogin.tsx는 이번 작업에서 이동하지 않음 — CC-2에서 별도 처리.
- components/common 폴더는 이번 작업 후 RequireLogin.tsx만 남는 것이 정상 상태.

## 3. 백업 파일
경로: `mysuit-ocr/backup/components_common_app_providers_20260522_before_FRONTEND_CC_1_APP_PROVIDERS_LAYOUT_MOVE/`

12개 파일 백업 (AppProviders.tsx + 11 importers):
- `AppProviders.tsx`
- `app_layout.tsx`
- `AutoRestoreWorkspace.tsx`
- `HistoryWorkspace.tsx`
- `TemplateWorkspace.tsx`
- `DetailHistoryView.tsx`
- `TestWorkspace.tsx`
- `UnstructuredBuilder.tsx`
- `TemplateAnnotator.tsx`
- `RunOcrWorkspace.tsx`
- `LoginWorkspace.tsx`
- `OcrResultPanel.tsx`

## 4. 이동 파일

| from | to | 방식 | 본문 변경 |
| --- | --- | --- | --- |
| `src/components/common/AppProviders.tsx` | `src/components/layout/AppProviders.tsx` | `git mv` | 본문 byte-identical. self-import 없음. |

## 5. 수정 파일 (import path 보정만, 총 11곳)

| 파일 | before | after |
| --- | --- | --- |
| `src/app/layout.tsx` | `../components/common/AppProviders` | `../components/layout/AppProviders` |
| `src/components/autorestore/AutoRestoreWorkspace.tsx` | `../common/AppProviders` | `../layout/AppProviders` |
| `src/components/history/HistoryWorkspace.tsx` | `../common/AppProviders` | `../layout/AppProviders` |
| `src/components/template/TemplateWorkspace.tsx` | `../common/AppProviders` | `../layout/AppProviders` |
| `src/components/history/DetailHistoryView.tsx` | `../common/AppProviders` | `../layout/AppProviders` |
| `src/components/test/TestWorkspace.tsx` | `../common/AppProviders` | `../layout/AppProviders` |
| `src/components/template/UnstructuredBuilder.tsx` | `../common/AppProviders` | `../layout/AppProviders` |
| `src/components/template/ui/TemplateAnnotator.tsx` | `../../common/AppProviders` | `../../layout/AppProviders` |
| `src/components/runocr/RunOcrWorkspace.tsx` | `../common/AppProviders` | `../layout/AppProviders` |
| `src/components/login/LoginWorkspace.tsx` | `../common/AppProviders` | `../layout/AppProviders` |
| `src/components/runocr/ui/OcrResultPanel.tsx` | `../../common/AppProviders` | `../../layout/AppProviders` |

기존 3개 검사에 post-CC-1 상태 허용 patch 적용 (검사 로직 변경 없음, regex/fallback만 추가):
- `tmp/check_template_workspace_move_4a.mjs` — `template_workspace_keeps_common_import`에
  `../layout/AppProviders` 양쪽 허용.
- `tmp/check_template_editor_ui_move_4b.mjs` — `annotator_imports_common_via_two_levels`에
  `../../layout/AppProviders` 양쪽 허용.
- `tmp/check_filedropzone_common_ui_move_5e.mjs` — `APP_PROVIDERS` 경로 자동 탐지
  (components/common ↔ components/layout).

## 6. 핵심 변경 내용
- `src/components/layout/`에 AppProviders.tsx 추가 (AppShell/Header/Sidebar에 이어 4번째 layout 입주자).
- 11개 importer 전부 `../layout/AppProviders` 또는 `../../layout/AppProviders`로 정리.
- `useUi` export, default export `AppProviders` 보존.
- src/ 운영 코드 잔존 `components/common/AppProviders` / `../common/AppProviders` 0건.
- components/common에는 `RequireLogin.tsx`만 남음 (CC-2 처리 대상).
- CC-1 신규 static check 36개 항목 PASS.

## 7. layout ownership 확인
이동 후 `src/components/layout/` 디렉터리 구성:

| 파일 | 역할 |
| --- | --- |
| `AppProviders.tsx` (CC-1) | 전역 UI context/provider (useUi/loading/alert/confirm) |
| `AppShell.tsx` | app shell layout |
| `Header.tsx` | header |
| `Sidebar.tsx` | sidebar |

→ Global UI provider가 app shell과 같은 도메인에 위치하여 layout 책임 일관성 확보.

## 8. TestWorkspace import path-only 수정 확인
- TestWorkspace.tsx 5줄 1줄만 변경 (`../common/AppProviders → ../layout/AppProviders`).
- CC-1 검사의 `test_workspace_import_path_only_edit` (import path strip 후
  logic-equivalence) PASS — 다른 어떤 code/JSX/state/handler/test flow 변경도
  없음을 byte-equivalent로 확인.
- `src/components/test/core/*` 미수정.

## 9. RequireLogin 미수정 확인
- `src/components/common/RequireLogin.tsx` 그대로 존재, 본 작업에서 미수정.
- CC-1 검사의 `RequireLogin_still_under_components_common`, `RequireLogin_default_export_preserved` 가드 PASS.
- CC-2에서 별도 phase로 처리 예정.

## 10. static check 결과 (CC-1 신규 스크립트)
- 파일: `tmp/check_app_providers_layout_move_cc1.mjs`
- 명령: `node tmp/check_app_providers_layout_move_cc1.mjs`
- 결과: **PASS** (36/36 checks, skippedBackupChecks=0, residuals=0)

## 11. runner 결과 (28개)

| # | runner | 결과 | 비고 |
| --- | --- | --- | --- |
| 1 | `npm run typecheck` | **PASS** (exit 0) | — |
| 2 | `npm run build` | **PASS** (exit 0) | known noise `ESLint: nextVitals is not iterable` |
| 3 | `node tmp/check_table_view_model_v1_fixtures_js.mjs` | **PASS** (8/8) | — |
| 4 | `node tmp/check_clean_json_v1_fixtures_js.mjs` | **PASS** (9/9) | — |
| 5 | `python tmp/codex_markdown_contract_fixture_lock.py --check --phase post_APP_PROVIDERS_LAYOUT_MOVE_20260522` | **PASS** (6/6) | — |
| 6 | `node tmp/check_runocr_formdata_keys_2a.mjs` | **PASS_WITH_SKIPPED_BACKUP** | historical backup |
| 7 | `node tmp/check_runocr_request_boundary_2b.mjs` | **PASS** | — |
| 8 | `node tmp/check_runocr_response_mapping_boundary_2c.mjs` | **PASS_WITH_SKIPPED_BACKUP** | historical backup |
| 9 | `node tmp/check_runocr_result_layout_boundary_3a.mjs` | **PASS** | — |
| 10 | `node tmp/check_runocr_doc_comments_3b.mjs` | **PASS_WITH_SKIPPED_BACKUP** | historical backup |
| 11 | `node tmp/check_template_workspace_move_4a.mjs` | **PASS_WITH_SKIPPED_BACKUP** | CC-1 layout 경로 양쪽 허용 patch |
| 12 | `node tmp/check_template_editor_ui_move_4b.mjs` | **PASS_WITH_SKIPPED_BACKUP** | CC-1 layout 경로 양쪽 허용 patch |
| 13 | `node tmp/check_template_right_panel_rename_6a.mjs` | **PASS** | — |
| 14 | `node tmp/check_template_annotator_rename_6b.mjs` | **PASS** | — |
| 15 | `node tmp/check_ocr_core_types_common_move_5a.mjs` | **PASS** | — |
| 16 | `node tmp/check_ocr_core_ops_common_move_5b.mjs` | **PASS** | — |
| 17 | `node tmp/check_ocr_core_table_common_move_5c.mjs` | **PASS** | — |
| 18 | `node tmp/check_template_export_payload_move_5d.mjs` | **PASS** | — |
| 19 | `node tmp/check_filedropzone_common_ui_move_5e.mjs` | **PASS** | CC-1 APP_PROVIDERS 자동 탐지 patch |
| 20 | `node tmp/check_ocr_canvas_pane_common_ui_move_5f.mjs` | **PASS** | — |
| 21 | `node tmp/check_lib_ocr_result_formatters_common_move_1a.mjs` | **PASS** | — |
| 22 | `node tmp/check_lib_invoice_field_labels_common_move_1b.mjs` | **PASS** | — |
| 23 | `node tmp/check_lib_markdown_report_builder_common_move_1c.mjs` | **PASS** | — |
| 24 | `node tmp/check_lib_clean_json_builder_common_move_1d.mjs` | **PASS** | — |
| 25 | `node tmp/check_lib_invoice_table_display_common_move_1e.mjs` | **PASS** | — |
| 26 | `node tmp/check_lib_structured_table_view_model_common_move_1f.mjs` | **PASS** | — |
| 27 | `node tmp/check_app_providers_layout_move_cc1.mjs` | **PASS** | 36/36 |
| 28 | `node tmp/check_validation_baseline_repair_1a.mjs` | **PASS** | — |

요약: 25개 노드 러너 + 1 파이썬 러너 + typecheck + build 전부 exit 0. PASS 또는
PASS_WITH_SKIPPED_BACKUP만 존재, FAIL 0건.

## 12. typecheck / build 결과
- `npm run typecheck` → **PASS** (exit 0)
- `npm run build` → **PASS** (exit 0)
- 로그: `ocr-server/logs/codex_FRONTEND_CC_1_APP_PROVIDERS_LAYOUT_MOVE.out.log`,
  `ocr-server/logs/codex_FRONTEND_CC_1_APP_PROVIDERS_LAYOUT_MOVE.err.log`

## 13. known stderr noise
- `ESLint: nextVitals is not iterable` — 빌드 exit 0, non-blocking (사전 기재된 known noise).

## 14. 남은 이슈
- 과거 phase(2A/2B/3B/4A/4B)의 logic-equivalence 검사는 backup 파일 부재로
  `PASS_WITH_SKIPPED_BACKUP`로 처리되고 있다. CC-1과 무관한 사전 상태.
- `common/utils/ocrResultFormatters.ts`가 여전히 `@/lib/autofillEngine`을
  type-only import (1A 시점부터, 후속 LIB phase에서 해소).
- `src/components/common/`에 `RequireLogin.tsx`만 남음. CC-2에서 별도 이동 예정.
- `src/lib/profiles.ts`의 doc-comment 문자열 `core/types.ts`는 5A 시점부터의
  잔존.

## 15. 다음 작업 제안
- CC-2 `RequireLogin → components/login/ui` 이동 (components/common 완전
  비우기).
- CC-3 `components/common` 폴더 absent/empty 검증.
- bizNumber 이동 전 TestWorkspace 영향 precheck.
- autofillEngine 이동 precheck (1A의 남은 type-only 임시 의존 해소 — runtime
  사용처 광범위, 별도 phase 권장).
- history/restore 구조 정리 precheck.
- TestWorkspace 구조 정리는 별도 사용자 확인 후 진행.
