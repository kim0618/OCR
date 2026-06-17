# Parser-drop classification — 053_20260617_142725\study

Defects scored (mismatch|ext_missing): **339**  |  parser-drop (OCR read it, recoverable): **189**  |  recognition (OCR-bound): **150**
Parser-recoverable share of defects: **55.8%**

## Parser-drops by column × pattern — CLEAN originals  (n=29)

| column | drop | mislocate | wrongpick | total |
|---|--:|--:|--:|--:|
| itemName | 0 | 1 | 6 | **7** |
| lotNo | 2 | 2 | 1 | **5** |
| quantity | 1 | 3 | 0 | **4** |
| expiryDate | 0 | 3 | 1 | **4** |
| buyerRepresentative | 0 | 0 | 2 | **2** |
| unitPrice | 0 | 1 | 1 | **2** |
| spec | 0 | 0 | 1 | **1** |
| buyerAddress | 0 | 0 | 1 | **1** |
| supplierCompany | 0 | 0 | 1 | **1** |
| supplierRepresentative | 0 | 0 | 1 | **1** |
| amount | 0 | 1 | 0 | **1** |

## Parser-drops by column × pattern — ANGLE variants  (n=160)

| column | drop | mislocate | wrongpick | total |
|---|--:|--:|--:|--:|
| itemName | 2 | 8 | 19 | **29** |
| lotNo | 23 | 1 | 1 | **25** |
| quantity | 8 | 8 | 8 | **24** |
| spec | 0 | 10 | 5 | **15** |
| unitPrice | 7 | 5 | 0 | **12** |
| amount | 3 | 4 | 3 | **10** |
| productCode | 10 | 0 | 0 | **10** |
| expiryDate | 5 | 4 | 1 | **10** |
| taxAmount | 3 | 1 | 1 | **5** |
| supplyAmount | 2 | 1 | 1 | **4** |
| buyerAddress | 0 | 0 | 3 | **3** |
| issueDate | 0 | 0 | 3 | **3** |
| buyerRepresentative | 1 | 1 | 1 | **3** |
| supplierRepresentative | 0 | 0 | 2 | **2** |
| totalAmount | 1 | 0 | 1 | **2** |
| cumulativeAmount | 0 | 1 | 0 | **1** |
| buyerCompany | 0 | 0 | 1 | **1** |
| totalQuantity | 0 | 0 | 1 | **1** |

## Parser-drops by column × pattern — ALL  (n=189)

| column | drop | mislocate | wrongpick | total |
|---|--:|--:|--:|--:|
| itemName | 2 | 9 | 25 | **36** |
| lotNo | 25 | 3 | 2 | **30** |
| quantity | 9 | 11 | 8 | **28** |
| spec | 0 | 10 | 6 | **16** |
| unitPrice | 7 | 6 | 1 | **14** |
| expiryDate | 5 | 7 | 2 | **14** |
| amount | 3 | 5 | 3 | **11** |
| productCode | 10 | 0 | 0 | **10** |
| buyerRepresentative | 1 | 1 | 3 | **5** |
| taxAmount | 3 | 1 | 1 | **5** |
| buyerAddress | 0 | 0 | 4 | **4** |
| supplyAmount | 2 | 1 | 1 | **4** |
| issueDate | 0 | 0 | 3 | **3** |
| supplierRepresentative | 0 | 0 | 3 | **3** |
| totalAmount | 1 | 0 | 1 | **2** |
| cumulativeAmount | 0 | 1 | 0 | **1** |
| buyerCompany | 0 | 0 | 1 | **1** |
| supplierCompany | 0 | 0 | 1 | **1** |
| totalQuantity | 0 | 0 | 1 | **1** |

## Recognition (OCR-bound, NOT parser) by column

| column | count |
|---|--:|
| itemName | 55 |
| spec | 16 |
| supplierAddress | 13 |
| supplierRepresentative | 12 |
| buyerAddress | 12 |
| productCode | 9 |
| quantity | 8 |
| buyerCompany | 7 |
| lotNo | 5 |
| supplierBizNumber | 4 |
| supplierCompany | 3 |
| totalAmount | 3 |
| buyerRepresentative | 2 |
| buyerBizNumber | 1 |
