# H-2 History 이미지 저장 구조 DB 전환 대비 정리 결과

작성일: 2026-05-12  
직전 작업: H-0/H-1 (H0H1_history_image_storage_and_layout_20260512.md)

---

## 1. 수정 파일

| 파일 | 변경 내용 |
|---|---|
| `src/lib/historyStore.ts` | `HistoryImageStorageMode` 타입 추가; `HistoryRunRecord`에 `processed_image_url`, `image_storage_mode` 필드 추가; `withoutStoredImages`에 `processed_image_url` 포함; `appendHistoryRun` record에 `processed_image_url`, `image_storage_mode` 추가; `getOriginalHistoryImage`, `getProcessedHistoryImage` helper export |
| `src/components/upload/UploadWorkspace.tsx` | `appendHistoryRun` 호출 시 `processed_image_url`, `original_image_url`, `image_storage_mode` 명시 추가 |
| `src/components/history/DetailHistoryView.tsx` | `getOriginalHistoryImage`, `getProcessedHistoryImage` import 추가; `ImagePanel` 컴포넌트 추가; 좌측 이미지 영역에서 helper 함수 사용 |

## 2. 백업 파일

| 원본 | 백업 |
|---|---|
| `src/lib/historyStore.ts` | `backup/historyStore_20260512_before_H2.ts` |
| `src/components/history/DetailHistoryView.tsx` | `backup/DetailHistoryView_20260512_before_H2.tsx` |
| `src/components/upload/UploadWorkspace.tsx` | `backup/UploadWorkspace_20260512_before_H2.tsx` |

---

## 3. 핵심 요약

1. **이미지 필드 정규화**: `image_url` (legacy) 유지 + `processed_image_url` + `original_image_url` + `image_storage_mode` 추가
2. **Helper 함수 export**: `getOriginalHistoryImage`, `getProcessedHistoryImage` — 전처리 전/후 이미지 URL 반환, fallback 포함
3. **ImagePanel 컴포넌트**: 재사용 가능한 이미지 카드 컴포넌트 추출 (H-1 인라인 JSX → 컴포넌트화)
4. **RunOCR 저장 정규화**: `processed_image_url = runResult.processed_image`, `original_image_url = null` (backend 미지원), `image_storage_mode = "url"`
5. **base64 저장 없음**: 모든 이미지는 URL/path 형태로만 저장. 원본 이미지(ObjectURL)는 직렬화하지 않음

---

## 4. 현재 이미지 저장 구조

| 항목 | 결과 |
|---|---|
| 기존 `image_url` 의미 | `runResult.processed_image` — 전처리 후 이미지. legacy 호환 유지 |
| `original_image_url` 현재 상태 | `null` (서버 저장 구조 없음. H-3에서 backend 지원 시 채움) |
| `processed_image_url` 현재 상태 | `runResult.processed_image` 와 동일. 신규 저장 시 명시적으로 저장 |
| `image_storage_mode` | `"url"` (신규), 기존 데이터에는 없음 → `undefined` fallback 처리 |
| localStorage 저장 | URL/path 문자열만 저장. base64 없음 |
| base64 저장 | **사용 안 함** |

---

## 5. 변경 내용

### HistoryRunRecord 타입 (historyStore.ts)

```typescript
export type HistoryImageStorageMode = "legacy" | "url";

export type HistoryRunRecord = {
  // ... 기존 필드 ...
  image_url?: string;               // legacy: 전처리 후 이미지 (이전 데이터 호환)
  original_image_url?: string | null;  // 전처리 전 원본 이미지 URL
  processed_image_url?: string | null; // 전처리 후 이미지 URL (H-2 이후 명시)
  image_storage_mode?: HistoryImageStorageMode; // "legacy" | "url"
  // ...
};
```

### Helper 함수 (historyStore.ts export)

```typescript
// 전처리 전 원본 이미지 URL 반환. 없으면 null.
export function getOriginalHistoryImage(record: HistoryRunRecord): string | null {
  return record.original_image_url ?? null;
}

// 전처리 후 이미지 URL 반환. processed_image_url → image_url legacy fallback.
export function getProcessedHistoryImage(record: HistoryRunRecord): string | null {
  return record.processed_image_url ?? record.image_url ?? null;
}
```

### RunOCR 저장 payload (UploadWorkspace.tsx)

