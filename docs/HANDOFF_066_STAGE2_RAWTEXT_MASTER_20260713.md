# 066 Stage 2: Fallback RawText Master Recovery (2026-07-13)

This document supplements the 066 reprioritization and Stage 1 handoff docs.
Scope is fallback parser output only. No learndata, re-OCR, or fine-tuning is
used, and raw itemName is intentionally unchanged.

## Baseline preservation

The official Stage 1 PASS artifacts were copied before this work so the next
official replay can be compared by protected row ID:

- `D:\Free_Vue\tmp\066_stage2_baseline_PARSER_DROP_CLASSIFY_replay_compare.json`
- `D:\Free_Vue\tmp\066_stage2_baseline_replay_history.json`

Stage 1 baseline master accuracy is `26,909 / 37,346`; raw itemName is
`13,586 / 37,363`.

## Residual fallback drop structure

After Stage 1, the official classifier contains 1,557 fallback itemName drop
defects over 793 documents. Using `gtOnlyRowIdx` as the authoritative structural
indicator:

- GT-only, rawText contains the GT name, no unique 2-field numeric anchor: 862
- GT-only, rawText contains the GT name, unique 2+ numeric anchors: 238
- GT-only, OCR row contains the name, no numeric anchor: 241
- aligned blank itemName: 118
- numeric row without name text: 34
- single numeric anchor: 28
- no row anchor: 35
- item relation plus numeric anchor: 1

`missingGtRow` is not equivalent to `gtOnlyRowIdx`: 330 defects were GT-only
while the row-level flag was false. Future analysis must use `gtOnlyRowIdx`.

## Rejected candidate

Filling raw itemName from same-row rawText was rejected. Even with a 46/46
oracle subset, changing itemName altered thin content alignment and caused large
existing-match losses across itemName and numeric columns.

## Accepted candidate

The accepted candidate fills only blank `itemNameMaster` values and leaves
itemName, itemCode, row count, and every numeric field untouched.

All release conditions are required:

1. Row source is exactly `invoice_statement_table_parser` (fallback canonical
   rows). Current free replay/sample rows use other source markers; 0 of 1,746
   free documents contain this marker.
2. itemName and itemNameMaster are both blank.
3. At least three of spec, quantity, unitPrice, amount, itemCode, and
   insuranceCode are non-empty.
4. Candidate text comes from the same row `_rawText`, cut before known numeric
   columns. Suffix candidates may skip only numeric/code or company tokens.
5. Master similarity is at least 0.80; a different-code runner-up must trail by
   at least 0.10; the selected code must be unique in the document.
6. The normalized master name must occur in the OCR candidate. Matcher-added
   qualifiers such as `(제약사품절)`, `(반품불가)`, or `(병)` are rejected when
   absent from OCR text.
7. A rejected best code remains reserved for later rows so tightening the gate
   cannot make a later duplicate newly eligible.

## Validation

Development sequence:

- sim >= 0.60 on 793 drop documents: master +55, but 5 new mismatches; rejected.
- sim >= 0.80 on all 4,218 fallback documents: master +48, but 2 new mismatches
  caused by matcher-added qualifiers; rejected.
- final containment gate is a strict subset of that full candidate.

Final selected-source A/B:

- itemNameMaster: +41
- transitions: 41 `ext_missing -> match`, 0 `ext_missing -> mismatch`
- itemName, spec, quantity, unitPrice, amount, expiryDate, manufacturingNo,
  itemCode, insuranceCode: zero lost or gained match rows
- protected absorb rows: lost 0, new 41
- raw-correct master-wrong/missing: new 0
- spurious: 0 -> 0
- study 24 documents: changed 0, count delta empty

Expected official thin smoke result, if no unrelated drift occurs:

- itemName unchanged: 13,586 / 37,363
- itemNameMaster: 26,909 -> 26,950 (+41)
- cross counts:
  `14,355 / 9,408 / 12,595 / 951 / 37`

The refreshed 5,964-file official replay and protectedRows ID diff against the
preserved Stage 1 classifier remain authoritative for acceptance.
