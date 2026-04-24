"""
영수증 총합계금액 추출 모듈.

흐름:
  1) extract_amount_candidates(rows)            — 모든 라인에서 금액 후보를 넓게 수집
  2) synthesize_supply_vat_totals(candidates)   — 공급가액+부가세=합계 합성 후보 생성
  3) score_amount_candidate(cand, all)          — 합계 후보 점수화 (키워드/위치/검산/부정문맥)
  4) select_best_total_amount(candidates)       — 최고점 후보 선택 + 디버그 메타 반환

정책:
  - 일반 영수증군 성능 최우선 (합계/총계/결제금액 키워드 기반)
  - 오탐 방지: 사업자번호/전화/승인번호/공급가액/부가세/잔액/계좌 등은 감점
  - bank_slip/form_or_handwritten: 사후 정책(main.py)에서 보수적 suppression
  - 총합계금액은 OCR 결과 기반 필드 (GT/autofill 참조 금지)
  - 잘못된 금액을 채택하느니 비워두는 쪽이 낫다
"""
import re


# ---- 숫자 정규화 ----

_OCR_DIGIT_FIX = {
    'O': '0', 'o': '0', 'Q': '0',
    'l': '1', 'I': '1', '|': '1',
    'S': '5', 's': '5',
    'B': '8',
    'Z': '2',
}


def _fix_ocr_digits(s: str) -> str:
    return "".join(_OCR_DIGIT_FIX.get(c, c) for c in s)


def _clean_number_text(s: str) -> str:
    """OCR 오인식 숫자 치환 + 점구분(33.000 → 33,000) 보정"""
    s = _fix_ocr_digits(s)
    s = re.sub(r'(\d)\.(\d{3})(?!\d)', r'\1,\2', s)
    return s


def _to_int(formatted_or_bare: str) -> int | None:
    digits = re.sub(r'[^\d]', '', formatted_or_bare)
    if not digits:
        return None
    try:
        return int(digits)
    except ValueError:
        return None


def _reasonable_amount(n: int) -> bool:
    return 100 <= n <= 500_000_000


# ---- 날짜/시간/전표번호 스팬 (금액 후보에서 제외) ----

_DATE_PATTERNS = [
    re.compile(r'(?:19|20)\d{2}\s?[./\-년]\s?\d{1,2}\s?[./\-월]\s?\d{1,2}\s?일?'),
    re.compile(r'(?<!\d)\d{2}\s?[./\-]\s?\d{1,2}\s?[./\-]\s?\d{1,2}(?!\d)'),
    re.compile(r'\d{1,2}:\d{2}(?::\d{2})?(?!\d)'),
    # 전표/영수 ID: 2025102510000032 처럼 YYYY + MMDD + 숫자 긴 꼬리
    re.compile(r'(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3,}'),
]


def _get_span_mask(text: str) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    for p in _DATE_PATTERNS:
        for m in p.finditer(text):
            spans.append((m.start(), m.end()))
    return spans


def _overlaps(pos_start: int, pos_end: int, spans: list[tuple[int, int]]) -> bool:
    for s, e in spans:
        if pos_start < e and pos_end > s:
            return True
    return False


# ---- 후보 수집 ----

