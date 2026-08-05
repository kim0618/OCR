"""demo_anchor_strata — 앵커 성분 층화 실험용 풀 모수 집계.

`build_demo_dataset.py` 의 앵커 후보(정답풀 labels_correct.txt) 를 품명 크롭의
<문자 성분>으로 층화해 각 층에 몇 장이 있는지 센다. 성분 배정 비율을 정하려면
먼저 뽑을 수 있는 상한을 알아야 한다.

층 서명: H=한글 E=영문 N=숫자 S=기호  (판정 분석과 같은 규칙이라 결과가 바로 대조된다)

★왜 필요한가(2026-08-05 판정셋 실측): 품명 앵커를 무작위로 뽑으면 풀 분포를 그대로
  따라가는데, 잃어버림 기여 36.3%인 HENS(한글+영문+숫자+기호)에 앵커가 19.6%만
  배정된다. 배정과 기여가 어긋난 상태다. 층화하려면 층별 풀 모수가 필요하다.

    python eval/demo_anchor_strata.py
    python eval/demo_anchor_strata.py --plan "HENS=0.473,HNS=0.135,HEN=0.122,HS=0.095,H=0.088,HES=0.054,HN=0.020,HE=0.014" --item 1654
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from finetune_ledger import CORPUS_DIR  # noqa: E402
from finetune_crops import load_labels  # noqa: E402

BAL_LABELS = os.path.join(CORPUS_DIR, "labels_correct.txt")
BAL_META = os.path.join(CORPUS_DIR, "labels_correct.meta.jsonl")
REPLAY = os.path.join(CORPUS_DIR, "replay_sources.txt")

SYMBOL_RE = r"[()\[\]{}/\\·,.:;+*%~°'\"-]"


def sig(label: str) -> str:
    """품명 앵커 성분 서명. build_demo_dataset._sig 와 같은 규칙을 유지할 것."""
    s = ""
    if re.search(r"[가-힣]", label):
        s += "H"
    if re.search(r"[A-Za-z]", label):
        s += "E"
    if re.search(r"[0-9]", label):
        s += "N"
    if re.search(SYMBOL_RE, label):
        s += "S"
    return s or "-"


def _meta() -> tuple[dict[str, str | None], dict[str, str | None]]:
    """정답풀 사이드카: 크롭 → (column, src). 없으면 컬럼을 알 수 없다."""
    col: dict[str, str | None] = {}
    src: dict[str, str | None] = {}
    if not os.path.exists(BAL_META):
        return col, src
    for line in open(BAL_META, encoding="utf-8"):
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        path = rec.get("path") or rec.get("crop")
        if path:
            col[path] = rec.get("column")
            src[path] = rec.get("src")
    return col, src


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", default="",
                    help="검증할 배정안 'HENS=0.47,...' (품명 앵커 내부 비율)")
    ap.add_argument("--item", type=int, default=0,
                    help="품명 앵커 총 장수 — --plan 의 소진율 계산에 쓴다")
    ap.add_argument("--replay-sources", default=REPLAY)
    args = ap.parse_args()

    col, src = _meta()
    replay = set()
    if os.path.exists(args.replay_sources):
        replay = set(open(args.replay_sources, encoding="utf-8").read().split())

    pools: dict[str, int] = {}
    n_item = n_num = n_rest = n_skip = 0
    for path, label in load_labels(BAL_LABELS).items():
        if replay and src.get(path) in replay:
            n_skip += 1                      # 기준셋 출신 = 앵커 금지
            continue
        flat = label.strip()
        if col.get(path) == "itemName":
            pools[sig(flat)] = pools.get(sig(flat), 0) + 1
            n_item += 1
        elif flat.isdigit() and len(flat) <= 3:
            n_num += 1
        else:
            n_rest += 1

    print(f"정답풀 총 {n_item + n_num + n_rest:,}  "
          f"(품명 {n_item:,} · 짧은숫자 {n_num:,} · 나머지 {n_rest:,})  "
          f"기준셋 제외 {n_skip:,}")
    print()
    print(f"{'서명':6s} {'조합':24s} {'풀':>9s} {'비중':>7s}")
    for key, cnt in sorted(pools.items(), key=lambda x: -x[1]):
        name = "+".join({"H": "한글", "E": "영문", "N": "숫자", "S": "기호"}[c] for c in key)
        print(f"{key:6s} {name:24s} {cnt:9,d} {100.0 * cnt / n_item:6.1f}%")

    if args.plan and args.item:
        print()
        print(f"[배정안 검증] 품명 앵커 {args.item:,}장 기준")
        print(f"{'서명':6s} {'요청':>7s} {'풀':>9s} {'소진율':>8s}  판정")
        short = []
        for part in args.plan.split(","):
            key, frac = part.split("=")
            key = key.strip()
            want = int(args.item * float(frac))
            have = pools.get(key, 0)
            rate = 100.0 * want / have if have else float("inf")
            mark = "OK" if want <= have * 0.30 else ("빠듯" if want <= have else "부족")
            if mark != "OK":
                short.append((key, want, have))
            print(f"{key:6s} {want:7,d} {have:9,d} {rate:7.1f}%  {mark}")
        if short:
            print()
            print("※ 빠듯/부족 층은 폴백이 나머지 풀에서 채운다 — 총량은 맞지만 "
                  "의도한 성분이 안 들어간다. strataGot 으로 사후 확인 필수.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
