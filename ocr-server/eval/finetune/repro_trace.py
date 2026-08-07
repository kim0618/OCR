"""Minimal, opt-in instrumentation for Paddle training reproducibility.

The tracer hashes the data returned by the first DataLoader iteration and the
parameters/gradients around the first optimizer step.  No tensor contents are
persisted.  It is deliberately installed before PaddleX imports its training
engine so the monkey patches also cover objects created by PaddleOCR.
"""

from __future__ import annotations

import atexit
import argparse
import hashlib
import json
import os
import platform
import random
import sys
import threading
import time
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import paddle


def _hash_update(hasher: "hashlib._Hash", value: Any) -> None:
    if isinstance(value, paddle.Tensor):
        array = value.detach().cpu().numpy()
        hasher.update(b"tensor\0")
        hasher.update(str(array.dtype).encode())
        hasher.update(repr(tuple(array.shape)).encode())
        hasher.update(array.tobytes(order="C"))
        return
    if isinstance(value, np.ndarray):
        hasher.update(b"ndarray\0")
        hasher.update(str(value.dtype).encode())
        hasher.update(repr(tuple(value.shape)).encode())
        hasher.update(value.tobytes(order="C"))
        return
    if isinstance(value, dict):
        hasher.update(b"dict\0")
        for key in sorted(value, key=lambda item: repr(item)):
            _hash_update(hasher, key)
            _hash_update(hasher, value[key])
        return
    if isinstance(value, (list, tuple)):
        hasher.update(type(value).__name__.encode() + b"\0")
        for item in value:
            _hash_update(hasher, item)
        return
    hasher.update(type(value).__name__.encode() + b"\0")
    hasher.update(repr(value).encode("utf-8", errors="backslashreplace"))


def _digest(value: Any) -> str:
    hasher = hashlib.sha256()
    _hash_update(hasher, value)
    return hasher.hexdigest()


def _parameters(optimizer: paddle.optimizer.Optimizer) -> list[paddle.Tensor]:
    result: list[paddle.Tensor] = []

    def add(value: Any) -> None:
        if isinstance(value, paddle.Tensor):
            result.append(value)
        elif isinstance(value, dict):
            for key in ("params", "parameters"):
                if key in value:
                    add(value[key])
        elif isinstance(value, (list, tuple)):
            for item in value:
                add(item)

    add(getattr(optimizer, "_parameter_list", []))
    if not result:
        add(getattr(optimizer, "_param_groups", []))

    unique: dict[str, paddle.Tensor] = {}
    for index, parameter in enumerate(result):
        name = getattr(parameter, "name", "") or f"unnamed_{index:06d}"
        unique[name] = parameter
    return [unique[name] for name in sorted(unique)]


def _parameter_digest(parameters: Iterable[paddle.Tensor], gradients: bool) -> str:
    hasher = hashlib.sha256()
    for parameter in parameters:
        hasher.update((getattr(parameter, "name", "") or "unnamed").encode())
        tensor = parameter.grad if gradients else parameter
        if tensor is None:
            hasher.update(b"<none>")
        else:
            _hash_update(hasher, tensor)
    return hasher.hexdigest()


