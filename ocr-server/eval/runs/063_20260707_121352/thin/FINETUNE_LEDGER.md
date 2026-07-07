# Fine-tune candidate ledger — 063_20260707_121352/thin

OCR-bound defects captured: **33317**  |  cropReady (confident misread localization): **27681**  |  lowConf (box present, ratio<0.55): **1944**  |  noBox (nothing localized): **3692**

_cropReady = OCR read a near-miss at a confidently-located box → (box, GT) is a rec fine-tune candidate once pixels are cut. lowConf = a box exists but match is weak (kept with its ratio for later re-thresholding). noBox = OCR produced nothing matchable._

## By class

| class | cropReady | notReady |
|---|--:|--:|
| recognition | 27003 | 5636 |
| ambiguous_fuzzy | 678 | 0 |

## By column

| column | cropReady | notReady |
|---|--:|--:|
| itemCode | 7096 | 337 |
| itemNameMaster | 3865 | 493 |
| itemName | 4136 | 204 |
| expiryDate | 2153 | 13 |
| spec | 1695 | 359 |
| quantity | 212 | 1669 |
| buyerAddress | 1635 | 73 |
| manufacturingNo | 1449 | 51 |
| buyerCompany | 1203 | 191 |
| insuranceCode | 1265 | 13 |
| supplierAddress | 1122 | 123 |
| unitPrice | 275 | 783 |
| supplierCompany | 637 | 176 |
| amount | 473 | 292 |
| supplyAmount | 157 | 180 |
| taxAmount | 30 | 244 |
| totalAmount | 57 | 206 |
| taxType | 18 | 223 |
| supplierBizNumber | 90 | 3 |
| issueDate | 66 | 1 |
| buyerBizNumber | 47 | 0 |
| discountAmount | 0 | 2 |
