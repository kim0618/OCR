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

anchor: 타깃과 무관한 정답 크롭을 섞는다. 수량은 타깃 크롭 × --anchor-ratio(기본 3.0)
  로 자동 산정 — 단계마다 타깃이 늘어나므로 절대값으로 두면 조건이 계속 달라진다.
  실제 운용값은 run-finetune.sh 의 DEMO_ANCHOR_* 상수가 넘긴다(현재 12.0 / 품명 0.8).
  ★없으면 안 되는 이유(2026-08-03 실측): 앵커 0 으로 돌린 1차 1단계는 판정 22/26 실패.
  '슐'은 다 고쳤지만 주변 글자가 흔들려 삽입("캡슐건")·치환("겁슐")·삭제("세파록캡슐")이
  났다. 학습 신호가 전부 같은 정답 하나뿐이면 글자/공백 판정 기준까지 함께 밀리기 때문.

    python eval/build_demo_dataset.py --targets "디아세렌캡슐" \
        --replay-sources eval/finetune_corpus/replay_sources.txt
"""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from finetune_ledger import CORPUS_DIR, CORPUS_PATH  # noqa: E402
from finetune_crops import load_labels, crop_name  # noqa: E402
from demo_next_target import basis_keep  # noqa: E402  (기준셋 확정 목록 - 조각 크롭 제외)

FAIL_LABELS = os.path.join(CORPUS_DIR, "labels.txt")
BAL_LABELS = os.path.join(CORPUS_DIR, "labels_correct.txt")
BAL_META = os.path.join(CORPUS_DIR, "labels_correct.meta.jsonl")
DATASET_DIR = os.path.join(CORPUS_DIR, "dataset")

MIN_TRAIN_TARGET = 10   # 학습용 타깃 크롭 최소치 — 미달이면 후보 차순위로 (abort)

# 앵커 성분 서명 - H 한글 / E 영문 / N 숫자 / S 기호. 판정 분석(recount)과 같은 문자
# 클래스를 써야 "어느 조합에서 잃었나 → 그 조합을 앵커에 얼마나 넣나"가 바로 이어진다.
SYMBOL_RE = r"[()\[\]{}/\\·,.:;+*%~°'\"-]"


def _sig(label: str) -> str:
    s = ""
    if re.search(r"[가-힣]", label):
        s += "H"
    if re.search(r"[A-Za-z]", label):
        s += "E"
    if re.search(r"[0-9]", label):
        s += "N"
    if re.search(SYMBOL_RE, label):
        s += "S"
    return s or "-"


def _bal_meta_rows() -> list[dict]:
    """정답 풀 사이드카를 행째로 — src 와 column 을 함께 봐야 하는 집계용."""
    if not os.path.exists(BAL_META):
        return []
    out = []
    for ln in open(BAL_META, encoding="utf-8"):
        try:
            out.append(json.loads(ln))
        except json.JSONDecodeError:
            continue
    return out


_ANCHOR_MIX: dict[str, int] = {}


def _bal_col() -> dict[str, str | None]:
    """정답 풀 사이드카: crops_correct/<hash>.jpg → column. 사이드카가 없으면 알 수 없다."""
    out: dict[str, str | None] = {}
    for rec in _bal_meta_rows():
        if rec.get("path"):
            out[rec["path"]] = rec.get("column")
    return out


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


_POOL = {"failBasis": 0, "failBasisItem": 0, "failItem": 0, "failUniq": 0}
_SRC = {"train": set(), "judge": set()}   # 크롭이 나온 원본 문서(이미지) — 몇 장을 돌렸나   # ledger 1패스에서 같이 세는 풀 통계


def _target_crops(targets: list[str], min_match: float,
                  replay: set | None = None) -> dict[str, dict]:
    """타깃 품명의 크롭을 두 풀에서 모아 {path: {label, src, pool}} 로 돌려준다.

    라벨 매칭은 공백 제거 후 부분일치 — 크롭 라벨에 회사명·수량 꼬리가 붙은 변형까지
    같은 품명으로 흡수한다(기준셋 실측: 세파클러캡슐250mg 정확 24셀 vs 변형 포함 131셀).
    """
    keys = [t.replace(" ", "") for t in targets]
    out: dict[str, dict] = {}

    fails = load_labels(FAIL_LABELS)
    _POOL["failUniq"] = len(fails)   # 2M줄짜리 파일을 main 에서 또 읽지 않도록 여기서 보관
    for ln in open(CORPUS_PATH, encoding="utf-8"):
        ln = ln.strip()
        if not ln:
            continue
        try:
            e = json.loads(ln)
        except json.JSONDecodeError:
            continue
        # ★풀 집계는 '크롭 실물이 있는 것'만 — ledger 에는 박스를 못 잡아 크롭이
        #  안 잘린 엔트리도 남아 있다(2026-08-04 실측: 기준셋 415,843줄 중 실물 364,054).
        path = "crops/" + crop_name(e)
        label = fails.get(path)
        # ★품명 풀은 matchRatio 게이트를 통과한 것만 센다 - 그 아래는 라벨(정답) 자체를
        #  못 믿는 크롭이라 채점에 못 쓴다. demo_next_target.basis_crops 와 같은 기준이라야
        #  리포트의 '판정 품명 크롭' 과 스캔이 읽는 장수가 한 숫자로 떨어진다.
        item_ok = (e.get("column") == "itemName"
                   and (e.get("matchRatio") or 0) >= min_match)
        if label and item_ok:
            _POOL["failItem"] += 1            # 실패풀 품명 크롭 전체
        if label and e.get("src"):
            (_SRC["judge"] if replay and e["src"] in replay else _SRC["train"]).add(e["src"])
        if replay is not None and e.get("src") in replay and label:
            _POOL["failBasis"] += 1       # 컬럼 무관 - 실패풀의 기준셋 출처 총량
            if item_ok:
                _POOL["failBasisItem"] += 1   # 그중 품명 크롭만
        if e.get("column") != "itemName" or e.get("labelForm") != "raw":
            continue
        if (e.get("matchRatio") or 0) < min_match:
            continue
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
    ap.add_argument("--anchor-ratio", type=float, default=3.0,
                    help="앵커 수 = 타깃 학습 크롭 × 이 배수(기본 3.0 = 검증된 값). "
                         "단계가 갈수록 타깃이 늘어나므로 절대값 대신 비율로 잡아야 조건이 "
                         "일정하게 유지된다. 0 = 앵커 없음(2026-08-03 실측: 판정 22/26 실패)")
    ap.add_argument("--anchor", type=int, default=0,
                    help="앵커 수 절대값. 주면 --anchor-ratio 를 덮어쓴다")
    # ★성분 층화(2026-08-06). 비율 플래그는 <실제 노출>을 보장하지 못한다: v7 에서
    #  --anchor-item-ratio 만 0.6→0.8 로 올렸는데 leftover 슬롯이 402→1 로 줄면서
    #  순수 짧은숫자가 513→420 으로 같이 빠졌다(의도 안 한 3중 개입 → 해석 불가).
    #  --anchor-plan 은 버킷별 <장수>를 못박아 leftover 자체를 없앤다.
    #    키: 성분 서명(HENS/HEN/H/HS/HNS/HN/HES/HE/N…)=품명 풀 / NUM=타컬럼 짧은숫자
    #        / REST=타컬럼 나머지.  합계가 곧 앵커 총량이 되므로 --anchor-ratio 와 함께
    #        쓰면 총량이 일치하는지 검사한다.
    ap.add_argument("--anchor-plan", default="",
                    help="앵커 버킷별 장수 'HENS=446,HEN=280,...,NUM=498,REST=302'. "
                         "주면 --anchor-item-ratio/--anchor-shortnum-ratio 를 대체한다")
    # ★앵커 구성 - 무작위로 뽑으면 정답풀 컬럼 분포를 그대로 따라가 품명이 8% 안팎뿐이다.
    #  그런데 파인튜닝이 깨뜨리는 건 품명(한 글자 치환)이라, 정작 지켜야 할 쪽 앵커가 얇다.
    #  clean4(2026-07-30)에서 '짧은 숫자'를 겨냥해 앵커를 채우자 숫자 -8.8 -> +2.0 으로
    #  뒤집힌 전례가 있다. 같은 수법을 품명에 적용한다.
    ap.add_argument("--anchor-item-ratio", type=float, default=0.6,
                    help="앵커 중 품명 크롭 비중(0~1). 기본 0.6")
    ap.add_argument("--anchor-shortnum-ratio", type=float, default=0.2,
                    help="앵커 중 짧은 숫자(1~3자리) 비중. 숫자 붕괴 방어용. 기본 0.2")
    ap.add_argument("--val-target", type=int, default=20,
                    help="검증용으로 <학습 크롭에서> 뺄 장수. 판정셋(기준셋)은 val 에도 쓰지 않는다")
    ap.add_argument("--val-anchor", type=int, default=0,
                    help="검증에 섞을 앵커 수. 기본 0 = 검증도 타깃 크롭만")
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

    tmap = _target_crops(targets, args.min_match, replay)
    rnd = random.Random(args.seed)

    # 타깃별로 학습(기준셋 아님) / 판정(기준셋) 분리
    keys = {t: t.replace(" ", "") for t in targets}
    train_t: list[tuple[str, str]] = []
    val_t: list[tuple[str, str]] = []
    judge_t: list[tuple[str, str]] = []
    detail: dict[str, dict] = {}
    _keep = basis_keep()
    for t in targets:
        mine = [(p, m) for p, m in sorted(tmap.items()) if keys[t] in m["label"].replace(" ", "")]
        judge = [(p, m) for p, m in mine if m["src"] and m["src"] in replay]
        if _keep is not None:
            # ★판정은 확정 목록 크롭만 - 조각 크롭(라벨과 다른 칸)이 판정셋에 끼면
            #  그 크롭은 영원히 오답이라 소생 판정이 성립할 수 없다(2026-08-04 실증).
            n_junk = sum(1 for p, _ in judge if p not in _keep)
            judge = [(p, m) for p, m in judge if p in _keep]
            if n_junk:
                print(f"[demo] '{t}': 판정 후보 중 조각 크롭 {n_junk}장 제외(basis_keep)")
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
    # ★수량은 타깃 크롭 수에 비례(--anchor-ratio). 단계마다 타깃이 늘어나는데 앵커를
    #  절대값으로 두면 비율이 계속 달라져 조건 비교가 안 된다.
    n_anchor = args.anchor if args.anchor > 0 else int(len(train_t) * args.anchor_ratio)
    anchors: list = []
    n_anchor_replay_skip = 0
    if n_anchor > 0:
        bal_src = _bal_src()
        bal_col = _bal_col()          # 정답풀 컬럼(사이드카에 있는 24% 만 알 수 있음)
        used = ({p for p, _ in judge_t} | {p for p, _ in train_t} | {p for p, _ in val_t})
        item_pool, num_pool, rest_pool = [], [], []
        for p, g in sorted(load_labels(BAL_LABELS).items()):
            if p in used:
                continue
            if replay and bal_src.get(p) in replay:
                n_anchor_replay_skip += 1
                continue
            flat = g.strip()
            if bal_col.get(p) == "itemName":
                item_pool.append((p, g))
            elif flat.isdigit() and len(flat) <= 3:
                num_pool.append((p, g))     # 라벨만 보면 되니 사이드카가 없어도 잡힌다
            else:
                rest_pool.append((p, g))
        for pool in (item_pool, num_pool, rest_pool):
            rnd.shuffle(pool)
        want = n_anchor + args.val_anchor
        # 품명 풀을 성분 서명으로 쪼갠다. 라벨이 순수 짧은숫자(1~3자리)인 품명 크롭은
        # ITEMNUM 으로 따로 뺀다 — 서명으로는 'N' 이지만 긴 숫자(제품코드 등)와 섞이면
        # v5 의 '품명·순수 짧은숫자 15장' 을 그대로 재현할 수 없다.
        sig_pools: dict[str, list] = {}
        for p, g in item_pool:
            flat = g.strip()
            key = "ITEMNUM" if (flat.isdigit() and len(flat) <= 3) else _sig(flat)
            sig_pools.setdefault(key, []).append((p, g))
        if args.anchor_plan:
            plan = {}
            for part in args.anchor_plan.split(","):
                key, _, val = part.partition("=")
                plan[key.strip()] = int(val)
            if sum(plan.values()) != want:
                raise SystemExit(f"--anchor-plan 합계 {sum(plan.values())} != 앵커 총량 {want}"
                                 " — 총량이 달라지면 이전 라운드와 비교가 성립하지 않는다.")
            picked, short = [], {}
            for key, n in plan.items():
                pool = (num_pool if key == "NUM" else
                        rest_pool if key == "REST" else sig_pools.get(key, []))
                picked += pool[:n]
                if len(pool) < n:
                    short[key] = {"want": n, "pool": len(pool)}
            if short:
                # 부족분을 다른 성분으로 조용히 메우지 않는다 — 그게 v7 의 해석 불가 원인이었다.
                raise SystemExit(f"★앵커 풀 부족 {short} — 계획대로 못 채우면 단일 변수 실험이"
                                 " 아니게 된다. 장수를 낮추거나 풀을 넓혀서 다시 실행할 것.")
            _ANCHOR_MIX.update(plan=plan)
        else:
            n_item = int(want * args.anchor_item_ratio)
            n_num = int(want * args.anchor_shortnum_ratio)
            picked = item_pool[:n_item] + num_pool[:n_num]
            # 어느 한 풀이 모자라면 나머지 풀에서 채운다 - 총량은 항상 맞춘다.
            leftover = (item_pool[n_item:] + num_pool[n_num:] + rest_pool)
            rnd.shuffle(leftover)
            picked += leftover[:max(0, want - len(picked))]
        rnd.shuffle(picked)
        anchors = picked
        got: dict[str, int] = {}
        for p, g in anchors:
            flat = g.strip()
            short_num = flat.isdigit() and len(flat) <= 3
            if bal_col.get(p) == "itemName":
                key = "ITEMNUM" if short_num else _sig(flat)
            else:
                key = "NUM" if short_num else "REST"
            got[key] = got.get(key, 0) + 1
        _ANCHOR_MIX.update(item=sum(1 for p, _ in anchors if bal_col.get(p) == "itemName"),
                           shortNum=sum(1 for _, g in anchors
                                        if g.strip().isdigit() and len(g.strip()) <= 3),
                           itemPool=len(item_pool), numPool=len(num_pool),
                           # ★요청(plan) 과 실제(got) 를 같이 남긴다 - 리포트가 배합을
                           #  추정이 아니라 실측으로 말할 수 있어야 한다.
                           sigGot=dict(sorted(got.items())),
                           sigPool={k: len(v) for k, v in sorted(sig_pools.items())})

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
    # ★풀 모수 — "이 전체에서 타깃 N장을 뽑았다"를 리포트가 말할 수 있게 세어 둔다.
    #   학습 풀 = 기준셋이 아닌 크롭(학습에 쓸 수 있는 전량)
    #   판정 풀 = 기준셋(9,001) 문서에서 온 크롭 전량
    # ★실패풀 쪽은 '라벨이 있는 것'만 세는데(=크롭 실물이 잘린 것), 정답풀도 같은 잣대를
    #  써야 한쪽만 부풀지 않는다. 사이드카에 행은 있는데 라벨이 없는 크롭은 채점 불가다.
    _corr_lbl = load_labels(BAL_LABELS) if os.path.exists(BAL_LABELS) else {}
    # ★줄 수가 아니라 고유 경로 수로 센다 - labels.txt 에 같은 크롭이 두 번 적힌 줄이
    #  있어(2026-08-04 실측 1,069줄) 줄 수로 세면 없는 크롭만큼 풀이 부푼다.
    n_fail_total = _POOL["failUniq"]
    n_corr_total = len(_corr_lbl)
    # 정답풀의 기준셋 출처는 사이드카(src)로 센다. 실패풀 쪽은 _target_crops 가
    # ledger 를 훑을 때 함께 세어 둔 값(_POOL)을 쓴다 — 1.7GB 파일을 두 번 읽지 않으려고.
    _bs = [r for r in _bal_meta_rows() if r.get("path") in _corr_lbl]
    for r in _bs:                       # 정답풀 쪽 출처도 합친다(메타 없는 크롭은 셀 수 없음)
        if r.get("src"):
            (_SRC["judge"] if r["src"] in replay else _SRC["train"]).add(r["src"])
    n_corr_basis = sum(1 for r in _bs if r.get("src") in replay)
    n_corr_basis_item = sum(1 for r in _bs
                            if r.get("src") in replay and r.get("column") == "itemName")
    pool_judge = _POOL["failBasis"] + n_corr_basis
    pool_judge_item = _POOL["failBasisItem"] + n_corr_basis_item
    _bk = basis_keep()
    if _bk is not None:
        pool_judge_item = len(_bk)   # 확정 목록이 곧 판정 품명 풀(45,617)
    pool_train = (n_fail_total + n_corr_total) - pool_judge
    # 학습 풀의 품명 크롭 — 출처·컬럼이 확인되는 것만 센 <최소치>다.
    # 정답풀 상당수가 메타 없이 수확돼 컬럼을 알 수 없어 그만큼은 빠진다.
    n_corr_item_train = sum(1 for r in _bs
                            if r.get("column") == "itemName" and r.get("src") not in replay)
    pool_train_item_fail = _POOL["failItem"] - _POOL["failBasisItem"]
    pool_train_item = pool_train_item_fail + n_corr_item_train

    manifest = {
        "mode": "demo",
        "targets": targets,
        # trainNote: 학습 풀은 (전체 − 판정 풀)이라 '기준셋이 아님이 확인된' 수가 아니다.
        #  정답풀 상당수가 출처 메타 없이 수확돼 기준셋 여부를 알 수 없기 때문.
        "pool": {"train": pool_train, "judge": pool_judge,
                 "trainItem": pool_train_item, "judgeItem": pool_judge_item,
                 "trainItemFail": pool_train_item_fail,
                 "failTotal": n_fail_total, "correctTotal": n_corr_total,
                 # 몇 장(문서)을 돌려서 저 크롭이 나왔는지. 출처 메타가 있는 크롭만 세므로 최소치.
                 "trainDocs": len(_SRC["train"]), "judgeDocs": len(_SRC["judge"]),
                 "trainNote": "기준셋으로 확인되지 않은 나머지(출처 메타 없는 크롭 포함)"},
        "targetCrops": {t: detail[t]["train"] + detail[t]["judge"] for t in targets},
        "byTarget": detail,
        "judgeBasis": "기준셋(9,001) 문서에서 수확한 같은 품명 크롭",
        "counts": {"train": len(train), "val": len(val), "test": len(judge_t),
                   "anchorMix": dict(_ANCHOR_MIX),
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
