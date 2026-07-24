"""replay_summary — persistent, append-on-each-run KPI history for the replay loop.

Model: every time parser_drop_classify runs (--compare-dir replay_compare), it
calls append_history() here, which reads the CURRENT replay_compare sidecars,
appends a row to a persistent log (runs/<ts>/study/replay_history.json), and the
caller injects the full accumulated table into the classify HTML. No git, no
commit messages, no extra command — the history just grows each run.

One-time seed: if the log doesn't exist yet, it is backfilled from git so the
progression built so far isn't lost; thereafter it's pure append.

A row is appended only when the KPI numbers changed vs the last row (re-running
with no parser change doesn't add noise).

Standalone use (optional, also writes eval/REPLAY_SUMMARY.md):
    ../.venv/Scripts/python.exe eval/replay_summary.py --ts 053_20260617_142725/study
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))   # git root = OCR/
sys.path.insert(0, HERE)

import contract as C  # noqa: E402

# v3: thin content alignment makes itemName the primary row identity
# (0.70 name / 0.20 amount / 0.10 quantity).  v2 used amount-heavy alignment,
# so cell totals across the boundary are not directly comparable.
CURRENT_METRIC_VERSION = 3

OUT_MD = os.path.join(HERE, "REPLAY_SUMMARY.md")
HISTORY_NAME = "replay_history.json"
_MARK_A, _MARK_B = "<!--REPLAY_SUMMARY_START-->", "<!--REPLAY_SUMMARY_END-->"


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=REPO, capture_output=True, text=True, encoding="utf-8", errors="replace"
    ).stdout


def _kpi_from_blobs(get_file, rc_files: list[str], classify_path: str) -> dict | None:
    cm = cs = fm = fs = spur = 0
    paths = {"free": 0, "fallback": 0}
    any_row = False
    for fp in rc_files:
        raw = get_file(fp)
        if not raw:
            continue
        try:
            d = json.loads(raw)
        except Exception:
            continue
        any_row = True
        if d.get("extractionPath") in paths:
            paths[d["extractionPath"]] += 1
        table = d.get("table") or {}
        counts = table.get("cellCounts")
        if isinstance(counts, dict):
            # This is the canonical aggregate: it excludes measurement-only
            # columns and includes cells from structurally missing GT rows.
            cs += int(counts.get("scored") or 0)
            cm += int(counts.get("match") or 0)
            spur += int(counts.get("spurious") or 0)
        else:
            # Compatibility with old sidecars that predate cellCounts.
            for r in table.get("rows", []):
                for col, cell in r.get("cells", {}).items():
                    if col in C.MEASUREMENT_KEYS:
                        continue
                    if cell.get("spurious"):
                        spur += 1
                    if cell.get("gtNorm"):
                        cs += 1
                        cm += 1 if cell.get("status") == "match" else 0
        fields = d.get("fields") or {}
        field_counts = fields.get("counts")
        if isinstance(field_counts, dict):
            fs += int(field_counts.get("scored") or 0)
            fm += int(field_counts.get("match") or 0)
        else:
            pf = fields.get("perField") or {}
            for _fn, cell in pf.items():
                if isinstance(cell, dict) and cell.get("gtNorm"):
                    fs += 1
                    fm += 1 if cell.get("status") == "match" else 0
    if not any_row:
        return None
    pdrop = ambiguous = recog = None
    cj = get_file(classify_path)
    if cj:
        try:
            defs = json.loads(cj).get("defects", [])
            pdrop = sum(1 for x in defs if x.get("class") == "parser_drop")
            ambiguous = sum(1 for x in defs if x.get("class") == "ambiguous_fuzzy")
            recog = sum(1 for x in defs if x.get("class") == "recognition")
        except Exception:
            pass
    return {"cm": cm, "cs": cs, "fm": fm, "fs": fs, "spur": spur,
            "paths": paths, "pdrop": pdrop, "ambiguous": ambiguous, "recog": recog}


def _paths(ts: str) -> tuple[str, str, str]:
    ts = ts.replace("\\", "/")
    rel_dir = f"ocr-server/eval/runs/{ts}/replay_compare"
    classify = f"ocr-server/eval/runs/{ts}/PARSER_DROP_CLASSIFY_replay_compare.json"
    hist = os.path.join(REPO, f"ocr-server/eval/runs/{ts}/{HISTORY_NAME}")
    return rel_dir, classify, hist


def _current_kpi(ts: str) -> dict | None:
    rel_dir, classify, _ = _paths(ts)

    def _wt(fp: str) -> str:
        p = os.path.join(REPO, fp)
        return open(p, encoding="utf-8").read() if os.path.isfile(p) else ""

    wt_dir = os.path.join(REPO, rel_dir)
    files = ([f"{rel_dir}/{n}" for n in sorted(os.listdir(wt_dir)) if n.endswith(".json")]
             if os.path.isdir(wt_dir) else [])
    return _kpi_from_blobs(_wt, files, classify)


def _seed_from_git(ts: str) -> list[dict]:
    """One-time backfill: per past commit that touched the classify json, read its
    sidecars and emit {ts, ...kpi}. Used only when the log file doesn't exist."""
    rel_dir, classify, _ = _paths(ts)
    out = []
    commits = [c for c in _git("log", "--reverse", "--format=%H\t%cd",
                               "--date=format:%m-%d %H:%M", "--", classify).splitlines() if c.strip()]
    for line in commits:
        h, date = (line.split("\t", 1) + ["", ""])[:2]
        files = [f for f in _git("ls-tree", "-r", "--name-only", h, "--", rel_dir).splitlines()
                 if f.endswith(".json")]
        k = _kpi_from_blobs(lambda fp, _h=h: _git("show", f"{_h}:{fp}"), files, classify)
        if k:
            out.append({"ts": date, **k})
    return out


