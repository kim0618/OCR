"""llm_sample_500 — 072 전처리 텔레메트리로 문서군을 가르고 500장 층화표본을 뽑는다.

전처리 축의 질문은 "우리가 방향을 잘못 잡아 깨뜨린 문서를 VLM 이 그냥 읽나" 하나다.
그 답이 걸린 오회전 위험군은 무작위 500 에 4~5장밖에 안 들어와 비교가 성립하지 않으므로
강제로 쿼터를 준다(--risk-quota). 나머지 세 군은 실발생률대로 비례 배분하고,
전체 발생률이 필요한 자리(파서 탭)는 9,001 본판정이 담당한다.

문서군은 상호배타 — 위험군 > 회전적용 > 기울기보정 > 정상 순으로 먼저 잡히는 곳에 넣는다.
위험군은 orientMargin(상위 2개 orientation 점수 차) 이 임계 미만인 문서.
낮다 = 90/180/270 선택이 동전던지기였다 = 페이지 통째로 잘못 돌아갔을 위험.
정의는 parser_drop_classify._pp_features 와 같은 식을 쓴다.

CLI:
    python eval/llm_sample_500.py --run eval/runs/072_20260802_182127
    python eval/llm_sample_500.py --run ... --risk-quota 150 --n 500 --seed 20260904
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import random
import sys

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))

EXCLUDE = {"itemCode", "itemNameMaster", "itemNameLearnA", "itemNameLearnB",
           "itemCodeLearnA", "itemCodeLearnB"}
SCORED = {"match", "mismatch", "ext_missing"}

RISK, ROT, SKEW, NORMAL = "오회전위험군", "회전적용", "기울기보정", "정상"
GROUP_ORDER = [NORMAL, ROT, SKEW, RISK]   # 계획 문서의 표 순서(위험군 마지막)


def pp_features(pp: dict | None) -> dict:
    """parser_drop_classify._pp_features 와 같은 신호. margin = 상위 2개 점수 차."""
    o = (pp or {}).get("orientation") or {}
    d = (pp or {}).get("deskew") or {}
    margin = None
    try:
        vals = sorted((float(v) for v in (o.get("allScores") or {}).values()), reverse=True)
        if len(vals) >= 2:
            margin = round(vals[0] - vals[1], 1)
    except (TypeError, ValueError):
        margin = None
    applied = o.get("finalAppliedAfterPolicy")
    if applied is None:
        applied = o.get("applied")
    return {
        "orientApplied": bool(applied),
        "orientAngle": o.get("angle"),
        "orientMargin": margin,
        "deskewApplied": bool(d.get("applied")),
        "deskewAbs": d.get("absAngle") if isinstance(d.get("absAngle"), (int, float)) else None,
    }


def group_of(f: dict, risk_margin: float) -> str:
    m = f["orientMargin"]
    if m is not None and m < risk_margin:
        return RISK
    if f["orientApplied"] and f["orientAngle"] not in (0, None):
        return ROT
    if f["deskewApplied"]:
        return SKEW
    return NORMAL


def base_acc(compare_path: str) -> tuple[int, int]:
    """(맞은 칸, 채점된 칸) — 기준선 46.7% 와 같은 저울(④ 제외)."""
    with open(compare_path, encoding="utf-8") as fh:
        doc = json.load(fh)
    match = scored = 0
    for row in ((doc.get("table") or {}).get("rows") or []):
        for key, verdict in (row.get("cells") or {}).items():
            if key in EXCLUDE:
                continue
            status = verdict.get("status")
            if status not in SCORED:
                continue
            scored += 1
            match += status == "match"
    return match, scored


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default=os.path.join(HERE, "runs", "072_20260802_182127"),
                    help="072 run 폴더(samples/ · compare/ 를 읽는다)")
    ap.add_argument("--risk-margin", type=float, default=20.0)
    ap.add_argument("--collapse", type=float, default=0.10, help="문서 붕괴 임계(cell 정확도)")
    ap.add_argument("--n", type=int, default=500)
    ap.add_argument("--risk-quota", type=int, default=150,
                    help="500 중 오회전 위험군에 강제 배정할 장수(무작위면 4~5장뿐)")
    ap.add_argument("--seed", type=int, default=20260904)
    ap.add_argument("--outdir", default=os.path.join(HERE, "LLM"))
    args = ap.parse_args()

    samples_dir = os.path.join(args.run, "samples")
    compare_dir = os.path.join(args.run, "compare")
    files = sorted(glob.glob(os.path.join(samples_dir, "*.json")))
    if not files:
        print("samples 가 없다: " + samples_dir, file=sys.stderr)
        return 1

    docs: dict[str, dict] = {}
    for path in files:
        with open(path, encoding="utf-8") as fh:
            s = json.load(fh)
        src = s.get("sourceFile") or os.path.basename(path)[:-5]
        f = pp_features(s.get("preprocess"))
        f["group"] = group_of(f, args.risk_margin)
        f["status"] = s.get("status")
        f["imagePath"] = s.get("imagePath")
        docs[src] = f

    # Base 점수 — 문서군별 cell 정확도 · 붕괴율. compare/ 가 없으면 건너뛴다.
    n_cmp = 0
    for path in glob.glob(os.path.join(compare_dir, "*.json")):
        src = os.path.basename(path)[:-5]
        if src not in docs:
            continue
        m, sc = base_acc(path)
        docs[src].update(cMatch=m, cScored=sc,
                         cellAcc=(m / sc) if sc else None,
                         collapsed=(sc > 0 and (m / sc) < args.collapse))
        n_cmp += 1

    by_group: dict[str, list[str]] = {g: [] for g in GROUP_ORDER}
    for src, f in docs.items():
        by_group[f["group"]].append(src)
    for g in by_group:
        by_group[g].sort()

    total = len(docs)
    print("문서 {:,}  (compare 결합 {:,})   위험군 임계 margin<{:g}   붕괴 임계 {:.0%}".format(
        total, n_cmp, args.risk_margin, args.collapse))
    print()
    print("{:<12}{:>8}{:>8}{:>11}{:>9}{:>8}{:>12}".format(
        "문서군", "문서수", "비율", "Base cell", "붕괴문서", "붕괴율", "avg margin"))
    print("-" * 68)
    grand_m = grand_s = 0
    for g in GROUP_ORDER:
        srcs = by_group[g]
        m = sum(docs[s].get("cMatch", 0) for s in srcs)
        sc = sum(docs[s].get("cScored", 0) for s in srcs)
        col = sum(1 for s in srcs if docs[s].get("collapsed"))
        scored_docs = sum(1 for s in srcs if docs[s].get("cScored"))
        margins = [docs[s]["orientMargin"] for s in srcs if docs[s]["orientMargin"] is not None]
        grand_m += m
        grand_s += sc
        print("{:<12}{:>8,}{:>8.1%}{:>11.1%}{:>9,}{:>8.1%}{:>12.1f}".format(
            g, len(srcs), len(srcs) / total, (m / sc if sc else 0), col,
            (col / scored_docs if scored_docs else 0),
            (sum(margins) / len(margins) if margins else 0)))
    print("-" * 68)
    print("{:<12}{:>8,}{:>8.1%}{:>11.1%}   (기준선 46.7% / 280,901 / 602,111 대조: {:,} / {:,})".format(
        "전체", total, 1, (grand_m / grand_s if grand_s else 0), grand_m, grand_s))

    # ── 표본 ──────────────────────────────────────────────────────────────
    rng = random.Random(args.seed)
    quota = {RISK: min(args.risk_quota, len(by_group[RISK]))}
    rest_pop = sum(len(by_group[g]) for g in GROUP_ORDER if g != RISK)
    rest_n = args.n - quota[RISK]
    alloc = []
    for g in GROUP_ORDER:
        if g == RISK:
            continue
        exact = rest_n * len(by_group[g]) / rest_pop if rest_pop else 0
        quota[g] = min(int(exact), len(by_group[g]))
        alloc.append((exact - quota[g], g))
    for _, g in sorted(alloc, reverse=True):          # 잔여분은 소수부 큰 군부터
        if sum(quota.values()) >= args.n:
            break
        if quota[g] < len(by_group[g]):
            quota[g] += 1

    picked: list[str] = []
    for g in GROUP_ORDER:
        picked += rng.sample(by_group[g], quota[g])
    picked.sort()

    print()
    print("표본 {}장  (seed {}, 위험군 쿼터 {})".format(len(picked), args.seed, args.risk_quota))
    print("{:<12}{:>7}{:>9}{:>9}{:>13}".format("문서군", "표본", "모집단", "추출률", "무작위였다면"))
    print("-" * 52)
    for g in GROUP_ORDER:
        nat = args.n * len(by_group[g]) / total
        print("{:<12}{:>7,}{:>9,}{:>9.1%}{:>13.1f}".format(
            g, quota[g], len(by_group[g]),
            (quota[g] / len(by_group[g]) if by_group[g] else 0), nat))

    os.makedirs(args.outdir, exist_ok=True)
    groups_path = os.path.join(args.outdir, "groups_072.json")
    with open(groups_path, "w", encoding="utf-8") as fh:
        json.dump({"run": os.path.basename(args.run.rstrip("/\\")),
                   "riskMargin": args.risk_margin, "collapse": args.collapse,
                   "docs": docs}, fh, ensure_ascii=False)
    sample_path = os.path.join(args.outdir, "sample_500.txt")
    with open(sample_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(picked) + "\n")
    print()
    print("→ " + groups_path + "   (9,001 문서군 라벨 + Base 점수)")
    print("→ " + sample_path + "   ({}장)".format(len(picked)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
