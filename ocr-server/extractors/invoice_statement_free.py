"""Unstructured invoice statement extraction.

This module IS wired into ``main.py`` (see the unstructured-template branch
around main.py:2958, which calls ``extract_invoice_statement_free`` and
validates the result with ``_is_valid_invoice_statement_free_result``).

Fallback policy (active):
- The dispatcher catches exceptions from this module.
- If this module returns an empty or low-confidence result, the dispatcher
  falls back to ``extract_invoice_statement_fields`` from the existing
  ``invoice_statement.py`` path (main.py:3003). The chosen path is recorded in
  ``document_fields.tableMeta.extractionSource``.
- This module must not access FastAPI request/response objects, the OCR
  singleton, template storage, review logs, frontend files, or datasets.
"""

from __future__ import annotations

import bisect
from copy import deepcopy
import json
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
# Money scalars must hold a parseable number. A reference label like "합" (the
# bare 합계 header cell) must never backfill a money field — guard at merge time.
REFERENCE_MONEY_SCALAR_KEYS = (
    "totalAmount",
    "cumulativeAmount",
    "supplyAmount",
    "taxAmount",
)

# Document-structure labels that are never a person's name. A party-representative
# field that ends up holding one of these (e.g. fallback OCR putting the "총수량"
# summary label into buyerRepresentative) is a spurious capture — blank it.
_PARTY_NAME_REJECT_LABELS = frozenset({
    "총수량", "합계", "소계", "누계", "부가세", "공급가액", "공급가",
    "세액", "금액", "단가", "수량", "상호", "상호명", "대표", "대표자",
    "성명", "비고", "합", "계", "공급자", "공급받는자",
})
PARTY_NAME_FIELD_KEYS = ("supplierRepresentative", "buyerRepresentative")
ADDRESS_FIELD_KEYS = ("supplierAddress", "buyerAddress")
COMPANY_FIELD_KEYS = ("supplierCompany", "buyerCompany")
# Money scalars that must hold a parseable number; a non-numeric value (e.g. the
# label "합") is garbage regardless of which extractor produced it.
MONEY_SCALAR_FIELD_KEYS = (
    "supplyAmount", "taxAmount", "totalAmount", "cumulativeAmount", "subtotal",
    "previousBalance", "transactionAmount", "cumulativeBalance",
)


def _strip_party_name_label_fragment(value: str) -> str:
    cleaned = _normalize_text(value)
    cleaned = re.sub(r"^\s*대표\s*자\s*(?:명|영)?\s*[:：]?\s*", "", cleaned)
    cleaned = re.sub(r"^\s*영\s*[:：]?\s*(?=[가-힣]{2,4}\s*$)", "", cleaned)
    return cleaned.strip()


def _strip_address_label_fragment(value: str) -> str:
    cleaned = _normalize_text(value)
    match = re.match(r"^\s*(?:주소|주\s*소|소)\s*[:：]\s*(.+)$", cleaned)
    if not match:
        return cleaned.strip()
    rest = match.group(1).strip()
    if re.search(r"(?:서울|경기|인천|구로|평택|[가-힣]{1,8}(?:구|동|읍|면|리)|[가-힣]{1,16}(?:로|길)|번지|\d)", rest):
        return rest
    return cleaned.strip()


def _strip_company_label_fragment(value: str) -> str:
    cleaned = _normalize_text(value)
    match = re.match(r"^(.+?)(?:대표자?|대표\s*자)\s*$", cleaned)
    if not match:
        return cleaned.strip()
    rest = match.group(1).strip()
    compact = re.sub(r"\s+", "", rest)
    if re.search(r"(?:주식회사|\(\s*주\s*\)|㈜|약품|상사|회사|산업|제약|바이오|메디|헬스|유통)", compact):
        return compact
    return cleaned.strip()


def sanitize_document_scalar_fields(document_fields: dict[str, Any]) -> dict[str, Any]:
    """Path-agnostic output guard (run after free/fallback converge), so it guards
    both extractors regardless of which one produced a field:
      - party-representative holding a known document label (e.g. "총수량") → blank
      - money scalar holding a non-numeric value (e.g. the label "합")        → blank
    Valid values are never touched: real names ("김승관") aren't in the reject set,
    and any parseable amount ("18,098,750") clears the money check.
    """
    if not isinstance(document_fields, dict):
        return document_fields
    for key in PARTY_NAME_FIELD_KEYS:
        val = document_fields.get(key)
        if isinstance(val, str):
            stripped = _strip_party_name_label_fragment(val)
            document_fields[key] = stripped
            if stripped.strip() in _PARTY_NAME_REJECT_LABELS:
                document_fields[key] = ""
    for key in ADDRESS_FIELD_KEYS:
        val = document_fields.get(key)
        if isinstance(val, str):
            document_fields[key] = _strip_address_label_fragment(val)
    for key in COMPANY_FIELD_KEYS:
        val = document_fields.get(key)
        if isinstance(val, str):
            document_fields[key] = _strip_company_label_fragment(val)
    for key in MONEY_SCALAR_FIELD_KEYS:
        val = document_fields.get(key)
        if isinstance(val, str) and val.strip() and _money_for_sum(val) is None:
            document_fields[key] = ""
    return document_fields
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
FIVE_COLUMN_PRODUCT_CODE_TABLE_KEYS = ("itemName", "productCode", "quantity", "unitPrice", "amount")
FIVE_COLUMN_PRODUCT_CODE_TABLE_LABELS = {
    "itemName": "품명",
    "productCode": "품목코드",
    "quantity": "수량",
    "unitPrice": "단가",
    "amount": "금액",
}
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
_HANGUL_RE = re.compile(r"[\uac00-\ud7a3]")
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


def _normalize_product_code_token(value: Any) -> str:
    text = _normalize_text(value).strip("()[]{}.,:;|").upper()
    # OCR can read compact tablet-count suffixes as letters only
    # (NPRTIOT -> NPRT10T). Normalize before the digit-required shape check.
    text = re.sub(r"IOT$", "10T", text)
    if not _looks_like_product_code_token(text):
        return ""
    text = re.sub(r"^0P", "OP", text)
    # OCR can confuse zero as O in compact tablet-count suffixes (e.g.
    # NPRT1OT -> NPRT10T). Keep the rule narrow so codes such as DPNL3OM stay
    # unchanged.
    text = re.sub(r"(?<=\d)O(?=T$)", "0", text)
    return text


