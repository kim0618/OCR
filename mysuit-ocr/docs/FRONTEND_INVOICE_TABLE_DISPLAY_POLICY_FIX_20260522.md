# FRONTEND-CLEANUP-3D4 — Invoice table display policy fix

## 1. 사용 도구와 모델
- 사용 도구: Claude Code
- 사용 모델: claude-opus-4-7 (Opus 4.7)
- 작업명: `FRONTEND-CLEANUP-3D4-INVOICE-TABLE-DISPLAY-POLICY-FIX`
- 작업 일자: 2026-05-22

## 2. 작업 목적
3D-3 manual smoke에서 발견된 거래명세서 Preview/Clean JSON 컬럼 표시 정책 3가지 문제 수정:
- **trade_4**: `totalAmount`가 row column으로 노출되는 문제 → SUMMARY 키로 제외
- **trade_6**: 정상 `lotNo`가 itemCode + manufacturingNo empty 노이즈 rule에 걸려 숨겨지는 문제 → explicit expected 컬럼에 대해 lot 노이즈 rule 면제
- **trade_7**: 정상 `serialLotComposite`가 internal/composite filter에 걸려 누락되는 문제 → 명시 allowlist 기반 composite 필터 우회

## 3. 백업 파일
- `mysuit-ocr/backup/invoiceTableDisplay_20260522_before_FRONTEND_CLEANUP_3D4_INVOICE_TABLE_DISPLAY_POLICY_FIX.ts` (12162 bytes, fix 직전 원본)
- `mysuit-ocr/backup/fixtures_3D4_safety_20260522/` — table_view_model_v1 + clean_json_v1 전체 fixture safety copy (1차 광범위 fix 시 trade_1/3 의도치 않은 변경 발생 → 백업에서 복원하여 narrower fix 재진행)

## 4. 수정 파일
- `mysuit-ocr/src/lib/invoiceTableDisplay.ts` — `_SUMMARY_KEYS`, `_EXPLICIT_COMPOSITE_ALLOWLIST` 상수 추가, `buildInvoicePreviewCols` 3가지 정책 보정
- `mysuit-ocr/tmp/codex_table_view_model_input_fixture_prep.py` — Python 재구현 동일 patch
- `mysuit-ocr/tmp/codex_table_view_model_fixture_lock.py` — Python 재구현 동일 patch
- `mysuit-ocr/tmp/codex_clean_json_v1_fixture_lock.py` — Python 재구현 동일 patch

수정 금지 파일 (모두 unchanged 확인):
- `src/components/upload/OcrResultPanel.tsx` ✓
- `src/lib/structuredTableViewModel.ts` ✓
- `src/lib/cleanJsonBuilder.ts` ✓
- `src/lib/markdownReportBuilder.ts` ✓
- `src/lib/ocrResultFormatters.ts` ✓
- `src/components/test/TestWorkspace.tsx` ✓
- backend / templates / GT / manifest ✓

## 5. fixture 갱신 파일 (의도된 변경)
- `tmp/fixtures/table_view_model_v1/inputs/trade_4_4pdf.input.json`
- `tmp/fixtures/table_view_model_v1/invoice_statement/trade_4_4pdf.view_model.json`
- `tmp/fixtures/clean_json_v1/invoice_statement/trade_4_4pdf.clean.json`
- `tmp/fixtures/table_view_model_v1/inputs/trade_6_6pdf.input.json`
- `tmp/fixtures/table_view_model_v1/invoice_statement/trade_6_6pdf.view_model.json`
- `tmp/fixtures/clean_json_v1/invoice_statement/trade_6_6pdf.clean.json`
- `tmp/fixtures/table_view_model_v1/inputs/trade_7_7pdf.input.json`
- `tmp/fixtures/table_view_model_v1/invoice_statement/trade_7_7pdf.view_model.json`
- `tmp/fixtures/clean_json_v1/invoice_statement/trade_7_7pdf.clean.json`
- `tmp/fixtures/table_view_model_v1/manifest.json` (재캡처에 따른 timestamp + trade_4/6/7 metadata)
- `tmp/fixtures/clean_json_v1/manifest.json` (재캡처에 따른 timestamp + trade_4/6/7 metadata)

**비대상 fixture 보존 (diff로 검증)**:
- `trade_1/2/3/5_*.view_model.json` ✓ unchanged
- `trade_1/2/3/5_*.input.json` ✓ unchanged
- `trade_1/2/3/5_*.clean.json` ✓ unchanged
- `synthetic/synthetic_empty_rows.view_model.json` ✓ unchanged
- `receipt/tpl_003_1jpg.clean.json`, `tpl_003_2jpg.clean.json` ✓ unchanged

## 6. 핵심 수정 내용

