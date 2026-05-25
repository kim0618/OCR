# FRONTEND_STRUCTURE_6A_TEMPLATE_RIGHT_PANEL_RENAME 20260522

## 1. 사용 도구와 모델
- 도구: Claude Code (VSCode extension)
- 모델: Claude Opus 4.7 (1M context)
- 작업 디렉터리: `mysuit-ocr/`

## 2. 작업 목적
Template editor 전용 right panel을 도메인-일치 이름으로 정리하는 rename
micro-step. `src/components/template/ui/OcrRightPanel.tsx`를
`src/components/template/ui/TemplateRightPanel.tsx`로 rename하고, default
component 식별자와 OcrAnnotator의 import/JSX tag도 좁게 보정한다.

- 기능/로직/JSX/state/handler/props 구조는 변경하지 않는다.
- props 필드/타입은 byte-identical 유지.
- Template table column definition 정책은 구현하지 않는다.
- OcrCanvasPane / FileDropzone / RunOCR / TestWorkspace 미수정.

## 3. 백업 파일
경로: `mysuit-ocr/backup/template_right_panel_20260522_before_FRONTEND_STRUCTURE_6A_TEMPLATE_RIGHT_PANEL_RENAME/`

| 파일 | bytes |
| --- | --- |
| `OcrRightPanel.tsx` | 24,504 |
| `OcrAnnotator.tsx` | 16,769 |

## 4. rename 파일

| from | to | 방식 | 본문 변경 |
| --- | --- | --- | --- |
| `src/components/template/ui/OcrRightPanel.tsx` | `src/components/template/ui/TemplateRightPanel.tsx` | `git mv` | 본문 byte-identical, `export default function OcrRightPanel` 한 줄만 `export default function TemplateRightPanel`로 변경. props 타입/필드/imports 변동 없음. |

## 5. 수정 파일 (import path + JSX tag만)

| 파일 | before | after |
| --- | --- | --- |
| `src/components/template/ui/OcrAnnotator.tsx` (import) | `import OcrRightPanel from "./OcrRightPanel";` | `import TemplateRightPanel from "./TemplateRightPanel";` |
| `src/components/template/ui/OcrAnnotator.tsx` (JSX tag) | `<OcrRightPanel ...>` | `<TemplateRightPanel ...>` |

OcrAnnotator의 다른 모든 코드(JSX 구조, props 전달, state, handler, 다른 import)는
byte-identical 유지.

기존 8개 검사에 post-6A 상태 허용 패치 적용 (검사 로직 자체 변경 없음, 경로
fallback / regex 양쪽 허용 / 식별자 normalize 확장):
- `tmp/check_template_workspace_move_4a.mjs` — `OcrRightPanel_untouched_path`에
  TemplateRightPanel 경로 허용 추가.
- `tmp/check_template_editor_ui_move_4b.mjs` — `NEW_RIGHT_PANEL` 경로 자동 탐지,
  `no_rename_TemplateRightPanel` 가드 완화 (post-6A 인정),
  `annotator_imports_right_panel_local`/`right_panel_export_name_preserved`에
  새 식별자 허용.
- `tmp/check_ocr_core_types_common_move_5a.mjs` — `RIGHT_PANEL` 경로 자동 탐지.
- `tmp/check_ocr_core_ops_common_move_5b.mjs` — `RIGHT_PANEL` 경로 자동 탐지,
  normalizer에 OcrRightPanel↔TemplateRightPanel 식별자 collapse + dynamic
  `import(...)` path stripping 추가.
- `tmp/check_ocr_core_table_common_move_5c.mjs` — 동일.
- `tmp/check_template_export_payload_move_5d.mjs` — `RIGHT_PANEL` 자동 탐지,
  normalizer에 식별자 collapse + dynamic import stripping 추가.
- `tmp/check_filedropzone_common_ui_move_5e.mjs` — `RIGHT_PANEL` 자동 탐지.
- `tmp/check_ocr_canvas_pane_common_ui_move_5f.mjs` — `RIGHT_PANEL` 자동 탐지,
  normalizer에 식별자 collapse 추가.

