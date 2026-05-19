# HISTORY-DETAIL-1: History 상세 tableRows 렌더링 연결 리포트

- 생성일: 2026-05-19
- 작업명: HISTORY-DETAIL-1
- 담당 모델: Claude Sonnet 4.6 (claude-sonnet-4-6)
- 작업 성격: 기능 추가 (History 상세 품목표 표시)
- 코드 수정: **있음** (historyStore.ts, DetailHistoryView.tsx)

---

## 1. 요약

| 항목 | 결과 |
|------|------|
| 전체 상태 | **PASS** |
| History 상세 tableRows 표시 | **구현 완료** |
| 기존 기능 회귀 | **없음** |
| npm run typecheck | **PASS** (오류 0건) |
| npm run build | **PASS** (ESLint 경고 1건 — 기존과 동일, 무관) |
| /history 페이지 JS 크기 | 5.71 kB → 6.43 kB (품목표 렌더링 코드 추가로 정상 증가) |

---

## 2. 백업/수정 파일

### 백업 파일

| 파일 | 백업 경로 |
|------|-----------|
| src/lib/historyStore.ts | backup/historyStore_20260519_before_HISTORY_DETAIL_1.ts |
| src/components/history/DetailHistoryView.tsx | backup/DetailHistoryView_20260519_before_HISTORY_DETAIL_1.tsx |

### 수정 파일

| 파일 | 변경 내용 |
|------|-----------|
| `src/lib/historyStore.ts` | HistoryRunRecord 타입에 `document_fields` 추가, detailToHistoryRunRecord() 반환에 포함 |
| `src/components/history/DetailHistoryView.tsx` | import 추가, 스타일/헬퍼 추가, useMemo 추가, 품목표 섹션 렌더링 추가, handleSave document_fields 보존 |

### 수정하지 않은 파일 (원칙 준수)

- `src/lib/invoiceTableDisplay.ts` — 재사용만, 수정 없음
- `src/components/upload/OcrResultPanel.tsx` — 수정 없음
- `src/components/history/HistoryWorkspace.tsx` — 수정 없음
- `src/lib/restoreProfileStore.ts` — 수정 없음
- `src/lib/autofillEngine.ts` — 수정 없음
- OCR/parser 파일 전체 — 수정 없음

---

## 3. tableRows 데이터 경로

### localStorage → HistoryRunRecord 전달 경로

```
mysuit_ocr_history_details[historyId]
  └─ .runSnapshot.documentFields.tableRows   ← HISTORY-STRUCTURE-2A에서 저장됨
  └─ .runSnapshot.documentFields.tableMeta   ← 동시 저장

       ↓ readHistoryDetailWithFallback(historyId)

detailToHistoryRunRecord(detail, meta)
  └─ 신규: document_fields: detail.runSnapshot?.documentFields   ← HISTORY-DETAIL-1 추가

       ↓ returns HistoryRunRecord

HistoryRunRecord.document_fields   ← 신규 optional 필드
  └─ .tableRows?: unknown[]
  └─ .tableMeta?: Record<string, unknown>
```

### HistoryRunRecord 타입 변경

```typescript
// historyStore.ts — HistoryRunRecord 타입 (추가된 필드)
document_fields?: HistoryDetailDocumentFields; // HISTORY-DETAIL-1
```

`HistoryDetailDocumentFields`는 기존에 이미 정의된 타입:
```typescript
export type HistoryDetailDocumentFields = {
  tableRows?: unknown[];
  tableMeta?: Record<string, unknown>;
};
```

### legacy fallback 안전성

- `readHistoryRuns()` 반환 record → `document_fields` 필드 없음 (undefined)
- optional 필드이므로 타입 에러 없음
- 렌더링 조건: `tableRows && tableRows.length > 0 && tableDisplayCols && tableDisplayCols.length > 0`
- legacy history에서는 모두 false → 품목표 섹션 미표시 → 기존 UI 그대로

### DetailHistoryView 추출 경로

```typescript
// useMemo — tableRows 추출
const tableRows = useMemo((): Record<string, unknown>[] | null => {
  const df = item?.document_fields;
  if (!df) return null;
  const rows = df.tableRows;
  if (!Array.isArray(rows) || rows.length === 0) return null;
  return rows as Record<string, unknown>[];
}, [item]);

// useMemo — tableMeta
const tableMeta = useMemo(
  () => (item?.document_fields?.tableMeta ?? null) as Record<string, unknown> | null,
  [item],
);

// useMemo — 표시 컬럼 결정 (buildInvoicePreviewCols 재사용)
const tableDisplayCols = useMemo(
  () => (tableRows ? buildInvoicePreviewCols(tableMeta, tableRows) : null),
  [tableRows, tableMeta],
);
```

