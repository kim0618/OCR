# T-6f Test RunAll expectedColumns 전달 연결 결과

## 1. 수정 파일
- `C:\OCR\mysuit-ocr\src\components\test\TestWorkspace.tsx`
- `C:\OCR\ocr-server\main.py`

## 2. 백업 파일
- `C:\OCR\ocr-server\backup\main_20260512_before_T6f_expected_columns_payload.py`
- `C:\OCR\mysuit-ocr\backup\TestWorkspace_20260512_before_T6f_expected_columns_payload.tsx`

## 3. 핵심 요약

T-6e에서 구현된 `extract_invoice_statement_fields(..., table_expected_columns=...)` 경로를
실제 Test UI RunAll/RunOne 실행 시 활성화되도록 frontend→backend 전달 연결을 완성했다.

변경 전: `fetchOcr(filename, path)` → FormData에 file만 전달 → backend extractor 기본 경로(T-6 auto-detect)
변경 후: `fetchOcr(filename, path, tec)` → FormData에 `tableExpectedColumns` JSON 추가 → backend가 파싱하여 extractor에 전달 → T-6e expectedColumns 경로 활성

---

## 4. frontend payload 변경

### `fetchOcr` 함수 시그니처 변경
```typescript
// 전: 
async function fetchOcr(filename: string, imageBaseUrl: string): Promise<OcrEntry>

// 후:
async function fetchOcr(
  filename: string,
  imageBaseUrl: string,
  tableExpectedColumns?: { required: string[]; optional?: string[] } | null,
): Promise<OcrEntry>
```

### FormData 추가 필드
```typescript
if (tableExpectedColumns) {
  form.append("tableExpectedColumns", JSON.stringify(tableExpectedColumns));
}
```

### `runOne` 호출 변경
```typescript
const _runOneMeta = manifest?.items.find((item) => item.filename === filename);
const _runOneTec = _runOneMeta?.invoiceProfile?.tableExpectedColumns ?? null;
const entry = await fetchOcr(filename, activeTestset.path, _runOneTec);
```

### `runAll` 호출 변경
```typescript
const _runAllMeta = manifest?.items.find((item) => item.filename === name);
const _runAllTec = _runAllMeta?.invoiceProfile?.tableExpectedColumns ?? null;
const entry = await fetchOcr(name, activeTestset.path, _runAllTec);
```

**tableExpectedColumns 포함 여부**: invoice_statement manifest에 `invoiceProfile.tableExpectedColumns`가 있으면 포함됨. 다른 문서 타입이나 tableExpectedColumns가 없는 경우 `null` → FormData에 추가 안 됨.

**tableBounds 포함 여부**: 이번 작업에서는 추가하지 않음. 향후 Template 연동 시 추가 예정.

---

## 5. backend main.py 변경

### `/ocr/extract` 엔드포인트 파라미터 추가
```python
@app.post("/ocr/extract")
async def ocr_extract(
    file: UploadFile = File(...),
    template_id: str = Form(""),
    regions: str = Form(""),
    corners: str = Form(""),
    model_id: str = Form(""),
    tableExpectedColumns: str = Form(""),  # T-6f: NEW
    tableBounds: str = Form(""),           # T-6f: future use
):
```

### `invoice_statement` 블록에서 파싱 및 전달
```python
# T-6f: parse tableExpectedColumns from request payload
_tec = None
if tableExpectedColumns:
    try:
        _tec = json.loads(tableExpectedColumns)
    except (json.JSONDecodeError, ValueError):
        _tec = None
_tbn = None
if tableBounds:
    try:
        _tbn = json.loads(tableBounds)
    except (json.JSONDecodeError, ValueError):
        _tbn = None

document_fields = extract_invoice_statement_fields(
    ocr_lines_raw,
    debug=invoice_debug,
    table_expected_columns=_tec,
    table_bounds=_tbn,
)
```

