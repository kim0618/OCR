# FRONTEND-CLEANUP-1 — Clean JSON builder extraction with fixture check runner

## 1. 사용 도구와 모델
- 사용 도구: Claude Code
- 사용 모델: claude-opus-4-7 (Opus 4.7, 1M context)
- 작업명: `FRONTEND-CLEANUP-1 Clean JSON builder extraction with fixture check runner`
- 작업 일자: 2026-05-21

## 2. 작업 목적
`OcrResultPanel.tsx` 내부 Clean JSON v1 생성 로직을 별도 순수 helper(`src/lib/cleanJsonBuilder.ts`)로 분리한다. 추출 전/후 Clean JSON v1 출력은 100% 동일해야 한다. 기능 변경이 아닌 구조 분리 작업이다.

분리에 앞서 fixture check runner를 추가해 사전·사후 deep equality 검증을 자동화했다.

## 3. 백업 파일 목록
- `mysuit-ocr/backup/OcrResultPanel_20260521_before_FRONTEND_CLEANUP_1_CLEAN_JSON_BUILDER_EXTRACT.tsx` (1789 lines, pre-extract 원본)
- `mysuit-ocr/backup/codex_clean_json_v1_fixture_lock_20260521_before_FRONTEND_CLEANUP_1_CHECK_RUNNER.py` (check 모드 추가 직전 fixture lock 스크립트 원본)

## 4. 수정 파일 목록
- `mysuit-ocr/tmp/codex_clean_json_v1_fixture_lock.py` — `--check` 모드, `deep_compare()`, `check_cases()`, `make_check_report_md()` 추가. capture path는 그대로 보존.
- `mysuit-ocr/src/components/upload/OcrResultPanel.tsx` — Clean JSON v1 inline 빌더 제거, helper 호출로 대체. 다른 영역(Preview/Custom/Validation/Raw JSON/Copy/Export) 미수정.

## 5. 신규 파일 목록
- `mysuit-ocr/src/lib/cleanJsonBuilder.ts` (171 lines) — `buildCleanJsonResult` 순수 helper, output/input types export.

## 6. fixture check runner 추가 내용
기존 `codex_clean_json_v1_fixture_lock.py`에 read-only `--check` 모드를 추가했다. capture 동작은 건드리지 않았다.

추가된 항목:
- CLI args: `--check`, `--phase <tag>`, `--check-report-json <path>`, `--check-report-md <path>`.
- `deep_compare(actual, expected, path)` — dict 키 순서, list 길이, 원시값 모두 비교. 첫 불일치 path 출력.
- `summarize_invoice_actual(clean)` — 거래명세서 actual rowCount / rowIndex 노출 여부 / row keys 추출.
- `check_cases(api_url, templates)` — `INVOICE_CASES`, `RECEIPT_CASES`를 순회하며 ① API에서 raw OCR 결과 수신 → ② `build_clean_json()`(스크립트 내부 Python 재현)으로 Clean JSON v1 생성 → ③ 기존 fixture 파일을 read-only로 읽음 → ④ `deep_compare` 결과를 case별로 누적.
- `make_check_report_md(report)` — phase, API source, case 별 diff 요약 markdown 생성.
- `main()` 분기: `--check`이면 fixture/manifest write 없이 check 결과만 `docs/CLEAN_JSON_V1_FIXTURE_CHECK_<phase>_20260521.{md,json}`에 기록 후 종료. capture path는 unchanged.

write 차단:
- `--check` 모드는 `MANIFEST_PATH`, fixture 디렉터리, capture 리포트(`REPORT_MD/JSON`)를 절대 쓰지 않는다.
- 디렉터리 mkdir도 fixture 쪽은 skip하고 `logs/`, `docs/`만 보장한다.

## 7. 추출 전 fixture check 결과 (pre)
- 실행: `python tmp/codex_clean_json_v1_fixture_lock.py --check --phase pre_extraction_20260521`
- 리포트: `mysuit-ocr/docs/CLEAN_JSON_V1_FIXTURE_CHECK_pre_extraction_20260521_20260521.{md,json}`
- 로그: `ocr-server/logs/codex_FRONTEND_CLEANUP_1_FIXTURE_CHECK_PRE.{out,err}.log`
- API: `http://127.0.0.1:9137/ocr/extract` (9099 비응답 → 스크립트가 자동 fallback port 기동, 종료 시 cleanup)
- 결과: **overall PASS, counts={'PASS': 9}, diffCount 0/0/0 (전 케이스)**

