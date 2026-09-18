#!/usr/bin/env bash
# run-vlm-bringup.sh — 후보 모델 하나를 스모크 통과까지 한 번에 세운다.
#
#   ~/OCR/run-vlm-bringup.sh minicpm
#
# 하는 일 = 전제 가드 → setup(venv·가중치) → serve(tmux vllm) → 스모크 50장 B.
# 전부 tee 로 ~/OCR/logs/vlm_<key>_bringup_<ts>.log 에 남고, 화면에도 그대로 흐른다.
# tmux 밖에서 부르면 스스로 tmux 세션(bringup_<key>)으로 들어간다 - SSH 가 끊겨도 안 죽는다.
#
# 왜 한 덩어리인가: setup 20분 + serve 5분 + 스모크 20분이라 사람이 붙어 있을 수 없고,
# 중간에 SSH 가 끊기면 어디까지 갔는지 알 길이 없다. 로그 한 장이 그 답이다.
#
# 전제: 인스턴스가 g6(L4) 이고 nvme 가 붙어 있어야 한다(둘 다 아래에서 막는다).
set -eo pipefail

KEY="${1:?모델 키(qwen|minicpm|internvl)}"

# ── tmux 자기 격리 ──────────────────────────────────────────────────────────
# ⚠️ 세션 이름을 vllm 으로 두면 안 된다 - run-vlm-serve.sh 가 그 이름을 먼저 kill 한다.
if [[ -z "${TMUX:-}" && "${VLM_NO_TMUX:-}" != "1" ]]; then
  SELF="$(cd "$(dirname "$0")" && pwd)/$(basename "$0")"
  SESSION="bringup_$KEY"
  tmux kill-session -t "$SESSION" 2>/dev/null || true
  echo "== tmux 세션 $SESSION 으로 들어간다 (빠져나오기 Ctrl-b d · 돌아오기 tmux attach -t $SESSION)"
  exec tmux new-session -s "$SESSION" \
    "VLM_NO_TMUX=1 '$SELF' '$KEY'; echo; echo '[끝났다. Ctrl-b d 로 나가거나 exit]'; exec bash"
fi

source ~/OCR/vlm-env.sh
REPO="$(vlm_repo "$KEY")"
TS="$(date +%Y%m%d_%H%M%S)"
LOG="$HOME/OCR/logs/vlm_${KEY}_bringup_${TS}.log"
mkdir -p "$HOME/OCR/logs"
exec > >(tee -a "$LOG") 2>&1            # 이후 모든 출력이 로그에도 남는다

START=$SECONDS
vlm_say "$KEY  ($REPO)  ·  로그 $LOG"

# ── 전제 가드 (20분 태우고 나서 걸리면 안 되는 것들을 먼저 본다) ──────────────
vlm_require_g6
vlm_require_nvme
grep -q 'trust-remote-code' ~/OCR/run-vlm-serve.sh || {
  echo "✗ run-vlm-serve.sh 가 옛 버전이다 (--trust-remote-code 없음)." >&2
  echo "  MiniCPM-V·InternVL 은 커스텀 코드 모델이라 그것 없이는 로딩에서 죽는다." >&2
  echo "  eval/LLM/aws/run-vlm-serve.sh 를 ~/OCR/ 로 다시 올릴 것." >&2
  exit 1; }
grep -q 'MODE=' ~/OCR/run-vlm-smoke.sh || {
  echo "✗ run-vlm-smoke.sh 가 옛 버전이다 (B 전용 모드 없음 - A 런에 40분·\$0.66 을 버린다)." >&2
  echo "  eval/LLM/aws/run-vlm-smoke.sh 를 ~/OCR/ 로 다시 올릴 것." >&2
  exit 1; }
[[ -f "$HOME/OCR/ocr-server/eval/LLM/inputs/smoke_50.txt" ]] || {
  echo "✗ 스모크 목록이 없다 - git pull 먼저." >&2; exit 1; }

# ── 1/3 setup ──────────────────────────────────────────────────────────────
# ⚠️ 인스턴스 스토어는 stop/start 로 비워진다. 재기동이면 venv·가중치를 다시 받는다(~20분).
vlm_say "1/3  setup  ·  vLLM venv + 가중치 (재기동 뒤라면 ~20분)"
~/OCR/run-vlm-setup.sh "$KEY"

# ── 2/3 serve ──────────────────────────────────────────────────────────────
vlm_say "2/3  serve  ·  tmux 세션 vllm  (로그 ~/OCR/logs/vllm.log)"
~/OCR/run-vlm-serve.sh "$KEY"

# ── 3/3 스모크 ─────────────────────────────────────────────────────────────
# full_text 제외는 2026-09-07 확정 - A 런은 돌리지 않는다.
vlm_say "3/3  스모크 50장  ·  full_text 제외 (B)"
~/OCR/run-vlm-smoke.sh "$KEY" b

# ── 마무리 ─────────────────────────────────────────────────────────────────
MIN=$(( (SECONDS - START) / 60 ))
vlm_say "끝  ·  $MIN 분  ·  로그 $LOG"
cat <<EOF

줄 세울 기준선 (Qwen3-VL 4B · 같은 50장 · full_text 제외)
  50/50 성공 · 176.1장/h · 잘림 0

통과했으면 500장 (리사이즈 제거본 - 500장 run 은 이것 하나로만 돈다)
  ~/OCR/ocr-server/eval/LLM/aws/run-vlm-500r.sh $KEY

인스턴스를 끌 때 지출 원장에 세션 한 줄을 남길 것 (켠 시각·끈 시각 둘 다 필요)
  python eval/llm_ledger.py --add-session "..." --hours H --rate g6 --write
EOF
