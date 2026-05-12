# H-0/H-1 History 이미지 저장 구조 분석 및 상세보기 UI 수정 결과

작성일: 2026-05-12

---

## 1. 수정 파일

| 파일 | 변경 내용 |
|---|---|
| `src/lib/historyStore.ts` | `HistoryRunRecord` type에 `original_image_url?: string` 추가; `withoutStoredImages` 함수에서 `original_image_url: undefined` 포함; `appendHistoryRun` 내부 record 생성 시 `original_image_url: partial.original_image_url` 포함 |
| `src/components/history/DetailHistoryView.tsx` | 좌측 이미지 영역 2분할 (상단: 전처리 전 원본, 하단: 전처리 후 이미지); `SourceBadge` 컴포넌트에서 `source === "text"` case 제거 → "직접입력" badge 제거; 이미지 카드 스타일 상수 추가 |

## 2. 백업 파일

| 원본 | 백업 |
|---|---|
| `src/lib/historyStore.ts` | `backup/historyStore_20260512_before_H0H1.ts` |
| `src/components/history/DetailHistoryView.tsx` | `backup/DetailHistoryView_20260512_before_H0H1.tsx` |

## 3. 핵심 요약

1. **이미지 구조 분석 (Case D)**: History record에 `image_url` 하나만 저장되며, 이 값은 backend `runResult.processed_image` (전처리 후 이미지). 원본 이미지(`previewUrl`)는 `URL.createObjectURL(File)` 임시 URL이라 localStorage에 저장 불가.
2. **이미지 2분할**: 좌측 pane을 상/하 카드로 분리. 상단 = 전처리 전(`original_image_url`, 현재 없음 → placeholder), 하단 = 전처리 후(`image_url`).
3. **직접입력 badge 제거**: `SourceBadge`에서 `source === "text"` case를 null 반환으로 변경. 수정 데이터 컬럼/input/저장 버튼/로직은 모두 유지.

---

## 4. RunOCR/History 이미지 저장 구조 분석

| 항목 | 확인 결과 |
|---|---|
| RunOCR 원본 이미지 보관 | `previewUrl` = `URL.createObjectURL(selectedFile)`. 메모리 임시 URL, localStorage 직렬화 불가 |
| 전처리 이미지 생성 여부 | 생성됨. `processedImageUrl` state 변수로 관리 |
| RunOCR 응답 이미지 필드 | `runResult.processed_image` (backend 응답) |
| History 저장 payload 이미지 필드 | `image_url: runResult.processed_image` (전처리 후 이미지 하나만 저장됨) |
| History 조회 응답 이미지 필드 | `image_url` 하나 (localStorage 기반) |
| 현재 History UI 이미지 필드 | `item.image_url` → 전처리 후 이미지 |
| 분류 Case | **Case D** — 전처리 이미지만 저장, 원본 이미지 저장 구조 없음 |

**세부 파일 위치:**
- `UploadWorkspace.tsx:978` → `image_url: runResult.processed_image`
- `historyStore.ts:64` → `image_url?: string` (기존 단일 필드)
- `DetailHistoryView.tsx:351` → `item.image_url` 렌더링 (기존)

---

## 5. History 저장 구조 변경 여부

| 항목 | 결과 |
|---|---|
| `original_image_url` type 추가 | **추가** — `historyStore.ts` `HistoryRunRecord` type에 optional 필드로 추가 |
| `original_image_url` 저장 | **미구현** — 원본 이미지가 ObjectURL이라 localStorage 직렬화 불가. placeholder 처리 |
| `processedImageUrl` type 변경 | **없음** — 기존 `image_url` 필드 유지 (backward compatibility) |
| 기존 `imageUrl` fallback | `item.image_url` 그대로 사용 |
| `withoutStoredImages` 업데이트 | `original_image_url: undefined` 추가 (quota 초과 시 양쪽 모두 제거) |
| backend/API 확장 필요 여부 | **필요** — 원본 이미지를 History에 포함하려면 backend에서 원본 이미지 URL/base64를 RunOCR 응답에 추가하거나, frontend에서 파일 base64 변환 후 저장 로직 추가 필요 |

---

## 6. 출력 필드 변경 내용

| 항목 | 결과 |
|---|---|
| 수정 데이터 컬럼 유지 | **유지** — `<th>수정 데이터</th>` 그대로 |
| 수정 데이터 input 유지 | **유지** — `<input onChange={handleModify} />` 그대로 |
| 저장 버튼 유지 | **유지** — `<button onClick={handleSave}>저장</button>` 그대로 |
| 직접입력 badge 제거 | **제거** — `SourceBadge`에서 `source === "text"` → `null` 반환으로 변경 |
| 남은 source badge | `"biz"` → "매칭복원", `"gt"` → "정답" (유지) |
| 수정 데이터 저장 로직 | **유지** — `handleModify`, `handleSave`, `updateHistoryRun` 모두 그대로 |

**변경 위치:** `DetailHistoryView.tsx` `SourceBadge` 함수 (line ~233)
```tsx
// 변경 전
if (!source || source === "ocr") return null;
// 변경 후
if (!source || source === "ocr" || source === "text") return null;
```

---

## 7. 이미지 영역 변경 내용

