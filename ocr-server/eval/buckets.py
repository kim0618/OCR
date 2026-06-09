"""buckets — 4-bucket defect tagging (Phase 3).

Assigns a probable-cause bucket to each defect. HEURISTIC and explainable: every
tag carries a `reason`. Small-sample tags are hypotheses, not verdicts (plan §8).

Buckets:
  recognition  (A) value present but characters wrong  -> OCR recognition
  structure    (B) value landed in the wrong field/row, row count off, mislocated
  layout           column shift within a table row (value of key K is GT's K')
  preprocessing    sample-wide collapse (most fields empty) -> orientation/deskew suspect
"""

from __future__ import annotations

from difflib import SequenceMatcher
from typing import Any

import normalize as N

RECOGNITION = "recognition"
STRUCTURE = "structure"
LAYOUT = "layout"
PREPROCESSING = "preprocessing"


def _similar(a: str, b: str) -> float:
    if not a and not b:
        return 1.0
    return SequenceMatcher(None, a, b).ratio()


def _value_index(field_cmp: dict[str, Any], table_cmp: dict[str, Any], side: str) -> dict[str, set[str]]:
    """Map normalized value -> set of locations on one side ('gt' or 'ext')."""
    key = "gtNorm" if side == "gt" else "extNorm"
    idx: dict[str, set[str]] = {}
    for label, info in field_cmp["perField"].items():
        v = info[key]
        if v:
            idx.setdefault(v, set()).add(f"field:{label}")
    for row in table_cmp["rows"]:
        for ck, cell in row["cells"].items():
            v = cell[key]
            if v:
                idx.setdefault(v, set()).add(f"row{row['rowIndex']}:{ck}")
    return idx


def tag_sample(field_cmp: dict[str, Any], table_cmp: dict[str, Any]) -> dict[str, Any]:
    gt_idx = _value_index(field_cmp, table_cmp, "gt")
    ext_idx = _value_index(field_cmp, table_cmp, "ext")
    defects: list[dict[str, Any]] = []
    tally = {RECOGNITION: 0, STRUCTURE: 0, LAYOUT: 0, PREPROCESSING: 0}

    def add(loc: str, status: str, gtn: str, extn: str, bucket: str, reason: str):
        defects.append({
            "location": loc, "status": status, "gtNorm": gtn, "extNorm": extn,
            "bucket": bucket, "reason": reason,
        })
        tally[bucket] += 1

    # --- scalar field defects ---
    for label, info in field_cmp["perField"].items():
        st = info["status"]
        if st not in ("mismatch", "ext_missing"):
            continue
        gtn, extn = info["gtNorm"], info["extNorm"]
        loc = f"field:{label}"
        # value landed in a different location on the extracted side?
        elsewhere = {l for l in ext_idx.get(gtn, set()) if l != loc}
        if gtn and elsewhere:
            add(loc, st, gtn, extn, STRUCTURE, f"gt value present at {sorted(elsewhere)}")
        elif st == "ext_missing":
            add(loc, st, gtn, extn, STRUCTURE, "gt value not found anywhere in extraction")
        elif _similar(gtn, extn) >= 0.5:
            add(loc, st, gtn, extn, RECOGNITION, f"char-level diff (sim={_similar(gtn, extn):.2f})")
        else:
            # extracted value belongs to another GT field? -> structure, else recognition
            ext_src = {l for l in gt_idx.get(extn, set()) if l != loc}
            if extn and ext_src:
                add(loc, st, gtn, extn, STRUCTURE, f"ext value is gt's {sorted(ext_src)}")
            else:
                add(loc, st, gtn, extn, RECOGNITION, "value differs, low similarity")

    # --- table row-count defects (structure) ---
    if table_cmp["gtOnlyRowIdx"]:
        add("table", "rows_missed", "", "", STRUCTURE,
            f"extractor missed rows {table_cmp['gtOnlyRowIdx']}")
    if table_cmp["extOnlyRowIdx"]:
        add("table", "rows_extra", "", "", STRUCTURE,
            f"extractor invented rows {table_cmp['extOnlyRowIdx']}")

    # --- table cell defects (layout vs recognition vs structure) ---
    for row in table_cmp["rows"]:
        # same-row column shift -> layout
        gt_cells = {ck: c["gtNorm"] for ck, c in row["cells"].items() if c["gtNorm"]}
        ext_cells = {ck: c["extNorm"] for ck, c in row["cells"].items() if c["extNorm"]}
        for ck, cell in row["cells"].items():
            st = cell["status"]
            if st not in ("mismatch", "ext_missing"):
                continue
            loc = f"row{row['rowIndex']}:{ck}"
            gtn, extn = cell["gtNorm"], cell["extNorm"]
            shifted_to = [k for k, v in ext_cells.items() if k != ck and v == gtn]
            if gtn and shifted_to:
                add(loc, st, gtn, extn, LAYOUT, f"gt cell appears in column(s) {shifted_to}")
            elif st == "ext_missing":
                add(loc, st, gtn, extn, STRUCTURE, "gt cell absent in extracted row")
            elif _similar(gtn, extn) >= 0.5:
                add(loc, st, gtn, extn, RECOGNITION, f"char-level diff (sim={_similar(gtn, extn):.2f})")
            else:
                add(loc, st, gtn, extn, RECOGNITION, "cell differs, low similarity")

    # --- sample-wide preprocessing suspicion ---
    fc = field_cmp["counts"]
    scored = fc["scored"]
    miss_rate = (fc["ext_missing"] / scored) if scored else 0.0
    preprocessing_suspect = bool(scored >= 6 and miss_rate >= 0.7)
    if preprocessing_suspect:
        # re-tag the dominant failure as preprocessing at the sample level (advisory)
        tally[PREPROCESSING] += 1

    return {
        "defects": defects,
        "bucketTally": tally,
        "preprocessingSuspect": preprocessing_suspect,
        "fieldMissRate": round(miss_rate, 3),
    }
