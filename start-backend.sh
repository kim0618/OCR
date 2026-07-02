#!/bin/bash
set -e
source ~/OCR/ocr-server/.venv/bin/activate
cd ~/OCR/ocr-server
mkdir -p ~/OCR/logs
echo "[$(date +'%F %T')] Backend starting on 0.0.0.0:9099 (uvicorn, 2 workers)"
# 2 워커 = T4 15GB VRAM 안전선. 3워커는 ~14GB(91%)라 고해상 이미지에서 OOM→요청 드롭 발생.
# 2워커면 워커당 VRAM 여유가 생겨 고해상도 안 터짐(완전성 우선). 1워커보다 ~2배 빠름.
# python main.py 와 동일한 앱(main:app)을 띄우되 워커만 늘린 것 — main.py 로직은 불변.
exec uvicorn main:app --host 0.0.0.0 --port 9099 --workers 2 2>&1 | tee -a ~/OCR/logs/backend.log
