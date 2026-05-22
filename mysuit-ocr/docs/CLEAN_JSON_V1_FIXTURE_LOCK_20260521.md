# CLEAN JSON V1 FIXTURE LOCK 20260521

## 1. 사용 도구와 모델
- 사용 도구: Codex
- 사용 모델: Codex
- 작업명: `CODEX_CLEAN_JSON_V1_FIXTURE_LOCK_NO_PROD_MODIFY`
- 생성 시각: `2026-05-22T11:12:09`

## 2. 운영 코드 수정 없음 확인
- 운영 frontend/backend/templates/manifest/GT는 수정하지 않았다.
- `OcrResultPanel.tsx` 리팩토링 및 `cleanJsonBuilder.ts` 생성은 하지 않았다.
- 생성물은 tmp 스크립트, tmp fixture, docs 리포트뿐이다.
- repo dirty 상태: `DIRTY`

```text
 M src/components/upload/OcrResultPanel.tsx
 M src/lib/invoiceTableDisplay.ts
 M ../ocr-server/data/review_log.jsonl
 M ../ocr-server/requirements.txt
?? docs/CLEAN_JSON_CONTRACT_20260521.json
?? docs/CLEAN_JSON_CONTRACT_20260521.md
?? docs/CLEAN_JSON_V1_FIXTURE_CHECK_post_extraction_20260521_20260521.json
?? docs/CLEAN_JSON_V1_FIXTURE_CHECK_post_extraction_20260521_20260521.md
?? docs/CLEAN_JSON_V1_FIXTURE_CHECK_pre_extraction_20260521_20260521.json
?? docs/CLEAN_JSON_V1_FIXTURE_CHECK_pre_extraction_20260521_20260521.md
?? docs/CLEAN_JSON_V1_FIXTURE_LOCK_20260521.json
?? docs/CLEAN_JSON_V1_FIXTURE_LOCK_20260521.md
?? docs/FRONTEND_CLEANUP_1B_JS_CLEAN_JSON_FIXTURE_RUNNER_20260521.json
?? docs/FRONTEND_CLEANUP_1B_JS_CLEAN_JSON_FIXTURE_RUNNER_20260521.md
?? docs/FRONTEND_CLEANUP_1_CLEAN_JSON_BUILDER_EXTRACT_20260521.json
?? docs/FRONTEND_CLEANUP_1_CLEAN_JSON_BUILDER_EXTRACT_20260521.md
?? docs/FRONTEND_CLEANUP_2B_MARKDOWN_BUILDER_EXTRACT_20260521.json
?? docs/FRONTEND_CLEANUP_2B_MARKDOWN_BUILDER_EXTRACT_20260521.md
?? docs/FRONTEND_CLEANUP_3A_PREVIEW_TABLE_BUILDER_PRECHECK_20260521.json
?? docs/FRONTEND_CLEANUP_3A_PREVIEW_TABLE_BUILDER_PRECHECK_20260521.md
?? docs/FRONTEND_CLEANUP_3C_TABLE_RENDERER_PRECHECK_20260521.json
?? docs/FRONTEND_CLEANUP_3C_TABLE_RENDERER_PRECHECK_20260521.md
?? docs/FRONTEND_CLEANUP_3D0_2_TABLE_VIEW_MODEL_CONTRACT_TRIM_PRECHECK_20260521.json
?? docs/FRONTEND_CLEANUP_3D0_2_TABLE_VIEW_MODEL_CONTRACT_TRIM_PRECHECK_20260521.md
?? docs/FRONTEND_CLEANUP_3D0_TABLE_VIEW_MODEL_CONTRACT_PRECHECK_20260521.json
?? docs/FRONTEND_CLEANUP_3D0_TABLE_VIEW_MODEL_CONTRACT_PRECHECK_20260521.md
?? docs/FRONTEND_CLEANUP_3D1_5_TABLE_VIEW_MODEL_INPUT_FIXTURE_PREP_20260521.json
?? docs/FRONTEND_CLEANUP_3D1_5_TABLE_VIEW_MODEL_INPUT_FIXTURE_PREP_20260521.md
?? docs/FRONTEND_CLEANUP_3D1_TABLE_VIEW_MODEL_FIXTURE_LOCK_20260521.json
?? docs/FRONTEND_CLEANUP_3D1_TABLE_VIEW_MODEL_FIXTURE_LOCK_20260521.md
?? docs/FRONTEND_CLEANUP_3D2_RUNNER_RESULT_20260521.json
?? docs/FRONTEND_CLEANUP_3D2_STRUCTURED_TABLE_VIEW_MODEL_HELPER_20260521.json
?? docs/FRONTEND_CLEANUP_3D2_STRUCTURED_TABLE_VIEW_MODEL_HELPER_20260521.md
?? docs/FRONTEND_CLEANUP_3D3_APPLY_STRUCTURED_TABLE_VIEW_MODEL_PREVIEW_ONLY_20260521.json
?? docs/FRONTEND_CLEANUP_3D3_APPLY_STRUCTURED_TABLE_VIEW_MODEL_PREVIEW_ONLY_20260521.md
?? docs/FRONTEND_CLEANUP_3D3_SMOKE_COLUMN_POLICY_PRECHECK_20260521.json
?? docs/FRONTEND_CLEANUP_3D3_SMOKE_COLUMN_POLICY_PRECHECK_20260521.md
?? docs/FRONTEND_CLEANUP_OCR_RESULT_PANEL_CYCLE_1_CLOSEOUT_20260521.json
?? docs/FRONTEND_CLEANUP_OCR_RESULT_PANEL_CYCLE_1_CLOSEOUT_20260521.md
?? docs/FRONTEND_FILE_INVENTORY_USAGE_PRECHECK_20260521.json
?? docs/FRONTEND_FILE_INVENTORY_USAGE_PRECHECK_20260521.md
?? docs/FRONTEND_FILE_INVENTORY_USAGE_PRECHECK_TABLE_20260521.csv
?? docs/FRONTEND_INVOICE_TABLE_DISPLAY_POLICY_FIX_PRECHECK_20260522.json
?? docs/FRONTEND_INVOICE_TABLE_DISPLAY_POLICY_FIX_PRECHECK_20260522.md
?? docs/MARKDOWN_V1_CONTRACT_20260521.json
?? docs/MARKDOWN_V1_CONTRACT_20260521.md
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_3D3_20260521_20260521.json
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_3D3_20260521_20260521.md
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_extraction_20260521_20260521.json
?? docs/MARKDOWN_V1_FIXTURE_CHECK_post_extraction_20260521_20260521.md
?? docs/MARKDOWN_V1_FIXTURE_CHECK_pre_extraction_20260521_20260521.json
?? docs/MARKDOWN_V1_FIXTURE_CHECK_pre_extraction_20260521_20260521.md
?? docs/MARKDOWN_V1_FIXTURE_CHECK_regression_3D2_20260521_20260521.json
?? docs/MARKDOWN_V1_FIXTURE_CHECK_regression_3D2_20260521_20260521.md
?? docs/MARKDOWN_V1_FIXTURE_COVERAGE_EOL_PRECHECK_20260521.json
?? docs/MARKDOWN_V1_FIXTURE_COVERAGE_EOL_PRECHECK_20260521.md
?? docs/MARKDOWN_V1_FIXTURE_LOCK_20260521.json
?? docs/MARKDOWN_V1_FIXTURE_LOCK_20260521.md
?? src/lib/cleanJsonBuilder.ts
?? src/lib/markdownReportBuilder.ts
?? src/lib/ocrResultFormatters.ts
?? src/lib/structuredTableViewModel.ts
?? tmp/
?? ../ocr-server/requirements-aws.txt
```

