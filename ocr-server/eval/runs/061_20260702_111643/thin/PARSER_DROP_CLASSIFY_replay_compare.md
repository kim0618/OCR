# Parser-drop classification — 061_20260702_111643\thin

Defects scored (mismatch|ext_missing): **113213**  |  parser-drop (OCR read it, recoverable): **70522**  |  ambiguous_fuzzy (fuzzy-only, pending): **1379**  |  recognition (OCR-bound): **41312**
Parser-recoverable share of defects: **62.3%**

## Parser-drops by column × pattern — CLEAN originals  (n=0)

| column | drop | mislocate | wrongpick | total |
|---|--:|--:|--:|--:|

## Parser-drops by column × pattern — ANGLE variants  (n=70522)

| column | drop | mislocate | wrongpick | total |
|---|--:|--:|--:|--:|
| amount | 8319 | 557 | 285 | **9161** |
| spec | 7769 | 599 | 730 | **9098** |
| unitPrice | 7892 | 360 | 434 | **8686** |
| manufacturingNo | 7035 | 376 | 189 | **7600** |
| quantity | 5534 | 836 | 690 | **7060** |
| itemName | 3817 | 41 | 2940 | **6798** |
| expiryDate | 6180 | 195 | 153 | **6528** |
| insuranceCode | 5153 | 380 | 105 | **5638** |
| itemNameMaster | 4110 | 720 | 0 | **4830** |
| supplyAmount | 291 | 155 | 329 | **775** |
| taxAmount | 337 | 94 | 340 | **771** |
| buyerCompany | 138 | 2 | 580 | **720** |
| totalAmount | 45 | 187 | 481 | **713** |
| supplierCompany | 32 | 7 | 618 | **657** |
| supplierBizNumber | 79 | 122 | 188 | **389** |
| buyerBizNumber | 18 | 96 | 153 | **267** |
| buyerAddress | 7 | 4 | 255 | **266** |
| discountAmount | 0 | 78 | 119 | **197** |
| issueDate | 0 | 0 | 178 | **178** |
| itemCode | 125 | 0 | 20 | **145** |
| supplierAddress | 1 | 6 | 38 | **45** |

## Parser-drops by column × pattern — ALL  (n=70522)

| column | drop | mislocate | wrongpick | total |
|---|--:|--:|--:|--:|
| amount | 8319 | 557 | 285 | **9161** |
| spec | 7769 | 599 | 730 | **9098** |
| unitPrice | 7892 | 360 | 434 | **8686** |
| manufacturingNo | 7035 | 376 | 189 | **7600** |
| quantity | 5534 | 836 | 690 | **7060** |
| itemName | 3817 | 41 | 2940 | **6798** |
| expiryDate | 6180 | 195 | 153 | **6528** |
| insuranceCode | 5153 | 380 | 105 | **5638** |
| itemNameMaster | 4110 | 720 | 0 | **4830** |
| supplyAmount | 291 | 155 | 329 | **775** |
| taxAmount | 337 | 94 | 340 | **771** |
| buyerCompany | 138 | 2 | 580 | **720** |
| totalAmount | 45 | 187 | 481 | **713** |
| supplierCompany | 32 | 7 | 618 | **657** |
| supplierBizNumber | 79 | 122 | 188 | **389** |
| buyerBizNumber | 18 | 96 | 153 | **267** |
| buyerAddress | 7 | 4 | 255 | **266** |
| discountAmount | 0 | 78 | 119 | **197** |
| issueDate | 0 | 0 | 178 | **178** |
| itemCode | 125 | 0 | 20 | **145** |
| supplierAddress | 1 | 6 | 38 | **45** |

## Ambiguous fuzzy-only evidence by column

| column | count |
|---|--:|
| itemName | 883 |
| itemNameMaster | 250 |
| insuranceCode | 96 |
| spec | 69 |
| manufacturingNo | 39 |
| buyerCompany | 13 |
| buyerAddress | 11 |
| supplierAddress | 10 |
| supplierCompany | 6 |
| itemCode | 2 |

## Recognition (OCR-bound, NOT parser) by column

| column | count |
|---|--:|
| itemCode | 12269 |
| itemNameMaster | 7362 |
| itemName | 3518 |
| quantity | 2294 |
| expiryDate | 2109 |
| spec | 1966 |
| supplierAddress | 1702 |
| buyerAddress | 1699 |
| manufacturingNo | 1403 |
| supplierCompany | 1282 |
| buyerCompany | 1265 |
| insuranceCode | 1162 |
| unitPrice | 1121 |
| amount | 802 |
| supplyAmount | 340 |
| taxAmount | 277 |
| totalAmount | 268 |
| taxType | 241 |
| supplierBizNumber | 105 |
| issueDate | 73 |
| buyerBizNumber | 51 |
| discountAmount | 3 |

## Preprocessing diagnosis  (telemetry 2002/2002 samples)

recognition rate = recognition defects / scored cells. Δ = vs baseline bucket (+ = that condition is costing accuracy → fix server-side preprocessing).

### Orientation

| condition | n | cellAcc | recognition% | Δ vs base |
|---|--:|--:|--:|--:|
| 270° 적용 | 105 | 5.1% | 47.4% | +12.5pp |
| 90° 적용 | 110 | 6.1% | 40.9% | +6.0pp |
| 180° 적용 | 47 | 19.7% | 36.7% | +1.7pp |
| 미적용(0°) | 1740 | 13.0% | 35.0% | — |

### Deskew

| condition | n | cellAcc | recognition% | Δ vs base |
|---|--:|--:|--:|--:|
| >2° | 24 | 3.7% | 42.4% | +6.8pp |
| ≤2° | 218 | 12.7% | 37.7% | +2.2pp |
| 미적용 | 1760 | 12.5% | 35.5% | — |

### Warp

| condition | n | cellAcc | recognition% | Δ vs base |
|---|--:|--:|--:|--:|
| 영역50–90% | 2 | 11.1% | 133.3% | +97.5pp |
| forcedWarpOnSkip | 2002 | 12.4% | 35.9% | +0.0pp |
| 영역≥90% | 2000 | 12.4% | 35.8% | — |
