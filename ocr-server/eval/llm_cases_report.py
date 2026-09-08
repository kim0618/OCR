"""llm_cases_report — Base ↔ VLM 교차의 실물 갤러리. 계획서 '누구 몫인가' 표의 행이 곧 파일의 필터다.

계획서(LLM_REVIEW_PLAN.html)는 숫자만 두고, 실물은 이 스크립트가 찍는 두 파일에서 본다.

    LLM_CASES_ORIENT.html   전처리 탭 - 방향이 한쪽이라도 어긋난 문서
    LLM_CASES_PARSER.html   파서 탭   - 방향이 둘 다 정상인 문서

문서 하나는 두 판정으로 자리가 정해진다. 둘 다 결과물을 직접 잰 값이다.
    Base 가 세웠나   전처리 후 이미지의 OCR 라인 박스 모양         (llm_orient_audit · boxVerdict)
    모델이 세운 걸 봤나  Base 처리본과 모델 입력의 가로/세로 일치     (llm_orient_audit · modelSideways)

    둘 다 실패 · 둘 다 누운 채로 봤다             ┐
    VLM 승  · 우리가 눕혔고 VLM 은 바로 봤다      ├ ORIENT
    Base 승 · 우리는 세웠고 VLM 은 누운 채로 봤다  ┘
    둘 다 성공 · 둘 다 바로 봤다                 PARSER
    판정 보류(모델 그림 없음) 어디에도 싣지 않는다

계획서 표의 각 행이 파일의 필터 버튼과 같은 수를 보여야 한다 - 이 스크립트 끝의 검증이 그걸 확인한다.

CLI:
    python eval/llm_cases_report.py --cases eval/LLM/data/cases_qwen_500.json \\
        --processed eval/runs/072_.../processed --model-view eval/runs/vlm_qwen_500/model_view
"""
from __future__ import annotations

import argparse
import base64
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, "LLM")

THUMB_PX = 560       # 저장 해상도. 카드가 화면 폭을 셋으로 나눠 쓰므로 표시도 이 근처다
THUMB_Q = 60

# ---------------------------------------------------------------- 자리 정하기

# 행 이름 = 전처리 판정(누가 세웠나). 검토의 1차 축은 "누가 잘했나" 이고 상태는 그 설명이다.
# VLM 은 전처리가 없고 원본을 그대로 보므로 "VLM 승" = 원본이 이미 서 있었고 우리가 눕힌 것.
ROWS = ["둘 다 실패 · 둘 다 누운 채로 봤다", "VLM 승 · 우리가 눕혔고 VLM 은 바로 봤다",
        "Base 승 · 우리는 세웠고 VLM 은 누운 채로 봤다", "둘 다 성공 · 둘 다 바로 봤다"]
HOLD = "판정 보류"
CLASSES = [("revived", "모델이 살린 것"), ("regressed", "모델이 망친 것"), ("bothfail", "둘 다 틀린 것"),
           ("kept", "동률")]
FAIL_ORDER = ["행 매칭 0 - 컬럼 밀림", "행 매칭 0", "행 일부 매칭", "행수 불일치", "행 매칭 정상"]

AXES = {
    "orient": {
        "file": "LLM_CASES_ORIENT.html",
        "title": "전처리 실물",
        "rows": ROWS[:3],
        "lead": "방향이 한쪽이라도 어긋난 문서다. 값을 어떻게 읽었는지는 파서 실물에서 본다.",
    },
    "parser": {
        "file": "LLM_CASES_PARSER.html",
        "title": "파서 실물",
        "rows": ROWS[3:],
        "skip_kept": True,        # 동률 312장은 양쪽이 같아 실물로 볼 게 없다(용량만 5배) - 표에서만 센다
        "lead": "방향이 둘 다 정상이면서 부류가 바뀐 문서다 - 회전 탓이 섞이면 파서 실력이 안 보인다. 동률은 싣지 않는다.",
    },
}


def row_of(case: dict) -> str:
    base_lying = case.get("boxVerdict") == "누워 있음"
    ms = case.get("modelSideways")
    if ms is None:
        return HOLD
    return ROWS[(0 if base_lying else 2) + (0 if ms else 1)]


