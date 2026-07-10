# Parser-drop classification — 065_20260709_090049\study

Defects scored (mismatch|ext_missing): **168**  |  parser-drop (OCR read it, recoverable): **15**  |  ambiguous_fuzzy (fuzzy-only, pending): **0**  |  recognition (OCR-bound): **153**
Parser-recoverable share of defects: **8.9%**

## Parser-drops by column × pattern — CLEAN originals  (n=3)

| column | drop | mislocate | wrongpick | total |
|---|--:|--:|--:|--:|
| supplierAddress | 0 | 0 | 1 | **1** |
| itemName | 0 | 0 | 1 | **1** |
| supplierCompany | 0 | 0 | 1 | **1** |

## Parser-drops by column × pattern — ANGLE variants  (n=12)

| column | drop | mislocate | wrongpick | total |
|---|--:|--:|--:|--:|
| supplierAddress | 0 | 0 | 3 | **3** |
| supplierCompany | 0 | 0 | 3 | **3** |
| buyerRepresentative | 0 | 1 | 1 | **2** |
| productCode | 1 | 0 | 0 | **1** |
| quantity | 0 | 0 | 1 | **1** |
| unitPrice | 1 | 0 | 0 | **1** |
| amount | 0 | 1 | 0 | **1** |

## Parser-drops by column × pattern — ALL  (n=15)

| column | drop | mislocate | wrongpick | total |
|---|--:|--:|--:|--:|
| supplierAddress | 0 | 0 | 4 | **4** |
| supplierCompany | 0 | 0 | 4 | **4** |
| buyerRepresentative | 0 | 1 | 1 | **2** |
| itemName | 0 | 0 | 1 | **1** |
| productCode | 1 | 0 | 0 | **1** |
| quantity | 0 | 0 | 1 | **1** |
| unitPrice | 1 | 0 | 0 | **1** |
| amount | 0 | 1 | 0 | **1** |

## Ambiguous fuzzy-only evidence by column

| column | count |
|---|--:|

## Recognition (OCR-bound, NOT parser) by column

| column | count |
|---|--:|
| itemName | 77 |
| spec | 18 |
| buyerAddress | 14 |
| supplierAddress | 12 |
| supplierRepresentative | 11 |
| buyerCompany | 8 |
| lotNo | 5 |
| supplierBizNumber | 4 |
| productCode | 2 |
| buyerBizNumber | 1 |
| quantity | 1 |

## Preprocessing diagnosis  (telemetry 24/24 samples)

recognition rate = recognition defects / scored cells. Δ = vs baseline bucket (+ = that condition is costing accuracy → fix server-side preprocessing).

### Orientation

| condition | n | cellAcc | recognition% | Δ vs base |
|---|--:|--:|--:|--:|
| 270° 적용 | 3 | 82.1% | 33.3% | +19.3pp |
| 180° 적용 | 6 | 89.8% | 14.4% | +0.3pp |
| 미적용(0°) | 11 | 90.1% | 14.1% | — |
| 90° 적용 | 4 | 90.5% | 12.3% | -1.7pp |

### Deskew

| condition | n | cellAcc | recognition% | Δ vs base |
|---|--:|--:|--:|--:|
| guard-revert | 1 | 60.0% | 100.0% | +86.0pp |
| 미적용 | 23 | 90.0% | 14.0% | — |

### Warp

| condition | n | cellAcc | recognition% | Δ vs base |
|---|--:|--:|--:|--:|
| forcedWarpOnSkip | 12 | 91.2% | 15.1% | +2.5pp |
| 영역50–90% | 17 | 89.0% | 15.0% | +2.5pp |
| 영역≥90% | 7 | 92.3% | 12.5% | — |
