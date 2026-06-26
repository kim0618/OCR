"""table_align_diag — quantify the W1 table-measurement weakness (audit A3).

READ-ONLY diagnostic sidecar. The scored cell accuracy (compare_table.py) is
sensitive to ROW ALIGNMENT: when the aligner mis-pairs a GT row to the wrong
extracted row, EVERY value cell in that row turns mismatch, so one alignment
fault inflates the error like N cell faults ("explosion", ~3pp noise). The
checker's invariants stay intact; we do NOT touch the scored path. Instead we
re-load each sample's GT + extracted rows and MEASURE how much of the table
error is alignment noise vs genuine cell error.

Per sample we report:
  cellAcc(auto)              the accuracy the loop scored (compare_table align=auto)
  cellAcc(rowindex/content)  same rows under each alignment -> sensitivity = spread
  explosionRows              paired rows that are fully wrong (match==0, ext present)
  misalignedRows             explosion rows where a STRICTLY better ext pairing
                             exists (a real alignment fault, not cell faults)
  misalignedCells            scored cells trapped in misalignedRows  = the W1 noise

Aggregate alignmentNoisePct = misalignedCells / totalScored gives the headline
"X pp of table error is alignment, not recognition/parser".

    ../.venv/Scripts/python.exe eval/table_align_diag.py
    ../.venv/Scripts/python.exe eval/table_align_diag.py --ts 053_.../study
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import contract as C  # noqa: E402
import compare_table as CT  # noqa: E402  (reuse the SAME aligner + similarity)
from gt_loader import load_gt, load_gt_aggregate  # noqa: E402


def _cell_acc(res: dict) -> float | None:
    return res.get("cellAccuracy")


def _explosion_rows(res: dict) -> list[dict]:
    """Paired rows scored fully wrong: every scored cell mismatch, none missing
    purely because GT was empty. These are the alignment-fault suspects."""
    out = []
    for row in res["rows"]:
        if row.get("missingGtRow"):
            continue
        scored = match = mism = 0
        for cell in row["cells"].values():
            if cell["status"] == "gt_empty":
                continue
            scored += 1
            if cell["status"] == "match":
                match += 1
            elif cell["status"] == "mismatch":
                mism += 1
        # fully wrong AND the wrongness is mismatch (a competing value), not just
        # ext_missing (a blank) — a mis-paired row shows competing values.
        if scored >= 2 and match == 0 and mism >= 1:
            out.append(row)
    return out


def _better_pairing_exists(gt_row, paired_ext, ext_rows) -> bool:
    """Is there an extracted row that the content aligner would prefer over the
    one this GT row was paired with? If so, the row's all-mismatch is an
    alignment artifact, not N independent cell errors."""
    base = CT._row_similarity(gt_row, paired_ext) if paired_ext is not None else -1.0
    for e in ext_rows:
        if e is paired_ext:
            continue
        if CT._row_similarity(gt_row, e) > base + 1e-9:
            return True
    return False


def diagnose_sample(gt_rows: list[dict], ext_rows: list[dict]) -> dict[str, Any]:
    auto = CT.compare_table(gt_rows, ext_rows, align="auto")
    has_idx = bool(gt_rows) and all(CT._has_rowindex(r) for r in gt_rows)
    accs = {"auto": _cell_acc(auto)}
    for m in ("rowindex", "content"):
        if m == "rowindex" and not has_idx:
            accs[m] = None
            continue
        try:
            accs[m] = _cell_acc(CT.compare_table(gt_rows, ext_rows, align=m))
        except Exception:
            accs[m] = None

    # map auto's paired rows back to (gt_row, ext_row) so we can test re-pairing.
    # compare_table keeps gt/ext values per cell; rebuild the row dicts it paired.
    explosions = _explosion_rows(auto)
    misaligned = 0
    misaligned_cells = 0
    for row in explosions:
        gt_row = {k: cell["gt"] for k, cell in row["cells"].items()}
        ext_row = {k: cell["ext"] for k, cell in row["cells"].items()}
        scored = sum(1 for c in row["cells"].values() if c["status"] != "gt_empty")
        if _better_pairing_exists(gt_row, ext_row, ext_rows):
            misaligned += 1
            misaligned_cells += scored

    counts = auto["cellCounts"]
    spread = [a for a in (accs["rowindex"], accs["content"]) if a is not None]
    return {
        "alignMode": auto["alignMode"],
        "rowsGt": auto["rowCountGt"],
        "rowsExt": auto["rowCountExt"],
        "scored": counts["scored"],
        "match": counts["match"],
        "cellAcc": accs["auto"],
        "cellAccByMode": {"rowindex": accs["rowindex"], "content": accs["content"]},
        "alignSensitivity": (round(max(spread) - min(spread), 4) if len(spread) == 2 else None),
        "explosionRows": len(explosions),
        "misalignedRows": misaligned,
        "misalignedCells": misaligned_cells,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ts", default=None)
    ap.add_argument("--testset", default=C.DEFAULT_TESTSET)
    args = ap.parse_args()

    run_dir = os.path.join(C.RUNS_DIR, args.ts) if args.ts else C.latest_run(args.testset)
    if not run_dir or not os.path.isdir(run_dir):
        print(f"no run dir ({run_dir})"); return 2
    samples_dir = os.path.join(run_dir, "samples")
    if not os.path.isdir(samples_dir):
        print(f"no samples/ in {run_dir}"); return 2

    from build_manifest import build_manifest
    manifest = build_manifest(args.testset)
    kind = manifest["kind"]
    runnable = [s for s in manifest["samples"] if s["status"] in ("active", "canned")]

    # War/ETL thin: ONE aggregate GT indexed by gtKey (load once). Else per-image.
    agg = None
    if manifest.get("gtAggregate"):
        agg = load_gt_aggregate(os.path.normpath(os.path.join(C.HERE, manifest["gtAggregate"])), profile=kind)

    per_sample: list[dict] = []
    tot_scored = tot_match = tot_misaligned_cells = tot_explosion = tot_misaligned = 0
    for s in runnable:
        src = s["sourceFile"]
        rp = os.path.join(samples_dir, src + ".json")
        if not os.path.exists(rp):
            continue
        try:
            gt = agg[s["gtKey"]] if agg is not None else load_gt(
                os.path.normpath(os.path.join(C.HERE, s["gt"])), profile=kind)
        except Exception as e:
            print(f"  skip {src}: GT load failed ({e})")
            continue
        ext_df = (json.load(open(rp, encoding="utf-8")).get("documentFields") or {})
        d = diagnose_sample(gt["tableRows"], ext_df.get("tableRows") or [])
        d["src"] = src
        per_sample.append(d)
        tot_scored += d["scored"]; tot_match += d["match"]
        tot_misaligned_cells += d["misalignedCells"]
        tot_explosion += d["explosionRows"]; tot_misaligned += d["misalignedRows"]

    noise_pct = (100 * tot_misaligned_cells / tot_scored) if tot_scored else 0.0
    raw_acc = (100 * tot_match / tot_scored) if tot_scored else 0.0
    # adjusted = accuracy with alignment-noise cells removed from the denominator
    # (i.e. if mis-aligned rows were correctly paired they would not count as cell faults).
    adj_den = tot_scored - tot_misaligned_cells
    adj_acc = (100 * tot_match / adj_den) if adj_den else None

    run_label = os.path.relpath(run_dir, C.RUNS_DIR)
    lines = [f"# Table alignment-noise diagnostic — {run_label}", ""]
    lines.append(f"Scored cells: **{tot_scored}**  |  raw cellAcc: **{raw_acc:.1f}%**  |  "
                 f"alignment-noise cells: **{tot_misaligned_cells}** ({noise_pct:.1f}pp)  |  "
                 f"alignment-adjusted cellAcc: **{adj_acc:.1f}%**" if adj_acc is not None
                 else f"Scored cells: **{tot_scored}**  |  raw cellAcc: **{raw_acc:.1f}%**")
    lines += ["", f"Explosion rows (fully-wrong): **{tot_explosion}**  |  "
              f"of which mis-aligned (a better pairing exists): **{tot_misaligned}**", ""]
    lines += ["_alignment-noise = cells trapped in rows the aligner mis-paired; these are "
              "ONE alignment fault each, not N cell faults. The gap between raw and adjusted "
              "cellAcc is the W1 measurement error (audit A3)._", ""]
    lines += ["## Per sample", "",
              "| sample | mode | rows g/e | cellAcc | sens. | explosion | misaligned | noiseCells |",
              "|---|---|---|--:|--:|--:|--:|--:|"]
    for d in sorted(per_sample, key=lambda x: -x["misalignedCells"]):
        ca = "n/a" if d["cellAcc"] is None else f"{d['cellAcc']*100:.1f}%"
        sn = "" if d["alignSensitivity"] is None else f"{d['alignSensitivity']*100:.1f}pp"
        lines.append(f"| {d['src']} | {d['alignMode']} | {d['rowsGt']}/{d['rowsExt']} | "
                     f"{ca} | {sn} | {d['explosionRows']} | {d['misalignedRows']} | {d['misalignedCells']} |")
    lines.append("")
    md = "\n".join(lines)

    out_md = os.path.join(run_dir, "TABLE_ALIGN_DIAG.md")
    out_json = os.path.join(run_dir, "TABLE_ALIGN_DIAG.json")
    open(out_md, "w", encoding="utf-8").write(md)
    json.dump({
        "schemaVersion": "table-align-diag.v1",
        "runDir": run_dir,
        "totals": {
            "scored": tot_scored, "match": tot_match,
            "rawCellAcc": round(raw_acc, 2),
            "alignmentNoiseCells": tot_misaligned_cells,
            "alignmentNoisePct": round(noise_pct, 2),
            "adjustedCellAcc": (round(adj_acc, 2) if adj_acc is not None else None),
            "explosionRows": tot_explosion, "misalignedRows": tot_misaligned,
        },
        "perSample": per_sample,
    }, open(out_json, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    sys.stdout.reconfigure(errors="replace")
    print(md)
    print(f"\n[written] {out_md}\n[written] {out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
