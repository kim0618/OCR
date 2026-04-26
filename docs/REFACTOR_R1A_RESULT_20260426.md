# REFACTOR R1-a RESULT 2026-04-26

Phase R1-a 실행 결과 기록 문서.
계획 문서: [docs/REFACTOR_PLAN_20260426.md](REFACTOR_PLAN_20260426.md)

---

## 1. 작업 요약

- **작업**: `_clean_number`, `_clean_inline_field_value` 를 `ocr-server/utils/text_normalize.py` 로 이동
- **성격**: 순수 위치 이동. 함수 본문 1줄도 변경 없음.
- **코드 변경 영향 범위**: main.py 라인 수 2450 → 2441 (함수 정의 9줄 제거, import 1줄 추가)

---

## 2. 이동한 함수

| 함수명 | 원래 위치 | 새 위치 |
|---|---|---|
| `_clean_number` | main.py L48-51 | utils/text_normalize.py |
| `_clean_inline_field_value` | main.py L166-168 | utils/text_normalize.py |

### 함수 본문 동일성 확인

`_clean_number` — 백업과 신규 모듈 완전 동일:
```python
def _clean_number(s: str) -> str:
    s = s.replace('O', '0').replace('l', '1').replace('I', '1').replace('S', '5').replace('B', '8')
    s = re.sub(r'(\d)\.(\d{3})', r'\1,\2', s)  # 33.000 -> 33,000
    return s
```

`_clean_inline_field_value` — 백업과 신규 모듈 완전 동일:
```python
def _clean_inline_field_value(value: str) -> str:
    value = re.sub(r'\s+', ' ', value or '').strip()
    return value.strip(" :;|/-")
```

### 주의 사항 (테스트 중 발견)

`_clean_number('normal')` -> `'norma1'` (lowercase `l` -> `1`).
이것은 **원본 함수의 정상 동작**이며 리팩토링으로 인한 변화가 아니다.
OCR 에서 숫자 1을 `l` 로 오인식하는 경우를 교정하는 의도된 치환이다.

---

## 3. 생성/수정 파일 목록

| 파일 | 구분 | 내용 |
|---|---|---|
| `backup/main_20260426_1252_before_refactor_r1a_text_normalize.py` | 백업 | 리팩토링 전 main.py 전체 |
| `ocr-server/utils/__init__.py` | 신규 | 빈 패키지 초기화 파일 |
| `ocr-server/utils/text_normalize.py` | 신규 | `_clean_number`, `_clean_inline_field_value` 정의 |
| `ocr-server/main.py` | 수정 | 두 함수 정의 제거, `from utils.text_normalize import ...` 추가 |

---

## 4. main.py import 구조 변경

변경 전:
```python
from document_classifier import classify_document

def _clean_number(s: str) -> str:
    ...

def _clean_inline_field_value(value: str) -> str:
    ...
```

변경 후:
```python
from document_classifier import classify_document
from utils.text_normalize import _clean_number, _clean_inline_field_value
```

---

## 5. 정적 검증 결과

| 항목 | 결과 |
|---|---|
| `python -m py_compile utils/text_normalize.py` | PASS |
| `python -m py_compile main.py` | PASS |
| `python -c "from utils.text_normalize import ..."` | PASS |
| `python -c "import main"` | PASS |
| 동작 검증 (test_r1a.py) | ALL PASS |

동작 검증 항목:
- `_clean_number`: O/l/I/S/B 자리 치환 + 33.000->33,000 패턴 변환
- `_clean_inline_field_value`: 공백 정규화, 양끝 `:;|/-` 제거, None 입력 -> ""

---

## 6. Live 검증 결과 — 완료 (2026-04-26 13:15)

검증 스크립트: `ocr-server/validate_r1a.py`
실행 순서: uvicorn 9100 기동 -> `/health` -> baseline_fast -> google -> baseline

### /health

```
{"status": "ok"}
```

### baseline_fast (5 images)

