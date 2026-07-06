"""item_name_clean — 품명(itemName) 매칭 전처리 클리너.

목적: Paddle이 읽은 품명 문자열을 마스터 매칭(trigram) 직전에 정제한다.
  - **매칭 전용**이다. 사용자에게 보이는 셀 값은 건드리지 않는다([[project_master_match_baseline]]).
  - 규격(strength: mg/ML/g/T 등)은 기본 보존한다 — 마스터 item_nm이 규격을 포함하는
    경우가 많아, 규격을 지우면 top1이 급락한다(로컬 프록시 -9.6pp 확인).
  - 오염(선행 행번호/품목코드, lot, 날짜, 수량·금액, PTP/OCR 아티팩트)만 제거한다.

두 모집단:
  1) 공백 없는 단일토큰 읽기(~60%): 이미 깔끔 → 경량 정규화(O→0, PTP strip).
  2) 행-blob 읽기(~6%): OCR이 한 행 전체를 품명칸에 병합 → 품명 코어 추출 필요.

`clean(name, level=...)` 하나로 여러 정제 수준을 낸다. level 목록은 LEVELS.
psql trigram 스코어러가 각 level을 채점 → 실측으로 룰 확정(G0/G1).
"""
from __future__ import annotations
import re

# 한글 dosage-form 마커(제형): 품명 코어의 앵커.
_FORM = r'(?:서방정|서방캡슐|정제|캡슐|캅셀|캡|정|주사|주|액|시럽|산|과립|크림|로션|겔|젤|연고|패치|패취|좌제|점안|점비|흡입|환)'
_FORM_RE = re.compile(_FORM)
_HANGUL_RE = re.compile(r'[가-힣]')

_MONEY_RE = re.compile(r'^\d{1,3}(?:,\d{3})+(?:\.\d+)?$|^\d+\.\d{2}$')
_DATE_RE = re.compile(
    r'(?:19|20)\d{2}[./-]?\d{1,2}[./-]?\d{1,2}'   # yyyymmdd / yyyy.mm.dd
    r'|\b\d{2}[./-]\d{2}[./-]\d{2,4}\b')          # yy.mm.dd
_PTP_RE = re.compile(r'(?:ptp)+$', re.I)
_O2ZERO_RE = re.compile(r'(?<=\d)[Oo]|[Oo](?=\d)')


def _norm(s: str) -> str:
    """pg _nm() 등가: 소문자 + 공백/괄호 제거."""
    return re.sub(r'[\s()]+', '', s or '').lower()


def _o_to_zero(s: str) -> str:
    return _O2ZERO_RE.sub('0', s)


def _drop_ptp(s: str) -> str:
    return _PTP_RE.sub('', s)


def _is_hangul(tok: str) -> bool:
    return bool(_HANGUL_RE.search(tok))


def _is_junk_token(tok: str) -> bool:
    """이름과 무관한 오염 토큰? (금액/날짜/코드/lot/순수숫자). 한글 포함 토큰은 절대 junk 아님."""
    if _is_hangul(tok):
        return False
    if _MONEY_RE.match(tok):
        return True
    if _DATE_RE.fullmatch(tok):
        return True
    t = tok.strip('.,/')
    if not t:
        return True
    if t.isdigit() and len(t) >= 3:            # 행번호(짧음은 아래) / 코드 / 바코드
        return True
    if re.search(r'\d', t) and re.fullmatch(r'[A-Za-z0-9./\\$₩-]+', t) and len(t) >= 4:
        return True                            # lot/코드(영숫자, 한글X, 숫자포함)
    return False


def _strip_variant(raw: str) -> str:
    """오염 토큰만 제거, 나머지(품명·규격·제조사) 유지. 선행 짧은 행번호도 제거."""
    s = re.sub(r'^\s*\d{1,3}\s+', '', raw)     # 선행 행번호
    toks = [t for t in s.split() if not _is_junk_token(t)]
    return _drop_ptp(_o_to_zero(''.join(toks)))


def _form_tokens(raw: str, base: bool) -> str:
    """제형 마커를 포함한 한글 토큰(품명 코어)만 추출.
    base=True면 마지막 제형 마커 이후의 규격 꼬리까지 잘라 기저명만 남긴다."""
    s = _o_to_zero(raw)
    cores = [t for t in s.split() if _is_hangul(t) and _FORM_RE.search(t)]
    if not cores:
        return _strip_variant(raw)             # 제형 마커 없으면 strip 폴백
    out = []
    for t in cores:
        if base:
            m = list(_FORM_RE.finditer(t))
            t = t[:m[-1].end()]                # 마지막 제형 마커까지만
        out.append(t)
    return _drop_ptp(''.join(out))


def _core_tokens(raw: str) -> str:
    """오염 토큰 + **제조사**(제형마커 없는 한글 토큰) 제거, 품명+규격은 보존.
    = 메모리 승리 레시피(선행코드/제조사/행번호 제거·규격유지). 규격이 별도 토큰이어도 유지."""
    s = re.sub(r'^\s*\d{1,3}\s+', '', raw)          # 선행 행번호
    s = _o_to_zero(s)
    toks = [t for t in s.split() if not _is_junk_token(t)]
    has_form = any(_is_hangul(t) and _FORM_RE.search(t) for t in toks)
    out = []
    for t in toks:
        if has_form and _is_hangul(t) and not _FORM_RE.search(t):
            continue                                # 제조사 등 제형마커 없는 한글 토큰 제거
        out.append(t)
    return _drop_ptp(''.join(out))


LEVELS = ('raw', 'strip', 'form', 'formbase', 'core')


def clean(name: str, level: str = 'strip') -> str:
    """정규화된 매칭키 반환. **기본=strip (2026-07-06 psql 7416 실측 승자).**
    level:
      raw      = 정규화만(기준선). 전체 top1 61.2
      strip    = 오염(숫자/코드/날짜/금액) 토큰만 제거, 규격+제조사+이름 유지.
                 ★전체 top1 63.5(+2.3), 오염행 61.6(+6.1)/top10 +8.4 — **채택**
      form     = 제형 마커 앵커 코어추출(제조사 제거). 62.6 — strip보다 못함
      core     = 오염+제조사 제거, 규격 유지. 62.9 — strip보다 못함(제조사 제거가 손해)
      formbase = 규격 꼬리 제거. 45.8 — **폐기**(규격이 동명이품 구별신호)
    주: 진짜 큰 레버는 클린이 아니라 랭킹(top1 63.5 vs top10 90.5, GT완벽도 top1 70). [[project_master_match_baseline]]"""
    if not name:
        return ''
    if level == 'raw':
        return _norm(name)
    if level == 'strip':
        return _norm(_strip_variant(name))
    if level == 'form':
        return _norm(_form_tokens(name, base=False))
    if level == 'formbase':
        return _norm(_form_tokens(name, base=True))
    if level == 'core':
        return _norm(_core_tokens(name))
    raise ValueError(f'unknown level: {level}')


if __name__ == '__main__':
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    for s in ['B2110 관류용식염-L 1000ML 2029/04/14',
              '기넥신에프정4Omg100TPTP',
              '5001710 라코르정120/12.5mg30T 2F001 2029.02.03 50 19,809 1,089,4',
              '10 641606150 대웅 크레젯정 10/5/100T 72,058 1,441,160 E07163 29010',
              '아모크라정375mg']:
        print(repr(s))
        for lv in LEVELS:
            print(f'   {lv:9s} {clean(s, lv)!r}')
