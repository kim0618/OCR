"""run_history — AWS eval/파인튜닝 실행 이력 장부 (append-only JSONL → HTML 표).

돌릴 때마다 한 줄씩 쌓인다(git 친화: 작음). eval/파인튜닝 두 표로 렌더:
  - 공통: 일시 · run · 처리 장수 · 소요 시간 · 시간당 처리량
  - eval:   필드/셀 정확도
  - 파인튜닝: epoch(반복 횟수) · best acc · 채택 여부

    # 렌더만 (jsonl → html)
    python eval/run_history.py
    # 기록 (run_all/run-finetune 이 호출)
    python eval/run_history.py --record eval --ts 066_.../thin --images 5964 --elapsed 8940 --field 54.2 --cell 44.4
    python eval/run_history.py --record finetune --ts v5 --images 10440 --epochs 6 --elapsed 1500 --best-acc 0.282 --adopted 0

파일: RUN_HISTORY.jsonl(장부·git추적) / RUN_HISTORY.html(뷰·git추적). 대용량 아님.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HERE, "RUN_HISTORY.jsonl")
OUT = os.path.join(HERE, "RUN_HISTORY.html")


def _now() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")


def record(kind: str, **fields) -> None:
    """한 run 을 장부에 추가(append) 후 HTML 재렌더. best-effort(호출측 안 깨짐)."""
    try:
        row = {"kind": kind, "when": _now()}
        row.update({k: v for k, v in fields.items() if v is not None})
        with open(LOG, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        render_html()
    except Exception as exc:  # 장부 실패가 run 을 깨선 안 됨
        print(f"  (run_history 기록 실패: {exc})")


def _load() -> list[dict]:
    rows = []
    if os.path.exists(LOG):
        for ln in open(LOG, encoding="utf-8"):
            ln = ln.strip()
            if ln:
                try:
                    rows.append(json.loads(ln))
                except json.JSONDecodeError:
                    continue
    return rows


def _dur(sec) -> str:
    if not sec:
        return "-"
    s = int(sec)
    if s >= 3600:
        return f"{s // 3600}시간 {(s % 3600) // 60}분"
    return f"{s // 60}분 {s % 60}초"


def _rate(images, sec) -> str:
    """시간당 처리 장수."""
    if not images or not sec:
        return "-"
    return f"{images / (sec / 3600):,.0f} 장/시간"


def _num(v, suffix="") -> str:
    return "-" if v is None else (f"{v:,}{suffix}" if isinstance(v, (int,)) else f"{v}{suffix}")


def render_html() -> str:
    rows = _load()
    ev = [r for r in rows if r.get("kind") == "eval"]
    ft = [r for r in rows if r.get("kind") == "finetune"]
    # 채택은 append-only 이벤트(kind=adopt, ts=버전)로 기록 → 해당 finetune 행에 반영.
    adopted_ts = {r.get("ts") for r in rows if r.get("kind") == "adopt"}
    for r in ft:
        if r.get("ts") in adopted_ts:
            r["adopted"] = 1

    def eval_rows():
        out = []
        tot_img = tot_sec = 0
        for i, r in enumerate(ev, 1):
            img = r.get("images"); sec = r.get("elapsedSec")
            tot_img += img or 0; tot_sec += sec or 0
            out.append(
                f"<tr><td>{i}</td><td>{r.get('when','-')}</td>"
                f"<td><code>{r.get('ts','-')}</code></td>"
                f"<td>{_num(img,'장')}</td><td>{_dur(sec)}</td><td>{_rate(img,sec)}</td>"
                f"<td>{_num(r.get('field'),'%')}</td><td>{_num(r.get('cell'),'%')}</td></tr>")
        out.append(
            f"<tr class='tot'><td colspan='3'>누계 ({len(ev)} run)</td>"
            f"<td>{tot_img:,}장</td><td>{_dur(tot_sec)}</td><td>{_rate(tot_img,tot_sec)}</td>"
            f"<td colspan='2'></td></tr>")
        return "".join(out)

    def ft_rows():
        out = []
        tot_img = tot_sec = 0
        for i, r in enumerate(ft, 1):
            img = r.get("images"); sec = r.get("elapsedSec")
            tot_img += img or 0; tot_sec += sec or 0
            ad = r.get("adopted")
            adtxt = ("<span class='up'>채택</span>" if ad in (1, True, "1")
                     else "<span class='muted'>미채택</span>" if ad is not None else "-")
            acc = r.get("bestAcc")
            out.append(
                f"<tr><td>{i}</td><td>{r.get('when','-')}</td>"
                f"<td><code>{r.get('ts','-')}</code></td>"
                f"<td><code class='b'>{r.get('base','official')}</code></td>"
                f"<td>{_num(img,'장')}</td><td>{_num(r.get('epochs'))}</td>"
                f"<td>{_dur(sec)}</td><td>{_rate(img,sec)}</td>"
                f"<td>{acc if acc is not None else '-'}</td><td>{adtxt}</td></tr>")
        out.append(
            f"<tr class='tot'><td colspan='4'>누계 ({len(ft)} run)</td>"
            f"<td>{tot_img:,}장</td><td colspan='1'></td><td>{_dur(tot_sec)}</td>"
            f"<td>{_rate(tot_img,tot_sec)}</td><td colspan='2'></td></tr>")
        return "".join(out)

    def lineage():
        """모델 계보 트리: base(부모)→자식. 채택=★줄기, 미채택=✗가지."""
        kids = {}
        for r in ft:
            kids.setdefault(r.get("base") or "official", []).append(r)
        if not ft:
            return "<div class='muted'>아직 파인튜닝 없음</div>"

        def node(name, depth):
            pad = "&nbsp;&nbsp;&nbsp;&nbsp;" * depth
            lines = []
            for r in kids.get(name, []):
                ad = r.get("adopted") in (1, True, "1")
                mark = "<span class='up'>★</span>" if ad else "<span class='muted'>✗</span>"
                acc = r.get("bestAcc")
                accs = f" acc {acc}" if acc is not None else ""
                cls = "adopt" if ad else "rej"
                lines.append(
                    f"<div class='ln {cls}'>{pad}└─ {mark} <code>{r.get('ts','?')}</code>"
                    f" <span class='muted'>(ep{r.get('epochs','?')}{accs})</span></div>")
                lines.append(node(r.get("ts"), depth + 1))   # 이 모델의 자식들
            return "".join(lines)
        return f"<div class='ln'><b>official</b> (공식 pretrained)</div>" + node("official", 1)

    css = """
