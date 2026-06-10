"""changes - 전역 룰 수정 장부 (rule-fix ledger).

룰 1개 고칠 때마다 한 줄씩 쌓이는 전역 관리 파일. 배치별로 흩어지지 않고
runs/ 맨 위에 전체 히스토리가 누적된다 (개별 배치 폴더는 그 아래).

  원본:  eval/runs/rule_changes.jsonl   (전역, append-only)
  렌더:  eval/runs/CHANGES.html         (브라우저 장부, 외부 의존성 0)

한 항목에 들어가는 것 (자세히):
  ts       언제 고쳤나 (날짜+시각)
  before   어떤 run을 돌린 다음 고쳤나 (기준 run = study)
  target   무슨 결함을 노렸나 (필드/버킷)
  rule     고친 룰 한 줄 요약
  detail   뭘 어떻게 바꿨는지 상세 (동작 before→after)
  kind     일반 / 오버핏  (전략: 점수 아닌 룰 성격으로 판정)
  where    고친 위치 (파일:함수)
  after    고친 뒤 돌린 run (효과 측정 대상)
  verdict  유지 / 롤백 / 대기
  note     비고

효과(필드/셀 Δ, 버킷 변화, 회귀필드수)는 before/after run의 metrics.json에서
자동 계산 — 손으로 % 적지 않는다(오타 방지).

CLI:
  python eval/changes.py --add --id R001 --target "..." --rule "..." \
      --detail "..." --kind 일반 --where "invoice_statement.py:fn" \
      --before 20260610_152454/study
  python eval/changes.py --set-after R001 --after 20260610_161200/study
  python eval/changes.py --verdict R001 --set 유지
  python eval/changes.py --render
"""

from __future__ import annotations

import argparse
import json
import os
from typing import Any

import contract as C

LEDGER_JSONL = os.path.join(C.RUNS_DIR, "rule_changes.jsonl")
LEDGER_HTML = os.path.join(C.RUNS_DIR, "CHANGES.html")

_FIELDS = ("id", "ts", "before", "target", "rule", "detail",
           "kind", "where", "after", "verdict", "note")


# ─── 원본 입출력 ────────────────────────────────────────────────────────────
def _read() -> list[dict[str, Any]]:
    if not os.path.isfile(LEDGER_JSONL):
        return []
    out = []
    with open(LEDGER_JSONL, encoding="utf-8") as fh:
        for ln in fh:
            ln = ln.strip()
            if ln:
                out.append(json.loads(ln))
    return out


def _write(entries: list[dict[str, Any]]) -> None:
    with open(LEDGER_JSONL, "w", encoding="utf-8") as fh:
        for e in entries:
            fh.write(json.dumps(e, ensure_ascii=False) + "\n")


def _now() -> str:
    import datetime as _dt
    return _dt.datetime.now().strftime("%Y-%m-%d %H:%M")


def log_change(*, id: str, target: str, rule: str, detail: str = "",
               kind: str = "일반", where: str = "", before: str = "",
               after: str = "", verdict: str = "대기", note: str = "",
               ts: str | None = None) -> dict[str, Any]:
    """장부에 한 줄 append. ts 생략 시 현재 시각."""
    entries = _read()
    if any(e["id"] == id for e in entries):
        raise ValueError(f"이미 있는 id: {id}")
    e = {"id": id, "ts": ts or _now(), "before": before, "target": target,
         "rule": rule, "detail": detail, "kind": kind, "where": where,
         "after": after, "verdict": verdict, "note": note}
    entries.append(e)
    _write(entries)
    return e


def _update(id: str, **kw) -> dict[str, Any]:
    entries = _read()
    for e in entries:
        if e["id"] == id:
            e.update({k: v for k, v in kw.items() if v is not None})
            _write(entries)
            return e
    raise ValueError(f"없는 id: {id}")


# ─── 효과 자동 계산 (before/after run metrics.json) ──────────────────────────
def _load_metrics(run_ts: str) -> dict[str, Any] | None:
    if not run_ts:
        return None
    p = os.path.join(C.RUNS_DIR, run_ts, "metrics.json")
    if not os.path.isfile(p):
        return None
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception:
        return None


def _effect(before: str, after: str) -> dict[str, Any]:
    """before→after 효과: 필드/셀 Δ, 버킷 변화, 개선/악화 필드 수."""
    bm, am = _load_metrics(before), _load_metrics(after)
    eff: dict[str, Any] = {"ready": bool(bm and am)}
    if not (bm and am):
        return eff
    eff["fieldBefore"] = bm["overall"]["field"]["accuracy"]
    eff["fieldAfter"] = am["overall"]["field"]["accuracy"]
    eff["cellBefore"] = bm["overall"]["cell"]["accuracy"]
    eff["cellAfter"] = am["overall"]["cell"]["accuracy"]
    eff["buckets"] = {k: (bm["buckets"].get(k, 0), am["buckets"].get(k, 0))
                      for k in ("recognition", "structure", "layout", "preprocessing")}
    # 필드별 개선/악화 (안 건드린 필드가 깨졌는지 = 회귀 신호)
    bpf, apf = bm.get("perField", {}), am.get("perField", {})
    improved, regressed = [], []
    for k in set(list(bpf.keys()) + list(apf.keys())):
        ba = bpf.get(k, {}).get("accuracy")
        aa = apf.get(k, {}).get("accuracy")
        if ba is None or aa is None:
            continue
        if aa > ba + 0.001:
            improved.append(k)
        elif aa < ba - 0.001:
            regressed.append(k)
    eff["improved"] = sorted(improved)
    eff["regressed"] = sorted(regressed)
    return eff


