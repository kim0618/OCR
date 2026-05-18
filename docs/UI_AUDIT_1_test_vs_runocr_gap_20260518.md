# UI Audit 1 — Test 탭 vs RunOCR/Template/Preview 격차 분석

- 작성일: 2026-05-18
- 모델: Claude Opus 4.7 (1M context)
- 분석 대상: `mysuit-ocr/src/components/test/TestWorkspace.tsx`(활성), `mysuit-ocr/src/components/upload/OcrResultPanel.tsx`(fix8 적용 상태),
  `mysuit-ocr/src/components/upload/UploadWorkspace.tsx`, `mysuit-ocr/src/components/ocr/OcrAnnotator.tsx`,
  `mysuit-ocr/src/components/ocr/OcrRightPanel.tsx`, `mysuit-ocr/src/components/ocr/core/export.ts`,
  `mysuit-ocr/src/lib/historyStore.ts`, `mysuit-ocr/src/lib/invoiceFieldLabels.ts`, `ocr-server/main.py`
- 산출물 종류: 분석 전용. 본 audit 실행 중 코드/설정/JSON/Markdown 기존 파일 일체 미수정. 본 리포트 2개(.md/.json)만 신규 생성.

---

## 1. 요약 (가장 큰 차이 3개와 우선순위)

### 가장 큰 차이 3개
1. **manifest 기반 expected 컬럼 강제 표시가 Test 탭 단독.**
   RunOCR Preview는 fix8로 `tableMeta.expectedColumnKeys → tableMeta.columns → hasValue` 까지는 동등하지만,
   manifest(`invoiceProfile.tableExpectedColumns.display/required`)는 사용하지 않는다.
   백엔드가 `_tec`을 받지 못한 경우 RunOCR 응답에 `expectedColumnKeys`가 빠질 수 있어
   동일 파일임에도 Test 탭과 컬럼 셋·헤더 라벨이 달라진다 (특히 1.jpg 한글 헤더 라벨).
2. **expected vs actual 비교 표시(rowCount, missing 컬럼, valueMappingWarnings)가 Preview에 거의 없음.**
   Test 탭은 `expectedRowCount`와 비교해 정상/부족/초과 색상 배지 + `missing: …` + Warning 배지를 모두 보여주는데,
   RunOCR Preview에는 "(N행)"만 표시되고 미스매치/누락은 노출되지 않는다.
3. **preprocessingDebug/autoApplyPreprocessing/Template gridMode·stopKeywords 디버그가 Preview에 미연결.**
   Test 탭은 `PreprocessingDebugPanel`로 전처리 후보 비교를 보여주고, 백엔드는 RunOCR 템플릿 경로에서
   `variableGridExpanded`/`stopKeywordHit`/`tableDebug`를 응답에 포함하지만 Preview UI가 이를 표시하지 않는다.

### 우선 수정 권장
- **P0**
  - A. RunOCR Preview에 manifest 미사용으로 인한 컬럼 셋·라벨 불일치 — 결과적으로 사용자가 "값이 있는데 안 나오는 컬럼/필요 없는 컬럼"을 보게 됨.
  - B. Preview에 expectedRowCount 비교 배지(정상/부족/초과) 추가.
  - C. Preview에 `valueMappingWarnings` / missing required 컬럼 표시.
- **P1**
  - F. `preprocessingDebug` 표시 (RunOCR도 백엔드에 옵션 전달하면 즉시 보일 수 있음).
  - E. Preview에 `variableGridExpanded`/`stopKeywordHit`/`extractionSource` 디버그 배지.
  - H. History 상세 보기 — `tableRows`/`tableMeta`/`valueMappingWarnings`가 History에 저장되지 않음.
- **P2**
  - D. documentType 표시 — RunOCR Preview에서 백엔드가 결정한 `doc_type`/template documentType을 항상 노출.
  - G. INVOICE_FIELD_KO 라벨 사전이 manifest `display.label`(예: "품목코드","보험No")과 동기화되지 않음.

---

## 2. 전체 분석 표 (요약)

