import re

from extractors.common import _bad_top_text_candidate
from extractors.phone import _format_phone_digits
from utils.regex_patterns import (
    _LABEL_ONLY_RE,
    _PHONE_ADMIN_NOISE_RE,
    _REPRESENTATIVE_COMPANYISH_RE,
    _REPRESENTATIVE_LABEL_ANCHOR_RE,
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
    if re.search(r'점|길|로|동|층|호|마트|카페|약국|툴|집$', candidate):
        return True
    if _REPRESENTATIVE_COMPANYISH_RE.search(candidate):
        return True
    return False


def _is_person_like_name(token: str) -> bool:
    """anchor 없이 단독 후보로 채택 가능한지 — 더 엄격한 조건 (precision 우선)."""
    if not token:
        return False
    candidate = re.sub(r'\s+', '', _clean_inline_field_value(token))
    if not re.fullmatch(r'[가-힣]{3,4}', candidate):
        return False
    if not _REPRESENTATIVE_SURNAME_RE.search(candidate):
        return False
    if _REPRESENTATIVE_NOISE_RE.search(candidate):
        return False
    if _REPRESENTATIVE_COMPANYISH_RE.search(candidate):
        return False
    if re.search(r'점|길|로|동|층|호|마트|카페|약국|툴', candidate):
        return False
    if re.search(r'[시군구읍면리동가]$', candidate):
        return False
    if re.search(r'(?:시|군|구|읍|면|리|동|로|길)\s*$', candidate):
        return False
    return True


def _row_has_business_hint(row_text: str) -> bool:
    if not row_text:
        return False
    if re.search(r'사업자|등록번호|가맹점|TEL|Tel|tel|전화', row_text):
        return True
    if re.search(r'[1-9]\d{2}[-\s.]?\d{2}[-\s.]?\d{5}', row_text):
        return True
    if re.search(r'0\d{1,2}[-\s.]?\d{3,4}[-\s.]?\d{4}', row_text):
        return True
    if re.search(r'\(주\)|주식회사|철물|조명|전기|공구|볼트|약국|카페|마트|편의점|스토어|매장|툴', row_text):
        return True
    return False


def _extract_lone_person_name_row(
    rows_text: list[str],
    row_index: int,
    target_company: str = "",
    target_address: str = "",
) -> str:
    """행 자체가 한글 3~4자 이름 단독일 때, 인접 행에 사업자/회사 hint가 있으면 채택.

    조건:
      - 라벨이 없는 lone-name 경로이므로 precision 우선 (3~4자만 허용, 2자 제외)
      - 회사명/주소 substring과 충돌하면 거부
      - 인접 행(prev OR next, 최대 2칸 이내)에 business hint 필요
    """
    if row_index < 0 or row_index >= len(rows_text):
        return ""
    raw = (rows_text[row_index] or "").strip()
    if not raw:
        return ""
    if _bad_top_text_candidate(raw):
        return ""
    cleaned = _clean_inline_field_value(raw)
    compact = re.sub(r'\s+', '', cleaned)
    if not compact or not _is_person_like_name(compact):
        return ""
    company_compact = re.sub(r'\s+', '', target_company or "")
    if company_compact and (compact in company_compact or company_compact in compact):
        return ""
    addr_compact = re.sub(r'\s+', '', target_address or "")
    if addr_compact and compact in addr_compact:
        return ""
    if _REPRESENTATIVE_LABEL_ANCHOR_RE.search(raw):
        return ""

    has_hint = False
    for offset in (-2, -1, 1, 2):
        idx = row_index + offset
        if 0 <= idx < len(rows_text) and _row_has_business_hint(rows_text[idx] or ""):
            has_hint = True
            break
    if not has_hint:
        return ""
    return compact


def _fill_lone_representative_from_lines(
    target: dict,
    rows_text: list[str],
    representative_key: str = "대표자",
    company_key: str = "회사명",
    address_key: str = "주소",
) -> None:
    if target.get(representative_key) or len(rows_text) < 2:
        return
    for row_index in range(len(rows_text)):
        lone = _extract_lone_person_name_row(
            rows_text,
            row_index,
            target_company=target.get(company_key, ""),
            target_address=target.get(address_key, ""),
        )
        if lone and not _is_bad_representative_candidate(lone, rows_text[row_index]):
            target[representative_key] = lone
            break


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
