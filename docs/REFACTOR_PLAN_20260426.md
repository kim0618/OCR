# MAIN.PY REFACTOR PLAN 2026-04-26

이 문서는 `ocr-server/main.py` 의 단계적 리팩토링 계획이다. **OCR 인식 결과는 이번 리팩토링 동안 절대 변경되지 않는다.** 모든 단계는 동일한 입력에 대해 동일한 출력을 보장하며, baseline / google lock 결과를 그대로 유지한다.

이 문서는 계획 문서이며, 본 문서 작성 자체로는 어떤 코드도 수정하지 않는다.

---

## 1. 리팩토링 목적

### 1.1 직접적 동기

- `main.py` 가 현재 **2450 라인** 으로 비대화되어 있다.
- API route, 정규식 상수, 필드 추출, bbox 계산, OCR 엔진 관리, 정책 결정, 응답 빌드, 디버그 로깅이 모두 한 파일에 섞여 있다.
- `documentType` 가 늘어날 때마다 `main.py` 를 직접 수정해야 하는 구조다.

### 1.2 product 방향과의 정합

- 본 OCR 은 단일 vendor / 단일 form 에 최적화되지 않는 일반 목적 OCR 을 지향한다 ([CLAUDE.md](../CLAUDE.md) 참조).
- `documentType` 별 parser branching 기반을 마련해야 한다. 후보:
  - `card_receipt`
  - `pos_receipt`
  - `food_cafe_receipt`
  - `finance_slip`
  - `medical_receipt`
  - `invoice_statement`
  - `unknown`
- 거래명세서 (`invoice_statement`) 는 본 리팩토링 **이후** 에 진입한다. 이번 리팩토링은 그 구조 기반만 마련한다.

### 1.3 Lock 보호

- baseline OCR 43/57, 최종 채택값 52/57, 사업자번호 9/9, 총합계금액 8/10 ([docs/BASELINE_LOCK_20260425.md](BASELINE_LOCK_20260425.md))
- google selected 10 / suppression 1 / unknown 0, 7.jpg = `GS25성신로데오점` / `7,650` / `02-927-2369` ([docs/GOOGLE_LOCK_20260425.md](GOOGLE_LOCK_20260425.md))
- 모든 Phase 후 위 수치가 그대로여야 한다.

---

## 2. 현재 main.py 책임 분석

`main.py` 안에 23개의 논리 섹션이 섞여 있다. (전체 라인 매핑은 본 리팩토링 작업 시 사용)

### 2.1 책임 클러스터