class ReproTracer:
    def __init__(self, output_dir: str | Path, seed: int) -> None:
        self.output_dir = Path(output_dir).resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.trace_path = self.output_dir / "trace.json"
        self._lock = threading.RLock()
        self.seed = seed
        self.started_at = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        self.loaders: list[dict[str, Any]] = []
        self.samplers: list[dict[str, Any]] = []
        self.first_backward: dict[str, Any] | None = None
        self.first_step: dict[str, Any] | None = None
        self.latest_batch: dict[str, Any] | None = None
        self.latest_indices: dict[str, Any] | None = None
        self._loader_count = 0
        self._sampler_count = 0
        self._save()

    def _payload(self) -> dict[str, Any]:
        return {
            "format": 1,
            "startedAt": self.started_at,
            "seed": self.seed,
            "environment": {
                "python": sys.version,
                "platform": platform.platform(),
                "paddle": paddle.__version__,
                "cuda": str(paddle.version.cuda()),
                "cudnn": str(paddle.version.cudnn()),
                "device": paddle.device.get_device(),
                "argv": sys.argv,
                "flags": {
                    name: os.environ.get(name)
                    for name in (
                        "FLAGS_cudnn_deterministic",
                        "FLAGS_cudnn_exhaustive_search",
                        "PYTHONHASHSEED",
                        "OCR_FIXED_TRAIN_SEED",
                        "OCR_TRAIN_SEED_PATCHED",
                    )
                },
            },
            "loaders": self.loaders,
            "samplers": self.samplers,
            "firstBackward": self.first_backward,
            "firstOptimizerStep": self.first_step,
        }

    def _save(self) -> None:
        with self._lock:
            temporary = self.trace_path.with_suffix(".json.tmp")
            temporary.write_text(
                json.dumps(self._payload(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            temporary.replace(self.trace_path)

    def start_loader(self) -> dict[str, Any]:
        with self._lock:
            self._loader_count += 1
            entry = {"index": self._loader_count, "batches": []}
            self.loaders.append(entry)
            return entry

    def record_batch(self, loader: dict[str, Any], index: int, batch: Any) -> None:
        # The first two batches are enough to distinguish order/augmentation drift
        # without synchronising every training batch back to the CPU.
        if index > 2:
            return
        entry = {"index": index, "sha256": _digest(batch)}
        with self._lock:
            loader["batches"].append(entry)
            self.latest_batch = {
                "loaderIndex": loader["index"],
                "batchIndex": index,
                "sha256": entry["sha256"],
            }
            self._save()

    def start_sampler(self, sampler_type: str) -> dict[str, Any]:
        with self._lock:
            self._sampler_count += 1
            entry = {"index": self._sampler_count, "type": sampler_type, "batches": []}
            self.samplers.append(entry)
            return entry

    def record_indices(self, sampler: dict[str, Any], index: int, indices: Any) -> None:
        if index > 2:
            return
        entry = {
            "index": index,
            "sha256": _digest(indices),
            "indices": list(indices) if isinstance(indices, (list, tuple)) else repr(indices),
        }
        with self._lock:
            sampler["batches"].append(entry)
            self.latest_indices = {
                "samplerIndex": sampler["index"],
                "batchIndex": index,
                "sha256": entry["sha256"],
            }
            self._save()

    def before_step(self, optimizer: paddle.optimizer.Optimizer) -> None:
        if self.first_step is not None:
            return
        parameters = _parameters(optimizer)
        with self._lock:
            self.first_step = {
                "parameterCount": len(parameters),
                "latestBatch": self.latest_batch,
                "latestIndices": self.latest_indices,
                "parametersBeforeSha256": _parameter_digest(parameters, gradients=False),
                "gradientsSha256": _parameter_digest(parameters, gradients=True),
                "parametersAfterSha256": None,
            }
            self._save()

    def record_backward(self, loss: paddle.Tensor) -> None:
        if self.first_backward is not None:
            return
        array = loss.detach().cpu().numpy()
        with self._lock:
            if self.first_backward is not None:
                return
            self.first_backward = {
                "sha256": _digest(loss),
                "dtype": str(array.dtype),
                "shape": list(array.shape),
                "value": array.tolist(),
                "latestBatch": self.latest_batch,
            }
            self._save()

    def after_step(self, optimizer: paddle.optimizer.Optimizer) -> None:
        if not self.first_step or self.first_step["parametersAfterSha256"] is not None:
            return
        with self._lock:
            self.first_step["parametersAfterSha256"] = _parameter_digest(
                _parameters(optimizer), gradients=False
            )
            self._save()


def install(output_dir: str | Path, seed: int = 1024) -> ReproTracer:
    random.seed(seed)
    np.random.seed(seed)
    paddle.seed(seed)

    tracer = ReproTracer(output_dir, seed)

    original_loader_init = paddle.io.DataLoader.__init__
    original_loader_iter = paddle.io.DataLoader.__iter__

    def wrap_sampler_class(sampler: Any) -> None:
        if sampler is None:
            return
        sampler_class = type(sampler)
        original_sampler_iter = sampler_class.__dict__.get("__iter__")
        if original_sampler_iter is None or getattr(
            original_sampler_iter, "_repro_traced", False
        ):
            return

        def traced_sampler_iter(instance):
            entry = tracer.start_sampler(sampler_class.__name__)
            for index, indices in enumerate(original_sampler_iter(instance), start=1):
                tracer.record_indices(entry, index, indices)
                yield indices

        traced_sampler_iter._repro_traced = True
        sampler_class.__iter__ = traced_sampler_iter

    def traced_loader_init(loader: paddle.io.DataLoader, *args, **kwargs):
        batch_sampler = kwargs.get("batch_sampler")
        if batch_sampler is None and len(args) >= 2:
            batch_sampler = args[1]
        wrap_sampler_class(batch_sampler)
        return original_loader_init(loader, *args, **kwargs)

    def traced_loader_iter(loader: paddle.io.DataLoader):
        entry = tracer.start_loader()
        iterator = original_loader_iter(loader)
        for index, batch in enumerate(iterator, start=1):
            tracer.record_batch(entry, index, batch)
            yield batch

    paddle.io.DataLoader.__init__ = traced_loader_init
    paddle.io.DataLoader.__iter__ = traced_loader_iter

    original_backward = paddle.Tensor.backward

    def traced_backward(tensor: paddle.Tensor, *args, **kwargs):
        tracer.record_backward(tensor)
        return original_backward(tensor, *args, **kwargs)

    paddle.Tensor.backward = traced_backward

    for sampler_name in ("BatchSampler", "DistributedBatchSampler"):
        sampler_class = getattr(paddle.io, sampler_name, None)
        if sampler_class is None:
            continue
        original_sampler_iter = sampler_class.__dict__.get("__iter__")
        if original_sampler_iter is None:
            continue

        def make_sampler_iter(iter_method, type_name):
            def traced_sampler_iter(sampler):
                entry = tracer.start_sampler(type_name)
                for index, indices in enumerate(iter_method(sampler), start=1):
                    tracer.record_indices(entry, index, indices)
                    yield indices

            traced_sampler_iter._repro_traced = True
            return traced_sampler_iter

        sampler_class.__iter__ = make_sampler_iter(original_sampler_iter, sampler_name)

    optimizer_base = paddle.optimizer.Optimizer
    for candidate in vars(paddle.optimizer).values():
        if not isinstance(candidate, type) or not issubclass(candidate, optimizer_base):
            continue
        original_step = candidate.__dict__.get("step")
        if original_step is None or getattr(original_step, "_repro_traced", False):
            continue

        def make_step(step_method):
            def traced_step(self, *args, **kwargs):
                tracer.before_step(self)
                result = step_method(self, *args, **kwargs)
                tracer.after_step(self)
                return result

            traced_step._repro_traced = True
            return traced_step

        candidate.step = make_step(original_step)

    atexit.register(tracer._save)
    return tracer


def checkpoint_digest(path: str | Path) -> str:
    """Hash checkpoint values, independent of pickle/container byte layout."""
    return _digest(paddle.load(str(path)))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", required=True)
    args = parser.parse_args()
    print(checkpoint_digest(args.checkpoint))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