## 3. 참조한 Contract 문서
- `docs/CLEAN_JSON_CONTRACT_20260521.md`
- `docs/CLEAN_JSON_CONTRACT_20260521.json`

## 4. Fixture 저장 위치
- fixture root: `tmp/fixtures/clean_json_v1`
- manifest: `tmp/fixtures/clean_json_v1/manifest.json`
- docs report: `docs/CLEAN_JSON_V1_FIXTURE_LOCK_20260521.md`
- docs json: `docs/CLEAN_JSON_V1_FIXTURE_LOCK_20260521.json`

## 5. API 실행 조건
- API URL: `http://127.0.0.1:9099/ocr/extract`
- API source: `existing`
- RunOCR와 같은 FormData 계열: `file`, `template_id`, `model_id`, `regions`, `documentType`
- 운영 코드는 수정하지 않았다.

## 6. 거래명세서 Fixture 결과
| caseId | templateId | rows | rowIndex | rowKeys | processing_time | wallClockSeconds | status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| trade_1_1jpg | TPL-31D13CF3 | 28 | excluded | itemName, spec, manufacturingNo, expiryDate, quantity, unitPrice, amount | 52.2 | 52.384 | PASS |
| trade_2_2pdf | TPL-5A8C2374 | 13 | included | rowIndex, itemCode, itemName, quantity, consumerUnitPrice, supplyUnitPrice, supplyAmount | 39.99 | 40.14 | PASS |
| trade_3_3pdf | TPL-E4B15A22 | 1 | included | rowIndex, insuranceCode, itemName, quantity, unitPrice, amount, manufacturer | 23.47 | 23.512 | PASS |
| trade_4_4pdf | TPL-FD07531C | 1 | excluded | itemName, lotNo, unit, quantity, unitPrice, supplyAmount, taxAmount | 22.47 | 22.554 | WARN |
| trade_5_5pdf | TPL-B8936EDE | 6 | excluded | itemName, itemCode, quantity, unitPrice, amount | 25.5 | 25.653 | PASS |
| trade_6_6pdf | TPL-95328E52 | 6 | included | rowIndex, itemCode, itemName, quantity, lotNo, expiryDate | 16.17 | 16.232 | WARN |
| trade_7_7pdf | TPL-3AFD383E | 1 | excluded | itemName, serialLotComposite, unit, quantity | 17.62 | 17.667 | WARN |


