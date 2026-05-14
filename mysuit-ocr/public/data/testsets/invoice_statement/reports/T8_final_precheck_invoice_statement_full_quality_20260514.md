# T-8-final-precheck 거래명세서 전체/표 품질 최종 점검

## 1. 생성 파일
- `c:\OCR\mysuit-ocr\public\data\testsets\invoice_statement\reports\T8_final_precheck_invoice_statement_full_quality_20260514.md`
- `c:\OCR\mysuit-ocr\public\data\testsets\invoice_statement\reports\T8_final_precheck_invoice_statement_full_quality_20260514.json`
- `C:\OCR\ocr-server\scripts\verify_invoice_statement_full_quality_t8_final_precheck.py`

## 2. 검증 방식
- API 실행 여부: 실제 API 실행
- API: `http://127.0.0.1:8130/ocr/extract`
- 사용 데이터: `c:\OCR\mysuit-ocr\public\data\testsets\invoice_statement`, `manifest.json`, 최신 T-8a/T-8b 리포트 보조 확인
- 한계: 실제 API 응답 기준으로 전체 문서 필드와 tableRows를 전수 집계함

## 3. 전체 요약
| 항목 | 결과 |
|---|---|
| rowCount exact | 7/7 |
| 전체 필드 주요 누락 | buyerBizNumber, buyerRepresentative, cumulativeAmount, cumulativeBalance, previousBalance, subtotal, supplierAddress, supplierBizNumber 외 7 |
| tableRows 주요 누락 | amount, insuranceCode, lotNo, manufacturer, manufacturingExpiryComposite, manufacturingNo, quantity, remark, serialNo, spec 외 5 |
| 금액 오배치 | 실제 오배치 없음 |
| warning 개수 | 6 |
| 코드 수정 필요 여부 | 심각한 회귀 없음, 코드 수정 없이 후속 후보로 분리 |

## 4. 전체 문서 필드 점검
| 샘플 | filled fields | 주요 missing | 이상 의심 | 판정 |
|---|---:|---|---|---|
| 1.jpg | 15 | buyerBizNumber, supplyAmount, taxAmount, previousBalance, transactionAmount 외 2 | - | pass |
| 2.pdf | 14 | supplyAmount, taxAmount, subtotal, cumulativeAmount, previousBalance 외 3 | - | pass_with_warning |
| 3.pdf | 14 | supplierBizNumber, supplierAddress, subtotal, cumulativeAmount, previousBalance 외 3 | - | acceptable_limit |
| 4.pdf | 16 | subtotal, cumulativeAmount, previousBalance, transactionAmount, cumulativeBalance 외 1 | - | pass_with_warning |
| 5.pdf | 16 | subtotal, cumulativeAmount, previousBalance, transactionAmount, cumulativeBalance 외 1 | - | acceptable_limit |
| 6.pdf | 9 | supplierCompany, supplierBizNumber, supplierRepresentative, supplierAddress, supplyAmount 외 8 | - | pass |
| 7.pdf | 13 | buyerRepresentative, supplyAmount, taxAmount, totalAmount, subtotal 외 4 | - | pass |

## 5. tableRows rowCount 점검
| 샘플 | GT | OCR | extractionSource | 상태 |
|---|---:|---:|---|---|
| 1.jpg | 28 | 28 | expected_columns_header_match | exact |
| 2.pdf | 13 | 13 | op_anchor_reconstructed_table | exact |
| 3.pdf | 1 | 1 | legacy_text_items | exact |
| 4.pdf | 1 | 1 | expected_columns_header_match | exact |
| 5.pdf | 6 | 6 | legacy_text_items | exact |
| 6.pdf | 6 | 6 | expected_columns_header_match | exact |
| 7.pdf | 1 | 1 | expected_columns_header_match | exact |

## 6. expected value fill 점검
| 샘플 | fill rate | filled keys | missing keys | 판정 |
|---|---:|---|---|---|
| 1.jpg | 60.4% | itemName, spec, manufacturingNo, expiryDate, quantity, unitPrice, amount, lotNo | unit, supplyAmount, taxAmount, totalAmount, remark | pass |
| 2.pdf | 44.8% | rowIndex, itemCode, itemName, quantity, consumerUnitPrice, supplyUnitPrice, supplyAmount | insuranceCode, amount, totalAmount, remark | pass_with_warning |
| 3.pdf | 16.7% | rowIndex, itemName | insuranceCode, spec, quantity, unitPrice, amount, manufacturer, manufacturingExpiryComposite, lotNo 외 2 | acceptable_limit |
| 4.pdf | 80.0% | itemName, lotNo, unit, quantity, unitPrice, supplyAmount, taxAmount, totalAmount | amount, remark | pass_with_warning |
| 5.pdf | 48.1% | itemName, itemCode, quantity, unitPrice, amount | supplyAmount, taxAmount, totalAmount, remark | acceptable_limit |
| 6.pdf | 50.0% | rowIndex, itemCode, itemName, quantity, lotNo, expiryDate | serialNo, manufacturingNo, unit, remark | pass |
| 7.pdf | 66.7% | itemName, serialLotComposite, unit, quantity | manufacturingNo, remark | pass |

