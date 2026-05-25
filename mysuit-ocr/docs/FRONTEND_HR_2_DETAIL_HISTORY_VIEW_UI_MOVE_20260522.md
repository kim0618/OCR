# FRONTEND_HR_2_DETAIL_HISTORY_VIEW_UI_MOVE 20260522

## 1. 사용 도구와 모델
- 도구: Claude Code (VSCode extension)
- 모델: Claude Opus 4.7 (1M context)
- 작업 디렉터리: `mysuit-ocr/`

## 2. 작업 목적
history/restore 구조 정리 두 번째 micro-step. `src/components/history/DetailHistoryView.tsx`만
`src/components/history/ui/DetailHistoryView.tsx`로 이동하여 history detail view를
HR-1의 두 popup과 같은 ui 폴더로 정리.

- DetailHistoryView 본문/JSX/state/handler/GT 저장/restore profile 액션 byte-identical 유지.
- 영향 받은 파일은 import path만 보정 (HistoryWorkspace 1줄 + 이동된 파일 내부
  `../layout/AppProviders → ../../layout/AppProviders` 1줄).
- historyStore/imageStore/groundTruthStore/restoreProfileStore/autofillEngine
  store/util 계층 미수정.
- autorestore/restore 미수정.
- TestWorkspace 미수정.

## 3. 백업 파일
경로: `mysuit-ocr/backup/detail_history_view_ui_20260522_before_FRONTEND_HR_2_DETAIL_HISTORY_VIEW_UI_MOVE/`

| 파일 | bytes |
| --- | --- |
| `DetailHistoryView.tsx` | 35,404 |
| `HistoryWorkspace.tsx` | 14,348 |

## 4. 이동 파일

| from | to | 방식 | 본문 변경 |
| --- | --- | --- | --- |
| `src/components/history/DetailHistoryView.tsx` | `src/components/history/ui/DetailHistoryView.tsx` | `git mv` | self-import 1줄(`../layout/AppProviders`)만 depth +1 (`../../layout/AppProviders`)로 보정. 나머지 imports는 `@/` 알리아스이라 깊이 변경 영향 없음. JSX/state/handler/GT/restore profile 액션 전부 byte-identical. |

## 5. 수정 파일 (import path 보정만)

| 파일 | before | after |
| --- | --- | --- |
| `src/components/history/HistoryWorkspace.tsx` (line 8) | `./DetailHistoryView` | `./ui/DetailHistoryView` |
| `src/components/history/ui/DetailHistoryView.tsx` (line 26) | `../layout/AppProviders` | `../../layout/AppProviders` |

기존 4개 검사에 post-HR-2 상태 허용 patch 적용 (검사 로직 변경 없음, regex/fallback만 추가):
- `tmp/check_history_popup_ui_move_hr1.mjs` — `DETAIL_HISTORY` 자동 탐지
  (history/ ↔ history/ui).
- `tmp/check_app_providers_layout_move_cc1.mjs` — `DETAIL_HISTORY` 자동 탐지 +
  `detail_history` importer의 `expectedImport` regex가 `../layout/AppProviders`
  와 `../../layout/AppProviders` 양쪽 허용.
- `tmp/check_lib_invoice_field_labels_common_move_1b.mjs` — `DETAIL_HISTORY` 자동
  탐지.
- `tmp/check_lib_invoice_table_display_common_move_1e.mjs` — `DETAIL_HISTORY`
  자동 탐지.

## 6. 핵심 변경 내용
- DetailHistoryView 본문 그대로 (logic-equivalent vs backup PASS).
- HistoryWorkspace 1줄 import path만 변경.
- `useUi` import depth만 1단계 깊어짐, hasStoredLogin/historyStore/groundTruthStore/
  restoreProfileStore/autofillEngine import는 `@/` 알리아스로 그대로 유지.
- src/ 운영 코드 잔존 `./DetailHistoryView` / `components/history/DetailHistoryView`
  문자열 0건.
- store/util 파일 5개(historyStore/imageStore/groundTruthStore/restoreProfileStore/autofillEngine)
  모두 미수정. HR-1 popup 2개(CreateHistoryPopup/EditHistoryPopup)도 미수정.
- HR-2 신규 static check 29개 항목 PASS.

## 7. history/ui ownership 확인
이동 후 `src/components/history/` 구성:

| 파일/디렉터리 | 역할 |
| --- | --- |
| `HistoryWorkspace.tsx` | feature root |
| `ui/CreateHistoryPopup.tsx` (HR-1) | 신규 history 생성 popup |
| `ui/EditHistoryPopup.tsx` (HR-1) | history 편집 popup |
| `ui/DetailHistoryView.tsx` (HR-2) | history detail view |

