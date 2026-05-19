# HISTORY-RESTORE-3 E2E 검증 리포트

검증 일시: 2026-05-19 (업데이트)  
초안 일시: 2026-05-18  
검증 방법: 코드 정적 분석 (브라우저 런타임 검증 불가 환경)  
도구: Claude Code (claude-sonnet-4-6)  
분석 대상 커밋: HISTORY-RESTORE-2A / 2B / 2C 완료 상태

---

## 1. 요약

| 항목 | 결과 |
|------|------|
| 전체 판정 | **PASS** (단, 이슈 I-5 주의) |
| 확인한 시나리오 수 | A~H 8개 (하위 체크포인트 포함 15개) |
| 회귀 발생 여부 | 없음 (UI 계층 회귀 없음) |
| 신규 이슈 | I-5: groundTruth 후보 제외 (행동 변경, 코드 수정 금지) |
| 기존 이슈 유지 | I-1~I-4 (모두 낮음~매우낮음) |
| typecheck | **PASS** (오류 0건) |
| build | **PASS** (21개 페이지 생성, ESLint 경고 1건 비차단) |
| 코드 수정 여부 | 없음 (검증/분석/리포트 전용) |
| HISTORY-RESTORE-2A~2C 마감 가능 여부 | **가능** (I-5 내용 확인 후 결정 권장) |

**이슈 I-5 요약**: HISTORY-RESTORE-2C에서 `collectInternalAutofillCandidates()` 재설계 과정에서 기존 groundTruth 후보(`mysuit_ocr_groundtruth`)가 autofill 경로에서 제외되었다. `readGroundTruthCandidateRecords()`는 현재 데드 코드 상태이다. 기존에 [저장] 버튼으로 groundTruth를 쌓아두었던 사용자는 해당 데이터가 autofill에 사용되지 않게 된다. 단, groundTruth의 "정답 비교" 표시 기능은 OcrResultPanel에서 별도 경로로 유지되어 영향 없다.

---

## 2. 현재 구조 요약

```
src/lib/
  historyStore.ts          — mysuit_ocr_history (localStorage, MAX 50건)
  restoreProfileStore.ts   — mysuit_ocr_restore_profiles (localStorage)
  autofillEngine.ts        — 우선순위 로직, autofill 적용
  groundTruthStore.ts      — mysuit_ocr_groundtruth (localStorage, 정답비교용)

src/app/
  history/page.tsx         — /history 라우트
  autorestore/page.tsx     — /autorestore 라우트 (HISTORY-RESTORE-2B 신규)

src/components/
  history/
    HistoryWorkspace.tsx      — 목록 페이지
    DetailHistoryView.tsx     — 상세보기 + [저장] + [자동복원 후보 저장] 버튼
  autorestore/
    AutoRestoreWorkspace.tsx  — restore profile 목록/상세/삭제 (2B 신규)
  upload/
    UploadWorkspace.tsx       — OCR 실행 시 autofill 호출 지점
```

### 자동복원 조회 우선순위 (HISTORY-RESTORE-2C 이후)

```
collectInternalAutofillCandidates(businessNumber) {
  1순위: mysuit_ocr_restore_profiles에서 같은 사업자번호 매칭
         → 있으면 즉시 반환 (history와 섞지 않음)
  2순위: mysuit_ocr_history에서 isUserEditedHistoryField 필터 기반 fallback
}
```

> **변경사항**: 이전에는 `mysuit_ocr_groundtruth`가 1순위로 포함됐으나 2C 이후 제외됨 (→ I-5)

---

## 3. 시나리오별 결과

