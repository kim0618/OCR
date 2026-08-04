"""demo_report — 소생 데모 사이클 전용, "처음 보는 사람용" 판정 리포트.

벤치/본판 리포트는 전문가용 집계라 맥락 설명이 없다. 이 리포트는 회사 리뷰에서
그 자체로 읽히도록, 아래를 전부 한 페이지에 담는다:
  - 무엇을 증명하는 실험인지(소생 사이클 설명, 판정 기준)
  - 기준 데이터가 무엇인지(9,001장 held-out 문서 리플레이, 품명(itemName) 컬럼)
  - 타깃 품명을 왜 골랐는지(출현/문서 수, base 전 출현 오독, 대표 오독 문자열)
  - 판정: 학습에 안 쓴 같은 품명 크롭(이미지째)을 base vs 파인튜닝이 읽은 결과
  - 누적 현황: 사이클별 살린 품명이 이번 버전에서도 유지되는지

재료(모두 기존 산출물 — 추가 GPU 작업 없음):
  dataset/manifest.json           build_demo_dataset 이 남긴 타깃/크롭 수
  FINETUNE_PREDICTIONS.jsonl      [6/6] finetune_report 가 남긴 판정셋 크롭별 base/FT 예측
  eval/runs/<최신 NNN_*>/compare  타깃 선정 근거(기준셋 전수 통계) — --replay-run 으로 지정 가능

출력: eval/finetune/demo/<실행번호>/DEMO_REPORT_<실행번호>.html (+ demo/DEMO_REPORT.html 최신본)

run-finetune.sh --round=demo 의 마지막에 자동 실행.
    python eval/demo_report.py --run-tag 260803_1200
    python eval/demo_report.py --run-tag 260803_1200 --replay-run eval/runs/072_20260802_182127
"""
from __future__ import annotations

import argparse
import base64
import glob
import html
import json
import os
import re
import sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from finetune_ledger import CORPUS_DIR  # noqa: E402
from finetune_report import _report_id, _write_text, \
    PREDICTIONS_JSONL, BASE_MODEL  # noqa: E402

MANIFEST = os.path.join(CORPUS_DIR, "dataset", "manifest.json")
RUNS_DIR = os.path.join(HERE, "runs")
# 데모 산출물은 벤치/본판 리포트(reports/)와 섞지 않고 finetune/demo/ 아래로 모은다.
#   demo/<실행번호>/DEMO_REPORT_<실행번호>.html   run 별 보존(폴더째 scp 반출)
#   demo/DEMO_REPORT.html                        최신본 포인터
#   demo/samples/                                실행 전 미리보기 샘플
DEMO_DIR = os.path.join(HERE, "finetune", "demo")
LATEST_OUT = os.path.join(DEMO_DIR, "DEMO_REPORT.html")


def _demo_run_dir(run_tag: str) -> str:
    """run별 산출물 폴더 `demo/NNN_<tag>/` — reports 폴더와 같은 순번 규약.

    같은 run 에서 리포트/스캔이 따로 실행돼도 한 폴더를 쓰도록, 이미 이 태그로
    만든 폴더가 있으면 재사용하고 없을 때만 다음 순번(NNN)을 새로 딴다.
    """
    os.makedirs(DEMO_DIR, exist_ok=True)
    existing = os.listdir(DEMO_DIR)
    for name in sorted(existing):
        if re.fullmatch(r"\d{3}_" + re.escape(run_tag), name):
            d = os.path.join(DEMO_DIR, name)
            break
    else:
        nums = [int(m.group(1)) for n in existing if (m := re.match(r"(\d{3})_", n))]
        d = os.path.join(DEMO_DIR, f"{max(nums, default=0) + 1:03d}_{run_tag}")
    os.makedirs(d, exist_ok=True)
    return d


def _latest_replay_run() -> str | None:
    """eval/runs/ 의 최신 기준셋 리플레이(NNN_* 폴더, compare/ 보유)를 자동 선택."""
    cands = sorted(glob.glob(os.path.join(RUNS_DIR, "[0-9][0-9][0-9]_*")))
    for d in reversed(cands):
        if os.path.isdir(os.path.join(d, "compare")):
            return d
    return None


