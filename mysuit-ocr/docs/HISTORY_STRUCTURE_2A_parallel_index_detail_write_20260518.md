# HISTORY-STRUCTURE-2A 병행 저장 구현 리포트

작성 일시: 2026-05-19  
도구: Claude Code (claude-sonnet-4-6)  
작업 범위: OCR 실행/저장 시 `mysuit_ocr_history_index` + `mysuit_ocr_history_details` 병행 저장 추가  
기존 기능 변경: **없음**

---

## 1. 요약

| 항목 | 결과 |
|------|------|
| 전체 판정 | **PASS** |
| 병행 저장 적용 | O — OCR 실행 성공 시 + [저장] 클릭 시 |
| 기존 기능 회귀 | 없음 |
| typecheck | **PASS** (오류 0건) |
| build | **PASS** (21개 페이지 생성) |
| 코드 수정 파일 | 3개 |
| 기존 mysuit_ocr_history 구조 변경 | **없음** |

---

## 2. 수정 파일 및 백업

### 백업 파일

| 백업 파일 | 원본 파일 |
|-----------|----------|
| `backup/historyStore_20260519_before_HISTORY_STRUCTURE_2A.ts` | `src/lib/historyStore.ts` |
| `backup/UploadWorkspace_20260519_before_HISTORY_STRUCTURE_2A.tsx` | `src/components/upload/UploadWorkspace.tsx` |
| `backup/DetailHistoryView_20260519_before_HISTORY_STRUCTURE_2A.tsx` | `src/components/history/DetailHistoryView.tsx` |

### 수정 파일 및 변경 내용

| 파일 | 변경 내용 |
|------|-----------|
| `src/lib/historyStore.ts` | 타입 4개 + 헬퍼 함수 10개 추가 (기존 코드 변경 없음) |
| `src/components/upload/UploadWorkspace.tsx` | import 추가 + `appendHistoryRun` 직후 sync 호출 12줄 추가 |
| `src/components/history/DetailHistoryView.tsx` | import 추가 + `updateHistoryRun` 직후 sync 호출 6줄 추가 |

---

## 3. 신규 localStorage key

| key | 구조 | 역할 |
|-----|------|------|
| `mysuit_ocr_history_index` | `HistoryIndexItem[]` (배열) | 목록용 경량 요약 |
| `mysuit_ocr_history_details` | `Record<historyId, HistoryDetailRecord>` (객체) | 상세용 무거운 데이터 |

기존 `mysuit_ocr_history`는 변경 없이 그대로 유지됨.

---

## 4. index 구조

### 실제 저장 예시

```json
[
  {
    "historyId": "RUN-A1B2C3D4",
    "fileName": "거래명세서_2026.pdf",
    "templateName": "거래명세서",
    "documentType": "invoice_statement",
    "createdAt": "2026-05-19 10:30:00",
    "updatedAt": "2026-05-19 10:30:00",
    "status": "success",
    "summary": {
      "fieldCount": 12,
      "tableRowCount": 13,
      "autofillStatus": "applied",
      "primaryBusinessNo": "119-10-88385",
      "primaryCompanyName": "세광전기조명"
    },
    "hasConfirmedResult": false,
    "hasRestoreProfile": false,
    "sourceFileName": "거래명세서_2026.pdf"
  }
]
```

### 필드 설명

| 필드 | 출처 | 비고 |
|------|------|------|
| `historyId` | `record.job_id` | 기존 job_id와 동일 |
| `fileName` | `record.file_name` | |
| `templateName` | `record.template_name` | |
| `documentType` | `activeTemplate.documentType` | 없으면 undefined |
| `createdAt` | `record.created_at` | |
| `updatedAt` | OCR 시점엔 createdAt과 동일. [저장] 시 갱신 | |
| `status` | `record.status` | "success" \| "fail" |
| `summary.fieldCount` | `output_fields.length` | |
| `summary.tableRowCount` | `document_fields.tableRows.length` | 없으면 undefined |
| `summary.autofillStatus` | `autofill_summary.status` | |
| `summary.primaryBusinessNo` | `autofill_summary.businessNumber` | |
| `summary.primaryCompanyName` | `output_fields`에서 "회사명"/"상호" ko 키 값 추출 | |
| `hasConfirmedResult` | OCR 시점엔 false. [저장] 시 true | |
| `hasRestoreProfile` | false (2A에서는 연결 미구현) | 2B/2C 이후 갱신 가능 |

