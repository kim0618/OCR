# T-6l GT tableRows 기준 rowCount / row alignment 리포트

## 1. 데이터 소스
- API: http://127.0.0.1:8204
- GT: `D:\Free_Vue\OCR\mysuit-ocr\public\data\testsets\invoice_statement\ground_truth.json`
- GT tableRows 배열: 7개 샘플 모두 저장되어 있지 않음
- 따라서 GT rowCount와 수동/문서 기반 anchor가 있는 샘플만 row alignment를 보조 분석함

## 2. GT tableRows 구조 확인
| 샘플 | GT entry | GT tableRows | GT rowCount | firstRowPreview | manual anchors |
|---|---|---|---:|---|---:|
| 1.jpg | True | False | 28 | 헥사메던액0.12% 15m\|*6포 | 0 |
| 2.pdf | True | False | 13 | LOXOLIFEN TABLET 3OT3Z | 0 |
| 3.pdf | True | False | 1 | 에스피씨세파클러캡슬250mg30 캡슐 | 0 |
| 4.pdf | True | False | 1 | 클리마토플란정 | 0 |
| 5.pdf | True | False | 6 | 노루모에프내복액75ML | 6 |
| 6.pdf | True | False | 6 | 알코텔정100T | 6 |
| 7.pdf | True | False | 1 | 클리마토플란정 | 1 |

## 3. 샘플별 rowCount before/after
- OCR before는 T-6l 시작 시점의 API baseline 실행값이다.
| 샘플 | GT rowCount | OCR before | OCR after | 상태 | 비고 |
|---|---:|---:|---:|---|---|
| 1.jpg | 28 | 29 | 28 | exact | expected_columns_header_match |
| 2.pdf | 13 | 2 | 2 | short | legacy_text_items |
| 3.pdf | 1 | 1 | 1 | exact | header_column_mapping |
| 4.pdf | 1 | 3 | 1 | exact | expected_columns_header_match |
| 5.pdf | 6 | 6 | 6 | exact | legacy_text_items |
| 6.pdf | 6 | 5 | 6 | exact | expected_columns_header_match |
| 7.pdf | 1 | 1 | 1 | exact | expected_columns_header_match |

## 4. 샘플별 row alignment
| 샘플 | matched | missing GT rows | extra OCR rows | low confidence | 판정 |
|---|---:|---:|---:|---:|---|
| 1.jpg | 0 | 0 | 28 | 0 | GT tableRows 없음 |
| 2.pdf | 0 | 0 | 2 | 0 | GT tableRows 없음 |
| 3.pdf | 0 | 0 | 1 | 0 | GT tableRows 없음 |
| 4.pdf | 0 | 0 | 1 | 0 | GT tableRows 없음 |
| 5.pdf | 0 | 1 | 1 | 5 | needs_review |
| 6.pdf | 6 | 0 | 0 | 0 | exact |
| 7.pdf | 1 | 0 | 0 | 0 | exact |

