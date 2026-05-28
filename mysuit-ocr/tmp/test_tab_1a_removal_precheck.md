## FRONTEND-TEST-TAB-1A Removal Precheck

### 1. Summary
- 운영 코드 수정 여부: 없음. `tmp` 산출물만 생성.
- Test 탭 entrypoint: `src/app/test/page.tsx` -> `src/components/test/TestWorkspace.tsx`.
- TestWorkspace 역할: OCR fixture runner, dataset selector, manifest/profile KPI viewer, GT editor, OCR/cache/autofill cache manager, RunOCR batch runner.
- 가장 위험한 연결점: `src/common/config/testsets.ts`는 TestWorkspace뿐 아니라 `src/app/api/test-images`, `ocr-cache`, `autofill-cache`, `ground-truth` route가 import한다. 즉 Test 탭 제거와 별개로 유지해야 한다.
- 추천 제거 전략: A안(UI hide only)을 1차로 권장. `/test` route와 source는 archive 전까지 유지.
- 추천 다음 phase: `FRONTEND-TEST-TAB-1B-BACKUP-AND-UI-HIDE`.

### 2. Current Test Tab Tree
```text
src/app/test/
  page.tsx

src/components/test/
  TestWorkspace.tsx
  core/
    autofill.ts
    extract.ts
    finalize.ts
    match.ts
    types.ts
  utils/
    profiles.ts

related:
  src/common/config/testsets.ts
  src/app/api/test-images/route.ts
  src/app/api/ocr-cache/route.ts
  src/app/api/autofill-cache/route.ts
  src/app/api/ground-truth/route.ts
  public/data/testsets/**
```

### 3. UI / Route Exposure
- sidebar/menu 위치: `src/components/layout/Sidebar.tsx`의 `DEFAULT_ITEMS`에는 현재 `Template`, `RunOCR`, `History`, `Restore`만 있고 `Test` 항목은 없다. `NavIcon`에는 `test` icon case가 남아 있지만 메뉴 노출은 안 된다.
- `/test` route 위치: `src/app/test/page.tsx`.
- layout/header/app shell 연결: `/test` page가 `AppShell headerTitle={"Test"} scrollMode="fixed"`를 렌더링하고 내부에 `TestWorkspace`를 둔다. `AppShell`은 `Sidebar`와 `Header`를 공통 제공한다.
- auth guard 여부: `/test` route 자체 guard는 발견되지 않았다. `Header`는 login 표시/로그아웃 UI만 처리하고, `src/app/page.tsx`는 `/login`으로 redirect한다.

### 4. TestWorkspace Dependency Map
| dependency | path | purpose | remove impact | keep/archive |
|---|---|---|---|---|
| React hooks | `react` | large client workspace state/UI | route 제거 시 영향 없음 | archive with workspace |
| UI modal/loading | `src/components/layout/AppProviders.tsx` | `useUi` alert/loading | Test 삭제 시 layout 영향 없음 | keep |
| business number utils | `src/common/utils/bizNumber.ts` | NTS/biz anchor normalization | RunOCR/History may still use common util | keep |
| invoice table display | `src/common/utils/invoiceTableDisplay.ts` | table column labels/display policy | RunOCR result panel also references policy | keep |
| test core types | `src/components/test/core/types.ts` | Entry/OCR/autofill/value source types | TestWorkspace compile dependency | archive |
| test core match | `src/components/test/core/match.ts` | similarity/match scoring | Test-only import | archive |
| test core extract | `src/components/test/core/extract.ts` | fallback field extraction/normalization | Test-only import | archive |
| test core autofill | `src/components/test/core/autofill.ts` | GT/cache-based suggestions | Test-only import | archive |
| test core finalize | `src/components/test/core/finalize.ts` | final field view/scoring/status | Test-only import | archive |
| manifest/testset types | `src/common/config/testsets.ts` | dataset metadata and manifest profile types | API routes need it | keep |
| test profiles | `src/components/test/utils/profiles.ts` | documentType -> receipt/finance/document profile policy | TestWorkspace-only runtime importer | archive with Test |
| test images API | `/api/test-images` | image list and TESTSETS payload | Test-only currently, but cheap to keep until route decision | keep for A/B, consider archive in C |
| GT API | `/api/ground-truth` | read/write `ground_truth.json`, migrate legacy `ocr_text` | Test tab primary user; route has storage side effects | keep until storage ownership decided |
| OCR cache API | `/api/ocr-cache` | read/write `ocr_cache.json` | Test tab primary user | keep until storage ownership decided |
| autofill cache API | `/api/autofill-cache` | read/write `autofill_cache.json` | Test tab primary user | keep until storage ownership decided |
| RunOCR proxy/backend | `/api/ocr-extract` or backend `/ocr/extract` | OCR sample runner | shared with RunOCR/Test | keep |
| public testsets | `public/data/testsets/**` | sample images, manifests, GT/cache/autofill fixtures | deletion would break future validation and runners | keep, optional snapshot |

