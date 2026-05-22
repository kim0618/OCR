# FRONTEND FILE INVENTORY USAGE PRECHECK 20260521

## 1. 사용 도구와 모델
- 사용 도구: Codex
- 사용 모델: Codex
- 작업명: `CODEX_FRONTEND_FILE_INVENTORY_USAGE_PRECHECK_NO_PROD_MODIFY`

## 2. 코드 수정 여부
- 운영 코드 수정 없음.
- 파일 삭제/이동/import 수정/리팩토링 없음.
- 현재 dirty 상태는 원복하지 않음.

## 3. 생성 파일
- `tmp/codex_frontend_file_inventory_usage_precheck.py`
- `docs/FRONTEND_FILE_INVENTORY_USAGE_PRECHECK_20260521.md`
- `docs/FRONTEND_FILE_INVENTORY_USAGE_PRECHECK_20260521.json`
- `docs/FRONTEND_FILE_INVENTORY_USAGE_PRECHECK_TABLE_20260521.csv`

## 4. 분석 범위
- projectRoot: `D:\Free_Vue\OCR\mysuit-ocr`
- included: `src/app`, `src/components`, `src/lib`, `src/types`, 기타 `src` 하위 대상 확장자
- excluded: node_modules, .next, dist, build, public, backup, tmp, docs

## 5. 전체 파일 수 요약
- totalFiles: 66
- usageStatusCounts: `{'DELETE_CANDIDATE_SAFE_CHECK_REQUIRED': 1, 'KEEP_BUT_RELOCATE_CANDIDATE': 5, 'KEEP_BUT_SPLIT_CANDIDATE': 8, 'USED_CONFIRMED': 50, 'USED_INDIRECT': 2}`
- routeReachableFiles: 63
- unresolved local imports: 0

## 6. Route Reachability 요약
| route | entry | reachableCount | directImports |
| --- | --- | --- | --- |
| /api/autofill-cache (api route) | src/app/api/autofill-cache/route.ts | 2 | src/lib/testsets.ts |
| /api/biz-validate (api route) | src/app/api/biz-validate/route.ts | 1 |  |
| /api/ground-truth (api route) | src/app/api/ground-truth/route.ts | 2 | src/lib/testsets.ts |
| /api/login (api route) | src/app/api/login/route.ts | 1 |  |
| /api/ocr-cache (api route) | src/app/api/ocr-cache/route.ts | 2 | src/lib/testsets.ts |
| /api/ocr-extract (api route) | src/app/api/ocr-extract/route.ts | 1 |  |
| /api/test-images (api route) | src/app/api/test-images/route.ts | 2 | src/lib/testsets.ts |
| /autorestore | src/app/autorestore/page.tsx | 10 | src/components/autorestore/AutoRestoreWorkspace.tsx, src/components/common/RequireLogin.tsx, src/components/layout/AppShell.tsx |
| /history | src/app/history/page.tsx | 21 | src/components/common/RequireLogin.tsx, src/components/history/HistoryWorkspace.tsx, src/components/layout/AppShell.tsx |
| ROOT_LAYOUT | src/app/layout.tsx | 2 | src/components/common/AppProviders.tsx |
| /login | src/app/login/page.tsx | 5 | src/components/login/LoginWorkspace.tsx |
| /ocr | src/app/ocr/page.tsx | 17 | src/components/layout/AppShell.tsx, src/components/ocr/OcrAnnotator.tsx, src/components/ocr/TemplateWorkspace.tsx |
| / | src/app/page.tsx | 1 |  |
| /runocr | src/app/runocr/page.tsx | 27 | src/components/layout/AppShell.tsx, src/components/upload/UploadWorkspace.tsx |
| /template | src/app/template/page.tsx | 17 | src/components/layout/AppShell.tsx, src/components/ocr/OcrAnnotator.tsx, src/components/template/UnstructuredBuilder.tsx, src/lib/imageStore.ts |
| /test | src/app/test/page.tsx | 17 | src/components/layout/AppShell.tsx, src/components/test/TestWorkspace.tsx |

