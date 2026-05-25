## LIB-CLEAN-4 Remaining src/lib Ownership Precheck

### 1. Summary
- **현재 src/lib 잔여 파일 (5)**: `autofillEngine.ts`, `groundTruthStore.ts`, `profiles.ts`, `restoreProfileStore.ts`, `testsets.ts`.
- **이번 precheck 결론 요약**: 모든 5개 파일에 명확한 target/owner가 존재. "보류" 0건. dep 그래프 위배 없이 7-step 순서로 `src/lib` 완전 제거 가능 (`CAN_CLOSE_LIB_AFTER_PLANNED_MOVES`).
- **바로 이동 가능한 파일 (Codex로 충분)**: `groundTruthStore.ts`, `restoreProfileStore.ts`.
- **추가 precheck 필요한 파일**: `autofillEngine.ts` (485 lines, 4 importer, common/utils 잔여 type-only 의존 1건 — LIB-CLEAN-4E 전용 precheck phase).
- **TestWorkspace import path-only 보정 동의가 필요한 파일**: `testsets.ts`, `profiles.ts` (각각 TestWorkspace 1줄 import path 변경 필요).
- **Claude Code로 진행해야 할 파일**: `testsets.ts` (새 도메인 폴더 `src/common/config/` 도입 + 6 importer + TestWorkspace touch), `profiles.ts` (TestWorkspace 2-line touch + testsets sibling resolution), `autofillEngine.ts` (size + multi-importer + 1A 잔여 dep + cycle/storage 분석 필요).
- **Codex로 가능한 move-only micro-step**: `groundTruthStore.ts → common/storage/` (2 importer leaf), `restoreProfileStore.ts → common/storage/` (3 importer, no new subdir).
- **utif.d.ts**: LIB cleanup과 무관. 유지 권고.

### 2. File-by-file Analysis

#### 2.1 autofillEngine.ts
- **책임**: Autofill 비즈니스 로직. history + restore profile에서 후보 수집 → suggestion 생성/정렬 → output field에 적용. 순수 로직 (저장소를 조합).
- **imports**:
  - `@/common/utils/bizNumber` (runtime — `normalizeBizNumber`)
  - `@/common/storage/historyStore` (runtime + type — `readHistoryRuns`, `HistoryOutputField`)
  - `./restoreProfileStore` (runtime sibling — `readRestoreProfiles`, `isMeaninglessValue`)
- **exports (key)**: `AutofillSource`/`OutputValueSource`/`AutofillAction` (types), `AutofillSuggestion`, `AutofillCandidateRecord`, `AutofillRunStatus`, `AutofillRunSummary`, `AutofillFieldMetadata`, `AutofillOutputFieldLike`, `AUTOFILLABLE_FIELDS`, `normalizeAutofillFieldKey`, `isAutofillableField`, `isEmptyOcrValue`, `canAutoApplySuggestion`, `sortAutofillSuggestions`, `collectInternalAutofillCandidates`, `buildAutofillSuggestionsFromCandidates`, `applyAutofillToOutputFields`, `suggestionsForHistoryField`.
- **direct users (4)**:
  - `src/components/runocr/RunOcrWorkspace.tsx:51` — runtime
  - `src/components/runocr/ui/OcrResultPanel.tsx:27` — type-only
  - `src/components/history/ui/DetailHistoryView.tsx:28` — runtime (`normalizeAutofillFieldKey`)
  - `src/common/utils/ocrResultFormatters.ts:21` — **type-only (1A 잔여 의존)**
