# FRONTEND_STRUCTURE_5C_OCR_CORE_TABLE_COMMON_MOVE 20260522

## 1. 사용 도구와 모델
- 도구: Claude Code (VSCode extension)
- 모델: Claude Opus 4.7 (1M context)
- 작업 디렉터리: `mysuit-ocr/`

## 2. 작업 목적
OCR core ownership 정리의 세 번째 micro-step.
`src/components/ocr/core/table.ts`만 `src/common/utils/ocrTableRegion.ts`로 이동하여
OCR table region primitive helper(`normalizeColGuides`, `buildTableRows`,
`normalizeStopKeywords`, `autoDetectRowBands`, `isStopRow`, type `OcrBox`)를
도메인-중립 위치로 이전한다.

- `export.ts`, `OcrCanvasPane.tsx`는 이동하지 않는다.
- 함수 이름·시그니처·본문은 변경하지 않는다 (logic byte-identical, self-import path 제외).
- 영향 받은 파일에서는 import path만 보정한다.
- Template table column definition 정책(canonical column mapping, 사용자 확인 상태,
  저장 payload 변환 등)은 이 step에서 구현하지 않는다.
- 5A에서 `types.ts → common/types/ocr.ts`, 5B에서 `ops.ts → common/utils/ocrCanvasOps.ts`
  완료된 상태에서 진행.

## 3. 백업 파일
경로: `mysuit-ocr/backup/ocr_core_table_20260522_before_FRONTEND_STRUCTURE_5C_OCR_CORE_TABLE_COMMON_MOVE/`

| 파일 | bytes |
| --- | --- |
| `table.ts` | 4,928 |
| `export.ts` | 3,261 |
| `OcrCanvasPane.tsx` | 52,631 |
| `OcrRightPanel.tsx` | 24,488 |

## 4. 이동 파일

| from | to | 방식 | 본문 변경 |
| --- | --- | --- | --- |
| `src/components/ocr/core/table.ts` | `src/common/utils/ocrTableRegion.ts` | `git mv` | self-import 두 줄만 깊이에 맞춰 보정. 함수 본문/타입 정의 전부 byte-identical. |

자세한 self-import 변경:

| import | before | after |
| --- | --- | --- |
| `Rect` from common/types | `../../../common/types/ocr` | `../types/ocr` |
| `clampRectToArea` from common/utils | `../../../common/utils/ocrCanvasOps` | `./ocrCanvasOps` |

## 5. 수정 파일 (import path 보정만)

| 파일 | before | after |
| --- | --- | --- |
| `src/components/ocr/core/export.ts` | `./table` | `../../../common/utils/ocrTableRegion` |
| `src/components/ocr/OcrCanvasPane.tsx` | `./core/table` | `../../common/utils/ocrTableRegion` |
| `src/components/template/ui/OcrRightPanel.tsx` | `../../ocr/core/table` | `../../../common/utils/ocrTableRegion` |

5A/5B/5C 양쪽 상태에서 일관되도록 다음 tmp 스크립트 보완 (검사 로직 자체 변경 없음, regex/경로 fallback만 추가):
- `tmp/check_template_editor_ui_move_4b.mjs` — `right_panel_imports_core_via_ocr`에 table 경로 양쪽 허용.
- `tmp/check_ocr_core_types_common_move_5a.mjs` — `TABLE` 경로 자동 탐지(post-5C fallback), `table_imports_common_types`에 양쪽 import path 허용.
- `tmp/check_ocr_core_ops_common_move_5b.mjs` — `TABLE` 경로 자동 탐지, `table_imports_common_utils`에 양쪽 import path 허용.

## 6. 핵심 변경 내용
- OCR table region primitive helper가 도메인-중립 `common/utils/ocrTableRegion.ts`로 이전.
- 모든 consumer는 새 경로를 import.
- `tmp/check_ocr_core_table_common_move_5c.mjs` 신규 작성 — 29개 검증 항목,
  잔여 `./table` / `../table` / `ocr/core/table` 문자열 src 전역 스캔 포함.
- Template table column definition 미구현 가드 포함:
  `src/components/template/utils/`, `TemplateTableColumnEditor.tsx` 미존재,
  새 table 파일 본문에 `canonicalColumn`, `mappingStatus`, `userConfirmed`,
  `savePayload`, `buildExportPayload` 어떤 식별자도 등장하지 않음.

## 7. 이동하지 않은 파일 (계약 유지)
- `src/components/ocr/core/export.ts` — 위치/내용 유지, import path만 변경.
- `src/components/ocr/OcrCanvasPane.tsx` — 위치/내용 유지, import path만 변경.
- `src/components/template/ui/OcrRightPanel.tsx` — 위치/내용 유지, import path만 변경.
- `src/components/template/ui/OcrAnnotator.tsx` — 완전 미수정 (table 직접 사용처 아님).
- `src/components/runocr/*` — 완전 미수정.
- `src/components/test/TestWorkspace.tsx`, `src/components/test/core/*` — 완전 미수정.
- `src/common/types/ocr.ts` (5A), `src/common/utils/ocrCanvasOps.ts` (5B) — 유지.

## 8. common/utils boundary 확인
`src/common/utils/ocrTableRegion.ts` 검증 (5C 스크립트가 직접 확인):

| 항목 | 결과 |
| --- | --- |
| `from "components/*"` import | 없음 |
| `from "react"` / `from "react-dom"` | 없음 |
| `window` / `document` / `localStorage` | 없음 |
| 타입 의존 (`Rect`) | `../types/ocr`에서 type-only import |
| 함수 의존 (`clampRectToArea`) | `./ocrCanvasOps`에서 sibling import |
| 백업 대비 logic equivalence (path 제외) | 동일 |
| 필수 export 이름 | `normalizeColGuides`, `buildTableRows`, `normalizeStopKeywords`, `autoDetectRowBands`, `isStopRow`, type `OcrBox` 전부 보존 |
| src/ 전역 잔존 `./table`, `../table`, `ocr/core/table` 문자열 | 0개 |