def _selection_stats(replay_dir: str, targets: list[str]) -> dict:
    """기준셋 compare 전수에서 타깃별 출현/문서/정답/대표오독 집계 (선정 근거).

    ★두 범위를 따로 센다 — 하나로 뭉치면 모수가 부풀려진다:
      exact  GT 가 그 품명과 정확히 같은 셀       = 그 품명 자체의 모수
      total  그 품명을 포함하는 셀(변형 포함)     = 학습 크롭 수집 규칙과 같은 범위
             예) "세파클러캡슐250mg" 정확일치 24셀 vs 변형 포함 131셀
             ("씨엠지제약세파클러캡슐250mg 30캡슐" 처럼 회사명·수량 꼬리가 붙은 것)
    """
    keys = {t: t.replace(" ", "") for t in targets}
    st = {t: {"total": 0, "exact": 0, "docs": set(), "exactDocs": set(),
              "match": 0, "exactMatch": 0, "wrong": {}} for t in targets}
    files = glob.glob(os.path.join(replay_dir, "compare", "*.json"))
    for fp in files:
        try:
            with open(fp, encoding="utf-8") as f:
                j = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        doc = j.get("sourceFile", os.path.basename(fp))
        for r in (j.get("table") or {}).get("rows") or []:
            c = (r.get("cells") or {}).get("itemName")
            if not c:
                continue
            flat = (c.get("gtNorm") or c.get("gt") or "").replace(" ", "")
            for t in targets:
                if keys[t] not in flat:
                    continue
                s = st[t]
                is_exact = flat == keys[t]
                ok = c.get("status") == "match"
                s["total"] += 1
                s["docs"].add(doc)
                if ok:
                    s["match"] += 1
                if is_exact:
                    s["exact"] += 1
                    s["exactDocs"].add(doc)
                    if ok:
                        s["exactMatch"] += 1
                if not ok:
                    ext = (c.get("ext") or "").strip() or "(빈칸)"
                    s["wrong"][ext] = s["wrong"].get(ext, 0) + 1
                break
    return {"nDocs": len(files), "byTarget": st}


def _img_b64(rel_path: str) -> str | None:
    """크롭을 base64 로 — HTML 에 박고, 요약(demo_summary)이 재사용하도록 JSON 에도 싣는다."""
    try:
        with open(os.path.join(CORPUS_DIR, rel_path), "rb") as f:
            return base64.b64encode(f.read()).decode("ascii")
    except OSError:
        return None


def _img_tag(rel_path: str, b64: str | None = None) -> str:
    b64 = b64 if b64 is not None else _img_b64(rel_path)
    if not b64:
        return html.escape(rel_path)
    return f'<img src="data:image/jpeg;base64,{b64}" style="max-height:34px">'


def _step_model_name(n: int) -> str:
    """통산 N번째 단계 모델의 사람 이름. n=1 → '1차 1단계 모델'."""
    return f"{(n + 1) // 2}차 {1 if n % 2 else 2}단계 모델"


