# FRONTEND CLEANUP 3D1 TABLE VIEW MODEL FIXTURE LOCK 20260521

## 1. 사용 도구와 모델
- 사용 도구: Codex
- 사용 모델: Codex
- 작업명: `CODEX_FRONTEND_CLEANUP_3D1_TABLE_VIEW_MODEL_FIXTURE_LOCK_NO_PROD_MODIFY`

## 2. 코드 수정 여부
- 운영 코드 수정 없음.
- helper 생성 없음.
- 금지 파일(`OcrResultPanel.tsx`, `cleanJsonBuilder.ts`, `markdownReportBuilder.ts`, `ocrResultFormatters.ts`, `invoiceTableDisplay.ts`, `TestWorkspace.tsx`) 수정 없음.

## 3. 생성 파일
- `tmp/codex_table_view_model_fixture_lock.py`
- `tmp/fixtures/table_view_model_v1/manifest.json`
- `tmp/fixtures/table_view_model_v1/invoice_statement/*.view_model.json`
- `docs/FRONTEND_CLEANUP_3D1_TABLE_VIEW_MODEL_FIXTURE_LOCK_20260521.md`
- `docs/FRONTEND_CLEANUP_3D1_TABLE_VIEW_MODEL_FIXTURE_LOCK_20260521.json`

## 4. Fixture 대상
- 대상 데이터셋: `public/data/testsets/invoice_statement`
- API URL: `http://127.0.0.1:9099/ocr/extract`
- API source: `existing_9099`

## 5. Fixture Contract 준수 결과
- 전체 상태: `PASS`
- disk validation: `PASS`
- fixture count: `7/7`
- excluded field validation: PASS when each case `excludedFieldCount == 0`
- fixture body는 trimmed `StructuredTableViewModel`만 포함.

## 6. rowCount / columnCount 결과
| caseId | templateId | actualRows | expectedRows | columnCount | rowIndexActual | rowIndexExpected | status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| trade_1_1jpg | TPL-31D13CF3 | 28 | 28 | 7 | excluded | excluded | PASS |
| trade_2_2pdf | TPL-5A8C2374 | 13 | 13 | 7 | included | included | PASS |
| trade_3_3pdf | TPL-E4B15A22 | 1 | 1 | 7 | included | included | PASS |
| trade_4_4pdf | TPL-FD07531C | 1 | 1 | 7 | excluded | excluded | PASS |
| trade_5_5pdf | TPL-B8936EDE | 6 | 6 | 5 | excluded | excluded | PASS |
| trade_6_6pdf | TPL-95328E52 | 6 | 6 | 6 | included | included | PASS |
| trade_7_7pdf | TPL-3AFD383E | 1 | 1 | 4 | excluded | excluded | PASS |

## 7. rowIndex 정책 결과
- included expected: 거래_2, 거래_3, 거래_6
- excluded expected: 거래_1, 거래_4, 거래_5, 거래_7
- 결과: `PASS`

## 8. 거래_3 locked behavior 기록
- insuranceCode column included: `True`
- insuranceCode value: `669700020`
- amount column included: `True`
- amount value: `301,320`

## 9. typecheck/build 결과
| command | status | exitCode | seconds | known stderr noise |
| --- | --- | --- | --- | --- |
| npm.cmd run typecheck | PASS | 0 | 1.715 | False |
| npm.cmd run build | PASS | 0 | 16.371 | True |

## 10. 다음 작업 제안
- 3D-2에서 `buildStructuredTableViewModel` helper direct output과 이 fixture를 deep equality로 비교한다.
- Clean JSON JS fixture runner 9/9 PASS, Markdown fixture check 6/6 PASS, typecheck/build PASS를 같은 3D-2 gate로 둔다.
- OcrResultPanel 적용은 helper direct runner가 7/7 PASS한 뒤 별도 단계로 두는 것을 추천한다.
