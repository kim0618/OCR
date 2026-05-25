# FRONTEND_BZ_1_BIZ_NUMBER_COMMON_UTILS_MOVE 20260522

## 1. 사용 도구와 모델
- 도구: Claude Code (VSCode extension)
- 모델: Claude Opus 4.7 (1M context)
- 작업 디렉터리: `mysuit-ocr/`

## 2. 작업 목적
`src/lib/bizNumber.ts`만 `src/common/utils/bizNumber.ts`로 이동.

bizNumber.ts는 사업자등록번호 normalize / checksum validate / OCR text
extraction helper로 순수 문자열 helper (자체 import 0, browser API 의존
없음). RunOCR/History/Test/autofill에서 공유되므로 common/utils로 정리.

- 본문 byte-identical 유지 (import path strip 후 동일, 단 bizNumber.ts는
  본래 import가 없으므로 raw 동등성).
- 6 importer는 import path만 보정: autofillEngine, RunOcrWorkspace,
  DetailHistoryView, TestWorkspace, test/core/extract, test/core/autofill.
- TestWorkspace + test/core는 import path-only 변경 (허용 범위).
- 다른 src/lib 파일(autofillEngine/restoreProfileStore/profiles/groundTruthStore/
  testsets/axios/version) 미이동.

## 3. 백업 파일
경로: `mysuit-ocr/backup/biz_number_common_utils_20260522_before_FRONTEND_BZ_1_BIZ_NUMBER_COMMON_UTILS_MOVE/`

| 파일 | bytes |
| --- | --- |
| `bizNumber.ts` | 2,964 |
| `autofillEngine.ts` | (pre-BZ-1) |
| `RunOcrWorkspace.tsx` | (pre-BZ-1) |
| `DetailHistoryView.tsx` | (pre-BZ-1) |
| `TestWorkspace.tsx` | (pre-BZ-1) |
| `test_core_extract.ts` | (pre-BZ-1) |
| `test_core_autofill.ts` | (pre-BZ-1) |
| 8 tmp 스크립트 (cs1/cs2/1a~1f) | (pre-BZ-1 patch) |

## 4. 이동 파일

| from | to | 방식 | 본문 변경 |
| --- | --- | --- | --- |
| `src/lib/bizNumber.ts` | `src/common/utils/bizNumber.ts` | `git mv` | byte-identical (leaf utility, no imports) |

## 5. 수정 파일 (import path 보정만)

| 파일 | before | after |
| --- | --- | --- |
| `src/lib/autofillEngine.ts` (line 1) | `./bizNumber` | `@/common/utils/bizNumber` |
| `src/components/runocr/RunOcrWorkspace.tsx` (line 39) | `@/lib/bizNumber` | `@/common/utils/bizNumber` |
| `src/components/history/ui/DetailHistoryView.tsx` (line 27) | `@/lib/bizNumber` | `@/common/utils/bizNumber` |
| `src/components/test/TestWorkspace.tsx` (line 4) | `@/lib/bizNumber` | `@/common/utils/bizNumber` |
| `src/components/test/core/extract.ts` (line 9) | `@/lib/bizNumber` | `@/common/utils/bizNumber` |
| `src/components/test/core/autofill.ts` (line 12) | `@/lib/bizNumber` | `@/common/utils/bizNumber` |

BZ-1 호환 patch 적용 (검사 의도 보존, 호환 확장만):
- `tmp/check_image_store_common_storage_move_cs1.mjs`: SIBLINGS에서 `bizNumber.ts` 제거.
- `tmp/check_history_store_common_storage_move_cs2.mjs`: 동일.
- `tmp/check_lib_*_1a~1f.mjs` 6건: 동일.

## 6. 핵심 변경 내용
- `src/common/utils/`에 `bizNumber.ts` 입주 (9번째 파일).
- 2개 핵심 export 모두 보존: `normalizeBizNumber`, `extractBizNumber`.
  - 내부 helper(`validateChecksum`, `applyCharFixes`, `OCR_CHAR_FIXES`)는
    private (export 없음) 그대로 유지.
- 자체 import 0건 유지 (leaf utility).
- React/React-DOM/window/document/localStorage/sessionStorage/indexedDB/
  navigator/fetch/storage/backend 의존 0건 (검증됨).
- src 운영 코드 잔존 `@/lib/bizNumber` / `../lib/bizNumber` /
  `../../lib/bizNumber` 문자열 0건.
- 5 lib sibling(autofillEngine/restoreProfileStore/profiles/groundTruthStore/
  testsets) 잔류 가드 통과.
- 6 importer logic byte-equivalent(import path strip 후) 확인 — TestWorkspace
  와 test/core도 import path-only 변경 확인.

## 7. common/utils ownership 확인
이동 후 `src/common/utils/` 구성 (9개):
- `ocrCanvasOps.ts` (5B)
- `ocrTableRegion.ts` (5C)
- `ocrResultFormatters.ts` (1A)
- `invoiceFieldLabels.ts` (1B)
- `markdownReportBuilder.ts` (1C)
- `cleanJsonBuilder.ts` (1D)
- `invoiceTableDisplay.ts` (1E)
- `structuredTableViewModel.ts` (1F)
- `bizNumber.ts` (BZ-1) — 신규

