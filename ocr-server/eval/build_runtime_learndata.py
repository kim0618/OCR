"""Build the compact runtime LearnData distribution from a replay corpus.

The source event log is large because it keeps one row per observation. Runtime
matching needs only readings whose total count passes the noise gate and their
per-code counts.
"""
from __future__ import annotations

import argparse
import json
import os

import learndata_apply as LDA


def main() -> int:
    here = os.path.dirname(os.path.abspath(__file__))
    server = os.path.abspath(os.path.join(here, ".."))
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--source",
        default=os.path.join(here, "data", "invoice_war", "learndata_heldout.json"),
    )
    ap.add_argument(
        "--out", default=os.path.join(server, "learndata_runtime.json")
    )
    ap.add_argument("--min-count", type=int, default=3)
    args = ap.parse_args()

    source = json.load(open(args.source, encoding="utf-8"))
    dist = LDA.load_dist(args.source, args.min_count)
    payload = {
        "schemaVersion": "learndata-runtime.v1",
        "minCount": args.min_count,
        "builtFrom": source.get("builtFrom"),
        "excludeList": source.get("excludeList"),
        "readings": {
            # Preserve first-seen code order: it is the final deterministic
            # tie-break used by the evaluation resolver.
            reading: list(counter.items())
            for reading, counter in sorted(dist.items())
        },
    }
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, separators=(",", ":"))
        fh.write("\n")
    print(
        f"[written] {args.out} "
        f"({len(payload['readings']):,} readings, min_count>={args.min_count})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
