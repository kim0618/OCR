"""trend - run-over-run regression view from metrics_timeseries.sqlite.

This is the answer to "where do I see whether my rule change helped?": after each
`run_all`, the timeseries gets one row; this prints the history for a testset with
the delta vs the previous run and flags any regression (▼) or gain (▲).

    python eval/trend.py                       # default testset (invoice_study)
    python eval/trend.py --testset invoice_thin
    python eval/trend.py --last 10

run_all also prints the latest one-line delta automatically at the end.
"""

from __future__ import annotations

import argparse
import sqlite3
from typing import Any

import contract as C
from metrics import TIMESERIES_DB

_COLS = ("runTs", "sampleCount", "fieldScored", "fieldMatch", "fieldAcc",
         "cellScored", "cellMatch", "cellAcc",
         "bRecognition", "bStructure", "bLayout", "bPreprocessing")


def _run_ts_key(run_ts: str) -> str:
    """runTs에 박힌 YYYYMMDD_HHMMSS를 정렬키로. 없으면 빈 문자열(가장 앞=오래된 것)."""
    import re as _re
    m = _re.search(r"(\d{8})_(\d{6})", run_ts or "")
    return m.group(1) + m.group(2) if m else ""


def _rows(testset: str) -> list[dict[str, Any]]:
    con = sqlite3.connect(TIMESERIES_DB)
    try:
        # rowid = 기록 순서. 단, metrics 재계산 시 rowid가 바뀌어 순서가 뒤집힐 수 있으므로
        # runTs에 박힌 실제 타임스탬프로 안정 정렬(동률·무타임스탬프는 rowid 순 유지).
        cur = con.execute(
            f"SELECT {','.join(_COLS)} FROM runs WHERE testset=? ORDER BY rowid", (testset,)
        )
        rows = [dict(zip(_COLS, r)) for r in cur.fetchall()]
        rows.sort(key=lambda r: _run_ts_key(r["runTs"]))  # 안정정렬: 같은 키면 rowid 순
        return rows
    finally:
        con.close()


def _pct(a) -> str:
    return "  n/a" if a is None else f"{a * 100:5.1f}%"


def _fmt_date(run_ts: str) -> str:
    """runTs(예 '20260610_105111/study')의 YYYYMMDD_HHMMSS를 '2026-06-10 10:51'로.
    날짜 형식이 아니면(예 canned 고정 id) 원본 그대로."""
    import datetime as _dt
    import re as _re
    m = _re.search(r"(\d{8})_(\d{6})", run_ts)  # NNN_ 프리픽스 있어도 날짜 추출
    if m:
        try:
            return _dt.datetime.strptime(m.group(1) + m.group(2), "%Y%m%d%H%M%S").strftime("%Y-%m-%d %H:%M")
        except ValueError:
            pass
    return run_ts


def _run_no(run_ts: str, fallback: int) -> str:
    """runTs 'NNN_YYYYMMDD_HHMMSS'의 NNN(run 폴더번호)을 회차로. 프리픽스 없으면 #순번 fallback."""
    import re as _re
    m = _re.match(r"(\d{1,4})_\d{8}_\d{6}", run_ts or "")
    return m.group(1) if m else f"#{fallback}"


def _delta_pp(cur, prev) -> str:
    """Delta in percentage points with ▲/▼/= marker."""
    if cur is None or prev is None:
        return "    ·"
    d = (cur - prev) * 100
    if abs(d) < 0.05:
        return "   ="
    return f"{'▲' if d > 0 else '▼'}{abs(d):4.1f}"


def _changed_population(cur, prev) -> bool:
    """직전 run과 표본 수(sampleCount)가 다르면 True.

    표본이 바뀌면(예: 6장 base-only → 24장 base+변주) 직전 대비 pp/버킷 델타는
    품질 변화가 아니라 모집단 변화이므로 비교가 무의미 → 표시에서 보류한다.
    """
    return bool(prev and cur.get("sampleCount") != prev.get("sampleCount"))


