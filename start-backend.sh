#!/bin/bash
set -e
source ~/OCR/ocr-server/.venv/bin/activate
cd ~/OCR/ocr-server
mkdir -p ~/OCR/logs
echo "[$(date +'%F %T')] Backend starting on 0.0.0.0:9099 (uvicorn, 3 workers)"
# 3 워커 = 4 vCPU 중 3개 병렬로 CPU 전처리 처리(1개는 eval/OS 몫). 워커당 모델 ~3GB GPU(3개≈9GB<15GB T4).
# python main.py 와 동일한 앱(main:app)을 띄우되 워커만 늘린 것 — main.py 로직은 불변.
exec uvicorn main:app --host 0.0.0.0 --port 9099 --workers 3 2>&1 | tee -a ~/OCR/logs/backend.log
