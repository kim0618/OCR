"""master_match — 품목 마스터 자동매칭 (②매칭 트랙 G4 런타임).

벤치(_match_engine.sql)와 같은 파이프라인의 파이썬 이식:
  clean(war fn_get_item_name_clean 등가: 괄호쌍 있으면 첫 greedy \\(.*\\) 제거) + 공백 strip
  → pg_trgm 등가 trigram 유사도로 마스터 전수 스코어(역색인이라 실질 후보만)
  → rerank: 유사도 DESC, |bp1 − 단가| ASC (단가 결측 = 유사도-only, SQL NULLS LAST 등가)
  → top1이 floor 이상이면 itemNameMaster/itemCode 빈칸 채움.

마스터 = build_master.sql 산출 master_dict.json (AWS 무DB 정적 사전).
파일이 없으면 조용히 비활성(응답 무영향) — 배포 시 사전 파일이 함께 가야 켜진다.

pg_trgm 등가성(벤치 psql과 top1 일치 검증은 eval/match_parity_check.py):
  - lower → 단어 = 영숫자 연속(비영숫자는 구분자, '_'도 구분자)
  - 단어마다 '  '+word+' ' 패딩 후 3-gram, 전 단어 집합 union(중복 제거)
  - similarity = |교집합| / |합집합|
"""
from __future__ import annotations

import json
import os
import re
import threading
import unicodedata
from typing import Any

# G3 스윕 실측(0~0.5): floor↑ = 배정중 정확도↑/coverage↓/spurious↓.
# 0.20 = coverage 85.9 / match_acc 82.8 / spurious 39.1 균형점(잠정 — G3 확정 대상).
# V5 jamo-trigram 스케일 재보정: 자모 gram은 음절보다 sim이 높게 나와 floor 상향.
# 063 스윕 실측: 0.25=+384(최적) / 0.30=+279 / 0.35=+75 / 0.40=-216.
MATCH_SIM_FLOOR = 0.25

_DICT_CANDIDATES = (
    # AWS 배포 위치(ocr-server/ 루트) 우선, 로컬 개발은 eval 데이터 폴더
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "master_dict.json"),
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "eval", "data",
                 "invoice_war", "master_dict.json"),
)

_WORD = re.compile(r"[^\W_]+", re.UNICODE)
_PAREN = re.compile(r"\(.*\)")          # greedy: 첫 '(' ~ 마지막 ')' (war 함수와 동일)
_NUM = re.compile(r"\d[\d,]*(?:\.\d+)?")

# 쿼리 프리클린용 junk 토큰 판별 (eval/item_name_clean.py 'strip' 승자 레시피 이식).
_Q_HANGUL = re.compile(r"[가-힣]")
_Q_MONEY = re.compile(r"^\d{1,3}(?:,\d{3})+(?:\.\d+)?$|^\d+\.\d{2}$")
_Q_DATE = re.compile(r"(?:19|20)\d{2}[./-]?\d{1,2}[./-]?\d{1,2}|\b\d{2}[./-]\d{2}[./-]\d{2,4}\b")
_Q_PTP = re.compile(r"(?:ptp)+$", re.I)
_Q_O2ZERO = re.compile(r"(?<=\d)[Oo]|[Oo](?=\d)")
# 용량/규격 토큰: junk로 오인 제거 금지 (dose 구별신호 보존).
_Q_DOSEISH = re.compile(
    r"\d\s*(?:mg|mcg|㎍|㎎|g|㎖|ml|l|iu|%|밀리그람|밀리그램|미리그람|미리그램|밀리리터|그람"
    r"|정|캡슐|캅셀|캡|t|c|v|정제|포|병|앰플|바이알)", re.I)
_Q_DOSECOMBO = re.compile(r"^\d+(?:\.\d+)?(?:/\d+(?:\.\d+)?)+", re.I)


def _q_is_doseish(tok: str) -> bool:
    to = _Q_O2ZERO.sub("0", tok)
    return bool(_Q_DOSEISH.search(to) or _Q_DOSECOMBO.match(to))


def _q_is_junk(tok: str) -> bool:
    """이름과 무관한 오염 토큰(금액/날짜/코드/lot/순수숫자). 한글·용량 토큰은 junk 아님."""
    if _Q_HANGUL.search(tok):
        return False
    if _Q_MONEY.match(tok) or _Q_DATE.fullmatch(tok):
        return True
    t = tok.strip(".,/")
    if not t:
        return True
    if t.isdigit() and len(t) >= 3:                     # 코드/바코드/행번호
        return True
    if re.search(r"\d", t) and re.fullmatch(r"[A-Za-z0-9./\\$₩-]+", t) and len(t) >= 4:
        return True                                      # lot/코드(영숫자, 한글X, 숫자포함)
    return False

