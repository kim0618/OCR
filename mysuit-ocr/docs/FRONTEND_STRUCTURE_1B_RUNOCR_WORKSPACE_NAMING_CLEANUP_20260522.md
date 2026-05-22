# FRONTEND_STRUCTURE_1B_RUNOCR_WORKSPACE_NAMING_CLEANUP_20260522

## 1. 사용 도구 / 모델
- 도구: Claude Code (VSCode 확장)
- 모델: Claude Opus 4.7 (1M context)
- 작업명: FRONTEND-STRUCTURE-1B-RUNOCR-WORKSPACE-NAMING-CLEANUP
- 실행 일자: 2026-05-22

## 2. 작업 목적
FRONTEND-STRUCTURE-1 폴더/파일 이동 직후 `RunOcrWorkspace.tsx` 내부에 잔존한 `UploadWorkspace` 계열 식별자(타입, 디폴트 export 함수명)를 `RunOcrWorkspace` 계열로 정리. **이름 정리만** 수행하며 로직/JSX/state/API/FormData/import 구조 변경은 없다.

## 3. 백업 파일
- `backup/RunOcrWorkspace_20260522_before_FRONTEND_STRUCTURE_1B_RUNOCR_WORKSPACE_NAMING_CLEANUP.tsx`

## 4. 수정 파일
- `mysuit-ocr/src/components/runocr/RunOcrWorkspace.tsx` (이 파일만 수정)

## 5. 변경한 식별자 목록
| Before | After | 위치 |
|--------|-------|------|
| `type UploadWorkspaceVariant` | `type RunOcrWorkspaceVariant` | line 47 (정의) + line 51 (참조) |
| `type UploadWorkspaceProps`   | `type RunOcrWorkspaceProps`   | line 50 (정의) + line 111 (참조) |
| `export default function UploadWorkspace(...)` | `export default function RunOcrWorkspace(...)` | line 111 |

총 4개 식별자 위치 변경 (정의 3 + 참조 자동 동기 1). `variant` 문자열 리터럴 union 값 `"upload" | "runocr"` 및 default 값 `variant = "upload"` 는 의미 변경 우려가 있어 보존 (식별자 이름 정리 범위 밖).

## 6. 프로젝트 전체 UploadWorkspace 검색 결과
- `src/` 전체 검색: **0 hit** (운영 코드에 잔존 식별자 없음)
- `docs/`, `tmp/`, `backup/` 의 과거 이력/리포트/백업에는 잔존하지만 작업 범위 밖이라 의도적으로 유지.

`RunOcrWorkspace` 검색 결과:
- `mysuit-ocr/src/app/runocr/page.tsx:4`: `import RunOcrWorkspace from "../../components/runocr/RunOcrWorkspace";`
- `mysuit-ocr/src/app/runocr/page.tsx:9`: `<RunOcrWorkspace variant="runocr" />`
- `mysuit-ocr/src/components/runocr/RunOcrWorkspace.tsx:47/50/51/111`: 새 식별자 정의 및 default export

`page.tsx` 는 default import 이므로 이번 rename 으로 인한 외부 import 수정 불필요.

## 7. 변경하지 않은 범위 (의도된 미수정)
- `src/components/runocr/ui/OcrResultPanel.tsx` (UI 컴포넌트, 로직/이름 변경 없음)
- `src/components/runocr/ui/OcrDocViewer.tsx`
- `src/components/runocr/ui/CornerAdjust.tsx`
- `src/components/test/TestWorkspace.tsx`
- `src/lib/invoiceTableDisplay.ts`
- `src/lib/structuredTableViewModel.ts`
- `src/lib/cleanJsonBuilder.ts`
- `src/lib/markdownReportBuilder.ts`
- `src/lib/ocrResultFormatters.ts`
- backend / parser / templates.json / manifest / GT / fixture 전부
- `RunOcrWorkspace.tsx` 내부 JSX, hook, state, FormData/API 호출 로직, 함수 본문 (전부 미변경)

## 8. typecheck / build 결과
- `npm run typecheck` → PASS (exit 0)
- `npm run build` → PASS (exit 0, Next.js 15.5.4, static 18/18, `/runocr` 65.7 kB / 184 kB — 사이즈 변화 없음)

## 9. runner 결과
| Runner | 결과 |
|--------|------|
| `node tmp/check_table_view_model_v1_fixtures_js.mjs` | PASS 8/8 |
| `node tmp/check_clean_json_v1_fixtures_js.mjs`       | PASS 9/9 (내부 typecheck=PASS, build=PASS) |
| `python tmp/codex_markdown_contract_fixture_lock.py --check --phase post_RUNOCR_NAMING_CLEANUP_20260522` | PASS 6/6 (`.venv/Scripts/python.exe` 사용) |

markdown runner 는 시스템 python 에 `requests` 패키지가 없어 `ocr-server/.venv` python 으로 실행. 본 rename 작업과는 무관한 환경 이슈.

## 10. known stderr noise
- `⨯ ESLint: nextVitals is not iterable` — `npm run build` 시 stderr 에 등장. exit code 0 으로 non-blocking 처리.

## 11. 다음 작업 제안
- RunOCR 내부 utils 분리 precheck (Phase 2 — 폴더 안정화 이후)
- `buildOcrFormData` / `runOcrRequest` / `mapOcrResponse` 분리 후보 분석
- Template 폴더 ownership precheck
- `common/utils` 이동은 feature 폴더(runocr / template / history / test) 안정화 이후 별도 진행
- TestWorkspace 폴더 정비는 사용자 확인 후 진행
- 선택적: `RunOcrTemplateMode` 같은 다른 내부 alias 정합성 점검 (현재는 의미 일치라 보류)
