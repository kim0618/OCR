# FRONTEND-CLEANUP-2B — toMarkdown helper extraction with Markdown fixture check runner

## 1. 사용 도구와 모델
- 사용 도구: Claude Code
- 사용 모델: claude-opus-4-7 (Opus 4.7, 1M context)
- 작업명: `FRONTEND-CLEANUP-2B toMarkdown helper extraction with Markdown fixture check runner`
- 작업 일자: 2026-05-21

## 2. 작업 목적
`OcrResultPanel.tsx` 내부 `toMarkdown` 로직과 공유 formatter(`fieldLabel`, `fieldLabelFull`, `getAdoptionLabel`, `isAmountLikeField`, `parseTableField`)를 순수 helper로 분리한다. Markdown v1 출력은 fixture와 정확히 일치해야 한다 (단, OCR `processing_time` 라인만 비결정성이라 마스킹). 기능 변경이 아닌 구조 분리 작업.

핵심 boundary 원칙:
- `markdownReportBuilder.ts`는 Markdown 전용. Preview/Custom/Validation JSX는 이 파일을 import하지 않는다.
- 공유 formatter는 `ocrResultFormatters.ts`에 두고 Preview/Custom/Validation/markdown 모두 거기서 import한다.

## 3. 백업 파일 목록
- `mysuit-ocr/backup/OcrResultPanel_20260521_before_FRONTEND_CLEANUP_2B_MARKDOWN_BUILDER_EXTRACT.tsx` (1714 lines, pre-2B 원본)
- `mysuit-ocr/backup/codex_markdown_contract_fixture_lock_20260521_before_FRONTEND_CLEANUP_2B_CHECK_RUNNER.py`

## 4. 수정 파일 목록
- `mysuit-ocr/tmp/codex_markdown_contract_fixture_lock.py` — `--check`/`--phase`/`--check-report-*` 모드 추가, `deep_compare`성 함수 `compute_first_diff`, `check_fixtures`, `make_check_report_md` 추가, `_normalize_for_compare`로 processing_time 라인 마스킹, `CASES`에 `trade_7_7pdf` 추가. capture path는 unchanged.
- `mysuit-ocr/src/components/upload/OcrResultPanel.tsx` — local `fieldLabel`/`fieldLabelFull`/`getAdoptionLabel`/`isAmountLikeField`/`parseTableField`/`toMarkdown` 정의 제거, formatter import 교체, `toMarkdown`을 helper wrapper로 축소 (1714 → 1649 lines, −65). Preview/Custom/Validation/Raw JSON/Clean JSON/Copy/Export JSX 미수정.

## 5. 신규 파일 목록
- `mysuit-ocr/src/lib/ocrResultFormatters.ts` (120 lines) — `OcrFormatterField` 입력 타입, `fieldLabel`, `fieldLabelFull`, `isAmountLikeField`, `getAdoptionLabel`, `parseTableField` 및 관련 타입 export.
- `mysuit-ocr/src/lib/markdownReportBuilder.ts` (81 lines) — `MarkdownReportField`, `BuildMarkdownReportInput`, `buildMarkdownReport` export. 내부에서 ocrResultFormatters만 의존.

## 6. grep / audit 결과 반영 내용
audit 명령: `Grep` for `fieldLabel`, `fieldLabelFull`, `getAdoptionLabel`, `parseTableField`, `isAmountLikeField`, `toMarkdown` across `mysuit-ocr/src`.

| 함수 | 사용처 (toMarkdown 외) | 결정 |
| --- | --- | --- |
| `fieldLabelFull` | Custom JSX (line 1308), Validation JSX (1603, 1690) | 공유 → `ocrResultFormatters.ts` |
| `parseTableField` | Preview JSX (`previewTableFields` 759), Custom JSX (1451), Validation JSX (1583) | 공유 → `ocrResultFormatters.ts` |
| `getAdoptionLabel` | Custom JSX (1382, 1465, 1494), Validation JSX (1624, 1697), `renderAdoption` (445) | 공유 → `ocrResultFormatters.ts` |
| `fieldLabel` (단수) | Custom JSX (1310), Validation JSX (1604, 1691), `isAmountLikeField` (501), autofill detail (551) | 공유 → `ocrResultFormatters.ts` |
| `isAmountLikeField` | `actionMeta` 호출 (522), autofill detail rows (547, 555) | `fieldLabel` 의존 → 같이 이동 |
| `toMarkdown` | Preview Markdown render (1044), Copy (1001), Export (998) — 모두 컴포넌트 내부 | `markdownReportBuilder.ts` 전용 |

