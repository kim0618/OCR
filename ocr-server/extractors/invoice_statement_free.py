"""Scaffold for unstructured invoice statement extraction.

This module is intentionally not wired into ``main.py`` yet.

Fallback policy:
- The future dispatcher must catch exceptions from this module.
- If this scaffold returns an empty or low-confidence result, the dispatcher
  should fall back to ``extract_invoice_statement_fields`` from the existing
  ``invoice_statement.py`` path until parity is proven.
- This module must not access FastAPI request/response objects, the OCR
  singleton, template storage, review logs, frontend files, or datasets.
"""

from __future__ import annotations

from copy import deepcopy
import math
import os
import re
from typing import Any


TABLE_ROW_KEYS = (
    "rowIndex",
    "itemCode",
    "itemName",
    "spec",
    "lotNo",
    "serialNo",
    "manufacturingNo",
    "expiryDate",
    "quantity",
    "unit",
    "unitPrice",
    "supplyAmount",
    "taxAmount",
    "amount",
    "totalAmount",
    "manufacturer",
    "insuranceCode",
    "remark",
    "_rawText",
    "_confidence",
    "_source",
)


DOCUMENT_FIELD_KEYS = (
    "supplierCompany",
    "supplierBizNumber",
    "supplierRepresentative",
    "supplierAddress",
    "buyerCompany",
    "buyerBizNumber",
    "buyerRepresentative",
    "buyerAddress",
    "issueDate",
    "supplyAmount",
    "taxAmount",
    "totalAmount",
    "subtotal",
    "cumulativeAmount",
    "previousBalance",
    "transactionAmount",
    "cumulativeBalance",
    "totalQuantity",
    "tableDetected",
    "rowCount",
    "firstRowPreview",
    "tableRows",
    "tableMeta",
)


# BACKEND-INVOICE-FREE-4D: party/summary scalar keys reused from the existing
# invoice_statement.py parser. The free parser fills these poorly on its own, so
# on a free-parser success we backfill empties from extract_invoice_statement_fields.
REFERENCE_SCALAR_MERGE_KEYS = (
    "supplierBizNumber",
    "supplierCompany",
    "supplierAddress",
    "supplierRepresentative",
    "buyerBizNumber",
    "buyerCompany",
    "buyerAddress",
    "buyerRepresentative",
    "totalAmount",
    "cumulativeAmount",
    "supplyAmount",
    "taxAmount",
    "issueDate",
)
# Table contract is owned by the free parser; reference values for these keys must
# never overwrite the free result (tableRows/tableMeta merge exclusion).
REFERENCE_SCALAR_MERGE_EXCLUDED_KEYS = (
    "tableRows",
    "tableMeta",
    "tableDetected",
    "rowCount",
    "firstRowPreview",
)


REQUIRED_TABLE_ROW_KEYS = ("itemName", "spec", "quantity", "unitPrice", "amount")
FORBIDDEN_FREE_TOP_LEVEL_KEYS = (
    "freeInvoiceRows",
    "freeInvoiceFields",
    "invoiceFreeResult",
    "invoiceStatementFreeRows",
    "freeTables",
)
FORBIDDEN_FREE_ROW_KEYS = (
    "col1",
    "col2",
    "col3",
    "freeItemName",
    "freeAmount",
    "invoiceFreeRow",
)

PRODUCT_CODE_TOKEN_RE = re.compile(r"^[A-Z]{2,}[\dA-Z]+$")
CODE_VS_MONEY_COMMA_MONEY_RE = re.compile(r"^-?\d{1,3}(,\d{3})+$")
CODE_VS_MONEY_GROUPED_MIXED_RE = re.compile(r"^-?\d{1,3}([.,]\d{3})+$")
CODE_VS_MONEY_DATE_RE = re.compile(r"^\d{4}/\d{2}/\d{2}$|^\d{2}/\d{2}/\d{2}")
CODE_VS_MONEY_PHONE_RE = re.compile(r"^0\d-\d{3,4}-\d{4}$")
CODE_VS_MONEY_BIZNO_RE = re.compile(r"^\d{3}-\d{2}-\d{5}$")
CODE_VS_MONEY_ZIP_RE = re.compile(r"^0\d{4}$")
CODE_VS_MONEY_HYPHEN_NUM_RE = re.compile(r"^\d+-\d+$")
CODE_VS_MONEY_PURE_NUM_RE = re.compile(r"^\d+$")


def _empty_table_meta() -> dict[str, Any]:
    return {
        "rowCount": 0,
        "columns": [],
        "columnLabels": {},
        "extractionSource": "invoice_statement_free_scaffold",
        "expectedColumnsUsed": False,
        "tableBoundsUsed": False,
        "columnGuidesReceived": False,
        "columnGuidesUsed": False,
        "columnGuidesCount": 0,
        "valueMappingWarnings": [],
        "scaffold": True,
    }


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return " ".join(value.replace("\r", "\n").split())
    if isinstance(value, (int, float)):
        return str(value)
    return ""


def _looks_like_product_code_token(value: Any) -> bool:
    """Detect compact product-code tokens that should not be merged into itemName."""
    text = _normalize_text(value).strip()
    if len(text) < 4:
        return False
    if not PRODUCT_CODE_TOKEN_RE.fullmatch(text):
        return False
    if not any(ch.isdigit() for ch in text):
        return False
    return True


def _classify_numeric_like_token(text: Any, context: dict[str, Any] | None = None) -> dict[str, Any]:
    """Classify code-vs-money token shapes before creating money candidates.

    FULL_UNSTRUCTURED_INVOICE_4E_CODE_VS_MONEY_HELPER_PATCH: this helper is a
    conservative pre-filter only. Comma-grouped money is always preserved, while
    clear product/order/id/date shapes are kept out of money candidate lists.
    """
    del context
    if text is None:
        return {
            "class": "unknown",
            "confidence": "low",
            "reason": "none_input",
            "preserveAsMoney": False,
        }
    token = _normalize_text(text).strip("()[]{}:;|")
    if not token:
        return {
            "class": "unknown",
            "confidence": "low",
            "reason": "empty_input",
            "preserveAsMoney": False,
        }

    if CODE_VS_MONEY_COMMA_MONEY_RE.fullmatch(token):
        return {
            "class": "real_money",
            "confidence": "high",
            "reason": "comma_grouped_numeric",
            "preserveAsMoney": True,
        }
    if CODE_VS_MONEY_GROUPED_MIXED_RE.fullmatch(token):
        return {
            "class": "real_money",
            "confidence": "medium",
            "reason": "grouped_numeric_ocr_separator_noise",
            "preserveAsMoney": True,
        }
    if CODE_VS_MONEY_DATE_RE.match(token):
        return {
            "class": "date_like",
            "confidence": "high",
            "reason": "date_pattern",
            "preserveAsMoney": False,
        }
    if CODE_VS_MONEY_PHONE_RE.fullmatch(token):
        return {
            "class": "phone_like",
            "confidence": "high",
            "reason": "phone_pattern",
            "preserveAsMoney": False,
        }
    if CODE_VS_MONEY_BIZNO_RE.fullmatch(token):
        return {
            "class": "biz_number_like",
            "confidence": "high",
            "reason": "biz_number_pattern",
            "preserveAsMoney": False,
        }
    if CODE_VS_MONEY_ZIP_RE.fullmatch(token):
        return {
            "class": "page_or_metadata",
            "confidence": "medium",
            "reason": "zip_code_pattern",
            "preserveAsMoney": False,
        }

    upper = token.upper()
    if re.fullmatch(r"\d+(?:ML|MG|G|T|TAB|CAP|P|EA|BOX|DOSE)", upper) or re.search(
        r"\d+(?:ML|MG|M|G)[*X|]+\d+", upper
    ):
        return {
            "class": "quantity_like",
            "confidence": "medium",
            "reason": "unit_or_spec_quantity",
            "preserveAsMoney": False,
        }
    if re.search(r"[가-힣]", token):
        return {
            "class": "unknown",
            "confidence": "low",
            "reason": "hangul_numeric_mixed_shape",
            "preserveAsMoney": False,
        }

    has_alpha = bool(re.search(r"[A-Za-z]", token))
    has_digit = any(ch.isdigit() for ch in token)
    if has_alpha and has_digit and "," not in token:
        if "-" in token and re.search(r"[O0]P-|[A-Z]-", upper):
            return {
                "class": "order_code",
                "confidence": "high",
                "reason": "alpha_hyphen_digit_order_code",
                "preserveAsMoney": False,
            }
        if "-" in token:
            return {
                "class": "order_code",
                "confidence": "medium",
                "reason": "alpha_hyphen_digit_order_code",
                "preserveAsMoney": False,
            }
        return {
            "class": "product_code",
            "confidence": "high",
            "reason": "alpha_digit_product_code",
            "preserveAsMoney": False,
        }

    if CODE_VS_MONEY_HYPHEN_NUM_RE.fullmatch(token):
        return {
            "class": "lot_or_serial",
            "confidence": "medium",
            "reason": "hyphenated_numeric_serial",
            "preserveAsMoney": False,
        }
    if CODE_VS_MONEY_PURE_NUM_RE.fullmatch(token):
        if len(token) <= 3:
            return {
                "class": "quantity_like",
                "confidence": "medium",
                "reason": "short_pure_numeric",
                "preserveAsMoney": False,
            }
        if len(token) >= 6:
            return {
                "class": "lot_or_serial",
                "confidence": "low",
                "reason": "long_pure_numeric_no_grouping",
                "preserveAsMoney": False,
            }
        return {
            "class": "unknown",
            "confidence": "low",
            "reason": "mid_pure_numeric_ungrouped",
            "preserveAsMoney": False,
        }

    return {
        "class": "unknown",
        "confidence": "low",
        "reason": "unresolved_shape",
        "preserveAsMoney": False,
    }


def _code_vs_money_container_token(text: str, start: int, end: int) -> str:
    left = start
    while left > 0 and not text[left - 1].isspace():
        left -= 1
    right = end
    while right < len(text) and not text[right].isspace():
        right += 1
    return text[left:right].strip()


def _is_code_like_non_money_token(value: Any) -> bool:
    classification = _classify_numeric_like_token(value)
    return (
        not classification.get("preserveAsMoney")
        and classification.get("class")
        in {"product_code", "order_code", "lot_or_serial", "date_like", "biz_number_like", "phone_like", "page_or_metadata"}
    )


def _build_code_vs_money_diagnostics(text: str) -> dict[str, Any]:
    summary = {
        "enabled": True,
        "removedCount": 0,
        "removedExamples": [],
        "preservedMoneyCount": 0,
        "unknownCount": 0,
    }
    seen_removed: set[str] = set()
    seen_tokens: set[str] = set()
    for raw in re.findall(r"\S*\d\S*", _normalize_text(text)):
        token = raw.strip("()[]{}:;|")
        if not token or token in seen_tokens:
            continue
        seen_tokens.add(token)
        classification = _classify_numeric_like_token(token)
        if classification.get("preserveAsMoney"):
            summary["preservedMoneyCount"] += 1
        elif classification.get("class") in {"product_code", "order_code"}:
            summary["removedCount"] += 1
            if token not in seen_removed and len(summary["removedExamples"]) < 8:
                seen_removed.add(token)
                summary["removedExamples"].append(
                    {
                        "text": token[:40],
                        "class": classification.get("class"),
                        "reason": classification.get("reason"),
                    }
                )
        elif classification.get("class") == "unknown":
            summary["unknownCount"] += 1
    return summary


def _bbox_metrics(bbox: Any) -> dict[str, float] | None:
    points: list[tuple[float, float]] = []
    if isinstance(bbox, (list, tuple)):
        if len(bbox) == 4 and all(isinstance(v, (int, float)) for v in bbox):
            x, y, w, h = bbox
            points = [(float(x), float(y)), (float(x) + float(w), float(y) + float(h))]
        else:
            for point in bbox:
                if isinstance(point, (list, tuple)) and len(point) >= 2:
                    x, y = point[0], point[1]
                    if isinstance(x, (int, float)) and isinstance(y, (int, float)):
                        points.append((float(x), float(y)))
    if not points:
        return None
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    x0, x1 = min(xs), max(xs)
    y0, y1 = min(ys), max(ys)
    return {
        "x": x0,
        "y": y0,
        "cx": (x0 + x1) / 2,
        "cy": (y0 + y1) / 2,
        "w": max(0.0, x1 - x0),
        "h": max(0.0, y1 - y0),
    }


def _extract_text_from_ocr_line(line: Any) -> tuple[str, Any, Any]:
    if isinstance(line, dict):
        text = _normalize_text(
            line.get("text")
            or line.get("value")
            or line.get("description")
            or line.get("lineText")
        )
        bbox = line.get("bbox") or line.get("box") or line.get("points") or line.get("poly")
        return text, bbox, line.get("confidence") or line.get("conf") or line.get("score")
    if isinstance(line, str):
        return _normalize_text(line), None, None
    if isinstance(line, (list, tuple)):
        if len(line) >= 2:
            return _normalize_text(line[1]), line[0], line[2] if len(line) >= 3 else None
        if len(line) == 1:
            return _normalize_text(line[0]), None, None
    return "", None, None


def _extract_ocr_line_items(ocr_lines_raw: Any) -> list[dict[str, Any]]:
    if not isinstance(ocr_lines_raw, (list, tuple)):
        return []
    items: list[dict[str, Any]] = []
    for line in ocr_lines_raw:
        text, bbox, confidence = _extract_text_from_ocr_line(line)
        if not text:
            continue
        metrics = _bbox_metrics(bbox)
        item: dict[str, Any] = {"text": text, "confidence": confidence}
        if metrics:
            item.update(metrics)
        items.append(item)
    return items


