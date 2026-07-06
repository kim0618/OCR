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
from typing import Any

# G3 스윕 실측(0~0.5): floor↑ = 배정중 정확도↑/coverage↓/spurious↓.
# 0.20 = coverage 85.9 / match_acc 82.8 / spurious 39.1 균형점(잠정 — G3 확정 대상).
MATCH_SIM_FLOOR = 0.20

_DICT_CANDIDATES = (
    # AWS 배포 위치(ocr-server/ 루트) 우선, 로컬 개발은 eval 데이터 폴더
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "master_dict.json"),
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "eval", "data",
                 "invoice_war", "master_dict.json"),
)

_WORD = re.compile(r"[^\W_]+", re.UNICODE)
_PAREN = re.compile(r"\(.*\)")          # greedy: 첫 '(' ~ 마지막 ')' (war 함수와 동일)
_NUM = re.compile(r"\d[\d,]*(?:\.\d+)?")

# 랭킹 tiebreak용 규격 토큰 (V3, match_rank_bench 실측 code +2.5pp @floor0.2)
_DOSE = re.compile(
    r"(\d+(?:\.\d+)?(?:/\d+(?:\.\d+)?)*)\s*"
    r"(mg|mcg|㎍|㎎|g|㎖|ml|l|iu|%|단위|밀리그람|미리그람|밀리리터|그람)", re.I)
_UNIT_ALIAS = {"㎍": "mcg", "㎎": "mg", "㎖": "ml", "밀리그람": "mg", "미리그람": "mg",
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


def trigrams(s: str) -> frozenset:
    """pg_trgm 등가 trigram 집합."""
    out = set()
    for w in _WORD.findall((s or "").lower()):
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


class MasterMatcher:
    def __init__(self, item_dict: dict):
        # entries: (item_cd, item_nm, bp1, unit, pyojun, bohum, trigram 크기) / 역색인: trigram -> [idx]
        self._cds: list[str] = []
        self._nms: list[str] = []
        self._bp1s: list[int] = []
        self._units: list[str] = []
        self._pyojuns: list[str] = []
        self._bohums: list[str] = []
        self._tlens: list[int] = []
        self._index: dict[str, list[int]] = {}
        for cd, e in item_dict.items():
            e = e or {}
            nm = e.get("nm") or ""
            if not nm:
                continue
            tri = trigrams(clean_item_name(nm))
            if not tri:
                continue
            i = len(self._cds)
            self._cds.append(cd)
            self._nms.append(nm)
            self._bp1s.append(int(e.get("bp1") or 0))
            self._units.append(e.get("unit") or "")
            self._pyojuns.append(e.get("pyojun") or "")
            self._bohums.append(e.get("bohum") or "")
            self._tlens.append(len(tri))
            for t in tri:
                self._index.setdefault(t, []).append(i)

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

        랭킹(V3, 벤치 실측): 유사도 DESC → 규격 dose점수(일치>정보없음>모순) → |bp1−단가|.
        단가 결측 시 amount/quantity 역산으로 대체."""
        cands = self.top_candidates(name, 30)
        if not cands:
            return None
        if price is None:
            q = re.sub(r"[^0-9]", "", str(quantity or ""))
            a = parse_price(amount)
            if q and a:
                qi = int(q)
                if qi > 0 and a > 0:
                    price = round(a / qi)
        q_dose = dose_tokens(f"{name} {spec or ''}")
        q_pack = pack_tokens(f"{spec or ''} {quantity or ''}")
        best_i, best_key = -1, None
        for sim, i in cands:
            if sim < floor:
                break  # sim DESC 정렬이라 이후 전부 미달
            ds = dose_score(q_dose, q_pack, self._nms[i], self._units[i])
            dkey = 0.0 if ds is None else (-1.0 if ds == 0 else ds)
            pd = abs(self._bp1s[i] - price) if price is not None else float("inf")
            key = (-sim, -dkey, pd)
            if best_key is None or key < best_key:
                best_key, best_i = key, i
        if best_i < 0:
            return None
        return {"itemCode": self._cds[best_i], "itemNameMaster": self._nms[best_i],
                "sim": round(-best_key[0], 4)}


_matcher: "MasterMatcher | None" = None
_load_tried = False
_lock = threading.Lock()


def get_matcher() -> "MasterMatcher | None":
    global _matcher, _load_tried
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
                    _matcher = MasterMatcher(d.get("item") or {})
                    print(f"[master_match] loaded {p} ({len(_matcher._cds)} items)")
                    break
                except Exception as e:
                    print(f"[master_match] load failed {p}: {e}")
        _load_tried = True
        return _matcher


def fill_master_match(rows: list, matcher: "MasterMatcher | None" = None):
    """itemName 있는 행의 itemNameMaster/itemCode 빈칸을 매칭 결과로 채움.

    빈칸만(파서가 읽은 값 절대 보존) + floor 미달은 미배정 → spurious 통제.
    반환 (rows, debug) — 시블링 룰(fill_pharma_columns 등)과 동일 계약.
    """
    matcher = matcher or get_matcher()
    dbg: dict[str, Any] = {"enabled": matcher is not None, "filled": 0, "belowFloor": 0}
    if matcher is None or not rows:
        return rows, dbg
    for r in rows:
        if not isinstance(r, dict):
            continue
        name = str(r.get("itemName") or "").strip()
        if not name:
            continue
        if str(r.get("itemNameMaster") or "").strip() and str(r.get("itemCode") or "").strip():
            continue
        m = matcher.match(name, parse_price(r.get("unitPrice")),
                          spec=str(r.get("spec") or ""), quantity=r.get("quantity"),
                          amount=r.get("amount"))
        if m is None:
            dbg["belowFloor"] += 1
            continue
        if not str(r.get("itemNameMaster") or "").strip():
            r["itemNameMaster"] = m["itemNameMaster"]
        if not str(r.get("itemCode") or "").strip():
            r["itemCode"] = m["itemCode"]
        dbg["filled"] += 1
    return rows, dbg
