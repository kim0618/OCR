"""run_all - one command: manifest -> run_batch -> compare -> metrics -> report -> checker.

Reproducibility entry point (plan Phase 5 gate).

    python eval/run_all.py                       # one testset (default invoice_study), fresh OCR
    python eval/run_all.py --reuse <run_ts>      # reuse an existing run's OCR (fast)
    python eval/run_all.py --testset invoice_thin
    python eval/run_all.py --all                 # ALL testsets in one shot (fire-and-forget,
                                                 #   e.g. start at 퇴근, read TREND next morning)

--all runs every registered testset, isolates failures (one bad testset does not
abort the rest), refreshes TREND.md/.html once, and prints a combined summary.
Live testsets re-OCR (need :9099); canned testsets replay recorded results.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from typing import Any


def _fmt_dur(sec: float | None) -> str:
    """Seconds -> human duration: '14분 32초' / '47초' / '-' when unknown."""
    if sec is None:
        return "-"
    s = int(round(sec))
    return f"{s // 60}분 {s % 60}초" if s >= 60 else f"{s}초"

import contract as C
from build_manifest import write_manifest
from compare_run import compare_run
from metrics import compute_metrics
from report import render_report, render_report_html
from run_batch import run_batch


def _measure(reuse: str | None, server: str, workers: int, testset: str,
             verbose: bool = True, run_id: str | None = None) -> dict[str, Any]:
    """Run steps 1–6 for one testset. Returns a result dict; never raises.

    run_id (e.g. "<batch>/study") forces the run dir, used by --all to nest both
    testsets under one batch folder.
    """
    def log(msg: str) -> None:
        if verbose:
            print(msg)

    res: dict[str, Any] = {"testset": testset, "ts": None, "ok": False,
                           "fieldAcc": None, "cellAcc": None,
                           "fieldMacro": None, "cellMacro": None, "error": None,
                           "elapsedSec": None}
    t0 = time.perf_counter()
    try:
        write_manifest(testset=testset)
        canned = C.get_testset(testset)["runMode"] == "canned"
        if reuse:
            ts = reuse
            if not os.path.isdir(os.path.join(C.RUNS_DIR, ts, "samples")):
                res["error"] = f"reuse run not found: {ts}"
                res["elapsedSec"] = round(time.perf_counter() - t0, 1)
                return res
            log(f"== [2/6] run_batch SKIPPED (reuse {ts}) ==")
        else:
            log(f"== [2/6] run_batch (testset={testset}) ==")
            # run_id (--all batch) forces the dir; else canned → stable dir,
            # live → fresh timestamp so history accumulates.
            forced = run_id or (testset if canned else None)
            out = run_batch(server=server, workers=workers, testset=testset, resume_ts=forced)
            ts = out["ts"]
        res["ts"] = ts

        log("== [3/6] compare ==")
        compare_run(ts, testset=testset)
        log("== [4/6] metrics ==")
        m = compute_metrics(os.path.join(C.RUNS_DIR, ts))
        res["fieldAcc"] = m["overall"]["field"]["accuracy"]
        res["cellAcc"] = m["overall"]["cell"]["accuracy"]
        res["fieldMacro"] = (m["overall"].get("fieldMacro") or {}).get("accuracy")
        res["cellMacro"] = (m["overall"].get("cellMacro") or {}).get("accuracy")
        res["sampleCount"] = m.get("sampleCount")
        _sp = m.get("spurious") or {}
        res["spuriousField"] = (_sp.get("field") or {}).get("count", 0)
        res["spuriousCell"] = (_sp.get("cell") or {}).get("count", 0)
        res["kind"] = C.get_testset(testset)["kind"]
        log(f"   field acc {res['fieldAcc']}  cell acc {res['cellAcc']}")
        log("== [5/6] report ==")
        rd = os.path.join(C.RUNS_DIR, ts)
        rp = render_report(rd)
        try:
            render_report_html(rd)
        except Exception as exc:
            log(f"   (report.html unavailable: {exc})")
        try:
            from report_compare import render_compare_html
            cmp = render_compare_html(rd)
            if cmp:
                log(f"   compare.html -> {cmp}")
            else:
                log("   (compare.html skipped - 직전 run 없음)")
        except Exception as exc:
            log(f"   (compare.html unavailable: {exc})")
        log(f"   {rp}")

        log("== [6/6] checker ==")
        p = subprocess.run(
            [sys.executable, os.path.join(C.HERE, "checker.py"), "--ts", ts, "--testset", testset],
            capture_output=not verbose, text=True, encoding="utf-8",
        )
        res["ok"] = p.returncode == 0
        if not res["ok"] and not verbose:
            out = (p.stdout or "") + (p.stderr or "")
            res["error"] = next((ln for ln in reversed(out.strip().splitlines()) if ln.strip()), "checker FAIL")

        # Analysis sidecars — generated HERE so they're produced wherever the run
        # executes (e.g. AWS overnight); no separate local pass needed. Best-effort:
        # never raises, never touches res["ok"] (not a gate). finetune_ledger runs
        # only on LIVE runs — canned thin is a mock, not real recognition to bank.
        log("== [analysis] finetune ledger + crops + table-align + parser-drop(전처리) ==")
        try:
            # live only (real recognition + real images): ledger first (writes
            # FINETUNE_LEDGER.json), then crops (reads it + processed/). table-align
            # + parser-drop-classify always (read compare/ + snapshots/ + samples/;
            # the latter emits PARSER_DROP_CLASSIFY incl. the 전처리 진단 section).
            # Order matters: crops depends on ledger.
            tools = []
            if not canned:
                tools += ["finetune_ledger.py", "finetune_crops.py", "finetune_crops_balance.py"]
            tools.append("table_align_diag.py")
            tools.append("parser_drop_classify.py")  # parser-drop 분류 + 전처리 진단(자동 생성)
            for tool in tools:
                rc = subprocess.run(
                    [sys.executable, os.path.join(C.HERE, tool), "--ts", ts, "--testset", testset],
                    capture_output=not verbose, text=True, encoding="utf-8",
                ).returncode
                if rc != 0:
                    log(f"   (WARN {tool} exit={rc} — sidecar not generated)")
        except Exception as exc:
            log(f"   (analysis sidecars skipped: {exc})")
    except Exception as exc:  # isolation: a broken testset must not sink the others
        res["error"] = f"{type(exc).__name__}: {exc}"
    res["elapsedSec"] = round(time.perf_counter() - t0, 1)
    return res


def _refresh_trend(testset_for_line: str | None = None) -> None:
    try:
        from trend import latest_delta_line, render_md, render_html
        md, html = render_md(), render_html()
        if testset_for_line:
            line = latest_delta_line(testset_for_line)
            if line:
                print("== trend ==")
                print(" ", line)
        print(f"  TREND.md   -> {md}")
        print(f"  TREND.html -> {html}")
    except Exception as exc:
        print(f"  (trend unavailable: {exc})")


def run_all(reuse: str | None, server: str, workers: int,
            testset: str = C.DEFAULT_TESTSET) -> int:
    """Single testset, verbose (the classic entry point)."""
    print(f"== [1/6] manifest (testset={testset}) ==")
    r = _measure(reuse, server, workers, testset, verbose=True)
    print()
    _refresh_trend(testset)
    # 실행 이력 장부(RUN_HISTORY): 단일 --testset 도 기록. run-rekey.sh 처럼 --all 이
    # 아닌 단일 testset(invoice_rekey) 실행이 여기로 오는데, 예전엔 기록 훅이 run_all_multi
    # (--all) 에만 있어 리키잉 eval 이 장부에 안 남았다 → 실데이터 testset 이면 여기서도 기록.
    try:
        import run_history
        if r.get("sampleCount") and testset != C.DEFAULT_TESTSET:
            run_history.record(
                "eval", ts=r.get("ts"), images=r.get("sampleCount"),
                elapsedSec=r.get("elapsedSec"),
                field=round((r.get("fieldAcc") or 0) * 100, 1) if r.get("fieldAcc") else None,
                cell=round((r.get("cellAcc") or 0) * 100, 1) if r.get("cellAcc") else None)
    except Exception as exc:
        print(f"  (run_history unavailable: {exc})")
    print()
    if r["ok"]:
        print(f"MVP GO - pipeline ran {r['ts']} (testset={testset}), checker PASS")
        return 0
    print(f"MVP FAIL - testset={testset}: {r.get('error') or 'checker failed'}")
    return 1


def _short(testset: str) -> str:
    """invoice_study -> study, invoice_thin -> thin (batch subfolder name)."""
    return testset.replace("invoice_", "") or testset


import re as _re

_BATCH_RE = _re.compile(r"^(?:(\d{3})_)?\d{8}_\d{6}$")  # 001_YYYYMMDD_HHMMSS 또는 옛 YYYYMMDD_HHMMSS


def _next_seq() -> int:
    """기존 배치 폴더 NNN 프리픽스의 최댓값 +1 = 다음 회차. 폴더 앞 NNN_ 프리픽스용.
    (개수 기반은 폴더 삭제 시 빈 번호를 재사용해 기존 폴더와 충돌하므로 max 기반 = 삭제 안전.)"""
    if not os.path.isdir(C.RUNS_DIR):
        return 1
    nums = []
    for d in os.listdir(C.RUNS_DIR):
        if not os.path.isdir(os.path.join(C.RUNS_DIR, d)):
            continue
        m = _BATCH_RE.match(d)
        if m and m.group(1):
            nums.append(int(m.group(1)))
    return (max(nums) + 1) if nums else 1


def _role_label(testset: str, kind: str, html: bool = False) -> str:
    """종류 컬럼: rich=기준점(골든), thin=학습데이터. thin이 아직 녹화본(canned)이면
    '현재 모형'을 덧붙여 '실제 수천장'으로 오해하지 않게 - 실데이터(live)면 자동 제거."""
    if kind == "rich":
        return "회귀 기준점"
    canned = C.get_testset(testset)["runMode"] == "canned"
    if not canned:
        return "학습데이터"
    tag = " <span class='muted'>(실데이터 대기)</span>" if html else " (실데이터 대기)"
    return "학습데이터" + tag


def _write_batch_summary(batch_dir: str, batch: str, results: list[dict[str, Any]],
                         elapsed: float | None = None) -> str:
    import datetime as _dt
    gen = _dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    gen_line = f"_생성 {gen} · 소요 {_fmt_dur(elapsed)}_" if elapsed is not None else f"_생성 {gen}_"
    L = [f"# 학습 종합보고서 - {batch}", "", gen_line, "",
         "> - **필드 정확도** = 공급자 상호·사업자번호·대표자·주소, 공급받는자 상호·사업자번호·대표자·주소, "
         "작성일자, 공급가액, 세액, 합계금액, 누계, 총수량 (thin 추가: 할인액·문서번호·과세유형)",
         "> - **셀 정확도** = 품명, 규격, 품목코드, LOT번호, 유효기간, 수량, 단가, 금액 (thin 추가: 제조번호)",
         "> - **검증(게이트)** = 하니스 자기점검(PASS여야 수치 신뢰)",
         "> - **정확도 표기 = micro / macro.** micro=일치÷전체 채점칸(큰 표가 지배) · "
         "macro=샘플당 정확도의 평균(샘플 동등 가중). 둘이 벌어지면 큰 표가 평균을 좌우하는 것 — "
         "수천장에선 macro 가 '핵심 샘플 다수가 깨져도 전체는 좋아 보임'을 정직하게 드러냄.", "",
         "| 데이터셋 | 종류 | 건수 | 필드 (micro/macro) | 셀 (micro/macro) | 소요 시간 | 검증(게이트) | 상세 |",
         "|---|---|--:|--:|--:|--:|---|---|"]
    n_ok = 0

    def _mm(micro, macro):
        mi = "n/a" if micro is None else f"{micro * 100:.1f}%"
        ma = "n/a" if macro is None else f"{macro * 100:.1f}%"
        return f"{mi} / {ma}"

    for r in results:
        n_ok += 1 if r["ok"] else 0
        sub = _short(r["testset"])
        fa = _mm(r["fieldAcc"], r.get("fieldMacro"))
        ca = _mm(r["cellAcc"], r.get("cellMacro"))
        chk = "✅ PASS" if r["ok"] else f"❌ FAIL ({r.get('error') or '?'})"
        role = _role_label(r["testset"], r.get("kind", ""), html=False)
        n = r.get("sampleCount", "-")
        dur = _fmt_dur(r.get("elapsedSec"))
        L.append(f"| {r['testset']} `{sub}/` | {role} | {n}건 | {fa} | {ca} | {dur} | {chk} "
                 f"| [리포트 보기]({sub}/report.html) |")
    all_ok = n_ok == len(results)
    _sp_tot = sum((r.get("spuriousField") or 0) for r in results)
    _sp_line = (f"- **지어내기(spurious)**: GT 빈칸인데 추출이 채운 필드 **{_sp_tot}건** "
                "(정확도엔 안 잡히는 false positive) — 상세·rule/learn 태그는 각 리포트 참조"
                ) if _sp_tot else "- 지어내기(spurious): 0건 (빈칸 지어내기 없음)"
    L += ["", f"**{'전체 GO' if all_ok else '일부 FAIL'}** ({n_ok}/{len(results)} checker PASS)", "",
          _sp_line,
          "- 추세(직전 대비 ▲/▼): [TREND.html](TREND.html) · [TREND.md](TREND.md)",
          "- study = 기준점(사람검수 골든 6장, 회귀 안전망) · "
          "thin = 학습데이터 자리(현재는 모형, 실 DB 데이터 오면 교체)"]
    out = os.path.join(batch_dir, "SUMMARY.md")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    return out


def render_summary_html(batch_dir: str, batch: str, results: list[dict[str, Any]],
                        elapsed: float | None = None) -> str:
    """SUMMARY.html - styled batch summary (same look as TREND.html, in a browser)."""
    import datetime as _dt
    from trend import _CSS, _esc, trend_sections_html
    from trend import _rows as _trend_rows, _delta_html, _changed_population
    gen = _dt.datetime.now().strftime("%Y-%m-%d %H:%M")

    def _prev_acc(testset: str) -> tuple[Any, Any] | None:
        """직전 run의 (fieldAcc, cellAcc). 표본 수가 다르면 비교 보류(None)."""
        try:
            trows = _trend_rows(testset)
        except Exception:
            return None
        if len(trows) < 2:
            return None
        cur, prev = trows[-1], trows[-2]
        if _changed_population(cur, prev):
            return None
        return prev.get("fieldAcc"), prev.get("cellAcc")
    dur_txt = f" · 소요 {_fmt_dur(elapsed)}" if elapsed is not None else ""
    n_ok = sum(1 for r in results if r["ok"])
    all_ok = n_ok == len(results)
    H = ["<!doctype html><html lang='ko'><head><meta charset='utf-8'>",
         "<meta name='viewport' content='width=device-width,initial-scale=1'>",
         f"<title>학습 종합보고서 - {_esc(batch)}</title><style>{_CSS}</style></head><body>",
         "<div class='head'><h1>학습 종합보고서</h1>"
         f"<div class='gen'>실행 {_esc(batch)} · 생성 {gen}{dur_txt}</div></div>",
         "<div class='note'>"
         "<div class='row'><b>필드 정확도</b> = 공급자 상호·사업자번호·대표자·주소, "
         "공급받는자 상호·사업자번호·대표자·주소, 작성일자, 공급가액, 세액, 합계금액, 누계, 총수량"
         " <span class='muted'>(thin 추가: 할인액·문서번호·과세유형)</span></div>"
         "<div class='row'><b>셀 정확도</b> = 품명, 규격, 품목코드, LOT번호, 유효기간, 수량, 단가, 금액"
         " <span class='muted'>(thin 추가: 제조번호)</span></div>"
         "<div class='row'><b>정확도 = micro / macro</b> · "
         "<b>micro</b>=일치÷전체 채점칸(큰 표가 지배) · <b>macro</b>=샘플당 정확도의 평균(샘플 동등 가중). "
         "<span class='muted'>둘이 벌어지면 큰 표가 평균을 좌우하는 것 — 수천장에선 macro 가 "
         "'핵심 샘플 다수가 깨져도 전체는 좋아 보임'을 정직하게 드러냄.</span></div>"
         "<div class='row'><b>검증(게이트)</b> = 하니스 자기점검(PASS여야 수치 신뢰)</div>"
         "</div>",
         "<section><table class='sumtable'><thead><tr>"
         "<th>데이터셋</th><th>종류</th><th>건수</th>"
         "<th>필드 정확도<br><span class='muted' style='font-weight:400'>micro / macro</span></th>"
         "<th>셀 정확도<br><span class='muted' style='font-weight:400'>micro / macro</span></th>"
         "<th>소요 시간</th><th>검증(게이트)</th><th>상세 리포트</th><th>비교 리포트</th>"
         "</tr></thead><tbody>"]

    def _mm(micro, macro):
        mi = "n/a" if micro is None else f"{micro * 100:.1f}%"
        ma = "n/a" if macro is None else f"{macro * 100:.1f}%"
        return f"{mi} <span class='muted'>/ {ma}</span>"

    for r in results:
        sub = _short(r["testset"])
        fa = _mm(r["fieldAcc"], r.get("fieldMacro"))
        ca = _mm(r["cellAcc"], r.get("cellMacro"))
        # 이전 run 대비 델타(▲/▼) — 상단 필드/셀 정확도 옆에
        _prev = _prev_acc(r["testset"])
        if _prev is not None:
            _fdh = _delta_html(r["fieldAcc"], _prev[0])
            _cdh = _delta_html(r["cellAcc"], _prev[1])
            fa = f"{fa} <span style='font-size:12px'>{_fdh}pp</span>"
            ca = f"{ca} <span style='font-size:12px'>{_cdh}pp</span>"
        chk = ("<span class='up'>✅ PASS</span>" if r["ok"]
               else f"<span class='down'>❌ FAIL</span>")
        role = _role_label(r["testset"], r.get("kind", ""), html=True)
        n = r.get("sampleCount", "-")
        # compare.html 존재 여부 확인
        cmp_path = os.path.join(batch_dir, sub, "compare.html")
        cmp_btn = (f"<a class='btn' style='background:var(--warn);border-color:var(--warn)' "
                   f"href='{sub}/compare.html'>비교 보기</a>"
                   if os.path.isfile(cmp_path)
                   else "<span class='muted' style='font-size:12px'>직전 없음</span>")
        dur = _fmt_dur(r.get("elapsedSec"))
        H.append(f"<tr><td>{_esc(r['testset'])} <code>{sub}/</code></td><td>{role}</td>"
                 f"<td>{n}건</td><td>{fa}</td><td>{ca}</td><td>{dur}</td><td>{chk}</td>"
                 f"<td><a class='btn' href='{sub}/report.html'>리포트 보기</a></td>"
                 f"<td>{cmp_btn}</td></tr>")
    H.append("</tbody></table>")
    cls, badge = ("ok", "🟢") if all_ok else ("bad", "🔴")
    H.append(f"<div class='latest {cls}'>{badge} <b>{'전체 GO' if all_ok else '일부 FAIL'}</b> "
             f"({n_ok}/{len(results)} checker PASS)</div>")
    H.append("<div class='legend'>study=기준점(사람검수 골든 6장)  ·  "
             "thin=학습데이터 자리(현재는 모형, 실 DB 오면 교체)  ·  "
             "전체 룰 수정 이력: <a href='../CHANGES.html'>CHANGES.html</a></div>")
    H.append("</section>")
    # 추세(TREND) 내용 임베드 - 클릭 없이 오늘 결과 + 이력 한 페이지에
    H.append("<div class='head' style='margin-top:24px'><h1 style='font-size:17px'>"
             "이전 학습 비교</h1><div class='gen'>직전 대비 ▲ 좋아짐 / ▼ 나빠짐 · "
             "단독 보기: <a href='TREND.html'>TREND.html</a></div></div>")
    H.append(trend_sections_html())
    H.append("</body></html>")
    out = os.path.join(batch_dir, "SUMMARY.html")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(H))
    return out


def run_all_multi(server: str, workers: int, testsets: list[str] | None = None) -> int:
    """Every testset in one shot, grouped under ONE batch folder. Failures isolated.

    runs/<batch>/{study,thin}/  + SUMMARY.md + TREND.{md,html} at the batch root,
    so next morning you open one folder and see everything.
    """
    import datetime as _dt
    import shutil
    testsets = testsets or list(C.TESTSETS.keys())
    # 폴더 앞에 회차 번호(NNN_) → 보고서 회차(#1, #2)와 일치, 시간순 정렬도 유지
    batch = f"{_next_seq():03d}_{_dt.datetime.now().strftime('%Y%m%d_%H%M%S')}"
    batch_dir = os.path.join(C.RUNS_DIR, batch)
    os.makedirs(batch_dir, exist_ok=True)
    print(f"== run --all : {testsets}  →  runs/{batch}/ ==\n")

    batch_t0 = time.perf_counter()
    results: list[dict[str, Any]] = []
    for i, ts in enumerate(testsets, 1):
        print(f"---- [{i}/{len(testsets)}] {ts}  →  {batch}/{_short(ts)} ----")
        results.append(_measure(None, server, workers, ts, verbose=True,
                                run_id=f"{batch}/{_short(ts)}"))
        print()
    batch_elapsed = time.perf_counter() - batch_t0

    # one combined TREND, then copy it into the batch folder for self-containment
    try:
        from trend import render_md, render_html
        md, html = render_md(), render_html()
        shutil.copyfile(md, os.path.join(batch_dir, "TREND.md"))
        shutil.copyfile(html, os.path.join(batch_dir, "TREND.html"))
    except Exception as exc:
        print(f"  (trend unavailable: {exc})")
    # 전역 룰 수정 장부 갱신 (효과 = 이 배치 run으로 자동 채워짐)
    try:
        from changes import render_html as render_changes
        render_changes()
    except Exception as exc:
        print(f"  (CHANGES.html unavailable: {exc})")
    # 실행 이력 장부(RUN_HISTORY): 실데이터 testset(thin)을 대표로 기록 — 장수·소요·처리량
    try:
        import run_history
        for r in results:
            if r.get("sampleCount") and r["testset"] != C.DEFAULT_TESTSET:  # thin(실데이터)
                run_history.record(
                    "eval", ts=r.get("ts"), images=r.get("sampleCount"),
                    elapsedSec=r.get("elapsedSec"),
                    field=round((r.get("fieldAcc") or 0) * 100, 1) if r.get("fieldAcc") else None,
                    cell=round((r.get("cellAcc") or 0) * 100, 1) if r.get("cellAcc") else None)
    except Exception as exc:
        print(f"  (run_history unavailable: {exc})")
    summary = _write_batch_summary(batch_dir, batch, results, batch_elapsed)
    try:
        render_summary_html(batch_dir, batch, results, batch_elapsed)
    except Exception as exc:
        print(f"  (SUMMARY.html unavailable: {exc})")

    print("\n" + "=" * 60)
    print(f"run --all 요약  →  runs/{batch}/")
    print("=" * 60)
    hdr = f"{'testset':<16} {'필드 mi/ma':>14} {'셀 mi/ma':>14}  checker"
    print(hdr)
    print("-" * len(hdr))

    def _mm(micro, macro):
        mi = "n/a" if micro is None else f"{micro * 100:.1f}"
        ma = "n/a" if macro is None else f"{macro * 100:.1f}"
        return f"{mi}/{ma}"

    n_ok = 0
    for r in results:
        n_ok += 1 if r["ok"] else 0
        fa = _mm(r["fieldAcc"], r.get("fieldMacro"))
        ca = _mm(r["cellAcc"], r.get("cellMacro"))
        status = "PASS" if r["ok"] else f"FAIL ({r.get('error') or '?'})"
        print(f"{r['testset']:<16} {fa:>14} {ca:>14}  {status}")
    all_ok = n_ok == len(results)
    print()
    print(f"{'전체 GO' if all_ok else '일부 FAIL'}  ({n_ok}/{len(results)} checker PASS)")
    print(f"총 소요 시간: {_fmt_dur(batch_elapsed)}")
    print(f"다음날 이 폴더 하나만 열면 됨:  runs/{batch}/")
    print(f"  ├ SUMMARY.html (요약, 브라우저)  ·  SUMMARY.md")
    print(f"  ├ TREND.html   (추세, 브라우저)")
    print(f"  ├ study/report.md")
    print(f"  └ thin/report.md")
    return 0 if all_ok else 1


def summarize_batch(batch: str) -> int:
    """재-OCR 없이 기존 배치 폴더에서 SUMMARY.md/html + TREND 만 재생성.

    각 testset 하위(<batch>/study, <batch>/thin)의 metrics.json을 읽어 요약을 만든다.
    --all 이 중간에 끊겨(또는 --reuse 로 개별만 돌려) 배치 SUMMARY 가 없을 때 사용:
        python eval/run_all.py --summary-only 061_20260702_111643
    """
    import json
    import shutil
    bdir = os.path.join(C.RUNS_DIR, batch)
    if not os.path.isdir(bdir):
        print(f"배치 폴더 없음: {bdir}")
        return 1
    sub2ts = {_short(name): name for name in C.TESTSETS}   # 'study'->'invoice_study'
    results: list[dict[str, Any]] = []
    for sub in sorted(os.listdir(bdir)):
        mp = os.path.join(bdir, sub, "metrics.json")
        if not os.path.isfile(mp) or sub not in sub2ts:
            continue
        testset = sub2ts[sub]
        m = json.load(open(mp, encoding="utf-8"))
        ov = m.get("overall", {})
        sp = m.get("spurious") or {}
        results.append({
            "testset": testset, "ts": f"{batch}/{sub}", "ok": True,
            "fieldAcc": (ov.get("field") or {}).get("accuracy"),
            "cellAcc": (ov.get("cell") or {}).get("accuracy"),
            "fieldMacro": (ov.get("fieldMacro") or {}).get("accuracy"),
            "cellMacro": (ov.get("cellMacro") or {}).get("accuracy"),
            "sampleCount": m.get("sampleCount"),
            "spuriousField": (sp.get("field") or {}).get("count", 0),
            "spuriousCell": (sp.get("cell") or {}).get("count", 0),
            "kind": C.get_testset(testset)["kind"], "elapsedSec": None,
        })
    if not results:
        print("metrics.json 있는 하위 testset 없음 — 먼저 리포트를 만들어야 함")
        return 1
    try:  # TREND 갱신 후 배치 폴더로 복사(자기완결)
        from trend import render_md, render_html
        shutil.copyfile(render_md(), os.path.join(bdir, "TREND.md"))
        shutil.copyfile(render_html(), os.path.join(bdir, "TREND.html"))
    except Exception as exc:
        print(f"(trend 재생성 스킵: {exc})")
    out = _write_batch_summary(bdir, batch, results)
    try:
        render_summary_html(bdir, batch, results)
    except Exception as exc:
        print(f"(SUMMARY.html 스킵: {exc})")
    print(f"SUMMARY 생성 완료 → {out}")
    print(f"  {os.path.join(bdir, 'SUMMARY.html')}")
    print(f"  {os.path.join(bdir, 'TREND.html')}")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--reuse", default=None, help="reuse an existing run_ts (skip live OCR)")
    ap.add_argument("--server", default="http://127.0.0.1:9099")
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--testset", default=C.DEFAULT_TESTSET)
    ap.add_argument("--all", action="store_true", help="run every registered testset in one shot")
    ap.add_argument("--summary-only", default=None,
                    help="재-OCR 없이 배치 SUMMARY/TREND만 재생성 (배치 폴더명, 예: 061_20260702_111643)")
    args = ap.parse_args()
    if args.summary_only:
        sys.exit(summarize_batch(args.summary_only))
    if args.all:
        sys.exit(run_all_multi(args.server, args.workers))
    sys.exit(run_all(args.reuse, args.server, args.workers, args.testset))
