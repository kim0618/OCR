# FRONTEND_CC_2_REQUIRE_LOGIN_LOGIN_UI_MOVE 20260522

## 1. 사용 도구와 모델
- 도구: Claude Code (VSCode extension)
- 모델: Claude Opus 4.7 (1M context)
- 작업 디렉터리: `mysuit-ocr/`

## 2. 작업 목적
components/common 잔여 정리(CC) 두 번째 micro-step. `src/components/common/RequireLogin.tsx`만
`src/components/login/ui/RequireLogin.tsx`로 이동하여 client auth guard
(hasStoredLogin + useRouter → `/login` redirect)를 login/auth 도메인으로 정리.

- 본문/JSX/route guard 동작 byte-identical 유지.
- 영향 받은 파일은 import path만 보정 (2곳: autorestore/page + history/page).
- AppProviders.tsx는 이미 CC-1에서 components/layout으로 이동되어 본 작업에서
  미수정.
- TestWorkspace 미수정.
- components/common 폴더는 RequireLogin 이동 후 빈 디렉터리가 되어 제거됨
  (placeholder 파일 미생성). CC-3 별도 검증 가능.

## 3. 백업 파일
경로: `mysuit-ocr/backup/components_common_require_login_20260522_before_FRONTEND_CC_2_REQUIRE_LOGIN_LOGIN_UI_MOVE/`

| 파일 | bytes |
| --- | --- |
| `RequireLogin.tsx` | 716 |
| `app_autorestore_page.tsx` | 435 |
| `app_history_page.tsx` | 419 |

## 4. 이동 파일

| from | to | 방식 | 본문 변경 |
| --- | --- | --- | --- |
| `src/components/common/RequireLogin.tsx` | `src/components/login/ui/RequireLogin.tsx` | `git mv` | 본문 byte-identical. self-import 없음. |

## 5. 수정 파일 (import path 보정만)

| 파일 | before | after |
| --- | --- | --- |
| `src/app/autorestore/page.tsx` | `@/components/common/RequireLogin` | `@/components/login/ui/RequireLogin` |
| `src/app/history/page.tsx` | `@/components/common/RequireLogin` | `@/components/login/ui/RequireLogin` |

`src/components/common/` 디렉터리는 비어 자연 제거. placeholder 파일 미생성.

기존 2개 검사에 post-CC-2 RequireLogin 위치 자동 탐지 patch 적용 (검사 로직
변경 없음, 경로 fallback만 추가):
- `tmp/check_filedropzone_common_ui_move_5e.mjs` — `REQUIRE_LOGIN` 경로 자동
  탐지 (components/common ↔ components/login/ui).
- `tmp/check_app_providers_layout_move_cc1.mjs` — 동일 패턴.

## 6. 핵심 변경 내용
- `src/components/login/ui/`에 RequireLogin.tsx 추가 (login 도메인 신규 ui 입주자).
- `hasStoredLogin`, `useRouter`, `/login` redirect 정책 보존 (CC-2 검사가 명시적
  확인).
- 2개 route page(autorestore/history) 전부 새 import path로 정리.
- **src/components/common/ 폴더 완전 제거** (자연 비움 + placeholder 없음).
- LoginWorkspace.tsx는 components/login에 유지(미수정), RequireLogin은
  components/login/ui로 추가되어 login 도메인 구조가 명확해짐.
- src/ 운영 코드 잔존 `@/components/common/RequireLogin` /
  `../common/RequireLogin` 0건.
- CC-2 신규 static check 18개 항목 PASS.

## 7. login/ui ownership 확인
이동 후 `src/components/login/` 디렉터리 구성:

| 파일/디렉터리 | 역할 |
| --- | --- |
| `LoginWorkspace.tsx` | login form workspace (미수정) |
| `ui/RequireLogin.tsx` (CC-2) | client auth guard (hasStoredLogin + useRouter → /login redirect) |

→ login 도메인 안에 workspace와 ui guard가 함께 위치하여 auth 책임 일관성 확보.

## 8. AppProviders 미수정 확인
- `src/components/layout/AppProviders.tsx` (CC-1 결과물) 그대로 존재.
- CC-2 검사의 `AppProviders_still_under_layout`, `AppProviders_absent_from_common`
  가드 PASS.
- CC-2 작업 중 AppProviders.tsx 본문 미수정.

## 9. TestWorkspace 미수정 확인
- `src/components/test/TestWorkspace.tsx` 미수정. RequireLogin을 직접 import한
  적이 없음.
- `src/components/test/core/*` 미수정.

## 10. components/common empty/absent 상태
- `src/components/common/` 디렉터리 자체가 제거됨.
- CC-2 검사의 `components_common_dir_empty_or_removed` 가드 PASS
  (`remainingCommonFiles === null`).
- CC-3 별도 phase에서 추가 검증 가능 (예: 어떤 import도 `components/common/`
  path를 참조하지 않음 확인).

## 11. static check 결과 (CC-2 신규 스크립트)
- 파일: `tmp/check_require_login_login_ui_move_cc2.mjs`
- 명령: `node tmp/check_require_login_login_ui_move_cc2.mjs`
- 결과: **PASS** (18/18 checks, skippedBackupChecks=0, residuals=0)

## 12. runner 결과 (29개)