_BUCKET_KO = {"bRecognition": "인식", "bStructure": "구조", "bLayout": "컬럼", "bPreprocessing": "전처리"}


def latest_delta_line(testset: str) -> str | None:
    """직전 run 대비 최신 run 1줄 요약 (run_all 끝 + TREND.md)."""
    rows = _rows(testset)
    if not rows:
        return None
    cur = rows[-1]
    if len(rows) == 1:
        return (f"[{testset}] 첫 run {_fmt_date(cur['runTs'])}: 필드 {_pct(cur['fieldAcc'])} "
                f"셀 {_pct(cur['cellAcc'])} (비교할 직전 run 없음)")
    prev = rows[-2]
    # 표본이 바뀌면 직전 대비 비교 자체가 무의미 → 보류(가짜 회귀 신호 방지).
    # (문구 안에는 '→' 를 쓰지 않는다: verdict 추출이 마지막 '→' 기준이므로.)
    if _changed_population(cur, prev):
        return (f"[{testset}] {_fmt_date(prev['runTs'])} → {_fmt_date(cur['runTs'])}: "
                f"필드 {_pct(cur['fieldAcc'])}  셀 {_pct(cur['cellAcc'])}  →  "
                f"표본 변경 ({prev['sampleCount']}건에서 {cur['sampleCount']}건), 직전 대비 비교 보류")
    # #10 가드: 정확도가 *정확히 0.0* 이어도 비교 가능해야 함(`and` 는 0.0 을 falsy 로
    # 떨어뜨려 delta=0 → 0%↔X 회귀를 놓침). None(채점 불가)일 때만 비교 보류.
    fd = ((cur["fieldAcc"] - prev["fieldAcc"]) * 100
          if cur["fieldAcc"] is not None and prev["fieldAcc"] is not None else None)
    cd = ((cur["cellAcc"] - prev["cellAcc"]) * 100
          if cur["cellAcc"] is not None and prev["cellAcc"] is not None else None)
    # 회귀(🔴) 판정은 *정확도*만으로 한다. 버킷 결함 수는 코드/계측 변경에 민감해
    # (정확도가 올라도 늘 수 있음) 회귀 신호로 쓰지 않고 '참고'로만 표기한다.
    flags = []
    if fd is not None and fd < -0.05:
        flags.append(f"필드 회귀 {fd:.1f}pp")
    if cd is not None and cd < -0.05:
        flags.append(f"셀 회귀 {cd:.1f}pp")
    verdict = "  ".join(flags) if flags else "회귀 없음"
    bucket_notes = [f"{_BUCKET_KO[b]}{'+' if cur[b] > prev[b] else ''}{cur[b] - prev[b]}"
                    for b in ("bRecognition", "bStructure", "bLayout", "bPreprocessing")
                    if cur[b] != prev[b]]
    note = f"  (참고 버킷변화: {', '.join(bucket_notes)})" if bucket_notes else ""
    return (f"[{testset}] {_fmt_date(prev['runTs'])} → {_fmt_date(cur['runTs'])}: "
            f"필드 {_pct(cur['fieldAcc'])} ({_delta_pp(cur['fieldAcc'], prev['fieldAcc'])}pp)  "
            f"셀 {_pct(cur['cellAcc'])} ({_delta_pp(cur['cellAcc'], prev['cellAcc'])}pp)  →  {verdict}{note}")


def _testsets_in_db() -> list[str]:
    con = sqlite3.connect(TIMESERIES_DB)
    try:
        return [r[0] for r in con.execute("SELECT DISTINCT testset FROM runs ORDER BY testset")]
    except sqlite3.OperationalError:
        return []
    finally:
        con.close()


