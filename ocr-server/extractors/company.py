import re

from extractors.address import _extract_address_fragment
from extractors.business_number import _extract_biz_number
from extractors.common import _bad_top_text_candidate, _extract_until_next_label
from extractors.phone import _extract_phone_candidate
from extractors.representative import _extract_company_rep_from_slash
from utils.regex_patterns import (
    _PHONE_RE,
    _ADDR_START_RE, _FIELD_NOISE_RE,
    _COMPANY_SUFFIX_HINT_RE, _COMPANY_LABEL_RE, _COMPANY_CONTEXT_HINT_RE,
    _CONVENIENCE_STORE_NAME_RE, _COMPANY_SLOGAN_RE,
    _PERSON_LIKE_NAME_RE, _REPRESENTATIVE_SURNAME_RE,
    _ADDRESS_CUT_RE, _ADDRESS_CORE_TOKEN_RE,
    _LABEL_ONLY_RE,
)
from utils.rows import _row_text, _is_merchant_notice_row
from utils.text_normalize import _clean_inline_field_value

def _is_bad_company_candidate(text: str, row_text: str = "") -> bool:
    candidate = _clean_inline_field_value(text)
    compact = re.sub(r'\s+', '', candidate)
    row_compact = re.sub(r'\s+', '', row_text or '')
    has_label = bool(_COMPANY_LABEL_RE.search(row_text or ""))
    short_hangul_name = bool(re.fullmatch(r'[가-힣]{3,4}', compact))
    short_standalone_ok = (
        short_hangul_name
        and not has_label
        and not re.search(r'\d', row_compact)
        and not _FIELD_NOISE_RE.search(row_compact)
        and not _is_merchant_notice_row(row_text or "")
    )
    digits = sum(ch.isdigit() for ch in compact)
    amount_like_count = len(re.findall(r'\d{1,3}(?:,\d{3})+|\d{4,}', row_text or ""))

    if not compact:
        return True
    if _LABEL_ONLY_RE.fullmatch(compact):
        return True
    if _COMPANY_SLOGAN_RE.search(compact):
        return True
    if _bad_top_text_candidate(compact) or _FIELD_NOISE_RE.search(compact):
        return True
    if re.search(r'체크카드|신용매출|귀하', compact, re.I):
        return True
    if re.search(r'품명|상품명|상품|품목|수량|단가|금액|합계|총계|부가가치세|부가세|공급가액|판매금액|판매사원|판매시간|영수번호|승인|전표|TID|VAN|CAT|가맹(?:No|점번호|번호)', compact, re.I):
        return True
    if re.search(r'계좌|송금|출금|입금|잔액|수수료|거래명|거래일자|거래금액|거래후|수취인|창구|은행업무|스마트폰', compact, re.I):
        return True
    if re.search(r'일시불|일시물|할부|회원용|고객용|취소용|무서명|신용구매|매입사|카드종류', compact, re.I):
        return True
    if re.search(r'유통단지|호계동|오전동|고천동|동안구|의왕시|안양시|경기도', compact):
        return True
    if re.search(r'다른경우|실제와|가맹점주소가|전기작업|작업지시|직원|식지|재발행|안내문|설명문구|예시문구|작성문구', compact, re.I):
        return True
    if re.search(r'표시|입니다|과세|면세|품목', compact):
        return True
    if re.search(r'응원합니다|감사합니다|유치|박람회', compact):
        return True
    if re.fullmatch(r'[가-힣]{2,8}(?:시|군|구|동|로|길|층|호|번지)', compact) and not _COMPANY_SUFFIX_HINT_RE.search(compact):
        return True
    if _ADDRESS_CORE_TOKEN_RE.search(compact) and _ADDR_START_RE.search(compact) and not _COMPANY_SUFFIX_HINT_RE.search(compact):
        return True
    if re.search(r'\d.*(?:\uC0AC\uC625|\uBE4C\uB529)|(?:\uC0AC\uC625|\uBE4C\uB529)\)?$', compact) and not _COMPANY_SUFFIX_HINT_RE.search(compact):
        return True
    if digits > 1 and not _CONVENIENCE_STORE_NAME_RE.search(compact):
        return True
    if len(compact) <= 2 and not _COMPANY_SUFFIX_HINT_RE.search(compact):
        return True
    if len(compact) <= 4 and not short_standalone_ok and not has_label and not _COMPANY_SUFFIX_HINT_RE.search(compact):
        return True
    if _PERSON_LIKE_NAME_RE.fullmatch(compact) and _REPRESENTATIVE_SURNAME_RE.search(compact) and not _COMPANY_SUFFIX_HINT_RE.search(compact):
        return True
    if _PERSON_LIKE_NAME_RE.fullmatch(compact) and not short_standalone_ok and not _COMPANY_SUFFIX_HINT_RE.search(compact):
        return True
    if _FIELD_NOISE_RE.search(row_compact) and not has_label and not _CONVENIENCE_STORE_NAME_RE.search(compact):
        return True
    if amount_like_count >= 2 and not has_label and not re.search(r'사업자|등록번호|주소|전화|TEL|Tel|tel', row_text or "", re.I):
        return True
    return False


