#!/usr/bin/env bash
# run-vlm-paddlevl-setup.sh — PaddleOCR-VL 을 세운다(venv 2개 + 서버).
#
#   bash ~/OCR/run-vlm-paddlevl-setup.sh
#
# 왜 venv 가 또 필요한가 - 이 인스턴스에 이미 둘이 있다:
#   ~/OCR/ocr-server/.venv   Paddle 백엔드(transformers 4.46 고정). 건드리면 OCR 서버가 깨진다.
#   $NVME/vllm/venv          vLLM. paddlepaddle-gpu 를 같이 넣으면 CUDA 스택이 충돌한다.
# 그래서 paddleocr[doc-parser] 용으로 $NVME/paddlevl/venv 를 따로 만든다.
# 이 venv 는 레이아웃 모델(PP-DocLayoutV2)만 돌리고, 0.9B VLM 은 vLLM 서버가 맡는다.
#
# ⚠️ nvme 는 stop/start 로 비워진다. 재기동하면 이 스크립트를 다시 돌려야 한다(~25분).
set -eo pipefail
source ~/OCR/vlm-env.sh

MODEL="PaddlePaddle/PaddleOCR-VL"
PVL_ROOT="$NVME/paddlevl"
PVL_VENV="$PVL_ROOT/venv"
LOG="$HOME/OCR/logs/paddlevl_setup_$(date +%Y%m%d_%H%M%S).log"
mkdir -p "$HOME/OCR/logs"
exec > >(tee -a "$LOG") 2>&1

vlm_say "전제 확인"
vlm_require_g6
vlm_require_nvme
vlm_stop_backend

# ── 1/4  vLLM venv (없으면 만든다 - 다른 후보와 공용) ────────────────────────
vlm_say "1/4  vLLM venv"
mkdir -p "$VLM_ROOT" "$HF_HOME"
[[ -x "$VLM_VENV/bin/python" ]] || python3.12 -m venv "$VLM_VENV"
"$VLM_VENV/bin/pip" install -q --upgrade pip
"$VLM_VENV/bin/pip" install -q vllm huggingface_hub
"$VLM_VENV/bin/python" -c "import vllm,torch;print('vllm',vllm.__version__,'/ torch',torch.__version__)"

# ── 2/4  가중치 ────────────────────────────────────────────────────────────
vlm_say "2/4  가중치  ($MODEL · 약 2GB)"
HF_REPO="$MODEL" "$VLM_VENV/bin/python" - <<'PYEOF'
import os
from huggingface_hub import snapshot_download
print("saved:", snapshot_download(os.environ["HF_REPO"], max_workers=8))
PYEOF

# ── 3/4  paddleocr venv (레이아웃 모델용) ───────────────────────────────────
# PP-DocLayoutV2 가중치는 첫 실행 때 자동으로 받는다.
vlm_say "3/4  paddleocr venv  ($PVL_VENV)"
mkdir -p "$PVL_ROOT"
[[ -x "$PVL_VENV/bin/python" ]] || python3.12 -m venv "$PVL_VENV"
"$PVL_VENV/bin/pip" install -q --upgrade pip
"$PVL_VENV/bin/pip" install -q paddlepaddle-gpu==3.2.1 \
  --extra-index-url https://www.paddlepaddle.org.cn/packages/stable/cu126/
"$PVL_VENV/bin/pip" install -q -U "paddleocr[doc-parser]" safetensors
"$PVL_VENV/bin/python" -c "import paddleocr;print('paddleocr', paddleocr.__version__)"

# ── 4/4  서버 ──────────────────────────────────────────────────────────────
# OCR 용 권장 설정: prefix 캐시·이미지 재사용 끄기(장마다 다른 그림이라 해싱만 손해).
vlm_say "4/4  serve  ·  tmux 세션 vllm"
tmux kill-session -t vllm 2>/dev/null || true
tmux new-session -d -s vllm \
  "export HF_HOME='$HF_HOME' VLLM_CACHE_ROOT='$VLLM_CACHE_ROOT' XDG_CACHE_HOME='$XDG_CACHE_HOME' TRITON_CACHE_DIR='$TRITON_CACHE_DIR' VLLM_USE_FLASHINFER_SAMPLER='$VLLM_USE_FLASHINFER_SAMPLER'; \
   '$VLM_VENV/bin/vllm' serve '$MODEL' --port $VLM_PORT \
     --trust-remote-code --served-model-name PaddleOCR-VL-0.9B \
     --max-num-batched-tokens 16384 --no-enable-prefix-caching --mm-processor-cache-gb 0 \
     2>&1 | tee -a ~/OCR/logs/vllm.log"

echo "기동 대기 중..."
for i in $(seq 1 120); do
  if curl -sf "http://localhost:$VLM_PORT/v1/models" >/dev/null 2>&1; then
    vlm_say "준비됨"
    curl -s "http://localhost:$VLM_PORT/v1/models"; echo
    nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader
    echo
    echo "다음: bash ~/OCR/run-vlm-paddlevl.sh smoke"
    exit 0
  fi
  sleep 5
done
echo "✗ 10분 동안 안 떴다. 원인 줄:" >&2
grep -E "ValueError|RuntimeError|OutOfMemory|ERROR.*failed" ~/OCR/logs/vllm.log | tail -5 >&2
exit 1
