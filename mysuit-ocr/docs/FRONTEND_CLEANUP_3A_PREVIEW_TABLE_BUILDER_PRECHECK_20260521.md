# FRONTEND CLEANUP 3A PREVIEW TABLE BUILDER PRECHECK 20260521

## 1. 사용 도구와 모델
- 사용 도구: Codex
- 사용 모델: Codex
- 작업명: `CODEX_FRONTEND_CLEANUP_3A_PREVIEW_TABLE_BUILDER_PRECHECK_NO_PROD_MODIFY`

## 2. 코드 수정 여부
- 운영 코드 수정 없음.
- `OcrResultPanel.tsx`, `cleanJsonBuilder.ts`, `markdownReportBuilder.ts`, `ocrResultFormatters.ts`, `TestWorkspace.tsx` 수정 없음.
- Preview table builder/helper 추출 없음.
- 생성 파일은 tmp 분석 스크립트와 docs 리포트뿐이다.

## 3. Preview Table 관련 코드 위치
| item | line |
| --- | ---: |
| filterInvoicePreviewDisplayCols | 108 |
| toMarkdown | 657 |
| docTableRowsUseMemo | 665 |
| docTableMetaUseMemo | 673 |
| docTableDisplayColsUseMemo | 683 |
| previewTableFieldsUseMemo | 690 |
| missingExpectedWarningUseMemo | 702 |
| cleanJsonUseMemo | 737 |
| previewMarkdownRender | 979 |
| previewTableMap | 981 |
| customStructuredTableBranch | 1293 |
| validationStructuredTableBranch | 1515 |

## 4. Preview Table Flow 요약
1. `docTableRows`는 `result.document_fields.tableRows`에서 추출한다.
2. `docTableMeta`는 `result.document_fields.tableMeta`에서 추출한다.
3. `docTableDisplayCols`는 `buildInvoicePreviewCols(docTableMeta, docTableRows)` 결과를 사용한다.
4. `previewTableFields`는 `editedFields` 중 `field_type === "table"`만 골라 `fieldLabelFull`과 `parseTableField(field.value)`를 붙인 list다.
5. Preview JSX는 첫 table field에서 `docTableRows + docTableDisplayCols`가 있으면 구조화 거래명세서 표를 렌더링한다.
6. 구조화 rows가 없으면 `parseTableField(field.value).displayRows` fallback을 렌더링한다.

## 5. Current Contract
- 입력: `editedFields`, `docTableRows`, `docTableMeta`, `docTableDisplayCols`, `parseTableField(field.value)`.
- `previewTableFields` 출력 shape: `idx`, `label`, `rows`, `nonEmpty`, `displayRows`, `isSingleCol`, `rowLabel`.
- 구조화 거래명세서 column order는 `docTableDisplayCols`를 그대로 따른다.
- legacy fallback은 `field.value` JSON cell array 순서를 따른다.
- Preview rowIndex 판단은 `previewTableFields`가 직접 하지 않고 `buildInvoicePreviewCols`/`shouldDisplayRowIndex` 결과를 따른다.

## 6. 추출 가능 범위
| layer | candidate | extractable | risk | note |
| --- | --- | --- | --- | --- |
| pure data builder | buildPreviewTableFields | True | LOW-MEDIUM | This is the safest first extraction; it does not touch JSX rendering. |
| structured invoice table display data | buildStructuredPreviewTableData | later | MEDIUM | Useful, but should follow a small PreviewTableFields extraction. |
| JSX renderer | PreviewInvoiceTable component | not in first step | HIGH | Rendering is heavily coupled to CSS/classes and should be a later component split. |

## 7. 의존 방향
권장:
- previewTableBuilder.ts may import ocrResultFormatters.ts
- previewTableBuilder.ts may import invoiceTableDisplay.ts only if it computes structured cols; first step can avoid this
- cleanJsonBuilder.ts remains Clean JSON output-only
- markdownReportBuilder.ts remains Markdown output-only
- OcrResultPanel.tsx remains the owner of React state, useMemo, JSX rendering, copy/export UI

피해야 할 방향:
- previewTableBuilder.ts importing React or OcrResultPanel
- previewTableBuilder.ts importing cleanJsonBuilder.ts or markdownReportBuilder.ts
- cleanJsonBuilder.ts <-> previewTableBuilder.ts circular dependency
- TestWorkspace.tsx included in this extraction scope

## 8. Fixture / Check 전략
- Preview table data helper가 `previewTableFields` 수준을 넘어서면 `tmp/fixtures/preview_table_v1` 별도 fixture를 먼저 만드는 것을 권장한다.
- 거래명세서 `trade_1~trade_7`은 구조화 tableRows/column order/rowIndex 검증에 적합하다.
- `field.value` fallback과 `table_data` legacy 경로는 별도 synthetic fixture가 필요하다.
- Clean JSON fixture는 API 케이스 커버리지에는 도움이 되지만 Preview fallback displayRows까지 보장하지는 못한다.

## 9. 위험도 평가
| risk | likelihood | impact | mitigation | fixture/check |
| --- | --- | --- | --- | --- |
| Preview JSX and data builder are coupled | MEDIUM | MEDIUM | First extract only previewTableFields pure data list; leave JSX in component. | True |
| legacy table_data / field.value fallback omitted | MEDIUM | HIGH | Add synthetic legacy fallback fixture before broad extraction. | True |
| rowIndex policy regression | LOW | HIGH | Keep rowIndex in buildInvoicePreviewCols; preview builder should consume cols, not recalculate policy. | True |
| docTableDisplayCols not passed to structured renderer | MEDIUM | HIGH | Contract explicitly requires cols from OcrResultPanel useMemo. | True |
| Clean JSON and Preview column order diverge | LOW-MEDIUM | HIGH | Both must continue using same docTableDisplayCols. | True |
| Custom/Validation behavior changes accidentally | MEDIUM | MEDIUM | Do not move shared parseTableField or structured JSX branches in first extraction. | False |
| History/TestWorkspace policy divergence | LOW | MEDIUM | Reference only in this stage; do not include in extraction scope. | False |

## 10. Typecheck / Build
| command | status | exit | seconds |
| --- | --- | ---: | ---: |
| npm run typecheck | PASS | 0 | 2.211 |
| npm run build | PASS | 0 | 16.028 |

Known stderr noise:
- ISSUE-FRONTEND-BUILD-LOG-1: `ESLint: nextVitals is not iterable` observed = `True`

## 11. 다음 작업 제안
1. FRONTEND-CLEANUP-3B는 `buildPreviewTableFields` 수준의 순수 데이터 helper만 추출한다.
2. JSX renderer와 Custom/Validation 구조화 table branch는 건드리지 않는다.
3. 더 넓은 추출 전에는 Preview table v1 fixture를 별도 생성한다.
4. TestWorkspace 정리는 이번 라인에 포함하지 않고 별도 사용자 확인 후 진행한다.
