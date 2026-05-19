# HISTORY-STRUCTURE-2D History 삭제 시 index/detail 동기화 리포트

작성 일시: 2026-05-19  
도구: Claude Code (claude-sonnet-4-6)  
작업 범위: History 삭제 시 `mysuit_ocr_history_index`와 `mysuit_ocr_history_details`도 함께 정리

---

## 1. 요약

| 항목 | 결과 |
|------|------|
| 전체 판정 | **PASS** |
| 삭제 동기화 적용 | O — 단건 삭제 + clear 전체 삭제 |
| 기존 기능 회귀 | 없음 |
| typecheck | **PASS** (오류 0건) |
| build | **PASS** (21개 페이지) |
| 기존 `mysuit_ocr_history` 동작 변경 | **없음** |
| restore profile 보존 | **O** — 삭제 시 미영향 |

---

## 2. 백업 및 수정 파일

### 백업 파일

| 백업 파일 | 원본 |
|-----------|------|
| `backup/historyStore_20260519_before_HISTORY_STRUCTURE_2D.ts` | `src/lib/historyStore.ts` |

`HistoryWorkspace.tsx`는 변경 없으므로 백업 없음.

### 수정 파일

| 파일 | 변경 내용 |
|------|-----------|
| `src/lib/historyStore.ts` | `syncHistoryIndexAndDetailOnDelete()` 추가, `deleteHistoryRun()` + `clearHistoryRuns()` 보강 |

---

## 3. 변경 내용

### 추가된 private 함수: `syncHistoryIndexAndDetailOnDelete(historyId)`

```typescript
function syncHistoryIndexAndDetailOnDelete(historyId: string): void {
  // index에서 해당 historyId 항목 제거
  try {
    const index = readHistoryIndex();
    const filtered = index.filter((item) => item.historyId !== historyId);
    if (filtered.length !== index.length) writeHistoryIndex(filtered);
  } catch (e) { console.warn(...); }

  // detail에서 해당 historyId 키 제거
  try {
    const details = readHistoryDetails();
    if (Object.prototype.hasOwnProperty.call(details, historyId)) {
      const rest = Object.fromEntries(
        Object.entries(details).filter(([k]) => k !== historyId),
      ) as Record<string, HistoryDetailRecord>;
      writeHistoryDetails(rest);
    }
  } catch (e) { console.warn(...); }
}
```

### 수정된 `deleteHistoryRun(jobId)`

```typescript
// 기존: try { tryWriteHistory(next); return true; } catch { return false; }
// 변경: legacy 삭제와 sync를 분리

try {
  tryWriteHistory(next);    // legacy 삭제
} catch (e) {
  console.warn(...);
  return false;             // legacy 실패 → false (기존과 동일)
}
// legacy 성공 후에만 sync 실행 (실패해도 true 반환 유지)
syncHistoryIndexAndDetailOnDelete(jobId);
return true;
```

### 수정된 `clearHistoryRuns()`

```typescript
window.localStorage.removeItem(STORAGE_KEY);          // 기존
try { window.localStorage.removeItem(HISTORY_INDEX_KEY); } catch { }   // 추가
try { window.localStorage.removeItem(HISTORY_DETAILS_KEY); } catch { } // 추가
```

### HistoryWorkspace.tsx 변경 없음

`deleteHistoryRun()` 자체를 수정했으므로 유일한 호출부(HistoryWorkspace.tsx:295)가 자동으로 동기화 동작을 얻음.

---

## 4. 삭제 동기화 정책

| 저장소 | 단건 삭제 | clear 전체 삭제 | 비고 |
|--------|----------|----------------|------|
| `mysuit_ocr_history` | O (기존 동작 유지) | O (기존 동작 유지) | |
| `mysuit_ocr_history_index` | O (historyId 항목 제거) | O (key 전체 제거) | 실패 시 console.warn |
| `mysuit_ocr_history_details` | O (historyId 키 제거) | O (key 전체 제거) | 실패 시 console.warn |
| `mysuit_ocr_restore_profiles` | **X (보존)** | **X (보존)** | 정책: 후보는 독립 유지 |

---

## 5. 단건 삭제 검증 (코드 분석 기준)

### 삭제 전 상태 (예)
```
mysuit_ocr_history:         [..., { job_id: "RUN-ABCD", ... }, ...]
mysuit_ocr_history_index:   [..., { historyId: "RUN-ABCD", ... }, ...]
mysuit_ocr_history_details: { "RUN-ABCD": { ... }, ... }
```

### 삭제 후 상태
```
mysuit_ocr_history:         [... (RUN-ABCD 제거)]
mysuit_ocr_history_index:   [... (RUN-ABCD 제거)]
mysuit_ocr_history_details: { ... (RUN-ABCD 키 제거) }
```

