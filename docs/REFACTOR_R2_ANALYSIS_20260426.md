# REFACTOR R2 PRE-MOVE ANALYSIS 2026-04-26

Phase R2 (field extractor 분리) 실제 이동 전 사전 분석 문서.
계획 문서: [docs/REFACTOR_PLAN_20260426.md](REFACTOR_PLAN_20260426.md)
선행 단계: R1 (utils 분리) 완료 — [REFACTOR_R1A](REFACTOR_R1A_RESULT_20260426.md), [REFACTOR_R1B](REFACTOR_R1B_RESULT_20260426.md), [REFACTOR_R1C_3](REFACTOR_R1C_3_RESULT_20260426.md), [REFACTOR_R1D](REFACTOR_R1D_RESULT_20260426.md)

본 문서는 분석만 수행하며, **코드는 어떤 것도 수정하지 않는다.**

---

## 1. R2 목적

R1 (utils 분리) 이 끝나 main.py 의 순수 helper 들은 모두 `ocr-server/utils/` 하위로 격리되었다. R2 는 그 다음으로, **field extractor 함수들** 을 별도 모듈로 분리한다.

목표 디렉터리 구조 (계획 문서 §3 기준):

```
ocr-server/extractors/
  __init__.py
  common.py           # _bad_top_text_candidate, _extract_until_next_label
  business_number.py  # _validate_biz_number, _extract_biz_number
  phone.py            # 5개 phone helper (rep_phone_pair 제외)
  representative.py   # _is_bad_representative_candidate, _extract_rep_phone_pair
  address.py          # 5개 address helper
  company.py          # company 관련 8개 함수 + _rescue_company_name
  fields_pipeline.py  # _extract_fields_from_rows, _repair_remaining_top_fields_from_text_lines
                      # (단, extract_receipt_fields 자체는 R5 response_builder 작업 영역)
```

R2 는 R1 보다 위험하다. 이유:
- 함수가 직접 OCR 추출 결과를 결정 (위치 이동만으로도 import 순서/시점 차이 가능)
- 함수 간 cross-group 의존성이 다수 (cross-group 호출 7곳 식별)
- import 순환 가능성 존재
- baseline final-selection policy 와 직접 연결

---

## 2. 분석 대상 함수 목록 (총 22개)

### 2.1 business_number group (2개)

| # | 함수 | 라인 | 역할 |
|---|---|---|---|
| 1 | `_validate_biz_number` | 61-69 | 10자리 사업자번호 체크섬 검증 |
| 2 | `_extract_biz_number` | 72-80 | 텍스트에서 사업자번호 추출 + 체크섬 검증 |

### 2.2 phone group (6개)

| # | 함수 | 라인 | 역할 |
|---|---|---|---|
| 3 | `_normalize_phone_digits` | 152-153 | 숫자만 추출 |
| 4 | `_format_phone_digits` | 156-167 | 한국식 하이픈 포맷 |
| 5 | `_valid_phone_digits` | 170-175 | 유효 전화번호 판정 (9~11자리) |
| 6 | `_valid_labeled_phone_digits` | 178-183 | 레이블 있을 때 02-xx-xxxx 등 완화 |
| 7 | `_extract_phone_candidate` | 186-210 | 텍스트에서 전화번호 후보 추출 |
| 8 | `_extract_rep_phone_pair` | 213-222 | "이름(전화)" 패턴 추출 (representative 의존) |

### 2.3 address group (5개)

| # | 함수 | 라인 | 역할 |
|---|---|---|---|
| 9 | `_extract_address_fragment` | 129-138 | 지역명 시작 주소 추출 |
| 10 | `_clean_address_candidate` | 301-325 | 주소 후보 정리 + 노이즈 절단 |
| 11 | `_address_needs_continuation` | 328-336 | 광역만 있는 불완전 주소 판정 |
| 12 | `_address_continuation_candidate` | 339-358 | 다음 행에서 주소 확장 |
| 13 | `_maybe_set_address` | 361-369 | 길이 개선 시 주소 교체 |

### 2.4 representative group (1개)

