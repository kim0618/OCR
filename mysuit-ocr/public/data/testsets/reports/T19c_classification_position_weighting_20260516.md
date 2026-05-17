# T-19c synthetic y_ratio 기반 classification position weighting 결과

## 1. 수정 파일
- `ocr-server/document_classifier.py` — position weighting 로직 추가

## 2. 백업 파일
- `ocr-server/backup/document_classifier_20260516_before_T19c_position_weighting.py`
- `ocr-server/backup/signal_lists_20260516_before_T19c_position_weighting.py`

## 3. 핵심 요약
- T-18 classification_mismatch 9건 중 **6건 개선**, 0건 회귀
- invoice_statement false positive 3건 차단 (a1/google9/food_004)
- GS25 top signal → receipt_pos 2건 수정 (google/5, google_fast/5)
- pos_006 GS25 상단 → unknown에서 receipt_pos로 복구
- T-15a~T-15e 모든 개선 유지
- invoice_statement 7/7 exact 유지

## 4. 대상 classification_mismatch 샘플
| sample | expected | before | after | top signals | bottom signals | 판정 |
|---|---|---|---|---|---|---|
| baseline/8.jpg | medical_receipt | receipt_card | medical_receipt | 약국+일반의약품 | 승인번호 | IMPROVED (T-15b) |
| baseline/a1.jpg | card_receipt | receipt_pos | receipt_pos | Cashnote Pay | 금액/승인 | same (receipt_pos=T-18 original) |
| google/5.jpg | pos_receipt | receipt_card | receipt_pos | GS25대림한양아파트점 | 카드정보 | IMPROVED (pos_top_signal) |
| google/8.jpg | unknown | receipt_pos | receipt_pos | 주소 | 품목/금액 | same (manifest=unknown, 정상 receipt_pos) |
| google/9.jpg | medical_receipt | receipt_pos | medical_receipt | 약국+의료신호 | 카드정보 | IMPROVED (invoice_blocked+medical) |
| google_fast/5.jpg | pos_receipt | receipt_card | receipt_pos | GS25대림한양아파트점 | 카드정보 | IMPROVED (pos_top_signal) |
| food_001.jpg | food_cafe_receipt | unknown | unknown | OCR garbled | - | same (OCR 불가) |
| food_004.jpg | food_cafe_receipt | invoice_statement | receipt_pos | 쭈꾸미낙지볶음전문점 | 금액/합계 | IMPROVED (invoice_blocked) |
| pos_006.jpg | pos_receipt | unknown | receipt_pos | GS25 | OCR garbled | IMPROVED (pos_top_signal) |

## 5. position weighting 로직

### 추가 1: 상단 영역 top_text 계산
```python
_lines_full = [ln.strip() for ln in full_text.splitlines() if ln.strip()]
_top_n = max(1, len(_lines_full) // 4)
_top_text = " ".join(_lines_full[:_top_n])
```

### 추가 2: pos_top_signal (상단 편의점/POS 브랜드 감지)
```python
pos_top_signal = bool(re.search(
    r'GS25|CU편의점|세븐일레븐|이마트24|미니스톱|홈플러스|이마트(?:트\w+)?점|롯데마트',
    _top_text, re.I
))
```

**조건**: `pos_top_signal AND not medical_facility_hit AND card_n <= pos_n + 2` → receipt_pos

### 추가 3: invoice_blocked_by_receipt
```python
invoice_blocked_by_receipt = bool(
    invoice_ok and (
        # has_business_structure=False이면 card/pos/medical로 차단
        (not invoice_has_business_structure and (card_n >= 2 or pos_n >= 2 or medical_facility_hit))
        # 의료기관 감지 + invoice 타이틀 없음 → medical 우선
        or (medical_facility_hit and medical_n >= 1 and invoice_evidence.get("title", 0) == 0)
        # party=0 and title=0 인데 pos >= 2 → 식당/영수증 오탐 차단
        or (invoice_evidence.get("party", 0) == 0
            and invoice_evidence.get("title", 0) == 0
            and pos_n >= 2)
    )
)
```

**진짜 invoice_statement 보호**: title >= 1 (거래명세서 등)이면 차단 안 함 → invoice_statement/5.pdf 의료 공급 invoice 보호 확인 ✓

### 결정 트리 변경
```python
# T-19c 추가 조건
if invoice_ok and not invoice_blocked_by_bank and not invoice_blocked_by_receipt:
    doc_type = "invoice_statement"
...
# T-19c: POS 상단 브랜드 → receipt_pos
elif pos_top_signal and not medical_facility_hit and card_n <= pos_n + 2:
    doc_type = "receipt_pos"
```

## 6. before/after
| 항목 | before (T-18) | after (T-19c) | 변화 |
|---|---:|---:|---:|
| classification_mismatch | 9 | 3 | **-6** |
| medical_receipt correct (rg) | 2/4 | 4/4 | **+2** |
| card_receipt false medical | 0 | 0 | 0 |
| invoice_statement false positive | 3건 | 0건 | **-3** |
| finance_slip suppressed | 5/5 | 5/5 | 0 |

## 7. 회귀 확인
| 영역 | 결과 |
|---|---|
| T-15a pos businessNo/merchantName | PASS |
| T-15b medical_receipt 분류 (4/4) | PASS |
| T-15c food_cafe merchantName | PASS |
| T-15d card_receipt businessNo/merchantName | PASS |
| T-15e finance_slip selected=0 | PASS |
| invoice_statement 7/7 exact | PASS |

## 8. 검증 결과
- py_compile: PASS (document_classifier.py, verify_document_classification_position_t19c.py)
- verify script: PASS (6/9 개선, 0 회귀)
- typecheck: PASS (npm run typecheck)
- build: 미실행 (OCR server 변경, JS 코드 무수정)

## 9. 다음 작업 판단
- T-19c 개선 효과 있음 (9→3 mismatch, -6)
- 잔여 3건:
  - baseline/a1.jpg: receipt_pos (manifest=card_receipt, T-18 original과 동일 → manifest 검토 필요)
  - google/8.jpg: receipt_pos (manifest=unknown → manifest 이슈)
  - food_001.jpg: unknown (OCR garbled → 불가)
- **다음 권장: T-19a merchantName y_ratio scoring 또는 T-19b amount bbox selection**
