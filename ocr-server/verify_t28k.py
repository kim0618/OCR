"""
T-28k offline verification:
For TPL-31D13CF3 + 1.jpg / 1-1.jpg, run the full OCR + homography pipeline
exactly like main.py and apply the proposed T-28k OCR-line nearest matching
to each non-table field, printing value + bbox center offset.

Run:
  d:/Free_Vue/OCR/ocr-server/.venv/Scripts/python.exe d:/Free_Vue/OCR/ocr-server/verify_t28k.py
"""
import os
import sys
import json
import time
import base64
import re

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from extractors.ocr_lines import _parse_ocr_lines  # type: ignore
from preprocess import detect_orientation  # type: ignore
from main import get_ocr_engine  # type: ignore


TEMPLATES_JSON = os.path.join(HERE, "data", "templates.json")
TARGET_TEMPLATE_ID = "TPL-31D13CF3"

CASES = [
    ("1.jpg", r"d:\Free_Vue\OCR\mysuit-ocr\public\data\testsets\invoice_statement\1.jpg"),
    ("1-1.jpg", r"d:\Free_Vue\OCR\mysuit-ocr\public\data\testsets\invoice_statement\1\1-1.jpg"),
]


def load_template():
    with open(TEMPLATES_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)
    for t in data:
        if t.get("template_id") == TARGET_TEMPLATE_ID:
            return t.get("template_json") or {}
    raise SystemExit(f"template {TARGET_TEMPLATE_ID} not found")


def text_anchor_homography(tmpl_ocr_lines, ref_ocr, ref_w, ref_h_dim):
    from collections import Counter as _Ctr
    if not (ref_w > 0 and ref_h_dim > 0 and len(ref_ocr) >= 6 and len(tmpl_ocr_lines) >= 6):
        return None, "skip_no_ref"
    _rc = _Ctr(x["text"] for x in ref_ocr)
    _ridx = {x["text"]: (x["cx"], x["cy"]) for x in ref_ocr
             if _rc[x["text"]] == 1 and len(x["text"]) >= 2}
    _uc = _Ctr(t for _, t, _ in tmpl_ocr_lines)
    _pts_r, _pts_s = [], []
    for _pu, _tu, _cu in tmpl_ocr_lines:
        if _cu < 0.6 or not _tu or len(_tu) < 2:
            continue
        if _uc[_tu] != 1 or _tu not in _ridx:
            continue
        _xu = [p[0] for p in _pu]
        _yu = [p[1] for p in _pu]
        _pts_s.append([(min(_xu) + max(_xu)) / 2, (min(_yu) + max(_yu)) / 2])
        _pts_r.append(list(_ridx[_tu]))
    print(f"  matches={len(_pts_r)}")
    if len(_pts_r) < 6:
        return None, f"too_few_matches={len(_pts_r)}"
    _H2, _msk2 = cv2.findHomography(
        np.float32(_pts_s).reshape(-1, 1, 2),
        np.float32(_pts_r).reshape(-1, 1, 2),
        cv2.RANSAC, 10.0,
    )
    _ni2 = int(_msk2.sum()) if _msk2 is not None else 0
    print(f"  RANSAC inliers={_ni2}/{len(_pts_r)}")
    if _H2 is None or _ni2 < 6:
        return None, f"ransac_failed inliers={_ni2}"
    return _H2, f"ok inliers={_ni2}"


def transform_lines(lines, H):
    out = []
    for pts, txt, cf in lines:
        new_pts = []
        for (x, y) in pts:
            p = H @ np.array([float(x), float(y), 1.0])
            new_pts.append((p[0] / p[2], p[1] / p[2]))
        out.append((new_pts, txt, cf))
    return out


def t28k_match(region, warped_lines):
    rx = float(region.get("x", 0))
    ry = float(region.get("y", 0))
    rw = float(region.get("width", 0))
    rh = float(region.get("height", 0))
    cx = rx + rw / 2.0
    cy = ry + rh / 2.0
    y_tol = max(rh * 2.0, 60.0)

    best = (float("inf"), "", 0.0, [int(rx), int(ry), int(rw), int(rh)], None)
    for pts, txt, cf in warped_lines:
        if not txt or cf < 0.3:
            continue
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        wcx = (min(xs) + max(xs)) / 2
        wcy = (min(ys) + max(ys)) / 2
        if not (rx <= wcx <= rx + rw):
            continue
        if not (cy - y_tol <= wcy <= cy + y_tol):
            continue
        dist = abs(wcx - cx) + abs(wcy - cy)
        if dist < best[0]:
            best = (
                dist, txt, cf,
                [int(min(xs)), int(min(ys)), int(max(xs) - min(xs)), int(max(ys) - min(ys))],
                wcy - cy,
            )
    return best  # (dist, text, conf, bbox, dy)


def main():
    tj = load_template()
    img_meta = tj.get("image") or {}
    ref_w = int(img_meta.get("width") or 0)
    ref_h = int(img_meta.get("height") or 0)
    ref_ocr = tj.get("referenceOcr") or []
    regions = tj.get("regions") or []
    field_regions = [r for r in regions if r.get("fieldType") != "table"]
    print(f"Template {TARGET_TEMPLATE_ID}: image={ref_w}x{ref_h} regions={len(regions)} (fields={len(field_regions)}) refOcr={len(ref_ocr)}")

    print("\nLoading PaddleOCR engine ...")
    ocr = get_ocr_engine()

    for case_name, path in CASES:
        print("\n=========================")
        print(f"CASE: {case_name}  ({path})")
        if not os.path.exists(path):
            print("  MISSING file, skip")
            continue
        img = cv2.imread(path)
        if img is None:
            print("  cv2.imread failed, skip")
            continue
        h0, w0 = img.shape[:2]
        print(f"  loaded {w0}x{h0}")

        t0 = time.time()
        img, orient_meta = detect_orientation(
            img, ocr, original_wh=(w0, h0),
            target_short=512, skip_second_pass=True,
        )
        print(f"  detect_orientation: angle={orient_meta.get('angle', 0)} ({(time.time()-t0)*1000:.0f}ms)")

        t1 = time.time()
        lines = list(_parse_ocr_lines(ocr.ocr(img)))
        print(f"  full OCR: {len(lines)} lines ({(time.time()-t1)*1000:.0f}ms)")

        t2 = time.time()
        H, status = text_anchor_homography(lines, ref_ocr, ref_w, ref_h)
        print(f"  homography: {status} ({(time.time()-t2)*1000:.0f}ms)")
        if H is None:
            print("  no homography → cannot run T-28k for this case")
            continue
        img = cv2.warpPerspective(img, H, (ref_w, ref_h))
        warped_lines = transform_lines(lines, H)
        print(f"  warped lines: {len(warped_lines)} in template space")

        print("\n  --- T-28k field results ---")
        for r in field_regions:
            name = r.get("name", "?")
            ko = r.get("koField", "")
            dist, txt, cf, bbox, dy = t28k_match(r, warped_lines)
            if not txt:
                marker = "EMPTY (fallback bbox=template)"
                dy_str = "-"
            else:
                marker = ""
                dy_str = f"dy={dy:+.0f}px"
            print(f"  {name:>8} [{ko}]  -> {txt!r}  conf={cf:.3f}  bbox={bbox}  {dy_str}  {marker}")


if __name__ == "__main__":
    main()
