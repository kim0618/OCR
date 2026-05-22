# FRONTEND-CLEANUP-3D-2 — buildStructuredTableViewModel helper extraction with direct fixture runner

## 1. 사용 도구와 모델
- 사용 도구: Claude Code
- 사용 모델: claude-opus-4-7 (Opus 4.7, 1M context)
- 작업명: `FRONTEND-CLEANUP-3D2 buildStructuredTableViewModel helper extraction with direct fixture runner`
- 작업 일자: 2026-05-21

## 2. 작업 목적
- `table_view_model_v1` input/output fixture를 기준으로 `buildStructuredTableViewModel` 순수 helper 생성.
- 신규 JS direct runner로 input fixture → helper → expected output fixture **deep equality** 검증.
- **OcrResultPanel.tsx 미적용** — helper standalone 검증까지만. Preview/Custom/Validation JSX 무수정.
- TestWorkspace.tsx도 미수정.

## 3. 코드 수정 여부
- 운영 컴포넌트 / 기존 helper / backend / template / GT / fixture 모두 **미수정**.
- 신규 helper와 runner만 생성. OcrResultPanel.tsx, TestWorkspace.tsx, cleanJsonBuilder.ts, markdownReportBuilder.ts, ocrResultFormatters.ts, invoiceTableDisplay.ts — 모두 unchanged.
- 기존 8개 fixture 파일 (manifest + 7 output + 1 synthetic + 8 input) 해시 변경 없음.

## 4. 생성 파일
- `mysuit-ocr/src/lib/structuredTableViewModel.ts` (130 lines) — 신규 helper
- `mysuit-ocr/tmp/check_table_view_model_v1_fixtures_js.mjs` (~270 lines) — 신규 JS direct runner
- `mysuit-ocr/docs/FRONTEND_CLEANUP_3D2_STRUCTURED_TABLE_VIEW_MODEL_HELPER_20260521.md` (이 문서)
- `mysuit-ocr/docs/FRONTEND_CLEANUP_3D2_STRUCTURED_TABLE_VIEW_MODEL_HELPER_20260521.json`
- `mysuit-ocr/docs/FRONTEND_CLEANUP_3D2_RUNNER_RESULT_20260521.json` (runner가 자체 생성하는 머신 판독용 결과)

부수 산출 (regression check가 갱신):
- `mysuit-ocr/docs/FRONTEND_CLEANUP_1B_JS_CLEAN_JSON_FIXTURE_RUNNER_20260521.{md,json}` — Clean JSON runner가 자체 자동 갱신 (시각만 변경)
- `mysuit-ocr/docs/MARKDOWN_V1_FIXTURE_CHECK_regression_3D2_20260521_20260521.{md,json}` — Markdown check report

로그:
- `ocr-server/logs/codex_FRONTEND_CLEANUP_3D2_STRUCTURED_TABLE_VIEW_MODEL_HELPER.{out,err}.log` (단일 쌍, 모든 단계 append)

## 5. helper input/output contract
입력 (`BuildStructuredTableViewModelInput`):
```ts
{
  rows: ReadonlyArray<Record<string, unknown>>;
  displayCols: ReadonlyArray<{ key: string; labelKo: string }>;
  emptyValue?: string;  // default "-"
}
```

출력 (`StructuredTableViewModel`):
```ts
{
  columns: Array<{ key: string; label: string }>;
  rows: Array<{ cells: Array<{ key: string; value: string; displayValue: string; isEmpty: boolean }> }>;
  meta: { rowCount: number; columnCount: number; hasRows: boolean; hasColumns: boolean };
}
```

## 6. isEmpty / value / displayValue rule (fixture에서 역추적 → Python re-impl로 교차 확인)
fixture 4쌍(trade_1/3/7 + synthetic_empty_rows)을 직접 열어 input vs output 패턴을 추출하고, `tmp/codex_table_view_model_fixture_lock.py`의 Python `normalize_cell` 구현으로 교차 확인했다.

