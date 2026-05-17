# T-15b medical_receipt 분류 mismatch 개선 결과

## 1. 수정 파일
- `ocr-server/signal_lists.py` — MEDICAL_SIGNALS 개선 (boundary 수정 + 신호 추가)
- `ocr-server/document_classifier.py` — medical_facility_hit 감지 + 결정 트리 규칙 추가

## 2. 백업 파일
- `ocr-server/backup/signal_lists_20260516_before_T15b_medical_receipt_classification.py`
- `ocr-server/backup/document_classifier_20260516_before_T15b_medical_receipt_classification.py`

## 3. 핵심 요약
- medical_receipt 정분류: 2/6 → 5/6 (+3 개선)
- card_receipt 오분류 발생: 0건 (회귀 없음)
- 필드 회귀: 0건
- invoice_statement 7/7 exact 유지
- T-15a pos_receipt businessNo/merchantName 개선 유지

## 4. 대상 오분류 샘플
| filename | expected | before doc_type | after doc_type | medical signal | card signal | 판정 |
|---|---|---|---|---|---|---|
| baseline/8.jpg | medical_receipt | receipt_card | medical_receipt | 약국+일반의약품+의약품(3) / facility_hit=True | 7 | 개선 |
| medical_003.jpg | medical_receipt | receipt_card | medical_receipt | 진료비+처방(2) | 1(layout) | 개선 |
| medical_004.jpg | medical_receipt | receipt_card | medical_receipt | 조제+의약품+대한약사회(3) | 3 | 개선 |
| medical_001.jpg | medical_receipt | medical_receipt | medical_receipt | 4 | 0 | 유지 |
| medical_002.jpg | medical_receipt | medical_receipt | medical_receipt | 3 | 1 | 유지 |
| google/9.jpg | medical_receipt | receipt_pos | (재실행 불가) | live RunAll 불가 | - | 미확인 |

## 5. 분류 로직 변경

### signal_lists.py — MEDICAL_SIGNALS 개선
| 변경 | 내용 | 이유 |
|---|---|---|
| `\b약국\b` → `약국` | word boundary 제거 | Python 3 re에서 한글은 `\w`이므로 한글끼리 이어진 "온누리약국"에서 `\b` 경계 미작동 |
| `\b의원\b` → `의원` | 동일 이유 | "XX의원"에서 `\b의원\b` 미매칭 |
| 중복 `r'진찰료'` 제거 | 2개 → 1개 | 중복 패턴 정리 |
| `r'처방'` 추가 | 처방전 없이도 처방 키워드 인식 | medical_003 vet clinic 영수증에서 처방 귀약/처방 안약 등 검출 |
| `r'조제'` 추가 | 조제의약품 인식 | medical_004 조제의약품 검출 |
| `r'일반의약품'`, `r'의약품'` 추가 | 약국 POS 대표 키워드 | baseline/8.jpg 약국 영수증에서 일반의약품 검출 |
| `r'대한약사회'` 추가 | 한국 약국 영수증 표준 하단 문구 | medical_004 약국 영수증 보조 신호 |

### document_classifier.py — 결정 트리 규칙 추가
```python
# 새 규칙: 의료기관 이름(약국/의원/병원) + 의료 시그널 1개 이상
# 카드 결제 방법과 무관하게 medical_receipt 우선
elif medical_facility_hit and medical_n >= 1:
    doc_type = "medical_receipt"
```

의료기관 감지 패턴: `약국|의원|동물병원|(?<=[가-힣])병원(?![가-힣])`

배경: 약국/병원에서 카드 결제 시 EDC 매출전표 형식이 인쇄되어 카드 시그널이 7까지 올라가도,
      약국 이름(약국)이 OCR에 있고 의료 시그널이 1개 이상이면 의료 영수증으로 확정.

## 6. 필드 영향
| filename | 분류 변화 | 영향 |
|---|---|---|
| baseline/8.jpg | receipt_card → medical_receipt | 필드 추출 로직 경로 변경. 필드값은 T-14 기준 merchantName/businessNo 등 모두 filled 유지 |
| medical_003.jpg | receipt_card → medical_receipt | 동물병원 영수증. 기존 필드 유지 (totalAmount 122,850 etc.) |
| medical_004.jpg | receipt_card → medical_receipt | 약국 영수증. 기존 필드 유지 |

분류 변경이 필드 추출 품질을 역전시키지 않음 (field_regressions = 0건).

## 7. 회귀 확인
| documentType | 확인 항목 | 결과 |
|---|---|---|
| card_receipt | medical_receipt로 오분류 여부 | PASS (0건) |
| food_cafe_receipt | 핵심 필드 회귀 | PASS |
| finance_slip | 핵심 필드 회귀 | PASS |
| pos_receipt | T-15a businessNo/merchantName 개선 유지 | PASS |

## 8. invoice_statement 영향
- rowCount 7/7 exact 유지 여부: **유지 (7/7 exact)**
- invoice_statement.py 수정 여부: 없음

## 9. 검증 결과
- py_compile: PASS (signal_lists.py, document_classifier.py, verify_medical_receipt_classification_t15b.py)
- verify_medical_receipt_classification_t15b.py: PASS (overall_pass=True)
- typecheck: PASS (npm run typecheck)
- build: 미실행 (OCR server 변경, JS 코드 무수정 → 이전 PASS 유지)

## 10. 다음 작업 판단
- medical_receipt 개선 완료 (3/4 mismatch 수정, 1건 google/9.jpg는 live runall 재실행 필요)
- google/9.jpg: receipt_pos → medical_receipt 전환 예상 (약국 이름 있고 facility_hit 조건 충족 가능)
  → 다음 live RunAll 시점에 자동 적용될 것
- 잔존: 추가 개선 가능한 항목:
  - food_cafe_receipt merchantName 4 missing
  - card_receipt merchantName/businessNo 2 missing
  - medical_receipt merchantName 2 missing (OCR source garbled)

**다음 권장 작업: T-15c — food_cafe_receipt merchantName missing 개선 또는 card_receipt mismatch**
