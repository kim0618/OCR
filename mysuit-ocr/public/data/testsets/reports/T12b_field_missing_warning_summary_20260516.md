# T-12b field missing / warning summary 결과

## 1. 수정 파일

| 파일 | 변경 내용 |
|---|---|
| `mysuit-ocr/src/components/test/TestWorkspace.tsx` | `parseWarningKey` 함수 추가, `DocTypeSummaryRow` 2개 필드 추가, `docTypeSummary` 집계 로직, `getInvoiceColLabel` 헬퍼, missing/warning 상세 UI |

## 2. 핵심 요약

- `parseWarningKey(w)` 헬퍼로 warning 문자열을 `"fieldKey:warningType"` 단위로 파싱
- `DocTypeSummaryRow`에 `missingFieldCounts` / `warningTypeCounts` 필드 추가
- `docTypeSummary` 계산 시 manifest required columns 기준으로 missing field 집계
- `tableMeta.valueMappingWarnings` 파싱으로 warning type별 count 집계
- `DocTypeSummarySection` 거래명세서 sub-table 아래에 Missing Top / Warn Top 상세 표시
- typecheck ✓ / build ✓ (44.6 kB)

## 3. expectedMissingKeys 집계

`tableMeta.missingExpectedColumnKeys` 대신 **실제 tableRows 데이터 기준**으로 집계:
- manifest `tableExpectedColumns.required` 목록의 각 column key에 대해
- 해당 샘플의 모든 tableRows에서 해당 key에 값이 있는지 확인
- 없으면 `missingFieldCounts[key]++`

이 방식은 OCR API 응답 구조에 무관하게 동작하며, 실제 추출된 데이터 기준으로 정확한 missing 판정이 가능하다.

**invoice_statement 예상 missing 후보** (RunAll 실행 후 확인):
- `insuranceCode` — 3.pdf 에서 자주 미추출
- `spec` — 일부 문서에서 누락
- `manufacturer` — 3.pdf 에서 누락 가능

## 4. valueMappingWarnings 집계

### parseWarningKey 파싱 규칙

| 입력 형식 | 출력 |
|---|---|
| `"insuranceCode:ocr_source_missing:..."` | `"insuranceCode:ocr_source_missing"` |
| `"taxAmount:doc_level_pushdown"` | `"taxAmount:doc_level_pushdown"` |
| `"multiline_layout_mapping_applied"` | `"multiline_layout_mapping_applied"` |
| `"quantity:ambiguous_numeric_candidates:..."` | `"quantity:ambiguous_numeric_candidates"` |

**invoice_statement 예상 warning 후보** (RunAll 실행 후 확인):
- `insuranceCode:ocr_source_missing`
- `taxAmount:doc_level_pushdown`
- `totalAmount:doc_level_pushdown`
- `multiline_layout_mapping_applied`
- `quantity:ambiguous_numeric_candidates`

## 5. UI 변경

### DocTypeSummarySection — 거래명세서 sub-table 아래 추가 표시

거래명세서 집계 표 행 아래에 (documentType당 1줄) 다음 정보 표시:
```
[거래명세서] Missing: 보험No(2), 규격(1)   Warn: insuranceCode:ocr_source_missing(3), taxAmount:doc_level_pushdown(2)
```

- **Missing** (적색): 필드 한국어 라벨 + 미추출 샘플 수
- **Warn** (황색): `key:type` 단위 warning 유형 + 발생 횟수
- missing/warning이 없는 documentType은 해당 줄 미표시

### `getInvoiceColLabel(key: string): string` 헬퍼 추가

`TABLE_COLUMN_META` + `CUSTOM_COL_LABELS` 기반으로 field key → 한국어 라벨 변환.

## 6. invoice_statement 확인

- rowCount exact 유지: T-12a 결과 그대로 (OCR 로직 미수정)
- missingTop / warningTop: RunAll 실행 후 UI에서 확인 가능
- tableMeta.valueMappingWarnings 없는 샘플은 skip (에러 없음)
- tableRows가 없는 샘플은 missing 집계 skip (empty tableRows)

## 7. 검증 결과

- typecheck: **passed** (0 errors)
- build: **passed** (/test 44.6 kB)
- OCR 로직 미수정 → 기존 T-10/T-11/T-12a 회귀 없음

## 8. 다음 작업 판단

**field-level summary 완료 → tax_invoice / transaction_statement 샘플 확장 가능**

현재 invoice_statement 집계 UI에서 제공하는 정보:
1. selected / suppressed / not_run / 선택률
2. 필드별 채움 수 (supplierCompany, buyerCompany, rowCount, ...)
3. rows有 / exact / short / over / warn
4. **Missing Top**: 자주 비는 expected field 상위 N개 (T-12b)
5. **Warning Top**: 자주 발생하는 warning type 상위 N개 (T-12b)

후속 후보:
1. `tax_invoice` / `transaction_statement` 실제 샘플 추가 → parser 분기
2. qualityTags × missing field 교차 집계 (ocr_garbled인 샘플의 missing 비율 등)
3. RunAll 결과를 JSON으로 저장해 리포트 자동 생성
