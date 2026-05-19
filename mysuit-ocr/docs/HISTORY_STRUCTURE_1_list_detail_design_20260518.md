# HISTORY-STRUCTURE-1 History list/detail 분리 설계 리포트

작성 일시: 2026-05-19  
작성 방법: 코드 정적 분석  
도구: Claude Code (claude-sonnet-4-6)  
분석 범위: HISTORY-RESTORE-2A/2B/2C/3 완료 상태 기준

---

## 1. 요약

### 현재 History 구조 한 줄 요약

`mysuit_ocr_history` 하나의 배열에 목록 표시용 경량 필드(6개)와 상세보기용 중량 데이터(`ocr_fields`, `output_fields`, 이미지 URL, `autofill_summary`)가 혼재하여 목록 조회 시 전체 데이터를 로드한다.

### 왜 list/detail 분리가 필요한가

| 문제 | 영향 |
|------|------|
| 목록 조회 시 `ocr_fields` + `output_fields` (suggestions 포함) + 이미지 URL 전부 로드 | localStorage 읽기 비용, 목록 렌더링 지연 가능 |
| `output_fields.suggestions[]`가 레코드당 수 KB 수준 | MAX_RECORDS=50 기준 최대 ~250KB 이상 |
| `updated_at` 필드 없음 | [저장] 시점 추적 불가 |
| `documentType` 필드 없음 | 문서 유형별 목록 필터 불가 |
| `primaryBusinessNo` / `primaryCompanyName` 없음 | 목록에서 사업자/업체명 확인 불가 |
| `document_fields.tableRows` 미저장 | History 상세에서 품목표 재확인 불가 |
| `hasRestoreProfile` 없음 | 목록에서 복원 후보 유무 표시 불가 |

### 당장 구현해도 되는가

**설계 확정 → HISTORY-STRUCTURE-2A 병행 저장 구현** 순서로 진행 권장.  
현재 mysuit_ocr_history는 수정 없이 유지. 신규 저장 시에만 index/detail을 병행 추가.

### 추천 진행 순서

```
HISTORY-STRUCTURE-1 (이번)    설계/분석 완료
HISTORY-STRUCTURE-2A          OCR 실행 시 index+detail 병행 저장 추가
HISTORY-STRUCTURE-2B          목록 조회를 index 우선으로 전환
HISTORY-STRUCTURE-2C          상세 조회를 detail 우선으로 전환
HISTORY-STRUCTURE-2D          index/detail 동기화 검증 + [저장] 버튼 연동
HISTORY-STRUCTURE-3           DB 전환 시 historyStore.ts 교체
```

---

## 2. 현재 mysuit_ocr_history 구조

### 2-1. HistoryRunRecord 전체 필드

```typescript
// src/lib/historyStore.ts
HistoryRunRecord = {
  // ── 식별자 ──
  job_id: string;                          // "RUN-XXXXXXXX"

  // ── 목록 표시용 경량 필드 (6개) ──
  file_name: string;
  template_name: string | null;
  processing_time: number;
  created_at: string;                      // "YYYY-MM-DD HH:mm:ss"
  status: "success" | "fail";

  // ── 이미지 (상세보기용, 무거움) ──
  image_url?: string;                      // legacy (이전 호환)
  original_image_url?: string | null;      // 전처리 전 원본
  processed_image_url?: string | null;     // 전처리 후
  image_storage_mode?: "legacy" | "url";

  // ── OCR 원본 데이터 (상세보기용, 중간 무게) ──
  ocr_fields?: HistoryOcrField[];          // { name, en, ko, field_type, value, confidence, bbox }

  // ── 출력 필드 + autofill 결과 (상세보기용, 매우 무거움) ──
  output_fields?: HistoryOutputField[];    // 레코드당 수 KB (suggestions 포함)
  autofill_summary?: HistoryAutofillRunSummary;
}
```

### 2-2. 혼재 데이터 분류