**수신 key**: `tableExpectedColumns` (Form field)
**extractor 전달 인자**: `table_expected_columns=_tec`, `table_bounds=_tbn`
**backward compatibility**: Form 기본값 `""` → `_tec = None` → `extract_invoice_statement_fields` 기존 동작 유지. 다른 문서 타입에는 invoice_statement 블록 자체가 실행되지 않으므로 영향 없음.

### 로그 보강
```
[invoice_statement] ... tec=yes tec_used=True src=expected_columns_header_match
```

---

## 6. tableMeta 확인 기준

실제 RunAll에서 T-6e 경로가 활성화되면 다음 값이 나와야 함:
- `tableMeta.extractionSource`: `"expected_columns_header_match"` (또는 fallback 시 `"header_column_mapping"` / `"legacy_text_items"`)
- `tableMeta.expectedColumnsUsed`: `true`
- `tableMeta.tableBoundsUsed`: `false` (이번 작업에서 table_bounds 미전달)

실패 판단:
- `expectedColumnsUsed: false` → payload 전달 실패 또는 T-6e 경로에서 matched headers < 2

---

## 7. 검증 결과

- **main.py py_compile**: ✓ PASS
- **invoice_statement.py py_compile**: ✓ PASS
- **typecheck**: ✓ PASS (오류 없음)
- **build**: ✓ PASS (모든 route 빌드 성공, `/test` 포함)

---

## 8. RunAll 확인 결과

> **실제 RunAll은 backend 재시작 후 브라우저 Test UI에서 확인 필요.**
> 아래는 이론적 예상이며 실제 OCR 결과에 따라 달라질 수 있다.

| 샘플 | tableExpectedColumns 전달 | 예상 expectedColumnsUsed | 예상 extractionSource | 비고 |
|---|---|---|---|---|
| 1.jpg | ✓ | true | expected_columns_header_match | 헤더 band 탐색 성공 예상 |
| 2.pdf | ✓ | true | expected_columns_header_match 또는 fallback | landscape OCR 구조에 따라 |
| 3.pdf | ✓ | true | expected_columns_header_match | 보험코드/품명 등 헤더 있음 |
| 4.pdf | ✓ | true | expected_columns_header_match | LotNo./단위 등 헤더 있음 |
| 5.pdf | ✓ | true | expected_columns_header_match | 품명/품목코드 헤더 있음 |
| 6.pdf | ✓ | true | expected_columns_header_match | 제품코드/제품명 헤더 있음 |
| 7.pdf | ✓ | true | expected_columns_header_match | 품명/단위/수량 헤더 있음 |

> 실제 RunAll 결과를 브라우저에서 확인하고 위 표를 채워야 함.

---

## 9. 남은 문제

1. **실제 RunAll 결과 미확인**: backend 재시작 후 Test UI에서 RunAll을 실행해야 실제 T-6e 경로 활성화 여부 확인 가능.

2. **T-6e 경로 실패 가능성**: 실제 OCR 결과에서 expected header band score < 2이면 T-6e fallback → 기존 auto-detect 경로로 복귀. 이 경우 `expectedColumnsUsed=false`.

3. **tableBounds 미전달**: Template에서 사용자가 표 영역을 그릴 경우 별도 작업 필요.

4. **2.pdf landscape 구조**: header band 탐색이 landscape(가로) 문서에서도 동작하는지 실제 OCR 결과로 확인 필요.

---

## 10. 다음 작업 판단

**T-6f 연결 완료 상태**: frontend→backend payload 전달 및 extractor 연결 완성.

실제 RunAll 후:
- `expectedColumnsUsed=true` + rowCount/column 개선 → **T-7 금액 계열 보정 검토 가능**
- `expectedColumnsUsed=true` 이지만 rowCount/column 여전히 부족 → **T-6e-fix** (header band 탐색 정밀도 개선)
- `expectedColumnsUsed=false` → payload 전달 확인 / T-6e 경로 디버그 필요