def _strip_company_label(text: str) -> str:
    value = text or ""
    match = _COMPANY_LABEL_RE.search(value)
    if match:
        value = value[match.end():]
    return re.sub(r'^\s*[:;：\-]*\s*', '', value).strip()


def _company_conflicts_with_known_fields(candidate: str, row_text: str = "", representative: str = "", address: str = "") -> bool:
    compact = re.sub(r'\s+', '', candidate or "")
    row_compact = re.sub(r'\s+', '', row_text or "")
    if not compact:
        return True
    if representative and compact == re.sub(r'\s+', '', representative):
        return True
    if address:
        addr_compact = re.sub(r'\s+', '', address)
        if compact and (compact in addr_compact or addr_compact in compact):
            return True
    if _ADDR_START_RE.search(candidate or "") and not _COMPANY_CONTEXT_HINT_RE.search(compact):
        return True
    if _PHONE_RE.search(row_text or "") and len(compact) <= 4 and not _COMPANY_CONTEXT_HINT_RE.search(compact):
        return True
    if _extract_biz_number(candidate or ""):
        return True
    if re.search(r'TEL|전화|FAX|사업자|등록번호|대표자|성명|주소|승인|전표|카드|은행|거래|품목|수량|단가|금액|합계|감사합니다|결제|매출전표|거래명세', row_compact, re.I):
        if not _COMPANY_LABEL_RE.search(row_text or "") and not _COMPANY_CONTEXT_HINT_RE.search(compact):
            return True
    return False




def _extract_company_near_biz(text: str) -> str:
    biz = re.search(r'[1-9]\d{2}[-\s.]?\d{2}[-\s.]?\d{5}', text or "")
    if not biz:
        return ""

    before = _clean_inline_field_value(_strip_company_label((text or "")[:biz.start()]))
    before_tokens = [
        token for token in re.findall(r'[가-힣A-Za-z0-9()]{2,}', before)
        if not _bad_top_text_candidate(token) and not _is_bad_company_candidate(token, text or "")
    ]
    if before_tokens and len(before_tokens[-1]) >= 3 and not _ADDR_START_RE.search(before_tokens[-1]):
        return before_tokens[-1]

    after = _clean_inline_field_value(_strip_company_label((text or "")[biz.end():]))
    after = _ADDRESS_CUT_RE.split(after, maxsplit=1)[0]
    after = _PHONE_RE.split(after, maxsplit=1)[0]
    addr_match = _ADDR_START_RE.search(after)
    if addr_match and addr_match.start() > 0:
        company = _clean_inline_field_value(after[:addr_match.start()])
        if 2 <= len(company) <= 20 and not _is_bad_company_candidate(company, text or ""):
            return company
    after_tokens = [
        token for token in re.findall(r'[가-힣A-Za-z0-9()]{2,}', after)
        if not _is_bad_company_candidate(token, text or "")
    ]
    if after_tokens:
        return after_tokens[0]
    return ""


