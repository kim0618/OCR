"""Install the repro tracer inside PaddleX's PaddleOCR child process."""

from __future__ import annotations

import os
import sys
from pathlib import Path


trace_dir = os.environ.get("OCR_REPRO_TRACE_DIR")
if trace_dir:
    finetune_dir = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(finetune_dir))
    from repro_trace import install

    install(trace_dir, seed=int(os.environ.get("OCR_REPRO_SEED", "1024")))
