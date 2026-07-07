import numpy as np
from matplotlib.backends.backend_agg import FigureCanvasAgg as _Canvas

if not hasattr(_Canvas, "tostring_rgb"):
    _Canvas.tostring_rgb = lambda self: np.asarray(self.buffer_rgba())[..., :3].tobytes()

from paddlex.engine import Engine

def main():
    return Engine().run()

if __name__ == "__main__":
    main()
