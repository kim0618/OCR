"""finetune_report — "인식이 좋아졌나"를 직접 보여주는 self-contained HTML.

파서·룰·end-to-end eval 을 안 섞고, RECOGNITION 수준에서 직접 비교한다:
  base 모델(서버가 쓰는 korean_PP-OCRv5_mobile_rec)과 파인튜닝 모델(export 된 inference)을
  held-out test 크롭(dataset test.txt)에 각각 돌려서
    - 정확 일치율(exact) / 문자 유사도(char) 를 모델별로
    - 파인튜닝이 맞히고 base 가 틀린 크롭(개선) + 그 반대(회귀) 를 크롭 이미지째
  를 하나의 HTML 로 낸다. 크롭은 base64 로 박아 넣어 로컬에서 파일만 열면 보인다.

run-finetune.sh 의 마지막 단계로 자동 실행.
출력: eval/finetune/FINETUNE_REPORT_<실행번호>.html
      eval/finetune/FINETUNE_REPORT.html (후속 도구 호환용 최신본)

    .venv/bin/python eval/finetune_report.py --run-tag 260727_1200
"""
from __future__ import annotations

import argparse
import base64
from datetime import datetime
import difflib
import glob
import html
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from finetune_ledger import CORPUS_DIR  # noqa: E402

BASE_MODEL = "korean_PP-OCRv5_mobile_rec"
TEST_LIST = os.path.join(CORPUS_DIR, "test.txt")
OUT = os.path.join(HERE, "finetune", "FINETUNE_REPORT.html")
OUT_JSON = os.path.join(HERE, "finetune", "FINETUNE_REPORT.json")
PREDICTIONS_JSONL = os.path.join(HERE, "finetune", "FINETUNE_PREDICTIONS.jsonl")
MAX_EXAMPLES = 0           # 0=개선/회귀 전체 표시, 양수=해당 건수까지만
SCROLL_AFTER = 20          # 이 행 이후는 같은 표 안에서 세로 스크롤

# 컬럼별 변화 표에 병기할 한글 이름 (원본 컬럼 id → 한글)
KO_COLS = {
    "itemName": "품명", "itemNameMaster": "품명(마스터)", "spec": "규격",
    "quantity": "수량", "unitPrice": "단가", "amount": "금액",
    "supplyAmount": "공급가액", "taxAmount": "세액", "totalAmount": "합계금액",
    "discountAmount": "할인금액", "itemCode": "품목코드", "insuranceCode": "보험코드",
    "expiryDate": "유효기한", "manufacturingNo": "제조번호", "lotNo": "LOT번호",
    "supplierCompany": "공급자상호", "supplierAddress": "공급자주소",
    "supplierBizNumber": "공급자사업자번호", "supplierRepresentative": "공급자대표",
    "buyerCompany": "구매처상호", "buyerAddress": "구매처주소",
    "buyerBizNumber": "구매처사업자번호", "issueDate": "발행일",
    "taxType": "과세구분", "documentNumber": "문서번호",
}
SPLIT_METADATA = os.path.join(CORPUS_DIR, "dataset", "split_metadata.jsonl")
HANGUL_RE = re.compile(r"[가-힣]")
DIGIT_RE = re.compile(r"[0-9]")


def _report_id(value: str | None) -> str:
    """파일명에 안전한 실행번호. 직접 실행할 때는 생성 시각을 쓴다."""
    raw = value or datetime.now().strftime("%y%m%d_%H%M%S")
    safe = re.sub(r"[^0-9A-Za-z._-]+", "_", raw).strip("._-")
    return safe or datetime.now().strftime("%y%m%d_%H%M%S")


def _numbered_paths(run_tag: str) -> tuple[str, str]:
    out_dir = os.path.dirname(OUT)
    return (
        os.path.join(out_dir, f"FINETUNE_REPORT_{run_tag}.html"),
        os.path.join(out_dir, f"FINETUNE_REPORT_{run_tag}.json"),
    )


def _write_text(path: str, content: str) -> None:
    """중간에 프로세스가 끊겨도 기존 최신본이 반쪽 파일이 되지 않게 쓴다."""
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(content)
    os.replace(tmp, path)


def _load_test_metadata() -> dict[str, dict]:
    result: dict[str, dict] = {}
    if not os.path.exists(SPLIT_METADATA):
        return result
    with open(SPLIT_METADATA, encoding="utf-8") as fh:
        for line in fh:
            try:
                rec = json.loads(line)
                if rec.get("split") == "test" and rec.get("path"):
                    result[rec["path"]] = rec
            except (json.JSONDecodeError, KeyError):
                continue
    return result


def _column_stats(rows, base_pred, ft_pred, metadata: dict[str, dict]) -> list[dict]:
    """held-out 각 크롭을 원본 컬럼별로 빠짐없이 집계한다."""
    buckets: dict[str, dict] = {}
    for (_, rel, gt), bp, fp in zip(rows, base_pred, ft_pred):
        column = metadata.get(rel, {}).get("column") or "(미분류)"
        bucket = buckets.setdefault(column, {
            "column": column, "total": 0, "baseCorrect": 0,
            "finetunedCorrect": 0, "bothCorrect": 0,
            "gains": 0, "regressions": 0,
        })
        b_ok = bp.strip() == gt.strip()
        f_ok = fp.strip() == gt.strip()
        bucket["total"] += 1
        bucket["baseCorrect"] += int(b_ok)
        bucket["finetunedCorrect"] += int(f_ok)
        bucket["bothCorrect"] += int(b_ok and f_ok)
        bucket["gains"] += int(f_ok and not b_ok)
        bucket["regressions"] += int(b_ok and not f_ok)

    result = []
    for bucket in buckets.values():
        total = bucket["total"]
        bucket["netChange"] = bucket["gains"] - bucket["regressions"]
        bucket["baseExactPct"] = 100.0 * bucket["baseCorrect"] / total
        bucket["finetunedExactPct"] = 100.0 * bucket["finetunedCorrect"] / total
        bucket["deltaPp"] = bucket["finetunedExactPct"] - bucket["baseExactPct"]
        result.append(bucket)
    return sorted(result, key=lambda item: (-item["total"], item["column"]))