# 랭킹 tiebreak용 규격 토큰 (V3, match_rank_bench 실측 code +2.5pp @floor0.2)
# V4: '밀리그램/미리그램'(램) 별칭 추가 — 기존엔 '밀리그람'(람)만 있어 송장 표기
# '20밀리그램'의 용량이 안 잡혀 dose 가드가 무력화(에소메졸 20mg→10mg 오픽류).
_DOSE = re.compile(
    r"(\d+(?:\.\d+)?(?:/\d+(?:\.\d+)?)*)\s*"
    r"(mg|mcg|㎍|㎎|g|㎖|ml|l|iu|%|단위|밀리그람|미리그람|밀리그램|미리그램|밀리리터|그람)", re.I)
_UNIT_ALIAS = {"㎍": "mcg", "㎎": "mg", "㎖": "ml", "밀리그람": "mg", "미리그람": "mg",
               "밀리그램": "mg", "미리그램": "mg",
               "밀리리터": "ml", "그람": "g", "단위": "iu"}
_PACK = re.compile(r"(\d+)\s*(t|c|v|정|캡슐|캅셀|포|병|앰플|amp|vial|바이알|매|개)", re.I)


def dose_tokens(s) -> set:
    """용량 토큰 {(수, 단위)}. 복합(25/500mg)은 분해, 단위 별칭 정규화."""
    out = set()
    for nums, unit in _DOSE.findall(str(s or "").lower()):
        u = _UNIT_ALIAS.get(unit, unit)
        for n in nums.split("/"):
            out.add((n.rstrip("0").rstrip(".") if "." in n else n.lstrip("0") or "0", u))
    return out


def pack_tokens(s) -> set:
    return {(n.lstrip("0") or "0", u.lower()) for n, u in _PACK.findall(str(s or "").lower())}


def _jac(a, b):
    if not a or not b:
        return None
    return len(a & b) / len(a | b)


_PAREN_TOK = re.compile(r"\(([^)]*)\)")


def paren_tokens(s) -> set:
    """괄호 안 토큰 집합(공백제거·대문자). 접미사 형제 SKU 구분용 — (병)/(PTP)/(한외)…"""
    return {re.sub(r"\s+", "", t).upper() for t in _PAREN_TOK.findall(str(s or ""))
            if re.sub(r"\s+", "", t)}


def _sfx_score(qp: set, cp: set) -> int:
    """쿼리 괄호토큰 ↔ 후보 괄호토큰 힌트일치 수. 부분포함 양방향 허용
    ('(30T*1병)' ↔ '(병)' 매칭). exact-only면 병기형 힌트를 놓침(V4 실측)."""
    s = 0
    for ct in cp:
        for qt in qp:
            if qt == ct or (len(qt) >= 2 and qt in ct) or (len(ct) >= 2 and ct in qt):
                s += 1
                break
    return s


def dose_score(q_dose, q_pack, cand_nm, cand_unit):
    """규격 합치 0~1, None=정보없음(중립). dose 우선, pack 보조(2:1 가중)."""
    d = _jac(q_dose, dose_tokens(cand_nm))
    p = _jac(q_pack, pack_tokens(f"{cand_nm} {cand_unit}"))
    if d is None and p is None:
        return None
    if d is None:
        return 0.5 * p
    if p is None:
        return d
    return (2 * d + p) / 3


def clean_item_name(s: str) -> str:
    """war fn_get_item_name_clean + 공백 strip (벤치 qclean/nmclean과 동일)."""
    s = s or ""
    if "(" in s and ")" in s:
        s = _PAREN.sub("", s, count=1)
    return s.replace(" ", "")


