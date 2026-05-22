# FRONTEND_STRUCTURE_4B_TEMPLATE_EDITOR_UI_MOVE_20260522

## 1. 사용 도구 / 모델
- 도구: Claude Code (VSCode 확장)
- 모델: Claude Opus 4.7 (1M context)
- 작업명: FRONTEND-STRUCTURE-4B-TEMPLATE-EDITOR-UI-MOVE
- 실행 일자: 2026-05-22

## 2. 작업 목적
Template editor UI 중 Template private 으로 확정된 `OcrAnnotator.tsx` 와 `OcrRightPanel.tsx` 두 파일만 `components/ocr/` → `components/template/ui/` 로 이동. **rename 없음**, **route 정책 변경 없음**. 내부 로직/JSX/state/handler/저장/annotation 흐름 일체 미변경. `OcrCanvasPane` / `ocr/core/*` / `UnstructuredBuilder` / RunOCR / TestWorkspace 는 건드리지 않는다.

## 3. 백업 파일
- `backup/OcrAnnotator_20260522_before_FRONTEND_STRUCTURE_4B_TEMPLATE_EDITOR_UI_MOVE.tsx`
- `backup/OcrRightPanel_20260522_before_FRONTEND_STRUCTURE_4B_TEMPLATE_EDITOR_UI_MOVE.tsx`
- `backup/app_ocr_page_20260522_before_FRONTEND_STRUCTURE_4B_TEMPLATE_EDITOR_UI_MOVE.tsx`
- `backup/app_template_page_20260522_before_FRONTEND_STRUCTURE_4B_TEMPLATE_EDITOR_UI_MOVE.tsx`

## 4. 이동 파일
| Before | After | 방식 |
|--------|-------|------|
| `src/components/ocr/OcrAnnotator.tsx` (442 줄) | `src/components/template/ui/OcrAnnotator.tsx` | `git mv` |
| `src/components/ocr/OcrRightPanel.tsx` (507 줄) | `src/components/template/ui/OcrRightPanel.tsx` | `git mv` |

## 5. 수정 파일
1. **`src/components/template/ui/OcrAnnotator.tsx`** — 이동 후 상대경로 import 5개 보정 (본문/JSX/state/handler 미변경)
2. **`src/components/template/ui/OcrRightPanel.tsx`** — 이동 후 상대경로 import 3개 보정 (본문/JSX/state/handler 미변경)
3. **`src/app/ocr/page.tsx`** — dynamic import 1줄 보정 (그 외 미변경)
4. **`src/app/template/page.tsx`** — dynamic import 1줄 보정 (그 외 미변경)

신규 생성:
- `mysuit-ocr/tmp/check_template_editor_ui_move_4b.mjs` (정적 boundary 검증)

검증 스크립트 보정 (tmp/, 운영 무관):
- `tmp/check_template_workspace_move_4a.mjs` — `OcrAnnotator_untouched_path` / `OcrRightPanel_untouched_path` 검사를 "기존 `ocr/` 경로 OR 새 `template/ui/` 경로 둘 중 하나에 존재" 로 완화 (4A-time invariant 가 4B 의 적법한 이동을 거부하지 않도록). `OcrCanvasPane` 과 `ocr/core/*` 는 여전히 strict 검사 유지.

## 6. import 수정 내용

**OcrAnnotator.tsx (new path: `components/template/ui/`)**:
| line | before | after |
|------|--------|-------|
| 4 | `"./core/types"` | `"../../ocr/core/types"` |
| 5 | `"./core/export"` | `"../../ocr/core/export"` |
| 6 | `"./OcrCanvasPane"` | `"../../ocr/OcrCanvasPane"` |
| 7 | `"./OcrRightPanel"` | `"./OcrRightPanel"` (변경 없음 — 형제) |
| 8 | `"@/lib/imageStore"` | `"@/lib/imageStore"` (alias, 변경 없음) |
| 9 | `"../common/AppProviders"` | `"../../common/AppProviders"` |

