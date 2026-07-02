"""compare_tabs — 단계별(탭) 비교 + 탭간 회귀/개선 비교 HTML 생성기 (사이드카).

목적: 측정 스냅샷(baseline / 룰수정 / 마스터 / 파인튜닝 / 2차·3차 …)을 **탭**으로 보고,
      탭 두 개를 골라 **셀·필드별 개선(↑)/회귀(↓)** 와 점수 델타를 한눈에.

읽기 전용: runs/<ts>/<testset>/compare_summary.json (+ compare/<file>.json) 만 읽음.
기존 채점/리포트/metrics·sqlite 무수정. checker 경로(samples/·compare/·metrics) 안 건드림.

usage:
  python eval/compare_tabs.py --testset study --runs 052 053 054 --labels baseline rule master
  python eval/compare_tabs.py --testset study            # 최근 4개 run 자동
출력: runs/<lastTs>/<testset>/COMPARE_TABS.html
"""
from __future__ import annotations

import argparse
import glob
import html
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
RUNS = os.path.join(HERE, "runs")


def _load_run(ts_dir: str, testset_sub: str) -> dict | None:
    """run 한 개의 compare_summary.json -> {sourceFile: {field/cell acc/counts}} 로."""
    base = os.path.join(ts_dir, testset_sub)
    summ = os.path.join(base, "compare_summary.json")
    if not os.path.isfile(summ):
        return None
    d = json.load(open(summ, encoding="utf-8"))
    samples = {}
    for s in d.get("samples", []):
        sf = s.get("sourceFile")
        if not sf:
            continue
        samples[sf] = {
            "fieldAcc": s.get("fieldAcc"),
            "cellAcc": s.get("cellAcc"),
            "fieldScored": s.get("fieldScored"),
            "fieldMatch": s.get("fieldMatch"),
            "fieldMismatch": s.get("fieldMismatch"),
            "fieldMiss": s.get("fieldMiss"),
            "rowsGt": s.get("rowsGt"),
            "rowsExt": s.get("rowsExt"),
            "path": s.get("path"),
        }
    return {
        "runTs": d.get("runTs") or os.path.basename(ts_dir),
        "testset": d.get("testset"),
        "kind": d.get("kind"),
        "samples": samples,
    }


def _micro(samples: dict) -> dict:
    """샘플 묶음 -> micro(항목가중) field/cell 정확도 (우리 + 구글)."""
    fs = sum((s.get("fieldScored") or 0) for s in samples.values())
    fm = sum((s.get("fieldMatch") or 0) for s in samples.values())
    cacc = [s.get("cellAcc") for s in samples.values() if s.get("cellAcc") is not None]
    gc = [s.get("googleCellAcc") for s in samples.values() if s.get("googleCellAcc") is not None]
    gf = [s.get("googleFieldAcc") for s in samples.values() if s.get("googleFieldAcc") is not None]
    return {
        "n": len(samples),
        "fieldMicro": (fm / fs) if fs else None,
        "cellMacro": (sum(cacc) / len(cacc)) if cacc else None,
        "googleFieldMicro": (sum(gf) / len(gf)) if gf else None,
        "googleCellMacro": (sum(gc) / len(gc)) if gc else None,
        "fieldScored": fs,
    }


def _clean_nm(s) -> str:
    """fn_get_item_name_clean 모사: 괄호내용·공백 제거 후 소문자."""
    if not s:
        return ""
    s = re.sub(r"\(.*?\)", "", str(s))
    return re.sub(r"\s+", "", s).lower()


