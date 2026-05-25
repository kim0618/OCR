# FRONTEND_STRUCTURE_5A_OCR_CORE_TYPES_COMMON_MOVE 20260522

## 1. 사용 도구와 모델
- 도구: Claude Code (VSCode extension)
- 모델: Claude Opus 4.7 (1M context)
- 작업 디렉터리: `C:\OCR\OCR\mysuit-ocr`

## 2. 작업 목적
OCR core ownership 정리의 첫 micro-step. `src/components/ocr/core/types.ts`만
`src/common/types/ocr.ts`로 이동하여 OCR 도메인의 공통 타입 위치를 안정화한다.

- `ops.ts`, `table.ts`, `export.ts`, `OcrCanvasPane.tsx`는 이동하지 않는다.
- 내부 타입 정의 내용은 변경하지 않는다 (logic byte-identical).
- 영향 받은 파일에서는 import path만 보정한다.
- 후속 단계에서 OcrCanvasPane common/ui 이동 작업을 진행하기 위한 선행 작업.

## 3. 백업 파일
경로: `mysuit-ocr/backup/ocr_core_types_20260522_before_FRONTEND_STRUCTURE_5A_OCR_CORE_TYPES_COMMON_MOVE/`

| 파일 | bytes |
| --- | --- |
| `types.ts` | 2,321 |
| `ops.ts` | 2,975 |
| `table.ts` | 4,881 |
| `export.ts` | 3,214 |
| `OcrCanvasPane.tsx` | 52,600 |
| `OcrAnnotator.tsx` | 16,741 |
| `OcrRightPanel.tsx` | 24,467 |
| `RunOcrWorkspace.tsx` | 66,973 |
| `buildOcrFormData.ts` | 2,185 |

## 4. 이동 파일

| from | to |
| --- | --- |
| `src/components/ocr/core/types.ts` | `src/common/types/ocr.ts` |

`git mv` 사용. 본문은 byte-identical 유지.

## 5. 수정 파일 (import path만 보정)

| 파일 | before | after |
| --- | --- | --- |
| `src/components/ocr/core/ops.ts` | `./types` | `../../../common/types/ocr` |
| `src/components/ocr/core/table.ts` | `./types` | `../../../common/types/ocr` |
| `src/components/ocr/core/export.ts` | `./types` | `../../../common/types/ocr` |
| `src/components/ocr/OcrCanvasPane.tsx` | `./core/types` | `../../common/types/ocr` |
| `src/components/template/ui/OcrAnnotator.tsx` | `../../ocr/core/types` | `../../../common/types/ocr` |
| `src/components/template/ui/OcrRightPanel.tsx` | `../../ocr/core/types` | `../../../common/types/ocr` |
| `src/components/runocr/RunOcrWorkspace.tsx` | `../ocr/core/types` | `../../common/types/ocr` |
| `src/components/runocr/utils/buildOcrFormData.ts` | `../../ocr/core/types` | `../../../common/types/ocr` |

각 파일의 변경 범위는 위 단일 import 라인뿐이며, 다른 코드(JSX/state/handler/로직)는 건드리지 않았다.

## 6. 핵심 변경 내용
- `src/common/types/` 폴더를 신규 생성.
- OCR 도메인의 공통 타입(`Region`, `FieldType`, `LoadedImage`, `Rect`, `TableMeta`,
  `TableColumnDef`, `FieldMappingCandidate`, `MappingStatus`, `CheckMode`,
  `DragKind`)을 `src/common/types/ocr.ts`로 이전.
- 모든 consumer는 새 경로를 import하며, 타입 이름/시그니처는 그대로 유지.
- `tmp/check_ocr_core_types_common_move_5a.mjs` 신규 작성 — 이동 사실/순수성/
  import 경로/타입 이름 보존 검증.
- `tmp/check_template_editor_ui_move_4b.mjs`의 두 regex
  (`annotator_imports_core_via_ocr`, `right_panel_imports_core_via_ocr`)는
  pre-5A 경로(`../../ocr/core/types`) 또는 post-5A 경로
  (`../../../common/types/ocr`) 둘 다 허용하도록 보완. 그 외 4B 검사 로직은
  변경 없음.

## 7. 이동하지 않은 파일 (계약 유지)
- `src/components/ocr/core/ops.ts` — 위치/내용 유지, import path만 변경.
- `src/components/ocr/core/table.ts` — 위치/내용 유지, import path만 변경.
- `src/components/ocr/core/export.ts` — 위치/내용 유지, import path만 변경.
- `src/components/ocr/OcrCanvasPane.tsx` — 위치/내용 유지, import path만 변경.
- `src/components/template/ui/OcrAnnotator.tsx` — 위치/내용 유지, import path만 변경.
- `src/components/template/ui/OcrRightPanel.tsx` — 위치/내용 유지, import path만 변경.
- `src/components/runocr/*` — 위치/내용 유지, 해당하는 두 파일만 import path 변경.
- `src/components/test/TestWorkspace.tsx`, `src/components/test/core/*` — 완전 미수정.

## 8. common/types boundary 확인
`src/common/types/ocr.ts` 검증 (5A 스크립트 자체에서 확인):

| 항목 | 결과 |
| --- | --- |
| `from "react"` import | 없음 |
| `from "components/*"` import | 없음 |
| `window` / `document` / `localStorage` 참조 | 없음 |
| 어떤 형태의 `import` 라인 | 0개 (순수 타입 모듈) |
| 백업 대비 logic equivalence (`normalizeForLogic`) | 동일 |
| 핵심 export 이름 보존 (`Region`, `FieldType`, ...) | 모두 보존 |

