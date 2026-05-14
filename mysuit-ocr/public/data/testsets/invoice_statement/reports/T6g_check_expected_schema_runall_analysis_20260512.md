# T-6g-check expected schema 기준 RunAll 결과 분석

## 1. 분석 대상
- 사용한 데이터 소스: manifest.json, reports 디렉터리, ocr_cache.json, API http://127.0.0.1:8172
- API 실행 여부: 실행 (7/7 성공)
- 저장 결과 사용 여부: tableRows/tableMeta 후보 파일 있음
- 한계: ocr_cache.json은 ocr_text 중심이며 좌표 OCR 라인이 없어 실제 row grouping 재현용으로는 부족함

## 2. expected schema 정적 검증
| 샘플 | 목표 count | manifest count | expected columns | 판정 |
|---|---:|---:|---|---|
| 1.jpg | 7 | 7 | 품목 `itemName`, 규격 `spec`, 제조번호 `manufacturingNo`, 유효기간 `expiryDate`, 수량 `quantity`, 단가 `unitPrice`, 금액 `amount` | 일치 |
| 2.pdf | 8 | 8 | NO `rowIndex`, 품목코드 `itemCode`, 품목명 `itemName`, 수량 `quantity`, 소비자단가 `consumerUnitPrice`, 공급단가 `supplyUnitPrice`, 공급금액 `supplyAmount`, 보험No `insuranceCode` | 일치 |
| 3.pdf | 9 | 9 | 순번 `rowIndex`, 보험코드 `insuranceCode`, 품명 `itemName`, 규격 `spec`, 수량 `quantity`, 단가 `unitPrice`, 금액 `amount`, 제조회사 `manufacturer`, 제조번호/유효기간 `manufacturingExpiryComposite` | 일치 |
| 4.pdf | 7 | 7 | 품목명 `itemName`, LotNo. `lotNo`, 단위 `unit`, 수량 `quantity`, 단가 `unitPrice`, 공급가액 `supplyAmount`, 세액 `taxAmount` | 일치 |
| 5.pdf | 5 | 5 | 품명 `itemName`, 품목코드 `itemCode`, 수량 `quantity`, 단가 `unitPrice`, 금액 `amount` | 일치 |
| 6.pdf | 6 | 6 | NO `rowIndex`, 제품코드 `itemCode`, 제품명 `itemName`, 수량 `quantity`, LotNo `lotNo`, 유효일자 `expiryDate` | 일치 |
| 7.pdf | 4 | 4 | 품명 `itemName`, 시리얼/로트No. `serialLotComposite`, 단위 `unit`, 수량 `quantity` | 일치 |

## 3. OCR 결과 수집 상태
| 샘플 | 결과 수집 방식 | 성공 여부 | 비고 |
|---|---|---|---|
| 1.jpg | api | 성공 | status=200, doc_type=invoice_statement |
| 2.pdf | api | 성공 | status=200, doc_type=invoice_statement |
| 3.pdf | api | 성공 | status=200, doc_type=invoice_statement |
| 4.pdf | api | 성공 | status=200, doc_type=invoice_statement |
| 5.pdf | api | 성공 | status=200, doc_type=invoice_statement |
| 6.pdf | api | 성공 | status=200, doc_type=invoice_statement |
| 7.pdf | api | 성공 | status=200, doc_type=invoice_statement |

## 4. 샘플별 rowCount 비교
| 샘플 | 목표 row 수 | 현재 rowCount | 차이 | 판정 |
|---|---:|---:|---:|---|
| 1.jpg | 28 | 29 | +1 | 초과 |
| 2.pdf | 확인 필요 | 2 | ? | 대량 누락 의심 |
| 3.pdf | 확인 필요 | 1 | ? | 이미지 기준 확인 필요 |
| 4.pdf | 확인 필요 | 3 | ? | 이미지 기준 확인 필요 |
| 5.pdf | 6 | 6 | 0 | OK |
| 6.pdf | 6 | 5 | -1 | 부족 |
| 7.pdf | 1 | 1 | 0 | OK |