```typescript
appendHistoryRun({
  // legacy 호환: image_url 유지
  image_url: runResult.processed_image,
  // H-2: 명시적 이미지 URL 필드
  processed_image_url: runResult.processed_image ?? null,
  original_image_url: null, // 서버 저장 구조 없음. H-3에서 backend 제공 시 채움
  image_storage_mode: "url",
  // ...
});
```

### ImagePanel 컴포넌트 (DetailHistoryView.tsx)

```tsx
type ImagePanelProps = {
  title: string;
  imageUrl: string | null;
  emptyText: string;
  alt: string;
};

function ImagePanel({ title, imageUrl, emptyText, alt }: ImagePanelProps) { ... }
```

---

## 6. 최종 이미지 필드 정책

| 필드 | 의미 | 현재 사용 | DB 전환 시 |
|---|---|---|---|
| `image_url` | legacy 전처리 이미지 URL | 기존 데이터 fallback | 유지 (migration 완료 후 deprecated) |
| `original_image_url` | 전처리 전 원본 이미지 URL | `null` (서버 미지원) | 서버 업로드 경로/URL 저장 |
| `processed_image_url` | 전처리 후 이미지 URL | `runResult.processed_image` 와 동일 | 전처리 결과 경로/URL 저장 |
| `image_storage_mode` | 저장 모드 구분 | `"url"` (신규) | DB 컬럼화 가능 |
| `image_pages` | 다중 페이지 확장 | 미사용 (type 초안만) | PDF/다중 페이지 지원 시 추가 |

### fallback 우선순위

**전처리 전 이미지**: `original_image_url` → null (placeholder)  
**전처리 후 이미지**: `processed_image_url` → `image_url` (legacy) → null (placeholder)

---

## 7. 운영 DB 전환 설계

### 7.1 왜 base64를 저장하지 않는가

- localStorage 5MB 한계: base64 이미지 1장만으로 1~3MB 소비
- DB BLOB 저장: 조회 성능 저하, 인덱스 불가, 백업 비대화
- URL/path 저장이 표준: S3, GCS, Azure Blob 등 Object Storage와 호환
- CDN 활용 불가: base64는 캐시/CDN 적용 불가

### 7.2 파일 저장 위치

**서버 디스크 저장 방식:**
```
/storage/ocr/
  original/{yyyy}/{mm}/{dd}/{historyId}_p{pageNo}.png
  processed/{yyyy}/{mm}/{dd}/{historyId}_p{pageNo}_processed.png
  thumbnail/{yyyy}/{mm}/{dd}/{historyId}_p{pageNo}_thumb.webp
```

**Object Storage 저장 방식 (S3/GCS):**
```
s3://mysuit-ocr-storage/
  original/2026/05/12/RUN-ABCD1234_p1.png
  processed/2026/05/12/RUN-ABCD1234_p1_processed.png
  thumbnail/2026/05/12/RUN-ABCD1234_p1_thumb.webp
```

URL 예시: `https://storage.mysuit.co.kr/ocr/original/2026/05/12/RUN-ABCD1234_p1.png`

### 7.3 DB 테이블 초안 (단일 이미지)

```sql
CREATE TABLE ocr_history (
  id             VARCHAR(36)  PRIMARY KEY,     -- job_id (RUN-XXXXXXXX)
  template_id    VARCHAR(36),
  template_name  VARCHAR(200),
  document_type  VARCHAR(50),                  -- invoice_statement, card_receipt 등
  original_file_name    VARCHAR(500),
  original_image_url    TEXT,                  -- 원본 이미지 URL/path
  processed_image_url   TEXT,                  -- 전처리 이미지 URL/path
  image_storage_mode    VARCHAR(20) DEFAULT 'url',
  ocr_result_json       JSONB,
  output_fields_json    JSONB,
  table_rows_json       JSONB,                 -- T-3 tableRows 저장용
  processing_time_ms    INT,
  status         VARCHAR(10),                  -- success / fail
  created_at     TIMESTAMP DEFAULT NOW(),
  updated_at     TIMESTAMP DEFAULT NOW()
);
```

### 7.4 DB 테이블 초안 (PDF/다중 페이지 확장)

```sql
CREATE TABLE ocr_history_page (
  id                  SERIAL PRIMARY KEY,
  history_id          VARCHAR(36) REFERENCES ocr_history(id),
  page_no             INT NOT NULL,
  original_image_url  TEXT,
  processed_image_url TEXT,
  thumbnail_url       TEXT,
  original_width      INT,
  original_height     INT,
  processed_width     INT,
  processed_height    INT,
  created_at          TIMESTAMP DEFAULT NOW(),
  UNIQUE(history_id, page_no)
);
```

