## FRONTEND-TEST-TAB-1B Backup and UI Hide

### 1. Summary
- 운영 코드 수정 여부: 없음. 운영 `src`, `public/data/testsets`, API routes, backend는 수정하지 않았다.
- backup 생성 여부: 생성 완료.
- backup 위치: `backup/test_tab_20260526_before_remove/`.
- Sidebar Test 노출 여부: `src/components/layout/Sidebar.tsx`의 `DEFAULT_ITEMS`에는 `Test` / `/test` 항목이 없다.
- /test route 존재 여부: `src/app/test/page.tsx`가 운영 src에 그대로 존재한다.
- 다음 단계 추천: `FRONTEND-TEST-TAB-1C-ROUTE-REMOVE-ARCHIVE`에서 route 제거를 진행한다.

### 2. Backup Contents
| source | backup path | copied |
|---|---|---|
| `src/app/test/**` | `backup/test_tab_20260526_before_remove/src/app/test/**` | yes |
| `src/components/test/TestWorkspace.tsx` | `backup/test_tab_20260526_before_remove/src/components/test/TestWorkspace.tsx` | yes |
| `src/components/test/core/**` | `backup/test_tab_20260526_before_remove/src/components/test/core/**` | yes |
| `src/components/test/utils/profiles.ts` | `backup/test_tab_20260526_before_remove/src/components/test/utils/profiles.ts` | yes |
| `tmp/test_tab_1a_removal_precheck.md` | `backup/test_tab_20260526_before_remove/tmp/test_tab_1a_removal_precheck.md` | yes |
| `public/data/testsets/*/manifest.json` | `backup/test_tab_20260526_before_remove/manifest_snapshots/public/data/testsets/*/manifest.json` | yes |

### 3. UI Hide Verification
- layout/sidebar/header에서 Test 메뉴 노출 여부: Sidebar `DEFAULT_ITEMS` 기준 노출 없음. `NavIcon`에는 `test` case가 남아 있으나 메뉴 항목이 아니므로 UI 노출은 없다.
- direct `/test` route 존재 여부: 존재. `src/app/test/page.tsx`가 `AppShell`과 `TestWorkspace`를 렌더링한다.
- route 제거는 1C에서 진행한다. 이번 단계는 백업과 UI 노출 최종 확인만 수행한다.

### 4. Files Preserved
- `src/app/test/**`: 운영 src에 유지.
- `src/components/test/**`: 운영 src에 유지.
- `src/common/config/testsets.ts`: 유지.
- `public/data/testsets/**`: 수정/삭제 없음. manifest snapshot만 backup에 복사.
- API routes: `test-images`, `ocr-cache`, `autofill-cache`, `ground-truth` 모두 유지.

### 5. Removal Readiness
- 1C에서 제거 가능한 파일:
  - `src/app/test/page.tsx`
  - 이후 별도 승인 시 `src/components/test/**`
- 1C에서 유지해야 할 파일:
  - `src/common/config/testsets.ts`
  - `src/app/api/test-images/route.ts`
  - `src/app/api/ocr-cache/route.ts`
  - `src/app/api/autofill-cache/route.ts`
  - `src/app/api/ground-truth/route.ts`
- 1C에서 절대 건드리면 안 되는 파일:
  - `public/data/testsets/**`
  - RunOCR/Template/History/Restore/Login source
  - backend/ocr-server production code

### 6. Verification
- typecheck: PASS (`typecheck_exit=0`).
- build: PASS (`build_exit=0`).
- static check: PASS. 1A checker and 1B checker both PASS.
- FAIL count: 0.
- known warnings: `next build` emitted `ESLint: nextVitals is not iterable` to stderr, but build exit code was 0 and Next build completed.
