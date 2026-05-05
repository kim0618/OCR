"""
문서 유형 경량 분류기.

목적:
  - 일반 매장 영수증(receipt_pos), 카드매출전표(receipt_card),
    의료/약국 영수증(medical_receipt),
    은행/ATM 거래표(bank_slip), 수기/폼 문서(form_or_handwritten),
    unknown 을 OCR 전체 텍스트의 시그널 가중합으로 구분.
  - 완벽한 분류가 아니라 "일반 영수증군 vs 비정형(은행/폼) vs 의료군"을 가르는 것이 핵심.

설계:
  - 시그널 사전은 signal_lists.py 에 분리되어 있다.
  - 정확 매칭(_STRICT) 외에 OCR 노이즈를 흡수하는 약 매칭(_FUZZY) 패턴도 사용.
  - 단일 키워드(예: '농협') 만으로 분류 결정이 뒤집히지 않도록 카드 브랜드와의
    동음이의 가드 + 은행 구조 시그널 요구를 함께 적용.
  - 공급가액 + 부가세 + 합계 3종 세트가 검출되면 카드/영수증 계열 가산 (bank 오분류 방지).

운영 정책 — unknown 은 실패가 아니라 '정상 검토 상태':
  - 세상의 모든 영수증 포맷을 사전에 완벽히 분류하는 것은 불가능하다.
  - 따라서 unknown 반환은 버그가 아니라 시스템이 신중하게 판단을 보류한 정상 경로다.
  - main._apply_doc_type_amount_policy 가 unknown 의 bare 저신뢰를 비움 처리하고,
    review_log.jsonl 에 남겨 장기 개선의 입력이 된다.
  - 동일한 unknown 패턴이 review_log 에 반복 누적되면 운영자는 시그널을 추가해
    정식 유형으로 승격시킨다. ground_truth.json 은 이 과정에서 수정되지 않는다.

사용:
  doc_info = classify_document(full_text)
  doc_info["type"] ∈ {
      "receipt_pos", "receipt_card", "medical_receipt",
      "bank_slip", "form_or_handwritten", "unknown",
  }
"""
import re

from signal_lists import (
    POS_SIGNALS,
    CARD_SIGNALS_STRICT,
    CARD_SIGNALS_FUZZY,
    CARD_BRAND_SIGNALS,
    BANK_STRUCT_SIGNALS,
    BANK_BRAND_SIGNALS,
    FORM_SIGNALS,
    MEDICAL_SIGNALS,
    BANK_TO_CARD_DISAMBIG_PREFIXES,
)


# ============================================================
# 보조: 사업자번호 체크섬
# ============================================================
def _has_valid_biz_checksum(digits: str) -> bool:
    if len(digits) != 10 or not digits.isdigit():
        return False
    weights = [1, 3, 7, 1, 3, 7, 1, 3, 5]
    total = sum(int(digits[i]) * weights[i] for i in range(9))
    total += (int(digits[8]) * 5) // 10
    return (10 - (total % 10)) % 10 == int(digits[9])


