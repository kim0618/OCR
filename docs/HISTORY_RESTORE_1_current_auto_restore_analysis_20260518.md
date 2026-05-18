# HISTORY-RESTORE-1: 현재 자동복원 구조 분석

날짜: 2026-05-18  
도구: Claude Code (Claude Sonnet 4.6)  
상태: 분석 전용 — 코드 수정 없음

---

## 1. 요약

| 항목 | 내용 |
|-----|------|
| 저장 위치 | localStorage (`mysuit_ocr_history`) 단일 스토어 |
| 후보 생성 기준 | History의 `output_fields` 중 사용자가 수정한 필드만 |
| 매칭 기준 | 정규화된 사업자번호 단일 비교 (공급자/공급받는자 미구분) |
| 대상 필드 | 회사명, 사업자번호, 대표자, tel, 주소 (5개 allowlist) |
| 제외 필드 | 금액·일자·tableRows — AUTOFILLABLE_FIELDS에 없어 자동 제외 |
| 가장 큰 문제 | 공급자/공급받는자 구분 없음 + localStorage 단일화로 DB 전환 시 구조 재설계 필요 |

---

## 2. 현재 데이터 흐름

```
RunOCR 실행
  └─ UploadWorkspace.tsx:798-1041
        │
        ├─ 1. OCR API 호출 → fields 배열 취득
        │
        ├─ 2. extractBizNumber(fields) 로 사업자번호 추출
        │       └─ bizNumber.ts:66-92
        │
        ├─ 3. collectInternalAutofillCandidates()
        │       └─ autofillEngine.ts:330-332
        │            └─ readHistoryCandidateRecords()
        │                 └─ localStorage "mysuit_ocr_history" 전체 읽기
        │                      → output_fields 반복
        │                      → isUserEditedHistoryField() == true인 필드만
        │                      → candidateFields 포함 여부 확인
        │                      → businessNumber 추출하여 AutofillCandidateRecord 생성
        │
        ├─ 4. buildAutofillSuggestionsFromCandidates()
        │       └─ autofillEngine.ts:344-390
        │            → businessNumber 매칭 후보에서 suggestion 생성
        │            → 동일 field+value 병합 (hitCount 누적)
        │
        ├─ 5. applyAutofillToOutputFields()
        │       └─ autofillEngine.ts:396-427
        │            → isAutofillableField() == true인 필드만 적용
        │            → action: filled / corrected / confirmed / none
        │
        └─ 6. appendHistoryRun()
                └─ historyStore.ts:147-202
                     → localStorage에 HistoryRunRecord 저장
                          - ocr_fields: 원본 OCR 필드
                          - output_fields: 자동복원 적용 후 최종 필드
                          - autofill_summary: 자동복원 결과 요약

Custom 탭 편집 시 (onBlur)
  └─ UploadWorkspace.tsx:1121-1140
        └─ updateHistoryRun(jobId, { output_fields: merged })
              - original: 변경 안 함 (OCR 원본 보존)
              - modified: 사용자 편집값으로 업데이트

다음 RunOCR 실행 시
  └─ 이전 history의 수정된 output_fields가 자동복원 후보로 재사용
```

---

## 3. 현재 저장 구조

### 3-1. localStorage Key

| Key | 용도 | 위치 |
|-----|------|------|
| `mysuit_ocr_history` | OCR 실행 기록 (max 50개) | historyStore.ts:4 |
| `mysuit_ocr_groundtruth` | Ground Truth 정답 데이터 | autofillEngine.ts:79 |

### 3-2. HistoryRunRecord 구조 (historyStore.ts:61-77)

```typescript
{
  job_id: string;                        // "RUN-XXXXXXXX"
  file_name: string;
  template_name: string | null;
  processing_time: number;
  created_at: string;                    // "YYYY-MM-DD HH:mm:ss"
  status: "success" | "fail";
  // 이미지
  image_url?: string;                    // legacy
  original_image_url?: string | null;    // 전처리 전 원본
  processed_image_url?: string | null;   // 전처리 후
  image_storage_mode?: "legacy" | "url";
  // 상세
  ocr_fields?: HistoryOcrField[];        // 원본 OCR 결과
  output_fields?: HistoryOutputField[];  // 정제·복원 후 최종 필드
  autofill_summary?: HistoryAutofillRunSummary;
}
```

