# Parser-drop classification — 065_20260709_090049/thin

Defects scored (mismatch|ext_missing): **74656**  |  parser-drop (OCR read it, recoverable): **44318**  |  ambiguous_fuzzy (fuzzy-only, pending): **448**  |  recognition (OCR-bound): **29890**
Parser-recoverable share of defects: **59.4%**

## Parser-drops by column × pattern — CLEAN originals  (n=0)

| column | drop | mislocate | wrongpick | total |
|---|--:|--:|--:|--:|

## Parser-drops by column × pattern — ANGLE variants  (n=44318)

| column | drop | mislocate | wrongpick | total |
|---|--:|--:|--:|--:|
| spec | 4830 | 815 | 1618 | **7263** |
| unitPrice | 2664 | 1512 | 1307 | **5483** |
| manufacturingNo | 3818 | 590 | 983 | **5391** |
| insuranceCode | 3419 | 483 | 994 | **4896** |
| quantity | 2337 | 1303 | 985 | **4625** |
| amount | 2276 | 403 | 1625 | **4304** |
| expiryDate | 2934 | 377 | 490 | **3801** |
| itemName | 659 | 499 | 2449 | **3607** |
| itemNameMaster | 400 | 178 | 231 | **809** |
| taxAmount | 342 | 107 | 314 | **763** |
| supplyAmount | 293 | 176 | 284 | **753** |
| totalAmount | 34 | 164 | 511 | **709** |
| supplierBizNumber | 67 | 110 | 211 | **388** |
| supplierCompany | 20 | 44 | 274 | **338** |
| buyerBizNumber | 20 | 93 | 153 | **266** |
| buyerAddress | 11 | 4 | 251 | **266** |
| discountAmount | 0 | 43 | 155 | **198** |
| issueDate | 0 | 0 | 178 | **178** |
| buyerCompany | 15 | 8 | 135 | **158** |
| itemCode | 39 | 2 | 42 | **83** |
| supplierAddress | 1 | 5 | 33 | **39** |

## Parser-drops by column × pattern — ALL  (n=44318)

| column | drop | mislocate | wrongpick | total |
|---|--:|--:|--:|--:|
| spec | 4830 | 815 | 1618 | **7263** |
| unitPrice | 2664 | 1512 | 1307 | **5483** |
| manufacturingNo | 3818 | 590 | 983 | **5391** |
| insuranceCode | 3419 | 483 | 994 | **4896** |
| quantity | 2337 | 1303 | 985 | **4625** |
| amount | 2276 | 403 | 1625 | **4304** |
| expiryDate | 2934 | 377 | 490 | **3801** |
| itemName | 659 | 499 | 2449 | **3607** |
| itemNameMaster | 400 | 178 | 231 | **809** |
| taxAmount | 342 | 107 | 314 | **763** |
| supplyAmount | 293 | 176 | 284 | **753** |
| totalAmount | 34 | 164 | 511 | **709** |
| supplierBizNumber | 67 | 110 | 211 | **388** |
| supplierCompany | 20 | 44 | 274 | **338** |
| buyerBizNumber | 20 | 93 | 153 | **266** |
| buyerAddress | 11 | 4 | 251 | **266** |
| discountAmount | 0 | 43 | 155 | **198** |
| issueDate | 0 | 0 | 178 | **178** |
| buyerCompany | 15 | 8 | 135 | **158** |
| itemCode | 39 | 2 | 42 | **83** |
| supplierAddress | 1 | 5 | 33 | **39** |

## Ambiguous fuzzy-only evidence by column

| column | count |
|---|--:|
| itemName | 204 |
| buyerCompany | 131 |
| supplierAddress | 37 |
| itemNameMaster | 20 |
| spec | 18 |
| insuranceCode | 14 |
| manufacturingNo | 12 |
| buyerAddress | 12 |

## Recognition (OCR-bound, NOT parser) by column

| column | count |
|---|--:|
| itemCode | 5576 |
| itemName | 4131 |
| itemNameMaster | 3059 |
| expiryDate | 2223 |
| spec | 2080 |
| quantity | 1782 |
| buyerAddress | 1696 |
| manufacturingNo | 1533 |
| insuranceCode | 1307 |
| buyerCompany | 1263 |
| supplierAddress | 1208 |
| unitPrice | 1088 |
| supplierCompany | 813 |
| amount | 807 |
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
| 270° 적용 | 105 | 38.1% | 32.8% | +6.9pp |
| 180° 적용 | 47 | 46.4% | 26.7% | +0.8pp |
| 미적용(0°) | 1740 | 43.8% | 26.0% | — |
| 90° 적용 | 110 | 54.1% | 21.6% | -4.3pp |

### Deskew

| condition | n | cellAcc | recognition% | Δ vs base |
|---|--:|--:|--:|--:|
| ≤2° | 217 | 38.6% | 30.6% | +5.2pp |
| >2° | 24 | 37.5% | 29.9% | +4.6pp |
| 미적용 | 1761 | 45.1% | 25.3% | — |

### Warp

| condition | n | cellAcc | recognition% | Δ vs base |
|---|--:|--:|--:|--:|
| 영역50–90% | 2 | 44.4% | 100.0% | +74.1pp |
| forcedWarpOnSkip | 2002 | 44.4% | 25.9% | +0.0pp |
| 영역≥90% | 2000 | 44.4% | 25.9% | — |
