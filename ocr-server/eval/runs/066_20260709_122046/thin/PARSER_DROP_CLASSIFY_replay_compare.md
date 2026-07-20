# Parser-drop classification — 066_20260709_122046\thin

Defects scored (mismatch|ext_missing): **201757**  |  parser-drop (OCR read it, recoverable): **116584**  |  ambiguous_fuzzy (fuzzy-only, pending): **1041**  |  recognition (OCR-bound): **84132**
Parser-recoverable share of defects: **57.8%**

Evaluation scope: **run_meta.ran 5964 sources**; out-of-scope compare files excluded: **49**

## Raw itemName × master itemNameMaster transitions

| transition | rows |
|---|--:|
| rawWrong_masterCorrect | **14321** |
| rawWrong_masterWrongOrMissing | **8918** |
| rawCorrect_masterCorrect | **13140** |
| rawCorrect_masterWrong | **928** |
| rawCorrect_masterMissing | **39** |

Regression gates use the persisted row identities, not fixed bin counts: a successful raw fix may legitimately move a protected row between bins.

Clean/angle split: **unavailable for this run**. The legacy six-file study filename list is not applied to thin data.

## Parser-drops by column × pattern — ALL  (n=116584)

| column | drop | mislocate | wrongpick | total |
|---|--:|--:|--:|--:|
| spec | 13668 | 2694 | 5222 | **21584** |
| manufacturingNo | 11779 | 2234 | 3079 | **17092** |
| insuranceCode | 10458 | 1350 | 2956 | **14764** |
| unitPrice | 4908 | 2477 | 4564 | **11949** |
| expiryDate | 9181 | 1006 | 1433 | **11620** |
| itemName | 1618 | 1756 | 6829 | **10203** |
| amount | 4072 | 1120 | 4371 | **9563** |
| quantity | 3774 | 3141 | 2536 | **9451** |
| itemNameMaster | 781 | 573 | 575 | **1929** |
| totalAmount | 96 | 376 | 1102 | **1574** |
| taxAmount | 581 | 202 | 710 | **1493** |
| supplyAmount | 457 | 352 | 629 | **1438** |
| buyerAddress | 41 | 8 | 710 | **759** |
| supplierCompany | 8 | 69 | 628 | **705** |
| discountAmount | 0 | 85 | 533 | **618** |
| issueDate | 0 | 0 | 504 | **504** |
| buyerCompany | 42 | 6 | 383 | **431** |
| buyerBizNumber | 38 | 157 | 212 | **407** |
| itemCode | 71 | 17 | 115 | **203** |
| supplierBizNumber | 54 | 28 | 105 | **187** |
| supplierAddress | 2 | 15 | 93 | **110** |

## Ambiguous fuzzy-only evidence by column

| column | count |
|---|--:|
| itemName | 400 |
| buyerCompany | 347 |
| supplierAddress | 99 |
| itemNameMaster | 59 |
| insuranceCode | 55 |
| spec | 31 |
| manufacturingNo | 27 |
| buyerAddress | 23 |

## Recognition (OCR-bound, NOT parser) by column

| column | count |
|---|--:|
| itemCode | 14828 |
| itemName | 12650 |
| itemNameMaster | 7897 |
| expiryDate | 6454 |
| spec | 6400 |
| buyerAddress | 5108 |
| manufacturingNo | 4791 |
| buyerCompany | 3842 |
| quantity | 3816 |
| insuranceCode | 3680 |
| supplierAddress | 3162 |
| unitPrice | 3065 |
| amount | 2182 |
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
| 270° 적용 | 268 | 47.4% | 28.0% | +3.6pp |
| 180° 적용 | 120 | 50.7% | 24.5% | +0.1pp |
| 미적용(0°) | 5269 | 49.1% | 24.4% | — |
| 90° 적용 | 307 | 55.5% | 21.1% | -3.3pp |

### Deskew

| condition | n | cellAcc | recognition% | Δ vs base |
|---|--:|--:|--:|--:|
| >2° | 80 | 42.2% | 30.9% | +7.1pp |
| ≤2° | 672 | 45.3% | 27.7% | +3.9pp |
| 미적용 | 5212 | 50.2% | 23.8% | — |

### Warp

| condition | n | cellAcc | recognition% | Δ vs base |
|---|--:|--:|--:|--:|
| 영역50–90% | 1 | 55.6% | 33.3% | +9.0pp |
| forcedWarpOnSkip | 5964 | 49.5% | 24.3% | +0.0pp |
| 영역≥90% | 5963 | 49.5% | 24.3% | — |
