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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--balance-ratio", type=float, default=1.0,
                    help="balance crops per failure crop (1.0 = equal; 0 = failures only)")
    ap.add_argument("--val", type=float, default=0.1)
    ap.add_argument("--test", type=float, default=0.1)
    ap.add_argument("--seed", type=int, default=20260622)
    args = ap.parse_args()

    fails = load_labels(FAIL_LABELS)            # {rel_path: gt}
    bals = load_labels(BAL_LABELS)
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
