# GPU A/B: 034 클린값 + DEVICE만 gpu (server_det/고해상 롤백)
DEVICE = "gpu"
DET_MODEL = "PP-OCRv5_mobile_det"
INVOICE_OCR_MAX_W = 950
DET_LIMIT_SIDE_LEN = 960
ORIENT_FULL_4WAY_512 = True  # P1: invoice 무조건 4방향+512. cpu 베이스라인은 False(28행 타임아웃)
