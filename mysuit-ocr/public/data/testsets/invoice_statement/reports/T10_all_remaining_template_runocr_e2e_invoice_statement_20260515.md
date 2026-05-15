# T-10 all remaining Template/RunOCR E2E 결과

## 1. 생성 파일
- Script: `D:\Free_Vue\OCR\ocr-server\scripts\verify_invoice_statement_template_runocr_e2e_t10_all_remaining.py`
- Markdown report: `D:\Free_Vue\OCR\mysuit-ocr\public\data\testsets\invoice_statement\reports\T10_all_remaining_template_runocr_e2e_invoice_statement_20260515.md`
- JSON report: `D:\Free_Vue\OCR\mysuit-ocr\public\data\testsets\invoice_statement\reports\T10_all_remaining_template_runocr_e2e_invoice_statement_20260515.json`

## 2. 핵심 요약
- API: `http://127.0.0.1:9099`
- 요약: {"executed": 3, "exact": 3, "missing": 4, "total": 7}
- 다음 판단: annotation 없음 → UI 저장 필요

## 3. Template annotation 확인
| 샘플 | template_id | documentType | table region | colGuides | 실행 여부 |
|---|---|---|---|---|---|
| 1.jpg | TPL-31D13CF3 | invoice_statement | {"x": 47, "y": 831, "width": 2361, "height": 2317, "yMax": 3148} | 6 | true |
| 2.pdf | TPL-A4585BC7 | invoice_statement | {"x": 111, "y": 136, "width": 1486, "height": 1080, "yMax": 1216} | 9 | true |
| 3.pdf | - | - | - | - | false |
| 4.pdf | - | - | - | - | false |
| 5.pdf | TPL-A6B12CED | invoice_statement | {"x": 68, "y": 39, "width": 1504, "height": 843, "yMax": 882} | 9 | true |
| 6.pdf | - | - | - | - | false |
| 7.pdf | - | - | - | - | false |

## 4. E2E rowCount 결과
| 샘플 | GT | Test 기준 | RunOCR E2E | 상태 |
|---|---:|---:|---:|---|
| 1.jpg | 28 | 28 | 28 | exact |
| 2.pdf | 13 | 13 | 13 | exact |
| 3.pdf | 1 | 1 | - | skipped_no_saved_template_annotation |
| 4.pdf | 1 | 1 | - | skipped_no_saved_template_annotation |
| 5.pdf | 6 | 6 | 6 | exact |
| 6.pdf | 6 | 6 | - | skipped_no_saved_template_annotation |
| 7.pdf | 1 | 1 | - | skipped_no_saved_template_annotation |

## 5. tableMeta/debug 결과
| 샘플 | doc_type | extractionSource | tableBoundsUsed | columnGuidesUsed | warnings |
|---|---|---|---|---|---|
| 1.jpg | invoice_statement | template_colguides_expected_columns | true | true | [] |
| 2.pdf | invoice_statement | template_colguides_expected_columns | true | true | [] |
| 3.pdf | - | - | - | - | [] |
| 4.pdf | - | - | - | - | [] |
| 5.pdf | invoice_statement | template_colguides_expected_columns | true | true | [] |
| 6.pdf | - | - | - | - | [] |
| 7.pdf | - | - | - | - | [] |

