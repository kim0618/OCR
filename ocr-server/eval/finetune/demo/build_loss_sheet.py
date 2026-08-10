"""남은 ①잃어버림(글자 오독) 전량을 크롭 실물과 함께 한 화면에 펼친다.

GT 검수 시트와 같은 레이아웃이지만 목적이 다르다. 검수 시트는 <GT 가 맞나>를 묻고,
이 시트는 <무엇이 남았나>를 본다. 그래서 분류가 GT 신호가 아니라 <오독의 성격>이다:

    A 저해상        크롭 높이 20px 미만 또는 글자당 가로 9px 미만 - 정보 자체가 얇다
    B 동형문자      I/l·O/0·q/g 처럼 이미지만으로는 구분이 안 되는 치환
    C 법인표기 ㈜    ㈜/(주) 처리
    D 기호·괄호     글자는 맞고 기호만 틀림
    E 다중 오류     편집거리 3 이상
    F 선명한데 틀림  위 어디에도 안 걸림 - 인쇄가 또렷한데 모델이 틀린 것

표기 정규화로 해소되는 ①-B 는 애초에 담지 않는다(품명 글자는 다 맞게 읽은 몫).

    python eval/finetune/demo/build_loss_sheet.py
    python eval/finetune/demo/build_loss_sheet.py --run 260810_1037 --out LOSS_v18.html
"""
from __future__ import annotations

import argparse
import base64
import os
import shutil
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from recount_reviewed_gt import (  # noqa: E402
    HERE, comparable, load_policy, load_scan, name_key, notation_norm, lost_cause,
)

CROPS = Path(os.environ.get(
    "LOSS_CROPS_DIR",
    r"C:\Users\jinsung\AppData\Local\Temp\claude\d--Free-Vue"
    r"\ce98f7eb-f95c-4472-9e47-0f5fb2157dd4\scratchpad\crops548"))
HOMOGLYPH = {("O", "0"), ("0", "O"), ("I", "l"), ("l", "I"), ("I", "1"), ("1", "I"),
             ("I", "L"), ("L", "I"), ("l", "1"), ("1", "l"), ("l", "L"), ("L", "l"),
             ("ㄱ", "7"), ("7", "ㄱ"), ("B", "8"), ("8", "B"), ("S", "5"), ("5", "S"),
             ("n", "m"), ("m", "n"), ("q", "g"), ("g", "q"), ("D", "0"), ("0", "D"),
             ("U", "V"), ("V", "U"), ("C", "G"), ("G", "C"), ("E", "F"), ("F", "E")}
BUCKETS = ("A 저해상", "B 동형문자", "C 법인표기 ㈜", "D 기호·괄호",
           "E 다중 오류", "F 선명한데 틀림")


def edit_dist(a: str, b: str) -> int:
    a, b = comparable(a), comparable(b)
    n, m = len(a), len(b)
    d = list(range(m + 1))
    for i in range(1, n + 1):
        prev, d[0] = d[0], i
        for j in range(1, m + 1):
            prev, d[j] = d[j], min(d[j] + 1, d[j - 1] + 1,
                                   prev + (a[i - 1] != b[j - 1]))
    return d[m]


