"""finetune_crops — cut recognition-failure crops from a run's processed images.

Closes the fine-tune DATA path: turns the coordinate-only ledger into actual
(crop image, label) pairs — the form a PP-OCR rec fine-tune consumes.

Source of truth = the EXACT image OCR ran on. run_batch saved it to
  runs/<ts>/processed/<src>.jpg   (== main.py processed_image == ocr_img)
so the ledger's ocrBox bbox (ocr_lines_raw space) lines up with it directly.
NO re-derivation, NO server change.

For every cropReady ledger entry it cuts the bbox (small context pad) and
accumulates it into the PINNED fine-tune folder, de-duplicated by the SAME
identity the corpus uses (src+location+gt+bbox), so re-running over the same
images never duplicates a crop:

  eval/finetune_corpus/crops/<hash>.jpg
  eval/finetune_corpus/labels.txt        (crops/<hash>.jpg \t <gt>)

cut_crops() + the label IO are reused by finetune_crops_balance.py (the correct-
read balance pool). Checker-safe sidecar.

    ../.venv/Scripts/python.exe eval/finetune_crops.py
    ../.venv/Scripts/python.exe eval/finetune_crops.py --ts 070_.../study
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import contract as C  # noqa: E402
from finetune_ledger import CORPUS_DIR  # reuse the pinned corpus home  # noqa: E402

CROPS_DIR = os.path.join(CORPUS_DIR, "crops")
LABELS_PATH = os.path.join(CORPUS_DIR, "labels.txt")
PAD = 2  # px context around the bbox (helps recognition training)


def crop_key(e: dict) -> str:
    """Dedup identity: same image + same location + same label + same box."""
    bbox = "|".join(str(v) for v in (e.get("ocrBox") or {}).get("bbox", []))
    return f"{e['src']}::{e['location']}::{e['gt']}::{bbox}"


def crop_name(e: dict) -> str:
    return hashlib.sha1(crop_key(e).encode("utf-8")).hexdigest()[:16] + ".jpg"


def load_labels(path: str) -> dict[str, str]:
    """rel_crop_path -> gt, from an existing label file (dedup across runs)."""
    out: dict[str, str] = {}
    if os.path.exists(path):
        for ln in open(path, encoding="utf-8"):
            ln = ln.rstrip("\n")
            if ln and "\t" in ln:
                p, gt = ln.split("\t", 1)
                out[p] = gt
    return out


def write_labels(labels: dict[str, str], path: str) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        for p in sorted(labels):
            fh.write(f"{p}\t{labels[p]}\n")
    os.replace(tmp, path)


def cut_crops(entries: list[dict], processed_dir: str, crops_dir: str,
              labels: dict[str, str], rel_prefix: str) -> dict[str, int]:
    """Cut each entry's bbox from runs/<ts>/processed/<src>.jpg into crops_dir,
    recording rel_prefix/<hash>.jpg -> gt in `labels` (mutated). De-dups by file
    existence. Returns stats. Requires cv2; caller imports it."""
    import cv2
    os.makedirs(crops_dir, exist_ok=True)
    by_src: dict[str, list[dict]] = {}
    for e in entries:
        by_src.setdefault(e["src"], []).append(e)

    stats = {"cut": 0, "existing": 0, "missing_img": 0, "oob": 0}
    for src, es in by_src.items():
        img_path = os.path.join(processed_dir, src + ".jpg")
        img = cv2.imread(img_path) if os.path.exists(img_path) else None
        if img is None:
            stats["missing_img"] += len(es); continue
        H, W = img.shape[:2]
        for e in es:
            name = crop_name(e)
            rel = f"{rel_prefix}/{name}"
            bbox = (e.get("ocrBox") or {}).get("bbox") or []
            x0, y0, x1, y1 = (list(bbox) + [0, 0, 0, 0])[:4]
            x0, y0 = max(0, int(x0) - PAD), max(0, int(y0) - PAD)
            x1, y1 = min(W, int(x1) + PAD), min(H, int(y1) + PAD)
            if x1 <= x0 or y1 <= y0:
                stats["oob"] += 1; continue
            labels[rel] = e["gt"]                       # label always recorded/refreshed
            if os.path.exists(os.path.join(crops_dir, name)):
                stats["existing"] += 1; continue         # crop already cut (dedup across runs)
            cv2.imwrite(os.path.join(crops_dir, name), img[y0:y1, x0:x1])
            stats["cut"] += 1
    return stats


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ts", default=None, help="run dir under runs/ (default: latest study run)")
    ap.add_argument("--testset", default="invoice_study")
    args = ap.parse_args()

    try:
        import cv2  # noqa: F401  (presence check; cut_crops re-imports locally)
    except Exception as exc:
        print(f"[finetune_crops] cv2 unavailable ({exc}); skipping crop extraction")
        return 0

    run_dir = os.path.join(C.RUNS_DIR, args.ts) if args.ts else C.latest_run(args.testset)
    if not run_dir or not os.path.isdir(run_dir):
        print(f"no run dir ({run_dir})"); return 2
    ledger_path = os.path.join(run_dir, "FINETUNE_LEDGER.json")
    processed_dir = os.path.join(run_dir, "processed")
    if not os.path.exists(ledger_path):
        print(f"no FINETUNE_LEDGER.json in {run_dir} (run finetune_ledger.py first)"); return 2
    if not os.path.isdir(processed_dir):
        print(f"no processed/ in {run_dir} (run_batch must save processed images)"); return 2

    entries = json.load(open(ledger_path, encoding="utf-8")).get("entries") or []
    ready = [e for e in entries if e.get("cropReady") and e.get("ocrBox")]
    labels = load_labels(LABELS_PATH)
    stats = cut_crops(ready, processed_dir, CROPS_DIR, labels, rel_prefix="crops")
    write_labels(labels, LABELS_PATH)

    sys.stdout.reconfigure(errors="replace")
    run_label = os.path.relpath(run_dir, C.RUNS_DIR)
    print(f"[finetune_crops] {run_label}: cropReady={len(ready)}  "
          f"cut={stats['cut']} new, {stats['existing']} already, "
          f"{stats['missing_img']} no-image, {stats['oob']} bad-bbox")
    print(f"[finetune_crops] FAILURE crops: {len(labels)} total  ->  {CROPS_DIR}")
    print(f"[finetune_crops] labels: {LABELS_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
