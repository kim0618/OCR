#!/bin/bash
# 기존 세션 있으면 그대로 두고, 없을 때만 새로 만들기
tmux has-session -t backend 2>/dev/null || tmux new-session -d -s backend "~/OCR/start-backend.sh"
tmux has-session -t frontend 2>/dev/null || tmux new-session -d -s frontend "~/OCR/start-frontend.sh"
echo "[$(date +'%F %T')] Sessions:"
tmux ls
