# FRONTEND TARGET STRUCTURE OWNERSHIP PRECHECK 20260522

## 1. 사용 도구와 모델
- 사용 도구: Codex
- 사용 모델: Codex
- 작업명: `CODEX_FRONTEND_TARGET_STRUCTURE_OWNERSHIP_PRECHECK_NO_PROD_MODIFY`

## 2. 코드 수정 여부
- 운영 코드 수정 없음.
- 파일 이동/삭제 없음.
- import 경로 수정 없음.
- fixture/backend/templates/manifest 수정 없음.

## 3. 생성 파일
- `tmp/codex_frontend_target_structure_ownership_precheck.py`
- `docs/FRONTEND_TARGET_STRUCTURE_OWNERSHIP_PRECHECK_20260522.md`
- `docs/FRONTEND_TARGET_STRUCTURE_OWNERSHIP_PRECHECK_20260522.json`
- `docs/FRONTEND_TARGET_STRUCTURE_OWNERSHIP_MAP_20260522.csv`

## 4. 사용자가 정한 목표 구조
- route entry는 `src/app`.
- 탭/기능별 UI는 `src/components/{runocr,template,history,restore,test,login,layout}`.
- 여러 탭 공통 UI는 `src/common/components`.
- 여러 탭 공통 순수 로직/정책/변환 함수는 `src/common/utils`.
- 여러 탭 공통 타입은 `src/common/types`.

## 5. 분석 범위
- 포함: `src/app`, `src/components`, `src/lib`, `src/types`, `src/hooks`가 있다면 포함.
- 제외: `node_modules`, `.next`, `dist`, `build`, `public`, `backup`, `tmp`, `docs`, backend.

## 6. 전체 파일 수
- totalFiles: 66
- routeReachableFiles: 63

## 7. ownership 분류 요약
| owner | count |
| --- | --- |
| app-route | 17 |
| common/components | 3 |
| common/types | 1 |
| common/utils | 10 |
| history | 5 |
| layout | 3 |
| login | 2 |
| restore | 4 |
| runocr | 4 |
| template | 9 |
| test | 8 |

## 8. common 후보 목록
| currentPath | targetPath | owner | sharedStatus | risk | notes |
| --- | --- | --- | --- | --- | --- |
| src/components/common/AppProviders.tsx | src/components/common/AppProviders.tsx | common/components | shared-component | MEDIUM | ["Imported from multiple feature areas: history, login, restore, runocr, template, test."] |
| src/components/common/FileDropzone.tsx | src/common/components/FileDropzone.tsx | common/components | shared-component | LOW | ["Imported from multiple feature areas: runocr, template."] |
| src/components/common/RequireLogin.tsx | src/common/components/RequireLogin.tsx | common/components | shared-component | LOW | ["Imported from multiple feature areas: history, restore."] |
| src/lib/axios.ts | src/common/utils/axios.ts | common/utils | shared-utils | MEDIUM | ["Contains IO/browser/API storage signal; verify feature boundary before move.", "Imported from multiple feature areas: history, login."] |
| src/lib/bizNumber.ts | src/common/utils/bizNumber.ts | common/utils | shared-utils | LOW | ["Imported from multiple feature areas: history, runocr, test."] |
| src/lib/cleanJsonBuilder.ts | src/common/utils/cleanJsonBuilder.ts | common/utils | shared-utils | MEDIUM | ["React signal found; verify before placing under utils."] |
| src/lib/imageStore.ts | src/common/utils/imageStore.ts | common/utils | shared-utils | MEDIUM | ["Contains IO/browser/API storage signal; verify feature boundary before move.", "Imported from multiple feature areas: runocr, template."] |
| src/lib/invoiceFieldLabels.ts | src/common/utils/invoiceFieldLabels.ts | common/utils | shared-utils | LOW | ["Imported from multiple feature areas: history, runocr."] |
| src/lib/invoiceTableDisplay.ts | src/common/utils/invoiceTableDisplay.ts | common/utils | shared-utils | HIGH | [] |
| src/lib/markdownReportBuilder.ts | src/common/utils/markdownReportBuilder.ts | common/utils | shared-utils | MEDIUM | ["React signal found; verify before placing under utils."] |
| src/lib/ocrResultFormatters.ts | src/common/utils/ocrResultFormatters.ts | common/utils | shared-utils | MEDIUM | ["React signal found; verify before placing under utils."] |
| src/lib/structuredTableViewModel.ts | src/common/utils/structuredTableViewModel.ts | common/utils | shared-utils | MEDIUM | ["React signal found; verify before placing under utils."] |
| src/lib/theme.ts | src/common/utils/theme.ts | common/utils | shared-utils | LOW | ["Contains IO/browser/API storage signal; verify feature boundary before move.", "React signal found; verify before placing under utils."] |
| src/types/utif.d.ts | src/common/types/utif.d.ts | common/types | shared-types | MEDIUM | ["Type/declaration file: do not judge by importedBy only."] |