## 7. Import/Export Graph 요약
- local import edges: 118
- alias import users: 23
- relative import users: 34
- barrel/export re-export files: 1
- dynamic import/require signals: 8

## 8. 파일별 인벤토리 표
| path | role | importedBy | imports | usageStatus | locationAssessment | delete | relocate | split | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| src/app/api/autofill-cache/route.ts | Next.js API route handler: /api/autofill-cache (api route) | 0 | 1 | USED_CONFIRMED | 적절 |  |  |  |  |
| src/app/api/biz-validate/route.ts | Next.js API route handler: /api/biz-validate (api route) | 0 | 0 | USED_CONFIRMED | 적절 |  |  |  |  |
| src/app/api/ground-truth/route.ts | Next.js API route handler: /api/ground-truth (api route) | 0 | 1 | USED_CONFIRMED | 적절 |  |  |  |  |
| src/app/api/login/route.ts | Next.js API route handler: /api/login (api route) | 0 | 0 | USED_CONFIRMED | 적절 |  |  |  |  |
| src/app/api/ocr-cache/route.ts | Next.js API route handler: /api/ocr-cache (api route) | 0 | 1 | USED_CONFIRMED | 적절 |  |  |  |  |
| src/app/api/ocr-extract/route.ts | Next.js API route handler: /api/ocr-extract (api route) | 0 | 0 | USED_CONFIRMED | 적절 |  |  |  |  |
| src/app/api/test-images/route.ts | Next.js API route handler: /api/test-images (api route) | 0 | 1 | USED_CONFIRMED | 적절 |  |  |  |  |
| src/app/autorestore/page.tsx | Next.js App Router entry: /autorestore | 0 | 3 | USED_CONFIRMED | 적절 |  |  |  |  |
| src/app/globals.css | 전역 CSS 스타일 | 0 | 0 | USED_INDIRECT | 적절 |  |  |  |  |
| src/app/history/page.tsx | Next.js App Router entry: /history | 0 | 3 | USED_CONFIRMED | 적절 |  |  |  |  |
| src/app/layout.tsx | Next.js App Router entry: ROOT_LAYOUT | 0 | 1 | USED_CONFIRMED | 적절 |  |  |  |  |
| src/app/login/page.tsx | Next.js App Router entry: /login | 0 | 1 | USED_CONFIRMED | 적절 |  |  |  |  |
| src/app/ocr/page.tsx | Next.js App Router entry: /ocr | 0 | 3 | USED_CONFIRMED | 적절 |  |  |  |  |
| src/app/page.tsx | Next.js App Router entry: / | 0 | 0 | USED_CONFIRMED | 적절 |  |  |  |  |
| src/app/runocr/page.tsx | Next.js App Router entry: /runocr | 0 | 2 | USED_CONFIRMED | 적절 |  |  |  |  |
| src/app/template/page.tsx | Next.js App Router entry: /template | 0 | 4 | USED_CONFIRMED | 적절 |  |  |  |  |
| src/app/test/page.tsx | Next.js App Router entry: /test | 0 | 2 | USED_CONFIRMED | 적절 |  |  |  |  |
| src/components/autorestore/AutoRestoreWorkspace.tsx | AutoRestoreWorkspace 화면 workspace 컴포넌트 | 1 | 2 | KEEP_BUT_RELOCATE_CANDIDATE | 기능 위치는 대체로 적절하지만 메뉴/도메인명이 restore라면 폴더명 정리 후보 |  | Y |  |  |
| src/components/common/AppProviders.tsx | AppProviders UI 컴포넌트 | 11 | 0 | USED_CONFIRMED | 적절 |  |  |  |  |
| src/components/common/FileDropzone.tsx | FileDropzone UI 컴포넌트 | 2 | 0 | USED_CONFIRMED | 적절 |  |  |  |  |
| src/components/common/RequireLogin.tsx | RequireLogin UI 컴포넌트 | 2 | 1 | USED_CONFIRMED | 적절 |  |  |  |  |
| src/components/history/DetailHistoryView.tsx | DetailHistoryView UI 컴포넌트 | 1 | 8 | KEEP_BUT_SPLIT_CANDIDATE | 적절 |  |  | Y | line count >= 500; 분리 후보 |
| src/components/history/HistoryWorkspace.tsx | HistoryWorkspace 화면 workspace 컴포넌트 | 1 | 6 | USED_CONFIRMED | 적절 |  |  |  |  |
| src/components/history/popup/CreateHistoryPopup.tsx | CreateHistoryPopup UI 컴포넌트 | 1 | 0 | USED_CONFIRMED | 적절 |  |  |  |  |
| src/components/history/popup/EditHistoryPopup.tsx | EditHistoryPopup UI 컴포넌트 | 1 | 0 | USED_CONFIRMED | 적절 |  |  |  |  |
| src/components/layout/AppShell.tsx | AppShell UI 컴포넌트 | 6 | 2 | USED_CONFIRMED | 적절 |  |  |  |  |
| src/components/layout/Header.tsx | Header UI 컴포넌트 | 1 | 2 | USED_CONFIRMED | 적절 |  |  |  |  |
| src/components/layout/Sidebar.tsx | Sidebar UI 컴포넌트 | 1 | 0 | USED_CONFIRMED | 적절 |  |  |  |  |
| src/components/login/LoginWorkspace.tsx | LoginWorkspace 화면 workspace 컴포넌트 | 1 | 3 | USED_CONFIRMED | 적절 |  |  |  |  |
| src/components/ocr/OcrAnnotator.tsx | 템플릿 영역/테이블 주석 편집용 OCR annotator 화면 | 2 | 6 | USED_CONFIRMED | 적절 |  |  |  |  |
| src/components/ocr/OcrCanvasPane.tsx | OcrCanvasPane UI 컴포넌트 | 2 | 4 | KEEP_BUT_SPLIT_CANDIDATE | 적절 |  |  | Y | line count >= 500; 분리 후보 |
| src/components/ocr/OcrRightPanel.tsx | OcrRightPanel UI 컴포넌트 | 1 | 3 | KEEP_BUT_SPLIT_CANDIDATE | 적절 |  |  | Y | line count >= 500; 분리 후보 |
| src/components/ocr/TemplateWorkspace.tsx | TemplateWorkspace 화면 workspace 컴포넌트 | 1 | 1 | USED_CONFIRMED | 적절 |  |  |  |  |
| src/components/ocr/core/export.ts | OCR annotator/template export payload 생성 로직 | 1 | 3 | KEEP_BUT_RELOCATE_CANDIDATE | 순수 로직 성격이 강해 components보다 src/lib/ocr 또는 features/ocr/core 이동 후보 |  | Y |  | 이동 전 import 영향 범위 확인 필요 |
| src/components/ocr/core/ops.ts | OCR annotator 상태 조작/유틸성 operation 로직 | 4 | 1 | KEEP_BUT_RELOCATE_CANDIDATE | 순수 로직 성격이 강해 components보다 src/lib/ocr 또는 features/ocr/core 이동 후보 |  | Y |  | 이동 전 import 영향 범위 확인 필요 |
| src/components/ocr/core/table.ts | OCR 템플릿 테이블/행/컬럼 관련 순수 계산 로직 | 3 | 2 | KEEP_BUT_RELOCATE_CANDIDATE | 순수 로직 성격이 강해 components보다 src/lib/ocr 또는 features/ocr/core 이동 후보 |  | Y |  | 이동 전 import 영향 범위 확인 필요 |
| src/components/ocr/core/types.ts | OCR annotator core 타입 정의 | 7 | 0 | KEEP_BUT_RELOCATE_CANDIDATE | 순수 로직 성격이 강해 components보다 src/lib/ocr 또는 features/ocr/core 이동 후보 |  | Y |  | 이동 전 import 영향 범위 확인 필요 |
| src/components/template/UnstructuredBuilder.tsx | UnstructuredBuilder UI 컴포넌트 | 1 | 1 | USED_CONFIRMED | 적절 |  |  |  |  |
| src/components/test/TestWorkspace.tsx | 테스트셋 실행/비교/리포트 생성을 담당하는 내부 QA workspace | 1 | 10 | KEEP_BUT_SPLIT_CANDIDATE | 적절 |  |  | Y | line count >= 500; 분리 후보; TestWorkspace 정리는 사용자 확인 후 별도 작업 필요 |
| src/components/test/core/autofill.ts | autofill feature 내부 core/helper | 2 | 3 | USED_CONFIRMED | 적절 |  |  |  |  |
| src/components/test/core/extract.ts | extract feature 내부 core/helper | 1 | 2 | USED_CONFIRMED | 적절 |  |  |  |  |
| src/components/test/core/finalize.ts | finalize feature 내부 core/helper | 1 | 3 | KEEP_BUT_SPLIT_CANDIDATE | 적절 |  |  | Y | line count >= 500; 분리 후보 |
| src/components/test/core/match.ts | match feature 내부 core/helper | 3 | 1 | USED_CONFIRMED | 적절 |  |  |  |  |
| src/components/test/core/types.ts | types feature 내부 core/helper | 5 | 0 | USED_CONFIRMED | 적절 |  |  |  |  |
| src/components/upload/CornerAdjust.tsx | CornerAdjust UI 컴포넌트 | 1 | 0 | USED_CONFIRMED | 적절 |  |  |  |  |
| src/components/upload/OcrDocViewer.tsx | OcrDocViewer UI 컴포넌트 | 1 | 2 | USED_CONFIRMED | 적절 |  |  |  |  |
| src/components/upload/OcrResultPanel.tsx | OCR 결과 Preview/Custom/Validation/Clean JSON/Markdown 표시 패널 | 2 | 7 | KEEP_BUT_SPLIT_CANDIDATE | 적절 |  |  | Y | line count >= 500; 분리 후보; 최근 Clean JSON/Markdown/formatter/table view model helper 분리와 연결됨 |
| src/components/upload/UploadWorkspace.tsx | RunOCR 업로드 화면의 파일 선택, OCR 실행, 결과 패널 조합 workspace | 1 | 11 | KEEP_BUT_SPLIT_CANDIDATE | 적절 |  |  | Y | line count >= 500; 분리 후보 |
| src/lib/autofillEngine.ts | autofillEngine 순수 helper 또는 클라이언트 유틸 | 4 | 3 | USED_CONFIRMED | 적절 |  |  |  |  |
| src/lib/axios.ts | axios 순수 helper 또는 클라이언트 유틸 | 2 | 1 | USED_CONFIRMED | 적절 |  |  |  |  |
| src/lib/bizNumber.ts | bizNumber 순수 helper 또는 클라이언트 유틸 | 6 | 0 | USED_CONFIRMED | 적절 |  |  |  |  |
| src/lib/cleanJsonBuilder.ts | OCR 결과를 Clean JSON v1 contract로 변환하는 순수 helper | 1 | 1 | USED_CONFIRMED | 적절 |  |  |  |  |
| src/lib/groundTruthStore.ts | groundTruthStore 상태/스토리지 접근 helper | 2 | 1 | USED_CONFIRMED | 적절 |  |  |  |  |
| src/lib/historyStore.ts | historyStore 상태/스토리지 접근 helper | 5 | 1 | KEEP_BUT_SPLIT_CANDIDATE | 적절 |  |  | Y | line count >= 500; 분리 후보 |
| src/lib/imageStore.ts | imageStore 상태/스토리지 접근 helper | 4 | 0 | USED_CONFIRMED | 적절 |  |  |  |  |
| src/lib/invoiceFieldLabels.ts | invoiceFieldLabels 순수 helper 또는 클라이언트 유틸 | 3 | 0 | USED_CONFIRMED | 적절 |  |  |  |  |
| src/lib/invoiceTableDisplay.ts | 거래명세서 tableRows 표시 컬럼/정규화/rowIndex 정책 helper | 4 | 0 | USED_CONFIRMED | 적절 |  |  |  |  |
| src/lib/login.ts | login 순수 helper 또는 클라이언트 유틸 | 4 | 0 | USED_CONFIRMED | 적절 |  |  |  |  |
| src/lib/markdownReportBuilder.ts | OCR 결과를 Markdown v1 report 문자열로 변환하는 helper | 1 | 1 | USED_CONFIRMED | 적절 |  |  |  |  |
| src/lib/ocrResultFormatters.ts | OCR 결과 라벨/금액/table field formatting helper | 2 | 2 | USED_CONFIRMED | 적절 |  |  |  |  |
| src/lib/profiles.ts | profiles 순수 helper 또는 클라이언트 유틸 | 1 | 1 | USED_CONFIRMED | 적절 |  |  |  |  |
| src/lib/restoreProfileStore.ts | restoreProfileStore 상태/스토리지 접근 helper | 3 | 0 | USED_CONFIRMED | 적절 |  |  |  |  |
| src/lib/structuredTableViewModel.ts | structured table input을 trimmed table view model로 변환하는 순수 helper | 0 | 0 | DELETE_CANDIDATE_SAFE_CHECK_REQUIRED | 적절 | Y |  |  |  |
| src/lib/testsets.ts | testsets 순수 helper 또는 클라이언트 유틸 | 6 | 0 | USED_CONFIRMED | 적절 |  |  |  |  |
| src/lib/theme.ts | theme 순수 helper 또는 클라이언트 유틸 | 1 | 0 | USED_CONFIRMED | 적절 |  |  |  |  |
| src/types/utif.d.ts | utif 패키지 TypeScript ambient declaration | 0 | 0 | USED_INDIRECT | 적절 |  |  |  | ambient declaration은 import graph만으로 삭제 판단 금지 |