def _script_stats(outcomes) -> dict[str, dict]:
    """GT 글자종류별 exact 개선/회귀. 한글+숫자 혼합 문자열은 양쪽에 포함."""
    buckets = {
        "hangul": {"label": "한글", "total": 0, "baseCorrect": 0,
                   "finetunedCorrect": 0, "gains": 0, "regressions": 0},
        "number": {"label": "숫자", "total": 0, "baseCorrect": 0,
                   "finetunedCorrect": 0, "gains": 0, "regressions": 0},
    }
    for gt, b_ok, f_ok in outcomes:
        matched = []
        if HANGUL_RE.search(gt):
            matched.append(buckets["hangul"])
        if DIGIT_RE.search(gt):
            matched.append(buckets["number"])
        for bucket in matched:
            bucket["total"] += 1
            bucket["baseCorrect"] += int(b_ok)
            bucket["finetunedCorrect"] += int(f_ok)
            bucket["gains"] += int(f_ok and not b_ok)
            bucket["regressions"] += int(b_ok and not f_ok)
    for bucket in buckets.values():
        total = bucket["total"]
        bucket["netChange"] = bucket["gains"] - bucket["regressions"]
        bucket["baseExactPct"] = 100.0 * bucket["baseCorrect"] / total if total else 0.0
        bucket["finetunedExactPct"] = (
            100.0 * bucket["finetunedCorrect"] / total if total else 0.0
        )
        bucket["deltaPp"] = bucket["finetunedExactPct"] - bucket["baseExactPct"]
    return buckets


def load_test():
    rows = []
    for ln in open(TEST_LIST, encoding="utf-8"):
        ln = ln.rstrip("\n")
        if "\t" not in ln:
            continue
        rel, gt = ln.split("\t", 1)
        p = os.path.join(CORPUS_DIR, rel)
        if os.path.isfile(p):
            rows.append((p, rel, gt))
    return rows


def find_ft_inference():
    hits = glob.glob(os.path.join(HERE, "finetune", "output", "**", "inference"), recursive=True)
    hits = [h for h in hits if os.path.isfile(os.path.join(h, "inference.yml"))]
    if not hits:
        return None
    # best_accuracy 를 최우선 (latest 는 마지막 epoch = best 가 아닐 수 있음)
    best = [h for h in hits if "best_accuracy" in h]
    return (best or hits)[0]


def predict_all(model, paths, batch=64):
    """paths -> [rec_text] (입력 순서 보존)."""
    out = []
    for i in range(0, len(paths), batch):
        for res in model.predict(paths[i:i + batch]):
            t = res.get("rec_text") if hasattr(res, "get") else res["rec_text"]
            if isinstance(t, list):
                t = t[0] if t else ""
            out.append(t or "")
    return out


def _sim(a, b):
    return difflib.SequenceMatcher(None, a, b).ratio()


def _b64(path):
    try:
        with open(path, "rb") as fh:
            return "data:image/jpeg;base64," + base64.b64encode(fh.read()).decode()
    except OSError:
        return ""


# ── 고정 벤치 (UNSEEN / SEEN / RETAIN 탭) ───────────────────────────────────
BENCH_UNSEEN = os.path.join(CORPUS_DIR, "bench_unseen.txt")
BENCH_SEEN = os.path.join(CORPUS_DIR, "bench_seen.txt")
BENCH_RETAIN = os.path.join(CORPUS_DIR, "bench_retain.txt")
BENCH_OUT = os.path.join(HERE, "finetune", "FINETUNE_REPORT.html")  # overwritten below per run-tag

# 금액계열은 학습라벨=콤마 인쇄형(819,800), 벤치GT=war 원본(819800)이라 포맷이 어긋난다.
# 문자 그대로 비교하면 배운 대로 콤마 찍은 정답이 오답 처리됨(probe1 실측: 금액 base 0.4%
# 로 보였으나 콤마무시 시 31.1%). 숫자 컬럼은 콤마·공백 무시 자릿수 비교로 채점한다.
# 짧은숫자/숫자 = retain 벤치의 글자종류 버킷(컬럼 메타 없는 정답풀)도 동일 적용.
BENCH_NUM_COLS = {"quantity", "unitPrice", "amount", "supplyAmount",
                  "taxAmount", "totalAmount", "discountAmount",
                  "짧은숫자", "숫자"}


def _bench_ok(pred: str, gt: str, col: str) -> bool:
    if col in BENCH_NUM_COLS:
        strip = lambda s: s.replace(",", "").replace(" ", "").strip()
        return strip(pred) == strip(gt)
    return pred.strip() == gt.strip()


def load_bench(path):
    """bench 파일(rel \\t gt \\t column) -> [(abspath, rel, gt, column)]. 없으면 []."""
    rows = []
    if not os.path.exists(path):
        return rows
    for ln in open(path, encoding="utf-8"):
        ln = ln.rstrip("\n")
        parts = ln.split("\t")
        if len(parts) < 2:
            continue
        rel, gt = parts[0], parts[1]
        col = parts[2] if len(parts) > 2 else "(미분류)"
        p = os.path.join(CORPUS_DIR, rel)
        if os.path.isfile(p):
            rows.append((p, rel, gt, col))
    return rows