**normalize 규칙** (`normalizeStructuredTableCell`):
- `null` / `undefined` → `""`
- 그 외 → `String(raw)` 변환 후:
  - Unicode dash 변종 (U+2010, U+2011, U+2012, U+2013, U+2014, U+2212) → ASCII `"-"`
  - leading / trailing whitespace `.trim()`
- 다른 문자(한글, 콤마, 괄호, 파이프 `|`, ASCII hyphen, 숫자 등)는 그대로 보존
- `isMeaningless` 매핑 없음 (Clean JSON의 `"-"`, `"n/a"`, `"null"` 등 empty 매핑은 view model에 적용 안 됨)

**per-cell 출력 규칙**:
- `value = normalizeStructuredTableCell(row[col.key])`
- `isEmpty = value === ""`
- `displayValue = isEmpty ? emptyValue : value`

**fixture 검증 근거**:
- trade_3 input `rowIndex: 1` (number) → output `value: "1"` (String 변환) ✓
- trade_1 input `manufacturingNo: ""` → output `value: ""`, `displayValue: "-"`, `isEmpty: true` ✓
- trade_4 input `unitPrice: "28,336.00"` → output `value: "28,336.00"` (comma + period 보존) ✓
- trade_3 input `manufacturer: "(주)에스피"` → 괄호 + 한글 그대로 보존 ✓
- trade_1 input `spec: "15m|*6포"` → 파이프 + 별표 그대로 보존 ✓
- synthetic_empty_rows input `rows: []` → output `rows: []`, `columns: [2개 유지]`, `meta.hasRows=false`, `meta.hasColumns=true` ✓

**column label 규칙**: `column.label = displayCol.labelKo || displayCol.key` (모든 fixture에 labelKo가 채워져 있어 fallback 자체는 발동되지 않음; helper는 안전한 fallback 보유).

## 7. helper 구현 요약
- 파일: `src/lib/structuredTableViewModel.ts` (130 lines)
- export: `buildStructuredTableViewModel`, 그리고 5개 타입 (`StructuredTableViewModel`, `StructuredTableViewModelCell`, `StructuredTableViewModelRow`, `StructuredTableViewModelColumn`, `StructuredTableViewModelMeta`, `StructuredTableInputCol`, `BuildStructuredTableViewModelInput`)
- 내부 private: `normalizeStructuredTableCell`, `UNICODE_DASH_PATTERN`, `DEFAULT_EMPTY_VALUE`
- 의존: 없음 (다른 `@/lib/*` import 없음 — 완전히 standalone)
- 순수성: React/DOM/storage/network/Blob/clipboard 없음, 입력 mutation 없음

## 8. runner 구현 요약
- 파일: `tmp/check_table_view_model_v1_fixtures_js.mjs` (~270 lines)
- 방식: **non-circular** — 3D-1.5의 `inputs/*.input.json`을 raw 입력으로, helper 실행, `*.view_model.json` expected output과 비교
- Clean JSON 1B의 fixture-derived synthesis circularity 한계가 없음 — 진짜 end-to-end
- import 방식: `typescript.transpileModule`로 helper를 임시 `tmp/.structured_table_view_model_runner_build/*.cjs`로 transpile, `require()`로 로드, 실행 후 임시 디렉토리 정리
- 검증 항목:
  1. **deep equality** (`diffValues`): expected vs actual 전체 비교 (path별 첫 50개 diff 누적)
  2. **ordered stringify equality** (key 순서까지 동일)
  3. **forbidden field 검사** (`findForbiddenFields`): output 어디에도 `align`, `width`, `style`, `isNumeric`, `isIndex`, `sourceRow`, `indices`, `hasEmptyCells`가 키로 나타나지 않음을 walk + assert. `rowIndex`는 column.key/cell.key 값으로는 허용, property name으로는 금지
  4. **rowIndex policy**: 거래_1/4/5/7 excluded, 거래_2/3/6 included
  5. **trade_3 LOCKED behavior**: `columns`에 `insuranceCode`와 `amount` 포함 확인
  6. **synthetic_empty_rows policy**: `rows.length=0`, `columns.length=2`, `meta.hasRows=false`, `meta.hasColumns=true`
  7. **purity check**: helper source에서 React import / DOM / storage / network / UI API 미발견 (주석은 strip 후 검사)
  8. **inputMutationFree**: helper 호출 전후 input stable stringify 비교
