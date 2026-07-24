"""build_dataset — combine the corpus crops into PaddleOCR rec train/val/test lists.

Reads the two accumulated label pools in the pinned corpus:
  labels.txt          failure-target crops (what we want the model to learn)
  labels_correct.txt  correct-read crops (balance, anti-forgetting)

Combines them at a chosen ratio, de-dups, shuffles deterministically (fixed
seed), and writes PaddleOCR rec label lists under eval/finetune_corpus/dataset/:
  train.txt val.txt test.txt   (each line: <crop_rel_path>\t<label>)
plus manifest.json with the counts and the split policy.

Paths in the lists are relative to the corpus dir, so PaddleOCR's data_dir =
eval/finetune_corpus/ and label_file_list = dataset/train.txt etc.

Pure file ops — no PaddleOCR/GPU needed, runnable & testable now. This is the
buildable half of the fine-tune pipeline; actual train/export is in RECIPE.md.

    ../.venv/Scripts/python.exe eval/build_dataset.py
    ../.venv/Scripts/python.exe eval/build_dataset.py --balance-ratio 1.0 --val 0.1 --test 0.1
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

from finetune_ledger import CORPUS_DIR  # noqa: E402
from finetune_crops import load_labels  # noqa: E402

FAIL_LABELS = os.path.join(CORPUS_DIR, "labels.txt")
BAL_LABELS = os.path.join(CORPUS_DIR, "labels_correct.txt")
DATASET_DIR = os.path.join(CORPUS_DIR, "dataset")

# 금액계열 = war GT 가 콤마 없는 숫자값(819800)이라 크롭 인쇄형(819,800)과 불일치 →
# 학습 시 콤마붕괴(v1~4~1차 실패 원인). 이 컬럼만 콤마 포맷으로 재구성한다. 코드/사업자
# 번호/제조번호/lotNo 는 GT 가 이미 인쇄형(평문·하이픈)이라 그대로 둔다.
MONEY_COLS = {"amount", "unitPrice", "quantity", "supplyAmount",
              "taxAmount", "totalAmount", "discountAmount"}


def _reconstruct_number_label(gt: str, column: str | None) -> str | None:
    """숫자 라벨을 크롭의 인쇄형에 맞게 재구성.

    금액계열: 콤마 포맷(`819800`→`819,800`) + garbage 필터(음수·12자리+ OCR오독).
    그 외 숫자필드(itemCode·bizNumber·manufacturingNo·lotNo·date): 이미 인쇄형이라 그대로.
    반환 None = 학습에서 제외(garbage).
    """
    if column not in MONEY_COLS:
        return gt
    s = (gt or "").strip()
    if s.startswith("-"):
        return None                       # 음수 = 반품/garbage 모호 → 제외(단순화)
    digits = re.sub(r"[^0-9]", "", s)
    if not digits or len(digits) > 11:
        return None                       # 숫자없음 / 12자리+(1000억+=OCR오독, bigint오버플로)
    return f"{int(digits):,}"             # 콤마 포맷 = 크롭 인쇄형과 일치


def _split(items: list, val: float, test: float, seed: int):
    rnd = random.Random(seed)
    items = list(items)
    rnd.shuffle(items)
    n = len(items)
    n_test = int(n * test)
    n_val = int(n * val)
    return (items[n_test + n_val:], items[n_test:n_test + n_val], items[:n_test])  # train, val, test


def _column_filter(fails: dict, columns: set, min_match: float | None,
                   raw_only: bool = False, reconstruct_numbers: bool = False,
                   exclude_sources: set | None = None) -> dict:
    """failure 크롭을 ledger 의 column/matchRatio 로 제한(+숫자라벨 재구성 옵션).

    크롭 파일명 = sha1(crop_key) 라 ledger.jsonl 엔트리에서 역산 가능(finetune_crops 와
    동일 해시). columns 로 학습 표적만 남기고, min_match 로 '크롭에 안 보이는 라벨'을 컷.
    reconstruct_numbers=True 면 금액계열 라벨을 인쇄형(콤마)으로 재구성 + garbage 제외.
    반환 = {path: label}(재구성 반영). reconstruct off 면 원본 라벨 그대로(= 구 동작).
    """
    import json
    from finetune_crops import crop_name
    from finetune_ledger import CORPUS_PATH
    label_by_path: dict = {}
    for ln in open(CORPUS_PATH, encoding="utf-8"):
        ln = ln.strip()
        if not ln:
            continue
        try:
            e = json.loads(ln)
        except json.JSONDecodeError:
            continue
        if columns and e.get("column") not in columns:
            continue
        if min_match is not None and (e.get("matchRatio") or 0) < min_match:
            continue
        if raw_only and e.get("labelForm") != "raw":
            continue    # 정규화 라벨(구세대 적립분) 배제 — rewrite 학습 차단
        if exclude_sources and e.get("src") in exclude_sources:
            continue    # 기준셋(9,001 held-out) 이미지의 크롭 = 학습 금지(측정 오염 방지)
        path = "crops/" + crop_name(e)
        if path not in fails:
            continue
        label = fails[path]
        if reconstruct_numbers:
            label = _reconstruct_number_label(label, e.get("column"))
            if label is None:
                continue    # garbage(음수·초거대값) 제외
        label_by_path[path] = label
    return label_by_path


def _label_gate(fails: dict, n_sample: int = 12) -> None:
    """학습 전 라벨 육안 게이트: 인쇄형 보존 신호(공백/슬래시/대문자/괄호) 통계 + 샘플.

    전부 0% 에 가까우면 라벨이 아직 정규화형 = 학습 돌리면 안 됨 (v1/v2 재발).
    """
    import random as _r
    n = len(fails) or 1
    sig = {"공백": sum(1 for g in fails.values() if " " in g),
           "슬래시(/)": sum(1 for g in fails.values() if "/" in g),
           "대문자": sum(1 for g in fails.values() if any(c.isupper() for c in g)),
           "괄호": sum(1 for g in fails.values() if "(" in g)}
    stats = " · ".join(f"{k} {100.0 * v / n:.1f}%" for k, v in sig.items())
    print(f"[label-gate] failure {n:,}건 인쇄형 보존율: {stats}")
    rnd = _r.Random(7)
    for p, g in rnd.sample(sorted(fails.items()), min(n_sample, len(fails))):
        print(f"[label-gate]   {g[:60]}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--balance-ratio", type=float, default=1.0,
                    help="balance crops per failure crop (1.0 = equal; 0 = failures only)")
    ap.add_argument("--columns", default=None,
                    help="failure 크롭을 이 컬럼들로 제한 (콤마구분, 예: itemName). "
                         "balance(정답 크롭)는 그대로 둬 숫자·타컬럼 망각 방지 앵커로 유지")
    ap.add_argument("--min-match", type=float, default=None,
                    help="failure 크롭 matchRatio 하한(예: 0.7) — 크롭에 없는 텍스트를 "
                         "라벨로 주는 rewrite 학습 차단")
    ap.add_argument("--hangul-min", type=int, default=0,
                    help="failure 라벨의 최소 한글 글자 수(예: 2). 라벨=정규화GT 라 숫자/날짜 "
                         "크롭은 '구분자 벗기기'를 가르침(v2 실측: 콤마 스트립·짧은숫자 삭제 회귀). "
                         "한글 품명만 남기고 숫자는 balance(인쇄 포맷 보존)로만 노출")
    ap.add_argument("--raw-only", action="store_true",
                    help="labelForm=raw(원문 GT 라벨) 엔트리만 학습 — 정규화 라벨 구세대 적립분 배제")
    ap.add_argument("--exclude-sources", default=None,
                    help="★기준셋 보호: 이 파일(한 줄=한 src, 예: 2512__256517__2025...jpg)에 있는 "
                         "이미지의 크롭을 학습에서 전부 제외. 9,001 held-out 기준셋으로 학습하면 "
                         "다음 replay 측정이 오염됨. failure=ledger src 로, balance=meta src 로 거름 "
                         "(meta 에 src 없는 구세대 balance 는 기준셋 배치로 간주해 함께 제외)")
    ap.add_argument("--reconstruct-number-labels", action="store_true",
                    help="★숫자 라운드: 금액계열 failure 라벨을 인쇄형(콤마)으로 재구성(819800→819,800) + "
                         "garbage(음수·12자리+) 제외. war GT가 콤마없는 숫자값이라 그대로 학습하면 콤마붕괴"
                         "(v1~4 실패 원인). itemCode·사업자번호 등은 이미 인쇄형이라 그대로 둔다.")
    ap.add_argument("--balance-hangul-min", type=int, default=0,
                    help="★품명(한글) 라운드용: balance(정답) 크롭도 한글 N자+ 만 남김. 숫자 balance "
                         "는 앵커(--number-anchor-ratio)로만 소량 추가 → 대량 숫자학습(콤마붕괴 원인, "
                         "실측 −9.1%p)을 피하고 한글 인식만 올림. 0=끄기(구 전필드 balance)")
    ap.add_argument("--number-anchor-ratio", type=float, default=0.0,
                    help="숫자 망각(forgetting) 방지 앵커 = failure 수 × 이 비율 만큼 '숫자 balance "
                         "크롭'을 추가(예: 1.0 ≈ 학습의 20%가 숫자). 소량이어야 함 — 대량이면 형식혼재로 "
                         "콤마붕괴. 품명 라운드에서 숫자 회귀 0 을 게이트로 보며 이 값 튜닝")
    ap.add_argument("--balance-digit-min", type=int, default=0,
                    help="★숫자 라운드용(품명 라운드의 --balance-hangul-min 대칭): balance(정답) 크롭을 "
                         "숫자만(한글無+숫자유) 남김. 품명은 --hangul-anchor-ratio 로만 앵커 추가")
    ap.add_argument("--hangul-anchor-ratio", type=float, default=0.0,
                    help="★품명(한글) 망각 방지 앵커 = failure 수 × 이 비율 만큼 '한글 balance 크롭' 추가. "
                         "숫자 라운드에서 품명 보존용 — 1차 교훈(앵커 13%→반대편 −18.8%p)상 크게(예: 2~4) "
                         "넣어 방금 얻은 품명 +11.3%p 를 지킴. 품명 회귀 0 게이트로 튜닝")
    ap.add_argument("--max-train", type=int, default=0,
                    help="총 학습 크롭 상한(0=무제한). 10만장 규모에서 balance 가 수백만이 되므로 "
                         "학습시간 관리용. failure(품목)는 우선 보존하고 balance 를 줄여 맞춤")
    ap.add_argument("--val", type=float, default=0.1)
    ap.add_argument("--test", type=float, default=0.1)
    ap.add_argument("--seed", type=int, default=20260622)
    args = ap.parse_args()

    fails = load_labels(FAIL_LABELS)            # {rel_path: gt}
    bals = load_labels(BAL_LABELS)

    # 기준셋(9,001 held-out) 제외 목록 — 측정셋으로 학습하면 replay 점수가 부풀려짐.
    excl_sources: set = set()
    if args.exclude_sources and os.path.exists(args.exclude_sources):
        excl_sources = {ln.strip() for ln in open(args.exclude_sources, encoding="utf-8")
                        if ln.strip()}
        print(f"[build_dataset] 기준셋 제외 소스: {len(excl_sources):,} 이미지")
        # balance: meta(src) 기반 제외. src 없는 meta 행 = 기준셋 replay 배치(구코드 수확)로 간주.
        meta_path = os.path.join(CORPUS_DIR, "labels_correct.meta.jsonl")
        drop_bal: set = set()
        if os.path.exists(meta_path):
            for ln in open(meta_path, encoding="utf-8"):
                try:
                    rec = json.loads(ln)
                except json.JSONDecodeError:
                    continue
                if not rec.get("src") or rec.get("src") in excl_sources:
                    drop_bal.add(rec.get("path"))
        n0b = len(bals)
        bals = {p: g for p, g in bals.items() if p not in drop_bal}
        print(f"[build_dataset] 기준셋 balance 제외: {n0b:,} -> {len(bals):,} "
              f"(-{n0b - len(bals):,}) · 리키잉-구세대 balance 의 기준셋 잔재는 meta 없어 "
              f"식별불가(순한 오염, 신규 수확부터 src 로 완전 차단)")

    cols = set(c.strip() for c in (args.columns or "").split(",") if c.strip())
    if (args.columns or args.min_match is not None or args.raw_only
            or args.reconstruct_number_labels or excl_sources):
        n0 = len(fails)
        fails = _column_filter(fails, cols, args.min_match, raw_only=args.raw_only,
                               reconstruct_numbers=args.reconstruct_number_labels,
                               exclude_sources=excl_sources)
        print(f"[build_dataset] column/match filter: failure {n0:,} -> {len(fails):,} "
              f"(columns={sorted(cols) or 'all'}, min_match={args.min_match}, "
              f"raw_only={args.raw_only}, reconstruct_num={args.reconstruct_number_labels})")
    if args.hangul_min > 0:
        n0 = len(fails)
        _hang = re.compile(r"[가-힣]")
        fails = {p: gt for p, gt in fails.items() if len(_hang.findall(gt)) >= args.hangul_min}
        print(f"[build_dataset] hangul filter(>= {args.hangul_min}자): "
              f"failure {n0:,} -> {len(fails):,}")
    _label_gate(fails)   # 학습 전 육안 게이트: 인쇄형 보존율 0%대면 돌리지 말 것
    if not fails and not bals:
        print(f"no labels in {CORPUS_DIR} (run finetune_crops[_balance] first)"); return 2

    fail_items = list(fails.items())
    # ★balance/anchor 를 글자종류로 구성 — 라운드에 따라 base balance 와 반대편 앵커가 뒤바뀜:
    #  품명 라운드: balance=한글(--balance-hangul-min), 앵커=숫자 소량(--number-anchor-ratio)
    #  숫자 라운드: balance=숫자(--balance-digit-min),  앵커=한글 크게(--hangul-anchor-ratio=품명보존)
    # 반대편을 대량 학습하면 형식혼재/망각으로 회귀(1차 실측: 숫자 앵커 13%→숫자 −18.8%p).
    _hang2 = re.compile(r"[가-힣]")
    _digit = re.compile(r"[0-9]")
    kor_bal = {p: g for p, g in bals.items() if _hang2.search(g)}
    num_bal = {p: g for p, g in bals.items() if not _hang2.search(g) and _digit.search(g)}

    if args.balance_digit_min > 0:                       # 숫자 라운드: base balance = 숫자
        bal_items = list(num_bal.items())
        print(f"[build_dataset] balance = 숫자 {len(num_bal):,} (한글 {len(kor_bal):,}) — 숫자 라운드")
    elif (args.balance_hangul_min > 0 or args.number_anchor_ratio > 0
          or args.hangul_anchor_ratio > 0):              # 품명 라운드: base balance = 한글
        bal_items = [(p, g) for p, g in kor_bal.items()
                     if len(_hang2.findall(g)) >= max(1, args.balance_hangul_min)]
        print(f"[build_dataset] balance = 한글 {len(bal_items):,} (숫자 {len(num_bal):,}) — 품명 라운드")
    else:
        bal_items = list(bals.items())                   # 구 동작(전필드 balance)

    # base balance 를 failure 대비 ratio 로 샘플(deterministic)
    want_bal = int(len(fail_items) * args.balance_ratio)
    if 0 <= want_bal < len(bal_items):
        random.Random(args.seed).shuffle(bal_items)
        bal_items = bal_items[:want_bal]

    # 반대편 앵커(망각방지): 숫자앵커=num_bal / 한글(품명)앵커=kor_bal. failure 대비 ratio 만큼.
    def _sample(pool: dict, ratio: float, seed_off: int) -> list:
        if ratio <= 0 or not pool:
            return []
        items = list(pool.items())
        random.Random(args.seed + seed_off).shuffle(items)
        return items[:int(len(fail_items) * ratio)]
    num_anchor = _sample(num_bal, args.number_anchor_ratio, 2)
    hangul_anchor = _sample(kor_bal, args.hangul_anchor_ratio, 3)
    anchor_items = num_anchor + hangul_anchor
    if num_anchor:
        print(f"[build_dataset] 숫자 앵커: {len(num_anchor):,} (failure×{args.number_anchor_ratio})")
    if hangul_anchor:
        print(f"[build_dataset] 품명(한글) 앵커: {len(hangul_anchor):,} (failure×{args.hangul_anchor_ratio})")

    # 총량 상한: failure·앵커 보존, base balance 를 줄여 상한 맞춤.
    if args.max_train and len(fail_items) + len(bal_items) + len(anchor_items) > args.max_train:
        keep_bal = max(0, args.max_train - len(fail_items) - len(anchor_items))
        random.Random(args.seed + 1).shuffle(bal_items)
        bal_items = bal_items[:keep_bal]
        print(f"[build_dataset] max-train {args.max_train:,}: failure {len(fail_items):,} + "
              f"anchor {len(anchor_items):,} 보존 + balance {len(bal_items):,}")

    combined = fail_items + bal_items + anchor_items   # rel paths distinct (separate dirs)
    tr, va, te = _split(combined, args.val, args.test, args.seed)

    # Build a path -> originating column map for honest held-out slices.  Failure
    # crop names can be reconstructed from ledger identity; correctly-read
    # balance crops carry the sidecar written by finetune_crops_balance.
    path_meta: dict[str, dict] = {}
    try:
        from finetune_crops import crop_name
        from finetune_ledger import CORPUS_PATH
        if os.path.exists(CORPUS_PATH):
            for line in open(CORPUS_PATH, encoding="utf-8"):
                try:
                    entry = json.loads(line)
                    path_meta["crops/" + crop_name(entry)] = {
                        "column": entry.get("column"), "source": "failure"
                    }
                except (json.JSONDecodeError, KeyError):
                    continue
        balance_meta = os.path.join(CORPUS_DIR, "labels_correct.meta.jsonl")
        if os.path.exists(balance_meta):
            for line in open(balance_meta, encoding="utf-8"):
                try:
                    entry = json.loads(line)
                    path_meta[entry["path"]] = {
                        "column": entry.get("column"), "source": entry.get("source", "balance")
                    }
                except (json.JSONDecodeError, KeyError):
                    continue
    except Exception as exc:
        print(f"[build_dataset] metadata warning: {exc}")

    os.makedirs(DATASET_DIR, exist_ok=True)
    for name, rows in (("train", tr), ("val", va), ("test", te)):
        tmp = os.path.join(DATASET_DIR, name + ".txt.tmp")
        with open(tmp, "w", encoding="utf-8") as fh:
            for rel, gt in rows:
                fh.write(f"{rel}\t{gt}\n")
        os.replace(tmp, os.path.join(DATASET_DIR, name + ".txt"))

    split_meta_path = os.path.join(DATASET_DIR, "split_metadata.jsonl")
    tmp_meta = split_meta_path + ".tmp"
    fail_paths = {p for p, _ in fail_items}
    num_anchor_paths = {p for p, _ in num_anchor}
    hangul_anchor_paths = {p for p, _ in hangul_anchor}
    with open(tmp_meta, "w", encoding="utf-8") as fh:
        for split, split_rows in (("train", tr), ("val", va), ("test", te)):
            for rel, _ in split_rows:
                meta = path_meta.get(rel, {})
                source = ("failure" if rel in fail_paths else
                          "numberAnchor" if rel in num_anchor_paths else
                          "hangulAnchor" if rel in hangul_anchor_paths else
                          meta.get("source", "balance"))
                fh.write(json.dumps({"split": split, "path": rel,
                                     "source": source, "column": meta.get("column")},
                                    ensure_ascii=False) + "\n")
    os.replace(tmp_meta, split_meta_path)

    manifest = {
        "corpusDir": CORPUS_DIR,
        "dataDirForPaddle": CORPUS_DIR,
        "counts": {"failure": len(fail_items), "balanceAvailable": len(bals),
                   "balanceUsed": len(bal_items), "numberAnchor": len(num_anchor),
                   "hangulAnchor": len(hangul_anchor), "combined": len(combined),
                   "train": len(tr), "val": len(va), "test": len(te)},
        "policy": {"balanceRatio": args.balance_ratio, "val": args.val,
                   "test": args.test, "seed": args.seed,
                   "columns": sorted(cols), "minMatch": args.min_match,
                   "hangulMin": args.hangul_min, "rawOnly": args.raw_only,
                   "reconstructNumberLabels": args.reconstruct_number_labels,
                   "balanceHangulMin": args.balance_hangul_min,
                   "balanceDigitMin": args.balance_digit_min,
                   "numberAnchorRatio": args.number_anchor_ratio,
                   "hangulAnchorRatio": args.hangul_anchor_ratio,
                   "maxTrain": args.max_train},
        "splitMetadata": os.path.basename(split_meta_path),
    }
    json.dump(manifest, open(os.path.join(DATASET_DIR, "manifest.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)

    sys.stdout.reconfigure(errors="replace")
    # 최종 학습셋 글자종류 구성(품명 라운드 확인용): 한글이 주도해야 정상
    _kh = sum(1 for _, g in combined if _hang2.search(g))
    _kn = sum(1 for _, g in combined if not _hang2.search(g) and _digit.search(g))
    _pct = lambda v: 100.0 * v / (len(combined) or 1)
    print(f"[build_dataset] 학습셋 구성: 한글 {_kh:,}({_pct(_kh):.0f}%) · "
          f"숫자 {_kn:,}({_pct(_kn):.0f}%) · 기타 {len(combined)-_kh-_kn:,}")
    print(f"[build_dataset] failure={len(fail_items)} balance={len(bal_items)}/{len(bals)} "
          f"anchor={len(anchor_items)} -> train={len(tr)} val={len(va)} test={len(te)}")
    print(f"[build_dataset] lists -> {DATASET_DIR}/(train|val|test).txt  + manifest.json")
    print(f"[build_dataset] PaddleOCR data_dir = {CORPUS_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
