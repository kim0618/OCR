"""Phase 1 gate — INGEST checker.

Asserts:
  - manifest builds with exactly 6 active samples + 2.pdf excluded, no orphans/invalid
  - gt_loader loads all 6 active GT files (6/6) under the contract
  - loaded shape matches contract: 12 common + exactly 1 per-sample, row counts §3.3,
    rows carry only value keys (no review-meta leaked)

Run:  python eval/phase1_check.py   (exit 0 = GATE PASS)
"""

from __future__ import annotations

import sys

import contract as C
from build_manifest import build_manifest
from gt_loader import GTLoadError, load_gt


def main() -> int:
    problems: list[str] = []

    # --- manifest ---
    manifest = build_manifest()
    samples = manifest["samples"]
    by_status: dict[str, list[str]] = {}
    for s in samples:
        by_status.setdefault(s["status"], []).append(s["sourceFile"])

    active = sorted(by_status.get("active", []))
    if set(active) != C.EXPECTED_ACTIVE_SOURCES:
        problems.append(
            f"active sources {active} != expected {sorted(C.EXPECTED_ACTIVE_SOURCES)}"
        )
    for bad in ("pending_gt", "gt_orphan", "gt_invalid"):
        if by_status.get(bad):
            problems.append(f"unexpected {bad}: {by_status[bad]}")
    if by_status.get("excluded") != ["2.pdf"]:
        problems.append(f"excluded != ['2.pdf']: {by_status.get('excluded')}")

    # --- loader 6/6 ---
    loaded_ok = 0
    for s in samples:
        if s["status"] != "active":
            continue
        gt_path = __import__("os").path.join(C.HERE, s["gt"])
        try:
            g = load_gt(gt_path)
        except GTLoadError as exc:
            problems.append(f"load {s['sourceFile']}: {exc}")
            continue

        fc = g["_meta"]["fieldCount"]
        # ➑➓ no hardcoded 13: rich = COMMON_12 + exactly one per-sample field.
        expected_fc = len(C.COMMON_12) + 1
        if g["profile"] == "rich" and fc != expected_fc:
            problems.append(f"{s['sourceFile']}: fieldCount {fc} != {expected_fc}")
        if g["perSampleField"] not in C.PER_SAMPLE:
            problems.append(f"{s['sourceFile']}: bad perSampleField {g['perSampleField']}")
        exp = C.EXPECTED_ROWS.get(s["sourceFile"])
        if exp is not None and g["_meta"]["rowCount"] != exp:
            problems.append(f"{s['sourceFile']}: rowCount {g['_meta']['rowCount']} != {exp}")
        # no review-meta leaked into value rows
        leaked = {
            k for r in g["tableRows"] for k in r
            if k in C.ROW_META_KEYS or k not in C.ROW_VALUE_KEYS
        }
        if leaked:
            problems.append(f"{s['sourceFile']}: non-value keys leaked into rows: {sorted(leaked)}")
        loaded_ok += 1

    # --- report ---
    print(f"manifest counts: {manifest['counts']}")
    print(f"active: {active}")
    print(f"loader: {loaded_ok}/{len(C.EXPECTED_ACTIVE_SOURCES)} loaded\n")

    if problems:
        print("GATE FAIL")
        for p in problems:
            print(f"  - {p}")
        return 1
    if loaded_ok != 6:
        print(f"GATE FAIL - loaded {loaded_ok}/6")
        return 1
    print("GATE PASS - manifest 6 active + 2.pdf excluded, loader 6/6")
    return 0


if __name__ == "__main__":
    sys.exit(main())
