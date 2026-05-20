# CODEX_T28_PERF3_TABLE_CROP_DEFER_PRE_APPLY_VALIDATION

- 사용 도구: Codex
- 사용 모델: Codex
- 운영 코드 수정: 없음
- repo dirty before work: True
- API URL: `http://127.0.0.1:9099/ocr/extract`
- 검증 스크립트: `D:\Free_Vue\OCR\tmp\codex_t28_perf3_table_crop_defer_pre_apply_validation.py`
- 최종 판정: **PASS**

## Baseline / Virtual Defer Results

| Template | File | processing_time | expected | document_fields rows | Clean JSON rows | Virtual deferred rows | est saved | est after | risk |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| 거래_1 | 1.jpg | 82.9 | 28 | 28 | 28 | 28 | 33.0 | 49.9 | low |
| 거래_2 | 2.pdf | 71.96 | 13 | 13 | 13 | 13 | 10.042 | 61.918 | low |
| 거래_3 | 3.pdf | 29.62 | 1 | 1 | 1 | 1 | 0.796 | 28.824 | low |
| 거래_4 | 4.pdf | 25.8 | 1 | 1 | 1 | 1 | 0.276 | 25.524 | low |
| 거래_5 | 5.pdf | 24.94 | 6 | 6 | 6 | 6 | 3.69 | 21.25 | low |
| 거래_6 | 6.pdf | 17.64 | 6 | 6 | 6 | 6 | 2.532 | 15.108 | low |
| 거래_7 | 7.pdf | 15.19 | 1 | 1 | 1 | 1 | 0.657 | 14.533 | low |

## table_data 소비처 정적 분석

### backend
- tableCropOcrCall: ocr-server/main.py:2118 calls _ocr_table_region(img, ocr, region) for field_type == 'table'
- tableDataCreation: ocr-server/main.py:2134 stores fields[].table_data and table field value=json.dumps(table_rows)
- documentFieldsTableRows: ocr-server/main.py:2631 calls extract_invoice_statement_fields(...); invoice_statement.py returns document_fields.tableRows
- orderingRisk: Current code runs table crop OCR before invoice_statement parser creates document_fields.tableRows, so defer requires moving/guarding the table branch or a second pass.
### frontend
- preview: OcrResultPanel.tsx:757-778 builds docTableRows/docTableDisplayCols from result.document_fields.tableRows; preview table at ~1123 prefers docTableRows.
- cleanJson: OcrResultPanel.tsx:866-871 uses docTableRows first, f.tableRows second, f.table_data third.
- custom: OcrResultPanel.tsx:1432-1524 uses docTableRows first; parseTableField(field.value) is fallback only.
- validation: OcrResultPanel.tsx:1654-1733 uses docTableRows first; field.value parse is fallback/row label only.
- history: historyStore.ts and DetailHistoryView.tsx persist/display document_fields.tableRows; no required table_data dependency found.
- testWorkspace: TestWorkspace uses document_fields.tableRows/tableMeta metrics; table_data not required for invoice table display.
- rawJson: Raw JSON will lose table_data debug detail unless an opt-in debug/includeTableDataOcr path keeps old behavior.

## 가상 table_data 제거 검증

- document_fields.tableRows expected rowCount 유지: 7/7
- Clean JSON rows 유지: 7/7
- table_data 제거/summary value 가상 응답 rows 유지: 7/7
- 총 processing_time: 268.05s
- 예상 총 절감: 50.993s
- 샘플 평균 예상 절감: 7.285s

## 적용 가능 조건
- Apply only on template RunOCR path.
- Apply only when doc_type/documentType is invoice_statement.
- Apply only when document_fields.tableRows exists and len(tableRows) > 0.
- Set table field value to a compact summary such as '표 데이터 (N행)'.
- Omit or empty table_data in the default response.
- Keep existing _ocr_table_region fallback when tableRows is missing/empty or when includeTableDataOcr/debug flag is requested.

## Fallback Pseudo-code

```python
if is_template_run and doc_type == 'invoice_statement' and document_fields.get('tableRows'):
    skip table crop OCR
    table_field['value'] = f"표 데이터 ({len(tableRows)}행)"
    table_field.pop('table_data', None)
    table_field['tableOcrDebug'] = {... tableCropOcrSkipped: true ...}
else:
    run existing _ocr_table_region fallback
```

## 위험 요소
- Raw JSON/debug consumers that expect fields[].table_data will see reduced debug detail by default.
- Any external integration reading table_1.value as stringified JSON would need migration or an opt-in legacy flag.
- The backend currently creates document_fields after table crop OCR, so implementation must reorder or defer table field materialization carefully.
- New invoice_statement templates without document_fields.tableRows must keep the existing fallback.
- History/TestWorkspace should continue to persist document_fields.tableRows; do not remove that structure.

## 다음 프롬프트 필수 조건
- No behavior change for non-invoice_statement and unstructured OCR paths.
- Fallback to _ocr_table_region when document_fields.tableRows is absent or empty.
- Optional includeTableDataOcr/debug flag for Raw JSON compatibility.
- Preserve document_fields.tableRows/tableMeta and processing_time.
- Run 거래_1~거래_7 regression after implementation and compare expected rowCount.
