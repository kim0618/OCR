import re

from utils.text_normalize import _clean_inline_field_value
from utils.rows import _row_text, _is_merchant_notice_row
from utils.regex_patterns import (
    _PHONE_RE,
    _ADDR_START_RE, _FIELD_NOISE_RE,
    _ADDRESS_CUT_RE, _ADDRESS_CORE_TOKEN_RE, _ADDRESS_STORE_NOISE_RE,
    _ADDRESS_LABEL_RE, _ADDRESS_CONTINUATION_RE,
    _ADDRESS_BROAD_ONLY_RE, _ADDRESS_TRAILING_NOISE_RE,
)
from extractors.common import _bad_top_text_candidate
from extractors.business_number import _extract_biz_number
from extractors.phone import _extract_phone_candidate

def _strip_address_label(text: str) -> str:
    value = text or ""
    match = _ADDRESS_LABEL_RE.search(value)
    if match:
        value = value[match.end():]
    return re.sub(r'^\s*[:;：\-]*\s*', '', value).strip()


def _extract_address_fragment(text: str) -> str:
    source = _strip_address_label(text or "")
    match = _ADDR_START_RE.search(source)
    if not match:
        return ""
    value = source[match.start():]
    value = _ADDRESS_CUT_RE.split(value, maxsplit=1)[0]
    value = _PHONE_RE.split(value, maxsplit=1)[0]
    value = re.split(r'\s*\d{4}[./-]\d{1,2}[./-]\d{1,2}', value, maxsplit=1)[0]
    value = re.sub(r'\d{2,3}[-\s.]?\d{2}[-\s.]?\d{5}.*$', '', value).strip()
    return _clean_inline_field_value(value)


def _address_token_score(text: str) -> int:
    compact = re.sub(r'\s+', '', text or "")
    score = len(re.findall(r'시|도|군|구|읍|면|동|리|가|로|길|번길|층|호|번지', compact))
    if re.search(r'\d+(?:-\d+)?', compact):
        score += 1
    if re.search(r'\([가-힣A-Za-z0-9\s.-]{1,18}\)', text or ""):
        score += 1
    return score


def _address_has_too_much_noise(text: str) -> bool:
    compact = re.sub(r'\s+', '', text or "")
    if not compact:
        return True
    noise_hits = len(re.findall(
        r'대표자|성명|상호|회사명|업체명|사업자|등록번호|TEL|전화|FAX|카드|은행|승인|전표|품목|상품명|수량|단가|금액|합계|안내|고객센터',
        compact,
        re.I,
    ))
    token_score = _address_token_score(compact)
    return noise_hits >= 2 or (noise_hits >= 1 and token_score < 3)


def _address_business_context_score(text: str) -> int:
    compact = re.sub(r'\s+', '', text or "")
    score = 0
    if _extract_biz_number(text or "") or re.search(r'사업자|등록번호', compact):
        score += 3
    if _extract_phone_candidate(text or "") or re.search(r'TEL|전화|FAX', compact, re.I):
        score += 2
    if re.search(r'대표자|성명|상호|회사명|업체명|가맹점명|매장명', compact):
        score += 2
    if _ADDRESS_LABEL_RE.search(text or ""):
        score += 3
    return score


