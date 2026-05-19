# HISTORY-STRUCTURE-2B History 목록 조회 index 우선 전환 리포트

작성 일시: 2026-05-19  
도구: Claude Code (claude-sonnet-4-6)  
작업 범위: History 목록 조회를 `mysuit_ocr_history_index` 우선으로 전환, 기존 기능 완전 유지

---

## 1. 요약

| 항목 | 결과 |
|------|------|
| 전체 판정 | **PASS** |
| 목록 조회 index 우선 전환 | O (merge 방식) |
| fallback 동작 | O (index 없음/빈 배열/parse 실패 → legacy 반환) |
| 기존 기능 회귀 | 없음 |
| typecheck | **PASS** (오류 0건) |
| build | **PASS** (21개 페이지) |
| 기존 `mysuit_ocr_history` 구조 변경 | **없음** |
| 기존 상세 조회 변경 | **없음** |

---

## 2. 백업 및 수정 파일

### 백업 파일

| 백업 파일 | 원본 |
|-----------|------|
| `backup/historyStore_20260519_before_HISTORY_STRUCTURE_2B.ts` | `src/lib/historyStore.ts` |
| `backup/HistoryWorkspace_20260519_before_HISTORY_STRUCTURE_2B.tsx` | `src/components/history/HistoryWorkspace.tsx` |

### 수정 파일

| 파일 | 변경 내용 |
|------|-----------|
| `src/lib/historyStore.ts` | `indexItemToRunRecord()` + `readHistoryListWithFallback()` 추가 (기존 코드 변경 없음) |
| `src/components/history/HistoryWorkspace.tsx` | import 추가 + `boardList()` 한 줄 변경 (`readHistoryRuns` → `readHistoryListWithFallback`) |

---

## 3. 변경 내용

### 추가된 함수 (`src/lib/historyStore.ts`)

#### `indexItemToRunRecord(item: HistoryIndexItem): HistoryRunRecord`

`HistoryIndexItem`을 `HistoryRunRecord`로 변환하는 private helper.  
index에 없는 상세 필드는 undefined로 남겨 목록 UI와 호환.

```typescript
{ job_id: item.historyId, file_name: ..., template_name: ..., processing_time: 0, created_at: ..., status: ... }
```

#### `readHistoryListWithFallback(): HistoryRunRecord[]` (exported)

목록 조회 핵심 함수. **Merge 전략** 채택.

```
1. readHistoryRuns() → legacy 항상 읽음 (base)
2. readHistoryIndex() 시도
   - index.length === 0 → legacy 반환 (완전 fallback)
   - index.length > 0 → legacy 항목마다 index 데이터로 보강
   - try/catch → parse 실패 시 legacy 반환
3. index에만 있는 항목 (방어용) 추가
4. created_at 내림차순 정렬
```

### HistoryWorkspace.tsx 변경

```typescript
// 기존
const list = readHistoryRuns();

// 변경
const list = readHistoryListWithFallback();
```

---

## 4. 조회 우선순위와 전략

### 왜 merge 방식인가?

| 방식 | index 없음 | 구 데이터 | 삭제 후 | 복잡도 |
|------|-----------|----------|---------|--------|
| index-only | 빈 목록 ✗ | 안 보임 ✗ | 재출현 ✗ | 낮음 |
| **merge (채택)** | legacy 전체 표시 ✓ | 그대로 표시 ✓ | 즉시 반영 ✓ | 중간 |
| always-legacy | index 미활용 ✗ | 표시 ✓ | 즉시 반영 ✓ | 낮음 |

merge 방식은:
- **삭제 즉시 반영**: `deleteHistoryRun()`이 legacy를 삭제하므로 다음 `boardList()` 때 merge 결과에서도 사라짐
- **구 데이터 보존**: 2A 이전 항목은 index에 없어도 legacy에서 그대로 표시
- **index 데이터 반영**: 2A 이후 항목은 index의 보강 필드(templateName, status 등) 사용

