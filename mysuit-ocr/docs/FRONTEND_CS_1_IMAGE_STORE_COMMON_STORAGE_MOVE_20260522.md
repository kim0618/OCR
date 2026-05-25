# FRONTEND_CS_1_IMAGE_STORE_COMMON_STORAGE_MOVE 20260522

## 1. 사용 도구와 모델
- 도구: Claude Code (VSCode extension)
- 모델: Claude Opus 4.7 (1M context)
- 작업 디렉터리: `mysuit-ocr/`

## 2. 작업 목적
common storage boundary 정리의 첫 micro-step. `src/lib/imageStore.ts`만
`src/common/storage/imageStore.ts`로 이동하여 IndexedDB 기반 image
persistence store(History original/processed + Template 이미지 저장/조회/삭제)를
common/storage 도메인으로 정리.

- 본문/IndexedDB 정책(DB name `mysuit_ocr_images`, store name, version,
  key 정책) byte-identical 유지.
- 영향 받은 파일은 import path만 보정 (4곳: historyStore + template page +
  RunOcrWorkspace + TemplateAnnotator).
- historyStore는 import path-only 변경 (`./imageStore → @/common/storage/imageStore`).
- historyStore/autofillEngine/restoreProfileStore/groundTruthStore/profiles/testsets/bizNumber 등
  다른 src/lib 파일은 미이동.
- TestWorkspace 미수정.

## 3. 백업 파일
경로: `mysuit-ocr/backup/image_store_common_storage_20260522_before_FRONTEND_CS_1_IMAGE_STORE_COMMON_STORAGE_MOVE/`

| 파일 | bytes |
| --- | --- |
| `imageStore.ts` | 4,232 |
| `historyStore.ts` | 31,804 |
| `app_template_page.tsx` | 10,394 |
| `RunOcrWorkspace.tsx` | 66,993 |
| `TemplateAnnotator.tsx` | 16,789 |

## 4. 이동 파일

| from | to | 방식 | 본문 변경 |
| --- | --- | --- | --- |
| `src/lib/imageStore.ts` | `src/common/storage/imageStore.ts` | `git mv` | 본문 byte-identical. imageStore 내부에는 import 없음 (leaf storage helper). |

## 5. 수정 파일 (import path 보정만)

| 파일 | before | after |
| --- | --- | --- |
| `src/lib/historyStore.ts` (line 5) | `./imageStore` (relative sibling) | `@/common/storage/imageStore` |
| `src/app/template/page.tsx` (line 7) | `@/lib/imageStore` | `@/common/storage/imageStore` |
| `src/components/runocr/RunOcrWorkspace.tsx` (line 38) | `@/lib/imageStore` | `@/common/storage/imageStore` |
| `src/components/template/ui/TemplateAnnotator.tsx` (line 8) | `@/lib/imageStore` | `@/common/storage/imageStore` |

기존 8개 검사에 post-CS-1 상태 허용 patch 적용 (검사 로직 변경 없음, sibling
리스트에서 imageStore 제거 + IMAGE_STORE 자동 탐지):
- `tmp/check_lib_ocr_result_formatters_common_move_1a.mjs` — sibling 가드 drop.
- `tmp/check_lib_invoice_field_labels_common_move_1b.mjs` — 동일.
- `tmp/check_lib_markdown_report_builder_common_move_1c.mjs` — 동일.
- `tmp/check_lib_clean_json_builder_common_move_1d.mjs` — 동일.
- `tmp/check_lib_invoice_table_display_common_move_1e.mjs` — 동일.
- `tmp/check_lib_structured_table_view_model_common_move_1f.mjs` — 동일.
- `tmp/check_history_popup_ui_move_hr1.mjs` — IMAGE_STORE 경로 자동 탐지.
- `tmp/check_detail_history_view_ui_move_hr2.mjs` — IMAGE_STORE 경로 자동 탐지.

## 6. 핵심 변경 내용
- `src/common/storage/` 신규 디렉터리 입주 (common/ 하위 4번째 폴더:
  ui/utils/types에 이은 storage).
- imageStore 6개 핵심 export(`saveImage`, `getImage`, `deleteImagesFor`,
  `saveTemplateImage`, `getTemplateImage`, `deleteTemplateImage`) 전부 보존.
- IndexedDB DB name(`mysuit_ocr_images`) + store name + version + key 정책
  보존 (`saveImage`/`getImage`/`deleteImagesFor`/`saveTemplateImage`/...
  모두 동일 동작).
- src/ 운영 코드 잔존 `@/lib/imageStore` / `../lib/imageStore` /
  `./imageStore` 문자열 0건.
- 7개 lib sibling(historyStore/autofillEngine/restoreProfileStore/profiles/
  groundTruthStore/testsets/bizNumber) 잔류 가드 통과.
- CS-1 신규 static check 28개 항목 PASS.

