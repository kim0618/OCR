# Parser-drop classification — 064_20260708_134418/study

Defects scored (mismatch|ext_missing): **715**  |  parser-drop (OCR read it, recoverable): **405**  |  ambiguous_fuzzy (fuzzy-only, pending): **3**  |  recognition (OCR-bound): **307**
Parser-recoverable share of defects: **56.6%**

## Parser-drops by column × pattern — CLEAN originals  (n=70)

| column | drop | mislocate | wrongpick | total |
|---|--:|--:|--:|--:|
| spec | 1 | 5 | 10 | **16** |
| itemName | 0 | 3 | 9 | **12** |
| quantity | 4 | 6 | 1 | **11** |
| buyerRepresentative | 0 | 0 | 4 | **4** |
| productCode | 2 | 1 | 1 | **4** |
| totalAmount | 0 | 0 | 3 | **3** |
| expiryDate | 1 | 1 | 1 | **3** |
| lotNo | 3 | 0 | 0 | **3** |
| issueDate | 0 | 0 | 2 | **2** |
| unitPrice | 1 | 1 | 0 | **2** |
| amount | 1 | 1 | 0 | **2** |
| supplierRepresentative | 0 | 0 | 2 | **2** |
| supplierAddress | 0 | 0 | 1 | **1** |
| cumulativeAmount | 1 | 0 | 0 | **1** |
| taxAmount | 1 | 0 | 0 | **1** |
| buyerBizNumber | 0 | 1 | 0 | **1** |
| buyerCompany | 0 | 1 | 0 | **1** |
| totalQuantity | 1 | 0 | 0 | **1** |

## Parser-drops by column × pattern — ANGLE variants  (n=335)

| column | drop | mislocate | wrongpick | total |
|---|--:|--:|--:|--:|
| quantity | 10 | 28 | 14 | **52** |
| spec | 5 | 23 | 22 | **50** |
| itemName | 1 | 14 | 35 | **50** |
| unitPrice | 5 | 23 | 0 | **28** |
| expiryDate | 7 | 19 | 2 | **28** |
| amount | 5 | 22 | 0 | **27** |
| productCode | 9 | 7 | 3 | **19** |
| lotNo | 12 | 1 | 1 | **14** |
| buyerRepresentative | 1 | 1 | 10 | **12** |
| taxAmount | 6 | 0 | 2 | **8** |
| totalAmount | 0 | 2 | 5 | **7** |
| supplierRepresentative | 0 | 0 | 6 | **6** |
| issueDate | 1 | 0 | 4 | **5** |
| supplyAmount | 2 | 0 | 3 | **5** |
| buyerBizNumber | 0 | 5 | 0 | **5** |
| supplierBizNumber | 0 | 1 | 3 | **4** |
| supplierAddress | 0 | 0 | 3 | **3** |
| cumulativeAmount | 3 | 0 | 0 | **3** |
| supplierCompany | 0 | 0 | 3 | **3** |
| totalQuantity | 1 | 2 | 0 | **3** |
| buyerCompany | 0 | 2 | 0 | **2** |
| buyerAddress | 0 | 0 | 1 | **1** |

## Parser-drops by column × pattern — ALL  (n=405)

| column | drop | mislocate | wrongpick | total |
|---|--:|--:|--:|--:|
| spec | 6 | 28 | 32 | **66** |
| quantity | 14 | 34 | 15 | **63** |
| itemName | 1 | 17 | 44 | **62** |
| expiryDate | 8 | 20 | 3 | **31** |
| unitPrice | 6 | 24 | 0 | **30** |
| amount | 6 | 23 | 0 | **29** |
| productCode | 11 | 8 | 4 | **23** |
| lotNo | 15 | 1 | 1 | **17** |
| buyerRepresentative | 1 | 1 | 14 | **16** |
| totalAmount | 0 | 2 | 8 | **10** |
| taxAmount | 7 | 0 | 2 | **9** |
| supplierRepresentative | 0 | 0 | 8 | **8** |
| issueDate | 1 | 0 | 6 | **7** |
| buyerBizNumber | 0 | 6 | 0 | **6** |
| supplyAmount | 2 | 0 | 3 | **5** |
| supplierBizNumber | 0 | 1 | 3 | **4** |
| supplierAddress | 0 | 0 | 4 | **4** |
| cumulativeAmount | 4 | 0 | 0 | **4** |
| totalQuantity | 2 | 2 | 0 | **4** |
| supplierCompany | 0 | 0 | 3 | **3** |
| buyerCompany | 0 | 3 | 0 | **3** |
| buyerAddress | 0 | 0 | 1 | **1** |

## Ambiguous fuzzy-only evidence by column

| column | count |
|---|--:|
| lotNo | 3 |

## Recognition (OCR-bound, NOT parser) by column

| column | count |
|---|--:|
| lotNo | 89 |
| itemName | 74 |
| quantity | 32 |
| spec | 25 |
| buyerAddress | 22 |
| productCode | 14 |
| supplierRepresentative | 12 |
| supplierAddress | 12 |
| buyerCompany | 11 |
| supplierCompany | 4 |
| supplierBizNumber | 4 |
| expiryDate | 2 |
| buyerRepresentative | 2 |
| totalAmount | 2 |
| issueDate | 1 |
| buyerBizNumber | 1 |

## Preprocessing diagnosis  (telemetry 24/24 samples)

recognition rate = recognition defects / scored cells. Δ = vs baseline bucket (+ = that condition is costing accuracy → fix server-side preprocessing).

### Orientation

| condition | n | cellAcc | recognition% | Δ vs base |
|---|--:|--:|--:|--:|
| 270° 적용 | 3 | 0.0% | 43.6% | +14.0pp |
| 180° 적용 | 6 | 24.1% | 31.4% | +1.8pp |
| 미적용(0°) | 11 | 52.9% | 29.6% | — |
| 90° 적용 | 4 | 65.8% | 23.2% | -6.3pp |

### Deskew

| condition | n | cellAcc | recognition% | Δ vs base |
|---|--:|--:|--:|--:|
| guard-revert | 1 | 0.0% | 80.0% | +51.4pp |
| 미적용 | 23 | 47.6% | 28.6% | — |

### Warp

| condition | n | cellAcc | recognition% | Δ vs base |
|---|--:|--:|--:|--:|
| forcedWarpOnSkip | 12 | 48.8% | 29.9% | +0.7pp |
| 영역≥90% | 7 | 56.5% | 29.2% | — |
| 영역50–90% | 17 | 44.3% | 28.8% | -0.4pp |
