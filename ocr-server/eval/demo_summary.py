"""demo_summary — 소생 데모 전 회차를 한 파일로 묶은 탭 리포트(회사 리뷰용).

★한 회차 = 품명 2개 = 파인튜닝 2번.
  1단계 = base 가 못 읽던 품명 1개를 살린다.
  2단계 = 그 파인튜닝이 새로 잃어버린 품명 1개를 추가해 둘 다 읽게 만든다 → 회차 완료.
  회차당 누적 +2개: 1차 2개 → 2차 4개 → 3차 6개 → 4차 8개.

run 별 리포트(DEMO_REPORT_<실행번호>.html)는 그대로 두고, 그 옆에 쌓이는 JSON 원장
(DEMO_REPORT_<실행번호>.json, demo-report.v1)을 모아 <b>1차·2차·3차·4차 탭</b>으로 낸다.
탭 전환은 인라인 JS 한 줄 — 외부 의존 없음, 파일 하나만 열면 끝(크롭도 base64 내장).

탭 구성
  실행 이력  (기본) 파인튜닝을 돌린 모든 시도 — 재시도 포함, 크롭 수·학습·AWS 비용까지
  전체       품명 × 회차 유지 매트릭스 + 최종 채택 게이트
  N차        그 회차의 단계별 하위 탭: <b>1-1차 / 1-2차</b>, 재시도가 있으면 <b>1-1-1차</b>
             처럼 늘어난다. 하위 탭 하나 = 파인튜닝 한 번(기준 정보·선정 근거·판정표).
             기본으로 열리는 건 그 단계에서 통과한 시도(체인에 들어간 모델).

    python eval/demo_summary.py                 # demo/ 아래 run 전부 + 4차까지 자리표시
    python eval/demo_summary.py --rounds 4      # 표시할 회차 상한(기본 4)
    python eval/demo_summary.py --input-dir eval/finetune/demo/samples --out <경로>
"""
from __future__ import annotations

import argparse
import glob
import html
import json
import os
import sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from finetune_report import _write_text  # noqa: E402

DEMO_DIR = os.path.join(HERE, "finetune", "demo")
DEFAULT_OUT = os.path.join(DEMO_DIR, "DEMO_SUMMARY.html")
ORD = ["1차", "2차", "3차", "4차", "5차", "6차", "7차", "8차"]


