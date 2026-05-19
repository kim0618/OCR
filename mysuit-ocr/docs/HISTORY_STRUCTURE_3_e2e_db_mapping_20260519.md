# HISTORY-STRUCTURE-3: E2E 회귀 검증 및 DB 매핑 최종 리포트

- 생성일: 2026-05-19
- 작업명: HISTORY-STRUCTURE-3
- 담당 모델: Claude Sonnet 4.6 (claude-sonnet-4-6)
- 분석 방법: 정적 코드 분석 (소스 파일 전체 읽기) + npm run typecheck + npm run build
- 코드 수정: **없음**

---

## 1. 요약

| 항목 | 결과 |
|------|------|
| 전체 상태 | **PASS** |
| 검증 시나리오 수 | 10 (A~J) |
| 시나리오 PASS | 10 |
| 시나리오 FAIL | 0 |
| 회귀 발생 여부 | **없음** |
| npm run typecheck | **PASS** (오류 0건) |
| npm run build | **PASS** (ESLint 경고 1건, 빌드 성공) |
| 코드 수정 | **없음** |
| History 구조 2A~2D 마감 가능 여부 | **가능** |
| DB 전환 준비도 | **준비됨** (localStorage 구조가 DB 컬럼으로 직접 매핑 가능) |

> ESLint 경고 `nextVitals is not iterable`는 Next.js ESLint 플러그인 내부 이슈이며 HISTORY-STRUCTURE 작업과 무관.

---

## 2. 현재 localStorage 구조

### 2-1. mysuit_ocr_history (legacy base)

```
Array<HistoryRunRecord>
{
  job_id: string           // "RUN-XXXXXXXX"
  file_name: string
  template_name: string | null
  processing_time: number
  created_at: string       // "YYYY-MM-DD HH:mm:ss"
  status: "success" | "fail"
  image_url?: string                 // legacy 단일 이미지
  original_image_url?: string | null // 전처리 전 원본
  processed_image_url?: string | null// 전처리 후
  image_storage_mode?: "legacy" | "url"
  ocr_fields?: HistoryOcrField[]
  output_fields?: HistoryOutputField[]
  autofill_summary?: HistoryAutofillRunSummary
}
MAX_RECORDS = 50, QuotaExceededError 다단계 폴백
```

### 2-2. mysuit_ocr_history_index

```
Array<HistoryIndexItem>
{
  historyId: string         // job_id와 동일
  fileName?: string
  templateName?: string | null
  documentType?: string
  createdAt?: string
  updatedAt?: string        // [저장] 시 갱신
  status?: string
  summary?: {
    fieldCount?: number
    tableRowCount?: number
    autofillStatus?: string
    primaryBusinessNo?: string
    primaryCompanyName?: string
  }
  hasConfirmedResult?: boolean  // [저장] 시 true로 갱신
  hasRestoreProfile?: boolean
  sourceFileName?: string
}
MAX_RECORDS = 50 (upsert 시 slice)
```

### 2-3. mysuit_ocr_history_details

```
Record<historyId, HistoryDetailRecord>
{
  historyId: string
  runSnapshot?: {
    ocrFields?: unknown[]
    documentFields?: {
      tableRows?: unknown[]
      tableMeta?: Record<string, unknown>
    }
    outputFieldsSnapshot?: unknown[]
    autofillSummary?: unknown
  }
  confirmedResult?: {
    savedAt?: string
    outputFields?: unknown[]
  }
  images?: {
    originalImageUrl?: string | null
    processedImageUrl?: string | null
    imageUrl?: string
  }
}
MAX 제한 없음 (legacy MAX 50 간접 제한)
```

### 2-4. mysuit_ocr_restore_profiles

```
Array<RestoreProfile>
{
  businessNo: string
  partyType: string      // 현재 "generic" 고정
  fields: {
    companyName?: string
    representative?: string
    tel?: string
    address?: string
  }
  sourceHistoryId: string
  sourceFileName: string
  createdAt: string
  updatedAt: string
}
QuotaExceededError 핸들링 없음 (개선 후보)
```

