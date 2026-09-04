"""llm_sample_500 — 072 전처리 텔레메트리로 문서군을 가르고 500장 층화표본을 뽑는다.

전처리 축의 질문은 "우리가 방향을 잘못 잡아 깨뜨린 문서를 VLM 이 그냥 읽나" 하나다.
위험군(margin<20)은 9,001 중 1,286 이라 무작위 500 에도 71장은 들어오지만, 그 안에서
실제로 깨진 문서는 훨씬 드물다. 그래서 두 겹으로 잡는다 - 위험군에 쿼터를 주고
(--risk-quota), **회전을 실제로 걸었는데 붕괴한 문서는 전량 강제 편입**한다.
나머지 세 군은 실발생률대로 비례 배분하고, 전체 발생률이 필요한 자리(파서 탭)는
9,001 본판정이 담당한다.

강제 편입 목록은 **분석 중인 run 에서 그때그때 계산한다**. 예전 작업 파일을 읽으면
기준선과 표본이 서로 다른 run 을 따라가 어긋난다(068 목록 85장 중 25장은 072 에서
이미 안 깨졌고, 072 에서 새로 깨진 75장은 그 목록에 없었다).

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

# 문서군은 "우리가 무엇을 했고 그 결과가 어땠나"로 가른다.
# margin(방향 판정 확신도)은 군을 가르는 기준이 아니다 - 애매했다는 사실만으로는
# 할 일이 정해지지 않는다. 답이 걸린 행은 맨 아래 "회전 적용 · 붕괴" = 오회전이다.
MISROT, ROTOK, SKEW, NONE = "회전적용·붕괴", "회전적용·정상", "기울기보정", "전처리없음"
GROUP_ORDER = [NONE, SKEW, ROTOK, MISROT]   # 답이 걸린 행이 마지막


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


def group_of(f: dict) -> str:
    """결과 기준 4분류. 붕괴 여부가 필요하므로 compare/ 결합 뒤에 부른다."""
    rotated = f["orientApplied"] and f["orientAngle"] not in (0, None)
    if rotated:
        return MISROT if f.get("collapsed") else ROTOK
    return SKEW if f["deskewApplied"] else NONE


def write_list(path: str, lines: list[str]) -> None:
    """목록 파일은 AWS(리눅스)로 건너가므로 LF 로 쓴다."""
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")


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
    ap.add_argument("--collapse", type=float, default=0.10, help="문서 붕괴 임계(cell 정확도)")
    ap.add_argument("--n", type=int, default=500)
    ap.add_argument("--rotok-quota", type=int, default=100,
                    help="'회전 적용 · 정상' 에 줄 최소 장수 - 오회전 행의 대조군이라 "
                         "비례 배분(약 45장)만으로는 얇다")
    ap.add_argument("--seed", type=int, default=20260904)
    ap.add_argument("--force", default="",
                    help="강제 편입할 sourceFile 목록 파일(선택). 규칙 산출분에 더해진다")
    ap.add_argument("--no-force-rule", action="store_true",
                    help="'회전 적용 AND 붕괴' 자동 강제 편입을 끈다")
    ap.add_argument("--smoke", type=int, default=50, help="환경 확정 게이트용 표본(500 밖)")
    ap.add_argument("--smoke-long", type=int, default=10,
                    help="스모크 중 행수 상위 강제분 - max_tokens 출력 잘림을 잡는 자리")
    ap.add_argument("--outdir", default=os.path.join(HERE, "LLM"),
                    help="LLM 폴더. 목록은 inputs/ 로, 라벨·대조본은 data/ 로 나뉜다")
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
        f["status"] = s.get("status")
        f["imagePath"] = s.get("imagePath")
        try:
            f["rowCount"] = int(s.get("rowCount") or 0)
        except (TypeError, ValueError):
            f["rowCount"] = 0
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

    # 붕괴 여부가 채워진 뒤에 군을 정한다.
    for f in docs.values():
        f["group"] = group_of(f)

    by_group: dict[str, list[str]] = {g: [] for g in GROUP_ORDER}
    for src, f in docs.items():
        by_group[f["group"]].append(src)
    for g in by_group:
        by_group[g].sort()

    total = len(docs)
    print("문서 {:,}  (compare 결합 {:,})   붕괴 임계 {:.0%}".format(
        total, n_cmp, args.collapse))
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
    # 오회전은 전량(답이 걸린 군) · 회전 정상은 그 대조군이라 바닥값을 준다.
    fixed = {MISROT: len(by_group[MISROT]),
             ROTOK: min(args.rotok_quota, len(by_group[ROTOK]))}
    quota = dict(fixed)
    rest_pop = sum(len(by_group[g]) for g in GROUP_ORDER if g not in fixed)
    rest_n = args.n - sum(fixed.values())
    alloc = []
    for g in GROUP_ORDER:
        if g in fixed:
            continue
        exact = rest_n * len(by_group[g]) / rest_pop if rest_pop else 0
        quota[g] = min(int(exact), len(by_group[g]))
        alloc.append((exact - quota[g], g))
    for _, g in sorted(alloc, reverse=True):          # 잔여분은 소수부 큰 군부터
        if sum(quota.values()) >= args.n:
            break
        if quota[g] < len(by_group[g]):
            quota[g] += 1

    # 강제 편입. 대개 각 군의 쿼터 안에 들어가므로 장수는 그대로고 '누가 뽑히나'만 고정된다.
    # 어느 군에서 쿼터를 넘으면 그 군을 늘리고 가장 큰 군(정상)에서 같은 수만큼 뺀다.
    # 강제 편입 목록은 **분석 중인 run 에서 직접 계산한다**. 옛 작업 파일
    # (misrot_candidates.txt 는 068 산출)을 읽으면 기준선이 072 인데 표본만 068 을
    # 따라가 어긋난다 - 실제로 068 85장 중 25장은 072 에서 이미 안 깨졌고,
    # 072 에서 새로 깨진 75장은 그 목록에 없었다.
    # 규칙 = 회전을 실제로 걸었는데(angle != 0) 문서가 붕괴한 것 = "우리가 돌려서 깨뜨린" 후보.
    forced: set[str] = set()
    if not args.no_force_rule:
        forced = set(by_group[MISROT])          # 회전 적용 AND 붕괴 = 오회전, 전량
    if args.force:
        forced |= {ln.strip() for ln in open(args.force, encoding="utf-8") if ln.strip()}
    forced &= set(docs)
    forced_by_group = {g: sorted(forced & set(by_group[g])) for g in GROUP_ORDER}
    overflow = 0
    for g in GROUP_ORDER:
        need = len(forced_by_group[g])
        if need > quota[g]:
            overflow += need - quota[g]
            quota[g] = need
    if overflow:
        big = max((g for g in GROUP_ORDER), key=lambda g: quota[g] - len(forced_by_group[g]))
        quota[big] = max(len(forced_by_group[big]), quota[big] - overflow)

    picked: list[str] = []
    for g in GROUP_ORDER:
        keep = forced_by_group[g][:quota[g]]
        pool = [s for s in by_group[g] if s not in forced]
        picked += keep + rng.sample(pool, max(0, quota[g] - len(keep)))
    picked.sort()

    print()
    print("표본 {}장  (seed {}, 회전정상 쿼터 {}, 오회전 강제편입 {}장)".format(
        len(picked), args.seed, args.rotok_quota, len(forced)))
    print("{:<12}{:>7}{:>7}{:>9}{:>9}{:>13}".format(
        "문서군", "표본", "강제", "모집단", "추출률", "무작위였다면"))
    print("-" * 59)
    for g in GROUP_ORDER:
        nat = args.n * len(by_group[g]) / total
        print("{:<12}{:>7,}{:>7,}{:>9,}{:>9.1%}{:>13.1f}".format(
            g, quota[g], len(forced_by_group[g][:quota[g]]), len(by_group[g]),
            (quota[g] / len(by_group[g]) if by_group[g] else 0), nat))
    got = len(forced & set(picked))
    print("오회전(회전 적용 AND 붕괴 · {} 산출) {}장 중 표본에 {}장 ({})".format(
        os.path.basename(args.run.rstrip("/\\"))[:3], len(forced), got,
        "전량" if got == len(forced) else "일부 - 쿼터에 밀림"))

    # 역할 분리: inputs/ = 러너가 먹는 목록, data/ = 채점·분석이 다시 읽는 라벨
    in_dir = os.path.join(args.outdir, "inputs")
    dat_dir = os.path.join(args.outdir, "data")
    os.makedirs(in_dir, exist_ok=True)
    os.makedirs(dat_dir, exist_ok=True)
    groups_path = os.path.join(dat_dir, "groups_072.json")
    with open(groups_path, "w", encoding="utf-8") as fh:
        json.dump({"run": os.path.basename(args.run.rstrip("/\\")),
                   "collapse": args.collapse,
                   "docs": docs}, fh, ensure_ascii=False)
    # llm_runner 의 --list 는 eval/ 기준 이미지 경로를 받는다(sourceFile 아님).
    # samples 의 imagePath 가 바로 그 형태 - data/invoice_war/images_replay/<월>/<docId>/<파일>.
    missing = [s for s in picked if not docs[s].get("imagePath")]
    sample_path = os.path.join(in_dir, "sample_500.txt")
    write_list(sample_path, [docs[s]["imagePath"] for s in picked if docs[s].get("imagePath")])
    srcs_path = os.path.join(dat_dir, "sample_500_sources.txt")
    write_list(srcs_path, picked)

    # ── 스모크 ────────────────────────────────────────────────────────────
    # 환경 확정 게이트용. 500 표본 밖에서 뽑아야 본판정이 스모크로 데워지지 않는다.
    # 행 많은 문서를 강제로 넣는 이유: max_tokens 로 출력이 잘리면 '행수 불일치'로
    # 오해되는데, 무작위 50장은 대개 짧아서 그 사고를 못 잡는다.
    picked_set = set(picked)
    pool = [s for s in sorted(docs) if s not in picked_set and docs[s].get("imagePath")]
    long_docs = sorted(pool, key=lambda s: (-docs[s]["rowCount"], s))[:args.smoke_long]
    rest = [s for s in pool if s not in set(long_docs)]
    smoke = long_docs + rng.sample(rest, max(0, args.smoke - len(long_docs)))
    rows = [docs[s]["rowCount"] for s in smoke]
    print()
    print("스모크 {}장  (500 표본 밖, 행수 상위 {}장 강제)".format(len(smoke), len(long_docs)))
    print("  행수 최대 {} / 중앙 {} / 최소 {}   강제분: {}".format(
        max(rows), sorted(rows)[len(rows) // 2], min(rows),
        ", ".join(str(docs[s]["rowCount"]) for s in long_docs)))
    smoke_path = os.path.join(in_dir, "smoke_50.txt")
    write_list(smoke_path, [docs[s]["imagePath"] for s in smoke])
    write_list(os.path.join(dat_dir, "smoke_50_sources.txt"), smoke)

    print()
    if missing:
        print("⚠ imagePath 없는 문서 {}개는 목록에서 빠짐: {}".format(len(missing), missing[:3]))
    print("→ " + groups_path + "   (9,001 문서군 라벨 + Base 점수)")
    print("→ " + sample_path + "   ({}장, llm_runner --list 용 이미지 경로)".format(
        len(picked) - len(missing)))
    print("→ " + srcs_path + "   (같은 표본의 sourceFile - 채점·대조용)")
    print("→ " + smoke_path + "   ({}장, 환경 확정 게이트 + full_text A/B)".format(len(smoke)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
