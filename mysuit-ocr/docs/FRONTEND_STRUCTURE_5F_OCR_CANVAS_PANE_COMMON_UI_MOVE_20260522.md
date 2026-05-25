# FRONTEND_STRUCTURE_5F_OCR_CANVAS_PANE_COMMON_UI_MOVE 20260522

## 1. 사용 도구와 모델
- 도구: Claude Code (VSCode extension)
- 모델: Claude Opus 4.7 (1M context)
- 작업 디렉터리: `mysuit-ocr/`

## 2. 작업 목적
Shared interactive OCR canvas를 common/ui로 정리하는 micro-step.
`src/components/ocr/OcrCanvasPane.tsx`만 `src/common/ui/OcrCanvasPane.tsx`로
이동하여, Template + RunOCR + 향후 다른 호출자가 공통으로 사용하는 canvas를
도메인-중립 위치로 옮긴다.

- props, JSX 구조, state, handler, canvas interaction 로직(region
  draw/move/resize/delete/duplicate/undo, multi split, table
  rowTemplate/colGuide, zoom/visible filtering 등)은 byte-identical 유지.
- 영향 받은 파일은 import path만 보정 — OcrAnnotator static import 1줄,
  RunOcrWorkspace dynamic import() 1줄.
- 5A/5B/5C/5D/5E에서 모든 의존이 common으로 정리되었으므로 OcrCanvasPane은
  자연스럽게 도메인-중립 위치로 옮길 수 있다.
- Template table column definition 정책은 구현하지 않는다.

## 3. 백업 파일
경로: `mysuit-ocr/backup/ocr_canvas_pane_20260522_before_FRONTEND_STRUCTURE_5F_OCR_CANVAS_PANE_COMMON_UI_MOVE/`

| 파일 | bytes |
| --- | --- |
| `OcrCanvasPane.tsx` | 52,658 |
| `OcrAnnotator.tsx` | 16,760 |
| `RunOcrWorkspace.tsx` | 66,984 |

## 4. 이동 파일

| from | to | 방식 | 본문 변경 |
| --- | --- | --- | --- |
| `src/components/ocr/OcrCanvasPane.tsx` | `src/common/ui/OcrCanvasPane.tsx` | `git mv` | self-import 4줄만 깊이에 맞춰 보정. 함수 본문/JSX/state/handler 전부 byte-identical. |

자세한 self-import 변경:

| import | before | after |
| --- | --- | --- |
| types (`DragKind`, `FieldType`, `LoadedImage`, `Rect`, `Region`) | `../../common/types/ocr` | `../types/ocr` |
| ops (`boxLabelStyle` 등) | `../../common/utils/ocrCanvasOps` | `../utils/ocrCanvasOps` |
| table (`buildTableRows`, `normalizeColGuides`) | `../../common/utils/ocrTableRegion` | `../utils/ocrTableRegion` |
| `FileDropzone` | `../../common/ui/FileDropzone` | `./FileDropzone` (sibling) |

## 5. 수정 파일 (import path 보정만)

| 파일 | before | after |
| --- | --- | --- |
| `src/components/template/ui/OcrAnnotator.tsx` | `../../ocr/OcrCanvasPane` (static import) | `../../../common/ui/OcrCanvasPane` |
| `src/components/runocr/RunOcrWorkspace.tsx` | `import("../ocr/OcrCanvasPane")` (dynamic) | `import("../../common/ui/OcrCanvasPane")` |

빈 `src/components/ocr/` 폴더는 자연 제거 (placeholder 파일 생성 없음).

기존 검사 7개에 양쪽 상태(`pre/post-5F`) 허용 패치 적용 (검사 로직 자체는 변경
없음, regex/fallback만 추가):
- `tmp/check_template_workspace_move_4a.mjs` — `OCR_CANVAS` 경로 자동 탐지.
- `tmp/check_template_editor_ui_move_4b.mjs` — `OCR_CANVAS` 자동 탐지,
  `annotator_imports_canvas_via_ocr`에 새 경로 허용.
- `tmp/check_ocr_core_types_common_move_5a.mjs` — `OCR_CANVAS` 자동 탐지,
  `canvas_imports_common_types`에 양쪽 경로 허용.
- `tmp/check_ocr_core_ops_common_move_5b.mjs` — `OCR_CANVAS` 자동 탐지,
  `canvas_imports_common_utils`에 양쪽 경로 허용.
- `tmp/check_ocr_core_table_common_move_5c.mjs` — `OCR_CANVAS` 자동 탐지,
  `canvas_imports_common_utils`에 양쪽 경로 허용.
