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
# 보수적으로 확장: 명확한 잔액/한도/수수료 전용 표현만 포함
_BALANCE_AFTER_RE = re.compile(
    r'거래\s*후\s*잔액|거래후\s*진액'
    r'|출금\s*후\s*잔액|이체\s*후\s*잔액|인출\s*후\s*잔액'
    r'|현재\s*잔액|잔액\s*합계|이용\s*가능\s*잔액'
    r'|잔액조회|수수료|이용한도|출금한도|거래한도',
    re.I,
)

# 거래금액 anchor 패턴 — 우선순위별 그룹 (높은 인덱스 = 낮은 우선순위)
# 각 그룹 내에서 먼저 발견된 값을 채택함
_AMOUNT_ANCHOR_GROUPS: list = [
    # P0: 가장 구체적 — 거래금액 계열
    re.compile(r'거래\s*금액', re.I),
    # P1: 이체 계열
    re.compile(r'이체\s*금액|이체\s*출금\s*금액|이체\s*입금\s*금액', re.I),
    # P2: 입금/출금 레이블 금액 계열
    re.compile(r'입금\s*금액|출금\s*금액|지급\s*금액|납입\s*금액', re.I),
    # P3: 단축형 및 기타
    re.compile(r'입금액|출금액|송금액|결제금액|요청금액|송금\s*금액', re.I),
]

# 하위 호환: 단일 앵커 패턴 (기존 코드 참조용 — _extract_amount에서는 _AMOUNT_ANCHOR_GROUPS 사용)
_AMOUNT_ANCHOR_RE = re.compile(
    r'거래\s*금액'
    r'|이체\s*금액|이체\s*출금\s*금액|이체\s*입금\s*금액'
    r'|입금\s*금액|출금\s*금액|지급\s*금액|납입\s*금액'
    r'|입금액|출금액|송금액|결제금액|요청금액',
    re.I,
)

# 날짜+시각 패턴: YYYY-MM-DD HH:MM(:SS)?  — 구분자 변형 허용
_DATETIME_RE = re.compile(
    r'(\d{4})[.\-/年](\d{1,2})[.\-/月](\d{1,2})[日]?'
    r'(?:\s+(\d{1,2}):(\d{2})(?::(\d{2}))?)?',
)

