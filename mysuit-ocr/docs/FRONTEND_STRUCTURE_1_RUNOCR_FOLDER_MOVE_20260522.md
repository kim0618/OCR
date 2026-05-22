# FRONTEND_STRUCTURE_1_RUNOCR_FOLDER_MOVE_20260522

## 1. 사용 도구 / 모델
- 도구: Claude Code (VSCode 확장)
- 모델: Claude Opus 4.7 (1M context)
- 작업명: FRONTEND-STRUCTURE-1-RUNOCR-FOLDER-MOVE
- 실행 일자: 2026-05-22

## 2. 작업 목적
- `src/components/upload` 폴더를 사용자가 확정한 최종 구조에 맞춰 `src/components/runocr` 로 이동
- `UploadWorkspace.tsx` → `RunOcrWorkspace.tsx` 파일 rename
- RunOCR 전용 UI 컴포넌트 3종을 `src/components/runocr/ui/` 로 이동
- 깨지는 import 경로만 최소 수정 (내부 로직/리팩토링 금지)
- 이번 작업은 폴더 위치 정리 Phase 1 (utils/service/hook 분리 없음)

## 3. 백업 파일
모두 `d:/Free_Vue/OCR/backup/` 하위에 생성:
- `UploadWorkspace_20260522_before_FRONTEND_STRUCTURE_1_RUNOCR_FOLDER_MOVE.tsx`
- `OcrResultPanel_20260522_before_FRONTEND_STRUCTURE_1_RUNOCR_FOLDER_MOVE.tsx`
- `OcrDocViewer_20260522_before_FRONTEND_STRUCTURE_1_RUNOCR_FOLDER_MOVE.tsx`
- `CornerAdjust_20260522_before_FRONTEND_STRUCTURE_1_RUNOCR_FOLDER_MOVE.tsx`

## 4. 이동 / rename 파일
| Before | After |
|--------|-------|
| `src/components/upload/UploadWorkspace.tsx` | `src/components/runocr/RunOcrWorkspace.tsx` |
| `src/components/upload/OcrResultPanel.tsx` | `src/components/runocr/ui/OcrResultPanel.tsx` |
| `src/components/upload/OcrDocViewer.tsx`   | `src/components/runocr/ui/OcrDocViewer.tsx`   |
| `src/components/upload/CornerAdjust.tsx`   | `src/components/runocr/ui/CornerAdjust.tsx`   |

빈 `src/components/upload/` 폴더는 제거 완료.

## 5. import 경로 수정 파일
1. `src/app/runocr/page.tsx`
   - `import UploadWorkspace from "../../components/upload/UploadWorkspace"`
     → `import RunOcrWorkspace from "../../components/runocr/RunOcrWorkspace"`
   - `<UploadWorkspace variant="runocr" />` → `<RunOcrWorkspace variant="runocr" />`

2. `src/components/runocr/RunOcrWorkspace.tsx` (이동 후 파일)
   - `./OcrResultPanel`  → `./ui/OcrResultPanel`
   - `./OcrDocViewer`    → `./ui/OcrDocViewer`
   - `./CornerAdjust`    → `./ui/CornerAdjust`

3. `src/components/runocr/ui/OcrResultPanel.tsx`
   - `../common/AppProviders` → `../../common/AppProviders`
   - 사유: `runocr/ui/` 로 한 단계 깊어졌기 때문에 상대경로 보정 필요. 깨지는 import 한 줄만 수정, 로직 변경 없음.

4. `src/components/runocr/ui/OcrDocViewer.tsx`
   - 같은 `ui/` 폴더 내 형제 import (`./OcrResultPanel`)는 유지. 수정 불필요.

5. `src/components/runocr/ui/CornerAdjust.tsx`
   - 상대 import 없음. 수정 불필요.

## 6. 목표 구조 반영 결과
```
src/components/runocr/
  RunOcrWorkspace.tsx
  ui/
    OcrResultPanel.tsx
    OcrDocViewer.tsx
    CornerAdjust.tsx
```
- 사용자가 최종 확정한 `components/runocr/ui` 구조 사용 (precheck 리포트의 `components/runocr/components` 가 아님)
- `utils/` 등 하위 폴더는 Phase 1 범위 밖이라 미생성

