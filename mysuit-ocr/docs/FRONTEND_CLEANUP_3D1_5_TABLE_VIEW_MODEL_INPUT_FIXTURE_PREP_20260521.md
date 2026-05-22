# FRONTEND CLEANUP 3D1.5 TABLE VIEW MODEL INPUT FIXTURE PREP 20260521

## 1. 사용 도구와 모델
- 사용 도구: Codex
- 사용 모델: Codex
- 작업명: `CODEX_FRONTEND_CLEANUP_3D1_5_TABLE_VIEW_MODEL_INPUT_FIXTURE_PREP_NO_PROD_MODIFY`

## 2. 코드 수정 여부
- 운영 코드 수정 없음.
- helper 생성 없음.
- 기존 trade_1~trade_7 output fixture 내용 변경 없음: `PASS`

## 3. 생성/수정 파일
- `tmp/codex_table_view_model_input_fixture_prep.py`
- `tmp/fixtures/table_view_model_v1/inputs/*.input.json`
- `tmp/fixtures/table_view_model_v1/synthetic/synthetic_empty_rows.view_model.json`
- `tmp/fixtures/table_view_model_v1/manifest.json`
- `docs/FRONTEND_CLEANUP_3D1_5_TABLE_VIEW_MODEL_INPUT_FIXTURE_PREP_20260521.md`
- `docs/FRONTEND_CLEANUP_3D1_5_TABLE_VIEW_MODEL_INPUT_FIXTURE_PREP_20260521.json`

## 4. Raw Input Fixture 결과
- API URL: `http://127.0.0.1:9099/ocr/extract`
- API source: `existing_9099`
| caseId | inputFixture | rows | displayCols | rowIndex | status |
| --- | --- | --- | --- | --- | --- |
| trade_1_1jpg | inputs/trade_1_1jpg.input.json | 28 | 7 | excluded | PASS |
| trade_2_2pdf | inputs/trade_2_2pdf.input.json | 13 | 7 | included | PASS |
| trade_3_3pdf | inputs/trade_3_3pdf.input.json | 1 | 7 | included | PASS |
| trade_4_4pdf | inputs/trade_4_4pdf.input.json | 1 | 7 | excluded | PASS |
| trade_5_5pdf | inputs/trade_5_5pdf.input.json | 6 | 5 | excluded | PASS |
| trade_6_6pdf | inputs/trade_6_6pdf.input.json | 6 | 6 | included | PASS |
| trade_7_7pdf | inputs/trade_7_7pdf.input.json | 1 | 4 | excluded | PASS |

## 5. Synthetic Empty Rows Fixture 결과
- input: `inputs/synthetic_empty_rows.input.json`
- output: `synthetic/synthetic_empty_rows.view_model.json`
- status: `PASS`
- rows: `0`
- columns retained: `2`

## 6. Manifest 보강 결과
- `inputFixturePath` 추가: trade_1~trade_7 + synthetic
- synthetic case 추가: `synthetic_empty_rows`
- trade_3 grep marker 추가: `LOCKED_CURRENT_BEHAVIOR`

## 7. 거래_3 LOCKED_CURRENT_BEHAVIOR 기록
- policy: `LOCKED_CURRENT_BEHAVIOR`
- extraColumns: `['insuranceCode', 'amount']`
- insuranceCode: `669700020`
- amount: `301,320`

## 8. Input/Output Consistency Validation 결과
- overall: `PASS`
- synthetic: `PASS`
- forbidden field check: `PASS`
- review_log restored: `True`

## 9. Typecheck/Build 결과
| command | status | exitCode | seconds | known stderr noise |
| --- | --- | --- | --- | --- |
| npm.cmd run typecheck | PASS | 0 | 1.905 | False |
| npm.cmd run build | PASS | 0 | 18.078 | True |

## 10. 다음 작업 제안
1. input fixture를 읽는다.
2. `buildStructuredTableViewModel(input)`을 실행한다.
3. expected output fixture를 읽는다.
4. deep equality로 비교한다.
5. trade_1~trade_7 + synthetic_empty_rows 총 8개 PASS를 3D-2 gate로 둔다.

3D-2 성공 기준: table view model fixture 8/8 PASS, Clean JSON JS fixture runner 9/9 PASS, Markdown fixture check 6/6 PASS, typecheck/build PASS.