def _address_candidate_score(candidate: str, row_text: str = "", adjacent_text: str = "", source: str = "full_ocr", y_ratio: float = 0.5) -> float:
    value = _clean_address_candidate(candidate)
    if not value:
        return -999.0
    compact = re.sub(r'\s+', '', value)
    row_blob = f"{row_text or ''} {adjacent_text or ''}"
    if _is_merchant_notice_row(row_blob) or _address_has_too_much_noise(row_blob):
        return -999.0
    if re.search(r'품목|상품명|수량|단가|금액|합계|총계|부가세|공급가액|판매금액|봉사료|승인|전표|카드번호|매입사|거래일시|TID|CAT|VANKEY', row_blob, re.I):
        if not _ADDRESS_LABEL_RE.search(row_text or ""):
            return -999.0

    token_score = _address_token_score(value)
    score = token_score * 8.0
    score += 10.0 if _ADDR_START_RE.search(value) else 0.0
    score += 8.0 if re.search(r'(?:로|길|번길)\s*\d+(?:-\d+)?|(?:동|리)\s*\d+(?:-\d+)?|\d+\s*(?:층|호)', compact) else 0.0
    score += 12.0 if _ADDRESS_LABEL_RE.search(row_text or "") else 0.0
    score += 12.0 if source == "upper_block" else 0.0
    score += max(0.0, 1.0 - y_ratio) * 8.0
    score += min(_address_business_context_score(row_blob), 6) * 3.0
    if len(compact) < 10:
        score -= 8.0
    if len(compact) > 70:
        score -= 10.0
    return score


def _is_split_gyeonggi_prefix_line(text: str) -> bool:
    return (text or "").strip() == "경"


def _is_split_gyeonggi_address_tail(text: str) -> bool:
    raw = (text or "").strip()
    if len(raw) < 8 or not raw.startswith("기"):
        return False

    compact = re.sub(r"\s+", "", raw)
    if re.search(
        r"승인|승인번호|카드|전표|거래일시|가맹|가맹NO|가맹No|판매금액|부가세|부가가치세|합계|총액|TEL|Tel|tel|전화",
        compact,
        re.I,
    ):
        return False
    if _extract_biz_number(raw) or _extract_phone_candidate(raw):
        return False
    if re.fullmatch(r"기?\s*\d{1,3}(?:,\d{3})+(?:원)?", raw):
        return False

    body = raw[1:].strip()
    if len(body) < 6:
        return False
    has_admin = bool(re.search(r"시|군|구", body))
    has_core = bool(re.search(r"번길|동|읍|면|리|로|길", body))
    return has_admin and has_core


def _merge_split_gyeonggi_address_candidate(prefix_line: str, tail_line: str) -> str:
    if not _is_split_gyeonggi_prefix_line(prefix_line) or not _is_split_gyeonggi_address_tail(tail_line):
        return ""
    body = (tail_line or "").strip()[1:].strip()
    if not body:
        return ""
    return re.sub(r"\s+", " ", f"경기 {body}").strip()


def _split_gyeonggi_address_repairs(row_texts: list[str]) -> dict[int, list[str]]:
    repairs: dict[int, list[str]] = {}
    for idx in range(len(row_texts) - 1):
        current = row_texts[idx]
        nxt = row_texts[idx + 1]

        merged = _merge_split_gyeonggi_address_candidate(current, nxt)
        if merged:
            repairs.setdefault(idx, []).append(merged)
            continue

        # Some OCR row grouping returns the visual pair in reverse order.
        merged = _merge_split_gyeonggi_address_candidate(nxt, current)
        if merged:
            repairs.setdefault(idx, []).append(merged)
    return repairs