`src/common/` 도메인 폴더 4종(`ui/`, `utils/`, `types/`, `storage/`) 구성
유지. components/* 역의존 0건.

## 8. test 영역 import path-only 변경 확인
- `src/components/test/TestWorkspace.tsx`: import path 1줄만 변경
  (logic_unchanged_vs_backup PASS).
- `src/components/test/core/extract.ts`: import path 1줄만 변경 (PASS).
- `src/components/test/core/autofill.ts`: import path 1줄만 변경 (PASS).
- test flow / handler / state / JSX 변경 0건 (byte-equivalent).

## 9. static check 결과 (BZ-1 신규 스크립트)
- 파일: `tmp/check_biz_number_common_utils_move_bz1.mjs`
- 명령: `node tmp/check_biz_number_common_utils_move_bz1.mjs`
- 결과: **PASS** (28/28 checks, skippedBackupChecks=0, residuals=0)

검증 항목 요약:
- `new_util_exists` + `old_util_absent`
- 5 lib sibling 잔류 가드
- `TestWorkspace_present`, `test_core_dir_present`
- new_util purity: no imports / no components/* / no react / no react-dom /
  no browser APIs (window/document/localStorage/sessionStorage/indexedDB/
  navigator/fetch) / no storage import
- 2 required exports 보존
- new_util logic_unchanged_vs_backup (byte-identical)
- 6 importer new path
- 6 importer logic_unchanged_vs_backup (import path-only)
- residual scan (`@/lib/bizNumber`, `../lib/bizNumber`,
  `../../lib/bizNumber`) 0건

## 10. runner 결과

| # | runner | 결과 |
| --- | --- | --- |
| 1 | `npm run typecheck` | **PASS** (exit 0) |
| 2 | `npm run build` | **PASS** (exit 0) |
| 3 | `check_biz_number_common_utils_move_bz1` | **PASS** (28/28, 신규) |
| 4 | `check_table_view_model_v1_fixtures_js` | **PASS** (8/8) |
| 5 | `check_clean_json_v1_fixtures_js` | **PASS** (9/9) |
| 6 | `python markdown contract --check --phase post_BIZ_NUMBER_COMMON_UTILS_MOVE_20260522` | **PASS** (6/6) |
| 7 | `check_history_store_common_storage_move_cs2` | **PASS** (BZ-1 patch 적용) |
| 8 | `check_image_store_common_storage_move_cs1` | **PASS** (BZ-1 patch 적용) |
| 9 | `check_detail_history_view_ui_move_hr2` | **PASS** |
| 10 | `check_history_popup_ui_move_hr1` | **PASS** |
| 11 | `check_app_providers_layout_move_cc1` | **PASS** |
| 12 | `check_require_login_login_ui_move_cc2` | **PASS** |
| 13 | `check_validation_baseline_repair_1a` | **PASS** |
| 14–19 | `check_lib_*_1a~1f` (6개) | **PASS** (bizNumber sibling drop patch 6건) |
| 20–25 | `check_ocr_core_*_5a~5c` + `5d` + `5e` + `5f` | **PASS** |
| 26–27 | `check_template_right_panel_rename_6a/6b` | **PASS** |
| 28–29 | `check_runocr_request_boundary_2b/result_layout_3a` | **PASS** |

요약: 26개 노드 러너 + 1 파이썬 러너 + typecheck + build 전부 exit 0. PASS만
존재, FAIL 0건.

## 11. typecheck / build 결과
- `npm run typecheck` → **PASS** (exit 0)
- `npm run build` → **PASS** (exit 0)
- 로그:
  - `ocr-server/logs/codex_FRONTEND_BZ_1_BIZ_NUMBER_COMMON_UTILS_MOVE.out.log`
  - `ocr-server/logs/codex_FRONTEND_BZ_1_BIZ_NUMBER_COMMON_UTILS_MOVE.err.log`

## 12. known stderr noise
- `ESLint: nextVitals is not iterable` — 빌드 exit 0, non-blocking (사전
  기재된 known noise).

## 13. 남은 이슈
- `src/lib`에 잔존: `autofillEngine.ts`, `restoreProfileStore.ts`,
  `profiles.ts`, `groundTruthStore.ts`, `testsets.ts`, `axios.ts`,
  `version.ts` (별도 phase 대상).
- `src/common/utils/ocrResultFormatters.ts`가 여전히 `@/lib/autofillEngine`
  type-only import (1A부터 잔존; autofillEngine 별도 phase에서 해소 예정).
- `src/lib/profiles.ts` doc-comment `core/types.ts` 잔존 (cosmetic).

## 14. 다음 작업 제안
- **RS-1 `autorestore → restore` 폴더 정리 precheck**.
- **`restoreProfileStore` 별도 precheck**.
- **`autofillEngine` 별도 precheck** (1A 잔여 type-only 의존 해소 후보).
- TestWorkspace 구조 정리는 별도 사용자 확인 후 진행.
- HR/RS/CS/BZ 단계 마무리 후 Template table column definition feature
  precheck로 이행 가능.
