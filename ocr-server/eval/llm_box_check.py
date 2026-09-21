"""llm_box_check — 모델이 준 행 좌표(box)가 실제로 그 행을 가리키는지 눈으로 본다.

프롬프트 v1-box 스모크의 판정 도구. 숫자(처리량·잘림)는 러너가 이미 찍으므로
여기서 보는 것은 하나뿐이다: **좌표가 쓸 만한가.**

쓸 만하다면 다음이 열린다 - 틀린 값이 어디서 왔는지 짚기, structure/recognition 가르기,
좌표 기반 Base 룰 11개를 VLM 경로에 태우기.

    python eval/llm_box_check.py --run vlm_qwen_smoke_box
    → eval/LLM/LLM_BOX_CHECK.html  (모델 박스대로 자른 크롭 + 그 행의 값)
"""
from __future__ import annotations

import argparse
import base64
import html
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(HERE, "LLM", "LLM_BOX_CHECK.html")
COLS = [("itemName", "품명"), ("spec", "규격"), ("quantity", "수량"),
        ("unitPrice", "단가"), ("amount", "금액"),
        ("manufacturingNo", "제조번호"), ("expiryDate", "유효기간")]


def esc(v) -> str:
    return html.escape(str(v or ""))


def to_px(box, w: int, h: int):
    """0~1000 정규화 좌표를 원본 픽셀로. Qwen3-VL 의 bbox_2d 규약."""
    try:
        x1, y1, x2, y2 = [float(v) for v in box]
    except (TypeError, ValueError):
        return None
    return [int(x1 * w / 1000), int(y1 * h / 1000), int(x2 * w / 1000), int(y2 * h / 1000)]


def crop_b64(img, box, pad: int = 4) -> str | None:
    try:
        x1, y1, x2, y2 = [int(v) for v in box]
    except (TypeError, ValueError):
        return None
    if x2 <= x1 or y2 <= y1:
        return None
    w, h = img.size
    x1, y1 = max(0, x1 - pad), max(0, y1 - pad)
    x2, y2 = min(w, x2 + pad), min(h, y2 + pad)
    if x2 - x1 < 8 or y2 - y1 < 4:
        return None
    buf = io.BytesIO()
    img.crop((x1, y1, x2, y2)).convert("RGB").save(buf, "JPEG", quality=72)
    return base64.b64encode(buf.getvalue()).decode()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--docs", type=int, default=10, help="볼 문서 수")
    ap.add_argument("--rows", type=int, default=6, help="문서마다 볼 행 수")
    a = ap.parse_args()

    from PIL import Image                                   # noqa: PLC0415
    sam = os.path.join(HERE, "runs", a.run, "samples")
    files = sorted(os.listdir(sam))

    cards, stat = [], {"docs": 0, "rows": 0, "boxed": 0, "zero": 0, "cropped": 0, "outside": 0}
    for fn in files:
        s = json.load(io.open(os.path.join(sam, fn), encoding="utf-8"))
        rows = (s.get("documentFields") or {}).get("tableRows") or []
        boxes = [r for r in rows if isinstance(r.get("bbox_2d"), list) and len(r["bbox_2d"]) == 4]
        stat["rows"] += len(rows)
        stat["boxed"] += len(boxes)
        stat["zero"] += sum(1 for r in boxes if r["bbox_2d"] == [0, 0, 0, 0])
        if stat["docs"] >= a.docs or not boxes:
            continue
        path = s.get("imagePath") or ""
        if not os.path.exists(path):
            path = os.path.join(ROOT, path.lstrip("/"))
        if not os.path.exists(path):
            continue
        img = Image.open(path)
        w, h = img.size
        trs = []
        for r in boxes[:a.rows]:
            n = r["bbox_2d"]
            if n != [0, 0, 0, 0] and (n[2] > 1050 or n[3] > 1050):
                stat["outside"] += 1          # 0~1000 밖 = 규약을 안 따른 것
            b = to_px(n, w, h) or [0, 0, 0, 0]
            c = crop_b64(img, b)
            if c:
                stat["cropped"] += 1
            vals = " · ".join("%s %s" % (ko, esc(r.get(k))) for k, ko in COLS if r.get(k))
            trs.append("<tr><td>%s</td><td class='m'>%s</td><td>%s</td></tr>" % (
                ("<img src='data:image/jpeg;base64,%s'>" % c) if c else "<span class='m'>(못 자름)</span>",
                esc(n) + " → " + esc(b), vals))
        cards.append("<h3>%s <span class='m'>· %d×%d · 행 %d개</span></h3>"
                     "<table><tr><th style='width:52%%'>모델 박스대로 자른 그림</th>"
                     "<th style='width:230px'>bbox_2d → 픽셀</th><th>그 행의 값</th></tr>%s</table>"
                     % (esc(s.get("sourceFile"))[:60], w, h, len(rows), "".join(trs)))
        stat["docs"] += 1

    pct = lambda n, d: (100.0 * n / d) if d else 0.0
    head = ("<p><b>행 %d개 중 박스 %d개(%.1f%%)</b> · 그중 [0,0,0,0] %d · 그림 밖 좌표 %d · 실제로 잘린 것 %d</p>"
            % (stat["rows"], stat["boxed"], pct(stat["boxed"], stat["rows"]),
               stat["zero"], stat["outside"], stat["cropped"]))
    html_doc = ("<!doctype html><meta charset='utf-8'><title>박스 확인 · %s</title>"
                "<style>body{font:14px/1.6 -apple-system,'Malgun Gothic',sans-serif;margin:24px;color:#1b2733}"
                "table{border-collapse:collapse;width:100%%;margin:8px 0 22px}"
                "th,td{border:1px solid #e3e8ee;padding:6px 8px;vertical-align:middle;font-size:13px}"
                "th{background:#f6f8fa;text-align:left}img{max-height:46px}"
                ".m{color:#5b6b7b;font-size:12px}h3{margin:18px 0 4px;font-size:15px}</style>"
                "<h1>모델 박스 확인 <span class='m'>· %s</span></h1>%s"
                "<p class='m'>이 크롭은 <b>모델이 준 좌표</b>로 자른 것이다(기존 실물 페이지의 크롭은 Base 가 잡은 영역이다). "
                "행 전체를 감싸고 있으면 좌표가 쓸 만한 것이고, 품명만 가리키거나 엉뚱한 곳이면 못 쓴다.</p>%s"
                % (esc(a.run), esc(a.run), head, "".join(cards)))
    io.open(OUT, "w", encoding="utf-8", newline="").write(html_doc)
    print("→ %s (%.0fKB)" % (os.path.basename(OUT), os.path.getsize(OUT) / 1024))
    print(head.replace("<p>", "").replace("</p>", "").replace("<b>", "").replace("</b>", ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
