"""finetune_crops_balance — harvest CORRECTLY-read crops for fine-tune balance.

Fine-tuning only on failures makes the model overfit to hard cases and FORGET
what it already reads well (catastrophic forgetting). The fix is to mix in
correctly-read examples. This harvests them, kept SEPARATE from the failure pool
so a training run can choose the mix ratio:

  eval/finetune_corpus/crops_correct/<hash>.jpg
  eval/finetune_corpus/labels_correct.txt

Only cells/fields that MATCHED GT are used — so the label is GT-verified, never
the OCR output itself (using OCR text as truth would be circular and could train
on errors). Reuses the SAME box-localization + crop-cutting as the failure path.

Capped per image (DEFAULT_CAP) so the balance pool stays bounded/representative
rather than swallowing every correct cell at scale. Checker-safe sidecar.

    ../.venv/Scripts/python.exe eval/finetune_crops_balance.py
    ../.venv/Scripts/python.exe eval/finetune_crops_balance.py --ts 070_.../study --cap 30
"""
from __future__ import annotations

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import contract as C  # noqa: E402
import parser_drop_classify as P  # noqa: E402
from finetune_ledger import _ocr_boxes, _best_box, BOX_MATCH_FLOOR, CORPUS_DIR  # noqa: E402
from finetune_crops import cut_crops, load_labels, write_labels  # noqa: E402

CROPS_CORRECT_DIR = os.path.join(CORPUS_DIR, "crops_correct")
LABELS_CORRECT_PATH = os.path.join(CORPUS_DIR, "labels_correct.txt")
DEFAULT_CAP = 30  # max correct crops per image (bound the balance pool)


def _cropready(gtn: str, vtype: str, boxes: list[dict]) -> dict | None:
    """Same localization rule as the failure path: best box over the floor, and
    for digit types require exact containment (avoid mis-localizing similar
    numbers). Returns the box or None."""
    box, ratio = _best_box(gtn, vtype, boxes)
    if not box or ratio < BOX_MATCH_FLOOR:
        return None
    if vtype in P.DIGIT_TYPES:
        g, k = P._collapse_digits(gtn), P._collapse_digits(box["text"])
        if not (len(g) >= 2 and (g in k or k in g)):
            return None
    return box


def correct_entries(src: str, cmp: dict, snap: dict | None, cap: int) -> list[dict]:
    if not snap:
        return []
    boxes = _ocr_boxes(snap)
    img_size = snap.get("image_size")
    candidates: list[tuple[str, str, str, str]] = []
    for label, info in cmp["fields"]["perField"].items():
        if info.get("status") == "match" and info.get("gtNorm"):
            candidates.append((f"field:{label}", label, P._field_type(label), info["gtNorm"]))
    for row in cmp["table"]["rows"]:
        for ck, cell in row["cells"].items():
            if cell.get("status") == "match" and cell.get("gtNorm"):
                candidates.append((f"row{row['rowIndex']}:{ck}", ck, P._cell_type(ck), cell["gtNorm"]))

    out: list[dict] = []
    for loc, col, vtype, gtn in candidates:
        box = _cropready(gtn, vtype, boxes)
        if not box:
            continue
        out.append({"src": src, "location": loc, "column": col, "gt": gtn,
                    "ocrBox": box, "imageSize": img_size})
        if len(out) >= cap:
            break
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ts", default=None)
    ap.add_argument("--testset", default="invoice_study")
    ap.add_argument("--cap", type=int, default=DEFAULT_CAP, help="max correct crops per image")
    args = ap.parse_args()

    try:
        import cv2  # noqa: F401
    except Exception as exc:
        print(f"[balance] cv2 unavailable ({exc}); skipping"); return 0

    run_dir = os.path.join(C.RUNS_DIR, args.ts) if args.ts else C.latest_run(args.testset)
    if not run_dir or not os.path.isdir(run_dir):
        print(f"no run dir ({run_dir})"); return 2
    cmp_dir = os.path.join(run_dir, "compare")
    snap_dir = os.path.join(run_dir, "snapshots")
    processed_dir = os.path.join(run_dir, "processed")
    if not (os.path.isdir(cmp_dir) and os.path.isdir(processed_dir)):
        print(f"need compare/ + processed/ in {run_dir}"); return 2

    entries: list[dict] = []
    for f in sorted(os.listdir(cmp_dir)):
        if not f.endswith(".json"):
            continue
        src = f[:-5]
        cmp = json.load(open(os.path.join(cmp_dir, f), encoding="utf-8"))
        sp = os.path.join(snap_dir, f)
        snap = json.load(open(sp, encoding="utf-8")) if os.path.exists(sp) else None
        entries += correct_entries(src, cmp, snap, args.cap)

    labels = load_labels(LABELS_CORRECT_PATH)
    stats = cut_crops(entries, processed_dir, CROPS_CORRECT_DIR, labels, rel_prefix="crops_correct")
    write_labels(labels, LABELS_CORRECT_PATH)

    sys.stdout.reconfigure(errors="replace")
    run_label = os.path.relpath(run_dir, C.RUNS_DIR)
    print(f"[balance] {run_label}: correct candidates={len(entries)}  "
          f"cut={stats['cut']} new, {stats['existing']} already, "
          f"{stats['missing_img']} no-image, {stats['oob']} bad-bbox")
    print(f"[balance] BALANCE crops: {len(labels)} total  ->  {CROPS_CORRECT_DIR}")
    print(f"[balance] labels: {LABELS_CORRECT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