def _bench_tab_stats(rows, base_pred, ft_pred, max_examples):
    """한 탭(seen/unseen)의 집계 + 컬럼 분해 + 개선/회귀 예시."""
    buckets = {}
    gains, regress = [], []
    outcomes = []
    base_ok = ft_ok = both_ok = 0
    for (p, _rel, gt, col), bp, fp in zip(rows, base_pred, ft_pred):
        b_ok = _bench_ok(bp, gt, col)
        f_ok = _bench_ok(fp, gt, col)
        base_ok += b_ok
        ft_ok += f_ok
        both_ok += b_ok and f_ok
        outcomes.append((gt, b_ok, f_ok))
        bk = buckets.setdefault(col, {"column": col, "total": 0, "baseCorrect": 0,
                                      "finetunedCorrect": 0, "bothCorrect": 0,
                                      "gains": 0, "regressions": 0})
        bk["total"] += 1
        bk["baseCorrect"] += int(b_ok)
        bk["finetunedCorrect"] += int(f_ok)
        bk["bothCorrect"] += int(b_ok and f_ok)
        bk["gains"] += int(f_ok and not b_ok)
        bk["regressions"] += int(b_ok and not f_ok)
        if f_ok and not b_ok:
            gains.append((p, gt, bp, fp))
        elif b_ok and not f_ok:
            regress.append((p, gt, bp, fp))
    columns = []
    for bk in buckets.values():
        t = bk["total"]
        bk["netChange"] = bk["gains"] - bk["regressions"]
        bk["baseExactPct"] = 100.0 * bk["baseCorrect"] / t
        bk["finetunedExactPct"] = 100.0 * bk["finetunedCorrect"] / t
        bk["deltaPp"] = bk["finetunedExactPct"] - bk["baseExactPct"]
        columns.append(bk)
    columns.sort(key=lambda it: (-it["total"], it["column"]))
    n = len(rows)
    b_ex = 100.0 * base_ok / n if n else 0.0
    f_ex = 100.0 * ft_ok / n if n else 0.0
    gains_ex = gains if max_examples <= 0 else gains[:max_examples]
    regress_ex = regress if max_examples <= 0 else regress[:max_examples]
    return {"n": n, "base_ok": base_ok, "ft_ok": ft_ok, "both_ok": both_ok,
            "b_ex": b_ex, "f_ex": f_ex, "gains": len(gains), "regress": len(regress),
            "columns": columns, "scripts": _script_stats(outcomes), "gainsEx": gains_ex,
            "regressEx": regress_ex}


def _example_caption(total: int, shown: int) -> str:
    return f"전체 {shown:,}" if shown == total else f"상위 {shown:,}"


def _script_card(script: dict, label: str) -> str:
    net = script["netChange"]
    cls = "up" if net >= 0 else "down"
    return _card(
        f'<span class="{cls}">{net:+,}건</span>',
        f"{label} 인식 순증",
        f'Exact Δ {script["deltaPp"]:+.1f}%p · 대상 {script["total"]:,}',
    )


