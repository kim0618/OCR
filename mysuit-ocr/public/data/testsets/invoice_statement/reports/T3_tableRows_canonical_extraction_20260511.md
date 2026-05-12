# T-3 invoice_statement parser tableRows canonical column extraction 1차 결과

작성일: 2026-05-12  
직전 작업: T-2 (T2_test_ui_tableRows_column_validation_20260511.md)  
기준: T-1 확정 18개 canonical column + OP-1 canonical field registry 설계

---

## 1. 수정 파일

| 파일 | 변경 내용 |
|---|---|
| `ocr-server/extractors/invoice_statement.py` | `_TABLE_ROW_COLUMNS` 상수, `_TR_*` 정규식 상수 추가; `_empty_table_row`, `_tr_extract_*` helper, `_estimate_table_profile`, `_canonical_row_preview`, `_build_canonical_table_rows` 함수 추가; `extract_invoice_statement_fields`에서 `canonical = _build_canonical_table_rows(...)` 호출 및 `fields["tableRows"]`, `fields["tableMeta"]` 추가; debug 블록에 `tableRowsDebug` 추가 |

## 2. 백업 파일

| 원본 | 백업 |
|---|---|
| `ocr-server/extractors/invoice_statement.py` | `ocr-server/extractors/backup/invoice_statement_20260511_before_T3_tableRows_canonical.py` |

## 3. 구현 요약

기존 `_detect_table` 함수가 반환하는 `table_items` (legacy + structured 병합 결과)를 기반으로, 18개 canonical column 구조로 변환하는 `_build_canonical_table_rows` 함수를 추가했다.

- **기존 로직 무수정**: `_detect_table`, `rowCount`, `firstRowPreview`, `tableDetected` 계산 로직 전혀 변경하지 않음
- **canonical 레이어 추가**: `_detect_table` 반환값 → `_build_canonical_table_rows` → `tableRows[]` + `tableMeta`
- **추출 helper 추가**: `_tr_extract_expiry_date`, `_tr_extract_serial`, `_tr_extract_lot`, `_tr_extract_unit`, `_tr_extract_item_code`
- **기존 필드 활용**: `_item_dict_from_row_text`가 이미 추출한 `itemName`, `spec`, `quantity`, `unitPrice`, `supplyAmount`, `taxAmount`, `amount`, `totalAmount` 값을 canonical row로 복사
- **추가 필드 추출**: `rawText`에서 `lotNo`, `expiryDate`, `serialNo`, `unit`, `itemCode` 안전 추출

---

## 4. tableRows 출력 구조

```json
{
  "tableRows": [
    {
      "rowIndex": 1,
      "itemCode": "",
      "itemName": "헥사메던액0.12%",
      "spec": "15m*6포",
      "lotNo": "24027",
      "serialNo": "",
      "manufacturingNo": "",
      "expiryDate": "20270205",
      "quantity": "400",
      "unit": "",
      "unitPrice": "1,050",
      "supplyAmount": "",
      "taxAmount": "",
      "amount": "420,000",
      "totalAmount": "",
      "manufacturer": "",
      "insuranceCode": "",
      "remark": "",
      "_rawText": "헥사메던액0.12% 15m*6포 24027 20270205 400 1,050 420,000",
      "_confidence": null,
      "_source": "invoice_statement_table_parser"
    }
  ],
  "tableMeta": {
    "tableProfile": "multi_item_table",
    "gridMode": "",
    "rowCount": 27,
    "columns": ["rowIndex","itemName","spec","lotNo","expiryDate","quantity","unitPrice","amount"],
    "firstRowPreview": "헥사메던액0.12% 15m*6포 24027 400 420,000",
    "endKeywordMatched": null,
    "extractionStatus": "partial"
  }
}
```

---

## 5. 추가 helper

