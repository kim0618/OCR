# REFACTOR MINIMAL COMMON READY 2026-04-26

최소 공통화 완료 선언 문서.
계획 문서: [docs/REFACTOR_PLAN_20260426.md](REFACTOR_PLAN_20260426.md)

이 문서는 거래명세서 진입 전 최소 공통화 기준이 충족되었음을 선언한다.

---

## 1. 최소 공통화 완료 선언

다음 단계가 모두 완료되었다:

| Phase | 내용 | 결과 |
|---|---|---|
| R1-a | `utils/text_normalize.py` | 완료 |
| R1-b | `utils/regex_patterns.py` | 완료 |
| R1-c | `utils/rows.py` | 완료 |
| R1-d | `utils/io_json.py` | 완료 |
| R2-a | `extractors/common.py` | 완료 |
| R2-b | `extractors/business_number.py` | 완료 |
| R2-c | `extractors/phone.py` | 완료 |

**Phase R1 (utils 분리) 전체 완료.**
**Phase R2 최소 공통화 (common + business_number + phone) 완료.**

---

## 2. 생성된 모듈 목록

```
ocr-server/
  utils/
    text_normalize.py   # _clean_number, _clean_inline_field_value
    regex_patterns.py   # 19개 정규식 상수
    rows.py             # _group_rows, _row_text, _single_line_rows, _is_merchant_notice_row
    io_json.py          # _load_json, _save_json
  extractors/
    common.py           # _bad_top_text_candidate, _extract_until_next_label
    business_number.py  # _validate_biz_number, _extract_biz_number
    phone.py            # _normalize_phone_digits, _format_phone_digits,
                        # _valid_phone_digits, _valid_labeled_phone_digits,
                        # _extract_phone_candidate
```

이동된 함수/상수 총계: 함수 19개 + 정규식 상수 19개.

---

## 3. 검증 결과 (전체 통과)

모든 Phase 완료 시점에서 baseline_fast / google / baseline 3개 dataset 회귀 검증 통과.

### 3.1 핵심 수치 (lock 기준 대비)

| 기준 | 기준값 | 최종 확인 |
|---|---|---|
| baseline selected | 8 | **8** |
| baseline suppression | 2 | **2** |
| baseline OCR 자체 | 43/57 | **유지** |
| baseline 최종 채택값 | 52/57 | **유지** |
| baseline 사업자번호 recall | 9/9 | **9/9** |
| baseline 총합계금액 | 8/10 | **유지** |
| google selected | 10 | **10** |
| google suppression | 1 | **1** |

### 3.2 핵심 케이스 (google lock)

| 케이스 | 기준 | 확인 |
|---|---|---|
| google 7.jpg company | GS25성신로데오점 | **유지** |
| google 7.jpg amount | 7,650 | **유지** |
| google 7.jpg phone | 02-927-2369 | **유지** |
| google 7.jpg doc_type | receipt_pos | **유지** |
| google 6.jpg | suppressed_bank_slip | **유지** |
| google 11.jpg phone | 02-33-4278 | **유지** |

### 3.3 baseline 전화번호 (R2-c 추가 확인)

| 파일 | locked tel | 확인 |
|---|---|---|
| 1.jpg | 031-479-0485 | **유지** |
| 2.jpg | 031-479-0090 | **유지** |
| 3.jpg | 031-479-2280 | **유지** |
| 4.jpg | 031-479-3690 | **유지** |
| 7.jpg | 031-388-1080 | **유지** |
| 8.jpg | 031-455-9955 | **유지** |
| 10.jpg | 010-9388-9936 | **유지** |
| a2.jpg | 031-479-2280 | **유지** |

---

## 4. 현재 main.py 상태

- 리팩토링 전: **2450라인**
- 현재: **2234라인** (216라인 감소)
- 분리 완료 영역: utils helper, common extractor, business_number, phone
- **아직 main.py 에 남아 있는 영역** (전체 리팩토링은 완료 아님):

| 영역 | 대상 함수 예시 | 계획 Phase |
|---|---|---|
| address extractor | `_extract_address_fragment`, `_clean_address_candidate` 등 | R2-e |
| representative extractor | `_is_bad_representative_candidate`, `_extract_rep_phone_pair` | R2-d |
| company extractor | `_is_bad_company_candidate`, `_rescue_company_name` 등 | R2-f |
| orchestrator | `_extract_fields_from_rows`, `extract_receipt_fields` | R2-g |
| pipeline (image/OCR/bbox) | `_detect_upper_block_bbox`, `_reocr_block` 등 | R3 |
| policy | `_apply_doc_type_amount_policy` | R4 |
| response builder | 응답 dict 조립 | R5 |
| routes | FastAPI endpoints | R6 |

