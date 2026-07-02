# Fine-tune candidate ledger — 060_20260702_110119/study

OCR-bound defects captured: **162**  |  cropReady (confident misread localization): **141**  |  lowConf (box present, ratio<0.55): **19**  |  noBox (nothing localized): **2**

_cropReady = OCR read a near-miss at a confidently-located box → (box, GT) is a rec fine-tune candidate once pixels are cut. lowConf = a box exists but match is weak (kept with its ratio for later re-thresholding). noBox = OCR produced nothing matchable._

## By class

| class | cropReady | notReady |
|---|--:|--:|
| recognition | 141 | 21 |

## By column

| column | cropReady | notReady |
|---|--:|--:|
| itemName | 73 | 4 |
| spec | 14 | 4 |
| buyerAddress | 14 | 1 |
| supplierAddress | 12 | 1 |
| supplierRepresentative | 9 | 3 |
| buyerCompany | 5 | 3 |
| supplierBizNumber | 3 | 1 |
| lotNo | 4 | 0 |
| supplierCompany | 2 | 1 |
| quantity | 2 | 1 |
| buyerRepresentative | 0 | 2 |
| productCode | 2 | 0 |
| buyerBizNumber | 1 | 0 |
