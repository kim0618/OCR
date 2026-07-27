"""Score dominant-LearnData override thresholds from existing compare sidecars."""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from extractors.master_match import get_matcher, strip_master_annotations  # noqa: E402
from normalize import normalize_cell  # noqa: E402


def score(compare_dir: str) -> dict:
    matcher = get_matcher()
    if matcher is None:
        raise RuntimeError("Master matcher unavailable")
    thresholds = [
        (5, 0.80), (5, 0.90), (5, 0.95),
        (10, 0.80), (10, 0.90), (10, 0.95),
    ]
    stats = {
        f"count{count}_dom{int(dom * 100)}": {
            "itemNameMaster": Counter(), "itemCode": Counter()
        }
        for count, dom in thresholds
    }
    for filename in os.listdir(compare_dir):
        if not filename.endswith(".json"):
            continue
        with open(os.path.join(compare_dir, filename), encoding="utf-8") as fh:
            doc = json.load(fh)
        for row in (doc.get("table") or {}).get("rows") or []:
            cells = row.get("cells") or {}

            def ext(key: str):
                return (cells.get(key) or {}).get("ext")

            reading = str(ext("itemName") or "").strip()
            counts = matcher._learn.get(reading)
            if not counts:
                continue
            total = sum(counts.values())
            code = matcher.resolve_learndata_code(
                reading, spec=ext("spec"), price=ext("unitPrice"),
                quantity=ext("quantity"), amount=ext("amount"),
            )
            idx = matcher._cd2i.get(code or "")
            if idx is None:
                continue
            dominance = counts.get(code, 0) / total
            proposed = {
                "itemCode": code,
                "itemNameMaster": strip_master_annotations(matcher._nms[idx]),
            }
            for min_count, min_dom in thresholds:
                if total < min_count or dominance < min_dom:
                    continue
                label = f"count{min_count}_dom{int(min_dom * 100)}"
                for key in ("itemNameMaster", "itemCode"):
                    cell = cells.get(key) or {}
                    before_ok = cell.get("status") == "match"
                    after_ok = (
                        normalize_cell(key, proposed[key])
                        == str(cell.get("gtNorm") or "")
                    )
                    if (
                        normalize_cell(key, proposed[key])
                        == str(cell.get("extNorm") or "")
                    ):
                        continue
                    bucket = (
                        "gain" if after_ok and not before_ok
                        else "regress" if before_ok and not after_ok
                        else "neutral"
                    )
                    stats[label][key][bucket] += 1
    return {
        label: {
            key: {
                **counter,
                "net": counter["gain"] - counter["regress"],
                "changed": sum(counter.values()),
            }
            for key, counter in columns.items()
        }
        for label, columns in stats.items()
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--compare-dir", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    result = score(args.compare_dir)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