def _build_token_bbox_debug(
    ocr_items: list[dict[str, Any]],
    ocr_w: int | float | None,
    ocr_h: int | float | None,
    *,
    max_tokens: int = 300,
) -> dict[str, Any]:
    def _finite_number(value: Any) -> float | None:
        if not isinstance(value, (int, float)):
            return None
        number = float(value)
        return number if math.isfinite(number) else None

    width = _finite_number(ocr_w)
    height = _finite_number(ocr_h)
    tokens: list[dict[str, Any]] = []
    for item in ocr_items:
        x = _finite_number(item.get("x"))
        y = _finite_number(item.get("y"))
        w = _finite_number(item.get("w"))
        h = _finite_number(item.get("h"))
        cx = _finite_number(item.get("cx"))
        cy = _finite_number(item.get("cy"))
        if None in (x, y, w, h, cx, cy):
            continue
        token = {
            "text": _normalize_text(item.get("text")),
            "bbox": {"x": x, "y": y, "w": w, "h": h},
            "cx": cx,
            "cy": cy,
            "confidence": item.get("confidence") if item.get("confidence") is not None else None,
        }
        tokens.append(token)

    token_count = len(ocr_items)
    finite_token_count = len(tokens)
    cap = max(1, int(max_tokens or 300))
    emitted = tokens[:cap]
    return {
        "available": True,
        "source": "ocr_items",
        "imageSize": {"width": width, "height": height},
        "tokenCount": token_count,
        "finiteTokenCount": finite_token_count,
        "emittedTokenCount": len(emitted),
        "maxTokenCap": cap,
        "truncated": finite_token_count > len(emitted),
        "tokens": emitted,
    }


def _build_gt_skeleton_candidates(
    ocr_items: list[dict[str, Any]],
    ocr_w: int | float | None,
    ocr_h: int | float | None,
    *,
    doc_type: str = "invoice_statement",
    max_rows: int = 20,
) -> dict[str, Any]:
    def _finite_number(value: Any) -> float | None:
        if not isinstance(value, (int, float)):
            return None
        number = float(value)
        return number if math.isfinite(number) else None

    def _finite_item(item: dict[str, Any]) -> dict[str, Any] | None:
        x = _finite_number(item.get("x"))
        y = _finite_number(item.get("y"))
        w = _finite_number(item.get("w"))
        h = _finite_number(item.get("h"))
        cx = _finite_number(item.get("cx"))
        cy = _finite_number(item.get("cy"))
        if None in (x, y, w, h, cx, cy):
            return None
        return {
            "text": _normalize_text(item.get("text")),
            "confidence": item.get("confidence") if item.get("confidence") is not None else None,
            "x": x,
            "y": y,
            "w": w,
            "h": h,
            "cx": cx,
            "cy": cy,
        }

    def _box_contains(box: dict[str, float], item: dict[str, Any]) -> bool:
        return (
            box["x"] <= float(item["cx"]) <= box["x"] + box["w"]
            and box["y"] <= float(item["cy"]) <= box["y"] + box["h"]
        )

    def _looks_like_code_anchor(text: Any) -> bool:
        value = _normalize_text(text).upper().replace(" ", "")
        if not value or "," in value:
            return False
        return bool(re.search(r"(?:^|\d)(?:O|0)?P-[A-Z0-9]{2,}", value) or re.search(r"\d+(?:O|0)P-[A-Z0-9]{2,}", value))

    def _amount_anchor_value(text: Any) -> str:
        value = _normalize_text(text)
        if not value or _looks_like_code_anchor(value) or _is_code_like_non_money_token(value):
            return ""
        money_tokens = _money_tokens_from_text(value)
        if not money_tokens:
            return ""
        return _normalize_money(money_tokens[-1])

    def _anchor_counts_for_box(box: dict[str, float], items: list[dict[str, Any]]) -> tuple[int, int]:
        inside = [item for item in items if _box_contains(box, item)]
        return (
            sum(1 for item in inside if _looks_like_code_anchor(item.get("text"))),
            sum(1 for item in inside if _amount_anchor_value(item.get("text"))),
        )

    if doc_type != "invoice_statement":
        return {
            "available": False,
            "source": "template_box_code_amount_anchor",
            "mode": "debug_gt_skeleton_only",
            "reason": "non_invoice_statement",
            "releaseImpact": "none",
            "rows": [],
        }

    width = _finite_number(ocr_w)
    height = _finite_number(ocr_h)
    finite_items = [item for item in (_finite_item(raw) for raw in ocr_items) if item is not None]
    if not finite_items or width is None or height is None:
        return {
            "available": False,
            "source": "template_box_code_amount_anchor",
            "mode": "debug_gt_skeleton_only",
            "reason": "missing_finite_token_bbox_or_image_size",
            "releaseImpact": "none",
            "rows": [],
        }

    template_source = {"width": 1654.0, "height": 2338.0}
    template_box = {"x": 112.0, "y": 599.0, "w": 1468.0, "h": 1134.0}
    scale_x_direct = width / template_source["width"]
    scale_y_direct = height / template_source["height"]
    direct_box = {
        "x": template_box["x"] * scale_x_direct,
        "y": template_box["y"] * scale_y_direct,
        "w": template_box["w"] * scale_x_direct,
        "h": template_box["h"] * scale_y_direct,
    }

    rotated_source = {"width": template_source["height"], "height": template_source["width"]}
    scale_x_rot = width / rotated_source["width"]
    scale_y_rot = height / rotated_source["height"]
    rotated_box = {
        "x": (template_source["height"] - (template_box["y"] + template_box["h"])) * scale_x_rot,
        "y": template_box["x"] * scale_y_rot,
        "w": template_box["h"] * scale_x_rot,
        "h": template_box["w"] * scale_y_rot,
    }

    candidates = [
        ("scaled", direct_box, scale_x_direct, scale_y_direct),
        ("scaled_rotated_clockwise", rotated_box, scale_x_rot, scale_y_rot),
    ]
    scored_boxes: list[tuple[str, dict[str, float], float, float, int, int]] = []
    for status, box, sx, sy in candidates:
        code_count, amount_count = _anchor_counts_for_box(box, finite_items)
        scored_boxes.append((status, box, sx, sy, code_count, amount_count))
    status, table_box, scale_x, scale_y, _, _ = max(scored_boxes, key=lambda item: (item[4] + item[5], item[4], item[5]))

    inside_items = [item for item in finite_items if _box_contains(table_box, item)]
    code_anchors = [
        {"text": item["text"], "cx": item["cx"], "cy": item["cy"], "confidence": item.get("confidence")}
        for item in inside_items
        if _looks_like_code_anchor(item.get("text"))
    ]
    amount_anchors = [
        {"text": _amount_anchor_value(item["text"]), "rawText": item["text"], "cx": item["cx"], "cy": item["cy"], "confidence": item.get("confidence")}
        for item in inside_items
        if _amount_anchor_value(item.get("text"))
    ]

    code_anchors.sort(key=lambda anchor: (float(anchor["cx"]), float(anchor["cy"])))
    amount_anchors.sort(key=lambda anchor: (float(anchor["cx"]), float(anchor["cy"])))
    used_amounts: set[int] = set()
    rows: list[dict[str, Any]] = []
    paired_count = 0
    orphan_code_count = 0
    for code in code_anchors[:max_rows]:
        best_idx = None
        best_distance = None
        for idx, amount in enumerate(amount_anchors):
            if idx in used_amounts:
                continue
            distance = abs(float(amount["cx"]) - float(code["cx"])) + (abs(float(amount["cy"]) - float(code["cy"])) * 0.1)
            if best_distance is None or distance < best_distance:
                best_idx = idx
                best_distance = distance
        amount = amount_anchors[best_idx] if best_idx is not None and best_distance is not None and best_distance <= 75.0 else None
        missing = []
        notes = ["debug_only_not_release_table_row"]
        confidence = "medium"
        if amount is None:
            orphan_code_count += 1
            missing.append("amount")
            notes.append("orphan_code_anchor")
            confidence = "low"
        else:
            used_amounts.add(best_idx)  # type: ignore[arg-type]
            paired_count += 1
        rows.append(
            {
                "rowIndex": len(rows),
                "itemName": "",
                "spec": "",
                "productCode": code["text"],
                "lotNo": "",
                "expiryDate": "",
                "quantity": "",
                "unitPrice": "",
                "amount": amount["text"] if amount else "",
                "_gtSkeleton": {
                    "reviewRequired": True,
                    "rowConfidence": confidence,
                    "anchors": {
                        "code": {"text": code["text"], "cx": code["cx"], "cy": code["cy"]},
                        "amount": {"text": amount["text"], "cx": amount["cx"], "cy": amount["cy"]} if amount else None,
                    },
                    "missingAnchors": missing,
                    "notes": notes,
                },
            }
        )

    balance_excluded = sum(
        1
        for item in finite_items
        if not _box_contains(table_box, item)
        and _amount_anchor_value(item.get("text"))
        and ("합계" in item.get("text", "") or "balance" in item.get("text", "").lower() or float(item.get("cx", 0.0)) < table_box["x"])
    )
    row_count = len(rows)
    available = 8 <= len(code_anchors) and row_count > 0
    return {
        "available": available,
        "source": "template_box_code_amount_anchor",
        "mode": "debug_gt_skeleton_only",
        "templateName": "거래_2",
        "templateId": "TPL-5A8C2374",
        "releaseImpact": "none",
        "rowCount": row_count,
        "expectedRowRange": "12-13",
        "coordinateAlignment": {
            "status": status if available else "uncertain",
            "ocrImageSize": {"width": width, "height": height},
            "templateSourceSize": template_source,
            "scaleX": scale_x,
            "scaleY": scale_y,
            "tableBoxUsed": {key: round(value, 3) for key, value in table_box.items()},
            "scoredBoxes": [
                {
                    "status": scored[0],
                    "codeCount": scored[4],
                    "amountCount": scored[5],
                    "tableBox": {key: round(value, 3) for key, value in scored[1].items()},
                }
                for scored in scored_boxes
            ],
        },
        "anchorSummary": {
            "codeCount": len(code_anchors),
            "amountCount": len(used_amounts),
            "rawAmountCandidateCount": len(amount_anchors),
            "pairedCount": paired_count,
            "orphanCodeCount": orphan_code_count,
            "orphanAmountCount": max(0, len(amount_anchors) - len(used_amounts)),
            "balanceExcludedCount": balance_excluded,
        },
        "candidateRowsReleaseIsolated": True,
        "rows": rows,
    }


def _extract_line_texts(ocr_lines_raw: Any) -> list[str]:
    out: list[str] = []
    for item in _extract_ocr_line_items(ocr_lines_raw):
        text = _normalize_text(item.get("text"))
        if text:
            out.append(text)
    return out


def _join_lines(lines: list[str]) -> str:
    return "\n".join(_normalize_text(line) for line in lines if _normalize_text(line))


def _unique_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        v = _normalize_text(value)
        if not v or v in seen:
            continue
        seen.add(v)
        out.append(v)
    return out


def _find_business_numbers(text: str) -> list[str]:
    normalized = _normalize_text(text)
    candidates: list[str] = []
    candidates.extend(re.findall(r"\b\d{3}-\d{2}-\d{5}\b", normalized))
    for raw in re.findall(r"(?<!\d)\d{10}(?!\d)", normalized):
        candidates.append(f"{raw[:3]}-{raw[3:5]}-{raw[5:]}")
    return _unique_preserve_order(candidates)


def _clean_labeled_value(value: str) -> str:
    cleaned = re.sub(r"^[\s:：\-|]+", "", value or "")
    cleaned = re.sub(r"^(?:상호|회사명|업체명|공급자|공급\s*자|공급받는자|받는자)\s*[:：\-]?\s*", "", cleaned)
    cleaned = re.split(r"\s{2,}|사업자|등록|번호|대표|전화|주소|합계|총액", cleaned, maxsplit=1)[0]
    return _normalize_text(cleaned).strip(" :：-|")


def _find_company_candidates(lines: list[str]) -> list[str]:
    candidates: list[str] = []
    label_patterns = (
        r"(?:공급자|공급\s*자|상호|회사명|업체명)\s*[:：\-]?\s*(?P<value>[^\n]{2,40})",
        r"(?:공급받는자|받는자)\s*[:：\-]?\s*(?P<value>[^\n]{2,40})",
    )
    for line in lines:
        text = _normalize_text(line)
        for pattern in label_patterns:
            match = re.search(pattern, text)
            if not match:
                continue
            value = _clean_labeled_value(match.group("value"))
            if value and not re.fullmatch(r"[\d\s\-.,]+", value):
                candidates.append(value)
    return _unique_preserve_order(candidates)


def _find_amount_candidates(text: str) -> list[str]:
    normalized = _normalize_text(text)
    candidates: list[str] = []
    pattern = re.compile(
        r"(?:합계|총액|청구금액|공급대가|총\s*합계|합계금액)\s*[:：\-]?\s*"
        r"(?P<amount>\d{1,3}(?:,\d{3})+|\d{4,})"
    )
    for match in pattern.finditer(normalized):
        candidates.append(match.group("amount"))
    return _unique_preserve_order(candidates)


def _is_number_token(value: str) -> bool:
    token = _normalize_text(value).strip("()[]{}.,:;|")
    token = token.replace("￦", "").replace("₩", "").replace("원", "")
    return bool(re.fullmatch(r"-?\d+(?:,\d{3})*(?:\.\d+)?", token))


def _clean_number_token(value: str) -> str:
    return _normalize_text(value).strip("()[]{}.,:;|").replace("￦", "").replace("₩", "").replace("원", "")


def _normalize_comma_space_money_text(value: Any) -> str:
    text = _normalize_text(value)
    if not text:
        return ""
    return re.sub(r"(?<!\d)(-?\d{1,3}),\s+(\d{3})(?!\d)", r"\1,\2", text)


