# T-25d: 거래명세서 cell-level safe cleanup 구현 리포트

**생성일**: 2026-05-19  
**사용 도구**: Claude Sonnet 4.6 (Claude Code)  
**코드 수정**: 있음 — `ocr-server/extractors/invoice_statement.py`

---

## 1. 요약

| 항목 | 결과 |
|------|------|
| 백업 파일 | `backup/invoice_statement_20260519_1327_before_T25d_cell_safe_cleanup.py` |
| 수정 파일 | `ocr-server/extractors/invoice_statement.py` |
| 추가된 helper 함수 | 3개 (`_t25d_amount_comma_space_cleanup`, `_t25d_qty_trailing_symbol_cleanup`, `_t25d_warning_only_checks`) |
| 추가된 regex 패턴 | 6개 (`_T25D_*`) |
| 적용된 cleanup 규칙 | 2개 (amount comma-space, qty trailing symbol) |
| warning-only 추가 | 3종 (qty handwritten, mfg handwritten, spec O/0) |
| py_compile | **OK** |
| typecheck | **PASS** |
| build | **PASS** |
| rowCount 7/7 | **유지** (코드 경로 미변경) |

---

## 2. 백업 파일 목록

```
ocr-server/backup/invoice_statement_20260519_1327_before_T25d_cell_safe_cleanup.py
```

---

## 3. 수정 파일 목록

| 파일 | 변경 유형 |
|-----|---------|
| `ocr-server/extractors/invoice_statement.py` | helper 함수 3개 + regex 6개 추가, `_build_canonical_table_rows` 내 3개 블록 삽입 |

**수정하지 않은 파일**: main.py, preprocessing_policy.py, History/Restore/영수증 parser, DB schema, Template/RunOCR payload, TypeScript UI 파일

---

## 4. 적용한 cleanup 규칙

### Rule 1: amount comma-space cleanup
```python
# "301, 100" → "301,100"
_T25D_AMOUNT_COMMA_SPACE_RE = re.compile(r"(\d),\s+(\d)")
```

**적용 조건** (모두 충족해야 함):
1. 대상 필드: `amount`, `supplyAmount`, `taxAmount`, `totalAmount`
2. 전체 값이 숫자/콤마/공백으로만 구성 (`[\d,\s]+` fullmatch)
3. 콤마-공백-숫자 패턴이 존재 (`\d,\s+\d`)
4. 정리 후 값이 올바른 금액 패턴 (`^\d{1,3}(?:,\d{3})*$`)
5. 값이 실제로 변경될 때만 적용

**적용 예:**
```
"301, 100" → "301,100"    (row 19, 10 × 30,110 = 301,100 ✓)
"782, 160" → "782,160"    (row 20, 240 × 3,259 = 782,160 ✓)
"163, 100" → "163,100"    (row 21, 10 × 16,310 = 163,100 ✓)
"220, 890" → "220,890"    (row 26, 30 × 7,363 = 220,890 ✓)
```

**warning key**: `amount:comma_space_cleanup_applied:amount:'301, 100'->'301,100'`

---

### Rule 2: quantity trailing symbol cleanup
```python
# "360 ^" → "360"
_T25D_QTY_TRAILING_RE = re.compile(r"^([\d,]+)\s+([^\d\s,가-힣A-Za-z]{1,2})\s*$")
_T25D_QTY_ALLOWED_SYMBOLS = {"^", "<", ">", ".", "·", "•"}
```

**적용 조건** (모두 충족해야 함):
1. 대상 필드: `quantity`
2. `숫자[,숫자]+ 공백 기호` 패턴 매칭
3. 숫자 부분이 올바른 수량 패턴 (`^\d{1,6}(?:,\d{3})*$`)
4. 기호가 보수적 허용 목록 안에 있을 것 (`^`, `<`, `>`, `.`, `·`, `•`)
5. 한글/영문자가 포함된 경우 미적용

**적용 예:**
```
"360 ^" → "360"
```

**warning key**: `quantity:trailing_markup_symbol_removed:'360 ^'->'360'`

---

## 5. warning-only 규칙 (자동 보정 없음)

### 5-1. `quantity:handwritten_overlay_suspected:rowN`
- **trigger**: quantity="" 이고 itemName + unitPrice + amount 모두 있을 때
- **guard**: `quantity`가 해당 테이블의 required columns에 있을 때만 발동
- **action**: warning 추가만, row value 불변

### 5-2. `manufacturingNo:handwritten_overlay_suspected:rowN`
- **trigger**: manufacturingNo="" 이고 expiryDate="" 이고 itemName + quantity + unitPrice 있을 때
- **guard**: `manufacturingNo`가 required columns에 있을 때만 발동
- **action**: warning 추가만, row value 불변

### 5-3. `spec:numeric_alpha_ambiguous:rowN:VALUE`
- **trigger**: spec 값이 `\d[O][A-Z]` 패턴 포함 (예: `6OT`, `3OT`)
- **guard**: `spec`이 required columns에 있을 때만 발동
- **action**: warning 추가만, spec value 불변

---

## 6. 적용하지 않은 항목 (이번 작업에서 금지)

