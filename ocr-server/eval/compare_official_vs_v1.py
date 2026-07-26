"""official(순정) vs itemname_V1 head-to-head on the SAME held-out crops.

No middleman: directly answers "V1 is how many pp below/above official on
numbers, on the CURRENT test set". Buckets = same sub-column split as
compare_v1_subcol (품명 / 금액 / 수량 / 코드·날짜 / 한글기타 / 숫자기타).
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

    print("=== held-out test crops (current set) ===")
    for label, items in sorted(buckets.items(), key=lambda p: -len(p[1])):
        print("  %s: %d" % (label, len(items)))

    print("\n[models] official(BASE) vs itemname_V1  — same crops, direct")
    official = create_model(BASE_MODEL)
    v1 = create_model(BASE_MODEL, V1_DIR)

    hdr = ("bucket".ljust(16) + "n".rjust(9) + "official".rjust(10)
           + "V1".rjust(9) + "V1-off".rjust(9)
           + "gain".rjust(7) + "regr".rjust(7) + "net".rjust(8))
    print("\n" + hdr)
    print("-" * len(hdr))
    groups = {}
    for label, items in sorted(buckets.items(), key=lambda p: -len(p[1])):
        paths = [p for p, _, _ in items]
        gts = [g for _, _, g in items]
        op = predict_all(official, paths)
        vp = predict_all(v1, paths)
        n = len(items)
        oe = exact(op, gts)
        ve = exact(vp, gts)
        gains = sum(a.strip() != g.strip() and b.strip() == g.strip()
                    for a, b, g in zip(op, vp, gts))
        regr = sum(a.strip() == g.strip() and b.strip() != g.strip()
                   for a, b, g in zip(op, vp, gts))
        opct = 100.0 * oe / n if n else 0.0
        vpct = 100.0 * ve / n if n else 0.0
        groups[label] = {"n": n, "officialPct": opct, "v1Pct": vpct,
                         "deltaPp": vpct - opct, "gains": gains,
                         "regressions": regr, "net": gains - regr}
        print("%s%9d%9.1f%%%8.1f%%%+9.1f%+7d%7d%+8d"
              % (label.ljust(16), n, opct, vpct, vpct - opct,
                 gains, -regr, gains - regr))

    out = os.path.join(HERE, "finetune", "COMPARE_OFFICIAL_VS_V1.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump({"base": "official", "ft": "itemname_V1",
                   "sameCropSet": True, "groups": groups},
                  fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    print("\n[wrote] %s" % out)


if __name__ == "__main__":
    main()
