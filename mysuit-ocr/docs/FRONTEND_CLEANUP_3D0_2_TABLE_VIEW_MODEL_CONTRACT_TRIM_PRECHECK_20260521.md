# FRONTEND CLEANUP 3D0-2 TABLE VIEW MODEL CONTRACT TRIM PRECHECK 20260521

## 1. 사용 도구와 모델
- 사용 도구: Codex
- 사용 모델: Codex
- 작업명: `CODEX_FRONTEND_CLEANUP_3D0_2_TABLE_VIEW_MODEL_CONTRACT_TRIM_PRECHECK_NO_PROD_MODIFY`

## 2. 코드 수정 여부
- 운영 코드 수정 없음.
- helper 생성 없음.
- fixture 생성 없음.
- `OcrResultPanel.tsx`, `cleanJsonBuilder.ts`, `markdownReportBuilder.ts`, `ocrResultFormatters.ts`, `invoiceTableDisplay.ts`, `TestWorkspace.tsx` 수정 없음.
- 생성 파일은 tmp 분석 스크립트와 docs 리포트뿐이다.

## 3. 3D0 Output Field별 Trim 판단
| field | deriveFrom | commonData | displayPolicy | customNeed | recommendation | reason |
| --- | --- | --- | --- | --- | --- | --- |
| columns.key | displayCols[].key | True | False | yes | include | primary column identity and rowIndex/column-order baseline |
| columns.label | displayCols[].labelKo | True | False | yes | include | header label needed by all structured table branches |
| columns.index | columns array index | False | False | no | exclude | derivable and brittle in fixture |
| columns.align | _invoiceDataAlign(col.key) | False | True | textarea style only | exclude | renderer/style policy; can be added by later display policy helper |
| columns.width | _invoiceColWidth(col.key) | False | True | colgroup style | exclude | style policy likely to change independently |
| columns.isNumeric | _NUM_KEYS.has(key) | False | True | nowrap/style | exclude | classification only supports style, not core data |
| columns.isIndex | _IDX_KEYS.has(key) | False | True | nowrap/style | exclude | avoid confusion with actual rowIndex data column |
| rows.rowIndex | rows array index | False | False | row index available in map | exclude | derive from array position and avoid naming collision |
| rows.sourceRow | input rows[n] | False | False | not needed; editRows uses row index + key | exclude | would bloat fixtures and duplicate raw OCR values |
| cells.key | column key | True | False | yes | include | cell identity for edit overlay and assertions |
| cells.label | columns.label by key/index | False | False | no | exclude | derive from columns; avoid repeated labels per cell |
| cells.value | normalizeTableCell(row[key]) | True | False | textarea base value | include | normalized canonical cell value before empty display replacement |
| cells.displayValue | value or emptyValue | True | False | optional display | include | captures '-' behavior without renderer logic |
| cells.isEmpty | value === '' / meaningless | True | False | useful | include | small stable semantic flag |
| cells.align | _invoiceDataAlign(key) | False | True | style | exclude | same reason as columns.align |
| cells.rowIndex | rows array index | False | False | no | exclude | derive from row array |
| cells.columnIndex | cells array index | False | False | no | exclude | derive from cell array |
| meta.rowCount | rows.length | True | False | summary | include | cheap and useful manifest/body sanity |
| meta.columnCount | columns.length | True | False | summary | include | cheap and useful fixture sanity |
| meta.hasRows | rows.length > 0 | True | False | yes | include | clear guard for empty state |
| meta.hasColumns | columns.length > 0 | True | False | yes | include | clear guard for empty state |
| meta.hasEmptyCells | cells.some(isEmpty) | False | False | not currently used | exclude | derive easily; avoid fixture churn |

## 4. align / width / isNumeric / isIndex 판단
- 결정: `exclude_from_v1_contract`
- 근거: _invoiceColWidth/_invoiceDataAlign are shared today but are style policy, not shared data. Keep them in renderer/display policy for now.
- `_invoiceColWidth`, `_invoiceDataAlign`, `_NUM_KEYS`, `_IDX_KEYS`는 현재 세 탭에서 비슷하게 쓰이지만 렌더링 style/nowrap 정책이다.
- 1차 view model fixture에는 넣지 않고, 나중에 renderer/display policy helper에서 다루는 편이 안전하다.

