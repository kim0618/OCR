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
import re
import sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from finetune_report import _write_text  # noqa: E402
from demo_next_target import is_item_name, same_text  # noqa: E402

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
        # 미리보기 샘플(demo/samples/)은 실적이 아니다 — 집계 제외.
        if "samples" in os.path.normpath(fp).split(os.sep):
            continue
        try:
            with open(fp, encoding="utf-8") as f:
                j = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        if j.get("schemaVersion") != "demo-report.v1":
            continue
        # 산출물 폴더 순번(001_260803_1508)을 실행번호에 함께 보여준다 — 폴더를 바로 찾게.
        folder = os.path.basename(os.path.dirname(fp))
        if (m := re.match(r"(\d{3})_", folder)):
            j["runSeq"] = m.group(1)
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


_SCAN_CACHE: dict[str, int | None] = {}


def _scan_fail_count(tag: str) -> int | None:
    """demo/scans/<tag>.jsonl 에서 '못 읽은 크롭' 수. 파일 없으면 None.

    스캔은 기준셋 품명 크롭 전량을 그 모델로 읽은 결과다 - 여기서 오답 수가
    곧 '그 모델이 못 읽는 품명 크롭' 규모다(1단계 타깃은 이 안에서 고른다).

    ★품명 칸이어도 할인·집계 행(매입에누리 등)과 표 헤더 조각이 섞여 들어온다.
      후보 표에서 그걸 빼는데 요약 숫자에는 남으면 둘이 안 맞는다 - 같이 뺀다.
    """
    if tag in _SCAN_CACHE:
        return _SCAN_CACHE[tag]
    path = os.path.join(DEMO_DIR, "scans", f"{tag}.jsonl")
    n = None
    if os.path.exists(path):
        n = 0
        for ln in open(path, encoding="utf-8"):
            ln = ln.strip()
            if not ln:
                continue
            try:
                r = json.loads(ln)
            except json.JSONDecodeError:
                continue
            # 공백만 다른 건 실패로 세지 않는다(demo_next_target.same_text 와 같은 잣대).
            if (is_item_name(r.get("gt") or "")
                    and not same_text(r.get("gt") or "", r.get("pred") or "")):
                n += 1
    _SCAN_CACHE[tag] = n
    return n


