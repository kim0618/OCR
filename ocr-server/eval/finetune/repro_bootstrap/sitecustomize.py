"""Install the repro tracer inside PaddleX's PaddleOCR child process."""

from __future__ import annotations

import os
import sys
from pathlib import Path


trace_dir = os.environ.get("OCR_REPRO_TRACE_DIR")
fixed_train_seed = os.environ.get("OCR_FIXED_TRAIN_SEED")

if fixed_train_seed:
    # PaddleOCR/tools/train.py intentionally calls build_dataloader(..., seed=None).
    # SimpleDataSet then executes random.seed(None), replacing Global.seed with
    # system entropy before it creates the image mapping and augmentations.
    # Import ppocr.data before tools/train.py's `from ppocr.data import ...` and
    # inject the already-declared Global.seed only for the Train loader.
    repo_root = Path.cwd()
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    try:
        import ppocr.data as _ppocr_data
    except ModuleNotFoundError:
        _ppocr_data = None

    if _ppocr_data is not None:
        _original_build_dataloader = _ppocr_data.build_dataloader

        def _deterministic_build_dataloader(
            config, mode, device, logger, seed=None
        ):
            if mode == "Train" and seed is None:
                seed = int(fixed_train_seed)
            return _original_build_dataloader(
                config, mode, device, logger, seed=seed
            )

        _ppocr_data.build_dataloader = _deterministic_build_dataloader
        os.environ["OCR_TRAIN_SEED_PATCHED"] = "1"

if trace_dir:
    finetune_dir = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(finetune_dir))
    from repro_trace import install

    install(trace_dir, seed=int(os.environ.get("OCR_REPRO_SEED", "1024")))
