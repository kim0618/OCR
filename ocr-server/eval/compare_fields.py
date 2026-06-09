"""compare_fields — per-sample scalar field comparison (Phase 3).

Matches by labelEn, applies the frozen normalization, scores only the contract
set (common-12 + the sample's one per-sample field). GT-empty values are skipped
(not penalized, per contract). Tracks `edited` (rich GT) so Phase 4 can slice.

compare_fields(gt_loaded, ext_document_fields) -> dict
"""

from __future__ import annotations

from typing import Any

import contract as C
import normalize as N

# Status values per field:
#   match        normalized GT == normalized extracted
#   mismatch     both non-empty, differ
#   ext_missing  GT non-empty, extracted empty/missing  (a real miss)
#   gt_empty     GT value empty -> skipped, not scored
#   gt_absent    field not in GT (e.g. the other per-sample field) -> skipped


def compare_fields(gt: dict[str, Any], ext_df: dict[str, Any]) -> dict[str, Any]:
    ext_df = ext_df or {}
    gt_fields: dict[str, Any] = gt["documentFields"]
    field_meta: dict[str, Any] = gt.get("fieldMeta", {})
    per_sample = gt["perSampleField"]

    # The keys we score for THIS sample: common-12 + its single per-sample field.
    scored_labels = list(C.COMMON_12) + [per_sample]

    per_field: dict[str, dict[str, Any]] = {}
    counts = {"scored": 0, "match": 0, "mismatch": 0, "ext_missing": 0, "gt_empty": 0}
    edited_counts = {"match": 0, "mismatch": 0, "ext_missing": 0}

    for label in scored_labels:
        gt_val = gt_fields.get(label, "")
        ext_val = ext_df.get(label, "")
        gt_empty = N.is_empty(gt_val)
        ext_empty = N.is_empty(ext_val)
        gt_n = N.normalize_field(label, gt_val)
        ext_n = N.normalize_field(label, ext_val)
        edited = bool(field_meta.get(label, {}).get("edited"))

        if gt_empty:
            status = "gt_empty"
        elif ext_empty:
            status = "ext_missing"
        elif gt_n == ext_n:
            status = "match"
        else:
            status = "mismatch"

        per_field[label] = {
            "gt": gt_val, "ext": ext_val,
            "gtNorm": gt_n, "extNorm": ext_n,
            "type": N.FIELD_TYPE.get(label, "text"),
            "status": status,
            "edited": edited,
        }

        if status != "gt_empty":
            counts["scored"] += 1
        counts[status] = counts.get(status, 0) + 1
        if edited and status in edited_counts:
            edited_counts[status] += 1

    scored = counts["scored"]
    accuracy = (counts["match"] / scored) if scored else None
    return {
        "perField": per_field,
        "perSampleField": per_sample,
        "counts": counts,
        "editedCounts": edited_counts,
        "fieldAccuracy": accuracy,  # match / scored (gt_empty excluded)
    }
