# FRONTEND_STRUCTURE_4A_TEMPLATE_WORKSPACE_MOVE_20260522

## 1. 사용 도구 / 모델
- 도구: Claude Code (VSCode 확장)
- 모델: Claude Opus 4.7 (1M context)
- 작업명: FRONTEND-STRUCTURE-4A-TEMPLATE-WORKSPACE-MOVE
- 실행 일자: 2026-05-22

## 2. 작업 목적
Template 탭의 최상위 list workspace 파일 `TemplateWorkspace.tsx` 만 사용자가 확정한 feature 폴더 구조에 맞춰 `components/ocr/` → `components/template/` 으로 이동. route import 1줄 보정 외에는 어떤 운영 파일도 수정하지 않는다. 내부 UI/canvas/annotator/right panel/core 파일은 **이번 phase 에서 이동하지 않는다**.

## 3. 백업 파일
- `backup/TemplateWorkspace_20260522_before_FRONTEND_STRUCTURE_4A_TEMPLATE_WORKSPACE_MOVE.tsx`
- `backup/app_ocr_page_20260522_before_FRONTEND_STRUCTURE_4A_TEMPLATE_WORKSPACE_MOVE.tsx`

## 4. 이동 파일
| Before | After | 방식 |
|--------|-------|------|
| `mysuit-ocr/src/components/ocr/TemplateWorkspace.tsx` | `mysuit-ocr/src/components/template/TemplateWorkspace.tsx` | `git mv` |

## 5. 수정 파일
- `mysuit-ocr/src/app/ocr/page.tsx`
  - `import TemplateWorkspace from "../../components/ocr/TemplateWorkspace";`
    → `import TemplateWorkspace from "../../components/template/TemplateWorkspace";`
  - 그 외 본문/JSX/state/handler 일체 미변경
- `mysuit-ocr/src/components/template/TemplateWorkspace.tsx`
  - `git mv` 로 위치만 이동. 본문/import/로직 byte-identical (boundary check 의 logic-equivalent 검사 통과)

## 6. import 수정 내용
**route (app/ocr/page.tsx, line 7)**:
- before: `"../../components/ocr/TemplateWorkspace"`
- after:  `"../../components/template/TemplateWorkspace"`

**TemplateWorkspace 내부 import**:
- `import { useUi } from "../common/AppProviders";` (line 4) — 수정 불필요.
  - 기존 위치: `components/ocr/` → `../common/AppProviders` = `components/common/AppProviders`
  - 새 위치:   `components/template/` → `../common/AppProviders` = `components/common/AppProviders`
  - 같은 depth (`components/<feature>/`) 라 상대경로 보존.

## 7. 이동하지 않은 파일 목록 (Phase 1 보류)
- `src/components/ocr/OcrAnnotator.tsx` (TEMPLATE_PRIVATE_UI, Phase 1 보류)
- `src/components/ocr/OcrCanvasPane.tsx` (RUNOCR_SHARED_CANDIDATE — RunOCR 도 사용 중, 단독 이동 금지)
- `src/components/ocr/OcrRightPanel.tsx` (rename 포함 시 고위험)
- `src/components/ocr/core/types.ts` (COMMON_UTIL_CANDIDATE)
- `src/components/ocr/core/table.ts`, `ops.ts`, `export.ts` (Template utils 후보 — 후속 phase)
- `src/components/template/UnstructuredBuilder.tsx` (이미 template/, 그대로)
- `src/components/test/TestWorkspace.tsx` (사용자 확인 전 이동/수정 금지)

## 8. route 정책 유지 여부
| 라우트 | 정책 변경 여부 | 비고 |
|--------|----------------|------|
| `/ocr` (app/ocr/page.tsx) | 변경 없음 | TemplateWorkspace 리스트 → "신규 템플릿" 클릭 시 OcrAnnotator 진입. import 경로만 보정. |
| `/template` (app/template/page.tsx) | 변경 없음 | OcrAnnotator + UnstructuredBuilder 직접 사용. TemplateWorkspace import 안 함. 수정 없음. |

`/ocr → /template` 이름 변경 같은 정책 작업은 명시적으로 금지됐고 본 phase 에서 진행하지 않았다.

## 9. static check 결과
`tmp/check_template_workspace_move_4a.mjs` (신규 생성):

