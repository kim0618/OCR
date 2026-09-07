#!/bin/bash
# run-vlm-serve — vLLM OpenAI 호환 서버를 tmux 세션 vllm 으로 띄운다.
#
#   bash ~/OCR/run-vlm-serve.sh            # qwen
#   bash ~/OCR/run-vlm-serve.sh minicpm
#
# 로그 = ~/OCR/logs/vllm.log. 붙어서 보려면 tmux attach -t vllm.
# 내리기 = tmux kill-session -t vllm
#
# ⚠️ 해상도는 지정하지 않는다 - 모델 preprocessor_config.json 기본값을 쓴다.
#    건드리는 유일한 사유는 OOM·처리량 붕괴이고, 그때만 최소로 내리고
#    값과 이유를 계획서 지출 원장 옆에 적는다(정확도 튜닝이 아니라 하드웨어 제약).
set -eo pipefail
source ~/OCR/vlm-env.sh
mkdir -p ~/OCR/logs

KEY="${1:-qwen}"
REPO=$(vlm_repo "$KEY")

vlm_require_g6
vlm_require_nvme
vlm_stop_backend

[[ -x "$VLM_VENV/bin/vllm" ]] || { echo "✗ vLLM 미설치. bash ~/OCR/run-vlm-setup.sh $KEY 먼저." >&2; exit 1; }

tmux kill-session -t vllm 2>/dev/null || true
vlm_say "$KEY  ($REPO)  포트 $VLM_PORT"
tmux new-session -d -s vllm \
  "export HF_HOME='$HF_HOME'; '$VLM_VENV/bin/vllm' serve '$REPO' \
     --port $VLM_PORT --max-model-len 16384 2>&1 | tee -a ~/OCR/logs/vllm.log"

echo "기동 대기 중 (모델 로딩에 수 분)..."
for i in $(seq 1 120); do
  if curl -sf "http://localhost:$VLM_PORT/v1/models" >/dev/null 2>&1; then
    vlm_say "준비됨"
    curl -s "http://localhost:$VLM_PORT/v1/models"
    echo
    nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader
    echo
    echo "다음: bash ~/OCR/run-vlm-smoke.sh $KEY"
    exit 0
  fi
  sleep 5
done
echo "✗ 120회(약 10분) 동안 안 떴다. tail -50 ~/OCR/logs/vllm.log 확인." >&2
exit 1
