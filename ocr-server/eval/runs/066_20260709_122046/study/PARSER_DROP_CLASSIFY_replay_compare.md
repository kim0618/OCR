# Parser-drop classification — 066_20260709_122046\study

Defects scored (mismatch|ext_missing): **163**  |  parser-drop (OCR read it, recoverable): **11**  |  ambiguous_fuzzy (fuzzy-only, pending): **0**  |  recognition (OCR-bound): **152**
Parser-recoverable share of defects: **6.7%**

Evaluation scope: **run_meta.ran 24 sources**; out-of-scope compare files excluded: **0**

## Raw itemName × master itemNameMaster transitions

| transition | rows |
|---|--:|
| rawWrong_masterCorrect | **0** |
| rawWrong_masterWrongOrMissing | **0** |
| rawCorrect_masterCorrect | **0** |
| rawCorrect_masterWrong | **0** |
| rawCorrect_masterMissing | **0** |

Regression gates use the persisted row identities, not fixed bin counts: a successful raw fix may legitimately move a protected row between bins.

## Parser-drops by column × pattern — CLEAN originals  (n=2)

| column | drop | mislocate | wrongpick | total |
|---|--:|--:|--:|--:|
| supplierAddress | 0 | 0 | 1 | **1** |
| itemName | 0 | 0 | 1 | **1** |

## Parser-drops by column × pattern — ANGLE variants  (n=9)

| column | drop | mislocate | wrongpick | total |
|---|--:|--:|--:|--:|
| supplierAddress | 0 | 0 | 3 | **3** |
| buyerRepresentative | 0 | 1 | 1 | **2** |
| productCode | 1 | 0 | 0 | **1** |
| quantity | 0 | 0 | 1 | **1** |
| unitPrice | 1 | 0 | 0 | **1** |
| amount | 0 | 1 | 0 | **1** |

## Parser-drops by column × pattern — ALL  (n=11)

| column | drop | mislocate | wrongpick | total |
|---|--:|--:|--:|--:|
| supplierAddress | 0 | 0 | 4 | **4** |
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
| itemName | 76 |
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
| 90° 적용 | 4 | 90.8% | 12.0% | -2.1pp |

### Deskew

| condition | n | cellAcc | recognition% | Δ vs base |
|---|--:|--:|--:|--:|
| guard-revert | 1 | 60.0% | 100.0% | +86.1pp |
| 미적용 | 23 | 90.1% | 13.9% | — |

### Warp

| condition | n | cellAcc | recognition% | Δ vs base |
|---|--:|--:|--:|--:|
| 영역50–90% | 17 | 89.2% | 14.9% | +2.3pp |
| forcedWarpOnSkip | 12 | 91.5% | 14.8% | +2.2pp |
| 영역≥90% | 7 | 92.3% | 12.5% | — |
