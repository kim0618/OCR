# FRONTEND-CLEANUP-3D-3 — Apply buildStructuredTableViewModel to OcrResultPanel Preview structured table only

## 1. 사용 도구와 모델
- 사용 도구: Claude Code
- 사용 모델: claude-opus-4-7 (Opus 4.7)
- 작업명: `FRONTEND-CLEANUP-3D3 Apply buildStructuredTableViewModel to OcrResultPanel Preview structured table only`
- 작업 일자: 2026-05-21

## 2. 작업 목적
3D-2에서 생성/검증 완료된 `buildStructuredTableViewModel`을 OcrResultPanel.tsx의 **Preview 구조화 table 렌더링에만** 적용. Custom / Validation / legacy fallback / Clean JSON / Markdown / TestWorkspace 무수정. UI 출력은 fixture가 보장하는 8개 케이스에서 동일.

## 3. 백업 파일
- `mysuit-ocr/backup/OcrResultPanel_20260521_before_FRONTEND_CLEANUP_3D3_APPLY_STRUCTURED_TABLE_VIEW_MODEL_PREVIEW_ONLY.tsx` (1649 lines, 3D-3 직전 원본)

## 4. 수정 파일
- `mysuit-ocr/src/components/upload/OcrResultPanel.tsx` — **유일한 수정 대상**
  - 1649 lines → 1648 lines (−1)
  - 변경 핵심 3곳: import 1줄 추가, useMemo 1개 (11줄) 추가, Preview structured table JSX 블록 교체 (들여쓰기 조정 포함)
- 기타 운영 파일 / helper / fixture / backend / TestWorkspace 전부 **미수정**

## 5. 적용 범위 (변경된 것)
1. **import**: `import { buildStructuredTableViewModel } from "@/lib/structuredTableViewModel";` 추가
2. **`previewStructuredTableViewModel` useMemo 신규**: `docTableDisplayCols` 정의 바로 다음에 위치. 입력 `{rows: docTableRows, displayCols: docTableDisplayCols, emptyValue: "-"}`, deps `[docTableRows, docTableDisplayCols]`. `docTableRows`/`docTableDisplayCols`가 비어있으면 `null` 반환
3. **Preview structured table JSX 교체** (`tableIdx === 0 && previewStructuredTableViewModel` 분기):
   - 외부 가드: `docTableRows && docTableDisplayCols` + `finalDisplayCols.length > 0` → `previewStructuredTableViewModel` 단일 조건 (`null` 가드가 모두 흡수)
   - 헤더 iteration: `finalDisplayCols.map((col))` → `viewModel.columns.map((column))`
   - 헤더 텍스트: `col.labelKo` → `column.label` (helper의 `labelKo || key` fallback)
   - secondary 표시 조건: `col.labelKo !== col.key` → `column.label !== column.key`
   - body iteration: `docTableRows.map((row, ri))` → `viewModel.rows.map((row, ri))`
   - cell iteration: `finalDisplayCols.map((col))` → `row.cells.map((cell))`
   - cell 텍스트: `normalizeCell(row[col.key]) || "-"` → `cell.displayValue`
   - row count: `docTableRows.length` → `viewModel.meta.rowCount` (값 동일, 단일 source of truth)
   - colgroup width / cell align / NUM/IDX whitespace 등 Preview-specific style 정책은 그대로 inline 유지 (cell.key 기반)

## 6. 적용하지 않은 범위 (미변경)
- **Custom 탭 JSX** (line 1293 근방 `UI-CUSTOM-1` 마커): `docTableRows` / `docTableDisplayCols` / `customTableEdits` 직접 사용 유지. textarea 편집 로직 그대로
- **Validation 탭 JSX** (line 1515 근방 `UI-VALIDATION-1` 마커): `docTableRows` / `docTableDisplayCols` 직접 사용 유지. status/confidence/adoption UI 그대로
- **legacy parseTableField fallback** (Preview 같은 map 내부 `// Fallback: raw displayRows`): `previewTableFields.displayRows` 기반 렌더링 그대로
- **Clean JSON / Markdown 생성 경로**: `buildCleanJsonResult` / `buildMarkdownReport` 호출 그대로
- **TestWorkspace.tsx, DetailHistoryView.tsx, invoiceTableDisplay.ts, cleanJsonBuilder.ts, markdownReportBuilder.ts, ocrResultFormatters.ts, structuredTableViewModel.ts** — 모두 unchanged
- **backend / templates / GT / fixture** — 미수정

