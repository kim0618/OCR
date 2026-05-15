# T-10 after 6pdf Template/RunOCR E2E 최종 검증 결과

## 1. 생성 파일
- script: `D:\Free_Vue\OCR\ocr-server\scripts\verify_invoice_statement_template_runocr_e2e_t10_after_6pdf.py`
- Markdown report: `D:\Free_Vue\OCR\mysuit-ocr\public\data\testsets\invoice_statement\reports\T10_after_6pdf_template_runocr_e2e_20260515.md`
- JSON report: `D:\Free_Vue\OCR\mysuit-ocr\public\data\testsets\invoice_statement\reports\T10_after_6pdf_template_runocr_e2e_20260515.json`

## 2. 핵심 요약
- 검증 서버: `http://127.0.0.1:9099`
- 전체 샘플: 7
- E2E 실행: 7
- exact: 6
- skipped: 0
- 최종 판단: 일부 over → 해당 샘플 tableBounds 하단 조정 필요

## 3. Template annotation 확인
| 샘플 | selectedTemplateId | selectionReason | documentType | table region | colGuides | 실행 여부 |
|---|---|---|---|---|---|---|
| 1.jpg | TPL-31D13CF3 | documentType=invoice_statement; table region exists; filename matched; latest updatedAt=2026-05-12 14:28:19; last matching record tie-break | invoice_statement | 있음 {"x": 47, "y": 831, "width": 2361, "height": 2317, "yMax": 3148} | 6 | 실행 |
| 2.pdf | TPL-A4585BC7 | documentType=invoice_statement; table region exists; filename matched; latest updatedAt=2026-05-15 13:32:59; last matching record tie-break | invoice_statement | 있음 {"x": 111, "y": 136, "width": 1486, "height": 1080, "yMax": 1216} | 9 | 실행 |
| 3.pdf | TPL-E4B15A22 | documentType=invoice_statement; table region exists; filename matched; latest updatedAt=2026-05-15 15:53:18; last matching record tie-break | invoice_statement | 있음 {"x": 54, "y": 358, "width": 1553, "height": 85, "yMax": 443} | 8 | 실행 |
| 4.pdf | TPL-FD07531C | documentType=invoice_statement; table region exists; filename matched; latest updatedAt=2026-05-15 15:55:34; last matching record tie-break | invoice_statement | 있음 {"x": 276, "y": 806, "width": 1090, "height": 42, "yMax": 848} | 6 | 실행 |
| 5.pdf | TPL-A6B12CED | documentType=invoice_statement; table region exists; filename matched; latest updatedAt=2026-05-15 10:45:03; last matching record tie-break | invoice_statement | 있음 {"x": 68, "y": 39, "width": 1504, "height": 843, "yMax": 882} | 9 | 실행 |
| 6.pdf | TPL-95328E52 | documentType=invoice_statement; table region exists; filename matched; latest updatedAt=2026-05-15 16:19:02; last matching record tie-break | invoice_statement | 있음 {"x": 66, "y": 621, "width": 1515, "height": 277, "yMax": 898} | 5 | 실행 |
| 7.pdf | TPL-3AFD383E | documentType=invoice_statement; table region exists; filename matched; latest updatedAt=2026-05-15 14:31:45; last matching record tie-break | invoice_statement | 있음 {"x": 70, "y": 961, "width": 1513, "height": 72, "yMax": 1033} | 3 | 실행 |

## 4. E2E rowCount 결과
| 샘플 | GT | Test 기준 | RunOCR E2E | 상태 |
|---|---:|---:|---:|---|
| 1.jpg | 28 | 28 | 28 | exact |
| 2.pdf | 13 | 13 | 13 | exact |
| 3.pdf | 1 | 1 | 1 | exact |
| 4.pdf | 1 | 1 | 1 | exact |
| 5.pdf | 6 | 6 | 6 | exact |
| 6.pdf | 6 | 6 | 7 | over |
| 7.pdf | 1 | 1 | 1 | exact |

