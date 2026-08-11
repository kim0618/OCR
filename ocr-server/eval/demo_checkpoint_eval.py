"""Evaluate one exported demo checkpoint on the held-out target crops only.

This is intentionally smaller than ``demo_report.py``: epoch-ladder checkpoints are
experimental points, not new demo rounds, so they must not create numbered report
directories or update the demo summary.  The output JSON is stored beside the archived
checkpoint and is used as the hard 26/26 gate before the full 45k scan is interpreted.

Example (from ``ocr-server/``)::

    python eval/demo_checkpoint_eval.py \
      --model-dir eval/finetune/versions/run_260806_1200/epochs/epoch_08/inference \
      --output eval/finetune/versions/run_260806_1200/epochs/epoch_08/TARGET_EVAL.json \
      --tag 260806_1200_ep08
"""
from __future__ import annotations

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from finetune_ledger import CORPUS_DIR  # noqa: E402
from finetune_report import BASE_MODEL, predict_all  # noqa: E402

# ★판정 기준은 저울(recount_reviewed_gt)과 <같은 함수>를 써야 한다(2026-08-10 사고).
#  저울은 comparable() 로 NFKC·공백을 흡수하는데 판정만 strict 비교였다. 1단계 타깃
#  (세파록스캡슐)은 GT 에 공백이 없어 드러나지 않다가, 2단계 4타깃에서 실패 5건 중
#  4건이 <공백만 다른 정답>으로 잡혀 run 전체가 기각됐다.
sys.path.insert(0, os.path.join(HERE, "finetune", "demo"))
from recount_reviewed_gt import comparable  # noqa: E402

MANIFEST = os.path.join(CORPUS_DIR, "dataset", "manifest.json")
TEST_LIST = os.path.join(CORPUS_DIR, "test.txt")


def _rows() -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    with open(TEST_LIST, encoding="utf-8") as handle:
        for line in handle:
            line = line.rstrip("\n")
            if line and "\t" in line:
                rows.append(tuple(line.split("\t", 1)))
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-dir", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--tag", required=True)
    args = parser.parse_args()

    if not os.path.isdir(args.model_dir):
        raise SystemExit(f"inference 디렉터리가 없습니다: {args.model_dir}")
    if not os.path.exists(MANIFEST):
        raise SystemExit(f"manifest 가 없습니다: {MANIFEST}")
    if not os.path.exists(TEST_LIST):
        raise SystemExit(f"판정 목록이 없습니다: {TEST_LIST}")

    manifest = json.load(open(MANIFEST, encoding="utf-8"))
    if manifest.get("mode") != "demo":
        raise SystemExit("현재 manifest 가 demo 모드가 아닙니다")
    targets = [str(value) for value in manifest.get("targets", [])]
    keys = {target: target.replace(" ", "") for target in targets}
    rows = _rows()
    if not rows:
        raise SystemExit("판정 크롭이 비어 있습니다")

    try:
        from paddlex import create_model
    except ImportError:
        from paddlex.inference import create_model  # type: ignore

    paths = [os.path.join(CORPUS_DIR, rel) for rel, _ in rows]
    predictions = predict_all(create_model(BASE_MODEL, args.model_dir), paths)
    if len(predictions) != len(rows):
        raise SystemExit(f"예측 수 {len(predictions)} != 판정 크롭 수 {len(rows)}")

    by_target: dict[str, dict[str, int | bool]] = {}
    details = []
    for (rel, gt), prediction in zip(rows, predictions):
        target = next((name for name in targets if keys[name] in gt.replace(" ", "")), None)
        ok = comparable(prediction or "") == comparable(gt)
        details.append({"path": rel, "gt": gt, "pred": prediction, "ok": ok,
                        "target": target})
    for target in targets:
        selected = [row for row in details if row["target"] == target]
        passed = sum(bool(row["ok"]) for row in selected)
        by_target[target] = {
            "pass": bool(selected) and passed == len(selected),
            "correct": passed,
            "total": len(selected),
        }

    all_pass = bool(by_target) and all(bool(row["pass"]) for row in by_target.values())
    result = {
        "tag": args.tag,
        "modelDir": os.path.abspath(args.model_dir),
        "summary": {"allPass": all_pass,
                    "correct": sum(bool(row["ok"]) for row in details),
                    "total": len(details)},
        "byTarget": by_target,
        "predictions": details,
    }
    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    temp = args.output + f".tmp.{os.getpid()}"
    try:
        with open(temp, "w", encoding="utf-8") as handle:
            json.dump(result, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, args.output)
    finally:
        if os.path.exists(temp):
            os.remove(temp)

    print(f"[에폭 판정] {args.tag}: {result['summary']['correct']}/{result['summary']['total']} "
          f"({'PASS' if all_pass else 'FAIL'}) → {args.output}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