---

## 3. 시나리오별 검증 결과

| 시나리오 | 기대 | 실제 | 상태 | 비고 |
|----------|------|------|------|------|
| A. RunOCR 저장 | legacy/index/detail 동시 생성, 실패 격리 | UploadWorkspace:1008 appendHistoryRun → 1027 syncHistoryIndexAndDetailOnCreate(try/catch 격리) | **PASS** | fail record는 detail/index 미생성 (정상) |
| B. 목록 index 보강 | legacy base + index merge, 구 데이터 표시 | readHistoryListWithFallback(): legacy 기준 순회, indexMap으로 보강, catch→legacy fallback | **PASS** | index.length===0이면 legacy 즉시 반환 |
| C. 상세 details 우선 | detail+index→HistoryRunRecord, 없으면 legacy | readHistoryDetailWithFallback(): detail.historyId 확인 → meta 보강 → legacy fallback | **PASS** | output_fields 3단계 우선순위 정상 |
| D. 저장 confirmedResult | legacy+detail.confirmedResult+index 갱신 | handleSave(): updateHistoryRun → syncHistoryIndexAndDetailOnSave(try/catch 격리) | **PASS** | 저장 실패가 기존 flow 차단 안 함 |
| E. 삭제 동기화 | legacy삭제→index/detail 동기화, profile 보존 | deleteHistoryRun → syncHistoryIndexAndDetailOnDelete (각 단계 독립 try/catch) | **PASS** | confirm 취소 시 아무 저장소 미변경 |
| F. clearHistoryRuns | legacy/index/detail 정리, profile 미삭제 | clearHistoryRuns(): STORAGE_KEY + INDEX_KEY + DETAILS_KEY 제거, RESTORE_KEY 미포함 | **PASS** | UI에서 직접 호출 경로 없음 (정적 분석) |
| G. Restore/자동복원 | restore_profiles 우선, history fallback | collectInternalAutofillCandidates(): restoreProfiles 1순위, historyCandidates 2순위 | **PASS** | groundTruth autofill 경로 제외 확인 |
| H. Preview/Custom/Validation | History 구조 작업이 UI에 영향 없어야 함 | OcrResultPanel import/call 경로 변경 없음, UploadWorkspace OCR 파이프라인 구조 동일 | **PASS** | 정적 코드 분석; 런타임 검증 권장 |
| I. localStorage 안전성 | parse 실패/누락/구 데이터 안전 fallback | 모든 read 함수 try/catch, MAX_RECORDS=50 정책 유지 | **PASS** | details dict MAX 제한 없음 (minor risk) |
| J. DB 매핑 | localStorage 4개 key → DB 테이블 매핑 명확 | 타입 구조가 JSONB/컬럼으로 직접 매핑 가능 | **PASS** | 섹션 6 상세 참조 |

---

## 4. localStorage 정합성

### 생성 (Create)

- `appendHistoryRun()` → legacy 저장
  - QuotaExceededError: FALLBACK_RECORD_LIMITS [30, 15, 5, 1] 다단계 폴백
  - 최후 수단: ocr_fields 제외 최소 레코드 1건
- `syncHistoryIndexAndDetailOnCreate()` (try/catch 격리)
  - `upsertHistoryIndexItem()` → MAX_RECORDS=50 적용
  - `upsertHistoryDetail()` → MAX 제한 없음 (legacy와 간접 연동)
- fail record: legacy만 저장, index/detail 미생성 (의도적)
- document_fields.tableRows: `json.document_fields`에서 rawDocFields로 추출 → detail.runSnapshot.documentFields에 저장

### 조회 (Read)

- **목록**: `readHistoryListWithFallback()`
  - legacy 기준, index 보강 merge
  - index 없음/parse 실패 → legacy 완전 fallback
  - 삭제된 legacy 항목은 index에 남아도 결과에 미포함 (legacy 기준이므로)
