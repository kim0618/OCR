# Parser-drop classification — 066_20260709_122046\thin

Defects scored (mismatch|ext_missing): **223637**  |  parser-drop (OCR read it, recoverable): **134308**  |  ambiguous_fuzzy (fuzzy-only, pending): **1266**  |  recognition (OCR-bound): **88063**
Parser-recoverable share of defects: **60.1%**

## Parser-drops by column × pattern — CLEAN originals  (n=0)

| column | drop | mislocate | wrongpick | total |
|---|--:|--:|--:|--:|

## Parser-drops by column × pattern — ANGLE variants  (n=134308)

| column | drop | mislocate | wrongpick | total |
|---|--:|--:|--:|--:|
| spec | 14205 | 2714 | 5175 | **22094** |
| unitPrice | 8102 | 4732 | 4301 | **17135** |
| manufacturingNo | 11914 | 2087 | 3105 | **17106** |
| insuranceCode | 10555 | 1448 | 2936 | **14939** |
| quantity | 7061 | 4201 | 2949 | **14211** |
| amount | 6725 | 1336 | 5081 | **13142** |
| expiryDate | 9302 | 1039 | 1471 | **11812** |
| itemName | 1972 | 1645 | 7283 | **10900** |
| taxAmount | 1023 | 325 | 868 | **2216** |
| itemNameMaster | 995 | 576 | 614 | **2185** |
| supplyAmount | 829 | 522 | 797 | **2148** |
| totalAmount | 124 | 457 | 1451 | **2032** |
| supplierCompany | 9 | 70 | 693 | **772** |
| buyerAddress | 41 | 7 | 719 | **767** |
| buyerBizNumber | 43 | 161 | 511 | **715** |
| discountAmount | 0 | 111 | 512 | **623** |
| issueDate | 0 | 0 | 504 | **504** |
| buyerCompany | 42 | 8 | 385 | **435** |
| itemCode | 108 | 13 | 121 | **242** |
| supplierBizNumber | 18 | 18 | 184 | **220** |
| supplierAddress | 2 | 15 | 93 | **110** |

## Parser-drops by column × pattern — ALL  (n=134308)

| column | drop | mislocate | wrongpick | total |
|---|--:|--:|--:|--:|
| spec | 14205 | 2714 | 5175 | **22094** |
| unitPrice | 8102 | 4732 | 4301 | **17135** |
| manufacturingNo | 11914 | 2087 | 3105 | **17106** |
| insuranceCode | 10555 | 1448 | 2936 | **14939** |
| quantity | 7061 | 4201 | 2949 | **14211** |
| amount | 6725 | 1336 | 5081 | **13142** |
| expiryDate | 9302 | 1039 | 1471 | **11812** |
| itemName | 1972 | 1645 | 7283 | **10900** |
| taxAmount | 1023 | 325 | 868 | **2216** |
| itemNameMaster | 995 | 576 | 614 | **2185** |
| supplyAmount | 829 | 522 | 797 | **2148** |
| totalAmount | 124 | 457 | 1451 | **2032** |
| supplierCompany | 9 | 70 | 693 | **772** |
| buyerAddress | 41 | 7 | 719 | **767** |
| buyerBizNumber | 43 | 161 | 511 | **715** |
| discountAmount | 0 | 111 | 512 | **623** |
| issueDate | 0 | 0 | 504 | **504** |
| buyerCompany | 42 | 8 | 385 | **435** |
| itemCode | 108 | 13 | 121 | **242** |
| supplierBizNumber | 18 | 18 | 184 | **220** |
| supplierAddress | 2 | 15 | 93 | **110** |

## Ambiguous fuzzy-only evidence by column

| column | count |
|---|--:|
| itemName | 567 |
| buyerCompany | 347 |
| supplierAddress | 88 |
| insuranceCode | 80 |
| itemNameMaster | 77 |
| spec | 47 |
| manufacturingNo | 35 |
| buyerAddress | 25 |

## Recognition (OCR-bound, NOT parser) by column

| column | count |
|---|--:|
| itemCode | 16097 |
| itemName | 12562 |
| itemNameMaster | 8299 |
| expiryDate | 6567 |
| spec | 6352 |
| quantity | 5197 |
| buyerAddress | 5147 |
| manufacturingNo | 5131 |
| buyerCompany | 3859 |
| insuranceCode | 3711 |
| supplierAddress | 3227 |
| unitPrice | 3209 |
| amount | 2338 |
| supplierCompany | 2190 |
| supplyAmount | 1040 |
| taxAmount | 882 |
| totalAmount | 831 |
| taxType | 809 |
| supplierBizNumber | 277 |
| issueDate | 176 |
| buyerBizNumber | 154 |
| discountAmount | 8 |

## Preprocessing diagnosis  (telemetry 6013/6013 samples)

recognition rate = recognition defects / scored cells. Δ = vs baseline bucket (+ = that condition is costing accuracy → fix server-side preprocessing).

### Orientation

| condition | n | cellAcc | recognition% | Δ vs base |
|---|--:|--:|--:|--:|
| 270° 적용 | 275 | 41.2% | 28.9% | +3.6pp |
| 180° 적용 | 120 | 44.8% | 25.6% | +0.4pp |
| 미적용(0°) | 5309 | 44.2% | 25.2% | — |
| 90° 적용 | 309 | 52.2% | 21.7% | -3.5pp |

### Deskew

| condition | n | cellAcc | recognition% | Δ vs base |
|---|--:|--:|--:|--:|
| >2° | 80 | 38.4% | 30.8% | +6.3pp |
| ≤2° | 682 | 39.4% | 28.6% | +4.1pp |
| 미적용 | 5251 | 45.4% | 24.6% | — |

### Warp

| condition | n | cellAcc | recognition% | Δ vs base |
|---|--:|--:|--:|--:|
| 영역50–90% | 1 | 44.4% | 33.3% | +8.2pp |
| forcedWarpOnSkip | 6013 | 44.6% | 25.1% | +0.0pp |
| 영역≥90% | 6012 | 44.6% | 25.1% | — |
