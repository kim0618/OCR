# REFACTOR R2-c RESULT 2026-04-26

Phase R2-c 실행 결과 기록 문서.
계획 문서: [docs/REFACTOR_PLAN_20260426.md](REFACTOR_PLAN_20260426.md)
분석 문서: [docs/REFACTOR_R2_ANALYSIS_20260426.md](REFACTOR_R2_ANALYSIS_20260426.md)
선행 단계: [docs/REFACTOR_R2B_RESULT_20260426.md](REFACTOR_R2B_RESULT_20260426.md)

---

## 1. 작업 요약

- **작업**: phone extractor/helper 5개를 main.py 에서 `ocr-server/extractors/phone.py` 로 이동
- **성격**: 순수 위치 이동. 함수 본문 1자도 변경 없음.
- **코드 변경 영향 범위**: main.py 라인 수 2288 -> 2234 (함수 정의 54줄 제거, import 6줄 추가, 순감 54라인)
- **`_extract_rep_phone_pair` 는 미이동** — representative 의존성으로 R2-d에서 처리.

---

## 2. 이동한 함수

| 함수명 | 원래 위치 | 새 위치 |
|---|---|---|
| `_normalize_phone_digits` | main.py L114-115 | extractors/phone.py |
| `_format_phone_digits` | main.py L118-129 | extractors/phone.py |
| `_valid_phone_digits` | main.py L132-137 | extractors/phone.py |
| `_valid_labeled_phone_digits` | main.py L140-145 | extractors/phone.py |
| `_extract_phone_candidate` | main.py L148-172 | extractors/phone.py |

### 함수 본문 동일성 확인 (AST 비교)

```
IDENTICAL: _extract_phone_candidate
IDENTICAL: _format_phone_digits
IDENTICAL: _normalize_phone_digits
IDENTICAL: _valid_labeled_phone_digits
IDENTICAL: _valid_phone_digits
```

### Phone smoke tests

```
smoke tests PASS:
- _extract_phone_candidate("031-479-0485") == "031-479-0485"  ✓
- _extract_phone_candidate("TEL:02)33-4278") == "02-33-4278"  ✓
- _extract_phone_candidate("010-9388-9936") == "010-9388-9936"  ✓
- _valid_phone_digits("0314790485") == True  ✓
- _valid_phone_digits("12345") == False  ✓
- _format_phone_digits("0314790485") == "031-479-0485"  ✓
```

---

## 3. 생성/수정 파일 목록

| 파일 | 구분 | 내용 |
|---|---|---|
| `backup/main_20260426_1932_before_refactor_r2c_phone.py` | 백업 | 리팩토링 전 main.py |
| `ocr-server/extractors/phone.py` | 신규 | 5개 phone 함수 정의 |
| `ocr-server/main.py` | 수정 | 5개 함수 정의 제거, `from extractors.phone import ...` 추가 |

---

## 4. main.py import 구조

```python
from extractors.common import _bad_top_text_candidate, _extract_until_next_label
from extractors.business_number import _validate_biz_number, _extract_biz_number
from extractors.phone import (
    _normalize_phone_digits,
    _format_phone_digits,
    _valid_phone_digits,
    _valid_labeled_phone_digits,
    _extract_phone_candidate,
)
```

## 5. extractors/phone.py 구조

```python
import re
from utils.regex_patterns import _PHONE_LABELED_RE, _PHONE_ADMIN_NOISE_RE

def _normalize_phone_digits(text: str) -> str: ...
def _format_phone_digits(digits: str) -> str: ...
def _valid_phone_digits(digits: str) -> bool: ...
def _valid_labeled_phone_digits(digits: str) -> bool: ...
def _extract_phone_candidate(text: str) -> str: ...
```

import 순환 없음: `extractors/phone.py` → `utils.regex_patterns` (한 방향).

---

## 6. 정적 검증 결과

| 항목 | 결과 |
|---|---|
| `python -m py_compile extractors/phone.py` | PASS |
| `python -m py_compile main.py` | PASS |
| `python -c "import main"` | PASS |
| AST 함수 본문 동일성 | IDENTICAL (5/5) |
| Phone smoke tests | PASS (6/6) |

---

## 7. Live 검증 결과 (2026-04-26 19:47, 재검증)

