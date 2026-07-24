#!/bin/bash
set -eo pipefail
export PYTHONUNBUFFERED=1
# RUN_HISTORY AWS 예상요금(실행시간×단가). 인스턴스/계약에 맞는 값을 서버 env에 지정:
# export AWS_INSTANCE_TYPE=g6.xlarge AWS_REGION=ap-northeast-2 AWS_PURCHASE_OPTION=OnDemand AWS_EC2_HOURLY_USD=<시간당 USD>
source ~/OCR/ocr-server/.venv/bin/activate
cd ~/OCR/ocr-server
mkdir -p ~/OCR/logs
stdbuf -oL -eL python -u eval/run_all.py --all 2>&1 | tee -a ~/OCR/logs/eval.log
echo "==================== 학습 끝 [$(date +'%F %T')] ===================="
echo "최신 결과: $(ls -1dt eval/runs/*/ | head -1)"
