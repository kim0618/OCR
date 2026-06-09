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
from gt_loader import load_gt


def _latest_run() -> str | None:
    runs = [p for p in glob.glob(os.path.join(C.RUNS_DIR, "*")) if os.path.isdir(p)]
    return sorted(runs)[-1] if runs else None


def compare_run(ts: str | None = None) -> dict[str, Any]:
    run_dir = os.path.join(C.RUNS_DIR, ts) if ts else _latest_run()
    if not run_dir or not os.path.isdir(run_dir):
        raise FileNotFoundError(f"run dir not found: {run_dir}")
    samples_dir = os.path.join(run_dir, "samples")
    compare_dir = os.path.join(run_dir, "compare")
    os.makedirs(compare_dir, exist_ok=True)

    manifest = build_manifest()
    actives = [s for s in manifest["samples"] if s["status"] == "active"]

    rows_summary: list[dict[str, Any]] = []
    for s in actives:
        src = s["sourceFile"]
        gt = load_gt(os.path.normpath(os.path.join(C.HERE, s["gt"])))
        res_path = os.path.join(samples_dir, src + ".json")
        result = json.load(open(res_path, encoding="utf-8"))
        ext_df = result.get("documentFields") or {}

        fcmp = compare_fields(gt, ext_df)
        tcmp = compare_table(gt["tableRows"], ext_df.get("tableRows") or [])
        tags = tag_sample(fcmp, tcmp)

        out = {
            "sourceFile": src,
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
    args = ap.parse_args()
    compare_run(args.ts)
