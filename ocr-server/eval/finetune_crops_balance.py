"""finetune_crops_balance — harvest CORRECTLY-read crops for fine-tune balance.

Fine-tuning only on failures makes the model overfit to hard cases and FORGET
what it already reads well (catastrophic forgetting). The fix is to mix in
correctly-read examples. This harvests them, kept SEPARATE from the failure pool
so a training run can choose the mix ratio:

  eval/finetune_corpus/crops_correct/<hash>.jpg
  eval/finetune_corpus/labels_correct.txt

Only cells/fields that MATCHED GT are used. LABEL = the OCR box text itself
(2026-07-08 변경): match 로 GT-검증된 크롭에 한해 OCR 원문이 곧 정답이며, **인쇄
포맷(콤마·대시·공백)을 보존한 유일한 소스**다 — war GT 는 원문조차 콤마가 없어
(684000), gtNorm 라벨은 모델에게 '구분자 벗기기'를 가르쳐 파이프라인을 붕괴시킴
(v1~v3 실측: 돈 콤마 스트립 → 064 amount 급락, 짧은수량 삭제). 무검증 OCR 텍스트를
라벨로 쓰는 순환은 여전히 금지 — match 검증된 것만 이 경로에 들어온다.
Reuses the SAME box-localization + crop-cutting as the failure path.

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
from finetune_crops import crop_name, cut_crops, load_labels, write_labels  # noqa: E402

CROPS_CORRECT_DIR = os.path.join(CORPUS_DIR, "crops_correct")
LABELS_CORRECT_PATH = os.path.join(CORPUS_DIR, "labels_correct.txt")
BALANCE_META_PATH = os.path.join(CORPUS_DIR, "labels_correct.meta.jsonl")
# 전 필드 인쇄형 학습(2026-07-09): balance = GT-검증된 '우리 읽음(인쇄형)' 크롭이 곧
# 전 필드(숫자·날짜·품목) 인쇄형 라벨 소스. 상한을 30→160 으로 올려 이미지당 대부분의
# 정답 셀을 담는다(문서당 ~160셀). 이걸 학습 주 데이터로 써서 전 필드 인식을 올림
# (품목 failure 는 그 위에 약점 보강). 라벨=인쇄형이라 v4 콤마-붕괴 없음.
DEFAULT_CAP = 160


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
        text = (box.get("text") or "").strip()
        if not text:
            continue
        # 라벨 = OCR 원문(인쇄형). gtNorm 은 검증에 이미 쓰였고 라벨로는 독(모듈 주석).
        out.append({"src": src, "location": loc, "column": col, "gt": text,
                    "gtNorm": gtn, "labelForm": "raw",
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

    # Preserve the originating column.  The old two-column label file is kept
    # for Paddle compatibility; this small sidecar lets held-out reporting
    # distinguish real itemName crops from company/address Hangul.
    metadata: dict[str, dict] = {}
    if os.path.exists(BALANCE_META_PATH):
        for line in open(BALANCE_META_PATH, encoding="utf-8"):
            try:
                rec = json.loads(line)
                metadata[rec["path"]] = rec
            except (json.JSONDecodeError, KeyError):
                continue
    for entry in entries:
        rel = f"crops_correct/{crop_name(entry)}"
        if rel in labels:
            metadata[rel] = {
                "path": rel, "column": entry.get("column"),
                "location": entry.get("location"), "source": "balance",
            }
    tmp = BALANCE_META_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        for rel in sorted(metadata):
            fh.write(json.dumps(metadata[rel], ensure_ascii=False) + "\n")
    os.replace(tmp, BALANCE_META_PATH)

    sys.stdout.reconfigure(errors="replace")
    run_label = os.path.relpath(run_dir, C.RUNS_DIR)
    print(f"[balance] {run_label}: correct candidates={len(entries)}  "
          f"cut={stats['cut']} new, {stats['existing']} already, "
          f"{stats['missing_img']} no-image, {stats['oob']} bad-bbox")
    print(f"[balance] BALANCE crops: {len(labels)} total  ->  {CROPS_CORRECT_DIR}")
    print(f"[balance] labels: {LABELS_CORRECT_PATH}")
    print(f"[balance] metadata: {BALANCE_META_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
