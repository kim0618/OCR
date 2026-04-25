# SESSION SUMMARY

## Current Status

Baseline validation is locked.

- Lock document: docs/BASELINE_LOCK_20260425.md
- Baseline OCR score: 43/57
- Baseline final selected value score: 52/57
- Business number: 9/9
- Total amount: 8/10
- selected: 8
- suppression: 2
- unknown: 0

Google validation is locked.

- Lock document: docs/GOOGLE_LOCK_20260425.md
- Google total: 11
- selected: 10
- suppression: 1
- unknown: 0
- error: 0

Key Google improvements:

- 7.jpg is receipt_pos / selected
- 7.jpg company: GS25성신로데오점
- 7.jpg amount: 7,650
- 7.jpg phone: 02-927-2369
- 6.jpg remains suppressed_bank_slip
- 11.jpg phone/address improvement retained
- 8.jpg company false positive removed
- 10.jpg address remains blank due to raw absence

## Current Next Stage

Do not continue OCR recognition improvement now.

Next stage is testset management and UI structure preparation.

Tasks:

1. Add manifest.json or equivalent metadata structure
2. Add documentType / qualityTags / difficulty / expectedStatus per image
3. Prepare UI/types to read testset metadata
4. Group samples by documentType later
5. Add documentType summary and qualityTags summary later
6. After this, refactor main.py/common structure
7. After refactoring, start invoice/transaction statement doc_type

## Important Direction

This OCR project should not overfit to a single vendor or sample set.

Goal:

- Compare with other OCR products
- Improve recognition as samples accumulate
- Support multiple document types
- Use baseline as regression safety
- Use google as real-world generalization validation

## Next Immediate Task

Metadata structure only.

No OCR logic modification.
No main.py modification.
No amount_extractor.py modification.
No document_classifier.py modification.
No parser changes.
No invoice implementation yet.