def _merge_comma_space_money_tokens(tokens: list[str]) -> list[str]:
    merged: list[str] = []
    idx = 0
    while idx < len(tokens):
        token = _normalize_text(tokens[idx])
        next_token = _normalize_text(tokens[idx + 1]) if idx + 1 < len(tokens) else ""
        if re.fullmatch(r"-?\d{1,3},", token) and re.fullmatch(r"\d{3}", next_token):
            merged.append(f"{token}{next_token}")
            idx += 2
            continue
        merged.append(token)
        idx += 1
    return merged


def _normalize_item_name(value: Any) -> str:
    return _normalize_text(value).strip()


def _normalize_spec(value: Any) -> str:
    text = _normalize_text(value).strip()
    text = re.sub(r"\s*\*\s*", "*", text)
    text = re.sub(r"(?<=\d)\s+(?=[A-Za-z])", "", text)
    text = re.sub(r"(?<=[A-Za-z])\s+(?=\()", "", text)
    return text


def _is_date_like_number(value: Any) -> bool:
    text = _clean_number_token(_normalize_text(value)).replace(",", "")
    return bool(re.fullmatch(r"(?:19|20)?\d{6}", text) or re.fullmatch(r"\d{8}", text))


def _is_lot_or_manufacturing_like_number(value: Any) -> bool:
    text = _clean_number_token(_normalize_text(value)).replace(",", "")
    return bool(re.fullmatch(r"\d{5,}", text)) and not _is_date_like_number(text)


def _normalize_quantity(value: Any) -> str:
    text = _clean_number_token(_normalize_text(value)).replace(",", "")
    if not text:
        return ""
    if re.fullmatch(r"\d+(?:\.0+)?", text):
        return text.split(".", 1)[0]
    return text


def _normalize_money(value: Any) -> str:
    text = _clean_number_token(_normalize_text(value))
    if not text:
        return ""
    return text if re.fullmatch(r"-?\d+(?:,\d{3})*(?:\.\d+)?", text) else _normalize_text(value)


def _number_value(value: Any) -> float | None:
    token = _clean_number_token(_normalize_text(value)).replace(",", "")
    if not token or not re.fullmatch(r"-?\d+(?:\.\d+)?", token):
        return None
    try:
        return float(token)
    except ValueError:
        return None


def _money_parse_value(value: Any) -> float | None:
    if _is_date_like_number(value):
        return None
    return _number_value(_normalize_money(value))


def _looks_like_money_token(value: Any) -> bool:
    text = _clean_number_token(_normalize_text(value))
    number = _number_value(text)
    if number is None:
        return False
    return "," in text or number >= 100


def _looks_like_quantity_token(value: Any) -> bool:
    text = _clean_number_token(_normalize_text(value)).replace(",", "")
    if not re.fullmatch(r"\d{1,4}(?:\.\d+)?", text):
        return False
    number = _number_value(text)
    return number is not None and 0 < number <= 9999


def _looks_like_spec_token(value: Any) -> bool:
    text = _normalize_text(value)
    if not text:
        return False
    if re.search(r"\d+\s*(?:T|TAB|CAP|EA|BOX|ML|MG|G|DOSE)\b", text, re.IGNORECASE):
        return True
    if re.search(r"\d+(?:ml|mg|g)\s*[*xX]\s*\d+", text, re.IGNORECASE):
        return True
    if re.search(r"\d+[A-Za-z|]*[*xX]\d+", text):
        return True
    return bool(re.search(r"\d", text) and re.search(r"[A-Za-z]", text) and len(text) <= 20)


def _looks_like_lot_code_with_unit_suffix(value: Any) -> bool:
    text = _normalize_text(value).strip("()[]{}.,:;|")
    if not text:
        return False
    compact = re.sub(r"\s+", "", text).upper()
    if "," in compact or _is_date_like_number(compact):
        return False
    if not compact.endswith("EA") or "-" not in compact:
        return False
    return bool(re.fullmatch(r"(?=.*\d)[A-Z0-9]+(?:-[A-Z0-9]+)*-\d+EA", compact))


def _looks_like_item_name_spec_tail(value: Any) -> bool:
    text = _normalize_spec(value).strip("()[]{}.,:;|")
    if not text or len(text) > 20:
        return False
    if _looks_like_lot_code_with_unit_suffix(text):
        return False
    if _money_parse_value(text) is not None and not re.search(r"[A-Za-z]", text):
        return False
    upper = text.upper()
    if re.fullmatch(r"\d+(?:\.\d+)?(?:T|C|CAP|TAB|DOSE|ML|MI|M[I1L]|MG|NG|G|N1)", upper):
        return True
    if re.fullmatch(r"\d+(?:ML|MG|G)\s*[*X]\s*\d+", upper):
        return True
    return _looks_like_spec_token(text)


def _split_item_name_spec_tail(value: Any) -> tuple[str, str] | None:
    text = _normalize_item_name(value)
    if not text:
        return None
    parts = text.rsplit(None, 1)
    if len(parts) != 2:
        return None
    item_name, tail = parts[0].strip(), _normalize_spec(parts[1])
    if not item_name or not _looks_like_item_name_spec_tail(tail):
        return None
    return item_name, tail


def _money_tokens_from_text(value: Any) -> list[str]:
    text = _normalize_comma_space_money_text(value)
    if not text:
        return []
    tokens: list[str] = []
    for match in re.finditer(r"(?<!\d)(?:-?\d{1,3}(?:,\d{3})+|-?\d{4,})(?!\d)", text):
        token = _clean_number_token(match.group(0))
        if not token:
            continue
        # FULL_UNSTRUCTURED_INVOICE_4E_CODE_VS_MONEY_HELPER_PATCH:
        # when a numeric regex match is embedded in a product/order code
        # (OP-NA0300, 0P-NA0300, INAP250G, NRFS75M), keep the code out of the
        # money candidate list without changing release or segmentation logic.
        container = _code_vs_money_container_token(text, match.start(), match.end())
        if container and container != token and _is_code_like_non_money_token(container):
            continue
        if "," not in token and _is_date_like_number(token):
            continue
        if _money_parse_value(token) is not None:
            tokens.append(token)
    return tokens


def _split_merged_money_pair(value: Any) -> tuple[str, str] | None:
    tokens = _money_tokens_from_text(value)
    if len(tokens) < 2:
        return None
    return _normalize_money(tokens[-2]), _normalize_money(tokens[-1])


def _candidate_item_name_from_raw_text(value: Any) -> str:
    text = _normalize_text(value)
    if not text or _is_summary_or_header_line(text):
        return ""
    tokens = text.split()
    if not tokens:
        return ""
    stop_idx = len(tokens)
    for idx, token in enumerate(tokens):
        if idx == 0:
            continue
        cleaned = _clean_number_token(token)
        if _is_number_token(token):
            stop_idx = idx
            break
        if _looks_like_spec_token(token):
            stop_idx = idx
            break
        if cleaned and (_is_date_like_number(cleaned) or _is_lot_or_manufacturing_like_number(cleaned)):
            stop_idx = idx
            break
    candidate = " ".join(tokens[:stop_idx]).strip()
    return candidate if _has_item_name_signal(candidate) else ""


def _repair_candidate_column_split(row: dict[str, Any], source: dict[str, Any]) -> dict[str, Any]:
    repaired = dict(row)
    unit_price = _normalize_text(repaired.get("unitPrice"))
    amount = _normalize_text(repaired.get("amount"))
    if not amount:
        split = _split_merged_money_pair(unit_price)
        if split:
            repaired["unitPrice"], repaired["amount"] = split
    elif not unit_price:
        split = _split_merged_money_pair(amount)
        if split:
            repaired["unitPrice"], repaired["amount"] = split

    raw_text = _normalize_text(source.get("_rawText") or repaired.get("_rawText"))
    if raw_text:
        raw_money_tokens = _money_tokens_from_text(raw_text)
        if len(raw_money_tokens) >= 2:
            if not _normalize_text(repaired.get("unitPrice")):
                repaired["unitPrice"] = _normalize_money(raw_money_tokens[-2])
            if not _normalize_text(repaired.get("amount")):
                repaired["amount"] = _normalize_money(raw_money_tokens[-1])

    if not _normalize_text(repaired.get("itemName")):
        repaired["itemName"] = _candidate_item_name_from_raw_text(raw_text)

    if (
        not _normalize_text(repaired.get("lotNo"))
        and _looks_like_lot_code_with_unit_suffix(repaired.get("spec"))
        and (_money_parse_value(repaired.get("unitPrice")) is not None or _money_parse_value(repaired.get("amount")) is not None)
    ):
        split = _split_item_name_spec_tail(repaired.get("itemName"))
        if split:
            repaired["itemName"], repaired["spec"] = split
            repaired["lotNo"] = _normalize_text(row.get("spec"))
    return repaired


def _build_split_diagnostics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    normalized_rows = [_normalize_candidate_row(row) for row in rows]
    before_rows = [row if isinstance(row, dict) else {} for row in rows]
    before_empty_item = sum(1 for row in before_rows if not _normalize_text(row.get("itemName")))
    before_empty_amount = sum(1 for row in before_rows if not _normalize_text(row.get("amount")))
    before_merged_money = sum(
        1
        for row in before_rows
        if not _normalize_text(row.get("amount")) and _split_merged_money_pair(row.get("unitPrice"))
    )
    after_merged_money = sum(
        1
        for row in normalized_rows
        if len(_money_tokens_from_text(row.get("unitPrice"))) >= 2
    )
    previews: list[dict[str, Any]] = []
    for before, after in zip(before_rows, normalized_rows):
        changed = any(
            _normalize_text(before.get(key)) != _normalize_text(after.get(key))
            for key in ("itemName", "lotNo", "expiryDate", "quantity", "unitPrice", "amount")
        )
        if changed and len(previews) < 5:
            previews.append(
                {
                    "before": {
                        "itemName": _normalize_text(before.get("itemName")),
                        "lotNo": _normalize_text(before.get("lotNo")),
                        "expiryDate": _normalize_text(before.get("expiryDate")),
                        "quantity": _normalize_text(before.get("quantity")),
                        "unitPrice": _normalize_text(before.get("unitPrice")),
                        "amount": _normalize_text(before.get("amount")),
                    },
                    "after": {
                        "itemName": _normalize_text(after.get("itemName")),
                        "lotNo": _normalize_text(after.get("lotNo")),
                        "expiryDate": _normalize_text(after.get("expiryDate")),
                        "quantity": _normalize_text(after.get("quantity")),
                        "unitPrice": _normalize_text(after.get("unitPrice")),
                        "amount": _normalize_text(after.get("amount")),
                    },
                }
            )
    return {
        "enabled": True,
        "moneySplitStrategy": "rightmost_money_pair",
        "rowsWithEmptyItemNameBefore": before_empty_item,
        "rowsWithEmptyItemNameAfter": sum(1 for row in normalized_rows if not _normalize_text(row.get("itemName"))),
        "rowsWithEmptyAmountBefore": before_empty_amount,
        "rowsWithEmptyAmountAfter": sum(1 for row in normalized_rows if not _normalize_text(row.get("amount"))),
        "rowsWithMergedMoneyBefore": before_merged_money,
        "rowsWithMergedMoneyAfter": after_merged_money,
        "rowsWithAmountFilled": max(0, before_empty_amount - sum(1 for row in normalized_rows if not _normalize_text(row.get("amount")))),
        "firstBeforeAfterPreview": previews,
    }


def _has_item_name_signal(value: Any) -> bool:
    text = _normalize_text(value)
    if len(text) < 2:
        return False
    if not re.search(r"[A-Za-z]", text) and not re.search(r"[^\x00-\x7F]", text):
        return False
    return not re.fullmatch(r"[\d\s,.\-_/]+", text)


def _metadata_negative_reason(text: str) -> str:
    normalized = _normalize_text(text).lower()
    markers = {
        "business_or_party_metadata": (
            "business", "supplier", "buyer", "address", "tel", "fax",
            "사업자", "대표자", "공급자", "공급받", "상호", "성명", "주소", "전화",
        ),
        "summary_or_balance": (
            "total", "balance", "vat", "tax", "합계", "소계", "총액", "부가세", "누계", "잔액", "계약잔액",
        ),
        "document_or_footer": (
            "page", "no.", "document", "ossbook", "www.", ".co.kr",
            "출력", "일자", "페이지", "문서", "세금계산서", "전자장부", "계약코드",
            "영업사원", "영업소", "도매관리", "간납처",
        ),
    }
    for reason, words in markers.items():
        if any(word in normalized for word in words):
            return reason
    if re.search(r"\d{3}-\d{2}-\d{5}", normalized):
        return "business_or_party_metadata"
    return ""


def _is_summary_or_header_line(text: str) -> bool:
    normalized = _normalize_text(text)
    if not normalized:
        return True
    if _metadata_negative_reason(normalized):
        return True
    summary_markers = (
        "합계",
        "소계",
        "총액",
        "청구금액",
        "공급대가",
        "사업자번호",
        "공급자",
        "공급받는자",
        "상호",
        "회사명",
        "업체명",
    )
    if any(marker in normalized for marker in summary_markers):
        return True
    header_markers = ("품명", "품목", "규격", "수량", "단가", "금액")
    return sum(1 for marker in header_markers if marker in normalized) >= 3 and not re.search(r"\d", normalized)


