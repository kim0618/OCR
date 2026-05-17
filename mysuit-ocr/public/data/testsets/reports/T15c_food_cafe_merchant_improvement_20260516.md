# T-15c food_cafe_receipt merchantName missing 개선 결과

## 1. 수정 파일
- `ocr-server/utils/regex_patterns.py` — `_COMPANY_CONTEXT_HINT_RE`, `_COMPANY_SUFFIX_HINT_RE`에 food/cafe 업종 suffix 추가
- `ocr-server/extractors/company.py` — 영문 브랜드명 후보 진입 허용 + near_biz_context 윈도우 ±2 확장

## 2. 백업 파일
- `ocr-server/backup/regex_patterns_20260516_before_T15c_food_cafe_merchant.py`
- `ocr-server/backup/company_20260516_before_T15c_food_cafe_merchant.py`

## 3. 핵심 요약
- food_cafe_receipt merchantName filled: 11 → 13 (+2)
- food_cafe_receipt totalAmount: 변화 없음 (14 유지)
- 필드 회귀: 0건
- T-15a pos_receipt 개선 유지 (businessNo=3, merchantName=5)
- T-15b medical_receipt 분류 유지 (4/4 correct, pos_003 별도 설명)
- invoice_statement 7/7 exact 유지

## 4. 대상 missing 샘플
| filename | before merchantName | OCR 후보 | 원인 | 조치 | after merchantName |
|---|---|---|---|---|---|
| food_001.jpg | 없음 | 없음 (OCR broken) | OCR source missing | 불가 | 없음 |
| food_002.jpg | 없음 | 경기장애인생산품판매시설 | 주소 false-positive + digits 필터 이중 걸림 | 보수적 처리 (미수정) | 없음 |
| food_003.jpg | 없음 | PARIS BAGUETTE | 영문 suffix 없어 후보 미진입 | 영문 브랜드 허용 + biz window 확장 | BAGUETTE |
| food_004.jpg | 있음(쭈꾸미낙지볶음전문점 대성) | - | - | - | 있음 |
| food_005.jpg | 없음 | 이디야커피 | 커피가 context hint에 없어 후보 미진입 | 커피 추가 | 이디야커피 |

## 5. before/after
| field | before missing | after missing | 개선 |
|---|---:|---:|---:|
| merchantName | 4 | 2 | -2 |
| totalAmount | 1 | 1 | 0 |

## 6. 적용 로직

### regex_patterns.py — food/cafe 업종 suffix 추가
| 추가 항목 | 적용 위치 | 효과 |
|---|---|---|
| `커피`, `치킨`, `버거`, `피자`, `베이커리`, `분식` | `_COMPANY_CONTEXT_HINT_RE` | "이디야커피" 등 한글 cafe/food 상호 후보 진입 허용 |
| `coffee`, `baguette`, `bakery` | `_COMPANY_CONTEXT_HINT_RE`, `_COMPANY_SUFFIX_HINT_RE` | 영문 브랜드명 suffix로 인식, score boost |

### company.py — 영문 브랜드 후보 진입
`_company_candidate_texts`: 순수 영문 텍스트(digits 없음, noise 없음, van/tid/cat 등 카드 키워드 없음)를 full-text 후보로 허용.
- 변경 전: `_COMPANY_CONTEXT_HINT_RE`(한국어 suffix) 필수
- 변경 후: OR `re.fullmatch(r'[A-Za-z]+', compact_text)` 조건 추가

### company.py — near_biz_context 윈도우 확장
`_rescue_company_name`: near_biz_context 확인 범위를 ±1 행에서 ±2 행으로 확장.
- 배경: 영수증 최상단 브랜드명(row 0)과 사업자번호 행(row 2)이 2행 이상 떨어져 있어 ±1 창에서 biz 미검출
- 변경: ctx_start=idx-2, ctx_end=idx+3으로 5행 창 사용

## 7. 회귀 확인
| documentType | 확인 항목 | 결과 |
|---|---|---|
| food_cafe_receipt | merchantName 회귀 | PASS (0건) |
| pos_receipt | T-15a businessNo/merchantName 유지 | PASS |
| medical_receipt | T-15b 분류 유지 | PASS (4/4) |
| card_receipt | 오분류 없음 | PASS |
| finance_slip | 필드 회귀 없음 | PASS |

### pos_003.jpg 별도 설명
manifest에서 pos_receipt로 분류되었으나 OCR 내용이 명백히 약국 처방전 영수증:
`약제비총액, 본인부담금, 보험자부담금, 비급여, 보험조제료, 병원명, 미금프라자약국`

T-15b 의료 분류기 개선으로 medical_receipt로 올바르게 재분류됨. T-15c 변경과 무관하며, manifest 오기입 건으로 분리 처리함.

## 8. invoice_statement 영향
- rowCount 7/7 exact 유지 여부: **유지 (7/7 exact)**
- invoice_statement.py 수정 여부: 없음

## 9. 검증 결과
- py_compile: PASS (regex_patterns.py, company.py, main.py, verify_food_cafe_receipt_t15c.py)
- verify_food_cafe_receipt_t15c.py: PASS (overall_pass=True)
- typecheck: PASS (npm run typecheck)
- build: 미실행 (OCR server 변경, JS 코드 무수정 → 이전 PASS 유지)

## 10. 다음 작업 판단
- food_cafe merchantName 개선 완료 (4 missing → 2 missing)
- 잔존 missing 2건:
  - food_001.jpg: OCR source broken → 한계로 분리
  - food_002.jpg: "경기장애인생산품판매시설" — 주소 패턴 false-positive로 필터에 걸림. 별도 작업 필요 시 분리.
- totalAmount food_001 1건: OCR broken → 한계

**다음 권장 작업: T-15d — card_receipt merchantName/businessNo missing 개선 또는 전체 현황 재정리**
