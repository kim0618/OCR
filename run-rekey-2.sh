#!/bin/bash
# run-rekey-2.sh — 2차: 1차 run(20260720_175949)에 --resume 으로 이어붙이기 + 통합 분석.
# → runs/20260720_175949 에 1+2차 93,708장 통합. learndata/리플레이 원스톱.
# tmux: tmux new -s eval_rekey2; bash ~/OCR/run-rekey-2.sh  (나오기 Ctrl+B D)
set -o pipefail
export PYTHONUNBUFFERED=1
source ~/OCR/ocr-server/.venv/bin/activate
cd ~/OCR/ocr-server
TS1=20260720_175949
echo "==================== 2차 시작 [$(date +%F\ %T)] ===================="
echo "== [OCR] 2차 65,703장 -> run $TS1 에 resume(1차는 skip) =="
stdbuf -oL -eL python -u eval/run_batch.py --resume $TS1 --testset invoice_rekey --workers 3 2>&1 | tee -a ~/OCR/logs/eval_rekey2.log
echo "== [분석] run_all --reuse $TS1 (1+2차 통합 크롭/지표) =="
stdbuf -oL -eL python -u eval/run_all.py --reuse $TS1 --testset invoice_rekey 2>&1 | tee -a ~/OCR/logs/eval_rekey2.log
echo "==================== 2차 끝 [$(date +%F\ %T)] — runs/$TS1 에 1+2차 통합 ===================="
