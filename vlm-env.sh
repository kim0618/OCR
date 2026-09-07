#!/bin/bash
# vlm-env — VLM 실험 공통 설정. run-vlm-*.sh 가 source 한다.
#
# 왜 nvme 인가: EBS(/) 는 99G 중 7.7G 밖에 안 남아 63GB 가 안 들어간다. 반면
# /opt/dlami/nvme 는 인스턴스 요금에 이미 포함된 물리 SSD 인데 109G 가 비어 있다.
# 모델 가중치는 HuggingFace 에서 언제든 다시 받는 공개 파일이라 - 우리가 GPU 시간을
# 들여 만든 finetune_corpus·versions 와 달리 - 날아가도 잃는 게 없다.
#
# ⚠️ 인스턴스 스토어는 stop/start 시 전부 지워진다(재부팅은 무사).
#    g6 전환을 먼저 끝내고 받을 것. 순서를 바꾸면 받자마자 날아간다.
# ⚠️ Paddle venv(~/OCR/ocr-server/.venv) 는 건드리지 않는다. transformers 4.46.1 이라
#    세 모델 다 못 읽는데, 거기서 올리면 OCR 백엔드가 깨진다. 그래서 별도 venv.

NVME=/opt/dlami/nvme
VLM_ROOT="$NVME/vllm"
VLM_VENV="$VLM_ROOT/venv"
export HF_HOME="$NVME/hf"
VLM_PORT=8000
VLM_SERVER="http://localhost:$VLM_PORT/v1"

# 후보 모델 - ⚠️ 처음 받기 전에 HF 페이지에서 정확한 repo id 를 확인할 것.
# 선정 논리(계획서): Qwen=한국어 축 1등 · MiniCPM=처리량 축(비전토큰 4× 적음) · InternVL=검증용 2위.
declare -A VLM_MODELS=(
  [qwen]="Qwen/Qwen3-VL-8B-Instruct"
  [minicpm]="openbmb/MiniCPM-V-4_5"
  [internvl]="OpenGVLab/InternVL3_5-8B"
)

vlm_say() { printf '\n\033[1m== %s\033[0m\n' "$*"; }

vlm_repo() {   # vlm_repo qwen -> Qwen/Qwen3-VL-8B-Instruct
  local key="${1:-qwen}" repo="${VLM_MODELS[${1:-qwen}]:-}"
  if [[ -z "$repo" ]]; then
    echo "모르는 모델 키: $key (qwen|minicpm|internvl)" >&2
    return 1
  fi
  echo "$repo"
}

# GPU·디스크 전제. 틀린 하드웨어에서 돌면 비교가 왜곡되므로 그냥 멈춘다.
vlm_require_g6() {
  local gpu
  gpu=$(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader)
  echo "GPU: $gpu"
  if grep -qi 't4' <<<"$gpu"; then
    echo "✗ 아직 T4(g4dn) 다. 8B bf16 이 안 올라가고 flash-attn2 도 없어 비교가 왜곡된다." >&2
    echo "  콘솔에서 g6.xlarge(L4 24GB) 로 전환한 뒤 다시 돌릴 것." >&2
    return 1
  fi
}

vlm_require_nvme() {
  if ! mountpoint -q "$NVME"; then
    cat >&2 <<EOF
✗ $NVME 가 마운트되어 있지 않다. 인스턴스 타입을 바꾸면 안 붙는 경우가 있다.
  lsblk 로 ephemeral 디스크를 찾아 붙인 뒤 다시 돌릴 것:
    lsblk
    sudo mkfs.ext4 /dev/nvme1n1        # 데이터 없는 새 인스턴스 스토어일 때만
    sudo mkdir -p $NVME && sudo mount /dev/nvme1n1 $NVME
    sudo chown ubuntu:ubuntu $NVME
EOF
    return 1
  fi
  touch "$NVME/.wtest" 2>/dev/null || { echo "✗ $NVME 쓰기 불가" >&2; return 1; }
  rm -f "$NVME/.wtest"
  df -h "$NVME" /
}

# RAM 15GB 라 VLM 과 Paddle 백엔드 동시 기동은 스래싱으로 인스턴스가 통째로 행업한다(069·070 실측).
vlm_stop_backend() {
  if fuser 9099/tcp >/dev/null 2>&1; then
    vlm_say "백엔드 내림 (RAM 15GB - vLLM 과 동시 기동은 행업)"
    fuser -k 9099/tcp || true
    tmux kill-session -t backend 2>/dev/null || true
    sleep 3
  fi
}