- **type-only users**: OcrResultPanel, ocrResultFormatters.
- **runtime users**: RunOcrWorkspace, DetailHistoryView.
- **historyStore 의존 여부**: O (runtime: `readHistoryRuns` + type).
- **RunOCR 의존**: 직접 import는 없음. 단 RunOcrWorkspace가 자신을 import.
- **History 의존**: DetailHistoryView가 self를 import.
- **Restore/autorestore 의존**: AutoRestoreWorkspace는 autofillEngine을 직접 import하지 않음. autofillEngine이 restoreProfileStore를 sibling으로 import.
- **TestWorkspace 의존**: 없음.
- **common/utils 적합성**: 적합. 순수 로직(no React/DOM/localStorage/fetch). 다중 feature 공유.
- **components/runocr/utils 적합성**: 부적합 — history + common/utils가 이 파일을 import하므로 runocr feature 폴더 안으로 가두면 cross-feature 침범.
- **components/history/utils 적합성**: 동일 사유로 부적합.
- **components/autorestore/utils 적합성**: 동일 사유로 부적합.
- **이동 전 추가 precheck**: 필요 (4 importer + sibling restoreProfile dep + 1A 잔여 type-only dep). LIB-CLEAN-4E PRECHECK 별도 phase로 분리.
- **recommended owner**: `src/common/utils/`
- **recommended target path**: `src/common/utils/autofillEngine.ts`
- **move readiness**: **NEEDS_PRECHECK**
- **recommended tool**: **Claude Code**
- **reason**: 가장 큰 잔여 파일(485 lines), 4 importer + 사이블링 의존 + 1A 잔여 dep의 동시 해소. precheck/move 2단계로 분리해 위험 통제.

#### 2.2 groundTruthStore.ts
- **책임**: `(template, file)` 페어 키 기반 localStorage GT 저장소. `HistoryOutputField` 배열로부터 수정값을 정답으로 보존. `compareToGt`로 비교.
- **imports**: `type HistoryOutputField from @/common/storage/historyStore`.
- **exports (key)**: `GroundTruthMap` (type), `MatchStatus` (type), `compositeKey`, `fieldKey`, `getGroundTruth`, `saveGroundTruth`, `clearGroundTruth`, `compareToGt`.
- **direct users (2)**:
  - `src/components/history/ui/DetailHistoryView.tsx:25` — runtime
  - `src/components/runocr/ui/OcrResultPanel.tsx:28` — runtime
- **TestWorkspace 직접 import**: 없음.
- **test/core 직접 import**: 없음 (이전 BZ-1에서 확인됨; 본 precheck에서도 재확인).
- **History detail 사용 여부**: O.
- **RunOCR 사용 여부**: O (OcrResultPanel).
- **ground truth 데이터 파일 직접 import**: 없음. localStorage `mysuit_ocr_groundtruth` key만 사용. backend GT 데이터 (`public/data/.../groundtruth.json` 등)와 무관.
- **fixture 직접 import**: 없음.
- **backend import**: 없음.
- **localStorage 책임**: O — 본래 책임. browser API만 사용.
- **common/storage 적합성**: 적합. 이미 imageStore/historyStore/login 입주한 폴더의 자연스러운 4번째 파일.
- **TestWorkspace 승인 필요**: 불필요 (TestWorkspace는 이 파일을 import하지 않음).
- **recommended owner**: `src/common/storage/`
- **recommended target path**: `src/common/storage/groundTruthStore.ts`
- **move readiness**: **READY**
- **recommended tool**: **Codex** (또는 Claude Code 어느 쪽도 가능)
- **reason**: 2 importer leaf, no new subdir, TestWorkspace 영향 없음. 단순 import path-only 2건 보정.

#### 2.3 profiles.ts
- **책임**: Test 탭 profile 정책 단일 진입점 — receipt/finance/document/none profile 결정, 컬럼 정의, table profile 정책, KPI family 해소. 순수 타입 + 상수 + 헬퍼.
- **imports**: `type DocumentType from ./testsets` (sibling).
- **exports (key)**: `Profile`, `Overlay`, `ProfileResolution`, `ReceiptFieldKey`/`FinanceFieldKey`/`DocumentFieldKey`/`CardOverlayFieldKey`/`MedicalOverlayFieldKey`/`AnyFieldKey`, `FINANCE_TIER1_FIELDS`/`FINANCE_TIER2_FIELDS`/`DOCUMENT_PARTY_FIELDS`, `RECEIPT_COLUMNS`/`FINANCE_COLUMNS`/`DOCUMENT_COLUMNS`/`CARD_OVERLAY_COLUMNS`/`MEDICAL_OVERLAY_COLUMNS`, `resolveProfile`, `getBaseColumns`, `getOverlayColumns`, `getVisibleColumns`, `isNotApplicableField`, `isFinanceTier1`, `isProfileMismatchSuspected`, `KpiFamily`, `resolveKpiFamily`, `TableColumnKey`, `GridModeRecommendation`, `TableColumnMeta`, `TABLE_COLUMN_META`, `TableProfilePolicyResult`, `getExpectedTableColumns`, `TableRowsValidation`.
- **direct users (1)**:
  - `src/components/test/TestWorkspace.tsx:36` — runtime (8개 심볼)
  - `src/components/test/TestWorkspace.tsx:37` — type (3개 심볼)