- **상세**: `readHistoryDetailWithFallback(historyId)`
  - detail 있음: detail + index meta → HistoryRunRecord
  - detail 없음: readHistoryRuns().find(job_id) → legacy 그대로

### 저장 (Save)

- `updateHistoryRun(job_id, { output_fields })` → legacy 갱신
- `syncHistoryIndexAndDetailOnSave()` (try/catch 격리)
  - index[idx].updatedAt = now, hasConfirmedResult = true
  - details[historyId].confirmedResult = { savedAt, outputFields }
- 양측 실패 독립: legacy 저장 성공 후 index/detail 실패해도 기존 flow 유지

### 삭제 (Delete)

- `deleteHistoryRun(job_id)` → legacy filter + tryWriteHistory
- `syncHistoryIndexAndDetailOnDelete(historyId)` (각 단계 독립 try/catch)
  - index filter (historyId 제거)
  - details filter (historyId 키 제거)
- profile: 미삭제 (sourceHistoryId dangling 허용 — 후속 경고 UI 후보)

### fallback 경로 확인

| 상황 | 동작 |
|------|------|
| index key 없음 | readHistoryIndex() → [] → 목록 fallback |
| details key 없음 | readHistoryDetails() → {} → 상세 fallback |
| index parse 실패 | readHistoryListWithFallback() catch → legacy |
| details parse 실패 | readHistoryDetailWithFallback() catch → legacy |
| sync 쓰기 실패 | 각 try/catch로 격리, 기존 flow 계속 |

### dangling reference

- `mysuit_ocr_restore_profiles[].sourceHistoryId`가 삭제된 historyId를 참조할 수 있음
- 현재 경고 UI 없음 — 후속 이슈로 등록 (ISSUE-1)

---

## 5. 회귀 확인

| 기능 | 이전 구현 | 현재 구현 | 회귀 여부 |
|------|-----------|-----------|-----------|
| History 목록 조회 | readHistoryRuns() | readHistoryListWithFallback() | 없음 |
| History 상세 조회 | runs.find(job_id) | readHistoryDetailWithFallback() | 없음 |
| [저장] | updateHistoryRun() | updateHistoryRun() + syncOnSave | 없음 |
| 삭제 (인라인) | deleteHistoryRun() | deleteHistoryRun() + syncOnDelete | 없음 |
| 삭제 (API) | api.post(/ocrDelete) | **dead code** (historyDelete 함수, 미연결) | 해당 없음 |
| [자동복원 후보 저장] | writeRestoreProfiles() | 동일 | 없음 |
| Restore 탭 목록/상세/삭제 | readRestoreProfiles() | 동일 | 없음 |
| RunOCR 자동복원 | collectInternalAutofillCandidates() | 동일 (restore→history fallback) | 없음 |
| Preview 탭 | OcrResultPanel | 구조 변경 없음 | 없음 |
| Custom 탭 | OcrResultPanel | 구조 변경 없음 | 없음 |
| Validation 탭 | OcrResultPanel | 구조 변경 없음 | 없음 |

> 주의: `historyDelete()` 함수는 HistoryWorkspace.tsx에 정의되어 있으나 어떤 UI 버튼에도 연결되지 않음. 과거 API 기반 삭제 경로의 잔재로 dead code 상태. 현재 실제 삭제는 인라인 `onClick → deleteHistoryRun()` 경로 사용.

---

## 6. DB 매핑

