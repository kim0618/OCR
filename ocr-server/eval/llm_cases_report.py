"""llm_cases_report — LLM 비교의 부류별 실물 갤러리(전량)를 만든다.

LLM_REVIEW_PLAN.html 은 숫자만 두고, 실물은 이 스크립트가 찍는 세 파일에서 전량 본다.
    LLM_CASES_REVIVED.html    소생   Base 붕괴 -> 모델 정상
    LLM_CASES_REGRESSED.html  회귀   Base 정상 -> 모델 붕괴
    LLM_CASES_BOTHFAIL.html   양쪽 붕괴

카드 한 장 = 문서 하나. 이미지 세 장을 화면 폭에 꽉 차게 나란히 놓는다.
    원본  ->  Base 전처리 후(우리가 OCR 에 먹인 것)  ->  모델 전처리 후(VLM 이 실제로 본 것)
같은 크기 상자에 contain 으로 넣으므로 한쪽이 90도 누우면 그 자리에서 보인다.
양쪽 다 '원본에 무슨 짓을 했나'를 같은 자리에서 비교하는 배치다.

전처리 후 이미지는 로컬에서 재현하지 않는다 - eval 을 돌리면 서버 응답의 processed_image 가
runs/<ts>/processed/<src>.jpg 로 떨어지고(run_batch.py), AWS run 에서 회수해 쓴다.

CLI:
    python eval/llm_cases_report.py --sample          # 시안(값은 전부 가짜, 이미지는 실물)
    python eval/llm_cases_report.py --cases <json>    # 실제 채점 결과로
"""
from __future__ import annotations

import argparse
import base64
import glob
import io
import json
import os
import random

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, "LLM")
REPLAY_DIR = os.path.join(HERE, "data", "invoice_war", "images_replay")

THUMB_PX = 560       # 저장 해상도. 카드가 화면 폭을 셋으로 나눠 쓰므로 표시도 이 근처다
THUMB_Q = 60

GROUPS = ["정상", "회전 적용 · 정상 처리", "기울기 보정됨", "방향 판정 애매"]
RISK = "방향 판정 애매"

# groups: 이 파일에 실을 문서군. 전처리 축의 답은 방향 판정 애매 한 행이므로 기본은 위험군만이다.
# 회귀만 예외로 전 문서군을 싣는다 - 모델이 '정상 문서'를 망치는 것이 채택을 막는 가장 큰 리스크라
# 위험군만 실으면 그게 안 보인다.
KINDS = {
    "revived": {
        "file": "LLM_CASES_REVIVED.html",
        "title": "모델이 살린 것",
        "sub": "Base 붕괴 → 모델 정상",
        "groups": [RISK],
        "lead": "원본은 똑바른데 전처리 후가 돌아가 있으면, 원인은 모델 실력이 아니라 <b>우리 전처리</b>다. "
                "그건 모델을 바꾸지 않고 전처리만 고쳐도 회수되는 몫이다.",
    },
    "regressed": {
        "file": "LLM_CASES_REGRESSED.html",
        "title": "모델이 망친 것",
        "sub": "Base 정상 → 모델 붕괴",
        "groups": GROUPS,
        "lead": "모델을 채택하면 <b>새로 잃는 것</b>이다. 한 부류로 묶이는지, 흩어진 사고인지가 채택 여부를 가른다. "
                "<b>여기만 전 문서군을 싣는다</b> - 모델이 정상 문서를 망치는 것이 가장 큰 채택 리스크다.",
    },
    "bothfail": {
        "file": "LLM_CASES_BOTHFAIL.html",
        "title": "둘 다 틀린 것",
        "sub": "양쪽 붕괴",
        "groups": [RISK],
        "lead": "전처리로도 모델로도 안 되는 잔여다. 다음 라운드의 재료가 된다.",
    },
}


# ---------------------------------------------------------------- 이미지

