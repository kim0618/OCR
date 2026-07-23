"""learndata_apply — learndata json(learndata_build 출력)을 {읽기→코드} 룩업으로 → replay 행에 적용.

측정1/측정2 용: replay_compare 가 itemCode 옆에 learndata 적용 결과를 나란히 채점하도록,
ext행·GT행에 새 키(itemCodeLearnA/B)를 주입한다. compare_table 이 GT행 키를 동적 채점하므로
(compare_table.py:30) 키만 넣으면 자동으로 컬럼이 생긴다.

캐스케이드(war ocr.xml selectMasterItemLearnData 재현):
  게이트 = learn_count(그 ocr_item_nm 총 학습수) >= 3.
  다중코드 = ★spec-unit 필터 → count majority → trigram sim → |bp1-단가| tiebreak.
    다중코드 읽기(gated의 ~54%)의 78%가 포장단위(unit) 상이(같은 품명·다른 pack=다른 코드).
    → 행 spec 을 master unit 과 대조해 후보를 먼저 거르면 majority-only 대비 +935셀(067 실측,
       itemCode 60.42→61.52%). war 는 master_dict/단가 없이 majority 근사였으나, replay 는
       행 spec·단가와 master_dict 가 있어 war 의 SIMILARITY+가격 tiebreak 를 더 충실히 재현.
  적용 = 읽기가 룩업에 있으면 resolve 한 cd, 없으면 기존 itemCode(=②master) fallback.
  master_index 없으면 majority-only 로 자동 폴백(사전 파일 없을 때 기존 동작 보존).
"""
from __future__ import annotations
import json
import re
import unicodedata
from collections import defaultdict, Counter

_SPEC_RE = re.compile(r"[^0-9a-z가-힣]")


def _normspec(s) -> str:
    return _SPEC_RE.sub("", unicodedata.normalize("NFC", str(s or "")).lower())


def _trigrams(s: str) -> set:
    """음절 단위 trigram(다중코드 count 동률 tiebreak용, 067 spec-unit 측정과 동일)."""
    s = re.sub(r"[^0-9a-zA-Z가-힣]+", " ", str(s or "").lower()).strip()
    out: set = set()
    for w in s.split():
        w = "  " + w + " "
        out |= {w[i:i + 3] for i in range(len(w) - 2)}
    return out


def _sim(a: str, b: str) -> float:
    ta, tb = _trigrams(a), _trigrams(b)
    if not ta or not tb:
        return 0.0
    i = len(ta & tb)
    return i / (len(ta) + len(tb) - i)


def _row_price(row: dict):
    """행 단가 → int. unitPrice 우선, 없으면 amount/quantity 역산. 결측=None."""
    up = re.sub(r"[^\d]", "", str(row.get("unitPrice") or ""))
    if up:
        return int(up)
    q = re.sub(r"[^\d]", "", str(row.get("quantity") or ""))
    a = re.sub(r"[^\d]", "", str(row.get("amount") or ""))
    if q and a and int(q) > 0:
        return round(int(a) / int(q))
    return None


def load_dist(path: str, min_count: int = 3) -> dict[str, Counter]:
    """learndata json → {ocr_item_nm: Counter(code→count)}. learn_count>=min_count 인 읽기만."""
    data = json.load(open(path, encoding="utf-8"))
    by_reading: dict[str, Counter] = defaultdict(Counter)
    for r in data.get("rows") or []:
        rd = (r.get("ocr_item_nm") or "").strip()
        cd = (r.get("user_item_cd") or "").strip()
        if rd and cd:
            by_reading[rd][cd] += 1
    return {rd: c for rd, c in by_reading.items() if sum(c.values()) >= min_count}


def load_lookup(path: str, min_count: int = 3) -> dict[str, str]:
    """{ocr_item_nm: dominant_cd} (majority). 하위호환 — spec-unit 미사용 경로용."""
    return {rd: c.most_common(1)[0][0] for rd, c in load_dist(path, min_count).items()}


def load_master_index(path: str) -> dict[str, dict]:
    """master_dict.json → {code: {'unit': normspec, 'bp1': int, 'nm': str}}. 다중코드 해소용."""
    md = (json.load(open(path, encoding="utf-8")).get("item")) or {}
    idx: dict[str, dict] = {}
    for cd, e in md.items():
        e = e or {}
        idx[cd] = {"unit": _normspec(e.get("unit")),
                   "bp1": int(e.get("bp1") or 0),
                   "nm": e.get("nm") or ""}
    return idx


def resolve_code(counter: Counter, reading: str, spec, price,
                 master_index: dict[str, dict] | None) -> str:
    """다중코드 해소: spec-unit 필터 → count → trigram sim → |bp1-단가|.
    단일코드/사전없음 = majority. spec 필터가 후보 전멸이면 전체 majority 로 폴백."""
    items = list(counter.items())
    if len(items) == 1 or master_index is None:
        return counter.most_common(1)[0][0]
    cands = items
    ns = _normspec(spec)
    if ns:
        filt = [(cd, n) for cd, n in items if master_index.get(cd, {}).get("unit") == ns]
        if filt:
            cands = filt
    best, best_key = None, None
    for cd, n in cands:
        m = master_index.get(cd, {})
        bp1 = m.get("bp1", 0)
        pd = abs(bp1 - price) if (price is not None and bp1) else float("inf")
        key = (-n, -_sim(reading, m.get("nm", "")), pd)
        if best_key is None or key < best_key:
            best_key, best = key, cd
    return best if best is not None else counter.most_common(1)[0][0]


def apply_to_rows(ext_rows: list[dict] | None, gt_rows: list[dict] | None,
                  dist: dict[str, Counter], out_key: str,
                  master_index: dict[str, dict] | None = None,
                  name_out_key: str | None = None) -> None:
    """양쪽에 out_key(코드) 주입 → compare_table 이 동적 채점.
      ext: 읽기(itemName raw) → learndata resolve cd, 없으면 기존 itemCode(②master) fallback.
      gt : out_key = itemCode(정답). itemCode 없는 행은 채점대상 아님(주입 안 함).
      ★name_out_key 주면 이름도 같이 채점: learndata 가 찾은 아이템의 정식명
      (master_index[cd].nm)을 ext 에, GT 정식명(itemNameMaster)을 gt 에 주입.
      learndata 는 [읽기]→[아이템] 이라 코드·이름이 같은 아이템에서 함께 나온다."""
    for r in ext_rows or []:
        reading = (r.get("itemName") or "").strip()
        counter = dist.get(reading)
        if counter:
            code = resolve_code(counter, reading, r.get("spec"),
                                _row_price(r), master_index)
        else:
            code = r.get("itemCode") or ""       # learndata 미적중 → ②master 코드
        r[out_key] = code
        if name_out_key:
            nm = (master_index or {}).get(code, {}).get("nm") if code else None
            r[name_out_key] = nm or r.get("itemNameMaster") or ""   # 미적중 시 ②master 정식명
    for g in gt_rows or []:
        code = (g.get("itemCode") or "").strip()
        if code:
            g[out_key] = code
        if name_out_key:
            nm = (g.get("itemNameMaster") or "").strip()
            if nm:
                g[name_out_key] = nm
