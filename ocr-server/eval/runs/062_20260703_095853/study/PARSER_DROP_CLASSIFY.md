# Parser-drop classification — 062_20260703_095853/study

Defects scored (mismatch|ext_missing): **166**  |  parser-drop (OCR read it, recoverable): **9**  |  ambiguous_fuzzy (fuzzy-only, pending): **0**  |  recognition (OCR-bound): **157**
Parser-recoverable share of defects: **5.4%**

## Parser-drops by column × pattern — CLEAN originals  (n=1)

| column | drop | mislocate | wrongpick | total |
|---|--:|--:|--:|--:|
| itemName | 0 | 0 | 1 | **1** |

## Parser-drops by column × pattern — ANGLE variants  (n=8)

| column | drop | mislocate | wrongpick | total |
|---|--:|--:|--:|--:|
| buyerRepresentative | 0 | 1 | 1 | **2** |
| unitPrice | 2 | 0 | 0 | **2** |
| amount | 0 | 2 | 0 | **2** |
| productCode | 1 | 0 | 0 | **1** |
| quantity | 0 | 0 | 1 | **1** |

## Parser-drops by column × pattern — ALL  (n=9)

| column | drop | mislocate | wrongpick | total |
|---|--:|--:|--:|--:|
| buyerRepresentative | 0 | 1 | 1 | **2** |
| unitPrice | 2 | 0 | 0 | **2** |
| amount | 0 | 2 | 0 | **2** |
| itemName | 0 | 0 | 1 | **1** |
| productCode | 1 | 0 | 0 | **1** |
| quantity | 0 | 0 | 1 | **1** |

## Ambiguous fuzzy-only evidence by column

| column | count |
|---|--:|

## Recognition (OCR-bound, NOT parser) by column

| column | count |
|---|--:|
| itemName | 77 |
| spec | 18 |
| buyerAddress | 14 |
| supplierAddress | 13 |
| supplierRepresentative | 11 |
| buyerCompany | 8 |
| lotNo | 5 |
| supplierBizNumber | 4 |
| supplierCompany | 3 |
| productCode | 2 |
| buyerBizNumber | 1 |
| quantity | 1 |

## Preprocessing diagnosis  (telemetry 24/24 samples)

recognition rate = recognition defects / scored cells. Δ = vs baseline bucket (+ = that condition is costing accuracy → fix server-side preprocessing).

### Orientation

| condition | n | cellAcc | recognition% | Δ vs base |
|---|--:|--:|--:|--:|
| 270° 적용 | 3 | 82.1% | 35.9% | +21.8pp |
| 180° 적용 | 6 | 89.8% | 15.3% | +1.2pp |
| 미적용(0°) | 11 | 89.7% | 14.1% | — |
| 90° 적용 | 4 | 90.5% | 12.7% | -1.4pp |

### Deskew

| condition | n | cellAcc | recognition% | Δ vs base |
|---|--:|--:|--:|--:|
| guard-revert | 1 | 60.0% | 100.0% | +85.6pp |
| 미적용 | 23 | 89.8% | 14.4% | — |

### Warp

| condition | n | cellAcc | recognition% | Δ vs base |
|---|--:|--:|--:|--:|
| forcedWarpOnSkip | 12 | 91.2% | 16.2% | +3.2pp |
| 영역50–90% | 17 | 88.8% | 15.4% | +2.5pp |
| 영역≥90% | 7 | 92.3% | 12.9% | — |
