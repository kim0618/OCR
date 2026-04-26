import re


def _clean_number(s: str) -> str:
    s = s.replace('O', '0').replace('l', '1').replace('I', '1').replace('S', '5').replace('B', '8')
    s = re.sub(r'(\d)\.(\d{3})', r'\1,\2', s)  # 33.000 → 33,000
    return s


def _clean_inline_field_value(value: str) -> str:
    value = re.sub(r'\s+', ' ', value or '').strip()
    return value.strip(" :;|/-")