## 9. 사용 중 파일 목록
- USED_CONFIRMED: 50
- USED_INDIRECT: 2

## 10. 미사용 의심/삭제 후보 목록
| path | status | role | locationAssessment | notes |
| --- | --- | --- | --- | --- |
| src/lib/structuredTableViewModel.ts | DELETE_CANDIDATE_SAFE_CHECK_REQUIRED | structured table input을 trimmed table view model로 변환하는 순수 helper | 적절 |  |

## 11. 위치 조정 후보 목록
| path | status | role | locationAssessment |
| --- | --- | --- | --- |
| src/components/autorestore/AutoRestoreWorkspace.tsx | KEEP_BUT_RELOCATE_CANDIDATE | AutoRestoreWorkspace 화면 workspace 컴포넌트 | 기능 위치는 대체로 적절하지만 메뉴/도메인명이 restore라면 폴더명 정리 후보 |
| src/components/ocr/core/export.ts | KEEP_BUT_RELOCATE_CANDIDATE | OCR annotator/template export payload 생성 로직 | 순수 로직 성격이 강해 components보다 src/lib/ocr 또는 features/ocr/core 이동 후보 |
| src/components/ocr/core/ops.ts | KEEP_BUT_RELOCATE_CANDIDATE | OCR annotator 상태 조작/유틸성 operation 로직 | 순수 로직 성격이 강해 components보다 src/lib/ocr 또는 features/ocr/core 이동 후보 |
| src/components/ocr/core/table.ts | KEEP_BUT_RELOCATE_CANDIDATE | OCR 템플릿 테이블/행/컬럼 관련 순수 계산 로직 | 순수 로직 성격이 강해 components보다 src/lib/ocr 또는 features/ocr/core 이동 후보 |
| src/components/ocr/core/types.ts | KEEP_BUT_RELOCATE_CANDIDATE | OCR annotator core 타입 정의 | 순수 로직 성격이 강해 components보다 src/lib/ocr 또는 features/ocr/core 이동 후보 |