### 3-3. HistoryOutputField 구조 (historyStore.ts:20-43)

```typescript
{
  no?: number;
  en: string;                    // 영문 필드명 (e.g. "field_1")
  ko: string;                    // 한글 필드명 (e.g. "공급자 사업자 번호")
  original: string;              // OCR 원본값 — 이후 변경 안 함
  modified: string;              // 사용자 수정값 또는 자동복원 적용값
  confidence: number;
  source?: "ocr" | "biz" | "gt" | "text";
  applied?: string;              // 자동복원으로 채운 값
  autofillAction?: "filled" | "corrected" | "confirmed" | "none";
  suggestions?: AutofillSuggestion[];
}
```

### 3-4. 구조 분리 여부

| 항목 | 분리 여부 |
|-----|---------|
| OCR 원본값 (`original`) vs 최종값 (`modified`) | ✅ 분리됨 |
| 자동복원 적용 여부 (`autofillAction`) | ✅ 저장됨 |
| 원본 OCR 필드 (`ocr_fields`) vs 정제 필드 (`output_fields`) | ✅ 분리됨 |
| confirmedResult 별도 저장 | ❌ 없음 |
| restoreExtract 별도 저장 | ❌ 없음 |
| runSnapshot 별도 저장 | ❌ 없음 |
| tableRows 별도 저장 | ❌ output_fields에 포함되지 않음 |

---

## 4. 자동복원 매칭 기준

### 4-1. 사업자번호 추출 (bizNumber.ts:66-92)

1. 정규식 1차: `/[1-9]\d{2}[\s\-.]?\d{2}[\s\-.]?\d{5}/g`
2. 체크섬 검증 후 통과한 값만 사용
3. 2차: OCR 오인식 문자 교정 (O→0, I→1, Z→2, S→5, B→8 등) 후 재매칭

### 4-2. 공급자/공급받는자 구분

**구분 없음.** autofillEngine.ts의 `readHistoryCandidateRecords()`는 단일 `businessNumber`만 추출하며 공급자/공급받는자를 구분하지 않는다. canonicalFields.ts에 supplier/buyer 분리 정의는 있으나 autofillEngine에서 미사용.

### 4-3. 후보 검색 범위

- localStorage `mysuit_ocr_history` 전체 (max 50건)
- `mysuit_ocr_groundtruth` 전체
- **documentType/templateId 필터 없음** — 전체 history에서 사업자번호만 매칭

### 4-4. 후보 우선순위 (suggestionPriority 점수)

| 조건 | 가중치 |
|-----|--------|
| 기본 confidence | 0.95 |
| sourceType=history | +0.02 |
| sourceType=groundTruth | +0.015 |
| templateName 일치 | +0.03 |
| hitCount ≥ 2 | +최대 0.012 |
| recency (1일 이내) | +0.012 |
| recency (7일 이내) | +0.009 |
| recency (30일 이내) | +0.006 |
| recency (90일 이내) | +0.003 |
| 값 품질 (3자 이상) | +0.004 |

### 4-5. 후보 여러 개일 때 처리 (autofillEngine.ts:374-387)

동일 `field::value` 조합이면 병합(hitCount 누적). 다른 value이면 confidence 높은 쪽 우선.

---

## 5. 자동복원 대상 필드

**AUTOFILLABLE_FIELDS** (autofillEngine.ts:70-77):

| 정규화 key | 한글 라벨 | 대상 여부 | 비고 |
|-----------|---------|---------|-----|
| 회사명 | 회사명/상호/가맹점명 | ✅ | alias 다수 |
| 사업자번호 | 사업자번호/등록번호 | ✅ | 매칭 기준 필드 |
| 대표자 | 대표자/대표자명 | ✅ | |
| tel | 전화번호/전화 | ✅ | |
| 주소 | 주소 | ✅ | |

**alias 매핑** (autofillEngine.ts:81-136):
- "상호" → 회사명
- "가맹점명" → 회사명
- "companyName" → 회사명
- "supplierName" → 회사명
- "대표자명" → 대표자
- "phone" → tel
- "address" → 주소

