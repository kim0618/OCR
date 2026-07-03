# Fine-tune candidate ledger — 062_20260703_095853/thin

OCR-bound defects captured: **41867**  |  cropReady (confident misread localization): **35444**  |  lowConf (box present, ratio<0.55): **2224**  |  noBox (nothing localized): **4199**

_cropReady = OCR read a near-miss at a confidently-located box → (box, GT) is a rec fine-tune candidate once pixels are cut. lowConf = a box exists but match is weak (kept with its ratio for later re-thresholding). noBox = OCR produced nothing matchable._

## By class

| class | cropReady | notReady |
|---|--:|--:|
| recognition | 34076 | 6423 |
| ambiguous_fuzzy | 1368 | 0 |

## By column

| column | cropReady | notReady |
|---|--:|--:|
| itemCode | 11812 | 456 |
| itemNameMaster | 6950 | 638 |
| itemName | 4092 | 213 |
| quantity | 127 | 2073 |
| expiryDate | 2022 | 22 |
| spec | 1508 | 371 |
| supplierAddress | 1564 | 148 |
| buyerAddress | 1633 | 75 |
| manufacturingNo | 1304 | 60 |
| supplierCompany | 1072 | 212 |
| buyerCompany | 1109 | 170 |
| insuranceCode | 1146 | 17 |
| unitPrice | 226 | 793 |
| amount | 413 | 300 |
| supplyAmount | 157 | 182 |
| taxAmount | 30 | 246 |
| totalAmount | 58 | 208 |
| taxType | 18 | 225 |
| supplierBizNumber | 90 | 5 |
| issueDate | 66 | 3 |
| buyerBizNumber | 47 | 2 |
| discountAmount | 0 | 4 |
