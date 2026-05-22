# FRONTEND CLEANUP 3C TABLE RENDERER PRECHECK 20260521

## 1. 사용 도구와 모델
- 사용 도구: Codex
- 사용 모델: Codex
- 작업명: `CODEX_FRONTEND_CLEANUP_3C_TABLE_RENDERER_PRECHECK_NO_PROD_MODIFY`

## 2. 코드 수정 여부
- 운영 코드 수정 없음.
- `OcrResultPanel.tsx`, `cleanJsonBuilder.ts`, `markdownReportBuilder.ts`, `ocrResultFormatters.ts`, `invoiceTableDisplay.ts`, `TestWorkspace.tsx` 수정 없음.
- Preview/Custom/Validation table renderer 또는 view model helper 추출 없음.
- 생성 파일은 tmp 분석 스크립트와 docs 리포트뿐이다.

## 3. Table Code Locations
| item | line |
| --- | ---: |
| docTableRows | 665 |
| docTableMeta | 673 |
| docTableDisplayCols | 683 |
| previewTableFields | 690 |
| previewRenderer | 981 |
| customStructuredBranch | 1293 |
| customFallbackBranch | 1385 |
| validationStructuredBranch | 1515 |
| missingExpectedWarning | 702 |
| customTableEditsState | 233 |

## 4. Data Flow 요약
- Preview: `previewTableFields`와 `docTableRows/docTableDisplayCols`를 사용한다. 구조화 table은 read-only, fallback은 `parseTableField(field.value).displayRows`를 렌더링한다.
- Custom: `docTableRows/docTableDisplayCols`와 `customTableEdits`를 사용한다. 구조화 table은 textarea editable이며 fallback은 raw `parseTableField` 표다.
- Validation: validation section item 안에서 `docTableRows/docTableDisplayCols`를 사용한다. 상태 dot/classes, confidence, adoption이 붙고 legacy fallback은 rowLabel 중심이다.
- 세 탭 모두 구조화 column order와 rowIndex는 `docTableDisplayCols`를 따르며, 직접 재계산하지 않아야 한다.

## 5. Difference Matrix
| axis | Preview | Custom | Validation | same | props? | risk |
| --- | --- | --- | --- | --- | --- | --- |
| data source | previewTableFields + docTableRows | field + docTableRows + customTableEdits | validation item.field + docTableRows | False | True | MEDIUM |
| structured table | first preview table only | field_type table branch | validation table item branch | False | True | MEDIUM |
| legacy fallback | renders displayRows body | renders displayRows body + firstRowPreview | rowLabel fallback only, no comparable body branch observed | False | False | HIGH |
| docTableRows | yes | yes | yes | True | True | LOW |
| docTableDisplayCols | yes | yes | yes | True | True | LOW |
| column order | docTableDisplayCols | docTableDisplayCols | docTableDisplayCols | True | True | LOW |
| rowIndex policy | docTableDisplayCols/shouldDisplayRowIndex | docTableDisplayCols/shouldDisplayRowIndex | docTableDisplayCols/shouldDisplayRowIndex | True | True | LOW |
| internal key filtering | already in buildInvoicePreviewCols | already in buildInvoicePreviewCols | already in buildInvoicePreviewCols | True | True | LOW |
| cell normalization | normalizeCell + '-' | normalizeCell into editRows, textarea empty string | normalizeCell + '-' | False | True | MEDIUM |
| empty cell | '-' | empty string in textarea | '-' | False | True | MEDIUM |
| header rendering | labelKo + key subtitle | labelKo + key subtitle, title differs | labelKo + key subtitle inside validation block | False | True | MEDIUM |
| alignment/width | _invoiceColWidth/_invoiceDataAlign | same + textarea padding 0 | same + validation margins | False | True | MEDIUM |
| editable | no | yes textarea/onChange/onBlur | no | False | True | HIGH |
| validation/GT status | none | none | status dot/classes/confidence section | False | False | HIGH |
| source/adoption/confidence | not per table cell; warning badge | adoption label in meta | adoption + confidence + status | False | True | MEDIUM |
| row label/summary | row count next to title | row count and firstRowPreview fallback | rowLabel in validation value line | False | True | MEDIUM |
| table field summary | Markdown summary plus JSX table | field value meta | validation value line | False | True | MEDIUM |
| trade_3 locked behavior | through docTableDisplayCols; warning badge possible | same cols/edit rows | same cols in validation table | True | True | MEDIUM |

