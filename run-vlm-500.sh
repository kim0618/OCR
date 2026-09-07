#!/bin/bash
# run-vlm-500 — 500장 스크리닝을 한 모델에 대해 돌린다.
#
#   bash ~/OCR/run-vlm-500.sh qwen
#   bash ~/OCR/run-vlm-500.sh minicpm
#
# ★full_text 는 요구하지 않는다(2026-09-07 결정). 스모크 A/B 실측에서 처리량이
#   2.4배 차이(72 vs 176장/h) 났고, full_text 가 필요한 건 파서 탭 26행 중
#   structure/recognition 두 행뿐이라 채택 판단(cell 정확도 1순위)에 영향이 없다.
#   그 두 행이 필요해지면 승자 모델로 200장만 따로 재면 된다.
#
# 이어 돌리기: 같은 --run 으로 다시 실행하면 이미 끝난 장은 건너뛴다(resume).
set -eo pipefail
source ~/OCR/vlm-env.sh
cd ~/OCR/ocr-server
mkdir -p ~/OCR/logs

KEY="${1:-qwen}"
REPO=$(vlm_repo "$KEY")
RUN="vlm_${KEY}_500"
LIST=eval/LLM/inputs/sample_500.txt

curl -sf "http://localhost:$VLM_PORT/v1/models" >/dev/null 2>&1   || { echo "✗ vLLM 서버가 안 떠 있다. bash ~/OCR/run-vlm-serve.sh $KEY 먼저." >&2; exit 1; }

# 서버가 지금 무슨 모델을 물고 있는지 확인 - 다른 모델이면 채점이 통째로 어긋난다
SERVING=$(curl -s "http://localhost:$VLM_PORT/v1/models" | grep -oE '"id":"[^"]+"' | head -1 | cut -d'"' -f4)
if [[ "$SERVING" != "$REPO" ]]; then
  echo "✗ 서버가 물고 있는 모델이 다르다: $SERVING (요청: $REPO)" >&2
  echo "  bash ~/OCR/run-vlm-serve.sh $KEY 로 바꿔 띄울 것." >&2
  exit 1
fi

vlm_say "$KEY · 500장 (full_text 제외) → $RUN"
stdbuf -oL -eL python3 -u eval/llm_runner.py   --server "$VLM_SERVER" --model "$REPO"   --list "$LIST" --run "$RUN" --no-fulltext   --max-tokens "$VLM_MAX_TOKENS" 2>&1 | tee -a ~/OCR/logs/vlm_500_"$KEY".log || true

vlm_say "결과"
cat "eval/runs/$RUN/run_meta.json"
echo
n=$(ls "eval/runs/$RUN/samples" 2>/dev/null | wc -l)
echo "samples $n / 500"
[[ -s "eval/runs/$RUN/errors.jsonl" ]] && { echo "실패:"; cat "eval/runs/$RUN/errors.jsonl"; } || echo "실패 없음"
cat <<EOF

덜 끝났으면 같은 명령을 다시 - 이미 끝난 장은 건너뛴다.
끝났으면 로컬에서:
  scp -r ubuntu@3.37.51.240:~/OCR/ocr-server/eval/runs/$RUN eval/runs/
  python eval/compare_run.py --ts $RUN --testset invoice_replay --skip-missing
  python eval/llm_ledger.py --add-run $RUN --label "$KEY · 500장" --write
EOF