## 5. tableMeta/debug 결과
| 샘플 | doc_type | extractionSource | tableBoundsUsed | columnGuidesReceived | columnGuidesUsed | warnings |
|---|---|---|---|---|---|---|
| 1.jpg | invoice_statement | template_colguides_expected_columns | true | true | true | [] |
| 2.pdf | invoice_statement | template_colguides_expected_columns | true | true | true | [] |
| 3.pdf | invoice_statement | template_colguides_expected_columns | true | true | true | ["insuranceCode:ocr_source_missing:보험No OCR 원문에서 보험코드 후보를 찾지 못함 - 빈 값 유지"] |
| 4.pdf | invoice_statement | template_colguides_expected_columns | true | true | true | ["totalAmount=doc_level_pushdown"] |
| 5.pdf | invoice_statement | template_colguides_expected_columns | true | true | true | [] |
| 6.pdf | invoice_statement | template_colguides_expected_columns | true | true | true | [] |
| 7.pdf | invoice_statement | template_colguides_expected_columns | true | true | true | [] |

## 6. 샘플별 상세

### 1.jpg
- template: TPL-31D13CF3 (documentType=invoice_statement; table region exists; filename matched; latest updatedAt=2026-05-12 14:28:19; last matching record tie-break)
- bounds: {"x": 47, "y": 831, "width": 2361, "height": 2317, "yMax": 3148}
- rowCount: 28/28
- extractionSource: template_colguides_expected_columns
- columnGuides: received=true, used=true, count=6
- warning: []
- first rows: [{"rowIndex": 1, "itemCode": "", "itemName": "헥사메딘액0.12%", "spec": "15m\|*6포", "lotNo": "24027", "serialNo": "", "manufacturingNo": "24027", "expiryDate": "20270205", "quantity": "400", "unit": "", "unitPrice": "1,050", "supplyAmount": "", "taxAmount": "", "amount": "420,000", "totalAmount": "", "manufacturer": "", "insuranceCode": "", "remark": "", "_rawText": "헥사메딘액0.12% 15m\|*6포 24027 20270205 400 1,050 420,000", "_confidence": null, "_source": "invoice_statement_table_parser", "manufacturingExpiryComposite": "24027 / 20270205", "serialLotComposite": "24027"}, {"rowIndex": 2, "itemCode": "", "itemName": "더모픽스크림", "spec": "30g", "lotNo": "24001", "serialNo": "", "manufacturingNo": "24001", "expiryDate": "20270116", "quantity": "100", "unit": "", "unitPrice": "4,490", "supplyAmount": "", "taxAmount": "", "amount": "449,000", "totalAmount": "", "manufacturer": "", "insuranceCode": "", "remark": "", "_rawText": "더모픽스크림 30g 24001 20270116 100 4,490 449,000", "_confidence": null, "_source": "invoice_statement_table_parser", "manufacturingExpiryComposite": "24001 / 20270116", "serialLotComposite": "24001"}, {"rowIndex": 3, "itemCode": "", "itemName": "하드칼추어블이지정", "spec": "30T", "lotNo": "23010", "serialNo": "", "manufacturingNo": "23010", "expiryDate": "20250601", "quantity": "180", "unit": "", "unitPrice": "1,400", "supplyAmount": "", "taxAmount": "", "amount": "252,000", "totalAmount": "", "manufacturer": "", "insuranceCode": "", "remark": "", "_rawText": "하드칼추어블이지정 30T 23010 20250601 180 1,400 252,000", "_confidence": null, "_source": "invoice_statement_table_parser", "manufacturingExpiryComposite": "23010 / 20250601", "serialLotComposite": "23010"}]
- last rows: [{"rowIndex": 26, "itemCode": "", "itemName": "소아용프리마란시럽", "spec": "500m", "lotNo": "23021", "serialNo": "", "manufacturingNo": "23021-30ea", "expiryDate": "261205", "quantity": "30", "unit": "", "unitPrice": "7,363", "supplyAmount": "", "taxAmount": "", "amount": "220, 890", "totalAmount": "", "manufacturer": "", "insuranceCode": "", "remark": "", "_rawText": "소아용프리마란시럽 500m\| 23021-30ea 261205 30 7,363 220, 890", "_confidence": null, "_source": "invoice_statement_table_parser", "manufacturingExpiryComposite": "23021-30ea / 261205", "serialLotComposite": "23021"}, {"rowIndex": 27, "itemCode": "", "itemName": "씬지로이드정0.025mg", "spec": "100T", "lotNo": "24001", "serialNo": "", "manufacturingNo": "24001-240ea", "expiryDate": "270107", "quantity": "240", "unit": "", "unitPrice": "2,180", "supplyAmount": "", "taxAmount": "", "amount": "523,200", "totalAmount": "", "manufacturer": "", "insuranceCode": "", "remark": "", "_rawText": "씬지로이드정0.025mg 100T 24001-240ea 270107 240 2,180 523,200", "_confidence": null, "_source": "invoice_statement_table_parser", "manufacturingExpiryComposite": "24001-240ea / 270107", "serialLotComposite": "24001"}, {"rowIndex": 28, "itemCode": "", "itemName": "부광실데나필정50mg", "spec": "4T", "lotNo": "23001", "serialNo": "", "manufacturingNo": "23001-30ea", "expiryDate": "260212", "quantity": "30", "unit": "", "unitPrice": "3,270", "supplyAmount": "", "taxAmount": "", "amount": "98,100", "totalAmount": "", "manufacturer": "", "insuranceCode": "", "remark": "", "_rawText": "부광실데나필정50mg 4T 23001-30ea 260212 30 3,270 98,100", "_confidence": null, "_source": "invoice_statement_table_parser", "manufacturingExpiryComposite": "23001-30ea / 260212", "serialLotComposite": "23001"}]
- 판정: exact