추가로 `resolveFieldLabel`은 두 label helper가 함께 사용 → OcrResultPanel에서는 unused가 되어 import 제거.

## 7. 공유 formatter 분리 내용 (ocrResultFormatters.ts)
- export type `OcrFormatterField` — 최소 입력 형태 (`name`, `ko?`, `en?`, `value?`, `source?`, `autofillAction?`). `OcrFieldResult`가 구조적으로 대입 가능.
- export function `fieldLabel(field)` — primary 라벨 반환.
- export function `fieldLabelFull(field)` — primary + optional secondary 라벨.
- export function `isAmountLikeField(field)` — 금액 계열 필드 감지 (`fieldLabel` 의존). AMOUNT_LIKE_TOKENS 상수는 모듈 내부 private.
- export type `OcrAdoptionLabel` = `"OCR" | "복원" | "직접입력" | "-"`.
- export function `getAdoptionLabel(field)` — autofillAction/source/value 기반 라벨.
- export type `TableCell`, `ParsedTableField`.
- export function `parseTableField(value)` — 원본 동작 그대로 (multi-row keep-as-is rule, single-row flatten rule, rowLabel 생성).

순수성 보장:
- `react` import 없음.
- DOM/window/storage/network 접근 없음.
- closure / module-level state 없음.
- 입력 mutation 없음.
- 의존: `@/lib/invoiceFieldLabels.resolveFieldLabel`, `@/lib/autofillEngine` 타입(`AutofillAction`, `OutputValueSource`).

## 8. markdownReportBuilder helper 위치와 역할
- 위치: `mysuit-ocr/src/lib/markdownReportBuilder.ts`
- 함수: `buildMarkdownReport(input: BuildMarkdownReportInput): string`
- export: `MarkdownReportField`, `BuildMarkdownReportInput`, `buildMarkdownReport`
- 입력 contract:
  - `fields: ReadonlyArray<MarkdownReportField>` — `name`, `field_type`, `value: string`, `confidence` 필수 + `ko`, `en`, `source`, `autofillAction` 선택
  - `processingTime: number`
  - `docTableRows?: Record<string, unknown>[] | null`
- 책임:
  - "# OCR 결과" 헤딩
  - 처리 시간 / 필드 수 요약 라인
  - Markdown table: No / 필드명 / 값 / 신뢰도 / 채택
  - table field는 `표 데이터 (N행)` 요약 (N = `docTableRows.length` 우선, fallback은 `parseTableField` rowLabel)
  - pipe / newline escaping (`escapeCell`)
  - 줄바꿈은 `"\n"` 만 사용
- 책임이 아닌 것:
  - Copy/Export 버튼, React state/useMemo, Raw JSON, Clean JSON, Preview/Custom/Validation 렌더링, tableRows 상세 펼침, rowIndex 정책, 거래_3 정책
- 의존: `ocrResultFormatters`의 `fieldLabelFull`, `getAdoptionLabel`, `parseTableField`만.
- React 의존 없음, DOM 없음, closure 없음.

## 9. 추출 전 Markdown fixture check 결과
- 실행 1차 (timing 정규화 추가 전): **overall FAIL, counts={'FAIL': 5}**
  - 원인 a) script `CASES`에 trade_7_7pdf 누락 (이전 단계에서 manifest에는 추가됐으나 script는 갱신되지 않음)
  - 원인 b) Markdown 출력의 `- 처리 시간: **N.NNs**` 라인이 OCR 매 실행마다 달라짐 (fixture lock 당시: trade_1 = 59.49s, 이번 실행 = 57.57s). v1 contract 자체에 OCR 비결정성이 leak되어 byte-exact 비교 불가.
  - 조치: `trade_7_7pdf` case 추가 + `_normalize_for_compare()`로 처리시간 라인을 `**X.XX**`로 마스킹. 다른 모든 byte는 비교 유지.