### `_SUMMARY_KEYS` 도입
```ts
const _SUMMARY_KEYS = new Set(["totalAmount"]);
```
`buildInvoicePreviewCols`의 모든 candidate-key 경로에서 SUMMARY_KEYS 제외. supplyAmount/taxAmount/amount는 row column으로 유지.

### `_EXPLICIT_COMPOSITE_ALLOWLIST` 도입
```ts
const _EXPLICIT_COMPOSITE_ALLOWLIST = new Set(["serialLotComposite"]);
const isAllowedComposite = (k) => _EXPLICIT_COMPOSITE_ALLOWLIST.has(k) && isExplicit(k);
```
expectedColumnKeys에서 candidate를 만들 때 `isInternalTableKey(k) && !isAllowedComposite(k)`이면 제외. 즉:
- `serialLotComposite`가 expected에 있으면 → 통과 (trade_7)
- `manufacturingExpiryComposite`가 expected에 있어도 → 여전히 internal로 필터 (trade_3 보존)

### lot 노이즈 rule explicit 면제
기존:
```ts
if (cols.some((c) => _LOT_KEYS.has(c.key)) && hasMeaningful(itemCode) && !hasMeaningful(manufacturingNo)) {
  cols = cols.filter((c) => !_LOT_KEYS.has(c.key));
}
```
변경:
```ts
const lotColsImplicit = cols.filter((c) => _LOT_KEYS.has(c.key) && !isExplicit(c.key));
if (lotColsImplicit.length > 0 && hasMeaningful(itemCode) && !hasMeaningful(manufacturingNo)) {
  const removeKeys = new Set(lotColsImplicit.map((c) => c.key));
  cols = cols.filter((c) => !removeKeys.has(c.key));
}
```
즉 explicit lotNo는 노이즈 rule에서 제외 (trade_6 정상 lotNo 표시).

### 적용 안 한 dedup rule (의도)
- **lot/mfg dup rule**: explicit 여부와 무관하게 유지 — trade_1의 `lotNo == manufacturingNo`가 dup이면 여전히 lotNo 숨김. 이게 없으면 trade_1에 중복 컬럼이 surface됨
- **serialNo vs lotNo dup rule**: explicit 여부와 무관하게 유지
- **itemCode 5% rule**: explicit 여부와 무관하게 유지

(1차 광범위 fix에서는 모든 dedup rule을 explicit으로 면제했으나, trade_1/3 의도치 않은 변경이 발생 → 1차 fix 폐기 후 narrower fix로 재진행)

## 7. trade_4 변경 결과
- 변경 전 columns (8개): `itemName, lotNo, unit, quantity, unitPrice, supplyAmount, taxAmount, totalAmount`
- 변경 후 columns (7개): `itemName, lotNo, unit, quantity, unitPrice, supplyAmount, taxAmount`
- `totalAmount` 제거 ✓
- `supplyAmount`, `taxAmount` 유지 ✓
- rowIndex excluded → excluded 유지 ✓

## 8. trade_6 변경 결과
- 변경 전 columns (5개): `rowIndex, itemCode, itemName, quantity, expiryDate`
- 변경 후 columns (6개): `rowIndex, itemCode, itemName, quantity, lotNo, expiryDate`
- `lotNo` 추가 ✓
- rowIndex included → included 유지 ✓

## 9. trade_7 변경 결과
- 변경 전 columns (3개): `itemName, unit, quantity`
- 변경 후 columns (4개): `itemName, serialLotComposite, unit, quantity`
- `serialLotComposite` 추가 ✓
- rowIndex excluded → excluded 유지 ✓

## 10. trade_1 / 2 / 3 / 5 무변경 확인
diff 결과 trade_1/2/3/5의 input/view_model/clean_json fixture 모두 100% bytes-identical (변경 없음).

| case | view_model | clean_json | input | rowIndex 정책 |
|---|---|---|---|---|
| trade_1_1jpg | unchanged | unchanged | unchanged | excluded (유지) |
| trade_2_2pdf | unchanged | unchanged | unchanged | included (유지) |
| trade_3_3pdf | unchanged | unchanged | unchanged | included (유지, LOCKED 보존) |
| trade_5_5pdf | unchanged | unchanged | unchanged | excluded (유지) |
| synthetic_empty_rows | unchanged | — | unchanged | excluded (유지) |
| TPL-003 1.jpg/2.jpg | — | unchanged | — | n/a |

## 11. rowIndex 정책 확인
| case | expected | actual | OK |
|---|---|---|---|
| trade_1_1jpg | excluded | excluded | ✓ |
| trade_2_2pdf | included | included | ✓ |
| trade_3_3pdf | included | included | ✓ |
| trade_4_4pdf | excluded | excluded | ✓ |
| trade_5_5pdf | excluded | excluded | ✓ |
| trade_6_6pdf | included | included | ✓ |
| trade_7_7pdf | excluded | excluded | ✓ |