def clean_query_name(name: str) -> str:
    """매칭 쿼리 전용 프리클린 — 파서 출력·사전(clean_item_name)은 불변.

    fallback 파서가 품명 앞에 끌어온 바코드/사업자·상품코드(숫자 5+자리)·행번호
    (숫자 1~3자리) 토큰과 말미 '//n' 아티팩트가 trigram 을 오염시켜, 사전에 있는
    정식명이 top30 후보에도 못 드는 실패(063 전수분해 B버킷 779행)를 만든다.
    선두 노이즈 토큰만 걷어내고 한글 약품토큰부터 보존한다.

    선두 노이즈뿐 아니라 이름 중간·끝의 junk(날짜/lot/금액/코드)까지 제거한다
    (eval/item_name_clean.py 'strip' 승자 레시피 이식 — psql 7416 실측 top1 +2.3pp).
    행-blob 읽기('라코르정120/12.5mg30T 2F001 2029.02.03 50 19,809')에서 큰 차이.
    괄호/공백 구조는 보존해 하류 랭킹(괄호 접미사·dose tiebreak)이 살아있게 한다.

    063 격리실측(동일 match, price=unitPrice): 선두만(구판) 대비 master +96 / 회귀 27
    (용량 토큰 보호로 dose 신호 유지, O→0 포함이 순이익). 전체 junk면 원문 유지."""
    s = str(name or "").strip()
    s = re.sub(r"//\s*\d*\s*$", "", s)           # 말미 '//1' 류 아티팩트
    s = re.sub(r"^\s*\d{1,3}\s+", "", s)         # 선행 행번호
    toks = []
    for t in s.split():
        if _q_is_doseish(t):                      # 용량/규격은 보존
            toks.append(t)
            continue
        if _q_is_junk(t):                         # 금액/날짜/lot/코드/바코드 제거
            continue
        toks.append(t)
    s = _Q_PTP.sub("", " ".join(toks).strip())   # 말미 PTP
    s = _Q_O2ZERO.sub("0", s)                     # 숫자 인접 O→0
    return s or (name or "").strip()


def trigrams(s: str) -> frozenset:
    """자모(jamo)-분해 trigram 집합 (V5).

    기존 pg_trgm 등가(음절 단위)는 OCR 한글자 오류(캡슬↔캡슐, 트르티저↔트르티전)에
    trigram 3개가 통째로 날아가 후보권 밖으로 밀림 — 063 전수분해 B버킷(사전엔
    있는데 top30밖) 802행의 주원인. NFD 자모 분해 후 gram하면 한 자모 차이는
    소량 손실이라 오류 내성이 구조적으로 높다.
    063 전면교체 실측(floor 0.25): master +384 (gain 474/reg 90), B버킷 top30
    도달 23%→. 주의: psql pg_trgm 벤치(match_parity_check)와는 이제 비등가."""
    out = set()
    s = unicodedata.normalize("NFD", s or "")
    for w in _WORD.findall(s.lower()):
        p = "  " + w + " "
        for i in range(len(p) - 2):
            out.add(p[i:i + 3])
    return frozenset(out)


def parse_price(v: Any):
    """셀 단가 → int. '950.00'/'1,234' 인지(digits-only는 950.00→95000이 됨). 결측=None."""
    m = _NUM.search(str(v or ""))
    if not m:
        return None
    try:
        return int(float(m.group().replace(",", "")))
    except ValueError:
        return None


# itembuycust rescue floor: 거래처 구매이력(작은 셋)이라 전역 floor(0.25)보다 낮게 안전.
# 065 실측(빈칸-only): 0.15=master+63/spurious0, 0.10=+66(오채움↑). 0.15 채택.
IBC_RESCUE_FLOOR = 0.15
IBC_STRICT_RERANK_FLOOR = 0.80


def _compact_alnum(value: object) -> str:
    """Case-insensitive alphanumeric form used by conservative containment gates."""
    return "".join(ch for ch in str(value or "").lower() if ch.isalnum())