## 9. feature-private 후보 목록
| currentPath | targetPath | owner | sharedStatus | risk |
| --- | --- | --- | --- | --- |
| src/components/autorestore/AutoRestoreWorkspace.tsx | src/components/restore/AutoRestoreWorkspace.tsx | restore | feature-private-component | MEDIUM |
| src/components/history/DetailHistoryView.tsx | src/components/history/DetailHistoryView.tsx | history | feature-private-component | HIGH |
| src/components/history/HistoryWorkspace.tsx | src/components/history/HistoryWorkspace.tsx | history | feature-private-component | MEDIUM |
| src/components/history/popup/CreateHistoryPopup.tsx | src/components/history/components/CreateHistoryPopup.tsx | history | feature-private-component | MEDIUM |
| src/components/history/popup/EditHistoryPopup.tsx | src/components/history/components/EditHistoryPopup.tsx | history | feature-private-component | MEDIUM |
| src/components/layout/AppShell.tsx | src/components/layout/AppShell.tsx | layout | feature-private-component | LOW |
| src/components/layout/Header.tsx | src/components/layout/Header.tsx | layout | feature-private-component | LOW |
| src/components/layout/Sidebar.tsx | src/components/layout/Sidebar.tsx | layout | feature-private-component | LOW |
| src/components/login/LoginWorkspace.tsx | src/components/login/LoginWorkspace.tsx | login | feature-private-component | LOW |
| src/components/ocr/OcrAnnotator.tsx | src/components/template/components/OcrAnnotator.tsx | template | feature-private-component | HIGH |
| src/components/ocr/OcrCanvasPane.tsx | src/components/template/components/OcrCanvasPane.tsx | template | feature-private-component | HIGH |
| src/components/ocr/OcrRightPanel.tsx | src/components/template/components/OcrRightPanel.tsx | template | feature-private-component | HIGH |
| src/components/ocr/TemplateWorkspace.tsx | src/components/template/TemplateWorkspace.tsx | template | feature-private-component | MEDIUM |
| src/components/ocr/core/export.ts | src/components/template/utils/export.ts | template | feature-private-utils | MEDIUM |
| src/components/ocr/core/ops.ts | src/components/template/utils/ops.ts | template | feature-private-utils | MEDIUM |
| src/components/ocr/core/table.ts | src/components/template/utils/table.ts | template | feature-private-utils | MEDIUM |
| src/components/ocr/core/types.ts | src/components/template/utils/types.ts | template | feature-private-utils | HIGH |
| src/components/template/UnstructuredBuilder.tsx | src/components/template/components/UnstructuredBuilder.tsx | template | feature-private-component | MEDIUM |
| src/components/test/TestWorkspace.tsx | src/components/test/TestWorkspace.tsx | test | feature-private-component | HIGH |
| src/components/test/core/autofill.ts | src/components/test/utils/autofill.ts | test | feature-private-utils | MEDIUM |
| src/components/test/core/extract.ts | src/components/test/utils/extract.ts | test | feature-private-utils | MEDIUM |
| src/components/test/core/finalize.ts | src/components/test/utils/finalize.ts | test | feature-private-utils | MEDIUM |
| src/components/test/core/match.ts | src/components/test/utils/match.ts | test | feature-private-utils | MEDIUM |
| src/components/test/core/types.ts | src/components/test/utils/types.ts | test | feature-private-utils | MEDIUM |
| src/components/upload/CornerAdjust.tsx | src/components/runocr/components/CornerAdjust.tsx | runocr | feature-private-component | MEDIUM |
| src/components/upload/OcrDocViewer.tsx | src/components/runocr/components/OcrDocViewer.tsx | runocr | feature-private-component | MEDIUM |
| src/components/upload/OcrResultPanel.tsx | src/components/runocr/components/OcrResultPanel.tsx | runocr | feature-private-component | HIGH |
| src/components/upload/UploadWorkspace.tsx | src/components/runocr/RunOcrWorkspace.tsx | runocr | feature-private-component | HIGH |
| src/lib/autofillEngine.ts | src/components/restore/utils/autofillEngine.ts | restore | feature-private-utils | HIGH |
| src/lib/groundTruthStore.ts | src/components/test/utils/groundTruthStore.ts | test | feature-private-utils | MEDIUM |
| src/lib/historyStore.ts | src/components/history/utils/historyStore.ts | history | feature-private-utils | HIGH |
| src/lib/login.ts | src/components/login/utils/login.ts | login | feature-private-utils | HIGH |
| src/lib/profiles.ts | src/components/restore/utils/profiles.ts | restore | feature-private-utils | HIGH |
| src/lib/restoreProfileStore.ts | src/components/restore/utils/restoreProfileStore.ts | restore | feature-private-utils | MEDIUM |
| src/lib/testsets.ts | src/components/test/utils/testsets.ts | test | feature-private-utils | MEDIUM |

