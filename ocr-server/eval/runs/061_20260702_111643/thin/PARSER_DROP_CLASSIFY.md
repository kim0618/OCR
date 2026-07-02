# Parser-drop classification — 061_20260702_111643/thin

Defects scored (mismatch|ext_missing): **117357**  |  parser-drop (OCR read it, recoverable): **71110**  |  ambiguous_fuzzy (fuzzy-only, pending): **1387**  |  recognition (OCR-bound): **44860**
Parser-recoverable share of defects: **60.6%**

## Parser-drops by column × pattern — CLEAN originals  (n=0)

| column | drop | mislocate | wrongpick | total |
|---|--:|--:|--:|--:|

## Parser-drops by column × pattern — ANGLE variants  (n=71110)

| column | drop | mislocate | wrongpick | total |
|---|--:|--:|--:|--:|
| amount | 8324 | 552 | 285 | **9161** |
| spec | 7770 | 599 | 730 | **9099** |
| unitPrice | 7892 | 360 | 434 | **8686** |
| manufacturingNo | 7517 | 329 | 96 | **7942** |
| quantity | 5533 | 835 | 690 | **7058** |
| itemName | 3817 | 41 | 2941 | **6799** |
| expiryDate | 6413 | 123 | 135 | **6671** |
| insuranceCode | 5269 | 368 | 73 | **5710** |
| itemNameMaster | 4113 | 721 | 0 | **4834** |
| supplyAmount | 291 | 155 | 329 | **775** |
| taxAmount | 337 | 94 | 340 | **771** |
| buyerCompany | 138 | 2 | 580 | **720** |
| totalAmount | 45 | 187 | 481 | **713** |
| supplierCompany | 32 | 7 | 618 | **657** |
| supplierBizNumber | 79 | 122 | 188 | **389** |
| buyerBizNumber | 18 | 96 | 153 | **267** |
| buyerAddress | 7 | 4 | 255 | **266** |
| discountAmount | 119 | 78 | 0 | **197** |
| issueDate | 0 | 0 | 178 | **178** |
| itemCode | 125 | 0 | 20 | **145** |
| supplierAddress | 1 | 6 | 38 | **45** |
| taxType | 27 | 0 | 0 | **27** |

## Parser-drops by column × pattern — ALL  (n=71110)

| column | drop | mislocate | wrongpick | total |
|---|--:|--:|--:|--:|
| amount | 8324 | 552 | 285 | **9161** |
| spec | 7770 | 599 | 730 | **9099** |
| unitPrice | 7892 | 360 | 434 | **8686** |
| manufacturingNo | 7517 | 329 | 96 | **7942** |
| quantity | 5533 | 835 | 690 | **7058** |
| itemName | 3817 | 41 | 2941 | **6799** |
| expiryDate | 6413 | 123 | 135 | **6671** |
| insuranceCode | 5269 | 368 | 73 | **5710** |
| itemNameMaster | 4113 | 721 | 0 | **4834** |
| supplyAmount | 291 | 155 | 329 | **775** |
| taxAmount | 337 | 94 | 340 | **771** |
| buyerCompany | 138 | 2 | 580 | **720** |
| totalAmount | 45 | 187 | 481 | **713** |
| supplierCompany | 32 | 7 | 618 | **657** |
| supplierBizNumber | 79 | 122 | 188 | **389** |
| buyerBizNumber | 18 | 96 | 153 | **267** |
| buyerAddress | 7 | 4 | 255 | **266** |
| discountAmount | 119 | 78 | 0 | **197** |
| issueDate | 0 | 0 | 178 | **178** |
| itemCode | 125 | 0 | 20 | **145** |
| supplierAddress | 1 | 6 | 38 | **45** |
| taxType | 27 | 0 | 0 | **27** |

## Ambiguous fuzzy-only evidence by column

| column | count |
|---|--:|
| itemName | 883 |
| itemNameMaster | 252 |
| insuranceCode | 98 |
| spec | 73 |
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
| itemNameMaster | 7356 |
| itemName | 3517 |
| quantity | 2296 |
| expiryDate | 2114 |
| taxType | 1977 |
| spec | 1961 |
| discountAmount | 1805 |
| supplierAddress | 1702 |
| buyerAddress | 1701 |
| manufacturingNo | 1412 |
| supplierCompany | 1282 |
| buyerCompany | 1267 |
| insuranceCode | 1158 |
| unitPrice | 1121 |
| amount | 802 |
| supplyAmount | 342 |
| taxAmount | 279 |
| totalAmount | 270 |
| supplierBizNumber | 105 |
| issueDate | 73 |
| buyerBizNumber | 51 |

## Preprocessing diagnosis  (telemetry 2002/2004 samples)

recognition rate = recognition defects / scored cells. Δ = vs baseline bucket (+ = that condition is costing accuracy → fix server-side preprocessing).

### Orientation

| condition | n | cellAcc | recognition% | Δ vs base |
|---|--:|--:|--:|--:|
| 270° 적용 | 105 | 5.0% | 52.2% | +14.1pp |
| 90° 적용 | 110 | 6.1% | 43.5% | +5.5pp |
| 180° 적용 | 47 | 18.6% | 39.2% | +1.1pp |
| 미적용(0°) | 1740 | 12.5% | 38.0% | — |

### Deskew

| condition | n | cellAcc | recognition% | Δ vs base |
|---|--:|--:|--:|--:|
| >2° | 24 | 3.7% | 46.1% | +7.5pp |
| ≤2° | 218 | 12.5% | 40.9% | +2.3pp |
| 미적용 | 1760 | 12.0% | 38.6% | — |

### Warp

| condition | n | cellAcc | recognition% | Δ vs base |
|---|--:|--:|--:|--:|
| 영역50–90% | 2 | 11.1% | 166.7% | +127.8pp |
| forcedWarpOnSkip | 2002 | 11.9% | 38.9% | +0.0pp |
| 영역≥90% | 2000 | 11.9% | 38.9% | — |
