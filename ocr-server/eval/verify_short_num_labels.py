# -*- coding: utf-8 -*-
"""짧은숫자(기본 1~3자리) 학습 라벨을 base(official) 모델로 재판독해 오염 제거.

배경 (2026-07-30, clean2 부검):
  clean2 는 실현성 필터로 "긴 라벨이 좁은 크롭에 붙은" 오염 9만장을 제거해
  4+자리 RETAIN 을 +2.6 으로 되살렸지만, 1자리는 오히려 -38.1 로 더 붕괴했다.
  원인 실측: 1자리 '정답풀'(balance/anchor) 크롭의 34%(육안 137/400)가 도장 조각·
  바코드·표 머리글·한글 글자에 숫자 라벨이 붙은 쓰레기 — 수확 bbox 정렬 버그가
  balance 에도 있었고, 1자리는 길이-실현성 검사로 잡을 수 없는 사각지대.
처방:
  학습 목록의 짧은숫자 라벨 크롭을 base 모델로 다시 읽혀 "출력==라벨"인 것만 남긴다
  (self-verify). 1자리 목표는 개선이 아니라 '유지'이므로 base 가 읽는 크롭만으로 충분.
사용 (run-finetune.sh clean3 라운드에서 build_dataset 직후):
  python eval/verify_short_num_labels.py                # dataset/train.txt 를 제자리 필터
  python eval/verify_short_num_labels.py --dry-run      # 드랍 통계만
"""
from __future__ import annotations

import argparse
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from finetune_ledger import CORPUS_DIR  # noqa: E402

NUM = re.compile(r"^[0-9][0-9,.]*$")


def _norm(t: str) -> str:
    return t.strip().replace(",", "").replace(" ", "")


class BaseRec:
    """official pretrained rec — paddle.inference 직접(래퍼 불요), GPU 있으면 GPU."""

    def __init__(self, model_dir: str, use_gpu: bool = True):
        import paddle.inference as pi
        import yaml
        with open(os.path.join(model_dir, "inference.yml"), encoding="utf-8") as fh:
            self.chars = yaml.safe_load(fh)["PostProcess"]["character_dict"]
        cfg = pi.Config(os.path.join(model_dir, "inference.json"),
                        os.path.join(model_dir, "inference.pdiparams"))
        if use_gpu:
            try:
                cfg.enable_use_gpu(512, 0)
            except Exception:
                cfg.disable_gpu()
        else:
            cfg.disable_gpu()
            cfg.set_cpu_math_library_num_threads(os.cpu_count() or 8)
        cfg.disable_glog_info()
        self.pred = pi.create_predictor(cfg)
        self.i = self.pred.get_input_names()[0]
        self.o = self.pred.get_output_names()[0]

    def batch(self, imgs) -> list[str]:
        import cv2
        import numpy as np
        x = np.zeros((len(imgs), 3, 48, 320), dtype="float32")
        for k, img in enumerate(imgs):
            h, w = img.shape[:2]
            rw = max(1, min(320, int(math.ceil(48 * w / float(h)))))
            r = cv2.resize(img, (rw, 48)).astype("float32").transpose((2, 0, 1)) / 255.0
            x[k, :, :, :rw] = (r - 0.5) / 0.5
        self.pred.get_input_handle(self.i).copy_from_cpu(x)
        self.pred.run()
        probs = self.pred.get_output_handle(self.o).copy_to_cpu()
        outs = []
        for pr in probs:
            idx = pr.argmax(axis=1)
            chars, prev = [], 0
            for t in idx:
                if t != 0 and t != prev:
                    ci = t - 1
                    chars.append(self.chars[ci] if ci < len(self.chars) else "?")
                prev = t
            outs.append("".join(chars).strip())
        return outs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", default=os.path.join(CORPUS_DIR, "dataset", "train.txt"),
                    help="필터할 라벨 목록(탭구분 rel\\tgt). 제자리 재작성, 원본은 .preverify 백업")
    ap.add_argument("--max-digits", type=int, default=3,
                    help="검증 대상 = 순수숫자 라벨 중 자릿수 <= 이 값 (기본 1~3자리)")
    ap.add_argument("--model-dir", default=os.path.expanduser(
        "~/.paddlex/official_models/korean_PP-OCRv5_mobile_rec"),
        help="base(official) rec inference 디렉터리")
    ap.add_argument("--batch", type=int, default=64)
    ap.add_argument("--cpu", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--corpus-dir", default=CORPUS_DIR,
                    help="크롭 rel 경로의 루트(기본=finetune_corpus). 로컬 검증 시 지정")
    args = ap.parse_args()

    if not os.path.isfile(os.path.join(args.model_dir, "inference.pdiparams")):
        print(f"[verify] base 모델 없음: {args.model_dir} — --model-dir 지정 필요")
        return 2

    import cv2
    rows = []
    targets = []          # (rows 인덱스, 라벨)
    for ln in open(args.list, encoding="utf-8"):
        parts = ln.rstrip("\n").split("\t")
        rows.append(parts)
        if len(parts) >= 2:
            gt = parts[1].strip()
            if NUM.match(gt) and len(_norm(gt)) <= args.max_digits:
                targets.append(len(rows) - 1)

    print(f"[verify] 목록 {len(rows):,}줄 중 짧은숫자(<= {args.max_digits}자리) {len(targets):,}건 검증")
    rec = BaseRec(args.model_dir, use_gpu=not args.cpu)

    drop: set[int] = set()
    stats = {}            # 자릿수 -> [검증수, 드랍수]
    miss_img = 0
    buf_idx, buf_img = [], []

    def flush():
        nonlocal buf_idx, buf_img
        if not buf_idx:
            return
        outs = rec.batch(buf_img)
        for i, out in zip(buf_idx, outs):
            gt = _norm(rows[i][1])
            k = str(len(gt))
            st = stats.setdefault(k, [0, 0])
            st[0] += 1
            if _norm(out) != gt:
                drop.add(i)
                st[1] += 1
        buf_idx, buf_img = [], []

    for i in targets:
        p = os.path.join(args.corpus_dir, rows[i][0])
        img = cv2.imread(p)
        if img is None or img.shape[0] < 2 or img.shape[1] < 2:
            miss_img += 1
            drop.add(i)
            continue
        buf_idx.append(i)
        buf_img.append(img)
        if len(buf_idx) >= args.batch:
            flush()
    flush()

    for k in sorted(stats):
        n, d = stats[k]
        print(f"[verify]   {k}자리: {n:,} 중 드랍 {d:,} ({d / max(n, 1) * 100:.1f}%)")
    if miss_img:
        print(f"[verify]   이미지 없음/깨짐 드랍: {miss_img:,}")
    print(f"[verify] 총 드랍 {len(drop):,} / 검증 {len(targets):,} "
          f"({len(drop) / max(len(targets), 1) * 100:.1f}%) — 남는 목록 {len(rows) - len(drop):,}줄")

    if args.dry_run:
        print("[verify] dry-run — 파일 무변경")
        return 0
    bak = args.list + ".preverify"
    os.replace(args.list, bak)
    with open(args.list, "w", encoding="utf-8") as fh:
        for i, parts in enumerate(rows):
            if i in drop:
                continue
            fh.write("\t".join(parts) + "\n")
    print(f"[verify] 재작성 완료: {args.list} (원본={os.path.basename(bak)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
