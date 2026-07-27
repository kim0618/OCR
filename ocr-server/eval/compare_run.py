"""compare_run — compare one run's results against GT for all active samples.

Ties gt_loader + run_batch results through compare_fields / compare_table /
buckets, writes per-sample comparisons to runs/<ts>/compare/ and a summary.

Measurement-only. CLI:
    python eval/compare_run.py [--ts <run_ts>]   (default: latest run)
"""

from __future__ import annotations

import argparse
import glob
import json
import os
from typing import Any

import contract as C
from build_manifest import build_manifest
from compare_fields import compare_fields
from compare_table import compare_table
from buckets import tag_sample
from gt_loader import load_gt, load_gt_aggregate
import learndata_apply as LDA


_LEARN_SPECS = [
    ("itemCodeLearnA", os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "data", "invoice_war", "learndata_heldout.json",
    )),
    ("itemCodeLearnB", os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "data", "invoice_war", "learndata_full.json",
    )),
]


def _latest_run() -> str | None:
    runs = [p for p in glob.glob(os.path.join(C.RUNS_DIR, "*")) if os.path.isdir(p)]
    return sorted(runs)[-1] if runs else None


def compare_run(ts: str | None = None, testset: str = C.DEFAULT_TESTSET) -> dict[str, Any]:
    run_dir = os.path.join(C.RUNS_DIR, ts) if ts else C.latest_run(testset)
    if not run_dir or not os.path.isdir(run_dir):
        raise FileNotFoundError(f"run dir not found: {run_dir}")
    samples_dir = os.path.join(run_dir, "samples")
    compare_dir = os.path.join(run_dir, "compare")
    os.makedirs(compare_dir, exist_ok=True)

    manifest = build_manifest(testset)
    kind = manifest["kind"]
    # active (live) and canned (recorded) samples are both compared.
    runnable = [s for s in manifest["samples"] if s["status"] in ("active", "canned")]

    # War/ETL thin testset: ONE aggregate GT file, indexed by gtKey. Load it once
    # here instead of a per-image load_gt (which assumes one file per sample).
    agg = None
    if manifest.get("gtAggregate"):
        agg = load_gt_aggregate(os.path.normpath(os.path.join(C.HERE, manifest["gtAggregate"])), profile=kind)

    # Apply the same LearnData A/B measurement columns used by snapshot replay.
    # This is measurement-only: values are injected into the loaded result/GT
    # copies immediately before compare_table and never written back to samples.
    learn_luts = []
    master_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "data", "invoice_war", "master_dict.json",
    )
    master_index = (
        LDA.load_master_index(master_path) if os.path.isfile(master_path) else None
    )
    for out_key, path in _LEARN_SPECS:
        if os.path.isfile(path):
            learn_luts.append((out_key, LDA.load_dist(path)))

    rows_summary: list[dict[str, Any]] = []
    for s in runnable:
        src = s["sourceFile"]
        gt = agg[s["gtKey"]] if agg is not None else load_gt(os.path.normpath(os.path.join(C.HERE, s["gt"])), profile=kind)
        res_path = os.path.join(samples_dir, src + ".json")
        result = json.load(open(res_path, encoding="utf-8"))
        ext_df = result.get("documentFields") or {}

        for out_key, dist in learn_luts:
            LDA.apply_to_rows(
                ext_df.get("tableRows"), gt.get("tableRows"), dist, out_key,
                master_index=master_index,
                name_out_key=out_key.replace("itemCode", "itemName"),
            )

        fcmp = compare_fields(gt, ext_df)
        tcmp = compare_table(gt["tableRows"], ext_df.get("tableRows") or [])
        tags = tag_sample(fcmp, tcmp, preprocess=result.get("preprocess"))

        out = {
            "sourceFile": src,
            "profile": gt["profile"],
            "extractionPath": result.get("extractionPath"),
            "pageCount": result.get("pageCount"),
            "multiPage": result.get("multiPage"),
            "fields": fcmp,
            "table": tcmp,
            "buckets": tags,
        }
        with open(os.path.join(compare_dir, src + ".json"), "w", encoding="utf-8") as fh:
            json.dump(out, fh, ensure_ascii=False, indent=2)
            fh.write("\n")

        rows_summary.append({
            "sourceFile": src,
            "path": result.get("extractionPath"),
            "fieldAcc": fcmp["fieldAccuracy"],
            "fieldScored": fcmp["counts"]["scored"],
            "fieldMatch": fcmp["counts"]["match"],
            "fieldMiss": fcmp["counts"]["ext_missing"],
            "fieldMismatch": fcmp["counts"]["mismatch"],
            "cellAcc": tcmp["cellAccuracy"],
            "rowCountMatch": tcmp["rowCountMatch"],
            "rowsGt": tcmp["rowCountGt"],
            "rowsExt": tcmp["rowCountExt"],
            "buckets": tags["bucketTally"],
        })

    summary = {
        "schemaVersion": "eval-compare.v1",
        "runTs": os.path.basename(run_dir),
        "testset": testset,
        "kind": kind,
        "samples": rows_summary,
    }
    with open(os.path.join(run_dir, "compare_summary.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=2)
        fh.write("\n")

    print(f"run: {os.path.basename(run_dir)}  ->  compare/ + compare_summary.json")
    hdr = f"{'sample':<8} {'path':<8} {'fieldAcc':>8} {'F m/s':>7} {'cellAcc':>8} {'rows g/e':>9}  buckets"
    print(hdr)
    print("-" * len(hdr))
    for r in rows_summary:
        fa = "n/a" if r["fieldAcc"] is None else f"{r['fieldAcc']*100:5.1f}%"
        ca = "n/a" if r["cellAcc"] is None else f"{r['cellAcc']*100:5.1f}%"
        bt = r["buckets"]
        bstr = " ".join(f"{k[:4]}={v}" for k, v in bt.items() if v)
        print(
            f"{r['sourceFile']:<8} {str(r['path']):<8} {fa:>8} "
            f"{r['fieldMatch']:>2}/{r['fieldScored']:<3} {ca:>8} "
            f"{r['rowsGt']:>3}/{r['rowsExt']:<3}{'' if r['rowCountMatch'] else '*'}  {bstr}"
        )
    return {"runDir": run_dir, "summary": summary}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--ts", default=None)
    ap.add_argument("--testset", default=C.DEFAULT_TESTSET)
    args = ap.parse_args()
    compare_run(args.ts, args.testset)
