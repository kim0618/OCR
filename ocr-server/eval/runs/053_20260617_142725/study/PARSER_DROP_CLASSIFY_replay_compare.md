# Parser-drop classification — 053_20260617_142725\study

Defects scored (mismatch|ext_missing): **323**  |  parser-drop (OCR read it, recoverable): **174**  |  recognition (OCR-bound): **149**
Parser-recoverable share of defects: **53.9%**

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

## Parser-drops by column × pattern — ANGLE variants  (n=145)

| column | drop | mislocate | wrongpick | total |
|---|--:|--:|--:|--:|
| itemName | 0 | 8 | 20 | **28** |
| lotNo | 23 | 1 | 1 | **25** |
| quantity | 8 | 6 | 7 | **21** |
| spec | 0 | 10 | 5 | **15** |
| expiryDate | 5 | 4 | 1 | **10** |
| amount | 2 | 4 | 3 | **9** |
| unitPrice | 5 | 3 | 0 | **8** |
| productCode | 7 | 0 | 0 | **7** |
| taxAmount | 3 | 0 | 1 | **4** |
| buyerAddress | 0 | 0 | 3 | **3** |
| issueDate | 0 | 0 | 3 | **3** |
| supplyAmount | 2 | 1 | 0 | **3** |
| buyerRepresentative | 1 | 1 | 1 | **3** |
| supplierRepresentative | 0 | 0 | 2 | **2** |
| cumulativeAmount | 0 | 1 | 0 | **1** |
| buyerCompany | 0 | 0 | 1 | **1** |
| totalAmount | 1 | 0 | 0 | **1** |
| totalQuantity | 0 | 0 | 1 | **1** |

## Parser-drops by column × pattern — ALL  (n=174)

| column | drop | mislocate | wrongpick | total |
|---|--:|--:|--:|--:|
| itemName | 0 | 9 | 26 | **35** |
| lotNo | 25 | 3 | 2 | **30** |
| quantity | 9 | 9 | 7 | **25** |
| spec | 0 | 10 | 6 | **16** |
| expiryDate | 5 | 7 | 2 | **14** |
| amount | 2 | 5 | 3 | **10** |
| unitPrice | 5 | 4 | 1 | **10** |
| productCode | 7 | 0 | 0 | **7** |
| buyerRepresentative | 1 | 1 | 3 | **5** |
| buyerAddress | 0 | 0 | 4 | **4** |
| taxAmount | 3 | 0 | 1 | **4** |
| issueDate | 0 | 0 | 3 | **3** |
| supplierRepresentative | 0 | 0 | 3 | **3** |
| supplyAmount | 2 | 1 | 0 | **3** |
| cumulativeAmount | 0 | 1 | 0 | **1** |
| buyerCompany | 0 | 0 | 1 | **1** |
| totalAmount | 1 | 0 | 0 | **1** |
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
| productCode | 8 |
| quantity | 8 |
| buyerCompany | 7 |
| lotNo | 5 |
| supplierBizNumber | 4 |
| supplierCompany | 3 |
| totalAmount | 3 |
| buyerRepresentative | 2 |
| buyerBizNumber | 1 |