## 10. currentPath -> targetPath 매핑표
| currentPath | targetPath | owner | sharedStatus | lines | importedBy | risk | phase | targetRole | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| src/app/api/autofill-cache/route.ts | src/app/api/autofill-cache/route.ts | app-route | route-entry | 26 | 0 | HIGH | Phase 0 | Next.js app route/API entry | [] |
| src/app/api/biz-validate/route.ts | src/app/api/biz-validate/route.ts | app-route | route-entry | 29 | 0 | HIGH | Phase 0 | Next.js app route/API entry | [] |
| src/app/api/ground-truth/route.ts | src/app/api/ground-truth/route.ts | app-route | route-entry | 78 | 0 | HIGH | Phase 0 | Next.js app route/API entry | [] |
| src/app/api/login/route.ts | src/app/api/login/route.ts | app-route | route-entry | 20 | 0 | HIGH | Phase 0 | Next.js app route/API entry | [] |
| src/app/api/ocr-cache/route.ts | src/app/api/ocr-cache/route.ts | app-route | route-entry | 26 | 0 | HIGH | Phase 0 | Next.js app route/API entry | [] |
| src/app/api/ocr-extract/route.ts | src/app/api/ocr-extract/route.ts | app-route | route-entry | 43 | 0 | HIGH | Phase 0 | Next.js app route/API entry | [] |
| src/app/api/test-images/route.ts | src/app/api/test-images/route.ts | app-route | route-entry | 28 | 0 | HIGH | Phase 0 | Next.js app route/API entry | [] |
| src/app/autorestore/page.tsx | src/app/autorestore/page.tsx | app-route | route-entry | 15 | 0 | MEDIUM | Phase 0 | Next.js app route/API entry | [] |
| src/app/globals.css | src/app/globals.css | app-route | route-entry | 2858 | 1 | MEDIUM | Phase 0 | Next.js app route/API entry | [] |
| src/app/history/page.tsx | src/app/history/page.tsx | app-route | route-entry | 15 | 0 | MEDIUM | Phase 0 | Next.js app route/API entry | [] |
| src/app/layout.tsx | src/app/layout.tsx | app-route | route-entry | 29 | 0 | MEDIUM | Phase 0 | Next.js app route/API entry | [] |
| src/app/login/page.tsx | src/app/login/page.tsx | app-route | route-entry | 7 | 0 | MEDIUM | Phase 0 | Next.js app route/API entry | [] |
| src/app/ocr/page.tsx | src/app/ocr/page.tsx | app-route | route-entry | 48 | 0 | MEDIUM | Phase 0 | Next.js app route/API entry | [] |
| src/app/page.tsx | src/app/page.tsx | app-route | route-entry | 14 | 0 | MEDIUM | Phase 0 | Next.js app route/API entry | [] |
| src/app/runocr/page.tsx | src/app/runocr/page.tsx | app-route | route-entry | 12 | 0 | MEDIUM | Phase 0 | Next.js app route/API entry | [] |
| src/app/template/page.tsx | src/app/template/page.tsx | app-route | route-entry | 281 | 0 | MEDIUM | Phase 0 | Next.js app route/API entry | [] |
| src/app/test/page.tsx | src/app/test/page.tsx | app-route | route-entry | 12 | 0 | MEDIUM | Phase 0 | Next.js app route/API entry | [] |
| src/components/autorestore/AutoRestoreWorkspace.tsx | src/components/restore/AutoRestoreWorkspace.tsx | restore | feature-private-component | 434 | 1 | MEDIUM | Phase 4 | Restore workspace UI | [] |
| src/components/common/AppProviders.tsx | src/components/common/AppProviders.tsx | common/components | shared-component | 362 | 11 | MEDIUM | Phase 0 | Shared UI/provider | ["Imported from multiple feature areas: history, login, restore, runocr, template, test."] |
| src/components/common/FileDropzone.tsx | src/common/components/FileDropzone.tsx | common/components | shared-component | 105 | 2 | LOW | Phase 5 | Shared UI/provider | ["Imported from multiple feature areas: runocr, template."] |
| src/components/common/RequireLogin.tsx | src/common/components/RequireLogin.tsx | common/components | shared-component | 35 | 2 | LOW | Phase 5 | Shared UI/provider | ["Imported from multiple feature areas: history, restore."] |
| src/components/history/DetailHistoryView.tsx | src/components/history/DetailHistoryView.tsx | history | feature-private-component | 996 | 1 | HIGH | Phase 4 | History UI | [] |
| src/components/history/HistoryWorkspace.tsx | src/components/history/HistoryWorkspace.tsx | history | feature-private-component | 363 | 1 | MEDIUM | Phase 4 | History UI | [] |
| src/components/history/popup/CreateHistoryPopup.tsx | src/components/history/components/CreateHistoryPopup.tsx | history | feature-private-component | 246 | 1 | MEDIUM | Phase 4 | History UI | [] |
| src/components/history/popup/EditHistoryPopup.tsx | src/components/history/components/EditHistoryPopup.tsx | history | feature-private-component | 252 | 1 | MEDIUM | Phase 4 | History UI | [] |
| src/components/layout/AppShell.tsx | src/components/layout/AppShell.tsx | layout | feature-private-component | 85 | 6 | LOW | Phase 0 | Global shell/layout UI | ["Imported from multiple feature areas: history, restore, runocr, template, test."] |
| src/components/layout/Header.tsx | src/components/layout/Header.tsx | layout | feature-private-component | 77 | 1 | LOW | Phase 0 | Global shell/layout UI | [] |
| src/components/layout/Sidebar.tsx | src/components/layout/Sidebar.tsx | layout | feature-private-component | 296 | 1 | LOW | Phase 0 | Global shell/layout UI | [] |
| src/components/login/LoginWorkspace.tsx | src/components/login/LoginWorkspace.tsx | login | feature-private-component | 179 | 1 | LOW | Phase 0 | Login UI | [] |
| src/components/ocr/OcrAnnotator.tsx | src/components/template/components/OcrAnnotator.tsx | template | feature-private-component | 442 | 2 | HIGH | Phase 3 | Template editor UI | [] |
| src/components/ocr/OcrCanvasPane.tsx | src/components/template/components/OcrCanvasPane.tsx | template | feature-private-component | 1527 | 2 | HIGH | Phase 3 | Template editor UI | ["Imported from multiple feature areas: runocr, template."] |
| src/components/ocr/OcrRightPanel.tsx | src/components/template/components/OcrRightPanel.tsx | template | feature-private-component | 507 | 1 | HIGH | Phase 3 | Template editor UI | [] |
| src/components/ocr/TemplateWorkspace.tsx | src/components/template/TemplateWorkspace.tsx | template | feature-private-component | 180 | 1 | MEDIUM | Phase 3 | Template editor UI | [] |
| src/components/ocr/core/export.ts | src/components/template/utils/export.ts | template | feature-private-utils | 90 | 1 | MEDIUM | Phase 3 | Template editor core logic | ["Could become common/utils if RunOCR also consumes template core later."] |
| src/components/ocr/core/ops.ts | src/components/template/utils/ops.ts | template | feature-private-utils | 99 | 3 | MEDIUM | Phase 3 | Template editor core logic | ["Could become common/utils if RunOCR also consumes template core later."] |
| src/components/ocr/core/table.ts | src/components/template/utils/table.ts | template | feature-private-utils | 151 | 3 | MEDIUM | Phase 3 | Template editor core logic | ["Could become common/utils if RunOCR also consumes template core later."] |
| src/components/ocr/core/types.ts | src/components/template/utils/types.ts | template | feature-private-utils | 110 | 6 | HIGH | Phase 3 | Template editor core logic | ["Could become common/utils if RunOCR also consumes template core later.", "Imported from multiple feature areas: runocr, template.", "Type/declaration file: do not judge by importedBy only."] |
| src/components/template/UnstructuredBuilder.tsx | src/components/template/components/UnstructuredBuilder.tsx | template | feature-private-component | 311 | 1 | MEDIUM | Phase 3 | Template helper UI | [] |
| src/components/test/TestWorkspace.tsx | src/components/test/TestWorkspace.tsx | test | feature-private-component | 6409 | 1 | HIGH | Phase 6 | Internal QA/test UI and runner logic | ["TestWorkspace work requires explicit user confirmation before changes."] |
| src/components/test/core/autofill.ts | src/components/test/utils/autofill.ts | test | feature-private-utils | 367 | 2 | MEDIUM | Phase 6 | Internal QA/test UI and runner logic | ["TestWorkspace work requires explicit user confirmation before changes."] |
| src/components/test/core/extract.ts | src/components/test/utils/extract.ts | test | feature-private-utils | 127 | 1 | MEDIUM | Phase 6 | Internal QA/test UI and runner logic | ["TestWorkspace work requires explicit user confirmation before changes."] |
| src/components/test/core/finalize.ts | src/components/test/utils/finalize.ts | test | feature-private-utils | 594 | 0 | MEDIUM | Phase 6 | Internal QA/test UI and runner logic | ["TestWorkspace work requires explicit user confirmation before changes."] |
| src/components/test/core/match.ts | src/components/test/utils/match.ts | test | feature-private-utils | 54 | 3 | MEDIUM | Phase 6 | Internal QA/test UI and runner logic | ["TestWorkspace work requires explicit user confirmation before changes."] |
| src/components/test/core/types.ts | src/components/test/utils/types.ts | test | feature-private-utils | 173 | 3 | MEDIUM | Phase 6 | Internal QA/test UI and runner logic | ["TestWorkspace work requires explicit user confirmation before changes.", "Type/declaration file: do not judge by importedBy only."] |
| src/components/upload/CornerAdjust.tsx | src/components/runocr/components/CornerAdjust.tsx | runocr | feature-private-component | 174 | 1 | MEDIUM | Phase 1 | RunOCR upload/result UI | [] |
| src/components/upload/OcrDocViewer.tsx | src/components/runocr/components/OcrDocViewer.tsx | runocr | feature-private-component | 224 | 1 | MEDIUM | Phase 1 | RunOCR upload/result UI | [] |
| src/components/upload/OcrResultPanel.tsx | src/components/runocr/components/OcrResultPanel.tsx | runocr | feature-private-component | 1660 | 2 | HIGH | Phase 1 | RunOCR upload/result UI | [] |
| src/components/upload/UploadWorkspace.tsx | src/components/runocr/RunOcrWorkspace.tsx | runocr | feature-private-component | 1587 | 1 | HIGH | Phase 1 | RunOCR upload/result UI | [] |
| src/lib/autofillEngine.ts | src/components/restore/utils/autofillEngine.ts | restore | feature-private-utils | 485 | 3 | HIGH | Phase 4 | Autofill/restore matching engine | ["Contains IO/browser/API storage signal; verify feature boundary before move.", "Imported from multiple feature areas: history, runocr."] |
| src/lib/axios.ts | src/common/utils/axios.ts | common/utils | shared-utils | 137 | 2 | MEDIUM | Phase 5 | API client | ["Contains IO/browser/API storage signal; verify feature boundary before move.", "Imported from multiple feature areas: history, login."] |
| src/lib/bizNumber.ts | src/common/utils/bizNumber.ts | common/utils | shared-utils | 92 | 6 | LOW | Phase 5 | Business number validation | ["Imported from multiple feature areas: history, runocr, test."] |
| src/lib/cleanJsonBuilder.ts | src/common/utils/cleanJsonBuilder.ts | common/utils | shared-utils | 171 | 1 | MEDIUM | Phase 5 | Clean JSON builder | ["React signal found; verify before placing under utils."] |
| src/lib/groundTruthStore.ts | src/components/test/utils/groundTruthStore.ts | test | feature-private-utils | 97 | 1 | MEDIUM | Phase 6 | Ground truth storage | ["Contains IO/browser/API storage signal; verify feature boundary before move."] |
| src/lib/historyStore.ts | src/components/history/utils/historyStore.ts | history | feature-private-utils | 807 | 4 | HIGH | Phase 4 | History storage | ["Contains IO/browser/API storage signal; verify feature boundary before move.", "Imported from multiple feature areas: history, runocr."] |
| src/lib/imageStore.ts | src/common/utils/imageStore.ts | common/utils | shared-utils | 117 | 4 | MEDIUM | Phase 5 | Image/cache store | ["Contains IO/browser/API storage signal; verify feature boundary before move.", "Imported from multiple feature areas: runocr, template."] |
| src/lib/invoiceFieldLabels.ts | src/common/utils/invoiceFieldLabels.ts | common/utils | shared-utils | 65 | 3 | LOW | Phase 5 | Invoice field label policy | ["Imported from multiple feature areas: history, runocr."] |
| src/lib/invoiceTableDisplay.ts | src/common/utils/invoiceTableDisplay.ts | common/utils | shared-utils | 335 | 1 | HIGH | Phase 5 | Invoice table display policy | [] |
| src/lib/login.ts | src/components/login/utils/login.ts | login | feature-private-utils | 59 | 4 | HIGH | Phase 0 | Login helper | ["Contains IO/browser/API storage signal; verify feature boundary before move.", "Imported from multiple feature areas: layout, login."] |
| src/lib/markdownReportBuilder.ts | src/common/utils/markdownReportBuilder.ts | common/utils | shared-utils | 81 | 1 | MEDIUM | Phase 5 | Markdown report builder | ["React signal found; verify before placing under utils."] |
| src/lib/ocrResultFormatters.ts | src/common/utils/ocrResultFormatters.ts | common/utils | shared-utils | 120 | 0 | MEDIUM | Phase 5 | OCR result formatters | ["React signal found; verify before placing under utils."] |
| src/lib/profiles.ts | src/components/restore/utils/profiles.ts | restore | feature-private-utils | 484 | 1 | HIGH | Phase 4 | Restore/autofill profile definitions | [] |
| src/lib/restoreProfileStore.ts | src/components/restore/utils/restoreProfileStore.ts | restore | feature-private-utils | 86 | 1 | MEDIUM | Phase 4 | Restore profile storage | ["Contains IO/browser/API storage signal; verify feature boundary before move."] |
| src/lib/structuredTableViewModel.ts | src/common/utils/structuredTableViewModel.ts | common/utils | shared-utils | 140 | 1 | MEDIUM | Phase 5 | Structured table view model helper | ["React signal found; verify before placing under utils."] |
| src/lib/testsets.ts | src/components/test/utils/testsets.ts | test | feature-private-utils | 217 | 6 | MEDIUM | Phase 6 | Testset loader | [] |
| src/lib/theme.ts | src/common/utils/theme.ts | common/utils | shared-utils | 42 | 1 | LOW | Phase 5 | Theme constants | ["Contains IO/browser/API storage signal; verify feature boundary before move.", "React signal found; verify before placing under utils."] |
| src/types/utif.d.ts | src/common/types/utif.d.ts | common/types | shared-types | 1 | 0 | MEDIUM | Phase 5 | Shared type declaration | ["Type/declaration file: do not judge by importedBy only."] |

