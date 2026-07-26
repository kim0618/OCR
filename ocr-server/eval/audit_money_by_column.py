"""Column-aware numeric-label audit: measure comma preservation ONLY on true
money columns (amount/unitPrice/supply/tax/total/discount), using
dataset/split_metadata.jsonl for the per-crop column. Dates, barcodes, biz
numbers, itemCode/lotNo are reported separately (they legitimately have no
commas). Pure counting; no model. No speculation — numbers only.
"""
from __future__ import annotations

import json
import os
import re

CORPUS = os.path.expanduser("~/OCR/ocr-server/eval/finetune_corpus")
META = os.path.join(CORPUS, "dataset", "split_metadata.jsonl")
TRAIN = os.path.join(CORPUS, "train.txt")
if not os.path.exists(TRAIN):
    TRAIN = os.path.join(CORPUS, "dataset", "train.txt")

MONEY_COLS = {"amount", "unitPrice", "supplyAmount", "taxAmount",
              "totalAmount", "discountAmount"}
QTY_COLS = {"quantity"}
CODE_COLS = {"itemCode", "lotNo", "expiryDate", "manufacturingNo",
             "buyerBizNumber", "supplierBizNumber", "issueDate"}

COMMA_GROUPED = re.compile(r"\d{1,3}(,\d{3})+")   # 819,800
BARE_4PLUS = re.compile(r"(?<!\d)\d{4,}(?!\d)")   # 8198 with no comma
ANY_DIGIT = re.compile(r"\d")


def load_meta():
    m = {}
    if not os.path.exists(META):
        return m
    for ln in open(META, encoding="utf-8"):
        try:
            r = json.loads(ln)
            m[r["path"]] = r
        except (json.JSONDecodeError, KeyError):
            continue
    return m


def bucket_of(col):
    if col in MONEY_COLS:
        return "money"
    if col in QTY_COLS:
        return "qty"
    if col in CODE_COLS:
        return "code/date"
    return None


def main():
    meta = load_meta()
    print("split_metadata rows: %d" % len(meta))
    print("train file: %s" % TRAIN)

    # money-label comma analysis
    stats = {}
    ex_ok, ex_bad = [], []
    matched = 0
    with open(TRAIN, encoding="utf-8") as fh:
        for ln in fh:
            parts = ln.rstrip("\n").split("\t")
            if len(parts) < 2:
                continue
            path, label = parts[0], parts[1]
            rec = meta.get(path)
            if not rec:
                continue
            matched += 1
            col = rec.get("column")
            b = bucket_of(col)
            if not b:
                continue
            s = stats.setdefault(b, {"n": 0, "has_comma": 0,
                                     "bare4plus_nocomma": 0, "no4digit": 0})
            s["n"] += 1
            has_comma = bool(COMMA_GROUPED.search(label))
            has_bare4 = bool(BARE_4PLUS.search(label))
            if has_comma:
                s["has_comma"] += 1
                if b == "money" and len(ex_ok) < 8:
                    ex_ok.append("%s=%s" % (col, label))
            elif has_bare4:
                s["bare4plus_nocomma"] += 1
                if b == "money" and len(ex_bad) < 10:
                    ex_bad.append("%s=%s" % (col, label))
            else:
                s["no4digit"] += 1  # value < 1000, comma irrelevant

    print("train rows matched to metadata: %d" % matched)
    print("=" * 64)
    for b in ("money", "qty", "code/date"):
        s = stats.get(b)
        if not s:
            print("[%s] (없음)" % b)
            continue
        n = s["n"]
        need_comma = s["has_comma"] + s["bare4plus_nocomma"]  # value >= 1000
        pres = 100.0 * s["has_comma"] / need_comma if need_comma else 0.0
        print("[%s] 총 %d" % (b, n))
        print("   1000+ (콤마 대상): %d" % need_comma)
        if need_comma:
            print("     ├ 콤마 보존   : %d  (%.1f%%)" % (s["has_comma"], pres))
            print("     └ 콤마 붕괴   : %d  (%.1f%%)"
                  % (s["bare4plus_nocomma"], 100.0 - pres))
        print("   1000미만(콤마무관): %d" % s["no4digit"])
    print("=" * 64)
    if ex_ok:
        print("money 콤마보존 예: %s" % "  |  ".join(ex_ok))
    if ex_bad:
        print("money 콤마붕괴 예: %s" % "  |  ".join(ex_bad))


if __name__ == "__main__":
    main()