### 5. Test Core File Ownership
| file | role | imported by | reusable outside Test? | recommended action |
|---|---|---|---|---|
| `src/components/test/core/types.ts` | Test-specific receipt field keys, OCR/cache/autofill shapes, thresholds | `TestWorkspace`, all test core files | No direct external import | archive with Test |
| `src/components/test/core/match.ts` | string/field similarity and match result | `TestWorkspace`, `autofill.ts`, `finalize.ts` | Could be generic, but current thresholds are Test-specific | archive |
| `src/components/test/core/extract.ts` | fallback extraction and normalization for test comparison | `TestWorkspace` | No, Test fallback policy | archive |
| `src/components/test/core/autofill.ts` | GT/cache/biz/text suggestion policy | `TestWorkspace`, `finalize.ts` | No, tied to Test GT/cache | archive |
| `src/components/test/core/finalize.ts` | field view, score, final source, status aggregation | `TestWorkspace` | No, tied to Test reporting | archive |

### 6. Test Utils / Profiles / Testsets
- `profiles.ts` 사용처: `src/components/test/TestWorkspace.tsx`가 runtime/type import한다. 다른 `src` runtime import는 발견되지 않았다.
- `profiles.ts`와 `testsets.ts` 관계: `profiles.ts`는 `DocumentType` type을 `src/common/config/testsets.ts`에서 가져와 documentType -> profile policy를 정의한다.
- `common/config/testsets.ts` 사용처: `TestWorkspace`, `profiles.ts`, `src/app/api/test-images/route.ts`, `src/app/api/ocr-cache/route.ts`, `src/app/api/autofill-cache/route.ts`, `src/app/api/ground-truth/route.ts`.
- `public/data/testsets` 사용처: TestWorkspace가 manifest/party_master를 직접 fetch하고 API routes가 dataset folder를 읽고 쓴다. tmp runners와 markdown fixture scripts도 fixture path를 참조한다.
- 삭제/유지/백업 판단: `profiles.ts`와 `components/test/**`는 Test archive 대상. `common/config/testsets.ts`, API routes, `public/data/testsets/**`는 즉시 삭제 금지.

### 7. API Route Impact
| route | uses testsets? | used by Test only? | recommended action |
|---|---|---|---|
| `src/app/api/test-images/route.ts` | Yes, `TESTSETS`, `getTestset` | 현재는 TestWorkspace 중심 | A/B에서 keep; C에서만 별도 archive 검토 |
| `src/app/api/ocr-cache/route.ts` | Yes, `DATASET_FOLDERS` | Test cache 중심 | keep until cache ownership replacement |
| `src/app/api/autofill-cache/route.ts` | Yes, `DATASET_FOLDERS` | Test autofill 중심 | keep until autofill storage decision |
| `src/app/api/ground-truth/route.ts` | Yes, `DATASET_FOLDERS` | Test GT 중심, GET has migration write side effect | keep; do not remove with UI-only phase |
| `src/app/api/ocr-extract/route.ts` | No direct testsets import | shared RunOCR proxy | keep |
| `src/app/api/biz-validate/route.ts` | No | TestWorkspace calls it, may be reusable | keep |

### 8. Backup Plan
- 권장 backup 위치: `backup/test_tab_YYYYMMDD_before_remove/`
- 포함 파일:
  - `src/app/test/**`
  - `src/components/test/**`
  - `src/components/test/core/**`
  - `src/components/test/utils/**`
  - `tmp/test_tab_1a_removal_precheck.md`
  - optional manifest snapshot list for `public/data/testsets/**/manifest.json`
- 제외 파일:
  - `public/data/testsets/**` full binary/image data by default. Keep in place.
  - `src/common/config/testsets.ts` unless doing full archive C. It is shared by API routes.
  - `src/app/api/ground-truth`, `ocr-cache`, `autofill-cache`, `test-images` in A/B initial phases.
