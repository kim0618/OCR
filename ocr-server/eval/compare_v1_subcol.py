"""combined vs V1 on the SAME held-out crops, with the numeric slice broken
down by real column: 금액 / 수량 / 코드·날짜. Answers whether FT improved the
MONEY numbers specifically (not lumped with barcodes/codes/dates).
Read-only inference. No speculation — measured exact-match per sub-column.
"""
from __future__ import annotations

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from finetune_report import BASE_MODEL, load_test, predict_all  # noqa: E402
from finetune_report_by_type import _load_test_metadata  # noqa: E402

V1_DIR = os.path.join(HERE, "finetune", "versions", "itemname_V1", "inference")
COMBINED_DIR = os.path.join(HERE, "finetune", "output", "best_accuracy", "inference")

HANGUL = re.compile(r"[가-힣]")
DIGIT = re.compile(r"[0-9]")
MONEY = {"amount", "unitPrice", "supplyAmount", "taxAmount", "totalAmount", "discountAmount"}
QTY = {"quantity"}
CODE = {"itemCode", "lotNo", "expiryDate", "manufacturingNo",
        "buyerBizNumber", "supplierBizNumber", "issueDate"}


def subtype(gt, meta):
    col = (meta or {}).get("column")
    if col in ("itemName", "itemNameMaster"):
        return "품명"
    if col in MONEY:
        return "숫자:금액"
    if col in QTY:
        return "숫자:수량"
    if col in CODE:
        return "숫자:코드/날짜"
    if HANGUL.search(gt):
        return "한글(기타)"
    if DIGIT.search(gt):
        return "숫자:기타"
    return "기타"


def exact(preds, gts):
    return sum(p.strip() == g.strip() for p, g in zip(preds, gts))


def main():
    try:
        from paddlex import create_model
    except ImportError:
        from paddlex.inference import create_model  # type: ignore

    rows = load_test()
    meta = _load_test_metadata()
    buckets = {}
    for path, rel, gt in rows:
        buckets.setdefault(subtype(gt, meta.get(rel)), []).append((path, rel, gt))

    print("=== held-out test 크롭 구성 (컬럼 기준) ===")
    for label, items in sorted(buckets.items(), key=lambda p: -len(p[1])):
        print("  %s: %d" % (label, len(items)))

    print("\n[models] V1 vs combined (same crops)")
    v1 = create_model(BASE_MODEL, V1_DIR)
    cmb = create_model(BASE_MODEL, COMBINED_DIR)

    hdr = ("bucket".ljust(16) + "n".rjust(9) + "V1".rjust(9)
           + "combined".rjust(10) + "Δvs V1".rjust(9)
           + "gain".rjust(7) + "regr".rjust(7) + "net".rjust(8))
    print("\n" + hdr)
    print("-" * len(hdr))
    groups = {}
    for label, items in sorted(buckets.items(), key=lambda p: -len(p[1])):
        paths = [p for p, _, _ in items]
        gts = [g for _, _, g in items]
        v1p = predict_all(v1, paths)
        cp = predict_all(cmb, paths)
        n = len(items)
        v1e = exact(v1p, gts)
        ce = exact(cp, gts)
        gains = sum(a.strip() != g.strip() and b.strip() == g.strip()
                    for a, b, g in zip(v1p, cp, gts))
        regr = sum(a.strip() == g.strip() and b.strip() != g.strip()
                   for a, b, g in zip(v1p, cp, gts))
        v1pct = 100.0 * v1e / n if n else 0.0
        cpct = 100.0 * ce / n if n else 0.0
        groups[label] = {"n": n, "v1Pct": v1pct, "combinedPct": cpct,
                         "deltaPp": cpct - v1pct, "gains": gains,
                         "regressions": regr, "net": gains - regr}
        print("%s%9d%8.1f%%%9.1f%%%+9.1f%+7d%7d%+8d"
              % (label.ljust(16), n, v1pct, cpct, cpct - v1pct,
                 gains, -regr, gains - regr))

    out = os.path.join(HERE, "finetune", "COMPARE_V1_SUBCOL.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump({"base": "itemname_V1", "ft": "combined_260724_1440",
                   "groups": groups}, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    print("\n[wrote] %s" % out)


if __name__ == "__main__":
    main()
