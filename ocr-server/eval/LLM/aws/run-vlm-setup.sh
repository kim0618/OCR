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
# huggingface_hub 1.x 는 hf_transfer 를 extra 로 제공하지 않는다(전송은 xet 이 맡는다).
# extra 를 붙이면 설치는 조용히 건너뛰는데 HF_HUB_ENABLE_HF_TRANSFER=1 만 남아
# 다운로드가 "enabled but not available" 로 죽는다. 그래서 둘 다 안 쓴다.
"$VLM_VENV/bin/pip" install -q vllm huggingface_hub
"$VLM_VENV/bin/python" - <<'PY'
import vllm, torch, transformers
print(f"vllm {vllm.__version__} / torch {torch.__version__} / transformers {transformers.__version__}")
print("cuda:", torch.cuda.is_available(), torch.cuda.get_device_name(0) if torch.cuda.is_available() else "")
PY

if [[ "${1:-}" == "--env-only" ]]; then
  echo "환경만 요청됨 - 종료"
  exit 0
fi

WANT=("$@")
[[ ${#WANT[@]} -eq 0 ]] && WANT=(qwen)      # 스모크는 큐윈 하나면 된다
for key in "${WANT[@]}"; do
  repo=$(vlm_repo "$key")
  vlm_say "$key  <-  $repo"
  # CLI 이름이 버전마다 바뀐다(huggingface-cli -> hf). 파이썬 API 는 안 바뀐다.
  # 진행률을 가리지 않으려고 파이프로 자르지 않는다 - 18GB 짜리다.
  HF_REPO="$repo" "$VLM_VENV/bin/python" - <<'PYEOF'
import os
from huggingface_hub import snapshot_download
p = snapshot_download(os.environ["HF_REPO"], max_workers=8)
print("saved:", p)
PYEOF
  df -h "$NVME" | tail -1
done

vlm_say "완료"
du -sh "$HF_HOME" "$VLM_VENV" 2>/dev/null
df -h "$NVME" /
echo
echo "다음: bash ~/OCR/run-vlm-serve.sh ${WANT[0]}"
