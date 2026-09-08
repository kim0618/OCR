"""llm_orient_audit — 전처리가 실제로 글자를 바로 세웠는지 OCR 박스 모양으로 채점한다.

"우리 회전이 옳았나" 는 우리 회전 판정기의 출력(angle · allScores)으로는 못 가린다.
그 판정기로 그 판정기를 채점하는 순환이다. 실제로 파일 치수(가로/세로)를 신호로 썼다가
같은 "세로 파일 + 90° 적용" 이 한쪽은 성공, 한쪽은 실패로 갈리는 걸 확인했다.

밖에서 답을 가져온다 - **전처리 결과물에서 뽑힌 OCR 라인 박스의 모양**이다.
한국어 문서는 가로쓰기라 글자가 바로 서 있으면 라인 박스가 가로로 길다(폭>높이).
전처리 후 이미지에서 세로로 긴 박스가 대부분이면 그 이미지는 누워 있는 것이고,
곧 우리 회전이 틀린 것이다. 판정 대상이 결과물이라 순환이 없다.

CLI:
    python eval/llm_orient_audit.py --snapshots eval/runs/070_.../snapshots \\
        --cases eval/LLM/data/cases_qwen_500.json
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys

try:
    from PIL import Image
except ImportError:                                    # noqa: BLE001
    Image = None

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
MIN_LINES = 8          # 라인이 너무 적으면 방향을 논할 수 없다
LAND_RATIO = 0.60      # 가로 박스가 이 비율 이상이면 '바로 섬'


def box_orient(snap_path: str) -> dict:
    """전처리 후 이미지의 OCR 라인 박스로 방향을 판정한다."""
    try:
        with io.open(snap_path, encoding="utf-8") as fh:
            d = json.load(fh)
    except Exception:                                  # noqa: BLE001
        return {}
    lines = d.get("ocr_lines_raw") or []
    wide = tall = 0
    for ln in lines:
        try:
            pts = ln[0]
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            w, h = max(xs) - min(xs), max(ys) - min(ys)
        except Exception:                              # noqa: BLE001
            continue
        if w <= 0 or h <= 0:
            continue
        # 정사각에 가까운 것(한 글자짜리)은 방향 정보가 없다 - 뺀다
        if 0.7 < w / h < 1.4:
            continue
        if w > h:
            wide += 1
        else:
            tall += 1
    n = wide + tall
    if n < MIN_LINES:
        return {"boxLines": n, "boxVerdict": "판정불가"}
    ratio = wide / n
    return {"boxLines": n, "boxWideRatio": round(ratio, 3),
            "boxVerdict": "바로 섬" if ratio >= LAND_RATIO else "누워 있음"}


def _side(path_dir: str, src: str):
    """이미지 한 장의 가로/세로. 파일이 없거나 정사각에 가까우면 None."""
    if Image is None or not path_dir:
        return None
    for ext in ("", ".jpg", ".png", ".jpeg"):
        p = os.path.join(path_dir, src + ext)
        if os.path.exists(p):
            try:
                with Image.open(p) as im:
                    w, h = im.size
            except Exception:                          # noqa: BLE001
                return None
            if 0.9 < w / h < 1.1:                      # 정사각은 방향 정보가 없다
                return None
            return "가로" if w > h else "세로"
    return None


def model_sideways(processed_dir: str, model_dir: str, src: str, orig_path: str | None = None):
    """모델이 우리 것과 90도 어긋난 그림을 봤는가.

    러너는 VLM 에 원본을 그대로 먹인다. 우리 처리본은 박스 감사로 이미 '바로 섬' 이 확인됐으므로,
    같은 문서의 두 그림이 가로/세로로 갈리면 모델 쪽이 누운 것이다.
    run_meta 의 angle 은 여기서 못 쓴다 - angle=0 인데 90도 어긋난 문서가 실제로 있다
    (2501__10006: base 950x670 vs model 969x1400).
    180도 뒤집힘은 이 방법으로 못 잡는다 - 치수가 같기 때문이다.
    """
    a, b = _side(processed_dir, src), _side(model_dir, src)
    if b is None and orig_path and os.path.exists(orig_path):
        # 모델 그림이 없으면 원본 치수를 쓴다. 러너는 원본을 그대로 보내고 프로세서는 리사이즈만 하므로
        # 가로/세로는 원본과 같다 - 156장에서 두 방법이 전부 일치하는 것을 확인했다.
        b = _side(os.path.dirname(orig_path), os.path.basename(orig_path))
    if a is None or b is None:
        return None
    return a != b


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshots", required=True, help="Base 스냅샷 폴더(전처리 후 OCR 결과)")
    ap.add_argument("--cases", required=True, help="compare_cross --out JSON")
    ap.add_argument("--processed", help="Base 전처리 결과 이미지 폴더")
    ap.add_argument("--model-view", dest="model_view", help="VLM 이 실제로 본 이미지 폴더")
    ap.add_argument("--write", action="store_true", help="cases JSON 에 판정을 써 넣는다")
    args = ap.parse_args()

    data = json.load(io.open(args.cases, encoding="utf-8"))
    docs = data["docs"]
    miss = 0
    for d in docs:
        p = os.path.join(args.snapshots, d["sourceFile"] + ".json")
        v = box_orient(p)
        if not v:
            miss += 1
        d.update(v)
        # 최종 원인: 전처리 결과가 누워 있으면 실패, 서 있으면 정상
        verdict = d.get("boxVerdict")
        differ = model_sideways(args.processed, args.model_view, d["sourceFile"], d.get("imagePath"))
        # differ 는 '두 그림의 가로/세로가 다르다' 일 뿐이다. 모델이 누웠는지는 Base 가 서 있었는지에 달렸다:
        #   Base 바로 섬 · 다르다  -> 모델이 누움
        #   Base 누워 있음 · 다르다 -> 모델은 서 있음   (이걸 뒤집지 않아 VLM 승과 둘 다 실패가 서로 바뀌어 있었다)
        if differ is None or verdict not in ("바로 섬", "누워 있음"):
            sw = None
        else:
            sw = differ if verdict == "바로 섬" else (not differ)
        d["modelSideways"] = sw
        if verdict == "누워 있음":
            d["orientCause"] = "Base 전처리 실패 - 우리가 눕힘"
        elif verdict == "바로 섬":
            if sw is None:
                d["orientCause"] = "모델 그림 없음"
            else:
                d["orientCause"] = ("모델 전처리 실패 - 누운 원본 그대로 봄" if sw
                                    else "둘 다 정상 - 원본이 서 있음")
        else:
            d["orientCause"] = "판정불가"

    agg = {}
    for d in docs:
        k = (d["class"], d["orientCause"])
        a = agg.setdefault(k, [0, 0])
        a[0] += 1
        a[1] += d.get("cellMove") or 0
    print(f"문서 {len(docs)} · 스냅샷 없음 {miss}")
    print("%-11s %-30s %5s %9s" % ("부류", "전처리 판정", "문서", "셀순증"))
    for (c, o), (n, mv) in sorted(agg.items(), key=lambda t: (t[0][0], -t[1][0])):
        print("%-11s %-30s %5d %+9d" % (c, o, n, mv))

    if args.write:
        io.open(args.cases, "w", encoding="utf-8", newline="\n").write(
            json.dumps(data, ensure_ascii=False, indent=1))
        print("\n→ " + args.cases)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
