# Parser-drop classification — 056_20260702_103410/study

Defects scored (mismatch|ext_missing): **165**  |  parser-drop (OCR read it, recoverable): **3**  |  ambiguous_fuzzy (fuzzy-only, pending): **0**  |  recognition (OCR-bound): **162**
Parser-recoverable share of defects: **1.8%**

## Parser-drops by column × pattern — CLEAN originals  (n=1)

| column | drop | mislocate | wrongpick | total |
|---|--:|--:|--:|--:|
| itemName | 0 | 0 | 1 | **1** |

## Parser-drops by column × pattern — ANGLE variants  (n=2)

| column | drop | mislocate | wrongpick | total |
|---|--:|--:|--:|--:|
| buyerRepresentative | 1 | 1 | 0 | **2** |

## Parser-drops by column × pattern — ALL  (n=3)

| column | drop | mislocate | wrongpick | total |
|---|--:|--:|--:|--:|
| buyerRepresentative | 1 | 1 | 0 | **2** |
| itemName | 0 | 0 | 1 | **1** |

## Ambiguous fuzzy-only evidence by column

| column | count |
|---|--:|

## Recognition (OCR-bound, NOT parser) by column

| column | count |
|---|--:|
| itemName | 77 |
| spec | 18 |
| buyerAddress | 15 |
| supplierAddress | 13 |
| supplierRepresentative | 12 |
| buyerCompany | 8 |
| supplierBizNumber | 4 |
| lotNo | 4 |
| supplierCompany | 3 |
| quantity | 3 |
| buyerRepresentative | 2 |
| productCode | 2 |
| buyerBizNumber | 1 |

## Preprocessing diagnosis  (telemetry 24/24 samples)

recognition rate = recognition defects / scored cells. Δ = vs baseline bucket (+ = that condition is costing accuracy → fix server-side preprocessing).

### Orientation

| condition | n | cellAcc | recognition% | Δ vs base |
|---|--:|--:|--:|--:|
| 270° 적용 | 3 | 82.1% | 48.7% | +34.7pp |
| 180° 적용 | 6 | 89.8% | 15.3% | +1.2pp |
| 미적용(0°) | 11 | 90.7% | 14.1% | — |
| 90° 적용 | 4 | 90.5% | 12.7% | -1.4pp |

### Deskew

| condition | n | cellAcc | recognition% | Δ vs base |
|---|--:|--:|--:|--:|
| guard-revert | 1 | 60.0% | 100.0% | +85.2pp |
| 미적용 | 23 | 90.3% | 14.8% | — |

### Warp

| condition | n | cellAcc | recognition% | Δ vs base |
|---|--:|--:|--:|--:|
| forcedWarpOnSkip | 12 | 91.2% | 17.5% | +4.6pp |
| 영역50–90% | 17 | 89.4% | 16.0% | +3.1pp |
| 영역≥90% | 7 | 92.3% | 12.9% | — |