---

## 5. detail 구조

### 실제 저장 예시

```json
{
  "RUN-A1B2C3D4": {
    "historyId": "RUN-A1B2C3D4",
    "runSnapshot": {
      "ocrFields": [
        { "name": "회사명", "en": "companyName", "ko": "회사명", "value": "세광전기조명", "confidence": 0.95 }
      ],
      "documentFields": {
        "tableRows": [
          { "품명": "LED조명 A형", "수량": "2", "단가": "15000", "금액": "30000" }
        ],
        "tableMeta": {}
      },
      "outputFieldsSnapshot": [
        { "no": 1, "en": "companyName", "ko": "회사명", "original": "세광전기조명주식회사", "modified": "", "confidence": 0.95 }
      ],
      "autofillSummary": {
        "status": "applied",
        "businessNumber": "119-10-88385",
        "filledCount": 3,
        "confirmedCount": 5
      }
    },
    "confirmedResult": null,
    "images": {
      "originalImageUrl": "data:image/jpeg;base64,...",
      "processedImageUrl": "data:image/jpeg;base64,...",
      "imageUrl": null
    }
  }
}
```

### runSnapshot 설명

| 필드 | 출처 | 비고 |
|------|------|------|
| `ocrFields` | `record.ocr_fields` | OCR 원본 필드 |
| `documentFields.tableRows` | `json.document_fields.tableRows` | ★ 거래명세서 품목표 포함 |
| `documentFields.tableMeta` | `json.document_fields.tableMeta` | |
| `outputFieldsSnapshot` | OCR 시점의 `record.output_fields` | 변경 불가 원본 스냅샷 |
| `autofillSummary` | `record.autofill_summary` | |

### confirmedResult 설명

[저장] 클릭 후 갱신:

```json
"confirmedResult": {
  "savedAt": "2026-05-19 10:45:10",
  "outputFields": [
    { "no": 1, "en": "companyName", "ko": "회사명", "original": "...", "modified": "세광전기조명", "source": "text" }
  ]
}
```

### tableRows 저장 여부

**저장됨** — `json.document_fields`에 tableRows가 있으면 `runSnapshot.documentFields.tableRows`에 저장.  
이로써 History 상세에서 거래명세서 품목표 재확인이 가능한 기반이 마련됨.  
(현재 DetailHistoryView UI는 아직 tableRows 표시 미구현. 2C 이후 UI 연결 예정.)

---

## 6. OCR 실행 후 병행 저장

### 적용 위치

`src/components/upload/UploadWorkspace.tsx` — `appendHistoryRun()` 직후

```typescript
// 기존 (유지)
const successRecord = appendHistoryRun({ ... });

// 추가
try {
  const rawDocFields = (json as Record<string, unknown>)?.document_fields as
    HistoryDetailDocumentFields | undefined;
  syncHistoryIndexAndDetailOnCreate(successRecord, {
    documentType: activeTemplate?.documentType || undefined,
    documentFields: rawDocFields,
  });
} catch (e) {
  console.warn("[history-structure] index/detail sync failed on create", e);
}
```

### 안전 설계

- 기존 `appendHistoryRun()` 실행 완료 후 sync 시도
- sync 실패 시 `console.warn`만 출력, 기존 flow 중단 없음
- `mysuit_ocr_history` 저장 결과에 영향 없음

---

## 7. [저장] 후 병행 갱신

### 적용 위치

`src/components/history/DetailHistoryView.tsx` — `updateHistoryRun()` 성공 직후

