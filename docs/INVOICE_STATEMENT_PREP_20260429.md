# 거래명세서 1차 구현 준비 문서

작성일: 2026-04-29  
작성 목적: 내일 Codex 거래명세서 1차 extractor 구현을 위한 사전 설계 정리  
코드 수정 없음 — 설계/분류/초안 문서 전용

---

## 1. 1차 샘플 추천 목록

> OCR/sample/ 내 PDF 4종을 페이지 수/크기로 식별 후 분류

### 1차 즉시 구현 대상 (extractor 개발 + GT 입력 병행)

| 샘플 파일 | 페이지 | 크기 | 추정 유형 | 역할 |
|---|---|---|---|---|
| `2.pdf` | 1페이지 | 161KB | 표준 단일 거래명세서 | **1차 주력 샘플** — 헤더 2블록 + 합계 추출 기준 |
| `3.pdf` | 1페이지 | 69KB | 청색 거래명세표 | **1차 보조 샘플** — 단순 폼 레이아웃, 정합성 검증용 |

### 구조 확인용 (1차 부분 처리 — p1만)

| 샘플 파일 | 페이지 | 크기 | 역할 |
|---|---|---|---|
| `4.pdf` | 2페이지 | 134KB | 2페이지 세트. 1차는 page 1만 처리. 다페이지 레이아웃 구조 확인 |

### 후속 단계용 (1차 범위 외)

| 샘플 파일 | 페이지 | 크기 | 사유 |
|---|---|---|---|
| `5.pdf` | 22페이지 | 1.3MB | 다페이지 병합 미구현. 전체 파싱 후속 단계로 이연 |

---

## 2. 후속 단계로 미룰 샘플 목록

| 파일 | 사유 | 1차 대응 방안 |
|---|---|---|
| `4.pdf` p2 | 2페이지 연속. 1차는 p1 단독 처리만 대상 | manifest notes에 "p1만 1차 처리" 명시 |
| `5.pdf` 전체 | 22페이지. 다페이지 병합/순서 처리 미구현 | manifest에 예약 등록, expectedStatus는 주석 |

---

## 3. invoice_statement 1차 필드 정의 요약

> 현황: `profiles.ts`에 `DocumentFieldKey` 및 `DOCUMENT_COLUMNS` 이미 정의 완료.  
> 타입 추가 불필요. 아래는 각 필드의 추출 전략 요약.

### 공급자 블록 (Supplier)

| 필드 키 | 한글명 | Required | 추출 전략 |
|---|---|---|---|
| `supplierCompany` | 공급자 회사명 | ✅ | "공급자" 레이블 아래 첫 텍스트 or 좌측 열 상단 |
| `supplierBizNumber` | 공급자 사업자번호 | ✅ | "등록번호" 레이블 + XXX-XX-XXXXX 패턴 (좌측 열) |
| `supplierRepresentative` | 공급자 대표자 | ☐ | "대표자" 레이블 우측 (좌측 블록 내) |
| `supplierAddress` | 공급자 주소 | ☐ | "주소" 레이블 우측 (좌측 블록 내) |

### 공급받는자 블록 (Buyer)

| 필드 키 | 한글명 | Required | 추출 전략 |
|---|---|---|---|
| `buyerCompany` | 구매자 회사명 | ✅ | "공급받는자" 레이블 아래 or 우측 열 상단 |
| `buyerBizNumber` | 구매자 사업자번호 | ☐ | "등록번호" 패턴 (우측 열) |
| `buyerRepresentative` | 구매자 대표자 | ☐ | "대표자" 레이블 (우측 블록 내) |
| `buyerAddress` | 구매자 주소 | ☐ | "주소" 레이블 (우측 블록 내) |

### 일자 / 금액

| 필드 키 | 한글명 | Required | 추출 전략 |
|---|---|---|---|
| `issueDate` | 발행일 | ✅ | "YYYY년 MM월 DD일" 또는 "YYYY-MM-DD" 패턴. 상단 또는 제목 우측 |
| `supplyAmount` | 공급가액 | ☐ | "공급가액" 레이블 우측 또는 합계 행 내 |
| `taxAmount` | 세액 | ☐ | "세액" or "부가세" 레이블 우측 |
| `totalAmount` | 합계금액 | ✅ | "합계금액" or "총액" 레이블 우측 (하단 합계 행) |

### 표 구조 감지