def _tuple(k: dict) -> tuple:
    p = k.get("paths") or {}
    return (k.get("cm"), k.get("cs"), k.get("fm"), k.get("fs"),
            k.get("pdrop"), k.get("ambiguous"), k.get("recog"), k.get("spur"),
            p.get("free"), p.get("fallback"))


def append_history(ts: str, now_str: str | None = None) -> list[dict]:
    """Append current KPIs to the persistent log (seeding from git once if empty),
    skipping the append when nothing changed vs the last row. Returns full list."""
    _, _, hist_path = _paths(ts)
    hist: list[dict] = []
    if os.path.isfile(hist_path):
        try:
            hist = json.load(open(hist_path, encoding="utf-8"))
        except Exception:
            hist = []
    if not hist:
        hist = _seed_from_git(ts)
    cur = _current_kpi(ts)
    if cur:
        for old in hist:
            if "metricVersion" not in old:
                old["metricVersion"] = 1
                old["metricsComparable"] = False
        last = hist[-1] if hist else None
        same_current_state = bool(
            last
            and last.get("metricsComparable") is False
            and all(last.get(k) == cur.get(k)
                    for k in ("pdrop", "ambiguous", "recog"))
            and (last.get("paths") or {}) == (cur.get("paths") or {})
        )
        if same_current_state:
            last.update(cur)
            last["metricVersion"] = CURRENT_METRIC_VERSION
            last["metricsComparable"] = True
        elif (
            last
            and _tuple(last) == _tuple(cur)
            and last.get("metricVersion") != CURRENT_METRIC_VERSION
        ):
            # The just-written replay row already uses the current scorer but
            # may have been appended by an older replay_summary process.
            last["metricVersion"] = CURRENT_METRIC_VERSION
            last["metricsComparable"] = True
            same_current_state = True
        if now_str is None:
            now_str = _dt.datetime.now().strftime("%m-%d %H:%M")
        current_row_already_recorded = bool(
            last
            and _tuple(last) == _tuple(cur)
            and last.get("metricVersion") == CURRENT_METRIC_VERSION
        )
        # 매 배치(replay 루프)마다 testset별로 한 행씩 항상 기록한다. 값이 안 바뀐
        # testset(예: 이번 룰이 thin만 건드려 study 동일)도 carry-forward 로 남겨야
        # study·thin 행 수가 어긋나지 않아 배치번호(#)가 lockstep 정렬된다
        # (#N = 같은 replay 배치). 이전엔 동일 KPI면 skip 해서 study 행이 빠지고
        # 최신정렬 번호와 충돌 → #1이 사라진 듯 보였다. 단, 연속으로 완전히 동일한
        # 행이 2줄 이상 쌓이는 것만 막는다(같은 배치 리포트 재생성 방지).
        if (not same_current_state
                and not current_row_already_recorded
                and (len(hist) < 2
                     or _tuple(hist[-1]) != _tuple(cur)
                     or _tuple(hist[-2]) != _tuple(cur))):
            hist.append({
                "ts": now_str, **cur,
                "metricVersion": CURRENT_METRIC_VERSION,
                "metricsComparable": True,
            })
    try:
        json.dump(hist, open(hist_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    except Exception:
        pass
    return hist


def _render_rows(hist: list[dict]):
    prev = None
    prev_version = None
    for k in hist:
        if k.get("metricsComparable") is False:
            p = k.get("paths") or {}
            yield k, None, None, "비교 제외", f"{p.get('free','-')}/{p.get('fallback','-')}"
            continue
        pct = (100 * k["cm"] / k["cs"]) if k.get("cs") else 0
        version = k.get("metricVersion", 1)
        d = None if prev is None or version != prev_version else pct - prev
        prev = pct
        prev_version = version
        fld = f"{100*k['fm']/k['fs']:.1f}%" if k.get("fs") else "-"
        p = k.get("paths") or {}
        yield k, pct, d, fld, f"{p.get('free','-')}/{p.get('fallback','-')}"


def inject_html(html_path: str, hist: list[dict]) -> None:
    cells = []
    for k, pct, d, fld, paths_s in _render_rows(hist):
        cell_text = (
            "비교 제외 <span class='muted'>(구 집계식)</span>"
            if pct is None else f"{k['cm']}/{k['cs']} ({pct:.1f}%)"
        )
        if d is None:
            dcol, dtxt = "var(--muted)", "·"
        else:
            dcol = "var(--up)" if d > 0 else ("var(--down)" if d < 0 else "var(--muted)")
            dtxt = f"{d:+.1f}"
        pending = k.get("ambiguous")
        pdrop_text = str(k.get("pdrop")) if pending is None else f"{k.get('pdrop')} (+{pending} pending)"
        cells.append(
            f"<tr><td>{k.get('ts','')}</td><td>{cell_text}</td>"
            f"<td style='color:{dcol}'>{dtxt}</td><td>{fld}</td>"
            f"<td>{pdrop_text}</td><td>{k.get('recog')}</td>"
            f"<td>{k.get('spur')}</td><td>{paths_s}</td></tr>"
        )
    total = ""
    latest_version = next(
        (k.get("metricVersion", 1) for k in reversed(hist)
         if k.get("metricsComparable") is not False and k.get("cs")),
        None,
    )
    comparable = [
        k for k in hist
        if k.get("metricsComparable") is not False
        and k.get("cs")
        and k.get("metricVersion", 1) == latest_version
    ]
    if len(comparable) >= 2:
        first, last = comparable[0], comparable[-1]
        f0 = 100 * first["cm"] / first["cs"]
        f1 = 100 * last["cm"] / last["cs"]
        taxonomy_changed = first.get("ambiguous") is None and last.get("ambiguous") is not None
        parser_part = (
            "parser taxonomy changed (old/new counts are not directly comparable), "
            if taxonomy_changed else
            f"parser_drop {first.get('pdrop')} &rarr; {last.get('pdrop')}, "
        )
        total = (f"<p class='note'><b>총 개선: 셀 {f0:.1f}% &rarr; {f1:.1f}% ({f1-f0:+.1f}pp), "
                 f"{parser_part}spurious {first.get('spur')} &rarr; {last.get('spur')}.</b></p>")
    legend = (
        "<p class='note'>"
        "<b>셀 정확도</b>=표 안 값(품명·규격·수량·단가·금액 등) 일치율 · "
        "<b>필드 정확도</b>=상단 스칼라 필드(상호·사업자번호·대표자·주소·금액 등) 일치율 · "
        "<b>&Delta;셀</b>=직전 대비 셀 정확도 변화(pp) · "
        "<b>파서누락</b>(parser_drop)=OCR엔 값이 있는데 파서가 떨군 결함 수 <b>(회수 가능)</b> · "
        "<b>인식오류</b>(recognition)=OCR이 글자 자체를 못 읽은 결함 수 (파서 대상 아님) · "
        "<b>지어내기</b>(spurious)=GT는 빈칸인데 추출이 값을 채운 오추출 수 <b>(낮을수록 좋음)</b> · "
        "<b>경로 free/fb</b>=free / fallback 경로로 처리된 장수"
        "</p>"
    )
    block = (
        f"{_MARK_A}<section><h2>Replay 진행 이력 <span class='muted'>(돌릴 때마다 자동 누적)</span></h2>"
        + legend +
        "<table><thead><tr><th>시각</th><th>셀 정확도</th><th>&Delta;셀</th><th>필드 정확도</th>"
        "<th>파서누락</th><th>인식오류</th><th>지어내기</th><th>경로 free/fb</th></tr></thead><tbody>"
        + "".join(cells) + "</tbody></table>" + total + f"</section>{_MARK_B}"
    )
    html = open(html_path, encoding="utf-8").read()
    if _MARK_A in html and _MARK_B in html:
        html = re.sub(re.escape(_MARK_A) + ".*?" + re.escape(_MARK_B), block, html, flags=re.S)
    else:
        html = html.replace("<body>", "<body>\n" + block, 1)
    open(html_path, "w", encoding="utf-8").write(html)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ts", default="053_20260617_142725/study")
    args = ap.parse_args()
    hist = append_history(args.ts)
    if not hist:
        print("no replay sidecars yet — run replay_compare.py first")
        return 1
    L = ["# Replay 요약 — 돌릴 때마다 자동 누적되는 KPI 이력", "",
         "> parser_drop_classify 실행마다 replay_history.json에 한 줄 추가(변화 있을 때만).",
         "> 수치=수정 파서를 스냅샷에 재실행한 로컬 채점(디바이스 무관=GPU 파서 기준).",
         ">",
         "> **컬럼 뜻** — 셀 정확도=표 안 값 일치율 · 필드 정확도=상단 스칼라 필드 일치율 · "
         "Δ셀=직전 대비(pp) · 파서누락(parser_drop)=OCR엔 있는데 파서가 떨군 결함(회수 가능) · "
         "인식오류(recognition)=OCR이 글자를 못 읽음(파서 대상 아님) · "
         "지어내기(spurious)=GT 빈칸인데 값 채운 오추출(낮을수록 좋음) · 경로 free/fb=경로별 장수.", "",
         "| 시각 | 셀 정확도 | Δ셀 | 필드 정확도 | 파서누락 | 인식오류 | 지어내기 | 경로 free/fb |",
         "|---|--:|--:|--:|--:|--:|--:|--:|"]
    for k, pct, d, fld, paths_s in _render_rows(hist):
        dtxt = "·" if d is None else f"{d:+.1f}"
        cell_text = "비교 제외(구 집계식)" if pct is None else f"{k['cm']}/{k['cs']} ({pct:.1f}%)"
        L.append(f"| {k.get('ts','')} | {cell_text} | {dtxt} | {fld} "
                 f"| {k.get('pdrop')} (+{k.get('ambiguous')} pending) "
                 f"| {k.get('recog')} | {k.get('spur')} | {paths_s} |")
    open(OUT_MD, "w", encoding="utf-8").write("\n".join(L) + "\n")
    html_path = os.path.join(REPO, f"ocr-server/eval/runs/{args.ts.replace(chr(92),'/')}/PARSER_DROP_CLASSIFY_replay_compare.html")
    if os.path.isfile(html_path):
        inject_html(html_path, hist)
    latest = next((k for k in reversed(hist)
                   if k.get("metricsComparable") is not False and k.get("cs")), None)
    latest_text = f"{100*latest['cm']/latest['cs']:.1f}%" if latest else "-"
    print(f"history rows: {len(hist)}  (latest cell {latest_text})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