## 11. 공통으로 빼야 할 파일
- `src/lib/cleanJsonBuilder.ts`, `markdownReportBuilder.ts`, `structuredTableViewModel.ts`, `invoiceTableDisplay.ts`, `ocrResultFormatters.ts`는 Preview/Clean JSON/Markdown/table 정책 계층이라 `src/common/utils` 후보.
- `src/components/common/FileDropzone.tsx`, `RequireLogin.tsx`는 `src/common/components` 후보.
- `src/types/utif.d.ts`는 `src/common/types` 후보. 단, declaration file은 importedBy만으로 삭제/이동 판단하지 않는다.

## 12. feature 안에 남겨야 할 파일
- RunOCR 전용: `src/components/upload/*` -> `src/components/runocr`.
- Template 전용: `src/components/ocr/*`, `src/components/template/*`, `src/components/ocr/core/*`.
- History 전용: `src/components/history/*`, `src/lib/historyStore.ts`.
- Restore 전용: `src/components/autorestore/*`, `src/lib/restoreProfileStore.ts`, `autofillEngine.ts`, `profiles.ts`.
- Test 전용: `src/components/test/*`, `src/lib/testsets.ts`, `groundTruthStore.ts`.

## 13. review needed 파일
| currentPath | targetPath | owner | sharedStatus | risk | notes |
| --- | --- | --- | --- | --- | --- |

