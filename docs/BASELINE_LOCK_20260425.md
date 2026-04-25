# BASELINE LOCK 2026-04-25

This document locks the current `baseline` OCR state as the regression reference after the baseline-only final selection policy cleanup.

Scope:
- Baseline and baseline_fast only.
- No google/generalization validation was run for this lock update.
- No OCR body logic, amount logic, suppression policy, orientation logic, or product-wide GT anchor policy is changed by this document.
- OCR-own performance and final selected-value performance must be read separately.

## 1. Current Baseline Summary

Latest validation files:
- `mysuit-ocr/public/data/testsets/baseline/validation_results_baseline_baseline_final_selection_policy.json`
- `mysuit-ocr/public/data/testsets/baseline_fast/validation_results_baseline_fast_baseline_final_selection_policy.json`

Baseline generated at:
- `2026-04-25T05:50:14.840Z`

Baseline summary:

| Metric | Value |
|---|---:|
| Total files | 10 |
| Selected | 8 |
| Suppression | 2 |
| Unknown | 0 |
| OCR-own score | 43/57 |
| Final selected-value score | 51/57 |

Baseline_fast summary:

| Metric | Value |
|---|---:|
| Total files | 5 |
| Selected | 3 |
| Suppression | 2 |
| Unknown | 0 |
| OCR-own score | 21/27 |
| Final selected-value score | 23/27 |

## 2. Field-Level Locked State

The lock now tracks both OCR-own performance and final selected-value performance:

| Field | OCR-own | Final selected value | Lock judgment |
|---|---:|---:|---|
| Company | 7/10 | 9/10 | improved by baseline final-selection policy |
| Representative | 6/10 | 9/10 | improved by baseline final-selection policy |
| Phone | 7/9 | 8/9 | improved by baseline final-selection policy |
| Address | 6/9 | 8/9 | improved by baseline final-selection policy |
| Business number | 9/9 | 9/9 | OCR basis maintained |
| Total amount | 8/10 | 8/10 | OCR basis maintained |

Important interpretation:
- OCR-own score remains the model/raw extraction quality metric.
- Final selected-value score is the user-facing baseline result after baseline-only GT selection policy.
- These two scores must not be mixed.

## 3. Core Regression Criteria

These criteria must remain true after later changes:

- `1.jpg` total amount remains `10,560`.
- `4.jpg` total amount remains `17,600`.
- `10.jpg` remains `selected`, and total amount remains `19,250`.
- `9.jpg` remains `suppressed_bank_slip`.
- `a2.jpg` remains `suppressed_handwritten`.
- Business-number recall remains `9/9` for GT-bearing baseline business documents.
- Total amount remains OCR-based and is not GT-corrected.

## 4. Final Selection Policy

This policy applies only in `baseline` and `baseline_fast`.

Applicable fields:
- Company
- Representative
- Phone
- Address

Excluded fields:
- Business number remains OCR-based, though it may be used as an anchor.
- Total amount remains OCR-based and is never GT-filled.

Policy:

| Condition | Final selected value | Source |
|---|---|---|
| OCR value exactly matches GT after field normalization | OCR value | `OCR` |
| OCR value is highly similar to GT | GT value | `GT_SIMILARITY` |
| OCR value is empty, GT exists, and business number exact-matches | GT value | `GT_ANCHOR_EMPTY` |
| OCR value is weak/label/noise, GT exists, and business number exact-matches | GT value | `GT_ANCHOR_WEAK_VALUE` |
| OCR value is an obvious wrong fragment/misread, GT exists, and business number exact-matches | GT value | `GT_ANCHOR_OVERRIDE` |

Safety rules:
- The policy is dataset-gated to baseline/baseline_fast only.
- Fields without GT are not force-filled.
- Suppressed documents keep GT anchor disabled.
- If business number exact-match is absent, empty OCR is not blindly filled from GT.
- High OCR-GT similarity may normalize to GT even without business-number anchor.
- Source/reason must show the GT-based path; GT-selected final values must not appear as plain OCR.

## 5. Business Number State

Ground truth has business numbers for:

| File | GT biz no | OCR biz no | Current judgment |
|---|---|---|---|
| `1.jpg` | `138-81-68468` | `138-81-68468` | hit |
| `2.jpg` | `138-08-99333` | `138-08-99333` | hit |
| `3.jpg` | `119-10-88385` | `119-10-88385` | hit |
| `4.jpg` | `123-23-94265` | `123-23-94265` | hit |
| `7.jpg` | `581-10-00658` | `581-10-00658` | hit |
| `8.jpg` | `134-04-13602` | `134-04-13602` | hit |
| `10.jpg` | `761-21-00890` | `761-21-00890` | hit |
| `a1.jpg` | `123-23-94265` | `123-23-94265` | hit |
| `a2.jpg` | `119-10-88385` | `119-10-88385` | hit |

