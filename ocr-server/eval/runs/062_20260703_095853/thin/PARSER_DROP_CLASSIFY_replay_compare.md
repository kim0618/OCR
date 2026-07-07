# Parser-drop classification — 062_20260703_095853\thin

Defects scored (mismatch|ext_missing): **82061**  |  parser-drop (OCR read it, recoverable): **48778**  |  ambiguous_fuzzy (fuzzy-only, pending): **677**  |  recognition (OCR-bound): **32606**
Parser-recoverable share of defects: **59.4%**

## Parser-drops by column × pattern — CLEAN originals  (n=0)

| column | drop | mislocate | wrongpick | total |
|---|--:|--:|--:|--:|

## Parser-drops by column × pattern — ANGLE variants  (n=48778)

| column | drop | mislocate | wrongpick | total |
|---|--:|--:|--:|--:|
| spec | 5096 | 830 | 1527 | **7453** |
| unitPrice | 3478 | 1275 | 1039 | **5792** |
| manufacturingNo | 4198 | 544 | 1046 | **5788** |
| quantity | 2725 | 1301 | 1045 | **5071** |
| itemName | 2059 | 386 | 2609 | **5054** |
| insuranceCode | 3602 | 499 | 760 | **4861** |
| amount | 3148 | 365 | 1152 | **4665** |
| expiryDate | 3330 | 357 | 393 | **4080** |
| itemNameMaster | 1512 | 120 | 230 | **1862** |
| taxAmount | 342 | 108 | 313 | **763** |
| supplyAmount | 294 | 176 | 283 | **753** |
| totalAmount | 35 | 162 | 512 | **709** |
| supplierBizNumber | 66 | 110 | 211 | **387** |
| supplierCompany | 20 | 44 | 273 | **337** |
| buyerBizNumber | 20 | 93 | 153 | **266** |
| buyerAddress | 11 | 4 | 251 | **266** |
| discountAmount | 0 | 43 | 155 | **198** |
| issueDate | 0 | 0 | 178 | **178** |
| buyerCompany | 15 | 8 | 135 | **158** |
| itemCode | 59 | 0 | 39 | **98** |
| supplierAddress | 1 | 5 | 33 | **39** |

## Parser-drops by column × pattern — ALL  (n=48778)

| column | drop | mislocate | wrongpick | total |
|---|--:|--:|--:|--:|
| spec | 5096 | 830 | 1527 | **7453** |
| unitPrice | 3478 | 1275 | 1039 | **5792** |
| manufacturingNo | 4198 | 544 | 1046 | **5788** |
| quantity | 2725 | 1301 | 1045 | **5071** |
| itemName | 2059 | 386 | 2609 | **5054** |
| insuranceCode | 3602 | 499 | 760 | **4861** |
| amount | 3148 | 365 | 1152 | **4665** |
| expiryDate | 3330 | 357 | 393 | **4080** |
| itemNameMaster | 1512 | 120 | 230 | **1862** |
| taxAmount | 342 | 108 | 313 | **763** |
| supplyAmount | 294 | 176 | 283 | **753** |
| totalAmount | 35 | 162 | 512 | **709** |
| supplierBizNumber | 66 | 110 | 211 | **387** |
| supplierCompany | 20 | 44 | 273 | **337** |
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
| buyerCompany | 130 |
| itemNameMaster | 55 |
| supplierAddress | 37 |
| spec | 28 |
| insuranceCode | 24 |
| manufacturingNo | 16 |
| buyerAddress | 12 |

## Recognition (OCR-bound, NOT parser) by column

| column | count |
|---|--:|
| itemCode | 7424 |
| itemNameMaster | 4302 |
| itemName | 3961 |
| expiryDate | 2162 |
| spec | 2020 |
| quantity | 1880 |
| buyerAddress | 1694 |
| manufacturingNo | 1481 |
| buyerCompany | 1262 |
| insuranceCode | 1254 |
| supplierAddress | 1207 |
| unitPrice | 1058 |
| supplierCompany | 813 |
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
| 270° 적용 | 105 | 31.8% | 35.2% | +6.9pp |
| 미적용(0°) | 1738 | 37.4% | 28.3% | — |
| 180° 적용 | 47 | 40.0% | 28.2% | -0.1pp |
| 90° 적용 | 110 | 46.1% | 25.0% | -3.3pp |

### Deskew

| condition | n | cellAcc | recognition% | Δ vs base |
|---|--:|--:|--:|--:|
| ≤2° | 215 | 33.2% | 32.2% | +4.4pp |
| >2° | 24 | 27.2% | 30.7% | +2.9pp |
| 미적용 | 1761 | 38.6% | 27.8% | — |

### Warp

| condition | n | cellAcc | recognition% | Δ vs base |
|---|--:|--:|--:|--:|
| 영역50–90% | 1 | 11.1% | 66.7% | +38.4pp |
| forcedWarpOnSkip | 2000 | 37.9% | 28.3% | +0.0pp |
| 영역≥90% | 1999 | 37.9% | 28.3% | — |