| 항목 | 결과 |
|------|------|
| 새 경로(`components/template/TemplateWorkspace.tsx`) 존재 | ✓ |
| 기존 경로(`components/ocr/TemplateWorkspace.tsx`) 부재 | ✓ |
| `/ocr/page.tsx` 가 새 경로 import | ✓ |
| `/ocr/page.tsx` 에 구 경로 import 잔존 없음 | ✓ |
| `/template/page.tsx` 의 TemplateWorkspace import 정책 보존 (import 안 함) | ✓ |
| 이동된 파일 안에 구 경로 자기참조 없음 | ✓ |
| OcrAnnotator.tsx 위치 그대로 (`components/ocr/`) | ✓ |
| OcrCanvasPane.tsx 위치 그대로 | ✓ |
| OcrRightPanel.tsx 위치 그대로 | ✓ |
| `components/ocr/core` 디렉토리 그대로 | ✓ |
| `components/template/UnstructuredBuilder.tsx` 존재 | ✓ |
| `components/test/TestWorkspace.tsx` 존재 | ✓ |
| TemplateWorkspace 본문 logic-identical to backup (주석 strip + ws 정규화 후 동일) | ✓ |
| TemplateWorkspace 가 `../common/AppProviders` import 유지 | ✓ |
| **[TEMPLATE_WORKSPACE_MOVE_4A]** | **PASS** |

## 10. runner 결과
| Runner | 결과 |
|--------|------|
| `node tmp/check_template_workspace_move_4a.mjs` | PASS |
| `node tmp/check_runocr_formdata_keys_2a.mjs` | PASS |
| `node tmp/check_runocr_request_boundary_2b.mjs` | PASS |
| `node tmp/check_runocr_response_mapping_boundary_2c.mjs` | PASS |
| `node tmp/check_runocr_result_layout_boundary_3a.mjs` | PASS |
| `node tmp/check_runocr_doc_comments_3b.mjs` | PASS |
| `node tmp/check_table_view_model_v1_fixtures_js.mjs` | PASS 8/8 |
| `node tmp/check_clean_json_v1_fixtures_js.mjs` | PASS 9/9 (내부 typecheck=PASS, build=PASS) |
| `python tmp/codex_markdown_contract_fixture_lock.py --check --phase post_TEMPLATE_WORKSPACE_MOVE_20260522` | PASS 6/6 (`.venv` python) |

## 11. typecheck / build 결과
- `npm run typecheck` → PASS (exit 0)
- `npm run build` → PASS (exit 0, Next.js 15.5.4, 18/18 static pages)
  - `/ocr` 2.73 kB / 113 kB (변화 없음)
  - `/template` 5.73 kB / 116 kB (변화 없음)
  - `/runocr` 65.7 kB / 184 kB (변화 없음)

## 12. known stderr noise
- `⨯ ESLint: nextVitals is not iterable` — `npm run build` 시 stderr 에 등장, exit code 0 (non-blocking)
- 시스템 python `requests` 미설치는 `.venv/Scripts/python.exe` 로 우회

## 13. 남은 이슈
- `OcrAnnotator` / `OcrCanvasPane` / `OcrRightPanel` 의 ownership 정리는 별도 phase (canvas 는 RunOCR shared 후보라 단독 이동 금지)
- `ocr/core/` (types.ts / table.ts / ops.ts / export.ts) common util 후보 분석 필요
- `/ocr` 라우트 이름이 Template list 화면을 가리키는 비대칭은 본 phase 범위 밖 — 정책 결정 후 별도 진행
- `ocr-server/data/templates.json` 여전히 dirty (이전 세션 영향)

## 14. 다음 작업 제안
- `OcrAnnotator` / `OcrRightPanel` 이동 precheck (template-private 인지 확인, rename 영향 분석)
- `OcrCanvasPane` common/shared 영향 precheck (RunOCR 직접 사용 + template 내부 사용 양쪽 케이스)
- `ocr/core` utils 이동 precheck — `types.ts` 는 common 후보, 나머지는 template utils 후보
- Template table column definition 설계 precheck
- TPL-95328E52 dirty 영향 precheck (markdown fixture 안정성)
- TestWorkspace 폴더 정비는 사용자 확인 후
- (선택) `/ocr` 라우트 이름 정책 결정 후 redirect/rename 별도 phase