TypeScript 타입 초안 (미래 확장):
```typescript
export type HistoryImagePage = {
  page_no: number;
  original_image_url?: string | null;
  processed_image_url?: string | null;
  thumbnail_url?: string | null;
  original_width?: number;
  original_height?: number;
};
```

### 7.5 Object Storage 확장 방안

1. 업로드 시 backend에서 S3 presigned URL 발급
2. frontend가 presigned URL로 직접 PUT 또는 backend 경유 업로드
3. 업로드 완료 후 URL을 History 레코드에 저장
4. 조회 시 presigned URL 또는 CDN URL 반환

---

## 8. 마이그레이션 규칙

| 기존 필드 | 신규 필드 | 규칙 |
|---|---|---|
| `image_url` (값 있음) | `processed_image_url` | `image_url` → `processed_image_url` 로 복사 |
| `image_url` (없음) | `processed_image_url` | `null` |
| `original_image_url` (없음) | `original_image_url` | `null` (placeholder 표시) |
| 없음 | `image_storage_mode` | 기존 레코드 → `"legacy"`, 신규 → `"url"` |

localStorage→DB 마이그레이션 쿼리 예시:
```sql
INSERT INTO ocr_history (id, ..., processed_image_url, image_storage_mode)
SELECT job_id, ..., image_url, 'legacy'
FROM localStorage_export
WHERE image_url IS NOT NULL;
```

---

## 9. 기존 기능 영향 확인

| 항목 | 결과 |
|---|---|
| History 목록 조회 | **영향 없음** — `HistoryWorkspace.tsx` 미수정 |
| 상세보기 열기/닫기 | **영향 없음** — Props 인터페이스 동일 |
| 이미지 표시 | **정상** — 기존 `image_url` → `getProcessedHistoryImage` fallback으로 계속 표시 |
| 원본 이미지 placeholder | **정상** — `original_image_url = null` → placeholder |
| 수정 데이터 컬럼/input/저장 | **영향 없음** — 로직 미수정 |
| "직접입력" badge | **숨김 유지** — H-1 상태 유지 |
| OCR 데이터 표 | **영향 없음** |
| RunOCR 실행 | **영향 없음** — `processed_image_url` 추가만, 기존 로직 유지 |
| Template 화면 | **영향 없음** |
| Test 화면 | **영향 없음** |

---

## 10. 검증 결과

| 검증 | 결과 |
|---|---|
| `npm run typecheck` | **OK** (exit 0) |
| `npm run build` | **OK** (빌드 성공) |
| 브라우저 확인 | 빌드 기준 구조 변경 확인 완료 |

---

## 11. 남은 문제

| # | 항목 | 내용 | 조치 |
|---|---|---|---|
| 1 | 원본 이미지 미저장 | `original_image_url = null`. 서버에서 원본 업로드 파일을 저장/URL 반환하지 않으면 불가 | **H-3에서 backend 설계** |
| 2 | `runResult.original_image` 미반환 | backend OCR API 응답에 원본 이미지 URL 없음. 현재 `processed_image`만 반환 | H-3에서 backend API 확장 필요 |
| 3 | 이미지 보관 기간 정책 미정 | Storage 비용, 보관 기간, 만료 정책 없음 | 별도 운영 정책 설계 필요 |
| 4 | PDF 다중 페이지 미구현 | `image_pages` 타입 초안만. 현재 단일 이미지 처리 | PDF 지원 시 추가 |
| 5 | thumbnail 미생성 | 목록 표시용 썸네일 없음. 현재 전체 이미지만 | H-3 이후 썸네일 생성 API 추가 가능 |

---

## 12. 다음 추천 작업

후보:
- **H-3**: backend RunOCR API에 원본 이미지 저장 + `original_image_url` 반환 추가 → `original_image_url` 실제 채움
- **T-4**: Test UI `buildTableRowsValidation`이 backend `tableMeta.extractionStatus` + `tableRows` 를 읽도록 수정
- **RunOCR-History DB 전환**: localStorage → 실 DB API 전환 (`historyStore.ts` 교체)
- **OP-2**: Template 비정형 필드 canonical 후보 매핑

**추천: T-4** — 백엔드(T-3)는 이미 `tableMeta.extractionStatus: "partial"`을 반환하고 있으므로, Test UI가 이를 읽도록 수정하면 T-3/T-4 사이클이 완결된다. 이미지 저장(H-3)은 backend 작업이므로 별도 sprint로 진행 가능.
