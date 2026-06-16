# GPU A/B: 034 클린값 + DEVICE만 gpu (server_det/고해상 롤백)
DEVICE = "gpu"
DET_MODEL = "PP-OCRv5_mobile_det"
INVOICE_OCR_MAX_W = 950
DET_LIMIT_SIDE_LEN = 960
ORIENT_FULL_4WAY_512 = False  # P1 롤백(039 net-negative: 큰표 오회전으로 셀73→45%). 상세=gpu.py