def _extract_numbers_from_text(text: str) -> list[tuple[int, str, str]]:
    """한 텍스트 조각에서 금액 후보 숫자 추출.
    반환: [(value, formatted, pattern_tag), ...]
      pattern_tag: 'comma' | 'ocr_colon' | 'won_suffix' | 'bare'
    """
    out: list[tuple[int, str, str]] = []
    cleaned = _clean_number_text(text)
    spans_cleaned = _get_span_mask(cleaned)
    spans_raw = _get_span_mask(text)

    # 1. 천단위 콤마 (33,000 / 1,234,567)
    for m in re.finditer(r'\d{1,3}(?:,\d{3})+', cleaned):
        if _overlaps(m.start(), m.end(), spans_cleaned):
            continue
        n = _to_int(m.group(0))
        if n is not None and _reasonable_amount(n):
            out.append((n, f"{n:,}", 'comma'))

    # 2. OCR 콜론/세미콜론 오인식 (1:750, 33;000)
    for m in re.finditer(r'(?<!\d)\d{1,3}[:;]\d{3}(?:[:;]\d{3})*(?!\d)', text):
        if _overlaps(m.start(), m.end(), spans_raw):
            continue
        digits = re.sub(r'[:;]', '', m.group(0))
        n = _to_int(digits)
        if n is not None and _reasonable_amount(n):
            out.append((n, f"{n:,}", 'ocr_colon'))

    # 3. 원/￦/₩/KRW 접미사
    for m in re.finditer(r'(\d[\d,.]*)\s*(?:원|￦|₩|KRW)', cleaned, re.I):
        if _overlaps(m.start(1), m.end(1), spans_cleaned):
            continue
        n = _to_int(m.group(1))
        if n is not None and _reasonable_amount(n) and n >= 1000:
            out.append((n, f"{n:,}", 'won_suffix'))

    # 4. 콤마 없는 4~9자리 정수 (날짜/시간/전표번호 구간은 제외)
    #    양쪽 모두 '-' 도 경계로 취급 — 카드번호/전화번호 같은 하이픈 구분 식별자 조각 차단
    for m in re.finditer(r'(?<![\d,.\-])\d{4,9}(?![\d,.\-])', cleaned):
        if _overlaps(m.start(), m.end(), spans_cleaned):
            continue
        n = _to_int(m.group(0))
        if n is not None and _reasonable_amount(n) and n >= 1000:
            out.append((n, f"{n:,}", 'bare'))

    # 같은 값은 더 신뢰 높은 패턴 하나만 유지
    rank = {'comma': 0, 'won_suffix': 1, 'ocr_colon': 2, 'bare': 3}
    best: dict[int, tuple[int, str, str]] = {}
    for n, f, tag in out:
        prev = best.get(n)
        if prev is None or rank[tag] < rank[prev[2]]:
            best[n] = (n, f, tag)
    return list(best.values())


def extract_amount_candidates(rows, row_text_fn, source: str = "full_ocr") -> list[dict]:
    """모든 행에서 금액 후보를 수집 (원문/정규화값/위치/문맥 포함).

    source:
      - "full_ocr"     : 전체 이미지 1차 OCR
      - "amount_block" : 하단 금액 블록 재OCR
      - "upper_block"  : 상단 사업자 블록 재OCR
    """
    candidates: list[dict] = []
    total_rows = max(1, len(rows))
    for i, row in enumerate(rows):
        row_str = row_text_fn(row)
        row_norm = re.sub(r'\s+', '', row_str).lower()
        near_above = re.sub(r'\s+', '', row_text_fn(rows[i - 1])).lower() if i > 0 else ""
        near_below = re.sub(r'\s+', '', row_text_fn(rows[i + 1])).lower() if i + 1 < total_rows else ""

        for pts, text, conf in row:
            for value, formatted, pattern in _extract_numbers_from_text(text):
                candidates.append({
                    "value": value,
                    "formatted": formatted,
                    "pattern": pattern,
                    "row_idx": i,
                    "row_pos": i / max(1, total_rows - 1),
                    "text": text,
                    "conf": conf,
                    "context": row_norm,
                    "near_above": near_above,
                    "near_below": near_below,
                    "source": source,
                })
    return candidates


