# REFACTOR R1-c PRE-MOVE ANALYSIS 2026-04-26

R1-c 실제 이동 전 사전 분석 문서.
계획 문서: [docs/REFACTOR_PLAN_20260426.md](REFACTOR_PLAN_20260426.md)
선행 단계: [docs/REFACTOR_R1A_RESULT_20260426.md](REFACTOR_R1A_RESULT_20260426.md), [docs/REFACTOR_R1B_RESULT_20260426.md](REFACTOR_R1B_RESULT_20260426.md)

본 문서는 분석만 수행하며, **코드는 어떤 것도 수정하지 않는다.**

---

## 1. R1-c 목적

`ocr-server/utils/rows.py` 신규 모듈에 OCR 라인 → 행 그룹핑 관련 helper 들을 분리하여, main.py 에서 row 처리 로직 영역을 명확히 격리한다.

R1-c 는 R1 (utils) 의 마지막 큰 단위가 될 가능성이 높다. R1-d (`io_json.py`) 는 별도 진행.

R1-c 가 위험한 이유:
- `_group_rows` 는 median 계산, vertical_layout 분기, threshold 스케일링이 들어 있음.
- `extract_receipt_fields` 의 입구에서 3번(full/upper/amount) 호출되어 모든 후속 추출에 영향.
- 1픽셀 단위의 정렬 결과가 달라지면 OCR 채택값이 달라질 수 있음.

따라서 R1-c 는 더 작게 쪼개야 한다.

---

## 2. 분석 대상 함수 목록

| # | 함수 | 위치 | 라인 수 | 본질 |
|---|---|---|---|---|
| F1 | `_row_text(row)` | main.py L151-152 | 2 | row → 공백 join |
| F2 | `_single_line_rows(ocr_lines)` | main.py L155-156 | 2 | 라인을 단일행 list 로 wrap |
| F3 | `_is_merchant_notice_row(text)` | main.py L159-168 | 10 | 행 텍스트가 머천트 안내문/노이즈인지 판정 |
| F4 | `_group_rows(ocr_lines)` | main.py L108-148 | 41 | OCR 라인을 행 단위로 그룹핑 (vertical layout 감지 포함) |

---

## 3. 함수별 역할

### F1. `_row_text(row)`
```python
def _row_text(row):
    return ' '.join(t for _, t, _ in row)
```
- row 의 각 line tuple `(pts, text, conf)` 에서 text 만 뽑아 공백으로 join.
- **순수 함수.** 부수효과 없음.

### F2. `_single_line_rows(ocr_lines)`
```python
def _single_line_rows(ocr_lines: list):
    return [[line] for line in (ocr_lines or []) if line and line[1]]
```
- 각 line 을 1개짜리 행으로 감싸서 list 반환.
- text 가 truthy 인 라인만 포함.
- **순수 함수.** 부수효과 없음.

### F3. `_is_merchant_notice_row(text)`
```python
def _is_merchant_notice_row(text: str) -> bool:
    norm = re.sub(r'\s+', '', text or '')
    if re.search(r'다른경우|실제와|가맹점주소가|전기작업|작업지시|직원|식지|재발행|안내문|설명문구|예시문구|작성문구', norm, re.I):
        return True
    return bool(re.search(
        r'신고안내|여신금융|협회|고객센터|가맹점주소.*다른경우|crefia|'
        r'승인번호|카드번호|거래일시|매출전표|공급가액|부가세|합계|총계|품목|수량|단가|금액',
        norm,
        re.I,
    ))
```
- 행 텍스트가 머천트 안내문 / 카드 매출전표 메타 / 영수증 푸터 노이즈인지 판정.
- 두 개의 **인라인 raw regex** 사용 (utils/regex_patterns.py 미등록).
- `re` 모듈 의존.
- **순수 함수.** 부수효과 없음.

### F4. `_group_rows(ocr_lines)`
- OCR 라인을 행 단위로 그룹핑.
- 내부 closure: `cy`, `cx`, `width`, `height` (단순 좌표 helper).
- median 으로 vertical_layout 판정 (median_h > max(median_w * 1.8, 80)).
- vertical_layout 여부에 따라 primary/secondary 축 결정.
- threshold scale (0.45 / 0.75) + 최소 8 픽셀.
- 정렬 후 인접 차이 비교로 행 묶음 생성.
- **순수 함수.** 부수효과 없음. **단, float 비교/median index 가 출력 결정에 직접 영향.**

---

## 4. 함수별 호출부

### F1. `_row_text` — main.py 내부 호출 12개 + 외부 callback 3개