| # | 함수 | 라인 | 역할 |
|---|---|---|---|
| 14 | `_is_bad_representative_candidate` | 284-298 | 대표자 false positive 필터 |

### 2.5 company group (8개)

| # | 함수 | 라인 | 역할 |
|---|---|---|---|
| 15 | `_is_bad_company_candidate` | 225-281 | 회사 false positive 필터 (가장 복잡) |
| 16 | `_extract_company_rep_from_slash` | 472-482 | "회사/대표자" slash 패턴 (공유 helper) |
| 17 | `_extract_company_near_biz` | 485-509 | 사업자번호 인접 회사명 추출 |
| 18 | `_normalize_company_candidate` | 512-524 | 회사명 정규화 (하드코드 교정 포함) |
| 19 | `_company_candidate_score` | 527-554 | 회사 후보 scoring |
| 20 | `_company_candidate_texts` | 557-585 | 한 행에서 회사 후보 후보군 생성 |
| 21 | `_rescue_company_name` | 588-639 | 다중 source rescue 추출 (3 그룹 모두 호출) |

### 2.6 common helpers (2개)

| # | 함수 | 라인 | 역할 |
|---|---|---|---|
| 22 | `_extract_until_next_label` | 120-126 | 패턴 이후 ~ 다음 레이블 추출 |
| 23 | `_bad_top_text_candidate` | 141-149 | 영수증 푸터/안내문 노이즈 판정 |

### 2.7 orchestrators (R2 후반)

| # | 함수 | 라인 | 역할 |
|---|---|---|---|
| 24 | `_extract_fields_from_rows` | 642-716 | 모든 필드 추출 메인 루프 |
| 25 | `_repair_remaining_top_fields_from_text_lines` | 372-469 | 누락 필드 raw line 기반 repair |
| 26 | `extract_receipt_fields` | 827-937 | public API (R5 response_builder 단계 영역) |

---

## 3. 함수별 의존성 (cross-group 포함)

### 3.1 utils 모듈 의존

| 함수 | text_normalize | regex_patterns | rows | io_json |
|---|---|---|---|---|
| `_validate_biz_number` | - | - | - | - |
| `_extract_biz_number` | `_clean_number` | - | - | - |
| `_normalize_phone_digits` | - | - | - | - |
| `_format_phone_digits` | - | - | - | - |
| `_valid_phone_digits` | - | - | - | - |
| `_valid_labeled_phone_digits` | - | - | - | - |
| `_extract_phone_candidate` | - | `_PHONE_LABELED_RE`, `_PHONE_ADMIN_NOISE_RE` | - | - |
| `_extract_rep_phone_pair` | - | `_PHONE_ADMIN_NOISE_RE` | - | - |
| `_extract_address_fragment` | `_clean_inline_field_value` | `_ADDR_START_RE`, `_ADDRESS_CUT_RE`, `_PHONE_RE` | - | - |
| `_clean_address_candidate` | `_clean_inline_field_value` | `_ADDR_START_RE`, `_ADDRESS_CUT_RE`, `_PHONE_RE`, `_ADDRESS_TRAILING_NOISE_RE`, `_ADDRESS_CORE_TOKEN_RE`, `_ADDRESS_STORE_NOISE_RE` | - | - |
| `_address_needs_continuation` | - | `_ADDRESS_BROAD_ONLY_RE` | - | - |
| `_address_continuation_candidate` | `_clean_inline_field_value` | `_ADDRESS_CUT_RE`, `_PHONE_RE`, `_ADDRESS_TRAILING_NOISE_RE`, `_FIELD_NOISE_RE`, `_ADDRESS_CONTINUATION_RE` | - | - |
| `_maybe_set_address` | - | - | - | - |
| `_is_bad_representative_candidate` | `_clean_inline_field_value` | `_LABEL_ONLY_RE`, `_REPRESENTATIVE_NOISE_RE`, `_REPRESENTATIVE_SURNAME_RE` | - | - |
| `_is_bad_company_candidate` | `_clean_inline_field_value` | `_LABEL_ONLY_RE`, `_COMPANY_SLOGAN_RE`, `_FIELD_NOISE_RE`, `_ADDRESS_CORE_TOKEN_RE`, `_ADDR_START_RE`, `_COMPANY_SUFFIX_HINT_RE`, `_CONVENIENCE_STORE_NAME_RE`, `_PERSON_LIKE_NAME_RE`, `_REPRESENTATIVE_SURNAME_RE` | `_is_merchant_notice_row` | - |
| `_extract_company_rep_from_slash` | `_clean_inline_field_value` | - | - | - |
| `_extract_company_near_biz` | `_clean_inline_field_value` | `_ADDR_START_RE`, `_ADDRESS_CUT_RE`, `_PHONE_RE` | - | - |
| `_normalize_company_candidate` | `_clean_inline_field_value` | - | - | - |
| `_company_candidate_score` | - | `_CONVENIENCE_STORE_NAME_RE`, `_COMPANY_SUFFIX_HINT_RE` | - | - |
| `_company_candidate_texts` | `_clean_inline_field_value` | `_FIELD_NOISE_RE` | `_is_merchant_notice_row` | - |
| `_rescue_company_name` | - | - | `_row_text` | - |
| `_extract_until_next_label` | `_clean_inline_field_value` | `_NEXT_LABEL_RE` | - | - |
| `_bad_top_text_candidate` | - | - | - | - |

