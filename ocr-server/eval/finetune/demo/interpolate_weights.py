"""가중치 보간(WiSE-FT) — base 와 FT 모델의 pdparams 를 α 로 섞어 새 모델을 만든다.

    새 가중치 = α × FT  +  (1−α) × base        (α=1 이면 FT 그대로, α=0 이면 base)

왜 (2026-08-10): v16(260807_1302)의 ①글자 손실 356 은 상당수가 <경계가 아슬아슬해서
뒤집힌 것>(㈜·꼬리 기호·CTC 반복 경계)이다. 가중치 이동을 일부 되돌리면 이런 건 먼저
돌아오고, 타깃(세파록스캡슐 0/26→26/26)은 이동 폭이 커서 α 를 내려도 유지될 여지가 크다.
학습이 아니라 이미 있는 두 파일의 자리별 가중평균이라 GPU 학습 0회.

재현: 산출물 옆에 manifest.json 으로 {base·ft 경로/sha256, alpha, 시각}을 남긴다.
      같은 두 파일 + 같은 α = 항상 같은 결과(순수 산술).

    python eval/finetune/demo/interpolate_weights.py \
        --base ~/.paddleocr/models/korean_PP-OCRv5_mobile_rec_pretrained.pdparams \
        --ft   eval/finetune/versions/run_260807_1302/best_accuracy/best_accuracy.pdparams \
        --alpha 0.8 --out /tmp/interp_a80.pdparams
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import time

import numpy as np
import paddle


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def to_numpy(v):
    return v.numpy() if hasattr(v, "numpy") else np.asarray(v)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True, help="base pdparams (α=0 쪽)")
    ap.add_argument("--ft", required=True, help="FT pdparams (α=1 쪽)")
    ap.add_argument("--alpha", type=float, required=True, help="FT 비중 0..1")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    if not 0.0 <= args.alpha <= 1.0:
        raise SystemExit(f"alpha 는 0..1 이어야 합니다: {args.alpha}")

    base = paddle.load(os.path.expanduser(args.base))
    ft = paddle.load(os.path.expanduser(args.ft))

    only_base = sorted(set(base) - set(ft))
    only_ft = sorted(set(ft) - set(base))
    if only_base or only_ft:
        # 구조가 다르면 보간 자체가 성립하지 않는다 - 어느 쪽 키가 남는지 보여주고 중단.
        raise SystemExit(f"★키 불일치: base에만 {len(only_base)}개 {only_base[:5]} / "
                         f"ft에만 {len(only_ft)}개 {only_ft[:5]}")

    out: dict = {}
    n_blend = n_copy = 0
    for key, fv in ft.items():
        f_np, b_np = to_numpy(fv), to_numpy(base[key])
        if f_np.shape != b_np.shape:
            raise SystemExit(f"★shape 불일치 {key}: base{b_np.shape} vs ft{f_np.shape}")
        if np.issubdtype(f_np.dtype, np.floating):
            out[key] = (args.alpha * f_np.astype(np.float64)
                        + (1.0 - args.alpha) * b_np.astype(np.float64)
                        ).astype(f_np.dtype)
            n_blend += 1
        else:
            out[key] = f_np          # int/bool 류는 섞을 수 없다 - FT 쪽을 쓴다
            n_copy += 1

    paddle.save(out, args.out)
    manifest = {
        "method": "wise-ft-interpolation",
        "alpha_ft": args.alpha,
        "base": {"path": os.path.expanduser(args.base),
                 "sha256": sha256(os.path.expanduser(args.base))},
        "ft": {"path": os.path.expanduser(args.ft),
               "sha256": sha256(os.path.expanduser(args.ft))},
        "out": {"path": args.out, "sha256": sha256(args.out)},
        "tensors": {"blended": n_blend, "copiedFromFt": n_copy},
        "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    mpath = args.out + ".manifest.json"
    with open(mpath, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)
    print(f"[보간] α={args.alpha}  blend {n_blend} / copy {n_copy} tensors")
    print(f"  -> {args.out}")
    print(f"  -> {mpath}")


if __name__ == "__main__":
    main()
