"""finetune_report — "인식이 좋아졌나"를 직접 보여주는 self-contained HTML.

파서·룰·end-to-end eval 을 안 섞고, RECOGNITION 수준에서 직접 비교한다:
  base 모델(서버가 쓰는 korean_PP-OCRv5_mobile_rec)과 파인튜닝 모델(export 된 inference)을
  held-out test 크롭(dataset test.txt)에 각각 돌려서
    - 정확 일치율(exact) / 문자 유사도(char) 를 모델별로
    - 파인튜닝이 맞히고 base 가 틀린 크롭(개선) + 그 반대(회귀) 를 크롭 이미지째
  를 하나의 HTML 로 낸다. 크롭은 base64 로 박아 넣어 로컬에서 파일만 열면 보인다.

run-finetune.sh 의 마지막 단계로 자동 실행. 출력: eval/finetune/FINETUNE_REPORT.html

    .venv/bin/python eval/finetune_report.py
"""
from __future__ import annotations

import base64
import difflib
import glob
import html
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from finetune_ledger import CORPUS_DIR  # noqa: E402

BASE_MODEL = "korean_PP-OCRv5_mobile_rec"
TEST_LIST = os.path.join(CORPUS_DIR, "test.txt")
OUT = os.path.join(HERE, "finetune", "FINETUNE_REPORT.html")
OUT_JSON = os.path.join(HERE, "finetune", "FINETUNE_REPORT.json")
PREDICTIONS_JSONL = os.path.join(HERE, "finetune", "FINETUNE_PREDICTIONS.jsonl")
MAX_EXAMPLES = 40          # 개선/회귀 각각 최대 표시(크롭 박음)


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