## 5. 샘플별 컬럼 값 매핑 상태
| 샘플 | 값 있는 컬럼 | 비어 있는 컬럼 | 잘못 들어간 의심 컬럼 | 비고 |
|---|---|---|---|---|
| 1.jpg | itemName, spec, manufacturingNo, expiryDate, quantity, unitPrice, amount |  |  | - |
| 2.pdf | rowIndex, itemName, supplyAmount | itemCode, quantity, consumerUnitPrice, supplyUnitPrice, insuranceCode | itemCode, quantity, consumerUnitPrice, supplyUnitPrice, insuranceCode | consumerUnitPrice: 비어 있음; supplyUnitPrice: 비어 있음 |
| 3.pdf | rowIndex, quantity | insuranceCode, itemName, spec, unitPrice, amount, manufacturer, manufacturingExpiryComp... | insuranceCode, itemName, spec, unitPrice, amount, manufacturer, manufacturingExpiryComp... | manufacturingExpiryComposite: 비어 있음 |
| 4.pdf | itemName, unit, quantity, unitPrice, supplyAmount, taxAmount | lotNo | lotNo | - |
| 5.pdf | itemName, quantity | itemCode, unitPrice, amount | itemCode, unitPrice, amount | - |
| 6.pdf | rowIndex, itemCode, itemName, quantity, lotNo, expiryDate |  |  | - |
| 7.pdf | itemName, serialLotComposite, unit | quantity | quantity | serialLotComposite: 값 있음 |

## 6. tableMeta 요약
| 샘플 | extractionSource | expectedColumnKeys | matchedColumnKeys | valueColumnKeys | missingExpectedColumnKeys |
|---|---|---|---|---|---|
| 1.jpg | expected_columns_header_match | itemName, spec, manufacturingNo, expiryDate, quantity, unitPrice, amount, lotNo, unit, ... | spec, manufacturingNo, expiryDate, quantity, unitPrice | rowIndex, itemCode, itemName, spec, lotNo, manufacturingNo, expiryDate, quantity, unitP... |  |
| 2.pdf | legacy_text_items | rowIndex, itemCode, itemName, quantity, consumerUnitPrice, supplyUnitPrice, supplyAmoun... |  | rowIndex, itemName, spec, supplyAmount, amount | itemCode, quantity, consumerUnitPrice, supplyUnitPrice, insuranceCode |
| 3.pdf | header_column_mapping | rowIndex, insuranceCode, itemName, spec, quantity, unitPrice, amount, manufacturer, man... |  | rowIndex, quantity | insuranceCode, itemName, spec, unitPrice, amount, manufacturer, manufacturingExpiryComp... |
| 4.pdf | expected_columns_header_match | itemName, lotNo, unit, quantity, unitPrice, supplyAmount, taxAmount, amount, totalAmoun... | quantity, supplyAmount | rowIndex, itemName, serialNo, expiryDate, quantity, unit, unitPrice, supplyAmount, taxA... | lotNo |
| 5.pdf | legacy_text_items | itemName, itemCode, quantity, unitPrice, amount, supplyAmount, taxAmount, totalAmount, ... |  | rowIndex, itemName, quantity | itemCode, unitPrice, amount |
| 6.pdf | expected_columns_header_match | rowIndex, itemCode, itemName, quantity, lotNo, expiryDate, serialNo, manufacturingNo, u... | rowIndex, itemCode, itemName, quantity, lotNo, expiryDate | rowIndex, itemCode, itemName, lotNo, expiryDate, quantity |  |
| 7.pdf | expected_columns_header_match | itemName, serialLotComposite, unit, quantity, manufacturingNo, remark | itemName, unit, quantity | rowIndex, itemName, serialNo, expiryDate, unit, serialLotComposite | quantity |

## 7. 샘플별 실패 유형
| 샘플 | 실패 유형 | 원인 추정 | 우선순위 |
|---|---|---|---|
| 1.jpg | row_count_over | row_count_over | P3 |
| 2.pdf | custom_key_empty, value_mapping_wrong | custom_key_empty / value_mapping_wrong | P2 |
| 3.pdf | composite_display_empty, value_mapping_wrong | composite_display_empty / value_mapping_wrong | P2 |
| 4.pdf | value_mapping_wrong | value_mapping_wrong | P2 |
| 5.pdf | value_mapping_wrong | value_mapping_wrong | P2 |
| 6.pdf | row_count_short | row_count_short | P1 |
| 7.pdf | value_mapping_wrong | value_mapping_wrong | P2 |

