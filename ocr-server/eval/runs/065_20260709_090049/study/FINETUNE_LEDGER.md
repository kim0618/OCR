# Fine-tune candidate ledger — 065_20260709_090049/study

OCR-bound defects captured: **153**  |  cropReady (confident misread localization): **137**  |  lowConf (box present, ratio<0.55): **14**  |  noBox (nothing localized): **2**

_cropReady = OCR read a near-miss at a confidently-located box → (box, GT) is a rec fine-tune candidate once pixels are cut. lowConf = a box exists but match is weak (kept with its ratio for later re-thresholding). noBox = OCR produced nothing matchable._

## By class

| class | cropReady | notReady |
|---|--:|--:|
| recognition | 137 | 16 |

## By column

| column | cropReady | notReady |
|---|--:|--:|
| itemName | 73 | 4 |
| spec | 14 | 4 |
| buyerAddress | 13 | 1 |
| supplierAddress | 12 | 0 |
| supplierRepresentative | 9 | 2 |
| buyerCompany | 6 | 2 |
| lotNo | 5 | 0 |
| supplierBizNumber | 2 | 2 |
| productCode | 2 | 0 |
| buyerBizNumber | 1 | 0 |
| quantity | 0 | 1 |