## 12. 큰 파일 TOP 20
| path | lines | role | usageStatus | split | notes |
| --- | --- | --- | --- | --- | --- |
| src/components/test/TestWorkspace.tsx | 6410 | 테스트셋 실행/비교/리포트 생성을 담당하는 내부 QA workspace | KEEP_BUT_SPLIT_CANDIDATE | Y | line count >= 500; 분리 후보; TestWorkspace 정리는 사용자 확인 후 별도 작업 필요 |
| src/app/globals.css | 2859 | 전역 CSS 스타일 | USED_INDIRECT |  |  |
| src/components/upload/OcrResultPanel.tsx | 1650 | OCR 결과 Preview/Custom/Validation/Clean JSON/Markdown 표시 패널 | KEEP_BUT_SPLIT_CANDIDATE | Y | line count >= 500; 분리 후보; 최근 Clean JSON/Markdown/formatter/table view model helper 분리와 연결됨 |
| src/components/upload/UploadWorkspace.tsx | 1588 | RunOCR 업로드 화면의 파일 선택, OCR 실행, 결과 패널 조합 workspace | KEEP_BUT_SPLIT_CANDIDATE | Y | line count >= 500; 분리 후보 |
| src/components/ocr/OcrCanvasPane.tsx | 1528 | OcrCanvasPane UI 컴포넌트 | KEEP_BUT_SPLIT_CANDIDATE | Y | line count >= 500; 분리 후보 |
| src/components/history/DetailHistoryView.tsx | 997 | DetailHistoryView UI 컴포넌트 | KEEP_BUT_SPLIT_CANDIDATE | Y | line count >= 500; 분리 후보 |
| src/lib/historyStore.ts | 808 | historyStore 상태/스토리지 접근 helper | KEEP_BUT_SPLIT_CANDIDATE | Y | line count >= 500; 분리 후보 |
| src/components/test/core/finalize.ts | 595 | finalize feature 내부 core/helper | KEEP_BUT_SPLIT_CANDIDATE | Y | line count >= 500; 분리 후보 |
| src/components/ocr/OcrRightPanel.tsx | 508 | OcrRightPanel UI 컴포넌트 | KEEP_BUT_SPLIT_CANDIDATE | Y | line count >= 500; 분리 후보 |
| src/lib/autofillEngine.ts | 486 | autofillEngine 순수 helper 또는 클라이언트 유틸 | USED_CONFIRMED |  |  |
| src/lib/profiles.ts | 485 | profiles 순수 helper 또는 클라이언트 유틸 | USED_CONFIRMED |  |  |
| src/components/ocr/OcrAnnotator.tsx | 443 | 템플릿 영역/테이블 주석 편집용 OCR annotator 화면 | USED_CONFIRMED |  |  |
| src/components/autorestore/AutoRestoreWorkspace.tsx | 435 | AutoRestoreWorkspace 화면 workspace 컴포넌트 | KEEP_BUT_RELOCATE_CANDIDATE |  |  |
| src/components/test/core/autofill.ts | 368 | autofill feature 내부 core/helper | USED_CONFIRMED |  |  |
| src/components/history/HistoryWorkspace.tsx | 364 | HistoryWorkspace 화면 workspace 컴포넌트 | USED_CONFIRMED |  |  |
| src/components/common/AppProviders.tsx | 363 | AppProviders UI 컴포넌트 | USED_CONFIRMED |  |  |
| src/components/template/UnstructuredBuilder.tsx | 312 | UnstructuredBuilder UI 컴포넌트 | USED_CONFIRMED |  |  |
| src/components/layout/Sidebar.tsx | 297 | Sidebar UI 컴포넌트 | USED_CONFIRMED |  |  |
| src/lib/invoiceTableDisplay.ts | 294 | 거래명세서 tableRows 표시 컬럼/정규화/rowIndex 정책 helper | USED_CONFIRMED |  |  |
| src/app/template/page.tsx | 282 | Next.js App Router entry: /template | USED_CONFIRMED |  |  |