- `tmp/check_template_export_payload_move_5d.mjs` — `OCR_CANVAS` 자동 탐지.
- `tmp/check_filedropzone_common_ui_move_5e.mjs` — `OCR_CANVAS` 자동 탐지,
  `OcrCanvasPane_not_moved_to_common_ui`를 informational로 완화,
  `canvas_imports_common_ui`에 sibling `./FileDropzone` 허용, normalizer에
  dynamic `import(...)` path stripping 추가.

## 6. 핵심 변경 내용
- `src/common/ui/OcrCanvasPane.tsx` 신규 생성 (이동 결과).
- 본문 byte-identical: drag/draw/move/resize/delete/duplicate/undo, multi
  split, table rowTemplate/colGuide, zoom/visible filtering, FileDropzone
  통합 로직 모두 그대로 유지.
- 새 파일은 `react`, `../types/ocr`, `../utils/ocrCanvasOps`,
  `../utils/ocrTableRegion`, `./FileDropzone`만 import. `components/*` 의존
  0건.
- src/ 전역 잔존 `../ocr/OcrCanvasPane` / `../../ocr/OcrCanvasPane` /
  `components/ocr/OcrCanvasPane` 문자열 0개 (정적/동적 import 모두 포함).
- `src/components/ocr/` 폴더 완전 제거 (이제 운영 파일 없음).
- `tmp/check_ocr_canvas_pane_common_ui_move_5f.mjs` 신규 작성 — 30개 검증
  항목, 잔존 정적/동적 import 문자열 src 전역 스캔, Template policy 가드,
  components/ocr 폴더 비어있음 검증, FileDropzone 미수정 검증 포함.

## 7. common/ui boundary 확인
`src/common/ui/OcrCanvasPane.tsx` 검증 (5F 스크립트):

| 항목 | 결과 |
| --- | --- |
| `from "components/*"` import | 없음 |
| `from "../types/ocr"` | 있음 |
| `from "../utils/ocrCanvasOps"` | 있음 |
| `from "../utils/ocrTableRegion"` | 있음 |
| `from "./FileDropzone"` | 있음 |
| `from "react"` | 있음 |
| `localStorage` 사용 | 없음 |
| 백업 대비 logic equivalence (path 제외) | 동일 |
| `export default function OcrCanvasPane` | 보존 |

## 8. components/ocr 폴더 상태
- 폴더 자체가 제거됨 (의미 없는 placeholder 파일 생성 없음).
- `src/components/`에는 이제 `autorestore/`, `common/`, `history/`,
  `layout/`, `login/`, `runocr/`, `template/`, `test/` 만 남는다.
- `src/components/common/`에는 `AppProviders.tsx`, `RequireLogin.tsx`만 남아
  있고 FileDropzone은 5E에서 이미 `src/common/ui/`로 옮겨졌다.

## 9. OcrCanvasPane 로직 미변경 확인
- `OcrCanvasPane` props/시그니처/JSX/state/handler 모두 보존
  (logic-equivalence vs backup PASS).
- 5F 검사의 `new_canvas_logic_unchanged_vs_backup`, OcrAnnotator/
  RunOcrWorkspace `*_logic_unchanged_vs_backup` 모두 PASS (path-stripped
  normalize 비교).
- Template policy blocklist 식별자(`canonicalColumn`, `userConfirmed`,
  `columnMappingStatus`, `columnCandidates`) 본문 등장 0건.

## 10. static check 결과 (5F 신규 스크립트)
- 파일: `tmp/check_ocr_canvas_pane_common_ui_move_5f.mjs`
- 명령: `node tmp/check_ocr_canvas_pane_common_ui_move_5f.mjs`
- 결과: **PASS** (30/30 checks, skippedBackupChecks=0, residuals=0)

## 11. runner 결과 (19개)

