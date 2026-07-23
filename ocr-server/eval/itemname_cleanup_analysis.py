"""Simulate conservative itemName tail cleanups on completed replay sidecars."""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
from collections import Counter
from collections.abc import Callable

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import contract as C  # noqa: E402
import normalize as N  # noqa: E402


_PAGE_FRACTION = re.compile(
    r"(?:\s+|(?<=\)))(?:1\s*/\s*\d+|/{1,2}\s*\d+)\s*$",
    re.IGNORECASE,
)
_PAGE_ONE_OF_N = re.compile(r"\s+1\s*/\s*[1-9]\d?\s*$", re.IGNORECASE)
_DOUBLE_SLASH_SINGLE = re.compile(r"\s*//\s*[1-9]\s*$", re.IGNORECASE)
_TRAILING_DATE = re.compile(
    r"\s+\d{4}[./-]\d{1,2}[./-]\d{1,2}\s*$",
    re.IGNORECASE,
)
_TRAILING_COUNTER_2_3 = re.compile(r"\s+\d{2,3}\s*$")
_TRAILING_COUNTER_111_119 = re.compile(r"\s+11[1-9]\s*$")
_TRAILING_COUNTER_111_119_SAFE = re.compile(r"(?<=[^/\s])\s+11[1-9]\s*$")


def _sub(pattern: re.Pattern[str]) -> Callable[[str], str]:
    return lambda value: pattern.sub("", value).rstrip()


CANDIDATES: dict[str, Callable[[str], str]] = {
    "page_fraction": _sub(_PAGE_FRACTION),
    "page_one_of_n": _sub(_PAGE_ONE_OF_N),
    "double_slash_single": _sub(_DOUBLE_SLASH_SINGLE),
    "trailing_date": _sub(_TRAILING_DATE),
    "counter_2_3": _sub(_TRAILING_COUNTER_2_3),
    "counter_111_119": _sub(_TRAILING_COUNTER_111_119),
    "counter_111_119_safe": _sub(_TRAILING_COUNTER_111_119_SAFE),
}


def analyze(compare_dir: str) -> dict:
    stats = {
        name: Counter(changed=0, gain=0, regress=0, neutral=0)
        for name in CANDIDATES
    }
    examples: dict[str, dict[str, list[dict]]] = {
        name: {"gain": [], "regress": []} for name in CANDIDATES
    }
    sources: dict[str, set[str]] = {name: set() for name in CANDIDATES}

    for path in glob.glob(os.path.join(compare_dir, "*.json")):
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
        source = doc.get("sourceFile") or os.path.basename(path)[:-5]
        for row in doc.get("table", {}).get("rows") or []:
            cell = (row.get("cells") or {}).get("itemName") or {}
            gt_norm = str(cell.get("gtNorm") or "")
            ext = str(cell.get("ext") or "")
            if not gt_norm or not ext:
                continue
            before_ok = cell.get("status") == "match"
            for name, transform in CANDIDATES.items():
                after = transform(ext)
                if after == ext:
                    continue
                stats[name]["changed"] += 1
                sources[name].add(source)
                after_ok = N.norm_name(after) == gt_norm
                if after_ok and not before_ok:
                    outcome = "gain"
                elif before_ok and not after_ok:
                    outcome = "regress"
                else:
                    outcome = "neutral"
                stats[name][outcome] += 1
                if outcome in ("gain", "regress") and len(examples[name][outcome]) < 20:
                    examples[name][outcome].append({
                        "sourceFile": source,
                        "rowIndex": row.get("rowIndex"),
                        "gt": cell.get("gt"),
                        "before": ext,
                        "after": after,
                    })

    return {
        name: {
            **dict(counts),
            "net": counts["gain"] - counts["regress"],
            "documents": len(sources[name]),
            "sources": sorted(sources[name]),
            "examples": examples[name],
        }
        for name, counts in stats.items()
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="067_20260720_175949")
    ap.add_argument("--compare-dir", default="replay_compare")
    ap.add_argument("--json-out", default=None)
    ap.add_argument("--targets-out", default=None)
    ap.add_argument("--candidate", choices=tuple(CANDIDATES), default="page_one_of_n")
    args = ap.parse_args()
    result = analyze(os.path.join(C.RUNS_DIR, args.run, args.compare_dir))
    summary = {
        name: {key: value for key, value in row.items()
               if key not in ("sources", "examples")}
        for name, row in result.items()
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as fh:
            json.dump(result, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
    if args.targets_out:
        with open(args.targets_out, "w", encoding="utf-8") as fh:
            for source in result[args.candidate]["sources"]:
                fh.write(source + "\n")
        print(
            f"[targets] {args.targets_out}: "
            f"{len(result[args.candidate]['sources']):,} documents"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