| 항목 | 기준 | 결과 |
|---|---|---|
| selected | 3 | **3** OK |
| suppression | 2 | **2** OK |
| unknown | 0 | **0** OK |
| error | 0 | **0** OK |
| 9.jpg status | suppressed_bank_slip | **suppressed_bank_slip** OK |
| a2.jpg status | suppressed_handwritten | **suppressed_handwritten** OK |

결과 파일: `mysuit-ocr/public/data/testsets/baseline_fast/validation_results_baseline_fast_after_refactor_r1a_text_normalize.json`

### google (11 images)

| 항목 | 기준 | 결과 |
|---|---|---|
| selected | 10 | **10** OK |
| suppression | 1 | **1** OK |
| unknown | 0 | **0** OK |
| error | 0 | **0** OK |
| 7.jpg status | selected | **selected** OK |
| 7.jpg doc_type | receipt_pos | **receipt_pos** OK |
| 7.jpg company | GS25성신로데오점 | **GS25성신로데오점** OK |
| 7.jpg amount | 7,650 | **7,650** OK |
| 7.jpg phone | 02-927-2369 | **02-927-2369** OK |
| 6.jpg status | suppressed_bank_slip | **suppressed_bank_slip** OK |

결과 파일: `mysuit-ocr/public/data/testsets/google/validation_results_google_after_refactor_r1a_text_normalize.json`

### baseline (10 images)

| 항목 | 기준 | 결과 |
|---|---|---|
| selected | 8 | **8** OK |
| suppression | 2 | **2** OK |
| unknown | 0 | **0** OK |
| error | 0 | **0** OK |
| 9.jpg status | suppressed_bank_slip | **suppressed_bank_slip** OK |
| a2.jpg status | suppressed_handwritten | **suppressed_handwritten** OK |
| 1.jpg amount | 10,560 | **10,560** OK |
| 4.jpg amount | 17,600 | **17,600** OK |
| 10.jpg status | selected | **selected** OK |
| 10.jpg amount | 19,250 | **19,250** OK |

결과 파일: `mysuit-ocr/public/data/testsets/baseline/validation_results_baseline_after_refactor_r1a_text_normalize.json`

### OVERALL: ALL PASS

---

## 7. 결과 변화 여부

**없음.** baseline / google / baseline_fast 모든 수치가 lock 기준과 동일하게 유지됨.

이유:
- 이동한 두 함수는 외부 상태를 읽거나 변경하지 않는 순수 함수.
- 함수 본문은 백업 대비 1바이트도 변경되지 않았다.
- 25개의 call site 는 함수 이름이 동일하므로 기존 동작과 완전히 동일.
- `re.sub`, `str.replace`, `str.strip` 는 동일한 Python 런타임 환경에서 결정론적으로 동작.

---

## 8. R1-a 완료 확정

- 정적 검증: PASS
- 동작 단위 검증: PASS
- Live baseline_fast: PASS
- Live google: PASS
- Live baseline: PASS

**Phase R1-a 완전 완료.**

---

## 9. 다음 단계

**Phase R1-b: `utils/regex_patterns.py` 분리**

대상 (main.py 모듈 레벨 상수 전체):
- `_PHONE_RE`, `_PHONE_LABELED_RE`, `_PHONE_ADMIN_NOISE_RE`
- `_ADDR_START_RE`, `_NEXT_LABEL_RE`, `_FIELD_NOISE_RE`
- `_REPRESENTATIVE_NOISE_RE`, `_COMPANY_*_RE`
- `_PERSON_LIKE_NAME_RE`, `_REPRESENTATIVE_SURNAME_RE`
- `_ADDRESS_*_RE`, `_LABEL_ONLY_RE`, `_ADDRESS_CONTINUATION_RE` 등

주의:
- 정규식 패턴 문자 1자도 변경 금지
- `re.IGNORECASE`, `re.I` flag 동일 유지
- `re.compile()` 호출을 모듈 레벨에서 유지 (lazy compile 금지)
- R1-b 시작 전 main.py 백업 필수
- R1-b 완료 후 동일한 live validation 절차 수행