class MasterMatcher:
    def __init__(self, item_dict: dict, itembuycust: dict | None = None):
        # entries: (item_cd, item_nm, bp1, unit, pyojun, bohum, trigram 크기) / 역색인: trigram -> [idx]
        self._cds: list[str] = []
        self._nms: list[str] = []
        self._bp1s: list[int] = []
        self._units: list[str] = []
        self._pyojuns: list[str] = []
        self._bohums: list[str] = []
        self._nmcleans: list[str] = []   # war fn_get_item_name_clean+공백strip (LIKE 단계용)
        self._tlens: list[int] = []
        self._index: dict[str, list[int]] = {}
        self._cd2i: dict[str, int] = {}
        self._itri_cache: dict[int, frozenset] = {}
        for cd, e in item_dict.items():
            e = e or {}
            nm = e.get("nm") or ""
            if not nm:
                continue
            nmc = clean_item_name(nm)
            tri = trigrams(nmc)
            if not tri:
                continue
            i = len(self._cds)
            self._cds.append(cd)
            self._nms.append(nm)
            self._bp1s.append(int(e.get("bp1") or 0))
            self._units.append(e.get("unit") or "")
            self._pyojuns.append(e.get("pyojun") or "")
            self._bohums.append(e.get("bohum") or "")
            self._nmcleans.append(nmc)
            self._tlens.append(len(tri))
            self._cd2i.setdefault(cd, i)
            for t in tri:
                self._index.setdefault(t, []).append(i)
        # itembuycust: 공급자 bizno -> {matcher index} (구매이력 품목)
        self._ibc: dict[str, set[int]] = {}
        for bz, cds in (itembuycust or {}).items():
            b = re.sub(r"\D", "", str(bz or ""))
            if len(b) != 10:
                continue
            idxs = {self._cd2i[c] for c in (cds or []) if c in self._cd2i}
            if idxs:
                self._ibc[b] = idxs

    def _itri(self, i: int) -> frozenset:
        t = self._itri_cache.get(i)
        if t is None:
            t = trigrams(self._nmcleans[i])
            self._itri_cache[i] = t
        return t

    def itembuycust_rescue(self, name: str, bizno: str, floor: float = IBC_RESCUE_FLOOR):
        """공급자 bizno의 구매이력 품목집합 안에서 jamo 최선 매칭(작은 셋→낮은 floor).
        → {itemCode, itemNameMaster, sim} | None. 빈칸 rescue 전용."""
        b = re.sub(r"\D", "", str(bizno or ""))
        idxs = self._ibc.get(b)
        if not idxs:
            return None
        q = trigrams(clean_item_name(clean_query_name(name)))
        if not q:
            return None
        best_i, best = -1, 0.0
        for i in idxs:
            tt = self._itri(i)
            inter = len(q & tt)
            u = len(q) + len(tt) - inter
            s = inter / u if u else 0.0
            if s > best:
                best, best_i = s, i
        if best_i < 0 or best < floor:
            return None
        return {"itemCode": self._cds[best_i], "itemNameMaster": self._nms[best_i],
                "sim": round(best, 4)}

    def itembuycust_strict_rerank(
        self,
        name: str,
        bizno: str,
        current: dict[str, Any] | None,
        floor: float = IBC_STRICT_RERANK_FLOOR,
    ) -> dict[str, Any] | None:
        """Return an observable, high-confidence purchase-history replacement.

        This is deliberately narrower than ``itembuycust_rescue``.  It may
        replace an existing global match only when the current SKU is outside
        the supplier's history, the best in-history top-30 candidate is at
        least as similar as the current candidate, and its canonical name is
        explicitly present in the OCR item name.  Otherwise the global match
        is preserved.
        """
        if not isinstance(current, dict):
            return None
        b = re.sub(r"\D", "", str(bizno or ""))
        idxs = self._ibc.get(b) if len(b) == 10 else None
        if not idxs:
            return None

        candidates = self.top_candidates(clean_query_name(name), 30)
        current_master_key = _compact_alnum(current.get("itemNameMaster"))
        current_candidate = next(
            (
                (float(sim), i)
                for sim, i in candidates
                if _compact_alnum(self._nms[i]) == current_master_key
            ),
            None,
        )
        if current_candidate is None:
            return None
        current_sim, current_i = current_candidate
        if current_i in idxs:
            return None
        proposed = next(((float(sim), i) for sim, i in candidates if i in idxs), None)
        if proposed is None:
            return None
        proposed_sim, proposed_i = proposed
        if proposed_sim < floor or proposed_sim < current_sim:
            return None
        if proposed_i == current_i:
            return None

        raw_key = _compact_alnum(name)
        master_name = self._nms[proposed_i]
        master_key = _compact_alnum(master_name)
        if master_key == current_master_key:
            return None
        if not raw_key or not master_key or master_key not in raw_key:
            return None
        return {
            "itemCode": self._cds[proposed_i],
            "itemNameMaster": master_name,
            "sim": round(proposed_sim, 4),
        }

    def top_candidates(self, name: str, k: int = 30):
        """유사도 상위 k 후보 → [(sim, idx)] sim DESC. 랭킹(tiebreak) 실험/재정렬용."""
        import heapq
        q = trigrams(clean_item_name(name))
        if not q:
            return []
        counts: dict[int, int] = {}
        for t in q:
            for i in self._index.get(t, ()):
                counts[i] = counts.get(i, 0) + 1
        qn = len(q)
        return heapq.nlargest(
            k, ((inter / (qn + self._tlens[i] - inter), i) for i, inter in counts.items()))

    def entry(self, i: int) -> dict:
        return {"itemCode": self._cds[i], "itemNameMaster": self._nms[i],
                "bp1": self._bp1s[i], "unit": self._units[i],
                "pyojun": self._pyojuns[i], "bohum": self._bohums[i]}

    def match(self, name: str, price=None, floor: float = MATCH_SIM_FLOOR,
              spec: str = "", quantity=None, amount=None):
        """→ {itemCode, itemNameMaster, sim} | None (floor 미달/무후보).

        랭킹(V4c+V4d, 063 전수 실측 V4c +183/회귀24 · V4d 가격구제 +117/회귀0):
        유사도 DESC → 규격 dose점수
        (일치>정보없음>모순) → 괄호 접미사 힌트일치(쿼리에 (PTP)/(병)류 있으면 해당
        형제 SKU 우선) → |bp1−단가| → 잉여 괄호토큰 최소·이름길이(힌트·단가 둘 다
        없을 때 base 변형 우선). 형제 SKU는 clean명이 동일해 sim/dose가 동률이라
        기존 V3은 price가 임의로 깨며 오픽(랭킹분해 F버킷 653행의 주 패턴).
        단가 결측 시 amount/quantity 역산으로 대체.

        NOTE: war 캐스케이드의 LIKE 단계(clean 부분포함 우선)는 062 실측에서 순손해
        (-0.05pp)라 미채택. 이유: 벤치의 +0.9pp 는 dose 없는 순수 trigram 대비였고,
        우리는 이미 규격 dose tiebreak 로 trigram 을 강화해 LIKE 의 이점(규격 구분)을
        흡수함 → LIKE 우선이 오히려 dose 정답을 동명이품으로 덮음. learndata 도 키
        불일치(적중 7.8%)로 후순위. (측정 근거: eval/data/invoice_war/_cascade_increment.sql)"""
        cands = self.top_candidates(name, 30)
        if not cands:
            return None
        if price is None:
            qd = re.sub(r"[^0-9]", "", str(quantity or ""))
            a = parse_price(amount)
            if qd and a:
                qi = int(qd)
                if qi > 0 and a > 0:
                    price = round(a / qi)
        q_dose = dose_tokens(f"{name} {spec or ''}")
        q_pack = pack_tokens(f"{spec or ''} {quantity or ''}")
        q_paren = paren_tokens(name) | paren_tokens(spec or "")
        best_i, best_key = -1, None
        low_i, low_key, low_sim = -1, None, 0.0  # V4d: floor 미달 최선(가격구제 판정용)
        for sim, i in cands:
            ds = dose_score(q_dose, q_pack, self._nms[i], self._units[i])
            dkey = 0.0 if ds is None else (-1.0 if ds == 0 else ds)
            cp = paren_tokens(self._nms[i])
            sfx = _sfx_score(q_paren, cp)
            pd = abs(self._bp1s[i] - price) if price is not None else float("inf")
            key = (-sim, -dkey, -sfx, pd, len(cp) - sfx, len(self._nms[i]))
            if sim < floor:
                if low_key is None or key < low_key:
                    low_key, low_i, low_sim = key, i, sim
                continue
            if best_key is None or key < best_key:
                best_key, best_i = key, i
        # V4d 가격구제(엄격): floor 미달로 전부 탈락했을 때, 미달 구간의 '키 기준 최선'
        # 후보가 송장 단가와 보험단가(bp1) 1% 이내로 일치하면 배정. 부분집합에서 다시
        # 고르는 루즈 변형(+151/오배정 73, 정밀도 67%)은 기각 — 최선 후보 자체의 가격
        # 일치만 인정해야 측정 정밀도가 유지된다(063 실측 +117/오배정 15, 88.6% ≥ 시스템
        # 평균 86.5%). sim>=0.05 는 잔반 후보 배제 가드.
        if (best_i < 0 and low_i >= 0 and low_sim >= 0.05
                and price is not None and price > 0
                and abs(self._bp1s[low_i] - price) <= price * 0.01):
            best_i, best_key = low_i, low_key
        if best_i < 0:
            return None
        return {"itemCode": self._cds[best_i], "itemNameMaster": self._nms[best_i],
                "sim": round(-best_key[0], 4)}