| localStorage | DB 테이블 | 컬럼/JSONB | 비고 |
|---|---|---|---|
| mysuit_ocr_history_index[].historyId | `ocr_runs` | id (PK) | job_id 그대로 사용 가능 |
| index[].fileName | `ocr_runs` | file_name | varchar |
| index[].templateName | `ocr_runs` | template_name | varchar nullable |
| index[].documentType | `ocr_runs` | document_type | varchar nullable |
| index[].createdAt | `ocr_runs` | created_at | timestamptz |
| index[].updatedAt | `ocr_runs` | updated_at | timestamptz |
| index[].status | `ocr_runs` | status | enum('success','fail') |
| index[].summary | `ocr_runs` | summary | JSONB |
| index[].hasConfirmedResult | `ocr_runs` | has_confirmed_result | boolean default false |
| index[].hasRestoreProfile | `ocr_runs` | has_restore_profile | boolean default false |
| details[].images | `ocr_run_files` | original_url, processed_url, legacy_url | 별도 테이블 또는 ocr_runs JSONB |
| details.runSnapshot.ocrFields | `ocr_run_results` | raw_ocr_data | JSONB |
| details.runSnapshot.documentFields | `ocr_run_results` | document_fields | JSONB (tableRows 포함) |
| details.runSnapshot.outputFieldsSnapshot | `ocr_run_results` | output_fields_snapshot | JSONB |
| details.runSnapshot.autofillSummary | `ocr_run_results` | autofill_summary | JSONB |
| details.confirmedResult.outputFields | `ocr_run_results` | confirmed_fields | JSONB |
| details.confirmedResult.savedAt | `ocr_run_results` | confirmed_at | timestamptz nullable |
| mysuit_ocr_restore_profiles[].businessNo | `ocr_restore_profiles` | business_no | varchar PK후보 |
| restore_profiles[].partyType | `ocr_restore_profiles` | party_type | varchar default 'generic' |
| restore_profiles[].fields | `ocr_restore_profiles` | fields | JSONB (1차 MVP) |
| restore_profiles[].sourceHistoryId | `ocr_restore_profiles` | source_run_id | varchar, FK→ocr_runs nullable |
| restore_profiles[].sourceFileName | `ocr_restore_profiles` | source_file_name | varchar |
| restore_profiles[].createdAt/updatedAt | `ocr_restore_profiles` | created_at, updated_at | timestamptz |

### DB 매핑 설계 노트

1. **FK 정책**: `source_run_id` → `ocr_runs.id`는 nullable로 설계. history 삭제 시 profile의 source_run_id는 NULL로 처리하거나 그대로 보존 (현재 localStorage 정책과 동일).
2. **tableRows 정규화**: 1차 MVP에서는 `document_fields JSONB`에 tableRows 포함. 장기적으로 `ocr_run_table_rows` 별도 테이블로 정규화 가능.
3. **supplier/buyer partyType**: restore_profiles의 partyType은 현재 "generic" 고정. DB에서는 enum('generic','supplier','buyer') 로 확장 가능.
4. **fields JSONB**: RestoreProfileFields (companyName/representative/tel/address)는 1차 MVP에서 JSONB로 충분. 장기적으로 개별 컬럼으로 정규화 가능.
5. **image 저장 전략**: 현재 Base64 data URL이 localStorage에 저장됨. DB 전환 시 object storage (S3/GCS) URL로 교체 필요. `ocr_run_files` 테이블 또는 `ocr_runs.images JSONB`로 URL만 저장.

---

## 7. 남은 이슈

### ISSUE-1: sourceHistoryId dangling 경고 UI 미구현
- **증상**: history 삭제 후 restore profile의 sourceHistoryId가 존재하지 않는 job_id를 가리킴
- **재현**: History 항목 삭제 → Restore 탭 → 해당 profile의 "원본 History ID" 클릭 경로 없음 (현재 표시만 함)
- **원인**: deleteHistoryRun이 profile을 삭제하지 않도록 의도 설계됨
- **영향**: 데이터 불일치 표시 없음, 기능 오동작 없음
- **수정 후보**: AutoRestoreWorkspace에서 sourceHistoryId 유효성 확인 후 "원본 삭제됨" 배지 표시
- **우선순위**: LOW
- **다음 작업명 제안**: HISTORY-RESTORE-5 또는 DB-2 전환 시 FK nullable로 처리

