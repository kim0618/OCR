"""AWS GPU deploy values.  Deploy:  cp runtime_config.gpu.py runtime_config.py

Keep this knob list in sync with runtime_config.py's docstring. This file is the
gpu counterpart template; the live import target is always runtime_config.py.
"""

# 036 전수분해 결론(2026-06-16): server_det + 고해상(2000) 둘 다 net-negative.
#  - server_det 가 dense 28행 한국어 표를 행병합·오인식(1-1 cell 78→12%, 해상도로 안풀림).
#  - 2000px 는 단일행 문서를 과분할(phantom rows) → fallback 파서 교란(구조 162→240).
# 결론: GPU 는 '속도 전용'(orientation 4방향·워프를 타임아웃 없이). det/해상도는 034 클린값 유지.
# server_det 는 일단 보류; 필요시 dense-표 한정 box param 튜닝으로 별도 재시도.
DEVICE = "gpu"
DET_MODEL = "PP-OCRv5_mobile_det"
INVOICE_OCR_MAX_W = 950
DET_LIMIT_SIDE_LEN = 960
