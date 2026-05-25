# FRONTEND_REMAINING_LIB_FULL_CLEANUP_PLAN_PRECHECK 20260522

## 1. 사용 도구와 모델
- 도구: Claude Code (VSCode extension)
- 모델: Claude Opus 4.7 (1M context)
- 작업 디렉터리: `mysuit-ocr/`

## 2. 코드 수정 여부
- **운영 코드 수정 없음**.
- 파일 이동/import 보정/rename/refactor 전부 수행 안 함.
- 본 작업은 precheck 전용 — 분석 + 산출물 생성만.

## 3. 생성 파일
- `tmp/claude_frontend_remaining_lib_full_cleanup_plan_precheck.py` (재실행 가능; 라이브 importedBy 재산정 포함)
- `docs/FRONTEND_REMAINING_LIB_FULL_CLEANUP_PLAN_PRECHECK_20260522.md` (본 문서)
- `docs/FRONTEND_REMAINING_LIB_FULL_CLEANUP_PLAN_PRECHECK_20260522.json`
- `docs/FRONTEND_REMAINING_LIB_FULL_CLEANUP_MAP_20260522.csv`

## 4. 현재 남은 src/lib 파일 목록
8 파일 잔존 (spec 9개 중 `version.ts`는 디스크에 부재 — 이미 제거됨).

| # | 파일 | lines | importedBy |
| --- | --- | --- | --- |
| 1 | `src/lib/theme.ts` | 42 | 1 |
| 2 | `src/lib/login.ts` | 59 | 4 |
| 3 | `src/lib/axios.ts` | 137 | 2 |
| 4 | `src/lib/groundTruthStore.ts` | 97 | 2 |
| 5 | `src/lib/restoreProfileStore.ts` | 86 | 3 |
| 6 | `src/lib/testsets.ts` | 217 | 6 |
| 7 | `src/lib/profiles.ts` | 484 | 1 |
| 8 | `src/lib/autofillEngine.ts` | 485 | 4 |
| – | `src/lib/version.ts` | (absent) | 0 |

총 운영 코드 영향: 23 importer 사이트 (중복 제거 기준).

## 5. 파일별 역할 / import / export / importedBy 요약

### 5.1 `theme.ts` (42 lines)
- **역할**: `useTheme()` React hook — light/dark theme를 localStorage에 보관하고 `data-theme` 속성을 `document.documentElement`에 부여.
- **imports**: `react`
- **exports (key)**: `useTheme`
- **importedBy (1)**: `src/components/layout/Header.tsx`
- **유형 판정**: React-dependent UI hook + browser API + localStorage. pure util 아님.

### 5.2 `login.ts` (59 lines)
- **역할**: 로그인 토큰 blob을 localStorage에 저장/조회/삭제. `StoredLogin` 타입 + `getStoredLogin`/`saveLogin`/`clearLogin`/`hasStoredLogin` 헬퍼.
- **imports**: 없음
- **exports (key)**: `StoredLogin` (type), `getStoredLogin`, `saveLogin`, `clearLogin`, `hasStoredLogin`
- **importedBy (4)**: `axios.ts` (sibling), `RequireLogin.tsx`, `LoginWorkspace.tsx`, `layout/Header.tsx`
- **유형 판정**: 순수 localStorage persistence helper (React 없음). 로그인 feature local이 아니라 cross-feature 공유.

### 5.3 `axios.ts` (137 lines)
- **역할**: `/api` baseURL 가진 axios 싱글톤 + 요청 Bearer 토큰 주입 + 401/`loginCode=9999` 시 `/login` 리디렉트 + `ApiResponseError` 클래스.
- **imports**: `axios` (npm), `./login` (sibling)
- **exports (key)**: `default api`, `ApiResponseError`
- **importedBy (2)**: `components/history/HistoryWorkspace.tsx`, `components/login/LoginWorkspace.tsx`
- **유형 판정**: API client (axios + backend 의존). browser API(`window.location`) 사용.