| # | 클러스터 | 대표 함수/내용 | 대략 라인 |
|---|---|---|---|
| A | Utils — OCR 정규화 / 숫자 정리 | `_parse_ocr_lines`, `_clean_number`, `_validate_biz_number`, `_extract_biz_number`, `_parse_amounts` | 31–101 |
| B | Utils — Row 그룹핑 / 라인 정리 | `_group_rows`, `_row_text`, `_single_line_rows`, `_is_merchant_notice_row`, `_clean_inline_field_value` | 103–169 |
| C | Regex 상수 (정규식 모듈 레벨) | `_PHONE_RE`, `_PHONE_LABELED_RE`, `_PHONE_ADMIN_NOISE_RE`, `_ADDR_*_RE`, `_NEXT_LABEL_RE`, `_FIELD_NOISE_RE`, `_REPRESENTATIVE_NOISE_RE`, `_COMPANY_*_RE`, `_PERSON_LIKE_NAME_RE`, `_REPRESENTATIVE_SURNAME_RE`, `_ADDRESS_*_RE`, `_LABEL_ONLY_RE` | 171–229 |
| D | Phone 추출 | `_normalize_phone_digits`, `_format_phone_digits`, `_valid_phone_digits`, `_valid_labeled_phone_digits`, `_extract_phone_candidate`, `_extract_rep_phone_pair` | 264–335 |
| E | Address 추출 | `_extract_address_fragment`, `_clean_address_candidate`, `_address_needs_continuation`, `_address_continuation_candidate`, `_maybe_set_address` | 241–480 |
| F | Company 추출 | `_is_bad_company_candidate`, `_extract_company_rep_from_slash`, `_extract_company_near_biz`, `_normalize_company_candidate`, `_company_candidate_score`, `_rescue_company_name` | 337–750 |
| G | Representative 추출 | `_is_bad_representative_candidate`, (slash pair 공유) | 396–410 |
| H | Common helper | `_extract_until_next_label`, `_repair_remaining_top_fields_from_text_lines`, `_bad_top_text_candidate` | 232–581 |
| I | 필드 추출 오케스트레이션 | `_extract_fields_from_rows` | 754–829 |
| J | 정책 — 문서 유형별 amount 처리 | `_apply_doc_type_amount_policy`, `_REVIEW_STATUSES` | 854–936 |
| K | 메인 추출 오케스트레이션 | `extract_receipt_fields` | 939–1048 |
| L | OCR 엔진 관리 | `_warmup_ocr`, `get_ocr_engine`, `_ocr_crop_region` | 1052–1519 |
| M | I/O 유틸 / 리뷰 로그 | `_load_json`, `_save_json`, `_append_review_log`, `_build_auto_extract_log` | 1081–1205 |
| N | 인증 / health route | `/health`, `/login` | 1208–1245 |
| O | Template route | `/templates`, `/templates/{id}` | 1251–1267 |
| P | 이력 route | `/ocrSelect`, `/ocrInsert`, `/ocrUpdate`, `/ocrDelete` | 1273–1324 |
| Q | 피드백 / 리뷰 로그 route | `/ocr/feedback`, `/ocr/review-log` | 1331–1401 |
| R | 이미지 read/encode + preprocess route | `read_image`, `encode_image`, `/preprocess`, `/preprocess/info`, `/preprocess/corners` | 1401–1466, 1921–1963 |
| S | Upper block bbox 검출 | `_detect_upper_block_bbox` | 1522–1643 |
| T | Amount block bbox 검출 | `_detect_amount_block_bbox` | 1646–1740 |
| U | Block re-OCR / table region | `_reocr_block`, `_ocr_table_region` | 1743–1920 |
| V | 메인 OCR 엔드포인트 | `/ocr/extract` | 1965–2378 |
| W | Revalidate route | `/ocr/revalidate` | 2379–2450 |

### 2.2 외부 모듈 (이미 분리되어 있음)

- [ocr-server/preprocess.py](../ocr-server/preprocess.py) (517 lines): `detect_document`, `detect_orientation`, `deskew`, `denoise`, `enhance_contrast`, `sharpen`, `binarize_for_ocr`, `preprocess`, `preprocess_for_ocr`, `downscale_if_large`, `upscale_if_needed`
- [ocr-server/amount_extractor.py](../ocr-server/amount_extractor.py) (659 lines): `extract_amount_candidates`, `merge_candidates`, `synthesize_supply_vat_totals`, `score_amount_candidate`, `select_best_total_amount`
- [ocr-server/document_classifier.py](../ocr-server/document_classifier.py) (175 lines): `classify_document`

위 3개 모듈은 본 리팩토링 동안 **수정하지 않는다.**

---

## 3. 목표 디렉터리 구조 (제안)