## 13. 폴더 구조 평가
| folder | files | assessment | risk | recommendation |
| --- | --- | --- | --- | --- |
| src/app | 17 | Next.js App Router entry와 API route 위치로 적절 | route entry이므로 이동 위험 높음 | precheck only; no move in this task |
| src/components/autorestore | 1 | 자동 복원 feature 위치 | 메뉴명이 restore라면 폴더명 rename precheck 후보 | precheck only; no move in this task |
| src/components/common | 3 | 공통 UI/provider 컴포넌트 위치로 대체로 적절 | feature 전용 컴포넌트가 섞이면 later relocate 검토 | precheck only; no move in this task |
| src/components/history | 4 | history feature UI 위치로 적절 | DetailHistoryView가 크면 section 분리 후보 | precheck only; no move in this task |
| src/components/layout | 3 | App shell/header/sidebar layout 위치로 적절 | 전역 navigation 변경 시 영향 큼 | precheck only; no move in this task |
| src/components/login | 1 | login feature UI 위치로 적절 | 현 상태 유지 권장 | precheck only; no move in this task |
| src/components/ocr | 8 | 템플릿 annotator/ocr 편집 UI feature 위치 | TemplateWorkspace/UnstructuredBuilder 경계 확인 필요 | precheck only; no move in this task |
| src/components/ocr/core | 4 | OCR annotator 내부 순수 로직 위치 | src/lib/ocr 또는 features/ocr/core 이동 후보 | relocate precheck candidate |
| src/components/template | 1 | template builder UI 위치 | ocr/template feature boundary precheck 후보 | precheck only; no move in this task |
| src/components/test | 6 | 내부 QA/test workspace 위치 | 큰 파일 분리 전 사용자 확인 필요 | precheck only; no move in this task |
| src/components/upload | 4 | RunOCR 업로드/결과 feature 위치로 적절 | OcrResultPanel/UploadWorkspace는 split 후보 | precheck only; no move in this task |
| src/lib | 17 | 순수 helper/store 위치로 적절 | 브라우저 저장소 helper와 순수 helper 혼재는 문서화 필요 | precheck only; no move in this task |
| src/types | 1 | ambient/type declaration 위치로 적절 | import graph만으로 삭제 판단 금지 | precheck only; no move in this task |

