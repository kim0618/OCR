#!/bin/bash
set -e
source ~/OCR/ocr-server/.venv/bin/activate
cd ~/OCR/ocr-server
mkdir -p ~/OCR/logs
echo "[$(date +'%F %T')] Backend starting on 0.0.0.0:9099"
exec python main.py 2>&1 | tee -a ~/OCR/logs/backend.log