## 8. 주요 샘플 상세 분석

### 1.jpg
- expected 7개 유지 여부: 유지
- rowCount 28 여부: 현재 29
- 누락 row 추정: 현재 rowCount가 28보다 작으면 row_count_short, API 실패 시 판단 불가
- 값 매핑 상태: 값 있음=itemName, spec, manufacturingNo, expiryDate, quantity, unitPrice, amount; 비어 있음=
- tableDebug 요약: {"fallbackSource": "expected_columns_header_match", "headerRowFound": true, "headerScore": 6, "headerUsed": true, "rejectedRows": {"header_or_contact": 1}}
- tableRows 첫 3개 preview: {'rowIndex': 1, 'itemCode': '', 'itemName': '헥사메던액0.12%', 'spec': '15m\|*6포', 'lotNo': '24027', 'serialNo': '', 'manufacturingNo': '24027', 'expiryDate': '20270205', 'quantity': '400', 'unit': '', 'unitPrice': '1,050'...
- 다음 수정 포인트: 큰 차단 이슈 없음

### 2.pdf
- expected 8개 유지 여부: 유지
- rowCount가 기존 2에서 개선되었는지: 현재 2, 2 이하이면 개선 확인 불가
- 소비자단가/공급단가/공급금액/보험No 분리 가능성: meta/valueColumnKeys와 preview 값 기준으로 판단
- 값 매핑 상태: 값 있음=rowIndex, itemName, supplyAmount; 비어 있음=itemCode, quantity, consumerUnitPrice, supplyUnitPrice, insuranceCode
- tableDebug 요약: {"fallbackSource": "legacy_text_items", "headerRowFound": true, "headerScore": 2, "headerUsed": false, "rejectedRows": {"header_or_contact": 3, "summary_row"...
- tableRows 첫 3개 preview: {'rowIndex': 1, 'itemCode': '', 'itemName': 'LOXOLIFEN', 'spec': 'TABLET 3OT3Z', 'lotNo': '', 'serialNo': '', 'manufacturingNo': '', 'expiryDate': '', 'quantity': '', 'unit': '', 'unitPrice': '', 'supplyAmount': '', '...
- 다음 수정 포인트: expected boundary/value mapping 점검

### 3.pdf
- expected 9개 유지 여부: 유지
- manufacturingExpiryComposite 상태: {'displayable': True, 'nonempty': False, 'sourceKeys': ['manufacturingNo', 'expiryDate']}
- 값 매핑 상태: 값 있음=rowIndex, quantity; 비어 있음=insuranceCode, itemName, spec, unitPrice, amount, manufacturer, manufacturingExpiryComp...
- tableDebug 요약: {"fallbackSource": "header_column_mapping", "headerRowFound": true, "headerScore": 2, "headerUsed": true, "rejectedRows": {"header_or_contact": 2}}
- tableRows 첫 3개 preview: {'rowIndex': 1, 'itemCode': '', 'itemName': '', 'spec': '', 'lotNo': '', 'serialNo': '', 'manufacturingNo': '', 'expiryDate': '', 'quantity': '제조회사 o묘 0 공급받눈재인료관용', 'unit': '', 'unitPrice': '', 'supplyAmount': '', 'ta...
- 다음 수정 포인트: expected boundary/value mapping 점검

### 4.pdf
- expected 7개 유지 여부: 유지
- LotNo/단위/수량/단가/공급가액/세액 상태: 값 있음=itemName, unit, quantity, unitPrice, supplyAmount, taxAmount, 비어 있음=lotNo
- 값 매핑 상태: 값 있음=itemName, unit, quantity, unitPrice, supplyAmount, taxAmount; 비어 있음=lotNo
- tableDebug 요약: {"fallbackSource": "expected_columns_header_match", "headerRowFound": true, "headerScore": 3, "headerUsed": true, "rejectedRows": {"no_item_name": 1, "summar...
- tableRows 첫 3개 preview: {'rowIndex': 1, 'itemCode': '', 'itemName': '중욕명', 'spec': '', 'lotNo': '', 'serialNo': '0350823-231024-200811', 'manufacturingNo': '', 'expiryDate': '231024', 'quantity': 'BOX 1,000', 'unit': '0350823-231024-200811',...
- 다음 수정 포인트: expected boundary/value mapping 점검

### 5.pdf
- expected 5개 유지 여부: 유지
- rowCount 6 유지 여부: 현재 6
- 값 매핑 상태: 값 있음=itemName, quantity; 비어 있음=itemCode, unitPrice, amount
- tableDebug 요약: {"fallbackSource": "legacy_text_items", "headerRowFound": true, "headerScore": 1, "headerUsed": false, "rejectedRows": {}}
- tableRows 첫 3개 preview: {'rowIndex': 1, 'itemCode': '', 'itemName': '노루모에프내복액75ML', 'spec': '', 'lotNo': '', 'serialNo': '', 'manufacturingNo': '', 'expiryDate': '', 'quantity': '', 'unit': '', 'unitPrice': '', 'supplyAmount': '', 'taxAmount...
- 다음 수정 포인트: expected boundary/value mapping 점검

### 6.pdf
- expected 6개 유지 여부: 유지
- rowCount 6 유지 여부: 현재 5
- NO/제품코드/제품명/LotNo/유효일자 상태: 값 있음=rowIndex, itemCode, itemName, quantity, lotNo, expiryDate
- 값 매핑 상태: 값 있음=rowIndex, itemCode, itemName, quantity, lotNo, expiryDate; 비어 있음=
- tableDebug 요약: {"fallbackSource": "expected_columns_header_match", "headerRowFound": true, "headerScore": 8, "headerUsed": true, "rejectedRows": {}}
- tableRows 첫 3개 preview: {'rowIndex': 1, 'itemCode': 'ATT100T', 'itemName': '알코텔정100T', 'spec': '', 'lotNo': '24001', 'serialNo': '', 'manufacturingNo': '', 'expiryDate': '270305', 'quantity': '5', 'unit': '', 'unitPrice': '', 'supplyAmount':...
- 다음 수정 포인트: header band 탐지와 row grouping 후보 조건 점검

### 7.pdf
- expected 4개 유지 여부: 유지
- rowCount 1 유지 여부: 현재 1
- serialLotComposite 상태: {'displayable': True, 'nonempty': True, 'sourceKeys': ['serialNo', 'lotNo']}
- 값 매핑 상태: 값 있음=itemName, serialLotComposite, unit; 비어 있음=quantity
- tableDebug 요약: {"fallbackSource": "expected_columns_header_match", "headerRowFound": true, "headerScore": 5, "headerUsed": true, "rejectedRows": {"no_item_name": 2}}
- tableRows 첫 3개 preview: {'rowIndex': 1, 'itemCode': '', 'itemName': '클리마토플란정', 'spec': '', 'lotNo': '', 'serialNo': '0350623-231024-260811', 'manufacturingNo': '', 'expiryDate': '231024', 'quantity': '', 'unit': 'BOX', 'unitPrice': '', 'supp...
- 다음 수정 포인트: expected boundary/value mapping 점검

## 9. 다음 작업 제안
- 결론: T-6g-fix row grouping 우선
- 후보: T-6g-fix row grouping 우선
- 후보: T-6h expected boundary/value mapping 우선
- 후보: T-6e-fix4 custom/composite value resolver 우선
- 후보: T-6i table bounds 연동 우선
- 후보: T-7 금액 계열로 이동 가능

## 10. 최종 결론
- 현재 상태: API 7/7 성공, schema 일치 7/7
- 가장 큰 병목: T-6g-fix row grouping 우선
- 다음 작업명: T-6g-fix
- 수정 대상 예상 파일: ocr-server/extractors/invoice_statement.py, 필요 시 TestWorkspace.tsx display resolver

### 저장 데이터 메모
- 최신 reports: T6j_check_template_colguides_runocr_20260512.md, T6j_check_template_colguides_direct_control_20260512.raw.json, T6j_check_template_colguides_runocr_20260512.raw.json, T6j_templa...
- tableRows/tableMeta 후보 파일: ground_truth_20260511_before_GT5.json, ground_truth_20260511_before_GTADDR.json, manifest_20260511_before_P2b.json, manifest__before_P1.json, manifest__before_P1_invoiceProfile....
- ocr_cache 좌표 포함 여부: False