- fixture 파일은 절대 쓰지 않음 (read-only).

## 9. table_view_model fixture 8/8 결과
- 실행: `node tmp/check_table_view_model_v1_fixtures_js.mjs`
- 결과: **overall PASS, counts={'PASS': 8/8}, totalDiffs=0, totalForbiddenHits=0**
- 처음 1회 실행은 file system caching 이슈로 ENOENT 발생 → helper 파일 재작성 후 정상 동작 (로그에 기록).

| caseId | status | diffs | forbidden | rowIndexExp | rowIndexAct | trade3LockedPass | syntheticPass |
| --- | --- | --- | --- | --- | --- | --- | --- |
| trade_1_1jpg | PASS | 0 | 0 | excluded | excluded | n/a | n/a |
| trade_2_2pdf | PASS | 0 | 0 | included | included | n/a | n/a |
| trade_3_3pdf | PASS | 0 | 0 | included | included | true | n/a |
| trade_4_4pdf | PASS | 0 | 0 | excluded | excluded | n/a | n/a |
| trade_5_5pdf | PASS | 0 | 0 | excluded | excluded | n/a | n/a |
| trade_6_6pdf | PASS | 0 | 0 | included | included | n/a | n/a |
| trade_7_7pdf | PASS | 0 | 0 | excluded | excluded | n/a | n/a |
| synthetic_empty_rows | PASS | 0 | 0 | excluded | excluded | n/a | true |

## 10. rowIndex 정책 확인
- 거래_1 / 거래_4 / 거래_5 / 거래_7 모두 `rowIndex` 컬럼 제외 → PASS
- 거래_2 / 거래_3 / 거래_6 모두 `rowIndex` 컬럼 포함 → PASS
- helper는 displayCols 순서를 그대로 따르므로 rowIndex 정책 자체는 caller(buildInvoicePreviewCols)가 결정. helper는 정책 위반 가능성 없음.

## 11. 거래_3 locked behavior 확인
- columns에 `insuranceCode` / `amount` 포함 → PASS
- 값 검증: `insuranceCode=669700020`, `amount=301,320` (manifest manifest.lockedCurrentBehavior.values와 일치)
- helper는 displayCols + rows pass-through만 하므로 LOCKED 항목이 자동 보존됨.

## 12. synthetic_empty_rows 확인
- input: `rows=[]`, `displayCols=[itemName, quantity]`, `emptyValue="-"`
- output: `rows=[]`, `columns=[{itemName/품목명}, {quantity/수량}]`, `meta={rowCount:0, columnCount:2, hasRows:false, hasColumns:true}`
- → PASS (8/8의 마지막 case)
- helper의 edge handling: `rows.map(...)`이 빈 배열이면 `outputRows=[]`, columns는 displayCols 기반으로 유지됨 (별도 분기 불필요한 자연 동작)

## 13. forbidden field check 결과
- output 8개 모두 forbidden 필드 0건.
- 검사 대상: `align`, `width`, `style`, `isNumeric`, `isIndex`, `sourceRow`, `indices`, `hasEmptyCells`, 그리고 `rowIndex`가 property name으로 나타나는지
- `rowIndex`는 column.key/cell.key 값으로만 나타남 (trade_2/3/6의 첫 column) — 허용된 사용처

