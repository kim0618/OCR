# FRONTEND_HR_1_HISTORY_POPUP_UI_MOVE 20260522

## 1. 사용 도구와 모델
- 도구: Claude Code (VSCode extension)
- 모델: Claude Opus 4.7 (1M context)
- 작업 디렉터리: `mysuit-ocr/`

## 2. 작업 목적
history/restore 구조 정리 첫 micro-step. `src/components/history/popup/CreateHistoryPopup.tsx`와
`src/components/history/popup/EditHistoryPopup.tsx`를 `src/components/history/ui/`로
이동하여 history feature 내부 UI 조각을 목표 구조에 맞춰 정리.

- 본문/JSX/state/handler/props 타입 byte-identical 유지.
- 영향 받은 파일은 import path만 보정 (HistoryWorkspace 2줄).
- DetailHistoryView.tsx는 이번 작업에서 미수정 (HR-2 별도 처리).
- HistoryWorkspace.tsx는 feature root 유지, import path만 보정.
- historyStore/imageStore 등 store 계층 미수정.
- autorestore/restore 폴더 미수정.
- TestWorkspace 미수정.
- history/popup 폴더는 자연 비움 후 제거 (placeholder 없음).

## 3. 백업 파일
경로: `mysuit-ocr/backup/history_popup_ui_20260522_before_FRONTEND_HR_1_HISTORY_POPUP_UI_MOVE/`

| 파일 | bytes |
| --- | --- |
| `CreateHistoryPopup.tsx` | 6,971 |
| `EditHistoryPopup.tsx` | 7,061 |
| `HistoryWorkspace.tsx` | 14,354 |

## 4. 이동 파일

| from | to | 방식 | 본문 변경 |
| --- | --- | --- | --- |
| `src/components/history/popup/CreateHistoryPopup.tsx` | `src/components/history/ui/CreateHistoryPopup.tsx` | `git mv` | 본문 byte-identical |
| `src/components/history/popup/EditHistoryPopup.tsx` | `src/components/history/ui/EditHistoryPopup.tsx` | `git mv` | 본문 byte-identical |

## 5. 수정 파일 (import path 보정만)

| 파일 | before | after |
| --- | --- | --- |
| `src/components/history/HistoryWorkspace.tsx` (line 6) | `./popup/CreateHistoryPopup` | `./ui/CreateHistoryPopup` |
| `src/components/history/HistoryWorkspace.tsx` (line 7) | `./popup/EditHistoryPopup` | `./ui/EditHistoryPopup` |

`src/components/history/popup/` 디렉터리 자연 제거 (placeholder 미생성).

기존 static check 어떤 것도 patch 불필요 — history/popup 또는 history/ui 경로를
참조하는 검사 없음.

## 6. 핵심 변경 내용
- `src/components/history/ui/` 신규 디렉터리 입주 (CreateHistoryPopup +
  EditHistoryPopup).
- `CreateHistoryPopup` default export, `HistoryPopupForm` type export 보존.
- `EditHistoryPopup` default export, `HistoryPopupRow` type export 보존.
- HistoryWorkspace.tsx 2줄 변경만 — 다른 모든 logic/JSX/state/handler 보존
  (HR-1 검사의 `workspace_logic_unchanged_vs_backup` 가드 PASS).
- src/ 운영 코드 잔존 `./popup/CreateHistoryPopup`, `./popup/EditHistoryPopup`,
  `history/popup/...` 문자열 0개.
- HR-1 신규 static check 24개 항목 PASS.

## 7. history/ui ownership 확인
이동 후 `src/components/history/` 구성:

| 파일/디렉터리 | 역할 |
| --- | --- |
| `HistoryWorkspace.tsx` | feature root |
| `DetailHistoryView.tsx` | history 상세 뷰 (HR-2 후보) |
| `ui/CreateHistoryPopup.tsx` (HR-1) | 신규 history 생성 popup |
| `ui/EditHistoryPopup.tsx` (HR-1) | history 편집 popup |

→ history 도메인 안에 feature root + 상세 뷰 + UI 조각이 정리됨.

## 8. DetailHistoryView 미수정 확인
- `src/components/history/DetailHistoryView.tsx` 미수정.
- HR-1 검사의 `DetailHistoryView_present`, `DetailHistoryView_default_export_preserved` 가드 PASS.
- store/GT/restore 연동 때문에 HR-2에서 별도 평가.

