"""
finance_slip.py — finance_profile Tier-1 최소 추출 (1차 구현)

대상: doc_type == "bank_slip" 문서에서만 호출됨
목표 (docs/FINANCE_PARSER_TARGET_20260427.md §2):
    bankName / transactionType / transactionDateTime / amount

설계 원칙:
  - BANK_BRAND_SIGNALS / BANK_STRUCT_SIGNALS 재사용 (과적합 방지)
  - 특정 파일/샘플/픽셀 좌표 맞춤 분기 금지
  - accountMasked raw 저장 금지 (이번 단계 비추출)
  - _apply_doc_type_amount_policy 수정 없음
  - receipt_fields 슬롯 수정 없음
  - 회귀 안전: 영수증 파이프라인과 완전 분리
"""

import re
import sys
import os

# ocr-server 루트 경로 보장 (standalone 실행 시에도 동작)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from signal_lists import BANK_BRAND_SIGNALS, BANK_STRUCT_SIGNALS  # noqa: E402

# ─────────────────────────────────────────────────────────────────────────────
# 내부 상수 / 컴파일 패턴
# ─────────────────────────────────────────────────────────────────────────────

# 거래후잔액/수수료 — amount 후보 제외 목록 (오채택 방지)
_BALANCE_AFTER_RE = re.compile(
    r'거래후\s*잔액|거래후\s*진액|잔액조회|수수료|이용한도|출금한도',
    re.I,
)

# 거래금액 anchor 패턴 (입금액/출금액/이체금액/거래금액/요청금액)
# "입금액"(입금+액) 과 "이체금액"(이체+금액) 모두 포함
_AMOUNT_ANCHOR_RE = re.compile(
    r'(?:거래|이체|입금|출금|송금|요청)\s*금액'
    r'|입금액|출금액|송금액',
    re.I,
)

# 날짜+시각 패턴: YYYY-MM-DD HH:MM(:SS)?  — 구분자 변형 허용
_DATETIME_RE = re.compile(
    r'(\d{4})[.\-/年](\d{1,2})[.\-/月](\d{1,2})[日]?'
    r'(?:\s+(\d{1,2}):(\d{2})(?::(\d{2}))?)?',
)

# 거래일시 anchor
_DATETIME_ANCHOR_RE = re.compile(
    r'거래\s*일시|거래\s*일자|처리\s*일시|이체\s*일시|처리\s*시간|요청\s*일시',
    re.I,
)

# transactionType 분류 패턴
# 주의: 한국어 뒤에 어미가 붙으므로 word boundary 미사용 (기존 정책 준수)
_TX_DEPOSIT_RE  = re.compile(r'예금\s*입금|타행\s*입금|입금(?!출금)')
_TX_WITHDRAW_RE = re.compile(r'예금\s*출금|타행\s*출금|출금(?!입금)|인출')
_TX_TRANSFER_RE = re.compile(r'이체|송금|타행이체|자동이체')
_TX_ATM_RE      = re.compile(r'\bATM\b|자동화\s*기기|현금자동입\S?출금|CD기')

# 숫자 후보 — 콤마/공백 허용, "원"/"₩" suffix 허용
_NUM_EXTRACT_RE = re.compile(r'\d[\d,\s]{1,14}\d(?:\s*[원₩])?')
_NUM_CLEAN_RE   = re.compile(r'[^\d]')


# ─────────────────────────────────────────────────────────────────────────────
# 내부 헬퍼
# ─────────────────────────────────────────────────────────────────────────────

def _clean_number(raw: str) -> str:
    """콤마/공백/원/₩ 제거 → 순수 숫자 문자열."""
    return _NUM_CLEAN_RE.sub("", raw).strip()


def _value_after_anchor(line: str, anchor_m: re.Match, max_chars: int = 50) -> str:
    """anchor 매치 직후 값 토큰 반환 (개행 전 한정)."""
    after = line[anchor_m.end(): anchor_m.end() + max_chars]
    after = re.sub(r'^[\s:：]+', '', after)  # 선행 공백/콜론 스킵
    return after.split('\n')[0].strip()


# ─────────────────────────────────────────────────────────────────────────────
# Tier-1 개별 추출기
# ─────────────────────────────────────────────────────────────────────────────

def _extract_bank_name(text: str, reasons: list) -> str:
    """bankName: BANK_BRAND_SIGNALS 기반 — 단독 한글 약어 금지."""
    matched = []
    for pat in BANK_BRAND_SIGNALS:
        m = re.search(pat, text, re.I)
        if m:
            matched.append(m.group(0).strip())

    if not matched:
        return ""

    # 중복 제거, 길이 기준 내림차순 (더 구체적인 이름 우선)
    unique = sorted(set(matched), key=len, reverse=True)
    if len(unique) >= 2:
        reasons.append("BANK_NAME_MULTIPLE_CANDIDATES")
    return unique[0]


def _extract_transaction_type(text: str, reasons: list) -> str:
    """transactionType: 입금/출금/이체/ATM enum."""
    hits = []
    if _TX_DEPOSIT_RE.search(text):  hits.append("deposit")
    if _TX_WITHDRAW_RE.search(text): hits.append("withdraw")
    if _TX_TRANSFER_RE.search(text): hits.append("transfer")
    if _TX_ATM_RE.search(text):      hits.append("atm_cash")

    unique = list(dict.fromkeys(hits))  # 순서 보존 중복 제거

    if not unique:
        reasons.append("TRANSACTION_TYPE_NOT_FOUND")
        return "unknown"

    if len(unique) >= 2:
        # 이체+입출금 공존 → 이체 우선 (이체 전표에 입금/출금이 함께 인쇄됨)
        if "transfer" in unique:
            return "transfer"
        # ATM+출금 공존 → ATM 우선
        if "atm_cash" in unique:
            return "atm_cash"
        reasons.append("TRANSACTION_TYPE_AMBIGUOUS")
        return unique[0]

    return unique[0]