### 2.pdf
- template: TPL-A4585BC7 (documentType=invoice_statement; table region exists; filename matched; latest updatedAt=2026-05-15 13:32:59; last matching record tie-break)
- bounds: {"x": 111, "y": 136, "width": 1486, "height": 1080, "yMax": 1216}
- rowCount: 13/13
- extractionSource: template_colguides_expected_columns
- columnGuides: received=true, used=true, count=9
- warning: []
- summary row 포함 여부: false
- first rows: [{"rowIndex": 1, "itemCode": "OP-AF0100", "itemName": "", "spec": "", "lotNo": "53210", "serialNo": "", "manufacturingNo": "", "expiryDate": "", "quantity": "", "unit": "", "unitPrice": "", "supplyAmount": "14,080", "taxAmount": "", "amount": "", "totalAmount": "", "manufacturer": "", "insuranceCode": "14,080 140,800", "remark": "", "_rawText": "1 OP-AF0100 오스템아세클로페낙정100T 53210 33220 14,080 14,080 140,800", "_confidence": null, "_source": "invoice_statement_table_parser", "consumerUnitPrice": "오스템아세클로페낙정100T", "supplyUnitPrice": "53210 33220", "serialLotComposite": "53210"}, {"rowIndex": 2, "itemCode": "OP-AL0500", "itemName": "", "spec": "", "lotNo": "0500", "serialNo": "", "manufacturingNo": "", "expiryDate": "", "quantity": "", "unit": "", "unitPrice": "", "supplyAmount": "24,200", "taxAmount": "", "amount": "", "totalAmount": "", "manufacturer": "", "insuranceCode": "24,200 2,420,000", "remark": "", "_rawText": "2 OP-AL0500 ALMAFEN TABLET 500T 3 24,200 24,200 2,420,000", "_confidence": null, "_source": "invoice_statement_table_parser", "consumerUnitPrice": "ALMAFEN TABLET 500T", "supplyUnitPrice": "3", "serialLotComposite": "0500"}, {"rowIndex": 3, "itemCode": "OP-AM0030", "itemName": "", "spec": "", "lotNo": "21240", "serialNo": "", "manufacturingNo": "", "expiryDate": "", "quantity": "", "unit": "", "unitPrice": "", "supplyAmount": "2,139", "taxAmount": "", "amount": "", "totalAmount": "", "manufacturer": "", "insuranceCode": "2,139 213.900", "remark": "", "_rawText": "3 OP-AM0030 AMOXIS CAPSULE 30C 25과 21240 100 2,139 2,139 213.900", "_confidence": null, "_source": "invoice_statement_table_parser", "consumerUnitPrice": "AMOXIS CAPSULE 30C", "supplyUnitPrice": "25과 21240 100", "serialLotComposite": "21240"}]
- last rows: [{"rowIndex": 11, "itemCode": "OP-M00100", "itemName": "", "spec": "", "lotNo": "2400", "serialNo": "", "manufacturingNo": "", "expiryDate": "", "quantity": "", "unit": "", "unitPrice": "", "supplyAmount": "9,064", "taxAmount": "", "amount": "", "totalAmount": "", "manufacturer": "", "insuranceCode": "9,064 2,719,200", "remark": "", "_rawText": "11 OP-M00100 모사프리정 100T 27,3.3/ 2400E 300 9,064 9,064 2,719,200", "_confidence": null, "_source": "invoice_statement_table_parser", "consumerUnitPrice": "모사프리정 100T", "supplyUnitPrice": "27,3.3/ 2400E 300", "serialLotComposite": "2400"}, {"rowIndex": 12, "itemCode": "OP-NA0030", "itemName": "", "spec": "", "lotNo": "54033", "serialNo": "", "manufacturingNo": "", "expiryDate": "", "quantity": "", "unit": "", "unitPrice": "", "supplyAmount": "3,036", "taxAmount": "", "amount": "", "totalAmount": "", "manufacturer": "", "insuranceCode": "3,036 303,600", "remark": "", "_rawText": "12 OP-NA0030 오스템 나프록소 30정 27.3 54033 100 3,036 3,036 303,600", "_confidence": null, "_source": "invoice_statement_table_parser", "consumerUnitPrice": "나프록소 30정", "supplyUnitPrice": "27.3 54033 100", "serialLotComposite": "54033"}, {"rowIndex": 13, "itemCode": "OP-NA0300", "itemName": "", "spec": "", "lotNo": "0300", "serialNo": "", "manufacturingNo": "", "expiryDate": "", "quantity": "NAPROXO", "unit": "", "unitPrice": "", "supplyAmount": "30,360", "taxAmount": "", "amount": "", "totalAmount": "", "manufacturer": "", "insuranceCode": "30,360 i,518,000", "remark": "", "_rawText": "13 OP-NA0300 NAPROXO [ABLET 300T 24004 50 30,360 30,360 i,518,000", "_confidence": null, "_source": "invoice_statement_table_parser", "consumerUnitPrice": "ABLET 300T", "supplyUnitPrice": "24004 50", "serialLotComposite": "0300"}]
- 판정: exact

