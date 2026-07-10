# Parser-drop classification — 065_20260709_090049\thin

Defects scored (mismatch|ext_missing): **73319**  |  parser-drop (OCR read it, recoverable): **43735**  |  ambiguous_fuzzy (fuzzy-only, pending): **432**  |  recognition (OCR-bound): **29152**
Parser-recoverable share of defects: **59.7%**

## Parser-drops by column × pattern — CLEAN originals  (n=0)

| column | drop | mislocate | wrongpick | total |
|---|--:|--:|--:|--:|

## Parser-drops by column × pattern — ANGLE variants  (n=43735)

| column | drop | mislocate | wrongpick | total |
|---|--:|--:|--:|--:|
| spec | 4827 | 813 | 1619 | **7259** |
| unitPrice | 2642 | 1530 | 1305 | **5477** |
| manufacturingNo | 3809 | 590 | 983 | **5382** |
| insuranceCode | 3413 | 484 | 994 | **4891** |
| quantity | 2335 | 1305 | 986 | **4626** |
| amount | 2248 | 408 | 1635 | **4291** |
| expiryDate | 2929 | 378 | 489 | **3796** |
| itemName | 646 | 513 | 2443 | **3602** |
| taxAmount | 343 | 106 | 314 | **763** |
| supplyAmount | 292 | 177 | 284 | **753** |
| totalAmount | 34 | 164 | 511 | **709** |
| itemNameMaster | 346 | 171 | 183 | **700** |
| supplierCompany | 0 | 24 | 242 | **266** |
| buyerAddress | 11 | 3 | 252 | **266** |
| buyerBizNumber | 14 | 49 | 171 | **234** |
| discountAmount | 0 | 43 | 155 | **198** |
| issueDate | 0 | 0 | 178 | **178** |
| buyerCompany | 16 | 3 | 139 | **158** |
| supplierBizNumber | 7 | 3 | 69 | **79** |
| itemCode | 37 | 1 | 38 | **76** |
| supplierAddress | 1 | 4 | 26 | **31** |

## Parser-drops by column × pattern — ALL  (n=43735)

| column | drop | mislocate | wrongpick | total |
|---|--:|--:|--:|--:|
| spec | 4827 | 813 | 1619 | **7259** |
| unitPrice | 2642 | 1530 | 1305 | **5477** |
| manufacturingNo | 3809 | 590 | 983 | **5382** |
| insuranceCode | 3413 | 484 | 994 | **4891** |
| quantity | 2335 | 1305 | 986 | **4626** |
| amount | 2248 | 408 | 1635 | **4291** |
| expiryDate | 2929 | 378 | 489 | **3796** |
| itemName | 646 | 513 | 2443 | **3602** |
| taxAmount | 343 | 106 | 314 | **763** |
| supplyAmount | 292 | 177 | 284 | **753** |
| totalAmount | 34 | 164 | 511 | **709** |
| itemNameMaster | 346 | 171 | 183 | **700** |
| supplierCompany | 0 | 24 | 242 | **266** |
| buyerAddress | 11 | 3 | 252 | **266** |
| buyerBizNumber | 14 | 49 | 171 | **234** |
| discountAmount | 0 | 43 | 155 | **198** |
| issueDate | 0 | 0 | 178 | **178** |
| buyerCompany | 16 | 3 | 139 | **158** |
| supplierBizNumber | 7 | 3 | 69 | **79** |
| itemCode | 37 | 1 | 38 | **76** |
| supplierAddress | 1 | 4 | 26 | **31** |

## Ambiguous fuzzy-only evidence by column

| column | count |
|---|--:|
| itemName | 196 |
| buyerCompany | 131 |
| supplierAddress | 30 |
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
| supplierAddress | 1108 |
| unitPrice | 1095 |
| amount | 814 |
| supplierCompany | 741 |
| supplyAmount | 337 |
| taxAmount | 274 |
| totalAmount | 263 |
| taxType | 241 |
| supplierBizNumber | 92 |
| issueDate | 67 |
| buyerBizNumber | 47 |
| discountAmount | 2 |

## Preprocessing diagnosis  (telemetry 2002/2002 samples)

recognition rate = recognition defects / scored cells. Δ = vs baseline bucket (+ = that condition is costing accuracy → fix server-side preprocessing).

### Orientation

| condition | n | cellAcc | recognition% | Δ vs base |
|---|--:|--:|--:|--:|
| 270° 적용 | 105 | 38.9% | 32.0% | +6.7pp |
| 180° 적용 | 47 | 46.9% | 26.3% | +1.0pp |
| 미적용(0°) | 1740 | 44.5% | 25.3% | — |
| 90° 적용 | 110 | 54.6% | 21.1% | -4.3pp |

### Deskew

| condition | n | cellAcc | recognition% | Δ vs base |
|---|--:|--:|--:|--:|
| ≤2° | 217 | 39.1% | 30.1% | +5.5pp |
| >2° | 24 | 38.2% | 29.3% | +4.6pp |
| 미적용 | 1761 | 45.8% | 24.7% | — |

### Warp

| condition | n | cellAcc | recognition% | Δ vs base |
|---|--:|--:|--:|--:|
| 영역50–90% | 2 | 44.4% | 100.0% | +74.7pp |
| forcedWarpOnSkip | 2002 | 45.0% | 25.3% | +0.0pp |
| 영역≥90% | 2000 | 45.0% | 25.3% | — |