| 시나리오 | 기대 | 코드 분석 결과 | 상태 | 비고 |
|---------|------|--------------|------|------|
| **A. restore profile 후보 있음** | restoreProfile이 history보다 우선 사용 | `collectInternalAutofillCandidates()`: matchingRestore > 0이면 즉시 반환. history 섞지 않음 | **PASS** | autofillEngine.ts:363-371 |
| A-1. 빈 값 비덮어쓰기 | 빈 restore profile 필드가 OCR 값 덮어쓰지 않음 | `readRestoreProfileCandidates()`에서 `isEmptyOcrValue()` + `isMeaninglessValue()` 필터로 빈 필드 제거 | **PASS** | autofillEngine.ts:338-343 |
| A-2. sourceType 확인 | suggestions에 sourceType: "restoreProfile" 포함 | `readRestoreProfileCandidates()`가 `sourceType: "restoreProfile"` 설정 | **PASS** | autofillEngine.ts:349 |
| **B. restore profile 없음 + history fallback** | 기존 history fallback 정상 작동 | matchingRestore.length === 0이면 `readHistoryCandidateRecords()` 반환 | **PASS** | autofillEngine.ts:372-373 |
| B-1. isUserEditedHistoryField 필터 유지 | 사용자가 수정한 필드만 fallback 후보 | `isUserEditedHistoryField()` 로직 그대로 유지 (source=text 또는 modified≠original) | **PASS** | autofillEngine.ts:251-258 |
| B-2. allowlist 5개 유지 | companyName/businessNumber/representative/tel/address만 | candidateFields 5개로 제한 | **PASS** | autofillEngine.ts:300 |
| **C. 둘 다 없음** | 후보 없음 상태 정상 표시 | candidateCount=0, status="no_candidates", 앱 크래시 없음 | **PASS** | UploadWorkspace.tsx:900 |
| **D. Restore 삭제 후 동작** | 삭제된 후보 다음 OCR에서 미사용, history 무영향 | `deleteRestoreProfile()`은 mysuit_ocr_restore_profiles만 write. historyStore 무관 | **PASS** | restoreProfileStore.ts:63-69 |
| **E. 일부 필드만 있는 restore profile** | 있는 필드만 복원, 빈 필드는 OCR 값 유지 | `readRestoreProfileCandidates()` 빈 필드 제거 → suggestions에서 해당 field 제외 → `applyAutofillToOutputFields()`에서 auto 없으면 currentValue 유지 | **PASS** | autofillEngine.ts:338-343, 453-468 |
| **F-1. History 목록** | 기존 목록 표시 정상 | HistoryWorkspace.tsx 변경 없음 | **PASS** | |
| **F-2. History 상세** | [저장]/[자동복원 후보 저장] 정상, 기존 데이터 표시 정상 | DetailHistoryView.tsx: 두 버튼 모두 구현, output_fields 표시 로직 변경 없음 | **PASS** | DetailHistoryView.tsx:578-583 |
| **F-3. Restore 탭** | 목록/상세/삭제/빈 상태 정상, history 무영향 | AutoRestoreWorkspace.tsx 전체 구현 확인. deleteTarget 확인 모달 포함 | **PASS** | |
| **F-4. RunOCR Preview** | 자동복원 상태 박스 정상, 품목표/배지 유지 | OcrResultPanel.tsx 타입 import만, 렌더링 로직 변경 없음 | **PASS** | |
| **F-5. Custom/Validation 탭** | 기존 동작 유지 | OcrResultPanel 변경 없음, autofillEngine 타입 레벨만 참조 | **PASS** | |
| **G. localStorage 안전성** | 두 키 구조 유지, parse 방어, 교차 영향 없음 | 항목 4에 상세 분석 | **PASS** | |
| **H. 자동복원 후보 저장 버튼** | 유효성 검사/diff 모달/merge 모두 정상 | 항목 H 상세 참조 | **PASS** | |

---

## 4. localStorage 상태 확인

### 4-1. `mysuit_ocr_history`

| 작업 | 위치 | 방어 코드 |
|------|------|-----------|
| 읽기 | `readHistoryRuns()` | try/catch, parse 실패 → `[]` |
| 쓰기 | `appendHistoryRun()`, `updateHistoryRun()` | QuotaExceededError 전용 폴백 (50→30→15→5→1 레코드 축소) |
| 행 삭제 | `deleteHistoryRun()` | try/catch |
| 전체 삭제 | `clearHistoryRuns()` | try/catch 없음 (사용처 없음, 위험도 매우 낮음) |

### 4-2. `mysuit_ocr_restore_profiles`

| 작업 | 위치 | 방어 코드 |
|------|------|-----------|
| 읽기 | `readRestoreProfiles()` | try/catch, parse 실패 → `[]`, Array 체크 포함 |
| 쓰기 | `writeRestoreProfiles()` | 내부 try/catch 없음; 호출처(handleSaveRestoreProfile, handleRestoreConfirmOk)에서 래핑 |
| 삭제 | `deleteRestoreProfile()` | readRestoreProfiles() 경로 보호됨, setItem은 미보호 |
| 정렬 | `sortRestoreProfilesByUpdatedAt()` | 순수 함수, 예외 없음 |

### 4-3. 두 키 간 교차 영향

- `historyStore.ts` ↔ `restoreProfileStore.ts`: 상호 import 없음
- `autofillEngine.ts`: 두 스토어 읽기만, 쓰기 없음
- `deleteRestoreProfile()`: `mysuit_ocr_restore_profiles`만 조작
- `deleteHistoryRun()`: `mysuit_ocr_history`만 조작
- **교차 영향 없음 → PASS**

### 4-4. updatedAt 내림차순 정렬

```typescript
sortRestoreProfilesByUpdatedAt():
  bTime.localeCompare(aTime) // 내림차순 확인 → PASS
```

### 4-5. businessNo + partyType 기준 중복 관리

