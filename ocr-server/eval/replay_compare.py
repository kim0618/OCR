"""replay_compare — re-score a parser edit LOCALLY, no re-OCR, no GPU, no training.

The missing link in the local loop. Pieces that already existed:
  - replay_free.replay_one : run the (edited) free parser on a frozen OCR snapshot
  - compare_fields / compare_table / buckets : the SAME scorer the AWS run uses

This wires them: for each snapshot in a run, replay the parser on it, score the
output against GT, and write a fresh per-sample comparison — into a SIDECAR dir
(default `replay_compare/`) so the original `compare/` (and the checker) are
untouched. Then `parser_drop_classify.py --compare-dir replay_compare` reads it.

So the loop closes WITHOUT AWS:
    edit parser  ->  python eval/replay_compare.py
                 ->  python eval/parser_drop_classify.py --compare-dir replay_compare
                 ->  see which class shrank  ->  edit again

Faithful dispatch: this reproduces the SERVER's real free->gate->fallback choice
(main.py ~3289-3419), not just the free path — because the fallback extractor
(extract_invoice_statement_fields) also consumes only the snapshot's inputs
(ocr_lines_raw + context's tableExpectedColumns/tableBounds/columnGuides). So all
24 samples replay as production would, and each is tagged path=free|fallback.
The one thing NOT replayed is FREE_HIRES_TABLE_REOCR (needs re-OCR; default OFF).
Faithfulness vs the recorded run is reported per sample (FAITHFUL = unchanged).

    ../.venv/Scripts/python.exe eval/replay_compare.py
    ../.venv/Scripts/python.exe eval/replay_compare.py --ts 053_20260617_142725/study
"""
from __future__ import annotations

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import contract as C  # noqa: E402
from build_manifest import build_manifest  # noqa: E402
from compare_fields import compare_fields  # noqa: E402
from compare_table import compare_table  # noqa: E402
from buckets import tag_sample  # noqa: E402
from gt_loader import load_gt, load_gt_aggregate  # noqa: E402
from replay_free import _deserialize_lines, _recorded_df, _canon  # noqa: E402

# server post-step + free-result gate + fallback extractor — all live in extractors
# (no main.py import => no OCR model load). Mirrors main.py ~3320-3419 dispatch.
from extractors.invoice_statement_free import (  # noqa: E402
    extract_invoice_statement_free,
    sanitize_document_scalar_fields as _sanitize,
    _is_valid_invoice_statement_free_result as _free_ok,
    fill_pharma_columns as _fill_pharma,
    fill_scalar_defaults as _fill_scalars,
    drop_boilerplate_table_rows as _drop_boiler,
    salvage_blob_amount as _salvage_blob_amount,
)
from extractors.invoice_statement import extract_invoice_statement_fields  # noqa: E402


def replay_dispatch(snap: dict) -> tuple[dict, str]:
    """Reproduce the server's free->gate->fallback choice on a snapshot envelope.

    Returns (document_fields, path) where path is 'free' or 'fallback'. Skips the
    default-OFF FREE_HIRES_TABLE_REOCR branch (it re-OCRs; not replayable offline).
    """
    lines = _deserialize_lines(snap.get("ocr_lines_raw"))
    img = snap.get("image_size") or [0, 0]
    ctx = snap.get("context") or {}
    dt = snap.get("doc_type", "invoice_statement")
    free = extract_invoice_statement_free(
        ocr_lines_raw=lines, full_text=snap.get("full_text", ""),
        image_size=(int(img[0]), int(img[1])), doc_type=dt, context=ctx,
    )
    if _free_ok(free):
        df = free.get("document_fields") if isinstance(free, dict) else None
        if not isinstance(df, dict):
            df = free
        path = "free"
    else:
        df = extract_invoice_statement_fields(
            lines, debug={},
            table_expected_columns=ctx.get("tableExpectedColumns"),
            table_bounds=ctx.get("tableBounds"),
            column_guides=ctx.get("columnGuides"),
        )
        path = "fallback"
    if isinstance(df, dict) and _sanitize is not None:
        df = _sanitize(df)
    # mirror main.py join-point boilerplate/footer row drop (R1) — before pharma fill
    if isinstance(df, dict) and df.get("tableRows"):
        try:
            df["tableRows"], _ = _drop_boiler(df["tableRows"])
        except Exception:
            pass
    # mirror main.py join-point blob-amount salvage (empty amount -> last comma-money)
    if isinstance(df, dict) and df.get("tableRows"):
        try:
            df["tableRows"], _ = _salvage_blob_amount(df["tableRows"])
        except Exception:
            pass
    # mirror main.py join-point pharma-column fill (empty cells only)
    if isinstance(df, dict) and df.get("tableRows"):
        try:
            df["tableRows"], _ = _fill_pharma(df["tableRows"], lines)
        except Exception:
            pass
    # mirror main.py scalar defaults (taxType/discountAmount)
    if isinstance(df, dict):
        try:
            df, _ = _fill_scalars(df)
        except Exception:
            pass
    return (df if isinstance(df, dict) else {}), path


