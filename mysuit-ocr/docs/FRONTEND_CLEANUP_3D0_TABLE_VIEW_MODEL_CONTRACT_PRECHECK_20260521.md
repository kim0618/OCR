# FRONTEND CLEANUP 3D0 TABLE VIEW MODEL CONTRACT PRECHECK 20260521

## 1. 사용 도구와 모델
- 사용 도구: Codex
- 사용 모델: Codex
- 작업명: `CODEX_FRONTEND_CLEANUP_3D0_TABLE_VIEW_MODEL_CONTRACT_PRECHECK_NO_PROD_MODIFY`

## 2. 코드 수정 여부
- 운영 코드 수정 없음.
- helper 생성 없음.
- fixture 생성 없음.
- `OcrResultPanel.tsx`, `cleanJsonBuilder.ts`, `markdownReportBuilder.ts`, `ocrResultFormatters.ts`, `invoiceTableDisplay.ts`, `TestWorkspace.tsx` 수정 없음.
- 생성 파일은 tmp 분석 스크립트와 docs 리포트뿐이다.

## 3. 현재 Structured Table 입력 분석
- `docTableRows`: `result.document_fields.tableRows`에서 온 `Record<string, unknown>[]`.
- `docTableMeta`: `result.document_fields.tableMeta`.
- `docTableDisplayCols`: `buildInvoicePreviewCols(docTableMeta, docTableRows)` 결과.
- rowIndex/column order/internal key filtering은 helper 입력 전 `docTableDisplayCols`에 반영되어 있다.
- `customTableEdits`는 Custom tab textarea 값 전용이며 base view model에는 넣지 않는 것이 안전하다.
- Validation status/adoption/confidence는 table wrapper decoration이며 base view model 책임이 아니다.

## 4. Clean JSON vs Table View Model
판정: **기존 Clean JSON fixture 일부 재사용 가능하지만 table_view_model_v1 fixture 별도 필요**

Clean JSON fixture는 ordered row 값과 rowIndex/column key baseline에는 일부 재사용 가능하다. 하지만 view model은 `columns`, `cells`, `displayValue`, `isEmpty`, `align`, `width`, `meta`가 필요하므로 별도 fixture가 필요하다.

## 5. Helper Name 후보
| name | pros | cons | recommendation |
| --- | --- | --- | --- |
| buildStructuredTableViewModel | 좁고 명확하다. docTableRows + displayCols 구조화 테이블 전용이라는 현재 1차 범위와 잘 맞는다. | 거래명세서 전용 정책이 숨어 보일 수 있다. | RECOMMENDED |
| buildOcrTableViewModel | 향후 범용 OCR table 모델까지 확장하기 좋다. | 현재 단계에는 범위가 넓고 legacy fallback까지 포함해야 할 것처럼 보인다. | NO |
| buildTableRowsViewModel | rows 변환 책임을 드러낸다. | columns/cells/meta까지 담는 output과 이름이 조금 맞지 않는다. | MAYBE |
| buildInvoiceStructuredTableViewModel | 거래명세서 rowIndex/column policy와 결합되어 있음을 명확히 한다. | helper가 displayCols만 받는다면 invoice 전용 이름이 과하게 좁다. | MAYBE_LATER |

추천 이름: **buildStructuredTableViewModel**

## 6. Input Contract
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

결정:
- `tableMeta`는 넣지 않는다. 이미 `displayCols`에 정책이 반영되어 있기 때문이다.
- `mode`는 1차 helper에 넣지 않는다.
- `customTableEdits`는 caller가 overlay한다.
- validation/adoption/confidence decoration은 caller가 처리한다.
- legacy fallback은 포함하지 않는다.

## 7. Output Contract
```ts
type StructuredTableColumn = {
  key: string;
  label: string;
  index: number;
  align: "left" | "center" | "right";
  width: string;
  isNumeric: boolean;
  isIndex: boolean;
};

type StructuredTableCell = {
  key: string;
  label: string;
  value: string;
  displayValue: string;
  isEmpty: boolean;
  align: "left" | "center" | "right";
  columnIndex: number;
  rowIndex: number;
};

type StructuredTableRow = {
  index: number;
  sourceRow: Record<string, unknown>;
  cells: StructuredTableCell[];
};

type StructuredTableViewModel = {
  columns: StructuredTableColumn[];
  rows: StructuredTableRow[];
  meta: {
    rowCount: number;
    columnCount: number;
    hasRows: boolean;
    hasColumns: boolean;
    hasEmptyCells: boolean;
  };
};
```

출력에 포함하지 않을 것:
- React nodes
- JSX
- event handlers
- textarea callbacks
- validation status UI
- adoption badges
- source/original/debug UI
- OcrResultPanel state

## 8. Mode 포함 여부
- `mode: preview | custom | validation`은 1차 helper에 넣지 않는 것을 추천한다.
- 이유: mode를 넣으면 helper가 탭별 UI 정책을 알게 되어 복잡해진다.
- base view model을 만든 뒤 Preview/Custom/Validation이 decoration을 붙이는 구조가 안전하다.

## 9. Legacy Fallback 포함 여부
- 1차 helper는 structured table 전용으로 둔다.
- `parseTableField(field.value)` fallback은 shape가 다르므로 추후 `buildLegacyTableViewModel` 후보로 분리한다.

## 10. Fixture 필요성 판단
판정: **Clean JSON fixture + table_view_model_v1 fixture 병행**
- 새 fixture 필요: `True`
- 후보 위치: `tmp/fixtures/table_view_model_v1/`
- 추천 대상: trade_1, trade_2, trade_3, trade_7
- runner: Node/TS helper direct runner after helper extraction; fixture lock can be generated from current OcrResultPanel-derived inputs before extraction.

## 11. 3D 작업 분해안
| step | description | recommendation |
| --- | --- | --- |
| 3D-1 table_view_model_v1 fixture lock | current structured table inputs/output contract 기준 JSON fixture 생성 | DO_FIRST |
| 3D-2 buildStructuredTableViewModel helper extraction | src/lib helper 생성 후 OcrResultPanel에서 structured table rows/cells 모델만 사용 | DO_SECOND |
| 3D-3 view model direct runner | helper를 직접 import해 fixture와 deep equality 비교 | DO_WITH_OR_AFTER_3D2 |
| 3D-4 OcrResultPanel 적용 확대 | Preview/Custom/Validation에서 view model 사용 범위 확대 | LATER |

## 12. Close-out 타이밍
- 지금 close-out 생성: `False`
- 권장: 3D contract -> fixture -> helper extraction -> direct runner 이후 close-out 생성 권장
- 이유: 지금 close-out하면 table view model 결과가 빠져 cleanup cycle 판단이 덜 닫힌다.

## 13. Typecheck / Build
| command | status | exit | seconds |
| --- | --- | ---: | ---: |
| npm run typecheck | PASS | 0 | 2.395 |
| npm run build | PASS | 0 | 16.272 |

Known stderr noise:
- ISSUE-FRONTEND-BUILD-LOG-1: `ESLint: nextVitals is not iterable` observed = `True`

## 14. 다음 작업 제안
1. 3D-1에서 `table_view_model_v1` fixture lock을 먼저 만든다.
2. 3D-2에서 `buildStructuredTableViewModel` helper를 추출한다.
3. 3D-3에서 helper direct runner로 fixture deep equality를 검증한다.
4. 3D 완료 후 OcrResultPanel cleanup cycle close-out 문서를 생성한다.