| 그룹 | 필드 | 목록 필요 | 상세 필요 | 자동복원 필요 |
|------|------|----------|----------|--------------|
| 식별자 | job_id | O | O | O (sourceHistoryId) |
| 목록용 | file_name, template_name, processing_time, created_at, status | O | O | X |
| 이미지 | image_url, original_image_url, processed_image_url, image_storage_mode | X | O | X |
| OCR 원본 | ocr_fields | X | O | X |
| 출력 필드 | output_fields | **X** (현재 목록에서 미참조) | O | O (history fallback) |
| 자동복원 요약 | autofill_summary | △ (status만 목록에 유용) | O | O (businessNumber) |

> **핵심**: `output_fields`와 `ocr_fields`는 목록에서 실제로 참조되지 않으나, 배열 전체가 메모리에 로드된다.

### 2-3. 현재 누락 필드 (목록/상세에 유용하나 미저장)

| 필드 | 누락 사유 | 영향 |
|------|-----------|------|
| `updated_at` | 설계 미포함 | [저장] 시점 추적 불가 |
| `documentType` | 설계 미포함 | 문서 유형 필터 불가 |
| `primaryBusinessNo` | 미계산 | 목록 업체 확인 불가 |
| `primaryCompanyName` | 미계산 | 목록 회사명 표시 불가 |
| `hasRestoreProfile` | 별도 저장소 | 목록 복원 후보 뱃지 불가 |
| `document_fields.tableRows` | 미저장 ★ | History 상세에서 품목표 확인 불가 |
| `warningCount / missingCount` | 미집계 | 목록 상태 요약 불가 |

> **★ 중요**: `document_fields.tableRows` (invoice 품목표)는 현재 RunOCR 결과(OcrResultPanel)에서만 표시되고 History에는 저장되지 않는다. History 상세는 flat output_fields 테이블만 표시한다.

### 2-4. output_fields 내부 구조 (무게 원인)

```typescript
HistoryOutputField = {
  no, en, ko,
  original: string,   // OCR 원본값
  modified: string,   // 사용자 수정값
  confidence: number,
  source: "ocr"|"biz"|"gt"|"text",
  applied: string,    // autofill 적용값
  autofillAction: "filled"|"corrected"|"confirmed"|"none",
  suggestions: [{     // ← 가장 무거운 부분
    source, value, label, reason, confidence,
    sourceType, createdAt, updatedAt, templateName, fileName, hitCount
  }]
}
```

suggestions 배열은 autofill 후보 목록으로, 필드당 다수 항목이 들어갈 수 있다. History fallback 후 다음 OCR에서는 불필요한 데이터이나 현재 전부 저장된다.

---

## 3. 현재 History 목록 사용 필드

### 3-1. boardList() 실제 매핑 (HistoryWorkspace.tsx:47-54)

```typescript
const mapped: HistoryRow[] = list.map((r) => ({
  job_id: r.job_id,
  file_name: r.file_name,
  template_name: r.template_name,
  processing_time: r.processing_time,
  created_at: r.created_at,
  status: r.status,
}));
```

### 3-2. 목록 사용 필드 분석

| 필드 | 현재 용도 | index로 이동 | 비고 |
|------|----------|-------------|------|
| job_id | PK, 상세보기 링크 | O | |
| file_name | 목록 표시 | O | |
| template_name | 목록 표시, 필터 | O | |
| processing_time | 목록 미표시 (현재) | O | 이후 표시 예정 |
| created_at | 목록 표시, 필터 | O | |
| status | 목록 표시, 필터 | O | |
| ocr_fields | **미사용** | 삭제 대상 (detail로) | 목록 로드 시 불필요하게 메모리 점유 |
| output_fields | **미사용** | 삭제 대상 (detail로) | 가장 무거운 항목 |
| autofill_summary | **미사용** (status만 유용) | autofill_status 추출 후 index에 | |
| image URLs | **미사용** | 삭제 대상 (detail로) | |