def _bucket_cell(cur, prev, key) -> str:
    """N · ▲ 결함 늘어남(나쁨) · ▼ 결함 줄어듦(좋음)."""
    n = cur[key]
    if not prev or n == prev[key]:
        return str(n)
    return f"{n}▲" if n > prev[key] else f"{n}▼"


TREND_MD = "TREND.md"  # rolling file under eval/, refreshed every run_all


def render_md(path: str | None = None) -> str:
    """Write eval/TREND.md - the whole run-over-run history (all testsets) in one
    file, like report.md but cumulative. Refreshed each run_all."""
    import datetime as _dt
    out = path or __import__("os").path.join(C.HERE, TREND_MD)
    gen = _dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    L: list[str] = []
    L.append("# 평가 추세 - run별 누적 이력")
    L.append("")
    L.append(f"_갱신 {gen}_")
    L.append("")
    L.append("> `run_all` 돌릴 때마다 자동 갱신. 한 행 = 측정 1회. **변화** = 같은 testset의"
             " 직전 run 대비 변화(퍼센트포인트). ▲좋아짐 · ▼나빠짐 · `N*` = 그 버킷 결함이"
             " 직전보다 늘어남. 버킷은 룰 보강 방향을 가리킴"
             "(인식=OCR글자, 구조=필드/행배치, 컬럼=표 열밀림, 전처리=회전/기울기).")
    L.append("")
    L.append("> ⚠️ 소표본 숫자는 **가설이지 릴리스 합격선이 아님**(계획 §8).")
    L.append("")

    testsets = _testsets_in_db()
    if not testsets:
        L.append("_아직 기록된 run 없음 - 먼저 `python eval/run_all.py` 실행._")
    for ts in testsets:
        rows = _rows(ts)
        L.append(f"## {ts}  (run {len(rows)}회)")
        L.append("")
        L.append("| 회차 | 날짜 | 건수 | 필드 정확도 | 필드 변화 | 셀 정확도 | 셀 변화 | 인식오류 | 구조오류 | 컬럼밀림 | 전처리 |")
        L.append("|--:|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|")
        for i, r in enumerate(rows):
            prev = rows[i - 1] if i > 0 else None
            changed = _changed_population(r, prev)
            # 표본 변경 행은 pp/버킷 델타 보류(↕). 같은 모집단일 때만 직전 대비 표시.
            bprev = None if changed else prev
            if not prev:
                fdp = cdp = "·"
            elif changed:
                fdp = cdp = "↕표본"
            else:
                fdp = _delta_pp(r["fieldAcc"], prev["fieldAcc"]).strip()
                cdp = _delta_pp(r["cellAcc"], prev["cellAcc"]).strip()
            L.append(
                f"| {_run_no(r['runTs'], i + 1)} | {_fmt_date(r['runTs'])} | {r['sampleCount']} | {_pct(r['fieldAcc']).strip()} | {fdp} "
                f"| {_pct(r['cellAcc']).strip()} | {cdp} "
                f"| {_bucket_cell(r, bprev, 'bRecognition')} | {_bucket_cell(r, bprev, 'bStructure')} "
                f"| {_bucket_cell(r, bprev, 'bLayout')} | {_bucket_cell(r, bprev, 'bPreprocessing')} |"
            )
        L.append("")
        line = latest_delta_line(ts)
        if line:
            verdict = line.split("→")[-1].strip()
            if "첫 run" in line or "표본 변경" in line:
                mark = "🟡"
            elif verdict.startswith("회귀 없음"):
                mark = "🟢"
            else:
                mark = "🔴"
            L.append(f"**최신:** {mark} {line}")
        L.append("")

    text = "\n".join(L) + "\n"
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(text)
    return out


TREND_HTML = "TREND.html"

