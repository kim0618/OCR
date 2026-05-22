# FRONTEND CLEANUP 1B JS CLEAN JSON FIXTURE RUNNER 20260521

## 1. 사용 도구와 모델
- 사용 도구: Codex
- 사용 모델: Codex
- 작업명: `CODEX_FRONTEND_CLEANUP_1B_JS_CLEAN_JSON_FIXTURE_RUNNER`
- 생성 시각: `2026-05-22T07:25:53.194Z`

## 2. 코드 수정 여부
- 운영 기능 코드는 수정하지 않았다.
- Clean JSON 출력 로직, OcrResultPanel, invoiceTableDisplay, backend/parser/templates/manifest/GT, fixture output JSON은 수정하지 않았다.
- 생성/갱신한 것은 JS fixture runner와 docs 리포트뿐이다.

## 3. Runner 구현 방식
- 선택 방식: `B-lite / fixture-derived in-memory input`
- 이유: No extra dependency or API rerun is required; locked output fixtures are read-only, converted to the current helper input contract in memory, then compared by deep equality and ordered stringify.
- import 방식: typescript.transpileModule to transient tmp/.clean_json_fixture_runner_build/*.cjs, then require()
- fixture manifest: `tmp\fixtures\clean_json_v1\manifest.json`
- fixture 파일은 읽기 전용으로 사용했다.

## 4. JS Fixture Deep Equality 결과
- overall: `PASS`
- total cases: 9
- pass: 9
- fail: 0
- total diffs: 0

| caseId | status | diffs | rowIndex | rowKeys | fixture |
| --- | --- | --- | --- | --- | --- |
| trade_1_1jpg | PASS | 0 | excluded | itemName, spec, manufacturingNo, expiryDate, quantity, unitPrice, amount | invoice_statement/trade_1_1jpg.clean.json |
| trade_2_2pdf | PASS | 0 | included | rowIndex, itemCode, itemName, quantity, consumerUnitPrice, supplyUnitPrice, supplyAmount | invoice_statement/trade_2_2pdf.clean.json |
| trade_3_3pdf | PASS | 0 | included | rowIndex, insuranceCode, itemName, quantity, unitPrice, amount, manufacturer | invoice_statement/trade_3_3pdf.clean.json |
| trade_4_4pdf | PASS | 0 | excluded | itemName, lotNo, unit, quantity, unitPrice, supplyAmount, taxAmount | invoice_statement/trade_4_4pdf.clean.json |
| trade_5_5pdf | PASS | 0 | excluded | itemName, itemCode, quantity, unitPrice, amount | invoice_statement/trade_5_5pdf.clean.json |
| trade_6_6pdf | PASS | 0 | included | rowIndex, itemCode, itemName, quantity, lotNo, expiryDate | invoice_statement/trade_6_6pdf.clean.json |
| trade_7_7pdf | PASS | 0 | excluded | itemName, serialLotComposite, unit, quantity | invoice_statement/trade_7_7pdf.clean.json |
| tpl_003_1jpg | PASS | 0 |  |  | receipt/tpl_003_1jpg.clean.json |
| tpl_003_2jpg | PASS | 0 |  |  | receipt/tpl_003_2jpg.clean.json |

## 5. rowIndex / 거래_3 / 영수증 확인
- 거래_1/4/5/7 rowIndex 제외: PASS
- 거래_2/3/6 rowIndex 유지: PASS
- 거래_3 insuranceCode/amount locked behavior: PASS
- 영수증 TPL-003 1.jpg/2.jpg field-only shape: PASS

## 6. Helper 순수성 재확인
- React hook import 없음: PASS
- DOM/window/localStorage/network 접근 없음: PASS
- Raw JSON/copy/export/UI state 책임 없음: PASS
- 입력 mutation 없음: PASS

## 7. Typecheck / Build
| command | status | exit | seconds |
| --- | --- | --- | --- |
| npm run typecheck | PASS | 0 | 1.869 |
| npm run build | PASS | 0 | 16.114 |

Known stderr noise:
- ISSUE-FRONTEND-BUILD-LOG-1: `ESLint: nextVitals is not iterable` can appear with build exit code 0.

## 8. 남은 리스크
- 이 runner는 helper를 직접 검증하지만, OCR API를 재실행하지 않는다.
- 입력은 locked fixture에서 메모리로 합성하므로 API-to-helper integration 회귀는 기존 Python fixture check와 함께 봐야 한다.
- table_data legacy fallback 전용 fixture는 아직 별도로 없다.

## 9. 다음 작업 제안
1. FRONTEND-CLEANUP 후속 작업마다 이 JS runner를 회귀 검증으로 실행한다.
2. 필요하면 별도 작업에서 API 기반 input fixture를 추가해 integration coverage를 넓힌다.
3. 거래_3 insuranceCode/amount 정책은 별도 이슈로 유지한다.