def _normalize_company_candidate(text: str) -> str:
    value = _clean_inline_field_value(text)
    value = _strip_company_label(value)
    value = re.sub(r'^[\[\]{}<>]+', '', value)
    value = re.sub(r'[\[\]{}<>]+$', '', value)
    value = re.sub(r'^[^가-힣A-Za-z0-9(]+', '', value)
    value = re.sub(r'[^가-힣A-Za-z0-9()&.\s]', '', value)
    value = re.sub(r'\s+', '', value)
    value = re.sub(r'은누리약국$', '온누리약국', value)
    value = re.sub(r'칠물$', '철물', value)
    value = re.sub(r'놀트$', '볼트', value)
    if value == "성울집":
        return "서울집"
    if value in {"화성들", "화성률"}:
        return "화성툴"
    return value


def _company_candidate_score(text: str, row_text: str, y_ratio: float, source: str, near_info: bool) -> float:
    candidate = _normalize_company_candidate(text)
    if not candidate or _is_bad_company_candidate(candidate, row_text):
        return -999.0
    if _company_conflicts_with_known_fields(candidate, row_text):
        return -999.0
    if len(candidate) < 2 or len(candidate) > 20:
        return -999.0

    hangul = sum(1 for ch in candidate if '가' <= ch <= '힣')
    digits = sum(1 for ch in candidate if ch.isdigit())
    hangul_ratio = hangul / max(len(candidate), 1)
    convenience_store = bool(_CONVENIENCE_STORE_NAME_RE.search(candidate))
    if digits > 1 and not convenience_store:
        return -999.0

    score = 0.0
    score += hangul_ratio * 22
    score += max(0.0, 1.0 - y_ratio) * 8
    if source == "upper_block":
        score += 2.0
    if near_info:
        score += 8.0
    if _COMPANY_SUFFIX_HINT_RE.search(candidate):
        score += 8.0
    if _COMPANY_CONTEXT_HINT_RE.search(candidate):
        score += 7.0
    if _COMPANY_LABEL_RE.search(row_text or ""):
        score += 12.0
    if _extract_biz_number(row_text or ""):
        score += 10.0
    if convenience_store:
        score += 18.0
    if 2 <= hangul <= 6:
        score += 3.0
    return score


