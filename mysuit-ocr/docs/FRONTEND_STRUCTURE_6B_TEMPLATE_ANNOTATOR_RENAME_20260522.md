# FRONTEND_STRUCTURE_6B_TEMPLATE_ANNOTATOR_RENAME 20260522

## 1. 사용 도구와 모델
- 도구: Claude Code (VSCode extension)
- 모델: Claude Opus 4.7 (1M context)
- 작업 디렉터리: `mysuit-ocr/`

## 2. 작업 목적
Template editor 전용 annotator 파일명을 도메인-일치 이름으로 정리하는
rename-only micro-step. `src/components/template/ui/OcrAnnotator.tsx`를
`src/components/template/ui/TemplateAnnotator.tsx`로 rename하고, default
component 식별자와 `/ocr`, `/template` route의 dynamic import local
symbol/path/JSX tag를 함께 좁게 보정한다.

- 기능/로직/JSX/state/handler/props 구조는 변경하지 않는다.
- props 필드/타입은 byte-identical 유지.
- route policy(`/ocr`의 list/editor mode branching, `/template`의
  `UnstructuredBuilder` 사용)는 변경하지 않는다.
- Template table column definition 정책은 구현하지 않는다.
- OcrCanvasPane, FileDropzone, TemplateRightPanel, RunOCR, TestWorkspace 미수정.

## 3. 백업 파일
경로: `mysuit-ocr/backup/template_annotator_20260522_before_FRONTEND_STRUCTURE_6B_TEMPLATE_ANNOTATOR_RENAME/`

| 파일 | bytes |
| --- | --- |
| `OcrAnnotator.tsx` | 16,784 |
| `app_ocr_page.tsx` | 1,283 |
| `app_template_page.tsx` | 10,379 |

## 4. rename 파일

| from | to | 방식 | 본문 변경 |
| --- | --- | --- | --- |
| `src/components/template/ui/OcrAnnotator.tsx` | `src/components/template/ui/TemplateAnnotator.tsx` | `git mv` | 본문 byte-identical, `export default function OcrAnnotator` 한 줄만 `export default function TemplateAnnotator`로 변경. props 타입/필드/모든 import/state/handler/JSX 보존. |

## 5. 수정 파일 (import path + symbol + JSX tag만)

| 파일 | before | after |
| --- | --- | --- |
| `src/app/ocr/page.tsx` (dynamic import) | `const OcrAnnotator = dynamic(() => import("../../components/template/ui/OcrAnnotator"), ...)` | `const TemplateAnnotator = dynamic(() => import("../../components/template/ui/TemplateAnnotator"), ...)` |
| `src/app/ocr/page.tsx` (JSX) | `<OcrAnnotator />` | `<TemplateAnnotator />` |
| `src/app/template/page.tsx` (dynamic import) | `const OcrAnnotator = dynamic(() => import("../../components/template/ui/OcrAnnotator"), ...)` | `const TemplateAnnotator = dynamic(() => import("../../components/template/ui/TemplateAnnotator"), ...)` |
| `src/app/template/page.tsx` (JSX) | `<OcrAnnotator ...>` | `<TemplateAnnotator ...>` |

route policy(mode branching/AppShell/UnstructuredBuilder branch 등)는 그대로 유지.

## 6. import/symbol 수정 내용 + 기존 검사 패치
- 본 작업이 직접 수정한 파일은 3개 (TemplateAnnotator.tsx + 2 route 페이지).
- 기존 9개 검사에 post-6B 상태 허용 패치 적용 (검사 로직 자체 변경 없음, 경로
  fallback / regex 양쪽 허용 / 식별자 normalize 확장):
  - `tmp/check_template_workspace_move_4a.mjs` — `OcrAnnotator_untouched_path`에
    TemplateAnnotator 경로 fallback 추가.
  - `tmp/check_template_editor_ui_move_4b.mjs` — `NEW_ANNOTATOR` 경로 자동 탐지,
    `ocr_route_imports_new` / `template_route_imports_new` / `ocr_route_policy_intact` /
    `template_route_policy_intact` / `annotator_export_name_preserved`에 새 식별자/경로 허용.
  - `tmp/check_ocr_core_types_common_move_5a.mjs` — `ANNOTATOR` 경로 자동 탐지.
  - `tmp/check_ocr_core_ops_common_move_5b.mjs` — `ANNOTATOR` 경로 자동 탐지.
  - `tmp/check_ocr_core_table_common_move_5c.mjs` — `ANNOTATOR` 경로 자동 탐지.
  - `tmp/check_template_export_payload_move_5d.mjs` — `ANNOTATOR` 경로 자동 탐지 +
    normalizer에 OcrAnnotator↔TemplateAnnotator 식별자 collapse 추가.
  - `tmp/check_filedropzone_common_ui_move_5e.mjs` — `ANNOTATOR` 경로 자동 탐지.
  - `tmp/check_ocr_canvas_pane_common_ui_move_5f.mjs` — `ANNOTATOR` 경로 자동 탐지 +
    normalizer에 식별자 collapse 추가.
  - `tmp/check_template_right_panel_rename_6a.mjs` — `ANNOTATOR` 경로 자동 탐지 +
    rename normalizer에 OcrAnnotator/TemplateAnnotator collapse 추가.

