# Parser-drop classification — 066_20260709_122046\thin

Defects scored (mismatch|ext_missing): **204657**  |  parser-drop (OCR read it, recoverable): **118744**  |  ambiguous_fuzzy (fuzzy-only, pending): **1063**  |  recognition (OCR-bound): **84850**
Parser-recoverable share of defects: **58.0%**

Evaluation scope: **run_meta.ran 5964 sources**; out-of-scope compare files excluded: **49**

## Raw itemName × master itemNameMaster transitions

| transition | rows |
|---|--:|
| rawWrong_masterCorrect | **14234** |
| rawWrong_masterWrongOrMissing | **9420** |
| rawCorrect_masterCorrect | **12748** |
| rawCorrect_masterWrong | **904** |
| rawCorrect_masterMissing | **40** |

Regression gates use the persisted row identities, not fixed bin counts: a successful raw fix may legitimately move a protected row between bins.

Clean/angle split: **unavailable for this run**. The legacy six-file study filename list is not applied to thin data.

## Parser-drops by column × pattern — ALL  (n=118744)

| column | drop | mislocate | wrongpick | total |
|---|--:|--:|--:|--:|
| spec | 13713 | 2690 | 5197 | **21600** |
| manufacturingNo | 11811 | 2225 | 3068 | **17104** |
| insuranceCode | 10396 | 1441 | 2932 | **14769** |
| unitPrice | 4985 | 2465 | 4539 | **11989** |
| expiryDate | 9239 | 1006 | 1427 | **11672** |
| itemName | 1759 | 1726 | 7120 | **10605** |
| amount | 4147 | 1081 | 4343 | **9571** |
| quantity | 3807 | 3149 | 2518 | **9474** |
| itemNameMaster | 902 | 555 | 624 | **2081** |
| taxAmount | 889 | 316 | 854 | **2059** |
| supplyAmount | 687 | 507 | 766 | **1960** |
| totalAmount | 118 | 489 | 1307 | **1914** |
| buyerAddress | 41 | 8 | 710 | **759** |
| supplierCompany | 8 | 69 | 628 | **705** |
| discountAmount | 0 | 81 | 537 | **618** |
| issueDate | 0 | 0 | 504 | **504** |
| buyerCompany | 42 | 6 | 383 | **431** |
| buyerBizNumber | 38 | 157 | 212 | **407** |
| itemCode | 106 | 9 | 110 | **225** |
| supplierBizNumber | 54 | 28 | 105 | **187** |
| supplierAddress | 2 | 15 | 93 | **110** |

## Ambiguous fuzzy-only evidence by column

| column | count |
|---|--:|
| itemName | 416 |
| buyerCompany | 347 |
| supplierAddress | 99 |
| itemNameMaster | 62 |
| insuranceCode | 56 |
| spec | 32 |
| manufacturingNo | 28 |
| buyerAddress | 23 |

## Recognition (OCR-bound, NOT parser) by column

| column | count |
|---|--:|
| itemCode | 15247 |
| itemName | 12647 |
| itemNameMaster | 8221 |
| expiryDate | 6452 |
| spec | 6396 |
| buyerAddress | 5108 |
| manufacturingNo | 4784 |
| buyerCompany | 3842 |
| quantity | 3815 |
| insuranceCode | 3678 |
| supplierAddress | 3162 |
| unitPrice | 3064 |
| amount | 2177 |
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
| 270° 적용 | 268 | 46.7% | 28.3% | +3.7pp |
| 180° 적용 | 120 | 49.8% | 24.9% | +0.3pp |
| 미적용(0°) | 5269 | 48.7% | 24.6% | — |
| 90° 적용 | 307 | 55.4% | 21.2% | -3.4pp |

### Deskew

| condition | n | cellAcc | recognition% | Δ vs base |
|---|--:|--:|--:|--:|
| >2° | 80 | 42.0% | 31.0% | +7.1pp |
| ≤2° | 672 | 44.8% | 28.0% | +4.0pp |
| 미적용 | 5212 | 49.8% | 24.0% | — |

### Warp

| condition | n | cellAcc | recognition% | Δ vs base |
|---|--:|--:|--:|--:|
| 영역50–90% | 1 | 55.6% | 33.3% | +8.8pp |
| forcedWarpOnSkip | 5964 | 49.1% | 24.5% | +0.0pp |
| 영역≥90% | 5963 | 49.1% | 24.5% | — |
