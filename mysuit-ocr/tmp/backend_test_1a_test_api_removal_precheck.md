## BACKEND-TEST-1A Test API Removal Precheck

### 1. Summary
- 운영 코드 수정 여부: no production code modified. This precheck only adds tmp report/checker and log files.
- 분석 대상: Next API test routes, `src/common/config/testsets.ts`, `public/data/testsets/**`, `ocr-server` review/feedback/preprocessing references, scripts/tmp runner references.
- 삭제 가능성이 높은 route: `/api/test-images` is the best first candidate because no current operating `src` caller remains after Test tab removal.
- 유지해야 할 route: `/api/ground-truth`, `/api/ocr-cache`, `/api/autofill-cache` should stay until storage ownership is separated; they write dataset JSON files and are still validation assets.
- 가장 위험한 파일: `public/data/testsets/**/manifest.json` and `ocr-server/preprocessing_policy.py` interaction. `ocr-server/main.py` also directly reads `invoice_statement/manifest.json` for table expected columns fallback.
- 추천 전략: Strategy A now, then Strategy B as a small follow-up: keep API routes for now, run a dedicated precheck/remove phase for `/api/test-images` only.
- 다음 phase: `BACKEND-TEST-1B-TEST-IMAGES-API-REMOVE-PRECHECK`.

### 2. Current Remaining Test-Related Backend/API Tree
```text
src/app/api/test-images/route.ts
src/app/api/ocr-cache/route.ts
src/app/api/autofill-cache/route.ts
src/app/api/ground-truth/route.ts
src/common/config/testsets.ts
public/data/testsets/
  baseline/manifest.json, ground_truth.json, ocr_cache.json, autofill_cache.json, samples...
  baseline_fast/manifest.json, ground_truth.json, ocr_cache.json, autofill_cache.json, samples...
  google/manifest.json, ground_truth.json, ocr_cache.json, autofill_cache.json, samples...
  google_fast/manifest.json, ground_truth.json, ocr_cache.json, autofill_cache.json, samples...
  invoice_statement/manifest.json, ground_truth.json, ocr_cache.json, autofill_cache.json, samples/reports...
  new_samples/manifest.json, ground_truth.json, ocr_cache.json, autofill_cache.json, samples...
  receipt_generalization/manifest.json, ground_truth.json, ocr_cache.json, autofill_cache.json, samples...
  tax_invoice/manifest.json
ocr-server/main.py
ocr-server/preprocessing_policy.py
ocr-server/data/review_log.jsonl
```

### 3. API Route Ownership
| route | file | role | data dependency | caller/reference | delete readiness | recommendation |
|---|---|---|---|---|---|---|
| `/api/test-images` | `src/app/api/test-images/route.ts` | Lists sample files and returns `TESTSETS` metadata for a dataset. | `src/common/config/testsets.ts`, `public/data/testsets/<folder>` image/PDF files. | No current operating `src` caller found. Historical tmp reports/checkers reference it. | MEDIUM-HIGH readiness; likely removable after a route-specific precheck. | Candidate for first removal phase. Preserve testsets data. |
| `/api/ocr-cache` | `src/app/api/ocr-cache/route.ts` | GET/POST `ocr_cache.json` for a dataset. | `DATASET_FOLDERS`, `public/data/testsets/<folder>/ocr_cache.json`; creates dataset folder if missing. | No current operating `src` caller found; tmp/fixture history references it. | LOW readiness; write side effect and fixture asset coupling. | Keep until cache ownership/storage replacement is designed. |
| `/api/autofill-cache` | `src/app/api/autofill-cache/route.ts` | GET/POST `autofill_cache.json` for a dataset. | `DATASET_FOLDERS`, `public/data/testsets/<folder>/autofill_cache.json`; creates dataset folder if missing. | No current operating `src` caller found; tmp/fixture history references it. | LOW readiness; linked to autofill validation assets. | Keep until autofill cache ownership is split from public testsets. |
| `/api/ground-truth` | `src/app/api/ground-truth/route.ts` | GET/POST `ground_truth.json`; GET migrates legacy `ocr_text` entries into `ocr_cache.json`. | `DATASET_FOLDERS`, `ground_truth.json`, `ocr_cache.json`; writes on migration. | No current operating `src` caller found. `src/common/storage/groundTruthStore.ts` is separate localStorage store, not this API. | LOW readiness; highest-risk of the four because GET can write. | Keep. Requires dedicated storage/data migration precheck. |

