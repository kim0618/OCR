"""
문서 유형 경량 분류기.

목적:
  - 일반 매장 영수증(receipt_pos), 카드매출전표(receipt_card),
    은행/ATM 거래표(bank_slip), 수기/폼 문서(form_or_handwritten),
    unknown 을 OCR 전체 텍스트 기반 키워드 시그널로 구분.
  - 완벽한 분류가 아니라 "일반 영수증군 vs 비정형(은행/폼)"를 가르는 것이 핵심.

운영 정책 — unknown 은 실패가 아니라 '정상 검토 상태':
  - 세상의 모든 영수증 포맷을 사전에 완벽히 분류하는 것은 불가능하다.
  - 따라서 unknown 반환은 버그가 아니라 **시스템이 스스로 신중하게 판단을 보류**한
    정상 경로다. main._apply_doc_type_amount_policy 가 unknown 의 bare 저신뢰를
    비움 처리하고, review_log.jsonl 에 남겨 장기 개선의 입력이 된다.
  - 동일한 unknown 패턴이 review_log 에 반복 누적되면 운영자는 해당 패턴의
    시그널 키워드를 아래 _*_SIGNALS 리스트에 추가해 정식 유형으로 승격시킨다.

패턴 승격(promotion) 흐름 (예시):
  1) review_log.jsonl 에서 image_id 별 status=low_confidence 또는 suppressed_*
     인 건수가 임계치 이상 축적된 unknown 패턴 식별
  2) 해당 문서의 공통 키워드/레이아웃 추출 (예: 특정 프랜차이즈 영수증 헤더)
  3) 새 분류(예: receipt_franchise_xxx) 를 만들거나 기존 _*_SIGNALS 에 키워드 추가
  4) classify_document() 가 다음 요청부터 정식 유형으로 반환 →
     총합계금액 정책이 정상 선택 경로로 전환
  5) ground_truth.json 은 이 과정에서 수정되지 않는다 (동결 데이터셋)

사용:
  doc_info = classify_document(full_text)
  doc_info["type"] ∈ {"receipt_pos","receipt_card","bank_slip","form_or_handwritten","unknown"}
"""
import re


def _has_valid_biz_checksum(digits: str) -> bool:
    if len(digits) != 10 or not digits.isdigit():
        return False
    weights = [1, 3, 7, 1, 3, 7, 1, 3, 5]
    total = sum(int(digits[i]) * weights[i] for i in range(9))
    total += (int(digits[8]) * 5) // 10
    return (10 - (total % 10)) % 10 == int(digits[9])


def _receipt_like_unknown_evidence(text: str) -> tuple[bool, dict]:
    """Promote only receipt-like unknowns with multiple independent signals."""
    compact = re.sub(r'\s+', '', text or '')
    if not compact:
        return False, {}

    biz_candidates = re.findall(r'(?<!\d)(\d{10})(?!\d)', compact)
    biz_hits = [d for d in biz_candidates if _has_valid_biz_checksum(d)]
    has_biz = bool(biz_hits)
    has_tel = bool(re.search(r'(?:0\d{1,2}[-)]?\d{3,4}[-]?\d{4})', compact))
    has_amount = bool(re.search(r'(?<!\d)\d{1,3}[,.]\d{3}(?!\d)', compact))
    has_address = bool(re.search(
        r'[\uAC00-\uD7A3]{1,12}(?:\uC2DC|\uAD70|\uAD6C|\uB3D9|\uC74D|\uBA74|\uB85C|\uAE38|\uB300\uB85C)\d*',
        compact,
    ))
    receipt_context_hits = [
        label for label, pattern in (
            ("receipt", r'\uC601\uC218|\uD615\uC218'),
            ("slip", r'\uC804\uD45C|\uC99D\uC778|\uC2B9\uC778'),
            ("point", r'\uD3EC\uC778\uD2B8'),
            ("item", r'(?:\uD488\uBAA9|\uC0C1\uD488|\uC218\uB7C9|\uAE08\uC561)'),
            ("receipt_no", r'(?:NO|N0)[:.]?\d{2,}'),
        )
        if re.search(pattern, compact, re.I)
    ]
    evidence_count = sum([has_amount, has_address, bool(receipt_context_hits)]) + sum([has_biz, has_tel])
    ok = has_amount and (has_biz or has_tel) and (has_address or bool(receipt_context_hits)) and evidence_count >= 3
    return ok, {
        "biz": has_biz,
        "tel": has_tel,
        "amount": has_amount,
        "address": has_address,
        "receipt_context": receipt_context_hits,
        "evidence_count": evidence_count,
    }


