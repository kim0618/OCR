"""paddlevl_runner — PaddleOCR-VL 로 문서를 파싱해 원본 결과를 그대로 떨궈 놓는다.

우리 JSON 으로 바꾸는 일은 **하지 않는다**. 그건 로컬의 paddlevl_adapt.py 몫이다.
여기서는 모델이 낸 것(블록·좌표·표 HTML)만 저장한다 - 어댑터를 고칠 때마다 GPU 를
다시 켜지 않으려면 원본이 남아 있어야 한다.

왜 llm_runner 를 못 쓰나
    Qwen·InternVL 은 "이미지 + 우리 스키마" 를 주면 JSON 을 돌려주는 지시형 모델이라
    OpenAI 호환 /v1/chat 으로 끝난다. PaddleOCR-VL 은 지시를 따르는 모델이 아니고,
    레이아웃 모델(PP-DocLayoutV2)이 먼저 영역을 자르고 0.9B VLM 이 조각을 읽는 2단 구조다.
    그 앞단을 paddleocr 패키지가 돌리므로 호출 방식 자체가 다르다.

전제
    vLLM 이 PaddleOCR-VL 을 서빙 중(run-vlm-serve 계열)
    paddleocr[doc-parser] 가 깔린 별도 venv 에서 실행(vLLM·Paddle 백엔드 venv 와 충돌한다)

    python eval/paddlevl_runner.py --list eval/LLM/inputs/smoke_50.txt --run vlm_paddlevl_smoke
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def source_name(path: str) -> str:
    """llm_runner.source_name 과 같은 규약이어야 compare_run 이 GT 를 찾는다.
    .../images_replay/2501/10006/NAME.jpg -> 2501__10006__NAME.jpg
    run 폴더의 파생 이미지(rotated/)는 꼬리 .jpg.jpg 를 한 번 뗀다."""
    norm = path.replace("\\", "/")
    m = re.search(r"images_replay/([^/]+)/([^/]+)/([^/]+)$", norm)
    if m:
        return "%s__%s__%s" % (m.group(1), m.group(2), m.group(3))
    base = os.path.basename(path)
    if "/runs/" in norm and base.endswith(".jpg.jpg"):
        return base[:-4]
    return base


def to_jsonable(o):
    """numpy 배열·스칼라가 섞여 온다(block_bbox 가 ndarray). JSON 으로 낮춘다."""
    if hasattr(o, "tolist"):
        return o.tolist()
    if isinstance(o, dict):
        return {str(k): to_jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [to_jsonable(v) for v in o]
    if isinstance(o, (str, int, float, bool)) or o is None:
        return o
    return str(o)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", required=True, help="이미지 경로 목록(eval/ 기준 상대경로)")
    ap.add_argument("--run", required=True, help="eval/runs/ 아래 run 이름")
    ap.add_argument("--server", default="http://localhost:8000/v1")
    ap.add_argument("--layout-name", default="", help="레이아웃 모델 이름(비우면 파이프라인 기본값)")
    ap.add_argument("--layout-dir", default="", help="레이아웃 모델 로컬 경로(비우면 자동 다운로드)")
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()

    from paddleocr import PaddleOCRVL                       # noqa: PLC0415

    # 레이아웃 모델은 파이프라인 기본값에 맡긴다 - 버전마다 다르다(v1=PP-DocLayoutV2 · 1.6=PP-DocLayoutV3).
    # 고정했다가 1.6 에서 어긋났다(2026-09-17).
    kw = {"vl_rec_backend": "vllm-server", "vl_rec_server_url": a.server}
    if a.layout_name:
        kw["layout_detection_model_name"] = a.layout_name
    if a.layout_dir:
        kw["layout_detection_model_dir"] = a.layout_dir
    pipeline = PaddleOCRVL(**kw)

    paths = [l.strip() for l in io.open(a.list, encoding="utf-8") if l.strip()]
    if a.limit:
        paths = paths[:a.limit]
    out_dir = os.path.join(HERE, "runs", a.run, "parse")
    os.makedirs(out_dir, exist_ok=True)

    t0 = time.time()
    ok = fail = 0
    for i, rel in enumerate(paths, 1):
        img = rel if os.path.isabs(rel) else os.path.join(HERE, rel)
        src = source_name(rel)
        dst = os.path.join(out_dir, src + ".json")
        if os.path.exists(dst):                              # 이어서 돌리기
            ok += 1
            continue
        t1 = time.time()
        try:
            res = pipeline.predict(img)
            page = res[0] if isinstance(res, (list, tuple)) and res else res
            raw = page.json if hasattr(page, "json") else page
            raw = raw.get("res", raw) if isinstance(raw, dict) else raw
            blocks = to_jsonable(raw.get("parsing_res_list") or [])
            w = h = 0
            for key in ("doc_preprocessor_res", "input_img_shape", "image_size"):
                v = raw.get(key)
                if isinstance(v, (list, tuple)) and len(v) >= 2:
                    h, w = int(v[0]), int(v[1])
                    break
            if not w:                                        # 블록 좌표에서 추정
                xs = [b["block_bbox"][2] for b in blocks if b.get("block_bbox")]
                ys = [b["block_bbox"][3] for b in blocks if b.get("block_bbox")]
                w, h = int(max(xs or [0])), int(max(ys or [0]))
            rec = {"sourceFile": src, "image_path": img, "image_size": [w, h],
                   "elapsedSec": round(time.time() - t1, 2),
                   "parsing_res_list": blocks}
            with io.open(dst, "w", encoding="utf-8") as fh:
                json.dump(rec, fh, ensure_ascii=False)
            ok += 1
            tables = sum(1 for b in blocks if (b.get("block_label") or "").lower() == "table")
            print("  [%4d/%d] OK  %-44s 블록 %3d · 표 %d · %5.1fs"
                  % (i, len(paths), src[:44], len(blocks), tables, time.time() - t1), flush=True)
        except Exception as exc:                             # noqa: BLE001
            fail += 1
            print("  [%4d/%d] ERR %-44s %s" % (i, len(paths), src[:44], exc), flush=True)

    sec = time.time() - t0
    meta = {"run": a.run, "model": "PaddlePaddle/PaddleOCR-VL", "docs": len(paths),
            "ok": ok, "fail": fail, "elapsedSec": round(sec, 1),
            "docsPerHour": round(ok / sec * 3600, 1) if sec else None}
    with io.open(os.path.join(HERE, "runs", a.run, "parse_meta.json"), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=2)
    print(json.dumps(meta, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