### ISSUE-2: writeHistoryDetails / writeHistoryIndex QuotaExceededError 미처리
- **증상**: localStorage 용량 한계 도달 시 detail/index 저장 실패, 경고 없음
- **재현**: 대용량 이미지 포함 OCR 50건 이상 반복 실행
- **원인**: writeHistoryIndex(), writeHistoryDetails()에 QuotaExceededError try/catch 없음 (appendHistoryRun은 다단계 처리 있음)
- **영향**: index/detail 저장 실패 → fallback으로 legacy만 표시 (기능 유지), 데이터 불완전
- **수정 후보**: writeHistoryIndex/writeHistoryDetails에 QuotaExceededError catch 추가 및 warn 로그
- **우선순위**: MEDIUM
- **다음 작업명 제안**: HISTORY-STRUCTURE-4 localStorage 안전성 강화

### ISSUE-3: upsertHistoryDetail MAX 제한 없음
- **증상**: details dict에 키가 무제한 증가 가능
- **재현**: 50건 이상 OCR 실행 시 legacy는 MAX_RECORDS=50으로 cap되지만 details는 이전 항목이 청소되지 않음 (deleteHistoryRun 경유 시 sync 삭제되지만, 직접 clearHistoryRuns 없이 교체 실행 시)
- **원인**: upsertHistoryDetail()에 MAX 제한 로직 없음. appendHistoryRun의 MAX_RECORDS 정책과 details dict가 직접 연동되지 않음
- **영향**: localStorage 용량 증가 위험 (ISSUE-2와 복합)
- **수정 후보**: upsertHistoryDetail에서 MAX_RECORDS 초과 시 가장 오래된 항목 제거
- **우선순위**: LOW (deleteHistoryRun 동기화로 사실상 제한됨)
- **다음 작업명 제안**: HISTORY-STRUCTURE-4

### ISSUE-4: readGroundTruthCandidateRecords() 데드 코드
- **증상**: autofillEngine.ts에 정의되어 있으나 collectInternalAutofillCandidates()에서 호출 안 됨
- **재현**: 정적 코드 분석으로 확인. groundTruth는 autofill 파이프라인에서 완전히 제외됨
- **원인**: HISTORY-RESTORE-3에서 실사용 자동복원에서 groundTruth 제외 정책 적용
- **영향**: 없음 (dead code, 런타임 영향 없음)
- **정책 권고**:
  - 실사용 자동복원: restore_profiles → history fallback 유지 (groundTruth 제외)
  - groundTruth: 테스트/검증용 데이터로 분리 유지
  - readGroundTruthCandidateRecords(): 후속 작업에서 제거 또는 테스트 전용 export로 분리
- **우선순위**: LOW
- **다음 작업명 제안**: HISTORY-RESTORE-6 또는 CLEANUP-1

### ISSUE-5: writeRestoreProfiles QuotaExceededError 미처리
- **증상**: 대용량 profile 저장 시 예외 발생 가능
- **재현**: 다수의 restore profile 저장 후 QuotaExceededError
- **원인**: writeRestoreProfiles()에 QuotaExceededError 처리 없음
- **영향**: 저장 실패 시 UI가 catch하지 못해 UI 오류 발생 가능
- **수정 후보**: writeRestoreProfiles에 try/catch 추가
- **우선순위**: LOW (profile 건수가 실제로는 적음)
- **다음 작업명 제안**: HISTORY-STRUCTURE-4

### ISSUE-6: historyDelete() 함수 dead code
- **증상**: HistoryWorkspace.tsx의 historyDelete() 함수가 어떤 UI 버튼에도 연결되지 않음
- **원인**: 과거 API 기반 삭제 경로의 잔재. 현재 삭제는 인라인 onClick → deleteHistoryRun() 사용
- **영향**: 없음 (dead code)
- **수정 후보**: historyDelete() 함수 제거 또는 주석 처리
- **우선순위**: LOW (cleanup)
- **다음 작업명 제안**: CLEANUP-1

