"""finetune_report_by_type — 파인튜닝 판정을 '필드 타입별'로 분해.

전체 리포트(finetune_report.py)는 base vs ft 를 뭉뚱그린 exact 만 준다. 하지만
숫자(콤마 붕괴로 회귀)와 품명(한글)은 방향이 정반대일 수 있다(이전 v-run 들에서
품명↑·숫자↓). 이 스크립트는 held-out test 크롭을 gt 로 분류해 타입별 base vs ft
exact / 개선·회귀를 따로 낸다.

분류(gt 기준):
  품명   = 한글 포함(itemName 계열)
  숫자   = 한글 없음 + 숫자 포함(수량/단가/금액/코드/날짜)
  기타   = 나머지

    ../.venv/bin/python eval/finetune_report_by_type.py            # 타입별 전량
    ../.venv/bin/python eval/finetune_report_by_type.py --sample 5000   # 타입별 표본(빠름)
"""
from __future__ import annotations

import argparse
import os
import re

from finetune_report import (BASE_MODEL, CORPUS_DIR, find_ft_inference,  # noqa: E402
                             load_test, predict_all)

HANGUL = re.compile(r"[가-힣]")
DIGIT = re.compile(r"[0-9]")


def _type(gt: str) -> str:
    if HANGUL.search(gt):
        return "품명(한글)"
    if DIGIT.search(gt):
        return "숫자"
    return "기타"


def _exact(preds, gts):
    return sum(p.strip() == g.strip() for p, g in zip(preds, gts))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=0, help="타입별 최대 표본(0=전량)")
    args = ap.parse_args()

    try:
        from paddlex import create_model
    except ImportError:
        from paddlex.inference import create_model  # type: ignore

    rows = load_test()
    # 타입별 버킷
    buckets: dict[str, list] = {}
    for p, rel, gt in rows:
        buckets.setdefault(_type(gt), []).append((p, gt))
    print("=== held-out test 크롭 구성 ===")
    for t, items in sorted(buckets.items(), key=lambda kv: -len(kv[1])):
        print(f"  {t}: {len(items):,}")

    if args.sample:  # 결정적 표본(앞에서 N개; 순서는 test.txt 고정이라 재현됨)
        for t in buckets:
            buckets[t] = buckets[t][: args.sample]

    ft_dir = find_ft_inference()
    if not ft_dir:
        raise SystemExit("no fine-tuned inference dir — run export first")
    print(f"\n[모델] base={BASE_MODEL}  ft={ft_dir}")

    base = create_model(BASE_MODEL)
    ft = create_model(BASE_MODEL, ft_dir)

    print(f"\n{'타입':<12}{'n':>8}{'base exact':>12}{'ft exact':>12}{'Δ%p':>8}"
          f"{'개선':>8}{'회귀':>8}{'순증':>8}")
    print("-" * 76)
    for t, items in sorted(buckets.items(), key=lambda kv: -len(kv[1])):
        paths = [p for p, _ in items]
        gts = [g for _, g in items]
        bp = predict_all(base, paths)
        fp = predict_all(ft, paths)
        n = len(items)
        be = _exact(bp, gts); fe = _exact(fp, gts)
        gains = sum(b.strip() != g.strip() and f.strip() == g.strip()
                    for b, f, g in zip(bp, fp, gts))
        regr = sum(b.strip() == g.strip() and f.strip() != g.strip()
                   for b, f, g in zip(bp, fp, gts))
        bpct = 100 * be / n if n else 0
        fpct = 100 * fe / n if n else 0
        print(f"{t:<12}{n:>8,}{bpct:>11.1f}%{fpct:>11.1f}%{fpct-bpct:>+8.1f}"
              f"{gains:>+8}{-regr:>8}{gains-regr:>+8}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