→ `common/types/ocr.ts`는 `components/*`를 import하지 않으며, React/브라우저 의존도 없다.

## 9. static check 결과 (5A 신규 스크립트)
- 파일: `tmp/check_ocr_core_types_common_move_5a.mjs`
- 명령: `node tmp/check_ocr_core_types_common_move_5a.mjs`
- 결과: **PASS** (29/29 checks)

검사 항목 요약:
- 새 경로 존재 / 옛 경로 부재 ✅
- core 형제 파일(`ops`,`table`,`export`)·`OcrCanvasPane`·`OcrAnnotator`·`OcrRightPanel` 위치 보존 ✅
- RunOCR / TestWorkspace / `test/core/types.ts` 위치 보존 ✅
- 새 타입 파일 순수성(no react/components/browser/import) ✅
- 백업과 logic-equivalence ✅
- 모든 importer에 새 import 경로 적용, 옛 경로 잔존 없음 ✅
- `ops`,`table`,`export` 본문 logic-equivalence (path 제외) ✅
- 필수 export 이름 보존 ✅

## 10. runner 결과

| # | runner | 결과 | 비고 |
| --- | --- | --- | --- |
| 3 | `node tmp/check_table_view_model_v1_fixtures_js.mjs` | **PASS** (8/8) | exit 0 |
| 4 | `node tmp/check_clean_json_v1_fixtures_js.mjs` | **PASS** (9/9) | exit 0 |
| 5 | `python tmp/codex_markdown_contract_fixture_lock.py --check --phase post_OCR_CORE_TYPES_COMMON_MOVE_20260522` | **FAIL** (0/6) | LF vs CRLF newline mismatch in backend response — pre-existing, unrelated to types move |
| 6 | `node tmp/check_runocr_formdata_keys_2a.mjs` | **FATAL (exit 2)** | backup file missing at `C:\OCR\OCR\backup\RunOcrWorkspace_20260522_before_FRONTEND_STRUCTURE_2A_*.tsx` — pre-existing |
| 7 | `node tmp/check_runocr_request_boundary_2b.mjs` | **PASS** | exit 0 |
| 8 | `node tmp/check_runocr_response_mapping_boundary_2c.mjs` | **FAIL** | single check `buildOcrFormData_unchanged_vs_2B_backup` — missing backup, pre-existing |
| 9 | `node tmp/check_runocr_result_layout_boundary_3a.mjs` | **PASS** | exit 0 |
| 10 | `node tmp/check_runocr_doc_comments_3b.mjs` | **FAIL** | 8 missing backup files — pre-existing |
| 11 | `node tmp/check_template_workspace_move_4a.mjs` | **FAIL** | `template_workspace_logic_unchanged_vs_backup` — missing backup, pre-existing |
| 12 | `node tmp/check_template_editor_ui_move_4b.mjs` | **FAIL** | 3 missing backup checks — pre-existing. 5A regression in `*_imports_core_via_ocr` was fixed by accepting either old or new types path |
| 13 | `node tmp/check_ocr_core_types_common_move_5a.mjs` | **PASS** | 29/29 checks |

요약: 5A가 직접 책임지는 검사는 모두 PASS. 그 외 FAIL 항목은 모두
`C:\OCR\OCR\backup\` 의 과거 phase backup 파일 부재(2A/2B/3B/4A/4B) 또는 백엔드
응답 CRLF/LF 차이(markdown contract) 때문이며, 본 작업 이전부터 동일한 사유로
실패하던 상태이다.

## 11. typecheck / build 결과
- `npm run typecheck` → **PASS** (exit 0)
- `npm run build` → **PASS** (exit 0)
- 로그: `C:/OCR/OCR/ocr-server/logs/codex_FRONTEND_STRUCTURE_5A_OCR_CORE_TYPES_COMMON_MOVE.out.log`,
  `.../codex_FRONTEND_STRUCTURE_5A_OCR_CORE_TYPES_COMMON_MOVE.err.log`

## 12. known stderr noise
- `ESLint: nextVitals is not iterable` — 빌드 exit 0, non-blocking (사전 기재된 known noise).

## 13. 남은 이슈
- `mysuit-ocr/../backup/` (즉 `C:\OCR\OCR\backup\`) 디렉터리 자체가 존재하지 않아
  과거 phase(2A, 2B, 3B, 4A, 4B)의 logic-equivalence 검사들이 일괄 실패하고 있다.
  → 본 작업의 직접적 결과가 아니라 사전 상태. 향후 phase 정리 시 별도 처리 필요.
- markdown contract fixture lock은 백엔드 응답이 LF, 기대 fixture가 CRLF인
  Windows-환경 차이로 6/6 FAIL. 본 5A 작업은 타입 위치만 옮긴 것이므로
  이 차이에 영향을 주지 않는다.
- `src/lib/profiles.ts`의 doc-comment 내부에 `core/types.ts` 문자열이 남아 있다.
  실제 import는 아니므로 코드 동작에는 영향 없음. 도큐멘트 갱신 여부는 후속
  작업에서 결정.

## 14. 다음 작업 제안 (소단위 micro-step 권장)
- `ops.ts`의 `common/utils` 이동 precheck 또는 실제 이동.
- `table.ts`의 `common/utils` 이동 precheck (Template table column definition
  설계와 함께 정밀 검토 필요).
- `export.ts`의 `template/utils` 이동 precheck (Template 저장 payload 전용).
- `OcrCanvasPane` common/ui 이동은 위 core 의존 정리 이후 진행.
- Template table column definition 설계 precheck.
- `C:\OCR\OCR\backup\` 누락 backup 복원 또는 과거 check 스크립트 정리.
- TestWorkspace 정리는 사용자 확인 후 진행.
