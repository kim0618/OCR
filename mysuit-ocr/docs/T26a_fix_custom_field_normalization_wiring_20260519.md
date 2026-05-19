# T-26a-fix: RunOCR Custom field final value normalization wiring

**생성일**: 2026-05-19  
**사용 도구**: Claude Sonnet 4.6 (Claude Code)  
**코드 수정**: `ocr-server/main.py` 1개

---

## 1. 원인

T-26a에서 `invoice_statement.py`의 `fields.update()`에 company name normalization을 적용했으나, 실제 Custom 탭 "최종값"에 반영되지 않았다.

### 구조 불일치

| 구조 | 용도 | T-26a 적용 여부 |
|-----|------|--------------|
| `response["document_fields"]["supplierCompany"]` | 정형 추출값 dict (tableRows 포함) | ✓ 적용됨 |
| `response["fields"][N]["value"]` | Custom 탭 "최종값" 원천 | ✗ 적용 안 됨 |

- Custom 탭의 "최종값"은 `field.value`를 표시
- Custom 탭의 "OCR 원본"은 `field.original` (없으면 `field.value`)을 표시
- `field.value`는 template region raw OCR text — `document_fields`와 별도 구조

### 템플릿 매핑 확인

TPL-31D13CF3 (1.jpg용 템플릿) region 구조:

| region | koField | value (before) |
|--------|---------|----------------|
| field_2 | 공급자 상호 | `부광 약 품(주)` (raw OCR) |
| field_6 | 공급받는자 상호 | `백제약품(주)영등포지점 1010546N` (raw OCR) |

---

## 2. 백업 파일 목록

```
ocr-server/backup/main_20260519_1549_before_T26a_fix_custom_field_normalization_wiring.py
```

---

## 3. 수정 파일 목록

| 파일 | 변경 내용 |
|-----|---------|
| `ocr-server/main.py` | invoice_statement 추출 후 template fields 값 패치 블록 추가 |

---

## 4. 핵심 수정 내용

`main.py`에서 invoice_statement 추출 블록 직후, template path(`region_list` 있음)인 경우:

```python
# T-26a-fix
if doc_type == "invoice_statement" and region_list and "document_fields" in response:
    _T26A_KOFIELD_MAP = {
        "공급자 상호":     "supplierCompany",
        "공급자 회사명":   "supplierCompany",
        "공급받는자 상호": "buyerCompany",
        "공급받는자 회사명":"buyerCompany",
    }
    for field, region in zip(fields, region_list):
        ko = region.get("koField", "").strip()
        doc_key = _T26A_KOFIELD_MAP.get(ko)
        if not doc_key: continue
        norm = response["document_fields"].get(doc_key, "")
        if not norm: continue
        orig = field.get("value", "")
        if orig == norm: continue
        field["original"] = orig   # → "OCR 원본"에 표시
        field["value"] = norm      # → "최종값"에 표시
```

**적용 조건**:
- `doc_type == "invoice_statement"` (다른 문서 유형 미적용)
- `region_list` 있음 (template path만)
- `document_fields` 응답에 있음 (추출 성공 시만)
- `koField`가 "공급자 상호" 또는 "공급받는자 상호" 등 매핑 대상인 경우만

---

## 5. 1.jpg 공급자 상호 before/after

| 탭 표시 항목 | Before (T-26a만) | After (T-26a-fix) |
|-----------|----------------|-----------------|
| OCR 원본 | 부광 약 품(주) | **부광 약 품(주)** (그대로) |
| 최종값 | 부광 약 품(주) | **부광약품(주)** ✓ |

---

## 6. 1.jpg 공급받는자 상호 before/after

| 탭 표시 항목 | Before (T-26a만) | After (T-26a-fix) |
|-----------|----------------|-----------------|
| OCR 원본 | 백제약품(주)영등포지점 1010546N | **백제약품(주)영등포지점 1010546N** (그대로) |
| 최종값 | 백제약품(주)영등포지점 1010546N | **백제약품(주)영등포지점** ✓ |

---

## 7. 변경하지 않은 영역

| 필드 | 이유 |
|-----|------|
| 공급자 사업자 번호 | koField 매핑 없음 |
| 공급자 주소 | koField 매핑 없음 |
| 공급자 성명 | koField 매핑 없음 |
| 공급받는자 사업자 번호 | 매핑 없음 |
| 공급받는자 주소 | 매핑 없음 |
| 공급받는자 성명 | 매핑 없음 |
| 합계금액 | 매핑 없음 |
| tableRows | 미변경 |
| document_fields 구조 | 미변경 |

---

## 8. OCR 원본과 최종값 분리 확인

`field["original"]` → "OCR 원본"에 표시 (raw OCR 그대로)  
`field["value"]` → "최종값"에 표시 (normalized company name)

OcrResultPanel.tsx `getOriginalOcrValue()`:
```typescript
if (typeof field.original === "string" && field.original.trim()) 
  return field.original.trim();  // ← original이 있으면 이걸 "OCR 원본"으로 표시
```

---

## 9. T-25/T-26 기준선 유지 확인

| 기준선 | 상태 |
|-------|------|
| T-25d amount/qty cleanup | ✓ invoice_statement.py 미변경 |
| T-25g spec trailing cleanup | ✓ invoice_statement.py 미변경 |
| T-25f RESET (warning UI 없음) | ✓ OcrResultPanel.tsx 미변경 |
| T-26a company normalization (backend) | ✓ 유지 |
| itemName 자동 보정 금지 | ✓ 준수 |

---

## 10. rowCount exact 유지 확인

row 추가/삭제 코드 미변경. main.py의 invoice_statement 결과 조립 경로만 수정. rowCount 회귀 불가.

---

## 11. py_compile / typecheck / build 결과

| 항목 | 결과 |
|-----|------|
| `py_compile` (main.py) | **OK** |
| `py_compile` (invoice_statement.py) | **OK** |
| 시뮬레이션 테스트 (5 assertions) | **ALL PASS** |
| `npm run typecheck` | **PASS** |
| `npm run build` | **PASS** |

---

## 12. 다음 작업 제안

1. **서버 재시작 후 1.jpg RunOCR 실행** → Custom 탭 live 검증
2. **T-26b**: 2~7.pdf 공급자/공급받는자 상호 RunOCR 결과 확인
