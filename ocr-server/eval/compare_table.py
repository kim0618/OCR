"""compare_table — per-row / per-cell table comparison (Phase 3).

Aligns GT rows to extracted rows, then compares the value cells the GT row
provides (⓰), under frozen normalization, skipping GT-empty cells. excludedRows
are separated by the loader, so they can never be counted as misses.

Alignment (step 4):
  rowindex  rich GT carries a 1-based rowIndex → positional truth (unchanged).
  content   thin GT has NO rowIndex → align by itemName/amount/quantity
            similarity (B). This is also the algorithm the rich rowIndex set
            validates as a numeric oracle (➏, in p0_thin_check).
  auto      rowindex when every GT row has a usable rowIndex, else content.

compare_table(gt_rows, ext_rows, align="auto") -> dict
"""

from __future__ import annotations

from difflib import SequenceMatcher
from typing import Any

import contract as C
import normalize as N


def _value_keys(gt_row: dict[str, Any]) -> list[str]:
    """⓰ The cells we compare = the value keys the GT row provides (minus the
    alignment key and any review-meta). rich → its 8 value keys; thin → its war
    columns (itemName/quantity/unitPrice/amount/expiryDate/manufacturingNo)."""
    return [k for k in gt_row if k not in C.ROW_META_KEYS and k != C.ROW_ALIGN_KEY]


def _has_rowindex(row: dict[str, Any]) -> bool:
    return N.norm_index(row.get(C.ROW_ALIGN_KEY)) != ""


def _index(rows: list[dict[str, Any]]) -> "dict[str, dict[str, Any]]":
    """Index raw rows by normalized rowIndex; rows without one are skipped.

    #3 가드: 중복 rowIndex 가 오면 *첫 행을 유지*한다(기존엔 뒤 행이 앞 행을 조용히
    덮어써 행 하나가 비교에서 통째로 사라졌음 — 행 누락이 숨음). rich GT 는 rowIndex 가
    unique 라 동작 변화 없음. 파서가 중복 rowIndex 를 뱉는 경우에만 결정론적으로 첫 행 유지.
    """
    out: dict[str, dict[str, Any]] = {}
    for r in rows or []:
        idx = N.norm_index(r.get(C.ROW_ALIGN_KEY))
        if idx == "" or idx in out:
            continue
        out[idx] = r
    return out


def _align_by_rowindex(gt_rows, ext_rows):
    """Positional alignment by rowIndex (rich oracle / unchanged behavior)."""
    gt_by = _index(gt_rows)
    ext_by = _index(ext_rows)
    gk, ek = set(gt_by), set(ext_by)
    matched = sorted(gk & ek, key=lambda s: int(s))
    pairs = [(idx, gt_by[idx], ext_by[idx]) for idx in matched]
    gt_only = sorted(gk - ek, key=lambda s: int(s))
    ext_only = sorted(ek - gk, key=lambda s: int(s))
    return pairs, gt_only, ext_only, len(gt_by), len(ext_by)


def _row_similarity(g: dict[str, Any], e: dict[str, Any]) -> float:
    """Content similarity for B: itemName text + amount/quantity exact signals."""
    name_sim = SequenceMatcher(
        None, N.norm_text(g.get("itemName", "")), N.norm_text(e.get("itemName", ""))
    ).ratio()
    amt_g, amt_e = N.norm_amount(g.get("amount", "")), N.norm_amount(e.get("amount", ""))
    qty_g, qty_e = N.norm_qty(g.get("quantity", "")), N.norm_qty(e.get("quantity", ""))
    amt_match = 1.0 if amt_g and amt_g == amt_e else 0.0
    qty_match = 1.0 if qty_g and qty_g == qty_e else 0.0
    return 0.5 * name_sim + 0.35 * amt_match + 0.15 * qty_match


def _align_by_content(gt_rows, ext_rows, threshold: float = 0.30):
    """Greedy best-first content alignment (B). Each GT/ext row used at most once."""
    gt_rows = gt_rows or []
    ext_rows = ext_rows or []
    cands = []
    for gi, g in enumerate(gt_rows):
        for ei, e in enumerate(ext_rows):
            cands.append((_row_similarity(g, e), gi, ei))
    cands.sort(key=lambda t: (-t[0], t[1], t[2]))  # best score first, stable
    used_g: set[int] = set()
    used_e: set[int] = set()
    pairs_idx: list[tuple[int, int]] = []
    for score, gi, ei in cands:
        if score < threshold:
            break
        if gi in used_g or ei in used_e:
            continue
        used_g.add(gi)
        used_e.add(ei)
        pairs_idx.append((gi, ei))
    pairs_idx.sort()  # report in GT order
    pairs = []
    for gi, ei in pairs_idx:
        key = N.norm_index(ext_rows[ei].get(C.ROW_ALIGN_KEY)) or str(gi + 1)
        pairs.append((key, gt_rows[gi], ext_rows[ei]))
    gt_only = [str(gi + 1) for gi in range(len(gt_rows)) if gi not in used_g]
    ext_only = [N.norm_index(ext_rows[ei].get(C.ROW_ALIGN_KEY)) or str(ei + 1)
                for ei in range(len(ext_rows)) if ei not in used_e]
    return pairs, gt_only, ext_only, len(gt_rows), len(ext_rows)