`shouldDisplayRowIndex` 정책 미수정.

## 12. 거래_3 locked behavior 확인
- trade_3 view_model columns: `rowIndex, insuranceCode, itemName, quantity, unitPrice, amount, manufacturer`
- `insuranceCode` 값: `669700020` (LOCKED)
- `amount` 값: `301,320` (LOCKED)
- manifest.lockedCurrentBehavior 마커 보존

## 13. table_view_model fixture runner 결과
- 실행: `node tmp/check_table_view_model_v1_fixtures_js.mjs`
- 결과: **overall PASS, 8/8 PASS, totalDiffs=0, totalForbiddenHits=0**
- purity: reactHookFree=true, noBrowserOrNetworkAccess=true, noUiResponsibility=true, inputMutationFree=true

## 14. Clean JSON fixture runner 결과
- 실행: `node tmp/check_clean_json_v1_fixtures_js.mjs`
- 결과: **9/9 PASS, totalDiffs=0**
- trade_4/6/7 Clean JSON tables의 row keys가 새 displayCols와 일치

## 15. Markdown fixture check 결과
- 실행: `python tmp/codex_markdown_contract_fixture_lock.py --check --phase post_3D4_20260522`
- 결과: **overall PASS, counts={'PASS': 6}**
- Markdown은 structured tableRows를 펼치지 않으므로 column policy 변경 영향 없음 (예상대로)

## 16. typecheck / build 결과
| command | status | exit |
| --- | --- | --- |
| `npm run typecheck` | PASS | 0 |
| `npm run build` | PASS | 0 |

build: ✓ Compiled successfully in 1.9s, ✓ 18/18 static pages, `/runocr` size unchanged.

## 17. known stderr noise 기록
- ID: `ISSUE-FRONTEND-BUILD-LOG-1`
- 메시지: `⨯ ESLint: nextVitals is not iterable`
- exit code 0과 동시 발생 (build success). 이번 작업과 무관, 이전 cycle부터 동일.

## 18. 남은 이슈
1. **1차 광범위 fix 시 trade_1/3 unexpected drift 발생** — explicit bypass를 모든 dedup rule에 적용하면 trade_1 lotNo dup + trade_3 manufacturingExpiryComposite가 surface됨. 백업 복원 후 narrower fix(serialLotComposite allowlist + lot 노이즈만 explicit 면제)로 재진행해 해결.
2. **manifest 재생성 순서 의존성** — view_model_fixture_lock.py가 manifest를 재작성하면서 `inputFixturePath` / `lockedCurrentBehavior` 필드 제거. input_fixture_prep.py를 view_model lock 이후 다시 실행해야 메타데이터 복원됨. 향후 lock script 통합 시 단일 실행으로 만들 여지.
3. **Manual smoke 재확인 필요** — 자동 검증은 모두 PASS이지만 실제 브라우저에서 trade_4/6/7의 column 변화 시각 확인 권장 (3D-3 close-out 전).
4. **EXPLICIT_COMPOSITE_ALLOWLIST 하드코딩** — 현재 `serialLotComposite` 한 개만. 향후 다른 composite (예: `manufacturingExpiry`)가 필요해지면 allowlist에 추가하거나 Template column definition으로 일반화 검토.
5. **trade_1 lotNo이 expectedColumnKeys에 있음에도 dup rule로 숨김 유지** — 데이터 의미상 정당하지만 backend OCR이 lotNo + manufacturingNo를 같은 값으로 채우는 패턴이라 발생. Template column definition 도입 시 재검토 여지.
6. **`ISSUE-FRONTEND-BUILD-LOG-1`** — stderr noise 별도 추적.

## 19. 다음 작업 제안
1. **Manual smoke 재확인** — `/runocr`에서 trade_4(totalAmount 사라짐), trade_6(lotNo 표시), trade_7(serialLotComposite 표시) 시각 확인 후 3D-3 close-out 문서에 `manual smoke WARN resolved` 추가
2. **OcrResultPanel cleanup cycle 1 close-out 리포트** — 3D-1 ~ 3D-4 통합 마감. 완료/보류/재개 조건 정리
3. **Custom / Validation view model migration** — cycle 2 후보. Custom textarea 편집 wrapper + Validation status UI를 view model output 위에서 처리할 contract 정의 필요
4. **legacy parseTableField fallback view model** (`buildLegacyTableViewModel`) — 별도 cycle
5. **Template table column definition** — 백엔드/manifest에서 explicit display column을 표현하는 정식 메커니즘. 도입되면 allowlist 하드코딩이 사라지고 `externalExpectedKeys`로 깔끔하게 대체됨
6. **TestWorkspace 정리** — 사용자 확인 후 별도 작업
7. **`ISSUE-FRONTEND-BUILD-LOG-1`** — `eslint-config-next` 호환 점검
