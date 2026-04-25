# OCR Project Rules for Claude Code

## Project Goal

This OCR project is not optimized for one specific vendor or one fixed form.  
The goal is to build a general-purpose OCR product that can be compared against other OCR companies/products.

Recognition quality should improve as samples accumulate, but improvements must generalize across document types and vendors. Avoid overfitting to a single sample, company, or dataset.

## Current Locked Baselines

Read these documents before making any change:

- docs/BASELINE_LOCK_20260425.md
- docs/GOOGLE_LOCK_20260425.md

Baseline is the regression safety set.  
Google is the real-world generalization set.

## Current Stage

Google validation is locked.  
The next stage is NOT OCR recognition improvement.

Current stage:

1. Testset management
2. UI grouping
3. documentType / qualityTags / difficulty metadata
4. summary aggregation
5. future parser branching foundation

OCR recognition logic must not be modified in this stage.

## Document Type Policy

documentType means the actual document type, such as:

- card_receipt
- pos_receipt
- food_cafe_receipt
- finance_slip
- medical_receipt
- invoice_statement
- unknown

Image conditions are NOT document types.

These must be qualityTags:

- folded
- curled
- skewed
- blurred
- low_contrast
- shadow
- stamp
- handwritten
- cropped
- rotated
- ocr_noise
- small_text

## Strict Rules

Before modifying any file:

1. Read CLAUDE.md
2. Read SESSION_SUMMARY.md
3. Read relevant lock documents
4. Identify exact task scope
5. Create backup files in the backup folder
6. Modify only files required by the task
7. Run typecheck/build if applicable
8. Report exact changed files and validation result

## Backup Rule

Before editing any file, copy it to backup with timestamp and task name.

Example:

backup/TestWorkspace_20260425_2200_before_dataset_manifest_metadata.tsx
backup/testsets_20260425_2200_before_dataset_manifest_metadata.ts

Never edit without backup.

## Validation Rule

For OCR logic changes:

1. google or target dataset
2. baseline_fast
3. baseline

For UI/metadata-only changes:

1. npm run typecheck
2. npm run build if possible
3. Confirm dataset selection and Run All path are not broken

## Do Not Modify Unless Explicitly Asked

- ocr-server/main.py
- ocr-server/amount_extractor.py
- ocr-server/document_classifier.py
- suppression logic
- orientation logic
- baseline final-selection policy
- validation result JSON files
- lock documents unless the task is documentation update

## Current Next Task

After Google Lock, proceed to testset management and UI structure preparation:

1. Add manifest.json or equivalent metadata structure
2. Assign documentType, qualityTags, difficulty, expectedStatus
3. Prepare UI/type structure to read metadata
4. Do not change OCR logic
5. Do not add invoice parser yet
6. Do not refactor main.py yet

## Important Product Direction

This OCR must become a scalable, generalizable product.

Do not optimize for one vendor only.
Do not add sample-specific rules unless explicitly marked as test-only.
Prefer reusable metadata, parser branching, documentType-based structure, and regression-safe changes.