### 3-3. 목록에 추가하면 유용한 신규 필드

| 필드 | 도출 방법 | 현재 가능 여부 |
|------|-----------|--------------|
| `updated_at` | [저장] 시 갱신 | 불가 (필드 없음) |
| `documentType` | template 메타에서 | 불가 (미저장) |
| `primaryBusinessNo` | autofill_summary.businessNumber | 가능 (값 있으면) |
| `primaryCompanyName` | output_fields 파싱 | 가능하나 비용 높음 |
| `autofill_status` | autofill_summary.status | 가능 |
| `hasRestoreProfile` | restoreProfileStore 조회 | 가능 (런타임) |
| `fieldCount` | output_fields.length | 가능 |
| `warningCount` | validation 결과 | 현재 미저장 |

---

## 4. 현재 History 상세 사용 필드

### 4-1. DetailHistoryView가 실제 참조하는 필드

| 필드 | 용도 | detail로 이동 | 비고 |
|------|------|-------------|------|
| job_id | updateHistoryRun() 키 | O | |
| file_name | 헤더 표시 | O | index에도 유지 |
| template_name | 헤더 표시, groundTruth 조회 | O | index에도 유지 |
| created_at | 헤더 표시 | O | index에도 유지 |
| output_fields | 출력 필드 테이블 표시 + 수정 | O | 가장 무거운 핵심 데이터 |
| ocr_fields | OCR 원본 데이터 표시 (`ocrRows`) | O | |
| original_image_url | 전처리 전 이미지 표시 | O | |
| processed_image_url | 전처리 후 이미지 표시 | O | |
| image_url | legacy fallback | O | |
| image_storage_mode | 이미지 URL 결정 로직 | O | |
| autofill_summary | **미사용** (Detail에서 미표시) | O | RunOCR Preview에서만 표시 |

> **주목**: `autofill_summary`는 History 상세에서 표시되지 않는다. RunOCR Preview의 OcrResultPanel에서만 표시된다.

### 4-2. [저장] 클릭 시 갱신되는 필드

```typescript
// DetailHistoryView.tsx:392-403
const handleSave = async () => {
  // outputs = 현재 상태의 output_fields (사용자가 modified에 입력한 값 포함)
  const updated = updateHistoryRun(item.job_id, { output_fields: outputs });
  // groundTruth 저장도 동시 실행
  const newGt = saveGroundTruth(item.template_name, item.file_name, outputs);
};
```

**[저장]으로 갱신되는 것**: `output_fields` 배열 전체 덮어쓰기  
**[저장]으로 갱신되지 않는 것**: `ocr_fields`, 이미지 URL, `autofill_summary`, `updated_at`(필드 없음)

### 4-3. 상세에서 불가능한 것 (미저장 데이터)

- 품목표(invoice tableRows) 재확인 → document_fields 미저장
- validation 결과 재확인 → 미저장
- autofill 제안 목록 확인 → suggestions는 저장되어 있으나 Detail UI에서 미표시

---

## 5. [저장] 버튼 동작 분석

### 5-1. 두 버튼의 역할 분리

| 버튼 | 저장 대상 | 저장 위치 | 영향 |
|------|-----------|----------|------|
| **[저장]** | output_fields 전체 (수정값 포함) | mysuit_ocr_history (updateHistoryRun) | 해당 job_id의 output_fields 덮어쓰기 |
| **[저장]** | 수정값 → groundTruth | mysuit_ocr_groundtruth | 다음 OCR 정답 비교 기준 |
| **[자동복원 후보 저장]** | businessNo + 4개 필드 | mysuit_ocr_restore_profiles | 다음 OCR autofill 기준 |

### 5-2. 원본값과 수정값 분리 여부

현재 output_fields 내부에서 분리됨:
- `original`: OCR 결과 원본값 (불변)
- `modified`: 사용자 수정값 (빈 문자열 = 수정 없음)
- `source`: 값 출처 ("ocr", "biz", "gt", "text")

