import re
from dataclasses import dataclass
from typing import Any


_BIZ_RE = re.compile(r"(?<!\d)([0-9OIlSB]{3})[-\s.]?([0-9OIlSB]{2})[-\s.]?([0-9OIlSB]{5})(?!\d)")
_AMOUNT_RE = re.compile(r"(?<!\d)([0-9OIlSB]{1,3}(?:[,.][0-9OIlSB]{3})+|[0-9OIlSB]{4,})(?!\d)")
_PHONE_RE = re.compile(r"(?:TEL|Tel|tel|\uc804\ud654)?[:\s(]*(?:0\d{1,2})[-)\s]?\d{3,4}[-\s]?\d{4}")

_COMPANY_ANCHOR_RE = re.compile(
    r"\uc0c1\s*\ud638(?:\uba85)?|\uc0c1\uc810\uba85|\uac70\ub798\ucc98\uba85|"
    r"\ub0a9\ud488\ucc98|\ud310\ub9e4\uc790|\uacf5\uae09\uc790|\ubc95\uc778\uba85"
)
_REP_ANCHOR_RE = re.compile(r"\uc131\s*\uba85|\ub300\ud45c\uc790(?:\uba85)?")
_ADDR_ANCHOR_RE = re.compile(r"\uc8fc\s*\uc18c|\uc18c\uc7ac\uc9c0|\uc0ac\uc5c5\uc7a5")
_BUYER_PARTY_LABEL_RE = re.compile(r"\uacf5\s*\uae09\s*\ubc1b|\uacf5.{0,4}\ub294\s*\uc790|\ubc1b\s*\ub294\s*\uc790|\uac70\s*\ub798\s*\ucc98|\uadc0\s*\ud558|\uc218\s*\uc2e0")
_SUPPLIER_PARTY_LABEL_RE = re.compile(r"\uacf5\s*\uae09\s*\uc790|\ubc1c\s*\ud589\s*\ucc98|\ub9e4\s*\ucd9c\s*\ucc98")
_ADDRESS_TOKEN_RE = re.compile(
    r"\uc11c\uc6b8|\uacbd\uae30|\uc778\ucc9c|\ubd80\uc0b0|\ub300\uad6c|\uad11\uc8fc|\ub300\uc804|"
    r"\uc6b8\uc0b0|\uc138\uc885|\uac15\uc6d0|\ucda9\ubd81|\ucda9\ub0a8|\uc804\ubd81|\uc804\ub0a8|"
    r"\uacbd\ubd81|\uacbd\ub0a8|\uc81c\uc8fc|[\uac00-\ud7a3]{1,10}(?:\uc2dc|\uad70|\uad6c|\ub3d9|\uc74d|\uba74|\ub9ac)|"
    r"[\uac00-\ud7a3]{1,16}(?:\ub85c|\uae38|\ubc88\uae38)"
)
_DATE_RE = re.compile(
    r"(?<!\d)(\d{4})\s*\ub144\s*(\d{1,2})\s*\uc6d4\s*(\d{1,2})\s*\uc77c"
    r"|(?<!\d)(\d{4})[.\-/]\s*(\d{1,2})[.\-/]\s*(\d{1,2})(?!\d)"
    r"|(?<!\d)(\d{2})[.\-/]\s*(\d{1,2})[.\-/]\s*(\d{1,2})(?!\d)"
)
_SUPPLY_AMOUNT_ANCHOR_RE = re.compile(
    r"\uacf5\s*\uae09\s*\uac00\s*\uc561|\uacf5\s*\uae09\s*\uc561|\uacf5\s*\uae09\s*\uae08\s*\uc561|"
    r"\uacf5\s*\uae09\s*\ub300\s*\uac00|\uacf5\s*\uae09\s*\uac00(?![\uac00-\ud7a3])"
)
_TAX_AMOUNT_ANCHOR_RE = re.compile(
    r"\uc138\s*\uc561|\uc0c8\s*\uc561|\uc138\s*\uc775|\uc138\s*\uc545|"
    r"\ubd80\s*\uac00\s*\uc138|\ubd80\s*\uac00\s*\uc11c|\ubd80\s*\uac00\s*\uac00\s*\uce58\s*\uc138|"
    r"\bVAT\b|\bV\.A\.T\b",
    re.I,
)
_TOTAL_AMOUNT_ANCHOR_RE = re.compile(
    r"\ud569\s*\uacc4|\ucd1d\s*\uacc4|\ucd1d\s*\ud569\s*\uacc4|\ucd1d\s*\uae08\s*\uc561|"
    r"\ucd1d\s*\uacb0\s*\uc81c\s*\uc561|\uacf5\s*\uae09\s*\ub300\s*\uac00|"
    r"\uccad\s*\uad6c\s*\uae08\s*\uc561|\uacb0\s*\uc81c\s*\uae08\s*\uc561|\bTOTAL\b",
    re.I,
)
_TABLE_SUMMARY_RE = re.compile(
    r"\uacf5\s*\uae09\s*\uae08\s*\uc561|\uacf5\s*\uae09\s*\uac00\s*\uc561|\uacf5\s*\uae09\s*\uc561|"
    r"\uacf5\s*\uae09\s*\uac00\ub825|\uacf5\s*\uae09\s*\ub300\s*\uac00|\uc138\s*\uc561|\uc0c8\s*\uc561|"
    r"\uc138\s*\uc775|\uc138\s*\uc545|\ubd80\s*\uac00\s*\uc138|\ubd80\s*\uac00\s*\uc11c|VAT|"
    r"\ud569\s*\uacc4|\ud568\s*\uacc4|\ud569\s*\uacc4\s*\uae08\s*\uc561|\ucd1d\s*\uacb0\s*\uc81c\s*\uc561|"
    r"\uccad\s*\uad6c\s*\uae08\s*\uc561|\uacb0\s*\uc81c\s*\uae08\s*\uc561|\uc794\s*\uc561|\ub204\s*\uacc4|"
    r"\uc778\uc218\s*\ud655\uc778|\uc778\uc218\uc790|\ucc3d\s*\uace0|Page|Fa:|\ud398\uc774\uc9c0|TOTAL",
    re.I,
)
_TABLE_HEADER_TOKEN_RE = re.compile(
    r"\ud488\s*\uba85|\ud488\s*\ubaa9|\uaddc\s*\uaca9|\uc218\s*\ub7c9|\ub2e8\s*\uac00|"
    r"\uacf5\uae09\s*\uac00\uc561|\uc138\s*\uc561|\ud569\s*\uacc4|\uae08\s*\uc561|"
    r"\ube44\s*\uace0|\uc81c\uc870\s*\ubc88\ud638|\uc720\ud6a8\s*\uae30\uac04|\ubcf4\ud5d8\s*\ucf54\ub4dc"
)
_COMPANY_HINT_RE = re.compile(
    r"\uc8fc\uc2dd\ud68c\uc0ac|\uc8fc\uc2dd\s*\ud76c\uc0ac|\(\s*\uc8fc\s*\)?|\uc8fc\)|\uc720\)|"
    r"\uc57d\s*\ud488|\uc784\ud50c\ub780\ud2b8|\ud68c\uc0ac|\uc9c0\uc810|\uc608\uc77c\uc120"
)
_COMPANY_REJECT_RE = re.compile(
    r"\uacf5\uae09\uae08\uc561|\uacf5\uae09\uac00\uc561|\uc18c\ube44\uc790\uae08\uc561|\ud569\uacc4|"
    r"\uc794\uc561|\ud488\ubaa9|\ud488\uba85|\ucf54\ub4dc|\uac70\ub798\uc77c\uc790|\uc8fc\ubb38\uc77c\uc790|"
    r"\uc601\uc5c5\uc9c0\uc810|\uc601\uc5c5\uc0ac\uc6d0|\uc57d\uc815|\ucc44\uad8c|\uc774\ud558\uc5ec\ubc31|"
    r"\ucc3d\uace0|FAX|Page|Fa:"
)
_ITEM_NAME_HINT_RE = re.compile(r"\uc815|\ucea1\uc290|\ucea1\uc2ac|\ud06c\ub9bc|\uc561|mg|ml|g|T|C", re.I)
_HEADER_LABEL_RE = re.compile(
    r"\uac70\ub798\uba85\uc138\uc11c?|\uac70\ub798\uba85\uc138\ud45c|\uacf5\uae09\uc790|\uacf5\uae09\ubc1b\ub294\uc790|"
    r"\uc0ac\uc5c5\uc790|\ub4f1\ub85d\ubc88\ud638|\ub300\ud45c\uc790|\uc8fc\uc18c|\uc18c\uc7ac\uc9c0|"
    r"\uc791\uc131|\ub144|\uc6d4|\uc77c|\uadc0\ud558|\ubc95\uc778\uba85|\uc0c1\ud638|\uc131\uba85"
)
_ADDRESS_HINT_RE = re.compile(
    r"\uc11c\uc6b8|\uacbd\uae30|\uc778\ucc9c|\ubd80\uc0b0|\ub300\uad6c|\uad11\uc8fc|\ub300\uc804|"
    r"\uc6b8\uc0b0|\uc138\uc885|\uac15\uc6d0|\ucda9\ubd81|\ucda9\ub0a8|\uc804\ubd81|\uc804\ub0a8|"
    r"\uacbd\ubd81|\uacbd\ub0a8|\uc81c\uc8fc"
)
_HANGUL_RE = re.compile(r"[\uac00-\ud7a3]")
_ASCII_WORD_RE = re.compile(r"[A-Za-z]{2,}")
_TABLE_BUSINESS_CONTACT_RE = re.compile(
    r"\uc0ac\s*\uc5c5\s*\uc790\s*\ubc88\s*\ud638|\ub4f1\s*\ub85d\s*\ubc88\s*\ud638|"
    r"\ub300\s*\ud45c\s*\uc790|\uc8fc\s*\uc18c|\uc804\s*\ud654|\uc774\s*\uba54\s*\uc77c|"
    r"\uc5c5\s*\ud0dc|\uc885\s*\ubaa9|\uacf5\s*\uae09\s*\uc790|\uacf5\s*\uae09\s*\ubc1b\s*\ub294\s*\uc790|"
    r"\uac70\s*\ub798\s*\ucc98|\uadc0\s*\ud558|\uc0ac\s*\uc5c5\s*\uc7a5|\uacc4\s*\uc88c\s*\ubc88\s*\ud638|"
    r"\uc601\s*\uc5c5\s*\uc9c0\s*\uc810|\uc601\s*\uc5c5\s*\uc0ac\s*\uc6d0|\ub2f4\s*\ub2f9\s*\uc790|"
    r"\uc0c1\s*\ud638|\ubc95\s*\uc778\s*\uba85|"
    r"\uc5f0\s*\ub77d\s*\ucc98|TEL|FAX|E-?mail|Page|Fa:",
    re.I,
)
_TABLE_SUMMARY_STRONG_RE = re.compile(
    r"\ud569\s*\uacc4|\ucd1d\s*\uacc4|\ucd1d\s*\ud569\s*\uacc4|\uacf5\s*\uae09\s*\uac00\s*\uc561|"
    r"\uacf5\s*\uae09\s*\uae08\s*\uc561|\uacf5\s*\uae09\s*\ub300\s*\uac00|\uc138\s*\uc561|"
    r"\ubd80\s*\uac00\s*\uc138|\ubd80\s*\uac00\s*\uac00\s*\uce58\s*\uc138|\uc138\s*\uc5ed|\uccad\s*\uad6c\s*\uae08\s*\uc561|"
    r"\uacb0\s*\uc81c\s*\uae08\s*\uc561|\ucd1d\s*\uacb0\s*\uc81c\s*\uc561|\uc794\s*\uc561|\ub204\s*\uacc4|"
    r"\ubbf8\s*\uc218|\uc778\s*\uc218\s*\ud655\s*\uc778|\ub2f4\s*\ub2f9\s*\uc790|TOTAL",
    re.I,
)
_TABLE_HEADER_STRONG_RE = re.compile(
    r"\ud488\s*\uba85|\ud488\s*\ubaa9|\ud488\s*\ubaa9\s*\uba85|\uaddc\s*\uaca9|\uc218\s*\ub7c9|"
    r"\ub2e8\s*\uc704|\ub2e8\s*\uac00|\uacf5\s*\uae09\s*\uac00\s*\uc561|\uacf5\s*\uae09\s*\uae08\s*\uc561|"
    r"\uae08\s*\uc561|\uc138\s*\uc561|\ubd80\s*\uac00\s*\uc138|\ud569\s*\uacc4|\ube44\s*\uace0|"
    r"\uc81c\s*\uc870\s*\ubc88\s*\ud638|\uc720\s*\ud6a8\s*\uae30\s*\uac04|\ubcf4\s*\ud5d8\s*\ucf54\s*\ub4dc|"
    r"\ud488\s*\ubaa9\s*\ucf54\s*\ub4dc",
    re.I,
)
_TABLE_STANDALONE_LABEL_RE = re.compile(
    r"^(?:\ud488\s*\uba85|\ud488\s*\ubaa9|\ud488\s*\ubaa9\s*\uba85|\uaddc\s*\uaca9|\uc218\s*\ub7c9|"
    r"\ub2e8\s*\uc704|\ub2e8\s*\uac00|\uacf5\s*\uae09\s*\uac00\s*\uc561|\uacf5\s*\uae09\s*\uae08\s*\uc561|"
    r"\uae08\s*\uc561|\uc138\s*\uc561|\ubd80\s*\uac00\s*\uc138|\ud569\s*\uacc4|\ube44\s*\uace0|"
    r"\uc0c1\s*\ud638|\uc8fc\s*\uc18c|\uc131\s*\uba85|\uc0ac\s*\uc5c5\s*\uc790\s*\ubc88\s*\ud638|"
    r"\uac70\s*\ub798\s*\uc77c\s*\uc790|\uc8fc\s*\ubb38\s*\uc77c\s*\uc790|\uc5f0\s*\ub77d\s*\ucc98|"
    r"\ucc3d\s*\uace0|\uc601\s*\uc5c5\s*\uc0ac\s*\uc6d0|\uc601\s*\uc5c5\s*\uc9c0\s*\uc810)$",
    re.I,
)
_SPEC_ONLY_RE = re.compile(r"^\d+(?:[.,]\d+)?(?:mg|ml|g|kg|t|tab|cap|caps?|c|\uc815|\ucea1\uc290|\ud3ec|\ubcd1|box|ea|p|dose|mI)(?:\([^)]+\))?$", re.I)