### 4. testsets.ts Ownership
- 사용처: currently imported at runtime only by `src/app/api/test-images/route.ts`, `src/app/api/ocr-cache/route.ts`, `src/app/api/autofill-cache/route.ts`, and `src/app/api/ground-truth/route.ts`.
- API route 의존: all four remaining Test-related API routes depend on either `TESTSETS/getTestset` or `DATASET_FOLDERS`.
- 삭제 가능 여부: not safe while any of the four API routes remain.
- 유지/이동/아카이브 판단: keep in `src/common/config` for now. If `/api/test-images` is removed first, `TESTSETS/getTestset` may become unused but `DATASET_FOLDERS` will still be used by cache/GT routes.

### 5. public/data/testsets Ownership
- dataset 목록: `baseline`, `baseline_fast`, `google`, `google_fast`, `invoice_statement`, `new_samples`, `receipt_generalization`, `tax_invoice`, plus `reports`.
- manifest 개수: 8 active dataset `manifest.json` files.
- API 의존: all four candidate API routes read/write under this root.
- runner/fixture 의존: many tmp/scripts validation runners and historical reports reference manifests, GT, OCR cache, and invoice sample outputs.
- 삭제 위험도: HIGH. `ocr-server/preprocessing_policy.py` scans this root for manifests. `ocr-server/main.py` also reads `public/data/testsets/invoice_statement/manifest.json` for expected table columns fallback.
- 추천 액션: do not delete or move in this phase. Treat as validation/fixture data until an archive precheck proves backend no longer reads it.

### 6. Ground Truth / Cache / Autofill Storage
- `/api/ocr-cache`: reads/writes `public/data/testsets/<folder>/ocr_cache.json`; creates folder on access.
- `/api/autofill-cache`: reads/writes `public/data/testsets/<folder>/autofill_cache.json`; creates folder on access.
- `/api/ground-truth`: reads/writes `public/data/testsets/<folder>/ground_truth.json`; GET may also write migrated data to `ocr_cache.json` and rewrite `ground_truth.json`.
- Test 전용 여부: originally Test tab/storage validation oriented, but now more accurately fixture/validation infrastructure. Current operating UI does not call these API routes.
- 제거 가능 여부: not ready. Remove only after a storage ownership precheck defines what happens to these JSON assets and migration side effects.

### 7. ocr-server Test/Review/Feedback Related Logic
- `ocr-server/main.py` routes:
  - `/ocr/feedback`: appends human correction entries to `ocr-server/data/review_log.jsonl`; comments describe operational review flow, not GT mutation.
  - `/ocr/review-log`: reads `review_log.jsonl` for operational/admin filtering.
  - `/ocr/extract`: appends auto extract review log entries and contains comments mentioning former Test tab debug metadata.
  - `/ocr/revalidate`: OCR revalidation endpoint, not a Test tab API.
- `ocr-server/preprocessing_policy.py`: reads `mysuit-ocr/public/data/testsets/**/manifest.json` for `qualityTags`, `expectedRowCount`, and `tableExpectedColumns`.
- 운영 기능 여부: review/feedback is operational/QA logging and is separate from Next Test tab routes. Manifest lookup affects OCR preprocessing/revalidation behavior.
- 삭제 가능 여부: do not remove in Test API cleanup. It is not equivalent to the removed frontend Test tab.
- 추천 판단: keep. Any backend review/manifest cleanup needs a backend-specific ownership phase.

### 8. Removal Strategy Options
| strategy | 수정 대상 | 장점 | 위험 | 추천 여부 | rollback 방법 |
|---|---|---|---|---|---|
| A. API route 유지 | none | Safest; preserves fixture/cache/GT automation assets. | Leaves dead-ish endpoints visible. | Recommended now. | No rollback needed. |
| B. test-images route만 제거 | `src/app/api/test-images/**`; possible later pruning of `TESTSETS/getTestset` if unused | Removes sample list endpoint most tightly coupled to deleted Test tab. | Need build route check and caller sweep; public data still remains. | Recommended next after 1B precheck. | Restore route from git/backup; rerun typecheck/build. |
| C. cache/GT/autofill/test-images 전체 제거 | four API route dirs, `src/common/config/testsets.ts`, public JSON storage references | Cleans all Test APIs. | High: storage writes, migration, fixture runners, backend manifest usage. | Not recommended. | Restore routes/config/data; rerun route smoke and fixture runners. |
| D. public/data/testsets archive | `public/data/testsets/**` move/archive | Removes large public fixture surface. | Very high: backend manifest lookup and regression assets break. | Not recommended without backend manifest replacement. | Restore full public data tree from backup/archive. |