| 위치 | 컨텍스트 |
|---|---|
| L662, L664, L665 | `_company_candidate_score` 의 row 텍스트 추출 |
| L702 | `_company_rescue` 또는 `_extract_fields_from_rows` 영역 |
| L710 | `_extract_fields_from_rows` 의 사업자번호 다음 행 추출 |
| L724 | `_extract_fields_from_rows` 의 대표자 다음 행 추출 |
| L743 | `_extract_fields_from_rows` 의 representative 다음 행 |
| L752 | `_extract_fields_from_rows` 의 address continuation 1 |
| L759, L765 | `_extract_fields_from_rows` 의 address continuation 2/3 |
| **L950, L951, L952** | **`extract_amount_candidates` 의 callback 으로 전달** |

**중요:** L950-952 에서 `_row_text` 가 함수 객체 그대로 `amount_extractor.extract_amount_candidates(rows, _row_text, source=...)` 에 전달된다. 이동 후에도 main.py 안에서 import 한 이름이 동일하면 문제 없음.

### F2. `_single_line_rows` — 호출 1개

| 위치 | 컨텍스트 |
|---|---|
| L913 | `extract_receipt_fields` 진입부에서 `upper_single_rows` 생성 |

### F3. `_is_merchant_notice_row` — 호출 3개

| 위치 | 컨텍스트 |
|---|---|
| L290 | `_is_bad_representative_candidate` 또는 인접 함수에서 노이즈 판정 |
| L615 | `_company_candidate_texts` 의 진입 가드 |
| L629 | `_company_candidate_texts` 의 labeled candidate 검증 |

### F4. `_group_rows` — 호출 3개 (모두 `extract_receipt_fields` 내부)

| 위치 | 컨텍스트 |
|---|---|
| L911 | `rows = _group_rows(ocr_lines)` (full ocr 행) |
| L912 | `upper_rows = _group_rows(upper_lines or [])` (upper block 재OCR 결과) |
| L914 | `amount_rows = _group_rows(amount_lines or [])` (amount block 재OCR 결과) |

---

## 5. 함수별 의존성

### 모듈 의존성

| 함수 | 외부 모듈 의존 |
|---|---|
| F1. `_row_text` | 없음 (Python 빌트인만) |
| F2. `_single_line_rows` | 없음 |
| F3. `_is_merchant_notice_row` | `re` (라이브러리만, 우리 utils 모듈 의존 없음) |
| F4. `_group_rows` | 없음 (Python 빌트인 `sorted`, `abs`, `max`, `min`만) |

### 우리 모듈 의존성

| 함수 | text_normalize | regex_patterns | extractor 함수 |
|---|---|---|---|
| F1 | 없음 | 없음 | 없음 |
| F2 | 없음 | 없음 | 없음 |
| F3 | 없음 | **없음** (인라인 regex 사용) | 없음 |
| F4 | 없음 | 없음 | 없음 |

### 다른 함수가 이 함수에 의존

- `_row_text` → 12개 main.py 함수에서 호출 + 외부 callback 으로 1번 export
- `_single_line_rows` → `extract_receipt_fields` 1곳
- `_is_merchant_notice_row` → company/representative extractor 영역 3곳
- `_group_rows` → `extract_receipt_fields` 3번 호출 (full/upper/amount)

---

## 6. 이동 가능 여부

### F1. `_row_text` — 이동 가능 (안전도 ★★★★★)
- 1줄 순수 함수.
- 외부 라이브러리 의존 없음.
- 12개 호출부는 import 만 추가하면 그대로 작동.
- L950-952 callback 전달도 동일 이름 import 로 호환.

### F2. `_single_line_rows` — 이동 가능 (안전도 ★★★★★)
- 1줄 순수 함수.
- 호출부 1곳만.
- 가장 위험 없음.

### F3. `_is_merchant_notice_row` — 이동 가능 (안전도 ★★★★)
- 인라인 regex 2개를 그대로 함수 본문에 두고 이동.
- `re` 모듈만 import.
- regex 를 utils/regex_patterns.py 로 추출하는 것은 R1-c 범위 밖 (별도 결정).
- 함수 위치 (rows.py) 에 대한 의문은 §8 에서 다룸.

### F4. `_group_rows` — 이동 가능하지만 위험도 높음 (안전도 ★★)
- 본문 자체는 순수 함수, 외부 의존 없음.
- 그러나:
  - median index 계산: `widths[len(widths) // 2]` — 정렬 + 인덱스 접근.
  - vertical_layout 판정 임계: `median_h > max(median_w * 1.8, 80)` — float 비교.
  - threshold: `max(median_primary * row_thr_scale, 8)` — 픽셀 단위.
  - 행 묶음: `abs(primary_center(line) - primary_center(cur[-1])) <= row_thr` — 미세 차이가 그룹핑 결과를 바꿀 수 있음.