- 복구 방식: restore route/component tree from backup, re-add sidebar item if UI hide was applied, run typecheck/build and `/test` smoke.

### 9. Removal Strategy Options
| option | 수정 파일 | 위험도 | 장점 | 단점 | 추천 여부 |
|---|---|---|---|---|---|
| A. UI hide only | `src/components/layout/Sidebar.tsx` only if Test menu exists; currently no visible Test item | LOW | safest, source/route/data intact, quick rollback | `/test` direct URL remains | 추천 |
| B. UI + route remove + archive | backup then remove `src/app/test`, optionally remove `src/components/test/**` from source | MEDIUM | app route surface is cleaner | archive/restore discipline needed; route smoke required | 2차 추천 |
| C. full archive | also remove test API routes/testsets config/data coupling | HIGH | cleanest removal | breaks validation runners, cache/GT tooling, future restore is expensive | 비추천 |

### 10. Recommended Actual Phase
1. `FRONTEND-TEST-TAB-1B-BACKUP-AND-UI-HIDE`
   - 도구: Codex
   - 수정 후보: `backup/test_tab_YYYYMMDD_before_remove/**`; `Sidebar.tsx` only if a Test nav item exists at that time.
   - 금지 파일: `src/components/test/**`, `public/data/testsets/**`, API storage routes.
   - 검증 기준: route list unchanged or menu hidden, typecheck/build, static checker.
   - rollback 방법: restore sidebar item from git/backup.

2. `FRONTEND-TEST-TAB-1C-ROUTE-REMOVE-ARCHIVE`
   - 도구: Codex
   - 수정 후보: `src/app/test/page.tsx` removal after backup, maybe keep `src/components/test/**` until no imports.
   - 금지 파일: `common/config/testsets.ts`, API storage routes, public data.
   - 검증 기준: `/test` absent/404 expectation, RunOCR/Template/History/Restore/Login route smoke, typecheck/build.
   - rollback 방법: restore `src/app/test/**` from backup.

3. `FRONTEND-TEST-TAB-1D-TEST-COMPONENTS-ABSENT-CHECK`
   - 도구: Codex
   - 수정 후보: static checker/report only or removal of `src/components/test/**` after archive.
   - 금지 파일: common utilities and dataset data.
   - 검증 기준: no imports from `components/test`, static checker PASS.
   - rollback 방법: restore `src/components/test/**` from backup.

### 11. Do Not Touch Yet
- `src/common/config/testsets.ts`: used by four Next API routes and TestWorkspace/profile types.
- `public/data/testsets/**`: sample assets, manifests, GT/cache/autofill fixtures and runner contracts.
- `src/app/api/ground-truth/route.ts`: GET can migrate data between GT and OCR cache; storage owner must be settled first.
- `src/app/api/ocr-cache/route.ts`, `src/app/api/autofill-cache/route.ts`: dataset storage APIs; remove only after replacement.
- `src/app/api/test-images/route.ts`: harmless if left; remove only with archive phase.
- `src/common/utils/invoiceTableDisplay.ts`: shared by RunOCR and Test; not Test-owned.
- `src/components/runocr/**`, `src/components/template/**`, `src/components/history/**`, `src/components/login/**`: no removal needed for Test tab A/B.

### 12. Verification Strategy
- typecheck: `npm run typecheck`.
- build: `npm run build`.
- route smoke: `/login`, `/runocr`, `/template`, `/history`, `/autorestore`; if B/C, confirm `/test` expected behavior.
- RunOCR route 확인: `/api/ocr-extract` proxy remains.
- Template route 확인: template page and `/templates` backend unaffected.
- History/Restore route 확인: `common/storage` imports unaffected.
- existing runner 영향: scan `tmp/check_*` references to `TestWorkspace`, `testsets`, `profiles`; update only in actual removal phase if absent checks require it.
- markdown contract: report/checker headings stay stable.
- src/lib absent: keep absent.
- `@/lib` import 0건: keep zero in `src`.

### 13. Zero-touch Verification
- production modified: no production/source/data modification by this task.
- files moved: no.
- static check: PASS via `node tmp/check_test_tab_removal_precheck_1a.mjs`.
- typecheck/build: PASS in this run. `npm run build` emitted `ESLint: nextVitals is not iterable` to stderr, but build exit code was 0 and Next build completed.
- FAIL count: 0.
- pre-existing issue: repository still has pre-existing dirty files, but no blocking typecheck/build issue reproduced in this run.