def replay_compare(ts: str | None, testset: str, out_subdir: str) -> int:
    run_dir = os.path.join(C.RUNS_DIR, ts) if ts else C.latest_run(testset)
    if not run_dir or not os.path.isdir(run_dir):
        print(f"no run dir ({run_dir})"); return 2
    snap_dir = os.path.join(run_dir, "snapshots")
    if not os.path.isdir(snap_dir):
        print(f"no snapshots/ in {run_dir} — cannot replay (run had no OCR snapshot)."); return 2
    out_dir = os.path.join(run_dir, out_subdir)
    os.makedirs(out_dir, exist_ok=True)

    manifest = build_manifest(testset)
    kind = manifest["kind"]
    # War/ETL thin: ONE aggregate GT, indexed by gtKey (load once). Else per-image.
    agg = None
    if manifest.get("gtAggregate"):
        agg = load_gt_aggregate(os.path.normpath(os.path.join(C.HERE, manifest["gtAggregate"])), profile=kind)
        gtkey_by_src = {s["sourceFile"]: s["gtKey"] for s in manifest["samples"] if s.get("gtKey")}
    else:
        gt_by_src = {s["sourceFile"]: s["gt"] for s in manifest["samples"] if s.get("gt")}

    snaps = sorted(f for f in os.listdir(snap_dir) if f.endswith(".json"))
    print(f"replay+score over {os.path.relpath(run_dir, C.RUNS_DIR)}: {len(snaps)} snapshot(s) "
          f"-> {out_subdir}/\n")
    n_written = n_faithful = n_free = 0
    sys.stdout.reconfigure(errors="replace")
    for f in snaps:
        src = f[:-5]
        if agg is not None:
            gtkey = gtkey_by_src.get(src)
            if not gtkey or gtkey not in agg:
                print(f"  skip {src:<10} (no GT in manifest)"); continue
        elif not gt_by_src.get(src):
            print(f"  skip {src:<10} (no GT in manifest)"); continue
        snap = json.load(open(os.path.join(snap_dir, f), encoding="utf-8"))
        ext_df, path = replay_dispatch(snap)            # (edited) parser, faithful dispatch
        n_free += 1 if path == "free" else 0
        gt = agg[gtkey] if agg is not None else load_gt(
            os.path.normpath(os.path.join(C.HERE, gt_by_src[src])), profile=kind)

        fcmp = compare_fields(gt, ext_df)
        tcmp = compare_table(gt["tableRows"], ext_df.get("tableRows") or [])
        tags = tag_sample(fcmp, tcmp, preprocess=None)
        out = {
            "sourceFile": src, "profile": gt["profile"],
            "extractionPath": path,                     # free | fallback (classifier reads this)
            "pageCount": None, "multiPage": None,
            "fields": fcmp, "table": tcmp, "buckets": tags,
        }
        with open(os.path.join(out_dir, src + ".json"), "w", encoding="utf-8") as fh:
            json.dump(out, fh, ensure_ascii=False, indent=2); fh.write("\n")
        n_written += 1

        rec = _recorded_df(run_dir, src)
        faithful = rec is not None and _canon(rec) == _canon(ext_df)
        n_faithful += 1 if faithful else 0
        fa = fcmp["fieldAccuracy"]; ca = tcmp["cellAccuracy"]
        tag = "FAITHFUL" if faithful else ("CHANGED " if rec is not None else "no-record")
        print(f"  {tag}  {path:<8} {src:<10} field={('n/a' if fa is None else f'{fa*100:5.1f}%')}"
              f"  cell={('n/a' if ca is None else f'{ca*100:5.1f}%')}")

    print(f"\n[written] {out_dir}  ({n_written} samples, path: {n_free} free / "
          f"{n_written - n_free} fallback, {n_faithful} unchanged vs recorded)")
    print(f"next: python eval/parser_drop_classify.py --ts {os.path.relpath(run_dir, C.RUNS_DIR)} "
          f"--compare-dir {out_subdir}")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--ts", default=None, help="run dir under runs/ (default: latest study run)")
    ap.add_argument("--testset", default=C.DEFAULT_TESTSET)
    ap.add_argument("--out-subdir", default="replay_compare",
                    help="sidecar dir under the run (NOT the checker's compare/)")
    args = ap.parse_args()
    raise SystemExit(replay_compare(args.ts, args.testset, args.out_subdir))