## 6. 샘플별 상세
### 1.jpg
- template: TPL-31D13CF3
- rowCount: 28/28 (exact)
- tableMeta: source=template_colguides_expected_columns, bounds=true, colGuidesReceived=true, colGuidesUsed=true
- row preview: [{"rowIndex": 1, "itemCode": "", "itemName": "헥사메딘액0.12%", "spec": "15m\|*6포", "lotNo": "24027", "serialNo": "", "manufacturingNo": "24027", "expiryDate": "20270205", "quantity": "400", "unit": "", "unitPrice": "1,050", "supplyAmount": "", "taxAmount": "", "amount": "420,000", "totalAmount": "", "manufacturer": "", "insuranceCode": "", "remark": "", "_rawText": "헥사메딘액0.12% 15m\|*6포 24027 20270205 400 1,050 420,000", "_confidence": null, "_source": "invoice_statement_table_parser", "manufacturingExpiryComposite": "24027 / 20270205", "serialLotComposite": "24027"}, {"rowIndex": 2, "itemCode": "", "itemName": "더모픽스크림", "spec": "30g", "lotNo": "24001", "serialNo": "", "manufacturingNo": "24001", "expiryDate": "20270116", "quantity": "100", "unit": "", "unitPrice": "4,490", "supplyAmount": "", "taxAmount": "", "amount": "449,000", "totalAmount": "", "manufacturer": "", "insuranceCode": "", "remark": "", "_rawText": "더모픽스크림 30g 24001 20270116 100 4,490 449,000", "_confidence": null, "_source": "invoice_statement_table_parser", "manufacturingExpiryComposite": "24001 / 20270116", "serialLotComposite": "24001"}, {"rowIndex": 3, "itemCode": "", "itemName": "하드칼추어블이지정", "spec": "30T", "lotNo": "23010", "serialNo": "", "manufacturingNo": "23010", "expiryDate": "20250601", "quantity": "180", "unit": "", "unitPrice": "1,400", "supplyAmount": "", "taxAmount": "", "amount": "252,000", "totalAmount": "", "manufacturer": "", "insuranceCode": "", "remark": "", "_rawText": "하드칼추어블이지정 30T 23010 20250601 180 1,400 252,000", "_confidence": null, "_source": "invoice_statement_table_parser", "manufacturingExpiryComposite": "23010 / 20250601", "serialLotComposite": "23010"}]

### 2.pdf
- template: TPL-A4585BC7
- rowCount: 13/13 (exact)
- tableMeta: source=template_colguides_expected_columns, bounds=true, colGuidesReceived=true, colGuidesUsed=true
- row preview: [{"rowIndex": 1, "itemCode": "OP-AF0100", "itemName": "", "spec": "", "lotNo": "53210", "serialNo": "", "manufacturingNo": "", "expiryDate": "", "quantity": "", "unit": "", "unitPrice": "", "supplyAmount": "14,080", "taxAmount": "", "amount": "", "totalAmount": "", "manufacturer": "", "insuranceCode": "14,080 140,800", "remark": "", "_rawText": "1 OP-AF0100 오스템아세클로페낙정100T 53210 33220 14,080 14,080 140,800", "_confidence": null, "_source": "invoice_statement_table_parser", "consumerUnitPrice": "오스템아세클로페낙정100T", "supplyUnitPrice": "53210 33220", "serialLotComposite": "53210"}, {"rowIndex": 2, "itemCode": "OP-AL0500", "itemName": "", "spec": "", "lotNo": "0500", "serialNo": "", "manufacturingNo": "", "expiryDate": "", "quantity": "", "unit": "", "unitPrice": "", "supplyAmount": "24,200", "taxAmount": "", "amount": "", "totalAmount": "", "manufacturer": "", "insuranceCode": "24,200 2,420,000", "remark": "", "_rawText": "2 OP-AL0500 ALMAFEN TABLET 500T 3 24,200 24,200 2,420,000", "_confidence": null, "_source": "invoice_statement_table_parser", "consumerUnitPrice": "ALMAFEN TABLET 500T", "supplyUnitPrice": "3", "serialLotComposite": "0500"}, {"rowIndex": 3, "itemCode": "OP-AM0030", "itemName": "", "spec": "", "lotNo": "21240", "serialNo": "", "manufacturingNo": "", "expiryDate": "", "quantity": "", "unit": "", "unitPrice": "", "supplyAmount": "2,139", "taxAmount": "", "amount": "", "totalAmount": "", "manufacturer": "", "insuranceCode": "2,139 213.900", "remark": "", "_rawText": "3 OP-AM0030 AMOXIS CAPSULE 30C 25과 21240 100 2,139 2,139 213.900", "_confidence": null, "_source": "invoice_statement_table_parser", "consumerUnitPrice": "AMOXIS CAPSULE 30C", "supplyUnitPrice": "25과 21240 100", "serialLotComposite": "21240"}]

