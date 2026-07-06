"""③P0b: dropped(행 통째 드롭) 미추출행의 거부 사유 세분화.

MISSING_ROW_CLASSIFY의 dropped 부류에 대해, 품명이 든 실제 OCR 라인을 찾아
free 라인 후보 게이트(_parse_table_row_candidate 경로)를 단계별로 재현해
어느 게이트에서 죽는지 센다. 파일의 실제 경로(free/fallback)도 함께 기록
— fallback 문서의 드롭은 free 게이트가 아니라 fallback 파서 몫.

usage: ../.venv/Scripts/python.exe eval/missing_row_why.py
"""
import json
import os
import re
import sys
from collections import Counter
from difflib import SequenceMatcher

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..")))

import contract as C  # noqa: E402
from build_manifest import build_manifest  # noqa: E402
from compare_table import _align_by_content, _has_rowindex  # noqa: E402
from gt_loader import load_gt_aggregate  # noqa: E402
from replay_compare import replay_dispatch  # noqa: E402
from replay_free import _deserialize_lines  # noqa: E402
from extractors import invoice_statement_free as F  # noqa: E402

RUN_TS = os.path.join("062_20260703_095853", "thin")
TESTSET = "invoice_thin"
_WS = re.compile(r"\s+")


def _norm(s):
    return _WS.sub("", str(s or "")).lower()


def _line_text(ln):
    t = getattr(ln, "text", None)
    if t is None and isinstance(ln, dict):
        t = ln.get("text")
    if t is None and isinstance(ln, (list, tuple)):
        t = next((x for x in ln if isinstance(x, str)), "")
    return t or ""


def why_rejected(line_text: str) -> str:
    """_parse_table_row_candidate의 게이트를 순서대로 재현 → 첫 거부 사유."""
    text = F._normalize_comma_space_money_text(line_text)
    if F._is_summary_or_header_line(text):
        return "summary_header_gate"
    text = F._strip_leading_row_index(text)
    tokens = F._merge_comma_space_money_tokens(text.split())
    if len(tokens) < 3:
        return "tokens<3"
    numerics = [(i, t) for i, t in enumerate(tokens) if F._is_number_token(t)]
    if len(numerics) < 2:
        return "numerics<2"
    if numerics[0][0] == 0:
        return "leading_numeric(label없음)"
    return "accepted(다른 단계서 소실)"


def main() -> int:
    run_dir = os.path.join(C.RUNS_DIR, RUN_TS)
    snap_dir = os.path.join(run_dir, "snapshots")
    manifest = build_manifest(TESTSET)
    agg = load_gt_aggregate(
        os.path.normpath(os.path.join(C.HERE, manifest["gtAggregate"])),
        profile=manifest["kind"])
    gtkey_by_src = {s["sourceFile"]: s["gtKey"] for s in manifest["samples"] if s.get("gtKey")}

    reasons = Counter()
    by_path = Counter()
    ex = {}
    n_dropped = 0
    for f in sorted(os.listdir(snap_dir)):
        if not f.endswith(".json"):
            continue
        src = f[:-5]
        gtkey = gtkey_by_src.get(src)
        if not gtkey or gtkey not in agg:
            continue
        snap = json.load(open(os.path.join(snap_dir, f), encoding="utf-8"))
        ext_df, path = replay_dispatch(snap)
        ext_rows = ext_df.get("tableRows") or []
        gt_rows = agg[gtkey]["tableRows"]
        if bool(gt_rows) and all(_has_rowindex(r) for r in gt_rows):
            continue  # thin은 content-align — rowindex GT는 대상 아님
        pairs, gt_only, _e, _ng, _ne = _align_by_content(gt_rows, ext_rows)
        if not gt_only:
            continue
        all_ext_text = _norm(" ".join(
            " ".join(str(v) for v in r.values() if isinstance(v, (str, int, float)))
            for r in ext_rows))
        lines = [_line_text(ln) for ln in (_deserialize_lines(snap.get("ocr_lines_raw")) or [])]
        line_norms = [_norm(t) for t in lines]
        for k in gt_only:
            g = gt_rows[int(k) - 1]
            name_n = _norm(g.get("itemName"))
            if not name_n or name_n in all_ext_text:
                continue  # merged/align_fail/이름없음 — dropped만 본다
            # 품명이 든 OCR 라인 찾기 (포함 우선, 없으면 fuzzy 최고)
            hit = next((i for i, ln in enumerate(line_norms) if ln and name_n in ln), None)
            if hit is None:
                best, bi = 0.0, None
                for i, ln in enumerate(line_norms):
                    if not ln:
                        continue
                    r = SequenceMatcher(None, name_n, ln).ratio()
                    if r > best:
                        best, bi = r, i
                if best < 0.8:
                    continue  # recognition — dropped 아님
                hit = bi
            n_dropped += 1
            reason = why_rejected(lines[hit])
            reasons[reason] += 1
            by_path[path] += 1
            key = (reason, path)
            if key not in ex:
                ex[key] = {"src": src, "line": lines[hit][:120]}

    sys.stdout.reconfigure(errors="replace")
    print(f"dropped(재판정): {n_dropped}")
    print("\n[거부 사유]  * accepted = 라인 게이트는 통과 → 경로별 상위 로직에서 소실")
    for r, c in reasons.most_common():
        print(f"  {r}: {c} ({100*c/n_dropped:.1f}%)")
    print("\n[문서 경로]")
    for p, c in by_path.most_common():
        print(f"  {p}: {c} ({100*c/n_dropped:.1f}%)")
    print("\n[사유×경로 예시]")
    for (r, p), e in ex.items():
        print(f"  {r} / {p} / {e['src']}\n    {e['line']}")
    out = {"n": n_dropped, "reasons": dict(reasons), "byPath": dict(by_path)}
    json.dump(out, open(os.path.join(run_dir, "MISSING_ROW_WHY.json"), "w",
                        encoding="utf-8"), ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
