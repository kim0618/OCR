# FRONTEND_CS_2_HISTORY_STORE_COMMON_STORAGE_MOVE 20260522

## 1. 사용 도구와 모델
- 도구: Claude Code (VSCode extension)
- 모델: Claude Opus 4.7 (1M context)
- 작업 디렉터리: `mysuit-ocr/`

## 2. 작업 목적
common storage boundary 정리의 두 번째 micro-step. `src/lib/historyStore.ts`만
`src/common/storage/historyStore.ts`로 이동하여 browser-side OCR history
persistence store(localStorage + IndexedDB image hydration)를 common/storage
도메인으로 정리.

- 본문 logic byte-equivalent 유지 (import path strip 후 동일).
- 내부 imageStore import는 sibling 형태 `./imageStore`로 보정 (alias →
  sibling, 단순 경로 변경).
- 5개 importer는 import path만 보정 (RunOcrWorkspace, HistoryWorkspace,
  DetailHistoryView, autofillEngine, groundTruthStore).
- imageStore/autofillEngine/restoreProfileStore/groundTruthStore/profiles/
  testsets/bizNumber 다른 파일은 미이동.
- TestWorkspace 미수정.

## 3. 백업 파일
경로: `mysuit-ocr/backup/history_store_common_storage_20260522_before_FRONTEND_CS_2_HISTORY_STORE_COMMON_STORAGE_MOVE/`

| 파일 | bytes |
| --- | --- |
| `historyStore.ts` | 31,819 |
| `RunOcrWorkspace.tsx` | 66,993 |
| `HistoryWorkspace.tsx` | (pre-CS-2) |
| `DetailHistoryView.tsx` | (pre-CS-2) |
| `autofillEngine.ts` | (pre-CS-2) |
| `groundTruthStore.ts` | (pre-CS-2) |
| `check_image_store_common_storage_move_cs1.mjs` | (pre-CS-2 patch) |
| `check_history_popup_ui_move_hr1.mjs` | (pre-CS-2 patch) |
| `check_detail_history_view_ui_move_hr2.mjs` | (pre-CS-2 patch) |
| `check_lib_ocr_result_formatters_common_move_1a.mjs` | (pre-CS-2 patch) |
| `check_lib_invoice_field_labels_common_move_1b.mjs` | (pre-CS-2 patch) |
| `check_lib_markdown_report_builder_common_move_1c.mjs` | (pre-CS-2 patch) |
| `check_lib_clean_json_builder_common_move_1d.mjs` | (pre-CS-2 patch) |
| `check_lib_invoice_table_display_common_move_1e.mjs` | (pre-CS-2 patch) |
| `check_lib_structured_table_view_model_common_move_1f.mjs` | (pre-CS-2 patch) |

## 4. 이동 파일

| from | to | 방식 | 본문 변경 |
| --- | --- | --- | --- |
| `src/lib/historyStore.ts` | `src/common/storage/historyStore.ts` | `git mv` | imageStore import path 1줄 변경 (`@/common/storage/imageStore` → `./imageStore`). 그 외 byte-identical. |

## 5. 수정 파일 (import path 보정만)

| 파일 | before | after |
| --- | --- | --- |
| `src/components/runocr/RunOcrWorkspace.tsx` (line 37) | `@/lib/historyStore` | `@/common/storage/historyStore` |
| `src/components/history/HistoryWorkspace.tsx` (line 9) | `@/lib/historyStore` | `@/common/storage/historyStore` |
| `src/components/history/ui/DetailHistoryView.tsx` (line 12) | `@/lib/historyStore` | `@/common/storage/historyStore` |
| `src/lib/autofillEngine.ts` (line 2) | `./historyStore` | `@/common/storage/historyStore` |
| `src/lib/groundTruthStore.ts` (line 5) | `./historyStore` | `@/common/storage/historyStore` |

