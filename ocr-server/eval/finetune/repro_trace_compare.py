"""Compare two run directories produced by run-finetune.sh --repro-trace."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def _run_dir(value: str) -> Path:
    path = Path(value)
    if (path / "dataset" / "repro_trace" / "trace.json").is_file():
        return path
    candidate = Path("eval/finetune/versions") / f"run_{value}"
    if (candidate / "dataset" / "repro_trace" / "trace.json").is_file():
        return candidate
    raise FileNotFoundError(f"repro trace not found: {value}")


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _first_batch(trace: dict[str, Any]) -> str | None:
    step_batch = (trace.get("firstOptimizerStep") or {}).get("latestBatch") or {}
    if step_batch.get("sha256"):
        return step_batch["sha256"]
    for loader in trace.get("loaders", []):
        batches = loader.get("batches", [])
        if batches:
            return batches[0].get("sha256")
    return None


def _first_indices(trace: dict[str, Any]) -> str | None:
    # DataLoader may prefetch sampler batch 2 before optimizer step 1. Comparing
    # latestIndices incorrectly reported the second batch as the first divergence.
    for sampler in trace.get("samplers", []):
        batches = sampler.get("batches", [])
        if batches:
            return batches[0].get("sha256")
    return None


def _checkpoint_hash(run_dir: Path) -> str | None:
    path = run_dir / "dataset" / "repro_trace" / "checkpoint.values.sha256"
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8").split()[0]


def _first_loss(trace: dict[str, Any]) -> str | None:
    return (trace.get("firstBackward") or {}).get("sha256")


def _dataset_hash(run_dir: Path) -> str | None:
    hasher = hashlib.sha256()
    dataset_dir = run_dir / "dataset"
    found = False
    for name in ("train.txt", "val.txt", "test.txt", "manifest.json", "dict.txt"):
        path = dataset_dir / name
        if not path.is_file():
            continue
        found = True
        hasher.update(name.encode())
        hasher.update(path.read_bytes())
    return hasher.hexdigest() if found else None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_a")
    parser.add_argument("run_b")
    args = parser.parse_args()

    run_a, run_b = _run_dir(args.run_a), _run_dir(args.run_b)
    trace_a = _read(run_a / "dataset" / "repro_trace" / "trace.json")
    trace_b = _read(run_b / "dataset" / "repro_trace" / "trace.json")
    step_a = trace_a.get("firstOptimizerStep") or {}
    step_b = trace_b.get("firstOptimizerStep") or {}

    checks = [
        ("dataset_bundle", _dataset_hash(run_a), _dataset_hash(run_b)),
        ("first_sample_indices", _first_indices(trace_a), _first_indices(trace_b)),
        ("first_batch", _first_batch(trace_a), _first_batch(trace_b)),
        ("initial_parameters", step_a.get("parametersBeforeSha256"), step_b.get("parametersBeforeSha256")),
        ("first_loss", _first_loss(trace_a), _first_loss(trace_b)),
        ("first_gradients", step_a.get("gradientsSha256"), step_b.get("gradientsSha256")),
        ("after_first_step", step_a.get("parametersAfterSha256"), step_b.get("parametersAfterSha256")),
        ("epoch1_checkpoint", _checkpoint_hash(run_a), _checkpoint_hash(run_b)),
    ]

    print(f"A: {run_a}")
    print(f"B: {run_b}")
    first_difference = None
    for name, value_a, value_b in checks:
        both_missing = value_a is None and value_b is None
        same = value_a is not None and value_a == value_b
        status = "MISSING" if both_missing else ("SAME" if same else "DIFF")
        print(f"{name:22} {status:7}  {value_a or '(missing)'}  {value_b or '(missing)'}")
        if not both_missing and not same and first_difference is None:
            first_difference = name

    if first_difference is None:
        print("RESULT: epoch 1까지 완전 동일합니다.")
        return 0
    if first_difference == "dataset_bundle":
        reason = "동결 데이터셋 파일이 서로 다릅니다."
    elif first_difference == "first_sample_indices":
        reason = "DataLoader shuffle/sampler 순서가 다릅니다."
    elif first_difference == "first_batch":
        reason = "샘플 순서는 같지만 augmentation 또는 전처리 결과가 다릅니다."
    elif first_difference == "initial_parameters":
        reason = "시작 가중치가 다릅니다."
    elif first_difference == "first_loss":
        reason = "같은 입력/가중치에서 forward 또는 loss 계산이 갈라졌습니다."
    elif first_difference == "first_gradients":
        if _first_loss(trace_a) is not None and _first_loss(trace_b) is not None:
            reason = "loss까지 같지만 backward gradient 계산이 갈라졌습니다."
        else:
            reason = "gradient가 갈라졌습니다. loss 계측이 없어 forward/backward 구분은 불가합니다."
    elif first_difference == "after_first_step":
        reason = "gradient까지 같지만 optimizer update가 갈라졌습니다."
    else:
        reason = "첫 스텝은 같고 그 이후 epoch 1 안에서 갈라졌습니다."
    print(f"RESULT: 최초 차이={first_difference} - {reason}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
