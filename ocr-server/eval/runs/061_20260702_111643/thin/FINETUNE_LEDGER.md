# Fine-tune candidate ledger — 061_20260702_111643/thin

OCR-bound defects captured: **46247**  |  cropReady (confident misread localization): **36628**  |  lowConf (box present, ratio<0.55): **3622**  |  noBox (nothing localized): **5997**

_cropReady = OCR read a near-miss at a confidently-located box → (box, GT) is a rec fine-tune candidate once pixels are cut. lowConf = a box exists but match is weak (kept with its ratio for later re-thresholding). noBox = OCR produced nothing matchable._

## By class

| class | cropReady | notReady |
|---|--:|--:|
| recognition | 35241 | 9619 |
| ambiguous_fuzzy | 1387 | 0 |

## By column

| column | cropReady | notReady |
|---|--:|--:|
| itemCode | 11834 | 437 |
| itemNameMaster | 6979 | 629 |
| itemName | 4199 | 201 |
| quantity | 162 | 2134 |
| expiryDate | 2103 | 11 |
| spec | 1661 | 373 |
| taxType | 364 | 1613 |
| discountAmount | 1 | 1804 |
| supplierAddress | 1561 | 151 |
| buyerAddress | 1632 | 80 |
| manufacturingNo | 1402 | 49 |
| supplierCompany | 1066 | 222 |
| buyerCompany | 1097 | 183 |
| insuranceCode | 1240 | 16 |
| unitPrice | 337 | 784 |
| amount | 511 | 291 |
| supplyAmount | 159 | 183 |
| taxAmount | 33 | 246 |
| totalAmount | 62 | 208 |
| supplierBizNumber | 101 | 4 |
| issueDate | 73 | 0 |
| buyerBizNumber | 51 | 0 |