### 9. Recommended Actual Phases
1. `BACKEND-TEST-1B-TEST-IMAGES-API-REMOVE-PRECHECK`
   - 도구: Codex
   - 목표: prove `/api/test-images` has no operating caller and define exact deletion/rollback.
   - 수정 후보: none in precheck.
   - 금지 파일: cache/GT/autofill routes, `testsets.ts`, `public/data/testsets/**`.
   - 검증 기준: route caller sweep, typecheck/build, build route list excludes `/api/test-images` only after later remove.
   - 위험도: LOW-MEDIUM.
2. `BACKEND-TEST-1C-TEST-IMAGES-API-REMOVE`
   - 도구: Codex
   - 목표: remove `src/app/api/test-images/**` only.
   - 수정 후보: `src/app/api/test-images/route.ts`; maybe no config change yet.
   - 금지 파일: cache/GT/autofill routes, public testsets, ocr-server.
   - 검증 기준: typecheck/build, route absence, RunOCR/Template/History/Login smoke, residual caller 0.
   - 위험도: MEDIUM.
3. `BACKEND-TEST-2A-CACHE-GT-AUTOFILL-OWNERSHIP-PRECHECK`
   - 도구: Codex
   - 목표: decide whether JSON cache/GT APIs become archive-only, admin-only, or removed.
   - 수정 후보: none in precheck.
   - 금지 파일: `public/data/testsets/**` deletion, ocr-server manifest logic.
   - 검증 기준: storage side-effect map, runner dependency list, route smoke if retained.
   - 위험도: HIGH.
4. `BACKEND-TEST-3A-PUBLIC-TESTSETS-ARCHIVE-PRECHECK`
   - 도구: Codex or Claude Code
   - 목표: plan public fixture archive only after backend no longer reads manifests from public data.
   - 수정 후보: none in precheck.
   - 금지 파일: direct public data deletion.
   - 검증 기준: backend import smoke, RunOCR fixture smoke, invoice rowCount exact fixtures, manifest replacement contract.
   - 위험도: HIGH.

### 10. Do Not Touch Yet
- `public/data/testsets/**`: backend preprocessing and many fixtures still depend on manifests/data.
- `src/common/config/testsets.ts`: still required by remaining API routes.
- `src/app/api/ground-truth/route.ts`: GET can write/migrate cache and GT files.
- `src/app/api/ocr-cache/route.ts`: owns `ocr_cache.json` read/write.
- `src/app/api/autofill-cache/route.ts`: owns `autofill_cache.json` read/write.
- `ocr-server/main.py`: review/feedback/extract behavior is operational backend logic.
- `ocr-server/preprocessing_policy.py`: manifest lookup is part of backend preprocessing policy.
- `backup/test_tab_20260526_before_remove/**`: rollback source for removed Test tab.

### 11. Verification Strategy
- typecheck and build.
- route smoke for retained `/api/ocr-cache`, `/api/autofill-cache`, `/api/ground-truth` before any removal.
- `/api/test-images` route absence smoke only in actual removal phase.
- RunOCR smoke and `/api/ocr-extract` proxy smoke.
- Template route/workspace smoke.
- History route/workspace smoke.
- representative table runner and invoice rowCount exact fixture checks before touching public testsets.
- OCR cache/GT route smoke if route retained.
- `src/lib` absent.
- `@/lib` import 0.
- markdown contract/report checker.

### 12. Zero-touch Verification
- production modified: no production code modified by this precheck.
- files moved: no.
- static check: PASS, `[BACKEND_TEST_API_REMOVAL_PRECHECK_1A] PASS`.
- typecheck/build: PASS / PASS.
- FAIL count: 0.
- known warning: build stderr emitted existing `ESLint: nextVitals is not iterable`; build exit code was 0 and compiled successfully.
