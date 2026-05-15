# T-10 2.pdf tableBounds 재조정 RunOCR E2E 결과

## 1. 생성 파일
- Script: `D:\Free_Vue\OCR\ocr-server\scripts\verify_invoice_statement_template_runocr_e2e_t10_2pdf_bounds_fix.py`
- Markdown report: `D:\Free_Vue\OCR\mysuit-ocr\public\data\testsets\invoice_statement\reports\T10_2pdf_bounds_fix_runocr_e2e_20260515.md`
- JSON report: `D:\Free_Vue\OCR\mysuit-ocr\public\data\testsets\invoice_statement\reports\T10_2pdf_bounds_fix_runocr_e2e_20260515.json`

## 2. 핵심 요약
- API: `http://127.0.0.1:9099`
- 2.pdf 상태: mismatch
- 회귀 포함 실행: {"apiExecuted": 3, "exact": 2, "total": 3}
- 다음 판단: 2.pdf 여전히 over → tableBounds 하단 y 추가 조정

## 3. 2.pdf annotation 확인
| 항목 | 결과 |
|---|---|
| template_id | TPL-A4585BC7 |
| documentType | invoice_statement |
| table region | {"x": 111, "y": 136, "width": 1486, "height": 2112} |
| colGuides count | 9 |
| tableBounds y 범위 | [136, 2248] |

## 4. 2.pdf E2E 결과
| 항목 | 결과 |
|---|---|
| doc_type | invoice_statement |
| extractionSource | template_colguides_expected_columns |
| tableBoundsUsed | true |
| columnGuidesReceived | true |
| columnGuidesUsed | true |
| rowCount | 18 |
| expected rowCount | 13 |
| 상태 | mismatch |

## 5. row preview 점검
- 첫 3개 row: [{"rowIndex": 1, "itemCode": "OP-AF0100", "itemName": "", "spec": "", "lotNo": "53210", "serialNo": "", "manufacturingNo": "", "expiryDate": "", "quantity": "", "unit": "", "unitPrice": "", "supplyAmount": "14,080", "taxAmount": "", "amount": "", "totalAmount": "", "manufacturer": "", "insuranceCode": "14,080 140,800", "remark": "", "_rawText": "1 OP-AF0100 오스템아세클로페낙정100T 53210 33220 14,080 14,080 140,800", "_confidence": null, "_source": "invoice_statement_table_parser", "consumerUnitPrice": "오스템아세클로페낙정100T", "supplyUnitPrice": "53210 33220", "serialLotComposite": "53210"}, {"rowIndex": 2, "itemCode": "OP-AL0500", "itemName": "", "spec": "", "lotNo": "0500", "serialNo": "", "manufacturingNo": "", "expiryDate": "", "quantity": "", "unit": "", "unitPrice": "", "supplyAmount": "24,200", "taxAmount": "", "amount": "", "totalAmount": "", "manufacturer": "", "insuranceCode": "24,200 2,420,000", "remark": "", "_rawText": "2 OP-AL0500 ALMAFEN TABLET 500T 3 24,200 24,200 2,420,000", "_confidence": null, "_source": "invoice_statement_table_parser", "consumerUnitPrice": "ALMAFEN TABLET 500T", "supplyUnitPrice": "3", "serialLotComposite": "0500"}, {"rowIndex": 3, "itemCode": "OP-AM0030", "itemName": "", "spec": "", "lotNo": "21240", "serialNo": "", "manufacturingNo": "", "expiryDate": "", "quantity": "", "unit": "", "unitPrice": "", "supplyAmount": "2,139", "taxAmount": "", "amount": "", "totalAmount": "", "manufacturer": "", "insuranceCode": "2,139 213.900", "remark": "", "_rawText": "3 OP-AM0030 AMOXIS CAPSULE 30C 25과 21240 100 2,139 2,139 213.900", "_confidence": null, "_source": "invoice_statement_table_parser", "consumerUnitPrice": "AMOXIS CAPSULE 30C", "supplyUnitPrice": "25과 21240 100", "serialLotComposite": "21240"}]
- 마지막 3개 row: [{"rowIndex": 16, "itemCode": "구분", "itemName": "", "spec": "", "lotNo": "", "serialNo": "", "manufacturingNo": "", "expiryDate": "", "quantity": "", "unit": "", "unitPrice": "", "supplyAmount": "당일거래금액", "taxAmount": "", "amount": "", "totalAmount": "", "manufacturer": "", "insuranceCode": "누계잔액", "remark": "", "_rawText": "구분 전일잔액 당일거래금액 누계잔액", "_confidence": null, "_source": "invoice_statement_table_parser", "consumerUnitPrice": "전일잔액", "supplyUnitPrice": ""}, {"rowIndex": 17, "itemCode": "채 권", "itemName": "", "spec": "", "lotNo": "", "serialNo": "", "manufacturingNo": "", "expiryDate": "", "quantity": "", "unit": "", "unitPrice": "", "supplyAmount": "22,312,320", "taxAmount": "", "amount": "", "totalAmount": "", "manufacturer": "", "insuranceCode": "256, 195, 543", "remark": "", "_rawText": "채 권 233,883,223 22,312,320 256, 195, 543", "_confidence": null, "_source": "invoice_statement_table_parser", "consumerUnitPrice": "233,883,223", "supplyUnitPrice": ""}, {"rowIndex": 18, "itemCode": "약정", "itemName": "", "spec": "", "lotNo": "", "serialNo": "", "manufacturingNo": "", "expiryDate": "", "quantity": "", "unit": "", "unitPrice": "", "supplyAmount": "0", "taxAmount": "", "amount": "", "totalAmount": "", "manufacturer": "", "insuranceCode": "0", "remark": "", "_rawText": "약정 0 0 0", "_confidence": null, "_source": "invoice_statement_table_parser", "supplyUnitPrice": "0", "consumerUnitPrice": ""}]
- summary row 포함 여부: true ["합계", "공급금액합계", "소비자금액합계", "전일잔액", "당일거래금액", "누계잔액"]

## 6. 회귀 확인
| 샘플 | 기대 | 결과 | 상태 |
|---|---:|---:|---|
| 1.jpg | 28 | 28 | exact |
| 5.pdf | 6 | 6 | exact |
| 2.pdf | 13 | 18 | mismatch |

## 7. 발견 문제
| 문제 | 원인 | 후속 |
|---|---|---|
| 2.pdf: rowCount mismatch | RunOCR=18, expected=13 | tableBounds 하단 y 추가 조정 |
| 2.pdf: summary row included | 합계, 공급금액합계, 소비자금액합계, 전일잔액, 당일거래금액, 누계잔액 | 하단 summary/잔액 영역 제외 후 재저장 |

## 8. 검증 결과
- script py_compile: passed
- E2E script: completed
- typecheck: passed after build regenerated `.next/types`
- build: passed; Next build completed, with ESLint message `nextVitals is not iterable`

## 9. 다음 작업 판단
- 2.pdf 여전히 over → tableBounds 하단 y 추가 조정