@dataclass
class OcrLine:
    pts: list
    text: str
    confidence: float
    x: float
    y: float
    w: float
    h: float
    cx: float
    cy: float


@dataclass
class SummaryAmountCandidate:
    value: str
    numeric: int
    row_idx: int
    cy: float
    x: float
    text: str
    context: str
    supply_anchor: bool
    tax_anchor: bool
    total_anchor: bool


def _line_from_raw(raw: tuple) -> OcrLine | None:
    pts, text, confidence = raw
    text = (text or "").strip()
    if not text:
        return None
    xs = [float(p[0]) for p in pts]
    ys = [float(p[1]) for p in pts]
    x = min(xs)
    y = min(ys)
    w = max(xs) - x
    h = max(ys) - y
    if w <= 0 or h <= 0:
        return None
    return OcrLine(pts, text, float(confidence), x, y, w, h, x + w / 2, y + h / 2)


def _canonical_digits(text: str) -> str:
    return (
        (text or "")
        .replace("O", "0")
        .replace("o", "0")
        .replace("I", "1")
        .replace("l", "1")
        .replace("S", "5")
        .replace("B", "8")
    )


def _format_biz(text: str) -> str:
    match = _BIZ_RE.search(_canonical_digits(text))
    if not match:
        return ""
    return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"


def _amount_values(text: str) -> list[str]:
    values: list[str] = []
    for match in _AMOUNT_RE.finditer(_canonical_digits(text)):
        digits = re.sub(r"\D", "", match.group(1))
        if not digits or re.fullmatch(r"(?:19|20)\d{6}", digits):
            continue
        value = int(digits)
        if 100 <= value <= 1_000_000_000:
            values.append(f"{value:,}")
    return values


def _amount_value(text: str) -> str:
    values = _amount_values(text)
    return values[-1] if values else ""


def _clean_value(value: str) -> str:
    value = (value or "").strip()
    value = re.sub(r"^[\s:：;|ㆍ.\-()\[\]]+", "", value)
    value = re.sub(r"[\s:：;|ㆍ.\-()\[\]]+$", "", value)
    return value.strip()


def _strip_inline_noise(text: str) -> str:
    value = _PHONE_RE.sub("", text or "")
    value = _BIZ_RE.sub("", _canonical_digits(value))
    value = re.sub(r"\d{4}[./-]\d{1,2}[./-]\d{1,2}.*$", "", value)
    return _clean_value(value)


def _clean_company_candidate(text: str) -> str:
    value = _strip_inline_noise(text)
    value = re.sub(
        r"^(?:\uc0c1\s*\ud638(?:\uba85)?|\ubc95\uc778\uba85|\uac70\ub798\ucc98\uba85|\ub0a9\ud488\ucc98|"
        r"\ud310\ub9e4\uc790|\uacf5\uae09\uc790)\s*[:：]?",
        "",
        value,
    )
    value = _clean_value(value)
    hint = _COMPANY_HINT_RE.search(value)
    if hint:
        if hint.group(0).startswith("\uc8fc\uc2dd\ud68c\uc0ac"):
            m = re.search(r"\uc8fc\uc2dd\ud68c\uc0ac[\uac00-\ud7a3A-Za-z0-9()&.\s]{1,24}", value)
            if m:
                value = m.group(0)
        elif "(\uc8fc" in re.sub(r"\s+", "", value) or "\uc8fc)" in value:
            m = re.search(r"[\uac00-\ud7a3A-Za-z0-9&.\s]{1,24}(?:\(\s*\uc8fc\s*\)|\uc8fc\))[\uac00-\ud7a3A-Za-z0-9&.\s]{0,16}", value)
            if m:
                value = m.group(0)
    value = re.sub(r"[^가-힣A-Za-z0-9()&.\s]", "", value)
    return _clean_value(value)


def _candidate_ok(value: str, kind: str) -> bool:
    value = _clean_value(value)
    compact = re.sub(r"\s+", "", value)
    if len(compact) < 2:
        return False
    if kind == "company":
        if _COMPANY_REJECT_RE.search(value) or _HEADER_LABEL_RE.fullmatch(compact):
            return False
        if _ADDRESS_HINT_RE.search(value):
            return False
        if not _COMPANY_HINT_RE.search(value):
            return False
        if not re.search(r"[가-힣]", value):
            return False
        if re.search(r"\d", value) and not _COMPANY_HINT_RE.search(value):
            return False
        return len(compact) <= 38
    if kind == "representative":
        return bool(re.fullmatch(r"[가-힣A-Za-z\s]{2,20}", value)) and not _HEADER_LABEL_RE.search(value)
    if kind == "address":
        return bool(_ADDRESS_HINT_RE.search(value)) and len(compact) >= 6
    return True


def _group_rows(lines: list[OcrLine]) -> list[list[OcrLine]]:
    rows: list[list[OcrLine]] = []
    for line in sorted(lines, key=lambda item: (item.cy, item.x)):
        if not rows:
            rows.append([line])
            continue
        current = rows[-1]
        avg_y = sum(item.cy for item in current) / len(current)
        avg_h = sum(item.h for item in current) / len(current)
        if abs(line.cy - avg_y) <= max(avg_h, line.h) * 0.75:
            current.append(line)
        else:
            rows.append([line])
    return [sorted(row, key=lambda item: item.x) for row in rows]


def _row_text(row: list[OcrLine]) -> str:
    return " ".join(line.text for line in sorted(row, key=lambda item: item.x)).strip()


def _table_token_count(text: str) -> int:
    compact = re.sub(r"\s+", "", text or "")
    return len(_TABLE_HEADER_TOKEN_RE.findall(compact))


def _text_has_name_signal(text: str) -> bool:
    return bool(_HANGUL_RE.search(text or "") or _ASCII_WORD_RE.search(text or ""))


def _is_business_contact_line(text: str) -> bool:
    compact = re.sub(r"\s+", "", text or "")
    if not compact:
        return True
    if _TABLE_STANDALONE_LABEL_RE.fullmatch(compact):
        return True
    return bool(
        _TABLE_BUSINESS_CONTACT_RE.search(text)
        or _ADDRESS_HINT_RE.search(text)
        or re.search(r"[\uac00-\ud7a3]{1,12}(?:\ub85c|\uae38)\s*\d", compact)
        or re.search(r"\d+\s*\([\uac00-\ud7a3]{1,12}\ub3d9\)", compact)
        or _BIZ_RE.search(_canonical_digits(text))
        or _PHONE_RE.search(text)
        or re.fullmatch(r"(?:\d{1,4}[-./]){2,}\d{1,6}", compact)
    )


def _is_table_header_row(text: str) -> bool:
    compact = re.sub(r"\s+", "", text or "")
    if not compact:
        return True
    if _TABLE_STANDALONE_LABEL_RE.fullmatch(compact):
        return True
    token_count = len(_TABLE_HEADER_STRONG_RE.findall(compact))
    digit_count = len(re.findall(r"\d", compact))
    return token_count >= 2 and digit_count <= 2


def _is_summary_row_for_items(text: str) -> bool:
    compact = re.sub(r"\s+", "", text or "")
    if not compact:
        return True
    if not _TABLE_SUMMARY_STRONG_RE.search(text):
        return False
    if _is_table_header_row(text):
        return True
    name_chars = len(re.findall(r"[\uac00-\ud7a3A-Za-z]", compact))
    amount_count = len(_amount_values(text))
    # A strong summary label with mostly numeric content should not become an item row.
    if amount_count >= 1 and name_chars <= 14:
        return True
    return bool(re.fullmatch(r"(?:TOTAL|[\uac00-\ud7a3\s]*(?:\ud569\uacc4|\ucd1d\uacc4|VAT|TOTAL)[\uac00-\ud7a3\s]*)[:\-\s0-9,.]*", text, re.I))


def _is_bad_table_data_row(text: str) -> bool:
    compact = re.sub(r"\s+", "", text or "")
    return bool(
        not compact
        or _is_business_contact_line(text)
        or _is_summary_row_for_items(text)
        or _HEADER_LABEL_RE.search(text)
        or _ADDRESS_HINT_RE.search(text)
        or _TOTAL_AMOUNT_ANCHOR_RE.search(text)
        or _TABLE_SUMMARY_RE.search(text)
        or _BIZ_RE.search(_canonical_digits(text))
        or _PHONE_RE.search(text)
        or re.search(r"(?:\ub85c|길)\d+|\d+\([가-힣]+동\)|[가-힣]+동\)", compact)
        or re.search(r"\uc0ac\uc5c5\uc7a5|\uc8fc\uc18c|\uc131\uba85|\ub300\ud45c|\uc138\uc561|\ud569\uacc4|FAX|TEL|Page|\ucc3d\uace0|\uc778\uc218\ud655\uc778", text)
    )


def _is_table_header_only_row(text: str) -> bool:
    compact = re.sub(r"\s+", "", text or "")
    if not compact:
        return True
    if _is_table_header_row(text):
        return True
    token_count = _table_token_count(compact)
    digit_count = len(re.findall(r"\d", compact))
    return token_count >= 2 and digit_count <= 1


