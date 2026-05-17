# T-20f receipt preprocessing regression validation result

## 1. Generated files
- `mysuit-ocr/public/data/testsets/reports/T20f_receipt_preprocessing_regression_validation_20260516.md`
- `mysuit-ocr/public/data/testsets/reports/T20f_receipt_preprocessing_regression_validation_20260516.json`
- `ocr-server/scripts/verify_receipt_preprocessing_regression_t20f.py`

## 2. Summary
- total targets: 15
- final result same: True
- productionApplied=false: True
- candidate recheck ok: True
- normal receipt regressions: 0
- normal candidate_accept debug-only count: 2
- overall verdict: PASS

## 3. Validation targets
| group | sample | documentType | reason |
|---|---|---|---|
| candidate | receipt_generalization/card_002.jpg | card_receipt | T20e candidate clahe |
| candidate | receipt_generalization/medical_001.jpg | medical_receipt | T20e candidate clahe |
| candidate | receipt_generalization/pos_006.jpg | pos_receipt | T20e candidate upscale_1_5x |
| candidate | receipt_generalization/medical_003.jpg | medical_receipt | T20e candidate grayscale |
| normal_receipt | receipt_generalization/card_001.jpg | card_receipt | card normal/no specific expectation |
| normal_receipt | baseline/2.jpg | card_receipt | locked baseline card normal |
| normal_receipt | receipt_generalization/pos_002.jpg | pos_receipt | pos normal |
| normal_receipt | receipt_generalization/pos_005.jpg | pos_receipt | pos long receipt normal |
| normal_receipt | receipt_generalization/food_003.jpg | food_cafe_receipt | food/cafe normal small text |
| normal_receipt | receipt_generalization/food_005.jpg | food_cafe_receipt | food/cafe normal small text |
| normal_receipt | receipt_generalization/medical_002.jpg | medical_receipt | medical normal small text |
| normal_receipt | receipt_generalization/medical_004.jpg | medical_receipt | medical easy normal |
| blocked_edge | invoice_statement/2.pdf | invoice_statement | invoice preprocessing blocked |
| blocked_edge | invoice_statement/3.pdf | invoice_statement | invoice debug candidate, production excluded |
| blocked_edge | receipt_generalization/pos_001.jpg | pos_receipt | receipt no-improvement/garbled edge |

## 4. Candidate sample recheck
| sample | selectedCandidate | decision | productionApplied | verdict |
|---|---|---|---|---|
| receipt_generalization/card_002.jpg | clahe | candidate_accept | False | PASS |
| receipt_generalization/medical_001.jpg | clahe | candidate_accept | False | PASS |
| receipt_generalization/pos_006.jpg | upscale_1_5x | candidate_accept | False | PASS |
| receipt_generalization/medical_003.jpg | grayscale | candidate_accept | False | PASS |

## 5. Normal receipt regression check
| sample | candidates | decision | final same | issue |
|---|---|---|---|---|
| receipt_generalization/card_001.jpg | 2 | candidate_accept | True | normal_candidate_accept_debug_only |
| baseline/2.jpg | 0 | preprocessing_blocked | True | none |
| receipt_generalization/pos_002.jpg | 0 | preprocessing_blocked | True | none |
| receipt_generalization/pos_005.jpg | 3 | candidate_accept | True | normal_candidate_accept_debug_only |
| receipt_generalization/food_003.jpg | 0 | preprocessing_blocked | True | none |
| receipt_generalization/food_005.jpg | 0 | preprocessing_blocked | True | none |
| receipt_generalization/medical_002.jpg | 0 | preprocessing_blocked | True | none |
| receipt_generalization/medical_004.jpg | 0 | preprocessing_blocked | True | none |

## 6. Invoice/blocked sample check
| sample | candidates | decision | rowCount | verdict |
|---|---|---|---|---|
| invoice_statement/2.pdf | 0 | preprocessing_blocked | 2 | PASS |
| invoice_statement/3.pdf | 1 | candidate_accept | 1 | PASS |
| receipt_generalization/pos_001.jpg | 2 | candidate_accept | - | PASS |

## 7. Auto-apply decision
- receipt: receipt limited auto-apply design is possible
- invoice_statement: exclude from auto-apply and keep debug-only
- production: do not enable auto-apply; keep productionApplied=false
- debug: keep debugPreprocessing=true validation path

## 8. Next decision
- T-20g receipt limited auto-apply design
- Do not enable production auto-apply in this task.
- If T-20g proceeds, start with receipt-only guards and keep invoice_statement excluded.

## 9. Verification
- py_compile: PASS
- validation script: PASS
- typecheck: PASS: npm.cmd run typecheck
- build: PASS: npm.cmd run build (Next.js reported existing ESLint nextVitals warning, exit 0)
