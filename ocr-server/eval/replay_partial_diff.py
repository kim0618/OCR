"""Compare a partial replay with the same files in an existing full replay.

This intentionally does not merge partial results into the official replay.
It is a fast regression gate used between code edits; a final full replay is
still required before accepting a release-level accuracy number.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import contract as C  # noqa: E402


def _load_dir(path: str) -> dict[str, dict]:
    rows: dict[str, dict] = {}
    if not os.path.isdir(path):
        raise FileNotFoundError(path)
    for name in os.listdir(path):
        if not name.endswith(".json"):
            continue
        with open(os.path.join(path, name), encoding="utf-8") as fh:
            doc = json.load(fh)
        source = doc.get("sourceFile") or name[:-5]
        rows[source] = doc
    return rows


def _add(store: dict[str, list[int]], key: str, status: str | None) -> None:
    if status not in {"match", "mismatch", "ext_missing"}:
        return
    store[key][1] += 1
    if status == "match":
        store[key][0] += 1


def _counts(doc: dict) -> dict[str, list[int]]:
    out: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for key, cell in (doc.get("fields", {}).get("perField") or {}).items():
        _add(out, f"field:{key}", cell.get("status"))
        _add(out, "FIELD TOTAL", cell.get("status"))
    for row in doc.get("table", {}).get("rows") or []:
        cells = row.get("cells") or {}
        for key, cell in cells.items():
            _add(out, f"cell:{key}", cell.get("status"))
            if key not in C.MEASUREMENT_KEYS:
                _add(out, "CELL TOTAL", cell.get("status"))
    return out


def _merge(docs: list[dict]) -> dict[str, list[int]]:
    out: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for doc in docs:
        for key, (match, scored) in _counts(doc).items():
            out[key][0] += match
            out[key][1] += scored
    return out


def _pct(pair: list[int]) -> float | None:
    return pair[0] * 100.0 / pair[1] if pair[1] else None


def _fmt(pair: list[int]) -> str:
    pct = _pct(pair)
    return "-" if pct is None else f"{pct:7.3f}% ({pair[0]:,}/{pair[1]:,})"


def compare(baseline_dir: str, candidate_dir: str) -> int:
    baseline = _load_dir(baseline_dir)
    candidate = _load_dir(candidate_dir)
    sources = sorted(candidate)
    missing = [src for src in sources if src not in baseline]
    if missing:
        print(f"baseline is missing {len(missing)} candidate source(s)")
        for src in missing[:20]:
            print(f"  {src}")
        return 2
    if not sources:
        print("candidate directory has no sidecars")
        return 2

    before = _merge([baseline[src] for src in sources])
    after = _merge([candidate[src] for src in sources])
    keys = sorted(set(before) | set(after))
    priority = {"FIELD TOTAL": 0, "CELL TOTAL": 1, "cell:itemName": 2, "cell:itemCode": 3}
    keys.sort(key=lambda key: (priority.get(key, 10), key))

    print(f"partial replay diff: {len(sources):,} same documents")
    print(f"baseline : {baseline_dir}")
    print(f"candidate: {candidate_dir}\n")
    print(f"{'metric':32} {'before':24} {'after':24} {'delta':>10}")
    print("-" * 96)
    for key in keys:
        b = before.get(key, [0, 0])
        a = after.get(key, [0, 0])
        bp, ap = _pct(b), _pct(a)
        delta = "-" if bp is None or ap is None else f"{ap - bp:+.3f}pp"
        important = key in priority or b != a
        if important:
            print(f"{key:32} {_fmt(b):24} {_fmt(a):24} {delta:>10}")
    print("\nPARTIAL ONLY: use this as a regression gate, not as the 9,001-document final score.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ts", default=None,
                    help="run dir under runs/ (default: latest study run)")
    ap.add_argument("--baseline-dir", default="replay_compare")
    ap.add_argument("--candidate-dir", required=True)
    ap.add_argument("--testset", default=C.DEFAULT_TESTSET)
    args = ap.parse_args()
    run_dir = os.path.join(C.RUNS_DIR, args.ts) if args.ts else C.latest_run(args.testset)
    if not run_dir:
        print("no run dir")
        return 2
    return compare(
        os.path.join(run_dir, args.baseline_dir),
        os.path.join(run_dir, args.candidate_dir),
    )


if __name__ == "__main__":
    raise SystemExit(main())