## 5. 샘플별 원인
| 샘플 | 문제 | 원인 | 수정 여부 | 후속 |
|---|---|---|---|---|
| 1.jpg | rowCount exact | source=expected_columns_header_match; rejected={'summary_row': 1}; rowEnd=summary_row at y=1220.9 after 28 rows | 분석 | GT tableRows 추가 필요 |
| 2.pdf | short | source=legacy_text_items; rejected={'header_or_contact': 3, 'summary_row': 1}; rowEnd=None | 분석 | GT tableRows 추가 필요 |
| 3.pdf | rowCount exact | source=header_column_mapping; rejected={'header_or_contact': 2}; rowEnd=None | 분석 | GT tableRows 추가 필요 |
| 4.pdf | rowCount exact | source=expected_columns_header_match; rejected={'item_name_only_split': 1, 'no_item_name': 1, 'summary_row': 2, 'notice_or_part... | 분석 | GT tableRows 추가 필요 |
| 5.pdf | rowCount exact | source=legacy_text_items; rejected={}; rowEnd=None | 분석 | GT tableRows 추가 필요 |
| 6.pdf | rowCount exact | source=expected_columns_header_match; rejected={}; rowEnd=None | 분석 | GT tableRows 추가 필요 |
| 7.pdf | rowCount exact | source=expected_columns_header_match; rejected={'no_item_name': 2, 'item_name_only_split': 1}; rowEnd=None | 분석 | GT tableRows 추가 필요 |

## 6. 상세 anchor preview
### 1.jpg
- expected columns: ["itemName", "spec", "manufacturingNo", "expiryDate", "quantity", "unitPrice", "amount"]
- extractionSource: expected_columns_header_match
- rejectedRows: {"summary_row": 1}
- OCR anchors: ["rowIndex=1; itemName=헥사메던액0.12%; lotNo=24027; serialLotComposite=24027; manufacturingNo=24027; expiryDate=20270205; quantity=400; amount=420,000", "rowIndex=2; itemName=더모픽스크림; lotNo=24001; serialLotComposite=24001; manufacturingNo=24001; expiryDate=20270...
- extraOcrRows: [{"ocrIndex": 1, "ocr": {"rowIndex": "1", "itemCode": "", "itemName": "헥사메던액0.12%", "lotNo": "24027", "serialLotComposite": "24027", "manufacturingNo": "24027", "manufacturingExpiryComposite": "24027 / 20270205", "expiryDate": "20270205", "quantity": "400",...

### 2.pdf
- expected columns: ["rowIndex", "itemCode", "itemName", "quantity", "consumerUnitPrice", "supplyUnitPrice", "supplyAmount", "insuranceCode"]
- extractionSource: legacy_text_items
- rejectedRows: {"header_or_contact": 3, "summary_row": 1}
- OCR anchors: ["rowIndex=1; itemName=LOXOLIFEN", "rowIndex=2; itemName=AMOXIS; amount=233,883,223; supplyAmount=233,883,223"]
- extraOcrRows: [{"ocrIndex": 1, "ocr": {"rowIndex": "1", "itemCode": "", "itemName": "LOXOLIFEN", "lotNo": "", "serialLotComposite": "", "manufacturingNo": "", "manufacturingExpiryComposite": "", "expiryDate": "", "quantity": "", "amount": "", "supplyAmount": "", "insuran...

### 3.pdf
- expected columns: ["rowIndex", "insuranceCode", "itemName", "spec", "quantity", "unitPrice", "amount", "manufacturer", "manufacturingExpiryCompos...
- extractionSource: header_column_mapping
- rejectedRows: {"header_or_contact": 2}
- OCR anchors: ["rowIndex=1; quantity=제조회사 o묘 0 공급받눈재인료관용"]
- extraOcrRows: [{"ocrIndex": 1, "ocr": {"rowIndex": "1", "itemCode": "", "itemName": "", "lotNo": "", "serialLotComposite": "", "manufacturingNo": "", "manufacturingExpiryComposite": "", "expiryDate": "", "quantity": "제조회사 o묘 0 공급받눈재인료관용", "amount": "", "supplyAmount": ""...

### 4.pdf
- expected columns: ["itemName", "lotNo", "unit", "quantity", "unitPrice", "supplyAmount", "taxAmount"]
- extractionSource: expected_columns_header_match
- rejectedRows: {"item_name_only_split": 1, "no_item_name": 1, "summary_row": 2, "notice_or_party": 2}
- OCR anchors: ["rowIndex=1; itemName=중욕명; serialLotComposite=0350823-231024-200811; expiryDate=231024; quantity=BOX 1,000; supplyAmount=25,760,000"]
- extraOcrRows: [{"ocrIndex": 1, "ocr": {"rowIndex": "1", "itemCode": "", "itemName": "중욕명", "lotNo": "", "serialLotComposite": "0350823-231024-200811", "manufacturingNo": "", "manufacturingExpiryComposite": "231024", "expiryDate": "231024", "quantity": "BOX 1,000", "amoun...

### 5.pdf
- expected columns: ["itemName", "itemCode", "quantity", "unitPrice", "amount"]
- extractionSource: legacy_text_items
- rejectedRows: {}
- OCR anchors: ["rowIndex=1; itemName=노루모에프내복액75ML", "rowIndex=2; itemName=나프록센나트롭정10T100; quantity=213", "rowIndex=3; itemName=노루모에스산15P; quantity=63", "rowIndex=4; itemName=노루모듀얼액션현탁액4P", "rowIndex=5; itemName=두피나액30ML", "rowIndex=6; itemName=노루모에이스산250G캔"]
- missingGtRows: [{"gtIndex": 3, "ocrIndex": null, "score": 1.85, "status": "missing_gt_row", "reasons": ["itemName:fuzzy"], "gt": {"itemName": "나프록센나트륨정10T100", "itemCode": "NPRT10T"}, "ocr": null}]
- extraOcrRows: [{"ocrIndex": 2, "ocr": {"rowIndex": "2", "itemCode": "", "itemName": "나프록센나트롭정10T100", "lotNo": "", "serialLotComposite": "", "manufacturingNo": "", "manufacturingExpiryComposite": "", "expiryDate": "", "quantity": "213", "amount": "", "supplyAmount": "", ...

### 6.pdf
- expected columns: ["rowIndex", "itemCode", "itemName", "quantity", "lotNo", "expiryDate"]
- extractionSource: expected_columns_header_match
- rejectedRows: {}
- OCR anchors: ["rowIndex=1; itemCode=ATT100T; itemName=알코텔정100T; lotNo=24001; serialLotComposite=24001; expiryDate=270305; quantity=5", "rowIndex=2; itemCode=ATGT3OT; itemName=액티글리정30T; lotNo=23001; serialLotComposite=23001; expiryDate=260403; quantity=10", "rowIndex=3; ...

### 7.pdf
- expected columns: ["itemName", "serialLotComposite", "unit", "quantity"]
- extractionSource: expected_columns_header_match
- rejectedRows: {"no_item_name": 2, "item_name_only_split": 1}
- OCR anchors: ["rowIndex=1; itemName=클리마토플란정; serialLotComposite=0350623-231024-260811; expiryDate=231024"]

## 7. 결론
- rowCount 불안정 샘플: 2.pdf
- 다음 단계는 T-6l-fix이며, T-6m/T-7로 이동하기 전 GT tableRows 확보 또는 row 후보 보정이 필요함
