# Parser-drop classification — 065_20260709_090049\thin

Defects scored (mismatch|ext_missing): **73920**  |  parser-drop (OCR read it, recoverable): **44156**  |  ambiguous_fuzzy (fuzzy-only, pending): **439**  |  recognition (OCR-bound): **29325**
Parser-recoverable share of defects: **59.7%**

## Parser-drops by column × pattern — CLEAN originals  (n=0)

| column | drop | mislocate | wrongpick | total |
|---|--:|--:|--:|--:|

## Parser-drops by column × pattern — ANGLE variants  (n=44156)

| column | drop | mislocate | wrongpick | total |
|---|--:|--:|--:|--:|
| spec | 4827 | 813 | 1619 | **7259** |
| unitPrice | 2642 | 1530 | 1305 | **5477** |
| manufacturingNo | 3809 | 590 | 983 | **5382** |
| insuranceCode | 3411 | 486 | 994 | **4891** |
| quantity | 2335 | 1305 | 986 | **4626** |
| amount | 2248 | 408 | 1635 | **4291** |
| expiryDate | 2929 | 378 | 489 | **3796** |
| itemName | 646 | 513 | 2443 | **3602** |
| taxAmount | 343 | 106 | 314 | **763** |
| supplyAmount | 292 | 177 | 284 | **753** |
| totalAmount | 34 | 164 | 511 | **709** |
| itemNameMaster | 346 | 171 | 183 | **700** |
| supplierBizNumber | 67 | 110 | 211 | **388** |
| supplierCompany | 20 | 44 | 274 | **338** |
| buyerBizNumber | 20 | 93 | 153 | **266** |
| buyerAddress | 11 | 4 | 251 | **266** |
| discountAmount | 0 | 43 | 155 | **198** |
| issueDate | 0 | 0 | 178 | **178** |
| buyerCompany | 15 | 8 | 135 | **158** |
| itemCode | 37 | 1 | 38 | **76** |
| supplierAddress | 1 | 5 | 33 | **39** |

## Parser-drops by column × pattern — ALL  (n=44156)

| column | drop | mislocate | wrongpick | total |
|---|--:|--:|--:|--:|
| spec | 4827 | 813 | 1619 | **7259** |
| unitPrice | 2642 | 1530 | 1305 | **5477** |
| manufacturingNo | 3809 | 590 | 983 | **5382** |
| insuranceCode | 3411 | 486 | 994 | **4891** |
| quantity | 2335 | 1305 | 986 | **4626** |
| amount | 2248 | 408 | 1635 | **4291** |
| expiryDate | 2929 | 378 | 489 | **3796** |
| itemName | 646 | 513 | 2443 | **3602** |
| taxAmount | 343 | 106 | 314 | **763** |
| supplyAmount | 292 | 177 | 284 | **753** |
| totalAmount | 34 | 164 | 511 | **709** |
| itemNameMaster | 346 | 171 | 183 | **700** |
| supplierBizNumber | 67 | 110 | 211 | **388** |
| supplierCompany | 20 | 44 | 274 | **338** |
| buyerBizNumber | 20 | 93 | 153 | **266** |
| buyerAddress | 11 | 4 | 251 | **266** |
| discountAmount | 0 | 43 | 155 | **198** |
| issueDate | 0 | 0 | 178 | **178** |
| buyerCompany | 15 | 8 | 135 | **158** |
| itemCode | 37 | 1 | 38 | **76** |
| supplierAddress | 1 | 5 | 33 | **39** |

## Ambiguous fuzzy-only evidence by column

| column | count |
|---|--:|
| itemName | 196 |
| buyerCompany | 131 |
| supplierAddress | 37 |
| itemNameMaster | 20 |
| spec | 17 |
| insuranceCode | 14 |
| manufacturingNo | 12 |
| buyerAddress | 12 |

## Recognition (OCR-bound, NOT parser) by column

| column | count |
|---|--:|
| itemCode | 5262 |
| itemName | 4139 |
| itemNameMaster | 2760 |
| expiryDate | 2228 |
| spec | 2086 |
| quantity | 1783 |
| buyerAddress | 1696 |
| manufacturingNo | 1542 |
| insuranceCode | 1312 |
| buyerCompany | 1263 |
| supplierAddress | 1208 |
| unitPrice | 1095 |
| amount | 814 |
| supplierCompany | 813 |
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
| 270° 적용 | 105 | 38.9% | 32.2% | +6.7pp |
| 180° 적용 | 47 | 46.9% | 26.5% | +1.0pp |
| 미적용(0°) | 1740 | 44.5% | 25.5% | — |
| 90° 적용 | 110 | 54.6% | 21.3% | -4.2pp |

### Deskew

| condition | n | cellAcc | recognition% | Δ vs base |
|---|--:|--:|--:|--:|
| ≤2° | 217 | 39.1% | 30.2% | +5.4pp |
| >2° | 24 | 38.2% | 29.6% | +4.8pp |
| 미적용 | 1761 | 45.8% | 24.8% | — |

### Warp

| condition | n | cellAcc | recognition% | Δ vs base |
|---|--:|--:|--:|--:|
| 영역50–90% | 2 | 44.4% | 100.0% | +74.6pp |
| forcedWarpOnSkip | 2002 | 45.0% | 25.4% | +0.0pp |
| 영역≥90% | 2000 | 45.0% | 25.4% | — |