def render_bench(tabs, run_tag, ft_dir):
    """seen/unseen 두 탭을 한 HTML 로. tabs = {'unseen': stats, 'seen': stats}."""
    style = """
:root{--bg:#f6f8fa;--card:#fff;--line:#d0d7de;--fg:#1f2328;--muted:#59636e;--up:#1a7f37;--down:#cf222e;--accent:#0969da}
*{box-sizing:border-box}html,body{max-width:100%;overflow-x:hidden}body{margin:0;background:var(--bg);color:var(--fg);
font-family:'Segoe UI','Malgun Gothic',system-ui,sans-serif;font-size:14px;padding:24px}
h1{font-size:20px;margin:0 0 4px}.gen{color:var(--muted);font-size:12.5px;margin-bottom:14px}
.tabbar{display:flex;gap:8px;border-bottom:2px solid var(--line);margin-bottom:16px}
.tabbtn{background:none;border:none;padding:10px 18px;font-size:14px;font-weight:600;color:var(--muted);
cursor:pointer;border-bottom:3px solid transparent;margin-bottom:-2px}
.tabbtn.active{color:var(--accent);border-bottom-color:var(--accent)}
.tabpane{display:none}.tabpane.active{display:block}
.banner{background:var(--card);border:1px solid var(--line);border-left:5px solid var(--up);
border-radius:10px;padding:14px 18px;width:100%;margin-bottom:16px;font-size:15px}.banner b{font-size:22px}
.cardgrid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px;width:100%;margin-bottom:16px}
.cardbox{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 18px}
.cardv{font-size:26px;font-weight:700}.cardl{color:var(--muted);font-size:12.5px}
section{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px 18px;
margin:16px 0;width:100%;min-width:0}h2{font-size:15px;margin:0 0 10px}
table{border-collapse:collapse;width:100%}th,td{padding:6px 10px;border-bottom:1px solid var(--line);
text-align:left;font-size:13px}th{color:var(--muted);font-weight:600;font-size:12px}
.up{color:var(--up);font-weight:600}.down{color:var(--down);font-weight:600}.muted{color:var(--muted)}
.hl{background:#ffd7d5;border-radius:2px}
.note{width:100%;color:var(--muted);font-size:12.5px;line-height:1.7;overflow-wrap:anywhere}.note b{color:var(--fg)}
.table-scroll{width:100%;overflow:auto}.column-table{min-width:880px}
.column-table th,.column-table td{white-space:nowrap}.total-row{background:#f0f4f8}
.missing-row td{color:var(--muted);opacity:.65}.missing-row b{color:var(--muted);font-weight:600}
.example-scroll{width:100%;overflow:auto;border:1px solid var(--line);border-radius:6px}
.example-table{width:100%;min-width:900px;table-layout:fixed}
.example-table th:nth-child(1){width:27%}.example-table th:nth-child(2){width:24%}
.example-table th:nth-child(3),.example-table th:nth-child(4){width:24.5%}
.example-table th{position:sticky;top:0;z-index:1;background:var(--card)}
.example-table td{white-space:normal;overflow-wrap:anywhere;word-break:break-word;vertical-align:middle}
.example-table .crop img{display:block;max-width:100%;max-height:42px;border:1px solid var(--line)}
@media(max-width:760px){body{padding:12px}.cardgrid{grid-template-columns:1fr}section{padding:12px}}
"""
    order = [("unseen", "처음 · 학습에 안 쓴 9,001장 실패셀"),
             ("retain", "유지 · 기존에 읽던 셀 (까먹음 감시)"),
             ("seen", "포함 · 학습에 쓴 셀 (외운 것 재현 상한)")]
    btns, panes = [], []
    gains_secs, regress_secs = [], []
    total_gains = total_regress = 0
    for i, (key, title) in enumerate(order):
        st = tabs.get(key)
        active = " active" if i == 0 else ""
        if not st or st["n"] == 0:
            btns.append(f'<button class="tabbtn{active}" data-tab="{key}">{html.escape(title)} <span class="muted">(0)</span></button>')
            panes.append(f'<div class="tabpane{active}" id="pane-{key}"><section><div class="note">이 탭은 크롭이 없습니다. '
                         f'(SEEN 은 해당 run 의 train.txt 에 그 컬럼 실패 크롭이 있어야 채워집니다 — build_ft_bench.py 재실행 필요.)</div></section></div>')
            continue
        d_ex = st["f_ex"] - st["b_ex"]
        dcls = "up" if d_ex >= 0 else "down"
        arrow = "▲" if d_ex >= 0 else "▼"
        net = st["gains"] - st["regress"]
        # 포함(seen) 탭: 처음(unseen) 탭엔 있는데 여기 없는 컬럼 = 이번 학습 미포함 → 회색 행.
        missing_cols = []
        if key == "seen":
            unseen_cols = [c["column"] for c in tabs.get("unseen", {}).get("columns", [])]
            have = {c["column"] for c in st["columns"]}
            missing_cols = [c for c in unseen_cols if c not in have]
        btns.append(f'<button class="tabbtn{active}" data-tab="{key}">{html.escape(title)} '
                    f'<span class="muted">({st["n"]:,})</span></button>')
        pane = f"""<div class="tabpane{active}" id="pane-{key}">
<div class="banner">정확일치율 <span class="muted">(Exact)</span>: <b>{st["b_ex"]:.1f}% → {st["f_ex"]:.1f}%</b>
<span class="{dcls}">{arrow} {abs(d_ex):.1f}%p</span> &nbsp;·&nbsp; 크롭 {st["n"]:,}장 · 순증 <span class="{"up" if net>=0 else "down"}">{net:+,}</span></div>
<div class="cardgrid">
{_card(f'{st["b_ex"]:.1f}%', 'base 정확일치', 'Base Exact')}
{_card(f'{st["f_ex"]:.1f}%', '파인튜닝 정확일치', 'Fine-tuned Exact')}
{_card(f'<span class="{dcls}">{arrow} {abs(d_ex):.1f}</span>', '정확일치 개선', 'Exact Δ %p')}
{_script_card(st["scripts"]["hangul"], "한글")}
{_script_card(st["scripts"]["number"], "숫자")}
</div>
<section><h2>컬럼별 변화 <span class="muted">(원본 컬럼 기준 · 개선/회귀/순증)</span></h2>
<div class="table-scroll"><table class="column-table"><thead><tr>
<th>컬럼</th><th>전체</th><th>base 정답</th><th>파인튜닝 정답</th>
<th>개선</th><th>회귀</th><th>순증</th><th>정확일치 Δ</th></tr></thead>
<tbody>{_column_rows(st["columns"], st, missing_cols=missing_cols)}</tbody></table></div></section>
</div>"""
        panes.append(pane)
        # 개선/회귀 사례는 데이터 탭에 안 붙이고 별도 상단 탭(개선/회귀)에 출처별 섹션으로 모은다.
        # (출처×종류 탭 분리안은 탭 9개로 과밀 — 5탭 + 출처 섹션이 비교에 유리)
        short = title.split(" ·")[0]
        total_gains += st["gains"]
        total_regress += st["regress"]
        gains_secs.append(
            f'<section><h2>{html.escape(short)} <span class="muted">탭 크롭</span> · '
            f'{st["gains"]:,}건 중 {_example_caption(st["gains"], len(st["gainsEx"]))}</h2>'
            f'<div class="example-scroll" data-scroll-after="{SCROLL_AFTER}">'
            f'<table class="example-table"><thead>{_TH}</thead>'
            f'<tbody>{_ex_rows(st["gainsEx"], len(st["gainsEx"]))}</tbody></table></div></section>')
        regress_secs.append(
            f'<section><h2>{html.escape(short)} <span class="muted">탭 크롭</span> · '
            f'{st["regress"]:,}건 중 {_example_caption(st["regress"], len(st["regressEx"]))}</h2>'
            f'<div class="example-scroll" data-scroll-after="{SCROLL_AFTER}">'
            f'<table class="example-table"><thead>{_TH}</thead>'
            f'<tbody>{_ex_rows(st["regressEx"], len(st["regressEx"]))}</tbody></table></div></section>')
    # 사례 탭 2개: 개선(새로 읽게 된 크롭) / 회귀(틀리게 된 크롭) — 출처(처음/유지/포함)별 섹션.
    btns.append(f'<button class="tabbtn" data-tab="gains">✅ 개선 사례 '
                f'<span class="muted">({total_gains:,})</span></button>')
    panes.append(f'<div class="tabpane" id="pane-gains">'
                 f'<div class="banner">FT가 새로 맞히게 된 크롭 (base ✗ → FT ✓) · 출처 탭별 구분</div>'
                 f'{"".join(gains_secs)}</div>')
    btns.append(f'<button class="tabbtn" data-tab="regress">⚠️ 회귀 사례 '
                f'<span class="muted">({total_regress:,})</span></button>')
    panes.append(f'<div class="tabpane" id="pane-regress">'
                 f'<div class="banner" style="border-left-color:var(--down)">FT가 틀리게 된 크롭 (base ✓ → FT ✗) · '
                 f'유지 섹션의 회귀 = 까먹음</div>'
                 f'{"".join(regress_secs)}</div>')
    return f"""<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8">
<title>인식 파인튜닝 벤치 (처음/유지/포함)</title><style>{style}</style></head><body>
<h1>인식 파인튜닝 벤치 <span class="muted" style="font-size:14px">Recognition Fine-tune Bench</span></h1>
<div class="gen">실행번호 {html.escape(run_tag)} · base vs 파인튜닝 · 고정 크롭 벤치(순수 인식) · 파인튜닝 모델 = {html.escape(ft_dir)}</div>
<section><h2>기준·용어 <span class="muted">(Basis)</span></h2><div class="note">
<b>처음</b> = 9,001 held-out 문서의 실패 크롭 — <b>학습에 안 쓴</b> 것. "처음 보는 송장의 안 읽히던 셀을 FT가 얼마나 읽게 되나" = 회사 답.<br>
<b>유지</b> = base 가 <b>원래 맞게 읽던</b> 크롭(정답풀, 학습 제외 샘플). "기존 걸 까먹지 않았나" — 여기 Δ가 −면 망각. 글자종류 버킷(짧은숫자=수량류 조기경보).<br>
<b>포함</b> = 이 run 이 학습에 실제로 쓴 실패 크롭(처음 탭과 컬럼 분포 매칭 샘플). "외운 걸 재현하는 상한". <b>포함↔처음 간격 = 일반화</b>(간격 크면 암기, 작으면 진짜 실력).<br>
<b>판정 = 처음(회복) + AND 유지(까먹음 없음) ≥0</b> — 둘 다 통과해야 본판/E2E 로 진행.<br>
<b>한글/숫자 인식 순증</b> = 해당 글자가 GT에 포함된 크롭의 개선−회귀. 괄호의 Δ는 정확일치 %p이며 한글+숫자 혼합 문자열은 양쪽에 포함.<br>
<b>구성</b> = 양쪽 다 <b>실패 크롭</b>(base 가 틀린 셀)만 — balance 정답크롭은 src 메타가 없어 9,001 식별 불가라 이 벤치 스코프 밖. 절대% 아니라 <b>base→FT 델타</b>가 핵심.<br>
<b>숫자</b>(수량·단가·금액) = <b>산술앵커</b>(수량×단가=금액) 통과 행의 값만 채점(war 숫자 GT 순환 차단). <b>바코드(itemCode) 제외</b>(broad-forgetting 독).<br>
</div></section>
<div class="tabbar">{"".join(btns)}</div>
{"".join(panes)}
<script>
// 숨김 탭(display:none)에서 offsetTop=0 으로 재면 maxHeight 1px 로 붕괴(probe1 실측:
// SEEN 탭 사례가 빈 것처럼 보임) → 보이는 탭만 재고, 탭 전환 때 다시 잰다.
function sizeScrollBoxes(root){{
  (root||document).querySelectorAll('.example-scroll').forEach(function(box){{
    if(box.dataset.sized||box.offsetParent===null) return;
    var rows=box.querySelectorAll('tbody tr');var after=Number(box.dataset.scrollAfter||{SCROLL_AFTER});
    if(rows.length>after){{
      var lv=rows[after-1];
      if(lv.offsetTop>0||lv.offsetHeight>0){{
        box.style.maxHeight=(lv.offsetTop+lv.offsetHeight+1)+'px';box.style.overflowY='auto';box.dataset.sized='1';
      }}
    }}else{{box.dataset.sized='1';}}
  }});
}}
document.querySelectorAll('.tabbtn').forEach(function(b){{b.addEventListener('click',function(){{
  document.querySelectorAll('.tabbtn').forEach(x=>x.classList.remove('active'));
  document.querySelectorAll('.tabpane').forEach(x=>x.classList.remove('active'));
  b.classList.add('active');
  var pane=document.getElementById('pane-'+b.dataset.tab);
  pane.classList.add('active');
  sizeScrollBoxes(pane);
}});}});
sizeScrollBoxes(document);
</script></body></html>"""


