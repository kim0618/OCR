# GPU A/B: 034 클린값 + DEVICE만 gpu (server_det/고해상 롤백)
DEVICE = "gpu"
DET_MODEL = "PP-OCRv5_mobile_det"
INVOICE_OCR_MAX_W = 1400  # 해상도 테스트: 작은글자(4-3/3-2 8px→950서 2.5px 뭉갬) 살리기. 과분할 재발하면 死
DET_LIMIT_SIDE_LEN = 1400  # 엔진이 1400을 도로 안 줄이게 같이 상향(036 함정)
ORIENT_FULL_4WAY_512 = False  # P1 롤백(039 net-negative: 큰표 오회전으로 셀73→45%). 상세=gpu.py
IMAGE_TEXT_DESKEW_PROJECTION = False  # P3 롤백(040 net-negative: 투영이 dense표서 가짜각→1-1 77→44%)
IMAGE_BBOX_DESKEW_REOCR = True  # P3': bbox 각도(신뢰소스)로 deskew+재OCR. dense=스킵, 진짜기운것만 보정
ORIENT_KOREAN_REVERIFY = True  # P1: 한글다움<0.10(garbage)이면 4방향 재OCR해 한글최다 채택(6-2/6-3 거꾸로 교정)
REFINE_MONEY_COLS_FROM_BODY = True  # 사진 칸밀림: 수량/단가/금액 경계를 본문 money X-클러스터로 snap(swap 교정)