def _is_numeric_detail_line(text: str) -> bool:
    compact = re.sub(r"\s+", "", text or "")
    if not compact or _is_business_contact_line(text) or _is_table_header_row(text) or _is_summary_row_for_items(text):
        return False
    digit_count = len(re.findall(r"\d", compact))
    if digit_count == 0:
        return False
    alpha_count = len(re.findall(r"[A-Za-z\uac00-\ud7a3]", compact))
    if _amount_values(text):
        return True
    if _SPEC_ONLY_RE.fullmatch(compact):
        return True
    if re.fullmatch(r"[A-Z0-9][A-Z0-9_\-/.]{1,24}", compact, re.I):
        return True
    return digit_count >= max(1, alpha_count)


def _is_probable_item_name_line(text: str) -> bool:
    compact = re.sub(r"\s+", "", text or "")
    if len(compact) < 2 or len(compact) > 90:
        return False
    if _is_business_contact_line(text) or _is_table_header_row(text) or _is_summary_row_for_items(text):
        return False
    if _COMPANY_HINT_RE.search(text) and not re.search(r"mg|ml|g|T|C|BOX|CAP|TAB|\uc815|\ucea1|\uc561|\ud06c\ub9bc", text, re.I):
        return False
    if re.fullmatch(r"[0-9,.\-_/()]+", compact):
        return False
    if _SPEC_ONLY_RE.fullmatch(compact):
        return False
    if _is_code_only_table_row(text):
        return False
    if re.fullmatch(r"[A-Z0-9_\-/.]{2,24}", compact, re.I) and not re.search(r"TABLET|CAPSULE|CAPS?|ABLET|TAB|CAP", compact, re.I):
        return False
    return _text_has_name_signal(text)


def _is_item_name_like(text: str) -> bool:
    compact = re.sub(r"\s+", "", text or "")
    if _is_probable_item_name_line(text):
        return True
    if len(compact) < 3 or len(compact) > 70:
        return False
    if _is_bad_table_data_row(text) or _is_table_header_only_row(text):
        return False
    if _COMPANY_HINT_RE.search(text) or re.search(r"\ub300\ud45c|\ub2f4\ub2f9|\uac70\ub798\ucc98|\uc8fc\ubb38", text):
        return False
    if _ADDRESS_HINT_RE.search(text) or re.search(r"(?:\ub85c|길)\d+|\d+\([가-힣]+동\)|[가-힣]+동\)", compact):
        return False
    if re.fullmatch(r"[A-Za-z0-9,.\-_/()]+", compact):
        return False
    if re.search(r"\d", compact) and re.search(r"mg|ml|g|T|C|\d{2,}", compact, re.I):
        return bool(re.search(r"[가-힣]", compact) or re.search(r"[A-Za-z]{3,}", compact))
    return bool(re.search(r"[가-힣A-Za-z0-9]{2,}(?:정|액|캡슐|캡슬|산|크림|겔|시럽|플란정)$", compact))


def _is_code_only_table_row(text: str) -> bool:
    compact = re.sub(r"\s+", "", text or "")
    if re.search(r"TABLET|ABLET|CAPSULE|CAPS?|TAB|CAP|\ucea1\uc290|\ucea1\uc2ac|mg|ml", text or "", re.I):
        return False
    return bool(
        re.fullmatch(r"[A-Z]{2,}[A-Z0-9_\-/.]{2,18}", compact)
        or re.fullmatch(r"[A-Z]+-[A-Z0-9_\-/.]{2,18}", compact)
        or re.fullmatch(r"\d{2,5}[-/.]\d{2,5}", compact)
    )


def _nearby_numeric_tail(rows: list[list[OcrLine]], start_idx: int, page_h: float) -> str:
    tail: list[str] = []
    base_y = sum(item.cy for item in rows[start_idx]) / len(rows[start_idx])
    for row in rows[start_idx + 1 : start_idx + 5]:
        row_y = sum(item.cy for item in row) / len(row)
        if row_y - base_y > page_h * 0.10:
            break
        text = _row_text(row)
        if _is_bad_table_data_row(text) or _is_table_header_only_row(text):
            continue
        if re.search(r"\d", text):
            tail.append(text)
        if len(tail) >= 3:
            break
    return " ".join(tail)


def _table_data_candidate_text(rows: list[list[OcrLine]], idx: int, page_h: float) -> str:
    text = _row_text(rows[idx])
    if _is_bad_table_data_row(text) or _is_table_header_only_row(text):
        return ""
    if _is_code_only_table_row(text):
        return ""
    if not re.search(r"[가-힣]", text) and not re.search(r"TABLET|CAPSULE|CAPS?|ABLET", text, re.I):
        return ""
    if re.search(r"\d", text) and _table_row_score(text) > 0:
        return text
    if _is_item_name_like(text):
        tail = _nearby_numeric_tail(rows, idx, page_h)
        if tail:
            return f"{text} {tail}".strip()
    return ""


def _text_order_table_fallback(lines: list[OcrLine]) -> list[str]:
    item_texts: list[str] = []
    for line in lines:
        text = _clean_value(line.text)
        if _is_item_name_like(text):
            item_texts.append(text)
    if not item_texts:
        return []
    return item_texts


def _table_row_score(text: str) -> float:
    if _is_bad_table_data_row(text):
        return -999.0
    score = 0.0
    amount_count = len(_amount_values(text))
    digit_count = len(re.findall(r"\d", text))
    hangul_count = len(re.findall(r"[가-힣]", text))
    score += min(amount_count, 3) * 4
    score += min(digit_count, 20) * 0.15
    score += min(hangul_count, 20) * 0.12
    if _ITEM_NAME_HINT_RE.search(text):
        score += 7
    if re.search(r"[가-힣]", text) and re.search(r"\d", text):
        score += 4
    if len(_amount_values(text)) >= 2 and not _ITEM_NAME_HINT_RE.search(text):
        score -= 4
    if len(text) > 120:
        score -= 2
    return score


def _summarize_table_row(text: str) -> str:
    parts = text.split()
    if len(parts) <= 10:
        return text[:120]
    head = parts[:4]
    tail = [p for p in parts[4:] if re.search(r"\d|,|[A-Za-z]", p)][:8]
    return " ".join(head + tail)[:120]


def _has_product_hint(text: str) -> bool:
    return bool(
        re.search(
            r"(?:\uc815|\uc561|\ud06c\ub9bc|\uc2dc\ub7fd|\uac94)$|"
            r"\ucea1\uc290|\ucea1\uc2ac|TABLET|ABLET|CAPSULE|CAPS?|"
            r"\d+(?:[.,]\d+)?\s*(?:mg|ml|g|kg|t|c|p|tab|cap|dose)",
            text or "",
            re.I,
        )
    )


def _is_compact_catalog_code(text: str) -> bool:
    compact = re.sub(r"[\s._\-/]+", "", text or "")
    return bool(
        not _HANGUL_RE.search(compact)
        and re.fullmatch(r"[A-Z]{2,}\d+[A-Z0-9]{0,10}", compact, re.I)
        and not re.search(r"TABLET|ABLET|CAPSULE|CAPS?|TAB|CAP", text or "", re.I)
    )