def merge_candidates(*cand_lists: list[dict]) -> list[dict]:
    """여러 소스의 후보 병합 — 같은 value 는 더 신뢰 높은 소스를 우선.

    우선순위 (낮을수록 우선):
      amount_block(0) > full_ocr(1) > synth_supply_vat(2) > upper_block(3)
    """
    source_rank = {"amount_block": 0, "full_ocr": 1, "synth_supply_vat": 2, "upper_block": 3}

    def key(c):
        return (source_rank.get(c.get("source", "full_ocr"), 1), -c.get("conf", 0))

    merged: dict[int, dict] = {}
    synth_values: set[int] = set()
    for lst in cand_lists:
        for c in lst:
            if c.get("source") == "synth_supply_vat":
                synth_values.add(c["value"])
            v = c["value"]
            if v not in merged or key(c) < key(merged[v]):
                merged[v] = c

    # cross_source 보너스 (synth 는 실 근거가 아니므로 제외)
    seen_by_src: dict[int, set[str]] = {}
    for lst in cand_lists:
        for c in lst:
            seen_by_src.setdefault(c["value"], set()).add(c.get("source", "full_ocr"))
    for v, srcs in seen_by_src.items():
        real_srcs = {s for s in srcs if s != "synth_supply_vat"}
        if v in merged and len(real_srcs) >= 2:
            merged[v] = {**merged[v], "cross_source": True, "source_set": sorted(real_srcs)}
        # 실 OCR 후보가 synth(공급가액+부가세) 결과와 값까지 일치 → 강한 교차 검증
        if (
            v in merged
            and v in synth_values
            and merged[v].get("source") != "synth_supply_vat"
        ):
            merged[v] = {**merged[v], "verified_by_synth": True}
    return list(merged.values())


def synthesize_supply_vat_totals(candidates: list[dict]) -> list[dict]:
    """공급가액 + 부가세(VAT 10%) = 합계 관계를 이용해 합성 후보 생성.

    조건 (오탐 억제):
      - 두 후보 모두 comma/won_suffix 패턴 (bare 제외)
      - 비율 0.08 ~ 0.12 (부가세율 10% ± 2%p)
      - 두 후보의 row 가 3행 이내로 인접
      - 두 후보 중 적어도 하나는 문서 하단부(row_pos >= 0.4)
      - a 자체가 이미 (supply + VAT) 합계처럼 보이면 제외
        (즉 a - b 에 해당하는 supply 후보가 이미 존재하면 a 는 total,
         이 때 (a, b) 쌍으로 합계를 또 만들면 중복/거짓 합계 생성됨)
    """
    values = {c["value"] for c in candidates}
    synth: list[dict] = []
    seen: set[int] = set()
    strong = {"comma", "won_suffix"}
    for a in candidates:
        if a["pattern"] not in strong:
            continue
        for b in candidates:
            if b is a or b["pattern"] not in strong:
                continue
            if a["value"] <= b["value"]:
                continue
            ratio = b["value"] / a["value"]
            if not (0.08 <= ratio <= 0.12):
                continue
            # a 가 이미 합계(other_supply + b)라면 skip — 중복 합성 방지
            if (a["value"] - b["value"]) in values:
                continue
            if abs(a["row_idx"] - b["row_idx"]) > 3:
                continue
            combined_ctx = (
                a.get("context", "") + " " + b.get("context", "") + " "
                + a.get("near_above", "") + " " + a.get("near_below", "") + " "
                + b.get("near_above", "") + " " + b.get("near_below", "")
            )
            if max(a["row_pos"], b["row_pos"]) < 0.4 and not (
                _TOTAL_OWN.search(combined_ctx)
                or _SEMI_PARTIAL.search(combined_ctx)
                or _SEMI_SALES.search(combined_ctx)
            ):
                continue
            total = a["value"] + b["value"]
            if not _reasonable_amount(total) or total in seen:
                continue
            seen.add(total)
            synth.append({
                "value": total,
                "formatted": f"{total:,}",
                "pattern": "synth",
                "row_idx": max(a["row_idx"], b["row_idx"]),
                "row_pos": max(a["row_pos"], b["row_pos"]),
                "text": f"[synth {a['formatted']}+{b['formatted']}]",
                "conf": min(a["conf"], b["conf"]) * 0.9,
                "context": "",
                "near_above": a["context"],
                "near_below": b["context"],
                "source": "synth_supply_vat",
                "synth_from": [a["formatted"], b["formatted"]],
            })
    return synth


# ---- 점수화 ----

