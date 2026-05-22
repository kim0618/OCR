# FRONTEND CLEANUP 3D3 SMOKE COLUMN POLICY PRECHECK 20260521

## 1. 사용 도구와 모델
- 사용 도구: Codex
- 사용 모델: Codex
- 작업명: `CODEX_FRONTEND_CLEANUP_3D3_SMOKE_COLUMN_POLICY_PRECHECK_NO_PROD_MODIFY`

## 2. 코드 수정 여부
- 운영 코드 수정 없음.
- fixture 수정 없음.
- `OcrResultPanel.tsx`, `invoiceTableDisplay.ts`, `structuredTableViewModel.ts`, backend/parser, templates, manifest/GT 수정 없음.
- API 재실행 없음. locked fixture/input 및 기존 리포트만 분석.

## 3. 생성 파일
- `tmp/codex_3d3_smoke_column_policy_precheck.py`
- `docs/FRONTEND_CLEANUP_3D3_SMOKE_COLUMN_POLICY_PRECHECK_20260521.md`
- `docs/FRONTEND_CLEANUP_3D3_SMOKE_COLUMN_POLICY_PRECHECK_20260521.json`

## 4. Smoke Issue 요약
- trade_4: Preview에 `totalAmount` 추가 컬럼 표시.
- trade_6: 원본에 Lot No 구조가 보이나 Preview에서 `lotNo` 누락.
- trade_7: 원본에 시리얼/로트No 구조가 보이나 Preview에서 `serialLotComposite` 누락.

## 5. Case별 분석 요약
| case | classification | displayCols | expectedDisplay | extraVsExpectedDisplay | missingExpectedDisplay |
| --- | --- | --- | --- | --- | --- |
| trade_4_4pdf | DISPLAY_POLICY_AND_CURRENT_FIXTURE_LOCK_ISSUE | ["itemName", "lotNo", "unit", "quantity", "unitPrice", "supplyAmount", "taxAmount", "totalAmount"] | ["itemName", "lotNo", "unit", "quantity", "unitPrice", "supplyAmount", "taxAmount"] | ["totalAmount"] | [] |
| trade_6_6pdf | FRONTEND_DISPLAY_POLICY_DEDUP_NOISE_RULE_ISSUE | ["rowIndex", "itemCode", "itemName", "quantity", "expiryDate"] | ["rowIndex", "itemCode", "itemName", "quantity", "lotNo", "expiryDate"] | [] | ["lotNo"] |
| trade_7_7pdf | FRONTEND_INTERNAL_COMPOSITE_FILTER_AND_EXPECTED_KEY_MISMATCH | ["itemName", "unit", "quantity"] | ["itemName", "serialLotComposite", "unit", "quantity"] | [] | ["serialLotComposite"] |

## 6. trade_4 분석
- `displayCols` / output / Clean JSON 모두 `totalAmount` 포함.
- input row `totalAmount=28,338,000`.
- testset manifest의 display 목록은 `itemName, lotNo, unit, quantity, unitPrice, supplyAmount, taxAmount`로 `totalAmount` 제외.
- 그러나 expected optional 및 3D1 capture `tableMetaExpectedColumnKeys`에는 `totalAmount`가 있고, 현재 `buildInvoicePreviewCols`는 expectedColumnKeys + hasValue 기준으로 유지한다.
- 판정: current fixture가 smoke에서 보기 싫은 current behavior를 lock했다. frontend display policy와 tableRows/document summary 혼입 경계 문제.

## 7. trade_6 분석
- `rows`에는 `lotNo` 값이 존재한다: `23001`, `23001`, `T17322003`.
- expected display는 `rowIndex,itemCode,itemName,quantity,lotNo,expiryDate`.
- 실제 display/output은 `rowIndex,itemCode,itemName,quantity,expiryDate`.
- `buildInvoicePreviewCols`의 lot 노이즈 규칙: itemCode가 의미 있고 manufacturingNo가 전부 비어 있으면 lotNo를 제거한다.
- 판정: 값은 있으나 frontend display dedup/noise 정책이 제거한 케이스. 일부 row는 lot/expiry 자체가 비어 있어 backend/parser 보정 이슈도 함께 존재.

## 8. trade_7 분석
- input row에 `serialLotComposite=0350623-231024-260811`, `serialNo=0350623-231024-260811`가 존재.
- expected display는 `itemName,serialLotComposite,unit,quantity`.
- 실제 display/output은 `itemName,unit,quantity`.
- `serialLotComposite`는 `_INTERNAL_KEYS` 및 `Composite` 필터로 후보에서 제외된다.
- 판정: 중요한 값은 rows에 있으나 frontend internal/composite filter가 expected display 요구와 충돌한다.