[저장] 후에도 `original`은 유지되고 `modified`/`source`만 갱신된다.

### 5-3. 두 버튼 충돌 가능성

**없음**. 두 버튼은 완전히 다른 localStorage key에 쓴다.
- [저장] → `mysuit_ocr_history`
- [자동복원 후보 저장] → `mysuit_ocr_restore_profiles`

단, 두 버튼을 같은 화면에서 독립적으로 클릭할 수 있어 사용자가 [저장] 없이 [자동복원 후보 저장]을 먼저 누를 수 있다. 이때 History에는 반영되지 않고 restore_profiles에만 저장된다. 이는 의도된 동작이다.

### 5-4. updated_at 미갱신 문제

[저장] 클릭 시 History record의 `created_at`은 변하지 않고, `updated_at` 필드가 없어 저장 시점을 알 수 없다. list/detail 분리 시 `updated_at` 필드를 history_index에 추가해야 한다.

---

## 6. Restore Profile과 History의 관계

### 6-1. 연결 필드

```typescript
// RestoreProfile 구조
{
  businessNo: string;
  partyType: string;                // "generic"
  fields: RestoreProfileFields;     // companyName, representative, tel, address
  sourceHistoryId: string;          // ← History job_id 참조
  sourceFileName: string;           // ← History file_name 참조
  createdAt: string;
  updatedAt: string;
}
```

- `sourceHistoryId` → `mysuit_ocr_history.job_id`를 참조하지만 **외래키 제약 없음**
- History가 삭제되어도 restore profile의 sourceHistoryId는 dangling reference 상태가 됨
- 현재 코드에서 이 dangliing을 감지하거나 처리하는 로직 없음

### 6-2. 삭제 영향 관계

| 삭제 동작 | 영향 |
|-----------|------|
| History 삭제 → restore profile | **영향 없음** (단방향 참조) |
| Restore profile 삭제 → History | **영향 없음** (분리된 저장소) |

### 6-3. hasRestoreProfile 표시 가능성

목록에서 restore profile 유무를 표시하려면 런타임에 `readRestoreProfiles()`에서 businessNo를 뽑아 History의 autofill_summary.businessNumber와 매칭해야 한다. 현재 저장 구조로는 즉시 알 수 없음. history_index에 `hasRestoreProfile: boolean`을 추가하면 가능하나, restore profile이 삭제될 때 index도 갱신해야 한다(동기화 문제).

---

## 7. 권장 list/detail 구조

### 7-1. history_index (경량 — 목록 전용)

```json
{
  "historyId": "RUN-A1B2C3D4",
  "fileName": "invoice_2026.pdf",
  "templateName": "거래명세서",
  "documentType": "invoice_statement",
  "createdAt": "2026-05-18 20:40:55",
  "updatedAt": "2026-05-18 20:45:10",
  "status": "success",
  "processingTime": 3.2,
  "summary": {
    "fieldCount": 12,
    "autofillStatus": "applied",
    "autofillFilledCount": 3,
    "autofillConfirmedCount": 5,
    "primaryBusinessNo": "119-10-88385",
    "primaryCompanyName": "세광전기조명",
    "tableRowCount": 13,
    "warningCount": 1,
    "missingCount": 1
  },
  "hasConfirmedResult": true,
  "hasRestoreProfile": false
}
```

**도출 방법**:
- `primaryBusinessNo` ← `autofill_summary.businessNumber`
- `primaryCompanyName` ← `output_fields`에서 `회사명` 필드 modified or original 값
- `fieldCount` ← `output_fields.length`
- `autofillStatus` ← `autofill_summary.status`
- `hasConfirmedResult` ← `output_fields` 중 modified ≠ "" 인 항목 존재 여부
- `tableRowCount` ← 현재 미저장, 추후 document_fields.tableRows.length에서 도출
- `warningCount / missingCount` ← 추후 validation 저장 시 도출