| caseId | templateId | rowCount exp/act | rowIndex exp/act | diff | status |
| --- | --- | --- | --- | --- | --- |
| trade_1_1jpg | TPL-31D13CF3 | 28/28 | excluded/excluded | 0 | PASS |
| trade_2_2pdf | TPL-5A8C2374 | 13/13 | included/included | 0 | PASS |
| trade_3_3pdf | TPL-E4B15A22 | 1/1 | included/included | 0 | PASS |
| trade_4_4pdf | TPL-FD07531C | 1/1 | excluded/excluded | 0 | PASS |
| trade_5_5pdf | TPL-B8936EDE | 6/6 | excluded/excluded | 0 | PASS |
| trade_6_6pdf | TPL-95328E52 | 6/6 | included/included | 0 | PASS |
| trade_7_7pdf | TPL-3AFD383E | 1/1 | excluded/excluded | 0 | PASS |
| tpl_003_1jpg | TPL-003 | info 6 / tables 0 | — | 0 | PASS |
| tpl_003_2jpg | TPL-003 | info 6 / tables 0 | — | 0 | PASS |

## 8. buildCleanJsonResult helper 위치와 역할
- 위치: `mysuit-ocr/src/lib/cleanJsonBuilder.ts`
- 함수: `buildCleanJsonResult(input: BuildCleanJsonInput): CleanJsonResult`
- export: `CleanJsonInfo`, `CleanJsonTable`, `CleanJsonResult`, `CleanJsonInputField`, `BuildCleanJsonInput`, `buildCleanJsonResult`
- 책임:
  - `templateName`을 받아 `CleanJsonResult.templateName = templateName ?? ""`로 정규화.
  - `field_type === "field"` 항목을 `info[]` (`{ key, label, value }`)로 변환.
  - `field_type === "table"` 항목을 `tables[]` (`{ key, label, rows }`)로 변환.
  - rows 우선순위: ① `docTableRows` + `docTableDisplayCols` (구조화) → ② `field.tableRows` → ③ `field.table_data` → ④ `JSON.parse(field.value)` legacy fallback.
  - rows 순서는 입력받은 display columns 순서를 그대로 따른다 (`Object.keys(row)` 미사용).
  - 셀 값 정규화는 `@/lib/invoiceTableDisplay`의 `normalizeTableCell`을 그대로 사용.
- 책임이 아닌 것:
  - Raw JSON 생성, React state/useMemo/closure, copy/export, Preview/Custom/Validation 렌더링, OCR/parser 호출, rowIndex 정책 변경, 거래_3 extra column 정책 변경.

## 9. OcrResultPanel.tsx 변경 요약
| 항목 | before | after |
| --- | --- | --- |
| 파일 라인 수 | 1789 | 1714 (−75) |
| import `INVOICE_TABLE_COL_PRIORITY` | 사용 | helper로 이동 → 제거 |
| import `buildCleanJsonResult, CleanJsonResult` | 없음 | `@/lib/cleanJsonBuilder`에서 추가 |
| local types `CleanJsonInfo/Table/Result` | 컴포넌트 파일 정의 | helper로 이동 (re-import) |
| local `cleanTableRowsFromObjects/Cells` | 컴포넌트 함수 | helper 내부로 이동 |
| `cleanJson` useMemo | inline 70 lines | helper 호출 11 lines |
| `toCleanJson` | 그대로 | 그대로 |
| `docTableRows`, `docTableMeta`, `docTableDisplayCols` 산출 코드 | 그대로 | 그대로 |
| Preview / Custom / Validation / Raw JSON / Copy / Export / handleCopy / handleExport | 그대로 | 그대로 |
| useMemo deps `[editedFields, docTableRows, docTableDisplayCols, templateName]` | 동일 | 동일 |

## 10. Clean JSON v1 출력 유지 확인
- top-level 구조 (`templateName`, optional `info`, optional `tables`) 보존.
- info item 키 순서 (`key`, `label`, `value`) 보존 — 객체 리터럴 동일.
- table item 키 순서 (`key`, `label`, `rows`) 보존 — 객체 리터럴 동일.
- table row 키 순서는 `docTableDisplayCols` 순서대로 ordered object 생성 (`for (const key of orderedKeys)` 보존).
- v1 외 top-level key (`info2`, `table2` 등) 도입 없음.
- 디버그 키 (`confidence`, `bbox`, `source`, `_`, composite 등) 노출 없음 — `invoiceTableDisplay.isInternalTableKey`가 이미 차단.

