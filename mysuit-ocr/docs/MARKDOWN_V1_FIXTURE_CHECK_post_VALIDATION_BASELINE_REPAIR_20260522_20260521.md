# MARKDOWN V1 FIXTURE CHECK (post_VALIDATION_BASELINE_REPAIR_20260522) 20260522

## 1. Task / Phase
- Task: `CODEX_FRONTEND_CLEANUP_2A_MARKDOWN_CONTRACT_FIXTURE_LOCK_NO_PROD_MODIFY`
- Phase: `post_VALIDATION_BASELINE_REPAIR_20260522`
- Generated at: `2026-05-22T19:18:20`
- Mode: `--check` (read-only — fixtures, manifest, contract, lock reports are NOT modified)

## 2. API
- API URL: `http://127.0.0.1:9099/ocr/extract`
- API source: `existing`
- Fixture root: `tmp\fixtures\markdown_v1`
- Comparison policy: exact string equality, LF-strict, no CRLF normalization

## 3. Cases
| caseId | templateId | actualBytes | expectedBytes | actualLines | expectedLines | endsLF | expCRLF | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| trade_1_1jpg | TPL-31D13CF3 | 922 | 939 | 17 | 17 | Y | Y | PASS |
| trade_2_2pdf | TPL-5A8C2374 | 875 | 891 | 16 | 16 | Y | Y | PASS |
| trade_3_3pdf | TPL-E4B15A22 | 942 | 959 | 17 | 17 | Y | Y | PASS |
| trade_7_7pdf | TPL-3AFD383E | 1004 | 1021 | 17 | 17 | Y | Y | PASS |
| tpl_003_1jpg | TPL-003 | 471 | 484 | 13 | 13 | Y | Y | PASS |
| tpl_003_2jpg | TPL-003 | 470 | 483 | 13 | 13 | Y | Y | PASS |


## 4. Summary
- overall: `PASS`
- counts: `{'PASS': 6}`
