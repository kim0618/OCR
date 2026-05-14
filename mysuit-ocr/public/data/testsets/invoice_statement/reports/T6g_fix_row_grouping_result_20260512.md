# T-6g-fix row grouping 보정 결과

## 1. 수정 파일
- `d:/Free_Vue/OCR/ocr-server/extractors/invoice_statement.py`
- `d:/Free_Vue/OCR/mysuit-ocr/public/data/testsets/invoice_statement/manifest.json`

## 2. 백업 파일
- `d:/Free_Vue/OCR/ocr-server/backup/invoice_statement_20260512_before_T6g_fix_row_grouping.py`
- `d:/Free_Vue/OCR/mysuit-ocr/backup/invoice_statement_manifest_20260512_before_T6g_fix_schema_mismatch.json`

## 3. schema mismatch 수정 결과
| 샘플 | 수정 전 key | 수정 후 key | 결과 |
|---|---|---|---|
| 3.pdf | manufacturingExpiry | manufacturingExpiryComposite | ✓ 완료 |
| 7.pdf | serialLot | serialLotComposite | ✓ 완료 |

schema 검증: 7/7 일치 (수정 전 5/7)

## 4. rowCount 비교
| 샘플 | 목표 row 수 | 수정 전 rowCount | 수정 후 rowCount | 차이 | 판정 |
|---|---:|---:|---:|---:|---|
| 1.jpg | 28 | 22 | 29 | +1 | 초과(목표 근접, 6행 복구) |
| 2.pdf | 확인 필요 | 2 | 2 | 0 | 변화 없음 |
| 3.pdf | 확인 필요 | 1 | 1 | 0 | 변화 없음 |
| 4.pdf | 확인 필요 | 1 | 3 | +2 | 개선(regex fix 효과) |
| 5.pdf | 6 | 6 | 6 | 0 | ✓ 유지 |
| 6.pdf | 6 | 2 | 5 | +3 | 개선(목표 근접, 3행 복구) |
| 7.pdf | 1 | 1 | 1 | 0 | ✓ 유지 |

## 5. 주요 수정 내용

### 5-1. _PHONE_RE 수정 (가장 중요)
**원인**: `_PHONE_RE`에 lookbehind가 없어 lot번호+유효기간 조합(예: `24027 20270205`)이 전화번호 `027-2027-0205`로 오인식 → 7개 product row가 `header_or_contact`로 거부됨

**수정**:
```
# 수정 전
_PHONE_RE = re.compile(r"(?:TEL|Tel|tel|전화)?[:\s(]*(?:0\d{1,2})[-)\s]?\d{3,4}[-\s]?\d{4}")
# 수정 후
_PHONE_RE = re.compile(r"(?:TEL|Tel|tel|전화)?[:\s(]*(?<!\d)(?:0\d{1,2})[-)\s]?\d{3,4}[-\s]?\d{4}")
```
→ `(?<!\d)` 추가: 숫자 뒤에서 시작하는 `0XX` 패턴 차단

### 5-2. _BIZ_RE 수정 (6.pdf 핵심)
**원인**: `[-\s.]?` (선택적 구분자)로 lot번호 2개의 연속(`23001 24001`)이 사업자번호 `230-01-24001`로 오인식

**수정**:
```
# 수정 전
_BIZ_RE = re.compile(r"(?<!\d)([0-9OIlSB]{3})[-\s.]?([0-9OIlSB]{2})[-\s.]?([0-9OIlSB]{5})(?!\d)")
# 수정 후
_BIZ_RE = re.compile(r"(?<!\d)([0-9OIlSB]{3})[-\s.]([0-9OIlSB]{2})[-\s.]([0-9OIlSB]{5})(?!\d)")
```
→ 구분자 필수화: 구분자 없는 연속 숫자는 사업자번호로 처리하지 않음

### 5-3. summary break threshold 완화
**위치**: `_table_items_with_expected_columns`, `_table_items_from_header_mapping`

```
# 수정 전: page_h * 0.65 / page_h * 0.72
# 수정 후: page_h * 0.85
```
→ 소계/누계 rolling subtotal이 중간에 있는 문서에서 조기 break 방지

