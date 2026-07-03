# Parser-drop classification — 062_20260703_095853\thin

Defects scored (mismatch|ext_missing): **101276**  |  parser-drop (OCR read it, recoverable): **59497**  |  ambiguous_fuzzy (fuzzy-only, pending): **872**  |  recognition (OCR-bound): **40907**
Parser-recoverable share of defects: **58.7%**

## Parser-drops by column × pattern — CLEAN originals  (n=0)

| column | drop | mislocate | wrongpick | total |
|---|--:|--:|--:|--:|

## Parser-drops by column × pattern — ANGLE variants  (n=59497)

| column | drop | mislocate | wrongpick | total |
|---|--:|--:|--:|--:|
| spec | 6305 | 761 | 1300 | **8366** |
| itemName | 2897 | 37 | 3843 | **6777** |
| manufacturingNo | 5412 | 513 | 806 | **6731** |
| unitPrice | 4595 | 918 | 832 | **6345** |
| quantity | 3598 | 940 | 1090 | **5628** |
| amount | 4253 | 379 | 976 | **5608** |
| insuranceCode | 4451 | 350 | 413 | **5214** |
| expiryDate | 4335 | 279 | 278 | **4892** |
| itemNameMaster | 4083 | 713 | 0 | **4796** |
| taxAmount | 342 | 107 | 314 | **763** |
| supplyAmount | 294 | 174 | 285 | **753** |
| buyerCompany | 143 | 2 | 574 | **719** |
| totalAmount | 35 | 163 | 511 | **709** |
| supplierCompany | 28 | 7 | 640 | **675** |
| supplierBizNumber | 66 | 110 | 211 | **387** |
| buyerBizNumber | 20 | 93 | 153 | **266** |
| buyerAddress | 11 | 4 | 251 | **266** |
| discountAmount | 0 | 43 | 155 | **198** |
| itemCode | 161 | 0 | 18 | **179** |
| issueDate | 0 | 0 | 178 | **178** |
| supplierAddress | 1 | 6 | 40 | **47** |

## Parser-drops by column × pattern — ALL  (n=59497)

| column | drop | mislocate | wrongpick | total |
|---|--:|--:|--:|--:|
| spec | 6305 | 761 | 1300 | **8366** |
| itemName | 2897 | 37 | 3843 | **6777** |
| manufacturingNo | 5412 | 513 | 806 | **6731** |
| unitPrice | 4595 | 918 | 832 | **6345** |
| quantity | 3598 | 940 | 1090 | **5628** |
| amount | 4253 | 379 | 976 | **5608** |
| insuranceCode | 4451 | 350 | 413 | **5214** |
| expiryDate | 4335 | 279 | 278 | **4892** |
| itemNameMaster | 4083 | 713 | 0 | **4796** |
| taxAmount | 342 | 107 | 314 | **763** |
| supplyAmount | 294 | 174 | 285 | **753** |
| buyerCompany | 143 | 2 | 574 | **719** |
| totalAmount | 35 | 163 | 511 | **709** |
| supplierCompany | 28 | 7 | 640 | **675** |
| supplierBizNumber | 66 | 110 | 211 | **387** |
| buyerBizNumber | 20 | 93 | 153 | **266** |
| buyerAddress | 11 | 4 | 251 | **266** |
| discountAmount | 0 | 43 | 155 | **198** |
| itemCode | 161 | 0 | 18 | **179** |
| issueDate | 0 | 0 | 178 | **178** |
| supplierAddress | 1 | 6 | 40 | **47** |

## Ambiguous fuzzy-only evidence by column

| column | count |
|---|--:|
| itemName | 576 |
| itemNameMaster | 127 |
| spec | 47 |
| insuranceCode | 47 |
| manufacturingNo | 31 |
| buyerCompany | 13 |
| buyerAddress | 12 |
| supplierAddress | 11 |
| supplierCompany | 7 |
| itemCode | 1 |

## Recognition (OCR-bound, NOT parser) by column

| column | count |
|---|--:|
| itemCode | 12257 |
| itemNameMaster | 7510 |
| itemName | 3788 |
| expiryDate | 2073 |
| quantity | 1959 |
| spec | 1918 |
| supplierAddress | 1699 |
| buyerAddress | 1694 |
| manufacturingNo | 1313 |
| supplierCompany | 1275 |
| buyerCompany | 1264 |
| insuranceCode | 1155 |
| unitPrice | 1003 |
| amount | 675 |
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
| 270° 적용 | 105 | 18.2% | 41.2% | +5.8pp |
| 180° 적용 | 47 | 25.0% | 35.9% | +0.5pp |
| 미적용(0°) | 1738 | 22.4% | 35.5% | — |
| 90° 적용 | 110 | 28.4% | 33.2% | -2.3pp |

### Deskew

| condition | n | cellAcc | recognition% | Δ vs base |
|---|--:|--:|--:|--:|
| ≤2° | 215 | 20.2% | 37.3% | +1.9pp |
| >2° | 24 | 18.1% | 35.4% | +0.1pp |
| 미적용 | 1761 | 23.1% | 35.3% | — |

### Warp

| condition | n | cellAcc | recognition% | Δ vs base |
|---|--:|--:|--:|--:|
| 영역50–90% | 1 | 11.1% | 66.7% | +31.1pp |
| forcedWarpOnSkip | 2000 | 22.7% | 35.5% | +0.0pp |
| 영역≥90% | 1999 | 22.7% | 35.5% | — |
