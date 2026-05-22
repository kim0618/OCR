# FRONTEND INVOICE TABLE DISPLAY POLICY FIX PRECHECK 20260522

## 1. 사용 도구와 모델
- 사용 도구: Codex
- 사용 모델: Codex
- 작업명: `CODEX_FRONTEND_INVOICE_TABLE_DISPLAY_POLICY_FIX_PRECHECK_NO_PROD_MODIFY`

## 2. 코드 수정 여부
- 운영 코드 수정 없음.
- fixture 수정 없음.
- `OcrResultPanel.tsx`, `invoiceTableDisplay.ts`, `structuredTableViewModel.ts`, `cleanJsonBuilder.ts`, backend/parser, templates, manifest/GT 수정 없음.

## 3. 생성 파일
- `tmp/codex_invoice_table_display_policy_fix_precheck.py`
- `docs/FRONTEND_INVOICE_TABLE_DISPLAY_POLICY_FIX_PRECHECK_20260522.md`
- `docs/FRONTEND_INVOICE_TABLE_DISPLAY_POLICY_FIX_PRECHECK_20260522.json`

## 4. 현재 Display Policy 흐름
1. `OcrResultPanel.tsx`에서 `docTableRows = result.document_fields.tableRows`.
2. `docTableDisplayCols = buildInvoicePreviewCols(docTableMeta, docTableRows)`.
3. Preview는 `buildStructuredTableViewModel({ rows, displayCols })` 결과를 사용한다.
4. Clean JSON은 같은 `docTableDisplayCols`를 `buildCleanJsonResult`에 전달한다.
5. 따라서 `invoiceTableDisplay.ts`의 display policy 변경은 Preview와 Clean JSON fixture 모두에 영향을 줄 수 있다.

## 5. trade_4 상세 원인
- `totalAmount`는 input rows/displayCols/view_model/Clean JSON에 모두 존재한다.
- testset manifest display columns에는 `totalAmount`가 없다.
- 현재 `tableMetaExpectedColumnKeys`에는 `totalAmount`가 있고, hasValue 필터를 통과해 표시된다.
- 판정: summary/doc-level 성격의 `totalAmount`를 item row display에서 제외하는 frontend display policy 보정이 필요하다.

## 6. trade_6 상세 원인
- `lotNo` 값은 rows에 존재한다.
- expected display에도 `lotNo`가 있다.
- 현재 `itemCode`가 있고 `manufacturingNo`가 비어 있으면 `lotNo`를 OCR 노이즈로 숨기는 규칙 때문에 displayCols에서 제거된다.
- 판정: expected/display column에 `lotNo`가 있고 값이 있으면 기존 노이즈 규칙보다 우선할지 결정해야 한다.

## 7. trade_7 상세 원인
- `serialLotComposite=0350623-231024-260811` 값은 rows에 존재한다.
- expected display에도 `serialLotComposite`가 있다.
- 현재 internal/composite key 필터가 `serialLotComposite`를 후보에서 제거한다.
- 판정: expected display가 명시한 composite key는 display 가능한 예외로 승격할 필요가 있다.

## 8. Helper 문제 여부
- `buildStructuredTableViewModel` 문제 아님.
- helper는 caller가 준 `displayCols`를 그대로 columns/cells로 변환하는 pass-through다.
- 수정 지점은 `invoiceTableDisplay.ts`의 `buildInvoicePreviewCols` 또는 그 입력으로 들어가는 expected/display policy 계층이다.

## 9. 추천 Display Policy
권장 1차 조합:
- `totalAmount`는 table row display summary key로 제외.
- expected/display columns가 명시한 `lotNo`는 값이 있으면 기존 lot noise rule보다 우선 표시.
- expected/display columns가 명시한 `serialLotComposite`는 internal/composite 필터 예외로 표시 허용.
- 빈 컬럼/완전 무의미 컬럼은 계속 숨김.
- rowIndex 정책과 trade_3 locked behavior는 그대로 유지.

## 10. trade_1~trade_7 예상 영향
| case | before | recommendedAfter | added | removed | rowIndex | cleanJsonFixture | tableViewModelFixture | risk |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| trade_1_1jpg | ["itemName", "spec", "manufacturingNo", "expiryDate", "quantity", "unitPrice", "amount"] | ["itemName", "spec", "manufacturingNo", "expiryDate", "quantity", "unitPrice", "amount"] | [] | [] | excluded -> excluded |  |  | low |
| trade_2_2pdf | ["rowIndex", "itemCode", "itemName", "quantity", "consumerUnitPrice", "supplyUnitPrice", "supplyAmount"] | ["rowIndex", "itemCode", "itemName", "quantity", "consumerUnitPrice", "supplyUnitPrice", "supplyAmount"] | [] | [] | included -> included |  |  | low |
| trade_3_3pdf | ["rowIndex", "insuranceCode", "itemName", "quantity", "unitPrice", "amount", "manufacturer"] | ["rowIndex", "insuranceCode", "itemName", "quantity", "unitPrice", "amount", "manufacturer"] | [] | [] | included -> included |  |  | low |
| trade_4_4pdf | ["itemName", "lotNo", "unit", "quantity", "unitPrice", "supplyAmount", "taxAmount", "totalAmount"] | ["itemName", "lotNo", "unit", "quantity", "unitPrice", "supplyAmount", "taxAmount"] | [] | ["totalAmount"] | excluded -> excluded | Y | Y | medium |
| trade_5_5pdf | ["itemName", "itemCode", "quantity", "unitPrice", "amount"] | ["itemName", "itemCode", "quantity", "unitPrice", "amount"] | [] | [] | excluded -> excluded |  |  | low |
| trade_6_6pdf | ["rowIndex", "itemCode", "itemName", "quantity", "expiryDate"] | ["rowIndex", "itemCode", "itemName", "quantity", "lotNo", "expiryDate"] | ["lotNo"] | [] | included -> included | Y | Y | medium |
| trade_7_7pdf | ["itemName", "unit", "quantity"] | ["itemName", "serialLotComposite", "unit", "quantity"] | ["serialLotComposite"] | [] | excluded -> excluded | Y | Y | medium |

