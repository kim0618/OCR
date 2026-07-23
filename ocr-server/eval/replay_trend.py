"""replay_trend — append-only KPI history for the LOCAL replay loop.

The replay loop (replay_compare.py + parser_drop_classify.py) overwrites its
sidecars every run, so each iteration's numbers are lost. This appends a
one-line summary per iteration to eval/REPLAY_TREND.md so you can watch the
loop's progress like runs/<ts>/TREND.md does for real runs.

Reads (no re-run, no scoring): the CURRENT replay_compare/<img>.json sidecars +
PARSER_DROP_CLASSIFY_replay_compare.json already written by the loop. Computes
cell%, field%, parser_drop/recognition counts, spurious — then APPENDS a row.

Usage (run right after replay_compare + parser_drop_classify):
    ../.venv/Scripts/python.exe eval/replay_trend.py --note "3G + lot fix"
    ../.venv/Scripts/python.exe eval/replay_trend.py --ts 053_20260617_142725/study --note "..."
"""
from __future__ import annotations

import argparse
import datetime as _dt
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import contract as C  # noqa: E402

TREND_PATH = os.path.join(HERE, "REPLAY_TREND.md")
HEADER = (
    "# Replay 추세 — 로컬 파서 루프 KPI 이력 (append-only)\n\n"
    "> replay_compare + parser_drop_classify 돌린 뒤 `replay_trend.py`로 한 줄 추가.\n"
    "> 실제 AWS run의 TREND.md와 별개 — 이건 **수정 파서를 스냅샷에 재실행한 로컬 채점**.\n"
    "> 파서는 디바이스 무관이라 이 수치는 GPU 프로덕션 파서 기준과 동일.\n\n"
    "| 시각 | 셀 정확도 | 필드 정확도 | parser_drop | recognition | 셀 spurious | free/fallback | 메모 |\n"
    "|---|--:|--:|--:|--:|--:|---|---|\n"
)


def _measure(study_dir: str) -> dict:
    cm = cs = fm = fs = spur = 0
    paths = {"free": 0, "fallback": 0}
    for f in sorted(glob.glob(os.path.join(study_dir, "replay_compare", "*.json"))):
        d = json.load(open(f, encoding="utf-8"))
        p = d.get("extractionPath")
        if p in paths:
            paths[p] += 1
        table = d.get("table") or {}
        counts = table.get("cellCounts")
        if isinstance(counts, dict):
            cs += int(counts.get("scored") or 0)
            cm += int(counts.get("match") or 0)
            spur += int(counts.get("spurious") or 0)
        else:
            for r in table.get("rows", []):
                for col, c in r.get("cells", {}).items():
                    if col in C.MEASUREMENT_KEYS:
                        continue
                    if c.get("spurious"):
                        spur += 1
                    if c.get("gtNorm"):
                        cs += 1
                        if c.get("status") == "match":
                            cm += 1
        fields = d.get("fields") or {}
        field_counts = fields.get("counts")
        if isinstance(field_counts, dict):
            fs += int(field_counts.get("scored") or 0)
            fm += int(field_counts.get("match") or 0)
        else:
            pf = fields.get("perField") or {}
            for _fn, c in pf.items():
                if isinstance(c, dict) and c.get("gtNorm"):
                    fs += 1
                    if c.get("status") == "match":
                        fm += 1
    pdrop = recog = None
    cls_path = os.path.join(study_dir, "PARSER_DROP_CLASSIFY_replay_compare.json")
    if os.path.isfile(cls_path):
        defs = json.load(open(cls_path, encoding="utf-8")).get("defects", [])
        pdrop = sum(1 for x in defs if x.get("class") == "parser_drop")
        recog = sum(1 for x in defs if x.get("class") == "recognition")
    return {
        "cell": (cm, cs), "field": (fm, fs), "spur": spur, "paths": paths,
        "pdrop": pdrop, "recog": recog,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ts", default=None, help="run subdir e.g. 053_..._142725/study")
    ap.add_argument("--note", default="", help="what changed this iteration")
    args = ap.parse_args()

    if args.ts:
        study_dir = os.path.join(C.RUNS_DIR, args.ts)
    else:
        run_dir = C.latest_run(C.DEFAULT_TESTSET)
        study_dir = os.path.join(run_dir, "study") if run_dir else None
    if not study_dir or not os.path.isdir(os.path.join(study_dir, "replay_compare")):
        print(f"no replay_compare/ in {study_dir} — run replay_compare.py first")
        return 1

    m = _measure(study_dir)
    cm, cs = m["cell"]; fm, fs = m["field"]
    cell_s = f"{cm}/{cs} ({100*cm/cs:.1f}%)" if cs else "-"
    field_s = f"{fm}/{fs} ({100*fm/fs:.1f}%)" if fs else "-"
    pd_s = str(m["pdrop"]) if m["pdrop"] is not None else "-"
    rc_s = str(m["recog"]) if m["recog"] is not None else "-"
    paths_s = f"{m['paths']['free']}/{m['paths']['fallback']}"
    ts = _dt.datetime.now().strftime("%m-%d %H:%M")
    note = (args.note or "").replace("|", "/")

    row = f"| {ts} | {cell_s} | {field_s} | {pd_s} | {rc_s} | {m['spur']} | {paths_s} | {note} |\n"
    if not os.path.isfile(TREND_PATH):
        open(TREND_PATH, "w", encoding="utf-8").write(HEADER)
    open(TREND_PATH, "a", encoding="utf-8").write(row)
    print(f"appended to {os.path.relpath(TREND_PATH, HERE)}:")
    print("  " + row.strip())
    return 0


if __name__ == "__main__":
    sys.exit(main())
