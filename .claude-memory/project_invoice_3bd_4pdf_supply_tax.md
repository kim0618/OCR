---
name: project_invoice_3bd_4pdf_supply_tax
description: 4.pdf 단일행 송장 표 컬럼 매핑 수정(3BD) + free/reference parser 선택 아키텍처
metadata: 
  node_type: memory
  type: project
  originSessionId: ebc95b98-9bcd-4279-9d46-3825a0d20853
---

3BD(2026-06-08): 4.pdf 품목표 1행 컬럼 scramble(단가↔공급가액 swap, 수량 누락, 세액→totalAmount, lot 내부일자 강제 expiryDate) 수정 완료.

**핵심 아키텍처(비자명)**: unstructured invoice의 tableRows는 free 추출기(`invoice_statement_free.py`)가 release gate 통과 시에만 사용되고, 실패하면 `main.py:2968`이 reference parser `invoice_statement.py`로 fallback한다. 4.pdf는 free gate 실패(releaseReadyRatio 0.0) → tableRows가 `invoice_statement.py`(`extractionSource=legacy_text_items`, `_source=invoice_statement_table_parser`)에서 생성됨. 즉 단일행 송장 표 수정은 `invoice_statement.py`의 reconstructor 체인에서 해야 한다(free 아님).

**reconstructor 체인**(invoice_statement.py, 적용 순서): detail(`_apply_legacy_detail_table_reconstruction`, 4~8행) → pharma(`_apply_legacy_single_pharma_reconstruction`, ≤4행+pharma코드) → **3BD 신규** `_apply_legacy_single_supply_tax_reconstruction`(rowCount==1 & legacy_text_items & lot복합값 & unit토큰 & money≥3). 게이트가 shape 기반이라 1/2/3/5/6/7.pdf 무영향(7.pdf는 header_column_mapping이라 제외). 수정 파일 1개(invoice_statement.py)뿐, forbidden 파일 전부 baseline 동일.

**값 모순**: 문서 totalAmount=28,338,000(OCR 푸터 실값)이나 supply+tax=28,336,000(2,000 차이) → 행 totalAmount 미생성(산술 금지), diagnostic 기록.

3BE(2026-06-08): itemName "중욕명" leak **해결**. OCR fields에 "클리마트플란정"(field55)·"중욕명"(field47)이 각각 독립 라인 → `_legacy_st_unmerge_item_name`: 끝 토큰과 prefix가 둘 다 독립 OCR 라인일 때만 끝 토큰 제거(증거 기반, 하드코딩 아님) → itemName="클리마트플란정". unit/세액은 row.tableExtraColumns/sourceRowMeta={unit:BOX,taxAmount}로 보존(2.pdf extra-column shape). **Draft GT export VM 경로(`tableRowsFromViewModel`)는 tableExtraColumns를 드롭** → end-to-end unit 표면화는 프론트 VM wiring 필요(회귀 위험으로 보류). 3BD/3BE 모두 invoice_statement.py 1파일만 수정, 1/2/3/5/6/7 무회귀(reconstructor는 4.pdf만 발동).

3BF(2026-06-08): 4.pdf Preview 기울기 = **deskew over-apply false-positive**. `deskew()`의 cv2.minAreaRect가 표/테두리에 락온되어 원본(거의 수평 -0.25°)에 2.619° 회전을 적용→processed/preview -2.75° 기울임(2.619>3O skip threshold 2.0이라 기존 정책이 못 막음). **핵심 발견: 3BD/3BE의 좋은 1행 테이블은 사실 이 잘못 기울어진 이미지에서 나온 것**이었음 — 회전 교정 시 OCR 입력이 바뀌어 테이블이 2행 legacy로 회귀. 사용자 "통합 수정" 승인. 패치 3파일: (1)preprocess.py `measure_skew_angle`(투영프로파일 독립측정), (2)main.py `PDF_ORIENTATION0_DESKEW_OVERAPPLY_REVERT_GUARD`(deskew 적용분 중 회전이 기울기를 abs(post)>abs(pre)+0.5°로 키운 경우만 회전 전으로 revert; PDF+orient0 scope; 4.pdf만 발동), (3)invoice_statement.py supply_tax 게이트를 `rowCount==1`→`_legacy_st_item_rows`(item-shaped 정확히 1개)로 일반화하여 수평이미지 2행(품목+합계noise)을 1행으로 collapse. 결과: preview 수평+테이블 매핑 보존. **OCR variance**: 수평이미지에서 itemName 한글 글자(트/로)·lotNo 자릿수(0350823↔0360623)가 run마다 달라짐(매핑은 안정). 1/2/3/5/6/7 무회귀.

3BG(2026-06-08): 4.pdf table column display + Draft GT export wiring. backend route는 row.tableExtraColumns{unit:BOX,taxAmount} 항상 내려줬으나 (a)3BF 수평이미지 후 doc-level supplyAmount/taxAmount field 빈값, (b)frontend Draft GT **VM 경로(`tableRowsFromViewModel`)가 tableExtraColumns 드롭**(TableResultRow가 extra 미보유). 수정 3파일: invoice_statement.py(supply_tax 적용시 doc supply/tax를 row값으로 backfill, 산술X), tableResultViewModel.ts(`TableResultRow`에 optional tableExtraColumns/sourceRowMeta + `buildBackendDocumentFieldsViewModel`이 raw row에서 복사, additive), gtDraftBuilder.ts(`tableRowsFromViewModel`이 extra 전달). **display는 무수정** — 기존 `buildInvoicePreviewCols`가 backend tableMeta.columns/columnLabels로 품목명/LOT/단위/수량/단가/공급가액/세액 자동 산출(unit/supply/tax가 값 있으면 hasValue로 표시). invoiceTableDisplay.ts/OcrResultPanel.tsx/main.py/preprocess.py 무수정. 1/2/3/5/6/7 무회귀(extra/backfill 4.pdf만). totalAmount는 수평이미지 footer 미검출로 빈값(diagnostic).

3BJ(2026-06-08, read-only precheck): RunOCR에서 Preview/Custom/Draft-export 표가 **서로 다른 VM selector**를 탐(비자명). Preview=`displayRepresentativeFirstVM`(raw representative; `selectRepresentativeTableResultViewModels` 우선순위 template_region_canonical>unstructured_definition>backend_document_fields, swap 없음). Custom=`chooseCustomTableFieldViewModel(rep,backend)`(3BI: backend가 unit+taxAmount 컬럼 보유&rep 미보유시 backend로 swap). Export=`draftExportTableResultViewModels`→4.pdf는 customTableFieldViewModel(Custom과 정렬). backend는 `unstructuredTables` 미방출(route 확인)→representative≠backend는 **region 템플릿 활성시에만**. root cause=Custom/Export만 backend-extra-aware로 고쳐지고 Preview는 raw representative 유지(비대칭). 추천 single source=`chooseCustomTableFieldViewModel`을 Preview에도 적용(OcrResultPanel.tsx 1파일). swap gate(unit+taxAmount)가 좁아 1/2/3/5/6/7·구조화템플릿 무회귀. 다음=FULL-UNSTRUCTURED-INVOICE-3BK-PREVIEW_TABLE_VM_SELECTION_FIX.

다음: USER_ACTION_REQUIRED_REEXPORT_4PDF_DRAFT_GT. [[project_data_storage_architecture]] [[project_invoice_1q_column_mapping]]