# 긍정 키워드
_POS_STRONG = re.compile(
    r'총합계|합계금액|총계|전체합계|실결제|최종금액|최종합계'
)
# 합계 OCR 파손 변형(합시계/합일계 등) 수용: 합과 계 사이에 한글 1글자 허용
_POS_MID = re.compile(
    r'결제금액|받을금액|청구금액|지불금액|승인금액|총액|합계|합[가-힣]계'
)
_POS_LOW = re.compile(r'total|amount(?!\s*vat)', re.I)
# '합' 단독 라인 파편 (키워드 OCR이 부서진 경우)
_POS_WEAK_HAP = re.compile(r'(?:^|\s)합(?:$|\s)')

# 부정 키워드
_NEG_BIZ = re.compile(r'사업자|등록번호')
_NEG_PHONE = re.compile(r'전화|\btel\b|\bfax\b|팩스')
_NEG_TID = re.compile(
    r'전표번호|전표no|승인번호|거래번호|catid|cat1d|cat\s*id|\btid\b|terminal|'
    r'일련번호|가맹점번호|가맹no|vankey|영수번호'
)
_NEG_BANK = re.compile(
    r'거래후잔액|거래후진액|진액|잔액|잔고|balance|'
    r'계좌번호|계좌변호|계좌|수취계좌|수취인|수수료|'
    r'처리은행|입금액|출금액|이체수수료|송금수수료'
)
_NEG_RECEIPT_TAIL = re.compile(r'감사합니다|재발행|재인쇄|취소용|cancel')
_NEG_CARD_NUM = re.compile(r'\d{4}-\d{4}-\d{4}-\d{4}|\d{4}-\d{3,4}\*+|\*{3,}')

# 영수증 안내문(guidance) 감점용 — "50,000원 이하 무서명", "포상금 10만원 지급" 등
# 카드 영수증 하단에 흔히 붙는 안내 블록의 숫자가 합계로 오탐되는 것을 차단
_NEG_GUIDANCE = re.compile(
    r'이하|미만|무서명|서명\s*(?:생략|면제)|'
    r'포상금|신고\s*안내|신고안내|매출전표\s*사본|사본\s*을|우편\s*접수|'
    r'여신금융|여신금최|crefia|협회|'
    r'자\s*급\b|지\s*급(?!\s*금액|\s*은행|\s*카드)',
    re.I,
)

# 세미 부정 (부분 금액)
_SEMI_PARTIAL = re.compile(r'공급가액|과세물품|면세물품|부가세|\bvat\b|봉사료|할인', re.I)
_SEMI_SALES = re.compile(r'판매금액|소계|중간합계|순매출')
_TOTAL_OWN = re.compile(
    r'총합계|합계금액|총계|최종금액|최종합계|결제금액|받을금액|청구금액|실결제|합계|합[가-힣]계',
    re.I,
)
_TOTAL_FRAGMENTED = re.compile(r'합.{0,12}계')