## 7. 샘플별 상세 점검
### 1.jpg
- 전체 필드: filled 15, suspicious -
- tableRows: rowCount 28 유지. display 핵심 컬럼은 대부분 채움. optional summary/table column 미존재는 정상 한계.
- firstRows: `[{"itemName": "헥사메던액0.12%", "spec": "15m|*6포", "manufacturingNo": "24027", "expiryDate": "20270205", "quantity": "400", "unitPrice": "1,050", "amount": "420,000"}, {"itemName": "더모픽스크림", "spec": "30g", "manufacturingNo": "24001", "expiry...`
- lastRows: `[{"itemName": "씬지로이드정0.025ng", "spec": "100T", "manufacturingNo": "24001-240ea", "expiryDate": "270107", "quantity": "240", "unitPrice": "2,180", "amount": "523,200"}, {"itemName": "부광실데나필정50mg", "spec": "4T", "manufacturingNo": "23001-3...`
- warning: -
- 판정: pass

### 2.pdf
- 전체 필드: filled 14, suspicious -
- tableRows: OP-anchor reconstruction 유지. OP-* itemCode 복구. insuranceCode는 비어 있으며 ocr_source_missing warning으로 분류.
- firstRows: `[{"rowIndex": 1, "itemCode": "OP-NA0300", "itemName": "NAPROXO [ABLEr 30UT24O", "quantity": "73", "consumerUnitPrice": "30,360", "supplyUnitPrice": "30,360"}, {"rowIndex": 2, "itemCode": "OP-NA0030", "consumerUnitPrice": "3,036", "supply...`
- lastRows: `[{"rowIndex": 12, "itemCode": "P-AL_0500", "quantity": "2", "consumerUnitPrice": "24,200", "supplyUnitPrice": "24,200"}, {"rowIndex": 13, "itemCode": "P-AF0100", "itemName": "금", "consumerUnitPrice": "14,080", "supplyUnitPrice": "14,080"}]`
- warning: insuranceCode:ocr_source_missing:보험No OCR 원문에서 보험코드 후보를 찾...
- 판정: pass_with_warning

### 3.pdf
- 전체 필드: filled 14, suspicious -
- tableRows: rowCount 1 유지. itemName 유지, garbage quantity 제거 상태. OCR/구조 한계로 fill rate 낮음.
- firstRows: `[{"rowIndex": 1, "itemName": "에스피씨세파클러캡슬250mg30 캡슐 0묘"}]`
- lastRows: `[{"rowIndex": 1, "itemName": "에스피씨세파클러캡슬250mg30 캡슐 0묘"}]`
- warning: insuranceCode:ocr_source_missing:보험No OCR 원문에서 보험코드 후보를 찾...
- 판정: acceptable_limit

### 4.pdf
- 전체 필드: filled 16, suspicious -
- tableRows: rowCount 1 유지. lotNo/unit/quantity 유지. taxAmount=2,576,000 및 totalAmount=28,338,000 pushdown 확인.
- firstRows: `[{"itemName": "중욕명", "lotNo": "0350823-231024-200811", "unit": "BOX", "quantity": "1,000", "unitPrice": "28,338.00", "supplyAmount": "25,760,000", "taxAmount": "2,576,000"}]`
- lastRows: `[{"itemName": "중욕명", "lotNo": "0350823-231024-200811", "unit": "BOX", "quantity": "1,000", "unitPrice": "28,338.00", "supplyAmount": "25,760,000", "taxAmount": "2,576,000"}]`
- warning: taxAmount=doc_level_pushdown, totalAmount=doc_level_pushdown
- 판정: pass_with_warning

### 5.pdf
- 전체 필드: filled 16, suspicious -
- tableRows: T-8a 다단 layout 후처리 적용. itemName/itemCode/unitPrice/amount 6/6, quantity 2/6. supply/tax/total은 row 연결 한계.
- firstRows: `[{"itemName": "노루모에프내복액75ML", "itemCode": "NPRT1OT", "unitPrice": "4,000", "amount": "100,000"}, {"itemName": "나프록센나트롭정10T100", "itemCode": "INAP250G", "quantity": "213", "unitPrice": "400,000", "amount": "273,000"}, {"itemName": "노루모에스산...`
- lastRows: `[{"itemName": "두피나액30ML", "itemCode": "NRDA4P", "unitPrice": "2,000", "amount": "1,650,000"}, {"itemName": "노루모에이스산250G캔", "itemCode": "NASP15P", "unitPrice": "2,730", "amount": "460,000"}]`
- warning: multiline_layout_mapping_applied, quantity:ambiguous_numeric_candidates:quantity candidates...
- 판정: acceptable_limit

