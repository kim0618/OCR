"""finetune_ledger — accumulate fine-tune candidate raw material from a run.

READ-ONLY analysis sidecar (like parser_drop_classify). For every defect the
classifier marks as OCR-bound work it records, per failing field/cell, the
EXPENSIVE-to-produce knowledge a future rec fine-tune needs:

    - the GT value (the would-be training LABEL)
    - what the parser emitted (for context)
    - the defect class/pattern (recognition vs parser_drop vs ambiguous_fuzzy)
    - the best-matching OCR box on the page: its recognized text, confidence
      score, and bbox  -> this is the CROP TARGET a fine-tune step would cut.

Why a ledger and not crops (decision 2026-06-22):
  * recognition-absent defects have NO OCR box (OCR never produced the value) so
    they CANNOT be auto-cropped — they are flagged noBox (needs spatial GT).
  * OCR boxes live in the preprocessed (~950px) image space; only the ORIGINAL
    image is on disk. Cutting accurate pixels would need the server to return the
    preprocessed image (a main.py change, out of scope per CLAUDE.md).
  So we capture the LABELS + box coordinates now (cheap, compounding, server-free)
  and defer pixel-cutting to the fine-tune pipeline, which is where the
  preprocessed-image plumbing belongs.

A "cropReady" entry = a misread: OCR read a near-miss at a locatable box, so the
(box, GT-label) pair is a directly trainable rec candidate later. "noBox" = OCR
produced nothing matchable -> truly absent, not yet croppable.

Touches NOTHING the checker reads. Writes only FINETUNE_LEDGER.{json,md} under
the run dir.

    ../.venv/Scripts/python.exe eval/finetune_ledger.py
    ../.venv/Scripts/python.exe eval/finetune_ledger.py --ts 053_.../study --compare-dir replay_compare
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from difflib import SequenceMatcher

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import contract as C  # noqa: E402
import parser_drop_classify as P  # noqa: E402  (reuse the SAME taxonomy)

# A box must look at least this much like the GT value before we call it the
# misread that produced this defect (and therefore a crop target). Below it we
# record noBox: nothing on the page localizes to this value.
BOX_MATCH_FLOOR = 0.55

# THE pinned accumulation home. Per-run sidecars are scattered across runs/<ts>/;
# the fine-tune corpus must live in ONE durable, de-duplicated place so it grows
# across runs and is directly consumable by a future fine-tune pipeline. This dir
# is NOT touched by the checker and is never under public/data.
CORPUS_DIR = os.path.join(HERE, "finetune_corpus")
CORPUS_PATH = os.path.join(CORPUS_DIR, "ledger.jsonl")


def _corpus_key(e: dict) -> str:
    """Dedup identity for a candidate: same image + same failing location + same
    label + same box = the same training item, even if seen in many runs."""
    bbox = "|".join(str(v) for v in (e.get("ocrBox") or {}).get("bbox", []))
    return f"{e['src']}::{e['location']}::{e['gt']}::{bbox}"


def accumulate_corpus(entries: list[dict], run_label: str) -> dict[str, int]:
    """Merge this run's entries into the pinned corpus JSONL, de-duplicated.

    Each stored record keeps firstRun/lastRun/seenCount so re-running over the
    same images grows confidence (seenCount) without duplicating rows. Rewrites
    the whole file (load→merge→write): safe and simple at our scale.
    """
    os.makedirs(CORPUS_DIR, exist_ok=True)
    store: dict[str, dict] = {}
    if os.path.exists(CORPUS_PATH):
        for ln in open(CORPUS_PATH, encoding="utf-8"):
            ln = ln.strip()
            if not ln:
                continue
            try:
                rec = json.loads(ln)
                store[rec["_key"]] = rec
            except (json.JSONDecodeError, KeyError):
                continue
    added = updated = 0
    for e in entries:
        k = _corpus_key(e)
        if k in store:
            rec = store[k]
            rec["seenCount"] = rec.get("seenCount", 1) + 1
            rec["lastRun"] = run_label
            updated += 1
        else:
            store[k] = {"_key": k, "firstRun": run_label, "lastRun": run_label,
                        "seenCount": 1, **e}
            added += 1
    # Atomic replace: the corpus is an accumulating ASSET — a crash mid-write must
    # not truncate/corrupt prior runs' candidates. Write a tmp then os.replace.
    tmp = CORPUS_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        for rec in store.values():
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    os.replace(tmp, CORPUS_PATH)
    return {"added": added, "updated": updated, "total": len(store)}


def _ocr_boxes(snap: dict | None) -> list[dict]:
    """[{text, score, bbox:[x0,y0,x1,y1]}] for every non-empty recognized line."""
    out: list[dict] = []
    for item in (snap or {}).get("ocr_lines_raw") or []:
        try:
            pts, text, score = item[0], str(item[1]), float(item[2])
        except (IndexError, TypeError, ValueError):
            continue
        if not text.strip() or not pts:
            continue
        try:
            xs = [float(p[0]) for p in pts]
            ys = [float(p[1]) for p in pts]
        except (TypeError, ValueError, IndexError):
            continue
        out.append({
            "text": text,
            "score": round(score, 4),
            "bbox": [round(min(xs), 1), round(min(ys), 1), round(max(xs), 1), round(max(ys), 1)],
        })
    return out


def _best_box(gt_norm: str, vtype: str, boxes: list[dict]) -> tuple[dict | None, float]:
    """The OCR box whose text best matches the (type-normalized) GT value.

    Digit values match on collapsed digits, text on collapsed alnum — same
    normalization parser_drop_classify uses for presence, so the ledger agrees
    with the taxonomy. Substring containment is treated as a strong match
    (tolerates OCR splitting/merging a value across a longer line)."""
    if not gt_norm or not boxes:
        return None, 0.0
    digit = vtype in P.DIGIT_TYPES
    g = P._collapse_digits(gt_norm) if digit else P._collapse_alnum(gt_norm)
    if len(g) < 2:
        return None, 0.0
    best, best_r = None, 0.0
    for b in boxes:
        k = P._collapse_digits(b["text"]) if digit else P._collapse_alnum(b["text"])
        if not k:
            continue
        r = SequenceMatcher(None, g, k).ratio()
        if g in k or k in g:
            r = max(r, 0.95)
        if r > best_r:
            best, best_r = b, r
    return best, round(best_r, 3)


def build_ledger(src: str, cmp: dict, snap: dict | None, image_path: str | None):
    """One ledger row per OCR-bound defect, enriched with its crop target."""
    boxes = _ocr_boxes(snap)
    image_size = (snap or {}).get("image_size")
    entries: list[dict] = []
    # Reuse the canonical taxonomy; keep only the OCR-bound classes — parser_drop
    # is recoverable by rules (handled in the rule loop, not fine-tune material).
    for d in P.classify_sample(src, cmp, snap):
        if d["class"] not in ("recognition", "ambiguous_fuzzy"):
            continue
        box, ratio = _best_box(d["gtNorm"], d["vtype"], boxes)
        crop_ready = box is not None and ratio >= BOX_MATCH_FLOOR
        # Digit guard: amounts/bizno/dates share digit-runs, so a high ratio can
        # localize to a DIFFERENT number (e.g. 25,760,000 vs 2,576,000). Demand
        # exact digit containment before trusting the box as this value's crop.
        if crop_ready and d["vtype"] in P.DIGIT_TYPES:
            g = P._collapse_digits(d["gtNorm"])
            k = P._collapse_digits(box["text"])
            crop_ready = len(g) >= 2 and (g in k or k in g)
        # 라벨 = 원문 GT(인쇄형 보존: 대소문자·슬래시·공백·괄호). 정규화형(gtNorm)을
        # 라벨로 쓰면 모델이 '읽기'가 아니라 '정규화(구분자 벗기기)'를 학습 — v1/v2 실측
        # (콤마 스트립 → 파서 돈인식 붕괴, 짧은수량 삭제). gtNorm 은 박스 매칭에만 사용.
        raw = (d.get("gtRaw") or "").strip()
        entries.append({
            "src": src,
            "clean": d["clean"],
            "location": d["location"],
            "column": d["column"],
            "vtype": d["vtype"],
            "class": d["class"],
            "pattern": d["pattern"],
            "status": d["status"],
            "gt": raw or d["gtNorm"],           # the would-be training label (원문 우선)
            "labelForm": "raw" if raw else "norm",  # build_dataset 게이트가 raw 만 채택
            "ext": d["extNorm"],                # what the parser emitted
            "cropReady": crop_ready,                 # trust flag: confident localization
            "matchRatio": ratio,
            # ALWAYS keep the best candidate box (preprocessed-image coords). cropReady
            # gates trust; keeping the box+ratio even when low lets later tooling
            # re-threshold without re-running, and never silently drops a near-miss.
            "ocrBox": box,
            "imageSize": image_size,            # box coords are in THIS space (~950px)
            "imagePath": image_path,            # original on disk (full-res)
        })
    return entries


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ts", default=None, help="run dir under runs/ (default: latest study run)")
    ap.add_argument("--testset", default="invoice_study")
    ap.add_argument("--compare-dir", default="compare",
                    help="'compare' (the run's) or 'replay_compare' (local parser-edit re-score)")
    ap.add_argument("--no-accumulate", action="store_true",
                    help="skip merging into the pinned corpus (per-run sidecar only)")
    args = ap.parse_args()

    run_dir = os.path.join(C.RUNS_DIR, args.ts) if args.ts else C.latest_run(args.testset)
    if not run_dir or not os.path.isdir(run_dir):
        print(f"no run dir ({run_dir})"); return 2
    cmp_dir = os.path.join(run_dir, args.compare_dir)
    snap_dir = os.path.join(run_dir, "snapshots")
    samples_dir = os.path.join(run_dir, "samples")
    if not os.path.isdir(cmp_dir):
        print(f"no {args.compare_dir}/ in {run_dir}"); return 2
    has_snap = os.path.isdir(snap_dir)
    if not has_snap:
        print("WARNING: no snapshots/ — every defect will be noBox (no boxes to localize).")

    entries: list[dict] = []
    for f in sorted(os.listdir(cmp_dir)):
        if not f.endswith(".json"):
            continue
        src = f[:-5]
        cmp = json.load(open(os.path.join(cmp_dir, f), encoding="utf-8"))
        snap = None
        sp = os.path.join(snap_dir, f)
        if has_snap and os.path.exists(sp):
            snap = json.load(open(sp, encoding="utf-8"))
        image_path = None
        rp = os.path.join(samples_dir, f)
        if os.path.exists(rp):
            try:
                image_path = json.load(open(rp, encoding="utf-8")).get("imagePath")
            except Exception:
                pass
        entries += build_ledger(src, cmp, snap, image_path)

    crop_ready = [e for e in entries if e["cropReady"]]
    low_conf = [e for e in entries if not e["cropReady"] and e["ocrBox"]]   # box exists, ratio < floor
    no_box = [e for e in entries if not e["ocrBox"]]                         # nothing localized at all
    by_class: dict = defaultdict(lambda: {"cropReady": 0, "notReady": 0})
    by_col: dict = defaultdict(lambda: {"cropReady": 0, "notReady": 0})
    for e in entries:
        k = "cropReady" if e["cropReady"] else "notReady"
        by_class[e["class"]][k] += 1
        by_col[e["column"]][k] += 1

    # --- markdown sidecar ---
    run_label = os.path.relpath(run_dir, C.RUNS_DIR)
    lines = [f"# Fine-tune candidate ledger — {run_label}", ""]
    lines.append(f"OCR-bound defects captured: **{len(entries)}**  |  "
                 f"cropReady (confident misread localization): **{len(crop_ready)}**  |  "
                 f"lowConf (box present, ratio<{BOX_MATCH_FLOOR}): **{len(low_conf)}**  |  "
                 f"noBox (nothing localized): **{len(no_box)}**"
                 + ("" if has_snap else "  _(NO SNAPSHOTS)_"))
    lines += ["", "_cropReady = OCR read a near-miss at a confidently-located box → (box, GT) is a "
              "rec fine-tune candidate once pixels are cut. lowConf = a box exists but match is weak "
              "(kept with its ratio for later re-thresholding). noBox = OCR produced nothing matchable._", ""]
    lines += ["## By class", "", "| class | cropReady | notReady |", "|---|--:|--:|"]
    for cls, c in sorted(by_class.items(), key=lambda kv: -(kv[1]["cropReady"] + kv[1]["notReady"])):
        lines.append(f"| {cls} | {c['cropReady']} | {c['notReady']} |")
    lines += ["", "## By column", "", "| column | cropReady | notReady |", "|---|--:|--:|"]
    for col, c in sorted(by_col.items(), key=lambda kv: -(kv[1]["cropReady"] + kv[1]["notReady"])):
        lines.append(f"| {col} | {c['cropReady']} | {c['notReady']} |")
    lines.append("")
    md = "\n".join(lines)

    suffix = "" if args.compare_dir == "compare" else "_" + args.compare_dir
    out_md = os.path.join(run_dir, f"FINETUNE_LEDGER{suffix}.md")
    out_json = os.path.join(run_dir, f"FINETUNE_LEDGER{suffix}.json")
    open(out_md, "w", encoding="utf-8").write(md)
    json.dump({
        "schemaVersion": "finetune-ledger.v1",
        "runDir": run_dir,
        "compareDir": args.compare_dir,
        "hasSnapshots": has_snap,
        "boxMatchFloor": BOX_MATCH_FLOOR,
        "summary": {
            "ocrBoundDefects": len(entries),
            "cropReady": len(crop_ready),
            "lowConf": len(low_conf),
            "noBox": len(no_box),
            "byClass": dict(by_class),
        },
        "entries": entries,
    }, open(out_json, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    # Accumulate into the pinned corpus — ONLY from the real OCR run ('compare').
    # replay_compare re-scores the SAME frozen OCR, so its recognition set is
    # identical; accumulating it would double-count, not add new evidence.
    corpus_msg = ""
    if args.compare_dir == "compare" and not args.no_accumulate:
        stats = accumulate_corpus(entries, run_label)
        corpus_msg = (f"\n[corpus] {CORPUS_PATH}\n[corpus] +{stats['added']} new, "
                      f"{stats['updated']} re-seen, {stats['total']} total candidates")
    elif args.compare_dir != "compare":
        corpus_msg = "\n[corpus] skipped (replay_compare re-scores frozen OCR; not new evidence)"

    sys.stdout.reconfigure(errors="replace")
    print(md)
    print(f"\n[written] {out_md}\n[written] {out_json}{corpus_msg}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