## 9. 공통 원인
- `buildStructuredTableViewModel`은 pass-through helper다. 컬럼 추가/삭제 정책을 갖지 않는다.
- 문제는 `docTableDisplayCols = buildInvoicePreviewCols(docTableMeta, docTableRows)` 이전/내부 정책에서 발생한다.
- 현재 우선순위는 `tableMeta.expectedColumnKeys -> tableMeta.columns -> allowlist`이며 이후 hasValue, itemCode majority, lot/mfg dedup, lot noise, serialNo/lotNo dedup, rowIndex prepend가 적용된다.
- `serialLotComposite` 같은 composite key는 expected display에 있어도 internal key로 제거된다.
- `totalAmount` 같은 doc summary 성격 값은 expectedColumnKeys와 row 값이 있으면 display에 남는다.

## 10. 수정 후보
| id | summary | pros | cons | regressionRisk | fixtureImpact |
| --- | --- | --- | --- | --- | --- |
| candidate_1_display_exclude_summary_keys | invoiceTableDisplay에서 문서 profile별 summary key(totalAmount 등)를 display exclude | trade_4 totalAmount extra column을 작게 해결 | 문서별 예외가 늘고 Clean JSON displayCols 공유 경로에 영향 가능 | medium: totalAmount가 품목 행으로 필요한 다른 sample이 있으면 숨겨짐 | table_view_model trade_4 갱신 필요 가능; Clean JSON 영향 확인 필요 |
| candidate_2_stronger_template_display_priority | tableMeta.expectedColumnKeys보다 template tableExpectedColumns.display를 강하게 우선 | 사용자가 보는 원본/템플릿 display 의도와 일치 | 현재 API tableMeta만으로는 OcrResultPanel에 display list 전달 경로가 필요할 수 있음 | medium-high: 기존 locked fixtures 다수 갱신 가능 | trade_4/6/7 table_view_model 갱신 가능 |
| candidate_3_hide_keys_not_in_expected_display | 값이 있어도 expected/display policy에 없는 key는 숨김 | totalAmount 같은 extra column 억제 | expected display가 누락/구버전이면 실제 유용한 OCR 값을 잃음 | high without robust template display source | table_view_model and possibly Clean JSON fixture update |
| candidate_4_backend_lot_serial_mapping_fix | trade_6/7 lot/serial 값이 표준 display key로 안정 매핑되도록 parser 보정 | 원본 표 구조와 data semantics 개선 | backend/parser 영향 범위가 크고 fixture 재생성 필요 | medium-high: OCR row grouping/value mapping 회귀 가능 | tableRows 기반 fixtures 갱신 필요 |
| candidate_5_defer_until_template_table_definition | Template table column definition 도입 전까지 known issue로 보류 | 현재 cleanup 안정성 유지, 임시 예외 최소화 | manual smoke WARN 지속 | low | none now |

## 11. Fixture 영향
- 현재 table_view_model_v1 및 Clean JSON fixture는 smoke에서 발견된 current behavior를 그대로 lock하고 있다.
- 정책 수정 시 trade_4/6/7 output fixture와 Clean JSON fixture 갱신 여부를 명시적으로 결정해야 한다.
- display-only 수정이면 Clean JSON fixture는 유지할 수 있으나, `buildInvoicePreviewCols`가 Clean JSON builder에도 입력으로 쓰이는 경로라 영향 범위 확인이 필요하다.

## 12. Smoke 판정 갱신
| sample | verdict |
| --- | --- |
| trade_2 | PASS |
| trade_3 | PASS_WITH_LABEL_NOTE |
| trade_4 | WARN_totalAmount_extra_column |
| trade_5 | PASS_OR_NOT_ANALYZED |
| trade_6 | WARN_lot_or_expiry_column_issue |
| trade_7 | WARN_serial_lot_column_missing |
| overall | automatic checks PASS; manual smoke WARN; OcrResultPanel technical cleanup successful; Preview column policy follow-up required |

## 13. Typecheck/Build 결과
| command | status | exit | seconds | known stderr noise |
| --- | --- | ---: | ---: | --- |
| npm.cmd run typecheck | PASS | 0 | 1.773 | False |
| npm.cmd run build | PASS | 0 | 15.867 | True |

## 14. 다음 작업 제안
1. trade_4/6/7 display policy를 수정할지, Template table column definition 도입까지 known issue로 둘지 결정.
2. 수정한다면 `invoiceTableDisplay.ts` 정책 변경 전 별도 fixture update intent 문서화.
3. Clean JSON과 Preview가 같은 displayCols를 공유하는 현 구조에서 display-only 정책과 export policy를 분리할지 precheck.
4. trade_6/7은 backend/parser가 lot/serial values를 표준 key로 더 안정적으로 매핑해야 하는지 별도 parser precheck.
5. 정책 변경 후 table_view_model runner, Clean JSON runner, Markdown check, manual smoke 재수행.