## 6. A/B/C 추천
- 최종 추천: **B. view model / pure helper만 추출**
- A가 아닌 이유:
  - difference axes are 12, more than the A threshold
  - HIGH-risk axes exist: legacy fallback, editable, validation/GT status
  - Custom textarea editing and Validation status wrapper would make a common renderer prop-heavy
- C가 아닌 이유:
  - structured table data policy is shared through docTableRows/docTableDisplayCols
  - rowIndex and column order are already centralized in buildInvoicePreviewCols
  - a pure view model can be fixture-tested without touching JSX

## 7. B 옵션 구체화
- pure helper 우선: `True`
- hook 필요 여부: `False`
- 후보 파일: `src/lib/ocrTableViewModel.ts, src/lib/structuredTableViewModel.ts`
- 후보 helper: `buildStructuredTableViewModel, buildLegacyTableViewModel, buildOcrTableViewModel`
- React 의존: No React dependency required for view model. JSX stays in OcrResultPanel or later components.

## 8. 공통 Renderer 가능성
- 지금 당장 공통 React renderer 추출은 권장하지 않는다.
- 이유: Custom editable textarea, Validation status wrapper, legacy fallback 차이 때문에 props가 과하게 늘어날 가능성이 높다.
- 추후 view model fixture가 안정화된 뒤 DOM/Playwright 검증까지 붙이면 재검토 가능하다.

## 9. Fixture / Check 전략
- 권장 fixture root: `tmp/fixtures/table_view_model_v1/`
- 권장 runner: `tmp/check_table_view_model_v1_fixtures_js.mjs or tsx`
- before/after: deep equality for view model JSON, plus existing Clean JSON and Markdown fixture runners
- 대상:
  - invoice_statement trade_1~trade_7 structured docTableRows
  - trade_3 to lock insuranceCode/amount behavior
  - synthetic legacy parseTableField fallback without document_fields.tableRows
  - optional custom editRows fixture for textarea value behavior

## 10. 위험도 평가
| risk | likelihood | impact | mitigation | fixture/check |
| --- | --- | --- | --- | --- |
| rowIndex policy regression | LOW | HIGH | Do not compute rowIndex in renderer; consume docTableDisplayCols only. | True |
| trade_3 insuranceCode/amount locked behavior changes | MEDIUM | HIGH | Include trade_3 view model fixture and Clean JSON runner. | True |
| Preview/Clean JSON column order divergence | LOW | HIGH | Keep shared docTableDisplayCols source. | True |
| Custom textarea edit behavior breaks | MEDIUM | HIGH | Leave Custom JSX in place; model editRows separately. | True |
| Validation status/GT wrapper breaks | MEDIUM | HIGH | Do not merge Validation renderer in first pass. | True |
| adoption/confidence/source display omitted | MEDIUM | MEDIUM | Keep metadata outside core table renderer or model explicitly. | True |
| legacy fallback omitted | MEDIUM | HIGH | Create synthetic fallback fixture before extraction. | True |
| props explosion in common renderer | HIGH | MEDIUM | Choose B, not A, for next step. | False |
| circular dependency | LOW | HIGH | View model may import invoiceTableDisplay/formatters only; not Clean JSON/Markdown. | False |
| TestWorkspace policy divergence | LOW | MEDIUM | Reference only; handle in separate approved task. | False |

## 11. OcrResultPanel Cleanup Cycle Close-out
- close-out 필요: `True`
- 이번 작업에서 생성: `False`
- 다음 close-out 후보 파일:
  - `docs/FRONTEND_CLEANUP_OCR_RESULT_PANEL_CYCLE_1_CLOSEOUT_20260521.md`
  - `docs/FRONTEND_CLEANUP_OCR_RESULT_PANEL_CYCLE_1_CLOSEOUT_20260521.json`

## 12. Typecheck / Build
| command | status | exit | seconds |
| --- | --- | ---: | ---: |
| npm run typecheck | PASS | 0 | 2.172 |
| npm run build | PASS | 0 | 16.183 |

Known stderr noise:
- ISSUE-FRONTEND-BUILD-LOG-1: `ESLint: nextVitals is not iterable` observed = `True`

## 13. 다음 작업 제안
1. 바로 renderer를 추출하지 말고 table view-model fixture lock 작업을 먼저 수행한다.
2. 이후 `buildStructuredTableViewModel` 같은 pure helper를 작게 추출한다.
3. 공통 React renderer는 view model 검증이 안정화된 뒤 별도 판단한다.
4. OcrResultPanel cleanup cycle 1 close-out 문서를 생성해 완료/보류/재개 조건을 정리한다.