| # | runner | 결과 | 비고 |
| --- | --- | --- | --- |
| 1 | `npm run typecheck` | **PASS** (exit 0) | — |
| 2 | `npm run build` | **PASS** (exit 0) | known noise `ESLint: nextVitals is not iterable` |
| 3 | `node tmp/check_table_view_model_v1_fixtures_js.mjs` | **PASS** (8/8) | exit 0 |
| 4 | `node tmp/check_clean_json_v1_fixtures_js.mjs` | **PASS** (9/9) | exit 0 |
| 5 | `python tmp/codex_markdown_contract_fixture_lock.py --check --phase post_OCR_CANVAS_PANE_COMMON_UI_MOVE_20260522` | **PASS** (6/6) | overall PASS, exit 0 |
| 6 | `node tmp/check_runocr_formdata_keys_2a.mjs` | **PASS_WITH_SKIPPED_BACKUP** | historical 2A backup absent |
| 7 | `node tmp/check_runocr_request_boundary_2b.mjs` | **PASS** | exit 0 |
| 8 | `node tmp/check_runocr_response_mapping_boundary_2c.mjs` | **PASS_WITH_SKIPPED_BACKUP** | historical 2B backup absent |
| 9 | `node tmp/check_runocr_result_layout_boundary_3a.mjs` | **PASS** | exit 0 |
| 10 | `node tmp/check_runocr_doc_comments_3b.mjs` | **PASS_WITH_SKIPPED_BACKUP** | historical 3B backups absent |
| 11 | `node tmp/check_template_workspace_move_4a.mjs` | **PASS_WITH_SKIPPED_BACKUP** | post-5F OCR_CANVAS fallback 패치 적용 |
| 12 | `node tmp/check_template_editor_ui_move_4b.mjs` | **PASS_WITH_SKIPPED_BACKUP** | post-5F OCR_CANVAS + annotator import path 양쪽 허용 |
| 13 | `node tmp/check_ocr_core_types_common_move_5a.mjs` | **PASS** | post-5F OCR_CANVAS + canvas import 양쪽 허용 |
| 14 | `node tmp/check_ocr_core_ops_common_move_5b.mjs` | **PASS** | post-5F OCR_CANVAS + canvas import 양쪽 허용 |
| 15 | `node tmp/check_ocr_core_table_common_move_5c.mjs` | **PASS** | post-5F OCR_CANVAS + canvas import 양쪽 허용 |
| 16 | `node tmp/check_template_export_payload_move_5d.mjs` | **PASS** | post-5F OCR_CANVAS fallback 패치 적용 |
| 17 | `node tmp/check_filedropzone_common_ui_move_5e.mjs` | **PASS** | post-5F OCR_CANVAS + sibling FileDropzone 허용 + dynamic-import path stripping |
| 18 | `node tmp/check_ocr_canvas_pane_common_ui_move_5f.mjs` | **PASS** | 30/30 |
| 19 | `node tmp/check_validation_baseline_repair_1a.mjs` | **PASS** | exit 0 |

요약: 16개 노드 러너 + 1 파이썬 러너 + typecheck + build 전부 exit 0. PASS 또는
PASS_WITH_SKIPPED_BACKUP만 존재, FAIL 0건.

## 12. typecheck / build 결과
- `npm run typecheck` → **PASS** (exit 0)
- `npm run build` → **PASS** (exit 0)
- 로그: `ocr-server/logs/codex_FRONTEND_STRUCTURE_5F_OCR_CANVAS_PANE_COMMON_UI_MOVE.out.log`,
  `ocr-server/logs/codex_FRONTEND_STRUCTURE_5F_OCR_CANVAS_PANE_COMMON_UI_MOVE.err.log`

## 13. known stderr noise
- `ESLint: nextVitals is not iterable` — 빌드 exit 0, non-blocking (사전 기재된 known noise).

## 14. 남은 이슈
- 과거 phase(2A/2B/3B/4A/4B)의 logic-equivalence 검사는 backup 파일 부재로
  `PASS_WITH_SKIPPED_BACKUP`로 처리되고 있다. 5F와 무관한 사전 상태.
- `src/components/ocr/` 폴더는 5F로 완전히 제거됨. 이제 `src/components/`에는
  OCR 도메인 전용 디렉터리가 남아 있지 않다.
- `src/lib/profiles.ts`의 doc-comment 문자열 `core/types.ts`는 5A 시점부터의
  잔존 (실제 import 아님, 동작 무영향, 후속 cleanup 후보).
- `src/components/template/ui/OcrRightPanel.tsx`는 OCR 명칭이지만 위치는
  Template 도메인. 다음 phase에서 `TemplateRightPanel`로 rename 고려 가능.

## 15. 다음 작업 제안 (소단위 micro-step 권장)
- Template table column definition 설계 precheck (canonical column mapping,
  사용자 확인 상태, 저장 payload 변환 등 신규 정책 — 별도
  `components/template/utils/` 또는 store layer로 분리).
- TPL-95328E52 dirty 영향 precheck.
- `src/lib/profiles.ts` doc-comment 잔존 정리.
- `OcrRightPanel → TemplateRightPanel` rename micro-step (이름이
  Template-도메인 위치와 일치하지 않는 잔존).
- TestWorkspace 정리는 사용자 확인 후 진행.
