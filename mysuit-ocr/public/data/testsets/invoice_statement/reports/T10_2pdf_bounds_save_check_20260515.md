# T-10 2.pdf bounds 저장 반영 확인 및 E2E 결과

## 1. 생성 파일
- Script: `D:\Free_Vue\OCR\ocr-server\scripts\verify_invoice_statement_template_runocr_e2e_t10_2pdf_bounds_save_check.py`
- Markdown report: `D:\Free_Vue\OCR\mysuit-ocr\public\data\testsets\invoice_statement\reports\T10_2pdf_bounds_save_check_20260515.md`
- JSON report: `D:\Free_Vue\OCR\mysuit-ocr\public\data\testsets\invoice_statement\reports\T10_2pdf_bounds_save_check_20260515.json`

## 2. bounds 변경 확인
| 항목 | 이전 | 현재 | 변경 여부 |
|---|---:|---:|---|
| x | 111 | 111 | false |
| y | 136 | 136 | false |
| width | 1486 | 1486 | false |
| height | 2112 | 1080 | true |
| yMax | 2248 | 1216 | true |

## 3. E2E 실행 여부
- boundsChanged: true
- E2E 실행 여부: true
- 실행하지 않았다면 사유: -

## 4. 2.pdf E2E 결과
| 항목 | 결과 |
|---|---|
| doc_type | invoice_statement |
| extractionSource | template_colguides_expected_columns |
| tableBoundsUsed | true |
| columnGuidesReceived | true |
| columnGuidesUsed | true |
| rowCount | 13 |
| expected rowCount | 13 |
| 상태 | exact |

## 5. row preview
- 마지막 row preview: [{"rowIndex": 11, "itemCode": "OP-M00100", "itemName": "", "spec": "", "lotNo": "2400", "serialNo": "", "manufacturingNo": "", "expiryDate": "", "quantity": "", "unit": "", "unitPrice": "", "supplyAmount": "9,064", "taxAmount": "", "amount": "", "totalAmount": "", "manufacturer": "", "insuranceCode": "9,064 2,719,200", "remark": "", "_rawText": "11 OP-M00100 모사프리정 100T 27,3.3/ 2400E 300 9,064 9,064 2,719,200", "_confidence": null, "_source": "invoice_statement_table_parser", "consumerUnitPrice": "모사프리정 100T", "supplyUnitPrice": "27,3.3/ 2400E 300", "serialLotComposite": "2400"}, {"rowIndex": 12, "itemCode": "OP-NA0030", "itemName": "", "spec": "", "lotNo": "54033", "serialNo": "", "manufacturingNo": "", "expiryDate": "", "quantity": "", "unit": "", "unitPrice": "", "supplyAmount": "3,036", "taxAmount": "", "amount": "", "totalAmount": "", "manufacturer": "", "insuranceCode": "3,036 303,600", "remark": "", "_rawText": "12 OP-NA0030 오스템 나프록소 30정 27.3 54033 100 3,036 3,036 303,600", "_confidence": null, "_source": "invoice_statement_table_parser", "consumerUnitPrice": "나프록소 30정", "supplyUnitPrice": "27.3 54033 100", "serialLotComposite": "54033"}, {"rowIndex": 13, "itemCode": "OP-NA0300", "itemName": "", "spec": "", "lotNo": "0300", "serialNo": "", "manufacturingNo": "", "expiryDate": "", "quantity": "NAPROXO", "unit": "", "unitPrice": "", "supplyAmount": "30,360", "taxAmount": "", "amount": "", "totalAmount": "", "manufacturer": "", "insuranceCode": "30,360 i,518,000", "remark": "", "_rawText": "13 OP-NA0300 NAPROXO [ABLET 300T 24004 50 30,360 30,360 i,518,000", "_confidence": null, "_source": "invoice_statement_table_parser", "consumerUnitPrice": "ABLET 300T", "supplyUnitPrice": "24004 50", "serialLotComposite": "0300"}]
- summary/잔액 row 포함 여부: false []

## 6. 회귀 확인
| 샘플 | 기대 | 결과 | 상태 |
|---|---:|---:|---|
| 1.jpg | 28 | 28 | exact |
| 5.pdf | 6 | 6 | exact |
| 2.pdf | 13 | 13 | exact |

## 7. 다음 작업 판단
- rowCount 13/13 → 7.pdf/6.pdf annotation 저장으로 이동

## 8. 검증 결과
- script py_compile: not_run_in_script
- E2E script: completed
- typecheck: not_run_in_script
- build: not_run_in_script
