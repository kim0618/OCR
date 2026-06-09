"""Phase 2 gate — RUNNER checker.

Validates a run under runs/<ts>/:
  - run_meta summary: ok == activeCount (6), error == 0 (isolation held)
  - each active sample has a result with status ok, http 200, documentFields object,
    extractionPath in {free, fallback}, pageCount recorded
  - free + fallback == 6 (every sample classified)
  - no U+FFFD replacement chars in any saved result (UTF-8 round-trip intact)
  - multiPage samples are flagged but NOT failed (page-0 policy)

Run:  python eval/phase2_check.py [--ts <run_ts>]   (default: latest)  exit 0 = PASS
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys

import contract as C


def _latest_run() -> str | None:
    runs = [p for p in glob.glob(os.path.join(C.RUNS_DIR, "*")) if os.path.isdir(p)]
    return sorted(runs)[-1] if runs else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ts", default=None)
    args = ap.parse_args()

    run_dir = os.path.join(C.RUNS_DIR, args.ts) if args.ts else _latest_run()
    if not run_dir or not os.path.isdir(run_dir):
        print(f"GATE FAIL - run dir not found ({run_dir})")
        return 1

    problems: list[str] = []
    meta_path = os.path.join(run_dir, "run_meta.json")
    try:
        meta = json.load(open(meta_path, encoding="utf-8"))
    except Exception as exc:
        print(f"GATE FAIL - cannot read run_meta: {exc}")
        return 1

    active_count = meta.get("activeCount")
    summ = meta.get("summary", {})
    if active_count != len(C.EXPECTED_ACTIVE_SOURCES):
        problems.append(f"activeCount {active_count} != {len(C.EXPECTED_ACTIVE_SOURCES)}")
    if summ.get("ok") != active_count:
        problems.append(f"summary.ok {summ.get('ok')} != activeCount {active_count}")
    if summ.get("error") != 0:
        problems.append(f"summary.error {summ.get('error')} != 0")
    if (summ.get("free", 0) + summ.get("fallback", 0)) != active_count:
        problems.append(
            f"free+fallback {summ.get('free')}+{summ.get('fallback')} != {active_count}"
        )

    samples_dir = os.path.join(run_dir, "samples")
    for src in sorted(C.EXPECTED_ACTIVE_SOURCES):
        p = os.path.join(samples_dir, src + ".json")
        if not os.path.isfile(p):
            problems.append(f"{src}: result file missing")
            continue
        raw = open(p, encoding="utf-8").read()
        if "�" in raw:
            problems.append(f"{src}: U+FFFD replacement char in saved result (encoding loss)")
        rec = json.loads(raw)
        if rec.get("status") != "ok":
            problems.append(f"{src}: status={rec.get('status')} err={rec.get('error')}")
        if rec.get("httpStatus") != 200:
            problems.append(f"{src}: httpStatus={rec.get('httpStatus')}")
        if not isinstance(rec.get("documentFields"), dict):
            problems.append(f"{src}: documentFields not an object")
        if rec.get("extractionPath") not in ("free", "fallback"):
            problems.append(f"{src}: extractionPath={rec.get('extractionPath')}")
        if "pageCount" not in rec:
            problems.append(f"{src}: pageCount not recorded")

    print(f"run: {os.path.basename(run_dir)}")
    print(f"summary: {summ}")
    if summ.get("multiPage"):
        print(f"multiPage (flagged, page-0 policy, not failed): {summ['multiPage']}")
    print()
    if problems:
        print("GATE FAIL")
        for p in problems:
            print(f"  - {p}")
        return 1
    print(f"GATE PASS - {active_count}/{active_count} ok, 0 errors, all classified, UTF-8 intact")
    return 0


if __name__ == "__main__":
    sys.exit(main())