# ─── HTML 렌더 ──────────────────────────────────────────────────────────────
_TOG_JS = """<script>
function tog(el){var b=el.nextElementSibling;var o=b.style.display!=='none';
 b.style.display=o?'none':'';el.querySelector('.arr').textContent=o?'▶':'▼';}
</script>"""

_EXTRA_CSS = """
.kind-gen{display:inline-block;padding:2px 8px;border-radius:4px;background:#e9f7ec;
  border:1px solid #a7e0b5;color:#1a7f37;font-size:12px;font-weight:600}
.kind-of{display:inline-block;padding:2px 8px;border-radius:4px;background:#fff8e6;
  border:1px solid #f0d99a;color:#9a6700;font-size:12px;font-weight:600}
.v-keep{color:#1a7f37;font-weight:600}.v-roll{color:#cf222e;font-weight:600}
.v-wait{color:#59636e}
h3.tog{cursor:pointer;user-select:none;display:flex;align-items:center;gap:10px;
  flex-wrap:wrap;font-size:14px;margin:16px 0 0}
h3.tog:hover{color:var(--link)}h3.tog .arr{font-size:11px;color:var(--muted);min-width:12px}
.tog-body{padding:6px 0 4px 22px}
.kv{margin:4px 0}.kv b{display:inline-block;min-width:84px;color:var(--muted);font-weight:600}
"""


def _pct(a) -> str:
    return "n/a" if a is None else f"{a * 100:.1f}%"


def _delta(after, before) -> str:
    if after is None or before is None:
        return "<span class='muted'>·</span>"
    d = (after - before) * 100
    if abs(d) < 0.05:
        return "<span class='muted'>=</span>"
    cls, arr = ("up", "▲") if d > 0 else ("down", "▼")
    return f"<span class='{cls}'>{arr} {abs(d):.1f}%</span>"


