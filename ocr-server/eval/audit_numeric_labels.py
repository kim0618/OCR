"""Audit numeric-label quality in the fine-tune corpus.

For each label pool (failure=labels.txt, balance=labels_correct.txt) measure,
among money-like labels (a maximal digit-run >= 4), how many preserve thousands
commas vs are collapsed bare digits, plus garbage (negative / >=12-digit runs).
Pure text counting; no model. Answers: are numeric labels actually clean?
"""
from __future__ import annotations

import os
import re
import sys

CORPUS = os.path.expanduser("~/OCR/ocr-server/eval/finetune_corpus")
FILES = {
    "failure(labels.txt)": os.path.join(CORPUS, "labels.txt"),
    "balance(labels_correct.txt)": os.path.join(CORPUS, "labels_correct.txt"),
}
# also audit the actual training split if present
for cand in (os.path.join(CORPUS, "dataset", "train.txt"),
             os.path.join(CORPUS, "train.txt")):
    if os.path.exists(cand):
        FILES["train(%s)" % os.path.basename(os.path.dirname(cand) or cand)] = cand
        break

DIGITRUN = re.compile(r"\d+")
# money-like: some digit run of length >= 4 (candidate for thousands sep)
COMMA_GROUPED = re.compile(r"\d{1,3}(,\d{3})+")  # 819,800 / 1,234,567


def classify(label: str):
    runs = DIGITRUN.findall(label)
    if not runs:
        return None  # no digits -> not numeric
    longest = max(len(r) for r in runs)
    is_money_like = longest >= 4  # a bare 4+ digit run = needs/omits comma
    has_comma_group = bool(COMMA_GROUPED.search(label))
    # garbage heuristics
    garbage = ("-" in label and re.search(r"-\d", label)) or longest >= 12
    return {"money_like": is_money_like, "has_comma": has_comma_group,
            "garbage": garbage, "longest": longest}


def audit(path: str):
    total = numeric = money_like = money_comma = money_collapsed = garbage = 0
    ex_collapsed, ex_comma, ex_garbage = [], [], []
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as fh:
        for ln in fh:
            parts = ln.rstrip("\n").split("\t")
            if len(parts) < 2:
                continue
            label = parts[1]
            total += 1
            c = classify(label)
            if not c:
                continue
            numeric += 1
            if c["garbage"]:
                garbage += 1
                if len(ex_garbage) < 5:
                    ex_garbage.append(label)
            if c["money_like"]:
                money_like += 1
                if c["has_comma"]:
                    money_comma += 1
                    if len(ex_comma) < 5:
                        ex_comma.append(label)
                else:
                    money_collapsed += 1
                    if len(ex_collapsed) < 6:
                        ex_collapsed.append(label)
    return {
        "total": total, "numeric": numeric, "money_like": money_like,
        "money_comma": money_comma, "money_collapsed": money_collapsed,
        "garbage": garbage, "ex_collapsed": ex_collapsed,
        "ex_comma": ex_comma, "ex_garbage": ex_garbage,
    }


def main() -> int:
    for name, path in FILES.items():
        r = audit(path)
        print("=" * 60)
        print("[%s]" % name)
        if r is None:
            print("  (파일 없음)")
            continue
        print("  총 라벨            : %d" % r["total"])
        print("  숫자 포함 라벨      : %d" % r["numeric"])
        ml = r["money_like"]
        print("  money-like(4자리+) : %d" % ml)
        if ml:
            pres = 100.0 * r["money_comma"] / ml
            print("    ├ 콤마 보존       : %d  (%.1f%%)" % (r["money_comma"], pres))
            print("    └ 콤마 붕괴(맨숫자): %d  (%.1f%%)"
                  % (r["money_collapsed"], 100.0 - pres))
        print("  garbage(음수/12자리+): %d" % r["garbage"])
        if r["ex_comma"]:
            print("  예) 콤마보존 : %s" % " | ".join(r["ex_comma"][:5]))
        if r["ex_collapsed"]:
            print("  예) 콤마붕괴 : %s" % " | ".join(r["ex_collapsed"][:6]))
        if r["ex_garbage"]:
            print("  예) garbage  : %s" % " | ".join(r["ex_garbage"][:5]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