CS-2 호환 patch 적용 (검사 로직 의도 보존, 호환 확장만):
- `tmp/check_image_store_common_storage_move_cs1.mjs`
  - HISTORY_STORE 경로 auto-detect (src/lib/ ↔ src/common/storage/).
  - SIBLINGS_THAT_MUST_STAY_IN_LIB에서 `historyStore.ts` 제거.
  - `history_store_imports_new_path`가 alias/sibling 모두 허용.
  - residual scan에서 `./imageStore`를 `src/common/storage/` 내부에서는 제외.
- `tmp/check_history_popup_ui_move_hr1.mjs`: HISTORY_STORE 경로 auto-detect.
- `tmp/check_detail_history_view_ui_move_hr2.mjs`
  - HISTORY_STORE 경로 auto-detect.
  - `new_detail_imports_historyStore`가 alias `@/lib/historyStore`와
    `@/common/storage/historyStore` 모두 허용.
- `tmp/check_lib_*_1a~1f.mjs` 6건: SIBLINGS_THAT_MUST_STAY_IN_LIB에서
  `historyStore.ts` 제거.

## 6. 핵심 변경 내용
- `src/common/storage/`에 `historyStore.ts` 입주, 같은 디렉터리의 sibling
  `imageStore.ts`와 정렬.
- historyStore의 18개 핵심 export 모두 보존: `RunStatus`, `HistoryOcrField`,
  `HistoryOutputField`, `HistoryRunRecord`, `HistoryDetailDocumentFields`,
  `readHistoryRuns`, `appendHistoryRun`, `updateHistoryRun`, `clearHistoryRuns`,
  `deleteHistoryRun`, `getOriginalHistoryImage`, `getProcessedHistoryImage`,
  `syncHistoryIndexAndDetailOnCreate`, `syncHistoryIndexAndDetailOnSave`,
  `syncHistoryDetailTableRowsOnSave`, `readHistoryListWithFallback`,
  `readHistoryDetailWithFallback`, `hydrateHistoryRecordImages`.
- localStorage key `mysuit_ocr_history` 정책 보존.
- IndexedDB image hydration 경로 보존 (`./imageStore` sibling).
- src/ 운영 코드 잔존 `@/lib/historyStore` / `../lib/historyStore` /
  `../../lib/historyStore` 문자열 0건.
- 6 lib sibling(autofillEngine/restoreProfileStore/profiles/groundTruthStore/
  testsets/bizNumber) 잔류 가드 통과.
- 5 importer logic byte-equivalent (import path strip 후) 확인.

## 7. common/storage ownership 확인
이동 후 `src/common/storage/` 구성:

| 파일 | 역할 |
| --- | --- |
| `imageStore.ts` (CS-1) | IndexedDB 기반 image persistence store |
| `historyStore.ts` (CS-2) | localStorage 기반 history persistence + image hydration |

