# T-6j-fix-2pdf-colguides-row-filter 결과 보고서

## 1. 변경 파일

- `d:/Free_Vue/OCR/ocr-server/extractors/invoice_statement.py`
- `d:/Free_Vue/OCR/ocr-server/scripts/verify_invoice_table_rows_t6j_2pdf.py` (테스트 스크립트 개선)

## 2. 백업 파일

- `d:/Free_Vue/OCR/ocr-server/backup/invoice_statement_20260513_before_T6j_fix_2pdf_colguides_row_filter.py`

## 3. 구현 내용

### 3-1. `_has_strong_item_signal(text)` 헬퍼 추가

```python
def _has_strong_item_signal(text: str) -> bool:
    # OP- 형태 품목코드
    if re.search(r"\bOP[-\s][A-Za-z0-9]{2,}", text, re.I):
        return True
    # rowIndex 1-13 (페이지번호 패턴 "N/M" 제외)
    if re.match(r"^\s*(?:1[0-3]|[1-9])[\s\t]", text):
        if not re.match(r"^\s*\d+\s*/", text):
            return True
    return False
```

### 3-2. `_extract_items_using_boundaries` 수정

- `skip_contact_filter: bool = False` 파라미터 추가
- `_is_business_contact_line` + `_is_table_notice_or_party_line` 필터를 각각 분리하여 조건부 bypass
- **bypass 조건**: `skip_contact_filter=True` AND `_has_strong_item_signal(text)` (OP- 코드 또는 rowIndex 1-13)
- `_cand_before` (y범위 내 row 수), `_cand_after` (필터 통과 row 수) 카운터 추가
- 루프 종료 후 `debug["rowCandidateCountBeforeFilter"]`, `debug["rowCandidateCountAfterFilter"]` 기록

### 3-3. colGuides path 수정 (`_table_items_with_expected_columns`)

- `debug["columnGuidesUsedAttempted"] = True` 추가
- `_extract_items_using_boundaries` 호출 시 `skip_contact_filter=True` 전달

### 3-4. debug 보존 개선 (`_detect_table`)

- colGuides path가 0 items를 반환할 때도 debug 필드 유실 방지
- `colGuidesRejectedRows` (별도 키) 로 colGuides path의 rejection 세부 정보 보존
- `header_debug.setdefault(k, v)` 로 colGuides debug 필드를 fallback debug에 병합

### 3-5. 새 debug 필드 전파

**tableDebug → tableMeta 경로 추가:**
- `columnGuidesUsedAttempted`
- `rowCandidateCountBeforeFilter`
- `rowCandidateCountAfterFilter`
- `colGuidesRejectedRows`

## 4. 테스트 결과

### 4-1. 회귀 테스트 (T-6l)

| 샘플 | GT | OCR | 상태 |
|---|---:|---:|---|
| 1.jpg | 28 | 28 | ✓ exact |
| 2.pdf | 13 | 2 | short (구조적 한계) |
| 3.pdf | 1 | 1 | ✓ exact |
| 4.pdf | 1 | 1 | ✓ exact |
| 5.pdf | 6 | 6 | ✓ exact |
| 6.pdf | 6 | 6 | ✓ exact |
| 7.pdf | 1 | 1 | ✓ exact |

**달성률: 6/7 exact (회귀 없음)**

### 4-2. 2.pdf colGuides path 테스트

| 테스트 | cgAttempted | before | after | 비고 |
|---|:---:|---:|---:|---|
| baseline (no bounds/guides) | False | - | - | legacy 2개 |
| colguides_price_area (y=355-490) | True | 2 | 0 | OP- 없는 row → 여전히 필터됨 |
| colguides_with_insurance (y=340-500) | True | 3 | 0 | 동일 |
| **colguides_full_page (y=40-560)** | **True** | **6** | **1** | **OP- row 통과** ✓ |
| colguides_top_half (y=40-350) | True | 3 | 1 | OP- row 통과 ✓ |

**핵심 변화**: `colguides_full_page` → `before=6, after=1, src=template_colguides_expected_columns`
- y=82.6 row (item codes "OP-NA0300, 120P-NA0030, 11OP-M00100..."): `notice_or_party` 필터 bypass → 1개 item 추출 성공

## 5. 2.pdf 구조 최종 분석

전체 페이지 (900×639, landscape) OCR row 분포:

| y | 내용 | 필터 결과 | bypass 여부 |
|---:|---|---|---|
| 82.6 | item codes (OP-xxx, 13개 수평 배치) | notice_or_party → **bypass** | ✓ (OP- 신호) |
| 227.0 | 소비자금액합계 등 | header_or_contact | ✗ |
| 342.4 | 1/1 거래명세서 URL | notice_or_party | ✗ (페이지 표기) |
| 412.6 | 당일거래금액 등 | header_or_contact | ✗ |
| 492.0 | 거래처 청구금액합계 | header_or_contact | ✗ |
| 549.8 | 총합계 | summary_row | ✗ (정상) |

**결론**: 전체 6개 OCR row만 존재 (13개 아님). 13개 품목이 수평으로 13개 column에 배치된 **전치(transposed) 구조**. row 기반 추출로 rowCount=13 달성 불가.

## 6. 달성/미달 항목

| 요구사항 | 상태 |
|---|---|
| `_is_business_contact_line` 무조건 적용 금지 (OP-/rowIndex 신호 시 bypass) | ✓ 구현 |
| `_is_table_notice_or_party_line` 동일 bypass 적용 | ✓ 구현 |
| `columnGuidesUsedAttempted` debug 필드 | ✓ 구현 |
| `rowCandidateCountBeforeFilter` / `AfterFilter` debug 필드 | ✓ 구현 |
| colGuides 0 items 시 debug 유실 방지 | ✓ 구현 |
| 회귀 없음 (1.jpg/3~7.pdf) | ✓ 확인 |
| py_compile | ✓ 통과 |
| typecheck | ✓ 통과 |
| build | ✓ 통과 |
| **2.pdf rowCount=13** | **✗ 구조적 한계 (전치 표)** |

## 7. 후속 조치

rowCount=13 달성을 위해서는 별도 태스크 필요:
- **T-6n: 전치 표 추출기** — colGuides N개 column 경계로 row(속성)×column(품목) 매트릭스를 13개 item dict로 변환
- OR: 2.pdf를 rowCount 검증 대상에서 제외 (실제 template annotation 미완)