| 항목 | 이유 |
|-----|------|
| itemName 자동 치환 | 韓字 혼동 판단 불가, false positive 위험 높음 |
| spec O/0 자동 수정 | `6OT`→`60T` 확실하지 않음, 위험 |
| quantity 수학 추정 삽입 | qty=10 추정 가능하나 자동 삽입 금지 원칙 |
| manufacturingNo/expiryDate 자동 복구 | OCR 원문 자체 부재, 추측 불가 |
| red_pen_suppression | 이번 작업 범위 밖 (T-25c 별도) |

---

## 7. 개선된 cell 목록 (1.jpg 기준)

| rowIndex | itemName | field | Before | After | 수학 검증 |
|---------|---------|-------|--------|-------|----------|
| 5 | 레가론캡슬140 | quantity | `360 ^` | `360` | — (live OCR 기준; 현재 캐시엔 ^없음, no-op 동작) |
| 19 | 헬론정20mg | amount | `301, 100` | `301,100` | 10 × 30,110 = 301,100 ✓ |
| 20 | 메티마졸정 | amount | `782, 160` | `782,160` | 240 × 3,259 = 782,160 ✓ |
| 21 | 메티마줄정 | amount | `163, 100` | `163,100` | 10 × 16,310 = 163,100 ✓ |
| 26 | 소아용프리마란시럽 | amount | `220, 890` | `220,890` | 30 × 7,363 = 220,890 ✓ |

---

## 8. 자동 보정하지 않은 warning-only 후보

| rowIndex | field | 현재 값 | warning |
|---------|-------|--------|--------|
| 4 | spec | `6OT` | `spec:numeric_alpha_ambiguous:row4:6OT` |
| 4 | manufacturingNo | `""` | `manufacturingNo:handwritten_overlay_suspected:row4` |
| 12 | spec | `3OT` | `spec:numeric_alpha_ambiguous:row12:3OT` |
| 12 | quantity | `""` | `quantity:handwritten_overlay_suspected:row12` |

수학 힌트: row 12, 27,900 ÷ 2,790 = **10** (자동 삽입 금지)

---

## 9. rowCount 7/7 회귀 여부

**회귀 없음.** 이유:
- cleanup 함수들은 row 추가/삭제를 하지 않음
- 기존 non-empty 값만 in-place 수정 (non-empty → non-empty)
- row grouping, table detection 경로 변경 없음

| 파일 | expected | 마지막 확인 |
|-----|---------|-----------|
| 1.jpg | 28 | T10_fix_2026-05-16 (exact) |
| 2.pdf | 13 | T10_fix_2026-05-16 (exact) |
| 3.pdf | 1 | T10_fix_2026-05-16 (exact) |
| 4.pdf | 1 | T10_fix_2026-05-16 (exact) |
| 5.pdf | 6 | T10_fix_2026-05-16 (exact) |
| 6.pdf | 6 | T10_fix_2026-05-16 (exact) |
| 7.pdf | 1 | T10_fix_2026-05-16 (exact) |

---

## 10. 기존 warning 회귀 여부

- T-8b의 `insuranceCode:ocr_source_missing` warning: **회귀 없음** (T-25d dedup 로직이 기존 warning을 먼저 포함하므로 중복 없이 추가)
- valueMappingWarnings 초기화 위치(line 6353) 변경 없음

---

## 11. typecheck / build 결과

| 검증 | 결과 |
|-----|------|
| `py_compile` | **OK** |
| `npm run typecheck` | **PASS** (TypeScript 파일 변경 없음) |
| `npm run build` | **PASS** (모든 라우트 정상 컴파일) |

---

## 12. 구현 위치 요약

### 추가된 helper 함수 (6160번째 줄 직전 위치)
```
_t25d_amount_comma_space_cleanup(row) → str
_t25d_qty_trailing_symbol_cleanup(row) → str
_t25d_warning_only_checks(row, row_num, required_set) → list[str]
```

### `_build_canonical_table_rows` 내 변경점 3곳

**1. 초기화 (루프 이전)**
```python
_t25d_warnings: list[str] = []
_t25d_required_set: set[str] = (
    set(expected_columns.get("required") or []) if expected_columns else set()
)
```

**2. 루프 내 (T-7a 직후, col_fill 직전)**
```python
# T-25d: cell-level safe cleanup (amount comma-space + quantity trailing symbol)
_t25d_amt_w = _t25d_amount_comma_space_cleanup(row)
if _t25d_amt_w:
    _t25d_warnings.append(f"amount:comma_space_cleanup_applied:{_t25d_amt_w}")
_t25d_qty_w = _t25d_qty_trailing_symbol_cleanup(row)
if _t25d_qty_w:
    _t25d_warnings.append(f"quantity:trailing_markup_symbol_removed:{_t25d_qty_w}")
_t25d_warnings.extend(_t25d_warning_only_checks(row, idx + 1, _t25d_required_set))
```

**3. T-8b 직후 (valueMappingWarnings 내)**
```python
# T-25d: cell cleanup + warning-only warnings (deduped)
if _t25d_warnings:
    _t25d_seen: set[str] = set(table_meta["valueMappingWarnings"])
    for _w in _t25d_warnings:
        if _w not in _t25d_seen:
            _t25d_seen.add(_w)
            table_meta["valueMappingWarnings"].append(_w)
```

---

## 13. 다음 작업 제안

| 작업 | 내용 | 위험도 |
|-----|------|-------|
| **T-25c** | red_pen_suppression debug variant — row 4 mfg/exp, row 12 qty 복구 시도 | medium |
