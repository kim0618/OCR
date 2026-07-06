"""③P0: 미추출 GT행 전수 분류 — ②매칭 다음 최대 레버(미추출 37.4%)의 설계 진단.

thin replay에서 GT행과 정렬되지 못한(gt-only) 행을 4부류로 나눈다:
  recognition : GT 품명이 OCR 텍스트에 없음 → 인식-bound (③이 못 고침, 파인튜닝 몫)
  merged      : GT 품명이 '정렬된 다른 ext행' 안에 붙어 있음 → 행 병합/blob (분리 대상)
  align_fail  : GT 품명이 '미정렬 ext행(ext-only)'에 있음 → 행은 만들었는데 셀이 어긋나
                content-align(0.30)이 못 붙임 → 2D 컬럼 재배정 대상
  dropped     : 품명이 OCR엔 있는데 어떤 ext행에도 없음 → 파서가 줄을 통째로 버림
                (라벨빔 등, 행 생성 자체 복구 대상)

usage: ../.venv/Scripts/python.exe eval/missing_row_classify.py
출력: runs/<ts>/thin/MISSING_ROW_CLASSIFY.{md,json} (사이드카, checker-safe)
"""
import json
import os
import re
import sys
from collections import Counter, defaultdict
from difflib import SequenceMatcher

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import contract as C  # noqa: E402
from build_manifest import build_manifest  # noqa: E402
from compare_table import _align_by_content, _align_by_rowindex, _has_rowindex  # noqa: E402
from gt_loader import load_gt_aggregate  # noqa: E402
from replay_compare import replay_dispatch  # noqa: E402
from replay_free import _deserialize_lines  # noqa: E402

RUN_TS = os.path.join("062_20260703_095853", "thin")
TESTSET = "invoice_thin"

_WS = re.compile(r"\s+")


def _norm(s) -> str:
    return _WS.sub("", str(s or "")).lower()


def _row_text(r) -> str:
    return _norm(" ".join(str(v) for v in r.values() if isinstance(v, (str, int, float))))


def _in_ocr(name_n: str, full_n: str, line_ns: list) -> bool:
    """norm 품명이 OCR에 있나: 전문 포함 or 어느 라인과 유사도>=0.8."""
    if not name_n:
        return False
    if name_n in full_n:
        return True
    for ln in line_ns:
        if not ln:
            continue
        if name_n in ln:
            return True
        if SequenceMatcher(None, name_n, ln).ratio() >= 0.8:
            return True
    return False


