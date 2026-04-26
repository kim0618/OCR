# REFACTOR R1-d RESULT 2026-04-26

Phase R1-d 실행 결과 기록 문서. **Phase R1 (utils 분리) 의 마지막 sub-phase 완료.**
계획 문서: [docs/REFACTOR_PLAN_20260426.md](REFACTOR_PLAN_20260426.md)

---

## 1. 작업 요약

- **작업**: `_load_json`, `_save_json` 를 main.py 에서 `ocr-server/utils/io_json.py` 로 이동
- **성격**: 순수 위치 이동. 함수 본문 1자도 변경 없음.
- **코드 변경 영향 범위**: main.py 라인 수 2337 -> 2326 (함수 정의 11줄 제거, import 1줄 추가, 순감 11라인)

---

## 2. 이동한 함수

| 함수명 | 원래 위치 | 새 위치 |
|---|---|---|
| `_load_json` | main.py L968-972 | utils/io_json.py |
| `_save_json` | main.py L975-977 | utils/io_json.py |

### 함수 본문 동일성 확인 (AST 비교)

```
IDENTICAL: _load_json
IDENTICAL: _save_json
```

---

## 3. 생성/수정 파일 목록

| 파일 | 구분 | 내용 |
|---|---|---|
| `backup/main_20260426_1829_before_refactor_r1d_io_json.py` | 백업 | 리팩토링 전 main.py |
| `ocr-server/utils/io_json.py` | 신규 | `_load_json`, `_save_json` 정의 |
| `ocr-server/main.py` | 수정 | 두 함수 정의 제거, `from utils.io_json import ...` 추가 |

---

## 4. main.py import 구조

```python
from utils.rows import _row_text, _single_line_rows, _is_merchant_notice_row, _group_rows
from utils.io_json import _load_json, _save_json
```

## 5. utils/io_json.py 구조

```python
import json
import os

def _load_json(path: str, default=None):
    if not os.path.exists(path):
        return default if default is not None else []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def _save_json(path: str, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
```

## 6. utils/ 모듈 현황 (R1 완료 시점)

```
ocr-server/utils/
  __init__.py
  text_normalize.py   (R1-a: _clean_number, _clean_inline_field_value)
  regex_patterns.py   (R1-b: 19개 정규식 상수)
  rows.py             (R1-c: _group_rows, _row_text, _single_line_rows, _is_merchant_notice_row)
  io_json.py          (R1-d: _load_json, _save_json)
```

---

## 7. 정적 검증 결과

| 항목 | 결과 |
|---|---|
| `python -m py_compile utils/io_json.py` | PASS |
| `python -m py_compile main.py` | PASS |
| `python -c "import main"` | PASS |
| AST 함수 본문 동일성 검증 | IDENTICAL (2/2) |

---

## 8. Live 검증 결과 (2026-04-26 18:30)

검증 스크립트: `ocr-server/validate_r1d.py`
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
| 9.jpg | suppressed_bank_slip | OK |
| a2.jpg | suppressed_handwritten | OK |

결과 파일: `validation_results_baseline_fast_after_refactor_r1d_io_json.json`

### google (11 images)

| 항목 | 기준 | 결과 |
|---|---|---|
| selected | 10 | **10** OK |
| suppression | 1 | **1** OK |
| 7.jpg company | GS25성신로데오점 | OK |
| 7.jpg amount | 7,650 | OK |
| 7.jpg phone | 02-927-2369 | OK |
| 6.jpg | suppressed_bank_slip | OK |

결과 파일: `validation_results_google_after_refactor_r1d_io_json.json`

### baseline (10 images)

| 항목 | 기준 | 결과 |
|---|---|---|
| selected | 8 | **8** OK |
| suppression | 2 | **2** OK |
| 1.jpg | 10,560 | OK |
| 4.jpg | 17,600 | OK |
| 10.jpg | 19,250 | OK |

결과 파일: `validation_results_baseline_after_refactor_r1d_io_json.json`

### OVERALL: ALL PASS

---

## 9. 결과 변화 여부

**없음.** 모든 수치 lock 기준 동일 유지.

---

## 10. R1 완료 확정 (전체)

Phase R1 (utils 분리) 의 모든 sub-phase 완료:

| Sub-phase | 대상 파일 | 이동 함수 수 | 상태 |
|---|---|---|---|
| R1-a | utils/text_normalize.py | 2 | ALL PASS |
| R1-b | utils/regex_patterns.py | 19개 상수 | ALL PASS |
| R1-c | utils/rows.py | 4 | ALL PASS |
| R1-d | utils/io_json.py | 2 | ALL PASS |

**Phase R1 (utils 분리) 완전 완료.**

main.py 라인 수 변화: 2450 (원본) -> **2326** (R1 완료 후). 총 124라인 감소.

---

## 11. 다음 단계

**Phase R2: extractor 분리**

계획 문서 §4 Phase R2 를 참조. 주요 대상:
- `extractors/business_number.py`: `_validate_biz_number`, `_extract_biz_number`
- `extractors/phone.py`: phone 관련 5개 함수
- `extractors/address.py`: address 관련 5개 함수
- `extractors/representative.py`: `_is_bad_representative_candidate`
- `extractors/company.py`: company 관련 6개 함수 + `_rescue_company_name`
- `extractors/fields_pipeline.py`: `_extract_fields_from_rows`, `_repair_remaining_top_fields_from_text_lines`

R2 는 R1 보다 함수 간 의존성이 복잡하므로, R2 시작 전 별도 분석 문서 작성 권장.
특히 company/representative 사이의 `_extract_company_rep_from_slash` 공유 함수 처리 방식을 미리 결정해야 한다.
