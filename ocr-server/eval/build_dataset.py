"""build_dataset — combine the corpus crops into PaddleOCR rec train/val/test lists.

Reads the two accumulated label pools in the pinned corpus:
  labels.txt          failure-target crops (what we want the model to learn)
  labels_correct.txt  correct-read crops (balance, anti-forgetting)

Combines them at a chosen ratio, de-dups, shuffles deterministically (fixed
seed), and writes PaddleOCR rec label lists under eval/finetune_corpus/dataset/:
  train.txt val.txt test.txt   (each line: <crop_rel_path>\t<label>)
plus manifest.json with the counts and the split policy.

Paths in the lists are relative to the corpus dir, so PaddleOCR's data_dir =
eval/finetune_corpus/ and label_file_list = dataset/train.txt etc.

Pure file ops — no PaddleOCR/GPU needed, runnable & testable now. This is the
buildable half of the fine-tune pipeline; actual train/export is in RECIPE.md.

    ../.venv/Scripts/python.exe eval/build_dataset.py
    ../.venv/Scripts/python.exe eval/build_dataset.py --balance-ratio 1.0 --val 0.1 --test 0.1
"""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from finetune_ledger import CORPUS_DIR  # noqa: E402
from finetune_crops import load_labels  # noqa: E402

FAIL_LABELS = os.path.join(CORPUS_DIR, "labels.txt")
BAL_LABELS = os.path.join(CORPUS_DIR, "labels_correct.txt")
DATASET_DIR = os.path.join(CORPUS_DIR, "dataset")


def _split(items: list, val: float, test: float, seed: int):
    rnd = random.Random(seed)
    items = list(items)
    rnd.shuffle(items)
    n = len(items)
    n_test = int(n * test)
    n_val = int(n * val)
    return (items[n_test + n_val:], items[n_test:n_test + n_val], items[:n_test])  # train, val, test


def _column_filter(fails: dict, columns: set, min_match: float | None,
                   raw_only: bool = False) -> dict:
    """failure 크롭을 ledger 의 column/matchRatio 로 제한.

    크롭 파일명 = sha1(crop_key) 라 ledger.jsonl 엔트리에서 역산 가능(finetune_crops 와
    동일 해시). columns 로 학습 표적(예: itemName)만 남기고, min_match 로 '크롭에 안
    보이는 정식명 라벨'(rewrite 학습 유발, 1차 run char-sim 하락 원인)을 컷.
    """
    import json
    from finetune_crops import crop_name
    from finetune_ledger import CORPUS_PATH
    allowed = set()
    for ln in open(CORPUS_PATH, encoding="utf-8"):
        ln = ln.strip()
        if not ln:
            continue
        try:
            e = json.loads(ln)
        except json.JSONDecodeError:
            continue
        if columns and e.get("column") not in columns:
            continue
        if min_match is not None and (e.get("matchRatio") or 0) < min_match:
            continue
        if raw_only and e.get("labelForm") != "raw":
            continue    # 정규화 라벨(구세대 적립분) 배제 — rewrite 학습 차단
        allowed.add("crops/" + crop_name(e))
    return {p: gt for p, gt in fails.items() if p in allowed}