def img_meta(path: Path) -> tuple[int, float, str]:
    """(높이, 글자당 가로 px, base64). 크롭이 없으면 (0, 0, '')."""
    if not path.exists():
        return 0, 0.0, ""
    from PIL import Image
    with Image.open(path) as im:
        w, h = im.size
    return h, float(w), "data:image/jpeg;base64," + base64.b64encode(
        path.read_bytes()).decode("ascii")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="260807_1302", help="볼 모델 태그(기본 v16)")
    ap.add_argument("--out", default="LOSS_SHEET.html")
    args = ap.parse_args()

    keep = {line.strip() for line
            in (HERE / "basis_keep.txt").read_text(encoding="utf-8").splitlines()
            if line.strip()}
    overrides, excluded, _ = load_policy()
    base = load_scan("000_base.jsonl", keep)
    ref = load_scan(f"{args.run}.jsonl", keep)

    rows, notation = [], 0
    for path, brow in base.items():
        key = name_key(brow["gt"])
        if key in excluded or path not in ref:
            continue
        gt = overrides.get(key, brow["gt"])
        pred = ref[path]["pred"]
        if comparable(gt) != comparable(brow["pred"]):      # base 가 못 읽음
            continue
        if comparable(gt) == comparable(pred):              # 손실 아님
            continue
        if notation_norm(gt) == notation_norm(pred):        # ①-B 표기층
            notation += 1
            continue
        rows.append({"path": path, "gt": gt, "base": brow["pred"], "pred": pred,
                     "cause": lost_cause(gt, pred), "dist": edit_dist(gt, pred)})

    if not any(CROPS.rglob("*.jpg")):
        arc = HERE / "verify" / f"loss548_crops_{args.run}.tgz"
        if arc.exists():
            import tarfile
            CROPS.mkdir(parents=True, exist_ok=True)
            with tarfile.open(arc) as t:
                t.extractall(CROPS)
            print(f"[크롭] {arc.name} 자동 추출")

    missing = 0
    for r in rows:
        h, w, img = img_meta(CROPS / r["path"].replace("/", os.sep))
        r["h"], r["img"] = h, img
        r["ppc"] = w / max(1, len(comparable(r["gt"])))
        if not img:
            missing += 1
        g, p = comparable(r["gt"]), comparable(r["pred"])
        homo = False
        if len(g) == len(p):
            sub = [(a, b) for a, b in zip(g, p) if a != b]
            homo = bool(sub) and all(tuple(s) in HOMOGLYPH for s in sub)
        if not h:
            r["bucket"] = "F 선명한데 틀림"
        elif h < 20 or r["ppc"] < 9:
            r["bucket"] = "A 저해상"
        elif homo:
            r["bucket"] = "B 동형문자"
        elif r["cause"] == "법인표기(㈜)":
            r["bucket"] = "C 법인표기 ㈜"
        elif r["cause"] == "기호·괄호":
            r["bucket"] = "D 기호·괄호"
        elif r["dist"] >= 3:
            r["bucket"] = "E 다중 오류"
        else:
            r["bucket"] = "F 선명한데 틀림"

    rows.sort(key=lambda r: (BUCKETS.index(r["bucket"]), r["cause"], r["gt"]))
    counts = Counter(r["bucket"] for r in rows)
    causes = Counter(r["cause"] for r in rows)

    def esc(s: str) -> str:
        return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    tr = []
    for i, r in enumerate(rows):
        img = (f'<img src="{r["img"]}">' if r["img"]
               else '<span class=no>크롭 없음</span>')
        tr.append(
            f'<tr data-b="{r["bucket"][0]}"><td class=n>{i + 1}</td>'
            f'<td class=k>{esc(r["bucket"])}<br><span class=why>{esc(r["cause"])}'
            f' · 거리{r["dist"]} · {r["h"]}px</span></td>'
            f'<td class=c>{img}</td>'
            f'<td class=gt>{esc(r["gt"])}</td>'
            f'<td class=p>{esc(r["base"])}</td>'
            f'<td class=bad>{esc(r["pred"])}</td></tr>')

    chips = " ".join(
        f'<button onclick="flt(\'{b[0]}\')">{esc(b)} {counts.get(b, 0)}</button>'
        for b in BUCKETS if counts.get(b))
    html = f"""<!doctype html><meta charset="utf-8">
<title>남은 잃어버림 {len(rows)}건 - {args.run}</title>
<style>
body{{font-family:'Malgun Gothic',sans-serif;margin:20px;color:#111;background:#fff}}
h1{{font-size:19px;margin:0 0 6px}} .sum{{color:#555;font-size:13px;line-height:1.7}}
table{{border-collapse:collapse;width:100%;font-size:13px;margin-top:10px}}
th,td{{border:1px solid #ddd;padding:5px 7px;vertical-align:middle}}
th{{background:#f4f4f4;position:sticky;top:0;z-index:2}}
img{{max-height:40px;image-rendering:crisp-edges}}
.n{{color:#999;width:38px}} .k{{width:132px;font-size:12px}} .why{{color:#888;font-size:11px}}
.c{{width:340px}} .gt{{font-weight:600}}
.p{{font-family:Consolas,monospace;font-size:12px;color:#0a7}}
.bad{{font-family:Consolas,monospace;font-size:12px;color:#c00}}
.no{{color:#c60;font-size:12px}}
#bar{{margin:10px 0}} button{{font-size:13px;padding:5px 10px;margin-right:6px;cursor:pointer}}
tr[data-b="A"]{{background:#fff4f4}} tr[data-b="B"]{{background:#eef7ff}}
tr[data-b="C"]{{background:#fff7e6}} tr[data-b="D"]{{background:#f6f0ff}}
</style>
<h1>남은 ① 잃어버림 <b>{len(rows)}건</b> — {args.run}</h1>
<div class=sum>
base 가 맞게 읽던 크롭을 이 모델이 <b>글자 단위로</b> 틀리게 읽은 것만 모았습니다.
표기 정규화로 해소되는 {notation}건(꼬리 기호·행번호 구분자)은 뺐습니다.<br>
원인별: {' · '.join(f'{esc(k)} <b>{v}</b>' for k, v in causes.most_common())}
{f'<br><b>크롭 없음 {missing}건</b>' if missing else ''}
</div>
<div id=bar>분류로 보기: <button onclick="flt('')">전체 {len(rows)}</button> {chips}</div>
<table><tr><th>#</th><th>분류</th><th>크롭 실물</th><th>GT</th>
<th>base 예측</th><th>{args.run} 예측</th></tr>
{chr(10).join(tr)}
</table>
<script>
function flt(b){{
  document.querySelectorAll('table tr').forEach(r=>{{
    if(!r.dataset.b) return;
    r.style.display = (!b || r.dataset.b===b) ? '' : 'none';
  }});
}}
</script>"""

    out = HERE / args.out
    if out.exists():
        bak = out.with_suffix(f".{time.strftime('%y%m%d_%H%M%S')}.bak.html")
        shutil.copy2(out, bak)
        print(f"[백업] {bak.name}")
    out.write_text(html, encoding="utf-8")
    print(f"wrote {out}")
    print(f"  {len(rows)}건 (표기 정규화 제외 {notation}건"
          + (f", 크롭 없음 {missing}건" if missing else "") + ")")
    for b in BUCKETS:
        if counts.get(b):
            print(f"    {b:<16} {counts[b]:>4}")


if __name__ == "__main__":
    main()