| ID | 항목 | 상태 | 한 줄 요약 |
|----|------|------|------------|
| A | tableRows 표시 컬럼 | PARTIAL | fix8로 tableMeta-기반 동등화 완료. 그러나 manifest `display` 라벨/순서 미적용. |
| B | rowCount exact 표시 | TEST_ONLY | Test 탭은 expected/exact/short/over 배지. Preview는 "N행"만. |
| C | missing field / warning 집계 | TEST_ONLY | DocTypeSummary와 InvoiceTableRowsPanel 모두 Test 전용. Preview·Validation 미반영. |
| D | documentType 처리 | PARTIAL | template→formData→backend 우선순위는 적용 (UploadWorkspace.tsx:816), Preview UI 표시 없음. |
| E | Template table mode/stopKeywords/colGuides | APPLIED | 저장/응답까지 완료. Preview 디버그 노출만 없음. |
| F | preprocessingDebug/autoApply | TEST_ONLY | Test 탭만 옵션 전달·표시. RunOCR은 form-data 전달 자체 없음. |
| G | field label 표시 | PARTIAL | resolveFieldLabel + INVOICE_FIELD_KO 사용. manifest fieldLabels/display.label과 미연결. |
| H | History 저장 구조 | MISMATCH | `tableRows`/`tableMeta`/`valueMappingWarnings`/`docType` 미저장. DetailHistoryView 표시 불가. |

---

## 3. 항목별 상세 분석

### A. tableRows 표시 컬럼  — PARTIAL

- **Test 탭 위치**
  - 컬럼 결정: `mysuit-ocr/src/components/test/TestWorkspace.tsx:4634` `getDisplayTableColumns()`
  - manifest expected 키 추출: `TestWorkspace.tsx:4546` `getManifestExpectedColKeys`, `:4571` `getManifestDisplayLabelMap`
  - 라벨 사전: `TestWorkspace.tsx:4581` `CUSTOM_COL_LABELS`, `:4738` `colLabelMap` (manifest display labels 최우선)
  - 렌더 패널: `TestWorkspace.tsx:4692` `InvoiceTableRowsPanel`
  - displayMode 자동 전환: `TestWorkspace.tsx:4716` useEffect → `"expected"`
- **실제 화면 위치 (RunOCR Preview)**
  - 컬럼 결정: `mysuit-ocr/src/components/upload/OcrResultPanel.tsx:189` `buildTableColsFromMeta`, `:212` `buildInvoiceDisplayCols`
  - post-filter: `OcrResultPanel.tsx:122` `filterInvoicePreviewDisplayCols`
  - 렌더: `OcrResultPanel.tsx:1014` previewTableFields map (fix8 적용)
  - 라벨 사전: `OcrResultPanel.tsx:177` `_ALL_COL_LABEL_MAP` (canonical+custom만, manifest display.label 미포함)
- **차이 내용**
  - fix8로 TestWorkspace의 1·2·3순위 (manifestExpectedColKeys → tableMeta.expectedColumnKeys → tableMeta.columns)
    중 2·3순위는 RunOCR에서도 동일하게 동작한다.
  - 1순위인 manifest `tableExpectedColumns.display/required`는 RunOCR에서 **사용되지 않는다** (의도된 차이: 외부 파일 처리 위함).
  - RunOCR이 백엔드에 `tableExpectedColumns`를 보내지 않으므로 백엔드 `_tec` lookup이 main.py:2473 분기로 fallback (콜가이드+manifest lookup) 되어
    파일이 manifest에 있을 때만 `expectedColumnKeys`가 응답에 채워진다. 즉 RunOCR에서 임의 파일을 OCR하면 `tableMeta.expectedColumnKeys`는 비어 있을 수 있다.
  - Manifest의 `display.label`(예: rowIndex→"NO", insuranceCode→"보험No")이 Preview에 반영되지 않으므로 canonical 라벨(`순번`, `보험코드`)이 노출된다.