### 3.2 Cross-group dependency graph (위험 요소)

| 호출하는 함수 (그룹) | 호출되는 함수 (그룹) | 위험 |
|---|---|---|
| `_extract_rep_phone_pair` (phone) | `_is_bad_representative_candidate` (representative) | phone → representative 역방향 |
| `_address_continuation_candidate` (address) | `_bad_top_text_candidate` (common) | address → common (안전) |
| `_is_bad_company_candidate` (company) | `_bad_top_text_candidate` (common) | company → common (안전) |
| `_extract_company_rep_from_slash` (company) | `_bad_top_text_candidate` (common) | company → common (안전) |
| `_extract_company_near_biz` (company) | `_bad_top_text_candidate` (common) | company → common (안전) |
| `_company_candidate_texts` (company) | `_extract_until_next_label`, `_extract_company_rep_from_slash`, `_extract_company_near_biz` | company 내부 + common |
| `_rescue_company_name` (company) | `_extract_biz_number` (business), `_extract_phone_candidate` (phone), `_extract_address_fragment` (address) | **company → 다중 그룹** |

### 3.3 Import 순서 제약

위 의존성을 정리한 import 순서 제약:

```
common (없음)
  ↑
business_number (text_normalize)
  ↑
phone (regex_patterns; _extract_rep_phone_pair 만 representative 의존)
  ↑
representative (regex_patterns)
  ↑
address (regex_patterns, common)
  ↑
company (text_normalize, regex_patterns, rows, common, business_number, phone, address)
  ↑
fields_pipeline (모든 그룹)
```

**핵심 결정**: `_extract_rep_phone_pair` 위치
- 옵션 A: phone.py 에 두고 representative 함수 import → phone → representative 역방향 의존
- **옵션 B (권장)**: representative.py 에 두고 phone helper import → 한 방향 (representative → phone)
- 의미적으로도 representative+phone 추출이 핵심 출력이므로 representative.py 가 자연스럽다.

---

## 4. 함수별 호출부 (main.py 내)

