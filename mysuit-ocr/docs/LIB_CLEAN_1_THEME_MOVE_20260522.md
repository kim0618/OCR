# LIB_CLEAN_1_THEME_MOVE 20260522

## 1. 사용 도구와 모델
- 도구: Claude Code (VSCode extension)
- 모델: Claude Opus 4.7 (1M context)
- 작업 디렉터리: `mysuit-ocr/`

## 2. 작업 목적
`src/lib` 완전 제거 plan의 첫 번째 실제 이동. `src/lib/theme.ts`(useTheme React hook, light/dark 토글 + `mysuit_ocr_theme` localStorage)를 `src/components/layout/utils/theme.ts`로 이동.

- 본문 byte-identical 유지 (import path strip 후 동일).
- 1 importer(Header.tsx)의 import path 한 줄만 보정 (`./utils/theme` sibling 형태).
- 다른 src/lib 파일은 미이동.
- TestWorkspace / test/core / fixture / templates.json 미수정.
- 새 디렉터리 `src/components/layout/utils/` 입주.

## 3. 백업 파일
경로: `mysuit-ocr/backup/theme_layout_utils_20260522_before_LIB_CLEAN_1_THEME_MOVE/`

| 파일 | bytes |
| --- | --- |
| `theme.ts` | 1,106 |
| `Header.tsx` | 2,464 |

## 4. 이동 파일

| from | to | 방식 | 본문 변경 |
| --- | --- | --- | --- |
| `src/lib/theme.ts` | `src/components/layout/utils/theme.ts` | `git mv` | byte-identical (leaf hook, react만 import). |

## 5. 수정 파일 (import path 보정만)

| 파일 | line | before | after |
| --- | --- | --- | --- |
| `src/components/layout/Header.tsx` | 6 | `@/lib/theme` | `./utils/theme` |

## 6. import 수정 내용
- Header.tsx는 layout 폴더 내부 파일이므로 sibling/하위 디렉터리 import (`./utils/theme`)가 더 자연스러움. alias(`@/components/layout/utils/theme`)도 검사상 동등하게 허용되지만 sibling 형태로 채택.
- 다른 어떤 파일도 theme import 없음 (precheck importedBy=1과 일치).

## 7. layout/utils ownership 확인
이동 후 `src/components/layout/` 구성:

| 항목 | 역할 |
| --- | --- |
| `AppProviders.tsx` | App-wide context providers (CC-1) |
| `AppShell.tsx` | 페이지 셸 |
| `Header.tsx` | 상단 헤더 (`./utils/theme` 사용) |
| `Sidebar.tsx` | 사이드바 |
| `utils/theme.ts` (LC-1) | useTheme hook (신규 입주) |

`src/components/layout/utils/`는 layout feature 전용 hook/util 디렉터리로 정착.

## 8. static check 결과 (LC-1 신규 스크립트)
- 파일: `tmp/check_theme_layout_utils_move_lc1.mjs`
- 명령: `node tmp/check_theme_layout_utils_move_lc1.mjs`
- 결과: **PASS** (17/17 checks, skippedBackupChecks=0, residuals=0)

검증 항목:
- `new_theme_exists` + `old_theme_absent`
- 7 lib sibling 잔류 가드 (다른 src/lib 파일 미이동 확인)
- `TestWorkspace_present`, `test_core_dir_present`
- `useTheme` export 보존
- react만 import (components/* import 없음, `mysuit_ocr_theme` key 보존)
- new_theme logic_unchanged_vs_backup (import strip 후 동일)
- Header.tsx new path import + logic_unchanged_vs_backup
- residual scan (`@/lib/theme`, `../lib/theme`, `../../lib/theme`) 0건

## 9. runner 결과

| # | runner | 결과 |
| --- | --- | --- |
| 1 | `npm run typecheck` | **PASS** (exit 0) |
| 2 | `npm run build` | **PASS** (exit 0) |
| 3 | `check_theme_layout_utils_move_lc1` | **PASS** (17/17, 신규) |
| 4 | `check_table_view_model_v1_fixtures_js` | **PASS** (8/8) |
| 5 | `check_clean_json_v1_fixtures_js` | **PASS** (9/9) |
| 6 | `python markdown contract --check --phase post_LIB_CLEAN_1_THEME_MOVE_20260522` | **PASS** (6/6) |
| 7 | `check_biz_number_common_utils_move_bz1` | **PASS** |
| 8 | `check_history_store_common_storage_move_cs2` | **PASS** |
| 9 | `check_image_store_common_storage_move_cs1` | **PASS** |
| 10 | `check_detail_history_view_ui_move_hr2` | **PASS** |
| 11 | `check_history_popup_ui_move_hr1` | **PASS** |
| 12 | `check_app_providers_layout_move_cc1` | **PASS** |
| 13 | `check_require_login_login_ui_move_cc2` | **PASS** |
| 14 | `check_validation_baseline_repair_1a` | **PASS** |
| 15–20 | `check_lib_*_1a~1f` (6개) | **PASS** |
| 21–26 | `check_ocr_core_*_5a~5c` + `5d` + `5e` + `5f` | **PASS** |
| 27–28 | `check_template_right_panel_rename_6a/6b` | **PASS** |
| 29–30 | `check_runocr_request_boundary_2b/result_layout_3a` | **PASS** |

요약: 27개 노드 러너 + 1 파이썬 러너 + typecheck + build 전부 exit 0. PASS만 존재, FAIL 0건.

기존 static check 어느 것도 LC-1 호환 patch가 필요하지 않았음 (이전 phase 검사들은 `theme.ts`를 SIBLINGS에 포함하지 않음).

## 10. typecheck / build 결과
- `npm run typecheck` → **PASS** (exit 0)
- `npm run build` → **PASS** (exit 0)
- 로그:
  - `ocr-server/logs/claude_LIB_CLEAN_1_THEME_MOVE.out.log`
  - `ocr-server/logs/claude_LIB_CLEAN_1_THEME_MOVE.err.log`

## 11. known stderr noise
- `ESLint: nextVitals is not iterable` — 빌드 exit 0, non-blocking.

## 12. 남은 src/lib 파일 (7개)
- `src/lib/autofillEngine.ts` (LIB-CLEAN-9 대상)
- `src/lib/axios.ts` (LIB-CLEAN-3 대상)
- `src/lib/groundTruthStore.ts` (LIB-CLEAN-4 대상)
- `src/lib/login.ts` (LIB-CLEAN-2 대상 — 다음 작업)
- `src/lib/profiles.ts` (LIB-CLEAN-7 대상)
- `src/lib/restoreProfileStore.ts` (LIB-CLEAN-5 대상)
- `src/lib/testsets.ts` (LIB-CLEAN-6 대상)

## 13. 다음 작업 제안
- **LIB-CLEAN-2-LOGIN-STORAGE-MOVE** — `src/lib/login.ts → src/common/storage/login.ts` (axios의 sibling 의존이라 LIB-CLEAN-3 axios 이동 전에 선행 필수).
- 이후 LIB-CLEAN-3 → 10 plan 순서대로 진행.
- LIB-CLEAN-10-SRC-LIB-ABSENT-CHECK PASS 후에만 Template table column definition 기능 작업 precheck로 진입.