### 3.pdf
- template: TPL-E4B15A22 (documentType=invoice_statement; table region exists; filename matched; latest updatedAt=2026-05-15 15:53:18; last matching record tie-break)
- bounds: {"x": 54, "y": 358, "width": 1553, "height": 85, "yMax": 443}
- rowCount: 1/1
- extractionSource: template_colguides_expected_columns
- columnGuides: received=true, used=true, count=8
- warning: ["insuranceCode:ocr_source_missing:보험No OCR 원문에서 보험코드 후보를 찾지 못함 - 빈 값 유지"]
- first rows: [{"rowIndex": 1, "itemCode": "", "itemName": "669700020에스피씨세파클러캡슬250mg 30 캡슐", "spec": "", "lotNo": "", "serialNo": "", "manufacturingNo": "", "expiryDate": "20261204", "quantity": "30", "unit": "", "unitPrice": "10,044", "supplyAmount": "", "taxAmount": "", "amount": "", "totalAmount": "", "manufacturer": "301.320(주)에스피", "insuranceCode": "", "remark": "", "_rawText": "669700020에스피씨세파클러캡슬250mg 30 캡슐 30 10,044 301.320(주)에스피 20261204", "_confidence": null, "_source": "invoice_statement_table_parser", "manufacturingExpiryComposite": "20261204"}]
- last rows: [{"rowIndex": 1, "itemCode": "", "itemName": "669700020에스피씨세파클러캡슬250mg 30 캡슐", "spec": "", "lotNo": "", "serialNo": "", "manufacturingNo": "", "expiryDate": "20261204", "quantity": "30", "unit": "", "unitPrice": "10,044", "supplyAmount": "", "taxAmount": "", "amount": "", "totalAmount": "", "manufacturer": "301.320(주)에스피", "insuranceCode": "", "remark": "", "_rawText": "669700020에스피씨세파클러캡슬250mg 30 캡슐 30 10,044 301.320(주)에스피 20261204", "_confidence": null, "_source": "invoice_statement_table_parser", "manufacturingExpiryComposite": "20261204"}]
- 판정: exact