def _company_candidate_texts(row_text: str) -> list[tuple[str, bool]]:
    text = _clean_inline_field_value(row_text)
    if not text:
        return []
    if _is_merchant_notice_row(text):
        return []

    candidates: list[tuple[str, bool]] = []
    compact_text = re.sub(r'\s+', '', text)
    normalized_compact = _normalize_company_candidate(compact_text)
    # 영문 단독 브랜드명 허용: PARIS BAGUETTE, STARBUCKS 등 suffix 없는 국제 브랜드
    english_brand_only = bool(
        re.fullmatch(r'[A-Za-z]+', compact_text)
        and not re.search(r'체크카드|신용매출|귀하|카드|van|tid|cat|ibk|nh|cashier|server|station|table|order', compact_text, re.I)
    )
    if (
        3 <= len(compact_text) <= 18
        and not re.search(r'\d', compact_text)
        and not _FIELD_NOISE_RE.search(compact_text)
        and (_COMPANY_CONTEXT_HINT_RE.search(normalized_compact) or english_brand_only)
        and not re.search(r'체크카드|신용매출|귀하|카드|^no\.?', compact_text, re.I)
    ):
        candidates.append((text, False))
    has_info = bool(re.search(r'주소|TEL|Tel|tel|전화|사업자|등록번호', text))

    company, _ = _extract_company_rep_from_slash(text)
    if company:
        candidates.append((company, True))

    labeled = _extract_until_next_label(text, _COMPANY_LABEL_RE.pattern)
    if labeled and not _is_merchant_notice_row(text):
        candidates.append((labeled, True))

    near_biz = _extract_company_near_biz(text)
    if near_biz:
        candidates.append((near_biz, True))

    for token in re.findall(r'[가-힣A-Za-z0-9()]{2,}', text):
        normalized_token = _normalize_company_candidate(token)
        if has_info or _COMPANY_CONTEXT_HINT_RE.search(normalized_token) or _COMPANY_SUFFIX_HINT_RE.search(normalized_token):
            candidates.append((token, has_info))
        else:
            # T-19a: 한글 뒤에 괄호/숫자가 붙은 복합 토큰(예: 상호명(영문)123)에서
            # 한글 접두어만 분리하여 company hint 체크 — 상호 suffix 감지 가능
            kr_prefix_m = re.match(r'^([가-힣]{3,})', token)
            if kr_prefix_m:
                kr_prefix = kr_prefix_m.group(1)
                kr_norm = _normalize_company_candidate(kr_prefix)
                if _COMPANY_CONTEXT_HINT_RE.search(kr_norm) or _COMPANY_SUFFIX_HINT_RE.search(kr_norm):
                    candidates.append((kr_prefix, has_info))

    return candidates


def _rescue_company_name(
    full_rows,
    upper_rows,
    current: str = "",
    representative: str = "",
    doc_type: str = "unknown",
) -> tuple[str, str]:
    if doc_type == "bank_slip":
        return "", ""

    scored: list[tuple[float, str, str]] = []

    def _row_y_ratio(row) -> float:
        ys = [p[1] for line in row for p in line[0]]
        if not ys:
            return 0.5
        return min(1.0, max(0.0, ((min(ys) + max(ys)) / 2) / 1000.0))

    for source, rows in (("upper_block", upper_rows or []), ("full_ocr", full_rows or [])):
        for idx, row in enumerate(rows):
            row_text = _row_text(row)
            y_ratio = _row_y_ratio(row)
            prev_text = _row_text(rows[idx - 1]) if idx > 0 else ""
            next_text = _row_text(rows[idx + 1]) if idx + 1 < len(rows) else ""
            adjacent_blob = prev_text + " " + next_text
            adjacent_info = bool(
                _extract_biz_number(adjacent_blob)
                or _extract_phone_candidate(adjacent_blob)
                or _extract_address_fragment(adjacent_blob)
            )
            # near_biz_context: ±2 행 윈도우로 확장 (영수증 상단 브랜드명과 사업자번호 행이 2행 이상 떨어질 수 있음)
            ctx_start = max(0, idx - 2)
            ctx_end = min(len(rows), idx + 3)
            ctx_blob = " ".join(_row_text(rows[i]) for i in range(ctx_start, ctx_end))
            near_biz_context = bool(_extract_biz_number(ctx_blob))
            for candidate, near_info in _company_candidate_texts(row_text):
                normalized = _normalize_company_candidate(candidate)
                if representative and normalized == re.sub(r'\s+', '', representative):
                    continue
                score = _company_candidate_score(normalized, row_text, y_ratio, source, near_info or adjacent_info)
                if near_biz_context:
                    score += 10.0
                if score > -100:
                    scored.append((score, normalized, source))

    if current:
        normalized = _normalize_company_candidate(current)
        score = _company_candidate_score(normalized, current, 0.2, "current", True)
        if score > -100 and normalized != re.sub(r'\s+', '', representative or ""):
            scored.append((score + 1.0, normalized, "company_rescue"))

    if not scored:
        return "", ""

    scored.sort(key=lambda item: (-item[0], len(item[1])))
    best_score, best_value, best_source = scored[0]
    if best_score < 12:
        return "", ""
    return best_value, best_source