## 7. Preview structured table 변경 요약
**시각적 출력**: 8개 fixture 케이스 (trade_1~7 + synthetic_empty_rows)에서 helper 출력은 fixture와 byte-identical 일치 → Preview 렌더 결과도 동일.

**잠재 미세 정규화 차이** (의도된 unification):
- 변경 전: 셀 텍스트 = `normalizeTableCell(row[col.key]) || "-"`
  - `normalizeTableCell` (invoiceTableDisplay): zero-width chars strip + Unicode dash `[–—−－―]` → `-` + trim
- 변경 후: 셀 텍스트 = `cell.displayValue` = `normalizeStructuredTableCell(row[col.key])` (empty 시 `"-"`)
  - `normalizeStructuredTableCell` (structuredTableViewModel): Unicode dash `[‐‑‒–—−]` (U+2010~2014, U+2212) → `-` + trim
- **차이점**:
  - 변경 후는 zero-width chars를 strip하지 않음 (현재 OCR 결과에서는 zero-width 미관측 → fixture PASS)
  - Unicode dash 집합이 다름 (변경 전: U+2013/2014/2212 + U+FF0D fullwidth/U+2015 horizontal bar; 변경 후: U+2010/2011/2012/2013/2014/2212). 실제 fixture data에는 양쪽 모두 미관측 → fixture PASS
- 향후 OCR 출력에 zero-width 문자나 fullwidth/horizontal bar dash가 나타나면 Preview 출력이 약간 달라질 수 있음. **3C precheck의 "시나리오 2" — 세 탭의 정규화가 미묘하게 다르던 부분이 helper로 일원화되는 의도된 변화**. fixture가 catch하지 못하는 영역.

## 8. Custom / Validation 미수정 확인
diff 전체에서 `UI-CUSTOM-1` / `UI-VALIDATION-1` 마커가 있는 라인 변경 0건. Custom의 `customTableEdits`, Validation의 GT 비교 / status 배지 로직 모두 그대로.

검증 명령:
```bash
diff -u backup/...3D3...tsx src/components/upload/OcrResultPanel.tsx | grep -E "UI-CUSTOM|UI-VALIDATION|Fallback: raw|parseTableField"
```
결과: 0 matches (Codex 추가 주석 1개 제외 — `// Custom / Validation / legacy fallback are intentionally NOT migrated yet`).

## 9. legacy fallback 미수정 확인
Preview JSX 같은 map 내부의 `// Fallback: raw displayRows (기존 동작)` 블록은 들여쓰기/내용 전부 그대로. `previewTableFields.displayRows.map(...)` + `cell.confidence < 0.7` 표시 / `cell.value || "-"` 모두 unchanged.

`parseTableField` import / 사용처 (Preview previewTableFields, Custom 1451, Validation 1583)도 모두 unchanged.

## 10. rowIndex 정책 확인
- 거래_1 / 거래_4 / 거래_5 / 거래_7: `rowIndex` 컬럼 제외 — view model runner 8/8 PASS로 검증
- 거래_2 / 거래_3 / 거래_6: `rowIndex` 컬럼 포함 — view model runner 8/8 PASS로 검증
- helper는 `displayCols` 순서를 그대로 따르므로 정책 결정자(`buildInvoicePreviewCols`)에 의존. helper 자체가 정책을 깰 여지 없음
- Preview JSX는 이제 `viewModel.columns` (= helper가 정렬한 displayCols)를 그대로 사용 → 정책 100% 보존

## 11. 거래_3 locked behavior 확인
- 거래_3 view model output에 `insuranceCode` (value=`669700020`), `amount` (value=`301,320`) 컬럼 포함 — runner의 `trade3LockedBehaviorPass = true`
- Preview JSX가 view model을 그대로 렌더링하므로 사용자 화면에도 동일하게 표시
- LOCKED 보존: pass-through 구조이므로 정책 자동 보존

## 12. table_view_model fixture runner 결과
- 실행: `node tmp/check_table_view_model_v1_fixtures_js.mjs`
- 결과: **overall PASS, 8/8 PASS, totalDiffs=0, totalForbiddenHits=0**
- 모든 case: trade_1 / 2 / 3 / 4 / 5 / 6 / 7 / synthetic_empty_rows PASS, diffs=0, forbidden=0
- purity check: reactHookFree / noBrowserOrNetworkAccess / noUiResponsibility / inputMutationFree 모두 PASS