## 6. 수정하지 않은 파일 (계약 유지)
- `src/components/template/ui/OcrAnnotator.tsx`는 위치 보존, **import 1줄 +
  JSX tag 1줄만** 변경. 다른 로직/JSX/state/handler/import 전부 byte-identical.
- `src/common/ui/OcrCanvasPane.tsx`, `src/common/ui/FileDropzone.tsx` 완전 미수정.
- `src/common/types/ocr.ts`, `src/common/utils/ocrCanvasOps.ts`,
  `src/common/utils/ocrTableRegion.ts` 완전 미수정.
- `src/components/template/TemplateWorkspace.tsx`,
  `src/components/template/utils/buildTemplateExportPayload.ts` 완전 미수정.
- `src/components/runocr/*`, `src/components/runocr/ui/*`,
  `src/components/runocr/utils/*` 완전 미수정.
- `src/components/test/TestWorkspace.tsx`, `src/components/test/core/*` 완전 미수정.

## 7. rename boundary 확인
`src/components/template/ui/TemplateRightPanel.tsx` 검증 (6A 스크립트):

| 항목 | 결과 |
| --- | --- |
| `export default function TemplateRightPanel` | 보존 |
| 잔존 `OcrRightPanel` 식별자 | 없음 |
| 백업 대비 logic-equivalence (path + 식별자 rename collapse) | 동일 |
| props 16개(`imgRef`, `templateName`, `setTemplateName`, `documentType`, `setDocumentType`, `loaded`, `regions`, `setRegions`, `selectedId`, `setSelectedId`, `rowTemplateTargetId`, `setRowTemplateTargetId`, `colGuideTargetId`, `setColGuideTargetId`, `updateName`, `deleteRegion`) | 전부 보존 |
| Template policy 식별자(`canonicalColumn`/`userConfirmed`/`columnMappingStatus`/`columnCandidates`) | 0건 |
| src/ 전역 잔존 `OcrRightPanel` 문자열 | 0개 |

OcrAnnotator 검증:
- `import TemplateRightPanel from "./TemplateRightPanel";` 존재, 옛 `import
  OcrRightPanel`/`from "./OcrRightPanel"` 모두 부재.
- JSX에 `<TemplateRightPanel ...>` 존재, 옛 `<OcrRightPanel ...>` 부재.
- 백업 대비 logic-equivalence (path + 식별자 rename collapse) 동일.

## 8. static check 결과 (6A 신규 스크립트)
- 파일: `tmp/check_template_right_panel_rename_6a.mjs`
- 명령: `node tmp/check_template_right_panel_rename_6a.mjs`
- 결과: **PASS** (26/26 checks, skippedBackupChecks=0, residuals=0)

## 9. runner 결과 (20개)

