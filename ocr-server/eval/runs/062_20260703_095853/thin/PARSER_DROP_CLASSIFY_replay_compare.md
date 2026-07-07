# Parser-drop classification — 062_20260703_095853\thin

Defects scored (mismatch|ext_missing): **83788**  |  parser-drop (OCR read it, recoverable): **49685**  |  ambiguous_fuzzy (fuzzy-only, pending): **541**  |  recognition (OCR-bound): **33562**
Parser-recoverable share of defects: **59.3%**

## Parser-drops by column × pattern — CLEAN originals  (n=0)

| column | drop | mislocate | wrongpick | total |
|---|--:|--:|--:|--:|

## Parser-drops by column × pattern — ANGLE variants  (n=49685)

| column | drop | mislocate | wrongpick | total |
|---|--:|--:|--:|--:|
| spec | 5096 | 830 | 1527 | **7453** |
| unitPrice | 3478 | 1275 | 1039 | **5792** |
| manufacturingNo | 4198 | 544 | 1046 | **5788** |
| quantity | 2725 | 1301 | 1045 | **5071** |
| itemName | 2062 | 384 | 2608 | **5054** |
| insuranceCode | 3602 | 499 | 760 | **4861** |
| amount | 3148 | 365 | 1152 | **4665** |
| expiryDate | 3330 | 357 | 393 | **4080** |
| itemNameMaster | 1512 | 120 | 230 | **1862** |
| taxAmount | 342 | 108 | 313 | **763** |
| supplyAmount | 294 | 176 | 283 | **753** |
| buyerCompany | 143 | 2 | 574 | **719** |
| totalAmount | 35 | 162 | 512 | **709** |
| supplierCompany | 28 | 7 | 640 | **675** |
| supplierBizNumber | 66 | 110 | 211 | **387** |
| buyerBizNumber | 20 | 93 | 153 | **266** |
| buyerAddress | 11 | 4 | 251 | **266** |
| discountAmount | 0 | 43 | 155 | **198** |
| issueDate | 0 | 0 | 178 | **178** |
| itemCode | 59 | 0 | 39 | **98** |
| supplierAddress | 1 | 6 | 40 | **47** |

## Parser-drops by column × pattern — ALL  (n=49685)

| column | drop | mislocate | wrongpick | total |
|---|--:|--:|--:|--:|
| spec | 5096 | 830 | 1527 | **7453** |
| unitPrice | 3478 | 1275 | 1039 | **5792** |
| manufacturingNo | 4198 | 544 | 1046 | **5788** |
| quantity | 2725 | 1301 | 1045 | **5071** |
| itemName | 2062 | 384 | 2608 | **5054** |
| insuranceCode | 3602 | 499 | 760 | **4861** |
| amount | 3148 | 365 | 1152 | **4665** |
| expiryDate | 3330 | 357 | 393 | **4080** |
| itemNameMaster | 1512 | 120 | 230 | **1862** |
| taxAmount | 342 | 108 | 313 | **763** |
| supplyAmount | 294 | 176 | 283 | **753** |
| buyerCompany | 143 | 2 | 574 | **719** |
| totalAmount | 35 | 162 | 512 | **709** |
| supplierCompany | 28 | 7 | 640 | **675** |
| supplierBizNumber | 66 | 110 | 211 | **387** |
| buyerBizNumber | 20 | 93 | 153 | **266** |
| buyerAddress | 11 | 4 | 251 | **266** |
| discountAmount | 0 | 43 | 155 | **198** |
| issueDate | 0 | 0 | 178 | **178** |
| itemCode | 59 | 0 | 39 | **98** |
| supplierAddress | 1 | 6 | 40 | **47** |

## Ambiguous fuzzy-only evidence by column

| column | count |
|---|--:|
| itemName | 375 |
| itemNameMaster | 55 |
| spec | 28 |
| insuranceCode | 24 |
| manufacturingNo | 16 |
| buyerCompany | 13 |
| buyerAddress | 12 |
| supplierAddress | 11 |
| supplierCompany | 7 |

## Recognition (OCR-bound, NOT parser) by column

| column | count |
|---|--:|
| itemCode | 7424 |
| itemNameMaster | 4302 |
| itemName | 3961 |
| expiryDate | 2162 |
| spec | 2020 |
| quantity | 1880 |
| supplierAddress | 1699 |
| buyerAddress | 1694 |
| manufacturingNo | 1481 |
| supplierCompany | 1275 |
| buyerCompany | 1264 |
| insuranceCode | 1254 |
| unitPrice | 1058 |
| amount | 764 |
| supplyAmount | 337 |
| taxAmount | 274 |
| totalAmount | 263 |
| taxType | 241 |
| supplierBizNumber | 93 |
| issueDate | 67 |
| buyerBizNumber | 47 |
| discountAmount | 2 |

## Preprocessing diagnosis  (telemetry 2000/2000 samples)

recognition rate = recognition defects / scored cells. Δ = vs baseline bucket (+ = that condition is costing accuracy → fix server-side preprocessing).

### Orientation

| condition | n | cellAcc | recognition% | Δ vs base |
|---|--:|--:|--:|--:|
| 270° 적용 | 105 | 31.8% | 36.1% | +7.0pp |
| 180° 적용 | 47 | 40.0% | 29.2% | +0.1pp |
| 미적용(0°) | 1738 | 37.4% | 29.1% | — |
| 90° 적용 | 110 | 46.1% | 25.8% | -3.3pp |

### Deskew

| condition | n | cellAcc | recognition% | Δ vs base |
|---|--:|--:|--:|--:|
| ≤2° | 215 | 33.2% | 33.0% | +4.4pp |
| >2° | 24 | 27.2% | 31.8% | +3.2pp |
| 미적용 | 1761 | 38.6% | 28.6% | — |

### Warp

| condition | n | cellAcc | recognition% | Δ vs base |
|---|--:|--:|--:|--:|
| 영역50–90% | 1 | 11.1% | 66.7% | +37.5pp |
| forcedWarpOnSkip | 2000 | 37.9% | 29.1% | +0.0pp |
| 영역≥90% | 1999 | 37.9% | 29.1% | — |