def war_google_baseline(gt_path: str, sample_limit: int = 500) -> dict:
    """war GT(구글 raw 포함) -> 구글 품목명 기준선. 우리 컬럼은 미실행(None).

    구글 품목명 정확도 = 구글 raw(itemName)가 정답 정식명(itemNameMaster)과
    정규화 후 일치하는 행 비율 (매칭 전 = raw 인식 기준).
    """
    import json as _json
    d = _json.load(open(gt_path, encoding="utf-8"))
    docs = d.get("documents", {})
    samples = {}
    agg_m = agg_t = 0
    for i, (key, doc) in enumerate(docs.items()):
        rows = doc.get("normalizedResult", {}).get("tableRows", [])
        m = t = 0
        for r in rows:
            gold = r.get("itemNameMaster")
            if not gold:
                continue
            t += 1
            if _clean_nm(r.get("itemName")) == _clean_nm(gold):
                m += 1
        if t == 0:
            continue
        agg_m += m
        agg_t += t
        if len(samples) < sample_limit:
            samples[key] = {
                "fieldAcc": None, "cellAcc": None,        # 우리 = 미실행
                "fieldMismatch": None, "fieldMiss": None,
                "googleFieldAcc": None,                    # field-level은 GT=구글이라 순환 → 생략
                "googleCellAcc": m / t,                    # 구글 품목명(raw→정답) 정확도
                "path": "google-raw", "rowsGt": t,
            }
    return {
        "runTs": "war-GT (구글 raw)", "testset": "invoice_war", "kind": "google-baseline",
        "samples": samples,
        "_aggGoogleName": (agg_m / agg_t) if agg_t else None,
        "_aggDocs": len(docs), "_aggRows": agg_t,
    }


def _fmt_pct(x) -> str:
    return "-" if x is None else f"{x * 100:.1f}%"