_CORP_SUFFIX = re.compile(r"\s*\((?:주|전|유|재|사|합|자|명|의|학|영)\)\s*$")


def _strip_corp_suffix(nm: str) -> str:
    """회사명 끝 법인격/구분 괄호('(주)','(전)' 등) 제거. war GT(thin)는 접미사 없는
    경향이라 마스터 정식명과 매치되게. (062: '대한약품(주)' vs GT '대한약품')."""
    return _CORP_SUFFIX.sub("", nm or "")


class PartyMatcher:
    """④거래처/지점 매칭 (war ocr.xml 재현): 공급자=사업자번호 정확일치 앵커 →
    거래처 마스터(nm/addr), 공급받는자=지점 마스터(10곳) 이름 trigram.

    war Master의 supplierCompany 84.5%/buyerCompany 100%는 읽기가 아니라 이 매칭.
    사업자번호는 정확 앵커라 오배정 위험이 낮고, 사전에 없는 번호(study 등 war 외
    문서)는 자동 미적용 = 자연 가드."""

    def __init__(self, md: dict):
        self.bizno_to_cust: dict[str, str] = {}
        for b, cd in (md.get("biznoToCust") or {}).items():
            d = re.sub(r"[^0-9]", "", str(b or ""))
            if len(d) == 10 and cd:
                self.bizno_to_cust.setdefault(d, str(cd))
        self.cust: dict = md.get("cust") or {}
        self.brch: list = [
            {"nm": (e or {}).get("nm") or "", "addr": (e or {}).get("addr") or "",
             "tri": trigrams((e or {}).get("nm") or "")}
            for e in (md.get("brch") or {}).values() if (e or {}).get("nm")
        ]

    def supplier(self, bizno):
        d = re.sub(r"[^0-9]", "", str(bizno or ""))
        if len(d) != 10:
            return None
        cd = self.bizno_to_cust.get(d)
        e = self.cust.get(cd) if cd else None
        if not e:
            return None
        # 접미사 정규화(_strip_corp_suffix)는 062 실측 thin -0.3pp(thin GT도 접미사 유무
        # 제각각)라 미적용.
        return {"nm": e.get("nm") or "", "addr": e.get("addr") or ""}

    def buyer(self, read_name, floor: float = 0.45):
        q = trigrams(read_name or "")
        if not q:
            return None
        best, best_sim = None, 0.0
        for b in self.brch:
            t = b["tri"]
            if not t:
                continue
            inter = len(q & t)
            sim = inter / (len(q) + len(t) - inter)
            if sim > best_sim:
                best_sim, best = sim, b
        return {"nm": best["nm"], "addr": best["addr"]} if best and best_sim >= floor else None