_CSS = """
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
.gen{color:var(--muted);font-size:12.5px;white-space:nowrap}
.note{color:var(--muted);font-size:12.5px;max-width:1600px;margin:4px auto}
.note.warn{color:var(--warn)}
section{background:var(--card);border:1px solid var(--line);border-radius:10px;
padding:16px 18px;margin:18px auto;max-width:1600px;overflow-x:auto;box-shadow:0 1px 2px rgba(27,31,36,.04)}
h2{font-size:16px;margin:0 0 10px}
h3{font-size:13.5px;margin:14px 0 6px}
table{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums}
th,td{padding:7px 10px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}
th:first-child,td:first-child{text-align:left}
th{color:var(--muted);font-weight:600;font-size:12.5px;border-bottom:2px solid var(--line)}
tr:last-child td{border-bottom:none}
tbody tr:hover{background:#f6f8fa}
code{background:#eff1f3;border:1px solid var(--line);border-radius:5px;padding:1px 6px;font-size:12.5px}
.up{color:var(--up);font-weight:600}
.down{color:var(--down);font-weight:600}
.muted{color:var(--muted)}
.bup{color:var(--down);font-weight:700}
.latest{margin-top:12px;padding:9px 12px;border-radius:8px;border:1px solid var(--line);font-size:13px}
.latest.ok{background:#e9f7ec;border-color:#a7e0b5}
.latest.warn{background:#fff8e6;border-color:#f0d99a}
.latest.bad{background:#ffeef0;border-color:#f5b0b8}
.legend{color:var(--muted);font-size:12px;margin-top:6px}
.note .row{margin:3px 0}
.btn{display:inline-block;padding:5px 12px;border-radius:6px;background:var(--link);
color:#fff;font-weight:600;font-size:12.5px;text-decoration:none;border:1px solid var(--link)}
.btn:hover{background:#0860ca;text-decoration:none}
/* SUMMARY 표: 텍스트=왼쪽, 숫자=오른쪽(기본), 검증/상세=가운데 */
table.sumtable td:nth-child(2),table.sumtable th:nth-child(2){text-align:left}
table.sumtable td:nth-child(6),table.sumtable th:nth-child(6),
table.sumtable td:nth-child(7),table.sumtable th:nth-child(7){text-align:center}
@media (max-width:640px){body{font-size:13px}h1{font-size:18px}th,td{padding:6px 8px}
.head{flex-direction:column;gap:2px}section{padding:14px}}
"""


def _esc(s) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def _delta_html(cur, prev) -> str:
    if cur is None or prev is None:
        return '<span class="muted">·</span>'
    d = (cur - prev) * 100
    if abs(d) < 0.05:
        return '<span class="muted">=</span>'
    cls, arrow = ("up", "▲") if d > 0 else ("down", "▼")
    return f'<span class="{cls}">{arrow}&nbsp;{abs(d):.1f}</span>'


def _bucket_html(cur, prev, key) -> str:
    """버킷=결함 수. 색은 정확도와 동일 의미: 초록=좋음, 빨강=나쁨.
    결함 줄어듦(좋음)=초록 ▼ · 늘어남(나쁨)=빨강 ▲."""
    n = cur[key]
    if not prev or n == prev[key]:
        return str(n)
    if n > prev[key]:
        return f'<span class="down">{n}&nbsp;▲</span>'   # 결함 늘어남 = 나빠짐(빨강)
    return f'<span class="up">{n}&nbsp;▼</span>'          # 결함 줄어듦 = 좋아짐(초록)


def _role_badge_html(ts: str) -> str:
    """testset 종류 배지: 회귀 기준점 / 학습데이터 (실데이터 대기)."""
    try:
        prof = C.get_testset(ts)
        if prof["kind"] == "rich":
            return "<span class='muted'>회귀 기준점</span>"
        suffix = " <span class='muted'>(실데이터 대기)</span>" if prof["runMode"] == "canned" else ""
        return f"<span class='muted'>학습데이터{suffix}</span>"
    except Exception:
        return ""