### 5.4 `groundTruthStore.ts` (97 lines)
- **역할**: `(template, file)` 페어 키 기반 localStorage GT 저장소. `HistoryOutputField` 배열로부터 수정값을 정답으로 보존. `compareToGt`로 비교.
- **imports**: `type HistoryOutputField from @/common/storage/historyStore`
- **exports (key)**: `GroundTruthMap` (type), `MatchStatus` (type), `compositeKey`, `fieldKey`, `getGroundTruth`, `saveGroundTruth`, `clearGroundTruth`, `compareToGt`
- **importedBy (2)**: `components/history/ui/DetailHistoryView.tsx`, `components/runocr/ui/OcrResultPanel.tsx`
- **유형 판정**: localStorage persistence — common 의존(historyStore type) 있음. React/components 없음.

### 5.5 `restoreProfileStore.ts` (86 lines)
- **역할**: 사업자번호+partyType 키 기반 restore profile localStorage CRUD. autofill용 키 매핑 상수도 함께 제공.
- **imports**: 없음
- **exports (key)**: `RESTORE_PROFILE_STORAGE_KEY`, `RestoreProfile`/`RestoreProfileFields` (types), `AUTOFILL_TO_PROFILE_KEY`, `PROFILE_FIELD_LABELS`, `isMeaninglessValue`, `readRestoreProfiles`, `writeRestoreProfiles`, `deleteRestoreProfile`, `findRestoreProfile`, `sortRestoreProfilesByUpdatedAt`
- **importedBy (3)**: `lib/autofillEngine.ts` (sibling), `components/autorestore/AutoRestoreWorkspace.tsx`, `components/history/ui/DetailHistoryView.tsx`
- **유형 판정**: 순수 localStorage persistence. cross-feature 공유 (autorestore + history + autofillEngine).

### 5.6 `testsets.ts` (217 lines)
- **역할**: 정적 dataset 레지스트리(`TESTSETS`, `DATASET_FOLDERS`, `getTestset`) + manifest item/invoice profile 타입군.
- **imports**: 없음
- **exports (key)**: `TESTSETS`, `DATASET_FOLDERS`, `getTestset`, `TestsetMeta`, `DocumentType`, `QualityTag`, `Difficulty`, `InvoiceSubType`, `AmountProfile`, `PartyProfile`, `TableProfile`, `InvoiceTableExpectedDisplayColumn`, `InvoiceProfile`, `DatasetRole`, `DatasetStatus`, `ExpectedStatus`, `ManifestItem`, `DatasetManifest`
- **importedBy (6)**: `app/api/autofill-cache/route.ts`, `app/api/ground-truth/route.ts`, `app/api/ocr-cache/route.ts`, `app/api/test-images/route.ts`, `components/test/TestWorkspace.tsx`, `lib/profiles.ts` (sibling)
- **유형 판정**: 순수 config/constants + types (no runtime side effect). 4 SSR API routes + TestWorkspace + profiles sibling이 공유.

### 5.7 `profiles.ts` (484 lines)
- **역할**: Test 탭 profile 정책 단일 진입점 — receipt/finance/document/none profile 결정, 컬럼 정의, table profile 정책, KPI family 해소. 순수 타입 + 상수 + 헬퍼.
- **imports**: `type DocumentType from ./testsets` (sibling)
- **exports (key)**: `Profile`, `Overlay`, `ProfileResolution`, `ReceiptFieldKey`/`FinanceFieldKey`/`DocumentFieldKey`/`CardOverlayFieldKey`/`MedicalOverlayFieldKey`/`AnyFieldKey`, `FINANCE_TIER1_FIELDS`/`FINANCE_TIER2_FIELDS`/`DOCUMENT_PARTY_FIELDS`, `RECEIPT_COLUMNS`/`FINANCE_COLUMNS`/`DOCUMENT_COLUMNS`/`CARD_OVERLAY_COLUMNS`/`MEDICAL_OVERLAY_COLUMNS`, `resolveProfile`, `getBaseColumns`, `getOverlayColumns`, `getVisibleColumns`, `isNotApplicableField`, `isFinanceTier1`, `isProfileMismatchSuspected`, `KpiFamily`, `resolveKpiFamily`, `TableColumnKey`, `GridModeRecommendation`, `TableColumnMeta`, `TABLE_COLUMN_META`, `TableProfilePolicyResult`, `getExpectedTableColumns`, `TableRowsValidation`
- **importedBy (1)**: `components/test/TestWorkspace.tsx` (2개 import 라인 — runtime + type)
- **유형 판정**: 순수 test-feature 정책 (React/storage/browser 없음).

