"""build_manifest — auto-pair images/recorded-results with GT into a manifest.

Pairing key = GT's top-level `sourceFile`. Status per sample:
  active      image present AND GT present (live OCR run)
  canned      GT present, NO image, recorded rec envelope present (⓲) — runnable
              from the recorded result, so a DB/thin testset runs with no image
  pending_gt  image present, no GT yet
  gt_orphan   GT present, no image and no recorded rec
  excluded    deliberately dropped (testset.excluded, e.g. 2.pdf)

Per-testset (⓬): pass a testset name; defaults to invoice_study (rich, live).
Measurement-only: reads the testset, writes ONLY eval/manifest.json.
"""

from __future__ import annotations

import glob
import json
import os
from typing import Any

import contract as C
from gt_loader import GTLoadError, load_gt


def _gt_index(gt_dir: str) -> dict[str, str]:
    """Map sourceFile -> GT file path, by reading each GT's sourceFile."""
    index: dict[str, str] = {}
    for path in sorted(glob.glob(os.path.join(gt_dir, "*.json"))):
        try:
            with open(path, encoding="utf-8") as fh:
                src = json.load(fh).get("sourceFile")
        except (OSError, json.JSONDecodeError):
            continue
        if src:
            index.setdefault(src, path)
    return index


def _images(img_dir: str) -> dict[str, str]:
    """Map sourceFile (basename) -> image path for files in the testset dir."""
    out: dict[str, str] = {}
    if not os.path.isdir(img_dir):
        return out
    for name in sorted(os.listdir(img_dir)):
        full = os.path.join(img_dir, name)
        if os.path.isfile(full) and name.lower().endswith(C.IMAGE_EXTS):
            out[name] = full
    return out


def _rec_index(rec_dir: str) -> dict[str, str]:
    """Map sourceFile -> recorded rec-envelope path (canned run, ⓲)."""
    out: dict[str, str] = {}
    if not os.path.isdir(rec_dir):
        return out
    for path in sorted(glob.glob(os.path.join(rec_dir, "*.json"))):
        out[os.path.basename(path)[:-5]] = path  # "<src>.json" -> "<src>"
    return out


def build_manifest(testset: str = C.DEFAULT_TESTSET) -> dict[str, Any]:
    ts = C.get_testset(testset)
    kind = ts["kind"]
    gt_by_src = _gt_index(ts["gtDir"])
    img_by_src = _images(ts["dir"])
    rec_by_src = _rec_index(ts["recDir"])
    excluded = ts["excluded"]
    expected = ts["expected"]
    samples: list[dict[str, Any]] = []

    all_sources = set(gt_by_src) | set(img_by_src) | set(rec_by_src) | set(excluded)
    for src in sorted(all_sources):
        has_img = src in img_by_src
        has_gt = src in gt_by_src
        has_rec = src in rec_by_src
        entry: dict[str, Any] = {
            "sourceFile": src,
            "image": os.path.relpath(img_by_src[src], C.HERE) if has_img else None,
            "gt": os.path.relpath(gt_by_src[src], C.HERE) if has_gt else None,
            "rec": os.path.relpath(rec_by_src[src], C.HERE) if has_rec else None,
        }

        if src in excluded:
            entry["status"] = "excluded"
            entry["reason"] = excluded[src]
        elif has_img and has_gt:
            entry["status"] = "active"
        elif has_gt and has_rec:
            entry["status"] = "canned"        # ⓲ runnable from recorded result, no image
        elif has_img:
            entry["status"] = "pending_gt"
        else:
            entry["status"] = "gt_orphan"

        # Enrich runnable samples (active|canned) from the loaded GT.
        if entry["status"] in ("active", "canned"):
            try:
                g = load_gt(gt_by_src[src], profile=kind)
                entry["profile"] = g["profile"]
                entry["perSampleField"] = g["perSampleField"]
                entry["rowCount"] = g["_meta"]["rowCount"]
                entry["excludedRowCount"] = g["_meta"]["excludedRowCount"]
                exp = expected.get(src)
                if exp is not None and g["_meta"]["rowCount"] != exp:
                    entry["rowCountWarning"] = f"expected {exp}"
            except GTLoadError as exc:
                entry["status"] = "gt_invalid"
                entry["error"] = str(exc)

        samples.append(entry)

    counts: dict[str, int] = {}
    for s in samples:
        counts[s["status"]] = counts.get(s["status"], 0) + 1

    return {
        "schemaVersion": "eval-manifest.v1",
        "testset": testset,
        "kind": kind,
        "runMode": ts["runMode"],
        "generatedFrom": os.path.basename(ts["dir"]),
        "testsetDir": os.path.relpath(ts["dir"], C.HERE),
        "counts": counts,
        "samples": samples,
    }


def write_manifest(manifest: dict[str, Any] | None = None,
                   testset: str = C.DEFAULT_TESTSET) -> str:
    manifest = manifest or build_manifest(testset)
    with open(C.MANIFEST_PATH, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    return C.MANIFEST_PATH


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--testset", default=C.DEFAULT_TESTSET)
    args = ap.parse_args()
    m = build_manifest(args.testset)
    path = write_manifest(m, args.testset)
    print(f"wrote {path}  (testset={m['testset']}, kind={m['kind']})")
    print(f"counts: {m['counts']}")
    for s in m["samples"]:
        line = f"  {s['status']:<11} {s['sourceFile']:<8}"
        if s["status"] in ("active", "canned"):
            line += f" rows={s.get('rowCount')} perSample={s.get('perSampleField')} ({s.get('profile')})"
        elif s["status"] == "excluded":
            line += f" — {s.get('reason')}"
        print(line)
