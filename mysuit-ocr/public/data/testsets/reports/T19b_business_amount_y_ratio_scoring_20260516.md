# T-19b synthetic y_ratio 기반 businessNo / totalAmount candidate scoring 결과

## 1. 수정 파일
- `ocr-server/main.py` — `_apply_doc_type_amount_policy`에 receipt bare 음수 score + 1000만원 이상 억압 추가

## 2. 백업 파일
- `ocr-server/backup/main_20260516_before_T19b_business_amount_y_ratio.py`

## 3. 핵심 요약
- **pos_006 totalAmount false positive 수정**: "22,719,138" (T-19c 부작용) → "" (올바르게 비움)
- businessNo: T-14 기준 누적 5→8 (+3, T-15a relaxed rescue 포함)
- totalAmount: 15→15 (0 변화, false positive 제거 후 동일 수준 유지)
- 회귀: 0건
- T-15a~T-15e, T-19a, T-19c, invoice_statement 7/7 모두 PASS

## 4. 대상 샘플
| sample | documentType | field | before | after | OCR 후보 | y_ratio 근거 | 판정 |
|---|---|---|---|---|---|---|---|
| pos_006.jpg | pos_receipt | totalAmount | 22,719,138 (T-19c 부작용) | "" | "22719138" (단말기ID) | bare+score-20+금액≥1000만 | **FALSE POSITIVE 수정** |
| card_001.jpg | card_receipt | businessNo | "" | "140-09-20255" | 가점시업지번호 row | T-15a relaxed rescue | (이전 개선) |
| card_002.jpg | card_receipt | businessNo | "" | "306-13-63556" | 사업자번호 row | T-15a relaxed rescue | (이전 개선) |
| pos_005.jpg | pos_receipt | businessNo | "" | "208-86-50913" | 이마트 충주점 row | T-15a relaxed rescue | (이전 개선) |
| medical_001~003, pos_001/002/006 | - | businessNo | "" | "" | OCR source missing/garbled | 복구 불가 | source_missing으로 분리 |

## 5. businessNo scoring 로직
**T-19b 직접 변경 없음** — T-15a에서 이미 적용된 relaxed rescue pass가 businessNo 개선의 주요 경로. OCR source missing/garbled 케이스는 복구 불가능.

**OCR source missing 케이스 최종 분리:**
| 샘플 | 이유 |
|---|---|
| medical_001.jpg | OCR에 사업자번호 라벨만 있고 숫자 없음 |
| medical_002.jpg | OCR에 사업자번호 없음 (동물병원 영수증) |
| medical_003.jpg | OCR에 사업자번호 없음 (수의원 처방영수증) |
| pos_001.jpg | OCR garbled, 사업자번호 원문 복구 불가 |
| pos_002.jpg | OCR에 헤더 없음, 마트 반품정책만 존재 |
| pos_006.jpg | OCR garbled, 사업자번호 원문 복구 불가 |

## 6. totalAmount scoring 로직 (T-19b 신규)
**문제**: T-19c에서 pos_006.jpg가 unknown → receipt_pos로 재분류됨. 기존 policy는 receipt_pos에서 negative score bare 후보도 값을 유지 → "22,719,138" 오탐 발생.

**해결**: `_apply_doc_type_amount_policy`에 추가:
```python
if amount_value and sel and sel.get("pattern") == "bare" and sel.get("score", 0) < 0:
    if doc_type in ("receipt_pos", "receipt_card"):
        amount_int = int(re.sub(r"[,\s원₩]", "", amount_value) or "0")
        if amount_int >= 10_000_000:  # 1000만원 이상
            amount_value = ""  # 번호/ID 오탐 방지
```

**조건 설계 이유**:
- `pattern == "bare"`: comma 형식 없는 숫자 → 실제 합계 금액보다 번호류 가능성 높음
- `score < 0`: 합계라벨/comma형식 등 금액 근거 전혀 없음
- `amount >= 10,000,000`: 일반 영수증 합계 금액 범위 초과 (10 million won = ~7,500 USD)
- `pos_001 "18,308"`처럼 소액 bare는 유지 (score=-20이라도 금액 범위가 합리적)

## 7. before/after
| 항목 | T-14 before | T-19b after | 변화 |
|---|---:|---:|---:|
| businessNo missing (rg) | 9 | 6 | -3 (T-15a 포함 누적) |
| totalAmount missing (rg) | 4 | 4 | 0 |
| totalAmount false positive | 0 | **0** (T-19c 부작용 제거) | 수정 |

## 8. 회귀 확인
| 영역 | 결과 |
|---|---|
| T-15a pos businessNo/merchantName | PASS |
| T-15b medical_receipt 분류 (4/4) | PASS |
| T-15c food_cafe merchantName | PASS |
| T-15d card_receipt businessNo/merchantName | PASS |
| T-15e finance_slip selected=0 | PASS |
| T-19a merchantName (+6 누적) | PASS |
| T-19c classification (pos_006=receipt_pos) | PASS |
| invoice_statement 7/7 exact | PASS |

## 9. 검증 결과
- py_compile: PASS (main.py, verify_business_amount_y_ratio_t19b.py)
- verify script: PASS (overall_pass=True)
- typecheck: PASS (npm run typecheck)
- build: 미실행 (OCR server 변경, JS 코드 무수정)

## 10. 다음 작업 판단
- **T-19b 핵심 개선**: pos_006 totalAmount false positive 제거 (T-19c 부작용 수정)
- businessNo 잔여 6건: 모두 OCR source missing/garbled → parser 복구 불가, 한계로 분리 완료
- totalAmount 잔여 missing 4건: food_001(OCR broken), food_002/medical_001(label만 있음) 등 OCR 한계

**다음 권장 작업: T-20 전처리 실험 또는 T-19 series final audit (T-16 형식 재집계)**