## 14. 특별 확인 대상 결과
| path | usageStatus | locationAssessment | role | notes |
| --- | --- | --- | --- | --- |
| src/components/ocr/OcrAnnotator.tsx | USED_CONFIRMED | 적절 | 템플릿 영역/테이블 주석 편집용 OCR annotator 화면 |  |
| src/types/utif.d.ts | USED_INDIRECT | 적절 | utif 패키지 TypeScript ambient declaration | ambient declaration은 import graph만으로 삭제 판단 금지 |
| src/components/test/TestWorkspace.tsx | KEEP_BUT_SPLIT_CANDIDATE | 적절 | 테스트셋 실행/비교/리포트 생성을 담당하는 내부 QA workspace | line count >= 500; 분리 후보; TestWorkspace 정리는 사용자 확인 후 별도 작업 필요 |
| src/components/upload/OcrResultPanel.tsx | KEEP_BUT_SPLIT_CANDIDATE | 적절 | OCR 결과 Preview/Custom/Validation/Clean JSON/Markdown 표시 패널 | line count >= 500; 분리 후보; 최근 Clean JSON/Markdown/formatter/table view model helper 분리와 연결됨 |
| src/lib/cleanJsonBuilder.ts | USED_CONFIRMED | 적절 | OCR 결과를 Clean JSON v1 contract로 변환하는 순수 helper |  |
| src/lib/markdownReportBuilder.ts | USED_CONFIRMED | 적절 | OCR 결과를 Markdown v1 report 문자열로 변환하는 helper |  |
| src/lib/ocrResultFormatters.ts | USED_CONFIRMED | 적절 | OCR 결과 라벨/금액/table field formatting helper |  |
| src/lib/structuredTableViewModel.ts | DELETE_CANDIDATE_SAFE_CHECK_REQUIRED | 적절 | structured table input을 trimmed table view model로 변환하는 순수 helper |  |
| src/lib/invoiceTableDisplay.ts | USED_CONFIRMED | 적절 | 거래명세서 tableRows 표시 컬럼/정규화/rowIndex 정책 helper |  |
| src/components/ocr/core/export.ts | KEEP_BUT_RELOCATE_CANDIDATE | 순수 로직 성격이 강해 components보다 src/lib/ocr 또는 features/ocr/core 이동 후보 | OCR annotator/template export payload 생성 로직 | 이동 전 import 영향 범위 확인 필요 |
| src/components/ocr/core/ops.ts | KEEP_BUT_RELOCATE_CANDIDATE | 순수 로직 성격이 강해 components보다 src/lib/ocr 또는 features/ocr/core 이동 후보 | OCR annotator 상태 조작/유틸성 operation 로직 | 이동 전 import 영향 범위 확인 필요 |
| src/components/ocr/core/table.ts | KEEP_BUT_RELOCATE_CANDIDATE | 순수 로직 성격이 강해 components보다 src/lib/ocr 또는 features/ocr/core 이동 후보 | OCR 템플릿 테이블/행/컬럼 관련 순수 계산 로직 | 이동 전 import 영향 범위 확인 필요 |
| src/components/ocr/core/types.ts | KEEP_BUT_RELOCATE_CANDIDATE | 순수 로직 성격이 강해 components보다 src/lib/ocr 또는 features/ocr/core 이동 후보 | OCR annotator core 타입 정의 | 이동 전 import 영향 범위 확인 필요 |

