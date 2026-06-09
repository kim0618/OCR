"""report — render runs/<ts>/report.md from metrics.json + compare/*.json.

Human-facing: hypothesis banner (small sample), overall + free/fallback, per-field
table (weakest first), bucket totals, slices, and failing GT-vs-extraction examples
side by side.

CLI: python eval/report.py [--ts <run_ts>] [--examples N]
"""

from __future__ import annotations

import argparse
import glob
import json
import os
from typing import Any

import contract as C


def _pct(a: float | None) -> str:
    return "n/a" if a is None else f"{a * 100:.1f}%"


def _load(run_dir: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    metrics = json.load(open(os.path.join(run_dir, "metrics.json"), encoding="utf-8"))
    compares = [json.load(open(p, encoding="utf-8"))
                for p in sorted(glob.glob(os.path.join(run_dir, "compare", "*.json")))]
    return metrics, compares


def render_report(run_dir: str, examples: int = 12) -> str:
    m, compares = _load(run_dir)
    L: list[str] = []
    L.append(f"# Eval Report — run {m['runTs']}")
    L.append("")
    L.append(f"> ⚠️ **HYPOTHESIS, not a verdict.** {m['sampleCount']} samples = infrastructure"
             f" check, not an accuracy judgement (plan §8). Numbers are signal to direct rule"
             f" work, not a release gate.")
    L.append("")

    of, oc = m["overall"]["field"], m["overall"]["cell"]
    L.append("## Overall")
    L.append("")
    L.append("| metric | scored | match | accuracy |")
    L.append("|---|---:|---:|---:|")
    L.append(f"| field (scalar) | {of['scored']} | {of['match']} | {_pct(of['accuracy'])} |")
    L.append(f"| cell (table) | {oc['scored']} | {oc['match']} | {_pct(oc['accuracy'])} |")
    L.append("")

    L.append("## By extraction path (free vs fallback)")
    L.append("")
    L.append("| path | field acc | cell acc |")
    L.append("|---|---:|---:|")
    for p, v in m["byPath"].items():
        L.append(f"| {p} | {_pct(v['field']['accuracy'])} | {_pct(v['cell']['accuracy'])} |")
    L.append("")

    es = m["editedSplit"]
    L.append("## Edited vs non-edited GT fields")
    L.append("")
    L.append("| group | scored | match | accuracy |")
    L.append("|---|---:|---:|---:|")
    for g in ("edited", "nonEdited"):
        v = es[g]
        L.append(f"| {g} | {v['scored']} | {v['match']} | {_pct(v['accuracy'])} |")
    L.append("> Mismatches on `edited=true` fields are where human-corrected GT diverges from"
             " raw-ish extraction — expected, and the main rule-boost target.")
    L.append("")

    L.append("## Per-field accuracy (weakest first)")
    L.append("")
    L.append("| field | scored | match | mismatch | miss | accuracy |")
    L.append("|---|---:|---:|---:|---:|---:|")
    rows = sorted(
        m["perField"].items(),
        key=lambda kv: (kv[1]["accuracy"] if kv[1]["accuracy"] is not None else 1.0),
    )
    for label, v in rows:
        L.append(f"| {label} | {v['scored']} | {v['match']} | {v['mismatch']} "
                 f"| {v['ext_missing']} | {_pct(v['accuracy'])} |")
    L.append("")

    b = m["buckets"]
    L.append("## Defect buckets (heuristic)")
    L.append("")
    L.append(f"- recognition (A): **{b['recognition']}**  ·  structure (B): **{b['structure']}**"
             f"  ·  layout: **{b['layout']}**  ·  preprocessing: **{b['preprocessing']}**")
    L.append("")

    L.append("## Slices")
    L.append("")
    for sname, groups in m["slices"].items():
        L.append(f"### {sname}")
        L.append("")
        L.append("| group | scored | match | accuracy |")
        L.append("|---|---:|---:|---:|")
        for g, v in sorted(groups.items(), key=lambda kv: str(kv[0])):
            L.append(f"| {g} | {v['scored']} | {v['match']} | {_pct(v['accuracy'])} |")
        L.append("")

    L.append("## Failing examples (GT vs extraction)")
    L.append("")
    shown = 0
    for d in compares:
        src = d["sourceFile"]
        defects = []
        for label, info in d["fields"]["perField"].items():
            if info["status"] in ("mismatch", "ext_missing"):
                defects.append((f"field:{label}", info["status"], info["gt"], info["ext"]))
        for row in d["table"]["rows"]:
            for ck, cell in row["cells"].items():
                if cell["status"] in ("mismatch", "ext_missing"):
                    defects.append((f"row{row['rowIndex']}:{ck}", cell["status"], cell["gt"], cell["ext"]))
        if not defects:
            continue
        L.append(f"### {src} ({d.get('extractionPath')})")
        L.append("")
        L.append("| location | status | GT | extracted |")
        L.append("|---|---|---|---|")
        for loc, st, gt, ext in defects:
            if shown >= examples:
                break
            gt_s = (gt or "").replace("|", "\\|")[:60]
            ext_s = (ext or "").replace("|", "\\|")[:60]
            L.append(f"| {loc} | {st} | {gt_s} | {ext_s} |")
            shown += 1
        L.append("")
        if shown >= examples:
            L.append(f"_… truncated at {examples} examples._")
            break

    text = "\n".join(L) + "\n"
    out_path = os.path.join(run_dir, "report.md")
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return out_path


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--ts", default=None)
    ap.add_argument("--examples", type=int, default=12)
    args = ap.parse_args()
    run_dir = (os.path.join(C.RUNS_DIR, args.ts) if args.ts
               else sorted(p for p in glob.glob(os.path.join(C.RUNS_DIR, "*")) if os.path.isdir(p))[-1])
    path = render_report(run_dir, args.examples)
    print(f"wrote {path}")
