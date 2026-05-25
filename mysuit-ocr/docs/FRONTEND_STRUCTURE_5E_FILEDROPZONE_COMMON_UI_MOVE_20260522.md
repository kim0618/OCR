# FRONTEND_STRUCTURE_5E_FILEDROPZONE_COMMON_UI_MOVE 20260522

## 1. 사용 도구와 모델
- 도구: Claude Code (VSCode extension)
- 모델: Claude Opus 4.7 (1M context)
- 작업 디렉터리: `mysuit-ocr/`

## 2. 작업 목적
OcrCanvasPane → common/ui 이동을 위한 blocker 제거 micro-step.
`src/components/common/FileDropzone.tsx`만 `src/common/ui/FileDropzone.tsx`로
이동하여 drag/drop + hidden file picker shared UI를 도메인-중립 위치로 이전한다.

- `OcrCanvasPane.tsx`는 **이번 작업에서 이동하지 않는다** (다음 phase).
- props, drag/drop 로직, hidden input 로직, 스타일 로직, JSX 구조 등 본문은
  byte-identical 유지.
- 영향 받은 파일은 import path만 보정 (OcrCanvasPane, RunOcrWorkspace).
- React만 의존하는 shared UI 컴포넌트이므로 self-import 변경도 불필요.

## 3. 백업 파일
경로: `mysuit-ocr/backup/filedropzone_20260522_before_FRONTEND_STRUCTURE_5E_FILEDROPZONE_COMMON_UI_MOVE/`

| 파일 | bytes |
| --- | --- |
| `FileDropzone.tsx` | 3,645 |
| `OcrCanvasPane.tsx` | 52,652 |
| `RunOcrWorkspace.tsx` | 66,978 |

## 4. 이동 파일

| from | to | 방식 | 본문 변경 |
| --- | --- | --- | --- |
| `src/components/common/FileDropzone.tsx` | `src/common/ui/FileDropzone.tsx` | `git mv` | 본문 byte-identical. React 외 의존 없음, self-import 변경 불필요. |

## 5. 수정 파일 (import path 보정만)

| 파일 | before | after |
| --- | --- | --- |
| `src/components/ocr/OcrCanvasPane.tsx` | `../common/FileDropzone` | `../../common/ui/FileDropzone` |
| `src/components/runocr/RunOcrWorkspace.tsx` | `../common/FileDropzone` | `../../common/ui/FileDropzone` |

`src/components/common/`에는 `AppProviders.tsx`, `RequireLogin.tsx`가 그대로 남아 있다.

## 6. 핵심 변경 내용
- `src/common/ui/` 폴더 신규 생성 — OCR 도메인 외의 첫 shared UI 입주자.
- `FileDropzone` props(`onPickFile`, `accept`, `hasFile`, `children`,
  `fileInputRef`, `className`, `style`) 전부 보존, default export 식별자
  (`FileDropzone`) 유지.
- 새 파일은 `react`만 import. `components/*` 의존 0건. Template/RunOCR/test
  policy 의존 0건. `localStorage` 미사용.
- 모든 consumer는 새 경로 사용. src/ 전역 잔존 `components/common/FileDropzone`,
  `../common/FileDropzone`, `../../common/FileDropzone` 문자열 0건.
- `tmp/check_filedropzone_common_ui_move_5e.mjs` 신규 작성 — 26개 검증 항목,
  잔존 문자열 src 전역 스캔 및 OcrCanvasPane 비이동 가드 포함.

## 7. 이동하지 않은 파일 (계약 유지)
- `src/components/ocr/OcrCanvasPane.tsx` — 위치/내용 유지, import path만 변경.
- `src/components/runocr/RunOcrWorkspace.tsx` — 위치/내용 유지, import path만 변경.
- `src/components/common/AppProviders.tsx` — 완전 미수정 (FileDropzone과 무관).
- `src/components/common/RequireLogin.tsx` — 완전 미수정.
- `src/components/template/ui/OcrAnnotator.tsx`, `OcrRightPanel.tsx` — 완전 미수정.
- `src/components/runocr/ui/*`, `src/components/runocr/utils/*` — 완전 미수정.
- `src/components/test/TestWorkspace.tsx`, `src/components/test/core/*` — 완전 미수정.
- `src/common/types/ocr.ts`, `src/common/utils/ocrCanvasOps.ts`,
  `src/common/utils/ocrTableRegion.ts`, `src/components/template/utils/buildTemplateExportPayload.ts`
  — 유지.

## 8. common/ui boundary 확인
`src/common/ui/FileDropzone.tsx` 검증 (5E 스크립트):

| 항목 | 결과 |
| --- | --- |
| `from "components/*"` import | 없음 |
| `from "components/runocr/*"` / `template/*` / `test/*` | 없음 |
| `react` import | 있음 (`useRef`, `useState`) |
| `localStorage` 사용 | 없음 |
| 백업 대비 logic equivalence (path 제외) | 동일 |
| `export default function FileDropzone` | 보존 |
| props 7개(`onPickFile`/`accept`/`hasFile`/`children`/`fileInputRef`/`className`/`style`) | 전부 보존 |

## 9. OcrCanvasPane blocker 해소 여부
- **해소됨.** precheck에서 식별된 "FileDropzone이 components/common에 남아 있어
  OcrCanvasPane을 common/ui로 옮기지 못한다"는 blocker가 5E로 제거되었다.
