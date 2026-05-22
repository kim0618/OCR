# CLEAN JSON V1 FIXTURE CHECK (pre_extraction_20260521) 20260521

## 1. Task / Phase
- Task: `CODEX_CLEAN_JSON_V1_FIXTURE_LOCK_NO_PROD_MODIFY`
- Phase: `pre_extraction_20260521`
- Generated at: `2026-05-21T14:25:08`
- Mode: `--check` (read-only — fixtures and manifest are NOT modified)

## 2. API
- API URL: `http://127.0.0.1:9137/ocr/extract`
- API source: `started_fallback_port`
- Fixture root: `tmp\fixtures\clean_json_v1`

## 3. Invoice cases
| caseId | templateId | rowCountExpected | rowCountActual | rowIndexExpected | rowIndexActual | diffCount | status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| trade_1_1jpg | TPL-31D13CF3 | 28 | 28 | excluded | excluded | 0 | PASS |
| trade_2_2pdf | TPL-5A8C2374 | 13 | 13 | included | included | 0 | PASS |
| trade_3_3pdf | TPL-E4B15A22 | 1 | 1 | included | included | 0 | PASS |
| trade_4_4pdf | TPL-FD07531C | 1 | 1 | excluded | excluded | 0 | PASS |
| trade_5_5pdf | TPL-B8936EDE | 6 | 6 | excluded | excluded | 0 | PASS |
| trade_6_6pdf | TPL-95328E52 | 6 | 6 | included | included | 0 | PASS |
| trade_7_7pdf | TPL-3AFD383E | 1 | 1 | excluded | excluded | 0 | PASS |


## 4. Receipt cases
| caseId | templateId | infoCount | tableCount | diffCount | status |
| --- | --- | --- | --- | --- | --- |
| tpl_003_1jpg | TPL-003 | 6 | 0 | 0 | PASS |
| tpl_003_2jpg | TPL-003 | 6 | 0 | 0 | PASS |


## 5. Summary
- overall: `PASS`
- counts: `{'PASS': 9}`