---

## 4. 렌더링 방식

### 사용한 helper

| helper | 출처 | 용도 |
|--------|------|------|
| `buildInvoicePreviewCols(tableMeta, rows)` | `src/lib/invoiceTableDisplay.ts` | 표시 컬럼 결정 (expectedColumnKeys → columns → allowlist + hasValue 필터) |
| `normalizeTableCell(value)` | `src/lib/invoiceTableDisplay.ts` | 셀 값 정규화 (null/dash/zero-width 처리) |

### 컬럼 결정 방식

Preview/Custom/Validation과 동일한 `buildInvoicePreviewCols` 사용:
1. `tableMeta.expectedColumnKeys` → 순서·라벨 참고 + hasValue 필터
2. `tableMeta.columns` → 순서·라벨 참고 + hasValue 필터
3. `INVOICE_TABLE_COL_PRIORITY` allowlist + hasValue fallback
4. 후처리: itemCode 노이즈 제거, lot/mfg 중복 제거, serialNo 중복 제거
5. `rowIndex` 실제 값이 있으면 맨 앞에 추가

### 헤더 표시 방식

Preview/Custom/Validation과 동일한 2줄 표시:
```
품목명          ← labelKo (한글)
(itemName)      ← key (monospace, opacity 0.5, 작은 글씨)
```
- `col.labelKo === col.key`이면 key 줄 생략
- `title` 속성으로 전체 key 확인 가능

### 컬럼 너비 및 정렬

| 컬럼 유형 | 너비 | 정렬 |
|-----------|------|------|
| rowIndex/NO 계열 | 48px | center |
| quantity | 60px | right |
| 금액/단가 계열 | 88px | right |
| 코드 계열 | 92px | left |
| itemName/manufacturer | auto | left |
| 기타 | 78px | left |

### tableRows 없는 경우 처리

```tsx
{tableRows && tableRows.length > 0 && tableDisplayCols && tableDisplayCols.length > 0 && (
  /* 품목표 섹션 */
)}
```

- tableRows = null (document_fields 없음) → 섹션 미표시
- tableRows = [] (빈 배열) → 섹션 미표시
- tableDisplayCols = [] (모든 컬럼 필터됨) → 섹션 미표시
- 앱 오류 없음

### 표시 위치

"출력 필드" 섹션과 "OCR 데이터" 섹션 사이에 별도 섹션으로 표시.

---

## 5. 화면 결과

### 거래명세서 History 상세

정적 코드 분석 기준:

- `appendHistoryRun()` + `syncHistoryIndexAndDetailOnCreate()` 호출 시점에 `json.document_fields`에서 `rawDocFields` 추출 (UploadWorkspace.tsx:1025-1030)
- `rawDocFields.tableRows`가 `detail.runSnapshot.documentFields.tableRows`에 저장됨
- `readHistoryDetailWithFallback(historyId)` 호출 시 `detailToHistoryRunRecord()` 경로를 통해 `document_fields.tableRows` 포함된 `HistoryRunRecord` 반환
- `DetailHistoryView`에서 `item.document_fields.tableRows` 추출 → `buildInvoicePreviewCols` → 품목표 렌더링

**기대 표시 예시 (2.pdf 거래명세서):**

```
품목표                                  표 데이터 · 13행
────────────────────────────────────────────────────────
번호     품목코드   품명        수량   공급단가   공급금액
(rowIndex)(itemCode)(itemName)(quantity)(supplyUnitPrice)(supplyAmount)
  1      A001     볼펜         10     500      5,000
  2      B002     노트         20     1,500    30,000
  ...
```

**기대 표시 예시 (1.jpg 의료기기 명세서):**

```
품목표                                  표 데이터 · N행
────────────────────────────────────────────────────────
품목명     규격     제조번호   유효기간   수량   단가    금액
(itemName)(spec)(manufacturingNo)(expiryDate)(quantity)(unitPrice)(amount)
```

### tableRows 없는 History 상세

- `document_fields` 필드 없음 → `tableRows = null` → 품목표 섹션 미표시
- "출력 필드" + "OCR 데이터" 섹션만 표시 (기존과 동일)

### detail 없는 legacy History

