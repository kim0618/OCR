## LIB-CLEAN-4E Autofill Engine Precheck

### 1. Summary
- **현재 src/lib 잔여 파일**: `autofillEngine.ts` (단 1개).
- **autofillEngine.ts 라인 수**: 485
- **importer 수 (production)**: 4 (runocr/RunOcrWorkspace runtime; runocr/ui/OcrResultPanel type-only; history/ui/DetailHistoryView runtime; common/utils/ocrResultFormatters type-only — 1A 잔여 dep)
- **importer 수 (tmp)**: 0
- **runtime importer**: 2 (RunOcrWorkspace, DetailHistoryView)
- **type-only importer**: 2 (OcrResultPanel, common/utils/ocrResultFormatters)
- **common/utils 이동 적합성**: **SUITABLE WITH NOTE** — React/components/JSX/DOM/fetch/XHR/backend/node-fs 의존 없음. 단 1건 SSR-guarded `window.localStorage.getItem` 존재 (line 274, `readGroundTruthCandidateRecords()` 내부, `typeof window === "undefined"` 가드 하). 쓰기 없음. LC-4F static check는 이 1건을 명시적으로 허용해야 함.
- **move readiness**: **READY** (sibling 의존 이미 alias로 해소됨 — LC-4B 결과)
- **권장 target**: `src/common/utils/autofillEngine.ts`
- **권장 도구**: Claude Code (485 lines + 4 importer + 1A 잔여 dep 해소 동반)
- **다음 작업명**: LIB-CLEAN-4F-AUTOFILL-ENGINE-MOVE → LIB-CLEAN-4G-SRC-LIB-ABSENT-CHECK

### 2. File Analysis
- **책임**: Autofill 비즈니스 로직. 사업자번호 → restoreProfile + history + GT 후보 수집 → suggestion 생성/정렬/적용. RunOCR/History 양쪽이 공유하는 cross-feature 엔진.
- **imports** (3 — 전부 alias):
  - `@/common/utils/bizNumber` (runtime: `normalizeBizNumber`)
  - `@/common/storage/historyStore` (runtime + type: `readHistoryRuns`, `HistoryOutputField`)
  - `@/common/storage/restoreProfileStore` (runtime: `readRestoreProfiles`, `isMeaninglessValue`)