→ history feature는 root(HistoryWorkspace) + ui/* 폴더 구조로 정리됨.

## 8. DetailHistoryView move-only 확인
- 본문 byte-identical (logic-equivalent vs backup, path strip 후 비교 PASS).
- 변경 라인은 self-import `useUi` 1줄(depth +1)뿐. 다른 JSX/state/handler/액션
  변경 없음.
- `output fields/tableRows` 편집, `GT 저장`, `restore profile 저장/update` 동작
  변경 없음.

## 9. historyStore/imageStore/restoreProfileStore/autofillEngine 미수정 확인
- 5개 store/util 파일(`historyStore.ts`, `imageStore.ts`, `groundTruthStore.ts`,
  `restoreProfileStore.ts`, `autofillEngine.ts`) 모두 미수정.
- HR-2 검사의 `historyStore_present` / `imageStore_present` /
  `groundTruthStore_present` / `restoreProfileStore_present` /
  `autofillEngine_present` 가드 PASS.
- 각 파일 `_has_exports` 가드도 PASS.

## 10. TestWorkspace 미수정 확인
- `src/components/test/TestWorkspace.tsx` 미수정.
- `src/components/test/core/*` 미수정.
- TestWorkspace는 DetailHistoryView를 직접 import한 적이 없음.

## 11. static check 결과 (HR-2 신규 스크립트)
- 파일: `tmp/check_detail_history_view_ui_move_hr2.mjs`
- 명령: `node tmp/check_detail_history_view_ui_move_hr2.mjs`
- 결과: **PASS** (29/29 checks, skippedBackupChecks=0, residuals=0)

## 12. runner 결과 (23개 + typecheck + build + markdown contract)

| # | runner | 결과 |
| --- | --- | --- |
| 1 | `npm run typecheck` | **PASS** (exit 0) |
| 2 | `npm run build` | **PASS** (exit 0) |
| 3 | `check_table_view_model_v1_fixtures_js` | **PASS** (8/8) |
| 4 | `check_clean_json_v1_fixtures_js` | **PASS** (9/9) |
| 5 | `python markdown contract --check --phase post_DETAIL_HISTORY_VIEW_UI_MOVE_20260522` | **PASS** (6/6) |
| 6 | `check_history_popup_ui_move_hr1` | **PASS** (HR-2 DETAIL_HISTORY 자동 탐지 patch) |
| 7 | `check_app_providers_layout_move_cc1` | **PASS** (HR-2 DETAIL_HISTORY 자동 탐지 + depth-flex regex) |
| 8 | `check_require_login_login_ui_move_cc2` | **PASS** |
| 9 | `check_validation_baseline_repair_1a` | **PASS** |
| 10–15 | `check_lib_*_1a~1f` (6개) | **PASS** (1B/1E에 HR-2 DETAIL_HISTORY 자동 탐지 patch) |
| 16–21 | `check_ocr_core_*_5a~5f` + `template_export_payload_5d` (총 6개) | **PASS** |
| 22–23 | `check_template_right_panel_rename_6a/6b` | **PASS** |
| 24–25 | `check_runocr_request_boundary_2b/result_layout_3a` | **PASS** |
| 26 | `check_detail_history_view_ui_move_hr2` | **PASS** (29/29) |

요약: 23개 노드 러너 + 1 파이썬 러너 + typecheck + build 전부 exit 0. PASS만
존재, FAIL 0건.

## 13. typecheck / build 결과
- `npm run typecheck` → **PASS** (exit 0)
- `npm run build` → **PASS** (exit 0)
- 로그: `ocr-server/logs/codex_FRONTEND_HR_2_DETAIL_HISTORY_VIEW_UI_MOVE.out.log`,
  `ocr-server/logs/codex_FRONTEND_HR_2_DETAIL_HISTORY_VIEW_UI_MOVE.err.log`

## 14. known stderr noise
- `ESLint: nextVitals is not iterable` — 빌드 exit 0, non-blocking (사전 기재된 known noise).

## 15. 남은 이슈
- historyStore/imageStore/restoreProfileStore/groundTruthStore/autofillEngine
  store/util 계층 미이동 — HR-3/HR-4 별도 phase.
- `common/utils/ocrResultFormatters.ts`가 여전히 `@/lib/autofillEngine`을
  type-only import (1A 시점부터, 후속 LIB phase에서 해소).
- `src/lib/profiles.ts`의 doc-comment 문자열 `core/types.ts`는 5A 시점부터의
  잔존.

## 16. 다음 작업 제안
- **HR-3 `historyStore` 별도 precheck** (영향 범위가 넓어 분리).
- **HR-4 `imageStore` 별도 precheck**.
- **RS-1 `autorestore → restore` 폴더 정리 precheck**.
- `autofillEngine` 별도 precheck.
- TestWorkspace 구조 정리는 별도 사용자 확인 후 진행.
- HR/RS 단계 마무리 후 Template table column definition feature precheck로 이행 가능.
