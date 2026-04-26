# REFACTOR R2-a RESULT 2026-04-26

Phase R2-a 실행 결과 기록 문서. **Phase R2 (extractor 분리) 의 첫 sub-phase.**
계획 문서: [docs/REFACTOR_PLAN_20260426.md](REFACTOR_PLAN_20260426.md)
분석 문서: [docs/REFACTOR_R2_ANALYSIS_20260426.md](REFACTOR_R2_ANALYSIS_20260426.md)

---

## 1. 작업 요약

- **작업**: `_bad_top_text_candidate`, `_extract_until_next_label` 를 main.py 에서 `ocr-server/extractors/common.py` 로 이동
- **성격**: 순수 위치 이동. 함수 본문 1자도 변경 없음.
- **의의**: `extractors/` 패키지 신규 생성. R2 의 모든 후속 extractor 모듈들이 이 common 을 import 가능.
- **코드 변경 영향 범위**: main.py 라인 수 2326 -> 2307 (함수 정의 19줄 제거, import 1줄 추가, 순감 19라인)

---

## 2. 이동한 함수

| 함수명 | 원래 위치 | 새 위치 |
|---|---|---|
| `_extract_until_next_label` | main.py L120-126 | extractors/common.py |
| `_bad_top_text_candidate` | main.py L141-149 | extractors/common.py |

### 함수 본문 동일성 확인 (AST 비교)

```
IDENTICAL: _extract_until_next_label
IDENTICAL: _bad_top_text_candidate
```

---

## 3. 생성/수정 파일 목록

| 파일 | 구분 | 내용 |
|---|---|---|
| `backup/main_20260426_1852_before_refactor_r2a_extractors_common.py` | 백업 | 리팩토링 전 main.py |
| `ocr-server/extractors/__init__.py` | 신규 | 빈 패키지 초기화 |
| `ocr-server/extractors/common.py` | 신규 | `_extract_until_next_label`, `_bad_top_text_candidate` 정의 |
| `ocr-server/main.py` | 수정 | 두 함수 정의 제거, `from extractors.common import ...` 추가 |

---

## 4. main.py import 구조

```python
from utils.rows import _row_text, _single_line_rows, _is_merchant_notice_row, _group_rows
from utils.io_json import _load_json, _save_json
from extractors.common import _bad_top_text_candidate, _extract_until_next_label
```

## 5. extractors/common.py 구조

```python
import re

from utils.text_normalize import _clean_inline_field_value
from utils.regex_patterns import _NEXT_LABEL_RE


def _extract_until_next_label(text: str, pattern: str) -> str: ...
def _bad_top_text_candidate(text: str) -> bool: ...
```

import 순환 없음: `extractors/common.py` → `utils/` (한 방향, main.py 를 import 하지 않음).

---

## 6. 정적 검증 결과

| 항목 | 결과 |
|---|---|
| `python -m py_compile extractors/common.py` | PASS |
| `python -m py_compile main.py` | PASS |
| `python -c "import main"` | PASS |
| AST 함수 본문 동일성 검증 | IDENTICAL (2/2) |

---

## 7. Live 검증 결과 (2026-04-26 18:54)

검증 스크립트: `ocr-server/validate_r2a.py`
순서: uvicorn 9100 재기동 -> `/health` -> baseline_fast -> google -> baseline

### /health: `{"status": "ok"}`

### baseline_fast (5 images)

| 항목 | 기준 | 결과 |
|---|---|---|
| selected | 3 | **3** OK |
| suppression | 2 | **2** OK |
| unknown | 0 | **0** OK |
| 9.jpg | suppressed_bank_slip | OK |
| a2.jpg | suppressed_handwritten | OK |

결과 파일: `validation_results_baseline_fast_after_refactor_r2a_extractors_common.json`

### google (11 images)

| 항목 | 기준 | 결과 |
|---|---|---|
| selected | 10 | **10** OK |
| suppression | 1 | **1** OK |
| 7.jpg company | GS25성신로데오점 | OK |
| 7.jpg amount | 7,650 | OK |
| 7.jpg phone | 02-927-2369 | OK |
| 6.jpg | suppressed_bank_slip | OK |

결과 파일: `validation_results_google_after_refactor_r2a_extractors_common.json`

### baseline (10 images)

| 항목 | 기준 | 결과 |
|---|---|---|
| selected | 8 | **8** OK |
| suppression | 2 | **2** OK |
| 1.jpg amount | 10,560 | OK |
| 4.jpg amount | 17,600 | OK |
| 10.jpg amount | 19,250 | OK |

결과 파일: `validation_results_baseline_after_refactor_r2a_extractors_common.json`

### OVERALL: ALL PASS

---

## 8. 결과 변화 여부

**없음.** 함수 본문 AST 동일 확인, 모든 lock 기준 유지.

이유:
- `_bad_top_text_candidate`: `re` 만 의존, 순수 함수.
- `_extract_until_next_label`: `_NEXT_LABEL_RE` (regex_patterns) + `_clean_inline_field_value` (text_normalize) 의존. 모두 이미 분리된 utils 모듈 → import 경로 정확.
- 5개 함수가 이 두 함수에 의존하나 이름이 동일하므로 호출부 무변경.

---

## 9. R2-a 완료 확정

- 정적 검증: PASS
- AST 본문 동일성: PASS (2/2)
- Live baseline_fast / google / baseline: ALL PASS

**Phase R2-a 완전 완료.**

R2 진행 현황:
- R2-a `extractors/common.py`: 완료
- R2-b `extractors/business_number.py`: 미시작
- R2-c `extractors/phone.py`: 미시작
- R2-d `extractors/representative.py`: 미시작
- R2-e `extractors/address.py`: 미시작
- R2-f `extractors/company.py`: 미시작

---

## 10. 다음 단계

**Phase R2-b: `extractors/business_number.py` 분리 (LOW risk)**

대상:
- `_validate_biz_number` (main.py L~61-69): 체크섬 검증. 의존: `re` 만.
- `_extract_biz_number` (main.py L~72-80): 추출 + 검증. 의존: `utils.text_normalize._clean_number`, `_validate_biz_number`, `re`.

import 구조: `extractors/business_number.py` → `utils.text_normalize` (한 방향, 순환 없음).

주의:
- `_extract_biz_number` 는 사업자번호 anchor 역할로 매우 중요. 이동 후 baseline 사업자번호 9/9 반드시 확인.
- R2-b 시작 전 main.py 백업 필수.