def fill_party_match(document_fields, party: "PartyMatcher | None" = None):
    """공급자(사업자번호 앵커)/공급받는자(지점 trigram) 상호·주소를 마스터 값으로 교체.

    교체(overwrite)인 이유: war GT의 상호/주소 = 마스터 정식값이라 raw 읽기는 채점상
    거의 0%(1.8/0.2%). 앵커가 정확(사업자번호 10자리 일치·지점 sim>=0.45)할 때만 발동,
    사전에 없는 문서는 미적용. 반환 (document_fields, debug)."""
    party = party or get_party()
    dbg = {"enabled": party is not None, "supplier": False, "buyer": False}
    if party is None or not isinstance(document_fields, dict):
        return document_fields, dbg
    s = party.supplier(document_fields.get("supplierBizNumber"))
    if s:
        if s["nm"]:
            document_fields["supplierCompany"] = s["nm"]
        if s["addr"]:
            document_fields["supplierAddress"] = s["addr"]
        dbg["supplier"] = True
    # NOTE: 공급받는자(지점) trigram 매칭은 미채택 — 지점 10곳뿐이라 앵커(사업자번호)가
    # 없는 trigram 이 임의 문서를 특정 지점으로 오교체(062 study: 모든 문서 buyerCompany
    # 가 '백제약품 영등포지점'으로 뒤바뀌어 필드 90.9→54.5% 회귀). 정확 앵커가 생기기
    # 전까지 buyer 는 손대지 않음.
    return document_fields, dbg


_matcher: "MasterMatcher | None" = None
_party: "PartyMatcher | None" = None
_load_tried = False
_lock = threading.Lock()


def get_party() -> "PartyMatcher | None":
    get_matcher()  # 같은 파일에서 함께 로드됨
    return _party


def get_matcher() -> "MasterMatcher | None":
    global _matcher, _party, _load_tried
    if _matcher is not None or _load_tried:
        return _matcher
    with _lock:
        if _matcher is not None or _load_tried:
            return _matcher
        for p in _DICT_CANDIDATES:
            p = os.path.normpath(p)
            if os.path.isfile(p):
                try:
                    d = json.load(open(p, encoding="utf-8"))
                    _matcher = MasterMatcher(d.get("item") or {}, d.get("itembuycust"))
                    _party = PartyMatcher(d)
                    print(f"[master_match] loaded {p} ({len(_matcher._cds)} items, "
                          f"{len(_party.bizno_to_cust)} bizno, {len(_party.brch)} brch)")
                    break
                except Exception as e:
                    print(f"[master_match] load failed {p}: {e}")
        _load_tried = True
        return _matcher