## 9. historyStore/imageStore 미수정 확인
- `src/lib/historyStore.ts`, `src/lib/imageStore.ts` 미수정.
- HR-1 검사의 `historyStore_has_exports`, `imageStore_has_exports` 가드 PASS.
- store 계층은 영향 범위가 넓어 별도 phase로 분리.

## 10. TestWorkspace 미수정 확인
- `src/components/test/TestWorkspace.tsx` 미수정.
- `src/components/test/core/*` 미수정.
- TestWorkspace는 popup을 직접 import한 적이 없음.

## 11. static check 결과 (HR-1 신규 스크립트)
- 파일: `tmp/check_history_popup_ui_move_hr1.mjs`
- 명령: `node tmp/check_history_popup_ui_move_hr1.mjs`
- 결과: **PASS** (24/24 checks, skippedBackupChecks=0, residuals=0)

## 12. runner 결과 (22개 + typecheck + build + markdown contract)

| # | runner | 결과 |
| --- | --- | --- |
| 1 | `npm run typecheck` | **PASS** (exit 0) |
| 2 | `npm run build` | **PASS** (exit 0) |
| 3 | `check_table_view_model_v1_fixtures_js` | **PASS** (8/8) |
| 4 | `check_clean_json_v1_fixtures_js` | **PASS** (9/9) |
| 5 | `python markdown contract --check --phase post_HISTORY_POPUP_UI_MOVE_20260522` | **PASS** (6/6) |
| 6 | `check_app_providers_layout_move_cc1` | **PASS** |
| 7 | `check_require_login_login_ui_move_cc2` | **PASS** |
| 8 | `check_validation_baseline_repair_1a` | **PASS** |
| 9–14 | `check_lib_*_1a~1f` (6개) | **PASS** (전부) |
| 15–20 | `check_ocr_core_*_5a~5f` + `template_export_payload_5d` (총 6개) | **PASS** (전부) |
| 21–22 | `check_template_right_panel_rename_6a/6b` | **PASS** |
| 23–24 | `check_runocr_request_boundary_2b/result_layout_3a` | **PASS** |
| 25 | `check_history_popup_ui_move_hr1` | **PASS** (24/24) |

요약: 22개 노드 러너 + 1 파이썬 러너 + typecheck + build 전부 exit 0. PASS만
존재, FAIL 0건.

## 13. typecheck / build 결과
- `npm run typecheck` → **PASS** (exit 0)
- `npm run build` → **PASS** (exit 0)
- 로그: `ocr-server/logs/codex_FRONTEND_HR_1_HISTORY_POPUP_UI_MOVE.out.log`,
  `ocr-server/logs/codex_FRONTEND_HR_1_HISTORY_POPUP_UI_MOVE.err.log`

## 14. known stderr noise
- `ESLint: nextVitals is not iterable` — 빌드 exit 0, non-blocking (사전 기재된 known noise).

## 15. 남은 이슈
- DetailHistoryView.tsx는 store/GT/restore 연동 때문에 HR-1에서 미이동. HR-2에서
  history/ui 이동 가능성을 별도 판단해야 함.
- historyStore/imageStore는 영향 범위가 넓어 별도 phase 대상.
- `common/utils/ocrResultFormatters.ts`가 여전히 `@/lib/autofillEngine`을
  type-only import (1A 시점부터, 후속 LIB phase에서 해소).
- `src/lib/profiles.ts`의 doc-comment 문자열 `core/types.ts`는 5A 시점부터의 잔존.

## 16. 다음 작업 제안
- **HR-2 `DetailHistoryView → history/ui` 이동 precheck** (store/GT/restore 연동
  점검 필요).
- **HR-3 `historyStore` 별도 precheck** (영향 범위가 넓어 분리).
- **HR-4 `imageStore` 별도 precheck**.
- **RS-1 `autorestore → restore` 폴더 정리 precheck**.
- `autofillEngine` 별도 precheck.
- TestWorkspace 구조 정리는 별도 사용자 확인 후 진행.
- 사용자가 구조 작업을 모두 마친 뒤 Template table column definition 기능으로
  진입한다고 표명함 — HR/RS 단계 마무리 후 Template feature precheck로 이행 가능.