### 5.8 `autofillEngine.ts` (485 lines)
- **역할**: Autofill 비즈니스 로직. history + restoreProfile에서 후보 수집 → suggestion 생성/정렬 → output field에 적용. 순수 로직 (저장소를 조합만 함).
- **imports**: `@/common/utils/bizNumber`, `@/common/storage/historyStore`, `./restoreProfileStore` (sibling)
- **exports (key)**: `AutofillSource`/`OutputValueSource`/`AutofillAction` (types), `AutofillSuggestion`, `AutofillCandidateRecord`, `AutofillRunStatus`, `AutofillRunSummary`, `AutofillFieldMetadata`, `AutofillOutputFieldLike`, `AUTOFILLABLE_FIELDS`, `normalizeAutofillFieldKey`, `isAutofillableField`, `isEmptyOcrValue`, `canAutoApplySuggestion`, `sortAutofillSuggestions`, `collectInternalAutofillCandidates`, `buildAutofillSuggestionsFromCandidates`, `applyAutofillToOutputFields`, `suggestionsForHistoryField`
- **importedBy (4)**: `components/runocr/RunOcrWorkspace.tsx` (runtime), `components/runocr/ui/OcrResultPanel.tsx` (type-only), `components/history/ui/DetailHistoryView.tsx` (runtime), `common/utils/ocrResultFormatters.ts` (type-only — **1A 잔여 의존**)
- **유형 판정**: 순수 비즈니스 로직 (no React/DOM/localStorage/fetch). common/utils가 자신을 type-only로 import하고 있어 이 파일을 그대로 두면 `common/utils → @/lib/*` 잔존이 영원히 풀리지 않음.

### 5.9 `version.ts` — 부재
- 스펙에 후보로 적혀 있지만 `src/lib/version.ts`는 디스크에 존재하지 않음 (이전 정리 단계에서 이미 제거된 것으로 보임).
- 본 plan의 영향 0. phase 미발급.

## 6. 파일별 target path 추천

| # | 파일 | recommended target | 후보 |
| --- | --- | --- | --- |
| 1 | `theme.ts` | `src/components/layout/utils/theme.ts` | `src/common/ui/theme.ts` |
| 2 | `login.ts` | `src/common/storage/login.ts` | `src/components/login/utils/login.ts` |
| 3 | `axios.ts` | `src/common/api/axios.ts` *(새 도메인 폴더)* | — |
| 4 | `groundTruthStore.ts` | `src/common/storage/groundTruthStore.ts` | `src/components/test/utils/groundTruthStore.ts` |
| 5 | `restoreProfileStore.ts` | `src/common/storage/restoreProfileStore.ts` | `src/components/autorestore/utils/restoreProfileStore.ts` |
| 6 | `testsets.ts` | `src/common/config/testsets.ts` *(새 도메인 폴더)* | `src/components/test/data/testsets.ts` |
| 7 | `profiles.ts` | `src/components/test/utils/profiles.ts` | `src/common/config/profiles.ts` |
| 8 | `autofillEngine.ts` | `src/common/utils/autofillEngine.ts` | — |

