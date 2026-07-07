# Parser-drop classification — 063_20260707_121352/thin

Defects scored (mismatch|ext_missing): **82105**  |  parser-drop (OCR read it, recoverable): **48788**  |  ambiguous_fuzzy (fuzzy-only, pending): **678**  |  recognition (OCR-bound): **32639**
Parser-recoverable share of defects: **59.4%**

## Parser-drops by column × pattern — CLEAN originals  (n=0)

| column | drop | mislocate | wrongpick | total |
|---|--:|--:|--:|--:|

## Parser-drops by column × pattern — ANGLE variants  (n=48788)

| column | drop | mislocate | wrongpick | total |
|---|--:|--:|--:|--:|
| spec | 5096 | 830 | 1528 | **7454** |
| unitPrice | 3478 | 1275 | 1039 | **5792** |
| manufacturingNo | 4198 | 545 | 1046 | **5789** |
| quantity | 2726 | 1302 | 1047 | **5075** |
| itemName | 2059 | 386 | 2609 | **5054** |
| insuranceCode | 3602 | 499 | 760 | **4861** |
| amount | 3148 | 366 | 1152 | **4666** |
| expiryDate | 3330 | 357 | 393 | **4080** |
| itemNameMaster | 1512 | 120 | 231 | **1863** |
| taxAmount | 342 | 108 | 313 | **763** |
| supplyAmount | 294 | 176 | 283 | **753** |
| totalAmount | 35 | 162 | 512 | **709** |
| supplierBizNumber | 67 | 110 | 211 | **388** |
| supplierCompany | 20 | 44 | 274 | **338** |
| buyerBizNumber | 20 | 93 | 153 | **266** |
| buyerAddress | 11 | 4 | 251 | **266** |
| discountAmount | 0 | 43 | 155 | **198** |
| issueDate | 0 | 0 | 178 | **178** |
| buyerCompany | 15 | 8 | 135 | **158** |
| itemCode | 59 | 0 | 39 | **98** |
| supplierAddress | 1 | 5 | 33 | **39** |

## Parser-drops by column × pattern — ALL  (n=48788)

| column | drop | mislocate | wrongpick | total |
|---|--:|--:|--:|--:|
| spec | 5096 | 830 | 1528 | **7454** |
| unitPrice | 3478 | 1275 | 1039 | **5792** |
| manufacturingNo | 4198 | 545 | 1046 | **5789** |
| quantity | 2726 | 1302 | 1047 | **5075** |
| itemName | 2059 | 386 | 2609 | **5054** |
| insuranceCode | 3602 | 499 | 760 | **4861** |
| amount | 3148 | 366 | 1152 | **4666** |
| expiryDate | 3330 | 357 | 393 | **4080** |
| itemNameMaster | 1512 | 120 | 231 | **1863** |
| taxAmount | 342 | 108 | 313 | **763** |
| supplyAmount | 294 | 176 | 283 | **753** |
| totalAmount | 35 | 162 | 512 | **709** |
| supplierBizNumber | 67 | 110 | 211 | **388** |
| supplierCompany | 20 | 44 | 274 | **338** |
| buyerBizNumber | 20 | 93 | 153 | **266** |
| buyerAddress | 11 | 4 | 251 | **266** |
| discountAmount | 0 | 43 | 155 | **198** |
| issueDate | 0 | 0 | 178 | **178** |
| buyerCompany | 15 | 8 | 135 | **158** |
| itemCode | 59 | 0 | 39 | **98** |
| supplierAddress | 1 | 5 | 33 | **39** |

## Ambiguous fuzzy-only evidence by column

| column | count |
|---|--:|
| itemName | 375 |
| buyerCompany | 131 |
| itemNameMaster | 55 |
| supplierAddress | 37 |
| spec | 28 |
| insuranceCode | 24 |
| manufacturingNo | 16 |
| buyerAddress | 12 |

## Recognition (OCR-bound, NOT parser) by column

| column | count |
|---|--:|
| itemCode | 7433 |
| itemNameMaster | 4303 |
| itemName | 3965 |
| expiryDate | 2166 |
| spec | 2026 |
| quantity | 1881 |
| buyerAddress | 1696 |
| manufacturingNo | 1484 |
| buyerCompany | 1263 |
| insuranceCode | 1254 |
| supplierAddress | 1208 |
| unitPrice | 1058 |
| supplierCompany | 813 |
| amount | 765 |
| supplyAmount | 337 |
| taxAmount | 274 |
| totalAmount | 263 |
| taxType | 241 |
| supplierBizNumber | 93 |
| issueDate | 67 |
| buyerBizNumber | 47 |
| discountAmount | 2 |

## Preprocessing diagnosis  (telemetry 2002/2002 samples)

recognition rate = recognition defects / scored cells. Δ = vs baseline bucket (+ = that condition is costing accuracy → fix server-side preprocessing).

### Orientation

| condition | n | cellAcc | recognition% | Δ vs base |
|---|--:|--:|--:|--:|
| 270° 적용 | 105 | 31.8% | 35.2% | +6.9pp |
| 미적용(0°) | 1740 | 37.5% | 28.3% | — |
| 180° 적용 | 47 | 40.0% | 28.2% | -0.1pp |
| 90° 적용 | 110 | 46.1% | 25.0% | -3.3pp |

### Deskew

| condition | n | cellAcc | recognition% | Δ vs base |
|---|--:|--:|--:|--:|
| ≤2° | 217 | 33.4% | 32.3% | +4.5pp |
| >2° | 24 | 27.2% | 30.7% | +2.9pp |
| 미적용 | 1761 | 38.6% | 27.8% | — |

### Warp

| condition | n | cellAcc | recognition% | Δ vs base |
|---|--:|--:|--:|--:|
| 영역50–90% | 1 | 11.1% | 66.7% | +38.3pp |
| forcedWarpOnSkip | 2002 | 37.9% | 28.3% | +0.0pp |
| 영역≥90% | 2001 | 37.9% | 28.3% | — |
