"""report_compare - 직전 run vs 이번 run 1:1 비교 리포트.

compare.html 생성:
  - 같은 testset의 직전 run이 있을 때만 생성 (없으면 None 반환)
  - run_all에서 render_report_html 이후 자동 호출

섹션:
  1. 전체 요약
  2. 이미지별 1:1 비교 (정렬)
  3. 필드(스칼라)별 비교 (정렬)
  4. 셀 컬럼별 비교 (정렬)
  5. 상세 변화 (개선/악화/값변화)

CLI: python eval/report_compare.py [--ts <run_ts>] [--testset <testset>]
"""

from __future__ import annotations

import glob
import json
import os
from typing import Any

import contract as C
from report import _FIELD_KO, _ko_field


_SORT_JS = """<script>
function st(t,c,n){var b=t.tBodies[0],r=[].slice.call(b.rows);
 var d=(t.getAttribute('data-sc')==c&&t.getAttribute('data-sd')=='asc')?'desc':'asc';
 r.sort(function(a,e){var x=a.cells[c].getAttribute('data-v'),y=e.cells[c].getAttribute('data-v');
  if(x===null)x=a.cells[c].innerText; if(y===null)y=e.cells[c].innerText;
  if(n){x=parseFloat(x);y=parseFloat(y);x=isNaN(x)?-1:x;y=isNaN(y)?-1:y;}
  else{x=(''+x).toLowerCase();y=(''+y).toLowerCase();}
  return (x<y?-1:x>y?1:0)*(d=='asc'?1:-1);});
 r.forEach(function(x){b.appendChild(x);});t.setAttribute('data-sc',c);t.setAttribute('data-sd',d);}
document.querySelectorAll('table.sortable').forEach(function(t){
 [].slice.call(t.tHead.rows[0].cells).forEach(function(h,i){h.onclick=function(){st(t,i,h.dataset.num=='1');};});});
function tog(el){
 var body=el.nextElementSibling;
 var open=body.style.display!=='none';
 body.style.display=open?'none':'';
 el.querySelector('.arr').textContent=open?'▶':'▼';}
</script>"""

_EXTRA_CSS = """
table.sortable th{cursor:pointer;user-select:none}
table.sortable th:hover{color:var(--fg)}
.tag-ok{display:inline-block;padding:2px 8px;border-radius:4px;
  background:#e9f7ec;border:1px solid #a7e0b5;color:#1a7f37;font-size:12px;font-weight:600}
.tag-bad{display:inline-block;padding:2px 8px;border-radius:4px;
  background:#ffeef0;border:1px solid #f5b0b8;color:#cf222e;font-size:12px;font-weight:600}
.tag-chg{display:inline-block;padding:2px 8px;border-radius:4px;
  background:#ffeef0;border:1px solid #f5b0b8;color:#cf222e;font-size:12px;font-weight:600}
h3.tog{cursor:pointer;user-select:none;display:flex;align-items:center;gap:8px}
h3.tog:hover{color:var(--link)}
h3.tog .arr{font-size:11px;color:var(--muted);min-width:12px}
.tog-body{overflow:hidden}
"""


def _find_prev_run_dir(run_dir: str, testset: str) -> str | None:
    """같은 testset의 직전 run 디렉토리 반환 (mtime 기준)."""
    current = os.path.realpath(run_dir)
    candidates: list[tuple[float, str]] = []
    for pattern in (
        os.path.join(C.RUNS_DIR, "*", "metrics.json"),
        os.path.join(C.RUNS_DIR, "*", "*", "metrics.json"),
    ):
        for p in glob.glob(pattern):
            d = os.path.dirname(p)
            if os.path.realpath(d) == current:
                continue
            try:
                m = json.load(open(p, encoding="utf-8"))
                if m.get("testset") == testset:
                    candidates.append((os.path.getmtime(p), d))
            except Exception:
                pass
    if not candidates:
        return None
    candidates.sort(reverse=True)
    return candidates[0][1]