def trend_sections_html(testsets: list[str] | None = None) -> str:
    """추세 <section> 블록만 반환 - TREND.html 본문 + SUMMARY.html 임베드 공용."""
    testsets = testsets if testsets is not None else _testsets_in_db()
    if not testsets:
        return ("<section><p class='muted'>아직 기록된 run 없음 - 먼저 "
                "<code>python eval/run_all.py</code> 실행.</p></section>")
    H: list[str] = []
    # 범례 — 제목 바로 밑 한 번만 (상단 종합보고서 범례 박스와 같은 위치/스타일), 항목별 줄바꿈
    H.append("<div class='note'>"
             "<div class='row'><span class='up'>초록 = 좋아짐</span> · "
             "<span class='down'>빨강 = 나빠짐</span> (정확도·버킷 공통)</div>"
             "<div class='row'><b>필드/셀 변화</b> = 직전 대비 정확도 "
             "<span class='up'>▲ 올라감(좋음)</span> · <span class='down'>▼ 내려감(나쁨)</span></div>"
             "<div class='row'><b>버킷(결함 수) 변화</b> = "
             "<span class='up'>▼ 줄어듦(좋음)</span> · <span class='down'>▲ 늘어남(나쁨)</span></div>"
             "<div class='row'><b>인식오류</b> = OCR 글자 틀림</div>"
             "<div class='row'><b>구조오류</b> = 값이 엉뚱한 필드/행</div>"
             "<div class='row'><b>컬럼밀림</b> = 표 안 열 어긋남</div>"
             "<div class='row'><b>전처리</b> = 회전/기울기</div>"
             "</div>")
    for ts in testsets:
        rows = _rows(ts)
        H.append("<section>")
        badge = _role_badge_html(ts)
        badge_html = f" · {badge}" if badge else ""
        H.append(f"<h2>{_esc(ts)}{badge_html} <span class='muted'>(run {len(rows)}회)</span></h2>")
        H.append("<table><thead><tr>"
                 "<th>회차</th><th>날짜</th><th>건수</th><th>필드 정확도</th><th>필드 변화</th>"
                 "<th>셀 정확도</th><th>셀 변화</th>"
                 "<th>인식오류</th><th>구조오류</th><th>컬럼밀림</th><th>전처리</th></tr></thead><tbody>")
        for i, r in enumerate(rows):
            prev = rows[i - 1] if i > 0 else None
            changed = _changed_population(r, prev)
            bprev = None if changed else prev
            mut = "<span class=muted>·</span>"
            chg = "<span class=muted>↕표본</span>"
            if not prev:
                fdh = cdh = mut
            elif changed:
                fdh = cdh = chg
            else:
                fdh = _delta_html(r["fieldAcc"], prev["fieldAcc"])
                cdh = _delta_html(r["cellAcc"], prev["cellAcc"])
            H.append(
                f"<tr><td>{_esc(_run_no(r['runTs'], i + 1))}</td><td title='{_esc(r['runTs'])}'>{_esc(_fmt_date(r['runTs']))}</td>"
                f"<td>{r['sampleCount']}</td>"
                f"<td>{_pct(r['fieldAcc']).strip()}</td><td>{fdh}</td>"
                f"<td>{_pct(r['cellAcc']).strip()}</td><td>{cdh}</td>"
                f"<td>{_bucket_html(r, bprev, 'bRecognition')}</td><td>{_bucket_html(r, bprev, 'bStructure')}</td>"
                f"<td>{_bucket_html(r, bprev, 'bLayout')}</td><td>{_bucket_html(r, bprev, 'bPreprocessing')}</td></tr>"
            )
        H.append("</tbody></table>")
        line = latest_delta_line(ts)
        if line:
            verdict = line.split("→")[-1].strip()
            if "첫 run" in line or "표본 변경" in line:
                cls, badge = "warn", "🟡"
            elif verdict.startswith("회귀 없음"):
                cls, badge = "ok", "🟢"
            else:
                cls, badge = "bad", "🔴"
            H.append(f"<div class='latest {cls}'><b>최신:</b> {badge} {_esc(line)}</div>")
        H.append("</section>")
    return "\n".join(H)