_RAW_MASTER_HANGUL_RE = re.compile(r"[가-힣]{2,}")
_RAW_MASTER_SUMMARY_RE = re.compile(
    r"합계|소계|총계|이하여백|공급가|부가세|세액|거래선|사업자|페이지"
)
_RAW_MASTER_COMPANY_RE = re.compile(
    r"제약|약품|파마|메디|바이오|헬스|상사|유통|주식회사"
)


def _raw_master_norm(value: object) -> str:
    return re.sub(r"[^0-9a-z가-힣]", "", str(value or "").lower())


def _raw_master_token_pos(text: str, value: object) -> int | None:
    raw = str(value or "").strip()
    if len(raw) < 2:
        return None
    match = re.search(rf"(?<!\d){re.escape(raw)}(?!\d)", text)
    return match.start() if match else None


def _raw_master_candidate_variants(row: dict[str, Any]) -> list[str]:
    raw = str(row.get("_rawText") or row.get("rawText") or "").strip()
    if not raw:
        return []

    positions: list[int] = []
    spec = str(row.get("spec") or "").strip()
    if spec:
        pos = raw.find(spec)
        if pos >= 2:
            positions.append(pos)
    for key in ("quantity", "unitPrice", "amount"):
        pos = _raw_master_token_pos(raw, row.get(key))
        if pos is not None and pos >= 2:
            positions.append(pos)

    prefix = raw[:min(positions)].strip() if positions else raw
    prefix = re.sub(r"^\s*\d{1,3}\s+", "", prefix)
    variants = [
        prefix,
        re.sub(r"^\s*\d{5,}[-./]?\d*\s*", "", prefix),
    ]
    parts = prefix.split()
    for index in range(1, min(len(parts), 4)):
        skipped = parts[:index]
        if all(
            _RAW_MASTER_COMPANY_RE.search(token)
            or not _RAW_MASTER_HANGUL_RE.search(token)
            for token in skipped
        ):
            variants.append(" ".join(parts[index:]))
    if parts and _RAW_MASTER_COMPANY_RE.search(parts[0]):
        variants.append(" ".join(parts[1:]))

    unique: list[str] = []
    seen: set[str] = set()
    for value in variants:
        value = value.strip(" -_/.,")
        key = _raw_master_norm(value)
        if (
            key in seen
            or not _RAW_MASTER_HANGUL_RE.search(value)
            or _RAW_MASTER_SUMMARY_RE.search(value)
        ):
            continue
        seen.add(key)
        unique.append(value)
    return unique


def _fill_blank_master_from_rawtext(
    rows: list, matcher: "MasterMatcher", dbg: dict[str, Any]
) -> None:
    """Fill only fallback master names from high-confidence same-row raw text.

    Raw itemName and numeric cells remain untouched so thin content alignment is
    structurally unchanged. The master name must be explicitly present in the
    OCR candidate; matcher-added qualifiers are rejected.
    """
    used_codes = {
        str(row.get("itemCode") or "").strip()
        for row in rows
        if isinstance(row, dict)
        and str(row.get("itemCode") or "").strip()
        and (
            str(row.get("itemName") or "").strip()
            or str(row.get("itemNameMaster") or "").strip()
        )
    }
    samples: list[dict[str, Any]] = []
    recovered = 0
    for row in rows:
        if (
            not isinstance(row, dict)
            or str(row.get("_source") or "") != "invoice_statement_table_parser"
            or str(row.get("itemName") or "").strip()
            or str(row.get("itemNameMaster") or "").strip()
        ):
            continue
        evidence_count = sum(
            bool(str(row.get(key) or "").strip())
            for key in (
                "spec", "quantity", "unitPrice", "amount", "itemCode", "insuranceCode"
            )
        )
        if evidence_count < 3:
            continue

        matches: list[tuple[float, str, dict[str, Any]]] = []
        for value in _raw_master_candidate_variants(row):
            match = matcher.match(
                clean_query_name(value),
                parse_price(row.get("unitPrice")),
                spec=str(row.get("spec") or ""),
                quantity=row.get("quantity"),
                amount=row.get("amount"),
                floor=0.45,
            )
            if match:
                matches.append((float(match.get("sim") or 0), value, match))
        if not matches:
            continue
        matches.sort(
            key=lambda item: (item[0], -len(_raw_master_norm(item[1]))),
            reverse=True,
        )
        best_sim, value, match = matches[0]
        best_code = str(match.get("itemCode") or "")
        other_scores = [
            score
            for score, _value, other in matches
            if str(other.get("itemCode") or "") != best_code
        ]
        if best_sim < 0.80 or (other_scores and best_sim - max(other_scores) < 0.10):
            continue
        if not best_code or best_code in used_codes:
            continue

        # Reserve before the qualifier gate so rejecting one row cannot make a
        # later duplicate newly eligible; this keeps the release set monotonic.
        used_codes.add(best_code)
        master_name = str(match.get("itemNameMaster") or "").strip()
        if not master_name or _raw_master_norm(master_name) not in _raw_master_norm(value):
            continue
        row["itemNameMaster"] = master_name
        recovered += 1
        if len(samples) < 8:
            samples.append({"candidate": value[:80], "master": master_name, "sim": best_sim})

    if recovered:
        dbg["rawTextMasterRecovered"] = recovered
        dbg["rawTextMasterSamples"] = samples