| 함수 | 호출하는 함수 | 호출 횟수 |
|---|---|---|
| `_validate_biz_number` | `_extract_biz_number` | 1 |
| `_extract_biz_number` | `_extract_fields_from_rows`, `_rescue_company_name` | 3 |
| `_normalize_phone_digits` | `_extract_phone_candidate`, `_extract_rep_phone_pair` | 5 |
| `_format_phone_digits` | `_extract_phone_candidate`, `_extract_rep_phone_pair` | 5 |
| `_valid_phone_digits` | `_valid_labeled_phone_digits`, `_extract_phone_candidate` | 4 |
| `_valid_labeled_phone_digits` | `_extract_phone_candidate` | 1 |
| `_extract_phone_candidate` | `_extract_fields_from_rows`, `_rescue_company_name` | 2 |
| `_extract_rep_phone_pair` | `_extract_fields_from_rows` | 1 |
| `_extract_address_fragment` | `_repair_remaining_top_fields_from_text_lines`, `_extract_fields_from_rows`, `_rescue_company_name` | 5 |
| `_clean_address_candidate` | `_repair_remaining_top_fields_from_text_lines`, `_extract_fields_from_rows` | 14 |
| `_address_needs_continuation` | `_maybe_set_address`, `_repair_remaining_top_fields_from_text_lines`, `_extract_fields_from_rows` | 8 |
| `_address_continuation_candidate` | `_repair_remaining_top_fields_from_text_lines`, `_extract_fields_from_rows` | 6 |
| `_maybe_set_address` | `_repair_remaining_top_fields_from_text_lines`, `_extract_fields_from_rows` | 7 |
| `_is_bad_representative_candidate` | `_extract_rep_phone_pair`, `_repair_remaining_top_fields_from_text_lines`, `_extract_fields_from_rows` | 5 |
| `_is_bad_company_candidate` | `_repair_remaining_top_fields_from_text_lines`, `_company_candidate_score`, `_extract_fields_from_rows` | 6 |
| `_bad_top_text_candidate` | 5곳 (common cross-cut) | 5 |
| `_extract_company_rep_from_slash` | `_company_candidate_texts`, `_extract_fields_from_rows` | 2 |
| `_extract_company_near_biz` | `_company_candidate_texts`, `_extract_fields_from_rows` | 2 |
| `_normalize_company_candidate` | `_repair_remaining_top_fields_from_text_lines`, `_company_candidate_score`, `_company_candidate_texts`, `_rescue_company_name` | 5 |
| `_company_candidate_score` | `_rescue_company_name` | 2 |
| `_company_candidate_texts` | `_rescue_company_name` | 1 |
| `_rescue_company_name` | `extract_receipt_fields` | 1 |
| `_extract_until_next_label` | `_repair_remaining_top_fields_from_text_lines`, `_company_candidate_texts`, `_extract_fields_from_rows` | 4 |

`_rescue_company_name` 는 **모든 그룹의 함수를 호출** 하는 가장 복잡한 cross-group 호출자.

---

## 5. 이동 가능 여부

| 함수 | 이동 가능? | 안전도 | 비고 |
|---|---|---|---|
| `_validate_biz_number` | 가능 | ★★★★★ | 의존 0개 |
| `_extract_biz_number` | 가능 | ★★★★★ | text_normalize 만 의존 |
| `_normalize_phone_digits` | 가능 | ★★★★★ | 의존 0개 |
| `_format_phone_digits` | 가능 | ★★★★★ | 의존 0개 |
| `_valid_phone_digits` | 가능 | ★★★★★ | re 만 |
| `_valid_labeled_phone_digits` | 가능 | ★★★★★ | re + `_valid_phone_digits` |
| `_extract_phone_candidate` | 가능 | ★★★★ | regex_patterns + 자체 helpers |
| `_extract_rep_phone_pair` | 가능 (representative.py) | ★★★ | representative 의존 |
| `_bad_top_text_candidate` | 가능 (common.py) | ★★★★★ | 의존 0개 (re만) |
| `_extract_until_next_label` | 가능 (common.py) | ★★★★★ | regex_patterns + text_normalize |
| `_extract_address_fragment` | 가능 | ★★★★ | text_normalize + regex_patterns |
| `_clean_address_candidate` | 가능 | ★★★★ | text_normalize + regex_patterns |
| `_address_needs_continuation` | 가능 | ★★★★★ | regex_patterns 만 |
| `_address_continuation_candidate` | 가능 | ★★★ | + common (`_bad_top_text_candidate`) |
| `_maybe_set_address` | 가능 | ★★★★★ | 자체 의존만 |
| `_is_bad_representative_candidate` | 가능 | ★★★★ | text_normalize + regex_patterns |
| `_is_bad_company_candidate` | 가능 | ★★★ | + common, utils.rows (`_is_merchant_notice_row`) |
| `_extract_company_rep_from_slash` | 가능 | ★★★ | + common |
| `_extract_company_near_biz` | 가능 | ★★★ | + common |
| `_normalize_company_candidate` | 가능 | ★★★★ | text_normalize 만 |
| `_company_candidate_score` | 가능 | ★★★ | regex_patterns + 자체 |
| `_company_candidate_texts` | 가능 | ★★ | + common, utils.rows, 자체 다수 |
| `_rescue_company_name` | 가능 | ★★ | **모든 그룹 cross-call** |

