# GOOGLE LOCK 2026-04-25

This document locks the current `google` validation state as the practical generalization reference after the baseline lock and google cleanup passes.

Scope:
- Google sample set only for practical generalization validation.
- Baseline remains the regression reference.
- This document does not change OCR logic, UI logic, suppression policy, orientation logic, amount logic, document classification, or baseline final-selection policy.
- Future work must avoid overfitting to a single sample and should move toward broadly comparable product quality across OCR products and companies.

## 1. Google Lock Purpose

The `google` sample set is a practical, real-world generalization validation set.

Baseline and google serve different purposes:
- `baseline` is the locked regression reference.
- `google` is the locked practical sample set used to observe generalization behavior and remaining failure patterns.

This document uses the latest google validation results as the reference point for later structure cleanup and regression validation.

The target is not one-off optimization for a specific vendor or sample. The target is a general-purpose OCR product level that can be compared across OCR products and companies.

After this lock, additional google samples should make the system more general, not more sample-specific.

## 2. Google Final Summary

Latest validation files:
- `mysuit-ocr/public/data/testsets/google/validation_results_google_final_before_lock.json`
- `mysuit-ocr/public/data/testsets/google/validation_results_google_final_before_lock_fields.json`

| Metric | Value |
|---|---:|
| Total files | 11 |
| Selected | 10 |
| Suppression | 1 |
| Unknown | 0 |
| Error | 0 |
| Avg total ms | 24531.5 |
| Avg detect_orientation ms | 10587.3 |
| Avg full_ocr ms | 8820.5 |
| Avg upper_reocr_total ms | 3619.3 |
| Avg amount_reocr_total ms | 1395.5 |

## 3. Main Success Cases

| File | Locked judgment |
|---|---|
| `7.jpg` | `receipt_pos` / `selected` maintained |
| `7.jpg` company | `GS25성신로데오점` |
| `7.jpg` total amount | `7,650` |
| `7.jpg` phone | `02-927-2369` |
| `6.jpg` | `suppressed_bank_slip` maintained |
| `11.jpg` phone/address | `02-33-4278`, `서울시 마포구홍익로 6길26 163-12호` |
| `8.jpg` company | false positive removed; remains blank |
| `10.jpg` address | remains blank due to raw absence/insufficient safe address evidence |

## 4. Remaining Limits

Known google limits:
- `7.jpg` address remains blank.
- `10.jpg` address remains blank.
- `11.jpg` phone is read as `02-33-4278`; actual digit recovery remains conservative.
- `9.jpg` business number may still have a one-digit `506/508` instability risk.
- Suppressed documents may show raw fields, but selected-value adoption and GT correction remain disabled by policy.
- Google must be read as a practical generalization benchmark, not a GT-based final-selection benchmark.

## 5. Baseline Regression Check

Baseline regression files used with this google lock:
- `mysuit-ocr/public/data/testsets/baseline_fast/validation_results_baseline_fast_after_google_final_before_lock.json`
- `mysuit-ocr/public/data/testsets/baseline/validation_results_baseline_after_google_final_before_lock.json`
- `docs/BASELINE_LOCK_20260425.md`

Baseline_fast:

| Metric | Value |
|---|---:|
| Selected | 3 |
| Suppression | 2 |
| Unknown | 0 |
| OCR-own score | 21/27 |
| Final selected-value score | 23/27 |

Baseline:

| Metric | Value |
|---|---:|
| Selected | 8 |
| Suppression | 2 |
| Unknown | 0 |
| OCR-own score | 43/57 |
| Final selected-value score | 52/57 |
| Business-number recall | 9/9 |
| Total amount | 8/10 |

Baseline interpretation:
- Baseline remains locked as the regression reference.
- OCR-own score and final selected-value score must continue to be read separately.
- Baseline final-selection behavior is baseline/baseline_fast specific and must not be treated as product-wide GT anchoring.

## 6. Post-Lock Work Principles

After google lock, do not immediately add more OCR recognition logic.

The next stage is testset management, UI, documentType, qualityTags, and summary structure cleanup.

Quality conditions must be managed as `qualityTags`, not document types:
- folded
- blurred
- skewed
- curled
- low contrast
- handwritten
- stamp/seal
- other capture or print quality conditions

`documentType` must represent the actual document class, for example:
- Card receipt
- POS / mart receipt
- Restaurant / cafe receipt
- Bank / financial slip
- Hospital / pharmacy receipt
- Tax invoice / transaction statement
- Other / Unknown

Prepare the system so later summaries can group by:
- documentType selected/suppression/unknown/error
- documentType field-level failure rate
- qualityTags selected/suppression/unknown/error
- qualityTags field-level failure rate

At this stage, OCR recognition logic itself should not be changed.

## 7. Next Stage

Recommended next steps:
- Add `manifest.json` or an equivalent metadata structure.
- Assign each image a `documentType`, `qualityTags`, and `difficulty`.
- Change the default UI grouping to documentType.
- Move existing folded/skewed style groups into qualityTags display.
- Add documentType-level summary.
- Add qualityTags-level summary.
- Prepare later `main.py` refactoring/commonization.
- Add transaction statement doc_type only after testset and structure cleanup.

## 8. Refactoring Premise

Do not go directly to transaction statement work after this google lock.

Recommended order:
1. Lock google with this document.
2. Clean up testset management, UI grouping, and common summary structure.
3. Split `main.py` step by step without functional changes.
4. Keep baseline/google results stable during refactoring.
5. Prepare separation for common normalize, regex, bbox, field extractor, policy, and response builder modules.
6. Add transaction statement doc_type after structure and regression visibility are ready.

Refactoring is structural cleanup, not feature improvement. Baseline and google locked results must remain stable.

## Lock Judgment

The current google state is suitable to lock as the practical generalization reference.

Final locked google interpretation:
- `selected`: 10
- `suppression`: 1
- `unknown`: 0
- `error`: 0
- Key 7.jpg improvements are maintained: `receipt_pos`, `selected`, `GS25성신로데오점`, `7,650`, `02-927-2369`.
- Baseline lock remains intact: baseline OCR `43/57`, final selected-value `52/57`, business-number recall `9/9`, total amount `8/10`.