### 3.pdf
- template: -
- rowCount: -/1 (skipped_no_saved_template_annotation)
- tableMeta: source=-, bounds=-, colGuidesReceived=-, colGuidesUsed=-
- row preview: -

### 4.pdf
- template: -
- rowCount: -/1 (skipped_no_saved_template_annotation)
- tableMeta: source=-, bounds=-, colGuidesReceived=-, colGuidesUsed=-
- row preview: -

### 5.pdf
- template: TPL-A6B12CED
- rowCount: 6/6 (exact)
- tableMeta: source=template_colguides_expected_columns, bounds=true, colGuidesReceived=true, colGuidesUsed=true
- row preview: [{"rowIndex": 1, "itemCode": "두피나액30ML", "itemName": "", "spec": "", "lotNo": "", "serialNo": "", "manufacturingNo": "", "expiryDate": "", "quantity": "", "unit": "", "unitPrice": "", "supplyAmount": "", "taxAmount": "", "amount": "DPNL30M 10Q 2,730 273,000", "totalAmount": "", "manufacturer": "", "insuranceCode": "", "remark": "", "_rawText": "두피나액30ML DPNL30M 10Q 2,730 273,000", "_confidence": null, "_source": "invoice_statement_table_parser"}, {"rowIndex": 2, "itemCode": "노루모에이스산250G캔", "itemName": "", "spec": "", "lotNo": "", "serialNo": "", "manufacturingNo": "", "expiryDate": "", "quantity": "", "unit": "", "unitPrice": "10 <", "supplyAmount": "", "taxAmount": "", "amount": "INAP250G 100 4,000 400,000", "totalAmount": "", "manufacturer": "", "insuranceCode": "", "remark": "", "_rawText": "노루모에이스산250G캔 10 < INAP250G 100 4,000 400,000", "_confidence": null, "_source": "invoice_statement_table_parser"}, {"rowIndex": 3, "itemCode": "노루모에스산15P", "itemName": "", "spec": "", "lotNo": "", "serialNo": "", "manufacturingNo": "", "expiryDate": "", "quantity": "", "unit": "", "unitPrice": "", "supplyAmount": "", "taxAmount": "", "amount": "NASP15P 200 2,300 460,000", "totalAmount": "", "manufacturer": "", "insuranceCode": "", "remark": "", "_rawText": "노루모에스산15P NASP15P 200 2,300 460,000", "_confidence": null, "_source": "invoice_statement_table_parser"}]

### 6.pdf
- template: -
- rowCount: -/6 (skipped_no_saved_template_annotation)
- tableMeta: source=-, bounds=-, colGuidesReceived=-, colGuidesUsed=-
- row preview: -

### 7.pdf
- template: -
- rowCount: -/1 (skipped_no_saved_template_annotation)
- tableMeta: source=-, bounds=-, colGuidesReceived=-, colGuidesUsed=-
- row preview: -

## 7. 발견 문제
| 샘플 | 문제 | 원인 | 후속 |
|---|---|---|---|
| 3.pdf | annotation 없음 | templates.json에 저장된 table template 없음 | UI에서 invoice_statement table region/colGuides 저장 |
| 4.pdf | annotation 없음 | templates.json에 저장된 table template 없음 | UI에서 invoice_statement table region/colGuides 저장 |
| 6.pdf | annotation 없음 | templates.json에 저장된 table template 없음 | UI에서 invoice_statement table region/colGuides 저장 |
| 7.pdf | annotation 없음 | templates.json에 저장된 table template 없음 | UI에서 invoice_statement table region/colGuides 저장 |

## 8. 검증 결과
- script py_compile: passed
- E2E script: completed
- typecheck: passed after build regenerated `.next/types`
- build: passed; Next build completed, with ESLint message `nextVitals is not iterable`

## 9. 다음 작업 판단
- annotation 없음 → UI 저장 필요
