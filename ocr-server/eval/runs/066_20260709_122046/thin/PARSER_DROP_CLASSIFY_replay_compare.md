# Parser-drop classification — 066_20260709_122046\thin

Defects scored (mismatch|ext_missing): **182324**  |  parser-drop (OCR read it, recoverable): **102653**  |  ambiguous_fuzzy (fuzzy-only, pending): **973**  |  recognition (OCR-bound): **78698**
Parser-recoverable share of defects: **56.3%**

Evaluation scope: **run_meta.ran 5964 sources**; out-of-scope compare files excluded: **49**

## Raw itemName × master itemNameMaster transitions

| transition | rows |
|---|--:|
| rawWrong_masterCorrect | **13804** |
| rawWrong_masterWrongOrMissing | **8250** |
| rawCorrect_masterCorrect | **14667** |
| rawCorrect_masterWrong | **587** |
| rawCorrect_masterMissing | **38** |

Regression gates use the persisted row identities, not fixed bin counts: a successful raw fix may legitimately move a protected row between bins.

Clean/angle split: **unavailable for this run**. The legacy six-file study filename list is not applied to thin data.

## Parser-drops by column × pattern — ALL  (n=102653)

| column | drop | mislocate | wrongpick | total |
|---|--:|--:|--:|--:|
| manufacturingNo | 12240 | 1418 | 3187 | **16845** |
| spec | 5485 | 3666 | 6291 | **15442** |
| unitPrice | 4837 | 2461 | 4591 | **11889** |
| expiryDate | 8920 | 1074 | 1433 | **11427** |
| amount | 4011 | 1117 | 4365 | **9493** |
| quantity | 3742 | 3171 | 2520 | **9433** |
| itemName | 1508 | 1950 | 5565 | **9023** |
| insuranceCode | 1874 | 1105 | 5602 | **8581** |
| itemNameMaster | 955 | 663 | 541 | **2159** |
| totalAmount | 96 | 377 | 1101 | **1574** |
| taxAmount | 580 | 203 | 710 | **1493** |
| supplyAmount | 457 | 353 | 628 | **1438** |
| buyerAddress | 41 | 8 | 710 | **759** |
| supplierCompany | 8 | 69 | 628 | **705** |
| discountAmount | 0 | 85 | 533 | **618** |
| issueDate | 0 | 0 | 504 | **504** |
| buyerCompany | 42 | 6 | 383 | **431** |
| buyerBizNumber | 38 | 157 | 212 | **407** |
| supplierBizNumber | 54 | 28 | 105 | **187** |
| itemCode | 65 | 39 | 31 | **135** |
| supplierAddress | 2 | 15 | 93 | **110** |

## Ambiguous fuzzy-only evidence by column

| column | count |
|---|--:|
| itemName | 386 |
| buyerCompany | 347 |
| supplierAddress | 99 |
| itemNameMaster | 48 |
| insuranceCode | 25 |
| spec | 23 |
| buyerAddress | 23 |
| manufacturingNo | 22 |

## Recognition (OCR-bound, NOT parser) by column

| column | count |
|---|--:|
| itemName | 12659 |
| itemCode | 11004 |
| itemNameMaster | 6668 |
| expiryDate | 6557 |
| spec | 6347 |
| buyerAddress | 5108 |
| manufacturingNo | 4907 |
| quantity | 3848 |
| buyerCompany | 3842 |
| unitPrice | 3163 |
| supplierAddress | 3162 |
| insuranceCode | 2887 |
| amount | 2289 |
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
| 270° 적용 | 268 | 53.1% | 26.6% | +3.8pp |
| 180° 적용 | 120 | 55.1% | 23.1% | +0.3pp |
| 미적용(0°) | 5269 | 54.8% | 22.8% | — |
| 90° 적용 | 307 | 60.5% | 20.0% | -2.8pp |

### Deskew

| condition | n | cellAcc | recognition% | Δ vs base |
|---|--:|--:|--:|--:|
| >2° | 80 | 48.1% | 29.2% | +7.1pp |
| ≤2° | 672 | 50.7% | 26.3% | +4.2pp |
| 미적용 | 5212 | 55.8% | 22.2% | — |

### Warp

| condition | n | cellAcc | recognition% | Δ vs base |
|---|--:|--:|--:|--:|
| 영역50–90% | 1 | 66.7% | 44.4% | +21.7pp |
| forcedWarpOnSkip | 5964 | 55.1% | 22.7% | +0.0pp |
| 영역≥90% | 5963 | 55.1% | 22.7% | — |
