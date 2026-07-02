# Fine-tune candidate ledger — 058_20260702_105036/study

OCR-bound defects captured: **1308**  |  cropReady (confident misread localization): **0**  |  lowConf (box present, ratio<0.55): **0**  |  noBox (nothing localized): **1308**

_cropReady = OCR read a near-miss at a confidently-located box → (box, GT) is a rec fine-tune candidate once pixels are cut. lowConf = a box exists but match is weak (kept with its ratio for later re-thresholding). noBox = OCR produced nothing matchable._

## By class

| class | cropReady | notReady |
|---|--:|--:|
| recognition | 0 | 1308 |

## By column

| column | cropReady | notReady |
|---|--:|--:|
| itemName | 0 | 172 |
| quantity | 0 | 172 |
| unitPrice | 0 | 144 |
| amount | 0 | 144 |
| lotNo | 0 | 136 |
| expiryDate | 0 | 128 |
| spec | 0 | 116 |
| productCode | 0 | 52 |
| buyerBizNumber | 0 | 24 |
| buyerCompany | 0 | 24 |
| buyerAddress | 0 | 24 |
| issueDate | 0 | 24 |
| supplierBizNumber | 0 | 20 |
| supplierCompany | 0 | 20 |
| supplierAddress | 0 | 20 |
| supplierRepresentative | 0 | 20 |
| buyerRepresentative | 0 | 20 |
| totalAmount | 0 | 16 |
| supplyAmount | 0 | 12 |
| taxAmount | 0 | 12 |
| cumulativeAmount | 0 | 4 |
| totalQuantity | 0 | 4 |