def _parse_table_row_candidate(line: str, row_index: int) -> dict[str, str] | None:
    text = _normalize_comma_space_money_text(line)
    if _is_summary_or_header_line(text):
        return None
    tokens = _merge_comma_space_money_tokens(text.split())
    if len(tokens) < 3:
        return None
    numeric_positions = [(idx, token) for idx, token in enumerate(tokens) if _is_number_token(token)]
    if len(numeric_positions) < 2:
        return None
    first_numeric_idx = numeric_positions[0][0]
    label_tokens = tokens[:first_numeric_idx]
    if not label_tokens:
        return None
    numeric_values = [_clean_number_token(token) for _, token in numeric_positions]
    item_name = " ".join(label_tokens)
    spec = ""
    if len(label_tokens) >= 2:
        item_name = " ".join(label_tokens[:-1])
        spec = label_tokens[-1]
    quantity = numeric_values[-3] if len(numeric_values) >= 3 else ""
    unit_price = numeric_values[-2]
    amount = numeric_values[-1]
    lot_no = ""
    expiry_date = ""
    for numeric_value in numeric_values[:-3]:
        if not expiry_date and _is_date_like_number(numeric_value):
            expiry_date = numeric_value
            continue
        if not lot_no and _is_lot_or_manufacturing_like_number(numeric_value):
            lot_no = numeric_value
    if (
        quantity
        and len(numeric_values) == 3
        and _is_date_like_number(quantity)
        and _money_parse_value(unit_price) is not None
        and _money_parse_value(amount) is not None
        and (_money_parse_value(amount) or 0) >= (_money_parse_value(unit_price) or 0)
    ):
        if not expiry_date:
            expiry_date = quantity
        quantity = ""
    if not item_name and not amount:
        return None
    return {
        "rowIndex": str(row_index),
        "itemName": item_name,
        "spec": spec,
        "lotNo": lot_no,
        "expiryDate": expiry_date,
        "quantity": quantity,
        "unitPrice": unit_price,
        "amount": amount,
        "_rawText": text,
        "_confidence": "0.2",
        "_source": "invoice_statement_free_line_candidate",
    }


def _parse_relaxed_table_row_candidate(line: str, row_index: int) -> dict[str, str] | None:
    """Generalized single-line candidate for invoices whose item rows are
    'item name ... amount' rather than the dense multi-numeric column layout.

    Conservative on purpose: requires BOTH an item-name signal AND a parseable
    money amount on the same line, and rejects summary/header/party-metadata
    lines, so footers and totals are never revived. Used only as a fallback when
    the strict column parser finds nothing (see ``_find_table_row_candidates``),
    which keeps dense single-line layouts (e.g. the 1.jpg reference) untouched.
    """
    text = _normalize_text(line)
    if _is_summary_or_header_line(text):
        return None
    if _metadata_negative_reason(text):
        return None
    money_tokens = _money_tokens_from_text(text)
    if not money_tokens:
        return None
    item_name = _candidate_item_name_from_raw_text(text)
    if not item_name:
        return None
    amount = _normalize_money(money_tokens[-1])
    unit_price = _normalize_money(money_tokens[-2]) if len(money_tokens) >= 2 else ""
    quantity = ""
    for token in text.split():
        cleaned = _clean_number_token(token)
        if cleaned and cleaned not in money_tokens and _looks_like_quantity_token(cleaned):
            quantity = _normalize_quantity(cleaned)
            break
    return {
        "rowIndex": str(row_index),
        "itemName": item_name,
        "spec": "",
        "lotNo": "",
        "expiryDate": "",
        "quantity": quantity,
        "unitPrice": unit_price,
        "amount": amount,
        "_rawText": text,
        "_confidence": "0.15",
        "_source": "invoice_statement_free_relaxed_line_candidate",
    }


def _is_acceptable_relaxed_row(row: dict[str, Any]) -> bool:
    """Strict keep-predicate for relaxed candidates inside the precision filter.

    Lets a clean ``item name + amount`` row survive even with a low column score,
    while still dropping forbidden-key rows, metadata/summary rows, and rows
    without a real item-name signal or a parseable money amount.
    """
    normalized = _normalize_candidate_row(row)
    if _has_forbidden_keys(row, FORBIDDEN_FREE_ROW_KEYS):
        return False
    if _metadata_negative_reason(" ".join(_normalize_text(normalized.get(key)) for key in REQUIRED_TABLE_ROW_KEYS)):
        return False
    if not _has_item_name_signal(normalized.get("itemName")):
        return False
    return _money_parse_value(normalized.get("amount")) is not None


def _find_table_row_candidates(lines: list[str], *, allow_relaxed: bool = True) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for line in lines:
        candidate = _parse_table_row_candidate(line, len(rows) + 1)
        if candidate is not None:
            rows.append(candidate)
    if rows or not allow_relaxed:
        return rows
    relaxed: list[dict[str, str]] = []
    for line in lines:
        candidate = _parse_relaxed_table_row_candidate(line, len(relaxed) + 1)
        if candidate is not None:
            relaxed.append(candidate)
    return relaxed


# ---------- 3E: 2D columnar row reconstruction (transposed PDF layouts) ----------
#
# Some invoice PDFs are rendered with the line-item table ROTATED 90deg, so
# cy-grouping produces one row per *field* (item names in one cy band, qty in
# another, unit price in another, amount in another) instead of one row per
# *item*. Index-zipping the rowTexts is unsafe (counts mismatch -> the wrong
# name paired with the wrong amount). The fix is to operate on raw OCR items,
# cluster by x to recover columns, and emit a row per name-column only when
# alignment is high-confidence (otherwise defer to the existing fallback).
#
# Safety: this is gated on "vertical-label stacking" detection
# (수량/단가/금액 found at similar x with distinctly different cy). A
# normal row-per-line table like 1.jpg has these labels on the SAME cy band,
# so the gate does not fire and the reference layout is untouched.

_COLUMNAR_FIELD_LABELS = {
    "수량": "quantity",
    "단가": "unitPrice",
    "금액": "amount",
    "공급금액": "amount",
    "공급가": "amount",
    "공급단가": "unitPrice",
}


