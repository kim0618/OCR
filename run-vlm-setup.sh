#!/bin/bash
# run-vlm-setup — vLLM 환경과 모델을 인스턴스 스토어(/opt/dlami/nvme)에 올린다.
#
#   bash ~/OCR/run-vlm-setup.sh              # 환경 + qwen (스모크용)
#   bash ~/OCR/run-vlm-setup.sh qwen minicpm internvl
#   bash ~/OCR/run-vlm-setup.sh --env-only
#
# 서버는 띄우지 않는다 - 기동은 run-vlm-serve.sh.
set -eo pipefail
source ~/OCR/vlm-env.sh
mkdir -p ~/OCR/logs

vlm_say "전제 확인"
vlm_require_g6
vlm_require_nvme
vlm_stop_backend

vlm_say "vLLM venv  ($VLM_VENV)"
mkdir -p "$VLM_ROOT" "$HF_HOME"
[[ -x "$VLM_VENV/bin/python" ]] || python3.12 -m venv "$VLM_VENV"
"$VLM_VENV/bin/pip" install -q --upgrade pip
# vllm 이 자기 torch 를 끌고 온다. Paddle venv 의 torch 2.11 과 격리된다.
# transformers 는 세 모델 다 최신을 요구하므로 vllm 이 정하는 버전에 맡긴다.
"$VLM_VENV/bin/pip" install -q vllm "huggingface_hub[hf_transfer]"
"$VLM_VENV/bin/python" - <<'PY'
import vllm, torch, transformers
print(f"vllm {vllm.__version__} / torch {torch.__version__} / transformers {transformers.__version__}")
print("cuda:", torch.cuda.is_available(), torch.cuda.get_device_name(0) if torch.cuda.is_available() else "")
PY

if [[ "${1:-}" == "--env-only" ]]; then
  echo "환경만 요청됨 - 종료"
  exit 0
fi

export HF_HUB_ENABLE_HF_TRANSFER=1
WANT=("$@")
[[ ${#WANT[@]} -eq 0 ]] && WANT=(qwen)      # 스모크는 큐윈 하나면 된다
for key in "${WANT[@]}"; do
  repo=$(vlm_repo "$key")
  vlm_say "$key  <-  $repo"
  "$VLM_VENV/bin/huggingface-cli" download "$repo" 2>&1 | tail -3
  df -h "$NVME" | tail -1
done

vlm_say "완료"
du -sh "$HF_HOME" "$VLM_VENV" 2>/dev/null
df -h "$NVME" /
echo
echo "다음: bash ~/OCR/run-vlm-serve.sh ${WANT[0]}"
