"""AWS eval / fine-tune run history (append-only JSONL -> self-contained HTML).

The JSONL is the source of truth.  Producers may omit fields they cannot know;
the renderer keeps old rows compatible and never invents missing duration/cost.

Cost is an *execution estimate*, not the AWS invoice:

    estimatedCostUsd = elapsedSec / 3600 * hourlyUsd

Set ``AWS_EC2_HOURLY_USD`` (and optionally ``AWS_INSTANCE_TYPE``,
``AWS_REGION``, ``AWS_PURCHASE_OPTION``) on the EC2 host.  The rate is copied
into every row, so later AWS price changes cannot rewrite historical estimates.
"""
from __future__ import annotations

import argparse
import datetime
import html
import json
import os
from typing import Any

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HERE, "RUN_HISTORY.jsonl")
OUT = os.path.join(HERE, "RUN_HISTORY.html")


def _now() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")


def _float(value: Any) -> float | None:
    try:
        return float(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def _enrich_aws(fields: dict[str, Any]) -> None:
    """Snapshot optional EC2 pricing context and calculate run estimate."""
    env_map = {
        "instanceType": "AWS_INSTANCE_TYPE",
        "region": "AWS_REGION",
        "purchaseOption": "AWS_PURCHASE_OPTION",
    }
    for key, env in env_map.items():
        if fields.get(key) is None and os.environ.get(env):
            fields[key] = os.environ[env]
    if fields.get("hourlyUsd") is None:
        fields["hourlyUsd"] = _float(os.environ.get("AWS_EC2_HOURLY_USD"))
    if fields.get("estimatedCostUsd") is None:
        sec, rate = _float(fields.get("elapsedSec")), _float(fields.get("hourlyUsd"))
        if sec is not None and rate is not None:
            fields["estimatedCostUsd"] = round(sec / 3600 * rate, 4)


def record(kind: str, **fields: Any) -> None:
    """Append one event and refresh HTML.  History failure never breaks a run."""
    try:
        _enrich_aws(fields)
        row = {"kind": kind, "when": _now()}
        row.update({k: v for k, v in fields.items() if v is not None})
        with open(LOG, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        render_html()
    except Exception as exc:
        print(f"  (run_history 기록 실패: {exc})")


def _load() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if os.path.exists(LOG):
        with open(LOG, encoding="utf-8") as fh:
            for line in fh:
                try:
                    if line.strip():
                        rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return rows


def _h(value: Any) -> str:
    return html.escape(str(value), quote=True)


def _dur(sec: Any) -> str:
    value = _float(sec)
    if value is None:
        return "기록 없음"
    seconds = max(0, int(round(value)))
    if seconds >= 3600:
        return f"{seconds // 3600}시간 {(seconds % 3600) // 60}분"
    return f"{seconds // 60}분 {seconds % 60}초"


def _rate(images: Any, sec: Any) -> str:
    seconds = _float(sec)
    count = _float(images)
    if count is None or seconds is None or seconds <= 0:
        return "-"
    return f"{count / (seconds / 3600):,.0f}장/h"


def _num(value: Any, suffix: str = "") -> str:
    if value is None:
        return "-"
    if isinstance(value, int):
        return f"{value:,}{suffix}"
    return f"{_h(value)}{suffix}"


def _pct(value: Any) -> str:
    number = _float(value)
    return "-" if number is None else f"{number:.1f}%"


def _best_acc(value: Any) -> str:
    """Render validation accuracy consistently without changing stored precision."""
    number = _float(value)
    return "-" if number is None else f"{number:.3f}"


def _signed(value: Any, suffix: str = "%p") -> str:
    number = _float(value)
    return "-" if number is None else f"{number:+.1f}{suffix}"


def _cost(row: dict[str, Any]) -> str:
    value = _float(row.get("estimatedCostUsd"))
    if value is None:
        return "-"
    context = " · ".join(str(x) for x in (
        row.get("instanceType"), row.get("purchaseOption"), row.get("region")
    ) if x)
    title = f" title='{_h(context)}'" if context else ""
    return f"<span{title}>${value:,.2f}</span>"


def _criteria(row: dict[str, Any]) -> str:
    return _h(row.get("criteria") or "기록 없음")


def _epoch_text(row: dict[str, Any]) -> tuple[str, str]:
    completed = row.get("epochsCompleted", row.get("epochs"))
    planned = row.get("epochsPlanned")
    total = _num(completed)
    if planned is not None and planned != completed:
        total = f"{total} <span class='muted'>/ 계획 {_num(planned)}</span>"
    best = _num(row.get("bestEpoch"))
    return total, best


def _delta_summary(row: dict[str, Any], compact: bool = False) -> str:
    chunks: list[str] = []
    deltas = row.get("sliceDeltas") if isinstance(row.get("sliceDeltas"), dict) else {}
    preferred = ("품명", "숫자", "한글", "전체")
    used: set[str] = set()
    for label in preferred:
        if label in deltas:
            chunks.append(f"{_h(label)} {_signed(deltas[label])}")
            used.add(label)
    if not compact:
        for label, value in deltas.items():
            if label not in used:
                chunks.append(f"{_h(label)} {_signed(value)}")
    if not chunks and row.get("overallDeltaPp") is not None:
        chunks.append(f"전체 {_signed(row.get('overallDeltaPp'))}")
    if row.get("netChange") is not None:
        net = int(row["netChange"])
        chunks.append(f"순증 {net:+,}건")
    return " · ".join(chunks) if chunks else "-"


def render_html() -> str:
    rows = _load()
    ev = [r for r in rows if r.get("kind") == "eval"]
    ft = [r for r in rows if r.get("kind") == "finetune"]
    adopted_ts = {r.get("ts") for r in rows if r.get("kind") == "adopt"}
    for row in ft:
        if row.get("ts") in adopted_ts:
            row["adopted"] = 1

    def eval_rows() -> str:
        out: list[str] = []
        total_images = 0
        timed_images = 0
        total_seconds = 0.0
        known_cost = 0.0
        cost_runs = 0
        aws_runs = 0
        replay_runs = 0
        for index, row in enumerate(ev, 1):
            images = int(row.get("images") or 0)
            seconds = _float(row.get("elapsedSec"))
            is_replay = row.get("runType") == "snapshot-replay"
            if is_replay:
                replay_runs += 1
                type_text = "<span class='muted'>스냅샷 재평가</span>"
            else:
                aws_runs += 1
                type_text = "AWS OCR"
                total_images += images
                if seconds is not None:
                    timed_images += images
                    total_seconds += seconds
                cost = _float(row.get("estimatedCostUsd"))
                if cost is not None:
                    known_cost += cost
                    cost_runs += 1
            item_title = ""
            if row.get("itemNameScored") is not None:
                item_title = (f" title='{_num(row.get('itemNameMatch'))} / "
                              f"{_num(row.get('itemNameScored'))} 일치'")
            master_title = ""
            if row.get("itemNameMasterScored") is not None:
                master_title = (f" title='{_num(row.get('itemNameMasterMatch'))} / "
                                f"{_num(row.get('itemNameMasterScored'))} 일치'")
            learn_a_title = ""
            if row.get("learnAScored") is not None:
                learn_a_title = (f" title='{_num(row.get('learnAMatch'))} / "
                                 f"{_num(row.get('learnAScored'))} 품명 일치'")
            learn_b_title = ""
            if row.get("learnBScored") is not None:
                learn_b_title = (f" title='{_num(row.get('learnBMatch'))} / "
                                 f"{_num(row.get('learnBScored'))} 품명 일치'")
            out.append(
                f"<tr><td>{index}</td><td>{_h(row.get('when','-'))}</td>"
                f"<td><code>{_h(row.get('ts','-'))}</code></td>"
                f"<td>{type_text}</td>"
                f"<td>{_num(row.get('images'),'장')}</td><td>{_dur(seconds)}</td>"
                f"<td>{_rate(images,seconds)}</td><td>{_pct(row.get('field'))}</td>"
                f"<td>{_pct(row.get('cell'))}</td>"
                f"<td{item_title}>{_pct(row.get('itemName'))}</td>"
                f"<td{master_title}>{_pct(row.get('itemNameMaster'))}</td>"
                f"<td{learn_a_title}>{_pct(row.get('learnA'))}</td>"
                f"<td{learn_b_title}>{_pct(row.get('learnB'))}</td>"
                f"<td>{_cost(row)}</td></tr>")
        rate_note = "" if timed_images == total_images else f" <span class='muted'>(시간 기록 {timed_images:,}장 기준)</span>"
        cost_note = "" if cost_runs == aws_runs else f" <span class='muted'>({cost_runs}/{aws_runs} AWS run)</span>"
        replay_note = (f" <span class='muted'>(스냅샷 재평가 {replay_runs} run 제외)</span>"
                       if replay_runs else "")
        out.append(
            f"<tr class='tot'><td colspan='4'>AWS OCR 누계 ({aws_runs} run){replay_note}</td><td>{total_images:,}장</td>"
            f"<td>{_dur(total_seconds) if total_seconds else '-'}</td>"
            f"<td>{_rate(timed_images,total_seconds)}{rate_note}</td><td colspan='6'></td>"
            f"<td>{('$' + format(known_cost, ',.2f')) if cost_runs else '-'}{cost_note}</td></tr>")
        return "".join(out)

    def ft_rows() -> str:
        out: list[str] = []
        total_images = 0
        total_seconds = 0.0
        known_cost = 0.0
        cost_runs = 0
        for index, row in enumerate(ft, 1):
            images = int(row.get("images") or 0)
            seconds = _float(row.get("elapsedSec"))
            total_images += images
            total_seconds += seconds or 0
            cost = _float(row.get("estimatedCostUsd"))
            if cost is not None:
                known_cost += cost
                cost_runs += 1
            adopted = row.get("adopted")
            adopted_text = ("<span class='up'>채택</span>" if adopted in (1, True, "1")
                            else "<span class='muted'>미채택</span>" if adopted is not None else "-")
            total_ep, best_ep = _epoch_text(row)
            out.append(
                f"<tr><td>{index}</td><td>{_h(row.get('when','-'))}</td>"
                f"<td><code>{_h(row.get('ts','-'))}</code></td>"
                f"<td><code class='b'>{_h(row.get('base','official'))}</code></td>"
                f"<td>{_num(row.get('images'),'장')}</td>"
                f"<td>{total_ep}</td><td>{best_ep}</td>"
                f"<td>{_best_acc(row.get('bestAcc'))}</td>"
                f"<td>{_dur(seconds)}</td><td>{_cost(row)}</td><td>{adopted_text}</td></tr>")
        cost_note = "" if cost_runs == len(ft) else f" <span class='muted'>({cost_runs}/{len(ft)} run)</span>"
        out.append(
            f"<tr class='tot'><td colspan='4'>누계 ({len(ft)} run)</td><td>{total_images:,}장</td>"
            f"<td colspan='3'></td><td>{_dur(total_seconds) if total_seconds else '-'}</td>"
            f"<td>{('$' + format(known_cost, ',.2f')) if cost_runs else '-'}{cost_note}</td><td></td></tr>")
        return "".join(out)

    def lineage() -> str:
        children: dict[str, list[dict[str, Any]]] = {}
        for row in ft:
            children.setdefault(row.get("base") or "official", []).append(row)
        if not ft:
            return "<div class='muted'>아직 파인튜닝 없음</div>"

        visited: set[str] = set()

        def node(name: str, depth: int) -> str:
            lines: list[str] = []
            for row in children.get(name, []):
                ts = str(row.get("ts", "?"))
                edge = f"{name}->{ts}"
                if edge in visited:
                    continue
                visited.add(edge)
                adopted = row.get("adopted") in (1, True, "1")
                mark = "<span class='up'>★</span>" if adopted else "<span class='muted'>✗</span>"
                css_class = "adopt" if adopted else "rej"
                pad = "&nbsp;&nbsp;&nbsp;&nbsp;" * depth
                total_ep, best_ep = _epoch_text(row)
                ep = f"전체 {total_ep} · 최고 ep{best_ep} · acc {_best_acc(row.get('bestAcc'))}"
                detail = f"기준: {_criteria(row)}"
                delta = _delta_summary(row, compact=True)
                if delta != "-":
                    detail += f" · {delta}"
                lines.append(
                    f"<div class='ln {css_class}'>{pad}└─ {mark} <code>{_h(ts)}</code> "
                    f"<span class='muted'>({ep})</span><div class='meta'>{pad}&nbsp;&nbsp;&nbsp;{detail}</div></div>")
                lines.append(node(ts, depth + 1))
            return "".join(lines)

        roots = node("official", 1)
        # Preserve visibility for legacy/mistyped parents instead of silently
        # dropping those runs from the tree.
        known_nodes = {str(r.get("ts")) for r in ft}
        orphans = [r for r in ft if str(r.get("base") or "official") not in known_nodes | {"official"}]
        orphan_html = ""
        if orphans:
            orphan_html = "<div class='warn'>부모를 찾지 못한 계보</div>" + "".join(
                f"<div class='ln'>└─ <code>{_h(r.get('ts','?'))}</code> (부모 {_h(r.get('base'))})</div>"
                for r in orphans)
        return "<div class='ln'><b>official</b> (공식 pretrained)</div>" + roots + orphan_html

    css = """
:root{--bg:#f6f8fa;--card:#fff;--line:#d0d7de;--fg:#1f2328;--muted:#59636e;--up:#1a7f37;--head:#eef1f4;--warn:#9a6700}
@media(prefers-color-scheme:dark){:root{--bg:#0d1117;--card:#161b22;--line:#30363d;--fg:#e6edf3;--muted:#8b949e;--head:#21262d;--warn:#d29922}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font-family:'Segoe UI','Malgun Gothic',system-ui,sans-serif;font-size:14px;padding:24px}
h1{font-size:20px;margin:0 0 4px}h2{font-size:15px;margin:22px 0 8px}.gen{color:var(--muted);font-size:12.5px;margin-bottom:8px}
section{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 18px;max-width:1600px;overflow-x:auto}
table{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums}th,td{padding:7px 10px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}
th:nth-child(-n+3),td:nth-child(-n+3),td.left{text-align:left}th{color:var(--muted);font-weight:600;font-size:12.5px;background:var(--head)}
code{background:var(--head);border:1px solid var(--line);border-radius:5px;padding:1px 5px;font-size:11.5px}.tot{font-weight:700;background:var(--head)}
.eval-table th,.eval-table td{padding-left:7px;padding-right:7px}.eval-table code{font-size:11px}
.up{color:var(--up);font-weight:600}.muted{color:var(--muted)}.warn{color:var(--warn);font-weight:600;margin-top:10px}code.b{background:transparent;border:0;padding:0;color:var(--muted)}
.tree .ln{font-family:'Consolas','D2Coding',monospace;font-size:12.5px;line-height:1.9;white-space:nowrap}.tree .meta{color:var(--muted);padding-left:1.2em}.tree .adopt>code{border-color:var(--up)}
"""
    document = f"""<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AWS 실행 이력 (eval / 파인튜닝)</title><style>{css}</style></head><body>
<h1>AWS 실행 이력</h1><div class="gen">생성 {_now()} · eval {len(ev)} run · 파인튜닝 {len(ft)} run · AWS 금액은 실행시간 기준 예상요금</div>
<h2>① eval (측정 + 크롭 수확)</h2><section><table class="eval-table"><thead><tr>
<th>#</th><th>일시</th><th>run</th><th>실행 유형</th><th>처리 장수</th><th>소요 시간</th><th>처리/h</th><th>필드</th><th>셀</th><th>품명 Base<br><span class="muted">(매칭 전)</span></th><th>품명 Master<br><span class="muted">(매칭 후)</span></th><th>Learn A 품명<br><span class="muted">(held-out)</span></th><th>Learn B 품명<br><span class="muted">(full 상한)</span></th><th>AWS 요금</th>
</tr></thead><tbody>{eval_rows()}</tbody></table></section>
<h2>② 파인튜닝 (모델 학습)</h2><section><table><thead><tr>
<th>#</th><th>일시</th><th>run</th><th>base</th><th>학습 크롭</th><th>전체 반복</th><th>최고 epoch</th><th>best acc</th><th>소요 시간</th><th>AWS 예상요금</th><th>채택</th>
</tr></thead><tbody>{ft_rows()}</tbody></table></section>
<h2>③ 모델 계보 — 무엇을 기준으로 얼마나 변했는지</h2><section class="tree">{lineage()}
<div class="gen" style="margin-top:10px">★=채택 · ✗=미채택. 증감은 동일 held-out 기준 파인튜닝−base 정확일치율(%p).</div></section>
</body></html>"""
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(document)
    return OUT


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--record", choices=["eval", "finetune"], default=None)
    parser.add_argument("--ts", default=None)
    parser.add_argument("--run-type", default=None, choices=["aws-ocr", "snapshot-replay"])
    parser.add_argument("--images", type=int, default=None)
    parser.add_argument("--elapsed", type=float, default=None)
    parser.add_argument("--field", type=float, default=None)
    parser.add_argument("--cell", type=float, default=None)
    parser.add_argument("--item-name", type=float, default=None)
    parser.add_argument("--item-name-match", type=int, default=None)
    parser.add_argument("--item-name-scored", type=int, default=None)
    parser.add_argument("--item-name-master", type=float, default=None)
    parser.add_argument("--item-name-master-match", type=int, default=None)
    parser.add_argument("--item-name-master-scored", type=int, default=None)
    parser.add_argument("--learn-a", type=float, default=None)
    parser.add_argument("--learn-a-match", type=int, default=None)
    parser.add_argument("--learn-a-scored", type=int, default=None)
    parser.add_argument("--learn-b", type=float, default=None)
    parser.add_argument("--learn-b-match", type=int, default=None)
    parser.add_argument("--learn-b-scored", type=int, default=None)
    parser.add_argument("--epochs", type=int, default=None, help="legacy alias for completed epochs")
    parser.add_argument("--epochs-planned", type=int, default=None)
    parser.add_argument("--epochs-completed", type=int, default=None)
    parser.add_argument("--best-epoch", type=int, default=None)
    parser.add_argument("--best-acc", default=None)
    parser.add_argument("--criteria", default=None)
    parser.add_argument("--overall-delta-pp", type=float, default=None)
    parser.add_argument("--slice-deltas", default=None, help="JSON object, e.g. {\"품명\":2.1,\"숫자\":0}")
    parser.add_argument("--net-change", type=int, default=None)
    parser.add_argument("--adopted", default=None)
    parser.add_argument("--base", default=None)
    parser.add_argument("--instance-type", default=None)
    parser.add_argument("--region", default=None)
    parser.add_argument("--purchase-option", default=None)
    parser.add_argument("--hourly-usd", type=float, default=None)
    parser.add_argument("--cost-usd", type=float, default=None)
    args = parser.parse_args()
    if args.record:
        deltas = json.loads(args.slice_deltas) if args.slice_deltas else None
        record(
            args.record, ts=args.ts, runType=args.run_type, images=args.images, elapsedSec=args.elapsed,
            field=args.field, cell=args.cell, itemName=args.item_name,
            itemNameMatch=args.item_name_match, itemNameScored=args.item_name_scored,
            itemNameMaster=args.item_name_master,
            itemNameMasterMatch=args.item_name_master_match,
            itemNameMasterScored=args.item_name_master_scored,
            learnA=args.learn_a, learnAMatch=args.learn_a_match,
            learnAScored=args.learn_a_scored,
            learnB=args.learn_b, learnBMatch=args.learn_b_match,
            learnBScored=args.learn_b_scored,
            epochs=args.epochs, epochsPlanned=args.epochs_planned,
            epochsCompleted=args.epochs_completed, bestEpoch=args.best_epoch,
            bestAcc=args.best_acc, criteria=args.criteria,
            overallDeltaPp=args.overall_delta_pp, sliceDeltas=deltas,
            netChange=args.net_change, adopted=args.adopted, base=args.base,
            instanceType=args.instance_type, region=args.region,
            purchaseOption=args.purchase_option, hourlyUsd=args.hourly_usd,
            estimatedCostUsd=args.cost_usd,
        )
        print(f"[run_history] recorded {args.record} -> {OUT}")
    else:
        print(f"[run_history] rendered -> {render_html()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
