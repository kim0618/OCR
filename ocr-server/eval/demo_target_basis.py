"""demo_target_basis — 기준셋(9,001)에서 데모 타깃 후보의 '판정 모수'를 실측한다.

학습 크롭은 코퍼스(AWS)에 있어 로컬에서 셀 수 없지만, 판정 쪽 모수(그 품명이
기준셋에 몇 셀·몇 문서 나오고 base 가 몇 개를 틀리는지)는 리플레이 결과만으로
전수 계산된다. 임의 숫자 대신 이 실측값을 리포트/샘플에 넣는다.

    python eval/demo_target_basis.py                      # 후보 상위 표
    python eval/demo_target_basis.py --targets "디아세렌캡슐,비탁스캡슐"
    python eval/demo_target_basis.py --json out.json      # 기계 판독용 저장
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

RUNS_DIR = os.path.join(HERE, "runs")
HANGUL = re.compile(r"[가-힣]")


def _latest_replay() -> str | None:
    for d in reversed(sorted(glob.glob(os.path.join(RUNS_DIR, "[0-9][0-9][0-9]_*")))):
        if os.path.isdir(os.path.join(d, "compare")):
            return d
    return None


def collect(replay_dir: str) -> tuple[int, dict]:
    """기준셋 전수: 품명별 {셀 수, 문서 수, base 정답/오독/누락, 대표 오독}."""
    stat: dict[str, dict] = defaultdict(
        lambda: {"cells": 0, "docs": set(), "match": 0, "mismatch": 0,
                 "missing": 0, "wrong": defaultdict(int), "gt": ""})
    files = glob.glob(os.path.join(replay_dir, "compare", "*.json"))
    for fp in files:
        try:
            with open(fp, encoding="utf-8") as f:
                j = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        doc = j.get("sourceFile", os.path.basename(fp))
        for r in (j.get("table") or {}).get("rows") or []:
            c = (r.get("cells") or {}).get("itemName")
            if not c:
                continue
            key = (c.get("gtNorm") or "").strip()
            if not key:
                continue
            s = stat[key]
            s["cells"] += 1
            s["docs"].add(doc)
            s["gt"] = (c.get("gt") or "").strip() or s["gt"]
            st = c.get("status")
            if st == "match":
                s["match"] += 1
            elif st == "mismatch":
                s["mismatch"] += 1
                s["wrong"][(c.get("ext") or "").strip() or "(빈칸)"] += 1
            else:
                s["missing"] += 1
                s["wrong"]["(빈칸)"] += 1
    return len(files), stat


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--replay-run", default=None)
    ap.add_argument("--targets", default=None, help="특정 품명만(콤마)")
    ap.add_argument("--min-cells", type=int, default=10, help="후보 최소 출현 셀")
    ap.add_argument("--top", type=int, default=15)
    ap.add_argument("--sort", choices=["mismatch", "cells"], default="mismatch",
                    help="정렬 기준 - mismatch(오독 수, 기본) / cells(출현 셀 수)")
    ap.add_argument("--max-missing-ratio", type=float, default=0.2,
                    help="누락 비율 상한. 누락 셀은 박스를 못 잡아 크롭이 없어 학습·판정 불가")
    ap.add_argument("--json", default=None)
    args = ap.parse_args()

    replay = args.replay_run or _latest_replay()
    if not replay:
        raise SystemExit(f"리플레이 결과가 없습니다: {RUNS_DIR}/<NNN>_*/compare")
    n_docs, stat = collect(replay)
    print(f"[기준셋] {os.path.basename(replay)} · 문서 {n_docs:,}장 · "
          f"품명 셀 {sum(s['cells'] for s in stat.values()):,} · 고유 품명 {len(stat):,}")

    def _row(key: str, s: dict) -> dict:
        return {"name": s["gt"] or key, "cells": s["cells"], "docs": len(s["docs"]),
                "baseMatch": s["match"], "baseMismatch": s["mismatch"],
                "baseMissing": s["missing"],
                "wrong": sorted(s["wrong"].items(), key=lambda x: -x[1])[:3]}

    if args.targets:
        keys = [t.strip().replace(" ", "") for t in args.targets.split(",") if t.strip()]
        rows = [_row(k, s) for k, s in stat.items() if k.replace(" ", "") in keys]
    else:
        # 후보 = base 가 전 출현 오독(정답 0) · 한글 · 충분히 반복되는 품명.
        # 누락(박스 미검출)은 크롭이 없어 학습에도 판정에도 못 쓰므로 비율로 걸러낸다.
        rows = [_row(k, s) for k, s in stat.items()
                if s["match"] == 0 and s["cells"] >= args.min_cells and HANGUL.search(s["gt"] or k)]
        rows = [r for r in rows
                if r["baseMissing"] <= r["cells"] * args.max_missing_ratio]
        rows.sort(key=lambda r: (-r["baseMismatch"], -r["cells"]) if args.sort == "mismatch"
                  else (-r["cells"], -r["baseMismatch"]))
        rows = rows[:args.top]

    print(f"\n{'품명':38} {'셀':>4} {'문서':>4} {'정답':>4} {'오독':>4} {'누락':>4}  대표 오독")
    for r in rows:
        w = " · ".join(f"{k}({n})" for k, n in r["wrong"][:2])
        print(f"{r['name'][:36]:38} {r['cells']:>4} {r['docs']:>4} {r['baseMatch']:>4} "
              f"{r['baseMismatch']:>4} {r['baseMissing']:>4}  {w[:60]}")

    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump({"replay": os.path.basename(replay), "docs": n_docs, "targets": rows},
                      f, ensure_ascii=False, indent=2)
        print(f"\n[저장] {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