def score_amount_candidate(cand: dict, all_candidates: list[dict]) -> dict:
    score = 0.0
    reasons: list[str] = []

    own_ctx = cand["context"]
    wide_ctx = own_ctx + " " + cand["near_above"] + " " + cand["near_below"]
    bracketed = " " + wide_ctx + " "
    own_amount_values = sorted({n for n, _, _ in _extract_numbers_from_text(own_ctx)})
    fragmented_total_max = (
        "합" in own_ctx
        and cand.get("pattern") in {"comma", "won_suffix", "ocr_colon"}
        and len(own_amount_values) >= 2
        and cand["value"] == own_amount_values[-1]
    )

    # 긍정 키워드
    matched_strong_pos = False
    if _POS_STRONG.search(wide_ctx):
        score += 55
        reasons.append("+55 총합계/합계금액/최종금액 키워드")
        matched_strong_pos = True
    elif _POS_MID.search(wide_ctx):
        score += 40
        reasons.append("+40 결제/청구/승인/합계 키워드")
        matched_strong_pos = True
    elif _POS_LOW.search(wide_ctx):
        score += 20
        reasons.append("+20 total/amount 키워드")

    if not matched_strong_pos and _TOTAL_FRAGMENTED.search(own_ctx):
        score += 40
        reasons.append("+40 합계 라벨 파편 문맥")
        matched_strong_pos = True

    if not matched_strong_pos and _POS_WEAK_HAP.search(bracketed):
        score += 18
        reasons.append("+18 인접 행 '합' 단독 — 합계 키워드 파편 추정")

    own_has_total = bool(
        _TOTAL_OWN.search(own_ctx)
        or _POS_WEAK_HAP.search(f" {own_ctx} ")
        or _TOTAL_FRAGMENTED.search(own_ctx)
        or fragmented_total_max
    )
    near_has_total = bool(_TOTAL_OWN.search(cand["near_above"] + " " + cand["near_below"]))
    own_has_partial = bool(_SEMI_PARTIAL.search(own_ctx) or _SEMI_SALES.search(own_ctx))
    near_has_partial = bool(
        _SEMI_PARTIAL.search(cand["near_above"] + " " + cand["near_below"])
        or _SEMI_SALES.search(cand["near_above"] + " " + cand["near_below"])
    )

    if own_has_total and not own_has_partial:
        score += 26
        reasons.append("+26 본문 행에 합계 문맥 직접 존재")
    elif own_has_total:
        score += 4
        reasons.append("+4 본문 행에 합계 문맥 존재")
        if fragmented_total_max:
            score += 24
            reasons.append("+24 합계 파편 행의 최대 금액")
    elif near_has_total and near_has_partial:
        score += 18
        reasons.append("+18 인접 행 공급가액/부가세 뒤의 합계 문맥")
    elif near_has_total:
        score += 10
        reasons.append("+10 인접 행 합계 문맥")

    # 원/￦ 단위 접미
    if re.search(r'원|￦|₩|KRW', cand["text"], re.I):
        score += 12
        reasons.append("+12 원/￦ 단위 접미")

    # 위치 가산점 (영수증 합계는 보통 하단)
    if cand["row_pos"] >= 0.75:
        score += 20
        reasons.append("+20 하단부 위치")
    elif cand["row_pos"] >= 0.55:
        score += 10
        reasons.append("+10 중하단 위치")
    elif cand["row_pos"] <= 0.25:
        score -= 10
        reasons.append("-10 상단부 위치 (합계 가능성 낮음)")

    # 포맷 품질
    if cand["pattern"] == "comma":
        score += 10
        reasons.append("+10 천단위 콤마 포맷")
    elif cand["pattern"] == "won_suffix":
        score += 10
        reasons.append("+10 '원' 접미 포맷")
    elif cand["pattern"] == "ocr_colon":
        score -= 4
        reasons.append("-4 OCR 콜론 오인식 복구")
    elif cand["pattern"] == "bare":
        score -= 14
        reasons.append("-14 콤마 없는 단순 숫자")
        if not matched_strong_pos:
            score -= 10
            reasons.append("-10 bare + 합계 키워드 부재")
    # synth 는 포맷 가점/감점 없음 (source 보정으로 처리)

    # 부정 문맥 — 해당 숫자가 속한 행(own_ctx)에 있을 때만 감점
    # (near_above/below 의 '승인번호' 줄이 인접해 있다고 전체 금액을 깎지는 않음)
    if _NEG_BIZ.search(own_ctx):
        score -= 60
        reasons.append("-60 사업자/등록번호 문맥")
    if _NEG_PHONE.search(own_ctx):
        score -= 60
        reasons.append("-60 전화/FAX 문맥")
    if _NEG_TID.search(own_ctx):
        if own_has_total:
            score -= 22
            reasons.append("-22 합계 행 내부의 전표/승인번호 잡음")
        else:
            score -= 70
            reasons.append("-70 전표/승인번호/가맹점번호 문맥")
    if _NEG_BANK.search(own_ctx):
        score -= 55
        reasons.append("-55 잔액/계좌/수수료/수취인 문맥")
    if _NEG_CARD_NUM.search(own_ctx):
        score -= 40
        reasons.append("-40 카드번호 마스킹 패턴")
    if _NEG_GUIDANCE.search(own_ctx):
        score -= 80
        reasons.append("-80 영수증 안내문(이하/무서명/포상금 등) 숫자")
    elif _NEG_GUIDANCE.search(cand["near_above"] + " " + cand["near_below"]):
        if own_has_total:
            score -= 8
            reasons.append("-8 합계 행 주변 안내문")
        else:
            score -= 30
            reasons.append("-30 인접 행이 안내문 (간접 근거)")

    # 세미 부정 (부분 금액)
    if _SEMI_PARTIAL.search(own_ctx):
        if own_has_total:
            score -= 8
            reasons.append("-8 합계 행에 섞인 공급가액/부가세 라벨")
        else:
            score -= 25
            reasons.append("-25 공급가액/부가세/봉사료 (부분 금액)")
    if _SEMI_SALES.search(own_ctx):
        if own_has_total:
            score -= 4
            reasons.append("-4 합계 행에 섞인 판매금액/소계 라벨")
        else:
            score -= 12
            reasons.append("-12 판매금액/소계 (합계보다 약함)")

    # 문서 최하단 bare 억제 (바코드/전표꼬리 숫자)
    if cand["row_pos"] >= 0.90 and cand["pattern"] == "bare" and not matched_strong_pos:
        score -= 30
        reasons.append("-30 문서 최하단 bare (바코드/전표꼬리 의심)")
    if _NEG_RECEIPT_TAIL.search(wide_ctx) and cand["pattern"] == "bare" and not matched_strong_pos:
        score -= 20
        reasons.append("-20 '감사합니다/재발행' 부근 bare")

    # OCR 신뢰도
    conf_bonus = (cand["conf"] - 0.5) * 10
    score += conf_bonus
    if cand["conf"] >= 0.85:
        reasons.append(f"+{conf_bonus:.1f} OCR 신뢰도 {cand['conf']:.2f}")
    elif cand["conf"] < 0.5:
        reasons.append(f"{conf_bonus:.1f} OCR 저신뢰도 {cand['conf']:.2f}")

    # 소스별 보정 (amount_block 은 하단 합계 영역 재OCR 결과 — 강하게 우선)
    src = cand.get("source", "full_ocr")
    if src == "amount_block":
        score += 28
        reasons.append("+28 하단 금액 블록 재OCR 소스")
    elif src == "upper_block":
        score -= 20
        reasons.append("-20 상단 사업자 블록 소스 (합계 가능성 낮음)")
    elif src == "synth_supply_vat":
        score += 55
        reasons.append("+55 공급가액+부가세=합계 검산 합성")
        # synth 구성 숫자 근처에 공급가액/부가세 라벨이 있으면 추가 신뢰
        combined_src_ctx = cand.get("near_above", "") + " " + cand.get("near_below", "")
        if re.search(r'공급가액|판매금액|과세물품|면세물품', combined_src_ctx) or \
           re.search(r'부가세|\bvat\b|부가가치세', combined_src_ctx, re.I):
            score += 15
            reasons.append("+15 합성 구성 숫자가 공급가액/부가세 라벨 인접")

    # 실 OCR 후보가 synth 와 값 일치 → 합계 가능성 매우 높음 (교차 검증)
    if cand.get("verified_by_synth"):
        score += 42
        reasons.append("+42 실 후보 값이 공급가액+부가세 합성과 일치 (교차 검증)")

    # 교차 소스 일치 (실 소스 ≥2)
    if cand.get("cross_source"):
        score += 14
        reasons.append("+14 복수 실소스 교차 일치")

    # 검산 보너스: 본인 값이 두 후보의 합과 같으면 합계일 가능성 매우 높음
    for a in all_candidates:
        if a is cand or a["value"] >= cand["value"]:
            continue
        for b in all_candidates:
            if b is cand or b is a or b["value"] >= cand["value"]:
                continue
            if a["value"] + b["value"] == cand["value"]:
                score += 45
                reasons.append(f"+45 검산 성공 ({a['formatted']}+{b['formatted']}={cand['formatted']})")
                if own_has_total or near_has_total:
                    score += 18
                    reasons.append("+18 검산 성공 + 합계 문맥 동시 충족")
                break
        else:
            continue
        break

    if own_has_partial and not own_has_total:
        for other in all_candidates:
            if other is cand:
                continue
            for total in all_candidates:
                if total is cand or total is other:
                    continue
                if cand["value"] + other["value"] != total["value"]:
                    continue
                total_ctx = (
                    _TOTAL_OWN.search(total.get("context", ""))
                    or _TOTAL_OWN.search(total.get("near_above", "") + " " + total.get("near_below", ""))
                    or total.get("source") == "synth_supply_vat"
                )
                if total_ctx:
                    score -= 28
                    reasons.append(
                        f"-28 부분 금액 쌍({cand['formatted']}+{other['formatted']})이 더 큰 합계 후보 {total['formatted']} 구성"
                    )
                    break
            else:
                continue
            break

    if own_has_total and cand.get("pattern") in {"comma", "won_suffix"}:
        score += 8
        reasons.append("+8 합계 문맥의 실 OCR 금액 우대")

    if own_has_total:
        ctx_amount_values = own_amount_values
        if len(ctx_amount_values) >= 2:
            if cand["value"] == ctx_amount_values[-1]:
                score += 18
                reasons.append("+18 합계 문맥 내 최대 금액")
            elif cand["value"] < ctx_amount_values[-1]:
                score -= 18
                reasons.append(f"-18 합계 문맥 내 더 큰 금액 후보 {ctx_amount_values[-1]:,} 존재")

    return {"score": round(score, 2), "reasons": reasons}