**OcrRightPanel.tsx (new path: `components/template/ui/`)**:
| line | before | after |
|------|--------|-------|
| 4 | `"./core/types"` | `"../../ocr/core/types"` |
| 5 | `"./core/ops"` | `"../../ocr/core/ops"` |
| 6 | `"./core/table"` | `"../../ocr/core/table"` |

**app/ocr/page.tsx (line 10) & app/template/page.tsx (line 10)**:
- before: `() => import("../../components/ocr/OcrAnnotator")`
- after:  `() => import("../../components/template/ui/OcrAnnotator")`

## 7. 이동하지 않은 파일 목록 (Phase 4B 보류)
- `src/components/ocr/OcrCanvasPane.tsx` — OcrAnnotator + RunOcrWorkspace 양쪽에서 사용. 향후 common/ui 후보. 단독 Template 전용 이동 금지.
- `src/components/ocr/core/types.ts` — RunOCR 도 의존. common util 후보.
- `src/components/ocr/core/table.ts`, `ops.ts`, `export.ts` — canvas/right panel/export save path 와 얽힘. Template utils 후보.
- `src/components/template/UnstructuredBuilder.tsx` — 이미 template/, 그대로.
- `src/components/runocr/*` — 미수정 (4B 와 무관).
- `src/components/test/TestWorkspace.tsx` — 사용자 확인 전 이동/수정 금지.

## 8. rename 보류 이유
- `OcrRightPanel` → `TemplateRightPanel` rename 은 다음 micro-step 으로 별도 진행 권장 (정확한 importer chain 영향 분석 + 검증 스크립트 동기 보정 동반 필요).
- `OcrAnnotator` 도 rename 없이 위치만 이동. import 경로만 변경됨.
- 이번 phase 의 invariant: 이동만 — rename 은 한 번에 진행하지 않는다.

## 9. route policy 유지 여부
| 라우트 | 정책 변경 | 비고 |
|--------|-----------|------|
| `/ocr` (app/ocr/page.tsx) | 없음 | `TemplateWorkspace` 리스트 + "editor" 모드에서 `<OcrAnnotator />` 사용. dynamic import path 만 새 위치로 보정. JSX/branching/state 모두 그대로. |
| `/template` (app/template/page.tsx) | 없음 | `OcrAnnotator` + `UnstructuredBuilder` 직접 사용. dynamic import path 만 새 위치로 보정. 모드 카드/저장 템플릿 카드/툴팁 등 모두 그대로. |

`/ocr → /template` rename 같은 정책 작업은 본 phase 에서 미수행.

## 10. static check 결과
`tmp/check_template_editor_ui_move_4b.mjs` (신규 생성):

| 항목 | 결과 |
|------|------|
| 새 경로 (`template/ui/OcrAnnotator.tsx`, `template/ui/OcrRightPanel.tsx`) 존재 | ✓ |
| 구 경로 (`ocr/OcrAnnotator.tsx`, `ocr/OcrRightPanel.tsx`) 부재 | ✓ |
| `OcrCanvasPane.tsx` / `ocr/core/` / `TemplateWorkspace.tsx` / `UnstructuredBuilder.tsx` 위치 그대로 | ✓ |
| `TemplateRightPanel.tsx` 생성 안 됨 (no rename) | ✓ |
| `RunOcrWorkspace.tsx` 가 3B 백업과 logic-equivalent (4B 가 RunOCR 미수정) | ✓ |
| `TestWorkspace.tsx` 존재 (미삭제) | ✓ |
| `/ocr/page.tsx`, `/template/page.tsx` 가 새 경로 import & 구 경로 import 잔존 없음 | ✓ |
| `/ocr` route 정책 (`TemplateWorkspace` + `<OcrAnnotator>` 사용) 보존 | ✓ |
| `/template` route 정책 (`<OcrAnnotator>` + `UnstructuredBuilder` 사용) 보존 | ✓ |
| 새 OcrAnnotator 가 `../../ocr/OcrCanvasPane`, `../../ocr/core/types`, `../../ocr/core/export`, `./OcrRightPanel`, `../../common/AppProviders` import | ✓ |
| 새 OcrRightPanel 이 `../../ocr/core/types`, `../../ocr/core/ops`, `../../ocr/core/table` import | ✓ |
| OcrAnnotator / OcrRightPanel 본문이 백업과 logic-equivalent (주석/import-path/whitespace strip 후 동일) | ✓ |
| `export default function OcrAnnotator` / `export default function OcrRightPanel` 이름 보존 | ✓ |
| **[TEMPLATE_EDITOR_UI_MOVE_4B]** | **PASS** |

