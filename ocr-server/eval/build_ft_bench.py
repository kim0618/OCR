"""build_ft_bench — freeze the fixed SEEN / UNSEEN recognition benches.

Purpose: give FINETUNE_REPORT two crop piles that answer two different
questions with the SAME scoring, so base→FT deltas are directly comparable:

  UNSEEN = 9,001 held-out 문서의 실패 크롭 (학습에서 완전 격리)
           → "처음 보는 송장의 안 읽히던 셀을 FT가 얼마나 읽게 되나" = 회사 답
  SEEN   = 학습에 실제로 쓴 문서의 실패 크롭, UNSEEN과 컬럼 분포·크기 동일 샘플
           → "외운 걸 재현하는 상한" (일반화 판정용 = SEEN↔UNSEEN 간격)

두 파일 모두 실패-크롭 구성이라 구성 편향이 상쇄되고, 남는 것은 순수 일반화.

원칙 (메모리 근거):
  * 숫자(quantity/unitPrice/amount) = 산술앵커(수량×단가=금액) 통과 행의 값만 채점
    (war 숫자 GT는 구글 raw라 순환 — gt_trust.verify_row_arithmetic 이 유일 오라클)
  * itemCode 바코드 = 4차에서 broad-forgetting 독으로 확정 → 기본 제외
  * UNSEEN 은 base 성패로 고르지 않음(전량) — 단 balance 정답크롭은 src 메타가 없어
    9,001 식별 불가라 이 벤치는 '실패 크롭' 스코프임을 명시(리포트에 표기).

입력(전부 AWS finetune_corpus/):  ledger.jsonl · replay_sources.txt · crops/ · train.txt
        + eval/data/invoice_war/ground_truth_replay.json
출력:  finetune_corpus/bench_unseen.txt · bench_seen.txt   (crop_rel \t gt \t column)
       finetune_corpus/bench_report.md   (구성 요약, freeze 근거)

    .venv/bin/python eval/build_ft_bench.py
    .venv/bin/python eval/build_ft_bench.py --keep-barcode   # 바코드 포함 비교용
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import gt_trust  # verify_row_arithmetic, _num  # noqa: E402
from finetune_ledger import CORPUS_DIR  # noqa: E402

LEDGER = os.path.join(CORPUS_DIR, "ledger.jsonl")
REPLAY_SOURCES = os.path.join(CORPUS_DIR, "replay_sources.txt")
CROPS_DIR = os.path.join(CORPUS_DIR, "crops")
TRAIN_TXT = os.path.join(CORPUS_DIR, "train.txt")
GT_REPLAY = os.path.join(HERE, "data", "invoice_war", "ground_truth_replay.json")

OUT_UNSEEN = os.path.join(CORPUS_DIR, "bench_unseen.txt")
OUT_SEEN = os.path.join(CORPUS_DIR, "bench_seen.txt")
OUT_REPORT = os.path.join(CORPUS_DIR, "bench_report.md")

NUM_COLS = {"quantity", "unitPrice", "amount"}
SEED = 42


def crop_rel(e: dict) -> str:
    """finetune_crops.crop_name 과 동일한 정체성 → crops/<hash>.jpg."""
    bbox = "|".join(str(v) for v in (e.get("ocrBox") or {}).get("bbox", []))
    key = f"{e['src']}::{e['location']}::{e['gt']}::{bbox}"
    return "crops/" + hashlib.sha1(key.encode("utf-8")).hexdigest()[:16] + ".jpg"


def load_trusted_numbers(nine_srcs: set[str]) -> dict[str, dict[str, set]]:
    """src -> {column -> {산술앵커 통과 행의 float 값}}. 숫자 크롭 채점 게이트."""
    trust: dict[str, dict[str, set]] = defaultdict(lambda: defaultdict(set))
    if not os.path.exists(GT_REPLAY):
        print(f"[warn] GT not found: {GT_REPLAY} — 숫자 산술앵커 필터 건너뜀")
        return trust
    doc_map = json.load(open(GT_REPLAY, encoding="utf-8"))
    docs = doc_map.get("documents", doc_map)
    matched = 0
    for gtkey, doc in docs.items():
        src = gtkey.replace("/", "__")
        if src not in nine_srcs:
            continue
        matched += 1
        nr = doc.get("normalizedResult", doc)
        for row in nr.get("tableRows", []):
            if gt_trust.verify_row_arithmetic(row):  # 수량×단가=금액
                for col in NUM_COLS:
                    v = gt_trust._num(row.get(col))
                    if v is not None:
                        trust[src][col].add(v)
    print(f"[gt] self_verified 값 수집: {matched} docs matched of {len(nine_srcs)} nine-srcs")
    return trust


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep-barcode", action="store_true",
                    help="itemCode 바코드도 포함(기본=제외)")
    ap.add_argument("--seed", type=int, default=SEED)
    args = ap.parse_args()
    drop_barcode = not args.keep_barcode

    nine = set(l.strip() for l in open(REPLAY_SOURCES, encoding="utf-8") if l.strip())
    print(f"[in] 9,001 srcs: {len(nine):,}")
    existing = set(os.listdir(CROPS_DIR)) if os.path.isdir(CROPS_DIR) else set()
    print(f"[in] crops/ files: {len(existing):,}")
    trained = set(l.split("\t", 1)[0] for l in open(TRAIN_TXT, encoding="utf-8") if "\t" in l)
    print(f"[in] train.txt paths: {len(trained):,}")

    trust = load_trusted_numbers(nine)

    # ledger 1-pass: unseen(9,001) + seen 후보(나머지) 실패 크롭 수집
    unseen: list[tuple[str, str, str]] = []           # (rel, gt, column)
    seen_pool: dict[str, list[tuple[str, str, str]]] = defaultdict(list)  # column -> [(rel,gt,col)]
    dropped = Counter()
    for line in open(LEDGER, encoding="utf-8"):
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not e.get("cropReady") or e.get("class") != "recognition":
            continue
        col = e.get("column") or "(미분류)"
        if drop_barcode and col == "itemCode":
            dropped["barcode"] += 1
            continue
        rel = crop_rel(e)
        fname = rel.split("/", 1)[1]
        if fname not in existing:
            dropped["no_crop_file"] += 1
            continue
        src = e.get("src")
        is_nine = src in nine
        gt = e.get("gt", "")
        if is_nine:
            # UNSEEN = 실제 읽기 정확도 → GT 신뢰 필요 → 숫자는 산술앵커 통과 값만.
            if col in NUM_COLS:
                v = gt_trust._num(gt)
                if v is None or v not in trust.get(src, {}).get(col, ()):
                    dropped["num_no_anchor"] += 1
                    continue
            unseen.append((rel, gt, col))
        elif rel in trained:
            # SEEN = 가르친 라벨을 외웠나 → 학습 라벨과 대조(앵커 불필요, 非9,001은 검산 불가).
            seen_pool[col].append((rel, gt, col))

    # seen 을 unseen 컬럼 분포에 맞춰 시드 고정 샘플
    unseen_by_col = Counter(c for _, _, c in unseen)
    rng = random.Random(args.seed)
    seen: list[tuple[str, str, str]] = []
    seen_short: dict[str, tuple[int, int]] = {}
    for col, want in unseen_by_col.items():
        pool = seen_pool.get(col, [])
        if len(pool) <= want:
            seen.extend(pool)
            if len(pool) < want:
                seen_short[col] = (len(pool), want)
        else:
            seen.extend(rng.sample(pool, want))

    def _clean(s: str) -> str:
        """탭·줄바꿈 제거 → 한 크롭 = 한 줄 보장(인식 라벨은 단일 라인)."""
        return " ".join(str(s).split())

    def write_list(path: str, rows: list[tuple[str, str, str]]) -> None:
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            for rel, gt, col in rows:
                fh.write(f"{rel}\t{_clean(gt)}\t{col}\n")
        os.replace(tmp, path)

    write_list(OUT_UNSEEN, unseen)
    write_list(OUT_SEEN, seen)

    seen_by_col = Counter(c for _, _, c in seen)
    lines = ["# FT 인식 벤치 (SEEN / UNSEEN) — freeze 요약", "",
             f"- 바코드(itemCode) 제외: {drop_barcode}   seed={args.seed}",
             f"- UNSEEN(9,001 held-out 실패 크롭): **{len(unseen):,}**",
             f"- SEEN(학습에 쓴 실패 크롭, UNSEEN 분포 매칭): **{len(seen):,}**",
             f"- drop: {dict(dropped)}", "",
             "| 컬럼 | UNSEEN | SEEN |", "|---|--:|--:|"]
    for col, n in unseen_by_col.most_common():
        lines.append(f"| {col} | {n:,} | {seen_by_col.get(col, 0):,} |")
    if seen_short:
        lines += ["", "> ⚠ SEEN 풀 부족(컬럼: (있음/필요)): " +
                  ", ".join(f"{c} ({a}/{b})" for c, (a, b) in seen_short.items())]
    with open(OUT_REPORT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")

    print(f"[out] UNSEEN {len(unseen):,} -> {OUT_UNSEEN}")
    print(f"[out] SEEN   {len(seen):,} -> {OUT_SEEN}")
    print(f"[out] report -> {OUT_REPORT}")
    print(f"[drop] {dict(dropped)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