def render_html() -> str:
    from trend import _CSS, _esc
    import datetime as _dt
    entries = _read()
    gen = _dt.datetime.now().strftime("%Y-%m-%d %H:%M")

    H = ["<!doctype html><html lang='ko'><head><meta charset='utf-8'>",
         "<meta name='viewport' content='width=device-width,initial-scale=1'>",
         "<title>룰 수정 장부 — CHANGES</title>",
         f"<style>{_CSS}{_EXTRA_CSS}</style></head><body>",
         "<div class='head'><h1>룰 수정 장부</h1>"
         f"<div class='gen'>갱신 {gen} · 총 {len(entries)}건</div></div>",
         "<div class='note'>"
         "<div class='row'>룰 1개 고칠 때마다 한 줄. <b>분류</b> = "
         "<span class='kind-gen'>일반</span>(구조·패턴 의존, 수천장에 이월) / "
         "<span class='kind-of'>오버핏</span>(특정 값 외우기 — 피해야 함).</div>"
         "<div class='row'><b>효과</b>는 기준 run↔이후 run의 metrics에서 자동 계산. "
         "<b>회귀</b> = 안 건드린 필드가 깨졌는지 신호. 제목 클릭=상세 펼치기.</div>"
         "</div>"]

    if not entries:
        H.append("<section><p class='muted'>아직 기록된 룰 수정 없음. "
                 "첫 수정 때 <code>changes.log_change(...)</code> 로 추가됨.</p></section>")
    else:
        # 요약 표
        H.append("<section><h2>요약</h2><table><thead><tr>"
                 "<th>ID</th><th>시각</th><th>타겟</th><th>분류</th>"
                 "<th>필드 Δ</th><th>셀 Δ</th><th>회귀</th><th>판정</th>"
                 "</tr></thead><tbody>")
        for e in entries:
            eff = _effect(e.get("before", ""), e.get("after", ""))
            fd = _delta(eff.get("fieldAfter"), eff.get("fieldBefore")) if eff["ready"] else "<span class='muted'>대기</span>"
            cd = _delta(eff.get("cellAfter"), eff.get("cellBefore")) if eff["ready"] else "<span class='muted'>대기</span>"
            nreg = len(eff.get("regressed", [])) if eff["ready"] else None
            reg = ("<span class='muted'>·</span>" if nreg is None
                   else (f"<span class='down'>{nreg}필드</span>" if nreg else "<span class='up'>없음</span>"))
            kb = ("<span class='kind-gen'>일반</span>" if e.get("kind") == "일반"
                  else "<span class='kind-of'>오버핏</span>")
            vmap = {"유지": "v-keep", "롤백": "v-roll", "대기": "v-wait"}
            vc = vmap.get(e.get("verdict", "대기"), "v-wait")
            H.append(f"<tr><td>{_esc(e['id'])}</td><td>{_esc(e.get('ts',''))}</td>"
                     f"<td>{_esc(e.get('target',''))}</td><td>{kb}</td>"
                     f"<td>{fd}</td><td>{cd}</td><td>{reg}</td>"
                     f"<td class='{vc}'>{_esc(e.get('verdict','대기'))}</td></tr>")
        H.append("</tbody></table></section>")

        # 상세 (최신 먼저, 접힘)
        H.append("<section><h2>상세 이력 <span class='muted'>(최신 먼저 · 제목 클릭=펼치기)</span></h2>")
        for e in reversed(entries):
            eff = _effect(e.get("before", ""), e.get("after", ""))
            kb = ("<span class='kind-gen'>일반</span>" if e.get("kind") == "일반"
                  else "<span class='kind-of'>오버핏</span>")
            H.append(f"<h3 class='tog' onclick='tog(this)'><span class='arr'>▶</span>"
                     f"<b>{_esc(e['id'])}</b> {_esc(e.get('ts',''))} &nbsp;{kb}&nbsp; "
                     f"{_esc(e.get('target',''))}</h3>")
            H.append("<div class='tog-body' style='display:none'>")
            H.append(f"<div class='kv'><b>고친 룰</b> {_esc(e.get('rule',''))}</div>")
            H.append(f"<div class='kv'><b>수정 상세</b> {_esc(e.get('detail','') or '-')}</div>")
            H.append(f"<div class='kv'><b>위치</b> <code>{_esc(e.get('where','') or '-')}</code></div>")
            H.append(f"<div class='kv'><b>기준 run</b> <code>{_esc(e.get('before','') or '-')}</code>"
                     f" &nbsp;→&nbsp; <b>이후 run</b> <code>{_esc(e.get('after','') or '대기')}</code></div>")
            if eff["ready"]:
                H.append(f"<div class='kv'><b>필드</b> {_pct(eff['fieldBefore'])} → {_pct(eff['fieldAfter'])} "
                         f"{_delta(eff['fieldAfter'], eff['fieldBefore'])} &nbsp;·&nbsp; "
                         f"<b>셀</b> {_pct(eff['cellBefore'])} → {_pct(eff['cellAfter'])} "
                         f"{_delta(eff['cellAfter'], eff['cellBefore'])}</div>")
                bk = eff["buckets"]
                _BK = {"recognition": "인식", "structure": "구조",
                       "layout": "컬럼", "preprocessing": "전처리"}
                H.append("<div class='kv'><b>버킷</b> " + " · ".join(
                    f"{_BK.get(k, k)} {bk[k][0]}→{bk[k][1]}" for k in bk) + "</div>")
                imp = eff["improved"]; reg = eff["regressed"]
                H.append(f"<div class='kv'><b>개선필드</b> "
                         f"{_esc(', '.join(imp) or '없음')}</div>")
                rcls = "down" if reg else "up"
                H.append(f"<div class='kv'><b>회귀필드</b> "
                         f"<span class='{rcls}'>{_esc(', '.join(reg) or '없음')}</span></div>")
            else:
                H.append("<div class='kv'><b>효과</b> <span class='muted'>이후 run 측정 대기</span></div>")
            if e.get("note"):
                H.append(f"<div class='kv'><b>비고</b> {_esc(e['note'])}</div>")
            H.append("</div>")
        H.append("</section>")

    H.append(_TOG_JS)
    H.append("</body></html>")
    with open(LEDGER_HTML, "w", encoding="utf-8") as fh:
        fh.write("\n".join(H))
    return LEDGER_HTML


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--add", action="store_true")
    ap.add_argument("--id"); ap.add_argument("--target"); ap.add_argument("--rule")
    ap.add_argument("--detail", default=""); ap.add_argument("--kind", default="일반")
    ap.add_argument("--where", default=""); ap.add_argument("--before", default="")
    ap.add_argument("--after", default=""); ap.add_argument("--note", default="")
    ap.add_argument("--set-after"); ap.add_argument("--verdict"); ap.add_argument("--set")
    ap.add_argument("--render", action="store_true")
    a = ap.parse_args()
    if a.add:
        log_change(id=a.id, target=a.target, rule=a.rule, detail=a.detail,
                   kind=a.kind, where=a.where, before=a.before, after=a.after, note=a.note)
        print(f"added {a.id}")
    if a.set_after:
        _update(a.set_after, after=a.after)
        print(f"{a.set_after} after={a.after}")
    if a.verdict:
        _update(a.verdict, verdict=a.set)
        print(f"{a.verdict} verdict={a.set}")
    print(f"wrote {render_html()}")