### 4.pdf
- template: TPL-FD07531C (documentType=invoice_statement; table region exists; filename matched; latest updatedAt=2026-05-15 15:55:34; last matching record tie-break)
- bounds: {"x": 276, "y": 806, "width": 1090, "height": 42, "yMax": 848}
- rowCount: 1/1
- extractionSource: template_colguides_expected_columns
- columnGuides: received=true, used=true, count=6
- warning: ["totalAmount=doc_level_pushdown"]
- first rows: [{"rowIndex": 1, "itemCode": "", "itemName": "클리마로플란정", "spec": "", "lotNo": "0360823-231024-200811", "serialNo": "0360823-231024-200811", "manufacturingNo": "", "expiryDate": "231024", "quantity": "1,000", "unit": "BOX", "unitPrice": "28,336.00", "supplyAmount": "25,760,000", "taxAmount": "2,578,000", "amount": "", "totalAmount": "28,338,000", "manufacturer": "", "insuranceCode": "", "remark": "", "_rawText": "클리마로플란정 0360823-231024-200811 BOX 1,000 28,336.00 25,760,000 2,578,000", "_confidence": null, "_source": "invoice_statement_table_parser", "manufacturingExpiryComposite": "231024", "serialLotComposite": "0360823-231024-200811 / 0360823-231024-200811"}]
- last rows: [{"rowIndex": 1, "itemCode": "", "itemName": "클리마로플란정", "spec": "", "lotNo": "0360823-231024-200811", "serialNo": "0360823-231024-200811", "manufacturingNo": "", "expiryDate": "231024", "quantity": "1,000", "unit": "BOX", "unitPrice": "28,336.00", "supplyAmount": "25,760,000", "taxAmount": "2,578,000", "amount": "", "totalAmount": "28,338,000", "manufacturer": "", "insuranceCode": "", "remark": "", "_rawText": "클리마로플란정 0360823-231024-200811 BOX 1,000 28,336.00 25,760,000 2,578,000", "_confidence": null, "_source": "invoice_statement_table_parser", "manufacturingExpiryComposite": "231024", "serialLotComposite": "0360823-231024-200811 / 0360823-231024-200811"}]
- 판정: exact

### 5.pdf
- template: TPL-A6B12CED (documentType=invoice_statement; table region exists; filename matched; latest updatedAt=2026-05-15 10:45:03; last matching record tie-break)
- bounds: {"x": 68, "y": 39, "width": 1504, "height": 843, "yMax": 882}
- rowCount: 6/6
- extractionSource: template_colguides_expected_columns
- columnGuides: received=true, used=true, count=9
- warning: []
- first rows: [{"rowIndex": 1, "itemCode": "두피나액30ML", "itemName": "", "spec": "", "lotNo": "", "serialNo": "", "manufacturingNo": "", "expiryDate": "", "quantity": "", "unit": "", "unitPrice": "", "supplyAmount": "", "taxAmount": "", "amount": "DPNL30M 10Q 2,730 273,000", "totalAmount": "", "manufacturer": "", "insuranceCode": "", "remark": "", "_rawText": "두피나액30ML DPNL30M 10Q 2,730 273,000", "_confidence": null, "_source": "invoice_statement_table_parser"}, {"rowIndex": 2, "itemCode": "노루모에이스산250G캔", "itemName": "", "spec": "", "lotNo": "", "serialNo": "", "manufacturingNo": "", "expiryDate": "", "quantity": "", "unit": "", "unitPrice": "10 <", "supplyAmount": "", "taxAmount": "", "amount": "INAP250G 100 4,000 400,000", "totalAmount": "", "manufacturer": "", "insuranceCode": "", "remark": "", "_rawText": "노루모에이스산250G캔 10 < INAP250G 100 4,000 400,000", "_confidence": null, "_source": "invoice_statement_table_parser"}, {"rowIndex": 3, "itemCode": "노루모에스산15P", "itemName": "", "spec": "", "lotNo": "", "serialNo": "", "manufacturingNo": "", "expiryDate": "", "quantity": "", "unit": "", "unitPrice": "", "supplyAmount": "", "taxAmount": "", "amount": "NASP15P 200 2,300 460,000", "totalAmount": "", "manufacturer": "", "insuranceCode": "", "remark": "", "_rawText": "노루모에스산15P NASP15P 200 2,300 460,000", "_confidence": null, "_source": "invoice_statement_table_parser"}]
- last rows: [{"rowIndex": 4, "itemCode": "나프록센나트륨정10T", "itemName": "", "spec": "", "lotNo": "", "serialNo": "", "manufacturingNo": "", "expiryDate": "", "quantity": "", "unit": "", "unitPrice": "100", "supplyAmount": "", "taxAmount": "", "amount": "NPRT10T 300 545 163,635", "totalAmount": "", "manufacturer": "", "insuranceCode": "", "remark": "", "_rawText": "나프록센나트륨정10T 100 NPRT10T 300 545 163,635", "_confidence": null, "_source": "invoice_statement_table_parser"}, {"rowIndex": 5, "itemCode": "노루모듀얼액션현탁액4P", "itemName": "", "spec": "", "lotNo": "", "serialNo": "", "manufacturingNo": "", "expiryDate": "", "quantity": "", "unit": "", "unitPrice": "", "supplyAmount": "", "taxAmount": "", "amount": "NRDA4P 2,000 100,000", "totalAmount": "", "manufacturer": "", "insuranceCode": "", "remark": "", "_rawText": "노루모듀얼액션현탁액4P NRDA4P 2,000 100,000", "_confidence": null, "_source": "invoice_statement_table_parser"}, {"rowIndex": 6, "itemCode": "노루모에프내복액75ML", "itemName": "", "spec": "", "lotNo": "", "serialNo": "", "manufacturingNo": "", "expiryDate": "", "quantity": "", "unit": "", "unitPrice": "", "supplyAmount": "", "taxAmount": "", "amount": "NRFS75M 3,000 550 1,650,000", "totalAmount": "", "manufacturer": "", "insuranceCode": "", "remark": "", "_rawText": "노루모에프내복액75ML NRFS75M 3,000 550 1,650,000", "_confidence": null, "_source": "invoice_statement_table_parser"}]
- 판정: exact

