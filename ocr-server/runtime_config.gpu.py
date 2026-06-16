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
# P1(039 net-negative, 롤백): 무조건 4방향+512는 6-2/6-3(작은표) 살리나 1.jpg/1-2(큰표)를
# 오회전(0°→90°)해 셀 73→45%·base 85→22% 폭락. early-stop이 맞던 방향을 512 스코어러가 재채점해
# 틀린 방향이 이김. '확신하며 맞음'vs'확신하며 틀림'을 confidence로 구분 불가 → 무조건 4방향은 틀린 도구.
# 6-2/3-2 오리엔트 미스파이어는 별도 targeted 방법으로(스코어러 개선) 후순위.
ORIENT_FULL_4WAY_512 = False
# P3(040 net-negative, 롤백): 투영기반 deskew가 dense 28행표 주기성에 락온→1-1 가짜 -3.5°→
# straight한 표를 돌려 셀 77→44%(투영=테두리락온과 같은 실패계열). 진짜기운 4-1(+20)은 살렸으나
# 1-1 손실이 큼. 재설계=OCR bbox 각도(P0 신뢰소스)로 전환 예정. 그때까지 OFF.
IMAGE_TEXT_DESKEW_PROJECTION = False
# P3'(bbox 기반): 1차 OCR 텍스트라인 bbox 중앙각으로 진짜 기울기 판정→회전 후 재OCR.
# dense표=0°라 스킵(1-1 안 건드림), 진짜 기운 sparse(4-1)만 보정. 재OCR 2-pass(기운 장만).
IMAGE_BBOX_DESKEW_REOCR = True