## 11. 수정 후보 비교
| id | summary | pros | cons | regressionRisk | fixtureImpact | recommendation |
| --- | --- | --- | --- | --- | --- | --- |
| candidate_1_summary_key_hard_exclude | summary/doc-level key(totalAmount)를 table display에서 제외 | trade_4 문제를 가장 작게 해결; supplyAmount/taxAmount는 유지 가능 | totalAmount가 실제 품목표 컬럼인 문서가 있으면 숨겨짐 | medium | trade_4 table_view_model/Clean JSON fixture 갱신 | adopt as targeted rule with fixture update intent |
| candidate_2_lot_serial_key_allowlist | expected/display에 있는 lotNo/serialLotComposite를 값이 있으면 표시 허용 | trade_6/7 원본 표 구조와 맞음 | 기존 노이즈 제거 규칙을 우회하므로 일부 샘플에서 중복/노이즈가 살아날 수 있음 | medium | trade_6/trade_7 table_view_model/Clean JSON fixture 갱신 | adopt only when expected/display column explicitly includes the key |
| candidate_3_expected_display_priority | manifest/template expected display columns를 우선하고 없는 key는 숨김 | 사용자 시각 기준과 가장 일관됨 | runtime에서 template display definition 전달 경로가 약하면 적용 범위가 커짐 | medium-high | trade_4/6/7 plus possibly more if display source changes | longer-term direction; first fix can be a constrained subset |
| candidate_4_known_issue_until_template_column_definition | Template table column definition 도입까지 known issue로 보류 | 현재 fixtures and cleanup stability 유지 | manual smoke WARN 지속 | low | none | acceptable only if UX issue can wait |
| candidate_5_backend_tableRows_policy | parser가 row-level이 아닌 doc-level key를 tableRows에 넣지 않게 수정 | 데이터 생성 계층을 근본적으로 정리 | backend/parser 영향 범위와 OCR 회귀 위험이 큼 | high | API-derived fixtures broadly may need regeneration | not first fix; do separate backend precheck if needed |

## 12. Fixture 갱신 계획
| fixture | reason | requiredIfPolicyApplied |
| --- | --- | --- |
| tmp/fixtures/table_view_model_v1/inputs/trade_4_4pdf.input.json | displayCols changed | True |
| tmp/fixtures/table_view_model_v1/invoice_statement/trade_4_4pdf.view_model.json | columns/cells/meta.columnCount changed | True |
| tmp/fixtures/clean_json_v1/invoice_statement/trade_4_4pdf.clean.json | Clean JSON table rows use docTableDisplayCols | True |
| tmp/fixtures/table_view_model_v1/inputs/trade_6_6pdf.input.json | displayCols changed | True |
| tmp/fixtures/table_view_model_v1/invoice_statement/trade_6_6pdf.view_model.json | columns/cells/meta.columnCount changed | True |
| tmp/fixtures/clean_json_v1/invoice_statement/trade_6_6pdf.clean.json | Clean JSON table rows use docTableDisplayCols | True |
| tmp/fixtures/table_view_model_v1/inputs/trade_7_7pdf.input.json | displayCols changed | True |
| tmp/fixtures/table_view_model_v1/invoice_statement/trade_7_7pdf.view_model.json | columns/cells/meta.columnCount changed | True |
| tmp/fixtures/clean_json_v1/invoice_statement/trade_7_7pdf.clean.json | Clean JSON table rows use docTableDisplayCols | True |
| tmp/fixtures/table_view_model_v1/manifest.json | columnCount/inputFixture metadata may change | True |
| tmp/fixtures/clean_json_v1/manifest.json | rowKeys metadata may change | True |

## 13. Smoke 판정 업데이트
- automatic checks: PASS
- manual smoke: WARN_COLUMN_POLICY
- 3D-3 technical helper migration: PASS
- Preview/Clean JSON column policy: FOLLOW_UP_REQUIRED

## 14. Typecheck/Build 결과
| command | status | exit | seconds | known stderr noise |
| --- | --- | ---: | ---: | --- |
| npm.cmd run typecheck | PASS | 0 | 2.372 | False |
| npm.cmd run build | PASS | 0 | 17.974 | True |

## 15. 다음 작업 제안
- 추천 작업명: `CODEX_FRONTEND_INVOICE_TABLE_DISPLAY_POLICY_FIX_OR_DRYRUN` 또는 `FRONTEND-CLEANUP-3D4-INVOICE-TABLE-DISPLAY-POLICY-FIX`.
- 예상 수정 파일: `src/lib/invoiceTableDisplay.ts`.
- 예상 갱신: table_view_model input/output fixtures, Clean JSON fixtures, manifest metadata for affected cases.
- `structuredTableViewModel.ts`와 `OcrResultPanel.tsx`는 수정하지 않을 가능성이 높다.
- 정책 변경 후 table_view_model runner 8/8, Clean JSON runner 9/9, Markdown check 6/6, typecheck/build, manual smoke를 재수행한다.