## 11. 추출 후 fixture check 결과 (post)
- 실행: `python tmp/codex_clean_json_v1_fixture_lock.py --check --phase post_extraction_20260521`
- 리포트: `mysuit-ocr/docs/CLEAN_JSON_V1_FIXTURE_CHECK_post_extraction_20260521_20260521.{md,json}`
- 로그: `ocr-server/logs/codex_FRONTEND_CLEANUP_1_FIXTURE_CHECK_POST.{out,err}.log`
- API: `http://127.0.0.1:9137/ocr/extract` (started_fallback_port)
- 결과: **overall PASS, counts={'PASS': 9}, diffCount 0/0/0 (전 케이스)**
- 거래_1~7, TPL-003 1/2.jpg 모두 pre-check와 동일한 row keys, rowCount, rowIndex 노출.

검증 범위 caveat:
- `--check` mode는 스크립트 내부의 Python `build_clean_json()` 재구현을 사용해 비교한다.
- 따라서 fixture는 "OCR API + Python 재구현" 출력이 고정되어 있는지를 확인하며, 직접적으로 JS extracted helper의 출력을 비교하지는 않는다.
- JS helper의 동작은 (a) literal 코드 이동을 통한 동등성, (b) `npm run typecheck` 타입 안전성, (c) `npm run build` Next.js 페이지 전체 빌드 (`/runocr` 65.2 kB) 로 간접 검증된다.
- 추후 JS-side runner를 별도 task로 분리 가능 (남은 리스크 참고).

## 12. rowIndex 정책 유지 확인
- 거래_1/4/5/7: rowIndex 제외 → 두 check 모두 `rowIndexActual = excluded`, row_keys 첫 항목 ≠ `rowIndex`.
- 거래_2/3/6: rowIndex 유지 → 두 check 모두 `rowIndexActual = included`, row_keys 첫 항목 `rowIndex`.
- rowIndex 정책 결정은 helper 외부 `buildInvoicePreviewCols(docTableMeta, docTableRows)`에 위임 (invoiceTableDisplay 미수정).
- helper는 입력 `docTableDisplayCols`만 신뢰하므로 `Object.keys(row)`로 rowIndex 부활 위험 없음.

## 13. 거래_3 locked behavior 유지 확인
- 거래_3 fixture rowKeys: `["rowIndex", "insuranceCode", "itemName", "quantity", "unitPrice", "amount", "manufacturer"]` (fixture lock 시점과 동일).
- pre/post check 모두 동일 row keys, diff 0.
- helper 본문 상단에 `LOCKED:` 주석으로 표시:
  - "LOCKED: 거래_3 insuranceCode/amount extra columns are current Clean JSON v1 behavior. See docs/CLEAN_JSON_V1_FIXTURE_LOCK_20260521.md — do not change here."
- 정책 변경은 별도 task로 분리한다.

## 14. 영수증 fixture 유지 확인
- TPL-003 1.jpg, 2.jpg: pre/post 모두 `infoCount=6`, `tableCount=0`, `status=PASS`, `diffCount=0`.
- field-only 케이스에서 `tables` 키가 누락되어 v1 contract와 일치 (helper의 `if (tables.length > 0) result.tables = tables;` 조건 보존).

## 15. helper 순수성 확인
helper는 다음을 사용하지 않는다 (`grep` 검증):
- React (`useState`, `useEffect`, `useMemo`, `useRef`, JSX 등) — `react` import 없음.
- DOM (`document`, `window`, `localStorage`, `navigator`, `URL`, `Blob`) — 호출 없음.
- 컴포넌트 closure / module-level 가변 state — 모든 입력은 `BuildCleanJsonInput` 인자에서 옴.
- OCR API 호출, `fetch`, `axios` — import 없음.
- 외부 module 의존은 `@/lib/invoiceTableDisplay`의 3개 순수 함수/상수만 (`INVOICE_TABLE_COL_PRIORITY`, `hasMeaningfulTableValue`, `normalizeTableCell`).
- 입력 객체 mutation 없음 — `rows.map()`로 새 객체 생성, `for...of`도 `obj[key] = ...`로 새 객체 채움.