## 7. common/storage ownership 확인
이동 후 `src/common/storage/` 구성:

| 파일 | 역할 |
| --- | --- |
| `imageStore.ts` (CS-1) | IndexedDB 기반 image persistence store (History/Template) |

`src/common/` 디렉터리는 이제 `ui/`, `utils/`, `types/`, `storage/`의 4개
도메인 폴더로 정리됨. components/* 역의존 0건 (검사가 명시적으로 확인).

## 8. historyStore import path-only 확인
- historyStore.ts 5줄 1줄만 변경 (`./imageStore → @/common/storage/imageStore`).
- CS-1 검사의 `history_store_logic_unchanged_vs_backup` (import path strip 후
  logic-equivalence) PASS — 다른 code/state/handler 변경 없음을 byte-equivalent로
  확인.

## 9. TestWorkspace 미수정 확인
- `src/components/test/TestWorkspace.tsx` 미수정.
- `src/components/test/core/*` 미수정.
- TestWorkspace는 imageStore를 직접 import한 적이 없음.

## 10. static check 결과 (CS-1 신규 스크립트)
- 파일: `tmp/check_image_store_common_storage_move_cs1.mjs`
- 명령: `node tmp/check_image_store_common_storage_move_cs1.mjs`
- 결과: **PASS** (28/28 checks, skippedBackupChecks=0, residuals=0)

## 11. runner 결과 (24개 + typecheck + build + markdown contract)

| # | runner | 결과 |
| --- | --- | --- |
| 1 | `npm run typecheck` | **PASS** (exit 0) |
| 2 | `npm run build` | **PASS** (exit 0) |
| 3 | `check_table_view_model_v1_fixtures_js` | **PASS** (8/8) |
| 4 | `check_clean_json_v1_fixtures_js` | **PASS** (9/9) |
| 5 | `python markdown contract --check --phase post_IMAGE_STORE_COMMON_STORAGE_MOVE_20260522` | **PASS** (6/6) |
| 6 | `check_detail_history_view_ui_move_hr2` | **PASS** (IMAGE_STORE 자동 탐지 patch) |
| 7 | `check_history_popup_ui_move_hr1` | **PASS** (IMAGE_STORE 자동 탐지 patch) |
| 8 | `check_app_providers_layout_move_cc1` | **PASS** |
| 9 | `check_require_login_login_ui_move_cc2` | **PASS** |
| 10 | `check_validation_baseline_repair_1a` | **PASS** |
| 11–16 | `check_lib_*_1a~1f` (6개) | **PASS** (imageStore sibling drop patch 6건) |
| 17–22 | `check_ocr_core_*_5a~5f` + `template_export_payload_5d` | **PASS** (6개) |
| 23–24 | `check_template_right_panel_rename_6a/6b` | **PASS** |
| 25–26 | `check_runocr_request_boundary_2b/result_layout_3a` | **PASS** |
| 27 | `check_image_store_common_storage_move_cs1` | **PASS** (28/28) |

요약: 24개 노드 러너 + 1 파이썬 러너 + typecheck + build 전부 exit 0. PASS만
존재, FAIL 0건.

## 12. typecheck / build 결과
- `npm run typecheck` → **PASS** (exit 0)
- `npm run build` → **PASS** (exit 0)
- 로그: `ocr-server/logs/codex_FRONTEND_CS_1_IMAGE_STORE_COMMON_STORAGE_MOVE.out.log`,
  `ocr-server/logs/codex_FRONTEND_CS_1_IMAGE_STORE_COMMON_STORAGE_MOVE.err.log`

## 13. known stderr noise
- `ESLint: nextVitals is not iterable` — 빌드 exit 0, non-blocking (사전 기재된 known noise).

## 14. 남은 이슈
- historyStore.ts는 여전히 src/lib에 있음 — CS-2 별도 phase 대상.
- autofillEngine/restoreProfileStore/groundTruthStore/profiles/testsets/bizNumber도 src/lib에 잔존.
- `common/utils/ocrResultFormatters.ts`가 여전히 `@/lib/autofillEngine`을
  type-only import (1A 시점부터, 후속 LIB phase에서 해소).
- `src/lib/profiles.ts`의 doc-comment 문자열 `core/types.ts`는 5A 시점부터의 잔존.

## 15. 다음 작업 제안
- **CS-2 `historyStore → common/storage` 이동 precheck 또는 실제 이동** (sibling import 패턴 정착).
- **RS-1 `autorestore → restore` 폴더 정리 precheck**.
- **`restoreProfileStore` 별도 precheck**.
- **`autofillEngine` 별도 precheck** (1A 남은 type-only 의존 해소 후보).
- **`bizNumber → common/utils` precheck** (TestWorkspace 영향 확인 후).
- TestWorkspace 구조 정리는 별도 사용자 확인 후 진행.
- HR/RS/CS 단계 마무리 후 Template table column definition feature precheck로 이행 가능.