### 6.pdf
- template: TPL-95328E52 (documentType=invoice_statement; table region exists; filename matched; latest updatedAt=2026-05-15 16:19:02; last matching record tie-break)
- bounds: {"x": 66, "y": 621, "width": 1515, "height": 277, "yMax": 898}
- rowCount: 7/6
- extractionSource: template_colguides_expected_columns
- columnGuides: received=true, used=true, count=5
- warning: []
- ANDC300C row 유지 여부: true
- first rows: [{"rowIndex": 1, "itemCode": "제품코드", "itemName": "", "spec": "", "lotNo": "24001", "serialNo": "", "manufacturingNo": "", "expiryDate": "270305", "quantity": "5", "unit": "", "unitPrice": "", "supplyAmount": "", "taxAmount": "", "amount": "", "totalAmount": "", "manufacturer": "", "insuranceCode": "", "remark": "", "_rawText": "NO 제품코드 5 24001 270305", "_confidence": null, "_source": "invoice_statement_table_parser", "manufacturingExpiryComposite": "270305", "serialLotComposite": "24001"}, {"rowIndex": 2, "itemCode": "ATT100T", "itemName": "알코텔정100T", "spec": "", "lotNo": "23001", "serialNo": "", "manufacturingNo": "", "expiryDate": "260403", "quantity": "10", "unit": "", "unitPrice": "", "supplyAmount": "", "taxAmount": "", "amount": "", "totalAmount": "", "manufacturer": "", "insuranceCode": "", "remark": "", "_rawText": "1 ATT100T 알코텔정100T 10 23001 260403", "_confidence": null, "_source": "invoice_statement_table_parser", "manufacturingExpiryComposite": "260403", "serialLotComposite": "23001"}, {"rowIndex": 3, "itemCode": "ATGT30T", "itemName": "액티글리정30T", "spec": "", "lotNo": "23001", "serialNo": "", "manufacturingNo": "", "expiryDate": "260809", "quantity": "10", "unit": "", "unitPrice": "", "supplyAmount": "", "taxAmount": "", "amount": "", "totalAmount": "", "manufacturer": "", "insuranceCode": "", "remark": "", "_rawText": "2 ATGT30T 액티글리정30T 10 23001 260809", "_confidence": null, "_source": "invoice_statement_table_parser", "manufacturingExpiryComposite": "260809", "serialLotComposite": "23001"}]
- last rows: [{"rowIndex": 5, "itemCode": "ASZT28T", "itemName": "에소시움정20MG28T", "spec": "", "lotNo": "", "serialNo": "", "manufacturingNo": "", "expiryDate": "", "quantity": "O", "unit": "", "unitPrice": "", "supplyAmount": "", "taxAmount": "", "amount": "", "totalAmount": "", "manufacturer": "", "insuranceCode": "", "remark": "", "_rawText": "4 ASZT28T 에소시움정20MG28T O", "_confidence": null, "_source": "invoice_statement_table_parser"}, {"rowIndex": 6, "itemCode": "ALG30P", "itemName": "알드린현탁액1.5G30P", "spec": "", "lotNo": "", "serialNo": "", "manufacturingNo": "", "expiryDate": "", "quantity": "0", "unit": "", "unitPrice": "", "supplyAmount": "", "taxAmount": "", "amount": "", "totalAmount": "", "manufacturer": "", "insuranceCode": "", "remark": "", "_rawText": "5 ALG30P 알드린현탁액1.5G30P 0", "_confidence": null, "_source": "invoice_statement_table_parser"}, {"rowIndex": 7, "itemCode": "ANDC300C", "itemName": "앤디락생캡슬300C", "spec": "", "lotNo": "", "serialNo": "", "manufacturingNo": "", "expiryDate": "", "quantity": "", "unit": "", "unitPrice": "", "supplyAmount": "", "taxAmount": "", "amount": "", "totalAmount": "", "manufacturer": "", "insuranceCode": "", "remark": "", "_rawText": "6 ANDC300C 앤디락생캡슬300C", "_confidence": null, "_source": "invoice_statement_table_parser"}]
- 판정: over

