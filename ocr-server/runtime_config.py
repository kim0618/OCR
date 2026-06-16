"""Deployment runtime switch — committed values = LOCAL CPU baseline.

main.py imports these so its logic stays single-source; ONLY this file differs
between local(cpu) and AWS(gpu). No more sed-on-deploy / main.py divergence.

Deploy to AWS GPU:  cp runtime_config.gpu.py runtime_config.py   (or edit values below)
On AWS->repo push:  exclude runtime_config.py so gpu values don't overwrite the
                    cpu baseline (replaces the old `git reset main.py` rule).

  knob                | local cpu            | AWS gpu
  --------------------|----------------------|-------------------------
  DEVICE              | "cpu"                | "gpu"
  DET_MODEL           | PP-OCRv5_mobile_det  | PP-OCRv5_server_det
  INVOICE_OCR_MAX_W   | 950  (speed)         | 2000 (dense-table hi-res)
  DET_LIMIT_SIDE_LEN  | 960  (engine cap)    | 2000 (lift det input cap)

rec model stays korean_PP-OCRv5_mobile_rec on both (no Korean server rec model).
INVOICE_OCR_MAX_W only affects documentType == "invoice_statement"; other doc
types keep the 950 receipt-tuned ceiling regardless.
"""

DEVICE = "cpu"
DET_MODEL = "PP-OCRv5_mobile_det"
INVOICE_OCR_MAX_W = 950
DET_LIMIT_SIDE_LEN = 960