## 16. Raw JSON / Preview / Custom / Validation 영향 없음 확인
- `toCleanJson = () => JSON.stringify(cleanJson, null, 2)` 그대로 유지.
- Preview tab JSX 블록 (`docTableRows && docTableDisplayCols && ...`) 변경 없음.
- Custom tab JSX (`docTableRows && docTableDisplayCols && ...`) 변경 없음.
- Validation tab JSX (`docTableRows && docTableDisplayCols && ...`) 변경 없음.
- Copy/Export 핸들러 (`handleCopy`, `handleExport`) 변경 없음.
- 자동저장 (`editedFieldsRef`, `onPersist`, `lastSavedAt`) 변경 없음.
- Markdown 빌더 (`fieldsToMarkdown` 호출 흐름) 변경 없음.
- diff 결과 (backup 대비) 합계: −75 lines (모두 Clean JSON 빌더 블록).

## 17. typecheck / build 결과
| command | status | exit | log |
| --- | --- | --- | --- |
| `npm run typecheck` | PASS | 0 | `ocr-server/logs/codex_FRONTEND_CLEANUP_1_TYPECHECK.{out,err}.log` |
| `npm run build` | PASS | 0 | `ocr-server/logs/codex_FRONTEND_CLEANUP_1_BUILD.{out,err}.log` |

build 결과 주요 라인:
- 18/18 static pages PASS
- `/runocr` size: 65.3 kB → 65.2 kB (helper code-split 효과)
- 신규 module `@/lib/cleanJsonBuilder` 추가에 따른 전체 First Load JS 변화 없음 (102 kB shared 유지).

## 18. known stderr noise 기록
- ID: `ISSUE-FRONTEND-BUILD-LOG-1` (fixture lock 작업에서 이미 기록됨)
- 메시지: `⨯ ESLint: nextVitals is not iterable`
- 발생: `npm run build` stderr, exit code 0과 동시 발생 (build는 성공).
- 이번 task와 인과 관계 없음 — pre-task에서도 동일하게 관찰됨. cleanup 실패와 구분해서 추적.

## 19. 남은 리스크
1. **JS-side direct validation 미보유** — fixture check runner는 Python 재구현으로 비교한다. JS helper의 실제 출력을 fixture와 직접 비교하는 runner는 아직 없음. 후속 task로 Node/ts-node CLI 또는 dev server 기반 smoke를 권장. 현재는 (a) literal 코드 이동, (b) typecheck/build, (c) `editedFields/docTableRows/docTableDisplayCols/templateName` deps 그대로 보존으로 간접 보증.
2. **거래_3 extra column 정책 미해결** — `insuranceCode`, `amount`가 현재 v1 출력에 포함된다. fixture에 locked 상태로 보존했으나 정책 자체는 변경 안 됨. 별도 task에서 다뤄야 한다.
3. **백엔드 9099 비응답 시 fallback port 9137 사용** — fixture check 실행 시 스크립트가 자체적으로 9137에 임시 백엔드 기동 후 종료한다. 현재 환경에서 정상 동작하지만, CI 환경에서는 9099 사전 기동을 가정하지 않으면 fallback 의존성이 남는다.
4. **build stderr known noise (ISSUE-FRONTEND-BUILD-LOG-1)** — 빌드 성공과 무관하지만 cleanup 실패 신호와 섞일 위험. 별도 추적 권장.
5. **Preview/Custom/Validation/Raw JSON 자체는 미리팩토링** — 이번 task 범위에서 의도적으로 제외. 향후 단계에서 별도 helper화 검토 가능 (Clean JSON helper 분리가 이를 위한 첫 단계).

## 20. 다음 작업 제안
1. **JS-side fixture check runner 추가** — Node/ts-node로 `buildCleanJsonResult`를 직접 호출해 fixture와 deep equality 비교. 이번 task의 caveat(11.) 해소. small 작업.
2. **거래_3 `insuranceCode`/`amount` 정책 결정** — 표시 유지 vs 숨김/세분화. 결정 후 `buildInvoicePreviewCols` 또는 `invoice_statement` extractor 단에서 처리.
3. **`previewTableFields` / `parseTableField` 공통화** — Clean JSON helper 분리 다음 단계로 Preview용 빌더 분리 검토. `OcrResultPanel.tsx`의 Preview JSX 블록 (line 1050~1190)이 후보.
4. **`fieldsToMarkdown` 빌더 분리** — `OcrResultPanel.tsx`에 inline 정의된 markdown 빌더 (line 720~745)를 `src/lib/markdownReportBuilder.ts`로 이동.
5. **`ISSUE-FRONTEND-BUILD-LOG-1` 정리** — `eslint-config-next` 버전 호환 점검. cleanup 작업과 무관한 별도 티켓.
