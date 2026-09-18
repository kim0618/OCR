#!/usr/bin/env bash
# run-vlm-paddlevl.sh — PaddleOCR-VL 로 문서를 파싱해 원본 결과만 떨궈 놓는다.
#
#   ~/OCR/run-vlm-paddlevl.sh smoke      # 스모크 50장 (게이트)
#   ~/OCR/run-vlm-paddlevl.sh 500r       # 500장 리사이즈 제거본 (본 비교)
#
# 다른 후보와 무엇이 다른가
#   Qwen·InternVL 은 "이미지 + 우리 스키마" → JSON 한 방이라 run-vlm-bringup.sh 로 끝난다.
#   PaddleOCR-VL 은 지시를 따르는 모델이 아니다. 문서를 구조로 재현할 뿐이라
#   ① 레이아웃 모델이 영역을 자르고 ② 0.9B VLM 이 조각을 읽는 2단이고,
#   ①을 paddleocr 패키지가 돌린다 → vLLM venv 와 별개인 **세 번째 venv** 가 필요하다.
#   그래서 채점 가능한 JSON 을 여기서 만들지 않는다. 로컬 eval/paddlevl_adapt.py 가
#   우리 파서에 태워서 만든다(인식 층만 교체하는 실험이므로 파서는 우리 것을 그대로 쓴다).
#
# 전제: run-vlm-paddlevl-setup.sh 를 한 번 돌려 venv·서버가 서 있어야 한다.
set -eo pipefail

WHAT="${1:?smoke | 500r}"
source ~/OCR/vlm-env.sh

REPO="$HOME/OCR/ocr-server"
PVL_VENV="$NVME/paddlevl/venv"
MODEL="PaddlePaddle/PaddleOCR-VL"

case "$WHAT" in
  smoke) LIST="eval/LLM/inputs/smoke_50.txt";  RUN="vlm_paddlevl_smoke" ;;
  500r)  LIST="eval/LLM/inputs/sample_500r.txt"; RUN="vlm_paddlevl_500r" ;;
  *) echo "smoke 아니면 500r" >&2; exit 1 ;;
esac

LOG="$HOME/OCR/logs/${RUN}_$(date +%Y%m%d_%H%M%S).log"
mkdir -p "$HOME/OCR/logs"
cd "$REPO"
exec > >(tee -a "$LOG") 2>&1

vlm_say "$RUN  ·  $MODEL  ·  로그 $LOG"

# ── 전제 가드 ───────────────────────────────────────────────────────────────
vlm_require_g6
vlm_require_nvme
[[ -x "$PVL_VENV/bin/python" ]] || {
  echo "✗ paddleocr venv 가 없다 - bash ~/OCR/run-vlm-paddlevl-setup.sh 먼저." >&2; exit 1; }
SERVED="$(curl -sf http://127.0.0.1:8000/v1/models | python3 -c 'import sys,json;print(json.load(sys.stdin)["data"][0]["id"])' 2>/dev/null || true)"
[[ "$SERVED" == *PaddleOCR-VL* ]] || {
  echo "✗ 서버가 PaddleOCR-VL 이 아니다 (지금: ${SERVED:-없음})." >&2
  echo "  bash ~/OCR/run-vlm-paddlevl-setup.sh 가 서버까지 띄운다." >&2; exit 1; }
[[ -f "$LIST" ]] || { echo "✗ 목록이 없다: $LIST - git pull 먼저." >&2; exit 1; }
if [[ "$WHAT" == "500r" ]]; then
  HAVE="$(ls "$REPO/eval/runs/072_20260802_182127/rotated" 2>/dev/null | wc -l)"
  [[ "$HAVE" -ge 500 ]] || {
    echo "✗ 회전본이 $HAVE 장뿐이다 - run-vlm-500r.sh 가 만드는 그 파일이 있어야 한다." >&2; exit 1; }
fi

# ── 실행 ───────────────────────────────────────────────────────────────────
# 이어서 돌기: parse/<src>.json 이 이미 있으면 건너뛴다(끊겨도 처음부터 안 간다).
"$PVL_VENV/bin/python" eval/paddlevl_runner.py --list "$LIST" --run "$RUN" || true

N="$(ls "eval/runs/$RUN/parse" 2>/dev/null | wc -l)"
vlm_say "끝  ·  파싱 결과 $N 장  ·  eval/runs/$RUN/parse/"
cat <<EOF

로컬에서 이어서 (AWS 불필요)
  scp -r ubuntu@<ip>:'~/OCR/ocr-server/eval/runs/$RUN' eval/runs/
  python eval/paddlevl_adapt.py --parse eval/runs/$RUN/parse --run $RUN --elapsed-sec <초>
  python eval/llm_derive_run.py --src $RUN --dst ${RUN}_post --lot-merge
  python eval/compare_run.py --ts ${RUN}_post --testset invoice_replay --skip-missing

⚠️ --base-chain 은 쓰지 않는다. Qwen 계열은 파서를 건너뛰어 후처리 체인을 따로 입혀야 했지만,
   이 경로는 우리 파서(replay_dispatch)가 합류점까지 재현하므로 이미 거친 상태다.
EOF