## 11. runner 결과
| Runner | 결과 |
|--------|------|
| `node tmp/check_template_editor_ui_move_4b.mjs` | PASS |
| `node tmp/check_template_workspace_move_4a.mjs` | PASS (after 4B-aware relax) |
| `node tmp/check_runocr_formdata_keys_2a.mjs` | PASS |
| `node tmp/check_runocr_request_boundary_2b.mjs` | PASS |
| `node tmp/check_runocr_response_mapping_boundary_2c.mjs` | PASS |
| `node tmp/check_runocr_result_layout_boundary_3a.mjs` | PASS |
| `node tmp/check_runocr_doc_comments_3b.mjs` | PASS |
| `node tmp/check_table_view_model_v1_fixtures_js.mjs` | PASS 8/8 |
| `node tmp/check_clean_json_v1_fixtures_js.mjs` | PASS 9/9 (내부 typecheck=PASS, build=PASS) |
| `python tmp/codex_markdown_contract_fixture_lock.py --check --phase post_TEMPLATE_EDITOR_UI_MOVE_20260522` | PASS 6/6 (`.venv` python) |

## 12. typecheck / build 결과
- `npm run typecheck` → PASS (exit 0)
- `npm run build` → PASS (exit 0, Next.js 15.5.4, 18/18 static pages)
  - `/ocr` 2.73 kB / 113 kB (변화 없음)
  - `/template` 5.73 kB / 116 kB (변화 없음)
  - `/runocr` 65.7 kB / 184 kB (변화 없음)

## 13. known stderr noise
- `⨯ ESLint: nextVitals is not iterable` — `npm run build` 시 stderr 에 등장, exit 0 (non-blocking)
- 시스템 python `requests` 미설치는 `.venv/Scripts/python.exe` 로 우회

## 14. 남은 이슈
- `OcrRightPanel` → `TemplateRightPanel` rename 은 별도 micro-step 으로 분리됨. 이번 phase 에서 진행하지 않음
- `OcrAnnotator` 도 이름 그대로 유지 — Template private 컴포넌트지만 식별자 rename 은 별도 단계
- `OcrCanvasPane` 은 RunOCR + Template 양쪽 사용 — common/ui 후보 분석 phase 필요
- `ocr/core/*` (types/ops/table/export) 분류/이동 phase 필요
- 4A 검증 스크립트는 이번 phase 의 적법한 이동을 거부하지 않도록 OcrAnnotator/OcrRightPanel 경로 검사를 "OR" 로 완화 — 향후 phase 에서 동일 패턴 적용 권장
- `ocr-server/data/templates.json` 여전히 dirty (별도 phase 정리 필요)

## 15. 다음 작업 제안
- `OcrRightPanel` → `TemplateRightPanel` rename micro-step precheck (정확한 importer 검사 + 검증 스크립트 동기 보정 포함)
- `OcrCanvasPane` common/shared 영향 precheck (RunOCR + Template 양쪽 사용 케이스)
- `ocr/core/*` utils 이동 precheck — `types.ts` 는 common 후보, `ops/table/export` 는 template utils 후보
- Template table column definition 설계 precheck
- TPL-95328E52 dirty 영향 precheck (markdown fixture 안정성)
- TestWorkspace 폴더 정비는 사용자 확인 후 진행
- (선택) `/ocr` 라우트 이름 정책 결정 후 redirect/rename 별도 phase