- 실행 2차 (수정 후): **overall PASS, counts={'PASS': 6}**, 전 케이스 PASS.
- 리포트: `mysuit-ocr/docs/MARKDOWN_V1_FIXTURE_CHECK_pre_extraction_20260521_20260521.{md,json}`

| caseId | templateId | actualBytes | expectedBytes | actualLines | expectedLines | endsLF | expCRLF | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| trade_1_1jpg | TPL-31D13CF3 | 922 | 922 | 17 | 17 | Y | N | PASS |
| trade_2_2pdf | TPL-5A8C2374 | 875 | 875 | 16 | 16 | Y | N | PASS |
| trade_3_3pdf | TPL-E4B15A22 | 942 | 942 | 17 | 17 | Y | N | PASS |
| trade_7_7pdf | TPL-3AFD383E | 1011 | 1011 | 17 | 17 | Y | N | PASS |
| tpl_003_1jpg | TPL-003 | 471 | 471 | 13 | 13 | Y | N | PASS |
| tpl_003_2jpg | TPL-003 | 470 | 470 | 13 | 13 | Y | N | PASS |

## 10. 추출 후 Markdown fixture check 결과
- 실행: `python tmp/codex_markdown_contract_fixture_lock.py --check --phase post_extraction_20260521`
- 결과: **overall PASS, counts={'PASS': 6}**
- 모든 case에서 bytes/lines 동일, LF 유지, CRLF 미포함.
- timing-normalize 적용 후 exact string equality.
- 리포트: `mysuit-ocr/docs/MARKDOWN_V1_FIXTURE_CHECK_post_extraction_20260521_20260521.{md,json}`

## 11. Clean JSON JS fixture runner 결과
- 실행: `node tmp/check_clean_json_v1_fixtures_js.mjs`
- 결과: **9/9 PASS, diffs=0**
- 거래_1~7, TPL-003 1.jpg, 2.jpg 모두 PASS.
- Clean JSON 회귀 없음 — toMarkdown helper 분리가 Clean JSON 출력에 영향 없음 확인.
- 리포트(runner 자체 자동 갱신): `mysuit-ocr/docs/FRONTEND_CLEANUP_1B_JS_CLEAN_JSON_FIXTURE_RUNNER_20260521.{md,json}` (overwritten by this run; same content as Codex 1B 결과 외 시각만 변경)

## 12. Preview / Custom / Validation 영향 없음 확인
- OcrResultPanel.tsx JSX 변경: **없음**. import 4줄 추가/1줄 제거 + 5개 형제 정의 제거 + toMarkdown body 11라인 단축이 전부.
- Preview JSX에서 `parseTableField` 사용처(`previewTableFields` useMemo) — 그대로 동작, import 경로만 변경.
- Custom JSX (`fieldLabel`, `fieldLabelFull`, `parseTableField`, `getAdoptionLabel` 호출) — 그대로 동작.
- Validation JSX (`fieldLabel`, `fieldLabelFull`, `getAdoptionLabel`, `parseTableField` 호출) — 그대로 동작.
- Markdown Preview render (`<Markdown>{toMarkdown()}</Markdown>`) — toMarkdown은 helper wrapper로 변경, output 동일.
- Copy / Export 핸들러 — 코드 자체 변경 없음, `toMarkdown()` 호출 결과만 helper 경유.
- Raw JSON / Clean JSON 경로 — 코드 변경 없음. Clean JSON runner 9/9 PASS로 회귀 없음 확인.
- TestWorkspace.tsx, DetailHistoryView.tsx, invoiceTableDisplay.ts, cleanJsonBuilder.ts — 미수정.

import boundary 검증 (grep):
- `markdownReportBuilder` import: `OcrResultPanel.tsx`에서만 (1건).
- `ocrResultFormatters` import: `OcrResultPanel.tsx` + `markdownReportBuilder.ts` (의도된 의존성).
- Preview/Custom/Validation JSX는 `markdownReportBuilder`를 import하지 않음 — 경계 원칙 준수.

