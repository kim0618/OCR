# REFACTOR R1-c-1 RESULT 2026-04-26

Phase R1-c-1 실행 결과 기록 문서.
계획 문서: [docs/REFACTOR_PLAN_20260426.md](REFACTOR_PLAN_20260426.md)
분석 문서: [docs/REFACTOR_R1C_ANALYSIS_20260426.md](REFACTOR_R1C_ANALYSIS_20260426.md)

---

## 1. 작업 요약

- **작업**: `_row_text`, `_single_line_rows` 를 `ocr-server/utils/rows.py` 로 이동
- **성격**: 순수 위치 이동. 함수 본문 1자도 변경 없음.
- **코드 변경 영향 범위**: main.py 라인 수 2392 -> 2387 (함수 정의 5줄 제거, import 1줄 추가, 순감 5라인)

---

## 2. 이동한 함수

| 함수명 | 원래 위치 | 새 위치 |
|---|---|---|
| `_row_text` | main.py L151-152 | utils/rows.py |
| `_single_line_rows` | main.py L155-156 | utils/rows.py |

### 함수 본문 동일성 확인 (AST 비교)

```
IDENTICAL: _row_text
IDENTICAL: _single_line_rows
```

---

## 3. 생성/수정 파일 목록

| 파일 | 구분 | 내용 |
|---|---|---|
| `backup/main_20260426_1737_before_refactor_r1c_1_row_helpers.py` | 백업 | 리팩토링 전 main.py 전체 |
| `ocr-server/utils/rows.py` | 신규 | `_row_text`, `_single_line_rows` 정의 |
| `ocr-server/main.py` | 수정 | 두 함수 정의 제거, `from utils.rows import ...` 추가 |

---

## 4. main.py import 구조 변경

변경 전:
```python
from utils.text_normalize import _clean_number, _clean_inline_field_value
from utils.regex_patterns import (...)

def _row_text(row): ...
def _single_line_rows(ocr_lines: list): ...
```

변경 후:
```python
from utils.text_normalize import _clean_number, _clean_inline_field_value
from utils.rows import _row_text, _single_line_rows
from utils.regex_patterns import (...)
```

---

## 5. 정적 검증 결과

| 항목 | 결과 |
|---|---|
| `python -m py_compile utils/rows.py` | PASS |
| `python -m py_compile main.py` | PASS |
| `python -c "import main"` | PASS |
| AST 함수 본문 동일성 검증 | IDENTICAL (2/2) |

---

## 6. Live 검증 결과 (2026-04-26 17:40)

검증 스크립트: `ocr-server/validate_r1c1.py`
순서: uvicorn 9100 재기동 -> `/health` -> baseline_fast -> google -> baseline

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

결과 파일: `mysuit-ocr/public/data/testsets/baseline_fast/validation_results_baseline_fast_after_refactor_r1c_1_row_helpers.json`

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

결과 파일: `mysuit-ocr/public/data/testsets/google/validation_results_google_after_refactor_r1c_1_row_helpers.json`

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

결과 파일: `mysuit-ocr/public/data/testsets/baseline/validation_results_baseline_after_refactor_r1c_1_row_helpers.json`

### OVERALL: ALL PASS

---

## 7. 결과 변화 여부

**없음.** 모든 수치가 lock 기준과 동일.

이유:
- `_row_text`: 1줄 순수 함수, 외부 의존 없음.
- `_single_line_rows`: 1줄 순수 함수, 외부 의존 없음.
- `_row_text` 는 `amount_extractor.extract_amount_candidates` 에 callback 으로 전달되나 이름이 동일하므로 동일하게 작동.
- 본문 AST 동일성 확인 완료.

---

## 8. R1-c-1 완료 확정

- 정적 검증: PASS
- AST 본문 동일성: PASS (2/2)
- Live baseline_fast: PASS
- Live google: PASS
- Live baseline: PASS

**Phase R1-c-1 완전 완료.**

R1-c 진행 현황:
- R1-c-1 `_row_text`, `_single_line_rows`: 완료
- R1-c-2 `_is_merchant_notice_row`: 미시작
- R1-c-3 `_group_rows`: 미시작

---

## 9. 다음 단계

**Phase R1-c-2: `_is_merchant_notice_row` 이동 (MEDIUM risk)**

대상:
- `_is_merchant_notice_row` (main.py L159-168)
- 인라인 regex 2개를 함수 본문과 함께 그대로 이동.
- utils/rows.py 에 추가 (기존 `_row_text`, `_single_line_rows` 와 동일 파일).

주의:
- 인라인 regex 패턴 1자도 변경 금지.
- `re` 모듈 import 를 rows.py 상단에 추가.
- `_is_merchant_notice_row` 는 company/representative extractor 에서 3곳 호출되므로 이동 후 결과 변화 주시.
- R1-c-2 시작 전 main.py 백업 필수.
