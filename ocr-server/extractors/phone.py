import re

from utils.regex_patterns import _PHONE_LABELED_RE, _PHONE_ADMIN_NOISE_RE


def _normalize_phone_digits(text: str) -> str:
    return re.sub(r'\D', '', text or '')


def _format_phone_digits(digits: str) -> str:
    if len(digits) == 8 and digits.startswith("02"):
        return f"{digits[:2]}-{digits[2:4]}-{digits[4:]}"
    if len(digits) == 9 and digits.startswith("02"):
        return f"{digits[:2]}-{digits[2:5]}-{digits[5:]}"
    if len(digits) == 10:
        if digits.startswith("02"):
            return f"{digits[:2]}-{digits[2:6]}-{digits[6:]}"
        return f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"
    if len(digits) == 11:
        return f"{digits[:3]}-{digits[3:7]}-{digits[7:]}"
    return digits


def _valid_phone_digits(digits: str) -> bool:
    if not digits or not digits.startswith("0") or digits.startswith("00"):
        return False
    if not (9 <= len(digits) <= 11):
        return False
    return bool(re.match(r'^(?:02|0[3-6]\d|070|010|011|016|017|018|019)', digits))


def _valid_labeled_phone_digits(digits: str) -> bool:
    if _valid_phone_digits(digits):
        return True
    # Some Google samples lose one Seoul exchange digit, e.g. TEL:02)33-4278.
    # Keep this narrow: only explicit TEL/전화 labels may accept 02-xx-xxxx.
    return bool(re.fullmatch(r'02\d{6}', digits or ""))


def _extract_phone_candidate(text: str) -> str:
    raw = text or ""
    label_match = _PHONE_LABELED_RE.search(raw)
    if label_match:
        digits = _normalize_phone_digits(label_match.group(1))
        if _valid_labeled_phone_digits(digits):
            return _format_phone_digits(digits)

    if _PHONE_ADMIN_NOISE_RE.search(raw):
        return ""

    for match in re.finditer(r'(?:\(\s*0\d{1,2}\s*\)\s*[-\s]?\d{3,4}[-\s]?\d{4}|0\d{1,2}[-\s]\d{3,4}[-\s]?\d{4})', raw):
        digits = _normalize_phone_digits(match.group(0))
        if _valid_phone_digits(digits):
            return _format_phone_digits(digits)

    for match in re.finditer(r'(?<!\d)0\d{1,2}\)\s*\d{3,4}[-\s.]?\d{4}(?!\d)', raw):
        digits = _normalize_phone_digits(match.group(0))
        if _valid_phone_digits(digits):
            return _format_phone_digits(digits)

    for digits in re.findall(r'(?<!\d)0\d{8,10}(?!\d)', raw):
        if _valid_phone_digits(digits):
            return _format_phone_digits(digits)
    return ""
