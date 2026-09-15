#!/usr/bin/env bash
# run-vlm-500r.sh — 방향만 Base 와 같게 맞추고 해상도는 원본 그대로인 500장을 VLM 에 먹인다.
#
# 왜 또 도나: 전처리본(950px) run 은 오히려 나빴다(cell −10.2%p · itemName −22%p · 실패 0.4→2.8%).
# 원인은 방향이 아니라 리사이즈다 - 950 은 Paddle det 이 dense 표 행을 병합하지 않는 한계값이라
# 글자를 희생해 잡은 값이고(1400 에서 dense 표 77→12%), det 을 쓰지 않는 VLM 에는 손해만 남는다.
# 이 run 이 실제 제품 구성("방향 보정 + VLM")에 해당하고, 세 입력 중 유일하게 공정한 비교다.
#
#   bash ~/OCR/ocr-server/eval/LLM/aws/run-vlm-500r.sh qwen
#
# 전제: run-vlm-serve.sh 로 같은 키의 서버가 떠 있어야 한다.
#       eval/runs/072_20260802_182127/processed/ 와 원본(images_replay)이 있어야 한다.
set -euo pipefail
KEY="${1:?모델 키(qwen|minicpm|internvl)}"
source ~/OCR/vlm-env.sh

REPO="$HOME/OCR/ocr-server"
BASE_RUN="eval/runs/072_20260802_182127"
LIST="$REPO/eval/LLM/inputs/sample_500r.txt"
ROT="$REPO/$BASE_RUN/rotated"
RUN="vlm_${KEY}_500r"
LOG="$HOME/OCR/logs/${RUN}_$(date +%Y%m%d_%H%M%S).log"
mkdir -p "$HOME/OCR/logs"
cd "$REPO"

# ── 전제 가드 ───────────────────────────────────────────────────────────────
WANT="${VLM_MODELS[$KEY]:?모르는 키: $KEY}"
SERVED="$(curl -sf http://127.0.0.1:8000/v1/models | python3 -c 'import sys,json;print(json.load(sys.stdin)["data"][0]["id"])' 2>/dev/null || true)"
if [[ "$SERVED" != "$WANT" ]]; then
  echo "서버가 $WANT 가 아니다 (지금: ${SERVED:-없음}). run-vlm-serve.sh $KEY 먼저." >&2
  exit 1
fi
[[ -d "$REPO/$BASE_RUN/processed" ]] || { echo "072 processed 가 없다: $REPO/$BASE_RUN/processed" >&2; exit 1; }
grep -q '"/runs/" in norm' eval/llm_runner.py || {
  echo "llm_runner.py 가 옛 버전이다(회전본 파일명 .jpg.jpg 를 못 떼 채점이 전부 빗나간다). git pull 먼저." >&2; exit 1; }
if [[ -d "$REPO/eval/runs/$RUN" ]]; then
  echo "이미 있다: eval/runs/$RUN - 지우거나 이름을 바꾸고 다시." >&2
  exit 1
fi

# ── 회전본 생성 (GPU 안 씀 · 이미 있으면 건너뜀) ─────────────────────────────
HAVE="$(ls "$ROT" 2>/dev/null | wc -l)"
if [[ "$HAVE" -lt 500 ]]; then
  # 시스템 python3 엔 PIL 도 pip 도 없다(DLAMI). VLM venv(vllm 이 pillow 를 끌고 옴) → Paddle venv 순으로 고른다.
  PYIMG=""
  for c in "${VLM_VENV:-}/bin/python" "$REPO/.venv/bin/python" python3; do
    if command -v "$c" >/dev/null 2>&1 && "$c" -c "import PIL" 2>/dev/null; then PYIMG="$c"; break; fi
  done
  [[ -n "$PYIMG" ]] || { echo "PIL 있는 python 이 없다 - 회전본을 못 만든다" >&2; exit 1; }
  echo "== 회전본 생성 (현재 $HAVE 장 · $PYIMG) - 각도는 처리본과 픽셀 상관으로 정한다"
  "$PYIMG" eval/llm_make_rotated.py \
    --sources eval/LLM/data/sample_500_sources.txt \
    --groups eval/LLM/data/groups_072.json \
    --processed "$BASE_RUN/processed" \
    --out "$BASE_RUN/rotated" \
    --list eval/LLM/inputs/sample_500r.txt 2>&1 | tee "$LOG"
else
  echo "== 회전본 $HAVE 장 이미 있음 - 건너뜀"
fi
[[ -f "$LIST" ]] || { echo "목록이 없다: $LIST" >&2; exit 1; }

# ── 실행 (지난 500장 run 들과 같은 설정: full_text 제외 · max_tokens · timeout · concurrency) ──
echo "== $RUN · $WANT · 500장 방향보정본(원본 해상도) · 로그 $LOG"
python3 eval/llm_runner.py \
  --model "$WANT" \
  --list "$LIST" \
  --run "$RUN" \
  --no-fulltext \
  --max-tokens "$VLM_MAX_TOKENS" \
  --timeout 2400 \
  --concurrency 8 \
  2>&1 | tee -a "$LOG" || true

# ── 채점 ───────────────────────────────────────────────────────────────────
echo "== 채점 (Base 072 와 같은 저울)"
python3 eval/compare_run.py --ts "$RUN" --testset invoice_replay --skip-missing 2>&1 | tail -5 | tee -a "$LOG" || true
python3 eval/compare_cross.py \
  --base "$BASE_RUN/compare" \
  --model "eval/runs/$RUN/compare" \
  --out "eval/LLM/data/cases_${KEY}_500r.json" --all 2>&1 | tail -20 | tee -a "$LOG" || true

echo
echo "== 끝. 로컬에서 회수할 것:"
echo "   eval/runs/$RUN/{run_meta.json,errors.jsonl,compare,samples,failed_raw}"
echo "   eval/LLM/data/cases_${KEY}_500r.json"
echo "   그리고 python eval/llm_ledger.py --add-run $RUN --label \"...\" 로 장부에 한 줄."
