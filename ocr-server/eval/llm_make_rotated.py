"""llm_make_rotated — 원본을 Base 가 적용한 각도로만 돌려 저장한다(리사이즈 없음).

왜 필요한가: Base 전처리본을 VLM 에 먹였더니 오히려 나빠졌다(cell −10.2%p · itemName −22%p).
원인은 방향이 아니라 **950px 리사이즈**다. 950 은 Paddle det 이 촘촘한 표의 행을 병합하지 않는
한계값이라 글자를 희생해 잡은 값이고(runtime_config: 1400 에서 dense 표 77→12%), VLM 은 det 을
쓰지 않으므로 그 희생이 손해로만 남는다.

그래서 **방향만 Base 와 같게 맞추고 해상도는 원본 그대로**인 입력을 만든다. 이게 실제 제품 구성
("방향 보정 + VLM")에 해당한다.

각도는 run_meta 의 orientAngle 을 쓰지 않는다 - 그 필드는 실제 적용 결과와 어긋나는 문서가 있다
(2501__10006: angle=0 인데 처리본은 90도 돌아 있다). 대신 **처리본과 직접 맞춰** 정한다:
원본을 0/90/180/270 으로 돌려 축소한 뒤 처리본 축소본과 픽셀 상관을 재고 가장 잘 맞는 각을 쓴다.
치수만으로는 90 과 270 을 못 가르므로 상관까지 본다.

CLI:
    python eval/llm_make_rotated.py \\
        --sources eval/LLM/data/sample_500_sources.txt \\
        --groups eval/LLM/data/groups_072.json \\
        --processed eval/runs/072_20260802_182127/processed \\
        --out eval/runs/072_20260802_182127/rotated \\
        --list eval/LLM/inputs/sample_500r.txt
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
SERVER = os.path.dirname(HERE)
CMP_PX = 96          # 각도 맞추기용 축소 크기. 작을수록 빠르고 노이즈에 둔감하다
JPEG_Q = 95          # 원본 화질을 지키는 것이 이 파일의 목적이라 높게 둔다
ANGLES = (0, 90, 180, 270)


def _gray(im, size):
    """비교용 축소 그레이스케일. 밝기 차를 없애려 평균 0 으로 맞춘다."""
    g = im.convert("L").resize(size, 1)          # 1 = BILINEAR
    px = list(g.getdata())
    m = sum(px) / len(px)
    return [p - m for p in px]


def best_angle(orig, proc) -> tuple[int, float]:
    """원본을 어느 각도로 돌려야 처리본과 같은 그림이 되나. (각도, 상관) 반환."""
    pw, ph = proc.size
    size = (CMP_PX, max(1, round(CMP_PX * ph / pw)))
    ref = _gray(proc, size)
    ref_n = sum(v * v for v in ref) ** 0.5 or 1.0
    best, best_r = 0, -2.0
    for a in ANGLES:
        rot = orig if a == 0 else orig.rotate(-a, expand=True)   # PIL 은 반시계라 부호를 뒤집는다
        if (rot.size[0] > rot.size[1]) != (pw > ph):
            continue                                             # 가로/세로가 다르면 그 각은 아니다
        cur = _gray(rot, size)
        n = sum(v * v for v in cur) ** 0.5 or 1.0
        r = sum(x * y for x, y in zip(ref, cur)) / (ref_n * n)
        if r > best_r:
            best, best_r = a, r
    return best, best_r


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sources", required=True, help="sourceFile 목록 txt")
    ap.add_argument("--groups", required=True, help="groups_072.json (docs[].imagePath)")
    ap.add_argument("--processed", required=True, help="Base 전처리 결과 이미지 폴더")
    ap.add_argument("--out", required=True, help="회전본 저장 폴더")
    ap.add_argument("--list", dest="listpath", required=True, help="러너용 경로 목록 출력")
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()

    from PIL import Image

    docs = json.load(io.open(a.groups, encoding="utf-8"))["docs"]
    srcs = [l.strip() for l in io.open(a.sources, encoding="utf-8") if l.strip()]
    if a.limit:
        srcs = srcs[:a.limit]
    os.makedirs(a.out, exist_ok=True)

    stats = {ang: 0 for ang in ANGLES}
    weak, miss, lines = [], [], []
    for i, src in enumerate(srcs, 1):
        g = docs.get(src) or {}
        # imagePath 는 eval/ 기준 상대경로다(러너 --list 와 같은 규약).
        op = g.get("imagePath") or ""
        if op and not os.path.isabs(op):
            op = next((c for c in (os.path.join(HERE, op), os.path.join(SERVER, op), op)
                       if os.path.exists(c)), op)
        pp = next((os.path.join(a.processed, src + e) for e in ("", ".jpg", ".png")
                   if os.path.exists(os.path.join(a.processed, src + e))), None)
        if not op or not os.path.exists(op) or not pp:
            miss.append(src)
            continue
        with Image.open(op) as orig, Image.open(pp) as proc:
            orig = orig.convert("RGB")
            ang, r = best_angle(orig, proc)
            out = orig if ang == 0 else orig.rotate(-ang, expand=True)
            out.save(os.path.join(a.out, src + ".jpg"), "JPEG", quality=JPEG_Q, optimize=True)
        stats[ang] += 1
        if r < 0.5:
            weak.append((src, ang, round(r, 3)))
        lines.append(os.path.relpath(os.path.join(a.out, src + ".jpg"), HERE).replace("\\", "/"))
        if i % 100 == 0:
            print("  %d/%d" % (i, len(srcs)))

    with open(a.listpath, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")

    print("\n회전본 %d장 -> %s" % (len(lines), a.out))
    print("각도 분포:", {k: v for k, v in stats.items() if v})
    print("상관 낮음(<0.5) %d장" % len(weak))
    for s, ang, r in weak[:10]:
        print("   %-46s %3d도 r=%.3f" % (s[:46], ang, r))
    if miss:
        print("원본/처리본 없음 %d장:" % len(miss), miss[:5])
    print("목록:", a.listpath)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
