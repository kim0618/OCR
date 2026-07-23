"""Collect one fine-tune run into a durable summary and RUN_HISTORY.

This is deliberately separate from the shell script: parsing and schema logic
remain testable on Windows, while AWS only supplies paths/timestamps.
"""
from __future__ import annotations

import argparse
import json
import os
import re
from typing import Any

HERE = os.path.dirname(os.path.abspath(__file__))
CORPUS = os.path.join(HERE, "finetune_corpus")
FINETUNE_DIR = os.path.join(HERE, "finetune")
DEFAULT_CONFIG = os.path.join(FINETUNE_DIR, "config_ppocrv5_rec_finetune.yaml")
DEFAULT_MANIFEST = os.path.join(CORPUS, "dataset", "manifest.json")
DEFAULT_OVERALL = os.path.join(FINETUNE_DIR, "FINETUNE_REPORT.json")
DEFAULT_SLICES = os.path.join(FINETUNE_DIR, "FINETUNE_REPORT_BY_TYPE.json")
LAST_SUMMARY = os.path.join(FINETUNE_DIR, "LAST_RUN_SUMMARY.json")

RE_CONFIG_EPOCHS = re.compile(r"^\s*epochs_iters:\s*(\d+)", re.MULTILINE)
RE_PROGRESS_EPOCH = re.compile(r"(?:epoch:\s*\[|\[ep\s+)(\d+)\s*/\s*(\d+)", re.I)
RE_ANY_EPOCH = re.compile(r"\bepoch\D{0,8}(\d+)\b", re.I)
RE_BEST = re.compile(r"best\s+metric.*?\bacc:\s*([0-9]*\.?[0-9]+)", re.I)


def _read_json(path: str, not_older_than: float | None = None) -> dict[str, Any]:
    try:
        if not_older_than is not None and os.path.getmtime(path) < not_older_than:
            return {}  # a failed report must not leak the previous run into history
        with open(path, encoding="utf-8") as fh:
            value = json.load(fh)
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def parse_training_log(text: str) -> dict[str, Any]:
    """Return completed epoch, best epoch and best validation accuracy."""
    current_epoch = 0
    completed = 0
    best_epoch: int | None = None
    best_acc: float | None = None
    for line in text.splitlines():
        progress = RE_PROGRESS_EPOCH.search(line)
        if progress:
            current_epoch = int(progress.group(1))
            completed = max(completed, current_epoch)
        elif "epoch" in line.lower():
            any_epoch = RE_ANY_EPOCH.search(line)
            if any_epoch:
                current_epoch = int(any_epoch.group(1))
                completed = max(completed, current_epoch)
        metric = RE_BEST.search(line)
        if metric:
            acc = float(metric.group(1))
            if best_acc is None or acc > best_acc:
                best_acc = acc
                best_epoch = current_epoch or None
    return {"epochsCompleted": completed or None, "bestEpoch": best_epoch, "bestAcc": best_acc}


def _planned_epochs(config_path: str) -> int | None:
    try:
        match = RE_CONFIG_EPOCHS.search(open(config_path, encoding="utf-8").read())
        return int(match.group(1)) if match else None
    except OSError:
        return None


def _line_count(path: str) -> int | None:
    try:
        with open(path, encoding="utf-8") as fh:
            return sum(1 for line in fh if line.strip())
    except OSError:
        return None


def describe_criteria(manifest: dict[str, Any]) -> str:
    policy = manifest.get("policy") or {}
    columns = policy.get("columns") or []
    names = {
        "itemName": "품명", "supplierCompany": "공급자명",
        "supplierAddress": "공급자주소", "buyerCompany": "공급받는자명",
        "buyerAddress": "공급받는자주소",
    }
    parts: list[str] = []
    if columns:
        parts.append("·".join(names.get(column, column) for column in columns) + " 중심")
    else:
        parts.append("전 필드")
    if policy.get("hangulMin"):
        parts.append(f"한글 {policy['hangulMin']}자+")
    anchor = policy.get("numberAnchorRatio")
    if anchor:
        parts.append(f"숫자 보존 앵커 {anchor:g}")
    if policy.get("rawOnly"):
        parts.append("원문 라벨")
    return " + ".join(parts)


def build_summary(args: argparse.Namespace) -> dict[str, Any]:
    try:
        log_text = open(args.log, encoding="utf-8", errors="replace").read()
    except OSError:
        log_text = ""
    parsed = parse_training_log(log_text)
    manifest = _read_json(args.manifest)
    try:
        log_mtime = os.path.getmtime(args.log)
    except OSError:
        log_mtime = None
    overall = _read_json(args.overall_report, log_mtime)
    slices = _read_json(args.slice_report, log_mtime)
    groups = slices.get("groups") or {}
    slice_deltas = {
        label: round(float(values["deltaPp"]), 3)
        for label, values in groups.items()
        if isinstance(values, dict) and values.get("deltaPp") is not None
    }
    payload: dict[str, Any] = {
        "schemaVersion": "finetune-run-summary.v1", "kind": "finetune",
        "ts": args.ts, "base": args.base, "criteria": args.criteria or describe_criteria(manifest),
        "images": _line_count(os.path.join(CORPUS, "train.txt")),
        "elapsedSec": args.elapsed, "epochsPlanned": _planned_epochs(args.config),
        **parsed, "overallDeltaPp": overall.get("overallDeltaPp"),
        "netChange": overall.get("netChange"), "sliceDeltas": slice_deltas,
        "comparison": {
            "baseExactPct": overall.get("b_ex"), "fineTunedExactPct": overall.get("f_ex"),
            "baseCharSimilarityPct": overall.get("b_ch"),
            "fineTunedCharSimilarityPct": overall.get("f_ch"),
            "sliceMetadataCoverage": slices.get("metadataCoverage"),
        },
    }
    return {key: value for key, value in payload.items() if value is not None}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ts", required=True)
    parser.add_argument("--base", default="official")
    parser.add_argument("--criteria", default=None)
    parser.add_argument("--elapsed", type=float, required=True)
    parser.add_argument("--log", required=True)
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    parser.add_argument("--manifest", default=DEFAULT_MANIFEST)
    parser.add_argument("--overall-report", default=DEFAULT_OVERALL)
    parser.add_argument("--slice-report", default=DEFAULT_SLICES)
    parser.add_argument("--no-record", action="store_true")
    args = parser.parse_args()

    summary = build_summary(args)
    os.makedirs(FINETUNE_DIR, exist_ok=True)
    with open(LAST_SUMMARY, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    if not args.no_record:
        from run_history import record
        record("finetune", adopted=0, **{key: value for key, value in summary.items()
                                        if key not in ("schemaVersion", "kind", "comparison")})
    print(f"[finetune-summary] {summary.get('ts')}: "
          f"전체 ep {summary.get('epochsCompleted','?')}/{summary.get('epochsPlanned','?')} · "
          f"최고 ep {summary.get('bestEpoch','?')} acc {summary.get('bestAcc','?')}")
    print(f"[finetune-summary] 기준: {summary.get('criteria')}")
    print(f"[finetune-summary] wrote {LAST_SUMMARY}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
