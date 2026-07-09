# Parser-drop classification — 066_20260709_122046/thin

Defects scored (mismatch|ext_missing): **223013**  |  parser-drop (OCR read it, recoverable): **133945**  |  ambiguous_fuzzy (fuzzy-only, pending): **1269**  |  recognition (OCR-bound): **87799**
Parser-recoverable share of defects: **60.1%**

## Parser-drops by column × pattern — CLEAN originals  (n=0)

| column | drop | mislocate | wrongpick | total |
|---|--:|--:|--:|--:|

## Parser-drops by column × pattern — ANGLE variants  (n=133945)

| column | drop | mislocate | wrongpick | total |
|---|--:|--:|--:|--:|
| spec | 14045 | 2682 | 5095 | **21822** |
| unitPrice | 7999 | 4641 | 4246 | **16886** |
| manufacturingNo | 11762 | 2072 | 3047 | **16881** |
| insuranceCode | 10372 | 1430 | 2906 | **14708** |
| quantity | 6980 | 4148 | 2908 | **14036** |
| amount | 6669 | 1328 | 4976 | **12973** |
| expiryDate | 9154 | 1029 | 1466 | **11649** |
| itemName | 1953 | 1623 | 7234 | **10810** |
| taxAmount | 1018 | 320 | 860 | **2198** |
| itemNameMaster | 1085 | 568 | 527 | **2180** |
| supplyAmount | 823 | 519 | 789 | **2131** |
| totalAmount | 124 | 455 | 1441 | **2020** |
| supplierBizNumber | 207 | 331 | 625 | **1163** |
| supplierCompany | 66 | 136 | 810 | **1012** |
| buyerBizNumber | 58 | 309 | 427 | **794** |
| buyerAddress | 41 | 9 | 709 | **759** |
| discountAmount | 0 | 109 | 509 | **618** |
| issueDate | 0 | 0 | 504 | **504** |
| buyerCompany | 41 | 24 | 366 | **431** |
| itemCode | 109 | 12 | 113 | **234** |
| supplierAddress | 1 | 19 | 116 | **136** |

## Parser-drops by column × pattern — ALL  (n=133945)

| column | drop | mislocate | wrongpick | total |
|---|--:|--:|--:|--:|
| spec | 14045 | 2682 | 5095 | **21822** |
| unitPrice | 7999 | 4641 | 4246 | **16886** |
| manufacturingNo | 11762 | 2072 | 3047 | **16881** |
| insuranceCode | 10372 | 1430 | 2906 | **14708** |
| quantity | 6980 | 4148 | 2908 | **14036** |
| amount | 6669 | 1328 | 4976 | **12973** |
| expiryDate | 9154 | 1029 | 1466 | **11649** |
| itemName | 1953 | 1623 | 7234 | **10810** |
| taxAmount | 1018 | 320 | 860 | **2198** |
| itemNameMaster | 1085 | 568 | 527 | **2180** |
| supplyAmount | 823 | 519 | 789 | **2131** |
| totalAmount | 124 | 455 | 1441 | **2020** |
| supplierBizNumber | 207 | 331 | 625 | **1163** |
| supplierCompany | 66 | 136 | 810 | **1012** |
| buyerBizNumber | 58 | 309 | 427 | **794** |
| buyerAddress | 41 | 9 | 709 | **759** |
| discountAmount | 0 | 109 | 509 | **618** |
| issueDate | 0 | 0 | 504 | **504** |
| buyerCompany | 41 | 24 | 366 | **431** |
| itemCode | 109 | 12 | 113 | **234** |
| supplierAddress | 1 | 19 | 116 | **136** |

## Ambiguous fuzzy-only evidence by column

| column | count |
|---|--:|
| itemName | 558 |
| buyerCompany | 347 |
| supplierAddress | 105 |
| insuranceCode | 78 |
| itemNameMaster | 76 |
| spec | 47 |
| manufacturingNo | 35 |
| buyerAddress | 23 |

## Recognition (OCR-bound, NOT parser) by column

| column | count |
|---|--:|
| itemCode | 16037 |
| itemName | 12411 |
| itemNameMaster | 8344 |
| expiryDate | 6489 |
| spec | 6295 |
| quantity | 5119 |
| buyerAddress | 5108 |
| manufacturingNo | 5025 |
| buyerCompany | 3842 |
| insuranceCode | 3659 |
| supplierAddress | 3512 |
| unitPrice | 3177 |
| supplierCompany | 2354 |
| amount | 2313 |
| supplyAmount | 1024 |
| taxAmount | 865 |
| totalAmount | 818 |
| taxType | 792 |
| supplierBizNumber | 282 |
| issueDate | 176 |
| buyerBizNumber | 149 |
| discountAmount | 8 |

## Preprocessing diagnosis  (telemetry 5964/5964 samples)

recognition rate = recognition defects / scored cells. Δ = vs baseline bucket (+ = that condition is costing accuracy → fix server-side preprocessing).

### Orientation

| condition | n | cellAcc | recognition% | Δ vs base |
|---|--:|--:|--:|--:|
| 270° 적용 | 268 | 42.0% | 29.2% | +3.7pp |
| 180° 적용 | 120 | 44.7% | 25.8% | +0.3pp |
| 미적용(0°) | 5269 | 44.1% | 25.5% | — |
| 90° 적용 | 307 | 52.1% | 22.0% | -3.5pp |

### Deskew

| condition | n | cellAcc | recognition% | Δ vs base |
|---|--:|--:|--:|--:|
| >2° | 80 | 38.3% | 31.1% | +6.3pp |
| ≤2° | 672 | 39.5% | 28.8% | +4.0pp |
| 미적용 | 5212 | 45.3% | 24.8% | — |

### Warp

| condition | n | cellAcc | recognition% | Δ vs base |
|---|--:|--:|--:|--:|
| 영역50–90% | 1 | 44.4% | 33.3% | +8.0pp |
| forcedWarpOnSkip | 5964 | 44.6% | 25.4% | +0.0pp |
| 영역≥90% | 5963 | 44.6% | 25.4% | — |
