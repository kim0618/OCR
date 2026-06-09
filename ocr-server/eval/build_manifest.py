"""build_manifest — auto-pair images with GT files into eval/manifest.json.

Pairing key = GT's top-level `sourceFile`. Status per sample:
  active      image present AND GT present (loads under contract)
  pending_gt  image present, no GT yet
  gt_orphan   GT present, image missing
  excluded    deliberately dropped (contract.EXCLUDED_SOURCES, e.g. 2.pdf)

Measurement-only: reads the testset, writes ONLY eval/manifest.json.
"""

from __future__ import annotations

import glob
import json
import os
from typing import Any

import contract as C
from gt_loader import GTLoadError, load_gt


def _gt_index() -> dict[str, str]:
    """Map sourceFile -> GT file path, by reading each GT's sourceFile."""
    index: dict[str, str] = {}
    for path in sorted(glob.glob(os.path.join(C.GT_DIR, "*.json"))):
        try:
            with open(path, encoding="utf-8") as fh:
                src = json.load(fh).get("sourceFile")
        except (OSError, json.JSONDecodeError):
            continue
        if src:
            index.setdefault(src, path)
    return index


def _images() -> dict[str, str]:
    """Map sourceFile (basename) -> image path for files in IMG_DIR."""
    out: dict[str, str] = {}
    for name in sorted(os.listdir(C.IMG_DIR)):
        full = os.path.join(C.IMG_DIR, name)
        if os.path.isfile(full) and name.lower().endswith(C.IMAGE_EXTS):
            out[name] = full
    return out


def build_manifest() -> dict[str, Any]:
    gt_by_src = _gt_index()
    img_by_src = _images()
    samples: list[dict[str, Any]] = []

    all_sources = set(gt_by_src) | set(img_by_src) | set(C.EXCLUDED_SOURCES)
    for src in sorted(all_sources):
        has_img = src in img_by_src
        has_gt = src in gt_by_src
        entry: dict[str, Any] = {
            "sourceFile": src,
            "image": os.path.relpath(img_by_src[src], C.HERE) if has_img else None,
            "gt": os.path.relpath(gt_by_src[src], C.HERE) if has_gt else None,
        }

        if src in C.EXCLUDED_SOURCES:
            entry["status"] = "excluded"
            entry["reason"] = C.EXCLUDED_SOURCES[src]
        elif has_img and has_gt:
            entry["status"] = "active"
        elif has_img:
            entry["status"] = "pending_gt"
        else:
            entry["status"] = "gt_orphan"

        # Enrich active samples from the loaded GT (and surface load failures).
        if entry["status"] == "active":
            try:
                g = load_gt(gt_by_src[src])
                entry["profile"] = g["profile"]
                entry["perSampleField"] = g["perSampleField"]
                entry["rowCount"] = g["_meta"]["rowCount"]
                entry["excludedRowCount"] = g["_meta"]["excludedRowCount"]
                exp = C.EXPECTED_ROWS.get(src)
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
        "generatedFrom": os.path.basename(C.TESTSET_DIR),
        "testsetDir": os.path.relpath(C.TESTSET_DIR, C.HERE),
        "counts": counts,
        "samples": samples,
    }


def write_manifest(manifest: dict[str, Any] | None = None) -> str:
    manifest = manifest or build_manifest()
    with open(C.MANIFEST_PATH, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    return C.MANIFEST_PATH


if __name__ == "__main__":
    m = build_manifest()
    path = write_manifest(m)
    print(f"wrote {path}")
    print(f"counts: {m['counts']}")
    for s in m["samples"]:
        line = f"  {s['status']:<11} {s['sourceFile']:<8}"
        if s["status"] == "active":
            line += f" rows={s.get('rowCount')} perSample={s.get('perSampleField')} ({s.get('profile')})"
        elif s["status"] == "excluded":
            line += f" — {s.get('reason')}"
        print(line)
