"""replay_gate_diff — 두 replay 사이드카(compare-스키마 디렉토리)의 게이트 판정 diff.

READ-ONLY 분석 사이드카. 파서 패치 전(base)/후(new) 의 per-sample 스코어카드를
행·셀 단위로 대조해 §3 채택 게이트를 기계 판정한다:

  - 컬럼별 GAIN(비매치→match) / REGRESSION(match→비매치, 행ID 수집) / net
  - SPURIOUS 신규 발생(행ID 수집) — GT빈칸에 새로 값 지어내기
  - 필드(perField)도 동일 대조
  - master(itemNameMaster) 회귀 = 066 §3 '기존 master 정답 훼손' 게이트와 등가

checker 가 읽는 어떤 파일도 건드리지 않는다. 산출물은 run 디렉토리의
GATE_DIFF_<base>_vs_<new>.md 하나.

    ../.venv/Scripts/python.exe eval/replay_gate_diff.py \
        --ts 066_20260709_122046/thin --testset invoice_thin \
        --base replay_compare --new replay_compare_p1
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import contract as C  # noqa: E402

BAD = {"mismatch", "ext_missing"}


def _load(path: str) -> dict | None:
    try:
        return json.load(open(path, encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _scope(run_dir: str) -> list[str] | None:
    meta = _load(os.path.join(run_dir, "run_meta.json")) or {}
    ran = meta.get("ran")
    if isinstance(ran, list) and all(isinstance(s, str) and s for s in ran):
        return list(dict.fromkeys(ran))
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ts", default=None,
                    help="run dir under runs/ (default: latest run for --testset)")
    ap.add_argument("--testset", default=C.DEFAULT_TESTSET)
    ap.add_argument("--base", default="replay_compare_base")
    ap.add_argument("--new", dest="new_dir", default="replay_compare")
    args = ap.parse_args()

    run_dir = os.path.join(C.RUNS_DIR, args.ts) if args.ts else C.latest_run(args.testset)
    if not run_dir or not os.path.isdir(run_dir):
        print(f"no run dir ({run_dir})"); return 2
    base_dir = os.path.join(run_dir, args.base)
    new_dir = os.path.join(run_dir, args.new_dir)
    for d in (base_dir, new_dir):
        if not os.path.isdir(d):
            print(f"missing dir: {d}"); return 2

    sources = _scope(run_dir)
    if sources is None:
        sources = sorted(f[:-5] for f in os.listdir(base_dir) if f.endswith(".json"))

    # column -> counters; regression/spurious row IDs
    cell_stat: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    field_stat: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    reg_rows: dict[str, list[str]] = defaultdict(list)
    spur_rows: dict[str, list[str]] = defaultdict(list)
    tot = {"cells_base_match": 0, "cells_new_match": 0, "cells_scored": 0,
           "missing_pair": 0, "docs": 0}

    for src in sources:
        b = _load(os.path.join(base_dir, src + ".json"))
        n = _load(os.path.join(new_dir, src + ".json"))
        if not b or not n:
            tot["missing_pair"] += 1
            continue
        tot["docs"] += 1
        # cells (rows are GT-aligned: same GT row order both sides)
        b_rows = (b.get("table") or {}).get("rows") or []
        n_rows = (n.get("table") or {}).get("rows") or []
        for br, nr in zip(b_rows, n_rows):
            bc, nc = br.get("cells") or {}, nr.get("cells") or {}
            for col in set(bc) | set(nc):
                bs = (bc.get(col) or {}).get("status", "none")
                ns = (nc.get(col) or {}).get("status", "none")
                if bs == "none" and ns == "none":
                    continue
                if bs in BAD or bs == "match" or ns in BAD or ns == "match":
                    tot["cells_scored"] += 1
                tot["cells_base_match"] += bs == "match"
                tot["cells_new_match"] += ns == "match"
                if bs == "match" and ns != "match":
                    cell_stat[col]["regression"] += 1
                    if len(reg_rows[col]) < 80:
                        reg_rows[col].append(f"{src}#row{br.get('rowIndex')}")
                elif bs != "match" and ns == "match":
                    cell_stat[col]["gain"] += 1
                b_sp = bool((bc.get(col) or {}).get("spurious"))
                n_sp = bool((nc.get(col) or {}).get("spurious"))
                if n_sp and not b_sp:
                    cell_stat[col]["spurious_new"] += 1
                    if len(spur_rows[col]) < 80:
                        spur_rows[col].append(f"{src}#row{br.get('rowIndex')}")
                elif b_sp and not n_sp:
                    cell_stat[col]["spurious_gone"] += 1
        # fields
        b_pf = (b.get("fields") or {}).get("perField") or {}
        n_pf = (n.get("fields") or {}).get("perField") or {}
        for label in set(b_pf) | set(n_pf):
            bs = (b_pf.get(label) or {}).get("status", "none")
            ns = (n_pf.get(label) or {}).get("status", "none")
            if bs == "match" and ns != "match":
                field_stat[label]["regression"] += 1
            elif bs != "match" and ns == "match":
                field_stat[label]["gain"] += 1

    lines = [f"# GATE DIFF — {args.ts}: {args.base} → {args.new_dir}", ""]
    lines.append(f"docs compared: **{tot['docs']}** (missing pair: {tot['missing_pair']})")
    lines.append(f"cell match: {tot['cells_base_match']} → {tot['cells_new_match']} "
                 f"(**net {tot['cells_new_match'] - tot['cells_base_match']:+d}**)")
    lines.append("")
    lines.append("## Cells by column")
    lines.append("")
    lines.append("| column | gain | regression | net | spurious_new | spurious_gone |")
    lines.append("|---|--:|--:|--:|--:|--:|")
    for col, st in sorted(cell_stat.items(),
                          key=lambda kv: -(kv[1].get("gain", 0) + kv[1].get("regression", 0))):
        g, r = st.get("gain", 0), st.get("regression", 0)
        if not (g or r or st.get("spurious_new", 0) or st.get("spurious_gone", 0)):
            continue
        lines.append(f"| {col} | {g} | {r} | **{g - r:+d}** "
                     f"| {st.get('spurious_new', 0)} | {st.get('spurious_gone', 0)} |")
    lines.append("")
    if any(field_stat.values()):
        lines.append("## Fields")
        lines.append("")
        lines.append("| field | gain | regression |")
        lines.append("|---|--:|--:|")
        for label, st in sorted(field_stat.items()):
            if st.get("gain", 0) or st.get("regression", 0):
                lines.append(f"| {label} | {st.get('gain', 0)} | {st.get('regression', 0)} |")
        lines.append("")
    # §3 게이트 기계 판정
    num_cols = ("quantity", "unitPrice", "amount", "supplyAmount", "taxAmount",
                "totalAmount", "itemCode")
    num_reg = sum(cell_stat[c].get("regression", 0) for c in num_cols)
    master_reg = cell_stat["itemNameMaster"].get("regression", 0)
    spur_new = sum(st.get("spurious_new", 0) for st in cell_stat.values())
    lines.append("## §3 gates")
    lines.append("")
    lines.append(f"- 숫자열(itemCode 포함) 회귀: **{num_reg}** {'✅ PASS' if num_reg == 0 else '❌ FAIL'}")
    lines.append(f"- master(itemNameMaster) 회귀: **{master_reg}** {'✅ PASS' if master_reg == 0 else '❌ FAIL'}")
    lines.append(f"- spurious 신규: **{spur_new}** {'✅ PASS' if spur_new == 0 else '❌ FAIL'}")
    lines.append("")
    if reg_rows:
        lines.append("### Regression row IDs (≤80/col)")
        lines.append("")
        for col, ids in sorted(reg_rows.items()):
            lines.append(f"- **{col}** ({cell_stat[col].get('regression', 0)}): " + ", ".join(ids[:80]))
        lines.append("")
    if spur_rows:
        lines.append("### New spurious row IDs (≤80/col)")
        lines.append("")
        for col, ids in sorted(spur_rows.items()):
            lines.append(f"- **{col}** ({cell_stat[col].get('spurious_new', 0)}): " + ", ".join(ids[:80]))
        lines.append("")

    md = "\n".join(lines)
    out = os.path.join(run_dir, f"GATE_DIFF_{args.base}_vs_{args.new_dir}.md")
    open(out, "w", encoding="utf-8").write(md)
    sys.stdout.reconfigure(errors="replace")
    print(md)
    print(f"\n[written] {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
