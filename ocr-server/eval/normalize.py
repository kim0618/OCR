"""normalize — FROZEN value normalization for comparison (Phase 3 lock).

Principle: neutralize only *representation* differences that a human would call
"the same value" (thousands separators, hyphens, whitespace, date separators).
NEVER repair OCR character errors — those are the signal we measure.

Applied identically to GT and extracted values before equality compare.
Field type is resolved by key via FIELD_TYPE / ROW_KEY_TYPE.
"""

from __future__ import annotations

import re
import unicodedata

# --- field key -> type -------------------------------------------------------
FIELD_TYPE = {
    "supplierCompany": "text", "supplierRepresentative": "text", "supplierAddress": "address",
    "buyerCompany": "text", "buyerRepresentative": "text", "buyerAddress": "address",
    "supplierBizNumber": "bizno", "buyerBizNumber": "bizno",
    "issueDate": "date",
    "supplyAmount": "amount", "taxAmount": "amount",
    "totalAmount": "amount", "cumulativeAmount": "amount",
    "totalQuantity": "qty",
    # --- thin/war new-3 fields (§6.6) ---
    "discountAmount": "amount",     # a money sum
    "documentNumber": "code",       # an identifier, not a sum (alnum-collapsed)
    "taxType": "text",              # 과세/영세/면세 etc.
}
ROW_KEY_TYPE = {
    "rowIndex": "index",
    "itemName": "name", "spec": "text",
    "productCode": "code", "lotNo": "code",
    "expiryDate": "date",
    "quantity": "qty", "unitPrice": "amount", "amount": "amount",
    # --- thin/war new row column ---
    "manufacturingNo": "code", "serialNo": "code",
}


def _infer_type(key: str) -> str:
    """Name-heuristic fallback (➍) for keys absent from the explicit maps.

    Lets future ETL/war columns normalize correctly without a code change. Never
    fires for the rich/thin contract keys (all are mapped explicitly above), so
    it cannot shift existing behavior — it is purely additive for unknown keys.
        *Amount / *Price -> amount
        *Date            -> date
        *Num / *Code / *No -> code   (incl. manufacturingNo / serialNo)
        else             -> text
    """
    low = key.lower()
    if low.endswith(("amount", "price")):
        return "amount"
    if low.endswith("date"):
        return "date"
    if low.endswith(("num", "code", "no")):
        return "code"
    return "text"

_DIGITS = re.compile(r"\D+")
_NON_ALNUM = re.compile(r"[^0-9A-Za-z가-힣]+")
_WS = re.compile(r"\s+")


def _s(v) -> str:
    return "" if v is None else str(v)


def norm_text(v) -> str:
    s = unicodedata.normalize("NFC", _s(v)).strip()
    s = _WS.sub(" ", s)
    return s.casefold()


def norm_amount(v) -> str:
    # digits only; drop commas, dots, spaces, currency. Integer-valued invoices.
    return _DIGITS.sub("", _s(v))


def norm_qty(v) -> str:
    return _DIGITS.sub("", _s(v))


def norm_bizno(v) -> str:
    return _DIGITS.sub("", _s(v))


def norm_date(v) -> str:
    return _DIGITS.sub("", _s(v))


def norm_code(v) -> str:
    s = unicodedata.normalize("NFC", _s(v))
    s = _NON_ALNUM.sub("", s)
    return s.upper()


def norm_address(v) -> str:
    # P3-b: 주소는 띄어쓰기·괄호·쉼표가 비의미(가변) — 같은 주소를 사람은 동일하다고 본다.
    # 공백/괄호/구두점 전부 제거하고 alnum+한글만 비교(글자 오류는 그대로 신호로 남김).
    s = unicodedata.normalize("NFC", _s(v))
    s = _NON_ALNUM.sub("", s)
    return s.casefold()


def norm_name(v) -> str:
    # 2026-07-06: 품명(itemName)도 공백/괄호가 비의미(GT 포맷 비일관: '생리식염 - 신형백'
    # vs '생리식염-신형백', '휴드론 정' vs '휴드론정'). 062 실측 = 공백만 다른 spurious
    # 결함 1,331건(itemName 결함의 20%). 주소식으로 공백/괄호 제거, 글자오류는 신호로 유지.
    # (이전 '품명은 공백 의미 있을 수 있어 text 유지' 가정을 데이터로 반증·정정.)
    s = unicodedata.normalize("NFC", _s(v))
    s = _NON_ALNUM.sub("", s)
    return s.casefold()


def norm_index(v) -> str:
    s = _DIGITS.sub("", _s(v))
    return str(int(s)) if s else ""


_NORMALIZERS = {
    "text": norm_text, "amount": norm_amount, "qty": norm_qty,
    "bizno": norm_bizno, "date": norm_date, "code": norm_code, "index": norm_index,
    "address": norm_address, "name": norm_name,
}


def normalize_field(label: str, value) -> str:
    return _NORMALIZERS[FIELD_TYPE.get(label) or _infer_type(label)](value)


def normalize_cell(row_key: str, value) -> str:
    return _NORMALIZERS[ROW_KEY_TYPE.get(row_key) or _infer_type(row_key)](value)


def is_empty(value) -> bool:
    return _s(value).strip() == ""
