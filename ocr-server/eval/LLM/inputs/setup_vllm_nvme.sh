#!/usr/bin/env bash
# setup_vllm_nvme — vLLM 환경과 후보 모델 3개를 인스턴스 스토어에 올린다.
#
# 왜 nvme 인가: EBS(/) 는 99G 중 7.7G 밖에 안 남아 63GB 가 안 들어간다. 반면
# /opt/dlami/nvme 는 인스턴스 요금에 이미 포함된 물리 SSD 인데 109G 가 비어 있다.
# 모델 가중치는 HuggingFace 에서 언제든 다시 받는 공개 파일이라 - 우리가 GPU 시간을
# 들여 만든 finetune_corpus·versions 와 달리 - 날아가도 잃는 게 없다. 재생성 가능한
# 것을 ephemeral 에 두는 게 맞는 배치다.
#
# ⚠️ 인스턴스 스토어는 stop/start 시 전부 지워진다(재부팅은 무사).
#    → g6 전환을 먼저 끝내고 이 스크립트를 돌릴 것. 순서를 바꾸면 받자마자 날아간다.
# ⚠️ Paddle venv(~/OCR/ocr-server/.venv) 는 건드리지 않는다. transformers 4.46.1 이라
#    세 모델 다 못 읽는데, 거기서 올리면 OCR 백엔드가 깨진다. 그래서 별도 venv.
# ⚠️ RAM 15G 라 VLM 과 Paddle 백엔드 동시 기동은 행업이다(069·070 실측).
#    이 스크립트는 다운로드만 하고 서버는 안 띄운다.
#
# 사용:
#   bash eval/LLM/setup_vllm_nvme.sh              # 전체(환경 + 모델 3개)
#   bash eval/LLM/setup_vllm_nvme.sh qwen         # 모델 하나만
#   bash eval/LLM/setup_vllm_nvme.sh --env-only   # 환경만
set -euo pipefail

NVME=/opt/dlami/nvme
ROOT="$NVME/vllm"
VENV="$ROOT/venv"
export HF_HOME="$NVME/hf"

# 모델 저장소 이름 - ⚠️ 돌리기 전에 실물 확인할 것(HF 페이지에서 정확한 repo id).
# 계획서 근거: Qwen=한국어 축, MiniCPM=처리량 축(비전토큰 4× 적음), InternVL=검증용 2위.
declare -A MODELS=(
  [qwen]="Qwen/Qwen3-VL-8B-Instruct"
  [minicpm]="openbmb/MiniCPM-V-4_5"
  [internvl]="OpenGVLab/InternVL3_5-8B"
)

say() { printf '\n\033[1m== %s\033[0m\n' "$*"; }

# ── 0. 전제 확인 ──────────────────────────────────────────────────────────
say "전제 확인"
if ! mountpoint -q "$NVME"; then
  echo "✗ $NVME 가 마운트되어 있지 않다. 인스턴스 타입을 바꾸면 안 붙는 경우가 있다."
  echo "  lsblk 로 ephemeral 디스크를 찾아 마운트한 뒤 다시 돌릴 것:"
  echo "    lsblk"
  echo "    sudo mkfs.ext4 /dev/nvme1n1        # 데이터 없는 새 인스턴스 스토어일 때만"
  echo "    sudo mkdir -p $NVME && sudo mount /dev/nvme1n1 $NVME"
  echo "    sudo chown ubuntu:ubuntu $NVME"
  exit 1
fi
touch "$NVME/.wtest" 2>/dev/null || { echo "✗ $NVME 쓰기 불가"; exit 1; }
rm -f "$NVME/.wtest"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
if nvidia-smi --query-gpu=name --format=csv,noheader | grep -q T4; then
  echo "✗ GPU 가 아직 T4(g4dn) 다. 8B bf16 이 안 올라가고 flash-attn2 도 없어 비교가 왜곡된다."
  echo "  g6.xlarge(L4 24GB) 로 전환한 뒤 다시 돌릴 것."
  exit 1
fi
df -h "$NVME" /

if [[ "${1:-}" == "--env-only" ]]; then ONLY_ENV=1; else ONLY_ENV=0; fi

# ── 1. vLLM 전용 venv ─────────────────────────────────────────────────────
say "vLLM venv  ($VENV)"
mkdir -p "$ROOT" "$HF_HOME"
if [[ ! -x "$VENV/bin/python" ]]; then
  python3.12 -m venv "$VENV"
fi
"$VENV/bin/pip" install -q --upgrade pip
# vllm 이 자기 torch 를 끌고 온다. Paddle venv 의 torch 2.11 과 무관하게 격리된다.
# transformers 는 세 모델 다 최신을 요구하므로 vllm 이 정하는 최신 버전에 맡긴다.
"$VENV/bin/pip" install -q vllm huggingface_hub[hf_transfer]
"$VENV/bin/python" - <<'PY'
import vllm, torch, transformers
print(f"vllm {vllm.__version__} / torch {torch.__version__} / transformers {transformers.__version__}")
print("cuda:", torch.cuda.is_available(), torch.cuda.get_device_name(0) if torch.cuda.is_available() else "")
PY
[[ $ONLY_ENV == 1 ]] && { echo "환경만 요청됨 - 종료"; exit 0; }

# ── 2. 모델 내려받기 ──────────────────────────────────────────────────────
export HF_HUB_ENABLE_HF_TRANSFER=1
WANT=("$@")
[[ ${#WANT[@]} -eq 0 ]] && WANT=(qwen minicpm internvl)
for key in "${WANT[@]}"; do
  repo="${MODELS[$key]:-}"
  [[ -z "$repo" ]] && { echo "모르는 모델 키: $key (qwen|minicpm|internvl)"; exit 1; }
  say "$key  ←  $repo"
  "$VENV/bin/huggingface-cli" download "$repo" --quiet
  df -h "$NVME" | tail -1
done

say "완료"
du -sh "$HF_HOME" "$VENV" 2>/dev/null
df -h "$NVME" /
cat <<EOF

다음 - 서버 기동(백엔드를 먼저 내릴 것: fuser -k 9099/tcp):
  export HF_HOME=$HF_HOME
  $VENV/bin/vllm serve ${MODELS[qwen]} --port 8000 --max-model-len 16384

해상도는 지정하지 않는다 - 모델 preprocessor_config.json 기본값을 쓴다.
건드리는 유일한 사유는 OOM·처리량 붕괴이고, 그때만 값과 이유를 지출 원장 옆에 적는다.
EOF