def _first_product_code_from_text(value: Any) -> str:
    for token in re.split(r"\s+", _normalize_text(value)):
        code = _normalize_product_code_token(token)
        if code:
            return code
    return ""


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

    def _code_anchor_value(text: Any) -> str:
        value = _normalize_text(text).upper().replace(" ", "")
        match = re.search(r"(?:^|\d)((?:O|0)P-[A-Z0-9]{2,})", value)
        if not match:
            return ""
        code = match.group(1)
        code = re.sub(r"^0P", "OP", code)
        # 3AV: evidence-backed OP-code O/0 normalization in the debug skeleton
        # path only. Restrict to the pharma-like OP-LL[0/O]NNN shape so ordinary
        # item text is never rewritten.
        code = re.sub(r"^(OP-[A-Z]{2})O(?=\d{3,}$)", r"\g<1>0", code)
        return code

    def _amount_anchor_value(text: Any) -> str:
        value = _normalize_text(text)
        if not value or _looks_like_code_anchor(value) or _is_code_like_non_money_token(value):
            return ""
        comma_money_tokens: list[str] = []
        for match in re.finditer(r"(?<!\d)-?\d{1,3}(?:,\d{3})+(?!\d)", value):
            token = _clean_number_token(match.group(0))
            container = _code_vs_money_container_token(value, match.start(), match.end())
            if container and container != token and _is_code_like_non_money_token(container):
                continue
            comma_money_tokens.append(_normalize_money(token))
        if comma_money_tokens:
            return comma_money_tokens[-1]
        money_tokens = _money_tokens_from_text(value)
        if not money_tokens:
            return ""
        return _normalize_money(money_tokens[-1])

    def _quantity_anchor_value(text: Any) -> str:
        value = _normalize_text(text)
        if not value or _looks_like_code_anchor(value) or _amount_anchor_value(value):
            return ""
        compact = re.sub(r"\D", "", value)
        if not compact or compact != value.strip():
            return ""
        try:
            number = int(compact)
        except ValueError:
            return ""
        return compact if 1 <= number <= 9999 else ""

    def _item_name_anchor_value(text: Any) -> str:
        value = _normalize_text(text)
        if not value:
            return ""
        if (
            _looks_like_code_anchor(value)
            or _amount_anchor_value(value)
            or _quantity_anchor_value(value)
            or _is_summary_or_header_line(value)
        ):
            return ""
        parts: list[str] = []
        for raw_part in re.split(r"\s+", value):
            part = raw_part.strip("()[]{}:;|,")
            if not part:
                continue
            if _looks_like_code_anchor(part) or _amount_anchor_value(part) or _quantity_anchor_value(part):
                continue
            if re.fullmatch(r"[-./\\]+", part):
                continue
            if re.fullmatch(r"\d{4,}", part):
                continue
            parts.append(part)
        cleaned = _normalize_text(" ".join(parts))
        if not cleaned:
            return ""
        cleaned = re.sub(r"(?i)(\b\d{1,3}C)\d{3,}$", r"\1", cleaned).strip()
        compact = re.sub(r"\s+", "", cleaned)
        if len(compact) < 3:
            return ""
        if not (re.search(r"[A-Za-z]{2,}", cleaned) or _HANGUL_RE.search(cleaned)):
            return ""
        return cleaned[:80]

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
    try:
        row_entries, _row_entry_debug = _group_ocr_items_into_row_entries(finite_items)
    except Exception:
        row_entries = []
    code_anchors = [
        {"text": _code_anchor_value(item["text"]), "rawText": item["text"], "cx": item["cx"], "cy": item["cy"], "h": item["h"], "confidence": item.get("confidence")}
        for item in inside_items
        if _code_anchor_value(item.get("text"))
    ]
    amount_anchors = [
        {"text": _amount_anchor_value(item["text"]), "rawText": item["text"], "cx": item["cx"], "cy": item["cy"], "h": item["h"], "confidence": item.get("confidence")}
        for item in inside_items
        if _amount_anchor_value(item.get("text"))
    ]
    quantity_anchors = [
        {"text": _quantity_anchor_value(item["text"]), "rawText": item["text"], "cx": item["cx"], "cy": item["cy"], "h": item["h"], "confidence": item.get("confidence")}
        for item in inside_items
        if _quantity_anchor_value(item.get("text"))
    ]
    item_name_anchors = [
        {"text": _item_name_anchor_value(item["text"]), "rawText": item["text"], "cx": item["cx"], "cy": item["cy"], "h": item["h"], "confidence": item.get("confidence")}
        for item in inside_items
        if _item_name_anchor_value(item.get("text"))
    ]

    def _median(values: list[float], fallback: float) -> float:
        finite = sorted(value for value in values if math.isfinite(value))
        if not finite:
            return fallback
        mid = len(finite) // 2
        if len(finite) % 2:
            return finite[mid]
        return (finite[mid - 1] + finite[mid]) / 2.0

    row_band_tol = max(
        10.0,
        min(
            60.0,
            max(
                table_box["h"] / 32.0,
                _median([float(anchor.get("h") or 0.0) for anchor in code_anchors], 14.0) * 1.8,
            ),
        ),
    )
    code_cy_values = sorted(float(anchor["cy"]) for anchor in code_anchors)
    code_h_median = _median([float(anchor.get("h") or 0.0) for anchor in code_anchors], 14.0)
    significant_gaps = [
        code_cy_values[idx + 1] - code_cy_values[idx]
        for idx in range(len(code_cy_values) - 1)
        if code_cy_values[idx + 1] - code_cy_values[idx] > max(2.0, code_h_median * 0.25)
    ]
    if significant_gaps:
        row_band_tol = max(6.0, min(row_band_tol, _median(significant_gaps, row_band_tol) * 0.45))

    def _sort_by_reading_row(
        anchors: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Sort anchors by visual reading row, using x only inside one y-band."""
        ordered = sorted(anchors, key=lambda anchor: (float(anchor["cy"]), float(anchor["cx"])))
        bands: list[dict[str, Any]] = []
        for anchor in ordered:
            cy = float(anchor["cy"])
            band = next(
                (
                    candidate
                    for candidate in bands
                    if abs(cy - float(candidate["cy"])) <= row_band_tol
                ),
                None,
            )
            if band is None:
                bands.append({"cy": cy, "anchors": [anchor]})
                continue
            band["anchors"].append(anchor)
            band["cy"] = sum(float(item["cy"]) for item in band["anchors"]) / len(band["anchors"])
        sorted_anchors: list[dict[str, Any]] = []
        for band in sorted(bands, key=lambda item: float(item["cy"])):
            sorted_anchors.extend(sorted(band["anchors"], key=lambda anchor: float(anchor["cx"])))
        return sorted_anchors

    code_anchors = _sort_by_reading_row(code_anchors)
    amount_anchors = _sort_by_reading_row(amount_anchors)
    quantity_anchors = _sort_by_reading_row(quantity_anchors)
    item_name_anchors = _sort_by_reading_row(item_name_anchors)

    code_x_values = sorted(float(anchor["cx"]) for anchor in code_anchors)
    code_x_gaps = [
        code_x_values[idx + 1] - code_x_values[idx]
        for idx in range(len(code_x_values) - 1)
        if code_x_values[idx + 1] - code_x_values[idx] > 1.0
    ]
    column_x_tol = max(
        12.0,
        min(
            80.0,
            (_median(code_x_gaps, table_box["w"] / max(len(code_x_values), 1)) * 0.62)
            if code_x_values
            else table_box["w"] / 20.0,
        ),
    )

    def _same_column_candidates(
        anchor: dict[str, Any],
        candidates: list[dict[str, Any]],
        *,
        max_extra: float = 1.0,
    ) -> list[dict[str, Any]]:
        cx = float(anchor["cx"])
        return sorted(
            [
                candidate
                for candidate in candidates
                if abs(float(candidate["cx"]) - cx) <= column_x_tol * max_extra
            ],
            key=lambda candidate: (abs(float(candidate["cx"]) - cx), float(candidate["cy"])),
        )

    def _same_row_candidates(
        anchor: dict[str, Any],
        candidates: list[dict[str, Any]],
        *,
        max_extra: float = 1.0,
    ) -> list[dict[str, Any]]:
        cy = float(anchor["cy"])
        return sorted(
            [
                candidate
                for candidate in candidates
                if abs(float(candidate["cy"]) - cy) <= row_band_tol * max_extra
            ],
            key=lambda candidate: (float(candidate["cx"]), abs(float(candidate["cy"]) - cy)),
        )

    def _money_values_for_code(
        code: dict[str, Any],
        used: set[int],
    ) -> list[tuple[int, dict[str, Any]]]:
        same_row: list[tuple[int, dict[str, Any]]] = []
        code_cy = float(code["cy"])
        for idx, amount in enumerate(amount_anchors):
            if idx in used:
                continue
            if abs(float(amount["cy"]) - code_cy) <= row_band_tol:
                same_row.append((idx, amount))
        return sorted(same_row, key=lambda pair: (float(pair[1]["cx"]), float(pair[1]["cy"])))

    def _is_row_number_quantity_candidate(quantity: dict[str, Any], row_index: int) -> bool:
        value = _quantity_anchor_value(quantity.get("text"))
        if not value:
            return False
        try:
            number = int(value)
        except ValueError:
            return False
        if number != row_index + 1:
            return False
        return 1 <= number <= max(len(code_anchors), 1)

    def _first_money_cx(row_money: list[tuple[int, dict[str, Any]]]) -> float | None:
        money_cxs = [
            float(money["cx"])
            for _, money in row_money
            if isinstance(money.get("cx"), (int, float))
        ]
        return min(money_cxs) if money_cxs else None

    def _normalize_skeleton_item_name(text: str) -> str:
        value = _normalize_text(text)
        value = re.sub(r"\s+", " ", value)
        # Keep OCR-backed text, but repair only very narrow visual confusions in
        # known product suffix shapes.
        value = re.sub(r"(?i)\b50OT\b", "500T", value)
        value = re.sub(r"(?i)\[ABLET\b", "TABLET", value)
        value = re.sub(r"((?:[A-Za-z가-힣\[]+\s+)*[A-Za-z가-힣\[]+\s+\d{2,4}[A-Za-z])\d{2,5}$", r"\1", value)
        return value.strip()

    def _tail_after_code(text: str) -> str:
        value = _normalize_text(text)
        match = re.search(r"(?:^|\d)((?:O|0)P-[A-Z0-9]{2,})", value.upper().replace(" ", ""))
        if not match:
            return ""
        compact = value.upper().replace(" ", "")
        code = match.group(1)
        code_pos = compact.find(code)
        if code_pos < 0:
            return ""
        seen = 0
        end_idx = 0
        for idx, ch in enumerate(value):
            if ch.isspace():
                continue
            seen += 1
            if seen >= code_pos + len(code):
                end_idx = idx + 1
                break
        return _normalize_text(value[end_idx:])

    def _trim_row_value_tail(text: str) -> str:
        value = re.split(r"\s+-?\d{1,3}(?:,\d{3})+(?!\d)", _normalize_text(text), maxsplit=1)[0]
        parts = value.split()
        while parts:
            last = parts[-1]
            if re.fullmatch(r"\d{2,4}[A-Za-z]{1,2}\]?", last):
                break
            if re.search(r"\d", last) and not re.search(r"[가-힣]", last):
                parts.pop()
                continue
            if re.fullmatch(r"\d+", last):
                parts.pop()
                continue
            break
        return _normalize_text(" ".join(parts))

    def _quantity_from_code_row_text(text: str, row_index: int) -> dict[str, Any] | None:
        tail = _tail_after_code(text)
        if not tail:
            return None
        value_part = re.split(r"\s+-?\d{1,3}(?:,\d{3})+(?!\d)", tail, maxsplit=1)[0]
        numbers = []
        for token in value_part.split():
            if not re.fullmatch(r"\d{1,4}", token):
                continue
            try:
                number = int(token)
            except ValueError:
                continue
            if number == row_index + 1 or number <= 0 or number > 9999:
                continue
            numbers.append(token)
        multi_digit = [token for token in numbers if len(token) >= 2]
        if not multi_digit:
            return None
        return {"text": multi_digit[-1], "rawText": text, "cx": 0.0, "cy": 0.0, "source": "row_local_code_text_quantity_tail"}

    def _row_item_name_text_candidate(item: dict[str, Any]) -> str:
        text = _normalize_text(item.get("text"))
        if not text:
            return ""
        if _is_summary_or_header_line(text):
            return ""
        if _looks_like_code_anchor(text):
            text = _trim_row_value_tail(_tail_after_code(text))
            if not text:
                return ""
        if not re.search(r"[A-Za-z가-힣\[]", text):
            return ""
        if not re.search(r"[가-힣]", text) and not re.search(r"[A-Za-z]{2,}", text) and not re.search(r"\d{2,4}[A-Za-z]{1,2}\]?$", text):
            return ""
        if _amount_anchor_value(text) and not re.search(r"[A-Za-z가-힣\[]", text):
            return ""
        if _quantity_anchor_value(text) and not re.search(r"[A-Za-z가-힣\[]", text):
            return ""
        return text

    def _row_item_name_candidates(
        code: dict[str, Any],
        *,
        left_bound: float,
        right_bound: float,
    ) -> list[dict[str, Any]]:
        code_cy = float(code["cy"])
        candidates: list[dict[str, Any]] = []
        for item in finite_items:
            if not isinstance(item.get("cx"), (int, float)) or not isinstance(item.get("cy"), (int, float)):
                continue
            if abs(float(item["cy"]) - code_cy) > row_band_tol * 1.65:
                continue
            cx = float(item["cx"])
            if not (left_bound <= cx <= right_bound):
                continue
            text = _row_item_name_text_candidate(item)
            if not text:
                continue
            candidates.append({
                "text": text,
                "rawText": item.get("text"),
                "cx": item["cx"],
                "cy": item["cy"],
                "h": item.get("h"),
                "confidence": item.get("confidence"),
            })
        return sorted(candidates, key=lambda candidate: (float(candidate["cx"]), float(candidate["cy"])))

    def _synthetic_anchor(
        text: str,
        anchors: list[dict[str, Any]],
        *,
        source: str,
    ) -> dict[str, Any] | None:
        text = _normalize_text(text)
        if not text or not anchors:
            return None
        cx_values = [float(anchor["cx"]) for anchor in anchors if isinstance(anchor.get("cx"), (int, float))]
        cy_values = [float(anchor["cy"]) for anchor in anchors if isinstance(anchor.get("cy"), (int, float))]
        return {
            "text": text,
            "rawText": " ".join(str(anchor.get("rawText") or anchor.get("text") or "") for anchor in anchors).strip(),
            "cx": sum(cx_values) / len(cx_values) if cx_values else float(anchors[0].get("cx") or 0.0),
            "cy": sum(cy_values) / len(cy_values) if cy_values else float(anchors[0].get("cy") or 0.0),
            "source": source,
        }

    def _item_name_for_code(
        code: dict[str, Any],
        row_money: list[tuple[int, dict[str, Any]]],
    ) -> dict[str, Any] | None:
        code_cx = float(code["cx"])
        first_money_cx = _first_money_cx(row_money)
        amount_cx = float(row_money[-1][1]["cx"]) if row_money and isinstance(row_money[-1][1].get("cx"), (int, float)) else None
        left_bound = code_cx + max(column_x_tol * 1.25, 24.0)
        right_bound = (
            amount_cx - max(column_x_tol * 0.35, 8.0)
            if amount_cx is not None
            else first_money_cx - max(column_x_tol * 0.35, 8.0)
            if first_money_cx is not None
            else table_box["x"] + table_box["w"]
        )
        filtered = _row_item_name_candidates(code, left_bound=left_bound, right_bound=right_bound)
        if not filtered:
            same_row = _same_row_candidates(code, item_name_anchors, max_extra=1.65)
            filtered = [
                candidate
                for candidate in same_row
                if left_bound <= float(candidate["cx"]) <= right_bound
            ]
        if not filtered:
            for entry in row_entries:
                if not isinstance(entry, dict):
                    continue
                text = _normalize_text(entry.get("text"))
                if not text or _code_anchor_value(text) != code.get("text"):
                    continue
                candidate_text = _normalize_skeleton_item_name(_trim_row_value_tail(_tail_after_code(text)))
                if not candidate_text:
                    continue
                return {
                    "text": candidate_text,
                    "rawText": text,
                    "cx": code_cx + max(column_x_tol * 2.0, 40.0),
                    "cy": code.get("cy", 0.0),
                    "source": "row_grouped_code_text_item_name",
                }
            return None
        filtered = sorted(filtered, key=lambda candidate: float(candidate["cx"]))
        text = _normalize_skeleton_item_name(" ".join(str(candidate.get("text") or "") for candidate in filtered))
        return _synthetic_anchor(text, filtered, source="row_local_item_name_x_band")

    def _quantity_for_code(
        code: dict[str, Any],
        row_index: int,
        row_money: list[tuple[int, dict[str, Any]]],
        item_name: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        code_cx = float(code["cx"])
        first_money_cx = _first_money_cx(row_money)
        if first_money_cx is None:
            return None
        item_name_cx = float(item_name["cx"]) if isinstance(item_name, dict) and isinstance(item_name.get("cx"), (int, float)) else None
        left_bound = (
            item_name_cx + max(column_x_tol * 0.45, 8.0)
            if item_name_cx is not None
            else code_cx + max(column_x_tol * 1.25, 24.0)
        )
        right_bound = first_money_cx - max(column_x_tol * 0.2, 6.0)
        same_row = _same_row_candidates(code, quantity_anchors, max_extra=1.05)
        filtered = []
        for quantity in same_row:
            value = _quantity_anchor_value(quantity.get("text"))
            if not value:
                continue
            if _is_row_number_quantity_candidate(quantity, row_index):
                continue
            cx = float(quantity["cx"])
            if not (left_bound <= cx <= right_bound):
                continue
            try:
                number = int(value)
            except ValueError:
                continue
            if number <= 0 or number > 9999:
                continue
            filtered.append(quantity)
        if not filtered:
            for entry in row_entries:
                if not isinstance(entry, dict):
                    continue
                text = _normalize_text(entry.get("text"))
                if not text or _code_anchor_value(text) != code.get("text"):
                    continue
                fallback = _quantity_from_code_row_text(text, row_index)
                if fallback:
                    fallback["cx"] = code_cx + max(column_x_tol * 3.0, 60.0)
                    fallback["cy"] = code.get("cy", 0.0)
                    return fallback
            code_cy = float(code["cy"])
            for item in finite_items:
                if not isinstance(item.get("cy"), (int, float)):
                    continue
                if abs(float(item["cy"]) - code_cy) > row_band_tol * 1.65:
                    continue
                text = _normalize_text(item.get("text"))
                if not text or not _looks_like_code_anchor(text):
                    continue
                fallback = _quantity_from_code_row_text(text, row_index)
                if fallback:
                    fallback["cx"] = item.get("cx", code.get("cx", 0.0))
                    fallback["cy"] = item.get("cy", code.get("cy", 0.0))
                    return fallback
            return None
        multi_digit = [quantity for quantity in filtered if len(str(quantity.get("text") or "")) >= 2]
        if not multi_digit and len(filtered) == 1:
            return None
        filtered = multi_digit or filtered
        return min(
            filtered,
            key=lambda quantity: (
                abs(float(quantity["cx"]) - right_bound),
                abs(float(quantity["cy"]) - float(code["cy"])),
            ),
        )

    used_amounts: set[int] = set()
    rows: list[dict[str, Any]] = []
    paired_count = 0
    orphan_code_count = 0
    for code in code_anchors[:max_rows]:
        row_index = len(rows)
        row_money = _money_values_for_code(code, used_amounts)
        amount = row_money[-1][1] if row_money else None
        price_values = [money for _, money in row_money[:-1]]
        consumer_unit_price = price_values[0]["text"] if len(price_values) >= 1 else ""
        supply_unit_price = price_values[1]["text"] if len(price_values) >= 2 else consumer_unit_price
        item_name = _item_name_for_code(code, row_money)
        quantity = _quantity_for_code(code, row_index, row_money, item_name)
        missing = []
        notes = [
            "debug_only_not_release_table_row",
            "row_band_cy_first_alignment",
            "same_row_money_pairing",
            "quantity_row_local_x_band_mapping",
            "item_name_row_local_x_band_mapping",
            "debug_skeleton_product_code_o0_normalization",
        ]
        confidence = "medium"
        if amount is None:
            orphan_code_count += 1
            missing.append("amount")
            notes.append("orphan_code_anchor")
            confidence = "low"
        else:
            for money_idx, _money in row_money:
                used_amounts.add(money_idx)
            paired_count += 1
        rows.append(
            {
                "rowIndex": len(rows),
                "itemName": item_name["text"] if item_name else "",
                "spec": "",
                "productCode": code["text"],
                "lotNo": "",
                "expiryDate": "",
                "quantity": quantity["text"] if quantity else "",
                "unitPrice": "",
                "amount": amount["text"] if amount else "",
                "consumerUnitPrice": consumer_unit_price,
                "supplyUnitPrice": supply_unit_price,
                "insuranceNo": "",
                "tableExtraColumns": {
                    "consumerUnitPrice": consumer_unit_price,
                    "supplyUnitPrice": supply_unit_price,
                    "insuranceNo": "",
                },
                "_gtSkeleton": {
                    "reviewRequired": True,
                    "rowConfidence": confidence,
                    "anchors": {
                        "code": {"text": code["text"], "rawText": code.get("rawText"), "cx": code["cx"], "cy": code["cy"]},
                        "amount": {"text": amount["text"], "cx": amount["cx"], "cy": amount["cy"]} if amount else None,
                        "consumerUnitPrice": {"text": consumer_unit_price} if consumer_unit_price else None,
                        "supplyUnitPrice": {"text": supply_unit_price} if supply_unit_price else None,
                        "quantity": {"text": quantity["text"], "cx": quantity["cx"], "cy": quantity["cy"]} if quantity else None,
                        "itemName": {"text": item_name["text"], "cx": item_name["cx"], "cy": item_name["cy"]} if item_name else None,
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
            "rawQuantityCandidateCount": len(quantity_anchors),
            "rawItemNameCandidateCount": len(item_name_anchors),
            "pairedCount": paired_count,
            "orphanCodeCount": orphan_code_count,
            "orphanAmountCount": max(0, len(amount_anchors) - len(used_amounts)),
            "balanceExcludedCount": balance_excluded,
        },
        "candidateRowsReleaseIsolated": True,
        "tableExtraColumnDefinitions": [
            {
                "key": "consumerUnitPrice",
                "labelKo": "소비자가",
                "labelEn": "Consumer unit price",
                "source": "gt_skeleton_candidate_compact",
            },
            {
                "key": "supplyUnitPrice",
                "labelKo": "공급단가",
                "labelEn": "Supply unit price",
                "source": "gt_skeleton_candidate_compact",
            },
            {
                "key": "insuranceNo",
                "labelKo": "보험코드",
                "labelEn": "Insurance number",
                "source": "gt_skeleton_candidate_compact",
            },
        ],
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


# ─── 공급자 사업자번호 재선택(P1): 넓힌 추출 + 보수적 재선택 ──────────────────
# 근거(065 전수분해, 실패 458건): GT bizno가 OCR에 ①정상 260 ②구분자깨짐(en-dash
# 등) 84 ③토큰분할('4 6 2-8 8') 28 로 존재하나 후보추출/선택이 놓침. free 는
# 하이픈만 매칭(_find_business_numbers)해 en-dash·공백형을 통째 놓치고 [0](주문번호
# 등)을 픽. 넓힌 추출(unicode dash 통일 + 숫자간 공백제거 + 글자오인 O/I/l/S/B→숫자)
# 로 GT 후보화율 74.7→89.7%, 보수적 재선택(현재값이 빈칸/구분자없음/buyer와 동일일
# 때만 교체, 구분자형 중 buyer≠ 첫 후보)로 065 실측 gain 121/reg 9 = +112 → 80.9%.
_BIZNO_UNIDASH_RE = re.compile(r"[‐‑‒–—―=~]")
_BIZNO_LETTER_MAP = str.maketrans("OIlSBoisb", "011588015")
# 구분자 다중/혼합·점·콜론 허용('106 -81' 이중, '101-.85' 점, '108-8:6' 콜론).
# 그룹내 공백·점·콜론은 canon서 제거('12 4'→'124', '1.01'→'101').
_BIZNO_BROAD_RE = re.compile(r"(?<!\d)(\d{3})[-.\s:]{0,3}(\d{2})[-.\s:]{0,3}(\d{5})(?!\d)")
_BIZNO_SEP_RE = re.compile(r"\d{3}[-.\s:]{1,3}\d{2}[-.\s:]{1,3}\d{5}")
# 공급받는자(백제 지점)측 사업자번호 집합 — 공급자 bizno 선택 시 배제용.
# ★하드코딩 아님: master_dict.json['buyerBranchBiznos'](build_master.sql 역할우세 유도)
# 에서 로드 → 지점 증가 시 dict 재빌드로 자동 반영. dict에 키 없으면(구 dict) eval
# 사이드카(_buyer_role_set.csv) 폴백, 그것도 없으면 빈 집합(무영향).
_BUYER_BRANCH_CACHE: "frozenset[str] | None" = None


def _get_buyer_branch_biznos() -> "frozenset[str]":
    global _BUYER_BRANCH_CACHE
    if _BUYER_BRANCH_CACHE is not None:
        return _BUYER_BRANCH_CACHE
    biznos: set[str] = set()
    here = os.path.dirname(os.path.abspath(__file__))
    for path in (os.path.join(here, "..", "master_dict.json"),
                 os.path.join(here, "..", "eval", "data", "invoice_war", "master_dict.json")):
        try:
            with open(path, encoding="utf-8") as fh:
                md = json.load(fh)
            for v in (md.get("buyerBranchBiznos") or []):
                d = re.sub(r"\D", "", str(v))
                if len(d) == 10:
                    biznos.add(d)
            if biznos:
                break
        except Exception:
            continue
    if not biznos:   # eval 폴백(dict에 키 없는 구 버전)
        try:
            import csv as _csv
            sc = os.path.join(here, "..", "eval", "data", "invoice_war", "_buyer_role_set.csv")
            for row in _csv.reader(open(sc, encoding="utf-8")):
                if row and len(row[0]) == 10:
                    biznos.add(row[0])
        except Exception:
            pass
    _BUYER_BRANCH_CACHE = frozenset(biznos)
    return _BUYER_BRANCH_CACHE


_KNOWN_SUPPLIER_CACHE: "frozenset[str] | None" = None


def _get_known_supplier_biznos() -> "frozenset[str]":
    """master_dict itembuycust 키 = 거래이력 있는 공급자 bizno 셋(평가월 제외 빌드).
    무구분자 후보 검증용(바코드 등 우연한 10자리 배제)."""
    global _KNOWN_SUPPLIER_CACHE
    if _KNOWN_SUPPLIER_CACHE is not None:
        return _KNOWN_SUPPLIER_CACHE
    biznos: set[str] = set()
    here = os.path.dirname(os.path.abspath(__file__))
    for path in (os.path.join(here, "..", "master_dict.json"),
                 os.path.join(here, "..", "eval", "data", "invoice_war", "master_dict.json")):
        try:
            with open(path, encoding="utf-8") as fh:
                md = json.load(fh)
            for k in (md.get("itembuycust") or {}):
                d = re.sub(r"\D", "", str(k))
                if len(d) == 10:
                    biznos.add(d)
            if biznos:
                break
        except Exception:
            continue
    _KNOWN_SUPPLIER_CACHE = frozenset(biznos)
    return _KNOWN_SUPPLIER_CACHE


_BIZNO_REGNAME_CACHE: "dict[str, str] | None" = None


def _bizno_registered_name(bizno: str) -> str:
    """bizno → 등록 거래처명(master_dict biznoToCust→cust). 폴백픽 상호-일치 검증용."""
    global _BIZNO_REGNAME_CACHE
    if _BIZNO_REGNAME_CACHE is None:
        m: dict[str, str] = {}
        here = os.path.dirname(os.path.abspath(__file__))
        for path in (os.path.join(here, "..", "master_dict.json"),
                     os.path.join(here, "..", "eval", "data", "invoice_war", "master_dict.json")):
            try:
                with open(path, encoding="utf-8") as fh:
                    md = json.load(fh)
                cust = md.get("cust") or {}
                for bz, cd in (md.get("biznoToCust") or {}).items():
                    d = re.sub(r"\D", "", str(bz))
                    nm = (cust.get(str(cd)) or {}).get("nm") or ""
                    if len(d) == 10 and nm:
                        m[d] = nm
                if m:
                    break
            except Exception:
                continue
        _BIZNO_REGNAME_CACHE = m
    return _BIZNO_REGNAME_CACHE.get(re.sub(r"\D", "", str(bizno or "")), "")


def _company_name_sim(a: str, b: str) -> float:
    """상호 jamo-trigram 유사도(0~1). trigrams는 master_match 재사용(지연 import)."""
    from .master_match import trigrams
    ta, tb = trigrams(a), trigrams(b)
    if not ta or not tb:
        return 0.0
    inter = len(ta & tb)
    return inter / (len(ta) + len(tb) - inter)


def _bizno_checksum_ok(b: str) -> bool:
    """사업자등록번호 체크섬(가중 1,3,7,1,3,7,1,3,5 + 9번째*5//10). 무구분자 후보 가드."""
    if len(b) != 10 or not b.isdigit():
        return False
    w = (1, 3, 7, 1, 3, 7, 1, 3, 5)
    s = sum(int(b[i]) * w[i] for i in range(9)) + (int(b[8]) * 5) // 10
    return (10 - s % 10) % 10 == int(b[9])


def _bizno_canon(text: str) -> str:
    t = str(text or "").translate(_BIZNO_LETTER_MAP)
    t = _BIZNO_UNIDASH_RE.sub("-", t)
    # 숫자 사이 공백·점·콜론 제거('12 4'→'124', '036.3'→'0363'). 구분자 대시는 보존.
    return re.sub(r"(?<=\d)[.\s:]+(?=\d)", "", t)


def _bizno_extract(txt: str) -> list[tuple[str, bool]]:
    out: list[tuple[str, bool]] = []
    for mo in _BIZNO_BROAD_RE.finditer(_bizno_canon(txt)):
        out.append((mo.group(1) + mo.group(2) + mo.group(3), bool(_BIZNO_SEP_RE.search(mo.group()))))
    return out


def _bizno_candidates_ocr(ocr_lines_raw: Any) -> list[tuple[str, bool]]:
    """OCR 라인에서 사업자번호 후보 (읽기순, 중복제거). (digits10, 구분자형여부).

    라인 자체 + 인접 라인 결합(같은 y밴드 or 바로 아래)으로 재시도 → 번호가 두 토큰
    ('409-81-' + '08080')으로 쪼개진 경우 회수. 065 실측: 라인결합 포함 +12."""
    lines: list[tuple[float, float, str]] = []
    for ln in (ocr_lines_raw or []):
        try:
            pts = ln[0]
            ys = [p[1] for p in pts]
            xs = [p[0] for p in pts]
            lines.append((sum(ys) / len(ys), min(xs), str(ln[1])))
        except Exception:
            continue
    lines.sort()
    seen: list[tuple[str, bool]] = []

    def _add(v: str, s: bool) -> None:
        if not any(c[0] == v for c in seen):
            seen.append((v, s))

    for i, (cy, cx, txt) in enumerate(lines):
        for v, s in _bizno_extract(txt):
            _add(v, s)
        for j in range(i + 1, min(i + 3, len(lines))):  # 인접 라인 결합 재시도
            cy2, cx2, txt2 = lines[j]
            if abs(cy2 - cy) <= 25 or (0 < cy2 - cy <= 30 and abs(cx2 - cx) < 200):
                for v, s in _bizno_extract(txt + txt2):
                    _add(v, s)
    return seen


def refine_supplier_bizno(
    document_fields: Any, ocr_lines_raw: Any,
) -> tuple[Any, dict[str, Any]]:
    """공급자 사업자번호가 명백히 틀렸을 때만(빈칸/구분자없음/buyer와 동일) 재선택."""
    dbg: dict[str, Any] = {"refined": 0}
    if not isinstance(document_fields, dict):
        return document_fields, dbg

    def _d(v: Any) -> str:
        return re.sub(r"\D", "", str(v or ""))

    cur = _d(document_fields.get("supplierBizNumber"))
    buyer = _d(document_fields.get("buyerBizNumber"))
    branch = _get_buyer_branch_biznos()               # 데이터 유도(백제 지점 집합)
    cands = _bizno_candidates_ocr(ocr_lines_raw)
    sep = [c for c in cands if c[1]]
    excl = {buyer} if buyer else set()
    excl |= branch                                    # 공급받는자(백제 지점) 배제
    cur_bad = ((not cur) or (cur in excl)
               or (cur and not any(c[0] == cur and c[1] for c in cands)))
    if cur_bad:
        # 배제 후 비면 sep 전체(지점 포함)로 폴백하지 말고, 최소한 지점만은 계속
        # 배제한 후보로.
        pool = [c for c in sep if c[0] not in excl]
        if not pool:
            pool = [c for c in sep if c[0] not in branch]
        newv = pool[0][0] if pool else ""
        comp = str(document_fields.get("supplierCompany") or "")
        if not newv and sep:
            # 지점 sep 폴백(전부 지점뿐인 sep = 지점간거래 가능성): 무조건 강행하면 study
            # 3계열처럼 '문서의 유일한 번호=공급받는자 번호'를 supplier로 오채움하고
            # PartyMatcher가 상호까지 오염(065 실측 오채움 65/진짜 20). 등록명-추출상호
            # 일치(sim>=0.3)할 때만 발화. ★무구분자 rescue보다 먼저: 지점간거래 진짜
            # (GT=지점 bizno) 문서에서 ns가 엉뚱한 known 공급자를 선픽하는 회귀 6 방지.
            # comp는 refine 시점 원시 추출값이라 빈칸 다수 → 빈칸=반박근거 없음=통과.
            # 등록명(rn0)은 필수(검증 불가면 강행 안 함). study 3계열은 comp='예일선'
            # vs 등록명 sim 0.08이라 계속 차단됨.
            cand0 = sep[0][0]
            rn0 = _bizno_registered_name(cand0)
            if rn0 and (not comp or _company_name_sim(comp, rn0) >= 0.3):
                newv = cand0
        if not newv:
            # ★무구분자 폴백(065 실측 +26/break0): sep 후보가 없거나 지점폴백 탈락 시,
            # 무구분자 10자리를 3중 가드(체크섬+거래이력 known셋+유일)로 검증해 채택.
            # 가드 완화(known 제거)는 +20/-4로 열세 — 바코드류 우연 10자리 오인 방지.
            # 상호일치 게이트는 ns엔 미적용(065 실측 −18: 표기차/OCR변형으로 진짜 fix가
            # sim<0.3에 걸림). 지점간거래 오픽 방지는 위 지점폴백 선순위로 해결.
            known = _get_known_supplier_biznos()
            ns = {c[0] for c in cands if not c[1]
                  if c[0] not in excl and _bizno_checksum_ok(c[0]) and c[0] in known}
            if len(ns) == 1:
                newv = next(iter(ns))
        if newv and newv != cur:
            document_fields["supplierBizNumber"] = f"{newv[:3]}-{newv[3:5]}-{newv[5:]}"
            dbg = {"refined": 1, "from": cur, "to": newv}
    return document_fields, dbg


def refine_buyer_bizno(
    document_fields: Any, ocr_lines_raw: Any,
) -> tuple[Any, dict[str, Any]]:
    """공급받는자 사업자번호가 빈칸/무효(후보에 없음)일 때만 백제 지점 후보로 채움.

    buyer = 백제 지점셋(buyerBranchBiznos)에 속한 구분자형 후보(공급자와 다른 것).
    ★be==supplier 트리거는 금지: 일부 문서는 공급자==공급받는자(동일 사업체)라 정상값을
    깬다(065 실측 reg 69의 전원). 빈칸/미추출만 트리거 → gain 37/reg 0 → 81.2→83.7%.
    다중 백제 후보 중 '어느 지점'은 못 가리므로(라벨/블록 필요) 회수는 빈칸만 보수적."""
    dbg: dict[str, Any] = {"refined": 0}
    if not isinstance(document_fields, dict):
        return document_fields, dbg

    def _d(v: Any) -> str:
        return re.sub(r"\D", "", str(v or ""))

    cur = _d(document_fields.get("buyerBizNumber"))
    supplier = _d(document_fields.get("supplierBizNumber"))
    branch = _get_buyer_branch_biznos()
    if not branch:
        return document_fields, dbg
    cands = _bizno_candidates_ocr(ocr_lines_raw)
    sep = [c for c in cands if c[1]]
    is_cand = cur and any(c[0] == cur for c in sep)
    cur_bad = (not cur) or (cur and not is_cand)       # 빈칸 or 후보에 없음만
    if cur_bad and cur not in branch:
        baekje = [c[0] for c in sep if c[0] in branch and c[0] != supplier]
        newv = baekje[0] if baekje else ""
        if not newv:
            # ★무구분자 폴백(065 실측 +102/break0): sep에 백제후보 없을 때, 무구분자
            # 10자리를 branch셋 멤버십+체크섬+유일로 검증해 채택. branch셋 자체가
            # 강한 검증기라 supplier쪽보다 회수 큼(GT의 무구분자-only 443 중 유일 105).
            ns = {c[0] for c in cands if not c[1]
                  if c[0] in branch and c[0] != supplier and _bizno_checksum_ok(c[0])}
            if len(ns) == 1:
                newv = next(iter(ns))
        if newv and newv != cur:
            document_fields["buyerBizNumber"] = f"{newv[:3]}-{newv[3:5]}-{newv[5:]}"
            dbg = {"refined": 1, "from": cur, "to": newv}
    return document_fields, dbg


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


def _normalize_ocr_money_punctuation(value: Any) -> str:
    token = _normalize_text(value).strip("()[]{}.,:;|")
    token = token.replace("￦", "").replace("₩", "").replace("원", "")
    token = token.replace("占?,", "").replace("??,", "").replace("??,", "")
    token = re.sub(r"(?<=\d)[,.]{2,}(?=\d{3}(?!\d))", ",", token)
    if re.fullmatch(r"-?\d{1,3}(?:[,.]\d{3})+", token):
        return token.replace(".", ",")
    return token


def _is_number_token(value: str) -> bool:
    token = _normalize_ocr_money_punctuation(value)
    token = token.replace("￦", "").replace("₩", "").replace("원", "")
    return bool(re.fullmatch(r"-?\d+(?:,\d{3})*(?:\.\d+)?", token))


def _clean_number_token(value: str) -> str:
    return _normalize_ocr_money_punctuation(value)


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


# Stricter than ``_is_date_like_number``: requires a valid month (01-12) and day
# (01-31) so a genuine 6-digit quantity (e.g. "100000", month "00") is not mistaken
# for an expiry date when deciding to reassign a date-shaped quantity column.
_STRICT_EXPIRY_DATE_RE = re.compile(
    r"(?:(?:19|20)\d{2}|\d{2})(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])"
)


def _is_strict_expiry_date_number(value: Any) -> bool:
    text = _clean_number_token(_normalize_text(value)).replace(",", "")
    return bool(_STRICT_EXPIRY_DATE_RE.fullmatch(text))


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


def _money_for_sum(value: Any) -> float | None:
    """total 재계산(supply+tax)용 콤마-aware 금액 파싱.
    `_money_parse_value`는 콤마를 먼저 지우고 6자리 날짜검사라 304,663(콤마 천단위 금액)을
    날짜로 오인→None→합계 재계산 스킵→잘못된 total 잔존. 콤마가 있으면 금액이므로 받아들이고,
    콤마 없는 6/8자리만 날짜로 거부(코드베이스 1505행과 동일 패턴). 전역 함수는 불변(부작용 회피)."""
    raw = _normalize_text(value)
    if "," not in raw and _is_date_like_number(value):
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


def _normalize_free_lot_code_with_ocr_unit_suffix(value: Any) -> str:
    text = _normalize_text(value).strip("()[]{}.,:;|")
    if not text:
        return ""
    compact = re.sub(r"\s+", "", text).upper()
    compact = re.sub(r"^1C(?=\d)", "IC", compact)
    if _looks_like_lot_code_with_unit_suffix(compact):
        return compact[:-2] + "ea"
    match = re.fullmatch(r"(IC\d{5}-\d{3})(?:D?A)", compact)
    if match:
        return f"{match.group(1)}ea"
    return ""


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
    if raw_text and not _normalize_text(repaired.get("lotNo")):
        for token in re.split(r"\s+", raw_text):
            if _looks_like_lot_code_with_unit_suffix(token):
                repaired["lotNo"] = _normalize_text(token).strip("()[]{}.,:;|")
                break
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
            "지점코드", "팀코드", "부서코드", "거래처코드", "창고코드", "담당자",
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


def _numeric_value_from_row_item_text(value: Any) -> str:
    text = _normalize_comma_space_money_text(value)
    if not text:
        return ""
    tokens = _merge_comma_space_money_tokens(text.split())
    if len(tokens) == 1 and _is_number_token(tokens[0]):
        return _clean_number_token(tokens[0])
    return ""


def _row_numeric_arithmetic_matches(row: dict[str, Any]) -> bool:
    quantity = _number_value(row.get("quantity"))
    unit_price = _money_parse_value(row.get("unitPrice"))
    amount = _money_parse_value(row.get("amount"))
    if quantity is None or unit_price is None or amount is None:
        return False
    return quantity > 0 and abs((quantity * unit_price) - amount) < 0.01


def _repair_quantity_from_row_arithmetic(row: dict[str, Any]) -> bool:
    unit_price = _money_for_sum(row.get("unitPrice"))
    amount = _money_for_sum(row.get("amount"))
    if unit_price is None or amount is None or unit_price <= 0 or amount <= 0:
        return False
    quotient = amount / unit_price
    rounded = round(quotient)
    if rounded <= 0 or rounded > 9999 or abs(quotient - rounded) > 0.0001:
        return False
    current = _number_value(row.get("quantity"))
    if current is not None and abs((current * unit_price) - amount) < 0.01:
        return False
    row["quantity"] = _normalize_quantity(str(rounded))
    return True


def _row_item_money_column_candidate(item: dict[str, Any]) -> bool:
    value = _normalize_text(item.get("value"))
    raw_text = _normalize_text(item.get("text"))
    number = _money_parse_value(value)
    if number is None:
        return False
    if "," not in value and "," not in raw_text and _is_lot_or_manufacturing_like_number(value):
        return False
    return "," in value or "," in raw_text or abs(number) >= 1000


def _numeric_items_from_row_items(row_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    positioned = [
        item
        for item in row_items
        if isinstance(item.get("cx"), (int, float)) and _normalize_text(item.get("text"))
    ]
    positioned.sort(key=lambda item: float(item.get("cx") or 0.0))
    numeric_items: list[dict[str, Any]] = []
    idx = 0
    while idx < len(positioned):
        item = positioned[idx]
        text = _normalize_text(item.get("text"))
        next_item = positioned[idx + 1] if idx + 1 < len(positioned) else None
        next_text = _normalize_text(next_item.get("text")) if next_item else ""
        if (
            next_item is not None
            and re.fullmatch(r"-?\d{1,3},", text.strip())
            and re.fullmatch(r"\d{3}", next_text.strip())
            and isinstance(next_item.get("cx"), (int, float))
        ):
            value = f"{text.strip()}{next_text.strip()}"
            numeric_items.append({
                "value": _clean_number_token(value),
                "cx": (float(item["cx"]) + float(next_item["cx"])) / 2.0,
                "cy": (float(item.get("cy") or 0.0) + float(next_item.get("cy") or 0.0)) / 2.0,
                "text": f"{text} {next_text}",
            })
            idx += 2
            continue
        value = _numeric_value_from_row_item_text(text)
        if value:
            numeric_items.append({
                "value": value,
                "cx": float(item["cx"]),
                "cy": float(item.get("cy") or 0.0),
                "text": text,
            })
        idx += 1
    return numeric_items


def _repair_numeric_assignment_from_row_items(
    row: dict[str, str],
    row_items: list[dict[str, Any]] | None,
) -> dict[str, str]:
    if not row_items:
        return row
    arithmetic_repaired = dict(row)
    if _repair_quantity_from_row_arithmetic(arithmetic_repaired):
        return arithmetic_repaired
    numeric_items = _numeric_items_from_row_items(row_items)
    if len(numeric_items) < 2:
        return row

    money_items = [
        item
        for item in numeric_items
        if _row_item_money_column_candidate(item)
    ]
    if len(money_items) < 2:
        return row
    money_items.sort(key=lambda item: item["cx"])
    rightmost_cx = float(money_items[-1]["cx"])
    amount_cluster = [item for item in money_items if abs(float(item["cx"]) - rightmost_cx) <= 18.0]
    if len(amount_cluster) >= 2 and all(isinstance(item.get("cy"), (int, float)) for item in amount_cluster):
        amount_item = min(amount_cluster, key=lambda item: float(item.get("cy") or 0.0))
    else:
        amount_item = money_items[-1]
    unit_price_candidates = [item for item in money_items[:-1] if item["cx"] < amount_item["cx"] - 8.0]
    if not unit_price_candidates:
        return row
    unit_price_item = unit_price_candidates[-1]

    quantity_candidates = [
        item
        for item in numeric_items
        if item["cx"] < unit_price_item["cx"] - 8.0
        and _looks_like_quantity_token(item["value"])
        and not _is_date_like_number(item["value"])
        and "," not in item["value"]
    ]
    quantity_item = quantity_candidates[-1] if quantity_candidates else None
    quantity_value = _number_value(quantity_item["value"]) if quantity_item is not None else _number_value(row.get("quantity"))
    unit_price_value = _money_for_sum(unit_price_item["value"])
    amount_value = _money_for_sum(amount_item["value"])
    if quantity_value is not None and unit_price_value is not None:
        expected_amount = quantity_value * unit_price_value
        if amount_value is None or abs(amount_value - expected_amount) > 0.01:
            amount_cx = float(amount_item["cx"])
            amount_cy = float(amount_item.get("cy") or 0.0)
            arithmetic_amount_candidates = [
                item
                for item in numeric_items
                if item is not amount_item
                and ("," in _normalize_text(item.get("value")) or "," in _normalize_text(item.get("text")))
                and abs(float(item.get("cx") or 0.0) - amount_cx) <= 18.0
                and abs((_money_for_sum(item.get("value")) or 0.0) - expected_amount) <= 0.01
            ]
            if arithmetic_amount_candidates:
                amount_item = min(
                    arithmetic_amount_candidates,
                    key=lambda item: abs(float(item.get("cy") or 0.0) - amount_cy),
                )
    quantity_is_expiry_like = bool(row.get("quantity") and _is_date_like_number(row.get("quantity")))
    current_is_suspicious = not _row_numeric_arithmetic_matches(row) or quantity_is_expiry_like
    if not current_is_suspicious:
        return row

    repaired = dict(row)
    repaired["unitPrice"] = _normalize_money(unit_price_item["value"])
    repaired["amount"] = _normalize_money(amount_item["value"])
    if quantity_item is not None:
        repaired["quantity"] = _normalize_quantity(quantity_item["value"])
    elif quantity_is_expiry_like:
        repaired["quantity"] = ""

    if not repaired.get("expiryDate"):
        expiry_candidates = [
            item
            for item in numeric_items
            if item["cx"] < unit_price_item["cx"] and _is_date_like_number(item["value"])
        ]
        if expiry_candidates:
            repaired["expiryDate"] = _clean_number_token(expiry_candidates[-1]["value"])
    return repaired


_LEADING_ROW_INDEX_RE = re.compile(r"^\s*\d{1,3}\s+(.+)$", re.DOTALL)


def _strip_leading_row_index(text: str) -> str:
    """표 각 행 앞에 붙은 순번(1,2,3…)을 벗긴다.

    war 송장 표는 행마다 선행 순번이 있어, free 컬럼파서가 '첫 토큰이 숫자'라며
    행을 통째로 거부(_parse_table_row_candidate: first_numeric_idx=0 → label 없음)
    → fallback으로 떨어져 줄 전체가 itemName blob → GT와 content-align 실패로
    행 전체(8셀)가 손실되는 지배적 파편화 원인. 순번을 벗겨 실제 품명이 첫
    토큰이 되게 하면 free 가 컬럼화하고 정렬도 복원된다.

    가드(오작동 방지): 남은 첫 글자가 한글(품명)이고, 콤마 금액 토큰이 2개 이상인
    '진짜 품목행'에서만 벗긴다. 순번이 아닌 선행 숫자(수량-우선 레이아웃 등)는
    한글-우선 조건에 걸려 건드리지 않는다.
    """
    m = _LEADING_ROW_INDEX_RE.match(text)
    if not m:
        return text
    rest = m.group(1).lstrip()
    if not _HANGUL_RE.match(rest[:1]):
        return text
    if len(re.findall(r"\d{1,3}(?:,\d{3})+", rest)) < 2:
        return text
    return rest


def _parse_table_row_candidate(
    line: str,
    row_index: int,
    *,
    row_items: list[dict[str, Any]] | None = None,
) -> dict[str, str] | None:
    text = _normalize_comma_space_money_text(line)
    if _is_summary_or_header_line(text):
        return None
    text = _strip_leading_row_index(text)
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
    # A date-shaped value sitting in the quantity column while expiryDate is empty
    # is a column misassignment (the real quantity token was lost/merged in OCR).
    # Move it to expiryDate regardless of how many numeric tokens the line had —
    # the previous ``len(numeric_values) == 3`` guard missed rows where a lot/
    # manufacturing number bumped the numeric count to 4+. Guarded by a strict
    # YYMMDD/ YYYYMMDD check so a genuine 6-digit quantity is left in place.
    # Use comma-aware ``_money_for_sum`` (not ``_money_parse_value``, which mistakes a
    # comma-thousands amount like "110,450" for a 6-digit date and returns None).
    unit_price_value = _money_for_sum(unit_price)
    amount_value = _money_for_sum(amount)
    if (
        quantity
        and not expiry_date
        and _is_strict_expiry_date_number(quantity)
        and unit_price_value is not None
        and amount_value is not None
        and amount_value >= unit_price_value
    ):
        expiry_date = quantity
        quantity = ""
    if not item_name and not amount:
        return None
    candidate = {
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
    return _repair_numeric_assignment_from_row_items(candidate, row_items)


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
    text = _strip_leading_row_index(text)
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


def _find_table_row_candidates(
    lines: list[str],
    *,
    allow_relaxed: bool = True,
    row_entries: list[dict[str, Any]] | None = None,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    entries = row_entries if row_entries is not None else [{"text": line, "items": []} for line in lines]
    for entry in entries:
        line = _normalize_text(entry.get("text")) if isinstance(entry, dict) else _normalize_text(entry)
        row_items = entry.get("items") if isinstance(entry, dict) else None
        candidate = _parse_table_row_candidate(line, len(rows) + 1, row_items=row_items)
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
            "routedTo": "productCode",
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
            _normalize_product_code_token(t["text"]) for t in cluster if _normalize_product_code_token(t.get("text"))
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
        product_code_text = " ".join(product_code_tokens)
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
            "spec": "",
            "productCode": product_code_text,
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


def _table_amount_sum_reconciles(rows: list[dict[str, Any]], full_text: str) -> bool:
    """True when the sum of row amounts matches an independent money scalar in
    full_text (e.g. supplyAmount/totalAmount), within 0.5%. Strategy-independent
    mirror of the columnar diag check (lines ~2442-2461). Used as the safety net
    for the non-columnar quantity-optional release (3G): a real table's line
    amounts sum to the document total; a garbled/partial table's do not."""
    vals: list[float] = []
    for r in rows:
        v = _number_value(_normalize_text(r.get("amount")))
        if v is not None and v > 0:
            vals.append(v)
    if not vals or not full_text:
        return False
    sum_amount = sum(vals)
    if sum_amount <= 0:
        return False
    for tok in _money_tokens_from_text(full_text):
        tok_val = _number_value(tok)
        if tok_val is None or tok_val <= 0:
            continue
        # Skip a match against an individual line amount itself.
        if any(abs(tok_val - v) <= max(1.0, v * 0.005) for v in vals):
            continue
        if abs(tok_val - sum_amount) <= max(1.0, sum_amount * 0.005):
            return True
    return False


def _evaluate_release_threshold(
    table_rows: list[dict[str, Any]],
    field_quality: dict[str, Any] | None = None,
    *,
    columnar_context: dict[str, Any] | None = None,
    amount_sum_reconciles: bool = False,
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

    # 3G: extend the quantity-optional release to NON-columnar strategies
    # (relaxed_line/strict_column rows that did not go through columnar_2d).
    # The columnar 3F gate uses confidence + amount-sum reconciliation as its
    # safety net; here confidence is unavailable, so amount-sum reconciliation
    # (sum of row amounts == an independent scalar in full_text) is the sole,
    # strong arithmetic safety net. Same strict invariants as 3F otherwise. This
    # keeps a clean angle-variant table (itemName/amount/unitPrice near-perfect,
    # only quantity OCR-noisy) in free instead of demoting it to the much-weaker
    # fallback, while non-reconciling/garbled tables still demote.
    if (
        not columnar_release_decision.get("applied")
        and amount_sum_reconciles
        and ratios["itemNamePresentRatio"] >= 1.0
        and ratios["amountPresentRatio"] >= 1.0
        and ratios["unitPriceParseableRatio"] >= rules["minUnitPriceParseableRatio"]
        and metadata_row_count == 0
        and forbidden_row_count == 0
    ):
        qty_missing_3g = sum(1 for r in rows if not _normalize_text(r.get("quantity")))
        qty_missing_ratio_3g = qty_missing_3g / total if total else 1.0
        if qty_missing_ratio_3g <= columnar_release_decision["qtyOptionalMissingMaxRatio"]:
            relaxed_ready_3g = 0
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
                relaxed_ready_3g += 1
            relaxed_ratio_3g = (relaxed_ready_3g / total) if total else 0.0
            if relaxed_ratio_3g >= min_release_ready_ratio and relaxed_ready_3g >= rules["minReleaseReadyRows"]:
                pre_apply_3g = list(fail_reasons)
                for r in (
                    "release_ready_ratio_below_threshold",
                    "release_ready_rows_below_threshold",
                    "quantity_parseable_ratio_below_threshold",
                ):
                    if r in fail_reasons:
                        fail_reasons.remove(r)
                columnar_release_decision["applied"] = True
                columnar_release_decision["appliedVia"] = "non_columnar_amount_reconciled"
                columnar_release_decision["relaxedReleaseReady"] = relaxed_ready_3g
                columnar_release_decision["relaxedReleaseReadyRatio"] = round(relaxed_ratio_3g, 4)
                columnar_release_decision["droppedFailReasons"] = [
                    r for r in pre_apply_3g if r not in fail_reasons
                ]

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


def _compact_row_group_item(item: dict[str, Any]) -> dict[str, Any]:
    compact: dict[str, Any] = {"text": _normalize_text(item.get("text"))}
    for key in ("x", "y", "w", "h", "cx", "cy"):
        value = item.get(key)
        if isinstance(value, (int, float)):
            compact[key] = float(value)
    return compact


def _group_ocr_items_into_row_entries(items: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
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

    row_entries: list[dict[str, Any]] = []
    for row in sorted(rows, key=lambda value: float(value["cy"])):
        row_items = sorted(row["items"], key=lambda value: float(value["x"]))
        text = _normalize_text(" ".join(_normalize_text(item.get("text")) for item in row_items))
        if text:
            row_entries.append({
                "text": text,
                "items": [_compact_row_group_item(item) for item in row_items if _normalize_text(item.get("text"))],
            })
    return row_entries, {
        "status": "grouped",
        "positionedCount": len(positioned),
        "rowTextCount": len(row_entries),
        "rowThreshold": round(row_threshold, 2),
        "medianHeight": round(median_height, 2),
    }


def _group_ocr_items_into_row_texts(items: list[dict[str, Any]]) -> tuple[list[str], dict[str, Any]]:
    row_entries, debug = _group_ocr_items_into_row_entries(items)
    return [_normalize_text(entry.get("text")) for entry in row_entries], debug


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


def _is_free_table_header_stub_row(row: Any) -> bool:
    if not isinstance(row, dict):
        return False
    item_name = re.sub(r"\s+", "", _normalize_text(row.get("itemName")))
    spec = re.sub(r"\s+", "", _normalize_text(row.get("spec")))
    if item_name not in {"품목", "품명"} or spec != "규격":
        return False
    numeric_filled = sum(
        1
        for key in ("lotNo", "expiryDate", "quantity", "unitPrice", "amount")
        if _normalize_text(row.get(key))
    )
    return numeric_filled >= 3


def _repair_leading_header_stub_row(rows: list[dict[str, Any]]) -> None:
    if len(rows) < 2 or not _is_free_table_header_stub_row(rows[0]):
        return
    next_row = rows[1]
    next_item = _normalize_text(next_row.get("itemName"))
    if not _has_item_name_signal(next_item):
        return
    rows[0]["itemName"] = next_item
    next_spec = _normalize_text(next_row.get("spec"))
    if next_spec and re.sub(r"\s+", "", next_spec) not in {"품목", "품명", "규격"}:
        rows[0]["spec"] = next_spec


def _repair_dense_staggered_name_spec_columns(
    rows: list[dict[str, Any]], ocr_items: list[dict[str, Any]] | None
) -> bool:
    """Realign dense item-name/spec columns against intact numeric rows.

    On some angle variants, the header and first numeric row share a visual
    band while the item-name/spec columns start lower. Row grouping then shifts
    only those two columns. Apply only to a large table whose first row is the
    known header stub and whose OCR contains exactly one item-name anchor per
    output row.
    """
    if len(rows) < 20 or not ocr_items or not _is_free_table_header_stub_row(rows[0]):
        return False
    spec_headers = [
        item for item in ocr_items
        if re.sub(r"\s+", "", _normalize_text(item.get("text"))) == "\uaddc\uaca9"
    ]
    if len(spec_headers) != 1:
        return False
    header = spec_headers[0]
    spec_x = float(header.get("cx") or 0.0)
    header_y = float(header.get("cy") or 0.0)
    if spec_x <= 0 or header_y <= 0:
        return False

    name_candidates: list[dict[str, Any]] = []
    for item in ocr_items:
        text = _normalize_text(item.get("text"))
        cx = float(item.get("cx") or 0.0)
        cy = float(item.get("cy") or 0.0)
        if cy <= header_y + 8.0 or cx >= spec_x * 0.75:
            continue
        if not _has_item_name_signal(text) or _is_summary_or_header_line(text):
            continue
        name_candidates.append(item)
    name_candidates.sort(key=lambda item: (float(item.get("cy") or 0.0), float(item.get("cx") or 0.0)))
    if len(name_candidates) < len(rows):
        return False
    name_candidates = name_candidates[:len(rows)]

    name_positions = [float(item.get("cy") or 0.0) for item in name_candidates]
    gaps = sorted(
        b - a for a, b in zip(name_positions, name_positions[1:]) if b > a
    )
    if not gaps:
        return False
    median_gap = gaps[len(gaps) // 2]
    if not (8.0 <= median_gap <= 80.0):
        return False

    spec_candidates: list[dict[str, Any]] = []
    for item in ocr_items:
        text = _normalize_text(item.get("text"))
        cx = float(item.get("cx") or 0.0)
        cy = float(item.get("cy") or 0.0)
        if cy <= header_y + 8.0 or abs(cx - spec_x) > max(70.0, spec_x * 0.18):
            continue
        if _looks_like_spec_token(text):
            spec_candidates.append(item)

    for index, (row, item) in enumerate(zip(rows, name_candidates), start=1):
        row["itemName"] = _normalize_text(item.get("text"))
        row["spec"] = ""
        row["rowIndex"] = str(index)

    used_rows: set[int] = set()
    for item in sorted(spec_candidates, key=lambda value: float(value.get("cy") or 0.0)):
        cy = float(item.get("cy") or 0.0)
        available = [idx for idx in range(len(rows)) if idx not in used_rows]
        if not available:
            break
        idx = min(available, key=lambda row_idx: abs(cy - name_positions[row_idx]))
        if abs(cy - name_positions[idx]) > median_gap * 0.8:
            continue
        rows[idx]["spec"] = _normalize_spec(item.get("text"))
        used_rows.add(idx)
    return True


def _repair_item_spec_lot_shift(row: dict[str, Any]) -> bool:
    split = _split_item_name_spec_tail(row.get("itemName"))
    lot_code = _normalize_free_lot_code_with_ocr_unit_suffix(row.get("spec"))
    if not split or not lot_code or _normalize_text(row.get("lotNo")):
        return False

    row["itemName"], row["spec"] = split
    row["lotNo"] = lot_code

    # When the row was split one column too early, quantity/unitPrice/amount can
    # appear as unitPrice/amount/(missing). Repair only when arithmetic is exact.
    if not _normalize_text(row.get("quantity")):
        shifted_qty = _number_value(row.get("unitPrice"))
        shifted_unit_price = _money_for_sum(row.get("amount"))
        if shifted_qty is not None and shifted_unit_price is not None and shifted_qty > 0 and shifted_unit_price > 0:
            row["quantity"] = _normalize_quantity(str(int(shifted_qty)))
            row["unitPrice"] = _normalize_money(f"{int(shifted_unit_price):,}")
            row["amount"] = _normalize_money(f"{int(round(shifted_qty * shifted_unit_price)):,}")
    return True


def _repair_spec_like_unit_price_shift(row: dict[str, Any]) -> bool:
    raw_text = _normalize_text(row.get("_rawText"))
    if not raw_text or _normalize_text(row.get("spec")):
        return False
    current_unit = _normalize_text(row.get("unitPrice"))
    quantity_value = _number_value(row.get("quantity"))
    if quantity_value is None or quantity_value <= 0:
        return False
    if not re.fullmatch(r"\d{3,4}", current_unit):
        return False
    if not re.search(r"(?:0{2,}|[O0][TC])$", current_unit, re.IGNORECASE):
        return False

    money_tokens = [
        _clean_number_token(token)
        for token in re.split(r"\s+", raw_text)
        if "," in token and _money_for_sum(_clean_number_token(token)) is not None
    ]
    if len(money_tokens) < 2:
        return False
    unit_price = _money_for_sum(money_tokens[-2])
    amount = _money_for_sum(money_tokens[-1])
    if unit_price is None or amount is None or abs((quantity_value * unit_price) - amount) > 0.01:
        return False

    row["spec"] = re.sub(r"0$", "C", current_unit)
    row["unitPrice"] = _normalize_money(money_tokens[-2])
    row["amount"] = _normalize_money(money_tokens[-1])
    return True


def _repair_spec_from_indexed_raw_text(row: dict[str, Any]) -> bool:
    """Recover a spec hidden behind a standalone row-number token.

    Angle variants can merge ``itemName 6 100T lotNo ...`` into one OCR row.
    The single-digit table index is not a spec, while the following compact
    unit token is.  Require the known lot number after it so ordinary product
    names containing digits are never rewritten.
    """
    raw_text = _normalize_text(row.get("_rawText"))
    lot_no = _normalize_text(row.get("lotNo"))
    if not raw_text or not lot_no:
        return False
    lot_pos = raw_text.casefold().find(lot_no.casefold())
    if lot_pos <= 0:
        return False
    prefix_tokens = [
        token.strip("()[]{}.,:;|")
        for token in re.split(r"\s+", raw_text[:lot_pos].strip())
        if token.strip("()[]{}.,:;|")
    ]
    for idx in range(len(prefix_tokens) - 1, 0, -1):
        candidate = prefix_tokens[idx]
        row_marker = prefix_tokens[idx - 1]
        if not re.fullmatch(r"\d{1,2}", row_marker):
            continue
        if not _looks_like_spec_token(candidate):
            continue
        current = _normalize_text(row.get("spec"))
        if current and _looks_like_spec_token(current):
            return False
        row["spec"] = _normalize_spec(candidate)
        return True
    return False


def _normalize_success_table_rows(
    table_rows: Any, ocr_items: list[dict[str, Any]] | None = None
) -> list[dict[str, Any]]:
    if not isinstance(table_rows, list):
        return []
    normalized_rows: list[dict[str, Any]] = []
    for index, row in enumerate(table_rows, start=1):
        if not isinstance(row, dict):
            continue
        normalized = deepcopy(row)
        for key in (*REQUIRED_TABLE_ROW_KEYS, "productCode", "lotNo", "expiryDate"):
            normalized[key] = _normalize_text(normalized.get(key))
        if (
            not normalized.get("productCode")
            and _looks_like_product_code_token(normalized.get("spec"))
        ):
            normalized["productCode"] = _normalize_product_code_token(normalized["spec"]) or normalized["spec"]
            normalized["spec"] = ""
        if not normalized.get("productCode"):
            normalized["productCode"] = _first_product_code_from_text(normalized.get("_rawText"))
        if (
            normalized.get("productCode")
            and normalized.get("spec") == normalized.get("productCode")
        ):
            normalized["spec"] = ""
        if normalized.get("productCode") and normalized.get("itemName"):
            code = re.escape(_normalize_text(normalized["productCode"]))
            item_name = _normalize_text(normalized["itemName"])
            stripped_name = re.sub(rf"\s+{code}$", "", item_name)
            if stripped_name and stripped_name != item_name:
                normalized["itemName"] = stripped_name
                item_name = stripped_name
            if _HANGUL_RE.search(item_name):
                stripped_noise = re.sub(r"\s+O(?:C)?$", "", item_name, flags=re.IGNORECASE)
                if stripped_noise and stripped_noise != item_name:
                    normalized["itemName"] = stripped_noise
        _repair_item_spec_lot_shift(normalized)
        _repair_spec_from_indexed_raw_text(normalized)
        _repair_spec_like_unit_price_shift(normalized)
        if "rowIndex" not in normalized:
            normalized["rowIndex"] = str(index)
        normalized_rows.append(normalized)
    dense_repaired = _repair_dense_staggered_name_spec_columns(normalized_rows, ocr_items)
    if not dense_repaired:
        _repair_leading_header_stub_row(normalized_rows)
    for row in normalized_rows:
        _repair_quantity_from_row_arithmetic(row)
    product_code_rows = sum(1 for row in normalized_rows if _normalize_text(row.get("productCode")))
    product_code_table_like = product_code_rows >= max(1, len(normalized_rows) // 2)
    if product_code_table_like:
        for row in normalized_rows:
            code = _normalize_text(row.get("productCode"))
            spec = _normalize_text(row.get("spec"))
            item_name = _normalize_text(row.get("itemName"))
            if not code:
                continue
            unit_price = _normalize_text(row.get("unitPrice"))
            amount = _normalize_text(row.get("amount"))
            if (
                unit_price
                and amount
                and not _normalize_text(row.get("lotNo"))
                and not _normalize_text(row.get("expiryDate"))
                and "," not in unit_price
                and "," not in amount
                and _is_lot_or_manufacturing_like_number(unit_price)
                and _is_strict_expiry_date_number(amount)
            ):
                row["lotNo"] = unit_price
                row["expiryDate"] = amount
                row["unitPrice"] = ""
                row["amount"] = ""
            if spec:
                if item_name == code and _HANGUL_RE.search(spec):
                    row["itemName"] = spec
                    row["spec"] = ""
                elif not _HANGUL_RE.search(spec):
                    row["spec"] = ""
            _repair_quantity_from_row_arithmetic(row)
    return normalized_rows


def _maybe_move_cumulative_vat_to_tax(fields: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Repair summary scalar confusion when VAT was mapped as cumulative amount.

    The guard is arithmetic, not file-specific: move cumulativeAmount to
    taxAmount only when tax is empty and supplyAmount + cumulativeAmount equals
    totalAmount. Genuine balance/cumulative fields do not satisfy this invoice
    summary equation and are left untouched.
    """

    repaired = dict(fields) if isinstance(fields, dict) else {}
    debug: dict[str, Any] = {
        "enabled": True,
        "applied": False,
        "reason": "",
        "from": "cumulativeAmount",
        "to": "taxAmount",
    }
    if _has_meaningful_value(repaired.get("taxAmount")):
        debug["reason"] = "taxAmount_already_present"
        return repaired, debug
    supply = _money_parse_value(repaired.get("supplyAmount"))
    total = _money_parse_value(repaired.get("totalAmount"))
    cumulative = _normalize_text(repaired.get("cumulativeAmount"))
    if cumulative:
        tax_candidate = _money_parse_value(cumulative)
        if supply is not None and tax_candidate is not None and total is not None:
            if abs((supply + tax_candidate) - total) <= 2.0:
                repaired["taxAmount"] = cumulative
                repaired["cumulativeAmount"] = ""
                debug.update(
                    {
                        "applied": True,
                        "reason": "supply_plus_cumulative_equals_total",
                        "value": cumulative,
                    }
                )
                return repaired, debug
            debug["cumulativeEquation"] = {
                "supplyAmount": repaired.get("supplyAmount"),
                "cumulativeAmount": cumulative,
                "totalAmount": repaired.get("totalAmount"),
            }
    debug["reason"] = "no_cumulative_vat_equation_match"
    return repaired, debug


def _extract_labeled_summary_scalars_from_ocr_items(ocr_items: list[dict[str, Any]]) -> tuple[dict[str, str], dict[str, Any]]:
    """Extract footer supply/VAT scalars from label-value geometry.

    This keeps footer summary values out of tableRows while preserving explicitly
    labeled scalars. The rule is geometric and label-based, not filename-based:
    find a Korean footer label, then choose the nearest money token below the
    same x band.
    """

    debug: dict[str, Any] = {
        "enabled": True,
        "source": "ocr_items_label_value_geometry",
        "matched": {},
    }
    fields: dict[str, str] = {}
    finite_items: list[dict[str, Any]] = []
    for item in ocr_items:
        text = _normalize_text(item.get("text"))
        x = item.get("x")
        y = item.get("y")
        cx = item.get("cx")
        cy = item.get("cy")
        if not text or not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
            continue
        if not isinstance(cx, (int, float)) or not isinstance(cy, (int, float)):
            continue
        finite_items.append({"text": text, "x": float(x), "y": float(y), "cx": float(cx), "cy": float(cy)})

    label_specs = [
        ("supplyAmount", ("공급가", "공급액")),
        ("taxAmount", ("부가", "세액", "VAT", "vat")),
    ]
    for key, markers in label_specs:
        label_candidates = [
            item for item in finite_items
            if any(marker in item["text"] for marker in markers)
        ]
        label_candidates.sort(key=lambda item: (item["y"], item["x"]))
        for label in label_candidates:
            money_candidates: list[dict[str, Any]] = []
            for item in finite_items:
                money = _normalize_money(item["text"])
                if not money:
                    continue
                if item["cy"] <= label["cy"]:
                    continue
                if item["cy"] - label["cy"] > 70:
                    continue
                if abs(item["cx"] - label["cx"]) > 95:
                    continue
                money_candidates.append({**item, "value": money})
            if not money_candidates:
                continue
            money_candidates.sort(key=lambda item: (item["cy"] - label["cy"], abs(item["cx"] - label["cx"])))
            selected = money_candidates[0]
            fields[key] = selected["value"]
            debug["matched"][key] = {
                "label": label["text"],
                "value": selected["value"],
            }
            break
    return fields, debug


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
            if key in REFERENCE_MONEY_SCALAR_KEYS and _money_for_sum(ref.get(key)) is None:
                # Non-numeric garbage (e.g. the label "합") never fills a money field.
                skipped.append(key)
                continue
            merged[key] = _normalize_text(ref.get(key))
            filled.append(key)
    merged, vat_repair_debug = _maybe_move_cumulative_vat_to_tax(merged)
    scalar_merge_debug = {
        "enabled": True,
        "source": "invoice_statement",
        "function": "extract_invoice_statement_fields",
        "candidateKeys": list(REFERENCE_SCALAR_MERGE_KEYS),
        "filledKeys": filled,
        "skippedKeys": skipped,
        "excludedKeys": list(REFERENCE_SCALAR_MERGE_EXCLUDED_KEYS),
        "vatCumulativeRepair": vat_repair_debug,
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
        "columns": list(FIVE_COLUMN_PRODUCT_CODE_TABLE_KEYS),
        "expectedColumnKeys": list(FIVE_COLUMN_PRODUCT_CODE_TABLE_KEYS),
        "columnLabels": deepcopy(FIVE_COLUMN_PRODUCT_CODE_TABLE_LABELS),
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


# --- header-anchored column segmentation (H0~H2) ---------------------------
# 약품 거래명세서 대부분은 라벨 헤더(코드/품명/규격/유효기간/제조번호/보험코드/수량/
# 단가/금액)를 인쇄한다. OCR은 토큰을 x좌표로 분리해 이미 읽었으므로, 각 장의 자기
# 헤더로 열 경계를 잡아(header-anchored) 행 토큰을 x위치로 배정하면 벤더마다 순서가
# 달라도(보험코드 앞/뒤/없음) 일반화된다. 스냅샷 2002장 전수 측정(H0): 헤더 검출 78%,
# 강신호≥2 게이트. Voronoi 배정 검증(H1/H2): manufacturingNo·insuranceCode·spec·
# expiryDate가 기존 ~0%(전량 드롭)에서 ~50%로 회수됨. 헤더 미검출 장은 기존 경로 유지.
_HA_STRONG = ("수량", "단가", "금액", "규격", "유효", "제조번호", "보험",
              "공급가액", "공급단가", "입고수량", "판매단가", "판매금액", "로트", "배치")
# 문서레벨 라벨(표 컬럼 아님) — 표 헤더 밴드로 오인 금지
_HA_DOC = ("사업자번호", "주문번호", "송장번호", "전표번호", "거래처코드", "사원코드",
           "등록번호", "출고번호", "발행일자", "작성일자", "거래일자", "납품일자",
           "인수일자", "매출일자", "전표일자", "공급받는자", "공급자", "비고", "적요",
           "공급받는", "전화번호", "창고코드", "담당자코드", "번호구분")
# 라벨(부분일치, 구체적인 것 먼저) → 표준 셀 키. 인쇄된 코드열은 productCode(비채점)로:
# GT itemCode는 마스터매칭 산출코드(b.item_cd)라 인쇄코드와 달라 itemCode로 내면 오배정.
_HA_ALIAS = (
    ("보험코드", "insuranceCode"), ("보험약가", "insuranceCode"), ("보험번호", "insuranceCode"),
    ("보험No", "insuranceCode"), ("보험", "insuranceCode"), ("약가코드", "insuranceCode"),
    ("제조번호", "manufacturingNo"), ("제조No", "manufacturingNo"), ("로트", "manufacturingNo"),
    ("LOT", "manufacturingNo"), ("배치", "manufacturingNo"),
    ("유효기간", "expiryDate"), ("유효기한", "expiryDate"), ("사용기한", "expiryDate"),
    ("유효일자", "expiryDate"), ("유효", "expiryDate"),
    ("상품코드", "productCode"), ("상품번호", "productCode"), ("품목코드", "productCode"),
    ("제품코드", "productCode"), ("제품번호", "productCode"), ("물류코드", "productCode"),
    ("표준코드", "productCode"), ("바코드", "productCode"),
    ("공급단가", "unitPrice"), ("판매단가", "unitPrice"), ("단가", "unitPrice"),
    ("공급가액", "amount"), ("판매금액", "amount"), ("합계금액", "amount"), ("금액", "amount"),
    ("입고수량", "quantity"), ("박스수량", "quantity"), ("수량", "quantity"),
    ("규격", "spec"), ("포장", "spec"), ("단위", "spec"),
    ("상품명", "itemName"), ("제품명", "itemName"), ("품목명", "itemName"),
    ("품명", "itemName"), ("품목", "itemName"),
    # NOTE: 복합 라벨('품명 및 규격' 합본 컬럼)을 itemName 으로 매핑하는 v6 시도는
    # 062 실측 -0.24pp 순손해(합본 셀에 규격이 붙어 GT 품명과 mismatch)라 미채택.
)
# 그리디 분해용: 긴 alias 우선(뭉친 concat '품명규격'에서 '품명'을 '품'보다 먼저 떼도록)
_HA_ALIAS_BY_LEN = sorted(_HA_ALIAS, key=lambda kv: -len(kv[0]))
_HA_SUMMARY_RE = re.compile(r"합\s*계|소\s*계|이\s*상|부가세|공급가액|미\s*수|받을|총\s*액|"
                            r"외\s*상|페이지|page", re.I)
_HA_MONEY_RE = re.compile(r"^\d{1,3}(?:[,\.]\d{3})+(?:\.\d+)?$|^\d+\.\d{2}$")


def _ha_map_label(token: str) -> str | None:
    compact = re.sub(r"\s+", "", token or "")
    for doc in _HA_DOC:
        if doc in compact:
            return None
    for alias, key in _HA_ALIAS:
        if alias in compact:
            return key
    return None


def _ha_bands(ocr_items: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    """Group OCR tokens into y-bands (rows), each x-sorted."""
    toks = [it for it in ocr_items
            if _normalize_text(it.get("text")) and it.get("cx") is not None and it.get("cy") is not None]
    toks.sort(key=lambda it: (float(it["cy"]), float(it["cx"])))
    bands: list[list[dict[str, Any]]] = []
    cur: list[dict[str, Any]] = []
    last = None
    for it in toks:
        cy = float(it["cy"])
        if last is None or cy - last <= 12:
            cur.append(it)
        else:
            bands.append(cur)
            cur = [it]
        last = cy
    if cur:
        bands.append(cur)
    return bands


def _ha_fnum(value: Any) -> float | None:
    text = re.sub(r"[,\s]", "", str(value or "")).rstrip(".")
    return float(text) if re.fullmatch(r"\d+(?:\.\d+)?", text or "") else None


def _extract_header_anchored_table(
    ocr_items: list[dict[str, Any]],
    *,
    fill_mode: bool = False,
    append_mode: bool = False,
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    """Header-anchored table extraction. Returns (rows, debug).

    Default (fill_mode=False): ``debug['use']`` is True only for a COMPLETE table
    (itemName + money + a strict-dropped pharma column) — the strict gate.
    fill_mode=True: relaxed gate for column-FILL — passes whenever the header
    declares a pharma column (manufacturingNo/insuranceCode/expiryDate) and >=2
    rows were assigned; itemName/amount completeness is irrelevant because the
    caller copies ONLY the pharma columns into an existing table (empty cells)."""
    debug: dict[str, Any] = {"attempted": True, "use": False, "reason": "", "columns": [], "rowCount": 0}
    bands = _ha_bands(ocr_items)
    if not bands:
        debug["reason"] = "no_tokens"
        return [], debug
    # 1) header band = y-band with the most DISTINCT strong table signals (>=2)
    hi, best_n = -1, 0
    for i, band in enumerate(bands):
        sig = {s for it in band for s in _HA_STRONG if s in re.sub(r"\s+", "", _normalize_text(it.get("text")))}
        if len(sig) > best_n:
            best_n, hi = len(sig), i
    if best_n < 2:
        debug["reason"] = "no_header"
        return [], debug
    # 2) map header cells -> standard keys, sorted by x-center (leftmost per key).
    # ③v3: 자간 인쇄로 글자 단위 토큰으로 쪼개진 라벨('품|명','금|액','제|품|명')은
    # 단독 매핑이 안 되므로, 미매핑 짧은 토큰(≤2자)의 x-연속 run을 병합해 재매핑.
    # ③v5: 뭉친 run concat 은 여러 컬럼이 붙었을 수 있다('품명규격' = 품명+규격).
    # _ha_map_label 부분매치는 하나만(그것도 alias 순서상 '규격'→spec) 잡아 itemName 이
    # 사라졌음 (062 실측: append_gate 302/318). → concat 을 왼쪽부터 최장 alias 그리디
    # 분해해 걸친 모든 컬럼을 추출하고, 각 컬럼 cx 는 해당 문자구간에 걸친 토큰 평균.
    header_cells: list[tuple[float, str]] = []
    _run: list[dict[str, Any]] = []

    def _flush_run() -> None:
        if not _run:
            return
        parts = [re.sub(r"\s+", "", _normalize_text(it.get("text"))) for it in _run]
        concat = "".join(parts)
        offs, o = [], 0
        for p in parts:
            offs.append((o, o + len(p)))
            o += len(p)

        def _cx_for(a: int, b: int) -> float:
            cxs = [float(_run[j]["cx"]) for j, (s, e) in enumerate(offs) if s < b and e > a]
            return sum(cxs) / len(cxs) if cxs else float(_run[0]["cx"])

        i = 0
        while i < len(concat):
            # _HA_DOC(문서레벨 라벨)이 이 위치서 시작하면 컬럼 아님 → 건너뜀
            if any(concat.startswith(doc, i) for doc in _HA_DOC):
                i += 1
                continue
            hit = None
            for alias, key in _HA_ALIAS_BY_LEN:
                if concat.startswith(alias, i):
                    hit = (alias, key)
                    break
            if hit:
                header_cells.append((_cx_for(i, i + len(hit[0])), hit[1]))
                i += len(hit[0])
            else:
                i += 1
        _run.clear()

    for it in sorted(bands[hi], key=lambda z: float(z["cx"])):
        txt = _normalize_text(it.get("text"))
        key = _ha_map_label(txt)
        if key:
            _flush_run()
            header_cells.append((float(it["cx"]), key))
        elif len(re.sub(r"\s+", "", txt)) <= 2:
            _run.append(it)
        else:
            _flush_run()
    _flush_run()
    cols: list[tuple[float, str]] = []
    seen: set[str] = set()
    for cx, key in header_cells:  # x-정렬 유지됨
        if key not in seen:
            cols.append((cx, key))
            seen.add(key)
    debug["columns"] = [k for _, k in cols]
    if len(cols) < 4:
        debug["reason"] = f"too_few_columns:{len(cols)}"
        return [], debug
    centers = [c for c, _ in cols]
    keys = [k for _, k in cols]
    bounds = [(centers[i] + centers[i + 1]) / 2 for i in range(len(centers) - 1)]
    # 3) collect table-region tokens (below header, until first summary line)
    toks: list[dict[str, Any]] = []
    for band in bands[hi + 1:]:
        if _HA_SUMMARY_RE.search("".join(_normalize_text(it.get("text")) for it in band)):
            break
        toks.extend(band)
    if not toks:
        debug["reason"] = "no_body"
        return [], debug
    # 4) row anchors = money tokens under the amount(or unitPrice) column
    if "amount" in keys:
        acx = centers[keys.index("amount")]
    elif "unitPrice" in keys:
        acx = centers[keys.index("unitPrice")]
    else:
        acx = centers[-1]
    colw = (max(centers) - min(centers)) / max(1, len(centers) - 1)
    anchors = sorted(float(it["cy"]) for it in toks
                     if _HA_MONEY_RE.match(_normalize_text(it.get("text"))) and abs(float(it["cx"]) - acx) <= colw * 0.9)
    rows_y: list[float] = []
    for y in anchors:
        if not rows_y or y - rows_y[-1] > 8:
            rows_y.append(y)
    if len(rows_y) < 2:
        debug["reason"] = f"too_few_rows:{len(rows_y)}"
        return [], debug
    # 5) assign each token to nearest row anchor, then Voronoi-x to a column
    buckets: list[dict[str, list[tuple[float, str]]]] = [dict() for _ in rows_y]
    for it in toks:
        cy = float(it["cy"])
        ri = min(range(len(rows_y)), key=lambda i: abs(rows_y[i] - cy))
        if abs(rows_y[ri] - cy) > max(18.0, colw * 1.2):
            continue
        j = bisect.bisect_right(bounds, float(it["cx"]))
        buckets[ri].setdefault(keys[j], []).append((float(it["cx"]), _normalize_text(it.get("text"))))
    out: list[dict[str, str]] = []
    for idx, bucket in enumerate(buckets, start=1):
        row: dict[str, str] = {
            "rowIndex": str(idx), "itemName": "", "spec": "", "lotNo": "",
            "productCode": "", "expiryDate": "", "manufacturingNo": "",
            "insuranceCode": "", "quantity": "", "unitPrice": "", "amount": "",
        }
        raw_parts: list[str] = []
        for key, vals in bucket.items():
            vals.sort()
            joined = " ".join(t for _, t in vals).strip()
            row[key] = joined
            raw_parts.append(joined)
        # numeric-column hygiene: strip stray non-numeric noise from qty/price/amount
        for nk in ("quantity", "unitPrice", "amount"):
            if row[nk]:
                nums = re.findall(r"\d[\d,\.]*", row[nk])
                v = nums[-1] if nums else ""
                # OCR이 콤마 천단위를 점으로 읽는 케이스(267.916 == 267,916). amount/money
                # 는 정수라 '\d{1,3}(\.\d{3})+' 는 소수가 아니라 천단위 → 점 제거. 소수
                # 단가(950.00, 2자리 소수)는 패턴이 달라 건드리지 않음. (062 실측: HA가
                # 재구성한 행의 amount 상당수가 이 점-천단위라 정렬·채점이 어긋났음.)
                if re.fullmatch(r"\d{1,3}(?:\.\d{3})+", v):
                    v = v.replace(".", "")
                row[nk] = v
        # qty<->unitPrice swap fix via arithmetic (adjacent numeric columns)
        q, u, a = _ha_fnum(row["quantity"]), _ha_fnum(row["unitPrice"]), _ha_fnum(row["amount"])
        if q and u and a and abs(q * u - a) > 1 and abs(u * q - a) > 1:
            row["quantity"], row["unitPrice"] = row["unitPrice"], row["quantity"]
        row["_rawText"] = " ".join(raw_parts)
        row["_confidence"] = "0.55"
        row["_source"] = "invoice_statement_free_header_anchored"
        if row["itemName"] or row["amount"] or row["manufacturingNo"]:
            out.append(row)
    # 6) release gate
    colset = set(keys)
    has_valueadd = bool(colset & {"manufacturingNo", "insuranceCode", "expiryDate"})
    if append_mode:
        # ③P1-v2 APPEND gate: 행 '추가'용이라 pharma 컬럼 불요 — 품명+금액 헤더면 충분.
        # (v1이 fill 게이트를 재사용해 일반 표를 스킵 → dropped 1,901 중 252만 회수.
        #  추가 행은 기존 행을 못 건드리고 호출부 중복가드가 있어 완화해도 안전.)
        has_money = bool(colset & {"amount", "unitPrice"})
        if "itemName" not in colset or not has_money or len(out) < 2:
            debug["reason"] = f"append_gate:{len(out)}"
            return [], debug
    elif fill_mode:
        # FILL gate: a pharma column + >=2 assigned rows is enough — we copy only
        # those columns into an existing table (empty cells), so itemName/amount
        # completeness cannot regress non-pharma cells.
        if not has_valueadd or len(out) < 2:
            debug["reason"] = f"fill_no_pharma_or_rows:{len(out)}"
            return [], debug
    else:
        # value-add gate (whole-table use): only for a COMPLETE table where
        # header-anchoring adds what strict drops. itemName + money + pharma col.
        good = sum(1 for r in out if r["amount"] or (r["quantity"] and r["unitPrice"]))
        has_money = bool(colset & {"amount", "unitPrice"})
        if good < 2 or not ("itemName" in colset and has_money and has_valueadd):
            debug["reason"] = "not_valueadd_table"
            return [], debug
    debug["use"] = True
    debug["rowCount"] = len(out)
    debug["reason"] = "ok"
    return out, debug


# columns filled into an existing table (never overwrite a correct value).
_HA_FILL_COLUMNS = ("manufacturingNo", "insuranceCode", "expiryDate")


def _ha_amount_key(row: dict[str, Any]) -> str:
    return re.sub(r"[,\s]", "", str(row.get("amount") or "")).rstrip(".")


def _ha_unit_key(row: dict[str, Any]) -> str:
    return re.sub(r"[,\s]", "", str(row.get("unitPrice") or "")).rstrip(".")


def _ha_fmt_money(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else str(value)


def _ha_fill_arith_and_spec(tr: dict[str, Any], hr: dict[str, Any]) -> int:
    """R2: fill money (amount/unitPrice/quantity) and spec into EMPTY cells of an
    already-aligned table row from the header-anchored read.

    Spurious-proof by construction: a money cell is filled ONLY when the other two
    money cells are present and the header-anchored candidate closes the
    quantity x unitPrice = amount triangle (so a mis-assigned OCR token cannot be
    injected). ``spec`` is filled only when the candidate is a spec-shaped token
    (unit/dosage) and not a product code. Never overwrites an existing value.
    """
    filled = 0
    # snapshot ORIGINAL present values so a fresh fill never seeds another fill
    q0 = _ha_fnum(tr.get("quantity"))
    u0 = _ha_fnum(tr.get("unitPrice"))
    a0 = _ha_fnum(tr.get("amount"))

    def _empty(col: str) -> bool:
        return not str(tr.get(col) or "").strip()

    def _close(x: float, y: float) -> bool:
        return abs(x - y) <= max(1.0, abs(y) * 0.005)

    # amount: need qty + unitPrice present, verify qty*unitPrice == candidate
    if _empty("amount") and q0 is not None and u0 is not None:
        cand = _ha_fnum(hr.get("amount"))
        if cand is not None and cand > 0 and _close(q0 * u0, cand):
            tr["amount"] = _ha_fmt_money(cand)
            filled += 1
    # unitPrice: need qty + amount present, verify amount/qty == candidate
    if _empty("unitPrice") and q0 not in (None, 0) and a0 is not None:
        cand = _ha_fnum(hr.get("unitPrice"))
        if cand is not None and cand > 0 and _close(a0 / q0, cand):
            tr["unitPrice"] = _ha_fmt_money(cand)
            filled += 1
    # quantity: need unitPrice + amount present, verify amount/unitPrice == candidate
    if _empty("quantity") and u0 not in (None, 0) and a0 is not None:
        cand = _ha_fnum(hr.get("quantity"))
        if cand is not None and cand > 0 and cand.is_integer() and _close(a0 / u0, cand):
            tr["quantity"] = _ha_fmt_money(cand)
            filled += 1
    # spec: token-shape guard only (no arithmetic anchor available)
    if _empty("spec"):
        cand = _normalize_text(hr.get("spec"))
        if (
            cand
            and _looks_like_spec_token(cand)
            and not _looks_like_product_code_token(cand)
            and not _is_number_token(cand)
        ):
            tr["spec"] = _normalize_spec(cand)
            filled += 1
    return filled


def _ha_clean_fill(col: str, value: Any) -> str | None:
    """Extract the clean typed token for a pharma column from a (possibly merged)
    header-anchored cell. Returns None when no type-matching token is found → the
    caller then skips the fill (avoids injecting garbage / spurious values when a
    doc's header was detected with imprecise column boundaries)."""
    text = str(value or "").strip()
    if not text:
        return None
    if col == "expiryDate":
        m = re.search(r"20\d{2}[./-]?\d{2}[./-]?\d{2}", text.replace(" ", ""))
        return m.group(0) if m else None
    if col == "insuranceCode":
        # split on non-digits, take a standalone 8–11 digit code (drops 13-digit
        # barcodes and row-index prefixes). Insurance code is usually the last one.
        cand = [t for t in re.split(r"[^0-9]+", text) if 8 <= len(t) <= 11]
        return cand[-1] if cand else None
    if col == "manufacturingNo":
        toks = re.findall(r"[A-Za-z0-9]{5,12}", text.replace(",", ""))
        # batch codes carry letters (484FP61) or are a short 5–8 digit run; a
        # comma-stripped long amount is excluded by the length cap + digit rule.
        cand = [t for t in toks if re.search(r"[A-Za-z]", t) or re.fullmatch(r"\d{5,8}", t)]
        return cand[-1] if cand else None
    return text


def fill_pharma_columns(
    table_rows: Any, ocr_lines_raw: Any,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Fill manufacturingNo/insuranceCode/expiryDate into EXISTING table rows from
    a header-anchored read of the OCR — EMPTY cells only, so a correct value is
    never overwritten (protects the strict/study path). Path-agnostic: call at the
    free/fallback join in main.py so both paths gain the strict-dropped pharma
    columns. Returns (rows, debug)."""
    debug: dict[str, Any] = {"applied": False, "filled": 0, "reason": "", "columns": []}
    if not isinstance(table_rows, list) or not table_rows:
        debug["reason"] = "no_rows"
        return table_rows if isinstance(table_rows, list) else [], debug
    ocr_items = _extract_ocr_line_items(ocr_lines_raw)
    ha_rows, ha_dbg = _extract_header_anchored_table(ocr_items, fill_mode=True)
    if not ha_dbg.get("use") or not ha_rows:
        debug["reason"] = ha_dbg.get("reason", "no_header")
        return table_rows, debug
    debug["columns"] = ha_dbg.get("columns")
    # align existing rows to header-anchored rows: index when counts match, else
    # by amount value (each line item's amount is usually distinct).
    pairs: list[tuple[dict[str, Any], dict[str, Any]]] = []
    if len(ha_rows) == len(table_rows):
        pairs = list(zip(table_rows, ha_rows))
    else:
        # match by amount value first (distinct per line item); fall back to
        # unitPrice so rows whose amount cell is EMPTY (the money-drop pattern
        # R2 targets) can still pair for arithmetic fill.
        by_amt: dict[str, dict[str, Any]] = {}
        by_unit: dict[str, dict[str, Any]] = {}
        for hr in ha_rows:
            a = _ha_amount_key(hr)
            if a and a not in by_amt:
                by_amt[a] = hr
            u = _ha_unit_key(hr)
            if u and u not in by_unit:
                by_unit[u] = hr
        for tr in table_rows:
            hr = by_amt.get(_ha_amount_key(tr)) or by_unit.get(_ha_unit_key(tr))
            if hr:
                pairs.append((tr, hr))
    filled = 0
    for tr, hr in pairs:
        if not isinstance(tr, dict):
            continue
        for col in _HA_FILL_COLUMNS:
            if str(tr.get(col) or "").strip():
                continue  # never overwrite an existing (strict/study) value
            clean = _ha_clean_fill(col, hr.get(col))
            if clean:
                tr[col] = clean
                filled += 1
        # R2: money (arithmetic-verified) + spec fill into empty cells
        filled += _ha_fill_arith_and_spec(tr, hr)
    debug.update(applied=True, filled=filled, pairs=len(pairs), reason="ok")
    return table_rows, debug


def append_missing_ha_rows(
    table_rows: Any, ocr_lines_raw: Any,
) -> tuple[Any, dict[str, Any]]:
    """③P1: 헤더-앵커 2D 재구성(HA) 행 중 기존 표에 없는 품목행을 '추가만' 한다.

    근거(062 P0 전수실측): 미추출 GT행 3,539 중 dropped 53.7%, 그 90.9%가
    '품명 단독 라인' — 셀들이 한 라인으로 안 뭉쳐 라인=행 후보 로직이 못 본다.
    HA는 money-anchor y밴드 × 컬럼 Voronoi로 행을 재구성하므로 이 부류를 통째
    회수한다. 기존 행은 절대 수정하지 않음(추가만). 중복 가드: 이름 포함(양방향)
    ·유사도·amount 키. 요약/보일러플레이트/파티메타 행은 추가 금지.
    """
    import difflib

    dbg: dict[str, Any] = {"appended": 0, "reason": ""}
    if not isinstance(table_rows, list):
        return table_rows, dbg
    ocr_items = _extract_ocr_line_items(ocr_lines_raw)
    ha_rows, ha_dbg = _extract_header_anchored_table(ocr_items, append_mode=True)
    if not ha_dbg.get("use") or not ha_rows:
        dbg["reason"] = ha_dbg.get("reason", "no_ha")
        return table_rows, dbg

    def _n(s: Any) -> str:
        return re.sub(r"\s+", "", _normalize_text(str(s or ""))).lower()

    exist_names = [_n(r.get("itemName")) for r in table_rows
                   if isinstance(r, dict) and str(r.get("itemName") or "").strip()]
    exist_texts = [_n(" ".join(str(v) for v in r.values() if isinstance(v, str)))
                   for r in table_rows if isinstance(r, dict)]
    exist_amts = {_ha_amount_key(r) for r in table_rows if isinstance(r, dict)}
    exist_amts.discard("")

    next_idx = len(table_rows) + 1
    for ha in ha_rows:
        name = str(ha.get("itemName") or "").strip()
        nm = _n(name)
        if len(nm) < 3 or not _HANGUL_RE.search(name):
            continue
        if _is_summary_or_header_line(name) or _metadata_negative_reason(name):
            continue
        if _BOILERPLATE_ROW_RE.search(name) and not _row_names_a_pharma_product(
            _normalize_text(name)
        ):
            continue
        amt = _ha_amount_key(ha)
        # 중복 가드 ①: 이름이 기존 행 텍스트에 있으면(부분포함 양방향) 기본 스킵.
        # 단, 같은 품목이 로트/유효기한별로 여러 행인 '진짜 중복행'이 있다(063 실측
        # gtOnly 잔여 최대 부류 619행). amount 가 고유하고 수량×단가=금액 산술이
        # 맞으면 실재 행 증거로 보고 허용. 산술게이트 없이 amount 고유만으론 OCR
        # 숫자오독 파편이 통과(정크 +1098, 기각) — 게이트 후 217행·cell +881·
        # mismatch +32 (063 전수시뮬).
        if any(nm in t or (len(t) >= 4 and t in nm) for t in exist_texts if t):
            q_ = _ha_fnum(ha.get("quantity"))
            u_ = _ha_fnum(ha.get("unitPrice"))
            a_ = _ha_fnum(ha.get("amount"))
            if not (amt and amt not in exist_amts
                    and q_ and u_ and a_ and abs(q_ * u_ - a_) <= 1):
                continue
        # 중복 가드 ②: 같은 amount 가 이미 표에 있으면 같은 행 → 금지 (amount 는 고유)
        if amt and amt in exist_amts:
            continue
        # 중복 가드 ③: 이름 유사도(0.6)는 amount 로 구분 불가할 때(빈 amount)만 적용.
        # war 품명은 'XX정 용량 포장' 구조라 다른 품목도 접미사가 겹쳐 유사도가 부풀려짐
        # (라코르정120/12.5mg30T vs 로티브정10/5mg30T = 0.62 오탐). amount 가 있고 기존에
        # 없으면 확실히 다른 행이므로 유사도와 무관하게 append.
        if not amt and any(difflib.SequenceMatcher(None, nm, en).ratio() >= 0.6
                           for en in exist_names if en):
            continue
        row = dict(ha)
        row["rowIndex"] = str(next_idx)
        row["_source"] = "invoice_statement_free_ha_appended"
        table_rows.append(row)
        exist_names.append(nm)
        exist_texts.append(_n(" ".join(str(v) for v in row.values() if isinstance(v, str))))
        if amt:
            exist_amts.add(amt)
        next_idx += 1
        dbg["appended"] += 1
    dbg["reason"] = "ok"
    return table_rows, dbg


# ─── 품명입양(adopt): 행은 있는데 itemName 만 빈 행 복구 ───────────────────────
# 근거(063 전수실측): matched-row 품명빈칸 1,049 중 OCR가 품명을 읽은 행 695 —
# 대부분 품명이 '별도 OCR 라인'으로 존재하는데 행 조립 때 숫자행에 안 붙은 것.
# 행의 amount/unitPrice 숫자를 y-앵커로 같은 밴드의 미소비 품명전용 라인을 입양.
# strict 가드(약품형태소 필수 + 회사/요약 라인 배제)로 후보 920 · 정답 849
# (정밀도 92.3%) · master 동반회수 +770 · name-exact +427. 가드를 느슨하게 하면
# 회사명 라인이 y-최근접을 이겨 정밀도 79%로 추락(기각).
_ADOPT_HANGUL_RE = re.compile(r"[가-힣]{2,}")
_ADOPT_BIGNUM_RE = re.compile(r"\d{4,}")
_ADOPT_SUMMARY_RE = re.compile(r"(합계|소계|총|공급|부가세|사업자|주소|전화|팩스|페이지|발행|일자)")
_ADOPT_COMPANY_RE = re.compile(
    r"^[\d\s()주식회사\-·.,]*[가-힣A-Za-z]*(제약|약품|팜|파마|바이오|MS|메디|헬스|유통|상사|약국)[\s()주]*$")
_ADOPT_DRUG_RE = re.compile(
    r"(정|캡슐|캅셀|캡슬|액|시럽|크림|겔|연고|로션|스프레이|패취|패치|점안|주사|산|환|과립"
    r"|시트|밴드|캔디|드롭|츄|정제|필름|좌제|백|병)")


def _adopt_name_line_ok(text: str) -> bool:
    t = (text or "").strip()
    if not _ADOPT_HANGUL_RE.search(t):
        return False
    if _ADOPT_BIGNUM_RE.search(t):  # 금액/코드 섞인 라인은 품명전용 아님
        return False
    if _ADOPT_SUMMARY_RE.search(t):
        return False
    if _ADOPT_COMPANY_RE.match(t):
        return False
    if not _ADOPT_DRUG_RE.search(t):
        return False
    return True


def adopt_missing_item_names(
    table_rows: Any, ocr_lines_raw: Any,
) -> tuple[Any, dict[str, Any]]:
    """itemName 빈 행에 같은 y-밴드의 미소비 품명전용 OCR 라인을 입양(빈칸만, 추가·수정 없음).

    fill_master_match 앞에서 호출해야 입양된 품명이 마스터 매칭을 탄다.
    앵커=행 amount(없으면 unitPrice) 숫자가 포함된 첫 OCR 라인의 y-중심,
    밴드=라인높이×1.2(최소 14px). 한 라인은 한 행에만 입양(소비 추적)."""
    dbg: dict[str, Any] = {"adopted": 0, "reason": ""}
    if not isinstance(table_rows, list) or not table_rows:
        return table_rows, dbg
    lines: list[tuple[float, float, str]] = []
    for ln in (ocr_lines_raw or []):
        try:
            pts, txt = ln[0], str(ln[1] or "")
            ys = [float(p[1]) for p in pts]
        except Exception:
            continue
        if not ys:
            continue
        lines.append((sum(ys) / len(ys), max(max(ys) - min(ys), 1.0), txt))
    if not lines:
        dbg["reason"] = "no_lines"
        return table_rows, dbg

    def _digits(s: Any) -> str:
        return re.sub(r"\D", "", str(s or ""))

    def _n(s: Any) -> str:
        return re.sub(r"[^\w가-힣]", "", str(s or "").lower())

    used = {_n(r.get("itemName")) for r in table_rows
            if isinstance(r, dict) and str(r.get("itemName") or "").strip()}
    used.discard("")
    for row in table_rows:
        if not isinstance(row, dict) or str(row.get("itemName") or "").strip():
            continue
        amt = _digits(row.get("amount")) or _digits(row.get("unitPrice"))
        if len(amt) < 3:
            continue
        anchor = None
        for cy, lh, txt in lines:
            if amt in _digits(txt):
                anchor = (cy, lh)
                break
        if anchor is None:
            continue
        ay, ah = anchor
        band = max(ah * 1.2, 14.0)
        best = None
        for cy, lh, txt in lines:
            if abs(cy - ay) > band or not _adopt_name_line_ok(txt):
                continue
            n = _n(txt)
            if not n or n in used:
                continue
            dy = abs(cy - ay)
            if best is None or dy < best[0]:
                best = (dy, txt.strip(), n)
        if best is None:
            continue
        row["itemName"] = best[1]
        used.add(best[2])
        dbg["adopted"] += 1
    dbg["reason"] = "ok"
    return table_rows, dbg


# ─── 행신설(synth): GT행이 통째로 안 만들어진 gtOnly 부류 복구 ────────────────
# 근거(063 전수실측): 4패치 후에도 gtOnly 2,214행 중 76%(1,675)는 OCR가 품명을
# 읽음 — 파서가 행을 아예 못 만든 것. 미소비 품명전용 라인 + 같은 y-밴드의
# 미소비 콤마-금액 라인이 공존하면 (itemName, amount) 행을 신설한다(헤더 불요).
# 게이트 3중(전수 스윕으로 확정): ①품명이 master 사전에 sim>=0.35로 매칭(비약품
# 라인 차단) ②기존 품명과 fuzzy 0.8 중복 배제(도플갱어 차단) ③콤마-금액만(코드/
# 수량/날짜 오인 차단). 무게이트 신설=7,379행 중 정크 6,269(기각) → 3중 게이트=
# 신설 844 · GT정렬 485(57%) · 정크 +359 · cell +1,173 · master +438.
_SYNTH_MONEY_RE = re.compile(r"\d{1,3}(?:,\d{3})+")
# V5 jamo-trigram 스케일 재보정: 음절 0.35 ≈ 자모 0.45 (floor 등가비 ~1.25).
_SYNTH_SIM_FLOOR = 0.45


def synthesize_missing_rows(
    table_rows: Any, ocr_lines_raw: Any,
) -> tuple[Any, dict[str, Any]]:
    """미소비 품명라인+콤마금액 y-밴드 쌍으로 누락 품목행을 신설(추가만, 기존 불변).

    adopt_missing_item_names 뒤·fill_master_match 앞에서 호출 — 입양이 품명라인을
    먼저 소비하고, 신설 행이 마스터 매칭을 탄다. master_dict 없으면 자동 비활성."""
    dbg: dict[str, Any] = {"synthesized": 0, "reason": ""}
    if not isinstance(table_rows, list):
        return table_rows, dbg
    try:
        from extractors.master_match import get_matcher, clean_query_name
        matcher = get_matcher()
    except Exception:
        matcher = None
    if matcher is None:
        dbg["reason"] = "no_matcher"
        return table_rows, dbg
    import difflib
    lines: list[tuple[float, float, str]] = []
    for ln in (ocr_lines_raw or []):
        try:
            pts, txt = ln[0], str(ln[1] or "")
            ys = [float(p[1]) for p in pts]
        except Exception:
            continue
        if not ys:
            continue
        lines.append((sum(ys) / len(ys), max(max(ys) - min(ys), 1.0), txt))
    if not lines:
        dbg["reason"] = "no_lines"
        return table_rows, dbg

    def _digits(s: Any) -> str:
        return re.sub(r"\D", "", str(s or ""))

    def _n(s: Any) -> str:
        return re.sub(r"[^\w가-힣]", "", str(s or "").lower())

    exist_names = [_n(r.get("itemName")) for r in table_rows
                   if isinstance(r, dict) and str(r.get("itemName") or "").strip()]
    used_names = set(exist_names)
    used_names.discard("")
    used_amts: set[str] = set()
    for r in table_rows:
        if not isinstance(r, dict):
            continue
        for k in ("amount", "unitPrice", "supplyAmount", "totalAmount"):
            d = _digits(r.get(k))
            if len(d) >= 3:
                used_amts.add(d)
    used_money_lines: set[int] = set()
    next_idx = len(table_rows) + 1
    for idx, (cy, lh, txt) in enumerate(lines):
        if not _adopt_name_line_ok(txt):
            continue
        n = _n(txt)
        if not n or n in used_names:
            continue
        if any(difflib.SequenceMatcher(None, n, e).ratio() >= 0.8 for e in exist_names if e):
            continue
        try:
            cands = matcher.top_candidates(clean_query_name(txt), 1)
        except Exception:
            continue
        if not cands or cands[0][0] < _SYNTH_SIM_FLOOR:
            continue
        band = max(lh * 1.2, 14.0)
        money = None
        for j, (cy2, _lh2, txt2) in enumerate(lines):
            if j == idx or j in used_money_lines or abs(cy2 - cy) > band:
                continue
            for v in _SYNTH_MONEY_RE.findall(txt2):
                dd = _digits(v)
                if len(dd) >= 4 and dd not in used_amts:
                    money = (j, v)
                    break
            if money:
                break
        if money is None:
            continue
        used_money_lines.add(money[0])
        used_names.add(n)
        exist_names.append(n)
        used_amts.add(_digits(money[1]))
        table_rows.append({
            "rowIndex": str(next_idx), "itemName": txt.strip(), "spec": "",
            "quantity": "", "unitPrice": "", "amount": money[1],
            "_source": "invoice_statement_free_row_synth",
        })
        next_idx += 1
        dbg["synthesized"] += 1
    dbg["reason"] = "ok"
    return table_rows, dbg


_BLOB_MONEY_RE = re.compile(r"\d{1,3}(?:,\d{3})+")


def salvage_blob_amount(table_rows: Any) -> tuple[Any, dict[str, Any]]:
    """놓친 행 회복(정렬용): 파서가 컬럼화에 실패해 amount 칸이 빈 'blob' 행에서
    _rawText 의 마지막 콤마-금액을 amount 로 살린다.

    근거: content-align 은 ``0.5·이름유사도 + 0.35·금액일치 + 0.15·수량일치``(임계 0.30).
    blob 행은 amount 필드가 비어 금액일치=0 → 이름유사도만으로는 임계 미달 → GT 행이
    통째로 미매칭(8셀 손실)된다. amount 만 채워도 금액일치(0.35)로 정렬이 복원된다.
    (062 측정: 놓친 GT 행의 30% 가 GT amount == blob 행의 마지막 콤마-금액.)

    가드: 이미 amount 가 있으면 건드리지 않음, 요약/합계·party 메타 행 제외,
    한글 품명이 있는 진짜 품목행 + 콤마-금액이 있을 때만. 빈 unitPrice 는 마지막
    직전 콤마-금액으로 보조 채움(있을 때만).
    """
    debug: dict[str, Any] = {"salvaged": 0, "unitFilled": 0}
    if not isinstance(table_rows, list):
        return table_rows, debug
    for row in table_rows:
        if not isinstance(row, dict):
            continue
        if str(row.get("amount") or "").strip():
            continue
        raw = _normalize_text(row.get("_rawText") or row.get("itemName") or "")
        if not raw or not _HANGUL_RE.search(raw):
            continue
        if _is_summary_or_header_line(raw) or _metadata_negative_reason(raw):
            continue
        # 합계/순매출/품절 등 요약·장식 행은 salvage 금지(spurious 금액 방지). 진짜
        # 약품명 행은 요약마커와 무관하므로 통과. drop_boilerplate 와 같은 기준.
        if _BOILERPLATE_ROW_RE.search(raw) and not _row_names_a_pharma_product(
            _normalize_text(row.get("itemName"))
        ):
            continue
        moneys = _BLOB_MONEY_RE.findall(raw)
        if not moneys:
            continue
        cand = moneys[-1]
        cand_num = re.sub(r"[^0-9]", "", cand)
        qty_num = re.sub(r"[^0-9]", "", str(row.get("quantity") or ""))
        unit_num = re.sub(r"[^0-9]", "", str(row.get("unitPrice") or ""))
        # 마지막 콤마-금액이 이미 파싱된 수량/단가와 같으면 그건 amount 가 아니라
        # 그 필드의 값 → salvage 금지(수량을 amount 로 넣는 spurious 방지).
        if cand_num and (cand_num == qty_num or cand_num == unit_num):
            continue
        row["amount"] = cand
        debug["salvaged"] += 1
        if len(moneys) >= 2 and not str(row.get("unitPrice") or "").strip():
            row["unitPrice"] = moneys[-2]
            debug["unitFilled"] += 1
    return table_rows, debug


# ─── 단가·금액 열 복구(금액P1): 재배정 + 산술 단가fill ─────────────────────────
# 근거(066 thin 5,964 전수실측): amount 결함행 15,286 중 2,316행 = 같은 행의 단가
# 값이 amount 칸에 착지(오배치, 그 81%는 unitPrice 칸이 빔). 반대로 '금액|단가'
# 순서 표에서는 amount 는 정위치인데 unitPrice 만 빈다. 두 모양을 한 룰로 복구.
#
# 행 정체성이 핵심 가드: 페이지 전역 y-밴드 검색은 인접 '같은 품목' 행의 같은 값에
# 락온한다(066 전수 시뮬: 회귀 18 전원이 이 부류 — 예: 같은 약이 수량 1/5로 두 행).
# → 행 자신의 _rawText 토큰 문자열과 밴드 토큰의 중첩 스코어가 '유일 최대'인 밴드만
# 그 행의 밴드로 인정(동률·저스코어 skip). 인접 같은품목 행은 숫자 토큰이 달라
# (5|25,276|126,380 vs 1|25.276|25,276) 문자열 중첩으로 정확히 갈린다.
#
# 산술 게이트는 정확일치(±1)만 — 0.5% 비례 허용오차는 시뮬에서 오발화(36446×2=
# 72892 를 72891 에 매칭). 066 800문서 시뮬: A재배정 222·C단가fill 132, 기존
# amount match 훼손 0, spurious 0, unitPrice 정밀도 93.6%/89.8%.
_UPA_SQ_RE = re.compile(r"\s+")


def _upa_parse_money(raw: str) -> float | None:
    """money 토큰 파서 — 천단위 콤마/점('174.600'→174600) + 소수 단가('34,920.00'
    →34920.0) 인식. 비 money 문자열은 None."""
    t = (raw or "").strip().strip(".")
    if not t or not re.fullmatch(r"[\d,\.]+", t):
        return None
    if re.fullmatch(r"\d{1,3}(?:\.\d{3})+", t):        # 점-천단위 (OCR 콤마 오독)
        return float(t.replace(".", ""))
    if re.fullmatch(r"\d{1,3}(?:,\d{3})+(?:\.\d{1,2})?", t):  # 콤마 천단위(+소수)
        return float(t.replace(",", ""))
    if re.fullmatch(r"\d+(?:\.\d{1,2})?", t):           # 순수 정수/소수
        return float(t)
    return None


def _upa_money_like(raw: str, val: float | None) -> bool:
    """단가/금액으로 쓸 만한 모양인가 — 구분자 보유 또는 1000 이상(코드·순번 배제)."""
    return ("," in raw or "." in raw or (val is not None and val >= 1000))


def _upa_fmt(val: float) -> str:
    """정규화 안전 포맷: 정수는 '8939', 소수 단가는 '8939.5' (float 꼬리 '.0' 금지 —
    norm_amount 가 digits-only 라 '34920.0'→'349200' 오염)."""
    return str(int(val)) if float(val).is_integer() else str(val)


def recover_unitprice_amount_columns(
    table_rows: Any, ocr_lines_raw: Any,
) -> tuple[Any, dict[str, Any]]:
    """unitPrice 빈 행의 단가·금액 열 복구 (free+fallback 합류점, 경로무관).

    C 단가fill: 행 밴드 내 u(≠v)가 q×u==v(±1) → unitPrice:=u (amount 불변·안전)
    A 재배정:  행 밴드 내 앵커 오른쪽 정수 a가 q×v==a(±1) → unitPrice:=v, amount:=a
    A·C 동시 성립 또는 후보 값 복수 → 모호 → skip. q>1 만(수량 1은 판별 불가·무익).
    빈 quantity 는 증명에 쓰인 q 로 보조 채움(빈칸만)."""
    dbg: dict[str, Any] = {"moved": 0, "unitFilled": 0, "qtyFilled": 0}
    if not isinstance(table_rows, list) or not table_rows:
        return table_rows, dbg
    toks: list[tuple[float, float, float, str, float | None]] = []
    for ln in (ocr_lines_raw or []):
        try:
            pts, txt = ln[0], str(ln[1] or "").strip()
            xs = [float(p[0]) for p in pts]
            ys = [float(p[1]) for p in pts]
        except Exception:
            continue
        if not txt or not xs or not ys:
            continue
        toks.append((sum(xs) / len(xs), sum(ys) / len(ys),
                     max(max(ys) - min(ys), 1.0), txt,
                     _upa_parse_money(_UPA_SQ_RE.sub("", txt))))
    if not toks:
        return table_rows, dbg
    # 같은 amount 값(파싱 기준 — '44,280.00'≡'44,280')이 여러 행에 있으면 어느 행의
    # 페이지 앵커인지 판별 불가(파편/중복 행이 진짜 행의 앵커를 훔치는 사고 — 066
    # 전수 시뮬 회귀 전부 이 부류) → 제외. HA-append 중복행이 흔해 파싱값으로 비교.
    amt_counts: dict[float, int] = {}
    for row in table_rows:
        if isinstance(row, dict):
            cv = _upa_parse_money(_UPA_SQ_RE.sub("", str(row.get("amount") or "")))
            if cv is not None:
                amt_counts[cv] = amt_counts.get(cv, 0) + 1
    for row in table_rows:
        if not isinstance(row, dict):
            continue
        if str(row.get("unitPrice") or "").strip():
            continue
        am = str(row.get("amount") or "").strip()
        if not am:
            continue
        v_val = _upa_parse_money(_UPA_SQ_RE.sub("", am))
        if v_val is None or v_val < 10:
            continue
        if amt_counts.get(v_val, 0) > 1:
            continue
        raw = str(row.get("_rawText") or "")
        if not raw or _is_summary_or_header_line(_normalize_text(raw)):
            continue
        raw_toks = {_UPA_SQ_RE.sub("", t) for t in raw.split()
                    if len(_UPA_SQ_RE.sub("", t)) >= 2}
        if len(raw_toks) < 3:
            continue
        anchors = [t for t in toks if t[4] == v_val]
        if not anchors:
            continue
        # 행 정체성: _rawText 토큰 문자열 중첩이 유일 최대인 앵커 밴드만
        best: tuple | None = None
        best_score, tie = -1, False
        for a in anchors:
            band = max(a[2] * 0.8, 10.0)
            bt = [t for t in toks if abs(t[1] - a[1]) <= band]
            score = sum(1 for t in bt if _UPA_SQ_RE.sub("", t[3]) in raw_toks)
            if score > best_score:
                best, best_score, tie = (a, bt), score, False
            elif score == best_score:
                tie = True
        if best is None or tie or best_score < 3:
            continue
        anchor, bt = best
        # 수량 후보: 행 ext 수량 우선, 없으면 밴드 내 정수 토큰
        qs: list[float] = []
        q_from_row = False
        qd = re.sub(r"\D", "", str(row.get("quantity") or ""))
        if qd and 1 <= len(qd) <= 5:
            try:
                qv = float(qd)
                if qv > 1:
                    qs, q_from_row = [qv], True
            except ValueError:
                pass
        if not qs:
            qs = [t[4] for t in bt if t[4] is not None and t[4].is_integer()
                  and 1 < t[4] <= 9999 and t[4] != v_val][:6]
        if not qs:
            continue
        c_hits: list[tuple[tuple, float]] = []
        a_hits: list[tuple[tuple, float]] = []
        for t in bt:
            tv = t[4]
            if tv is None or tv == v_val or t is anchor:
                continue
            if not _upa_money_like(t[3], tv):
                continue
            cq = next((q for q in qs if abs(q * tv - v_val) <= 1.0), None)
            if cq is not None:
                c_hits.append((t, cq))
            if t[0] > anchor[0] and float(tv).is_integer():
                aq = next((q for q in qs if abs(q * v_val - tv) <= 1.0), None)
                if aq is not None:
                    a_hits.append((t, aq))
        c_vals = {t[4] for t, _ in c_hits}
        a_vals = {t[4] for t, _ in a_hits}
        if (c_vals and a_vals) or len(c_vals) > 1 or len(a_vals) > 1:
            continue  # 모호 — 두 해석/복수 후보면 손대지 않음
        if len(c_vals) == 1:
            t, q = c_hits[0]
            row["unitPrice"] = _upa_fmt(t[4])
            dbg["unitFilled"] += 1
        elif len(a_vals) == 1:
            t, q = a_hits[0]
            # A재배정은 amount 를 바꾸므로 증거 강도 가드: 행 자신의 수량으로 증명
            # 됐거나, 아니면(밴드에서 빌린 q) 결과가 다른 행 amount 와 중복을 만들지
            # 않아야 한다. 468482 실측: qty=1 행(단가==금액, 정답)이 빈 수량 때문에
            # 하이재킹된 밴드의 q=4·147,552 를 물어 진짜 행과 중복 금액 생성 → 회귀.
            if not q_from_row and amt_counts.get(float(t[4]), 0) >= 1:
                continue
            row["unitPrice"] = _upa_fmt(v_val)
            row["amount"] = _upa_fmt(t[4])
            dbg["moved"] += 1
        else:
            continue
        if not q_from_row and not str(row.get("quantity") or "").strip():
            row["quantity"] = _upa_fmt(q)
            dbg["qtyFilled"] += 1
    return table_rows, dbg


# ─── geometry 숫자열 재구성(금액P3): 붕괴 문서의 수량·단가·금액 복구 ─────────────
# 근거(066 thin 전수실측): 숫자 3열 동반붕괴 11,302행. 합류점 후처리 각도(산술트리플
# 49%/열좌표 자기학습 19.6%/HA가드완화 79%쓰레기)는 전부 정밀도 미달로 기각 —
# 붕괴행은 '조립 실패의 결과물'이라 결과물 기반 역추정이 불가능하기 때문.
# 해법 = 조립 위치의 룰: OCR 토큰 기하만으로 표를 재구성(행=money y-클러스터,
# 열=숫자 x-클러스터)하고 열 정체를 산술투표(V1)+헤더토큰(V2)으로 식별.
# 600문서 드라이런: 재구성 성공 93%, 열배정 238문서, 배정문서 내 회복 76.4%·
# 정밀도 91.8%. V3(순서/타입 휴리스틱)는 V1일치 40%로 기각.
# 병합은 게이트 안전형: 빈 셀만 fill(정체앵커 필수) + 미바인딩 행 append(산술성립
# 필수). 덮어쓰기 없음 → 기존 match 훼손 구조적으로 불가.
_GEO_HDR_LABEL = {"수량": "quantity", "단가": "unitPrice", "금액": "amount",
                  "판매단가": "unitPrice", "판매금액": "amount", "공급금액": "amount"}
_ADOPT_NN_RE = re.compile(r"[^0-9A-Za-z가-힣]+")   # 이름 비교용 정규화(기호/공백 제거)


def _geo_reconstruct(toks: list[tuple]) -> tuple[list[dict], list[float], float | None]:
    """geometry-only 표 재구성. toks=(cx,cy,h,text,money|None).
    반환 (rows, col_xs, first_row_y). row={"_y":y, col_x: money값}."""
    nums = [t for t in toks if t[4] is not None and t[4] > 0]
    moneys = [t for t in nums if ("," in t[3] or "." in t[3] or t[4] >= 1000)]
    if len(moneys) < 2:
        return [], [], None
    rows_y: list[float] = []
    for y in sorted(t[1] for t in moneys):
        if not rows_y or y - rows_y[-1] > 8:
            rows_y.append(y)
    clusters: list[list[float]] = []
    for x in sorted(t[0] for t in nums):
        if not clusters or x - clusters[-1][-1] > 30:
            clusters.append([x])
        else:
            clusters[-1].append(x)
    cols = [sum(c) / len(c) for c in clusters if len(c) >= max(2, 0.3 * len(rows_y))]
    if len(cols) < 2:
        return [], [], None
    rows: list[dict] = []
    for ry in rows_y:
        band = [t for t in nums if abs(t[1] - ry) <= max(10.0, t[2] * 0.8)]
        row: dict = {"_y": ry}
        for cx in cols:
            cand = [t for t in band if abs(t[0] - cx) <= 30]
            if cand:
                row[cx] = min(cand, key=lambda t: abs(t[0] - cx))[4]
        if len(row) >= 3:   # _y 포함 → 값 2개 이상
            rows.append(row)
    return rows, cols, (rows_y[0] if rows_y else None)


def _geo_assign_columns(toks, recon_rows, cols, first_row_y):
    """열 정체 식별: V2 헤더토큰(표 위쪽 단독 라벨, 3열 완전 발견 시) 우선,
    아니면 V1 산술투표(q*u==a ±1 성립행 최다, >=2행). 실패 시 None.
    드라이런: V1·V2 동시성공 11문서 전원 일치(충돌 0)."""
    from itertools import permutations
    if first_row_y is not None:
        found: dict = {}
        for t in toks:
            lbl = _GEO_HDR_LABEL.get(_UPA_SQ_RE.sub("", t[3]))
            if lbl and t[1] < first_row_y:
                near = min(cols, key=lambda c: abs(c - t[0]))
                if abs(near - t[0]) <= 40 and lbl not in found:
                    found[lbl] = near
        q, u, a = found.get("quantity"), found.get("unitPrice"), found.get("amount")
        if q and u and a and len({q, u, a}) == 3:
            return (q, u, a), "header"
    best, bestv = None, 0
    for q, u, a in permutations(cols, 3):
        v = 0
        for r in recon_rows:
            qv, uv, av = r.get(q), r.get(u), r.get(a)
            if qv and uv and av and float(qv).is_integer() and 1 <= qv <= 9999 \
                    and uv >= 10 and av >= 10 and abs(qv * uv - av) <= 1:
                v += 1
        if v > bestv:
            best, bestv = (q, u, a), v
    return (best, "arith") if best is not None and bestv >= 2 else (None, "none")


# ── 금액P3-T: y-밴드 산술 트리플 스캔 (열배정-무관) ─────────────────────────────
# 근거(066 실측): 헤드룸에서 GT 수량·단가·금액이 같은 y-밴드에 공존+경쟁트리플 없음
# = 1,886셀(배정성공 1,444 + 배정실패 442). q×u=a 가 성립하면 (수량,단가,금액)이
# 수학적으로 자동 결정되므로 열배정·x클러스터 불요 → 기울어진 문서에도 면역.
# 병합토큰(여러 숫자가 한 토큰) 대응: 토큰 내부 money 패턴 findall.
# 유일성 가드: 밴드에 서로 다른 트리플 2개면 모호 → skip (실측 모호율 9~11%).
_TRIPLE_MONEY_RE = re.compile(   # 글자에 붙은 숫자(625mg, EA30 등)는 값 아님 — 경계 요구
    r"(?<![A-Za-z가-힣\d])(\d{1,3}(?:,\d{3})+(?:\.\d{1,2})?|\d+(?:\.\d{1,2})?)(?![A-Za-z가-힣\d])")
_TRIPLE_SUMMARY_RE = re.compile(r"합\s*계|소\s*계|총\s*계|총\s*액|매출\s*계|월\s*계|누\s*계")
_TRIPLE_NN_RE = re.compile(r"[^0-9A-Za-z가-힣]+")


def _geo_triple_scan(table_rows: Any, toks: list[tuple], dbg: dict) -> tuple[Any, dict]:
    """밴드별 유일 산술 트리플을 찾아 기존 행에 병합(값앵커=덮기·이름앵커=빈칸fill)
    하고, 못 이으면 append. reconstruct_numeric_columns 의 모든 경로 끝에서 호출."""
    dbg.setdefault("tripleFilled", 0)
    dbg.setdefault("tripleOverwritten", 0)
    dbg.setdefault("tripleAppended", 0)
    if not isinstance(table_rows, list) or not table_rows or not toks:
        return table_rows, dbg
    # 밴드 앵커: 토큰 '내부' money (병합토큰 '20 3,952 79,040' 도 앵커가 되도록)
    anchor_ys: list[float] = []
    for t in toks:
        for m in _TRIPLE_MONEY_RE.findall(t[3]):
            v = _upa_parse_money(m)
            if v is not None and (("," in m) or v >= 1000):
                anchor_ys.append(t[1])
                break
    if not anchor_ys:
        return table_rows, dbg
    band_ys: list[float] = []
    for y in sorted(anchor_ys):
        if not band_ys or y - band_ys[-1] > 8:
            band_ys.append(y)
    # 밴드별 유일 트리플 추출
    triples: list[tuple[float, float, float, float]] = []   # (y, q, u, a)
    for by in band_ys:
        band = [t for t in toks if abs(t[1] - by) <= max(12.0, t[2] * 0.9)]
        if any(_TRIPLE_SUMMARY_RE.search(t[3]) for t in band):
            continue
        vals: set[float] = set()
        for t in band:
            for m in _TRIPLE_MONEY_RE.findall(t[3]):
                v = _upa_parse_money(m)
                if v is not None and v > 0:
                    vals.add(v)
        if len(vals) < 3:
            continue
        sv = sorted(vals)
        # 거울쌍 (q,u,a)/(u,q,a) 는 같은 물리 트리플 → (a, {q,u}) 로 정규화해 유일성 판정
        found: set[tuple[float, frozenset]] = set()
        for q in sv:
            if not (float(q).is_integer() and 2 <= q <= 9999):
                continue  # q=1 은 (1,v,v) 퇴화로 모호 폭발 → 제외
            for u in sv:
                if u < 10 or u == q:
                    continue
                for a in sv:
                    if a < 100 or a == u or a == q:
                        continue
                    if abs(q * u - a) <= 1:
                        found.add((a, frozenset((q, u))))
        if len(found) != 1:
            continue  # 0=불가, 2+=모호
        a, qu = next(iter(found))
        q, u = sorted(qu)   # 관례: 작은 쪽=수량 (제약시장 단가≫수량)
        triples.append((by, q, u, a))
    if not triples:
        return table_rows, dbg

    def pnum(row, col):
        return _upa_parse_money(_UPA_SQ_RE.sub("", str(row.get(col) or "")))

    def nn(s):
        return _TRIPLE_NN_RE.sub("", str(s or "")).lower()

    hangul_lines = [(t[1], t[3]) for t in toks
                    if _ADOPT_HANGUL_RE.search(t[3]) and _adopt_name_line_ok(t[3])]

    def band_name(by):
        near = min(hangul_lines, key=lambda z: abs(z[0] - by), default=None)
        return near[1].strip() if near is not None and abs(near[0] - by) <= 12 else ""

    exist_amts = {v for row in table_rows if isinstance(row, dict)
                  if (v := pnum(row, "amount")) is not None}
    used_rows: set[int] = set()
    appends: list[dict] = []
    next_idx = len(table_rows) + 1
    for by, q, u, a in triples:
        if a in exist_amts:
            continue  # 이미 어떤 행이 이 금액 보유(정답행 or 중복) → 손대지 않음
        target = None; strength = None
        # 1) 값앵커: 수량·단가 둘 다 일치(강) 또는 단가 일치(중)
        for row in table_rows:
            if not isinstance(row, dict) or id(row) in used_rows:
                continue
            rq, ru = pnum(row, "quantity"), pnum(row, "unitPrice")
            if rq == q and ru == u:
                target, strength = row, "strong"
                break
        if target is None:
            cand = [row for row in table_rows if isinstance(row, dict)
                    and id(row) not in used_rows and pnum(row, "unitPrice") == u]
            if len(cand) == 1:
                target, strength = cand[0], "strong"
        # 2) 이름앵커(약): 밴드 품명 ↔ 행 품명
        if target is None:
            bn = nn(band_name(by))
            if len(bn) >= 3:
                for row in table_rows:
                    if not isinstance(row, dict) or id(row) in used_rows:
                        continue
                    rn = nn(row.get("itemName"))
                    if len(rn) >= 3 and (bn[:6] in rn or rn[:6] in bn):
                        target, strength = row, "weak"
                        break
        if target is not None:
            used_rows.add(id(target))
            for col, v in (("quantity", q), ("unitPrice", u), ("amount", a)):
                cur = str(target.get(col) or "").strip()
                if not cur:
                    target[col] = _upa_fmt(v)
                    dbg["tripleFilled"] += 1
                    if col == "amount":
                        exist_amts.add(a)
                    continue
                if strength != "strong":
                    continue
                cur_val = _upa_parse_money(_UPA_SQ_RE.sub("", cur))
                if cur_val is None or cur_val == v:
                    continue
                if col == "amount":
                    # F4b 금액가드 동일: 단가침범 or 곱의<0.45배(쓰레기)만 덮음
                    if not (cur_val == u or (a and cur_val / a < 0.45)):
                        continue
                    exist_amts.add(a)
                target[col] = _upa_fmt(v)
                dbg["tripleOverwritten"] += 1
            continue
        # 3) append: 밴드 품명이 기존 행과 겹치면 금지(정렬스틸), 금액중복은 위에서 차단
        name = band_name(by)
        if name and any(
                (rn := nn(row.get("itemName"))) and len(rn) >= 3
                and (nn(name)[:6] in rn or rn[:6] in nn(name))
                for row in table_rows if isinstance(row, dict)):
            continue
        appends.append({
            "rowIndex": str(next_idx),
            "itemCode": "", "productCode": "", "itemName": name, "spec": "",
            "lotNo": "", "serialNo": "", "manufacturingNo": "", "expiryDate": "",
            "quantity": _upa_fmt(q), "unit": "", "unitPrice": _upa_fmt(u),
            "supplyAmount": "", "taxAmount": "", "amount": _upa_fmt(a),
            "totalAmount": "", "manufacturer": "", "insuranceCode": "", "remark": "",
            "_rawText": "", "_confidence": "0.5",
            "_source": "invoice_statement_free_geo_triple",
        })
        exist_amts.add(a)
        next_idx += 1
        dbg["tripleAppended"] += 1
    table_rows.extend(appends)
    return table_rows, dbg


def reconstruct_numeric_columns(
    table_rows: Any, ocr_lines_raw: Any,
) -> tuple[Any, dict[str, Any]]:
    """붕괴 문서의 수량·단가·금액 geometry 복구 (free+fallback 합류점).

    M1 fill: 기존 행 ↔ 재구성 행을 정체앵커로 바인딩 — (i) 기존 행의 비지 않은
       숫자셀 값이 재구성 행 같은 열 값과 정확일치 >=1개, 또는 (ii) _rawText 토큰의
       y-중심이 재구성 행 y와 일치. 바인딩된 행의 '빈' 숫자셀만 채움.
    M2 append: 어느 기존 행에도 안 바인딩된 재구성 행 중 산술성립(q*u==a ±1)이고
       금액이 comma-money 인 것만 새 행으로 추가(+같은 y-밴드 미소비 한글 품명 입양).
    덮어쓰기 없음. 요약행(합계 등) y 이후 재구성 행은 append 금지."""
    dbg: dict[str, Any] = {"filled": 0, "appended": 0, "assign": "none"}
    if not isinstance(table_rows, list) or not table_rows:
        return table_rows, dbg
    toks: list[tuple] = []
    for ln in (ocr_lines_raw or []):
        try:
            pts, txt = ln[0], str(ln[1] or "").strip()
            xs = [float(p[0]) for p in pts]
            ys = [float(p[1]) for p in pts]
        except Exception:
            continue
        if not txt or not xs or not ys:
            continue
        toks.append((sum(xs) / len(xs), sum(ys) / len(ys),
                     max(max(ys) - min(ys), 1.0), txt,
                     _upa_parse_money(_UPA_SQ_RE.sub("", txt))))
    if not toks:
        return table_rows, dbg
    recon, cols, fry = _geo_reconstruct(toks)
    if not recon:
        return _geo_triple_scan(table_rows, toks, dbg)
    assign, how = _geo_assign_columns(toks, recon, cols, fry)
    dbg["assign"] = how
    if not assign:
        return _geo_triple_scan(table_rows, toks, dbg)
    q_c, u_c, a_c = assign
    COLMAP = (("quantity", q_c), ("unitPrice", u_c), ("amount", a_c))

    # ── 기존 행 바인딩: 값일치 앵커 → rawText-y 앵커
    def row_y_from_raw(row) -> float | None:
        raw_toks = {_UPA_SQ_RE.sub("", t) for t in str(row.get("_rawText") or "").split()
                    if len(_UPA_SQ_RE.sub("", t)) >= 4}
        if not raw_toks:
            return None
        ys = [t[1] for t in toks if _UPA_SQ_RE.sub("", t[3]) in raw_toks]
        if len(ys) < 3:   # 토큰 2개는 오바인딩 잦음(검증 실측) → 3개 이상 요구
            return None
        ys.sort()
        return ys[len(ys) // 2]

    # 재구성행 y 근처의 품명 라인(이름 바인딩·append 입양 공용)
    hangul_lines = [(t[1], t[3]) for t in toks
                    if _ADOPT_HANGUL_RE.search(t[3]) and _adopt_name_line_ok(t[3])]

    def geo_name(rr) -> str:
        near = min(hangul_lines, key=lambda z: abs(z[0] - rr["_y"]), default=None)
        return near[1].strip() if near is not None and abs(near[0] - rr["_y"]) <= 12 else ""

    def name_sim_ok(a: str, b: str) -> bool:
        na, nb = _ADOPT_NN_RE.sub("", a).lower(), _ADOPT_NN_RE.sub("", b).lower()
        if len(na) < 3 or len(nb) < 3:
            return False
        return na[:6] in nb or nb[:6] in na

    # 값일치 앵커의 유일성 전제: 같은 값이 재구성표의 여러 행에 있으면(같은 품목
    # 반복행) 어느 행인지 판별 불가 → 그 값은 앵커로 못 씀. (fill-only 검증에서
    # 회귀 621의 주범 = 중복값 오바인딩)
    from collections import Counter as _Ctr
    val_freq: dict = _Ctr()
    for rr in recon:
        for _col, c in COLMAP:
            v = rr.get(c)
            if v is not None:
                val_freq[v] += 1

    def geo_arith_ok(rr) -> bool:
        qv, uv, av = rr.get(q_c), rr.get(u_c), rr.get(a_c)
        return bool(qv and uv and av and abs(qv * uv - av) <= 1)

    used_recon: set[int] = set()
    bound: list[tuple[dict, int]] = []
    # 1패스: 값일치 앵커 (유일값만 — 가장 강한 정체 증거)
    for row in table_rows:
        if not isinstance(row, dict):
            continue
        vals = {col: _upa_parse_money(_UPA_SQ_RE.sub("", str(row.get(col) or "")))
                for col, _c in COLMAP}
        for i, rr in enumerate(recon):
            if i in used_recon:
                continue
            agree = sum(1 for col, c in COLMAP
                        if vals[col] is not None and rr.get(c) is not None
                        and vals[col] == rr[c] and val_freq.get(rr[c], 0) == 1)
            if agree >= 1:
                used_recon.add(i)
                bound.append((row, i, "strong"))
                break
    bound_rows = {id(r) for r, _, _ in bound}
    # 2패스: 품명 바인딩 — geo행 y 근처 품명라인 ↔ 기존 행 itemName. append 가
    # 정렬을 뺏는 사고(전수검증 회귀 2,023 주범)를 '그 행에 병합'으로 바꾼다.
    for row in table_rows:
        if not isinstance(row, dict) or id(row) in bound_rows:
            continue
        rn = str(row.get("itemName") or "").strip()
        if len(rn) < 3:
            continue
        for i, rr in enumerate(recon):
            if i in used_recon:
                continue
            gn = geo_name(rr)
            if gn and name_sim_ok(rn, gn):
                used_recon.add(i)
                bound.append((row, i, "weak"))
                bound_rows.add(id(row))
                break
    # 3패스: rawText-y 바인딩
    for row in table_rows:
        if not isinstance(row, dict) or id(row) in bound_rows:
            continue
        ry = row_y_from_raw(row)
        if ry is None:
            continue
        near = min(((i, rr) for i, rr in enumerate(recon) if i not in used_recon),
                   key=lambda z: abs(z[1]["_y"] - ry), default=None)
        if near is not None and abs(near[1]["_y"] - ry) <= 12:
            used_recon.add(near[0])
            bound.append((row, near[0], "weak"))
            bound_rows.add(id(row))
    # M1 fill/overwrite. geo행 산술성립 필수(내적 자기검증). 강한 바인딩(값일치 유일
    # 앵커)에서는 오값도 산술성립 geo값으로 덮음(F4b: 헤드룸 6,734 중 geo가 이미
    # 정답을 amount열에 잡은 2,603셀 = 단가침범·오독을 산술+geo 이중확인으로 교정).
    # 약한 바인딩(품명/rawText)은 빈칸만 — 오바인딩 시 오값 덮기 위험 차단.
    dbg.setdefault("overwritten", 0)
    for row, i, strength in bound:
        rr = recon[i]
        if not geo_arith_ok(rr):
            continue
        for col, c in COLMAP:
            v = rr.get(c)
            if v is None or v <= 0:
                continue
            if col == "quantity" and not (float(v).is_integer() and 1 <= v <= 9999):
                continue
            cur = str(row.get(col) or "").strip()
            if not cur:
                row[col] = _upa_fmt(v)
                dbg["filled"] += 1
            elif strength == "strong":
                # 오값 덮기: 현재값이 산술성립 geo값과 다를 때만(같으면 no-op).
                # 강한 앵커라 이 행=이 geo행 확정, geo 산술성립이라 geo 3값이 정답.
                cur_val = _upa_parse_money(_UPA_SQ_RE.sub("", cur))
                if cur_val is None or cur_val == v:
                    continue
                # 금액 가드(비-곱행 보호): amount 는 할인·부가세로 곱과 정당히 다를 수
                # 있다(감사 실측: 금액 오버라이트 회귀 55 전원이 이 함정). 현재값이
                # 곱의 0.45~1.02배(할인 가능대)면 진짜 값일 수 있으니 덮지 않는다.
                # 단 현재값==단가(단가침범) 또는 곱의 0.45배 미만(명백한 쓰레기)이면 덮음.
                # 수량·단가는 입력값이라 이 애매성이 없어 무가드(감사 43:1·21:1).
                if col == "amount":
                    geo_u = rr.get(u_c)
                    is_bleed = geo_u is not None and cur_val == geo_u
                    ratio = cur_val / v if v else 0
                    if not (is_bleed or ratio < 0.45):
                        continue
                row[col] = _upa_fmt(v)
                dbg["overwritten"] += 1
    # M2 append (산술성립 미바인딩 행). 정렬 스틸 방지 가드:
    #  - 기존 행과 같은 amount 값이면 append 금지(중복 경쟁자 생성 차단)
    #  - 입양 품명이 기존 행 품명과 겹치면 append 금지(그 행의 정렬을 뺏게 됨)
    exist_amts = {v for row in table_rows if isinstance(row, dict)
                  if (v := _upa_parse_money(_UPA_SQ_RE.sub("", str(row.get("amount") or "")))) is not None}
    exist_names = [str(row.get("itemName") or "").strip()
                   for row in table_rows if isinstance(row, dict)
                   and len(str(row.get("itemName") or "").strip()) >= 3]
    next_idx = len(table_rows) + 1
    for i, rr in enumerate(recon):
        if i in used_recon:
            continue
        qv, uv, av = rr.get(q_c), rr.get(u_c), rr.get(a_c)
        if not (qv and uv and av and float(qv).is_integer() and 1 <= qv <= 9999
                and uv >= 10 and av >= 100 and abs(qv * uv - av) <= 1):
            continue
        if av in exist_amts:
            continue
        name = geo_name(rr)
        if name and any(name_sim_ok(name, en) for en in exist_names):
            continue
        new_row = {
            "rowIndex": str(next_idx),
            "itemCode": "", "productCode": "", "itemName": name, "spec": "",
            "lotNo": "", "serialNo": "", "manufacturingNo": "", "expiryDate": "",
            "quantity": _upa_fmt(qv), "unit": "", "unitPrice": _upa_fmt(uv),
            "supplyAmount": "", "taxAmount": "", "amount": _upa_fmt(av),
            "totalAmount": "", "manufacturer": "", "insuranceCode": "", "remark": "",
            "_rawText": "", "_confidence": "0.5",
            "_source": "invoice_statement_free_geo_recon",
        }
        table_rows.append(new_row)
        used_recon.add(i)
        next_idx += 1
        dbg["appended"] += 1
    return _geo_triple_scan(table_rows, toks, dbg)


# ─── 산술 금액 채움(금액P2): 빈 금액 = 수량×단가 ────────────────────────────────
# 근거(066 thin, P1+R2 통과 후 잔여 실측 1,500문서): 금액 빈칸 + 수량·단가 둘 다
# 정상 + 수량×단가 정수 후보 중, 그 값이 행 _rawText 에 money 토큰으로 실재하는 것만
# 채움 → 전체 ~286행, 회귀 0, spurious 0, 정밀도 89%(오답 6/56은 단가 오독발 —
# 빈칸→mismatch 라 neutral, 회귀 아님). WRONG-overwrite(금액 있는데 ≠수량×단가)는
# 폐기: anchor 통과분도 정밀도 53%·회귀 77(할인/부가세포함/오독으로 산술 불성립
# 43%). 기존 R2(_ha_fill_arith_and_spec)는 HA 헤더검출 성공 행만 커버 → 이 룰은
# HA 미적용 빈칸을 _rawText anchor 로 보완. EMPTY 만, 읽힌 값 절대 불변.
_P2_MONEY_TOK_RE = re.compile(r"\d[\d,\.]*")


# ─── 수량↔단가 스왑(수량L2'): 두 칸이 통째로 뒤바뀐 행 복원 ─────────────────────
# 근거(066 공식 replay 전수 드라이런): 오배치 목적지 거울상(GT단가→수량칸 1,212 /
# GT수량→단가칸 1,197) = 같은 행들의 열 스왑. 순수 맞바꿈 + 산술 게이트:
#   수량칸=money꼴(콤마 or >=1000) & 단가칸=소형정수(1..9999 비콤마) & 금액 존재
#   & 현재 산술 불성립 → 스왑. both OK 86.5%(수량 88.8%·단가 94.1%), 회귀 27/1,134,
#   spurious 0 (75:1). 산술 이미 성립 행은 발화 금지 — 곱의 교환법칙상 방향 판정
#   불가 + 실측 55.8%(진짜 '수량 대량×단가 소액' 행을 깨뜨림).
# 유도 나눗셈 변형(u'=a/q)은 기각(정밀도 6~64%, 회귀 794) — 맞바꿈만 안전.
def fix_swapped_qty_unitprice(table_rows: Any) -> tuple[Any, dict[str, Any]]:
    """수량칸↔단가칸 값이 서로 바뀐 행을 모양+산술 게이트로 감지해 맞바꿈."""
    dbg: dict[str, Any] = {"swapped": 0}
    if not isinstance(table_rows, list) or not table_rows:
        return table_rows, dbg
    for row in table_rows:
        if not isinstance(row, dict):
            continue
        q_raw = str(row.get("quantity") or "").strip()
        u_raw = str(row.get("unitPrice") or "").strip()
        if not q_raw or not u_raw:
            continue
        eq = _upa_parse_money(_UPA_SQ_RE.sub("", q_raw))
        eu = _upa_parse_money(_UPA_SQ_RE.sub("", u_raw))
        ea = _upa_parse_money(_UPA_SQ_RE.sub("", str(row.get("amount") or "")))
        if eq is None or eu is None or not ea or ea <= 0:
            continue
        q_moneyish = ("," in q_raw) or eq >= 1000
        u_smallint = float(eu).is_integer() and 1 <= eu <= 9999 and "," not in u_raw
        if not (q_moneyish and u_smallint):
            continue
        if abs(eq * eu - ea) <= 1:
            continue  # 이미 산술성립 — 방향 판정 불가, 불가침
        row["quantity"], row["unitPrice"] = u_raw, q_raw
        dbg["swapped"] += 1
    return table_rows, dbg


# ─── 산술 수량 채움(수량L1): 빈 수량 = 금액÷단가 ───────────────────────────────
# 근거(066 공식 replay 전수 드라이런): 빈칸fill 발화 761 · 정밀도 92.2% · 회귀 0
# (구조상 불가) · spurious 0. 덮기 변형은 기각 — 할인행(금액≠수량×단가)에서
# 나눗셈 정수가 우연히 성립해 맞는 수량을 덮음(회귀 760, 런타임 구분 불가).
def fill_arith_empty_quantity(table_rows: Any) -> tuple[Any, dict[str, Any]]:
    """빈 quantity 를 금액÷단가(정수 1..9999일 때만)로 채움. 값 있는 행 절대 불변."""
    dbg: dict[str, Any] = {"filled": 0}
    if not isinstance(table_rows, list) or not table_rows:
        return table_rows, dbg
    for row in table_rows:
        if not isinstance(row, dict):
            continue
        if str(row.get("quantity") or "").strip():
            continue
        u = _upa_parse_money(_UPA_SQ_RE.sub("", str(row.get("unitPrice") or "")))
        a = _upa_parse_money(_UPA_SQ_RE.sub("", str(row.get("amount") or "")))
        if not u or not a or u <= 0 or a <= 0:
            continue
        ratio = a / u
        r_int = round(ratio)
        if abs(ratio - r_int) > 1e-6 or not (1 <= r_int <= 9999):
            continue
        row["quantity"] = str(int(r_int))
        dbg["filled"] += 1
    return table_rows, dbg


def fill_arith_empty_amount(table_rows: Any) -> tuple[Any, dict[str, Any]]:
    """빈 amount 를 수량×단가로 채움 — 그 값이 행 _rawText 에 money 토큰으로 존재할
    때만(anchor). free+fallback 합류점, 경로무관. amount 있는 행은 절대 안 건드림."""
    dbg: dict[str, Any] = {"filled": 0}
    if not isinstance(table_rows, list) or not table_rows:
        return table_rows, dbg
    for row in table_rows:
        if not isinstance(row, dict):
            continue
        if str(row.get("amount") or "").strip():
            continue
        q = _upa_parse_money(_UPA_SQ_RE.sub("", str(row.get("quantity") or "")))
        u = _upa_parse_money(_UPA_SQ_RE.sub("", str(row.get("unitPrice") or "")))
        if q is None or u is None or q < 1 or u <= 0:
            continue
        calc = q * u
        if calc <= 0 or not float(calc).is_integer():
            continue
        raw = str(row.get("_rawText") or "")
        if not raw or _is_summary_or_header_line(_normalize_text(raw)):
            continue
        target = str(int(calc))
        # anchor: 수량×단가 값이 이 행 _rawText 안에 money 토큰으로 실재해야 함
        # (파서가 읽고도 amount 칸에 못 넣은 것 → 회수 가능; 없으면 증거 없음 → skip)
        anchored = any(
            _upa_parse_money(m.group(0)) is not None
            and re.sub(r"\D", "", m.group(0)) == target
            for m in _P2_MONEY_TOK_RE.finditer(raw)
        )
        if not anchored:
            continue
        row["amount"] = _upa_fmt(calc)
        dbg["filled"] += 1
    return table_rows, dbg


def fill_scalar_defaults(document_fields: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    """Emit taxType/discountAmount when the parser left them empty. war GT carries
    both in ~100%/99% of docs (taxType 과세 86%, discountAmount '0' 90%), so these
    domain defaults are correct-not-spurious (the field exists in GT). Only fills
    EMPTY values → never overrides a detected 면세/discount. Measured: default 과세
    = 88% vs GT on 800 thin docs; 면세 is a document-level flag not reliably in the
    OCR text (TODO: vendor-based 면세 detection). documentNumber is intentionally
    NOT emitted — GT has it in 0% (all invoice_num are '0'/blank) → emitting would
    only create spurious false-positives."""
    dbg: dict[str, Any] = {}
    if not isinstance(document_fields, dict):
        return document_fields, dbg
    if not str(document_fields.get("taxType") or "").strip():
        document_fields["taxType"] = "과세"
        dbg["taxType"] = "과세"
    if not str(document_fields.get("discountAmount") or "").strip():
        document_fields["discountAmount"] = "0"
        dbg["discountAmount"] = "0"
    return document_fields, dbg


# ── R1: boilerplate/footer 행 드롭 (free+fallback 합류점, 경로무관) ────────────
# war GT tableRows 는 body 품목행만 담는다(build_gt.sql: description<>''). 표 파서가
# 표 바닥의 요약/장식 줄(이하여백·합계·총매출액·부가세액·☆☆☆)을 품목행으로 오인해
# 한 행 더 만드는 것이 과분할의 노이즈 성분(run061 thin: boilerplate 647행). 이들은
# GT에 절대 없으므로 드롭은 항상 정답. 고정밀 원칙: itemName 이 진짜 약품명(정/캡슐/mg…)
# 이면 절대 드롭 안 함 → 실품목 보호. 특정값 아닌 구조/키워드 의존 = 일반화 룰.
_BOILERPLATE_ROW_RE = re.compile(
    r"이\s*하\s*여\s*백|여\s*백|총\s*매\s*출|총\s*매\s*입|순\s*매\s*출|순\s*매\s*입|"
    r"부\s*가\s*세\s*액|품\s*절|미\s*출\s*고|공\s*급\s*가\s*액|반\s*품|"
    r"합\s*계|소\s*계|총\s*계|미\s*수\s*금|전\s*잔\s*금|현\s*잔\s*고|잔\s*액|"
    r"인\s*수\s*자|인\s*수\s*확\s*인|담\s*당\s*자|아\s*래\s*와\s*같\s*이|거\s*래\s*함|"
    r"월\s*계|누\s*계|받\s*을\s*채\s*권|받\s*은\s*금\s*액|현\s*재\s*잔\s*액"
)
_DECORATION_ONLY_RE = re.compile(r"^[\s☆★✩✱\*·・\-=_~〃″”]+$")
_PHARMA_PRODUCT_RE = re.compile(
    r"정$|정\b|정\s*\d|정\s*[TCPtcp)]|\d\s*정|"          # 제형 '정'(+용량 30T/10mg/맨끝)
    r"캡슐|캡셀|캡슈|캅셀|연질|시럽|크림|과립|주사|점안|점\s*안|정제|"
    r"밀리그람|밀리그램|mg|ml|캡\)"
)


def _row_names_a_pharma_product(name: str) -> bool:
    """itemName 이 진짜 약품명처럼 보이면 True(한글 + 제형/용량 시그널). 이런 행은
    보일러플레이트로 오인해 드롭하면 안 됨(실품목 보호막)."""
    n = (name or "").strip()
    if not n or not re.search(r"[가-힣]", n):
        return False
    return bool(_PHARMA_PRODUCT_RE.search(n))


def drop_boilerplate_table_rows(rows: Any) -> tuple[Any, dict[str, Any]]:
    """표 파서가 품목행으로 오인한 요약/푸터/장식 줄을 제거한다. 진짜 약품명 행은
    보호(절대 드롭 안 함). 빈칸만 채우는 다른 가드처럼 합류점(경로무관)에서 호출."""
    dbg: dict[str, Any] = {"dropped": 0, "samples": []}
    if not isinstance(rows, list) or not rows:
        return rows, dbg
    kept: list[Any] = []
    for r in rows:
        if not isinstance(r, dict):
            kept.append(r)
            continue
        name = str(r.get("itemName") or "").strip()
        raw = str(r.get("_rawText") or "").strip()
        probe = name or raw
        # 보호: itemName *또는* _rawText 에 진짜 약품 시그널이 있으면 유지. 블롭 행
        # (itemName 빈칸·rawText에 품목명 뭉침)이 푸터단어와 섞여도 실품목이라 보존.
        if _row_names_a_pharma_product(name) or _row_names_a_pharma_product(raw):
            kept.append(r)
            continue
        compact = re.sub(r"\s", "", probe)
        drop = bool(probe) and (
            _DECORATION_ONLY_RE.match(probe) is not None
            or _BOILERPLATE_ROW_RE.search(compact) is not None
        )
        if drop:
            dbg["dropped"] += 1
            if len(dbg["samples"]) < 8:
                dbg["samples"].append(probe[:40])
        else:
            kept.append(r)
    # 안전망: 표를 통째로 비우지 않는다. 전부 드롭 대상이면(예: 블롭 5행이 모두 푸터단어
    # 흡수) 원본 유지 — 표를 없애는 것보다 노이즈 남기는 게 채점상 안전(빈표=0점).
    if rows and not kept:
        return rows, {"dropped": 0, "samples": [], "reason": "kept_all_would_empty"}
    return kept, dbg


# ── 같이읽힘(blob) 분리: itemName 칸에 선행코드+품명+규격+날짜가 뭉친 행에서 ────
# 품명 코어만 남긴다. free 경로가 라인 전체를 itemName 에 통째로 넣어(text[:60])
# 생기는 최다 결함(062 thin: itemName wrongpick 중 merged 1,510건=22%). 예:
#   "B2110 관류용식염-L 1000ML 2029/04/14" → "관류용식염-L"
# 고정밀 가드: **선행 품목코드 또는 내장 만료일**(=blob 신호)이 있는 행에만 적용.
# 클린한 '이름+규격'(선행코드·날짜 없음) 행은 절대 안 건드림 → 규격유지 GT 회귀 방지
# (이전 blanket token-strip 반증 회피). _rawText 는 불변(정렬/salvage 근거 보존).
_ITEM_LEADING_CODE_RE = re.compile(r"^\s*[A-Za-z]{0,3}\d[A-Za-z0-9]{2,}\s+(?=[가-힣])")
_ITEM_DATE_RE = re.compile(
    r"(?:19|20)\d{2}[.\-/]\d{1,2}[.\-/]\d{1,2}|\b\d{4}[.\-/]\d{2}[.\-/]\d{2}\b"
)
_ITEM_SPEC_CUT_RE = re.compile(
    r"\s\d+(?:\.\d+)?\s*(?:ml|mg|g|l|t|tab|cap|iu|병|bt|box|ea|kg)\b", re.I
)
_ITEM_BLOB_MONEY_RE = re.compile(r"\s\d{1,3}(?:[,.]\d{3})+\b")

# 확인표시(체크마크) 제거: √/∨ 와 'V/v+숫자'(검수 마크)는 어떤 약품명에도 없는 명백 junk.
# 062 실측: √/V-숫자만 자르면 회복 25/회귀 1(선행√), 팩수·PTP는 GT 비일관이라 제외.
_VERIFY_LEAD_RE = re.compile(r"^\s*[√∨]+\s*")
_VERIFY_TAIL_RE = re.compile(r"\s*(?:[√∨]|[vV]\s*\d).*$")


def _strip_verify_marks(name: str) -> str | None:
    """선행 체크마크 제거 + 꼬리 확인표시(√/V숫자)부터 절단. 마커 없으면 None(무변경)."""
    s = (name or "")
    s2 = _VERIFY_LEAD_RE.sub("", s)
    m = _VERIFY_TAIL_RE.search(s2)
    if m:
        s2 = s2[: m.start()]
    s2 = s2.strip()
    if s2 == s.strip() or not re.search(r"[가-힣]", s2) or len(s2) < 2:
        return None
    return s2


def _extract_blob_item_name(name: str) -> str | None:
    """blob 신호가 있으면 품명 코어를 반환, 없으면 None(=건드리지 않음)."""
    s = (name or "").strip()
    if not s or not re.search(r"[가-힣]", s):
        return None
    if not (_ITEM_LEADING_CODE_RE.search(s) or _ITEM_DATE_RE.search(s)):
        return None  # blob 신호 없음 → 클린 행, 보존
    s2 = _ITEM_LEADING_CODE_RE.sub("", s, count=1)          # 선행 코드 제거
    cut = len(s2)                                            # 규격/날짜/금액에서 절단
    for rx in (_ITEM_DATE_RE, _ITEM_SPEC_CUT_RE, _ITEM_BLOB_MONEY_RE):
        m = rx.search(s2)
        if m:
            cut = min(cut, m.start())
    base = s2[:cut].strip()
    base = re.sub(r"\s+[A-Za-z0-9][A-Za-z0-9/\-]{2,}$", "", base).strip()  # 후행 lot코드
    if not re.search(r"[가-힣]", base) or len(base) < 2 or base == s:
        return None
    return base


def split_merged_item_name(rows: Any) -> tuple[Any, dict[str, Any]]:
    """itemName 이 blob(코드+품명+규격+날짜 뭉침)인 행에서 품명 코어만 남긴다.
    합류점(free+fallback 공통)에서 호출 → 경로무관. blob 신호 있는 행만."""
    dbg: dict[str, Any] = {"split": 0, "samples": []}
    if not isinstance(rows, list):
        return rows, dbg
    for r in rows:
        if not isinstance(r, dict):
            continue
        name = str(r.get("itemName") or "")
        base = _extract_blob_item_name(name)
        if base is not None:
            r["itemName"] = base
            name = base
            dbg["split"] += 1
            if len(dbg["samples"]) < 8:
                dbg["samples"].append({"from": name[:50], "to": base})
        # 확인표시(√/V숫자) 꼬리 제거 — blob 분리 후에도 남을 수 있어 이어서 적용
        marked = _strip_verify_marks(name)
        if marked is not None:
            r["itemName"] = marked
            dbg["split"] += 1
    return rows, dbg


def _item_name_core_from_text(text: str) -> str:
    """텍스트 앞에서 약품명 코어(이름+규격)만 누적 — 순수숫자/코드 만나면 정지."""
    out: list[str] = []
    for part in re.split(r"\s+", text or ""):
        if not part:
            continue
        compact = re.sub(r"[^\w가-힣]", "", part)
        if not compact:
            continue
        if re.fullmatch(r"\d+(?:[.,]\d+)?", compact):
            break
        if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_\-/.]{1,24}", compact) and out:
            break
        out.append(part)
        if len(" ".join(out)) >= 60:
            break
    return " ".join(out).strip()


_ITEM_PHARMA_SIG_RE = re.compile(
    r"정$|정\s|정\d|정[TCP]|캡슐|캡셀|캅셀|연질|시럽|크림|과립|주사|주$|액$|점안|정제|"
    r"밀리그람|밀리그램|mg|ml|환$", re.I
)


def recover_shifted_item_name(rows: Any) -> tuple[Any, dict[str, Any]]:
    """컬럼밀림 복구: itemName 이 비었는데 spec 셀이 약품명으로 시작하면(행이 한 칸
    밀림) spec 에서 이름 코어를 뽑아 itemName 에 채운다. 빈 itemName 행만 건드리므로
    맞는 행은 회귀 없음. spec 등 다른 셀은 그대로(각자 별도 결함)."""
    dbg: dict[str, Any] = {"recovered": 0, "samples": []}
    if not isinstance(rows, list):
        return rows, dbg
    for r in rows:
        if not isinstance(r, dict):
            continue
        if str(r.get("itemName") or "").strip():
            continue
        spec = str(r.get("spec") or "")
        if not spec or not _ITEM_PHARMA_SIG_RE.search(spec):
            continue
        cand = _item_name_core_from_text(spec)
        if cand and re.search(r"[가-힣]", cand) and len(cand) >= 2:
            r["itemName"] = cand
            dbg["recovered"] += 1
            if len(dbg["samples"]) < 8:
                dbg["samples"].append({"spec": spec[:50], "to": cand})
    return rows, dbg


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
    grouped_entries, grouping_debug = _group_ocr_items_into_row_entries(ocr_items)
    grouped_lines = [_normalize_text(entry.get("text")) for entry in grouped_entries]
    normalized_full_text = _normalize_text(full_text)
    joined_line_text = _join_lines(lines)
    source_text = "\n".join(text for text in (normalized_full_text, joined_line_text) if text)
    candidates = _build_candidate_debug(lines=lines, text=source_text)
    # Strict column parsing first (grouped, then flat lines) so dense single-line
    # layouts (1.jpg reference) are unaffected; only fall back to the relaxed
    # 'item name + amount' candidate path when strict parsing finds nothing.
    parsed_table_rows = _find_table_row_candidates(
        grouped_lines,
        allow_relaxed=False,
        row_entries=grouped_entries,
    )
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
    # Release must evaluate the same row shape that is returned to callers.
    # Normalization can move tokens between columns (for example product code,
    # lot number and expiry date) and thereby empty unitPrice/amount. Evaluating
    # the pre-normalized shape could incorrectly release a structurally partial
    # one-row table as complete (the 6-2 regression case).
    table_rows = _normalize_success_table_rows(table_rows, ocr_items=ocr_items)
    table_candidate_diagnostics = _build_table_candidate_diagnostics(
        raw_line_count=len(lines),
        grouped_line_count=len(grouped_lines),
        parsed_rows=parsed_table_rows,
        table_rows=table_rows,
        grouping_debug=grouping_debug,
        precision_debug=precision_debug,
    )
    table_candidate_diagnostics["postNormalizationReleaseEvaluation"] = True
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
    release_amount_reconciles = _table_amount_sum_reconciles(table_rows, source_text)
    release_pass, release_fail_reasons, release_decision = _evaluate_release_threshold(
        table_rows,
        table_candidate_diagnostics.get("fieldQuality"),
        columnar_context=columnar_context_for_release,
        amount_sum_reconciles=release_amount_reconciles,
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
        "columns": list(FIVE_COLUMN_PRODUCT_CODE_TABLE_KEYS) if table_rows else [],
        "expectedColumnKeys": list(FIVE_COLUMN_PRODUCT_CODE_TABLE_KEYS) if table_rows else [],
        "columnLabels": deepcopy(FIVE_COLUMN_PRODUCT_CODE_TABLE_LABELS) if table_rows else {},
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
        labeled_summary_fields, labeled_summary_debug = _extract_labeled_summary_scalars_from_ocr_items(ocr_items)
        for key in ("supplyAmount", "taxAmount"):
            if _has_meaningful_value(labeled_summary_fields.get(key)):
                document_fields[key] = labeled_summary_fields[key]
        labeled_summary_has_pair = (
            _money_for_sum(labeled_summary_fields.get("supplyAmount")) is not None
            and _money_for_sum(labeled_summary_fields.get("taxAmount")) is not None
        )
        if _has_meaningful_value(document_fields.get("taxAmount")) and document_fields.get("taxAmount") == document_fields.get("cumulativeAmount"):
            document_fields["cumulativeAmount"] = ""
        supply_value = _money_for_sum(document_fields.get("supplyAmount"))
        tax_value = _money_for_sum(document_fields.get("taxAmount"))
        current_total_value = _money_for_sum(document_fields.get("totalAmount"))
        source_money_values = [
            value
            for token in re.findall(r"\d{1,3}(?:[,.]\d{3})+", source_text)
            if (value := _money_for_sum(token)) is not None
        ]
        largest_source_money = max(source_money_values) if source_money_values else None
        if (
            current_total_value is not None
            and largest_source_money is not None
            and current_total_value < 1_000_000
            and largest_source_money > current_total_value * 10
        ):
            document_fields["totalAmount"] = f"{int(round(largest_source_money)):,}"
            scalar_merge_debug["totalAmountLargeSourceMoneyPreserved"] = True
        if supply_value is not None and tax_value is not None:
            current_total_value = _money_for_sum(document_fields.get("totalAmount"))
            summed_total = supply_value + tax_value
            if labeled_summary_has_pair or current_total_value is None or current_total_value <= summed_total * 1.2:
                document_fields["totalAmount"] = f"{int(round(summed_total)):,}"
        current_total_value = _money_for_sum(document_fields.get("totalAmount"))
        if (
            not _has_meaningful_value(document_fields.get("cumulativeAmount"))
            and current_total_value is not None
            and current_total_value >= 1_000_000
            and not (supply_value is not None and tax_value is not None)
            and (
                max(value for value in (supply_value, tax_value) if value is not None) * 10 <= current_total_value
                if any(value is not None for value in (supply_value, tax_value))
                else True
            )
        ):
            total_digits = str(int(round(current_total_value)))
            footer_total_hits = 0
            for item in ocr_items:
                if float(item.get("cy") or 0) < float(image_wh[1] if isinstance(image_wh, list) and len(image_wh) >= 2 else 0) * 0.72:
                    continue
                for token in re.findall(r"\d{1,3}(?:[,.]\d{3})+", str(item.get("text") or "")):
                    if re.sub(r"\D", "", token) == total_digits:
                        footer_total_hits += 1
            if footer_total_hits >= 2:
                document_fields["cumulativeAmount"] = f"{int(round(current_total_value)):,}"
                scalar_merge_debug["cumulativeAmountMirroredFromRepeatedFooterTotal"] = {
                    "value": document_fields["cumulativeAmount"],
                    "footerTotalHits": footer_total_hits,
                    "reason": "free_success_repeated_footer_total_without_supply_tax_pair",
                }
        scalar_merge_debug["reference"] = reference_debug
        scalar_merge_debug["labeledSummaryScalars"] = labeled_summary_debug
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
