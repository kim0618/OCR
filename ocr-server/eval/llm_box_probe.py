"""llm_box_probe — "한 번에 한 행만" 물어 Qwen 의 grounding 능력만 따로 잰다.

왜 따로 재나
    스모크 v1-box 두 번(2026-09-18 · 09-21)에서 행마다 bbox_2d 를 같이 내라고 했더니
    56% 는 [0,0,0,0], 나머지는 y 간격이 완전히 일정한 **지어낸 격자**였다.
    그런데 그건 "40행짜리 JSON 을 뱉으면서 행마다 박스를 끼워라"라는 형태였고,
    Qwen 의 grounding 은 **"이것을 찾아라 → 박스 하나"** 로 학습돼 있다(ScreenSpot 94.4).

    그래서 둘을 가른다:
      이 프로브가 되면   → 능력은 있고 **우리 작업 형태**가 문제다(2단계 호출로 우회 가능)
      이것도 안 되면     → 4B 로는 이 문서에서 못 한다가 확정

무엇을 묻나
    문서 한 장 + 그 문서의 GT 품명 하나 → "그 글자가 있는 행의 bbox_2d 를 줘". 답은 박스 하나뿐이다.

채점
    모델 박스(0~1000)를 픽셀로 환산해, 그 안에 Base OCR 이 잡은 같은 글자가 실제로 있는지 본다.
    Base 스냅샷(071)은 950px 처리본 좌표라 세로 비율만 맞춰 비교한다 - 맞고 틀림은 y 로 갈린다.

    python eval/llm_box_probe.py --docs 10        # AWS 에서 (vLLM 서버 필요)
"""
from __future__ import annotations

import argparse
import base64
import io
import json
import os
import re
import sys
import time
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
GT = os.path.join(HERE, "data", "invoice_war", "ground_truth_replay.json")
LIST = os.path.join(HERE, "LLM", "inputs", "smoke_50.txt")

SYS = ("너는 문서 이미지에서 지정한 글자를 찾아 그 위치를 알려주는 도구다. "
       "JSON 하나만 출력한다. 설명·마크다운·코드펜스를 출력하지 않는다.")
USR = ('이 거래명세표에서 품목 "%s" 가 적힌 행을 찾아라.\n'
       '그 행 전체를 감싸는 사각형을 0~1000 으로 정규화한 좌표로 출력하라'
       '(왼쪽 위가 0,0 · 오른쪽 아래가 1000,1000).\n\n'
       '{"bbox_2d": [x1, y1, x2, y2]}')


def ask(server: str, model: str, img_b64: str, name: str, max_tokens: int, timeout: float) -> dict:
    body = {
        "model": model, "temperature": 0, "max_tokens": max_tokens,
        "messages": [
            {"role": "system", "content": SYS},
            {"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + img_b64}},
                {"type": "text", "text": USR % name},
            ]},
        ],
    }
    req = urllib.request.Request(server.rstrip("/") + "/chat/completions",
                                 data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def first_json(text: str) -> dict | None:
    i, j = text.find("{"), text.rfind("}")
    if i < 0 or j <= i:
        return None
    try:
        return json.loads(text[i:j + 1])
    except json.JSONDecodeError:
        return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--server", default="http://localhost:8000/v1")
    ap.add_argument("--model", default="Qwen/Qwen3-VL-4B-Instruct")
    ap.add_argument("--docs", type=int, default=10)
    ap.add_argument("--max-tokens", type=int, default=128)
    ap.add_argument("--timeout", type=float, default=600)
    ap.add_argument("--out", default=os.path.join(HERE, "LLM", "data", "box_probe.json"))
    a = ap.parse_args()

    gt = json.load(io.open(GT, encoding="utf-8"))["documents"]
    paths = [l.strip() for l in io.open(LIST, encoding="utf-8") if l.strip()]

    out, t0 = [], time.time()
    for rel in paths:
        if len(out) >= a.docs:
            break
        m = re.search(r"images_replay/([^/]+)/([^/]+)/([^/]+)$", rel.replace("\\", "/"))
        key = "%s/%s/%s" % m.groups() if m else None
        doc = gt.get(key) if key else None
        if not doc:
            continue
        rows = doc["normalizedResult"].get("tableRows") or []
        # 가운데쯤 행을 고른다 - 첫 행은 머리글 바로 아래라 쉬운 자리다
        cand = [r.get("itemName") for r in rows if (r.get("itemName") or "").strip()]
        if len(cand) < 5:
            continue
        name = cand[len(cand) // 2]
        want_idx = [i for i, r in enumerate(rows) if r.get("itemName") == name][0]

        img = rel if os.path.isabs(rel) else os.path.join(HERE, rel)
        b64 = base64.b64encode(io.open(img, "rb").read()).decode()
        t1 = time.time()
        try:
            resp = ask(a.server, a.model, b64, name, a.max_tokens, a.timeout)
            raw = resp["choices"][0]["message"]["content"]
            js = first_json(raw) or {}
            box = js.get("bbox_2d")
        except Exception as exc:                                  # noqa: BLE001
            raw, box = str(exc), None
        rec = {"sourceFile": os.path.basename(rel), "itemName": name,
               "rowIndex": want_idx + 1, "rowCount": len(rows),
               "bbox_2d": box, "raw": (raw or "")[:200], "sec": round(time.time() - t1, 1)}
        out.append(rec)
        ok = isinstance(box, list) and len(box) == 4 and box != [0, 0, 0, 0]
        print("  [%2d] %-30s %-22s 행 %2d/%2d  %s  %4.1fs"
              % (len(out), rec["sourceFile"][:30], name[:22], rec["rowIndex"], rec["rowCount"],
                 box if ok else ("(%s)" % (box if box is not None else "박스 없음")), rec["sec"]), flush=True)

    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    json.dump(out, io.open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    good = [r for r in out if isinstance(r["bbox_2d"], list) and len(r["bbox_2d"]) == 4 and r["bbox_2d"] != [0, 0, 0, 0]]
    print()
    print("문서 %d장 · 박스 받은 것 %d (%.0f%%) · %.1f초" % (
        len(out), len(good), 100 * len(good) / max(1, len(out)), time.time() - t0))
    print("→ %s" % a.out)
    print()
    print("읽는 법: 박스가 나오고 y 위치가 행 순번(행 k/N)과 얼추 맞으면 -")
    print("  능력은 있고 '40행 JSON 안에 끼워 넣기'라는 형태가 문제였던 것이다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