## 7. 남은 upload 참조 검색 결과
- 검색 쿼리: `components/upload`, `@/components/upload`, `../upload`, `../../upload`, `from "..../upload/"`
- 결과: 0건
- `UploadWorkspace` 식별자 검색 결과: 모두 `RunOcrWorkspace.tsx` 내부의 type/local 식별자 (`UploadWorkspaceVariant`, `UploadWorkspaceProps`, `export default function UploadWorkspace`). 외부 consumer 는 default import 이므로 동작에 영향 없음. Phase 1 범위(폴더/파일 이동) 밖이라 내부 식별자 rename 은 보류.

## 8. 내부 로직 미수정 확인
- 4개 파일의 함수/훅/JSX/상태/타입 정의 모두 변경 없음
- 수정된 라인은 import 경로 3종 + page.tsx 의 default import alias + JSX 태그 이름 1회뿐
- `useRunOcr.ts`, `useRunOcrState.ts`, `runOcrRequest.ts`, `buildOcrFormData.ts`, `mapOcrResponse.ts`, `RunOcrControls.tsx`, `RunOcrResultLayout.tsx` 신규 생성 없음
- `invoiceTableDisplay.ts`, `structuredTableViewModel.ts`, `cleanJsonBuilder.ts`, `markdownReportBuilder.ts`, `ocrResultFormatters.ts` 수정 없음
- backend/parser/templates/manifest/GT/fixture 수정 없음

## 9. TestWorkspace 미수정 확인
- `src/components/test/TestWorkspace.tsx` 수정 없음
- 검색: `from "..../upload/"` 결과 0건 (TestWorkspace 는 애초에 upload 컴포넌트 직접 import 없음)
- History / Template / Restore 파일 수정 없음

## 10. fixture runner 결과
| Runner | 결과 |
|--------|------|
| `node tmp/check_table_view_model_v1_fixtures_js.mjs` | PASS 8/8 |
| `node tmp/check_clean_json_v1_fixtures_js.mjs`       | PASS 9/9 (스크립트 내부 typecheck/build 재실행 결과는 main typecheck/build 로 대체 검증) |
| `python tmp/codex_markdown_contract_fixture_lock.py --check --phase post_RUNOCR_FOLDER_MOVE_20260522` | PASS 6/6 |

clean JSON runner 의 내부 typecheck/build 단계는 첫 실행 시 `ui/OcrResultPanel` 의 `../common/AppProviders` 상대경로 오류로 FAIL 이 1회 기록됐다. 해당 import 수정 후 외부에서 `npm run typecheck` / `npm run build` 를 직접 재실행하여 PASS 확인 (아래 11번 항목). fixture 자체(9/9) 는 영향 없음.

## 11. typecheck / build 결과
- `npm run typecheck` → PASS (exit 0, tsc --noEmit 출력 없음)
- `npm run build` → PASS (exit 0, Next.js 15.5.4 static generation 18/18 성공, `/runocr` 65.7 kB / 184 kB)

## 12. known stderr noise
- `⨯ ESLint: nextVitals is not iterable`
  - build 시 stderr 에 항상 등장하지만 exit code 0 (non-blocking)
- markdown runner 1회 실패는 시스템 python 에 `requests` 미설치 때문이며, `.venv/Scripts/python.exe` 로 재실행하여 정상 6/6 PASS. 코드/구조 변경과 무관.

## 13. 다음 작업 제안
- RunOCR 내부 utils 분리 precheck (현재 `RunOcrWorkspace.tsx` 단일 파일에 응집된 helper/runOcr 호출/응답 매핑 분리 후보 분석)
- buildOcrFormData / runOcrRequest / mapOcrResponse 분리 후보 분석 (Phase 2 후보)
- Template 폴더 ownership precheck (template 컴포넌트와의 경계 정리)
- common/utils 이동은 feature 폴더(runocr / test / template / history) 안정화 이후 별도 진행
- TestWorkspace 폴더 구조 정비는 사용자 확인 후 진행 (이번 Phase 1 범위 밖)
- `UploadWorkspace` 내부 식별자 rename(`UploadWorkspaceProps` 등) 은 별도 micro-step 으로 분리 가능
