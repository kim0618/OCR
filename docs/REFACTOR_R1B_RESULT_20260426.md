# REFACTOR R1-b RESULT 2026-04-26

Phase R1-b 실행 결과 기록 문서.
계획 문서: [docs/REFACTOR_PLAN_20260426.md](REFACTOR_PLAN_20260426.md)
선행 단계: [docs/REFACTOR_R1A_RESULT_20260426.md](REFACTOR_R1A_RESULT_20260426.md)

---

## 1. 작업 요약

- **작업**: main.py 모듈 레벨 정규식 상수 19개를 `ocr-server/utils/regex_patterns.py` 로 이동
- **성격**: 순수 위치 이동. 정규식 pattern, flags, 이름 1자도 변경 없음.
- **코드 변경 영향 범위**: main.py 라인 수 2441 -> 2392 (정규식 블록 59라인 제거, import 10라인 추가, 순감 49라인)

---

## 2. 이동한 정규식 상수 (19개)

| 상수명 | flags | 비고 |
|---|---|---|
| `_PHONE_RE` | 없음 | 전화번호 패턴 |
| `_PHONE_LABELED_RE` | re.I | TEL/전화 레이블 이후 번호 |
| `_PHONE_ADMIN_NOISE_RE` | re.I | 전화 주변 행정 노이즈 필터 |
| `_ADDR_START_RE` | 없음 | 주소 시작 지역명 |
| `_NEXT_LABEL_RE` | re.I | 다음 필드 레이블 경계 |
| `_FIELD_NOISE_RE` | re.I | 필드값 공통 노이즈 |
| `_REPRESENTATIVE_NOISE_RE` | re.I | 대표자 노이즈 |
| `_COMPANY_SUFFIX_HINT_RE` | re.I | 회사명 suffix 힌트 |
| `_CONVENIENCE_STORE_NAME_RE` | re.I | 편의점 이름 패턴 |
| `_COMPANY_SLOGAN_RE` | 없음 | 회사 슬로건 패턴 |
| `_PERSON_LIKE_NAME_RE` | 없음 | 3글자 이름형 패턴 |
| `_REPRESENTATIVE_SURNAME_RE` | 없음 | 대표자 성씨 패턴 |
| `_ADDRESS_CUT_RE` | re.I | 주소 절단 기준 레이블 |
| `_ADDRESS_CORE_TOKEN_RE` | 없음 | 주소 핵심 토큰 |
| `_ADDRESS_STORE_NOISE_RE` | re.I | 주소 내 업종 노이즈 |
| `_LABEL_ONLY_RE` | re.I | 레이블만 있는 행 판정 |
| `_ADDRESS_CONTINUATION_RE` | 없음 | 주소 연속 패턴 |
| `_ADDRESS_BROAD_ONLY_RE` | 없음 | 광역 주소만 있는 패턴 |
| `_ADDRESS_TRAILING_NOISE_RE` | re.I | 주소 끝 노이즈 절단 |

---

## 3. 생성/수정 파일 목록

| 파일 | 구분 | 내용 |
|---|---|---|
| `backup/main_20260426_1640_before_refactor_r1b_regex_patterns.py` | 백업 | 리팩토링 전 main.py 전체 |
| `ocr-server/utils/regex_patterns.py` | 신규 | 19개 정규식 상수 정의 |
| `ocr-server/main.py` | 수정 | 정규식 블록 제거, import 추가 |

---

## 4. main.py import 구조 변경

변경 전:
```python
from utils.text_normalize import _clean_number, _clean_inline_field_value
# 이후 모듈 레벨에 19개 re.compile(...) 정의
```

변경 후:
```python
from utils.text_normalize import _clean_number, _clean_inline_field_value
from utils.regex_patterns import (
    _PHONE_RE, _PHONE_LABELED_RE, _PHONE_ADMIN_NOISE_RE,
    _ADDR_START_RE, _NEXT_LABEL_RE, _FIELD_NOISE_RE,
    _REPRESENTATIVE_NOISE_RE, _COMPANY_SUFFIX_HINT_RE,
    _CONVENIENCE_STORE_NAME_RE, _COMPANY_SLOGAN_RE,
    _PERSON_LIKE_NAME_RE, _REPRESENTATIVE_SURNAME_RE,
    _ADDRESS_CUT_RE, _ADDRESS_CORE_TOKEN_RE, _ADDRESS_STORE_NOISE_RE,
    _LABEL_ONLY_RE, _ADDRESS_CONTINUATION_RE,
    _ADDRESS_BROAD_ONLY_RE, _ADDRESS_TRAILING_NOISE_RE,
)
```

---

## 5. 정적 검증 결과

| 항목 | 결과 |
|---|---|
| `python -m py_compile utils/regex_patterns.py` | PASS |
| `python -m py_compile main.py` | PASS |
| `python -c "import main"` | PASS |
| pattern/flags 동일성 검증 (test_r1b.py) | ALL 19 PASS |

pattern/flags 검증 방식: AST 파싱으로 backup main.py 와 신규 regex_patterns.py 의 각 상수 pattern 문자열 및 flags 값을 비교. 19개 전부 완전 동일 확인.

---

## 6. Live 검증 결과 (2026-04-26 16:46)

검증 스크립트: `ocr-server/validate_r1b.py`
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

결과 파일: `mysuit-ocr/public/data/testsets/baseline_fast/validation_results_baseline_fast_after_refactor_r1b_regex_patterns.json`

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

결과 파일: `mysuit-ocr/public/data/testsets/google/validation_results_google_after_refactor_r1b_regex_patterns.json`

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

결과 파일: `mysuit-ocr/public/data/testsets/baseline/validation_results_baseline_after_refactor_r1b_regex_patterns.json`

### OVERALL: ALL PASS

---

## 7. 결과 변화 여부

**없음.** baseline / google / baseline_fast 모든 수치가 lock 기준과 동일.

이유:
- 이동한 19개 정규식 상수는 re.compile() 결과 객체이며 외부 상태를 변경하지 않음.
- pattern 문자열, flags 모두 백업 대비 1바이트도 변경 없음 (AST 검증 통과).
- 모든 call site 는 이름이 동일하므로 기존 동작과 완전히 동일.

---

## 8. R1-b 완료 확정

- 정적 검증 (py_compile + import): PASS
- pattern/flags 동일성 검증 (AST 기반): ALL 19 PASS
- Live baseline_fast: PASS
- Live google: PASS
- Live baseline: PASS

**Phase R1-b 완전 완료.**

R1 진행 현황:
- R1-a text_normalize: 완료
- R1-b regex_patterns: 완료
- R1-c rows.py: 미시작
- R1-d io_json.py: 미시작

---

## 9. 다음 단계

**Phase R1-c: `utils/rows.py` 분리**

대상:
- `_group_rows(ocr_lines)` — 행 그룹핑 (vertical layout 감지 포함)
- `_row_text(row)` — 행 텍스트 join
- `_single_line_rows(ocr_lines)` — 단일행 래핑
- `_is_merchant_notice_row(text)` — 머천트 안내문 판정

주의:
- `_group_rows` 는 vertical_layout 분기와 median 계산이 있어 R1 중 가장 위험한 이동 대상.
- 함수 본문 1줄도 변경 금지.
- `_group_rows` 는 단독 commit 으로 격리.
- R1-c 완료 후 동일한 live validation 절차 수행.
- R1-c 시작 전 main.py 백업 필수.
