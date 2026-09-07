"""llm_ledger — LLM 비교에서 실제로 쓴 요금을 기록하고 계획서 지출 내역표에 써 넣는다.

원장은 `eval/LLM/data/ledger.jsonl` 한 곳이 출처다(append-only). 계획서 HTML 은
그걸 렌더한 결과이지 손으로 고치는 표가 아니다 - 손으로 고치면 다음 run 때 어긋난다.

두 종류를 구분해 적는다. 섞으면 합계가 부풀려진다:
  session  인스턴스가 켜져 있던 시간. **AWS 가 실제로 청구하는 것** → 누적에 더한다.
  run      개별 run 의 소요초 × 단가. 세션 안에 이미 포함된 **내역**이라 누적에 안 더한다.
           (072 를 3시간27분=$3.45 로 적은 기존 RUN_HISTORY 방식과 같은 계산)

CLI:
    python eval/llm_ledger.py                                   # 현재 원장 출력
    python eval/llm_ledger.py --add-run vlm_qwen_500 --label "Qwen3-VL 4B · 500장"
    python eval/llm_ledger.py --add-session "g6 전환·vLLM 구축" --hours 2.18 --rate g6
    python eval/llm_ledger.py --write                           # 계획서 표 갱신
"""
from __future__ import annotations

import argparse
import datetime
import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
PLAN = os.path.join(HERE, "LLM", "LLM_REVIEW_PLAN.html")
LEDGER = os.path.join(HERE, "LLM", "data", "ledger.jsonl")

# ap-northeast-2 on-demand Linux (2026-09-07 콘솔 실측)
RATES = {"g6": ("g6.xlarge", 0.9896), "g4dn": ("g4dn.xlarge", 0.6470)}


def load() -> list[dict]:
    if not os.path.exists(LEDGER):
        return []
    return [json.loads(l) for l in io.open(LEDGER, encoding="utf-8") if l.strip()]


def append(row: dict) -> None:
    os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
    with io.open(LEDGER, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def hhmm(h: float) -> str:
    m = round(h * 60)
    return f"{m}분" if m < 90 else f"{m // 60}시간 {m % 60}분"


def report(rows: list[dict]) -> None:
    print(f"{'날짜':<12}{'구분':<9}{'항목':<44}{'자원':<14}{'소요':>12}{'비용':>9}")
    print("-" * 102)
    for r in rows:
        print(f"{r['date']:<12}{r['kind']:<9}{r['item'][:42]:<44}{r['resource']:<14}"
              f"{hhmm(r['hours']):>12}{'$%.2f' % r['usd']:>9}")
    billed = sum(r["usd"] for r in rows if r["kind"] == "session")
    attrib = sum(r["usd"] for r in rows if r["kind"] == "run")
    print("-" * 102)
    print(f"{'실제 청구(세션 합)':<66}{'$%.2f' % billed:>36}")
    print(f"{'  그중 run 내역 합(중복 아님)':<66}{'$%.2f' % attrib:>36}")


def render(rows: list[dict]) -> str:
    out = []
    for r in rows:
        cls = ' class="dim"' if r["kind"] == "run" else ""
        mark = "&nbsp;&nbsp;↳ " if r["kind"] == "run" else ""
        note = f' <span class="muted">{r["note"]}</span>' if r.get("note") else ""
        out.append(
            f'      <tr{cls}><td>{r["date"]}</td><td>{mark}{r["item"]}{note}</td>'
            f'<td class="muted">{r["resource"]}</td><td>{hhmm(r["hours"])}</td>'
            f'<td>${r["usd"]:.2f}</td></tr>')
    billed = sum(r["usd"] for r in rows if r["kind"] == "session")
    hours = sum(r["hours"] for r in rows if r["kind"] == "session")
    foot = (f'      <tr><td></td><td><b>실제 청구</b> <span class="muted">세션 합</span></td>'
            f'<td></td><td>{hhmm(hours)}</td><td><b>${billed:.2f}</b></td></tr>')
    return "\n".join(out), foot


def write_plan(rows: list[dict]) -> None:
    body, foot = render(rows)
    s = io.open(PLAN, encoding="utf-8").read()
    head = s.index("<h2>지출 내역")
    tb0 = s.index("<tbody>", head) + len("<tbody>")
    tb1 = s.index("</tbody>", tb0)
    tf0 = s.index("<tfoot>", tb1) + len("<tfoot>")
    tf1 = s.index("</tfoot>", tf0)
    s = s[:tb0] + "\n" + body + "\n    " + s[tb1:tf0] + "\n" + foot + "\n    " + s[tf1:]
    io.open(PLAN, "w", encoding="utf-8", newline="\n").write(s)
    print(f"→ {PLAN}  (지출 {len(rows)}행 기입)")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--add-run", help="runs/<이름>/run_meta.json 을 읽어 run 행 추가")
    ap.add_argument("--label", help="--add-run 의 표시 이름")
    ap.add_argument("--add-session", help="세션 행 추가(인스턴스 가동 시간)")
    ap.add_argument("--hours", type=float, help="--add-session 의 시간")
    ap.add_argument("--rate", default="g6", choices=sorted(RATES), help="요금 종류")
    ap.add_argument("--date", default=datetime.date.today().isoformat())
    ap.add_argument("--note", default="")
    ap.add_argument("--write", action="store_true", help="계획서 표 갱신")
    args = ap.parse_args()

    resource, rate = RATES[args.rate]

    if args.add_run:
        p = os.path.join(HERE, "runs", args.add_run, "run_meta.json")
        m = json.load(open(p, encoding="utf-8"))
        h = m["elapsedSec"] / 3600
        note = args.note or f'{m.get("ok", 0)}/{m.get("docs", 0)}장'
        append({"date": args.date, "kind": "run",
                "item": args.label or args.add_run, "resource": f"{resource} · vLLM",
                "hours": round(h, 4), "usd": round(h * rate, 2), "note": note})
        print("run 행 추가:", args.label or args.add_run)

    if args.add_session:
        if args.hours is None:
            print("--add-session 에는 --hours 가 필요하다", file=sys.stderr)
            return 1
        append({"date": args.date, "kind": "session", "item": args.add_session,
                "resource": resource, "hours": round(args.hours, 4),
                "usd": round(args.hours * rate, 2), "note": args.note})
        print("세션 행 추가:", args.add_session)

    rows = load()
    report(rows)
    if args.write:
        write_plan(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
