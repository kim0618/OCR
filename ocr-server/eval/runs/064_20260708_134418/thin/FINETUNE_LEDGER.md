# Fine-tune candidate ledger — 064_20260708_134418/thin

OCR-bound defects captured: **37066**  |  cropReady (confident misread localization): **30081**  |  lowConf (box present, ratio<0.55): **2110**  |  noBox (nothing localized): **4875**

_cropReady = OCR read a near-miss at a confidently-located box → (box, GT) is a rec fine-tune candidate once pixels are cut. lowConf = a box exists but match is weak (kept with its ratio for later re-thresholding). noBox = OCR produced nothing matchable._

## By class

| class | cropReady | notReady |
|---|--:|--:|
| recognition | 29091 | 6985 |
| ambiguous_fuzzy | 990 | 0 |

## By column

| column | cropReady | notReady |
|---|--:|--:|
| itemCode | 6892 | 479 |
| itemName | 4154 | 92 |
| quantity | 1291 | 2718 |
| itemNameMaster | 2846 | 516 |
| spec | 2273 | 629 |
| expiryDate | 2281 | 16 |
| manufacturingNo | 1850 | 87 |
| buyerAddress | 1818 | 78 |
| supplierAddress | 1232 | 146 |
| insuranceCode | 1317 | 32 |
| buyerCompany | 1241 | 86 |
| unitPrice | 503 | 794 |
| amount | 762 | 302 |
| supplierCompany | 740 | 129 |
| supplierBizNumber | 360 | 13 |
| supplyAmount | 148 | 184 |
| totalAmount | 58 | 212 |
| taxAmount | 21 | 245 |
| taxType | 26 | 218 |
| issueDate | 205 | 3 |
| buyerBizNumber | 62 | 2 |
| discountAmount | 1 | 4 |
