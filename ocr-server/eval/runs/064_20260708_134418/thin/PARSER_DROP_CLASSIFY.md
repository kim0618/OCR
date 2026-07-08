# Parser-drop classification — 064_20260708_134418/thin

Defects scored (mismatch|ext_missing): **103860**  |  parser-drop (OCR read it, recoverable): **66794**  |  ambiguous_fuzzy (fuzzy-only, pending): **990**  |  recognition (OCR-bound): **36076**
Parser-recoverable share of defects: **64.3%**

## Parser-drops by column × pattern — CLEAN originals  (n=0)

| column | drop | mislocate | wrongpick | total |
|---|--:|--:|--:|--:|

## Parser-drops by column × pattern — ANGLE variants  (n=66794)

| column | drop | mislocate | wrongpick | total |
|---|--:|--:|--:|--:|
| amount | 10159 | 489 | 75 | **10723** |
| unitPrice | 8548 | 486 | 519 | **9553** |
| spec | 7825 | 542 | 148 | **8515** |
| manufacturingNo | 7409 | 579 | 65 | **8053** |
| quantity | 5082 | 520 | 1768 | **7370** |
| expiryDate | 5345 | 273 | 1128 | **6746** |
| insuranceCode | 5247 | 362 | 118 | **5727** |
| itemName | 2000 | 287 | 1085 | **3372** |
| itemNameMaster | 1465 | 98 | 155 | **1718** |
| taxAmount | 507 | 127 | 291 | **925** |
| supplyAmount | 439 | 87 | 367 | **893** |
| totalAmount | 120 | 202 | 570 | **892** |
| supplierCompany | 17 | 7 | 422 | **446** |
| issueDate | 15 | 0 | 425 | **440** |
| buyerCompany | 99 | 35 | 281 | **415** |
| supplierBizNumber | 37 | 156 | 153 | **346** |
| buyerBizNumber | 11 | 111 | 109 | **231** |
| discountAmount | 0 | 45 | 153 | **198** |
| itemCode | 58 | 3 | 56 | **117** |
| buyerAddress | 4 | 0 | 89 | **93** |
| supplierAddress | 2 | 5 | 14 | **21** |

## Parser-drops by column × pattern — ALL  (n=66794)

| column | drop | mislocate | wrongpick | total |
|---|--:|--:|--:|--:|
| amount | 10159 | 489 | 75 | **10723** |
| unitPrice | 8548 | 486 | 519 | **9553** |
| spec | 7825 | 542 | 148 | **8515** |
| manufacturingNo | 7409 | 579 | 65 | **8053** |
| quantity | 5082 | 520 | 1768 | **7370** |
| expiryDate | 5345 | 273 | 1128 | **6746** |
| insuranceCode | 5247 | 362 | 118 | **5727** |
| itemName | 2000 | 287 | 1085 | **3372** |
| itemNameMaster | 1465 | 98 | 155 | **1718** |
| taxAmount | 507 | 127 | 291 | **925** |
| supplyAmount | 439 | 87 | 367 | **893** |
| totalAmount | 120 | 202 | 570 | **892** |
| supplierCompany | 17 | 7 | 422 | **446** |
| issueDate | 15 | 0 | 425 | **440** |
| buyerCompany | 99 | 35 | 281 | **415** |
| supplierBizNumber | 37 | 156 | 153 | **346** |
| buyerBizNumber | 11 | 111 | 109 | **231** |
| discountAmount | 0 | 45 | 153 | **198** |
| itemCode | 58 | 3 | 56 | **117** |
| buyerAddress | 4 | 0 | 89 | **93** |
| supplierAddress | 2 | 5 | 14 | **21** |

## Ambiguous fuzzy-only evidence by column

| column | count |
|---|--:|
| itemName | 610 |
| insuranceCode | 98 |
| itemNameMaster | 64 |
| manufacturingNo | 62 |
| spec | 60 |
| buyerCompany | 50 |
| supplierAddress | 32 |
| buyerAddress | 10 |
| itemCode | 2 |
| supplierCompany | 2 |

## Recognition (OCR-bound, NOT parser) by column

| column | count |
|---|--:|
| itemCode | 7369 |
| quantity | 4009 |
| itemName | 3636 |
| itemNameMaster | 3298 |
| spec | 2842 |
| expiryDate | 2297 |
| buyerAddress | 1886 |
| manufacturingNo | 1875 |
| supplierAddress | 1346 |
| unitPrice | 1297 |
| buyerCompany | 1277 |
| insuranceCode | 1251 |
| amount | 1064 |
| supplierCompany | 867 |
| supplierBizNumber | 373 |
| supplyAmount | 332 |
| totalAmount | 270 |
| taxAmount | 266 |
| taxType | 244 |
| issueDate | 208 |
| buyerBizNumber | 64 |
| discountAmount | 5 |

## Preprocessing diagnosis  (telemetry 1999/2002 samples)

recognition rate = recognition defects / scored cells. Δ = vs baseline bucket (+ = that condition is costing accuracy → fix server-side preprocessing).

### Orientation

| condition | n | cellAcc | recognition% | Δ vs base |
|---|--:|--:|--:|--:|
| 270° 적용 | 104 | 15.7% | 37.2% | +6.4pp |
| 90° 적용 | 124 | 24.4% | 32.8% | +1.9pp |
| 180° 적용 | 59 | 21.6% | 31.3% | +0.5pp |
| 미적용(0°) | 1712 | 20.2% | 30.8% | — |

### Deskew

| condition | n | cellAcc | recognition% | Δ vs base |
|---|--:|--:|--:|--:|
| >2° | 24 | 21.4% | 34.3% | +3.2pp |
| ≤2° | 217 | 20.2% | 31.8% | +0.7pp |
| 미적용 | 1758 | 20.4% | 31.1% | — |

### Warp

| condition | n | cellAcc | recognition% | Δ vs base |
|---|--:|--:|--:|--:|
| 영역50–90% | 1 | 0.0% | 66.7% | +35.5pp |
| forcedWarpOnSkip | 1999 | 20.4% | 31.2% | +0.0pp |
| 영역≥90% | 1998 | 20.4% | 31.2% | — |
