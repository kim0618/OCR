import re

from extractors.common import _bad_top_text_candidate
from extractors.phone import _format_phone_digits
from utils.regex_patterns import (
    _LABEL_ONLY_RE,
    _PHONE_ADMIN_NOISE_RE,
    _REPRESENTATIVE_NOISE_RE,
    _REPRESENTATIVE_SURNAME_RE,
)
from utils.text_normalize import _clean_inline_field_value


def _extract_rep_phone_pair(text: str) -> tuple[str, str]:
    raw = text or ""
    match = re.search(r'([가-힣]{2,4})\s*[\(:]\s*(0\d{8,10})\s*\)?', raw)
    if not match or _PHONE_ADMIN_NOISE_RE.search(raw):
        return "", ""
    representative = match.group(1)
    phone = _format_phone_digits(match.group(2))
    if _is_bad_representative_candidate(representative, raw):
        representative = ""
    return representative, phone


def _is_bad_representative_candidate(text: str, row_text: str = "") -> bool:
    candidate = re.sub(r'\s+', '', _clean_inline_field_value(text))
    if not candidate:
        return True
    if _LABEL_ONLY_RE.fullmatch(candidate):
        return True
    if _REPRESENTATIVE_NOISE_RE.search(candidate) or _REPRESENTATIVE_NOISE_RE.search(row_text or ""):
        return True
    if not re.fullmatch(r'[가-힣]{2,4}', candidate):
        return True
    if not _REPRESENTATIVE_SURNAME_RE.search(candidate):
        return True
    if re.search(r'점|길|로|동|층|호|마트|카페|약국', candidate):
        return True
    return False


def _extract_company_rep_from_slash(text: str) -> tuple[str, str]:
    if re.search(r'IBK|NH|신고안내|여신금융|주소|성명|대표자|사업자', text or "", re.I):
        return "", ""
    match = re.search(r'([가-힣A-Za-z0-9()&.\s]{2,24})\s*/\s*([가-힣]{2,4})', text or "")
    if not match:
        return "", ""
    company = _clean_inline_field_value(match.group(1))
    representative = _clean_inline_field_value(match.group(2))
    if _bad_top_text_candidate(company) or _bad_top_text_candidate(representative):
        return "", ""
    return company, representative
