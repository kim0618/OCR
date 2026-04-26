# REFACTOR R1-c-3 RESULT 2026-04-26

Phase R1-c-3 실행 결과 기록 문서. **R1-c (rows.py 분리) 의 마지막 sub-phase, R1 단계 중 가장 위험한 이동.**
계획 문서: [docs/REFACTOR_PLAN_20260426.md](REFACTOR_PLAN_20260426.md)
분석 문서: [docs/REFACTOR_R1C_ANALYSIS_20260426.md](REFACTOR_R1C_ANALYSIS_20260426.md)
선행 단계: [docs/REFACTOR_R1C_1_RESULT_20260426.md](REFACTOR_R1C_1_RESULT_20260426.md), [docs/REFACTOR_R1C_2_RESULT_20260426.md](REFACTOR_R1C_2_RESULT_20260426.md)

---

## 1. 작업 요약

- **작업**: `_group_rows` 를 main.py 에서 `ocr-server/utils/rows.py` 로 이동
- **성격**: 순수 위치 이동. 41라인 함수 본문 1자도 변경 없음.
- **위험도**: HIGH (median 계산, vertical_layout 분기, threshold scaling, 모든 추출의 입구)
- **코드 변경 영향 범위**: main.py 라인 수 2378 -> 2337 (함수 정의 41줄 제거)

---

## 2. 이동한 함수

| 함수명 | 원래 위치 | 새 위치 |
|---|---|---|
| `_group_rows` | main.py L109-149 | utils/rows.py |

### 함수 본문 동일성 확인 (AST 비교)

```
IDENTICAL: _group_rows
NEW in rows.py: _row_text              (R1-c-1 에서 이미 이동됨)
NEW in rows.py: _is_merchant_notice_row (R1-c-2 에서 이미 이동됨)
NEW in rows.py: _single_line_rows      (R1-c-1 에서 이미 이동됨)
```

`_group_rows` AST-동일 확인: 41라인 본문 (median, threshold, vertical_layout, inner closures `cy`/`cx`/`width`/`height`, sort/threshold-grouping loop) 전부 backup main.py 와 완전 동일.

---

## 3. 생성/수정 파일 목록

| 파일 | 구분 | 내용 |
|---|---|---|
| `backup/main_20260426_1811_before_refactor_r1c_3_group_rows.py` | 백업 | 리팩토링 전 main.py |
| `backup/rows_20260426_1811_before_refactor_r1c_3_group_rows.py` | 백업 | 리팩토링 전 rows.py |
| `ocr-server/utils/rows.py` | 수정 | `_group_rows` 추가 (import re 직후, _row_text 앞) |
| `ocr-server/main.py` | 수정 | 함수 정의 제거, import 에 `_group_rows` 추가 |

---

## 4. main.py import 구조

```python
from utils.rows import _row_text, _single_line_rows, _is_merchant_notice_row, _group_rows
```

## 5. utils/rows.py 최종 구조 (총 64라인)

```python
import re

def _group_rows(ocr_lines: list):
    """OCR 라인들을 행 기준으로 그룹핑.

    PaddleOCR v5 에서는 세로형 영수증에서 polygon 이 '세로로 긴 박스'로 들어오는 경우가 있어
    단순 y-span 기준 그룹핑이 전표 전체를 한 행으로 합쳐버릴 수 있다. 그런 경우에는 x축을
    읽기 진행축으로 간주해 행을 복구한다.
    """
    ... (median, vertical_layout, threshold-grouping)

def _row_text(row): ...
def _single_line_rows(ocr_lines: list): ...
def _is_merchant_notice_row(text: str) -> bool: ...
```

---

## 6. 정적 검증 결과

| 항목 | 결과 |
|---|---|
| `python -m py_compile utils/rows.py` | PASS |
| `python -m py_compile main.py` | PASS |
| `python -c "import main"` | PASS |
| AST 함수 본문 동일성 검증 | IDENTICAL (1/1, `_group_rows`) |

---

## 7. Live 검증 결과 (2026-04-26 18:14)

검증 스크립트: `ocr-server/validate_r1c3.py`
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

결과 파일: `mysuit-ocr/public/data/testsets/baseline_fast/validation_results_baseline_fast_after_refactor_r1c_3_group_rows.json`

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

결과 파일: `mysuit-ocr/public/data/testsets/google/validation_results_google_after_refactor_r1c_3_group_rows.json`

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

결과 파일: `mysuit-ocr/public/data/testsets/baseline/validation_results_baseline_after_refactor_r1c_3_group_rows.json`

### OVERALL: ALL PASS

---

## 8. 결과 변화 여부

**없음.** 모든 수치 lock 기준 동일 유지.

이유:
- `_group_rows` 본문 1바이트도 변경하지 않고 이동 (AST 동일성 확인 완료).
- `extract_receipt_fields` 의 3개 호출부 (full/upper/amount) 가 동일 이름으로 import 된 함수를 호출.
- median 계산, vertical_layout 분기, threshold scaling 모두 원본과 비트 단위 동일하게 작동.
- 인접 함수와의 import 순환 위험 없음 (rows.py 는 main.py 의 어떤 것도 import 하지 않음).

분석 문서 §10.4 의 우려 (정렬 결과의 미세 차이로 그룹핑 결과 변화) 는 발생하지 않음. 함수 본문이 동일하면 동일 입력에 대해 결정론적으로 동일 출력.

---

## 9. R1-c 완료 확정 (전체)

R1-c 의 3개 sub-phase 모두 통과:

| Sub-phase | 대상 | 위험도 | 결과 |
|---|---|---|---|
| R1-c-1 | `_row_text`, `_single_line_rows` | LOW | ALL PASS |
| R1-c-2 | `_is_merchant_notice_row` | MEDIUM | ALL PASS |
| **R1-c-3** | **`_group_rows`** | **HIGH** | **ALL PASS** |

**Phase R1-c (utils/rows.py 분리) 완전 완료.**

이제 main.py 의 row 처리 영역은 모두 utils/rows.py 로 격리되었다.

---

## 10. R1 (utils 분리) 진행 현황

| Sub-phase | 대상 | 상태 |
|---|---|---|
| R1-a | `utils/text_normalize.py` | 완료 |
| R1-b | `utils/regex_patterns.py` | 완료 |
| R1-c | `utils/rows.py` | 완료 |
| R1-d | `utils/io_json.py` | **미시작** |

R1 의 마지막 sub-phase 만 남았다.

---

## 11. 다음 단계

**Phase R1-d: `utils/io_json.py` 분리 (LOW risk)**

대상:
- `_load_json(path, default)` — JSON 파일 로드 (없으면 default 반환)
- `_save_json(path, data)` — JSON 파일 atomic write (temp -> rename)

특징:
- 순수 I/O helper. OCR 로직과 무관.
- 파일 경로 처리 + json 직렬화 + os.rename 만 사용.
- main.py 의 review log 기록, ground truth 저장 등에서 호출됨.
- R1 중 가장 안전한 마지막 단계.

주의:
- `_save_json` 의 atomic rename 동작 (temp 파일명 생성 규칙) 1자도 변경 금지.
- R1-d 시작 전 main.py 백업 필수.
- R1-d 완료 후 R1 단계 전체 종료. 이후 R2 (extractor 분리) 진입.
