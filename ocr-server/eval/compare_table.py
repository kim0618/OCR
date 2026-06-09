"""compare_table — per-row / per-cell table comparison (Phase 3).

Aligns GT rows to extracted rows by normalized rowIndex, compares only contract
value cells (ROW_VALUE_KEYS minus the rowIndex alignment key), applies frozen
normalization, skips GT-empty cells. excludedRows are already separated by the
loader, so they can never be counted as misses.

Extracted rows carry internal keys (_rawText/_confidence/_source) which are
dropped to the value-key projection before compare.

compare_table(gt_rows, ext_rows) -> dict
"""

from __future__ import annotations

from typing import Any

import contract as C
import normalize as N

CELL_KEYS = [k for k in C.ROW_VALUE_KEYS if k != C.ROW_ALIGN_KEY]


def _project(rows: list[dict[str, Any]]) -> "dict[str, dict[str, Any]]":
    """Index rows by normalized rowIndex, keep only value keys."""
    out: dict[str, dict[str, Any]] = {}
    for r in rows or []:
        idx = N.norm_index(r.get(C.ROW_ALIGN_KEY))
        if idx == "":
            continue
        out[idx] = {k: r.get(k) for k in C.ROW_VALUE_KEYS if k in r}
    return out


def compare_table(gt_rows: list[dict[str, Any]], ext_rows: list[dict[str, Any]]) -> dict[str, Any]:
    gt_by_idx = _project(gt_rows)
    ext_by_idx = _project(ext_rows)

    gt_keys = set(gt_by_idx)
    ext_keys = set(ext_by_idx)
    matched_idx = sorted(gt_keys & ext_keys, key=lambda s: int(s))
    gt_only = sorted(gt_keys - ext_keys, key=lambda s: int(s))   # rows extractor missed
    ext_only = sorted(ext_keys - gt_keys, key=lambda s: int(s))  # spurious extra rows

    cell_counts = {"scored": 0, "match": 0, "mismatch": 0, "ext_missing": 0, "gt_empty": 0}
    row_results: list[dict[str, Any]] = []

    for idx in matched_idx:
        g = gt_by_idx[idx]
        e = ext_by_idx[idx]
        cells: dict[str, dict[str, Any]] = {}
        row_match = True
        for key in CELL_KEYS:
            gv = g.get(key, "")
            ev = e.get(key, "")
            gn = N.normalize_cell(key, gv)
            en = N.normalize_cell(key, ev)
            if N.is_empty(gv):
                status = "gt_empty"
            elif N.is_empty(ev):
                status = "ext_missing"
            elif gn == en:
                status = "match"
            else:
                status = "mismatch"
            cells[key] = {"gt": gv, "ext": ev, "gtNorm": gn, "extNorm": en, "status": status}
            if status != "gt_empty":
                cell_counts["scored"] += 1
            cell_counts[status] = cell_counts.get(status, 0) + 1
            if status in ("mismatch", "ext_missing"):
                row_match = False
        row_results.append({"rowIndex": idx, "rowMatch": row_match, "cells": cells})

    scored = cell_counts["scored"]
    cell_accuracy = (cell_counts["match"] / scored) if scored else None
    return {
        "rowCountGt": len(gt_by_idx),
        "rowCountExt": len(ext_by_idx),
        "rowCountMatch": len(gt_by_idx) == len(ext_by_idx),
        "matchedRowIdx": matched_idx,
        "gtOnlyRowIdx": gt_only,     # extractor missed these rows (structural)
        "extOnlyRowIdx": ext_only,   # extractor invented these rows (structural)
        "rows": row_results,
        "cellCounts": cell_counts,
        "cellAccuracy": cell_accuracy,
    }
