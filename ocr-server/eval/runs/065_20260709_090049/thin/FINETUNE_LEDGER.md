# Fine-tune candidate ledger — 065_20260709_090049/thin

OCR-bound defects captured: **30338**  |  cropReady (confident misread localization): **24922**  |  lowConf (box present, ratio<0.55): **1846**  |  noBox (nothing localized): **3570**

_cropReady = OCR read a near-miss at a confidently-located box → (box, GT) is a rec fine-tune candidate once pixels are cut. lowConf = a box exists but match is weak (kept with its ratio for later re-thresholding). noBox = OCR produced nothing matchable._

## By class

| class | cropReady | notReady |
|---|--:|--:|
| recognition | 24474 | 5416 |
| ambiguous_fuzzy | 448 | 0 |

## By column

| column | cropReady | notReady |
|---|--:|--:|
| itemCode | 5262 | 314 |
| itemName | 4131 | 204 |
| itemNameMaster | 2661 | 418 |
| expiryDate | 2210 | 13 |
| spec | 1739 | 359 |
| quantity | 237 | 1545 |
| buyerAddress | 1635 | 73 |
| manufacturingNo | 1494 | 51 |
| buyerCompany | 1203 | 191 |
| insuranceCode | 1306 | 15 |
| supplierAddress | 1122 | 123 |
| unitPrice | 305 | 783 |
| supplierCompany | 637 | 176 |
| amount | 515 | 292 |
| supplyAmount | 157 | 180 |
| taxAmount | 30 | 244 |
| totalAmount | 57 | 206 |
| taxType | 18 | 223 |
| supplierBizNumber | 90 | 3 |
| issueDate | 66 | 1 |
| buyerBizNumber | 47 | 0 |
| discountAmount | 0 | 2 |