## 13. Clean JSON runner 결과
- 실행: `node tmp/check_clean_json_v1_fixtures_js.mjs`
- 결과: **9/9 PASS, totalDiffs=0**
- Preview structured table 변경이 Clean JSON 생성 경로에 영향 없음 확인
- Runner 자체적으로 typecheck/build도 실행 (PASS)

## 14. Markdown runner 결과
- 실행: `python tmp/codex_markdown_contract_fixture_lock.py --check --phase post_3D3_20260521`
- 결과: **overall PASS, counts={'PASS': 6}**
- Markdown 출력 회귀 없음 (processing_time 정규화 정책 유지)
- 리포트: `docs/MARKDOWN_V1_FIXTURE_CHECK_post_3D3_20260521_20260521.{md,json}`

## 15. typecheck / build 결과
| command | status | exit |
| --- | --- | --- |
| `npm run typecheck` | PASS | 0 |
| `npm run build` | PASS | 0 |

build 결과:
- ✓ Compiled successfully in 2.4s
- ✓ Generating static pages (18/18)
- `/runocr` size: **65.3 kB → 65.6 kB (+0.3 kB)** — helper가 처음으로 컴포넌트에 import됨에 따른 자연스러운 증가
- First Load JS shared: 102 kB (unchanged)

## 16. known stderr noise 기록
- ID: `ISSUE-FRONTEND-BUILD-LOG-1`
- 메시지: `⨯ ESLint: nextVitals is not iterable`
- 발생: `npm run build` stderr, exit code 0과 동시
- 이번 작업과 인과 관계 없음 (CLEANUP-1 / 2A / 2B / 3D-1 / 3D-2부터 이미 관찰)

## 17. 남은 이슈
1. **시각적 regression risk** — 8개 fixture는 PASS이지만, **manual smoke 테스트 미실시**. 실제 브라우저에서 `/runocr` 열어 인보이스 업로드 후 Preview 탭의 표가 fixture와 동일하게 나오는지 직접 확인 권장 (3C에서 사용자에게 안내한 시각적 unification 점검)
2. **Custom / Validation 미적용** — 같은 데이터를 다른 코드 경로로 렌더링하는 중복 유지. 만약 Custom/Validation도 view model로 migrate한다면 별도 cycle 필요 (Custom textarea 편집 wrapper / Validation status UI를 view model output 위에서 별도 처리)
3. **legacy `parseTableField(field.value)` fallback 미커버** — structured table 전용. 별도 `buildLegacyTableViewModel` 분리 cycle로 미룸
4. **`ISSUE-FRONTEND-BUILD-LOG-1`** — stderr noise 별도 추적
5. **bundle 영향 +0.3 kB** — Preview만 적용한 결과. Custom/Validation까지 통합되면 그 부분이 view model 호출로 단순화되어 일부 상쇄 가능

## 18. 다음 작업 제안
1. **(권장 우선) Manual smoke 테스트 1회** — `npm run dev` 후 `/runocr`에서 인보이스 1~2개 업로드, Preview 탭 표 시각 확인. UI 회귀 없는지 30초 점검. 안정성 확인되면 cycle 1 close-out으로 진행
2. **OcrResultPanel cleanup cycle 1 close-out 리포트** — 그간 완료된 작업 (Clean JSON, Markdown, ocrResultFormatters, structuredTableViewModel, Preview adoption) / 의도적으로 보류한 작업 (Custom/Validation/legacy fallback/2C) / 재개 트리거 조건 정리. cycle 1 마감 신호
3. **Custom / Validation view model 통합 (cycle 2 후보)** — 사용자가 통합을 원하면 별도 precheck 후 진행. Custom textarea 편집 wrapper와 Validation status UI를 view model 위에서 어떻게 처리할지 별도 contract 필요
4. **legacy `parseTableField` fallback view model (`buildLegacyTableViewModel`)** — 별도 cycle (3E 또는 cycle 2 일부)
5. **TestWorkspace 정리** — 운영 cycle 1 close-out 후 사용자 재확인을 받고 진행 (메모리에 deferred로 기록됨)
6. **`ISSUE-FRONTEND-BUILD-LOG-1`** — `eslint-config-next` 호환 점검 (작은 별도 task)
