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
# 캐시도 전부 nvme 로. EBS(/) 는 96% 라 여유가 없고, vLLM 은 torch.compile 산출물을
# 기본값이면 ~/.cache/vllm(EBS)에 수 GB 쌓는다 - 기동 중에 / 가 차면 통째로 깨진다.
export VLLM_CACHE_ROOT="$NVME/cache/vllm"
export XDG_CACHE_HOME="$NVME/cache"
export TRITON_CACHE_DIR="$NVME/cache/triton"
mkdir -p "$VLLM_CACHE_ROOT" "$XDG_CACHE_HOME" "$TRITON_CACHE_DIR" 2>/dev/null || true
VLM_PORT=8000
# ★L4 24GB 제약으로 확정한 값(2026-09-07 실측). 정확도 튜닝이 아니라 하드웨어 제약이다.
#   기본값(util 0.9 · len 16384)은 기동 실패한다:
#     "Model loading took 16.65 GiB / Available KV cache 1.1 GiB /
#      max seq len 16384 needs 2.25 GiB ... estimated maximum model length is 8000"
#   가중치가 23GB 중 16.65GB 를 먹어 KV 가 안 남는다.
#   util 을 0.95 로 올려 KV 를 ~2.2GB 확보하고, 길이는 우리 문서에 맞춰 12288 로 잡았다.
#   내역 = 이미지 약 4.9K 토큰(1655x2340) + 프롬프트 약 1.5K + 출력 6K.
#   ⚠️ 해상도(max_pixels)는 건드리지 않는다 - 작은 글씨 인식이 바로 이 실험의 측정 대상이라
#      줄이면 교란 요인이 된다. 세 모델에 같은 값을 쓰고 지출 원장 옆에 기록한다.
VLM_MAX_LEN="${VLM_MAX_LEN:-12288}"
VLM_GPU_UTIL="${VLM_GPU_UTIL:-0.95}"
VLM_MAX_TOKENS="${VLM_MAX_TOKENS:-6144}"

# ★FlashInfer 샘플러 끄기(2026-09-07 실측). DLAMI 에 CUDA 툴킷이 없어 nvcc 가 없는데
#   flashinfer/sampling.py 의 get_sampling_module 이 JIT 로 커널을 빌드하려다 죽는다:
#     "RuntimeError: Could not find nvcc and default cuda_home='/usr/local/cuda' doesn't exist"
#   (알려진 이슈 vllm#26642). nvcc 를 wheel 로 넣을 수도 없다 - torch 가 cu130 인데
#   nvidia-cuda-nvcc-cu13 은 0.0.1 스텁뿐이고 실물은 cu12 까지만 있다.
#   우리는 temperature=0(greedy) 이라 샘플러 구현이 결과·속도에 사실상 영향이 없다.
export VLLM_USE_FLASHINFER_SAMPLER=0
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