```
ocr-server/
  main.py                       # FastAPI app + route 등록만 남김 (얇은 layer)
  pipeline/
    __init__.py
    image_io.py                 # read_image, encode_image, PDF 디코드
    document_region.py          # detect_document 호출 wrapper, corners route 지원
    orientation.py              # orientation 감지 wrapper, deskew 호출 wrapper
    ocr_runner.py               # get_ocr_engine, _warmup_ocr, _ocr_crop_region
    blocks.py                   # _detect_upper_block_bbox, _detect_amount_block_bbox
    block_reocr.py              # _reocr_block, _ocr_table_region
    response_builder.py         # receipt_fields / field_sources / processed_image / debug payload 조립
  extractors/
    __init__.py
    common.py                   # _extract_until_next_label, _bad_top_text_candidate, _is_merchant_notice_row 등
    business_number.py          # _validate_biz_number, _extract_biz_number
    phone.py                    # _normalize_phone_digits, _format_phone_digits, _valid_*, _extract_phone_candidate, _extract_rep_phone_pair
    address.py                  # _extract_address_fragment, _clean_address_candidate, _address_needs_continuation, _address_continuation_candidate, _maybe_set_address
    company.py                  # _is_bad_company_candidate, _extract_company_*, _company_candidate_score, _rescue_company_name
    representative.py           # _is_bad_representative_candidate (+ slash pair 공유 위치)
    fields_pipeline.py          # _extract_fields_from_rows, _repair_remaining_top_fields_from_text_lines (필드 단위 통합 오케스트레이터)
  policies/
    __init__.py
    receipt_policy.py           # _apply_doc_type_amount_policy
    suppression.py              # _REVIEW_STATUSES + suppression 관련 status 매핑
    candidate_scoring.py        # 향후 확장용 (현재는 amount_extractor 내부에 있음 — 이번 리팩토링은 wrapper만)
  utils/
    __init__.py
    text_normalize.py           # _clean_number, _clean_inline_field_value
    regex_patterns.py           # 모든 _XXX_RE 모듈 레벨 상수 모음
    bbox.py                     # bbox 좌표/박스 헬퍼 (있으면 추출)
    rows.py                     # _group_rows, _row_text, _single_line_rows
    debug.py                    # _build_auto_extract_log, _append_review_log
    io_json.py                  # _load_json, _save_json
  schemas/                      # 향후 확장용 — 이번 리팩토링은 placeholder만
    __init__.py
    receipt_schema.py           # receipt 응답 스키마 정의 (현재 dict 응답을 형식화)
    invoice_schema.py           # placeholder. 거래명세서 진입 시 사용. 본 리팩토링에서는 빈 인터페이스만
    finance_slip_schema.py      # finance_slip suppression 응답 스키마 (현재 main.py 정책에 묻혀 있음)
  routes/
    __init__.py
    health.py                   # /health
    auth.py                     # /login
    template.py                 # /templates, /templates/{id}
    history.py                  # /ocrSelect, /ocrInsert, /ocrUpdate, /ocrDelete
    feedback.py                 # /ocr/feedback, /ocr/review-log
    preprocess_routes.py        # /preprocess, /preprocess/info, /preprocess/corners
    extract.py                  # /ocr/extract, /ocr/revalidate
  amount_extractor.py           # 무수정 유지
  document_classifier.py        # 무수정 유지
  preprocess.py                 # 무수정 유지
```

### 3.1 main.py 의 최종 모습 (목표)

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes import health, auth, template, history, feedback, preprocess_routes, extract
from pipeline.ocr_runner import warmup_ocr

app = FastAPI(title="MySuit OCR Server")
app.add_middleware(CORSMiddleware, ...)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(template.router)
app.include_router(history.router)
app.include_router(feedback.router)
app.include_router(preprocess_routes.router)
app.include_router(extract.router)

@app.on_event("startup")
async def _startup():
    warmup_ocr()