def main() -> int:
    run_dir = os.path.join(C.RUNS_DIR, RUN_TS)
    snap_dir = os.path.join(run_dir, "snapshots")
    manifest = build_manifest(TESTSET)
    agg = load_gt_aggregate(
        os.path.normpath(os.path.join(C.HERE, manifest["gtAggregate"])),
        profile=manifest["kind"])
    gtkey_by_src = {s["sourceFile"]: s["gtKey"] for s in manifest["samples"] if s.get("gtKey")}

    cnt = Counter()
    samples = defaultdict(list)
    per_src = Counter()
    n_gt_rows = n_missing = 0
    for f in sorted(os.listdir(snap_dir)):
        if not f.endswith(".json"):
            continue
        src = f[:-5]
        gtkey = gtkey_by_src.get(src)
        if not gtkey or gtkey not in agg:
            continue
        snap = json.load(open(os.path.join(snap_dir, f), encoding="utf-8"))
        ext_df, _ = replay_dispatch(snap)
        ext_rows = ext_df.get("tableRows") or []
        gt_rows = agg[gtkey]["tableRows"]
        n_gt_rows += len(gt_rows)
        use_rowindex = bool(gt_rows) and all(_has_rowindex(r) for r in gt_rows)
        if use_rowindex:
            pairs, gt_only, _e, _ng, _ne = _align_by_rowindex(gt_rows, ext_rows)
        else:
            pairs, gt_only, _e, _ng, _ne = _align_by_content(gt_rows, ext_rows)
        if not gt_only:
            continue
        paired_ids = {id(e) for _k, _g, e in pairs}
        paired_texts = [_row_text(e) for _k, _g, e in pairs]
        unpaired_texts = [_row_text(e) for e in ext_rows if id(e) not in paired_ids]
        full_n = _norm(snap.get("full_text", ""))
        line_ns = []
        try:
            for ln in _deserialize_lines(snap.get("ocr_lines_raw")) or []:
                t = getattr(ln, "text", None)
                if t is None and isinstance(ln, dict):
                    t = ln.get("text")
                if t is None and isinstance(ln, (list, tuple)):
                    t = next((x for x in ln if isinstance(x, str)), "")
                line_ns.append(_norm(t))
        except Exception:
            pass

        # gt_only 인덱스 → 실제 GT행 (aligner와 같은 키 공간)
        if use_rowindex:
            from compare_table import _index as _idx
            gt_by = _idx(gt_rows)
            missing = [gt_by[k] for k in gt_only if k in gt_by]
        else:
            missing = [gt_rows[int(k) - 1] for k in gt_only]

        for g in missing:
            n_missing += 1
            name_n = _norm(g.get("itemName"))
            if not _in_ocr(name_n, full_n, line_ns):
                cls = "recognition"
            elif any(name_n in t for t in paired_texts):
                cls = "merged"
            elif any(name_n in t for t in unpaired_texts) or any(
                    SequenceMatcher(None, name_n, t).ratio() >= 0.5 for t in unpaired_texts if t):
                cls = "align_fail"
            else:
                cls = "dropped"
            cnt[cls] += 1
            per_src[src] += 1
            if len(samples[cls]) < 15:
                samples[cls].append({"src": src, "itemName": g.get("itemName"),
                                     "amount": g.get("amount")})

    out = {"gtRows": n_gt_rows, "missing": n_missing, "classes": dict(cnt),
           "samples": {k: v for k, v in samples.items()},
           "topSrc": per_src.most_common(15)}
    jp = os.path.join(run_dir, "MISSING_ROW_CLASSIFY.json")
    json.dump(out, open(jp, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    lines = [f"# Missing-row classification — {RUN_TS}", "",
             f"GT rows {n_gt_rows} · 미추출(gt-only) {n_missing} "
             f"({100*n_missing/n_gt_rows:.1f}%)", "",
             "| class | 뜻 | count | 미추출 중 % |", "|---|---|--:|--:|"]
    KO = {"recognition": "품명이 OCR에 없음(인식-bound, ③불가)",
          "merged": "정렬된 다른 행에 붙음(병합/blob → 분리)",
          "align_fail": "ext행은 있는데 정렬 실패(셀 어긋남 → 2D 재배정)",
          "dropped": "OCR엔 있는데 행 통째 드롭(행 생성 복구)"}
    for k in ("align_fail", "merged", "dropped", "recognition"):
        c = cnt.get(k, 0)
        lines.append(f"| {k} | {KO[k]} | {c} | {100*c/n_missing:.1f}% |" if n_missing else "")
    lines += ["", "## 샘플", ""]
    for k in ("align_fail", "merged", "dropped", "recognition"):
        lines.append(f"### {k}")
        for s in samples.get(k, [])[:8]:
            lines.append(f"- `{s['src']}` {s['itemName']} (amt {s['amount']})")
        lines.append("")
    mp = os.path.join(run_dir, "MISSING_ROW_CLASSIFY.md")
    open(mp, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    sys.stdout.reconfigure(errors="replace")
    print(f"gtRows={n_gt_rows} missing={n_missing}")
    for k in ("align_fail", "merged", "dropped", "recognition"):
        print(f"  {k}: {cnt.get(k,0)} ({100*cnt.get(k,0)/n_missing:.1f}%)")
    print(f"[written] {mp}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
