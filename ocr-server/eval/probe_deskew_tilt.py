"""probe_deskew_tilt — P0 계측 (PREPROCESS_DESKEW_PLAN §5 P0).

스냅샷의 OCR 텍스트 bbox에서 *실제* 텍스트라인 기울기(잔여tilt)를 재고,
deskew가 보고한 각도(테두리 락온이면 ≈0)와 셀 정확도를 나란히 놓아
"전처리(미보정 tilt)가 변주 셀하락의 원인"인지 상관으로 확인한다.

이미지·서버·device 불필요(스냅샷 bbox만 사용, 읽기전용). 전처리 적용 *후* OCR
입력의 잔여 기울기를 재므로, deskew가 스킵한 진짜 tilt가 그대로 잡힌다.

CLI:  python eval/probe_deskew_tilt.py [--ts <run_ts>]
"""
from __future__ import annotations
import argparse, json, math, os, statistics
import contract as C


def _line_angle(bbox) -> float | None:
    """상단 엣지(좌상→우상) 기울기(deg, [-45,45]). 텍스트라인 방향."""
    try:
        (x0, y0), (x1, y1) = bbox[0], bbox[1]
    except Exception:
        return None
    dx, dy = (x1 - x0), (y1 - y0)
    if abs(dx) < 1e-6 and abs(dy) < 1e-6:
        return None
    a = math.degrees(math.atan2(dy, dx))
    while a > 45:
        a -= 90
    while a < -45:
        a += 90
    return a


def _residual_tilt(snap: dict) -> tuple[float | None, int]:
    angs = []
    for ln in (snap.get("ocr_lines_raw") or []):
        try:
            bbox, text, conf = ln[0], ln[1], ln[2]
        except Exception:
            continue
        if not text or float(conf) < 0.5:
            continue
        a = _line_angle(bbox)
        if a is not None:
            angs.append(a)
    if len(angs) < 4:
        return None, len(angs)
    return round(statistics.median(angs), 3), len(angs)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ts", default=None)
    ap.add_argument("--testset", default=C.DEFAULT_TESTSET)
    args = ap.parse_args()
    run_dir = os.path.join(C.RUNS_DIR, args.ts) if args.ts else C.latest_run(args.testset)
    study = os.path.join(run_dir, "study")
    snap_dir = os.path.join(study, "snapshots")
    cmp = {s["sourceFile"]: s for s in json.load(open(os.path.join(study, "compare_summary.json"), encoding="utf-8"))["samples"]}

    def _deskew_ang(src):
        try:
            d = json.load(open(os.path.join(study, "samples", src + ".json"), encoding="utf-8"))
            return ((d.get("preprocess") or {}).get("deskew") or {}).get("normalizedAngle")
        except Exception:
            return None

    rows = []
    for f in sorted(os.listdir(snap_dir)):
        if not f.endswith(".json"):
            continue
        src = f[:-5]
        snap = json.load(open(os.path.join(snap_dir, f), encoding="utf-8"))
        tilt, n = _residual_tilt(snap)
        s = cmp.get(src, {})
        is_variant = "-" in src.split(".")[0]
        rows.append({
            "src": src, "variant": is_variant,
            "deskew_reported": _deskew_ang(src),
            "residual_tilt": tilt, "n_lines": n,
            "cell": round(s.get("cellAcc", 0) * 100, 1),
            "rows": f"{s.get('rowsGt','?')}/{s.get('rowsExt','?')}",
            "path": s.get("path", "?"),
        })

    print(f"run = {os.path.relpath(run_dir, C.RUNS_DIR)}\n")
    print(f"{'img':9} {'grp':4} {'deskew_rpt':>10} {'true_tilt':>9} {'|tilt|':>6} {'cell%':>6} {'rows':>7} {'path':>8}")
    for r in sorted(rows, key=lambda r: (-(abs(r["residual_tilt"]) if r["residual_tilt"] is not None else -1))):
        t = r["residual_tilt"]
        at = f"{abs(t):.2f}" if t is not None else "  ?"
        print(f"{r['src']:9} {'VAR' if r['variant'] else 'base':4} "
              f"{str(r['deskew_reported']):>10} {str(t):>9} {at:>6} {r['cell']:>6} {r['rows']:>7} {r['path']:>8}")

    # 상관: |잔여tilt| vs 셀 (변주만, tilt 측정된 것)
    pairs = [(abs(r["residual_tilt"]), r["cell"]) for r in rows if r["residual_tilt"] is not None]
    if len(pairs) >= 3:
        xs = [p[0] for p in pairs]; ys = [p[1] for p in pairs]
        mx, my = statistics.mean(xs), statistics.mean(ys)
        cov = sum((x-mx)*(y-my) for x, y in pairs)
        vx = sum((x-mx)**2 for x in xs); vy = sum((y-my)**2 for y in ys)
        r_pearson = cov / (math.sqrt(vx*vy)) if vx > 0 and vy > 0 else 0.0
        hi = [c for t, c in pairs if t >= 1.0]; lo = [c for t, c in pairs if t < 1.0]
        print(f"\n상관(|tilt| vs cell) Pearson r = {r_pearson:.3f}  (음수=기울수록 셀↓ = 전처리 원인)")
        if hi and lo:
            print(f"  |tilt|≥1.0° 그룹 평균 셀 = {statistics.mean(hi):.1f}%  (n={len(hi)})")
            print(f"  |tilt|<1.0° 그룹 평균 셀 = {statistics.mean(lo):.1f}%  (n={len(lo)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
