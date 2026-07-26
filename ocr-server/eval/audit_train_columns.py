"""What is actually in the fine-tune training set, by column, with label
patterns — so we can decide the composition (keep real GT fields, cut barcodes/
junk). Joins train.txt labels with dataset/split_metadata.jsonl. Pure counting.
"""
from __future__ import annotations

import json
import os
import re
from collections import defaultdict

CORPUS = os.path.expanduser("~/OCR/ocr-server/eval/finetune_corpus")
META = os.path.join(CORPUS, "dataset", "split_metadata.jsonl")
TRAIN = os.path.join(CORPUS, "train.txt")
if not os.path.exists(TRAIN):
    TRAIN = os.path.join(CORPUS, "dataset", "train.txt")

DIGITRUN = re.compile(r"\d+")


def main():
    # path -> (column, source) for train split
    meta = {}
    for ln in open(META, encoding="utf-8"):
        try:
            r = json.loads(ln)
        except json.JSONDecodeError:
            continue
        if r.get("split") == "train":
            meta[r["path"]] = (r.get("column"), r.get("source"))

    by_col = defaultdict(lambda: {"n": 0, "src": defaultdict(int),
                                  "maxrun": defaultdict(int), "ex": []})
    unmatched = 0
    total = 0
    with open(TRAIN, encoding="utf-8") as fh:
        for ln in fh:
            parts = ln.rstrip("\n").split("\t")
            if len(parts) < 2:
                continue
            total += 1
            path, label = parts[0], parts[1]
            rec = meta.get(path)
            if not rec:
                unmatched += 1
                col, src = "(NO-META)", "?"
            else:
                col, src = rec
                col = col or "(none)"
            b = by_col[col]
            b["n"] += 1
            b["src"][src] += 1
            runs = DIGITRUN.findall(label)
            longest = max((len(r) for r in runs), default=0)
            # bucket max digit-run length
            key = "0" if longest == 0 else ("1-3" if longest <= 3 else
                  ("4-7" if longest <= 7 else ("8-11" if longest <= 11 else "12+")))
            b["maxrun"][key] += 1
            if len(b["ex"]) < 4:
                b["ex"].append(label[:30])

    print("train total: %d   (NO-META unmatched: %d)" % (total, unmatched))
    print("=" * 90)
    print("%-20s%9s   %-22s  %-28s" % ("column", "n", "digit-run-len dist", "examples"))
    print("-" * 90)
    for col, b in sorted(by_col.items(), key=lambda kv: -kv[1]["n"]):
        dist = " ".join("%s:%d" % (k, b["maxrun"][k])
                        for k in ("0", "1-3", "4-7", "8-11", "12+")
                        if b["maxrun"][k])
        ex = " | ".join(b["ex"][:3])
        print("%-20s%9d   %-22s  %s" % (col, b["n"], dist, ex))


if __name__ == "__main__":
    main()
