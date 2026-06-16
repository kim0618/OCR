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


def _spurious_tag(field_type: str | None, ext_value: Any) -> str:
    """Route a spurious (invented) value: `rule` when it violates the field's
    type invariant — a deterministic guard can reject it (e.g. the label "합" in a
    money field) — else `learn`, a type-valid value in the wrong field (mapping).
    """
    text = str(ext_value or "").strip()
    digits = "".join(ch for ch in text if ch.isdigit())
    if field_type == "amount":
        return "rule" if not digits else "learn"
    if field_type == "bizno":
        return "rule" if len(digits) != 10 else "learn"
    if field_type == "date":
        return "rule" if len(digits) not in (6, 8) else "learn"
    return "learn"


def compare_fields(gt: dict[str, Any], ext_df: dict[str, Any]) -> dict[str, Any]:
    ext_df = ext_df or {}
    gt_fields: dict[str, Any] = gt["documentFields"]
    field_meta: dict[str, Any] = gt.get("fieldMeta", {})
    per_sample = gt.get("perSampleField")
    profile = gt.get("profile", "rich")

    # ➊⓭ Score exactly the keys the GT provides (perSampleField retired as a
    # scoring driver). For rich GT this is the identical COMMON_12 + 1 per-sample
    # set; for thin GT it is whatever war columns the ETL emitted.
    scored_labels = list(gt_fields.keys())

    per_field: dict[str, dict[str, Any]] = {}
    # `spurious` = GT empty but extractor produced a value (a false positive the
    # recall accuracy never sees, because gt_empty is excluded from scoring). We
    # keep status == "gt_empty" untouched (recall denominator unchanged) and only
    # add a parallel flag/tally, so existing accuracy and the TREND stay identical.
    counts = {"scored": 0, "match": 0, "mismatch": 0, "ext_missing": 0, "gt_empty": 0, "spurious": 0}
    edited_counts = {"match": 0, "mismatch": 0, "ext_missing": 0}
    # ➌E coverage two denominators: of GT-present (graded) fields, separate the
    # extractor's genuine misses (tried, wrong/empty) from "never even attempted"
    # (key absent from extractor output — the new-3 honest-miss case).
    coverage = {"gtPresent": 0, "matched": 0, "extNotAttempted": 0, "extAttemptedMiss": 0}

    for label in scored_labels:
        gt_val = gt_fields.get(label, "")
        ext_attempted = label in ext_df          # key present in extractor output at all
        ext_val = ext_df.get(label, "")
        gt_empty = N.is_empty(gt_val)
        ext_empty = N.is_empty(ext_val)
        gt_n = N.normalize_field(label, gt_val)
        ext_n = N.normalize_field(label, ext_val)
        edited = bool(field_meta.get(label, {}).get("edited"))
        # difficulty subset (➐): rich = human-edited; thin = war low-confidence field.
        difficult = edited if profile == "rich" else (label in C.THIN_LOW_CONFIDENCE_FIELDS)

        if gt_empty:
            status = "gt_empty"
        elif ext_empty:
            status = "ext_missing"
        elif gt_n == ext_n:
            status = "match"
        else:
            status = "mismatch"

        # spurious = should-be-blank (GT empty) but extractor invented a value.
        spurious = gt_empty and not ext_empty
        field_type = N.FIELD_TYPE.get(label) or N._infer_type(label)

        per_field[label] = {
            "gt": gt_val, "ext": ext_val,
            "gtNorm": gt_n, "extNorm": ext_n,
            "type": field_type,
            "status": status,
            "edited": edited,
            "difficult": difficult,
            "extAttempted": ext_attempted,
            "spurious": spurious,
            "spuriousTag": _spurious_tag(field_type, ext_val) if spurious else None,
        }

        if status != "gt_empty":
            counts["scored"] += 1
            coverage["gtPresent"] += 1
            if status == "match":
                coverage["matched"] += 1
            elif status == "ext_missing":
                coverage["extNotAttempted" if not ext_attempted else "extAttemptedMiss"] += 1
        counts[status] = counts.get(status, 0) + 1
        if spurious:
            counts["spurious"] += 1
        if edited and status in edited_counts:
            edited_counts[status] += 1

    scored = counts["scored"]
    accuracy = (counts["match"] / scored) if scored else None
    return {
        "perField": per_field,
        "perSampleField": per_sample,
        "profile": profile,
        "counts": counts,
        "editedCounts": edited_counts,
        "coverage": coverage,
        "fieldAccuracy": accuracy,  # match / scored (gt_empty excluded)
    }