## 14. Clean JSON runner 결과 (회귀 검증)
- 실행: `node tmp/check_clean_json_v1_fixtures_js.mjs`
- 결과: **9/9 PASS, total diffs 0** (trade_1~7 + tpl_003_1/2)
- Clean JSON 출력 회귀 없음 — view model helper 추가가 Clean JSON에 영향 없음 확인.
- Runner는 자체 typecheck/build도 실행 (둘 다 PASS, 시각만 reports에 갱신).

## 15. Markdown runner 결과 (회귀 검증)
- 실행: `python tmp/codex_markdown_contract_fixture_lock.py --check --phase regression_3D2_20260521`
- 결과: **6/6 PASS** (trade_1/2/3/7 + tpl_003_1/2)
- Markdown 출력 회귀 없음 — view model helper 추가가 Markdown 생성에 영향 없음 확인.
- processing_time 정규화 정책(기존)대로 적용.

## 16. typecheck / build 결과
| command | status | exit |
| --- | --- | --- |
| `npm run typecheck` | PASS | 0 |
| `npm run build` | PASS | 0 |

build 결과:
- ✓ Compiled successfully in 2.3s
- ✓ Generating static pages (18/18)
- `/runocr` size: **65.3 kB (unchanged)** — helper가 아직 OcrResultPanel에 적용되지 않아 bundle 영향 없음
- First Load JS shared: 102 kB (unchanged)
- 신규 helper(`structuredTableViewModel.ts`)는 import되지 않은 상태라 tree-shake됨

## 17. known stderr noise 기록
- ID: `ISSUE-FRONTEND-BUILD-LOG-1`
- 메시지: `⨯ ESLint: nextVitals is not iterable`
- 발생: `npm run build` stderr, exit code 0과 동시.
- 이번 작업과 인과 관계 없음. CLEANUP-1 / 2A / 2B / 3D-1에서도 동일하게 관찰됨.
- 별도 추적 권장.

부수 noise (초기 1회):
- runner 첫 실행 시 ENOENT (`structuredTableViewModel.ts`). file system caching 이슈로 추정. helper 재작성 후 정상 동작. err.log에 stacktrace 기록되어 있으나 실제 검증에는 영향 없음.

## 18. 남은 이슈
1. **OcrResultPanel 미적용** — helper와 runner는 완성됐으나 실제 Preview/Custom/Validation JSX는 helper를 아직 호출하지 않음. 3D-3에서 진행 예정.
2. **legacy `parseTableField(field.value)` fallback 미커버** — structured table 전용 helper. legacy fallback은 별도 `buildLegacyTableViewModel`로 분리 예정.
3. **거래_3 LOCKED columns** — `insuranceCode` / `amount` 그대로 유지. 정책 변경은 별도 task.
4. **`ISSUE-FRONTEND-BUILD-LOG-1`** — 별도 추적.
5. **helper 미사용으로 bundle 영향 0** — 3D-3 적용 후 bundle 크기 약간 증가 예상 (`+1~2 kB`).

## 19. 다음 작업 제안
1. **3D-3 OcrResultPanel 적용 precheck / extract** — Preview / Custom / Validation JSX 중 어디까지 helper를 연결할지 별도 작은 적용 작업 권장:
   - 가장 좁은 범위: Preview 구조화 table 렌더링만 view model 경유
   - 중간: Preview + Validation (둘 다 read-only)
   - 최대: Preview + Custom + Validation (Custom textarea 편집 wrapper는 helper output 위에서 별도 처리)
   - precheck로 각 tab의 JSX cell 렌더 코드와 helper output의 mapping 차이를 enumerate 후 결정
2. **OcrResultPanel cleanup cycle 1 close-out 리포트** — 3D-3 적용 후가 적절. cycle 1 완료/보류/재개 조건 정리.
3. **legacy `parseTableField` fallback view model 분리** — 별도 cycle (3E?)로 진행 권장.
4. **TestWorkspace 진입 여부** — 운영 cycle 1 close-out 후 사용자 재확인.
5. **`ISSUE-FRONTEND-BUILD-LOG-1`** — `eslint-config-next` 호환 점검 (작은 별도 task).
