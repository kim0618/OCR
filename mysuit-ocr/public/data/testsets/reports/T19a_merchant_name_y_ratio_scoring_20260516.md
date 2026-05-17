# T-19a synthetic y_ratio 기반 merchantName candidate scoring 결과

## 1. 수정 파일
- `ocr-server/utils/regex_patterns.py` — `_COMPANY_CONTEXT_HINT_RE`, `_COMPANY_SUFFIX_HINT_RE`에 의료기관/시설 suffix 추가
- `ocr-server/extractors/company.py` — 복합 토큰 한글 prefix 분리 로직 + `경기` 단독 차단 → `경기도`로 보수화

## 2. 백업 파일
- `ocr-server/backup/company_20260516_before_T19a_merchant_y_ratio.py`
- `ocr-server/backup/regex_patterns_20260516_before_T19a_merchant_y_ratio.py`

## 3. 핵심 요약
- T-19a 수정으로 2건 추가 개선 (medical_002, food_002)
- T-14 기준 누적: merchantName filled 7→13 (+6, T-15c/T-19c/T-19a 합산)
- 회귀: 0건
- T-15a~T-15e, T-19c 전체 PASS
- invoice_statement 7/7 exact 유지

## 4. 대상 merchantName 샘플
| sample | documentType | before | after (T-19a) | OCR 후보 | y_ratio 근거 | 판정 |
|---|---|---|---|---|---|---|
| medical_002.jpg | medical_receipt | 없음 | 하나동물병원 | y=0.0 (최상단) | 병원 suffix 추가 → 최상단 후보 score 43 | IMPROVED (T-19a) |
| food_002.jpg | food_cafe_receipt | 없음 | 경기장애인생산품판매시설 | y=0.1 (상단) | 시설 suffix 추가 + 경기 단독 차단 해제 | IMPROVED (T-19a) |
| food_003.jpg | food_cafe_receipt | 없음 | BAGUETTE | y=0.0 (최상단) | T-15c/T-19c에서 수정 완료 | (이전 개선) |
| food_005.jpg | food_cafe_receipt | 없음 | 이디야커피 | y=0.02 (최상단) | T-15c 커피 suffix | (이전 개선) |
| card_002.jpg | card_receipt | 없음 | 당신만식부께 | - | T-15d 점명 라벨 | (이전 개선) |
| pos_006.jpg | pos_receipt | 없음 | GS25 | y=0.0 (최상단) | T-19c pos_top_signal | (이전 개선) |

## 5. scoring 로직 변경 내용

### Fix 1: regex_patterns.py — 의료기관/시설 suffix 추가
`_COMPANY_CONTEXT_HINT_RE` 및 `_COMPANY_SUFFIX_HINT_RE`에 추가:
- `병원` — 하나동물병원, 삼성병원 등 병원명 suffix
- `의원` — 내과의원, 피부과의원 등 클리닉 suffix
- `한의원` — 한방의원
- `동물병원` — 수의원 suffix
- `시설` — 경기장애인생산품판매시설 등 공공시설 suffix

**효과**: "하나동물병원" → ends with "병원" → `_COMPANY_CONTEXT_HINT_RE` 매칭 → 후보 리스트 진입 → score ~43 → ACCEPTED

### Fix 2: company.py — 복합 토큰 한글 prefix 분리
토큰 루프에 복합 토큰(예: "경기장애인생산품판매시설(Ensemble)124") 처리 추가:
- 전체 토큰이 hint 매칭 실패 시, 한글 3글자 이상 prefix만 분리하여 재체크
- 한글 prefix가 context/suffix hint에 매칭되면 prefix만 후보로 등록

**효과**: "경기장애인생산품판매시설(Ensemble)124" → full token hint 실패 → kr_prefix "경기장애인생산품판매시설" → "시설" suffix 매칭 → 후보 등록

### Fix 3: company.py — `경기` 단독 차단 보수화
기존 `_is_bad_company_candidate`의 하드코딩 차단에서 `경기` → `경기도` 변경:
- 기존: `if re.search(r'...|경기', compact)` → "경기"로 시작하는 모든 후보 차단
- 변경: `if re.search(r'...|경기도', compact)` → "경기도" (주소 표현)만 차단
- "경기장애인생산품판매시설"은 기관명 → 정상 추출 가능

## 6. before/after
| 항목 | T-14 before | T-19a after | 변화 |
|---|---:|---:|---:|
| merchantName missing (rg) | 12 | 6 | -6 (누적) |
| T-19a 기여 | - | -2 | -2 |
| false positive | 0 | 0 | 0 |

## 7. 회귀 확인
| 영역 | 결과 |
|---|---|
| T-15a pos businessNo/merchantName | PASS |
| T-15b medical_receipt 분류 (4/4) | PASS |
| T-15c food_cafe merchantName | PASS |
| T-15d card_receipt businessNo/merchantName | PASS |
| T-15e finance_slip selected=0 | PASS |
| T-19c classification_mismatch 개선 | PASS |
| invoice_statement 7/7 exact | PASS |

## 8. 검증 결과
- py_compile: PASS (regex_patterns.py, company.py, main.py, verify_merchant_name_y_ratio_t19a.py)
- verify script: PASS (merchantName +6 누적, 회귀 0)
- typecheck: PASS (npm run typecheck)
- build: 미실행 (OCR server 변경, JS 코드 무수정)

## 9. 다음 작업 판단
- merchantName 개선 효과 있음 (T-19a 기여 +2)
- 잔여 merchantName missing 케이스:
  - medical_001.jpg: OCR에 상호명 없음 → 불가
  - card_001.jpg: OCR 불완전 → 불가
  - food_001.jpg: OCR broken → 불가
  - pos_002.jpg: OCR에 상호명 없음 → 불가

**다음 권장 작업: T-19b — businessNo/totalAmount y_ratio scoring 또는 T-20 전처리 개선**
