#!/bin/bash
set -eo pipefail
export PYTHONUNBUFFERED=1
source ~/OCR/ocr-server/.venv/bin/activate
cd ~/OCR/ocr-server
mkdir -p ~/OCR/logs
stdbuf -oL -eL python -u eval/run_all.py --all 2>&1 | tee -a ~/OCR/logs/eval.log
echo "==================== 학습 끝 [$(date +'%F %T')] ===================="
echo "최신 결과: $(ls -1dt eval/runs/*/ | head -1)"
