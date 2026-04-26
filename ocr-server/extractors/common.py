import re

from utils.text_normalize import _clean_inline_field_value
from utils.regex_patterns import _NEXT_LABEL_RE


def _extract_until_next_label(text: str, pattern: str) -> str:
    match = re.search(pattern, text, re.I)
    if not match:
        return ""
    value = text[match.end():]
    value = _NEXT_LABEL_RE.split(value, maxsplit=1)[0]
    return _clean_inline_field_value(value)


def _bad_top_text_candidate(text: str) -> bool:
    if re.search(r'다른경우|실제와|가맹점주소가|전기작업|작업지시|직원|식지|재발행|체크카드|신용매출|귀하|안내문|설명문구|예시문구|작성문구', text or "", re.I):
        return True
    return bool(re.search(
        r'신고안내|여신금융|협회|고객센터|승인번호|카드번호|거래일시|매출전표|'
        r'공급가액|부가세|합계|총계|품목|수량|단가|금액|van|tid|cat|ibk|nh',
        text or "",
        re.I,
    ))