# ---- 최종 선택 ----

def select_best_total_amount(candidates: list[dict]) -> tuple[str, dict]:
    """점수화 후 최고점 후보 선택.

    debug.status:
      - 'no_candidate'   : 후보 자체 없음
      - 'all_rejected'   : 모든 후보가 강한 부정 문맥
      - 'low_confidence' : 점수 < 5 (채택은 하지만 신뢰도 낮음)
      - 'selected'       : 정상 채택
    """
    if not candidates:
        return "", {
            "status": "no_candidate",
            "reason": "raw OCR에서 금액 후보 자체가 없음",
            "candidates": [],
            "selected": None,
            "rejected_top": [],
        }

    scored: list[dict] = []
    for c in candidates:
        s = score_amount_candidate(c, candidates)
        scored.append({**c, **s})

    scored.sort(key=lambda x: (-x["score"], -x["value"], -x["row_pos"]))
    best = scored[0]

    rejected_top = [
        {
            "value": c["formatted"],
            "score": c["score"],
            "source": c.get("source"),
            "pattern": c["pattern"],
            "row_pos": round(c["row_pos"], 3),
            "reasons": c["reasons"],
        }
        for c in scored[1:4]
    ]

    if best["score"] <= -30:
        return "", {
            "status": "all_rejected",
            "reason": "모든 후보가 비-합계 문맥(사업자/전화/승인번호/잔액 등)에서만 검출됨",
            "candidates": scored[:10],
            "selected": None,
            "rejected_top": rejected_top,
        }

    status = "selected"
    if best["score"] < 5:
        status = "low_confidence"

    return best["formatted"], {
        "status": status,
        "reason": "; ".join(best["reasons"]),
        "accept_reasons": best["reasons"],
        "rejected_top": rejected_top,
        "candidates": scored[:10],
        "selected": {
            "value": best["formatted"],
            "row_idx": best["row_idx"],
            "row_pos": round(best["row_pos"], 3),
            "pattern": best["pattern"],
            "score": best["score"],
            "reasons": best["reasons"],
            "text": best["text"],
            "source": best.get("source"),
            "synth_from": best.get("synth_from"),
            "cross_source": bool(best.get("cross_source")),
            "source_set": best.get("source_set"),
            "verified_by_synth": bool(best.get("verified_by_synth")),
        },
    }
