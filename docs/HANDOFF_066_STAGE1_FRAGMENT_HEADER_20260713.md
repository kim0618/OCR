# 066 Stage 1: Fragmented itemName Header Candidate (2026-07-13)

This document supplements `HANDOFF_066_MASTER_REPRIORITIZATION_20260713.md`.
Scope is fallback table extraction only; no learndata, re-OCR, or fine-tuning.

## Root cause

- OCR frequently splits item-name headers into adjacent tokens such as
  `품` + `명` or `제` + `품`.
- Reconstructing all split headers (`수`+`량`, `단`+`가`, `금`+`액`) caused
  cross-column regressions. The production candidate reconstructs only the
  canonical `itemName` header.

## Release gate

All conditions are required:

1. Adjacent fragments map to `itemName`, and itemName is not already present.
2. Original and candidate row counts are equal, non-zero, and at most six.
3. Every original itemName is empty; row-by-row `spec` is unchanged.
4. Every newly filled name resolves through the current master matcher, with
   non-empty and unique item codes.
5. The downstream HA append step would append zero rows for both paths. This
   prevents GT/alignment changes after leading blank-name rows are filled.

## 066 validation

- Broad split-header candidate was rejected due protected-row and numeric
  regressions.
- ItemName-only plus equal HA append counts was also rejected: equal counts
  still changed GT alignment for `471406...#row10/#row11`.
- Final zero-HA gate was recomposed over every source selected by the 4,218-file
  fallback oracle: itemName `+2`, itemNameMaster `+7`, spec `+4`, itemCode `+7`.
- Lost match row IDs were zero for itemName, itemNameMaster, spec, quantity,
  unitPrice, amount, expiryDate, manufacturingNo, itemCode, and insuranceCode.
  Spurious remained unchanged.
- The production implementation reproduced the same deltas on the complete
  selected-source superset.

Implementation: `ocr-server/extractors/invoice_statement.py`.

Acceptance remains pending until the user refreshes official study/thin replay
outputs and Claude Code reviews the committed diff and protectedRows changes.
The 5,964-file official replay is authoritative; focused oracle values are not.
