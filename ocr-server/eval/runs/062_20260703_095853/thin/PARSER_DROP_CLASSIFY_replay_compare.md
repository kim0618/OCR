# Parser-drop classification — 062_20260703_095853\thin

Defects scored (mismatch|ext_missing): **88433**  |  parser-drop (OCR read it, recoverable): **53648**  |  ambiguous_fuzzy (fuzzy-only, pending): **712**  |  recognition (OCR-bound): **34073**
Parser-recoverable share of defects: **60.7%**

## Parser-drops by column × pattern — CLEAN originals  (n=0)

| column | drop | mislocate | wrongpick | total |
|---|--:|--:|--:|--:|

## Parser-drops by column × pattern — ANGLE variants  (n=53648)

| column | drop | mislocate | wrongpick | total |
|---|--:|--:|--:|--:|
| spec | 6057 | 723 | 1379 | **8159** |
| manufacturingNo | 5036 | 550 | 865 | **6451** |
| unitPrice | 4220 | 1069 | 880 | **6169** |
| quantity | 3343 | 1056 | 1093 | **5492** |
| amount | 3874 | 396 | 1079 | **5349** |
| itemName | 2474 | 330 | 2347 | **5151** |
| insuranceCode | 4213 | 437 | 479 | **5129** |
| expiryDate | 4001 | 291 | 319 | **4611** |
| itemNameMaster | 1748 | 112 | 215 | **2075** |
| taxAmount | 342 | 107 | 314 | **763** |
| supplyAmount | 294 | 174 | 285 | **753** |
| buyerCompany | 143 | 2 | 574 | **719** |
| totalAmount | 35 | 163 | 511 | **709** |
| supplierCompany | 28 | 7 | 640 | **675** |
| supplierBizNumber | 66 | 110 | 211 | **387** |
| buyerBizNumber | 20 | 93 | 153 | **266** |
| buyerAddress | 11 | 4 | 251 | **266** |
| discountAmount | 0 | 43 | 155 | **198** |
| issueDate | 0 | 0 | 178 | **178** |
| itemCode | 62 | 0 | 39 | **101** |
| supplierAddress | 1 | 6 | 40 | **47** |

## Parser-drops by column × pattern — ALL  (n=53648)

| column | drop | mislocate | wrongpick | total |
|---|--:|--:|--:|--:|
| spec | 6057 | 723 | 1379 | **8159** |
| manufacturingNo | 5036 | 550 | 865 | **6451** |
| unitPrice | 4220 | 1069 | 880 | **6169** |
| quantity | 3343 | 1056 | 1093 | **5492** |
| amount | 3874 | 396 | 1079 | **5349** |
| itemName | 2474 | 330 | 2347 | **5151** |
| insuranceCode | 4213 | 437 | 479 | **5129** |
| expiryDate | 4001 | 291 | 319 | **4611** |
| itemNameMaster | 1748 | 112 | 215 | **2075** |
| taxAmount | 342 | 107 | 314 | **763** |
| supplyAmount | 294 | 174 | 285 | **753** |
| buyerCompany | 143 | 2 | 574 | **719** |
| totalAmount | 35 | 163 | 511 | **709** |
| supplierCompany | 28 | 7 | 640 | **675** |
| supplierBizNumber | 66 | 110 | 211 | **387** |
| buyerBizNumber | 20 | 93 | 153 | **266** |
| buyerAddress | 11 | 4 | 251 | **266** |
| discountAmount | 0 | 43 | 155 | **198** |
| issueDate | 0 | 0 | 178 | **178** |
| itemCode | 62 | 0 | 39 | **101** |
| supplierAddress | 1 | 6 | 40 | **47** |

## Ambiguous fuzzy-only evidence by column

| column | count |
|---|--:|
| itemName | 487 |
| itemNameMaster | 82 |
| insuranceCode | 39 |
| spec | 37 |
| manufacturingNo | 24 |
| buyerCompany | 13 |
| buyerAddress | 12 |
| supplierAddress | 11 |
| supplierCompany | 7 |

## Recognition (OCR-bound, NOT parser) by column

| column | count |
|---|--:|
| itemCode | 7897 |
| itemNameMaster | 4496 |
| itemName | 3830 |
| expiryDate | 2144 |
| spec | 1994 |
| quantity | 1961 |
| supplierAddress | 1699 |
| buyerAddress | 1694 |
| manufacturingNo | 1471 |
| supplierCompany | 1275 |
| buyerCompany | 1264 |
| insuranceCode | 1214 |
| unitPrice | 1052 |
| amount | 758 |
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
| 270° 적용 | 105 | 29.8% | 36.2% | +6.6pp |
| 미적용(0°) | 1738 | 33.2% | 29.6% | — |
| 180° 적용 | 47 | 39.3% | 29.2% | -0.4pp |
| 90° 적용 | 110 | 41.9% | 26.1% | -3.5pp |

### Deskew

| condition | n | cellAcc | recognition% | Δ vs base |
|---|--:|--:|--:|--:|
| ≤2° | 215 | 30.6% | 33.1% | +4.0pp |
| >2° | 24 | 26.9% | 31.8% | +2.7pp |
| 미적용 | 1761 | 34.3% | 29.1% | — |

### Warp

| condition | n | cellAcc | recognition% | Δ vs base |
|---|--:|--:|--:|--:|
| 영역50–90% | 1 | 11.1% | 66.7% | +37.1pp |
| forcedWarpOnSkip | 2000 | 33.8% | 29.6% | +0.0pp |
| 영역≥90% | 1999 | 33.8% | 29.6% | — |