# ============================================================
# 보조: receipt-like (unknown 후보 중 영수증 가능성 평가)
# ============================================================
def _receipt_like_unknown_evidence(text: str) -> tuple[bool, dict]:
    """unknown 으로 떨어졌더라도 영수증 같은 다중 증거가 있으면 receipt_pos 로 승격."""
    compact = re.sub(r'\s+', '', text or '')
    if not compact:
        return False, {}

    biz_candidates = re.findall(r'(?<!\d)(\d{10})(?!\d)', compact)
    biz_hits = [d for d in biz_candidates if _has_valid_biz_checksum(d)]
    has_biz = bool(biz_hits)
    has_tel = bool(re.search(r'(?:0\d{1,2}[-)]?\d{3,4}[-]?\d{4})', compact))
    has_amount = bool(re.search(r'(?<!\d)\d{1,3}[,.]\d{3}(?!\d)', compact))
    has_address = bool(re.search(
        r'[가-힣]{1,12}(?:시|군|구|동|읍|면|로|길|대로)\d*',
        compact,
    ))
    receipt_context_hits = [
        label for label, pattern in (
            ("receipt", r'영수|형수'),
            ("slip", r'전표|증인|승인'),
            ("point", r'포인트'),
            ("item", r'(?:품목|상품|수량|금액)'),
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


# ============================================================
# 보조: 시그널 패턴 카운트 (패턴 1개당 1점)
# ============================================================
def _count_hits(patterns: list[str], text: str) -> tuple[int, list[str]]:
    hits = []
    for p in patterns:
        if re.search(p, text, re.I):
            hits.append(p)
    return len(hits), hits


# ============================================================
# 보조: 공급가액 + 부가세 + 합계 3종 세트 검출
#
# 카드/세금계산서 영수증의 결정적 구조 시그널.
# 일반 영수증에도 등장 가능 — pos/card 모두에 가산하므로 false positive 영향 최소.
#
# 판정 기준:
#   - 1000 이상 정수 후보 amounts 추출 (콤마 또는 점 천단위 허용)
#   - a + b == c, a >= 1000, b/a ∈ [0.08, 0.12] (부가세율 ±2%p)
# ============================================================
def _detect_supply_vat_total_triple(text: str) -> bool:
    if not text:
        return False
    amounts: list[int] = []
    for m in re.finditer(r'(?<!\d)(\d{1,3}(?:[.,]\d{3})+|\d{4,})(?!\d)', text):
        s = m.group(1).replace(',', '').replace('.', '')
        try:
            n = int(s)
        except ValueError:
            continue
        if 1000 <= n <= 100_000_000:
            amounts.append(n)
    if len(amounts) < 3:
        return False
    distinct = sorted(set(amounts))
    distinct_set = set(distinct)
    for a in distinct:
        for b in distinct:
            if b >= a:
                continue
            ratio = b / a
            if not (0.08 <= ratio <= 0.12):
                continue
            if (a + b) in distinct_set:
                return True
    return False


def _invoice_statement_evidence(text: str) -> tuple[bool, dict]:
    compact = re.sub(r'\s+', '', text or '')
    if not compact:
        return False, {}

    title_hits = len(re.findall(r'\uac70\ub798\uba85\uc138\uc11c|\uac70\ub798\uba85\uc138\ud45c|\ub798\uba85\uc138\uc11c|\uba85\uc138\uc11c|\uc138\ud45c', compact))
    party_hits = len(re.findall(r'\uacf5\uae09\uc790|\uacf5\uae09\ubc1b\ub294\uc790|\uacf5\uae09\ubc1b\ub294|\uacf5\uae09\ubc1b\ub208|\uacf5\uae09\ubc1b\ub294\uc790\ubcf4\uad00\uc6a9', compact))
    header_hits = len(re.findall(r'\uc0ac\uc5c5\uc790\ubc88\ud638|\ub4f1\ub85d\ubc88\ud638|\uc0c1\ud638|\ub300\ud45c\uc790|\uc131\uba85|\uc8fc\uc18c|\uc0ac\uc5c5\uc7a5', compact))
    table_hits = len(re.findall(r'\ud488\uba85|\ud488\ubaa9|\uaddc\uaca9|\uc218\ub7c9|\ub2e8\uac00|\ube44\uace0|\uc81c\uc870\ubc88\ud638|\uc720\ud6a8\uae30\uac04|\ubcf4\ud5d8\ucf54\ub4dc|\uc81c\uc870\ud68c\uc0ac', compact))
    amount_hits = len(re.findall(r'\uacf5\uae09\uac00\uc561|\uc138\uc561|\ud569\uacc4\uae08\uc561|\uacf5\uae09\ub300\uac00|\uae08\uc561', compact))
    ok = (
        (title_hits >= 1 and header_hits >= 1 and (table_hits >= 2 or amount_hits >= 1))
        or (party_hits >= 1 and header_hits >= 2 and (table_hits >= 1 or amount_hits >= 1))
        or (table_hits >= 3 and amount_hits >= 1 and header_hits >= 2)
    )
    return ok, {
        "title": title_hits,
        "party": party_hits,
        "header": header_hits,
        "table": table_hits,
        "amount": amount_hits,
    }


# ============================================================
# 보조: 카드 브랜드 prefix 로 쓰이는 은행명 차감
#
# '농협비씨카드', '신한카드' 처럼 은행명이 카드명 일부로 등장한 경우
# bank_n 에서 그만큼 차감해 bank_slip 오분류를 방지.
#
# 현재 BANK_BRAND_SIGNALS 가 단독 한글 약어를 보유하지 않으므로
# 정상 경로에서는 이 차감이 0 이지만, 안전장치로 유지.
# ============================================================
def _bank_to_card_disambig(text: str) -> int:
    if not text:
        return 0
    count = 0
    for prefix in BANK_TO_CARD_DISAMBIG_PREFIXES:
        # 은행 prefix 직후 4자 이내에 카드 키워드가 오는 패턴
        pat = re.compile(
            prefix + r'\s*.{0,4}?(?:비씨\s*카드|체크\s*카드|신용\s*카드|IC\s*카드|카드(?!사)|VISA|MASTER|JCB|AMEX)',
            re.I,
        )
        count += len(pat.findall(text))
    return count


# ============================================================
# 메인 분류기
# ============================================================
def classify_document(full_text: str) -> dict:
    """OCR 전체 텍스트에서 시그널 가중합으로 문서 유형 분류.

    Returns:
        {
            "type":   "receipt_pos" | "receipt_card" | "medical_receipt" |
                       "bank_slip" | "form_or_handwritten" | "unknown",
            "scores": {pos, card, bank, form, medical, bank_struct, layout_svt},
            "hits":   {pos, card_strict, card_fuzzy, card_brand,
                       bank_struct, bank_brand, form, medical},
            "guards": {bank_to_card_subtract, layout_supply_vat_total},
        }
    """
    text = re.sub(r'\s+', '', full_text or '')

    # --- 시그널 카운트 ---
    pos_n,        pos_hits         = _count_hits(POS_SIGNALS,         text)
    cs_n,         cs_hits          = _count_hits(CARD_SIGNALS_STRICT, text)
    cf_n,         cf_hits          = _count_hits(CARD_SIGNALS_FUZZY,  text)
    cb_n,         cb_hits          = _count_hits(CARD_BRAND_SIGNALS,  text)
    bs_n,         bs_hits          = _count_hits(BANK_STRUCT_SIGNALS, text)
    bb_n,         bb_hits          = _count_hits(BANK_BRAND_SIGNALS,  text)
    form_n,       form_hits        = _count_hits(FORM_SIGNALS,        text)
    medical_n,    medical_hits     = _count_hits(MEDICAL_SIGNALS,     text)

    # --- 구조/가드 시그널 ---
    layout_svt_triple = _detect_supply_vat_total_triple(full_text or '')
    bank_subtract     = _bank_to_card_disambig(text)
    invoice_ok, invoice_evidence = _invoice_statement_evidence(full_text or '')

    # --- 종합 ---
    # card_n: strict + fuzzy + brand + (layout +1 if triplet)
    card_n = cs_n + cf_n + cb_n + (1 if layout_svt_triple else 0)

    # bank_n: struct + brand - 동음이의 차감
    bank_n = max(0, bs_n + bb_n - bank_subtract)

    # bank_struct_n: 단독 변수로 분류 임계 조건에 사용
    bank_struct_n = bs_n

    # --- 결정 트리 ---
    #
    # 우선순위:
    #   1. form_n ≥ 2 (수기/폼)
    #   2. bank_slip (구조 시그널 충족 필요)
    #   3. medical_receipt (강한 의료 시그널 ≥ 2)
    #   4. receipt_card (카드 시그널 합 ≥ 2)
    #   5. receipt_pos (pos ≥ 2)
    #   6. 단일 시그널 fallback (form/card/medical/pos 순)
    #   7. bank_struct ≥ 1 만 있으면 bank_slip
    #   8. receipt_like 증거 있으면 receipt_pos
    #   9. unknown
    #
    # 핵심 정책:
    #   - bank_slip 은 구조 시그널(BANK_STRUCT) 이 1개 이상 있어야 확정 가능.
    #     단순 은행명 1회 출현으로는 bank_slip 결정하지 않음.
    #   - layout_svt_triple(+공급가액/VAT/합계 검산)이 있으면 card 측에 이미 +1 가산되어
    #     bank 와의 우선순위 다툼에서 카드/영수증 쪽이 유리하다.

    if invoice_ok:
        doc_type = "invoice_statement"

    elif form_n >= 2 and form_n >= max(pos_n, card_n, bank_n, medical_n):
        doc_type = "form_or_handwritten"

    # bank_slip 강한 결정: 구조 시그널 ≥ 2 또는 (구조 ≥ 1 + 브랜드 ≥ 1)
    elif (
        (bank_struct_n >= 2 or (bank_struct_n >= 1 and bb_n >= 1))
        and bank_n > card_n
        and bank_n > pos_n
        and bank_n > medical_n
    ):
        doc_type = "bank_slip"

    # 의료 영수증
    elif medical_n >= 2 and medical_n >= card_n and medical_n >= max(pos_n - 1, 0):
        doc_type = "medical_receipt"

    # 카드 매출전표
    elif card_n >= 2 and card_n >= pos_n:
        doc_type = "receipt_card"

    # 일반 영수증
    elif pos_n >= 2 and pos_n >= card_n:
        doc_type = "receipt_pos"

    # 단일 시그널 fallback (낮은 신뢰)
    elif form_n >= 1 and form_n >= max(pos_n, card_n, bank_n, medical_n):
        doc_type = "form_or_handwritten"
    elif card_n >= 1 and card_n >= max(pos_n, bank_n, medical_n):
        doc_type = "receipt_card"
    elif medical_n >= 1 and medical_n >= max(pos_n, card_n):
        doc_type = "medical_receipt"
    elif pos_n >= 1 and pos_n >= bank_n:
        doc_type = "receipt_pos"

    # bank 단일 fallback — 반드시 구조 시그널이 있을 때만
    elif bank_struct_n >= 1:
        doc_type = "bank_slip"

    # 마지막 보정: 영수증-like 증거가 있으면 receipt_pos
    elif _receipt_like_unknown_evidence(full_text or '')[0] and bank_struct_n == 0 and form_n == 0:
        doc_type = "receipt_pos"

    else:
        doc_type = "unknown"

    receipt_like_ok, receipt_like_evidence = _receipt_like_unknown_evidence(full_text or '')

    return {
        "type": doc_type,
        "scores": {
            "pos":          pos_n,
            "card":         card_n,
            "bank":         bank_n,
            "form":         form_n,
            "medical":      medical_n,
            "bank_struct":  bank_struct_n,
            "layout_svt":   1 if layout_svt_triple else 0,
        },
        "hits": {
            "pos":         pos_hits,
            "card_strict": cs_hits,
            "card_fuzzy":  cf_hits,
            "card_brand":  cb_hits,
            "bank_struct": bs_hits,
            "bank_brand":  bb_hits,
            "form":        form_hits,
            "medical":     medical_hits,
        },
        "guards": {
            "bank_to_card_subtract":   bank_subtract,
            "layout_supply_vat_total": layout_svt_triple,
            "invoice_statement":       invoice_evidence,
        },
        "receipt_like_unknown_evidence": receipt_like_evidence,
    }
