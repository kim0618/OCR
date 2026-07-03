# Parser-drop classification — 062_20260703_095853/thin

Defects scored (mismatch|ext_missing): **112035**  |  parser-drop (OCR read it, recoverable): **70168**  |  ambiguous_fuzzy (fuzzy-only, pending): **1368**  |  recognition (OCR-bound): **40499**
Parser-recoverable share of defects: **62.6%**

## Parser-drops by column × pattern — CLEAN originals  (n=0)

| column | drop | mislocate | wrongpick | total |
|---|--:|--:|--:|--:|

## Parser-drops by column × pattern — ANGLE variants  (n=70168)

| column | drop | mislocate | wrongpick | total |
|---|--:|--:|--:|--:|
| spec | 7780 | 620 | 746 | **9146** |
| amount | 8248 | 548 | 286 | **9082** |
| unitPrice | 7719 | 365 | 451 | **8535** |
| manufacturingNo | 6994 | 392 | 261 | **7647** |
| itemName | 3932 | 30 | 2952 | **6914** |
| quantity | 5319 | 859 | 695 | **6873** |
| expiryDate | 6091 | 196 | 154 | **6441** |
| insuranceCode | 5129 | 391 | 117 | **5637** |
| itemNameMaster | 4154 | 700 | 0 | **4854** |
| supplyAmount | 267 | 149 | 320 | **736** |
| taxAmount | 300 | 107 | 328 | **735** |
| buyerCompany | 143 | 2 | 574 | **719** |
| totalAmount | 38 | 198 | 463 | **699** |
| supplierCompany | 29 | 7 | 625 | **661** |
| supplierBizNumber | 77 | 118 | 191 | **386** |
| buyerBizNumber | 20 | 97 | 149 | **266** |
| buyerAddress | 11 | 4 | 251 | **266** |
| discountAmount | 0 | 79 | 119 | **198** |
| issueDate | 0 | 0 | 178 | **178** |
| itemCode | 126 | 0 | 22 | **148** |
| supplierAddress | 1 | 6 | 40 | **47** |

## Parser-drops by column × pattern — ALL  (n=70168)

| column | drop | mislocate | wrongpick | total |
|---|--:|--:|--:|--:|
| spec | 7780 | 620 | 746 | **9146** |
| amount | 8248 | 548 | 286 | **9082** |
| unitPrice | 7719 | 365 | 451 | **8535** |
| manufacturingNo | 6994 | 392 | 261 | **7647** |
| itemName | 3932 | 30 | 2952 | **6914** |
| quantity | 5319 | 859 | 695 | **6873** |
| expiryDate | 6091 | 196 | 154 | **6441** |
| insuranceCode | 5129 | 391 | 117 | **5637** |
| itemNameMaster | 4154 | 700 | 0 | **4854** |
| supplyAmount | 267 | 149 | 320 | **736** |
| taxAmount | 300 | 107 | 328 | **735** |
| buyerCompany | 143 | 2 | 574 | **719** |
| totalAmount | 38 | 198 | 463 | **699** |
| supplierCompany | 29 | 7 | 625 | **661** |
| supplierBizNumber | 77 | 118 | 191 | **386** |
| buyerBizNumber | 20 | 97 | 149 | **266** |
| buyerAddress | 11 | 4 | 251 | **266** |
| discountAmount | 0 | 79 | 119 | **198** |
| issueDate | 0 | 0 | 178 | **178** |
| itemCode | 126 | 0 | 22 | **148** |
| supplierAddress | 1 | 6 | 40 | **47** |

## Ambiguous fuzzy-only evidence by column

| column | count |
|---|--:|
| itemName | 889 |
| itemNameMaster | 232 |
| insuranceCode | 93 |
| spec | 70 |
| manufacturingNo | 40 |
| buyerCompany | 13 |
| buyerAddress | 12 |
| supplierAddress | 11 |
| supplierCompany | 7 |
| itemCode | 1 |

## Recognition (OCR-bound, NOT parser) by column

| column | count |
|---|--:|
| itemCode | 12267 |
| itemNameMaster | 7356 |
| itemName | 3416 |
| quantity | 2200 |
| expiryDate | 2044 |
| spec | 1809 |
| supplierAddress | 1701 |
| buyerAddress | 1696 |
| manufacturingNo | 1324 |
| supplierCompany | 1277 |
| buyerCompany | 1266 |
| insuranceCode | 1070 |
| unitPrice | 1019 |
| amount | 713 |
| supplyAmount | 339 |
| taxAmount | 276 |
| totalAmount | 266 |
| taxType | 243 |
| supplierBizNumber | 95 |
| issueDate | 69 |
| buyerBizNumber | 49 |
| discountAmount | 4 |

## Preprocessing diagnosis  (telemetry 2000/2002 samples)

recognition rate = recognition defects / scored cells. Δ = vs baseline bucket (+ = that condition is costing accuracy → fix server-side preprocessing).

### Orientation

| condition | n | cellAcc | recognition% | Δ vs base |
|---|--:|--:|--:|--:|
| 270° 적용 | 105 | 8.2% | 41.2% | +6.3pp |
| 180° 적용 | 47 | 20.2% | 36.1% | +1.1pp |
| 미적용(0°) | 1738 | 13.0% | 35.0% | — |
| 90° 적용 | 110 | 18.7% | 32.8% | -2.2pp |

### Deskew

| condition | n | cellAcc | recognition% | Δ vs base |
|---|--:|--:|--:|--:|
| ≤2° | 215 | 13.2% | 36.4% | +1.5pp |
| 미적용 | 1761 | 13.5% | 34.9% | — |
| >2° | 24 | 6.2% | 33.1% | -1.8pp |

### Warp

| condition | n | cellAcc | recognition% | Δ vs base |
|---|--:|--:|--:|--:|
| 영역50–90% | 1 | 11.1% | 66.7% | +31.6pp |
| forcedWarpOnSkip | 2000 | 13.4% | 35.1% | +0.0pp |
| 영역≥90% | 1999 | 13.4% | 35.1% | — |
