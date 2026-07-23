"""Compare base vs fine-tuned recognition on honest held-out slices.

Unlike the legacy implementation, Hangul is not automatically called
``itemName``.  ``build_dataset.py`` preserves each crop's originating column in
``dataset/split_metadata.jsonl``; that metadata gives us a real 품명 slice while
still reporting other Hangul and numeric preservation separately.
"""
from __future__ import annotations

import argparse
import json
import os
import re

from finetune_report import (BASE_MODEL, CORPUS_DIR, PREDICTIONS_JSONL,
                             find_ft_inference, load_test, predict_all)

HANGUL = re.compile(r"[가-힣]")
DIGIT = re.compile(r"[0-9]")
NUMERIC_COLUMNS = {
    "quantity", "unitPrice", "amount", "supplyAmount", "taxAmount",
    "discountAmount", "totalAmount", "itemCode", "lotNo", "expiryDate",
    "manufacturingNo", "buyerBizNumber", "supplierBizNumber", "issueDate",
}
DEFAULT_OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "finetune", "FINETUNE_REPORT_BY_TYPE.json")


def _load_test_metadata() -> dict[str, dict]:
    path = os.path.join(CORPUS_DIR, "dataset", "split_metadata.jsonl")
    result: dict[str, dict] = {}
    if not os.path.exists(path):
        return result
    for line in open(path, encoding="utf-8"):
        try:
            rec = json.loads(line)
            if rec.get("split") == "test":
                result[rec["path"]] = rec
        except (json.JSONDecodeError, KeyError):
            continue
    return result


def _type(gt: str, meta: dict | None = None) -> str:
    meta = meta or {}
    column = meta.get("column")
    if column in ("itemName", "itemNameMaster"):
        return "품명"
    if column in NUMERIC_COLUMNS or meta.get("source") == "numberAnchor":
        return "숫자"
    if HANGUL.search(gt):
        return "한글(기타)"
    if DIGIT.search(gt):
        return "숫자"
    return "기타"


def _exact(preds: list[str], gts: list[str]) -> int:
    return sum(p.strip() == g.strip() for p, g in zip(preds, gts))


def _prediction_cache(rows: list[tuple[str, str, str]]) -> dict[str, dict] | None:
    """Load only when it exactly matches the current held-out path+label set."""
    if not os.path.exists(PREDICTIONS_JSONL):
        return None
    cached: dict[str, dict] = {}
    try:
        for line in open(PREDICTIONS_JSONL, encoding="utf-8"):
            rec = json.loads(line)
            cached[rec["path"]] = rec
    except (OSError, json.JSONDecodeError, KeyError):
        return None
    if len(cached) != len(rows):
        return None
    if any(rel not in cached or cached[rel].get("gt") != gt for _, rel, gt in rows):
        return None
    return cached


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", type=int, default=0, help="타입별 최대 표본(0=전량)")
    parser.add_argument("--json-out", default=DEFAULT_OUT)
    args = parser.parse_args()

    try:
        from paddlex import create_model
    except ImportError:
        from paddlex.inference import create_model  # type: ignore

    rows = load_test()
    cache = _prediction_cache(rows)
    metadata = _load_test_metadata()
    buckets: dict[str, list[tuple[str, str, str]]] = {}
    unknown_column = 0
    for path, rel, gt in rows:
        meta = metadata.get(rel)
        if not meta or not meta.get("column"):
            unknown_column += 1
        buckets.setdefault(_type(gt, meta), []).append((path, rel, gt))

    print("=== held-out test 크롭 구성 ===")
    for label, items in sorted(buckets.items(), key=lambda pair: -len(pair[1])):
        print(f"  {label}: {len(items):,}")
    if unknown_column:
        print(f"  (원본 컬럼 메타데이터 없음: {unknown_column:,} — 글자종류로 분류)")

    total_rows = sum(len(items) for items in buckets.values())
    if args.sample:
        for label in buckets:
            buckets[label] = buckets[label][:args.sample]

    ft_dir = find_ft_inference()
    if not ft_dir:
        raise SystemExit("no fine-tuned inference dir — run export first")
    print(f"\n[모델] base={BASE_MODEL}  ft={ft_dir}")
    base = ft = None
    if cache:
        print(f"[type-report] 전체 리포트 예측 캐시 재사용: {len(cache):,}장")
    else:
        print("[type-report] 예측 캐시 없음/불일치 — 모델 추론 실행")
        base = create_model(BASE_MODEL)
        ft = create_model(BASE_MODEL, ft_dir)

    print(f"\n{'타입':<12}{'n':>8}{'base exact':>12}{'ft exact':>12}{'Δ%p':>8}"
          f"{'개선':>8}{'회귀':>8}{'순증':>8}")
    print("-" * 76)
    groups: dict[str, dict] = {}
    for label, items in sorted(buckets.items(), key=lambda pair: -len(pair[1])):
        paths = [path for path, _, _ in items]
        rels = [rel for _, rel, _ in items]
        gts = [gt for _, _, gt in items]
        if cache:
            base_preds = [cache[rel].get("base") or "" for rel in rels]
            ft_preds = [cache[rel].get("finetuned") or "" for rel in rels]
        else:
            base_preds = predict_all(base, paths)
            ft_preds = predict_all(ft, paths)
        n = len(items)
        base_exact = _exact(base_preds, gts)
        ft_exact = _exact(ft_preds, gts)
        gains = sum(b.strip() != g.strip() and f.strip() == g.strip()
                    for b, f, g in zip(base_preds, ft_preds, gts))
        regressions = sum(b.strip() == g.strip() and f.strip() != g.strip()
                          for b, f, g in zip(base_preds, ft_preds, gts))
        base_pct = 100 * base_exact / n if n else 0.0
        ft_pct = 100 * ft_exact / n if n else 0.0
        groups[label] = {
            "n": n, "baseExact": base_exact, "fineTunedExact": ft_exact,
            "baseExactPct": base_pct, "fineTunedExactPct": ft_pct,
            "deltaPp": ft_pct - base_pct, "gains": gains,
            "regressions": regressions, "netChange": gains - regressions,
        }
        print(f"{label:<12}{n:>8,}{base_pct:>11.1f}%{ft_pct:>11.1f}%"
              f"{ft_pct-base_pct:>+8.1f}{gains:>+8}{-regressions:>8}{gains-regressions:>+8}")

    payload = {
        "schemaVersion": "finetune-slices.v2", "baseModel": BASE_MODEL,
        "fineTunedModel": ft_dir, "metadataCoverage": {
            "knownColumn": total_rows - unknown_column,
            "unknownColumn": unknown_column,
        }, "groups": groups,
    }
    os.makedirs(os.path.dirname(os.path.abspath(args.json_out)), exist_ok=True)
    with open(args.json_out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    print(f"[type-report] wrote {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