def build_html(runs: list[dict], labels: list[str]) -> str:
    # 데이터를 JS로 임베드 → 탭/탭간비교 클라이언트에서 즉시
    payload = []
    for run, label in zip(runs, labels):
        payload.append({
            "label": label,
            "runTs": run["runTs"],
            "micro": _micro(run["samples"]),
            "samples": run["samples"],
        })
    data_json = json.dumps(payload, ensure_ascii=False)

    css = """
:root{--bg:#0f1115;--card:#1a1d24;--fg:#e6e6e6;--muted:#8b93a1;--line:#2a2f3a;
--link:#6cabff;--good:#2ea043;--bad:#e5534b;--warn:#d29922;--up:#1f6feb;--down:#da3633}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);
font:14px/1.5 -apple-system,Segoe UI,Roboto,'Malgun Gothic',sans-serif}
.wrap{max-width:1400px;margin:0 auto;padding:20px}
h1{font-size:20px;margin:0 0 4px}.muted{color:var(--muted)}
.tabbar{display:flex;gap:6px;flex-wrap:wrap;margin:16px 0;border-bottom:1px solid var(--line)}
.tab{padding:8px 14px;background:var(--card);border:1px solid var(--line);border-bottom:none;
border-radius:8px 8px 0 0;cursor:pointer;color:var(--muted)}
.tab.active{color:var(--fg);background:#222732;font-weight:600}
.kpi{display:flex;gap:16px;flex-wrap:wrap;margin:14px 0}
.kpi .box{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 18px}
.kpi .v{font-size:22px;font-weight:700}.kpi .l{color:var(--muted);font-size:12px}
table{width:100%;border-collapse:collapse;margin-top:10px;font-size:13px}
th,td{padding:6px 10px;border-bottom:1px solid var(--line);text-align:left}
th{color:var(--muted);font-weight:600;cursor:pointer}
td.num{text-align:right;font-variant-numeric:tabular-nums}
.up{color:var(--good)}.down{color:var(--bad)}.same{color:var(--muted)}
.pill{padding:1px 7px;border-radius:10px;font-size:11px}
.sel{background:var(--card);color:var(--fg);border:1px solid var(--line);border-radius:8px;padding:6px 10px;margin-right:8px}
.panel{display:none}.panel.active{display:block}
.legend{margin:8px 0;color:var(--muted);font-size:12px}
"""

    js = """
const DATA = __DATA__;
function pct(x){return x==null?'-':(x*100).toFixed(1)+'%';}
function el(t,c,h){const e=document.createElement(t);if(c)e.className=c;if(h!=null)e.innerHTML=h;return e;}

function renderTabs(){
  const bar=document.getElementById('tabbar'), body=document.getElementById('body');
  DATA.forEach((d,i)=>{
    const t=el('div','tab'+(i===0?' active':''),`${i+1}. ${d.label}`);
    t.onclick=()=>activate(i); t.dataset.i=i; bar.appendChild(t);
  });
  const ct=el('div','tab','⚖️ 탭간 비교'); ct.onclick=()=>activate('cmp'); ct.dataset.i='cmp'; bar.appendChild(ct);
  DATA.forEach((d,i)=>body.appendChild(renderRunPanel(d,i)));
  body.appendChild(renderComparePanel());
}
function activate(i){
  document.querySelectorAll('.tab').forEach(t=>t.classList.toggle('active',t.dataset.i==i));
  document.querySelectorAll('.panel').forEach(p=>p.classList.toggle('active',p.dataset.i==i));
}
function renderRunPanel(d,i){
  const p=el('div','panel'+(i===0?' active':'')); p.dataset.i=i;
  const m=d.micro;
  const kpi=el('div','kpi');
  const gfm=(m.googleFieldMicro==null)?'—':pct(m.googleFieldMicro);
  const gcm=(m.googleCellMacro==null)?'—':pct(m.googleCellMacro);
  kpi.innerHTML=`<div class="box"><div class="v">${pct(m.fieldMicro)}</div><div class="l">우리 필드정확도 (micro)</div></div>
  <div class="box"><div class="v muted">${gfm}</div><div class="l">구글 필드정확도</div></div>
  <div class="box"><div class="v">${pct(m.cellMacro)}</div><div class="l">우리 셀정확도 (macro)</div></div>
  <div class="box"><div class="v muted">${gcm}</div><div class="l">구글 셀정확도</div></div>
  <div class="box"><div class="v">${m.n}</div><div class="l">샘플 수</div></div>
  <div class="box"><div class="v muted" style="font-size:14px">${d.runTs}</div><div class="l">run</div></div>`;
  p.appendChild(kpi);
  const tbl=el('table'); tbl.innerHTML=`<thead><tr>
    <th>파일<br><span class="muted">sourceFile</span></th>
    <th>경로<br><span class="muted">path</span></th>
    <th>우리 필드정확도<br><span class="muted">our field (vs 정답)</span></th>
    <th>구글 필드정확도<br><span class="muted">google field</span></th>
    <th>우리 셀정확도<br><span class="muted">our cell</span></th>
    <th>구글 셀정확도<br><span class="muted">google cell</span></th>
    <th>불일치<br><span class="muted">mismatch</span></th>
    <th>누락<br><span class="muted">miss</span></th></tr></thead>`;
  const tb=el('tbody');
  Object.entries(d.samples).sort((a,b)=>(a[1].fieldAcc||0)-(b[1].fieldAcc||0)).forEach(([sf,s])=>{
    const gf=(s.googleFieldAcc==null)?'<span class="muted">—</span>':pct(s.googleFieldAcc);
    const gc=(s.googleCellAcc==null)?'<span class="muted">—</span>':pct(s.googleCellAcc);
    tb.appendChild(el('tr',null,`<td>${sf}</td><td class="muted">${s.path||''}</td>
      <td class="num">${pct(s.fieldAcc)}</td><td class="num">${gf}</td>
      <td class="num">${pct(s.cellAcc)}</td><td class="num">${gc}</td>
      <td class="num">${s.fieldMismatch||0}</td><td class="num">${s.fieldMiss||0}</td>`));
  });
  tbl.appendChild(tb); p.appendChild(tbl); return p;
}
function renderComparePanel(){
  const p=el('div','panel'); p.dataset.i='cmp';
  const opts=DATA.map((d,i)=>`<option value="${i}">${i+1}. ${d.label}</option>`).join('');
  p.innerHTML=`<div style="margin:12px 0">
    <select class="sel" id="baseSel">${opts}</select> →
    <select class="sel" id="tgtSel">${opts}</select>
    <span class="legend">정답 기준 개선<span class="up"> ▲</span> / 회귀<span class="down"> ▼</span> (field · cell 정확도 델타)</span>
  </div><div id="cmpOut"></div>`;
  setTimeout(()=>{
    const b=document.getElementById('baseSel'), t=document.getElementById('tgtSel');
    if(DATA.length>1){t.value=1;}
    const run=()=>renderDiff(+b.value,+t.value);
    b.onchange=run; t.onchange=run; run();
  },0);
  return p;
}
function renderDiff(bi,ti){
  const out=document.getElementById('cmpOut'); const A=DATA[bi], B=DATA[ti];
  let fUp=0,fDown=0,cUp=0,cDown=0;
  const keys=new Set([...Object.keys(A.samples),...Object.keys(B.samples)]);
  const rows=[];
  keys.forEach(sf=>{
    const a=A.samples[sf]||{}, b=B.samples[sf]||{};
    const df=(b.fieldAcc??0)-(a.fieldAcc??0), dc=(b.cellAcc??0)-(a.cellAcc??0);
    if(df>1e-9)fUp++; else if(df<-1e-9)fDown++;
    if(dc>1e-9)cUp++; else if(dc<-1e-9)cDown++;
    rows.push({sf,af:a.fieldAcc,bf:b.fieldAcc,df,ac:a.cellAcc,bc:b.cellAcc,dc});
  });
  rows.sort((x,y)=>x.df-y.df);
  const dcls=v=>v>1e-9?'up':(v<-1e-9?'down':'same');
  const sgn=v=>(v>0?'+':'')+(v*100).toFixed(1);
  let h=`<div class="kpi">
    <div class="box"><div class="v up">${fUp}</div><div class="l">field 개선</div></div>
    <div class="box"><div class="v down">${fDown}</div><div class="l">field 회귀</div></div>
    <div class="box"><div class="v up">${cUp}</div><div class="l">cell 개선</div></div>
    <div class="box"><div class="v down">${cDown}</div><div class="l">cell 회귀</div></div></div>`;
  h+='<table><thead><tr><th>sourceFile</th><th>field A→B (Δ)</th><th>cell A→B (Δ)</th></tr></thead><tbody>';
  rows.forEach(r=>{
    h+=`<tr><td>${r.sf}</td>
      <td class="num">${pct(r.af)}→${pct(r.bf)} <span class="${dcls(r.df)}">${sgn(r.df)}</span></td>
      <td class="num">${pct(r.ac)}→${pct(r.bc)} <span class="${dcls(r.dc)}">${sgn(r.dc)}</span></td></tr>`;
  });
  h+='</tbody></table>';
  out.innerHTML=h;
}
renderTabs();
"""
    js = js.replace("__DATA__", data_json)
    return f"""<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8">
<title>compare tabs</title><style>{css}</style></head><body><div class="wrap">
<h1>단계별 비교 (탭) <span class="muted">· 우리 vs 구글 · 탭간 개선/회귀</span></h1>
<div class="muted">각 탭 = 측정 스냅샷 · 마지막 탭 = 탭간 비교 · 점수는 모두 <b>정답(GT) 기준</b></div>
<div class="legend">⚠️ 구글 컬럼은 <b>war 송장 데이터</b>에서만 채워짐 (study 데모셋엔 구글 미적용 → —). war GT는 구글 raw를 담고 있어 별도 실행 없이도 구글 기준선 산출 가능.</div>
<div class="tabbar" id="tabbar"></div><div id="body"></div></div>
<script>{js}</script></body></html>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--testset", default="study")
    ap.add_argument("--runs", nargs="*", default=None, help="run ts prefix들 (예: 052 053 054). 생략시 최근 4개")
    ap.add_argument("--labels", nargs="*", default=None)
    ap.add_argument("--war-gt", dest="war_gt", default=None,
                    help="war GT 경로 → 구글 품목명 기준선 탭 추가 (이미지 불필요)")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    all_runs = sorted(d for d in glob.glob(os.path.join(RUNS, "*")) if os.path.isdir(d))
    if a.runs:
        chosen = []
        for r in a.runs:
            hit = [d for d in all_runs if os.path.basename(d).startswith(r)]
            if hit:
                chosen.append(hit[-1])
    else:
        chosen = all_runs[-4:]

    runs, used = [], []
    for d in chosen:
        r = _load_run(d, a.testset)
        if r:
            runs.append(r)
            used.append(d)

    labels = a.labels if (a.labels and len(a.labels) == len(runs)) else [
        os.path.basename(d).split("_")[0] for d in used]

    if not runs:
        print("no runs with compare_summary.json for testset", a.testset, "(and no --war-gt)")
        return

    # 전체(크로스-run) 뷰라 runs/ 최상위에 생성
    out = a.out or os.path.join(RUNS, "COMPARE_TABS.html")
    open(out, "w", encoding="utf-8").write(build_html(runs, labels))
    print("wrote", out)
    for r, l in zip(runs, labels):
        m = _micro(r["samples"])
        print(f"  tab [{l}] {r['runTs']}: field {_fmt_pct(m['fieldMicro'])} / cell {_fmt_pct(m['cellMacro'])} / n={m['n']}")


if __name__ == "__main__":
    main()