**1차 검증** (19:35): 기댓값 오류로 실패 — `2.jpg`, `8.jpg` 전화번호의 기댓값을 raw digits 형태(`03147900090`)로 잘못 설정함. 실제 OCR 출력은 하이픈 포맷(`031-479-0090`)으로 BASELINE_LOCK 기준 정확히 일치.

**2차 검증** (19:47): 기댓값을 BASELINE_LOCK 기준 하이픈 형식으로 수정 후 재실행 → ALL PASS.

### /health: `{"status": "ok"}`

### baseline_fast (5 images)

| 항목 | 기준 | 결과 |
|---|---|---|
| selected | 3 | **3** OK |
| suppression | 2 | **2** OK |

결과 파일: `validation_results_baseline_fast_after_refactor_r2c_phone.json`

### google (11 images)

| 항목 | 기준 | 결과 |
|---|---|---|
| selected | 10 | **10** OK |
| suppression | 1 | **1** OK |
| 7.jpg phone | 02-927-2369 | **02-927-2369** OK |
| 11.jpg phone | 02-33-4278 | **02-33-4278** OK |
| 6.jpg | suppressed_bank_slip | OK |

결과 파일: `validation_results_google_after_refactor_r2c_phone.json`

### baseline (10 images) — 전화번호 8/8

| 파일 | 기준 (BASELINE_LOCK) | 결과 |
|---|---|---|
| 1.jpg | 031-479-0485 | **031-479-0485** OK |
| 2.jpg | 031-479-0090 | **031-479-0090** OK |
| 3.jpg | 031-479-2280 | **031-479-2280** OK |
| 4.jpg | 031-479-3690 | **031-479-3690** OK |
| 7.jpg | 031-388-1080 | **031-388-1080** OK |
| 8.jpg | 031-455-9955 | **031-455-9955** OK |
| 10.jpg | 010-9388-9936 | **010-9388-9936** OK |
| a2.jpg | 031-479-2280 | **031-479-2280** OK |

**Phone checks: 8/8**

결과 파일: `validation_results_baseline_after_refactor_r2c_phone.json`

### OVERALL: ALL PASS

---

## 8. 1차 실패 원인 및 조치

| 항목 | 내용 |
|---|---|
| 실패 원인 | 테스트 스크립트 기댓값 오류. `2.jpg: 03147900090`, `8.jpg: 0314559955` (raw digits) 로 설정했으나 실제 출력은 하이픈 포맷 |
| OCR 변화 여부 | 없음. `_format_phone_digits` AST 동일 확인, 실제 출력 불변 |
| 조치 | 기댓값을 BASELINE_LOCK 실제 값 (`031-479-0090`, `031-455-9955`) 으로 수정 후 재검증 |
| 결과 | ALL PASS |

---

## 9. 결과 변화 여부

**없음.** 5개 함수 AST 동일, 모든 전화번호 lock 기준 유지.

---

## 10. R2-c 완료 확정

**Phase R2-c 완전 완료.**

R2 진행 현황:
- R2-a `extractors/common.py`: 완료
- R2-b `extractors/business_number.py`: 완료
- R2-c `extractors/phone.py`: 완료
- R2-d `extractors/representative.py`: 미시작
- R2-e `extractors/address.py`: 미시작
- R2-f `extractors/company.py`: 미시작

---

## 11. 다음 단계

**Phase R2-d: `extractors/representative.py` 분리 (MEDIUM risk)**

대상:
- `_is_bad_representative_candidate` (main.py) — `utils.text_normalize` + `utils.regex_patterns` 의존.
- `_extract_rep_phone_pair` (main.py) — `extractors.phone` + 이 단계의 `_is_bad_representative_candidate` 의존.

`_extract_rep_phone_pair` 는 phone helper 를 호출하므로 phone (R2-c) 완료 후에만 진행 가능. ✓ 조건 충족됨.

import 순서: `extractors/representative.py` → `extractors/phone.py` → `utils/regex_patterns.py` (한 방향).

주의:
- R2-d 완료 후 baseline 대표자 추출 (특히 정공구 4.jpg/a1.jpg 대표자) 확인.
- R2-d 시작 전 main.py 백업 필수.
