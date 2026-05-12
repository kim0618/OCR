# T-6b 거래명세서 샘플별 실제 품목표 컬럼 기준 정리 결과

## 1. 수정 파일
- `src/lib/testsets.ts` — InvoiceProfile에 tableExpectedColumns 필드 추가
- `public/data/testsets/invoice_statement/manifest.json` — 샘플 7개에 tableExpectedColumns 추가
- `src/components/test/TestWorkspace.tsx` — buildTableRowsValidation 샘플 override, TableRowsValidationPanel 주석 추가

## 2. 백업 파일
- `backup/TestWorkspace_20260512_before_T6b_expected_table_columns.tsx`
- `backup/invoice_statement_manifest_20260512_before_T6b_expected_table_columns.json`
- `backup/testsets_20260512_before_T6b_expected_table_columns.ts`

## 3. 핵심 요약
- `InvoiceProfile`에 `tableExpectedColumns?: { required: string[]; optional: string[] }` 필드 추가
- manifest.json의 7개 샘플 각각에 사용자가 눈으로 확인한 실제 품목표 컬럼을 canonical key로 매핑하여 기입
- `buildTableRowsValidation`에서 `invoiceProfile.tableExpectedColumns`를 tableProfile 전역 기준보다 우선 적용
- Actual 판단: `tableMeta.columns`(T-6 backend 감지) 우선, 없으면 tableRows 값 존재 컬럼 fallback
- Missing 판단: required - actual(∪rowValueCols) 기준
- TABLE ROWS PROFILE 패널에 "샘플 기준" 안내 및 Required/Optional/Actual/Missing tooltip 추가
- 이 구조는 `visibleAmountFields` override 패턴과 동일한 방식으로 설계됨

## 4. 샘플별 expected columns
| 샘플 | 실제 표 컬럼 | required canonical | optional canonical |
|---|---|---|---|
| 1.jpg | 품목/규격/제조번호/유효기간/수량/단가/금액 | itemName, spec, manufacturingNo, expiryDate, quantity, unitPrice, amount | lotNo, unit, supplyAmount, taxAmount, totalAmount, remark |
| 2.pdf | NO/품목코드/품목명/수량/소비자단가/공급단가/공급금액/보험No | itemCode, itemName, quantity, unitPrice, supplyAmount, insuranceCode | amount, totalAmount, remark |
| 3.pdf | 순번/보험코드/품명/규격/수량/단가/금액/제조회사/제조번호·유효기간 | insuranceCode, itemName, spec, quantity, unitPrice, amount, manufacturer, manufacturingNo, expiryDate | lotNo, serialNo, remark |
| 4.pdf | 품목명/LotNo./단위/수량/단가/공급가액/세액 | itemName, lotNo, unit, quantity, unitPrice, supplyAmount, taxAmount | amount, totalAmount, remark |
| 5.pdf | 품명/품목코드/수량/단가/금액 | itemName, itemCode, quantity, unitPrice, amount | supplyAmount, taxAmount, totalAmount, remark |
| 6.pdf | NO/제품코드/제품명/수량/LotNo/유효일자 | itemCode, itemName, quantity, lotNo, expiryDate | serialNo, manufacturingNo, unit, remark |
| 7.pdf | 품명/시리얼·로트No./단위/수량 | itemName, serialNo, unit, quantity | lotNo, manufacturingNo, remark |

## 5. TABLE ROWS PROFILE 변경
- **Required 기준**: `invoiceProfile.tableExpectedColumns.required` (있으면) → 없으면 tableProfile 전역 기준
- **Optional 기준**: `invoiceProfile.tableExpectedColumns.optional` (있으면) → 없으면 tableProfile 전역 기준
- **Actual 기준**: `tableMeta.columns`(T-6 backend 감지 컬럼) 우선 → 없으면 tableRows에서 값이 있는 컬럼
- **Missing 기준**: required 컬럼 중 Actual(tableMeta.columns + rowValueCols)에 없는 컬럼
- **sample override 우선순위**: tableExpectedColumns > tableProfile 전역 TABLE_PROFILE_POLICY
- **안내 표시**: tableExpectedColumns가 있으면 패널에 "※ Required/Optional은 이 샘플의 실제 품목표 기준 (T-6b)" 표시

## 6. UI 확인
- **실제 감지 컬럼 모드**: T-6a 유지 — tableMeta.columns 기준 동적 표시
- **값 있는 컬럼 모드**: T-6a 유지 — tableRows 값 존재 기준
- **전체 canonical 18개 모드**: T-6a 유지 — 18개 전부
- **raw JSON 버튼**: 유지

## 7. 기존 기능 영향
| 항목 | 결과 |
|---|---|
| Test 탭 진입 | 유지 |
| invoice_statement 결과 | 샘플별 Required/Missing이 실제 표 기준으로 변경됨 |
| party/address/amount 판정 | 미수정 — 영향 없음 |
| 표 추출 결과 패널 (T-6a) | 유지 |
| 영수증 테스트셋 | 미수정 — 영향 없음 |

## 8. 검증 결과
- **typecheck**: 통과 (오류 0건)
- **build**: 성공 (`/test` 42.2 kB — T-6b 코드 반영)
- **브라우저 확인**: backend(T-6) 재시작 후 샘플별 Required/Missing 확인 필요

## 9. 남은 문제
- backend T-6 감지 성능이 partial이므로 Missing 컬럼이 아직 많을 수 있음 → T-6c/T-7에서 보강
- 2.pdf의 "소비자단가/공급단가"는 canonical unitPrice에 매핑하나 둘 다 있는 구조는 현재 unitPrice 하나로 처리
- 3.pdf의 "제조번호/유효기간" 복합 컬럼은 manufacturingNo + expiryDate 둘 다 required에 포함 — backend에서 분리 감지 필요
- 7.pdf의 "시리얼/로트No." 복합 컬럼은 serialNo required + lotNo optional로 처리 — 실제로는 serialNo가 핵심
- tableMeta.columns 없는 경우(4.pdf 등 OCR garbled)는 rowValueCols fallback이 동작

## 10. 다음 추천 작업
- **T-6c**: backend header canonical 감지 보강 — Missing 컬럼 줄이기 (특히 quantity, lotNo, expiryDate, itemCode)
- **T-7**: 거래명세서 금액 계열 컬럼 매핑 보강 (unitPrice/supplyAmount/taxAmount/amount/totalAmount)
- **RunOCR-Table-1**: RunOCR 거래명세서 tableRows 표시 반영