def _clean_address_candidate(text: str) -> str:
    value = _clean_inline_field_value(_strip_address_label(text))
    if not value:
        return ""
    value = _ADDRESS_CUT_RE.split(value, maxsplit=1)[0]
    value = _PHONE_RE.split(value, maxsplit=1)[0]
    value = re.split(r'\s*\d{4}[./-]\d{1,2}[./-]\d{1,2}', value, maxsplit=1)[0]
    value = re.sub(r'\d{2,3}[-\s.]?\d{2}[-\s.]?\d{5}.*$', '', value).strip()
    value = _ADDRESS_TRAILING_NOISE_RE.split(value, maxsplit=1)[0]
    value = re.sub(r'\s*\((?:일시불|일시물|할부|승인|취소|고객용|회원용)[^)]*\).*$','', value, flags=re.I).strip()
    value = re.sub(r'\s+[일업전상공]$', '', value).strip()
    value = _clean_inline_field_value(value)
    region_match = _ADDR_START_RE.search(value)
    if region_match and region_match.start() > 0:
        value = _clean_inline_field_value(value[region_match.start():])
    value = re.sub(r'\s+[A-Z]\d{2,}\s+', ' ', value).strip()
    if _address_has_too_much_noise(value):
        return ""
    has_region = bool(_ADDR_START_RE.search(value))
    if not has_region:
        return ""
    compact = re.sub(r'\s+', '', value)
    if len(compact) < 6 or len(compact) > 90:
        return ""
    tail = value[2:]
    if not _ADDRESS_CORE_TOKEN_RE.search(tail):
        return ""
    if _address_token_score(value) < 2 and not re.search(r'\d+(?:-\d+)?', value):
        return ""
    if _ADDRESS_STORE_NOISE_RE.search(value) and not _ADDRESS_CORE_TOKEN_RE.search(tail):
        return ""
    value = re.sub(r'\s+[A-Z]{2,}\d+[A-Z0-9-]*$', '', value).strip()
    value = re.sub(r'\s+[A-Za-z]{2,}\d{2,}[A-Za-z0-9-]*$', '', value).strip()
    value = re.sub(r'(?<=\d)\s+[가-힣]{2,}(?:조명|전기|철물|공구|볼트|약국|집|툴)?$', '', value).strip()
    value = re.sub(r'[\[\]{}<>]+$', '', value).strip()
    return value


def _address_needs_continuation(value: str) -> bool:
    compact = re.sub(r'\s+', ' ', value or '').strip()
    if not compact:
        return False
    if compact.count("(") > compact.count(")"):
        return True
    if re.search(r'[,，]\s*$', compact):
        return True
    if _ADDRESS_BROAD_ONLY_RE.fullmatch(compact):
        return True
    if re.search(r'\([^)]+$', compact):
        return True
    if re.search(r'(?:로|길|번길)\s*\d+(?:-\d+)?$', compact):
        return True
    return not bool(re.search(r'로|길|번길|동|읍|면|리|가|층|호|번지|\d', compact[2:]))


def _address_continuation_candidate(text: str) -> str:
    raw = _strip_address_label(text or "")
    raw = _ADDRESS_CUT_RE.split(raw, maxsplit=1)[0]
    raw = _PHONE_RE.split(raw, maxsplit=1)[0]
    raw = _ADDRESS_TRAILING_NOISE_RE.split(raw, maxsplit=1)[0]
    raw = _clean_inline_field_value(raw)
    if not raw or _ADDR_START_RE.search(raw):
        return ""
    if re.search(r'일시불|일시물|할부|승인|취소|고객용|회원용|매입사|카드', raw, re.I):
        return ""
    if _bad_top_text_candidate(raw) or _FIELD_NOISE_RE.search(raw):
        return ""
    if _address_has_too_much_noise(raw):
        return ""
    if re.fullmatch(r'\([가-힣A-Za-z0-9,.\-\s]{1,30}\)|[가-힣A-Za-z0-9\s]{1,12}\)', raw):
        return raw
    if re.fullmatch(r'(?:\d+\s*)?층|[가-힣A-Za-z0-9(),.\-\s]{1,18}(?:동|층|호)|제\s*\d+\s*호', raw):
        return raw
    match = _ADDRESS_CONTINUATION_RE.search(raw)
    if not match:
        return ""
    value = _clean_inline_field_value(match.group(0))
    if len(value) < 3:
        return ""
    return value


def _extend_address_with_following_lines(address: str, lines: list[str], start_index: int, max_lines: int = 2) -> str:
    best = address
    if not best or not _address_needs_continuation(best):
        return best
    for offset in range(1, max_lines + 1):
        next_index = start_index + offset
        if next_index >= len(lines):
            break
        cont = _address_continuation_candidate(lines[next_index])
        if not cont:
            break
        combined = _clean_address_candidate(f"{best} {cont}")
        if not combined or len(re.sub(r'\s+', '', combined)) <= len(re.sub(r'\s+', '', best)):
            break
        best = combined
        if not _address_needs_continuation(best):
            break
    return best