- 다만 **OcrCanvasPane 자체는 본 step에서 이동하지 않는다.** 5E 검사는
  `OcrCanvasPane_not_moved_to_common_ui` 가드로 이를 명시적으로 확인한다.
- 다음 phase (가칭 5F)에서 OcrCanvasPane을 `src/common/ui/OcrCanvasPane.tsx`로
  옮기면 된다.

## 10. static check 결과 (5E 신규 스크립트)
- 파일: `tmp/check_filedropzone_common_ui_move_5e.mjs`
- 명령: `node tmp/check_filedropzone_common_ui_move_5e.mjs`
- 결과: **PASS** (26/26 checks, skippedBackupChecks=0, residuals=0)

## 11. runner 결과 (18개)

| # | runner | 결과 | 비고 |
| --- | --- | --- | --- |
| 1 | `npm run typecheck` | **PASS** (exit 0) | — |
| 2 | `npm run build` | **PASS** (exit 0) | known noise `ESLint: nextVitals is not iterable` |
| 3 | `node tmp/check_table_view_model_v1_fixtures_js.mjs` | **PASS** (8/8) | exit 0 |
| 4 | `node tmp/check_clean_json_v1_fixtures_js.mjs` | **PASS** (9/9) | exit 0 |
| 5 | `python tmp/codex_markdown_contract_fixture_lock.py --check --phase post_FILEDROPZONE_COMMON_UI_MOVE_20260522` | **PASS** (6/6) | overall PASS, exit 0 |
| 6 | `node tmp/check_runocr_formdata_keys_2a.mjs` | **PASS_WITH_SKIPPED_BACKUP** | historical 2A backup absent |
| 7 | `node tmp/check_runocr_request_boundary_2b.mjs` | **PASS** | exit 0 |
| 8 | `node tmp/check_runocr_response_mapping_boundary_2c.mjs` | **PASS_WITH_SKIPPED_BACKUP** | historical 2B backup absent |
| 9 | `node tmp/check_runocr_result_layout_boundary_3a.mjs` | **PASS** | exit 0 |
| 10 | `node tmp/check_runocr_doc_comments_3b.mjs` | **PASS_WITH_SKIPPED_BACKUP** | historical 3B backups absent |
| 11 | `node tmp/check_template_workspace_move_4a.mjs` | **PASS_WITH_SKIPPED_BACKUP** | historical 4A backup absent |
| 12 | `node tmp/check_template_editor_ui_move_4b.mjs` | **PASS_WITH_SKIPPED_BACKUP** | historical 4B backups absent |
| 13 | `node tmp/check_ocr_core_types_common_move_5a.mjs` | **PASS** | post-5B/5C/5D fallback 유지 |
| 14 | `node tmp/check_ocr_core_ops_common_move_5b.mjs` | **PASS** | post-5C/5D fallback 유지 |
| 15 | `node tmp/check_ocr_core_table_common_move_5c.mjs` | **PASS** | post-5D fallback 유지 |
| 16 | `node tmp/check_template_export_payload_move_5d.mjs` | **PASS** | 31/31 |
| 17 | `node tmp/check_filedropzone_common_ui_move_5e.mjs` | **PASS** | 26/26 |
| 18 | `node tmp/check_validation_baseline_repair_1a.mjs` | **PASS** | exit 0 |

요약: 15개 노드 러너 + 1 파이썬 러너 + typecheck + build 전부 exit 0. PASS 또는
PASS_WITH_SKIPPED_BACKUP만 존재, FAIL 0건. 본 5E 작업에서는 기존 검사 스크립트
어떤 것도 patch가 필요하지 않았다 (FileDropzone은 어떤 5A~5D 검사도 참조하지
않았기 때문).

## 12. typecheck / build 결과
- `npm run typecheck` → **PASS** (exit 0)
- `npm run build` → **PASS** (exit 0)
- 로그: `ocr-server/logs/codex_FRONTEND_STRUCTURE_5E_FILEDROPZONE_COMMON_UI_MOVE.out.log`,
  `ocr-server/logs/codex_FRONTEND_STRUCTURE_5E_FILEDROPZONE_COMMON_UI_MOVE.err.log`

## 13. known stderr noise
- `ESLint: nextVitals is not iterable` — 빌드 exit 0, non-blocking (사전 기재된 known noise).

## 14. 남은 이슈
- 과거 phase(2A/2B/3B/4A/4B)의 logic-equivalence 검사는 backup 파일 부재로
  `PASS_WITH_SKIPPED_BACKUP`로 처리되고 있다. 5E와 무관한 사전 상태.
- `src/components/ocr/` 디렉터리에는 `OcrCanvasPane.tsx`만 남아 있다.
  FileDropzone blocker는 해소되었으므로 다음 phase에서 자연스럽게 common/ui로
  옮길 수 있다.
- `src/lib/profiles.ts`의 doc-comment 문자열 `core/types.ts`는 5A 시점부터의
  잔존 (실제 import 아님, 동작 무영향, 후속 cleanup 후보).

## 15. 다음 작업 제안 (소단위 micro-step 권장)
- `OcrCanvasPane → common/ui` 이동 precheck 또는 실제 이동 (5F 후보). 5E로
  blocker가 해소되었으므로 정상적으로 진행 가능.
- Template table column definition 설계 precheck (canonical column mapping,
  사용자 확인 상태, 저장 payload 변환 등 신규 정책).
- TPL-95328E52 dirty 영향 precheck.
- `src/lib/profiles.ts` doc-comment 잔존 정리.
- TestWorkspace 정리는 사용자 확인 후 진행.