### 목록 반영
- 2B의 merge 전략: legacy base에서 RUN-ABCD 사라짐 → `boardList()` 호출 후 목록에서 제거 ✓

### 상세 조회
- `readHistoryDetailWithFallback("RUN-ABCD")`:
  1. `readHistoryDetails()["RUN-ABCD"]` → 없음 (삭제됨)
  2. `readHistoryRuns().find(job_id === "RUN-ABCD")` → 없음 (삭제됨)
  3. → `null` 반환 → `setDetailRecord(null)` → 목록으로 복귀 ✓

---

## 6. 구 데이터 삭제 검증 (legacy-only 항목)

`mysuit_ocr_history_index`와 `mysuit_ocr_history_details`에 없는 구 항목 삭제:

1. legacy 삭제 성공 → `syncHistoryIndexAndDetailOnDelete` 호출
2. index 조회 → 해당 historyId 없음 → `filtered.length === index.length` → write 스킵
3. detail 조회 → `hasOwnProperty` 없음 → write 스킵
4. 두 경우 모두 no-op, no error → `true` 반환 ✓

---

## 7. Restore profile 영향 확인

| 항목 | 결과 |
|------|------|
| `mysuit_ocr_restore_profiles` 삭제 여부 | **없음** |
| sourceHistoryId dangling reference | 잔존 (의도적) |
| 이유 | 복원 후보는 업체 정보 마스터 데이터. 원본 History 없어도 autofill에 사용 가능. |
| 후속 처리 | Restore 상세에서 sourceHistoryId가 legacy/detail에 없으면 "원본 History 없음" 경고 표시 (별도 작업) |

---

## 8. 회귀 확인

| 항목 | 상태 | 근거 |
|------|------|------|
| History 목록 삭제 | **회귀 없음** | `deleteHistoryRun` 반환값 동일, `boardList()` 호출 유지 |
| 삭제 취소 | **회귀 없음** | `if (!ok) return` 시 `deleteHistoryRun` 미호출 → sync 미실행 |
| History 삭제 실패 시 | **회귀 없음** | legacy `tryWriteHistory` 실패 시 `return false` (sync 미실행) |
| History 목록 표시 | **회귀 없음** | `readHistoryListWithFallback()` 변경 없음 |
| History 상세 열기 | **회귀 없음** | `readHistoryDetailWithFallback()` 변경 없음 |
| [저장] 버튼 | **회귀 없음** | `updateHistoryRun` + `syncHistoryIndexAndDetailOnSave` 변경 없음 |
| [자동복원 후보 저장] | **회귀 없음** | `restoreProfileStore` 변경 없음 |
| Restore 탭 | **회귀 없음** | `AutoRestoreWorkspace` 변경 없음 |
| RunOCR autofill | **회귀 없음** | `autofillEngine.ts` 변경 없음 |
| Preview/Custom/Validation | **회귀 없음** | `OcrResultPanel.tsx` 변경 없음 |

---

## 9. localStorage 안전성

| 시나리오 | 동작 |
|---------|------|
| index key 없음 | `readHistoryIndex()` → `[]` → filter no-op → `return` ✓ |
| details key 없음 | `readHistoryDetails()` → `{}` → `hasOwnProperty` false → no-op ✓ |
| index parse 실패 | try/catch → `console.warn` → details 단계 진행 ✓ |
| details parse 실패 | try/catch → `console.warn` → 종료 ✓ |
| index write 실패 | try/catch → `console.warn` → details 단계 진행 ✓ |
| details write 실패 | try/catch → `console.warn` → 종료 ✓ |
| 모든 sync 실패 | legacy 삭제는 이미 성공 → `true` 반환 유지 ✓ |

---

## 10. 남은 이슈

| 항목 | 처리 시점 |
|------|-----------|
| Restore 상세 sourceHistoryId dangling 경고 표시 | 별도 UI 작업 |
| History 상세 tableRows UI 연결 | 별도 UI 작업 |
| `clearHistoryRuns()` 호출처 없음 — 전체 삭제 UI 필요 여부 | 후속 기획 |
| 2A 이전 legacy-only 항목 index/detail 이전 | DB 마이그레이션(3) |

---

## 11. 다음 단계

| 단계 | 작업 |
|------|------|
| **HISTORY-STRUCTURE-3** | 전체 E2E 회귀 검증 + DB 매핑 정리 문서화 |
| **DB-2** | `ocr_runs`, `ocr_run_results`, `ocr_restore_profiles` schema 반영 |
| I-5 | groundTruth autofill 정책 확정 |