---

## 6. 위험도 종합

### 6.1 그룹별 위험도

| 그룹 | 위험도 | 사유 |
|---|---|---|
| common | LOW | 의존 0개, 모두가 의존하므로 가장 먼저 이동 필요 |
| business_number | LOW | 2개 함수, text_normalize 만 의존 |
| phone (rep_phone_pair 제외) | LOW-MEDIUM | 5개 함수, regex_patterns 만 의존, 폐쇄적 그룹 |
| representative | MEDIUM | 1개 함수 + `_extract_rep_phone_pair` 옮김 |
| address | MEDIUM | continuation 로직 + common 의존 |
| company | HIGH | 8개 함수, scoring + cross-group rescue |
| orchestrator (`_extract_fields_from_rows` 등) | HIGH | 모든 그룹 호출 |

### 6.2 import 순환 위험

위 §3.3 import 순서를 지키면 순환 위험 없음. 단, 다음 케이스는 주의:
- phone 모듈에서 `_extract_rep_phone_pair` 를 빼지 않으면 phone → representative 역의존 발생 → **반드시 representative.py 로 옮긴다.**
- company 모듈은 `_rescue_company_name` 때문에 business_number / phone / address / common / utils.rows 모두 import → **반드시 가장 마지막에 이동.**

### 6.3 결과 변화 위험

- 함수 본문 변경 0 → 결정론적으로 동일 결과
- 단, 다음은 주의:
  - 모듈 import 순서 변경으로 sys.modules 캐시 시점 달라질 수 있음 (Python 자체는 안전하나 third-party 라이브러리 lazy init이 영향받을 가능성 매우 낮음)
  - 함수 객체 참조: main.py 의 callback 사용 (예: `extract_amount_candidates(rows, _row_text, ...)`) 같은 패턴은 import 후에도 동일 작동
  - 함수 이름이 main.py 에서 import 된 이름 그대로면 호출부 1글자 변경 없음

---

## 7. 권장 하위 단계 (R2 분할)

R1 의 sub-phase 패턴을 따라 작은 단위로 쪼갠다.

### R2-a: `extractors/common.py` (LOW risk, 필수 선행)

대상:
- `_bad_top_text_candidate`
- `_extract_until_next_label`

**왜 가장 먼저?** 5개 다른 함수에서 호출되며, common helper 가 분리되어야 후속 그룹들이 import 가능.

검증: 정적 + AST 동일성 + live full validation.

### R2-b: `extractors/business_number.py` (LOW risk)

대상:
- `_validate_biz_number`
- `_extract_biz_number`

**가장 폐쇄적인 그룹.** text_normalize 만 의존. 2개 함수.

검증: 정적 + AST + live. 특히 baseline 사업자번호 9/9, google 7.jpg biz 일치 확인.

### R2-c: `extractors/phone.py` (LOW-MEDIUM risk)

대상 (5개, `_extract_rep_phone_pair` 는 R2-d):
- `_normalize_phone_digits`
- `_format_phone_digits`
- `_valid_phone_digits`
- `_valid_labeled_phone_digits`
- `_extract_phone_candidate`

검증: 정적 + AST + live. 특히 google 7.jpg `02-927-2369`, 11.jpg `02-33-4278` 확인.

### R2-d: `extractors/representative.py` (MEDIUM risk)

대상:
- `_is_bad_representative_candidate`
- `_extract_rep_phone_pair` (phone helper import)

**phone 모듈이 R2-c 에서 분리된 후에만 진행 가능.** representative → phone 한 방향 의존.

검증: 정적 + AST + live. baseline 7.jpg 대표자, 정공구 4.jpg/a1.jpg 대표자 확인.

### R2-e: `extractors/address.py` (MEDIUM-HIGH risk)