def _extract_transaction_datetime(text: str, reasons: list) -> str:
    """transactionDateTime: 거래일시 anchor 직후 날짜+시각 추출."""
    lines = text.split('\n')

    # 1단계: anchor가 있는 줄에서 우선 탐색
    for line in lines:
        anc_m = _DATETIME_ANCHOR_RE.search(line)
        if not anc_m:
            continue
        remaining = _value_after_anchor(line, anc_m, max_chars=40)
        dt_m = _DATETIME_RE.search(remaining)
        if not dt_m:
            # anchor는 있는데 날짜가 같은 줄에 없으면 다음 줄도 확인
            idx = lines.index(line)
            if idx + 1 < len(lines):
                dt_m = _DATETIME_RE.search(lines[idx + 1])
        if dt_m:
            return _format_datetime(dt_m, reasons)

    # 2단계: 전체 텍스트에서 첫 번째 날짜 패턴 (anchor 없음 → review)
    dt_m = _DATETIME_RE.search(text)
    if dt_m:
        reasons.append("DATETIME_FORMAT_UNSTABLE")  # anchor 없이 날짜만 탐지
        return _format_datetime(dt_m, reasons)

    reasons.append("DATETIME_NOT_FOUND")
    return ""


def _format_datetime(m: re.Match, reasons: list) -> str:
    """Match → YYYY-MM-DD HH:MM(:SS) 또는 YYYY-MM-DD."""
    year = m.group(1)
    month = m.group(2).zfill(2)
    day   = m.group(3).zfill(2)

    try:
        if int(year) > 2100:
            reasons.append("DATETIME_FORMAT_UNSTABLE")
            return ""
    except ValueError:
        return ""

    if m.group(4) and m.group(5):
        hour = m.group(4).zfill(2)
        minute = m.group(5)
        sec = m.group(6)
        dt = f"{year}-{month}-{day} {hour}:{minute}"
        if sec:
            dt += f":{sec}"
        return dt

    # 날짜만 — 시각 결손
    reasons.append("DATETIME_FORMAT_UNSTABLE")
    return f"{year}-{month}-{day}"


def _extract_amount(text: str, reasons: list) -> str:
    """amount (거래금액): anchor 직후 숫자 추출. 잔액/수수료 anchor와 혼동 금지."""
    lines = text.split('\n')

    anchor_values: list[str] = []
    balance_values: list[str] = []

    for line in lines:
        anc_m = _AMOUNT_ANCHOR_RE.search(line)
        if anc_m:
            after = _value_after_anchor(line, anc_m, max_chars=30)
            n_m = _NUM_EXTRACT_RE.search(after)
            if n_m:
                num = _clean_number(n_m.group(0))
                if len(num) >= 3:  # 3자리 이상만 (너무 짧은 숫자 제외)
                    anchor_values.append(num)

        bal_m = _BALANCE_AFTER_RE.search(line)
        if bal_m:
            after = _value_after_anchor(line, bal_m, max_chars=30)
            n_m = _NUM_EXTRACT_RE.search(after)
            if n_m:
                num = _clean_number(n_m.group(0))
                if num:
                    balance_values.append(num)

    if anchor_values:
        # anchor 후보와 balance 후보가 겹치면 AMOUNT_AMBIGUOUS
        balance_set = set(balance_values)
        clean_anchor = [v for v in anchor_values if v not in balance_set]
        if clean_anchor:
            return clean_anchor[0]
        # 전부 겹침
        reasons.append("AMOUNT_AMBIGUOUS")
        return ""

    # anchor 없는 단독 숫자 — 채택 금지, review만 부여
    reasons.append("AMOUNT_ANCHOR_NOT_FOUND")
    return ""


# ─────────────────────────────────────────────────────────────────────────────
# 공개 API
# ─────────────────────────────────────────────────────────────────────────────

def extract_finance_fields(full_text: str) -> dict:
    """
    finance_profile Tier-1 최소 추출.

    반환:
        bankName            str
        transactionType     str  deposit|withdraw|transfer|atm_cash|unknown
        transactionDateTime str  YYYY-MM-DD HH:MM(:SS) 또는 YYYY-MM-DD 또는 ""
        amount              str  숫자 문자열 또는 ""
        _reviewReasons      list[str]  — 내부 감사용 (호출부에서 분리 후 노출)

    회귀 안전:
        _apply_doc_type_amount_policy 미수정
        receipt_fields 슬롯 미수정
        doc_type == "bank_slip" 분기에서만 호출됨
    """
    if not full_text or not full_text.strip():
        return {
            "bankName":            "",
            "transactionType":     "unknown",
            "transactionDateTime": "",
            "amount":              "",
            "_reviewReasons":      ["EMPTY_TEXT"],
        }

    reasons: list[str] = []

    bank_name   = _extract_bank_name(full_text, reasons)
    tx_type     = _extract_transaction_type(full_text, reasons)
    tx_datetime = _extract_transaction_datetime(full_text, reasons)
    amount      = _extract_amount(full_text, reasons)

    # Tier-1 완전 추출 여부 확인
    tier1_ok = all([
        bank_name,
        tx_type not in ("", "unknown"),
        tx_datetime,
        amount,
    ])
    if not tier1_ok and "TIER1_PARTIAL" not in reasons:
        reasons.append("TIER1_PARTIAL")

    return {
        "bankName":            bank_name,
        "transactionType":     tx_type,
        "transactionDateTime": tx_datetime,
        "amount":              amount,
        "_reviewReasons":      reasons,
    }