## 7. 수정하지 않은 파일 (계약 유지)
- `src/common/ui/OcrCanvasPane.tsx` — doc-comment에 "OcrAnnotator" 단어가
  3곳(46/229/859줄) 나오지만 모두 자유서술 주석(임포트/식별자 아님). 본 작업은
  수정 금지 파일이므로 그대로 둔다. 6B 검사는 `stripComments` 후 잔존 검색으로
  주석을 제외한다.
- `src/common/ui/FileDropzone.tsx`, `src/common/types/ocr.ts`,
  `src/common/utils/ocrCanvasOps.ts`, `src/common/utils/ocrTableRegion.ts` 완전 미수정.
- `src/components/template/ui/TemplateRightPanel.tsx`,
  `src/components/template/TemplateWorkspace.tsx`,
  `src/components/template/utils/buildTemplateExportPayload.ts` 완전 미수정.
- `src/components/runocr/*`, `src/components/runocr/ui/*`,
  `src/components/runocr/utils/*` 완전 미수정.
- `src/components/test/TestWorkspace.tsx`, `src/components/test/core/*` 완전 미수정.

## 8. current dirty diff 확인 결과
- 작업 전 `OcrAnnotator.tsx`에는 5A/5D/5F + 6A 누적 import-path 변경만 dirty
  상태로 존재 (코드/JSX/state 변경 없음, +5/-5 라인). 본 6B 작업의 rename-only
  scope에 자연스럽게 흡수됨 — 별도 원복 불필요.
