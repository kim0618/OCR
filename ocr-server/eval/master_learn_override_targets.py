"""Select documents changed by the experimental dominant-LearnData override."""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from extractors.master_match import get_matcher  # noqa: E402


def select(compare_dir: str) -> tuple[list[str], int]:
    matcher = get_matcher()
    if matcher is None:
        raise RuntimeError("Master matcher is unavailable")
    sources: set[str] = set()
    changed_rows = 0
    for filename in os.listdir(compare_dir):
        if not filename.endswith(".json"):
            continue
        path = os.path.join(compare_dir, filename)
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
        changed = False
        for scored_row in (doc.get("table") or {}).get("rows") or []:
            cells = scored_row.get("cells") or {}

            def ext(key: str):
                return (cells.get(key) or {}).get("ext")

            match = matcher.learndata_dominant_match(
                ext("itemName"), spec=ext("spec"), price=ext("unitPrice"),
                quantity=ext("quantity"), amount=ext("amount"),
                min_count=5, min_dominance=0.80,
            )
            if match is None:
                continue
            if (
                str(ext("itemCode") or "") == match["itemCode"]
                and str(ext("itemNameMaster") or "") == match["itemNameMaster"]
            ):
                continue
            changed_rows += 1
            changed = True
        if changed:
            sources.add(str(doc.get("sourceFile") or filename[:-5]))
    return sorted(sources), changed_rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--compare-dir", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    sources, changed_rows = select(args.compare_dir)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        for source in sources:
            fh.write(source + "\n")
    print(f"changed rows={changed_rows:,}; documents={len(sources):,}; {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
