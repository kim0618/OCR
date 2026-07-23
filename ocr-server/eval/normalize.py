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
    "supplierCompany": "company", "supplierRepresentative": "text", "supplierAddress": "address",
    "buyerCompany": "company", "buyerRepresentative": "text", "buyerAddress": "address",
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
    "itemName": "name", "itemNameMaster": "master_name", "spec": "spec",
    # itemNameLearnA/B = learndata 아이템 정식명 측정컬럼 → itemNameMaster 와 동일 정규화.
    "itemNameLearnA": "master_name", "itemNameLearnB": "master_name",
    "productCode": "code", "lotNo": "code",
    "expiryDate": "date",
    "quantity": "qty", "unitPrice": "amount", "amount": "amount",
    # --- thin/war new row column ---
    "manufacturingNo": "code", "serialNo": "code",
    # itemCode 계열: itemCode 는 _infer_type 로도 'code'(끝이 code)지만, 측정컬럼
    # itemCodeLearnA/B 는 끝이 'code' 아님 → 'text' 로 잘못 추론됨. 명시해서 itemCode 와
    # 동일 정규화(norm_code: 비-alnum 제거+대문자) 보장 = OFF/learndata 공정 비교.
    "itemCode": "code", "itemCodeLearnA": "code", "itemCodeLearnB": "code",
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


_MASTER_NAME_ANNOTATION = re.compile(r"\([^)]*\)")


def norm_master_name(v) -> str:
    """Neutralize war-master parenthetical annotations on both GT and output.

    This is intentionally separate from ``norm_name``: raw OCR item names can
    contain meaningful parenthetical text, while ``itemNameMaster`` is the
    canonical display column whose parentheses are lifecycle/packaging/admin
    metadata in the war master.
    """
    s = unicodedata.normalize("NFC", _s(v))
    s = _MASTER_NAME_ANNOTATION.sub("", s)
    s = _NON_ALNUM.sub("", s)
    return s.casefold()


def norm_spec(v) -> str:
    # 2026-07-21: 규격(spec)도 공백·괄호·마침표·체크마크가 비의미(포장/용량 서술자).
    # war GT('100 C','(병)30T','/30Tab.')와 파서 출력('100C','병)30T','/30Tab')·검수마크
    # 붙은 OCR('30T √')이 같은 규격인데 text 정규화는 내부공백/구두점을 남겨 오불일치.
    # 066 실측: 전체 비-alnum 제거 시 mismatch->match +1,132(thin), 회귀 0, study 무변화,
    # 오병합 0(전부 순수 공백/구두점/junk마크 차이). norm_name/address 와 동일 방식.
    s = unicodedata.normalize("NFC", _s(v))
    s = _NON_ALNUM.sub("", s)
    return s.casefold()


def norm_index(v) -> str:
    s = _DIGITS.sub("", _s(v))
    return str(int(s)) if s else ""


# 법인격/구분 표기(사람이 같은 회사로 보는 차이): '㈜','주식회사','(주)','(전)' 등.
# 회사명 본문 글자는 건드리지 않고 이 표기만 중립화 → 마스터 정식명('부광약품(전)')과
# GT raw('부광약품(주)')·raw 읽기('대한약품' vs 마스터 '대한약품(주)')를 동일 취급.
_CORP_WORD = re.compile(r"㈜|주식회사|유한회사|합자회사|합명회사|의료법인|재단법인|사단법인|학교법인")
_CORP_PAREN = re.compile(r"\((?:주|전|유|재|사|합|자|명|본|지|국|영|의|학)\)")


def norm_company(v) -> str:
    s = unicodedata.normalize("NFC", _s(v))
    s = _CORP_WORD.sub("", s)
    s = _CORP_PAREN.sub("", s)
    s = _NON_ALNUM.sub("", s)   # 나머지 공백/구두점/잔여 괄호 제거 (norm_name/address 와 동일)
    return s.casefold()


_NORMALIZERS = {
    "text": norm_text, "amount": norm_amount, "qty": norm_qty,
    "bizno": norm_bizno, "date": norm_date, "code": norm_code, "index": norm_index,
    "address": norm_address, "name": norm_name, "master_name": norm_master_name,
    "company": norm_company,
    "spec": norm_spec,
}


def normalize_field(label: str, value) -> str:
    return _NORMALIZERS[FIELD_TYPE.get(label) or _infer_type(label)](value)


def normalize_cell(row_key: str, value) -> str:
    return _NORMALIZERS[ROW_KEY_TYPE.get(row_key) or _infer_type(row_key)](value)


def is_empty(value) -> bool:
    return _s(value).strip() == ""