- `readHistoryRuns().find()` 경로 (legacy fallback) → `document_fields` 없음
- 품목표 섹션 미표시
- 기존 UI 그대로 동작

---

## 6. 회귀 확인

| 기능 | 변경 전 | 변경 후 | 회귀 |
|------|---------|---------|------|
| History 목록 | readHistoryListWithFallback() | 동일 | 없음 |
| History 상세 열기 | readHistoryDetailWithFallback() | 동일 (document_fields 추가) | 없음 |
| History 상세 렌더링 | 출력 필드 + OCR 데이터 | 출력 필드 + 품목표(선택) + OCR 데이터 | 없음 |
| [저장] 동작 | updateHistoryRun → onSaved(updated) | updateHistoryRun → onSaved({...updated, document_fields}) | 없음 |
| [저장] 후 document_fields | 저장 후 tableRows 사라짐 | 저장 후 tableRows 유지됨 | 개선 |
| [자동복원 후보 저장] | handleSaveRestoreProfile → writeRestoreProfiles | 동일 | 없음 |
| History 삭제 | deleteHistoryRun + syncOnDelete | 동일 | 없음 |
| Restore 탭 | readRestoreProfiles() | 동일 | 없음 |
| RunOCR 실행 | appendHistoryRun + syncOnCreate | 동일 | 없음 |
| Preview 품목표 | buildInvoicePreviewCols 사용 | 동일 (파일 미수정) | 없음 |
| Custom 품목표 | buildInvoicePreviewCols 사용 | 동일 (파일 미수정) | 없음 |
| Validation 품목표 | buildInvoicePreviewCols 사용 | 동일 (파일 미수정) | 없음 |
| localStorage 구조 | 불변 | 불변 | 없음 |

---

## 7. 남은 이슈

### ISSUE-D1: table cell 편집 기능 없음 (의도된 제외)
- 이번 작업은 읽기 전용 표시
- 품목표 셀 수정은 후속 작업으로 분리

### ISSUE-D2: History 2A 이전 거래명세서 → tableRows 없음
- HISTORY-STRUCTURE-2A (syncHistoryIndexAndDetailOnCreate) 이전에 실행된 OCR은 detail이 없거나 documentFields.tableRows가 없음
- 해당 항목은 legacy fallback으로 열리며 품목표 섹션 미표시 (정상 동작)
- 다시 OCR 실행하면 신규 detail에 tableRows 포함됨

### ISSUE-D3: 거래명세서 외 문서의 tableRows
- documentType 제한 없이 tableRows 존재 여부 기준으로 표시 (요구사항 준수)
- 현재 tableRows는 invoice_statement에서만 생성됨 → 실질적으로 거래명세서만 표시
- 향후 다른 문서에서도 tableRows 생성 시 자동 표시됨

### ISSUE-D4: 긴 표 UI 개선 여부
- maxHeight: 220px 내 수직 스크롤, 수평 스크롤 허용
- 행이 매우 많으면 스크롤 필요 → 기본 충분
- 후속 작업에서 pagination 또는 collapse 가능

---

## 8. 다음 단계

| 순서 | 작업명 | 내용 |
|------|--------|------|
| 1 | **DB-2** | PostgreSQL schema 작성 (이전 HISTORY-STRUCTURE-3 리포트 참조) |
| 2 | **HISTORY-STRUCTURE-4** | localStorage QuotaExceededError 처리 강화 |
| 3 | **HISTORY-RESTORE-5** | sourceHistoryId dangling 경고 UI |

---

## 9. 변경 파일 요약

```
src/lib/historyStore.ts
  HistoryRunRecord 타입: document_fields?: HistoryDetailDocumentFields 추가
  detailToHistoryRunRecord(): document_fields: detail.runSnapshot?.documentFields 추가

src/components/history/DetailHistoryView.tsx
  import: buildInvoicePreviewCols, normalizeTableCell from invoiceTableDisplay
  스타일: _TBL_IDX_KEYS, _TBL_NUM_KEYS, _TBL_CODE_KEYS, _TBL_WIDE_KEYS
  헬퍼: tblColWidth(), tblDataAlign()
  스타일 상수: tblThStyle, tblTdStyle
  useMemo: tableRows, tableMeta, tableDisplayCols
  handleSave: onSaved({...updated, document_fields: item.document_fields})
  JSX: 품목표 섹션 (출력 필드와 OCR 데이터 사이)
```

---

*리포트 생성: HISTORY-DETAIL-1 / Claude Sonnet 4.6 / 2026-05-19*