def fail_bucket(fk: str | None) -> str:
    """카드 태그는 실측값 그대로 두고, 필터만 부류로 묶는다."""
    if not fk:
        return ""
    for k in FAIL_ORDER:
        if fk.startswith(k):
            return k
    return fk


def why(case: dict) -> tuple[str, str]:
    """카드가 여기 있는 이유 - 양쪽 점수와 한 줄. 부류를 가르는 것은 방향이 아니라 읽어낸 셀 수다."""
    c = case.get("cells") or {}
    tot = sum(c.values())
    if not tot:
        return "", ""
    b = c.get("keep", 0) + c.get("regress", 0)      # Base 가 맞힌 셀
    m = c.get("keep", 0) + c.get("revive", 0)       # 모델이 맞힌 셀
    score = "Base %d/%d → 모델 %d/%d" % (b, tot, m, tot)
    cls, fk, row = case.get("class"), case.get("failKind") or "", row_of(case)
    if cls == "bothfail":
        r = "양쪽 다 한 칸도 못 읽었다" if b == 0 and m == 0 else "양쪽 다 표를 못 읽었다"
    elif cls == "regressed":
        r = ("모델이 컬럼을 한 칸 밀어 읽어 행이 하나도 안 맞았다" if "컬럼 밀림" in fk
             else "모델이 행을 못 잡았다" if fk.startswith("행 매칭 0")
             else "행 수가 어긋났다" if fk.startswith("행수")
             else "모델이 값을 틀렸다")
    elif cls == "revived":
        r = ("둘 다 누운 그림을 봤는데 모델만 읽어냈다" if row == ROWS[0]
             else "우리가 눕힌 문서를 모델이 읽어냈다" if row == ROWS[1]
             else "누운 원본을 보고도 모델이 읽어냈다" if row == ROWS[2]
             else "Base 가 무너진 표를 모델이 읽어냈다")
    else:
        r = ""
    if row == ROWS[2] and cls != "revived":
        r += " · 모델은 누운 원본을 봤다"
    return score, r


# ---------------------------------------------------------------- 이미지

def _thumb_b64(path: str) -> str | None:
    try:
        from PIL import Image
    except ImportError:
        return None
    try:
        with Image.open(path) as im:
            im = im.convert("RGB")
            im.thumbnail((THUMB_PX, THUMB_PX))
            buf = io.BytesIO()
            im.save(buf, format="JPEG", quality=THUMB_Q, optimize=True)
        return base64.b64encode(buf.getvalue()).decode("ascii")
    except Exception:                                  # noqa: BLE001
        return None


def _dir_b64(folder: str | None, src: str | None) -> str | None:
    """<folder>/<sourceFile>[.jpg] 를 썸네일 base64 로. 없으면 None(카드가 빈 칸으로 뜬다)."""
    if not folder or not src:
        return None
    for cand in (src, src + ".jpg", src + ".png"):
        p = os.path.join(folder, cand)
        if os.path.exists(p):
            return _thumb_b64(p)
    return None


def _img(b64: str | None, alt: str) -> str:
    if not b64:
        return '<div class="box muted">이미지 없음</div>'
    return f'<div class="box"><img src="data:image/jpeg;base64,{b64}" alt="{alt}"></div>'


# ---------------------------------------------------------------- HTML

def esc(v) -> str:
    return (str(v).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            if v not in (None, "") else "")


