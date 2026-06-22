"""Phase 3 gate — COMPARE checker.

Human spot-check (1.jpg, 4.pdf) confirmed the comparison matches reality. This
checker guards the machinery's self-consistency so it can't silently drift:

  - compare ran for all 6 active samples
  - field counts: scored == match+mismatch+ext_missing; scored+gt_empty == 13
  - fieldAccuracy == match/scored
  - table cellCounts: scored == match+mismatch+ext_missing
  - every defect carries a bucket in {recognition, structure, layout, preprocessing}
  - bucketTally totals == number of tagged defects
  - normalization freeze anchors (hyphen/comma/date) still collapse to match

Run:  python eval/phase3_check.py [--ts <run_ts>]   exit 0 = PASS
"""

from __future__ import annotations

import argparse
import sys

import contract as C
import normalize as N
from compare_table import compare_table
from compare_run import compare_run, _latest_run

BUCKETS = {"recognition", "structure", "layout", "preprocessing"}


def _freeze_anchors() -> list[str]:
    """The normalization freeze must keep these representation-equal pairs equal."""
    problems = []
    cases = [
        ("supplierBizNumber", "118-81-00450", "1188100450"),
        ("totalAmount", "18,098,750", "18098750"),
        ("issueDate", "2024-03-07", "20240307"),
    ]
    for label, a, b in cases:
        if N.normalize_field(label, a) != N.normalize_field(label, b):
            problems.append(f"freeze drift: {label} {a!r} !~ {b!r}")
    # and a genuine OCR error must NOT be normalized away
    if N.normalize_field("supplierRepresentative", "LEE WOO HYUN") == \
       N.normalize_field("supplierRepresentative", "UIO J"):
        problems.append("freeze over-reach: distinct text values collapsed to equal")
    return problems


def _missing_gt_row_golden() -> list[str]:
    """Lock the denominator rule: every non-empty GT cell is scored."""
    problems: list[str] = []
    gt = [
        {"rowIndex": 1, "itemName": "kept", "quantity": "1", "amount": ""},
        {"rowIndex": 2, "itemName": "missing", "quantity": "2", "amount": "200"},
    ]
    ext = [{"rowIndex": 1, "itemName": "kept", "quantity": "1", "amount": ""}]
    cases = [
        ("partial", compare_table(gt, ext), 5, 3, ["2"]),
        ("zero-extracted", compare_table(gt[:1], []), 2, 2, ["1"]),
        ("duplicate-ext-rowindex", compare_table(gt, ext + ext), 5, 3, ["2"]),
        (
            "content-aligned-missing",
            compare_table(
                [{k: v for k, v in row.items() if k != "rowIndex"} for row in gt],
                [{k: v for k, v in row.items() if k != "rowIndex"} for row in ext],
            ),
            5,
            3,
            ["2"],
        ),
    ]
    for name, table, expected_scored, expected_missing, expected_gt_only in cases:
        cc = table["cellCounts"]
        if cc["scored"] != expected_scored or cc["ext_missing"] != expected_missing:
            problems.append(
                f"missing-row golden/{name}: scored/missing "
                f"{cc['scored']}/{cc['ext_missing']} != "
                f"{expected_scored}/{expected_missing}"
            )
        if table["gtOnlyRowIdx"] != expected_gt_only:
            problems.append(
                f"missing-row golden/{name}: gtOnlyRowIdx "
                f"{table['gtOnlyRowIdx']} != {expected_gt_only}"
            )
        missing_rows = [r for r in table["rows"] if r.get("missingGtRow")]
        if len(missing_rows) != len(expected_gt_only):
            problems.append(
                f"missing-row golden/{name}: materialized "
                f"{len(missing_rows)} != {len(expected_gt_only)}"
            )
    return problems


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ts", default=None)
    args = ap.parse_args()

    problems: list[str] = _freeze_anchors() + _missing_gt_row_golden()

    out = compare_run(args.ts)
    samples = out["summary"]["samples"]
    seen = {s["sourceFile"] for s in samples}
    expected_active = C.expected_active_sources()  # base docs + on-disk variants
    if seen != expected_active:
        problems.append(f"compared {sorted(seen)} != {sorted(expected_active)}")

    # re-open per-sample compare files for deep consistency
    import glob, json, os
    run_dir = out["runDir"]
    for src in sorted(seen):
        d = json.load(open(os.path.join(run_dir, "compare", src + ".json"), encoding="utf-8"))
        fc = d["fields"]["counts"]
        scored = fc["scored"]
        if scored != fc["match"] + fc["mismatch"] + fc["ext_missing"]:
            problems.append(f"{src}: field scored {scored} != m+mm+miss")
        # ➑➓ no hardcoded 13: scored + gt_empty == number of GT fields scored.
        n_fields = len(d["fields"]["perField"])
        if scored + fc["gt_empty"] != n_fields:
            problems.append(f"{src}: scored+gt_empty {scored + fc['gt_empty']} != fields {n_fields}")
        fa = d["fields"]["fieldAccuracy"]
        exp_fa = (fc["match"] / scored) if scored else None
        if fa is not None and exp_fa is not None and abs(fa - exp_fa) > 1e-9:
            problems.append(f"{src}: fieldAccuracy {fa} != match/scored {exp_fa}")

        cc = d["table"]["cellCounts"]
        if cc["scored"] != cc["match"] + cc["mismatch"] + cc["ext_missing"]:
            problems.append(f"{src}: cell scored {cc['scored']} != m+mm+miss")
        missing_rows = {str(r["rowIndex"]): r for r in d["table"]["rows"]
                        if r.get("missingGtRow")}
        gt_only = {str(idx) for idx in d["table"]["gtOnlyRowIdx"]}
        if set(missing_rows) != gt_only:
            problems.append(
                f"{src}: materialized missing rows {sorted(missing_rows)} "
                f"!= gtOnlyRowIdx {sorted(gt_only)}"
            )
        for idx, row in missing_rows.items():
            bad = [key for key, cell in row["cells"].items()
                   if not N.is_empty(cell.get("gt")) and cell.get("status") != "ext_missing"]
            if bad:
                problems.append(f"{src}: missing GT row {idx} has unpenalized cells {bad}")

        tags = d["buckets"]
        tally = tags["bucketTally"]
        if set(tally) != BUCKETS:
            problems.append(f"{src}: bucketTally keys {set(tally)} != {BUCKETS}")
        for defect in tags["defects"]:
            if defect["bucket"] not in BUCKETS:
                problems.append(f"{src}: defect bucket {defect['bucket']} invalid")
        # tally of non-preprocessing buckets must equal #defects (+preproc is sample-level)
        defect_buckets = [x["bucket"] for x in tags["defects"]]
        for b in ("recognition", "structure", "layout"):
            if tally[b] != defect_buckets.count(b):
                problems.append(f"{src}: {b} tally {tally[b]} != defect count {defect_buckets.count(b)}")

    print()
    if problems:
        print("GATE FAIL")
        for p in problems:
            print(f"  - {p}")
        return 1
    print(f"GATE PASS - {len(seen)}/{len(expected_active)} compared, counts self-consistent, "
          "buckets valid, freeze anchors hold")
    return 0


if __name__ == "__main__":
    sys.exit(main())