### 7-2. history_details (중량 — 상세 전용)

```json
{
  "historyId": "RUN-A1B2C3D4",
  "runSnapshot": {
    "fileName": "invoice_2026.pdf",
    "templateName": "거래명세서",
    "documentType": "invoice_statement",
    "ocrFields": [
      { "name": "회사명", "en": "companyName", "ko": "회사명", "value": "세광전기조명", "confidence": 0.95, "bbox": [10, 20, 200, 40] }
    ],
    "documentFields": {
      "tableRows": [
        { "품명": "LED조명 A형", "수량": "2", "단가": "15000", "금액": "30000" }
      ],
      "tableMeta": { "columns": ["품명", "수량", "단가", "금액"] }
    },
    "autofillSummary": {
      "status": "applied",
      "businessNumber": "119-10-88385",
      "candidateCount": 3,
      "filledCount": 3,
      "confirmedCount": 5,
      "correctedCount": 0
    }
  },
  "confirmedResult": {
    "savedAt": "2026-05-18 20:45:10",
    "outputFields": [
      {
        "no": 1, "en": "companyName", "ko": "회사명",
        "original": "세광전기조명주식회사",
        "modified": "세광전기조명",
        "confidence": 0.95,
        "source": "text",
        "autofillAction": "confirmed"
      }
    ]
  },
  "images": {
    "originalImageUrl": "data:image/jpeg;base64,...",
    "processedImageUrl": "data:image/jpeg;base64,...",
    "imageStorageMode": "url"
  }
}
```

**분리 개념**:
- `runSnapshot`: OCR 실행 시점의 변경 불가 원본 데이터
- `confirmedResult`: [저장] 클릭 시 갱신되는 채택값. savedAt 타임스탬프 포함
- `images`: 별도 접근이 잦아 분리하거나 detail에 포함

### 7-3. restore_profiles와의 관계

```
history_index[historyId] ← sourceHistoryId → restore_profiles[businessNo+partyType]
```

- `history_index`의 `hasRestoreProfile`은 restore profile 저장/삭제 시 함께 갱신
- DB 전환 시 `ocr_restore_profiles.source_run_id` FK로 매핑

---

## 8. 단계별 전환 계획

| 단계 | 작업 | 수정 범위 | 위험도 | 검증 포인트 | rollback |
|------|------|-----------|--------|-------------|----------|
| **2A** 병행 저장 | OCR 실행 시 index/detail 병행 write | UploadWorkspace.tsx, historyStore.ts에 신규 함수 추가 | **낮음** | 기존 history 동작 유지, 신규 key 추가 확인 | 신규 key만 삭제 |
| **2A-b** [저장] 연동 | [저장] 클릭 시 history_details도 갱신 | DetailHistoryView.tsx | **낮음** | updated_at 갱신 확인, output_fields 일치 | key 삭제 |
| **2B** 목록 index 우선 | 목록 조회를 history_index 우선으로 | HistoryWorkspace.tsx | **낮음** | index 없으면 기존 history fallback | 조건문 제거 |
| **2C** 상세 detail 우선 | 상세 조회를 history_details 우선으로 | HistoryWorkspace.tsx, DetailHistoryView.tsx | **중간** | fallback 경로 충분히 테스트 | 조건문 제거 |
| **2D** 동기화 검증 | 삭제 시 index/detail/history 세 곳 동기화 | deleteHistoryRun() 확장 | **중간** | 삭제 후 orphan 레코드 없음 확인 | 동기화 로직 제거 |
| **3** DB 전환 | historyStore.ts → API 호출로 교체 | historyStore.ts 전체 | **높음** | 모든 CRUD, 페이지네이션, 필터 | DB 롤백 |

### 2A 수정 범위 예시

