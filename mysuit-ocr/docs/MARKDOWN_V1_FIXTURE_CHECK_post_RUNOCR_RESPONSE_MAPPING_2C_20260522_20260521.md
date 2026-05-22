# MARKDOWN V1 FIXTURE CHECK (post_RUNOCR_RESPONSE_MAPPING_2C_20260522) 20260522

## 1. Task / Phase
- Task: `CODEX_FRONTEND_CLEANUP_2A_MARKDOWN_CONTRACT_FIXTURE_LOCK_NO_PROD_MODIFY`
- Phase: `post_RUNOCR_RESPONSE_MAPPING_2C_20260522`
- Generated at: `2026-05-22T13:44:20`
- Mode: `--check` (read-only — fixtures, manifest, contract, lock reports are NOT modified)

## 2. API
- API URL: `http://127.0.0.1:9099/ocr/extract`
- API source: `existing`
- Fixture root: `tmp\fixtures\markdown_v1`
- Comparison policy: exact string equality, LF-strict, no CRLF normalization

## 3. Cases
| caseId | templateId | actualBytes | expectedBytes | actualLines | expectedLines | endsLF | expCRLF | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| trade_1_1jpg | TPL-31D13CF3 | 922 | 922 | 17 | 17 | Y | N | PASS |
| trade_2_2pdf | TPL-5A8C2374 | 875 | 875 | 16 | 16 | Y | N | PASS |
| trade_3_3pdf | TPL-E4B15A22 | 942 | 942 | 17 | 17 | Y | N | PASS |
| trade_7_7pdf | TPL-3AFD383E | 1004 | 1011 | 17 | 17 | Y | N | FAIL |
| tpl_003_1jpg | TPL-003 | 471 | 471 | 13 | 13 | Y | N | PASS |
| tpl_003_2jpg | TPL-003 | 470 | 470 | 13 | 13 | Y | N | PASS |


## 4. Summary
- overall: `FAIL`
- counts: `{'PASS': 5, 'FAIL': 1}`

## 5. First diffs per failed case

### trade_7_7pdf
- type: `line_diff`
- lineNumber: `9`
- actualLine: `'| 2 | 공급받는자 사업자 번호 (field_2) | 113-85-04425 | 100.0% | OCR |\n'`
- expectedLine: `'| 2 | 공급받는자 사업자 번호 (field_2) | (113-85-04425) | 97.1% | OCR |\n'`
