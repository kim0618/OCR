# T-20e preprocessing debug API validation result

## 1. Generated files
- `mysuit-ocr/public/data/testsets/reports/T20e_preprocessing_debug_api_validation_20260516.md`
- `mysuit-ocr/public/data/testsets/reports/T20e_preprocessing_debug_api_validation_20260516.json`
- `ocr-server/scripts/verify_preprocessing_debug_api_t20e.py`

## 2. Summary
- API baseUrl: `http://127.0.0.1:8121`
- debug=false has no preprocessingDebug: True
- debug=true non-template has preprocessingDebug: True
- productionApplied=false: True
- debug=false and debug=true final result same: True
- overall verdict: PASS
- Current main.py behavior does not attach preprocessingDebug on template region calls. Invoice validation is split into Template/RunOCR exact row guard and non-template debug candidate checks.

## 3. Validation targets
| sample | documentType | qualityTags | expected behavior |
|---|---|---|---|
| receipt_generalization/card_002.jpg | card_receipt | ["blurred"] | ["clahe", "candidate_accept"] |
| receipt_generalization/medical_001.jpg | medical_receipt | ["shadow"] | ["clahe", "candidate_accept"] |
| receipt_generalization/pos_006.jpg | pos_receipt | ["small_text", "garbled_source", "preprocessing_candidate"] | ["upscale_1_5x", "candidate_accept"] |
| receipt_generalization/medical_003.jpg | medical_receipt | ["long_receipt", "small_text"] | ["grayscale", "candidate_accept"] |
| invoice_statement/3.pdf | invoice_statement | ["pdf_low_resolution", "preprocessing_candidate", "rowcount_guard_required"] | ["render_dpi_200_grayscale", "candidate_accept"] |
| invoice_statement/2.pdf | invoice_statement | ["dense_table", "rowcount_guard_required", "preprocessing_blocked"] | [null, "preprocessing_blocked"] |
| invoice_statement/1.jpg | invoice_statement | [] | ["-", "no_specific_expectation"] |
| invoice_statement/5.pdf | invoice_statement | [] | ["-", "no_specific_expectation"] |
| receipt_generalization/pos_005.jpg | pos_receipt | ["long_receipt", "small_text"] | ["-", "no_specific_expectation"] |
| receipt_generalization/card_001.jpg | card_receipt | ["small_text", "garbled_source"] | ["-", "no_specific_expectation"] |

## 4. debug=false baseline
| sample | docType | rowCount | preprocessingDebug | verdict |
|---|---|---|---|---|
| receipt_generalization/card_002.jpg | receipt_card | - | False | PASS |
| receipt_generalization/medical_001.jpg | medical_receipt | - | False | PASS |
| receipt_generalization/pos_006.jpg | receipt_pos | - | False | PASS |
| receipt_generalization/medical_003.jpg | medical_receipt | - | False | PASS |
| invoice_statement/3.pdf | invoice_statement | 1 | False | PASS |
| invoice_statement/2.pdf | invoice_statement | 2 | False | PASS |
| invoice_statement/1.jpg | invoice_statement | 28 | False | PASS |
| invoice_statement/5.pdf | invoice_statement | 6 | False | PASS |
| receipt_generalization/pos_005.jpg | receipt_pos | - | False | PASS |
| receipt_generalization/card_001.jpg | receipt_card | - | False | PASS |

## 5. debug=true result
| sample | candidates | selectedCandidate | productionApplied | decision | verdict |
|---|---|---|---|---|---|
| receipt_generalization/card_002.jpg | 3 | clahe | False | candidate_accept | PASS |
| receipt_generalization/medical_001.jpg | 2 | clahe | False | candidate_accept | PASS |
| receipt_generalization/pos_006.jpg | 2 | upscale_1_5x | False | candidate_accept | PASS |
| receipt_generalization/medical_003.jpg | 3 | grayscale | False | candidate_accept | PASS |
| invoice_statement/3.pdf | 1 | render_dpi_200_grayscale | False | candidate_accept | PASS |
| invoice_statement/2.pdf | 0 | - | False | preprocessing_blocked | PASS |
| invoice_statement/1.jpg | 0 | - | False | preprocessing_blocked | PASS |
| invoice_statement/5.pdf | 0 | - | False | preprocessing_blocked | PASS |
| receipt_generalization/pos_005.jpg | 3 | grayscale | False | candidate_accept | PASS |
| receipt_generalization/card_001.jpg | 2 | upscale_1_5x | False | candidate_accept | PASS |

## 6. Final result equality
| sample | fields same | rowCount same | warnings same | verdict |
|---|---|---|---|---|
| receipt_generalization/card_002.jpg | True | True | True | PASS |
| receipt_generalization/medical_001.jpg | True | True | True | PASS |
| receipt_generalization/pos_006.jpg | True | True | True | PASS |
| receipt_generalization/medical_003.jpg | True | True | True | PASS |
| invoice_statement/3.pdf | True | True | True | PASS |
| invoice_statement/2.pdf | True | True | True | PASS |
| invoice_statement/1.jpg | True | True | True | PASS |
| invoice_statement/5.pdf | True | True | True | PASS |
| receipt_generalization/pos_005.jpg | True | True | True | PASS |
| receipt_generalization/card_001.jpg | True | True | True | PASS |

## 7. Invoice guard
| sample | original rowCount | candidate | candidate rowCount | decision | final applied |
|---|---|---|---|---|---|
| invoice_statement/3.pdf | 1 | render_dpi_200_grayscale | 1 | candidate_accept | False |
| invoice_statement/2.pdf | 13 | - | 2 | preprocessing_blocked | False |
| invoice_statement/1.jpg | 28 | - | 28 | preprocessing_blocked | False |
| invoice_statement/5.pdf | 6 | - | 6 | preprocessing_blocked | False |

## 8. Auto-apply decision
- receipt: limited auto-apply candidate, but keep debug-only until broader receipt regression validation
- invoice_statement: keep debug-only; template region path and non-template debug path are separated, so production apply is deferred
- production: defer auto-apply and keep productionApplied=false
- debug: keep debugPreprocessing=true validation path

## 9. Next decision
- keep debug mode and validate additional samples
- Receipt limited auto-apply is plausible, but needs broader normal-sample regression validation before production.
- Invoice preprocessing needs template path debug wiring and rowCount guard hardening before production.

## 10. Verification
- py_compile: PASS
- API validation script: PASS
- typecheck: PASS: npm.cmd run typecheck
- build: PASS: npm.cmd run build (Next.js reported existing ESLint nextVitals warning, exit 0)