### 7.pdf
- template: TPL-3AFD383E (documentType=invoice_statement; table region exists; filename matched; latest updatedAt=2026-05-15 14:31:45; last matching record tie-break)
- bounds: {"x": 70, "y": 961, "width": 1513, "height": 72, "yMax": 1033}
- rowCount: 1/1
- extractionSource: template_colguides_expected_columns
- columnGuides: received=true, used=true, count=3
- warning: []
- serialLotComposite/unit/quantity 유지 여부: {"has_1000": true, "has_unit": true}
- first rows: [{"rowIndex": 1, "itemCode": "", "itemName": "클리마토플란정", "spec": "", "lotNo": "", "serialNo": "0350623-231024-260811", "manufacturingNo": "", "expiryDate": "231024", "quantity": "1,000", "unit": "BOX", "unitPrice": "", "supplyAmount": "", "taxAmount": "", "amount": "", "totalAmount": "", "manufacturer": "", "insuranceCode": "", "remark": "", "_rawText": "클리마토플란정 0350623-231024-260811 BOX 1,000", "_confidence": null, "_source": "invoice_statement_table_parser", "serialLotComposite": "0350623-231024-260811", "manufacturingExpiryComposite": "231024"}]
- last rows: [{"rowIndex": 1, "itemCode": "", "itemName": "클리마토플란정", "spec": "", "lotNo": "", "serialNo": "0350623-231024-260811", "manufacturingNo": "", "expiryDate": "231024", "quantity": "1,000", "unit": "BOX", "unitPrice": "", "supplyAmount": "", "taxAmount": "", "amount": "", "totalAmount": "", "manufacturer": "", "insuranceCode": "", "remark": "", "_rawText": "클리마토플란정 0350623-231024-260811 BOX 1,000", "_confidence": null, "_source": "invoice_statement_table_parser", "serialLotComposite": "0350623-231024-260811", "manufacturingExpiryComposite": "231024"}]
- 판정: exact

## 7. 발견 문제
| 샘플 | 문제 | 원인 추정 | 후속 |
|---|---|---|---|
| 6.pdf | rowCount over | 7/6 | tableBounds 하단 조정 필요 |

## 8. annotation 없는 샘플
| 샘플 | 사유 | 필요한 작업 |
|---|---|---|
| - | 없음 | - |

## 9. 회귀 확인
| 샘플 | 기존 E2E | 최종 E2E | 회귀 여부 |
|---|---:|---:|---|
| 1.jpg | 28 | 28 | 없음 |
| 2.pdf | 13 | 13 | 없음 |
| 5.pdf | 6 | 6 | 없음 |

## 10. 검증 결과
- script py_compile: PASS
- E2E script: completed
- npm typecheck: PASS
- npm build: PASS
- 기존 ESLint nextVitals 메시지 여부: present: ESLint: nextVitals is not iterable

## 11. 다음 작업 판단
- 일부 over → 해당 샘플 tableBounds 하단 조정 필요

## value-level 후속 메모
- 4.pdf taxAmount 기대값 2,576,000 vs E2E 응답 2,578,000 차이 기록
- 이번 단계에서는 rowCount E2E 마감 우선
- 필요 시 별도 value-level 검토 작업으로 분리