```

대략 ~50 라인 수준.

---

## 4. 단계별 리팩토링 순서

각 Phase 는 독립적으로 commit 가능하며, 각 Phase 종료 시 baseline_fast → baseline → google 검증을 모두 통과해야 한다.

### Phase R1 — Utils 분리 (가장 안전)

**목표:** 어느 추출 로직과도 결합도 없는 순수 helper 만 분리.

**대상:**
- `utils/text_normalize.py`: `_clean_number`, `_clean_inline_field_value`
- `utils/regex_patterns.py`: 모든 `_XXX_RE` 상수
- `utils/rows.py`: `_group_rows`, `_row_text`, `_single_line_rows`
- `utils/io_json.py`: `_load_json`, `_save_json`

**금지:**
- regex 의미 변경 금지
- 정규식 합치기/리팩토링 금지 (`|` 추가, group 변경 금지)
- `_clean_number` 의 swap 사전 변경 금지 (`O→0`, `l→1`, `I→1`, `S→5`, `B→8` 그대로)
- row threshold 계산식 변경 금지

**검증:** Phase 검증 절차 (5 절) 전체 수행.

### Phase R2 — Field extractor 분리

**목표:** 단일 필드 추출 로직을 modular 파일로 분리.

**대상:**
- `extractors/common.py`: `_extract_until_next_label`, `_bad_top_text_candidate`, `_is_merchant_notice_row`
- `extractors/business_number.py`: `_validate_biz_number`, `_extract_biz_number`
- `extractors/phone.py`: phone 관련 5개 함수
- `extractors/address.py`: address 관련 5개 함수
- `extractors/representative.py`: `_is_bad_representative_candidate`
- `extractors/company.py`: company 관련 6개 함수 (`_rescue_company_name` 포함)

**금지:**
- 추출 함수 시그니처 변경 금지
- 함수 내부 분기 / threshold 변경 금지
- "이 함수는 필요 없다" 같은 판단으로 삭제 금지
- 함수 간 호출 순서 변경 금지

**주의:** company 와 representative 사이에 slash pair (`_extract_company_rep_from_slash`) 가 공유되어 있다. company 모듈에 두고 representative 모듈에서 import 하는 방향으로 통일.

**검증:** Phase 검증 절차 전체.

### Phase R3 — Pipeline 분리

**목표:** 이미지 입출력 / OCR runner / bbox 검출 분리.

**대상:**
- `pipeline/image_io.py`: `read_image`, `encode_image` + PDF 처리
- `pipeline/document_region.py`: `detect_document` 호출 wrapper (얇음)
- `pipeline/orientation.py`: orientation/deskew 호출 wrapper
- `pipeline/ocr_runner.py`: `get_ocr_engine`, `_warmup_ocr`, `_ocr_crop_region`
- `pipeline/blocks.py`: `_detect_upper_block_bbox`, `_detect_amount_block_bbox`
- `pipeline/block_reocr.py`: `_reocr_block`, `_ocr_table_region`

**금지:**
- bbox 좌표 계산식 변경 금지
- height bound (14–42% / 18–38% / 20–45%) 변경 금지
- 키워드 셋 (`사업자`, `등록번호`, `TEL`, `대표`, `상호`, `총합계`, `공급가액`, ...) 변경 금지
- re-OCR mode 별 preprocessing 순서 변경 금지

**검증:** Phase 검증 절차 전체. 특히 google 7.jpg 의 bbox 결과가 동일한지 debug 출력으로 비교.

### Phase R4 — Policies 분리

**목표:** status / suppression / scoring 정책 분리.

**대상:**
- `policies/receipt_policy.py`: `_apply_doc_type_amount_policy`
- `policies/suppression.py`: `_REVIEW_STATUSES` + suppression status 매핑
- `policies/candidate_scoring.py`: amount_extractor 의 scoring 함수 wrapper (분리 X. 기존 amount_extractor 의 score 호출만 wrapping)

**금지:**
- bank_slip threshold (score < 40) 변경 금지
- form_or_handwritten suppression 조건 변경 금지
- unknown bare threshold (score < 15) 변경 금지
- review code 문자열 변경 금지 (`no_candidate`, `all_rejected`, `low_confidence`, `suppressed_bank_slip`, `suppressed_handwritten`, `suppressed_unknown_bare`)
- `_apply_doc_type_amount_policy` 의 반환 dict key 변경 금지

**검증:** Phase 검증 절차 전체. 특히 baseline 9.jpg / a2.jpg suppression, google 6.jpg suppression 그대로 유지.

### Phase R5 — Response builder 분리

**목표:** 응답 조립 / debug payload / processed_image 분리.

**대상:**
- `pipeline/response_builder.py`:
  - `extract_receipt_fields` 의 응답 dict 조립 분리
  - field_sources dict 조립
  - processed_image base64 인코딩
  - debug payload 조립 (timing, amount_debug, document_classification 등)
- `utils/debug.py`: `_build_auto_extract_log`, `_append_review_log`

**금지:**
- API 응답 JSON key 변경 금지
- `receipt_fields`, `field_sources`, `document_classification`, `amount_debug`, `processing_time`, `total_ms`, `detect_orientation_ms`, `full_ocr_ms`, `upper_reocr_total_ms`, `amount_reocr_total_ms`, `upper_reocr_ran`, `amount_reocr_ran`, `processed_image` 의 key 또는 의미 변경 금지
- 응답 dict 의 필드 순서가 frontend 코드의 어딘가에서 의미를 가지는 경우 그 순서 유지

**검증:** Phase 검증 절차 + 프런트엔드 (`mysuit-ocr/src/components/test/TestWorkspace.tsx`) 가 응답을 그대로 파싱하는지 spot-check (typecheck/build).

### Phase R6 — Routes 분리 + main.py 얇게

**목표:** FastAPI route 들을 `routes/` 하위로 이동, `main.py` 는 app 등록만.

**대상:**
- `routes/health.py` ← `/health`
- `routes/auth.py` ← `/login`
- `routes/template.py` ← `/templates`, `/templates/{id}`
- `routes/history.py` ← `/ocrSelect`, `/ocrInsert`, `/ocrUpdate`, `/ocrDelete`
- `routes/feedback.py` ← `/ocr/feedback`, `/ocr/review-log`
- `routes/preprocess_routes.py` ← `/preprocess`, `/preprocess/info`, `/preprocess/corners`
- `routes/extract.py` ← `/ocr/extract`, `/ocr/revalidate`

**금지:**
- route URL 변경 금지
- request/response schema 변경 금지
- HTTP method 변경 금지
- query parameter 이름 변경 금지

**검증:** Phase 검증 절차 + frontend 의 모든 fetch 경로가 그대로 작동하는지 spot-check.

### Phase R7 (선택) — documentType parser 분기 준비

**목표:** documentType 별 parser 분기 인터페이스만 마련. **신규 parser 구현은 하지 않는다.**

**대상:**
- `schemas/receipt_schema.py`: receipt 응답 스키마 dataclass/TypedDict 정의 (기존 응답 dict 와 100% 동일)
- `schemas/invoice_schema.py`: 빈 placeholder. `class InvoiceSchema: pass`
- `schemas/finance_slip_schema.py`: 현재 suppression 응답 형식 명문화
- `extractors/fields_pipeline.py` 에 `parse_by_doc_type(doc_type, rows, upper, amount, debug) -> dict` 함수 추가:
  ```python
  def parse_by_doc_type(doc_type, ...):
      # 현재는 모두 receipt 로 처리 (기존 extract_receipt_fields 그대로 호출)
      return extract_receipt_fields(...)
  ```
- 미래에 `if doc_type == "invoice_statement": return extract_invoice_fields(...)` 같은 분기 가능.

**금지:**
- invoice_statement 신규 추출 로직 금지 — 다음 단계 작업
- doc_type 분기 조건 금지 — 현재는 모두 동일 함수
- 응답 형식 변경 금지

**검증:** Phase 검증 절차 전체.

---

## 5. 각 Phase 검증 방법

각 Phase 종료 후 **반드시** 다음 절차를 모두 수행한다.

### 5.1 정적 검증

```bash
# Python 컴파일 검증
python -m py_compile ocr-server/main.py
python -m py_compile ocr-server/pipeline/*.py
python -m py_compile ocr-server/extractors/*.py
python -m py_compile ocr-server/policies/*.py
python -m py_compile ocr-server/utils/*.py
python -m py_compile ocr-server/routes/*.py

# import 정상 확인
cd ocr-server && python -c "import main"
```

### 5.2 서버 기동 검증

```bash
# 서버 기동 후
curl -fsS http://localhost:9100/health
# 응답: {"status":"ok"}
```

### 5.3 회귀 검증 (필수 순서)

1. **google 전체** 검증 (실전형 generalization)
2. **baseline_fast** 검증 (5장 회귀 빠른 확인)
3. **baseline 전체** 검증 (10장 회귀 완전 확인)

검증 결과는 [docs/BASELINE_LOCK_20260425.md](BASELINE_LOCK_20260425.md) 와 [docs/GOOGLE_LOCK_20260425.md](GOOGLE_LOCK_20260425.md) 의 모든 수치와 동일해야 한다.

### 5.4 결과 diff 확인

각 Phase 직전/직후의 validation_results JSON 을 비교:

```bash
diff <(jq -S 'del(.generated_at) | del(.summary.avg_total_ms) | del(.summary.avg_detect_orientation_ms) | del(.summary.avg_full_ocr_ms) | del(.summary.avg_upper_reocr_total_ms) | del(.summary.avg_amount_reocr_total_ms)' before.json) \
     <(jq -S 'del(.generated_at) | del(.summary.avg_total_ms) | del(.summary.avg_detect_orientation_ms) | del(.summary.avg_full_ocr_ms) | del(.summary.avg_upper_reocr_total_ms) | del(.summary.avg_amount_reocr_total_ms)' after.json)
# 빈 출력이어야 함 (timing 외 모든 값 동일)
```

processing_time 등 timing 값은 무시한다 (기능 검증이 목적).

---

## 6. 리팩토링 성공 기준

한 Phase 든 전체 리팩토링이든, 다음이 100% 유지되어야 성공이다.

### 6.1 Baseline 회귀 기준

- baseline OCR 자체 점수: **43/57**
- baseline 최종 채택값 점수: **52/57**
- baseline 사업자번호 recall: **9/9**
- baseline 총합계금액: **8/10**
- baseline selected: **8** / suppression: **2** / unknown: **0**
- 1.jpg 총합계금액 = `10,560`
- 4.jpg 총합계금액 = `17,600`
- 10.jpg status = `selected` / 총합계금액 = `19,250`
- 9.jpg = `suppressed_bank_slip`
- a2.jpg = `suppressed_handwritten`

### 6.2 Google 회귀 기준

- google selected: **10** / suppression: **1** / unknown: **0** / error: **0**
- 7.jpg = `receipt_pos` / `selected`
- 7.jpg 회사명 = `GS25성신로데오점`
- 7.jpg 총합계금액 = `7,650`
- 7.jpg 전화 = `02-927-2369`
- 6.jpg = `suppressed_bank_slip`
- 11.jpg phone = `02-33-4278`, address = `서울시 마포구홍익로 6길26 163-12호`
- 8.jpg 회사명 공란 유지

### 6.3 API 호환성

- 모든 route URL 동일
- 모든 response JSON key 동일
- 모든 query parameter 동일
- frontend `mysuit-ocr` typecheck/build 통과

---

## 7. 리스크

### 7.1 import 순환 위험

- `extractors/company.py` ↔ `extractors/representative.py` (slash pair 공유)
  - **완화책:** company 모듈에 slash pair 를 두고 representative 가 import. 양방향 import 금지.
- `policies/` ↔ `extractors/` (extractor 결과를 policy 가 검증)
  - **완화책:** policy 는 extractor 를 import 하지 않고 dict in/out 으로만 처리.
- `pipeline/response_builder.py` ↔ 모든 모듈 (응답 조립)
  - **완화책:** response_builder 는 모든 결과를 인자로 받기만 하고 다른 pipeline 함수를 직접 호출하지 않음.

### 7.2 regex / normalize 의미 변화

- 정규식 옮길 때 `re.compile` 호출 시점 변경으로 인한 부작용 (모듈 로드 시점 vs lazy)
  - **완화책:** 모두 모듈 레벨 상수로 두고, lazy compile 도입 금지.
- `_clean_number` swap 사전이 다른 함수에서도 이미 swap 된 입력을 받는 경우 중복 swap 위험
  - **완화책:** swap 사전은 idempotent (한 번 더 적용해도 결과 동일). 이미 검증되어 있음.

### 7.3 row grouping side effect

- `_group_rows` 의 vertical_layout 판정은 median 계산에 의존. 함수 분리 중 median 계산식이 부동소수점 차이로 다른 결과를 낼 수 있음.
  - **완화책:** 분리 시 함수 본문을 그대로 복사. `import` 만 변경. 어떤 식 수정도 금지.

### 7.4 upper bbox / amount bbox side effect

- bbox 계산은 keyword 셋 + height bound + tail keyword 컷오프의 조합. 모든 항목이 정확히 같은 순서/조건이어야 함.
  - **완화책:** 함수 본문 1:1 복사. 키워드 리스트 alphabetize 같은 cosmetic 변경도 금지.
  - **추가 검증:** Phase R3 직후 google 7.jpg / 11.jpg / baseline 1.jpg 의 bbox 디버그 출력을 직접 비교.

### 7.5 field_sources 누락

- `_extract_fields_from_rows` 는 호출자가 `field_sources` dict 를 미리 만들어 넣어야 함. response builder 분리 시 누락 가능.
  - **완화책:** `field_sources` 가 최종 응답에 포함되는지 회귀 검증 (response shape 비교).

### 7.6 debug payload 누락

- debug dict (`amount_debug`, `document_classification`, `field_sources`, `upper_reocr_ran`, `amount_reocr_ran` 등) 가 빠지면 프런트엔드 디버그 패널이 깨진다.
  - **완화책:** Phase R5 직후 프런트엔드 디버그 패널 (`DebugPanel`) 이 모든 필드를 표시하는지 확인.

### 7.7 performance regression

- 함수 import 추가로 cold start 가 느려질 수 있음.
- `re.compile` 위치가 여러 모듈로 분산되면 모듈 로드 시점이 분산.
  - **완화책:** Phase 후 `avg_total_ms`, `avg_full_ocr_ms` 가 ±10% 이내인지 확인. 큰 변화가 있으면 import 구조 재점검.

### 7.8 routes 분리 시 dependency injection

- FastAPI route 가 `get_ocr_engine()` 같은 lazy 싱글톤에 의존. routes 모듈에서 import 시 circular import 위험.
  - **완화책:** routes 모듈은 `pipeline.ocr_runner` 만 import 하고, `pipeline.ocr_runner` 는 외부 모듈을 import 하지 않게 유지.

---

## 8. 첫 실제 리팩토링 작업 추천

다음 실제 작업은 **Phase R1 — Utils 분리** 다.

단, R1 안에서도 한 번에 모두 옮기지 말고 **가장 안전한 것부터** 시작한다.

### 8.1 R1 권장 순서 (R1 의 sub-phase)

1. **R1-a: `utils/text_normalize.py`** — `_clean_number`, `_clean_inline_field_value`
   - 이유: 외부 의존 없음, 순수 문자열 함수, regex 도 단순.
   - 옮기고 회귀 검증 → 통과하면 commit.
2. **R1-b: `utils/regex_patterns.py`** — 모든 `_XXX_RE` 상수
   - 이유: 정규식 자체는 변경 없이 위치만 이동.
   - 주의: import 순서 / 모듈 로드 시점이 변하지 않게 한다.
   - 옮기고 회귀 검증 → 통과하면 commit.
3. **R1-c: `utils/rows.py`** — `_group_rows`, `_row_text`, `_single_line_rows`
   - 이유: row grouping 은 약간의 위험 (median 계산). 단독 commit 으로 격리.
   - 옮기고 회귀 검증 → 통과하면 commit.
4. **R1-d: `utils/io_json.py`** — `_load_json`, `_save_json`
   - 이유: 가장 단순. 거의 무위험.
   - 옮기고 회귀 검증 → 통과하면 commit.

각 sub-phase 마다 baseline_fast → google → baseline 순서로 검증한다.

### 8.2 R1 시작 전 준비

- 작업 시작 전 `ocr-server/main.py` 를 `backup/main_20260426_<HHMM>_before_refactor_R1a.py` 형식으로 백업.
- 작업 중 `validation_results_*.json` 을 새로 만들지 않는다 (lock 보호).
- 작업 후 검증 시 새 validation 파일을 만들면 `_after_refactor_R1a.json` 식으로 명시적 suffix 사용.

---

## 9. 본 리팩토링 이후

다음 작업은 본 문서 범위가 아니다. 참고용으로만 기록.

- **거래명세서 진입:** `extractors/invoice_statement.py` 신규 작성, `schemas/invoice_schema.py` 채움, `parse_by_doc_type` 분기에 invoice_statement 케이스 추가.
- **OCR 인식 개선 재개:** `extractors/` 모듈 단위로 안전하게 개선 가능.
- **신규 documentType 추가:** `medical_receipt`, `food_cafe_receipt` 별 specialized extractor.

---

## 10. 본 문서의 위치

- 본 문서는 docs/REFACTOR_PLAN_20260426.md 에 위치한다.
- 본 문서는 코드 변경을 동반하지 않는다.
- 본 문서 자체는 Phase 가 진행되어도 수정하지 않는다 (계획 기록 보존). Phase 별 상세 결과는 별도 문서 (`docs/REFACTOR_R1_RESULT_*.md` 등) 로 기록.