---

## 6. 자동복원 제외 필드

`isAutofillableField()` 통과 조건: `AUTOFILLABLE_FIELDS`에 포함 AND `key !== "총합계금액"`

| 필드 key/라벨 | 제외 여부 | 제외 사유 | 코드 위치 | 위험 |
|-------------|---------|---------|---------|-----|
| 총합계금액/합계금액/총액 | ✅ 제외 | FIELD_ALIASES에서 "총합계금액"으로 정규화 후 isAutofillableField에서 명시 제외 | autofillEngine.ts:114-118, 148-151 | 낮음 |
| 판매금액/부가세/공급가액 | ✅ 제외 | AUTOFILLABLE_FIELDS에 없음 | autofillEngine.ts:119-124 | 낮음 |
| 거래일시/발행일 | ✅ 제외 | AUTOFILLABLE_FIELDS에 없음 | autofillEngine.ts:129-131 | 낮음 |
| 승인번호/카드번호 | ✅ 제외 | AUTOFILLABLE_FIELDS에 없음 | autofillEngine.ts:125-128 | 낮음 |
| tableRows 전체 | ✅ 제외 | output_fields에 포함 안 됨 | readHistoryCandidateRecords 구조상 | 낮음 |
| 품목명/단가/수량 등 | ✅ 제외 | output_fields에 포함 안 됨 | 동일 | 낮음 |
| 전표번호/가맹번호 | ✅ 제외 | AUTOFILLABLE_FIELDS에 없음 | autofillEngine.ts:133-136 | 낮음 |

---

## 7. Custom 수정값 반영 방식

### 7-1. 원본값/수정값 분리

```
original  = OCR 실행 시점 값 → appendHistoryRun() 시 고정, 이후 변경 안 함
modified  = 자동복원 적용 후 값 또는 사용자 편집값 → updateHistoryRun()으로 업데이트 가능
```

### 7-2. source 타입

| source | 의미 |
|--------|------|
| `"ocr"` | OCR 원본값 |
| `"biz"` | 자동복원(사업자번호 매칭)으로 채운 값 |
| `"gt"` | Ground Truth에서 채운 값 |
| `"text"` | 사용자가 직접 입력한 값 |

### 7-3. 사용자 수정 판정 기준 (isUserEditedHistoryField, autofillEngine.ts:249-256)

```typescript
source === "text"                       → 수정됨
source === "biz" || source === "gt"     → 수정 안 됨 (자동복원값은 후보로 재사용 안 함)
modified !== original && modified 있음  → 수정됨
```

**중요**: `source="biz"` (자동복원값)는 재사용 후보에서 제외됨. 사용자가 명시적으로 편집한 값만 후보로 올라감.

### 7-4. Custom 탭 저장 시점

- onBlur 시 `onPersist(editedFields)` 호출 (자동저장)
- `updateHistoryRun(jobId, { output_fields: merged })` 호출
- `original`은 `base.original` 유지, `modified`만 업데이트

---

## 8. 위험 요소

| # | 위험 | 현황 | 수준 |
|---|------|------|------|
| 1 | 금액/일자가 자동복원 후보로 혼입 | AUTOFILLABLE_FIELDS 제외로 현재 안전 | 낮음 |
| 2 | tableRows가 자동복원 후보로 혼입 | output_fields에 포함 안 됨으로 현재 안전 | 낮음 |
| 3 | 공급자/공급받는자 구분 없이 복원 | **구분 없음** — 거래명세서에서 공급자 사업자번호가 공급받는자 필드로 복원될 수 있음 | **높음** |
| 4 | 자동복원값(biz)이 다시 후보로 저장됨 | isUserEditedHistoryField()에서 source=biz 제외로 안전 | 낮음 |
| 5 | 낮은 confidence OCR값이 후보로 저장 | isUserEditedHistoryField() 기준이므로 OCR confidence와 무관, confidence가 낮아도 사용자가 수정한 값은 후보가 됨 | 중간 |
| 6 | 사용자 오입력이 계속 자동복원됨 | 오입력값도 source=text → 후보로 저장됨. 수동 삭제 수단 없음 | **높음** |
| 7 | localStorage/backend 이원화 없음 | localStorage 단일 → 브라우저 초기화 시 소실 | **높음** |
| 8 | DB 전환 시 구조 재설계 필요 | confirmedResult/restoreExtract 미분리 → 전환 시 마이그레이션 복잡 | **높음** |
| 9 | documentType 없이 전체 history 검색 | 거래명세서 history가 영수증 자동복원에 혼입 가능 | 중간 |