| # | runner | 결과 | 비고 |
| --- | --- | --- | --- |
| 1 | `npm run typecheck` | **PASS** (exit 0) | — |
| 2 | `npm run build` | **PASS** (exit 0) | known noise `ESLint: nextVitals is not iterable` |
| 3 | `node tmp/check_table_view_model_v1_fixtures_js.mjs` | **PASS** (8/8) | — |
| 4 | `node tmp/check_clean_json_v1_fixtures_js.mjs` | **PASS** (9/9) | — |
| 5 | `python tmp/codex_markdown_contract_fixture_lock.py --check --phase post_REQUIRE_LOGIN_LOGIN_UI_MOVE_20260522` | **PASS** (6/6) | — |
| 6 | `node tmp/check_runocr_formdata_keys_2a.mjs` | **PASS_WITH_SKIPPED_BACKUP** | historical backup |
| 7 | `node tmp/check_runocr_request_boundary_2b.mjs` | **PASS** | — |
| 8 | `node tmp/check_runocr_response_mapping_boundary_2c.mjs` | **PASS_WITH_SKIPPED_BACKUP** | historical backup |
| 9 | `node tmp/check_runocr_result_layout_boundary_3a.mjs` | **PASS** | — |
| 10 | `node tmp/check_runocr_doc_comments_3b.mjs` | **PASS_WITH_SKIPPED_BACKUP** | historical backup |
| 11 | `node tmp/check_template_workspace_move_4a.mjs` | **PASS_WITH_SKIPPED_BACKUP** | — |
| 12 | `node tmp/check_template_editor_ui_move_4b.mjs` | **PASS_WITH_SKIPPED_BACKUP** | — |
| 13 | `node tmp/check_template_right_panel_rename_6a.mjs` | **PASS** | — |
| 14 | `node tmp/check_template_annotator_rename_6b.mjs` | **PASS** | — |
| 15 | `node tmp/check_ocr_core_types_common_move_5a.mjs` | **PASS** | — |
| 16 | `node tmp/check_ocr_core_ops_common_move_5b.mjs` | **PASS** | — |
| 17 | `node tmp/check_ocr_core_table_common_move_5c.mjs` | **PASS** | — |
| 18 | `node tmp/check_template_export_payload_move_5d.mjs` | **PASS** | — |
| 19 | `node tmp/check_filedropzone_common_ui_move_5e.mjs` | **PASS** | CC-2 REQUIRE_LOGIN 자동 탐지 patch |
| 20 | `node tmp/check_ocr_canvas_pane_common_ui_move_5f.mjs` | **PASS** | — |
| 21 | `node tmp/check_lib_ocr_result_formatters_common_move_1a.mjs` | **PASS** | — |
| 22 | `node tmp/check_lib_invoice_field_labels_common_move_1b.mjs` | **PASS** | — |
| 23 | `node tmp/check_lib_markdown_report_builder_common_move_1c.mjs` | **PASS** | — |
| 24 | `node tmp/check_lib_clean_json_builder_common_move_1d.mjs` | **PASS** | — |
| 25 | `node tmp/check_lib_invoice_table_display_common_move_1e.mjs` | **PASS** | — |
| 26 | `node tmp/check_lib_structured_table_view_model_common_move_1f.mjs` | **PASS** | — |
| 27 | `node tmp/check_app_providers_layout_move_cc1.mjs` | **PASS** | CC-2 REQUIRE_LOGIN 자동 탐지 patch |
| 28 | `node tmp/check_require_login_login_ui_move_cc2.mjs` | **PASS** | 18/18 |
| 29 | `node tmp/check_validation_baseline_repair_1a.mjs` | **PASS** | — |

요약: 26개 노드 러너 + 1 파이썬 러너 + typecheck + build 전부 exit 0.
PASS 또는 PASS_WITH_SKIPPED_BACKUP만 존재, FAIL 0건.

## 13. typecheck / build 결과
- `npm run typecheck` → **PASS** (exit 0)
- `npm run build` → **PASS** (exit 0)
- 로그: `ocr-server/logs/codex_FRONTEND_CC_2_REQUIRE_LOGIN_LOGIN_UI_MOVE.out.log`,
  `ocr-server/logs/codex_FRONTEND_CC_2_REQUIRE_LOGIN_LOGIN_UI_MOVE.err.log`

## 14. known stderr noise
- `ESLint: nextVitals is not iterable` — 빌드 exit 0, non-blocking (사전 기재된 known noise).

## 15. 남은 이슈
- 과거 phase(2A/2B/3B/4A/4B)의 logic-equivalence 검사는 backup 파일 부재로
  `PASS_WITH_SKIPPED_BACKUP`로 처리되고 있다. CC-2와 무관한 사전 상태.
- `common/utils/ocrResultFormatters.ts`가 여전히 `@/lib/autofillEngine`을
  type-only import (1A 시점부터, 후속 LIB phase에서 해소).
- `src/components/common/` 폴더 완전 제거됨 — CC-3 검증 시 absent 상태로 확인 가능.
- `src/lib/profiles.ts`의 doc-comment 문자열 `core/types.ts`는 5A 시점부터의
  잔존.

## 16. 다음 작업 제안
- CC-3 `components/common` 폴더 absent/empty 정식 검증 (선택).
- `bizNumber → common/utils` 이동 precheck (TestWorkspace 영향 확인 후 진행).
- `autofillEngine → common/utils` 이동 precheck (1A 남은 type-only 임시 의존 해소).
- `profiles/imageStore/historyStore/restoreProfileStore/groundTruthStore/testsets`는
  별도 precheck 후 진행.
- history/restore 구조 정리 precheck.
- TestWorkspace 구조 정리는 별도 사용자 확인 후 진행.