대상 (5개):
- `_extract_address_fragment`
- `_clean_address_candidate`
- `_address_needs_continuation`
- `_address_continuation_candidate` (common 의존)
- `_maybe_set_address`

**common (R2-a) 이후에만 진행.** address 의 continuation 로직은 미세한 row scan 차이에 민감.

검증: 정적 + AST + live. 특히 baseline 7.jpg GT_SIMILARITY 주소, google 11.jpg 주소, baseline 1.jpg 주소 trailing `국` 유지.

### R2-f: `extractors/company.py` (HIGH risk, R2 의 가장 위험한 단계)

대상 (8개 + `_rescue_company_name` 단독 격리 권장):

R2-f-1 (company helpers 먼저):
- `_extract_company_rep_from_slash`
- `_extract_company_near_biz`
- `_normalize_company_candidate`
- `_is_bad_company_candidate`
- `_company_candidate_score`
- `_company_candidate_texts`

R2-f-2 (`_rescue_company_name` 단독):
- 모든 그룹 (business, phone, address) cross-import 필요
- 단독 commit + 별도 검증

검증: 정적 + AST + live. 특히 baseline 10.jpg 토탈철물, baseline a1.jpg 정공구, google 7.jpg GS25 명확 확인.

### R2-g (선택): `extractors/fields_pipeline.py`

대상 (3개 orchestrator):
- `_extract_fields_from_rows`
- `_repair_remaining_top_fields_from_text_lines`

**주의**: `extract_receipt_fields` 는 response builder / 정책과 강하게 묶여 있어 R5 단계 영역. R2-g 에서는 두 helper만.

---

## 8. 첫 실제 R2 작업 추천 범위

**다음 실행 작업: R2-a (`extractors/common.py`)**

이유:
- 의존 0개 (`_bad_top_text_candidate`) + 의존 1개 utils 만 (`_extract_until_next_label`).
- 5개 다른 함수에서 호출되므로 가장 먼저 분리되어야 후속 작업 가능.
- 함수 본문이 짧고 (각 ~10라인) 명확.
- 회귀 위험 매우 낮음.

준비 사항:
- main.py 백업
- `ocr-server/extractors/__init__.py` (빈 파일) 생성
- `ocr-server/extractors/common.py` 신규 파일 생성
- main.py 정의부 제거 + import 추가

검증: §10 절차 전체.

---

## 9. 검증 전략

### 9.1 정적 검증 (각 sub-phase 공통)

```bash
cd ocr-server
python -m py_compile extractors/<new_module>.py
python -m py_compile main.py
python -c "import main"
```

### 9.2 AST 함수 본문 동일성 검증

R1 와 동일한 방식 (backup main.py vs 신규 모듈 함수 본문 ast.dump 비교):

```python
import ast
TARGETS = {<this sub-phase functions>}
b = {n.name: ast.dump(n) for n in ast.walk(ast.parse(open(BACKUP).read()))
     if isinstance(n, ast.FunctionDef) and n.name in TARGETS}
r = {n.name: ast.dump(n) for n in ast.walk(ast.parse(open(NEW_MODULE).read()))
     if isinstance(n, ast.FunctionDef) and n.name in TARGETS}
assert all(b[k] == r[k] for k in TARGETS)
```

### 9.3 Live validation (각 sub-phase 공통)

uvicorn 9100 재기동 → /health → baseline_fast → google → baseline.

### 9.4 회귀 기준 (모든 sub-phase 공통)

baseline_fast: selected 3 / suppression 2 / unknown 0 / 9.jpg suppressed_bank_slip / a2.jpg suppressed_handwritten

google: total 11 / selected 10 / suppression 1 / 7.jpg `selected, GS25성신로데오점, 7,650, 02-927-2369` / 6.jpg suppressed_bank_slip

baseline: selected 8 / suppression 2 / OCR 43/57 / final 52/57 / biz 9/9 / 1.jpg 10560 / 4.jpg 17600 / 10.jpg 19250

### 9.5 Sub-phase 별 추가 확인 케이스