_POS_SIGNALS = [
    r'영수증', r'세금계산서', r'상품명', r'수량', r'단가',
    r'공급가액', r'과세물품', r'면세물품', r'부가세', r'봉사료',
    r'상호', r'가맹점명', r'점명',
]

_CARD_SIGNALS = [
    r'승인번호', r'승인금액', r'승인일시',
    r'카드종류', r'카드번호', r'매입사', r'할부',
    r'거래구분', r'거래번호', r'신용카드', r'체크카드', r'IC카드',
    r'CASHNOTE', r'KOCES', r'CATID', r'CAT1D', r'\bTID\b',
    r'터미널', r'가맹점번호', r'매출전표',
]

_BANK_SIGNALS = [
    r'거래후잔액', r'거래후진액', r'잔액조회', r'입금', r'출금',
    r'계좌번호', r'계좌변호', r'수취인', r'수취계좌',
    r'처리은행', r'이체', r'송금',
    r'현금자동입출금', r'현금자동입\S?출금', r'ATM', r'타행이체', r'자동이체',
    r'거래일시', r'거래일자', r'거래내역', r'거래명세',
    r'i-?ONE\s?Bank', r'기업은행', r'국민은행', r'신한은행', r'우리은행', r'하나은행', r'농협',
]

# 수기 세금계산서/영수증 폼 문서
_FORM_SIGNALS = [
    r'작성년월일',
    r'공급대가총액',
    r'공급받는\s*자',
    r'영수\s*[\(（]?\s*청구\s*[\)）]?\s*함',
    r'귀하',
    r'품\s*명\s*수\s*량\s*단\s*가',
    r'아래\s*금액을\s*영수',
    r'아래\s*금액을\s*청구',
]


def _count_hits(patterns: list[str], text: str) -> tuple[int, list[str]]:
    hits = []
    for p in patterns:
        if re.search(p, text, re.I):
            hits.append(p)
    return len(hits), hits


def classify_document(full_text: str) -> dict:
    """OCR 전체 텍스트에서 키워드 시그널을 세어 문서 유형 분류.

    Returns:
        {
            "type":    "receipt_pos" | "receipt_card" | "bank_slip" | "form_or_handwritten" | "unknown",
            "scores":  {pos, card, bank, form},
            "hits":    {pos, card, bank, form},
        }
    """
    text = re.sub(r'\s+', '', full_text)

    pos_n, pos_hits = _count_hits(_POS_SIGNALS, text)
    card_n, card_hits = _count_hits(_CARD_SIGNALS, text)
    bank_n, bank_hits = _count_hits(_BANK_SIGNALS, text)
    form_n, form_hits = _count_hits(_FORM_SIGNALS, text)
    receipt_like_ok, receipt_like_evidence = _receipt_like_unknown_evidence(full_text)

    # 결정 규칙 (우선순위):
    #   1. form_n ≥ 2 이고 다른 타입보다 높으면 form_or_handwritten (수기/폼 문서)
    #   2. bank_n 최다이고 ≥2 면 bank_slip
    #   3. card_n ≥ 2 면 receipt_card
    #   4. pos_n ≥ 2 면 receipt_pos
    #   5. 1건씩만 있으면 각각 낮은 신뢰도로 분류
    #   6. 아무것도 없으면 unknown
    if form_n >= 2 and form_n >= pos_n and form_n >= card_n and form_n >= bank_n:
        doc_type = "form_or_handwritten"
    elif bank_n >= 2 and bank_n > pos_n and bank_n > card_n:
        doc_type = "bank_slip"
    elif card_n >= 2 and card_n >= pos_n:
        doc_type = "receipt_card"
    elif pos_n >= 2 and pos_n >= card_n:
        doc_type = "receipt_pos"
    elif form_n >= 1 and form_n >= pos_n and form_n >= card_n and form_n >= bank_n:
        doc_type = "form_or_handwritten"
    elif card_n >= 1 and card_n >= pos_n and card_n >= bank_n:
        doc_type = "receipt_card"
    elif pos_n >= 1 and pos_n >= bank_n:
        doc_type = "receipt_pos"
    elif bank_n >= 1:
        doc_type = "bank_slip"
    elif receipt_like_ok and bank_n == 0 and form_n == 0:
        doc_type = "receipt_pos"
    else:
        doc_type = "unknown"

    return {
        "type": doc_type,
        "scores": {"pos": pos_n, "card": card_n, "bank": bank_n, "form": form_n},
        "hits": {"pos": pos_hits, "card": card_hits, "bank": bank_hits, "form": form_hits},
        "receipt_like_unknown_evidence": receipt_like_evidence,
    }