### 6.pdf
- 전체 필드: filled 9, suspicious -
- tableRows: rowCount 6 유지. ANDC300C 포함 마지막 row 유지. optional serial/manufacturing/unit/remark missing 정상.
- firstRows: `[{"rowIndex": 1, "itemCode": "ATT100T", "itemName": "알코텔정100T", "quantity": "5", "lotNo": "24001", "expiryDate": "270305"}, {"rowIndex": 2, "itemCode": "ATGT3OT", "itemName": "액티글리정30T", "quantity": "10", "lotNo": "23001", "expiryDate": ...`
- lastRows: `[{"rowIndex": 5, "itemCode": "ALG30P", "itemName": "알드린현탁액1.5G30P"}, {"rowIndex": 6, "itemCode": "ANDC300C", "itemName": "앤디락생캡슬300C"}]`
- warning: -
- 판정: pass

### 7.pdf
- 전체 필드: filled 13, suspicious -
- tableRows: rowCount 1 유지. serialLotComposite/unit/quantity=1,000 유지. 1,000은 금액이 아닌 수량으로 분류.
- firstRows: `[{"itemName": "클리마토플란정", "serialLotComposite": "0350623-231024-260811", "unit": "BOX", "quantity": "1,000"}]`
- lastRows: `[{"itemName": "클리마토플란정", "serialLotComposite": "0350623-231024-260811", "unit": "BOX", "quantity": "1,000"}]`
- warning: -
- 판정: pass

## 8. 금액 계열 점검
| 샘플 | 문제 여부 | 설명 |
|---|---|---|
| 1.jpg | 정상 | 수량/금액 계열 오배치 의심 없음 |
| 2.pdf | 정상 | 수량/금액 계열 오배치 의심 없음 |
| 3.pdf | 정상 | 수량/금액 계열 오배치 의심 없음 |
| 4.pdf | 정상 | row[0] quantity=1,000: comma number, treated as quantity ... |
| 5.pdf | 정상 | 수량/금액 계열 오배치 의심 없음 |
| 6.pdf | 정상 | 수량/금액 계열 오배치 의심 없음 |
| 7.pdf | 정상 | row[0] quantity=1,000: comma number, treated as quantity ... |

## 9. valueMappingWarnings 요약
| 샘플 | key | warning | severity | 후속 |
|---|---|---|---|---|
| 2.pdf | insuranceCode | ocr_source_missing: insuranceCode:ocr_source_missing:보험No OCR 원문에서 보험코드 후보를 찾지 못함 - 빈 값 유지 | warning | source/OCR improvement candidate |
| 3.pdf | insuranceCode | ocr_source_missing: insuranceCode:ocr_source_missing:보험No OCR 원문에서 보험코드 후보를 찾지 못함 - 빈 값 유지 | warning | source/OCR improvement candidate |
| 4.pdf | taxAmount | doc_level_pushdown: taxAmount=doc_level_pushdown | info | monitor |
| 4.pdf | totalAmount | doc_level_pushdown: totalAmount=doc_level_pushdown | info | monitor |
| 5.pdf | - | multiline_layout_mapping_applied: multiline_layout_mapping_applied | info | none |
| 5.pdf | quantity | low_confidence: quantity:ambiguous_numeric_candidates:quantity candidates 3/6; kept existing empty values | info | none |

## 10. 남은 한계
| 샘플 | 한계 | 이유 | 후속 필요성 |
|---|---|---|---|
| 1.jpg | optional amount/summary row columns empty | 문서 표 display에는 해당 컬럼이 없음 | 낮음 |
| 2.pdf | insuranceCode empty | OCR source missing, 억지 생성 금지 | T-9c 후보 |
| 3.pdf | 낮은 fill rate | OCR 품질/구조 한계, 단일 itemName 중심 복구 | T-9b 후보 |
| 4.pdf | doc-level pushdown 의존 | 단일 행 문서에서 summary tax/total을 row에 보강 | 모니터링 |
| 5.pdf | quantity 2/6 및 supply/tax/total row 미연결 | 다단 OCR layout에서 일부 컬럼 연결 한계 | T-9a 후보 |
| 6.pdf | optional missing | 문서 구조상 정상 empty | 낮음 |
| 7.pdf | quantity 1,000 amount-like false positive | 실제 수량 값 | 낮음 |

## 11. 다음 작업 판단
- 심각한 회귀 없음 -> T-8-final 마감 리포트 진행
- Template/RunOCR 실제 저장 annotation 기반 end-to-end 검증은 T-9에서 진행 권장