```typescript
// 저장 시
profiles.findIndex((p) => p.businessNo === businessNo && p.partyType === "generic")
// 삭제 시
profiles.filter((p) => !(p.businessNo === businessNo && p.partyType === partyType))
// 조회 시
readRestoreProfiles().find((p) => p.businessNo === businessNo && p.partyType === partyType)
```
→ businessNo + partyType 복합키 중복 관리 정상 → **PASS**

---

## 5. UI 회귀 확인

### 5-1. autofillEngine이 UI에 영향 주는 방식

```
UploadWorkspace
  → collectInternalAutofillCandidates(bizNo)
  → buildAutofillSuggestionsFromCandidates()
  → applyAutofillToOutputFields()
  → OcrResultPanel (타입만 참조, 렌더링 로직 변경 없음)
```

### 5-2. 변경 범위 내 파일 영향

| 파일 | 변경 내용 | UI 회귀 위험 |
|------|-----------|-------------|
| `autofillEngine.ts` | restoreProfile 소스 추가, 우선순위 재설계 | 낮음 (OcrResultPanel은 타입만 참조) |
| `historyStore.ts` | 변경 없음 | 없음 |
| `restoreProfileStore.ts` | 신규 파일 | 없음 |
| `DetailHistoryView.tsx` | 버튼/모달 추가 | 없음 (기존 [저장] 동작 유지) |
| `AutoRestoreWorkspace.tsx` | 신규 컴포넌트 | 없음 |
| `OcrResultPanel.tsx` | 변경 없음 | 없음 |

### 5-3. 백업 파일 존재 확인

`OcrResultPanel_20260517_before_PREVIEW1.tsx` 확인됨. 이전 상태 복원 가능.

---

## 6. 발견된 이슈

### I-1: ESLint 경고 (심각도: 낮음)

- **증상**: `npm run build` 시 `ESLint: nextVitals is not iterable` 경고 출력
- **재현**: `npm run build` 실행
- **원인**: Next.js 15.5.x와 `eslint-config-next` 플러그인 버전 호환 문제
- **영향**: 빌드 결과물 영향 없음. CI/CD에서 ESLint를 error로 처리하면 차단 가능
- **수정 후보**: `eslint-config-next` 버전 업데이트 또는 `nextVitals` 규칙 비활성화
- **우선순위**: 낮음 (비기능적 경고)

---

### I-2: `writeRestoreProfiles()` QuotaExceededError 미처리 (심각도: 낮음)

- **증상**: localStorage 용량 초과 시 `writeRestoreProfiles()`가 예외를 던질 수 있음
- **재현**: localStorage가 가득 찬 환경에서 restore profile 저장 시도
- **원인**: `window.localStorage.setItem()`을 직접 호출, 내부 try/catch 없음
- **영향**: 호출처(handleSaveRestoreProfile, handleRestoreConfirmOk)에서 catch 래핑됨. 단, 세부 폴백 없음
- **수정 후보**: `writeRestoreProfiles()` 내부에 QuotaExceededError 처리 추가 (historyStore 패턴 참조)
- **우선순위**: 낮음 (현재 restore profile 수는 매우 적어 5MB 초과 가능성 낮음)

---

### I-3: `clearHistoryRuns()` try/catch 없음 (심각도: 매우 낮음)

- **증상**: clearHistoryRuns() 호출 시 예외 발생 가능
- **원인**: `window.localStorage.removeItem()` 직접 호출, try/catch 없음
- **영향**: removeItem은 일반적으로 예외 발생 매우 드뭄. 현재 호출처 없음
- **수정 후보**: 필요 시 try/catch 추가
- **우선순위**: 매우 낮음

---

### I-4: `allSame` 비교 단방향 (심각도: 매우 낮음)

- **증상**: handleSaveRestoreProfile()에서 기존 profile에 newProfile에 없는 필드가 있어도 allSame=true 가능
- **재현**: newProfile.fields = {companyName: "ABC"}, existing.fields = {companyName: "ABC", representative: "홍길동"} → allSame = true
- **원인**: `Object.entries(fields)` (newProfile)로만 순회
- **영향**: RestoreProfileFields가 4개 고정 필드라 실질적 영향 없음
- **수정 후보**: 양방향 비교 또는 PROFILE_FIELD_LABELS 키로 순회
- **우선순위**: 매우 낮음

---

### I-5: groundTruth 후보가 autofill 경로에서 제외됨 (심각도: 중간) ★ 신규 발견

- **증상**: HISTORY-RESTORE-2C 이후 `mysuit_ocr_groundtruth` 데이터가 autofill에 사용되지 않음
- **재현 단계**:
  1. History 상세에서 [저장] 클릭 → `mysuit_ocr_groundtruth`에 저장됨
  2. 동일 사업자번호 문서를 RunOCR → autofill 후보 없음 (groundTruth 미반영)
  3. `restore_profiles`에도 후보 없으면 history fallback만 사용