## 14. 위험도 평가
- HIGH: app route/API entry, 큰 workspace, canvas/template core, shared policy util, TestWorkspace.
- MEDIUM: 여러 import 경로 변경이 필요한 feature component/utils.
- LOW: import 수가 적고 목표 위치가 명확한 단순 이동.

## 15. phase별 이동 계획
| phase | scope | risk | validation | notes |
| --- | --- | --- | --- | --- |
| Phase 0 | 목표 구조 문서화/route 유지 | LOW | typecheck/build | 실제 이동 전 기준선 |
| Phase 1 | components/upload -> components/runocr | HIGH | /runocr smoke + runners | UploadWorkspace rename 포함 |
| Phase 2 | RunOCR 내부 utils/components 분리 | HIGH | /runocr smoke + runners | 이동 후 내부 분리 |
| Phase 3 | template/ocr 폴더 정리 | HIGH | /template, /ocr smoke | canvas/core 영향 큼 |
| Phase 4 | restore/history 네이밍 및 utils 위치 정리 | MEDIUM | /autorestore, /history smoke | store import 영향 확인 |
| Phase 5 | src/lib -> src/common/utils/types/components | HIGH | 전체 runners + typecheck/build | 공통 import 영향 큼 |
| Phase 6 | TestWorkspace 및 test utils | HIGH | /test smoke + user confirmation | 사용자 확인 전 진행 금지 |