def _dedupe_table_rows(rows: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for text in rows:
        value = _clean_value(text)
        if not value:
            continue
        key = re.sub(r"[\s,._/\-]+", "", _canonical_digits(value)).lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(value)
    return result


def _item_name_from_row_text(text: str) -> str:
    parts = [part for part in re.split(r"\s+", text or "") if part]
    name_parts: list[str] = []
    for part in parts:
        compact = re.sub(r"[^\w\uac00-\ud7a3]", "", part)
        if not compact:
            continue
        if _amount_values(part) or re.fullmatch(r"\d+(?:[.,]\d+)?", compact):
            break
        if re.fullmatch(r"[A-Z0-9][A-Z0-9_\-/.]{1,24}", compact, re.I) and name_parts:
            break
        name_parts.append(part)
        if len(" ".join(name_parts)) >= 60:
            break
    value = _clean_value(" ".join(name_parts))
    return value or _clean_value(text)[:60]


def _numbers_from_row_text(text: str) -> list[str]:
    values: list[str] = []
    for match in re.finditer(r"(?<!\d)(?:\u20a9\s*)?(\d+(?:[,.]\d{3})+|\d+(?:[.]\d+)?)(?:\s*\uc6d0)?(?!\d)", _canonical_digits(text or "")):
        raw = match.group(1)
        digits = re.sub(r"\D", "", raw)
        if not digits:
            continue
        if re.fullmatch(r"(?:19|20)\d{6}", digits):
            continue
        values.append(f"{int(digits):,}" if len(digits) >= 4 else raw)
    return values


def _item_dict_from_row_text(text: str) -> dict[str, str]:
    amounts = _amount_values(text)
    numbers = _numbers_from_row_text(text)
    quantity = ""
    unit_price = ""
    if numbers:
        small_numbers = [value for value in numbers if int(re.sub(r"\D", "", value) or "0") <= 10000]
        if small_numbers:
            quantity = small_numbers[0]
    if len(amounts) >= 2:
        unit_price = amounts[-2]
    return {
        "itemName": _item_name_from_row_text(text),
        "quantity": quantity,
        "unitPrice": unit_price,
        "amount": amounts[-1] if amounts else "",
        "rawText": _summarize_table_row(text),
    }


def _is_valid_final_item_text(text: str) -> bool:
    value = _clean_value(text)
    if not value:
        return False
    name = _item_name_from_row_text(value)
    compact_name = re.sub(r"\s+", "", name)
    if len(compact_name) < 2:
        return False
    product_hint = _has_product_hint(value)
    if _is_compact_catalog_code(value) or _is_compact_catalog_code(name):
        return False
    if _COMPANY_HINT_RE.search(value) and not product_hint:
        return False
    if re.search(r"\(\s*\uc8fc\s*\)|\uc8fc\s*\)|\uc8fc\uc2dd|\ud68c\uc0ac", value):
        return False
    if _is_table_header_row(name) or _is_business_contact_line(name) or _is_summary_row_for_items(name):
        return False
    if _is_code_only_table_row(value) or (_is_code_only_table_row(name) and not product_hint):
        return False
    if _is_numeric_detail_line(value) and not (product_hint or _is_probable_item_name_line(name)):
        return False
    if re.search(
        r"^(?:\uc804?\uc77c?\uc794\uc561|\uc794\uc561|\uc8fc\ubb38\uc11c|\uc8fc\ubb38NO|\ub2e8\uac00|\ub2e8\ubb50|"
        r"\uc218\ub7c9|\uacf5\uae09|\uc138\uc561|\ud569\uacc4|\uac70\ub798\uc77c\uc790|\uc8fc\ubb38\uc77c\uc790|"
        r"\ud488\ubaa9\ucf54\ub4dc|\uacc4\uc57d\ucf54\ub4dc|\uac70\ub798\uba85\uc138|\ub2f4\uac00|\ub204\uacc4|"
        r".*(?:\uac70\ub798\uae08\uc561|\uc794\uc561|\uc794\uace0|\uae08\uc561)$)",
        compact_name,
        re.I,
    ):
        return False
    if re.search(r"[\uac00-\ud7a3]{2,4}[,/][\uac00-\ud7a3]{2,4}", name):
        return False
    if len(compact_name) <= 4 and not product_hint:
        return False
    if re.fullmatch(r"[0-9A-Za-z\uac00-\ud7a3]{1,3}", compact_name) and not _amount_values(value):
        return False
    if re.fullmatch(r"[\uac00-\ud7a3]{1,3}", compact_name) and not re.search(
        r"(?:\uc815|\uc561|\ud06c\ub9bc)$|\ucea1\uc290|\ucea1\uc2ac|mg|ml|\d\s*g|tab|cap|box|dose",
        value,
        re.I,
    ):
        return False
    if re.search(r"^(?:\uc138\s*[\uc561\uc5ed\ud45c]|\uacf5\s*\uae09|\ud569\s*\uacc4|TOTAL)$", compact_name, re.I):
        return False
    return _text_has_name_signal(name) and (product_hint or bool(_amount_values(value)) or len(re.findall(r"\d", value)) >= 2)


def _collect_numeric_tail_rows(rows: list[list[OcrLine]], start_idx: int, page_h: float) -> list[tuple[int, str]]:
    tail: list[tuple[int, str]] = []
    base_y = _row_center_y(rows[start_idx])
    for idx in range(start_idx + 1, min(len(rows), start_idx + 8)):
        row_y = _row_center_y(rows[idx])
        if row_y - base_y > page_h * 0.16:
            break
        text = _row_text(rows[idx])
        if _is_table_header_row(text) or _is_business_contact_line(text) or _is_summary_row_for_items(text):
            break
        if _has_product_hint(text) and _is_probable_item_name_line(text):
            break
        if _is_numeric_detail_line(text):
            tail.append((idx, text))
            if len(tail) >= 5 or _amount_values(text):
                # Continue one more nearby numeric row for unit price/amount pairs.
                if len(tail) >= 2:
                    break
        elif tail:
            break
    return tail


def _extract_table_row_texts(rows: list[list[OcrLine]], page_h: float, header_index: int) -> list[str]:
    data_rows: list[str] = []
    consumed_indices: set[int] = set()
    start_idx = max(header_index + 1, 0) if header_index >= 0 else 0
    for idx in range(start_idx, len(rows)):
        if idx in consumed_indices:
            continue
        row = rows[idx]
        row_y = _row_center_y(row)
        if row_y < page_h * 0.16 or row_y > page_h * 0.92:
            continue
        text = _row_text(row)
        if _is_table_header_row(text) or _is_business_contact_line(text) or _is_summary_row_for_items(text):
            continue
        candidate = ""
        if _is_probable_item_name_line(text):
            tail = _collect_numeric_tail_rows(rows, idx, page_h)
            tail_texts = [item[1] for item in tail]
            if tail_texts or re.search(r"\d", text) or _has_product_hint(text):
                candidate = " ".join([text] + tail_texts)
                consumed_indices.update(item[0] for item in tail)
        elif re.search(r"\d", text) and _text_has_name_signal(text) and _table_row_score(text) > 1:
            candidate = text
        if not candidate:
            continue
        if not _has_product_hint(candidate) and not _amount_values(candidate) and not any(_is_numeric_detail_line(part) for part in candidate.splitlines()):
            continue
        data_rows.append(_summarize_table_row(candidate))
    return [text for text in _dedupe_table_rows(data_rows) if _is_valid_final_item_text(text)]


def _find_table_header_y(lines: list[OcrLine], page_h: float) -> float | None:
    for row in _group_rows(lines):
        text = _row_text(row)
        row_y = sum(item.cy for item in row) / len(row)
        if row_y >= page_h * 0.22 and _table_token_count(text) >= 2:
            return min(item.y for item in row)
    return None


def _normalize_date(full_text: str) -> str:
    match = _DATE_RE.search(full_text or "")
    if not match:
        compact = re.sub(r"\D", "", full_text or "")
        m = re.search(r"(20\d{2})(\d{2})(\d{2})", compact)
        if not m:
            return ""
        year, month, day = m.group(1), m.group(2), m.group(3)
    elif match.group(1):
        year, month, day = match.group(1), match.group(2), match.group(3)
    elif match.group(4):
        year, month, day = match.group(4), match.group(5), match.group(6)
    else:
        yy = int(match.group(7))
        year = str(2000 + yy if yy < 70 else 1900 + yy)
        month, day = match.group(8), match.group(9)
    return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"


def _same_row_candidates(lines: list[OcrLine], anchor: OcrLine) -> list[OcrLine]:
    return [
        line
        for line in lines
        if line is not anchor and abs(line.cy - anchor.cy) <= max(anchor.h, line.h) * 1.2 and line.x > anchor.x
    ]


def _value_after_anchor(lines: list[OcrLine], anchor_re: re.Pattern, kind: str) -> str:
    ordered = sorted(lines, key=lambda line: (line.y, line.x))
    for idx, line in enumerate(ordered):
        match = anchor_re.search(line.text)
        if not match:
            continue
        same_line = _clean_value(line.text[match.end():])
        if kind == "company":
            same_line = _clean_company_candidate(same_line)
        if _candidate_ok(same_line, kind):
            return same_line
        for peer in _same_row_candidates(ordered, line):
            candidate = _clean_company_candidate(peer.text) if kind == "company" else _clean_value(peer.text)
            if _candidate_ok(candidate, kind):
                return candidate
        for nxt in ordered[idx + 1 : idx + 4]:
            candidate = _clean_company_candidate(nxt.text) if kind == "company" else _clean_value(nxt.text)
            if _candidate_ok(candidate, kind):
                return candidate
    return ""


def _company_candidates(lines: list[OcrLine], page_h: float, limit_y: float) -> list[tuple[float, float, str]]:
    candidates: list[tuple[float, float, str]] = []
    seen: set[str] = set()
    for line in sorted(lines, key=lambda item: (item.y, item.x)):
        if line.cy > limit_y or line.cy > page_h * 0.78:
            continue
        candidate = _clean_company_candidate(line.text)
        if not _candidate_ok(candidate, "company"):
            continue
        key = re.sub(r"\s+", "", candidate)
        if key in seen:
            continue
        seen.add(key)
        candidates.append((line.cx, line.cy, candidate))
    return candidates


def _biz_candidates(lines: list[OcrLine], limit_y: float) -> list[tuple[float, float, str, OcrLine]]:
    candidates: list[tuple[float, float, str, OcrLine]] = []
    seen: set[str] = set()
    for line in sorted(lines, key=lambda item: (item.x, item.y)):
        if line.cy > limit_y:
            continue
        value = _format_biz(line.text)
        if not value or value in seen:
            continue
        seen.add(value)
        candidates.append((line.cx, line.cy, value, line))
    return candidates


def _nearest_company(
    biz: tuple[float, float, str, OcrLine],
    companies: list[tuple[float, float, str]],
    used: set[str],
    page_w: float,
    page_h: float,
    side: str | None = None,
    split_x: float | None = None,
) -> str:
    bx, by, _, _ = biz
    scored: list[tuple[float, str]] = []
    for cx, cy, company in companies:
        key = re.sub(r"\s+", "", company)
        if key in used:
            continue
        if side and split_x is not None:
            in_side = cx <= split_x if side == "left" else cx > split_x
            if not in_side:
                continue
        dx = abs(cx - bx) / max(page_w, 1)
        dy = abs(cy - by) / max(page_h, 1)
        if dx > 0.45 or dy > 0.28:
            continue
        hint_bonus = -0.10 if _COMPANY_HINT_RE.search(company) else 0
        scored.append((dx * 1.5 + dy + hint_bonus, company))
    if not scored:
        return ""
    scored.sort(key=lambda item: item[0])
    return scored[0][1]


def _local_company_near_biz(
    lines: list[OcrLine],
    biz: tuple[float, float, str, OcrLine],
    used: set[str],
    page_w: float,
    page_h: float,
) -> str:
    bx, by, _, _ = biz
    scored: list[tuple[float, str]] = []
    for line in lines:
        candidate = _clean_company_candidate(line.text)
        if not _candidate_ok(candidate, "company"):
            continue
        key = re.sub(r"\s+", "", candidate)
        if key in used:
            continue
        dx = abs(line.cx - bx) / max(page_w, 1)
        dy = abs(line.cy - by) / max(page_h, 1)
        if dx > 0.24 or dy > 0.24:
            continue
        if _TOTAL_AMOUNT_ANCHOR_RE.search(line.text) or _TABLE_HEADER_TOKEN_RE.search(line.text):
            continue
        scored.append((dx * 1.2 + dy, candidate))
    if not scored:
        return ""
    scored.sort(key=lambda item: item[0])
    return scored[0][1]


def _fallback_company_for_side(
    companies: list[tuple[float, float, str]],
    side: str,
    split_x: float,
    used: set[str],
) -> str:
    pool = [
        (abs(cx - split_x), company)
        for cx, _, company in companies
        if (cx <= split_x if side == "left" else cx > split_x)
        and re.sub(r"\s+", "", company) not in used
    ]
    if not pool:
        return ""
    pool.sort(key=lambda item: item[0])
    return pool[0][1]


def _assign_unique_fallbacks(
    supplier: dict[str, str],
    buyer: dict[str, str],
    companies: list[tuple[float, float, str]],
    split_x: float,
    used_companies: set[str],
) -> None:
    left = [
        (abs(cx - split_x), company)
        for cx, _, company in companies
        if cx <= split_x and re.sub(r"\s+", "", company) not in used_companies
    ]
    right = [
        (abs(cx - split_x), company)
        for cx, _, company in companies
        if cx > split_x and re.sub(r"\s+", "", company) not in used_companies
    ]
    left.sort(key=lambda item: item[0])
    right.sort(key=lambda item: item[0])

    if not supplier["company"] and left:
        supplier["company"] = left[0][1]
        used_companies.add(re.sub(r"\s+", "", supplier["company"]))
    if not buyer["company"] and right:
        buyer["company"] = right[0][1]
        used_companies.add(re.sub(r"\s+", "", buyer["company"]))

    remaining = [
        (cx, company)
        for cx, _, company in companies
        if re.sub(r"\s+", "", company) not in used_companies
    ]
    if not supplier["company"] and not buyer["company"] and len(remaining) >= 2:
        remaining.sort(key=lambda item: item[0])
        supplier["company"] = remaining[0][1]
        buyer["company"] = remaining[-1][1]
    elif not supplier["company"] and remaining:
        remaining.sort(key=lambda item: item[0])
        supplier["company"] = remaining[0][1]
    elif not buyer["company"] and remaining:
        remaining.sort(key=lambda item: item[0])
        buyer["company"] = remaining[-1][1]


def _address_near(lines: list[OcrLine], x_center: float, y_center: float, page_w: float, page_h: float) -> str:
    candidates: list[tuple[float, str]] = []
    for line in lines:
        if abs(line.cx - x_center) / max(page_w, 1) > 0.45 or abs(line.cy - y_center) / max(page_h, 1) > 0.25:
            continue
        text = _clean_value(line.text)
        if _candidate_ok(text, "address"):
            candidates.append((abs(line.cy - y_center), text))
    candidates.sort(key=lambda item: item[0])
    return candidates[0][1] if candidates else ""


def _rep_near(lines: list[OcrLine], x_center: float, y_center: float, page_w: float, page_h: float) -> str:
    scoped = [
        line
        for line in lines
        if abs(line.cx - x_center) / max(page_w, 1) <= 0.35 and abs(line.cy - y_center) / max(page_h, 1) <= 0.22
    ]
    return _value_after_anchor(scoped, _REP_ANCHOR_RE, "representative")


def _is_representative_candidate(text: str) -> bool:
    value = _clean_value(text)
    value = re.sub(r"^(?:\ub300\s*\ud45c(?:\uc790|\uc790\uba85)?|\uc131\s*\uba85|\ub300\s*\ud45c\s*\uc774\s*\uc0ac)\s*[:：]?", "", value).strip()
    compact = re.sub(r"\s+", "", value)
    if not compact or re.search(r"\d", compact):
        return False
    if _TABLE_STANDALONE_LABEL_RE.fullmatch(compact) or _TABLE_BUSINESS_CONTACT_RE.search(value):
        return False
    if _COMPANY_HINT_RE.search(value) or _ADDRESS_HINT_RE.search(value) or re.search(r"(?:\ub85c|\uae38|\ubc88\uae38)\s*\d*|\d+\s*\([\uac00-\ud7a3]{1,12}\ub3d9\)", value):
        return False
    if re.search(
        r"\ud2b9\uae30|\uae30\ud0c0|\uc5f0\ub77d|\ubd80\uac00|\ubc30\uc1a1|\ud488\ubaa9|\ub2f4\ub2f9|\ucf54\ub4dc|"
        r"\uacc4\uc57d|\uc794\uc561|\uc138\ud45c|\uac70\ub798\uba85\uc138|\uc0c1\ud750|\uc0c1\ud638|\uc5c5\ud14c|\uc5c5\ud0dc|\ucd1d\ubaa9|\ud1b5\ubaa9|"
        r"\uc591\uc57d|\ub3c4\uba54|\uc6d4\ub9d0|\ub9e4\uc7a5|\uc74c\uc2dd|\uc678\uc57d|\uacf5\uae09",
        value,
    ):
        return False
    if re.fullmatch(r"[\uac00-\ud7a3]{2,5}(?:[,/][\uac00-\ud7a3]{2,5})?", compact):
        return True
    return bool(re.fullmatch(r"[A-Z][A-Z\s.]{3,30}", value))


def _clean_representative_candidate(text: str) -> str:
    value = _clean_value(text)
    match = _REP_ANCHOR_RE.search(value)
    if match:
        value = value[match.end() :]
    value = re.sub(r"^(?:\ub300\s*\ud45c(?:\uc790|\uc790\uba85)?|\uc131\s*\uba85|\ub300\s*\ud45c\s*\uc774\s*\uc0ac)\s*[:：]?", "", value).strip()
    value = re.sub(r"\(\s*\uc778\s*\)|[\[\]()]|[:：]", "", value).strip()
    value = re.sub(r"^([\uac00-\ud7a3]{2,5})\s*\uc778$", r"\1", value).strip()
    return value if _is_representative_candidate(value) else ""


def _representative_from_scope(lines: list[OcrLine]) -> str:
    ordered = sorted(lines, key=lambda item: (item.y, item.x))
    for idx, line in enumerate(ordered):
        if not _REP_ANCHOR_RE.search(line.text):
            continue
        same = _clean_representative_candidate(_REP_ANCHOR_RE.sub("", line.text, count=1))
        if same:
            return same
        for peer in _same_row_candidates(ordered, line):
            candidate = _clean_representative_candidate(peer.text)
            if candidate:
                return candidate
        for nxt in ordered[idx + 1 : idx + 5]:
            candidate = _clean_representative_candidate(nxt.text)
            if candidate:
                return candidate
    candidates: list[tuple[int, str]] = []
    for line in ordered:
        candidate = _clean_representative_candidate(line.text)
        if candidate:
            score = 10
            if "," in candidate or "/" in candidate:
                score += 12
            if re.fullmatch(r"[\uac00-\ud7a3]{2,3}", candidate):
                score += 4
            candidates.append((score, candidate))
    if not candidates:
        return ""
    candidates.sort(key=lambda item: -item[0])
    return candidates[0][1]


def _should_replace_representative(current: str, candidate: str) -> bool:
    if not candidate:
        return False
    if not current:
        return True
    return not _is_representative_candidate(current)


def _is_address_candidate_line(text: str) -> bool:
    value = _clean_value(text)
    compact = re.sub(r"\s+", "", value)
    if len(compact) < 5:
        return False
    if _BIZ_RE.search(_canonical_digits(value)) or _PHONE_RE.search(value):
        return False
    if _COMPANY_HINT_RE.search(value) or _REP_ANCHOR_RE.search(value):
        return False
    if _TABLE_SUMMARY_RE.search(value) or _TABLE_HEADER_TOKEN_RE.search(value) or _has_product_hint(value):
        return False
    if _amount_values(value) and not _ADDRESS_TOKEN_RE.search(value):
        return False
    return bool(_ADDRESS_TOKEN_RE.search(value) or re.search(r"\d+\s*\([\uac00-\ud7a3]{1,12}\ub3d9\)", compact))


def _clean_address_candidate_line(text: str) -> str:
    value = _clean_value(text)
    value = re.sub(r"^(?:\uc8fc\s*\uc18c|\uc18c\s*\uc7ac\s*\uc9c0|\uc0ac\s*\uc5c5\s*\uc7a5(?:\s*\uc8fc\s*\uc18c)?)\s*[:：]?", "", value).strip()
    return value if _is_address_candidate_line(value) else ""


def _address_from_scope(lines: list[OcrLine]) -> str:
    ordered = sorted(lines, key=lambda item: (item.y, item.x))
    candidates: list[tuple[int, int, str]] = []
    for idx, line in enumerate(ordered):
        candidate = _clean_address_candidate_line(line.text)
        if not candidate:
            continue
        score = len(_ADDRESS_TOKEN_RE.findall(candidate)) * 4 + min(len(candidate), 50)
        if _ADDR_ANCHOR_RE.search(line.text):
            score += 10
        candidates.append((score, idx, candidate))
    if not candidates:
        return ""
    candidates.sort(key=lambda item: (-item[0], item[1]))
    _, idx, first = candidates[0]
    parts = [first]
    for near in ordered[idx + 1 : idx + 3]:
        extra = _clean_address_candidate_line(near.text)
        if extra and extra not in parts:
            parts.append(extra)
    if len(parts) == 1:
        for near in reversed(ordered[max(0, idx - 2) : idx]):
            extra = _clean_address_candidate_line(near.text)
            if extra and extra not in parts:
                parts.insert(0, extra)
                break
    if len(parts) >= 2 and _ADDRESS_HINT_RE.search(parts[1]) and not _ADDRESS_HINT_RE.search(parts[0]):
        parts[0], parts[1] = parts[1], parts[0]
    return _clean_value(" ".join(parts))


def _party_for_biz_value(
    supplier: dict[str, str],
    buyer: dict[str, str],
    value: str,
    fallback_role: str,
) -> tuple[str, dict[str, str]]:
    if supplier.get("bizNumber") == value:
        return "supplier", supplier
    if buyer.get("bizNumber") == value:
        return "buyer", buyer
    return (fallback_role, supplier if fallback_role == "supplier" else buyer)


def _looks_like_customer_company(company: str) -> bool:
    value = company or ""
    return bool(re.search(r"\uc9c0\s*\uc810|\uac70\s*\ub798\s*\ucc98|\ub0a9\s*\ud488\s*\ucc98|\uadc0\s*\ud558|\uc601\s*\uc5c5\s*\uc18c", value))


def _rebalance_customer_company_hint(supplier: dict[str, str], buyer: dict[str, str], debug: dict[str, Any]) -> None:
    supplier_company = supplier.get("company", "")
    buyer_company = buyer.get("company", "")
    if not supplier_company or not _looks_like_customer_company(supplier_company):
        return
    if buyer_company and _looks_like_customer_company(buyer_company):
        return

    if buyer.get("bizNumber"):
        supplier["company"], buyer["company"] = buyer_company, supplier_company
        debug["applied"].append("company.swap_customer_hint")
        return

    moved = {
        "company": supplier.get("company", ""),
        "bizNumber": supplier.get("bizNumber", ""),
        "representative": supplier.get("representative", ""),
        "address": supplier.get("address", ""),
    }
    supplier["company"] = buyer_company
    supplier["bizNumber"] = ""
    supplier["representative"] = ""
    supplier["address"] = ""
    buyer.update(moved)
    debug["applied"].append("party.move_customer_hint")


def _ordered_scope(lines: list[OcrLine], start_idx: int, end_idx: int) -> list[OcrLine]:
    ordered = sorted(lines, key=lambda item: (item.y, item.x))
    return ordered[max(0, start_idx) : min(len(ordered), end_idx)]


def _line_indices(lines: list[OcrLine]) -> dict[int, int]:
    return {id(line): idx for idx, line in enumerate(sorted(lines, key=lambda item: (item.y, item.x)))}


def _apply_party_block_refinements(
    supplier: dict[str, str],
    buyer: dict[str, str],
    all_lines: list[OcrLine],
    bizs: list[tuple[float, float, str, OcrLine]],
    page_h: float,
) -> dict[str, Any]:
    ordered = sorted(all_lines, key=lambda item: (item.y, item.x))
    index_by_id = _line_indices(all_lines)
    debug: dict[str, Any] = {"mode": "", "applied": []}
    if not bizs:
        return debug
    sorted_bizs = sorted(bizs, key=lambda item: index_by_id.get(id(item[3]), 0))
    biz_indices = [index_by_id.get(id(item[3]), 0) for item in sorted_bizs]

    if len(sorted_bizs) >= 2 and biz_indices[1] - biz_indices[0] <= 6:
        scope_end = min(len(ordered), biz_indices[1] + 26)
        header_scope = ordered[biz_indices[0] : scope_end]
        blob = " ".join(line.text for line in header_scope)
        role_order = ["buyer", "supplier"] if _BUYER_PARTY_LABEL_RE.search(blob) and not _SUPPLIER_PARTY_LABEL_RE.search(blob) else ["supplier", "buyer"]
        reps = [_clean_representative_candidate(line.text) for line in header_scope]
        reps = [item for item in reps if item]
        addresses = [_clean_address_candidate_line(line.text) for line in header_scope]
        addresses = [item for item in addresses if item]
        debug.update({"mode": "shared_stacked_block", "roleOrder": role_order, "reps": reps, "addresses": addresses})
        role_to_party = {"supplier": supplier, "buyer": buyer}
        for role, biz in zip(role_order, sorted_bizs[:2]):
            role_to_party[role]["bizNumber"] = biz[2]
        for pos, role in enumerate(role_order):
            party = role_to_party[role]
            duplicate_rep = party.get("representative", "") and any(
                party.get("representative") == other.get("representative")
                for other_role, other in role_to_party.items()
                if other_role != role
            )
            if pos < len(reps) and (_should_replace_representative(party.get("representative", ""), reps[pos]) or duplicate_rep):
                party["representative"] = reps[pos]
                debug["applied"].append(f"{role}.representative")
            if pos < len(addresses):
                party["address"] = addresses[pos]
                debug["applied"].append(f"{role}.address")
        _rebalance_customer_company_hint(supplier, buyer, debug)
        return debug

    for pos, biz in enumerate(sorted_bizs[:2]):
        idx = biz_indices[pos]
        prev_idx = biz_indices[pos - 1] if pos > 0 else -1
        next_idx = biz_indices[pos + 1] if pos + 1 < len(biz_indices) else len(ordered)
        start = max(prev_idx + 1, idx - 12)
        end = min(next_idx, idx + 18)
        scope = ordered[start:end]
        fallback_role = "supplier" if pos == 0 else "buyer"
        role, party = _party_for_biz_value(supplier, buyer, biz[2], fallback_role)
        rep = _representative_from_scope(scope)
        addr = _address_from_scope(scope)
        if _should_replace_representative(party.get("representative", ""), rep):
            party["representative"] = rep
            debug["applied"].append(role + ".representative")
        if addr:
            party["address"] = addr
            debug["applied"].append(role + ".address")
    debug["mode"] = "per_biz_window"
    _rebalance_customer_company_hint(supplier, buyer, debug)
    return debug


def _extract_party_fields(
    header_lines: list[OcrLine],
    all_lines: list[OcrLine],
    page_w: float,
    page_h: float,
    header_limit_y: float,
) -> tuple[dict[str, str], dict[str, str], dict[str, Any]]:
    split_x = page_w * 0.5
    candidate_limit_y = max(header_limit_y, page_h * 0.90)
    companies = _company_candidates(all_lines, page_h, candidate_limit_y)
    bizs = _biz_candidates(all_lines, candidate_limit_y)
    supplier = {"company": "", "bizNumber": "", "representative": "", "address": ""}
    buyer = {"company": "", "bizNumber": "", "representative": "", "address": ""}
    used_companies: set[str] = set()

    if len(bizs) >= 2:
        biz_span_x = max(item[0] for item in bizs) - min(item[0] for item in bizs)
        stacked_blocks = biz_span_x <= page_w * 0.18
        if stacked_blocks:
            supplier_biz, buyer_biz = sorted(bizs, key=lambda item: item[1])[:2]
            buyer["bizNumber"] = buyer_biz[2]
            supplier["bizNumber"] = supplier_biz[2]
            buyer["company"] = _nearest_company(buyer_biz, companies, used_companies, page_w, page_h, None, None)
            if not buyer["company"]:
                buyer["company"] = _local_company_near_biz(all_lines, buyer_biz, used_companies, page_w, page_h)
            if buyer["company"]:
                used_companies.add(re.sub(r"\s+", "", buyer["company"]))
            supplier["company"] = _nearest_company(supplier_biz, companies, used_companies, page_w, page_h, None, None)
            if not supplier["company"]:
                supplier["company"] = _local_company_near_biz(all_lines, supplier_biz, used_companies, page_w, page_h)
            if supplier["company"]:
                used_companies.add(re.sub(r"\s+", "", supplier["company"]))
            buyer["representative"] = _rep_near(all_lines, buyer_biz[0], buyer_biz[1], page_w, page_h)
            supplier["representative"] = _rep_near(all_lines, supplier_biz[0], supplier_biz[1], page_w, page_h)
            buyer["address"] = _address_near(all_lines, buyer_biz[0], buyer_biz[1], page_w, page_h)
            supplier["address"] = _address_near(all_lines, supplier_biz[0], supplier_biz[1], page_w, page_h)
        else:
            left_biz, right_biz = sorted(bizs, key=lambda item: item[0])[:2]
            supplier["bizNumber"] = left_biz[2]
            buyer["bizNumber"] = right_biz[2]
            supplier["company"] = _nearest_company(left_biz, companies, used_companies, page_w, page_h, "left", split_x)
            if supplier["company"]:
                used_companies.add(re.sub(r"\s+", "", supplier["company"]))
            buyer["company"] = _nearest_company(right_biz, companies, used_companies, page_w, page_h, "right", split_x)
            if buyer["company"]:
                used_companies.add(re.sub(r"\s+", "", buyer["company"]))
            supplier["representative"] = _rep_near(header_lines, left_biz[0], left_biz[1], page_w, page_h)
            buyer["representative"] = _rep_near(header_lines, right_biz[0], right_biz[1], page_w, page_h)
            supplier["address"] = _address_near(header_lines, left_biz[0], left_biz[1], page_w, page_h)
            buyer["address"] = _address_near(header_lines, right_biz[0], right_biz[1], page_w, page_h)
    elif len(bizs) == 1:
        bx, by, value, _ = bizs[0]
        target = supplier if bx <= split_x else buyer
        side = "left" if bx <= split_x else "right"
        target["bizNumber"] = value
        target["company"] = _nearest_company(bizs[0], companies, used_companies, page_w, page_h, side, split_x)
        if not target["company"]:
            target["company"] = _local_company_near_biz(all_lines, bizs[0], used_companies, page_w, page_h)
        if target["company"]:
            used_companies.add(re.sub(r"\s+", "", target["company"]))
        target["representative"] = _rep_near(header_lines, bx, by, page_w, page_h)
        target["address"] = _address_near(header_lines, bx, by, page_w, page_h)

    _assign_unique_fallbacks(supplier, buyer, companies, split_x, used_companies)

    if not supplier["representative"]:
        supplier["representative"] = _value_after_anchor([l for l in header_lines if l.cx <= split_x], _REP_ANCHOR_RE, "representative")
    if not buyer["representative"]:
        buyer["representative"] = _value_after_anchor([l for l in header_lines if l.cx > split_x], _REP_ANCHOR_RE, "representative")
    if not supplier["address"]:
        supplier["address"] = _value_after_anchor([l for l in header_lines if l.cx <= split_x], _ADDR_ANCHOR_RE, "address")
    if not buyer["address"]:
        buyer["address"] = _value_after_anchor([l for l in header_lines if l.cx > split_x], _ADDR_ANCHOR_RE, "address")

    block_debug = _apply_party_block_refinements(supplier, buyer, all_lines, bizs, page_h)

    return supplier, buyer, {
        "companies": companies,
        "bizs": [(round(x), round(y), value) for x, y, value, _ in bizs],
        "split_x": split_x,
        "block_refinement": block_debug,
    }


def _extract_amount_near(lines: list[OcrLine], anchor_re: re.Pattern) -> str:
    ordered = sorted(lines, key=lambda line: (line.y, line.x))
    for idx, line in enumerate(ordered):
        if not anchor_re.search(line.text):
            continue
        value = _amount_value(line.text)
        if value:
            return value
        row_text = " ".join(peer.text for peer in _same_row_candidates(ordered, line))
        value = _amount_value(row_text)
        if value:
            return value
        for prev in reversed(ordered[max(0, idx - 4) : idx]):
            if _BIZ_RE.search(_canonical_digits(prev.text)) or _PHONE_RE.search(prev.text):
                continue
            value = _amount_value(prev.text)
            if value:
                return value
        for nxt in ordered[idx + 1 : idx + 9]:
            if _BIZ_RE.search(_canonical_digits(nxt.text)) or _PHONE_RE.search(nxt.text):
                continue
            value = _amount_value(nxt.text)
            if value:
                return value
    return ""


def _large_amount_value(text: str, min_value: int = 10_000) -> str:
    values = [
        value
        for value in _amount_values(text)
        if int(value.replace(",", "")) >= min_value
    ]
    return values[-1] if values else ""


def _extract_amount_near_reading_order(lines: list[OcrLine], anchor_re: re.Pattern) -> str:
    for idx, line in enumerate(lines):
        if not anchor_re.search(line.text):
            continue
        window = list(reversed(lines[max(0, idx - 6) : idx])) + lines[idx : idx + 12]
        for item in window:
            if _BIZ_RE.search(_canonical_digits(item.text)) or _PHONE_RE.search(item.text):
                continue
            value = _large_amount_value(item.text)
            if value:
                return value
    return ""


def _row_center_y(row: list[OcrLine]) -> float:
    return sum(item.cy for item in row) / len(row)


def _row_has_item_context(text: str) -> bool:
    compact = re.sub(r"\s+", "", text or "")
    return bool(
        _is_item_name_like(text)
        or _is_code_only_table_row(text)
        or re.search(r"\ud488\s*\uba85|\ud488\s*\ubaa9|\ud488\s*\ucf54\ub4dc|\uc218\s*\ub7c9|\ub2e8\s*\uac00", text)
        or re.search(r"[A-Z]{2,}[A-Z0-9]{2,}\s+\d", compact)
    )


def _row_has_non_summary_noise(text: str) -> bool:
    compact = re.sub(r"\s+", "", text or "")
    return bool(
        _ADDRESS_HINT_RE.search(text)
        or _BIZ_RE.search(_canonical_digits(text))
        or _PHONE_RE.search(text)
        or _DATE_RE.search(text)
        or re.search(r"\uc0ac\uc5c5\uc790|\ub4f1\ub85d\ubc88\ud638|\uc804\s*\ud654|FAX|TEL|\uacc4\uc88c|\uc740\ud589|Page|\ud398\uc774\uc9c0", text, re.I)
        or re.fullmatch(r"(?:\d{1,3}[-./]){2,}\d{1,5}", compact)
    )


def _summary_anchor_flags(text: str) -> tuple[bool, bool, bool]:
    return (
        bool(_SUPPLY_AMOUNT_ANCHOR_RE.search(text)),
        bool(_TAX_AMOUNT_ANCHOR_RE.search(text)),
        bool(_TOTAL_AMOUNT_ANCHOR_RE.search(text) or re.search(r"\ud568\s*\uacc4", text)),
    )


def _nearby_summary_context(rows: list[list[OcrLine]], idx: int, page_h: float) -> str:
    base_y = _row_center_y(rows[idx])
    parts: list[str] = []
    for near_idx in range(max(0, idx - 1), min(len(rows), idx + 2)):
        near_y = _row_center_y(rows[near_idx])
        if abs(near_y - base_y) <= page_h * 0.045:
            parts.append(_row_text(rows[near_idx]))
    return " ".join(parts)


def _footer_summary_candidates(
    lines: list[OcrLine],
    page_h: float,
    table_header_y: float | None,
) -> tuple[list[SummaryAmountCandidate], float]:
    rows = _group_rows(lines)
    footer_start = max(page_h * 0.68, (table_header_y or 0) + page_h * 0.18)
    if not rows:
        return [], footer_start

    candidates: list[SummaryAmountCandidate] = []
    for idx, row in enumerate(rows):
        text = _row_text(row)
        cy = _row_center_y(row)
        if cy < footer_start or cy > page_h * 0.94:
            continue
        if _row_has_non_summary_noise(text):
            continue
        context = _nearby_summary_context(rows, idx, page_h)
        has_summary_anchor = bool(_TABLE_SUMMARY_RE.search(context) or _TOTAL_AMOUNT_ANCHOR_RE.search(context))
        if _row_has_item_context(text) and not has_summary_anchor:
            continue
        supply_anchor, tax_anchor, total_anchor = _summary_anchor_flags(context)
        if not (has_summary_anchor or supply_anchor or tax_anchor or total_anchor):
            continue
        for line in row:
            if _row_has_non_summary_noise(line.text):
                continue
            for value in _amount_values(line.text):
                numeric = int(value.replace(",", ""))
                if numeric < 10_000:
                    continue
                candidates.append(
                    SummaryAmountCandidate(
                        value=value,
                        numeric=numeric,
                        row_idx=idx,
                        cy=cy,
                        x=line.x,
                        text=line.text,
                        context=context,
                        supply_anchor=supply_anchor,
                        tax_anchor=tax_anchor,
                        total_anchor=total_anchor,
                    )
                )
        if not any(item.row_idx == idx for item in candidates):
            for value in _amount_values(text):
                numeric = int(value.replace(",", ""))
                if numeric >= 10_000:
                    candidates.append(
                        SummaryAmountCandidate(
                            value=value,
                            numeric=numeric,
                            row_idx=idx,
                            cy=cy,
                            x=min(item.x for item in row),
                            text=text,
                            context=context,
                            supply_anchor=supply_anchor,
                            tax_anchor=tax_anchor,
                            total_anchor=total_anchor,
                        )
                    )
    return candidates, footer_start


def _summary_candidate_base_score(candidate: SummaryAmountCandidate, footer_start: float, page_h: float, role: str) -> float:
    score = 0.0
    if footer_start <= candidate.cy <= page_h * 0.94:
        score += 8
        score += min(max((candidate.cy - footer_start) / max(page_h * 0.24, 1), 0), 1) * 4
    if _TABLE_SUMMARY_RE.search(candidate.context):
        score += 6
    if role == "supply" and candidate.supply_anchor:
        score += 13
    if role == "tax" and candidate.tax_anchor:
        score += 13
    if role == "total" and candidate.total_anchor:
        score += 13
    if _row_has_item_context(candidate.text) and not _TABLE_SUMMARY_RE.search(candidate.context):
        score -= 18
    if _row_has_non_summary_noise(candidate.context):
        score -= 24
    if candidate.cy < page_h * 0.55:
        score -= 20
    return score


def _amounts_close(left: int, right: int) -> bool:
    tolerance = max(2_500, int(max(left, right) * 0.001))
    return abs(left - right) <= tolerance


def _summary_amount_pool(lines: list[OcrLine], min_value: int = 10_000) -> list[tuple[int, str, int, float, str]]:
    rows = _group_rows(lines)
    pool: list[tuple[int, str, int, float, str]] = []
    seen: set[tuple[int, int]] = set()
    for idx, row in enumerate(rows):
        text = _row_text(row)
        if _row_has_non_summary_noise(text):
            continue
        context_parts = [
            _row_text(rows[near_idx])
            for near_idx in range(max(0, idx - 4), min(len(rows), idx + 5))
        ]
        context = " ".join(context_parts)
        cy = _row_center_y(row)
        for value in _amount_values(text):
            numeric = int(value.replace(",", ""))
            if numeric < min_value:
                continue
            key = (idx, numeric)
            if key in seen:
                continue
            seen.add(key)
            pool.append((numeric, value, idx, cy, context))
    return pool


def _infer_summary_pair_from_amount_pool(
    lines: list[OcrLine],
    total: str = "",
    allow_synthesized_total: bool = False,
) -> tuple[dict[str, str], dict[str, Any]]:
    total_num = int(total.replace(",", "")) if total else 0
    pool = _summary_amount_pool(lines)
    debug: dict[str, Any] = {"source": "", "candidateCount": len(pool)}
    if len(pool) < 2:
        return {}, debug

    scored: list[tuple[float, int, int, int, str, str, str, str]] = []
    for supply_num, supply_value, supply_idx, supply_y, supply_text in pool:
        for tax_num, tax_value, tax_idx, tax_y, tax_text in pool:
            if supply_num <= tax_num or supply_idx == tax_idx and supply_num == tax_num:
                continue
            ratio = tax_num / supply_num
            if not 0.05 <= ratio <= 0.15:
                continue
            synthesized = supply_num + tax_num
            if total_num and not _amounts_close(synthesized, total_num):
                continue
            row_span = abs(supply_idx - tax_idx)
            if row_span > 24:
                continue
            score = 40.0
            if total_num:
                score += 35
            elif allow_synthesized_total:
                score += 12
            if abs(ratio - 0.1) <= 0.015:
                score += 14
            if row_span <= 4:
                score += 10
            elif row_span <= 12:
                score += 4
            context = f"{supply_text} {tax_text}"
            if _SUPPLY_AMOUNT_ANCHOR_RE.search(context):
                score += 10
            if _TAX_AMOUNT_ANCHOR_RE.search(context):
                score += 10
            if _row_has_item_context(supply_text):
                score -= 8
            if _row_has_item_context(tax_text):
                score -= 8
            scored.append((score, synthesized, supply_num, tax_num, supply_value, tax_value, supply_text, tax_text))

    if not scored:
        return {}, debug
    scored.sort(key=lambda item: (-item[0], -item[1]))
    score, synthesized, _, _, supply_value, tax_value, supply_text, tax_text = scored[0]
    if total_num and score < 62:
        debug["bestScore"] = round(score, 2)
        return {}, debug
    if not total_num and (not allow_synthesized_total or score < 58):
        debug["bestScore"] = round(score, 2)
        return {}, debug

    result = {
        "supplyAmount": supply_value,
        "taxAmount": tax_value,
    }
    if total_num:
        result["totalAmount"] = f"{total_num:,}"
    elif allow_synthesized_total:
        result["totalAmount"] = f"{synthesized:,}"
    debug.update(
        {
            "source": "amount_pair_checksum",
            "bestScore": round(score, 2),
            "supply": [supply_value, supply_text],
            "tax": [tax_value, tax_text],
            "total": result.get("totalAmount", ""),
        }
    )
    return result, debug


def _extract_footer_summary_triple(
    lines: list[OcrLine],
    page_h: float,
    table_header_y: float | None,
    existing_total: str = "",
) -> tuple[dict[str, str], dict[str, Any]]:
    candidates, footer_start = _footer_summary_candidates(lines, page_h, table_header_y)
    debug: dict[str, Any] = {"source": "", "candidateCount": len(candidates)}
    if len(candidates) < 2:
        return {}, debug

    existing_total_num = int(existing_total.replace(",", "")) if existing_total else 0
    scored: list[tuple[float, SummaryAmountCandidate, SummaryAmountCandidate, SummaryAmountCandidate | None, int]] = []
    for supply_candidate in candidates:
        for tax_candidate in candidates:
            if supply_candidate is tax_candidate:
                continue
            supply_num = supply_candidate.numeric
            tax_num = tax_candidate.numeric
            if supply_num <= 0 or tax_num <= 0 or supply_num <= tax_num:
                continue
            tax_ratio = tax_num / supply_num
            if not 0.05 <= tax_ratio <= 0.15:
                continue
            synthesized_num = supply_num + tax_num
            if existing_total_num and synthesized_num > existing_total_num * 5:
                continue
            total_matches = [
                item
                for item in candidates
                if _amounts_close(item.numeric, synthesized_num) and item is not supply_candidate and item is not tax_candidate
            ]
            if existing_total_num and _amounts_close(synthesized_num, existing_total_num):
                total_matches.append(
                    SummaryAmountCandidate(
                        value=f"{existing_total_num:,}",
                        numeric=existing_total_num,
                        row_idx=max(supply_candidate.row_idx, tax_candidate.row_idx),
                        cy=max(supply_candidate.cy, tax_candidate.cy),
                        x=max(supply_candidate.x, tax_candidate.x),
                        text="existing_total",
                        context=f"{supply_candidate.context} {tax_candidate.context}",
                        supply_anchor=False,
                        tax_anchor=False,
                        total_anchor=True,
                    )
                )
            if not total_matches and not existing_total_num:
                total_matches.append(None)
            for total_candidate in total_matches:
                total_num = total_candidate.numeric if total_candidate else synthesized_num
                if existing_total_num and total_num < existing_total_num * 0.2:
                    continue
                row_span = max(supply_candidate.row_idx, tax_candidate.row_idx, total_candidate.row_idx if total_candidate else tax_candidate.row_idx) - min(
                    supply_candidate.row_idx, tax_candidate.row_idx, total_candidate.row_idx if total_candidate else tax_candidate.row_idx
                )
                y_values = [supply_candidate.cy, tax_candidate.cy]
                if total_candidate:
                    y_values.append(total_candidate.cy)
                y_span = max(y_values) - min(y_values)
                if row_span > 3 or y_span > page_h * 0.08:
                    continue

                score = 40.0
                score += _summary_candidate_base_score(supply_candidate, footer_start, page_h, "supply")
                score += _summary_candidate_base_score(tax_candidate, footer_start, page_h, "tax")
                if total_candidate:
                    score += _summary_candidate_base_score(total_candidate, footer_start, page_h, "total")
                else:
                    score += 6
                if row_span <= 1:
                    score += 12
                elif row_span == 2:
                    score += 6
                if y_span <= page_h * 0.035:
                    score += 8
                if supply_candidate.supply_anchor and tax_candidate.tax_anchor:
                    score += 10
                if total_candidate and total_candidate.total_anchor:
                    score += 8
                if existing_total_num and _amounts_close(total_num, existing_total_num):
                    score += 18
                if total_num == synthesized_num:
                    score += 5
                if abs(tax_ratio - 0.1) <= 0.015:
                    score += 8
                scored.append((score, supply_candidate, tax_candidate, total_candidate, synthesized_num))

    if not scored:
        return {}, debug
    scored.sort(key=lambda item: (-item[0], -item[4]))
    score, supply_candidate, tax_candidate, total_candidate, synthesized_num = scored[0]
    if score < 78:
        debug["bestScore"] = round(score, 2)
        return {}, debug

    result = {
        "supplyAmount": supply_candidate.value,
        "taxAmount": tax_candidate.value,
        "totalAmount": total_candidate.value if total_candidate else f"{synthesized_num:,}",
    }
    debug.update(
        {
            "source": "footer_summary_triple",
            "bestScore": round(score, 2),
            "supplySource": "footer_supply_anchor" if supply_candidate.supply_anchor else "footer_summary_amount",
            "taxSource": "footer_tax_anchor" if tax_candidate.tax_anchor else "footer_summary_amount",
            "totalSource": "footer_total_anchor" if total_candidate and total_candidate.total_anchor else "synthesized_supply_tax",
            "supply": [supply_candidate.value, round(supply_candidate.x), round(supply_candidate.cy), supply_candidate.text],
            "tax": [tax_candidate.value, round(tax_candidate.x), round(tax_candidate.cy), tax_candidate.text],
            "total": (
                [total_candidate.value, round(total_candidate.x), round(total_candidate.cy), total_candidate.text]
                if total_candidate
                else [f"{synthesized_num:,}", None, None, "synthesized_supply_tax"]
            ),
        }
    )
    return result, debug


def _extract_footer_total_amount(lines: list[OcrLine], page_h: float, table_header_y: float | None) -> str:
    rows = _group_rows(lines)
    if not rows:
        return ""
    footer_start = max(page_h * 0.68, (table_header_y or 0) + page_h * 0.18)
    summary_rows: list[tuple[int, str, float]] = []
    for idx, row in enumerate(rows):
        text = _row_text(row)
        cy = _row_center_y(row)
        if cy < footer_start or cy > page_h * 0.94:
            continue
        if _row_has_item_context(text) and not _TABLE_SUMMARY_RE.search(text):
            continue
        if _TABLE_SUMMARY_RE.search(text) or _TOTAL_AMOUNT_ANCHOR_RE.search(text):
            summary_rows.append((idx, text, cy))

    candidates: list[tuple[float, int, str]] = []
    for idx, text, cy in summary_rows:
        neighborhood = [text]
        for near_idx in (idx - 1, idx + 1, idx + 2):
            if 0 <= near_idx < len(rows):
                near_text = _row_text(rows[near_idx])
                near_cy = _row_center_y(rows[near_idx])
                if abs(near_cy - cy) <= page_h * 0.055 and not _row_has_item_context(near_text):
                    neighborhood.append(near_text)
        blob = " ".join(neighborhood)
        for value in _amount_values(blob):
            numeric = int(value.replace(",", ""))
            score = 20.0
            if _TOTAL_AMOUNT_ANCHOR_RE.search(blob) or re.search(r"\ud569\s*\uacc4|\ud568\s*\uacc4|TOTAL", blob, re.I):
                score += 12
            if re.search(r"\uacf5\uae09\s*\uac00\uc561|\uacf5\uae09\s*\uae08\uc561|\uc138\s*\uc561|\ubd80\uac00\s*\uc138", blob):
                score += 5
            score += min(max((cy - footer_start) / max(page_h * 0.25, 1), 0), 1) * 6
            candidates.append((score, numeric, value))

    if not candidates:
        footer_lines = [
            line
            for line in lines
            if footer_start <= line.cy <= page_h * 0.94
            and not _row_has_item_context(line.text)
            and not _BIZ_RE.search(_canonical_digits(line.text))
            and not _PHONE_RE.search(line.text)
        ]
        for line in footer_lines:
            text = line.text
            if not (_TABLE_SUMMARY_RE.search(text) or _TOTAL_AMOUNT_ANCHOR_RE.search(text)):
                continue
            for value in _amount_values(text):
                candidates.append((18.0, int(value.replace(",", "")), value))

    if not candidates:
        return ""
    candidates.sort(key=lambda item: (-item[0], -item[1]))
    return candidates[0][2]


def _extract_amount_fields(
    lines: list[OcrLine],
    page_h: float,
    table_header_y: float | None,
    debug: dict[str, Any] | None = None,
) -> dict[str, str]:
    start_y = max((table_header_y or page_h * 0.45), page_h * 0.35)
    bottom = [line for line in lines if line.cy >= start_y]
    if not bottom:
        bottom = lines
    supply = _extract_amount_near(bottom, _SUPPLY_AMOUNT_ANCHOR_RE)
    tax = _extract_amount_near(bottom, _TAX_AMOUNT_ANCHOR_RE)
    if not supply:
        supply = _extract_amount_near_reading_order(lines, _SUPPLY_AMOUNT_ANCHOR_RE)
    if not tax:
        tax = _extract_amount_near_reading_order(lines, _TAX_AMOUNT_ANCHOR_RE)
    if supply and int(supply.replace(",", "")) < 10_000:
        supply = ""
    if tax and int(tax.replace(",", "")) < 10_000:
        tax = ""
    footer_total = _extract_footer_total_amount(lines, page_h, table_header_y)
    total = footer_total or _extract_amount_near(bottom, _TOTAL_AMOUNT_ANCHOR_RE)
    summary_triple, summary_debug = _extract_footer_summary_triple(lines, page_h, table_header_y, existing_total=total)
    pair_debug: dict[str, Any] = {}
    used_summary_triple = False
    if summary_triple:
        triple_total_num = int(summary_triple["totalAmount"].replace(",", ""))
        total_num = int(total.replace(",", "")) if total else 0
        if not total or _amounts_close(triple_total_num, total_num) or triple_total_num > total_num:
            supply = summary_triple["supplyAmount"]
            tax = summary_triple["taxAmount"]
            total = summary_triple["totalAmount"]
            used_summary_triple = True
        elif total_num and triple_total_num <= total_num * 5:
            supply = summary_triple["supplyAmount"]
            tax = summary_triple["taxAmount"]
            used_summary_triple = True
    values = _amount_values("\n".join(line.text for line in bottom))
    tail_max = max(values, key=lambda item: int(item.replace(",", ""))) if values else ""
    synthesized_total = ""
    if supply and tax:
        supply_num = int(supply.replace(",", ""))
        tax_num = int(tax.replace(",", ""))
        if supply_num > tax_num > 0:
            synthesized_total = f"{supply_num + tax_num:,}"
    if synthesized_total:
        synth_num = int(synthesized_total.replace(",", ""))
        total_num = int(total.replace(",", "")) if total else 0
        if not total or (synth_num > total_num and synth_num <= total_num * 5):
            total = synthesized_total
    total_num_for_pair = int(total.replace(",", "")) if total else 0
    weak_total = bool(total_num_for_pair and total_num_for_pair < 10_000 and not used_summary_triple)
    pair_summary, pair_debug = _infer_summary_pair_from_amount_pool(
        lines,
        total="" if weak_total else total,
        allow_synthesized_total=weak_total,
    )
    if pair_summary:
        pair_total_num = int(pair_summary.get("totalAmount", "0").replace(",", ""))
        current_total_num = int(total.replace(",", "")) if total else 0
        if weak_total or not total or (current_total_num and _amounts_close(pair_total_num, current_total_num)):
            supply = pair_summary.get("supplyAmount", supply)
            tax = pair_summary.get("taxAmount", tax)
            total = pair_summary.get("totalAmount", total)
            used_summary_triple = True
    if tail_max and (
        not total
        or (not synthesized_total and int(tail_max.replace(",", "")) > int(total.replace(",", "")) * 1.5)
    ):
        if not total or int(tail_max.replace(",", "")) > int(total.replace(",", "")):
            total = tail_max
    if total:
        total_num = int(total.replace(",", ""))
        supply_absurd = bool(supply and int(supply.replace(",", "")) > total_num * 5)
        if supply_absurd:
            supply = ""
        if supply_absurd and tax and int(tax.replace(",", "")) > total_num * 0.5:
            tax = ""
        if not used_summary_triple:
            if supply and tax:
                supply_num = int(supply.replace(",", ""))
                tax_num = int(tax.replace(",", ""))
                if supply_num > tax_num > 0 and not _amounts_close(supply_num + tax_num, total_num):
                    supply = ""
                    tax = ""
            if tax and int(tax.replace(",", "")) >= total_num * 0.3:
                tax = ""
            if supply and int(supply.replace(",", "")) >= total_num * 0.98:
                supply = ""
    if debug is not None:
        debug["amount_summary_triple"] = summary_debug
        debug["amount_pair_checksum"] = pair_debug
    return {"supplyAmount": supply, "taxAmount": tax, "totalAmount": total}


def _detect_table(lines: list[OcrLine], page_h: float, table_header_y: float | None) -> dict[str, str]:
    rows = _group_rows(lines)
    header_index = -1
    for idx, row in enumerate(rows):
        row_y = sum(item.cy for item in row) / len(row)
        if table_header_y is not None and abs(row_y - table_header_y) <= max(item.h for item in row) * 2:
            header_index = idx
            break
        if _table_token_count(_row_text(row)) >= 2:
            header_index = idx
            break

    table_detected = header_index >= 0
    data_rows: list[str] = _extract_table_row_texts(rows, page_h, header_index)
    if table_detected:
        header_y = max(item.cy for item in rows[header_index])
        for idx in range(header_index + 1, len(rows)):
            row = rows[idx]
            text = _row_text(row)
            row_y = sum(item.cy for item in row) / len(row)
            if row_y <= header_y or row_y >= page_h * 0.90:
                continue
            if _is_summary_row_for_items(text):
                break
            if _is_table_header_only_row(text):
                continue
            candidate = _table_data_candidate_text(rows, idx, page_h)
            if candidate:
                data_rows.append(candidate)
        data_rows = [text for text in _dedupe_table_rows(data_rows) if _is_valid_final_item_text(text)]

    if not data_rows:
        body_start = min((table_header_y or page_h * 0.25), page_h * 0.25)
        body_rows = [
            (idx, _row_text(row))
            for idx, row in enumerate(rows)
            if body_start <= sum(item.cy for item in row) / len(row) <= page_h * 0.88
        ]
        data_rows = [
            candidate
            for idx, _ in body_rows
            if (candidate := _table_data_candidate_text(rows, idx, page_h))
        ]
        if not data_rows:
            data_rows = [
                text
                for _, text in body_rows
                if re.search(r"\d", text)
                and len(text) >= 3
                and not _is_code_only_table_row(text)
                and not _is_numeric_detail_line(text)
                and not _is_table_header_only_row(text)
                and _table_row_score(text) > 0
            ]
        data_rows = [text for text in _dedupe_table_rows(data_rows) if _is_valid_final_item_text(text)]
        table_detected = table_detected or len(data_rows) >= 2

    if not data_rows:
        item_line_candidates: list[tuple[float, float, float, str]] = []
        numeric_lines = [
            line
            for line in lines
            if page_h * 0.18 <= line.cy <= page_h * 0.88
            and re.search(r"\d", line.text or "")
            and not _is_bad_table_data_row(line.text)
            and not _is_table_header_only_row(line.text)
        ]
        for line in lines:
            if not (page_h * 0.18 <= line.cy <= page_h * 0.88):
                continue
            text = _clean_value(line.text)
            if not _is_item_name_like(text):
                continue
            nearby = [
                item
                for item in numeric_lines
                if item is not line
                and (
                    (0 < item.cy - line.cy <= page_h * 0.12)
                    or abs(item.cy - line.cy) <= page_h * 0.04
                )
            ]
            nearby.sort(key=lambda item: (abs(item.cy - line.cy), item.x))
            if not nearby and not re.search(r"\d", text):
                continue
            preview = " ".join([text] + [item.text for item in nearby[:4]])
            score = _table_row_score(preview) + 10
            item_line_candidates.append((score, line.cy, line.x, preview))
        if item_line_candidates:
            item_line_candidates.sort(key=lambda item: (-item[0], item[1], item[2]))
            data_rows = [_summarize_table_row(item_line_candidates[0][3])]
            table_detected = True

    if not data_rows:
        line_candidates: list[tuple[float, float, float, str]] = []
        for line in lines:
            if not (page_h * 0.18 <= line.cy <= page_h * 0.88):
                continue
            text = _clean_value(line.text)
            if len(text) < 3 or not re.search(r"\d", text):
                continue
            if _is_code_only_table_row(text) or _is_numeric_detail_line(text):
                continue
            if _is_bad_table_data_row(text) or _is_table_header_only_row(text):
                continue
            if not re.search(r"[가-힣]", text) and not re.search(r"TABLET|CAPSULE|CAPS?|ABLET", text, re.I):
                continue
            score = _table_row_score(text)
            if _ITEM_NAME_HINT_RE.search(text):
                score += 8
            if score <= 2:
                continue
            line_candidates.append((score, line.cy, line.x, text))
        if line_candidates:
            line_candidates.sort(key=lambda item: (-item[0], item[1], item[2]))
            _, first_y, _, first_text = line_candidates[0]
            nearby = [
                (x, text)
                for _, cy, x, text in line_candidates
                if abs(cy - first_y) <= page_h * 0.08 and text != first_text
            ]
            nearby.sort(key=lambda item: item[0])
            preview = " ".join([first_text] + [text for _, text in nearby[:5]])
            data_rows = [_summarize_table_row(preview)]
            table_detected = True

    if not data_rows:
        data_rows = _text_order_table_fallback(lines)
        table_detected = table_detected or bool(data_rows)
    if not data_rows:
        data_rows = [
            _clean_value(line.text)
            for line in lines
            if 0 <= line.cy <= page_h * 0.92
            and _has_product_hint(line.text)
            and not _is_business_contact_line(line.text)
            and not _is_table_header_row(line.text)
            and not _is_summary_row_for_items(line.text)
        ]
        table_detected = table_detected or bool(data_rows)

    data_rows = [text for text in _dedupe_table_rows(data_rows) if _is_valid_final_item_text(text)]
    if not data_rows:
        data_rows = [
            _clean_value(line.text)
            for line in lines
            if 0 <= line.cy <= page_h * 0.92
            and _has_product_hint(line.text)
            and _is_valid_final_item_text(line.text)
        ]
    table_items = [_item_dict_from_row_text(text) for text in data_rows]
    table_detected = table_detected or bool(data_rows)
    return {
        "tableDetected": "Y" if table_detected else "N",
        "rowCount": str(len(data_rows)) if data_rows else "",
        "firstRowPreview": _summarize_table_row(data_rows[0]) if data_rows else "",
        "tableRows": table_items,
        "items": table_items,
    }


def extract_invoice_statement_fields(ocr_lines_raw: list[tuple], debug: dict[str, Any] | None = None) -> dict[str, str]:
    lines = [line for raw in ocr_lines_raw if (line := _line_from_raw(raw))]
    fields = {
        "supplierCompany": "",
        "supplierBizNumber": "",
        "supplierRepresentative": "",
        "supplierAddress": "",
        "buyerCompany": "",
        "buyerBizNumber": "",
        "buyerRepresentative": "",
        "buyerAddress": "",
        "issueDate": "",
        "supplyAmount": "",
        "taxAmount": "",
        "totalAmount": "",
        "tableDetected": "N",
        "rowCount": "",
        "firstRowPreview": "",
    }
    if not lines:
        return fields

    page_w = max(line.x + line.w for line in lines)
    page_h = max(line.y + line.h for line in lines)
    table_header_y = _find_table_header_y(lines, page_h)
    header_limit_y = min((table_header_y - page_h * 0.02) if table_header_y else page_h * 0.62, page_h * 0.68)
    header_limit_y = max(header_limit_y, page_h * 0.22)
    header_lines = [line for line in lines if line.cy <= header_limit_y]

    supplier, buyer, party_debug = _extract_party_fields(header_lines, lines, page_w, page_h, header_limit_y)
    amount_debug: dict[str, Any] = {}
    amounts = _extract_amount_fields(lines, page_h, table_header_y, debug=amount_debug)
    table = _detect_table(lines, page_h, table_header_y)
    full_text = "\n".join(line.text for line in lines)

    fields.update(
        {
            "supplierCompany": supplier["company"],
            "supplierBizNumber": supplier["bizNumber"],
            "supplierRepresentative": supplier["representative"],
            "supplierAddress": supplier["address"],
            "buyerCompany": buyer["company"],
            "buyerBizNumber": buyer["bizNumber"],
            "buyerRepresentative": buyer["representative"],
            "buyerAddress": buyer["address"],
            "issueDate": _normalize_date(full_text),
            **amounts,
            **table,
        }
    )

    if debug is not None:
        debug["invoice_statement"] = {
            "page_size": [round(page_w), round(page_h)],
            "table_header_y": round(table_header_y) if table_header_y else None,
            "header_limit_y": round(header_limit_y),
            "header_line_count": len(header_lines),
            "party_candidates": {
                **party_debug,
                "companies": [(round(x), round(y), value) for x, y, value in party_debug["companies"]],
            },
            "supplier_nonempty": [key for key, value in supplier.items() if value],
            "buyer_nonempty": [key for key, value in buyer.items() if value],
            "amount_nonempty": [key for key, value in amounts.items() if value],
            "amount_summary_triple": amount_debug.get("amount_summary_triple", {}),
            "amount_pair_checksum": amount_debug.get("amount_pair_checksum", {}),
            "table": table,
        }

    return fields