def _label_gate(fails: dict, n_sample: int = 12) -> None:
    """학습 전 라벨 육안 게이트: 인쇄형 보존 신호(공백/슬래시/대문자/괄호) 통계 + 샘플.

    전부 0% 에 가까우면 라벨이 아직 정규화형 = 학습 돌리면 안 됨 (v1/v2 재발).
    """
    import random as _r
    n = len(fails) or 1
    sig = {"공백": sum(1 for g in fails.values() if " " in g),
           "슬래시(/)": sum(1 for g in fails.values() if "/" in g),
           "대문자": sum(1 for g in fails.values() if any(c.isupper() for c in g)),
           "괄호": sum(1 for g in fails.values() if "(" in g)}
    stats = " · ".join(f"{k} {100.0 * v / n:.1f}%" for k, v in sig.items())
    print(f"[label-gate] failure {n:,}건 인쇄형 보존율: {stats}")
    rnd = _r.Random(7)
    for p, g in rnd.sample(sorted(fails.items()), min(n_sample, len(fails))):
        print(f"[label-gate]   {g[:60]}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--balance-ratio", type=float, default=1.0,
                    help="balance crops per failure crop (1.0 = equal; 0 = failures only)")
    ap.add_argument("--columns", default=None,
                    help="failure 크롭을 이 컬럼들로 제한 (콤마구분, 예: itemName). "
                         "balance(정답 크롭)는 그대로 둬 숫자·타컬럼 망각 방지 앵커로 유지")
    ap.add_argument("--min-match", type=float, default=None,
                    help="failure 크롭 matchRatio 하한(예: 0.7) — 크롭에 없는 텍스트를 "
                         "라벨로 주는 rewrite 학습 차단")
    ap.add_argument("--hangul-min", type=int, default=0,
                    help="failure 라벨의 최소 한글 글자 수(예: 2). 라벨=정규화GT 라 숫자/날짜 "
                         "크롭은 '구분자 벗기기'를 가르침(v2 실측: 콤마 스트립·짧은숫자 삭제 회귀). "
                         "한글 품명만 남기고 숫자는 balance(인쇄 포맷 보존)로만 노출")
    ap.add_argument("--raw-only", action="store_true",
                    help="labelForm=raw(원문 GT 라벨) 엔트리만 학습 — 정규화 라벨 구세대 적립분 배제")
    ap.add_argument("--val", type=float, default=0.1)
    ap.add_argument("--test", type=float, default=0.1)
    ap.add_argument("--seed", type=int, default=20260622)
    args = ap.parse_args()

    fails = load_labels(FAIL_LABELS)            # {rel_path: gt}
    bals = load_labels(BAL_LABELS)
    if args.columns or args.min_match is not None or args.raw_only:
        cols = set(c.strip() for c in (args.columns or "").split(",") if c.strip())
        n0 = len(fails)
        fails = _column_filter(fails, cols, args.min_match, raw_only=args.raw_only)
        print(f"[build_dataset] column/match filter: failure {n0:,} -> {len(fails):,} "
              f"(columns={sorted(cols) or 'all'}, min_match={args.min_match}, "
              f"raw_only={args.raw_only})")
    if args.hangul_min > 0:
        n0 = len(fails)
        _hang = re.compile(r"[가-힣]")
        fails = {p: gt for p, gt in fails.items() if len(_hang.findall(gt)) >= args.hangul_min}
        print(f"[build_dataset] hangul filter(>= {args.hangul_min}자): "
              f"failure {n0:,} -> {len(fails):,}")
    _label_gate(fails)   # 학습 전 육안 게이트: 인쇄형 보존율 0%대면 돌리지 말 것
    if not fails and not bals:
        print(f"no labels in {CORPUS_DIR} (run finetune_crops[_balance] first)"); return 2

    fail_items = list(fails.items())
    bal_items = list(bals.items())
    # sample balance to the requested ratio of the failure count (deterministic)
    want_bal = int(len(fail_items) * args.balance_ratio)
    if 0 <= want_bal < len(bal_items):
        random.Random(args.seed).shuffle(bal_items)
        bal_items = bal_items[:want_bal]

    combined = fail_items + bal_items            # rel paths are distinct (separate dirs)
    tr, va, te = _split(combined, args.val, args.test, args.seed)

    os.makedirs(DATASET_DIR, exist_ok=True)
    for name, rows in (("train", tr), ("val", va), ("test", te)):
        tmp = os.path.join(DATASET_DIR, name + ".txt.tmp")
        with open(tmp, "w", encoding="utf-8") as fh:
            for rel, gt in rows:
                fh.write(f"{rel}\t{gt}\n")
        os.replace(tmp, os.path.join(DATASET_DIR, name + ".txt"))

    manifest = {
        "corpusDir": CORPUS_DIR,
        "dataDirForPaddle": CORPUS_DIR,
        "counts": {"failure": len(fail_items), "balanceAvailable": len(bals),
                   "balanceUsed": len(bal_items), "combined": len(combined),
                   "train": len(tr), "val": len(va), "test": len(te)},
        "policy": {"balanceRatio": args.balance_ratio, "val": args.val,
                   "test": args.test, "seed": args.seed},
    }
    json.dump(manifest, open(os.path.join(DATASET_DIR, "manifest.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)

    sys.stdout.reconfigure(errors="replace")
    print(f"[build_dataset] failure={len(fail_items)} balance={len(bal_items)}/{len(bals)} "
          f"-> train={len(tr)} val={len(va)} test={len(te)}")
    print(f"[build_dataset] lists -> {DATASET_DIR}/(train|val|test).txt  + manifest.json")
    print(f"[build_dataset] PaddleOCR data_dir = {CORPUS_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
