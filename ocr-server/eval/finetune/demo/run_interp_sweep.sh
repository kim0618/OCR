#!/bin/bash
# 가중치 보간 스윕 (AWS) — base↔v16 을 α별로 섞어 export→판정→전수 스캔까지.
#
#   tmux new -s interp
#   bash ~/OCR/ocr-server/eval/finetune/demo/run_interp_sweep.sh
#
# 학습 없음(순수 산술 + 추론). α당 export ~2분 + 판정 26장 ~1분 + 전수 스캔 ~15분.
# 산출물(재현 가능):
#   eval/finetune/versions/run_260807_1302/interp/a<XX>/
#     interp_a<XX>.pdparams (+ .manifest.json: base·ft sha256, α)  / inference/  / TARGET_EVAL.json
#   eval/finetune/demo/scans/260810_wf<XX>.jsonl   ← check_latest_run 이 자동 인식
# 끝나면 로컬에서:  python eval/finetune/demo/check_latest_run.py
set -eo pipefail
export PYTHONUNBUFFERED=1
source ~/OCR/ocr-server/.venv/bin/activate
cd ~/OCR/ocr-server

# α=1.0(=v16 그대로)은 이미 260807_1302 로 측정돼 있어 돌리지 않는다.
ALPHAS="0.9 0.8 0.7 0.6"
BASE=~/.paddleocr/models/korean_PP-OCRv5_mobile_rec_pretrained.pdparams
FT=eval/finetune/versions/run_260807_1302/best_accuracy/best_accuracy.pdparams
CFG=eval/finetune/config_ppocrv5_rec_finetune.yaml
DRV=eval/finetune/paddlex_train.py
ROOT=eval/finetune/versions/run_260807_1302/interp
RUN_TAG=260807_1302          # demo_next_target 이 타깃 목록을 찾는 기준 run

if [ ! -f "$FT" ]; then echo "★v16 가중치가 없습니다: $FT"; exit 1; fi
if [ ! -f "$BASE" ]; then echo "★base 가중치가 없습니다: $BASE"; exit 1; fi
if pgrep -f "uvicorn" >/dev/null; then echo "★백엔드가 떠 있습니다 - 내리고 실행"; exit 1; fi

for A in $ALPHAS; do
  XX=$(python -c "print(int(round($A*100)))")
  DIR="$ROOT/a$XX"
  INF="$DIR/inference"
  PDP="$DIR/interp_a$XX.pdparams"
  SCAN_TAG="260810_wf$XX"
  echo "===== α=$A → $DIR ====="
  mkdir -p "$DIR"

  python eval/finetune/demo/interpolate_weights.py \
      --base "$BASE" --ft "$FT" --alpha "$A" --out "$PDP"

  echo "[α=$A] export"
  python "$DRV" -c "$CFG" -o Global.mode=export \
      -o Export.weight_path="$PDP" -o Global.output="$INF"
  if [ -z "$(find "$INF" -type f -print -quit)" ]; then
    echo "★α=$A inference 산출물이 비어 있음"; exit 1
  fi

  echo "[α=$A] 타깃 판정 26장"
  python eval/demo_checkpoint_eval.py --model-dir "$INF" \
      --output "$DIR/TARGET_EVAL.json" --tag "$SCAN_TAG" || true

  echo "[α=$A] 기준셋 전수 스캔 → scans/$SCAN_TAG.jsonl"
  python -u eval/demo_next_target.py --run-tag "$RUN_TAG" \
      --scan-tag "$SCAN_TAG" --model-dir "$INF" --scan-only
done

echo "===== 완료. 로컬에서: python eval/finetune/demo/check_latest_run.py ====="
