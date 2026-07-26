"""combined vs V1 head-to-head on the SAME held-out crops (current test split).

Reuses finetune_report helpers. Treats V1 as 'base' and combined as 'ft' so the
per-type deltas ARE combined-vs-V1 directly (no cross-set subtraction).
Read-only inference; writes finetune/COMPARE_COMBINED_VS_V1.json only.
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from finetune_report import BASE_MODEL, load_test, predict_all  # noqa: E402
from finetune_report_by_type import _load_test_metadata, _type, _exact  # noqa: E402

V1_DIR = os.path.join(HERE, "finetune", "versions", "itemname_V1", "inference")
COMBINED_DIR = os.path.join(HERE, "finetune", "output", "best_accuracy", "inference")


def main() -> int:
    try:
        from paddlex import create_model
    except ImportError:
        from paddlex.inference import create_model  # type: ignore

    rows = load_test()
    metadata = _load_test_metadata()
    buckets: dict[str, list] = {}
    for path, rel, gt in rows:
        meta = metadata.get(rel)
        buckets.setdefault(_type(gt, meta), []).append((path, rel, gt))

    print("=== held-out test crops (combined's test split) ===")
    for label, items in sorted(buckets.items(), key=lambda p: -len(p[1])):
        print("  %s: %d" % (label, len(items)))

    print("\n[models] V1=%s" % V1_DIR)
    print("         combined=%s" % COMBINED_DIR)
    v1 = create_model(BASE_MODEL, V1_DIR)
    cmb = create_model(BASE_MODEL, COMBINED_DIR)

    hdr = ("type".ljust(12) + "n".rjust(9) + "V1_exact".rjust(11)
           + "cmb_exact".rjust(11) + "dPp_vsV1".rjust(11)
           + "gain".rjust(8) + "regr".rjust(8) + "net".rjust(8))
    print("\n" + hdr)
    print("-" * len(hdr))

    groups: dict[str, dict] = {}
    for label, items in sorted(buckets.items(), key=lambda p: -len(p[1])):
        paths = [p for p, _, _ in items]
        gts = [g for _, _, g in items]
        v1p = predict_all(v1, paths)
        cp = predict_all(cmb, paths)
        n = len(items)
        v1e = _exact(v1p, gts)
        ce = _exact(cp, gts)
        gains = sum(a.strip() != g.strip() and b.strip() == g.strip()
                    for a, b, g in zip(v1p, cp, gts))
        regr = sum(a.strip() == g.strip() and b.strip() != g.strip()
                   for a, b, g in zip(v1p, cp, gts))
        v1pct = 100.0 * v1e / n if n else 0.0
        cpct = 100.0 * ce / n if n else 0.0
        groups[label] = {
            "n": n, "v1ExactPct": v1pct, "combinedExactPct": cpct,
            "deltaPp_vs_v1": cpct - v1pct, "gains": gains,
            "regressions": regr, "netChange": gains - regr,
        }
        print("%s%9d%10.1f%%%10.1f%%%+11.1f%+8d%8d%+8d"
              % (label.ljust(12), n, v1pct, cpct, cpct - v1pct,
                 gains, -regr, gains - regr))

    out = os.path.join(HERE, "finetune", "COMPARE_COMBINED_VS_V1.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump({"base": "itemname_V1", "ft": "combined_260724_1440",
                   "sameCropSet": "current test split (combined build)",
                   "groups": groups}, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    print("\n[wrote] %s" % out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
