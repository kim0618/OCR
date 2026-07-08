# Fine-tune candidate ledger — 064_20260708_134418/study

OCR-bound defects captured: **310**  |  cropReady (confident misread localization): **282**  |  lowConf (box present, ratio<0.55): **8**  |  noBox (nothing localized): **20**

_cropReady = OCR read a near-miss at a confidently-located box → (box, GT) is a rec fine-tune candidate once pixels are cut. lowConf = a box exists but match is weak (kept with its ratio for later re-thresholding). noBox = OCR produced nothing matchable._

## By class

| class | cropReady | notReady |
|---|--:|--:|
| recognition | 279 | 28 |
| ambiguous_fuzzy | 3 | 0 |

## By column

| column | cropReady | notReady |
|---|--:|--:|
| lotNo | 92 | 0 |
| itemName | 72 | 2 |
| quantity | 15 | 17 |
| spec | 25 | 0 |
| buyerAddress | 21 | 1 |
| productCode | 14 | 0 |
| supplierRepresentative | 6 | 6 |
| supplierAddress | 12 | 0 |
| buyerCompany | 11 | 0 |
| supplierCompany | 3 | 1 |
| supplierBizNumber | 4 | 0 |
| expiryDate | 2 | 0 |
| buyerRepresentative | 1 | 1 |
| totalAmount | 2 | 0 |
| issueDate | 1 | 0 |
| buyerBizNumber | 1 | 0 |