# 거래일시 anchor — 다양한 form 흡수 (\s* 기본 매치 \n 포함, full-text scan에서 split-anchor 자동 흡수)
_DATETIME_ANCHOR_RE = re.compile(
    r'거래\s*일시|거래\s*일자|거래\s*시간'
    r'|처리\s*일시|처리\s*일자|처리\s*시간'
    r'|이체\s*일시|이체\s*일자'
    r'|요청\s*일시|요청\s*일자',
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
# OCR prefix 노이즈 제거 패턴 (#, ₩, W, \, 공백 등)
_NUM_PREFIX_NOISE_RE = re.compile(r'^[\s#₩W\\]+')  # 숫자 앞 특수문자 스트립용


# ─────────────────────────────────────────────────────────────────────────────
# 은행명 canonical 매핑 — 동일 은행의 여러 표기를 단일 canonical name으로 정규화
#
# 설계 원칙:
#   - 공식 은행명(법인명) + 약식(접두사 제외) + 대표 모바일/온라인 브랜드 + 도메인만 등록
#   - 마케팅 카피·앱 내부 용어·제휴명 등 무한 확장 금지
#   - 모호한 약어 단독(국민/신한/하나 등)은 등록 안 함 (카드 brand 충돌 방지 — signal_lists 정책 준수)
#   - canonical name은 가장 일반적인 공식 표기를 사용
# ─────────────────────────────────────────────────────────────────────────────
_BANK_CANONICAL_MAP: list = [
    # (canonical_name, [variant patterns])
    ("IBK기업은행",  [r'IBK\s*기업은행', r'기업은행', r'i-?ONE\s*Bank', r'ibk\.co\.kr']),
    ("KB국민은행",   [r'KB\s*국민은행', r'국민은행', r'kbstar(?:\.com)?', r'kbstar\.co\.kr']),
    ("신한은행",     [r'신한은행', r'shinhanbank(?:\.com)?']),
    ("우리은행",     [r'우리은행', r'wooribank(?:\.com)?']),
    ("KEB하나은행",  [r'KEB\s*하나은행', r'하나은행', r'hanabank(?:\.com)?']),
    ("NH농협은행",   [r'NH\s*농협은행', r'농협은행', r'nonghyup\.com']),
]


def _canonicalize_bank_name(matched_raw: str) -> str:
    """
    매치된 raw 텍스트를 canonical bank name으로 변환.
    매핑되지 않으면 원본 그대로 반환 (안전한 fallback).
    """
    if not matched_raw:
        return ""
    for canonical, patterns in _BANK_CANONICAL_MAP:
        for pat in patterns:
            if re.search(pat, matched_raw, re.I):
                return canonical
    return matched_raw  # 매핑 없으면 원본 보존


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
    """
    bankName: canonical map 기반 매치 → canonical name 반환.

    동작:
      1) _BANK_CANONICAL_MAP의 variants를 텍스트에 검색
      2) 매치된 variants를 canonical 이름으로 그룹핑
      3) canonical 그룹이 1개면 해당 canonical 반환 (review reason 없음)
      4) canonical 그룹이 2개 이상이면 첫 번째 반환 + BANK_NAME_MULTIPLE_CANDIDATES
      5) canonical map 매치가 없으면 BANK_BRAND_SIGNALS 폴백 (backwards-compat)
    """
    # 1+2단계: canonical map으로 매치 → canonical 그룹핑 (insert 순서 보존)
    canonical_hits: dict = {}  # canonical_name → 첫 매치된 raw text (감사용)
    for canonical, patterns in _BANK_CANONICAL_MAP:
        for pat in patterns:
            m = re.search(pat, text, re.I)
            if m and canonical not in canonical_hits:
                canonical_hits[canonical] = m.group(0).strip()
                break  # 같은 canonical 내 다른 variant는 더 안 봄

    if canonical_hits:
        # 3+4단계: canonical 그룹 수에 따라 review 부여
        if len(canonical_hits) >= 2:
            reasons.append("BANK_NAME_MULTIPLE_CANDIDATES")
        # canonical map 정의 순서대로 가장 우선되는 canonical 반환
        return next(iter(canonical_hits))

    # 5단계: canonical map에 없는 은행 — BANK_BRAND_SIGNALS 폴백
    matched: list = []
    for pat in BANK_BRAND_SIGNALS:
        m = re.search(pat, text, re.I)
        if m:
            matched.append(m.group(0).strip())

    if not matched:
        return ""

    # 폴백 경로에서도 canonical 변환 시도 (있는 경우만)
    canonicalized = [_canonicalize_bank_name(v) for v in matched]
    unique_canonical = list(dict.fromkeys(canonicalized))  # 순서 보존 + 중복 제거
    if len(unique_canonical) >= 2:
        reasons.append("BANK_NAME_MULTIPLE_CANDIDATES")
    return unique_canonical[0]


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
    """
    transactionDateTime: 거래일시 anchor 직후 날짜+시각 추출.

    보강:
      - full-text scan으로 전환 (line-by-line → 전체 텍스트)
        → \\s* 가 \\n 을 포함하므로 split-anchor (예: '거래\\n일자:') 자동 흡수
      - anchor 매치 위치 직후 80자 윈도우에서 datetime 탐색
    """
    # 1단계: 전체 텍스트에서 anchor 매치 (multi-line 흡수)
    for anc_m in _DATETIME_ANCHOR_RE.finditer(text):
        # anchor 이후 윈도우 (안전 거리 80자)
        window = text[anc_m.end(): anc_m.end() + 80]
        # 선행 콜론/공백/개행 제거
        window = re.sub(r'^[\s:：]+', '', window)
        dt_m = _DATETIME_RE.search(window)
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


def _num_from_token(token: str) -> str:
    """토큰에서 숫자만 추출. OCR prefix 노이즈(#, ₩ 등) 제거 후 파싱."""
    # prefix 노이즈 제거 후 숫자 패턴 탐색
    stripped = _NUM_PREFIX_NOISE_RE.sub("", token)
    n_m = _NUM_EXTRACT_RE.search(stripped)
    if not n_m:
        return ""
    return _clean_number(n_m.group(0))


def _balance_nums_from_text(lines: list) -> set:
    """잔액/수수료/한도 anchor가 붙은 숫자 집합 반환 (amount 후보 제외용)."""
    balance_values: set = set()
    for i, line in enumerate(lines):
        if not _BALANCE_AFTER_RE.search(line):
            continue
        # 같은 줄 이후 숫자
        for n_m in _NUM_EXTRACT_RE.finditer(line):
            num = _clean_number(n_m.group(0))
            if num:
                balance_values.add(num)
        # anchor만 있고 숫자가 없으면 다음 줄까지 확인
        if not _NUM_EXTRACT_RE.search(line):
            for j in range(i + 1, min(i + 3, len(lines))):
                next_line = lines[j].strip()
                if not next_line:
                    continue
                for n_m in _NUM_EXTRACT_RE.finditer(next_line):
                    num = _clean_number(n_m.group(0))
                    if num:
                        balance_values.add(num)
                break
    return balance_values


def _extract_amount(text: str, reasons: list) -> str:
    """
    amount (거래금액): 우선순위 anchor 기반 추출.

    보강 내역:
      - anchor 직후 숫자가 없으면 다음 줄(최대 2줄)까지 탐색 (next-line 폴백)
      - 잔액/수수료 anchor 확장 (현재잔액/출금후잔액/이체후잔액 등 포함)
      - 앵커 우선순위 그룹 도입: 거래금액 > 이체금액 > 입금금액/출금금액 > 단축형
      - OCR prefix 노이즈(#, ₩ 등) 흡수
    """
    lines = text.split('\n')

    # 1. 잔액/수수료 연관 숫자 수집 (amount 후보 제외용)
    balance_values = _balance_nums_from_text(lines)

    found_any_anchor = False

    # 2. 우선순위 순서로 anchor 그룹 탐색 — 높은 우선순위에서 먼저 찾으면 즉시 반환
    for anchor_pat in _AMOUNT_ANCHOR_GROUPS:
        candidates: list = []

        for i, line in enumerate(lines):
            anc_m = anchor_pat.search(line)
            if not anc_m:
                continue
            found_any_anchor = True

            # 2a. anchor 직후 (같은 줄) — max_chars 40으로 여유 확보
            after = _value_after_anchor(line, anc_m, max_chars=40)
            num = _num_from_token(after)
            if num and len(num) >= 3 and num not in balance_values:
                candidates.append(num)
                continue

            # 2b. 다음 줄 폴백 — anchor와 숫자가 줄 구분된 형식
            #     (거래 금액:\n117,920원  같은 패턴)
            for j in range(i + 1, min(i + 3, len(lines))):
                next_line = lines[j].strip()
                if not next_line:
                    continue  # 빈 줄은 건너뜀
                # 다음 줄이 잔액 anchor이면 중단 (오탐 방지)
                if _BALANCE_AFTER_RE.search(next_line):
                    break
                # 다음 줄에서 숫자 탐색
                num = _num_from_token(next_line)
                if num and len(num) >= 3 and num not in balance_values:
                    candidates.append(num)
                break  # 첫 번째 비빈 줄만 확인

        if candidates:
            return candidates[0]

    # 3. anchor를 찾았지만 유효 숫자가 없는 경우 → AMBIGUOUS
    #    anchor 자체가 없는 경우 → ANCHOR_NOT_FOUND
    if found_any_anchor:
        reasons.append("AMOUNT_AMBIGUOUS")
    else:
        reasons.append("AMOUNT_ANCHOR_NOT_FOUND")
    return ""


# ─────────────────────────────────────────────────────────────────────────────
# Tier-2 추출 (balanceAfter / accountMasked / branchOrChannel(수취인 계좌) / memo(수취인명))
#
# 설계 원칙:
#   - 보수적 추출: 명시적 anchor 가 있을 때만 추출. 없으면 빈값.
#   - Tier-1 무영향: review reason 추가 안 함 (Tier-2 미추출이 selected → review 트리거하지 않음)
#   - accountMasked: 마스킹된 형태(***, xxx)일 때만 저장. raw 계좌번호 저장 금지.
#   - branchOrChannel: 수취인측 계좌만(수취/입금/받는 anchor). 일반 "계좌번호"와 분리.
#   - 외부 try/except 로 Tier-2 오류가 Tier-1 결과를 가리지 않도록 보호 (extract_finance_fields 내).
# ─────────────────────────────────────────────────────────────────────────────

# balanceAfter: 명시적 잔액 anchor (잔액조회/수수료/한도는 제외 — _BALANCE_AFTER_RE 와 분리)
_BALANCE_VALUE_ANCHOR_RE = re.compile(
    r'거래\s*후\s*잔액|거래후\s*진액'        # 진액: 잔→진 OCR 노이즈 흡수
    r'|출금\s*후\s*잔액|이체\s*후\s*잔액|인출\s*후\s*잔액'
    r'|현재\s*잔액|이용\s*가능\s*잔액'
    r'|거래\s*후\s*잔고|통장\s*잔고|통장\s*잔액',  # 잔고 synonym (잔액과 등가)
    re.I,
)

# 마스킹 토큰 검사 (2개 이상 연속 *, x, X)
_MASK_TOKEN_RE = re.compile(r'\*{2,}|[xX]{2,}')

# 일반 계좌번호 anchor (자기/출금 계좌)
_ACCT_NUM_ANCHOR_RE = re.compile(
    r'계좌\s*번호|계좌\s*변호|계최\s*번호|계최\s*변호'  # 변/최: OCR 노이즈
    r'|출금\s*계좌|보내는\s*계좌|보내는분\s*계좌',
    re.I,
)

# 수취인 계좌 anchor (UI 라벨: 수취인 계좌 → branchOrChannel 슬롯에 저장)
_BENEFICIARY_ACCT_ANCHOR_RE = re.compile(
    r'수취\s*계좌|수취인\s*계좌|입금\s*계좌|받는\s*계좌|받는분\s*계좌'
    r'|송금\s*받을\s*계좌|받으시는\s*계좌',  # 자연어 변형
    re.I,
)

# 수취인명 anchor (UI 라벨: 수취인명 → memo 슬롯에 저장)
_BENEFICIARY_NAME_ANCHOR_RE = re.compile(
    r'수취인\s*(?:성명|명|이름)'
    r'|받는\s*분\s*(?:성명|명|이름)'
    r'|받는\s*사람\s*(?:성명|명|이름)'
    r'|예금주(?:\s*성명|\s*명|\s*이름)?'
    r'|입금\s*대상\s*(?:성명|명)'
    r'|수취\s*고객\s*(?:성명|명)',  # 일부 은행 변형
    re.I,
)

# balanceAfter 전용 lenient 숫자 패턴: ',' OCR 노이즈로 '.'이 들어와도 자릿수 구분자로 흡수
# (amount 추출의 strict _NUM_EXTRACT_RE 는 변경하지 않음)
_LENIENT_NUM_RE = re.compile(r'\d[\d,.\s]{1,14}\d(?:\s*[원₩])?')

# 한글 이름 false-positive 방지 — 일반어/라벨/은행명 제외
_NAME_BLACKLIST: set = {
    "성명", "이름", "수취인", "수취인성명", "받는분", "받는분성명",
    "예금주", "보내는분", "거래", "정보", "확인", "감사", "처리", "계좌",
    "정상처리", "거래일시", "거래금액", "거래일자", "거래시간",
}


def _num_from_token_balance(token: str) -> str:
    """balanceAfter 전용 — '.' 구분자도 흡수 (OCR 노이즈)."""
    stripped = _NUM_PREFIX_NOISE_RE.sub("", token)
    m = _LENIENT_NUM_RE.search(stripped)
    if not m:
        return ""
    return _clean_number(m.group(0))


def _extract_balance_after(lines: list, reasons: list) -> str:
    """
    balanceAfter (거래후잔액): 명시적 잔액 anchor 직후 숫자.
    - 같은 줄 → 다음 1~2 줄 폴백
    - amount 와 anchor 가 disjoint 하므로 자연스럽게 분리됨
    """
    for i, line in enumerate(lines):
        anc = _BALANCE_VALUE_ANCHOR_RE.search(line)
        if not anc:
            continue
        after = _value_after_anchor(line, anc, max_chars=40)
        num = _num_from_token_balance(after)
        if num and len(num) >= 3:
            return num
        for j in range(i + 1, min(i + 3, len(lines))):
            nxt = lines[j].strip()
            if not nxt:
                continue
            num = _num_from_token_balance(nxt)
            if num and len(num) >= 3:
                return num
            break
    return ""


def _find_masked_acct_token(token: str) -> str:
    """
    마스킹된 계좌번호 후보 추출.
      - 마스킹 토큰(***/xxx) 2개 이상 + 숫자 3개 이상 + 계좌 형태
    """
    if not token or not _MASK_TOKEN_RE.search(token):
        return ""
    m = re.search(r'(?:\[\d{2,4}\])?\d[\d\-\s\*xX]{4,40}', token)
    if not m:
        return ""
    cand = m.group(0).strip().rstrip(' :,.원')
    digit_count = sum(1 for c in cand if c.isdigit())
    mask_count = sum(1 for c in cand if c in '*xX')
    if digit_count < 3 or mask_count < 2:
        return ""
    return re.sub(r'\s+', '', cand)


def _extract_account_masked(lines: list, reasons: list) -> str:
    """
    accountMasked: 계좌번호 anchor 직후 마스킹된 값일 때만.
    - 마스킹 안 된 raw 계좌번호는 저장 안 함 (privacy)
    - 다음 anchor 만나면 중단
    """
    for i, line in enumerate(lines):
        anc = _ACCT_NUM_ANCHOR_RE.search(line)
        if not anc:
            continue
        after = _value_after_anchor(line, anc, max_chars=80)
        cand = _find_masked_acct_token(after)
        if cand:
            return cand
        for j in range(i + 1, min(i + 4, len(lines))):
            nxt = lines[j].strip()
            if not nxt:
                continue
            if (_ACCT_NUM_ANCHOR_RE.search(nxt)
                    or _BENEFICIARY_ACCT_ANCHOR_RE.search(nxt)
                    or _BENEFICIARY_NAME_ANCHOR_RE.search(nxt)
                    or _BALANCE_VALUE_ANCHOR_RE.search(nxt)):
                break
            cand = _find_masked_acct_token(nxt)
            if cand:
                return cand
            break
    return ""


def _find_acct_value_token(token: str) -> str:
    """
    수취인 계좌 형태 값 (마스킹 여부 무관).
    형식: [bank_code]nnn-nnnnnn-nn-nnn 또는 nnn-nnnn-nnnn 류.
    """
    if not token:
        return ""
    m = re.search(r'\[\d{2,4}\][\d\-\s]{6,30}|\d[\d\-\s\*xX]{6,40}', token)
    if not m:
        return ""
    cand = m.group(0).strip().rstrip(' :,.원')
    digit_count = sum(1 for c in cand if c.isdigit())
    if digit_count < 6:
        return ""
    return re.sub(r'\s+', '', cand)


def _extract_beneficiary_account(lines: list, reasons: list) -> str:
    """
    branchOrChannel (UI 라벨: 수취인 계좌): 수취/입금/받는 계좌 anchor 전용.
    """
    for i, line in enumerate(lines):
        anc = _BENEFICIARY_ACCT_ANCHOR_RE.search(line)
        if not anc:
            continue
        after = _value_after_anchor(line, anc, max_chars=80)
        cand = _find_acct_value_token(after)
        if cand:
            return cand
        for j in range(i + 1, min(i + 4, len(lines))):
            nxt = lines[j].strip()
            if not nxt:
                continue
            if (_ACCT_NUM_ANCHOR_RE.search(nxt)
                    or _BENEFICIARY_NAME_ANCHOR_RE.search(nxt)
                    or _BALANCE_VALUE_ANCHOR_RE.search(nxt)):
                break
            cand = _find_acct_value_token(nxt)
            if cand:
                return cand
            break
    return ""


def _extract_name_value(token: str) -> str:
    """anchor 뒤 한글 이름 후보 (2-10자, 블랙리스트/은행명 제외)."""
    if not token:
        return ""
    s = token.strip().lstrip(':：').strip()
    m = re.search(r'[가-힣]{2,10}', s)
    if not m:
        return ""
    cand = m.group(0)
    if cand in _NAME_BLACKLIST:
        return ""
    if any(b in cand for b in ['은행', '카드', '코리아']):
        return ""
    return cand


def _extract_beneficiary_name(lines: list, reasons: list) -> str:
    """
    memo (UI 라벨: 수취인명): 명시적 수취인 anchor + 한글 이름.
    'anchor:\\n:\\n이름' 같은 multi-line 라벨 분리 형식도 흡수.
    """
    for i, line in enumerate(lines):
        anc = _BENEFICIARY_NAME_ANCHOR_RE.search(line)
        if not anc:
            continue
        after = _value_after_anchor(line, anc, max_chars=40)
        cand = _extract_name_value(after)
        if cand:
            return cand
        for j in range(i + 1, min(i + 5, len(lines))):
            nxt = lines[j].strip()
            if not nxt:
                continue
            if re.fullmatch(r'[:\s：]+', nxt):
                continue
            cand = _extract_name_value(nxt)
            if cand:
                return cand
            break
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
            "balanceAfter":        "",
            "accountMasked":       "",
            "branchOrChannel":     "",
            "memo":                "",
            "_reviewReasons":      ["EMPTY_TEXT"],
        }

    reasons: list[str] = []
    lines = full_text.split('\n')

    # Tier-1 (selected 판정 기준 4필드)
    bank_name   = _extract_bank_name(full_text, reasons)
    tx_type     = _extract_transaction_type(full_text, reasons)
    tx_datetime = _extract_transaction_datetime(full_text, reasons)
    amount      = _extract_amount(full_text, reasons)

    # Tier-2 (보조 4필드) — review reason 추가 안 함, 오류 시 Tier-1 보호
    balance_after        = ""
    account_masked       = ""
    beneficiary_account  = ""
    beneficiary_name     = ""
    try:
        balance_after        = _extract_balance_after(lines, reasons)
        account_masked       = _extract_account_masked(lines, reasons)
        beneficiary_account  = _extract_beneficiary_account(lines, reasons)
        beneficiary_name     = _extract_beneficiary_name(lines, reasons)
    except Exception as _e:
        # Tier-2 추출 실패가 Tier-1 응답을 가리지 않도록 차단
        print(f"[finance_slip:tier2] extraction error (Tier-1 보호): {_e}")

    # Tier-1 완전 추출 여부 확인 (Tier-2 무관)
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
        "balanceAfter":        balance_after,
        "accountMasked":       account_masked,
        "branchOrChannel":     beneficiary_account,
        "memo":                beneficiary_name,
        "_reviewReasons":      reasons,
    }
