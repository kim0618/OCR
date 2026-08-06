import sys

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
        from repro_trace import install

        install(trace_dir, seed=seed)


_install_repro_trace()

from paddlex.engine import Engine

def main():
    return Engine().run()

if __name__ == "__main__":
    main()
