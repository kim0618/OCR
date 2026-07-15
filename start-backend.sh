#!/bin/bash
set -e
source ~/OCR/ocr-server/.venv/bin/activate
cd ~/OCR/ocr-server
mkdir -p ~/OCR/logs
echo "[$(date +'%F %T')] Backend starting on 0.0.0.0:9099 (uvicorn, 2 workers)"
# 워커 수 = GPU VRAM 안전선. T4(g4dn, 16GB)=2워커(3워커는 91% OOM). L4(g6, 24GB)=3워커 가능.
#   ★ g6.xlarge/g6.2xlarge(L4 24GB)에서 실행 = 3. g4dn(T4)로 폴백하면 반드시 2로 되돌릴 것
#     (안 그러면 고해상 이미지에서 VRAM OOM→요청 드롭 재발).
# 시스템 RAM(16GB)·vCPU(4)는 g6.xlarge도 동일 → run_batch 의 "고해상 1장/동시 3장"은 그대로 유지.
# python main.py 와 동일한 앱(main:app)을 띄우되 워커만 늘린 것 — main.py 로직은 불변.
exec uvicorn main:app --host 0.0.0.0 --port 9099 --workers 3 2>&1 | tee -a ~/OCR/logs/backend.log