---

## 5. 거래명세서 진입 가능 여부

### 5.1 최소 공통화 기준 충족 여부

거래명세서 parser 가 필요로 하는 핵심 anchor 함수가 분리되었다:

| 함수 | 위치 | 거래명세서 재사용 가능 여부 |
|---|---|---|
| `_extract_biz_number` | `extractors.business_number` | 가능 (사업자번호 추출) |
| `_extract_phone_candidate` | `extractors.phone` | 가능 (전화번호 추출) |
| `_clean_number` | `utils.text_normalize` | 가능 (숫자 정규화) |
| `_clean_inline_field_value` | `utils.text_normalize` | 가능 (필드값 정리) |
| `_ADDR_START_RE`, `_NEXT_LABEL_RE` 등 | `utils.regex_patterns` | 가능 (주소/레이블 패턴) |

**최소 공통화 기준 충족: 거래명세서 진입 가능.**

### 5.2 거래명세서 진입 전 준비 사항

코드보다 샘플과 스펙이 먼저다:

1. **샘플 준비**: 거래명세서 실제 이미지 수집 (3~5장 이상)
2. **testset 추가**: `mysuit-ocr/public/data/testsets/invoice_statement/` 생성
3. **manifest 작성**: `documentType: "invoice_statement"` 로 manifest.json 작성
4. **필드 요구사항 정리**: 거래명세서에서 추출할 필드와 판단 기준 문서화
   - 공급자 사업자번호, 회사명, 대표자, 전화, 주소 (6개 기본 필드 동일한가?)
   - 총합계금액 위치 (표 하단 vs 상단)
   - 품목/수량/단가 처리 여부 (이번에는 무시?)
5. **parser 분기 준비**: `parse_by_doc_type` 인터페이스 (계획 R7)

### 5.3 권장 다음 순서

```
① SESSION_SUMMARY.md 업데이트  ← 즉시 가능
② invoice_statement 샘플 수집 ← 실제 이미지 필요
③ testset/manifest 작성       ← 샘플 확보 후
④ 필드 요구사항 정리           ← 스펙 결정
⑤ parser 최소 구현             ← R2-d~g 일부 없이도 진입 가능
⑥ (병행) R2 나머지 분리 계속   ← 거래명세서와 독립 가능
```

---

## 6. 보류된 리팩토링 범위

아래 Phase 는 현재 보류 상태이며, 거래명세서 진입과 독립적으로 진행 가능:

| Phase | 내용 | 우선순위 |
|---|---|---|
| R2-d | `extractors/representative.py` | 중간 |
| R2-e | `extractors/address.py` | 중간 |
| R2-f | `extractors/company.py` | 높음 (가장 복잡) |
| R2-g | `extractors/fields_pipeline.py` | 높음 |
| R3 | `pipeline/` (image/OCR/bbox) | 낮음 |
| R4 | `policies/` (amount/suppression) | 낮음 |
| R5 | `pipeline/response_builder.py` | 낮음 |
| R6 | `routes/` | 낮음 |

R2-d~g 는 거래명세서 parser 가 address/company extractor 를 재사용할 계획이라면 우선도를 높이는 게 좋다. 그렇지 않으면 거래명세서 전용 구현 후 나중에 일반화해도 무방.

---

## 7. 다음 추천 단계

1. **SESSION_SUMMARY.md 업데이트** — 최소 공통화 완료, 거래명세서 진입 준비 상태로 갱신
2. **거래명세서 샘플셋 준비** — `testsets/invoice_statement/` + manifest.json
3. **거래명세서 필드 요구사항 정의** — 어떤 필드를 추출할 것인지 스펙 문서화
4. **R2-d~g 계속 진행** (병행 또는 순차) — 거래명세서 구현과 독립적으로 진행 가능

---

## 8. 참조 문서

| 문서 | 내용 |
|---|---|
| [docs/BASELINE_LOCK_20260425.md](BASELINE_LOCK_20260425.md) | baseline 회귀 기준 |
| [docs/GOOGLE_LOCK_20260425.md](GOOGLE_LOCK_20260425.md) | google 일반화 기준 |
| [docs/REFACTOR_PLAN_20260426.md](REFACTOR_PLAN_20260426.md) | 전체 리팩토링 계획 |
| [docs/REFACTOR_R2_ANALYSIS_20260426.md](REFACTOR_R2_ANALYSIS_20260426.md) | R2 extractor 의존성 분석 |