### 조회 우선순위

```
1순위: mysuit_ocr_history_index (있는 항목만 보강)
2순위: mysuit_ocr_history (항상 base, fallback)
```

---

## 5. fallback 조건

| 조건 | 결과 |
|------|------|
| `mysuit_ocr_history_index` key 없음 | legacy 반환 |
| index parse 실패 | legacy 반환 (catch) |
| index 배열이 아님 | legacy 반환 (length check) |
| index.length === 0 | legacy 반환 |
| index item에 historyId 없음 | 해당 item skip (indexMap에 미포함) |
| 변환 중 예외 | legacy 반환 (catch) |

---

## 6. 상세 조회 영향 확인

상세 조회는 변경 없음.

```typescript
// HistoryWorkspace.tsx 상세보기 클릭 (변경 없음)
onClick={() => {
  const all = readHistoryRuns();  // ← 여전히 readHistoryRuns() 사용
  const full = all.find((r) => r.job_id === row.job_id) ?? null;
  setDetailRecord(full);
}}
```

- `row.job_id` = index의 `historyId` = legacy의 `job_id` → 연결 정상
- 상세보기 클릭 시 전체 legacy를 다시 읽어 상세 record를 찾음 → 변경 없음
- DetailHistoryView 코드 변경 없음

---

## 7. 회귀 확인

| 항목 | 상태 | 근거 |
|------|------|------|
| History 목록 표시 | **회귀 없음** | legacy 항상 읽으므로 기존 모든 항목 표시 |
| 삭제 즉시 반영 | **회귀 없음** | deleteHistoryRun() → legacy 삭제 → 다음 boardList에서 merge 결과에서 제거 |
| History 상세 열기 | **회귀 없음** | readHistoryRuns() 독립 재조회, job_id 연결 유지 |
| [저장] 버튼 | **회귀 없음** | DetailHistoryView 변경 없음 |
| [자동복원 후보 저장] | **회귀 없음** | restoreProfileStore 변경 없음 |
| Restore 탭 | **회귀 없음** | AutoRestoreWorkspace 변경 없음 |
| RunOCR autofill | **회귀 없음** | autofillEngine.ts 변경 없음 |
| Preview/Custom/Validation | **회귀 없음** | OcrResultPanel.tsx 변경 없음 |

---

## 8. localStorage 안전성

| 항목 | 상태 |
|------|------|
| 기존 `mysuit_ocr_history` 미변경 | ✓ |
| index read parse 실패 방어 | ✓ (try/catch → legacy fallback) |
| index 빈 배열 방어 | ✓ (length === 0 체크 → legacy fallback) |
| index item 누락 필드 방어 | ✓ (`?? run.field` fallback) |
| 기존 데이터 마이그레이션 | 없음 (금지) |

---

## 9. 남은 이슈

| 항목 | 처리 시점 |
|------|-----------|
| 삭제 시 index/detail 동기화 | HISTORY-STRUCTURE-2D |
| 상세 조회 `history_details` 우선 전환 | HISTORY-STRUCTURE-2C |
| `updatedAt` 컬럼 목록 UI 표시 | 후속 UI 개선 |
| `documentType` / `primaryCompanyName` 목록 표시 | 후속 UI 개선 |
| `hasConfirmedResult` 목록 뱃지 | 후속 UI 개선 |
| 기존 legacy 항목의 index 없음 (2A 이전 데이터) | DB 마이그레이션(3)에서 해결 |

---

## 10. 다음 단계

| 단계 | 작업 |
|------|------|
| **HISTORY-STRUCTURE-2C** | 상세 조회를 `mysuit_ocr_history_details` 우선으로 전환 |
| **HISTORY-STRUCTURE-2D** | 삭제 시 index/detail 동기화 |
| **HISTORY-STRUCTURE-3** | 전체 회귀 검증 후 DB 매핑 준비 |