`src/common/` 디렉터리는 `ui/`, `utils/`, `types/`, `storage/`의 4개 도메인
폴더 구성을 유지. components/* 역의존 0건 (검사가 명시적으로 확인).

## 8. imageStore sibling/import 관계 확인
- 이동된 `src/common/storage/historyStore.ts` 5번 줄: `./imageStore` sibling
  import. (이전 alias `@/common/storage/imageStore`에서 sibling 형태로 변경.)
- 외 다른 src 운영 코드의 imageStore import는 모두 alias
  `@/common/storage/imageStore` 형태 유지 (`template/page.tsx`,
  `RunOcrWorkspace.tsx`, `TemplateAnnotator.tsx`).
- `@/lib/imageStore` 잔존 0건.

## 9. TestWorkspace 미수정 확인
- `src/components/test/TestWorkspace.tsx` 미수정.
- `src/components/test/core/*` 미수정.
- TestWorkspace는 historyStore를 직접 import한 적 없음 (재확인).

## 10. static check 결과 (CS-2 신규 스크립트)
- 파일: `tmp/check_history_store_common_storage_move_cs2.mjs`
- 명령: `node tmp/check_history_store_common_storage_move_cs2.mjs`
- 결과: **PASS** (30/30 checks, skippedBackupChecks=0, residuals=0)

검증 항목 요약:
- `new_store_exists` + `old_store_absent`
- 6 lib sibling 잔류 가드 + `imageStore_still_in_common_storage`
- `TestWorkspace_present`, `test_core_dir_present`
- new_store purity (no components/*, no react, no react-dom)
- 18 required exports 보존
- `mysuit_ocr_history` localStorage key + localStorage 사용
- imageStore import (alias OR sibling) + `@/lib/imageStore` 잔존 부재
- new_store logic_unchanged_vs_backup
- 5 importer new path + 5 importer logic_unchanged_vs_backup
- residual scan (`@/lib/historyStore`, `../lib/historyStore`,
  `../../lib/historyStore`) 0건

## 11. runner 결과

| # | runner | 결과 |
| --- | --- | --- |
| 1 | `npm run typecheck` | **PASS** (exit 0) |
| 2 | `npm run build` | **PASS** (exit 0) |
| 3 | `check_table_view_model_v1_fixtures_js` | **PASS** (8/8) |
| 4 | `check_clean_json_v1_fixtures_js` | **PASS** (9/9) |
| 5 | `python markdown contract --check --phase post_HISTORY_STORE_COMMON_STORAGE_MOVE_20260522` | **PASS** (6/6) |
| 6 | `check_image_store_common_storage_move_cs1` | **PASS** (CS-2 patch 적용) |
| 7 | `check_history_store_common_storage_move_cs2` | **PASS** (30/30, 신규) |
| 8 | `check_detail_history_view_ui_move_hr2` | **PASS** (CS-2 patch 적용) |
| 9 | `check_history_popup_ui_move_hr1` | **PASS** (CS-2 patch 적용) |
| 10 | `check_app_providers_layout_move_cc1` | **PASS** |
| 11 | `check_require_login_login_ui_move_cc2` | **PASS** |
| 12 | `check_validation_baseline_repair_1a` | **PASS** |
| 13–18 | `check_lib_*_1a~1f` (6개) | **PASS** (historyStore sibling drop patch 6건) |
| 19–24 | `check_ocr_core_*_5a~5c` + `template_export_payload_5d` + `filedropzone_5e` + `ocr_canvas_pane_5f` | **PASS** |
| 25–26 | `check_template_right_panel_rename_6a/6b` | **PASS** |
| 27–28 | `check_runocr_request_boundary_2b/result_layout_3a` | **PASS** |

요약: 25개 노드 러너 + 1 파이썬 러너 + typecheck + build 전부 exit 0. PASS만
존재, FAIL 0건.

## 12. typecheck / build 결과
- `npm run typecheck` → **PASS** (exit 0)
- `npm run build` → **PASS** (exit 0)
- 로그:
  - `ocr-server/logs/codex_FRONTEND_CS_2_HISTORY_STORE_COMMON_STORAGE_MOVE.out.log`
  - `ocr-server/logs/codex_FRONTEND_CS_2_HISTORY_STORE_COMMON_STORAGE_MOVE.err.log`

## 13. known stderr noise
- `ESLint: nextVitals is not iterable` — 빌드 exit 0, non-blocking (사전
  기재된 known noise).

## 14. 남은 이슈
- `src/lib`에 잔존: `autofillEngine.ts`, `restoreProfileStore.ts`,
  `profiles.ts`, `groundTruthStore.ts`, `testsets.ts`, `bizNumber.ts`,
  `axios.ts`, `version.ts` 등 (별도 phase 대상).
- `src/common/utils/ocrResultFormatters.ts`가 여전히 `@/lib/autofillEngine`
  type-only import (1A부터 잔존; autofillEngine 별도 phase에서 해소 예정).
- `src/lib/profiles.ts` doc-comment 문자열 `core/types.ts` 잔존 (cosmetic).

## 15. 다음 작업 제안
- **RS-1 `autorestore → restore` 폴더 정리 precheck**.
- **`restoreProfileStore` 별도 precheck**.
- **`autofillEngine` 별도 precheck** (1A 잔여 type-only 의존 해소 후보).
- **`bizNumber → common/utils` precheck** (TestWorkspace 영향 확인 후).
- TestWorkspace 구조 정리는 별도 사용자 확인 후 진행.
- HR/RS/CS 단계 마무리 후 Template table column definition feature precheck로
  이행 가능.
