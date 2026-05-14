# T-6m Expected Column Value Mapping 검증 결과 (before)

## rowCount 비교
| 샘플 | GT | OCR | 상태 | source |
|---|---:|---:|---|---|
| 1.jpg | 28 | 28 | exact | expected_columns_header_match |
| 2.pdf | 13 | 13 | exact | op_anchor_reconstructed_table |
| 3.pdf | 1 | 1 | exact | header_column_mapping |
| 4.pdf | 1 | 1 | exact | expected_columns_header_match |
| 5.pdf | 6 | 6 | exact | legacy_text_items |
| 6.pdf | 6 | 6 | exact | expected_columns_header_match |
| 7.pdf | 1 | 1 | exact | expected_columns_header_match |

## 샘플별 Expected Column Fill Rate

### 1.jpg  (overall 98.5%)
| 컬럼 | key | filled/total | rate |
|---|---|---:|---:|
| OK 품목 | `itemName` | 28/28 | 100.0% |
| OK 규격 | `spec` | 28/28 | 100.0% |
| -- 제조번호 | `manufacturingNo` | 27/28 | 96.4% |
| -- 유효기간 | `expiryDate` | 27/28 | 96.4% |
| -- 수량 | `quantity` | 27/28 | 96.4% |
| OK 단가 | `unitPrice` | 28/28 | 100.0% |
| OK 금액 | `amount` | 28/28 | 100.0% |

### 2.pdf  (overall 60.6%)
| 컬럼 | key | filled/total | rate |
|---|---|---:|---:|
| OK NO | `rowIndex` | 13/13 | 100.0% |
| OK 품목코드 | `itemCode` | 13/13 | 100.0% |
| -- 품목명 | `itemName` | 2/13 | 15.4% |
| -- 수량 | `quantity` | 8/13 | 61.5% |
| -- 소비자단가 | `consumerUnitPrice` | 12/13 | 92.3% |
| -- 공급단가 | `supplyUnitPrice` | 12/13 | 92.3% |
| -- 공급금액 | `supplyAmount` | 3/13 | 23.1% |
| NG 보험No | `insuranceCode` | 0/13 | 0.0% |

### 3.pdf  (overall 22.2%)
| 컬럼 | key | filled/total | rate |
|---|---|---:|---:|
| OK 순번 | `rowIndex` | 1/1 | 100.0% |
| NG 보험코드 | `insuranceCode` | 0/1 | 0.0% |
| NG 품명 | `itemName` | 0/1 | 0.0% |
| NG 규격 | `spec` | 0/1 | 0.0% |
| OK 수량 | `quantity` | 1/1 | 100.0% |
| NG 단가 | `unitPrice` | 0/1 | 0.0% |
| NG 금액 | `amount` | 0/1 | 0.0% |
| NG 제조회사 | `manufacturer` | 0/1 | 0.0% |
| NG 제조번호/유효기간 | `manufacturingExpiryComposite` | 0/1 | 0.0% |

### 4.pdf  (overall 71.4%)
| 컬럼 | key | filled/total | rate |
|---|---|---:|---:|
| OK 품목명 | `itemName` | 1/1 | 100.0% |
| NG LotNo. | `lotNo` | 0/1 | 0.0% |
| OK 단위 | `unit` | 1/1 | 100.0% |
| OK 수량 | `quantity` | 1/1 | 100.0% |
| OK 단가 | `unitPrice` | 1/1 | 100.0% |
| OK 공급가액 | `supplyAmount` | 1/1 | 100.0% |
| NG 세액 | `taxAmount` | 0/1 | 0.0% |

### 5.pdf  (overall 26.7%)
| 컬럼 | key | filled/total | rate |
|---|---|---:|---:|
| OK 품명 | `itemName` | 6/6 | 100.0% |
| NG 품목코드 | `itemCode` | 0/6 | 0.0% |
| -- 수량 | `quantity` | 2/6 | 33.3% |
| NG 단가 | `unitPrice` | 0/6 | 0.0% |
| NG 금액 | `amount` | 0/6 | 0.0% |

