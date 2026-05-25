# FRONTEND_STRUCTURE_5B_OCR_CORE_OPS_COMMON_MOVE 20260522

## 1. 사용 도구와 모델
- 도구: Claude Code (VSCode extension)
- 모델: Claude Opus 4.7 (1M context)
- 작업 디렉터리: `mysuit-ocr/`

## 2. 작업 목적
OCR core ownership 정리의 두 번째 micro-step.
`src/components/ocr/core/ops.ts`만 `src/common/utils/ocrCanvasOps.ts`로 이동하여
OCR canvas/region operation helper를 도메인-중립 위치로 이전한다.

- `table.ts`, `export.ts`, `OcrCanvasPane.tsx`는 이동하지 않는다.
- 함수 이름·시그니처·본문은 변경하지 않는다 (logic byte-identical, import-path 제외).
- 영향 받은 파일에서는 import path만 보정한다.
- 5A에서 이미 `types.ts → common/types/ocr.ts` 이전 완료된 상태에서 진행.

## 3. 백업 파일
경로: `mysuit-ocr/backup/ocr_core_ops_20260522_before_FRONTEND_STRUCTURE_5B_OCR_CORE_OPS_COMMON_MOVE/`

| 파일 | bytes |
| --- | --- |
| `ops.ts` | 2,993 |
| `table.ts` | 4,899 |
| `export.ts` | 3,232 |
| `OcrCanvasPane.tsx` | 52,610 |
| `OcrRightPanel.tsx` | 24,472 |

## 4. 이동 파일

| from | to | 방식 | 본문 변경 |
| --- | --- | --- | --- |
| `src/components/ocr/core/ops.ts` | `src/common/utils/ocrCanvasOps.ts` | `git mv` | self-import 한 줄(`../../../common/types/ocr` → `../types/ocr`)만 깊이에 맞춰 보정. 함수 본문 전부 byte-identical. |

## 5. 수정 파일 (import path 보정만)

| 파일 | before | after |
| --- | --- | --- |
| `src/common/utils/ocrCanvasOps.ts` (이동된 본인) | `../../../common/types/ocr` | `../types/ocr` |
| `src/components/ocr/core/table.ts` | `./ops` | `../../../common/utils/ocrCanvasOps` |
| `src/components/ocr/core/export.ts` | `./ops` | `../../../common/utils/ocrCanvasOps` |
| `src/components/ocr/OcrCanvasPane.tsx` | `./core/ops` | `../../common/utils/ocrCanvasOps` |
| `src/components/template/ui/OcrRightPanel.tsx` | `../../ocr/core/ops` | `../../../common/utils/ocrCanvasOps` |

5A/5B 양쪽 상태에서 일관되도록 다음 tmp 스크립트의 regex를 보완(검사 로직 자체는 변경 없음):
- `tmp/check_template_editor_ui_move_4b.mjs` — `right_panel_imports_core_via_ocr`에 ops 경로 양쪽 허용.
- `tmp/check_ocr_core_types_common_move_5a.mjs` — `OPS` 경로 자동 탐지(post-5B fallback), `ops_imports_common_types`에 양쪽 import path 허용.

## 6. 핵심 변경 내용
- `src/common/utils/` 폴더 신규 생성.
- OCR canvas/region operation helper(`clamp`, `normalizeRect`, `uid`, `parseIndex`,
  `normalizeRatios`, `boxLabelStyle`, `calcMultiSubRegions`, `clampRectToArea`)가
  도메인-중립 위치 `common/utils/ocrCanvasOps.ts`로 이전.
- 모든 consumer는 새 경로를 import.
- `tmp/check_ocr_core_ops_common_move_5b.mjs` 신규 작성 — 25개 검증 항목, 잔여
  `./ops` / `../ops` / `ocr/core/ops` 문자열 src 전역 스캔 포함.

## 7. 이동하지 않은 파일 (계약 유지)
- `src/components/ocr/core/table.ts` — 위치/내용 유지, import path만 변경.
- `src/components/ocr/core/export.ts` — 위치/내용 유지, import path만 변경.
- `src/components/ocr/OcrCanvasPane.tsx` — 위치/내용 유지, import path만 변경.
- `src/components/template/ui/OcrRightPanel.tsx` — 위치/내용 유지, import path만 변경.
- `src/components/template/ui/OcrAnnotator.tsx` — 완전 미수정 (ops를 직접 사용하지 않음).
- `src/components/runocr/*` — 완전 미수정 (ops를 직접 사용하지 않음, OcrCanvasPane 경유 간접).
- `src/components/test/TestWorkspace.tsx`, `src/components/test/core/*` — 완전 미수정.
- `src/common/types/ocr.ts` (5A 결과물) — 유지.

## 8. common/utils boundary 확인
`src/common/utils/ocrCanvasOps.ts` 검증 (5B 스크립트가 직접 확인):