- 다른 dirty 파일들(runocr/* 등)은 직전 phase들이 이미 commit 대기 중인 import
  보정으로, 6B 범위 외 작업이 섞이지 않았다.

## 9. route policy 유지 여부
- `/ocr/page.tsx` — `mode === "editor"` 분기 + `TemplateWorkspace` list-mode +
  Suspense + AppShell 구조 모두 보존.
- `/template/page.tsx` — `Mode` 타입(`template` / `unstructured`),
  `UnstructuredBuilder` 분기, savedTemplates rendering, tooltip 모두 보존.
- 6B 검사의 `ocr_route_policy_intact` / `template_route_policy_intact` 가드가
  명시적으로 확인.

## 10. rename boundary 확인
`src/components/template/ui/TemplateAnnotator.tsx` 검증 (6B 스크립트):

| 항목 | 결과 |
| --- | --- |
| `export default function TemplateAnnotator` | 보존 |
| 잔존 `OcrAnnotator` 식별자 (본 파일) | 없음 |
| 백업 대비 logic-equivalence (path + 식별자 rename collapse) | 동일 |
| Template policy 식별자(`canonicalColumn`/`userConfirmed`/`columnMappingStatus`/`columnCandidates`) | 0건 |
| src/ 운영 코드(주석 제외) 전역 잔존 `OcrAnnotator` 식별자 | 0개 |
| src/ 전역 잔존 `components/(ocr\|template/ui)/OcrAnnotator` 경로 문자열 | 0개 |

route 페이지 검증:
- `/ocr/page.tsx`: `const TemplateAnnotator = dynamic(...import("../../components/template/ui/TemplateAnnotator")...)` + `<TemplateAnnotator />`, 옛 식별자/경로 부재. 백업 대비 logic-equivalence(rename collapse) 동일.
- `/template/page.tsx`: 동일 패턴, 옛 식별자/경로 부재. 백업 대비 logic-equivalence 동일.

## 11. static check 결과 (6B 신규 스크립트)
- 파일: `tmp/check_template_annotator_rename_6b.mjs`
- 명령: `node tmp/check_template_annotator_rename_6b.mjs`
- 결과: **PASS** (34/34 checks, skippedBackupChecks=0, residuals=0)

## 12. runner 결과 (21개)

| # | runner | 결과 | 비고 |
| --- | --- | --- | --- |
| 1 | `npm run typecheck` | **PASS** (exit 0) | — |
| 2 | `npm run build` | **PASS** (exit 0) | known noise `ESLint: nextVitals is not iterable` |
| 3 | `node tmp/check_table_view_model_v1_fixtures_js.mjs` | **PASS** (8/8) | exit 0 |
| 4 | `node tmp/check_clean_json_v1_fixtures_js.mjs` | **PASS** (9/9) | exit 0 |
| 5 | `python tmp/codex_markdown_contract_fixture_lock.py --check --phase post_TEMPLATE_ANNOTATOR_RENAME_20260522` | **PASS** (6/6) | overall PASS, exit 0 |
| 6 | `node tmp/check_runocr_formdata_keys_2a.mjs` | **PASS_WITH_SKIPPED_BACKUP** | historical 2A backup absent |
| 7 | `node tmp/check_runocr_request_boundary_2b.mjs` | **PASS** | exit 0 |
| 8 | `node tmp/check_runocr_response_mapping_boundary_2c.mjs` | **PASS_WITH_SKIPPED_BACKUP** | historical 2B backup absent |
| 9 | `node tmp/check_runocr_result_layout_boundary_3a.mjs` | **PASS** | exit 0 |
| 10 | `node tmp/check_runocr_doc_comments_3b.mjs` | **PASS_WITH_SKIPPED_BACKUP** | historical 3B backups absent |
| 11 | `node tmp/check_template_workspace_move_4a.mjs` | **PASS_WITH_SKIPPED_BACKUP** | post-6B ANNOTATOR fallback 적용 |
| 12 | `node tmp/check_template_editor_ui_move_4b.mjs` | **PASS_WITH_SKIPPED_BACKUP** | post-6B NEW_ANNOTATOR 자동 탐지 + route 정책/식별자 양쪽 허용 |
| 13 | `node tmp/check_ocr_core_types_common_move_5a.mjs` | **PASS** | post-6B ANNOTATOR 자동 탐지 |
| 14 | `node tmp/check_ocr_core_ops_common_move_5b.mjs` | **PASS** | post-6B ANNOTATOR 자동 탐지 |
| 15 | `node tmp/check_ocr_core_table_common_move_5c.mjs` | **PASS** | post-6B ANNOTATOR 자동 탐지 |
| 16 | `node tmp/check_template_export_payload_move_5d.mjs` | **PASS** | post-6B ANNOTATOR 자동 탐지 + 식별자 collapse |
| 17 | `node tmp/check_filedropzone_common_ui_move_5e.mjs` | **PASS** | post-6B ANNOTATOR 자동 탐지 |
| 18 | `node tmp/check_ocr_canvas_pane_common_ui_move_5f.mjs` | **PASS** | post-6B ANNOTATOR 자동 탐지 + 식별자 collapse |
| 19 | `node tmp/check_template_right_panel_rename_6a.mjs` | **PASS** | post-6B ANNOTATOR 자동 탐지 + 식별자 collapse |
| 20 | `node tmp/check_template_annotator_rename_6b.mjs` | **PASS** | 34/34 |
| 21 | `node tmp/check_validation_baseline_repair_1a.mjs` | **PASS** | exit 0 |

요약: 18개 노드 러너 + 1 파이썬 러너 + typecheck + build 전부 exit 0. PASS 또는
PASS_WITH_SKIPPED_BACKUP만 존재, FAIL 0건.

## 13. typecheck / build 결과
- `npm run typecheck` → **PASS** (exit 0)
- `npm run build` → **PASS** (exit 0)
- 로그: `ocr-server/logs/codex_FRONTEND_STRUCTURE_6B_TEMPLATE_ANNOTATOR_RENAME.out.log`,
  `ocr-server/logs/codex_FRONTEND_STRUCTURE_6B_TEMPLATE_ANNOTATOR_RENAME.err.log`

## 14. known stderr noise
- `ESLint: nextVitals is not iterable` — 빌드 exit 0, non-blocking (사전 기재된 known noise).

## 15. 남은 이슈
- 과거 phase(2A/2B/3B/4A/4B)의 logic-equivalence 검사는 backup 파일 부재로
  `PASS_WITH_SKIPPED_BACKUP`로 처리되고 있다. 6B와 무관한 사전 상태.
- `src/common/ui/OcrCanvasPane.tsx`의 doc-comment 3곳에 "OcrAnnotator" 단어가
  남아 있지만 import/식별자가 아니다. 본 작업의 수정 금지 파일이므로 그대로 유지.
  6B 검사는 주석 제외 후 스캔하여 통과.
- `src/lib/profiles.ts`의 doc-comment 문자열 `core/types.ts`는 5A 시점부터의
  잔존 (실제 import 아님, 동작 무영향).

## 16. 다음 작업 제안
- Template structure close-out 리포트 (4A→4B→5A→5B→5C→5D→5E→5F→6A→6B 누적
  정리 결과 요약 및 최종 디렉터리 구조 스냅샷).
- Template table column definition 설계 precheck (canonical column mapping,
  사용자 확인 상태, 저장 payload 변환 — 별도 `components/template/utils/`
  또는 store layer로 분리).
- TPL-95328E52 dirty 영향 precheck.
- `src/lib/profiles.ts` doc-comment 잔존 정리.
- `src/common/ui/OcrCanvasPane.tsx`의 doc-comment 표현 정리(`OcrAnnotator` →
  `TemplateAnnotator` 또는 도메인-중립 단어) micro-step.
- TestWorkspace 정리는 사용자 확인 후 진행.