def _maybe_set_address(target: dict, candidate: str) -> None:
    if not candidate:
        return
    current = target.get("주소", "")
    if not current:
        target["주소"] = candidate
        return
    if _address_needs_continuation(current) and len(candidate) > len(current):
        target["주소"] = candidate


def _best_address_from_rows(rows, source: str = "full_ocr") -> tuple[str, float, str]:
    if not rows:
        return "", -999.0, ""

    row_texts = [_row_text(r) for r in rows]
    split_gyeonggi_repairs = _split_gyeonggi_address_repairs(row_texts)

    def _row_y_ratio(row) -> float:
        ys = [p[1] for line in row for p in line[0]]
        if not ys:
            return 0.5
        return min(1.0, max(0.0, ((min(ys) + max(ys)) / 2) / 1000.0))

    scored: list[tuple[float, str, str]] = []
    for idx, row in enumerate(rows):
        row_text = row_texts[idx]
        if not row_text or _is_merchant_notice_row(row_text):
            continue
        prev_text = row_texts[idx - 1] if idx > 0 else ""
        next_text = row_texts[idx + 1] if idx + 1 < len(row_texts) else ""
        adjacent = f"{prev_text} {next_text}"
        y_ratio = _row_y_ratio(row)

        raw_candidates = [
            _extract_address_fragment(row_text),
            row_text,
        ]
        raw_candidates.extend(split_gyeonggi_repairs.get(idx, []))
        if idx + 1 < len(row_texts):
            raw_candidates.append(f"{row_text} {row_texts[idx + 1]}")
        if idx + 2 < len(row_texts):
            raw_candidates.append(f"{row_text} {row_texts[idx + 1]} {row_texts[idx + 2]}")

        for raw in raw_candidates:
            addr = _clean_address_candidate(raw)
            if not addr:
                continue
            addr = _extend_address_with_following_lines(addr, row_texts, idx)
            score = _address_candidate_score(addr, row_text, adjacent, source, y_ratio)
            if score > -100:
                scored.append((score, addr, source))

    if not scored:
        return "", -999.0, ""
    scored.sort(key=lambda item: (-item[0], -len(re.sub(r'\s+', '', item[1]))))
    best_score, best_addr, best_source = scored[0]
    return best_addr, best_score, best_source


def _rescue_address_candidate(
    full_rows,
    upper_rows,
    current: str = "",
) -> tuple[str, str]:
    candidates: list[tuple[float, str, str]] = []
    upper_addr, upper_score, upper_source = _best_address_from_rows(upper_rows or [], "upper_block")
    if upper_addr:
        candidates.append((upper_score, upper_addr, upper_source))
    full_addr, full_score, full_source = _best_address_from_rows(full_rows or [], "full_ocr")
    if full_addr:
        candidates.append((full_score, full_addr, full_source))
    if current:
        current_score = _address_candidate_score(current, current, "", "current", 0.2)
        if current_score > -100:
            candidates.append((current_score + 2.0, current, "current"))
    if not candidates:
        return "", ""

    candidates.sort(key=lambda item: (-item[0], -len(re.sub(r'\s+', '', item[1]))))
    best_score, best_addr, best_source = candidates[0]
    current_score = _address_candidate_score(current, current, "", "current", 0.2) if current else -999.0
    current_len = len(re.sub(r'\s+', '', current or ""))
    best_len = len(re.sub(r'\s+', '', best_addr or ""))
    if not current:
        return (best_addr, best_source) if best_score >= 26 else ("", "")
    if best_addr == current:
        return "", ""
    if _address_needs_continuation(current) and best_len > current_len and best_score >= current_score:
        return best_addr, best_source
    if best_score >= current_score + 12 and best_len >= max(10, current_len - 4):
        return best_addr, best_source
    return "", ""


