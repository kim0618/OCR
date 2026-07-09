# Fine-tune candidate ledger — 066_20260709_122046/thin

OCR-bound defects captured: **89068**  |  cropReady (confident misread localization): **72872**  |  lowConf (box present, ratio<0.55): **5543**  |  noBox (nothing localized): **10653**

_cropReady = OCR read a near-miss at a confidently-located box → (box, GT) is a rec fine-tune candidate once pixels are cut. lowConf = a box exists but match is weak (kept with its ratio for later re-thresholding). noBox = OCR produced nothing matchable._

## By class

| class | cropReady | notReady |
|---|--:|--:|
| recognition | 71603 | 16196 |
| ambiguous_fuzzy | 1269 | 0 |

## By column

| column | cropReady | notReady |
|---|--:|--:|
| itemCode | 15080 | 957 |
| itemName | 12400 | 569 |
| itemNameMaster | 7276 | 1144 |
| expiryDate | 6444 | 45 |
| spec | 5133 | 1209 |
| buyerAddress | 4946 | 185 |
| quantity | 660 | 4459 |
| manufacturingNo | 4883 | 177 |
| buyerCompany | 3586 | 603 |
| insuranceCode | 3684 | 53 |
| supplierAddress | 3255 | 362 |
| unitPrice | 912 | 2265 |
| supplierCompany | 1872 | 482 |
| amount | 1446 | 867 |
| supplyAmount | 417 | 607 |
| taxAmount | 69 | 796 |
| totalAmount | 145 | 673 |
| taxType | 72 | 720 |
| supplierBizNumber | 270 | 12 |
| issueDate | 171 | 5 |
| buyerBizNumber | 146 | 3 |
| discountAmount | 5 | 3 |
