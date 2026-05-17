# T-15d card_receipt merchantName / businessNo / totalAmount missing 개선 결과

## 1. 수정 파일
- `ocr-server/utils/regex_patterns.py` — `_COMPANY_LABEL_RE`에 `점\s*명` 추가 (가맹점명 OCR garble 대응)

## 2. 백업 파일
- `ocr-server/backup/regex_patterns_20260516_before_T15d_card_receipt_fields.py`

## 3. 핵심 요약

### T-14 기준 대비 T-15a~T-15d 전체 개선 (receipt_generalization 기준)
| 항목 | 개선 |
|---|---|
| card_receipt merchantName | T-14 2 missing → T-15d 1 missing (-1) |
| card_receipt businessNo | T-14 2 missing → **T-15a에서 0 missing** (T-15d에서 확인) |
| pos_receipt businessNo | T-14 5 missing → T-15a 4 missing (-1) |
| pos_receipt merchantName | T-14 3 missing → T-15a 2 missing (-1) |
| medical_receipt 정분류 | T-14 2/6 → T-15b 5/6 (+3) |
| food_cafe merchantName | T-14 4 missing → T-15c 2 missing (-2) |

### 이번 T-15d 결과
- card_receipt merchantName: 11 → 12 (+1, card_002 복구)
- card_receipt businessNo: 11 → 13 (+2, T-15a rescue pass로 card_001+card_002 모두 복구)
- card_receipt totalAmount: 11 → 11 (변화 없음, 이미 모두 채워짐)
- 필드 회귀: 0건
- invoice_statement 7/7 exact 유지

## 4. 대상 missing 샘플
| filename | missing before | OCR 후보 | 원인 | 조치 | after |
|---|---|---|---|---|---|
| card_001.jpg | merchantName, businessNo, phone | businessNo: 가점시업지번호 79161161/140-09-20255 | businessNo: checksum 실패 → T-15a relaxed rescue로 복구. merchantName: "송명( 이" OCR 불완전 | businessNo: T-15a에서 이미 복구. merchantName: 복구 불가 | businessNo='140-09-20255' |
| card_002.jpg | merchantName, businessNo, address | businessNo: 306-13-63556. merchantName: 기명점명 당신만식부께 | businessNo: checksum 실패. merchantName: 가맹점명 라벨 OCR garble(기명점명). address: 충청남도 → 충심남도 OCR garble | businessNo: T-15a 복구. merchantName: 점명 라벨 추가. address: 불가 | businessNo='306-13-63556', merchantName='당신만식부께' |

## 5. before/after
| field | before missing | after missing | 개선 |
|---|---:|---:|---:|
| merchantName | 2 | 1 | -1 |
| businessNo | 2 | 0 | **-2** (T-15a 복구 확인) |
| totalAmount | 0 | 0 | 0 |

## 6. 적용 로직

### regex_patterns.py — _COMPANY_LABEL_RE에 점명 추가
```python
_COMPANY_LABEL_RE = re.compile(
    r'(?:상호\s*명?|가맹점\s*명|회사\s*명|...|판매자|공급자|점\s*명)(?!\s*(?:성명|명|번호|주소))\s*[:;]?',
    re.I,
)
```

**왜 점명 추가가 필요한가**:
- OCR에서 "가맹점명" → "기명점명" (가→기, 맹→명) 변환이 발생
- 기존 `가맹점\s*명` 패턴은 "기명점명"을 인식하지 못함
- "기명점명" 끝 2글자인 "점명"을 라벨로 인식하면 이후 텍스트를 상호명으로 추출 가능
- 부정형 예외: `(?!\s*(?:성명|명|번호|주소))` 가드로 점명번호, 점명주소 등 오인식 방지

**note**: card_002 merchantName="당신만식부께"는 garbled OCR이지만 "가맹점명" 행의 실제 텍스트를 추출한 것으로, 완전한 복구는 아니나 빈 값보다 정보가 있음.

### T-15a businessNo rescue pass (이미 적용)
- relaxed biz_number 추출 (구분자 필수, checksum 없이)
- phone/address 컨텍스트가 있을 때 rescue pass 발동
- card_001, card_002 모두 businessNo 복구 완료 (T-15a 시점)

## 7. 회귀 확인
| documentType | 확인 항목 | 결과 |
|---|---|---|
| card_receipt | 기존 merchantName/businessNo/totalAmount 유지 | PASS |
| pos_receipt | T-15a businessNo/merchantName 유지 | PASS |
| medical_receipt | T-15b 분류 유지 (4/4 correct) | PASS |
| food_cafe_receipt | T-15c merchantName 유지 | PASS |
| finance_slip | 필드 회귀 없음 | PASS |

## 8. invoice_statement 영향
- rowCount 7/7 exact 유지 여부: **유지 (7/7 exact)**
- invoice_statement.py 수정 여부: 없음

## 9. 검증 결과
- py_compile: PASS (regex_patterns.py, main.py, verify_card_receipt_t15d.py)
- verify_card_receipt_t15d.py: PASS (overall_pass=True)
- typecheck: PASS (npm run typecheck)
- build: 미실행 (OCR server 변경, JS 코드 무수정)

## 10. 다음 작업 판단
- card_receipt 개선 완료
  - merchantName: 2 missing → 1 missing (card_001 OCR 불완전으로 복구 불가 → 한계로 분리)
  - businessNo: 2 missing → 0 missing (T-15a rescue pass로 완전 복구)
  - totalAmount: 0 missing (이미 완전)

**T-15a~T-15d 전체 요약 결론:**
T-14 baseline 이후 4번의 개선 작업으로 receipt_generalization 기준:
- pos_receipt businessNo: 5→4, merchantName: 3→2
- medical_receipt 정분류: 2→5 (of 6)
- food_cafe merchantName: 4→2
- card_receipt businessNo: 2→0, merchantName: 2→1

모든 작업에서 invoice_statement 7/7 exact 유지, 회귀 0건.

**다음 권장 작업: T-15e — finance_slip selected/suppressed 정책 분리 또는 T-15 시리즈 완료 후 전체 현황 리포트 작성**