- **Restore/autorestore 사용 여부**: 없음.
- **TestWorkspace 사용 여부**: O (유일 importer; 2 줄).
- **profile preset/data 성격**: 정책 + 타입 + 컬럼 카탈로그. 데이터 stash가 아니라 test 탭 평가 정책 (test-feature-local).
- **common/data 적합성**: 부적합. 정책이 test 탭에 한정되어 다른 feature가 소비하지 않음.
- **common/utils 적합성**: 부적합. 같은 사유 + utils은 cross-feature 유틸 용도.
- **components/autorestore/utils 적합성**: 부적합. autorestore는 이 파일을 사용하지 않음.
- **components/restore/utils 적합성**: 부적합. restore 폴더는 아직 별도 plan(RS-1 후보)에 잡혀 있을 뿐, profiles와 무관.
- **components/test/utils 적합성**: 적합. 유일 소비자가 TestWorkspace인 정책 파일.
- **doc-comment 옛 경로 문자열**: 있음 (`docs/TEST_PROFILE_SCHEMA_20260427.md`, `core/types.ts`) — 문자열 잔존이지 import가 아니므로 이동 자체에 영향 없음. cosmetic.
- **이동 시 route/name 변경 위험**: 없음.
- **recommended owner**: `src/components/test/utils/`
- **recommended target path**: `src/components/test/utils/profiles.ts`
- **move readiness**: **READY (선행 의존: testsets 이동)**
- **recommended tool**: **Claude Code**
- **reason**: TestWorkspace 2-line import path 보정 + sibling testsets 의존(`./testsets` → `@/common/config/testsets`) 동시 해소 필요. TestWorkspace touch가 발생하므로 Claude Code로 logic-equivalent 가드 강제.

#### 2.4 restoreProfileStore.ts
- **책임**: 사업자번호 + partyType 키 기반 restore profile localStorage CRUD. autofill용 키 매핑 상수 동봉.
- **imports**: 없음.
- **exports (key)**: `RESTORE_PROFILE_STORAGE_KEY`, `RestoreProfile`/`RestoreProfileFields` (types), `AUTOFILL_TO_PROFILE_KEY`, `PROFILE_FIELD_LABELS`, `isMeaninglessValue`, `readRestoreProfiles`, `writeRestoreProfiles`, `deleteRestoreProfile`, `findRestoreProfile`, `sortRestoreProfilesByUpdatedAt`.
- **direct users (3)**:
  - `src/components/autorestore/AutoRestoreWorkspace.tsx:12` — runtime
  - `src/components/history/ui/DetailHistoryView.tsx:37` — runtime
  - `src/lib/autofillEngine.ts:3` — runtime (sibling)