추천 근거 요약:
- **theme**: React hook이라 `src/common/utils`는 금지 boundary (React-free). 단일 importer가 `components/layout/Header.tsx`이므로 layout/utils가 자연스러움.
- **login**: 단순 localStorage helper지만 axios + layout Header + login UI 3개 feature가 공유 → login feature local로 가두면 layout/axios가 login feature를 import하게 됨. `common/storage`(imageStore/historyStore 옆)가 정확.
- **axios**: API client는 `common/storage`도 `common/utils`도 적합치 않음 → 새 도메인 `src/common/api/` 도입.
- **groundTruthStore**: history + runocr가 소비, test feature는 직접 import 없음. `common/storage`가 적합.
- **restoreProfileStore**: autorestore + history + autofillEngine 3 feature가 공유. `autorestore/utils`로 두면 history/autofillEngine이 autorestore feature를 import하게 됨 → `common/storage`로.
- **testsets**: 4 SSR API route + TestWorkspace + profiles sibling. test feature 폴더로 두면 4 API route가 feature 폴더를 import하게 됨 → 새 도메인 `src/common/config/`.
- **profiles**: 유일 importer가 TestWorkspace, 자체도 test-tab 정책. `components/test/utils/`가 정확.
- **autofillEngine**: 4 importer 중 1개가 `common/utils/ocrResultFormatters` (1A 시점부터 잔존하는 `@/lib/autofillEngine` 의존). 순수 로직이라 `common/utils/`가 적합. 이 이동으로 1A 잔여 의존이 자동 해소됨.

## 7. 파일별 TestWorkspace 영향

| 파일 | TestWorkspace 영향 | test/core 영향 |
| --- | --- | --- |
| `theme.ts` | `NO_TEST_IMPACT` | × |
| `login.ts` | `NO_TEST_IMPACT` | × |
| `axios.ts` | `NO_TEST_IMPACT` | × |
| `groundTruthStore.ts` | `NO_TEST_IMPACT` | × |
| `restoreProfileStore.ts` | `NO_TEST_IMPACT` | × |
| `testsets.ts` | `TEST_WORKSPACE_DIRECT_IMPORT_BUT_SAFE_IMPORT_PATH_ONLY` | × |
| `profiles.ts` | `TEST_WORKSPACE_DIRECT_IMPORT_BUT_SAFE_IMPORT_PATH_ONLY` | × |
| `autofillEngine.ts` | `NO_TEST_IMPACT` | × |

확인 사실:
- `src/components/test/core/*` 디렉터리에는 잔존 src/lib 파일 중 어느 것도 직접 import하지 않음 (BZ-1에서 이미 정리됨).
- TestWorkspace는 testsets/profiles 두 파일만 import. 이동 시 import path 1~2줄만 보정 → byte-equivalent 확인 가능 (logic_unchanged_vs_backup 패턴).

## 8. 파일별 위험도

| 파일 | risk | 사유 |
| --- | --- | --- |
| `theme.ts` | LOW | 1 importer, leaf |
| `login.ts` | LOW | 4 importer, leaf |
| `axios.ts` | LOW | 2 importer; login 사이블링 의존 |
| `groundTruthStore.ts` | LOW | 2 importer, leaf |
| `restoreProfileStore.ts` | LOW | 3 importer, leaf |
| `testsets.ts` | MEDIUM | 6 importer (4 API route 포함), 새 폴더 `common/config/` 도입 |
| `profiles.ts` | LOW | 1 importer; testsets 선행 이동 필요 |
| `autofillEngine.ts` | MEDIUM | 485 lines, 4 importer (common/utils 잔여 dep 1개), restoreProfile 선행 이동 필요 |

## 9. 이동 우선순위 (확정 phase 시퀀스)

low-risk leaf 우선, dep 그래프 위배 방지 순:

| phase | 대상 | 이유 |
| --- | --- | --- |
| **LIB-CLEAN-1-THEME-MOVE** | `theme.ts → components/layout/utils/` | 1 importer leaf, 가장 빠른 시작점. |
| **LIB-CLEAN-2-LOGIN-STORAGE-MOVE** | `login.ts → common/storage/` | 순수 localStorage helper. axios의 sibling 의존이라 먼저. |
| **LIB-CLEAN-3-AXIOS-API-MOVE** | `axios.ts → common/api/` | login 이동 후. 새 폴더 `common/api/` 도입. |
| **LIB-CLEAN-4-GROUND-TRUTH-STORE-MOVE** | `groundTruthStore.ts → common/storage/` | leaf, 2 importer. |
| **LIB-CLEAN-5-RESTORE-PROFILE-STORE-MOVE** | `restoreProfileStore.ts → common/storage/` | autofillEngine의 sibling 의존 해소를 위해 autofillEngine 선행. |
| **LIB-CLEAN-6-TESTSETS-COMMON-CONFIG-MOVE** | `testsets.ts → common/config/` | 새 폴더 `common/config/` 도입. profiles의 sibling 의존 해소. |
| **LIB-CLEAN-7-PROFILES-TEST-UTILS-MOVE** | `profiles.ts → components/test/utils/` | testsets 이동 후. 단일 importer = TestWorkspace. |
| **LIB-CLEAN-8-AUTOFILL-ENGINE-PRECHECK** | (precheck only) | 485 lines + common/utils 잔여 type-only 의존 분석. |
| **LIB-CLEAN-9-AUTOFILL-ENGINE-MOVE** | `autofillEngine.ts → common/utils/` | 1A 잔여 `@/lib/autofillEngine` import 동시 해소. |
| **LIB-CLEAN-10-SRC-LIB-ABSENT-CHECK** | (final guard) | `src/lib` empty/absent + `@/lib/*` 잔존 0 + typecheck/build PASS. |

## 10. src/lib 완전 제거 가능성

**판정: `CAN_CLOSE_LIB_AFTER_PLANNED_MOVES`**

- 분석 대상 8 파일 모두 명확한 target path 존재. "유지" 판정 0건.
- "보류" 판정 0건. `autofillEngine`은 precheck 단계가 한 phase 추가될 뿐, 결국 이동되어 최종 LIB-CLEAN-9에서 사라짐.
- 신규 도메인 폴더 2개(`src/common/api/`, `src/common/config/`) 도입 필요 — 각 첫 도입 phase(3, 6)에서 처리.
- LIB-CLEAN-10에서 디렉터리 부재 + 잔존 import 0건을 강제 확인.
- 따라서 위 10개 phase 완수 시 **`src/lib` 디렉터리는 비워지거나 제거 가능**.

## 11. static check 계획

각 이동 phase의 static check script + 핵심 검증 항목:

| phase | script | 핵심 검증 |
| --- | --- | --- |
| 1 | `tmp/check_theme_layout_utils_move_th1.mjs` | new 존재 / old 부재 / `useTheme` 보존 / Header 1줄 logic-equivalent / `@/lib/theme` 잔존 0 |
| 2 | `tmp/check_login_common_storage_move_lg1.mjs` | `mysuit_ocr_login` key 보존 / 5 import 보정 (axios sibling 포함) / no components/* import |
| 3 | `tmp/check_axios_common_api_move_api1.mjs` | default + `ApiResponseError` 보존 / login import = `@/common/storage/login` / 2 importer 보정 |
| 4 | `tmp/check_ground_truth_store_common_storage_move_gt1.mjs` | `mysuit_ocr_groundtruth` key 보존 / 8 export 보존 / 2 importer 보정 / no components/* import |
| 5 | `tmp/check_restore_profile_store_common_storage_move_rp1.mjs` | `RESTORE_PROFILE_STORAGE_KEY` 보존 / 11 export 보존 / 3 importer 보정 (autofillEngine sibling 포함) |
| 6 | `tmp/check_testsets_common_config_move_ts1.mjs` | `TESTSETS`/`DATASET_FOLDERS`/`getTestset` 보존 / 18 type export 보존 / 6 importer 보정 / TestWorkspace logic-equivalent / no components/* import |
| 7 | `tmp/check_profiles_test_utils_move_pr1.mjs` | 정책 export 30+ 보존 / TestWorkspace 2 import 보정 / TestWorkspace logic-equivalent / testsets sibling 해소 |
| 8 (precheck) | `tmp/codex_frontend_autofill_engine_move_precheck.py` | 4 importer impact + cycle 분석 + storage import 검증 |
| 9 | `tmp/check_autofill_engine_common_utils_move_af1.mjs` | 18+ export 보존 / 3 import 보정 (bizNumber/historyStore/restoreProfileStore) / 4 importer 보정 (1A 잔여 dep 포함) / no React/DOM/localStorage / `@/lib/autofillEngine` 잔존 0 (특히 common/utils) |
| 10 (final) | `tmp/check_src_lib_absent_final.mjs` | `src/lib` 디렉터리 empty 또는 absent / `@/lib/*` import 0건 / typecheck PASS / build PASS |

각 phase는 기존 phase 패턴 유지: 백업 → `git mv` → import path 보정 → tmp static check → typecheck/build → md+json 보고서.

## 12. dirty 상태
git status (--short) 기준 사전 dirty:
- 운영 코드 dirty: `src/app/{autorestore,history,layout,ocr,template}/page.tsx`, `src/components/{autorestore/AutoRestoreWorkspace,history/HistoryWorkspace,login/LoginWorkspace,runocr/RunOcrWorkspace,runocr/ui/OcrDocViewer,runocr/ui/OcrResultPanel,runocr/utils/buildOcrFormData,template/TemplateWorkspace,template/UnstructuredBuilder,test/TestWorkspace,test/core/autofill,test/core/extract}.tsx/.ts`, `src/lib/{autofillEngine,groundTruthStore}.ts`
- 이름 변경(R)/이동(RM) 다수 — 이전 phase 산출물(이미 commit 안 된 상태로 누적).
- 외부 데이터 dirty: `../ocr-server/data/templates.json` (TPL-95328E52 영향 후보 — **본 precheck에서 손대지 않음**), `../ocr-server/data/review_log.jsonl`.
- 다수 docs 신규 파일(`??`) — 이전 phase 보고서.

dirty 파일은 본 precheck에서 **되돌리지 않음** (작업 원칙 준수). `templates.json` dirty는 별도 TPL-95328E52 후속 precheck에서 다룬다.

## 13. typecheck / build 결과
- `npm run typecheck` → **PASS** (exit 0)
- `npm run build` → **PASS** (exit 0)
- known stderr noise: `ESLint: nextVitals is not iterable` — exit 0 (non-blocking)
- 로그:
  - `ocr-server/logs/claude_CLAUDE_FRONTEND_REMAINING_LIB_FULL_CLEANUP_PLAN_PRECHECK_NO_PROD_MODIFY.out.log`
  - `ocr-server/logs/claude_CLAUDE_FRONTEND_REMAINING_LIB_FULL_CLEANUP_PLAN_PRECHECK_NO_PROD_MODIFY.err.log`

## 14. 다음 실제 작업 제안

1. **LIB-CLEAN-1-THEME-MOVE** 실행 (가장 단순, 1 importer leaf).
2. 이후 phase 2 → 10을 위 순서대로 진행. 각 phase는 1 파일만 이동하고 즉시 static check + typecheck + build로 가드.
3. LIB-CLEAN-9 완료 시 `src/common/utils/ocrResultFormatters.ts`의 `@/lib/autofillEngine` type-only 잔여 import가 자동 해소됨.
4. **LIB-CLEAN-10-SRC-LIB-ABSENT-CHECK** PASS 후에만 Template table column definition 기능 작업 precheck로 진입.
5. `templates.json` dirty와 TPL-95328E52는 별도 precheck로 분리하여 본 lib 정리 close-out 후에 다룬다.
6. autorestore 폴더명 / `/autorestore` 라우트 / `AutoRestoreWorkspace` 명칭은 본 plan에서 변경하지 않음 (제약 준수).
