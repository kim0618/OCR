"""고객 POC 1단계 화면(OCR 실행)을 실측 데이터로 생성한다.

v22(=260811_1105_wf80) 리포트의 판정 행을 그대로 쓴다. 크롭 이미지는 리포트에
들어 있는 imgB64 를 그대로 심으므로 별도 크롭 파일이 없어도 재현된다.

이 화면이 지키는 것:
  - <정답을 표시하지 않는다>. 제품 실행 화면은 무엇이 틀렸는지 모르는 상태다.
    검수 결과는 다음 단계(못 읽은 항목) 화면의 몫이다.
  - 원본 문서 이미지는 고객 데이터라 로컬에 없다. 없는 것을 그리지 않고
    <실제 인식 크롭>을 그대로 보여주고 그 사실을 화면에 적는다.

    python eval/finetune/demo/build_poc_run_screen.py
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from recount_reviewed_gt import HERE  # noqa: E402

DEFAULT_RUN = "260811_1105_wf80"
OUT = HERE.parents[3] / "docs" / "POC_RUN_SCREEN_v22.html"   # OCR/docs/


def load(run: str) -> dict:
    d = next((p for p in HERE.glob(f"*_{run}") if p.is_dir()), None)
    if d is None:
        raise SystemExit(f"리포트 폴더가 없습니다: demo/*_{run}")
    return json.loads((d / f"DEMO_REPORT_{run}.json").read_text(encoding="utf-8"))


def esc(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default=DEFAULT_RUN)
    args = ap.parse_args()
    rep = load(args.run)

    # 표시용 행 — 리포트 순서를 그대로 유지한다(품명별 묶음).
    rows = []
    for t in rep["targets"]:
        for r in t["rows"]:
            rows.append({"group": t["name"], "base": r["base"], "img": r["imgB64"],
                         "path": r["path"]})
    groups = [t["name"] for t in rep["targets"]]
    reads = Counter(r["base"] for r in rows)

    stat_cards = [
        ("판독 위치", f"{len(rows)}", "고객 문서에서 추출된 품명 셀"),
        ("품명 종류", f"{len(groups)}", "이 화면에 포함된 품명"),
        ("서로 다른 판독", f"{len(reads)}", "같은 품명도 다르게 읽힐 수 있음"),
        ("실행 모델", "base", "학습 전 · 공식 배포 모델"),
        ("정답 대조", "안 함", "이 화면은 검수 전 결과입니다"),
    ]
    stats = "".join(
        f'<div class="stat"><span>{esc(k)}</span><b>{esc(v)}</b><small>{esc(c)}</small></div>'
        for k, v, c in stat_cards)

    chips = "".join(
        f'<button class="chip{" on" if i == 0 else ""}" data-g="{i}">{esc(g)}'
        f'<i>{sum(1 for r in rows if r["group"] == g)}</i></button>'
        for i, g in enumerate(groups))

    trs = []
    for i, r in enumerate(rows):
        gi = groups.index(r["group"])
        trs.append(
            f'<tr data-i="{i}" data-g="{gi}"{" class=on" if i == 0 else ""}>'
            f'<td class="no">{i + 1}</td>'
            f'<td class="cropcell"><img src="data:image/jpeg;base64,{r["img"]}" alt=""></td>'
            f'<td class="read">{esc(r["base"])}</td>'
            f'<td class="grp">{esc(r["group"])}</td></tr>')

    payload = json.dumps(
        [{"i": i, "img": r["img"], "base": r["base"], "group": r["group"],
          "path": r["path"]} for i, r in enumerate(rows)], ensure_ascii=False)

    html = TEMPLATE.format(
        run=esc(rep["runTag"]), docs=f'{rep["basisDocs"]:,}',
        judge=f'{rep["pool"]["judgeItem"]:,}', stats=stats, chips=chips,
        rows="".join(trs), n=len(rows), payload=payload,
        gen=esc(rep["generatedAt"]))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html, encoding="utf-8")
    print(f"wrote {OUT}")
    print(f"  {len(rows)} 행 · 품명 {len(groups)}종 · 서로 다른 판독 {len(reads)}종")
    for k, v in reads.most_common():
        print(f"     {v:3d}  {k}")


TEMPLATE = """<!doctype html>
<html lang="ko" data-theme="light">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>MySuit OCR · 01 OCR 실행 (실측 {run})</title>
<style>
:root{{--bg:#f6f7fb;--panel:#fff;--panel2:#f1f3f7;--text:#172033;--muted:#697386;
 --line:#dfe3ea;--cyan:#0794b3;--cyan2:#e8f7fa;--blue:#416fc1;--blue2:#edf2ff;
 --amber:#b66b08;--amber2:#fff4df;--shadow:0 2px 14px rgba(26,38,62,.09)}}
[data-theme=dark]{{--bg:#080b12;--panel:#10151e;--panel2:#171e2a;--text:#edf2f7;
 --muted:#8a99ad;--line:#293242;--cyan:#18b9d8;--cyan2:#102b33;--blue2:#16233c;
 --amber2:#302515;--shadow:0 3px 18px rgba(0,0,0,.45)}}
*{{box-sizing:border-box}}
html,body{{margin:0;height:100%;background:var(--bg);color:var(--text);
 font-family:Pretendard,"Noto Sans KR","Malgun Gothic",Arial,sans-serif}}
button{{font:inherit}}
.app{{height:100vh;display:flex;overflow:hidden}}
.side{{width:190px;flex:none;background:var(--panel);border-right:1px solid var(--line);
 padding:17px 13px;display:flex;flex-direction:column}}
.brand{{display:flex;align-items:center;justify-content:space-between;font-size:16px;
 font-weight:900;margin-bottom:20px}}
.logo{{width:30px;height:30px;border-radius:9px;background:var(--cyan);color:#fff;
 display:grid;place-items:center;font-size:11px;font-style:italic}}
.nav-label{{display:block;color:var(--muted);font-size:9px;font-weight:800;margin:21px 0 8px}}
.project-box{{border:1px solid var(--line);background:var(--panel2);border-radius:8px;
 padding:9px;font-size:10px;font-weight:700}}
.nav{{display:grid;gap:7px}}
.nav-btn{{border:0;background:transparent;color:var(--muted);border-radius:10px;padding:10px 9px;
 display:grid;grid-template-columns:27px 1fr;align-items:center;gap:7px;text-align:left;cursor:pointer}}
.nav-btn.on{{background:var(--cyan2);color:var(--cyan);box-shadow:inset 3px 0 0 var(--cyan)}}
.nav-num{{width:24px;height:24px;border-radius:50%;background:var(--panel2);display:grid;
 place-items:center;font-size:8px;font-weight:900}}
.nav-btn.on .nav-num{{background:var(--cyan);color:#fff}}
.nav-copy b{{display:block;font-size:11px}}.nav-copy span{{font-size:8px;opacity:.8}}
.side-foot{{margin-top:auto;padding-top:12px;border-top:1px solid var(--line);font-size:8px;
 line-height:1.55;color:var(--muted)}}
.shell{{flex:1;min-width:0;display:flex;flex-direction:column}}
.header{{height:56px;flex:none;background:var(--panel);border-bottom:1px solid var(--line);
 display:flex;align-items:center;justify-content:space-between;padding:0 18px}}
.header-title{{font-size:13px;font-weight:900}}
.crumb{{font-size:9px;color:var(--muted);margin-left:8px}}
.pill{{display:inline-flex;align-items:center;gap:5px;border-radius:999px;padding:5px 8px;
 font-size:8px;font-weight:900;white-space:nowrap}}
.pill.real{{background:var(--cyan2);color:var(--cyan)}}
.pill.internal{{background:var(--blue2);color:var(--blue)}}
.pill.warn{{background:var(--amber2);color:var(--amber)}}
.dot{{width:6px;height:6px;border-radius:50%;background:currentColor}}
.btn{{border:1px solid var(--line);background:var(--panel);color:var(--text);border-radius:9px;
 padding:8px 10px;font-size:9px;font-weight:800;cursor:pointer}}
.btn:hover{{border-color:var(--cyan);color:var(--cyan)}}
.btn.primary{{background:var(--cyan);border-color:var(--cyan);color:#fff}}
.workspace{{flex:1;min-height:0;padding:16px;display:flex;flex-direction:column}}
.view-head{{display:flex;align-items:flex-start;justify-content:space-between;gap:12px;
 margin-bottom:10px;flex:none}}
.view-head h1{{margin:0 0 4px;font-size:19px;letter-spacing:-.04em}}
.view-head p{{margin:0;font-size:9px;line-height:1.5;color:var(--muted)}}
.head-actions{{display:flex;gap:7px;align-items:center}}
.stats{{display:grid;grid-template-columns:repeat(5,1fr);gap:8px;margin-bottom:10px;flex:none}}
.stat{{background:var(--panel);border-radius:10px;border:1px solid var(--line);padding:9px 11px}}
.stat span{{display:block;font-size:8px;color:var(--muted);margin-bottom:4px}}
.stat b{{font-size:15px}}
.stat small{{display:block;font-size:7px;color:var(--muted);margin-top:3px}}
.two{{display:grid;grid-template-columns:1fr 1.25fr;gap:10px;flex:1;min-height:0}}
.card{{background:var(--panel);border-radius:12px;box-shadow:var(--shadow);min-width:0;
 display:flex;flex-direction:column;overflow:hidden}}
.card-head{{display:flex;justify-content:space-between;align-items:flex-start;gap:10px;
 padding:13px;border-bottom:1px solid var(--line)}}
.card-head h2{{font-size:12px;margin:0 0 3px}}
.card-head p{{font-size:8px;color:var(--muted);margin:0}}
.docbar{{height:32px;flex:none;background:#273245;color:#fff;display:flex;align-items:center;
 justify-content:space-between;padding:0 11px;font-size:8px}}
.docbar b{{color:#28d4ef}}
.zoomarea{{flex:1;min-height:0;display:grid;place-items:center;padding:18px;background:var(--panel2)}}
.zoombox{{background:#fff;padding:14px 16px;border-radius:8px;box-shadow:0 5px 20px rgba(0,0,0,.14);
 max-width:100%}}
.zoombox img{{display:block;max-width:100%;image-rendering:-webkit-optimize-contrast}}
.zoommeta{{flex:none;padding:11px 13px;border-top:1px solid var(--line);display:grid;
 grid-template-columns:auto 1fr;gap:6px 12px;font-size:9px}}
.zoommeta dt{{color:var(--muted);font-weight:800}}
.zoommeta dd{{margin:0;font-weight:700;word-break:break-all}}
.chips{{display:flex;gap:6px;flex-wrap:wrap;padding:10px 13px;border-bottom:1px solid var(--line);
 flex:none}}
.chip{{border:1px solid var(--line);background:var(--panel);color:var(--muted);border-radius:99px;
 padding:5px 9px;font-size:9px;font-weight:800;cursor:pointer;display:inline-flex;gap:5px;
 align-items:center}}
.chip i{{font-style:normal;background:var(--panel2);border-radius:99px;padding:1px 5px;font-size:8px}}
.chip.on{{border-color:var(--cyan);color:var(--cyan);background:var(--cyan2)}}
.chip.on i{{background:var(--cyan);color:#fff}}
.tablewrap{{flex:1;min-height:0;overflow:auto}}
table{{width:100%;border-collapse:collapse;font-size:10px}}
thead th{{position:sticky;top:0;background:var(--panel2);text-align:left;font-size:8px;
 color:var(--muted);padding:7px 10px;border-bottom:1px solid var(--line);z-index:1}}
td{{padding:6px 10px;border-bottom:1px solid var(--line);vertical-align:middle}}
tr{{cursor:pointer}}
tr:hover td{{background:var(--panel2)}}
tr.on td{{background:var(--cyan2)}}
td.no{{color:var(--muted);font-size:8px;width:30px}}
td.cropcell{{width:190px}}
td.cropcell img{{display:block;height:22px;width:auto;max-width:180px;border-radius:2px}}
td.read{{font-weight:800}}
td.grp{{color:var(--muted);font-size:8px;max-width:190px;overflow:hidden;text-overflow:ellipsis;
 white-space:nowrap}}
.foot{{flex:none;padding:11px 13px;border-top:1px solid var(--line);display:flex;
 align-items:center;gap:7px;flex-wrap:wrap}}
.foot .lab{{font-size:8px;font-weight:900;color:var(--muted);margin-right:2px}}
.notice{{margin-top:10px;flex:none;border-radius:10px;background:var(--blue2);color:var(--blue);
 padding:10px 12px;font-size:9px;line-height:1.55}}
.notice b{{font-weight:900}}
.toast{{position:fixed;left:50%;bottom:24px;transform:translate(-50%,14px);background:#111826;
 color:#fff;padding:9px 14px;border-radius:9px;font-size:10px;opacity:0;pointer-events:none;
 transition:.18s}}
.toast.show{{opacity:1;transform:translate(-50%,0)}}
</style>
</head>
<body>
<div class="app">
  <aside class="side">
    <div class="brand">MySuit OCR<span class="logo">M</span></div>
    <div><span class="nav-label" style="margin-top:0">POC 프로젝트</span>
      <div class="project-box">거래명세서 · 품명 열</div></div>
    <span class="nav-label">CUSTOMER POC FLOW</span>
    <nav class="nav">
      <button class="nav-btn on"><span class="nav-num">01</span>
        <span class="nav-copy"><b>OCR 실행</b><span>제품 사용 방식</span></span></button>
      <button class="nav-btn"><span class="nav-num">02</span>
        <span class="nav-copy"><b>못 읽은 항목</b><span>개선 대상 확정</span></span></button>
      <button class="nav-btn"><span class="nav-num">03</span>
        <span class="nav-copy"><b>학습 분석</b><span>학습과 유지 비용</span></span></button>
      <button class="nav-btn"><span class="nav-num">04</span>
        <span class="nav-copy"><b>블라인드 검증</b><span>처음 보는 문서 확인</span></span></button>
      <button class="nav-btn"><span class="nav-num">05</span>
        <span class="nav-copy"><b>남은 항목과 처리</b><span>운영 처리 경로</span></span></button>
    </nav>
    <div class="side-foot">고객 공개용 POC 시안<br>실측 리포트 {run}<br>정답·학습 정보 미표시</div>
  </aside>

  <div class="shell">
    <header class="header">
      <div><span class="header-title">01 · OCR 실행</span>
        <span class="crumb">실측 데이터 · 리포트 {run}</span></div>
      <div style="display:flex;align-items:center;gap:7px">
        <span class="pill real"><span class="dot"></span>실제 인식 결과</span>
        <span class="pill warn">정답 미표시</span>
      </div>
    </header>

    <div class="workspace">
      <div class="view-head">
        <div><h1>제품은 이렇게 사용합니다</h1>
          <p>고객 문서 {docs}건에서 추출된 품명 셀을 학습 전 모델(base)로 읽은 결과입니다.
             행을 누르면 실제 인식 이미지를 확대해 볼 수 있습니다.</p></div>
        <div class="head-actions">
          <button class="btn">새 문서</button>
          <button class="btn primary" data-toast="시안 화면입니다. 값은 실측 리포트에서 가져왔습니다.">OCR 실행</button>
        </div>
      </div>

      <div class="stats">{stats}</div>

      <div class="two">
        <div class="card">
          <div class="docbar"><b>인식 이미지</b><span id="zoomIdx">1 / {n}</span></div>
          <div class="zoomarea"><div class="zoombox"><img id="zoomImg" src="" alt=""></div></div>
          <dl class="zoommeta">
            <dt>판독값</dt><dd id="mRead">—</dd>
            <dt>품명 묶음</dt><dd id="mGroup">—</dd>
            <dt>크롭 경로</dt><dd id="mPath">—</dd>
          </dl>
        </div>

        <div class="card">
          <div class="card-head">
            <div><h2>추출 결과 {n}건</h2>
              <p>학습 전 모델이 읽은 문자열 그대로입니다. 정답과 대조하지 않았습니다.</p></div>
            <span class="pill internal">base 모델</span>
          </div>
          <div class="chips"><button class="chip on" data-g="all">전체<i>{n}</i></button>{chips}</div>
          <div class="tablewrap">
            <table><thead><tr><th>#</th><th>인식 이미지</th><th>판독값</th><th>품명 묶음</th></tr></thead>
              <tbody id="tb">{rows}</tbody></table>
          </div>
          <div class="foot"><span class="lab">결과 내보내기</span>
            <button class="btn" data-toast="Excel(.xlsx) 내보내기는 시안입니다.">Excel</button>
            <button class="btn" data-toast="JSON 내보내기는 현재 제품에서 동작합니다.">JSON</button>
            <button class="btn" data-toast="Markdown 내보내기는 현재 제품에서 동작합니다.">Markdown</button>
            <button class="btn" data-toast="HWP 내보내기는 시안입니다.">HWP</button>
          </div>
        </div>
      </div>

      <div class="notice">
        <b>이 화면은 무엇이 틀렸는지 표시하지 않습니다.</b>
        실제 운영에서도 제품은 정답을 모른 채 읽습니다. 어떤 값이 잘못됐는지는
        다음 단계에서 검수로 확인합니다. — 원본 문서 이미지는 고객 데이터이므로 이 화면에는
        포함하지 않고, 인식에 실제로 사용된 이미지를 그대로 표시합니다.
        전체 평가 기준은 품명 셀 {judge}개입니다.
      </div>
    </div>
  </div>
</div>
<div class="toast" id="toast"></div>

<script>
const DATA={payload};
const tb=document.querySelector('#tb');
function pick(i){{
  const d=DATA[i];
  document.querySelectorAll('#tb tr').forEach(r=>r.classList.toggle('on',+r.dataset.i===i));
  document.querySelector('#zoomImg').src='data:image/jpeg;base64,'+d.img;
  document.querySelector('#zoomIdx').textContent=(i+1)+' / '+DATA.length;
  document.querySelector('#mRead').textContent=d.base;
  document.querySelector('#mGroup').textContent=d.group;
  document.querySelector('#mPath').textContent=d.path;
}}
tb.addEventListener('click',e=>{{const tr=e.target.closest('tr');if(tr)pick(+tr.dataset.i);}});
document.querySelectorAll('.chip').forEach(c=>c.addEventListener('click',()=>{{
  document.querySelectorAll('.chip').forEach(x=>x.classList.remove('on'));
  c.classList.add('on');
  const g=c.dataset.g;
  document.querySelectorAll('#tb tr').forEach(r=>{{
    r.style.display=(g==='all'||r.dataset.g===g)?'':'none';}});
}}));
const toast=document.querySelector('#toast');let t;
document.querySelectorAll('[data-toast]').forEach(b=>b.addEventListener('click',()=>{{
  toast.textContent=b.dataset.toast;toast.classList.add('show');
  clearTimeout(t);t=setTimeout(()=>toast.classList.remove('show'),1800);}}));
pick(0);
</script>
</body>
</html>
"""

if __name__ == "__main__":
    main()