- 본문 1바이트도 변경하지 않으면 결과는 동일. 그러나 인코딩/줄바꿈 차이까지 주의 필요.
- 단독 commit 권장.

---

## 7. 위험도 종합

| 함수 | 위험도 | 사유 |
|---|---|---|
| `_row_text` | LOW | 1줄, str.join 만, callback 전달도 호환 |
| `_single_line_rows` | LOW | 1줄, list comp 만, 호출 1곳 |
| `_is_merchant_notice_row` | MEDIUM | 인라인 regex 2개. extractor 영역에서 호출. company 후보 결정에 직접 영향 |
| `_group_rows` | HIGH | median, threshold scaling, 모든 후속 추출의 입구 |

### import 순환 가능성

| 시나리오 | 위험 |
|---|---|
| utils/rows.py → utils/text_normalize.py | 없음 (rows 가 text_normalize 를 import 안 함) |
| utils/rows.py → utils/regex_patterns.py | 없음 (rows 가 regex_patterns 를 import 안 함) |
| utils/rows.py → main.py | 없음 (rows 가 main 의 어떤 것도 import 안 함) |
| main.py → utils/rows.py | 안전 (한 방향) |

**순환 import 위험 없음.**

### 기존 utils 모듈과의 충돌

| 충돌 영역 | 결과 |
|---|---|
| 함수명 중복 (text_normalize.py) | 없음 |
| 함수명 중복 (regex_patterns.py) | 없음 |
| 상수명 중복 | 없음 (`_is_merchant_notice_row` 의 인라인 regex 는 모듈 레벨 상수가 아님) |

---

## 8. `_is_merchant_notice_row` 위치 검토

**rows.py 가 적절한가?**

찬성:
- 함수 이름에 `row` 가 들어 있음.
- 행 텍스트를 입력으로 받음.
- 행 단위 분류 작업.

반대:
- 본질적으로는 noise / notice 분류기.
- company / representative extractor 가 사용.
- 미래에 다른 noise 분류기가 추가되면 noise.py 같은 모듈이 더 자연스러울 수 있음.

**판단:** R1-c 단계에서는 **rows.py 에 둔다.**
- 이름이 `*_row` 로 끝남 → 직관적으로 rows.py.
- 새 모듈(`noise.py`) 도입은 R1 의 미니멀 정신에 어긋남.
- R2 (extractor 분리) 에서 noise 분류기들이 모이면 그때 재배치 가능.

대안: 만약 R2 에서 `extractors/common.py` 에 noise 분류기들을 모을 계획이라면, 이 함수는 R1-c 에서 빼고 R2 에서 직접 처리하는 것도 합리적. 그러나 이 결정은 R1-c 의 단순성을 해치므로 일단 **rows.py 에 포함** 하는 것을 권장.

---

## 9. 권장 하위 단계 (R1-c 분할)

### R1-c-1: `_row_text` + `_single_line_rows` 이동 (LOW risk)

가장 안전한 두 함수만 먼저 이동. 1 commit.

대상:
- `_row_text` (L151-152)
- `_single_line_rows` (L155-156)

신규 파일: `ocr-server/utils/rows.py` (초기 버전)

main.py 변경:
```python
from utils.rows import _row_text, _single_line_rows
```

검증:
- py_compile main.py + utils/rows.py
- import main
- /health
- baseline_fast → google → baseline 3개 모두 통과
- 결과 파일: `validation_results_*_after_refactor_r1c_1_row_helpers.json`

### R1-c-2: `_is_merchant_notice_row` 이동 (MEDIUM risk)

R1-c-1 통과 후 단독 진행.

대상:
- `_is_merchant_notice_row` (L159-168) — 인라인 regex 2개 포함하여 본문 그대로 이동.

main.py 변경:
```python
from utils.rows import _row_text, _single_line_rows, _is_merchant_notice_row
```

검증:
- 정적 검증 + live validation 전체.
- 특히 company/representative 추출에 의존하므로 baseline a1.jpg, baseline 7.jpg, google 3.jpg, google 7.jpg 의 회사명 결과 변화 여부 주시.
- 결과 파일: `validation_results_*_after_refactor_r1c_2_merchant_notice.json`

### R1-c-3: `_group_rows` 이동 (HIGH risk, 단독 commit)

R1-c-2 통과 후 마지막에 진행.

대상:
- `_group_rows` (L108-148) — 본문 1바이트도 변경 없이 이동.

main.py 변경:
```python
from utils.rows import _row_text, _single_line_rows, _is_merchant_notice_row, _group_rows
```

검증:
- 정적 검증 + live validation 전체.
- **모든 lock 기준** 재확인.
- 특히 google 7.jpg, baseline 1.jpg/4.jpg/10.jpg/a1.jpg, baseline 9.jpg/a2.jpg suppression 모두 확인.
- 결과 파일: `validation_results_*_after_refactor_r1c_3_group_rows.json`