def _gt_only_rows(gt_rows, gt_only, use_rowindex):
    """Return unmatched GT rows in the same key space used by the aligner."""
    if use_rowindex:
        gt_by = _index(gt_rows)
        return [(idx, gt_by[idx]) for idx in gt_only]
    return [(idx, gt_rows[int(idx) - 1]) for idx in gt_only]


def compare_table(gt_rows: list[dict[str, Any]], ext_rows: list[dict[str, Any]],
                  align: str = "auto") -> dict[str, Any]:
    if align == "auto":
        use_rowindex = bool(gt_rows) and all(_has_rowindex(r) for r in gt_rows)
    else:
        use_rowindex = align == "rowindex"

    if use_rowindex:
        pairs, gt_only, ext_only, n_gt, n_ext = _align_by_rowindex(gt_rows, ext_rows)
        align_mode = "rowIndex"
    else:
        pairs, gt_only, ext_only, n_gt, n_ext = _align_by_content(gt_rows, ext_rows)
        align_mode = "content"

    # `spurious` mirrors compare_fields: GT-empty cell the extractor filled anyway.
    # status stays "gt_empty" (cell recall unchanged); only a parallel tally is added.
    cell_counts = {"scored": 0, "match": 0, "mismatch": 0, "ext_missing": 0, "gt_empty": 0, "spurious": 0}
    row_results: list[dict[str, Any]] = []

    for row_key, g, e in pairs:
        cells: dict[str, dict[str, Any]] = {}
        row_match = True
        for key in _value_keys(g):
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
            spurious = N.is_empty(gv) and not N.is_empty(ev)
            cells[key] = {"gt": gv, "ext": ev, "gtNorm": gn, "extNorm": en, "status": status, "spurious": spurious}
            if key in C.MEASUREMENT_KEYS:
                continue  # 컬럼별 %만 리포트, 헤드라인 cellAccuracy/spurious/rowMatch엔 불참
            if status != "gt_empty":
                cell_counts["scored"] += 1
            cell_counts[status] = cell_counts.get(status, 0) + 1
            if spurious:
                cell_counts["spurious"] += 1
            if status in ("mismatch", "ext_missing"):
                row_match = False
        row_results.append({"rowIndex": row_key, "rowMatch": row_match, "cells": cells})

    # A structurally missing GT row is still part of cell recall.  Previously
    # these rows were exposed only through gtOnlyRowIdx, so every non-empty GT
    # cell in them disappeared from both the numerator and denominator.
    for row_key, g in _gt_only_rows(gt_rows, gt_only, use_rowindex):
        cells: dict[str, dict[str, Any]] = {}
        for key in _value_keys(g):
            gv = g.get(key, "")
            gn = N.normalize_cell(key, gv)
            status = "gt_empty" if N.is_empty(gv) else "ext_missing"
            cells[key] = {
                "gt": gv,
                "ext": "",
                "gtNorm": gn,
                "extNorm": "",
                "status": status,
                "spurious": False,
            }
            if key in C.MEASUREMENT_KEYS:
                continue  # 측정 컬럼은 헤드라인 집계 불참(위와 동일)
            if status != "gt_empty":
                cell_counts["scored"] += 1
            cell_counts[status] += 1
        row_results.append({
            "rowIndex": row_key,
            "rowMatch": False,
            "missingGtRow": True,
            "cells": cells,
        })

    scored = cell_counts["scored"]
    cell_accuracy = (cell_counts["match"] / scored) if scored else None
    return {
        "alignMode": align_mode,
        "rowCountGt": n_gt,
        "rowCountExt": n_ext,
        "rowCountMatch": n_gt == n_ext,
        "matchedRowIdx": [k for k, _, _ in pairs],
        "gtOnlyRowIdx": gt_only,     # extractor missed these rows (structural)
        "extOnlyRowIdx": ext_only,   # extractor invented these rows (structural)
        "rows": row_results,
        "cellCounts": cell_counts,
        "cellAccuracy": cell_accuracy,
    }
