"""REVIEW-SIGNAL Phase B: arithmetic consistency review flags.

Recomputes invoice arithmetic constraints at response-assembly time and emits
field-attributed flags (additive-only — no extractor logic touched). Works for
both the free and legacy invoice paths because it only reads document_fields.

Flag shape (flat list, frontend-friendly):
    {"scope": "document"|"row", "rowIndex": int|None,
     "fields": [...], "reason": str, "expected": str, "actual": str}

A flag means "these fields are mutually inconsistent — at least one is wrong",
not "this exact field is wrong". Frontend should mark all listed fields.
"""
from __future__ import annotations

import re
from typing import Any

# VAT rounding + OCR-of-printed-rounding slack (won).
_TOLERANCE = 2


def _num(value: Any) -> int | None:
    if not isinstance(value, str):
        return None
    cleaned = re.sub(r"[,\s원₩\\]", "", value.strip())
    if not cleaned or not re.fullmatch(r"-?\d+", cleaned):
        return None
    return int(cleaned)


def _close(a: int, b: int, tolerance: int = _TOLERANCE) -> bool:
    return abs(a - b) <= tolerance


def _flag(scope: str, fields: list[str], reason: str, expected: int, actual: int,
          row_index: int | None = None) -> dict[str, Any]:
    return {
        "scope": scope,
        "rowIndex": row_index,
        "fields": fields,
        "reason": reason,
        "expected": f"{expected:,}",
        "actual": f"{actual:,}",
    }


def build_review_flags(document_fields: dict[str, Any]) -> dict[str, Any]:
    flags: list[dict[str, Any]] = []
    df = document_fields or {}

    supply = _num(df.get("supplyAmount"))
    tax = _num(df.get("taxAmount"))
    total = _num(df.get("totalAmount"))

    # 1) document checksum: supply + tax = total
    if supply is not None and tax is not None and total is not None:
        if not _close(supply + tax, total):
            flags.append(_flag(
                "document", ["supplyAmount", "taxAmount", "totalAmount"],
                "checksum_supply_tax_total", supply + tax, total,
            ))

    rows = df.get("tableRows")
    rows = rows if isinstance(rows, list) else []
    row_supply_sum = 0
    row_supply_count = 0
    for idx, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        r_qty = _num(row.get("quantity"))
        r_unit = _num(row.get("unitPrice"))
        r_supply = _num(row.get("supplyAmount"))
        r_tax = _num(row.get("taxAmount"))
        # 2) row: quantity × unitPrice = supplyAmount
        if r_qty is not None and r_unit is not None and r_supply is not None:
            if not _close(r_qty * r_unit, r_supply):
                flags.append(_flag(
                    "row", ["quantity", "unitPrice", "supplyAmount"],
                    "row_qty_times_unit_price", r_qty * r_unit, r_supply,
                    row_index=idx,
                ))
        # 3) row: supplyAmount × 10% = taxAmount (Korean VAT)
        if r_supply is not None and r_tax is not None and r_tax > 0:
            if not _close(round(r_supply * 0.1), r_tax):
                flags.append(_flag(
                    "row", ["supplyAmount", "taxAmount"],
                    "row_vat_ten_percent", round(r_supply * 0.1), r_tax,
                    row_index=idx,
                ))
        if r_supply is not None:
            row_supply_sum += r_supply
            row_supply_count += 1

    # 4) column sum: Σ row supplyAmount = document supplyAmount.
    #    Only when every row contributed a parseable value — partial sums
    #    would false-positive on rows whose cell OCR simply failed.
    if rows and supply is not None and row_supply_count == len(rows) and row_supply_count > 0:
        if not _close(row_supply_sum, supply, tolerance=_TOLERANCE * len(rows)):
            flags.append(_flag(
                "document", ["supplyAmount"],
                "column_sum_supply", row_supply_sum, supply,
            ))

    return {"flags": flags, "method": "arithmetic.v1"}