| 항목 | 결과 |
| --- | --- |
| `from "components/*"` import | 없음 |
| React runtime / `from "react-dom"` | 없음 (`CSSProperties` type-only react import만 사용 — 명시 허용 사항) |
| `window` / `document` / `localStorage` | 없음 |
| 타입 의존 (`Rect`,`Region`) | `../types/ocr`에서 type-only import |
| 백업 대비 logic equivalence (path 제외) | 동일 |
| 필수 함수 export 이름 | `clamp`,`normalizeRect`,`uid`,`parseIndex`,`normalizeRatios`,`boxLabelStyle`,`calcMultiSubRegions`,`clampRectToArea` 전부 보존 |
| src/ 전역 잔존 `./ops`, `../ops`, `ocr/core/ops` 문자열 | 0개 |

→ `common/utils/ocrCanvasOps.ts`는 `components/*`를 import하지 않으며 React/브라우저 런타임 의존이 없다.

## 9. static check 결과 (5B 신규 스크립트)
- 파일: `tmp/check_ocr_core_ops_common_move_5b.mjs`
- 명령: `node tmp/check_ocr_core_ops_common_move_5b.mjs`
- 결과: **PASS** (25/25 checks, skippedBackupChecks=0, residuals=0)

## 10. runner 결과 (15개)

| # | runner | 결과 | 비고 |
| --- | --- | --- | --- |
| 1 | `npm run typecheck` | **PASS** (exit 0) | — |
| 2 | `npm run build` | **PASS** (exit 0) | known noise `ESLint: nextVitals is not iterable` |
| 3 | `node tmp/check_table_view_model_v1_fixtures_js.mjs` | **PASS** (8/8) | exit 0 |
| 4 | `node tmp/check_clean_json_v1_fixtures_js.mjs` | **PASS** (9/9) | exit 0 |
| 5 | `python tmp/codex_markdown_contract_fixture_lock.py --check --phase post_OCR_CORE_OPS_COMMON_MOVE_20260522` | **PASS** (6/6) | overall PASS, exit 0 |
| 6 | `node tmp/check_runocr_formdata_keys_2a.mjs` | **PASS_WITH_SKIPPED_BACKUP** | historical 2A backup absent — skip with reason |
| 7 | `node tmp/check_runocr_request_boundary_2b.mjs` | **PASS** | exit 0 |
| 8 | `node tmp/check_runocr_response_mapping_boundary_2c.mjs` | **PASS_WITH_SKIPPED_BACKUP** | historical 2B backup absent |
| 9 | `node tmp/check_runocr_result_layout_boundary_3a.mjs` | **PASS** | exit 0 |
| 10 | `node tmp/check_runocr_doc_comments_3b.mjs` | **PASS_WITH_SKIPPED_BACKUP** | historical 3B backups absent |
| 11 | `node tmp/check_template_workspace_move_4a.mjs` | **PASS_WITH_SKIPPED_BACKUP** | historical 4A backup absent |
| 12 | `node tmp/check_template_editor_ui_move_4b.mjs` | **PASS_WITH_SKIPPED_BACKUP** | historical 4B backups absent + 5B ops 경로 양쪽 허용 패치 적용 |
| 13 | `node tmp/check_ocr_core_types_common_move_5a.mjs` | **PASS** | post-5B 경로 fallback 패치 적용 |
| 14 | `node tmp/check_ocr_core_ops_common_move_5b.mjs` | **PASS** | 25/25 |
| 15 | `node tmp/check_validation_baseline_repair_1a.mjs` | **PASS** | exit 0 |

요약: 12개 노드 러너 + 1 파이썬 러너 + typecheck + build 전부 exit 0. 모든 결과는
PASS 또는 PASS_WITH_SKIPPED_BACKUP. FAIL 0건.

## 11. typecheck / build 결과
- `npm run typecheck` → **PASS** (exit 0)
- `npm run build` → **PASS** (exit 0)
- 로그: `ocr-server/logs/codex_FRONTEND_STRUCTURE_5B_OCR_CORE_OPS_COMMON_MOVE.out.log`,
  `ocr-server/logs/codex_FRONTEND_STRUCTURE_5B_OCR_CORE_OPS_COMMON_MOVE.err.log`

## 12. known stderr noise
- `ESLint: nextVitals is not iterable` — 빌드 exit 0, non-blocking (사전 기재된 known noise).

## 13. 남은 이슈
- 과거 phase(2A/2B/3B/4A/4B)의 logic-equivalence 검사는 backup 파일 부재로 인해
  `PASS_WITH_SKIPPED_BACKUP`으로 처리되고 있다. 5B의 영향이 아닌 사전 상태.
- markdown contract fixture check가 이번 회차에서는 6/6 PASS로 회복.
- `src/lib/profiles.ts`의 doc-comment 문자열 `core/types.ts`는 5A 당시부터의
  잔존 (실제 import 아님, 동작 무영향, 후속 cleanup 후보).

## 14. 다음 작업 제안 (소단위 micro-step 권장)
- `table.ts → common/utils` 이동 precheck (Template table column definition 설계와 정합 검토).
- `export.ts → template/utils` 이동 precheck (Template 저장 payload 전용).
- `OcrCanvasPane → common/ui` 이동: core 의존 정리 이후 별도 phase로 진행.
- Template table column definition 설계 precheck.
- TPL-95328E52 dirty 영향 precheck.
- `src/lib/profiles.ts` doc-comment 잔존 정리.
- TestWorkspace 정리는 사용자 확인 후 진행.
