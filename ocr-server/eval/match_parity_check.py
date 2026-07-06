"""G4 parity: 파이썬 매처(extractors/master_match.py) top1 == psql 벤치 top1 확인.

입력 = _me_pick.csv (_match_engine.sql이 덤프한 per-row psql top1: cd1/sim1).
파이썬 매처를 같은 (our_name, our_price)에 floor=0으로 돌려 비교한다.

판정:
  sim 일치(4dp)  = trigram/clean 이식이 pg_trgm과 동등하다는 증거 (핵심)
  cd 일치        = 최종 top1 동일. sim 동점(애매밴드 62%)에서 동순위 후보 간
                   타이브레이크 순서는 psql도 임의라, sim 일치하며 cd만 다른 건
                   '동점 내 스왑'으로 따로 센다(결함 아님).
"""
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..")))

from extractors.master_match import get_matcher  # noqa: E402

PICK = os.path.join(HERE, "data", "invoice_war", "_me_pick.csv")


def main() -> int:
    matcher = get_matcher()
    if matcher is None:
        print("master_dict.json not found — cannot run"); return 2
    n = n_sim = n_cd = n_swap = n_both_none = 0
    diffs = []
    with open(PICK, encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            n += 1
            price = int(row["our_price"]) if row["our_price"] else None
            m = matcher.match(row["our_name"], price, floor=0.0)
            sql_sim = float(row["sim1"]) if row["sim1"] else None
            sql_cd = row["cd1"] or None
            py_sim = m["sim"] if m else None
            py_cd = m["itemCode"] if m else None
            if py_sim is None and sql_sim is None:
                n_both_none += 1; n_sim += 1; n_cd += 1
                continue
            sim_ok = (py_sim is not None and sql_sim is not None
                      and abs(py_sim - sql_sim) < 5e-4)
            cd_ok = py_cd == sql_cd
            n_sim += 1 if sim_ok else 0
            n_cd += 1 if cd_ok else 0
            if sim_ok and not cd_ok:
                n_swap += 1
            if not sim_ok and len(diffs) < 10:
                diffs.append((row["our_name"], row["our_price"], sql_sim, sql_cd, py_sim, py_cd))
    sys.stdout.reconfigure(errors="replace")
    print(f"rows={n}")
    print(f"  sim 일치(4dp): {n_sim} ({100*n_sim/n:.2f}%)  <- pg_trgm 등가성")
    print(f"  cd  일치:      {n_cd} ({100*n_cd/n:.2f}%)")
    print(f"  sim 일치·cd만 다름(동점 스왑): {n_swap} ({100*n_swap/n:.2f}%)")
    print(f"  둘 다 무배정: {n_both_none}")
    if diffs:
        print("\nsim 불일치 샘플:")
        for d in diffs:
            print("  ", d)
    return 0 if n_sim == n else 1


if __name__ == "__main__":
    raise SystemExit(main())