def render_html(path: str | None = None) -> str:
    """eval/TREND.html - 브라우저로 바로 보는 스타일된 추세 리포트 (외부 의존성 0)."""
    import datetime as _dt
    import os as _os
    out = path or _os.path.join(C.HERE, TREND_HTML)
    gen = _dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    H: list[str] = []
    H.append("<!doctype html><html lang='ko'><head><meta charset='utf-8'>")
    H.append("<meta name='viewport' content='width=device-width,initial-scale=1'>")
    H.append("<title>평가 추세 - TREND</title>")
    H.append(f"<style>{_CSS}</style></head><body>")
    H.append(f"<div class='head'><h1>평가 추세 - run별 누적 이력</h1>"
             f"<div class='gen'>갱신 {gen}</div></div>")
    H.append("<p class='note'><code>run_all</code> 돌릴 때마다 자동 갱신. 한 행 = 측정 1회. "
             "<b>변화</b> = 같은 testset의 직전 run 대비 변화(퍼센트포인트, ▲좋아짐/▼나빠짐). "
             "버킷은 룰 보강 방향(인식=OCR글자, 구조=필드/행배치, 컬럼=표 열밀림, 전처리=회전/기울기).</p>")
    H.append("<p class='note warn'>⚠️ 소표본 숫자는 가설이지 릴리스 합격선이 아님 (계획 §8).</p>")
    H.append(trend_sections_html())
    H.append("</body></html>")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(H))
    return out


def print_table(testset: str, last: int | None = None) -> None:
    rows = _rows(testset)
    if not rows:
        print(f"no timeseries rows for testset={testset}")
        return
    shown = rows[-last:] if last else rows
    print(f"# 추세 - testset={testset}  (run {len(rows)}회)\n")
    hdr = f"{'날짜':<18} {'필드':>7} {'Δpp':>6} {'셀':>7} {'Δpp':>6}  {'인식':>5} {'구조':>5} {'컬럼':>5} {'전처리':>5}"
    print(hdr)
    print("-" * len(hdr))
    for i, r in enumerate(shown):
        gi = rows.index(r)
        prev = rows[gi - 1] if gi > 0 else None
        changed = _changed_population(r, prev)
        if not prev:
            fdp = cdp = "    ·"
        elif changed:
            fdp = cdp = " ↕표본"
        else:
            fdp = _delta_pp(r["fieldAcc"], prev["fieldAcc"])
            cdp = _delta_pp(r["cellAcc"], prev["cellAcc"])
        # mark bucket increases (more defects) with * — 표본 변경 시엔 비교 보류
        def bmark(key):
            if prev and not changed and r[key] > prev[key]:
                return f"{r[key]}*"
            return str(r[key])
        print(f"{_fmt_date(r['runTs']):<18} {_pct(r['fieldAcc']):>7} {fdp:>6} {_pct(r['cellAcc']):>7} {cdp:>6}  "
              f"{bmark('bRecognition'):>5} {bmark('bStructure'):>5} {bmark('bLayout'):>5} {bmark('bPreprocessing'):>5}")
    print()
    line = latest_delta_line(testset)
    if line:
        print(line)
    print("\n(▲ 좋아짐 · ▼ 나빠짐 · * = 직전보다 결함 늘어남)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--testset", default=C.DEFAULT_TESTSET)
    ap.add_argument("--last", type=int, default=None)
    ap.add_argument("--md", action="store_true", help="(re)write eval/TREND.md and exit")
    ap.add_argument("--html", action="store_true", help="(re)write eval/TREND.html and exit")
    args = ap.parse_args()
    if args.md:
        print(f"wrote {render_md()}")
    elif args.html:
        print(f"wrote {render_html()}")
    else:
        print_table(args.testset, args.last)
