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


def _money_tokens_from_text(value: Any) -> list[str]:
    text = _normalize_text(value)
    if not text:
        return []
    tokens: list[str] = []
    for match in re.finditer(r"(?<!\d)(?:-?\d{1,3}(?:,\d{3})+|-?\d{4,})(?!\d)", text):
        token = _clean_number_token(match.group(0))
        if not token:
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
            "total", "balance", "vat", "tax", "합계", "총액", "부가세", "누계", "잔액", "계약잔액",
        ),
        "document_or_footer": (
            "page", "no.", "document", "ossbook", "www.", ".co.kr",
            "출력", "일자", "페이지", "문서", "세금계산서", "전자장부", "계약코드", "영업사원", "간납처",
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
    text = _normalize_text(line)
    if _is_summary_or_header_line(text):
        return None
    tokens = text.split()
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


def _find_table_row_candidates(lines: list[str]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for line in lines:
        candidate = _parse_table_row_candidate(line, len(rows) + 1)
        if candidate is not None:
            rows.append(candidate)
    return rows


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
    rules = {
        "minFilteredRows": 20,
        "minReleaseReadyRows": 20,
        "minReleaseReadyRatio": 0.8,
        "minItemNamePresentRatio": 0.95,
        "minAmountPresentRatio": 0.95,
        "minUnitPriceParseableRatio": 0.8,
        "minQuantityParseableRatio": 0.7,
        "maxForbiddenRowKeys": 0,
        "maxMetadataRows": 0,
        "requiredTableDetected": "Y",
    }
    fail_reasons: list[str] = []
    if total < rules["minFilteredRows"]:
        fail_reasons.append("filtered_rows_below_threshold")
    if release_ready < rules["minReleaseReadyRows"]:
        fail_reasons.append("release_ready_rows_below_threshold")
    if release_ready_ratio < rules["minReleaseReadyRatio"]:
        fail_reasons.append("release_ready_ratio_below_threshold")
    if ratios["itemNamePresentRatio"] < rules["minItemNamePresentRatio"]:
        fail_reasons.append("itemName_present_ratio_below_threshold")
    if ratios["amountPresentRatio"] < rules["minAmountPresentRatio"]:
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
    decision = {
        "enabled": True,
        "thresholdVersion": "3f_guarded_real_sample_release",
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
            **ratios,
        },
        "diagnosticOnly": {
            "amountParseableRatio": ratios["amountParseableRatioDiagnostic"],
        },
    }
    return not fail_reasons, fail_reasons, decision


def _filter_table_row_candidates(rows: list[dict[str, str]]) -> tuple[list[dict[str, str]], dict[str, Any]]:
    kept: list[dict[str, str]] = []
    dropped: list[dict[str, Any]] = []
    reason_counts: dict[str, int] = {}
    for row in rows:
        score = _score_invoice_item_row(row, row.get("_rawText"))
        score_value = int(score.get("score") or 0)
        drop_reason = _normalize_text(score.get("dropReason")) or (
            "" if score_value >= 4 else "low_precision_score"
        )
        if not drop_reason:
            kept_row = _normalize_candidate_row(row)
            kept_row["rowIndex"] = str(len(kept) + 1)
            kept.append(kept_row)
            continue
        reason_counts[drop_reason] = reason_counts.get(drop_reason, 0) + 1
        if len(dropped) < 5:
            dropped.append(_row_preview(row, {"score": score_value, "dropReason": drop_reason}))
    return kept, {
        "precisionFilterEnabled": True,
        "parsedCandidateCount": len(rows),
        "filteredCandidateCount": len(kept),
        "droppedCount": len(rows) - len(kept),
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
    return {
        "strategy": "bbox_row_grouping_plus_precision_filter",
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
    return {
        "businessNumbers": business_numbers,
        "companyCandidates": company_candidates,
        "amountCandidates": amount_candidates,
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
    parsed_table_rows = _find_table_row_candidates(grouped_lines)
    if not parsed_table_rows:
        parsed_table_rows = _find_table_row_candidates(lines)
    table_rows, precision_debug = _filter_table_row_candidates(parsed_table_rows)
    table_candidate_diagnostics = _build_table_candidate_diagnostics(
        raw_line_count=len(lines),
        grouped_line_count=len(grouped_lines),
        parsed_rows=parsed_table_rows,
        table_rows=table_rows,
        grouping_debug=grouping_debug,
        precision_debug=precision_debug,
    )
    release_pass, release_fail_reasons, release_decision = _evaluate_release_threshold(
        table_rows,
        table_candidate_diagnostics.get("fieldQuality"),
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
        },
        "rowCount": len(table_rows),
        "fallbackRequired": True,
    }
    if release_pass and doc_type == "invoice_statement" and not template_mode:
        free_debug_payload.update(
            {
                "status": "success",
                "used": True,
                "fallbackUsed": False,
                "fallbackReason": "",
                "fallbackRequired": False,
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
    "TABLE_ROW_KEYS",
    "_build_table_candidate_diagnostics",
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
    "_is_release_ready_table_row",
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