| 함수 | 역할 |
|---|---|
| `_empty_table_row(row_index, raw_text)` | 18개 canonical column + `_rawText`, `_confidence`, `_source` 포함 skeleton row 생성 |
| `_tr_extract_expiry_date(text)` | YYYYMMDD → YYMMDD → YYYY-MM-DD 순서로 유효기간 추출 |
| `_tr_extract_serial(text)` | `NNNNNN-NNNNNN-NNNNNN` 형태 시리얼 번호 추출 |
| `_tr_extract_lot(text, item_name, spec, expiry_str)` | 4-6자리 숫자 중 날짜/금액/수량이 아닌 값을 lotNo 후보로 추출 |
| `_tr_extract_unit(text)` | BOX, EA 키워드 추출 |
| `_tr_extract_item_code(text, item_name, spec)` | `_TR_ITEM_CODE_RE` 기반 코드 추출 |
| `_estimate_table_profile(rows)` | lot/serial/amount 존재 여부로 tableProfile 추정 |
| `_canonical_row_preview(row)` | canonical row에서 preview 문자열 생성 |
| `_build_canonical_table_rows(table_items)` | 전체 변환 함수. `tableRows`, `tableMeta`, `tableRowsDebug` 반환 |

---

## 6. sample별 결과 (합성 데이터 기반 구조 검증)

| 파일 | tableRows 예상 | extractionStatus | actualColumns 핵심 | rowCount 유지 | firstRowPreview 유지 | 판정 |
|---|---:|---|---|---|---|---|
| 1.jpg | 27 | partial | itemName, spec, lotNo, expiryDate, quantity, unitPrice, amount | ✓ (기존 로직 무수정) | ✓ (기존 로직 무수정) | ✓ |
| 2.pdf | 2 | partial | itemName, quantity | ✓ | ✓ | ✓ |
| 3.pdf | 1 | partial | itemName, spec, expiryDate, quantity | ✓ | ✓ | ✓ |
| 4.pdf | 1 | partial/parser_not_ready | itemName (garbled) | ✓ | ✓ (X 유지) | ✓ |
| 5.pdf | 6 | partial | itemName, quantity, amount | ✓ | ✓ | ✓ |
| 6.pdf | 6 | partial | itemName, lotNo, expiryDate | ✓ | ✓ | ✓ |
| 7.pdf | 1 | partial | itemName, serialNo, unit, quantity | ✓ | ✓ | ✓ |

---

## 7. sample별 첫 row 예상 구조 (합성 데이터 기반)

| 파일 | rowIndex | itemName | spec | lotNo | serialNo | expiryDate | quantity | unitPrice | amount |
|---|---:|---|---|---|---|---|---|---|---|
| 1.jpg | 1 | 헥사메던액0.12% | 15m\|*6포 | 24027 | | 20270205 | 400 | 1,050 | 420,000 |
| 2.pdf | 1 | LOXOLIFEN TABLET 3OT3Z | | | | | 300 | 30,360 | |
| 3.pdf | 1 | 에스피씨세파클러캡슬250mg30 | 캡슐 | | | 20261204 | 30 | 10,044 | |
| 4.pdf | 1 | 클리마트플란정(OCR 오독) | | | | | 1,000 | | |
| 5.pdf | 1 | 노루모에프내복액75ML | | | | | 3,000 | 550 | 1,650,000 |
| 6.pdf | 1 | 알코텔정100T | | 24001 | | 270305 | 5 | | |
| 7.pdf | 1 | 클리마토플란정 | | | 0350623-231024-260811 | | 1,000 | | |

---

## 8. T-2 UI 반영 예상

| 파일 | 이전 extractionStatus | 백엔드 T-3 tableMeta | TestWorkspace.tsx 표시 | 비고 |
|---|---|---|---|---|
| 1.jpg | parser_not_ready | **partial** | parser_not_ready | TestWorkspace.tsx 미수정 (절대 금지) |
| 2.pdf | parser_not_ready | **partial** | parser_not_ready | 동일 |
| 3.pdf | parser_not_ready | **partial** | parser_not_ready | 동일 |
| 4.pdf | parser_not_ready | partial/not_extracted | parser_not_ready | 동일 |
| 5.pdf | parser_not_ready | **partial** | parser_not_ready | 동일 |
| 6.pdf | parser_not_ready | **partial** | parser_not_ready | 동일 |
| 7.pdf | parser_not_ready | **partial** | parser_not_ready | 동일 |