- **원인**: HISTORY-RESTORE-2C에서 `collectInternalAutofillCandidates()`를 재설계하면서 `readGroundTruthCandidateRecords()` 호출이 제거됨
  - **이전**: `return [...readGroundTruthCandidateRecords(), ...readHistoryCandidateRecords()]`
  - **이후**: restoreProfile > history (groundTruth 제외)
  - `readGroundTruthCandidateRecords()` 함수는 autofillEngine.ts에 잔존하지만 현재 데드 코드
- **영향 범위**:
  - [저장] 버튼을 통해 groundTruth에 데이터를 쌓아둔 사용자의 autofill 동작이 변경됨
  - groundTruth "정답 비교" 표시(OcrResultPanel)는 별도 경로로 유지되어 영향 없음
  - `mysuit_ocr_groundtruth` localStorage 데이터는 훼손되지 않음
- **수정 후보 (즉시 수정 금지)**:
  - 옵션 A: `collectInternalAutofillCandidates()`에 groundTruth 경로 재추가 (3순위)
  - 옵션 B: groundTruth 제외를 공식 정책으로 확정하고 `readGroundTruthCandidateRecords()` 삭제
  - 옵션 C: restoreProfile이 없고 history도 없을 때만 groundTruth fallback 추가 (3순위)
- **우선순위**: 중간 (기존 사용자에게 행동 변경 발생, 기존 mysuit_ocr_groundtruth 데이터 사장 우려)

---

## 7. 최종 결론

### HISTORY-RESTORE-2A~2C 마감 가능 여부

**조건부 마감 가능**

세 작업의 핵심 요구사항은 모두 구현되어 있다:
1. **2A**: [자동복원 후보 저장] 버튼 — 사업자번호 검증, allowlist 4개 필드, diff 모달, 빈 값 merge 비덮어쓰기 모두 구현
2. **2B**: `/autorestore` 라우트 — 목록/상세/삭제, updatedAt 내림차순, 확인 모달, history 무영향 모두 구현
3. **2C**: 우선순위 로직 — restoreProfile 1순위, history fallback 2순위, 혼합 없음, 빈 값 방어 모두 구현

단, **I-5 (groundTruth 제외)** 에 대해 팀 합의가 필요하다:
- groundTruth 제외가 의도적 설계 결정이라면 → 마감 가능, readGroundTruthCandidateRecords() 정리 권장
- groundTruth를 autofill에 계속 사용하려면 → 수정 후 마감

### 자동복원 구조 1차 분리 완료 여부

완료. localStorage 두 키 독립성, 우선순위 분리, UI 격리 모두 확인됨.

---

## 8. 다음 단계 제안

### 필수 확인 (마감 전)
- I-5 groundTruth 제외 의도 여부 팀 합의

### 브라우저 런타임 검증 권장 항목
- 실제 OCR 실행 후 `mysuit_ocr_history` 항목 확인
- [자동복원 후보 저장] 클릭 → `/autorestore` 화면에서 목록 확인
- 동일 사업자번호 이미지 재실행 → autofill 동작 확인
- restore profile 삭제 → history fallback autofill 확인

### 후속 작업 후보 (우선순위 순)
1. **I-5 처리**: groundTruth 포함/제외 정책 확정
2. **sourceType 배지 표시**: Preview에서 `sourceType === "restoreProfile"` 배지 표시 (현재 UX 누락)
3. **writeRestoreProfiles() QuotaExceededError 처리** (I-2)
4. **History list/detail 분리 설계**: 목록에서 상세 데이터 지연 로딩
5. **partyType supplier/buyer 확장**: 현재 "generic" 고정
6. **Restore 후보 직접 수정 기능**: /autorestore에서 필드 직접 편집
7. **Restore 후보 검색/필터**: 사업자번호/회사명 검색
8. **DB `ocr_restore_profiles` 매핑**: localStorage → DB 전환 시 restoreProfileStore.ts 교체

---

## 검증에 사용된 파일 목록

| 파일 | 역할 |
|------|------|
| `src/lib/autofillEngine.ts` | 우선순위 로직, 후보 수집, autofill 적용 |
| `src/lib/historyStore.ts` | mysuit_ocr_history CRUD |
| `src/lib/restoreProfileStore.ts` | mysuit_ocr_restore_profiles CRUD |
| `src/components/history/DetailHistoryView.tsx` | [저장]/[자동복원 후보 저장] 버튼 |
| `src/components/autorestore/AutoRestoreWorkspace.tsx` | Restore 탭 UI |
| `src/components/upload/UploadWorkspace.tsx` | OCR 실행 시 autofill 호출 |
| `backup/autofillEngine_20260506_before_autofill_detail_ui.ts` | 이전 구조 비교 기준 |
