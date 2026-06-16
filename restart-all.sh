#!/bin/bash
# 둘 다 재기동
tmux kill-session -t backend 2>/dev/null
tmux kill-session -t frontend 2>/dev/null
sleep 1

tmux new-session -d -s backend "~/OCR/start-backend.sh"
tmux new-session -d -s frontend "~/OCR/start-frontend.sh"

echo "[$(date +'%F %T')] Backend + Frontend restarted"
echo "---"
tmux ls