## 9. Template table column definition 미구현 확인
- `src/components/template/utils/` — 폴더 미생성.
- `src/components/template/ui/TemplateTableColumnEditor.tsx` — 파일 미생성.
- `common/utils/ocrTableRegion.ts` 본문 식별자 스캔: `canonicalColumn`,
  `mappingStatus`, `userConfirmed`, `savePayload`, `buildExportPayload` 모두 0건.
- 즉 canonical column mapping, 사용자 확인 상태, 저장 payload 변환 정책은 5C에서 일체 구현/이전하지 않았다.

## 10. static check 결과 (5C 신규 스크립트)
- 파일: `tmp/check_ocr_core_table_common_move_5c.mjs`
- 명령: `node tmp/check_ocr_core_table_common_move_5c.mjs`
- 결과: **PASS** (29/29 checks, skippedBackupChecks=0, residuals=0)

## 11. runner 결과 (16개)

| # | runner | 결과 | 비고 |
| --- | --- | --- | --- |
| 1 | `npm run typecheck` | **PASS** (exit 0) | — |
| 2 | `npm run build` | **PASS** (exit 0) | known noise `ESLint: nextVitals is not iterable` |
| 3 | `node tmp/check_table_view_model_v1_fixtures_js.mjs` | **PASS** (8/8) | exit 0 |
| 4 | `node tmp/check_clean_json_v1_fixtures_js.mjs` | **PASS** (9/9) | exit 0 |
| 5 | `python tmp/codex_markdown_contract_fixture_lock.py --check --phase post_OCR_CORE_TABLE_COMMON_MOVE_20260522` | **PASS** (6/6) | overall PASS, exit 0 |
| 6 | `node tmp/check_runocr_formdata_keys_2a.mjs` | **PASS_WITH_SKIPPED_BACKUP** | historical 2A backup absent — skip with reason |
| 7 | `node tmp/check_runocr_request_boundary_2b.mjs` | **PASS** | exit 0 |
| 8 | `node tmp/check_runocr_response_mapping_boundary_2c.mjs` | **PASS_WITH_SKIPPED_BACKUP** | historical 2B backup absent |
| 9 | `node tmp/check_runocr_result_layout_boundary_3a.mjs` | **PASS** | exit 0 |
| 10 | `node tmp/check_runocr_doc_comments_3b.mjs` | **PASS_WITH_SKIPPED_BACKUP** | historical 3B backups absent |
| 11 | `node tmp/check_template_workspace_move_4a.mjs` | **PASS_WITH_SKIPPED_BACKUP** | historical 4A backup absent |
| 12 | `node tmp/check_template_editor_ui_move_4b.mjs` | **PASS_WITH_SKIPPED_BACKUP** | 5C table 경로 양쪽 허용 패치 적용 |
| 13 | `node tmp/check_ocr_core_types_common_move_5a.mjs` | **PASS** | post-5C TABLE 경로 fallback 패치 적용 |
| 14 | `node tmp/check_ocr_core_ops_common_move_5b.mjs` | **PASS** | post-5C TABLE 경로 fallback 패치 적용 |
| 15 | `node tmp/check_ocr_core_table_common_move_5c.mjs` | **PASS** | 29/29 |
| 16 | `node tmp/check_validation_baseline_repair_1a.mjs` | **PASS** | exit 0 |

요약: 13개 노드 러너 + 1 파이썬 러너 + typecheck + build 전부 exit 0. PASS 또는
PASS_WITH_SKIPPED_BACKUP만 존재, FAIL 0건.

## 12. typecheck / build 결과
- `npm run typecheck` → **PASS** (exit 0)
- `npm run build` → **PASS** (exit 0)
- 로그: `ocr-server/logs/codex_FRONTEND_STRUCTURE_5C_OCR_CORE_TABLE_COMMON_MOVE.out.log`,
  `ocr-server/logs/codex_FRONTEND_STRUCTURE_5C_OCR_CORE_TABLE_COMMON_MOVE.err.log`

## 13. known stderr noise
- `ESLint: nextVitals is not iterable` — 빌드 exit 0, non-blocking (사전 기재된 known noise).

## 14. 남은 이슈
- 과거 phase(2A/2B/3B/4A/4B)의 logic-equivalence 검사는 backup 파일 부재로
  `PASS_WITH_SKIPPED_BACKUP`으로 처리되고 있다. 5C와 무관한 사전 상태.
- `src/components/ocr/core/`에는 이제 `export.ts` 한 파일만 남았다. 5D
  (`export.ts → template/utils`) 또는 의도적으로 core 폴더 유지 여부에 대한
  결정이 필요하다.
- `src/lib/profiles.ts`의 doc-comment 문자열 `core/types.ts`는 5A 시점부터의
  잔존 (실제 import 아님, 동작 무영향, 후속 cleanup 후보).

## 15. 다음 작업 제안 (소단위 micro-step 권장)
- `export.ts → template/utils` 이동 precheck 또는 실제 이동 (5D 후보).
- `OcrCanvasPane → common/ui` 이동은 export 의존 정리 이후 별도 phase로 진행.
- Template table column definition 설계 precheck (canonical mapping, 사용자
  확인 상태, 저장 payload 변환 등 — 별도 `components/template/utils/` layer로
  분리하는 것이 5C 정책의 연장선이다).
- TPL-95328E52 dirty 영향 precheck.
- `src/lib/profiles.ts` doc-comment 잔존 정리.
- TestWorkspace 정리는 사용자 확인 후 진행.