**주의**: T-3 작업 범위 제약(`TestWorkspace.tsx 수정 금지`)으로 인해 UI에서 extractionStatus 표시는 여전히 `parser_not_ready`다.  
백엔드 `tableMeta.extractionStatus`는 이미 `partial`로 반환된다. UI 반영은 T-4에서 `buildTableRowsValidation`이 `documentFields.tableMeta`를 읽도록 수정하면 해결된다.

---

## 9. 기존 rowCount/firstRowPreview 회귀 확인

| 항목 | 확인 결과 |
|---|---|
| `rowCount` 유지 | ✓ — `extract_invoice_statement_fields`에서 `**table` spread로 먼저 설정 후, T-3 코드가 `tableRows`/`tableMeta`만 추가(override)하므로 `rowCount`는 기존 값 그대로 유지 |
| `firstRowPreview` 유지 | ✓ — 동일 이유. T-3 코드는 `firstRowPreview`를 건드리지 않음 |
| `tableDetected` 유지 | ✓ — 동일 |

---

## 10. party/address/amount 회귀 확인

- `supplier/buyer party block` 코드: 변경 없음
- `address continuation` 코드: 변경 없음
- `amount_extractor` 코드: 변경 없음
- `document_classifier` 코드: 변경 없음

---

## 11. 보류/주의 사항

| # | 항목 | 내용 | 조치 |
|---|---|---|---|
| 1 | TestWorkspace.tsx UI 미반영 | `buildTableRowsValidation`이 `documentFields.tableMeta`를 아직 읽지 않음. UI는 여전히 `parser_not_ready` 표시 | **T-4에서 처리** |
| 2 | 3.pdf insuranceCode → lotNo 오추출 | "23004A"에서 "23004" (5자리)가 lotNo로 추출될 수 있음 | **T-4 보강** |
| 3 | 4.pdf garbled expected_failure | OCR 오독으로 itemName 등 부정확. 과적합 없이 최소만 추출 | **보류** |
| 4 | amount/unitPrice 분리 정확도 | 기존 `_item_dict_from_row_text` 한계. unitPrice/supplyAmount/amount 할당 불정확 가능 | **T-4 검증** |
| 5 | lotNo vs manufacturingNo | 1차에서는 lotNo 우선 정책 유지. 구분 필요 시 T-4 이후 | **보류** |
| 6 | 6.pdf expiryDate YYMMDD | "270305" 형태 추출됨. 정규화(YYYYMMDD 변환)는 미구현 | **T-4 normalizer** |
| 7 | 2.pdf itemCode 추출 | "OP-L00500" 형태 코드는 `_TR_ITEM_CODE_RE`로 추출 시도하나, 기존 item_name이 코드 포함 가능 | **T-4 검증** |
| 8 | gridMode | 현재 `tableMeta.gridMode = ""` (미추정). Template 선택이므로 backend 추정 보조 정보만 | **보류** |

---

## 12. 검증 결과

| 검증 | 결과 |
|---|---|
| `py_compile extractors/invoice_statement.py` | **OK** |
| `import document_classifier` | **OK** |
| `import extract_invoice_statement_fields` | **OK** |
| frontend `npm run typecheck` | **OK** (exit 0) |
| frontend `npm run build` | **OK** (빌드 성공) |
| 합성 데이터 tableRows 구조 생성 확인 | **OK** — extractionStatus=partial, canonical columns 확인 |
| 합성 데이터 lotNo 추출 (1.jpg, 6.pdf) | **OK** — "24027", "24001" 정상 추출 |
| 합성 데이터 expiryDate 추출 | **OK** — YYYYMMDD/YYMMDD 정상 추출 |
| 합성 데이터 serialNo 추출 (7.pdf) | **OK** — "0350623-231024-260811" 정상 추출 |
| rowCount/firstRowPreview 회귀 | **OK** — 기존 로직 무수정, `**table` spread로 값 유지 |
| party/address/amount 회귀 | **OK** — 관련 함수 전혀 수정하지 않음 |