각 sub-phase 후:
- 통과시 commit
- 실패시 즉시 rollback (백업 복원) 후 원인 분석

---

## 10. 검증 전략

### 10.1 정적 검증 (각 sub-phase 공통)

```bash
cd ocr-server
python -m py_compile utils/rows.py
python -m py_compile main.py
python -c "import main"
```

### 10.2 함수 본문 동일성 검증

R1-b 처럼 AST 기반으로 backup main.py vs 신규 utils/rows.py 의 함수 본문이 동일한지 자동 검증.

```python
# 각 함수의 ast.dump 비교
import ast
backup_funcs = {n.name: ast.dump(n) for n in ast.walk(ast.parse(open('backup/main_*_before_refactor_r1c_*.py').read())) if isinstance(n, ast.FunctionDef) and n.name in TARGETS}
new_funcs = {n.name: ast.dump(n) for n in ast.walk(ast.parse(open('utils/rows.py').read())) if isinstance(n, ast.FunctionDef) and n.name in TARGETS}
assert backup_funcs == new_funcs
```

### 10.3 Live validation (각 sub-phase 공통)

uvicorn 9100 재기동 → /health → baseline_fast → google → baseline.

회귀 기준 (3개 sub-phase 공통):

baseline_fast:
- selected 3 / suppression 2 / unknown 0
- 9.jpg = suppressed_bank_slip
- a2.jpg = suppressed_handwritten

google:
- selected 10 / suppression 1 / unknown 0 / error 0
- 7.jpg = receipt_pos / selected / GS25성신로데오점 / 7,650 / 02-927-2369
- 6.jpg = suppressed_bank_slip

baseline:
- selected 8 / suppression 2 / unknown 0
- OCR 43/57, 최종 채택값 52/57
- 사업자번호 9/9, 총합계금액 8/10
- 1.jpg 10,560, 4.jpg 17,600, 10.jpg 19,250

### 10.4 R1-c-3 (`_group_rows`) 추가 검증

`_group_rows` 는 모든 추출의 입구이므로, lock 기준 외에 **전 dataset 의 모든 row** 가 OCR 출력의 모든 필드와 일치하는지 비교:

```bash
diff <(jq -S '.rows | map(del(.processing_time))' validation_before.json) \
     <(jq -S '.rows | map(del(.processing_time))' validation_after.json)
```
빈 출력이어야 함.

### 10.5 롤백 절차

각 sub-phase 직전에 main.py 백업:
- R1-c-1 직전: `backup/main_<HHMM>_before_refactor_r1c_1_row_helpers.py`
- R1-c-2 직전: `backup/main_<HHMM>_before_refactor_r1c_2_merchant_notice.py`
- R1-c-3 직전: `backup/main_<HHMM>_before_refactor_r1c_3_group_rows.py`

검증 실패시:
1. 즉시 `cp backup/main_*.py ocr-server/main.py` 로 복원
2. 신규 utils/rows.py 는 그대로 두거나 삭제 (다음 시도용)
3. 원인 분석 (인코딩? 줄바꿈? regex literal 변환?)
4. 분석 결과를 별도 noted 문서로 기록 후 재시도

---

## 11. 첫 실제 R1-c 작업 추천 범위

**다음 실행 작업: R1-c-1 (`_row_text` + `_single_line_rows`)**

이유:
- 1줄 순수 함수 2개로 가장 안전.
- 호출 패턴이 명확 (callback 전달 포함).
- 통과시 R1-c-2/3 진행에 자신감.
- 실패해도 원인이 좁아서 디버깅 용이.

준비 사항:
- main.py 백업
- `utils/rows.py` 신규 파일 생성 (이 두 함수만 포함)
- main.py 정의부 제거 + import 추가

검증:
- §10 절차 전체

---

## 12. R1-c 후 R1 의 잔여 작업

R1-c 완료 후 R1 의 마지막 sub-phase:

### R1-d: `utils/io_json.py` 분리 (LOW risk)

대상:
- `_load_json(path, default)`
- `_save_json(path, data)`

순수 I/O helper. R1-c-3 완료 후 진행.

R1-d 까지 완료하면 R1 (utils 분리) 단계가 마무리되고, R2 (extractor 분리) 로 진입 준비.

---

## 13. 본 문서의 위치

- `docs/REFACTOR_R1C_ANALYSIS_20260426.md`
- 본 문서는 분석/계획 문서이며 코드를 변경하지 않는다.
- R1-c-1/2/3 의 실제 결과는 별도 문서 (`docs/REFACTOR_R1C_RESULT_20260426.md` 또는 sub-phase 별) 로 기록.
