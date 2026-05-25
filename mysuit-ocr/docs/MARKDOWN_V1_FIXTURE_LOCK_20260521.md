# MARKDOWN V1 FIXTURE LOCK 20260521

## 1. 사용 도구와 모델
- 사용 도구: Codex
- 사용 모델: Codex
- 작업명: `CODEX_FRONTEND_CLEANUP_2A_MARKDOWN_CONTRACT_FIXTURE_LOCK_NO_PROD_MODIFY`

## 2. 코드 수정 여부
- 운영 코드 수정 없음.
- `OcrResultPanel.tsx` 리팩토링 없음.
- Markdown helper 생성 없음.
- fixture와 docs, tmp 분석 스크립트만 생성했다.
- `review_log.jsonl` API append side effect는 실행 전 바이트로 복원했다.

## 3. Fixture 저장 위치
- `tmp/fixtures/markdown_v1/manifest.json`
- `tmp/fixtures/markdown_v1/invoice_statement/*.md`
- `tmp/fixtures/markdown_v1/receipt/*.md`

## 4. Fixture 생성 방식
- API URL: `http://127.0.0.1:9099/ocr/extract`
- API source: `existing`
- 현재 `OcrResultPanel.tsx` `toMarkdown` 로직을 tmp 스크립트에서 mirror했다.
- fixture line ending은 LF로 저장했다.

## 5. Fixture 결과
| caseId | templateId | fixturePath | bytes | lines | status |
| --- | --- | --- | --- | --- | --- |
| trade_1_1jpg | TPL-31D13CF3 | invoice_statement/trade_1_1jpg.md | 922 | 17 | PASS |
| trade_2_2pdf | TPL-5A8C2374 | invoice_statement/trade_2_2pdf.md | 875 | 16 | PASS |
| trade_3_3pdf | TPL-E4B15A22 | invoice_statement/trade_3_3pdf.md | 942 | 17 | PASS |
| trade_7_7pdf | TPL-3AFD383E | invoice_statement/trade_7_7pdf.md | 1004 | 17 | PASS |
| tpl_003_1jpg | TPL-003 | receipt/tpl_003_1jpg.md | 471 | 13 | PASS |
| tpl_003_2jpg | TPL-003 | receipt/tpl_003_2jpg.md | 470 | 13 | PASS |


## 6. rowIndex / 거래_3 / 영수증 확인
- Markdown v1은 tableRows columns를 펼치지 않으므로 rowIndex 포함/제외는 문자열에 직접 나타나지 않는다.
- 거래_1/2/3은 table field 요약 `표 데이터(N행)`을 고정했다.
- 거래_3 insuranceCode/amount locked behavior는 Markdown v1 상세 문자열에는 직접 반영되지 않는다.
- 영수증 1.jpg/2.jpg는 field-only Markdown 대표 fixture로 고정했다.

## 7. Typecheck / Build
| command | status | exit | seconds |
| --- | --- | --- | --- |
| npm run typecheck | PASS | 0 | 1.672 |
| npm run build | PASS | 0 | 16.661 |

Known stderr noise:
- ISSUE-FRONTEND-BUILD-LOG-1: `ESLint: nextVitals is not iterable`

## 8. 최종 판정
- overall: `PASS`
- counts: `{'PASS': 6}`

## 9. 다음 작업 제안
1. FRONTEND-CLEANUP-2B에서 `fieldsToMarkdown` helper를 분리한다.
2. 분리 후 이번 Markdown fixture와 exact string equality를 비교한다.
3. Clean JSON fixture runner와 함께 회귀 검증에 포함한다.