- **사용자 영향**
  - 1.jpg의 RunOCR 결과는 manifest "display"(itemName/spec/manufacturingNo/expiryDate/quantity/unitPrice/amount)와 일치하는 컬럼이 나올 수 있지만 헤더 라벨이 "품목"이 아닌 "품목명"으로 표시된다.
  - 2.pdf처럼 백엔드가 column_guides path로 `expectedColumnKeys`를 채우면 컬럼 키는 같지만 라벨이 만점이 안 됨(rowIndex→"순번"이 manifest의 "NO"와 다름).
  - 외부에서 가져온 임의 invoice 이미지는 Preview에서 hasValue fallback+post-filter가 가동되어 Test 탭(전체 canonical 18개 옵션 가능)과 표시 컬럼이 차이가 큼.
- **위험도**: 중간
- **추천 수정 방향**
  - `OcrResultPanel`에 manifest lookup props/hook 추가하거나, 백엔드 응답에 `displayLabels` 맵을 추가해 라벨까지 함께 내려주는 방향.
  - 단기 fix: `buildTableColsFromMeta` 결과에 `tableMeta.displayLabels`(백엔드 신규) 우선 적용.

### B. rowCount exact 표시  — TEST_ONLY

- **Test 탭 위치**: `TestWorkspace.tsx:4805` (`expRow` 비교 → `exact/short/over/unknown` 배지, 색상 #22c55e/#f59e0b/#ef4444)
- **실제 화면 위치 (RunOCR Preview)**: `OcrResultPanel.tsx:1027` `{docTableRows.length}행` 만 표시. expectedRowCount 비교 없음.
- **차이 내용**: `invoiceProfile.expectedRowCount`를 Preview가 읽을 수 없음 (manifest 미참조). 백엔드 응답 `document_fields.rowCount`만 사용.
- **사용자 영향**: 2.pdf 13행/4.pdf 1행 같이 manifest 기대값과 행 수 일치 여부를 RunOCR 사용자가 알 수 없음.
- **위험도**: 중간 (validation 가시성)
- **추천 수정 방향**: 백엔드 응답에 `expectedRowCount`/`rowCountMatchStatus` 키를 포함시키거나, 프런트에서 manifest 조회 추가.

### C. missing field / warning 집계  — TEST_ONLY

- **Test 탭 위치**
  - `TestWorkspace.tsx:4760` `manifestMissingRequired` 계산
  - `TestWorkspace.tsx:4850` `valueMappingWarnings` 배지
  - 도큐먼트타입 요약: `TestWorkspace.tsx:1389~1417`, 표시 `TestWorkspace.tsx:5998~6034` (Missing top6 / Warn top6)
- **실제 화면 위치 (RunOCR Preview)**
  - `OcrResultPanel.tsx`에서 `valueMappingWarnings`/`missingExpectedColumnKeys` 처리 없음.
  - Validation 탭은 `field.value`/`field.confidence`만 기준으로 success/warning/error 분류.
- **차이 내용**: 백엔드는 `tableMeta.valueMappingWarnings`/`missingExpectedColumnKeys`를 채워서 보내지만 Preview/Validation UI가 이를 표시하지 않는다.
- **사용자 영향**: 1.jpg `itemCode` 거의 빈값, 2.pdf `mfgNo` 전부 빈값 같은 매핑 실패가 화면에 노출되지 않음. 검수자가 OCR 누락을 알 수 없음.
- **위험도**: 높음 (품질 가시성)
- **추천 수정 방향**: Preview 표 위/Validation 탭 상단에 `tableMeta` 기반 missing/warning 카드 추가.

### D. documentType 처리  — PARTIAL

- **Test 탭 위치**: manifest item.documentType을 직접 사용 (`InvoiceTableRowsPanel`은 manifest 객체 props로 받음).
- **Template 저장**
  - `mysuit-ocr/src/components/ocr/OcrAnnotator.tsx:24,66,103` documentType state + auto-detect.
  - `mysuit-ocr/src/components/ocr/OcrRightPanel.tsx:12,32,233,235` UI select.
  - `mysuit-ocr/src/components/ocr/core/export.ts:18,28` 저장 payload에 `documentType` 포함.
- **RunOCR 전달**: `UploadWorkspace.tsx:815~818` `if (activeTemplate?.documentType) formData.append("documentType", ...)` — OK.
- **백엔드 우선순위**: `ocr-server/main.py:2020~2034` `_explicit_doc_type or _template_doc_type or _classified_doc_type` — OK.
- **차이 내용**: 라우팅 우선순위까지는 모두 적용됨. 다만 RunOCR Preview UI는 `result.doc_type`을 노출하지 않음 (Test 탭 DocumentDetailPanel에는 PROFILE 배지로 표시됨).
- **사용자 영향**: 잘못 분류돼도 사용자가 인지하기 어려움.
- **위험도**: 낮음~중간
- **추천 수정 방향**: Preview 헤더 영역에 `doc_type` 배지 1줄 추가.

### E. Template table mode/stopKeywords/columnGuides  — APPLIED

- **Template 저장 payload**: `mysuit-ocr/src/components/ocr/core/export.ts:61~84` colGuides/mode/stopKeywords/colX/tableName/columns 모두 포함.
- **백엔드 처리**:
  - `ocr-server/main.py:2447~2466` Template region → `colX` 스케일링, `mode`, `stopKeywords` 전파.
  - `ocr-server/main.py:1502` `_ocr_table_region` colGuides 사용.
  - 가변 그리드: `ocr-server/extractors/invoice_statement.py:2548~2653` mode/stopKeywords로 row 중단.
- **RunOCR Preview 표시**: `tableDebug`/`variableGridExpanded`/`stopKeywordHit` 등이 응답에 포함되지만 OcrResultPanel에서 노출 없음.
- **차이 내용**: 데이터 경로는 완벽하나, 사용자 디버그 가시성이 Test 탭/Annotator 화면에만 머무름.
- **사용자 영향**: 정지 키워드/가변 그리드가 의도대로 작동했는지 RunOCR 단독으로는 확인 불가.
- **위험도**: 낮음
- **추천 수정 방향**: Preview 표 옆에 작은 디버그 토글로 `extractionSource`/`stopKeywordHit`/`variableGridExpanded` 노출.

### F. preprocessingDebug / autoApplyPreprocessing  — TEST_ONLY

- **Test 탭 위치**
  - 옵션 전달: `TestWorkspace.tsx:785~793` form-data `debugPreprocessing`, `autoApplyPreprocessing`, `qualityTagsJson`.
  - state UI: `TestWorkspace.tsx:938~939, 2344~2349`.
  - 응답 매핑: `TestWorkspace.tsx:816` `preprocessingDebug: data.preprocessingDebug`.
  - 표시: `TestWorkspace.tsx:3096` `<PreprocessingDebugPanel debug={selOcr.preprocessingDebug} />`.
- **RunOCR 전달**: `UploadWorkspace.tsx:798~828` runOcr() — `debugPreprocessing`/`autoApplyPreprocessing`을 form-data에 전달하지 않음.
- **OcrResultPanel 표시**: 없음.
- **차이 내용**: 동일 백엔드 옵션이 RunOCR 흐름에선 호출 자체가 안 일어남.
- **사용자 영향**: RunOCR에서 흐림/저대비 등 입력 품질 분석을 못 함.
- **위험도**: 낮음 (Test 탭에서 별도로 가능)
- **추천 수정 방향**: RunOCR에 옵션 토글 + Preview에 PreprocessingDebugPanel 재사용.

### G. field label 표시  — PARTIAL

- **Test 탭 위치**
  - `TestWorkspace.tsx`에서 `INVOICE_FIELD_KO`(`mysuit-ocr/src/lib/invoiceFieldLabels.ts:1`) + `CUSTOM_COL_LABELS` + manifest `display.label` 3중 병합.
- **실제 화면 위치 (RunOCR Preview)**
  - `OcrResultPanel.tsx:551` `fieldLabel` → `resolveFieldLabel` 사용 (`invoiceFieldLabels.ts:42`). 우선순위 ko prop > INVOICE_FIELD_KO > en > name.
  - Template region이 `koField`를 가지면 일관 표시되지만, 가지지 않은 region(분리되지 않은 OCR 라인) 또는 canonical 키만 가진 경우는 INVOICE_FIELD_KO에 의존.
- **Template region 저장 우선순위**: `mysuit-ocr/src/components/ocr/core/export.ts:44~47` `koField/enField/canonicalField` 그대로 저장.
- **차이 내용**: INVOICE_FIELD_KO가 manifest의 `display.label`(예: `보험No`)을 알지 못해, 동일 키라도 Test 탭과 RunOCR이 라벨 다르게 표시.
- **사용자 영향**: 라벨 텍스트 불일치 (의미 통일 안 됨). 동일 키이므로 데이터 분석엔 영향 없음.
- **위험도**: 낮음
- **추천 수정 방향**: invoiceFieldLabels.ts에 manifest `display.label` 우선 사용 옵션 추가하거나, 백엔드가 응답에 `displayLabels` 동봉.

### H. History 저장 구조  — MISMATCH

- **TestWorkspace 결과**: History에 저장되지 않음 (Test 탭은 검증 패널 전용, 별도 영속화 없음).
- **RunOCR 저장**: `UploadWorkspace.tsx:1008~1022` `appendHistoryRun`.
  - 저장 필드: `image_url`, `original_image_url`, `processed_image_url`, `ocr_fields`(raw OCR), `output_fields`(template/receipt_fields), `autofill_summary`.
- **historyStore.ts**: HistoryRunRecord 정의 (`historyStore.ts:61~77`)에는 `tableRows`/`tableMeta`/`document_fields`/`doc_type`/`valueMappingWarnings` 필드 자체가 **없음**.
- **차이 내용**: invoice_statement 표 추출 결과가 history에 영속화되지 않으므로 DetailHistoryView에서 표 미리보기/검수 불가.
- **사용자 영향**: 과거 RunOCR 결과에서 행 데이터를 다시 보거나 검수 통계를 누적할 수 없음.
- **위험도**: 높음 (장기 데이터 자산화)
- **추천 수정 방향**: `HistoryRunRecord`에 `document_fields`/`doc_type`/`table_meta` 옵션 필드 추가, `appendHistoryRun` 호출 시 함께 저장. DB 전환 전 임시.

---

## 4. 1.jpg / 2.pdf / 4.pdf tableRows 표시 차이 비교

### 4.1 1.jpg (28행, itemCode 거의 빈값, lotNo≈mfgNo prefix-match)

| 영역 | Test 탭 | RunOCR Preview (fix8) | 차이 |
|------|---------|----------------------|------|
| 컬럼 셋 | manifest `display`: itemName, spec, manufacturingNo, expiryDate, quantity, unitPrice, amount | tableMeta.expectedColumnKeys(있으면 위와 동일) → 없으면 hasValue fallback + post-filter | 정상 케이스 동일, fallback 케이스 itemCode 컬럼이 majority rule(<5% meaningful)로 숨김 처리됨 |
| 헤더 라벨 | manifest "품목" "규격" "제조번호" "유효기간" "수량" "단가" "금액" | canonical "품목명" "규격" "제조번호" "유효기간" "수량" "단가" "금액" | "품목" vs "품목명" 차이 (manifest 미반영) |
| rowCount | "행 수: 28 / 기대 28 · 정상" 녹색 배지 | "28행" (회색 텍스트) | expected 비교 누락 |
| missing 컬럼 | 0개 missing → 표시 없음 | 동일하게 표시 없음 | 동일 |
| valueMappingWarnings | 배지로 표시 | 미표시 | gap |

### 4.2 2.pdf (13행, itemCode "OP-…" 유의미, mfgNo 전부 빈값, lotNo column misidentification 노이즈)

| 영역 | Test 탭 | RunOCR Preview (fix8) | 차이 |
|------|---------|----------------------|------|
| 컬럼 셋 | manifest `display`: rowIndex, itemCode, itemName, quantity, consumerUnitPrice, supplyUnitPrice, supplyAmount, insuranceCode | tableMeta.expectedColumnKeys(백엔드가 column_guides+manifest lookup으로 채움 → 동일) → 없으면 hasValue + post-filter | manifest 미사용 분기에서 lotNo 노이즈 컬럼은 `isLotNoiseFromItemCodeTable`로 자동 제거 |
| 헤더 라벨 | "NO" "품목코드" "품목명" "수량" "소비자단가" "공급단가" "공급금액" "보험No" | "순번" "품목코드" "품목명" "수량" "소비자단가" "공급단가" "공급금액" "보험코드" | "NO"→"순번", "보험No"→"보험코드" 차이 |
| rowCount | "13 / 기대 13 · 정상" | "13행" | expected 비교 누락 |
| missing required | mfgNo 등 일부 표시 | 표시 없음 | gap |
| warning | "Warning: ocr_source_missing: …" 노출 | 노출 없음 | gap |

### 4.3 4.pdf (1행, serialNo만 있음, totalAmount 값 있음, party 깨짐)

| 영역 | Test 탭 | RunOCR Preview (fix8) | 차이 |
|------|---------|----------------------|------|
| 컬럼 셋 | manifest `display`: itemName, lotNo, unit, quantity, unitPrice, supplyAmount, taxAmount | expectedColumnKeys(채워지면 동일) → fallback에선 hasValue 기반으로 lotNo 빈값이라 제거될 수 있음 | manifest 미반영 시 lotNo 컬럼이 hasValue=false로 사라짐 |
| 헤더 라벨 | manifest "품목명" "LotNo." "단위" "수량" "단가" "공급가액" "세액" | canonical "품목명" "LOT/제조번호" "단위" "수량" "단가" "공급금액" "세액" | "LotNo."→"LOT/제조번호", "공급가액"→"공급금액" 라벨 차이 |
| rowCount | "1 / 기대 1 · 정상" | "1행" | expected 비교 누락 |
| missing | required `lotNo` 비었으면 "missing: LotNo.(lotNo)" 표기 | 표기 없음 | gap |
| warning | party_garbled 케이스에서 warning 노출 가능 | 미노출 | gap |
| serialNo 표시 | manifest required에 serialNo 없음 → expected 모드면 숨김 | hasValue 기반은 표시 후 majority rule로 lotNo 중복 시 제거 | 동작 다름 (manifest 우선 적용 시 더 명확) |

---

## 5. 미수정 영역 확인

- 활성 분석 파일:
  - `mysuit-ocr/src/components/test/TestWorkspace.tsx` — 읽기 전용
  - `mysuit-ocr/src/components/upload/OcrResultPanel.tsx` — 읽기 전용 (fix8 상태 확인)
  - `mysuit-ocr/src/components/upload/UploadWorkspace.tsx` — 읽기 전용
  - `mysuit-ocr/src/components/ocr/OcrAnnotator.tsx`, `OcrRightPanel.tsx`, `core/export.ts` — 읽기 전용
  - `mysuit-ocr/src/lib/historyStore.ts`, `invoiceFieldLabels.ts`, `profiles.ts` — 읽기 전용
  - `ocr-server/main.py`, `ocr-server/extractors/invoice_statement.py` — 읽기 전용
  - `mysuit-ocr/public/data/testsets/invoice_statement/manifest.json` — 읽기 전용
- 백업 파일(`*_before_*.tsx`, `main_20260517_before_TGrid1.py`)은 본 분석 대상에서 제외.
- 본 audit 단계에서 **코드/설정/JSON/Markdown(기존)/DB/이미지 파일 일체 미수정**.
  Edit/Write 사용은 본 리포트 2개(.md, .json) 신규 작성에만 사용.

코드 수정 없음 확인: docs 폴더에 신규 2개 파일만 생성됨. `OCR/main.py / extractors/invoice_statement.py / OcrResultPanel / TestWorkspace / Template (OcrAnnotator·OcrRightPanel·export.ts) / RunOCR (UploadWorkspace) / DB / JSON / Markdown 기존 파일 전부 미수정`.