## 16. phase별 검증 계획
- 공통: `npm run typecheck`, `npm run build`.
- RunOCR 이동 후: `/runocr` 업로드/Preview smoke, Clean JSON runner, Markdown check, table_view_model runner.
- Template 이동 후: `/template` 및 `/ocr` route 확인, 영역/캔버스 smoke.
- Restore/History 이동 후: `/autorestore`, `/history` route smoke.
- Common 이동 후: 전체 typecheck/build와 주요 runner 재수행.

## 17. TestWorkspace gate
- `TestWorkspace.tsx`는 매우 큰 내부 QA 화면이며 Phase 6으로만 분류한다.
- TestWorkspace 분리/이동은 사용자에게 먼저 확인한 뒤 별도 작업으로 진행한다.

## 18. Typecheck/Build 결과
| command | status | exit | seconds | known stderr noise |
| --- | --- | ---: | ---: | --- |
| npm.cmd run typecheck | PASS | 0 | 1.908 | False |
| npm.cmd run build | PASS | 0 | 13.188 | True |

## 19. 다음 작업 추천
1. 3D4 display policy fix 완료.
2. Phase 0 목표 구조 문서화 확정.
3. Phase 1 RunOCR 폴더 이동 precheck/이동.
4. Phase 2 RunOCR 내부 utils 분리.
5. Phase 3 Template 정리.
6. Phase 4 Restore/History 정리.
7. Phase 5 Common 이동.
8. Phase 6 TestWorkspace는 사용자 확인 후 별도 진행.