def main_bench(run_tag, max_examples):
    """--bench: 고정 SEEN/UNSEEN 벤치에 base vs FT 채점 → 탭 리포트."""
    try:
        from paddlex import create_model
    except ImportError:
        from paddlex.inference import create_model  # type: ignore
    ft_dir = find_ft_inference()
    if not ft_dir:
        raise SystemExit("no fine-tuned inference dir under eval/finetune/output — run export first")
    base = create_model(BASE_MODEL)
    ft = create_model(BASE_MODEL, ft_dir)

    tabs = {}
    for key, path in (("unseen", BENCH_UNSEEN), ("retain", BENCH_RETAIN), ("seen", BENCH_SEEN)):
        rows = load_bench(path)
        print(f"[bench] {key}: {len(rows):,} crops ({path})")
        if not rows:
            tabs[key] = {"n": 0}
            continue
        paths = [p for p, _, _, _ in rows]
        bp = predict_all(base, paths)
        fp = predict_all(ft, paths)
        # 예측 보존: 채점 방식이 바뀌어도 GPU 재추론 없이 재채점 가능하게.
        pred_path = os.path.join(HERE, "finetune", f"BENCH_PREDICTIONS_{run_tag}_{key}.jsonl")
        with open(pred_path + ".tmp", "w", encoding="utf-8") as fh:
            for (_, rel, gt, col), b, f in zip(rows, bp, fp):
                fh.write(json.dumps({"path": rel, "col": col, "gt": gt, "base": b, "ft": f},
                                    ensure_ascii=False) + "\n")
        os.replace(pred_path + ".tmp", pred_path)
        st = _bench_tab_stats(rows, bp, fp, max_examples)
        print(f"[bench] {key}: base {st['b_ex']:.1f}% -> ft {st['f_ex']:.1f}%  "
              f"(Δ{st['f_ex']-st['b_ex']:+.1f})  net {st['gains']-st['regress']:+,}")
        tabs[key] = st

    html_out = render_bench(tabs, run_tag, ft_dir)
    out_dir = os.path.join(HERE, "finetune")
    os.makedirs(out_dir, exist_ok=True)
    numbered = os.path.join(out_dir, f"FINETUNE_BENCH_{run_tag}.html")
    latest = os.path.join(out_dir, "FINETUNE_BENCH.html")
    _write_text(numbered, html_out)
    _write_text(latest, html_out)
    summary = {"schemaVersion": "finetune-bench.v1", "runTag": run_tag, "ftDir": ft_dir,
               "tabs": {k: {kk: v[kk] for kk in ("n", "b_ex", "f_ex", "gains", "regress")
                            if kk in v} for k, v in tabs.items()}}
    _write_text(os.path.join(out_dir, f"FINETUNE_BENCH_{run_tag}.json"),
                json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    print(f"[bench] wrote {numbered}")
    print(f"[bench] updated {latest}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--run-tag", "--report-id", dest="run_tag",
        help="파일명 뒤에 붙일 실행번호(미지정 시 현재시각 YYMMDD_HHMMSS)",
    )
    parser.add_argument(
        "--max-examples", type=int, default=MAX_EXAMPLES,
        help="개선/회귀 표에 포함할 최대 행 수(기본 0=전체, 양수=제한)",
    )
    parser.add_argument(
        "--bench", action="store_true",
        help="고정 SEEN/UNSEEN 벤치(bench_unseen.txt/bench_seen.txt)에 채점, 탭 리포트 출력",
    )
    args = parser.parse_args()
    if args.bench:
        return main_bench(_report_id(args.run_tag), max(0, args.max_examples))
    run_tag = _report_id(args.run_tag)
    numbered_out, numbered_json = _numbered_paths(run_tag)
    max_examples = max(0, args.max_examples)

    try:
        from paddlex import create_model
    except ImportError:
        from paddlex.inference import create_model  # type: ignore

    rows = load_test()
    if not rows:
        raise SystemExit(f"no test rows in {TEST_LIST} — run build_paddlex_dataset.py first")
    ft_dir = find_ft_inference()
    if not ft_dir:
        raise SystemExit("no fine-tuned inference dir under eval/finetune/output — run export first")
    paths = [p for p, _, _ in rows]
    gts = [gt for _, _, gt in rows]

    print(f"[report] test crops: {len(rows):,}")
    print(f"[report] base = {BASE_MODEL}")
    base = create_model(BASE_MODEL)
    base_pred = predict_all(base, paths)
    print(f"[report] fine-tuned = {ft_dir}")
    # create_model 시그니처 = (model_name, model_dir): 이름은 그대로, 가중치 디렉터리만 교체.
    # (경로만 넘기면 model_name 자리로 들어가 'Model name mismatch' — 실측 에러)
    ft = create_model(BASE_MODEL, ft_dir)
    ft_pred = predict_all(ft, paths)

    # The slice report runs immediately after this report.  Persist predictions
    # once so 품명/숫자 breakdown does not perform the same expensive GPU
    # inference a second time.  Labels/paths are included for stale-cache checks.
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    pred_tmp = PREDICTIONS_JSONL + ".tmp"
    with open(pred_tmp, "w", encoding="utf-8") as fh:
        for (_, rel, gt), base_text, ft_text in zip(rows, base_pred, ft_pred):
            fh.write(json.dumps({"path": rel, "gt": gt, "base": base_text, "finetuned": ft_text},
                                ensure_ascii=False) + "\n")
    os.replace(pred_tmp, PREDICTIONS_JSONL)

    def acc(preds):
        exact = sum(p.strip() == g.strip() for p, g in zip(preds, gts))
        char = sum(_sim(p.strip(), g.strip()) for p, g in zip(preds, gts))
        return 100.0 * exact / len(gts), 100.0 * char / len(gts)

    b_ex, b_ch = acc(base_pred)
    f_ex, f_ch = acc(ft_pred)

    gains, regress = [], []
    outcomes = []
    base_ok = ft_ok = both_ok = 0
    for (p, rel, gt), bp, fp in zip(rows, base_pred, ft_pred):
        b_ok = bp.strip() == gt.strip()
        f_ok = fp.strip() == gt.strip()
        base_ok += b_ok
        ft_ok += f_ok
        both_ok += b_ok and f_ok
        outcomes.append((gt, b_ok, f_ok))
        if f_ok and not b_ok:
            gains.append((p, gt, bp, fp))
        elif b_ok and not f_ok:
            regress.append((p, gt, bp, fp))

    metadata = _load_test_metadata()
    columns = _column_stats(rows, base_pred, ft_pred, metadata)
    metadata_matched = sum(
        bool(metadata.get(rel, {}).get("column")) for _, rel, _ in rows
    )
    print(f"[report] exact: base {b_ex:.1f}% -> ft {f_ex:.1f}%  (Δ{f_ex - b_ex:+.1f})")
    print(f"[report] gains {len(gains)} / regress {len(regress)}")

    stats = {"n": len(rows), "b_ex": b_ex, "f_ex": f_ex, "b_ch": b_ch, "f_ch": f_ch,
             "base_ok": base_ok, "ft_ok": ft_ok, "both_ok": both_ok,
             "gains": len(gains), "regress": len(regress), "ft_dir": ft_dir,
             "runTag": run_tag, "columnMetadataMatched": metadata_matched,
             "columns": columns, "scripts": _script_stats(outcomes)}
    html_out = render(stats, gains, regress, max_examples=max_examples)
    json_out = json.dumps({
        "schemaVersion": "finetune-report.v2", **stats,
        "overallDeltaPp": f_ex - b_ex,
        "netChange": len(gains) - len(regress),
    }, ensure_ascii=False, indent=2) + "\n"

    # 실행별 번호 파일은 보존하고, 고정 파일은 기존 후속 집계용 최신본으로 유지한다.
    _write_text(numbered_out, html_out)
    _write_text(numbered_json, json_out)
    _write_text(OUT, html_out)
    _write_text(OUT_JSON, json_out)
    print(f"[report] wrote numbered {numbered_out}")
    print(f"[report] wrote numbered {numbered_json}")
    print(f"[report] updated latest {OUT}")
    print(f"[report] updated latest {OUT_JSON}")
    return 0


def _card(val, ko, en):
    return (f'<div class="cardbox"><div class="cardv">{val}</div>'
            f'<div class="cardl">{ko} <span class="muted">({en})</span></div></div>')


def _diff(pred, gt):
    """pred 에서 gt 와 다른 글자만 빨강 배경 하이라이트."""
    sm = difflib.SequenceMatcher(None, gt, pred)
    out = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        seg = html.escape(pred[j1:j2])
        out.append(seg if (tag == "equal" or not seg) else f'<span class="hl">{seg}</span>')
    return "".join(out) or '<span class="muted">(빈칸)</span>'


def _ex_rows(items, limit=MAX_EXAMPLES):
    out = []
    selected = items if limit <= 0 else items[:limit]
    for p, gt, bp, fp in selected:
        out.append(
            f'<tr><td class="crop"><img src="{_b64(p)}" alt="평가 크롭" loading="lazy"></td>'
            f'<td><b>{html.escape(gt)}</b></td>'
            f'<td class="down">{_diff(bp, gt)}</td>'
            f'<td class="up">{_diff(fp, gt)}</td></tr>')
    return "".join(out) or '<tr><td colspan="4" class="muted">해당 없음</td></tr>'


_TH = ('<tr><th>크롭 <span class="muted">(Crop)</span></th>'
       '<th>정답 <span class="muted">(Ground Truth)</span></th>'
       '<th>base 읽음 <span class="muted">(Base OCR)</span></th>'
       '<th>파인튜닝 읽음 <span class="muted">(Fine-tuned OCR)</span></th></tr>')


def _column_rows(columns: list[dict], stats: dict,
                 missing_cols: list[str] | None = None) -> str:
    """missing_cols = 이 탭(학습)에 크롭이 하나도 없는 컬럼 — 회색 행으로 명시."""
    rows = []
    for item in columns:
        net = item["netChange"]
        ko = KO_COLS.get(item["column"])
        col_label = (f'{html.escape(item["column"])} <span class="muted">({ko})</span>'
                     if ko else html.escape(item["column"]))
        rows.append(
            f'<tr><td><b>{col_label}</b></td>'
            f'<td>{item["total"]:,}</td>'
            f'<td>{item["baseCorrect"]:,} <span class="muted">({item["baseExactPct"]:.1f}%)</span></td>'
            f'<td>{item["finetunedCorrect"]:,} <span class="muted">({item["finetunedExactPct"]:.1f}%)</span></td>'
            f'<td class="up">+{item["gains"]:,}</td>'
            f'<td class="down">-{item["regressions"]:,}</td>'
            f'<td class="{"up" if net >= 0 else "down"}">{net:+,}</td>'
            f'<td class="{"up" if item["deltaPp"] >= 0 else "down"}">{item["deltaPp"]:+.1f}%p</td></tr>'
        )
    for col in (missing_cols or []):
        ko = KO_COLS.get(col)
        label = (f'{html.escape(col)} <span class="muted">({ko})</span>'
                 if ko else html.escape(col))
        rows.append(
            f'<tr class="missing-row"><td><b>{label}</b> '
            f'<span class="muted">— 학습 미포함</span></td><td>0</td>'
            + '<td>—</td>' * 6 + '</tr>')
    net = stats["gains"] - stats["regress"]
    rows.append(
        f'<tr class="total-row"><td><b>Total</b></td><td><b>{stats["n"]:,}</b></td>'
        f'<td><b>{stats["base_ok"]:,}</b> <span class="muted">({stats["b_ex"]:.1f}%)</span></td>'
        f'<td><b>{stats["ft_ok"]:,}</b> <span class="muted">({stats["f_ex"]:.1f}%)</span></td>'
        f'<td class="up"><b>+{stats["gains"]:,}</b></td>'
        f'<td class="down"><b>-{stats["regress"]:,}</b></td>'
        f'<td class="{"up" if net >= 0 else "down"}"><b>{net:+,}</b></td>'
        f'<td class="{"up" if stats["f_ex"] >= stats["b_ex"] else "down"}">'
        f'<b>{stats["f_ex"] - stats["b_ex"]:+.1f}%p</b></td></tr>'
    )
    return "".join(rows)


def render(stats, gains, regress, max_examples=MAX_EXAMPLES):
    n, b_ex, f_ex = stats["n"], stats["b_ex"], stats["f_ex"]
    b_ch, f_ch = stats["b_ch"], stats["f_ch"]
    d_ex, d_ch = f_ex - b_ex, f_ch - b_ch
    dcls = "up" if d_ex >= 0 else "down"
    arrow = "▲" if d_ex >= 0 else "▼"
    net = stats["gains"] - stats["regress"]
    style = """
:root{--bg:#f6f8fa;--card:#fff;--line:#d0d7de;--fg:#1f2328;--muted:#59636e;--up:#1a7f37;--down:#cf222e}
*{box-sizing:border-box}html,body{max-width:100%;overflow-x:hidden}body{margin:0;background:var(--bg);color:var(--fg);
font-family:'Segoe UI','Malgun Gothic',system-ui,sans-serif;font-size:14px;padding:24px}
h1{font-size:20px;margin:0 0 4px}.gen{color:var(--muted);font-size:12.5px;margin-bottom:14px}
.banner{background:var(--card);border:1px solid var(--line);border-left:5px solid var(--up);
border-radius:10px;padding:14px 18px;width:100%;margin-bottom:16px;font-size:15px}
.banner b{font-size:22px}
.cardgrid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px;width:100%;margin-bottom:16px}
.cardbox{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 18px}
.cardv{font-size:26px;font-weight:700}.cardl{color:var(--muted);font-size:12.5px}
section{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px 18px;
margin:16px 0;width:100%;min-width:0}h2{font-size:15px;margin:0 0 10px}
table{border-collapse:collapse;width:100%}th,td{padding:6px 10px;border-bottom:1px solid var(--line);
text-align:left;font-size:13px}th{color:var(--muted);font-weight:600;font-size:12px}
.up{color:var(--up);font-weight:600}.down{color:var(--down);font-weight:600}.muted{color:var(--muted)}
.hl{background:#ffd7d5;border-radius:2px}
.note{width:100%;color:var(--muted);font-size:12.5px;line-height:1.7;overflow-wrap:anywhere}
.note b{color:var(--fg)}.kv td:first-child{color:var(--muted)}.kv td{border:none;padding:3px 14px 3px 0}
.table-scroll{width:100%;overflow:auto}.column-table{min-width:880px}
.column-table th,.column-table td{white-space:nowrap}.total-row{background:#f0f4f8}
.example-scroll{width:100%;overflow:auto;border:1px solid var(--line);border-radius:6px}
.example-table{width:100%;min-width:900px;table-layout:fixed}
.example-table th:nth-child(1){width:27%}.example-table th:nth-child(2){width:24%}
.example-table th:nth-child(3),.example-table th:nth-child(4){width:24.5%}
.example-table th{position:sticky;top:0;z-index:1;background:var(--card)}
.example-table td{white-space:normal;overflow-wrap:anywhere;word-break:break-word;vertical-align:middle}
.example-table .crop img{display:block;max-width:100%;max-height:42px;border:1px solid var(--line)}
@media(max-width:760px){body{padding:12px}.cardgrid{grid-template-columns:1fr}
section{padding:12px}.banner b{font-size:18px}}
"""
    return f"""<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8">
<title>인식 파인튜닝 리포트 (Recognition Fine-tune Report)</title><style>{style}</style></head><body>
<h1>인식 파인튜닝 리포트 <span class="muted" style="font-size:14px">Recognition Fine-tune Report</span></h1>
<div class="gen">실행번호 {html.escape(stats.get("runTag", "-"))} · base 모델 vs 파인튜닝 모델 · held-out test {n:,}장 · 크롭 직접 인식 비교 (파서·룰·매칭 무관, 순수 인식)</div>

<div class="banner">정확일치율 <span class="muted">(Exact Match)</span>:
<b>{b_ex:.1f}% → {f_ex:.1f}%</b>
<span class="{dcls}">{arrow} {abs(d_ex):.1f}%p</span>
&nbsp;·&nbsp; 문자유사도 <span class="muted">(Char Similarity)</span>: {b_ch:.1f}% → {f_ch:.1f}%
<span class="{"up" if d_ch>=0 else "down"}">{d_ch:+.1f}%p</span></div>

<div class="cardgrid">
{_card(f'{b_ex:.1f}%', 'base 정확일치', 'Base Exact')}
{_card(f'{f_ex:.1f}%', '파인튜닝 정확일치', 'Fine-tuned Exact')}
{_card(f'<span class="{dcls}">{arrow} {abs(d_ex):.1f}</span>', '정확일치 개선', 'Exact Δ %p')}
{_card(f'{b_ch:.1f}%', 'base 문자유사도', 'Base Char Sim')}
{_card(f'{f_ch:.1f}%', '파인튜닝 문자유사도', 'Fine-tuned Char Sim')}
{_card(f'<span class="{"up" if d_ch>=0 else "down"}">{d_ch:+.1f}</span>', '문자유사도 개선', 'Char Sim Δ %p')}
{_script_card(stats["scripts"]["hangul"], "한글")}
{_script_card(stats["scripts"]["number"], "숫자")}
</div>

<section><h2>집계 <span class="muted">(Summary)</span></h2>
<table class="kv"><tbody>
<tr><td>전체 (Total test crops)</td><td><b>{n:,}</b></td></tr>
<tr><td>base 정답 (Base correct)</td><td>{stats["base_ok"]:,} ({b_ex:.1f}%)</td></tr>
<tr><td>파인튜닝 정답 (Fine-tuned correct)</td><td>{stats["ft_ok"]:,} ({f_ex:.1f}%)</td></tr>
<tr><td>둘 다 정답 (Both correct)</td><td>{stats["both_ok"]:,}</td></tr>
<tr><td>개선 (Gains: base✗ → ft✓)</td><td class="up">+{stats["gains"]:,}</td></tr>
<tr><td>회귀 (Regressions: base✓ → ft✗)</td><td class="down">-{stats["regress"]:,}</td></tr>
<tr><td>순증 (Net = gains − regressions)</td><td class="{"up" if net>=0 else "down"}"><b>{net:+,}</b></td></tr>
</tbody></table></section>

<section><h2>컬럼별 변화 <span class="muted">(원본 컬럼 기준 · 개선/회귀/순증 · 메타데이터 {stats.get("columnMetadataMatched", 0):,}/{n:,})</span></h2>
<div class="table-scroll"><table class="column-table"><thead><tr>
<th>컬럼</th><th>전체</th><th>base 정답</th><th>파인튜닝 정답</th>
<th>개선</th><th>회귀</th><th>순증</th><th>정확일치 Δ</th>
</tr></thead><tbody>{_column_rows(stats.get("columns", []), stats)}</tbody></table></div>
</section>

<section><h2>기준·용어 <span class="muted">(Basis & Definitions)</span></h2>
<div class="note">
<b>base 모델 (Base)</b> = <code>{html.escape(BASE_MODEL)}</code> — 현재 서버가 쓰는 원본 PP-OCRv5 mobile 한국어 rec<br>
<b>파인튜닝 모델 (Fine-tuned)</b> = {html.escape(stats["ft_dir"])}<br>
<b>평가셋 (Test set)</b> = held-out 크롭 {n:,}장 — <b>학습에 쓰지 않은</b> 것만 (063 시대 corpus 유래). 학습 데이터로 재면 오버핏 착시라 제외<br>
<b>정확일치 (Exact Match)</b> = 읽은 문자열이 정답과 완전히 같음 (앞뒤 공백 무시). 이게 "제대로 읽었나"의 핵심 지표<br>
<b>문자유사도 (Char Similarity)</b> = difflib ratio 평균 — 부분적으로 맞은 것도 반영 (한 글자만 틀려도 0 아님)<br>
<b>한글/숫자 인식 순증</b> = 해당 글자가 GT에 포함된 크롭의 개선−회귀. 괄호의 Δ는 정확일치 %p이며 한글+숫자 혼합 문자열은 양쪽에 포함<br>
<b>Δ (개선폭)</b> = 파인튜닝 − base (%p). 아래 표에서 <span class="hl">빨강 배경</span> = 정답과 다른 글자<br>
</div></section>

<section><h2>✅ 개선 사례 <span class="muted">(Gains — 파인튜닝이 맞히고 base 가 틀림)</span> · {stats["gains"]:,}건 중 {_example_caption(stats["gains"], stats["gains"] if max_examples <= 0 else min(stats["gains"], max_examples))} <span class="muted">({SCROLL_AFTER}행 이후 스크롤)</span></h2>
<div class="example-scroll" data-scroll-after="{SCROLL_AFTER}"><table class="example-table"><thead>{_TH}</thead><tbody>{_ex_rows(gains, max_examples)}</tbody></table></div></section>

<section><h2>⚠️ 회귀 사례 <span class="muted">(Regressions — base 가 맞혔는데 파인튜닝이 틀림)</span> · {stats["regress"]:,}건 중 {_example_caption(stats["regress"], stats["regress"] if max_examples <= 0 else min(stats["regress"], max_examples))} <span class="muted">({SCROLL_AFTER}행 이후 스크롤)</span></h2>
<div class="example-scroll" data-scroll-after="{SCROLL_AFTER}"><table class="example-table"><thead>{_TH}</thead><tbody>{_ex_rows(regress, max_examples)}</tbody></table></div></section>
<script>
document.querySelectorAll('.example-scroll').forEach(function(box) {{
  var rows = box.querySelectorAll('tbody tr');
  var after = Number(box.dataset.scrollAfter || {SCROLL_AFTER});
  if (rows.length > after) {{
    var lastVisible = rows[after - 1];
    if (lastVisible.offsetTop > 0 || lastVisible.offsetHeight > 0) {{
      box.style.maxHeight = (lastVisible.offsetTop + lastVisible.offsetHeight + 1) + 'px';
      box.style.overflowY = 'auto';
    }}
  }}
}});
</script>
</body></html>"""


if __name__ == "__main__":
    raise SystemExit(main())