## 13. LF / exact string equality 유지 확인
- 6개 fixture 모두 LF (no CRLF), endsWithNewline=true.
- Comparison policy: LF-strict, no CRLF normalization, "exact string equality modulo OCR processing_time".
- timing 마스킹 패턴: `r"(- 처리 시간: \*\*)\d+\.\d+(s\*\*)"` → `r"\1X.XX\2"` (양측 모두 적용).
- 다른 모든 byte는 byte-for-byte 비교 (헤딩, 테이블, 필드 값, confidence %, 라벨, escaping, 순서, trailing newline).

## 14. typecheck / build 결과
| command | status | exit |
| --- | --- | --- |
| `npm run typecheck` | PASS | 0 |
| `npm run build` | PASS | 0 |

build 결과:
- ✓ Compiled successfully in 2.3s
- ✓ Generating static pages (18/18)
- `/runocr` size: 65.2 kB → 65.3 kB (markdown builder/formatter import 약간의 overhead, 의미 없음)
- First Load JS shared: 102 kB (변동 없음)

## 15. known stderr noise 기록
- ID: `ISSUE-FRONTEND-BUILD-LOG-1`
- 메시지: `⨯ ESLint: nextVitals is not iterable`
- 발생: `npm run build` stderr, exit code 0과 동시.
- 이번 작업과 인과 관계 없음 — FRONTEND-CLEANUP-1 / 2A부터 이미 동일 패턴.
- 별도 추적 권장 (FRONTEND-CLEANUP-1 리포트의 next suggested task #5와 동일).

## 16. 남은 리스크
1. **Markdown fixture의 OCR processing_time 비결정성** — v1 contract가 비결정적 출력을 포함하고 있어 strict byte equality는 구조적으로 불가능. `--check` 모드에서는 해당 라인만 마스킹해 비교. helper 추출의 정합성 검증에는 충분하지만, "exact string equality" 원안에서 한 발 양보한 셈. 장기적으로 helper input에서 timing을 분리하거나, raw OCR snapshot replay를 도입하면 더 엄격한 검증 가능.
2. **JS-side direct check runner 미구비** — Markdown은 Python 재구현(`to_markdown`)으로 fixture와 비교한다. Clean JSON처럼 Node에서 `buildMarkdownReport`를 직접 import해 비교하는 runner는 별도 task로 분리 가능. 현재는 (a) literal 코드 이동, (b) typecheck/build, (c) Clean JSON JS runner 회귀 통과로 간접 보증.
3. **거래_4/5/6 markdown fixture 미포함** — coverage precheck에서 trade_7만 추가하고 다른 거래는 redundant로 판단됨 (Markdown은 table을 펼치지 않으므로 패턴이 유사). 정책 변경 시 fixture 확장 검토.
4. **`ISSUE-FRONTEND-BUILD-LOG-1`** — build stderr noise는 별도 추적 필요.
5. **Preview/Custom/Validation 자체 리팩토링 미수행** — 이번 작업 범위 의도적 제외. 다음 단계 후보.

## 17. 다음 작업 제안
1. **JS-side Markdown direct check runner** — `node tmp/check_markdown_v1_fixtures_js.mjs` (Clean JSON 1B runner의 패턴 재사용, `buildMarkdownReport`를 직접 import해 fixture와 비교). 위 리스크 #2 해소.
2. **거래_3 `insuranceCode`/`amount` 정책 결정** — Clean JSON v1에 locked 상태로 남아 있는 컬럼 정책. 별도 task.
3. **`previewTableFields` 공통화 (FRONTEND-CLEANUP-3?)** — OcrResultPanel Preview tab의 `previewTableFields` useMemo (parseTableField 기반)를 별도 helper로 분리 검토. 이번 작업으로 parseTableField가 이미 ocrResultFormatters에 있으므로 다음 단계가 자연스러움.
4. **Custom/Validation JSX 분리** — 더 큰 PR이 되겠지만, 같은 패턴(contract → fixture → extract → check) 적용 가능.
5. **`ISSUE-FRONTEND-BUILD-LOG-1`** — `eslint-config-next` 호환 점검.
