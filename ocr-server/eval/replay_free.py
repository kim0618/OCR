"""replay_free — re-run the free invoice extractor on a captured OCR snapshot.

The eval run (run_batch with captureOcrSnapshot) saves, per image, the EXACT
input envelope the server passed to extract_invoice_statement_free, under
runs/<ts>/snapshots/<src>.json. This script feeds that envelope back into the
extractor LOCALLY (CPU, no re-OCR), so a parser change can be tested against a
GPU run's real OCR output deterministically.

Mirrors the server's default free path: extract_invoice_statement_free(...) then
the document-scalar sanitize post-step (main.py). It does NOT replay the
FREE_HIRES_TABLE_REOCR branch (default OFF) — replay reflects that default.

Faithfulness self-check: with UNCHANGED parser code, the replayed document_fields
should equal the recorded server output (runs/<ts>/samples/<src>.json:documentFields).
FAITHFUL there means the snapshot+replay reproduce the run; after a parser edit,
the DIFFERS rows are exactly your change's effect.

CLI:
    python eval/replay_free.py                  # latest run, all snapshots
    python eval/replay_free.py --ts <run_ts>
    python eval/replay_free.py --only 1.jpg 5.pdf
    python eval/replay_free.py --show-fields    # print produced document_fields
"""
from __future__ import annotations

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))  # ocr-server/ so `extractors` imports

import contract as C  # noqa: E402
from extractors.invoice_statement_free import extract_invoice_statement_free  # noqa: E402

# Server post-step (main.py applies it after the free extractor). Imported
# defensively: the parser is under active refactor, so a rename must NOT break
# replay — we fall back to identity and flag the faithfulness caveat instead.
try:
    from extractors.invoice_statement_free import (  # noqa: E402
        sanitize_document_scalar_fields as _sanitize,
    )
except Exception:  # pragma: no cover - name moved/renamed
    _sanitize = None


def _deserialize_lines(serial: list | None) -> list:
    """[[pts, text, conf], ...] -> [(pts, text, conf), ...] (extractor input shape)."""
    out: list = []
    for row in (serial or []):
        try:
            out.append((row[0], row[1], row[2]))
        except Exception:
            continue
    return out


def replay_one(snapshot: dict) -> dict:
    """Reproduce the server's default free path for one captured envelope."""
    lines = _deserialize_lines(snapshot.get("ocr_lines_raw"))
    img = snapshot.get("image_size") or [0, 0]
    result = extract_invoice_statement_free(
        ocr_lines_raw=lines,
        full_text=snapshot.get("full_text", ""),
        image_size=(int(img[0]), int(img[1])),
        doc_type=snapshot.get("doc_type", "invoice_statement"),
        context=snapshot.get("context") or {},
    )
    df = result.get("document_fields") if isinstance(result, dict) else None
    if not isinstance(df, dict):
        df = result
    if isinstance(df, dict) and _sanitize is not None:
        df = _sanitize(df)  # server post-step (main.py)
    return df if isinstance(df, dict) else {}


def _recorded_df(run_dir: str, src: str) -> dict | None:
    try:
        rec = json.load(open(os.path.join(run_dir, "samples", src + ".json"), encoding="utf-8"))
        return rec.get("documentFields")
    except Exception:
        return None


def _canon(obj) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ts", default=None)
    ap.add_argument("--testset", default=C.DEFAULT_TESTSET)
    ap.add_argument("--only", nargs="*", default=None)
    ap.add_argument("--show-fields", action="store_true")
    args = ap.parse_args()

    run_dir = os.path.join(C.RUNS_DIR, args.ts) if args.ts else C.latest_run(args.testset)
    if not run_dir or not os.path.isdir(run_dir):
        print(f"no run dir ({run_dir})")
        return 1
    snap_dir = os.path.join(run_dir, "snapshots")
    if not os.path.isdir(snap_dir):
        print(f"no snapshots/ in {run_dir} — this run captured no OCR snapshot.\n"
              "  (needs a server with captureOcrSnapshot support + the free path taken)")
        return 1

    files = sorted(f for f in os.listdir(snap_dir) if f.endswith(".json"))
    if args.only:
        keep = set(args.only)
        files = [f for f in files if f[:-5] in keep]
    if not files:
        print("no matching snapshots")
        return 1

    print(f"replay over {os.path.relpath(run_dir, C.RUNS_DIR)}: {len(files)} snapshot(s)\n")
    n_faithful = 0
    for f in files:
        src = f[:-5]
        snap = json.load(open(os.path.join(snap_dir, f), encoding="utf-8"))
        df = replay_one(snap)
        rows = df.get("tableRows") if isinstance(df, dict) else None
        rec_df = _recorded_df(run_dir, src)
        faithful = rec_df is not None and _canon(rec_df) == _canon(df)
        n_faithful += 1 if faithful else 0
        tag = "FAITHFUL" if faithful else ("DIFFERS " if rec_df is not None else "no-record")
        print(f"  {tag}  {src:<10} rows={len(rows) if isinstance(rows, list) else '?':<3} "
              f"lines={len(snap.get('ocr_lines_raw') or [])}")
        if args.show_fields:
            print(json.dumps(df, ensure_ascii=False, indent=2))
    print(f"\nfaithful (== recorded server output): {n_faithful}/{len(files)}")
    print("  FAITHFUL = replay reproduces the run. After a parser edit, "
          "DIFFERS rows are your change's effect.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
