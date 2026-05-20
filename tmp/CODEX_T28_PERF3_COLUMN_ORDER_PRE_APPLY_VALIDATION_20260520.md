# CODEX_T28_PERF3_COLUMN_ORDER_PRE_APPLY_VALIDATION

- 사용 도구: Codex
- 사용 모델: Codex
- 운영 코드 수정: 없음
- repo dirty before work: True
- API URL: `http://127.0.0.1:9099/ocr/extract`
- 검증 스크립트: `D:\Free_Vue\OCR\tmp\codex_t28_perf3_column_order_pre_apply_validation.py`
- 최종 판정: **PASS**

## Column Order Source
- Preview: OcrResultPanel.tsx uses docTableDisplayCols = buildInvoicePreviewCols(docTableMeta, docTableRows), then renders headers/cells in that order.
- CleanJSON: Clean JSON uses cleanTableRowsFromObjects(docTableRows, docTableDisplayCols), so object insertion order follows docTableDisplayCols, not tableRows key order.
- Custom: Custom table branch uses docTableDisplayCols for colgroup, header, cells, and textarea edit columns.
- Validation: Validation table branch uses docTableDisplayCols for colgroup, header, and cells.
- TestWorkspace: TestWorkspace has an equivalent getDisplayTableColumns path using tableMeta / expected columns and tableRows.
- table_data: table_data is only a fallback when document_fields.tableRows/docTableDisplayCols is not available; it is not the normal column order source for invoice_statement RunOCR Preview.
- objectKeyOrder: Current structured path does not rely on document_fields.tableRows object key order for display or Clean JSON; it indexes each row by ordered column keys.
- priority: buildInvoicePreviewCols priority is tableMeta.expectedColumnKeys, then tableMeta.columns, then INVOICE_TABLE_COL_PRIORITY with hasValue and dedup filters.

## 거래_1~거래_7 Column Order 비교

| Template | File | rows | beforeColumnKeys | afterColumnKeys | same | Clean JSON same |
|---|---|---:|---|---|:---:|:---:|
| 거래_1 | 1.jpg | 28/28 | `itemName, spec, manufacturingNo, expiryDate, quantity, unitPrice, amount` | `itemName, spec, manufacturingNo, expiryDate, quantity, unitPrice, amount` | True | True |
| 거래_2 | 2.pdf | 13/13 | `itemCode, itemName, quantity, consumerUnitPrice, supplyUnitPrice, supplyAmount` | `itemCode, itemName, quantity, consumerUnitPrice, supplyUnitPrice, supplyAmount` | True | True |
| 거래_3 | 3.pdf | 1/1 | `itemName, quantity, unitPrice, manufacturer` | `itemName, quantity, unitPrice, manufacturer` | True | True |
| 거래_4 | 4.pdf | 1/1 | `itemName, lotNo, unit, quantity, unitPrice, supplyAmount, taxAmount, totalAmount` | `itemName, lotNo, unit, quantity, unitPrice, supplyAmount, taxAmount, totalAmount` | True | True |
| 거래_5 | 5.pdf | 6/6 | `itemName, itemCode, quantity, unitPrice, amount` | `itemName, itemCode, quantity, unitPrice, amount` | True | True |
| 거래_6 | 6.pdf | 6/6 | `itemCode, itemName, quantity, expiryDate` | `itemCode, itemName, quantity, expiryDate` | True | True |
| 거래_7 | 7.pdf | 1/1 | `itemName, unit, quantity` | `itemName, unit, quantity` | True | True |

## PASS Conditions
- rowCount7of7: True
- columnOrderSame7of7: True
- cleanJsonColumnOrderSame7of7: True
- cleanJsonRowsMaintained7of7: True
- noTableDataColumnOrderDependency: True
- noObjectKeyOrderDependency: True

## 영향 분석
- Preview: docTableDisplayCols 순서 그대로 유지.
- Clean JSON: docTableDisplayCols 기반 ordered object 생성으로 순서 유지.
- Custom: docTableDisplayCols 기반 header/cell/edit column 순서 유지.
- Validation: docTableDisplayCols 기반 header/cell 순서 유지.
- table_data: document_fields.tableRows가 있는 invoice_statement RunOCR 기본 경로에서는 컬럼 순서 source가 아님.

## 운영 반영 필수 조건
- Limit optimization to Template RunOCR + invoice_statement only.
- Do not apply to unstructured OCR, unstructured templates, or receipt paths.
- Skip table crop OCR only when document_fields.tableRows exists and len(tableRows) > 0.
- Run existing _ocr_table_region fallback when tableRows is missing or empty.
- Use buildInvoicePreviewCols/docTableDisplayCols or the same ordering rules for Preview, Clean JSON, Custom, and Validation.
- Build Clean JSON rows as ordered objects from column keys, never from raw tableRows object key order.
- Use a compact table field value such as '표 데이터 (N행)'.
- Omit or empty table_data in the default response; keep fallback/debug option if Raw JSON compatibility is needed.

## Pseudo-code
```python
if is_template_run and doc_type == 'invoice_statement' and document_fields.get('tableRows'):
    table_rows = document_fields['tableRows']
    skip _ocr_table_region
    table_field['value'] = f"표 데이터 ({len(table_rows)}행)"
    table_field.pop('table_data', None)
    column_keys = buildInvoicePreviewCols(tableMeta, table_rows)  # frontend/helper-equivalent order
else:
    run existing _ocr_table_region fallback
```

## 위험 요소
- If future UI code bypasses docTableDisplayCols and iterates Object.keys(tableRows[0]), column order can drift.
- Raw JSON consumers using fields[].table_data may need a debug/legacy option.
- Backend implementation must ensure document_fields.tableRows is available before deciding to skip table crop OCR.
- New templates without tableMeta.expectedColumnKeys/tableMeta.columns should still use canonical priority fallback.

## 다음 프롬프트 필수 조건
- Preserve buildInvoicePreviewCols/docTableDisplayCols as the single UI column order source.
- Do not derive Clean JSON table order from document_fields.tableRows object key order.
- Add fallback to existing table crop OCR when document_fields.tableRows is absent/empty.
- Keep scope to invoice_statement template RunOCR only.
- After implementation, rerun 거래_1~거래_7 and compare rowCount plus before/after column keys.