## 5. sourceRow 필요성 판단
- 결정: `exclude`
- 근거: Custom edit write-back uses row index + col key; sourceRow duplicates raw input and bloats fixture.

## 6. cells.label / index 중복성 판단
- cells.label: exclude; derive from columns
- indices: exclude; derive from array positions and avoid rowIndex naming collision

## 7. meta.hasEmptyCells 판단
- 결정: `exclude`
- 근거: derive from rows[].cells[].isEmpty; not currently used as UI input

## 8. 최종 추천 Contract
선택: `candidate_1_minimal`

### Input
```ts
type BuildStructuredTableViewModelInput = {
  rows: ReadonlyArray<Record<string, unknown>>;
  displayCols: ReadonlyArray<{
    key: string;
    labelKo: string;
  }>;
  emptyValue?: string; // default "-"
};
```

### Output
```ts
type StructuredTableViewModel = {
  columns: Array<{
    key: string;
    label: string;
  }>;
  rows: Array<{
    cells: Array<{
      key: string;
      value: string;
      displayValue: string;
      isEmpty: boolean;
    }>;
  }>;
  meta: {
    rowCount: number;
    columnCount: number;
    hasRows: boolean;
    hasColumns: boolean;
  };
};
```

제외 그룹:
- displayPolicy: align, width, isNumeric, isIndex
- derivedIndexes: columns.index, rows.rowIndex, cells.rowIndex, cells.columnIndex
- duplicates: cells.label
- rawDuplication: rows.sourceRow
- derivedMeta: meta.hasEmptyCells

## 9. Clean JSON Fixture 재사용 가능성 재판단
판정: **Clean JSON fixture는 보조 baseline으로만 사용하고 table_view_model_v1 fixture는 별도 필요**

보조 재사용:
- ordered values
- rowIndex/column key baseline
- trade_3 locked behavior cross-check

별도 fixture가 필요한 이유:
- trim 후에도 columns가 추가된다.
- trim 후에도 cells/displayValue/isEmpty가 추가된다.
- trim 후에도 meta가 추가된다.
- Clean JSON rows는 object rows이고 view model rows는 cells array다.

## 10. 3D-1 Fixture Lock 지시안
- 위치: `tmp/fixtures/table_view_model_v1/`
- 대상: trade_1, trade_2, trade_3, trade_4, trade_5, trade_6, trade_7
- 본문 shape: StructuredTableViewModel only; metadata goes to manifest.json
- equality: deep equality on trimmed view model JSON
- fixture에 넣지 않을 것: align, width, style, sourceRow, indices, cells.label, hasEmptyCells
- rowIndex 확인: check columns.some(c.key === 'rowIndex') for include/exclude cases
- 거래_3 확인: record whether columns include insuranceCode/amount and preserve current behavior

## 11. 3D-2 Helper Extraction 지시안
- helper: `buildStructuredTableViewModel`
- 후보 파일: `src/lib/structuredTableViewModel.ts`
- 제외: legacy fallback, mode, custom edits, validation decoration, React/DOM/localStorage/network, input mutation
- 적용: Prefer helper extraction + direct runner first; OcrResultPanel adoption may be same step only if fixture runner passes and diff remains tiny.

## 12. Typecheck / Build
| command | status | exit | seconds |
| --- | --- | ---: | ---: |
| npm run typecheck | PASS | 0 | 2.322 |
| npm run build | PASS | 0 | 17.606 |

Known stderr noise:
- ISSUE-FRONTEND-BUILD-LOG-1: `ESLint: nextVitals is not iterable` observed = `True`

## 13. 다음 작업 제안
1. 3D-1에서 trimmed contract 기준으로 `table_view_model_v1` fixture lock을 만든다.
2. 3D-2에서 `buildStructuredTableViewModel` helper를 생성한다.
3. helper direct runner에서 trimmed fixture deep equality를 검증한다.
4. align/width/style 공통화는 renderer 단계까지 보류한다.
