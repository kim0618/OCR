## BACKEND-TEST-1B Test Images API Remove Precheck

### 1. Summary
- 운영 코드 수정 여부: no production code modified.
- 삭제/이동 여부: no files deleted or moved.
- route: `/api/test-images`, implemented by `src/app/api/test-images/route.ts`.
- 운영 caller: 0 current operating `src` callers outside the route file itself.
- 삭제 readiness: HIGH for route-only removal. Remove only `src/app/api/test-images/**`; keep testsets config/data and cache/GT/autofill routes.
- 추천 다음 phase: `BACKEND-TEST-1C-TEST-IMAGES-API-REMOVE`.

### 2. Current Route Anatomy
- file: `src/app/api/test-images/route.ts`
- HTTP methods: `GET` only.
- imports:
  - `NextResponse` from `next/server`
  - `fs`
  - `path`
  - `TESTSETS`, `getTestset` from `@/common/config/testsets`
- data dependencies:
  - `src/common/config/testsets.ts` for dataset metadata and fallback selection.
  - `public/data/testsets/<testset.folder>` for image/PDF directory listing.
  - supported extensions: `.jpg`, `.jpeg`, `.png`, `.webp`, `.bmp`, `.tif`, `.tiff`, `.pdf`.
- response shape:
  - `{ testsets, current, imageBaseUrl, images }`
  - `testsets`: full `TESTSETS` metadata array.
  - `current`: selected dataset id.
  - `imageBaseUrl`: selected dataset public path.
  - `images`: sorted file names in the selected dataset folder.
- side effects:
  - no write side effect.
  - no directory creation.
  - missing dataset folders are caught and returned as an empty `images` array.

### 3. Caller Sweep
| area | references | meaning |
|---|---|---|
| src | Route file itself only; no operating UI caller found for `/api/test-images`. | Safe for route-only removal from current app flow. |
| tmp | Historical reports/checkers mention `test-images` as protected route or prior Test tab dependency. | Test/documentation residue; may need phase-aware checker updates after 1C. |
| scripts | No active operating caller found in the sweep. | No script blocker identified. |
| ocr-server | No `/api/test-images` caller found. `ocr-server` references `public/data/testsets` directly for manifests/samples. | Removing route does not remove backend manifest/data dependency. |
| backup | Multiple archived `TestWorkspace` files call `/api/test-images`. | Expected rollback/archive evidence only. |

### 4. Removal Impact
| area | impact | recommendation |
|---|---|---|
| typecheck | Route removal should not affect TS imports because no operating source imports the route module. | Run typecheck after removal. |
| build route | `/api/test-images` should disappear from Next build route list. | Verify route absence in 1C. |
| RunOCR | No caller found; RunOCR uses backend `/ocr/extract` or `/api/ocr-extract`. | Preserve RunOCR files. |
| Template | No caller found; Template uses `/api/ocr-extract` and `/templates`. | Preserve Template files. |
| History/Login/Layout | No caller found. | Preserve. |
| `src/common/config/testsets.ts` | `TESTSETS/getTestset` may become unused after route removal, but `DATASET_FOLDERS` remains used by cache/GT/autofill routes. | Keep unchanged in 1C. |
| `public/data/testsets/**` | No direct removal impact; backend and fixture runners still rely on manifests/data. | Keep unchanged. |
| cache/GT/autofill APIs | Independent routes still use `DATASET_FOLDERS` and public data JSON. | Keep unchanged. |

### 5. Keep List
- `src/common/config/testsets.ts`
- `public/data/testsets/**`
- `src/app/api/ocr-cache/**`
- `src/app/api/autofill-cache/**`
- `src/app/api/ground-truth/**`
- `src/app/api/ocr-extract/**`
- `src/components/runocr/**`
- `src/components/template/**`
- `src/components/history/**`
- `src/components/login/**`
- `ocr-server/**`
- `backup/test_tab_20260526_before_remove/**`

### 6. Remove Candidate
- `src/app/api/test-images/route.ts`
- `src/app/api/test-images/` directory

No other source/config/data file should be removed in 1C.

### 7. Verification Strategy for 1C
- Confirm backup/rollback source before deletion: git restore path or prior backup reference.
- Remove only `src/app/api/test-images/**`.
- Verify `src/app/api/test-images` absent.
- Verify `src/app/api/ocr-cache/route.ts`, `autofill-cache/route.ts`, `ground-truth/route.ts`, `src/common/config/testsets.ts`, and `public/data/testsets` still exist.
- Verify operating `src` caller `/api/test-images` remains 0.
- Run typecheck and build.
- Confirm build route list no longer contains `/api/test-images`.
- Confirm RunOCR, Template, History, Login, Layout paths remain present.
- Keep `src/lib` absent and `@/lib` import 0.
- Run a 1C static checker with `[BACKEND_TEST_IMAGES_API_REMOVE_1C] PASS`.

### 8. Rollback Plan
- backup source: git index/worktree can restore `src/app/api/test-images/route.ts`; if needed, reconstruct from this precheck's route anatomy and current git state.
- 복구 방법: restore `src/app/api/test-images/route.ts` under `src/app/api/test-images/`.
- 검증 방법: rerun typecheck, build, caller sweep, and route presence checker.

### 9. Zero-touch Verification
- production modified: no.
- files moved: no.
- files deleted: no.
- typecheck: PASS.
- build: PASS.
- static check: PASS, `[BACKEND_TEST_IMAGES_API_REMOVE_PRECHECK_1B] PASS`.
- FAIL count: 0.
- known warning: build stderr emitted existing `ESLint: nextVitals is not iterable`; build exit code was 0 and compiled successfully.