| 필드 키 | 한글명 | Required | 추출 전략 |
|---|---|---|---|
| `tableDetected` | 품목표 감지 | ✅ | bbox y-좌표 밀도 분석 + "규격" "단가" "수량" 헤더 시그널 |
| `rowCount` | 행 수 | ☐ | 품목표 행 카운트 (tableDetected=true일 때만) |
| `firstRowPreview` | 첫 행 미리보기 | ☐ | 품목표 첫 데이터 행 원문 텍스트 |

---

## 4. manifest item 초안

> 현재 ManifestItem 타입 기준 + 1차 전용 확장 필드 제안 포함.

### 현재 ManifestItem 타입 (profiles/testsets.ts)

```typescript
type ManifestItem = {
  filename: string;
  documentType: DocumentType;       // "invoice_statement"
  qualityTags: QualityTag[];
  difficulty: Difficulty;
  expectedStatus: string;
  notes?: string;
};
```

### 거래명세서용 확장 제안 (1차 구현 후 추가 예정)

```typescript
// 거래명세서 전용 확장 (ManifestItem 타입 확장 방향)
type InvoiceManifestItem = ManifestItem & {
  id: string;                        // 식별자 (e.g. "inv_001")
  expectedFields: boolean;           // ground_truth.documentFields 입력 여부
};
```

> **오늘 타입 수정 불필요.** 내일 extractor 구현 후 GT 입력 단계에서 추가.

### 실제 manifest.json 초안 (invoice_statement 전용)

```json
{
  "datasetId": "invoice_statement",
  "datasetRole": "document_type",
  "status": "draft",
  "description": "거래명세서 1차 검증셋. 헤더 2블록·합계·표 구조 감지 검증.",
  "items": [
    {
      "filename": "2.pdf",
      "documentType": "invoice_statement",
      "qualityTags": [],
      "difficulty": "easy",
      "expectedStatus": "selected",
      "notes": "단일 페이지 표준 거래명세서. 1차 주력 샘플. 헤더 2블록 + 합계 GT 입력 대상."
    },
    {
      "filename": "3.pdf",
      "documentType": "invoice_statement",
      "qualityTags": [],
      "difficulty": "easy",
      "expectedStatus": "selected",
      "notes": "청색 거래명세표 1장. 단순 폼 레이아웃. 1차 보조 샘플. GT 입력 대상."
    },
    {
      "filename": "4.pdf",
      "documentType": "invoice_statement",
      "qualityTags": [],
      "difficulty": "medium",
      "expectedStatus": "selected",
      "notes": "2페이지 거래명세서 세트. 1차는 page 1만 처리. 구조 확인용. GT는 p1 기준."
    },
    {
      "filename": "5.pdf",
      "documentType": "invoice_statement",
      "qualityTags": [],
      "difficulty": "hard",
      "expectedStatus": "selected",
      "notes": "22페이지 다페이지 PDF. 후속 단계용. 1차 extractor 범위 외. 다페이지 병합 구현 후 처리."
    }
  ]
}
```

---

## 5. 내일 Codex로 구현할 extractor 1차 범위

### 신규 파일

```
ocr-server/extractors/invoice_statement.py
```

### 함수 시그니처

```python
def extract_invoice_statement(lines: list[dict]) -> dict:
    """
    PaddleOCR lines → invoice_statement documentFields 추출.
    lines: [{"text": str, "bbox": [[x,y], ...], "score": float}, ...]
    반환: DocumentFieldKey 기준 dict (없으면 "" 또는 None)
    """
```

### 1차 구현 IN-SCOPE

| 항목 | 구현 내용 |
|---|---|
| 헤더 블록 분리 | x-좌표 중앙값(midpoint) 기준으로 supplier(좌) / buyer(우) 열 분리 |
| issueDate | 상단 YYYY년 MM월 DD일 or YYYY-MM-DD 패턴 탐색 |
| supplierCompany | "공급자" 레이블 이후 or 좌측 블록 최상단 텍스트 |
| supplierBizNumber | 좌측 블록 내 "등록번호" + XXX-XX-XXXXX 패턴 |
| supplierRepresentative | 좌측 블록 "대표자" 레이블 우측 |
| supplierAddress | 좌측 블록 "주소" 레이블 이후 |
| buyerCompany | "공급받는자" 레이블 이후 or 우측 블록 상단 |
| buyerBizNumber | 우측 블록 내 "등록번호" + XXX-XX-XXXXX 패턴 |
| buyerRepresentative | 우측 블록 "대표자" 레이블 우측 |
| buyerAddress | 우측 블록 "주소" 레이블 이후 |
| supplyAmount | "공급가액" 레이블 우측 숫자 |
| taxAmount | "세액" or "부가세" 레이블 우측 숫자 |
| totalAmount | "합계금액" or "합 계" 레이블 우측 숫자 |
| tableDetected | "규격" "단가" "수량" "금액" 헤더 시그널 존재 여부 |
| rowCount | 품목표 데이터 행 수 카운트 |
| firstRowPreview | 품목표 첫 번째 데이터 행 원문 텍스트 |

