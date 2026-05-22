# MARKDOWN V1 TRADE7 FIXTURE REBAKE 20260522

## 1. 사용 도구와 모델
- 사용 도구: Codex
- 사용 모델: Codex
- 작업명: `MARKDOWN-V1-TRADE7-FIXTURE-REBAKE`

## 2. 코드 수정 여부
- 운영 frontend/backend 코드 수정 없음.
- backend parser, `templates.json`, Clean JSON fixture, table view model fixture 수정 없음.
- markdown fixture는 `trade_7_7pdf.md`만 갱신.
- markdown manifest는 trade_7 rebake metadata만 갱신.

## 3. 수정 파일
- `tmp/fixtures/markdown_v1/invoice_statement/trade_7_7pdf.md`
- `tmp/fixtures/markdown_v1/manifest.json`
- `tmp/codex_markdown_trade7_fixture_rebake.py`
- `docs/MARKDOWN_V1_TRADE7_FIXTURE_REBAKE_20260522.md`
- `docs/MARKDOWN_V1_TRADE7_FIXTURE_REBAKE_20260522.json`

## 4. rebake 결정 이유
- precheck 결과 drift는 2C frontend code와 직접 인과가 없고, backend `TPL-3AFD383E` template 좌표 변경으로 인한 현재 backend actual 차이로 판단됨.
- 사용자가 현재 actual을 새 기준으로 인정함.
- 새 결과는 사업자번호 괄호가 제거되고 confidence가 `100.0%`로 개선됨.

## 5. old expected / new expected 비교
| item | old | new |
| --- | --- | --- |
| value | `(113-85-04425)` | `113-85-04425` |
| confidence | `97.1%` | `100.0%` |
| line | `| 2 | 공급받는자 사업자 번호 (field_2) | (113-85-04425) | 97.1% | OCR |` | `| 2 | 공급받는자 사업자 번호 (field_2) | 113-85-04425 | 100.0% | OCR |` |

## 6. TPL-3AFD383E template dirty와의 관계
- `ocr-server/data/templates.json`은 수정하지 않음.
- `TPL-3AFD383E` dirty 좌표 변경을 이번 rebake의 기준으로 수용.
- `TPL-95328E52` dirty는 이번 범위 밖이며 follow-up 후보로 기록.

## 7. 수정하지 않은 범위
- `src/**`
- `ocr-server/data/templates.json`
- backend parser/extractors
- Clean JSON fixtures
- table_view_model fixtures
- trade_7 외 markdown fixtures

## 8. runner 결과
| check | status | exit | seconds |
| --- | --- | --- | --- |
| markdown | PASS | 0 | 202.498 |
| table_view_model | PASS | 0 | 0.288 |
| clean_json | PASS | 0 | 21.32 |
| typecheck | PASS | 0 | 1.499 |
| build | PASS | 0 | 16.776 |

## 9. 다른 fixture 변경 확인
| fixture | unchanged |
| --- | --- |
| invoice_statement/trade_1_1jpg.md | True |
| invoice_statement/trade_2_2pdf.md | True |
| invoice_statement/trade_3_3pdf.md | True |
| receipt/tpl_003_1jpg.md | True |
| receipt/tpl_003_2jpg.md | True |

## 10. known stderr noise
- build known stderr noise observed: `True`
- issue: `ESLint: nextVitals is not iterable`
- exit code 0이면 non-blocking.

## 11. 남은 이슈
- `TPL-95328E52` dirty 영향은 이번 작업 범위 밖. 별도 precheck 후보.
- `review_log.jsonl` append 여부: {'beforeBytes': 14195276, 'afterBytes': 14195276, 'appendedBytes': 0, 'note': 'Recorded only; no manual revert performed.'}

## 12. 다음 작업 제안
- RunOCR UI split precheck
- Template folder ownership precheck
- TPL-95328E52 dirty 영향 precheck
- common/utils 이동은 feature 폴더 안정화 후 진행
- TestWorkspace는 사용자 확인 후 진행
