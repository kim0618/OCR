"""Phase 4 gate — METRICS-REPORT checker.

Asserts metrics are self-consistent and the report renders:
  - overall field counts == sum of per-sample field counts (cross-foot)
  - per-field scored totals reconcile to overall
  - byPath (free+fallback) partitions sum to overall field scored/match
  - editedSplit partitions sum to overall field scored
  - every slice group's accuracy == match/scored
  - report.md exists, non-empty, has the hypothesis banner
  - one time-series row was written for this run

Run: python eval/phase4_check.py [--ts <run_ts>]   exit 0 = PASS
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sqlite3
import sys

import contract as C
from metrics import compute_metrics, TIMESERIES_DB
from report import render_report


def _sum_field_counts(run_dir):
    scored = match = 0
    for p in sorted(glob.glob(os.path.join(run_dir, "compare", "*.json"))):
        fc = json.load(open(p, encoding="utf-8"))["fields"]["counts"]
        scored += fc["scored"]
        match += fc["match"]
    return scored, match


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ts", default=None)
    args = ap.parse_args()
    run_dir = (os.path.join(C.RUNS_DIR, args.ts) if args.ts
               else sorted(p for p in glob.glob(os.path.join(C.RUNS_DIR, "*")) if os.path.isdir(p))[-1])

    problems: list[str] = []
    m = compute_metrics(run_dir)
    report_path = render_report(run_dir)

    # cross-foot overall vs per-sample
    s_scored, s_match = _sum_field_counts(run_dir)
    of = m["overall"]["field"]
    if of["scored"] != s_scored or of["match"] != s_match:
        problems.append(f"overall field {of['scored']}/{of['match']} != sum {s_scored}/{s_match}")

    # per-field reconciles to overall
    pf_scored = sum(v["scored"] for v in m["perField"].values())
    pf_match = sum(v["match"] for v in m["perField"].values())
    if pf_scored != of["scored"] or pf_match != of["match"]:
        problems.append(f"perField sum {pf_scored}/{pf_match} != overall {of['scored']}/{of['match']}")

    # byPath partitions sum to overall
    bp_scored = sum(v["field"]["scored"] for v in m["byPath"].values())
    bp_match = sum(v["field"]["match"] for v in m["byPath"].values())
    if bp_scored != of["scored"] or bp_match != of["match"]:
        problems.append(f"byPath sum {bp_scored}/{bp_match} != overall {of['scored']}/{of['match']}")

    # editedSplit partitions sum to overall
    es_scored = sum(v["scored"] for v in m["editedSplit"].values())
    if es_scored != of["scored"]:
        problems.append(f"editedSplit scored {es_scored} != overall {of['scored']}")

    # slice accuracy internal consistency
    for sname, groups in m["slices"].items():
        for g, v in groups.items():
            exp = (v["match"] / v["scored"]) if v["scored"] else None
            if v["accuracy"] is not None and exp is not None and abs(v["accuracy"] - exp) > 1e-9:
                problems.append(f"slice {sname}/{g}: acc {v['accuracy']} != {exp}")
    # extractionPath slice must equal byPath
    for p, v in m["byPath"].items():
        sl = m["slices"]["extractionPath"].get(p, {})
        if sl.get("scored") != v["field"]["scored"]:
            problems.append(f"slice extractionPath/{p} scored != byPath")

    # report sanity
    if not os.path.isfile(report_path):
        problems.append("report.md not written")
    else:
        txt = open(report_path, encoding="utf-8").read()
        if len(txt) < 200 or "가설" not in txt:
            problems.append("report.md missing hypothesis banner / too short")

    # time series row present
    con = sqlite3.connect(TIMESERIES_DB)
    try:
        row = con.execute("SELECT runTs, fieldAcc FROM runs WHERE runTs=?", (m["runTs"],)).fetchone()
    finally:
        con.close()
    if not row:
        problems.append("time-series row not appended for this run")

    print(f"run: {m['runTs']}  field acc {m['overall']['field']['accuracy']}  "
          f"cell acc {m['overall']['cell']['accuracy']}")
    print(f"report: {report_path}")
    print()
    if problems:
        print("GATE FAIL")
        for p in problems:
            print(f"  - {p}")
        return 1
    print("GATE PASS - metrics self-consistent, report rendered, time-series appended")
    return 0


if __name__ == "__main__":
    sys.exit(main())
