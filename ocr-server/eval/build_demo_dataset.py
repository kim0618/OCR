"""build_demo_dataset — 소생 데모 전용 미니 학습셋.

★기준셋(9,001)이 곧 판정셋이다. 따로 홀드아웃을 뗄 필요가 없다:
  학습 = 코퍼스(리키잉 10.5만 이미지) 크롭 중 <기준셋이 아닌 문서>에서 온 것
  판정 = 같은 품명 크롭 중 <기준셋 문서>에서 온 것 (replay_sources 로 식별)
  기준셋은 애초에 학습 금지 대상이라, 이 구분만으로 "학습에 안 쓴 크롭으로 판정"이
  구조적으로 보장된다. 무작위 홀드아웃보다 학습 크롭도 더 많이 쓰고, 회사에는
  "그 9,001장 안에서 읽게 됐다"로 바로 말할 수 있다.

크롭을 모으는 두 풀:
  failure 풀 (labels.txt + ledger)  base 가 틀리던 크롭 — 1단계 타깃이 여기 있다.
                                    ledger 에 src 가 있어 기준셋 여부를 안다.
  정답 풀   (labels_correct.txt)    base 가 맞히던 크롭 — 2단계 타깃(잃어버린 품명)은
                                    failure 풀에 없으므로 여기서 나온다. src 는
                                    labels_correct.meta.jsonl 사이드카에 있다.
  src 를 모르는 정답 크롭은 기준셋 여부를 확인할 수 없으므로 <판정에 쓰지 않고>
  학습에만 쓴다(오염 위험은 manifest 에 기록해 리포트가 표기).

anchor: 타깃 크롭 수십 장만으로 학습하면 모델이 아무 크롭에나 타깃 문자열을 뱉는
  출력붕괴가 온다. 무관한 정답 크롭을 섞어 그걸 막는다(--anchor 0 = 순수 타깃만).

    python eval/build_demo_dataset.py --targets "디아세렌캡슐" \
        --replay-sources eval/finetune_corpus/replay_sources.txt
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from finetune_ledger import CORPUS_DIR, CORPUS_PATH  # noqa: E402
from finetune_crops import load_labels, crop_name  # noqa: E402

FAIL_LABELS = os.path.join(CORPUS_DIR, "labels.txt")
BAL_LABELS = os.path.join(CORPUS_DIR, "labels_correct.txt")
BAL_META = os.path.join(CORPUS_DIR, "labels_correct.meta.jsonl")
DATASET_DIR = os.path.join(CORPUS_DIR, "dataset")

MIN_TRAIN_TARGET = 10   # 학습용 타깃 크롭 최소치 — 미달이면 후보 차순위로 (abort)


def _bal_src() -> dict[str, str | None]:
    """정답 풀 사이드카: crops_correct/<hash>.jpg → src(출처 이미지). 없으면 빈 dict."""
    out: dict[str, str | None] = {}
    if not os.path.exists(BAL_META):
        return out
    for ln in open(BAL_META, encoding="utf-8"):
        try:
            rec = json.loads(ln)
        except json.JSONDecodeError:
            continue
        if rec.get("path"):
            out[rec["path"]] = rec.get("src")
    return out


def _target_crops(targets: list[str], min_match: float) -> dict[str, dict]:
    """타깃 품명의 크롭을 두 풀에서 모아 {path: {label, src, pool}} 로 돌려준다.

    라벨 매칭은 공백 제거 후 부분일치 — 크롭 라벨에 회사명·수량 꼬리가 붙은 변형까지
    같은 품명으로 흡수한다(기준셋 실측: 세파클러캡슐250mg 정확 24셀 vs 변형 포함 131셀).
    """
    keys = [t.replace(" ", "") for t in targets]
    out: dict[str, dict] = {}

    fails = load_labels(FAIL_LABELS)
    for ln in open(CORPUS_PATH, encoding="utf-8"):
        ln = ln.strip()
        if not ln:
            continue
        try:
            e = json.loads(ln)
        except json.JSONDecodeError:
            continue
        if e.get("column") != "itemName" or e.get("labelForm") != "raw":
            continue
        if (e.get("matchRatio") or 0) < min_match:
            continue
        path = "crops/" + crop_name(e)
        label = fails.get(path)
        if not label:
            continue
        if any(k in label.replace(" ", "") for k in keys):
            out[path] = {"label": label, "src": e.get("src"), "pool": "failure"}

    src_by_path = _bal_src()
    crops_dir = os.path.join(CORPUS_DIR, "crops_correct")
    have = set(os.listdir(crops_dir)) if os.path.isdir(crops_dir) else set()
    for path, label in load_labels(BAL_LABELS).items():
        if path in out or path.split("/", 1)[-1] not in have:
            continue
        if any(k in label.replace(" ", "") for k in keys):
            out[path] = {"label": label, "src": src_by_path.get(path), "pool": "correct"}
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--targets", required=True,
                    help="살릴 품명(콤마 구분). 이전 단계 타깃을 누적해서 전달")
    ap.add_argument("--replay-sources", "--exclude-sources", dest="replay_sources",
                    default=os.path.join(CORPUS_DIR, "replay_sources.txt"),
                    help="기준셋(9,001) 소스 목록 — 이 문서에서 온 크롭이 판정셋이 된다")
    ap.add_argument("--oversample-to", type=int, default=0,
                    help="타깃 학습 줄 복제 상한. 0=복제 안 함(권장 - 반복 노출은 에폭이 담당)")
    ap.add_argument("--anchor", type=int, default=500,
                    help="labels_correct 랜덤 앵커 수(출력붕괴 보험). 0=순수 타깃만. "
                         "타깃의 3배 정도가 출발점(보호 대상이 다수여야 함)")
    ap.add_argument("--val-target", type=int, default=20,
                    help="검증용으로 <학습 크롭에서> 뺄 장수. 판정셋(기준셋)은 val 에도 쓰지 않는다")
    ap.add_argument("--val-anchor", type=int, default=100,
                    help="검증에 섞을 앵커 수(붕괴 조기경보)")
    ap.add_argument("--min-match", type=float, default=0.7)
    ap.add_argument("--fallback-holdout", type=float, default=0.25,
                    help="기준셋 크롭이 하나도 없을 때만 쓰는 무작위 홀드아웃 비율")
    ap.add_argument("--seed", type=int, default=20260803)
    args = ap.parse_args()

    targets = [t.strip() for t in args.targets.split(",") if t.strip()]
    replay: set[str] = set()
    if args.replay_sources and os.path.exists(args.replay_sources):
        replay = {ln.strip() for ln in open(args.replay_sources, encoding="utf-8") if ln.strip()}
    if not replay:
        print("[demo] ★replay_sources 가 비어 있습니다 — 기준셋 식별 불가. "
              "무작위 홀드아웃으로 대체합니다(권장하지 않음).", file=sys.stderr)

    tmap = _target_crops(targets, args.min_match)
    rnd = random.Random(args.seed)

    # 타깃별로 학습(기준셋 아님) / 판정(기준셋) 분리
    keys = {t: t.replace(" ", "") for t in targets}
    train_t: list[tuple[str, str]] = []
    val_t: list[tuple[str, str]] = []
    judge_t: list[tuple[str, str]] = []
    detail: dict[str, dict] = {}
    for t in targets:
        mine = [(p, m) for p, m in sorted(tmap.items()) if keys[t] in m["label"].replace(" ", "")]
        judge = [(p, m) for p, m in mine if m["src"] and m["src"] in replay]
        train = [(p, m) for p, m in mine if not (m["src"] and m["src"] in replay)]
        unknown = sum(1 for _, m in train if not m["src"])
        if not judge:
            # 기준셋에서 수확된 크롭이 없으면(드묾) 무작위 홀드아웃으로 대체
            rnd.shuffle(train)
            n_hold = max(1, int(len(train) * args.fallback_holdout))
            judge, train = train[:n_hold], train[n_hold:]
            print(f"[demo] '{t}': 기준셋 크롭 0개 → 무작위 홀드아웃 {len(judge)}장으로 대체",
                  file=sys.stderr)
        detail[t] = {
            "train": len(train), "judge": len(judge),
            "trainFailure": sum(1 for _, m in train if m["pool"] == "failure"),
            "trainCorrect": sum(1 for _, m in train if m["pool"] == "correct"),
            "judgeFromBasis": sum(1 for _, m in judge if m["src"] and m["src"] in replay),
            "trainUnknownSrc": unknown,
        }
        print(f"[demo] '{t}': 학습 {len(train)}장(실패풀 {detail[t]['trainFailure']} / "
              f"정답풀 {detail[t]['trainCorrect']}, 출처불명 {unknown}) · "
              f"판정 {len(judge)}장(기준셋)")
        if len(train) < MIN_TRAIN_TARGET:
            print(f"[demo] ★'{t}' 학습 크롭 {MIN_TRAIN_TARGET}장 미만 — 코퍼스가 얇습니다. "
                  f"차순위 후보로 교체하세요.", file=sys.stderr)
            return 1
        # ★검증(val)은 <학습 크롭>에서 뺀다. 판정셋(기준셋)을 val 로 쓰면 그걸로 best
        #   체크포인트를 고른 셈이 되어 'held-out' 주장이 약해진다.
        rnd.shuffle(train)
        n_val = min(max(1, args.val_target // max(1, len(targets))), len(train) // 5)
        val_part, train_part = train[:n_val], train[n_val:]
        detail[t]["valFromTrain"] = len(val_part)
        detail[t]["train"] = len(train_part)
        detail[t]["trainFailure"] = sum(1 for _, m in train_part if m["pool"] == "failure")
        detail[t]["trainCorrect"] = sum(1 for _, m in train_part if m["pool"] == "correct")
        train_t += [(p, m["label"]) for p, m in train_part]
        val_t += [(p, m["label"]) for p, m in val_part]
        judge_t += [(p, m["label"]) for p, m in judge]

    # 반복 노출은 에폭이 담당한다 — 기본값(--oversample-to 0)은 복제하지 않는다.
    if args.oversample_to and train_t:
        over: list = []
        while len(over) < args.oversample_to:
            over += train_t
        over = over[:args.oversample_to]
    else:
        over = list(train_t)

    # 앵커: 정답풀 랜덤(타깃과 무관한 크롭 유지 신호). 타깃·판정·검증과 겹치지 않게 제외.
    # ★기준셋(9,001) 출처 크롭은 앵커에서도 제외 — 기준셋은 어떤 형태로든 학습 금지.
    #  (다음 회차 타깃의 판정 크롭이 앵커로 흘러들면 그 판정이 오염된다)
    anchors: list = []
    n_anchor_replay_skip = 0
    if args.anchor > 0:
        bal_src = _bal_src()
        used = ({p for p, _ in judge_t} | {p for p, _ in train_t} | {p for p, _ in val_t})
        bal = []
        for p, g in sorted(load_labels(BAL_LABELS).items()):
            if p in used:
                continue
            if replay and bal_src.get(p) in replay:
                n_anchor_replay_skip += 1
                continue
            bal.append((p, g))
        rnd.shuffle(bal)
        anchors = bal[:args.anchor + args.val_anchor]

    val_anchor = anchors[:args.val_anchor]
    train_anchor = anchors[args.val_anchor:]
    train = over + train_anchor
    rnd.shuffle(train)
    # val = 학습에서 뺀 타깃 크롭(소생 여부) + 앵커(붕괴 조기경보)
    val = val_t + val_anchor

    os.makedirs(DATASET_DIR, exist_ok=True)
    for name, rows in (("train", train), ("val", val), ("test", judge_t)):
        with open(os.path.join(DATASET_DIR, f"{name}.txt"), "w", encoding="utf-8") as f:
            for p, g in rows:
                f.write(f"{p}\t{g}\n")
    manifest = {
        "mode": "demo",
        "targets": targets,
        "targetCrops": {t: detail[t]["train"] + detail[t]["judge"] for t in targets},
        "byTarget": detail,
        "judgeBasis": "기준셋(9,001) 문서에서 수확한 같은 품명 크롭",
        "counts": {"train": len(train), "val": len(val), "test": len(judge_t),
                   "targetTrainUnique": len(train_t), "oversampledTo": len(over),
                   "anchor": len(train_anchor), "valTarget": len(val_t),
                   "valAnchor": len(val_anchor)},
        "seed": args.seed,
    }
    with open(os.path.join(DATASET_DIR, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    dup = f" → {len(over):,}줄 복제" if args.oversample_to else " (복제 없음)"
    steps = -(-len(train) // 64)      # batch 64 기준 에폭당 스텝(올림)
    print(f"[demo] 학습셋: train {len(train):,}줄 = 타깃 {len(train_t)}장{dup} "
          f"+ 앵커 {len(train_anchor):,}  (타깃 비중 {100.0 * len(over) / max(1, len(train)):.0f}%)")
    if n_anchor_replay_skip:
        print(f"[demo] 앵커 후보 중 기준셋 출처 {n_anchor_replay_skip:,}장 제외(학습 금지)")
    print(f"[demo] 검증 {len(val)}줄 = 학습에서 뺀 타깃 {len(val_t)}장 + 앵커 {len(val_anchor)}")
    print(f"[demo] 판정 {len(judge_t)}장 = 기준셋 9,001 문서의 같은 품명 크롭(학습·검증에 미포함)")
    print(f"[demo] 배치 64 기준 에폭당 약 {steps} 스텝")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