---

## 9. 권장 구조 (제안, 이번 작업에서 코드 수정 없음)

### 9-1. 현재 구조

```
HistoryRunRecord
  ├─ ocr_fields[]          (원본 OCR 결과)
  ├─ output_fields[]       (자동복원 포함 최종 필드)
  └─ autofill_summary      (자동복원 요약)
```

### 9-2. 권장 구조

```
HistoryRunRecord
  ├─ runSnapshot
  │    ├─ originalOcrFields[]    (OCR 원본, 이후 불변)
  │    ├─ tableRows[]            (품목표 원본)
  │    ├─ tableMeta              (컬럼 메타)
  │    ├─ processingTime
  │    └─ validationResult
  │
  ├─ confirmedResult
  │    ├─ confirmedFields[]      (사용자가 최종 확인한 필드)
  │    ├─ confirmedTableRows[]
  │    └─ savedAt
  │
  └─ restoreExtract
       ├─ businessNo             (정규화된 사업자번호)
       ├─ partyType              ("supplier" | "buyer" | "merchant")
       ├─ restoreFields{}        (자동복원에 사용할 필드만)
       │    ├─ companyName
       │    ├─ representative
       │    ├─ tel
       │    └─ address
       └─ sourceRunId            (이 복원 데이터의 출처 run)
```

### 9-3. 구조 분리 이점

| 항목 | 현재 | 권장 |
|-----|------|------|
| 자동복원 후보 | output_fields 전체 스캔 | restoreExtract만 조회 |
| 공급자/공급받는자 구분 | 불가 | partyType으로 구분 |
| 오입력 필터링 | 없음 | confirmedResult만 restoreExtract로 승격 |
| DB 전환 | 전체 output_fields 파싱 필요 | restoreExtract 테이블만 전환 |

---

## 10. DB 전환 관점 (필요 테이블 후보)

| 테이블 | 역할 |
|--------|------|
| `ocr_runs` | 실행 기록 (job_id, file_name, created_at, status) |
| `ocr_run_results` | runSnapshot + confirmedResult 저장 |
| `ocr_restore_profiles` | 사업자번호별 복원 프로파일 (businessNo, partyType) |
| `ocr_restore_profile_fields` | 복원 프로파일의 필드별 값 (companyName, tel, address 등) |
| `ocr_restore_applications` | 자동복원 적용 이력 (어떤 run에서 어떤 profile을 사용했는지) |

---

## 11. 다음 작업 제안

| 우선순위 | 작업명 | 내용 |
|---------|--------|------|
| 1 | HISTORY-RESTORE-2 | confirmedResult/restoreExtract 저장 구조 추가 (localStorage 유지) |
| 2 | HISTORY-RESTORE-3 | 자동복원 조회를 restoreExtract 기준으로 변경 |
| 3 | HISTORY-RESTORE-4 | 공급자/공급받는자 partyType 구분 추가 |
| 4 | HISTORY-RESTORE-5 | History 상세 UI에서 confirmedResult/runSnapshot 섹션 분리 |
| 5 | HISTORY-RESTORE-DB | PostgreSQL 전환 시 ocr_restore_profiles 테이블 설계 |

---

## 12. 코드 수정 없음 확인

이 분석 작업에서 수정한 파일: **없음**  
읽은 파일:
- `src/lib/historyStore.ts`
- `src/lib/autofillEngine.ts`
- `src/lib/bizNumber.ts` (agent 분석)
- `src/components/upload/UploadWorkspace.tsx` (agent 분석)
- `src/components/upload/OcrResultPanel.tsx` (agent 분석)