def _detect_vertical_field_labels(items: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    """Return (labels, stacked).

    Looks for 수량/단가/금액-class label tokens. ``stacked`` is True only when
    >=2 labels sit at similar x (within ~60px) AND distinctly different cy
    (gap >= ~100px) — i.e. the labels appear as a vertical column on the page,
    which is the signature of a rotated/transposed invoice table.
    """
    found: list[dict[str, Any]] = []
    for it in items:
        text = _normalize_text(it.get("text", "")).strip()
        if not text:
            continue
        kind = _COLUMNAR_FIELD_LABELS.get(text)
        if kind is None:
            continue
        x = it.get("x")
        cy = it.get("cy")
        if not isinstance(x, (int, float)) or not isinstance(cy, (int, float)):
            continue
        found.append({
            "label": text,
            "kind": kind,
            "x": float(x),
            "cy": float(cy),
            "w": float(it.get("w") or 0),
            "h": float(it.get("h") or 0),
        })
    if len(found) < 2:
        return found, False
    # Cluster by x; within a cluster, check vertical spread.
    found_sorted = sorted(found, key=lambda f: f["x"])
    clusters: list[list[dict[str, Any]]] = [[found_sorted[0]]]
    for f in found_sorted[1:]:
        if abs(f["x"] - clusters[-1][-1]["x"]) <= 60:
            clusters[-1].append(f)
        else:
            clusters.append([f])
    for cl in clusters:
        if len(cl) < 2:
            continue
        cys = sorted(f["cy"] for f in cl)
        if cys[-1] - cys[0] >= 100:
            # Keep one representative per kind (the topmost cy).
            by_kind: dict[str, dict[str, Any]] = {}
            for f in cl:
                cur = by_kind.get(f["kind"])
                if cur is None or f["cy"] < cur["cy"]:
                    by_kind[f["kind"]] = f
            return list(by_kind.values()), True
    return found, False


def _build_columnar_rows_from_ocr_items(
    items: list[dict[str, Any]],
    *,
    doc_type: str = "invoice_statement",
    full_text: str = "",
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    """2D coordinate-based column-row reconstruction for transposed tables.

    Returns ``(rows, diagnostics)``. ``rows`` is empty when the gate does not
    fire OR when alignment confidence is below the emit threshold OR when a
    contamination check trips (a value that equals the sum of the other values
    in its field band is treated as a footer/total and rejects the whole
    attempt). Diagnostics include the decision and reason.

    3F: also attempts row-local quantity completion for emitted rows whose qty
    cell is missing (search a wider cy band around the qty label, narrow x
    window at the column, strict qty-token filter) and computes an amount-sum
    reconciliation against money tokens found in ``full_text`` (e.g. a document
    supplyAmount). Both are surfaced in diagnostics; neither relaxes the global
    release gate — that decision belongs to ``_evaluate_release_threshold``.
    """
    diag: dict[str, Any] = {
        "attempted": False,
        "strategy": "raw_ocr_xy_column_row",
        "confidence": 0.0,
        "decision": "reject",
        "reason": "",
        "columnGroups": {"itemName": 0, "quantity": 0, "unitPrice": 0, "amount": 0},
        "emittedRows": 0,
        "rejectedRows": 0,
        "alignmentIssues": [],
        "quantityCompletion": {
            "attempted": False,
            "method": "none",
            "beforeMissing": 0,
            "afterMissing": 0,
            "candidatesFound": 0,
            "reasons": [],
        },
        "productCodeRouting": {
            "detected": False,
            "tokens": [],
            "routedTo": "spec",
            "excludedFromItemName": 0,
        },
        "amountSumActual": None,
        "amountSumTarget": None,
        "amountSumReconciles": False,
    }
    if not items:
        diag["reason"] = "no_items"
        return [], diag

    labels, stacked = _detect_vertical_field_labels(items)
    if not stacked:
        diag["reason"] = "no_vertical_label_stacking"
        return [], diag
    diag["attempted"] = True

    # For each label, gather candidate field values within cy +/- band AND
    # strictly to the LEFT of the label (rotated layout convention observed on
    # 5.pdf and 2.pdf). Reject metadata/summary tokens.
    band_height = 50.0
    field_bands: dict[str, list[dict[str, Any]]] = {}
    for label in labels:
        kind = label["kind"]
        if kind in field_bands:
            continue
        cy0 = label["cy"]
        x_label = label["x"]
        vals: list[dict[str, Any]] = []
        for it in items:
            x = it.get("x")
            cy = it.get("cy")
            if not isinstance(x, (int, float)) or not isinstance(cy, (int, float)):
                continue
            x = float(x)
            cy = float(cy)
            if abs(cy - cy0) > band_height:
                continue
            if x >= x_label - 10:
                continue
            text = _normalize_text(it.get("text") or "")
            if not text:
                continue
            if _is_summary_or_header_line(text) or _metadata_negative_reason(text):
                continue
            if kind == "quantity":
                cleaned = _clean_number_token(text)
                if _looks_like_quantity_token(cleaned):
                    vals.append({"x": x, "cy": cy, "text": text, "value": _normalize_quantity(cleaned)})
            else:
                if _looks_like_money_token(text):
                    money = _normalize_money(text)
                    if money:
                        vals.append({"x": x, "cy": cy, "text": text, "value": money})
        field_bands[kind] = vals

    field_xs: list[float] = []
    for vs in field_bands.values():
        field_xs.extend(v["x"] for v in vs)
    if not field_xs:
        diag["reason"] = "no_field_values_in_bands"
        return [], diag
    field_x_min = min(field_xs)
    field_x_max = max(field_xs)

    # Item-name column: hangul/letter-bearing tokens above the topmost label cy,
    # within the x-range of the field values (with a small margin), with the
    # metadata/summary guards.
    min_label_cy = min(label["cy"] for label in labels)
    name_band_cy_max = min_label_cy - 100.0
    item_name_tokens: list[dict[str, Any]] = []
    for it in items:
        x = it.get("x")
        cy = it.get("cy")
        if not isinstance(x, (int, float)) or not isinstance(cy, (int, float)):
            continue
        x = float(x)
        cy = float(cy)
        if cy >= name_band_cy_max:
            continue
        if x < field_x_min - 50 or x > field_x_max + 50:
            continue
        text = _normalize_text(it.get("text") or "")
        if not text:
            continue
        if _is_summary_or_header_line(text) or _metadata_negative_reason(text):
            continue
        if not _has_item_name_signal(text):
            continue
        item_name_tokens.append({"x": x, "cy": cy, "text": text})
    if not item_name_tokens:
        diag["reason"] = "no_item_name_tokens"
        return [], diag

    # Cluster item-name tokens by x with a strict tolerance so distinct
    # name-columns are not merged. (5.pdf names are spaced ~50px apart; tol 35
    # keeps them separate while still tolerating minor jitter.)
    item_name_tokens.sort(key=lambda t: t["x"])
    name_clusters: list[list[dict[str, Any]]] = [[item_name_tokens[0]]]
    for tok in item_name_tokens[1:]:
        if tok["x"] - name_clusters[-1][-1]["x"] <= 35:
            name_clusters[-1].append(tok)
        else:
            name_clusters.append([tok])

    align_tol = 35.0
    rows: list[dict[str, str]] = []
    rejected = 0
    for cluster in name_clusters:
        col_x = sum(t["x"] for t in cluster) / len(cluster)
        cluster.sort(key=lambda t: t["cy"])
        product_code_tokens = [
            t["text"] for t in cluster if _looks_like_product_code_token(t.get("text"))
        ]
        name_parts = [
            t["text"] for t in cluster if not _looks_like_product_code_token(t.get("text"))
        ]
        if product_code_tokens:
            diag["productCodeRouting"]["detected"] = True
            diag["productCodeRouting"]["excludedFromItemName"] += len(product_code_tokens)
            for token in product_code_tokens:
                if token not in diag["productCodeRouting"]["tokens"]:
                    diag["productCodeRouting"]["tokens"].append(token)
        if not name_parts:
            rejected += 1
            diag["alignmentIssues"].append("product_code_only_name_cluster")
            continue
        name_text = " ".join(name_parts)
        spec_text = " ".join(product_code_tokens)
        matched: dict[str, dict[str, Any]] = {}
        for kind, vals in field_bands.items():
            candidates = [v for v in vals if abs(v["x"] - col_x) <= align_tol]
            if not candidates:
                continue
            candidates.sort(key=lambda v: abs(v["x"] - col_x))
            matched[kind] = candidates[0]
        # A real row needs at least amount OR unitPrice plus the name.
        if "amount" not in matched and "unitPrice" not in matched:
            rejected += 1
            continue
        rows.append({
            "rowIndex": str(len(rows) + 1),
            "itemName": name_text,
            "spec": spec_text,
            "lotNo": "",
            "expiryDate": "",
            "quantity": matched.get("quantity", {}).get("value", ""),
            "unitPrice": matched.get("unitPrice", {}).get("value", ""),
            "amount": matched.get("amount", {}).get("value", ""),
            "_rawText": name_text,
            "_confidence": "0.4",
            "_source": "invoice_statement_free_columnar_2d_row",
        })

    if not rows:
        diag["reason"] = "no_rows_after_alignment"
        diag["rejectedRows"] = rejected
        return [], diag

    cnt_name = len(name_clusters)
    cnt_amount = len(field_bands.get("amount", []))
    cnt_qty = len(field_bands.get("quantity", []))
    cnt_up = len(field_bands.get("unitPrice", []))
    diag["columnGroups"] = {
        "itemName": cnt_name,
        "quantity": cnt_qty,
        "unitPrice": cnt_up,
        "amount": cnt_amount,
    }

    # Contamination guard: if any row's amount equals the sum of the other
    # rows' amounts (within rounding), it is almost certainly a document total
    # (e.g. 공급가액합계) that leaked into the amount band. Reject the whole
    # attempt rather than emit a fake/mixed table.
    amount_vals = [_money_parse_value(r.get("amount") or "") for r in rows]
    amount_vals = [v for v in amount_vals if v is not None]
    if amount_vals:
        total = sum(amount_vals)
        for v in amount_vals:
            others = total - v
            if others > 0 and abs(v - others) <= max(1.0, others * 0.005):
                diag["reason"] = "amount_band_contaminated_by_total"
                diag["alignmentIssues"].append("amount_equals_sum_of_others")
                return [], diag

    # 3F: row-local quantity completion. Some rotated tables have missing qty
    # tokens for a subset of columns (5.pdf has qty for 4 of 6 columns). Try to
    # recover the missing ones by widening the cy search around the qty label
    # while keeping the strict x window of the column AND the strict qty-token
    # filter (no money, no date-like, no lot-like, no metadata). If exactly one
    # candidate is found and it is not already used by another row, fill it.
    qty_label = next((label for label in labels if label["kind"] == "quantity"), None)
    used_qty_token_keys: set[tuple[float, float]] = set()
    for r in rows:
        for v in field_bands.get("quantity") or []:
            if v.get("value") and r.get("quantity") == v.get("value"):
                used_qty_token_keys.add((v["x"], v["cy"]))
    before_missing = sum(1 for r in rows if not _normalize_text(r.get("quantity")))
    diag["quantityCompletion"]["beforeMissing"] = before_missing
    found_total = 0
    if qty_label and before_missing > 0:
        diag["quantityCompletion"]["attempted"] = True
        diag["quantityCompletion"]["method"] = "row_local_search"
        wide_band = 100.0
        for r in rows:
            if _normalize_text(r.get("quantity")):
                continue
            # Recover the row's column x from its name token cluster: rows are
            # built in name-cluster order, but we don't store col_x on the row.
            # Re-derive by matching to the closest name cluster center.
            row_name = r.get("itemName") or ""
            row_x = None
            for cluster in name_clusters:
                cluster_name = " ".join(
                    t["text"] for t in cluster if not _looks_like_product_code_token(t.get("text"))
                )
                if cluster_name == row_name:
                    row_x = sum(t["x"] for t in cluster) / len(cluster)
                    break
            if row_x is None:
                diag["quantityCompletion"]["reasons"].append(f"col_x_unresolved_for_{row_name[:20]}")
                continue
            candidates: list[dict[str, Any]] = []
            for it in items:
                x = it.get("x")
                cy = it.get("cy")
                if not isinstance(x, (int, float)) or not isinstance(cy, (int, float)):
                    continue
                x = float(x)
                cy = float(cy)
                if abs(cy - qty_label["cy"]) > wide_band:
                    continue
                if x >= qty_label["x"] - 10:
                    continue
                if abs(x - row_x) > align_tol:
                    continue
                if (x, cy) in used_qty_token_keys:
                    continue
                text = _normalize_text(it.get("text") or "")
                if not text:
                    continue
                if _is_summary_or_header_line(text) or _metadata_negative_reason(text):
                    continue
                cleaned = _clean_number_token(text)
                if not _looks_like_quantity_token(cleaned):
                    continue
                if _is_date_like_number(cleaned) or _is_lot_or_manufacturing_like_number(cleaned):
                    continue
                candidates.append({"x": x, "cy": cy, "value": _normalize_quantity(cleaned)})
            if len(candidates) == 1:
                r["quantity"] = candidates[0]["value"]
                used_qty_token_keys.add((candidates[0]["x"], candidates[0]["cy"]))
                found_total += 1
            elif len(candidates) > 1:
                diag["quantityCompletion"]["reasons"].append(f"ambiguous_{len(candidates)}_for_{row_name[:20]}")
            else:
                diag["quantityCompletion"]["reasons"].append(f"no_token_for_{row_name[:20]}")
        diag["quantityCompletion"]["candidatesFound"] = found_total
    after_missing = sum(1 for r in rows if not _normalize_text(r.get("quantity")))
    diag["quantityCompletion"]["afterMissing"] = after_missing

    # 3F: amount-sum reconciliation. Sum of emitted line amounts is compared to
    # money tokens found in the document full_text. A near-exact match with an
    # independently-extracted scalar (e.g. supplyAmount) is strong evidence that
    # the columns are aligned correctly and the table is a real table.
    #
    # NOTE: we intentionally use ``_number_value`` instead of ``_money_parse_value``
    # for this numeric comparison. ``_money_parse_value`` calls
    # ``_is_date_like_number`` which has a long-standing false-positive on plain
    # 6-digit numbers (e.g. "420000" matches ``\d{6}``), so legitimate comma-bearing
    # amounts like "420,000" get parsed to None inside that helper. Fixing the
    # global helper risks regressing the existing 1.jpg release path (which relies
    # on the ≥2-numeric-fields rule via the same helper). For this reconciliation
    # we only need a numeric value of an already-validated money token, so we
    # bypass the date check with ``_number_value`` directly. ``_money_tokens_from_text``
    # already filters no-comma date-like tokens upstream.
    amount_vals_for_sum: list[float] = []
    for r in rows:
        v = _number_value(_normalize_text(r.get("amount")))
        if v is not None and v > 0:
            amount_vals_for_sum.append(v)
    sum_amount = sum(amount_vals_for_sum)
    diag["amountSumActual"] = sum_amount if amount_vals_for_sum else None
    if sum_amount > 0 and full_text:
        ft_money = _money_tokens_from_text(full_text)
        for tok in ft_money:
            tok_val = _number_value(tok)
            if tok_val is None or tok_val <= 0:
                continue
            # Skip a match against an individual line amount itself.
            if any(abs(tok_val - v) <= max(1.0, v * 0.005) for v in amount_vals_for_sum):
                continue
            if abs(tok_val - sum_amount) <= max(1.0, sum_amount * 0.005):
                diag["amountSumTarget"] = tok
                diag["amountSumReconciles"] = True
                break

    # Confidence aggregate. Components:
    #  - consistency: how close per-field counts are to each other (1.0 perfect)
    #  - field_density: average filled (qty/unit/amount) fields per emitted row
    #  - emit_coverage: emitted rows / max field count
    non_zero = [c for c in (cnt_name, cnt_amount, cnt_qty, cnt_up) if c > 0]
    consistency = (min(non_zero) / max(non_zero)) if non_zero else 0.0
    filled = sum(1 for r in rows for k in ("quantity", "unitPrice", "amount") if r.get(k))
    field_density = filled / (3 * len(rows))
    emit_coverage = len(rows) / max(1, max(cnt_amount, cnt_name))
    confidence = round(0.5 * consistency + 0.3 * field_density + 0.2 * emit_coverage, 4)
    diag["confidence"] = confidence
    diag["emittedRows"] = len(rows)
    diag["rejectedRows"] = rejected
    if cnt_amount and cnt_name and abs(cnt_amount - cnt_name) >= 2:
        diag["alignmentIssues"].append(f"name_count={cnt_name}_vs_amount_count={cnt_amount}")
    if rejected:
        diag["alignmentIssues"].append(f"rejected_columns_without_amount_or_unitPrice={rejected}")

    HIGH = 0.65
    MED = 0.5
    if confidence >= HIGH:
        diag["decision"] = "emit"
        return rows, diag
    if confidence >= MED:
        diag["decision"] = "diagnostics_only"
        diag["reason"] = f"confidence_medium({confidence})_no_emit"
        return [], diag
    diag["decision"] = "reject"
    diag["reason"] = f"confidence_below_threshold({confidence})"
    return [], diag


def _score_invoice_item_row(row: dict[str, Any], row_text: str | None = None) -> dict[str, Any]:
    text = _normalize_text(row_text or row.get("_rawText") or "")
    reasons: list[str] = []
    score = 0
    negative = _metadata_negative_reason(text)
    if negative:
        reasons.append(negative)
        score -= 5

    item_name = _normalize_text(row.get("itemName"))
    spec = _normalize_text(row.get("spec"))
    quantity = _normalize_text(row.get("quantity"))
    unit_price = _normalize_text(row.get("unitPrice"))
    amount = _normalize_text(row.get("amount"))
    amount_value = _number_value(amount)
    unit_price_value = _number_value(unit_price)

    if _has_item_name_signal(item_name):
        score += 2
        reasons.append("item_name_signal")
    else:
        score -= 2
        reasons.append("weak_item_name")
    if _looks_like_spec_token(spec):
        score += 2
        reasons.append("spec_signal")
    elif spec:
        reasons.append("weak_spec")
    else:
        score -= 1
        reasons.append("missing_spec")
    if _looks_like_quantity_token(quantity):
        score += 1
        reasons.append("quantity_signal")
    else:
        score -= 1
        reasons.append("weak_quantity")
    if _looks_like_money_token(unit_price):
        score += 1
        reasons.append("unit_price_signal")
    else:
        score -= 1
        reasons.append("weak_unit_price")
    if _looks_like_money_token(amount):
        score += 2
        reasons.append("amount_signal")
    else:
        score -= 3
        reasons.append("weak_amount")
    if amount_value is not None and unit_price_value is not None and amount_value >= unit_price_value:
        score += 1
        reasons.append("amount_ge_unit_price")
    elif amount_value is not None and unit_price_value is not None:
        score -= 2
        reasons.append("amount_lt_unit_price")
    if len(re.findall(r"\d", text)) >= 6 and _has_item_name_signal(item_name):
        score += 1
        reasons.append("numeric_cluster")

    metadata_reasons = {"business_or_party_metadata", "summary_or_balance", "document_or_footer"}
    return {
        "score": score,
        "reasons": reasons,
        "dropReason": next((reason for reason in reasons if reason in metadata_reasons), ""),
    }


def _is_plausible_invoice_item_row(row: dict[str, Any], row_text: str | None = None) -> bool:
    score = _score_invoice_item_row(row, row_text)
    if score.get("dropReason"):
        return False
    return int(score.get("score") or 0) >= 4


def _row_preview(row: dict[str, Any], extra: dict[str, Any] | None = None) -> dict[str, Any]:
    preview = {
        "itemName": row.get("itemName", ""),
        "spec": row.get("spec", ""),
        "quantity": row.get("quantity", ""),
        "unitPrice": row.get("unitPrice", ""),
        "amount": row.get("amount", ""),
    }
    if extra:
        preview.update(extra)
    return preview


def _normalize_candidate_row(row: Any) -> dict[str, Any]:
    source = row if isinstance(row, dict) else {}
    normalized: dict[str, Any] = {
        "itemName": _normalize_item_name(source.get("itemName")),
        "spec": _normalize_spec(source.get("spec")),
        "lotNo": _clean_number_token(source.get("lotNo")),
        "expiryDate": _clean_number_token(source.get("expiryDate")),
        "quantity": _normalize_quantity(source.get("quantity")),
        "unitPrice": _normalize_money(source.get("unitPrice")),
        "amount": _normalize_money(source.get("amount")),
    }
    for key in ("itemCode", "supplyAmount", "taxAmount", "rowIndex"):
        if key in source:
            normalized[key] = _normalize_text(source.get(key))
    for key in ("_rawText", "_confidence", "_source"):
        if key in source:
            normalized[key] = deepcopy(source.get(key))
    return _repair_candidate_column_split(normalized, source)


def _amount_relation_reason(row: dict[str, Any]) -> str:
    unit_price = _money_parse_value(row.get("unitPrice"))
    amount = _money_parse_value(row.get("amount"))
    if unit_price is None or amount is None:
        return ""
    return "amount_lt_unit_price" if amount < unit_price else ""


def _is_release_ready_table_row(row: dict[str, Any]) -> tuple[bool, list[str]]:
    normalized = _normalize_candidate_row(row)
    reasons: list[str] = []
    if _has_forbidden_keys(row, FORBIDDEN_FREE_ROW_KEYS):
        reasons.append("forbidden_row_key")
    if not normalized.get("itemName"):
        reasons.append("missing_itemName")
    if not normalized.get("amount"):
        reasons.append("missing_amount")
    if _metadata_negative_reason(" ".join(_normalize_text(normalized.get(key)) for key in REQUIRED_TABLE_ROW_KEYS)):
        reasons.append("metadata_or_summary_row")
    quantity = normalized.get("quantity", "")
    if quantity:
        if _is_date_like_number(quantity):
            reasons.append("quantity_date_like")
        elif _is_lot_or_manufacturing_like_number(quantity):
            reasons.append("quantity_lot_like")
    else:
        reasons.append("missing_quantity")
    numeric_values = [
        _number_value(normalized.get("quantity")),
        _money_parse_value(normalized.get("unitPrice")),
        _money_parse_value(normalized.get("amount")),
    ]
    if sum(1 for value in numeric_values if value is not None) < 2:
        reasons.append("insufficient_numeric_fields")
    relation = _amount_relation_reason(normalized)
    if relation:
        reasons.append(relation)
    return len(reasons) == 0, reasons


def _summarize_candidate_field_quality(rows: list[dict[str, Any]]) -> dict[str, Any]:
    normalized_rows = [_normalize_candidate_row(row) for row in rows]
    field_completeness = {
        field: {
            "present": sum(1 for row in normalized_rows if _normalize_text(row.get(field))),
            "empty": sum(1 for row in normalized_rows if not _normalize_text(row.get(field))),
        }
        for field in REQUIRED_TABLE_ROW_KEYS
    }
    numeric_parseability = {
        "quantity": {
            "parseable": sum(1 for row in normalized_rows if _number_value(row.get("quantity")) is not None),
            "suspicious": sum(1 for row in normalized_rows if _normalize_text(row.get("quantity")) and _number_value(row.get("quantity")) is None),
        },
        "unitPrice": {
            "parseable": sum(1 for row in normalized_rows if _money_parse_value(row.get("unitPrice")) is not None),
            "suspicious": sum(1 for row in normalized_rows if _normalize_text(row.get("unitPrice")) and _money_parse_value(row.get("unitPrice")) is None),
        },
        "amount": {
            "parseable": sum(1 for row in normalized_rows if _money_parse_value(row.get("amount")) is not None),
            "suspicious": sum(1 for row in normalized_rows if _normalize_text(row.get("amount")) and _money_parse_value(row.get("amount")) is None),
        },
    }
    release_ready = 0
    reason_counts: dict[str, int] = {}
    suspicious_rows = 0
    for row in normalized_rows:
        ready, reasons = _is_release_ready_table_row(row)
        if ready:
            release_ready += 1
        else:
            suspicious_rows += 1
            for reason in reasons:
                reason_counts[reason] = reason_counts.get(reason, 0) + 1
    total = len(normalized_rows)
    return {
        "fieldQualityEnabled": True,
        "totalRows": total,
        "releaseReadyRows": release_ready,
        "suspiciousRows": suspicious_rows,
        "releaseReadyRatio": round(release_ready / total, 4) if total else 0.0,
        "fieldCompleteness": field_completeness,
        "numericParseability": numeric_parseability,
        "suspiciousPatterns": reason_counts,
        "releaseThresholdPreview": {
            "minRows": 20,
            "minReleaseReadyRatio": 0.8,
            "passes": total >= 20 and (release_ready / total if total else 0.0) >= 0.8,
        },
        "firstNormalizedPreview": [_row_preview(row) for row in normalized_rows[:5]],
    }


def _ratio(numerator: Any, denominator: Any) -> float:
    try:
        den = float(denominator)
        return round(float(numerator) / den, 4) if den else 0.0
    except Exception:
        return 0.0


def _evaluate_release_threshold(
    table_rows: list[dict[str, Any]],
    field_quality: dict[str, Any] | None = None,
    *,
    columnar_context: dict[str, Any] | None = None,
) -> tuple[bool, list[str], dict[str, Any]]:
    rows = [_normalize_candidate_row(row) for row in table_rows]
    quality = deepcopy(field_quality) if isinstance(field_quality, dict) else _summarize_candidate_field_quality(rows)
    total = len(rows)
    release_ready = int(quality.get("releaseReadyRows") or 0)
    release_ready_ratio = float(quality.get("releaseReadyRatio") or _ratio(release_ready, total))
    completeness = quality.get("fieldCompleteness") if isinstance(quality.get("fieldCompleteness"), dict) else {}
    numeric = quality.get("numericParseability") if isinstance(quality.get("numericParseability"), dict) else {}
    forbidden_row_count = sum(1 for row in table_rows if _has_forbidden_keys(row, FORBIDDEN_FREE_ROW_KEYS))
    metadata_row_count = sum(
        1
        for row in rows
        if _metadata_negative_reason(" ".join(_normalize_text(row.get(key)) for key in REQUIRED_TABLE_ROW_KEYS))
    )
    ratios = {
        "releaseReadyRatio": release_ready_ratio,
        "itemNamePresentRatio": _ratio((completeness.get("itemName") or {}).get("present", 0), total),
        "amountPresentRatio": _ratio((completeness.get("amount") or {}).get("present", 0), total),
        "unitPriceParseableRatio": _ratio((numeric.get("unitPrice") or {}).get("parseable", 0), total),
        "quantityParseableRatio": _ratio((numeric.get("quantity") or {}).get("parseable", 0), total),
        "amountParseableRatioDiagnostic": _ratio((numeric.get("amount") or {}).get("parseable", 0), total),
    }
    # Generalized release floor. Large tables (>= largeTableMinRows) keep the
    # original strict-but-generous gate calibrated on the dense reference layout
    # (e.g. 1.jpg, 28 rows). Small tables (1..largeTableMinRows-1) are allowed to
    # release, but only when their quality is near-perfect — so a small invoice
    # with a few clean rows can pass while a single spurious/garbled row cannot.
    # The strictness for small tables comes from completeness/parseability ratios
    # and the metadata-negative guard, not from an absolute row-count floor.
    rules = {
        "largeTableMinRows": 20,
        "minFilteredRows": 1,
        "minReleaseReadyRows": 1,
        "minReleaseReadyRatio": 0.8,
        "minItemNamePresentRatio": 0.95,
        "minAmountPresentRatio": 0.95,
        "minUnitPriceParseableRatio": 0.8,
        "minQuantityParseableRatio": 0.7,
        "smallTableMinReleaseReadyRatio": 0.99,
        "smallTableMinItemNamePresentRatio": 0.99,
        "smallTableMinAmountPresentRatio": 0.99,
        "maxForbiddenRowKeys": 0,
        "maxMetadataRows": 0,
        "requiredTableDetected": "Y",
    }
    is_large_table = total >= rules["largeTableMinRows"]
    table_size_class = "large" if is_large_table else "small"
    min_release_ready_ratio = (
        rules["minReleaseReadyRatio"] if is_large_table else rules["smallTableMinReleaseReadyRatio"]
    )
    min_item_name_ratio = (
        rules["minItemNamePresentRatio"] if is_large_table else rules["smallTableMinItemNamePresentRatio"]
    )
    min_amount_ratio = (
        rules["minAmountPresentRatio"] if is_large_table else rules["smallTableMinAmountPresentRatio"]
    )
    fail_reasons: list[str] = []
    if total < rules["minFilteredRows"]:
        fail_reasons.append("filtered_rows_below_threshold")
    if release_ready < rules["minReleaseReadyRows"]:
        fail_reasons.append("release_ready_rows_below_threshold")
    if release_ready_ratio < min_release_ready_ratio:
        fail_reasons.append("release_ready_ratio_below_threshold")
    if ratios["itemNamePresentRatio"] < min_item_name_ratio:
        fail_reasons.append("itemName_present_ratio_below_threshold")
    if ratios["amountPresentRatio"] < min_amount_ratio:
        fail_reasons.append("amount_present_ratio_below_threshold")
    if ratios["unitPriceParseableRatio"] < rules["minUnitPriceParseableRatio"]:
        fail_reasons.append("unitPrice_parseable_ratio_below_threshold")
    if ratios["quantityParseableRatio"] < rules["minQuantityParseableRatio"]:
        fail_reasons.append("quantity_parseable_ratio_below_threshold")
    if forbidden_row_count != rules["maxForbiddenRowKeys"]:
        fail_reasons.append("forbidden_row_keys_present")
    if metadata_row_count != rules["maxMetadataRows"]:
        fail_reasons.append("metadata_or_summary_rows_present")
    if ("Y" if total else "N") != rules["requiredTableDetected"]:
        fail_reasons.append("table_not_detected")

    # 3F: Safe quantity-optional release for columnar 2D rows. Hard-gated:
    # ALL of the following must hold, OR no relaxation is applied.
    #  - There is a non-empty ``columnar_context`` from ``_build_columnar_rows_from_ocr_items``
    #  - columnar confidence >= 0.80 (above the emit threshold)
    #  - Amount-sum reconciliation passed (sum of row amounts matches an
    #    independently-extracted scalar in full_text, e.g. supplyAmount)
    #  - Item-name present ratio is 1.0 AND amount present ratio is 1.0
    #  - Unit-price parseable ratio >= 0.8 (the original strict threshold)
    #  - No metadata-bearing rows AND no forbidden-key rows
    #  - All current table_rows are columnar_2d_row source
    #  - The quantity missing ratio is at most ``qtyOptionalMissingMaxRatio``
    #    (currently 0.5 — half the rows can be qty-missing, no more)
    #
    # When the gate passes, drop only ``release_ready_ratio_below_threshold``
    # and ``quantity_parseable_ratio_below_threshold`` from fail_reasons after
    # confirming that, IF qty had been present, the rows would have been
    # release-ready (i.e. their non-qty reasons must reduce to {missing_quantity}).
    # The release_ready count is recomputed accordingly.
    columnar_release_decision: dict[str, Any] = {
        "applied": False,
        "reason": "",
        "qtyOptionalMissingMaxRatio": 0.5,
        "minConfidence": 0.80,
    }
    if isinstance(columnar_context, dict) and table_rows:
        all_columnar = all(
            str(row.get("_source", "")).endswith("columnar_2d_row") for row in table_rows
        )
        confidence = float(columnar_context.get("confidence") or 0.0)
        reconciles = bool(columnar_context.get("amountSumReconciles"))
        qty_missing = sum(1 for r in rows if not _normalize_text(r.get("quantity")))
        qty_missing_ratio = qty_missing / total if total else 0.0
        gate_failures: list[str] = []
        if not all_columnar:
            gate_failures.append("not_all_columnar_2d_source")
        if confidence < columnar_release_decision["minConfidence"]:
            gate_failures.append(f"confidence_{confidence}_below_{columnar_release_decision['minConfidence']}")
        if not reconciles:
            gate_failures.append("amount_sum_not_reconciled")
        if ratios["itemNamePresentRatio"] < 1.0:
            gate_failures.append("itemName_present_ratio_lt_1.0")
        if ratios["amountPresentRatio"] < 1.0:
            gate_failures.append("amount_present_ratio_lt_1.0")
        if ratios["unitPriceParseableRatio"] < rules["minUnitPriceParseableRatio"]:
            gate_failures.append("unitPrice_parseable_ratio_below_strict")
        if metadata_row_count != 0:
            gate_failures.append("metadata_rows_present")
        if forbidden_row_count != 0:
            gate_failures.append("forbidden_rows_present")
        if qty_missing_ratio > columnar_release_decision["qtyOptionalMissingMaxRatio"]:
            gate_failures.append(f"qty_missing_ratio_{qty_missing_ratio}_above_cap")
        if gate_failures:
            columnar_release_decision["reason"] = ";".join(gate_failures)[:200]
        else:
            # Recompute release_ready treating qty-only-missing columnar rows as
            # ready. We do NOT delegate to ``_is_release_ready_table_row`` here
            # because that helper depends on ``_money_parse_value`` which has a
            # long-standing false-positive on plain 6-digit numbers
            # ("420000" matches ``\d{6}`` in ``_is_date_like_number``), so
            # comma-bearing amounts like "420,000" get treated as None and
            # trip ``insufficient_numeric_fields`` on qty-missing rows. We
            # already gated on the strict upstream invariants (itemName=1.0,
            # amount=1.0, unitPrice parseable >= 0.8, no metadata, no
            # forbidden, confidence >= 0.80, amount-sum reconciles), so a row
            # qualifies as relaxed-ready when:
            #   - itemName text is present
            #   - amount text is present
            #   - no metadata-negative reason on the row
            #   - if both unitPrice and amount are numerically parseable
            #     (via _number_value to bypass the date-like false positive),
            #     then amount >= unitPrice (sanity)
            relaxed_ready = 0
            for row in rows:
                name_t = _normalize_text(row.get("itemName"))
                amt_t = _normalize_text(row.get("amount"))
                if not name_t or not amt_t:
                    continue
                joined = " ".join(_normalize_text(row.get(k)) for k in REQUIRED_TABLE_ROW_KEYS)
                if _metadata_negative_reason(joined):
                    continue
                if _has_forbidden_keys(row, FORBIDDEN_FREE_ROW_KEYS):
                    continue
                up_val = _number_value(_normalize_text(row.get("unitPrice")))
                amt_val = _number_value(amt_t)
                if up_val is not None and amt_val is not None and amt_val < up_val:
                    continue
                relaxed_ready += 1
            relaxed_ratio = (relaxed_ready / total) if total else 0.0
            if relaxed_ratio >= min_release_ready_ratio and relaxed_ready >= rules["minReleaseReadyRows"]:
                # Apply: drop the two qty-related fail reasons (others stand).
                pre_apply = list(fail_reasons)
                for r in (
                    "release_ready_ratio_below_threshold",
                    "release_ready_rows_below_threshold",
                    "quantity_parseable_ratio_below_threshold",
                ):
                    if r in fail_reasons:
                        fail_reasons.remove(r)
                columnar_release_decision["applied"] = True
                columnar_release_decision["relaxedReleaseReady"] = relaxed_ready
                columnar_release_decision["relaxedReleaseReadyRatio"] = round(relaxed_ratio, 4)
                columnar_release_decision["droppedFailReasons"] = [
                    r for r in pre_apply if r not in fail_reasons
                ]
            else:
                columnar_release_decision["reason"] = (
                    f"relaxed_ready_{relaxed_ready}/{total}_ratio_{round(relaxed_ratio,4)}_still_below_floor"
                )

    decision = {
        "enabled": True,
        "thresholdVersion": "3f_columnar_quantity_optional_release",
        "passes": not fail_reasons,
        "failReasons": fail_reasons,
        "rules": rules,
        "metrics": {
            "filteredRows": total,
            "releaseReadyRows": release_ready,
            "suspiciousRows": int(quality.get("suspiciousRows") or 0),
            "forbiddenRowKeyCount": forbidden_row_count,
            "metadataHeaderFooterKeptCount": metadata_row_count,
            "tableDetected": "Y" if total else "N",
            "tableSizeClass": table_size_class,
            "appliedReleaseReadyRatioFloor": min_release_ready_ratio,
            **ratios,
        },
        "columnarSafeRelease": columnar_release_decision,
        "diagnosticOnly": {
            "amountParseableRatio": ratios["amountParseableRatioDiagnostic"],
        },
    }
    return not fail_reasons, fail_reasons, decision


def _filter_table_row_candidates(rows: list[dict[str, str]]) -> tuple[list[dict[str, str]], dict[str, Any]]:
    kept: list[dict[str, str]] = []
    dropped: list[dict[str, Any]] = []
    reason_counts: dict[str, int] = {}
    relaxed_kept = 0
    for row in rows:
        score = _score_invoice_item_row(row, row.get("_rawText"))
        score_value = int(score.get("score") or 0)
        metadata_drop = _normalize_text(score.get("dropReason"))
        source = str(row.get("_source", ""))
        is_alternative = source.endswith(("relaxed_line_candidate", "columnar_2d_row"))
        # Metadata/summary rows always drop. Strict rows keep at score>=4.
        # Relaxed single-line candidates AND columnar (2D-reconstructed) rows
        # keep when they pass the strict relaxed predicate (item-name signal +
        # parseable amount, no metadata), so coordinate-aligned 'name + amount'
        # rows are not lost to the column-score threshold.
        if metadata_drop:
            drop_reason = metadata_drop
        elif score_value >= 4:
            drop_reason = ""
        elif is_alternative and _is_acceptable_relaxed_row(row):
            drop_reason = ""
        else:
            drop_reason = "low_precision_score"
        if not drop_reason:
            kept_row = _normalize_candidate_row(row)
            kept_row["rowIndex"] = str(len(kept) + 1)
            kept.append(kept_row)
            if is_alternative:
                relaxed_kept += 1
            continue
        reason_counts[drop_reason] = reason_counts.get(drop_reason, 0) + 1
        if len(dropped) < 5:
            dropped.append(_row_preview(row, {"score": score_value, "dropReason": drop_reason}))
    return kept, {
        "precisionFilterEnabled": True,
        "parsedCandidateCount": len(rows),
        "filteredCandidateCount": len(kept),
        "droppedCount": len(rows) - len(kept),
        "relaxedKeptCount": relaxed_kept,
        "dropReasons": reason_counts,
        "firstDroppedPreview": dropped,
        "firstKeptPreview": [_row_preview(row) for row in kept[:5]],
    }


def _group_ocr_items_into_row_texts(items: list[dict[str, Any]]) -> tuple[list[str], dict[str, Any]]:
    positioned = [
        item
        for item in items
        if isinstance(item.get("cy"), (int, float)) and isinstance(item.get("x"), (int, float))
    ]
    if not positioned:
        return [], {"status": "no_positioned_items", "positionedCount": 0}
    heights = sorted(float(item.get("h") or 0) for item in positioned if float(item.get("h") or 0) > 0)
    median_height = heights[len(heights) // 2] if heights else 12.0
    row_threshold = max(8.0, min(24.0, median_height * 0.75))
    rows: list[dict[str, Any]] = []
    for item in sorted(positioned, key=lambda value: (float(value["cy"]), float(value["x"]))):
        cy = float(item["cy"])
        target = None
        for row in rows:
            if abs(cy - float(row["cy"])) <= row_threshold:
                target = row
                break
        if target is None:
            target = {"cy": cy, "items": []}
            rows.append(target)
        target["items"].append(item)
        count = len(target["items"])
        target["cy"] = ((float(target["cy"]) * (count - 1)) + cy) / count

    row_texts: list[str] = []
    for row in sorted(rows, key=lambda value: float(value["cy"])):
        row_items = sorted(row["items"], key=lambda value: float(value["x"]))
        text = _normalize_text(" ".join(_normalize_text(item.get("text")) for item in row_items))
        if text:
            row_texts.append(text)
    return row_texts, {
        "status": "grouped",
        "positionedCount": len(positioned),
        "rowTextCount": len(row_texts),
        "rowThreshold": round(row_threshold, 2),
        "medianHeight": round(median_height, 2),
    }


def _build_table_candidate_diagnostics(
    *,
    raw_line_count: int,
    grouped_line_count: int,
    parsed_rows: list[dict[str, str]],
    table_rows: list[dict[str, str]],
    grouping_debug: dict[str, Any],
    precision_debug: dict[str, Any] | None = None,
) -> dict[str, Any]:
    precision = dict(precision_debug or {})
    field_quality = _summarize_candidate_field_quality(table_rows)
    split_diagnostics = _build_split_diagnostics(table_rows)
    if any(str(row.get("_source", "")).endswith("columnar_2d_row") for row in parsed_rows):
        candidate_strategy = "columnar_2d"
    elif any(str(row.get("_source", "")).endswith("relaxed_line_candidate") for row in parsed_rows):
        candidate_strategy = "relaxed_line"
    elif parsed_rows:
        candidate_strategy = "strict_column"
    else:
        candidate_strategy = "none"
    return {
        "strategy": "bbox_row_grouping_plus_precision_filter",
        "candidateStrategy": candidate_strategy,
        "rawLineCount": raw_line_count,
        "groupedLineCount": grouped_line_count,
        "parsedCandidateCount": len(parsed_rows),
        "candidateRowCount": len(table_rows),
        "meaningfulRowCount": sum(1 for row in table_rows if _is_meaningful_table_row(row)),
        "grouping": grouping_debug,
        "precision": precision,
        "splitDiagnostics": split_diagnostics,
        "fieldQuality": field_quality,
        "droppedCount": precision.get("droppedCount", 0),
        "dropReasons": precision.get("dropReasons", {}),
        "firstDroppedPreview": precision.get("firstDroppedPreview", []),
        "firstKeptPreview": precision.get("firstKeptPreview", []),
        "firstCandidatePreview": [
            {
                "itemName": row.get("itemName", ""),
                "spec": row.get("spec", ""),
                "lotNo": row.get("lotNo", ""),
                "expiryDate": row.get("expiryDate", ""),
                "quantity": row.get("quantity", ""),
                "unitPrice": row.get("unitPrice", ""),
                "amount": row.get("amount", ""),
            }
            for row in table_rows[:3]
        ],
    }


def _has_meaningful_value(value: Any) -> bool:
    text = _normalize_text(value)
    return bool(text and text not in {"-", "--", "N/A", "n/a", "None", "none"})


def _has_forbidden_keys(mapping: Any, forbidden_keys: tuple[str, ...]) -> bool:
    return isinstance(mapping, dict) and any(key in mapping for key in forbidden_keys)


def _is_meaningful_table_row(row: Any) -> bool:
    if not isinstance(row, dict):
        return False
    if _has_forbidden_keys(row, FORBIDDEN_FREE_ROW_KEYS):
        return False
    if any(key not in row for key in REQUIRED_TABLE_ROW_KEYS):
        return False
    return _has_meaningful_value(row.get("itemName")) or _has_meaningful_value(row.get("amount"))


def _is_success_like_free_debug(debug: Any) -> bool:
    if not isinstance(debug, dict):
        return False
    status = _normalize_text(debug.get("status")).lower()
    if status in {"success", "valid", "used"}:
        return True
    return debug.get("used") is True and debug.get("fallbackUsed") is False


def _is_valid_invoice_statement_free_result(result: Any) -> bool:
    try:
        if not isinstance(result, dict):
            return False
        if _has_forbidden_keys(result, FORBIDDEN_FREE_TOP_LEVEL_KEYS):
            return False
        document_fields = result.get("document_fields")
        if not isinstance(document_fields, dict):
            return False
        table_rows = result.get("tableRows")
        if not isinstance(table_rows, list) or len(table_rows) == 0:
            return False
        document_table_rows = document_fields.get("tableRows")
        if not isinstance(document_table_rows, list) or document_table_rows != table_rows:
            return False
        table_meta = result.get("tableMeta")
        if not isinstance(table_meta, dict):
            return False
        if table_meta.get("source") != "invoice_statement_free":
            return False
        if table_meta.get("mode") != "unstructured":
            return False
        if table_meta.get("fallbackRequired") is not False:
            return False
        if table_meta.get("rowCount") != len(table_rows):
            return False
        if result.get("tableDetected") != "Y":
            return False
        extract_debug = result.get("extract_debug")
        if not isinstance(extract_debug, dict):
            return False
        free_debug = extract_debug.get("invoice_statement_free")
        if not _is_success_like_free_debug(free_debug):
            return False
        return any(_is_meaningful_table_row(row) for row in table_rows)
    except Exception:
        return False


def _normalize_success_table_rows(table_rows: Any) -> list[dict[str, Any]]:
    if not isinstance(table_rows, list):
        return []
    normalized_rows: list[dict[str, Any]] = []
    for index, row in enumerate(table_rows, start=1):
        if not isinstance(row, dict):
            continue
        normalized = deepcopy(row)
        for key in REQUIRED_TABLE_ROW_KEYS:
            normalized[key] = _normalize_text(normalized.get(key))
        if "rowIndex" not in normalized:
            normalized["rowIndex"] = str(index)
        normalized_rows.append(normalized)
    return normalized_rows


def _extract_reference_invoice_statement_fields(
    ocr_lines_raw: Any,
    context: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Reuse the existing ``invoice_statement.py`` scalar extraction.

    The free parser fills party/summary scalars poorly, so on a free success we
    run the proven ``extract_invoice_statement_fields`` over the *same*
    ``ocr_lines_raw`` and reuse its party/summary scalar output. The import is
    lazy: ``invoice_statement.py`` never imports this module, so there is no
    circular import, and a lazy import keeps the standalone scaffold loadable.
    The call is purely in-memory (no extra OCR), and any failure degrades to an
    empty result so the free parser never raises on the success path.
    """

    debug: dict[str, Any] = {"attempted": False, "ok": False}
    if not isinstance(ocr_lines_raw, (list, tuple)) or not ocr_lines_raw:
        debug["reason"] = "no_ocr_lines"
        return {}, debug
    try:
        from extractors.invoice_statement import extract_invoice_statement_fields
    except Exception as exc:  # pragma: no cover - import guard
        debug["reason"] = f"import_failed: {exc}"
        return {}, debug
    ctx = dict(context or {})
    debug["attempted"] = True
    try:
        reference = extract_invoice_statement_fields(
            list(ocr_lines_raw),
            table_expected_columns=ctx.get("tableExpectedColumns"),
            table_bounds=ctx.get("tableBounds"),
            column_guides=ctx.get("columnGuides"),
        )
    except Exception as exc:
        debug["reason"] = f"extract_failed: {exc}"
        return {}, debug
    if not isinstance(reference, dict):
        debug["reason"] = "non_dict_result"
        return {}, debug
    debug["ok"] = True
    debug["referenceFilledScalarKeys"] = [
        key for key in REFERENCE_SCALAR_MERGE_KEYS if _has_meaningful_value(reference.get(key))
    ]
    return reference, debug


def _merge_invoice_statement_reference_scalars(
    free_fields: dict[str, Any],
    reference_fields: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Backfill empty party/summary scalars in the free result from the reference.

    Policy:
    - Only the scalar keys in ``REFERENCE_SCALAR_MERGE_KEYS`` are considered.
    - A meaningful free value is preserved (free wins; recorded as skipped).
    - An empty free value is filled from a meaningful reference value.
    - ``tableRows`` / ``tableMeta`` / ``tableDetected`` / ``rowCount`` /
      ``firstRowPreview`` are never read from the reference (merge exclusion),
      so the free parser's table output is preserved verbatim.
    """

    merged = dict(free_fields) if isinstance(free_fields, dict) else {}
    ref = reference_fields if isinstance(reference_fields, dict) else {}
    filled: list[str] = []
    skipped: list[str] = []
    for key in REFERENCE_SCALAR_MERGE_KEYS:
        if key in REFERENCE_SCALAR_MERGE_EXCLUDED_KEYS:
            continue
        if _has_meaningful_value(merged.get(key)):
            skipped.append(key)
            continue
        if _has_meaningful_value(ref.get(key)):
            merged[key] = _normalize_text(ref.get(key))
            filled.append(key)
    scalar_merge_debug = {
        "enabled": True,
        "source": "invoice_statement",
        "function": "extract_invoice_statement_fields",
        "candidateKeys": list(REFERENCE_SCALAR_MERGE_KEYS),
        "filledKeys": filled,
        "skippedKeys": skipped,
        "excludedKeys": list(REFERENCE_SCALAR_MERGE_EXCLUDED_KEYS),
        "tablePreserved": True,
    }
    return merged, scalar_merge_debug


def _build_success_invoice_statement_free_result(
    *,
    table_rows: list[dict[str, Any]] | None,
    document_fields: dict[str, Any] | None = None,
    confidence: float = 0.0,
    extract_debug: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a guard-compatible success shape without changing default flow."""

    rows = _normalize_success_table_rows(table_rows)
    if not rows:
        result = empty_invoice_statement_free_result()
        result["document_fields"] = {key: deepcopy(result.get(key)) for key in DOCUMENT_FIELD_KEYS}
        result["tableRows"] = []
        result["tableDetected"] = "N"
        result["tableMeta"] = {
            **deepcopy(result["tableMeta"]),
            "source": "invoice_statement_free",
            "mode": "unstructured",
            "fallbackRequired": True,
            "rowCount": 0,
        }
        result["document_fields"]["tableMeta"] = deepcopy(result["tableMeta"])
        result["extract_debug"] = {
            "invoice_statement_free": {
                "status": "empty",
                "used": False,
                "fallbackUsed": True,
                "fallbackRequired": True,
                "rowCount": 0,
            }
        }
        result["confidence"] = float(confidence or 0.0)
        return result

    fields = empty_invoice_statement_free_result()
    if isinstance(document_fields, dict):
        for key, value in document_fields.items():
            if key in DOCUMENT_FIELD_KEYS:
                fields[key] = deepcopy(value)
    table_meta = {
        "source": "invoice_statement_free",
        "mode": "unstructured",
        "fallbackRequired": False,
        "rowCount": len(rows),
        "columns": ["itemName", "spec", "lotNo", "expiryDate", "quantity", "unitPrice", "amount"],
        "expectedColumnKeys": ["itemName", "spec", "lotNo", "expiryDate", "quantity", "unitPrice", "amount"],
        "extractionSource": "invoice_statement_free_success_shape",
    }
    fields["tableDetected"] = "Y"
    fields["rowCount"] = len(rows)
    fields["firstRowPreview"] = _normalize_text(rows[0].get("itemName") or rows[0].get("amount"))
    fields["tableRows"] = deepcopy(rows)
    fields["tableMeta"] = deepcopy(table_meta)

    free_debug = {}
    if isinstance(extract_debug, dict):
        free_debug = deepcopy(extract_debug.get("invoice_statement_free") or {})
    free_debug.update(
        {
            "status": "success",
            "attempted": True,
            "used": True,
            "fallbackUsed": False,
            "fallbackRequired": False,
            "rowCount": len(rows),
        }
    )
    return {
        "document_fields": deepcopy(fields),
        "tableRows": deepcopy(rows),
        "tableDetected": "Y",
        "tableMeta": deepcopy(table_meta),
        "extract_debug": {"invoice_statement_free": free_debug},
        "confidence": float(confidence or 0.0),
    }


def _is_controlled_success_enabled() -> bool:
    return os.getenv("USE_INVOICE_STATEMENT_FREE_CONTROLLED_SUCCESS", "0") == "1"


def _build_controlled_success_rows() -> list[dict[str, Any]]:
    return [
        {
            "itemName": "CONTROLLED_TEST_ITEM",
            "spec": "1EA",
            "quantity": "1",
            "unitPrice": "100",
            "amount": "100",
        }
    ]


def _build_candidate_debug(
    *,
    lines: list[str],
    text: str,
) -> dict[str, Any]:
    business_numbers = _find_business_numbers(text)
    company_candidates = _find_company_candidates(lines)
    amount_candidates = _find_amount_candidates(text)
    code_vs_money = _build_code_vs_money_diagnostics(text)
    return {
        "businessNumbers": business_numbers,
        "companyCandidates": company_candidates,
        "amountCandidates": amount_candidates,
        "codeVsMoney": code_vs_money,
        "lineCount": len(lines),
        "textLength": len(text),
    }


def empty_invoice_statement_free_result() -> dict[str, Any]:
    """Return the existing invoice ``document_fields`` shape with no findings."""

    fields: dict[str, Any] = {key: "" for key in DOCUMENT_FIELD_KEYS}
    fields.update(
        {
            "tableDetected": "N",
            "rowCount": "",
            "firstRowPreview": "",
            "tableRows": [],
            "tableMeta": _empty_table_meta(),
        }
    )
    return fields


def extract_invoice_statement_free(
    *,
    ocr_lines_raw: list[tuple[Any, str, float]] | None = None,
    full_text: str = "",
    image_size: tuple[int, int] | list[int] | None = None,
    doc_type: str = "invoice_statement",
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a response-compatible scaffold result for a free-form invoice.

    The function is side-effect free and performs no OCR. It accepts the inputs
    that the future dispatcher is expected to have available, but this 1B phase
    deliberately returns an empty compatible result so existing production flow
    cannot change.
    """

    result = empty_invoice_statement_free_result()
    ocr_items = _extract_ocr_line_items(ocr_lines_raw)
    lines = [_normalize_text(item.get("text")) for item in ocr_items if _normalize_text(item.get("text"))]
    grouped_lines, grouping_debug = _group_ocr_items_into_row_texts(ocr_items)
    normalized_full_text = _normalize_text(full_text)
    joined_line_text = _join_lines(lines)
    source_text = "\n".join(text for text in (normalized_full_text, joined_line_text) if text)
    candidates = _build_candidate_debug(lines=lines, text=source_text)
    # Strict column parsing first (grouped, then flat lines) so dense single-line
    # layouts (1.jpg reference) are unaffected; only fall back to the relaxed
    # 'item name + amount' candidate path when strict parsing finds nothing.
    parsed_table_rows = _find_table_row_candidates(grouped_lines, allow_relaxed=False)
    if not parsed_table_rows:
        parsed_table_rows = _find_table_row_candidates(lines, allow_relaxed=False)
    if not parsed_table_rows:
        parsed_table_rows = _find_table_row_candidates(grouped_lines)
    if not parsed_table_rows:
        parsed_table_rows = _find_table_row_candidates(lines)
    # 3E: when strict+relaxed produced few candidates AND the page has a
    # rotated/transposed table signature (vertical-label stacking), attempt 2D
    # coordinate-based column-row reconstruction. The helper is self-gated on
    # the stacking signature so dense reference layouts (1.jpg with 28 strict
    # rows) never enter this path. The helper returns rows ONLY when alignment
    # confidence is high and a contamination check passes; otherwise it returns
    # an empty list with diagnostics, leaving the existing fallback intact.
    columnar_diag: dict[str, Any] = {
        "attempted": False,
        "strategy": "raw_ocr_xy_column_row",
        "confidence": 0.0,
        "decision": "skipped",
        "reason": "strict_or_relaxed_sufficient" if len(parsed_table_rows) >= 5 else "",
        "columnGroups": {"itemName": 0, "quantity": 0, "unitPrice": 0, "amount": 0},
        "emittedRows": 0,
        "rejectedRows": 0,
        "alignmentIssues": [],
    }
    if len(parsed_table_rows) < 5:
        columnar_rows, columnar_diag = _build_columnar_rows_from_ocr_items(
            ocr_items, doc_type=doc_type, full_text=source_text
        )
        if columnar_rows:
            parsed_table_rows = columnar_rows
    table_rows, precision_debug = _filter_table_row_candidates(parsed_table_rows)
    table_candidate_diagnostics = _build_table_candidate_diagnostics(
        raw_line_count=len(lines),
        grouped_line_count=len(grouped_lines),
        parsed_rows=parsed_table_rows,
        table_rows=table_rows,
        grouping_debug=grouping_debug,
        precision_debug=precision_debug,
    )
    # 3F: thread columnar context through release evaluation so the
    # quantity-optional gate has access to confidence + amount-sum reconciliation.
    columnar_context_for_release = None
    if columnar_diag.get("decision") == "emit":
        columnar_context_for_release = {
            "confidence": columnar_diag.get("confidence"),
            "amountSumReconciles": columnar_diag.get("amountSumReconciles"),
            "amountSumActual": columnar_diag.get("amountSumActual"),
            "amountSumTarget": columnar_diag.get("amountSumTarget"),
        }
    release_pass, release_fail_reasons, release_decision = _evaluate_release_threshold(
        table_rows,
        table_candidate_diagnostics.get("fieldQuality"),
        columnar_context=columnar_context_for_release,
    )
    table_candidate_diagnostics["releaseDecision"] = release_decision
    line_count = len(lines)
    ctx = dict(context or {})
    image_wh = list(image_size) if image_size is not None else None
    template_mode = bool(ctx.get("templateMode") or ctx.get("template_id") or ctx.get("templateId"))

    if _is_controlled_success_enabled() and doc_type == "invoice_statement" and not template_mode:
        return _build_success_invoice_statement_free_result(
            table_rows=_build_controlled_success_rows(),
            confidence=1.0,
            extract_debug={
                "invoice_statement_free": {
                    "controlled": True,
                    "controlledFlag": "USE_INVOICE_STATEMENT_FREE_CONTROLLED_SUCCESS",
                    "controlledReason": "route_smoke_2h",
                }
            },
        )

    if candidates["businessNumbers"]:
        result["supplierBizNumber"] = candidates["businessNumbers"][0]
    if candidates["companyCandidates"]:
        result["supplierCompany"] = candidates["companyCandidates"][0]
    if candidates["amountCandidates"]:
        result["totalAmount"] = candidates["amountCandidates"][0]

    fallback_required = not (release_pass and doc_type == "invoice_statement" and not template_mode)
    result["tableMeta"] = {
        **deepcopy(result["tableMeta"]),
        "inputLineCount": line_count,
        "fullTextLength": len(normalized_full_text),
        "docType": doc_type,
        "imageSize": image_wh,
        "templateMode": template_mode,
        "fallbackRequired": fallback_required,
        "fallbackRecommendation": "" if not fallback_required else "existing_invoice_statement_parser",
        "source": "invoice_statement_free",
        "mode": "unstructured",
        "rowCount": len(table_rows),
        "columns": ["itemName", "spec", "lotNo", "expiryDate", "quantity", "unitPrice", "amount"] if table_rows else [],
        "expectedColumnKeys": ["itemName", "spec", "lotNo", "expiryDate", "quantity", "unitPrice", "amount"] if table_rows else [],
        "columnLabels": {
            "itemName": "품목명",
            "spec": "규격",
            "quantity": "수량",
            "unitPrice": "단가",
            "amount": "금액",
        } if table_rows else {},
    }
    result["tableRows"] = table_rows
    result["tableDetected"] = "Y" if table_rows else "N"
    result["rowCount"] = len(table_rows) if table_rows else ""
    result["firstRowPreview"] = table_rows[0]["_rawText"] if table_rows else ""
    document_fields = {key: deepcopy(result.get(key)) for key in DOCUMENT_FIELD_KEYS}
    free_debug_payload = {
        "status": "partial",
        "attempted": True,
        "used": False,
        "fallbackUsed": True,
        "fallbackReason": "release_threshold_failed" if release_fail_reasons else "not_guarded_release_context",
        "releaseDecision": release_decision,
        "candidates": candidates,
        "tableCandidates": {
            "rows": table_rows,
            "rowCount": len(table_rows),
            "parsedRowCount": len(parsed_table_rows),
            "meaningfulRowCount": table_candidate_diagnostics["meaningfulRowCount"],
            "status": "candidate_only",
            "diagnostics": table_candidate_diagnostics,
            "fieldQuality": table_candidate_diagnostics.get("fieldQuality"),
            "splitDiagnostics": table_candidate_diagnostics.get("splitDiagnostics"),
            "releaseDecision": release_decision,
            "columnar": columnar_diag,
        },
        "rowCount": len(table_rows),
        "fallbackRequired": True,
        "tokenBboxDebug": _build_token_bbox_debug(
            ocr_items,
            image_wh[0] if isinstance(image_wh, list) and len(image_wh) >= 2 else None,
            image_wh[1] if isinstance(image_wh, list) and len(image_wh) >= 2 else None,
        ),
        "gtSkeletonCandidates": _build_gt_skeleton_candidates(
            ocr_items,
            image_wh[0] if isinstance(image_wh, list) and len(image_wh) >= 2 else None,
            image_wh[1] if isinstance(image_wh, list) and len(image_wh) >= 2 else None,
            doc_type=doc_type,
        ),
    }
    if release_pass and doc_type == "invoice_statement" and not template_mode:
        reference_fields, reference_debug = _extract_reference_invoice_statement_fields(
            ocr_lines_raw, ctx
        )
        document_fields, scalar_merge_debug = _merge_invoice_statement_reference_scalars(
            document_fields, reference_fields
        )
        scalar_merge_debug["reference"] = reference_debug
        free_debug_payload.update(
            {
                "status": "success",
                "used": True,
                "fallbackUsed": False,
                "fallbackReason": "",
                "fallbackRequired": False,
                "scalarMerge": scalar_merge_debug,
            }
        )
        return _build_success_invoice_statement_free_result(
            table_rows=table_rows,
            document_fields=document_fields,
            confidence=0.65,
            extract_debug={"invoice_statement_free": free_debug_payload},
        )

    result["document_fields"] = document_fields
    result["extract_debug"] = {
        "invoice_statement_free": free_debug_payload
    }
    result["confidence"] = 0.0
    return result


def extract_invoice_statement_free_fields(**kwargs: Any) -> dict[str, Any]:
    """Compatibility alias for the dispatch name proposed during precheck."""

    return extract_invoice_statement_free(**kwargs)


__all__ = [
    "DOCUMENT_FIELD_KEYS",
    "REFERENCE_SCALAR_MERGE_KEYS",
    "REFERENCE_SCALAR_MERGE_EXCLUDED_KEYS",
    "TABLE_ROW_KEYS",
    "_build_table_candidate_diagnostics",
    "_extract_reference_invoice_statement_fields",
    "_merge_invoice_statement_reference_scalars",
    "_extract_line_texts",
    "_extract_ocr_line_items",
    "_extract_text_from_ocr_line",
    "_evaluate_release_threshold",
    "_filter_table_row_candidates",
    "_find_amount_candidates",
    "_find_business_numbers",
    "_find_company_candidates",
    "_find_table_row_candidates",
    "_build_success_invoice_statement_free_result",
    "_build_controlled_success_rows",
    "_build_code_vs_money_diagnostics",
    "_classify_numeric_like_token",
    "_is_release_ready_table_row",
    "_is_code_like_non_money_token",
    "_is_controlled_success_enabled",
    "_is_meaningful_table_row",
    "_is_plausible_invoice_item_row",
    "_is_valid_invoice_statement_free_result",
    "_score_invoice_item_row",
    "_normalize_candidate_row",
    "_normalize_item_name",
    "_normalize_money",
    "_normalize_quantity",
    "_normalize_spec",
    "_summarize_candidate_field_quality",
    "_join_lines",
    "_normalize_text",
    "empty_invoice_statement_free_result",
    "extract_invoice_statement_free",
    "extract_invoice_statement_free_fields",
]