- **exports — type (10)**: `AutofillSource`, `OutputValueSource`, `AutofillAction`, `AutofillSuggestion`, `AutofillCandidateRecord`, `AutofillRunStatus`, `AutofillRunSummary`, `AutofillFieldMetadata`, `AutofillOutputFieldLike`
- **exports — runtime const (1)**: `AUTOFILLABLE_FIELDS`
- **exports — runtime functions (9)**: `normalizeAutofillFieldKey`, `isAutofillableField`, `isEmptyOcrValue`, `canAutoApplySuggestion`, `sortAutofillSuggestions`, `collectInternalAutofillCandidates`, `buildAutofillSuggestionsFromCandidates`, `applyAutofillToOutputFields`, `suggestionsForHistoryField`
- **storage dependencies**: indirect via `@/common/storage/historyStore.readHistoryRuns` + `@/common/storage/restoreProfileStore.readRestoreProfiles` + 1건 직접 `window.localStorage.getItem('mysuit_ocr_groundtruth')` (SSR-guarded fallback; 쓰기 없음).
- **common utility dependencies**: `@/common/utils/bizNumber.normalizeBizNumber`.
- **feature dependencies**: 없음 (components/* import 0건, app/api/* import 0건).
- **side effects**: 없음 (top-level 실행/구독 없음). 모든 storage 접근은 함수 호출 시점에만 발생, SSR-guarded.

### 3. Importer Analysis

| importer | kind | usage | required change in 4F |
| --- | --- | --- | --- |
| `src/components/runocr/RunOcrWorkspace.tsx` (line 51) | runtime + type | 다수 심볼 destructured (collectInternalAutofillCandidates, applyAutofillToOutputFields, canAutoApplySuggestion, buildAutofillSuggestionsFromCandidates, AUTOFILLABLE_FIELDS, types 등) | `@/lib/autofillEngine` → `@/common/utils/autofillEngine`, import path-only |
| `src/components/runocr/ui/OcrResultPanel.tsx` (line 27) | type-only | `AutofillAction`, `AutofillRunSummary`, `AutofillSuggestion`, `OutputValueSource` | `@/lib/autofillEngine` → `@/common/utils/autofillEngine`, import path-only |
| `src/components/history/ui/DetailHistoryView.tsx` (line 28) | runtime | `normalizeAutofillFieldKey` | `@/lib/autofillEngine` → `@/common/utils/autofillEngine`, import path-only |
| `src/common/utils/ocrResultFormatters.ts` (line 21) | type-only | `AutofillAction`, `OutputValueSource` (1A 시점부터 잔존하는 `@/lib/autofillEngine` 잔여 dep) | `@/lib/autofillEngine` → `./autofillEngine` (sibling) — LC-4F가 1A 잔여 dep을 자동 해소 |

tmp importer: **0건** (none of tmp/* scripts import autofillEngine; some scripts only NAME-mention "autofillEngine" in SIBLINGS_THAT_MUST_STAY_IN_LIB lists which are mechanical expected-list entries, not imports).

### 4. Common Utils Suitability
- **React / components dependency**: 없음 (`no_react_import` PASS, `no_components_import` PASS)
- **DOM / browser global dependency**: `document` / `window.location` / `window.history` 사용 0건. **`window.localStorage` 직접 read 1건**(line 274) — `readGroundTruthCandidateRecords()`. 함수 전체가 `if (typeof window === "undefined") return [];` SSR guard 안에서 실행. `localStorage.setItem/removeItem/clear` 호출 0건 (write 없음).
- **storage direct dependency**: 위 1건 + 간접(historyStore/restoreProfileStore 헬퍼).
- **backend / fixture dependency**: 없음 (`no_backend_or_node_fs_import` PASS — `fs`/`fs/promises`/`path`/`backend/*` import 0건).
- **API route dependency**: 없음 (`fetch` / `XMLHttpRequest` 사용 0건).
- **common/utils suitability verdict**: **SUITABLE**
- **reason**:
  1. 본질은 비즈니스 로직 (suggestion 생성/정렬/적용 + 후보 수집). 저장소는 *읽기 fallback* 으로만 사용.
  2. 4 importer가 runocr + history + common/utils로 cross-feature이므로 어떤 components/feature 폴더로도 가둘 수 없음.
  3. SSR-guarded localStorage read는 common/utils 내 기존 helper 패턴과 어긋나지 않음 (정확히 같은 패턴이 common/storage 내 store들 — historyStore, imageStore — 에 적용 중).
  4. `common/storage`로 옮기는 대안은 부적합 — autofillEngine은 storage CRUD가 아니라 candidate orchestration이다. common/storage는 read/write/delete primitive 전용.

### 5. Expected 4F Move Scope

- **move**:
  - from: `src/lib/autofillEngine.ts`
  - to: `src/common/utils/autofillEngine.ts`
  - method: `git mv` (body byte-identical; 3 alias imports 그대로 유지 가능)

- **import path 보정 파일 (4)**:
  - `src/components/runocr/RunOcrWorkspace.tsx:51` — `@/lib/autofillEngine` → `@/common/utils/autofillEngine`
  - `src/components/runocr/ui/OcrResultPanel.tsx:27` — same
  - `src/components/history/ui/DetailHistoryView.tsx:28` — same
  - `src/common/utils/ocrResultFormatters.ts:21` — `@/lib/autofillEngine` → `./autofillEngine` (sibling, 1A 잔여 dep 해소)

- **static checks to add/update (LC-4F)**:
  - **신규**: `tmp/check_autofill_engine_common_utils_move_lc4f.mjs`
    - new path 존재 / old path 부재
    - SIBLINGS_THAT_MUST_STAY_IN_LIB = [] (autofillEngine 마지막)
    - autofillEngine 19개 export 보존
    - autofillEngine purity: no React / no components / no fetch / no document / no localStorage.write — 단 `window.localStorage` *읽기 1건* 는 SSR guard 하에서 허용 (LC-4F는 이 specific case를 explicit allowlist로 처리)
    - 4 importer new path 사용
    - 4 importer logic_unchanged_vs_backup
    - residual `@/lib/autofillEngine` / `../lib/autofillEngine` / `../../lib/autofillEngine` 0건
    - sibling import in ocrResultFormatters resolved (`./autofillEngine`)
  - **patch (기대값 보정)**: 14개 기존 SIBLINGS 가드 (cs1/cs2/bz1/lc1/lc2/lc3/lc4a/lc4b/lc4c-via-EXPECTED + 1a~1f)에서 `"autofillEngine.ts"` 항목 제거.
  - **patch**: `tmp/check_remaining_src_lib_ownership_lc4_precheck.mjs`의 `REMAINING_LIB`을 `[]`로 변경 (또는 `lib_dir_exists`가 false인 케이스 허용).
  - **patch**: `tmp/check_testsets_common_config_move_lc4c.mjs`의 `EXPECTED_REMAINING_LIB`를 `[]`로 변경.
  - **patch**: `tmp/check_profiles_test_utils_move_lc4d.mjs`의 `EXPECTED_REMAINING_LIB`를 `[]`로 변경.

- **invariants (반드시 보존)**:
  - 10 type export + 1 runtime const + 9 runtime function = **19 export 모두 보존**
  - 3 alias import (bizNumber / historyStore / restoreProfileStore) 그대로 유지
  - body byte-identical (import 보정 없이도 동일 — 모두 alias이므로 이동 후에도 유효)
  - SSR-guarded `window.localStorage.getItem('mysuit_ocr_groundtruth')` 동작 보존
  - `mysuit_ocr_groundtruth` storage key 보존
  - 4 importer는 import path 1줄만 변경 (logic_unchanged_vs_backup PASS 필수)

### 6. Risk Assessment
- **risk**: **MEDIUM**
- **사유**:
  - 485 lines (가장 큰 잔여 파일)
  - 4 importer (runocr + history + common/utils 잔여 dep)
  - SSR-guarded localStorage read 1건이 LC-4F static check에서 strict "no localStorage" 가드와 충돌할 수 있음 → check 설계에 주의
  - 1A 잔여 dep 해소가 동시에 발생 (`common/utils/ocrResultFormatters.ts`의 import) → 의도된 부수 효과지만 검사로 명시
  - import path만 변경되므로 로직/저장소/UI 동작 변경 위험 LOW
  - LC-4F 통과 시 `src/lib` 완전 부재 가능 → LC-4G 통과 가능성 매우 높음

### 7. Do Not Change in 4F
- `src/components/test/TestWorkspace.tsx` (autofillEngine import 없음 — touch 금지)
- `src/components/test/core/**` (autofillEngine import 없음 — touch 금지)
- `src/components/autorestore/**` (autofillEngine import 없음 — touch 금지). autorestore 폴더명, route, AutoRestoreWorkspace 명칭 그대로.
- `src/common/storage/**` (restoreProfile/groundTruth/history/image/login: 로직 수정 금지; LC-4F는 sibling 의존 변경 없음 — alias 그대로 유지)
- `src/common/config/testsets.ts`, `src/components/test/utils/profiles.ts` (이번 이동과 무관)
- `src/common/api/axios.ts` (autofillEngine과 무관)
- backend, fixture, templates.json, public/data/testsets, ground truth 데이터 — 전부 touch 금지
- autofillEngine 로직/export 이름/storage key 변경 금지
- 4 importer는 import path 1줄 외 수정 금지 (특히 RunOcrWorkspace JSX/state/handler/test flow 보존)

### 8. LIB-CLEAN-4G Preparation
- **src/lib absent 가능 여부**: **YES**. autofillEngine 이동 후 src/lib 디렉터리는 빈 폴더가 됨. LC-4G는 빈 디렉터리 + `@/lib/*` 잔존 0 + typecheck/build PASS를 final guard로 강제.
- **`@/lib/*` 잔존 import 제거 가능 여부**: **YES**. 현재 잔존은 4건 (전부 `@/lib/autofillEngine`). LC-4F가 4 importer 보정으로 0건 만듦.
- **expected check updates**:
  - LC-4 precheck (`REMAINING_LIB` → `[]`)
  - LC-4C / LC-4D (EXPECTED_REMAINING_LIB → `[]`)
  - 14 기존 SIBLINGS 가드 (autofillEngine.ts 제거)
- **final guard items (LC-4G에서 확인)**:
  - `src/lib` 디렉터리 empty 또는 absent
  - `src/lib/*.ts` 0건
  - `src` 전체에서 `from "@/lib/*"` / `from "../lib/*"` / `from "../../lib/*"` 0건
  - `tmp/*` 잔존 `@/lib/*` import는 historical precheck.py snapshot만 허용 (정보용)
  - typecheck PASS / build PASS
  - 모든 기존 static check 러너 exit 0
  - markdown contract PASS
  - LC-4G 자체 static check가 `[SRC_LIB_ABSENT_CHECK_LC4G] PASS` 출력
  - Template table column definition 기능 작업 precheck는 LC-4G PASS 직후에만 진입

### 9. Verification Results
- **typecheck**: PASS (exit 0)
- **build**: PASS (exit 0)
- **static precheck**: `tmp/check_autofill_engine_precheck_lc4e.mjs` → PASS
- **production code modified**: false (본 precheck zero touch)
- **forbidden area modified**: false (TestWorkspace, test/core, AutoRestoreWorkspace, autorestore route, backend, fixtures, templates.json, public/data/testsets, GT 데이터 모두 미수정)
- **FAIL count**: 0