:root{--bg:#f6f8fa;--card:#fff;--line:#d0d7de;--fg:#1f2328;--muted:#59636e;--up:#1a7f37;--head:#eef1f4}
@media(prefers-color-scheme:dark){:root{--bg:#0d1117;--card:#161b22;--line:#30363d;--fg:#e6edf3;--muted:#8b949e;--head:#21262d}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);
font-family:'Segoe UI','Malgun Gothic',system-ui,sans-serif;font-size:14px;padding:24px}
h1{font-size:20px;margin:0 0 4px}h2{font-size:15px;margin:22px 0 8px}
.gen{color:var(--muted);font-size:12.5px;margin-bottom:8px}
section{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 18px;
max-width:1200px;overflow-x:auto}
table{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums}
th,td{padding:7px 10px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}
th:nth-child(-n+3),td:nth-child(-n+3){text-align:left}
th{color:var(--muted);font-weight:600;font-size:12.5px;background:var(--head)}
code{background:var(--head);border:1px solid var(--line);border-radius:5px;padding:1px 5px;font-size:11.5px}
.tot{font-weight:700;background:var(--head)}.up{color:var(--up);font-weight:600}.muted{color:var(--muted)}
code.b{background:transparent;border:0;padding:0;color:var(--muted)}
.tree .ln{font-family:'Consolas','D2Coding',monospace;font-size:12.5px;line-height:1.9;white-space:nowrap}
.tree .adopt code{border-color:var(--up)}
"""
    html = f"""<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AWS 실행 이력 (eval / 파인튜닝)</title><style>{css}</style></head><body>
<h1>AWS 실행 이력</h1><div class="gen">생성 {_now()} · eval {len(ev)} run · 파인튜닝 {len(ft)} run · 돌릴 때마다 자동 누적</div>

<h2>① eval (측정 + 크롭 수확)</h2>
<section><table><thead><tr>
<th>#</th><th>일시</th><th>run</th><th>처리 장수</th><th>소요 시간</th><th>시간당 처리</th>
<th>필드</th><th>셀</th></tr></thead>
<tbody>{eval_rows()}</tbody></table></section>

<h2>② 파인튜닝 (모델 학습)</h2>
<section><table><thead><tr>
<th>#</th><th>일시</th><th>run</th><th>base(이어받은 부모)</th><th>학습 크롭</th><th>epoch(반복)</th><th>소요 시간</th>
<th>시간당 처리</th><th>best acc</th><th>채택</th></tr></thead>
<tbody>{ft_rows()}</tbody></table></section>

<h2>③ 모델 계보 (트리) — 채택★을 이어받아 쌓는 줄기</h2>
<section class="tree">{lineage()}
<div class="gen" style="margin-top:10px">★=채택(다음 학습의 base로 이어받음) · ✗=미채택(가지, 이어받지 않음). base 미지정 run 은 official(공식 pretrained)에서 시작.</div>
</section>
</body></html>"""
    open(OUT, "w", encoding="utf-8").write(html)
    return OUT


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", choices=["eval", "finetune"], default=None)
    ap.add_argument("--ts", default=None)
    ap.add_argument("--images", type=int, default=None)
    ap.add_argument("--elapsed", type=float, default=None)
    ap.add_argument("--field", type=float, default=None)
    ap.add_argument("--cell", type=float, default=None)
    ap.add_argument("--epochs", type=int, default=None)
    ap.add_argument("--best-acc", dest="best_acc", default=None)
    ap.add_argument("--adopted", default=None)
    ap.add_argument("--base", default=None, help="이어받은 부모 모델(트리). 미지정=official")
    args = ap.parse_args()
    if args.record:
        record(args.record, ts=args.ts, images=args.images, elapsedSec=args.elapsed,
               field=args.field, cell=args.cell, epochs=args.epochs,
               bestAcc=args.best_acc, adopted=args.adopted, base=args.base)
        print(f"[run_history] recorded {args.record} -> {OUT}")
    else:
        print(f"[run_history] rendered -> {render_html()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
