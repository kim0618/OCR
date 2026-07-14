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
    append_missing_ha_rows as _append_ha,
    salvage_blob_amount as _salvage_blob_amount,
    split_merged_item_name as _split_merged_item_name,
    recover_shifted_item_name as _recover_shifted_item_name,
    adopt_missing_item_names as _adopt_item_names,
    synthesize_missing_rows as _synth_rows,
    refine_supplier_bizno as _refine_sup_bizno,
    refine_buyer_bizno as _refine_buy_bizno,
)
from extractors.invoice_statement import extract_invoice_statement_fields  # noqa: E402
from extractors.master_match import fill_master_match as _fill_master  # noqa: E402
from extractors.master_match import fill_party_match as _fill_party  # noqa: E402
from extractors.master_match import (  # noqa: E402
    strip_trailing_item_classification as _strip_item_classification,
)

# ②G4 마스터 매칭 포함 여부. False(--no-master-match)로 돌리면 Rule 단계(매칭 전) 사이드카가
# 나온다 — baseline_matrix가 Rule=replay_compare_rule / Master=replay_compare로 단계 분리.
MASTER_MATCH = True


def _load_recorded_run_scope(run_dir: str) -> list[str] | None:
    """Return the exact source-file scope recorded by the historical live run.

    A run's snapshots directory may contain files left by an older invocation,
    while the current manifest may have changed since the run was created.
    ``run_meta.ran`` is therefore the only stable replay scope for historical
    runs. Older runs without this metadata retain the legacy snapshot behavior.
    """
    path = os.path.join(run_dir, "run_meta.json")
    try:
        meta = json.load(open(path, encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    ran = meta.get("ran")
    if not isinstance(ran, list) or not all(isinstance(src, str) and src for src in ran):
        return None
    # Preserve the recorded order while rejecting accidental duplicates.
    return list(dict.fromkeys(ran))


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
    # mirror main.py join-point ③P1 HA-append (품명단독라인 → 2D 재구성 행 추가)
    if isinstance(df, dict) and isinstance(df.get("tableRows"), list):
        try:
            df["tableRows"], _ = _append_ha(df["tableRows"], lines)
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
    # mirror main.py join-point 같이읽힘(blob) itemName split (blob 신호 행만)
    if isinstance(df, dict) and df.get("tableRows"):
        try:
            df["tableRows"], _ = _split_merged_item_name(df["tableRows"])
        except Exception:
            pass
    # mirror main.py join-point 컬럼밀림 복구 (itemName 빈칸 + spec 약품명)
    if isinstance(df, dict) and df.get("tableRows"):
        try:
            df["tableRows"], _ = _recover_shifted_item_name(df["tableRows"])
        except Exception:
            pass
    # mirror main.py join-point 품명입양 (itemName 빈 행 ← y-밴드 미소비 품명전용 라인)
    if isinstance(df, dict) and df.get("tableRows"):
        try:
            df["tableRows"], _ = _adopt_item_names(df["tableRows"], lines)
        except Exception:
            pass
    # mirror main.py join-point 행신설 (미소비 품명라인+콤마금액 y-밴드 쌍, 3중 게이트)
    if isinstance(df, dict) and df.get("tableRows"):
        try:
            df["tableRows"], _ = _synth_rows(df["tableRows"], lines)
        except Exception:
            pass
    # mirror main.py join-point standalone trailing 전문/일반 cleanup
    if isinstance(df, dict) and df.get("tableRows"):
        try:
            df["tableRows"], _ = _strip_item_classification(df["tableRows"])
        except Exception:
            pass
    # mirror main.py join-point 사업자번호 재선택 (마스터매칭 앞 — itembuycust 앵커)
    if isinstance(df, dict):
        try:
            df, _ = _refine_sup_bizno(df, lines)
            df, _ = _refine_buy_bizno(df, lines)
        except Exception:
            pass
    # mirror main.py join-point 마스터 자동매칭 (빈칸 채움 + itembuycust rescue, ②G4)
    if MASTER_MATCH and isinstance(df, dict) and df.get("tableRows"):
        try:
            df["tableRows"], _ = _fill_master(
                df["tableRows"], supplier_bizno=df.get("supplierBizNumber"))
        except Exception:
            pass
    # mirror main.py join-point ④거래처/지점 매칭 (사업자번호 앵커/지점 trigram)
    if isinstance(df, dict):
        try:
            df, _ = _fill_party(df)
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

    recorded_scope = _load_recorded_run_scope(run_dir)
    snapshot_sources = {f[:-5] for f in os.listdir(snap_dir) if f.endswith(".json")}
    if recorded_scope is not None:
        missing_snapshots = [src for src in recorded_scope if src not in snapshot_sources]
        if missing_snapshots:
            print(f"run_meta.ran has {len(missing_snapshots)} source(s) without snapshots; "
                  "historical replay would be incomplete")
            for src in missing_snapshots[:20]:
                print(f"  missing snapshot: {src}")
            return 2
        sources = recorded_scope
        stale_count = len(snapshot_sources - set(recorded_scope))
        scope_label = f"run_meta.ran ({len(sources)}), excluded stale snapshots={stale_count}"
    else:
        sources = sorted(snapshot_sources)
        scope_label = f"legacy snapshots ({len(sources)}; no usable run_meta.ran)"
    print(f"replay+score over {os.path.relpath(run_dir, C.RUNS_DIR)}: {scope_label} "
          f"-> {out_subdir}/\n")
    n_written = n_faithful = n_free = 0
    sys.stdout.reconfigure(errors="replace")
    for src in sources:
        if agg is not None:
            gtkey = gtkey_by_src.get(src)
            if not gtkey or gtkey not in agg:
                print(f"  skip {src:<10} (no GT in manifest)"); continue
        elif not gt_by_src.get(src):
            print(f"  skip {src:<10} (no GT in manifest)"); continue
        snap = json.load(open(os.path.join(snap_dir, src + ".json"), encoding="utf-8"))
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
    ap.add_argument("--no-master-match", action="store_true",
                    help="②G4 마스터 매칭 없이 replay (Rule 단계 사이드카용; "
                         "관례: --out-subdir replay_compare_rule)")
    args = ap.parse_args()
    if args.no_master_match:
        MASTER_MATCH = False
    raise SystemExit(replay_compare(args.ts, args.testset, args.out_subdir))