```typescript
// historyStore.ts에 추가할 함수 (기존 mysuit_ocr_history 변경 없음)
export const HISTORY_INDEX_KEY = "mysuit_ocr_history_index";
export const HISTORY_DETAILS_KEY = "mysuit_ocr_history_details";

export function appendHistoryIndex(record: HistoryRunRecord): HistoryIndexEntry {}
export function appendHistoryDetail(record: HistoryRunRecord): void {}
export function updateHistoryDetail(jobId: string, patch: Partial<HistoryDetailEntry>): void {}
export function readHistoryIndex(): HistoryIndexEntry[] {}
export function readHistoryDetail(jobId: string): HistoryDetailEntry | null {}
export function deleteHistoryIndex(jobId: string): boolean {}
export function deleteHistoryDetail(jobId: string): boolean {}
```

---

## 9. DB 매핑

| localStorage 구조 | DB 테이블 후보 | 컬럼/JSONB 후보 | 비고 |
|-------------------|----------------|-----------------|------|
| history_index.historyId | `ocr_runs.id` | UUID PK | |
| history_index.fileName | `ocr_run_files.original_file_name` | VARCHAR | |
| history_index.templateName | `ocr_runs.template_id` → `ocr_templates.name` | FK | |
| history_index.documentType | `ocr_runs.document_type` | VARCHAR | |
| history_index.createdAt | `ocr_runs.created_at` | TIMESTAMPTZ | |
| history_index.updatedAt | `ocr_runs.updated_at` | TIMESTAMPTZ | |
| history_index.status | `ocr_runs.status` | ENUM | |
| history_index.summary.primaryBusinessNo | `ocr_runs.primary_business_no` | VARCHAR | 검색 인덱스 후보 |
| history_index.summary.primaryCompanyName | `ocr_runs.primary_company_name` | VARCHAR | |
| history_index.summary.fieldCount | `ocr_run_results.field_count` | INTEGER | |
| history_index.summary.tableRowCount | `ocr_run_results.table_row_count` | INTEGER | |
| history_index.hasRestoreProfile | 런타임 join | `ocr_restore_profiles.source_run_id` 존재 여부 | |
| history_details.runSnapshot.ocrFields | `ocr_run_results.raw_ocr_data` | JSONB | |
| history_details.runSnapshot.documentFields | `ocr_run_results.document_fields` | JSONB | tableRows 포함 |
| history_details.runSnapshot.autofillSummary | `ocr_run_results.autofill_summary` | JSONB | |
| history_details.confirmedResult.outputFields | `ocr_run_results.confirmed_fields` | JSONB | 별도 컬럼 권장 |
| history_details.confirmedResult.savedAt | `ocr_run_results.confirmed_at` | TIMESTAMPTZ | |
| history_details.images.originalImageUrl | `ocr_run_files.original_image_path` | VARCHAR | S3 key or URL |
| history_details.images.processedImageUrl | `ocr_run_files.processed_image_path` | VARCHAR | |
| mysuit_ocr_restore_profiles | `ocr_restore_profiles` | | |
| restore_profile.businessNo | `ocr_restore_profiles.business_no` | VARCHAR(20) | |
| restore_profile.partyType | `ocr_restore_profiles.party_type` | VARCHAR(20) | |
| restore_profile.fields | `ocr_restore_profiles.fields` | JSONB | companyName 등 |
| restore_profile.sourceHistoryId | `ocr_restore_profiles.source_run_id` | UUID FK | |

---

## 10. 위험 요소와 방어책