- **TestWorkspace impact**: 없음.
- **Restore/autorestore impact**: AutoRestoreWorkspace 1 importer (runtime). 폴더명 `components/autorestore`, route `/autorestore`, `AutoRestoreWorkspace` 명칭은 본 이동으로 변경되지 않음 (스펙 준수).
- **storage responsibility**: O — `RESTORE_PROFILE_STORAGE_KEY = "mysuit_ocr_restore_profiles"` localStorage 단독 책임.
- **common/storage 적합성**: 적합. autorestore feature 폴더로 가두면 history/autofillEngine이 autorestore feature를 import하게 됨 → cross-feature 침범. common/storage가 정확.
- **components/autorestore/utils 적합성**: 부적합 (위 사유).
- **이동 시 autorestore route/name 영향**: 없음. autorestore 폴더/route는 위치 그대로 유지.
- **recommended owner**: `src/common/storage/`
- **recommended target path**: `src/common/storage/restoreProfileStore.ts`
- **move readiness**: **READY**
- **recommended tool**: **Codex** (단순 3 importer 보정)
- **reason**: leaf, no React/components/* import, autofillEngine sibling 의존 해소(`./restoreProfileStore` → `@/common/storage/restoreProfileStore`). autofillEngine 이동 전에 이걸 먼저 옮겨야 autofillEngine static check가 깨끗하게 끝남.

#### 2.5 testsets.ts
- **책임**: 정적 dataset 레지스트리(`TESTSETS`, `DATASET_FOLDERS`, `getTestset`) + manifest item/invoice profile 타입군.
- **imports**: 없음.
- **exports (key)**: `TESTSETS`, `DATASET_FOLDERS`, `getTestset`, `TestsetMeta`, `DocumentType`, `QualityTag`, `Difficulty`, `InvoiceSubType`, `AmountProfile`, `PartyProfile`, `TableProfile`, `InvoiceTableExpectedDisplayColumn`, `InvoiceProfile`, `DatasetRole`, `DatasetStatus`, `ExpectedStatus`, `ManifestItem`, `DatasetManifest`.
- **direct users (6)**:
  - `src/app/api/autofill-cache/route.ts:4` — runtime (`DATASET_FOLDERS`)
  - `src/app/api/ground-truth/route.ts:4` — runtime (`DATASET_FOLDERS`)
  - `src/app/api/ocr-cache/route.ts:4` — runtime (`DATASET_FOLDERS`)
  - `src/app/api/test-images/route.ts:4` — runtime (`TESTSETS`, `getTestset`)
  - `src/components/test/TestWorkspace.tsx:35` — type-only (6 manifest/profile types)
  - `src/lib/profiles.ts:14` — type-only sibling (`DocumentType`)
- **TestWorkspace 직접 사용**: O (type-only 1 줄).
- **test/core 직접 사용**: 없음.
- **RunOCR/History/Restore 사용**: 없음.
- **public/data/testsets 관련 여부**: `path: "/data/testsets/<folder>"` 문자열만 보유 (정적 메타). 실제 데이터 디렉터리(`public/data/testsets/*`)는 별도 backend asset이며 본 이동 영향 없음.
- **fixture/manifest 관련**: manifest 타입 정의만 보유. manifest.json 파일은 backend/public/data asset로 본 이동 영향 없음.
- **common/data 적합성**: 적합한 후보지만 본 plan은 `src/common/config/` 도메인을 표준화함 (앞선 plan precheck와 일치). config는 *정적 레지스트리 + 타입 카탈로그*의 자연스러운 owner.
- **components/test/utils 적합성**: 부적합 — 4 SSR API route가 이 파일을 import하므로 test feature 폴더로 가두면 API routes가 feature 폴더에 의존하게 됨.
- **TestWorkspace 별도 승인 필요**: import path-only 보정 (1 줄)만 발생 — logic byte-equivalent (import strip 후) 가드로 안전성 확보. 본 plan precheck에서 이미 `TEST_WORKSPACE_DIRECT_IMPORT_BUT_SAFE_IMPORT_PATH_ONLY` 판정.
- **recommended owner**: `src/common/config/` (새 도메인 폴더)
- **recommended target path**: `src/common/config/testsets.ts`
- **move readiness**: **READY**
- **recommended tool**: **Claude Code**
- **reason**: 6 importer + 새 도메인 폴더(`src/common/config/`) 도입 + TestWorkspace touch + 4 SSR API route 보정. import path만 변경하지만 importers 폭이 넓어 logic-equivalent 가드와 새 폴더 ownership 검사를 Claude Code static check로 묶는 것이 안전.

#### 2.6 src/types/utif.d.ts
- **책임**: npm 패키지 `utif`에 대한 ambient module 선언 1줄 (`declare module "utif";`).
- **references**:
  - `src/components/runocr/RunOcrWorkspace.tsx:390` — `await import("utif")` (동적 import). `.tif/.tiff` 디코딩 fallback.
  - `src/components/runocr/RunOcrWorkspace.tsx:117/118`, `1275` — `.tif/.tiff` 확장자 체크 / `<input accept>`.
  - `src/common/ui/FileDropzone.tsx`, `src/app/api/test-images/route.ts` — `.tif/.tiff` 확장자 문자열만 사용.
- **src/lib cleanup relevance**: **무관**. `src/types/utif.d.ts`는 TypeScript ambient module shim일 뿐 src/lib 정리 plan 대상이 아님.
- **recommended action**: **유지** (별도 후속 type cleanup에서 `src/common/types/`로 이동 여부를 따로 평가). 현재 plan에서는 손대지 않음.
- **reason**: ambient declaration은 path alias 영향이 없고 (`declare module "utif"`는 tsconfig의 typeRoots/include로 인식), 이동해도 동작이 변하지 않으나 본 LIB-CLEAN-4 plan은 src/lib 제거에 집중하므로 scope-creep 방지를 위해 유지.

### 3. Dependency Graph
```
[runtime / type-only] → 표시.

src/lib/autofillEngine.ts
  ← src/components/runocr/RunOcrWorkspace.tsx           [runtime]
  ← src/components/runocr/ui/OcrResultPanel.tsx         [type-only]
  ← src/components/history/ui/DetailHistoryView.tsx     [runtime]
  ← src/common/utils/ocrResultFormatters.ts             [type-only — 1A 잔여]
  → @/common/utils/bizNumber                            [runtime]
  → @/common/storage/historyStore                       [runtime + type]
  → ./restoreProfileStore                               [runtime sibling]

src/lib/groundTruthStore.ts
  ← src/components/history/ui/DetailHistoryView.tsx     [runtime]
  ← src/components/runocr/ui/OcrResultPanel.tsx         [runtime]
  → @/common/storage/historyStore                       [type-only]

src/lib/profiles.ts
  ← src/components/test/TestWorkspace.tsx               [runtime + type]
  → ./testsets                                          [type-only sibling]

src/lib/restoreProfileStore.ts
  ← src/components/autorestore/AutoRestoreWorkspace.tsx [runtime]
  ← src/components/history/ui/DetailHistoryView.tsx     [runtime]
  ← src/lib/autofillEngine.ts                           [runtime sibling]

src/lib/testsets.ts
  ← src/app/api/autofill-cache/route.ts                 [runtime]
  ← src/app/api/ground-truth/route.ts                   [runtime]
  ← src/app/api/ocr-cache/route.ts                      [runtime]
  ← src/app/api/test-images/route.ts                    [runtime]
  ← src/components/test/TestWorkspace.tsx               [type-only]
  ← src/lib/profiles.ts                                 [type-only sibling]

src/types/utif.d.ts
  (ambient — 직접 import 사용처 없음; `import("utif")` 동적 호출에 의해 간접 보장)
```

### 4. Risk Assessment

| 파일 | risk | 사유 |
| --- | --- | --- |
| `autofillEngine.ts` | **MEDIUM** | 485 lines, 4 importer (1A 잔여 type-only 포함), sibling restoreProfile 의존, 사전 precheck 별도 필요 |
| `groundTruthStore.ts` | **LOW** | 2 importer leaf, no TestWorkspace, no new subdir |
| `profiles.ts` | **LOW** | 1 importer (TestWorkspace 2-line), testsets 사이블링 해소만 추가 |
| `restoreProfileStore.ts` | **LOW** | 3 importer leaf, no TestWorkspace, no new subdir |
| `testsets.ts` | **MEDIUM** | 6 importer (4 SSR API route + TestWorkspace + sibling), 새 도메인 `src/common/config/` 도입 |
| `utif.d.ts` | **N/A** | 본 plan scope 외 |

### 5. Recommended Next Steps

1. **LIB-CLEAN-4A-GROUND-TRUTH-STORE-MOVE**
   - **tool**: Codex (또는 Claude Code 무방)
   - **target**: `src/common/storage/groundTruthStore.ts`
   - **reason**: leaf, 2 importer, TestWorkspace 영향 없음, 가장 빠른 추가 정리.
   - **caution**: `mysuit_ocr_groundtruth` localStorage key 보존 가드 필수. backend GT 데이터(`public/data/.../groundtruth.json`)는 절대 touch 금지.

2. **LIB-CLEAN-4B-RESTORE-PROFILE-STORE-MOVE**
   - **tool**: Codex
   - **target**: `src/common/storage/restoreProfileStore.ts`
   - **reason**: leaf, autofillEngine 사이블링 해소 — autofillEngine 이동 전 반드시 선행.
   - **caution**: `RESTORE_PROFILE_STORAGE_KEY = "mysuit_ocr_restore_profiles"` 보존. autorestore 폴더명/route/`AutoRestoreWorkspace` 명칭 변경 금지(스펙 준수). AutoRestoreWorkspace + DetailHistoryView + autofillEngine 3 importer는 import path-only 변경.

3. **LIB-CLEAN-4C-TESTSETS-COMMON-CONFIG-MOVE**
   - **tool**: Claude Code
   - **target**: `src/common/config/testsets.ts` (새 도메인 폴더 도입)
   - **reason**: 6 importer + 새 폴더 + TestWorkspace touch + 4 SSR API route. logic-equivalent 가드와 새 폴더 ownership 검사가 묶음으로 필요.
   - **caution**: TestWorkspace는 import path-only 1줄만 보정. profiles 사이블링은 LIB-CLEAN-4D에서 해소되므로 본 phase에서는 `./testsets` sibling 그대로 두어도 무방. `public/data/testsets/**` 자산은 touch 금지.

4. **LIB-CLEAN-4D-PROFILES-TEST-UTILS-MOVE**
   - **tool**: Claude Code
   - **target**: `src/components/test/utils/profiles.ts`
   - **reason**: 단일 importer = TestWorkspace. testsets 사이블링이 alias로 바뀐 직후가 이동 적기. test feature local 정책 파일이 자기 폴더로 귀속.
   - **caution**: TestWorkspace 2줄 (line 36, 37) import path만 변경. logic_unchanged_vs_backup 가드 강제.

5. **LIB-CLEAN-4E-AUTOFILL-ENGINE-PRECHECK**
   - **tool**: Claude Code
   - **target**: (precheck only — 산출물 tmp/ + logs/)
   - **reason**: 485 lines + 4 importer + 1A 잔여 type-only dep + sibling restoreProfile dep. 이동 충돌/사이클/저장소 import 분석을 단독 phase로 분리.
   - **caution**: 운영 코드 수정 금지. ocrResultFormatters의 `@/lib/autofillEngine` type-only dep 해소 시나리오를 미리 점검.

6. **LIB-CLEAN-4F-AUTOFILL-ENGINE-MOVE**
   - **tool**: Claude Code
   - **target**: `src/common/utils/autofillEngine.ts`
   - **reason**: precheck 결과 반영. 이 이동으로 1A 잔여 `@/lib/autofillEngine` (in `common/utils/ocrResultFormatters.ts`)도 함께 해소.
   - **caution**: 18+ export 보존 검증. 3 import 보정 (bizNumber/historyStore/restoreProfileStore — restoreProfileStore는 LIB-CLEAN-4B에서 이미 alias로 변경되어 있어야 함). 4 importer 보정 (RunOcrWorkspace, OcrResultPanel, DetailHistoryView, common/utils/ocrResultFormatters). no React/DOM/localStorage 가드.

7. **LIB-CLEAN-4G-SRC-LIB-ABSENT-CHECK**
   - **tool**: Claude Code (또는 Codex 무방, 최종 가드만)
   - **target**: (final guard — 산출물 tmp/ + logs/)
   - **reason**: `src/lib` 디렉터리 empty/absent + `@/lib/*` 잔존 0 + typecheck/build PASS 강제. 이 PASS 후에만 Template table column definition 기능 작업 precheck 진입.

### 6. Do Not Move Yet
- **file**: `src/types/utif.d.ts`
- **reason**: src/lib cleanup 범위 외. ambient TypeScript shim이라 이동해도 의미가 거의 없고, 본 plan scope에서 다루면 scope-creep 위험.
- **required precheck or approval**: 별도 type cleanup phase에서 `src/common/types/`로 이동 여부 평가 (선택 사항). LIB-CLEAN-4G PASS 후에 결정.

(다른 5개 src/lib 파일은 "지금 이동 금지"가 아니라 "위의 순서대로 이동"이므로 본 섹션에 추가 없음.)

### 7. Verification Results
- **typecheck**: PASS (exit 0) — 본 precheck 실행 흐름에 포함됨
- **build**: PASS (exit 0) — 동일
- **static precheck**: `tmp/check_remaining_src_lib_ownership_lc4_precheck.mjs` → PASS (필수 항목; 잔존 `@/lib/*` import는 informational로만 출력)
- **src/lib remaining files**: 5 (`autofillEngine.ts`, `groundTruthStore.ts`, `profiles.ts`, `restoreProfileStore.ts`, `testsets.ts`)
- **production code modified**: false (본 precheck는 운영 파일 zero touch)
- **forbidden area modified**: false (TestWorkspace, test/core, AutoRestoreWorkspace, autorestore route, backend, fixtures, templates.json, GT 데이터 모두 미수정)
