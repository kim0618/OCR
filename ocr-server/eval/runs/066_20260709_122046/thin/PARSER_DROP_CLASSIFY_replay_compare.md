# Parser-drop classification — 066_20260709_122046\thin

Defects scored (mismatch|ext_missing): **184772**  |  parser-drop (OCR read it, recoverable): **104080**  |  ambiguous_fuzzy (fuzzy-only, pending): **1003**  |  recognition (OCR-bound): **79689**
Parser-recoverable share of defects: **56.3%**

Evaluation scope: **run_meta.ran 5964 sources**; out-of-scope compare files excluded: **49**

## Raw itemName × master itemNameMaster transitions

| transition | rows |
|---|--:|
| rawWrong_masterCorrect | **14351** |
| rawWrong_masterWrongOrMissing | **8888** |
| rawCorrect_masterCorrect | **13176** |
| rawCorrect_masterWrong | **892** |
| rawCorrect_masterMissing | **39** |

Regression gates use the persisted row identities, not fixed bin counts: a successful raw fix may legitimately move a protected row between bins.

Clean/angle split: **unavailable for this run**. The legacy six-file study filename list is not applied to thin data.

## Parser-drops by column × pattern — ALL  (n=104080)

| column | drop | mislocate | wrongpick | total |
|---|--:|--:|--:|--:|
| manufacturingNo | 12326 | 1407 | 3330 | **17063** |
| spec | 5566 | 3748 | 6225 | **15539** |
| unitPrice | 4881 | 2475 | 4541 | **11897** |
| expiryDate | 9051 | 1088 | 1415 | **11554** |
| itemName | 1614 | 1766 | 6806 | **10186** |
| amount | 4059 | 1111 | 4339 | **9509** |
| quantity | 3761 | 3169 | 2506 | **9436** |
| insuranceCode | 1941 | 1089 | 5596 | **8626** |
| itemNameMaster | 780 | 570 | 557 | **1907** |
| totalAmount | 96 | 376 | 1102 | **1574** |
| taxAmount | 580 | 203 | 710 | **1493** |
| supplyAmount | 457 | 352 | 629 | **1438** |
| buyerAddress | 41 | 8 | 710 | **759** |
| supplierCompany | 8 | 69 | 628 | **705** |
| discountAmount | 0 | 85 | 533 | **618** |
| issueDate | 0 | 0 | 504 | **504** |
| buyerCompany | 42 | 6 | 383 | **431** |
| buyerBizNumber | 38 | 157 | 212 | **407** |
| supplierBizNumber | 54 | 28 | 105 | **187** |
| itemCode | 69 | 19 | 49 | **137** |
| supplierAddress | 2 | 15 | 93 | **110** |

## Ambiguous fuzzy-only evidence by column

| column | count |
|---|--:|
| itemName | 400 |
| buyerCompany | 347 |
| supplierAddress | 99 |
| itemNameMaster | 59 |
| spec | 27 |
| insuranceCode | 25 |
| manufacturingNo | 23 |
| buyerAddress | 23 |

## Recognition (OCR-bound, NOT parser) by column

| column | count |
|---|--:|
| itemName | 12667 |
| itemCode | 11090 |
| itemNameMaster | 7853 |
| expiryDate | 6520 |
| spec | 6315 |
| buyerAddress | 5108 |
| manufacturingNo | 4824 |
| buyerCompany | 3842 |
| quantity | 3831 |
| supplierAddress | 3162 |
| unitPrice | 3117 |
| insuranceCode | 2867 |
| amount | 2236 |
| supplierCompany | 2151 |
| supplyAmount | 1023 |
| taxAmount | 864 |
| totalAmount | 818 |
| taxType | 792 |
| supplierBizNumber | 276 |
| issueDate | 176 |
| buyerBizNumber | 149 |
| discountAmount | 8 |

## Preprocessing diagnosis  (telemetry 5964/5964 samples)

recognition rate = recognition defects / scored cells. Δ = vs baseline bucket (+ = that condition is costing accuracy → fix server-side preprocessing).

### Orientation

| condition | n | cellAcc | recognition% | Δ vs base |
|---|--:|--:|--:|--:|
| 270° 적용 | 268 | 52.3% | 26.9% | +3.8pp |
| 180° 적용 | 120 | 54.6% | 23.2% | +0.1pp |
| 미적용(0°) | 5269 | 54.1% | 23.1% | — |
| 90° 적용 | 307 | 60.1% | 20.2% | -2.9pp |

### Deskew

| condition | n | cellAcc | recognition% | Δ vs base |
|---|--:|--:|--:|--:|
| >2° | 80 | 47.4% | 29.6% | +7.2pp |
| ≤2° | 672 | 50.3% | 26.6% | +4.1pp |
| 미적용 | 5212 | 55.1% | 22.5% | — |

### Warp

| condition | n | cellAcc | recognition% | Δ vs base |
|---|--:|--:|--:|--:|
| 영역50–90% | 1 | 66.7% | 44.4% | +21.4pp |
| forcedWarpOnSkip | 5964 | 54.4% | 23.0% | +0.0pp |
| 영역≥90% | 5963 | 54.4% | 23.0% | — |