## 7. 영수증 Fixture 결과
| caseId | templateId | infoCount | tableCount | processing_time | wallClockSeconds | status |
| --- | --- | --- | --- | --- | --- | --- |
| tpl_003_1jpg | TPL-003 | 6 | 0 | 30.67 | 30.696 | PASS |
| tpl_003_2jpg | TPL-003 | 6 | 0 | 41.07 | 41.15 | PASS |


## 8. rowIndex / Column Order 검증
- 거래_1/4/5/7은 fixture rows에서 `rowIndex` 제외를 검증했다.
- 거래_2/3/6은 fixture rows에서 `rowIndex` 유지를 검증했다.
- 구조화 거래명세서 rows는 `docTableDisplayCols` 순서로 ordered object를 생성했다.
- fixture 검증은 저장 후 다시 읽어 row keys와 rowCount를 확인했다.

## 9. 거래_3 Locked Current Behavior
- 거래_3의 `insuranceCode`, `amount`는 rowIndex 정책과 별도 이슈다.
- 현재 Clean JSON v1 출력에 존재하면 fixture에 그대로 저장하고 `unresolved but locked current behavior`로 기록한다.
- helper 분리 작업에서는 이 동작을 바꾸면 안 된다.

## 10. Before / After Deep Equality 방법
1. 이번 fixture를 helper 분리 전 golden output으로 사용한다.
2. FRONTEND-CLEANUP-1 이후 같은 API/input/template으로 Clean JSON을 재생성한다.
3. `tmp/fixtures/clean_json_v1` 아래 fixture와 deep equality 비교한다.
4. key order까지 검증하려면 ordered stringify 결과를 비교한다.
5. 비교 실패 시 diff path를 출력한다.
6. Preview column order와 Clean JSON row keys 일치도 별도 검사한다.

## 11. Known Stderr Noise
- `ISSUE-FRONTEND-BUILD-LOG-1`
- `npm run build`는 exit code 0이지만 stderr에 `ESLint: nextVitals is not iterable` 메시지가 기록된다.
- cleanup 작업 실패 원인과 구분해야 한다.

## 12. Typecheck / Build
| command | status | exit | seconds |
| --- | --- | --- | --- |
| npm run typecheck | PASS | 0 | 2.092 |
| npm run build | PASS | 0 | 17.03 |

### build stderr tail
```text
 ⨯ ESLint: nextVitals is not iterable

```

## 13. 최종 판정
- fixture lock status: `WARN`
- status counts: `{'PASS': 6, 'WARN': 3}`

## 14. 다음 작업 제안
1. FRONTEND-CLEANUP-1에서 `buildCleanJsonResult` helper를 분리한다.
2. helper 분리 후 이번 fixture와 deep equality를 비교한다.
3. 거래_3 `insuranceCode`/`amount` 정책은 별도 프롬프트로 다룬다.
4. build stderr known noise는 cleanup 실패와 분리해서 추적한다.
