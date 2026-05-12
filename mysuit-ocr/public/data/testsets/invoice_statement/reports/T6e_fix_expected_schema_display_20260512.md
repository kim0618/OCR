# T-6e-fix expectedColumns 스키마 고정 및 표시 정리 결과

## 1. 수정 파일
- `C:\OCR\ocr-server\extractors\invoice_statement.py`
- `C:\OCR\mysuit-ocr\src\components\test\TestWorkspace.tsx`

## 2. 백업 파일
- `C:\OCR\ocr-server\backup\invoice_statement_20260512_before_T6e_fix_expected_schema.py`
- `C:\OCR\mysuit-ocr\backup\TestWorkspace_20260512_before_T6e_fix_expected_schema.tsx`

## 3. 핵심 요약

**이번 작업의 핵심**: `tableExpectedColumns`가 있는 경우, 결과 표의 컬럼 구조를 expectedColumns 전체 기준으로 고정.

- OCR이 일부 헤더를 못 읽어도 컬럼은 사라지지 않음
- 값이 없는 cell은 `""` (빈 문자열)로 존재함
- UI는 자동으로 "expected 컬럼" 모드로 전환되어 스키마 전체를 표시함
- missing required columns는 헤더에 빨간색으로 표시됨

---

## 4. 구현 내용

### 4.1 backend — `_build_canonical_table_rows` expected schema 처리

**시그니처 변경**:
```python
def _build_canonical_table_rows(
    table_items: list[dict[str, Any]],
    expected_columns: dict[str, list[str]] | None = None,  # NEW
    matched_column_keys: list[str] | None = None,           # NEW
) -> dict[str, Any]:
```

**expected schema 처리**:
1. `expected_columns`에서 `required + optional` 순서로 `expected_all_keys` 빌드
2. 각 canonical row에 expected keys가 없으면 `""` 값으로 보장
3. `missingExpectedColumnKeys` = expected required 중 값이 없는 컬럼

**tableMeta 추가 필드**:
```python
if expected_all_keys:
    table_meta["expectedColumnKeys"] = expected_all_keys   # 스키마 전체 순서
    table_meta["matchedColumnKeys"] = matched_keys_clean   # OCR에서 헤더 매칭 성공
    table_meta["valueColumnKeys"] = value_column_keys      # 실제 값이 있는 컬럼
    table_meta["missingExpectedColumnKeys"] = missing_expected_required
```

**tableRowsDebug 추가**:
```python
"expectedColumnsApplied": bool(expected_all_keys),
"displaySchemaColumnKeys": expected_all_keys or actual_columns,
"columnSchemaSource": "expected_columns" if expected_all_keys else "actual_detected",
```

### 4.2 backend — `extract_invoice_statement_fields` 호출 변경

```python
tdbg = table.get("tableDebug") or {}
_matched_keys = tdbg.get("matchedHeaders", [])
canonical = _build_canonical_table_rows(
    table.get("tableRows") or table.get("items") or [],
    expected_columns=table_expected_columns,
    matched_column_keys=_matched_keys,
)
```

### 4.3 frontend — `CanonicalTableMeta` 타입 확장

```typescript
type CanonicalTableMeta = {
  ...기존 필드...
  // T-6e-fix: expected schema fields
  expectedColumnsUsed?: boolean;
  extractionSource?: string;
  expectedColumnKeys?: string[];     // 스키마 전체 순서
  matchedColumnKeys?: string[];      // 헤더 매칭 성공 컬럼
  valueColumnKeys?: string[];        // 값 있는 컬럼
  missingExpectedColumnKeys?: string[];  // missing required
};
```

### 4.4 frontend — 표시 모드 추가 (`"expected"`)

```typescript
type TableDisplayMode = "detected" | "all" | "hasValue" | "expected";
```

**`getDisplayTableColumns` `"expected"` 모드**:
- `tableMeta.expectedColumnKeys`를 순서대로 사용
- `rowIndex` 항상 첫 번째
- expectedColumnKeys 없으면 detected 모드로 fallback

### 4.5 frontend — `InvoiceTableRowsPanel` 변경

**auto-switch** (새 OCR 결과가 들어올 때 자동으로 expected 모드):
```typescript
const prevExpColKeyRef = React.useRef<string>("");
React.useEffect(() => {
  const newKey = (tableMeta?.expectedColumnKeys ?? []).join(",");
  if (newKey && newKey !== prevExpColKeyRef.current) {
    setDisplayMode("expected");
    prevExpColKeyRef.current = newKey;
  }
}, [tableMeta?.expectedColumnKeys]);
```

**헤더 expected 정보 표시**:
```
expected 7개  missing: unitPrice, amount
```

**표시 모드 버튼** (expectedColumnKeys 있을 때 "expected 컬럼" 버튼 앞에 추가):
```
[expected 컬럼] [실제 감지 컬럼] [값 있는 컬럼] [전체 canonical 18개]
```

---

## 5. 검증 결과

- **py_compile** (invoice_statement.py): ✓ PASS
- **verify script**: ✓ 실행 완료 (rowCount 회귀 없음, 1.jpg t6e=YES 유지)
- **typecheck**: ✓ PASS (오류 없음)
- **build**: ✓ PASS (`/test` 42.6 kB, 빌드 성공)

---

## 6. 샘플별 expected schema 표시 확인 (실제 RunAll 후 확인 필요)

| 샘플 | expected schema | expectedColumnKeys 예상 | rowCount | 비고 |
|---|---|---:|---|---|
| 1.jpg | 품목, 규격, 제조번호, 유효기간, 수량, 단가, 금액 | 7개 | 23~28 | T-6e 경로 활성 |
| 2.pdf | 품목코드, 품목명, 수량, 단가, 공급금액, 보험No | 6개 | 미확인 | — |
| 3.pdf | 보험코드, 품명, 규격, 수량, 단가, 금액, 제조회사, 제조번호+유효기간 | 9개 | 미확인 | — |
| 4.pdf | 품목명, LotNo, 단위, 수량, 단가, 공급가액, 세액 | 7개 | 미확인 | — |
| 5.pdf | 품명, 품목코드, 수량, 단가, 금액 | 5개 | 6 | rowCount 유지 |
| 6.pdf | 제품코드, 제품명, 수량, LotNo, 유효일자 | 5개 | 6 | rowCount 유지 |
| 7.pdf | 품명, 시리얼/로트No, 단위, 수량 | 4개 | 1 | rowCount 유지 |

> 실제 RunAll 결과로 위 표를 채워야 함. 특히 expected 모드에서 컬럼이 스키마 기준으로 고정되는지 확인.

---

## 7. 다음 작업 판단

**T-6e-fix 완료**: expected schema 고정 구조 완성.

- expected 컬럼 표시 모드가 UI에 추가됨 → 실제 RunAll에서 스키마 고정 확인 필요
- **rowCount는 이번 작업에서 의도적으로 건드리지 않음** → T-6g row grouping 보정 단계에서 개선
- 1.jpg rowCount 23~27 유지(기존 수준), 5/6/7.pdf rowCount 유지됨
- 2.pdf rowCount 2 문제는 표 스키마와 별개로 row detection 문제 → T-6g

**판단**:
- expected schema 표시 UI 완성 → 실제 RunAll 브라우저 확인 후 row grouping 보정 단계
- rowCount가 핵심으로 남음 → **T-6g row grouping 보정** 또는 template bounds 연동 고려