def _thumb_b64(path: str, rotate: int = 0, cap_px: int = 0) -> str | None:
    """긴 변 THUMB_PX 로 줄여 base64 JPEG.

    rotate  시안에서 'Base 전처리 후' 판을 흉내낼 때만 쓴다.
    cap_px  시안에서 VLM 프로세서의 해상도 상한을 흉내낸다 - 먼저 이만큼 뭉갠 뒤 썸네일을 만들어
            모델이 실제로 본 화질이 눈에 보이게 한다.
    """
    try:
        from PIL import Image
    except ImportError:
        return None
    try:
        with Image.open(path) as im:
            im = im.convert("RGB")
            if rotate:
                im = im.rotate(rotate, expand=True)
            if cap_px:
                im = im.resize((max(1, im.width * cap_px // max(im.width, im.height)),
                                max(1, im.height * cap_px // max(im.width, im.height))),
                               Image.BILINEAR)
            im.thumbnail((THUMB_PX, THUMB_PX))
            buf = io.BytesIO()
            im.save(buf, format="JPEG", quality=THUMB_Q, optimize=True)
        return base64.b64encode(buf.getvalue()).decode("ascii")
    except Exception:
        return None


def _img(b64: str | None, alt: str) -> str:
    if not b64:
        return '<div class="box muted">이미지 없음</div>'
    return f'<div class="box"><img src="data:image/jpeg;base64,{b64}" alt="{alt}"></div>'


# ---------------------------------------------------------------- HTML

def esc(v) -> str:
    return (str(v).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            if v not in (None, "") else "")


def _card(case: dict) -> str:
    move = case.get("cellMove")
    move_html = (f'<b class="{"up" if move > 0 else "down"}">{move:+,}</b>' if isinstance(move, int)
                 else '<span class="muted">-</span>')
    panes = [
        ("원본", "손대기 전", case.get("origB64")),
        ("Base 전처리 후", "우리가 OCR 에 먹인 것", case.get("procB64")),
        ("모델 전처리 후", "VLM 이 실제로 본 것", case.get("vlmB64")),
    ]
    body = "".join(
        f'<div class="pane"><span class="lab">{lab} <span class="muted">{sub}</span></span>{_img(b64, lab)}</div>'
        for lab, sub, b64 in panes
    )
    return f'''    <figure class="shot" data-group="{esc(case.get("group"))}">
      <figcaption><b>{esc(case.get("docId"))}</b>
        <span class="tag">{esc(case.get("group"))}</span>
        셀 이동 {move_html}
        <span class="muted">· 전처리 {esc(case.get("preprocess") or "-")}</span></figcaption>
      <div class="pair">{body}</div>
    </figure>
'''


CSS = """
:root{--bg:#f6f8fa;--card:#ffffff;--line:#d0d7de;--fg:#1f2328;--muted:#59636e;
--up:#1a7f37;--down:#cf222e;--warn:#9a6700;--link:#0969da}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
font-family:'Segoe UI','Malgun Gothic','Apple SD Gothic Neo',system-ui,sans-serif;
font-size:14px;line-height:1.55;padding:clamp(14px,2.5vw,32px)}
a{color:var(--link);text-decoration:none;font-weight:500}
a:hover{text-decoration:underline}
h1{font-size:20px;margin:0}
.head{display:flex;justify-content:space-between;align-items:baseline;flex-wrap:wrap;gap:8px;max-width:1600px;margin:0 auto 6px}
.gen{color:var(--muted);font-size:12.5px}
.note{color:var(--muted);font-size:12.5px;max-width:1600px;margin:6px auto}
.note.warn{color:var(--warn);font-weight:600}
section{background:var(--card);border:1px solid var(--line);border-radius:10px;
padding:16px 18px;margin:18px auto;max-width:1600px;box-shadow:0 1px 2px rgba(27,31,36,.04)}
h2{font-size:16px;margin:0 0 10px}
.kpis{display:flex;flex-wrap:wrap;gap:10px;max-width:1600px;margin:0 auto}
.kpi{flex:1;min-width:140px;background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 16px}
.kpi .lab{color:var(--muted);font-size:12px}
.kpi b{font-size:24px;display:block;margin:2px 0}
.kpi.hot{border-color:#f0d99a;background:#fff8e6}
.kpi.hot b{color:var(--warn)}
.up{color:var(--up);font-weight:600}
.down{color:var(--down);font-weight:600}
.muted{color:var(--muted)}
.legend{color:var(--muted);font-size:12px;margin-top:8px}
.legend div+div{margin-top:5px}
code{background:#eff1f3;border:1px solid var(--line);border-radius:5px;padding:1px 6px;font-size:12px}
.tag{display:inline-block;font-size:11px;padding:1px 7px;border-radius:10px;border:1px solid var(--line);
color:var(--muted);background:#f6f8fa;font-weight:600}
/* 문서군 필터 */
.filters{display:flex;flex-wrap:wrap;gap:6px;margin:0 0 12px}
.filters button{appearance:none;background:none;border:1px solid var(--line);padding:5px 12px;
font:inherit;font-size:12.5px;font-weight:600;color:var(--muted);cursor:pointer;border-radius:20px}
.filters button:hover{color:var(--fg);background:#eef1f4}
.filters button[aria-pressed="true"]{background:var(--fg);border-color:var(--fg);color:#fff}
/* 카드: 문서 하나가 한 줄을 다 쓰고, 이미지 세 장이 폭을 삼등분한다 */
.shots{display:flex;flex-direction:column;gap:14px}
.shot{border:1px solid var(--line);border-radius:9px;padding:11px 12px;background:#f6f8fa;margin:0}
.shot figcaption{font-size:12.5px;color:var(--muted);margin-bottom:8px}
.pair{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}
.pane{display:flex;flex-direction:column;gap:4px;min-width:0}
.pane .lab{font-size:11.5px;color:var(--muted);font-weight:600}
.box{width:100%;height:560px;display:flex;align-items:center;justify-content:center;
background:#fff;border:1px solid var(--line);border-radius:6px;overflow:hidden;font-size:12px}
.box img{max-width:100%;max-height:100%;object-fit:contain;cursor:zoom-in;display:block}
.shot.big .box{height:1100px}
.shot.big .box img{cursor:zoom-out}
@media (max-width:900px){.pair{grid-template-columns:1fr}.box{height:420px}}
"""

JS = """
// 카드 클릭 = 세 장을 함께 확대(한 장만 커지면 비교가 깨진다)
document.addEventListener('click', function (e) {
  var box = e.target.closest ? e.target.closest('.shot .box') : null;
  if (box) box.closest('.shot').classList.toggle('big');
});
// 문서군 필터
(function () {
  var btns = [].slice.call(document.querySelectorAll('.filters button'));
  var cards = [].slice.call(document.querySelectorAll('.shot'));
  btns.forEach(function (b) {
    b.addEventListener('click', function () {
      var g = b.dataset.group;
      btns.forEach(function (x) { x.setAttribute('aria-pressed', x === b ? 'true' : 'false'); });
      cards.forEach(function (c) { c.hidden = !(g === '*' || c.dataset.group === g); });
      var n = cards.filter(function (c) { return !c.hidden; }).length;
      document.getElementById('shown').textContent = n.toLocaleString();
    });
  });
})();
"""


def render(kind: str, cases: list[dict], sample: bool, kept: list[str]) -> str:
    meta = KINDS[kind]
    counts = {g: sum(1 for c in cases if c.get("group") == g) for g in GROUPS}
    risk = counts.get("방향 판정 애매", 0)
    filters = ['<button data-group="*" aria-pressed="true">전체 '
               f'<span class="muted">{len(cases):,}</span></button>']
    for g in GROUPS:
        if counts.get(g):
            filters.append(f'<button data-group="{g}" aria-pressed="false">{g} '
                           f'<span class="muted">{counts[g]:,}</span></button>')
    only = ('<div class="note">이 파일은 <b>' + ' · '.join(kept) + '</b> 만 싣는다. '
            + ('전처리 축의 답은 이 한 행이고, 나머지 문서군은 계량표의 숫자로 충분하다.'
               if kept == [RISK] else
               '모델이 정상 문서를 망치는 것이 가장 큰 채택 리스크라 여기만 전 문서군을 본다.')
            + '</div>')
    banner = ('<div class="note warn">⚠️ 시안 - 값과 갈린 셀은 전부 가짜다. 이미지만 실물이고 '
              '&ldquo;전처리 후&rdquo; 판은 회전을 걸어 흉내낸 것이다. 배치와 읽는 순서를 보기 위한 파일이다.</div>'
              if sample else "")
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{meta['title']} · LLM 비교</title>
<style>{CSS}</style>
</head>
<body>

<div class="head">
  <h1>{meta['title']} <span class="muted" style="font-size:14px;font-weight:400">{meta['sub']}</span></h1>
  <div class="gen">전량 · <a href="LLM_REVIEW_PLAN.html">← LLM 비교</a></div>
</div>
{banner}
<div class="note">{meta['lead']}</div>
{only}

<div class="kpis">
  <div class="kpi"><div class="lab">문서</div><b id="shown">{len(cases):,}</b>
    <div class="sub muted">이 부류 전량</div></div>
  <div class="kpi hot"><div class="lab">방향 판정 애매</div><b>{risk:,}</b>
    <div class="sub muted">{(100 * risk / len(cases)) if cases else 0:.1f}% · 이 축의 핵심</div></div>
</div>

<section>
  <h2>사례 <span class="muted">(카드를 누르면 세 장이 함께 커진다)</span></h2>
  <div class="filters">{''.join(filters)}</div>
  <div class="shots">
{''.join(_card(c) for c in cases)}  </div>
  <div class="legend">
    <div><b>원본</b>은 손대기 전 스캔이다.
      <b>Base 전처리 후</b>는 우리가 OCR 에 먹인 바로 그 이미지(<code>processed_image</code>)로
      <code>runs/&lt;ts&gt;/processed/</code> 에서 가져온다.
      <b>모델 전처리 후</b>는 VLM 프로세서가 리사이즈 · 타일링한 뒤 실제로 본 이미지다 - 러너가 저장한다.</div>
    <div>세 장을 같은 크기 상자에 <code>contain</code> 으로 넣는다. 한쪽이 90도 누우면 상자 안에서 가로로 눕고
      위아래 여백이 생기므로 <b>어느 단계에서 무너졌는지가 그 자리에서 갈린다</b>.</div>
    <div>정렬은 <b>셀 이동이 큰 순</b>이다.</div>
  </div>
</section>

<script>{JS}</script>
</body>
</html>
"""


# ---------------------------------------------------------------- 시안 데이터

def _sample_cases(n: int = 6) -> list[dict]:
    """실물 이미지 + 가짜 값. Base 전처리 후 판은 회전을 걸어 '우리가 깬 문서'를 흉내낸다."""
    files = sorted(glob.glob(os.path.join(REPLAY_DIR, "**", "*.jpg"), recursive=True))
    if not files:
        raise SystemExit(f"replay 이미지를 찾지 못했다: {REPLAY_DIR}")
    rnd = random.Random(20260903)
    picked = rnd.sample(files, min(n, len(files)))
    plan = [
        ("방향 판정 애매", 90, "orientation 270° 적용 · margin 12", 34),
        ("방향 판정 애매", 90, "orientation 90° 적용 · margin 8", 27),
        ("방향 판정 애매", 180, "orientation 180° 적용 · margin 15", 19),
        ("회전 적용 · 정상 처리", 0, "orientation 90° 적용 · margin 61", 12),
        ("기울기 보정됨", 0, "deskew 3.2°", 8),
        ("정상", 0, "전처리 미적용", 5),
    ]
    cases = []
    for path, (group, rot, pre, move) in zip(picked, plan):
        cases.append({
            "docId": os.path.basename(path)[:24],
            "group": group,
            "cellMove": move,
            "preprocess": pre,
            "origB64": _thumb_b64(path),
            "procB64": _thumb_b64(path, rotate=rot),
            # 시안에서는 VLM 프로세서의 해상도 상한을 흉내내 뭉갠다(실제론 러너가 저장한 것)
            "vlmB64": _thumb_b64(path, cap_px=300),
        })
    cases.sort(key=lambda c: -(c.get("cellMove") or 0))
    return cases


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", action="store_true", help="시안 생성(값은 가짜, 이미지는 실물)")
    ap.add_argument("--kind", choices=sorted(KINDS), default="revived")
    ap.add_argument("--cases", help="실제 채점 결과 JSON")
    ap.add_argument("-n", type=int, default=6, help="시안 카드 수")
    ap.add_argument("--groups", help="수록 문서군(쉼표) 또는 all. 생략하면 부류별 기본값")
    args = ap.parse_args()

    if args.cases:
        # compare_cross.py --out 산출물을 그대로 받는다: {"summary":..., "docs":[...]}
        with open(args.cases, encoding="utf-8") as fh:
            data = json.load(fh)
        docs = data.get("docs") if isinstance(data, dict) else data
        want = {"revived": "revived", "regressed": "regressed", "bothfail": "bothfail"}[args.kind]
        cases = []
        for d in docs:
            if d.get("class") not in (want, None):
                continue
            move = d.get("cellMove")
            cases.append({
                "docId": os.path.basename(d.get("sourceFile") or d.get("docId") or "?")[:40],
                "group": d.get("group"),
                "cellMove": move,
                "preprocess": d.get("preprocess"),
                "origB64": _thumb_b64(d["imagePath"]) if d.get("imagePath") else None,
                "procB64": d.get("procB64"),   # runs/<ts>/processed/ 회수 후 채워진다
                "vlmB64": d.get("vlmB64"),     # VLM 러너가 저장한 입력 이미지
            })
        cases.sort(key=lambda c: -abs(c.get("cellMove") or 0))
        sample = False
    elif args.sample:
        cases = _sample_cases(args.n)
        sample = True
    else:
        ap.error("--sample 또는 --cases 중 하나가 필요하다")

    if args.groups == "all":
        kept = list(GROUPS)
    elif args.groups:
        kept = [g.strip() for g in args.groups.split(",") if g.strip()]
    else:
        kept = list(KINDS[args.kind]["groups"])
    # 문서군이 아직 없는 문서(samples 회수 전)는 거르지 않는다 - 라벨이 생기면 그때 걸러진다
    dropped = len(cases)
    cases = [c for c in cases if c.get("group") is None or c.get("group") in kept]
    dropped -= len(cases)

    os.makedirs(OUT_DIR, exist_ok=True)
    out = os.path.join(OUT_DIR, KINDS[args.kind]["file"])
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(render(args.kind, cases, sample, kept))
    note = f" · 문서군 밖 {dropped} 제외" if dropped else ""
    print(f"{out}  ({os.path.getsize(out) / 1024:.0f}KB · 카드 {len(cases)}{note})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