## 15. 삭제 전 검증 계획
1. import graph 재확인
2. grep/string reference 재확인
3. dynamic import/require 확인
4. route reachability 확인
5. `npm run typecheck`
6. `npm run build`
7. 주요 화면 수동 확인
8. 삭제 전 백업
9. 삭제 후 diff 확인

## 16. 이동 전 검증 계획
1. import 경로 영향 범위 확인
2. alias import와 상대경로 정책 결정
3. barrel export 영향 확인
4. 이동 전 백업
5. `npm run typecheck`
6. `npm run build`
7. 기능 화면 확인

## 17. 다음 정리 우선순위
1. 삭제 후보 안전 검증 작업을 별도 수행하되 이번 리포트 후보를 즉시 삭제하지 않는다.
2. components/ocr/core 순수 로직 위치 조정 precheck를 별도 수행한다.
3. OcrResultPanel Cycle 1 close-out은 table view model helper 적용 이후 진행한다.
4. TestWorkspace summary/export/tableRows/UI 섹션 분리는 사용자 확인 후 별도 precheck로 진행한다.
5. UploadWorkspace 책임 분리 precheck를 수행한다.
6. History Detail tableRows 표시/분리 precheck를 수행한다.
7. autorestore/restore 네이밍 정리 precheck를 수행한다.

## 18. Typecheck/Build 결과
| command | status | exit | seconds | known stderr noise |
| --- | --- | ---: | ---: | --- |
| npm.cmd run typecheck | PASS | 0 | 1.922 | False |
| npm.cmd run build | PASS | 0 | 16.794 | True |

## 19. Known Stderr Noise
- `ESLint: nextVitals is not iterable` observed: `True`
- build exit code: `0`

## 20. 최종 결론
- 운영 코드 변경 없이 src 파일 인벤토리와 사용처 precheck를 완료했다.
- 삭제/이동 후보는 즉시 조치 대상이 아니라 별도 검증 작업 대상이다.
- TestWorkspace 정리는 사용자 확인 후 별도 작업으로 진행해야 한다.