| Sub-phase | 추가 확인 |
|---|---|
| R2-a (common) | 회사/주소 추출 유지 (cross-cut helper) |
| R2-b (business) | baseline biz 9/9 그대로 |
| R2-c (phone) | google 7.jpg 02-927-2369, 11.jpg 02-33-4278 |
| R2-d (representative) | baseline 정공구 4.jpg/a1.jpg 대표자 |
| R2-e (address) | baseline 7.jpg GT_SIMILARITY 주소, 1.jpg trailing `국` 유지 |
| R2-f (company) | baseline 10.jpg 토탈철물, a1.jpg 정공구, google 7.jpg GS25 |

### 9.6 롤백 절차

각 sub-phase 직전 main.py 백업. 검증 실패시 즉시 백업 복원 + 분석.

---

## 10. 거래명세서 진입 전 최소 권장 분리 범위

거래명세서 (invoice_statement) parser 는 본 R2 이후에 시작한다. 거래명세서가 시작될 때 어떤 분리가 최소로 필요한가?

### 거래명세서의 특징
- 표 구조 기반 (영수증과 다른 layout)
- 사업자번호, 회사명, 대표자, 주소, 전화 모두 포함됨
- 총합계금액 위치 다름 (표 하단)

### 거래명세서 parser 가 재사용해야 할 함수
- `_extract_biz_number` — 그대로 재사용 (anchor 역할)
- `_extract_phone_candidate` — 그대로 재사용
- `_extract_address_fragment` — 그대로 재사용 (도/시 앞 토큰 동일)
- `_clean_inline_field_value` — 이미 utils.text_normalize (R1-a 완료)
- `_clean_number` — 이미 utils.text_normalize

### 거래명세서 전용으로 갈 가능성이 높은 함수
- company 추출 (다른 위치/scoring 가능)
- address continuation (표 안 vs 상단 차이)
- representative 패턴

### 거래명세서 진입 전 **최소 권장 분리 범위**

| 단계 | 필수도 | 사유 |
|---|---|---|
| **R2-a common** | **필수** | 모두가 의존, 분리되지 않으면 다른 모듈 모두 import 어려움 |
| **R2-b business_number** | **필수** | 거래명세서에서도 그대로 import 필요 |
| **R2-c phone** | **필수** | 거래명세서에서도 그대로 import 필요 |
| R2-d representative | 권장 | 분리되면 invoice 전용 분기 깔끔 |
| R2-e address | 권장 | 분리되면 invoice 전용 변형 가능 |
| R2-f company | 선택 | 거래명세서 회사명은 다른 위치 가능, 별도 작성도 OK |
| R2-g fields_pipeline | 선택 | 거래명세서는 자체 pipeline 가능 |

**최소 진입 권장 범위**: R2-a + R2-b + R2-c (3개 sub-phase).

이 3개만 끝내면:
- 거래명세서 parser 가 `from extractors.business_number import _extract_biz_number`, `from extractors.phone import _extract_phone_candidate` 등으로 핵심 anchor를 재사용.
- company / address / representative 의 거래명세서 분기는 invoice_statement.py 에서 별도 구현 후 추후 일반화.

**완전 권장 범위**: R2-a~f 전체 (7개 sub-phase). 깔끔한 invoice parser 진입 가능.

---

## 11. R2 후 R1+R2 종합

R2 완료 후 main.py 의 책임은 다음만 남는다:
- FastAPI app + route (R6 영역)
- OCR engine 관리 + warmup (R3 영역)
- bbox / block re-OCR (R3 영역)
- amount policy (R4 영역)
- response builder (R5 영역)
- `extract_receipt_fields` (R5 영역)
- `_warmup_ocr` 등 startup hook

R2 까지 완료 시 main.py 라인 수 예상: **2326 → ~1400 라인** (대략 -900라인, 함수 22개 + helper 2개 분리).

---

## 12. 본 문서의 위치

- `docs/REFACTOR_R2_ANALYSIS_20260426.md`
- 본 문서는 분석/계획 문서이며 코드를 변경하지 않는다.
- R2-a/b/c/d/e/f 의 실제 결과는 별도 문서 (`docs/REFACTOR_R2A_RESULT_*.md` 등) 로 기록.