def _load_run(run_dir: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    m = json.load(open(os.path.join(run_dir, "metrics.json"), encoding="utf-8"))
    cs = [json.load(open(p, encoding="utf-8"))
          for p in sorted(glob.glob(os.path.join(run_dir, "compare", "*.json")))]
    return m, cs


def _pct(a: float | None) -> str:
    return "n/a" if a is None else f"{a * 100:.1f}%"


def _fmt_ts(ts: str) -> str:
    import datetime as _dt
    import re as _re
    m = _re.search(r"(\d{8})_(\d{6})", ts)  # NNN_ 프리픽스 있어도 날짜 추출
    if m:
        try:
            return _dt.datetime.strptime(m.group(1) + m.group(2), "%Y%m%d%H%M%S").strftime("%Y-%m-%d %H:%M")
        except ValueError:
            pass
    return ts


def _delta_html(curr: float | None, prev: float | None) -> str:
    if curr is None or prev is None:
        return "<span class='muted'>·</span>"
    d = (curr - prev) * 100
    if abs(d) < 0.05:
        return "<span class='muted'>=</span>"
    cls, arrow = ("up", "▲") if d > 0 else ("down", "▼")
    return f"<span class='{cls}'>{arrow} {abs(d):.1f}%</span>"


def _acc_td(a: float | None) -> str:
    v = "" if a is None else f"{a:.4f}"
    return f"<td data-v='{v}'>{_pct(a)}</td>"


def _num_td(n: Any) -> str:
    return f"<td data-v='{n}'>{n}</td>"


def _name_td(key: str) -> str:
    """필드/컬럼키 한글+영문 표시 셀."""
    from trend import _esc
    ko = _FIELD_KO.get(key, "")
    if ko:
        return (f"<td><span>{_esc(ko)}</span>"
                f" <span class='muted' style='font-size:11.5px'>({_esc(key)})</span></td>")
    return f"<td>{_esc(key)}</td>"


def _cell_col_stats(compares: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """표 컬럼별 정확도 집계."""
    stats: dict[str, dict[str, Any]] = {}
    for d in compares:
        for row in d["table"]["rows"]:
            for ck, cell in row["cells"].items():
                if ck not in stats:
                    stats[ck] = {"scored": 0, "match": 0, "mismatch": 0, "ext_missing": 0}
                s = cell["status"]
                if s == "gt_empty":
                    continue
                stats[ck]["scored"] += 1
                if s in ("match", "mismatch", "ext_missing"):
                    stats[ck][s] += 1
    for v in stats.values():
        sc = v["scored"]
        v["accuracy"] = v["match"] / sc if sc else None
    return stats


def _changes_for_image(prev_d: dict[str, Any], curr_d: dict[str, Any]) -> list[dict[str, Any]]:
    """한 이미지에서 상태가 바뀐 필드/셀 목록."""
    _bad = {"mismatch", "ext_missing"}
    changes: list[dict[str, Any]] = []

    # 스칼라 필드
    pf = prev_d["fields"]["perField"]
    cf = curr_d["fields"]["perField"]
    for label in sorted(set(list(pf.keys()) + list(cf.keys()))):
        ps = pf.get(label, {}).get("status", "gt_empty")
        cs = cf.get(label, {}).get("status", "gt_empty")
        if ps == "gt_empty" and cs == "gt_empty":
            continue
        if ps == cs and pf.get(label, {}).get("ext") == cf.get(label, {}).get("ext"):
            continue
        gt = cf.get(label, {}).get("gt") or pf.get(label, {}).get("gt") or ""
        prev_ext = pf.get(label, {}).get("ext") or ""
        curr_ext = cf.get(label, {}).get("ext") or ""
        if ps in _bad and cs == "match":
            kind = "ok"
        elif ps == "match" and cs in _bad:
            kind = "bad"
        elif ps != cs or prev_ext != curr_ext:
            kind = "chg"
        else:
            continue
        changes.append({
            "loc": f"필드 - {_ko_field(label)}",
            "gt": gt, "prev_ext": prev_ext, "curr_ext": curr_ext,
            "prev_status": ps, "curr_status": cs, "kind": kind,
        })

    # 표 셀 (행 정렬 후 비교)
    pr_map = {row["rowIndex"]: row["cells"] for row in prev_d["table"]["rows"]}
    cr_map = {row["rowIndex"]: row["cells"] for row in curr_d["table"]["rows"]}
    for idx in sorted(set(list(pr_map.keys()) + list(cr_map.keys()))):
        pr = pr_map.get(idx, {})
        cr = cr_map.get(idx, {})
        for ck in sorted(set(list(pr.keys()) + list(cr.keys()))):
            ps = pr.get(ck, {}).get("status", "gt_empty")
            cs = cr.get(ck, {}).get("status", "gt_empty")
            if ps == "gt_empty" and cs == "gt_empty":
                continue
            prev_ext = (pr.get(ck) or {}).get("ext") or ""
            curr_ext = (cr.get(ck) or {}).get("ext") or ""
            if ps == cs and prev_ext == curr_ext:
                continue
            gt = ((cr.get(ck) or {}) or (pr.get(ck) or {})).get("gt") or ""
            if ps in _bad and cs == "match":
                kind = "ok"
            elif ps == "match" and cs in _bad:
                kind = "bad"
            elif ps != cs or prev_ext != curr_ext:
                kind = "chg"
            else:
                continue
            changes.append({
                "loc": f"행{idx} - {_ko_field(ck)}",
                "gt": gt, "prev_ext": prev_ext, "curr_ext": curr_ext,
                "prev_status": ps, "curr_status": cs, "kind": kind,
            })
    return changes


def render_compare_html(run_dir: str) -> str | None:
    """compare.html 생성. 직전 run 없으면 None 반환."""
    import datetime as _dt
    from trend import _CSS, _esc

    curr_m, curr_cs = _load_run(run_dir)
    testset = curr_m.get("testset", "")
    prev_dir = _find_prev_run_dir(run_dir, testset)
    if not prev_dir:
        return None

    prev_m, prev_cs = _load_run(prev_dir)
    gen = _dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    role = "학습데이터" if "thin" in testset else "회귀 기준값"
    prev_ts = _fmt_ts(prev_m.get("runTs", ""))
    curr_ts = _fmt_ts(curr_m.get("runTs", ""))

    prev_by_file = {d["sourceFile"]: d for d in prev_cs}
    curr_by_file = {d["sourceFile"]: d for d in curr_cs}
    all_files = sorted(set(list(prev_by_file.keys()) + list(curr_by_file.keys())))

    prev_cols = _cell_col_stats(prev_cs)
    curr_cols = _cell_col_stats(curr_cs)
    all_col_keys = sorted(set(list(prev_cols.keys()) + list(curr_cols.keys())))

    H: list[str] = []
    H.append("<!doctype html><html lang='ko'><head><meta charset='utf-8'>")
    H.append("<meta name='viewport' content='width=device-width,initial-scale=1'>")
    H.append(f"<title>비교 리포트 - {_esc(role)}</title>")
    H.append(f"<style>{_CSS}{_EXTRA_CSS}</style></head><body>")

    # 헤더
    H.append(f"<div class='head'><h1>비교 리포트 - {_esc(role)}</h1>"
             f"<div class='gen'>생성 {gen}</div></div>")
    H.append("<div class='note'>"
             f"<div class='row'><b>직전</b> {_esc(prev_ts)}"
             f" &nbsp;→&nbsp; <b>이번</b> {_esc(curr_ts)}</div>"
             "<div class='row'><b>초록 = 좋아짐 · 빨강 = 나빠짐/변화</b></div>"
             "<div class='row'>"
             "<span class='tag-ok'>✅ 개선</span> 이전에 틀렸으나 이번에 맞음(초록) &nbsp; "
             "<span class='tag-bad'>❌ 악화</span> 이전에 맞았으나 이번에 틀림(빨강) &nbsp; "
             "<span class='tag-chg'>🔄 변화</span> 상태·값이 달라짐(빨강)"
             "</div></div>")

    # ── 1. 전체 요약 ──────────────────────────────────────────────────────────
    pof = prev_m["overall"]["field"]
    poc = prev_m["overall"]["cell"]
    cof = curr_m["overall"]["field"]
    coc = curr_m["overall"]["cell"]
    H.append("<section><h2>전체 요약</h2>")
    H.append("<table><thead><tr><th>항목</th><th>직전</th><th>이번</th><th>변화</th></tr></thead><tbody>")
    H.append(f"<tr><td>필드 정확도</td>{_acc_td(pof['accuracy'])}{_acc_td(cof['accuracy'])}"
             f"<td>{_delta_html(cof['accuracy'], pof['accuracy'])}</td></tr>")
    H.append(f"<tr><td>셀 정확도</td>{_acc_td(poc['accuracy'])}{_acc_td(coc['accuracy'])}"
             f"<td>{_delta_html(coc['accuracy'], poc['accuracy'])}</td></tr>")
    H.append("</tbody></table></section>")

    # ── 2. 이미지별 1:1 비교 ──────────────────────────────────────────────────
    H.append(f"<section><h2>이미지별 1:1 비교"
             f" <span class='muted'>({len(all_files)}장 · 컬럼 클릭=정렬)</span></h2>")
    H.append("<table class='sortable'><thead><tr>"
             "<th>이미지</th>"
             "<th data-num='1'>직전 필드</th><th data-num='1'>이번 필드</th><th>필드 변화</th>"
             "<th data-num='1'>직전 셀</th><th data-num='1'>이번 셀</th><th>셀 변화</th>"
             "</tr></thead><tbody>")
    for f in all_files:
        pd = prev_by_file.get(f)
        cd = curr_by_file.get(f)
        p_fa = pd["fields"]["fieldAccuracy"] if pd else None
        c_fa = cd["fields"]["fieldAccuracy"] if cd else None
        p_ca = pd["table"]["cellAccuracy"] if pd else None
        c_ca = cd["table"]["cellAccuracy"] if cd else None
        H.append(f"<tr><td>{_esc(f)}</td>"
                 f"{_acc_td(p_fa)}{_acc_td(c_fa)}<td>{_delta_html(c_fa, p_fa)}</td>"
                 f"{_acc_td(p_ca)}{_acc_td(c_ca)}<td>{_delta_html(c_ca, p_ca)}</td></tr>")
    H.append("</tbody></table></section>")

    # ── 3. 필드(스칼라)별 비교 ────────────────────────────────────────────────
    pf_all = prev_m.get("perField", {})
    cf_all = curr_m.get("perField", {})
    all_field_keys = sorted(set(list(pf_all.keys()) + list(cf_all.keys())))
    H.append("<section><h2>필드별 비교"
             " <span class='muted'>(스칼라 상단값 · 컬럼 클릭=정렬)</span></h2>")
    H.append("<table class='sortable'><thead><tr>"
             "<th>필드명</th>"
             "<th data-num='1'>직전 정확도</th><th data-num='1'>이번 정확도</th><th>변화</th>"
             "<th data-num='1'>직전 일치</th><th data-num='1'>이번 일치</th>"
             "</tr></thead><tbody>")
    for label in all_field_keys:
        pv = pf_all.get(label, {})
        cv = cf_all.get(label, {})
        pa, ca = pv.get("accuracy"), cv.get("accuracy")
        H.append(f"<tr>{_name_td(label)}"
                 f"{_acc_td(pa)}{_acc_td(ca)}<td>{_delta_html(ca, pa)}</td>"
                 f"{_num_td(pv.get('match', '-'))}{_num_td(cv.get('match', '-'))}</tr>")
    H.append("</tbody></table></section>")

    # ── 4. 셀 컬럼별 비교 ────────────────────────────────────────────────────
    H.append("<section><h2>셀 컬럼별 비교"
             " <span class='muted'>(표 내부 각 열 · 컬럼 클릭=정렬)</span></h2>")
    H.append("<table class='sortable'><thead><tr>"
             "<th>컬럼</th>"
             "<th data-num='1'>직전 정확도</th><th data-num='1'>이번 정확도</th><th>변화</th>"
             "<th data-num='1'>직전 일치</th><th data-num='1'>이번 일치</th>"
             "</tr></thead><tbody>")
    for ck in all_col_keys:
        pv = prev_cols.get(ck, {})
        cv = curr_cols.get(ck, {})
        pa, ca = pv.get("accuracy"), cv.get("accuracy")
        H.append(f"<tr>{_name_td(ck)}"
                 f"{_acc_td(pa)}{_acc_td(ca)}<td>{_delta_html(ca, pa)}</td>"
                 f"{_num_td(pv.get('match', '-'))}{_num_td(cv.get('match', '-'))}</tr>")
    H.append("</tbody></table></section>")

    # ── 5. 상세 변화 ──────────────────────────────────────────────────────────
    H.append("<section><h2>상세 변화 <span class='muted'>(이미지별 · 바뀐 항목만 · 제목 클릭=펼치기)</span></h2>")
    _TAG = {"ok": "<span class='tag-ok'>✅ 개선</span>",
            "bad": "<span class='tag-bad'>❌ 악화</span>",
            "chg": "<span class='tag-chg'>🔄 변화</span>"}

    def _ext_cell(val: str) -> str:
        if not val:
            return "<td><span class='muted'>(없음)</span></td>"
        return f"<td>{_esc(val[:60])}</td>"

    has_any = False
    for f in all_files:
        pd = prev_by_file.get(f)
        cd = curr_by_file.get(f)
        if not pd or not cd:
            continue
        changes = _changes_for_image(pd, cd)
        if not changes:
            continue
        has_any = True
        n_ok  = sum(1 for c in changes if c["kind"] == "ok")
        n_bad = sum(1 for c in changes if c["kind"] == "bad")
        n_chg = sum(1 for c in changes if c["kind"] == "chg")
        badges = []
        if n_bad:
            badges.append(f"<span class='tag-bad'>❌ 악화 {n_bad}</span>")
        if n_ok:
            badges.append(f"<span class='tag-ok'>✅ 개선 {n_ok}</span>")
        if n_chg:
            badges.append(f"<span class='tag-chg'>🔄 변화 {n_chg}</span>")
        badge_html = " &nbsp;".join(badges)
        # 제목: 기본 접힘(▶), 클릭 시 펼침(▼)
        H.append(f"<h3 class='tog' onclick='tog(this)'>"
                 f"<span class='arr'>▶</span>{_esc(f)} &nbsp; {badge_html}</h3>")
        # 내용: 기본 숨김
        H.append("<div class='tog-body' style='display:none'>")
        H.append("<table><thead><tr>"
                 "<th>위치</th><th>상태</th><th>GT(정답)</th>"
                 "<th>직전 추출값</th><th>이번 추출값</th>"
                 "</tr></thead><tbody>")
        for ch in sorted(changes, key=lambda x: (x["kind"] != "bad", x["kind"] != "ok", x["loc"])):
            H.append(f"<tr><td>{_esc(ch['loc'])}</td><td>{_TAG[ch['kind']]}</td>"
                     f"<td>{_esc((ch['gt'] or '')[:60])}</td>"
                     f"{_ext_cell(ch['prev_ext'])}{_ext_cell(ch['curr_ext'])}</tr>")
        H.append("</tbody></table></div>")

    if not has_any:
        H.append("<p class='muted'>변화된 항목 없음 (모든 상태/값 동일)</p>")
    H.append("</section>")

    H.append(_SORT_JS)
    H.append("</body></html>")

    out = os.path.join(run_dir, "compare.html")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(H))
    return out


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--ts", default=None)
    ap.add_argument("--testset", default=C.DEFAULT_TESTSET)
    args = ap.parse_args()
    if args.ts:
        run_dir = os.path.join(C.RUNS_DIR, args.ts)
    else:
        dirs = sorted(
            (p for p in glob.glob(os.path.join(C.RUNS_DIR, "*")) if os.path.isdir(p)),
            key=os.path.getmtime,
        )
        run_dir = dirs[-1] if dirs else ""
    out = render_compare_html(run_dir)
    print(f"wrote {out}" if out else "직전 run 없음 - compare.html 생성 생략")