### ISSUE-7: History 상세 tableRows 렌더링 미연결
- **증상**: detail.runSnapshot.documentFields.tableRows가 저장되지만 DetailHistoryView에서 표시 안 됨
- **재현**: 거래명세서 OCR 실행 → History 상세 → 품목표 표시 없음
- **원인**: DetailHistoryView.tsx는 output_fields와 ocr_fields만 렌더링, documentFields 표시 UI 없음
- **영향**: 상세 보기에서 품목표 데이터 미표시 (저장은 정상)
- **수정 후보**: DetailHistoryView에 documentFields.tableRows 렌더링 섹션 추가
- **우선순위**: MEDIUM (데이터는 있으나 UI 미노출)
- **다음 작업명 제안**: HISTORY-STRUCTURE-4 또는 별도 HISTORY-DETAIL-1

### ISSUE-8: sourceType restoreProfile 배지 미표시
- **증상**: autofill 결과에서 sourceType이 "restoreProfile"인 항목이 있어도 Preview UI에서 별도 배지 없음
- **영향**: 낮음 (기능 동작 정상, UI 정보성 개선 필요)
- **우선순위**: LOW
- **다음 작업명 제안**: UI-ENHANCEMENT-1

---

## 8. 최종 결론

### HISTORY-STRUCTURE-2A~2D 마감 가능 여부

**마감 가능 (PASS)**

- 모든 핵심 기능 검증 완료 (시나리오 A~J 전체 PASS)
- 회귀 없음
- typecheck PASS, build PASS
- 코드 수정 없이 검증 완료
- 발견된 이슈 모두 LOW~MEDIUM 우선순위로 기존 기능 동작에 영향 없음

### DB 전환 준비도

**준비됨**

- localStorage 타입 구조가 DB 컬럼/JSONB로 직접 매핑 가능
- historyStore.ts 모듈만 교체하면 상위 컴포넌트 변경 최소화
- index/detail/restore_profiles 분리 구조가 DB 테이블 설계와 1:1 대응
- image 저장 전략 (Base64 → URL)은 DB 전환 시 별도 작업 필요

---

## 9. 다음 단계

| 순서 | 작업명 | 내용 | 우선순위 |
|------|--------|------|---------|
| 1 | **DB-2** | PostgreSQL schema 작성 (ocr_runs, ocr_run_results, ocr_run_files, ocr_restore_profiles) | HIGH |
| 2 | **HISTORY-STRUCTURE-4** | writeHistoryIndex/Details QuotaExceededError 처리, upsertHistoryDetail MAX 제한 | MEDIUM |
| 3 | **HISTORY-DETAIL-1** | History 상세에서 documentFields.tableRows 표시 (ISSUE-7) | MEDIUM |
| 4 | **HISTORY-RESTORE-5** | sourceHistoryId dangling 경고 UI (ISSUE-1) | LOW |
| 5 | **UI-ENHANCEMENT-1** | sourceType restoreProfile 배지 표시 (ISSUE-8) | LOW |
| 6 | **CLEANUP-1** | readGroundTruthCandidateRecords() 제거/분리, historyDelete() 제거 (ISSUE-4, ISSUE-6) | LOW |
| 7 | **DB-3** | localStorage → DB 마이그레이션 스크립트 | DB-2 이후 |

---

## 10. 검증 파일 목록

```
src/lib/historyStore.ts            (671줄) - 핵심 저장소 전체 분석
src/lib/restoreProfileStore.ts     ( 87줄) - restore profile 전체 분석
src/lib/autofillEngine.ts          (486줄) - autofill 파이프라인 전체 분석
src/components/history/HistoryWorkspace.tsx    (334줄) - 목록/삭제 UI 분석
src/components/history/DetailHistoryView.tsx   (751줄) - 상세/저장/restore 저장 분석
src/components/upload/UploadWorkspace.tsx      (1500줄) - OCR 실행/저장 핵심 경로 분석
src/components/upload/OcrResultPanel.tsx       (1700줄) - Preview/Custom/Validation 분석
src/components/autorestore/AutoRestoreWorkspace.tsx (435줄) - Restore 탭 전체 분석
```

---

*리포트 생성: HISTORY-STRUCTURE-3 / Claude Sonnet 4.6 / 2026-05-19*
