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
from gt_loader import GTLoadError, load_gt, load_gt_aggregate

# Angle/condition variants ("<base>-<N>.<ext>", e.g. 1-1.jpg = reshot 1.jpg)
# inherit the base document's GT (same document => same answers). The pattern
# is owned by contract (C._VARIANT_RE), shared with the checkers. qualityTags
# are NOT inferred here — they stay empty until the real condition is provided.


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


def _variant_base_map(img_by_src: dict[str, str],
                      gt_by_src: dict[str, str]) -> dict[str, str]:
    """Map variant sourceFile -> base sourceFile (whose GT it inherits).

    "1-1.jpg" -> "1.jpg", "3-2.jpg" -> "3.pdf": match the part before "-<N>"
    against the stem (extension-stripped) of a GT-backed base document. Only
    images that are NOT themselves a GT base become variants.
    """
    gt_stem = {os.path.splitext(src)[0]: src for src in gt_by_src}
    out: dict[str, str] = {}
    for name in img_by_src:
        if name in gt_by_src:
            continue
        m = C._VARIANT_RE.match(os.path.splitext(name)[0])
        if m:
            base_src = gt_stem.get(m.group("base"))
            if base_src:
                out[name] = base_src
    return out


def _images_nested(img_dir: str) -> dict[str, str]:
    """Map relative-path key ('<subfolder>/<file>.jpg') -> image path, walking
    nested dirs. Key uses forward slashes so it matches the aggregate GT keys
    (war: separate_img_path relative to the month folder)."""
    out: dict[str, str] = {}
    if not os.path.isdir(img_dir):
        return out
    for root, _dirs, files in os.walk(img_dir):
        for name in files:
            if not name.lower().endswith(C.IMAGE_EXTS):
                continue
            full = os.path.join(root, name)
            key = os.path.relpath(full, img_dir).replace("\\", "/")
            out[key] = full
    return out


def _build_manifest_aggregate(testset: str, ts: dict[str, Any]) -> dict[str, Any]:
    """Manifest for a war/ETL thin testset: ONE aggregate GT file + nested images.

    Pairing key = relative image path ('<subfolder>/<file>.jpg'). sourceFile =
    filesystem-safe id (slash->__) used for result/snapshot filenames; the original
    key is carried as `gtKey` so compare_run can look it up in the preloaded
    aggregate. Only images actually on disk become `active` — drop a sample of
    images in and exactly those run (the rest stay `gt_orphan`, never run)."""
    kind = ts["kind"]
    agg = load_gt_aggregate(ts["gtAggregate"], profile=kind)   # {gtKey: loaded-gt}
    img_by_key = _images_nested(ts["dir"])
    gt_rel = os.path.relpath(ts["gtAggregate"], C.HERE)
    samples: list[dict[str, Any]] = []
    for key in sorted(set(agg) | set(img_by_key)):
        has_img = key in img_by_key
        has_gt = key in agg
        entry: dict[str, Any] = {
            "sourceFile": C.safe_sample_id(key),     # flat, filesystem-safe
            "gtKey": key,                            # original aggregate key
            "image": os.path.relpath(img_by_key[key], C.HERE) if has_img else None,
            "gt": gt_rel if has_gt else None,        # the aggregate file (shared)
            "rec": None,
        }
        if has_img and has_gt:
            entry["status"] = "active"
        elif has_img:
            entry["status"] = "pending_gt"
        else:
            entry["status"] = "gt_orphan"
        if entry["status"] == "active":
            g = agg[key]
            entry["profile"] = g["profile"]
            entry["perSampleField"] = g["perSampleField"]
            entry["rowCount"] = g["_meta"]["rowCount"]
            entry["excludedRowCount"] = g["_meta"]["excludedRowCount"]
        samples.append(entry)

    counts: dict[str, int] = {}
    for s in samples:
        counts[s["status"]] = counts.get(s["status"], 0) + 1
    return {
        "schemaVersion": "eval-manifest.v1",
        "testset": testset,
        "kind": kind,
        "runMode": ts["runMode"],
        "gtAggregate": gt_rel,            # signals compare_run to use the aggregate loader
        "generatedFrom": os.path.basename(ts["dir"]),
        "testsetDir": os.path.relpath(ts["dir"], C.HERE),
        "counts": counts,
        "samples": samples,
    }


def build_manifest(testset: str = C.DEFAULT_TESTSET) -> dict[str, Any]:
    ts = C.get_testset(testset)
    if ts.get("gtAggregate"):
        return _build_manifest_aggregate(testset, ts)
    kind = ts["kind"]
    gt_by_src = _gt_index(ts["gtDir"])
    img_by_src = _images(ts["dir"])
    rec_by_src = _rec_index(ts["recDir"])
    variant_base = _variant_base_map(img_by_src, gt_by_src)
    excluded = ts["excluded"]
    expected = ts["expected"]
    samples: list[dict[str, Any]] = []

    all_sources = set(gt_by_src) | set(img_by_src) | set(rec_by_src) | set(excluded)
    for src in sorted(all_sources):
        has_img = src in img_by_src
        is_variant = src in variant_base
        base_src = variant_base.get(src)
        # A variant inherits its base document's GT (same document, same answers).
        gt_path = gt_by_src.get(base_src) if is_variant else gt_by_src.get(src)
        has_gt = gt_path is not None
        has_rec = src in rec_by_src
        entry: dict[str, Any] = {
            "sourceFile": src,
            "image": os.path.relpath(img_by_src[src], C.HERE) if has_img else None,
            "gt": os.path.relpath(gt_path, C.HERE) if has_gt else None,
            "rec": os.path.relpath(rec_by_src[src], C.HERE) if has_rec else None,
        }
        if is_variant:
            entry["variantOf"] = base_src

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
                g = load_gt(gt_path, profile=kind)
                entry["profile"] = g["profile"]
                entry["perSampleField"] = g["perSampleField"]
                entry["rowCount"] = g["_meta"]["rowCount"]
                entry["excludedRowCount"] = g["_meta"]["excludedRowCount"]
                exp = expected.get(base_src if is_variant else src)
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
