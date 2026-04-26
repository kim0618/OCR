# REFACTOR R2-b RESULT 2026-04-26

Phase R2-b 실행 결과 기록 문서.
계획 문서: [docs/REFACTOR_PLAN_20260426.md](REFACTOR_PLAN_20260426.md)
분석 문서: [docs/REFACTOR_R2_ANALYSIS_20260426.md](REFACTOR_R2_ANALYSIS_20260426.md)
선행 단계: [docs/REFACTOR_R2A_RESULT_20260426.md](REFACTOR_R2A_RESULT_20260426.md)

---

## 1. 작업 요약

- **작업**: `_validate_biz_number`, `_extract_biz_number` 를 main.py 에서 `ocr-server/extractors/business_number.py` 로 이동
- **성격**: 순수 위치 이동. 함수 본문 + 체크섬 로직 1자도 변경 없음.
- **코드 변경 영향 범위**: main.py 라인 수 2307 -> 2288 (함수 정의 19줄 제거, import 1줄 추가, 순감 19라인)

---

## 2. 이동한 함수

| 함수명 | 원래 위치 | 새 위치 |
|---|---|---|
| `_validate_biz_number` | main.py L62-70 | extractors/business_number.py |
| `_extract_biz_number` | main.py L73-81 | extractors/business_number.py |

### 함수 본문 동일성 확인 (AST 비교)

```
IDENTICAL: _validate_biz_number
IDENTICAL: _extract_biz_number
```

### 체크섬 smoke test

```
checksum smoke tests PASS
- _validate_biz_number("1388168468") == True  ✓
- _extract_biz_number("138-81-68468") == "138-81-68468"  ✓
- _extract_biz_number("no biz here") is None  ✓
```

---

## 3. 생성/수정 파일 목록

| 파일 | 구분 | 내용 |
|---|---|---|
| `backup/main_20260426_1915_before_refactor_r2b_business_number.py` | 백업 | 리팩토링 전 main.py |
| `ocr-server/extractors/business_number.py` | 신규 | `_validate_biz_number`, `_extract_biz_number` 정의 |
| `ocr-server/main.py` | 수정 | 두 함수 정의 제거, `from extractors.business_number import ...` 추가 |

---

## 4. main.py import 구조

```python
from extractors.common import _bad_top_text_candidate, _extract_until_next_label
from extractors.business_number import _validate_biz_number, _extract_biz_number
```

## 5. extractors/business_number.py 구조

```python
import re
from utils.text_normalize import _clean_number

def _validate_biz_number(digits: str) -> bool: ...   # 체크섬 검증 (가중치, mod 10)
def _extract_biz_number(text: str) -> str | None: ... # 패턴 + 체크섬 추출
```

import 순환 없음: `extractors/business_number.py` → `utils.text_normalize` (한 방향).

---

## 6. 정적 검증 결과

| 항목 | 결과 |
|---|---|
| `python -m py_compile extractors/business_number.py` | PASS |
| `python -m py_compile main.py` | PASS |
| `python -c "import main"` | PASS |
| AST 함수 본문 동일성 | IDENTICAL (2/2) |
| 체크섬 smoke tests | PASS (3/3) |

---

## 7. Live 검증 결과 (2026-04-26 19:18)

검증 스크립트: `ocr-server/validate_r2b.py`
순서: uvicorn 9100 재기동 -> `/health` -> baseline_fast -> google -> baseline

### /health: `{"status": "ok"}`

### baseline_fast (5 images)

| 항목 | 기준 | 결과 |
|---|---|---|
| selected | 3 | **3** OK |
| suppression | 2 | **2** OK |
| 9.jpg | suppressed_bank_slip | OK |
| a2.jpg | suppressed_handwritten | OK |

결과 파일: `validation_results_baseline_fast_after_refactor_r2b_business_number.json`

### google (11 images)

| 항목 | 기준 | 결과 |
|---|---|---|
| selected | 10 | **10** OK |
| suppression | 1 | **1** OK |
| 7.jpg company | GS25성신로데오점 | OK |
| 7.jpg amount | 7,650 | OK |
| 7.jpg phone | 02-927-2369 | OK |
| 6.jpg | suppressed_bank_slip | OK |

결과 파일: `validation_results_google_after_refactor_r2b_business_number.json`

### baseline (10 images)

| 항목 | 기준 | 결과 |
|---|---|---|
| selected | 8 | **8** OK |
| suppression | 2 | **2** OK |
| 1.jpg amount | 10,560 | OK |
| 4.jpg amount | 17,600 | OK |
| 10.jpg amount | 19,250 | OK |

결과 파일: `validation_results_baseline_after_refactor_r2b_business_number.json`

### 사업자번호 recall (9/9)

| 파일 | 기준 | 결과 |
|---|---|---|
| 1.jpg | 138-81-68468 | **138-81-68468** OK |
| 2.jpg | 138-08-99333 | **138-08-99333** OK |
| 3.jpg | 119-10-88385 | **119-10-88385** OK |
| 4.jpg | 123-23-94265 | **123-23-94265** OK |
| 7.jpg | 581-10-00658 | **581-10-00658** OK |
| 8.jpg | 134-04-13602 | **134-04-13602** OK |
| 10.jpg | 761-21-00890 | **761-21-00890** OK |
| a1.jpg | 123-23-94265 | **123-23-94265** OK |
| a2.jpg | 119-10-88385 | **119-10-88385** OK |

**Biz recall: 9/9** — lock 기준 완전 유지.

### OVERALL: ALL PASS

---

## 8. 결과 변화 여부

**없음.** 체크섬 로직 + 패턴 매칭 동일, 사업자번호 recall 9/9 유지.

---

## 9. R2-b 완료 확정

**Phase R2-b 완전 완료.**

R2 진행 현황:
- R2-a `extractors/common.py`: 완료
- R2-b `extractors/business_number.py`: 완료
- R2-c `extractors/phone.py`: 미시작
- R2-d `extractors/representative.py`: 미시작
- R2-e `extractors/address.py`: 미시작
- R2-f `extractors/company.py`: 미시작

---

## 10. 다음 단계

**Phase R2-c: `extractors/phone.py` 분리 (LOW-MEDIUM risk)**

대상 (5개, `_extract_rep_phone_pair` 는 R2-d):
- `_normalize_phone_digits`
- `_format_phone_digits`
- `_valid_phone_digits`
- `_valid_labeled_phone_digits`
- `_extract_phone_candidate`

의존: `utils.regex_patterns` (`_PHONE_LABELED_RE`, `_PHONE_ADMIN_NOISE_RE`) + `re`.
`_extract_rep_phone_pair` 는 `_is_bad_representative_candidate` (representative) 에 의존하므로 R2-d 로 미룬다.

주의:
- R2-c 완료 후 google 7.jpg `02-927-2369`, google 11.jpg `02-33-4278` 전화번호 유지 확인.
- R2-c 시작 전 main.py 백업 필수.