| # | runner | 결과 | 비고 |
| --- | --- | --- | --- |
| 1 | `npm run typecheck` | **PASS** (exit 0) | — |
| 2 | `npm run build` | **PASS** (exit 0) | known noise `ESLint: nextVitals is not iterable` |
| 3 | `node tmp/check_table_view_model_v1_fixtures_js.mjs` | **PASS** (8/8) | exit 0 |
| 4 | `node tmp/check_clean_json_v1_fixtures_js.mjs` | **PASS** (9/9) | exit 0 |
| 5 | `python tmp/codex_markdown_contract_fixture_lock.py --check --phase post_TEMPLATE_RIGHT_PANEL_RENAME_20260522` | **PASS** (6/6) | overall PASS, exit 0 |
| 6 | `node tmp/check_runocr_formdata_keys_2a.mjs` | **PASS_WITH_SKIPPED_BACKUP** | historical 2A backup absent |
| 7 | `node tmp/check_runocr_request_boundary_2b.mjs` | **PASS** | exit 0 |
| 8 | `node tmp/check_runocr_response_mapping_boundary_2c.mjs` | **PASS_WITH_SKIPPED_BACKUP** | historical 2B backup absent |
| 9 | `node tmp/check_runocr_result_layout_boundary_3a.mjs` | **PASS** | exit 0 |
| 10 | `node tmp/check_runocr_doc_comments_3b.mjs` | **PASS_WITH_SKIPPED_BACKUP** | historical 3B backups absent |
| 11 | `node tmp/check_template_workspace_move_4a.mjs` | **PASS_WITH_SKIPPED_BACKUP** | post-6A RIGHT_PANEL fallback 적용 |
| 12 | `node tmp/check_template_editor_ui_move_4b.mjs` | **PASS_WITH_SKIPPED_BACKUP** | post-6A NEW_RIGHT_PANEL 자동 탐지 + 가드 완화 + 식별자 양쪽 허용 |
| 13 | `node tmp/check_ocr_core_types_common_move_5a.mjs` | **PASS** | post-6A RIGHT_PANEL 자동 탐지 |
| 14 | `node tmp/check_ocr_core_ops_common_move_5b.mjs` | **PASS** | post-6A RIGHT_PANEL 자동 탐지 + 식별자 collapse normalizer |
| 15 | `node tmp/check_ocr_core_table_common_move_5c.mjs` | **PASS** | post-6A RIGHT_PANEL 자동 탐지 + 식별자 collapse normalizer |
| 16 | `node tmp/check_template_export_payload_move_5d.mjs` | **PASS** | post-6A RIGHT_PANEL 자동 탐지 + 식별자 collapse normalizer |
| 17 | `node tmp/check_filedropzone_common_ui_move_5e.mjs` | **PASS** | post-6A RIGHT_PANEL 자동 탐지 |
| 18 | `node tmp/check_ocr_canvas_pane_common_ui_move_5f.mjs` | **PASS** | post-6A RIGHT_PANEL 자동 탐지 + 식별자 collapse normalizer |
| 19 | `node tmp/check_template_right_panel_rename_6a.mjs` | **PASS** | 26/26 |
| 20 | `node tmp/check_validation_baseline_repair_1a.mjs` | **PASS** | exit 0 |

요약: 17개 노드 러너 + 1 파이썬 러너 + typecheck + build 전부 exit 0. PASS 또는
PASS_WITH_SKIPPED_BACKUP만 존재, FAIL 0건.

## 10. typecheck / build 결과
- `npm run typecheck` → **PASS** (exit 0)
- `npm run build` → **PASS** (exit 0)
- 로그: `ocr-server/logs/codex_FRONTEND_STRUCTURE_6A_TEMPLATE_RIGHT_PANEL_RENAME.out.log`,
  `ocr-server/logs/codex_FRONTEND_STRUCTURE_6A_TEMPLATE_RIGHT_PANEL_RENAME.err.log`

## 11. known stderr noise
- `ESLint: nextVitals is not iterable` — 빌드 exit 0, non-blocking (사전 기재된 known noise).

## 12. 남은 이슈
- 과거 phase(2A/2B/3B)의 logic-equivalence 검사는 backup 파일 부재로
  `PASS_WITH_SKIPPED_BACKUP`로 처리되고 있다. 6A와 무관한 사전 상태.
- 4A/4B 검사도 backup 부재로 PASS_WITH_SKIPPED_BACKUP. 6A 패치는 backup 미존재
  레거시 항목을 새로 망가뜨리지 않았다.
- `src/components/template/ui/OcrAnnotator.tsx` 파일명은 도메인-적합한 위치이지만
  `Ocr-` prefix가 남아 있음. 후속 cleanup 후보.
- `src/lib/profiles.ts`의 doc-comment 문자열 `core/types.ts`는 5A 시점부터의
  잔존 (실제 import 아님, 동작 무영향).

## 13. 다음 작업 제안
- Template table column definition 설계 precheck (canonical column mapping,
  사용자 확인 상태, 저장 payload 변환 — 별도 `components/template/utils/`
  또는 store layer로 분리).
- TPL-95328E52 dirty 영향 precheck.
- `src/lib/profiles.ts` doc-comment 잔존 정리.
- Template structure close-out 리포트 (4A→4B→6A까지 누적된 Template 도메인
  정리 결과 요약).
- `OcrAnnotator → TemplateAnnotator` rename micro-step 검토 (이름이 위치와
  완전히 일치하도록).
- TestWorkspace 정리는 사용자 확인 후 진행.
