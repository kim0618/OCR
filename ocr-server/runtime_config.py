"""AWS GPU deploy values.  Deploy:  cp runtime_config.gpu.py runtime_config.py

Keep this knob list in sync with runtime_config.py's docstring. This file is the
gpu counterpart template; the live import target is always runtime_config.py.
"""

DEVICE = "gpu"
DET_MODEL = "PP-OCRv5_server_det"
INVOICE_OCR_MAX_W = 2000
DET_LIMIT_SIDE_LEN = 2000
