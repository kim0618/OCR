import re

from utils.text_normalize import _clean_number


def _validate_biz_number(digits: str) -> bool:
    """사업자등록번호 체크섬 검증 (10자리 숫자 문자열)"""
    if len(digits) != 10 or digits[0] == '0':
        return False
    weights = [1, 3, 7, 1, 3, 7, 1, 3, 5]
    total = sum(int(digits[i]) * weights[i] for i in range(9))
    total += int(digits[8]) * 5 // 10
    check = (10 - (total % 10)) % 10
    return check == int(digits[9])


def _extract_biz_number(text: str) -> str | None:
    """텍스트에서 사업자번호 추출 + 체크섬 검증"""
    cleaned = _clean_number(text)
    candidates = re.findall(r'[1-9]\d{2}[-\s.]?\d{2}[-\s.]?\d{5}', cleaned)
    for c in candidates:
        digits = re.sub(r'\D', '', c)
        if _validate_biz_number(digits):
            return f"{digits[:3]}-{digits[3:5]}-{digits[5:]}"
    return None


def _extract_biz_number_relaxed(text: str) -> str | None:
    """사업자번호 형식 매칭 (체크섬 없이).

    OCR 오류로 체크섬이 틀린 경우를 위한 fallback.
    구분자(- 또는 공백 또는 점)가 명시적으로 있어야 허용 — 승인번호/상품코드 오탐 방지.
    전화번호(0으로 시작)와 구분을 위해 [1-9]로 시작하는 패턴만 매칭.
    """
    cleaned = _clean_number(text)
    # 구분자가 반드시 있어야 하는 패턴: 3자리-2자리-5자리
    candidates = re.findall(r'[1-9]\d{2}[-\s.]\d{2}[-\s.]\d{5}', cleaned)
    for c in candidates:
        digits = re.sub(r'\D', '', c)
        if len(digits) == 10:
            return f"{digits[:3]}-{digits[3:5]}-{digits[5:]}"
    return None
