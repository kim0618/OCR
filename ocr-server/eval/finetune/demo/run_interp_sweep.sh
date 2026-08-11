#!/bin/bash
# 가중치 보간 스윕 (AWS) — base↔FT run 을 α별로 섞어 export→판정→전수 스캔까지.
#
#   bash run_interp_sweep.sh                       # 기본: v16(260807_1302)
#   bash run_interp_sweep.sh --ft-run=260811_XXXX  # 임의 run 에 스윕
#   bash run_interp_sweep.sh --ft-run=... --alphas="0.9 0.8 0.7"
#
# 학습 없음(순수 산술 + 추론). α당 export ~2분 + 판정 ~1분 + 전수 스캔 ~6분(T4).
# 산출물(재현 가능):
#   eval/finetune/versions/run_<FT>/interp/a<XX>/
#     interp_a<XX>.pdparams (+ .manifest.json: base·ft sha256, α) / inference/ / TARGET_EVAL.json
#   eval/finetune/demo/scans/<FT>_wf<XX>.jsonl   ← check_latest_run 이 자동 인식
# 판정 크롭 목록은 <현재 corpus dataset> 의 test.txt 를 쓰므로, 해당 run 직후
# (dataset 이 아직 그 run 것일 때) 돌리는 것이 안전하다. run-finetune.sh --interp 가 그 경로.
# 끝나면 로컬에서:  python eval/finetune/demo/check_latest_run.py
set -eo pipefail
export PYTHONUNBUFFERED=1
source ~/OCR/ocr-server/.venv/bin/activate
cd ~/OCR/ocr-server

FT_RUN=260807_1302
# α=1.0(=FT 그대로)은 본 run 스캔으로 이미 측정돼 있어 돌리지 않는다.
ALPHAS="0.9 0.8 0.7 0.6"
for a in "$@"; do
  case "$a" in
    --ft-run=*) FT_RUN="${a#*=}" ;;
    --alphas=*) ALPHAS="${a#*=}" ;;
    *) echo "알 수 없는 인자: $a"; exit 2 ;;
  esac
done

BASE=$(find ~/.paddleocr ~/.paddlex -name "korean_PP-OCRv5_mobile_rec_pretrained.pdparams" 2>/dev/null | head -1)
FT=eval/finetune/versions/run_${FT_RUN}/best_accuracy/best_accuracy.pdparams
CFG=eval/finetune/config_ppocrv5_rec_finetune.yaml
DRV=eval/finetune/paddlex_train.py
ROOT=eval/finetune/versions/run_${FT_RUN}/interp

if [ ! -f "$FT" ]; then echo "★FT 가중치가 없습니다: $FT"; exit 1; fi
if [ -z "$BASE" ] || [ ! -f "$BASE" ]; then echo "★base 가중치 캐시가 없습니다"; exit 1; fi

for A in $ALPHAS; do
  XX=$(python -c "print(int(round($A*100)))")
  DIR="$ROOT/a$XX"
  INF="$DIR/inference"
  PDP="$DIR/interp_a$XX.pdparams"
  SCAN_TAG="${FT_RUN}_wf$XX"
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

  echo "[α=$A] 타깃 판정"
  python eval/demo_checkpoint_eval.py --model-dir "$INF" \
      --output "$DIR/TARGET_EVAL.json" --tag "$SCAN_TAG" || true

  echo "[α=$A] 기준셋 전수 스캔 → scans/$SCAN_TAG.jsonl"
  python -u eval/demo_next_target.py --run-tag "$FT_RUN" \
      --scan-tag "$SCAN_TAG" --model-dir "$INF" --scan-only
done

echo "===== 보간 스윕 완료 (${FT_RUN}, α: $ALPHAS). 로컬에서 check_latest_run.py ====="
