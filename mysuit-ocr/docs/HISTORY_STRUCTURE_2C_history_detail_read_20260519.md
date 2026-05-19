# HISTORY-STRUCTURE-2C History 상세 조회 details 우선 전환 리포트

작성 일시: 2026-05-19  
도구: Claude Code (claude-sonnet-4-6)  
작업 범위: History 상세 조회를 `mysuit_ocr_history_details` 우선으로 전환, 기존 기능 완전 유지

---

## 1. 요약

| 항목 | 결과 |
|------|------|
| 전체 판정 | **PASS** |
| 상세 조회 detail 우선 전환 | O — detail 있으면 detail+index 조합, 없으면 legacy fallback |
| fallback 동작 | O — detail 없음/parse 실패/오류 → `readHistoryRuns()` fallback |
| 기존 기능 회귀 | 없음 |
| typecheck | **PASS** (오류 0건) |
| build | **PASS** (21개 페이지) |
| 기존 `mysuit_ocr_history` 구조 변경 | **없음** |
| `DetailHistoryView.tsx` 변경 | **없음** |

---

## 2. 백업 및 수정 파일

### 백업 파일

| 백업 파일 | 원본 |
|-----------|------|
| `backup/historyStore_20260519_before_HISTORY_STRUCTURE_2C.ts` | `src/lib/historyStore.ts` |
| `backup/HistoryWorkspace_20260519_before_HISTORY_STRUCTURE_2C.tsx` | `src/components/history/HistoryWorkspace.tsx` |

### 수정 파일

| 파일 | 변경 내용 |
|------|-----------|
| `src/lib/historyStore.ts` | `detailToHistoryRunRecord()` + `readHistoryDetailWithFallback()` 추가 (기존 코드 변경 없음) |
| `src/components/history/HistoryWorkspace.tsx` | import 정리 + 상세보기 클릭 핸들러 1줄 변경 |

---

## 3. 변경 내용

### 추가된 함수 (`src/lib/historyStore.ts`)

#### `detailToHistoryRunRecord(detail, meta?)` (exported)

`HistoryDetailRecord` → `HistoryRunRecord` 변환.

```typescript
// output_fields 우선순위:
const outputFields =
  detail.confirmedResult?.outputFields    // [저장]된 최신 채택값 (1순위)
  ?? detail.runSnapshot?.outputFieldsSnapshot  // OCR 실행 시점 원본 (2순위)
  ?? [];                                       // 없으면 빈 배열
```

meta 파라미터(index 데이터)로 `file_name`, `template_name`, `created_at`, `status` 보강.

#### `readHistoryDetailWithFallback(historyId)` (exported)

```
1. readHistoryDetails()[historyId] 시도
   ├─ detail 있고 historyId 정상 → detail + index 메타 조합 반환
   │    (heavy legacy 전체 로드 없이 처리)
   └─ detail 없음 / parse 실패 → catch 후 legacy fallback
2. Legacy fallback: readHistoryRuns().find(job_id === historyId)
```

### HistoryWorkspace.tsx 변경

```typescript
// 기존 import
import { readHistoryRuns, readHistoryListWithFallback, ... }

// 변경 (readHistoryRuns 제거, readHistoryDetailWithFallback 추가)
import { readHistoryListWithFallback, readHistoryDetailWithFallback, ... }

// 기존 상세보기 클릭
onClick={() => {
  const all = readHistoryRuns();
  const full = all.find((r) => r.job_id === row.job_id) ?? null;
  setDetailRecord(full);
}}

// 변경 (1줄로 단순화)
onClick={() => {
  setDetailRecord(readHistoryDetailWithFallback(row.job_id));
}}
```

`DetailHistoryView.tsx`는 `item` prop을 그대로 사용하므로 **변경 없음**.

---

## 4. 상세 조회 우선순위

```
1순위: mysuit_ocr_history_details[historyId]
  ├─ 있으면: detail + mysuit_ocr_history_index[historyId] 메타 조합
  └─ detail만으로 HistoryRunRecord 완성 (heavy legacy 미로드)

2순위: mysuit_ocr_history (readHistoryRuns().find())
  └─ detail 없음 / parse 실패 / 오류 시 fallback
```

**성능 특성**:
- detail 있음: `readHistoryDetails()` + `readHistoryIndex()` 조회 (경량)
- detail 없음: `readHistoryRuns()` 조회 (heavy, 기존 동작과 동일)

---

## 5. output_fields 우선순위

