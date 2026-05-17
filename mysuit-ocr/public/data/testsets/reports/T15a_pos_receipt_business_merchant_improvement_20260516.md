# T-15a pos_receipt businessNo / merchantName missing 개선 결과

## 1. 수정 파일
- `ocr-server/extractors/business_number.py` — `_extract_biz_number_relaxed` 추가
- `ocr-server/utils/regex_patterns.py` — `_CONVENIENCE_STORE_NAME_RE` 업데이트 (점 옵션화)
- `ocr-server/extractors/company.py` — 토큰 루프에 `_COMPANY_SUFFIX_HINT_RE` 조건 추가
- `ocr-server/main.py` — import 추가, labeled context relaxed 시도, businessNo rescue pass 추가

## 2. 백업 파일
- `ocr-server/backup/business_number_20260516_before_T15a_pos_receipt_business_merchant.py`
- `ocr-server/backup/regex_patterns_20260516_before_T15a_pos_receipt_business_merchant.py`
- `ocr-server/backup/company_20260516_before_T15a_pos_receipt_business_merchant.py`
- `ocr-server/backup/main_20260516_before_T15a_pos_receipt_business_merchant.py`

## 3. 핵심 요약
- businessNo: 5 missing → 4 missing (+1 개선, pos_005 복구)
- merchantName: 3 missing → 2 missing (+1 개선, pos_006 복구)
- totalAmount: 변화 없음 (1 missing 유지)
- 회귀: 없음 (card/food_cafe/medical/finance_slip 전체 필드 유지)
- invoice_statement 7/7 exact 유지

## 4. 대상 샘플
| filename | missing before | OCR 후보 | 원인 | 조치 |
|---|---|---|---|---|
| pos_001.jpg | businessNo | 없음 (garbled) | OCR source missing | 불가 |
| pos_002.jpg | businessNo, merchantName | 없음 (헤더 없는 영수증) | OCR source missing | 불가 |
| pos_005.jpg | businessNo | `208-86-50913` | checksum 실패 (OCR 오류) | relaxed rescue로 복구 |
| pos_006.jpg | merchantName, businessNo, totalAmount | `기피운 행복을 만나다 GS25` | GS25 standalone 필터 차단 | _CONVENIENCE_STORE_NAME_RE 수정으로 복구 |
| google_fast/5.jpg | merchantName, businessNo | doc_type_mismatch | receipt_card로 오분류 | 미수정 (별도 분류기 이슈) |

## 5. before/after
| field | before missing | after missing | 개선 |
|---|---:|---:|---:|
| businessNo | 5 | 4 | -1 |
| merchantName | 3 | 2 | -1 |
| totalAmount | 1 | 1 | 0 |

## 6. 회귀 확인
| documentType | 확인 항목 | 결과 |
|---|---|---|
| card_receipt | merchantName, businessNo, totalAmount | PASS (회귀 없음) |
| food_cafe_receipt | merchantName, totalAmount | PASS (회귀 없음) |
| medical_receipt | merchantName, totalAmount | PASS (회귀 없음) |
| finance_slip | 전체 필드 | PASS (회귀 없음) |

## 7. invoice_statement 영향
- rowCount 7/7 exact 유지 여부: **유지 (7/7 exact)**
- invoice_statement.py 수정 여부: 없음 (수정 대상 아님)

## 8. 개선 내용 상세

### businessNo 개선 (pos_005.jpg)
OCR 원문: `208-86-50913 이칼수`
- 3-2-5 형식 구분자 필수 패턴 `[1-9]\d{2}[-\s.]\d{2}[-\s.]\d{5}` 추가
- `_extract_biz_number_relaxed`: 체크섬 없이 형식만으로 추출
- rescue 조건: 전화/주소가 이미 추출된 경우(비즈니스 정보 블록)에만 발동
- 전화번호 행 제외 guard: `_extract_phone_candidate` 양성인 행 skip

### merchantName 개선 (pos_006.jpg)
OCR 원문: `기피운 행복을 만나다 GS25`
1. `_CONVENIENCE_STORE_NAME_RE` 업데이트: `점` 옵션화 (`점?`)
   - 변경 전: `^(?:GS25|...)[가-힣A-Za-z0-9()]*점$`
   - 변경 후: `^(?:GS25|...)[가-힣A-Za-z0-9()]*점?$`
   - 효과: GS25 standalone이 체인스토어로 인식 → digits>1 guard 통과
2. `_company_candidate_texts` 토큰 루프: `_COMPANY_SUFFIX_HINT_RE` 조건 추가
   - 효과: GS25(=suffix hint에 포함)가 후보 리스트에 진입

## 9. 검증 결과
- py_compile: PASS (business_number.py, regex_patterns.py, company.py, main.py, verify_pos_receipt_t15a.py)
- verify_pos_receipt_t15a.py: PASS
- typecheck: PASS (npm run typecheck)
- build: 미실행 (OCR server 변경, JS 코드 무수정 → 이전 PASS 유지)

## 10. 다음 작업 판단
- pos_receipt businessNo: 4 missing 잔존 (pos_001/pos_002 OCR source missing, pos_006 OCR garbled, google_fast/5.jpg 오분류)
- pos_receipt merchantName: 2 missing 잔존 (pos_002 OCR source missing, google_fast/5.jpg 오분류)
- google_fast/5.jpg 오분류 → **T-15b medical_receipt 분류 mismatch** 또는 별도 분류기 이슈 작업으로 분리
- pos_006 totalAmount missing → OCR source 자체가 없어서 불가 → warning/한계로 분리
- 추가 개선 여지: food_cafe_receipt merchantName 4 missing, card_receipt merchantName/businessNo 2 missing

**다음 권장 작업: T-15b medical_receipt 분류 mismatch 개선**