```typescript
// 기존 (유지)
const updated = updateHistoryRun(item.job_id, { output_fields: outputs });
if (updated) {
  ...
  // 추가
  try {
    syncHistoryIndexAndDetailOnSave(item.job_id, outputs);
  } catch (e) {
    console.warn("[history-structure] index/detail sync failed on save", e);
  }
  await ui.alert("저장되었습니다...");
}
```

### 갱신 항목

| 항목 | 변경 내용 |
|------|-----------|
| `index[historyId].updatedAt` | 현재 시각으로 갱신 |
| `index[historyId].hasConfirmedResult` | `true`로 갱신 |
| `detail[historyId].confirmedResult.savedAt` | 현재 시각 |
| `detail[historyId].confirmedResult.outputFields` | 저장된 output_fields |

---

## 8. 회귀 확인

| 항목 | 상태 | 근거 |
|------|------|------|
| History 목록 (`readHistoryRuns()`) | **회귀 없음** | 함수 변경 없음, 기존 key 그대로 읽음 |
| History 상세 (`DetailHistoryView`) | **회귀 없음** | import 1개 추가만, 기존 표시 로직 변경 없음 |
| [저장] 버튼 | **회귀 없음** | `updateHistoryRun` + `saveGroundTruth` 기존 그대로. sync는 성공 후 try/catch 추가만 |
| [자동복원 후보 저장] | **회귀 없음** | `restoreProfileStore` 관련 코드 변경 없음 |
| Restore 탭 | **회귀 없음** | `AutoRestoreWorkspace` 변경 없음 |
| RunOCR autofill | **회귀 없음** | `autofillEngine.ts` 변경 없음 |
| Preview/Custom/Validation | **회귀 없음** | `OcrResultPanel.tsx` 변경 없음 |
| 자동복원 조회 우선순위 | **회귀 없음** | `collectInternalAutofillCandidates` 변경 없음 |

---

## 9. localStorage 안전성

### 읽기 방어

| 함수 | parse 실패 시 |
|------|--------------|
| `readHistoryIndex()` | `[]` 반환 |
| `readHistoryDetails()` | `{}` 반환 |

### 쓰기 방어

- 모든 sync 호출은 호출처(UploadWorkspace, DetailHistoryView)에서 `try/catch`로 래핑
- sync 내부의 `writeHistoryIndex`, `writeHistoryDetails` 실패 시 exception이 위로 전파되고 호출처 catch에서 `console.warn` 후 흡수
- **기존 `mysuit_ocr_history` 쓰기(`tryWriteHistory`)는 sync와 완전히 분리됨**

### QuotaExceededError 영향

- sync 실패 → `console.warn` → 기존 history 저장 정상 완료
- 신규 key 저장 실패가 기존 History 저장 실패로 이어지지 않음

---

## 10. 남은 이슈

| 항목 | 처리 시점 |
|------|-----------|
| 삭제 동기화 (index/detail도 삭제) | HISTORY-STRUCTURE-2D |
| 목록 조회 index 우선 전환 | HISTORY-STRUCTURE-2B |
| 상세 조회 detail 우선 전환 | HISTORY-STRUCTURE-2C |
| `hasRestoreProfile` 실시간 반영 | 2B/2C 이후 |
| `output_fields.suggestions[]` 경량화 | 별도 검토 |
| DetailHistoryView에서 tableRows UI 표시 | 별도 구현 |
| groundTruth autofill 정책 확정 (I-5) | HISTORY-RESTORE-3 잔여 |

---

## 11. 다음 단계

| 단계 | 작업 | 전제 조건 |
|------|------|-----------|
| **HISTORY-STRUCTURE-2B** | 목록 조회를 `mysuit_ocr_history_index` 우선으로 전환 | 2A 완료 후 index에 충분한 데이터 쌓임 확인 |
| **HISTORY-STRUCTURE-2C** | 상세 조회를 `mysuit_ocr_history_details` 우선으로 전환 | 2B 완료 |
| **HISTORY-STRUCTURE-2D** | 삭제 시 index/detail 동기화 | 2C 완료 |
| **HISTORY-STRUCTURE-3** | DB 전환 (`historyStore.ts` 교체) | 2D 완료 + schema 확정 |
