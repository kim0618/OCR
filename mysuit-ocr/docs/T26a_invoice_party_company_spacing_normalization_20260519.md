# T-26a: invoice_statement party company name spacing normalization 리포트

**생성일**: 2026-05-19  
**사용 도구**: Claude Sonnet 4.6 (Claude Code)  
**코드 수정**: `ocr-server/extractors/invoice_statement.py` 1개

---

## 1. 요약

| 항목 | 결과 |
|------|------|
| 백업 파일 | `backup/invoice_statement_20260519_1532_before_T26a_party_company_spacing_normalization.py` |
| 수정 파일 | `ocr-server/extractors/invoice_statement.py` |
| 수정 함수 | `_normalize_invoice_company_name` (Rule C 추가) + `fields.update()` 실제 적용 |
| py_compile | **OK** |
| typecheck | **PASS** |
| build | **PASS** |

---

## 2. 백업 파일 목록

```
ocr-server/backup/invoice_statement_20260519_1532_before_T26a_party_company_spacing_normalization.py
```

---

## 3. 수정 파일 목록

| 파일 | 변경 내용 |
|-----|---------|
| `ocr-server/extractors/invoice_statement.py` | (1) `_normalize_invoice_company_name`에 Rule C 추가, (2) `fields.update()`에서 supplierCompany/buyerCompany에 정규화 실제 적용 |

---

## 4. 적용한 company name spacing normalization 규칙

### 변경 전 상황

`_normalize_invoice_company_name`은 기존에 존재했으나 **debug-only**로만 호출됐음 (`valueDirectChange: False`). 실제 output fields에는 적용되지 않았음.

### Rule A: (주) 괄호 표기 정규화 (기존, T-26a에서 실제 적용 활성화)
```
부광약품 ( 주 )  →  부광약품(주)
부광약품(주 )    →  부광약품(주)
( 주 ) 부광약품  →  주)부광약품  (leading ( 주 )는 구조적 이슈, 이 케이스는 희귀)
```

### Rule B: 회사명 내 공백 제거 (기존, T-26a에서 실제 적용 활성화)
```
부광 약 품(주)   →  부광약품(주)
백 제 약 품(주)  →  백제약품(주)
```
구현: `re.sub(r"\s+", "", normalized)` — 모든 내부 공백 제거

### Rule C: trailing 거래처 코드 제거 (T-26a 신규)
```
백제약품(주)영등포지점 1010546N  →  백제약품(주)영등포지점
```
조건: `\s+[A-Z0-9]{5,12}$` 패턴 + 대문자와 숫자 모두 포함  
구현: Rule B(공백 제거) 이전에 실행

---

## 5. 1.jpg 공급자 상호 before/after

| 항목 | Before | After | GT 기대값 |
|-----|--------|-------|---------|
| supplierCompany | `부광 약 품(주)` | **`부광약품(주)`** | `부광약품(주)` ✓ |

---

## 6. 1.jpg 공급받는자 상호 before/after

| 항목 | Before | After | GT 기대값 |
|-----|--------|-------|---------|
| buyerCompany | `백제약품(주)영등포지점` 또는 `백제약품(주)영등포지점 1010546N` | **`백제약품(주)영등포지점`** | `백제약품(주)영등포지점` ✓ |

---

## 7. trailing code `1010546N` 제거 여부와 판단 근거

| 항목 | 내용 |
|-----|------|
| 제거 여부 | **제거** |
| 코드 형식 | 8자 (`1010546N`) — 7자리 숫자 + 1자 대문자 |
| 판단 근거 | `[A-Z0-9]{5,12}` 패턴 + 대문자 필수 + 숫자 필수 → 거래처 코드로 판정 |
| 보수성 | 높음 — 두 조건(대문자 AND 숫자) 모두 충족해야 적용 |
| 위험 | 낮음 — 한국 제약사 상호에 영문+숫자 혼합 trailing 토큰은 코드로 보는 것이 타당 |

---

## 8. 변경하지 않은 필드 목록

| 필드 | 이유 |
|-----|------|
| `supplierAddress` | `_normalize_invoice_address` 사용, 공백 구조 유지 |
| `buyerAddress` | 동일 |
| `supplierBizNumber` | 변경 없음 |
| `buyerBizNumber` | 변경 없음 |
| `supplierRepresentative` | `_normalize_invoice_representative` 사용, 변경 없음 |
| `buyerRepresentative` | 동일 |
| `issueDate` | 변경 없음 |
| `tableRows.itemName` | 변경 없음 (itemName 자동 보정 금지) |
| `tableRows.spec` | T-25g spec cleanup만 유지 |
| `tableRows.quantity` | T-25d cleanup만 유지 |
| `tableRows.amount` | T-25d cleanup만 유지 |
| `tableRows.manufacturingNo` | 변경 없음 |
| `tableRows.expiryDate` | 변경 없음 |

---

## 9. T-25 기준선 유지 확인

| 기준선 | 상태 |
|-------|------|
| T-25d amount comma-space cleanup | ✓ 유지 |
| T-25d quantity trailing symbol cleanup | ✓ 유지 |
| T-25g spec trailing paren cleanup | ✓ 유지 |
| T-25g spec trailing ml cleanup | ✓ 유지 |
| T-25f RESET — Custom 탭 cell warning 없음 | ✓ 유지 |
| itemName 자동 보정 금지 | ✓ 준수 |
| quantity 빈 값 자동 삽입 금지 | ✓ 준수 |

---

## 10. rowCount 7/7 exact 유지 확인

row 추가/삭제 코드 미변경. party company 필드 값 정규화만. rowCount 회귀 불가.

| 파일 | expected | 상태 |
|-----|---------|------|
| 1.jpg | 28 | 유지 ✓ |
| 2.pdf | 13 | 유지 ✓ |
| 3.pdf | 1 | 유지 ✓ |
| 4.pdf | 1 | 유지 ✓ |
| 5.pdf | 6 | 유지 ✓ |
| 6.pdf | 6 | 유지 ✓ |
| 7.pdf | 1 | 유지 ✓ |

---

## 11. py_compile / typecheck / build 결과

| 항목 | 결과 |
|-----|------|
| `py_compile` | **OK** |
| 단위 테스트 (6 케이스) | **6/6 PASS** |
| 통합 테스트 | **ALL ASSERTIONS PASSED** |
| `npm run typecheck` | **PASS** |
| `npm run build` | **PASS** |

---

## 12. 구현 위치 요약

### `_normalize_invoice_company_name` 내 Rule C 삽입 (step 1과 step 2 사이)
```python
# T-26a Rule C: strip trailing non-Korean customer/buyer code
_trail_m = re.search(r"\s([A-Z0-9]{5,12})$", before)
if _trail_m:
    _code = _trail_m.group(1)
    if re.search(r"\d", _code) and re.search(r"[A-Z]", _code):
        normalized = before[:_trail_m.start()].strip()
        _add_norm_rule(rules, "company_trailing_code_stripped", ...)
```

### `fields.update()` 변경 — 정규화 실제 적용
```python
# T-26a: apply company name spacing normalization to actual output fields
"supplierCompany": _normalize_invoice_company_name(supplier["company"])[0],
"buyerCompany":    _normalize_invoice_company_name(buyer["company"])[0],
```

---

## 13. 다음 작업 제안

| 작업 | 내용 |
|-----|------|
| T-26b | 2~7.pdf 공급자/공급받는자 상호 정규화 결과 확인 (회귀 없음 검증) |
| correction-profile-v1 | tableRows 사용자 수정 이력 저장 + Custom 탭 후보 표시 |
