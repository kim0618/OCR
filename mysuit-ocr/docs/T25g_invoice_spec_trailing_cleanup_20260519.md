# T-25g: 거래명세서 spec trailing character safe cleanup 리포트

**생성일**: 2026-05-19  
**사용 도구**: Claude Sonnet 4.6 (Claude Code)  
**코드 수정**: `ocr-server/extractors/invoice_statement.py` 1개

---

## 1. 요약

| 항목 | 결과 |
|------|------|
| 백업 파일 | `backup/invoice_statement_20260519_1456_before_T25g_spec_trailing_cleanup.py` |
| 수정 파일 | `ocr-server/extractors/invoice_statement.py` |
| 추가 helper | `_cleanup_spec_trailing_chars()` |
| 추가 regex | `_T25G_ML_TRAILING_RE`, `_T25G_OPEN_PAREN_RE` |
| spec 개선 | 3건 (500T(B), 150m, 500m) |
| T-25d cleanup 유지 | ✓ |
| rowCount 회귀 | 없음 (row 추가/삭제 코드 미변경) |
| py_compile | **OK** |
| typecheck | **PASS** |
| build | **PASS** |
| 단위 테스트 | **17/17 PASS** |
| 통합 테스트 | **PASS** |

---

## 2. 백업 파일 목록

```
ocr-server/backup/invoice_statement_20260519_1456_before_T25g_spec_trailing_cleanup.py
```

---

## 3. 수정 파일 목록

| 파일 | 변경 내용 |
|-----|---------|
| `ocr-server/extractors/invoice_statement.py` | T-25g 섹션 추가 (helper + 루프 내 호출) |

---

## 4. spec trailing cleanup 규칙

### Rule A: 닫힘 괄호 누락 복구

```
조건: "(" 있음 + ")" 없음 + 길이 ≤ 20자 + 괄호 앞 부분이 정상 spec 패턴
처리: 끝에 ")" 추가
예시: 500T(B → 500T(B)
     100T(A → 100T(A)
```

warning key: `spec:trailing_closing_parenthesis_restored`

### Rule B: ml suffix 누락 복구

```
조건: 값이 ^\d{1,4}[mM]$ 에 fullmatch
처리: 끝에 "l" 추가
예시: 150m → 150ml
     500m → 500ml
     30m  → 30ml
```

warning key: `spec:trailing_ml_suffix_restored`

**우선순위**: Rule B → Rule A (B가 적용되면 A는 스킵)

---

## 5. 1.jpg 개선 예시

| rowIndex | itemName | before | after | rule |
|---------|---------|--------|-------|------|
| 8 | 파자임정95mg | `500T(B` | `500T(B)` | Rule A |
| 23 | 오르필시럽 | `150m` | `150ml` | Rule B |
| 26 | 소아용프리마란시럽 | `500m` | `500ml` | Rule B |

---

## 6. 변경하지 않은 필드

| 필드 | 이유 |
|-----|------|
| itemName | 자동 보정 금지 (별도 correction profile 구조로 처리 예정) |
| quantity | T-25d cleanup만 유지 (빈 값 자동 삽입 금지) |
| manufacturingNo, expiryDate | 자동 복구 금지 |
| unitPrice, amount, supplyAmount, taxAmount, totalAmount | T-25d cleanup만, 추가 수정 없음 |

---

## 7. T-25d cleanup 유지 확인

| 케이스 | before | after | 상태 |
|-------|--------|-------|------|
| row 5 quantity | `360 ^` | `360` | ✓ |
| row 19 amount | `301, 100` | `301,100` | ✓ |
| row 20 amount | `782, 160` | `782,160` | ✓ |
| row 21 amount | `163, 100` | `163,100` | ✓ |
| row 26 amount | `220, 890` | `220,890` | ✓ |

---

## 8. 변경되지 않는 spec 값

| spec 값 | 이유 |
|--------|------|
| `15m\|*6포` | 파이프/포 포함 → ml regex 미매칭, 괄호 없음 |
| `150mI` | m 뒤에 I 있음 → `^\d+m$` 미매칭 |
| `500n1` | m 없음 → 미매칭 |
| `30T`, `500C`, `100T`, `120DOSE`, `10g`, `4T` | 정상 spec → 변경 없음 |
| `500T(B)` | 이미 `)` 있음 → Rule A 미적용 |

---

## 9. invoice_statement 7개 rowCount exact 유지 확인

row 추가/삭제 코드 미변경. spec 필드 값만 수정. rowCount 회귀 불가.

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

## 10. py_compile / typecheck / build 결과

| 항목 | 결과 |
|-----|------|
| `py_compile` | **OK** |
| 단위 테스트 (17 케이스) | **17/17 PASS** |
| 통합 테스트 | **ALL ASSERTIONS PASSED** |
| `npm run typecheck` | **PASS** |
| `npm run build` | **PASS** |

---

## 11. 구현 위치

### 추가된 helper 및 regex (T-25d 섹션 직후)
```python
_T25G_ML_TRAILING_RE = re.compile(r"^\d{1,4}[mM]$")
_T25G_OPEN_PAREN_RE  = re.compile(r"^([^\(\)]{1,18})\([A-Za-z0-9]{0,4}$")

def _cleanup_spec_trailing_chars(value: str) -> tuple[str, list[str]]: ...
```

### `_build_canonical_table_rows` 내 호출 (T-25d 블록 직후)
```python
# T-25g: spec trailing character safe cleanup (ml suffix + closing parenthesis)
if row.get("spec"):
    _t25g_spec, _t25g_debug = _cleanup_spec_trailing_chars(str(row["spec"]))
    if _t25g_debug:
        row["spec"] = _t25g_spec
        _t25d_warnings.extend(_t25g_debug)
```

---

## 12. 다음 작업 제안

| 작업 | 내용 | 우선순위 |
|-----|------|---------|
| correction profile | 사용자 수정 tableRows 값 저장 → 다음 OCR에서 동일 품목코드 발견 시 후보 표시 | 미래 |
| itemName OCR 오인식 | 아집린청 같은 품목명 문제는 correction profile 완성 후 처리 | 미래 |
