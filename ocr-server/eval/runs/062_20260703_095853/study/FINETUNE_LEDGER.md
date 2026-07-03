# Fine-tune candidate ledger — 062_20260703_095853/study

OCR-bound defects captured: **157**  |  cropReady (confident misread localization): **141**  |  lowConf (box present, ratio<0.55): **14**  |  noBox (nothing localized): **2**

_cropReady = OCR read a near-miss at a confidently-located box → (box, GT) is a rec fine-tune candidate once pixels are cut. lowConf = a box exists but match is weak (kept with its ratio for later re-thresholding). noBox = OCR produced nothing matchable._

## By class

| class | cropReady | notReady |
|---|--:|--:|
| recognition | 141 | 16 |

## By column

| column | cropReady | notReady |
|---|--:|--:|
| itemName | 73 | 4 |
| spec | 14 | 4 |
| buyerAddress | 13 | 1 |
| supplierAddress | 13 | 0 |
| supplierRepresentative | 9 | 2 |
| buyerCompany | 7 | 1 |
| lotNo | 5 | 0 |
| supplierBizNumber | 2 | 2 |
| supplierCompany | 2 | 1 |
| productCode | 2 | 0 |
| buyerBizNumber | 1 | 0 |
| quantity | 0 | 1 |
