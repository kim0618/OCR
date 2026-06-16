#!/bin/bash
set -e
cd ~/OCR/mysuit-ocr
mkdir -p ~/OCR/logs
echo "[$(date +'%F %T')] Frontend starting on 0.0.0.0:8089"
exec npm run dev 2>&1 | tee -a ~/OCR/logs/frontend.log
