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
_DATE_RE = re.compile(
    r"(?<!\d)(\d{4})\s*\ub144\s*(\d{1,2})\s*\uc6d4\s*(\d{1,2})\s*\uc77c"
    r"|(?<!\d)(\d{4})[.\-/]\s*(\d{1,2})[.\-/]\s*(\d{1,2})(?!\d)"
    r"|(?<!\d)(\d{2})[.\-/]\s*(\d{1,2})[.\-/]\s*(\d{1,2})(?!\d)"
)
_SUPPLY_AMOUNT_ANCHOR_RE = re.compile(r"\uacf5\uae09\s*\uac00\uc561")
_TAX_AMOUNT_ANCHOR_RE = re.compile(r"\uc138\s*\uc561|\ubd80\uac00\s*\uc138|\ubd80\uac00\s*\uc11c")
_TOTAL_AMOUNT_ANCHOR_RE = re.compile(
    r"\ud569\uacc4\s*\uae08\uc561|\ucd1d\s*\uacb0\uc81c\uc561|\uacf5\uae09\s*\ub300\uac00|"
    r"\uccad\uad6c\s*\uae08\uc561|\ucd1d\s*\ud569\uacc4"
)
_TABLE_SUMMARY_RE = re.compile(
    r"\uacf5\uae09\s*\uae08\uc561|\uacf5\uae09\s*\uac00\uc561|\uacf5\uae09\s*\uac00\ub825|\uc138\s*\uc561|\ubd80\uac00\s*\uc138|"
    r"\ud569\s*\uacc4|\ud568\s*\uacc4|\ud569\uacc4\s*\uae08\uc561|\ucd1d\s*\uacb0\uc81c\uc561|"
    r"\uacf5\uae09\s*\ub300\uac00|\uccad\uad6c\s*\uae08\uc561|\uc794\s*\uc561|\ub204\s*\uacc4|"
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


def _is_bad_table_data_row(text: str) -> bool:
    compact = re.sub(r"\s+", "", text or "")
    return bool(
        not compact
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
    token_count = _table_token_count(compact)
    digit_count = len(re.findall(r"\d", compact))
    return token_count >= 2 and digit_count <= 1


def _is_item_name_like(text: str) -> bool:
    compact = re.sub(r"\s+", "", text or "")
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
    return bool(
        re.fullmatch(r"[A-Z]{2,}[A-Z0-9_\-/.]{2,18}", compact)
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
    elif not supplier["company"] and len(remaining) >= 2:
        remaining.sort(key=lambda item: item[0])
        supplier["company"] = remaining[0][1]
    elif not buyer["company"] and len(remaining) >= 2:
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

    return supplier, buyer, {
        "companies": companies,
        "bizs": [(round(x), round(y), value) for x, y, value, _ in bizs],
        "split_x": split_x,
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


def _extract_amount_fields(lines: list[OcrLine], page_h: float, table_header_y: float | None) -> dict[str, str]:
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
    data_rows: list[str] = []
    if table_detected:
        header_y = max(item.cy for item in rows[header_index])
        for idx in range(header_index + 1, len(rows)):
            row = rows[idx]
            text = _row_text(row)
            row_y = sum(item.cy for item in row) / len(row)
            if row_y <= header_y or row_y >= page_h * 0.90:
                continue
            if _TOTAL_AMOUNT_ANCHOR_RE.search(text) or _TABLE_SUMMARY_RE.search(text):
                break
            if _is_table_header_only_row(text):
                continue
            candidate = _table_data_candidate_text(rows, idx, page_h)
            if candidate:
                data_rows.append(candidate)

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
                and not _is_table_header_only_row(text)
                and _table_row_score(text) > 0
            ]
        data_rows.sort(key=lambda text: _table_row_score(text), reverse=True)
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

    return {
        "tableDetected": "Y" if table_detected else "N",
        "rowCount": str(len(data_rows)) if data_rows else "",
        "firstRowPreview": _summarize_table_row(data_rows[0]) if data_rows else "",
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
    amounts = _extract_amount_fields(lines, page_h, table_header_y)
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
            "table": table,
        }

    return fields