### 5-4. row_has_data 조건 강화 (lot table 지원)
`_table_items_with_expected_columns` 및 `_table_items_from_header_mapping` 양쪽에 추가:
```python
or (has_lot and has_exp)   # lot + expiry 조합
or (has_code and has_lot)  # code + lot 조합
or (has_code and has_exp)  # code + expiry 조합
```

### 5-5. _group_rows tolerance 조정 (6.pdf 핵심)
**원인**: `max(avg_h, line.h) * 0.75` 허용치가 밀집된 table row를 인접 row와 병합 → 6.pdf에서 2개 품목이 1개 row로 합쳐짐

**수정**: `_group_rows`에 `tolerance_factor` 파라미터 추가 (기본값 0.75 유지)
```python
# _table_items_with_expected_columns 및 _table_items_from_header_mapping
scope_rows = _group_rows(scope_lines, tolerance_factor=0.55)
```

### 5-6. date 필드 amount 오인식 방지
expiryDate / manufacturingNo / lotNo에 천 단위 콤마 숫자(금액 형식)가 들어온 경우 클리어:
```python
if re.search(r"\d{1,3}(?:,\d{3})+", _val) and not re.search(r"[가-힣A-Za-z]", _val):
    item[_date_key] = ""
```

## 6. tableDebug/rejectedRows 분석
| 샘플 | 수정 전 주요 rejected reason | 수정 후 변화 | 비고 |
|---|---|---|---|
| 1.jpg | header_or_contact: 7 | 7행 복구 (PHONE_RE 오인식 해결) | lot번호+유효기간 → 전화번호 오인식이 원인 |
| 6.pdf | header_or_contact: 1 | 1행 추가 복구 (BIZ_RE 해결) | lot번호 2개 연속 → 사업자번호 오인식이 원인 |
| 6.pdf | row merging (2행이 1행으로) | tolerance=0.55 적용으로 분리 개선 | 밀집 table에서 인접 row 병합 방지 |

## 7. value mapping 변화
| 샘플 | 개선된 컬럼 | 여전히 비어 있는 컬럼 | 다음 단계 필요 여부 |
|---|---|---|---|
| 1.jpg | rowCount 복구(22→29) | itemName, unitPrice (전체 행에서 비어 있음) | T-6h: 컬럼 boundary 조정 필요 |
| 6.pdf | rowCount 복구(2→5), 6개 컬럼 모두 값 있음 | (1행 누락) | T-6h 또는 T-6g-fix2 |
| 5.pdf | 변화 없음 | itemCode, unitPrice, amount | T-6h |
| 7.pdf | 변화 없음 | serialLotComposite, unit, quantity | T-6h |

## 8. 회귀 확인
| 샘플 | 회귀 여부 | 근거 |
|---|---|---|
| 5.pdf | 없음 | rowCount 6 유지 (수정 전 = 수정 후 = 6) |
| 7.pdf | 없음 | rowCount 1 유지 (수정 전 = 수정 후 = 1) |

## 9. 검증 결과
- backend py_compile: `invoice_statement.py` 통과, `verify_invoice_table_rows_t6g_check.py` 통과
- verify script: 7/7 API 성공, schema 7/7 일치
- frontend typecheck: 통과 (오류 없음)
- frontend build: 통과 (/test 페이지 포함 전체 빌드 성공)

## 10. 다음 작업 판단
**rowCount 개선 완료 (22→29, 2→5), 회귀 없음 → T-6h 진행 가능**

- 1.jpg: rowCount 29 (목표 28 대비 +1). 한 개 footer row(영업사원명 영역)가 false positive로 잔존. 값 매핑(itemName, unitPrice 공란)은 T-6h에서 컬럼 boundary 조정 필요.
- 6.pdf: rowCount 5 (목표 6 대비 -1). 나머지 1행 복구는 T-6g-fix2 또는 T-6h 에서 추가 처리 가능.
- 2.pdf: rowCount 2 유지. `consumerUnitPrice`, `supplyUnitPrice` 비표준 key가 canonical column에 없어 구조적 한계. T-6h에서 별도 처리 필요.
- **결론: T-6h expected boundary/value mapping 진행**
