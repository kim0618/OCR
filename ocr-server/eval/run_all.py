"""run_all — one command: manifest -> run_batch -> compare -> metrics -> report -> checker.

This is the reproducibility entry point (plan Phase 5 gate).

    python eval/run_all.py                      # fresh: re-OCR all 6 (needs live :9099, ~10min)
    python eval/run_all.py --reuse <run_ts>     # reuse an existing run's OCR results (fast)
    python eval/run_all.py --server ... --workers N

Prints MVP GO/FAIL based on the consolidated checker.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys

import contract as C
from build_manifest import write_manifest
from compare_run import compare_run
from metrics import compute_metrics
from report import render_report
from run_batch import run_batch


def run_all(reuse: str | None, server: str, workers: int) -> int:
    print("== [1/6] manifest ==")
    write_manifest()

    if reuse:
        ts = reuse
        run_dir = os.path.join(C.RUNS_DIR, ts)
        if not os.path.isdir(os.path.join(run_dir, "samples")):
            print(f"!! reuse run not found: {run_dir}")
            return 1
        print(f"== [2/6] run_batch SKIPPED (reuse {ts}) ==")
    else:
        print("== [2/6] run_batch (live OCR) ==")
        out = run_batch(server=server, workers=workers)
        ts = out["ts"]

    print("== [3/6] compare ==")
    compare_run(ts)
    print("== [4/6] metrics ==")
    m = compute_metrics(os.path.join(C.RUNS_DIR, ts))
    print(f"   field acc {m['overall']['field']['accuracy']}  cell acc {m['overall']['cell']['accuracy']}")
    print("== [5/6] report ==")
    rp = render_report(os.path.join(C.RUNS_DIR, ts))
    print(f"   {rp}")

    print("== [6/6] checker ==")
    p = subprocess.run([sys.executable, os.path.join(C.HERE, "checker.py"), "--ts", ts])
    print()
    if p.returncode == 0:
        print(f"MVP GO - one-command pipeline reproduced run {ts}, checker PASS")
        return 0
    print(f"MVP FAIL - checker failed for run {ts}")
    return 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--reuse", default=None, help="reuse an existing run_ts (skip live OCR)")
    ap.add_argument("--server", default="http://127.0.0.1:9099")
    ap.add_argument("--workers", type=int, default=3)
    args = ap.parse_args()
    sys.exit(run_all(args.reuse, args.server, args.workers))