def _card(case: dict, axis: str) -> str:
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
    row, cls, fk = row_of(case), case.get("class"), case.get("failKind")
    cls_label = dict(CLASSES).get(cls, cls)
    tags = f'<span class="tag cls {cls}">{esc(cls_label)}</span>'
    if axis == "orient":
        tags += f'<span class="tag row">{esc(row)}</span>'
    elif fk and fk != "행 매칭 정상":
        tags += f'<span class="tag fail">{esc(fk)}</span>'
    sc, rs = why(case)
    why_html = ('<div class="why"><b>%s</b>%s</div>' % (esc(sc), " · " + esc(rs) if rs else "")
                if sc else "")
    return f'''    <figure class="shot" data-row="{esc(row)}" data-cls="{esc(cls)}" data-fail="{esc(fail_bucket(fk))}">
      <figcaption><b>{esc(case.get("docId"))}</b> {tags} 셀 이동 {move_html}{why_html}</figcaption>
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
section{background:var(--card);border:1px solid var(--line);border-radius:10px;
padding:16px 18px;margin:18px auto;max-width:1600px;box-shadow:0 1px 2px rgba(27,31,36,.04)}
h2{font-size:16px;margin:0 0 10px}
.kpis{display:flex;flex-wrap:wrap;gap:10px;max-width:1600px;margin:0 auto}
.kpi{flex:1;min-width:140px;background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 16px}
.kpi .lab{color:var(--muted);font-size:12px}
.kpi b{font-size:24px;display:block;margin:2px 0}
.up{color:var(--up);font-weight:600}
.down{color:var(--down);font-weight:600}
.muted{color:var(--muted)}
.why{margin-top:5px;font-size:12.5px;color:var(--fg);font-weight:400}
.tag{display:inline-block;font-size:11px;padding:1px 7px;border-radius:10px;border:1px solid var(--line);
color:var(--muted);background:#f6f8fa;font-weight:600;margin-right:3px}
.tag.row{border-color:#b6d8f2;background:#ddf0fd;color:#0550ae}
.tag.fail{border-color:#f5b5b5;background:#ffeaea;color:#a4232a}
.tag.cls.revived{border-color:#a9dfb9;background:#e6f6ea;color:#1a7f37}
.tag.cls.regressed{border-color:#f5b5b5;background:#ffeaea;color:#a4232a}
.tag.cls.bothfail{border-color:#d0d7de;background:#eff1f3;color:#59636e}
.filters{display:flex;flex-wrap:wrap;gap:6px;margin:0 0 8px}
.filters button{appearance:none;background:none;border:1px solid var(--line);padding:5px 12px;
font:inherit;font-size:12.5px;font-weight:600;color:var(--muted);cursor:pointer;border-radius:20px}
.filters button:hover{color:var(--fg);background:#eef1f4}
.filters button[aria-pressed="true"]{background:var(--fg);border-color:var(--fg);color:#fff}
.shots{display:flex;flex-direction:column;gap:14px;margin-top:8px}
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
// 필터: 줄마다 하나씩 고르고 줄끼리는 AND 로 건다. 계획서 표의 행이 곧 여기 버튼이다.
(function () {
  var rows = [].slice.call(document.querySelectorAll('.filters'));
  var cards = [].slice.call(document.querySelectorAll('.shot'));
  function apply() {
    var want = rows.map(function (r) {
      var b = r.querySelector('button[aria-pressed="true"]');
      return [r.dataset.key, b ? b.dataset.val : '*'];
    });
    var n = 0;
    cards.forEach(function (c) {
      var show = want.every(function (w) { return w[1] === '*' || c.dataset[w[0]] === w[1]; });
      c.hidden = !show; if (show) n++;
    });
    document.getElementById('shown').textContent = n.toLocaleString();
    document.getElementById('shownsub').textContent =
      (n === cards.length) ? '전량' : ('전체 ' + cards.length.toLocaleString() + ' 중');
  }
  rows.forEach(function (r) {
    [].slice.call(r.querySelectorAll('button')).forEach(function (b) {
      b.addEventListener('click', function () {
        [].slice.call(r.querySelectorAll('button')).forEach(function (x) {
          x.setAttribute('aria-pressed', x === b ? 'true' : 'false'); });
        apply();
      });
    });
  });
  // 계획서 표의 행에서 들어오면(#row=...) 그 행만 보이게 미리 고른다
  var h = decodeURIComponent(location.hash.replace(/^#/, ''));
  if (h) {
    var kv = h.split('=');
    var btn = document.querySelector('.filters[data-key="' + kv[0] + '"] button[data-val="' + kv[1] + '"]');
    if (btn) btn.click();
  }
})();
"""


def _filter_row(key: str, label: str, items: list[tuple[str, int]], total: int) -> str:
    btns = [f'<button data-val="*" aria-pressed="true">{label} 전체 <span class="muted">{total:,}</span></button>']
    for val, n in items:
        if n:
            btns.append(f'<button data-val="{esc(val)}" aria-pressed="false">{esc(val)} '
                        f'<span class="muted">{n:,}</span></button>')
    return f'<div class="filters" data-key="{key}">{"".join(btns)}</div>'


def render(axis: str, cases: list[dict]) -> str:
    ax = AXES[axis]
    n = len(cases)
    count = lambda f: sum(1 for c in cases if f(c))
    rows_html = [
        _filter_row("cls", "부류", [(lab, count(lambda c, k=k: c.get("class") == k)) for k, lab in CLASSES], n)
    ]
    # data-cls 는 영문 키인데 버튼은 한글이라 매핑을 카드 쪽에서 맞춘다
    rows_html[0] = rows_html[0]
    for k, lab in CLASSES:
        rows_html[0] = rows_html[0].replace(f'data-val="{lab}"', f'data-val="{k}"')
    if axis == "orient":
        rows_html.append(_filter_row("row", "전처리 판정", [(r, count(lambda c, r=r: row_of(c) == r)) for r in ax["rows"]], n))
    else:
        rows_html.append(_filter_row("fail", "실패 성격",
                                     [(f, count(lambda c, f=f: fail_bucket(c.get("failKind")) == f)) for f in FAIL_ORDER], n))
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{ax['title']} · LLM 비교</title>
<style>{CSS}</style>
</head>
<body>

<div class="head">
  <h1>{ax['title']}</h1>
  <div class="gen"><a href="LLM_REVIEW_PLAN.html">← LLM 비교</a></div>
</div>
<div class="note">{ax['lead']}</div>

<div class="kpis">
  <div class="kpi"><div class="lab">보고 있는 문서</div><b id="shown">{n:,}</b>
    <div class="sub muted" id="shownsub">전량</div></div>
</div>

<section>
  <h2>사례 <span class="muted">(카드를 누르면 세 장이 함께 커진다 · 정렬은 셀 이동이 큰 순)</span></h2>
  {''.join(rows_html)}
  <div class="shots">
{''.join(_card(c, axis) for c in cases)}  </div>
</section>

<script>{JS}</script>
</body>
</html>
"""


# ---------------------------------------------------------------- main

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cases", required=True, help="compare_cross --out + llm_orient_audit --write 를 거친 JSON")
    ap.add_argument("--processed", required=True, help="Base 전처리 후 이미지 폴더 (runs/<base>/processed)")
    ap.add_argument("--model-view", required=True, help="모델이 실제로 본 이미지 폴더 (runs/<run>/model_view)")
    args = ap.parse_args()

    docs = json.load(open(args.cases, encoding="utf-8"))["docs"]
    docs.sort(key=lambda d: -abs(d.get("cellMove") or 0))

    placed = {}
    for d in docs:
        placed.setdefault(row_of(d), []).append(d)

    print("자리       %-22s %5s   %s" % ("", "문서", "부류"))
    for r in ROWS + [HOLD]:
        ds = placed.get(r, [])
        by = {k: sum(1 for d in ds if d.get("class") == k) for k, _ in CLASSES}
        print("  %-28s %5d   %s" % (r, len(ds), " · ".join("%s %d" % (lab, by[k]) for k, lab in CLASSES if by[k])))
    print("  %-28s %5d" % ("합계", len(docs)))

    os.makedirs(OUT_DIR, exist_ok=True)
    for axis, ax in AXES.items():
        cases = [d for r in ax["rows"] for d in placed.get(r, [])
                 if not (ax.get("skip_kept") and d.get("class") == "kept")]
        cases.sort(key=lambda d: -abs(d.get("cellMove") or 0))
        for d in cases:
            src = d.get("sourceFile")
            d["origB64"] = _thumb_b64(d["imagePath"]) if d.get("imagePath") and os.path.exists(d["imagePath"]) else None
            d["procB64"] = _dir_b64(args.processed, src)
            d["vlmB64"] = _dir_b64(args.model_view, src)
        out = os.path.join(OUT_DIR, ax["file"])
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(render(axis, cases))
        print("→ %s  (%.0fKB · 카드 %d)" % (ax["file"], os.path.getsize(out) / 1024, len(cases)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