_TRAILING_ITEM_CLASS_RE = re.compile(
    r"^(?P<base>\S(?:.*\S)?)\s+(?P<classification>전문|일반)\s*$"
)


def strip_trailing_item_classification(rows: list) -> tuple[list, dict[str, Any]]:
    """Remove a standalone trailing prescription/OTC marker from item names.

    Only a whitespace-delimited final token is removed.  Standalone markers
    and parenthesized text such as ``Mago 250mg(일반)`` are intentionally left
    unchanged.  No other cell or row structure is touched.
    """
    dbg: dict[str, Any] = {"stripped": 0, "samples": []}
    if not isinstance(rows, list):
        return rows, dbg
    for row in rows:
        if not isinstance(row, dict):
            continue
        name = str(row.get("itemName") or "").strip()
        match = _TRAILING_ITEM_CLASS_RE.fullmatch(name)
        if not match:
            continue
        base = match.group("base").strip()
        if len(_compact_alnum(base)) < 3:
            continue
        row["itemName"] = base
        dbg["stripped"] += 1
        if len(dbg["samples"]) < 8:
            dbg["samples"].append({"before": name[:100], "after": base[:100]})
    return rows, dbg


def fill_master_match(rows: list, matcher: "MasterMatcher | None" = None,
                      supplier_bizno: str | None = None):
    """itemName 있는 행의 itemNameMaster/itemCode 빈칸을 매칭 결과로 채움.

    빈칸만(파서가 읽은 값 절대 보존) + floor 미달은 미배정 → spurious 통제.
    supplier_bizno 주면: 전역매칭 미달로 빈칸 남은 행을 itembuycust(그 거래처 구매
    이력)에서 낮은 floor로 rescue(작은 셋이라 안전). 065 실측 +63 master/spurious0.
    반환 (rows, debug) — 시블링 룰(fill_pharma_columns 등)과 동일 계약.
    """
    matcher = matcher or get_matcher()
    dbg: dict[str, Any] = {
        "enabled": matcher is not None,
        "filled": 0,
        "belowFloor": 0,
        "ibcFilled": 0,
        "ibcStrictReranked": 0,
    }
    if matcher is None or not rows:
        return rows, dbg
    bz = re.sub(r"\D", "", str(supplier_bizno or ""))
    for r in rows:
        if not isinstance(r, dict):
            continue
        name = str(r.get("itemName") or "").strip()
        if not name:
            continue
        if str(r.get("itemNameMaster") or "").strip() and str(r.get("itemCode") or "").strip():
            continue
        m = matcher.match(clean_query_name(name), parse_price(r.get("unitPrice")),
                          spec=str(r.get("spec") or ""), quantity=r.get("quantity"),
                          amount=r.get("amount"))
        if m is None:
            # itembuycust rescue: 거래처 구매이력 셋에서 낮은 floor로 재시도(빈칸만)
            if len(bz) == 10:
                m = matcher.itembuycust_rescue(name, bz)
            if m is None:
                dbg["belowFloor"] += 1
                continue
            dbg["ibcFilled"] += 1
        if len(bz) == 10:
            reranked = matcher.itembuycust_strict_rerank(name, bz, m)
            if reranked is not None:
                m = reranked
                dbg["ibcStrictReranked"] += 1
        if not str(r.get("itemNameMaster") or "").strip():
            r["itemNameMaster"] = m["itemNameMaster"]
        if not str(r.get("itemCode") or "").strip():
            r["itemCode"] = m["itemCode"]
        dbg["filled"] += 1
    _fill_blank_master_from_rawtext(rows, matcher, dbg)
    return rows, dbg