def main() -> int:
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
    base_ok = ft_ok = both_ok = 0
    for (p, rel, gt), bp, fp in zip(rows, base_pred, ft_pred):
        b_ok = bp.strip() == gt.strip()
        f_ok = fp.strip() == gt.strip()
        base_ok += b_ok
        ft_ok += f_ok
        both_ok += b_ok and f_ok
        if f_ok and not b_ok:
            gains.append((p, gt, bp, fp))
        elif b_ok and not f_ok:
            regress.append((p, gt, bp, fp))

    print(f"[report] exact: base {b_ex:.1f}% -> ft {f_ex:.1f}%  (Δ{f_ex - b_ex:+.1f})")
    print(f"[report] gains {len(gains)} / regress {len(regress)}")

    stats = {"n": len(rows), "b_ex": b_ex, "f_ex": f_ex, "b_ch": b_ch, "f_ch": f_ch,
             "base_ok": base_ok, "ft_ok": ft_ok, "both_ok": both_ok,
             "gains": len(gains), "regress": len(regress), "ft_dir": ft_dir}
    html_out = render(stats, gains, regress)
    open(OUT, "w", encoding="utf-8").write(html_out)
    with open(OUT_JSON, "w", encoding="utf-8") as fh:
        json.dump({"schemaVersion": "finetune-report.v1", **stats,
                   "overallDeltaPp": f_ex - b_ex,
                   "netChange": len(gains) - len(regress)},
                  fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    print(f"[report] wrote {OUT}")
    print(f"[report] wrote {OUT_JSON}")
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


def _ex_rows(items):
    out = []
    for p, gt, bp, fp in items[:MAX_EXAMPLES]:
        out.append(
            f'<tr><td><img src="{_b64(p)}" style="max-height:36px;border:1px solid var(--line)"></td>'
            f'<td><b>{html.escape(gt)}</b></td>'
            f'<td class="down">{_diff(bp, gt)}</td>'
            f'<td class="up">{_diff(fp, gt)}</td></tr>')
    return "".join(out) or '<tr><td colspan="4" class="muted">해당 없음</td></tr>'


_TH = ('<tr><th>크롭 <span class="muted">(Crop)</span></th>'
       '<th>정답 <span class="muted">(Ground Truth)</span></th>'
       '<th>base 읽음 <span class="muted">(Base OCR)</span></th>'
       '<th>파인튜닝 읽음 <span class="muted">(Fine-tuned OCR)</span></th></tr>')


def render(stats, gains, regress):
    n, b_ex, f_ex = stats["n"], stats["b_ex"], stats["f_ex"]
    b_ch, f_ch = stats["b_ch"], stats["f_ch"]
    d_ex, d_ch = f_ex - b_ex, f_ch - b_ch
    dcls = "up" if d_ex >= 0 else "down"
    arrow = "▲" if d_ex >= 0 else "▼"
    net = stats["gains"] - stats["regress"]
    style = """
:root{--bg:#f6f8fa;--card:#fff;--line:#d0d7de;--fg:#1f2328;--muted:#59636e;--up:#1a7f37;--down:#cf222e}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);
font-family:'Segoe UI','Malgun Gothic',system-ui,sans-serif;font-size:14px;padding:24px}
h1{font-size:20px;margin:0 0 4px}.gen{color:var(--muted);font-size:12.5px;margin-bottom:14px}
.banner{background:var(--card);border:1px solid var(--line);border-left:5px solid var(--up);
border-radius:10px;padding:14px 18px;max-width:1100px;margin-bottom:16px;font-size:15px}
.banner b{font-size:22px}
.cardgrid{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;max-width:1100px;margin-bottom:16px}
.cardbox{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 18px}
.cardv{font-size:26px;font-weight:700}.cardl{color:var(--muted);font-size:12.5px}
section{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px 18px;
margin:16px 0;max-width:1100px;overflow-x:auto}h2{font-size:15px;margin:0 0 10px}
table{border-collapse:collapse;width:100%}th,td{padding:6px 10px;border-bottom:1px solid var(--line);
text-align:left;font-size:13px;white-space:nowrap}th{color:var(--muted);font-weight:600;font-size:12px}
.up{color:var(--up);font-weight:600}.down{color:var(--down);font-weight:600}.muted{color:var(--muted)}
.hl{background:#ffd7d5;border-radius:2px}
.note{max-width:1100px;color:var(--muted);font-size:12.5px;line-height:1.7}
.note b{color:var(--fg)}.kv td:first-child{color:var(--muted)}.kv td{border:none;padding:3px 14px 3px 0}
"""
    return f"""<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8">
<title>인식 파인튜닝 리포트 (Recognition Fine-tune Report)</title><style>{style}</style></head><body>
<h1>인식 파인튜닝 리포트 <span class="muted" style="font-size:14px">Recognition Fine-tune Report</span></h1>
<div class="gen">base 모델 vs 파인튜닝 모델 · held-out test {n:,}장 · 크롭 직접 인식 비교 (파서·룰·매칭 무관, 순수 인식)</div>

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

<section><h2>기준·용어 <span class="muted">(Basis & Definitions)</span></h2>
<div class="note">
<b>base 모델 (Base)</b> = <code>{html.escape(BASE_MODEL)}</code> — 현재 서버가 쓰는 원본 PP-OCRv5 mobile 한국어 rec<br>
<b>파인튜닝 모델 (Fine-tuned)</b> = {html.escape(stats["ft_dir"])}<br>
<b>평가셋 (Test set)</b> = held-out 크롭 {n:,}장 — <b>학습에 쓰지 않은</b> 것만 (063 시대 corpus 유래). 학습 데이터로 재면 오버핏 착시라 제외<br>
<b>정확일치 (Exact Match)</b> = 읽은 문자열이 정답과 완전히 같음 (앞뒤 공백 무시). 이게 "제대로 읽었나"의 핵심 지표<br>
<b>문자유사도 (Char Similarity)</b> = difflib ratio 평균 — 부분적으로 맞은 것도 반영 (한 글자만 틀려도 0 아님)<br>
<b>Δ (개선폭)</b> = 파인튜닝 − base (%p). 아래 표에서 <span class="hl">빨강 배경</span> = 정답과 다른 글자<br>
</div></section>

<section><h2>✅ 개선 사례 <span class="muted">(Gains — 파인튜닝이 맞히고 base 가 틀림)</span> · {stats["gains"]:,}건 중 상위 {min(stats["gains"],MAX_EXAMPLES)}</h2>
<table><thead>{_TH}</thead><tbody>{_ex_rows(gains)}</tbody></table></section>

<section><h2>⚠️ 회귀 사례 <span class="muted">(Regressions — base 가 맞혔는데 파인튜닝이 틀림)</span> · {stats["regress"]:,}건 중 상위 {min(stats["regress"],MAX_EXAMPLES)}</h2>
<table><thead>{_TH}</thead><tbody>{_ex_rows(regress)}</tbody></table></section>
</body></html>"""


if __name__ == "__main__":
    raise SystemExit(main())