def _predict_pairs(compare_dir: str | None) -> list[dict] | None:
    """판정셋(test.txt)을 <비교 모델> 과 <이번 파인튜닝 모델> 로 각각 판독.

    ★회차 체인: 비교 모델은 그 회차의 <b>시작 모델</b>이다.
      1회차 = official base / 2회차 이상 = 직전 회차 결과 모델(compare_dir).
    판정셋은 타깃 홀드아웃 몇 장뿐이라 GPU 부담이 없다. paddlex 가 없는 환경
    (로컬 미리보기 등)에서는 None 을 돌려주고 호출부가 예측 파일로 폴백한다.
    """
    test_list = os.path.join(CORPUS_DIR, "test.txt")
    if not os.path.exists(test_list):
        return None
    rows = []
    for ln in open(test_list, encoding="utf-8"):
        ln = ln.rstrip("\n")
        if ln and "\t" in ln:
            rel, gt = ln.split("\t", 1)
            rows.append((rel, gt))
    if not rows:
        return None
    try:
        try:
            from paddlex import create_model
        except ImportError:
            from paddlex.inference import create_model  # type: ignore
        from finetune_report import find_ft_inference, predict_all
    except ImportError:
        return None
    ft_dir = find_ft_inference()
    if not ft_dir:
        return None
    paths = [os.path.join(CORPUS_DIR, rel) for rel, _ in rows]
    cmp_model = (create_model(BASE_MODEL, compare_dir) if compare_dir
                 else create_model(BASE_MODEL))
    cmp_pred = predict_all(cmp_model, paths)
    ft_pred = predict_all(create_model(BASE_MODEL, ft_dir), paths)
    return [{"path": rel, "gt": gt, "base": b, "finetuned": f}
            for (rel, gt), b, f in zip(rows, cmp_pred, ft_pred)]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-tag", dest="run_tag", help="실행번호(리포트 폴더 공유)")
    ap.add_argument("--replay-run", default=None,
                    help="타깃 선정 근거로 쓸 기준셋 리플레이 폴더(기본: eval/runs 최신)")
    ap.add_argument("--compare-dir", default=None,
                    help="이 회차의 시작 모델 inference 디렉터리(2회차 이상 = 직전 회차 모델). "
                         "미지정 = official base")
    ap.add_argument("--compare-step", type=int, default=0,
                    help="시작 모델이 통산 몇 번째 단계 모델인지(2번째 단계 이상). 표 이름에 쓴다")
    ap.add_argument("--compare-label", default=None,
                    help="표에 쓸 시작 모델 이름(기본: base 또는 'N차 M단계 모델')")
    args = ap.parse_args()
    run_tag = _report_id(args.run_tag)
    cmp_label = args.compare_label or (
        _step_model_name(args.compare_step) if args.compare_step
        else ("직전 단계 모델" if args.compare_dir else "base"))

    if not os.path.exists(MANIFEST):
        raise SystemExit(f"manifest 없음: {MANIFEST} — build_demo_dataset.py 먼저")
    mf = json.load(open(MANIFEST, encoding="utf-8"))
    if mf.get("mode") != "demo":
        raise SystemExit("manifest 가 demo 모드가 아님 — --round=demo 로 빌드한 학습셋이 아님")
    targets: list[str] = mf["targets"]
    keys = {t: t.replace(" ", "") for t in targets}

    # 판정셋 판독: 이 회차의 시작 모델 vs 이번 파인튜닝 모델(직접 추론).
    # paddlex 가 없으면 [6/6] 이 남긴 예측 파일로 폴백(비교 = official base).
    preds = _predict_pairs(args.compare_dir)
    if preds is None:
        if not os.path.exists(PREDICTIONS_JSONL):
            raise SystemExit(f"예측 파일 없음: {PREDICTIONS_JSONL} — [6/6] finetune_report 먼저")
        if args.compare_dir:
            print("[demo-report] ★경고: 직접 추론 불가 → 예측 파일 폴백. "
                  "비교 모델이 official base 로 기록됨(직전 회차 모델 아님)")
            cmp_label = "base"
        preds = [json.loads(ln) for ln in open(PREDICTIONS_JSONL, encoding="utf-8") if ln.strip()]

    # 크롭별 판정을 타깃별로 그룹 (demo 의 test.txt = 타깃 홀드아웃 전부)
    by_target: dict[str, list] = {t: [] for t in targets}
    for e in preds:
        flat = (e.get("gt") or "").replace(" ", "")
        for t in targets:
            if keys[t] in flat:
                by_target[t].append(e)
                break

    replay_dir = args.replay_run or _latest_replay_run()
    sel = _selection_stats(replay_dir, targets) if replay_dir else None

    # ---- 타깃별 판정 ----
    verdicts = {}
    for t in targets:
        rows = by_target[t]
        n = len(rows)
        ft_ok = sum((e["finetuned"] or "").strip() == (e["gt"] or "").strip() for e in rows)
        b_ok = sum((e["base"] or "").strip() == (e["gt"] or "").strip() for e in rows)
        verdicts[t] = {"n": n, "ft": ft_ok, "base": b_ok,
                       "pass": n > 0 and ft_ok == n}
    all_pass = all(v["pass"] for v in verdicts.values())

    esc = html.escape
    cyc = len(targets)
    # ★한 회차 = 품명 2개 = 파인튜닝 2번.
    #   1단계 = base 가 못 읽던 품명 1개를 살린다.
    #   2단계 = 그 파인튜닝이 새로 잃어버린 품명 1개를 추가해, 둘 다 읽게 만든다.
    # 누적 타깃 수 n 이 홀수면 1단계 진행 중, 짝수면 그 회차 완료(누적 성공 n 개).
    round_no = (cyc + 1) // 2
    step = 1 if cyc % 2 else 2
    step_label = f"{round_no}차 {step}단계"
    parts: list[str] = []
    parts.append(f"""<!doctype html><html lang="ko"><head><meta charset="utf-8">
<title>파인튜닝 {esc(run_tag)}</title>
<meta name="viewport" content="width=device-width, initial-scale=1"><style>
*{{box-sizing:border-box}}
body{{font-family:'Segoe UI',Malgun Gothic,sans-serif;margin:0;padding:20px 28px;
 max-width:none;color:#1a2733}}
h1{{font-size:22px}} h2{{font-size:17px;margin-top:30px;border-bottom:2px solid #dde5ec;padding-bottom:6px}}
.tw{{overflow-x:auto;-webkit-overflow-scrolling:touch}}
table{{border-collapse:collapse;width:100%;margin:10px 0;min-width:640px}}
th,td{{border:1px solid #d7dee5;padding:6px 10px;font-size:13.5px;text-align:left;vertical-align:middle}}
th{{background:#f2f6fa}}
@media (max-width:820px){{
 body{{padding:14px 12px}}
 th,td{{padding:5px 7px;font-size:12.5px}}
}}
.box{{background:#f6f9fc;border:1px solid #d7dee5;border-radius:8px;padding:14px 18px;margin:14px 0;font-size:14px;line-height:1.65}}
.ok{{color:#0a7a3d;font-weight:700}} .bad{{color:#c0392b;font-weight:700}}
.badge{{display:inline-block;padding:2px 10px;border-radius:12px;font-size:12.5px;font-weight:700}}
.badge.pass{{background:#e3f6ea;color:#0a7a3d}} .badge.fail{{background:#fdeceb;color:#c0392b}}
.muted{{color:#5b6b7b;font-size:12.5px}} .big{{font-size:16px}}
</style></head><body>
<h1>파인튜닝 <span class="muted">- {step_label} · 실행번호 {esc(run_tag)} · {datetime.now().strftime('%Y-%m-%d %H:%M')}</span></h1>
""")

    # ---- 기준 정보 ----
    c = mf.get("counts", {})
    n_docs = f"{sel['nDocs']:,}장" if sel else "(리플레이 폴더 없음)"
    parts.append(f"""<h2>기준 정보</h2><table>
<tr><th style="width:30%">기준 문서셋</th><td>거래명세서 {n_docs} — held-out 리플레이 기준셋
 (모델 학습에 절대 쓰지 않는 측정 전용 문서. 타깃 선정과 "못 읽는다"의 근거)</td></tr>
<tr><th>대상 컬럼</th><td>품목표의 <b>품명 (itemName)</b></td></tr>
<tr><th>시작 모델 (이번 학습의 출발점)</th><td><b>{esc(cmp_label)}</b>
 {'(바로 앞 단계 모델 위에서 이어 학습 - 모델은 한 줄로 이어진다)' if args.compare_dir
   else '(official, 현 서비스 기준선 - 파인튜닝 없음)'}</td></tr>
<tr><th>이번 단계 결과 모델</th><td><b>{esc(_step_model_name(cyc))}</b>
 (통산 {cyc}번째 · 다음 단계의 시작 모델)</td></tr>
<tr><th>학습 데이터</th><td>{
 f"타깃 품명 크롭 <b>{c['targetTrainUnique']}</b>장(코퍼스, 기준셋과 다른 문서)"
 + (f" ×복제 {c.get('oversampledTo', 0):,}줄"
    if (c.get('oversampledTo') or 0) > (c.get('targetTrainUnique') or 0) else " (복제 없음)")
 + (f" + 일반 정답 크롭 앵커 {c['anchor']:,}장" if c.get('anchor') else " · 앵커 없음")
 if c.get('targetTrainUnique') is not None else
 '<span class="muted">미측정 - 코퍼스 집계(demo_corpus_count.py) 후 확정</span>'}</td></tr>
<tr><th>판정 데이터</th><td>학습에서 제외한 같은 품명 크롭 <b>{c.get('test', '?')}장</b> (held-out)</td></tr>
<tr><th>판정 기준</th><td>held-out 크롭을 시작 모델과 파인튜닝 모델이 각각 읽음 —
 <b>시작 모델 0% → 파인튜닝 전부 정답이면 "성공"</b></td></tr>
</table>""")

    # ---- 타깃별 섹션 (+ 요약 리포트가 재사용할 JSON 동시 구성) ----
    j_targets: list[dict] = []
    for i, t in enumerate(targets, 1):
        v = verdicts[t]
        i_round, i_step = (i + 1) // 2, (1 if i % 2 else 2)
        if i == cyc:
            role = ("이번 단계 타깃 - 시작 모델이 못 읽던 품명" if i_step == 1
                    else "이번 단계 타깃 - 직전 단계 모델이 잃어버린 품명")
        else:
            role = f"{i_round}차 {i_step}단계에서 살린 품명 - 유지 확인"
        badge = ('<span class="badge pass">성공</span>' if v["pass"]
                 else '<span class="badge fail">실패</span>')
        parts.append(f'<h2>[{i}/{cyc}] {esc(t)} <span class="muted">({role})</span> {badge}</h2>')
        pool = (mf.get("poolByTarget") or {}).get(t) or {}
        if pool.get("correct"):
            parts.append(f'<p class="muted">이 품명의 크롭 {pool.get("correct")}개는 정답 풀에서 '
                         f'가져왔습니다(원래 읽히던 품명). 정답 풀은 출처 메타가 없어 기준셋 '
                         f'격리 여부는 확인되지 않습니다 — 판정 크롭이 학습에서 제외된 것은 동일합니다.</p>')
        j_sel = None
        if sel:
            s = sel["byTarget"][t]
            j_sel = {"exact": s["exact"], "exactDocs": len(s["exactDocs"]),
                     "exactMatch": s["exactMatch"],
                     "total": s["total"], "docs": len(s["docs"]), "match": s["match"],
                     "wrong": sorted(s["wrong"].items(), key=lambda x: -x[1])[:3]}
            wrong = j_sel["wrong"]
            wrong_s = " · ".join(f"“{esc(w)}” {n}회" for w, n in wrong) or "-"
            if not s["exact"] and not s["total"]:
                why = "기준셋에 미출현 - 학습 코퍼스/벤치 회귀 사례에서 선정"
            elif s["exactMatch"] == 0 and s["exact"]:
                why = "base 가 <b>전 출현 오독</b> - 원래 한 번도 못 읽던 품명"
            elif s["exact"]:
                rate = 100.0 * s["exactMatch"] / s["exact"]
                why = (f"base 정답률 <b>{rate:.0f}%</b>({s['exactMatch']}/{s['exact']}) - "
                       f"불안정하게 읽던 품명")
            else:
                why = "이 품명은 변형 형태로만 기준셋에 나타남"
            variants = ""
            if s["total"] > s["exact"]:
                variants = (f'<br><span class="muted">회사명·수량 꼬리가 붙은 변형까지 포함하면 '
                            f'{s["total"]}셀 / {len(s["docs"])}문서 (base 정답 {s["match"]}). '
                            f'학습 크롭은 이 변형까지 모읍니다.</span>')
            parts.append(f"""<div class="box">선정 근거 - {why}.<br>
기준셋 {sel['nDocs']:,}장 중 <b>{s['exact']}셀({len(s['exactDocs'])}개 문서),
base 정답 {s['exactMatch']}셀</b>. 대표 오독: {wrong_s}{variants}</div>""")
        parts.append(f"""<table><tr><th style="width:220px">크롭 (판정용 held-out)</th>
<th>정답</th><th>{esc(cmp_label)} 읽음</th><th>파인튜닝 읽음</th>
<th style="width:70px">판정</th></tr>""")
        j_rows = []
        for e in by_target[t]:
            gt, b, f_ = e["gt"].strip(), (e["base"] or "").strip(), (e["finetuned"] or "").strip()
            f_ok = f_ == gt
            b_cls = "ok" if b == gt else "bad"
            f_cls = "ok" if f_ok else "bad"
            mark = '<span class="ok">성공</span>' if f_ok else '<span class="bad">실패</span>'
            b64 = _img_b64(e["path"])
            parts.append(f"<tr><td>{_img_tag(e['path'], b64)}</td><td><b>{esc(gt)}</b></td>"
                         f"<td class='{b_cls}'>{esc(b) or '(빈칸)'}</td>"
                         f"<td class='{f_cls}'>{esc(f_) or '(빈칸)'}</td><td>{mark}</td></tr>")
            j_rows.append({"gt": gt, "base": b, "finetuned": f_, "ok": f_ok, "imgB64": b64})
        parts.append(f"</table><p class='muted'>{esc(cmp_label)} {v['base']}/{v['n']} 정답 → "
                     f"파인튜닝 <b>{v['ft']}/{v['n']}</b> 정답</p>")
        j_targets.append({"name": t, "role": role, "isNew": i == cyc,
                          "introducedRound": i_round, "introducedStep": i_step,
                          "selection": j_sel, "verdict": v, "rows": j_rows})

    # ---- 누적 요약 ----
    n_pass = sum(1 for v in verdicts.values() if v["pass"])
    overall = ('<span class="badge pass big">전체 판정: 성공</span>' if all_pass
               else '<span class="badge fail big">전체 판정: 실패 (레시피 조정 후 재실행)</span>')
    parts.append(f"<h2>누적 현황</h2><table><tr><th>회차·단계</th><th>품명</th>"
                 f"<th>이번 모델 판정</th></tr>")
    for i, t in enumerate(targets, 1):
        v = verdicts[t]
        st = ('<span class="ok">성공 (유지)</span>' if v["pass"] and i < cyc
              else '<span class="ok">성공 (소생)</span>' if v["pass"]
              else '<span class="bad">실패</span>')
        parts.append(f"<tr><td>{(i + 1) // 2}차 {1 if i % 2 else 2}단계</td>"
                     f"<td><b>{esc(t)}</b></td><td>{st} — {v['ft']}/{v['n']}</td></tr>")
    parts.append(f"</table><p class='big'>누적 성공 <b>{n_pass}개</b> / 시도 {cyc}개 &nbsp; {overall}</p>")
    nxt = ("다음 단계(2단계): 이번 파인튜닝으로 새로 틀리게 된 품명(벤치 리포트의 회귀 사례)에서"
           " 대표 1개를 골라 --targets 에 추가하면 이번 회차가 완료된다."
           if step == 1 else
           f"{round_no}차 완료(누적 {cyc}개). 다음 회차(1단계): 이번 모델이 못 읽는 품명 1개를"
           " 새로 골라 --targets 에 추가해 반복한다.")
    parts.append(f'<p class="muted">{nxt}</p></body></html>')

    out_dir = _demo_run_dir(run_tag)
    out = os.path.join(out_dir, f"DEMO_REPORT_{run_tag}.html")
    # 대시는 하이픈으로 통일(사용자 요청). base64 는 영향 없음.
    # 표는 스크롤 컨테이너로 감싼다(좁은 화면에서 본문이 밀리지 않도록).
    doc = ("\n".join(parts).replace("—", "-")
           .replace("<table>", '<div class="tw"><table>')
           .replace("</table>", "</table></div>"))
    _write_text(out, doc)
    _write_text(LATEST_OUT, doc)
    # 요약 리포트(demo_summary)가 차수 탭을 만들 때 읽는 원장. HTML 과 같은 폴더.
    payload = {
        "schemaVersion": "demo-report.v1",
        "runTag": run_tag,
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "cycle": cyc,          # 누적 타깃 수 (= 통산 단계 번호 = 누적 성공 목표치)
        "roundNo": round_no,   # 회차 (품명 2개 = 1회차)
        "step": step,          # 1 = 소생, 2 = 잃은 것 회수(회차 완료)
        "stepIndex": cyc,      # 통산 몇 번째 모델인지 (체인 위치, 1..8)
        "modelName": _step_model_name(cyc),
        "baseModel": BASE_MODEL,
        "compareLabel": cmp_label,          # 시작 모델 = 바로 앞 단계 모델
        "compareStep": args.compare_step or None,
        "compareDir": args.compare_dir,     # None = official base(1번째 단계)
        "basisDocs": sel["nDocs"] if sel else None,
        "column": "itemName",
        "counts": mf.get("counts", {}),
        "pool": mf.get("pool", {}),
        "targets": j_targets,
        "summary": {"pass": n_pass, "total": cyc, "allPass": all_pass},
    }
    _write_text(os.path.join(out_dir, f"DEMO_REPORT_{run_tag}.json"),
                json.dumps(payload, ensure_ascii=False, indent=2))
    print(f"[demo-report] {out}")
    for t in targets:
        v = verdicts[t]
        print(f"[demo-report]   {t}: base {v['base']}/{v['n']} → FT {v['ft']}/{v['n']} "
              f"{'PASS' if v['pass'] else 'FAIL'}")
    print(f"[demo-report] {step_label} · 누적 성공 {n_pass}/{cyc} — "
          f"{'PASS' if all_pass else 'FAIL'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
