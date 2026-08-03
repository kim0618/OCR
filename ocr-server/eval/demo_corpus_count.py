"""demo_corpus_count — 타깃 품명의 <학습 크롭>이 코퍼스에 실제로 몇 장 있는지 센다.

판정 쪽 모수(기준셋 9,001)는 demo_target_basis.py 로 로컬에서 세지만, 학습 크롭은
코퍼스(AWS: finetune_corpus/)에만 있어 여기서만 셀 수 있다. GPU 불필요, 파일만 읽는다.

세는 범위 = build_demo_dataset 과 동일한 수집 규칙:
  failure 풀  ledger.jsonl 에서 column=itemName · labelForm=raw · matchRatio≥0.7,
              기준셋(replay_sources) 제외 → crops/<hash>.jpg
  정답 풀     labels_correct.txt (crops_correct/) — 2단계 타깃(원래 읽히던 품명)은
              failure 풀에 없으므로 이쪽에서 나온다. balance 메타에 src 가 있으면
              기준셋 출처 여부까지 구분해 준다.
라벨 매칭은 공백 제거 후 '정확일치'와 '포함(변형)'을 따로 센다 — 변형까지 모으면
크롭이 몇 배가 되므로 학습량 결정에 그 차이가 중요하다.

    python eval/demo_corpus_count.py --targets "디아세렌캡슐"
    python eval/demo_corpus_count.py --targets "디아세렌캡슐,비탁스캡슐" --json out.json
    python eval/demo_corpus_count.py --top 20        # 후보 자동(기준셋 전출현 오독 품명)
"""
from __future__ import annotations

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from finetune_ledger import CORPUS_DIR, CORPUS_PATH  # noqa: E402
from finetune_crops import load_labels, crop_name  # noqa: E402

FAIL_LABELS = os.path.join(CORPUS_DIR, "labels.txt")
BAL_LABELS = os.path.join(CORPUS_DIR, "labels_correct.txt")
BAL_META = os.path.join(CORPUS_DIR, "labels_correct.meta.jsonl")
REPLAY_SRC = os.path.join(CORPUS_DIR, "replay_sources.txt")


def _bal_meta() -> dict[str, dict]:
    """정답 풀 사이드카(path → {column, src}). 없으면 빈 dict."""
    out: dict[str, dict] = {}
    for cand in (BAL_META, os.path.join(CORPUS_DIR, "labels_correct_meta.jsonl")):
        if not os.path.exists(cand):
            continue
        for ln in open(cand, encoding="utf-8"):
            try:
                rec = json.loads(ln)
            except json.JSONDecodeError:
                continue
            if rec.get("path"):
                out[rec["path"]] = rec
        break
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--targets", required=True, help="세어볼 품명(콤마 구분)")
    ap.add_argument("--min-match", type=float, default=0.7)
    ap.add_argument("--json", default=None)
    args = ap.parse_args()

    targets = [t.strip() for t in args.targets.split(",") if t.strip()]
    keys = {t: t.replace(" ", "") for t in targets}
    excl = set()
    if os.path.exists(REPLAY_SRC):
        excl = {ln.strip() for ln in open(REPLAY_SRC, encoding="utf-8") if ln.strip()}
    print(f"[코퍼스] {CORPUS_DIR}")
    print(f"[기준셋 보호] 제외 소스 {len(excl):,}개")

    stat = {t: {"failExact": 0, "failVariant": 0, "corrExact": 0, "corrVariant": 0,
                "corrFromReplay": 0, "samples": []} for t in targets}

    fails = load_labels(FAIL_LABELS)
    n_ledger = 0
    for ln in open(CORPUS_PATH, encoding="utf-8"):
        ln = ln.strip()
        if not ln:
            continue
        try:
            e = json.loads(ln)
        except json.JSONDecodeError:
            continue
        n_ledger += 1
        if e.get("column") != "itemName" or e.get("labelForm") != "raw":
            continue
        if (e.get("matchRatio") or 0) < args.min_match:
            continue
        if e.get("src") in excl:
            continue
        label = fails.get("crops/" + crop_name(e))
        if not label:
            continue
        flat = label.replace(" ", "")
        for t in targets:
            if keys[t] not in flat:
                continue
            s = stat[t]
            if flat == keys[t]:
                s["failExact"] += 1
            else:
                s["failVariant"] += 1
                if len(s["samples"]) < 5:
                    s["samples"].append(label)
            break

    meta = _bal_meta()
    crops_correct = os.path.join(CORPUS_DIR, "crops_correct")
    have = set(os.listdir(crops_correct)) if os.path.isdir(crops_correct) else set()
    n_corr = 0
    for path, label in load_labels(BAL_LABELS).items():
        if path.split("/", 1)[-1] not in have:
            continue
        n_corr += 1
        flat = label.replace(" ", "")
        for t in targets:
            if keys[t] not in flat:
                continue
            s = stat[t]
            if flat == keys[t]:
                s["corrExact"] += 1
            else:
                s["corrVariant"] += 1
            if (meta.get(path) or {}).get("src") in excl:
                s["corrFromReplay"] += 1
            break

    print(f"[풀 규모] ledger {n_ledger:,}줄 · failure 라벨 {len(fails):,} · 정답 크롭 {n_corr:,}\n")
    print(f"{'품명':26} {'실패풀(정확/변형)':>18} {'정답풀(정확/변형)':>18} {'합계':>6} "
          f"{'정답풀 중 기준셋':>14}")
    rows = []
    for t in targets:
        s = stat[t]
        total = s["failExact"] + s["failVariant"] + s["corrExact"] + s["corrVariant"]
        rows.append({"name": t, **s, "total": total})
        print(f"{t[:24]:26} {s['failExact']:>8} / {s['failVariant']:<7} "
              f"{s['corrExact']:>8} / {s['corrVariant']:<7} {total:>6} "
              f"{s['corrFromReplay']:>14}")
    print("\n· 실패풀 = base 가 틀리던 크롭(1단계 타깃이 여기 있음)")
    print("· 정답풀 = base 가 맞히던 크롭(2단계 타깃=잃어버린 품명이 여기 있음)")
    print("· 변형 = 회사명·수량 꼬리가 붙은 라벨. 학습에 포함할지는 선택 사항")
    print("· '정답풀 중 기준셋' = 그 크롭이 9,001 기준셋 문서에서 온 것(학습 제외 대상)")
    for t in targets:
        if stat[t]["samples"]:
            print(f"\n[{t}] 변형 라벨 예시: " + " | ".join(stat[t]["samples"][:3]))

    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump({"corpus": CORPUS_DIR, "targets": rows}, f, ensure_ascii=False, indent=2)
        print(f"\n[저장] {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
