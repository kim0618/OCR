#!/bin/bash
# run-rekey.sh — 리키잉 대량 eval (invoice_rekey testset). run-eval.sh 의 rekey 전용판.
# ★ run-eval.sh(--all)와 달리 rekey testset만 돌림 (6월 study/thin 재실행 안 함).
# tmux:  tmux new -s eval_rekey
#        bash ~/OCR/run-rekey.sh          (나오기: Ctrl+B 떼고 D / 재접속: tmux attach -t eval_rekey)
export PYTHONUNBUFFERED=1
cd ~/OCR/ocr-server
stdbuf -oL -eL python -u eval/run_all.py --testset invoice_rekey 2>&1 | tee -a ~/OCR/logs/eval_rekey.log