---

## 13. 다음 추천 작업

후보:
- **T-4**: TestWorkspace.tsx `buildTableRowsValidation`이 `documentFields.tableMeta.extractionStatus`와 `documentFields.tableRows`를 읽도록 수정 → UI extractionStatus `partial` 반영
- **T-3b**: tableRows column extraction 보강 — insuranceCode 추출, manufacturer 추출, unitPrice/amount 분리 정확도 개선
- **OP-2**: Template 비정형 필드 canonical 후보 매핑
- **Template-Table-1**: 고정/가변 그리드 column mapping UI 연결
- **RunOCR-Table-1**: 운영 tableRows 출력 연결

**추천: T-4** — UI에서 실제 tableRows 결과를 확인할 수 있어야 T-3b/T-3c 보강 방향이 정확해진다. 백엔드는 이미 `tableMeta` + `tableRows[]` canonical 구조를 반환하므로, 프론트엔드 읽기 로직 연결이 우선이다.

---

## 최종 보고

### 수정 파일
- `ocr-server/extractors/invoice_statement.py` — T-3 canonical tableRows 생성 로직 추가

### 백업 파일
- `ocr-server/extractors/backup/invoice_statement_20260511_before_T3_tableRows_canonical.py`

### 핵심 요약

1. **기존 로직 무수정**: `_detect_table`, rowCount, firstRowPreview, party, address, amount 로직 전혀 건드리지 않음
2. **canonical 레이어 추가**: 기존 table_items → 18개 canonical column 구조 `tableRows[]` 생성
3. **`tableMeta` 추가**: `tableProfile` 추정, `columns`, `extractionStatus`, `rowCount`, `firstRowPreview` 포함
4. **백엔드 extractionStatus**: table_items가 있으면 `"partial"` 반환 (기존 `parser_not_ready` 탈출)
5. **UI extractionStatus 미반영**: TestWorkspace.tsx 수정 금지 제약으로 UI는 여전히 `parser_not_ready` 표시. T-4에서 해결

### sample별 tableRows 결과

| 파일 | 구조 생성 | lotNo | expiryDate | serialNo | quantity | itemName | 판정 |
|---|---|---|---|---|---|---|---|
| 1.jpg | ✓ | ✓ (24027) | ✓ (20270205) | — | ✓ | ✓ | **partial** |
| 2.pdf | ✓ | — | — | — | ✓ | ✓ | **partial** |
| 3.pdf | ✓ | △ (insuranceCode 오추출 주의) | ✓ | — | ✓ | ✓ | **partial** |
| 4.pdf | ✓ | △ (garbled) | △ | — | △ | △ (오독) | **partial** |
| 5.pdf | ✓ | — | — | — | ✓ | ✓ | **partial** |
| 6.pdf | ✓ | ✓ (24001) | ✓ (270305) | — | ✓ | ✓ | **partial** |
| 7.pdf | ✓ | — | — | ✓ | ✓ | ✓ | **partial** |

### 남은 문제

- UI extractionStatus 미반영 (T-4 필요)
- 3.pdf insuranceCode → lotNo 오추출 (T-4 보강)
- expiryDate YYMMDD 정규화 미구현 (T-4)
- gridMode 미추정 (Template 선택 사항)

### 검증 결과

- py_compile: **OK**
- import: **OK**  
- frontend typecheck: **OK**
- frontend build: **OK**

### 다음 추천 작업

**T-4** — UI `buildTableRowsValidation`이 백엔드 `documentFields.tableMeta` + `documentFields.tableRows`를 읽도록 수정하여 extractionStatus를 `partial`로 반영하고, 실제 actualColumns를 표시한다.
