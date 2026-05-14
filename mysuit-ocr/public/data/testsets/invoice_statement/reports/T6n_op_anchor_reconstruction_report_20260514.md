# T-6n OP Anchor Row Reconstruction 검증 결과

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

## 2.pdf 행 미리보기
| # | itemCode | itemName | quantity | consumerUnitPrice | supplyAmount |
|---|---|---|---|---|---|
| 1 | OP-NA0300 |  | 3024 | 30,360 |  |
| 2 | OP-NA0030 |  |  | 3,036 |  |
| 3 | OP-M00100 |  | 300 | 34,002 | 9,064 |
| 4 | OP-M00030 |  | 200 | 2,719 |  |
| 5 | OP-AM0030 |  | 333 | 2,139 |  |
| 6 |  |  |  |  |  |
| 7 | OP-L00500 |  | 6 | 55,000 |  |
| 8 | OP-L00030 |  | 33 | 500,028 | 3,300 |
| 9 | OP-AM0300 |  | 4 | 21,384 |  |
| 10 | OP-CF0030 |  | 8 | 9,821 |  |
| 11 | OP-CF0100 |  |  | 32,736 |  |
| 12 | P-AL_0500 |  | 2 | 24,200 |  |
| 13 | P-AF0100 | 금 |  | 14,080 |  |