| 항목 | 결과 |
|---|---|
| 상단 원본 이미지 | `item.original_image_url` 사용. 현재 데이터 없음 → "원본 이미지 없음" placeholder |
| 하단 전처리 후 이미지 | `item.image_url` 사용. 기존과 동일 |
| fallback 처리 | `onError` → 이미지 숨김; URL 없음 → placeholder span |
| 레이아웃 | flexDirection: column, 각 카드 flex: 1 → 50:50 분할 |
| 이미지 object-fit | `contain` 유지 |
| 기존 이미지 확대/클릭 기능 | 기존에도 없었음 (단순 img 태그) |

**스타일 상수 추가:**
- `imageCardStyle` — 개별 이미지 카드 테두리/배경
- `imageCardHeaderStyle` — 카드 제목 ("전처리 전/후 이미지")
- `imageCardBodyStyle` — 이미지/placeholder 래퍼
- `imagePlaceholderStyle` — 없음 표시 텍스트

---

## 8. 기존 기능 영향 확인

| 항목 | 결과 |
|---|---|
| History 목록 조회 | **영향 없음** — `HistoryWorkspace.tsx` 미수정 |
| 상세보기 열기/닫기 | **영향 없음** — Props(`item`, `onBack`, `onSaved`) 동일 |
| 출력 필드 표시 | **영향 없음** — 테이블 구조 유지 |
| 수정 데이터 저장 | **영향 없음** — 로직 미수정 |
| OCR 데이터 표시 | **영향 없음** — 섹션 유지 |
| 이미지 표시 | **변경** — 단일 → 2분할 카드 (기능 동일, 레이아웃만 변경) |
| RunOCR 영향 | **없음** — UploadWorkspace.tsx 미수정 |
| Template 영향 | **없음** — 무관 파일 미수정 |
| Test 영향 | **없음** — TestWorkspace.tsx 미수정 |
| tableRows 관련 Test UI | **없음** — 무관 |

---

## 9. 검증 결과

| 검증 | 결과 |
|---|---|
| `npm run typecheck` | **OK** (exit 0, 오류 없음) |
| `npm run build` | **OK** (빌드 성공) |
| 브라우저 확인 | 빌드 기준으로 구조 변경 확인 필요 (서버 실행 환경 없음) |

---

## 10. 남은 문제

| # | 항목 | 내용 | 조치 |
|---|---|---|---|
| 1 | 원본 이미지 저장 불가 | `previewUrl`은 ObjectURL이라 localStorage 직렬화 불가. 현재 상단 카드는 항상 "원본 이미지 없음" placeholder 표시 | **H-2에서 처리** — backend RunOCR 응답에 원본 이미지 URL/base64 추가, 또는 frontend에서 File→base64 변환 후 저장 (용량 관리 필요) |
| 2 | 기존 History 레코드 | 과거 저장 레코드에 `original_image_url` 없음 → placeholder 표시 (예상된 동작) | 정상. fallback 처리 완료 |
| 3 | 이미지 카드 고정 높이 | 각 카드가 50:50으로 분할되므로 긴 이미지는 잘릴 수 있음. `object-fit: contain`으로 비율 유지 | 허용 가능. 향후 resize 가능 |
| 4 | `runResult.processed_image` 형식 | base64 data URL 여부 미검증 (현재 동작 중이면 OK) | RunOCR 실행 후 실제 확인 필요 |

---

## 11. 다음 추천 작업

후보:
- **H-2**: backend RunOCR 응답에 원본 이미지 필드 추가 또는 frontend File→base64 저장 — "원본 이미지 없음" 해결
- **T-4**: Test UI `buildTableRowsValidation`이 backend `tableMeta.extractionStatus`와 `tableRows`를 읽도록 수정 (T-3 연계)
- **RunOCR-History 저장 구조 정리**: `appendHistoryRun` payload 확장, `original_image_url` 실제 저장 구현

**추천: H-2** — 상단 카드가 항상 placeholder인 상태를 해결해야 이미지 2분할의 실질적 효과가 생긴다. frontend에서 `selectedFile`→Blob URL을 base64(축소) 변환 후 `original_image_url`로 저장하는 방식이 가장 간단하다.

---

## 최종 보고

### 수정 파일
- `src/lib/historyStore.ts` — `original_image_url?: string` type 추가
- `src/components/history/DetailHistoryView.tsx` — 이미지 2분할 + "직접입력" 제거

### 핵심 요약
- **Case D 확정**: History record에 `image_url` (전처리 이미지) 하나만 저장됨. 원본 이미지는 ObjectURL이라 저장 불가 → placeholder 처리
- **이미지 2분할**: 좌측 pane을 상/하 카드로 변경. 상단 = 전처리 전 (현재 placeholder), 하단 = 전처리 후 (기존 image_url 표시)
- **직접입력 제거**: `SourceBadge`에서 `source === "text"` → null. 수정 데이터 컬럼/input/저장은 모두 유지
- **기존 기능 영향 없음**: 테이블 구조, 저장 로직, 출력 필드, OCR 데이터 표 모두 유지

### 검증 결과
- typecheck: **OK** | build: **OK**

### 다음 추천 작업
**H-2** — 원본 이미지 저장 구현 (frontend File→thumbnail base64 변환 또는 backend 응답 확장)
