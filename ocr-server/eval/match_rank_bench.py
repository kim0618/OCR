"""랭킹(tiebreak) 벤치 — ②매칭 애매밴드(동점 62%) 개선 실험.

_match_engine.csv(matched 행)에 대해 top-30 후보를 뽑고 tiebreak 변형별로 top1을
다시 골라 채점한다. 유사도 자체(coverage)는 건드리지 않음 — 동점/근접 순위만 바꿈.

변형 (누적):
  V0 baseline : sim DESC → |bp1−단가| ASC            (현행 = psql 벤치와 동일)
  V1 +규격    : sim DESC → dose점수 DESC → 가격 ASC   (용량토큰: our_name+spec vs nm+unit)
  V2 +가격역산 : V0에서 단가 결측이면 amount/qty로 대체
  V3 = V1+V2

채점(psql 벤치와 동일): code_ok = (item_cd|pyojun|bohum)=gt_code, name_ok = _nm(nm)=_nm(gt_master)
usage: ../.venv/Scripts/python.exe eval/match_rank_bench.py
"""
import csv
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..")))

from extractors.master_match import (  # noqa: E402
    get_matcher, dose_tokens, pack_tokens, dose_score,
)

CSV = os.path.join(HERE, "data", "invoice_war", "_match_engine.csv")
FLOORS = (0.0, 0.2)
K = 30

_NM_STRIP = re.compile(r"[\s()]+")


def _nm(s):
    return _NM_STRIP.sub("", str(s or "")).lower()


def main() -> int:
    m = get_matcher()
    if m is None:
        print("no master_dict"); return 2
    rows = [r for r in csv.DictReader(open(CSV, encoding="utf-8", newline=""))
            if r["row_kind"] == "matched"]
    print(f"matched rows: {len(rows)}")

    # 사전계산: 후보 + 쿼리 토큰
    prep = []
    for r in rows:
        cands = m.top_candidates(r["our_name"], K)
        price = int(r["our_price"]) if r["our_price"] else None
        qty = re.sub(r"[^0-9]", "", r.get("our_qty") or "")
        amt = r.get("our_amount") or ""
        backfill = None
        if price is None and qty and amt:
            try:
                q, a = int(qty), int(amt)
                if q > 0 and a > 0:
                    backfill = round(a / q)
            except ValueError:
                pass
        prep.append({
            "cands": cands, "price": price, "backfill": backfill,
            "q_dose": dose_tokens(r["our_name"] + " " + (r.get("our_spec") or "")),
            "q_pack": pack_tokens((r.get("our_spec") or "") + " " + (r.get("our_qty") or "")),
            "gt_code": r["gt_code"], "gt_master_nm": _nm(r["gt_master"]),
        })

    def pick(p, use_dose, use_backfill):
        cands = p["cands"]
        if not cands:
            return None
        price = p["price"] if p["price"] is not None else (p["backfill"] if use_backfill else None)
        best, key_best = None, None
        for sim, i in cands:
            e = m.entry(i)
            ds = dose_score(p["q_dose"], p["q_pack"], e["itemNameMaster"], e["unit"]) if use_dose else None
            pd = abs(e["bp1"] - price) if price is not None else None
            # dose 순서: 일치(>0) > 정보없음(중립 0) > 모순(0 → -1로 강등)
            dkey = 0.0 if ds is None else (-1.0 if ds == 0 else ds)
            key = (-sim, -dkey, pd if pd is not None else float("inf"))
            if key_best is None or key < key_best:
                key_best, best = key, (sim, e)
        return best

    def score(use_dose, use_backfill, label):
        out = []
        for f in FLOORS:
            asg = code = name = either = 0
            for p in prep:
                got = pick(p, use_dose, use_backfill)
                if not got:
                    continue
                sim, e = got
                if sim < f:
                    continue
                asg += 1
                c = p["gt_code"] and p["gt_code"] in (e["itemCode"], e["pyojun"], e["bohum"])
                nn = p["gt_master_nm"] and _nm(e["itemNameMaster"]) == p["gt_master_nm"]
                code += 1 if c else 0
                name += 1 if nn else 0
                either += 1 if (c or nn) else 0
            n = len(prep)
            out.append(f"  floor {f:.1f}: asg {asg} ({100*asg/n:.1f}%)  "
                       f"code {100*code/asg:.1f}%  name {100*name/asg:.1f}%  "
                       f"either {100*either/asg:.1f}%  overall {100*either/n:.1f}%")
        print(label)
        print("\n".join(out))

    sys.stdout.reconfigure(errors="replace")
    score(False, False, "V0 baseline (sim -> price)")
    score(True, False, "V1 +규격(dose/pack) tiebreak")
    score(False, True, "V2 +가격 결측 역산(amount/qty)")
    score(True, True, "V3 = V1+V2")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