### 1차 구현 OUT-OF-SCOPE

| 항목 | 사유 |
|---|---|
| 품목표 전체 완전 파싱 | 행별 품목명/규격/단가/수량/금액 전체 → 2차 |
| 다페이지 병합 | 5.pdf 같은 22페이지 → 후속 단계 |
| Lot / 제조번호 / 유효기간 | 의약품/식품 특화 필드 → 2차 이후 |
| buyerBizNumber required 처리 | 일부 거래명세서에 미기재 → optional 유지 |
| PDF 레이아웃 분석 | 1차는 PaddleOCR OCR lines 기반만 |

### main.py 연동 방식

```python
# document_classifier가 "invoice_statement" 분류 시
# 아래 브랜치 추가 (main.py에 최소 추가)

from extractors.invoice_statement import extract_invoice_statement

if doc_type == "invoice_statement":
    document_fields = extract_invoice_statement(lines)
    result["documentFields"] = document_fields
```

> `document_classifier.py`에 "invoice_statement" 감지 시그널 추가 필요:  
> "거래명세서", "거래명세표", "공급자", "공급받는자" 등

---

## 6. 구현 시 주의할 점

### A. 2열 레이아웃 처리

- PaddleOCR는 y좌표 순으로 bbox를 반환함. 2열 레이아웃이면 좌우 열 텍스트가 **y순으로 뒤섞임**
- 반드시 `bbox[0][0]` (x 좌표) 기준으로 좌/우 열을 먼저 분리한 뒤 각 열 내에서 y순으로 처리
- 중앙 x 계산: `image_width / 2` 또는 모든 bbox x 분포의 중앙값

### B. 사업자번호 2개 구분

- 공급자와 공급받는자 모두 사업자번호 보유 → 동일 패턴(XXX-XX-XXXXX)이 2회 나옴
- x좌표로 좌측 = supplier, 우측 = buyer 분리 필수
- 기존 `business_number.py`의 `_validate_biz_number` 재활용 가능

### C. 금액 3종 혼재

- 거래명세서 하단에 공급가액 / 세액 / 합계금액이 나란히 있음
- 레이블 "공급가액" → supplyAmount, "세액" → taxAmount, "합계금액" → totalAmount
- 기존 영수증의 `totalAmount` 추출 로직과 충돌하지 않도록 별도 브랜치 처리

### D. 발행일 형식 다양성

- "2025년 11월 05일", "2025-11-05", "25.11.05" 등 형식 혼재
- 정규식: `r'(\d{4})[년\-\.](\d{1,2})[월\-\.](\d{1,2})[일]?'`
- 파싱 후 YYYY-MM-DD 정규화 권장

### E. 표 감지 신호

- 헤더 행 키워드: "품목", "규격", "단가", "수량", "금액", "공급가액"
- 이 중 3개 이상 같은 y범위 내 → `tableDetected = true`
- rowCount는 헤더 이후 유사 패턴(숫자+숫자 패턴) 연속 행 카운트

### F. document_classifier.py 수정 범위

- 수정 전 CLAUDE.md 확인 필수 (Do Not Modify 항목 재확인)
- 거래명세서 감지 시그널 추가는 새 분기/상수 추가 방식으로 최소화
- main.py의 기존 영수증/finance_slip 브랜치에 영향 없어야 함

### G. 기존 baseline/google 회귀 보호

- 거래명세서 extractor는 invoice_statement 분류 시에만 실행
- 영수증/finance_slip 경로 영향 없어야 함
- 구현 후 baseline_fast → google → baseline 순으로 회귀 검증 필수

---

## 7. 내일 Codex 작업 체크리스트

```
[ ] 1. document_classifier.py에 invoice_statement 감지 시그널 추가
[ ] 2. extractors/invoice_statement.py 신규 작성
[ ] 3. main.py에 invoice_statement 브랜치 최소 연결
[ ] 4. 2.pdf, 3.pdf OCR 실행 → ocr_cache.json 갱신
[ ] 5. 2.pdf, 3.pdf ground_truth.json documentFields 입력
[ ] 6. invoice_statement manifest.json 상태 in_progress로 갱신
[ ] 7. baseline_fast / google / baseline 회귀 검증
[ ] 8. SESSION_SUMMARY.md 업데이트
```
