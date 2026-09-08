#!/usr/bin/env bash
# run-vlm-500p.sh — 후보 모델에 Base 전처리본(072 processed, 950px)을 먹여 500장을 돌린다.
#
# 왜 따로 도나: 지금까지의 500장 run 은 VLM 에 원본을 그대로 줬다(전처리 없음). 그러면 113장에서
# 두 쪽이 다른 그림을 보게 되어 파서 비교가 385장으로 줄고, 실제 제품 구성(방향 보정 + VLM)과도 다르다.
# 이 run 은 Paddle 과 **완전히 같은 그림**을 주어 인식+파서만 남긴다. 결과 폴더는 vlm_<키>_500p.
#
#   bash ~/OCR/run-vlm-500p.sh qwen
#
# 전제: run-vlm-serve.sh 로 같은 키의 서버가 떠 있어야 한다.
#       eval/runs/072_20260802_182127/processed/ 가 있어야 한다(072 는 이 인스턴스에서 돌았다).
set -euo pipefail
KEY="${1:?모델 키(qwen|minicpm|internvl)}"
source ~/OCR/vlm-env.sh

REPO="$HOME/OCR/ocr-server"
LIST="$REPO/eval/LLM/inputs/sample_500p.txt"
RUN="vlm_${KEY}_500p"
LOG="$HOME/OCR/logs/${RUN}_$(date +%Y%m%d_%H%M%S).log"
mkdir -p "$HOME/OCR/logs"

# ── 전제 가드 ───────────────────────────────────────────────────────────────
WANT="${VLM_MODELS[$KEY]:?모르는 키: $KEY}"
SERVED="$(curl -sf http://127.0.0.1:8000/v1/models | python3 -c 'import sys,json;print(json.load(sys.stdin)["data"][0]["id"])' 2>/dev/null || true)"
if [[ "$SERVED" != "$WANT" ]]; then
  echo "서버가 $WANT 가 아니다 (지금: ${SERVED:-없음}). run-vlm-serve.sh $KEY 먼저." >&2
  exit 1
fi
[[ -f "$LIST" ]] || { echo "목록이 없다: $LIST (git pull 했나)" >&2; exit 1; }
FIRST="$REPO/eval/$(head -1 "$LIST")"
[[ -f "$FIRST" ]] || {
  echo "전처리본이 없다: $FIRST" >&2
  echo "072 processed 폴더가 이 인스턴스에 없으면 로컬에서 올린다:" >&2
  echo "  scp -r <로컬>/eval/runs/072_20260802_182127/processed ubuntu@<host>:$REPO/eval/runs/072_20260802_182127/" >&2
  exit 1
}
MISSING="$(cd "$REPO/eval" && while read -r p; do [[ -f "$p" ]] || echo "$p"; done < "$LIST" | wc -l)"
[[ "$MISSING" == "0" ]] || { echo "전처리본 $MISSING 장이 없다. 폴더가 온전한지 확인." >&2; exit 1; }
if [[ -d "$REPO/eval/runs/$RUN" ]]; then
  echo "이미 있다: eval/runs/$RUN - 지우거나 이름을 바꾸고 다시." >&2
  exit 1
fi

# ── 실행 (지난 500장 run 과 같은 설정: full_text 제외 · max_tokens · timeout · concurrency. 다른 것은 입력 그림뿐) ───────────────────────────────────────────────────────────────────
echo "== $RUN · $WANT · 500장 전처리본(950px) · 로그 $LOG"
cd "$REPO"
python3 eval/llm_runner.py \
  --model "$WANT" \
  --list "$LIST" \
  --run "$RUN" \
  --no-fulltext \
  --max-tokens "$VLM_MAX_TOKENS" \
  --timeout 2400 \
  --concurrency 8 \
  2>&1 | tee "$LOG" || true

# ── 채점 ───────────────────────────────────────────────────────────────────
echo "== 채점 (Base 072 와 같은 저울)"
python3 eval/compare_run.py --ts "$RUN" --testset invoice_replay --skip-missing 2>&1 | tail -5 | tee -a "$LOG" || true
python3 eval/compare_cross.py \
  --base eval/runs/072_20260802_182127/compare \
  --model "eval/runs/$RUN/compare" \
  --out "eval/LLM/data/cases_${KEY}_500p.json" --all 2>&1 | tail -20 | tee -a "$LOG" || true

echo
echo "== 끝. 로컬에서 회수할 것:"
echo "   eval/runs/$RUN/{run_meta.json,errors.jsonl,compare,samples}   (model_view 는 원본과 같으니 필요 없음)"
echo "   eval/LLM/data/cases_${KEY}_500p.json"
echo "   그리고 python eval/llm_ledger.py 에 run 한 줄 추가."