| 우선순위 | 소스 | 의미 |
|---------|------|------|
| 1순위 | `detail.confirmedResult.outputFields` | [저장] 클릭으로 저장된 최신 채택값 |
| 2순위 | `detail.runSnapshot.outputFieldsSnapshot` | OCR 실행 시점 원본 스냅샷 |
| 3순위 | `readHistoryRuns().output_fields` (fallback 시) | legacy 기반 output_fields |
| 최종 | `[]` | 없으면 빈 배열 |

→ `DetailHistoryView`의 `useEffect`에서 `setOutputs(item?.output_fields ? [...item.output_fields] : [])` 로직이 이 순서대로 가장 최신 값을 사용하게 됨.

---

## 6. fallback 조건

| 조건 | 결과 |
|------|------|
| `mysuit_ocr_history_details` key 없음 | legacy fallback |
| details parse 실패 | legacy fallback (catch) |
| details가 객체가 아님 | legacy fallback |
| 해당 `historyId` detail 없음 | legacy fallback |
| `detail.historyId` 없음 (corrupted) | legacy fallback |
| 변환 중 예외 | legacy fallback (catch) |

---

## 7. tableRows 보존 확인

`detail.runSnapshot.documentFields.tableRows`는 `detailToHistoryRunRecord()` 변환에서 직접 포함되지 않지만:

- `HistoryDetailRecord` 구조에서 `runSnapshot.documentFields`가 유지됨
- `detailToHistoryRunRecord()`는 `ocr_fields`, `output_fields`, `autofill_summary`, `images`를 추출
- `documentFields.tableRows`는 `HistoryRunRecord`에 없는 필드이므로 전달하지 않음 (HistoryRunRecord에 해당 필드 없음)
- **localStorage의 `mysuit_ocr_history_details` 데이터 자체는 유실 없음** — `writeHistoryDetails()`에서 그대로 보존

→ History 상세 UI에서 tableRows를 표시하려면 `DetailHistoryView`를 별도 수정해야 함 (이번 작업 범위 아님, 후속 작업).

---

## 8. 회귀 확인

| 항목 | 상태 | 근거 |
|------|------|------|
| History 목록 | **회귀 없음** | `readHistoryListWithFallback()` 그대로, import에서 `readHistoryRuns` 제거만 |
| History 상세 열기 (신규 — detail 있음) | **회귀 없음** | `readHistoryDetailWithFallback` → detail + index 조합 → 완전한 record |
| History 상세 열기 (구 — detail 없음) | **회귀 없음** | legacy fallback → `readHistoryRuns().find()` 기존 동작 |
| [저장] 버튼 | **회귀 없음** | `DetailHistoryView` 변경 없음, `updateHistoryRun` + `syncHistoryIndexAndDetailOnSave` 그대로 |
| [저장] 후 재조회 | **정상** | `onSaved(updated)` → legacy record로 detail 갱신. 다음 열기 때는 `confirmedResult` 우선 |
| [자동복원 후보 저장] | **회귀 없음** | `restoreProfileStore` 변경 없음 |
| Restore 탭 | **회귀 없음** | `AutoRestoreWorkspace` 변경 없음 |
| RunOCR autofill | **회귀 없음** | `autofillEngine.ts` 변경 없음 |
| Preview/Custom/Validation | **회귀 없음** | `OcrResultPanel.tsx` 변경 없음 |

---

## 9. localStorage 안전성

| 항목 | 상태 |
|------|------|
| 기존 `mysuit_ocr_history` 미변경 | ✓ |
| details read parse 실패 방어 | ✓ (try/catch → legacy fallback) |
| detail 없는 historyId 방어 | ✓ (`detail?.historyId` 체크) |
| index read 실패 시 meta=undefined | ✓ (`meta` optional, `??` 기본값) |
| 기존 데이터 마이그레이션 | 없음 (금지) |

---

## 10. 남은 이슈

| 항목 | 처리 시점 |
|------|-----------|
| 삭제 시 index/detail 동기화 | HISTORY-STRUCTURE-2D |
| History 상세 UI에서 `tableRows` 렌더링 | 별도 UI 작업 |
| `hasRestoreProfile` 실시간 반영 | 별도 작업 |
| 2A 이전 entry detail 없음 | DB 마이그레이션(3) |
| `onSaved` 콜백 후 detail 기반 reopen | 현재는 legacy record로 재설정. 2D 이후 개선 가능 |

---

## 11. 다음 단계

| 단계 | 작업 |
|------|------|
| **HISTORY-STRUCTURE-2D** | 삭제 시 index/detail 동기화 |
| **HISTORY-STRUCTURE-3** | 전체 회귀 검증 후 DB 매핑 준비 |