### 6.pdf  (overall 88.9%)
| 컬럼 | key | filled/total | rate |
|---|---|---:|---:|
| OK NO | `rowIndex` | 6/6 | 100.0% |
| OK 제품코드 | `itemCode` | 6/6 | 100.0% |
| OK 제품명 | `itemName` | 6/6 | 100.0% |
| OK 수량 | `quantity` | 6/6 | 100.0% |
| -- LotNo | `lotNo` | 4/6 | 66.7% |
| -- 유효일자 | `expiryDate` | 4/6 | 66.7% |

### 7.pdf  (overall 75.0%)
| 컬럼 | key | filled/total | rate |
|---|---|---:|---:|
| OK 품명 | `itemName` | 1/1 | 100.0% |
| OK 시리얼/로트No. | `serialLotComposite` | 1/1 | 100.0% |
| OK 단위 | `unit` | 1/1 | 100.0% |
| NG 수량 | `quantity` | 0/1 | 0.0% |

## 샘플별 Row Fill 상세 (최대 13개)

### 1.jpg
- row 1: 7/7  missing=[없음]
- row 2: 7/7  missing=[없음]
- row 3: 7/7  missing=[없음]
- row 4: 5/7  missing=[manufacturingNo, expiryDate]
- row 5: 7/7  missing=[없음]
- row 6: 7/7  missing=[없음]
- row 7: 7/7  missing=[없음]
- row 8: 7/7  missing=[없음]
- row 9: 7/7  missing=[없음]
- row 10: 7/7  missing=[없음]
- row 11: 7/7  missing=[없음]
- row 12: 6/7  missing=[quantity]
- row 13: 7/7  missing=[없음]

### 2.pdf
- row 1: 3/8  missing=[quantity, consumerUnitPrice, supplyUnitPrice, supplyAmount, insuranceCode]
- row 2: 5/8  missing=[itemName, quantity, insuranceCode]
- row 3: 5/8  missing=[itemName, supplyAmount, insuranceCode]
- row 4: 4/8  missing=[itemName, quantity, supplyAmount, insuranceCode]
- row 5: 6/8  missing=[itemName, insuranceCode]
- row 6: 5/8  missing=[itemName, supplyAmount, insuranceCode]
- row 7: 5/8  missing=[itemName, supplyAmount, insuranceCode]
- row 8: 5/8  missing=[itemName, supplyAmount, insuranceCode]
- row 9: 6/8  missing=[itemName, insuranceCode]
- row 10: 5/8  missing=[itemName, supplyAmount, insuranceCode]
- row 11: 5/8  missing=[itemName, supplyAmount, insuranceCode]
- row 12: 4/8  missing=[itemName, quantity, supplyAmount, insuranceCode]
- row 13: 5/8  missing=[quantity, supplyAmount, insuranceCode]

### 3.pdf
- row 1: 2/9  missing=[insuranceCode, itemName, spec, unitPrice, amount, manufacturer, manufacturingExpiryComposite]

### 4.pdf
- row 1: 5/7  missing=[lotNo, taxAmount]

### 5.pdf
- row 1: 1/5  missing=[itemCode, quantity, unitPrice, amount]
- row 2: 2/5  missing=[itemCode, unitPrice, amount]
- row 3: 2/5  missing=[itemCode, unitPrice, amount]
- row 4: 1/5  missing=[itemCode, quantity, unitPrice, amount]
- row 5: 1/5  missing=[itemCode, quantity, unitPrice, amount]
- row 6: 1/5  missing=[itemCode, quantity, unitPrice, amount]

### 6.pdf
- row 1: 6/6  missing=[없음]
- row 2: 6/6  missing=[없음]
- row 3: 6/6  missing=[없음]
- row 4: 6/6  missing=[없음]
- row 5: 4/6  missing=[lotNo, expiryDate]
- row 6: 4/6  missing=[lotNo, expiryDate]

### 7.pdf
- row 1: 3/4  missing=[quantity]
