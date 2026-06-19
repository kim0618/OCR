# Parser-drop classification — 053_20260617_142725\study

Defects scored (mismatch|ext_missing): **216**  |  parser-drop (OCR read it, recoverable): **77**  |  recognition (OCR-bound): **139**
Parser-recoverable share of defects: **35.6%**

## Parser-drops by column × pattern — CLEAN originals  (n=10)

| column | drop | mislocate | wrongpick | total |
|---|--:|--:|--:|--:|
| itemName | 0 | 1 | 5 | **6** |
| buyerRepresentative | 1 | 0 | 1 | **2** |
| buyerAddress | 0 | 0 | 1 | **1** |
| supplierCompany | 0 | 0 | 1 | **1** |

## Parser-drops by column × pattern — ANGLE variants  (n=67)

| column | drop | mislocate | wrongpick | total |
|---|--:|--:|--:|--:|
| itemName | 0 | 7 | 17 | **24** |
| spec | 0 | 8 | 3 | **11** |
| productCode | 4 | 0 | 0 | **4** |
| lotNo | 4 | 0 | 0 | **4** |
| expiryDate | 4 | 0 | 0 | **4** |
| buyerAddress | 0 | 0 | 3 | **3** |
| issueDate | 0 | 0 | 3 | **3** |
| taxAmount | 0 | 0 | 3 | **3** |
| buyerRepresentative | 1 | 1 | 1 | **3** |
| quantity | 3 | 0 | 0 | **3** |
| cumulativeAmount | 0 | 1 | 0 | **1** |
| buyerCompany | 0 | 0 | 1 | **1** |
| supplyAmount | 0 | 1 | 0 | **1** |
| supplierRepresentative | 0 | 0 | 1 | **1** |
| totalAmount | 0 | 0 | 1 | **1** |

## Parser-drops by column × pattern — ALL  (n=77)

| column | drop | mislocate | wrongpick | total |
|---|--:|--:|--:|--:|
| itemName | 0 | 8 | 22 | **30** |
| spec | 0 | 8 | 3 | **11** |
| buyerRepresentative | 2 | 1 | 2 | **5** |
| buyerAddress | 0 | 0 | 4 | **4** |
| productCode | 4 | 0 | 0 | **4** |
| lotNo | 4 | 0 | 0 | **4** |
| expiryDate | 4 | 0 | 0 | **4** |
| issueDate | 0 | 0 | 3 | **3** |
| taxAmount | 0 | 0 | 3 | **3** |
| quantity | 3 | 0 | 0 | **3** |
| cumulativeAmount | 0 | 1 | 0 | **1** |
| buyerCompany | 0 | 0 | 1 | **1** |
| supplyAmount | 0 | 1 | 0 | **1** |
| supplierRepresentative | 0 | 0 | 1 | **1** |
| totalAmount | 0 | 0 | 1 | **1** |
| supplierCompany | 0 | 0 | 1 | **1** |

## Recognition (OCR-bound, NOT parser) by column

| column | count |
|---|--:|
| itemName | 55 |
| spec | 16 |
| supplierAddress | 13 |
| supplierRepresentative | 12 |
| buyerAddress | 12 |
| buyerCompany | 7 |
| supplierBizNumber | 4 |
| lotNo | 4 |
| productCode | 4 |
| supplierCompany | 3 |
| totalAmount | 3 |
| quantity | 3 |
| buyerRepresentative | 2 |
| buyerBizNumber | 1 |