| 위험 | 영향 | 방어책 |
|------|------|--------|
| localStorage 용량 증가 (index+detail 추가) | 기존 50개 제한에 추가 부담 | 신규 key에도 MAX_RECORDS=50 동일 적용. QuotaExceededError 폴백 구현 필수 |
| index/detail 간 불일치 (부분 쓰기 실패) | 목록은 있으나 상세 없는 상태 | 상세 조회 실패 시 mysuit_ocr_history fallback. 동기화 검증 주기적 실행 |
| [저장] 후 index.updatedAt 미갱신 | 목록에서 최근 수정 시점 오표시 | 2A-b 단계에서 [저장] → index.updatedAt 갱신 연동 |
| [저장] 후 index.hasConfirmedResult 미갱신 | 목록 상태 뱃지 오표시 | index 갱신 함수에서 hasConfirmedResult 재계산 |
| 삭제 시 index만 삭제되고 detail 잔존 | orphan detail 레코드 누적 | deleteHistoryRun() 확장으로 index/detail 동시 삭제 |
| restore_profile.sourceHistoryId dangling | 삭제된 History를 가리키는 포인터 잔존 | History 삭제 시 연관 restore_profile 경고 표시 (즉시 삭제 불필요) |
| 기존 mysuit_ocr_history와 신규 index 불일치 | 기존 데이터는 index에 없음 | 목록 조회 시 index 없으면 mysuit_ocr_history fallback. 마이그레이션은 별도 단계 |
| DB 전환 시 localStorage 마이그레이션 | 기존 데이터 손실 위험 | historyStore.ts 교체 시 읽기 우선순위: DB → localStorage fallback → 사용자에게 마이그레이션 안내 |

---

## 11. 결론

### 다음 작업 추천

**HISTORY-STRUCTURE-2A** 구현을 즉시 진행 가능하다. 기존 `mysuit_ocr_history`를 건드리지 않고 신규 key(`mysuit_ocr_history_index`, `mysuit_ocr_history_details`)를 병행 write하는 구조이므로 기존 기능에 영향이 없다.

단, 아래 두 가지를 먼저 확정해야 한다:
1. **document_fields.tableRows 저장 결정**: History 상세에서 품목표 재확인 기능이 필요하면 runSnapshot에 포함
2. **suggestions 저장 범위 결정**: output_fields.suggestions[]는 매우 무거움. detail에서 제외하고 History Fallback용 필드만 저장하는 option 고려

### 지금 바로 구현할지 설계만 마감할지

이번 작업(HISTORY-STRUCTURE-1)은 **설계 마감**. 구현은 HISTORY-STRUCTURE-2A로 분리한다.

---

## 12. 다음 작업 후보

| 작업 | 내용 | 우선순위 |
|------|------|---------|
| HISTORY-STRUCTURE-2A | index/detail 병행 저장 추가 (코드 구현) | 높음 |
| HISTORY-STRUCTURE-2B | 목록 조회 index 우선 전환 | 중간 |
| HISTORY-STRUCTURE-2C | 상세 조회 detail 우선 전환 | 중간 |
| I-5 처리 (HISTORY-RESTORE-3) | groundTruth 포함/제외 정책 확정 | 높음 |
| HISTORY-STRUCTURE-2D | [저장] 버튼 index.updatedAt 연동 | 중간 |
| DB-2 schema 반영 | ocr_runs/ocr_run_results/ocr_restore_profiles 정의 | 낮음 |

---

## 분석에 사용된 파일 목록

| 파일 | 분석 내용 |
|------|-----------|
| `src/lib/historyStore.ts` | HistoryRunRecord 전체 구조, CRUD 함수, QuotaExceeded 처리 |
| `src/lib/restoreProfileStore.ts` | RestoreProfile 구조, sourceHistoryId 관계 |
| `src/lib/autofillEngine.ts` | history fallback 로직, output_fields 파싱 방법 |
| `src/components/history/HistoryWorkspace.tsx` | 목록 실제 사용 필드, boardList() 매핑 |
| `src/components/history/DetailHistoryView.tsx` | 상세 사용 필드, [저장]/[자동복원 후보 저장] 로직 |
| `src/components/upload/UploadWorkspace.tsx` | appendHistoryRun() 호출 시 저장 필드 전체 |
| `src/components/upload/OcrResultPanel.tsx` | document_fields.tableRows 사용처, autofill_summary 표시 |
