# REFACTOR R1-c-2 RESULT 2026-04-26

Phase R1-c-2 실행 결과 기록 문서.
계획 문서: [docs/REFACTOR_PLAN_20260426.md](REFACTOR_PLAN_20260426.md)
분석 문서: [docs/REFACTOR_R1C_ANALYSIS_20260426.md](REFACTOR_R1C_ANALYSIS_20260426.md)
선행 단계: [docs/REFACTOR_R1C_1_RESULT_20260426.md](REFACTOR_R1C_1_RESULT_20260426.md)

---

## 1. 작업 요약

- **작업**: `_is_merchant_notice_row` 를 main.py 에서 `ocr-server/utils/rows.py` 로 이동
- **성격**: 순수 위치 이동. 인라인 regex 2개 포함 함수 본문 1자도 변경 없음.
- **코드 변경 영향 범위**: main.py 라인 수 2387 -> 2378 (함수 정의 11줄 제거, import 1단어 추가, 순감 9라인)

---

## 2. 이동한 함수

| 함수명 | 원래 위치 | 새 위치 |
|---|---|---|
| `_is_merchant_notice_row` | main.py L154-163 | utils/rows.py |

### 함수 본문 동일성 확인 (AST 비교)

```
IDENTICAL: _is_merchant_notice_row
```

인라인 regex 2개 포함 본문 전체 AST-동일 확인 완료.

---

## 3. 생성/수정 파일 목록

| 파일 | 구분 | 내용 |
|---|---|---|
| `backup/main_20260426_1754_before_refactor_r1c_2_notice_row.py` | 백업 | 리팩토링 전 main.py |
| `backup/rows_20260426_1754_before_refactor_r1c_2_notice_row.py` | 백업 | 리팩토링 전 rows.py |
| `ocr-server/utils/rows.py` | 수정 | `import re` 추가 + `_is_merchant_notice_row` 추가 |
| `ocr-server/main.py` | 수정 | 함수 정의 제거, import 에 `_is_merchant_notice_row` 추가 |

---

## 4. main.py import 구조

```python
from utils.rows import _row_text, _single_line_rows, _is_merchant_notice_row
```

## 5. utils/rows.py 최종 구조

```python
import re


def _row_text(row):
    return ' '.join(t for _, t, _ in row)


def _single_line_rows(ocr_lines: list):
    return [[line] for line in (ocr_lines or []) if line and line[1]]


def _is_merchant_notice_row(text: str) -> bool:
    norm = re.sub(r'\s+', '', text or '')
    if re.search(r'다른경우|실제와|가맹점주소가|...', norm, re.I):
        return True
    return bool(re.search(
        r'신고안내|여신금융|...', norm, re.I,
    ))
```

---

## 6. 정적 검증 결과

| 항목 | 결과 |
|---|---|
| `python -m py_compile utils/rows.py` | PASS |
| `python -m py_compile main.py` | PASS |
| `python -c "import main"` | PASS |
| AST 함수 본문 동일성 검증 | IDENTICAL (1/1) |

---

## 7. Live 검증 결과 (2026-04-26 17:57)

검증 스크립트: `ocr-server/validate_r1c2.py`
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

결과 파일: `mysuit-ocr/public/data/testsets/baseline_fast/validation_results_baseline_fast_after_refactor_r1c_2_notice_row.json`

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

결과 파일: `mysuit-ocr/public/data/testsets/google/validation_results_google_after_refactor_r1c_2_notice_row.json`

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

결과 파일: `mysuit-ocr/public/data/testsets/baseline/validation_results_baseline_after_refactor_r1c_2_notice_row.json`

### OVERALL: ALL PASS

---

## 8. 결과 변화 여부

**없음.** 모든 수치 lock 기준 동일 유지.

이유:
- 인라인 regex 포함 함수 본문을 1자도 변경하지 않고 이동.
- AST 동일성 검증 완료.
- company/representative 추출 영역에서 3곳 호출되지만 모두 동일하게 작동.

---

## 9. R1-c-2 완료 확정

- 정적 검증: PASS
- AST 본문 동일성: PASS (1/1)
- Live baseline_fast: PASS
- Live google: PASS
- Live baseline: PASS

**Phase R1-c-2 완전 완료.**

R1-c 진행 현황:
- R1-c-1 `_row_text`, `_single_line_rows`: 완료
- R1-c-2 `_is_merchant_notice_row`: 완료
- R1-c-3 `_group_rows`: 미시작

---

## 10. 다음 단계

**Phase R1-c-3: `_group_rows` 이동 (HIGH risk, 단독 commit 필수)**

대상:
- `_group_rows` (main.py L108-148, 41라인)
- median 계산, vertical_layout 분기, threshold scaling 포함.
- 함수 본문 1바이트도 변경 금지.
- utils/rows.py 에 추가.

주의:
- R1-c 중 가장 위험한 이동.
- `extract_receipt_fields` 의 입구에서 full/upper/amount 3번 호출됨.
- 이동 후 baseline_fast -> google -> baseline 전체 결과가 완전히 동일해야 함.
- R1-c-3 시작 전 main.py 와 rows.py 모두 백업 필수.
- 결과 검증 시 분석 문서 §10.4 의 전체 row diff 확인 권장.