def _start_scan_tag(attempts: dict, run: dict) -> str:
    """이 run 의 <시작 모델>에 해당하는 스캔 파일 태그.

    1단계째면 base 기준선(000_base), 그 외에는 직전 단계 통과본의 실행번호.
    """
    prev_n = int(run.get("compareStep") or 0)
    if prev_n <= 0:
        return "000_base"
    key = ((prev_n + 1) // 2, 1 if prev_n % 2 else 2)
    for r in reversed(attempts.get(key) or []):
        if (r.get("summary") or {}).get("allPass"):
            return str(r.get("runTag") or "")
    return ""


def _fmt_crops(n: int | None) -> str:
    """크롭 수 표기 - 반올림 없이 있는 그대로."""
    return f"{n:,} 크롭" if n else "-"


def _fmt_docs(n: int | None) -> str:
    """문서(원본 이미지) 수 표기."""
    return f"{n:,}장" if n else "-"


def _run_id(run: dict) -> str:
    """실행번호 표기 - 산출물 폴더 순번이 있으면 붙인다(001_260803_1508)."""
    tag = run.get("runTag") or ""
    seq = run.get("runSeq")
    return f"{seq}_{tag}" if seq else tag


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
    # 기준 정보(문서셋·컬럼·시작 모델·크롭 수·실행번호)는 실행 이력 탭에 있으므로
    # 회차 탭에서는 반복하지 않는다 — 여기서는 타깃별 판정만 본다.
    p: list[str] = []
    n = len(run.get("targets") or [])
    for i, t in enumerate(run.get("targets") or [], 1):
        v = t.get("verdict") or {}
        badge = ('<span class="badge pass">성공</span>' if v.get("pass")
                 else '<span class="badge fail">실패</span>')
        cmp_l = esc(run.get("compareLabel") or "base")
        # 한 줄 요약 — 실행 이력과 같은 크롭 단위로만 말한다(셀·문서 수는 여기서 안 씀).
        pool_item = (run.get("pool") or {}).get("judgeItem")
        from_pool = (f' <span class="muted">(기준셋 품명 {_fmt_crops(pool_item)} 중)</span>'
                     if pool_item else "")
        # 품명이 8개까지 늘어나므로 각 표를 접을 수 있게 한다. 기본은 펼침.
        p.append(f'<details open style="margin:10px 0"><summary class="big" '
                 f'style="cursor:pointer;list-style:none">'
                 f'{esc(t["name"])} {badge} '
                 f'<span class="muted">· 판정 {v.get("n", 0)} 크롭</span>{from_pool}'
                 f'<span class="muted"> · {cmp_l} {v.get("base", 0)} 크롭 정답 → '
                 f'이 모델 {v.get("ft", 0)} 크롭 정답</span></summary>')
        p.append(f'<table><tr><th style="width:220px">크롭 (판정용 held-out)</th><th>정답</th>'
                 f'<th>{cmp_l} 읽음</th><th>파인튜닝 읽음</th>'
                 f'<th style="width:70px">판정</th></tr>')
        # 실패 크롭을 위로 — 26장이든 260장이든 스크롤 없이 문제부터 보이게.
        for r in sorted(t.get("rows") or [], key=lambda r: bool(r.get("ok"))):
            img = (f'<img src="data:image/jpeg;base64,{r["imgB64"]}" style="max-height:34px">'
                   if r.get("imgB64") else "")
            b_cls = "ok" if r["base"] == r["gt"] else "bad"
            f_cls = "ok" if r.get("ok") else "bad"
            mark = ('<span class="ok">성공</span>' if r.get("ok") else '<span class="bad">실패</span>')
            p.append(f"<tr><td>{img}</td><td><b>{esc(r['gt'])}</b></td>"
                     f"<td class='{b_cls}'>{esc(r['base']) or '(빈칸)'}</td>"
                     f"<td class='{f_cls}'>{esc(r['finetuned']) or '(빈칸)'}</td><td>{mark}</td></tr>")
        p.append("</table></details>")
    return "\n".join(p)


def _sub_label(round_no: int, step: int, attempt: int) -> str:
    """모델 이름 = 회차-단계-버전. 1차 1단계 첫 시도면 1-1-v1, 재시도는 1-1-v2 …"""
    return f"{round_no}-{step}-v{attempt + 1}"


def _passing_tag(attempts: dict, step_index: int) -> str | None:
    """통산 N번째 단계에서 <통과한> 시도의 모델 이름. 없으면 None."""
    if step_index < 1:
        return None
    key = ((step_index + 1) // 2, 1 if step_index % 2 else 2)
    out = None
    for i, run in enumerate(attempts.get(key) or []):
        if (run.get("summary") or {}).get("allPass"):
            out = _sub_label(key[0], key[1], i)
    return out


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
    p: list[str] = []

    # 하위 탭 구성: (라벨, 본문, 통과여부)
    subs: list[tuple[str, str, bool]] = []
    for st in (1, 2):
        for i, run in enumerate(tries.get(st) or []):
            ok = (run.get("summary") or {}).get("allPass")
            label = _sub_label(round_no, st, i)
            label += (' <span class="ok">성공</span>' if ok
                      else ' <span class="bad">실패</span>')
            inner = (f'<h3 style="border-bottom:2px solid #dde5ec;padding-bottom:6px">'
                     f'{_sub_label(round_no, st, i)}</h3>'
                     + _step_body(run, esc))
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

    p = ['<table><tr><th style="width:44px">#</th>'
         '<th style="width:56px">회차</th><th style="width:66px">단계</th>'
         '<th style="width:56px">버전</th><th style="width:150px">타깃 품명</th>'
         '<th style="width:88px">모델</th>'
         # 앞 3개는 '가진 것'(풀 모수), 네 번째가 '이번에 실제로 쓴 것'이다.
         # 헤더에 근거를 달아둬야 470만이 '학습에 쓴 장수'로 오해되지 않는다.
         '<th style="width:96px" title="그 학습 크롭이 나온 원본 문서 수 - 리키잉한 이미지 중 기준셋(9,001)이 아닌 것. 출처 메타가 있는 크롭으로만 세므로 최소치다">학습 문서</th>'
         '<th style="width:118px" title="학습에 쓸 수 있는 크롭 전량 = (실패풀+정답풀) − 판정풀. '
         '정답풀 상당수가 출처 메타 없이 수확돼, 정확히는 &quot;기준셋임이 확인되지 않은 나머지&quot;다. '
         '이번에 실제로 학습한 장수는 오른쪽 &quot;학습 크롭&quot; 열이다">학습 총크롭</th>'
         '<th style="width:112px" title="그중 품명 컬럼 크롭(matchRatio≥0.7). 출처·컬럼이 확인되는 것만 '
         '센 최소치 — 메타 없는 정답 크롭은 빠져 있다">품명 크롭</th>'
         '<th title="이번 run 이 실제로 학습한 크롭 = 타깃 + 앵커 (검증용 20장 제외)">학습 크롭</th>'
         '<th style="width:88px" title="판정 크롭이 나온 기준셋 문서 수 - 학습 금지 대상이라 이 문서들이 곧 판정 대상이다">판정 문서</th>'
         '<th style="width:112px" title="기준셋(9,001 문서)에서 온 크롭 전량 — 학습 금지 대상이라 '
         '이게 곧 판정 풀이다">판정 총크롭</th>'
         '<th style="width:108px" title="그중 품명 컬럼 크롭(matchRatio≥0.7). 다음 타깃 스캔이 '
         "읽는 장수와 같은 수다\">품명 크롭</th>"
         '<th style="width:104px" title="이 run 이 만든 모델이 기준셋 품명 크롭 전량을 다시 읽어 틀린 수(스캔 실측). 다음 단계 타깃은 이 안에서 고른다. 스캔은 판정 통과 run 에서만 돌므로 실패 행은 비어 있다">실패 크롭</th>'
         '<th style="width:72px" title="이번 단계에서 실제로 채점한 크롭 = 타깃 품명의 기준셋 출신 크롭">판정 크롭</th>'
                  '<th style="width:90px">AWS 비용</th><th style="width:80px">결과</th></tr>']
    total_sec = total_usd = 0.0
    for seq, (_, n, i, r_no, st, run) in enumerate(rows, 1):
        s = run.get("summary") or {}
        ok = s.get("allPass")
        # ★타깃은 누적이다 - 1차 2단계면 1단계 품명 + 이번 신규 품명 둘 다 학습·판정 대상.
        #   이번 단계에서 새로 들어온 것만 굵게.
        tl = []
        for t in run.get("targets") or []:
            nm = esc(t["name"])
            tl.append(f"<b>{nm}</b>" if t.get("isNew") else nm)
        tgt = " · ".join(tl) or "-"
        h = hist.get(str(run.get("runTag") or ""), {})
        sec = float(h.get("elapsedSec") or 0)
        usd = float(h.get("estimatedCostUsd") or 0)
        total_sec += sec
        total_usd += usd
        train = []
        # epochsPlanned 는 config 파일 값이라 -o 오버라이드(DEMO_EPOCHS)를 모른다 → 표기 안 함.
        # 대신 best 에폭을 보여준다: "ep 20 (best 13)" = 20 돌렸고 13에서 정점(자동 선택).
        if h.get("epochsCompleted"):
            ep = f"ep {h['epochsCompleted']}"
            if h.get("bestEpoch"):
                ep += f" (best {h['bestEpoch']})"
            train.append(ep)
        badge = ('<span class="badge pass">성공</span>' if ok
                 else '<span class="badge fail">실패</span>')
        # 버전 = 그 단계의 시도 순번. 첫 시도 v1, 재시도부터 v2·v3 …
        ver = f"v{i + 1}"
        retry = ''
        # 크롭 수 — 타깃 고유 크롭(복제 줄) + 망각방지 앵커 / 판정용 홀드아웃
        c = run.get("counts") or {}
        uniq, over = c.get("targetTrainUnique"), c.get("oversampledTo")
        anchor, test = c.get("anchor"), c.get("test")
        mix = c.get("anchorMix") or {}
        mix_t = (f' (품명 {mix.get("item", 0):,} · 짧은숫자 {mix.get("shortNum", 0):,})'
                 if mix else "")
        crop_train = (f'타깃 <b>{uniq}</b>'
                      + (f' <span class="muted">({over:,}줄 복제)</span>'
                         if over and over > (uniq or 0) else "")
                      + (f' <span class="muted" title="앵커 구성{mix_t}">· 앵커 {anchor:,}</span>'
                         if anchor else ' <span class="muted">· 앵커 없음</span>')
                      ) if uniq is not None else '<span class="muted">미측정</span>'
        # 총크롭 = 그 타깃이 코퍼스/기준셋에 가지고 있던 크롭 전량("가진 것").
        # 옆의 학습·판정 크롭은 그중 실제로 쓴 것 — 학습분은 검증용 20장을 뺀 수치다.
        pool = run.get("pool") or {}
        train_total = pool.get("train")
        train_item = pool.get("trainItem")
        basis = run.get("basisDocs")
        judge_total = pool.get("judge")
        judge_item = pool.get("judgeItem")
        judge_fail = _scan_fail_count(str(run.get("runTag") or ""))
        cost = f"${usd:.2f}" if usd else "-"
        p.append(f'<tr><td class="muted">{seq}</td>'
                 f'<td><b>{ORD[r_no - 1]}</b></td>'
                 f'<td><b>{st}단계</b></td>'
                 f'<td><b>{ver}</b>{retry}</td>'
                 f'<td>{tgt}</td>'
                 f'<td class="muted nw">{esc(_passing_tag(attempts, n - 1) or "base")}</td>'
                 f'<td class="nw">{_fmt_docs(pool.get("trainDocs"))}</td>'
                 f'<td class="nw">{_fmt_crops(train_total)}</td>'
                 f'<td class="nw">{_fmt_crops(train_item)}</td>'
                 f'<td class="nw">{crop_train}</td>'
                 f'<td class="nw">{_fmt_docs(pool.get("judgeDocs") or basis)}</td>'
                 f'<td class="nw">{_fmt_crops(judge_total)}</td>'
                 f'<td class="nw">{_fmt_crops(judge_item)}</td>'
                 f'<td class="nw">{_fmt_crops(judge_fail)}</td>'
                 f'<td class="nw">{test if test is not None else "-"} 크롭</td>'
                 f'<td>{cost}</td>'
                 f'<td>{badge}</td></tr>')
        if not ok:
            # 실패 사유 펼침 — 접혀 있다가 ▸ 를 누르면 실제 오답이 보인다(JS 불필요).
            p.append(f'<tr><td colspan="17" style="background:#fdf7f7">'
                     f'<details><summary style="cursor:pointer;color:#c0392b;font-weight:700">'
                     f'▸ 실패 사유</summary>'
                     f'<div style="padding:8px 4px 2px">{_why_fail(run, esc)}</div>'
                     f'</details></td></tr>')
        else:
            nxt = _next_block(run, esc, attempts)
            if nxt:
                p.append(f'<tr><td colspan="17" style="background:#f6faf7">'
                         f'<details><summary style="cursor:pointer;color:#0a7a3d;'
                         f'font-weight:700">▸ 다음 타깃 후보</summary>'
                         f'<div style="padding:8px 4px 2px">{nxt}</div>'
                         f'</details></td></tr>')
    # 합계는 표의 마지막 행으로 — AWS 비용 열 아래에 정렬돼야 읽기 쉽다.
    if total_usd:
        p.append(f'<tr style="background:#f2f6fa"><td colspan="15" '
                 f'style="text-align:right"><b>합계</b></td>'
                 f'<td><b>${total_usd:.2f}</b></td><td></td></tr>')
    p.append("</table>")
    p.append(_lineage(attempts, esc))
    return "\n".join(p)


def _next_targets(run: dict) -> dict | None:
    """그 run 폴더의 NEXT_TARGETS.json(스캔 결과). 스캔 전이면 None."""
    seq, tag = run.get("runSeq"), run.get("runTag")
    if not tag:
        return None
    folder = f"{seq}_{tag}" if seq else tag
    path = os.path.join(DEMO_DIR, folder, "NEXT_TARGETS.json")
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def _cand_table(items: list, esc, empty: str) -> str:
    """후보 목록 표 - 크롭 많은 순으로 보여 타깃을 바로 고를 수 있게."""
    if not items:
        return f'<p class="muted">{empty}</p>'
    # 품명이 아닌 것(할인·집계 행, 표 헤더 조각)은 후보에서 뺀다.
    # 스캔 시점에도 같은 규칙이 걸리지만, 그 전에 만든 JSON 도 여기서 걸러진다.
    rows = [c for c in items if is_item_name(c.get("name") or "")]
    if not rows:
        return f'<p class="muted">{empty}</p>'
    rows.sort(key=lambda c: (-c.get("crops", 0), -c.get("rate", 0)))
    out = ['<table style="margin:6px 0 12px"><tr><th style="width:44px">#</th>'
           '<th>품명</th><th style="width:90px">크롭</th>'
           '<th style="width:110px">틀린 크롭</th><th>대표 오독</th></tr>']
    for i, c in enumerate(rows[:10], 1):
        w = " · ".join(f'"{esc(k)}" {n}' for k, n in (c.get("wrong") or [])[:2]) or "-"
        out.append(f'<tr><td class="muted">{i}</td><td><b>{esc(c["name"])}</b></td>'
                   f'<td>{c.get("crops", 0)} 크롭</td>'
                   f'<td><span class="bad">{c.get("hits", 0)}</span> '
                   f'<span class="muted">({c.get("rate", 0)}%)</span></td>'
                   f'<td class="muted">{w}</td></tr>')
    out.append("</table>")
    return "\n".join(out)


def _scan_delta(tag: str, prev_name: str) -> dict | None:
    """이 모델 스캔 vs 직전 모델 스캔 - 잃은 크롭 / 못 읽는 크롭을 비율까지.

    두 표(① 잃음 ② 못 읽음)가 각각 몇 %인지가 한 줄로 안 보이면, 표만 보고는
    "많은 건가 적은 건가"를 판단할 수 없다.
    """
    d = os.path.join(DEMO_DIR, "scans")
    cur, prev = os.path.join(d, f"{tag}.jsonl"), os.path.join(d, prev_name or "")
    if not (tag and os.path.exists(cur) and prev_name and os.path.exists(prev)):
        return None

    def _ok(path: str) -> dict[str, bool]:
        """품명이 아닌 항목(할인·집계 행, 헤더 조각)은 빼고 읽는다 - 후보 표와 같은 모집단."""
        out = {}
        for ln in open(path, encoding="utf-8"):
            ln = ln.strip()
            if not ln:
                continue
            try:
                r = json.loads(ln)
            except json.JSONDecodeError:
                continue
            if r.get("path") and is_item_name(r.get("gt") or ""):
                gt, pr = r.get("gt") or "", r.get("pred") or ""
                # (관대, 엄격) - 둘이 갈리는 게 곧 '글자는 맞는데 표기만 다른' 건이다.
                out[r["path"]] = (same_text(gt, pr), gt.strip() == pr.strip())
        return out

    a, b = _ok(prev), _ok(cur)
    keys = a.keys() & b.keys()
    if not keys:
        return None
    prev_ok = sum(1 for k in keys if a[k][0])
    lost = sum(1 for k in keys if a[k][0] and not b[k][0])
    gained = sum(1 for k in keys if not a[k][0] and b[k][0])
    unread = sum(1 for k in keys if not b[k][0])
    # 글자는 다 맞는데 공백·앞뒤 잡문자 때문에 엄격 비교로는 오답인 것 = 집계에서 뺀 몫.
    notation = sum(1 for k in keys if b[k][0] and not b[k][1])
    return {"n": len(keys), "prevOk": prev_ok, "lost": lost,
            "gained": gained, "unread": unread, "notation": notation}


def _next_block(run: dict, esc, attempts: dict | None = None) -> str:
    """다음 타깃 후보 — 이 모델이 잃은 품명 / 아직 못 읽는 품명."""
    nt = _next_targets(run)
    if not nt:
        return ""
    # ★대조 상대는 이 run 의 <시작 모델>이다. NEXT_TARGETS.json 의 prevScan 은 파일명
    #  순서로 고른 값이라, 재시도(v2·v3)에서는 형제 시도를 부모로 잡을 수 있다.
    #  체인 정보(compareStep)로 다시 구해 쓰고, 그게 없을 때만 JSON 값을 쓴다.
    prev_tag = _start_scan_tag(attempts, run) if attempts is not None else ""
    prev_name = f"{prev_tag}.jsonl" if prev_tag else (nt.get("prevScan") or "")
    d = _scan_delta(str(run.get("runTag") or ""), prev_name)
    if d:
        lost_pct = 100.0 * d["lost"] / d["prevOk"] if d["prevOk"] else 0.0
        unread_pct = 100.0 * d["unread"] / d["n"] if d["n"] else 0.0
        net = d["gained"] - d["lost"]
        summary = (
            f'<p class="big">① 잃어버림 <b>{d["lost"]:,} 크롭</b> '
            f'<span class="muted">(직전 모델이 읽던 {d["prevOk"]:,} 중 </span>'
            f'<b>{lost_pct:.1f}%</b><span class="muted">)</span> &nbsp;·&nbsp; '
            f'② 못 읽음 <b>{d["unread"]:,} 크롭</b> '
            f'<span class="muted">(전체 {d["n"]:,} 중 </span>'
            f'<b>{unread_pct:.1f}%</b><span class="muted">)</span>'
            f' &nbsp;·&nbsp; ③ 표기만 다름 <b>{d["notation"]:,} 크롭</b> '
            f'<span class="muted">(글자는 맞게 읽었으나 공백·표 테두리 차이 - '
            f'집계에서 제외)</span><br>'
            f'<span class="muted">되살린 크롭 {d["gained"]:,} - 잃은 크롭 {d["lost"]:,} = '
            f'순증 {net:+,} 크롭</span></p>')
    else:
        summary = ""
    return (
        summary +
        f'<p><b>① 이번 회차 2단계 타깃 후보</b> '
        f'<span class="muted">- 직전 모델은 읽던 품명을 이 모델이 잃었다</span></p>'
        + _cand_table(nt.get("lost") or [], esc, "잃어버린 품명이 없습니다.")
        + f'<p><b>② 다음 회차 1단계 타깃 후보</b> '
          f'<span class="muted">- 이 모델도 여전히 못 읽는 품명</span></p>'
        + _cand_table(nt.get("unread") or [], esc, "해당 품명이 없습니다."))


def _why_fail(run: dict, esc) -> str:
    """실패 run 의 근거 — 어떤 타깃이 몇 장 틀렸고 <실제로 뭐라고 읽었는지>.

    '앵커가 없어서'처럼 단정하지 않고, 오류의 종류(삽입/삭제/치환)와 학습 조건
    (앵커 수·정점 에폭)을 같이 보여줘 읽는 사람이 연결하게 한다.
    """
    c = run.get("counts") or {}
    lines = []
    for t in run.get("targets") or []:
        v = t.get("verdict") or {}
        if v.get("pass"):
            continue
        bad = [r for r in (t.get("rows") or []) if not r.get("ok")]
        lines.append(f'<b>{esc(t["name"])}</b> - 판정 {v.get("n", 0)} 크롭 중 '
                     f'<b>{len(bad)} 크롭 실패</b> (시작 모델은 {v.get("base", 0)} 크롭 정답)')
        if bad:
            items = "".join(
                f'<li>정답 <b>{esc(r["gt"])}</b> → 이 모델 '
                f'<span class="bad">{esc(r["finetuned"]) or "(빈칸)"}</span>'
                f' <span class="muted">(시작 모델: {esc(r["base"]) or "(빈칸)"})</span></li>'
                for r in bad[:6])
            lines.append(f'<ul style="margin:6px 0 10px">{items}</ul>')
    cond = []
    if c.get("targetTrainUnique") is not None:
        cond.append(f'타깃 {c["targetTrainUnique"]} 크롭')
        cond.append("앵커 없음" if not c.get("anchor") else f'앵커 {c["anchor"]:,} 크롭')
    if cond:
        lines.append(f'<p class="muted">이 실행의 학습 조건: {" · ".join(cond)}. '
                     f'타깃 글자는 고쳐졌는데 주변 글자가 삽입·삭제·치환으로 흔들린다면, '
                     f'학습 신호가 타깃 하나로 쏠려 글자/공백 판정 기준이 함께 밀린 것이다 '
                     f'— 앵커(타깃과 무관한 정답 크롭)를 섞으면 그 기준이 유지된다.</p>')
    return "\n".join(lines)


def _step_model_name_ko(r_no: int, step: int) -> str:
    """그 단계가 만든 모델 이름(실행번호 없이) — 계보 트리에서 중복 표기를 피한다."""
    return f"{ORD[r_no - 1]} 결과 모델" if step == 2 else f"{ORD[r_no - 1]} 1단계 모델"


def _lineage(attempts: dict[tuple[int, int], list[dict]], esc) -> str:
    """모델 계보 트리 — base 에서 시작해 통과한 단계만 줄기로 이어진다.

    실패 시도는 같은 자리에서 갈라진 가지(✗)로 표시하고 줄기를 잇지 않는다
    (run-finetune 이 통과본만 demo/models/step<N>/ 에 보관하기 때문).
    마지막 통과본이 곧 '현재 모델' = 다음 단계의 시작점.
    """
    keys = sorted(attempts)
    if not keys:
        return ""
    hist = _run_history_index()      # 에폭·정점은 여기(계보)에만 적는다
    max_n = max(_step_index(*k) for k in keys)
    rows = ['<b>base</b> <span class="muted">(official pretrained · 파인튜닝 없음)</span>']
    depth, current, _cur_tag = 0, None, ""
    for n in range(1, max_n + 1):
        r_no, st = (n + 1) // 2, (1 if n % 2 else 2)
        lst = attempts.get((r_no, st)) or []
        for i, run in enumerate(lst):
            sm = run.get("summary") or {}
            ok = sm.get("allPass")
            tgt = next((t["name"] for t in run.get("targets") or [] if t.get("isNew")), "-")
            pad = "&nbsp;" * (depth * 4)
            mark = ('<span class="ok">★</span>' if ok else '<span class="bad">✗</span>')
            # 실행번호를 단계 라벨 바로 뒤에 둔다 — 폴더(demo/<실행번호>/)를 바로 찾게.
            head = (f'<b>{_sub_label(r_no, st, i)}</b> '
                    f'<span class="muted">[{esc(_run_id(run))}]</span>')
            # 통과한 것만 결과 모델 이름이 생긴다(체인에 들어간 모델).
            made = ""   # 라벨 자체가 모델 이름이므로 '→ …모델' 중복 표기는 생략
            note = "" if ok else ' <span class="muted">(체인 미반영 - 시작 모델 그대로)</span>'
            h = hist.get(str(run.get("runTag") or ""), {})
            ep = ""
            if h.get("epochsCompleted"):
                ep = f' · ep {h["epochsCompleted"]}'
                if h.get("bestEpoch"):
                    ep += f' (best {h["bestEpoch"]})'
            rows.append(f'{pad}└ {mark} {head}{made} '
                        f'<span class="muted">· 타깃 +{esc(tgt)} · '
                        f'판정 {sm.get("pass", 0)}/{sm.get("total", 0)}{ep}</span>{note}')
            if ok:
                current = (run, r_no, st)
                _cur_tag = _sub_label(r_no, st, i)
        if any((x.get("summary") or {}).get("allPass") for x in lst):
            depth += 1        # 통과했을 때만 줄기가 한 칸 내려간다
    if current:
        run, r_no, st = current
        sm = run.get("summary") or {}
        rows.append(f'<p class="big" style="margin-top:14px">현재 모델 = '
                    f'<b>{_cur_tag}</b> '
                    f'<span class="muted">[{esc(_run_id(run))}] · 누적 '
                    f'{sm.get("pass", 0)}개 품명을 읽음 · 보관 '
                    f'<code>demo/models/step{_step_index(r_no, st)}/</code></span></p>')
    else:
        rows.append('<p class="big" style="margin-top:14px">현재 모델 = <b>base</b> '
                    '<span class="muted">(아직 통과한 단계가 없어 체인이 비어 있음)</span></p>')
    body = "<br>".join(rows[:-1]) + rows[-1]
    return ('<h3>모델 계보</h3>'
            '<div class="box" style="font-family:Consolas,monospace;font-size:13px;'
            'line-height:1.9">' + body + '</div>'
            '<p class="muted">★ = 판정 통과(체인에 반영) · ✗ = 실패(같은 자리에서 재시도). '
            '단계마다 바로 앞 모델 위에서 학습하므로 줄기가 한 줄로 이어진다.</p>')


def _final_run(runs: dict, r_no: int) -> dict | None:
    """그 회차의 최종 모델 = 2단계 run(없으면 1단계)."""
    return runs.get((r_no, 2)) or runs.get((r_no, 1))


def _model_name(r_no: int, step: int, run: dict, esc) -> str:
    """그 단계가 만들어낸 파인튜닝 모델 이름 + 실행번호.

    2단계 산출물은 그 회차의 결과 모델 = 다음 회차의 시작 모델
    (run-finetune 이 demo/models/round<N>/ 에 보관).
    """
    name = (f"{ORD[r_no - 1]} 결과 모델" if step == 2 else f"{ORD[r_no - 1]} 1단계 모델")
    tag = esc(_run_id(run))
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


def _overview(runs: dict, rounds: int, esc, attempts: dict | None = None) -> str:
    """전체 탭 - 시도(파인튜닝 1회)를 행으로, 누적 품명을 열로 둔 판정 표.

    회차 단위로 합치지 않는다: 실패한 시도도 그 자리에 한 줄로 남아야
    "무엇을 몇 번 만에 통과시켰는지"와 "그때 다른 품명은 어땠는지"가 같이 보인다.
    """
    attempts = attempts or {}
    p: list[str] = []

    # 행 = 시도(시간순), 열 = 그때까지 등장한 품명 전부
    rows = []
    for (r_no, st), lst in attempts.items():
        for i, run in enumerate(lst):
            rows.append((run.get("generatedAt") or "", r_no, st, i, run))
    rows.sort()
    if not rows:
        return "\n".join(p)

    names: list[str] = []
    for _, _, _, _, run in rows:
        for t in run.get("targets") or []:
            if t["name"] not in names:
                names.append(t["name"])
    # ★자리 미리 확보 — 최종적으로 품명 8개(4회차×2)가 들어온다. 아직 안 정해진 칸은
    #   회차·단계 번호만 적어 비워 둔다(표 폭이 중간에 바뀌지 않게).
    n_slots = rounds * 2
    slots = list(names) + [None] * max(0, n_slots - len(names))

    p.append('<table><tr><th style="width:56px">회차</th>'
             '<th style="width:66px">단계</th><th style="width:56px">버전</th>'
             '<th style="width:110px">시작 모델</th>'
             + "".join(
                 f'<th>{esc(n)}</th>' if n else
                 f'<th class="muted" style="font-weight:400">'
                 f'{(k // 2) + 1}-{(k % 2) + 1} <span style="font-size:11.5px">예정</span></th>'
                 for k, n in enumerate(slots))
             + '<th style="width:80px">결과</th></tr>')
    for _, r_no, st, i, run in rows:
        sm = run.get("summary") or {}
        ok = sm.get("allPass")
        cells = []
        for nm in slots:
            if nm is None:
                cells.append('<td class="muted"></td>')
                continue
            t = next((x for x in run.get("targets") or [] if x["name"] == nm), None)
            if not t:
                cells.append('<td class="muted">-</td>')
                continue
            v = t.get("verdict") or {}
            mark = ('<span class="ok">성공</span>' if v.get("pass")
                    else '<span class="bad">실패</span>')
            new = ' <span class="muted">(신규)</span>' if t.get("isNew") else ""
            cells.append(f'<td>{mark} <span class="muted">{v.get("ft", 0)}/'
                         f'{v.get("n", 0)}</span>{new}</td>')
        badge = ('<span class="badge pass">성공</span>' if ok
                 else '<span class="badge fail">실패</span>')
        n_idx = _step_index(r_no, st)
        p.append(f'<tr><td><b>{ORD[r_no - 1]}</b></td>'
                 f'<td><b>{st}단계</b></td>'
                 f'<td><b>v{i + 1}</b></td>'
                 f'<td class="muted nw">{esc(_passing_tag(attempts, n_idx - 1) or "base")}</td>'
                 f'{"".join(cells)}<td>{badge}</td></tr>')
    p.append('</table><p class="muted">"-" = 그 시도에서는 아직 타깃이 아니었음. '
             '(신규) = 그 시도에서 새로 추가된 타깃.</p>')
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
th,td{{border:1px solid #d7dee5;padding:6px 8px;font-size:13px;text-align:left;vertical-align:middle}}
th{{background:#f2f6fa;white-space:nowrap}}
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
.nw{{white-space:nowrap}}
details>summary::-webkit-details-marker{{display:none}}
details>summary.big{{padding:7px 10px;background:#f7fafd;border:1px solid #e3eaf1;
 border-radius:7px;user-select:none}}
details>summary.big:hover{{background:#eef4fa}}
details>summary.big::before{{content:"\\25B8 ";color:#5b6b7b;font-weight:700}}
details[open]>summary.big::before{{content:"\\25BE "}}
details[open]>summary.big{{border-radius:7px 7px 0 0;margin-bottom:-1px}}
.tabs{{display:flex;flex-wrap:wrap;gap:4px;border-bottom:2px solid #dde5ec;margin:18px 0 4px}}
.tabs button{{border:1px solid #dde5ec;border-bottom:none;background:#f2f6fa;color:#37485a;
 padding:8px 20px;font-size:14px;font-weight:600;cursor:pointer;border-radius:8px 8px 0 0}}
.tabs button.on{{background:#fff;color:#0b63ce;border-color:#b9d3ef;box-shadow:0 2px 0 #fff}}
.tabs button:disabled{{color:#9aa8b5;cursor:default}}
.tabs.sub{{margin:14px 0 2px;border-bottom-width:1px}}
.tabs.sub button{{padding:6px 14px;font-size:13px}}
.pane{{display:none}} .pane.on{{display:block}}
</style></head><body>
<h1>파인튜닝</h1>
<div class="tabs">"""]
    # 탭 = 실행 이력(기본) · 전체(누적·채택) · 1차~N차(회차 상세)
    panes: list[tuple[str, str, bool]] = [
        ("실행 이력", _history(attempts, esc), True),
        ("전체", _overview(runs, rounds, esc, attempts), True),
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