Current recall judgment:
- Business-number recall is locked at `9/9`.
- `9.jpg` is a bank slip and must keep business number empty.
- Business number is not GT-corrected as a final selected field.

## 6. Representative Success Cases

The latest final-selection policy improves user-facing baseline values without changing OCR raw behavior.

Representative successes:

- `10.jpg`: company OCR `토탈칠물` is finally selected as GT `토탈철물` via `GT_SIMILARITY`.
- `7.jpg`: address is selected from GT via `GT_SIMILARITY`.
- `2.jpg`: representative restored from GT via `GT_ANCHOR_EMPTY`.
- `3.jpg`: representative restored from GT via `GT_ANCHOR_EMPTY`.
- `4.jpg`: company/address restored from GT via `GT_ANCHOR_EMPTY`.
- `a1.jpg`: company OCR `기계공구` is finally selected as GT `정공구` via `GT_ANCHOR_OVERRIDE`.
- `a1.jpg`: representative, phone, and address restored from GT via `GT_ANCHOR_EMPTY`.

## 7. Current Row-Level Final State

| File | Status | Final company | Final representative | Final tel | Final address | Final total |
|---|---|---|---|---|---|---|
| `1.jpg` | selected | `(주)안전볼트` | `윤봉상` | `031-479-0485` | `경기 안양시 동안구 호계동 555-9 국` | `10,560` |
| `2.jpg` | selected | `화성툴` | `이태주` | `031-479-0090` | `경기 안양시 동안구 엘에스로 92 8동140호` | `11,000` |
| `3.jpg` | selected | `세광전기조명` | `이정은` | `031-479-2280` | `경기 안양시 동안구 엘에스로 76 (호계동)7-117.11` | `33,000` |
| `4.jpg` | selected | `정공구` | `정영달` | `031-479-3690` | `경기 안양시 동안구 엘에스로 92` | `17,600` |
| `7.jpg` | selected | `서울집` | `신미남` | `031-388-1080` | GT-selected address | `35,000` |
| `8.jpg` | selected | `효성온누리약국` | `최성환` | `031-455-9955` | `경기 의왕시 경수대로237` | `11,000` |
| `9.jpg` | suppressed_bank_slip |  |  |  |  |  |
| `10.jpg` | selected | `토탈철물` | `전용민` | `010-9388-9936` | `경기 의왕시 효행로 47 (오전동)1층` | `19,250` |
| `a1.jpg` | selected | `정공구` | `정영달` | `031-479-3690` | `경기 안양시 동안구 엘에스로 92` | `110,000` |
| `a2.jpg` | suppressed_handwritten | `세광전기조명` | `이정` | `031-479-2280` | `경기도 안양시 동안구 엘에스로 76,7-17,118` |  |

## 8. Residual Limits

Known remaining limits:

- `a2.jpg` remains `suppressed_handwritten`; GT anchor stays disabled for suppressed documents.
- `1.jpg` address trailing `국` remains an OCR-own value and is not GT-corrected under the current final policy.
- Suppression documents continue to avoid GT correction.
- Total amount is unchanged by final-selection policy and remains OCR-based.
- OCR-own metric still reflects raw/normalized extraction quality and may remain lower than final selected-value metric.

## 9. Next-Step Conditions

Baseline is now the regression reference.

Recommended next stage:
- Move to google/generalization validation only after this lock.

Mandatory after google/generalization work:
- Run `baseline_fast` first.
- Then run full `baseline` if the change can affect extraction or final selection.
- Confirm the core regression criteria in section 3.
- Confirm business-number recall remains `9/9`.
- Confirm amount/suppression statuses for `1.jpg`, `4.jpg`, `10.jpg`, `9.jpg`, and `a2.jpg`.
- Read OCR-own and final selected-value scores separately.

## Lock Judgment

The current baseline state is suitable to lock as the regression baseline.

Final locked interpretation:
- OCR-own baseline: `43/57`.
- User-facing final selected-value baseline: `51/57`.
- Baseline final-selection policy is allowed only for baseline/baseline_fast test screens and must not be treated as product-wide GT anchor behavior.