def _load_attempts(input_dir: str) -> dict[tuple[int, int], list[dict]]:
    """demo/**/DEMO_REPORT_*.json 을 (회차, 단계) → 시도 목록(시간순)으로 정리.

    ★재시도도 카운트한다. 2번째 모델이 실패해서 다시 돌리면 그건 '2-1 모델'이고,
      이력 탭에 전부 남는다. 체인에 들어가는 건 그중 통과한 시도.
    회차·단계는 누적 타깃 수에서 결정된다(홀수=1단계, 짝수=2단계).
    """
    out: dict[tuple[int, int], list[dict]] = {}
    for fp in sorted(glob.glob(os.path.join(input_dir, "**", "DEMO_REPORT_*.json"),
                               recursive=True)):
        try:
            with open(fp, encoding="utf-8") as f:
                j = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        if j.get("schemaVersion") != "demo-report.v1":
            continue
        cyc = int(j.get("cycle") or len(j.get("targets") or []))
        key = (int(j.get("roundNo") or (cyc + 1) // 2),
               int(j.get("step") or (1 if cyc % 2 else 2)))
        out.setdefault(key, []).append(j)
    for key in out:
        out[key].sort(key=lambda r: r.get("generatedAt") or "")
    return out


def _chain_view(attempts: dict[tuple[int, int], list[dict]]) -> dict[tuple[int, int], dict]:
    """단계별 대표 run = 통과한 마지막 시도(없으면 마지막 시도).

    체인(다음 단계의 시작 모델)에 들어가는 건 통과본이므로, 회차 탭·매트릭스는
    이 뷰를 쓴다. 실패 시도는 '실행 이력' 탭에서 본다.
    """
    view: dict[tuple[int, int], dict] = {}
    for key, lst in attempts.items():
        passed = [r for r in lst if (r.get("summary") or {}).get("allPass")]
        view[key] = (passed or lst)[-1]
    return view


def _attempt_label(step_index: int, i: int) -> str:
    """시도 표기 - 첫 시도는 'N', 재시도는 'N-1', 'N-2' …"""
    return f"{step_index}" if i == 0 else f"{step_index}-{i}"


def _run_history_index() -> dict[str, dict]:
    """RUN_HISTORY.jsonl 의 파인튜닝 기록을 실행번호(ts)로 색인 - 소요시간·요금·에폭."""
    path = os.path.join(HERE, "RUN_HISTORY.jsonl")
    idx: dict[str, dict] = {}
    if not os.path.exists(path):
        return idx
    for ln in open(path, encoding="utf-8"):
        ln = ln.strip()
        if not ln:
            continue
        try:
            d = json.loads(ln)
        except json.JSONDecodeError:
            continue
        if d.get("kind") == "finetune" and d.get("ts"):
            idx[str(d["ts"])] = d
    return idx


def _sel_line(sel: dict | None, basis: int | None, esc) -> str:
    """선정 근거 - demo_report 와 같은 기준(정확일치 우선, 변형은 병기)으로 표기."""
    if not sel:
        return ""
    # 구버전 JSON(exact 키 없음)은 total 로 폴백
    exact = sel.get("exact", sel.get("total", 0))
    exact_docs = sel.get("exactDocs", sel.get("docs", 0))
    exact_match = sel.get("exactMatch", sel.get("match", 0))
    wrong = " · ".join(f"“{esc(w)}” {n}회" for w, n in (sel.get("wrong") or [])) or "-"
    if not exact and not sel.get("total"):
        why = "기준셋에 미출현 - 학습 코퍼스/스캔 결과에서 선정"
    elif exact and not exact_match:
        why = "base 가 <b>전 출현 오독</b> - 원래 한 번도 못 읽던 품명"
    elif exact:
        why = (f"base 정답률 <b>{100.0 * exact_match / exact:.0f}%</b>"
               f"({exact_match}/{exact}) - 불안정하게 읽던 품명")
    else:
        why = "이 품명은 변형 형태로만 기준셋에 나타남"
    docs = f"기준셋 {basis:,}장 중 " if basis else ""
    variants = ""
    if (sel.get("total") or 0) > exact:
        variants = (f'<br><span class="muted">회사명·수량 꼬리가 붙은 변형까지 포함하면 '
                    f'{sel["total"]}셀 / {sel.get("docs", 0)}문서 (base 정답 {sel.get("match", 0)}). '
                    f'학습 크롭은 이 변형까지 모읍니다.</span>')
    return (f'<div class="box">선정 근거 - {why}.<br>{docs}'
            f'<b>{exact}셀({exact_docs}개 문서), base 정답 {exact_match}셀</b>. '
            f'대표 오독: {wrong}{variants}</div>')


def _step_body(run: dict, esc) -> str:
    c = run.get("counts") or {}
    basis = run.get("basisDocs")
    n_docs = f"{basis:,}장" if basis else "(리플레이 폴더 없음)"
    p = [f"""<table>
<tr><th style="width:30%">기준 문서셋</th><td>거래명세서 {n_docs} — held-out 리플레이 기준셋
 (학습에 절대 쓰지 않는 측정 전용 문서. 타깃 선정과 "못 읽는다"의 근거)</td></tr>
<tr><th>대상 컬럼</th><td>품목표의 <b>품명 ({esc(run.get('column') or 'itemName')})</b></td></tr>
<tr><th>시작 모델</th><td><b>{esc(run.get('compareLabel') or run.get('baseModel') or '')}</b>
 {'(직전 회차 결과 모델 위에서 이어 학습)' if run.get('compareDir') else '(official, 파인튜닝 없음)'}</td></tr>
<tr><th>학습 데이터</th><td>{
 f"타깃 품명 크롭 <b>{c['targetTrainUnique']}</b>장"
 + (f" ×복제 {c.get('oversampledTo', 0):,}줄"
    if (c.get('oversampledTo') or 0) > (c.get('targetTrainUnique') or 0) else " (복제 없음)")
 + f" + 일반 정답 크롭 앵커 {c.get('anchor', 0):,}장"
 if c.get('targetTrainUnique') is not None else
 '<span class="muted">미측정 - 코퍼스 집계(demo_corpus_count.py) 후 확정</span>'}</td></tr>
<tr><th>판정 데이터</th><td>학습에서 제외한 같은 품명 크롭 <b>{c.get('test', '?')}장</b> (held-out)</td></tr>
<tr><th>실행번호</th><td>{esc(run.get('runTag') or '')} · {esc(run.get('generatedAt') or '')}</td></tr>
</table>"""]
    n = len(run.get("targets") or [])
    for i, t in enumerate(run.get("targets") or [], 1):
        v = t.get("verdict") or {}
        badge = ('<span class="badge pass">성공</span>' if v.get("pass")
                 else '<span class="badge fail">실패</span>')
        p.append(f'<h3>[{i}/{n}] {esc(t["name"])} '
                 f'<span class="muted">({esc(t.get("role") or "")})</span> {badge}</h3>')
        p.append(_sel_line(t.get("selection"), basis, esc))
        cmp_l = esc(run.get("compareLabel") or "base")
        p.append(f'<table><tr><th style="width:220px">크롭 (판정용 held-out)</th><th>정답</th>'
                 f'<th>{cmp_l} 읽음</th><th>파인튜닝 읽음</th>'
                 f'<th style="width:70px">판정</th></tr>')
        for r in t.get("rows") or []:
            img = (f'<img src="data:image/jpeg;base64,{r["imgB64"]}" style="max-height:34px">'
                   if r.get("imgB64") else "")
            b_cls = "ok" if r["base"] == r["gt"] else "bad"
            f_cls = "ok" if r.get("ok") else "bad"
            mark = ('<span class="ok">성공</span>' if r.get("ok") else '<span class="bad">실패</span>')
            p.append(f"<tr><td>{img}</td><td><b>{esc(r['gt'])}</b></td>"
                     f"<td class='{b_cls}'>{esc(r['base']) or '(빈칸)'}</td>"
                     f"<td class='{f_cls}'>{esc(r['finetuned']) or '(빈칸)'}</td><td>{mark}</td></tr>")
        p.append(f"</table><p class='muted'>{cmp_l} {v.get('base', 0)}/{v.get('n', 0)} 정답 → "
                 f"파인튜닝 <b>{v.get('ft', 0)}/{v.get('n', 0)}</b> 정답</p>")
    s = run.get("summary") or {}
    ov = ('<span class="badge pass big">이 단계 판정: 성공</span>' if s.get("allPass")
          else '<span class="badge fail big">이 단계 판정: 실패</span>')
    p.append(f"<p class='big'>누적 성공 <b>{s.get('pass', 0)}개</b> / 시도 "
             f"{s.get('total', 0)}개 &nbsp; {ov}</p>")
    return "\n".join(p)


def _sub_label(round_no: int, step: int, attempt: int) -> str:
    """하위 탭 이름 - 1-1차 / 1-2차, 재시도는 1-1-1차, 1-1-2차 …"""
    return (f"{round_no}-{step}차" if attempt == 0
            else f"{round_no}-{step}-{attempt}차")


def _round_body(round_no: int, tries: dict[int, list[dict]], esc,
                starts: dict[int, str]) -> str:
    """한 회차 탭 = 단계별 하위 탭(1-1차 / 1-2차, 재시도는 1-1-1차 …).

    각 시도가 하위 탭 하나다. 실패한 시도도 탭으로 남아 무엇이 왜 실패했는지 볼 수 있고,
    기본으로 열리는 건 그 단계에서 통과한 시도(체인에 들어간 모델)다.
    """
    step_desc = {
        1: (f"시작 모델({starts.get(1, 'base')})이 한 번도 못 읽던 품명 1개를 골라 "
            f"파인튜닝으로 읽게 만든다."),
        2: (f"1단계 모델({starts.get(2, '')})이 새로 틀리게 된 품명 1개를 타깃에 추가해, "
            f"누적 품명을 <b>모두</b> 읽게 만든다. (통과하면 회차 완료)"),
    }
    last = (tries.get(2) or tries.get(1) or [])
    passed2 = [r for r in (tries.get(2) or []) if (r.get("summary") or {}).get("allPass")]
    if passed2:
        s = passed2[-1].get("summary") or {}
        head = (f'<span class="badge pass">성공 · 타깃 품명 모두 읽음 '
                f'(누적 {s.get("pass", 0)}개)</span>')
    elif tries.get(2):
        head = '<span class="badge fail">실패 · 재실행 필요</span>'
    else:
        head = '<span class="badge wait">1단계까지 진행 · 2단계(잃어버린 품명 회수) 남음</span>'
    p = [f'<p class="big">{ORD[round_no - 1]} {head}</p>']

    # 하위 탭 구성: (라벨, 본문, 통과여부)
    subs: list[tuple[str, str, bool]] = []
    for st in (1, 2):
        for i, run in enumerate(tries.get(st) or []):
            ok = (run.get("summary") or {}).get("allPass")
            label = _sub_label(round_no, st, i)
            if not ok:
                label += ' <span class="bad">실패</span>'
            elif i:
                label += ' <span class="muted">(재시도)</span>'
            inner = (f'<h3 style="border-bottom:2px solid #dde5ec;padding-bottom:6px">'
                     f'{_sub_label(round_no, st, i)} '
                     f'<span class="muted">→ {_model_name(round_no, st, run, esc)}</span></h3>'
                     f'<p class="muted">{step_desc[st]}</p>' + _step_body(run, esc))
            subs.append((label, inner, bool(ok)))
    if not subs:
        return "\n".join(p + ['<div class="box muted">아직 실행 전입니다.</div>'])

    # 기본으로 열 탭 = 마지막 통과 시도(체인에 들어간 모델), 없으면 마지막 시도
    default = max((i for i, (_, _, ok) in enumerate(subs) if ok), default=len(subs) - 1)
    g = round_no
    p.append('<div class="tabs sub">')
    for i, (label, _, _ok) in enumerate(subs):
        p.append(f'<button id="t{g}_{i}" class="{"on" if i == default else ""}"'
                 f' onclick="sub({g},{i},{len(subs)})">{label}</button>')
    p.append("</div>")
    for i, (_, inner, _ok) in enumerate(subs):
        p.append(f'<div id="p{g}_{i}" class="pane{" on" if i == default else ""}">{inner}</div>')
    if not tries.get(2):
        p.append('<div class="box muted">2단계는 아직 실행 전입니다. 1단계 모델이 새로 틀리게 된 '
                 '품명(스캔 결과 NEXT_TARGETS)에서 대표 1개를 골라 진행합니다.</div>')
    return "\n".join(p)


def _history(attempts: dict[tuple[int, int], list[dict]], esc) -> str:
    """실행 이력 탭 - 파인튜닝을 돌린 모든 시도(실패 포함)를 시간순으로.

    RUN_HISTORY.jsonl 의 파인튜닝 기록(소요시간·에폭·최고 acc·예상요금)을 실행번호로
    붙여서, '무엇을 몇 번 돌렸고 얼마 들었나'가 한 표에 보이게 한다.
    """
    hist = _run_history_index()
    rows = []
    for (r_no, st), lst in attempts.items():
        n = _step_index(r_no, st)
        for i, run in enumerate(lst):
            rows.append((run.get("generatedAt") or "", n, i, r_no, st, run))
    rows.sort()
    if not rows:
        return '<p class="muted">아직 실행 기록이 없습니다.</p>'

    p = ['<p class="muted">파인튜닝을 돌린 <b>모든 시도</b>입니다 - 실패해서 다시 돌린 것도 '
         '번호를 먹습니다(2번째 모델이 실패하면 다음이 <b>2-1</b>). 체인에 들어가는 건 '
         '통과한 시도이고, 실패 시도는 시작 모델을 바꾸지 않습니다.</p>',
         '<table><tr><th style="width:150px">회차·단계</th><th>타깃 품명 (누적)</th>'
         '<th style="width:130px">시작 모델</th><th>학습 크롭</th><th style="width:80px">판정 크롭</th>'
         '<th style="width:90px">누적 판정</th><th>실행번호</th><th>학습</th>'
         '<th style="width:90px">AWS 비용</th><th style="width:80px">결과</th></tr>']
    total_sec = total_usd = 0.0
    for _, n, i, r_no, st, run in rows:
        s = run.get("summary") or {}
        ok = s.get("allPass")
        # ★타깃은 누적이다 - 1차 2단계면 1단계 품명 + 이번 신규 품명 둘 다 학습·판정 대상.
        #   이번 단계에서 새로 들어온 것만 굵게.
        tl = []
        for t in run.get("targets") or []:
            nm = esc(t["name"])
            tl.append(f"<b>{nm}</b> <span class='muted'>(신규)</span>" if t.get("isNew") else nm)
        tgt = " · ".join(tl) or "-"
        h = hist.get(str(run.get("runTag") or ""), {})
        sec = float(h.get("elapsedSec") or 0)
        usd = float(h.get("estimatedCostUsd") or 0)
        total_sec += sec
        total_usd += usd
        train = []
        if h.get("epochsCompleted"):
            train.append(f"ep {h['epochsCompleted']}/{h.get('epochsPlanned', '?')}")
        if h.get("bestAcc") is not None:
            train.append(f"acc {float(h['bestAcc']):.3f}")
        if sec:
            train.append(f"{sec / 60:.0f}분")
        badge = ('<span class="badge pass">성공</span>' if ok
                 else '<span class="badge fail">실패</span>')
        retry = '' if i == 0 else f' <span class="muted">(재시도 {i})</span>'
        # 크롭 수 — 타깃 고유 크롭(복제 줄) + 망각방지 앵커 / 판정용 홀드아웃
        c = run.get("counts") or {}
        uniq, over = c.get("targetTrainUnique"), c.get("oversampledTo")
        anchor, test = c.get("anchor"), c.get("test")
        crop_train = (f'타깃 <b>{uniq}</b>장'
                      + (f' <span class="muted">({over:,}줄 복제)</span>'
                         if over and over > (uniq or 0) else "")
                      + (f'<br><span class="muted">+ 앵커 {anchor:,}장</span>' if anchor else "")
                      ) if uniq is not None else '<span class="muted">미측정</span>'
        cost = f"${usd:.2f}" if usd else "-"
        p.append(f'<tr><td><b>{ORD[r_no - 1]} {st}단계</b>{retry}</td>'
                 f'<td>{tgt}</td>'
                 f'<td class="muted">{esc(run.get("compareLabel") or "base")}</td>'
                 f'<td>{crop_train}</td>'
                 f'<td>{test if test is not None else "-"}장</td>'
                 f'<td>{s.get("pass", 0)}/{s.get("total", 0)}</td>'
                 f'<td class="muted">{esc(run.get("runTag") or "")}</td>'
                 f'<td class="muted">{" · ".join(train) or "-"}</td>'
                 f'<td>{cost}</td>'
                 f'<td>{badge}</td></tr>')
    p.append("</table>")
    tail = [f"총 {len(rows)}회 실행"]
    if total_sec:
        tail.append(f"학습 누적 {total_sec / 3600:.1f}시간")
    tail.append(f"AWS 예상 요금 합계 <b>${total_usd:.2f}</b>" if total_usd
                else "AWS 비용 기록 없음")
    p.append(f'<p class="muted">{" · ".join(tail)} '
             f'(학습·요금은 RUN_HISTORY.jsonl 의 파인튜닝 기록, 크롭 수는 각 실행의 학습셋 '
             f'manifest 에서 가져옵니다.)</p>')
    return "\n".join(p)


def _final_run(runs: dict, r_no: int) -> dict | None:
    """그 회차의 최종 모델 = 2단계 run(없으면 1단계)."""
    return runs.get((r_no, 2)) or runs.get((r_no, 1))


def _model_name(r_no: int, step: int, run: dict, esc) -> str:
    """그 단계가 만들어낸 파인튜닝 모델 이름 + 실행번호.

    2단계 산출물은 그 회차의 결과 모델 = 다음 회차의 시작 모델
    (run-finetune 이 demo/models/round<N>/ 에 보관).
    """
    name = (f"{ORD[r_no - 1]} 결과 모델" if step == 2 else f"{ORD[r_no - 1]} 1단계 모델")
    tag = esc(run.get("runTag") or "")
    return f"<b>{name}</b>" + (f' <span class="muted">({tag})</span>' if tag else "")


def _step_index(r_no: int, step: int) -> int:
    """통산 단계 번호(체인 위치). 1차1단계=1 … 4차2단계=8."""
    return (r_no - 1) * 2 + step


def _start_model(runs: dict, r_no: int, step: int, esc) -> str:
    """그 단계의 시작 모델 = 바로 앞 단계 모델(모델은 한 줄로 이어진다)."""
    run = runs.get((r_no, step))
    if run and run.get("compareLabel"):
        return esc(run["compareLabel"])
    n = _step_index(r_no, step)
    if n <= 1:
        return "base"
    prev = n - 1
    return f"{(prev + 1) // 2}차 {1 if prev % 2 else 2}단계 모델"


def _overview(runs: dict, rounds: int, esc) -> str:
    """전체 탭 - 누적 매트릭스 + 최종 채택.

    회차별 상세(단계·타깃·판정)는 회차 탭에 있으므로 여기서 반복하지 않는다.
    """
    p = [f'<p class="muted">모델은 단계마다 이어집니다 - base → 1차 1단계 → 1차 2단계 → '
         f'2차 1단계 → … → {ORD[rounds - 1]} 2단계(통산 {rounds * 2}번째). '
         f'각 단계는 <b>바로 앞 단계 모델</b> 위에서 학습하고, 누적 타깃도 함께 늘어납니다. '
         f'회차별 상세는 위의 회차 탭에서 봅니다.</p>']

    # 품명 × 회차 유지 매트릭스 — "살린 게 계속 읽히는가"를 한 장으로
    names: list[str] = []
    for key in sorted(runs):
        for t in runs[key].get("targets") or []:
            if t["name"] not in names:
                names.append(t["name"])
    if names:
        p.append('<h3>누적 - 살린 품명이 회차를 넘어 유지되는가</h3>'
                 '<p class="muted">회차마다 이전에 살린 품명을 학습에 계속 포함하고, 다음 회차는 '
                 '그 결과 모델 위에서 시작한다. 그래도 새 학습이 이전 품명을 다시 깨뜨릴 수 있으므로 '
                 '<b>매 회차 누적 품명 전부를 같은 판정셋으로 다시 채점</b>한다 - 아래 한 칸이라도 '
                 '하나라도 실패면 그 회차는 미완료.</p>'
                 '<table><tr><th>품명</th><th>도입</th>'
                 + "".join(f"<th>{ORD[i - 1]}</th>" for i in range(1, rounds + 1)) + "</tr>")
        for nm in names:
            intro, cells = "", []
            for i in range(1, rounds + 1):
                run = _final_run(runs, i)
                t = next((x for x in (run.get("targets") if run else []) or []
                          if x["name"] == nm), None)
                if not t:
                    cells.append('<td class="muted">-</td>')
                    continue
                if not intro:
                    intro = (f'{ORD[(t.get("introducedRound") or i) - 1]} '
                             f'{t.get("introducedStep") or "?"}단계')
                v = t.get("verdict") or {}
                mark = ('<span class="ok">성공</span>' if v.get("pass")
                        else '<span class="bad">실패</span>')
                cells.append(f"<td>{mark} <span class='muted'>{v.get('ft', 0)}/"
                             f"{v.get('n', 0)}</span></td>")
            p.append(f"<tr><td><b>{esc(nm)}</b></td>"
                     f"<td class='muted'>{intro or '-'}</td>{''.join(cells)}</tr>")
        p.append('</table><p class="muted">성공 = 그 회차의 최종 모델이 held-out 크롭을 전부 정답으로 '
                 '읽음. “-” = 그 회차에서는 아직 타깃이 아니었음.</p>')

    # ---- 최종 채택 게이트 ----
    last_n = rounds * 2
    last = runs.get((rounds, 2))
    p.append(f'<h3>최종 채택</h3>')
    if not last:
        p.append(f'<p class="muted">채택 조건: 마지막 <b>{last_n}번째 모델</b>'
                 f'({ORD[rounds - 1]} 2단계)이 누적 <b>{last_n}개 품명 전부</b>를 읽는 상태. '
                 f'아직 진행 중입니다.</p>')
    else:
        s = last.get("summary") or {}
        okall = s.get("allPass") and s.get("total") == last_n
        badge = (f'<span class="badge pass big">채택 가능 - {last_n}번째 모델이 '
                 f'{last_n}개 전부 읽음</span>' if okall
                 else f'<span class="badge fail big">채택 불가 - '
                      f'{s.get("pass", 0)}/{s.get("total", 0)}만 읽음</span>')
        p.append(f'<p class="big">{badge}</p>')
        p.append(f'<p class="muted">채택 후보 = {esc(last.get("modelName") or "")} '
                 f'({esc(last.get("runTag") or "")}) · 보관 위치 '
                 f'<code>eval/finetune/demo/models/step{last_n}/</code></p>')
    return "\n".join(p)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-dir", default=DEMO_DIR, help="DEMO_REPORT_*.json 을 찾을 폴더")
    ap.add_argument("--out", default=None, help="출력 HTML 경로")
    ap.add_argument("--rounds", "--cycles", dest="rounds", type=int, default=4,
                    help="표시할 회차(미실행분은 '예정'). 한 회차 = 품명 2개")
    args = ap.parse_args()

    attempts = _load_attempts(args.input_dir)
    runs = _chain_view(attempts)          # 단계별 대표(통과본) — 요약·회차 탭용
    rounds = max(args.rounds, max((k[0] for k in runs), default=0))
    esc = html.escape
    n_try = sum(len(v) for v in attempts.values())
    n_done = sum(1 for i in range(1, rounds + 1)
                 if (runs.get((i, 2)) or {}).get("summary", {}).get("allPass"))

    body = [f"""<!doctype html><html lang="ko"><head><meta charset="utf-8">
<title>파인튜닝</title>
<meta name="viewport" content="width=device-width, initial-scale=1"><style>
*{{box-sizing:border-box}}
body{{font-family:'Segoe UI',Malgun Gothic,sans-serif;margin:0;padding:20px 28px;
 max-width:none;color:#1a2733}}
h1{{font-size:22px}} h3{{font-size:16px;margin-top:26px}}
/* 표는 화면 폭을 다 쓰고, 좁아지면 표 안에서만 가로 스크롤(본문은 안 밀림) */
.tw{{overflow-x:auto;-webkit-overflow-scrolling:touch}}
table{{border-collapse:collapse;width:100%;margin:10px 0;min-width:640px}}
th,td{{border:1px solid #d7dee5;padding:6px 10px;font-size:13.5px;text-align:left;vertical-align:middle}}
th{{background:#f2f6fa}}
@media (max-width:820px){{
 body{{padding:14px 12px}}
 th,td{{padding:5px 7px;font-size:12.5px}}
 .tabs button{{padding:7px 12px;font-size:13px}}
}}
.box{{background:#f6f9fc;border:1px solid #d7dee5;border-radius:8px;padding:14px 18px;margin:14px 0;font-size:14px;line-height:1.65}}
.ok{{color:#0a7a3d;font-weight:700}} .bad{{color:#c0392b;font-weight:700}}
.badge{{display:inline-block;padding:2px 10px;border-radius:12px;font-size:12.5px;font-weight:700}}
.badge.pass{{background:#e3f6ea;color:#0a7a3d}} .badge.fail{{background:#fdeceb;color:#c0392b}}
.badge.wait{{background:#eef1f4;color:#5b6b7b}}
.muted{{color:#5b6b7b;font-size:12.5px}} .big{{font-size:16px}}
.tabs{{display:flex;flex-wrap:wrap;gap:4px;border-bottom:2px solid #dde5ec;margin:18px 0 4px}}
.tabs button{{border:1px solid #dde5ec;border-bottom:none;background:#f2f6fa;color:#37485a;
 padding:8px 20px;font-size:14px;font-weight:600;cursor:pointer;border-radius:8px 8px 0 0}}
.tabs button.on{{background:#fff;color:#0b63ce;border-color:#b9d3ef;box-shadow:0 2px 0 #fff}}
.tabs button:disabled{{color:#9aa8b5;cursor:default}}
.tabs.sub{{margin:14px 0 2px;border-bottom-width:1px}}
.tabs.sub button{{padding:6px 14px;font-size:13px}}
.pane{{display:none}} .pane.on{{display:block}}
</style></head><body>
<h1>파인튜닝 <span class="muted">- {datetime.now().strftime('%Y-%m-%d %H:%M')}
 · 완료 {n_done}회차 / 계획 {rounds}회차 (한 회차 = 품명 2개) · 총 {n_try}회 실행</span></h1>
<div class="tabs">"""]
    # 탭 = 실행 이력(기본) · 전체(누적·채택) · 1차~N차(회차 상세)
    panes: list[tuple[str, str, bool]] = [
        ("실행 이력", _history(attempts, esc), True),
        ("전체", _overview(runs, rounds, esc), True),
    ]
    for i in range(1, rounds + 1):
        tries = {st: attempts[(i, st)] for st in (1, 2) if (i, st) in attempts}
        starts = {st: _start_model(runs, i, st, esc) for st in (1, 2)}
        inner = (_round_body(i, tries, esc, starts) if tries else
                 f'<div class="box">{ORD[i - 1]}는 아직 실행 전입니다. 시작 모델 = '
                 f'{starts[1]} - 이 모델이 못 읽는 품명 1개를 1단계 타깃으로 골라 '
                 f'진행합니다.</div>')
        label = ORD[i - 1]
        if tries and (i, 2) not in tries:
            label += " <span class=muted>(진행중)</span>"
        elif not tries:
            label += " <span class=muted>(예정)</span>"
        panes.append((label, inner, bool(tries)))

    for i, (label, _, enabled) in enumerate(panes):
        dis = "" if enabled else " disabled"
        body.append(f'<button id="t{i}" class="{"on" if i == 0 else ""}"'
                    f' onclick="sel({i})"{dis}>{label}</button>')
    body.append("</div>")
    for i, (_, inner, _e) in enumerate(panes):
        body.append(f'<div id="p{i}" class="pane{" on" if i == 0 else ""}">{inner}</div>')

    body.append(f"""<script>
function sel(i){{for(var k=0;k<{len(panes)};k++){{
 document.getElementById('t'+k).className=(k==i?'on':'');
 document.getElementById('p'+k).className=(k==i?'pane on':'pane');}}}}
function sub(g,i,n){{for(var k=0;k<n;k++){{
 document.getElementById('t'+g+'_'+k).className=(k==i?'on':'');
 document.getElementById('p'+g+'_'+k).className=(k==i?'pane on':'pane');}}}}
</script></body></html>""")

    out = args.out or DEFAULT_OUT
    os.makedirs(os.path.dirname(out), exist_ok=True)
    # 대시는 하이픈으로 통일(사용자 요청). base64 는 영향 없음.
    # 표는 전부 스크롤 컨테이너로 감싼다(좁은 화면에서 본문이 밀리지 않도록).
    doc = ("\n".join(body).replace("—", "-")
           .replace("<table>", '<div class="tw"><table>')
           .replace("</table>", "</table></div>"))
    _write_text(out, doc)
    print(f"[demo-summary] {out}  (완료 {n_done}회차 / 표시 {rounds}회차 · 총 {n_try}회 실행)")
    for key in sorted(attempts):
        n = _step_index(*key)
        for i, run in enumerate(attempts[key]):
            s = run.get("summary") or {}
            print(f"[demo-summary]   모델 {_attempt_label(n, i)} "
                  f"({ORD[key[0] - 1]} {key[1]}단계): 누적 성공 "
                  f"{s.get('pass', 0)}/{s.get('total', 0)} "
                  f"{'PASS' if s.get('allPass') else 'FAIL'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
