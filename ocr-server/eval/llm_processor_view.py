"""llm_processor_view — VLM 이 실제로 본 이미지(프로세서 뷰)를 재현해 저장한다.

카드 셋째 판의 재료다. 리사이즈·타일링은 vLLM 안에서 일어나 클라이언트가 받을 수 없지만,
같은 모델의 preprocessor_config.json 을 AutoProcessor 로 물리면 **결정적으로 재현된다** -
추론 결과가 아니라 원본 이미지 + 모델 설정만의 함수라 run 을 다시 돌릴 필요가 없다.

GPU 를 쓰지 않는다(리사이즈·정규화뿐, 가중치도 안 읽는다). vLLM 서버를 띄운 채 병행해도 된다.
다만 RAM 15GB 를 vLLM 과 나눠 쓰므로 한 장씩 처리하고 바로 버린다.

셋째 판의 관전 포인트는 **화질**이다 - 작은 글씨가 뭉개져 있으면 그게 VLM 실패의 원인이다.
같이 찍는 비전 토큰 수는 계획서 스모크 게이트 ④(실제 적용 해상도) 를 채우는 값이기도 하다.

CLI:
    python eval/llm_processor_view.py --model Qwen/Qwen3-VL-4B-Instruct \\
        --list eval/LLM/data/cases_sources.txt --out eval/runs/vlm_qwen_500/model_view
    python eval/llm_processor_view.py --model ... --cases eval/LLM/data/cases.json --out ...
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
REPLAY = os.path.join(HERE, "data", "invoice_war", "images_replay")


def source_to_path(src: str) -> str | None:
    """2501__10006__NAME.jpg -> images_replay/2501/10006/NAME.jpg"""
    parts = src.split("__")
    if len(parts) < 3:
        return None
    p = os.path.join(REPLAY, parts[0], parts[1], "__".join(parts[2:]))
    return p if os.path.exists(p) else None


def to_image(pixel_values, grid_thw=None, ip=None):
    """프로세서가 낸 텐서를 눈으로 볼 수 있는 이미지로 되돌린다.

    Qwen 계열은 패치를 **merge 블록 단위로 재배열해** 평탄화한다 - 단순 reshape 으로는
    안 돌아온다. 정방향(Qwen2VLImageProcessor)이
        (grid_t, T, C, gh//m, m, ph, gw//m, m, pw) --transpose(0,3,6,4,7,2,1,5,8)-->
        (grid_t*gh*gw, C*T*ph*pw)
    이므로 그 역치환 [0,6,5,1,3,7,2,4,8] 로 되돌린다.
    타일 방식(InternVL 등)은 (타일, C, H, W) 로 와서 세로로 이어 붙인다.
    """
    import numpy as np
    from PIL import Image

    a = pixel_values
    if hasattr(a, "numpy"):
        a = a.detach().cpu().numpy()
    a = np.asarray(a, dtype="float32")
    while a.ndim > 4 and a.shape[0] == 1:
        a = a[0]

    if a.ndim == 2 and grid_thw is not None and ip is not None:
        g = np.asarray(grid_thw).reshape(-1, 3)[0]
        gt, gh, gw = int(g[0]), int(g[1]), int(g[2])
        ps = int(getattr(ip, "patch_size", 16))
        tp = int(getattr(ip, "temporal_patch_size", 2))
        m = int(getattr(ip, "merge_size", 2))
        c = a.shape[1] // (tp * ps * ps)
        if c * tp * ps * ps != a.shape[1] or gt * gh * gw != a.shape[0]:
            return None
        a = a.reshape(gt, gh // m, gw // m, m, m, c, tp, ps, ps)
        a = a.transpose(0, 6, 5, 1, 3, 7, 2, 4, 8)      # 역치환
        a = a.reshape(gt * tp, c, gh * ps, gw * ps)[0]   # 첫 프레임만
        a = np.transpose(a, (1, 2, 0))
    elif a.ndim == 4:                       # (타일, C, H, W) - 세로로 이어 붙인다
        if a.shape[1] not in (1, 3):
            return None
        a = np.concatenate([np.transpose(t, (1, 2, 0)) for t in a], axis=0)
    elif a.ndim == 3 and a.shape[0] in (1, 3):
        a = np.transpose(a, (1, 2, 0))
    else:
        return None

    mean = np.asarray(getattr(ip, "image_mean", [0.5, 0.5, 0.5]), dtype="float32")
    std = np.asarray(getattr(ip, "image_std", [0.5, 0.5, 0.5]), dtype="float32")
    if a.shape[-1] == mean.shape[0]:
        a = a * std + mean               # 정규화 역산 - 원래 밝기를 되살린다
    else:
        lo, hi = float(a.min()), float(a.max())
        a = (a - lo) / (hi - lo + 1e-8)
    if a.shape[-1] == 1:
        a = np.repeat(a, 3, axis=-1)
    return Image.fromarray((a * 255).clip(0, 255).astype("uint8"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, help="HF repo id (프로세서만 읽는다)")
    ap.add_argument("--list", help="sourceFile 목록 txt")
    ap.add_argument("--cases", help="compare_cross --out JSON (docs[].sourceFile 사용)")
    ap.add_argument("--out", required=True, help="저장 폴더")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--max-side", type=int, default=1400, help="저장 시 긴 변 상한(용량)")
    args = ap.parse_args()

    srcs: list[str] = []
    if args.cases:
        d = json.load(io.open(args.cases, encoding="utf-8"))
        srcs = [x["sourceFile"] for x in d.get("docs", [])]
    if args.list:
        srcs += [l.strip() for l in io.open(args.list, encoding="utf-8") if l.strip()]
    seen, uniq = set(), []
    for s in srcs:
        if s not in seen:
            seen.add(s)
            uniq.append(s)
    srcs = uniq[:args.limit] if args.limit else uniq
    if not srcs:
        print("대상이 없다 - --list 또는 --cases 를 줄 것", file=sys.stderr)
        return 1

    from transformers import AutoProcessor
    from PIL import Image

    proc = AutoProcessor.from_pretrained(args.model, trust_remote_code=True)
    os.makedirs(args.out, exist_ok=True)
    meta_path = os.path.join(args.out, "_tokens.jsonl")
    ok = skip = 0
    toks = []

    print(f"{len(srcs)}장 · {args.model}", flush=True)
    for i, src in enumerate(srcs, 1):
        path = source_to_path(src)
        if not path:
            print(f"  [{i:>4}/{len(srcs)}] SKIP 원본 없음 {src[:44]}", flush=True)
            skip += 1
            continue
        try:
            with Image.open(path) as im:
                im = im.convert("RGB")
                enc = proc.image_processor(images=im, return_tensors="np")
            pv = enc.get("pixel_values")
            grid = enc.get("image_grid_thw")
            n_tok = None
            if grid is not None:
                import numpy as np
                g = np.asarray(grid).reshape(-1, 3)[0]
                # 비전 토큰 = 패치 격자 ÷ merge(보통 2x2)
                mg = int(getattr(proc.image_processor, "merge_size", 2))
                n_tok = int(g[0] * g[1] * g[2] // (mg * mg))
            elif pv is not None:
                n_tok = int(getattr(pv, "shape", [0])[0])

            img = to_image(pv, grid, proc.image_processor)
            if img is None:
                print(f"  [{i:>4}/{len(srcs)}] SKIP 텐서 모양 미지원 {src[:40]}", flush=True)
                skip += 1
                continue
            if max(img.size) > args.max_side:
                r = args.max_side / max(img.size)
                img = img.resize((int(img.width * r), int(img.height * r)))
            img.save(os.path.join(args.out, src + ".jpg"), quality=72)
            with io.open(meta_path, "a", encoding="utf-8", newline="\n") as fh:
                fh.write(json.dumps({"sourceFile": src, "visionTokens": n_tok,
                                     "size": list(img.size)}, ensure_ascii=False) + "\n")
            if n_tok:
                toks.append(n_tok)
            ok += 1
            if i % 20 == 0 or i == len(srcs):
                print(f"  [{i:>4}/{len(srcs)}] OK {src[:40]} tokens={n_tok}", flush=True)
        except Exception as exc:                      # noqa: BLE001
            print(f"  [{i:>4}/{len(srcs)}] ERR {src[:40]} !! {exc}", flush=True)
            skip += 1

    print(f"\n저장 {ok} · 건너뜀 {skip} → {args.out}")
    if toks:
        t = sorted(toks)
        print(f"비전 토큰: 중앙 {t[len(t)//2]:,} · 최소 {t[0]:,} · 최대 {t[-1]:,}")
        print("  (계획서 스모크 게이트 ④ '실제 적용 해상도·멀티모달 토큰 수' 에 넣을 값)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
