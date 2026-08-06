import os
import sys
from pathlib import Path

import numpy as np
from matplotlib.backends.backend_agg import FigureCanvasAgg as _Canvas

if not hasattr(_Canvas, "tostring_rgb"):
    _Canvas.tostring_rgb = lambda self: np.asarray(self.buffer_rgba())[..., :3].tobytes()

def _install_repro_trace() -> None:
    trace_dir = None
    seed = 1024
    remaining = [sys.argv[0]]
    for argument in sys.argv[1:]:
        if argument.startswith("--repro-trace-dir="):
            trace_dir = argument.split("=", 1)[1]
        elif argument.startswith("--repro-seed="):
            seed = int(argument.split("=", 1)[1])
        else:
            remaining.append(argument)
    sys.argv[:] = remaining
    if trace_dir:
        # PaddleX launches PaddleOCR/tools/train.py in a child Python process.
        # Put a dedicated sitecustomize on that child's import path; patching
        # this thin PaddleX driver does not reach the actual training process.
        bootstrap = Path(__file__).resolve().parent / "repro_bootstrap"
        current_pythonpath = os.environ.get("PYTHONPATH", "")
        os.environ["PYTHONPATH"] = os.pathsep.join(
            part for part in (str(bootstrap), current_pythonpath) if part
        )
        os.environ["OCR_REPRO_TRACE_DIR"] = str(Path(trace_dir).resolve())
        os.environ["OCR_REPRO_SEED"] = str(seed)


_install_repro_trace()

from paddlex.engine import Engine

def main():
    return Engine().run()

if __name__ == "__main__":
    main()
